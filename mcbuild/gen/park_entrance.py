"""THE PARK'S FRONT DOOR: where a visitor lands, the queue they walk, and the gate they pay at.

    PF Entry Gate   V0-5 x U270-330, world X97500-97505 / Z80570-80630, Y203 up

A visitor logs in at the VOID EDGE of the centre island, facing the railway down the park's own
axis. In front of them is a walled forecourt they cannot leave sideways; ahead of that a gate
building whose ceremonial arch is barred, so the park is visible and not reachable; and either
side of the arch two turnstile lanes with IRON DOORS that open when 23 grass blocks go into the
till beside them.

---------------------------------------------------------------------------------------------
THE SITE WAS MEASURED BEFORE ANYTHING WAS DRAWN, AND IT DECIDED ALMOST ALL OF IT

`out/Park Ways.litematic` is the shipped ground and it is finished. Read cell by cell over
V0-V5 x U240-U369 it says:

    V0-V5, U270..U331     lawn, and NOTHING ELSE - the only clear apron in the Midway
    V0-V5, U251..U269     the round plaza at the U260 avenue, paved: a STREET
    V0-V5, U332..U350     the round plaza at the U341 avenue, paved: a STREET
    V4, U269 / U300 / U332  APRON LAMP MASTS - base, four courses of fence, a slab canopy,
                            with lantern arms reaching V2 and V6 at y3-y5
    ~17 scattered `moss_carpet` cells at Y203, on the lawn

So the compound is **U270..U330** and not one cell wider: a cell further either way is somebody's
plaza. That is why the axis is U300 and why the composition is 61 wide.

**AND THE PARK'S OWN LAMP STANDS ON THE AXIS.** The mast at V4/U300 occupies Y203-Y208 in the
one column the gate would most like to be solid. It is not moved and it is not built over: the
ceremonial arch is a nine-wide portico open at V3-V4, the mast stands INSIDE it as the gate's own
lamp, and the grille that closes the arch is at V5 behind it. Every cell `Park Ways` owns is
refused by `_Lot.put` and counted, so the rule "nothing may touch a street, a path, a plaza, a
verge or a lamp" holds BY CONSTRUCTION rather than by a promise - see `_ways_mask`.

**THE FLOOR IS NOT MINE AND IS NOT PAVED.** Every Y202 cell in the compound is `Park Ways`'
moss. A design that repaved it would be replacing a finished ground layer, so the forecourt is
lawn and everything this file places starts one course up. That also settles where the machine
lives: there is no crawlspace to dig, because the course under the paving belongs to somebody
else. It lives in the gate building's own interior instead - see below.

---------------------------------------------------------------------------------------------
CONTAINMENT IS A CLOSED CURVE, AND THE VOID IS ONE SIDE OF IT

    V-1        open void - the park's own edge, and the reason the spawn is dramatic
    V0         the sea wall: two courses, the whole 61
    U270, U330 the flank walls: two courses, V0..V2
    V3..V5     the gate building, solid the whole 61 but for two door portals and one grille

With the doors shut that is a sealed pen. It is not asserted by looking at it:
`tests/test_park_entrance.py` floods the composite from the spawn cell and asserts that nothing
outside V0-5 / U270-330 is reachable at all - so neither the Frontier (U<170) nor Prismworks
(U>430) can be walked to without passing the gate.

A moss carpet the wall has to skip is not a hole in it: a carpet is passable and the course ABOVE
it is mine, and a player needs two clear courses to walk through. The flood is what proves that
rather than the reasoning.

---------------------------------------------------------------------------------------------
THE PAY GATE, AND WHY THE PRICE IS 23

**GRASS IS THIS SERVER'S CURRENCY** - `blocks.spendable("grass_block")` is False for exactly the
reason the park's lawn is moss - so "pay the grass" is a real transaction and the till is a real
container. What it costs is not a number somebody liked. A comparator reads a container as

    floor(14 * total / (slots * 64)) + (1 if anything at all)

and a hopper has five slots, so a hopper of grass steps every 320/14 = 22.86 blocks:

    0 blocks      -> 0        22 blocks -> 1        23 blocks -> 2        46 blocks -> 3

**23 IS THE FIRST COUNT THAT MOVES THE READING PAST "SOMETHING IS IN HERE".** The gate is a
threshold at level 2, so the price is 23 grass blocks, measured rather than chosen; `price_level`
in the config is the LEVEL and `price_blocks()` derives the count from the same arithmetic, so
the sign, the meta and the test cannot disagree about what a visitor owes.

The machine is nine cells in one straight line inside the gate building's interior course:

    till       hopper[facing=down] - a DEAD END, so it accumulates. Nothing below it is a
               container, so nothing drains it.
    mouth      hopper[facing=down] one course up, reached through a slot in the front face:
               the visitor's grass falls from the mouth into the till.
    comparator reads the till from behind      -> level L
    2 x dust   THE THRESHOLD. Dust loses one per block, so a tap one cell along carries
               something only when L was at least 2. `circuits.threshold` is this rule and this
               is the same rule inlined, because the run has to share a line with the rest.
    A          the block the dust weakly powers
    T0         a wall torch on A. LIT at rest - which is what shuts the gate.
    B          the block T0 powers
    T1         a wall torch on B. UNLIT at rest, and `lit=false` is SHIPPED that way: a torch
               standing on a powered block that ships `lit=true` is high for the tick or two the
               stack takes to settle, and that is a gate that opens on every chunk load.
    door       T1 is beside the lower half, so `emit` powers it; and a lit torch STRONGLY POWERS
               THE BLOCK ABOVE IT, which is the jamb beside the upper half. One torch, both
               halves, and `test_both_halves_of_every_door_are_powered` is what keeps it.

Two inversions and not one, for the reason `ticketing.py` records: a single torch gives a gate
that stands open at rest and shuts when you pay.

**WHAT IT DELIBERATELY IS NOT.** It is a TOLL GATE, not a turnstile: the fare sits in the till
and the doors stand open while it is there, until the keeper empties the till through the same
slot. The self-resetting version - a latch set by the threshold and reset by "till empty",
unlocking a drain hopper into a collection barrel - is a good machine and it is NOT SHIPPED,
because the drain is a hopper transfer, this simulator has no entities, and the house rule of
this repo is that an unassertable mechanism does not go in. The hazard is pinned instead, exactly
as the casino pins its own: `test_A_FARE_LEFT_IN_THE_TILL_HOLDS_THE_GATE_OPEN`.

**A HOPPER BESIDE A LIT REDSTONE TORCH IS DISABLED**, and nothing in `mcbuild.circuit` can see
that. It is designed out - the till and the mouth sit at one end of the line and both torches at
the other, seven cells away - and `test_no_hopper_touches_a_torch` is what keeps them apart.

---------------------------------------------------------------------------------------------
THE ARCHITECTURE, AND THE ONE THING THAT MAKES VOXELS READ AS A BUILDING

Regularity and openings, never damage - the rule the void tower settled and the casino repeated.
So: a plinth, a bay rhythm on the front, a string course, a deep portico on the axis, a cornice
that projects, a parapet with crenellations, and two towers. The palette is the Midway's own out
of `parkways.LANDS`, with a value ladder taken ACROSS material families because inside one family
a ladder cannot exist by construction:

    white_wool 236  >  smooth_stone 159  >  stone_bricks 122  >  polished_blackstone_bricks 45

The queue is stanchion rails in the two-deep forecourt, weaving a walker between V1 and V2, under
a lit oak canopy carried on posts standing off the sea wall. It is shallow because the compound is
six courses deep and that is all the apron there is; it is 61 long, which is where the walk comes
from.
"""
from __future__ import annotations

