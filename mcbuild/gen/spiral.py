"""A helical stair wound around a vertical design (the taproot).

Modelled on a reference build Jack supplied. Two things that make it work, both of which I got wrong
on my own:

1. It is built ONLY from slabs, alternating `bottom` (surface y+0.5) and `top` (y+1.0), so every
   course gives two half-steps and the rise is 0.5 a tread. Slabs carry no facing and no shape, so a
   curve costs nothing - stairs, by contrast, have their `shape` recomputed by the game from their
   neighbours and silently merge into corner pieces wherever the path turns.

2. A tread is a radial SPOKE three or four cells wide, not a single cell. That is what sets the
   pitch: consecutive spokes need only touch at the INNER edge, so the angular step is 1/inner_radius
   and the outer end just makes the tread wide. Treating each tread as one cell at a fixed radius is
   what limited the earlier attempt to 0.6 of a lap.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .interior import _settle_walls
from .vertical import Ctx, World, load_capture

SPIRAL = {
    "under": None,             # capture, for collision checks
    "around": None,            # design .litematic to wrap (its radius per course drives the taper)
    "center": None,            # world (x, z); defaults to the wrapped design's centre
    "y0": None, "y1": None,    # first and last course
    "clearance": 2,            # inner edge sits this far outside the wrapped design
    "min_radius": 3.0,
    "width": 4,                # tread depth, measured outward from the inner edge
    "start_angle": 0.0,
    "direction": 1,            # +1 anticlockwise, -1 clockwise
    "slab": "stone_brick_slab",
    "slab_alt": "mossy_stone_brick_slab",
    "alt_rate": 0.35,          # share of treads in the second slab, so it is not one flat tone
    "rail": "stone_brick_wall",
    "lantern_every": 12,       # a lantern on the rail every N treads; 0 for none
    "seed": 0,
}

DIRS4 = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))


def build_spiral(cfg: dict, donors=None) -> Canvas:
    p = {**SPIRAL, **cfg}
    ctx = Ctx(p["under"]) if p.get("under") else None
    prof, (cx, cz), (ry0, ry1) = _target(p)
    y0 = int(p["y0"]) if p["y0"] is not None else ry0
    y1 = int(p["y1"]) if p["y1"] is not None else ry1
    if y1 <= y0:
        raise ValueError(f"spiral needs y1 > y0 (got {y0}..{y1})")
    prof = _smooth(prof, float(p["clearance"]), float(p["min_radius"]))

    w = World()
    spin = 1 if int(p["direction"]) >= 0 else -1
    theta = float(p["start_angle"])
    width, seed = int(p["width"]), int(p["seed"])
    steps = (y1 - y0 + 1) * 2                          # two half-steps to a course
    treads, laps = [], 0.0
    for k in range(steps):
        y = y0 + k // 2
        low = (k % 2) == 0                             # bottom slab, then top slab, then up a course
        r_in = prof.get(y) or float(p["min_radius"])
        d = spin / max(1.0, r_in)                      # one cell of arc at the inner edge
        cells = _spoke(cx, cz, theta, theta + d, r_in, r_in + width)
        for (x, z) in cells:
            name = p["slab_alt"] if hash01(x, z, 19, seed) < p["alt_rate"] else p["slab"]
            w.put(x, y, z, name, type="bottom" if low else "top", waterlogged="false")
        if cells:
            treads.append([cells[0][0], y, cells[0][1]])
        theta += d
        laps += abs(d) / (2 * math.pi)

    rails = _rails(w, ctx, cx, cz, prof, y0, y1, width, p, seed)
    return w.canvas({"kind": "spiral", "center": [cx, cz], "y0": y0, "y1": y1,
                     "treads": len(treads), "turns": round(laps, 2), "rails": rails,
                     "width": width})


def _spoke(cx: int, cz: int, t0: float, t1: float, r_in: float, r_out: float) -> list:
    """Every cell in the WEDGE between two angles, across the tread's radial band.

    A single radial line leaves holes: the angular step is one cell of arc at the INNER edge, so by
    the outer edge consecutive treads are two or more cells apart. Filling the wedge makes each tread
    a compact patch that shares an edge with the next, which is how the reference build reads solid."""
    lo, hi = (t0, t1) if t1 >= t0 else (t1, t0)
    span = hi - lo
    rr = int(math.ceil(r_out)) + 1
    out = []
    for dx in range(-rr, rr + 1):
        for dz in range(-rr, rr + 1):
            r = math.hypot(dx, dz)
            if not (r_in - 0.5 <= r <= r_out + 0.5):
                continue
            a = math.atan2(dz, dx)
            # bring the cell's angle into [lo, lo + 2pi) so the comparison survives wraparound
            while a < lo:
                a += 2 * math.pi
            if a - lo <= span:
                out.append((cx + dx, cz + dz))
    out.sort(key=lambda c: math.hypot(c[0] - cx, c[1] - cz))
    return out


def _bridge(a, b) -> list:
    """Face-adjacent cells from a to b, exclusive of both ends."""
    (x0, z0), (x1, z1) = a, b
    out, x, z = [], x0, z0
    while (x, z) != (x1, z1):
        if x != x1:
            x += 1 if x1 > x else -1
        elif z != z1:
            z += 1 if z1 > z else -1
        if (x, z) != (x1, z1):
            out.append((x, z))
    return out


def _rails(w: World, ctx, cx: int, cz: int, prof: dict, y0: int, y1: int, width: int,
           p: dict, seed: int) -> int:
    """A wall on the outer lip, one course above whatever tread is under it, plus the odd lantern."""
    n = 0
    tread_cells = {(x, y, z) for (x, y, z) in w.cells}
    for (x, y, z) in sorted(tread_cells):
        r = math.hypot(x - cx, z - cz)
        r_in = prof.get(y) or float(p["min_radius"])
        if r < r_in + width - 0.7:                     # only the outermost ring of each tread
            continue
        if (x, y + 1, z) in tread_cells or w.has(x, y + 1, z):
            continue
        if ctx is not None and ctx.name_at(x, y + 1, z) not in ("air", "cave_air", "void_air", "vine"):
            continue
        w.put(x, y + 1, z, p["rail"], up="true", north="none", south="none",
              east="none", west="none", waterlogged="false")
        n += 1
    if p["lantern_every"]:
        posts = [c for c in sorted(w.cells) if w.name(*c) == p["rail"]]
        for i, (x, y, z) in enumerate(posts):
            if i % int(p["lantern_every"]) == 0 and not w.has(x, y + 1, z):
                w.put(x, y + 1, z, "lantern", hanging="false", waterlogged="false")
    _settle_walls(w, ctx or _NoCtx(), p["rail"])
    return n


# ------------------------------------------------------------------ the thing being wrapped

def _target(p) -> tuple[dict, tuple[int, int], tuple[int, int]]:
    """Max radius per course of the wrapped design, plus its centre and vertical extent."""
    if not p.get("around"):
        if not p.get("center") or p["y0"] is None or p["y1"] is None:
            raise ValueError("spiral needs params.around, or an explicit center + y0 + y1")
        cx, cz = (int(v) for v in p["center"])
        return {}, (cx, cz), (int(p["y0"]), int(p["y1"]))
    import numpy as np
    m, (ox, oy, oz) = load_capture(p["around"])
    ys, zs, xs = np.where(m.ids > 0)
    if p.get("center"):
        cx, cz = (int(v) for v in p["center"])
    else:
        cx, cz = int(round(xs.mean())) + ox, int(round(zs.mean())) + oz
    prof: dict[int, float] = {}
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        Y = y + oy
        r = math.hypot(x + ox - cx, z + oz - cz)
        if r > prof.get(Y, -1.0):
            prof[Y] = r
    return prof, (cx, cz), (min(prof), max(prof))


def _smooth(prof: dict, clearance: float, min_r: float) -> dict:
    """A monotone, gently growing radius.

    The raw profile of the taproot jumps - 2.2 to 4.0 in one course - and a helix that widens that
    fast folds back over the course below it, burying treads. Take a running maximum so the stair
    never narrows, then cap how fast it may grow."""
    if not prof:
        return prof
    out, run, prev = {}, 0.0, None
    for y in sorted(prof):
        run = max(run, prof[y])
        want = max(min_r, run + clearance)
        if prev is not None:
            want = min(want, prev + 0.34)               # at most a third of a block wider per course
        out[y] = want
        prev = want
    return out


# ------------------------------------------------------------------ pieces

class _NoCtx:
    """Stand-in when no capture is given: nothing exists, so walls only see their own neighbours."""

    def name_at(self, x, y, z) -> str:
        return "air"
