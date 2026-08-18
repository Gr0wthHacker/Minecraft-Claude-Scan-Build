"""Dressing kits fitted to a capture: chimney smoke, statue footings, rim hem, paths (+ light posts),
entrance frame, ride lights, apiary flowers, bird lanterns.

    chimney:  campfire + 4 stone-brick wall posts on the highest roof block of each given (x, z); smoke rises
              through the open top. `soul: [i, ...]` indexes that get a soul campfire.
    footing:  ragged ring of moss carpet / azalea / short grass / a few mossy cobbles on the lawn around a
              build's footprint (world box), so statues sit in the ground instead of on it.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01
from .vertical import Ctx, World, load_capture

CHIMNEY = {"under": None, "points": [], "max_y": 240, "soul": [], "seed": 0}
FOOTING = {"under": None, "boxes": [], "ring": 2, "lawn_y": 202, "carpet": 0.55, "azalea": 0.10, "grass": 0.12,
           "cobble": 0.08, "seed": 0}


def build_chimney(cfg: dict, donors=None) -> Canvas:
    p = {**CHIMNEY, **cfg}
    ctx = Ctx(p["under"])
    w = World()
    placed = []
    for i, (x, z) in enumerate(p["points"]):
        top = _roof_top(ctx, x, z, int(p["max_y"]))
        if top is None:
            continue
        y = top + 1
        if any(ctx.occupied(x + dx, y + dy, z + dz) for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)) for dy in (0, 1)):
            continue
        name = "soul_campfire" if i in p["soul"] else "campfire"
        w.put(x, y, z, name, lit="true", signal_fire="false", facing="north", waterlogged="false")
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            w.put(x + dx, y, z + dz, "stone_brick_wall", up="true", north="none", south="none", east="none", west="none", waterlogged="false")
        placed.append([x, y, z, name])
    return w.canvas({"kind": "chimney", "placed": placed})


def _roof_top(ctx: Ctx, x, z, max_y):
    lx, lz = x - ctx.ox, z - ctx.oz
    if not (0 <= lz < ctx.m.ids.shape[1] and 0 <= lx < ctx.m.ids.shape[2]):
        return None
    col = np.where(ctx.solid[:, lz, lx])[0]
    col = col[col + ctx.oy <= max_y]
    skip = {"torch", "wall_torch", "lantern", "soul_lantern", "moss_carpet", "short_grass", "vine", "iron_chain"}
    for y in sorted(col.tolist(), reverse=True):
        if str(ctx.names[ctx.m.ids[y, lz, lx]]) not in skip:
            return int(y + ctx.oy)
    return None


def build_footing(cfg: dict, donors=None) -> Canvas:
    p = {**FOOTING, **cfg}
    ctx = Ctx(p["under"])
    seed, ly = int(p["seed"]), int(p["lawn_y"])
    w = World()
    for k, (x1, z1, x2, z2) in enumerate(p["boxes"]):
        foot = _footprint(ctx, x1, z1, x2, z2, ly + 1)
        ring = _dilate_pts(foot, int(p["ring"])) - foot
        for (x, z) in sorted(ring):
            if ctx.name_at(x, ly, z) != "moss_block" or ctx.name_at(x, ly + 1, z) != "air":
                continue
            h = hash01(x, z, 81 + k, seed)
            edge = 1.0 - min(1.0, _dist_to(foot, x, z) / (int(p["ring"]) + 0.5))   # denser near the build
            if h < p["carpet"] * (0.6 + 0.6 * edge):
                w.put(x, ly + 1, z, "moss_carpet")
            elif h < p["carpet"] + p["azalea"]:
                w.put(x, ly + 1, z, "azalea" if hash01(x, z, 83, seed) < 0.7 else "flowering_azalea")
            elif h < p["carpet"] + p["azalea"] + p["grass"]:
                w.put(x, ly + 1, z, "short_grass")
            elif h < p["carpet"] + p["azalea"] + p["grass"] + p["cobble"]:
                w.put(x, ly + 1, z, "mossy_cobblestone")
    return w.canvas({"kind": "footing", "boxes": p["boxes"]})


def _footprint(ctx: Ctx, x1, z1, x2, z2, y):
    pts = set()
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for z in range(min(z1, z2), max(z1, z2) + 1):
            if ctx.name_at(x, y, z) not in ("air", "vine"):
                pts.add((x, z))
    return pts


def _dilate_pts(pts, r):
    out = set()
    for (x, z) in pts:
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                out.add((x + dx, z + dz))
    return out


def _dist_to(pts, x, z):
    return min(max(abs(x - px), abs(z - pz)) for (px, pz) in pts) if pts else 99

# ================================================================== rim hem

HEM = {"under": None, "lawn_y": 202, "ring": 2, "carpet": 0.40, "azalea": 0.07, "grass": 0.14, "stairs": 0.10, "seed": 0}


def build_hem(cfg: dict, donors=None) -> Canvas:
    """Perimeter treatment: moss carpet / azalea / grass on the rim ring of the lawn, and the odd
    mossy-cobble stair hung off the plate edge so the lip reads eroded instead of cut."""
    p = {**HEM, **cfg}
    ctx = Ctx(p["under"])
    ly, seed = int(p["lawn_y"]), int(p["seed"])
    plate = _plate_mask(ctx, ly)
    ring = plate & ~_erode(plate, int(p["ring"]))
    edge = plate & ~_erode(plate, 1)
    w = World()
    for (z, x) in np.argwhere(ring):
        X, Z = x + ctx.ox, z + ctx.oz
        if ctx.name_at(X, ly, Z) != "moss_block" or ctx.name_at(X, ly + 1, Z) != "air" or _column_busy(ctx, X, Z, ly + 2, ly + 12):
            continue
        h = hash01(X, Z, 91, seed)
        if h < p["carpet"]:
            w.put(X, ly + 1, Z, "moss_carpet")
        elif h < p["carpet"] + p["azalea"]:
            w.put(X, ly + 1, Z, "azalea" if hash01(X, Z, 93, seed) < 0.6 else "flowering_azalea")
        elif h < p["carpet"] + p["azalea"] + p["grass"]:
            w.put(X, ly + 1, Z, "short_grass")
    for (z, x) in np.argwhere(edge):
        X, Z = x + ctx.ox, z + ctx.oz
        if hash01(X, Z, 95, seed) >= p["stairs"]:
            continue
        for facing, (dx, dz) in (("east", (-1, 0)), ("west", (1, 0)), ("south", (0, -1)), ("north", (0, 1))):
            ox_, oz_ = X + dx, Z + dz            # the outside cell; stair faces back toward the island
            if plate[z + dz, x + dx] if (0 <= z + dz < plate.shape[0] and 0 <= x + dx < plate.shape[1]) else True:
                continue
            ye = ly if ctx.name_at(X, ly, Z) not in ("air", "moss_carpet", "short_grass", "vine") else ly - 1   # height of the edge block
            if ctx.name_at(X, ye, Z) in ("air", "vine", "moss_carpet", "short_grass"):
                continue
            if ctx.name_at(ox_, ye, oz_) == "air" and ctx.name_at(ox_, ye + 1, oz_) == "air" and not w.has(ox_, ye, oz_):
                w.put(ox_, ye, oz_, "mossy_cobblestone_stairs", facing=facing, half="bottom", shape="straight", waterlogged="false")
                break
    return w.canvas({"kind": "hem"})


def _plate_mask(ctx: Ctx, ly: int) -> np.ndarray:
    ys = np.arange(ctx.m.ids.shape[0])[:, None, None]
    return (ctx.solid & (ys + ctx.oy >= ly - 2) & (ys + ctx.oy <= ly + 1)).any(axis=0)


def _erode(mask: np.ndarray, r: int) -> np.ndarray:
    from .belly import dilate
    out = mask.copy()
    for _ in range(r):
        out = out & ~dilate(~out, 1)
    return out


def _column_busy(ctx: Ctx, x, z, y0, y1) -> bool:
    return any(ctx.name_at(x, y, z) not in ("air", "vine") for y in range(y0, y1 + 1))


# ================================================================== paths

PATHS = {"under": None, "nodes": [], "lawn_y": 202, "slab_mix": [["stone_brick_slab", 0.45], ["mossy_cobblestone_slab", 0.35], ["cobblestone_slab", 0.20]],
         "avoid_names": ["water"], "seed": 0}
PATH_NAMES = {"stone_brick_slab", "mossy_cobblestone_slab", "cobblestone_slab", "mossy_stone_brick_slab", "smooth_stone_slab",
              "stone_brick_stairs", "mossy_stone_brick_stairs", "cobblestone_stairs", "mossy_cobblestone_stairs"}
GROUND = {"moss_block", "cobblestone", "mossy_cobblestone", "stone", "stone_bricks", "mossy_stone_bricks", "grass_block", "dirt",
          "coarse_dirt", "rooted_dirt", "podzol", "snow_block", "smooth_stone", "andesite", "gravel", "cracked_stone_bricks"}
DIGGABLE = {"short_grass", "tall_grass", "moss_carpet", "pink_tulip", "white_tulip", "poppy", "dandelion", "azalea",
            "flowering_azalea", "lily_of_the_valley", "fern"}


def build_paths(cfg: dict, donors=None) -> Canvas:
    """Connect the given nodes into one network (MST of A* routes) with bottom slabs on the lawn (existing
    path cells are reused at near-zero cost, never re-placed). Sidecar carries the dig list (plants)."""
    p = {**PATHS, **cfg}
    ctx = Ctx(p["under"])
    ly, seed = int(p["lawn_y"]), int(p["seed"])
    nodes = [tuple(n) for n in p["nodes"]] + _fragment_nodes(ctx, ly)
    routes, dig = _mst_routes(ctx, nodes, ly, p)
    w = World()
    mix = p["slab_mix"]; cum = np.cumsum([m[1] for m in mix])
    for (x, z) in routes:
        c = _cell(ctx, x, z, ly)
        if c is None or c[2]:
            continue
        name = mix[int(np.searchsorted(cum, hash01(x, z, 101, seed) * cum[-1]))][0]
        w.put(x, c[0] + 1, z, name, type="bottom", waterlogged="false")
    return w.canvas({"kind": "paths", "nodes": [list(n) for n in nodes], "cells": len(routes), "dig": [list(d) for d in dig]})


def _fragment_nodes(ctx: Ctx, ly: int, min_cells: int = 9) -> list:
    """One representative cell per existing path fragment, so the MST stitches every fragment in."""
    from .. import morph
    ys = np.arange(ctx.m.ids.shape[0])[:, None, None]
    pathm = (np.isin(ctx.names[ctx.m.ids], list(PATH_NAMES)) & (ys + ctx.oy >= ly) & (ys + ctx.oy <= ly + 2)).any(axis=0)
    labels, sizes = morph.components(pathm[None], conn=6)
    out = []
    for i, sz_ in enumerate(sizes, 1):
        if sz_ < min_cells:
            continue
        cells = np.argwhere(labels[0] == i)
        cz, cx = cells.mean(axis=0)
        z, x = min(cells, key=lambda c: (c[0] - cz) ** 2 + (c[1] - cx) ** 2)      # the cell nearest the centroid
        out.append((int(x + ctx.ox), int(z + ctx.oz)))
    return out


def _cell(ctx: Ctx, x, z, ly):
    """(ground height h, step cost, is_existing_path) for a walkable column, or None.
    Ground may sit at ly-1..ly+1 so paths follow 1-block terraces; a new slab goes at h+1."""
    for h in (ly + 1, ly, ly - 1):
        s, a, above = ctx.name_at(x, h, z), ctx.name_at(x, h + 1, z), ctx.name_at(x, h + 2, z)
        if a in PATH_NAMES and above == "air":
            return h, 0.15, True
        if s in PATH_NAMES and a == "air":
            return h - 1, 0.15, True
        if s in GROUND and (a == "air" or a in DIGGABLE) and above == "air":
            return h, (1.0 if s == "moss_block" else 1.4) if a == "air" else 1.2, False
        if s not in ("air", "vine") and s not in DIGGABLE:
            return None                                   # something solid but not walkable ground (build, water...)
    return None


def _walk_cost(ctx: Ctx, x, z, ly, p):
    c = _cell(ctx, x, z, ly)
    return None if c is None else c[1]


def _astar(ctx: Ctx, a, b, ly, p):
    import heapq
    (ax, az), (bx, bz) = a, b
    ca = _cell(ctx, ax, az, ly)
    if ca is None:
        return None
    best = {a: 0.0}; prev = {}; height = {a: ca[0]}
    pq = [(abs(ax - bx) + abs(az - bz), 0.0, a)]
    while pq:
        _, g, cur = heapq.heappop(pq)
        if cur == b:
            break
        if g > best.get(cur, 1e18):
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = cur[0] + dx, cur[1] + dz
            c = _cell(ctx, nx, nz, ly)
            if c is None or abs(c[0] - height[cur]) > 1:
                continue
            ng = g + c[1] + (0.6 if c[0] != height[cur] else 0.0)
            if ng < best.get((nx, nz), 1e18):
                best[(nx, nz)] = ng; prev[(nx, nz)] = cur; height[(nx, nz)] = c[0]
                heapq.heappush(pq, (ng + abs(nx - bx) + abs(nz - bz), ng, (nx, nz)))
    if b not in prev and a != b:
        return None
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    return path[::-1]


def _mst_routes(ctx: Ctx, nodes, ly, p):
    """Prim's MST on straight-line distance, each edge routed with A*."""
    if not nodes:
        return [], []
    done = {nodes[0]}; cells = []; dig = []
    while len(done) < len(nodes):
        best = None
        for a in done:
            for b in nodes:
                if b in done:
                    continue
                d = abs(a[0] - b[0]) + abs(a[1] - b[1])
                if best is None or d < best[0]:
                    best = (d, a, b)
        _, a, b = best
        r = _astar(ctx, a, b, ly, p)
        done.add(b)
        if r is None:
            continue
        for (x, z) in r:
            cells.append((x, z))
            c = _cell(ctx, x, z, ly)
            if c is not None and not c[2] and ctx.name_at(x, c[0] + 1, z) in DIGGABLE:
                dig.append((x, c[0] + 1, z, ctx.name_at(x, c[0] + 1, z)))
    seen = set(); out = []
    for c in cells:
        if c not in seen:
            seen.add(c); out.append(c)
    return out, dig