import pathlib

from .canvas import Canvas
from .parkways import LANDS as WAYS_LANDS

#: V0 -> world X, the first course ABOVE the lawn, U0 -> world Z. The same anchor
#: `gen/park_vantage.py` uses, so two park modules cannot disagree about where the park is.
ANCHOR = (97500, 203, 80300)
LAWN_Y = 202                      # the course `Park Ways` paves; canvas y0 is the one above it

#: The park's own reserves, refused at the door rather than discovered in an audit.
RIM_RESERVE = (171, 199)
REACHES = ((170, 214), (385, 429))

#: The shipped ground layer. Every cell of it is REFUSED, which is how "nothing may touch a
#: street, a path, a plaza, a verge or a lamp" becomes a property of the code rather than a
#: promise in a docstring. Missing, the build still runs and says so in `meta`.
WAYS = "out/Park Ways.litematic"

SIGN_WIDTH = 15                   # a sign line clips mid-word past this


def price_blocks(level: int, slots: int = 5, stack: int = 64) -> int:
    """The number of grass blocks a comparator level costs, from the game's own formula.

    A comparator reads `floor(14 * total / (slots * stack)) + 1`, so the smallest total that
    reads `level` is the smallest n with `floor(14n / (slots*stack)) >= level - 1`.

    ONE SOURCE, so the sign, the meta and the test cannot drift: this is the only place the
    arithmetic is written down.
    """
    level = max(1, min(15, int(level)))
    cap = slots * stack
    n = 0
    while (14 * n) // cap < level - 1:
        n += 1
    return n


PARK_ENTRANCE = {
    "kind": "gate",
    "land": "midway",
    "at": [0, 270],            # [V, U] of the lot's near corner, in park coordinates
    "size": [6, 61],           # [dV, dU] - V0..V5 and U270..U330
    "axis": 30,                # local u of the composition's axis (U300)
    "lanes": [22, 38],         # local u of the two turnstile lanes (U292, U308)
    "arch": [26, 34],          # local u range of the ceremonial portico (U296..U304)
    "towers": [6, 54],         # local u of the two tower centres
    "spawn": [1, 30],          # local [v, u] of the spawn cell - V1, U300
    "price_level": 2,          # the comparator level the gate opens at -> 23 grass blocks
    "wall_h": 5,               # courses of the gate building's main wall
    "canopy_y": 4,             # the queue canopy's soffit course
    "ways": WAYS,
    "title": "THE MIDWAY",
}


