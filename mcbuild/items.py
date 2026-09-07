"""What ITEM you must be holding to place a block.

A block name and an item name are not the same thing, and this is the third time in this repo that
assuming they are has cost something real. `ActionRecipe.itemFor` on the Java side has always known
that a wall sign is placed from `oak_sign` and that water comes out of a bucket; the Python side had
no such map at all, so `craft`, `shop` and `analyze` asked a chest for `oak_wall_sign`, `water` and
`redstone_wire` - items that do not exist - and reported **7,965 cells of `Park Complete`** as
unobtainable raw materials. The list they printed under *"no recipe known"* named eight things that
are not materials, they are the wrong NAME for a material.

**THIS FILE IS THE SOURCE AND THE JAR READS IT.** `tools/export_rules.py` writes the exception map
into `chunkscan_rules.json` beside the protection and economy rules, exactly as this repo already
does for every other fact both languages need - one source, so two tools cannot drift. Java keeps
its own rules as the fallback for a jar older than the file it is reading, and
`tests/test_items.py` fails if the shipped file and these rules disagree.

The rule, not a table: almost every block IS its own item, and the exceptions are the blocks that
are a STATE of something else - a sign on a wall rather than in the ground, a crop part way to being
grown, a fluid, a plant's second half.
"""
from __future__ import annotations

#: A block placed from a bucket. The bucket is consumed into an empty one, which is why the
#: builder budgets a filled bucket per cell rather than one bucket for the run.
FLUIDS = {
    "water": "water_bucket",
    "lava": "lava_bucket",
    "powder_snow": "powder_snow_bucket",
}

#: A crop is planted from its seed, and the block you see is a growth stage of it.
CROPS = {
    "wheat": "wheat_seeds",
    "carrots": "carrots",
    "potatoes": "potatoes",
    "beetroots": "beetroot_seeds",
    "melon_stem": "melon_seeds",
    "pumpkin_stem": "pumpkin_seeds",
    "attached_melon_stem": "melon_seeds",
    "attached_pumpkin_stem": "pumpkin_seeds",
    "cocoa": "cocoa_beans",
    "sweet_berry_bush": "sweet_berries",
    "torchflower_crop": "torchflower_seeds",
    "pitcher_crop": "pitcher_pod",
    "nether_wart": "nether_wart",
    "bamboo_sapling": "bamboo",
}

#: The second block of a two-block plant, or a plant's "grown" form. Placing the first places both.
CONTINUATIONS = {
    "kelp_plant": "kelp",
    "cave_vines_plant": "glow_berries",
    "cave_vines": "glow_berries",
    "twisting_vines_plant": "twisting_vines",
    "weeping_vines_plant": "weeping_vines",
    "big_dripleaf_stem": "big_dripleaf",
    "tall_seagrass": "seagrass",
    "bubble_column": "soul_sand",
}

#: Blocks that are simply named differently from the item that makes them.
RENAMED = {
    "redstone_wire": "redstone",
    "tripwire": "string",
    "water_cauldron": "cauldron",
    "lava_cauldron": "cauldron",
    "powder_snow_cauldron": "cauldron",
    "wall_torch": "torch",
    "soul_wall_torch": "soul_torch",
    "redstone_wall_torch": "redstone_torch",
    "frosted_ice": "ice",
    "carrots": "carrot",
    "potatoes": "potato",
}

#: A `<x>_wall_<y>` is the same item as `<x>_<y>`: the FACE you click decides how it lands.
WALL_SUFFIXES = ("_wall_hanging_sign", "_wall_sign", "_wall_banner", "_wall_fan", "_wall_head",
                 "_wall_skull")


def short(name: str) -> str:
    """`minecraft:oak_wall_sign[facing=east]` -> `oak_wall_sign`."""
    return name.split(":")[-1].split("[")[0]


def item_for(block: str) -> str:
    """The item a player must hold to place this block.

    Returns the block's own name whenever it is its own item, which is almost always. It never
    invents a name it cannot justify: a block with no placing item at all (`fire`, `nether_portal`,
    `piston_head`) comes back unchanged, so the caller reports it as unobtainable rather than
    silently substituting something plausible.
    """
    b = short(block)
    if b in FLUIDS:
        return FLUIDS[b]
    if b in RENAMED:
        return RENAMED[b]
    if b in CROPS:
        return CROPS[b]
    if b in CONTINUATIONS:
        return CONTINUATIONS[b]
    for suffix in WALL_SUFFIXES:
        if b.endswith(suffix):
            head = b[: -len(suffix)]
            tail = suffix.replace("_wall", "", 1)
            return head + tail
    # A potted plant is two items and the pot is the one you place; the plant goes in afterwards.
    if b.startswith("potted_"):
        return "flower_pot"
    return b


def exceptions() -> dict[str, str]:
    """Every block whose item differs from its own name, for export into `chunkscan_rules.json`.

    Derived from the block registry rather than hand-listed, so a block family added to the game
    cannot be silently missing from the file the jar reads.
    """
    from . import blocks
    out = {}
    names = {short(n) for n in blocks.search("")}
    for b in sorted(names | set(FLUIDS) | set(RENAMED) | set(CROPS) | set(CONTINUATIONS)):
        b = short(b)
        it = item_for(b)
        if it != b:
            out[b] = it
    return out
