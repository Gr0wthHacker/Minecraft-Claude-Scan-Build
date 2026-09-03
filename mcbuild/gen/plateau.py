"""THE LOST PLATEAU - the jungle that turns a grey mining mountain into a land.

Jack, on the Frontier: *"I just think this theme is boring and dull and doesnt represent well -
its confusing to the end user ... lets take the same color schemes potentially so we dont change
the coaster, but I think 'frontier' needs to change."*

**MEASURED, AND ONE NUMBER IS THE WHOLE COMPLAINT.** Show material - wool, concrete, copper,
glass, lamps, carpet, anything MADE and coloured - as a share of each land:

    Midway       87,967 blocks   24.0%
    Prismworks   96,576          21.7%
    Wyrm reach   31,738          31.7%
    FRONTIER    144,620           1.3%

It is the BIGGEST land in the park and the one with the MOST things to do (349 interactive blocks
against the Midway's 335), so it was never short on effort. It is short on IDENTITY: 54% of it is
moss, stone, stone brick and cobblestone, and nothing in it tells you what land you are standing
in. **And a gold-rush mining camp cannot be fixed by adding colour, because timber and stone IS
the theme** - which is why the theme had to go rather than the execution.

**THE COASTER AND THE MOUNTAIN DO NOT MOVE.** `Mine Coaster` (56,635) and `PF Mine Ridge` (41,948)
are 98,583 blocks - **72% of the land's mass** - and a mountain with a rail ride cut through it
works under any story. A cave tunnel and a mine tunnel are the same tunnel; a timber trestle over a
gorge is a timber trestle. Not one cell of either is touched here.

**THIS IS THE LEVER, AND IT IS MEASURED TOO.** The ridge is 8,804 columns of which **5,776 stand
at Y206 or above** - the mass rather than the lawn - and its top surface is stone 14%, gravel 13%,
cobblestone 9%, andesite 4%. That is the single biggest grey object in the park, and dressing it is
the cheapest way to change what the land reads as.

What it does, in order of how much colour it buys:

    turf      a moss cap ONE COURSE OVER the rock - additive, and the soil everything else roots in
    trees     jungle and azalea canopies on the crest and the benches
    vines     curtains down the faces the ridge already has
    ferns     and lichen in the shade, so the ground under the canopy is not bare rock

**ADDITIVE, NEVER A RE-CARVE.** The deck floor's rule is that a remedial design's damage is
measured in what it REPLACES, not in what it places: 492 replacements read as vandalism and 84 read
as a repair. Every cell here goes into AIR above the ridge's own surface, so the mountain underneath
is untouched and the pass can be deleted by breaking what it placed.

Rules it runs under, each of which has cost this repo a rebuild:

* **A PLANT ROOTS IN THE DIRT FAMILY AND NOWHERE ELSE.** The Lowland Thicket returned 173 placement
  problems for listing mossy cobble and mossy stone brick as soil because they look like ground.
  Ferns here go on the moss cap this pass lays, never on the rock.
* **ANYTHING CLINGING NEEDS A FULL BLOCK, tested against the world as it is today** (rule 9), and a
  vine's direction flags are WHICH FACE IT CLINGS TO - `work.MULTIFACE`'s own exception.
* **PASSABLE IS NOT EMPTY.** A vine and a carpet both answer yes to *can light pass* and no to *may
  I build here*.
* **LEAVES ARE PERSISTENT**, or the canopy decays the moment somebody breaks a trunk.
* **RULE 15 IS ANSWERED BY `previous:`**, this design's own shipped litematic - not by a material
  list, because the Mine Ridge is built out of the same rock this pass would have to claim as its
  own. `gen/claimrow.py` records what that heuristic costs when the palette is shared.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .frontier_scatter import shipped_cells
from .vertical import Ctx

#: Every entry is checked against `blocks.available` (1.19), `blocks.spendable` (dirt and grass are
#: CURRENCY here) and `palette.tier` by `tests/test_plateau.py`, which asks the registry.
JUNGLE = {
    "turf": "moss_block",
    "carpet": "moss_carpet",
    "rock_moss": "mossy_cobblestone",
    "trunk": "jungle_log",
    "bare": "stripped_jungle_log",
    "leaf": "jungle_leaves",
    "leaf_b": "azalea_leaves",
    "leaf_c": "flowering_azalea_leaves",
    "vine": "vine",
    "fern": "fern",
    "lichen": "glow_lichen",
    "root": "hanging_roots",
}

#: THE SURFACE THIS MAY DRESS, and nothing else. A column whose top is a stair, a fence, a rail or
#: a plank belongs to the coaster or to a building, and the whole promise of this pass is that it
#: does not touch either. Measured off the ridge's own top-surface histogram.
ROCK = {"stone", "cobblestone", "andesite", "gravel", "granite", "diorite", "tuff",
        "cobbled_deepslate", "deepslate", "dripstone_block", "coal_ore", "iron_ore",
        "mossy_cobblestone", "moss_block", "stone_bricks", "cracked_stone_bricks",
        "mossy_stone_bricks", "smooth_basalt", "basalt"}

#: What a canopy may grow THROUGH. Anything else overhead means the tree would grow into somebody's
#: build - the coaster's trestles are the ones that matter, and they are 14.9% of this lot's top
#: surface, so "is the sky clear" is not a question that can be skipped.
AIRY = {"air", "cave_air", "void_air", "moss_carpet", "vine", "fern", "glow_lichen",
        "hanging_roots", "jungle_leaves", "azalea_leaves", "flowering_azalea_leaves",
        "short_grass", "grass", "tall_grass", "snow"}

PLATEAU = {
    "kind": "canopy",
    "lot": None,                  # [dv, du]
    "at": None,                   # [V, U]
    "anchor": [97500, 203, 80300],
    "under": None,                # the world this is verified against - ASK THE SAME ONE
    "previous": None,             # this design's own shipped artifact - rule 15, exactly
    "sy": 64,
    "keep_out": [],               # LOCAL [[v0, v1, u0, u1], ...]
    #: The course a column's top must reach before it counts as the MASS rather than the lawn
    #: around it. Measured: the ridge's lot runs Y202-256 and 5,776 of its 8,804 columns stand at
    #: Y206 or over.
    "base": 206,
    "turf": 0.72,                 # share of dressable columns that get a moss cap
    "trees": {"step": 5, "density": 0.5},
    "vines": {"density": 0.55, "drop": 7, "min_face": 3},
    "ferns": 0.30,
    "lichen": 0.06,
    "seed": 0,
    "title": "THE LOST PLATEAU",
}


# --------------------------------------------------------------------------- the world


class _Relief:
    """The ridge's own surface, read once off the capture as arrays rather than cell by cell.

    `Ctx.name_at` is the repo's idiom and it is a per-cell call; this lot is 8,804 columns over
    sixty courses, so probing it that way is half a million calls before a block is placed. `Ctx`
    already holds the model and a solidity mask, so the height map is one numpy pass over it.
    """

    def __init__(self, ctx: Ctx, anchor, at, dv: int, du: int, keep_out=(), mine=()):
        self.ctx = ctx
        self.ax, self.ay, self.az = anchor
        self.at_v, self.at_u = at
        self.dv, self.du = dv, du
        self.keep_out = [tuple(int(x) for x in b) for b in (keep_out or ())]
        self.mine = frozenset(mine or ())
        ids = ctx.m.ids
        names = ctx.names
        sy, sz, sx = ids.shape
        self.top = np.full((dv, du), -1, int)
        self.name = np.full((dv, du), "", object)
        for v in range(dv):
            x = self.ax + self.at_v + v - ctx.ox
            if not (0 <= x < sx):
                continue
            for u in range(du):
                z = self.az + self.at_u + u - ctx.oz
                if not (0 <= z < sz):
                    continue
                col = ids[:, z, x]
                nz = np.nonzero(col)[0]
                if not len(nz):
                    continue
                k = int(nz[-1])
                self.top[v, u] = k + ctx.oy
                self.name[v, u] = names[col[k]]

    def owned(self, v, u) -> bool:
        return any(a <= v <= b and c <= u <= d for a, b, c, d in self.keep_out)

    def world(self, v, u):
        return self.ax + self.at_v + v, self.az + self.at_u + u

    def dressable(self, v, u, base: int) -> bool:
        """Is this column the plateau's own rock, high enough to be the mass, and ours to touch?"""
        if not (0 <= v < self.dv and 0 <= u < self.du) or self.owned(v, u):
            return False
        return self.top[v, u] >= base and self.name[v, u] in ROCK

    def clear_above(self, v, u, height: int) -> bool:
        """**IS THE SKY ACTUALLY CLEAR?** The coaster's trestles are 14.9% of this lot's top
        surface, so a tree planted on a bench beside the track grows straight through it - and a
        canopy through a trestle is invisible in a plan view and obvious from the ride."""
        if not (0 <= v < self.dv and 0 <= u < self.du):
            return False
        x, z = self.world(v, u)
        y0 = self.top[v, u] + 1
        for y in range(y0, y0 + height):
            n = self.ctx.name_at(x, y, z).split(":")[-1]
            if n in AIRY or (x, y, z) in self.mine:
                continue
            return False
        return True

    def face_below(self, v, u, du_v, du_u, drop: int) -> int:
        """How many courses of solid rock this column shows to the neighbour in that direction.

        A vine curtain wants a FACE, and a face is where the ground falls away: the neighbour is
        lower, and the rock between the two heights is what the vine clings to.
        """
        a, b = v + du_v, u + du_u
        if not (0 <= a < self.dv and 0 <= b < self.du):
            return 0
        here, there = self.top[v, u], self.top[a, b]
        if there < 0:
            return 0
        return max(0, min(drop, here - there))


