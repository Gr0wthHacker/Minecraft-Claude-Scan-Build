"""A floating island in the void with a lake on it, sited where a waterfall already lands.

    voidisle: rock with a surface that actually undulates, a lake set INTO that surface rather than
              being the whole of it, a beach where the water meets the ground, planting, vines off the
              underside and an outflow notch so the stream carries on down.

The difference between this and a basin is that the lake is a FEATURE of a landform, not the landform
itself. The surface is a height field - a knoll, hollows, a ragged rim that thins as it goes - and the
water sits in one hollow of it. A bowl with water in it reads as a tub no matter how big you make it.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .ground import prune_plants
from .vertical import Ctx, World, rock_name

VOIDISLE = {
    "under": None,
    "center": None,            # world (x, z) - put it under where the fall lands
    "top_y": 100,              # nominal surface; the height field moves around this
    "rx": 20.0, "rz": 17.0,
    "relief": 3,               # how far the surface rises and falls
    "depth": 10,               # rock under the surface at the middle
    "wobble": 2.4,             # raggedness of the outline
    "lake_at": None,           # world (x, z) the lake centres on; defaults to `center`
    "lake_rx": 7.0, "lake_rz": 6.0,
    "lake_drop": 3,            # how far below the local surface the water sits
    "beach": [("gravel", 0.42), ("sand", 0.30), ("cobblestone", 0.28)],
    "ground": [("moss_block", 0.46), ("mossy_cobblestone", 0.24), ("cobblestone", 0.18),
               ("stone", 0.12)],
    "carpet": 0.26, "grass": 0.14, "azalea": 0.05, "fern": 0.05,
    "trees": 3,                # small leaf-and-log clusters
    "vine_rate": 0.18, "vine_len": [3, 9],
    "lantern_reach": 8,        # no daylight down here
    "outflow": True,           # a notch so the stream leaves again and carries on falling
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
# ferns, grass and azalea root only in soil; moss carpet will sit on any solid block
SOIL = ("moss_block", "grass_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "mud")
DIRS4 = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))


def build_voidisle(cfg: dict, donors=None) -> Canvas:
    p = {**VOIDISLE, **cfg}
    if not p.get("center"):
        raise ValueError("voidisle needs params.center")
    ctx = Ctx(p["under"]) if p.get("under") else None
    cx, cz = (int(v) for v in p["center"])
    lx, lz = (int(v) for v in (p["lake_at"] or p["center"]))
    ty, seed = int(p["top_y"]), int(p["seed"])

    surf = _surface(cx, cz, ty, p, seed)
    lake, water_y = _carve_lake(surf, lx, lz, p)
    w = World()
    _rock(w, surf, cx, cz, ty, p, seed)
    wet = _water(w, surf, lake, water_y)
    beach = _beach(w, surf, lake, p, seed)
    _planting(w, surf, lake, beach, p, seed)
    trees = _trees(w, surf, lake, beach, cx, cz, p, seed)
    notch = _outflow(w, surf, lake, water_y, cx, cz, p) if p["outflow"] else None
    vines = _vines(w, surf, p, seed)
    lit = _lanterns(w, surf, lake, water_y, p)
    prune_plants(w, ctx)

    return w.canvas({"kind": "voidisle", "center": [cx, cz], "top_y": ty,
                     "surface_cells": len(surf), "water_cells": wet, "water_y": water_y,
                     "beach_cells": len(beach), "trees": trees, "vines": vines,
                     "lanterns": lit, "outflow": notch})


# ------------------------------------------------------------------ the landform

def _noise(x: int, z: int, seed: int, scale: int = 5) -> float:
    """Smooth-ish value noise: average the lattice cell and its neighbours so the surface rolls
    instead of jittering one block at a time."""
    gx, gz = x // scale, z // scale
    tot = 0.0
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            tot += hash01(gx + dx, gz + dz, 7, seed)
    return tot / 9.0


def _surface(cx, cz, ty, p, seed) -> dict:
    """Height field: {(x, z): surface_y}. Thins and drops toward a ragged rim."""
    rx, rz, relief, wob = float(p["rx"]), float(p["rz"]), int(p["relief"]), float(p["wobble"])
    out = {}
    for dx in range(-int(rx) - 4, int(rx) + 5):
        for dz in range(-int(rz) - 4, int(rz) + 5):
            x, z = cx + dx, cz + dz
            d = ((dx / rx) ** 2 + (dz / rz) ** 2) ** 0.5
            edge = 1.0 + 0.08 * wob * (hash01(x, z, 11, seed) - 0.5)
            if d > edge:
                continue
            if d > 0.86 and hash01(x, z, 13, seed) < 0.18:
                continue                                # a bite out of the rim
            h = ty + int(round(relief * (_noise(x, z, seed) - 0.45) * 2))
            h -= int(round(4 * max(0.0, d - 0.62) / 0.38))   # the ground falls away at the edges
            out[(x, z)] = h
    return out


def _carve_lake(surf: dict, lx, lz, p) -> tuple[set, int]:
    """Sink one hollow for the water and return its surface level.

    The water level is taken from the LOWEST ground it has to sit in, then the shore around it is
    raised to contain it - so the lake is a hollow in the land, not a tub bolted on."""
    lrx, lrz, drop = float(p["lake_rx"]), float(p["lake_rz"]), int(p["lake_drop"])
    inside = {c for c in surf
              if ((c[0] - lx) / lrx) ** 2 + ((c[1] - lz) / lrz) ** 2 <= 1.0}
    if not inside:
        raise ValueError("the lake ellipse does not land on the island - check lake_at")
    water_y = min(surf[c] for c in inside) - 1
    for c in inside:
        d = (((c[0] - lx) / lrx) ** 2 + ((c[1] - lz) / lrz) ** 2) ** 0.5
        surf[c] = water_y - max(1, int(round(drop * (1.0 - d ** 1.5))))
    for c in list(surf):                                # bank: anything ringing the water must hold it
        if c in inside:
            continue
        if any((c[0] + dx, c[1] + dz) in inside for _, dx, dz in DIRS4):
            surf[c] = max(surf[c], water_y + 1)
    return inside, water_y


def _rock(w: World, surf: dict, cx, cz, ty, p, seed):
    """Fill from each surface cell down, thicker toward the middle, undercut at the rim."""
    rx, rz, depth = float(p["rx"]), float(p["rz"]), int(p["depth"])
    for (x, z), h in surf.items():
        d = (((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2) ** 0.5
        thick = max(2, int(round(depth * (1.0 - d ** 1.7))))
        for k in range(thick):
            w.put(x, h - k, z, rock_name(x, h - k, z, seed))


def _water(w: World, surf: dict, lake: set, water_y: int) -> int:
    n = 0
    for c in lake:
        for y in range(surf[c] + 1, water_y + 1):
            w.put(c[0], y, c[1], "water", level="0")
            n += 1
    return n


def _beach(w: World, surf: dict, lake: set, p, seed) -> set:
    """Sand and gravel on the ground that rings the water."""
    out = set()
    for c in surf:
        if c in lake:
            continue
        if not any((c[0] + dx, c[1] + dz) in lake for _, dx, dz in DIRS4):
            continue
        out.add(c)
        w.put(c[0], surf[c], c[1], _pick(p["beach"], c[0], surf[c], c[1], seed))
    # the lake bed itself, where it is shallow
    for c in lake:
        if any((c[0] + dx, c[1] + dz) not in lake for _, dx, dz in DIRS4):
            w.put(c[0], surf[c], c[1], _pick(p["beach"], c[0], surf[c], c[1], seed + 1))
    return out


def _planting(w: World, surf: dict, lake: set, beach: set, p, seed):
    """Ground cover on the dry land, thinning nowhere in particular - it is a wild island."""
    for c, h in surf.items():
        if c in lake or c in beach:
            continue
        ground = _pick(p["ground"], c[0], h, c[1], seed)
        w.put(c[0], h, c[1], ground)
        if w.has(c[0], h + 1, c[1]):
            continue
        r = hash01(c[0], c[1], 31, seed)
        if ground not in SOIL:
            # bare rock takes carpet and nothing that needs roots
            if r < p["carpet"]:
                w.put(c[0], h + 1, c[1], "moss_carpet")
            continue
        if r < p["azalea"]:
            w.put(c[0], h + 1, c[1], "flowering_azalea" if r < p["azalea"] * 0.4 else "azalea")
        elif r < p["azalea"] + p["fern"]:
            w.put(c[0], h + 1, c[1], "fern")
        elif r < p["azalea"] + p["fern"] + p["grass"]:
            w.put(c[0], h + 1, c[1], "short_grass")
        elif r < p["azalea"] + p["fern"] + p["grass"] + p["carpet"]:
            w.put(c[0], h + 1, c[1], "moss_carpet")


def _trees(w: World, surf: dict, lake: set, beach: set, cx, cz, p, seed) -> int:
    """Small oak clumps: a trunk and a blob of leaves. Enough to break the skyline of the island."""
    want = int(p["trees"])
    if want <= 0:
        return 0
    dry = sorted(c for c in surf if c not in lake and c not in beach
                 and 3 <= math.hypot(c[0] - cx, c[1] - cz))
    placed, spots = 0, []
    for c in dry:
        if placed >= want:
            break
        if hash01(c[0], c[1], 37, seed) > 0.12:
            continue
        if any(abs(c[0] - a) + abs(c[1] - b) < 7 for a, b in spots):
            continue
        h = surf[c]
        trunk = 3 + int(hash01(c[0], c[1], 41, seed) * 2)
        for k in range(1, trunk + 1):
            w.put(c[0], h + k, c[1], "oak_log", axis="y")
        top = h + trunk
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in (0, 1):
                    if abs(dx) + abs(dz) + dy * 2 > 3:
                        continue
                    if dx == 0 and dz == 0 and dy == 0:
                        continue
                    w.put(c[0] + dx, top + dy, c[1] + dz, "oak_leaves",
                          distance="1", persistent="true", waterlogged="false")
        spots.append(c)
        placed += 1
    return placed


def _outflow(w: World, surf: dict, lake: set, water_y: int, cx, cz, p):
    """A notch in the bank so the stream leaves again and carries on falling into the dark."""
    bank = [c for c in surf if c not in lake
            and any((c[0] + dx, c[1] + dz) in lake for _, dx, dz in DIRS4)]
    if not bank:
        return None
    # the notch goes on the far side from the island's middle, so the water leaves outward
    out = max(bank, key=lambda c: math.hypot(c[0] - cx, c[1] - cz))
    x, z = out
    for y in range(water_y, surf[out] + 1):
        w.cells.pop((x, y, z), None)
    w.put(x, water_y - 1, z, "mossy_cobblestone")
    w.put(x, water_y, z, "water", level="0")
    # and clear the lip outward so it spills off the island rather than pooling on it
    for _, dx, dz in DIRS4:
        n = (x + dx, z + dz)
        if n in surf or n in lake:
            continue
        for y in range(water_y - 1, water_y + 2):
            w.cells.pop((n[0], y, n[1]), None)
    return [x, water_y, z]


def _vines(w: World, surf: dict, p, seed) -> int:
    """Strands off the underside rim so the island hangs rather than floats."""
    lo, hi = p["vine_len"]
    n = 0
    for c in surf:
        if all((c[0] + dx, c[1] + dz) in surf for _, dx, dz in DIRS4):
            continue
        for dx, dz, facing in ((1, 0, "west"), (-1, 0, "east"), (0, 1, "north"), (0, -1, "south")):
            if (c[0] + dx, c[1] + dz) in surf or hash01(c[0], c[1], 43, seed) >= p["vine_rate"]:
                continue
            y = min(yy for (xx, yy, zz) in w.cells if (xx, zz) == c) if any(
                (xx, zz) == c for (xx, yy, zz) in w.cells) else surf[c]
            L = lo + int(hash01(c[0], c[1], 47, seed) * (hi - lo + 1))
            props = {"east": "false", "north": "false", "south": "false", "west": "false", "up": "false"}
            props[facing] = "true"
            for k in range(L):
                if w.has(c[0] + dx, y - k, c[1] + dz):
                    break
                w.put(c[0] + dx, y - k, c[1] + dz, "vine", **props)
                n += 1
            break
    return n


def _lanterns(w: World, surf: dict, lake: set, water_y: int, p) -> int:
    """Greedy cover over the dry land: nothing at this depth sees the sun."""
    reach = int(p["lantern_reach"])
    if reach <= 0:
        return 0
    dry = [c for c in surf if c not in lake and not w.has(c[0], surf[c] + 1, c[1])]
    need = set(surf)
    lit = 0
    while need and dry:
        best = max(dry, key=lambda c: sum(1 for d in need
                                          if abs(c[0] - d[0]) + abs(c[1] - d[1]) <= reach))
        covered = {d for d in need if abs(best[0] - d[0]) + abs(best[1] - d[1]) <= reach}
        if not covered:
            break
        w.put(best[0], surf[best] + 1, best[1], "lantern", hanging="false", waterlogged="false")
        lit += 1
        need -= covered
        dry.remove(best)
    return lit


def _pick(table, x, y, z, seed) -> str:
    h = hash01(x, y, z, 53, seed)
    acc = 0.0
    for name, weight in table:
        acc += weight
        if h < acc:
            return name
    return table[-1][0]