# ================================================================== light posts (along a paths design)

LIGHTPOSTS = {"under": None, "paths": None, "every": 9, "lawn_y": 202, "seed": 0}


def build_lightposts(cfg: dict, donors=None) -> Canvas:
    """Oak fence + lantern beside the path every N cells; sidecar lists surface torches to remove."""
    p = {**LIGHTPOSTS, **cfg}
    ctx = Ctx(p["under"])
    ly = int(p["lawn_y"])
    pm, (px0, py0, pz0) = load_capture(p["paths"])
    pn = np.array([n.split(":")[-1] for n in pm.names])
    cells = [(int(x + px0), int(z + pz0)) for y, z, x in np.argwhere(pm.ids > 0)]
    ys = np.arange(ctx.m.ids.shape[0])[:, None, None]
    existing = (np.isin(ctx.names[ctx.m.ids], list(PATH_NAMES)) & (ys + ctx.oy >= ly) & (ys + ctx.oy <= ly + 2)).any(axis=0)
    cells += [(int(x + ctx.ox), int(z + ctx.oz)) for z, x in np.argwhere(existing)]
    cells = sorted(set(cells), key=lambda t: (t[0] + t[1], t[0]))
    cellset = set(cells)
    # posts already standing in the world seed the spacing rule, so regenerating never crowds them
    placed = [(int(x + ctx.ox), int(z + ctx.oz)) for y, z, x in np.argwhere(ctx.names[ctx.m.ids] == "oak_fence")
              if y + ctx.oy >= ly and str(ctx.names[ctx.m.ids[y + 1, z, x]]) in ("lantern", "soul_lantern")]
    w = World(); k = 0
    for (x, z) in cells:
        if any(abs(x - qx) + abs(z - qz) < int(p["every"]) for qx, qz in placed):
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            bx, bz = x + dx, z + dz
            c = _cell(ctx, bx, bz, ly)
            if (bx, bz) in cellset or c is None or c[2] or ctx.name_at(bx, c[0] + 1, bz) != "air" or ctx.name_at(bx, c[0] + 3, bz) != "air":
                continue
            w.put(bx, c[0] + 1, bz, "oak_fence", north="false", south="false", east="false", west="false", waterlogged="false")
            w.put(bx, c[0] + 2, bz, "lantern", hanging="false", waterlogged="false")
            placed.append((bx, bz)); k += 1
            break
    torches = [(int(x + ctx.ox), int(y + ctx.oy), int(z + ctx.oz)) for y, z, x in np.argwhere(np.isin(ctx.names[ctx.m.ids], ["torch", "wall_torch"])) if y + ctx.oy >= ly]
    return w.canvas({"kind": "lightposts", "posts": k, "existing_posts": len(placed) - k, "remove_torches": torches})


