"""Wall gecko — clings to a vertical face (island cliff / casing side).

Canvas: x = along the wall, y = up, z = out from the wall (z=0 touches it).
Head DOWN like a climbing gecko, tail curling up and to the side, four legs
splayed with 4 fanned toes each, bulbous eyes on the sides of the head.
Bright day-gecko palette: lime wool with green and orange spots, orange
eyes with black pupils, black mouth line. 3-4 deep, so it stands proud of
the wall. Paste with the z=0 face flush against the cliff.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

DEFAULTS = {"size": [30, 38, 6], "seed": 0}


def _taper_curve(c: Canvas, pts, r0, r1, blk, n=48):
    pts = [np.array(p, float) for p in pts]
    for i, t in enumerate(np.linspace(0, 1, n)):
        layer = pts
        while len(layer) > 1:
            layer = [(1 - t) * u + t * v for u, v in zip(layer, layer[1:])]
        q = layer[0]
        c.sphere(q[0], q[1], q[2], r0 + (r1 - r0) * t, blk)


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    SX, SY, SZ = p["size"]; seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {"skin": st("lime_wool"), "spot": st("green_wool"), "spot2": st("orange_wool"),
         "eye": st("orange_wool"), "pupil": st("black_wool"), "dark": st("black_wool"), "pad": st("moss_block"),
         "pale": st("light_gray_wool")}
    h = lambda *a: hash01(*a, seed)
    cx = SX / 2.0
    # ---- body: flat ellipsoid pressed to the wall (z 0..2)
    c.ellipsoid(cx, 19.0, 1.4, 3.9, 8.0, 2.6, S["skin"])
    # ---- head (down): wider, with a snout; bulbous eyes on the sides
    c.ellipsoid(cx, 9.0, 1.5, 4.4, 3.4, 2.5, S["skin"])
    c.ellipsoid(cx, 5.6, 1.4, 2.8, 2.0, 2.0, S["skin"])
    for sx in (-1, 1):
        c.sphere(cx + sx * 3.9, 10.2, 2.9, 1.75, S["eye"])
        ex = int(cx + sx * 3.8 - 0.5 + (0.5 if sx > 0 else 0))
        for y in (9, 10, 11):                                                # vertical slit pupil, 3 tall
            c.put(ex, y, 4, S["pupil"])
    for x in range(int(cx - 2), int(cx + 2)):                     # mouth line on the snout's outer face
        z = 3 if c.get(x, 4, 3) != 0 else 2 if c.get(x, 4, 2) != 0 else 1
        c.put(x, 4, z, S["dark"])
    for x in (int(cx - 3), int(cx + 2)):                          # grin: corners turn up
        z = 3 if c.get(x, 5, 3) != 0 else 2 if c.get(x, 5, 2) != 0 else 1
        if c.get(x, 5, z) != 0:
            c.put(x, 5, z, S["dark"])
    # ---- tail: from the top of the body, curling up and to the right, tapering
    _taper_curve(c, [(cx, 26.5, 1.4), (cx - 2.5, 31.5, 1.3), (cx + 3.5, 36, 1.2), (cx + 10, 33, 1.1), (cx + 11.5, 28, 1.0)],
                 1.7, 0.7, S["skin"])
    # ---- spots on the outer skin of body / head / tail only (legs come after, stay clean)
    for y in range(SY):
        for z in (1, 2, 3, 4):
            for x in range(SX):
                if c.get(x, y, z) == S["skin"] and (z == SZ - 1 or c.get(x, y, z + 1) == 0):
                    k = h(x, y, z, 7)
                    if k < 0.10:
                        c.put(x, y, z, S["spot2"])
                    elif k < 0.22:
                        c.put(x, y, z, S["spot"])
    for y in range(12, 27):                                        # darker dorsal stripe
        for x in (int(cx) - 1, int(cx)):
            for z in (3, 2, 1):
                if c.get(x, y, z) in (S["skin"], S["spot2"]) and c.get(x, y, z + 1) == 0:
                    if h(x, y, 9) < 0.7:
                        c.put(x, y, z, S["spot"])
                    break
    # ---- legs: two segments with a bent knee; front pair down-out, hind pair up-out; 4 toes + pads
    legs = [((cx - 3.2, 13.5), (cx - 7.5, 12.5), (cx - 10.0, 9.0)), ((cx + 3.2, 13.5), (cx + 7.5, 12.5), (cx + 10.0, 9.0)),
            ((cx - 3.2, 22.0), (cx - 7.5, 22.5), (cx - 10.0, 26.0)), ((cx + 3.2, 22.0), (cx + 7.5, 22.5), (cx + 10.0, 26.0))]
    for (x0, y0), (xk, yk), (x1, y1) in legs:
        c.line((x0, y0, 1.3), (xk, yk, 1.1), 1.05, S["skin"], replace=False)   # upper leg
        c.line((xk, yk, 1.1), (x1, y1, 1.0), 0.95, S["skin"], replace=False)   # lower leg
        d = np.array([x1 - xk, y1 - yk]); d /= np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        base = np.array([x1, y1])
        for k in (-1.5, -0.5, 0.5, 1.5):                                # toes fan around the foot
            tip = base + d * 2.6 + n * k * 1.5
            c.line((x1, y1, 1.0), (tip[0], tip[1], 1.0), 0.6, S["skin"], replace=False)
            for z in (0, 1, 2):                                         # pad: full-depth so it shows
                c.put(int(tip[0]), int(tip[1]), z, S["pad"])
    return c
