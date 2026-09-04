"""THE PARK'S GROUND DRESSING - shrubbery, flowers and accents on the ground nobody claimed.

Jack: *"lets do a empty ground cleanup, we want to look and locate all available spaces, make
plans to deal with them or intentionally leave them, we can add shrubbery, flowers, or other
accents, or new objects if appropriate."*

**MEASURED FIRST, AND THE MEASUREMENT IS ALSO THE MECHANISM.** Counted over the shipped
`out/Park Complete.litematic`, of the park's 120,000 lattice columns:

    28,474 are BARE LAWN          moss at the plane, nothing standing on it (23.7%)
     9,083 of those are DEAD      four or more blocks from anything built or planted
     1,081 are eight or more away, and the worst is THIRTEEN

The island's own recorded standard is the opposite of that - *"the plate has no dead ground:
every walkable cell is within 4 blocks of something built or planted, median 0"* - so the park
was failing a bar this project had already set for itself and measured once.

**THE DISTANCE IS THE DENSITY.** Every land-dressing pass in this repo so far has used a smooth
noise field, which spreads material evenly over ground that is not evenly empty: a two-cell verge
beside a kerb gets the same treatment as the middle of a forty-cell field. Here the density is
driven by the MEASURED OPENNESS of each column - its distance to the nearest non-lawn column -
so the pass puts its material exactly where the hole is and leaves the verges alone. It is the
one thing a cleanup pass must get right, and it falls out of the same distance transform that
found the holes in the first place.

    openness 3      a verge - a carpet, a tuft, nothing that narrows a walk
    openness 4-6    beds, low shrubs, a hedge run
    openness 7+     a real stand: ornamental trees, a boulder, a planted island

**DRIFTS, NEVER CONFETTI**, and the noise goes on the drift's RADIUS rather than on the cell.
The Lowland Thicket shipped the per-cell version once - 191 blobs of which 75% were one or two
cells - and the deck soffit shipped it a second time in the loudest block available. A patch of
planting has a solid middle and a wobbly edge or it is not a patch.

**ONE HUE PER BED.** Three tones of one colour beat two tones and a third hue - the flamingo
settled that, and a bed of one species reads as a planting where a bed of eight reads as a seed
packet emptied on the ground. A drift picks its flower FAMILY once and varies the tone inside it.

**IT KEEPS OUT OF THE FRONTIER.** `PF Frontier Scatter`, `PF Frontier Overgrowth`, `PF Frontier
Rim`, `PF Plateau Vale` and `PF Plateau Bone Bed` already dress that land, and two planting
passes on one strip is the clash no single design can see - each honestly reports `overlap 0`
against the capture, because the capture does not contain the other. The one exception is the
front threshold V0-5, which the scatter cannot reach at all: `clearing()` refuses any candidate
whose `path_clear` neighbourhood leaves the lot, so the park's outermost two columns are
unplantable BY CONSTRUCTION for a lot that stops at V0. Here the lattice IS the lot, so a
neighbour past its edge is open sky rather than a refusal.

**NOTHING GOES ON PAVING AND NOTHING NARROWS A WALK.** `Park Ways` owns every paved cell in the
park; a shrub in a street is not dressing, it is an obstruction. The mask is `moss_block` and
`moss_carpet` and nothing else, and every candidate is held off the paving by `path_clear`.
"""
from __future__ import annotations

import json
import os
from collections import deque

import numpy as np

from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .frontier_scatter import _Ground, shipped_cells
from .vertical import Ctx

#: THE GROUND THIS MAY PLANT ON, and nothing else - the same mask `frontier_scatter` uses.
LAWN = {"moss_block", "moss_carpet"}

