"""What you may plant on, and what will hold something that clings.

Four generators rediscovered these rules the hard way - ferns on cobblestone, vines on wall blocks -
so they live in one place now.
"""
from __future__ import annotations

from .. import audit as _audit

# ferns, grass, azalea and saplings root only in soil. Carpet sits on any solid block.
SOIL = ("moss_block", "grass_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "mud", "clay")
AIRY = ("air", "cave_air", "void_air", "vine")


def is_soil(name: str) -> bool:
    return name.split(":")[-1] in SOIL


def holds(name: str) -> bool:
    """True when a block is a FULL cube that something can cling to or stand on.

    "Not air" is not enough: walls, fences, slabs and stairs will not hold a vine, and a design that
    assumes otherwise leaves orphan strands the moment the world differs from it.
    """
    return _audit._is_solid_name(name.split(":")[-1])


ROOTED = ("short_grass", "tall_grass", "fern", "large_fern", "azalea", "flowering_azalea",
          "dandelion", "poppy", "pink_tulip", "white_tulip", "lily_of_the_valley",
          "oak_sapling", "birch_sapling", "spruce_sapling", "sweet_berry_bush")


def prune_plants(w, ctx=None) -> int:
    """Remove anything that needs roots but does not have soil under it.

    Guarding at placement time keeps failing because the block underneath can change afterwards - a
    later pass overwrites it, or the world already holds something the design does not know about.
    Sweeping once at the end is order-independent, which is the only version that stays correct.
    """
    dropped = 0
    for (x, y, z), (name, _props) in list(w.cells.items()):
        if name not in ROOTED:
            continue
        # what will REALLY be underneath: the capture wins the merge wherever it already holds a
        # block, so the world's block beats the design's intention for this cell.
        under = None
        if ctx is not None:
            here = ctx.name_at(x, y - 1, z)
            if here not in AIRY:
                under = here
        if under is None:
            under = w.name(x, y - 1, z)
        if not is_soil(under or "air"):
            del w.cells[(x, y, z)]
            dropped += 1
    return dropped
