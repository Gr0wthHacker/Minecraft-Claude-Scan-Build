"""THE PARK LINE: a double-track circuit down the park's outer edge, and three island stations.

**IT IS A RIDE, NOT A UTILITY.** The corridor it runs in is the one strip of the 200x600 envelope
with the park on one side and open void on the other, so the whole point of the thing is the view
off the outer edge.

**AND IT IS SYMMETRIC, BECAUSE THAT IS WHAT WAS WRONG WITH IT.** Jack, on the first line: *"they
look decent but are a little asymettric with the hanging facade which is a bit strange."* Measured
off the block list rather than off a render - `render3d` draws a fence, a wall and a chain as full
cubes and has hidden six separate faults on this park - the old section was eight columns deep with
the track at V177, which puts the deck's own centre line on V175.5. **Every hanging thing on it was
therefore half a block off the axis of the structure it hung from**: the canopy was a six-column
roof on an eight-column deck with an eave on ONE side and two bare columns on the other, and the
portal frames spanned all eight columns and hung a single lantern at V175. 10,232 of the old
design's 22,362 cells had no mirror image across its own corridor.

The cure is not to move the lantern. It is that **a viaduct with one track has no axis to be
symmetric about**, so the section is now odd-width with a real centre column, two running lines
mirrored about it, and an ISLAND platform between them:

    k0   parapet, the park face
    k1   kerb
    k2   TRACK A          - the UP line, running toward +U
    k3   platform edge, dark - the boarding edge, and where the signal plinth stands
    k4   |
    k5   |
    k6   |
    k7   | THE ISLAND: the promenade for six hundred blocks, the platform where a station
    k8   |              stands, and the three centre columns carry the flight down
    k9   |
    k10  |
    k11  platform edge, dark
    k12  TRACK B          - the DOWN line, running toward -U
    k13  kerb
    k14  parapet, the void face

`k` counts AWAY FROM THE PARK, so the section mirrors whichever side the park is on; `park_side`
is the only thing that decides it and `_section` is the one place the columns are named.

**WHY TWO TRACKS AND NOT A BLOCK SYSTEM.** One track the length of the corridor with three stations
on it is a line on which two carts can meet head-on, and the only cure for that is redstone: a
detector rail holding a cart out of a section until the section ahead is clear. Redstone is the
thing in this project whose wrongness is invisible in every render, every audit and every bill of
materials - so a mechanism that has to be right is a mechanism that has to be simulated, and one
that is right BY CONSTRUCTION is worth more than one that is right by simulation. Two running
lines, one direction each, joined only at the two ends, cannot present two carts to each other on
the same rails at all. It costs SEVEN extra columns of corridor and four iron rails.

**THE TWO ENDS ARE TURNBACK CURVES, AND THAT IS WHAT THE CORNERS BUY.** Jack: *"if needed we can
add turns curves etc, just not excessive, we can invest iron for aesthetic clear value purpose."*
Four corners - two at each end - join the up line to the down line, so the whole railway is ONE
CLOSED CIRCUIT: a cart set going calls at all six platform bays and comes back to where it started
without anyone lifting it off the track. Before this it was an out-and-back on a single line with a
buffer at each end. Four corners is the cheapest possible purchase of that:

    rail          6 iron -> 16 rails    0.375 iron each   - iron is the SCARCE metal here
    powered_rail  6 gold ->  6 rails    1.0   gold each   - and gold is farmable

so the four turnback rails are **1.5 iron ingots** and every other running rail on the line is
gold. The six detector rails at the platforms are 1 iron each. Nothing else in the track is iron.

THE RAIL RULES, and every one of them is CORRECTNESS rather than taste. Read off `blocks.json`
rather than remembered, and asserted in `tests/test_parkrail.py` because **our renderer draws a
wrong rail orientation identically to a right one**:

    powered_rail  shape = north_south, east_west, ascending_{n,s,e,w}
    rail          shape = ...those six, PLUS south_east, south_west, north_west, north_east

  * **A POWERED RAIL CANNOT CURVE**, so every direction change costs a plain - and therefore IRON -
    rail. The budget is four, and they are the two turnbacks.
  * **NEVER DESCEND INTO A CORNER.** A curve has no ascending shape, so a corner and both of its
    neighbours must share one height, or the game re-derives the turn as a slope and the line dead
    ends. This circuit is dead level, so the rule costs it nothing - and `shapes_for` is shared with
    `railspiral` and `transit` so that one implementation enforces it for all three.
  * **AN UNPOWERED POWERED_RAIL IS A BRAKE.** The bed cell under the track becomes a
    `redstone_block` every `power_every`, and the sources are dealt **per RUN between breaks** -
    a corner is a plain rail and a detector rail is a plain rail, and neither propagates the chain.
    A flat spacing leaves a dead rail past every one of them, and a dead rail is a cart stopped in
    mid-air. Nothing about the emitted model looks wrong when this is missed: `shape` and `powered`
    are DERIVED by the game, so the schematic, the audit and the bill of materials all pass while
    the line does not run. It is verified by SIMULATION in `mcbuild.circuit`.
  * **A TRACK CELL IS NEVER OPTIONAL.** A cell that cannot be placed is an error naming the cell,
    never a silent skip: a broken line still audits as one clean solid.
  * **A CLOSED CIRCUIT HAS NO TERMINUS, so it needs no stop block.** The rule that a terminus needs
    one at both ends is not relaxed here, it is inapplicable - and the stronger property replaces
    it: `test_the_line_is_one_closed_circuit` asserts every rail has exactly two rail neighbours
    and that the whole ring is one cycle, which is a thing a line with a missing cell cannot be.

**THE BRAKE IS WHAT MAKES IT A RAILWAY RATHER THAN A LOOP OF TRACK, AND IT IS AUTOMATIC NOW.** A
continuously powered line cannot be boarded - the cart never stops. Each of the six platform bays
therefore holds a stretch of powered rail with **no source of its own**, so an arriving cart brakes
on it and stops ON THE PLATFORM whatever anybody does. That is the whole of the auto-stop, and it
needs no redstone at all: an unpowered powered rail halves a cart's speed every tick.

What the old design got wrong was the RELEASE. It was a LEVER, and a lever is a state: left up, the
bay is live and no cart ever stops there again - the one failure a station must not have. It is a
momentary **button** on a plinth at the platform edge now. The button strongly powers the plinth,
the plinth is horizontally adjacent to the rail, and a powered rail carries its own state eight
rails each way - which is why `bay_half` must stay under eight, so ONE button lights the whole bay
from wherever in it the cart came to rest. When the button pops out the bay is dead again, by
itself, ready for the next cart. **The default is stop, and there is no way to leave it running.**

The geometry of the quiet band is arithmetic and it is the fiddly part. A bay `bay_half` cells each
side of its centre must go dead, and a source reaches eight rails, so sources are suppressed across
`[c - h - 8, c + h + 8]` and FORCED at `c - h - 9` and `c + h + 9`. Those two shoulders then cover
every quiet cell except the `2h+1` in the middle, which is exactly the bay. Move `bay_half` and the
arithmetic moves with it; `_sources` is the one place it is written. (The old file wrote the same
band as `[c - 2h, c + 2h]`, which gives `4h - 15` dead cells - equal to `2h + 1` only at `h = 8`.
It was correct for the one value it had and silently wrong for every other, which is what a comment
saying "move it and the arithmetic moves with it" is supposed to prevent.)

**AND EVERY PLATFORM RINGS.** A `detector_rail` at each bay's own approach end - one per track, so
they mirror - stands beside a `bell` on the platform edge. A detector rail powers what is next to
it, so there is no wire anywhere: a cart entering the platform rings the bell. It is the one thing
on the line that tells a walker on the promenade that a train is coming, and it costs one iron
ingot and no dust.
"""
from __future__ import annotations

