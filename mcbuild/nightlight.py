"""Block light, and what a mob can stand on: ONE source for every tool that asks.

The lowland glow, the island night pass, the solver that produced them and the tests that pin
them all have to agree about three things - what light passes through, what emits it, and what
counts as a surface a mob can spawn on. They were three separate copies for one session and
that was long enough to matter: the solver's set held `dead_bush` and the test's did not, so
the test saw walkable cells the solver had never considered and reported three dark spots in a
design the solver called finished. Neither was wrong; they were measuring different islands.

Same rule as `proportions.measure` / `rubric.score` and as `export_rules.py`: one source, so
two tools cannot drift.

The classifier that matters most is `surface`, and it is the one this project keeps getting
wrong. A column's walking surface is its TOPMOST standable cell. Taking the LOWEST grades the
buried seams under the massif fill as floor and reports the island as three-quarters dark; it
has misled three separate passes now.
"""
from __future__ import annotations

import numpy as np

from . import blocks

# Light goes through these, and nothing stands on them.
PASSY = {
    "air", "cave_air", "void_air", "vine", "moss_carpet", "short_grass", "tall_grass",
    "fern", "large_fern", "azalea", "flowering_azalea", "glow_lichen", "hanging_roots",
    "small_dripleaf", "big_dripleaf", "spore_blossom", "poppy", "dandelion", "cornflower",
    "oxeye_daisy", "lily_of_the_valley", "allium", "torchflower", "pink_petals",
    "sugar_cane", "bamboo", "bamboo_sapling", "kelp", "kelp_plant", "seagrass",
    "tall_seagrass", "lily_pad", "twisting_vines", "twisting_vines_plant", "weeping_vines",
    "weeping_vines_plant", "cave_vines", "cave_vines_plant", "sculk_vein", "tripwire",
    "rail", "powered_rail", "detector_rail", "activator_rail", "redstone_wire", "lever",
    "tripwire_hook", "wheat", "carrots", "potatoes", "beetroots", "sweet_berry_bush",
    "cocoa", "brown_mushroom", "red_mushroom", "crimson_roots", "warped_roots",
    "nether_sprouts", "snow", "dead_bush", "sunflower", "lilac", "rose_bush", "peony",
}

# What a block gives off. Values are vanilla light levels.
EMIT = {
    "lantern": 15, "soul_lantern": 10, "glow_lichen": 7, "amethyst_cluster": 5,
    "ochre_froglight": 15, "verdant_froglight": 15, "pearlescent_froglight": 15,
    "sea_pickle": 6, "torch": 14, "wall_torch": 14, "soul_torch": 10, "soul_wall_torch": 10,
    "campfire": 15, "soul_campfire": 10, "glowstone": 15, "shroomlight": 15,
    "sea_lantern": 15, "jack_o_lantern": 15, "redstone_lamp": 15, "beacon": 15,
    "conduit": 15, "end_rod": 14, "candle": 3, "lava": 15, "magma_block": 3,
    "crying_obsidian": 10, "furnace": 13, "smoker": 13, "blast_furnace": 13,
    "brewing_stand": 1, "enchanting_table": 7, "ender_chest": 7, "small_amethyst_bud": 1,
    "medium_amethyst_bud": 2, "large_amethyst_bud": 4, "cave_vines": 14,
    "cave_vines_plant": 14,
}

WATERY = ("water", "bubble_column")
MAX_LIGHT = 15


def _full_cube(b, cache):
    if b not in cache:
        try:
            cache[b] = blocks.is_full_cube(b)
        except Exception:
            cache[b] = False
    return cache[b]


def classify(states):
    """`states` is a list of block states indexed the way an id array indexes it.

    Returns five parallel arrays over that palette: opaque, emit, passy, spawn, water.
    `spawn` is "could a mob stand ON this" - which for a slab means the top half only.
    """
    cache = {}
    n = len(states)
    opaque = np.zeros(n, bool)
    emit = np.zeros(n, np.int16)
    passy = np.zeros(n, bool)
    spawn = np.zeros(n, bool)
    water = np.zeros(n, bool)
    for i, st in enumerate(states):
        b = st.split(":")[-1].split("[")[0]
        emit[i] = EMIT.get(b, 0)
        passy[i] = b in PASSY
        water[i] = b in WATERY
        if passy[i] or water[i]:
            continue
        opaque[i] = _full_cube(b, cache)
        spawn[i] = ("type=top" in st or "type=double" in st) if b.endswith("_slab") \
            else opaque[i]
    return opaque, emit, passy, spawn, water


def propagate(opaque, emit):
    """Block light through a 3-D (y, z, x) volume. Iterated max-filter rather than a queue:
    light caps at 15 so it converges in at most that many rounds, and numpy does it in a
    fraction of the time a per-cell BFS over two million cells takes."""
    light = emit.copy()
    for _ in range(MAX_LIGHT):
        nxt = light.copy()
        for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)):
            rolled = np.roll(light, sh, axis=ax) - 1
            edge = [slice(None)] * 3
            edge[ax] = 0 if sh == 1 else -1
            rolled[tuple(edge)] = 0          # np.roll WRAPS; the far plane is not a neighbour
            np.maximum(nxt, rolled, out=nxt)
        nxt[opaque] = emit[opaque]
        if np.array_equal(nxt, light):
            break
        light = nxt
    return light


def surface(passy, spawn, water):
    """Every column's walking surface: the air cell above its TOPMOST standable block, with
    two passable cells for a mob to occupy and no water in them.

    Topmost, never lowest - see the module docstring. Returns {(x, y, z) index tuple: True}
    in ARRAY indices, so the caller adds its own origin.
    """
    NY, NZ, NX = passy.shape
    out = {}
    for z in range(NZ):
        for x in range(NX):
            ys = np.nonzero(spawn[:, z, x])[0]
            for iy in ys[::-1]:
                if iy + 2 >= NY:
                    continue
                if not (passy[iy + 1, z, x] and passy[iy + 2, z, x]):
                    continue
                if water[iy + 1, z, x]:
                    continue
                out[(x, iy + 1, z)] = True
                break
    return out