#: Every entry is checked by `tests/test_parkgreen.py` against `blocks.available` (the 1.19
#: allowlist), `blocks.spendable` (dirt and grass are CURRENCY on this server) and
#: `palette.tier`. `pink_petals` is deliberately absent: it is a 1.20 block, and rule 12 in
#: CLAUDE.md exists because exactly that block sailed through every other check once already.
GREEN = {
    "turf": "moss_carpet",
    "grass": "short_grass",
    "fern": "fern",
    "tall": "tall_grass",
    "bush": "azalea",
    "bush_b": "flowering_azalea",
    "berry": "sweet_berry_bush",
    "trunk": "oak_log",
    "leaf": "oak_leaves",
    "hedge": "oak_leaves",
    "rock": "cobblestone",
    "rock_b": "andesite",
    "rock_c": "stone",
    "moss_rock": "mossy_cobblestone",
    "kerb": "stone_brick_slab",
    "soil": "moss_block",
    #: ONE HUE PER BED - see the module docstring. Each family is a flower and its own second
    #: tone, so a drift varies WITHIN a colour instead of across the rainbow.
    "flowers": [("poppy", "red_tulip"), ("dandelion", "orange_tulip"),
                ("cornflower", "blue_orchid"), ("oxeye_daisy", "azure_bluet"),
                ("allium", "pink_tulip"), ("lily_of_the_valley", "white_tulip")],
}

#: **A LAND'S PLANTING IS ITS OWN, AND THE PALETTE TRAVELS WITH THE GROUND PROBE.** The three
#: lands are told apart by their paving already; their greenery has to agree with it or the
#: dressing is the one thing in the park that reads the same everywhere.
PALETTES = {
    #: The fairground. Ornamental, clipped, bedded - a park in the municipal sense, because that
    #: is what a midway's verges are: oak, hedges, and beds in the land's own red.
    "midway": {"trunk": "oak_log", "leaf": "oak_leaves", "hedge": "oak_leaves",
               "kerb": "stone_brick_slab",
               "flowers": [("poppy", "red_tulip"), ("oxeye_daisy", "white_tulip"),
                           ("dandelion", "orange_tulip"), ("allium", "pink_tulip")]},
    #: The Lost Plateau. Jungle, to agree with `PF Frontier Scatter` and `gen/plateau.py` - the
    #: canopy on the ridge and the trees on the flat below it read as one wood or neither does.
    "frontier": {"trunk": "jungle_log", "leaf": "jungle_leaves", "hedge": "jungle_leaves",
                 "kerb": "stone_brick_slab",
                 "flowers": [("dandelion", "orange_tulip"), ("poppy", "red_tulip")]},
    #: Prismworks. Cold, mineral, blue-white: azalea and birch over deepslate, and the flowers
    #: are the blue end of the game's own range so they sit against cyan paving rather than
    #: fighting it.
    "prismworks": {"trunk": "birch_log", "leaf": "birch_leaves", "hedge": "azalea_leaves",
                   "kerb": "polished_deepslate_slab", "rock": "cobbled_deepslate",
                   "rock_b": "deepslate", "rock_c": "tuff", "moss_rock": "mossy_cobblestone",
                   "flowers": [("cornflower", "blue_orchid"), ("allium", "pink_tulip"),
                               ("lily_of_the_valley", "white_tulip")]},
    #: The reaches between lands, which are countryside rather than park: unclipped, wilder,
    #: mixed - the transition idiom `Park Ways` already uses for its paving, in planting.
    "reach": {"trunk": "birch_log", "leaf": "birch_leaves", "hedge": "oak_leaves",
              "kerb": "stone_brick_slab",
              "flowers": [("oxeye_daisy", "azure_bluet"), ("cornflower", "blue_orchid"),
                          ("dandelion", "white_tulip"), ("poppy", "red_tulip")]},
}

#: WHICH U RANGE IS WHICH LAND. Read off `configs/park_ways.yaml`'s own `lands` list; the gaps
#: between them are the reaches, and a reach is a land in its own right here because it is where
#: most of the park's unclaimed ground actually is.
BANDS = [(0, 169, "frontier"), (170, 214, "reach"), (215, 384, "midway"),
         (385, 429, "reach"), (430, 599, "prismworks")]

#: A cell this design itself placed is built progress, not an obstruction - rule 15. Narrow, and
#: the union across every palette, because a land that changes species still has to recognise
#: what it planted last time. `shipped_cells` is the exact answer and this is the fallback.
_OWN_KEYS = ("turf", "grass", "fern", "tall", "bush", "bush_b", "berry", "trunk", "leaf",
             "hedge", "rock", "rock_b", "rock_c", "moss_rock", "kerb")
OWN = ({GREEN[k] for k in _OWN_KEYS}
       | {v for pal in PALETTES.values() for k, v in pal.items() if k in _OWN_KEYS}
       | {f for pal in [GREEN, *PALETTES.values()]
          for pair in pal.get("flowers", []) for f in pair})

