"""Belly: an eroded, hollow rock mass fitted UNDER a real capture (chunkscan `/cscan`).

    under:        capture .litematic used for geometry (its .scan.json gives the world origin)
    world:        optional newer capture = current state; already-built cells are dropped (remaining work)
    encase_below: world Y of the plate underside; blocks up to hug_max_above above it are "plate", higher = surface builds
    hug:          rock hangs from the lowest built block per column after a side_gap min-filter, so it never rises
                  beside anything hanging lower; depth by distance to the footprint edge (depth_min rim -> depth_max)
    sub_plate:    none | skin | full — what happens under things hanging below the plate (skin_boxes limits skin)
    cut_boxes / min_plate_width: bridges and necks left bare

Output contains ONLY the belly (+ vines/lanterns): paste at the origin in <name>.scan.json.
"""
from __future__ import annotations

import json
import os

import numpy as np

from .. import audit as audit_mod
from .vertical import resolve_capture
from .canvas import Canvas, hash01
from .. import morph, schem

DEFAULTS = {
    "under": None,                 # capture used for GEOMETRY (the pre-build scan once building has started)
    "world": None,                 # optional newer capture = current state: already-built cells are removed (remaining work only)
    "side_gap": 2,                 # hug: rock never rises within this many columns of anything hanging lower
    "top_gap": 0,                  # hug: air rows between the built bottom and the rock
    "hug_max_above": 12,           # hug: built blocks higher than encase_below + this are surface builds (ignored)
    "overhang": 0,                 # hug: rock footprint extends this many columns past the built footprint (rim lip)
    "sub_plate": "none",           # hug: rock under things hanging below the plate? none | skin (thin, only in skin_boxes if given) | full
    "skin_depth": 1,
    "skin_boxes": [],              # hug: world [x1,z1,x2,z2] boxes where sub-plate structures get a skin (empty = everywhere if sub_plate=skin)
    "min_plate_width": 5,          # hug: plate parts thinner than this (necks, bridges) get no rock
    "cut_boxes": [],               # hug: world [x1,z1,x2,z2] boxes with no rock at all
    "strip": ["vine", "water", "bubble_column", "lava", "kelp", "kelp_plant", "seagrass"],
    "encase_below": None,          # world Y (auto: 2 below the densest layer)
    "depth_max": 20, "depth_min": 2, "ramp": 12,
    "wall": 2, "min_fragment": 16,
    "exclude_boxes": [],           # world [x1,y1,z1,x2,y2,z2] boxes: existing blocks there are ignored (re-hang decor after)
    "moss_bottom": 0.30, "vine_rate": 0.10, "vine_len": [4, 10],
    "lanterns_out": 14,
    "seed": 0,
}
AIRLIKE = {"air", "cave_air", "void_air"}
# never hang rock from these (canopy / plants / hangers); hangers also get a 1-block dimple
SOFT_SUFFIXES = ("_leaves", "_carpet", "_tulip", "_sapling", "_flower", "_petals")
SOFT_NAMES = {"azalea", "flowering_azalea", "short_grass", "tall_grass", "fern", "large_fern", "moss_carpet",
              "dandelion", "poppy", "lily_of_the_valley", "spore_blossom", "hanging_roots", "glow_lichen"}
HANGER_NAMES = {"lantern", "soul_lantern", "chain", "bell", "end_rod", "lightning_rod"}


def _mask_by_name(m: schem.Model, pred) -> np.ndarray:
    names = np.array([n.split(":")[-1] for n in m.names])
    return np.array([bool(pred(n)) for n in names])[m.ids]


def _is_soft(n: str) -> bool:
    return n in SOFT_NAMES or n.endswith(SOFT_SUFFIXES)


def _is_hanger(n: str) -> bool:
    return n in HANGER_NAMES or n.endswith("_chain")


# ---------------------------------------------------------------- mask helpers

def _shift(a: np.ndarray, d: tuple[int, ...], fill=False) -> np.ndarray:
    """a shifted by d (per axis); vacated cells = fill."""
    out = np.full_like(a, fill)
    src = [slice(max(0, -k), a.shape[i] - max(0, k)) for i, k in enumerate(d)]
    dst = [slice(max(0, k), a.shape[i] - max(0, -k)) for i, k in enumerate(d)]
    out[tuple(dst)] = a[tuple(src)]
    return out


