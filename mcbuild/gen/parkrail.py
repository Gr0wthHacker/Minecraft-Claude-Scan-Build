"""THE PARK LINE: a viaduct railway down the park's outer edge, and three stations on it.

**IT IS A RIDE, NOT A UTILITY.** The corridor it runs in is the one strip of the 200x600 envelope
with the park on one side and open void on the other, so the whole point of the thing is the view
off the outer edge - which is why the track hugs the VOID face (V2) and the four-wide promenade
and every station platform sit on the PARK face (V3-V6). A rider looks out; a walker boards from
behind. Get that round the other way and the best sightline in the park is spent on a hedge.

    V0   outer parapet - a wall course, the void side
    V1   kerb, dark - the track's outer edge, and where the flush deck lights sit
    V2   THE TRACK - bed at `deck_y`, rail one course up
    V3   platform edge, dark - you board from here; the signal pedestal stands on it
    V4   |
    V5   | the promenade, four wide, and the station platform where a station stands
    V6   |
    V7   inner parapet - and at a station, the station's back wall

**WHAT MAKES 600 BLOCKS OF SPAN READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT LENGTH** -
the void tower's rule, and a viaduct is its purest case. So the deck stands eight courses over the
lawn on a pier every `bay`, with a segmental arch springing between them, an arch RING in a
darker stone than the spandrel it carries, a cross-rib at every crown, and a portal frame every
`portal_every` bays. Nothing about it is damage or irregularity; all of it repeats.

THE RAIL RULES, and every one of them is CORRECTNESS rather than taste. Read off `blocks.json`
rather than remembered, and asserted in `tests/test_parkrail.py` because **our renderer draws a
wrong rail orientation identically to a right one**:

    powered_rail  shape = north_south, east_west, ascending_{n,s,e,w}
    rail          shape = ...those six, PLUS south_east, south_west, north_west, north_east

  * **A POWERED RAIL CANNOT CURVE**, so every direction change costs a plain - and therefore IRON -
    rail. On this server iron is the scarce metal and gold is farmable, so the cheap rail is the
    gold one: powered rail on the straights, iron only at corners. This line lies along one axis
    and needs no corner at all, so its metal is entirely gold and its iron cost is ZERO.
  * **NEVER DESCEND INTO A CORNER.** A curve has no ascending shape, so a corner and both of its
    neighbours must share one height, or the game re-derives the turn as a slope and the line dead
    ends. This line is dead level, so the rule costs it nothing - and `shapes_for` is shared with
    `railspiral` and `transit` so that one implementation enforces it for all three.
  * **AN UNPOWERED POWERED_RAIL IS A BRAKE.** The bed cell under the track becomes a
    `redstone_block` every `power_every`, and the runs are counted BETWEEN CORNERS because a plain
    rail does not propagate the chain. Nothing about the emitted model looks wrong when this is
    missed: `shape` and `powered` are DERIVED by the game, so the schematic, the audit and the
    bill of materials all pass while the line does not run. It is verified by SIMULATION in
    `mcbuild.circuit`, which models the eight-rail propagation directly.
  * **A TRACK CELL IS NEVER OPTIONAL.** A cell that cannot be placed is an error naming the cell,
    never a silent skip: a broken line still audits as one clean solid.
  * **A TERMINUS NEEDS A STOP BLOCK.** A stationary cart on a powered rail launches AWAY from the
    adjacent solid block; with neither end blocked the line only runs whichever way you shoved it.

**AND THE BRAKE IS WHAT MAKES IT A RAILWAY RATHER THAN A LOOP OF TRACK.** A continuously powered
line cannot be boarded - the cart never stops. Each station therefore holds a DEAD ZONE of
`brake_half * 2 + 1` powered rails with no source of their own, and a lever on a pedestal at the
platform edge whose block is adjacent to the track: lever off, the zone is unpowered and a cart
coasting in stops on the platform; lever on, the pedestal drives the zone and its eight-rail
propagation exactly bridges the gap to the sources outside it. Both states are asserted by
simulation, because "it looked right" is how every dead circuit in this repo shipped.

The geometry of the quiet band is arithmetic and it is the fiddly part: sources are suppressed
across `[c - 2h, c + 2h]` and FORCED at `c - 2h - 1` and `c + 2h + 1`, so with the lever off the
nearest source is nine hops from the nearest brake rail (dead), and with it on the zone plus those
two sources cover every cell between them (live). Move `brake_half` and the arithmetic moves with
it; `_sources` is the one place it is written.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .railspiral import runs_of, shapes_for

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
#: hundred blocks long over open void, the only lamp nobody can knock off.
FLUSH_LIGHT = "ochre_froglight"

PARKRAIL = {
    "bounds": [0, 0, 7, 599],     # v0, u0, v1, u1 - THE CORRIDOR, and nothing may leave it
    "lands": None,                 # [{name, u0, u1}] in U order; the gaps between them are reaches
    "track_v": 2,                  # V of the rail; V1 and V3 are its kerbs
    "park_side": 1,                # +1: the park is toward higher V. -1 for the rim corridor.
    "deck_y": 12,                  # the deck FLOOR course. You stand, and the rail sits, at +1
    "ground_y": 1,                 # the first course above the park's lawn - see the module note
    "bay": 15,                     # pier to pier
    "pier_u": 3,                   # pier thickness along U
    "spring_y": 4,                 # the arch springing course
    "crown_gap": 2,                # courses of masonry between the arch crown and the deck
    "gate_v": [5, 7],              # the V band cut through every pier at ground level
    "gate_h": 4,                   # ...and how many courses tall
    "portal_every": 4,             # a portal frame every this many bays
    "power_every": 8,              # a redstone_block in the bed this often, per RUN
    "light_every": 12,             # a froglight flush in a kerb this often
    "arch_light_every": 2,         # a lantern under the crown every this many bays
    "brake_half": 8,               # half the station dead zone, in rails
    "track_inset": 3,              # cells of deck beyond each terminus, for the stop block
    "stations": None,              # [{at_u, land, title, board, stair}]
    "station_half": 13,            # platform half-length; the platform is 2*half + 1
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
    """(side, park_edge, void_edge) - WHICH WAY THE PARK IS, from the track.

    The cross-section in this module's docstring is written with the void at the LOW V edge,
    because the first corridor it was given ran along V0-7. In the 200-deep envelope the void is
    at the HIGH edge: V0 is the arrival apron against the connector and V170-199 is the rim and
    void reserve. A viaduct that gets this the wrong way round puts the promenade, the platforms
    and every station stair on the void side, so a visitor boards facing nothing and descends into
    the reserve - and NOTHING IN AN AUDIT CAN SEE IT, because a mirrored viaduct is one connected
    piece with no placement problem and the same bill of materials.

    So the side is a parameter, `park_side`: +1 when the park lies toward higher V (the original
    corridor), -1 when it lies toward lower V (the rim corridor). Everything that is genuinely
    one-sided - the promenade, the platform, the back wall, the flight, the signs, the eave - is
    written against it; everything symmetric about the track is left alone.
    """
    v0, _u0, v1, _u1 = p["bounds"]
    side = 1 if int(p.get("park_side", 1)) >= 0 else -1
    return (side, v1, v0) if side > 0 else (side, v0, v1)


def _span(a: int, b: int, step: int):
    """The inclusive run from `a` to `b`, whichever direction `step` points."""
    return range(a, b + step, step)


# ---------------------------------------------------------------------------- the track


def plan(params: dict) -> list:
    """THE track for a config: the one entry point the build and the tests both go through.

    Written twice they drift - `railspiral`'s own tests once called `route` without a ground table,
    got a terminus the design does not have, and reported a missing stop block on a line that has
    one. Same rule `proportions.measure` and `rubric.score` already follow.

    Returns [(x, y, z, is_corner)] in CANVAS coordinates, which is `railspiral`'s own cell shape,
    so `shapes_for`, `runs_of` and `power_cells` all apply to it unchanged.
    """
    p = {**PARKRAIL, **(params or {})}
    v0, u0, v1, u1 = p["bounds"]
    inset = int(p["track_inset"])
    x = int(p["track_v"]) - v0
    y = int(p["deck_y"]) + 1
    n = (u1 - u0 + 1) - 2 * inset
    if n < 4:
        raise ValueError("parkrail needs a corridor long enough for at least 4 track cells")
    if not (0 <= x <= v1 - v0):
        raise ValueError(f"track_v {p['track_v']} is outside the corridor {p['bounds']}")
    return [(x, y, inset + a, False) for a in range(n)]


def _sources(n: int, every: int, brakes: list, half: int) -> tuple:
    """(source indices, quiet indices) for the track's BED.

    A source is a `redstone_block` under a powered rail. Everything about this function is the
    brake: a station needs a stretch of track that is DEAD when its lever is off, and a powered
    rail carries its own state eight rails past a source, so "dead" is a statement about a
    twenty-five-cell neighbourhood rather than about one cell.
    """
    quiet, forced = set(), set()
    for c in brakes:
        for i in range(c - 2 * half, c + 2 * half + 1):
            if 0 <= i < n:
                quiet.add(i)
        for i in (c - 2 * half - 1, c + 2 * half + 1):
            if 0 <= i < n:
                forced.add(i)
    picks = set(forced)
    for i in (0, n - 1):
        if i not in quiet:
            picks.add(i)
    last = None
    for i in range(n):
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
        return self.c.get_name(v - self.v0, y, u - self.u0)

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
    if sx < 8:
        raise ValueError("parkrail needs a corridor at least 8 cells deep")
    seed = int(p["seed"])
    deck_y, ground_y = int(p["deck_y"]), int(p["ground_y"])
    walk_y = deck_y + 1
    canopy_y = walk_y + int(p["canopy_h"])
    c = Canvas(sx, canopy_y + 3, sz)
    d = _Deck(c, p)
    pal_at, land_name = _land_table(p)
    track_v = int(p["track_v"])
    side, park_edge, void_edge = _sides(p)

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
    gate_lo, gate_hi = (int(v) for v in p["gate_v"])
    gate_h = int(p["gate_h"])
    piers = gates = 0
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
            # and there is nowhere on six hundred blocks that you can get inside. It runs to V7,
            # so every pier is a doorway off the lawn as well as a link along the arcade.
            if gate_hi >= gate_lo:
                mid = (gate_lo + gate_hi) // 2
                for v in range(gate_lo, gate_hi + 1):
                    for y in range(ground_y, ground_y + gate_h):
                        d.clear(v, y, u)
                    a, bb, t = pal_at(u)
                    # THE LINTEL IS THE LAMP. The arch lanterns hang two courses under the deck,
                    # eleven above a head walking the arcade, so the passage came out a dark
                    # tunnel with a lit ceiling. A froglight in the lintel costs no metal, cannot
                    # be knocked off, and is the only fixture in a doorway that nobody can walk
                    # into - which is the same argument the flush deck lights already make.
                    d.put(v, ground_y + gate_h, u,
                          FLUSH_LIGHT if v == mid else pick(a, bb, t, "band", v, u))
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

    # ------------------------------------------------------------------ 2. the deck
    #
    # Eight cells across, six hundred long, and every column of it says which of the four things
    # it is: parapet, kerb, track bed, promenade.
    # A DECK OF ONE MATERIAL FOR SIX HUNDRED BLOCKS IS A FLOOR, NOT A WALK. That is exactly the
    # complaint the ground layer was rebuilt to answer - "massive amounts of the same stone, no
    # patterns" - and a promenade four wide and six hundred long is the easiest place in the park
    # to make it again. Two rhythms, both derived from something real rather than drawn on: a
    # transverse rung in the land's own band over EVERY PIER, so the walk shows you the structure
    # under it, and a dotted kerb inlay along the promenade's middle.
    lights = 0
    pier_cols = {u for b0 in range(u0, u1 + 1, bay) for u in range(b0, b0 + pier_u)}
    for u in range(u0, u1 + 1):
        a, bb, t = pal_at(u)
        for v in range(v0, v1 + 1):
            if v in (v0, v1, track_v - 1, track_v + 1):
                key = "kerb"
            elif v == track_v:
                key = "deck"
            elif u in pier_cols:
                key = "band"
            elif v == track_v + 2 * side and (u - u0) % 4 == 0:
                key = "kerb"
            else:
                key = "deck"
            d.put(v, deck_y, u, pick(a, bb, t, key, v, u))
        # THE LIGHT IS THE DECK, NOT A FIXTURE ON IT. A flush froglight costs no metal, cannot be
        # knocked off a walkway eight courses over the lawn, and leaves the deck clear to walk.
        if (u - u0) % max(1, int(p["light_every"])) == 0:
            v = track_v - 1 if ((u - u0) // int(p["light_every"])) % 2 == 0 else track_v + 1
            if u not in platform_u:
                d.put(v, deck_y, u, FLUSH_LIGHT)
                lights += 1

    # ------------------------------------------------------------------ 3. the track
    cells = plan(p)
    shapes = shapes_for(cells)
    brakes = [next(i for i, cell in enumerate(cells) if cell[2] == s["at_u"] - u0)
              for s in stations if any(cell[2] == s["at_u"] - u0 for cell in cells)]
    picks, quiet = _sources(len(cells), int(p["power_every"]), brakes, int(p["brake_half"]))
    for i, (x, y, z, _corner) in enumerate(cells):
        # THE BED FIRST, and the bed IS the railway: an unpowered powered rail is a brake, so a
        # `redstone_block` here is not decoration. Nothing is consulted before writing either the
        # bed or the rail - not a dither, not a station, not the deck that was laid a moment ago.
        # A TRACK CELL IS NOT OPTIONAL.
        if not c.put(x, y - 1, z, c.state("redstone_block") if i in picks
                     else _bed_block(d, pal_at, pick, track_v, z + u0)):
            raise ValueError(f"parkrail: track bed cell {i} fell outside the corridor")
        if not c.put(x, y, z, c.raw_state("powered_rail", shape=shapes[i],
                                          powered="true", waterlogged="false")):
            raise ValueError(f"parkrail: track cell {i} fell outside the corridor")
    # A TERMINUS NEEDS A STOP BLOCK, at BOTH ends, or the line only runs whichever way you shove
    # the cart - and the whole point of three stations is that a visitor can come back.
    stops = 0
    for z in (cells[0][2] - 1, cells[-1][2] + 1):
        u = z + u0
        a, bb, t = pal_at(u)
        if d.put(track_v, walk_y, u, pick(a, bb, t, "band", track_v, u)):
            stops += 1
        # ...and a BUFFER round it, so the end of the line reads as an end rather than as a cell
        # somebody forgot to lay track in. Two courses across the three cells of the track's own
        # width, and a screen wall across the whole deck at the corridor's last column.
        for v in (track_v - 1, track_v + 1):
            d.put(v, walk_y, u, pick(a, bb, t, "band", v, u))
        for v in range(track_v - 1, track_v + 2):
            d.put(v, walk_y + 1, u, pick(a, bb, t, "kerb", v, u))
    for u in (u0, u1):
        a, bb, t = pal_at(u)
        for v in range(v0, v1 + 1):
            d.put(v, walk_y, u, pick(a, bb, t, "band", v, u))
            d.put(v, walk_y + 1, u, pick(a, bb, t, "parapet", v, u))

    # ------------------------------------------------------------------ 4. parapets and portals
    #
    # NOTHING IS A FULL-BLOCK PILLAR WHERE A SLIM BLOCK WILL DO. A parapet is a wall course, a
    # portal's legs are walls, and the only full blocks above the deck are the portal beam and the
    # station masonry - which are lintels and buildings, not posts.
    seats = 0
    for u in range(u0, u1 + 1):
        a, bb, t = pal_at(u)
        for v in (v0, v1):
            if v == v1 and u in platform_u:
                continue                            # a station's own back wall stands here
            # A NEWEL OVER EVERY PIER. A wall course is a railing; six hundred blocks of one is a
            # line. What turns it into a balustrade is a post where the structure under it says
            # there should be one, which is the same argument the deck's own transverse rungs make
            # one course down - the rhythm is READ OFF the viaduct, never drawn on it.
            if u in pier_cols:
                d.put(v, walk_y, u, pick(a, bb, t, "band", v, u))
                d.put(v, walk_y + 1, u, pick(a, bb, t, "parapet", v, u))
            else:
                d.put(v, walk_y, u, pick(a, bb, t, "parapet", v, u))
        # A PROMENADE SIX HUNDRED BLOCKS LONG NEEDS SOMEWHERE TO SIT, and a seat here faces the
        # VOID: a stair's TALL side is its `facing`, so a bench with its back to the park wall
        # faces east and a visitor on it looks out over the track and the edge. Written the other
        # way round every bench on the park's own verges once had its backrest to the street.
        if (u - u0) % 24 == 12 and u not in platform_u and u not in pier_cols:
            if d.put(park_edge - side, walk_y, u, pal_at(u)[0]["eave"],
                     facing=_v_dir(side), half="bottom", shape="straight"):
                seats += 1

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
        # a lantern on a chain under the beam, over the promenade rather than over the track
        d.put(track_v + 2 * side, canopy_y - 1, u, "iron_chain", axis="y")
        if d.put(track_v + 2 * side, canopy_y - 2, u, pal_at(u)[0]["light"], hanging="true",
                 waterlogged="false"):
            lanterns += 1
        portals += 1

    # ...and a lantern under the crown of every other arch, so the arcade below is lit and the
    # elevation has a rhythm of lights read from the lawn as well as from the deck.
    for k, b0 in enumerate(range(u0, u1 + 1, bay)):
        if k % max(1, int(p["arch_light_every"])):
            continue
        u = b0 + pier_u + span_w // 2
        if u > u1 or u in platform_u:
            continue
        pal = pal_at(u)[0]
        d.put(track_v + 2 * side, deck_y - 1, u, "iron_chain", axis="y")
        if d.put(track_v + 2 * side, deck_y - 2, u, pal["light"], hanging="true",
                 waterlogged="false"):
            lanterns += 1

    # ------------------------------------------------------------------ 5. the stations
    built = []
    for s in stations:
        built.append(_station(d, p, s, pal_at, canopy_y))
        lanterns += built[-1]["lanterns"]

    c.meta = {
        "kind": "parkrail",
        "bounds": list(p["bounds"]),
        "track_v": track_v, "rail_y": walk_y, "deck_y": deck_y,
        "track_cells": len(cells), "corners": sum(1 for cell in cells if cell[3]),
        "power_sources": len(picks), "brake_zones": len(brakes), "quiet_cells": len(quiet),
        "stop_blocks": stops, "piers": piers, "pier_gates": gates, "portals": portals,
        "flush_lights": lights, "lanterns": lanterns, "deck_seats": seats,
        "stations": [{"title": s["title"], "land": s["land"], "at_u": s["at_u"]} for s in stations],
        "station_detail": built,
        "runs": [list(r) for r in runs_of(cells)],
        "contract": "one straight level powered line the length of the corridor, three stations "
                    "with a lever-held brake each, a stop block at both termini, on an arcaded "
                    "viaduct - and not one cell outside V%d-%d" % (v0, v1),
    }
    return c


def _bed_block(d: _Deck, pal_at, pick, track_v: int, u: int) -> int:
    """The bed under an unpowered track cell: the deck's own material, never a hole."""
    a, bb, t = pal_at(u)
    return d.blk(pick(a, bb, t, "deck", track_v, u))