GREEN_CFG = {
    "kind": "green",
    "lot": None,                  # [dv, du] - the whole lattice
    "at": None,                   # [V, U]
    "anchor": [97500, 203, 80300],
    "under": None,                # the world this is verified against - ASK THE SAME ONE
    "previous": None,             # this design's own artifact, for rule 15
    #: [[v0, v1, u0, u1], ...] - ground somebody else already dresses.
    "keep_out": [],
    "path_clear": 2,              # how far a planting stands off anything paved
    #: **THE OPENNESS GATE, WHICH IS THE WHOLE POINT.** A column's distance to the nearest
    #: non-lawn column. Below `open_min` nothing at all is placed, so a verge stays a verge.
    "open_min": 3,
    #: ...and the density ramp. `density` is the chance at `open_full` and above; below it the
    #: chance falls off linearly to nothing at `open_min`.
    "open_full": 7,
    "density": 0.55,
    "step": 3,
    #: WHICH PIECES, and how often. Weighted by repetition, the same way `frontier_scatter`
    #: makes a stand read as woodland rather than as a sampler of four things.
    "kinds": ["meadow", "meadow", "bed", "shrub", "hedge", "tree", "rock"],
    #: Height cap in courses. The rim reserve is a VOID-VIEW reserve, so anything placed there
    #: has to stay under the sightline - see `configs/pf_park_green.yaml`.
    "max_height": 99,
    "seed": 0,
}


# --------------------------------------------------------------------------- the openness field


def openness(under: str, anchor, dv: int, du: int, at, mine=()) -> np.ndarray:
    """[V, U] - each column's distance to the nearest column that is NOT open lawn.

    **MEASURED ONCE, IN NUMPY, OFF THE SAME FILE THE DESIGN IS VERIFIED AGAINST.** The park is
    120,000 columns and every candidate would otherwise re-probe its own neighbourhood through
    `Ctx.name_at` - the cost `_Ground` already caches against, one order of magnitude larger.

    A column outside the capture reads as OPEN, not as built. The lattice is the plot, so what is
    past its edge is sky; treating it as built would make the park's own outer courses measure as
    crowded and leave the front threshold - the first ground a guest sees - permanently untouched,
    which is exactly the failure `frontier_scatter.clearing` has at a lot boundary.

    **AND THIS DESIGN'S OWN STANDING CELLS READ AS OPEN TOO** - rule 15, applied to the one place
    `_Ground.mine` cannot reach. Once the pass is shipped, `Park Complete` CONTAINS it, so the
    columns it planted last time measure as built, the openness under every drift collapses, and
    the next run plants almost nothing: `PF Frontier Scatter` shipped exactly that failure once,
    at 428 blocks against 3,843. `mine` is knowable exactly - it is this design's own litematic -
    so those columns are put back to lawn before the transform runs.
    """
    from .. import schem

    m = schem.load(under)
    side = os.path.splitext(under)[0] + ".scan.json"
    o = json.load(open(side))["origin"]
    names = np.array([n.split(":")[-1] for n in m.names])
    ax, ay, az = (int(x) for x in anchor)
    plane = ay - 1 - o["y"]                      # the ground course, one under the build plane
    sy, sz, sx = m.ids.shape
    v0, u0 = ax + int(at[0]) - o["x"], az + int(at[1]) - o["z"]
    if plane < 0 or plane >= sy:
        return np.full((dv, du), 99, np.int32)

    xs = np.arange(v0, v0 + dv)
    zs = np.arange(u0, u0 + du)
    okx = np.nonzero((xs >= 0) & (xs < sx))[0]
    okz = np.nonzero((zs >= 0) & (zs < sz))[0]
    lawn = np.ones((dv, du), bool)               # past the capture: sky, and sky is not built
    if okx.size and okz.size:
        grid = np.ix_(zs[okz], xs[okx])
        ground = np.isin(names[m.ids[plane][grid]].T, list(LAWN))
        clear = np.ones_like(ground)
        for y in range(plane + 1, min(sy, plane + 10)):
            blk = names[m.ids[y][grid]].T
            clear &= np.isin(blk, ["air", "cave_air", "void_air", "moss_carpet"])
        lawn[np.ix_(okx, okz)] = ground & clear
    for x, _y, z in mine:                        # rule 15: my own planting is not an obstacle
        a, b = x - ax - int(at[0]), z - az - int(at[1])
        if 0 <= a < dv and 0 <= b < du:
            lawn[a, b] = True

    # a multi-source BFS off every non-lawn column
    INF = 1 << 20
    dist = np.full((dv, du), INF, np.int32)
    dist[~lawn] = 0
    q = deque((int(a), int(b)) for a, b in zip(*np.nonzero(~lawn)))
    while q:
        v, u = q.popleft()
        d = dist[v, u] + 1
        for a, b in ((v + 1, u), (v - 1, u), (v, u + 1), (v, u - 1)):
            if 0 <= a < dv and 0 <= b < du and dist[a, b] > d:
                dist[a, b] = d
                q.append((a, b))
    return np.where(dist >= INF, 99, dist).astype(np.int32)


