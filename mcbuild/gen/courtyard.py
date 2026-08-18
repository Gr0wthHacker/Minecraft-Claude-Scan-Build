"""The sky-well court: a garden on the moss skin between the statue lobe and the working deck.

    court:  the floor here is a ONE-BLOCK skin over open air, so a sunken basin would drain into the
            void - the pool is built up instead, water one course proud of the floor inside a rim.
            Planting grades by distance from the water, dripstone hangs off the statue's underside,
            and the light stays out of sight: lanterns under the water, glow lichen on the rock.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01
from .interior import AIRY, DIRS, _at, _slab
from .vertical import Ctx, World

COURT = {
    "under": None,               # capture that supplies the floor - pin it once building starts
    "floor_y": 194,              # the moss skin the court stands on
    "box": None,                 # [x1, z1, x2, z2] window to look for the floor in
    "sky_probe": 20,             # a cell counts as open if nothing sits above it for this many blocks
    "pool_center": None,         # world (x, z); defaults to the centroid of the open cells
    "pool_r": 4.6, "pool_wobble": 1.5, "pool_inset": 1,   # every cell around the water must have floor,
                                                          # so the rim never hangs off the lip of the skin
    "rill": True,                # a channel running from the pool toward the covered side
    "sink_lanterns": 0.12,       # share of pool cells with a submerged lantern (the hidden light)
    "lichen": 0.20,              # share of eligible rock faces that get glow lichen
    "carpet": 0.30, "azalea": 0.07, "grass": 0.11, "dripleaf": 0.03,
    "dripstone": 0.10,           # share of the covered ceiling that grows a dripstone tip
    "edge_slabs": True,          # a slab lip where the open well meets the covered apron
    "clear_names": ["redstone_wire", "repeater", "comparator", "stone_button", "lever", "redstone_torch"],
    "seed": 0,
}

WET = ("water", "bubble_column")
SOFT = AIRY + WET
# short grass, azalea and dripleaf only take on soil; carpet and slabs sit on anything solid.
SOIL = ("moss_block", "grass_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "mud", "clay")


def build_court(cfg: dict, donors=None) -> Canvas:
    p = {**COURT, **cfg}
    ctx = Ctx(p["under"])
    fy, seed = int(p["floor_y"]), int(p["seed"])
    wy = fy + 1                                       # the course everything stands on

    floor = _slab(ctx, fy, p["box"])
    openc = _sky_open(ctx, floor, wy, int(p["sky_probe"]))
    dig = _dead_cells(ctx, floor, wy, p["clear_names"])     # the abandoned circuit comes out first
    w = World()

    pool = _pool_cells(ctx, openc, floor, p, seed)
    _pool(ctx, w, dig, pool, wy, p, seed)
    rill = _rill(ctx, w, dig, pool, openc, floor, wy, p) if p["rill"] else []
    wet = set(pool) | set(rill)
    _planting(ctx, w, dig, floor, openc, wet, wy, p, seed)
    if p["edge_slabs"]:
        _edge(ctx, w, dig, floor, openc, wet, wy, p, seed)
    drips = _dripstone(ctx, w, floor, openc, fy, p, seed)
    lichen = _lichen(ctx, w, floor, wy, p, seed)

    return w.canvas({
        "kind": "court", "floor_y": fy, "open_cells": len(openc), "pool": len(pool), "rill": len(rill),
        "dripstone": drips, "lichen": lichen, "dig": [list(d) for d in dig],
    })


# ------------------------------------------------------------------ reading the space

def _sky_open(ctx: Ctx, floor: np.ndarray, wy: int, probe: int) -> set:
    return {(X, Z) for (X, Z) in _floor_cells(ctx, floor)
            if all(ctx.name_at(X, y, Z) in AIRY for y in range(wy, wy + probe))}


def _floor_cells(ctx: Ctx, floor: np.ndarray) -> list:
    # int() matters: numpy scalars leak all the way into the sidecar and json.dump chokes on them
    return [(int(x) + ctx.ox, int(z) + ctx.oz) for z, x in np.argwhere(floor)]


def _dead_cells(ctx: Ctx, floor: np.ndarray, wy: int, names) -> list:
    out = []
    for (X, Z) in _floor_cells(ctx, floor):
        for y in (wy, wy + 1):
            if ctx.name_at(X, y, Z) in names:
                out.append((X, int(y), Z))
    return out


def _inset_ok(ctx: Ctx, floor: np.ndarray, X: int, Z: int, inset: int) -> bool:
    """True when every cell within `inset` still has floor - water must never reach the lip."""
    return all(_at(floor, Z + dz - ctx.oz, X + dx - ctx.ox)
               for dx in range(-inset, inset + 1) for dz in range(-inset, inset + 1))


# ------------------------------------------------------------------ water

def _pool_cells(ctx, openc, floor, p, seed) -> list:
    if not openc:
        return []
    if p["pool_center"]:
        cx, cz = int(p["pool_center"][0]), int(p["pool_center"][1])
    else:
        cx = round(sum(x for x, _ in openc) / len(openc))
        cz = round(sum(z for _, z in openc) / len(openc))
    r, wob, inset = float(p["pool_r"]), float(p["pool_wobble"]), int(p["pool_inset"])
    out = []
    for (X, Z) in sorted(openc):
        d = ((X - cx) ** 2 + (Z - cz) ** 2) ** 0.5
        if d > r + wob * (hash01(X, Z, 31, seed) - 0.3):
            continue
        if not _inset_ok(ctx, floor, X, Z, inset):
            continue
        out.append((X, Z))
    return out


def _pool(ctx, w, dig, pool, wy, p, seed):
    """Water one block proud of the floor, held in by a rim on every open side."""
    wet = set(pool)
    for (X, Z) in pool:
        _put(w, dig, ctx, X, wy, Z, "water", level="0")
    for (X, Z) in pool:
        for _, dx, dz in DIRS:
            nx, nz = X + dx, Z + dz
            if (nx, nz) in wet or ctx.name_at(nx, wy, nz) not in AIRY:
                continue
            kind = "mossy_cobblestone" if hash01(nx, nz, 37, seed) < 0.55 else "moss_block"
            _put(w, dig, ctx, nx, wy, nz, kind)
    for (X, Z) in pool:                               # the light lives under the water
        if hash01(X, Z, 41, seed) < p["sink_lanterns"] and _held(w, X, wy, Z):
            w.put(X, wy, Z, "lantern", hanging="false", waterlogged="true")


def _held(w, X, y, Z) -> bool:
    """Only sink a lantern where the design itself walls all four sides - never against raw air."""
    return all(w.name(X + dx, y, Z + dz) in ("water", "moss_block", "mossy_cobblestone")
               for _, dx, dz in DIRS)


def _rill(ctx, w, dig, pool, openc, floor, wy, p) -> list:
    """A one-wide channel from the pool toward the covered side, walled the same way."""
    covered = [c for c in _floor_cells(ctx, floor) if c not in openc]
    if not pool or not covered:
        return []
    cx = sum(x for x, _ in pool) / len(pool)
    cz = sum(z for _, z in pool) / len(pool)
    dx = sum(x for x, _ in covered) / len(covered) - cx
    dz = sum(z for _, z in covered) / len(covered) - cz
    step = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dz) else (0, 1 if dz > 0 else -1)
    X, Z = max(pool, key=lambda c: (c[0] - cx) * step[0] + (c[1] - cz) * step[1])
    out = []
    for _ in range(10):
        X, Z = X + step[0], Z + step[1]
        if (X, Z) in pool or not _inset_ok(ctx, floor, X, Z, 1) or ctx.name_at(X, wy, Z) not in AIRY:
            break
        _put(w, dig, ctx, X, wy, Z, "water", level="0")
        out.append((X, Z))
    for (X, Z) in out:                                # wall it after the run is known
        for _, ax, az in DIRS:
            nx, nz = X + ax, Z + az
            if (nx, nz) in out or (nx, nz) in pool or w.has(nx, wy, nz):
                continue
            if ctx.name_at(nx, wy, nz) in AIRY:
                _put(w, dig, ctx, nx, wy, nz, "mossy_cobblestone")
    return out


# ------------------------------------------------------------------ planting and finish

def _planting(ctx, w, dig, floor, openc, wet, wy, p, seed):
    """Foliage thickest near the water, thinning under the statue's overhang."""
    for (X, Z) in _floor_cells(ctx, floor):
        if (X, Z) in wet or w.has(X, wy, Z) or not _plantable(ctx, dig, X, wy, Z):
            continue
        near = min((abs(X - a) + abs(Z - b) for a, b in wet), default=99)
        boost = 1.5 if near <= 3 else (1.2 if near <= 6 else 1.0)
        carpet, az, gr, dl = (p["carpet"] * boost, p["azalea"] * boost, p["grass"] * boost, p["dripleaf"] * boost)
        if (X, Z) not in openc:
            carpet, az, gr, dl = carpet * 0.6, az * 0.3, gr * 0.4, 0.0
        if ctx.name_at(X, wy - 1, Z) not in SOIL:
            dl = az = gr = 0.0                        # bare rock takes carpet, nothing that roots
        h = hash01(X, Z, 47, seed)
        if h < dl and near <= 2:
            _put(w, dig, ctx, X, wy, Z, "small_dripleaf", half="lower", facing="north", waterlogged="false")
        elif h < dl + az:
            _put(w, dig, ctx, X, wy, Z, "flowering_azalea" if hash01(X, Z, 53, seed) < 0.4 else "azalea")
        elif h < dl + az + gr:
            _put(w, dig, ctx, X, wy, Z, "short_grass")
        elif h < dl + az + gr + carpet:
            _put(w, dig, ctx, X, wy, Z, "moss_carpet")


