"""Block palette knowledge: colours, cost tiers, substitutions, donor borrowing.

COST TIERS (skyblock economy, from experience on this server):
  cheap      renewable / farmable: wool, snow, moss, logs/planks/wood,
             cobble, stone, stone brick family, dirt, leaves, vines,
             lanterns/chains, glow berries, dripstone
  ok         needs some grind but fine in small counts: iron bars, glass panes,
             smooth stone, andesite/tuff, quartz slabs...
  expensive  DO NOT bulk-use: terracotta (10 grass each), concrete, quartz,
             glass blocks, prismarine, purpur, copper

`cheapen()` maps expensive -> cheap by hue, so a build's look survives.
"""
from __future__ import annotations

import numpy as np

from . import nbt
from .nbt import Tag

# ------------------------------------------------------------- colours (RGB)
# Approximate top-face colours; used only for renders and image matching.
COLORS: dict[str, tuple[int, int, int]] = {
    "air": (255, 255, 255),
    # whites / grays
    "snow_block": (240, 245, 247), "white_wool": (234, 236, 237), "white_concrete": (207, 213, 214),
    "white_terracotta": (209, 178, 161), "quartz_block": (236, 233, 226), "bone_block": (229, 225, 205),
    "light_gray_wool": (142, 142, 134), "light_gray_concrete": (125, 125, 115),
    "light_gray_terracotta": (135, 106, 97), "gray_wool": (62, 68, 71), "gray_concrete": (54, 57, 61),
    "gray_terracotta": (57, 42, 35), "black_wool": (20, 21, 25), "black_concrete": (8, 10, 15),
    "black_terracotta": (37, 22, 16),
    # stone family
    "stone": (126, 126, 126), "cobblestone": (127, 127, 127), "mossy_cobblestone": (100, 112, 85),
    "stone_bricks": (122, 122, 122), "mossy_stone_bricks": (110, 118, 100),
    "cracked_stone_bricks": (105, 105, 105), "chiseled_stone_bricks": (120, 120, 120),
    "smooth_stone": (158, 158, 158), "andesite": (136, 136, 136), "polished_andesite": (132, 134, 132),
    "diorite": (188, 188, 190), "granite": (149, 103, 85), "tuff": (108, 109, 102),
    "tuff_bricks": (108, 102, 94), "deepslate": (80, 80, 82), "deepslate_bricks": (70, 70, 72),
    "cobbled_deepslate": (77, 77, 80), "polished_tuff": (110, 112, 104),
    # earth
    "dirt": (134, 96, 67), "coarse_dirt": (119, 85, 59), "rooted_dirt": (144, 103, 76),
    "podzol": (90, 60, 30), "grass_block": (95, 159, 53), "moss_block": (89, 109, 45),
    "moss_carpet": (99, 121, 50), "mud": (60, 57, 60), "clay": (160, 166, 179),
    # wood
    "oak_log": (109, 85, 50), "oak_wood": (109, 85, 50), "stripped_oak_log": (160, 130, 80),
    "stripped_oak_wood": (160, 130, 80), "oak_planks": (162, 130, 78), "oak_slab": (162, 130, 78),
    "oak_stairs": (162, 130, 78), "oak_fence": (162, 130, 78), "oak_trapdoor": (140, 110, 66),
    "spruce_log": (58, 37, 16), "spruce_wood": (58, 37, 16), "spruce_planks": (114, 84, 48),
    "spruce_stairs": (114, 84, 48), "spruce_slab": (114, 84, 48), "spruce_fence": (114, 84, 48),
    "spruce_trapdoor": (114, 84, 48), "spruce_door": (114, 84, 48),
    "dark_oak_planks": (66, 43, 20), "dark_oak_slab": (66, 43, 20), "dark_oak_stairs": (66, 43, 20),
    "dark_oak_fence": (66, 43, 20), "dark_oak_log": (60, 40, 20), "birch_planks": (192, 175, 121),
    "birch_log": (216, 215, 210), "jungle_log": (85, 67, 25), "acacia_log": (103, 96, 86),
    "cherry_log": (55, 33, 44), "cherry_planks": (227, 178, 172), "cherry_leaves": (240, 170, 200),
    "mangrove_log": (84, 66, 41),
    # foliage
    "oak_leaves": (60, 143, 40), "azalea_leaves": (90, 112, 44), "flowering_azalea_leaves": (150, 160, 90),
    "spruce_leaves": (40, 90, 40), "birch_leaves": (128, 167, 85), "azalea": (101, 124, 47),
    "flowering_azalea": (180, 130, 160), "short_grass": (94, 157, 52), "tall_grass": (94, 157, 52),
    "fern": (90, 140, 60), "vine": (52, 90, 35), "hanging_roots": (140, 110, 80),
    "cave_vines": (96, 180, 88), "cave_vines_plant": (80, 120, 50), "big_dripleaf": (110, 150, 60),
    "pink_petals": (230, 150, 180), "oxeye_daisy": (225, 225, 225), "white_tulip": (225, 228, 225),
    "azure_bluet": (210, 215, 220), "blue_orchid": (48, 144, 240), "allium": (180, 120, 220),
    "lily_of_the_valley": (232, 240, 232),
    # light / misc
    "lantern": (245, 190, 90), "soul_lantern": (90, 190, 200), "chain": (60, 65, 75),
    "iron_chain": (60, 65, 75), "torch": (255, 200, 90), "wall_torch": (255, 200, 90),
    "glowstone": (200, 160, 80), "shroomlight": (240, 150, 80), "sea_lantern": (170, 220, 210),
    "campfire": (200, 120, 40), "pointed_dripstone": (134, 107, 92), "dripstone_block": (134, 107, 92),
    "iron_bars": (150, 150, 150), "ladder": (150, 120, 78), "chest": (162, 130, 78),
    "barrel": (130, 100, 60), "flower_pot": (120, 70, 50), "water": (63, 118, 228),
    "gold_block": (246, 208, 61), "tnt": (219, 66, 30), "glass": (200, 230, 235),
    "glass_pane": (200, 230, 235), "white_stained_glass": (255, 255, 255),
    "stone_pressure_plate": (125, 125, 125), "stone_button": (125, 125, 125),
    # colour families: wool / concrete / terracotta
    "orange_wool": (240, 118, 19), "orange_concrete": (224, 97, 0), "orange_terracotta": (161, 83, 37),
    "yellow_wool": (248, 197, 39), "yellow_concrete": (241, 175, 21), "yellow_terracotta": (186, 133, 35),
    "lime_wool": (112, 185, 25), "lime_concrete": (94, 168, 24), "lime_terracotta": (103, 117, 52),
    "green_wool": (84, 109, 27), "green_concrete": (73, 91, 36), "green_terracotta": (76, 83, 42),
    "cyan_wool": (21, 137, 145), "cyan_concrete": (21, 119, 136), "cyan_terracotta": (86, 91, 91),
    "light_blue_wool": (58, 175, 217), "light_blue_concrete": (36, 137, 199), "light_blue_terracotta": (113, 109, 138),
    "blue_wool": (53, 57, 157), "blue_concrete": (45, 47, 143), "blue_terracotta": (74, 60, 91),
    "purple_wool": (121, 42, 172), "purple_concrete": (100, 32, 156), "purple_terracotta": (118, 70, 86),
    "magenta_wool": (189, 68, 179), "magenta_concrete": (169, 48, 159), "magenta_terracotta": (150, 88, 109),
    "pink_wool": (238, 141, 172), "pink_concrete": (214, 101, 143), "pink_terracotta": (162, 78, 79),
    "red_wool": (160, 39, 34), "red_concrete": (142, 33, 33), "red_terracotta": (143, 61, 47),
    "brown_wool": (114, 71, 40), "brown_concrete": (96, 59, 31), "brown_terracotta": (77, 51, 35),
    "terracotta": (152, 94, 67),
    # farm kit
    "farmland": (98, 62, 36), "wheat": (214, 186, 84), "carrots": (94, 150, 46), "potatoes": (86, 140, 52),
    "beetroots": (110, 60, 60), "beehive": (196, 156, 78), "composter": (110, 78, 42),
    "stripped_spruce_log": (120, 92, 54), "cobblestone_slab": (127, 127, 127),
    "mossy_cobblestone_slab": (100, 112, 85), "stone_brick_slab": (122, 122, 122),
    "cobblestone_wall": (127, 127, 127), "lily_pad": (40, 110, 40), "sweet_berry_bush": (70, 110, 50),
    "dandelion": (240, 220, 60), "poppy": (220, 50, 40), "cornflower": (70, 90, 200),
    "spruce_door": (114, 84, 48), "spruce_fence": (114, 84, 48), "spruce_trapdoor": (114, 84, 48),
    "azalea_leaves": (98, 124, 52), "flowering_azalea_leaves": (176, 130, 170),
    "birch_planks": (192, 175, 121), "birch_slab": (192, 175, 121), "stone_brick_stairs": (122, 122, 122),
    "observer": (96, 96, 96), "dispenser": (110, 110, 110), "hopper": (70, 70, 70),
    "redstone_wire": (200, 40, 30), "crafting_table": (120, 90, 55), "spruce_door": (114, 84, 48),
    "mossy_stone_brick_stairs": (110, 118, 100), "yellow_wool": (248, 197, 39),
    "birch_trapdoor": (214, 205, 170),
    # --- redstone / rails / mechanisms -------------------------------------
    "rail": (124, 110, 96), "powered_rail": (160, 130, 60), "detector_rail": (150, 116, 84),
    "activator_rail": (140, 96, 70), "repeater": (188, 182, 178), "comparator": (188, 182, 178),
    "redstone_torch": (170, 50, 40), "redstone_wall_torch": (170, 50, 40), "lever": (124, 102, 74),
    "piston": (150, 133, 105), "sticky_piston": (130, 145, 90), "piston_head": (150, 133, 105),
    "note_block": (98, 73, 48), "jukebox": (85, 60, 44), "sculk_sensor": (18, 52, 60),
    "spawner": (55, 64, 74), "furnace": (110, 110, 110), "lectern": (156, 124, 74),
    "anvil": (68, 68, 68), "bookshelf": (110, 86, 55), "red_shulker_box": (140, 50, 50),
    # --- liquids / hot / cold ----------------------------------------------
    "ice": (145, 183, 235), "bubble_column": (60, 120, 200), "lava": (215, 110, 30),
    "magma_block": (142, 68, 38), "soul_sand": (81, 62, 50), "bedrock": (85, 85, 85),
    "ochre_froglight": (218, 201, 139),
    # --- plants / decor -----------------------------------------------------
    "glow_lichen": (124, 140, 116), "spore_blossom": (216, 120, 160), "pink_tulip": (224, 160, 196),
    "pumpkin": (198, 118, 24), "pumpkin_stem": (120, 150, 60), "attached_pumpkin_stem": (188, 150, 60),
    "bee_nest": (198, 153, 79), "cake": (240, 225, 215), "candle": (226, 204, 168),
    "purple_bed": (125, 62, 178),
    "potted_crimson_fungus": (150, 98, 76), "potted_lily_of_the_valley": (150, 98, 76),
    "potted_red_mushroom": (150, 98, 76),
    # --- wood / leaves missing from the families above ----------------------
    "jungle_leaves": (48, 110, 26), "mangrove_leaves": (60, 130, 55),
    "mangrove_planks": (117, 54, 48), "stripped_mangrove_log": (139, 66, 58),
    # --- carpets ------------------------------------------------------------
    "white_carpet": (234, 236, 237), "red_carpet": (160, 39, 34), "light_blue_carpet": (58, 175, 217),
}
FALLBACK_COLOR = (255, 0, 255)


