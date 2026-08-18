"""Rock casing that wraps AROUND an existing enclosed structure (a workspace
box hanging under the island). Rock outside its walls and under its floor,
tapered to an eroded belly beneath; NOTHING inside the box, nothing above
its top face (the island sits there).

  under   : litematic of the existing box (walls + floor + ceiling), saved
            with the same origin you'll paste this at
  wall    : rock thickness outside the box's side walls
  belly   : extra depth of rock under the box's floor at centre (bowl)
  headroom: air rows below the belly for hangings

Output has the box's x/z footprint + 2*wall, and height = box height + belly
+ headroom; the box occupies the top rows of the output at offset (wall,wall).
Paste at (box_origin_x - wall, box_origin_y - belly - headroom, box_origin_z - wall).
"""
from __future__ import annotations

import numpy as np

from .vertical import resolve_capture
from .canvas import Canvas, hash01
from ..ops.hollow import hollow

DEFAULTS = {"under": None, "wall": 3, "belly": 12, "headroom": 8, "lanterns": 10, "seed": 0,
            "wall_top_offset": 6,   # side casing starts this many rows below the box top (moss walls stay visible above)
            "grow": 0}              # enlarge the forbidden zone by this many blocks on every side + below,
                                    # for when the saved selection was cut INSIDE the real walls


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    from .. import schem as _schem
    ex = _schem.load(resolve_capture(p["under"]))
    es = ex.solid()
    EY, EZ, EX = es.shape
    W, B, H = int(p["wall"]), int(p["belly"]), int(p["headroom"])
    G = int(p["grow"])
    seed = int(p["seed"])
    # the forbidden hull is the saved box grown by G on x/z sides and below;
    # rock casing sits outside THAT
    EX2, EZ2, EY2 = EX + 2 * G, EZ + 2 * G, EY + G
    SX, SZ = EX2 + 2 * W, EZ2 + 2 * W
    SY = EY2 + B + H
    OY = B + H                     # grown-box y -> canvas y + OY ; x/z -> + W
    c = Canvas(SX, SY, SZ, donors)
    S = {
        "moss": c.state("moss_block"), "stone": c.state("stone"), "cobble": c.state("cobblestone"),
        "mosscobble": c.state("mossy_cobblestone"), "andesite": c.state("andesite"), "tuff": c.raw_state("tuff"),
        "rooted": c.raw_state("rooted_dirt"),
        "roots": c.raw_state("hanging_roots", waterlogged="false"),
        "chain": c.state("chain", axis="y", waterlogged="false"),
        "lant_h": c.state("lantern", hanging="true", waterlogged="false"),
        "soul_h": c.state("soul_lantern", hanging="true", waterlogged="false"),
        "drip_tip": c.state("pointed_dripstone", vertical_direction="down", thickness="tip", waterlogged="false"),
        "drip_frustum": c.state("pointed_dripstone", vertical_direction="down", thickness="frustum", waterlogged="false"),
        "drip_middle": c.state("pointed_dripstone", vertical_direction="down", thickness="middle", waterlogged="false"),
    }
    # the box, in canvas coordinates
    box = np.zeros((SY, SZ, SX), bool)
    box[OY + G:OY + G + EY, W + G:W + G + EZ, W + G:W + G + EX] = es
    # forbidden hull = saved box grown by G (sides + below); rock never enters it
    forbid = np.zeros((SY, SZ, SX), bool)
    forbid[OY:OY + EY2, W:W + EZ2, W:W + EX2] = True
    EX, EZ, EY = EX2, EZ2, EY2

    CX, CZ = SX / 2.0, SZ / 2.0
    RX, RZ = SX / 2.0, SZ / 2.0

    def rock(x, y, z):
        h = hash01(x, y, z, 7, seed)
        if h < 0.40: return S["stone"]
        if h < 0.66: return S["cobble"]
        if h < 0.84: return S["mosscobble"]
        if h < 0.93: return S["andesite"]
        return S["tuff"]

    def sq(x, z, n=3.5):
        ax = abs(x + 0.5 - CX) / RX; az = abs(z + 0.5 - CZ) / RZ
        return (ax ** n + az ** n) ** (1.0 / n)

    def belly_depth(x, z):
        t = min(1.0, sq(x, z))
        d = (1.0 - t ** 2.4) * B
        return int(round(d + 1.4 * np.sin(t * 7.0) + 0.7 * np.sin(t * 13.0)))

    # side casing: for every column outside the box footprint but inside the rounded outer
    # boundary, fill rock from the box's top face down to the belly bottom for that column
    top_face = OY + EY - 1 - int(p["wall_top_offset"])
    for z in range(SZ):
        for x in range(SX):
            r = sq(x, z) + 0.05 * (hash01(x, z, 3, seed) - 0.5)
            if r > 1.0:
                continue
            in_box_fp = W <= x < W + EX and W <= z < W + EZ
            if in_box_fp:
                # under the floor only
                d = max(1, belly_depth(x, z))
                for i in range(d):
                    y = OY - 1 - i
                    if y >= 0:
                        c.put(x, y, z, rock(x, y, z))
            else:
                # side casing: full height of the box, plus tapering below
                for y in range(top_face, OY - 1, -1):
                    if y == top_face and hash01(x, z, 11, seed) < 0.55:
                        c.put(x, y, z, S["moss"] if hash01(x, z, 12, seed) < 0.6 else S["rooted"])
                    else:
                        c.put(x, y, z, rock(x, y, z))
                d = max(0, belly_depth(x, z))
                for i in range(d):
                    y = OY - 1 - i
                    if y >= 0:
                        c.put(x, y, z, rock(x, y, z))
    # hard guarantee: nothing inside the box's bounding hull
    c.ids[forbid] = 0
    # hollow the casing (ceiling = island above; the box itself is context we must not carve)
    m = c.to_model()
    merged = m.copy()
    merged.ids = np.where(box, 1, m.ids)
    carve_ok = (m.ids > 0) & ~forbid
    hollow(merged, shell=2, ground=False, ceiling=True, keep_floor=False, keep_top_layers=0, carve_only=carve_ok)
    c.ids = np.where(forbid, 0, merged.ids)
    # hangings from the underside
    bottom = {}
    for z in range(SZ):
        for x in range(SX):
            col = np.where(c.ids[:, z, x] > 0)[0]
            if col.size:
                bottom[(x, z)] = int(col.min())
    for (x, z), y in bottom.items():
        if y < 2:
            continue
        h = hash01(x, z, 13, seed)
        if h < 0.09:
            ln = min(y, 1 + int(hash01(x, z, 17, seed) * 2.6))
            for i in range(ln):
                th = "tip" if (i == ln - 1 or ln == 1) else ("frustum" if i == 0 else "middle")
                c.put(x, y - 1 - i, z, S[f"drip_{th}"])
        elif h < 0.24:
            c.put(x, y - 1, z, S["roots"])
    nl = int(p["lanterns"])
    for k in range(nl):
        a = np.radians(k * (360.0 / nl) + 12)
        x, z = int(CX + 0.62 * RX * np.cos(a)), int(CZ + 0.62 * RZ * np.sin(a))
        col = np.where(c.ids[:, z, x] > 0)[0]
        if not col.size:
            continue
        y = int(col.min())
        n = c.get_name(x, y, z)
        if any(k2 in n for k2 in ("dripstone", "roots")):
            continue
        c.hang_string(x, y, z, 3 + (k % 4), "soul" if k % 5 == 2 else "lant", S)
    c.forbid = forbid
    return c
