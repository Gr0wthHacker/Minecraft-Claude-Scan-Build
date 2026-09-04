"""The arcade: redstone games a player PLAYS, not machines a player watches.

**THE PARK'S FIVE SIDESHOWS ARE ALL THE SAME SHAPE.** Press a button, a dropper RNG rolls, a
threshold or a window decides, a dropper pays. They differ in their odds and in their paint, and
in none of them does anything the player does change the outcome - you press, and then you read
what happened. That is a vending machine with suspense.

Every kind here turns a REAL PLAYER ACTION into a redstone signal. The circuit's job is to read
the player rather than to replace them:

    plinko        drop a ball; the channel it lands in pays that channel's prize
    range         shoot three targets at three distances; each scores on its own lamp ladder
    strength      hit the striker; the harder you hit, the higher it climbs, then a bell
    weigh         drop items on the scale until it reads EXACTLY the number on the sign
    reaction      a light runs along a row; press when it reaches the mark
    safe          three lectern dials, a hidden combination, an iron door onto the vault
    quiet         a corridor of sculk sensors; make a sound and the alarm shuts the far door
    prizecounter  where you spend what you won: barrels, prices, and a live IN STOCK lamp

**FIVE OF THEM ARE ANALOG, AND THAT IS WHAT THIS PROJECT HAS NEVER USED.** A `target` block emits
1..15 by how close to centre a projectile landed, a `light_weighted_pressure_plate` emits one
level per item standing on it, a `lectern`'s comparator reads the page you turned to, and a
`sculk_sensor` reads the strength of a vibration. Those are DIALS, not buttons - the player's aim,
count, choice and care arrive as a NUMBER, and three of the games show that number back as a
column of lamps you can read from across the midway. Everything the park had until now was a
button and a roll.

THE RULES THIS SUBSYSTEM RUNS UNDER, each of which has already cost this project a rebuild:

* **NOTHING SHIPS UNVERIFIED.** Every kind states a CONTRACT and `tests/test_arcade.py` asserts it
  by SIMULATION through `mcbuild.circuit`. Two finished casino games (`chase`, `vault`) were
  deleted for failing exactly this, and the park's credibility rests on the rule holding.
* **AN ANALOG VALUE CANNOT TRAVEL.** A level of 4 reaches four blocks of dust; a repeater carries
  it only by destroying it. So every analog decision here is made where the value still exists -
  at the comparator that read it - and only a BOOLEAN is ever routed anywhere. That rule killed
  seven display attempts in the casino and it shapes every layout below.
* **AN ENTITY IS AN INPUT YOU STATE.** The simulator has no entities: it cannot fire an arrow into
  a target, drop a ball into a hopper or turn a page. Every one of those is driven in the tests
  with `Circuit.fill`, which is the same mechanism and the same honesty the item sorter and the
  dropper randomiser already run under, and the entity half of each contract is listed in
  `unverified` rather than quietly assumed.
* **THE HOUSE MUST NOT BE ABLE TO LOSE BY ACCIDENT.** The casino pins a hazard where a stuck item
  in a hopper reads a winning level against an edge that never falls, and pays for ever. Every
  lane here puts `circuits.pulse` between the reading and the payout, so a held reading is ONE
  prize however long it is held - and `test_a_stuck_ball_pays_once_and_only_once` proves it.
* **A GAME NOBODY CAN WORK OUT HOW TO PLAY IS AN EMPTY STRUCTURE.** Every kind signs itself: what
  to do, and what it pays. Fifteen characters a line, checked rather than eyeballed.

**WHAT COULD NOT BE BUILT, stated rather than silently dropped.**

* **`item_frame` IS AN ENTITY, NOT A BLOCK.** `blocks.exists("item_frame")` is False, and it is
  false correctly: a frame lives in a region's Entities list, not in its block palette, so no
  litematic this pipeline writes can place one and no printer can build one. The eight-position
  rotation dial a frame would give is real and it is out of reach here - which is why `safe` uses
  LECTERNS, whose page number a comparator reads exactly the same way and which are blocks.
* **`chiseled_bookshelf`, `crafter`, `copper_bulb` and `calibrated_sculk_sensor` are 1.20/1.21
  blocks.** They pass `blocks.available()` only because the allowlist is provisional and cannot
  say no - rule 12, and the reason `pink_petals` once sailed through every check in this pipeline.
  None of them is used.
* **A "PICK THE LIT DOOR" GAME WAS BUILT AND IS NOT SHIPPED.** Three windows off one randomiser
  decoded correctly and three per-lane `and_gate`s verified on their own; what could not be laid
  was the routing between them - three L-routes out of a pit decoder into three separate gates,
  each crossing the others' lanes, with the decoder's outputs scattered around a hopper's three
  faces rather than on lanes of anybody's choosing. Every attempt produced two signals sharing a
  cell, which is one signal, which is a machine that pays for the wrong door. `reaction` carries
  the same mechanic - the machine's state AND the player's action - on a geometry that could be
  laid honestly. The ordering rule that finally worked for the `safe`'s three routes is written
  down there; the next attempt should start from it.
* **A PISTON-DRIVEN WHACK-A-MOLE IS NOT VERIFIABLE HERE**, and the reason is in `circuit.py`'s own
  docstring: anything driven by a MOVING block is invisible to a static model, and a target block
  that rides a piston head is not at the coordinate its comparator reads. The clock and the piston
  would verify; the game would not.

**THE EXPENSIVE PARTS ARE COUNTED, NOT SMUGGLED.** `redstone_lamp` is the only switchable light in
the game and it is `expensive` here, so it is the one thing that cannot be substituted by colour -
a dark block that looks like a lamp is a display that does not work. `build` counts every one into
`budget` so a plan can price them. A `bell` rings on a signal and costs nothing, so a chime is a
bell wherever a bell will do; `note_block` is expensive and is not used at all.

GEOMETRY is `gen/park.py`'s, unchanged, so an arcade unit sits in a zone exactly as a stall does:

    at       the structure's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out - a visitor stands in the +facing direction
    i        along the frontage      d   from the front INTO the building     h   courses up

and where a machine has to hide, it hides in a pit `pit` courses below the floor or in a service
void behind the back wall - exactly as the reference casino's does.
"""
from __future__ import annotations

from . import circuits, conceal
from .canvas import Canvas
from .park import LANDS, SIGN_WIDTH, _BACK, _STEP, _Frame, _hang_light, _pad, _sign
from .vertical import Ctx, World

# The i axis of `_Frame` as a NAMED world direction, so a circuit module can be pointed along the
# frontage. Derived from `_Frame`: (sx, sz) = (-dz, -dx). Asserted in the tests, not trusted here.
_SIDE = {"east": "north", "west": "south", "north": "east", "south": "west"}

ARCADE = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "plinko",
    "facing": "east",
    "land": "midway",
    "title": None,
    "lanes": 5,                 # plinko channels / prizecounter barrels
    "pit": 4,                   # how far under the play floor a hidden machine sits
    "board": 12,                # plinko: how tall the board is
    "rungs": 8,                 # strength: how many lamps the striker's column carries
    "score": 5,                 # range: how many lamps each lane's score ladder carries
    "win": 6,                   # range: how central a hit has to be to pay, 1..15
    "stages": 6,                # reaction: how many lamps the runner crosses
    "mark": 3,                  # reaction: which one is the mark (0-based)
    "combo": None,              # safe: the three dial values, 1..12. None = the default combo
    "sensors": 3,               # quiet: how many sculk sensors line the corridor
    "alarm": 4,                 # quiet: the vibration strength that trips it, 1..15
    "sign": True,
}
DEFAULTS = ARCADE           # the generator-module protocol's name for the same table


# ---------------------------------------------------------------------------- circuit primitives
#
# These have CONTRACTS in the same sense as `gen/circuits.py`'s, and `tests/test_arcade.py`
# asserts each one ALONE before any game is built on it. That ordering is the whole lesson of
# `circuits.climb`, which was written and used in the same breath, failed silently three times
# inside the casino, and gave up its bug the moment it was finally exercised by itself.
#
# They live here rather than in `circuits.py` because this file is their only caller.


def and_gate(pos, facing: str, side: str, inputs: int = 2) -> dict:
    """A AND B (AND C...), out of one torch per input and one more to invert the merge.

    **THE ONE GATE A SKILL GAME CANNOT DO WITHOUT.** Every kind here whose input is a CHOICE or a
    MOMENT has to ask two questions at once - is the machine offering this lane, AND did the player
    pick it; is the light on the mark, AND did the player press; are all three dials right at the
    same time. Redstone has no AND primitive, and a comparator cannot be one: COMPARE passes the
    back when back >= side, which is a threshold, and SUBTRACT is a difference. What redstone has
    is the inverter, and De Morgan does the rest:

        each input -> a solid block -> a torch  =  NOT input
        every torch -> ONE merged dust          =  NOT a OR NOT b OR ...
        that dust -> a block -> a torch         =  a AND b AND ...

    Two torch delays plus the merge, about three redstone ticks - far inside any window a human
    hand can aim at.

    **THE ODD PERPENDICULAR ROWS MUST STAY EMPTY**, and that is the whole reason this returns
    `keep_clear`. The input supports sit two apart so that a feed can power one without powering
    its neighbour; anything powered in the row between them powers BOTH and the gate silently
    becomes an OR. Nothing here writes those cells and nothing may be routed through them.

    **THE FEEDS ARRIVE FROM BEHIND, ALONG `facing`.** at(-1, 2k) is dust this module lays itself,
    so a caller's run can stop one short of it - `circuits.connect` never lays its own endpoints,
    and a gate whose feed cell was the endpoint of every run came out fed by nothing at all. The
    feeds are parallel lanes two apart, which is what lets three of them be routed with three
    straight runs and no crossing.

    CONTRACT: `out` carries a signal when EVERY input does, and nothing in any other case.
    """
    n = max(2, min(4, int(inputs)))
    fx, fz = _STEP[facing]
    px, pz = _STEP[side]

    def at(i, j):
        return (pos[0] + fx * i + px * j, pos[1], pos[2] + fz * i + pz * j)

    torch = f"redstone_wall_torch[facing={facing}]"
    cells, feeds = {}, []
    for k in range(n):
        j = 2 * k
        cells[at(-1, j)] = "redstone_wire"        # the feed cell, laid HERE - see the docstring
        cells[at(0, j)] = "smooth_stone"          # the support the feed weakly powers
        cells[at(1, j)] = torch                   # ...which the torch inverts
        feeds.append(at(-1, j))
    for j in range(0, 2 * n - 1):                 # the merge column: NOT a OR NOT b OR ...
        cells[at(2, j)] = "redstone_wire"
    cells[at(3, 0)] = "redstone_wire"
    cells[at(4, 0)] = "smooth_stone"
    cells[at(5, 0)] = torch                       # ...inverted once more, which is the AND
    cells[at(6, 0)] = "redstone_wire"

    clear = [at(-1, 2 * k + 1) for k in range(n - 1)]
    clear += [at(0, 2 * k + 1) for k in range(n - 1)]
    clear += [at(1, 2 * k + 1) for k in range(n - 1)]
    clear += [at(1, -1), at(1, 2 * n - 1)]
    return {"cells": cells, "feeds": feeds, "a": feeds[0], "b": feeds[1],
            "out": at(6, 0), "keep_clear": clear,
            "contract": f"out is high only when all {n} inputs are"}


