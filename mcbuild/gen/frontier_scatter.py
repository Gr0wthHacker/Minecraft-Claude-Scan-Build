"""THE FRONTIER'S PLANTING AND PROPS - the land dressing, and not one building in it.

Jack: *"i dont want a bunch of buildings to go into, this is just a village then"* ... *"find other
small things to add in the area either design or otherwise that complete it."*

**MEASURED FIRST, AND THE NUMBER IS THE WHOLE ARGUMENT.** Counted over the shipped
`out/Park Complete.litematic`, the Frontier's entire flora is:

    moss_block 29,488 . moss_carpet 731 . mossy_cobblestone 439 . mossy_stone_bricks 2,356

and **not one leaf**. Zero trees, zero bushes, zero grass, in a land that is 66% bare lawn. That
is why 22,000 columns of it read as a green carpet with things standing on it: nothing GROWS
there. A gold-rush frontier is pines and dead snags and rock, and the land had none of the three.

What this places, and why each one is not a building:

    pines      spruce, in DRIFTS, on the open lawn - the thing the land is missing
    snags      dead standing trunks, barkless, a couple of stubs - a worked-out hillside
    boulders   rock lumps in the land's own quarried palette, so the mountain reads as local
    debris     what a mine leaves lying about: timber stacks, an ore pile, a barrel, a cart axle

**DRIFTS, NEVER CONFETTI.** The Lowland Thicket shipped the confetti version once - 191 blobs of
which 75% were one or two cells - and the fix is the same here: the randomness goes on the DRIFT'S
RADIUS, never on the cell, so a stand of pines has a solid middle and a wobbly edge.

**IT READS THE WORLD IT IS VERIFIED AGAINST**, through `vertical.Ctx`, which is the same rule the
shop islet learned by planting grass on somebody's cobblestone: one design, two worlds, two
answers. A cell is planted only where the world's own ground course is LAWN, the courses above it
are clear to the canopy's full height, and nothing anybody uses stands within the clearance.

**NOTHING IS PLACED ON PAVING, AND NOTHING NARROWS A WALK.** `Park Ways` owns every paved cell in
the park; a tree in a street is not dressing, it is an obstruction. The mask is `moss_block` and
`moss_carpet` and nothing else, and every candidate is additionally held clear of the paving by
`path_clear` - because a pine one cell off a kerb still crowds the guest walking past it.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .vertical import Ctx

#: Every entry checked by `tests/test_frontier_scatter.py` against `blocks.available` (1.19),
#: `blocks.spendable` (dirt and grass are CURRENCY here) and `palette.tier`.
FLORA = {
    "trunk": "spruce_log",
    "bark": "stripped_spruce_log",       # a dead snag, barkless
    "leaf": "spruce_leaves",
    "rock": "cobblestone",
    "rock_b": "andesite",
    "rock_c": "stone",
    "moss_rock": "mossy_cobblestone",
    "scree": "gravel",
    "ore": "coal_ore",
    "plank": "spruce_planks",
    "slab": "spruce_slab",
    "fence": "spruce_fence",
    "barrel": "barrel",
    "rail": "rail",
    "turf": "moss_carpet",
}

#: THE GROUND THIS MAY PLANT ON, and nothing else. Anything paved belongs to `Park Ways`.
LAWN = {"moss_block", "moss_carpet"}

#: **A CELL THIS DESIGN ITSELF PLACED IS BUILT PROGRESS, NOT AN OBSTRUCTION** - rule 15, and the
#: third time in one session that reading a composite as "the world before the design" has bitten
#: this work. The scatter reads `Park Complete`, and once it is placed the composite CONTAINS it:
#: measured, the second run refused almost every candidate it had already planted and came out at
#: **428 blocks against 3,843**. The ground course still has to be lawn, so this cannot let it
#: plant on the diggings' trail or on a bank - only back onto its own standing trees and rocks.
#: ...and it is NARROW: only what this design actually places. `spruce_planks` and the like are
#: in `FLORA` but unused here, and leaving them in let a canopy spread over a NEIGHBOUR built from
#: the same timber - measured, 33 cells of leaf reaching into the Diggings, Mining Square and the
#: Assay Office.
OWN = {FLORA[k] for k in ("trunk", "bark", "leaf", "rock", "rock_b", "rock_c",
                          "moss_rock", "scree", "ore", "barrel", "rail", "turf")}

def shipped_cells(path) -> frozenset:
    """The world cells a design SHIPPED last time, off its own artifact and sidecar.

    **THIS IS THE HONEST ANSWER TO RULE 15, AND `own` IS NOT.** A cell this design placed is built
    progress rather than an obstruction - but in a land where every module is stone brick,
    blackstone and spruce, **a material test cannot tell a neighbour's plinth from this design's
    own.** Measured: the claim row put a board post and a pine straight through the Prospecting
    Porch's marquee because the marquee's plinth is `polished_blackstone_bricks` and so is the
    claim row's, and the muster yard grew 39 cells of canopy into the Trailhead Gate for the same
    reason. `own` was the mechanism that let both happen, and widening or narrowing it only ever
    trades one of those failures for the other.

    A design's own previous cells are knowable EXACTLY: they are in its own litematic. So this
    reads them, in world coordinates, and the ground probe treats those and nothing else as its
    own. Absent (a first run, or a design never shipped) is an empty set, which is the correct
    answer - there is nothing of ours standing yet.
    """
    import json
    import os

    from .. import schem

    if not path or not os.path.exists(path):
        return frozenset()
    side = os.path.splitext(path)[0] + ".scan.json"
    if not os.path.exists(side):
        return frozenset()
    o = json.load(open(side))["origin"]
    m = schem.load(path)
    ids = m.ids
    out = set()
    sy, sz, sx = ids.shape
    nz = ids.nonzero()
    for y, z, x in zip(*nz):
        out.add((int(x) + o["x"], int(y) + o["y"], int(z) + o["z"]))
    return frozenset(out)


SCATTER = {
    "kind": "scatter",
    "lot": None,                 # [dv, du]
    "at": None,                  # [V, U]
    "anchor": [97500, 203, 80300],
    "under": None,               # the world this is verified against - ASK THE SAME ONE
    "drifts": [],                # [[v, u, radius, kind], ...] - kind: pine | snag | rock | debris
    # **THE LAWN IS NOT IN PATCHES, SO THE PLANTING CANNOT BE EITHER.** Measured over the shipped
    # park: 11,562 open lawn columns, of which only 1,542 survive a three-cell erosion - the open
    # ground is verges and gaps between buildings, and the largest free rectangle in the whole
    # land is 8 x 18. A hand-picked list of stand centres found exactly ONE site. So the planting
    # SWEEPS instead: it walks the land on a coarse lattice and plants wherever the ground itself
    # allows, which is the only method that survives the shape this land actually has.
    "sweep": None,               # {step, density, kinds: [...]}
    # **AND IT KEEPS OUT OF EVERY MODULE'S LOT.** `OWN` has to exist or the second run refuses
    # every cell the first one planted - but the Diggings and the Mine Ridge are built from the
    # same rock and the same timber, so a material test cannot tell my own standing pine from
    # theirs. Measured: 33 cells of leaf and boulder inside neighbours, then 18 after the canopy
    # went per-cell. The two requirements are both real and they need two different mechanisms -
    # `OWN` for re-planting my own ground, and a lot list for everybody else's. Land dressing goes
    # on the ground BETWEEN modules.
    "keep_out": [],              # [[v0, v1, u0, u1], ...] - other modules' lots
    "path_clear": 2,             # how far a planting stands off anything paved
    "seed": 0,
}


# --------------------------------------------------------------------------- the ground


class _Ground:
    """What the world says about a column, cached - and the only test that decides planting.

    A GENERATOR THAT ASKS THE WORLD MUST ASK IT ONCE PER CELL, not once per candidate: the
    Frontier is 34,000 columns and every drift re-probes its own neighbourhood.
    """

    def __init__(self, ctx: Ctx, anchor, dv, du, at, clear: int, keep_out=(), own=None,
                 mine=None):
        self.ctx, self.dv, self.du = ctx, dv, du
        self.ax, self.ay, self.az = anchor
        self.at_v, self.at_u = at
        self.clear = clear
        self.keep_out = [tuple(int(x) for x in b) for b in (keep_out or ())]
        #: **WHOSE STANDING BLOCKS COUNT AS THIS DESIGN'S OWN.** Rule 15 - a cell this design
        #: itself placed is built progress, not an obstruction - and the set is different for
        #: every design, because it is exactly what that design PLACES. Defaulting it to this
        #: module's `OWN` would hand a borrower the scatter's answer to its own question, which
        #: is the drift `proportions.measure` and `rubric.score` share an entry point to avoid.
        self.own = frozenset(OWN if own is None else own)
        #: The world cells this design itself shipped last time - see `shipped_cells`. This is the
        #: exact answer to rule 15; `own` is the heuristic one, and where both are given this wins
        #: on the cells it names and `own` covers the rest.
        self.mine = frozenset(mine or ())
        self._lawn: dict = {}

    def owned(self, v, u) -> bool:
        """Is this column inside somebody else's lot?"""
        return any(a <= v <= b and c <= u <= d for a, b, c, d in self.keep_out)

    def world(self, v, u):
        return self.ax + self.at_v + v, self.az + self.at_u + u

    def lawn(self, v, u) -> bool:
        """Is this column open lawn, with nothing standing on it?"""
        key = (v, u)
        if key in self._lawn:
            return self._lawn[key]
        if self.owned(v, u):
            self._lawn[key] = False
            return False
        x, z = self.world(v, u)
        # the ground course is one UNDER the plane a build stands on - `Park Ways` paves at 202
        ok = self.ctx.name_at(x, self.ay - 1, z).split(":")[-1] in LAWN
        if ok:
            for y in range(self.ay, self.ay + 9):
                n = self.ctx.name_at(x, y, z).split(":")[-1]
                if n in ("air", "cave_air", "void_air", "moss_carpet") or n in self.own:
                    continue
                if (x, y, z) in self.mine:
                    continue
                ok = False
                break
        self._lawn[key] = ok
        return ok

    def free(self, v, u, y) -> bool:
        """Is this exact CELL free in the world?

        **A COLUMN TEST IS NOT A CELL TEST, AND A CANOPY IS CELLS.** `lawn` asks about a whole
        column, which is right for deciding where a trunk may stand and wrong for deciding where a
        leaf may go: a pine on open ground two cells from a neighbour spread its canopy straight
        over that neighbour's roof, and thirty-three cells of leaf ended up inside the Diggings,
        Mining Square and the Assay Office. Every spreading part asks this instead.
        """
        if not (0 <= v < self.dv and 0 <= u < self.du) or self.owned(v, u):
            return False
        x, z = self.world(v, u)
        n = self.ctx.name_at(x, self.ay + y, z).split(":")[-1]
        if n in ("air", "cave_air", "void_air", "moss_carpet") or n in self.own:
            return True
        return (x, self.ay + y, z) in self.mine

    def clearing(self, v, u) -> bool:
        """...and is it far enough from anything paved or built to plant on?

        A PINE ONE CELL OFF A KERB STILL CROWDS THE WALK. The lawn test alone puts a trunk right
        against every street in the park, which is not dressing - it is a chicane.
        """
        if not self.lawn(v, u):
            return False
        c = self.clear
        for dv in range(-c, c + 1):
            for du in range(-c, c + 1):
                a, b = v + dv, u + du
                if not (0 <= a < self.dv and 0 <= b < self.du):
                    return False
                if not self.lawn(a, b):
                    return False
        return True