# --------------------------------------------------------------------------- the palette

def _pal(land: str) -> dict:
    """The land's four anchor materials, plus the vocabulary a gate needs and a street does not.

    Taken from `parkways.LANDS` rather than retyped: a gate standing on a land's own paving has to
    read as the same hand, and a second copy of the palette is a second thing to forget.
    """
    if land not in WAYS_LANDS:
        raise ValueError(f"unknown land {land!r}; have {sorted(WAYS_LANDS)}")
    w = WAYS_LANDS[land]
    return {
        "field": w["accent"],                 # white_wool  236 - the fairground front
        "pier": w["core"],                    # smooth_stone 159
        "band": w["inlay"],                   # red_wool          - the Midway's own line
        "plinth": w["border"],                # polished_blackstone_bricks 45
        "trim": "stone_bricks",               # 122
        "trim_stair": "stone_brick_stairs",
        "trim_slab": "stone_brick_slab",
        "trim_wall": "stone_brick_wall",
        "chisel": "chiseled_stone_bricks",
        "post": w["post"],                    # oak_fence
        "beam": "oak_planks",
        "roof": "oak_slab",
        "eave": "oak_stairs",
        "light": w["light"],                  # lantern
        "glow": w["glow"],                    # ochre_froglight
        "grille": "iron_bars",
        "door": "iron_door",
        "sign": "oak_wall_sign",
    }


# --------------------------------------------------------------------------- the ground mask

_MASK_CACHE: dict = {}


def _ways_mask(path: str, v0: int, u0: int, dv: int, du: int) -> set | None:
    """Every cell of the shipped ground layer inside this lot, in LOCAL (v, u, y).

    `Park Ways` sits at world Y202 and canvas y0 here is Y203, so a ways row `k` maps to local
    `k - 1`; row 0 is the lawn itself and lands at -1, outside this canvas and therefore outside
    the question. Returns None when the file is absent - the build still runs, and `meta` says so
    rather than claiming a check it did not make.
    """
    key = (path, v0, u0, dv, du)
    if key in _MASK_CACHE:
        return _MASK_CACHE[key]
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = pathlib.Path(__file__).resolve().parents[2] / path
    if not p.exists():
        _MASK_CACHE[key] = None
        return None
    from .. import schem
    m = schem.load(str(p))
    ids = m.ids                                    # [y][z=U][x=V], origin Y202 / U0 / V0
    sy, su, sv = ids.shape
    out = set()
    for k in range(1, sy):
        layer = ids[k]
        for v in range(v0, min(v0 + dv, sv)):
            for u in range(u0, min(u0 + du, su)):
                if layer[u][v]:
                    out.add((v - v0, u - u0, k - 1))
    _MASK_CACHE[key] = out
    return out


# --------------------------------------------------------------------------- the lot

class _Lot:
    """The lot, and the only way a block reaches the canvas.

    Two refusals, counted separately because they mean different things: OUTSIDE is a design that
    does not fit its own declared box, and WAYS is the ground layer winning a cell it already
    owns. A cropped parapet is not a fault anything downstream can report, so both are reported.
    """

    def __init__(self, c: Canvas, dv: int, du: int, mask: set | None):
        self.c, self.dv, self.du = c, dv, du
        self.mask = mask
        self.outside = 0
        self.ways = 0
        self.lights = 0
        self.signs = 0
        self._state: dict = {}

    def blk(self, name: str) -> int:
        if name not in self._state:
            self._state[name] = self.c.state(name)
        return self._state[name]

    def owned(self, v: int, u: int, y: int) -> bool:
        return self.mask is not None and (int(v), int(u), int(y)) in self.mask

    def put(self, v: int, u: int, y: int, name: str, **props) -> bool:
        v, u, y = int(v), int(u), int(y)
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy):
            self.outside += 1
            return False
        if self.owned(v, u, y):
            self.ways += 1
            return False
        blk = self.c.raw_state(name, **props) if props else self.blk(name)
        return self.c.put(v, y, u, blk)

    def has(self, v: int, u: int, y: int) -> bool:
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy):
            return False
        return self.c.solid(int(v), int(y), int(u))

    def clear(self, v: int, u: int, y: int) -> None:
        if 0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy:
            self.c.put(int(v), int(y), int(u), 0)

    def lamp(self, v: int, u: int, y: int, name: str, **props) -> bool:
        if self.put(v, u, y, name, **props):
            self.lights += 1
            return True
        return False

    def sign(self, v: int, u: int, y: int, facing: str, lines, behind) -> bool:
        """A wall sign in the cell in FRONT of its wall, its text facing away from its support.

        THE SUPPORT IS CHECKED, NOT ASSUMED. `gen/park.py` records four kinds shipping a sign hung
        on a column that had an opening in it - a map board behind a lane, a nameplate behind a
        window slit - and a wall sign floating in air draws exactly like one on a wall. `behind` is
        the cell the sign hangs from and it must already be solid.
        """
        bv, bu, by = behind
        if not self.has(bv, bu, by):
            return False
        if not self.put(v, u, y, "oak_wall_sign", facing=facing, waterlogged="false"):
            return False
        text = [str(s)[:SIGN_WIDTH] for s in list(lines)[:4]]
        self.c.sign_text(int(v), int(y), int(u), front=text)
        self.signs += 1
        return True


