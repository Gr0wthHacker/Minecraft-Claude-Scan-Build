"""Island underside belly: an eroded rock mass that hangs BELOW an existing
island (and below any built skirt), with dripstone, roots, glow-berry falls
and hanging lanterns. Nothing beside the skirt. Hollow, sealed.

Paste: schematic top layer = the layer directly under your skirt's bottom.
"""
from __future__ import annotations

import numpy as np

from .vertical import resolve_capture
from .canvas import Canvas, hash01
from ..ops.hollow import hollow

DEFAULTS = {
    "footprint": 41, "cap_depth": 16, "hang_headroom": 8,
    "footprint_shape": "rounded",       # rounded | square | circle
    "roundness": 4.0,                   # superellipse exponent for 'rounded'
    "lanterns": 10, "central_lanterns": 4, "seed": 0,
    # ---- fit-to-existing mode ------------------------------------------------
    # "under": path to a litematic of the EXISTING area beneath your island
    #          (select it in Litematica incl. air, save). The belly is then
    #          generated per-column directly BELOW the lowest existing block in
    #          that column, hugging walkways/walls, never overlapping them.
    #          Output has the same x/z origin and size as that file; paste it
    #          at the same corner.
    "under": None,
    "under_gap": 0,                     # extra air rows between existing bottom and belly top
}


