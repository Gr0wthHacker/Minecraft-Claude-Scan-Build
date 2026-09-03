"""THE PARK'S FRONT DOOR: where a visitor lands, the queue they walk, and the gate they pay at.

    PF Entry Gate   V0-5 x U270-330, world X97500-97505 / Z80570-80630, Y203 up

A visitor logs in at the VOID EDGE of the centre island, facing the railway down the park's own
axis. In front of them is a walled forecourt they cannot leave sideways; ahead of that a gate
building whose ceremonial grille contains two IRON DOORS. A signed chest beside each lane receives
one grass from the server adapter; the hopper below is the success receipt for a five-second entry.

    spawn   X97501 Y203 Z80602, yaw -90 (facing world east, +V)   -   V1 / U302

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
    U270, U330 the flank walls: V0..V2, and up OVER the queue canopy - see `_flanks`
    V3..V5     the gate building, solid the whole 61 but for two door portals and one grille

With the doors shut that is a sealed pen. It is not asserted by looking at it:
`tests/test_park_entrance.py` floods the composite from the spawn cell and asserts that nothing
outside V0-5 / U270-330 is reachable at all - so neither the Frontier (U<170) nor Prismworks
(U>430) can be walked to without passing the gate.

A moss carpet the wall has to skip is not a hole in it: a carpet is passable and the course ABOVE
it is mine, and a player needs two clear courses to walk through. The flood is what proves that
rather than the reasoning.

---------------------------------------------------------------------------------------------
THE PAY GATE, AND WHY THE LOCAL PREVIEW OPENS ON ONE ITEM

**GRASS IS THIS SERVER'S CURRENCY** - `blocks.spendable("grass_block")` is False for exactly the
reason the park's lawn is moss - so "pay the grass" is a real transaction and the till is a real
container. What it costs is not a number somebody liked. A comparator reads a container as

    floor(14 * total / (slots * 64)) + (1 if anything at all)

and a hopper has five slots, so a hopper of grass steps every 320/14 = 22.86 blocks:

    0 blocks      -> 0        22 blocks -> 1        23 blocks -> 2        46 blocks -> 3

Comparator level 1 is the only honest local representation of a one-block fare. It proves the
door response and containment, but cannot distinguish grass from another item. The server payment
adapter therefore owns exact item validation and consumption; local tests do not claim otherwise.

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
    if level == 1:
        return 1
    cap = slots * stack
    n = 0
    while (14 * n) // cap < level - 1:
        n += 1
    return n


PARK_ENTRANCE = {
    "kind": "gate",
    "land": "midway",
    "at": [0, 270],            # [V, U] of the lot's near corner, in park coordinates
    # NINETEEN DEEP, and eighteen of that is the approach. Six was the composition's own depth
    # and the whole lot with it, which made the sealed compound 143 standable cells - five deep by
    # fifty-nine wide, a pen rather than an arrival. Jack asked for a spawn at the void edge and a
    # WALK to a central entrance. V0-18 is the arrival apron (V0-5) plus the spine's own paving
    # (V6-18); the ground layer keeps that paving because the ways mask only protects what stands
    # ABOVE the floor course, so the approach walks on the park's own stone.
    "size": [19, 61],          # [dV, dU] - V0..V18 and U270..U330
    "front": 13,               # the gate composition sets back to V13..V18
    "axis": 30,                # local u of the composition's axis (U300)
    "lanes": [28, 32],         # paired iron doors inside the barred arch (U298, U302)
    "arch": [26, 34],          # local u range of the ceremonial portico (U296..U304)
    "towers": [6, 54],         # local u of the two tower centres
    # THE SPAWN IS ONE CELL OFF THE AXIS, AND THAT IS A MEASUREMENT. `Park Ways` stands an apron
    # lamp mast at V4/U300 - a fence post from Y203 to Y207 - so a visitor standing on the exact
    # axis looks straight into it at three blocks. One cell south the sightline runs clear through
    # the portico and the grille to the carousel, the wheel and the railway, which is the whole
    # point of putting them here. `test_the_spawn_looks_down_a_clear_sightline` re-derives it.
    "spawn": [1, 32],          # local [v, u] - at the void edge, aligned with the right-hand door
    "price_level": 1,          # one-item local trigger; live adapter enforces one grass block
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

    def __init__(self, c: Canvas, dv: int, du: int, mask: set | None, front: int = 0):
        self.c, self.dv, self.du = c, dv, du
        #: HOW FAR THE GATE SETS BACK FROM THE VOID EDGE, and it is the whole of the approach.
        #: Every piece of the composition was written against a six-deep lot with absolute v of
        #: 0..5, which is correct geometry and a five-block walk - a visitor spawned three steps
        #: from the doors. Measured on the assembled park the sealed compound was 143 standable
        #: cells, 5 deep by 59 wide: a pen rather than an arrival, and Jack asked for a WALK to a
        #: central entrance. Rather than re-anchor thirty put-sites against `dv` (and re-earn the
        #: containment proof), the composition keeps its own coordinates and the LOT grows in
        #: front of it. Only the two pieces that belong to the edge itself - the sea wall and the
        #: flank walls - opt out with `raw=True`.
        self.front = int(front)
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

    def put(self, v: int, u: int, y: int, name: str, raw: bool = False, **props) -> bool:
        v, u, y = int(v) + (0 if raw else self.front), int(u), int(y)
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy):
            self.outside += 1
            return False
        if self.owned(v, u, y):
            self.ways += 1
            return False
        blk = self.c.raw_state(name, **props) if props else self.blk(name)
        return self.c.put(v, y, u, blk)

    def has(self, v: int, u: int, y: int, raw: bool = False) -> bool:
        v = int(v) + (0 if raw else self.front)
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
        self.c.sign_text(int(v) + self.front, int(y), int(u), front=text)
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
        n += bool(L.put(0, u, 0, pal["plinth"], raw=True))
        # A WALL BLOCK, NOT A FENCE. A fence reads as a rail and a rail is what the queue is made
        # of; the park's edge over open void wants mass, and a wall is also what a balustrade cap
        # sits on. The cap is the course a player cannot get over.
        #
        # **PLACED BARE, BECAUSE A WALL'S CONNECTIONS ARE `none|low|tall`, NOT `true|false`.**
        # Written the way a fence is written, all 61 came back as illegal states from the audit -
        # rule 11 in a new costume. They are DERIVED by the game anyway, which is why
        # `work.INTENTIONAL` drops them, so the right number of properties to state here is none.
        n += bool(L.put(0, u, 1, pal["trim_wall"], raw=True))
    return {"cells": n}


def _flanks(L: _Lot, pal: dict, du: int) -> dict:
    """The two walls that close the forecourt sideways: V0..V2, up OVER the canopy.

    THEY HAVE TO REACH THE CANOPY'S OWN COURSE. Built three high they close the ground and leave
    the roof open at both ends, and a walker who ever gets on to that roof steps straight over
    them - a two-course drop is not a wall. Making them tall is cheap; the flood is what settles
    whether it was necessary.
    """
    n = 0
    # ...AND THEY RUN THE WHOLE LOT. Written as `range(0, 3)` they closed the composition's own
    # three columns, which was the whole lot when the lot was six deep. With an approach in front
    # of the gate they have to close that too, or the walk is a corridor with both sides open and
    # the containment the flood proves is gone.
    for u in (0, du - 1):
        for v in range(0, L.dv):
            for y in range(0, CANOPY + 2):
                mat = pal["plinth"] if y in (0, CANOPY + 1) else pal["pier"]
                n += bool(L.put(v, u, y, mat, raw=True))
            n += bool(L.put(v, u, CANOPY + 2, pal["trim_slab"], raw=True, type="bottom",
                            waterlogged="false"))
    return {"cells": n}


def _queue(L: _Lot, p: dict, pal: dict, du: int) -> dict:
    """Stanchion rails and a lit canopy, in the two courses of forecourt there are.

    THE QUEUE WEAVES, IT DOES NOT SWITCH BACK. A switchback needs four bands and the apron has
    two, so a walker is put through both: the gate's own PILASTERS close V2 on the six-grid, and a
    rail stub closes V1 three cells later. That is what a stanchion line does at small scale, it
    is what reads as a queue, and it costs no block that is not already architecture.

    **THE TWO MUST NEVER LAND ON THE SAME COLUMN.** A pilaster and a rail together close both
    bands and cut the forecourt in half, which is a queue nobody can walk - so the rails sit at
    `u % 6 == 3` and the pilasters at `u % 6 == 0`, and the containment flood is what would catch
    it if they ever met.

    The rails stop clear of the two lane approaches, the portico and the towers, so the last
    stretch to a door is open - a queue you cannot leave at the front is a trap, not a queue.
    """
    keep = _keep_clear(p)
    # THE CANOPY KEEPS LESS CLEAR THAN THE RAILS DO, and that distinction is the difference
    # between a canopy and four bus shelters. A roof five courses up over a lane approach is
    # exactly where a queue wants one; a RAIL there is what would stop you reaching the door.
    roof_keep = set(range(p["arch"][0] - 1, p["arch"][1] + 2))
    for cu in p["towers"]:
        roof_keep.update(range(cu - 4, cu + 5))
    # The weave: a pilaster already closes V2 at every sixth column, so a rail closes V1 three
    # cells later and V2 again two cells after that. Never on a pilaster column - that would close
    # both bands and cut the forecourt in half, which is a queue nobody can walk.
    rails = 0
    for u in range(3, du - 3):
        if u in keep or _is_pier(u):
            continue
        band = 1 if u % 6 == 3 else (2 if u % 6 == 1 else None)
        if band is None:
            continue
        # A STANCHION IN BAND 1 REACHES BACK TO BAND 2, or it is a fence post standing alone.
        # It used to touch the sea wall at the composition's own V0; with the gate set back
        # behind an approach the sea wall is thirteen columns away, and four rails came off as
        # single-cell components - which a connectivity check sees and a render does not, because
        # `render3d` draws a fence as a full cube. Band 2 already reaches the gate's front face.
        rails += bool(L.put(band, u, 0, pal["post"], **_fence_props(True)))
        if band == 1:
            rails += bool(L.put(2, u, 0, pal["post"], **_fence_props(True)))

    # THE CANOPY. Posts stand ON the sea wall, never in the queue: a post in the walked band is
    # an obstacle the rails already provide. The beam spans V0..V3 so it lands on the gate
    # building at the far end, and the roof is a course of slab over both walked bands.
    posts = beams = roof = 0
    for u in range(6, du - 5, 6):
        if u in roof_keep:
            continue
        for y in range(2, CANOPY):
            posts += bool(L.put(0, u, y, pal["post"], **_fence_props(False)))
        for v in range(0, 4):
            beams += bool(L.put(v, u, CANOPY, pal["beam"]))
        L.lamp(1, u, CANOPY - 1, pal["light"], hanging="true", waterlogged="false")
        L.lamp(2, u, CANOPY - 1, pal["light"], hanging="true", waterlogged="false")
    for u in range(4, du - 4):
        if u in roof_keep or u % 6 == 0:
            continue
        for v in (1, 2):
            roof += bool(L.put(v, u, CANOPY, pal["roof"], type="bottom", waterlogged="false"))
        # the eave, so the canopy has an edge rather than stopping in mid-air
        roof += bool(L.put(0, u, CANOPY, pal["eave"], facing=V_IN, half="bottom",
                           shape="straight", waterlogged="false"))
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
#
# THE COURSE SCHEDULE, written once. Every band is a LINE across the whole 61 rather than a
# scatter - the deck soffit's lesson, which shipped 215 grid runs of which 184 were one or two
# cells. A number that appears in two of these functions is a number that drifts, so they are
# module constants and the tests read them from here.

DADO = 2            # y0..y2: the solid front face a fare slot and a door are cut into
PANEL = (3, 6)      # the RECESSED bay panel - V3 is left OPEN here and V4 carries the field
STRING = 7          # the string course, red, the whole width
UPPER = (8, 11)     # the upper wall
CORNICE = 12        # ...and its cornice, which PROJECTS into V2
PARAPET = 13
MERLON = 14
PORTICO_TOP = 9     # the ceremonial opening runs y0..y9 at V3-V4
GRILLE_TOP = 5      # ...and is barred y0..y5 at V5, with a tympanum of stone over it
ATTIC = (15, 19)    # the raised block over the portico that breaks the roof line
TOWER_TOP = 23      # the towers' own crown course
CANOPY = 5          # the queue canopy's soffit


def _keep_clear(p: dict) -> set:
    """Where the forecourt must stay open: the lane approaches, the portico, the tower feet."""
    keep = set()
    for lane in p["lanes"]:
        keep.update(range(lane - 2, lane + 3))
    keep.update(range(p["arch"][0] - 1, p["arch"][1] + 2))
    for cu in p["towers"]:
        keep.update(range(cu - 3, cu + 4))     # the tower's own base, at V2
    return keep


def _is_pier(u: int) -> bool:
    return u % 6 == 0


def _course(pal: dict, u: int, y: int, pier: bool) -> str:
    """What material a cell of the wall takes. ONE function, so a band cannot come out two-toned
    the way the deck soffit's weathering did when it was hashed on the course instead of the
    cell."""
    if y in (0, CORNICE, MERLON):
        return pal["plinth"]
    if y == STRING:
        return pal["band"]
    if y == PARAPET:
        return pal["trim"]
    if y <= DADO:
        return pal["pier"] if pier else pal["trim"]
    return pal["pier"] if pier else pal["field"]


def _building(L: _Lot, p: dict, pal: dict, du: int) -> dict:
    """V3..V5, the whole 61, solid but for two door portals and one barred portico.

    **A THREE-DEEP WALL FILLED SOLID IS A SLAB, AND IT RENDERED AS ONE.** The first build was
    exactly that - one plane of field with a pier tone every six and a red line across it - and
    from every bearing it read as a long low wall rather than as a gate. What makes voxels read as
    architecture is relief and openings, so the bays are RECESSED: at a bay column V3 is left open
    from `PANEL[0]` to `PANEL[1]` and the field stands at V4, which buys a cell of real shadow the
    whole length of the front.

    **THE DADO UNDER IT IS NOT DECORATION.** The machine lives at V4 in those very columns, so a
    recess reaching the floor would put a comparator and a redstone torch on show from the queue.
    Solid to `DADO`, and the only opening cut in it is the fare slot.

    The piers then PROJECT, one cell into V2, so the front is a colonnade rather than a plane. A
    pilaster is also what closes V2 on the six-grid, which is half of what marshals the queue.
    """
    lanes, arch = p["lanes"], p["arch"]
    open_u = set(lanes)
    portico = set(range(arch[0], arch[1] + 1))
    n = 0

    for u in range(du):
        pier = _is_pier(u)
        in_portico = u in portico
        in_lane = u in open_u
        for y in range(0, MERLON + 1):
            for v in (3, 4, 5):
                if in_lane and y <= 1:
                    continue                              # the turnstile portal
                if in_portico and v in (3, 4) and y <= PORTICO_TOP:
                    continue                              # the ceremonial opening
                if in_portico and v == 5 and y <= PORTICO_TOP:
                    continue                              # ...and its grille and tympanum
                if (not pier) and v == 3 and PANEL[0] <= y <= PANEL[1] and not in_portico:
                    continue                              # the recessed bay panel
                n += bool(L.put(v, u, y, _course(pal, u, y, pier)))
        # the pilaster: the pier's own projection into the forecourt, plinth to string course
        if pier and not in_portico:
            for y in range(0, STRING + 1):
                n += bool(L.put(2, u, y, _course(pal, u, y, True)))
            n += bool(L.put(2, u, STRING + 1, pal["trim_slab"], type="bottom",
                            waterlogged="false"))
            L.lamp(2, u, STRING - 2, pal["light"], hanging="false", waterlogged="false")
        # THE CORNICE PROJECTS, and an upside-down stair is what makes it a cornice rather than a
        # painted line. Its tall side is its `facing`, so it leans back INTO the wall it grows
        # from - the rule `gen/enrich.py` states, asserted rather than eyeballed because this
        # repo's renderer draws both directions identically.
        n += bool(L.put(2, u, CORNICE, pal["trim_stair"], facing=V_IN, half="top",
                        shape="straight", waterlogged="false"))
    return {"cells": n, "cornice_y": CORNICE, "panel": list(PANEL)}


def _portal(L: _Lot, p: dict, pal: dict, lane: int) -> dict:
    """One turnstile lane: the reveal, the iron door, and the arch over it.

    The door is in the MIDDLE band, V4, so it is recessed a course from the front and a course
    from the back: a gate you walk INTO rather than past, and the reveal is what carries the fare
    slot and the lane's own lanterns.
    """
    n = 0
    for du_ in (-1, 1):                       # the jambs, both courses - one of them is what the
        for y in (0, 1):                      # machine's torch strongly powers
            n += bool(L.put(4, lane + du_, y, pal["pier"]))
    # THE HEAD CARRIES THE LAND'S ACCENT AND A LAMP EACH SIDE, which is the vocabulary
    # `gen/park_frontage.py` established over every attraction spur in the park: an ENTRANCE takes
    # the accent across its head and a lamp either side, an EXIT takes neither, because at twenty
    # blocks the word is unreadable and the shape is not. This is the park's front door, so it is
    # the grandest member of that family rather than a different language.
    n += bool(L.put(3, lane, 2, pal["band"]))                 # the read face
    for v in (4, 5):
        n += bool(L.put(v, lane, 2, pal["chisel"]))
    for du_ in (-1, 1):
        n += bool(L.put(3, lane + du_, 2, pal["trim_stair"],
                        facing=U_PLUS if du_ < 0 else U_MINUS,
                        half="bottom", shape="straight", waterlogged="false"))
    # THE DOOR. `facing` is the way it opens - into the park - and both halves ship SHUT and
    # UNPOWERED, which is the state the machine puts them in at rest.
    for y, half in ((0, "lower"), (1, "upper")):
        n += bool(L.put(5, lane, y, pal["door"], facing=V_IN, half=half, hinge="left",
                        open="false", powered="false"))
    L.lamp(3, lane - 1, 3, pal["light"], hanging="false", waterlogged="false")
    L.lamp(3, lane + 1, 3, pal["light"], hanging="false", waterlogged="false")
    return {"cells": n}


def _portico(L: _Lot, p: dict, pal: dict) -> dict:
    """The ceremonial arch: nine wide, ten tall, open at V3-V4, and BARRED at V5.

    **YOU SEE THE PARK AND YOU CANNOT WALK INTO IT.** That is the whole idea, and it is what makes
    a paywall an experience rather than an obstruction: the vista down the axis - the carousel, the
    wheel and the railway beyond - is framed by an arch and closed by a grille you look straight
    through. The park's own apron lamp stands inside it, on the axis, because `Park Ways` put it
    there and this design does not move other people's furniture.

    The grille stops at `GRILLE_TOP` and stone carries the rest. Barred to the crown it is ninety
    iron bars - about thirty-four ingots - for four courses nobody looks through, and iron is the
    scarce metal on this island.
    """
    a0, a1 = p["arch"]
    ax = int(p["axis"])
    n = 0
    door_u = set(int(v) for v in p["lanes"])
    for u in range(a0, a1 + 1):
        for y in range(0, GRILLE_TOP + 1):
            if u in door_u and y <= 1:
                continue
            n += bool(L.put(5, u, y, pal["grille"], north="true", south="true",
                            east="false", west="false", waterlogged="false"))
        for y in range(GRILLE_TOP + 1, PORTICO_TOP + 1):
            n += bool(L.put(5, u, y, pal["field"]))       # the tympanum behind the arch
    # the arch head: the land's accent across the read face - the same entrance grammar as every
    # attraction gantry in the park, nine cells of it rather than three - over a chiselled soffit,
    # with a springer either side leaning into the opening.
    for u in range(a0, a1 + 1):
        n += bool(L.put(3, u, PORTICO_TOP + 1, pal["band"]))
        for v in (4, 5):
            n += bool(L.put(v, u, PORTICO_TOP + 1, pal["chisel"]))
    for v in (3, 4):
        n += bool(L.put(v, a0 - 1, PORTICO_TOP, pal["trim_stair"], facing=U_PLUS, half="bottom",
                        shape="straight", waterlogged="false"))
        n += bool(L.put(v, a1 + 1, PORTICO_TOP, pal["trim_stair"], facing=U_MINUS, half="bottom",
                        shape="straight", waterlogged="false"))
    # THE ATTIC: a raised block over the arch, so the roof line has a middle as well as two ends.
    # A parapet that runs level for sixty-one cells is a wall however tall it is.
    for u in range(a0 - 2, a1 + 3):
        for v in (3, 4, 5):
            for y in range(ATTIC[0], ATTIC[1] + 1):
                if y in (ATTIC[0], ATTIC[1]):
                    mat = pal["plinth"]
                elif u in (a0 - 2, a1 + 2):
                    mat = pal["pier"]
                else:
                    mat = pal["field"]
                n += bool(L.put(v, u, y, mat))
        if (u - ax) % 2 == 0:
            n += bool(L.put(3, u, ATTIC[1] + 1, pal["plinth"]))
            n += bool(L.put(5, u, ATTIC[1] + 1, pal["plinth"]))
    # the roundel, on the attic and on the axis: a red field ringed in chiselled stone
    for du_ in range(-2, 3):
        n += bool(L.put(3, ax + du_, ATTIC[0] + 2, pal["band"]))
    for du_ in (-3, 3):
        n += bool(L.put(3, ax + du_, ATTIC[0] + 2, pal["chisel"]))
    for du_ in (-2, -1, 0, 1, 2):
        mat = pal["chisel"] if abs(du_) == 2 else pal["band"]
        n += bool(L.put(3, ax + du_, ATTIC[0] + 1, mat))
        n += bool(L.put(3, ax + du_, ATTIC[0] + 3, mat))
    for u in range(a0, a1 + 1, 2):
        L.lamp(3, u, PORTICO_TOP, pal["light"], hanging="true", waterlogged="false")
    return {"cells": n}


def _towers(L: _Lot, p: dict, pal: dict) -> dict:
    """Two towers, so the gate has a SILHOUETTE rather than a roof line.

    The first pair were four wide and five courses over the cornice, and they read as chimneys. A
    tower is a mass that goes to the GROUND: these are seven wide, they project into V2 with the
    pilasters, they carry a lit belfry stage with an opening on the front face, and they are
    crenellated - the one crown treatment this repo has measured as reading from the ground.
    """
    n = 0
    belfry = (TOWER_TOP - 7, TOWER_TOP - 5)
    for cu in p["towers"]:
        for u in range(cu - 3, cu + 4):
            edge = u in (cu - 3, cu + 3)
            for v in (2, 3, 4, 5):
                for y in range(0, TOWER_TOP):
                    if v == 2 and y > TOWER_TOP - 4:
                        continue                          # the shaft sets back above the belfry
                    if (not edge) and v == 3 and belfry[0] <= y <= belfry[1]:
                        continue                          # the belfry opening
                    if y in (0, CORNICE, belfry[0] - 1):
                        mat = pal["plinth"]
                    elif y == STRING:
                        mat = pal["band"]
                    else:
                        mat = pal["pier"] if edge else pal["field"]
                    n += bool(L.put(v, u, y, mat))
        for u in range(cu - 4, cu + 5):
            for v in (2, 3, 4, 5):
                n += bool(L.put(v, u, TOWER_TOP, pal["plinth"]))
            if (u - cu) % 2 == 0:
                for v in (2, 5):
                    n += bool(L.put(v, u, TOWER_TOP + 1, pal["plinth"]))
        for du_ in (-2, 2):
            L.lamp(2, cu + du_, belfry[0], pal["light"], hanging="false", waterlogged="false")
    return {"cells": n, "top": TOWER_TOP}


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
        s*5  dust threshold cell (for a one-item fare, comparator level 1 reaches it)
        s*6  dust the threshold's near cell
        s*7  comparator, reading the till at its back
        s*8  the TILL, and the mouth one course over it

    Everything is at course y0 except the mouth and the jamb T1 strongly powers, and that is what
    makes one torch open both halves of the door: `emit` reaches the lower half beside it, and a
    lit torch STRONGLY POWERS THE BLOCK ABOVE IT, which is the jamb beside the upper half.
    """
    price = int(p["price_level"])
    if price < 1:
        raise ValueError("price_level must be at least 1")

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
    cells += bool(L.put(4, till, 1, "chest", facing=V_OUT, type="single",
                        waterlogged="false"))
    # the slot: a hole in the front face at the mouth's own course, so a visitor reaches through
    # the wall rather than walking round it. The cell is cleared rather than never placed,
    # because the wall loop has already run.
    L.clear(3, till, 1)
    cells += bool(L.put(3, till, 2, pal["chisel"]))
    return {
        "lane": lane, "side": side,
        "door": (5, lane, 0), "door_upper": (5, lane, 1),
        "till": (4, till, 0), "mouth": (4, till, 1), "slot": (3, till, 1),
        "torches": [(4, t1, 0), (4, t0, 0)],
        "threshold": [(4, u, 0) for u in dust],
        "comparator": (4, comp, 0),
        "cells": cells,
    }