# --------------------------------------------------------------------------- directions
#
# V runs along world X and U along world Z, so +v is EAST and +u is SOUTH. Written down once
# because a facing bug is invisible in every render this repo has: `render3d` draws a stair,
# a door and a torch facing the wrong way exactly as it draws a right one.

EAST, WEST, SOUTH, NORTH = "east", "west", "south", "north"
V_IN, V_OUT = EAST, WEST          # +v is into the park; -v is out toward the void
U_PLUS, U_MINUS = SOUTH, NORTH


# --------------------------------------------------------------------------- the forecourt

def _sea_wall(L: _Lot, pal: dict, du: int) -> dict:
    """The parapet along V0, over the void. Two courses, because one can be jumped."""
    n = 0
    for u in range(du):
        n += bool(L.put(0, u, 0, pal["plinth"]))
        # A WALL BLOCK, NOT A FENCE. A fence reads as a rail and a rail is what the queue is made
        # of; the park's edge over open void wants mass, and a wall is also what a balustrade cap
        # sits on. The cap is the course a player cannot get over.
        #
        # **PLACED BARE, BECAUSE A WALL'S CONNECTIONS ARE `none|low|tall`, NOT `true|false`.**
        # Written the way a fence is written, all 61 came back as illegal states from the audit -
        # rule 11 in a new costume. They are DERIVED by the game anyway, which is why
        # `work.INTENTIONAL` drops them, so the right number of properties to state here is none.
        n += bool(L.put(0, u, 1, pal["trim_wall"]))
    return {"cells": n}


def _flanks(L: _Lot, pal: dict, du: int) -> dict:
    """The two walls that close the forecourt sideways. V0..V2, three courses tall.

    Three and not two: two is unjumpable from the flat, and the queue's own canopy posts stand
    against them. The gate building closes V3..V5 on its own.
    """
    n = 0
    for u in (0, du - 1):
        for v in range(0, 3):
            for y in range(0, 3):
                n += bool(L.put(v, u, y, pal["pier"] if y else pal["plinth"]))
            n += bool(L.put(v, u, 3, pal["trim_slab"], type="bottom", waterlogged="false"))
    return {"cells": n}


def _queue(L: _Lot, p: dict, pal: dict, du: int) -> dict:
    """Stanchion rails and a lit canopy, in the two courses of forecourt there are.

    THE QUEUE WEAVES, IT DOES NOT SWITCH BACK. A switchback needs four bands and the apron has
    two, so the rails alternate: a stub off the sea wall closes V1, a stub off the gate closes V2
    three cells later, and a walker is put through both bands the length of the compound. That is
    what a stanchion line does at small scale and it is what reads as a queue.

    The rails stop clear of the two lane approaches and of the portico, so the last stretch to a
    door is open - a queue you cannot leave at the front is a trap, not a queue.
    """
    lanes, arch = p["lanes"], p["arch"]
    keep_clear = set()
    for lane in lanes:
        keep_clear.update(range(lane - 2, lane + 3))
    keep_clear.update(range(arch[0] - 1, arch[1] + 2))
    rails = 0
    for u in range(4, du - 4):
        if u in keep_clear:
            continue
        if u % 6 == 0:
            rails += bool(L.put(1, u, 0, pal["post"], **_fence_props(True)))
        elif u % 6 == 3:
            rails += bool(L.put(2, u, 0, pal["post"], **_fence_props(True)))

    # THE CANOPY. Posts stand ON the sea wall, never in the queue: a post in the walked band is
    # an obstacle the rails already provide. The beam spans V0..V3 so it lands on the gate
    # building at the far end, and the roof is two courses of slab over the walked bands.
    cy = int(p["canopy_y"])
    posts = beams = roof = 0
    for u in range(3, du - 3, 6):
        if u in keep_clear:
            continue
        for y in range(2, cy):
            posts += bool(L.put(0, u, y, pal["post"], **_fence_props(False)))
        for v in range(0, 4):
            beams += bool(L.put(v, u, cy, pal["beam"]))
        L.lamp(1, u, cy - 1, pal["light"], hanging="true", waterlogged="false")
        L.lamp(2, u, cy - 1, pal["light"], hanging="true", waterlogged="false")
    for u in range(3, du - 3):
        if u in keep_clear or u % 6 == 3:
            continue
        for v in (1, 2):
            roof += bool(L.put(v, u, cy, pal["roof"], type="bottom", waterlogged="false"))
    return {"rails": rails, "posts": posts, "beams": beams, "roof": roof}


def _fence_props(along_u: bool) -> dict:
    """A fence's connections are DERIVED by the game and `work.INTENTIONAL` drops them.

    They are written anyway, and only for the render: a post with every side false draws as a
    lone stick. Nothing downstream compares them, which is why this returns a plain dict rather
    than pretending it is a decision.
    """
    return {"north": "true" if along_u else "false",
            "south": "true" if along_u else "false",
            "east": "false", "west": "false", "waterlogged": "false"}


