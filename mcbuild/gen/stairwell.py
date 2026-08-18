"""The shaft that joins something below the island to the deck above it.

    stairwell: a cased shaft with a slab spiral inside, punched through the deck floor, finished with
               a kerb and railing around the opening so the hole reads as a stair head rather than a
               place to fall down.

Same slab technique as gen/spiral: bottom slab then top slab, half a block a tread, no facing and no
shape to go wrong. The cells it has to cut - the deck floor, any skin - go into the dig list.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .interior import _settle_walls
from .vertical import Ctx, World

STAIRWELL = {
    "under": None,             # capture: what is really there, so the dig list is honest
    "center": None,            # world (x, z) of the shaft's middle
    "radius": 1,               # 1 gives a 3x3 shaft
    "y_bottom": None,          # surface you arrive from below
    "y_top": None,             # surface you step off onto at the top
    "start_angle": 0.0,
    "direction": 1,
    "slab": "stone_brick_slab",
    "slab_alt": "mossy_stone_brick_slab",
    "alt_rate": 0.3,
    "casing": "stone_bricks",  # shaft wall; null to leave the shaft open
    "entry_dir": None,         # side the lower stair arrives from: north/south/east/west. The casing
                               # leaves a doorway there - without it the shaft walls off its own
                               # approach and the climb stops at the bottom.
    "entry_high": 3,           # how many courses of that doorway to leave open
    "kerb": "stone_brick_slab",   # a lip around the opening at deck level
    "rail": "stone_brick_wall",   # railing around the opening; null for none
    "lanterns": 3,
    "apron": 0,                # cells of foyer paving beyond the kerb at deck level; 0 for none
    "apron_carpet": 0.42,      # share of apron cells carpeted - laid flat so it never trips the walk
    "apron_posts": 4,          # fence-and-lantern posts around the apron
    "keep_boxes": [],          # world [x1,y1,z1,x2,y2,z2]: the foyer never reaches in here
    "container_clear": 3,      # cells of clearance around ANY container, furnace or workbench found in
                               # the capture - enough to stand and work. Derived rather than configured:
                               # storage moves, and a hand-written box goes stale the moment it does.
    "cut_names": ["stone_bricks", "moss_block", "mossy_stone_bricks", "cobblestone", "stone"],
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
DIRS4 = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))


def build_stairwell(cfg: dict, donors=None) -> Canvas:
    p = {**STAIRWELL, **cfg}
    for k in ("center", "y_bottom", "y_top"):
        if p.get(k) is None:
            raise ValueError(f"stairwell needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    cx, cz = (int(v) for v in p["center"])
    yb, yt = int(p["y_bottom"]), int(p["y_top"])
    r, seed = int(p["radius"]), int(p["seed"])
    if yt <= yb:
        raise ValueError(f"stairwell needs y_top > y_bottom (got {yb}..{yt})")

    w, dig = World(), []
    shaft = [(cx + dx, cz + dz) for dx in range(-r, r + 1) for dz in range(-r, r + 1)]
    _cut(ctx, dig, shaft, yb, yt, p)
    treads = _spiral(w, cx, cz, yb, yt, r, p, seed)
    if p["casing"]:
        _case(ctx, w, dig, cx, cz, yb, yt, r, p)
    _head(ctx, w, dig, cx, cz, yt, r, p, seed)
    if int(p["apron"]):
        _apron(ctx, w, cx, cz, yt, r, p, seed, _containers(ctx, cx, cz, yt, p))
    _settle_walls(w, ctx or _NoCtx(), p["rail"] or "stone_brick_wall")

    return w.canvas({"kind": "stairwell", "center": [cx, cz], "y_bottom": yb, "y_top": yt,
                     "treads": treads, "dig": [list(d) for d in dig]})


def _cut(ctx, dig, shaft, yb: int, yt: int, p):
    """Everything solid inside the shaft has to come out, and it goes in the dig list by name so you
    can see what you are breaking before you break it."""
    if ctx is None:
        return
    for (x, z) in shaft:
        for y in range(yb, yt + 2):
            n = ctx.name_at(x, y, z)
            if n not in AIRY and n in p["cut_names"]:
                dig.append((x, y, z))


def _spiral(w: World, cx: int, cz: int, yb: int, yt: int, r: int, p, seed: int) -> int:
    """Half a block a tread around the shaft wall, leaving the middle open as a newel."""
    steps = (yt - yb) * 2
    theta = float(p["start_angle"])
    spin = 1 if int(p["direction"]) >= 0 else -1
    n = 0
    for k in range(steps):
        y = yb + k // 2
        low = (k % 2) == 0
        d = spin / max(1.0, float(r))
        for (x, z) in _wedge(cx, cz, theta, theta + d, r):
            name = p["slab_alt"] if hash01(x, z, 23, seed) < p["alt_rate"] else p["slab"]
            w.put(x, y, z, name, type="bottom" if low else "top", waterlogged="false")
            n += 1
        theta += d
    return n


def _wedge(cx: int, cz: int, t0: float, t1: float, r: int) -> list:
    """Ring cells between two angles - the middle cell is left out, it is the newel."""
    lo, hi = (t0, t1) if t1 >= t0 else (t1, t0)
    span = hi - lo
    out = []
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            if dx == 0 and dz == 0:
                continue
            a = math.atan2(dz, dx)
            while a < lo:
                a += 2 * math.pi
            if a - lo <= span:
                out.append((cx + dx, cz + dz))
    return out


def _case(ctx, w: World, dig, cx: int, cz: int, yb: int, yt: int, r: int, p):
    """A one-block wall around the shaft, only where the world is open - never into the island.

    Stops one below the top: at deck level the shaft opens into the room, and the kerb and railing
    take over. Casing all the way up would wall the stair head off from the workshop."""
    for y in range(yb, yt):
        for dx in range(-r - 1, r + 2):
            for dz in range(-r - 1, r + 2):
                if max(abs(dx), abs(dz)) != r + 1:
                    continue
                x, z = cx + dx, cz + dz
                if _is_doorway(dx, dz, y, yb, p):
                    continue
                if w.has(x, y, z) or (ctx is not None and ctx.name_at(x, y, z) not in AIRY):
                    continue
                w.put(x, y, z, p["casing"])


def _is_doorway(dx: int, dz: int, y: int, yb: int, p) -> bool:
    """The opening the lower stair walks in through."""
    d = p.get("entry_dir")
    if not d or y >= yb + int(p["entry_high"]):
        return False
    return {"east": dx > 0, "west": dx < 0, "south": dz > 0, "north": dz < 0}[d]


def _head(ctx, w: World, dig, cx: int, cz: int, yt: int, r: int, p, seed: int):
    """The stair head at deck level: a kerb ring, a railing on it, and a gap to walk in through."""
    ring = [(cx + dx, cz + dz) for dx in range(-r - 1, r + 2) for dz in range(-r - 1, r + 2)
            if max(abs(dx), abs(dz)) == r + 1]
    gap = max(ring, key=lambda c: (c[1] - cz, c[0] - cx))     # leave one side open as the doorway
    lit = 0
    for (x, z) in ring:
        if (x, z) == gap or (ctx is not None and ctx.name_at(x, yt, z) not in AIRY and not w.has(x, yt, z)):
            continue
        if not w.has(x, yt, z):
            w.put(x, yt, z, p["kerb"], type="bottom", waterlogged="false")
        if not p["rail"] or w.has(x, yt + 1, z):
            continue
        if ctx is not None and ctx.name_at(x, yt + 1, z) not in AIRY:
            continue
        if lit < int(p["lanterns"]) and hash01(x, z, 29, seed) < 0.4:
            w.put(x, yt + 1, z, "lantern", hanging="false", waterlogged="false")
            lit += 1
        else:
            w.put(x, yt + 1, z, p["rail"], up="true", north="none", south="none",
                  east="none", west="none", waterlogged="false")


def _containers(ctx, cx: int, cz: int, yt: int, p) -> set:
    """Cells within `container_clear` of a chest, barrel or furnace in the capture.

    Read off the world instead of listed in the config: the storage wall is what it is on the day you
    generate, and a hand-written box is wrong as soon as you move a chest."""
    if ctx is None or not int(p["container_clear"]):
        return set()
    c = int(p["container_clear"])
    reach = 12 + c
    out = set()
    for x in range(cx - reach, cx + reach + 1):
        for z in range(cz - reach, cz + reach + 1):
            for y in range(yt - 1, yt + 3):
                n = ctx.name_at(x, y, z)
                if any(k in n for k in ("chest", "barrel", "furnace", "shulker", "hopper",
                                        "crafting_table", "anvil", "smoker", "brewing", "lectern")):
                    for dx in range(-c, c + 1):
                        for dz in range(-c, c + 1):
                            out.add((x + dx, z + dz))
    return out


def _apron(ctx, w: World, cx: int, cz: int, yt: int, r: int, p, seed: int, near_storage: set):
    """A foyer around the stair head: carpet laid flat on the deck floor and a few lantern posts.

    Carpet rather than slabs - a slab course would put a half-block step across the whole workshop
    floor. Everything here is skipped where the world already holds something, so it dresses the gaps
    between the machines instead of burying them."""
    a = int(p["apron"])
    # a band hugging the head, not a square: at apron 5 the old test scattered carpet seven cells out
    ring = [(cx + dx, cz + dz) for dx in range(-r - 1 - a, r + 2 + a)
            for dz in range(-r - 1 - a, r + 2 + a)
            if r + 1 < max(abs(dx), abs(dz)) <= r + 1 + a]
    posts = 0
    for (x, z) in ring:
        if _off_limits(p, x, yt, z) or w.has(x, yt, z) or (x, z) in near_storage:
            continue
        if ctx is not None and (ctx.name_at(x, yt, z) not in AIRY or ctx.name_at(x, yt - 1, z) in AIRY):
            continue                                   # nothing to lay it on, or something already there
        h = hash01(x, z, 31, seed)
        corner = max(abs(x - cx), abs(z - cz)) == r + 1 + a and abs(abs(x - cx) - abs(z - cz)) <= 0
        if corner and posts < int(p["apron_posts"]) and not w.has(x, yt + 1, z):
            w.put(x, yt, z, "oak_fence", north="false", south="false", east="false", west="false",
                  waterlogged="false")
            w.put(x, yt + 1, z, "lantern", hanging="false", waterlogged="false")
            posts += 1
        elif h < p["apron_carpet"]:
            w.put(x, yt, z, "moss_carpet")


def _off_limits(p, x: int, y: int, z: int) -> bool:
    for x1, y1, z1, x2, y2, z2 in p["keep_boxes"]:
        if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2) and min(z1, z2) <= z <= max(z1, z2):
            return True
    return False


class _NoCtx:
    def name_at(self, x, y, z) -> str:
        return "air"