def ladder(pos, rungs: int, facing: str, side: str, block: str = "smooth_stone") -> dict:
    """A VERTICAL analog bar: a dust staircase with a lamp beside every step.

    `circuits.bar` reads a level as a length along the ground, which is the right instrument for a
    slot machine and the wrong one for a fairground high striker or a score column, whose whole
    drama is HEIGHT. The physics is identical and free: dust loses one per block whether it runs
    sideways or climbs, so a hit of strength L dies L steps up and the puck stops where it stopped.

    **THERE IS NO REPEATER IN IT, AND THAT IS THE POINT.** `circuits.climb` puts one every 14 to
    keep a long run alive; here the decay IS the measurement, and a repeater would restore the
    signal to 15 and light the whole tower on any hit at all.

    CONTRACT: driving the foot at level L lights exactly the bottom min(L, rungs) lamps, and a
    signal that reaches `top` means L was at least `rungs` - which is what a bell is hung on.
    """
    rungs = max(2, min(15, int(rungs)))
    fx, fz = _STEP[facing]
    px, pz = _STEP[side]
    x, y, z = pos
    cells, lamps = {}, []
    for i in range(rungs):
        dust = (x + fx * i, y + i, z + fz * i)
        lamp = (dust[0] + px, dust[1], dust[2] + pz)
        cells[(dust[0], dust[1] - 1, dust[2])] = block
        cells[dust] = "redstone_wire"
        cells[(lamp[0], lamp[1] - 1, lamp[2])] = block
        cells[lamp] = "redstone_lamp[lit=false]"
        lamps.append(lamp)
    top = (x + fx * (rungs - 1), y + rungs - 1, z + fz * (rungs - 1))
    return {"cells": cells, "in": (x - fx, y, z - fz), "foot": (x, y, z),
            "lamps": lamps, "top": top, "rungs": rungs,
            "contract": f"level L lights the bottom L of {rungs} lamps; L >= {rungs} reaches the top"}


def clock(pos, facing: str, side: str, period: int = 4, block: str = "smooth_stone") -> dict:
    """A free-running clock, in the axes the CALLER chose rather than in the world's.

    `circuits.clock` is the one module in that file which its own docstring admits is not rotated
    by its `facing` at all - it always builds along +x and +z. Used inside a `_Frame`, that means
    its footprint and its output land somewhere different for every one of the four facings, and
    the reaction game ran perfectly facing east and not at all facing west, north or south. The
    topology is six blocks and rotating it properly is cheaper than working around it.

    A torch is lit until the block it is attached to is powered; its own output comes back through
    a repeater into that block and switches it off; a tick later the block is unpowered and the
    torch lights again. **THE LOOP MUST CLOSE ON THE SUPPORT, NOT ON THE TORCH** - a torch reads
    the block it stands on and nothing else, and the first version of `circuits.clock` pointed the
    repeater at the torch's own cell, emitted four tidy blocks, audited clean and never ticked.

    CONTRACT: `out` takes both states for ever with no input at all, and a larger `period` makes
    it change less often.
    """
    period = max(1, min(4, int(period)))
    fx, fz = _STEP[facing]
    px, pz = _STEP[side]

    def at(i, j):
        return (pos[0] + fx * i + px * j, pos[1], pos[2] + fz * i + pz * j)

    back = _BACK[side]
    return {"cells": {
        at(0, 0): block,
        at(1, 0): f"redstone_wall_torch[facing={facing}]",
        at(1, 1): "redstone_wire",
        at(1, 2): "redstone_wire",
        at(0, 2): "redstone_wire",
        at(0, 1): f"repeater[facing={back},delay={period}]",
    }, "out": at(1, 1), "support": at(0, 0),
        "contract": f"free-running, {period}-tick delay in the loop; never settles"}


def read_out(pos, facing: str) -> dict:
    """A comparator reading whatever is BEHIND it - the shape every reading in this file takes.

    A COMPARATOR READS WHAT IS BEHIND IT AND OUTPUTS WHERE IT FACES. Written the other way round
    the machine can never fire, it is legal and supported and affordable, and our renderer draws
    both directions identically - which is how the item sorter shipped backwards in every lane for
    months. So the relationship is arithmetic here rather than typed out at each of a dozen call
    sites.

    It reads a hopper's fullness, a lectern's page, a sculk sensor's vibration strength and a
    target block's hit strength with exactly the same three blocks, which is why one helper covers
    all four.

    CONTRACT: `out` carries the reading of whatever sits at `reads`, at its own strength.
    """
    fx, fz = _STEP[facing]
    x, y, z = pos
    return {"cells": {(x, y, z): f"comparator[facing={facing},mode=compare]"},
            "reads": (x - fx, y, z - fz), "out": (x + fx, y, z + fz),
            "contract": "passes the reading of whatever is at its back"}


# ---------------------------------------------------------------------------- placement helpers

def _split(spec: str):
    name = spec.split("[")[0]
    props = {}
    if "[" in spec and spec.endswith("]"):
        for part in spec[spec.index("[") + 1:-1].split(","):
            k, _, v = part.partition("=")
            props[k.strip()] = v.strip()
    return name, props


def _structural(pal: dict) -> set:
    """Fill a wire run may cut through. NOT a component: a link that overwrites a comparator is
    the bug that ate the first casino's own button and its own payout."""
    out = {pal[k] for k in ("ground", "path", "wall", "trim", "post", "beam", "slab", "stair")}
    out.add("smooth_stone")
    return out


def _lay(w: World, pal: dict, mods, floor: str | None = None) -> None:
    """Place a module's cells, never over a component, and give every wire cell a floor.

    **"SKIP ANYTHING ALREADY PLACED" IS NOT THE RULE, AND GETTING THAT WRONG COST THE CASINO FIVE
    COMPOSITION BUGS IN A ROW.** A game draws its structure first, so a run crossing a floor was
    swallowed cell by cell and the machine below was never joined to anything above it. Structure
    yields to wiring; wiring never yields to wiring.
    """
    keep = _structural(pal)
    floor = floor or pal["ground"]
    for mod in mods:
        for pos, spec in mod["cells"].items():
            if w.has(*pos) and w.name(*pos) not in keep:
                continue
            name, props = _split(spec)
            w.put(pos[0], pos[1], pos[2], name, **props)
        for pos, spec in mod["cells"].items():
            if spec.split("[")[0] in ("redstone_wire", "repeater", "comparator"):
                if not w.has(pos[0], pos[1] - 1, pos[2]):
                    w.put(pos[0], pos[1] - 1, pos[2], floor)


def _ij(f, world) -> tuple:
    """World cell -> the (i, d, h) it sits at in a `_Frame`'s own axes.

    The inverse of `_Frame.at`, and the reason it exists is that a circuit module returns WORLD
    coordinates: a `window`'s output lands wherever its own length put it, and a caller that wants
    to route from there in building axes must be able to ask rather than to re-derive the geometry
    by hand. Every hand-derived version of this in the first draft was wrong by a cell or two, and
    a route that is off by one cell is a route that connects nothing.
    """
    dx, dz = _STEP[f.facing]
    sx, sz = -dz, -dx
    ox, oz = world[0] - f.x, world[2] - f.z
    return (ox * sx + oz * sz, -(ox * dx + oz * dz), world[1] - f.y)


def _dirs(facing: str) -> dict:
    """The four building directions as world direction NAMES, once, so nothing derives them twice."""
    return {"in": _BACK[facing], "out": facing,
            "i+": _SIDE[facing], "i-": _BACK[_SIDE[facing]]}


def _line(w: World, pal: dict, f, a, b, h: int, floor: str | None = None) -> list:
    """A STRAIGHT dust run between two (i, d) points at one height, in BUILDING coordinates.

    **`circuits.connect` LAYS AN L IN WORLD AXES, AND THAT IS WHY IT IS NOT USED FOR ROUTING HERE.**
    Its corner lands wherever the world's x and z happen to put it, which on a machine built in
    building coordinates is a leg through the middle of something else: the first `safe` routed
    three booleans with it and two of them ran straight down the AND gate's own keep-clear column,
    powering both inverters at once and turning the gate into an OR. A run whose path a caller
    cannot predict cannot be kept out of anything.

    So this is deliberately dumber: one axis, both endpoints laid, a repeater every 14 because wire
    dies at 15 - and a repeater every TWELVE, not every fourteen, because a run is measured from
    wherever the signal ENTERED it and the entry is rarely a full 15: the safe's home lanes came in
    at 14 after their own corner and died two cells short of the gate.

    A caller lays its own corners, which means it knows exactly which cells it used.

    CONTRACT: the far end carries a signal when the near end does.
    """
    ai, ad = a
    bi, bd = b
    assert ai == bi or ad == bd, "a _line is straight - lay the corner yourself"
    keep = _structural(pal)
    floor = floor or pal["ground"]
    n = max(abs(bi - ai), abs(bd - ad))
    if ai == bi:
        step = (0, 1 if bd > ad else -1)
        dname = _dirs(f.facing)["in" if bd > ad else "out"]
    else:
        step = (1 if bi > ai else -1, 0)
        dname = _dirs(f.facing)["i+" if bi > ai else "i-"]
    laid = []
    for k in range(n + 1):
        i, d = ai + step[0] * k, ad + step[1] * k
        pos = f.at(i, d, h)
        if w.has(*pos) and w.name(*pos) not in keep:
            laid.append(pos)
            continue
        if k and k % 12 == 0 and 0 < k < n - 1:
            w.put(pos[0], pos[1], pos[2], "repeater", facing=dname, delay="1",
                  locked="false", powered="false")
        else:
            w.put(pos[0], pos[1], pos[2], "redstone_wire")
        if not w.has(pos[0], pos[1] - 1, pos[2]):
            w.put(pos[0], pos[1] - 1, pos[2], floor)
        laid.append(pos)
    return laid


