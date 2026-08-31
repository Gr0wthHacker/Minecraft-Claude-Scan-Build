"""A library of circuits that are VERIFIED, not drawn.

Every module here is a function that emits cells plus a stated CONTRACT — what it does, how long
it takes, what drives it and what it drives. `tests/test_circuits.py` builds each one, runs it
through `mcbuild.circuit`, and asserts the contract. A module whose contract is not asserted does
not belong in this file, because the whole reason this file exists is that a redstone build is the
one thing in this project whose wrongness is invisible in every render, every audit and every BOM.

    clock(pos, period)          a repeating pulse
    pulse(pos, length)          a button press stretched to a fixed length
    latch(pos)                  set/reset memory, from two locked repeaters
    randomiser(pos, n)          ONE of n outputs, unpredictably - the casino's whole premise
    payout(pos, n)              n droppers fired one at a time from a single edge
    lamp_bank(pos, n)           n lamps driven together, for signage

**RANDOMNESS IS THE HARD ONE AND IT IS NOT A CIRCUIT TRICK.** Redstone is deterministic; every
"random" build in Minecraft borrows entropy from something the game simulates loosely - item
routing through a hopper into several droppers, a dispenser firing into water, a minecart on a
junction. `randomiser` uses the hopper-and-droppers form, and **the simulator cannot verify the
randomness** - it has no entities. What it verifies is that exactly one output fires per trigger
and that the mechanism resets. The randomness itself is a property of the game, stated here and
tested in world, and `RANDOM_NOTE` says so wherever it is used.
"""
from __future__ import annotations

RANDOM_NOTE = ("the odds come from the ITEM MIX, not the wiring: a dropper ejects a uniformly "
               "random one of its occupied slots. The mix is recorded in `stock` and MUST be "
               "loaded exactly - the simulator has no entities and cannot check it for you.")

# Direction helpers, matching mcbuild.circuit.
STEP = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
BACKWARD = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _off(pos, d: str, n: int = 1):
    dx, dy, dz = STEP[d]
    return (pos[0] + dx * n, pos[1] + dy * n, pos[2] + dz * n)


def clock(pos, period: int = 4, facing: str = "east") -> dict:
    """A repeating pulse: a torch whose own output comes back, delayed, and switches it off.

    THE LOOP MUST CLOSE ON THE TORCH'S SUPPORT BLOCK, NOT ON THE TORCH. The first version pointed
    the repeater at the torch's own cell, which does nothing at all -- a torch reads the block it
    is ATTACHED to and nothing else. It emitted four tidy blocks, audited clean, and never ticked
    once. That is this whole file's reason for existing, found on its own first module.

    Built along +Z from `pos`; `facing` is accepted for symmetry with the other modules and does
    not rotate the footprint yet.

    CONTRACT: `out` toggles for ever with no input, and a larger `period` toggles less often.
    """
    period = max(1, min(4, int(period)))
    x, y, z = pos
    return {
        "cells": {
            (x, y, z): "stone",                                     # the torch's support
            (x + 1, y, z): "redstone_wall_torch[facing=east]",      # attached to the support
            (x + 1, y, z + 1): "redstone_wire",                     # lit by the torch
            (x + 1, y, z + 2): "redstone_wire",
            (x, y, z + 2): "redstone_wire",                         # ...and back round
            (x, y, z + 1): f"repeater[facing=north,delay={period}]",  # front = the support
        },
        "out": (x + 1, y, z + 1),
        "contract": f"free-running, {period}-tick delay in the loop; never settles",
    }


def latch(pos, facing: str = "east") -> dict:
    """Set/reset memory: two repeaters locking each other.

    This is the mechanism every memory cell in the game is built from, and the reason
    `circuit._locked` exists. A latch that does not HOLD is a wire with extra steps.

    CONTRACT: a pulse on `set` turns `out` on and it STAYS on after the pulse ends; a pulse on
    `reset` turns it off and it stays off.
    """
    side = "north" if facing in ("east", "west") else "east"
    a = pos
    b = _off(pos, side, 2)
    return {
        "cells": {
            a: f"repeater[facing={facing},delay=1]",
            _off(a, side, 1): f"repeater[facing={BACKWARD[side]},delay=1]",
            b: f"repeater[facing={facing},delay=1]",
            _off(b, BACKWARD[side], 1): f"repeater[facing={side},delay=1]",
        },
        "set": _off(a, BACKWARD[facing], 1),
        "reset": _off(b, BACKWARD[facing], 1),
        "out": _off(a, facing, 1),
        "contract": "holds its state after the input pulse ends",
    }


