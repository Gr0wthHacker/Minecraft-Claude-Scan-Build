"""Pond garden kit — a raised spring pool plus small scatter pieces.

Constraint that shaped it: you cannot dig (a workspace sits 1 below the
surface), so the pond is a RAISED BASIN: a mossy-stone rim wall built up
2 from the surface with the water sitting on a sealed floor at y+1. Reads
as a natural spring pool, not a hole.

Pieces (each is its own generator so they paste independently):
  pond       raised basin, water, lily pads, dripleaf, a stone-slab step,
             pier + lantern post, a big frog on a lily pad
  bench      log bench under a lantern post (2 variants: straight / L)
  planter    raised herb bed: trapdoor sides, moss+flowers, 3x3 / 3x5
  well       stone-rim wishing well with a spruce roof, chain + bucket
  lamp       standalone lantern post (fence + trapdoor cap + lantern)
  scatter    a sprinkle of azalea bushes, moss carpet, flowers, rocks

Everything sits ON y0 (= your moss surface). Nothing goes below y0.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

# ---------------------------------------------------------------- shared

def _states(c: Canvas) -> dict:
    return {
        "moss": c.state("moss_block"), "carpet": c.state("moss_carpet"),
        "mosscobble": c.state("mossy_cobblestone"), "cobble": c.state("cobblestone"),
        "mossbrick": c.state("mossy_stone_bricks"), "stone": c.state("stone"),
        "cobble_slab": c.state("cobblestone_slab", type="bottom", waterlogged="false"),
        "stone_slab": c.state("smooth_stone_slab", type="bottom", waterlogged="false"),
        "mosscobble_stairs": c.state("mossy_cobblestone_stairs", facing="north", half="bottom",
                                     shape="straight", waterlogged="false"),
        "water": c.state("water", level="0"),
        "lily": c.raw_state("lily_pad"),
        "dripleaf": c.raw_state("big_dripleaf", facing="north", tilt="none", waterlogged="false"),
        "dripleaf_stem": c.raw_state("big_dripleaf_stem", facing="north", waterlogged="false"),
        "cane": c.raw_state("sugar_cane", age="0"),
        "planks": c.state("oak_planks"), "slab": c.state("oak_slab", type="bottom", waterlogged="false"),
        "log": c.state("oak_log", axis="y"), "log_x": c.state("oak_log", axis="x"), "log_z": c.state("oak_log", axis="z"),
        "slog": c.state("spruce_log", axis="y"),
        "fence": c.state("oak_fence", north="false", south="false", east="false", west="false", waterlogged="false"),
        "sfence": c.state("spruce_fence", north="false", south="false", east="false", west="false", waterlogged="false"),
        "trap": c.state("spruce_trapdoor", facing="north", half="top", open="false", powered="false", waterlogged="false"),
        "trap_open_n": c.raw_state("spruce_trapdoor", facing="north", half="bottom", open="true", powered="false", waterlogged="false"),
        "trap_open_s": c.raw_state("spruce_trapdoor", facing="south", half="bottom", open="true", powered="false", waterlogged="false"),
        "trap_open_e": c.raw_state("spruce_trapdoor", facing="east", half="bottom", open="true", powered="false", waterlogged="false"),
        "trap_open_w": c.raw_state("spruce_trapdoor", facing="west", half="bottom", open="true", powered="false", waterlogged="false"),
        "chain": c.state("chain", axis="y", waterlogged="false"),
        "lant": c.state("lantern", hanging="false", waterlogged="false"),
        "lant_h": c.state("lantern", hanging="true", waterlogged="false"),
        "azalea": c.state("azalea"), "fazalea": c.state("flowering_azalea"),
        "daisy": c.state("oxeye_daisy"), "allium": c.state("allium"), "orchid": c.state("blue_orchid"),
        "petals": c.state("pink_petals", facing="north", flower_amount="3", waterlogged="false"),
        "berry": c.state("sweet_berry_bush", age="3"),
        "green": c.state("lime_wool"), "dark": c.state("green_wool"), "belly": c.state("yellow_wool"),
        "black": c.state("black_wool"), "white": c.state("white_wool"),
        "spruce_slab": c.state("spruce_slab", type="bottom", waterlogged="false"),
        "spruce_stairs_n": c.state("spruce_stairs", facing="north", half="bottom", shape="straight", waterlogged="false"),
        "spruce_stairs_s": c.state("spruce_stairs", facing="south", half="bottom", shape="straight", waterlogged="false"),
        "spruce_stairs_e": c.state("spruce_stairs", facing="east", half="bottom", shape="straight", waterlogged="false"),
        "spruce_stairs_w": c.state("spruce_stairs", facing="west", half="bottom", shape="straight", waterlogged="false"),
        "cobble_wall": c.state("cobblestone_wall", up="true", north="none", south="none", east="none", west="none", waterlogged="false"),
        "barrel": c.state("barrel", facing="up", open="false"),
        "campfire": c.state("campfire", facing="north", lit="true", signal_fire="false", waterlogged="false"),
    }


def _lamp_post(c, S, x, z, h=3):
    for y in range(0, h):
        c.put(x, y, z, S["fence"])
    c.put(x, h, z, S["trap"])
    c.put(x, h - 1, z, S["fence"])
    # lantern hangs one out from the post top: use a slab cap + hanging lantern beside
    c.put(x, h, z, S["slab"])
    c.put(x, h - 1, z, S["fence"])
    c.put(x, h, z + 1, S["slab"])
    c.put(x, h - 1, z + 1, S["lant_h"])


# ---------------------------------------------------------------- pond

POND_DEFAULTS = {"size": [17, 8, 17], "rx": 6.5, "rz": 5.5, "rim_h": 2, "frog": True, "pier": True, "seed": 0}


def build_pond(cfg: dict, donors=None) -> Canvas:
    p = {**POND_DEFAULTS, **cfg}
    SX, SY, SZ = p["size"]; CX, CZ = SX / 2.0, SZ / 2.0
    RX, RZ = float(p["rx"]), float(p["rz"]); H = int(p["rim_h"]); seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors); S = _states(c)

    def ell(x, z, rx, rz):
        return ((x + 0.5 - CX) / rx) ** 2 + ((z + 0.5 - CZ) / rz) ** 2

    # sealed floor at y0 across the basin, rim wall y0..H, water y1..H inside
    for z in range(SZ):
        for x in range(SX):
            e = ell(x, z, RX, RZ)
            jitter = 0.10 * (hash01(x, z, 3, seed) - 0.5)
            if e <= 1.0 + jitter:
                inner = e <= (1.0 - 0.32) + jitter
                if inner:
                    c.put(x, 0, z, S["mosscobble"] if hash01(x, z, 5, seed) < 0.6 else S["stone"])
                    for y in range(1, H + 1):
                        c.put(x, y, z, S["water"])
                else:
                    # rim: mossy cobble core, varied top (slab / full / stairs-ish)
                    for y in range(0, H + 1):
                        c.put(x, y, z, S["mosscobble"] if hash01(x, y, z, 7, seed) < 0.55
                              else (S["cobble"] if hash01(x, y, z, 9, seed) < 0.5 else S["mossbrick"]))
                    top = hash01(x, z, 11, seed)
                    if top < 0.35:
                        c.put(x, H + 1, z, S["cobble_slab"])
                    elif top < 0.50:
                        c.put(x, H + 1, z, S["carpet"])
    # water surface dressing
    for z in range(SZ):
        for x in range(SX):
            if c.get(x, H, z) == S["water"]:
                h = hash01(x, z, 13, seed)
                if h < 0.14:
                    c.put(x, H + 1, z, S["lily"])
                elif h < 0.19 and c.get(x, H, z - 1) != S["water"]:
                    c.put(x, H + 1, z, S["dripleaf_stem"]); c.put(x, H + 2, z, S["dripleaf"])
    # cane and dripleaf on the rim's inner shoulder
    for z in range(SZ):
        for x in range(SX):
            if c.get(x, H, z) != S["water"] and c.get(x, H, z) != 0 and c.get(x, H + 1, z) == 0:
                near_water = any(c.get(x + dx, H, z + dz) == S["water"] for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if near_water and hash01(x, z, 17, seed) < 0.18:
                    for i in range(1, 3 + int(hash01(x, z, 19, seed) * 2)):
                        c.put(x, H + i, z, S["cane"])
    # a low step on the front (+z) so you can walk up to the water
    sx0 = int(CX) - 1
    for x in range(sx0, sx0 + 3):
        z = int(CZ + RZ) - 1
        c.put(x, H + 1, z, 0)
        c.put(x, H, z, S["mosscobble_stairs"])
    # pier: 2 wide, from the rim out over the water on the +x side, lantern post at the end
    if p["pier"]:
        z0 = int(CZ) - 1
        x_end = int(CX + RX) - 1                    # on the rim (+x side)
        x_start = x_end - 5                          # reaches 5 in over the water
        for x in range(x_start, x_end + 1):
            for z in (z0, z0 + 1):
                c.put(x, H + 1, z, S["planks"] if (x - x_start) % 2 else S["slab"])
        for z in (z0, z0 + 1):                       # posts into the water at the tip
            for y in range(1, H + 1):
                if c.get(x_start, y, z) == S["water"]:
                    c.put(x_start, y, z, S["sfence"])
        # lantern post at the tip
        c.put(x_start, H + 2, z0, S["fence"]); c.put(x_start, H + 3, z0, S["fence"])
        c.put(x_start, H + 4, z0, S["slab"]); c.put(x_start, H + 4, z0 + 1, S["slab"])
        c.put(x_start, H + 3, z0 + 1, S["lant_h"])
    # frog on a lily pad in the middle-left
    if p["frog"]:
        fx, fz = int(CX - 3), int(CZ) - 1            # body spans fx..fx+2, fz..fz+2 ; faces +z
        for x in range(fx - 1, fx + 4):
            for z in range(fz - 1, fz + 3):
                if c.get(x, H, z) == S["water"] and hash01(x, z, 47, seed) < 0.6:
                    c.put(x, H + 1, z, S["lily"])
        for x in range(fx, fx + 3):                  # sit the frog on a solid pad row (its own body base)
            for z in range(fz, fz + 3):
                c.put(x, H + 1, z, S["lily"])
        for x in range(fx, fx + 3):                  # body 3x3
            for z in range(fz, fz + 3):
                c.put(x, H + 2, z, S["green"])
        for x in range(fx, fx + 3):                  # yellow throat / belly band on the front face
            c.put(x, H + 2, fz + 2, S["belly"])
        for x in (fx, fx + 2):                       # eye bumps: green with black front
            c.put(x, H + 3, fz + 1, S["green"])
            c.put(x, H + 3, fz + 2, S["black"])
        c.put(fx + 1, H + 3, fz + 1, S["dark"])      # brow ridge between the eyes
        c.put(fx - 1, H + 2, fz + 2, S["green"]); c.put(fx + 3, H + 2, fz + 2, S["green"])   # front feet
        c.put(fx - 1, H + 2, fz, S["dark"]); c.put(fx + 3, H + 2, fz, S["dark"])              # haunches
    return c


# ---------------------------------------------------------------- small pieces

def build_bench(cfg: dict, donors=None) -> Canvas:
    p = {"variant": "straight", **cfg}
    c = Canvas(7, 5, 5, donors); S = _states(c)
    # log seat 4 long on two stump legs, lamp post beside
    for x in range(1, 5):
        c.put(x, 1, 2, S["log_x"])
    c.put(1, 0, 2, S["slog"]); c.put(4, 0, 2, S["slog"])
    if p["variant"] == "L":
        for z in range(2, 5):
            c.put(1, 1, z, S["log_z"])
    _lamp_post(c, S, 5, 1, h=3)
    c.put(0, 0, 3, S["azalea"]); c.put(3, 0, 4, S["carpet"])
    return c


def build_planter(cfg: dict, donors=None) -> Canvas:
    p = {"w": 3, "d": 5, "seed": 0, **cfg}
    W, D = int(p["w"]), int(p["d"]); seed = int(p["seed"])
    c = Canvas(W + 2, 4, D + 2, donors); S = _states(c)
    # raised bed: log corners, trapdoor sides, moss fill, flowers/berries on top
    for z in range(1, D + 1):
        for x in range(1, W + 1):
            c.put(x, 0, z, S["moss"])
    for x in range(1, W + 1):
        c.put(x, 0, 0, S["trap_open_n"]); c.put(x, 0, D + 1, S["trap_open_s"])
    for z in range(1, D + 1):
        c.put(0, 0, z, S["trap_open_w"]); c.put(W + 1, 0, z, S["trap_open_e"])
    for x, z in ((0, 0), (W + 1, 0), (0, D + 1), (W + 1, D + 1)):
        c.put(x, 0, z, S["log"])
    for z in range(1, D + 1):
        for x in range(1, W + 1):
            h = hash01(x, z, 23, seed)
            c.put(x, 1, z, S["berry"] if h < 0.25 else S["allium"] if h < 0.45 else
                  S["daisy"] if h < 0.62 else S["orchid"] if h < 0.75 else S["fazalea"] if h < 0.85 else 0)
    return c


def build_well(cfg: dict, donors=None) -> Canvas:
    c = Canvas(5, 7, 5, donors); S = _states(c)
    # 3x3 mossy cobble ring, water inside, spruce posts + slab roof, chain + lantern
    for z in range(1, 4):
        for x in range(1, 4):
            if (x, z) == (2, 2):
                c.put(x, 0, z, S["water"])
            else:
                c.put(x, 0, z, S["mosscobble"] if hash01(x, z, 29) < 0.6 else S["cobble"])
    for x, z in ((1, 1), (3, 3)):
        c.put(x, 1, z, S["cobble_wall"])
    for x, z in ((1, 3), (3, 1)):
        for y in (1, 2, 3):
            c.put(x, y, z, S["sfence"])
    for z in range(0, 5):
        for x in range(0, 5):
            edge = x in (0, 4) or z in (0, 4)
            c.put(x, 4, z, S["spruce_stairs_n"] if z == 0 else S["spruce_stairs_s"] if z == 4 else
                  S["spruce_stairs_w"] if x == 0 else S["spruce_stairs_e"] if x == 4 else S["spruce_slab"])
    c.put(2, 5, 2, S["spruce_slab"])
    c.put(2, 3, 2, S["chain"]); c.put(2, 2, 2, S["lant_h"])
    return c


def build_lamp(cfg: dict, donors=None) -> Canvas:
    c = Canvas(3, 5, 3, donors); S = _states(c)
    _lamp_post(c, S, 1, 1, h=3)
    return c


def build_scatter(cfg: dict, donors=None) -> Canvas:
    p = {"size": [9, 3, 9], "density": 0.35, "seed": 0, **cfg}
    SX, SY, SZ = p["size"]; seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors); S = _states(c)
    for z in range(SZ):
        for x in range(SX):
            h = hash01(x, z, 31, seed)
            if h > p["density"]:
                continue
            k = hash01(x, z, 37, seed)
            if k < 0.30:
                c.put(x, 0, z, S["carpet"])
            elif k < 0.48:
                c.put(x, 0, z, S["azalea"])
            elif k < 0.58:
                c.put(x, 0, z, S["fazalea"])
            elif k < 0.72:
                c.put(x, 0, z, S["daisy"] if hash01(x, z, 41, seed) < 0.5 else S["allium"])
            elif k < 0.85:
                c.put(x, 0, z, S["mosscobble"])
                if hash01(x, z, 43, seed) < 0.4:
                    c.put(x, 1, z, S["carpet"])
            else:
                c.put(x, 0, z, S["petals"])
    return c