def _plantable(ctx, dig, X, wy, Z) -> bool:
    if ctx.name_at(X, wy - 1, Z) in AIRY:             # nothing to stand on
        return False
    return ctx.name_at(X, wy, Z) in AIRY or (X, wy, Z) in dig


def _edge(ctx, w, dig, floor, openc, wet, wy, p, seed):
    """A slab lip where the sky-lit court meets the covered apron, so the well reads as a room."""
    for (X, Z) in _floor_cells(ctx, floor):
        if (X, Z) not in openc or (X, Z) in wet or w.has(X, wy, Z):
            continue
        if all((X + dx, Z + dz) in openc for _, dx, dz in DIRS):
            continue                                  # interior of the court, not its lip
        if not _plantable(ctx, dig, X, wy, Z) or hash01(X, Z, 59, seed) > 0.7:
            continue
        kind = "mossy_cobblestone_slab" if hash01(X, Z, 61, seed) < 0.6 else "cobblestone_slab"
        _put(w, dig, ctx, X, wy, Z, kind, type="bottom", waterlogged="false")


def _dripstone(ctx, w, floor, openc, fy, p, seed) -> int:
    """Tips hanging off the statue's underside over the covered apron."""
    n = 0
    for (X, Z) in _floor_cells(ctx, floor):
        if (X, Z) in openc or hash01(X, Z, 67, seed) >= p["dripstone"]:
            continue
        ceil = next((y for y in range(fy + 3, fy + 12) if ctx.name_at(X, y, Z) not in AIRY), None)
        if ceil is None or ceil - fy < 4 or w.has(X, ceil - 1, Z):
            continue
        w.put(X, ceil - 1, Z, "pointed_dripstone", vertical_direction="down", thickness="tip", waterlogged="false")
        n += 1
    return n


