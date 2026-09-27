"""THE JUNGLE TAKES THE CAMP BACK - overgrowth on the Lost Plateau's own buildings.

Jack, after the re-theme: *"can we improve further"*, and then all three of what the measurement
offered.

**THE RENDER SAID IT PLAINLY: THE JUNGLE STOPS AT THE PLATEAU'S EDGE.** Measured over the shipped
land, leaves are **7.0% of the plateau and 3.0-3.5% of the town**, and the ~35,000 exposed cells of
masonry and timber in the camp carry NOTHING green at all. So the land reads as a rainforest
standing next to a grey mining town: the re-theme was done on the terrain and never on the
architecture, and no amount of further planting on the LAWN fixes that, because the grey is the
buildings.

**IT IS ENTIRELY ADDITIVE, AND THAT IS A BUILDABILITY RULE RATHER THAN A TASTEFUL ONE.** The
obvious move for overgrowth is to swap stone brick for its mossy variant - and a litematica printer
places into AIR and never replaces, so every swapped cell would be a cell nobody can ever print.
The deck floor's rule says the same thing from the other side: *a remedial design's damage is
measured in what it REPLACES*. So nothing here touches a standing block. Vines hang in the air
BESIDE a wall, moss carpets the air ABOVE a roof, ferns stand in the air over open ground, and
hanging roots hang in the air UNDER an overhang.

**AND IT KEEPS OUT OF THE WALK, WHICH IS WHY IT STARTS ABOVE HEAD HEIGHT.** A vine at a wall's foot
is exactly where a guest walks past it, and this land has needed the "a way is stated and refused"
rule four times already. Vines begin three courses above whatever surface is under them, so a
doorway, a street and a queue all stay clear by construction rather than by a list of exceptions.

Rules it runs under:

* **ANYTHING CLINGING NEEDS A FULL BLOCK** (rule 9), tested against the world as it is today - a
  vine on a slab, a stair or a fence comes away as a loose fitting, and `Ctx` is asked per cell.
* **A VINE'S DIRECTION FLAGS ARE WHICH FACE IT CLINGS TO** - `work.MULTIFACE`'s own exception, and
  the one place a direction is a DECISION rather than something the game derived.
* **THE DRIFT IS ON A COARSE LATTICE.** Per cell, this is confetti - the deck soffit shipped 215
  runs of which 184 were one or two cells, and the Lowland Thicket shipped 191 blobs of which 75%
  were a single cell. Growth comes in patches.
* **RULE 15 IS ANSWERED BY `previous:`** - this design's own shipped litematic - because every
  material it places also grows on the plateau next door, so a material test cannot tell its own
  work from `gen/plateau.py`'s.
"""
from __future__ import annotations

import numpy as np

from .. import blocks
from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .frontier_scatter import shipped_cells
from .vertical import Ctx

#: Checked against `blocks.available` (1.19), `blocks.spendable` and `palette.tier` by
#: `tests/test_overgrowth.py`, which asks the registry rather than trusting this list.
GROWTH = {
    "vine": "vine",
    "carpet": "moss_carpet",
    "fern": "fern",
    "roots": "hanging_roots",
    "lichen": "glow_lichen",
    "leaf": "azalea_leaves",
    "flower_leaf": "flowering_azalea_leaves",
}

#: **WHAT COUNTS AS A WALL.** A vine needs a FULL block to cling to, so a stair, a slab, a fence or
#: a pane is not a wall however much it looks like one - rule 9, and the belly design hung three
#: vines off a railing before it was written down. Measured off the land's own building histogram.
WALL = {"stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks", "chiseled_stone_bricks",
        "smooth_stone", "stone", "cobblestone", "mossy_cobblestone", "andesite",
        "polished_blackstone_bricks", "deepslate_bricks", "cobbled_deepslate",
        "spruce_planks", "dark_oak_planks", "jungle_planks", "spruce_log", "stripped_spruce_log",
        "jungle_log", "stripped_jungle_log", "white_wool", "red_wool", "yellow_wool",
        "orange_wool", "brown_wool", "gray_wool", "light_gray_wool", "bone_block"}

