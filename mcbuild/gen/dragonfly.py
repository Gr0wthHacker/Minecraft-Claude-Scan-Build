"""Small dragonfly — a pond/willow accent, optionally on a perch.

Body along +x: two black compound eyes, light-blue thorax, long thin
banded abdomen tapering to 1x1. Two pairs of wings = closed birch trapdoors
(top half) so they read as thin pale translucent plates and need no support.
`perch`: a spruce fence post under the thorax so it can sit on a reed / post.

Cheap: light-blue / blue / black wool, birch trapdoors, spruce fence.
"""
from __future__ import annotations

from .canvas import Canvas

DEFAULTS = {"length": 14, "perch": 3, "seed": 0}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    L = int(p["length"]); perch = int(p["perch"])
    span = 7                                                   # wing length each side
    SX, SZ = L + 2, 2 * span + 3
    SY = 3 + perch + 1
    c = Canvas(SX, SY, SZ, donors)
    st, raw = c.state, c.raw_state
    S = {"body": st("light_blue_wool"), "band": st("blue_wool"), "eye": st("black_wool"),
         "wing": raw("birch_trapdoor", facing="north", half="top", open="false", powered="false", waterlogged="false"),
         "wing2": raw("birch_trapdoor", facing="north", half="bottom", open="false", powered="false", waterlogged="false"),
         "post": st("spruce_fence", north="false", south="false", east="false", west="false", waterlogged="false")}
    y0 = perch                                                 # body sits on top of the perch
    zc = SZ // 2
    hx = 1                                                     # head at low x
    # head: 3 wide, eyes bulging out on the sides and top
    for z in (zc - 1, zc, zc + 1):
        c.put(hx, y0, z, S["body"])
    for x in (hx - 1, hx):                                     # big wrap-around compound eyes, 2x2 each side
        for y in (y0, y0 + 1):
            c.put(x, y, zc - 1, S["eye"]); c.put(x, y, zc + 1, S["eye"])
    c.put(hx - 1, y0, zc, S["body"])                            # face between the eyes
    # thorax: 3 long, 3 wide, 2 tall
    for x in range(hx + 1, hx + 4):
        for z in (zc - 1, zc, zc + 1):
            c.put(x, y0, z, S["body"])
        c.put(x, y0 + 1, zc, S["body"])
    # abdomen: long, thin, banded, tapering to 1x1 (2 wide for the first third)
    ax0 = hx + 4
    for i, x in enumerate(range(ax0, ax0 + L - 5)):
        blk = S["band"] if i % 3 == 2 else S["body"]
        c.put(x, y0, zc, blk)
        if i < (L - 5) // 3:
            c.put(x, y0, zc + (1 if i % 2 else -1), blk)
    # wings: two pairs off the thorax top, front pair swept slightly forward, rear pair back
    wy = y0 + 1
    for side in (-1, 1):
        for k in range(1, span + 1):
            z = zc + side * (1 + k)
            # front pair: 2 wide, tapering to 1 at the tip
            fw = 2 if k < span - 1 else 1
            for x in range(hx + 1, hx + 1 + fw):
                c.put(x, wy, z, S["wing"])
            # hind pair: broader at the base (3), then 2, tip 1
            hw = 3 if k <= 2 else 2 if k < span - 1 else 1
            for x in range(hx + 4, hx + 4 + hw):                # 1-block gap between the pairs
                c.put(x, wy, z, S["wing"])
    # perch
    for y in range(0, perch):
        c.put(hx + 2, y, zc, S["post"])
    return c