import math

from .. import blocks as _blocks
from .canvas import Canvas, hash01
from .railspiral import shapes_for

SIGN_WIDTH = 15                     # a sign line clips mid-word past this

#: The viaduct's own masonry, per land. NOT a second copy of `parkways.LANDS`: that table is
#: chosen for PAVING read from above, and a viaduct wants a value ladder read from the SIDE, where
#: the arch ring has to draw a curve against the spandrel behind it. Every ring/spandrel pair here
#: is >= 45 luminance apart, measured ACROSS material families - inside one family a ladder cannot
#: exist by construction, which is the mistake this repo has now made four times.
#:
#:     frontier    polished_blackstone_bricks 45  <  stone_bricks 122
#:     midway      polished_blackstone_bricks 45  <  smooth_stone 159
#:     prismworks  black_wool 21  <  polished_blackstone_bricks 45  <  deepslate_tiles 76
#:
#: `deck`, `pier` and `spandrel` are the BULK and are cheap-tier on purpose; `kerb`, `ring` and
#: `accent` are the small parts that may be `ok`. Prismworks reads as deepslate without being
#: BUILT of it: `polished_deepslate` and `deepslate_tiles` are both ok-tier, and a third of a
#: 600-block viaduct made of them would put the whole design over its material policy.
SPAN = {
    "frontier": {
        "deck": "stone_bricks", "kerb": "polished_blackstone_bricks", "pier": "stone_bricks",
        "spandrel": "stone_bricks", "ring": "polished_blackstone_bricks",
        "weather": "cracked_stone_bricks", "band": "chiseled_stone_bricks",
        "wall": "spruce_planks",
        "parapet": "stone_brick_wall", "post": "spruce_fence", "beam": "spruce_planks",
        "roof": "spruce_slab", "eave": "spruce_stairs", "tread": "stone_brick_stairs",
        "accent": "spruce_planks", "light": "lantern", "wood": "spruce",
        "screen": "spruce_trapdoor",
    },
    "midway": {
        "deck": "smooth_stone", "kerb": "polished_blackstone_bricks", "pier": "stone_bricks",
        "spandrel": "stone_bricks", "ring": "polished_blackstone_bricks",
        "weather": "chiseled_stone_bricks", "band": "red_wool", "wall": "smooth_stone",
        "parapet": "stone_brick_wall", "post": "oak_fence", "beam": "white_wool",
        "roof": "stone_slab", "eave": "stone_brick_stairs", "tread": "stone_brick_stairs",
        "accent": "red_wool", "light": "lantern", "wood": "oak",
        "screen": "oak_trapdoor",
    },
    "prismworks": {
        # THE DECK YOU WALK ON IS THE PAVING THE LAND PAVES ITSELF WITH - `parkways` gives
        # Prismworks `polished_deepslate`, so the promenade twelve courses up is the same stone as
        # the spine underneath it. Only the surface: the pier, spandrel and ring behind it are
        # cheap-tier blackstone, because a third of a viaduct built out of an ok-tier block would
        # put the whole design over its material policy on its own.
        "deck": "polished_deepslate", "kerb": "deepslate_tiles",
        "pier": "polished_blackstone_bricks", "spandrel": "polished_blackstone_bricks",
        "ring": "black_wool", "weather": "blackstone", "band": "cyan_wool",
        "wall": "polished_blackstone_bricks",
        "parapet": "polished_blackstone_brick_wall", "post": "polished_blackstone_brick_wall",
        "beam": "polished_deepslate", "roof": "polished_deepslate_slab",
        "eave": "polished_deepslate_stairs", "tread": "polished_deepslate_stairs",
        "accent": "cyan_wool", "light": "soul_lantern", "wood": "dark_oak",
        "screen": "iron_bars",
    },
}

#: The one light that costs no metal. A flush froglight IS the floor - an opaque emitter a course
#: down, so it reaches 14 rather than 15 - which is this island's own idiom and, on a walkway a
#: hundred blocks long over open void, the only lamp nobody can knock off. A LANTERN IS AN IRON
#: INGOT AND A CHAIN IS ANOTHER, so the viaduct's own rhythm of light - one in every portal beam,
#: one in every other arch crown, one in every pier lintel - is froglight set into the masonry, and
#: the iron is spent only where a light has to HANG: the six station canopies and the three station
#: doors, which are the three places a visitor stands still.
FLUSH_LIGHT = "ochre_froglight"

PARKRAIL = {
    # THE CORRIDOR, and nothing may leave it. v0, u0, v1, u1. The width must be ODD and at least
    # 13: an even-width deck has no centre column, and a viaduct with no centre column has no axis
    # for its canopy, its portals and its hanging lights to be symmetric about - which is the whole
    # complaint this section was rebuilt to answer.
    "bounds": [0, 0, 14, 599],
    "lands": None,                 # [{name, u0, u1}] in U order; the gaps between them are reaches
    "park_side": 1,                # +1: the park is toward higher V. -1 for the rim corridor.
    "deck_y": 12,                  # the deck FLOOR course. You stand, and the rails sit, at +1
    "ground_y": 1,                 # the first course above the park's lawn - see the module note
    "bay": 15,                     # pier to pier
    "pier_u": 3,                   # pier thickness along U
    "spring_y": 4,                 # the arch springing course
    "crown_gap": 2,                # courses of masonry between the arch crown and the deck
    "gate_k": 5,                   # columns cut off EACH face of every pier - two passages
    "gate_h": 4,                   # ...and how many courses tall
    "portal_every": 4,             # a portal frame every this many bays
    "power_every": 8,              # a redstone_block in the bed this often, per RUN
    "light_every": 12,             # a froglight flush in each platform-edge kerb this often
    "arch_light_every": 2,         # a froglight in the crown rib every this many bays
    # HALF THE DEAD ZONE AT A PLATFORM, IN RAILS - so the bay is 2*bay_half + 1 cells long and a
    # cart brakes to a stop inside it. It MUST stay under 8, because the release button powers one
    # rail and a powered rail carries its own state at most eight rails each way: at 8 or more the
    # button would light only part of its own bay and a cart could be left stranded in the far half
    # of the platform it is trying to leave.
    "bay_half": 3,
    "track_inset": 3,              # cells of deck beyond each turnback, for the end walls
    "stations": None,              # [{at_u, land, title, board, stair}]
    "station_half": 13,            # platform half-length; the platform is 2*half + 1
    # THE ENTRY, and it is the difference between a station and a fire escape. Jack, on the first
    # three: "the railway needs clear entry ways (stairs); and proper lead up platforms etc."
    "stair_w": 3,                  # V columns of flight - two is a service stair, not a way in
    "head_half": 5,                # the forecourt at the foot, half-length along U
    "head_v": 8,                   # ...and how far it reaches into the arcade from the park face
    "canopy_h": 5,                 # courses from the deck walk up to the canopy soffit
    "band_blend": 30,              # cells over which one land's masonry dithers into the next
    "seed": 0,
}

STATION = {
    "at_u": None,
    "land": None,
    "title": "STATION",
    "board": None,                 # up to four lines on the departure board
    "stair": 1,                    # +1/-1: which way along U the stair descends
}

_NORTH, _SOUTH, _WEST, _EAST = "north", "south", "west", "east"


def _u_dir(sign: int) -> str:
    """A direction along U. Canvas z is U, and +z is SOUTH."""
    return _SOUTH if sign > 0 else _NORTH


def _v_dir(sign: int) -> str:
    """A direction across V. Canvas x is V, and +x is EAST."""
    return _EAST if sign > 0 else _WEST