# --------------------------------------------------------------------------- the gate building

def _building(L: _Lot, p: dict, pal: dict, du: int) -> dict:
    """V3..V5: solid the whole 61 but for two door portals and one barred portico.

    The elevation, and every band of it is a LINE rather than a scatter - the deck soffit's
    lesson, which shipped 215 grid runs of which 184 were one or two cells:

        y0        plinth, blackstone, the whole width
        y1..y4    the field, with a smooth-stone pier every six
        y5        the string course, red
        y6..y8    the upper wall
        y9        the cornice, projecting into V2 on a course of upside-down stairs
        y10       the parapet
        y11       crenellations, one on two
    """
    wall_h = int(p["wall_h"])
    lanes, arch, towers = p["lanes"], p["arch"], p["towers"]
    open_u = set()
    for lane in lanes:
        open_u.add(lane)
    portico = set(range(arch[0], arch[1] + 1))

    n = 0
    for u in range(du):
        for v in (3, 4, 5):
            # the plinth
            n += bool(L.put(v, u, 0, pal["plinth"]) if u not in open_u | portico else 0)
            for y in range(1, wall_h + 1):
                if u in open_u and y <= 2:
                    continue                      # the turnstile portal, two courses tall
                if u in portico and v in (3, 4) and y <= 6:
                    continue                      # the portico, open to its own arch head
                if u in portico and v == 5 and y <= 5:
                    continue                      # ...and the grille goes here
                mat = pal["pier"] if (u % 6 == 0 or u in (0, du - 1)) else pal["field"]
                n += bool(L.put(v, u, y, mat))
    # the plinth under the portals and the portico is the threshold you walk on, so it is left to
    # the lawn; the plinth course either side of a portal is a pier foot instead.
    for u in sorted(open_u | portico):
        for v in (3, 4, 5):
            if u in portico and v in (3, 4):
                continue
            if u in open_u:
                continue
            n += bool(L.put(v, u, 0, pal["plinth"]))

    # ---- the string course, the upper wall, the cornice, the parapet
    for u in range(du):
        n += bool(L.put(3, u, wall_h + 1, pal["band"]))
        n += bool(L.put(4, u, wall_h + 1, pal["trim"]))
        n += bool(L.put(5, u, wall_h + 1, pal["band"]))
        for y in range(wall_h + 2, wall_h + 5):
            for v in (3, 4, 5):
                mat = pal["pier"] if u % 6 == 0 else pal["field"]
                n += bool(L.put(v, u, y, mat))
    cor = wall_h + 5
    for u in range(du):
        for v in (3, 4, 5):
            n += bool(L.put(v, u, cor, pal["plinth"]))
        # THE CORNICE PROJECTS, and an upside-down stair is what makes it a cornice rather than a
        # painted line. Its tall side is its `facing`, so it leans back INTO the wall it grows
        # from - the rule `gen/enrich.py` states and `tests/test_park_entrance.py` asserts,
        # because this repo's renderer draws both directions identically.
        n += bool(L.put(2, u, cor, pal["trim_stair"], facing=V_IN, half="top",
                        shape="straight", waterlogged="false"))
    for u in range(du):
        for v in (3, 4, 5):
            n += bool(L.put(v, u, cor + 1, pal["trim"]))
        if u % 2 == 0:
            for v in (3, 5):
                n += bool(L.put(v, u, cor + 2, pal["plinth"]))
    return {"cells": n, "cornice_y": cor}


def _portal(L: _Lot, p: dict, pal: dict, lane: int) -> dict:
    """One turnstile lane: the reveal, the iron door, and the arch over it.

    The door is in the MIDDLE band, V4, so it is recessed a course from the front and a course
    from the back: a gate you walk INTO rather than past, and the reveal is what carries the
    till slot and the lane's own lantern.
    """
    n = 0
    # jambs - the two cells either side of the door, both courses, because one of them is what
    # the machine's torch strongly powers.
    for du_ in (-1, 1):
        for y in (0, 1):
            n += bool(L.put(4, lane + du_, y, pal["pier"]))
    # the arch head over the portal
    n += bool(L.put(3, lane, 2, pal["chisel"]))
    n += bool(L.put(4, lane, 2, pal["chisel"]))
    n += bool(L.put(5, lane, 2, pal["chisel"]))
    for du_ in (-1, 1):
        n += bool(L.put(3, lane + du_, 2, pal["trim_stair"], facing=U_PLUS if du_ < 0 else U_MINUS,
                        half="bottom", shape="straight", waterlogged="false"))
    # THE DOOR. `facing` is the way it opens - into the park - and both halves ship SHUT and
    # UNPOWERED, which is the state the machine puts them in at rest.
    for y, half in ((0, "lower"), (1, "upper")):
        n += bool(L.put(4, lane, y, pal["door"], facing=V_IN, half=half, hinge="left",
                        open="false", powered="false"))
    L.lamp(3, lane - 1, 3, pal["light"], hanging="false", waterlogged="false")
    L.lamp(3, lane + 1, 3, pal["light"], hanging="false", waterlogged="false")
    return {"cells": n}