def pulse(pos, length: int = 2, facing: str = "east", side: int = 1) -> dict:
    """Stretch any input - HELD OR NOT - to a fixed-length pulse. A rising-edge monostable.

    A casino needs this because a player HOLDS a button and a payout must fire once. It is the
    same reason `circuit` models a dispenser as edge-triggered.

    **THE FIRST VERSION OF THIS WAS A REPEATER, AND A REPEATER DOES NOT PULSE.** It delays both
    edges, so a held input gives a held output: measured against the simulator, a lever left on
    put the output high for 21 of 24 ticks against a contract promising two. Every casino game
    runs its button through here, so the house paid for as long as a player leaned on the button -
    the one failure a house must not have. It shipped because its own test asserted only that the
    output was high for FEWER than twenty ticks out of twenty, which a delay satisfies as easily
    as a pulse: **a test whose bound is looser than the bug passes vacuously.**

    What it is now is the standard AND-NOT, built out of what is already modelled:

        run     the input reaches the comparator's BACK immediately
        delay   and its SIDE through a repeater, `length` ticks later
        gate    a comparator in SUBTRACT mode

    Back minus side is the input while the side is still dark, and zero the moment it arrives -
    however long the input is held. This is the same shape as `window`, one axis down.

    CONTRACT: an input of ANY length, held or momentary, gives `out` high for about `length`
    ticks and then low; releasing and pressing again gives another pulse.
    """
    n = max(1, min(4, int(length)))
    dx, _dy, dz = STEP[facing]
    # WHICH SIDE THE DELAY LEG SITS ON IS THE CALLER'S CHOICE, for `window`'s reason: several of
    # these radiating from one machine collide otherwise.
    sx, sz = (-dz * side, -dx * side)
    x, y, z = pos

    def at(i, j):
        return (x + dx * i + sx * j, y, z + dz * i + sz * j)

    return {
        "cells": {
            at(0, 0): "redstone_wire",
            at(1, 0): "redstone_wire",
            at(2, 0): f"comparator[facing={facing},mode=subtract]",
            at(3, 0): "redstone_wire",
            # the delay leg, PERPENDICULAR, so it reaches the comparator's side input rather than
            # standing in the line it is supposed to be racing.
            at(0, 1): "redstone_wire",
            at(1, 1): f"repeater[facing={facing},delay={n}]",
            at(2, 1): "redstone_wire",
        },
        "in": at(-1, 0),
        "out": at(3, 0),
        "contract": f"input of ANY length, held or not -> about {n} ticks high, then low",
    }


# minecraft.wiki, Tutorial:Randomizers. THE DISTRIBUTION IS A PROPERTY OF THE ITEM MIX, not of
# the wiring, and it is the whole difference between a casino and a money leak:
#
#   2 outcomes, EQUAL   one stackable + one non-stackable        -> power 1 or 3
#   3 outcomes, EQUAL   one 64-stackable, one 16-stackable,
#                       one non-stackable                        -> power 1, 2 or 4
#
# and, quoting the same page, adding extras makes it LOPSIDED: "with two different stackable items
# and three different non-stackable items, the RNG will output power level 1 40% of the time and
# power level 3 60% of the time". So the recipe travels with the build and anything outside these
# two mixes is refused rather than guessed at.
RNG_MIXES = {
    2: {"items": ["a stackable item (e.g. cobblestone)", "a non-stackable item (e.g. a sword)"],
        "levels": [1, 3], "uniform": True},
    3: {"items": ["a 64-stackable item (e.g. cobblestone)", "a 16-stackable item (e.g. an egg)",
                  "a non-stackable item (e.g. a sword)"],
        "levels": [1, 2, 4], "uniform": True},
}