class _Green(_Ground):
    """`_Ground`, with the lattice boundary treated as open sky rather than as a refusal.

    **THE OUTERMOST TWO COURSES OF THE PARK ARE UNPLANTABLE FOR ANY LOT THAT STOPS AT THEM**, and
    that is why the front threshold V0-5 measured as the third-largest hole in the park with a
    dressing pass already nominally covering it: `clearing` refuses a candidate whose whole
    `path_clear` neighbourhood is not lawn, and past V0 there is no lawn because there is no lot.
    Here the lot IS the plot, so out of bounds means nothing is there - which is a reason to plant
    at V1, not a reason to refuse it.
    """

    def clearing(self, v, u) -> bool:
        if not self.lawn(v, u):
            return False
        c = self.clear
        for dv in range(-c, c + 1):
            for du in range(-c, c + 1):
                a, b = v + dv, u + du
                if not (0 <= a < self.dv and 0 <= b < self.du):
                    continue                     # past the plot edge: sky, not an obstruction
                if not self.lawn(a, b):
                    return False
        return True


# --------------------------------------------------------------------------- the pieces


def _meadow(lot: _Lot, g: _Green, v: int, u: int, seed: int, cap: int, room: int = 0) -> int:
    """Rough grass: tufts, ferns and moss carpet in a soft blob. The cheapest thing here and the
    one that does most of the work - it is what turns a mown-looking sheet of moss into ground."""
    n = 0
    r = 2 + int(hash01(v, u, seed + 81) * 2) + room
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            a, b = v + dv, u + du
            jit = (hash01(a, b, seed + 82) - 0.5) * 1.8
            if (dv * dv + du * du) ** 0.5 > r + jit:
                continue
            if not (g.lawn(a, b) and g.free(a, b, 0)):
                continue
            k = hash01(a, b, seed + 83)
            key = "turf" if k < 0.42 else ("grass" if k < 0.74 else "fern")
            n += 1 if lot.put(a, 0, b, g.flora[key]) else 0
    return n


def _bed(lot: _Lot, g: _Green, v: int, u: int, seed: int, cap: int, room: int = 0) -> int:
    """A flower bed. ONE HUE, two tones of it, on a soft-edged patch of turf.

    A bed of eight species is a seed packet emptied on the ground; the flamingo settled that three
    tones of one colour beat two tones and a third hue, and it holds for planting as much as for
    a coat.
    """
    fam = g.flora["flowers"]
    a_f, b_f = fam[int(hash01(v, u, seed + 84) * len(fam))]
    n = 0
    r = 2 + int(hash01(v, u, seed + 85) * 2) + room
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            a, b = v + dv, u + du
            jit = (hash01(a, b, seed + 86) - 0.5) * 1.6
            if (dv * dv + du * du) ** 0.5 > r + jit:
                continue
            if not (g.lawn(a, b) and g.free(a, b, 0)):
                continue
            k = hash01(a, b, seed + 87)
            key = a_f if k < 0.5 else (b_f if k < 0.78 else g.flora["turf"])
            n += 1 if lot.put(a, 0, b, key) else 0
    return n