def _portico(L: _Lot, p: dict, pal: dict) -> dict:
    """The ceremonial arch: nine wide, open at V3-V4, and BARRED at V5.

    **YOU SEE THE PARK AND YOU CANNOT WALK INTO IT.** That is the whole idea, and it is what makes
    a paywall an experience rather than an obstruction: the vista down the axis - the carousel,
    the wheel and the railway beyond - is framed by an arch and closed by a grille you can look
    straight through. The park's own apron lamp stands inside it, on the axis, because `Park Ways`
    put it there and this design does not move other people's furniture.
    """
    a0, a1 = p["arch"]
    n = 0
    for u in range(a0, a1 + 1):
        for y in range(0, 6):
            n += bool(L.put(5, u, y, pal["grille"], north="true", south="true",
                            east="false", west="false", waterlogged="false"))
    # the arch head, a flat course with a stepped soffit either side
    for u in range(a0, a1 + 1):
        for v in (3, 4):
            n += bool(L.put(v, u, 7, pal["chisel"]))
    for v in (3, 4):
        n += bool(L.put(v, a0 - 1, 6, pal["trim_stair"], facing=U_PLUS, half="bottom",
                        shape="straight", waterlogged="false"))
        n += bool(L.put(v, a1 + 1, 6, pal["trim_stair"], facing=U_MINUS, half="bottom",
                        shape="straight", waterlogged="false"))
    # the roundel over the arch - a red field ringed in chiselled stone, on the axis
    ax = int(p["axis"])
    for du_ in range(-2, 3):
        n += bool(L.put(3, ax + du_, 9, pal["band"]))
    for du_ in (-3, 3):
        n += bool(L.put(3, ax + du_, 9, pal["chisel"]))
    for du_ in (-2, 2):
        n += bool(L.put(3, ax + du_, 8, pal["chisel"]))
        n += bool(L.put(3, ax + du_, 10, pal["chisel"]))
    for du_ in (-1, 0, 1):
        n += bool(L.put(3, ax + du_, 8, pal["band"]))
        n += bool(L.put(3, ax + du_, 10, pal["band"]))
    for u in range(a0, a1 + 1, 2):
        L.lamp(3, u, 6, pal["light"], hanging="true", waterlogged="false")
    return {"cells": n}


def _towers(L: _Lot, p: dict, pal: dict) -> dict:
    """Two towers, so the gate has a silhouette rather than a wall line.

    They rise out of the building's own bays, four wide, to twice its height, and they are
    crenellated - the one crown treatment this repo has measured as reading from the ground.
    """
    cor = int(p["wall_h"]) + 5
    top = cor + 7
    n = 0
    for cu in p["towers"]:
        for u in range(cu - 1, cu + 3):
            for v in (3, 4, 5):
                for y in range(cor + 2, top):
                    mat = pal["pier"] if (u in (cu - 1, cu + 2)) else pal["field"]
                    n += bool(L.put(v, u, y, mat))
            n += bool(L.put(3, u, top - 3, pal["band"]))
            n += bool(L.put(5, u, top - 3, pal["band"]))
        for u in range(cu - 2, cu + 4):
            for v in (3, 4, 5):
                n += bool(L.put(v, u, top, pal["plinth"]))
            if (u - cu) % 2 == 0:
                for v in (3, 5):
                    n += bool(L.put(v, u, top + 1, pal["plinth"]))
        L.lamp(3, cu, top - 4, pal["light"], hanging="false", waterlogged="false")
        L.lamp(3, cu + 1, top - 4, pal["light"], hanging="false", waterlogged="false")
    return {"cells": n, "top": top}


# --------------------------------------------------------------------------- the machine