def _run(w: World, pal: dict, f, pts, h: int, delay: int = 1) -> None:
    """A polyline of straight `_line` legs with a REPEATER STANDING ON EVERY CORNER.

    **A CORNER IS THE ONLY PLACE A REPEATER COSTS NOTHING, AND A LONG ROUTE NEEDS ONE.** Laid as
    plain dust, the reaction game's two routes were fourteen and twenty-five cells: the button's
    signal left its pulse at 13 and arrived at the gate at ZERO, so the machine could be pressed
    perfectly and never paid - and every cell of it was placed, legal and supported. A repeater at
    the bend restores 15 and points along the next leg, so distance stops being a constraint on
    where a gate may sit.

    It is only ever used on a BOOLEAN. A repeater outputs 15 whatever went in, which is exactly
    what must never happen to an analog reading - see the module docstring.

    CONTRACT: the far end carries a signal when the near end does, at any length.
    """
    D = _dirs(f.facing)
    # A ZERO-LENGTH LEG IS NOT A CORNER. Left in, `_run` puts a repeater one step past a bend that
    # does not exist, pointing at empty space - the reaction game's only circuit finding, and the
    # kind of leftover the inspection exists to catch.
    pts = [q for k, q in enumerate(pts) if k == 0 or q != pts[k - 1]]
    if len(pts) < 2:
        return
    for k in range(len(pts) - 1):
        _line(w, pal, f, pts[k], pts[k + 1], h)
    for k in range(1, len(pts) - 1):
        (i, d), (ni, nd) = pts[k], pts[k + 1]
        # **THE REPEATER GOES ONE CELL PAST THE CORNER, NEVER ON IT.** A repeater's back is
        # exactly opposite its front, so one standing ON a 90-degree bend reads the cell along its
        # OUTGOING axis and takes the incoming leg on its SIDE - which does not feed it, it LOCKS
        # it. Both of the reaction game's routes died at their first corner that way, and every
        # cell of them was placed, legal and supported. One step along the new leg, the corner
        # itself is dust and the repeater's back is that dust.
        if ni == i:
            name, step = (D["in"], (0, 1)) if nd > d else (D["out"], (0, -1))
        else:
            name, step = (D["i+"], (1, 0)) if ni > i else (D["i-"], (-1, 0))
        pos = f.at(i + step[0], d + step[1], h)
        w.put(pos[0], pos[1], pos[2], "repeater", facing=name, delay=str(delay),
              locked="false", powered="false")
        if not w.has(pos[0], pos[1] - 1, pos[2]):
            w.put(pos[0], pos[1] - 1, pos[2], pal["ground"])


def _pit_floor(w: World, f, pal: dict, i0: int, i1: int, d0: int, d1: int, h: int) -> None:
    """A floor for a hidden machine to stand on. The play floor above it is `_pad`'s, so the room
    is out of sight by construction."""
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if not w.has(*f.at(i, d, h)):
                w.put(*f.at(i, d, h), pal["ground"])


def _button(w: World, f, pal: dict, i: int, d: int, h: int, facing: str) -> tuple:
    """A floor button on a pad of the land's accent, so it reads as the thing to press."""
    b = f.at(i, d, h)
    w.put(b[0], b[1] - 1, b[2], pal["accent"])
    w.put(b[0], b[1], b[2], "stone_button", face="floor", facing=facing, powered="false")
    return b


def _award(w: World, pal: dict, src, facing: str, count: int = 1) -> dict:
    """The end of every paying lane: boost the reading, pulse it, and pay ONCE per reading.

    Laid as one straight chain along `facing` from `src`, so it needs no routing at all and its
    footprint is exactly `6 + count` cells long and three wide.

    **THE PULSE IS NOT DECORATION, IT IS THE HOUSE'S ONLY PROTECTION.** A hopper holding a ball
    reads a level for as long as the ball is in it, and a dropper wired to a held signal fires on
    the rising edge and then never again - which sounds safe until the ball is taken out and put
    back, or the hopper jams half-full. The casino pins that hazard in a test and does not fix it;
    here the reading becomes a fixed 2-tick pulse the moment it is read, so a held reading is one
    prize and a stuck ball is one prize.

    **`boost` FIRST**, because `pulse` passes its input's own LEVEL through: a hopper holding one
    item reads 1, and a pulse of 1 reaches exactly one block of dust and arrives nowhere.

    **AND THE PRIZE DROPPERS SIT ON TOP OF THE DUST, NOT BESIDE IT.** `circuits.payout` puts its
    feed one course BELOW its droppers, which is a diagonal from anything laid at the machine's own
    course and connects to nothing; a dropper directly above a lit dust cell is simply powered.

    CONTRACT: a reading of any strength at `src` fires each of `count` droppers exactly once, and
    a reading held for ever still fires them exactly once.
    """
    fx, fz = _STEP[facing]

    def on(k):
        return (src[0] + fx * k, src[1], src[2] + fz * k)

    amp = circuits.boost(on(1), facing=facing)
    pul = circuits.pulse(on(3), length=2, facing=facing)
    _lay(w, pal, (amp, pul))
    for cell in (src, on(2)):
        if not w.has(*cell):
            w.put(cell[0], cell[1], cell[2], "redstone_wire")
    drops = []
    for k in range(count):
        d = on(6 + k)
        if not w.has(*d):
            w.put(d[0], d[1], d[2], "redstone_wire")
            if not w.has(d[0], d[1] - 1, d[2]):
                w.put(d[0], d[1] - 1, d[2], pal["ground"])
        w.put(d[0], d[1] + 1, d[2], "dropper", facing="up", triggered="false")
        drops.append(d[0:1] + (d[1] + 1,) + d[2:])
    return {"boost": amp, "pulse": pul, "lit": on(2), "out": on(6),
            "droppers": [list(x) for x in drops], "length": 6 + count}


def _bell(w: World, pal: dict, near, facing: str) -> tuple | None:
    """A bell BESIDE a lit dust cell, on its own block - never standing on the dust itself.

    **A FLOOR BELL NEEDS A FLOOR, AND ALL THREE OF THEM WERE STANDING ON REDSTONE DUST.** The range,
    the high striker and the scale each hung their bell in the cell directly above the wire that
    rings it, with `attachment=floor` - a state the game will not place and a bell that pops the
    moment anyone loads the chunk. Three games' only audible output, and every check in this
    pipeline passed it: the state is legal, the block is cheap, the cell is supported by the
    generous reading of what a support is, and no render shows a bell falling off.

    A bell is rung by any redstone power reaching it, so BESIDE the dust on its own block rings
    exactly as well and is a bell that stays put. The first free horizontal neighbour is taken, so
    a caller does not have to know which way its own ladder ran.
    """
    for d in ("i+", "i-", "in", "out"):
        dx, dz = _STEP[_dirs(facing)[d]]
        cell = (near[0] + dx, near[1], near[2] + dz)
        under = (cell[0], cell[1] - 1, cell[2])
        if w.has(*cell):
            continue
        if not w.has(*under):
            w.put(under[0], under[1], under[2], pal["ground"])
        w.put(cell[0], cell[1], cell[2], "bell", attachment="floor",
              facing=facing, powered="false")
        return cell
    # **LOUD, NOT NONE.** A bell with nowhere to stand is a game with no audible output, and this
    # repo's own rule is that a thing which does nothing quietly is the worst outcome available.
    # Every kind here has four free neighbours at its ringing cell; if one ever does not, the
    # build should stop rather than ship a silent machine and a `None` in its own sidecar.
    raise ValueError(f"no free cell beside {near} to stand a bell on")


def _shell(w: World, f, pal: dict, width: int, depth: int, height: int,
           front_open: bool = True) -> None:
    """The ordinary fairground shell every kind wears: corner posts, a back wall, a roof beam.

    Deliberately plain. **WHAT MAKES VOXELS READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT
    DAMAGE** - the void tower settled it, the casino hall repeated it, and a game booth is the
    place least in need of novelty: the interesting thing in it is the game.
    """
    # **THE WALL STARTS AT THE STANDING COURSE, NOT ONE ABOVE IT.** Begun at h=1 the whole shell
    # floated one cell over its own pad - four kinds shipped in exactly two connected pieces, the
    # ground and the building, with zero placement problems reported because every cell had
    # something under it at its OWN course. A component count is the only check that sees this.
    for i in range(width):
        for h in range(0, height):
            w.put(*f.at(i, depth - 1, h), pal["wall"])
            if not front_open:
                w.put(*f.at(i, 0, h), pal["wall"])
    for d in range(depth):
        for h in range(0, height):
            w.put(*f.at(0, d, h), pal["post"])
            w.put(*f.at(width - 1, d, h), pal["post"])
    for i in range(-1, width + 1):
        for d in range(-1, depth + 1):
            w.put(*f.at(i, d, height), pal["beam"])
    # **AN OPEN FRONT HAS NOTHING TO HANG A SIGN ON**, which `park._stall`'s own docstring warns
    # about and which five kinds here shipped without: `_sign` refuses a cell with no block behind
    # it and returns False, so the name and the rules were SILENTLY not placed on a build that
    # audited clean. The fascia is the board a fairground booth's name goes on, and it is also
    # what makes a row of these read as a street rather than as sheds.
    if front_open:
        for i in range(width):
            w.put(*f.at(i, 0, height - 1), pal["trim"])


# ---------------------------------------------------------------------------- the games