def _shrub(lot: _Lot, g: _Green, v: int, u: int, seed: int, cap: int, room: int = 0) -> int:
    """A bush - azalea, flowering azalea or a berry bush. One or three cells, never a line."""
    n = 0
    k = hash01(v, u, seed + 88)
    key = "bush" if k < 0.4 else ("bush_b" if k < 0.7 else "berry")
    props = {"age": "3"} if g.flora[key] == "sweet_berry_bush" else {}
    for dv, du in ((0, 0), (1, 0), (0, 1)):
        if (dv or du) and hash01(v, u, dv, seed + 89) > 0.45:
            continue
        a, b = v + dv, u + du
        if g.lawn(a, b) and g.free(a, b, 0):
            n += 1 if lot.put(a, 0, b, g.flora[key], **props) else 0
    return n


def _hedge(lot: _Lot, g: _Green, v: int, u: int, seed: int, cap: int, room: int = 0) -> int:
    """A clipped hedge, and it is the one piece here that MUST BE A RUN.

    **A COURSE SHORTER THAN ITS MINIMUM GETS NOTHING.** The deck soffit drew a coffer grid per
    cell and shipped 215 runs of which 184 were one or two cells - confetti in the loudest block
    available - and the fix there is the fix here: measure the run first, and if it is too short
    to read as a line, place nothing at all rather than a scatter of lone dark blocks.
    """
    axis = 0 if hash01(v, u, seed + 90) < 0.5 else 1
    want = 5 + int(hash01(v, u, seed + 91) * 6) + 2 * room
    h = 1 if cap < 2 else (1 if hash01(v, u, seed + 92) < 0.45 else 2)
    run = []
    for k in range(want):
        a, b = (v + k, u) if axis == 0 else (v, u + k)
        if not (g.lawn(a, b) and all(g.free(a, b, y) for y in range(h))):
            break
        run.append((a, b))
    if len(run) < 4:                              # too short to read as a line
        return 0
    n = 0
    for a, b in run:
        for y in range(h):
            n += 1 if lot.put(a, y, b, g.flora["hedge"], persistent="true", distance="7",
                              waterlogged="false") else 0
    return n


def _tree(lot: _Lot, g: _Green, v: int, u: int, seed: int, cap: int, room: int = 0) -> int:
    """An ornamental: a bare trunk carrying a crown wider than it is tall.

    The same shape `frontier_scatter._jungle` uses, for the reason recorded there - a crown you
    can see UNDER is what makes a voxel broadleaf read, and it is also what keeps a park tree from
    walling off the view down its own avenue.
    """
    h = min(max(3, cap - 2), 4 + int(hash01(v, u, seed + 93) * 3))
    if h < 3 or cap < 5:
        return 0
    n = 0
    for y in range(h):
        n += 1 if lot.put(v, y, u, g.flora["trunk"], axis="y") else 0
    for dy, r in ((h - 1, 2), (h, 2), (h + 1, 1)):
        if dy < 1 or dy > cap - 1:
            continue
        for dv in range(-r, r + 1):
            for du in range(-r, r + 1):
                if dv * dv + du * du > r * r + r:
                    continue
                if dv == 0 and du == 0 and dy < h + 1:
                    continue
                if not (g.lawn(v + dv, u + du) and g.free(v + dv, u + du, dy)):
                    continue
                n += 1 if lot.put(v + dv, dy, u + du, g.flora["leaf"], persistent="true",
                                  distance="7", waterlogged="false") else 0
    return n


def _rock(lot: _Lot, g: _Green, v: int, u: int, seed: int, cap: int, room: int = 0) -> int:
    """A boulder in the land's own stone, so an accent reads as local rather than imported."""
    r = 1 + int(hash01(v, u, seed + 94) * 2) + (1 if room else 0)
    n = 0
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            d = (dv * dv + du * du) ** 0.5
            if d > r or not g.lawn(v + dv, u + du):
                continue
            top = min(cap, max(1, int(round(r * 1.1 * (1 - d / (r + 0.6))))))
            for y in range(top):
                if not g.free(v + dv, u + du, y):
                    continue
                k = hash01(v + dv, u + du, y, seed + 95)
                key = "moss_rock" if k < 0.22 else ("rock_b" if k < 0.46 else "rock")
                n += 1 if lot.put(v + dv, y, u + du, g.flora[key]) else 0
    return n


KINDS = {"meadow": _meadow, "bed": _bed, "shrub": _shrub,
         "hedge": _hedge, "tree": _tree, "rock": _rock}

#: WHICH PIECES ARE FLAT. Below the halfway mark of the openness ramp only these are on the
#: table: a tree wants room round it or it is a post standing in a verge.
FLAT = ("meadow", "bed", "shrub")