# --------------------------------------------------------------------------- the pieces


def _turf(lot: _Lot, r: _Relief, p: dict, seed: int) -> dict:
    """A moss cap one course over the rock.

    **THIS IS THE COLOUR, AND IT IS ALSO THE SOIL.** A plant roots in the dirt family and nowhere
    else - the Lowland Thicket returned 173 placement problems for treating mossy cobble as
    ground - so nothing else in this pass can be planted until the cap exists. It goes ABOVE the
    rock rather than replacing it, so the mountain is untouched and the pass is reversible.
    """
    share = float(p.get("turf") or 0)
    base = int(p["base"])
    n = 0
    caps = set()
    for v in range(r.dv):
        for u in range(r.du):
            if not r.dressable(v, u, base):
                continue
            # the noise is on a COARSE lattice, so the cap comes out as drifts of green with rock
            # showing through rather than as an even fur - the confetti rule, in moss.
            q = 0.7 * hash01(v // 4, u // 4, seed + 11) + 0.3 * hash01(v, u, seed + 12)
            if q > share:
                continue
            if not r.clear_above(v, u, 1):
                continue
            y = r.top[v, u] + 1 - r.ay
            if y < 0 or y >= lot.c.sy:
                continue
            if lot.put(v, y, u, JUNGLE["turf"]):
                caps.add((v, u))
                n += 1
    return {"cells": n, "caps": caps}


def _tree(lot: _Lot, r: _Relief, v: int, u: int, y: int, seed: int) -> int:
    """A jungle tree: a straight trunk and a broad flat canopy that overhangs it.

    **A JUNGLE CANOPY IS WIDE AND FLAT, NOT CONICAL.** A spruce narrows in steps and reads as a
    fir; the thing that says jungle is a crown wider than it is tall, carried clear of the ground
    on a bare trunk, so you see UNDER it. That is also what makes it read from the ride, which
    passes below the crest rather than over it.
    """
    h = 5 + int(hash01(v, u, seed + 21) * 4)
    n = 0
    for k in range(h):
        if lot.put(v, y + k, u, JUNGLE["trunk"], axis="y"):
            n += 1
    crown = [(h - 1, 3), (h, 3), (h + 1, 2)]
    for dy, rad in crown:
        for dv in range(-rad, rad + 1):
            for du in range(-rad, rad + 1):
                if dv * dv + du * du > rad * rad + rad:
                    continue
                if dv == 0 and du == 0 and dy < h + 1:
                    continue
                a, b, yy = v + dv, u + du, y + dy
                if not (0 <= a < r.dv and 0 <= b < r.du) or r.owned(a, b):
                    continue
                if r.top[a, b] >= yy + r.ay:          # inside the hill, not over it
                    continue
                key = "leaf"
                q = hash01(a, b, dy, seed + 22)
                if q < 0.14:
                    key = "leaf_b"
                elif q < 0.18:
                    key = "leaf_c"
                # PERSISTENT, or the crown decays the moment somebody breaks the trunk
                if lot.put(a, yy, b, JUNGLE[key], persistent="true", distance="7",
                           waterlogged="false"):
                    n += 1
    return n


def _trees(lot: _Lot, r: _Relief, p: dict, caps: set, seed: int) -> dict:
    """The canopy, swept over the cap rather than planted at hand-picked stands.

    The scatter's own measurement applies here: the open ground on this island is verges and
    gaps, and a list of stand centres finds almost nothing. A sweep plants wherever the relief
    itself allows.
    """
    spec = p.get("trees") or {}
    step = max(2, int(spec.get("step", 5)))
    dens = float(spec.get("density", 0.5))
    trees = cells = 0
    for v in range(1, r.dv - 1, step):
        for u in range(1, r.du - 1, step):
            a = v + int(hash01(v, u, seed + 31) * step)
            b = u + int(hash01(v, u, seed + 32) * step)
            if (a, b) not in caps:
                continue
            if hash01(a, b, seed + 33) > dens:
                continue
            if not r.clear_above(a, b, 11):
                continue
            y = r.top[a, b] + 2 - r.ay        # on TOP of the moss cap
            if y < 0 or y + 11 >= lot.c.sy:
                continue
            got = _tree(lot, r, a, b, y, seed)
            if got:
                trees += 1
                cells += got
    return {"trees": trees, "cells": cells}


#: A vine's flags are WHICH FACE IT CLINGS TO, so a vine hanging on the face a neighbour to the
#: NORTH exposes is attached on its own north side. `work.MULTIFACE` records this as the one
#: exception where a direction flag is a DECISION rather than something the game derived.
_SIDES = (("north", 0, -1), ("south", 0, 1), ("west", -1, 0), ("east", 1, 0))


def _vines(lot: _Lot, r: _Relief, p: dict, seed: int) -> dict:
    """Vine curtains down the faces the ridge already has.

    **A FACE IS WHERE THE GROUND FALLS AWAY**, so it is found rather than drawn: a column whose
    neighbour is several courses lower shows that many courses of rock, and the curtain hangs on
    it. Drawn as a rule about position instead, a curtain lands on flat ground and reads as green
    string in mid-air.
    """
    spec = p.get("vines") or {}
    dens = float(spec.get("density", 0.55))
    drop = int(spec.get("drop", 7))
    min_face = int(spec.get("min_face", 3))
    base = int(p["base"])
    n = curtains = 0
    for v in range(r.dv):
        for u in range(r.du):
            if not r.dressable(v, u, base):
                continue
            for side, dv, du in _SIDES:
                fall = r.face_below(v, u, dv, du, drop)
                if fall < min_face:
                    continue
                if hash01(v, u, hash(side) & 0xFFFF, seed + 41) > dens:
                    continue
                a, b = v + dv, u + du
                if r.owned(a, b):
                    continue
                # ...and it hangs from the top of the face DOWNWARD, each cell clinging to the
                # rock still beside it. The wall is what supports it, so the run stops where the
                # wall does rather than at a chosen length.
                run = 0
                back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
                for k in range(fall):
                    y = r.top[v, u] - k - r.ay
                    if y < 0 or y >= lot.c.sy:
                        break
                    props = {s: "false" for s, _, _ in _SIDES}
                    props[back] = "true"
                    if not lot.put(a, y, b, JUNGLE["vine"], up="false", **props):
                        break
                    run += 1
                    n += 1
                if run:
                    curtains += 1
    return {"cells": n, "curtains": curtains}


def _undergrowth(lot: _Lot, r: _Relief, p: dict, caps: set, seed: int) -> dict:
    """Ferns on the cap and lichen on the shaded rock - so the ground under the canopy is not bare.

    A fern roots in the DIRT FAMILY, which here is the moss cap this pass laid; on the rock it is
    a placement problem, and 173 of them is what the Lowland Thicket shipped by treating mossy
    cobble as soil.
    """
    fern_share = float(p.get("ferns") or 0)
    lichen_share = float(p.get("lichen") or 0)
    ferns = lichen = 0
    for (v, u) in sorted(caps):
        y = r.top[v, u] + 2 - r.ay
        if y < 0 or y >= lot.c.sy or lot.has(v, y, u):
            continue
        # **CHECK THE SOIL, DO NOT ASSUME IT.** The cap is at top+1 and the fern at top+2, so the
        # soil looks guaranteed - until a neighbouring tree whose ground is one course lower drops
        # a canopy leaf into that very cell and the cap is overwritten. Six ferns shipped standing
        # on `jungle_leaves`, which is a placement problem in context and invisible in isolation.
        if lot.name_at(v, y - 1, u) != JUNGLE["turf"]:
            continue
        q = hash01(v, u, seed + 51)
        if q < fern_share:
            ferns += 1 if lot.put(v, y, u, JUNGLE["fern"]) else 0
        elif q < fern_share + 0.10:
            ferns += 1 if lot.put(v, y, u, JUNGLE["carpet"]) else 0
    base = int(p["base"])
    for v in range(r.dv):
        for u in range(r.du):
            if not r.dressable(v, u, base) or (v, u) in caps:
                continue
            if hash01(v, u, seed + 52) > lichen_share:
                continue
            y = r.top[v, u] + 1 - r.ay
            if y < 0 or y >= lot.c.sy or lot.has(v, y, u):
                continue
            # a lichen clings DOWNWARD onto the rock it sits over
            if lot.put(v, y, u, JUNGLE["lichen"], down="true", up="false", north="false",
                       south="false", east="false", west="false", waterlogged="false"):
                lichen += 1
    return {"ferns": ferns, "lichen": lichen}


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PLATEAU, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the plateau needs its measured lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("the plateau reads the world it dresses: under: <capture>")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    seed = int(p.get("seed", 0))
    c = Canvas(dv, int(p.get("sy") or 64), du, donors)
    lot = _Lot(c, dv, du, seed=seed)
    anchor = [int(v) for v in p["anchor"]]
    at_v, at_u = (int(v) for v in (p.get("at") or (0, 0)))
    ctx = Ctx(p["under"])
    r = _Relief(ctx, anchor, (at_v, at_u), dv, du,
                keep_out=p.get("keep_out") or (), mine=shipped_cells(p.get("previous")))

    # ORDER: the cap first, because it is the soil everything else roots in; then the trees, which
    # need the clearance test run before anything of this design is standing; then the vines on the
    # faces the cap does not reach; then the undergrowth in whatever the canopy left.
    parts = {}
    turf = _turf(lot, r, p, seed)
    caps = turf.pop("caps")
    parts["turf"] = turf
    parts["trees"] = _trees(lot, r, p, caps, seed)
    parts["vines"] = _vines(lot, r, p, seed)
    parts["undergrowth"] = _undergrowth(lot, r, p, caps, seed)

    c.world_origin = (anchor[0] + at_v, anchor[1], anchor[2] + at_u)
    c.meta = {
        "kind": "lost_plateau",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "signs": lot.signs,
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "the jungle that turns the Mine Ridge from the biggest grey object in the park into "
            "the Lost Plateau: a moss cap one course over the rock, jungle and azalea canopies on "
            "the crest, vine curtains down the faces the ridge already has, and ferns and lichen "
            "under them. Every cell goes into AIR above the ridge's own surface, so the mountain "
            "and the coaster are untouched and the pass is reversible by breaking what it placed."),
    }
    return c