# ================================================================== entrance frame

ENTRANCE = {"under": None, "ladder": [-24190, 29991], "landing_z": 29992, "lawn_y": 202}


def build_entrance(cfg: dict, donors=None) -> Canvas:
    """Top of the vine ladder down to the deck: two stone-brick wall posts flanking it, a lantern on one,
    two mossy slabs as the landing."""
    p = {**ENTRANCE, **cfg}
    ctx = Ctx(p["under"])
    lx, lz = p["ladder"]; zl = int(p["landing_z"]); ly = int(p["lawn_y"])
    w = World()
    def top(x, z):
        for y in range(ly + 1, ly - 3, -1):
            if ctx.name_at(x, y, z) not in ("air", "vine"):
                return y
        return None
    for k, dx in enumerate((-1, 1)):
        x = lx + dx
        t = top(x, zl)
        if t is not None and ctx.name_at(x, t + 1, zl) == "air":
            w.put(x, t + 1, zl, "stone_brick_wall", up="true", north="none", south="none", east="none", west="none", waterlogged="false")
            if k == 0 and ctx.name_at(x, t + 2, zl) == "air":
                w.put(x, t + 2, zl, "lantern", hanging="false", waterlogged="false")
    for dz in (0, 1):
        t = top(lx, zl + dz)
        if t is not None and ctx.name_at(lx, t + 1, zl + dz) == "air":
            w.put(lx, t + 1, zl + dz, "mossy_stone_brick_slab", type="bottom", waterlogged="false")
    return w.canvas({"kind": "entrance", "keep_vine_ladder_at": [lx, lz]})


