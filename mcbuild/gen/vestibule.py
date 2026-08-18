"""The entry: a threshold at a stair head, and a paved route from it to somewhere worth going.

    vestibule: a small medallion round the arrival, lantern posts flanking it, and a spine of paving
               running to a target - laid IN the floor course, so it never puts a step across a room
               you have to walk and cart things through.

It shares the atelier's four greys deliberately. The court below and the workshop above should read
as the same hand, and a floor is the cheapest place to say so.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .interior import _settle_walls
from .vertical import Ctx, World

VESTIBULE = {
    "under": None,
    "head": None,              # world (x, z) of the stair head you are arriving at
    "to": None,                # world (x, z) the spine runs to
    "floor_y": 194,            # the course paving replaces
    "threshold": 4,            # radius of the medallion round the head
    "spine": 3,                # paving width
    "pale": "smooth_stone",
    "mid": "stone_bricks",
    "figure": "cracked_stone_bricks",
    "verge": "mossy_stone_bricks",
    "post": "stone_brick_wall",
    "posts": 4,                # lantern posts flanking the threshold
    "clear_names": ["chest", "trapped_chest", "barrel"],   # what the entry needs cleared to exist
    "clear_box": None,         # world [x1,z1,x2,z2] the clearing is allowed in
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
DIRS4 = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))


def build_vestibule(cfg: dict, donors=None) -> Canvas:
    p = {**VESTIBULE, **cfg}
    for k in ("head", "to"):
        if p.get(k) is None:
            raise ValueError(f"vestibule needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    hx, hz = (int(v) for v in p["head"])
    tx, tz = (int(v) for v in p["to"])
    fy, seed = int(p["floor_y"]), int(p["seed"])

    w, dig = World(), []
    _clear(ctx, dig, p, fy)
    route = _route((hx, hz), (tx, tz), int(p["spine"]))
    thresh = _threshold(hx, hz, int(p["threshold"]))
    laid = _pave(ctx, w, dig, thresh, route, hx, hz, fy, p, seed)
    posts = _posts(ctx, w, hx, hz, fy, int(p["threshold"]), p, dig)

    return w.canvas({"kind": "vestibule", "head": [hx, hz], "to": [tx, tz], "floor_y": fy,
                     "paved": laid, "posts": posts, "route_cells": len(route),
                     "dig": [list(d) for d in dig]})


def _clear(ctx, dig: list, p, fy: int):
    """Containers in the clear box go on the dig list: the entry cannot exist while they stand."""
    box = p.get("clear_box")
    if ctx is None or not box:
        return
    x1, z1, x2, z2 = (int(v) for v in box)
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for z in range(min(z1, z2), max(z1, z2) + 1):
            for y in range(fy + 1, fy + 7):
                n = ctx.name_at(x, y, z)
                if any(k in n for k in p["clear_names"]):
                    dig.append((x, y, z))


def _route(a, b, width: int) -> set:
    """An L from a to b, `width` wide - one leg in x, one in z."""
    (x0, z0), (x1, z1) = a, b
    half = max(0, width // 2)
    out = set()
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for d in range(-half, half + 1):
            out.add((x, z0 + d))
    for z in range(min(z0, z1), max(z0, z1) + 1):
        for d in range(-half, half + 1):
            out.add((x1 + d, z))
    return out


def _threshold(hx, hz, r) -> set:
    return {(hx + dx, hz + dz) for dx in range(-r, r + 1) for dz in range(-r, r + 1)
            if math.hypot(dx, dz) <= r + 0.4}


def _pave(ctx, w: World, dig: list, thresh: set, route: set, hx, hz, fy, p, seed) -> int:
    """Rings round the arrival, a plain spine beyond it. The figure marks where you come UP."""
    n = 0
    for (x, z) in sorted(thresh | route):
        if ctx is not None and ctx.name_at(x, fy, z) in AIRY:
            continue                                     # no deck floor here to pave
        if ctx is not None and ctx.name_at(x, fy + 1, z) not in AIRY:
            continue                                     # something is standing on it
        r = math.hypot(x - hx, z - hz)
        if (x, z) in thresh:
            if r <= 1.4:
                name = p["figure"]                       # the mouth of the stair
            elif r >= float(p["threshold"]) - 0.6:
                name = p["verge"]
            else:
                name = p["pale"] if int(r) % 2 == 0 else p["mid"]
        else:
            name = p["mid"] if hash01(x, z, 17, seed) < 0.72 else p["pale"]
        if _put(w, dig, ctx, x, fy, z, name):
            n += 1
    return n


def _posts(ctx, w: World, hx, hz, fy, r, p, dig) -> int:
    """Lantern posts at the four corners of the threshold, so the arrival is lit and framed."""
    n = 0
    for dx, dz in ((r, r), (r, -r), (-r, r), (-r, -r)):
        x, z = hx + dx, hz + dz
        # a cell already on the dig list is going anyway, so it does not block a post
        going = {(a, b) for (a, _y, b) in dig}
        blocked = ctx is not None and (
            ctx.name_at(x, fy, z) in AIRY
            or (ctx.name_at(x, fy + 1, z) not in AIRY and (x, z) not in going)
            or (ctx.name_at(x, fy + 2, z) not in AIRY and (x, z) not in going))
        if blocked:
            continue
        if n >= int(p["posts"]):
            break
        w.put(x, fy + 1, z, p["post"], up="true", north="none", south="none",
              east="none", west="none", waterlogged="false")
        w.put(x, fy + 2, z, "lantern", hanging="false", waterlogged="false")
        n += 1
    _settle_walls(w, ctx or _NoCtx(), p["post"])
    return n


def _put(w: World, dig: list, ctx, x, y, z, name) -> bool:
    if w.has(x, y, z):
        return False
    if ctx is not None:
        here = ctx.name_at(x, y, z)
        if here not in AIRY and here != name and (x, y, z) not in dig:
            dig.append((int(x), int(y), int(z)))
    w.put(x, y, z, name)
    return True


class _NoCtx:
    def name_at(self, x, y, z) -> str:
        return "air"