# --------------------------------------------------------------------------- the sweep


def land_at(u: int, at_u: int = 0) -> str:
    world_u = u + at_u
    for a, b, name in BANDS:
        if a <= world_u <= b:
            return name
    return "reach"


def flora_for(name):
    """The planting palette for a land, by name. An unknown palette RAISES rather than falling
    back - a silent fallback is how a land keeps the wrong species through a re-theme and nobody
    ever sees a thing."""
    key = str(name or "reach")
    if key not in PALETTES:
        raise ValueError(f"unknown green palette {key!r}; have {sorted(PALETTES)}")
    return {**GREEN, **PALETTES[key]}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**GREEN_CFG, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the park green needs its lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("planting must ask the world it is verified against: under: <capture>")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    at = [int(x) for x in (p.get("at") or (0, 0))]
    anchor = [int(x) for x in p["anchor"]]
    seed = int(p.get("seed", 0))
    c = Canvas(dv, 16, du, donors)
    lot = _Lot(c, dv, du, seed=seed)

    ctx = Ctx(p["under"])
    mine = shipped_cells(p.get("previous"))
    open_field = openness(p["under"], anchor, dv, du, at, mine)
    grounds = {name: _Green(ctx, anchor, dv, du, at, int(p.get("path_clear", 2)),
                            p.get("keep_out") or (), own=OWN, mine=mine,
                            flora=flora_for(name))
               for name in PALETTES}

    step = max(2, int(p.get("step", 3)))
    o_min, o_full = int(p.get("open_min", 3)), int(p.get("open_full", 7))
    dens = float(p.get("density", 0.55))
    cap = int(p.get("max_height", 99))
    kinds = list(p.get("kinds") or GREEN_CFG["kinds"])
    flat_pool = [k for k in kinds if k in FLAT] or ["meadow"]
    tally: dict = {}
    by_land: dict = {}
    placed = pieces = 0

    for v in range(0, dv, step):
        for u in range(0, du, step):
            a = v + int(hash01(v, u, seed + 71) * step)
            b = u + int(hash01(v, u, seed + 72) * step)
            if not (0 <= a < dv and 0 <= b < du):
                continue
            o = int(open_field[a, b])
            if o < o_min:
                continue
            # THE DISTANCE IS THE DENSITY: nothing at the gate, full at `open_full`.
            ramp = min(1.0, (o - o_min + 1) / max(1, o_full - o_min + 1))
            if hash01(a, b, seed + 73) > dens * ramp:
                continue
            land = land_at(b, at[1])
            g = grounds[land]
            if not g.clearing(a, b):
                continue
            pool = kinds if o >= (o_min + o_full) // 2 else flat_pool
            kind = pool[int(hash01(a, b, seed + 74) * len(pool))]
            # **THE ROOM SETS THE SIZE AS WELL AS THE ODDS.** A dozen small beds in a
            # forty-cell field read as spots on a lawn; the same material in three big
            # ones reads as planting. A drift grows one step for every three blocks of
            # openness past the ramp's own top, capped at two.
            room = min(2, max(0, (o - o_full) // 3))
            got = KINDS[kind](lot, g, a, b, seed, cap, room)
            if not got:
                continue
            placed += got
            pieces += 1
            tally[kind] = tally.get(kind, 0) + 1
            by_land[land] = by_land.get(land, 0) + got

    c.world_origin = (anchor[0] + at[0], anchor[1], anchor[2] + at[1])
    c.meta = {
        "kind": "parkgreen",
        "lot": [dv, du],
        "at": at,
        "facing": "west",
        "profile_axis": "u",
        "refused": lot.refused,
        "parts": {"pieces": pieces, "cells": placed,
                  "by_kind": tally, "by_land": by_land,
                  "open_min": o_min, "open_full": o_full},
        "contract": (
            "shrubbery, flowers and accents on the park's UNCLAIMED lawn: every cell stands on a "
            "column whose own ground course is moss and whose neighbourhood within `path_clear` "
            "is moss too, so nothing is placed on paving, against a kerb, or on anything anybody "
            "uses. The density is the measured distance from the column to the nearest built or "
            "planted thing, so a verge is left as a verge and the dead middles get the material. "
            "It never replaces a standing block."),
    }
    return c