def _plinko(w: World, p: dict, ctx) -> dict:
    """DROP A BALL. It rattles down through the pegs into one of the channels; that channel's
    hopper reads it and that channel's prize is paid.

    **THE BALL IS THE PLAYER'S PROBLEM, AND IT HAS TO BE.** No schematic can drop an entity and
    this simulator has none at all - so what gets built is a REAL PHYSICAL BOARD: a back wall, a
    lattice of staggered pegs in a one-block-deep play slot, a fence grille across the front so
    you can watch the ball and it cannot escape, dividers between the channels, and a hopper at
    the foot of each. Where the ball lands is decided by Minecraft, exactly as the dropper RNG's
    odds are, and that half of the contract travels in `unverified` rather than being assumed away.

    What IS verified is everything downstream of the landing: the hopper reads, its own lane pays
    its own number of prizes exactly once, and no other lane does anything at all.

    **THE CHANNELS ARE NOT WORTH THE SAME**, which is what turns an aimless drop into a bet: the
    outer channels pay three, the next pair two, the middle one. That is the real plinko curve -
    the outside is the hard place to land, so it is the good place to land - and the board's own
    peg lattice is what makes it hard.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    lanes = max(3, min(7, int(p["lanes"])) | 1)      # odd, so there is a middle
    board = max(8, min(20, int(p["board"])))
    width = lanes * 4 + 1
    mid = lanes // 2
    prizes = [min(3, 1 + abs(k - mid)) for k in range(lanes)]
    depth = 4 + 6 + max(prizes) + 2
    height = board + 3
    # **THE CHANNELS ARE FOUR APART, AND EVERY STEP OF THAT WAS PAID FOR.** At two, one lane's
    # perpendicular pulse leg lay directly beside the next lane's main run - adjacent dust is ONE
    # network, and the first build paid every channel on every ball while auditing perfectly clean.
    # At three the dust no longer touched, but the column between two chains is a pulse
    # comparator's own SIDE INPUT and it is live: a lid there bridges lane k's run into lane k+1's
    # gate, so the wiring could not be covered without re-making the very fault that spacing was
    # widened to fix. Four leaves a dead column between the chains, which can be capped, and a
    # wider divider is a better board as well.

    _pad(w, f, pal, width, depth, margin=1)

    # THE BOARD. d=2 is the back wall, d=1 the one-block play slot, d=0 the grille you watch
    # through. A solid front would be a cabinet; a fully open one lets the ball out.
    for i in range(width):
        for h in range(height):
            w.put(*f.at(i, 2, h), pal["wall"])
    for i in (0, width - 1):
        for h in range(height):
            w.put(*f.at(i, 1, h), pal["post"])
            w.put(*f.at(i, 0, h), pal["post"])
    for i in range(1, width - 1):
        for h in range(3, height - 1):
            w.put(*f.at(i, 0, h), pal["fence"], waterlogged="false")
    for i in range(width):
        w.put(*f.at(i, 0, height - 1), pal["trim"])
        w.put(*f.at(i, 1, height), pal["trim"])

    # THE PEGS, staggered so a ball never has a straight fall. Left out of the top courses (the
    # drop slot) and the bottom ones (the channel mouths).
    pegs = 0
    for h in range(4, board):
        for i in range(1, width - 1):
            if (i + h) % 2:
                continue
            w.put(*f.at(i, 1, h), pal["trim"])
            pegs += 1

    lane_i = [1 + k * 4 for k in range(lanes)]
    for i in range(0, width, 4):                     # the dividers between the channels
        for h in range(0, 3):
            w.put(*f.at(i, 1, h), pal["post"])

    reads, drops = [], []
    for k, i in enumerate(lane_i):
        hop = f.at(i, 1, 0)
        w.put(hop[0], hop[1], hop[2], "hopper", facing="down", enabled="true")
        w.put(*f.at(i, 1, -1), "barrel", facing="up", open="false")
        # The comparator sits INSIDE the back wall reading the hopper and firing into the machine
        # room behind the board, where the whole award chain is one straight line in its own lane.
        rd = read_out(f.at(i, 2, 0), D["in"])
        _lay(w, pal, (rd,))
        award = _award(w, pal, rd["out"], D["in"], count=prizes[k])
        reads.append(hop)
        drops.append(award["droppers"])

    _pit_floor(w, f, pal, -1, width, 3, depth, -1)
    title = str(p.get("title") or "PLINKO").upper()
    signed = _sign(w, f, pal, width // 2, -1, height - 1, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, width // 2 - 3, -1, height - 1, f.facing,
                    ["DROP A BALL IN", "at the top slot", "outside pays 3", "middle pays 1"])
    for i in (0, width - 1):
        _hang_light(w, f, pal, i, -1, height - 3)

    return {"kind": "plinko", "width": width, "depth": depth, "height": height + 1,
            "lanes": lanes, "pegs": pegs, "prizes": prizes,
            "hoppers": [list(h) for h in reads], "droppers": drops, "signed": signed,
            "inputs": [list(h) for h in reads],
            "outputs": [d for lane in drops for d in lane],
            "stock": {"each lane's droppers": "the prize that channel pays",
                      "the player": "a ball to drop - an egg, a snowball, any item"},
            "contract": (f"{lanes} channels; a ball read by channel k pays {prizes} prizes from "
                         f"that channel alone, exactly once per ball, and nothing from any other"),
            "unverified": ["WHERE THE BALL LANDS is Minecraft's item physics, which this "
                           "simulator has no entities to model. The board is real and the pegs "
                           "are staggered; the distribution is the game's own and must be watched "
                           "in world, exactly as the dropper randomiser's odds are."]}


def _range(w: World, p: dict, ctx) -> dict:
    """THE ARCHERY RANGE. Three target discs at three distances; each scores on its own column of
    lamps, and only the far one pays.

    **THE TARGET BLOCK IS THE ONLY GENUINELY ANALOG INPUT THIS PROJECT HAS EVER HAD.** It emits 1
    to 15 by how close the projectile landed to the centre, so the player's AIM arrives as a
    NUMBER rather than as a yes. Everything else in this park has been a button.

    That number obeys the rule the whole subsystem turns on - **AN ANALOG VALUE CANNOT TRAVEL** -
    so it is never routed anywhere. The comparator behind each disc feeds a `ladder` that starts
    at the comparator's own output cell, and the score column IS the decay: a hit of 5 lights five
    lamps because a level of 5 dies five blocks up. There is no discriminator, nothing to tune, and
    the whole reason it works is the one property of dust this project spent a year fighting.

    **AND THE SCORE IS THE REASON TO STAY.** A machine that pays and says nothing is a machine you
    use once; three columns of lamps that remember your last shot are something to beat.

    The far target pays, and it pays because its ladder is the tallest: reaching the top of a
    `score`-rung ladder needs a hit of at least `score`, and the far disc is the hard one to hit
    centrally at all. The bell hangs beside that top rung, so a full-score shot is heard across
    the midway.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    score = max(3, min(10, int(p["score"])))
    lanes = 3
    width = 13
    depth = 12
    height = score + 6

    _pad(w, f, pal, width, depth, margin=1)
    _shell(w, f, pal, width, depth, height)
    # THE FIRING LINE, in the accent, because a range with no mark is a room with holes in it.
    for i in range(1, width - 1):
        w.put(*f.at(i, 0, -1), pal["accent"])

    # Three butts at three depths, on their own i lanes. The lanes are four apart so a ladder
    # (which is two cells wide) and its comparator never meet the next lane's.
    spec = [(2, 4), (6, 7), (10, 10)]
    targets, ladders, bell = [], [], None
    for k, (i, d) in enumerate(spec):
        for h in range(1, 3):
            w.put(*f.at(i, d, h), pal["post"])
        for dd in (-1, 1):
            w.put(*f.at(i + dd, d, 3), pal["trim"])
        tgt = f.at(i, d, 3)
        w.put(tgt[0], tgt[1], tgt[2], "target", power="0")
        targets.append(tgt)

        # THE COMPARATOR BEHIND THE DISC, and the ladder starting on its own output cell. Nothing
        # is routed and nothing can decay on the way.
        rd = read_out(f.at(i, d + 1, 3), D["in"])
        _lay(w, pal, (rd,))
        lad = ladder(rd["out"], score, D["in"], D["i+"], block=pal["trim"])
        _lay(w, pal, (lad,))
        ladders.append(lad)

        if k == lanes - 1:
            # THE FAR LANE PAYS, and the bell is its threshold for free: it is beside the TOP rung,
            # so it rings exactly when the signal got all the way up - a full-score shot and
            # nothing less. A `bell` is cheap here; `note_block` is expensive and makes this the
            # one sound the park can afford.
            bell = _bell(w, pal, lad["top"], p["facing"])
            award = _award(w, pal, lad["top"], D["in"])
            drops = award["droppers"]

    _pit_floor(w, f, pal, -1, width, depth, depth + 12, -1)
    title = str(p.get("title") or "THE RANGE").upper()
    signed = _sign(w, f, pal, width // 2, -1, height - 1, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, width // 2 - 3, -1, height - 1, f.facing,
                    ["SHOOT A DISC", "centre = higher", f"all {score} lamps on", "far one pays"])
    for i in (0, width - 1):
        _hang_light(w, f, pal, i, -1, height - 2)

    return {"kind": "range", "width": width, "depth": depth, "height": height + score,
            "lanes": lanes, "score": score,
            "targets": [list(t) for t in targets],
            "lamps": [[list(l) for l in lad["lamps"]] for lad in ladders],
            "tops": [list(lad["top"]) for lad in ladders],
            "bell": list(bell), "droppers": drops, "signed": signed,
            "inputs": [list(t) for t in targets],
            "outputs": [list(bell)] + drops,
            "stock": {"the dropper": "the prize a full-score shot on the far disc pays",
                      "the player": "arrows, or anything that hits a target block"},
            "contract": (f"three discs; a hit of strength L on disc k lights the bottom L of that "
                         f"disc's {score} lamps and no other disc's, and only a hit of {score} or "
                         f"more on the FAR disc rings the bell and pays, once"),
            "unverified": ["A TARGET'S OUTPUT IS AN INPUT YOU STATE. The simulator has no "
                           "entities and cannot fire an arrow; that a bullseye really reads 15 "
                           "and a rim hit really reads 1 is the game's own behaviour."]}


