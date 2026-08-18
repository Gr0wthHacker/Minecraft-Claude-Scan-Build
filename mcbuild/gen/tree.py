"""Lantern moss tree, standalone (paste onto an existing platform).

Buttressed twisting trunk, knee-arc roots, staggered forking limbs, big
weeping canopy, lantern strings under the canopy, glow-berry falls, dead
spire, moss-carpet crown fuzz. All knobs live in the config.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

DEFAULTS = {
    "size": [25, 36, 25],
    "trunk_height": 16,
    "trunk_r0": 1.8, "trunk_r1": 0.85,
    "buttress_amp": 1.9, "buttress_fade": 0.5, "twist_deg": 70,
    "lobes": [[15, 1.0], [75, 0.75], [140, 0.95], [205, 0.85], [265, 0.9], [325, 0.7]],
    "lean": [2.2, -1.8],
    "root_len": 3.2, "root_len_w": 2.6, "root_knee": 1.4,
    "canopy_r": 9.8, "canopy_lift": 5.0,
    "spire": True,
    "lantern_strings": 17, "soul_every": 5, "berry_strings": 3,
    "vine_p": 0.62, "vine_len": [3, 8],
    "fuzz_p": 0.30, "moss_clump_p": 0.10,
    "wood": "oak_log", "wood_dark": "spruce_log", "wood_scar": "stripped_oak_log",
    "leaf": "oak_leaves", "leaf2": "azalea_leaves", "flower_leaf": "flowering_azalea_leaves",
    "seed": 0,
}


def build(cfg: dict, donors: list | None = None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    SX, SY, SZ = p["size"]
    CX, CZ = SX // 2, SZ // 2
    H = p["trunk_height"]
    seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors)
    S = {
        "wood": c.state(p["wood"], axis="y"), "wood_dark": c.state(p["wood_dark"], axis="y"),
        "wood_scar": c.state(p["wood_scar"], axis="y"),
        "leaf": c.state(p["leaf"], persistent="true", distance="7", waterlogged="false"),
        "leaf2": c.state(p["leaf2"], persistent="true", distance="7", waterlogged="false"),
        "flower": c.state(p["flower_leaf"], persistent="true", distance="7", waterlogged="false"),
        "moss": c.state("moss_block"), "carpet": c.state("moss_carpet"),
        "fence": c.state("oak_fence", north="false", south="false", east="false", west="false", waterlogged="false"),
        "chain": c.state("iron_chain", axis="y", waterlogged="false"),
        "lant": c.state("lantern", hanging="false", waterlogged="false"),
        "lant_h": c.state("lantern", hanging="true", waterlogged="false"),
        "soul_h": c.state("soul_lantern", hanging="true", waterlogged="false"),
    }
    lean = p["lean"]

    def center(t):
        return CX - 0.5 + lean[0] * t * t, CZ + 1.0 + lean[1] * t

    # ---- trunk ---------------------------------------------------------------
    lobes = p["lobes"]
    for iy in range(H + 1):
        t = iy / H
        cx, cz = center(t)
        r0 = p["trunk_r0"] + (p["trunk_r1"] - p["trunk_r0"]) * t
        amp = p["buttress_amp"] * max(0.0, 1.0 - t / p["buttress_fade"])
        twist = p["twist_deg"] * t
        span = int(np.ceil(r0 + amp)) + 1
        for z in range(int(cz) - span, int(cz) + span + 1):
            for x in range(int(cx) - span, int(cx) + span + 1):
                dx, dz = x - cx, z - cz
                d = (dx * dx + dz * dz) ** 0.5
                th = np.degrees(np.arctan2(dz, dx))
                ridge = sum(w * max(0.0, np.cos(np.radians(th - a - twist))) ** 6 for a, w in lobes)
                if d <= r0 + amp * ridge:
                    c.put(x, iy, z, S["wood"])
    # ---- roots ---------------------------------------------------------------
    bx, bz = center(0.0)
    for a, w in lobes:
        u = np.radians(a)
        ux, uz = np.cos(u), np.sin(u)
        ln = p["root_len"] + p["root_len_w"] * w
        knee = p["root_knee"] + 1.1 * w
        p0 = (bx + 1.2 * ux, 2.2, bz + 1.2 * uz)
        p1 = (bx + 0.55 * ln * ux, knee, bz + 0.55 * ln * uz)
        p2 = (bx + ln * ux, 0.4, bz + ln * uz)
        c.line(p0, p1, 0.62, S["wood"])
        c.line(p1, p2, 0.58, S["wood"])
        tip = 1.2 + 1.6 * hash01(int(a), 5, seed)
        c.line(p2, (bx + (ln + tip) * ux, 0.0, bz + (ln + tip) * uz), 0.5, S["wood"])
    # ---- limbs ---------------------------------------------------------------
    for t0, (dx, dz), ln, (fx, fz), fl in [
        (0.55, (-1.0, -0.55), 7.0, (-0.4, -1.0), 3.5),
        (0.72, (0.95, 0.65), 6.5, (1.0, -0.3), 3.5),
        (0.86, (-0.6, 0.95), 5.5, (-1.0, 0.2), 3.0),
        (0.94, (0.4, -1.0), 5.0, (1.0, -0.6), 2.5),
    ]:
        x0, z0 = center(t0)
        y0 = 1 + t0 * H
        n = (dx * dx + dz * dz) ** 0.5
        dx, dz = dx / n, dz / n
        x1, y1, z1 = x0 + dx * ln, y0 + 0.45 * ln, z0 + dz * ln
        c.line((x0, y0, z0), (x1, y1, z1), 0.55, S["wood"])
        fn = (fx * fx + fz * fz) ** 0.5
        c.line((x1, y1, z1), (x1 + fx / fn * fl, y1 + 0.5 * fl, z1 + fz / fn * fl), 0.45, S["wood"])
    ax, az = center(1.0)
    c.line((ax - 1, 9, az + 0.5), (CX - 8, 13, CZ - 5), 0.7, S["wood"])       # low bough
    if p["spire"]:
        sp = [(ax, H - 1, az), (ax + 4, H + 6, az - 3), (ax + 6.5, H + 13, az - 4)]
        c.line(sp[0], sp[1], 0.7, S["wood_dark"])
        c.line(sp[1], sp[2], 0.5, S["wood_scar"])
        c.line(sp[1], (ax + 7, H + 8, az - 1), 0.4, S["wood_scar"])
    # ---- canopy --------------------------------------------------------------
    R = p["canopy_r"]
    L = p["canopy_lift"]
    jit = lambda x, y, z: 1.2 * (hash01(x, z, 31, seed) - 0.5)
    for x, y, z, r, sq, key in [
        (CX + 0.5, H + L, CZ, R, 0.55, "leaf"),
        (CX - 5, H + L - 2.5, CZ - 3, R * 0.61, 0.5, "leaf2"),
        (CX + 5.5, H + L - 2.5, CZ + 3.5, R * 0.59, 0.5, "leaf2"),
        (CX + 0.5, H + L + 3.5, CZ + 0.5, R * 0.65, 0.6, "leaf"),
        (CX - 8, H - 3.0, CZ - 5, 4.0, 0.55, "leaf2"),
        (CX + 4.5, H + L + 1, CZ - 4.5, R * 0.49, 0.5, "leaf"),
        (CX - 4.5, H + L + 1, CZ + 4.5, R * 0.49, 0.5, "leaf"),
    ]:
        c.sphere(x, y, z, r, S[key], squash=sq, replace=False, jitter=jit)
    ids = c.ids
    leafy = (S["leaf"], S["leaf2"])
    for (y, z, x) in zip(*np.where(ids > 0)):
        if ids[y, z, x] in leafy and hash01(x, y, z, 37, seed) < 0.12:
            if any(c.get(x + dx, y + dy, z + dz) == 0 for dx, dy, dz in
                   ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))):
                ids[y, z, x] = S["flower"]
    # ---- hollow niche ------------------------------------------------------
    woods = (S["wood"], S["wood_dark"], S["wood_scar"])
    for dz in range(4, -5, -1):
        for dx in range(-4, 5):
            x, z = CX + dx, CZ + dz
            if (c.get(x, 2, z) in woods and c.get(x, 3, z) in woods and c.get(x, 2, z + 1) == 0
                    and c.get(x, 1, z) in woods):
                c.put(x, 3, z, 0)
                c.put(x, 2, z, S["lant"])
                dz = -99
                break
        if dz == -99:
            break
    # ---- trunk vines -------------------------------------------------------
    for z in range(SZ):
        for x in range(SX):
            for y in range(1, H - 2):
                if c.get(x, y, z) != S["wood"]:
                    continue
                for prop, dx, dz in (("west", 1, 0), ("east", -1, 0), ("south", 0, -1), ("north", 0, 1)):
                    vx, vz = x + dx, z + dz
                    if c.get(vx, y, vz) == 0 and hash01(vx, y, vz, 61, seed) < 0.10:
                        c.put(vx, y, vz, c.vine(vx, y, vz, prop))
    # ---- weeping fringe ----------------------------------------------------
    leafy3 = (S["leaf"], S["leaf2"], S["flower"])
    ids0 = c.ids.copy()
    up_vine = c.raw_state("vine", east="false", north="false", south="false", west="false", up="true")
    for (y, z, x) in zip(*np.where(ids0 > 0)):
        if ids0[y, z, x] not in leafy3 or y < H - 4 or c.get(x, y - 1, z) != 0:
            continue
        rim = sum(1 for ddx, ddz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if c.get(x + ddx, y, z + ddz) <= 0) >= 2
        if not rim:
            continue
        h = hash01(x, y, z, 41, seed)
        if h < 0.45:
            for i in range(1, 2 + int(hash01(x, z, 43, seed) * 2.5)):
                if c.get(x, y - i, z) == 0:
                    c.put(x, y - i, z, ids0[y, z, x])
        elif h < p["vine_p"]:
            ln = p["vine_len"][0] + int(hash01(x, z, 47, seed) * (p["vine_len"][1] - p["vine_len"][0]))
            for i in range(1, ln + 1):
                if y - i <= 3 or c.get(x, y - i, z) != 0:
                    break
                c.put(x, y - i, z, up_vine)
    # ---- crown texture -----------------------------------------------------
    ids0 = c.ids.copy()
    for (y, z, x) in zip(*np.where(ids0 > 0)):
        if ids0[y, z, x] not in leafy3 or y < H:
            continue
        above_air = c.get(x, y + 1, z) == 0
        if above_air and y >= H + 3 and hash01(x, y, z, 83, seed) < p["fuzz_p"]:
            c.put(x, y + 1, z, S["carpet"])
        if above_air and y >= H + 2 and hash01(x, y, z, 89, seed) < p["moss_clump_p"]:
            c.ids[y, z, x] = S["moss"]
    for ang in range(0, 360, 30):
        a = np.radians(ang + 8)
        tx = int(CX + 0.5 + (R + 1.2) * np.cos(a))
        ty = H + 3 + int(3.5 * hash01(ang, 5, seed) * 2 - 3.5)
        tz = int(CZ + (R + 1.2) * np.sin(a))
        if not (1 <= tx < SX - 1 and 1 <= tz < SZ - 1 and 1 <= ty < SY - 1):
            continue
        near = any(ids0[ty + dy, tz + dz, tx + dx] in leafy3
                   for dx in (-2, -1, 0, 1, 2) for dy in (-1, 0, 1) for dz in (-2, -1, 0, 1, 2)
                   if c.inb(tx + dx, ty + dy, tz + dz))
        if near and c.get(tx, ty, tz) == 0:
            c.put(tx, ty, tz, S["leaf"])
            if c.get(tx, ty - 1, tz) == 0 and hash01(tx, tz, 7, seed) < 0.4:
                c.put(tx, ty - 1, tz, S["leaf"])
    for ang in range(15, 360, 40):
        a = np.radians(ang)
        dx, dz = np.cos(a), np.sin(a)
        for rr in range(7, 12):
            tx, tz = int(CX + 0.5 + rr * dx), int(CZ + rr * dz)
            ty = H + 3 + int(2 * hash01(ang, 9, seed)) - 1
            if not c.inb(tx, ty, tz):
                break
            if c.get(tx, ty, tz) == 0:
                bx2, bz2 = int(CX + 0.5 + (rr - 1) * dx), int(CZ + (rr - 1) * dz)
                if c.get(bx2, ty, bz2) in leafy3:
                    c.put(tx, ty, tz, S["fence"])
                break
    # ---- lanterns ----------------------------------------------------------
    n_l = int(p["lantern_strings"])
    spots = []
    for k in range(n_l):
        a = np.radians(k * (360.0 / n_l) + 17)
        rr = 3.5 + 5.0 * hash01(k, 3, seed)
        spots.append((int(CX + rr * np.cos(a)), int(CZ + rr * np.sin(a)),
                      1 + int(5 * hash01(k, 11, seed)),
                      "soul" if p["soul_every"] and k % p["soul_every"] == 2 else "lant"))
    berry_head = c.raw_state("cave_vines", age="25", berries="true")
    berry_body = c.raw_state("cave_vines_plant", berries="false")
    berry_bodyb = c.raw_state("cave_vines_plant", berries="true")
    for k in range(int(p["berry_strings"])):
        a = np.radians(k * 120 + 60)
        spots.append((int(CX + 4.5 * np.cos(a)), int(CZ + 4.5 * np.sin(a)), 2 + k % 3, "berry"))
    for x, z, drop, kind in spots:
        ceil = None
        for y in range(6, SY - 1):
            n = c.get_name(x, y, z)
            if any(k2 in n for k2 in ("leaves", "log", "wood")) and c.get(x, y - 1, z) == 0:
                ceil = y
                break
        if ceil is None or ceil <= 6:
            continue
        free = 0
        while free < drop + 1 and ceil - 1 - free > 3 and c.get(x, ceil - 1 - free, z) == 0:
            free += 1
        drop = min(drop, free - 1)
        if drop < 1:
            continue
        if kind == "berry":
            for i in range(1, drop + 1):
                last = i == drop or c.get(x, ceil - i - 1, z) != 0
                c.put(x, ceil - i, z, berry_head if last else
                      (berry_bodyb if hash01(x, i, z, seed) < 0.4 else berry_body))
        else:
            c.hang_string(x, ceil, z, drop, kind, S)
    return c