def build(cfg: dict, donors: list | None = None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    CAP = int(p["cap_depth"]); HEAD = int(p["hang_headroom"])
    seed = int(p["seed"])
    existing = None
    if p.get("under"):
        from .. import schem as _schem
        existing = _schem.load(resolve_capture(p["under"]))
        ex_s = existing.solid()
        SX, SZ = ex_s.shape[2], ex_s.shape[1]
        # per-column lowest existing block (relative to the existing file's y0)
        col_bottom = np.full((SZ, SX), -1, int)
        for z in range(SZ):
            for x in range(SX):
                col = np.where(ex_s[:, z, x])[0]
                if col.size:
                    col_bottom[z, x] = int(col.min())
        # belly must fit below the LOWEST existing block anywhere in the footprint;
        # canvas y0 = existing y0 - (CAP+HEAD)  -> offset everything by that
        SY_ex = ex_s.shape[0]
        SY = SY_ex + CAP + HEAD
        OFF = CAP + HEAD                    # existing y -> canvas y + OFF
    else:
        N = int(p["footprint"]); SX = SZ = N; SY = CAP + HEAD
        col_bottom = None; OFF = 0
    CX, CZ = SX / 2.0, SZ / 2.0; RIN = min(SX, SZ) / 2.0
    TOPY = SY - 1
    c = Canvas(SX, SY, SZ, donors)
    if existing is not None:
        # copy the existing structure in so hangings/lanterns can attach to it
        # and so the audit sees the real context; it is stripped before export
        # (see `existing_mask` returned on the canvas)
        pass
    S = {
        "moss": c.state("moss_block"), "stone": c.state("stone"),
        "cobble": c.state("cobblestone"), "mosscobble": c.state("mossy_cobblestone"),
        "andesite": c.state("andesite"), "tuff": c.raw_state("tuff"),
        "roots": c.raw_state("hanging_roots", waterlogged="false"),
        "chain": c.state("iron_chain", axis="y", waterlogged="false"),
        "lant_h": c.state("lantern", hanging="true", waterlogged="false"),
        "soul_h": c.state("soul_lantern", hanging="true", waterlogged="false"),
        "drip_tip": c.state("pointed_dripstone", vertical_direction="down", thickness="tip", waterlogged="false"),
        "drip_frustum": c.state("pointed_dripstone", vertical_direction="down", thickness="frustum", waterlogged="false"),
        "drip_middle": c.state("pointed_dripstone", vertical_direction="down", thickness="middle", waterlogged="false"),
    }
    rad = lambda x, z: ((x + 0.5 - CX) ** 2 + (z + 0.5 - CZ) ** 2) ** 0.5

    def inside(x, z) -> bool:
        ax = abs(x + 0.5 - CX) / RIN; az = abs(z + 0.5 - CZ) / RIN
        shape = p["footprint_shape"]
        if shape == "square":
            return max(ax, az) < 1.0
        if shape == "circle":
            return (ax * ax + az * az) ** 0.5 < 1.0
        n = float(p["roundness"])
        return (ax ** n + az ** n) ** (1.0 / n) < 1.0

    def cap_depth(r):
        t = min(1.0, max(0.0, r) / RIN)
        d = (1.0 - t ** 2.6) * CAP
        return int(round(d + 1.6 * np.sin(t * 7.0) + 0.8 * np.sin(t * 13.0)))

    def rock(x, y, z):
        h = hash01(x, y, z, 7, seed)
        if h < 0.42: return S["stone"]
        if h < 0.66: return S["cobble"]
        if h < 0.84: return S["mosscobble"]
        if h < 0.93: return S["andesite"]
        return S["tuff"]

    for z in range(SZ):
        for x in range(SX):
            if not inside(x, z):
                continue
            r = rad(x, z) + 0.7 * (hash01(x, z, 3, seed) - 0.5)
            d = max(1, cap_depth(min(r, RIN)))
            if col_bottom is not None:
                if col_bottom[z, x] < 0:
                    continue                    # nothing above this column: no belly here
                top = col_bottom[z, x] + OFF - 1 - int(p["under_gap"])
            else:
                top = TOPY
            for i in range(d):
                y = top - i
                if y >= 0:
                    c.put(x, y, z, S["moss"] if (i == 0 and hash01(x, z, 11, seed) < 0.35) else rock(x, y, z))
    # hollow the belly (ceiling = the island above seals it)
    m = c.to_model()
    if existing is not None:
        # temporarily merge existing structure so the flood sees it as sealed above
        ex_ids = np.zeros_like(m.ids)
        ex_ids[OFF:OFF + existing.ids.shape[0]] = (existing.solid()).astype(np.int32)
        merged = m.copy(); merged.ids = np.where(ex_ids > 0, 1, m.ids)   # 1 = any solid palette idx
        belly_only = (m.ids > 0) & (ex_ids == 0)
        hollow(merged, shell=2, ground=False, ceiling=True, keep_floor=False, keep_top_layers=0,
               carve_only=belly_only)
        c.ids = np.where(ex_ids > 0, 0, merged.ids)
    else:
        hollow(m, shell=2, ground=False, ceiling=True, keep_floor=False, keep_top_layers=1)
        c.ids = m.ids
    c.existing_mask = None
    # hangings from the underside
    bottom = {}
    for z in range(SZ):
        for x in range(SX):
            col = np.where(c.ids[:, z, x] > 0)[0]
            if col.size:
                bottom[(x, z)] = int(col.min())
    berry_head = c.raw_state("cave_vines", age="25", berries="true")
    berry_body = c.raw_state("cave_vines_plant", berries="false")
    berry_bodyb = c.raw_state("cave_vines_plant", berries="true")
    for (x, z), y in bottom.items():
        if y < 2:
            continue
        h = hash01(x, z, 13, seed)
        r = rad(x, z)
        if h < 0.09:
            ln = min(y, 1 + int(hash01(x, z, 17, seed) * 2.6))
            for i in range(ln):
                th = "tip" if (i == ln - 1 or ln == 1) else ("frustum" if i == 0 else "middle")
                c.put(x, y - 1 - i, z, S[f"drip_{th}"])
        elif h < 0.24:
            c.put(x, y - 1, z, S["roots"])
        elif h < 0.30 and r < RIN - 4:
            ln = min(y, 2 + int(hash01(x, z, 19, seed) * 4))
            for i in range(1, ln + 1):
                c.put(x, y - i, z, berry_head if i == ln else
                      (berry_bodyb if hash01(x, i, z, seed) < 0.35 else berry_body))
    # lantern ring + central
    spots = []
    nl = int(p["lanterns"])
    for k in range(nl):
        a = np.radians(k * (360.0 / nl) + 12)
        spots.append((int(CX + 0.66 * RIN * np.cos(a)), int(CZ + 0.66 * RIN * np.sin(a)),
                      3 + (k % 4), "soul" if k % 5 == 2 else "lant"))
    for k in range(int(p["central_lanterns"])):
        a = np.radians(k * (360.0 / max(1, p["central_lanterns"])) + 45)
        spots.append((int(CX + 0.27 * RIN * np.cos(a)), int(CZ + 0.27 * RIN * np.sin(a)), 3 + (k % 2), "lant"))
    for x, z, drop, kind in spots:
        col = np.where(c.ids[:, z, x] > 0)[0]
        if not col.size:
            continue
        y = int(col.min())
        n = c.get_name(x, y, z)
        if any(k2 in n for k2 in ("dripstone", "roots", "vine")) or y - drop - 1 < 0:
            continue
        c.hang_string(x, y, z, drop, kind, S)
    return c
