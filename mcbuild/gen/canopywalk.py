"""THE CANOPY WALK - the Lost Plateau's route through its own treetops.

Jack, after the three park scans of 2026-09-13: *"we can add and dress more from where we are and
build upwards in smart ways."*

---------------------------------------------------------------------------------------------
WHY UP, AND WHY HERE

The scans made the park measurable for the first time, and two numbers decide this design:

  * **THE GROUND IS FULL.** Of 82,482 bare lawn columns only 20,769 are two clear of anything
    standing, and a maximal-rectangle search finds **27 free pads of 8x8 or better in the whole
    600x200**. There is nowhere left to put a module. The lawn is a mesh of verges, not plots.
  * **THE AIR IS EMPTY.** 78% of everything built sits in the twelve courses above the lawn, the
    median column has 117 courses of headroom, and the **Lost Plateau has 21 cells above Y250 in
    the entire land** - the thinnest land in the park at 2.61 blocks per column.

So the one direction left is up, and the Lost Plateau is where it is worth most. A canopy walk is
also the one upward thing that costs NO ground: it stands on piers in the verges, which is exactly
what the park has a surplus of.

---------------------------------------------------------------------------------------------
THE ROUTE IS FOUND, NOT DRAWN, AND THAT IS THE WHOLE DESIGN PROBLEM

Measured off `out/park_world.litematic`, the ridge is a band at z80395-80470 whose top surface runs
Y202-250 with a median of 219. Two naive answers both fail on those numbers:

  * a deck at a CONSTANT height collides with the ridge's own peaks - there are four of them over
    Y237 between x97608 and x97645, and a deck high enough to clear them (Y250+) is not a canopy
    walk, it is a viaduct over a hill;
  * a deck that FOLLOWS the surface at fixed clearance undulates Y210-252, which is a staircase.

What works is the third: **hold the deck level and move the ROUTE**. A sweep across the ridge found
a corridor at z80405-80422 where the surface sits near 220 for ninety blocks, and within that band
there is almost always a z whose surface is moderate - 28 to 61 valid choices per column of x. So
the route is a shortest-path over that field: keep the surface under the deck inside a window, and
pay for every sideways step, so the walk wanders only where the rock makes it.

**IT IS RE-DERIVED FROM THE WORLD ON EVERY BUILD.** Hard-coded waypoints would be a snapshot of one
day's ridge, and `PF Mine Ridge` is 36% built - the rock under this walk is going to keep arriving.
A route that cannot be re-found is one that goes stale the first time somebody prints a mountain.
"""
from __future__ import annotations

import numpy as np

from .. import blocks
from .canvas import Canvas, hash01
from .. import schem
from .vertical import Ctx

#: The Lost Plateau's own timber. Every one is cheap, 1.19, and witnessed on this server.
JUNGLE = {
    "deck": "jungle_planks",
    "slab": "jungle_slab",
    "stair": "jungle_stairs",
    "rail": "jungle_fence",
    "post": "jungle_log",
    "trim": "stripped_jungle_log",
    "lamp": "ochre_froglight",
    "leaf": "jungle_leaves",
}