def _lichen(ctx, w, floor, wy, p, seed) -> int:
    """Glow lichen on whatever rock bounds the well: light 7 is plenty to stop spawns, and it reads
    as part of the moss rather than as lighting."""
    n = 0
    for (X, Z) in _floor_cells(ctx, floor):
        for y in range(wy, wy + 8):
            if ctx.name_at(X, y, Z) not in AIRY or w.has(X, y, Z):
                continue
            if hash01(X, y, Z, 71, seed) >= p["lichen"]:
                continue
            sides = {f: ("true" if ctx.name_at(X + dx, y, Z + dz) not in SOFT else "false")
                     for f, dx, dz in DIRS}
            sides["up"] = "true" if ctx.name_at(X, y + 1, Z) not in SOFT else "false"
            sides["down"] = "true" if ctx.name_at(X, y - 1, Z) not in SOFT else "false"
            if not any(v == "true" for v in sides.values()):
                continue
            w.put(X, y, Z, "glow_lichen", waterlogged="false", **sides)
            n += 1
    return n


def _put(w: World, dig: list, ctx: Ctx, x, y, z, name, **props) -> bool:
    """Place, recording anything that has to come out first (vines, the dead circuit)."""
    x, y, z = int(x), int(y), int(z)
    if w.has(x, y, z):
        return False
    here = ctx.name_at(x, y, z)
    if here not in AIRY and (x, y, z) not in dig:
        return False
    if here not in ("air", "cave_air", "void_air") and (x, y, z) not in dig:
        dig.append((x, y, z))
    w.put(x, y, z, name, **props)
    return True