#: **A ROOF IS NOT A WALL, AND ASKING THE REGISTRY IS THE DIFFERENCE.** `WALL` is what a vine may
#: CLING to, which must be a full block (rule 9). A carpet only needs a solid TOP face, and this
#: land's roofs are stairs and slabs - so the first build put moss on 486 cells of the ~35,000 it
#: was aiming at, because it asked the wall question about a roof. `blocks.supports_top` answers
#: the roof question, which is rule 11: ask the game, not your memory.
ROOF = frozenset(WALL) | {n for n in (
    "dark_oak_stairs", "dark_oak_slab", "spruce_stairs", "spruce_slab", "jungle_stairs",
    "jungle_slab", "stone_brick_stairs", "stone_brick_slab", "cobblestone_stairs",
    "cobblestone_slab", "smooth_stone_slab", "andesite_slab", "deepslate_tile_slab",
    "polished_blackstone_brick_slab", "mossy_stone_brick_slab", "mossy_cobblestone_slab")
    if blocks.supports_top(n)}

#: A cell a growth may occupy. Nothing else is ever written over.
AIRY = {"air", "cave_air", "void_air"}

#: ...and the ground a fern may root in. **A PLANT ROOTS IN THE DIRT FAMILY AND NOWHERE ELSE** -
#: the Lowland Thicket returned 173 placement problems for treating mossy cobble as soil.
SOIL = {"moss_block", "grass_block", "dirt", "coarse_dirt", "podzol", "rooted_dirt", "mud"}

#: A cell over PAVING is somewhere a guest stands. `Park Ways` owns every paved cell in the park.
PAVED = {"stone_bricks", "smooth_stone", "cracked_stone_bricks", "mossy_stone_bricks",
         "stone", "cobblestone", "andesite", "polished_blackstone_bricks", "gravel",
         "spruce_planks", "dark_oak_planks", "stone_brick_slab", "cobblestone_slab"}

OVERGROWTH = {
    "kind": "overgrowth",
    "lot": None,                 # [dv, du]
    "at": None,                  # [V, U]
    "anchor": [97500, 203, 80300],
    "under": None,               # the world it grows on - ASK THE SAME ONE
    "previous": None,            # its own shipped artifact - rule 15, exactly
    "sy": 40,
    "keep_out": [],              # LOCAL [[v0, v1, u0, u1], ...]
    #: **THREE COURSES, AND IT IS THE WHOLE REASON THIS DOES NOT BLOCK A DOORWAY.** A vine at a
    #: wall's foot is exactly where a guest walks past it.
    "head_room": 3,
    "vines": {"density": 0.30, "drop": 6},
    "roofs": {"density": 0.22},
    "ferns": {"density": 0.20},
    "roots": {"density": 0.16},
    "seed": 0,
    "title": "THE OVERGROWTH",
}

_SIDES = (("north", 0, -1), ("south", 0, 1), ("west", -1, 0), ("east", 1, 0))
_BACK = {"north": "south", "south": "north", "west": "east", "east": "west"}