# ================================================================== ride lights (under the plate along the rails)

RIDELIGHTS = {"under": None, "every": 6, "plate_y": 201, "seed": 0}


def build_ridelights(cfg: dict, donors=None) -> Canvas:
    """Chain + lantern from the plate underside above rail cells that run under the plate, spaced along the line."""
    p = {**RIDELIGHTS, **cfg}
    ctx = Ctx(p["under"])
    rails = sorted({(int(x + ctx.ox), int(y + ctx.oy), int(z + ctx.oz)) for y, z, x in np.argwhere(np.isin(ctx.names[ctx.m.ids], ["rail", "powered_rail"]))},
                   key=lambda t: (t[0] + t[2], t[0]))
    w = World(); placed = []
    for (x, y, z) in rails:
        py = int(p["plate_y"])
        from ..audit import _is_solid_name
        if not _is_solid_name(ctx.name_at(x, py, z)) or y > py - 5:                    # needs plate above and 2 blocks of rider headroom below the lantern
            continue
        if any(abs(x - qx) + abs(z - qz) < int(p["every"]) for qx, qz in placed):
            continue
        if any(ctx.name_at(x, yy, z) != "air" for yy in (py - 1, py - 2)):
            continue
        w.put(x, py - 1, z, "iron_chain", axis="y", waterlogged="false")
        w.put(x, py - 2, z, "lantern", hanging="true", waterlogged="false")
        placed.append((x, z))
    return w.canvas({"kind": "ridelights", "count": len(placed)})