def randomiser(pos, outputs: int = 3, facing: str = "east") -> dict:
    """A dropper RNG with a KNOWN, UNIFORM distribution — 2 or 3 outcomes and nothing else.

    Deterministic redstone cannot make randomness; the entropy comes from a dropper choosing which
    of its stacks to eject, which the game does uniformly at random over the OCCUPIED SLOTS. That
    is why the item mix decides the odds and the wiring does not.

    **N IS RESTRICTED TO 2 AND 3 ON PURPOSE.** The earlier version took any N up to 8 and admitted
    it could not say what the odds were. For a slot machine that is not a caveat, it is a bug: a
    house that does not know its own odds cannot know whether it is losing money. Only the two
    mixes the wiki gives an equal-probability figure for are offered, and asking for more RAISES.

    CONTRACT: one comparator reads the dropper's hopper and outputs one of `levels`, each equally
    likely, once per trigger. The item mix is REQUIRED and is recorded in `stock`.
    """
    outputs = int(outputs)
    if outputs not in RNG_MIXES:
        raise ValueError(
            f"randomiser supports {sorted(RNG_MIXES)} outcomes with a KNOWN uniform distribution; "
            f"{outputs} would need an item mix whose odds nobody has measured. A casino that does "
            f"not know its odds is a casino that loses money.")
    mix = RNG_MIXES[outputs]
    x, y, z = pos
    # A COMPARATOR READS WHAT IS BEHIND IT, so the hopper must be at its BACK and it must FACE
    # the way its signal is going. Placed one step along `facing` from the hopper and pointed the
    # same way, that is automatic; placed by hand it was wrong first time, and the simulator caught
    # it as a machine that could never pay out.
    dx, dy, dz = STEP[facing][0], 0, STEP[facing][1]
    hop = (x, y - 1, z)
    cmp_ = (hop[0] + dx, hop[1], hop[2] + dz)
    cells = {
        (x, y, z): "dropper[facing=down]",
        hop: "hopper[facing=down]",
        cmp_: f"comparator[facing={facing},mode=compare]",
    }
    return {
        "cells": cells,
        "in": (x - dx, y, z - dz),
        "out": (cmp_[0] + dx, cmp_[1], cmp_[2] + dz),
        "comparator": cmp_,
        "hopper": hop,
        "dropper": (x, y, z),
        "levels": mix["levels"],
        "stock": mix["items"],
        "uniform": True,
        "note": RANDOM_NOTE,
        "contract": (f"{outputs} equally likely outcomes at power {mix['levels']}, "
                     f"one per trigger — REQUIRES exactly: " + "; ".join(mix["items"])),
    }


def payout(pos, count: int = 3, facing: str = "east") -> dict:
    """`count` droppers on one line, fired by a single rising edge.

    CONTRACT: one edge fires every dropper exactly once. A held signal fires them once, not
    continuously - which is the difference between paying a prize and emptying the bank.
    """
    count = max(1, min(16, int(count)))
    cells = {}
    for i in range(count):
        p = _off(pos, facing, i)
        cells[p] = "dropper[facing=up]"
        cells[(p[0], p[1] - 1, p[2])] = "redstone_wire"
    return {
        "cells": cells,
        "in": (pos[0], pos[1] - 1, pos[2]),
        "droppers": [_off(pos, facing, i) for i in range(count)],
        "contract": f"one rising edge fires all {count} droppers exactly once",
    }


def lamp_bank(pos, count: int = 5, facing: str = "east") -> dict:
    """`count` lamps driven together, for a sign or a floor.

    CONTRACT: all of them light from one input, and the LAST one lights - which is the assertion
    that catches a bank longer than 15 blocks with no repeater in it.
    """
    count = max(1, min(60, int(count)))
    cells = {}
    for i in range(count):
        p = _off(pos, facing, i)
        cells[p] = "redstone_lamp"
        wire = (p[0], p[1] - 1, p[2])
        # A REPEATER EVERY 15, because wire dies at 15 and a long sign is the commonest way to
        # discover that in game rather than here.
        cells[wire] = (f"repeater[facing={facing},delay=1]" if i and i % 14 == 0
                       else "redstone_wire")
    return {
        "cells": cells,
        "in": (pos[0], pos[1] - 1, pos[2]),
        "lamps": [_off(pos, facing, i) for i in range(count)],
        "last": _off(pos, facing, count - 1),
        "contract": f"one input lights all {count}, including the last",
    }