class _World:
    """The land's own blocks, read once as arrays.

    `Ctx.name_at` is a per-cell call and this lot is 200 x 170 x 40; probing it that way is over a
    million calls before a block is placed. `Ctx` already holds the model, so one numpy slice does
    it - the same reason `gen/plateau.py` reads its relief in one pass.
    """

    def __init__(self, ctx: Ctx, anchor, at, dv, du, sy, keep_out=(), mine=()):
        self.ax, self.ay, self.az = anchor
        self.at_v, self.at_u = at
        self.dv, self.du, self.sy = dv, du, sy
        self.keep_out = [tuple(int(x) for x in b) for b in (keep_out or ())]
        self.mine = frozenset(mine or ())
        ids = ctx.m.ids
        names = ctx.names
        msy, msz, msx = ids.shape
        self.name = np.full((dv, sy, du), "air", object)
        for v in range(dv):
            x = self.ax + self.at_v + v - ctx.ox
            if not (0 <= x < msx):
                continue
            for u in range(du):
                z = self.az + self.at_u + u - ctx.oz
                if not (0 <= z < msz):
                    continue
                for y in range(sy):
                    k = self.ay + y - ctx.oy
                    if 0 <= k < msy and ids[k, z, x]:
                        self.name[v, y, u] = names[ids[k, z, x]]
        # the surface a guest stands on, per column - anything at or below head height
        self.surface = np.full((dv, du), -1, int)
        for v in range(dv):
            for u in range(du):
                for y in range(min(sy, 8) - 1, -1, -1):
                    if self.name[v, y, u] != "air":
                        self.surface[v, u] = y
                        break

    def owned(self, v, u) -> bool:
        return any(a <= v <= b and c <= u <= d for a, b, c, d in self.keep_out)

    def at(self, v, y, u) -> str:
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.sy):
            return "air"
        return self.name[v, y, u]

    def free(self, v, y, u) -> bool:
        """Is this cell empty in the world, and ours to grow into?"""
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.sy):
            return False
        if self.owned(v, u):
            return False
        if self.name[v, y, u] in AIRY:
            return True
        x, z = self.ax + self.at_v + v, self.az + self.at_u + u
        return (x, self.ay + y, z) in self.mine