WALK = {
    "under": None,            # the world; the ROUTE is measured off it
    "anchor": None,           # [v, y, u] world origin of the lot
    "lot": None,              # [dv, du]
    "at": [0, 0],
    "sy": 64,
    # the corridor the route may wander inside, in LOT coordinates
    "v0": 55, "v1": 145,      # V is world X: the walk runs along it
    "u_mid": 110, "u_slack": 9,
    "deck_y": 228,
    #: A column is only a candidate if the rock under the deck leaves headroom AND is close
    #: enough that a pier is a pier rather than a tower.
    "clear_min": 3,
    "clear_max": 16,
    "turn_cost": 2.2,
    "width": 3,
    "pier_every": 6,
    "lamp_every": 9,
    "seed": 73,
    #: **THE RIDE, WHICH IS NOT IN THE WORLD THE ROUTE IS MEASURED OFF.** `under` is a CAPTURE and
    #: a capture holds only what is BUILT - the Mine Coaster is 62% placed, and every one of the
    #: 81 cells this walk took off it was in the unbuilt 38%, so `finish.verify_against` reported
    #: overlap 0 honestly while two piers ran down through the ride's trestle and five cells of
    #: timber stood in the two courses over live track. Read in the SAME lot frame
    #: `gen/mineridge.py` uses, because both designs are placed from the same park anchor.
    "ride": None,
    "ride_at": [0, 0],        # the ride's lot origin, in THIS lot's coordinates
    "ride_plane": 13,         # courses of the ride's own canvas that sit below the park's plane
    "ride_clear": 2,          # courses over a rail a rider occupies
}


def _ride_keepout(p: dict, ay: int, dv: int, du: int) -> tuple[set, set]:
    """(the ride's own cells, the clearance a rider needs) as (v, u, world Y).

    **A SHARED TERRAIN CELL IS A WORK PROBLEM AND A SHARED TRACK IS A BROKEN RIDE**, so the two
    sets are kept apart and reported apart. What the ride OWNS may not be built into; what a rider
    passes through may not be built into either, and neither can be seen by an audit against a
    capture, because the cells in question have not been placed yet.
    """
    if not p.get("ride"):
        return set(), set()
    m = schem.load(str(p["ride"]))
    sol = m.solid()                                   # [y, U, V]
    names = [n.split("[")[0].split(":")[-1] for n in m.names]
    is_rail = np.isin(m.ids, [i for i, n in enumerate(names) if n.endswith("rail")])
    plane = int(p.get("ride_plane", 13))
    rv, ru = (int(x) for x in (p.get("ride_at") or (0, 0)))
    own, env = set(), set()
    for y, u, v in zip(*sol.nonzero()):
        if y < plane:
            continue
        a, b = int(v) + rv, int(u) + ru
        if 0 <= a < dv and 0 <= b < du:
            own.add((a, b, ay + int(y) - plane))
    for y, u, v in zip(*is_rail.nonzero()):
        if y < plane:
            continue
        a, b = int(v) + rv, int(u) + ru
        wy = ay + int(y) - plane
        for d in range(1, int(p.get("ride_clear", 2)) + 1):
            if 0 <= a < dv and 0 <= b < du:
                env.add((a, b, wy + d))
    return own, env - own


def _surface(ctx: Ctx, ax: int, az: int, dv: int, du: int, y_top: int,
             vs=None, us=None) -> np.ndarray:
    """The highest solid cell in each column, as a world Y. 0 where nothing stands.

    **SCOPED TO THE CORRIDOR.** Over the whole lot this is 22,400 columns times thirty-odd courses
    of world lookup for a route that can only ever wander inside a nineteen-cell band; the corridor
    is 1,729 columns and answers the same question.
    """
    out = np.zeros((dv, du), np.int32)
    for v in (vs if vs is not None else range(dv)):
        for u in (us if us is not None else range(du)):
            if not (0 <= v < dv and 0 <= u < du):
                continue
            x, z = ax + v, az + u
            for y in range(y_top, 195, -1):
                if ctx.occupied(x, y, z):
                    out[v, u] = y
                    break
    return out