def _machine(L: _Lot, p: dict, pal: dict, lane: int, side: int) -> dict:
    """One pay gate, nine cells in a straight line inside V4 - the building's own interior.

    `side` is +1 when the line runs toward increasing u and -1 when it runs the other way, so the
    two lanes are mirror images about the axis and neither machine crosses the portico.

        s*0  the DOOR                      (V4, lane)              - lower y0, upper y1
        s*1  T1   wall torch on B          UNLIT at rest
        s*2  B    T1's support             powered at rest, by T0
        s*3  T0   wall torch on A          LIT at rest
        s*4  A    T0's support             powered when the fare is in
        s*5  dust the threshold's far cell - carries only a level >= 2
        s*6  dust the threshold's near cell
        s*7  comparator, reading the till at its back
        s*8  the TILL, and the mouth one course over it

    Everything is at course y0 except the mouth and the jamb T1 strongly powers, and that is what
    makes one torch open both halves of the door: `emit` reaches the lower half beside it, and a
    lit torch STRONGLY POWERS THE BLOCK ABOVE IT, which is the jamb beside the upper half.
    """
    price = int(p["price_level"])
    if price < 2:
        raise ValueError("a price level under 2 is not a price: a hopper reads 1 for ANY item, "
                         "so the gate would open on a single block of grass")

    def at(k):
        return lane + side * k

    t1, b, t0, a = at(1), at(2), at(3), at(4)
    # the threshold's dust: `price` cells, the last of which carries only when the comparator
    # reads at least `price`. Distance IS the threshold - the same rule `circuits.threshold`
    # states, inlined because this run has to share a line with the rest of the machine.
    dust = [at(4 + price - k) for k in range(price)]
    comp = at(5 + price)
    till = at(6 + price)

    # A WALL TORCH'S `facing` POINTS AWAY FROM ITS SUPPORT, and a comparator's back is behind its
    # `facing`. Every support and the till sit one step FURTHER from the door than the thing that
    # reads them - `at(k+1) - at(k) == side` - so both face `-side`, and that is the same
    # direction. Written once because a facing bug is invisible in every render this repo has:
    # built the other way the torches stand on the blocks they are supposed to be driving.
    torch_facing = comp_facing = U_MINUS if side > 0 else U_PLUS

    cells = 0
    # the two supports, and the jamb the upper half reads
    cells += bool(L.put(4, b, 0, pal["trim"]))
    cells += bool(L.put(4, a, 0, pal["trim"]))
    cells += bool(L.put(4, t1, 1, pal["trim"]))        # the jamb T1 strongly powers
    # the torches. T1 SHIPS UNLIT because unlit is what it is at rest: B is powered by T0, and a
    # torch shipped `lit=true` on a powered block is high for the tick or two the stack takes to
    # settle - which is a gate that opens on every chunk load.
    cells += bool(L.put(4, t1, 0, "redstone_wall_torch", facing=torch_facing, lit="false"))
    cells += bool(L.put(4, t0, 0, "redstone_wall_torch", facing=torch_facing, lit="true"))
    for u in dust:
        cells += bool(L.put(4, u, 0, "redstone_wire"))
    cells += bool(L.put(4, comp, 0, "comparator", facing=comp_facing, mode="compare",
                        powered="false"))
    # THE TILL IS A DEAD END. `facing=down` puts its output into the lawn, which is not a
    # container, so nothing drains it and the count accumulates - which is the whole reason a
    # PRICE can be read off it at all.
    cells += bool(L.put(4, till, 0, "hopper", facing="down", enabled="true"))
    cells += bool(L.put(4, till, 1, "hopper", facing="down", enabled="true"))   # the mouth
    # the slot: a hole in the front face at the mouth's own course, so a visitor reaches through
    # the wall rather than walking round it. The cell is cleared rather than never placed,
    # because the wall loop has already run.
    L.clear(3, till, 1)
    cells += bool(L.put(3, till, 2, pal["chisel"]))
    return {
        "lane": lane, "side": side,
        "door": (4, lane, 0), "door_upper": (4, lane, 1),
        "till": (4, till, 0), "mouth": (4, till, 1), "slot": (3, till, 1),
        "torches": [(4, t1, 0), (4, t0, 0)],
        "threshold": [(4, u, 0) for u in dust],
        "comparator": (4, comp, 0),
        "cells": cells,
    }


# --------------------------------------------------------------------------- the words

def _signs(L: _Lot, p: dict, pal: dict, mach: list, du: int) -> int:
    """What the gate has to say, and it says the price because a house that will not print its
    odds does not know them. Fifteen characters a line, asserted rather than eyeballed."""
    price = price_blocks(int(p["price_level"]))
    ax = int(p["axis"])
    n = 0
    n += L.sign(2, ax - 1, 3, V_OUT, (p["title"], "", "MIDWAY GATE", ""), (3, ax - 1, 3))
    n += L.sign(2, ax + 1, 3, V_OUT, ("ONE FARE", f"{price} GRASS BLOCKS", "", "PAY AT A LANE"),
                (3, ax + 1, 3))
    for m in mach:
        lane, side = m["lane"], m["side"]
        n += L.sign(2, lane, 3, V_OUT, ("TURNSTILE", f"{price} GRASS", "IN THE SLOT", "->"),
                    (3, lane, 3))
        slot_u = m["slot"][1]
        n += L.sign(2, slot_u, 2, V_OUT, ("FARE SLOT", f"{price} GRASS", "BLOCKS", ""),
                    (3, slot_u, 2))
    return n


# --------------------------------------------------------------------------- entry point