def _strength(w: World, p: dict, ctx) -> dict:
    """THE HIGH STRIKER. Hit the pad; the harder you hit, the higher the column climbs; a maximum
    rings the bell at the top and pays.

    Same physics as `range`'s score columns and a completely different game: there is no aim in
    it, no distance, and one column rather than three. What it is for is the fairground's oldest
    dare - hit it as hard as you can, in front of everybody - and it is the tallest thing on the
    midway, which is what makes it worth walking over to.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    rungs = max(4, min(14, int(p["rungs"])))
    # **A DUST STAIRCASE CLIMBS DIAGONALLY, SO THE TOWER LEANS**, and the footprint has to admit
    # it: one cell of run per course is what a redstone staircase IS, and pretending otherwise is
    # how `circuits.connect` broke four casino games in a row.
    width = rungs + 5
    depth = 5
    height = rungs + 4

    _pad(w, f, pal, width, depth, margin=1)
    for h in range(0, height):
        w.put(*f.at(0, 3, h), pal["post"])
    for i in range(width):
        w.put(*f.at(i, 3, 0), pal["trim"])
        w.put(*f.at(i, 3, 1), pal["wall"])
    # THE FRONT FRAME: two posts and a board across them. It is what the striker's two signs hang
    # on, and without it `_sign` refuses both and says nothing.
    for h in range(0, 5):
        w.put(*f.at(0, 0, h), pal["post"])
        w.put(*f.at(width - 1, 0, h), pal["post"])
    for i in range(width):
        w.put(*f.at(i, 0, 4), pal["trim"])

    # **THE COMPARATOR SITS BESIDE THE DISC, NOT BEHIND IT, AND THE LADDER STARTS ON ITS OWN
    # OUTPUT CELL.** Behind the disc, the ladder's foot had to be nudged one cell along to keep the
    # first lamp off the comparator - and a cell of dust costs a LEVEL, so an eight-rung tower
    # needed a hit of nine to ring. The reading has to enter the ladder at full strength or the
    # instrument is lying about what it measured. Beside it, both problems go away at once.
    tgt = f.at(2, 3, 2)
    w.put(tgt[0], tgt[1], tgt[2], "target", power="0")
    rd = read_out(f.at(3, 3, 2), D["i+"])
    _lay(w, pal, (rd,))

    # THE TOWER climbs along the frontage, so the lamps face the midway rather than the back of
    # the machine - which is where every one of them would be if it climbed inward.
    lad = ladder(rd["out"], rungs, D["i+"], D["out"], block=pal["trim"])
    _lay(w, pal, (lad,))
    bell = _bell(w, pal, lad["top"], p["facing"])
    # THE AWARD RUNS INWARD, NOT ON UP THE FRONTAGE. Laid along the ladder's own axis it put the
    # pulse's comparator exactly on the TOP LAMP - and every test still passed, because
    # `Circuit.powered` answers for a coordinate and does not care what block is standing there.
    # A lamp that has been quietly replaced by a comparator is lit in the simulator and dark in
    # the game, which is this project's oldest failure shape wearing a new hat.
    award = _award(w, pal, lad["top"], D["in"])

    title = str(p.get("title") or "STRIKER").upper()
    signed = _sign(w, f, pal, 2, -1, 4, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, 5, -1, 4, f.facing,
                    ["HIT THE DISC", "harder = higher", f"light all {rungs}", "rings the bell"])

    return {"kind": "strength", "width": width, "depth": depth, "height": height + rungs,
            "rungs": rungs, "target": list(tgt), "bell": list(bell),
            "lamps": [list(l) for l in lad["lamps"]], "top": list(lad["top"]),
            "droppers": award["droppers"], "signed": signed,
            "inputs": [list(tgt)], "outputs": [list(bell)] + award["droppers"],
            "stock": {"the dropper": "the prize a maximum hit pays"},
            "contract": (f"a hit of strength L lights the bottom L of {rungs} lamps; only "
                         f"L >= {rungs} reaches the bell, and only that pays, once"),
            "unverified": ["A TARGET'S OUTPUT IS AN INPUT YOU STATE - the simulator has no "
                           "entities and cannot swing at it."]}


def _reaction(w: World, p: dict, ctx) -> dict:
    """A LIGHT RUNS ALONG THE ROW. PRESS WHEN IT REACHES THE MARK.

    **THE ONLY GAME HERE THAT IS PURE TIMING**, and the only one whose input is a MOMENT rather
    than a place. A clock launches a pulse into a chain of repeaters; each stage drives its own
    lamp, so a single point of light walks the row and comes round again. One stage is the MARK,
    painted in the land's accent, and its line is one input of an `and_gate` whose other input is
    the player's button.

    Press early and the gate sees your pulse alone; press late and it sees the mark alone; press
    right and both are high together. There is nothing random in it at all - which after five
    randomiser games is the point.

    **A ONE-TICK PULSE IS SWALLOWED BY A DELAY-ONE REPEATER**, in this model and in the game's own
    scheduler alike, so the runner is launched through `circuits.pulse` at length 3 and each stage
    is a delay-2 repeater - **a repeater of delay N needs N+1 ticks of input**, and at delay 3 the
    chain swallowed the runner whole and the row stayed dark on a build where every block was
    legal, supported and correctly wired. What is left is also a window wide enough for a human
    hand rather than for a test harness.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    pit = max(3, int(p["pit"]))
    stages = max(4, min(10, int(p["stages"])))
    mark = max(1, min(stages - 2, int(p["mark"])))
    width = stages * 2 + 3
    depth = 6
    height = 6
    my = -pit
    row = 2                                  # the d the runner's lamps sit at
    # THE BACK LANES, and the ORDER between them is the whole layout. Two signals have to meet at
    # one gate, and the only way to lay two L-routes that never touch is to give each its own
    # CROSS band and to make the later cross stop short of the earlier one's home lane. So: the
    # button crosses first at `bd`, on the far lane; the mark crosses second at `md`, on the near
    # one; and the gate's two feeds are two apart, which is why `and_gate`'s feeds are.
    gi = -6                                  # the gate's own lane, clear of the clock and the row
    gd = depth + 12
    bd = 12                                  # the button's cross band
    md = 15                                  # the mark's cross band, which must be the LATER one

    _pad(w, f, pal, width, depth, margin=1)
    _shell(w, f, pal, width, depth, height)
    _pit_floor(w, f, pal, gi - 2, width + 2, -2, gd + 10, my - 1)

    # THE CLOCK, and a pulse so what enters the chain is a travelling POINT rather than a square
    # wave - a square wave lights half the row at once, which is a band and not a runner.
    clk = clock(f.at(-4, row, my), D["i+"], D["in"], period=4, block=pal["ground"])
    _lay(w, pal, (clk,))
    launch = circuits.pulse(f.at(-2, row, my), length=3, facing=D["i+"])
    _lay(w, pal, (launch,))
    # **THE CLOCK IS BUILT IN THE BUILDING'S OWN AXES, WHICH `circuits.clock` CANNOT DO.** Used
    # from there it landed in a different set of cells for every facing: the row ran perfectly
    # facing east and not at all facing west, north or south, and no test that only built the
    # default facing would ever have seen it. Local `clock` rotates properly, so its output is one
    # straight run from the launch whichever way the booth is turned.
    ci, cd, _ = _ij(f, clk["out"])
    _run(w, pal, f, [(ci, cd), (ci, row), (-3, row)], my)

    # THE CHAIN, running along the frontage under the floor, each stage's lamp set INTO the counter
    # directly above its own dust - a lit floor panel, and no journey at all.
    lamps, taps = [], []
    for k in range(stages):
        rep = f.at(2 + k * 2, row, my)
        dust = f.at(3 + k * 2, row, my)
        # **A REPEATER OF DELAY N NEEDS N+1 TICKS OF INPUT.** At delay 3 against a 3-tick pulse
        # the chain swallowed the runner whole: the first repeater's countdown was reset by the
        # input falling before it expired, so lamp 0 never lit and the row was dark for ever
        # while every block in it was legal, supported and correctly wired. Delay 2 against a
        # 4-tick launch has a tick of margin, and still holds each lamp long enough to aim at.
        w.put(rep[0], rep[1], rep[2], "repeater", facing=D["i+"], delay="2",
              locked="false", powered="false")
        w.put(dust[0], dust[1], dust[2], "redstone_wire")
        lamp = (dust[0], dust[1] + 1, dust[2])
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        lamps.append(lamp)
        taps.append((3 + k * 2, row))
    _line(w, pal, f, (1, row), (1, row), my)

    # THE ROW THE PLAYER SEES: a shaft of the land's own stone over each lamp, with the MARK in
    # the accent. The lamps are a course under the floor, so the shaft is what carries the light
    # up to where it can be watched.
    for k in range(stages):
        i = 3 + k * 2
        # UP TO AND INCLUDING THE STANDING COURSE. Stopping at h=-1 left the accent square at h=1
        # hanging over a one-cell gap - five single-cell strays, one per stage, in a design with
        # zero placement problems.
        for h in range(my + 2, 1):
            w.put(*f.at(i, row, h), pal["ground"])
        w.put(*f.at(i, row, 1), pal["accent"] if k == mark else pal["trim"])

    # THE BUTTON, on the far left so its route never has to cross the runner's own lamps.
    btn = _button(w, f, pal, 1, 1, 0, f.facing)
    bdown = circuits.climb(btn, (btn[0], f.at(0, 0, my)[1], btn[2]),
                           block=pal["ground"], facing=D["in"])
    _lay(w, pal, (bdown,))
    bi, bdd, _ = _ij(f, bdown["top"])
    bp = circuits.pulse(f.at(bi, bdd + 1, my), length=4, facing=D["in"])
    _lay(w, pal, (bp,))
    if not w.has(*bp["in"]):
        w.put(bp["in"][0], bp["in"][1], bp["in"][2], "redstone_wire")
    pi, pd, _ = _ij(f, bp["out"])

    ag = and_gate(f.at(gi, gd, my), D["in"], D["i+"])
    _lay(w, pal, (ag,))
    # the player's press: down its own lane, across at `bd`, home on the gate's FIRST feed.
    _run(w, pal, f, [(pi, pd), (pi, bd), (gi, bd), (gi, gd - 1)], my)
    # the mark's own line: down its lane, across at `md`, home on the SECOND feed - which stops
    # two short of the button's lane, so the two crosses can never share a cell.
    _run(w, pal, f, [taps[mark], (taps[mark][0], md), (gi + 2, md), (gi + 2, gd - 1)], my,
         delay=MARK_DELAY)
    # **A TORCH GATE PAYS ONCE THE MOMENT IT IS BUILT, AND THAT IS A REAL PRIZE OUT OF THE BANK.**
    # Every torch in the gate starts LIT, so for the two ticks before the inverters settle the
    # output is high - measured at exactly 2 ticks here, and it happens again on every chunk load.
    # A winning press holds the gate for 4. A delay-2 repeater needs THREE consecutive ticks to
    # switch, so it swallows the startup glitch whole and passes a genuine win untouched: the
    # cheapest possible filter, and it exists because the house must not be able to lose by
    # accident. `test_the_reaction_game_pays_nothing_when_it_is_first_built` pins it.
    gx, gz = _STEP[D["in"]]
    guard = (ag["out"][0] + gx, ag["out"][1], ag["out"][2] + gz)
    w.put(guard[0], guard[1], guard[2], "repeater", facing=D["in"], delay="2",
          locked="false", powered="false")
    if not w.has(guard[0], guard[1] - 1, guard[2]):
        w.put(guard[0], guard[1] - 1, guard[2], pal["ground"])
    award = _award(w, pal, (guard[0] + gx, guard[1], guard[2] + gz), D["in"])

    title = str(p.get("title") or "REACTION").upper()
    signed = _sign(w, f, pal, width // 2, -1, height - 1, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, width // 2 - 3, -1, height - 1, f.facing,
                    ["WATCH THE LIGHT", "press when it", "hits the bright", "square: no luck"])
    for i in (0, width - 1):
        _hang_light(w, f, pal, i, -1, height - 2)

    return {"kind": "reaction", "width": width, "depth": depth, "height": height + 1,
            "stages": stages, "mark": mark,
            "lamps": [list(l) for l in lamps],
            "taps": [list(f.at(i, d, my)) for (i, d) in taps],
            "button": list(btn), "droppers": award["droppers"], "signed": signed,
            "inputs": [list(btn)],
            "outputs": [list(l) for l in lamps] + award["droppers"],
            "stock": {"the dropper": "the prize a correct press pays"},
            "contract": (f"a light walks {stages} lamps for ever; pressing while lamp {mark} is "
                         f"lit pays once, and pressing while it is dark pays nothing"),
            "unverified": []}