def route(surf: np.ndarray, p: dict, ride: set | None = None) -> list[tuple[int, int]]:
    """A least-cost line along V through the corridor, as [(v, u), ...].

    **THE COST IS THE ROCK, NOT THE DISTANCE.** Every column of V must be crossed, so length is
    fixed and the only free choice is U. A column is legal when the deck clears the surface under
    it by `clear_min` and stands no more than `clear_max` over it - the first keeps the walk out of
    the rock, the second keeps a pier from becoming a tower. Among the legal ones the walk prefers
    to go STRAIGHT: `turn_cost` per cell of sideways movement is what stops a least-cost path
    slaloming for a block of clearance nobody can see.
    """
    v0, v1 = int(p["v0"]), int(p["v1"])
    um, us = int(p["u_mid"]), int(p["u_slack"])
    deck, cmin, cmax = int(p["deck_y"]), int(p["clear_min"]), int(p["clear_max"])
    turn = float(p["turn_cost"])
    us_lo, us_hi = um - us, um + us
    width = range(us_lo, us_hi + 1)
    ride = ride or set()
    #: The courses the walk itself occupies over a column: the deck, and the rail standing on it.
    #: A pier is below and is refused at placement - but the DECK is the thing that cannot move
    #: cell by cell, so a column the ride stands in has to be refused by the ROUTE or the walk
    #: arrives there and is holed.
    band = range(deck, deck + 3)

    def legal(v, u):
        """**THE ONLY HARD RULE IS NOT BEING INSIDE THE ROCK.**

        `clear_max` was a gate here and it made the route impossible: four columns of the ridge
        (x97618-97623) are a SADDLE where the rock is either 18-26 courses below the deck or two
        above it, and a gate on both ends refuses the lot. But a walkway does not need ground under
        every column - it needs ground under its PIERS, and it SPANS what is between them. So being
        far above the rock is a cost, and a run of it is a span, bounded by `max_span` after the
        route is found. Being INSIDE the rock is still fatal.
        """
        s = int(surf[v, u])
        if any((v, u, y) in ride for y in band):
            return False
        return s == 0 or deck - s >= cmin

    INF = float("inf")
    cost = {u: (0.0 if legal(v0, u) else INF) for u in width}
    back: list[dict] = [{}]
    for v in range(v0 + 1, v1 + 1):
        nxt, bk = {}, {}
        for u in width:
            if not legal(v, u):
                nxt[u] = INF
                continue
            best, arg = INF, None
            for pu in width:
                if cost[pu] == INF:
                    continue
                # **ONE CELL OF SIDEWAYS PER CELL OF FORWARD.** Left free, the least-cost path
                # jumps several cells of u between adjacent columns of v - and a three-wide deck
                # whose next course starts three cells over is not joined to it. The first build
                # came out in SIX pieces for exactly that, and a walkway does not teleport.
                if abs(u - pu) > 1:
                    continue
                drop = deck - int(surf[v, u]) if surf[v, u] else deck - 202
                # near the rock is cheap; past `clear_max` the cost rises hard, so the route
                # crosses a saddle only where it must and never wanders out over the lawn.
                over = max(0, drop - cmax)
                c = cost[pu] + turn * abs(u - pu) + abs(drop - 8) * 0.15 + over * 1.8
                if c < best:
                    best, arg = c, pu
            nxt[u], bk[u] = best, arg
        cost, _ = nxt, back.append(bk)
    end = min((c, u) for u, c in cost.items())
    if end[0] == INF:
        raise ValueError("no legal canopy route through the corridor - the rock or the ride "
                         "closes it; widen u_slack, move deck_y, or shorten v0/v1")
    path = [(v1, end[1])]
    for i in range(len(back) - 1, 0, -1):
        v, u = path[-1]
        path.append((v - 1, back[i][u]))
    path.reverse()

    # **A SPAN IS BOUNDED.** A walkway crosses a dip; it does not fly. A run of columns with no
    # rock within `clear_max` is unsupported deck, and past `max_span` of it the design is lying
    # about being carried - so it says so rather than shipping a bridge with no piers.
    span = worst = 0
    for (v, u) in path:
        s = int(surf[v, u])
        if s and deck - s <= cmax:
            span = 0
        else:
            span += 1
            worst = max(worst, span)
    if worst > int(p.get("max_span", 14)):
        raise ValueError(f"the route crosses {worst} columns with nothing to stand a pier on - "
                         f"raise max_span deliberately or move the corridor")
    return path