# ---------------------------------------------------------------------------- a station


def _station(d: _Deck, p: dict, s: dict, pal_at, canopy_y: int) -> dict:
    """One station: platform, back wall, canopy, departure board, signal lever, and a stair down.

    THE THREE STATIONS ARE THREE PLACES, NOT ONE STATION PAINTED THREE COLOURS. Each takes its own
    land's masonry, its own post, its own roof material and its own light - the same argument
    `parkways` makes for its lamps, which is that a land is told apart by what its street furniture
    is MADE of as much as by its paving, and a station is the object a visitor stands inside.

    **THE STAIR IS INSIDE THE STATION'S OWN FOOTPRINT AND THAT IS THE WHOLE SITING DECISION.** The
    corridor is eight cells deep and the promenade is four of them; a flight cut through the open
    deck would pinch that walk to one cell for the length of the flight, every time. Taken out of
    the platform's own back two columns instead, the deck outside the station is untouched, the
    canopy already roofs the flight, and it lands under the viaduct facing the park - which is the
    side a visitor arrives from.
    """
    pal = SPAN[s["land"]]
    v1 = d.v1
    deck_y, walk_y = d.deck_y, d.walk_y
    half = int(p["station_half"])
    ac = int(s["at_u"])
    track_v = int(p["track_v"])
    lanterns = 0

    # THE FLIGHT FIRST, as a SET of cells, because everything else has to keep out of it. Written
    # the other way round - wall, canopy, then carve - the carve has to guess which of its own
    # courses were somebody else's, and a station whose back wall crosses its own stairwell is
    # invisible in every render.
    side, park_edge, _void_edge = _sides(p)
    step = 1 if int(s["stair"]) >= 0 else -1
    ascend = _u_dir(-step)                          # a flight ascends TOWARD the platform
    rise = walk_y - d.ground_y
    stair_v = (park_edge - side, park_edge)
    stair = {ac + step * (half - rise + 1 + k): deck_y - k for k in range(rise)}
    if half < rise:
        raise ValueError("a parkrail station platform is shorter than its own flight")

    # -- the platform floor: the land's own deck with a banded inlay, so it reads as a room -----
    for u in range(ac - half, ac + half + 1):
        for v in _span(track_v + side, park_edge, side):
            key = "kerb" if v == track_v + side else ("band" if (u - ac) % 4 == 0 else "deck")
            d.put(v, deck_y, u, pal[key])

    # -- the back wall, in the cell the parapet would otherwise have -----------------------------
    wall_top = canopy_y - 1
    for u in range(ac - half, ac + half + 1):
        if u in stair:
            continue                                # the flight comes down through this column
        for y in range(walk_y, wall_top + 1):
            # A STATION IS A BUILDING, AND A BUILDING IS MADE OF ITS LAND'S OWN MATERIAL. Built out
            # of the viaduct's masonry all three came out as the same grey blockhouse with three
            # different roofs on it - which is `parkways`' own argument about its lamps, and the
            # reason `wall` is a key of its own rather than a reuse of `pier`.
            key = "band" if y in (walk_y, wall_top) or (u - ac) % 5 == 0 else "wall"
            if y == walk_y + 1 and (u - ac) % 5 == 0 and abs(u - ac) < half:
                # A SLIT, SO THE WALL IS NOT A BLANK SLAB - and an OPEN trapdoor is the vertical
                # slab this game never shipped, which is why it is worth reaching for here rather
                # than another full block. It hinges on the masonry beside it along the wall, which
                # is solid by construction: the wall runs the platform's whole length.
                if pal["screen"] == "iron_bars":
                    d.put(park_edge, y, u, "iron_bars")
                else:
                    d.put(park_edge, y, u, pal["screen"], facing=_u_dir(1), half="bottom",
                          open="true", powered="false", waterlogged="false")
                continue
            d.put(park_edge, y, u, pal[key])

    # -- the canopy: slim posts at the platform edge, a slab roof, a stair eave over the track ---
    for u in range(ac - half, ac + half + 1):
        if (u - ac) % 5 == 0:
            for y in range(walk_y, canopy_y):
                d.put(track_v + side, y, u, pal["post"])
        for v in _span(track_v + side, park_edge, side):
            d.put(v, canopy_y, u, pal["roof"], type="bottom")
        # the eave leans OUT over the track, which is what makes a canopy read as shelter rather
        # than as a lid: a stair's TALL side IS its `facing`, so an eave shading the track faces
        # AWAY from the platform.
        d.put(track_v, canopy_y, u, pal["eave"], facing=_v_dir(side), half="bottom",
              shape="straight")
        d.put(park_edge, canopy_y + 1, u, pal["band"])     # a ridge band along the back, read from afar
        if (u - ac) % 5 == 2 and u not in stair:
            # a seat with its back to the station wall, looking out across the track
            d.put(park_edge - side, walk_y, u, pal["eave"], facing=_v_dir(side), half="bottom",
                  shape="straight")
        if (u - ac) % 6 == 3:
            d.put(track_v + 2 * side, canopy_y - 1, u, "iron_chain", axis="y")
            if d.put(track_v + 2 * side, canopy_y - 2, u, pal["light"], hanging="true",
                     waterlogged="false"):
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
        if y < deck_y:                              # a balustrade round the opening, never across
            d.put(park_edge - 2 * side, walk_y, u, pal["parapet"])   # its head, or you cannot get on to it
    # AND THE FOOT NEEDS A DOOR. The bottom tread lands under the viaduct, and a pier may be
    # standing exactly where a visitor has to walk in from the lawn; two courses of headroom
    # through the abutment is an opening in a wall, which is what an arcade is made of anyway.
    foot = ac + step * half
    for k in (1, 2):
        for v in stair_v:
            for y in range(d.ground_y, d.ground_y + 3):
                d.clear(v, y, foot + step * k)

    # -- the name, on the wall where it is read from the deck ------------------------------------
    titled = 0
    #: A NAME SIGN HAS TO BE ON A WALL THAT EXISTS. The flight takes the back wall out of eight of
    #: the platform's twenty-one columns, so a sign placed by a hand-typed offset is refused
    #: silently at one end of every station whose stair runs that way - which is what happened, and
    #: it cost one of the two names on all three. Walk inward from both ends until the wall is
    #: there, and count what was actually placed.
    for end in (-1, 1):
        for k in range(2, half):
            u = ac + end * (half - k)
            if u in stair:
                continue
            if abs(u - ac) >= 4 and d.sign(park_edge - side, wall_top - 1, u, _v_dir(-side),
                                            pal["wood"], [s["title"]]):
                titled += 1
            break

    # -- the departure board ---------------------------------------------------------------------
    board = list(s["board"] or [s["title"], "PARK LINE", "ALL STATIONS", ""])
    boarded = d.sign(park_edge - side, walk_y + 1, ac, _v_dir(-side), pal["wood"], board)

    # -- the signal pedestal: THIS is the brake, and it is the reason a cart can be boarded ------
    #
    # The pedestal stands on the platform edge, so its block is horizontally adjacent to the rail;
    # a lever on top strongly powers it, and a strongly powered block beside a powered rail
    # energises it. Lever down, the station's dead zone is dead and a coasting cart stops here.
    d.put(track_v + side, walk_y, ac, pal["band"])
    lever = d.put(track_v + side, walk_y + 1, ac, "lever",
                  face="floor", facing=_u_dir(1), powered="false")

    return {"title": s["title"], "land": s["land"], "at_u": ac,
            "platform": 2 * half + 1, "treads": treads, "lanterns": lanterns,
            "stair_from_u": min(stair), "stair_to_u": max(stair),
            "lever": bool(lever), "board": bool(boarded), "name_signs": titled}

DEFAULTS = PARKRAIL
