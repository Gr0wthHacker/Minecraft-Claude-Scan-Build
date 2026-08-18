"""A workshop court on a platform: a laid floor, stations round the rim, balustrade and lanterns.

    atelier: takes whatever floor a platform actually has - ragged edges and all - and lays a RADIAL
             pattern on it: a medallion at the middle, concentric rings, eight spokes, and a rough
             mossy verge where the rock runs out. A radial pattern is the one that survives an
             irregular outline; a rectangular tile grid needs a rectangle, and a raft is not one.

Stations sit on the outer ring facing in, each with a cell to stand in. The palette is deliberately
narrow - four greys the island already contains - so the floor reads as one surface with figure in it
rather than as a pile of different blocks.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .interior import _settle_walls
from .vertical import Ctx, World

ATELIER = {
    "under": None,             # capture: the platform as it stands
    "center": None,            # world (x, z) the pattern radiates from
    "floor_y": None,           # the course the floor is laid IN (replaces what is there)
    "radius": 12,              # how far out to look for platform floor
    "headroom": 5,             # a cell only counts as floor if this many courses above are clear
    # four greys, light to dark. Ring parity alternates the first two; spokes take the third.
    "pale": "smooth_stone",
    "mid": "stone_bricks",
    "figure": "cracked_stone_bricks",
    "verge": "mossy_cobblestone",
    "medallion": "chiseled_stone_bricks",
    "spokes": 8,
    "spoke_width": 0.30,       # radians at r=1; narrows with radius so spokes stay one cell wide
    "verge_width": 1.2,        # cells of rough edging where the platform runs out
    "stations": ["anvil", "grindstone", "smithing_table", "stonecutter",
                 "loom", "cartography_table", "fletching_table", "cauldron"],
    "station_gap": 2,          # cells between stations along the rim
    "balustrade": "stone_brick_wall",
    "lantern_every": 5,
    "floor_lantern_reach": 6,  # no sky reaches this platform, so block light is the ONLY light: stand
                               # lanterns on the verge until every floor cell is within this of one
    "planters": 0.10,          # share of verge cells that take moss carpet or azalea instead
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
DIRS4 = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))
# stations that take a horizontal facing; the rest have no orientation worth setting
FACING = {"anvil", "grindstone", "stonecutter", "loom", "barrel", "lectern"}
INWARD = {"east": "west", "west": "east", "south": "north", "north": "south"}


def build_atelier(cfg: dict, donors=None) -> Canvas:
    p = {**ATELIER, **cfg}
    for k in ("center", "floor_y"):
        if p.get(k) is None:
            raise ValueError(f"atelier needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    cx, cz = (int(v) for v in p["center"])
    fy, seed = int(p["floor_y"]), int(p["seed"])

    cells = _platform(ctx, cx, cz, fy, int(p["radius"]), int(p["headroom"]))
    cells = _connected(cells, cx, cz)
    if not cells:
        raise ValueError("no open platform floor found - check center, floor_y and headroom")
    # radius from the CONTIGUOUS floor. Taking it from every open cell lets a couple of far-flung
    # fragments stretch the rings, and the pattern scatters instead of reading as one floor.
    rmax = max(math.hypot(x - cx, z - cz) for x, z in cells)
    w, dig = World(), []
    laid = _floor(ctx, w, dig, cells, cx, cz, fy, rmax, p, seed)
    stations = _stations(ctx, w, cells, cx, cz, fy, p)
    rail = _balustrade(ctx, w, cells, fy, p)
    lit = _lanterns(ctx, w, cells, cx, cz, fy, p)
    lit += _floor_lights(ctx, w, cells, fy, p)
    _settle_walls(w, ctx or _NoCtx(), p["balustrade"])

    return w.canvas({"kind": "atelier", "center": [cx, cz], "floor_y": fy,
                     "floor_cells": laid, "stations": stations, "balustrade": rail,
                     "lanterns": lit, "radius_used": round(rmax, 1),
                     "dig": [list(d) for d in dig]})


def _platform(ctx, cx, cz, fy, radius, headroom) -> list:
    """Floor cells that are solid at fy and open above - the space you can actually stand in."""
    if ctx is None:
        return [(cx + dx, cz + dz) for dx in range(-radius, radius + 1)
                for dz in range(-radius, radius + 1) if math.hypot(dx, dz) <= radius]
    out = []
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            x, z = cx + dx, cz + dz
            if ctx.name_at(x, fy, z) in AIRY:
                continue
            if any(ctx.name_at(x, fy + 1 + k, z) not in AIRY for k in range(headroom)):
                continue
            out.append((x, z))
    return out


def _connected(cells, cx, cz) -> list:
    """Only the run of floor you can walk to from the middle - fragments elsewhere are left alone."""
    S = set(cells)
    if (cx, cz) not in S:
        near = min(S, key=lambda c: math.hypot(c[0] - cx, c[1] - cz), default=None)
        if near is None:
            return []
        start = near
    else:
        start = (cx, cz)
    seen, stack = {start}, [start]
    while stack:
        x, z = stack.pop()
        for _, dx, dz in DIRS4:
            n = (x + dx, z + dz)
            if n in S and n not in seen:
                seen.add(n)
                stack.append(n)
    return sorted(seen)


def _floor(ctx, w: World, dig: list, cells, cx, cz, fy, rmax, p, seed) -> int:
    """Rings, spokes, medallion, verge. One block per cell, all full blocks so the floor stays flat."""
    spokes, sw = int(p["spokes"]), float(p["spoke_width"])
    n = 0
    for (x, z) in cells:
        dx, dz = x - cx, z - cz
        r = math.hypot(dx, dz)
        if r <= 0.6:
            name = p["medallion"]
        elif r >= rmax - float(p["verge_width"]):
            name = p["verge"]
            if hash01(x, z, 41, seed) < p["planters"]:
                _put(w, dig, ctx, x, fy, z, name)
                w.put(x, fy + 1, z, "moss_carpet" if hash01(x, z, 43, seed) < 0.6 else "azalea")
                n += 1
                continue
        else:
            a = math.atan2(dz, dx) % (2 * math.pi / spokes)
            half = min(math.pi / spokes, sw / max(1.0, r))
            on_spoke = a < half or a > (2 * math.pi / spokes) - half
            name = p["figure"] if on_spoke else (p["pale"] if int(r) % 2 == 0 else p["mid"])
        if _put(w, dig, ctx, x, fy, z, name):
            n += 1
    return n


def _stations(ctx, w: World, cells, cx, cz, fy, p) -> list:
    """Stations on the outer ring, facing the middle, each with a free cell to stand in."""
    S = set(cells)
    rim = sorted((c for c in cells
                  if any((c[0] + dx, c[1] + dz) not in S for _, dx, dz in DIRS4)),
                 key=lambda c: math.atan2(c[1] - cz, c[0] - cx))
    placed, used = [], []
    gap = int(p["station_gap"])
    for name in p["stations"]:
        for (x, z) in rim:
            if any(abs(x - a) + abs(z - b) <= gap for a, b in used):
                continue
            if w.has(x, fy + 1, z) or (ctx is not None and ctx.name_at(x, fy + 1, z) not in AIRY):
                continue
            face = _inward(x, z, cx, cz)
            sx, sz = x - _off(face)[0], z - _off(face)[1]
            if (sx, sz) not in S:                       # nowhere to stand and use it
                continue
            props = {"facing": face} if name in FACING else {}
            if name == "grindstone":
                props["face"] = "floor"
            w.put(x, fy + 1, z, name, **props)
            placed.append([name, x, fy + 1, z])
            used.append((x, z))
            break
    return placed


def _inward(x, z, cx, cz) -> str:
    dx, dz = cx - x, cz - z
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def _off(face) -> tuple[int, int]:
    return {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}[face]


def _balustrade(ctx, w: World, cells, fy, p) -> int:
    """A wall course where the platform drops away, so the court has an edge and you cannot walk off."""
    if not p["balustrade"]:
        return 0
    S = set(cells)
    n = 0
    for (x, z) in cells:
        for _, dx, dz in DIRS4:
            nx, nz = x + dx, z + dz
            if (nx, nz) in S:
                continue
            if ctx is not None and ctx.name_at(nx, fy, nz) not in AIRY:
                continue                                # rock backs it: not an edge
            if w.has(nx, fy + 1, nz) or (ctx is not None and ctx.name_at(nx, fy + 1, nz) not in AIRY):
                continue
            if ctx is not None and ctx.name_at(nx, fy, nz) in AIRY:
                w.put(nx, fy, nz, p["verge"])           # a lip to stand the wall on
            w.put(nx, fy + 1, nz, p["balustrade"], up="true", north="none", south="none",
                  east="none", west="none", waterlogged="false")
            n += 1
            break
    return n


def _lanterns(ctx, w: World, cells, cx, cz, fy, p) -> int:
    """Lanterns on posts along the balustrade - the only light this space gets."""
    if not int(p["lantern_every"]):
        return 0
    posts = sorted((c for c in w.cells if w.name(*c) == p["balustrade"]),
                   key=lambda c: math.atan2(c[2] - cz, c[0] - cx))
    n = 0
    for i, (x, y, z) in enumerate(posts):
        if i % int(p["lantern_every"]):
            continue
        if w.has(x, y + 1, z) or (ctx is not None and ctx.name_at(x, y + 1, z) not in AIRY):
            continue
        w.put(x, y + 1, z, "lantern", hanging="false", waterlogged="false")
        n += 1
    return n


def _floor_lights(ctx, w: World, cells, fy, p) -> int:
    """Greedy cover: light the least-covered floor cell, repeat, until nothing is left in the dark.

    Scattering lanterns by eye leaves pockets at light 0, and this space has no daylight at all - the
    same mistake that let the sky-well pond freeze, in the other direction."""
    reach = int(p["floor_lantern_reach"])
    if reach <= 0:
        return 0
    free = [c for c in cells if not w.has(c[0], fy + 1, c[1])]
    need = set(cells)
    lit = 0
    while need and free:
        best = max(free, key=lambda c: sum(1 for d in need if abs(c[0] - d[0]) + abs(c[1] - d[1]) <= reach))
        covered = {d for d in need if abs(best[0] - d[0]) + abs(best[1] - d[1]) <= reach}
        if not covered:
            break
        if ctx is None or ctx.name_at(best[0], fy + 1, best[1]) in AIRY:
            w.put(best[0], fy + 1, best[1], "lantern", hanging="false", waterlogged="false")
            lit += 1
        need -= covered
        free.remove(best)
    return lit


def _put(w: World, dig: list, ctx, x, y, z, name) -> bool:
    """Lay a floor block, recording what has to come out first."""
    if w.has(x, y, z):
        return False
    if ctx is not None:
        here = ctx.name_at(x, y, z)
        # Lay the block even when the world already has the right one. Skipping made the design a
        # DELTA, which left lanterns standing on cells the design did not contain - and `progress`
        # counts a matching cell as built anyway, so nothing is lost by describing the whole floor.
        if here not in AIRY and here != name:
            dig.append((int(x), int(y), int(z)))
    w.put(x, y, z, name)
    return True


class _NoCtx:
    def name_at(self, x, y, z) -> str:
        return "air"