def dilate(mask: np.ndarray, r: int) -> np.ndarray:
    """Chebyshev dilation by r in every axis (works for 2-D and 3-D masks)."""
    out = mask.copy()
    rng = range(-r, r + 1)
    for d in np.ndindex(*([len(rng)] * mask.ndim)):
        off = tuple(rng[k] for k in d)
        if any(off):
            out |= _shift(mask, off)
    return out


def edge_distance(footprint: np.ndarray, cap: int) -> np.ndarray:
    """Chebyshev distance to the nearest non-footprint cell (box border counts), capped."""
    dist = np.zeros(footprint.shape, int)
    cur = footprint.copy()
    for i in range(cap):
        eroded = cur & ~dilate(~cur, 1)
        dist[cur & ~eroded] = i
        cur = eroded
    dist[cur] = cap
    return dist


# ---------------------------------------------------------------- capture side

def _load_under(path: str):
    m = schem.load(resolve_capture(path))
    side = path[:-len(".litematic")] + ".scan.json" if path.endswith(".litematic") else None
    origin = (0, 0, 0)
    if side and os.path.exists(side):
        with open(side, encoding="utf-8") as f:
            o = json.load(f)["origin"]
        origin = (int(o["x"]), int(o["y"]), int(o["z"]))
    return m, origin


def _existing_solid(m: schem.Model, strip: set[str]) -> np.ndarray:
    names = np.array([n.split(":")[-1] for n in m.names])
    bad = np.isin(names, list(AIRLIKE | strip))
    return ~bad[m.ids]


def _clear_box(E: np.ndarray, box, origin) -> None:
    ox, oy, oz = origin
    x1, y1, z1, x2, y2, z2 = box
    xs = slice(max(0, min(x1, x2) - ox), max(x1, x2) - ox + 1)
    ys = slice(max(0, min(y1, y2) - oy), max(y1, y2) - oy + 1)
    zs = slice(max(0, min(z1, z2) - oz), max(z1, z2) - oz + 1)
    E[ys, zs, xs] = False


def _auto_encase_level(E: np.ndarray, oy: int) -> int:
    per_y = E.sum(axis=(1, 2))
    return int(np.argmax(per_y)) + oy - 2


# ---------------------------------------------------------------- geometry