class _Walk:
    """The canvas in LOT coordinates, with the world beside it so nothing is placed into rock."""

    def __init__(self, c: Canvas, ctx: Ctx, anchor, at, dv, du, ride=None, rider=None):
        self.c, self.ctx = c, ctx
        self.ax, self.ay, self.az = anchor[0] + at[0], anchor[1], anchor[2] + at[1]
        self.dv, self.du = dv, du
        self.refused = 0
        # KEPT APART, because they are different faults: one is two designs contending for a cell,
        # the other is a beam in the face of somebody riding past.
        self.ride, self.rider = ride or set(), rider or set()
        self.ride_refused = self.rider_refused = self.cables_declined = 0

    def world(self, v, u, y):
        return self.ax + v, y, self.az + u

    def free(self, v, u, y) -> bool:
        x, wy, z = self.world(v, u, y)
        return not self.ctx.occupied(x, wy, z)

    def put(self, v, u, y, name, **props) -> bool:
        """Never into rock, never over the lot edge. A refusal is COUNTED, not swallowed."""
        if not (0 <= v < self.dv and 0 <= u < self.du):
            self.refused += 1
            return False
        if (v, u, y) in self.ride:
            self.ride_refused += 1
            return False
        if (v, u, y) in self.rider:
            self.rider_refused += 1
            return False
        if not self.free(v, u, y):
            self.refused += 1
            return False
        return self.c.put(v, y - self.ay, u, self.c.state(name, **props))