def _weigh(w: World, p: dict, ctx) -> dict:
    """GUESS THE WEIGHT. Drop items on the scale until it reads EXACTLY the number on the sign.

    **THE ONE GAME HERE THAT IS NEITHER LUCK NOR REFLEX.** A `light_weighted_pressure_plate` emits
    one level per item standing on it, so the plate is a SCALE and the player's input is a count
    they build up by hand: drop one too many and the reading goes past the mark and stops paying,
    which is the whole tension. Nothing about it is hidden and nothing about it is fast.

    Two comparators read the ONE plate from two sides, which is the wheel's trick and the only way
    to do it: **A SPUR OFF ONE COMPARATOR'S OUTPUT IS ALREADY A LEVEL DOWN** and the two consumers
    would then disagree about what the scale says. A plate has four horizontal neighbours; two of
    them read it at full strength.

    * the SCALE side drives a `ladder` - the live readout the player watches climb;
    * the JUDGE side drives a `circuits.window`, which passes one exact value and nothing else. A
      `threshold` would pay for anything heavier, which is not a guessing game, it is a shelf.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    rungs = max(4, min(14, int(p["rungs"])))
    target = max(2, min(rungs, int(p["win"])))
    ci = 6
    width = ci + 3 + rungs
    depth = 8 + target
    height = 6

    _pad(w, f, pal, width, depth, margin=1)
    _shell(w, f, pal, width, depth, height)

    # THE SCALE ITSELF, on a plinth at counter height so it is somewhere to put things rather than
    # something to tread on. A plate needs a full block under it, which the plinth is.
    w.put(*f.at(ci, 2, 0), pal["trim"])
    plate = f.at(ci, 2, 1)
    w.put(plate[0], plate[1], plate[2], "light_weighted_pressure_plate", power="0")
    for dd in (1, 3):
        w.put(*f.at(ci, dd, 0), pal["trim"])

    # THE READOUT: a comparator on one side of the plate, and the ladder climbing straight off it.
    scale = read_out(f.at(ci + 1, 2, 1), D["i+"])
    _lay(w, pal, (scale,))
    lad = ladder(scale["out"], rungs, D["i+"], D["out"], block=pal["trim"])
    _lay(w, pal, (lad,))

    # THE JUDGE: a second comparator on the other side, into a window that passes ONE value.
    judge = read_out(f.at(ci, 3, 1), D["in"])
    _lay(w, pal, (judge,))
    gate = circuits.window(judge["out"], target, target + 1, facing=D["in"], side=1)
    _lay(w, pal, (gate,))
    # **`next`, NOT ONE STEP ALONG THE RUN.** One step along is the cell beside the gate's own
    # SIDE input, which carries the HIGH boolean at a full 15 - so anything put there reads the
    # very signal the gate exists to reject, and "stop at exactly N" quietly becomes "anything at
    # or over N", which is the shelf this game's own docstring says it is not.
    amp = circuits.boost(gate["next"], facing=gate["face"])
    _lay(w, pal, (amp,))
    award = _award(w, pal, amp["out"], D["in"])
    # A BELL RATHER THAN A LAMP: it costs nothing on this economy, it is heard from the aisle, and
    # a lamp here would be one more expensive block in a machine that already carries a ladder.
    bell = _bell(w, pal, award["lit"], p["facing"])

    _pit_floor(w, f, pal, -1, width, depth, depth + 14, -1)
    title = str(p.get("title") or "THE SCALE").upper()
    signed = _sign(w, f, pal, width // 2, -1, height - 1, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, width // 2 - 3, -1, height - 1, f.facing,
                    ["DROP ITEMS ON", "the gold plate", f"stop at {target}", "one over: lose"])
    for i in (0, width - 1):
        _hang_light(w, f, pal, i, -1, height - 2)

    return {"kind": "weigh", "width": width, "depth": depth, "height": height + rungs,
            "rungs": rungs, "target": target, "plate": list(plate),
            "lamps": [list(l) for l in lad["lamps"]], "bell": list(bell),
            "droppers": award["droppers"], "signed": signed,
            "inputs": [list(plate)], "outputs": [list(bell)] + award["droppers"],
            "stock": {"the dropper": "the prize an exact reading pays",
                      "the player": "items to weigh - one level per item on a gold plate"},
            "contract": (f"the ladder shows the plate's reading as a height; the bell rings and "
                         f"the prize drops ONLY on exactly {target}, once, and never on "
                         f"{target - 1} or {target + 1}"),
            "unverified": ["HOW MANY ITEMS MAKE A LEVEL is the game's own table - one per item on "
                           "a gold plate, ten on an iron one. The simulator has no entities and "
                           "cannot put anything down."]}


# **THE PRESS HAS FURTHER TO GO THAN THE MARK DOES, AND THE SIGN WOULD HAVE LIED ABOUT IT.**
# A press travels a button, a climb, a monostable and two corners before it reaches the gate; the
# mark's own line travels two corners. Left alone the machine paid for a press made SIX TICKS
# BEFORE the light arrived - it worked perfectly and rewarded the opposite of what it told you to
# do, which for a skill game is worse than not working at all. The MARK's corner repeaters carry
# the difference, because delaying the button moves the winning press earlier and delaying the
# mark moves it later. Calibrated by simulation in `tests/test_arcade.py`, which asserts that a
# press made WHILE THE MARK IS LIT is the one that pays.
MARK_DELAY = 3


# THE SAFE'S DEFAULT COMBINATION. Small values on purpose - a `window` is `high` cells of dust
# long, so a dial of 12 is a twelve-block run and a building four blocks deeper. Ascending, because
# the routing depends on it: see `_safe`.
SAFE_COMBO = (3, 5, 8)


def _safe(w: World, p: dict, ctx) -> dict:
    """CRACK THE SAFE. Three lectern dials, a hidden combination, and an iron door onto the vault.

    **A PUZZLE, NOT A BET.** Nothing in it is random and nothing in it is timed: three numbers are
    either right or they are not, and a player who watches somebody else win learns the answer -
    which is exactly what makes a crowd stand around it. It is the only attraction here that gets
    HARDER to keep interesting rather than easier, and the combination is one line of config.

    **THE DIAL IS A LECTERN BECAUSE AN ITEM FRAME IS AN ENTITY.** A frame's eight rotations are
    the classic Minecraft combination lock, and `blocks.exists("item_frame")` is False - correctly:
    a frame lives in a region's Entities list, not in its block palette, so nothing this pipeline
    writes can place one. A lectern is a BLOCK, its comparator reads the page you turned to, and
    turning a page is exactly the gesture a dial wants.

    THE LAYOUT IS THE HARD PART AND IT IS DECIDED BY THREE FACTS:

    * a `window` is `high` cells long along the run and five wide across it, so the three dials are
      six apart on the frontage and their gates never share a cell;
    * **the combination is SORTED ASCENDING**, so dial 0's gate ends nearest the front and dial 2's
      furthest back - which is what stops any dial's cross run from crossing another's home run;
    * every boolean is boosted where it is decided, because a `window` whose high is its low plus
      one outputs 1 rather than 15 (its two taps are adjacent and the low tap leaks into the gate's
      side), and a level of 1 reaches exactly one block.

    The three booleans then run in three parallel lanes into one three-input `and_gate`, whose
    output opens the door. Nothing else opens it.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    combo = tuple(sorted(int(v) for v in (p.get("combo") or SAFE_COMBO)))
    if len(combo) != 3 or not all(1 <= v <= 12 for v in combo) or len(set(combo)) != 3:
        raise ValueError("safe needs three DISTINCT dial values between 1 and 12")
    dial_i = [5, 11, 17]
    # **THE GATE SITS PAST EVERY WINDOW BAND, AND THAT IS FORCED.** A `window` is five cells wide
    # across its own run, so dial k's gate fills the whole band i = dial_i[k]-4 .. dial_i[k]: 1-5,
    # 7-11, 13-17. The first version put the three home lanes at 1, 3 and 5 - which is what the AND
    # gate's own feed spacing suggested - and every one of them ran straight down the middle of a
    # window. The safe opened for nothing at all, and the reason was invisible in every render.
    gate_i = 19
    width = 25
    cross = combo[-1] + 8            # the first cross band, past every boost
    gate_d = cross + 12
    depth = gate_d + 12
    height = 6

    _pad(w, f, pal, width, depth, margin=1)
    _shell(w, f, pal, width, 4, height)          # the LOBBY: the only part a player stands in
    for i in range(width):
        for h in range(1, height):
            w.put(*f.at(i, 3, h), pal["wall"])   # the machine room is walled off behind it
    for i in range(-1, width + 1):
        for d in range(-1, depth + 1):
            w.put(*f.at(i, d, height), pal["beam"])

    outs = []
    for k, (i, v) in enumerate(zip(dial_i, combo)):
        w.put(*f.at(i, 2, 0), pal["trim"])
        lec = f.at(i, 2, 1)
        w.put(lec[0], lec[1], lec[2], "lectern", facing=p["facing"],
              has_book="true", powered="false")
        rd = read_out(f.at(i, 3, 1), D["in"])
        _lay(w, pal, (rd,))
        gate = circuits.window(rd["out"], v, v + 1, facing=D["in"], side=1)
        _lay(w, pal, (gate,))
        # BOOSTED WHERE IT IS DECIDED. The window's own out is a level of 1; one block later it is
        # a 15 that may be routed anywhere at all.
        amp = circuits.boost(gate["next"], facing=gate["face"])
        _lay(w, pal, (amp,))
        outs.append(_ij(f, amp["out"])[:2])       # (i, d) of the boosted boolean, ASKED not guessed

    ag = and_gate(f.at(gate_i, gate_d, 1), D["in"], D["i+"], inputs=3)
    _lay(w, pal, (ag,))
    # **THE LONGEST CROSS GOES LAST, AND THAT ORDERING IS THE WHOLE ROUTING.** Three L-routes into
    # one gate cross each other unless each one's sideways leg is at a depth the others have
    # already left. Lane 2 has the shortest reach to the gate, so it crosses nearest; lane 0 has
    # the longest, so it crosses furthest back, by which point the other two are already running
    # home in columns its leg never reaches. Every other assignment produces two lines sharing a
    # cell, which is one signal, which is a safe that opens on one dial.
    for k, (oi, od) in enumerate(outs):
        cross_d = cross + (len(outs) - 1 - k) * 2
        _run(w, pal, f, [(oi, od), (oi, cross_d), (gate_i + 2 * k, cross_d),
                         (gate_i + 2 * k, gate_d - 1)], 1)

    # THE DOOR, and the vault behind it. It is in the machine room's own far wall on lane 0, so
    # the boolean has nowhere to travel and nothing can open it but the gate.
    door = f.at(gate_i, gate_d + 8, 1)
    # **A TORCH GATE IS HIGH FOR TWO TICKS THE MOMENT IT IS BUILT**, because every torch in it
    # starts lit and the inverters take a tick each to settle - so the door flicked open on every
    # chunk load. A delay-2 repeater needs THREE consecutive ticks to switch and swallows that
    # glitch whole, while a solved combination holds the gate indefinitely.
    # **AND IT DRIVES THE DOOR THROUGH A SOLID BLOCK, NOT INTO ITS FACE.** A repeater in the cell
    # behind an iron door is a repeater a player looks straight at the moment the door opens - and
    # the door is the one thing this machine exists to open. A strongly powered block beside a door
    # opens it exactly as well and is a wall.
    hold = f.at(gate_i, gate_d + 6, 1)
    w.put(hold[0], hold[1], hold[2], "repeater", facing=D["in"], delay="2",
          locked="false", powered="false")
    w.put(hold[0], hold[1] - 1, hold[2], pal["ground"])
    w.put(*f.at(gate_i, gate_d + 7, 1), pal["wall"])          # the conductor the repeater drives
    _line(w, pal, f, (gate_i, gate_d + 5), (gate_i, gate_d + 5), 1)
    w.put(door[0], door[1], door[2], "iron_door", facing=p["facing"], half="lower",
          hinge="left", open="false", powered="false")
    w.put(door[0], door[1] + 1, door[2], "iron_door", facing=p["facing"], half="upper",
          hinge="left", open="false", powered="false")
    for i in range(gate_i - 2, gate_i + 3):
        for d in range(gate_d + 8, depth):
            w.put(*f.at(i, d, -1), pal["trim"])
    for d in range(gate_d + 8, depth):
        for h in range(1, height):
            w.put(*f.at(gate_i - 2, d, h), pal["wall"])
            w.put(*f.at(gate_i + 2, d, h), pal["wall"])
    for i in range(gate_i - 2, gate_i + 3):
        for h in range(1, height):
            if i == gate_i and h < 3:
                continue
            w.put(*f.at(i, gate_d + 8, h), pal["wall"])
            w.put(*f.at(i, depth - 1, h), pal["wall"])
    prizes = []
    for i in (gate_i - 1, gate_i + 1):
        b = f.at(i, depth - 2, 0)
        w.put(b[0], b[1], b[2], "barrel", facing="up", open="false")
        prizes.append(b)

    _pit_floor(w, f, pal, -1, width, 3, depth, -1)
    title = str(p.get("title") or "THE SAFE").upper()
    signed = _sign(w, f, pal, width // 2, -1, height - 1, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, width // 2 - 3, -1, height - 1, f.facing,
                    ["THREE DIALS", "turn the pages", "all three right", "and it opens"])
    for i in (0, width - 1):
        _hang_light(w, f, pal, i, -1, height - 2)

    return {"kind": "safe", "width": width, "depth": depth, "height": height + 1,
            "combo": list(combo), "dials": [list(f.at(i, 2, 1)) for i in dial_i],
            "door": list(door), "vault": [list(b) for b in prizes], "signed": signed,
            "inputs": [list(f.at(i, 2, 1)) for i in dial_i], "outputs": [list(door)],
            "stock": {"the vault barrels": "the prizes behind the door",
                      "each lectern": "a book, so there are pages to turn"},
            "contract": (f"the door opens only when all three dials read {list(combo)}; any one "
                         f"of them wrong and it stays shut"),
            "unverified": ["WHICH PAGE MAPS TO WHICH LEVEL is the game's own scaling of a book's "
                           "page count onto 1..15. The combination is stated as levels; set the "
                           "books' length so the numbers a player can reach include them."]}