def _vines(lot: _Lot, w: _World, p: dict, seed: int) -> dict:
    """Curtains hanging down the walls, from ABOVE head height.

    **A VINE'S FLAGS ARE WHICH FACE IT CLINGS TO**, so the cell beside a wall carries the flag
    pointing back AT the wall - and the wall has to be a FULL block, which is rule 9 and the reason
    a stair or a fence is not in `WALL` however much it looks like one.
    """
    spec = p.get("vines") or {}
    dens = float(spec.get("density", 0.30))
    drop = int(spec.get("drop", 6))
    head = int(p.get("head_room", 3))
    n = curtains = 0
    for v in range(w.dv):
        for u in range(w.du):
            base = int(w.surface[v, u])
            for y in range(w.sy - 1, max(base + head, head) - 1, -1):
                if not w.free(v, y, u):
                    continue
                for side, dv, du in _SIDES:
                    if w.at(v + dv, y, u + du) not in WALL:
                        continue
                    # the drift is on a COARSE lattice - per cell this is confetti
                    if hash01(v // 3, u // 3, y // 4, seed + 11) > dens:
                        continue
                    run = 0
                    for k in range(drop):
                        yy = y - k
                        if yy <= base + 1 or not w.free(v, yy, u):
                            break
                        if w.at(v + dv, yy, u + du) not in WALL:
                            break
                        # **THE FLAG IS THE DIRECTION THE WALL IS IN, NOT ITS OPPOSITE.** The
                        # vine sits at (v, u) and the wall at (v+dv, u+du), so it clings to its own
                        # `side` face. `gen/plateau.py` uses `_BACK` and is right to - there the
                        # vine is placed at the NEIGHBOUR and clings back toward the rock. Copying
                        # that line into a generator whose geometry is the other way round cost
                        # 2,948 unattached vines, every one of which our renderer draws exactly
                        # like an attached one.
                        props = {s: "false" for s, _, _ in _SIDES}
                        props[side] = "true"
                        if not lot.put(v, yy, u, GROWTH["vine"], up="false", **props):
                            break
                        run += 1
                        n += 1
                    if run:
                        curtains += 1
                    break
    return {"cells": n, "curtains": curtains}


def _roofs(lot: _Lot, w: _World, p: dict, seed: int) -> dict:
    """Moss and a leaf or two creeping over the flat tops.

    A carpet needs a full block under it and open sky over it, so this finds the roof rather than
    being told where one is - and a roof is any full block with nothing on it, which is what a roof
    IS whatever design put it there.
    """
    dens = float((p.get("roofs") or {}).get("density", 0.22))
    head = int(p.get("head_room", 3))
    n = leaves = 0
    for v in range(w.dv):
        for u in range(w.du):
            base = int(w.surface[v, u])
            for y in range(max(base + head, head), w.sy - 1):
                if w.at(v, y, u) not in ROOF or not w.free(v, y + 1, u):
                    continue
                q = 0.72 * hash01(v // 3, u // 3, seed + 21) + 0.28 * hash01(v, u, seed + 22)
                if q > dens:
                    continue
                if q < dens * 0.22:
                    if lot.put(v, y + 1, u, GROWTH["leaf"], persistent="true", distance="7",
                               waterlogged="false"):
                        leaves += 1
                        n += 1
                elif lot.put(v, y + 1, u, GROWTH["carpet"]):
                    n += 1
    return {"cells": n, "leaves": leaves}


def _ferns(lot: _Lot, w: _World, p: dict, seed: int) -> dict:
    """Ferns at the foot of a wall, on open ground and never on paving.

    **A CELL OVER PAVING IS SOMEWHERE A GUEST STANDS**, and `Park Ways` owns every paved cell in
    the park - so growth at ground level goes only where the ground is soil.
    """
    dens = float((p.get("ferns") or {}).get("density", 0.20))
    n = 0
    for v in range(w.dv):
        for u in range(w.du):
            base = int(w.surface[v, u])
            if base < 0 or w.at(v, base, u) not in SOIL:
                continue
            if not w.free(v, base + 1, u):
                continue
            if not any(w.at(v + dv, base + 1, u + du) in WALL for _s, dv, du in _SIDES):
                continue
            q = 0.7 * hash01(v // 2, u // 2, seed + 31) + 0.3 * hash01(v, u, seed + 32)
            if q > dens:
                continue
            n += 1 if lot.put(v, base + 1, u, GROWTH["fern"]) else 0
    return {"cells": n}


def _roots(lot: _Lot, w: _World, p: dict, seed: int) -> dict:
    """Hanging roots under an overhang - the one growth that reads from directly underneath."""
    dens = float((p.get("roots") or {}).get("density", 0.16))
    head = int(p.get("head_room", 3))
    n = 0
    for v in range(w.dv):
        for u in range(w.du):
            base = int(w.surface[v, u])
            for y in range(max(base + head, head), w.sy - 1):
                if w.at(v, y + 1, u) not in WALL or not w.free(v, y, u):
                    continue
                if any(w.at(v + dv, y, u + du) in WALL for _s, dv, du in _SIDES):
                    continue          # under a WALL is a corner, not an overhang
                if hash01(v // 2, u // 2, y, seed + 41) > dens:
                    continue
                n += 1 if lot.put(v, y, u, GROWTH["roots"], waterlogged="false") else 0
    return {"cells": n}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**OVERGROWTH, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the overgrowth needs its measured lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("the overgrowth grows on a world: under: <capture>")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    sy = int(p.get("sy") or 40)
    seed = int(p.get("seed", 0))
    c = Canvas(dv, sy, du, donors)
    lot = _Lot(c, dv, du, seed=seed)
    anchor = [int(x) for x in p["anchor"]]
    at_v, at_u = (int(x) for x in (p.get("at") or (0, 0)))
    w = _World(Ctx(p["under"]), anchor, (at_v, at_u), dv, du, sy,
               keep_out=p.get("keep_out") or (), mine=shipped_cells(p.get("previous")))

    parts = {"vines": _vines(lot, w, p, seed),
             "roofs": _roofs(lot, w, p, seed),
             "ferns": _ferns(lot, w, p, seed),
             "roots": _roots(lot, w, p, seed)}

    c.world_origin = (anchor[0] + at_v, anchor[1], anchor[2] + at_u)
    c.meta = {
        "kind": "overgrowth",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "the jungle taking the camp back: vine curtains down the walls from above head "
            "height, moss and azalea creeping over the roofs, ferns at the foot of a wall where "
            "the ground is soil, and hanging roots under the overhangs. Every cell goes into AIR "
            "beside or above a standing block, so nothing is replaced, a printer can place all of "
            "it, and it can be undone by breaking what it placed."),
    }
    return c