def connect(a, b, y: int | None = None, every: int = 14, facing: str = "east") -> dict:
    """A wire run from `a` to `b`, with a repeater before the signal would die.

    COMPOSING VERIFIED MODULES DOES NOT GIVE YOU A VERIFIED MACHINE. The casino's first slot
    machine was a correct pulse, a correct randomiser and a correct payout sitting near each other
    with nothing between them - and the circuit inspection said so on the first plan: "wire dies
    before the end", "dropper is not wired", "repeater drives nothing". Every module was fine and
    the machine did nothing.

    An L path, x first then z, because a straight line between two arbitrary points is not
    something a block grid has. A repeater every `every` cells because **wire dies at 15** and this
    is the one rule that turns a working bench test into a build that stops halfway.

    CONTRACT: the far end carries a signal when the near end does.
    """
    ax, ay, az = a
    bx, by, bz = b
    y = ay if y is None else y
    path = []
    step = 1 if bx >= ax else -1
    for x in range(ax, bx + step, step):
        path.append((x, y, az))
    step = 1 if bz >= az else -1
    for z in range(az + step, bz + step, step):
        path.append((bx, y, z))

    # THE ENDPOINTS ARE COMPONENTS, NOT WIRE. Emitting a cell at `a` or `b` overwrites the very
    # thing being connected: the casino's first wired slot replaced its own button and its own
    # payout dropper with redstone dust, and simulated as firing nothing at all. A connector runs
    # BETWEEN two things; it is not allowed to stand on either of them.
    # A HEIGHT DIFFERENCE IS NOT AN ERROR, IT IS A STAIRCASE.
    #
    # This function was planar and said so only in a docstring, and that ONE fact broke four
    # casino games in a row: the button sits on the floor, the machine sits seven courses down,
    # and every link between them ran happily along at the wrong height and delivered nothing.
    # Each failure looked like a different bug. It was always this.
    #
    # A caller should not have to know whether two points happen to share a Y. So when they do
    # not, the climb is done FIRST - it is a tested primitive - and the planar run continues from
    # the top of it.
    if ay != by:
        up = climb((ax, ay, az), (ax, by, az), facing=facing)
        rest = connect(up["top"], (bx, by, bz), y=by, every=every, facing=facing)
        cells = dict(up["cells"])
        for pos, spec in rest["cells"].items():
            cells.setdefault(pos, spec)
        laid_ = [q for q in cells if cells[q] != "smooth_stone"]
        return {"cells": cells,
                "from": up["foot"], "to": rest["to"],
                "ends": (tuple(a), tuple(b)), "length": len(laid_),
                "climbed": abs(by - ay),
                "contract": f"{abs(by - ay)} step(s) of climb then a planar run to the target"}

    ends = {tuple(a), tuple(b)}
    cells = {}
    facing_x = "east" if bx >= ax else "west"
    facing_z = "south" if bz >= az else "north"
    for i, pos in enumerate(path):
        if pos in ends:
            continue
        # A REPEATER AT THE CORNER WOULD POINT THE WRONG WAY. Only straight stretches get one,
        # and its facing comes from which leg it is on.
        if i and i % every == 0 and 0 < i < len(path) - 1:
            leg = facing_x if pos[2] == az and path[i + 1][2] == az else facing_z
            cells[pos] = f"repeater[facing={leg},delay=1]"
        else:
            cells[pos] = "redstone_wire"
    # `from`/`to` name the WIRE, not the components. The endpoints are skipped (a connector may
    # not stand on the thing it connects), so reporting `b` here would hand every caller a cell
    # this module never emitted - which is what broke its own test the moment the skip went in.
    laid = list(cells)
    return {"cells": cells,
            "from": laid[0] if laid else tuple(a),
            "to": laid[-1] if laid else tuple(b),
            "ends": (tuple(a), tuple(b)),
            "length": len(laid),
            "contract": f"{len(path)} cells; a repeater every {every} so the far end still fires"}