# A variant is the colour of the block it is cut from, so walls, gates, slabs and signs never need
# their own entry - and neither will the next wood set Mojang ships. Longest suffix first: a
# fence_gate is not a gate, and a wall_sign is not a sign.
_VARIANT_SUFFIXES = ("_pressure_plate", "_hanging_sign", "_fence_gate", "_wall_sign", "_trapdoor",
                     "_stairs", "_button", "_carpet", "_fence", "_slab", "_door", "_sign", "_wall",
                     "_bars", "_pane", "_gate")
_BASE_FORMS = ("", "s", "_block", "_planks", "_log")


def _derive(short: str) -> tuple[int, int, int] | None:
    for suf in _VARIANT_SUFFIXES:
        if not short.endswith(suf):
            continue
        stem = short[: -len(suf)]
        for form in _BASE_FORMS:
            hit = COLORS.get(stem + form)
            if hit:
                return hit
    return None


def color_of(name: str) -> tuple[int, int, int]:
    short = name.split(":")[-1]
    got = COLORS.get(short)
    if got is not None:
        return got
    return _derive(short) or FALLBACK_COLOR


def missing_colors(names) -> list[str]:
    """Names that will render magenta - neither listed nor derivable from the block they are cut from."""
    out = set()
    for n in names:
        short = n.split(":")[-1]
        if short not in COLORS and _derive(short) is None:
            out.add(short)
    return sorted(out)