def _deck(w: _Walk, path, p) -> int:
    """The walking surface: planks, with a TOP SLAB kerb either side.

    A `type=top` slab's own top face is the cell boundary, so the kerb is walked on exactly like a
    plank and costs half the timber - the cut-course rule this repo measured against
    `reference/amazingsteal`, where 66% of all slabs are `type=top` against our 10%.
    """
    y = int(p["deck_y"])
    half = max(1, int(p["width"]) // 2)
    n = 0
    for (v, u) in path:
        # **`width` IS THE WALKABLE WIDTH, AND THE RAIL STANDS OUTSIDE IT.** Laid with the rail ON
        # the deck's own kerb, a three-wide walk has ONE clear lane - the first build gave 128
        # standable cells for 91 columns of deck, which is a plank, not a walk.
        laid = {}
        for du_ in range(-half, half + 1):
            laid[du_] = bool(w.put(v, u + du_, y, JUNGLE["deck"]))
        n += sum(laid.values())
        # **A KERB NEEDS THE LANE CELL BESIDE IT, not merely a lane somewhere in this column.**
        # Where the rock refuses the outermost plank the kerb has nothing to be the edge OF and
        # ships as a one-cell island of slab - which is what it did.
        for s in (-1, 1):
            if laid.get(s * half):
                n += bool(w.put(v, u + s * (half + 1), y, JUNGLE["slab"],
                                type="top", waterlogged="false"))
    return n


def _rails(w: _Walk, path, p) -> int:
    y = int(p["deck_y"]) + 1
    half = max(1, int(p["width"]) // 2) + 1      # the rail stands OUTSIDE the walking surface
    n = 0
    for (v, u) in path:
        for s in (-1, 1):
            n += bool(w.put(v, u + s * half, y, JUNGLE["rail"], waterlogged="false"))
    return n


def _piers(w: _Walk, path, surf, p) -> int:
    """A post down to the rock, and it stops ON the rock rather than at a computed height.

    **ANYTHING CLINGING IS ANCHORED TO WHAT IS THERE** - this repo has hung a mane, a pair of
    ossicones and a tail off computed radii and had all three come away. A pier walks down until
    the world stops it, and a column whose rock never arrives simply gets no pier rather than a
    post ending in mid-air.
    """
    y = int(p["deck_y"])
    every = max(2, int(p["pier_every"]))
    half = max(1, int(p["width"]) // 2) + 1      # under the kerb, not under the lane
    n = 0
    for i, (v, u) in enumerate(path):
        if i % every:
            continue
        for s in (-1, 1):
            uu = u + s * half
            if not (0 <= v < w.dv and 0 <= uu < w.du):
                continue
            seated = False
            for yy in range(y - 1, y - int(p["clear_max"]) - 3, -1):
                if not w.free(v, uu, yy):
                    seated = True
                    break
                n += bool(w.put(v, uu, yy, JUNGLE["post"], axis="y"))
            if not seated:                       # nothing to stand on: take the post back out
                for yy in range(y - 1, y - int(p["clear_max"]) - 3, -1):
                    w.c.put(v, yy - w.ay, uu, 0)
    return n


def _lamps(w: _Walk, path, p) -> int:
    """Set INTO the kerb, never standing on the deck. A lantern on a three-wide walk is a bollard."""
    y = int(p["deck_y"])
    half = max(1, int(p["width"]) // 2) + 1      # set INTO the kerb
    every = max(3, int(p["lamp_every"]))
    n = 0
    for i, (v, u) in enumerate(path):
        if i % every:
            continue
        s = 1 if (i // every) % 2 else -1
        n += bool(w.put(v, u + s * half, y, JUNGLE["lamp"]))
    return n


def _stairhead(w: _Walk, v, u, p, inward: int) -> int:
    """A flight from the deck down to whatever the rock is at this end.

    **A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD `facing=D`, `half=bottom`** - read off Jack's
    own stairs and asserted in `tests/test_stairhead.py`, because our renderer draws a backwards
    flight identically to a right one. This one descends away from the walk, so a rider climbing it
    is heading back along `inward` and every tread faces that way.
    """
    y = int(p["deck_y"])
    n = 0
    for k in range(1, 40):
        vv = v + inward * k
        if not (0 <= vv < w.dv):
            break
        yy = y - k
        n += bool(w.put(vv, u, yy, JUNGLE["stair"],
                        facing=("west" if inward > 0 else "east"), half="bottom",
                        shape="straight", waterlogged="false"))
        for s in (-1, 1):
            n += bool(w.put(vv, u + s, yy, JUNGLE["deck"]))
            n += bool(w.put(vv, u + s, yy + 1, JUNGLE["rail"], waterlogged="false"))
        # landed? the next course down is rock
        if not w.free(vv, u, yy - 1):
            break
    return n


def _spans(path, surf, p):
    """Runs of deck with no rock within `clear_max` under them - the bits that are BRIDGE."""
    deck, cmax = int(p["deck_y"]), int(p["clear_max"])
    runs, cur = [], []
    for (v, u) in path:
        s = int(surf[v, u])
        if s and deck - s <= cmax:
            if cur:
                runs.append(cur); cur = []
        else:
            cur.append((v, u))
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 4]


def _truss(w: _Walk, path, surf, p) -> int:
    """A suspension bay over every real span, because a span should LOOK carried.

    The ridge has a saddle at x97618-97635 with no supportable ground at any corridor width - the
    route is forced across eighteen columns of open air whatever `u_slack` is, which the sweep
    confirmed at 9, 12, 15 and 18. Deck alone there reads as a plank floating over a gap. A pylon
    at each end and a fence catenary between them says the span is spanned, and it is the one place
    on the walk where the structure is the thing you look at.
    """
    y = int(p["deck_y"])
    half = max(1, int(p["width"]) // 2) + 1
    tall = int(p.get("pylon", 5))
    n = 0

    def pylon(v, u, s) -> int:
        """**A PYLON IS ALL OR NOTHING**, and it steps inward rather than being built with holes.

        The ride keep-out refuses cell by cell, which on a mast leaves a floating fragment - seven
        of them the first time this ran beside the coaster. `_piers` already states the rule for
        the other end of the same post (*"nothing to stand on: take the post back out"*); this is
        it upward. A mast that cannot stand where the span ends is tried a few cells along the run
        before it is given up on, because a bay whose pylon is missing is a plank over a gap.
        """
        cells = [(v, u + s * half, y + k) for k in range(1, tall + 1)]
        if all(w.put(a, b, c, JUNGLE["post"], axis="y") for a, b, c in cells):
            return len(cells)
        for a, b, c in cells:                       # take back whatever went in
            w.c.put(a, c - w.ay, b, 0)
        return 0

    for run in _spans(path, surf, p):
        ends = []
        for end, step in ((run[0], +1), (run[-1], -1)):
            i = run.index(end)
            for k in range(0, 4):                   # nominal end, then a few cells INTO the span
                j = i + step * k
                if not (0 <= j < len(run)):
                    break
                v, u = run[j]
                got = sum(pylon(v, u, s) for s in (-1, 1))
                if got:
                    n += got
                    ends.append((v, u))
                    break
        if len(ends) < 2:                           # no mast at one end: the bay is not a bay
            continue
        run = run[run.index(ends[0]):run.index(ends[1]) + 1] or run
        # the catenary: a fence line along the top, dipping one course at mid-span
        # **THE CABLE IS ONE CELL WIDE, SO EVERY STEP IT TAKES HAS TO BE THREADED.** The deck gets
        # away with a sideways step because it is three wide and the courses overlap; a single line
        # of fence does not, and neither does a change of sag. Both came out as diagonal-only joins
        # - ten stray cells at Y232-233 - which is the ear-tip rule this repo has already paid for
        # on a mane, a pair of ossicones and a tail. The corner is filled ONE AXIS AT A TIME.
        for s in (-1, 1):
            # **THE CABLE IS LEVEL.** A sagging one changes course mid-run, and every change is a
            # join - the sag shipped a seven-cell chain of fence that never rejoined its own line.
            # A catenary is worth nothing if it arrives as a stray.
            line = [(v, u + s * half, y + tall) for (v, u) in run]
            # **A CABLE RUNS THE WHOLE SPAN OR IT IS NOT STRUNG.** One refused cell breaks a
            # one-wide line and everything after it is a stray, so laying it and stopping leaves
            # debris the prune then hides. Here the refusal is the COASTER: its lift hill climbs
            # y236 to y244 through u101-103 across this span, which is above any pylon worth
            # building, so the cable cannot cross it and should not pretend to. The masts stand,
            # the deck passes under the ride, and `truss_cables_declined` says it happened.
            if any((cv, cu, cy) in w.ride or (cv, cu, cy) in w.rider or not w.free(cv, cu, cy)
                   for cv, cu, cy in line):
                w.cables_declined += 1
                continue
            for j, (cv, cu, cy) in enumerate(line):
                n += bool(w.put(cv, cu, cy, JUNGLE["rail"], waterlogged="false"))
                if j:
                    pv, pu, py = line[j - 1]
                    for uu in range(min(pu, cu), max(pu, cu) + 1):
                        n += bool(w.put(pv, uu, py, JUNGLE["rail"], waterlogged="false"))
                    for yy in range(min(py, cy), max(py, cy) + 1):
                        n += bool(w.put(pv, cu, yy, JUNGLE["rail"], waterlogged="false"))
                # HANGERS: the cable carries the deck, so every so often it is seen to - and a
                # hanger that cannot reach the deck is a fence hanging in the air, so it is taken
                # back out rather than left as the prune's problem.
                if j and j % 4 == 0 and j != len(line) - 1:
                    drop = [(cv, cu, yy) for yy in range(y + 2, cy)]
                    if all(w.put(a, b, c, JUNGLE["rail"], waterlogged="false") for a, b, c in drop):
                        n += len(drop)
                    else:
                        for a, b, c in drop:
                            w.c.put(a, c - w.ay, b, 0)
    return n


def _prune_strays(c: Canvas, keep_min: int = 12) -> int:
    """Drop anything that came away from the walk, and REPORT it.

    Prevention is better and most of it is prevented - the deck's kerb, the cable's threading, the
    step limit on the route. What is left is the truss's corner fills near a span's own ends, and
    chasing each one by arithmetic is how `stegosaur` spent a session finding that every fix left
    another rounding corner: *a bug that passes the example you tried is the worst kind there is*.
    So the contract is GUARANTEED rather than hoped for, and the count is reported, because a walk
    that needs a lot of pruning is a walk whose geometry is wrong.
    """
    from collections import deque
    ids = c.ids
    Y, Z, X = ids.shape
    seen = np.zeros(ids.shape, bool)
    dropped = 0
    for y in range(Y):
        for z in range(Z):
            for x in range(X):
                if ids[y, z, x] == 0 or seen[y, z, x]:
                    continue
                q, cells = deque([(y, z, x)]), []
                seen[y, z, x] = True
                while q:
                    a, bq, cc = q.popleft()
                    cells.append((a, bq, cc))
                    for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                        ny, nz, nx = a + dy, bq + dz, cc + dx
                        if (0 <= ny < Y and 0 <= nz < Z and 0 <= nx < X
                                and ids[ny, nz, nx] != 0 and not seen[ny, nz, nx]):
                            seen[ny, nz, nx] = True
                            q.append((ny, nz, nx))
                if len(cells) < keep_min:
                    for (a, bq, cc) in cells:
                        ids[a, bq, cc] = 0
                    dropped += len(cells)
    return dropped


def build(cfg: dict, donors=None) -> Canvas:
    p = {**WALK, **(cfg or {})}
    for k in ("under", "anchor", "lot"):
        if not p.get(k):
            raise ValueError(f"the canopy walk needs {k}")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    at = [int(x) for x in (p.get("at") or (0, 0))]
    anchor = [int(x) for x in p["anchor"]]
    ctx = Ctx(p["under"])
    ride, rider = _ride_keepout(p, anchor[1], dv, du)
    c = Canvas(dv, int(p["sy"]), du, donors)
    w = _Walk(c, ctx, anchor, at, dv, du, ride, rider)

    um, uslack = int(p["u_mid"]), int(p["u_slack"])
    surf = _surface(ctx, w.ax, w.az, dv, du, int(p["deck_y"]) + 2,
                    vs=range(int(p["v0"]), int(p["v1"]) + 1),
                    us=range(um - uslack, um + uslack + 1))
    path = route(surf, p, ride | rider)

    parts = {}
    parts["deck"] = _deck(w, path, p)
    parts["rails"] = _rails(w, path, p)
    parts["piers"] = _piers(w, path, surf, p)
    parts["lamps"] = _lamps(w, path, p)
    parts["truss"] = _truss(w, path, surf, p)
    parts["west stair"] = _stairhead(w, path[0][0], path[0][1], p, -1)
    parts["east stair"] = _stairhead(w, path[-1][0], path[-1][1], p, +1)

    parts["pruned"] = _prune_strays(c)

    c.world_origin = (w.ax, anchor[1], w.az)
    us = [u for _v, u in path]
    c.meta = {
        "kind": "canopywalk",
        "lot": [dv, du],
        "at": at,
        "land": "frontier",
        "facing": "west",
        "profile_axis": "v",
        "deck_y": int(p["deck_y"]),
        "route": {"v0": path[0][0], "v1": path[-1][0],
                  "u_min": min(us), "u_max": max(us), "length": len(path)},
        "parts": parts,
        "refused": w.refused,
        "ride_cells_refused": w.ride_refused,
        "rider_clearance_refused": w.rider_refused,
        "truss_cables_declined": w.cables_declined,
        "note": ("The route is re-derived from the world on every build: the ridge under it is "
                 "36% built and hard-coded waypoints would be a snapshot of one day's rock."),
    }
    return c