def _quiet(w: World, p: dict, ctx) -> dict:
    """THE QUIET ROOM. Walk the corridor without making a sound. Set a sensor off and the alarm
    lights and the door at the far end shuts in your face.

    **THE ONE ATTRACTION HERE WITH NO BUTTON AND NO PRIZE DROPPER**, because the prize is getting
    through. `sculk_sensor` is 1.19's headline block - the deep dark shipped in the same release
    this server runs - and nothing in this project has ever used it. It reads a VIBRATION: walking,
    landing, opening a door, breaking a block. Wool absorbs vibrations, which is the trick, and the
    sign hints at it rather than stating it: the floor is a chequer of wool and stone and the wool
    is the safe route.

    **THE DOOR IS HELD OPEN AND THE ALARM TAKES IT AWAY**, which is the opposite of every other
    door in this repo and is why it needs an inverter. A torch on a block is lit until that block
    is powered, so the torch holds the door open and the alarm's own line switches the torch off.
    A door wired the ordinary way would be shut until the alarm opened it, which is a machine that
    rewards being loud.

    The alarm is an OR of every sensor - merged dust, which is free - so any one of them ends it.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    n = max(2, min(6, int(p["sensors"])))
    trip = max(1, min(10, int(p["alarm"])))
    # THE CORRIDOR MUST HOLD ITS OWN THRESHOLD. A `trip`-cell dust run plus a boost plus the bus
    # is `trip + 6` cells across; sized at a flat 7 the bus lane landed BEHIND the threshold and
    # the return run doubled back over it, shorting every sensor to the alarm permanently.
    width = trip + 7
    depth = n * 3 + 8
    height = 5

    # **THE WALL STARTS AT THE STANDING COURSE.** Begun at h=1 the corridor stood open all round at
    # ankle height and the room floated one course over its own pad - `_shell`'s own recorded
    # lesson, made again here where no `_shell` is used.
    _pad(w, f, pal, width, depth, margin=1)
    for i in range(width):
        for h in range(0, height):
            w.put(*f.at(i, depth - 1, h), pal["wall"])
    for d in range(depth):
        for h in range(0, height):
            w.put(*f.at(0, d, h), pal["wall"])
            w.put(*f.at(width - 1, d, h), pal["wall"])
    for i in range(-1, width + 1):
        for d in range(-1, depth + 1):
            w.put(*f.at(i, d, height), pal["trim"])
    for i in range(1, width - 1):
        for h in range(0, height):
            if i == width // 2 and h in (0, 1):
                continue                                   # ...with a way in, left EMPTY
            w.put(*f.at(i, 0, h), pal["wall"])
    for i in range(1, width - 1):
        for d in range(1, depth - 1):
            # THE CHEQUER. Wool absorbs a vibration, so the wool cells are the quiet route and the
            # stone ones are not. Said on the sign as a hint, never as an instruction.
            w.put(*f.at(i, d, -1), "white_wool" if (i + d) % 2 == 0 else pal["path"])

    # **THE MACHINE IS UNDER THE FLOOR, AND THE CHEQUER IS ITS CEILING.** It used to run at the
    # standing course, straight across the corridor: three bands of dust and comparators laid over
    # the very floor the game asks you to cross, which is Jack's whole complaint in one room.
    # Under the chequer it is invisible and the corridor is clear end to end - and it is BETTER
    # physics, because the wool a player is picking their way across is now the thing between
    # their footsteps and the sensor, which is exactly what the sign hints at.
    MACH, DECK = -2, -3
    _pit_floor(w, f, pal, -1, width, -1, depth, DECK)

    sensors, alarms = [], []
    bus_i = width - 2
    for k in range(n):
        d = 3 + k * 3
        s = f.at(1, d, MACH)
        w.put(s[0], s[1], s[2], "sculk_sensor", power="0",
              sculk_sensor_phase="inactive", waterlogged="false")
        rd = read_out(f.at(2, d, MACH), D["i+"])
        _lay(w, pal, (rd,))
        gate = circuits.threshold(rd["out"], trip, facing=D["i+"])
        _lay(w, pal, (gate,))
        amp = circuits.boost((gate["out"][0] + _STEP[D["i+"]][0], gate["out"][1],
                              gate["out"][2] + _STEP[D["i+"]][1]), facing=D["i+"])
        _lay(w, pal, (amp,))
        sensors.append(s)
        # EVERY SENSOR ONTO ONE BUS. An OR is merged dust and costs nothing at all.
        _line(w, pal, f, (2 + trip + 2, d), (bus_i, d), MACH)
        _line(w, pal, f, (bus_i, d), (bus_i, depth - 4), MACH)

    # THE ALARM LAMPS ARE SET INTO THE FLOOR, lit by the bus directly beneath them. A lamp is a
    # full cube, so a floor is not weakened by one - and an alarm underfoot is read from anywhere
    # in the corridor without hanging anything in the way of the walk.
    for k in range(n):
        lamp = f.at(bus_i, 3 + k * 3, -1)
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        alarms.append(lamp)

    # THE INVERTER THAT HOLDS THE DOOR OPEN, AND IT LIVES UNDER THE FLOOR.
    #
    # **THE DOOR WAS AT HEAD HEIGHT AND IT WAS HALF A DOOR.** Built at h=2 and h=3 with the wall
    # loop running afterwards over h=3, the upper half was overwritten by wool the same tick it was
    # placed - so the far end of the corridor held a lower door leaf, two courses above a player's
    # feet, blocking nothing at all. The game's whole point is that the alarm shuts the way out,
    # and the way out was never shut. A door is at h=0 and h=1, which is where a body is.
    #
    # **AND THE TORCH IS TWO COURSES AWAY FROM IT, NOT BESIDE IT.** A torch in the cell next to a
    # door is a torch a player looks straight at when the door opens - which is precisely when
    # they are looking. The inverter sits under the floor and drives the door through the SOLID
    # BLOCK the door stands on: a strongly powered block beside a door opens it exactly as well as
    # a wire does, and it is a floor.
    # **THE BUS DRIVES A BLOCK AND THE TORCH HANGS OFF THE FAR SIDE OF IT.** Put the torch's own
    # support directly under the bus's last cell and the cell the torch drives comes out ADJACENT
    # to that same bus: the torch feeds its own input, the alarm latches on the moment the chunk
    # loads, and the door is shut for ever with no vibration anywhere. Measured, it settled at a
    # permanent 15 on a machine whose every block was legal, supported and affordable. Two cells of
    # separation is the fix, and the block between them is what the bus points into.
    into = f.at(bus_i, depth - 3, MACH)
    w.put(into[0], into[1], into[2], pal["trim"])
    torch = f.at(bus_i, depth - 2, MACH)
    w.put(torch[0], torch[1], torch[2], "redstone_wall_torch", facing=D["in"], lit="true")
    cond = f.at(bus_i, depth - 2, -1)          # the torch drives the block above it: the doorstep
    w.put(cond[0], cond[1], cond[2], pal["trim"])
    door = f.at(bus_i, depth - 2, 0)
    w.put(door[0], door[1], door[2], "iron_door", facing=p["facing"], half="lower",
          hinge="left", open="false", powered="false")
    w.put(door[0], door[1] + 1, door[2], "iron_door", facing=p["facing"], half="upper",
          hinge="left", open="false", powered="false")
    # THE CROSS WALL THE DOOR IS IN, and the way out beyond it. The doorway column is left EMPTY by
    # the loop rather than punched afterwards: built the other way round, this door's upper half
    # was overwritten by the wall the same tick it was placed, and the far end of the corridor held
    # half a door two courses over a player's head, blocking nothing at all.
    for i in range(1, width - 1):
        for h in range(0, height):
            if i == bus_i and h in (0, 1):
                continue
            w.put(*f.at(i, depth - 2, h), pal["wall"])
    for h in (0, 1):
        w.cells.pop(f.at(bus_i, depth - 1, h), None)         # ...and out through the far wall

    title = str(p.get("title") or "QUIET ROOM").upper()
    signed = _sign(w, f, pal, 1, -1, 3, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, width - 2, -1, 2, f.facing,
                    ["GET TO THE DOOR", "without a sound", "the sculk hears", "stone, not wool"])
    _hang_light(w, f, pal, width // 2, 1, height - 1)

    return {"kind": "quiet", "width": width, "depth": depth, "height": height + 1,
            "sensors": [list(s) for s in sensors], "lamps": [list(a) for a in alarms],
            "door": list(door), "torch": list(torch), "trip": trip, "signed": signed,
            "inputs": [list(s) for s in sensors], "outputs": [list(door)] + [list(a) for a in alarms],
            "stock": {},
            "contract": (f"the door is HELD OPEN while every sensor is quiet; a vibration of "
                         f"{trip} or more at any one of them lights the alarm and shuts it"),
            "unverified": ["WHAT MAKES A VIBRATION, and how strong, is the game's own table - the "
                           "simulator has no entities and cannot walk down the corridor. That "
                           "wool absorbs vibrations is vanilla behaviour and is the whole trick."]}


def _prizecounter(w: World, p: dict, ctx) -> dict:
    """WHERE YOU SPEND WHAT YOU WON. Barrels of prizes behind a counter, the price board on the
    wall, an IN STOCK lamp over each barrel - and a bench and a lamp outside it.

    **AN ARCADE IS SOMEWHERE PEOPLE LINGER, NOT A ROOM OF MACHINES.** A game with nothing to spend
    its prizes on is a game worth playing once. This is the reason to play the others twice, and
    it is deliberately the only kind here with somewhere to SIT.

    **THE STOCK LAMP IS THE ONLY MECHANISM AND IT EARNS ITS PLACE.** A comparator reads a
    container's fullness, and that is the whole circuit: a counter that tells whoever restocks it
    which barrel is empty, from across the midway, without opening anything. It is also the one
    thing in this file the house cannot lose money on - there is no dispenser in it, because
    handing over a prize is a person's job and the prices are a person's decision.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    D = _dirs(p["facing"])
    lanes = max(2, min(8, int(p["lanes"])))
    width = lanes * 2 + 1
    depth = 5
    height = 5

    # MARGIN 3, because the bench stands three cells out in front and a bench with no ground under
    # it is a nineteen-cell stray that no placement check reports.
    _pad(w, f, pal, width, depth, margin=3)
    _shell(w, f, pal, width, depth, height)
    for i in range(1, width - 1):                    # the serving counter
        w.put(*f.at(i, 1, 0), pal["trim"])
        w.put(*f.at(i, 1, 1), pal["slab"], type="top", waterlogged="false")
    for i in range(width):                           # the fascia the name hangs on
        w.put(*f.at(i, 1, height - 1), pal["trim"])

    barrels, lamps = [], []
    for k in range(lanes):
        i = 1 + k * 2
        bar = f.at(i, 3, 1)
        w.put(bar[0], bar[1], bar[2], "barrel", facing=p["facing"], open="false")
        w.put(*f.at(i, 3, 0), pal["trim"])
        # A COMPARATOR READS WHAT IS BEHIND IT: the barrel at its back, the lamp in front. Written
        # the other way round the whole row is dark for ever, and legal, and supported.
        rd = read_out(f.at(i, 2, 1), D["out"])
        _lay(w, pal, (rd,))
        lamp = rd["out"]
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        w.put(lamp[0], lamp[1] - 1, lamp[2], pal["trim"])
        barrels.append(bar)
        lamps.append(lamp)

    # THE BENCH AND THE LAMP OUTSIDE, which is the actual difference between a shop and a place.
    for i in range(1, width - 1):
        w.put(*f.at(i, -3, 0), pal["stair"], facing=p["facing"], half="bottom",
              shape="straight", waterlogged="false")
    for i in (0, width - 1):
        for h in range(0, 3):
            w.put(*f.at(i, -3, h), pal["post"])
        w.put(*f.at(i, -3, 3), pal["trim"])
        w.put(*f.at(i, -3, 4), pal["light"], hanging="false", waterlogged="false")

    title = str(p.get("title") or "PRIZES").upper()
    signed = _sign(w, f, pal, width // 2, 0, height - 1, f.facing, [title[:SIGN_WIDTH]])
    signed &= _sign(w, f, pal, width // 2 - 2, 0, height - 1, f.facing,
                    ["TRADE THEM IN", "lit = in stock", "dark = sold out", "prices at bar"])
    _hang_light(w, f, pal, width // 2, 2, height - 1)

    return {"kind": "prizecounter", "width": width, "depth": depth, "height": height + 1,
            "lanes": lanes, "barrels": [list(b) for b in barrels],
            "lamps": [list(l) for l in lamps], "signed": signed,
            "inputs": [list(b) for b in barrels], "outputs": [list(l) for l in lamps],
            "stock": {"each barrel": "the prizes it hands out"},
            "contract": ("each barrel's lamp is lit while that barrel holds anything and dark "
                         "when it is empty"),
            "unverified": []}


BUILDERS = {
    "plinko": _plinko,
    "range": _range,
    "strength": _strength,
    "weigh": _weigh,
    "reaction": _reaction,
    "safe": _safe,
    "quiet": _quiet,
    "prizecounter": _prizecounter,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ARCADE, **cfg}
    if not p.get("at"):
        raise ValueError("arcade needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown arcade kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # **COVER THE WIRING.** Every kind here lays its machine and then hands it to one pass, rather
    # than each one growing its own lid: the rule is the same for all of them and a per-kind lid is
    # a per-kind way to forget. `stand` is what the kind says a player must be able to occupy, and
    # `conceal` will not cap one - so a component still visible afterwards is REPORTED and fails
    # `tests/test_conceal.py` rather than being quietly accepted.
    hidden = conceal.conceal(w, LANDS[p["land"]]["ground"],
                             protect=[tuple(c) for c in meta.get("stand", ())])

    # THE EXPENSIVE PARTS ARE COUNTED, because they decide whether this can be built at all. A
    # lamp cannot be substituted by colour - a dark block that looks like a lamp is a display that
    # does not work - so it is priced rather than swapped.
    budget = {}
    for pos, (name, _pr) in w.cells.items():
        if name in ("redstone_lamp", "note_block"):
            budget[name] = budget.get(name, 0) + 1

    # **THE MEASURED FOOTPRINT, NOT THE DECLARED ONE.** A kind's `width`/`depth` describe the part
    # a player stands in; the machine behind and under it is often three times as deep, and a
    # planner that books the declared box sites the next attraction inside this one's pit. Both are
    # reported, and `footprint` is the one that is true.
    f = _Frame(p)
    ijs = [_ij(f, c) for c in w.cells]
    lo_i, hi_i = min(v[0] for v in ijs), max(v[0] for v in ijs)
    lo_d, hi_d = min(v[1] for v in ijs), max(v[1] for v in ijs)
    lo_h, hi_h = min(v[2] for v in ijs), max(v[2] for v in ijs)

    return w.canvas({
        "kind": f"arcade/{p['kind']}",
        "footprint": [hi_i - lo_i + 1, hi_d - lo_d + 1],
        "courses": [lo_h, hi_h],
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        "budget": budget,
        "concealed": hidden["placed"],
        "visible_redstone": len(hidden["left"]),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