# ------------------------------------------------------------- cost tiers

EXPENSIVE_SUFFIXES = ("_terracotta", "_concrete", "_concrete_powder", "_stained_glass",
                      "_stained_glass_pane", "_glazed_terracotta")
EXPENSIVE_NAMES = {"terracotta", "quartz_block", "smooth_quartz", "quartz_pillar", "chiseled_quartz_block",
                   "quartz_bricks", "glass", "tinted_glass", "prismarine", "prismarine_bricks",
                   "dark_prismarine", "sea_lantern", "purpur_block", "purpur_pillar", "end_stone",
                   "end_stone_bricks", "copper_block", "netherite_block", "diamond_block", "gold_block",
                   "emerald_block", "lapis_block", "amethyst_block", "calcite", "obsidian", "crying_obsidian",
                   "shroomlight", "glowstone", "redstone_lamp", "beacon", "sponge", "wet_sponge",
                   "honey_block", "slime_block", "hay_block", "bookshelf", "note_block", "jukebox"}
OK_NAMES = {"iron_bars", "glass_pane", "smooth_stone", "smooth_stone_slab", "andesite", "polished_andesite",
            "diorite", "polished_diorite", "granite", "polished_granite", "tuff", "tuff_bricks",
            "polished_tuff", "deepslate", "cobbled_deepslate", "deepslate_bricks", "deepslate_tiles",
            "cracked_deepslate_bricks", "polished_deepslate", "iron_block", "iron_trapdoor", "iron_door",
            "sea_pickle", "sandstone", "red_sandstone", "smooth_sandstone", "cut_sandstone",
            "bricks", "nether_bricks", "blackstone", "polished_blackstone", "basalt", "polished_basalt",
            "packed_mud", "mud_bricks", "bamboo_block", "stripped_bamboo_block", "bamboo_planks"}


