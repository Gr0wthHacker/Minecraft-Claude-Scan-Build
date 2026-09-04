"""Read a WorldEdit `.schem` — the OTHER schematic format people share.

Everything here speaks Litematica, because that is what `chunkscan` writes and what Litematica
places. But the wider world shares `.schem` (Sponge), and a reference build that cannot be opened
is a reference build nobody learns from — `tools/corpus.py` already exists precisely because
outside builds are the only non-circular evidence this project has.

    m = sponge.load("item_filter.schem")     # -> the same schem.Model everything else takes

**THE FORMAT IS VARINT-PACKED, NOT BIT-PACKED**, which is the one real difference from a
litematic and the thing to get right: `BlockData` is a byte array of LEB128 varints, one per cell,
each an index into a palette that maps NAME -> index (the reverse of Litematica's list). Ordered
Y, then Z, then X — the same order as Litematica, which is the one thing that makes this cheap.

v2 keeps everything at the root; v3 nests it under `Schematic` and moves the palette and block
array inside a `Blocks` compound. Both are read here, because a file in the wild is whichever
version the person who exported it had.
"""
from __future__ import annotations

import numpy as np

from . import nbt
from .schem import Model


def _varints(data: bytes, n: int) -> list[int]:
    """LEB128, one per cell. `n` is how many to expect; a short read is a corrupt file."""
    out = []
    i = 0
    for _ in range(n):
        val = 0
        shift = 0
        while True:
            if i >= len(data):
                raise ValueError(f"BlockData ran out after {len(out)} of {n} cells")
            b = data[i]
            i += 1
            val |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        out.append(val)
    return out


def load(path: str) -> Model:
    """A Sponge `.schem` as the same `Model` the rest of this project passes around."""
    root_name, root = nbt.read(path)
    v = root.value
    # v3 nests everything under `Schematic`; v2 is flat. Same fields either way.
    if "Schematic" in v:
        v = v["Schematic"].value
    sx = int(v["Width"].value)
    sy = int(v["Height"].value)
    sz = int(v["Length"].value)

    blocks = v.get("Blocks")
    if blocks is not None:                       # v3
        bv = blocks.value
        pal_tag = bv["Palette"].value
        data = bv["Data"].value
    else:                                        # v2
        pal_tag = v["Palette"].value
        data = v["BlockData"].value

    # SPONGE'S PALETTE IS NAME -> INDEX, the reverse of Litematica's list. Building the list by
    # position rather than by iteration order matters: the entries are not necessarily in index
    # order, and a palette read in the wrong order silently relabels every block in the file.
    size = max(int(t.value) for t in pal_tag.values()) + 1
    names = ["minecraft:air"] * size
    for name, idx in pal_tag.items():
        names[int(idx.value)] = name

    raw = bytes(data if isinstance(data, (bytes, bytearray)) else bytearray(data))
    ids = np.array(_varints(raw, sx * sy * sz), np.int32).reshape(sy, sz, sx)

    palette = [nbt.block_state(n.split("[")[0], **_props(n)) for n in names]
    return Model(ids, palette, root, root_name, "sponge", [], [])


def _props(name: str) -> dict:
    if "[" not in name or not name.endswith("]"):
        return {}
    out = {}
    for part in name[name.index("[") + 1:-1].split(","):
        k, _, val = part.partition("=")
        out[k.strip()] = val.strip()
    return out


