"""Dug-in spring pool using exactly THREE layers.

    y0  = surface-1  pool bed (dark), gravel/sand ring at the bed edge, and the
                     stone footing under the shore
    y1  = surface    the WATERLINE: water inside; an irregular stone/moss shore
                     ring outside; slabs + stairs stepping down into the water;
                     nothing built up -- the water is flush with your moss
    y2  = surface+1  dressing only: lily pads, dripleaf, cane, moss carpet,
                     azalea, a sitting log, a lantern, the frog

Paste with the schematic's y0 ONE BLOCK BELOW your moss surface. Cells the
schematic leaves as air are not touched on your island (Litematica pastes
air as air only if you tell it to; default replace mode replaces -- use
"paste replace: none/all" as you prefer; the kit is designed so air outside
the shore is your existing moss).

Why it reads "dug": the shore is at surface height and the water is at
surface height. Nothing rises above the ground except plants and a log.
"""
from __future__ import annotations

from .canvas import Canvas, hash01

DEFAULTS = {
    "size": [19, 3, 15],
    "rx": 6.6, "rz": 4.9,           # water half-axes at the surface
    "shore": 2.0,                   # shore ring width beyond the water (blocks)
    "frog": True, "post": True, "spring": True, "sitting_log": True,
    "seed": 0,
}

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    SX, SY, SZ = p["size"]
    CX, CZ = SX / 2.0, SZ / 2.0
    RX, RZ = float(p["rx"]), float(p["rz"])
    SH = float(p["shore"]) / min(RX, RZ)
    seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors)

    st = lambda n, **k: c.state(n, **k)
    raw = lambda n, **k: c.raw_state(n, **k)
    WATER = st("water", level="0")
    BED = raw("clay")   # was mud: dirt-derived, and dirt is CURRENCY here (rule 16)
    GRAVEL = st("gravel"); SAND = raw("sand")
    STONE = st("stone"); COB = st("cobblestone"); MCOB = st("mossy_cobblestone")
    MOSS = st("moss_block"); CARPET = st("moss_carpet")
    COB_SLAB = st("cobblestone_slab", type="bottom", waterlogged="false")
    SS_SLAB_WL = raw("smooth_stone_slab", type="bottom", waterlogged="true")
    COB_SLAB_WL = raw("cobblestone_slab", type="bottom", waterlogged="true")
    STAIR = {d: raw("mossy_cobblestone_stairs", facing=d, half="bottom", shape="straight", waterlogged="false")
             for d in ("north", "south", "east", "west")}
    LILY = raw("lily_pad"); DRIPLEAF = raw("big_dripleaf", facing="north", tilt="none", waterlogged="false")
    CANE = raw("sugar_cane", age="0"); AZALEA = st("azalea"); FAZALEA = st("flowering_azalea")
    LOG_Z = st("oak_log", axis="z"); LANT = st("lantern", hanging="false", waterlogged="false")
    GREEN = st("lime_wool"); DARK = st("green_wool"); YEL = st("yellow_wool"); BLACK = st("black_wool")

    def r_of(x, z):
        ax = abs(x + 0.5 - CX) / RX
        az = abs(z + 0.5 - CZ) / RZ
        n = 2.6
        return (ax ** n + az ** n) ** (1.0 / n) + 0.09 * (hash01(x, z, 3, seed) - 0.5)

    water, shore = {}, {}
    for z in range(SZ):
        for x in range(SX):
            r = r_of(x, z)
            if r <= 1.0:
                water[(x, z)] = r
            elif r <= 1.0 + SH:
                shore[(x, z)] = r

    # ---------------------------------------------------------------- y0 bed
    for (x, z), r in water.items():
        h = hash01(x, z, 5, seed)
        if r > 0.80:
            c.put(x, 0, z, GRAVEL if h < 0.6 else SAND)
        else:
            c.put(x, 0, z, BED if h < 0.5 else MCOB if h < 0.82 else STONE)
    for (x, z), r in shore.items():
        c.put(x, 0, z, STONE if hash01(x, z, 6, seed) < 0.7 else MCOB)

    # ---------------------------------------------------------------- y1 waterline
    for (x, z), r in water.items():
        c.put(x, 1, z, WATER)
    facing_from = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
    opposite = {"east": "west", "west": "east", "north": "south", "south": "north"}
    for (x, z), r in shore.items():
        h = hash01(x, z, 7, seed)
        near = [(dx, dz) for dx, dz in DIRS4 if (x + dx, z + dz) in water]
        if near and h < 0.50:
            # a step DOWN into the water: stairs whose back faces the water
            f = facing_from[near[0]]
            c.put(x, 1, z, STAIR[opposite[f]] if h < 0.28 else COB_SLAB)
        else:
            c.put(x, 1, z, MCOB if h < 0.30 else MOSS if h < 0.75 else COB if h < 0.90 else STONE)
    # shallows: waterlogged slabs just inside the waterline
    for (x, z), r in water.items():
        if r > 0.85 and hash01(x, z, 11, seed) < 0.24:
            c.put(x, 1, z, SS_SLAB_WL if hash01(x, z, 13, seed) < 0.5 else COB_SLAB_WL)

    # ---------------------------------------------------------------- spring inlet (-z)
    if p["spring"]:
        for x in (int(CX) - 1, int(CX), int(CX) + 1):
            zs = [z for (xx, z) in shore if xx == x and z < CZ]
            if not zs:
                continue
            z = max(zs)                                # shore cell nearest the water on the -z side
            c.put(x, 1, z, STAIR["north"])             # step rising away from the water
            if (x, z - 1) in shore:
                c.put(x, 1, z - 1, MCOB)               # solid footing behind the step
                c.put(x, 2, z - 1, MCOB if x == int(CX) else COB_SLAB)   # low source stones

    # ---------------------------------------------------------------- y2 dressing
    for (x, z), r in water.items():
        if c.get(x, 1, z) != WATER:
            continue
        h = hash01(x, z, 17, seed)
        if h < 0.11 and r < 0.9:
            c.put(x, 2, z, LILY)
        elif h < 0.145 and 0.6 < r < 0.95:
            c.put(x, 2, z, DRIPLEAF)
    for (x, z), r in shore.items():
        if c.get(x, 2, z) != 0:
            continue
        top = c.get(x, 1, z)
        near_w = any((x + dx, z + dz) in water for dx, dz in DIRS4)
        h = hash01(x, z, 19, seed)
        if near_w and h < 0.30 and top == MOSS:
            c.put(x, 2, z, CANE)
        elif top == MOSS and h < 0.32:
            c.put(x, 2, z, CARPET if h < 0.18 else AZALEA if h < 0.27 else FAZALEA)
        elif top in (COB, STONE) and h < 0.36:
            c.put(x, 2, z, COB_SLAB)                   # low boulder
    # sitting log on the +x shore
    if p["sitting_log"]:
        for (x, z), r in sorted(shore.items(), key=lambda kv: -kv[0][0]):
            if abs(z + 0.5 - CZ) < 1.2 and c.get(x, 2, z) == 0 and c.get(x, 2, z + 1) == 0 \
                    and c.get(x, 1, z) in (MOSS, MCOB, COB, STONE) and c.get(x, 1, z + 1) in (MOSS, MCOB, COB, STONE):
                c.put(x, 2, z, LOG_Z); c.put(x, 2, z + 1, LOG_Z)
                break
    # standing lantern on the -x shore
    if p["post"]:
        for (x, z), r in sorted(shore.items(), key=lambda kv: kv[0][0]):
            if abs(z + 0.5 - CZ) < 1.2 and c.get(x, 2, z) == 0 and c.get(x, 1, z) in (MOSS, MCOB, COB, STONE):
                c.put(x, 2, z, LANT)
                break
    # frog: 3x3 lime body on a pad of waterlogged slabs AT the waterline, near +z shore
    if p["frog"]:
        fx, fz = int(CX) - 4, int(CZ) - 1
        for x in range(fx - 1, fx + 4):
            for z in range(fz - 1, fz + 3):
                if c.get(x, 1, z) == WATER and c.get(x, 2, z) == 0 and hash01(x, z, 47, seed) < 0.5:
                    c.put(x, 2, z, LILY)
        for x in range(fx, fx + 3):
            for z in range(fz, fz + 3):
                if c.get(x, 1, z) in (WATER, SS_SLAB_WL, COB_SLAB_WL):
                    c.put(x, 1, z, SS_SLAB_WL)
                    c.put(x, 2, z, GREEN)
        # front row: black eye corners, yellow throat centre
        if c.get(fx, 2, fz + 2) == GREEN:
            c.put(fx, 2, fz + 2, BLACK)
        if c.get(fx + 2, 2, fz + 2) == GREEN:
            c.put(fx + 2, 2, fz + 2, BLACK)
        if c.get(fx + 1, 2, fz + 2) == GREEN:
            c.put(fx + 1, 2, fz + 2, YEL)
        if c.get(fx + 1, 2, fz + 1) == GREEN:
            c.put(fx + 1, 2, fz + 1, DARK)             # back stripe
    return c