def tier(name: str) -> str:
    n = name.split(":")[-1]
    if n in ("air", "cave_air", "void_air"):
        return "air"
    if n in EXPENSIVE_NAMES or n.endswith(EXPENSIVE_SUFFIXES):
        return "expensive"
    if n in OK_NAMES or any(n.startswith(o + "_") for o in ("andesite", "diorite", "granite", "tuff",
                                                            "deepslate", "sandstone", "brick", "iron")):
        return "ok"
    return "cheap"


# ------------------------------------------------------------- substitution
# Hue-preserving cheap replacements. Order: try exact, then family rule.
_DYES = ["white", "light_gray", "gray", "black", "brown", "red", "orange", "yellow", "lime",
         "green", "cyan", "light_blue", "blue", "purple", "magenta", "pink"]

SUBSTITUTIONS: dict[str, str] = {
    "white_concrete": "snow_block",
    "white_terracotta": "white_wool",
    "terracotta": "brown_wool",
    "quartz_block": "snow_block",
    "smooth_quartz": "snow_block",
    "quartz_pillar": "snow_block",
    "chiseled_quartz_block": "snow_block",
    "quartz_bricks": "snow_block",
    "quartz_stairs": "oak_stairs",
    "quartz_slab": "smooth_stone_slab",
    "glass": "glass_pane",           # panes are cheap-ish; flag anyway
    "glowstone": "lantern",
    "shroomlight": "lantern",
    "sea_lantern": "soul_lantern",
    "gold_block": "yellow_wool",
    "diamond_block": "light_blue_wool",
    "emerald_block": "lime_wool",
    "lapis_block": "blue_wool",
    "lime_concrete": "moss_block",   # nicer than lime_wool for nature builds
    "green_concrete": "moss_block",
    "lime_terracotta": "moss_block",
    "green_terracotta": "green_wool",
}


def substitute(name: str) -> str | None:
    """Cheap replacement for an expensive block name, or None if already fine."""
    n = name.split(":")[-1]
    if tier(n) != "expensive":
        return None
    if n in SUBSTITUTIONS:
        return "minecraft:" + SUBSTITUTIONS[n]
    for d in _DYES:
        for suf in ("_concrete", "_terracotta", "_concrete_powder", "_glazed_terracotta",
                    "_stained_glass", "_stained_glass_pane"):
            if n == d + suf:
                return f"minecraft:{d}_wool"
    return None


# ------------------------------------------------------------- state registry

class Registry:
    """Builds a palette for a new model. `state()` borrows a full state
    (with properties) from donor models when available -- guaranteed valid for
    the target MC version -- and `raw()` hand-crafts one when no donor has it."""

    def __init__(self, donors: list | None = None):
        self.palette: list[Tag] = [nbt.block_state("minecraft:air")]
        self.index: dict[tuple, int] = {nbt.state_key(self.palette[0]): 0}
        self.donor_states: dict[tuple, Tag] = {}
        for d in donors or []:
            for e in d.palette:
                self.donor_states.setdefault(nbt.state_key(e), e)

    def _add(self, entry: Tag) -> int:
        k = nbt.state_key(entry)
        if k in self.index:
            return self.index[k]
        self.index[k] = len(self.palette)
        self.palette.append(entry)
        return self.index[k]

    def state(self, name: str, **props) -> int:
        name = name if ":" in name else "minecraft:" + name
        want = nbt.state_key(nbt.block_state(name, **props))
        if want in self.donor_states:
            return self._add(self.donor_states[want])
        # donor has this block name with different/extra props -> take the closest
        cands = [(k, e) for k, e in self.donor_states.items() if k[0] == name]
        if cands and props:
            best = max(cands, key=lambda ke: sum(1 for kv in ke[0][1] if kv in want[1]))
            return self._add(best[1])
        if cands and not props:
            return self._add(cands[0][1])
        return self.raw(name, **props)

    def raw(self, name: str, **props) -> int:
        return self._add(nbt.block_state(name, **props))