# ================================================================== apiary flowers

APIARY = {"under": None, "center": None, "radius": 8, "count": 12, "lawn_y": 202, "seed": 0}


def build_apiary(cfg: dict, donors=None) -> Canvas:
    p = {**APIARY, **cfg}
    ctx = Ctx(p["under"])
    cx, cz = p["center"]; r, ly, seed = int(p["radius"]), int(p["lawn_y"]), int(p["seed"])
    cands = [(x, z) for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1)
             if (x - cx) ** 2 + (z - cz) ** 2 <= r * r and ctx.name_at(x, ly, z) == "moss_block" and ctx.name_at(x, ly + 1, z) == "air"
             and ctx.name_at(x, ly + 2, z) == "air"]
    cands.sort(key=lambda t: hash01(t[0], t[1], 111, seed))
    w = World(); n = 0
    for (x, z) in cands:
        if n >= int(p["count"]):
            break
        if any(abs(x - qx) + abs(z - qz) < 3 for qx, qz in [(k[0], k[2]) for k in w.cells]):
            continue
        w.put(x, ly + 1, z, "flowering_azalea" if hash01(x, z, 113, seed) < 0.6 else "pink_tulip")
        n += 1
    return w.canvas({"kind": "apiary", "count": n})


# ================================================================== bird lanterns