# ---------------------------------------------------------------------- the OLD format
#
# MCEdit `.schematic` is pre-1.13: `Blocks` is a byte array of NUMERIC ids and `Data` a parallel
# array of metadata nibbles. There is no palette and no names, so reading one means carrying a
# table - and a table is exactly the thing rule 11 says not to trust.
#
# So this one is EXPLICITLY PARTIAL and says so in the output. An id that is not in the table
# becomes `unknown_<id>` rather than a guess: a wrongly named block reads as a clean import of a
# different build, which is the worst of both worlds. Add ids here as real files need them.
MCEDIT_IDS = {
    0: "air", 1: "stone", 2: "grass_block", 3: "dirt", 4: "cobblestone", 5: "oak_planks",
    7: "bedrock", 8: "water", 9: "water", 10: "lava", 11: "lava", 12: "sand", 13: "gravel",
    17: "oak_log", 18: "oak_leaves", 20: "glass", 22: "lapis_block", 23: "dispenser",
    24: "sandstone", 25: "note_block", 27: "powered_rail", 28: "detector_rail",
    29: "sticky_piston", 33: "piston", 34: "piston_head", 35: "white_wool", 41: "gold_block",
    42: "iron_block", 43: "smooth_stone", 44: "smooth_stone_slab", 45: "bricks", 46: "tnt",
    47: "bookshelf", 48: "mossy_cobblestone", 49: "obsidian", 50: "torch", 53: "oak_stairs",
    54: "chest", 55: "redstone_wire", 56: "diamond_ore", 57: "diamond_block",
    58: "crafting_table", 61: "furnace", 62: "furnace", 64: "oak_door", 65: "ladder",
    66: "rail", 67: "cobblestone_stairs", 68: "oak_wall_sign", 69: "lever",
    70: "stone_pressure_plate", 72: "oak_pressure_plate", 73: "redstone_ore",
    75: "redstone_torch", 76: "redstone_torch", 77: "stone_button", 79: "ice", 80: "snow_block",
    85: "oak_fence", 87: "netherrack", 89: "glowstone", 93: "repeater", 94: "repeater",
    98: "stone_bricks", 101: "iron_bars", 102: "glass_pane", 108: "brick_stairs",
    109: "stone_brick_stairs", 112: "nether_bricks", 121: "end_stone", 123: "redstone_lamp",
    124: "redstone_lamp", 125: "oak_slab", 126: "oak_slab", 129: "emerald_ore",
    130: "ender_chest", 133: "emerald_block", 137: "command_block", 138: "beacon",
    139: "cobblestone_wall", 143: "oak_button", 145: "anvil", 146: "trapped_chest",
    149: "comparator", 150: "comparator", 152: "redstone_block", 154: "hopper",
    155: "quartz_block", 156: "quartz_stairs", 157: "activator_rail", 158: "dropper",
    159: "white_terracotta", 165: "slime_block", 170: "hay_block", 171: "white_carpet",
    173: "coal_block", 251: "white_concrete", 252: "white_concrete_powder",
}


def load_mcedit(path: str) -> tuple[Model, dict]:
    """A pre-1.13 MCEdit `.schematic`. Returns (model, {"unmapped": {id: count}}).

    THE UNMAPPED IDS ARE RETURNED, NOT SWALLOWED. A reader that quietly renders an unknown id as
    stone produces a build that looks imported and is wrong, and nothing downstream can tell.
    """
    import collections
    root_name, root = nbt.read(path)
    v = root.value
    sx = int(v["Width"].value)
    sy = int(v["Height"].value)
    sz = int(v["Length"].value)
    raw = v["Blocks"].value
    ids_raw = [int(b) & 0xFF for b in raw]

    unmapped: collections.Counter = collections.Counter()
    names, index = ["minecraft:air"], {0: 0}
    out = np.zeros(sx * sy * sz, np.int32)
    for i, bid in enumerate(ids_raw):
        if bid not in index:
            name = MCEDIT_IDS.get(bid)
            if name is None:
                unmapped[bid] += 1
                name = f"unknown_{bid}"
            index[bid] = len(names)
            names.append("minecraft:" + name)
        out[i] = index[bid]
    # MCEdit order is Y, then Z, then X - the same as everything else here.
    ids = out.reshape(sy, sz, sx)
    palette = [nbt.block_state(n) for n in names]
    return Model(ids, palette, root, root_name, "mcedit", [], []), {"unmapped": dict(unmapped)}


def load_any(path: str) -> Model:
    """A litematic or a `.schem`, whichever this is — decided by CONTENT, not by extension.

    A file called `.litematic.gz` is still a litematic, and people rename things. The root tag
    says what it really is, and asking it costs one read.
    """
    root_name, root = nbt.read(path)
    v = root.value
    if "Regions" in v:
        from . import schem
        return schem.load(path)
    if "Blocks" in v and "Palette" not in v:          # pre-1.13 MCEdit: numeric ids, no palette
        return load_mcedit(path)[0]
    return load(path)
