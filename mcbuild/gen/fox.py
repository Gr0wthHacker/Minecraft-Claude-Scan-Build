"""Sitting fox statue, built at target scale (no downscale) on a mossy log stump."""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

DEFAULTS = {
    "size": [13, 28, 15], "stump_h": 3, "stump_r": 4.6,
    "body": "orange_wool", "white": "snow_block", "dark": "black_wool", "ear_inner": "red_wool",
    "seed": 0,
}


def build(cfg: dict, donors: list | None = None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    SX, SY, SZ = p["size"]
    CX = SX / 2.0 - 0.5
    G = int(p["stump_h"])
    c = Canvas(SX, SY, SZ, donors)
    O = c.state(p["body"]); W = c.state(p["white"]); K = c.state(p["dark"]); R = c.state(p["ear_inner"])
    LOG = c.state("oak_log", axis="y"); MOSS = c.state("moss_block"); CARPET = c.state("moss_carpet")
    cx = int(CX)
    # stump
    for y in range(G):
        for z in range(SZ):
            for x in range(SX):
                if ((x + 0.5 - CX - 0.5) ** 2 + (z + 0.5 - SZ / 2.0) ** 2) ** 0.5 <= p["stump_r"]:
                    c.ids[y, z, x] = LOG
    # body
    c.ellipsoid(CX + 0.5, G + 6.5, 7.0, 3.6, 6.5, 3.4, O)
    c.ellipsoid(CX + 0.5, G + 3.0, 7.5, 4.2, 3.2, 4.0, O)
    c.ellipsoid(CX + 0.5, G + 6.0, 9.6, 2.2, 4.4, 1.6, W)
    for y in range(G, G + 4):
        for x in (cx, cx + 1):
            for z in (9, 10):
                c.put(x, y, z, W)
    # neck + skull + face plane
    c.ellipsoid(CX + 0.5, G + 12.0, 7.4, 2.6, 2.0, 2.6, O)
    c.ellipsoid(CX + 0.5, G + 16.0, 7.2, 4.6, 3.8, 4.2, O)
    for y in range(G + 13, G + 20):
        for x in range(1, SX - 1):
            for z in range(10, SZ):
                c.put(x, y, z, 0)
        for x in range(2, SX - 2):
            if abs(x + 0.5 - CX - 0.5) <= 3.6:
                c.put(x, y, 9, O)
    # muzzle 3 forward, bridge, nose, recessed eyes, cheeks
    for y in (G + 14, G + 15, G + 16):
        for x in range(cx - 1, cx + 3):
            for z in (10, 11, 12):
                c.put(x, y, z, W)
    for y in (G + 15, G + 16):
        for x in (cx, cx + 1):
            for z in (10, 11, 12):
                c.put(x, y, z, O)
    for x in (cx, cx + 1):
        c.put(x, G + 14, 12, K)
    for y in (G + 17, G + 18):
        for x in (cx - 2, cx - 1, cx + 2, cx + 3):
            c.put(x, y, 9, 0)
            c.put(x, y, 8, K)
    for x in (cx - 3, cx - 2, cx + 3, cx + 4):
        for y in (G + 14, G + 15):
            if c.get(x, y, 9) == O:
                c.put(x, y, 9, W)
    # ears
    for side in (-1, 1):
        cols = [cx - 3, cx - 2, cx - 1] if side < 0 else [cx + 2, cx + 3, cx + 4]
        rows = [(G + 20, cols), (G + 21, cols), (G + 22, cols), (G + 23, [cols[1]])]
        for y, xs in rows:
            for x in xs:
                for z in (6, 7, 8):
                    c.put(x, y, z, K)
                if x == cols[1] and y <= G + 21:
                    c.put(x, y, 8, R)
    for x in range(cx - 3, cx + 5):
        for z in (6, 7, 8):
            if c.get(x, G + 19, z) == 0:
                c.put(x, G + 19, z, O)
    # tail on the right flank ending beside the right paw
    pts = [(CX + 3.5, G + 2.5, 5.0), (CX + 5.4, G + 1.8, 7.5), (CX + 5.4, G + 1.3, 10.5), (CX + 4.9, G + 0.9, 12.0)]
    for a, b in zip(pts, pts[1:]):
        c.line(a, b, 1.4, O)
    c.ellipsoid(CX + 4.7, G + 1.1, 12.4, 1.6, 1.4, 1.5, W)
    # back-leg shading (flanks only, hidden from front)
    for x in (cx - 3, cx + 4):
        for y in (G, G + 1):
            for z in (5, 6, 7):
                if c.get(x, y, z) == O and c.get(x, y, z + 1) != 0:
                    c.put(x, y, z, K)
    # front legs + paws (last, so nothing overwrites)
    for x in (cx - 1, cx + 2):
        for y in range(G, G + 7):
            for z in (9, 10):
                c.put(x, y, z, K)
        for z in (10, 11):
            c.put(x, G, z, K)
    # moss on stump
    for z in range(SZ):
        for x in range(SX):
            if c.get(x, G - 1, z) == LOG and c.get(x, G, z) == 0:
                h = hash01(x, z, 5, p["seed"])
                if h < 0.55:
                    c.put(x, G - 1, z, MOSS)
                elif h < 0.75:
                    c.put(x, G, z, CARPET)
    return c