BIRDLANTERNS = {"under": None, "min_y": 245, "count": 6, "drop": [6, 10], "gap": 10, "seed": 0}


def build_birdlanterns(cfg: dict, donors=None) -> Canvas:
    """Chain + lantern strings from the underside of the sky object (solid cells with air below), spread out."""
    p = {**BIRDLANTERNS, **cfg}
    ctx = Ctx(p["under"])
    ys = np.arange(ctx.m.ids.shape[0])[:, None, None]
    obj = ctx.solid & (ys + ctx.oy >= int(p["min_y"]))
    below_air = np.zeros_like(obj); below_air[:-1] = ~ctx.solid[1:]
    faces = [(int(x + ctx.ox), int(y + ctx.oy), int(z + ctx.oz)) for y, z, x in np.argwhere(obj & np.roll(below_air, 0, axis=0)) if not ctx.solid[y - 1, z, x]]
    faces.sort(key=lambda t: hash01(t[0], t[2], 121, int(p["seed"])))
    w = World(); placed = []
    lo, hi = p["drop"]
    for (x, y, z) in faces:
        if len(placed) >= int(p["count"]):
            break
        if any(abs(x - qx) + abs(z - qz) < int(p["gap"]) for qx, qz in placed):
            continue
        d = lo + int(hash01(x, z, 123, int(p["seed"])) * (hi - lo + 1))
        if any(ctx.name_at(x, y - i, z) != "air" for i in range(1, d + 2)):
            continue
        for i in range(1, d + 1):
            w.put(x, y - i, z, "iron_chain", axis="y", waterlogged="false")
        w.put(x, y - d - 1, z, "lantern", hanging="true", waterlogged="false")
        placed.append((x, z))
    return w.canvas({"kind": "birdlanterns", "count": len(placed)})

# ================================================================== altar inside a hollow build

ALTAR = {"under": None, "box": None, "floor_y": 203, "door": {"side": "east", "z": None, "x": None, "width": 2, "height": 3},
         "aisle_width": 3, "inset": 3, "seed": 0}