def bar(pos, lamps: int = 4, facing: str = "east") -> dict:
    """An ANALOG BAR: a run of dust with a lamp beside each cell, so a level reads as a length.

    Signal strength falls by one per block of dust, so a level of L reaches L cells and lights L
    lamps. That turns the randomiser's analog outcome into something a player can READ, with no
    level discriminator to build and nothing to get subtly wrong.

    **THE LAMP GOES BESIDE THE DUST, NOT ON TOP OF IT.** On the back wall it is diagonal from the
    run and nothing reaches it; that mistake cost a whole display in the first casino. Beside it,
    on the same course, is simply adjacent.

    CONTRACT: driving the foot at level L lights exactly the first L lamps and no others.
    """
    lamps = max(2, min(14, int(lamps)))
    dx, _dy, dz = STEP[facing]
    px, pz = -dz, -dx                                # sideways, for the lamp row
    x, y, z = pos
    cells, row = {}, []
    for i in range(lamps):
        c = (x + dx * i, y, z + dz * i)
        cells[c] = "redstone_wire"
        lamp = (c[0] + px, c[1], c[2] + pz)
        cells[lamp] = "redstone_lamp[lit=false]"
        row.append(lamp)
    return {"cells": cells, "in": (x - dx, y, z - dz), "foot": (x, y, z),
            "lamps": row, "length": lamps,
            "contract": f"level L lights the first L of {lamps} lamps"}


def boost(pos, facing: str = "east") -> dict:
    """A repeater that restores a dying signal to full strength - and DESTROYS its analog value.

    **AN ANALOG VALUE CANNOT TRAVEL.** This is the constraint the whole casino turned on and it is
    worth stating plainly: dust loses one per block, so a roll of 4 survives four blocks. Carrying
    it six courses up out of a machine pit consumes exactly the magnitude you were trying to show,
    and no amount of wiring fixes that - a repeater would carry it, but a repeater outputs 15 and
    the value is gone either way.

    So the rule is: **DECIDE IN THE PIT, AND SEND BOOLEANS UP.** Compare, threshold and choose
    where the machine is; then boost the yes/no and it travels as far as you like. That is exactly
    why `double_or_none` worked on the first try while three analog displays did not.

    CONTRACT: out is full strength whenever in carries anything at all.
    """
    dx, _dy, dz = STEP[facing]
    x, y, z = pos
    return {"cells": {(x, y, z): f"repeater[facing={facing},delay=1]"},
            "in": (x - dx, y, z - dz), "out": (x + dx, y, z + dz),
            "contract": "any signal in -> full strength out (the analog value is lost, on purpose)"}


def threshold(pos, level: int, facing: str = "east") -> dict:
    """Pass a signal ONLY when the incoming level is at least `level`.

    **DISTANCE IS THE THRESHOLD, AND IT IS ALREADY PROVEN.** Dust loses one per block, so a tap
    `level - 1` cells along a run carries something only when the signal was at least `level` to
    begin with. That is the same property `bar` reads as a length, used to gate instead of to
    display - which means this needs no new mechanism and inherits a contract that is already
    tested.

    The alternative was a per-lane subtract decoder, and it was tried: every lane needs its own
    threshold as an analog SIDE input, which needs another comparator chain per lane to produce.
    That is inventing a circuit, and this file's rule is that it does not.

    CONTRACT: `out` carries a signal when the input is >= `level`, and nothing when it is below.
    """
    level = max(1, min(15, int(level)))
    dx, _dy, dz = STEP[facing]
    x, y, z = pos
    cells = {}
    for i in range(level):
        cells[(x + dx * i, y, z + dz * i)] = "redstone_wire"
    return {"cells": cells, "in": (x - dx, y, z - dz), "foot": (x, y, z),
            "out": (x + dx * (level - 1), y, z + dz * (level - 1)),
            "level": level,
            "contract": f"passes only a level >= {level}"}


