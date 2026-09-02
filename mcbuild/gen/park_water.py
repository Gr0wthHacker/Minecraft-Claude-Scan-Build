"""THE PARK'S WATER: a scenic lake as a congregation point, on the reach between two lands.

**MEASURED FIRST.** The whole park is 273,356 blocks and holds **171 water blocks** - no lake, no
pond, no fountain, no stream. Jack: *"realistically this includes things like, we should probably
have a scenic lake for example as a congregation point, and things like this as normal large theme
parks and parks in general do."* A 600x200 park with no water reads as three towns rather than one
destination, and water is the only element that can belong to all three at once.

THE SITE IS THE CLAIM LINE REACH, U170-214 - the connector between the Frontier (ends U169) and
the Midway (starts U215). Measured off `out/Park Complete.litematic`:

    the whole reach at Y202          9,000 columns, ALL of them a one-course plate
    below Y202                       NOTHING. The park is a 1-block skin over open void.
    paved, and untouchable           spine V6-18 . promenade V123-127 . service V154-156 .
                                     rim V170 . thresholds U170-172 and U212-214, full depth
    lamp masts                       V20 at U179/192/205 and V121 at U175/192/209
    the Signal Heron                 feet at Y203 on (V45,U198) and (V52,U198), body V42-55
                                     U194-203, crown Y258 - in its own reserved garden

So the free ground is V24-V121 by U173-U211, and this design takes **V24-V112 by U173-U211**,
stopping nine courses short of the promenade's own lamp line rather than measuring to it.

------------------------------------------------------------------------------------------------
THE PARK IS ONE BLOCK THICK, SO A LAKE IS A BOWL HUNG UNDER IT, NOT A HOLE DUG IN IT.

There is nothing at all below Y202. Every cell of the basin - bed AND wall - is placed by this
design, and the moss skin at Y202 inside the outline is BROKEN (it is in the dig list). That makes
rule 1 the whole engineering problem rather than a detail:

**WATER LEAKS, AND IT IS CATASTROPHIC.** `fluids.escapes` and `fluids.unenclosed` exist in this
repo because a log flume self-checked with `fluids.carries` - which asks whether the ride PATH is
wet - and drained 199,959 cells to Y-1908 while every render, every audit, the bill of materials
and the generator's own check passed it. So containment here is not argued from the geometry being
right; `_seal` walks EVERY water cell after the shape is drawn and places a wall wherever a
horizontal neighbour or the cell below is not already solid. A leak is then impossible by
construction rather than by reasoning, and `tests/test_park_water.py` re-derives it from the
finished model in the composite anyway, which is the only evidence worth having.

**WATER FREEZES.** Block light must be >= 10 in every water cell or it turns to ice; the court
hall's pool froze on its first build - 29 ice blocks - and `freeze_guard` exists because of it. A
lantern is 15 and a soul lantern is EXACTLY 10, one block of falloff from failing, so a soul
lantern is mood and never a guard. A bank lantern reaches four blocks of water and this lake is
sixty across, so the light has to come from INSIDE it: `ochre_froglight` set flush into the bed,
placed by a SOLVER that propagates light and re-solves to a fixpoint, exactly as `Island Night`
does. It is the park's own glow block, it is invisible as a fixture (it is the bed), and under two
courses of water it reads as a pale sand patch by day and as a lake lit from within at night.

The solver is a fixpoint and not one pass for the reason the night pass records: placing a light
changes the model, so the answer has to be recomputed against the model that now holds it.

------------------------------------------------------------------------------------------------
WHAT MAKES IT A CONGREGATION POINT RATHER THAN A PUDDLE

  * **A REAL SHORELINE.** The outline is a blob - an ellipse with three harmonics on its radius -
    so no run of it is straight, and the depth is a distance transform from that shore, so
    shallows happen at the edge by construction rather than being drawn. Three depths: a 1-deep
    shelf you can see the bed through, a 2-deep body, a 3-deep core.
  * **THE STRAND IS THE SHORE, AND IT IS NOT SAND.** `sand`, `gravel`, `clay` and every form of
    dirt are currency on this server (and sand and gravel FALL, over a basin hung in void). The
    shore is a shingle instead - `stone`, `andesite` and `mossy_stone_bricks` dithered by distance
    from the water into the park's own moss lawn, so the lawn BECOMES the beach over four courses
    rather than stopping at a line. It is the Lowland Stair's gradient rule on a horizontal plane.
  * **SOMEWHERE TO STAND AND LOOK, AT THE SCALE OF A CROWD.** The Look-Out Terrace is 31 wide by
    10 deep on the spine side: a raised stone deck one course up, a balustrade along its water
    edge broken by three flights down, and a quay at lawn level where the water meets built stone.
    It is six courses from the spine's own verge, so it is the first thing the spine shows you.
  * **A CROSSING, BECAUSE THE REACH IS A ROUTE.** Nothing but the spine crosses this reach. The
    Boardwalk runs the whole 39 columns from the U173 bank to the U211 bank - landing one cell
    clear of both threshold paths, never on them - on piles, one course above the water, with a
    viewing bay in the middle of the lake. THE WATER RUNS UNDER IT: the deck is at Y203 and the
    lake surface at Y202, so it is one body of water with a bridge over it, not two ponds.
  * **THE HERON IS FISHING.** It already stands here. The lake is built AROUND it: a shoal carries
    its two feet, and a shallow creek is cut through the shoal between its legs, so a wading bird
    stands in the water it wades in. Its own cells are never touched - `_refuse` raises on any
    cell the world already holds that is not lawn.

------------------------------------------------------------------------------------------------
RULES THIS FILE IS BUILT ON, each of which cost this repo a rebuild somewhere else

  * **NOTHING MAY TOUCH A STREET.** Zero of the park's nineteen placed modules touches another,
    and that single property is the difference between this park and the one Jack threw away. So
    the world is READ, not assumed: `_refuse` walks every cell this design wants and raises naming
    the cell if the world holds anything but `moss_block` or `moss_carpet` there. A paving cell,
    a lamp mast, a bench or a heron leg is an ERROR, never a silent skip - `parkrail`'s rule that
    a structural cell is never optional, applied to a whole design.
  * **A LITEMATIC CANNOT EXPRESS REMOVAL.** Every lawn cell the lake replaces goes in `meta["dig"]`
    - including the `moss_carpet` scatter standing on a cell that becomes water, which would
    otherwise be left floating on the lake.
  * **GRAVITY BLOCKS CANNOT BE USED OVER AIR** (`blocks.falls`) and this whole basin is over air.
  * **A STAIR'S TALL SIDE IS ITS `facing`.** Our renderer draws a backwards stair identically to a
    right one, so every riser here is asserted in the tests rather than eyeballed.
  * **THE VALUE LADDER IS MEASURED ACROSS FAMILIES, NEVER INSIDE ONE** - four notes in CLAUDE.md
    conclude this economy has no contrast and every one of them searched inside a single family.
    Measured with `blocks.color`: `polished_blackstone_bricks` 48 -> `smooth_basalt` 73 ->
    `moss_block` 89 -> `mossy_stone_bricks` 115 -> `stone` 126 -> `andesite` 136 ->
    `smooth_stone` 159 -> `ochre_froglight` 245. Every adjacent step is at least 10 and the ones
    that have to draw a line are 20 or more.
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np

from .canvas import Canvas, hash01

# Everything this design may find standing where it wants to build. Anything else is an error
# naming the cell: the park's paving, its lamp masts and the Signal Heron are all off limits, and
# a design that quietly skipped them would ship a lake with a hole in it and audit clean.
LAWN = "moss_block"
LAWN_TRIM = "moss_carpet"
REPLACEABLE = (LAWN, LAWN_TRIM)

#: The bed, by depth. Pale in the shallows where you see it through one course of water, dark in
#: the core so the deep reads as deep - the one thing that makes a flat basin look like a lake.
BED = {1: ("stone", "andesite"), 2: ("andesite", "stone"), 3: ("smooth_basalt", "andesite")}
WALL = "stone"                      # the basin's own containment shell - never seen, never optional
GLOW = "ochre_froglight"            # the park's own glow block, set flush INTO the bed

#: The shingle shore, wet-to-dry. Index 0 touches the water.
SHINGLE = ("andesite", "stone", "mossy_stone_bricks", LAWN)

PARK_WATER = {
    "kind": "lake",
    "anchor": None,             # [x, y, z] world corner of this canvas; y is the DEEPEST bed course
    "v0": 24, "v1": 112,        # the park's V band this design owns (world V)
    "u0": 173, "u1": 211,       # the park's U band this design owns (world U)
    "ground_y": 202,            # the course the park's lawn occupies; the lake's surface sits here
    "world": None,              # the capture to read: what is already standing, and what may be dug

    # ---- the lake ---------------------------------------------------------------------------
    # TWO EDGE CURVES, NOT A RADIUS. A quay's water edge is STRAIGHT - that is what a quay is -
    # and a shore's is not, and no single ellipse can be both: fitted to the straight run it
    # stops touching the built edge two columns either side of centre, and forced out to it, it
    # leaves a rectangular notch. So the near shore is a curve in U that the terrace pins flat
    # across its own frontage and that flares away into shingle on both sides of it, and the far
    # shore is an independent wobble that closes on the near one at both ends of the reach.
    "far_reach": 66.0,                  # how far the far shore stands off the quay at its widest
    "end_shape": 0.55,                  # <1 holds the lake wide through the middle of the reach
    "flare": 1.55,                      # how fast the shore leaves the quay, per column
    "deep_at": 5, "deepest_at": 13,     # shore distance at which the bed drops a course

    # ---- the shoal the heron stands on ------------------------------------------------------
    "shoal_v": 52, "shoal_u": 200, "shoal_rv": 8.5, "shoal_ru": 9.5,
    "creek_v": 48.5, "creek_u": 199, "creek_rv": 3.4, "creek_ru": 7.5,
    "heron_feet": [[45, 198], [52, 198]],       # V, U - never water, never planted, never touched
    "heron_clear": [41, 193, 56, 205],          # v0, u0, v1, u1 - no planting inside it

    # ---- the terrace ------------------------------------------------------------------------
    "terrace_v": 27, "terrace_deep": 7,         # deck V27..V33, one course above the lawn
    "terrace_u0": 183, "terrace_u1": 201,
    "quay_deep": 4,                             # quay V34..V37 at lawn level
    "stair_u": [186, 192, 198],                 # the three flights down through the balustrade
    "lamp_u": [184, 189, 195, 200],
    "bench_u": [[187, 190], [193, 196]],        # runs of seats, in the bays between the flights

    # ---- the boardwalk ----------------------------------------------------------------------
    "walk_v": 84, "walk_wide": 3,               # deck V84..V86
    "bay_v": 80, "bay_u0": 190, "bay_u1": 196,  # the viewing bay, jutting toward the terrace
    "pier_every": 5,
    "walk_lamp_every": 9,

    # ---- planting ---------------------------------------------------------------------------
    "trees": [[104, 178], [107, 186], [103, 199], [108, 206], [100, 176]],
    "lily_frac": 0.10,
    "seagrass_frac": 0.07,

    # ---- light ------------------------------------------------------------------------------
    "light_floor": 10,          # below this, water freezes
    "light_target": 11,         # what the solver aims for, so the floor keeps a course of margin
    "light_rounds": 8,
    "seed": 7,
}


# --------------------------------------------------------------------------- the world underneath


class _World:
    """What is already standing in the box, read off a capture rather than assumed.

    Absent (`world: null`) every cell reads as the park's own lawn at the ground course and air
    everywhere else, which is what the reach measures as - but then nothing can be REFUSED, so a
    real build always passes the capture.
    """

    def __init__(self, path: str | None, ground_y: int):
        self.ground_y = ground_y
        self.model = self.origin = None
        if not path:
            return
        from .. import scan as scan_mod
        s = scan_mod.load(path)
        self.model, self.origin = s.model, s.origin
        self.names = [n.split(":")[-1] for n in s.model.names]

    def name(self, x: int, y: int, z: int) -> str:
        if self.model is None:
            return LAWN if y == self.ground_y else "air"
        ox, oy, oz = self.origin
        sy, sz, sx = self.model.ids.shape
        i, j, k = y - oy, z - oz, x - ox
        if not (0 <= i < sy and 0 <= j < sz and 0 <= k < sx):
            return "air"
        return self.names[self.model.ids[i, j, k]]

    def solid(self, x: int, y: int, z: int) -> bool:
        n = self.name(x, y, z)
        return n not in ("air", LAWN_TRIM)


# --------------------------------------------------------------------------- shapes


def _blob(dv: float, du: float, rv: float, ru: float, phase: float) -> float:
    """r <= this is inside. An ellipse with three harmonics on its radius: no run of the shore is
    straight and no lobe repeats, which is the whole difference between a lake and a pond liner."""
    th = math.atan2(du, dv)
    return (1.0
            + 0.105 * math.sin(3 * th + phase)
            + 0.070 * math.sin(5 * th + 2.3 + phase)
            + 0.045 * math.sin(7 * th + 0.4 + phase))


def _shore(p: dict, u0: int, u1: int, quay: int) -> dict:
    """(near, far) in V for every U across the reach - the lake's whole outline.

    THE NEAR SHORE IS PINNED FLAT ACROSS THE TERRACE AND FLARES AWAY EITHER SIDE OF IT, because
    a quay's water edge is a built line and a beach's is not. The FAR shore is three harmonics
    with no straight run in it at all, scaled by an end taper that closes the two curves on each
    other before either reaches a threshold path - so the lake ends in water, not in a cut edge.
    """
    tu0, tu1 = int(p["terrace_u0"]), int(p["terrace_u1"])
    reach, flare = float(p["far_reach"]), float(p["flare"])
    out = {}
    for u in range(u0, u1 + 1):
        t = (u - u0) / max(1, u1 - u0)
        e = math.sin(math.pi * t) ** float(p["end_shape"])
        far = quay + reach * e + e * (3.4 * math.sin(u * 0.37 + 1.2)
                                      + 2.1 * math.sin(u * 0.83 + 2.9)
                                      + 1.3 * math.sin(u * 1.61 + 0.3))
        if tu0 <= u <= tu1:
            near = float(quay)
        else:
            d = (tu0 - u) if u < tu0 else (u - tu1)
            near = (quay + flare * d + 0.05 * d * d
                    + 1.4 * math.sin(u * 0.55 + 1.1) + 0.9 * math.sin(u * 0.29 + 2.4))
        out[u] = (max(float(quay), near), far)
    return out


def _inside(v: float, u: float, cv: float, cu: float, rv: float, ru: float, phase: float) -> bool:
    dv, du = (v - cv) / rv, (u - cu) / ru
    r = math.hypot(dv, du)
    return r <= _blob(dv, du, rv, ru, phase)


def _distance_to_land(water: np.ndarray) -> np.ndarray:
    """Cells to the nearest non-water cell, 4-connected, over the [V][U] plan.

    A BFS rather than a formula: the shore is a blob with a shoal cut out of it and a creek cut
    into that, and no radius expression knows where the nearest land is once the outline stops
    being convex. Depth then falls out of the shape instead of being drawn on top of it.
    """
    nv, nu = water.shape
    dist = np.full(water.shape, 1 << 20, np.int32)
    q: deque = deque()
    for v in range(nv):
        for u in range(nu):
            if not water[v, u]:
                dist[v, u] = 0
                q.append((v, u))
    # the plan's own border is land too, or a lake touching the edge would measure as bottomless
    while q:
        v, u = q.popleft()
        d = dist[v, u] + 1
        for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = v + dv, u + du
            if 0 <= a < nv and 0 <= b < nu and dist[a, b] > d:
                dist[a, b] = d
                q.append((a, b))
    return dist


# --------------------------------------------------------------------------- the build


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PARK_WATER, **(cfg or {})}
    if not p.get("anchor"):
        raise ValueError("park_water needs anchor: [x, y, z] - the world corner of its canvas")
    ax, ay, az = (int(q) for q in p["anchor"])
    v0, v1, u0, u1 = int(p["v0"]), int(p["v1"]), int(p["u0"]), int(p["u1"])
    gy = int(p["ground_y"])
    seed = int(p["seed"])
    nv, nu = v1 - v0 + 1, u1 - u0 + 1
    ny = 14                                     # Y199..Y212: three courses of basin, ten above
    if gy - ay < 3:
        raise ValueError("the anchor must sit at least three courses below the ground course")

    c = Canvas(nv, ny, nu, donors)
    c.world_origin = (ax, ay, az)
    world = _World(p.get("world"), gy)

    GY = gy - ay                                # the canvas row the lawn / water surface occupies
    states: dict[tuple, int] = {}
    refused: list[str] = []
    dig: set[tuple[int, int, int]] = set()

    def blk(name: str, **props) -> int:
        key = (name, tuple(sorted(props.items())))
        if key not in states:
            states[key] = c.raw_state(name, **props) if props else c.state(name)
        return states[key]

    def wx(x: int) -> int: return ax + x
    def wy(y: int) -> int: return ay + y
    def wz(z: int) -> int: return az + z

    def put(x: int, y: int, z: int, name: str, **props) -> bool:
        """One cell, and the whole safety story is here.

        A cell the world already holds is REFUSED unless it is lawn - the park's paving, its lamp
        masts, its benches and the Signal Heron are all things this design must go round, and a
        silent skip would leave a hole in a lake that audits perfectly clean. A lawn cell is
        broken instead, and recorded in the dig list, because a litematic cannot say "remove this".
        """
        if not (0 <= x < nv and 0 <= y < ny and 0 <= z < nu):
            return False
        held = world.name(wx(x), wy(y), wz(z))
        if held != "air":
            if held not in REPLACEABLE:
                refused.append(f"{name} at V{v0 + x} Y{wy(y)} U{u0 + z} - the world holds {held}")
                return False
            dig.add((wx(x), wy(y), wz(z)))
        c.put(x, y, z, blk(name, **props))
        return True

    def has(x: int, y: int, z: int) -> bool:
        return c.solid(x, y, z)

    def solid_here(x: int, y: int, z: int) -> bool:
        """Solid in the FINISHED world: this design's cell, or the world's own block."""
        if not (0 <= x < nv and 0 <= y < ny and 0 <= z < nu):
            return True                         # outside the box the park's plate carries on
        if c.solid(x, y, z):
            n = c.get_name(x, y, z)
            return n not in ("water", "seagrass", "lily_pad", "air")
        return world.solid(wx(x), wy(y), wz(z))

    # ------------------------------------------------------------------ 1. the plan
    quay_face = int(p["terrace_v"]) + int(p["terrace_deep"]) + int(p["quay_deep"])
    edges = _shore(p, u0, u1, quay_face)
    lake = np.zeros((nv, nu), bool)
    shoal = np.zeros((nv, nu), bool)
    for x in range(nv):
        v = v0 + x
        for z in range(nu):
            u = u0 + z
            near, far = edges[u]
            wet = near <= v <= far
            if _inside(v, u, p["shoal_v"], p["shoal_u"], p["shoal_rv"], p["shoal_ru"], 0.35):
                shoal[x, z] = True
                wet = False
            lake[x, z] = wet
    # the creek through the shoal: a wading bird stands IN water, and this is the water
    for x in range(nv):
        v = v0 + x
        for z in range(nu):
            u = u0 + z
            if not shoal[x, z]:
                continue
            if [v, u] in [list(f) for f in p["heron_feet"]]:
                continue
            if _inside(v, u, p["creek_v"], p["creek_u"], p["creek_rv"], p["creek_ru"], 2.0):
                shoal[x, z] = False
                lake[x, z] = True
    # NOTHING MAY REACH THE THRESHOLD PATHS. They stand at U170-172 and U212-214 and this design's
    # box stops at U173/U211, so the water is pulled one further in on top of that: a shoreline
    # against a street is a street with a lake edge in it.
    lake[:, 0] = False
    lake[:, -1] = False
    lake[0, :] = False
    lake[-1, :] = False

    dist = _distance_to_land(lake)
    depth = np.zeros((nv, nu), np.int8)
    depth[lake] = 1
    depth[lake & (dist >= p["deep_at"])] = 2
    depth[lake & (dist >= p["deepest_at"])] = 3

    # ------------------------------------------------------------------ 2. the basin
    for x in range(nv):
        for z in range(nu):
            d = int(depth[x, z])
            if not d:
                continue
            for k in range(d):
                put(x, GY - k, z, "water")
            a, b = BED[d]
            put(x, GY - d, z, a if hash01(x, z, seed + 2) < 0.72 else b)

    # ------------------------------------------------------------------ 3. THE SEAL
    # Every water cell, every neighbour. See the module docstring: containment is not argued from
    # the outline being right, it is walked. A basin hung under a one-block plate has open void on
    # every side below the lawn course, so most of this ring is genuinely load-bearing.
    sealed = 0
    for y in range(GY, GY - 4, -1):
        for x in range(nv):
            for z in range(nu):
                if not (0 <= y < ny) or not has(x, y, z) or c.get_name(x, y, z) != "water":
                    continue
                for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
                    if solid_here(x + dx, y + dy, z + dz):
                        continue
                    if put(x + dx, y + dy, z + dz, WALL):
                        sealed += 1

    # ------------------------------------------------------------------ 4. the shore
    land = ~lake
    to_water = _distance_to_land(land)          # over LAND cells: how far from the water
    strand = 0
    for x in range(nv):
        for z in range(nu):
            if lake[x, z]:
                continue
            d = int(to_water[x, z])
            if d < 1 or d > 4:
                continue
            # A HARD LINE IS TWO SURFACES BUTTED TOGETHER. The shingle thins with distance so the
            # lawn BECOMES the beach - the Lowland Stair's dithered gradient, laid flat.
            odds = (1.0, 0.78, 0.45, 0.18)[d - 1]
            if hash01(x, z, seed + 5) > odds:
                continue
            pick = SHINGLE[min(3, max(0, d - 1 + (1 if hash01(x, z, seed + 6) < 0.35 else 0)))]
            if pick == LAWN:
                continue                        # already lawn; leave the world's own block alone
            if put(x, GY, z, pick):
                strand += 1

    # ------------------------------------------------------------------ 5. the Look-Out Terrace
    tv0 = int(p["terrace_v"])
    tv1 = tv0 + int(p["terrace_deep"]) - 1                       # deck, one course up
    qv0, qv1 = tv1 + 1, tv1 + int(p["quay_deep"])                # quay, at lawn level
    tu0, tu1 = int(p["terrace_u0"]), int(p["terrace_u1"])
    stair_u = set(int(q) for q in p["stair_u"])
    deck = 0

    def _reach(u: int) -> float:
        """Frontier stone brick into Midway smooth stone, dithered across the reach - the same
        transition `parkways` runs through every reach, so the terrace belongs to both lands."""
        return min(1.0, max(0.0, (u - 169) / 46.0))

    for u in range(tu0, tu1 + 1):
        z = u - u0
        t = _reach(u)
        for v in range(tv0, tv1 + 1):
            x = v - v0
            edge = v in (tv0, tv1) or u in (tu0, tu1)
            if edge:
                name = "polished_blackstone_bricks"
            else:
                band = (v - tv0) % 3 == 1
                core = "smooth_stone" if hash01(x, z, seed + 9) < t else "stone_bricks"
                name = "cracked_stone_bricks" if band and hash01(x, z, seed + 11) < 0.4 else core
            if put(x, GY + 1, z, name):
                deck += 1
        # the approach: a stair skirt on the lawn side, ascending EAST onto the deck (+V is +x)
        put(tv0 - 1 - v0, GY + 1, z, "stone_brick_stairs",
            facing="east", half="bottom", shape="straight")
        # the quay, at the water's own level, in front of the retaining course
        for v in range(qv0, qv1 + 1):
            x = v - v0
            if lake[x, z]:
                continue
            name = "polished_blackstone_bricks" if v == qv1 else "stone_bricks"
            put(x, GY, z, name)

    # the balustrade, and the three flights down through it
    for u in range(tu0, tu1 + 1):
        z = u - u0
        gap = any(abs(u - s) <= 1 for s in stair_u)
        if gap:
            # a flight down to the quay: ascending WEST, toward the deck, per the stair convention
            put(qv0 - v0, GY + 1, z, "stone_brick_stairs",
                facing="west", half="bottom", shape="straight")
        else:
            put(tv1 - v0, GY + 2, z, "stone_brick_wall", up="true",
                north="none", south="none", east="none", west="none", waterlogged="false")

    # benches looking at the water, and lamps on the park's own idiom
    #
    # PLACED BY NAME, NOT BY MODULUS. Written as `(u - tu0) % 5 in (0, 1)` against a separate
    # rule keeping seats clear of the flights, the two rhythms cancelled: of ten benches EIGHT
    # were suppressed and the terrace shipped with two. A run of seats is a decision about where
    # people sit, so it is stated.
    lamps = benches = 0
    for a, b in p["bench_u"]:
        for u in range(int(a), int(b) + 1):
            z = u - u0
            if any(abs(u - s) <= 1 for s in stair_u):
                continue
            # A SEAT'S BACKREST IS ITS TALL SIDE, so a bench facing WEST seats you looking EAST,
            # at the lake. Asserted rather than eyeballed: our renderer draws both alike.
            if put(tv0 + 2 - v0, GY + 2, z, "oak_stairs",
                   facing="west", half="bottom", shape="straight"):
                benches += 1
            put(tv0 + 1 - v0, GY + 2, z, "oak_trapdoor", facing="east", half="top",
                open="false", powered="false", waterlogged="false")
    for u in p["lamp_u"]:
        z = int(u) - u0
        x = tv0 + 5 - v0
        put(x, GY + 2, z, "chiseled_stone_bricks")
        put(x, GY + 3, z, "lightning_rod", facing="up", powered="false")
        if put(x, GY + 4, z, "lantern", hanging="false", waterlogged="false"):
            lamps += 1

    # ------------------------------------------------------------------ 6. the Boardwalk
    wv0 = int(p["walk_v"])
    wv1 = wv0 + int(p["walk_wide"]) - 1
    bay = set()
    for v in range(int(p["bay_v"]), wv0):
        for u in range(int(p["bay_u0"]), int(p["bay_u1"]) + 1):
            bay.add((v, u))
    walk = {(v, u) for v in range(wv0, wv1 + 1) for u in range(u0, u1 + 1)} | bay
    piers = 0
    for v, u in sorted(walk):
        x, z = v - v0, u - u0
        t = _reach(u)
        name = "oak_planks" if hash01(x, z, seed + 13) < t else "spruce_planks"
        put(x, GY + 1, z, name)
    # rails, and the two ends left open so you can walk on
    for v, u in sorted(walk):
        x, z = v - v0, u - u0
        if u in (u0, u1):
            continue
        if all((v + dv, u + du) in walk for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        post = "oak_fence" if hash01(x, z, seed + 13) < _reach(u) else "spruce_fence"
        put(x, GY + 2, z, post, north="false", south="false", east="false", west="false",
            waterlogged="false")
        if u % int(p["walk_lamp_every"]) == 0:
            put(x, GY + 3, z, post, north="false", south="false", east="false", west="false",
                waterlogged="false")
            if put(x, GY + 4, z, "lantern", hanging="false", waterlogged="false"):
                lamps += 1
    # piles, from the deck down to the bed - the reason the water runs UNDER the crossing
    for v, u in sorted(walk):
        x, z = v - v0, u - u0
        if not lake[x, z] or u % int(p["pier_every"]) != 0:
            continue
        if not (v in (wv0, wv1) or (v, u) in bay and v == int(p["bay_v"])):
            continue
        for k in range(int(depth[x, z])):
            if put(x, GY - k, z, "spruce_log", axis="y"):
                piers += 1
    # benches in the bay, looking back down the lake at the terrace
    for u in range(int(p["bay_u0"]) + 1, int(p["bay_u1"])):
        z = u - u0
        if (u - int(p["bay_u0"])) % 2:
            put(int(p["bay_v"]) + 1 - v0, GY + 2, z, "oak_stairs",
                facing="east", half="bottom", shape="straight")
    # the two landings: a half step up off the lawn onto the deck, ascending toward the water
    for v in range(wv0, wv1 + 1):
        x = v - v0
        put(x, GY + 1, 0, "oak_stairs", facing="south", half="bottom", shape="straight")
        put(x, GY + 1, nu - 1, "oak_stairs", facing="north", half="bottom", shape="straight")

    # ------------------------------------------------------------------ 7. planting
    hv0, hu0, hv1, hu1 = p["heron_clear"]
    built = {(v, u) for v in range(v0, v1 + 1) for u in range(u0, u1 + 1)
             if c.solid(v - v0, GY + 1, u - u0)}
    plants = lilies = weed = 0
    for x in range(nv):
        for z in range(nu):
            v, u = v0 + x, u0 + z
            if hv0 <= v <= hv1 and hu0 <= u <= hu1:
                continue                        # the Signal Heron's own ground stays bare
            if (v, u) in built or (v, u) in walk:
                continue
            d = int(depth[x, z])
            if d:
                # lilies on the shallow shelf only, and weed a course under the surface where it
                # cannot be mistaken for something growing out of the water
                if d == 1 and hash01(x, z, seed + 17) < p["lily_frac"]:
                    if put(x, GY + 1, z, "lily_pad"):
                        lilies += 1
                elif d >= 2 and hash01(x, z, seed + 19) < p["seagrass_frac"]:
                    if put(x, GY - 1, z, "seagrass"):
                        weed += 1
                continue
            if world.name(wx(x), wy(GY), wz(z)) != LAWN or c.solid(x, GY, z):
                continue                        # only the living lawn carries a plant
            dw = int(to_water[x, z])
            if dw > 9:
                continue
            odds = 0.22 if dw <= 3 else 0.10
            h = hash01(x, z, seed + 23)
            if h > odds:
                continue
            pick = ("short_grass", "fern", "azalea", "flowering_azalea",
                    "tall_grass")[int(hash01(x, z, seed + 29) * 5) % 5]
            if pick == "tall_grass":
                if put(x, GY + 1, z, "tall_grass", half="lower") and \
                        put(x, GY + 2, z, "tall_grass", half="upper"):
                    plants += 1
                continue
            if put(x, GY + 1, z, pick):
                plants += 1

    # a few trees on the far bank, so the lake has a far side worth looking at
    trees = 0
    for tv, tu in p["trees"]:
        x, z = int(tv) - v0, int(tu) - u0
        if not (0 <= x < nv and 0 <= z < nu) or lake[x, z] or (tv, tu) in walk:
            continue
        ok = True
        for k in range(4):
            ok &= put(x, GY + 1 + k, z, "oak_log", axis="y")
        for dy, r in ((3, 2), (4, 2), (5, 1)):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if abs(dx) == r and abs(dz) == r:
                        continue
                    if dx == 0 and dz == 0 and dy < 5:
                        continue
                    put(x + dx, GY + 1 + dy, z + dz, "oak_leaves",
                        distance="1", persistent="true", waterlogged="false")
        trees += 1 if ok else 0

    # ------------------------------------------------------------------ 8. the light
    glow, rounds, worst = _light_the_water(c, world, p, GY, ax, ay, az)

    # ------------------------------------------------------------------ 9. the dig list
    # A moss carpet standing on a cell that becomes water would be left floating on the lake, and
    # nothing in the pipeline would say so: the carpet is not a collision, it is a leftover.
    for x in range(nv):
        for z in range(nu):
            if not c.solid(x, GY, z):
                continue
            if world.name(wx(x), wy(GY + 1), wz(z)) == LAWN_TRIM and not c.solid(x, GY + 1, z):
                dig.add((wx(x), wy(GY + 1), wz(z)))

    if refused:
        raise ValueError(f"park_water: {len(refused)} cell(s) the world already holds and this "
                         f"design must not take - " + "; ".join(refused[:6]))

    water_cells = int(sum(1 for x in range(nv) for z in range(nu) for k in range(int(depth[x, z]))))
    c.meta = {
        "kind": "park_water",
        "land": "reach",
        "facing": "east",
        "profile_axis": "u",
        "band": [v0, u0, v1, u1],
        "surface_y": gy,
        "water_cells": water_cells,
        "surface_cells": int(lake.sum()),
        "shallow": int((depth == 1).sum()), "mid": int((depth == 2).sum()),
        "deep": int((depth == 3).sum()),
        "seal_cells": sealed, "strand_cells": strand, "deck_cells": deck,
        "piers": piers, "lamps": lamps, "benches": benches,
        "glow": glow, "glow_rounds": rounds,
        "darkest_water": worst,
        "lilies": lilies, "seagrass": weed, "plants": plants, "trees": trees,
        "dig": sorted(list(d) for d in dig),
        "contract": (
            "one lake on the Claim Line reach whose every water cell is enclosed - solid bed "
            "below and a solid neighbour on all four sides - and lit to at least "
            f"{p['light_floor']} so it cannot freeze; a shingle shore dithered into the park's "
            "lawn; a terrace and a boardwalk to stand on; and not one cell on any street, path, "
            "plaza, verge, lamp or building"),
    }
    return c


# --------------------------------------------------------------------------- light


def _light_the_water(c: Canvas, world: _World, p: dict, GY: int, ax: int, ay: int, az: int):
    """Set `ochre_froglight` into the bed until no water cell is dark enough to freeze.

    A FIXPOINT, NOT ONE PASS - the night pass's own rule. Placing a light changes the model the
    answer was computed against, so the propagation is re-run and the remainder re-solved. Each
    round the darkest cells are taken in turn and the coverage a new light buys is claimed, so one
    round places a spread-out set rather than a clump.

    The lights go in the BED, never on the surface and never on a bank: a bank lantern reaches
    four blocks of water and this lake is sixty across, and a fixture standing in a lake is a
    fixture standing in a lake. Under two courses of water a froglight reads as a pale patch of
    the bed by day, and as a lake lit from within at night.

    **THE DEEP CORE IS WHAT A BED LIGHT COSTS, AND IT IS ARITHMETIC RATHER THAN TASTE.** Light
    falls one a block, so a bed light under `d` courses of water reaches the surface with `15 - d`
    and spreads `15 - d - target` sideways from there: at three courses deep that is ONE block,
    and a solid deep core eats a light every other column. So a light in a deep column is a small
    GLOWING MOUND rather than a flat patch - it is stacked until its top stands two courses below
    the surface, which puts every emitter in the lake on one horizontal budget whatever the depth
    is. The first version did not, and shipped 492 froglights - a quarter of the bed.
    """
    from .. import nightlight

    floor, target = int(p["light_floor"]), int(p["light_target"])
    rounds = int(p["light_rounds"])
    surface = GY
    ny, nu, nv = c.ids.shape
    glow = 0
    worst = 0
    r = 0
    for r in range(1, rounds + 1):
        names = [q.value["Name"].value for q in c.palette]
        opaque_p, emit_p, _passy, _spawn, water_p = nightlight.classify(names)
        opaque = opaque_p[c.ids]
        emit = emit_p[c.ids].astype(np.int16)
        # THE PARK'S OWN LAWN IS PART OF THE MODEL. Every column of this box holds moss at the
        # ground course; leaving those cells air lets light leak sideways under the bank and
        # reports a lake brighter than it is.
        empty = c.ids[GY] == 0
        opaque[GY][empty] = True
        light = nightlight.propagate(opaque, emit)
        water = water_p[c.ids]
        dark = water & (light < target)
        worst = int(light[water].min()) if water.any() else 15
        if not dark.any():
            break
        # take the darkest first, and claim what each new light covers so one round spreads out
        idx = np.argwhere(dark)
        order = sorted(idx.tolist(), key=lambda q: int(light[q[0], q[1], q[2]]))
        claimed = np.zeros_like(dark)
        placed = 0
        for y, z, x in order:
            if claimed[y, z, x]:
                continue
            # the bed under this column: walk down to the first cell that is not water
            b = y
            while b - 1 >= 0 and water[b - 1, z, x]:
                b -= 1
            b -= 1
            if b < 0 or not c.solid(x, b, z):
                continue
            if world.name(ax + x, ay + b, az + z) != "air":
                continue                        # never break something the world owns for a lamp
            top = min(surface - 2, b + 2)       # a mound, never higher than two under the surface
            ok = True
            for yy in range(b, max(b, top) + 1):
                if yy != b and not water[yy, z, x]:
                    ok = False
                    break
                if world.name(ax + x, ay + yy, az + z) != "air":
                    ok = False
                    break
            if not ok:
                continue
            for yy in range(b, max(b, top) + 1):
                c.put(x, yy, z, c.state(GLOW))
                glow += 1
            placed += 1
            reach = 15 - target
            head = max(b, top)
            for yy in range(max(0, head - reach), min(ny, head + reach + 1)):
                for zz in range(max(0, z - reach), min(nu, z + reach + 1)):
                    for xx in range(max(0, x - reach), min(nv, x + reach + 1)):
                        if abs(yy - head) + abs(zz - z) + abs(xx - x) <= reach:
                            claimed[yy, zz, xx] = True
        if not placed:
            break
    # the honest answer is measured against the model that now holds the lights, not the one the
    # last round was solved from
    names = [q.value["Name"].value for q in c.palette]
    opaque_p, emit_p, _p2, _s2, water_p = nightlight.classify(names)
    opaque = opaque_p[c.ids]
    opaque[GY][c.ids[GY] == 0] = True
    light = nightlight.propagate(opaque, emit_p[c.ids].astype(np.int16))
    water = water_p[c.ids]
    worst = int(light[water].min()) if water.any() else 15
    if worst < floor:
        raise ValueError(f"park_water: the light solver stopped at {worst}, below the freezing "
                         f"floor of {floor} - the lake would ice over")
    return glow, r, worst


DEFAULTS = PARK_WATER