def build_altar(cfg: dict, donors=None) -> Canvas:
    """Shrine inside a hollow statue: dug doorway (dig list in sidecar), slab aisle from the door, a 3x3
    stone-brick altar against the far wall with a soul lantern on a wall pillar, candles, flanking lanterns,
    a lectern facing the door, and soul lanterns hanging from the shell ceiling."""
    p = {**ALTAR, **cfg}
    ctx = Ctx(p["under"])
    x1, z1, x2, z2 = p["box"]; fy = int(p["floor_y"]); seed = int(p["seed"])
    interior = _interior(ctx, (x1, z1, x2, z2), fy + 2)
    if not interior:
        raise ValueError("no enclosed interior found in the box at floor_y+2")
    floor = {(x, z) for (x, z) in interior if ctx.name_at(x, fy, z) == "air" and ctx.name_at(x, fy - 1, z) not in ("air", "vine")}
    cx = round(sum(x for x, _ in floor) / len(floor)); cz = round(sum(z for _, z in floor) / len(floor))
    door, dig = _doorway(ctx, p["door"], (x1, z1, x2, z2), fy, interior)
    dx, dz = _door_dir(p["door"]["side"])                       # unit vector pointing INTO the room
    w = World()
    # altar 3x3 against the far wall (opposite the door), 2 in from the wall
    far = _far_point(floor, cx, cz, dx, dz)
    ax, az = far[0] - int(p["inset"]) * dx, far[1] - int(p["inset"]) * dz
    _altar_block(w, ctx, ax, az, fy, dx, dz, floor)
    # aisle from the door to the altar
    _aisle(w, ctx, door, (ax, az), fy, int(p["aisle_width"]), floor, seed)
    # ceiling soul lanterns
    _ceiling_lights(w, ctx, interior, fy, seed)
    return w.canvas({"kind": "altar", "interior_cells": len(interior), "floor_cells": len(floor), "altar_at": [ax, fy, az],
                     "door": door, "dig": [list(d) for d in dig]})


def _door_dir(side):
    return {"east": (-1, 0), "west": (1, 0), "south": (0, -1), "north": (0, 1)}[side]


def _interior(ctx: Ctx, box, y):
    """2-D flood from the box centre at height y, bounded by solid; empty if it leaks out of the box."""
    x1, z1, x2, z2 = box
    sx, sz = (x1 + x2) // 2, (z1 + z2) // 2
    seen, stack = set(), [(sx, sz)]
    while stack:
        x, z = stack.pop()
        if (x, z) in seen:
            continue
        if not (x1 <= x <= x2 and z1 <= z <= z2):
            return set()
        if ctx.name_at(x, y, z) not in ("air", "vine"):
            continue
        seen.add((x, z))
        stack += [(x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)]
    return seen