def climb(frm, to, block: str = "smooth_stone", facing: str = "east") -> dict:
    """A staircase of dust from one height to another.

    **`connect` IS PLANAR AND SAYS SO NOWHERE.** It lays an L path in X then Z at ONE height, so
    asked to join a machine six courses down to a display on the floor it quietly ran along the
    pit and never climbed - the comparator read 4, the bus read 0, and the board stayed dark on a
    build the inspection called clean. Dust climbs one block at a time, on a solid step, offset one
    along the run: that is what a vertical run IS, and it needed its own primitive.

    CONTRACT: a signal at the bottom reaches the top, with a repeater every `EVERY` steps because
    each step is a block of travel and wire still dies at 15.
    """
    fx, fy, fz = frm
    tx, ty, tz = to
    sx, _sy, sz = STEP[facing]          # STEP holds 3-tuples here, unlike casino's 2-tuples
    dx, dz = sx, sz
    cells = {}
    steps = abs(ty - fy)
    up = 1 if ty >= fy else -1
    x, y, z = fx, fy, fz

    # THE FIRST CELL MUST BE ADJACENT TO THE SOURCE, AT ITS OWN HEIGHT. The first version stepped
    # up AND along before placing anything, so its first dust was DIAGONAL from `frm` - and nothing
    # ever entered the staircase. It looked like a perfectly formed climb and carried no signal,
    # which is how it cost three attempts inside the casino before being tested on its own.
    #
    # THE LESSON IS THE TESTING ORDER, NOT THE GEOMETRY: this primitive was written and used in the
    # same breath. Every other module in this file had its contract asserted before anything was
    # built on it, and this one did not.
    x += dx
    z += dz
    cells[(x, y - 1, z)] = block
    cells[(x, y, z)] = "redstone_wire"
    for i in range(steps):
        y += up
        x += dx
        z += dz
        cells[(x, y - 1, z)] = block                 # the step to stand the dust on
        cells[(x, y, z)] = ("redstone_wire" if (i + 1) % 14 else
                            f"repeater[facing={facing},delay=1]")
    return {"cells": cells, "top": (x, y, z), "bottom": tuple(frm),
            "foot": (fx + dx, fy, fz + dz),
            "steps": steps,
            "contract": f"{steps} step(s) of climb; a repeater every 14 so the top still fires"}


MODULES = {
    "clock": clock,
    "latch": latch,
    "pulse": pulse,
    "randomiser": randomiser,
    "payout": payout,
    "lamp_bank": lamp_bank,
}
# `connect` is not a MODULE: it takes two points rather than one, so it cannot go through the
# same "build it at the origin and assert its contract" harness. It has its own tests.