def _sides(p: dict) -> tuple:
    """(side, park_edge, void_edge) - WHICH WAY THE PARK IS, from the corridor.

    In the 200-deep envelope the void is at the HIGH edge: V0 is the arrival apron against the
    connector and V170-199 is the rim and void reserve. A viaduct that gets this the wrong way
    round puts the island, the platforms and every station stair against the void and a visitor
    descends into the reserve - and NOTHING IN AN AUDIT CAN SEE IT, because a mirrored viaduct is
    one connected piece with no placement problem and the same bill of materials.

    So the side is a parameter, `park_side`: +1 when the park lies toward higher V, -1 when it lies
    toward lower V (the rim corridor). Every column is then named as an offset AWAY from the park
    (`_section`), so the whole cross-section mirrors with one number.
    """
    v0, _u0, v1, _u1 = p["bounds"]
    side = 1 if int(p.get("park_side", 1)) >= 0 else -1
    return (side, v1, v0) if side > 0 else (side, v0, v1)


def _section(p: dict) -> dict:
    """THE CROSS-SECTION, NAMED ONCE. Every column of the deck, derived from the corridor alone.

    `k` counts away from the park face, so `at(k) = park_edge - side * k` and the whole section
    mirrors when `park_side` does. The width must be ODD: the centre column is the axis the canopy,
    the portal lights, the ridge and the flight are all built about, and an even-width deck has
    none - which is exactly why the first version of this line had every hanging fixture half a
    block off the structure it hung from.
    """
    v0, u0, v1, u1 = p["bounds"]
    w = v1 - v0 + 1
    side, park_edge, void_edge = _sides(p)
    if w < 13 or w % 2 == 0:
        raise ValueError(
            f"parkrail needs an ODD corridor at least 13 deep for two tracks and an island "
            f"between them; got {w}")
    stair_w = max(3, int(p.get("stair_w", 3)))
    if stair_w % 2 == 0:
        raise ValueError("stair_w must be odd, or the flight cannot sit on the island's own axis")
    island = [park_edge - side * k for k in range(4, w - 4)]
    if len(island) < stair_w + 2:
        raise ValueError(
            f"the island is {len(island)} wide and the flight is {stair_w}: the promenade could "
            f"not get past its own stairwell")
    kc = (w - 1) // 2
    centre = park_edge - side * kc
    h = (stair_w - 1) // 2
    # THE ARCADE'S TWO PASSAGES, one off each face, with the pier's own core between them. `gate_k`
    # is how many columns each passage takes; the core is what is left, and it must be wide enough
    # to carry the flight's stringer, which lands on the island's own centre columns.
    gk = max(2, int(p.get("gate_k", 5)))
    if 2 * gk + stair_w > w:
        raise ValueError(
            f"gate_k {gk} twice over leaves a pier core narrower than the {stair_w}-wide flight "
            f"that has to stand in it")
    return {
        "side": side, "w": w, "v0": v0, "v1": v1,
        "park": park_edge - side * 0,
        "kerb_a": park_edge - side * 1,
        "track_a": park_edge - side * 2,
        "edge_a": park_edge - side * 3,
        "island": island,
        "edge_b": park_edge - side * (w - 4),
        "track_b": park_edge - side * (w - 3),
        "kerb_b": park_edge - side * (w - 2),
        "void": void_edge,
        "centre": centre,
        "inner_a": island[0], "inner_b": island[-1],
        "stair_v": tuple(park_edge - side * k for k in range(kc - h, kc + h + 1)),
        "gate_k": gk,
        "gate_cols": tuple(park_edge - side * k
                           for k in list(range(gk)) + list(range(w - gk, w))),
        "gate_lamps": (park_edge - side * (gk // 2), park_edge - side * (w - 1 - gk // 2)),
    }


def _span(a: int, b: int, step: int):
    """The inclusive run from `a` to `b`, whichever direction `step` points."""
    return range(a, b + step, step)


# ---------------------------------------------------------------------------- the track


def plan(params: dict) -> list:
    """THE CIRCUIT for a config: the one entry point the build and the tests both go through.

    Written twice they drift - `railspiral`'s own tests once called `route` without a ground table,
    got a terminus the design does not have, and reported a missing stop block on a line that has
    one. Same rule `proportions.measure` and `rubric.score` already follow.

    Returns [(x, y, z, is_corner)] in CANVAS coordinates, which is `railspiral`'s own cell shape,
    so `shapes_for` applies to it unchanged. The list is a CLOSED RING in travel order, and it
    starts on a straight so that the wrap between the last cell and the first needs no special
    case in `shapes_for` (both are straights on the same leg, and `_loop_shapes` supplies the wrap
    for the four corners that do need it).
    """
    p = {**PARKRAIL, **(params or {})}
    v0, u0, v1, u1 = p["bounds"]
    sec = _section(p)
    inset = int(p["track_inset"])
    y = int(p["deck_y"]) + 1
    xa, xb = sec["track_a"] - v0, sec["track_b"] - v0
    za, zb = inset, (u1 - u0) - inset
    if zb - za < 8:
        raise ValueError("parkrail needs a corridor long enough for a circuit")
    if xa > xb:
        xa, xb = xb, xa
    lo, hi = min(za, zb), max(za, zb)
    cells = []
    # the UP line, on the park side, running toward +U
    for z in range(lo + 1, hi):
        cells.append((xa, y, z, False))
    cells.append((xa, y, hi, True))                       # turnback corner, far end
    for x in range(xa + 1, xb):
        cells.append((x, y, hi, False))
    cells.append((xb, y, hi, True))
    # the DOWN line, on the void side, running toward -U
    for z in range(hi - 1, lo, -1):
        cells.append((xb, y, z, False))
    cells.append((xb, y, lo, True))                       # turnback corner, near end
    for x in range(xb - 1, xa, -1):
        cells.append((x, y, lo, False))
    cells.append((xa, y, lo, True))
    return cells


def _loop_shapes(cells: list) -> list:
    """`shapes_for`, closed. A ring's first and last cells are neighbours and the shared
    implementation cannot know that, so it is handed one cell of context at each end and the
    padding is thrown away. Written without this, the two turnback corners at the ring's seam come
    out as straights - a shape the game would derive as a dead end, and one our renderer draws
    exactly like a corner."""
    ring = [cells[-1]] + list(cells) + [cells[0]]
    return shapes_for(ring)[1:-1]


def _runs(n: int, breaks) -> list:
    """Index ranges of consecutive POWERED cells. A corner is a plain rail and a detector rail is a
    plain rail; neither propagates the powered chain, so power is dealt per run - a flat spacing
    leaves a dead rail past every one of them."""
    breaks = set(breaks)
    out, start = [], None
    for i in range(n):
        if i in breaks:
            if start is not None:
                out.append((start, i))
            start = None
        elif start is None:
            start = i
    if start is not None:
        out.append((start, n))
    return out


def _sources(n: int, every: int, bays: list, half: int, breaks=()) -> tuple:
    """(source indices, quiet indices) for the track's BED.

    A source is a `redstone_block` under a powered rail. Everything about this function is the
    brake: a platform needs a stretch of track that is DEAD, and a powered rail carries its own
    state eight rails past a source, so "dead" is a statement about a neighbourhood rather than
    about one cell.

    THE BAND IS `[c - half - 8, c + half + 8]` AND THE SHOULDERS ARE FORCED AT `c +/- (half + 9)`.
    Each shoulder then covers the eight quiet cells nearest it, which leaves exactly the `2*half+1`
    in the middle dead - the bay, centred on the platform, for any `half`. The previous version
    wrote the band as `[c - 2h, c + 2h]`, which leaves `4h - 15` dead: right for h=8 and quietly
    wrong for every other value, under a docstring promising it moved with the parameter.

    `breaks` are cells that are not powered rails at all, and they bound the runs sources are
    dealt within - a source cannot reach past one.
    """
    breaks = set(breaks)
    quiet, forced = set(), set()
    for c in bays:
        for i in range(c - half - 8, c + half + 9):
            if 0 <= i < n and i not in breaks:
                quiet.add(i)
        for i in (c - half - 9, c + half + 9):
            if 0 <= i < n and i not in breaks:
                forced.add(i)
    picks = set()
    for a, b in _runs(n, breaks):
        picks |= {i for i in forced if a <= i < b}
        for i in (a, b - 1):
            if i not in quiet:
                picks.add(i)
        last = None
        for i in range(a, b):
            if i in quiet:
                continue
            if i in picks:
                last = i
                continue
            if last is None or i - last >= max(1, every):
                picks.add(i)
                last = i
    return picks, quiet


# ---------------------------------------------------------------------------- the build


class _Deck:
    """The corridor's frame. Everything is placed through it, so an axis bug is one bug."""

    def __init__(self, c: Canvas, p: dict):
        self.c, self.p = c, p
        self.v0, self.u0, self.v1, self.u1 = p["bounds"]
        self.sx, self.sz = self.v1 - self.v0 + 1, self.u1 - self.u0 + 1
        self.deck_y = int(p["deck_y"])
        self.walk_y = self.deck_y + 1
        self.ground_y = int(p["ground_y"])
        self._state: dict = {}

    # -- materials -------------------------------------------------------
    def blk(self, name: str) -> int:
        if name not in self._state:
            self._state[name] = self.c.state(name)
        return self._state[name]

    def put(self, v: int, y: int, u: int, name: str, **props) -> bool:
        """One cell, in corridor coordinates. Refuses anything outside the corridor."""
        x, z = v - self.v0, u - self.u0
        if not (0 <= x < self.sx and 0 <= z < self.sz):
            return False
        blk = self.c.raw_state(name, **props) if props else self.blk(name)
        return self.c.put(x, y, z, blk)

    def has(self, v: int, y: int, u: int) -> bool:
        return self.c.solid(v - self.v0, y, u - self.u0)

    def clear(self, v: int, y: int, u: int) -> None:
        """Cut a cell back to air.

        A STAIRWELL IS A HOLE, AND A HOLE HAS TO BE CUT. The deck is laid across the whole
        corridor before a station exists, so a flight descending through it walks into a ceiling
        unless the courses over every tread are taken back out - and a buried flight audits as one
        clean solid with nothing to say about it.
        """
        self.c.put(v - self.v0, y, u - self.u0, 0)

    def name_at(self, v: int, y: int, u: int) -> str:
        return self.c.get_name(v - self.v0, y, u - self.u0).split(":")[-1]

    def raw_at(self, v: int, y: int, u: int) -> int:
        return self.c.get(v - self.v0, y, u - self.u0)

    def sign(self, v: int, y: int, u: int, facing: str, wood: str, lines) -> bool:
        """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.

        THE SUPPORT IS CHECKED, NOT ASSUMED. Four of the park's seven building kinds once shipped
        a sign hung on the one column that has an opening in it, and the mistake is invisible in
        every render: a wall sign floating in air draws exactly like one on a wall. A caller that
        ignores a False here is asking for that bug back.
        """
        dv = {"east": 1, "west": -1}.get(facing, 0)
        du = {"south": 1, "north": -1}.get(facing, 0)
        if not self.has(v - dv, y, u - du):
            return False
        if not self.put(v, y, u, f"{wood}_wall_sign", facing=facing, waterlogged="false"):
            return False
        text = [str(t)[:SIGN_WIDTH] for t in list(lines)[:4]]
        self.c.sign_text(v - self.v0, y, u - self.u0, front=text, colour="white", glowing=True)
        return True


def _land_table(p):
    """(pal_a, pal_b, t) at a U: inside a land t is 0, and across a reach it ramps.

    A HARD SEAM ACROSS A LONG SPAN READS AS TWO VIADUCTS STACKED - the Lowland Stair's finding, and
    the reason its bands dither per CELL rather than per course. The reaches here are the same
    reaches `parkways` grades its paving across, so the viaduct changes material exactly where the
    ground under it does.
    """
    lands = p["lands"]
    if not lands:
        raise ValueError("parkrail needs params.lands = [{name, u0, u1}, ...] in U order")
    for land in lands:
        if land["name"] not in SPAN:
            raise ValueError(f"unknown land {land['name']!r}; have {sorted(SPAN)}")

    def at(u: int):
        for land in lands:
            if land["u0"] <= u <= land["u1"]:
                pal = SPAN[land["name"]]
                return pal, pal, 0.0
        for a, b in zip(lands, lands[1:]):
            if a["u1"] < u < b["u0"]:
                t = (u - a["u1"]) / max(1, b["u0"] - a["u1"])
                return SPAN[a["name"]], SPAN[b["name"]], t
        pal = SPAN[lands[0]["name"]] if u < lands[0]["u0"] else SPAN[lands[-1]["name"]]
        return pal, pal, 0.0

    def land_name(u: int) -> str:
        for land in lands:
            if land["u0"] <= u <= land["u1"]:
                return land["name"]
        for a, b in zip(lands, lands[1:]):
            if a["u1"] < u < b["u0"]:
                return a["name"] if (u - a["u1"]) <= (b["u0"] - u) else b["name"]
        return lands[0]["name"] if u < lands[0]["u0"] else lands[-1]["name"]

    return at, land_name


def _intrados(i: int, span: int, spring_y: int, crown_y: int) -> int:
    """The underside course of the arch ring, `i` cells into an opening `span` wide.

    A sine gives a segmental arch that springs cleanly at both piers and is flat across its crown,
    which at ten cells and three courses of rise is the only profile that reads as an arch rather
    than as a staircase. `math.floor(x + 0.5)` and NOT `round`: `round` is banker's rounding, and
    the last generator that forgot it built a lump out of eighteen one-wide towers.
    """
    f = math.sin(math.pi * (i + 0.5) / max(1, span))
    return spring_y + int(math.floor((crown_y - spring_y) * f + 0.5))


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PARKRAIL, **cfg}
    v0, u0, v1, u1 = p["bounds"]
    sx, sz = v1 - v0 + 1, u1 - u0 + 1
    sec = _section(p)
    seed = int(p["seed"])
    deck_y, ground_y = int(p["deck_y"]), int(p["ground_y"])
    walk_y = deck_y + 1
    canopy_y = walk_y + int(p["canopy_h"])
    c = Canvas(sx, canopy_y + 4, sz)
    d = _Deck(c, p)
    pal_at, land_name = _land_table(p)
    side = sec["side"]
    track_a, track_b = sec["track_a"], sec["track_b"]
    centre = sec["centre"]

    def pick(pal_a, pal_b, t, key, v, u):
        """One material, dithered across a reach. A hard line is two viaducts butted together."""
        return pal_b[key] if hash01(v, u, seed + 17) < t else pal_a[key]

    stations = [{**STATION, **s} for s in (p["stations"] or [])]
    for s in stations:
        if s["at_u"] is None:
            raise ValueError("a parkrail station needs at_u")
        s["land"] = s["land"] or land_name(s["at_u"])
        if s["land"] not in SPAN:
            raise ValueError(f"unknown land {s['land']!r}; have {sorted(SPAN)}")

    half = int(p["station_half"])
    platform_u = set()
    for s in stations:
        platform_u |= set(range(s["at_u"] - half, s["at_u"] + half + 1))

    # ------------------------------------------------------------------ 1. piers and arches
    #
    # A PIER IS A BUILDING, NOT A COLUMN OF ONE BLOCK. Base course, weathered shaft, cap: three
    # bands, and the weathering hash is on the CELL. Hashed on the COURSE instead, every block in
    # a course comes out identical and the shaft is horizontal stripes - which the deck soffit
    # shipped once and nothing in any render said a word about.
    bay, pier_u = int(p["bay"]), int(p["pier_u"])
    span_w = bay - pier_u
    spring_y, crown_y = int(p["spring_y"]), deck_y - 1 - int(p["crown_gap"])
    gate_h = int(p["gate_h"])
    gate_cols, gate_lamps = sec["gate_cols"], sec["gate_lamps"]
    piers = gates = 0
    lights = 0
    for b0 in range(u0, u1 + 1, bay):
        piers += 1
        for u in range(b0, min(b0 + pier_u, u1 + 1)):
            for v in range(v0, v1 + 1):
                for y in range(ground_y, deck_y):
                    a, bb, t = pal_at(u)
                    if y == ground_y:
                        key = "kerb"
                    elif y == deck_y - 1:
                        key = "band"           # the cornice - see the arch below
                    elif hash01(v, y * 977 + u, seed + 31) < 0.16:
                        key = "weather"
                    else:
                        key = "pier"
                    d.put(v, y, u, pick(a, bb, t, key, v, u))
            # A PIER EVERY FIFTEEN BLOCKS IS A WALL EVERY FIFTEEN BLOCKS. Left solid, the ground
            # under the viaduct is forty separate rooms and the strip is dead; cut through, it is
            # a six-hundred-block arcade under a six-hundred-block promenade, which is two walks
            # for the price of one and the cheapest thing in this design.
            #
            # AND THE CUT HAS TO REACH THE PARK FACE. Taken out of the pier's middle it is a
            # tunnel with a solid wall at each end of it: perfectly walkable once you are inside,
            # and there is nowhere on six hundred blocks that you can get inside.
            #
            # **SO IT IS TWO PASSAGES AND A CORE, NOT ONE OPENING.** One band cut from the park
            # face is the obvious answer and it is the single biggest asymmetry a viaduct of this
            # section can have: measured, one 10-wide cut through 40 piers left 441 more cells on
            # the void half of the deck than on the park half and put every pier's remaining leg
            # on one side. A band off EACH face, with the pier's own core standing between them,
            # reaches the park face just as well, gives the arcade a second lane at the piers
            # where the station aprons take the first one, and mirrors exactly.
            for v in gate_cols:
                for y in range(ground_y, ground_y + gate_h):
                    d.clear(v, y, u)
                a, bb, t = pal_at(u)
                # THE LINTEL IS THE LAMP. The arcade's own crown lights are eleven courses over
                # a head walking it, so the passage came out a dark tunnel with a lit ceiling.
                # A froglight in the lintel costs no metal, cannot be knocked off, and is the
                # only fixture in a doorway that nobody can walk into. One per passage, which is
                # a mirrored pair.
                hit = v in gate_lamps
                d.put(v, ground_y + gate_h, u,
                      FLUSH_LIGHT if hit else pick(a, bb, t, "band", v, u))
                lights += 1 if hit else 0
        gates += 1
        # the arch between this pier and the next: a RING on each visible face, the spandrel it
        # carries above it, and a cross-rib at the crown that ties the two faces into a vault
        for i in range(span_w):
            u = b0 + pier_u + i
            if u > u1:
                break
            a, bb, t = pal_at(u)
            ys = _intrados(i, span_w, spring_y, crown_y)
            for v in (v0, v1):
                d.put(v, ys, u, pick(a, bb, t, "ring", v, u))
                for y in range(ys + 1, deck_y):
                    # A CORNICE IS WHAT SEPARATES AN ARCADE FROM THE THING IT CARRIES. Without one
                    # the spandrel runs straight into the deck edge and eleven courses of masonry
                    # read as a single grey slab with notches cut in the bottom of it.
                    key = "band" if y == deck_y - 1 else (
                        "weather" if hash01(v, y * 977 + u, seed + 31) < 0.12 else "spandrel")
                    d.put(v, y, u, pick(a, bb, t, key, v, u))
            if ys == crown_y:                      # the crown: a rib right through the depth
                for v in range(v0 + 1, v1):
                    d.put(v, crown_y, u, pick(a, bb, t, "ring", v, u))

    # ...and a froglight in the crown rib of every other arch, ON THE CENTRE COLUMN, so the arcade
    # below is lit and the elevation has a rhythm read from the lawn as well as from the deck. It
    # replaces the lantern-on-a-chain the first line hung here: a lantern is an iron ingot and a
    # chain is another, and this one is set into masonry that is already being placed.
    for k, b0 in enumerate(range(u0, u1 + 1, bay)):
        if k % max(1, int(p["arch_light_every"])):
            continue
        u = b0 + pier_u + span_w // 2
        if u > u1 or u in platform_u:
            continue
        if d.has(centre, crown_y, u) and d.put(centre, crown_y, u, FLUSH_LIGHT):
            lights += 1

    # ------------------------------------------------------------------ 2. the deck
    #
    # A DECK OF ONE MATERIAL FOR SIX HUNDRED BLOCKS IS A FLOOR, NOT A WALK. That is exactly the
    # complaint the ground layer was rebuilt to answer - "massive amounts of the same stone, no
    # patterns" - and a promenade seven wide and six hundred long is the easiest place in the park
    # to make it again. Two rhythms, both derived from something real rather than drawn on: a
    # transverse rung in the land's own band over EVERY PIER, so the walk shows you the structure
    # under it, and a dotted kerb inlay down the island, MIRRORED about the centre column.
    kerbs = {v0, v1, sec["kerb_a"], sec["kerb_b"], sec["edge_a"], sec["edge_b"]}
    inlay = {sec["island"][1], sec["island"][-2]}
    pier_cols = {u for b0 in range(u0, u1 + 1, bay) for u in range(b0, b0 + pier_u)}
    cells = plan(p)
    cross_u = {cells[0][2] + u0 - 1 + 0 for _ in (0,)}          # placeholder, filled below
    cross_u = {z + u0 for (_x, _y, z, corner) in cells if corner}
    for u in range(u0, u1 + 1):
        a, bb, t = pal_at(u)
        for v in range(v0, v1 + 1):
            if v in kerbs:
                key = "kerb"
            elif v in (track_a, track_b):
                key = "deck"
            elif u in pier_cols:
                key = "band"
            elif v in inlay and (u - u0) % 4 == 0:
                key = "kerb"
            else:
                key = "deck"
            d.put(v, deck_y, u, pick(a, bb, t, key, v, u))
        # THE LIGHT IS THE DECK, NOT A FIXTURE ON IT. A flush froglight costs no metal, cannot be
        # knocked off a walkway twelve courses over the lawn, and leaves the deck clear to walk.
        # A PAIR, one in each platform-edge kerb, because a single one on a symmetric section is
        # the very fault this line was rebuilt to fix.
        if (u - u0) % max(1, int(p["light_every"])) == 0 and u not in platform_u \
                and u not in cross_u:
            for v in (sec["edge_a"], sec["edge_b"]):
                if d.put(v, deck_y, u, FLUSH_LIGHT):
                    lights += 1

    # ------------------------------------------------------------------ 3. the track
    shapes = _loop_shapes(cells)
    index = {(x, z): i for i, (x, y, z, _c) in enumerate(cells)}
    corners = [i for i, cell in enumerate(cells) if cell[3]]
    dead_half = int(p["bay_half"])
    if dead_half >= 8:
        raise ValueError(
            "bay_half must stay under 8: a powered rail carries its own state eight rails past a "
            "source, so a longer bay could not be lit end to end by its own release button")

    # THE SIX PLATFORM BAYS AND THE SIX APPROACH DETECTORS, one of each per track per station, so
    # they mirror. The detector sits `dead_half + 10` cells back along the direction of travel:
    # that is exactly far enough that the powered run RESTARTING after it begins on the forced
    # shoulder at `c - (dead_half + 9)`, so the detector costs the bay nothing and the dead zone
    # stays centred on the platform. Move it one cell nearer and the run's own start source lands
    # inside the band, lights half the bay, and the cart stops off-centre - which no render, no
    # audit and no bill of materials could see.
    bays, detectors, bay_meta = [], [], []
    for s in stations:
        for (tv, adir) in ((track_a, 1), (track_b, -1)):
            zc = s["at_u"] - u0
            i = index.get((tv - v0, zc))
            if i is None:
                raise ValueError(f"station {s['title']} at u={s['at_u']} is off the running line")
            j = index.get((tv - v0, zc - adir * (dead_half + 10)))
            if j is None:
                raise ValueError(f"station {s['title']} has no room for its approach detector")
            bays.append(i)
            detectors.append(j)
            bay_meta.append({"title": s["title"], "track": "a" if tv == track_a else "b",
                             "at_u": s["at_u"], "detector_u": cells[j][2] + u0})

    breaks = set(corners) | set(detectors)
    picks, quiet = _sources(len(cells), int(p["power_every"]), bays, dead_half, breaks)
    for i, (x, y, z, corner) in enumerate(cells):
        # THE BED FIRST, and the bed IS the railway: an unpowered powered rail is a brake, so a
        # `redstone_block` here is not decoration. A source is NEVER wasted on a break - a plain
        # rail does not propagate the chain, so a block under one powers exactly itself.
        if i in picks and i not in breaks:
            bed = c.state("redstone_block")
        else:
            bed = _bed_block(d, pal_at, pick, x + v0, z + u0)
        if not c.put(x, y - 1, z, bed):
            raise ValueError(f"parkrail: track bed cell {i} fell outside the corridor")
        if corner:
            rail = c.raw_state("rail", shape=shapes[i], waterlogged="false")
        elif i in detectors:
            rail = c.raw_state("detector_rail", shape=shapes[i], powered="false",
                               waterlogged="false")
        else:
            rail = c.raw_state("powered_rail", shape=shapes[i], powered="true",
                               waterlogged="false")
        # A TRACK CELL IS NOT OPTIONAL: an error naming the cell, never a silent skip.
        if not c.put(x, y, z, rail):
            raise ValueError(f"parkrail: track cell {i} fell outside the corridor")

    # ------------------------------------------------------------------ 4. parapets and portals
    #
    # NOTHING IS A FULL-BLOCK PILLAR WHERE A SLIM BLOCK WILL DO. A parapet is a wall course, a
    # portal's legs are walls, and the only full blocks above the deck are the portal beam and the
    # station masonry - which are lintels and buildings, not posts.
    seats = 0
    for u in range(u0, u1 + 1):
        a, bb, t = pal_at(u)
        for v in (v0, v1):
            # A NEWEL OVER EVERY PIER. A wall course is a railing; six hundred blocks of one is a
            # line. What turns it into a balustrade is a post where the structure under it says
            # there should be one, which is the same argument the deck's own transverse rungs make
            # one course down - the rhythm is READ OFF the viaduct, never drawn on it.
            if u in pier_cols:
                d.put(v, walk_y, u, pick(a, bb, t, "band", v, u))
                d.put(v, walk_y + 1, u, pick(a, bb, t, "parapet", v, u))
            else:
                d.put(v, walk_y, u, pick(a, bb, t, "parapet", v, u))
        # A PROMENADE SIX HUNDRED BLOCKS LONG NEEDS SOMEWHERE TO SIT, AND IT SITS IN PAIRS. A
        # bench's backrest is its `facing` - a stair's TALL side IS its facing - so the pair backs
        # on to the island's own centre and each half looks out over its own track and its own
        # edge. Written as one bench on one side, which is what the first line had, the promenade
        # is lopsided every twenty-four blocks for six hundred blocks.
        if (u - u0) % 24 == 12 and u not in platform_u and u not in pier_cols and u not in cross_u:
            for v, f in ((sec["inner_a"], _v_dir(-side)), (sec["inner_b"], _v_dir(side))):
                if d.put(v, walk_y, u, pal_at(u)[0]["eave"], facing=f, half="bottom",
                         shape="straight"):
                    seats += 1

    # the corridor's two end walls, across the full width, behind the turnbacks
    for u in (u0, u1):
        a, bb, t = pal_at(u)
        for v in range(v0, v1 + 1):
            d.put(v, walk_y, u, pick(a, bb, t, "band", v, u))
            d.put(v, walk_y + 1, u, pick(a, bb, t, "parapet", v, u))

    portals = lanterns = 0
    for k, b0 in enumerate(range(u0, u1 + 1, bay)):
        u = b0 + pier_u // 2
        if k % max(1, int(p["portal_every"])) or u in platform_u or u > u1:
            continue
        a, bb, t = pal_at(u)
        beam = pick(a, bb, t, "beam", v0, u)
        for v in (v0, v1):
            for y in range(walk_y, canopy_y):
                d.put(v, y, u, pick(a, bb, t, "post", v, u))
        for v in range(v0, v1 + 1):
            d.put(v, canopy_y, u, beam)
        # THE LIGHT IS IN THE BEAM AND ON THE AXIS. A lantern on a chain here was one iron ingot
        # and one chain per portal, hung one cell off the deck's own centre line because the deck
        # had no centre line. Set into the beam's middle block it is free, it cannot be knocked
        # off, and it is exactly on the axis the portal is symmetric about.
        if d.put(centre, canopy_y, u, FLUSH_LIGHT):
            lights += 1
        portals += 1

    # ------------------------------------------------------------------ 5. the stations
    built = []
    for s in stations:
        built.append(_station(d, p, s, sec, canopy_y, dead_half))
        lanterns += built[-1]["lanterns"]

    c.meta = {
        "kind": "parkrail",
        "bounds": list(p["bounds"]),
        "park_side": side,
        "track_a": track_a, "track_b": track_b, "centre_v": centre,
        "island": [sec["island"][0], sec["island"][-1]],
        "rail_y": walk_y, "deck_y": deck_y,
        "track_cells": len(cells), "corners": len(corners),
        "iron_rails": len(corners) + len(detectors),
        "detector_rails": len(detectors),
        "power_sources": len(picks - breaks), "brake_zones": len(bays), "quiet_cells": len(quiet),
        "bay_half": dead_half,
        "closed_circuit": True,
        "piers": piers, "pier_gates": gates, "portals": portals,
        "flush_lights": lights, "lanterns": lanterns, "deck_seats": seats,
        "stations": [{"title": s["title"], "land": s["land"], "at_u": s["at_u"]} for s in stations],
        "station_detail": built,
        "bay_detail": bay_meta,
        "runs": [list(r) for r in _runs(len(cells), breaks)],
        "contract": "TWO one-way running lines the length of the corridor, joined at both ends by "
                    "turnback curves into ONE CLOSED CIRCUIT, so two carts can never meet head-on; "
                    "three island stations, each with a dead bay on each track that stops an "
                    "arriving cart by itself and a momentary button that releases it; a detector "
                    "rail and a bell at each bay's approach - and not one cell outside V%d-%d"
                    % (v0, v1),
    }
    return c


def _bed_block(d: _Deck, pal_at, pick, v: int, u: int) -> int:
    """The bed under a track cell: the deck that is already there, or the deck's own material.

    THE DECK IS LAID FIRST AND THE TURNBACK CROSSES IT. At the two ends the track runs ACROSS the
    corridor, over the island's own paving, and rewriting those cells with the track's material
    would draw a stripe of plain deck through the platform-edge kerb and the inlay. Whatever is
    there is kept whenever it is a full block, which is what a rail needs and what the deck always
    lays; only a cell with nothing under it falls back to the material.
    """
    cur = d.name_at(v, d.deck_y, u)
    if cur not in ("OOB", "air") and _blocks.is_full_cube(cur):
        return d.raw_at(v, d.deck_y, u)
    a, bb, t = pal_at(u)
    return d.blk(pick(a, bb, t, "deck", v, u))


# ---------------------------------------------------------------------------- a station


def _head(d: _Deck, p: dict, sec: dict, pal: dict, title: str, step: int, foot: int) -> int:
    """THE LEAD-UP AT THE FOOT OF A FLIGHT, under the viaduct.

    Jack: "the railway needs clear entry ways (stairs); and proper lead up platforms etc." What
    was there was a two-wide flight ending on the lawn in the gap between two piers - correct,
    walkable, and indistinguishable from a maintenance ladder. **A WAY IN HAS TO BE VISIBLE FROM
    THE PLACE YOU ARE STANDING BEFORE YOU KNOW THE STATION IS THERE**, which on this line is the
    arcade under the deck, six hundred blocks of it, every bay identical by design.

    So the foot gets a room: a raised apron across the arcade's walkable width, a kerb round it so
    it reads as a platform rather than as paving, a portal frame with a lintel across the bay you
    walk in through, lanterns on the jambs and the station's name at head height on the pier.

    **THE APRON MAY NOT REACH THE WHOLE WIDTH.** It is a raised course, so anything it covers is a
    step up rather than a walk-through, and the arcade is a six-hundred-block walk that has to get
    past it. `head_v` therefore stops short of the pier gate's far column, and the lane that is
    left is the one the arcade uses at a station - asserted, because a severed arcade is invisible
    in every render and the flood that was supposed to catch it was reading absolute V against a
    model-indexed map and passing on every design ever put through it.
    """
    side = sec["side"]
    park_edge = sec["park"]
    gy = d.ground_y
    hh = max(2, int(p.get("head_half", 5)))
    hv = max(2, int(p.get("head_v", 8)))
    inner = park_edge - side * hv                  # how far the apron reaches into the arcade
    lanterns = 0

    # -- the apron: one course of the land's own paving, banded on the flight's own rhythm -------
    # **THE APRON MAY NOT WRITE OVER THE FLIGHT IT SERVES.** It reaches to `foot + hh`, and the
    # flight's own bottom tread is at `foot` - so laid unconditionally it repaved the last tread
    # and the stair came out eleven steps for a twelve-course rise, which is a flight you walk up
    # to a wall. Nothing in the audit sees that: eleven treads are as legal as twelve.
    # THE APRON REACHES THE DOOR, because the door STANDS ON IT. Ended one row short, the
    # portal's two jambs began a course above bare lawn and both came away as fourteen-cell
    # strays - they had been held on only by the kerb course, which was removed for sealing the
    # arcade. A thing that carries something else has to reach under it.
    door = foot + step * (hh + 1)
    lo_u, hi_u = min(foot - hh, door), max(foot + hh, door)
    for u in range(lo_u, hi_u + 1):
        for k in range(hv + 1):
            v = park_edge - side * k
            if d.has(v, gy, u):
                continue
            # the apron's own edge is drawn HERE, as the end rows of the paving itself
            key = ("kerb" if u in (lo_u, hi_u)
                   else "band" if (u - foot) % 4 == 0 or k == hv else "deck")
            d.put(v, gy, u, pal[key])

    # -- the portal you walk in through: jambs, a lintel, and a light on each jamb ---------------
    #
    # A LINTEL IS WHAT MAKES AN OPENING READ AS A DOOR. The void tower settled this - regularity
    # and openings, not damage - and the arcade already has forty identical arches, so the one you
    # are meant to walk through has to say so with something the others do not have.
    head = gy + 4
    for v in (park_edge, inner):
        for y in range(gy + 1, head):
            d.put(v, y, door, pal["post"])
    for k in range(hv + 1):
        d.put(park_edge - side * k, head, door, pal["beam"])
    # A LANTERN ON A JAMB HAS NOTHING TO STAND ON. Placed beside the doorway at head height it
    # was floating in the opening - five of them, and the audit said so on the first build. They
    # hang from the LINTEL, which is the one solid thing over an opening by definition. A PAIR,
    # mirrored about the doorway's own middle.
    for k in (1, hv - 1):
        if d.put(park_edge - side * k, head - 1, door, pal["light"],
                 hanging="true", waterlogged="false"):
            lanterns += 1

    # -- the name, at head height on the jamb, read walking UP the arcade toward the station -----
    # A wall sign hangs off the block behind it, so this sits one cell out from the jamb facing
    # away from it - which is the direction a visitor is coming from.
    d.sign(park_edge, head - 1, door + step, _u_dir(step), pal["wood"],
           [title, "PARK LINE", "PLATFORM ABOVE", ""])

    # -- and the flight's own bottom step flares into the apron ---------------------------------
    for v in sec["stair_v"]:
        if not d.has(v, gy, foot + step):
            d.put(v, gy, foot + step, pal["band"])
    return lanterns


def _station(d: _Deck, p: dict, s: dict, sec: dict, canopy_y: int, dead_half: int) -> dict:
    """One station: an ISLAND platform between the two running lines, and a flight down from it.

    THE THREE STATIONS ARE THREE PLACES, NOT ONE STATION PAINTED THREE COLOURS. Each takes its own
    land's masonry, its own post, its own roof material and its own light - the same argument
    `parkways` makes for its lamps, which is that a land is told apart by what its street furniture
    is MADE of as much as by its paving, and a station is the object a visitor stands inside.

    **AND IT IS AN ISLAND, WHICH IS WHAT MAKES IT SYMMETRIC.** The first version put the platform
    on one side of a single track and hung a canopy over it with an eave on one edge only - a roof
    whose mass was entirely to one side of a deck that had no centre column to be on the wrong side
    of. Between two running lines there is only one place a platform can be, and everything on it
    is built as a mirrored pair about the centre: posts on both edges, an eave over both tracks, a
    ridge on the axis, lanterns in pairs, a bench pair, a name sign on each face of one pylon, and
    a departure board read from each approach.

    **THE STAIR IS THE ISLAND'S OWN THREE CENTRE COLUMNS AND THAT IS THE WHOLE SITING DECISION.**
    A flight cut anywhere else would pinch the promenade to one cell for its own length; taken out
    of the middle, two columns of walk survive on each side of it, the canopy already roofs it, and
    it lands under the viaduct in the arcade a visitor is already walking.
    """
    pal = SPAN[s["land"]]
    deck_y, walk_y = d.deck_y, d.walk_y
    half = int(p["station_half"])
    ac = int(s["at_u"])
    side = sec["side"]
    track_a, track_b = sec["track_a"], sec["track_b"]
    edge_a, edge_b = sec["edge_a"], sec["edge_b"]
    isl, centre = sec["island"], sec["centre"]
    inner_a, inner_b = sec["inner_a"], sec["inner_b"]
    stair_v = sec["stair_v"]
    cols = [edge_a] + list(isl) + [edge_b]
    mid = (len(cols) - 1) // 2                       # the roof's own axis, and the island's
    lanterns = screens = 0

    # THE FLIGHT FIRST, as a SET of cells, because everything else has to keep out of it. Written
    # the other way round - roof, pylon, then carve - the carve has to guess which of its own
    # courses were somebody else's, and a station whose pylon crosses its own stairwell is
    # invisible in every render.
    step = 1 if int(s["stair"]) >= 0 else -1
    ascend = _u_dir(-step)                          # a flight ascends TOWARD the platform
    rise = walk_y - d.ground_y
    stair = {ac + step * (half - rise + 1 + k): deck_y - k for k in range(rise)}
    if half < rise:
        raise ValueError("a parkrail station platform is shorter than its own flight")

    # -- the platform floor: the land's own deck with a banded inlay, so it reads as a room -----
    for u in range(ac - half, ac + half + 1):
        for v in cols:
            key = "kerb" if v in (edge_a, edge_b) else ("band" if (u - ac) % 4 == 0 else "deck")
            d.put(v, deck_y, u, pal[key])

    # -- the canopy: slim posts on BOTH platform edges, a slab roof, an eave over EACH track -----
    for u in range(ac - half, ac + half + 1):
        if (u - ac) % 5 == 0 and u != ac:
            for v in (edge_a, edge_b):
                for y in range(walk_y, canopy_y):
                    d.put(v, y, u, pal["post"])
        # **A ROOF IS PITCHED OR IT IS A LID**, and a lid is exactly what the first flat plate of
        # slabs read as in the round: one plane, one tone, no shadow anywhere on it. Two courses
        # of rise over four columns each side, mirrored about the axis - eave, eave, mid, mid,
        # RIDGE, mid, mid, eave, eave - which is a shallow gable rather than a staircase, and it
        # is the ridge that catches the light and gives the canopy a line down its own length.
        end = u in (ac - half, ac + half)
        for i, v in enumerate(cols):
            j = abs(i - mid)
            inward = _v_dir(-side) if i < mid else _v_dir(side)
            if j == 0:
                d.put(v, canopy_y + 2, u, pal["band"])    # the ridge beam, ON THE AXIS
                continue
            # **A STEPPED ROOF ONLY HOLDS TOGETHER IF THE STEPS OVERLAP.** A slab at (v, y) and a
            # slab at (v+1, y+1) share no face - they are DIAGONAL - so a plain staircase of
            # courses comes out as one detached ribbon per course. Built that way this canopy
            # shipped as 27 separate components with a clean audit and zero placement problems,
            # which is the ear-tip failure in a roof. The riser column therefore carries a cell in
            # BOTH courses: a stair leaning up toward the ridge, with the flat above it.
            if j in (1, 3):
                d.put(v, canopy_y + (1 if j == 1 else 0), u, pal["eave"], facing=inward,
                      half="bottom",
                      shape="straight")
            if j == 1 and end:
                # THE GABLE, and it is where the land's `screen` earns its keep - an OPEN trapdoor
                # is the vertical slab this game never shipped. It stands beside the ridge beam,
                # which is a full block in its own course, so the support a trapdoor and a pane of
                # bars both want is there by construction. A run of them between two posts is not.
                if pal["screen"] == "iron_bars":
                    ok = d.put(v, canopy_y + 2, u, "iron_bars")
                else:
                    ok = d.put(v, canopy_y + 2, u, pal["screen"], facing=_u_dir(1), half="bottom",
                               open="true", powered="false", waterlogged="false")
                screens += 1 if ok else 0
            else:
                d.put(v, canopy_y + (2 if j == 1 else 1 if j <= 3 else 0), u,
                      pal["roof"], type="bottom")
        # the eave leans OUT over its own track, which is what makes a canopy read as shelter
        # rather than as a lid: a stair's TALL side IS its `facing`, so an eave sheltering a track
        # has its tall side toward the roof it grows from and steps down over the rails.
        d.put(track_a, canopy_y, u, pal["eave"], facing=_v_dir(-side), half="bottom",
              shape="straight")
        d.put(track_b, canopy_y, u, pal["eave"], facing=_v_dir(side), half="bottom",
              shape="straight")
        if (u - ac) % 5 == 2 and u not in stair:
            # a bench PAIR, backs to the island's own centre, each half looking out over its track
            for v, f in ((inner_a, _v_dir(-side)), (inner_b, _v_dir(side))):
                d.put(v, walk_y, u, pal["eave"], facing=f, half="bottom", shape="straight")
        if (u - ac) % 7 == 3:
            for v in (inner_a, inner_b):
                d.put(v, canopy_y - 1, u, "iron_chain", axis="y")
                if d.put(v, canopy_y - 2, u, pal["light"], hanging="true", waterlogged="false"):
                    lanterns += 1

    # -- the flight: treads, the masonry they stand on, and the hole they descend through --------
    treads = 0
    for u, y in sorted(stair.items()):
        for v in stair_v:
            for cut in range(y + 1, canopy_y):      # a stairwell is a HOLE, and a hole is cut
                d.clear(v, cut, u)
            if d.put(v, y, u, pal["tread"], facing=ascend, half="bottom", shape="straight"):
                treads += 1
            for fill in range(d.ground_y, y):       # the stringer: a flight stands on masonry
                d.put(v, fill, u, pal["pier"])
    # AND THE FOOT NEEDS A DOOR. The bottom tread lands under the viaduct, and a pier may be
    # standing exactly where a visitor has to walk in from the lawn; two courses of headroom
    # through the abutment is an opening in a wall, which is what an arcade is made of anyway.
    foot = ac + step * half
    for k in (1, 2):
        for v in stair_v:
            for y in range(d.ground_y, d.ground_y + 3):
                d.clear(v, y, foot + step * k)
    lanterns += _head(d, p, sec, pal, s["title"], step, foot)

    # -- the pylon on the axis, and the four signs it carries ------------------------------------
    #
    # AN ISLAND PLATFORM HAS NO BACK WALL TO HANG A NAME ON, which is the one thing the old
    # single-sided station had going for it. What replaces it is better: one pylon on the centre
    # column at the platform's own middle, carrying the station's name on BOTH faces - so it reads
    # from a cart on either line - and the departure board on both approaches. Four signs, in two
    # mirrored pairs, on a thing that is symmetric by construction.
    for v in stair_v:
        for y in range(walk_y, walk_y + 3):
            d.put(v, y, ac, pal["band"] if y == walk_y + 2 else pal["wall"])
    titled = 0
    for v, f in ((sec["island"][1], _v_dir(side)), (sec["island"][-2], _v_dir(-side))):
        if d.sign(v, walk_y + 1, ac, f, pal["wood"], [s["title"]]):
            titled += 1
    board = list(s["board"] or [s["title"], "PARK LINE", "ALL STATIONS", ""])
    boarded = 0
    for du in (-1, 1):
        if d.sign(centre, walk_y + 1, ac + du, _u_dir(du), pal["wood"], board):
            boarded += 1

    # -- the release plinths: THIS is what lets a stopped cart go, and there are two -------------
    #
    # The plinth stands on the platform edge, so its block is horizontally adjacent to its own
    # rail; the button on top strongly powers it, and a strongly powered block beside a powered
    # rail energises that rail and the eight each side of it - which is the whole bay. Button out,
    # the bay is dead and an arriving cart stops here whatever anybody has done. **A LEVER WOULD BE
    # A STATE**: left up, this station never stops a cart again, and nothing on the platform would
    # say so. A button cannot be left anywhere.
    buttons = 0
    for v in (edge_a, edge_b):
        d.put(v, walk_y, ac, pal["band"])
        if d.put(v, walk_y + 1, ac, f"{pal['wood']}_button", face="floor",
                 facing=_u_dir(1), powered="false"):
            buttons += 1

    # -- the approach detector and its bell, one per track, mirrored -----------------------------
    #
    # A detector rail powers what stands next to it, so a bell on the platform edge beside one
    # rings when a cart runs over it and there is NO WIRE ANYWHERE. It is the only thing on six
    # hundred blocks of promenade that tells a walker a train is coming.
    bells = 0
    for tv, ev, adir in ((track_a, edge_a, 1), (track_b, edge_b, -1)):
        du = ac - adir * (dead_half + 10)
        if d.put(ev, walk_y, du, "bell", attachment="floor",
                 facing=_v_dir(-side) if ev == edge_a else _v_dir(side), powered="false"):
            bells += 1

    return {"title": s["title"], "land": s["land"], "at_u": ac,
            "platform": 2 * half + 1, "treads": treads, "lanterns": lanterns,
            "stair_from_u": min(stair), "stair_to_u": max(stair),
            "buttons": buttons, "bells": bells, "screens": screens,
            "board": boarded, "name_signs": titled}


DEFAULTS = PARKRAIL
