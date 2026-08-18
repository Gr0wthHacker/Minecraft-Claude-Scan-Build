"""A lake hanging in the void, and the fall that feeds it.

    lake: an elliptical basin - rock floor deepening toward the middle, a rim one course above the
          water so nothing can spill, a shore of gravel and moss, and water filled as SOURCE blocks
          so the surface is still rather than a permanent churn.

The fall is only its source block and a stone lip to spill from. Flowing water is not a placeable
state worth putting in a schematic: place the source and Minecraft draws the other sixty blocks for
you, and Litematica will not nag about cells that physics owns.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

LAKE = {
    "under": None,             # capture, so the basin can be checked against the void
    "center": None,            # world (x, z) - put it under where the fall lands
    "water_y": 100,            # the surface
    "depth": 3,                # water courses; the floor sits depth below the surface
    "rx": 14.0, "rz": 12.0,
    "wobble": 2.0,             # ragged outline, so it does not read as a machined bowl
    "rock": [("cobblestone", 0.30), ("mossy_cobblestone", 0.26), ("stone", 0.24),
             ("andesite", 0.12), ("mossy_stone_bricks", 0.08)],
    "shore": [("gravel", 0.45), ("moss_block", 0.35), ("cobblestone", 0.20)],
    "shore_width": 1.6,
    "lily": 0.04,              # lily pads on the surface
    "lichen": 0.14,            # glow lichen on the rim rock
    "lantern_reach": 7,        # nothing here sees sky: lanterns are the only light
    "spout": None,             # world (x, y, z) of the fall's source block
    "spout_lip": True,         # a little stone spillway around the source
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
DIRS4 = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))


def build_lake(cfg: dict, donors=None) -> Canvas:
    p = {**LAKE, **cfg}
    for k in ("center",):
        if p.get(k) is None:
            raise ValueError(f"lake needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    cx, cz = (int(v) for v in p["center"])
    wy, depth, seed = int(p["water_y"]), int(p["depth"]), int(p["seed"])
    rx, rz, wob = float(p["rx"]), float(p["rz"]), float(p["wobble"])

    w = World()
    inside, rim = _outline(cx, cz, rx, rz, wob, seed)
    _basin(w, inside, rim, cx, cz, rx, rz, wy, depth, p, seed)
    water = _fill(w, inside, wy, depth, p, seed)
    shore = _shore(w, inside, rim, cx, cz, rx, rz, wy, p, seed)
    lichen = _lichen(w, rim, wy, p, seed)
    lit = _lights(w, inside, rim, wy, p)
    spout = _spout(ctx, w, p)

    return w.canvas({"kind": "lake", "center": [cx, cz], "water_y": wy, "depth": depth,
                     "water_cells": water, "shore_cells": shore, "rim_cells": len(rim),
                     "lichen": lichen, "lanterns": lit, "spout": spout})


def _outline(cx, cz, rx, rz, wob, seed):
    """Cells inside the ragged ellipse, and the ring just outside them."""
    inside = set()
    for dx in range(-int(rx) - 3, int(rx) + 4):
        for dz in range(-int(rz) - 3, int(rz) + 4):
            d = ((dx / rx) ** 2 + (dz / rz) ** 2) ** 0.5
            edge = 1.0 + 0.09 * wob * (hash01(cx + dx, cz + dz, 11, seed) - 0.5)
            if d <= edge:
                inside.add((cx + dx, cz + dz))
    rim = {(x + dx, z + dz) for (x, z) in inside for _, dx, dz in DIRS4} - inside
    return inside, rim


def _basin(w: World, inside, rim, cx, cz, rx, rz, wy, depth, p, seed):
    """Floor that deepens toward the middle, and a wall a course above the water all the way round."""
    for (x, z) in inside:
        d = (((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2) ** 0.5
        # shallow at the edge, full depth in the middle - a bowl, not a box
        sink = max(1, int(round(depth * (1.0 - d ** 1.6))))
        floor = wy - sink
        for y in range(floor - 1, floor + 1):
            w.put(x, y, z, _rock(x, y, z, p, seed))
    for (x, z) in rim:
        for y in range(wy - depth - 1, wy + 2):
            w.put(x, y, z, _rock(x, y, z, p, seed))


def _fill(w: World, inside, wy, depth, p, seed) -> int:
    """Every water cell a SOURCE. A basin of flowing water never settles and looks wrong."""
    n = 0
    for (x, z) in inside:
        for y in range(wy, wy - depth, -1):
            if w.has(x, y, z):
                continue
            w.put(x, y, z, "water", level="0")
            n += 1
        if hash01(x, z, 19, seed) < p["lily"] and w.name(x, wy, z) == "water":
            w.put(x, wy + 1, z, "lily_pad")
    return n


def _shore(w: World, inside, rim, cx, cz, rx, rz, wy, p, seed) -> int:
    """Gravel and moss where the water meets the rock, so the edge is a beach not a kerb."""
    n = 0
    for (x, z) in inside:
        d = (((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2) ** 0.5
        if d < 1.0 - float(p["shore_width"]) / max(rx, rz):
            continue
        y = wy
        while y > wy - 6 and w.name(x, y, z) == "water":
            y -= 1
        if w.has(x, y, z):                              # the floor under the shallow edge
            w.put(x, y, z, _pick(p["shore"], x, y, z, seed))
            n += 1
    return n


def _lichen(w: World, rim, wy, p, seed) -> int:
    n = 0
    for (x, z) in rim:
        for y in (wy, wy + 1):
            if not w.has(x, y, z) or hash01(x, y, z, 23, seed) >= p["lichen"]:
                continue
            # lichen sits ON the rock face, so it needs the cell above free
            if w.has(x, y + 1, z):
                continue
            w.put(x, y + 1, z, "glow_lichen", down="true", up="false", north="false",
                  south="false", east="false", west="false", waterlogged="false")
            n += 1
            break
    return n


def _lights(w: World, inside, rim, wy, p) -> int:
    """Greedy cover on the rim: no daylight reaches this deep, so unlit means dark and spawning."""
    reach = int(p["lantern_reach"])
    if reach <= 0:
        return 0
    posts = sorted(c for c in rim if w.has(c[0], wy + 1, c[1]))
    need = set(inside) | set(rim)
    lit = 0
    while need and posts:
        best = max(posts, key=lambda c: sum(1 for d in need
                                            if abs(c[0] - d[0]) + abs(c[1] - d[1]) <= reach))
        covered = {d for d in need if abs(best[0] - d[0]) + abs(best[1] - d[1]) <= reach}
        if not covered:
            break
        if not w.has(best[0], wy + 2, best[1]):
            w.put(best[0], wy + 2, best[1], "lantern", hanging="false", waterlogged="false")
            lit += 1
        need -= covered
        posts.remove(best)
    return lit


def _spout(ctx, w: World, p):
    """The fall: one source block, and a lip for it to leave by. Physics draws the rest."""
    if not p.get("spout"):
        return None
    sx, sy, sz = (int(v) for v in p["spout"])
    if p["spout_lip"]:
        for _, dx, dz in DIRS4:
            if ctx is None or ctx.name_at(sx + dx, sy, sz + dz) in AIRY:
                w.put(sx + dx, sy, sz + dz, "mossy_cobblestone")
        # nothing under the source: the cell below has to stay open or the water cannot fall
    w.put(sx, sy, sz, "water", level="0")
    return [sx, sy, sz]


def _rock(x, y, z, p, seed) -> str:
    return _pick(p["rock"], x, y, z, seed)


def _pick(table, x, y, z, seed) -> str:
    h = hash01(x, y, z, 29, seed)
    acc = 0.0
    for name, weight in table:
        acc += weight
        if h < acc:
            return name
    return table[-1][0]
