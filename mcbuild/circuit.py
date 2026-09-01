"""Does the circuit WORK — the question nothing in this pipeline has ever asked.

Everything here validates SHAPE. `audit` asks whether a block state is legal, whether a cell has
support, whether it collides; `blocks` asks whether the server has it; `palette` asks what it
costs. A redstone circuit passes every one of those while doing absolutely nothing, and you find
out by flipping the lever an hour later. That is this project's oldest failure mode -- *a clean
audit and a wrong build* -- pointed at the one subsystem where the wrongness is invisible.

**THE PRECEDENT IS `nightlight.propagate`.** The night pass is trusted because light is propagated
through the finished model and the spawnable cells are COUNTED, not reasoned about. Signal is the
same shape of problem: a value that spreads from sources, decays with distance, and is blocked by
geometry. So this is a simulator, and a circuit is verified before a single block is placed.

    sim = Circuit.of(model, origin)          # from a design, a capture, or a composite
    sim.set("lever", True)                   # drive an input
    trace = sim.run(ticks=20)                # advance in REDSTONE TICKS
    assert sim.powered(piston_pos)           # ...and assert what happened

WHAT IS MODELLED, and it is enough for every machine a build here needs:

    wire            power 0-15, -1 per step, derived connections (up/side/none), fixpoint solve
    redstone_block  a constant 15
    torch           inverts its attachment, powers the block ABOVE strongly, 1-tick delay
    lever/button    a source you drive; a button is a timed pulse
    plate           a source while pressed
    repeater        delay 1-4, one-way, LOCKED by a powered repeater/comparator on its side
    comparator      compare and subtract, rear vs the greater side, container fullness behind
    observer        a 1-tick pulse when the block it faces changes
    piston          extends while powered; sticky retracts what it pushed
    lamp/door/      driven outputs, so a test can assert on the thing a player sees
    dispenser       fires on a RISING edge, which is why a held signal dispenses once

WHAT IS NOT, stated because a simulator you trust past its limits is worse than none:

  * **QUASI-CONNECTIVITY.** Java pistons and dispensers also fire when the block ABOVE them is
    powered. Real circuits use it deliberately (BUD switches) and real circuits are broken by it
    accidentally. `strict_qc=True` turns the check on and REPORTS every cell where QC would change
    the answer, so a design can be told "this works, but only if you did not mean to use QC".
  * **Update order and 0-tick pulses.** Java's exact neighbour-update order decides sub-tick
    races. Anything depending on it is unverifiable here and `Circuit.warnings` says so.
  * **Entities.** Items, minecarts, mobs. A hopper's contents are an INPUT you state, not a thing
    that fills itself.
  * **ANYTHING DRIVEN BY A MOVING BLOCK.** Calibrated against a working bonemeal farm, the
    inspection reported seven "piston is not wired" - one whole row at a single course, with no
    wire, no observer and nothing overhead. They are driven by a redstone block that a piston
    PUSHES along, which is how half the compact farms in the game work and which no static
    inspection can see: at rest the driver is not next to the thing it drives. A finding of that
    shape on a machine you know works is this limit, not a fault.

So a green result means *this circuit is sound in the ordinary model*, never *this is exactly what
Java does*. The tests in `tests/test_circuit.py` pin the components against hand-worked cases.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field

from . import blocks

MAX_POWER = 15

# A face direction as a delta, in world axes.
DIRS = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0),
        "up": (0, 1, 0), "down": (0, -1, 0)}
HORIZONTAL = ("north", "south", "east", "west")
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east",
            "up": "down", "down": "up"}

# Blocks a signal treats as air for the purposes of "is this cell open".
AIRY = {"air", "cave_air", "void_air"}

# Constant sources.
SOURCES = {"redstone_block"}
# Things a test can assert on, and that a circuit exists in order to move.
OUTPUTS = {"redstone_lamp", "piston", "sticky_piston", "iron_door", "iron_trapdoor",
           "dispenser", "dropper", "note_block", "oak_door", "bell", "tnt"}


def _short(n: str) -> str:
    return n.split(":")[-1].split("[")[0]


@dataclass
class Cell:
    name: str
    props: dict = field(default_factory=dict)

    def prop(self, k: str, default: str = "") -> str:
        return self.props.get(k, default)


class Circuit:
    """A redstone world, simulated in redstone ticks."""

    # QUASI-CONNECTIVITY IS REAL JAVA BEHAVIOUR AND IS NOW MODELLED, NOT ONLY REPORTED.
    # minecraft.wiki, Redstone mechanics: pistons "can also be activated if a redstone signal is
    # supplied to the block above them, even if that block is air", and the same holds for
    # dispensers and droppers. The first version of this file only WARNED about it, which was the
    # honest thing to do while it was unverified - and Jack supplied the source, so it is a rule
    # now. `quasi_connectivity_risk()` still reports the cells where it MATTERS, because a circuit
    # that works only by accident of QC is worth knowing about either way.
    QC_BLOCKS = {"piston", "sticky_piston", "dispenser", "dropper"}

    def __init__(self, cells: dict, opaque_extra: set | None = None, qc: bool = True):
        self.qc = qc
        self.cells: dict[tuple, Cell] = cells
        self.power: dict[tuple, int] = {}          # wire power
        self.strong: dict[tuple, int] = {}         # blocks powered hard enough to feed wire
        self.weak: dict[tuple, int] = {}           # blocks powered enough to drive a component
        self.inputs: dict[tuple, bool] = {}        # levers/buttons/plates the caller drives
        self.delayed: dict[tuple, list] = {}       # repeater/torch scheduled changes
        self.state: dict[tuple, bool] = {}         # powered-ness of stateful components
        self.pulses: dict[tuple, int] = {}         # button/observer countdowns
        self.fired: collections.Counter = collections.Counter()   # dispenser/dropper edges
        self.warnings: list[str] = []
        self.tick_no = 0
        self._opaque_extra = opaque_extra or set()

    # ------------------------------------------------------------------ construction

    @classmethod
    def of(cls, model, origin=(0, 0, 0)) -> "Circuit":
        """Read a `schem.Model` into a circuit, in WORLD coordinates.

        World coordinates on purpose: a circuit is usually verified against a design COMPOSITED
        onto a capture, and two grids with different origins cannot be reasoned about together.
        That is the same contract the sidecars carry everywhere else here.
        """
        cells = {}
        sy, sz, sx = model.ids.shape
        names = model.names
        ox, oy, oz = origin
        import numpy as np
        for y, z, x in np.argwhere(model.ids > 0):
            n = _short(names[model.ids[y, z, x]])
            if n in AIRY:
                continue
            cells[(int(x) + ox, int(y) + oy, int(z) + oz)] = Cell(
                n, model.props_at(int(x), int(y), int(z)))
        return cls(cells)

    @classmethod
    def from_cells(cls, spec: dict) -> "Circuit":
        """{(x, y, z): "repeater[facing=east,delay=2]"} — for tests and hand-built cases."""
        cells = {}
        for pos, s in spec.items():
            name = _short(s)
            props = {}
            if "[" in s and s.endswith("]"):
                for part in s[s.index("[") + 1:-1].split(","):
                    k, _, v = part.partition("=")
                    props[k.strip()] = v.strip()
            cells[pos] = Cell(name, props)
        return cls(cells)

    # ------------------------------------------------------------------ geometry

    def at(self, pos) -> Cell | None:
        return self.cells.get(pos)

    def name(self, pos) -> str:
        c = self.cells.get(pos)
        return c.name if c else "air"

    def opaque(self, pos) -> bool:
        """Can a signal pass THROUGH this cell as a block.

        Uses the registry rather than a list, which is rule 11: `is_full_cube` is derived from the
        block TYPE, and a hand-written list of "solid" blocks has been wrong in this repo before.
        """
        n = self.name(pos)
        if n == "air":
            return False
        if n in self._opaque_extra:
            return True
        return blocks.is_full_cube(n)

    def neighbours(self, pos):
        x, y, z = pos
        for d, (dx, dy, dz) in DIRS.items():
            yield d, (x + dx, y + dy, z + dz)

    # ------------------------------------------------------------------ inputs

    def set(self, pos, on: bool) -> None:
        """Drive a lever/plate. A BUTTON should use `press` — holding a button is not a thing."""
        self.inputs[pos] = on

    def press(self, pos, ticks: int = 10) -> None:
        """A button: on for `ticks` redstone ticks, then off by itself.

        Modelled as a real pulse rather than a held input because half the circuits that exist
        only work on an EDGE, and a test that holds a button forever silently tests a lever.
        """
        self.inputs[pos] = True
        self.pulses[pos] = ticks

    # ------------------------------------------------------------------ the solve

    def _sources(self) -> dict:
        """Who is providing power this tick, in the TWO ways Minecraft distinguishes.

        THE SPLIT IS THE WHOLE MODEL, and getting it wrong is what made the first version report a
        torch as powering nothing:

          * `emit[pos]`  - this cell radiates to all six neighbours. A torch, a lever, a plate and
            a block of redstone do this; it is how wire beside a torch lights up.
          * `into[pos]`  - this cell is being driven AT that position, by something aimed at it. A
            repeater and a comparator do this and ONLY this: a repeater does not leak sideways,
            which is the entire reason it is used to isolate one line from another. A lit torch
            also drives the block directly above it, which is how every inverter stack works.

        A block carrying `into` is what Minecraft calls STRONGLY powered, and it passes 15 on to
        any wire touching it. A block merely touched by wire is weakly powered: it drives a piston
        or a lamp, and it does NOT re-power wire on the other side. Conflating those two is how a
        simulator certifies a circuit that shorts across a wall.
        """
        emit, into = {}, {}
        # A TORCH DOES NOT POWER THE BLOCK IT IS ATTACHED TO. Without this the torch powers its own
        # support, reads that as "my attachment is powered", switches itself off, and the whole
        # circuit oscillates every other tick - which is exactly what the first version did, and it
        # looked like a delay bug. A LEVER is the opposite: it strongly powers its attachment, which
        # is what `into` below is for. The two cases are not symmetric and cannot share a rule.
        attach: dict = {}
        for pos, c in self.cells.items():
            n = c.name
            if n in SOURCES:
                emit[pos] = MAX_POWER
            elif n in ("lever", "stone_button", "oak_button", "polished_blackstone_button",
                       "stone_pressure_plate", "oak_pressure_plate",
                       "light_weighted_pressure_plate", "heavy_weighted_pressure_plate"):
                if self.inputs.get(pos):
                    emit[pos] = MAX_POWER
                    # **A PRESSURE PLATE HAS NO `face` PROPERTY, AND THE DEFAULT WAS "wall".**
                    # A plate lies on the ground and strongly powers the block BENEATH it
                    # (minecraft.wiki, Redstone mechanics); read through `_attachment` with a
                    # made-up wall face it strongly powered a cell to one SIDE instead, decided by
                    # a `facing` the block does not have either. So a plate could power a lamp
                    # beside it - `emit` reaches all six neighbours and that part was right - and
                    # could never feed dust under its own support, which is where a hidden machine
                    # has to take its trigger from. Legal states, correct blocks, and a set piece
                    # that cannot fire.
                    if n.endswith("_pressure_plate"):
                        att = (pos[0], pos[1] - 1, pos[2])
                    else:
                        att = self._attachment(pos, c.prop("face", "wall"),
                                               c.prop("facing", "north"))
                    if att is not None:
                        into[att] = MAX_POWER
            elif n in ("redstone_torch", "redstone_wall_torch"):
                att = self._attachment(pos, "floor" if n == "redstone_torch" else "wall",
                                       c.prop("facing", "north"))
                attach[pos] = att
                if self.state.get(pos, True):                 # a torch starts LIT
                    emit[pos] = MAX_POWER
                    into[(pos[0], pos[1] + 1, pos[2])] = MAX_POWER
            elif n == "repeater":
                if self.state.get(pos, False):
                    into[self._front(pos, c)] = MAX_POWER
            elif n == "comparator":
                out = int(self.state.get(pos, 0) or 0)
                if out:
                    into[self._front(pos, c)] = out
            elif n == "observer":
                if self.pulses.get(pos, 0) > 0:
                    into[self._front(pos, c)] = MAX_POWER
        return {"emit": emit, "into": into, "attach": attach}

    def _attachment(self, pos, face: str, facing: str):
        x, y, z = pos
        if face == "floor":
            return (x, y - 1, z)
        if face == "ceiling":
            return (x, y + 1, z)
        d = DIRS.get(OPPOSITE.get(facing, "north"))
        return (x + d[0], y + d[1], z + d[2]) if d else None

    def _front(self, pos, c: Cell):
        """The cell a repeater/comparator/observer OUTPUTS into.

        A repeater's `facing` is the direction it points, which is where the signal GOES. Getting
        this backwards is the commonest redstone mistake and it is invisible in a render -- the
        same reason the stair convention is asserted rather than eyeballed.
        """
        d = DIRS.get(c.prop("facing", "north"), (0, 0, 0))
        return (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])

    def _back(self, pos, c: Cell):
        d = DIRS.get(OPPOSITE.get(c.prop("facing", "north"), "south"), (0, 0, 0))
        return (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])

    def _sides(self, pos, c: Cell):
        f = c.prop("facing", "north")
        if f in ("up", "down"):
            return []
        left = {"north": "west", "south": "east", "east": "north", "west": "south"}[f]
        right = OPPOSITE[left]
        out = []
        for s in (left, right):
            d = DIRS[s]
            out.append((pos[0] + d[0], pos[1] + d[1], pos[2] + d[2]))
        return out

    def _wire_connects(self, pos, other) -> bool:
        """Does wire at `pos` carry signal to `other`.

        DERIVED, never read off the state. Connections are what the game computes from the
        neighbourhood -- `work.INTENTIONAL` drops them for exactly this reason -- so a simulator
        that trusted the recorded `north=side` would be grading the design's own guess.
        """
        if self.name(other) == "redstone_wire":
            return True
        # up a block: wire climbs the side of a non-opaque-topped block
        up = (other[0], other[1] + 1, other[2])
        if self.name(up) == "redstone_wire" and not self.opaque((pos[0], pos[1] + 1, pos[2])):
            return True
        # down a block
        down = (other[0], other[1] - 1, other[2])
        if self.name(down) == "redstone_wire" and not self.opaque(other):
            return True
        return False

    def _solve_wire(self, src: dict) -> None:
        """Spread power through wire to a fixpoint - the same relaxation `nightlight` uses."""
        emit, into = src["emit"], src["into"]
        power = {}
        for pos, c in self.cells.items():
            if c.name != "redstone_wire":
                continue
            best = into.get(pos, 0)                    # aimed at directly, e.g. a repeater's front
            for d, nb in self.neighbours(pos):
                if src.get("attach", {}).get(nb) == pos:
                    continue                        # a torch never powers its own support
                best = max(best, emit.get(nb, 0))
                # A STRONGLY powered solid block passes 15 to wire touching it. A weakly powered
                # one does not, and that difference is the whole point of the split.
                if self.opaque(nb) and into.get(nb, 0) > 0:
                    best = max(best, into[nb])
            power[pos] = min(MAX_POWER, best)
        changed = True
        guard = 0
        while changed and guard < MAX_POWER + 2:
            guard += 1
            changed = False
            for pos, p in list(power.items()):
                if p <= 1:
                    continue
                for d, nb in self.neighbours(pos):
                    if d in ("up", "down"):
                        continue
                    for cand in (nb, (nb[0], nb[1] + 1, nb[2]), (nb[0], nb[1] - 1, nb[2])):
                        if self.name(cand) != "redstone_wire":
                            continue
                        if cand == nb and not self._wire_connects(pos, nb):
                            continue
                        if power.get(cand, 0) < p - 1:
                            power[cand] = p - 1
                            changed = True
        self.power = power

    def _block_power(self, pos, src: dict) -> int:
        """How hard this cell is driven - what a lamp, a piston or a repeater beside it sees."""
        # A CELL THAT EMITS IS ITSELF POWERED. Missing this reported a lever as unpowered, so a
        # repeater fed directly by one never turned on - and the failure looked like the delay
        # logic, which is where an hour would have gone.
        best = max(src["into"].get(pos, 0), src["emit"].get(pos, 0))
        for d, nb in self.neighbours(pos):
            if src.get("attach", {}).get(nb) == pos:
                continue                            # a torch never powers its own support
            best = max(best, src["emit"].get(nb, 0))
            if self.name(nb) == "redstone_wire":
                best = max(best, self.power.get(nb, 0))
            elif self.opaque(nb) and src["into"].get(nb, 0) > 0:
                best = max(best, src["into"][nb])
        return best

    _last_src: dict = {"emit": {}, "into": {}, "attach": {}}

    def powered(self, pos) -> bool:
        """Is this cell being driven right now — the assertion a test actually wants."""
        if self.name(pos) == "redstone_wire":
            return self.power.get(pos, 0) > 0
        return self._block_power(pos, self._last_src) > 0

    def level(self, pos) -> int:
        if self.name(pos) == "redstone_wire":
            return self.power.get(pos, 0)
        return self._block_power(pos, self._last_src)

    # ------------------------------------------------------------------ the tick

    def run(self, ticks: int = 20) -> list:
        """Advance `ticks` REDSTONE ticks (2 game ticks each). Returns a trace of output states."""
        trace = []
        for _ in range(max(0, ticks)):
            trace.append(self.step())
        return trace

    def step(self) -> dict:
        """One redstone tick: solve the combinational network, then advance the delayed parts."""
        self.tick_no += 1
        src = self._sources()
        self._solve_wire(src)
        self._last_src = src

        # --- what every delayed component WANTS to be, given this tick's network
        want: dict[tuple, object] = {}
        for pos, c in self.cells.items():
            n = c.name
            if n in ("redstone_torch", "redstone_wall_torch"):
                att = src["attach"].get(pos)
                # A TORCH INVERTS ITS ATTACHMENT. Off when the block it stands on is powered.
                want[pos] = not (att is not None and self._block_power(att, src) > 0)
            elif n == "repeater":
                if self._locked(pos, c, src):
                    continue                                   # a locked repeater holds its state
                back = self._back(pos, c)
                want[pos] = self._drives(back, src, pos)
            elif n == "comparator":
                want[pos] = self._comparator_out(pos, c, src)
            elif n == "observer":
                pass                                           # handled by pulse countdown

        # --- delays
        for pos, target in want.items():
            c = self.cells[pos]
            delay = 1
            if c.name == "repeater":
                delay = int(c.prop("delay", "1") or 1)
            current = self.state.get(pos, True if c.name.endswith("torch") else
                                     (0 if c.name == "comparator" else False))
            if target == current:
                self.delayed.pop(pos, None)
                continue
            queue = self.delayed.get(pos)
            if queue is None or queue[1] != target:
                self.delayed[pos] = [delay, target]
            else:
                queue[0] -= 1
                if queue[0] <= 0:
                    self.state[pos] = target
                    self.delayed.pop(pos, None)

        # --- pulses (buttons, observers) tick down
        for pos in list(self.pulses):
            self.pulses[pos] -= 1
            if self.pulses[pos] <= 0:
                self.pulses.pop(pos)
                if self.name(pos) in ("stone_button", "oak_button", "polished_blackstone_button"):
                    self.inputs[pos] = False

        # --- outputs, and the RISING EDGE that makes a dispenser fire once rather than forever
        out = {}
        for pos, c in self.cells.items():
            if c.name not in OUTPUTS:
                continue
            on = self._block_power(pos, src) > 0
            if not on and self.qc and c.name in self.QC_BLOCKS:
                # ...or the block ABOVE is powered, even when that block is air.
                on = self._block_power((pos[0], pos[1] + 1, pos[2]), src) > 0
            was = self.state.get(("out",) + pos, False)
            if on and not was and c.name in ("dispenser", "dropper"):
                self.fired[pos] += 1
            self.state[("out",) + pos] = on
            out[pos] = on
        return out

    def _drives(self, pos, src: dict, reader=None) -> bool:
        """Is this cell delivering a signal INTO a component that reads it."""
        if self.name(pos) == "redstone_wire":
            return self.power.get(pos, 0) > 0
        aimed = self._aimed(pos, src, reader)
        if aimed is not None:
            return aimed > 0
        return self._block_power(pos, src) > 0

    def _aimed(self, pos, src: dict, reader) -> int | None:
        """What a repeater/comparator at `pos` delivers to `reader` — None if it is neither.

        **A REPEATER IS NOT A CONDUCTOR, AND READING AMBIENT POWER AT ITS CELL IS A LEAK.** Both
        `_read` and `_drives` used to fall through to `_block_power(pos)`, which is the maximum of
        everything touching that cell — so a repeater standing beside an unrelated dust run
        reported that run's level to whatever was reading it. Measured on `circuits.window(5, 9)`,
        the gate's side input read 12 instead of the repeater's own 15 and the subtract gave
        `15 - 12 = 3`: the gate PASSED a level it exists to block, quietly and by three, and the
        machine's own test could not see it because the simulator and the build agreed.

        A repeater or comparator outputs only out of its FRONT, and only into the cell it faces.
        Read from anywhere else it is a solid obstruction carrying nothing, which is what 0 means
        here. That distinction is the same one `_sources` already draws between `emit` and `into`;
        it simply was not applied to the two places that read a neighbour.
        """
        c = self.at(pos)
        if c is None:
            # **AN EMPTY CELL IS NOT AN INPUT.** `_block_power` answers "how hard is this cell
            # driven", which for AIR is the maximum of everything touching it - and that is right
            # for quasi-connectivity, where the game really does read the empty cell above a
            # piston. It is quite wrong for a component's own back or side: dust running past a
            # comparator one cell out is DIAGONAL to it and powers nothing, and the game knows it.
            #
            # Read the other way, the casino's pulse had a permanent 14 on its subtract's side the
            # moment the button's descent passed within two cells - so the monostable never opened,
            # the randomiser's dropper was never triggered, its hopper never received an item, and
            # `double_or_none` and `lucky_number` could not pay at any odds. They shipped that way,
            # and every test drove the hopper with `fill`, which states a roll rather than rolling
            # one, so the entire input half of both machines was unexercised.
            return 0
        if c.name not in ("repeater", "comparator"):
            return None
        if reader is not None and self._front(pos, c) != reader:
            return 0
        if c.name == "repeater":
            return MAX_POWER if self.state.get(pos, False) else 0
        return int(self.state.get(pos, 0) or 0)

    def _locked(self, pos, c: Cell, src: dict) -> bool:
        """A repeater is LOCKED by a powered repeater or comparator pointing into its side.

        This is the mechanism every memory cell in the game is built from, and a simulator without
        it reports every latch as a wire.
        """
        for side in self._sides(pos, c):
            sc = self.at(side)
            if sc is None or sc.name not in ("repeater", "comparator"):
                continue
            if self._front(side, sc) != pos:
                continue                                       # must point INTO us
            if self.state.get(side):
                return True
        return False

    def _comparator_out(self, pos, c: Cell, src: dict) -> int:
        back = self._back(pos, c)
        rear = self._read(back, src, pos)
        side = 0
        for s in self._sides(pos, c):
            side = max(side, self._read(s, src, pos))
        if c.prop("mode", "compare") == "subtract":
            return max(0, rear - side)
        return rear if rear >= side else 0

    def _read(self, pos, src: dict, reader=None) -> int:
        """Signal strength a comparator at `reader` reads from this cell.

        `reader` is not decoration: a repeater or comparator at `pos` delivers 15 (or its own
        output) ONLY into the cell it faces, and nothing at all anywhere else. See `_aimed`.
        """
        n = self.name(pos)
        if n == "redstone_wire":
            return self.power.get(pos, 0)
        fill = self.container.get(pos)
        if fill is not None:
            return int(fill)
        aimed = self._aimed(pos, src, reader)
        if aimed is not None:
            return aimed
        return self._block_power(pos, src)

    # Container fullness is an INPUT, not something that fills itself: this simulator has no
    # entities, and pretending a hopper fills would certify a sorter that has never seen an item.
    container: dict = {}

    def fill(self, pos, strength: int) -> None:
        """State what a comparator reads out of the container at `pos` (0-15)."""
        self.container = dict(self.container)
        self.container[pos] = max(0, min(MAX_POWER, int(strength)))

    # ------------------------------------------------------------------ honesty

    def quasi_connectivity_risk(self) -> list:
        """Cells that CAN be fired from the block above them.

        Now that QC is modelled rather than assumed away, this is no longer a disclaimer - it is a
        list of the places where the circuit's behaviour depends on a mechanic most people do not
        expect. A build that works only by accident of QC is worth knowing about, and so is one
        that a stray piece of dust overhead would fire.
        """
        risky = []
        for pos, c in self.cells.items():
            if c.name not in self.QC_BLOCKS:
                continue
            above = (pos[0], pos[1] + 1, pos[2])
            if self.name(above) == "redstone_wire" or self.at(above) is not None:
                risky.append(pos)
        return risky


# ---------------------------------------------------------------------- static inspection

# Components that only make sense if something drives them, and that drive something in turn.
DRIVEN = {"repeater", "comparator", "redstone_lamp", "piston", "sticky_piston", "dispenser",
          "dropper", "note_block", "iron_door", "iron_trapdoor", "tnt"}
EMITTERS = {"redstone_block", "lever", "stone_button", "oak_button",
            "polished_blackstone_button", "redstone_torch", "redstone_wall_torch",
            "stone_pressure_plate", "oak_pressure_plate", "observer",
            "light_weighted_pressure_plate", "heavy_weighted_pressure_plate", "daylight_detector",
            "target", "sculk_sensor", "trapped_chest", "repeater", "comparator"}


PISTONS = {"piston", "sticky_piston"}


def moving_driver_near(c, pos, reach: int = 2) -> bool:
    """Could a MOVING block drive this cell.

    THE LIMIT THIS FILE ALREADY RECORDS, TURNED INTO A CHECK. Half the compact machines in the game
    are driven by a redstone block that a piston pushes: at rest the driver is not next to the
    thing it drives, so a static inspection calls a working machine unwired. Calibrated against two
    builds that demonstrably work - a bonemeal farm with seven "unwired" pistons in one row, and a
    contraption whose repeater points at empty air with a redstone block on a sticky piston one
    cell above it.

    Deliberately generous: a piston or a redstone block anywhere within `reach` is enough to say
    "this may be driven by something that moves". A false NEGATIVE here costs a real finding; a
    false positive costs a warning nobody needed, and this file's own rule is that a check which
    cries wolf is a check nobody runs.
    """
    x, y, z = pos
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                n = c.name((x + dx, y + dy, z + dz))
                if n in PISTONS or n == "redstone_block":
                    return True
    return False


def _observed(c, pos) -> bool:
    """Is an observer touching this component.

    An observer PULSES on a block update rather than holding a signal, and the update it watches
    for may be a block that only exists while something moves. Two repeaters in a working
    contraption came back as "reads nothing" with observers on two sides; the model cannot follow
    that, so it does not claim to.
    """
    for d, nb in c.neighbours(pos):
        if c.name(nb) == "observer":
            return True
    return False


def inspect(model, origin=(0, 0, 0)) -> list:
    """Circuit SMELLS in a design, without needing a per-design contract.

    `verify` answers "does this machine do what it promises", which needs someone to have written
    the promise down. This answers the cheaper question every redstone build should be asked
    anyway, and it is the one that can run on EVERY design automatically:

      * **a wire run longer than 15 with no repeater in it.** The signal dies partway and the far
        half looks like a build that was never finished. This is the single commonest redstone
        mistake and it is completely invisible in a render.
      * **a driven component with nothing that could ever drive it** - a repeater, lamp or piston
        in a connected group containing no source at all.
      * **a repeater or comparator pointing into thin air**, which is a line that was rerouted and
        left behind.
      * **quasi-connectivity risk**, reported rather than modelled - see the module docstring.

    Returns a list of (kind, pos, detail). Empty means nothing suspicious, never "verified".
    """
    c = Circuit.of(model, origin) if hasattr(model, "ids") else model
    out = []

    # IS THIS MODEL EVEN ORIENTED? A pre-1.13 `.schematic` keeps facing in the `Data` nibbles, and
    # `sponge.load_mcedit` does not decode them - so every repeater and comparator arrives with no
    # `facing` at all and `_front`/`_back` fall back to north, pointing at arbitrary cells. Run
    # blind, one such file produced 66 direction findings, every one of them about the reader
    # rather than the build.
    #
    # Detected rather than declared, so it is right for any source: if not one directional
    # component carries a facing, the direction checks are SKIPPED and the reason is the finding.
    directional = [p for p, cell in c.cells.items()
                   if cell.name in ("repeater", "comparator", "observer", "piston", "sticky_piston")]
    oriented = any(c.at(p).prop("facing") for p in directional)
    if directional and not oriented:
        out.append(("orientation unknown", directional[0],
                    f"{len(directional)} directional component(s) carry no facing - this model came "
                    f"from a format that stores it separately (pre-1.13 .schematic). Direction "
                    f"checks are skipped rather than guessed."))

    wires = [p for p, cell in c.cells.items() if cell.name == "redstone_wire"]
    seen = set()
    for start in wires:
        if start in seen:
            continue
        # one connected dust group
        group, stack = set(), [start]
        while stack:
            p = stack.pop()
            if p in group:
                continue
            group.add(p)
            for d, nb in c.neighbours(p):
                for cand in (nb, (nb[0], nb[1] + 1, nb[2]), (nb[0], nb[1] - 1, nb[2])):
                    if c.name(cand) == "redstone_wire" and cand not in group:
                        stack.append(cand)
        seen |= group

        # Is anything at all able to power this group, and WHICH CELLS does it reach.
        #
        # SEEDS, NOT SOURCES. The first version collected the emitter - which may be two cells away,
        # through a block it powers - and then seeded the distance walk from wire ADJACENT TO THAT
        # EMITTER. The two do not match: a dust cell fed through a stone block is never adjacent to
        # the torch under it, so the walk seeded nothing, every cell measured as unreachable, and
        # six runs of a working build were reported as dying. Collect the wire cells the power
        # actually ARRIVES AT and walk from those.
        powered_by = set()
        seeds = set()
        for p in group:
            for d, nb in c.neighbours(p):
                n = c.name(nb)
                if n in EMITTERS or n in SOURCES:
                    powered_by.add(nb)
                    seeds.add(p)
                # a block driven from the far side counts too: a torch under it, a repeater into it
                if c.opaque(nb):
                    for d2, nb2 in c.neighbours(nb):
                        if c.name(nb2) in ("redstone_torch", "redstone_wall_torch", "repeater",
                                           "comparator", "observer", "redstone_block", "lever"):
                            powered_by.add(nb2)
                            seeds.add(p)
        if not powered_by:
            out.append(("dust with no source", min(group),
                        f"{len(group)} cells of wire that nothing can power"))
            continue

        # THE 15-BLOCK RULE. Measured as the true path length through the dust from the nearest
        # source, not as a bounding box: a coiled run is just as dead as a straight one.
        dist = {p: 0 for p in seeds}
        frontier = collections.deque(dist)
        while frontier:
            p = frontier.popleft()
            for d, nb in c.neighbours(p):
                for cand in (nb, (nb[0], nb[1] + 1, nb[2]), (nb[0], nb[1] - 1, nb[2])):
                    if cand in group and cand not in dist:
                        dist[cand] = dist[p] + 1
                        frontier.append(cand)
        far = [p for p in group if dist.get(p, 99) >= MAX_POWER]
        if far:
            out.append(("wire dies before the end", min(far),
                        f"{len(far)} cell(s) more than {MAX_POWER} from any source - "
                        f"put a repeater in the run"))

    for pos, cell in c.cells.items():
        if cell.name in ("repeater", "comparator") and oriented:
            front = c._front(pos, cell)
            if c.at(front) is None and not moving_driver_near(c, front):
                out.append((f"{cell.name} drives nothing", pos,
                            "it points at empty space - a rerouted line left behind?"))
            back = c._back(pos, cell)
            if c.at(back) is None and not moving_driver_near(c, back) and not _observed(c, pos):
                out.append((f"{cell.name} reads nothing", pos, "nothing behind it to read"))
        elif cell.name in DRIVEN and cell.name not in ("repeater", "comparator"):
            # A COMPONENT DOES NOT HAVE TO TOUCH DUST. Half the machines on this island are driven
            # by a powered BLOCK - a torch underneath it, a repeater aimed into it - and the first
            # version of this check called all fifteen of Jack's dispensers unwired. A check that
            # cries wolf is a check nobody runs, which is a rule this project already wrote down
            # about the audit.
            near = False
            # A DOOR IS ONE MECHANISM IN TWO BLOCKS. Power reaching EITHER half opens it, so the
            # half that is not next to the wiring is not an unwired component - it is the top of
            # a door that works. Reported per cell, every correctly built iron door in this repo
            # came back as a finding, which is exactly the crying-wolf this file calibrates
            # against on four reference builds.
            probe = [pos]
            if cell.name.endswith("_door"):
                half = cell.prop("half", "lower")
                other = (pos[0], pos[1] + (-1 if half == "upper" else 1), pos[2])
                if c.name(other) == cell.name:
                    probe.append(other)
            # QUASI-CONNECTIVITY COUNTS AS WIRED, because it is now MODELLED rather than merely
            # reported. Calibrated against a working bonemeal farm, which came back with seven
            # "piston is not wired" findings on pistons that a real build fires from above - a
            # check that cries wolf on a machine that demonstrably works is a check nobody runs.
            if c.name(pos) in Circuit.QC_BLOCKS:
                above = (pos[0], pos[1] + 1, pos[2])
                for d2, nb2 in c.neighbours(above):
                    n2 = c.name(nb2)
                    if n2 == "redstone_wire" or n2 in EMITTERS or n2 in SOURCES:
                        near = True
                        break
            for cell_pos in probe:
                for d, nb in c.neighbours(cell_pos):
                    n = c.name(nb)
                    if n == "redstone_wire" or n in EMITTERS or n in SOURCES:
                        near = True
                        break
                    if c.opaque(nb):
                        for d2, nb2 in c.neighbours(nb):
                            if c.name(nb2) in ("redstone_torch", "redstone_wall_torch", "repeater",
                                               "comparator", "lever", "redstone_block",
                                               "redstone_wire", "observer"):
                                near = True
                                break
                    if near:
                        break
                if near:
                    break
            if not near and not moving_driver_near(c, pos):
                out.append((f"{cell.name} is not wired", pos,
                            "no wire and no source touches it"))

    # ONE LINE, NOT SIXTY-TWO. The same farm reported 62 of these, and every one was a piston in a
    # piston machine with something over it - which is what a piston machine looks like. A per-cell
    # warning that fires on every cell of a working build is noise, and noise is how a real finding
    # gets scrolled past. Reported as a count, with one example.
    qc = c.quasi_connectivity_risk()
    if qc:
        out.append(("quasi-connectivity", qc[0],
                    f"{len(qc)} component(s) can also fire from the block above - modelled, but "
                    f"worth knowing if you did not intend it"))
    return out


def near_edge(model, origin, pos, margin: int = 1) -> bool:
    """Is this finding within `margin` of the model's own boundary.

    EVERY FINITE CUT TRUNCATES SOMETHING. The audit already knows this - a capture "has problems of
    its own, so reporting them against the design sends you hunting faults you did not cause" - and
    it is just as true of a schematic somebody exported. A piston at the edge of a cropped farm has
    no driver IN THE FILE and may be perfectly driven in the world.

    A finding away from the edge has no such excuse, which is the useful half.
    """
    sy, sz, sx = model.ids.shape
    ox, oy, oz = origin
    x, y, z = pos
    return (x - ox <= margin or x - ox >= sx - 1 - margin
            or y - oy <= margin or y - oy >= sy - 1 - margin
            or z - oz <= margin or z - oz >= sz - 1 - margin)


def report(findings: list) -> str:
    if not findings:
        return "circuit: nothing suspicious (this is a SMELL check, not a proof that it works)"
    by = collections.Counter(k for k, _, _ in findings)
    lines = [f"circuit: {len(findings)} finding(s)"]
    for kind, n in by.most_common():
        first = next(f for f in findings if f[0] == kind)
        lines.append(f"  {kind} x{n}  e.g. {first[1]} - {first[2]}")
    return "\n".join(lines)


def has_redstone(model) -> bool:
    """Is this design worth inspecting at all."""
    names = {_short(n) for n in model.names}
    return bool(names & (EMITTERS | DRIVEN | SOURCES | {"redstone_wire"}))