def _open2d(mask: np.ndarray, min_width: int) -> np.ndarray:
    """Morphological opening: drops parts thinner than min_width (necks, bridges, 1-2 wide tails)."""
    r = max(0, (int(min_width) - 1) // 2)
    if r == 0:
        return mask
    er = mask.copy()
    for _ in range(r):
        er = er & ~dilate(~er, 1)
    return dilate(er, r) & mask


def _boxes_mask(boxes, origin_xz, shape) -> np.ndarray:
    ox, oz = origin_xz
    m = np.zeros(shape, bool)
    for x1, z1, x2, z2 in boxes:
        m[max(0, min(z1, z2) - oz):max(z1, z2) - oz + 1, max(0, min(x1, x2) - ox):max(x1, x2) - ox + 1] = True
    return m


def _hug_tops(E: np.ndarray, side_gap: int, top_gap: int, overhang: int = 0):
    """Belly top per column = (lowest built block within radius side_gap) - 1 - top_gap.
    The min-filter keeps rock from rising beside anything that hangs lower than its surroundings.
    `overhang` widens the footprint (those columns take their top from the neighbourhood too)."""
    SY = E.shape[0]
    built = E.any(axis=0)
    lowest = np.where(built, np.argmax(E, axis=0), SY)
    r = max(side_gap, overhang)
    nb = lowest.copy()
    for dz in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if max(abs(dz), abs(dx)) <= side_gap or max(abs(dz), abs(dx)) <= overhang:
                nb = np.minimum(nb, _shift(lowest, (dz, dx), fill=SY))
    foot = dilate(built, overhang) if overhang > 0 else built
    top = np.where(foot, nb - 1 - top_gap, -1)
    return top, foot


def _depth_map(foot: np.ndarray, p: dict) -> np.ndarray:
    dist = edge_distance(foot, int(p["ramp"]))
    t = np.clip(dist / float(p["ramp"]), 0, 1) ** 0.8
    zz, xx = np.indices(foot.shape)
    noise = (1.8 * np.sin(0.21 * xx + 1.3) + 1.5 * np.sin(0.17 * zz + 0.4)
             + 1.2 * np.sin(0.11 * (xx + zz) + 2.0) + 0.8 * np.sin(0.29 * (xx - zz) + 0.7))
    d = p["depth_min"] + (p["depth_max"] - p["depth_min"]) * t + noise * t
    d = np.where(foot, np.maximum(1, np.round(d)).astype(int), 0)
    return _despike(d, foot)


def _despike(d: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """No column deeper than every neighbour (kills 1-wide spikes; ridges survive). Two passes."""
    for _ in range(2):
        nb_max = np.zeros_like(d)
        for dz in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dz or dx:
                    nb_max = np.maximum(nb_max, _shift(d, (dz, dx), fill=0))
        d = np.where(foot, np.minimum(d, np.maximum(nb_max, 1)), 0)
    return d


def _drop_small(B: np.ndarray, min_cells: int) -> np.ndarray:
    labels, sizes = morph.components(B, conn=6)
    keep = np.zeros(len(sizes) + 1, bool)
    for i, sz in enumerate(sizes, 1):
        keep[i] = sz >= min_cells
    return B & keep[labels]


# ---------------------------------------------------------------- build

def build(cfg: dict, donors: list | None = None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    if not p.get("under"):
        raise ValueError("belly needs params.under = path to a capture .litematic")
    um, (ox, oy, oz) = _load_under(p["under"])
    E0 = _existing_solid(um, set(p["strip"]))
    for box in p["exclude_boxes"]:
        _clear_box(E0, box, (ox, oy, oz))
    ey_world = p["encase_below"] if p["encase_below"] is not None else _auto_encase_level(E0, oy)
    PAD = int(p["depth_max"]) + 48 + int(p["vine_len"][1]) + 4
    E = np.concatenate([np.zeros((PAD,) + E0.shape[1:], bool), E0], axis=0)
    lo = ey_world - oy + PAD
    hang = np.concatenate([np.zeros((PAD,) + E0.shape[1:], bool), _mask_by_name(um, _is_hanger)], axis=0)
    soft = np.concatenate([np.zeros((PAD,) + E0.shape[1:], bool), _mask_by_name(um, _is_soft)], axis=0)

    B = _geometry(E, hang, soft, lo, (ox, oz), p)
    Wnew, Wsolid = _already_built(p, E, E0.shape, (ox, oy, oz), PAD)
    # "Already built" means a cell of THIS design you have placed - not any block that has appeared
    # since the baseline. Without the mask, a new build under the island (the root stair) becomes part
    # of the belly, and its vines then hang off it below the origin lock.
    Wnew &= B
    B = _drop_small(B & ~Wnew, int(p["min_fragment"]))
    B = _hollow(B, E | Wnew, int(p["wall"]))     # shell against air; built rock counts as mass
    Bfull = B | Wnew                              # decorate against what will actually be there
    outside = morph.flood_outside(Bfull | E, pad=True, ground=False)   # exterior air (not sealed pockets)

    c = Canvas(*[E.shape[i] for i in (2, 0, 1)], donors)
    p = {**p, "_wo": (ox, oy - PAD, oz), "_ymax": lo - 1}   # world offset for texture; vines never climb above the plate underside
    _paint(c, B, E, outside, p)
    # The anchor mask is world-solid AND belly: a vine may only cling to a belly cell that is really
    # there, never to something else that happens to be standing in the same place.
    _vines(c, Bfull, Wsolid & Bfull, Wsolid, outside, p)
    _lanterns(c, Bfull, E | Wnew, outside, p)
    c.world_origin = (ox, oy - PAD, oz)
    c.meta = {"encase_below": int(ey_world), "under": os.path.basename(p["under"]), "clear": ["vine"],
              "exclude_boxes": [list(map(int, b)) for b in p["exclude_boxes"]], "belly_cells": int(B.sum())}
    _crop_y(c)
    return c


def _geometry(E, hang, soft, lo, origin_xz, p) -> np.ndarray:
    """Rock mask before hollowing: hug the built underside, thin skin under sub-plate structures, bridges bare."""
    ys = np.arange(E.shape[0])[:, None, None]
    built = E & ~soft & ~hang & (ys < lo + int(p["hug_max_above"]))
    plate_cols = _open2d((built & (ys >= lo)).any(axis=0), int(p["min_plate_width"]))
    sub_cols = (built & (ys < lo)).any(axis=0)          # anything hanging below the plate level
    top, _ = _hug_tops(built, int(p["side_gap"]), int(p["top_gap"]), int(p["overhang"]))
    foot = dilate(plate_cols, int(p["overhang"])) if p["overhang"] else plate_cols
    depth = _depth_map(foot, p)
    skin = np.zeros_like(foot)
    if p["sub_plate"] != "none":
        skin = sub_cols.copy()
        if p["skin_boxes"]:
            skin &= _boxes_mask(p["skin_boxes"], origin_xz, foot.shape)
        if p["sub_plate"] == "skin":
            depth = np.where(skin, int(p["skin_depth"]), depth)
    foot = (foot & ~sub_cols) | skin
    if p["cut_boxes"]:
        foot &= ~_boxes_mask(p["cut_boxes"], origin_xz, foot.shape)
    return foot[None] & (ys <= top[None]) & (ys > (top - depth)[None]) & ~E & ~dilate(hang & E, 1)


def _already_built(p, E, shape0, origin, PAD):
    """(cells the player has already placed, full blocks in `world` that things may cling to).

    The second mask matters for decoration: `under` is the PRE-build baseline, so a block that has
    since been mined still reads as solid there. Anything that clings to a neighbour has to test
    against what is in the world today, not against the baseline."""
    if not p.get("world"):
        return np.zeros_like(E), E.copy()   # no world file: the baseline is all we know
    ox, oy, oz = origin
    wm, (wx, wy, wz) = _load_under(p["world"])
    W0 = _existing_solid(wm, set(p["strip"]))
    for box in p["exclude_boxes"]:
        _clear_box(W0, box, (wx, wy, wz))
    assert (wx, wz) == (ox, oz) and W0.shape[1:] == shape0[1:], "world capture must share the under capture's x/z box"
    W = np.zeros_like(E)
    y0 = wy - oy + PAD
    src0, dst0 = max(0, -y0), max(0, y0)
    n = min(W0.shape[0] - src0, E.shape[0] - dst0)
    W[dst0:dst0 + n] = W0[src0:src0 + n]
    # Anchors are stricter than "not air": a vine needs a full block face, so walls, fences, slabs
    # and stairs in the world are NOT something to cling to (audit.check_supports agrees).
    F0 = _mask_by_name(wm, audit_mod._is_solid_name)
    F = np.zeros_like(E)
    F[dst0:dst0 + n] = F0[src0:src0 + n]
    return W & ~E, F


def _hollow(B: np.ndarray, E: np.ndarray, wall: int) -> np.ndarray:
    """Drop belly cells farther than `wall` from any air (outside or cavern)."""
    air = ~(B | E)
    near_air = dilate(air, wall)
    return B & near_air


def _paint(c: Canvas, B: np.ndarray, E: np.ndarray, outside: np.ndarray, p: dict) -> None:
    seed = int(p["seed"])
    S = [c.state("cobblestone"), c.state("stone"), c.state("mossy_cobblestone"), c.state("stone_bricks"),
         c.state("mossy_stone_bricks"), c.state("cracked_stone_bricks"), c.state("cobblestone")]
    W = [0.34, 0.24, 0.16, 0.10, 0.08, 0.06, 0.02]
    cum = np.cumsum(W)
    moss = c.state("moss_block")
    below_air = _shift(outside, (1, 0, 0))              # cell below is exterior air
    wox, woy, woz = p.get("_wo", (0, 0, 0))
    for (y, z, x) in zip(*np.where(B)):
        wx_, wy_, wz_ = x + wox, y + woy, z + woz
        h = hash01(wx_, wy_, wz_, 7, seed)
        if below_air[y, z, x] and hash01(wx_, wz_, 11, seed) < p["moss_bottom"]:
            c.put(x, y, z, moss)
            continue
        c.put(x, y, z, S[int(np.searchsorted(cum, h))])



def _vines(c: Canvas, B: np.ndarray, held: np.ndarray, taken: np.ndarray, outside: np.ndarray, p: dict) -> None:
    """Strands down the outer side faces: side-attached while beside rock, vine-under-vine below.

    `held` is belly that is really there today (a legal anchor); `taken` is everything solid in the
    world today (never build into it). The baseline predates anything you have built since, so
    without `taken` the strand runs straight through, say, the taproot you just put up."""
    seed = int(p["seed"])
    lo, hi = p["vine_len"]
    # (dz, dx) = offset from the vine cell to the belly cell it clings to; prop name = that direction
    for dname, (dz, dx) in {"east": (0, 1), "west": (0, -1), "south": (1, 0), "north": (-1, 0)}.items():
        face = B & _shift(outside, (0, dz, dx))     # belly cell whose (z-dz, x-dx) neighbour is outside air
        for (z, x) in zip(*np.where(face.any(axis=0))):
            if hash01(x, z, 31, seed) >= p["vine_rate"]:
                continue
            vx, vz = x - dx, z - dz
            rows = np.where(face[:, z, x])[0]
            rows = rows[rows <= int(p.get("_ymax", 10**9))]        # never start above the plate underside
            if rows.size == 0:
                continue
            y = int(rows.max())
            L = lo + int(hash01(x, z, 37, seed) * (hi - lo + 1))
            hang = 0
            while y >= 0 and c.get(vx, y, vz) == 0 and outside[y, vz, vx] and not taken[y, vz, vx]:
                if not B[y, vz + dz, vx + dx]:
                    hang += 1
                    if hang > L:
                        break
                # A side-attached vine needs its neighbour to exist for real: either this file places
                # it, or the world already has it. `B` here is the FULL belly, which still contains
                # rock that `_already_built` dropped - clinging to that leaves an orphan strand.
                # Must be a BELLY cell, and really there: either this file places it or the world
                # already has it. Without the B test a vine will happily cling to anything solid that
                # turns up nearby - the root stair, once built - and hang below the origin lock.
                anchored = B[y, vz + dz, vx + dx] and (
                    c.get(vx + dx, y, vz + dz) != 0 or held[y, vz + dz, vx + dx])
                above = c.get(vx, y + 1, vz) != 0
                if not anchored and not above:
                    break
                c.put(vx, y, vz, c.vine(vx, y, vz, dname))
                y -= 1


def _lanterns(c: Canvas, B, E, outside, p: dict) -> None:
    seed = int(p["seed"])
    S = {"chain": c.raw_state("iron_chain", axis="y", waterlogged="false"),
         "lant_h": c.raw_state("lantern", hanging="true", waterlogged="false"),
         "soul_h": c.raw_state("soul_lantern", hanging="true", waterlogged="false")}
    bottom = B & _shift(outside, (1, 0, 0))                    # belly cell with exterior air below
    _scatter_hang(c, bottom, E, int(p["lanterns_out"]), (1, 3), 41, seed, S, min_gap=6)


def _scatter_hang(c, faces, E, n, drop_range, salt, seed, S, min_gap):
    cand = [(int(y), int(z), int(x)) for y, z, x in zip(*np.where(faces))]
    cand.sort(key=lambda t: hash01(t[2], t[1], salt, seed))
    placed = []
    for y, z, x in cand:
        if len(placed) >= n:
            break
        if any(abs(x - px) < min_gap and abs(z - pz) < min_gap for px, pz in placed):
            continue
        drop = drop_range[0] + int(hash01(x, z, salt + 1, seed) * (drop_range[1] - drop_range[0] + 1))
        if y - drop - 1 < 0 or any(E[y - i, z, x] for i in range(1, drop + 2)):
            continue
        if c.hang_string(x, y, z, drop, "soul" if hash01(x, z, salt + 2, seed) < 0.15 else "lant", S):
            placed.append((x, z))


def _crop_y(c: Canvas) -> None:
    ys = np.where(c.ids.any(axis=(1, 2)))[0]
    if ys.size == 0:
        return
    y0, y1 = int(ys.min()), int(ys.max())
    c.ids = c.ids[y0:y1 + 1]
    c.sy = c.ids.shape[0]
    ox, oy, oz = c.world_origin
    c.world_origin = (ox, oy + y0, oz)