def _doorway(ctx: Ctx, d, box, fy, interior):
    """Cells to dig for a width x height opening through the wall on `side`, at the given z (E/W) or x (N/S)."""
    x1, z1, x2, z2 = box
    side, wdt, hgt = d["side"], int(d["width"]), int(d["height"])
    dig = []
    if side in ("east", "west"):
        zc = int(d["z"]); xs = range(x2, x1 - 1, -1) if side == "east" else range(x1, x2 + 1)
        # walk inward from the box edge until interior is reached; dig every solid on the way
        cols = [(x, z) for z in range(zc - wdt // 2, zc - wdt // 2 + wdt) for x in xs]
        stop = {}
        for (x, z) in cols:
            if (x, z) in interior:
                stop[z] = True
            if not stop.get(z):
                for y in range(fy, fy + hgt):
                    if ctx.name_at(x, y, z) not in ("air", "vine"):
                        dig.append((x, y, z, ctx.name_at(x, y, z)))
        inner = [(x, z) for (x, z) in cols if (x, z) in interior]
        door = inner[0] if inner else cols[-1]
    else:
        xc = int(d["x"]); zs = range(z2, z1 - 1, -1) if side == "south" else range(z1, z2 + 1)
        cols = [(x, z) for x in range(xc - wdt // 2, xc - wdt // 2 + wdt) for z in zs]
        stop = {}
        for (x, z) in cols:
            if (x, z) in interior:
                stop[x] = True
            if not stop.get(x):
                for y in range(fy, fy + hgt):
                    if ctx.name_at(x, y, z) not in ("air", "vine"):
                        dig.append((x, y, z, ctx.name_at(x, y, z)))
        inner = [(x, z) for (x, z) in cols if (x, z) in interior]
        door = inner[0] if inner else cols[-1]
    return list(door), dig


def _far_point(floor, cx, cz, dx, dz):
    return max(floor, key=lambda c: (c[0] - cx) * dx + (c[1] - cz) * dz)


def _altar_block(w, ctx, ax, az, fy, dx, dz, floor):
    S = lambda x, y, z, n, **pr: (w.put(x, y, z, n, **pr) if (x, z) in floor and ctx.name_at(x, y, z) == "air" else None)
    for ddx in (-1, 0, 1):
        for ddz in (-1, 0, 1):
            x, z = ax + ddx, az + ddz
            S(x, fy, z, "mossy_stone_bricks" if (ddx + ddz) % 2 else "stone_bricks")
    # centre pillar + soul lantern
    S(ax, fy + 1, az, "stone_brick_wall", up="true", north="none", south="none", east="none", west="none", waterlogged="false")
    S(ax, fy + 2, az, "stone_brick_wall", up="true", north="none", south="none", east="none", west="none", waterlogged="false")
    S(ax, fy + 3, az, "soul_lantern", hanging="false", waterlogged="false")
    # candles on the two front corners (toward the door), lanterns on posts at the back corners
    px, pz = -dz, dx                                             # perpendicular
    fx, fz = ax - dx, az - dz                                    # one step toward the door
    for s in (-1, 1):
        S(fx + s * px, fy + 1, fz + s * pz, "candle", candles="3", lit="true", waterlogged="false")
        bx, bz = ax + dx + s * px, az + dz + s * pz
        S(bx, fy + 1, bz, "stone_brick_wall", up="true", north="none", south="none", east="none", west="none", waterlogged="false")
        S(bx, fy + 2, bz, "lantern", hanging="false", waterlogged="false")
    # lectern facing the door, two steps in front of the altar
    lx, lz = ax - 3 * dx, az - 3 * dz
    facing = {(-1, 0): "west", (1, 0): "east", (0, -1): "north", (0, 1): "south"}[(-dx, -dz)]
    S(lx, fy, lz, "lectern", facing=facing, has_book="false", powered="false")


def _aisle(w, ctx, door, altar, fy, width, floor, seed):
    (x0, z0), (x1, z1) = tuple(door), altar
    n = max(abs(x1 - x0), abs(z1 - z0), 1)
    px, pz = (0, 1) if abs(x1 - x0) >= abs(z1 - z0) else (1, 0)
    for i in range(n + 1):
        t = i / n
        cx, cz = round(x0 + (x1 - x0) * t), round(z0 + (z1 - z0) * t)
        for k in range(-(width // 2), width - width // 2):
            x, z = cx + k * px, cz + k * pz
            if (x, z) in floor and ctx.name_at(x, fy, z) == "air" and not w.has(x, fy, z):
                name = "mossy_stone_brick_slab" if hash01(x, z, 131, seed) < 0.4 else "stone_brick_slab"
                w.put(x, fy, z, name, type="bottom", waterlogged="false")


def _ceiling_lights(w, ctx, interior, fy, seed):
    """Three soul lanterns on chains from the highest interior ceiling above the room's middle."""
    cells = sorted(interior, key=lambda c: hash01(c[0], c[1], 137, seed))
    placed = 0
    for (x, z) in cells:
        if placed >= 3:
            break
        if any(abs(x - qx) + abs(z - qz) < 4 for (qx, qy, qz) in w.cells if w.cells[(qx, qy, qz)][0] == "soul_lantern" and qy > fy + 4):
            continue
        y = fy + 3
        while ctx.name_at(x, y + 1, z) == "air" and y < fy + 40:
            y += 1
        if ctx.name_at(x, y + 1, z) in ("air", "vine") or y - fy < 8:
            continue
        drop = 3 + int(hash01(x, z, 139, seed) * 3)
        for i in range(drop):
            w.put(x, y - i, z, "iron_chain", axis="y", waterlogged="false")
        w.put(x, y - drop, z, "soul_lantern", hanging="true", waterlogged="false")
        placed += 1