def build(cfg: dict, donors=None) -> Canvas:
    p = {**PARK_ENTRANCE, **(cfg or {})}
    if p.get("kind") != "gate":
        raise ValueError(f"unknown entrance kind {p.get('kind')!r}; have 'gate'")
    v0, u0 = int(p["at"][0]), int(p["at"][1])
    dv, du = int(p["size"][0]), int(p["size"][1])
    _refuse_reserves(v0, u0, dv, du)
    pal = _pal(p["land"])

    mask = _ways_mask(p["ways"], v0, u0, dv, du) if p.get("ways") else None
    top = int(p["wall_h"]) + 13
    c = Canvas(dv, top + 3, du)
    L = _Lot(c, dv, du, mask)

    detail = {}
    detail["sea_wall"] = _sea_wall(L, pal, du)
    detail["flanks"] = _flanks(L, pal, du)
    detail["building"] = _building(L, p, pal, du)
    detail["portico"] = _portico(L, p, pal)
    detail["towers"] = _towers(L, p, pal)
    mach = []
    for lane, side in zip(p["lanes"], (-1, 1)):
        _portal(L, p, pal, lane)
        mach.append(_machine(L, p, pal, lane, side))
    detail["queue"] = _queue(L, p, pal, du)
    detail["signs"] = _signs(L, p, pal, mach, du)

    sv, su = int(p["spawn"][0]), int(p["spawn"][1])
    spawn = {
        "park": [v0 + sv, u0 + su],
        "world": [ANCHOR[0] + v0 + sv, ANCHOR[1], ANCHOR[2] + u0 + su],
        # +v is world +X, which is EAST, and Minecraft's yaw is 0 south / 90 west / 180 north /
        # -90 east. Asserted rather than remembered: a yaw is a fact about the game, not a taste.
        "yaw": -90.0, "pitch": 0.0,
        "faces": "+V (world +X, east) - down the park's own axis toward the railway",
    }
    price = price_blocks(int(p["price_level"]))

    c.world_origin = (ANCHOR[0] + v0, ANCHOR[1], ANCHOR[2] + u0)
    c.meta = {
        "kind": "park_entrance",
        "land": p["land"],
        "lot": [v0, u0, v0 + dv - 1, u0 + du - 1],
        "size": [dv, du],
        "height": top + 3,
        "facing": "west",                     # the gate's front looks out toward the void
        "spawn": spawn,
        "price_level": int(p["price_level"]),
        "price_blocks": price,
        "currency": "grass_block",
        "lanes": [
            {
                "lane_u": u0 + m["lane"],
                "door": _world(c, m["door"]),
                "door_upper": _world(c, m["door_upper"]),
                "till": _world(c, m["till"]),
                "mouth": _world(c, m["mouth"]),
                "comparator": _world(c, m["comparator"]),
                "torches": [_world(c, t) for t in m["torches"]],
                "threshold": [_world(c, t) for t in m["threshold"]],
            }
            for m in mach
        ],
        "outputs": [_world(c, m["door"]) for m in mach],
        "lights": L.lights,
        "signs": L.signs,
        "outside_lot_refused": L.outside,
        "ground_layer_refused": L.ways,
        "ground_layer_checked": mask is not None,
        "detail": detail,
        "contract": (
            f"a sealed arrival compound at the park's void edge: a visitor spawns at "
            f"X{spawn['world'][0]} Y{spawn['world'][1]} Z{spawn['world'][2]} facing east and "
            f"cannot reach any other land on foot until {price} grass blocks go into a lane's "
            f"till, at which point BOTH halves of that lane's iron door are powered and it "
            f"opens; below {price} the doors are shut, at rest they are shut, and emptying the "
            f"till shuts them again"),
        "hazards": [
            "A FARE LEFT IN THE TILL HOLDS THAT LANE OPEN. The comparator reads the till "
            "continuously and nothing drains it, so the gate is a TOLL GATE and not a "
            "turnstile: the keeper empties the till through the same slot. Pinned by "
            "test_A_FARE_LEFT_IN_THE_TILL_HOLDS_THE_GATE_OPEN.",
            "A till holds five slots of grass - about thirteen fares - and then cannot take "
            "another. Empty it through the slot.",
            "A visitor can reopen the MOUTH hopper and take back whatever has not yet fallen "
            "into the till. The mouth passes an item every eight game ticks, so that is a "
            "fraction of a second, and it is the same exposure `gen/ticketing.py` ships.",
        ],
        "requires_in_game": [
            "the hopper transfer rate is ENTITY behaviour and this simulator has none: how long "
            "a fare takes to fall from the mouth into the till is the game's number, not ours",
            "colour, and whether the gate reads as a front rather than as a wall, can only be "
            "judged in world",
            "the self-resetting version of this machine - a latch set by the threshold and reset "
            "by an empty till, unlocking a drain hopper into a collection barrel - is designed "
            "and NOT built, because the drain is a hopper transfer and cannot be asserted here",
        ],
    }
    return c


def _world(c: Canvas, cell) -> list:
    v, u, y = cell
    ox, oy, oz = c.world_origin
    return [ox + int(v), oy + int(y), oz + int(u)]


def _refuse_reserves(v0: int, u0: int, dv: int, du: int) -> None:
    """The park's reserves, refused at the door rather than discovered in an audit."""
    if v0 + dv - 1 >= RIM_RESERVE[0]:
        raise ValueError(f"the entrance may not reach V{RIM_RESERVE[0]}-{RIM_RESERVE[1]}, the "
                         f"protected rim reserve; this lot ends at V{v0 + dv - 1}")
    for a, b in REACHES:
        if u0 <= b and u0 + du - 1 >= a:
            raise ValueError(f"the entrance may not stand in the reach U{a}-{b}; this lot is "
                             f"U{u0}-{u0 + du - 1}")


DEFAULTS = PARK_ENTRANCE