# --------------------------------------------------------------------------- the pieces


def _pine(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """A spruce: a straight trunk and a conical canopy that narrows in steps.

    **A CONE IN STEPS, NOT A SMOOTH TAPER.** At this size a smooth cone is a blob three cells
    across; what makes a voxel conifer read is the SKIRT - a wide bottom whorl, a gap, a narrower
    one - which is the same reason the ladybird's spots need a clear cell between them.
    """
    h = 5 + int(hash01(v, u, seed + 3) * 4)
    n = 0
    for y in range(0, h):
        n += 1 if lot.put(v, y, u, FLORA["trunk"], axis="y") else 0
    tiers = [(h - 5, 2), (h - 4, 2), (h - 3, 1), (h - 2, 1), (h - 1, 1), (h, 0)]
    for y, r in tiers:
        if y < 1:
            continue
        for dv in range(-r, r + 1):
            for du in range(-r, r + 1):
                if dv * dv + du * du > r * r + r:
                    continue
                if dv == 0 and du == 0 and y < h:
                    continue
                if (dv or du) and not (g.lawn(v + dv, u + du) and g.free(v + dv, u + du, y)):
                    continue
                # PERSISTENT, or the canopy decays the moment somebody breaks the trunk. Every
                # leaf this repo has ever placed is persistent and this is why.
                n += 1 if lot.put(v + dv, y, u + du, FLORA["leaf"],
                                  persistent="true", distance="7",
                                  waterlogged="false") else 0
    return n


def _snag(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """A dead standing trunk. Barkless, broken off, with a stub or two - what a worked-out
    hillside is covered in, and the cheapest thing here that says the land has a history."""
    h = 3 + int(hash01(v, u, seed + 11) * 4)
    n = 0
    for y in range(0, h):
        n += 1 if lot.put(v, y, u, FLORA["bark"], axis="y") else 0
    for s, (dv, du) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
        if hash01(v, u, s, seed + 12) > 0.35:
            continue
        y = max(1, h - 1 - s % 2)
        if g.lawn(v + dv, u + du) and g.free(v + dv, u + du, y):
            n += 1 if lot.put(v + dv, y, u + du, FLORA["bark"],
                              axis="x" if dv else "z") else 0
    return n


def _boulder(lot: _Lot, g: _Ground, v: int, u: int, r: int, seed: int) -> int:
    n = 0
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            d = (dv * dv + du * du) ** 0.5
            if d > r or not g.lawn(v + dv, u + du):
                continue
            top = max(1, int(round(r * 1.1 * (1 - d / (r + 0.6)))))
            for y in range(0, top):
                if not g.free(v + dv, u + du, y):
                    continue
                k = hash01(v + dv, u + du, y, seed + 21)
                key = "moss_rock" if k < 0.18 else ("rock_b" if k < 0.42 else "rock")
                n += 1 if lot.put(v + dv, y, u + du, FLORA[key]) else 0
    return n


def _debris(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """What a mine leaves lying about. A PROP WITH A JOB - timber cut and stacked, ore tipped out,
    a barrel - never a heap of vague blocks, which the void tower had rejected on sight."""
    n = 0
    pick = hash01(v, u, seed + 31)
    if pick < 0.34:
        # A CROSS-PILE, AND EVERY COURSE SITS ON THE ONE UNDER IT. Written as three rows at
        # k//2 heights the top row landed on columns the bottom rows never touched, and eighteen
        # cells shipped as six free-floating clusters - a stack of timber floating over the lawn.
        for j in range(-1, 2):                               # course 0: along U
            if g.lawn(v + j, u):
                n += 1 if lot.put(v + j, 0, u, FLORA["trunk"], axis="x") else 0
        for j in range(-1, 2):                               # course 1: along V, crossing it
            if g.lawn(v, u + j) and lot.has(v, 0, u + j) or j == 0:
                n += 1 if lot.put(v, 1, u + j, FLORA["trunk"], axis="z") else 0
        n += 1 if lot.put(v, 2, u, FLORA["trunk"], axis="x") else 0
    elif pick < 0.68:                                        # an ore pile, tipped and spreading
        for dv in range(-2, 3):
            for du in range(-2, 3):
                if abs(dv) + abs(du) > 2 or not g.lawn(v + dv, u + du):
                    continue
                key = "ore" if hash01(v + dv, u + du, seed + 32) < 0.35 else "scree"
                n += 1 if lot.put(v + dv, 0, u + du, FLORA[key]) else 0
    else:                                                    # a cart axle and a barrel
        for k in range(3):
            if g.lawn(v + k, u):
                n += 1 if lot.put(v + k, 0, u, FLORA["rail"], shape="east_west",
                                  waterlogged="false") else 0
        if g.lawn(v + 1, u + 1):
            n += 1 if lot.put(v + 1, 0, u + 1, FLORA["barrel"],
                              facing="up", open="false") else 0
    return n


# --------------------------------------------------------------------------- the drifts


KINDS = {"pine": _pine, "snag": _snag}


def _drift(lot: _Lot, g: _Ground, spec, seed: int) -> dict:
    """One stand. **THE NOISE IS ON THE RADIUS, NOT ON THE CELL** - thresholded per cell this is
    confetti, which is exactly what the Lowland Thicket shipped and had to rebuild."""
    v0, u0, r, kind = int(spec[0]), int(spec[1]), int(spec[2]), str(spec[3])
    placed = trees = 0
    step = 3 if kind == "pine" else 4
    for v in range(v0 - r, v0 + r + 1, step):
        for u in range(u0 - r, u0 + r + 1, step):
            jitter = (hash01(v, u, seed + 51) - 0.5) * 2.2
            d = ((v - v0) ** 2 + (u - u0) ** 2) ** 0.5
            if d > r + jitter:
                continue
            a = v + int(hash01(v, u, seed + 52) * 2)
            b = u + int(hash01(v, u, seed + 53) * 2)
            if not g.clearing(a, b):
                continue
            if kind == "rock":
                placed += _boulder(lot, g, a, b, 1 + int(hash01(a, b, seed + 54) * 2), seed)
            elif kind == "debris":
                placed += _debris(lot, g, a, b, seed)
            else:
                placed += KINDS[kind](lot, g, a, b, seed)
            trees += 1
    return {"kind": kind, "at": [v0, u0], "r": r, "n": trees, "cells": placed}


def _sweep(lot: _Lot, g: _Ground, spec: dict, dv: int, du: int, seed: int) -> dict:
    """Walk the whole land and plant wherever the ground allows.

    **THE DENSITY IS A SMOOTH FIELD, NOT A PER-CELL COIN FLIP.** Flipped per candidate this is
    evenly-spread confetti - the thing that reads as a texture rather than as woodland. A coarse
    noise field gives thickets and clearings, which is what a hillside looks like, and it is the
    Thicket's own rule (the randomness belongs on the drift, never on the cell) expressed as a
    sweep rather than as a list of centres.
    """
    step = max(2, int(spec.get("step", 5)))
    dens = float(spec.get("density", 0.35))
    kinds = list(spec.get("kinds") or ["pine", "pine", "snag", "rock", "debris"])
    placed = n = 0
    tally: dict = {}
    for v in range(2, dv - 2, step):
        for u in range(2, du - 2, step):
            # the field: a 17-cell lattice, so stands are tens of blocks across
            field = (hash01(v // 17, u // 17, seed + 61) * 0.7
                     + hash01(v // 7, u // 7, seed + 62) * 0.3)
            if hash01(v, u, seed + 63) > dens * (0.35 + 1.3 * field):
                continue
            a = v + int(hash01(v, u, seed + 64) * step)
            b = u + int(hash01(v, u, seed + 65) * step)
            if not g.clearing(a, b):
                continue
            kind = kinds[int(hash01(a, b, seed + 66) * len(kinds))]
            if kind == "rock":
                got = _boulder(lot, g, a, b, 1 + int(hash01(a, b, seed + 67) * 2), seed)
            elif kind == "debris":
                got = _debris(lot, g, a, b, seed)
            else:
                got = KINDS[kind](lot, g, a, b, seed)
            placed += got
            n += 1
            tally[kind] = tally.get(kind, 0) + 1
    return {"kind": "sweep", "n": n, "cells": placed, "by_kind": tally}


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**SCATTER, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the frontier scatter needs its lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("planting must ask the world it is verified against: under: <capture>")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    c = Canvas(dv, 16, du, donors)
    lot = _Lot(c, dv, du, seed=int(p.get("seed", 0)))
    at = [int(x) for x in (p.get("at") or (0, 0))]
    g = _Ground(Ctx(p["under"]), [int(x) for x in p["anchor"]], dv, du, at,
                int(p.get("path_clear", 2)), p.get("keep_out") or ())

    seed = int(p.get("seed", 0))
    drifts = [_drift(lot, g, d, seed) for d in (p.get("drifts") or [])]
    if p.get("sweep"):
        drifts.append(_sweep(lot, g, p["sweep"], dv, du, seed))

    av, ay, au = (int(v) for v in p["anchor"])
    c.world_origin = (av + at[0], ay, au + at[1])
    c.meta = {
        "kind": "frontier_scatter",
        "lot": [dv, du],
        "at": at,
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "refused": lot.refused,
        "parts": {"drifts": drifts,
                  "pieces": sum(d["n"] for d in drifts),
                  "by_kind": {k: sum(d.get("by_kind", {}).get(k, 0)
                                     + (d["n"] if d["kind"] == k else 0) for d in drifts)
                              for k in ("pine", "snag", "rock", "debris")},
                  "cells": sum(d["cells"] for d in drifts)},
        "contract": (
            "planting and props on the Frontier's open lawn and nowhere else: every cell stands "
            "on a column whose own ground is moss and whose neighbourhood within `path_clear` is "
            "moss too, so nothing is placed on paving, against a kerb, or on anything anybody "
            "built - and every stand is a drift with a noisy edge rather than scattered cells"),
    }
    return c
