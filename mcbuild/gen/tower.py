"""Mossy ruined watchtower: round, hollow, climbable, half-collapsed."""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

DEFAULTS = {
    "size": [15, 36, 15], "radius": 4.6, "wall_top": 26,
    "collapse_from": 14, "collapse_arc": [95, 215],
    "batter": 1.4, "floors": [9, 18], "windows_y": [6, 14, 22], "windows_ang": [40, 320],
    "roof_apex": 8, "seed": 0,
}


def build(cfg: dict, donors: list | None = None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    SX, SY, SZ = p["size"]
    CX, CZ = SX / 2.0, SZ / 2.0
    R = float(p["radius"]); TOP = int(p["wall_top"]); seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors)
    S = {
        "bricks": c.state("stone_bricks"), "mossy": c.state("mossy_stone_bricks"),
        "cracked": c.state("cracked_stone_bricks"), "cobble": c.state("cobblestone"),
        "mosscobble": c.state("mossy_cobblestone"), "planks": c.state("spruce_planks"),
        "log": c.state("spruce_log", axis="y"),
        "ladder": c.state("ladder", facing="west", waterlogged="false"),
        "bars": c.state("iron_bars", north="false", south="false", east="false", west="false", waterlogged="false"),
        "chain": c.state("chain", axis="y", waterlogged="false"),
        "lant_h": c.state("lantern", hanging="true", waterlogged="false"),
        "lant": c.state("lantern", hanging="false", waterlogged="false"),
        "carpet": c.state("moss_carpet"),
    }
    rad = lambda x, z: ((x + 0.5 - CX) ** 2 + (z + 0.5 - CZ) ** 2) ** 0.5
    R_at = lambda y: R + max(0.0, p["batter"] - 0.28 * y)
    a0, a1 = p["collapse_arc"]

    def mat(x, y, z):
        t = y / TOP
        h = hash01(x, y, z, 7, seed)
        if y <= 4 and h < 0.45:
            return S["mosscobble"]
        moss_p = 0.70 * (1.0 - t) ** 1.3
        crack_p = 0.10 + 0.35 * t
        if h < moss_p:
            return S["mossy"]
        if h < moss_p + crack_p:
            return S["cracked"]
        if h < moss_p + crack_p + 0.06:
            return S["cobble"]
        return S["bricks"]

    solid_names = {"minecraft:stone_bricks", "minecraft:mossy_stone_bricks", "minecraft:cracked_stone_bricks",
                   "minecraft:cobblestone", "minecraft:mossy_cobblestone"}
    # shell
    for y in range(TOP + 1):
        Ry = R_at(y)
        for z in range(SZ):
            for x in range(SX):
                r = rad(x, z)
                if not (Ry - 1.0 <= r <= Ry):
                    continue
                ang = np.degrees(np.arctan2(z + 0.5 - CZ, x + 0.5 - CX))
                if a0 < ang < a1:
                    frac = (ang - a0) / (a1 - a0)
                    limit = p["collapse_from"] + int(12 * abs(frac - 0.5) * 2) + int(3 * hash01(x, z, 3, seed))
                    if y > limit:
                        continue
                if 200 <= ang < 240 and 9 <= y <= 12 and hash01(x, y, z, 5, seed) < 0.75:
                    continue
                c.put(x, y, z, mat(x, y, z))
    # floors
    for fy in [0] + list(p["floors"]):
        for z in range(SZ):
            for x in range(SX):
                if rad(x, z) < R - 1.0:
                    if fy == 0:
                        c.put(x, fy, z, S["cobble"] if hash01(x, z, 9, seed) < 0.5 else S["mossy"])
                    elif hash01(x, fy, z, 11, seed) < 0.82:
                        c.put(x, fy, z, S["planks"])
    # doorway (+z)
    for y in (1, 2, 3):
        for x in (int(CX) - 1, int(CX)):
            for z in range(SZ):
                if rad(x, z) >= R - 1.0 and z > CZ:
                    c.put(x, y, z, 0)
    for x in (int(CX) - 1, int(CX)):
        c.put(x, 4, SZ - 3, S["mossy"])
    # windows
    for wy in p["windows_y"]:
        for ang in p["windows_ang"]:
            a = np.radians(ang)
            wx, wz = int(CX + (R - 0.5) * np.cos(a)), int(CZ + (R - 0.5) * np.sin(a))
            for dy in (0, 1):
                c.put(wx, wy + dy, wz, S["bars"])
    # parapet
    for z in range(SZ):
        for x in range(SX):
            r = rad(x, z)
            if not (R - 1.0 <= r <= R) or c.get(x, TOP, z) == 0:
                continue
            ang = np.degrees(np.arctan2(z + 0.5 - CZ, x + 0.5 - CX))
            if a0 + 15 < ang < a1 - 15:
                continue
            if (int(ang + 360) // 24) % 2 == 0:
                c.put(x, TOP + 1, z, S["bricks"] if hash01(x, z, 13, seed) < 0.7 else S["cracked"])
    # roof frame
    apex = (CX + 0.8, TOP + p["roof_apex"], CZ - 0.3)
    for ang in range(-85, 96, 22):
        a = np.radians(ang)
        c.line((CX + (R - 0.4) * np.cos(a), TOP + 1, CZ + (R - 0.4) * np.sin(a)), apex, 0.62, S["log"])
    # solid apex knot so every rafter meets and the lantern has something to hang from
    c.sphere(apex[0], apex[1], apex[2], 1.1, S["log"])
    for ang in range(-85, 96, 6):
        a = np.radians(ang); t = 0.6
        x = CX + (R - 0.4) * (1 - t) * np.cos(a) + (apex[0] - CX) * t
        z = CZ + (R - 0.4) * (1 - t) * np.sin(a) + (apex[2] - CZ) * t
        y = TOP + 1 + (apex[1] - TOP - 1) * t
        c.put(int(x), int(y), int(z), S["planks"])
    c.line((CX - 3.8, TOP - 8, CZ + 2.5), (CX - 0.5, TOP + 2, CZ - 0.5), 0.45, S["log"])
    ax, az = int(apex[0]), int(apex[2])
    ay = int(apex[1])
    while ay > TOP and c.get(ax, ay, az) == 0:
        ay -= 1                                  # find the knot's underside
    if c.get(ax, ay - 1, az) == 0 and c.get(ax, ay - 2, az) == 0:
        c.put(ax, ay - 1, az, S["chain"])
        c.put(ax, ay - 2, az, S["lant_h"])
    # vines + edge moss + door lanterns
    for z in range(SZ):
        for x in range(SX):
            for y in range(1, TOP):
                if c.get_name(x, y, z) not in solid_names:
                    continue
                for prop, dx, dz in (("west", 1, 0), ("east", -1, 0), ("south", 0, -1), ("north", 0, 1)):
                    vx, vz = x + dx, z + dz
                    if not c.inb(vx, y, vz) or rad(vx, vz) <= R or c.get(vx, y, vz) != 0:
                        continue
                    if hash01(vx, y, vz, 23, seed) > 0.40 * (1.0 - y / TOP):
                        continue
                    c.put(vx, y, vz, c.vine(vx, y, vz, prop))
    for z in range(SZ):
        for x in range(SX):
            col = np.where(c.ids[:, z, x] > 0)[0]
            if col.size and 12 <= col.max() < TOP and c.get_name(x, int(col.max()), z) in solid_names \
                    and hash01(x, z, 31, seed) < 0.5:
                c.put(x, int(col.max()) + 1, z, S["carpet"])
    for x in (int(CX) - 3, int(CX) + 2):
        for z in range(SZ - 1, -1, -1):
            if c.get(x, 0, z) != 0 and c.get(x, 1, z) == 0:
                c.put(x, 1, z, S["lant"]); break
    # ladders last, guaranteed backing
    lx = int(CX + R - 1.0) - 1
    for y in range(1, TOP):
        c.put(lx, y, int(CZ), S["ladder"])
        c.put(lx + 1, y, int(CZ), S["bricks"] if hash01(lx, y, 3, seed) < 0.6 else S["mossy"])
    return c