# --------------------------------------------------------------------------- the words

def _signs(L: _Lot, p: dict, pal: dict, mach: list, du: int) -> int:
    """What the gate has to say, and it says the price because a house that will not print its
    odds does not know them. Fifteen characters a line, asserted rather than eyeballed.

    **EVERY ONE OF THEM HANGS IN THE DADO**, which is the only band of the front face that is
    solid all the way along. The first pass hung the title over the portico and the lane plates in
    the recessed bay panels - both of them columns with an OPENING in them, which is the exact
    failure `gen/park.py` records four kinds shipping: a wall sign floating in air draws exactly
    like one on a wall. `_Lot.sign` refuses rather than places, so they came back as a count of
    two instead of six and nothing else said a word.
    """
    price = price_blocks(int(p["price_level"]))
    a0, a1 = p["arch"]
    n = 0
    n += L.sign(2, a0 - 3, DADO, V_OUT, (p["title"], "", "MAIN GATE", ""), (3, a0 - 3, DADO))
    n += L.sign(2, a1 + 3, DADO, V_OUT, ("ONE FARE", f"{price} GRASS", "PAY AT A LANE", ""),
                (3, a1 + 3, DADO))
    for m in mach:
        lane = m["lane"]
        n += L.sign(2, lane, DADO, V_OUT, ("CLICK TO ENTER", f"{price} GRASS", "FROM INVENTORY", ""),
                    (3, lane, DADO))
        slot_u = m["slot"][1]
        n += L.sign(2, slot_u, DADO, V_OUT, ("PAY HERE", f"{price} GRASS", "RECEIPT CHEST", ""),
                    (3, slot_u, DADO))
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
    # THE CANVAS IS SIZED OFF THE COURSE SCHEDULE, never off a number typed twice: the towers
    # are the tallest thing here and a canvas an inch short CROPS them, which `_Lot.put`
    # would report as a refusal and nothing else would notice.
    top = TOWER_TOP + 2
    c = Canvas(dv, top + 1, du)
    L = _Lot(c, dv, du, mask, front=int(p.get("front", 0)))
    if int(p.get("front", 0)) + 6 > dv:
        raise ValueError(f"the gate sets back {p['front']} into a lot only {dv} deep - the "
                         f"composition is six columns and would be cropped")

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
                "door": _world(c, m["door"], L.front),
                "door_upper": _world(c, m["door_upper"], L.front),
                "till": _world(c, m["till"], L.front),
                "mouth": _world(c, m["mouth"], L.front),
                "payment_chest": _world(c, m["mouth"], L.front),
                "receipt_hopper": _world(c, m["till"], L.front),
                "comparator": _world(c, m["comparator"], L.front),
                "torches": [_world(c, t, L.front) for t in m["torches"]],
                "threshold": [_world(c, t, L.front) for t in m["threshold"]],
            }
            for m in mach
        ],
        "outputs": [_world(c, m["door"], L.front) for m in mach],
        "lights": L.lights,
        "signs": L.signs,
        "outside_lot_refused": L.outside,
        "ground_layer_refused": L.ways,
        "ground_layer_checked": mask is not None,
        "detail": detail,
        "adapter_contract": {
            "trigger": "right-click either CLICK TO ENTER sign",
            "debit": {"item": "grass_block", "count": 1, "from": "player inventory"},
            "deposit": "put the debited grass into that lane's payment_chest",
            "success_probe": "wait until that grass reaches the receipt_hopper below the chest",
            "success": "open both halves of that lane's iron door for 5 seconds",
            "reset": "move the receipt grass to the park collection store and close the door",
            "failure": "if debit or hopper receipt fails, keep the door closed and refund once",
        },
        "contract": (
            f"a sealed arrival compound at the park's void edge: a visitor spawns at "
            f"X{spawn['world'][0]} Y{spawn['world'][1]} Z{spawn['world'][2]} facing east and "
            f"cannot reach any other land on foot until the sign adapter debits {price} grass, "
            "deposits it in the lane chest, observes it in the receipt hopper, and opens both "
            "halves of that lane's iron door for five seconds"),
        "hazards": [],
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


def _world(c: Canvas, cell, front: int = 0) -> list:
    """A composition cell as world coordinates - AND THE SET-BACK IS PART OF THE ADDRESS.

    `_Lot.put` adds `front` to every composition cell, so the machine's own `(v, u, y)` is local
    to the composition and not to the lot. Read without it, every world coordinate this design
    publishes was thirteen blocks west of the block it names: the meta said the till stood at
    X97504 and the hopper is at X97517.

    That is invisible in every check this repo has - the build audits clean, the circuit
    simulates, the containment floods, and a render draws the machine exactly where it is. The
    one consumer that cannot look is the SERVER PAYMENT ADAPTER, which is handed these numbers to
    debit a fare against, and it would have been pointed at the middle of the forecourt.
    """
    v, u, y = cell
    ox, oy, oz = c.world_origin
    return [ox + int(v) + int(front), oy + int(y), oz + int(u)]


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