def window(pos, low: int, high: int, facing: str = "east", side: int = 1) -> dict:
    """Pass a signal ONLY when the level is at least `low` and BELOW `high`. An exact-value gate.

    **THIS IS THE FIRST GAME MECHANIC HERE THAT IS NOT A MAXIMUM.** `threshold` pays on "roll high
    enough", which is the same game whatever number you put in it - and a measurement of the four
    games we shipped said so: High Roller and Coin Toss were 99.2% the same cells, One In Three and
    Even Money 97.8%. Two shapes wearing four names. Paying on ONE value is a different bet, with
    different odds, that a player reads differently.

    It is an AND-NOT and it is built out of what is already modelled rather than invented:

        run       one dust line off the source, so both taps see the SAME decaying signal
        tap LOW   a repeater beside the line at low-1, on when the level was >= low
        tap HIGH  a repeater beside the line at high-1, on when the level was >= high
        gate      a comparator in SUBTRACT mode, back = LOW, side = HIGH

    Subtract gives 15 - 0 = 15 when only LOW fired, and 15 - 15 = 0 when HIGH fired too. The taps
    are PERPENDICULAR because a repeater laid in the line would break the line it is measuring.

    CONTRACT: `out` carries a signal when low <= input < high, and nothing otherwise.
    """
    low = max(1, min(15, int(low)))
    high = max(low + 1, min(16, int(high)))
    dx, _dy, dz = STEP[facing]
    # **WHICH SIDE THE TAPS SIT ON IS THE CALLER'S CHOICE**, because three of these radiating from
    # one hopper collide otherwise: each occupies a 5x5 quadrant, and with the perpendicular fixed
    # two of them always land in the same one. The wheel's east and north gates overlapped exactly
    # this way and two pockets ended up in adjacent cells.
    sx, sz = (-dz * side, -dx * side)
    x, y, z = pos

    def at(i, j):
        return (x + dx * i + sx * j, y, z + dz * i + sz * j)

    cells = {}
    for i in range(high):                  # the line must reach the far tap
        cells[at(i, 0)] = "redstone_wire"

    # THE TAPS ARE PERPENDICULAR, because a repeater laid IN the line would break the line it is
    # measuring. Each reads the dust cell beside it and outputs a clean 15 when that cell is lit.
    face = _rev(facing, sx, sz)
    cells[at(low - 1, 1)] = f"repeater[facing={face},delay=1]"
    cells[at(high - 1, 1)] = f"repeater[facing={face},delay=1]"
    cells[at(low - 1, 2)] = "redstone_wire"
    cells[at(high - 1, 2)] = "redstone_wire"

    # THE GATE: back = LOW, side = HIGH. Written with both taps on one perpendicular the side
    # input landed TWO cells from the comparator and never arrived - the gate passed every level
    # at or above `low` and the window was just a threshold with extra parts. The HIGH boolean is
    # a full 15, so unlike the level it came from it CAN travel: it is routed along its own lane
    # to the gate's side.
    gate = at(low - 1, 3)
    cells[gate] = f"comparator[facing={face},mode=subtract]"
    # A SIDE INPUT IS READ AS A LEVEL, so it must arrive at FULL STRENGTH. Run as plain dust the
    # HIGH boolean decayed on the way and the subtract gave 15 - 13 = 2 instead of 0: the gate
    # "passed" a level it was built to block, quietly and by two. A repeater at the gate's side
    # delivers a clean 15, and 15 - 15 is the zero the contract promises.
    rev = {"east": "west", "west": "east", "north": "south", "south": "north"}[facing]
    for i in range(low + 1, high):
        cells[at(i, 3)] = "redstone_wire"
    side = at(low, 3)
    cells[side] = f"repeater[facing={rev},delay=1]"

    out = at(low - 1, 4)
    cells[out] = "redstone_wire"
    return {"cells": cells, "in": at(-1, 0), "foot": at(0, 0), "out": out,
            "low": low, "high": high,
            "contract": f"passes only {low} <= level < {high}"}


def _rev(facing, sx, sz):
    """The direction a perpendicular tap must FACE to read the line beside it."""
    if sx > 0:
        return "east"
    if sx < 0:
        return "west"
    return "south" if sz > 0 else "north"


def _perp_out(facing, sx, sz):
    return _rev(facing, sx, sz)


def duel(pos, facing: str = "east") -> dict:
    """Compare TWO rolls: pass when A is at least B. Two players' worth of luck in one machine.

    **AN ANALOG VALUE CANNOT TRAVEL, so both rolls have to be DECIDED where they are made.** That
    rule killed seven display attempts and it is what shapes this: the comparing comparator sits
    with roll A directly behind it and roll B directly beside it, and only the yes/no leaves.

    A comparator in COMPARE mode outputs its back signal when back >= side, and nothing otherwise.
    So with two uniform rolls out of the same mix the odds are exactly countable - for the
    three-outcome mix {1,2,4} there are 9 equally likely pairs and 6 of them have A >= B, which is
    2 in 3. **That is a game whose odds we can state**, which is this file's whole bar for shipping
    one.

    CONTRACT: `out` carries a signal when the back roll is >= the side roll.
    """
    dx, _dy, dz = STEP[facing]
    sx, sz = -dz, -dx
    x, y, z = pos
    cells = {
        (x, y, z): f"comparator[facing={facing},mode=compare]",
        (x + dx, y, z + dz): "redstone_wire",
    }
    return {"cells": cells,
            "back": (x - dx, y, z - dz),      # roll A goes here
            "side": (x + sx, y, z + sz),      # roll B goes here
            "out": (x + dx, y, z + dz),
            "contract": "passes when the back roll is at least the side roll"}

