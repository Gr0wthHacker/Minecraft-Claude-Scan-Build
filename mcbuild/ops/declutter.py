"""Take the ground clutter OUT of a design, and swap a block that is not earning its place.

Two operations that are one job: what a printer should not be asked to place, and what it should
place instead. Both run over a finished model rather than over a generator, because the clutter is
laid by a dozen different passes (`parkgreen`, `frontier_scatter`, `thicket`, `plateau`, every
`_Ground` planting helper) and turning them all off one config at a time is a decision taken twelve
times that has to be remembered twelve times.

**A LITEMATIC CANNOT EXPRESS REMOVAL**, so this HIDES rather than clears: a fern taken out of the
design is a fern the printer never places and `/cscan check` never reports, and one already
standing in the world is left exactly where it is. That is what "hide it from the schematic" means
and it is the reason this is safe to run over a half-built design.

Three rules decide what is clutter, and each of them was a wrong answer first:

* **MOSS BLOCK IS GROUND; MOSS CARPET IS CLUTTER.** The block is the surface a lawn is made of -
  106,996 cells of the park - and the carpet is a one-cell frill over it. Removing the family would
  delete the ground itself.
* **A LEAF IS NOT A SHRUB.** `jungle_leaves`, `oak_leaves` and `azalea_leaves` are the canopies of
  trees whose trunks are logs; strip them and every tree in the park becomes a bare post. The
  AZALEA BUSH (`azalea`, `flowering_azalea`) is a shrub and goes; the azalea leaves stay.
* **A PLANT THAT EMITS LIGHT IS A FIXTURE.** `glow_lichen`, `sea_pickle` and berried cave vines are
  what the night pass solved a dark surface with, and taking one out re-opens a spawnable cell that
  nothing will report. They are named in `LIT` and never removed by default.
"""
from __future__ import annotations

from collections import Counter

from .. import nbt
from ..schem import Model


def _full(n: str) -> str:
    return n if ":" in n else "minecraft:" + n


#: Ground cover, shrubs, flowers and water weed - everything whose whole job is dressing the floor.
CLUTTER: set[str] = {
    # ground cover
    "moss_carpet", "fern", "large_fern", "short_grass", "grass", "tall_grass", "dead_bush",
    "hanging_roots", "small_dripleaf", "big_dripleaf", "big_dripleaf_stem", "spore_blossom",
    # shrubs
    "azalea", "flowering_azalea", "sweet_berry_bush", "brown_mushroom", "red_mushroom",
    # flowers
    "dandelion", "poppy", "blue_orchid", "allium", "azure_bluet", "oxeye_daisy", "cornflower",
    "lily_of_the_valley", "wither_rose", "red_tulip", "orange_tulip", "white_tulip", "pink_tulip",
    "sunflower", "lilac", "rose_bush", "peony",
    # water weed and crops
    "lily_pad", "seagrass", "tall_seagrass", "kelp", "kelp_plant", "sugar_cane",
}

#: Plants that are LIGHT SOURCES. Never removed unless asked for by name - see the module docstring.
LIT: set[str] = {"glow_lichen", "sea_pickle", "cave_vines", "cave_vines_plant"}

#: Blocks kept out of `CLUTTER` on purpose, with the reason, so nobody re-adds one by accident.
NOT_CLUTTER: dict[str, str] = {
    "moss_block": "the ground itself, not a frill on it",
    "vine": "the Overgrowth pass's curtains - vertical mass on a wall, not floor dressing",
    "jungle_leaves": "a tree canopy; strip it and the trunk is a bare post",
    "oak_leaves": "a tree canopy",
    "birch_leaves": "a tree canopy",
    "azalea_leaves": "the canopy of an azalea TREE; the bush is `azalea`",
    "flowering_azalea_leaves": "the canopy of an azalea tree",
    "mossy_cobblestone": "masonry that happens to be called mossy",
    "mossy_stone_bricks": "masonry that happens to be called mossy",
    "bamboo": "columnar, and structural wherever it is used",
    **{n: "a plant that EMITS LIGHT - see LIT" for n in LIT},
}

#: What to put where a block is not earning its place. `andesite` is 136 in luminance against
#: `stone`'s 126 and `cobblestone`'s 127 - inside the ~15 at which a tone stops being a tone - so a
#: rock body mixing all three reads as one flat grey. `dripstone_block` (134,108,93) is WARM against
#: every grey in that body, is natural cave rock rather than something quarried, and is `cheap`
#: where andesite is `ok`. This is `lowland.py`'s own recorded swap, applied to the park.
SWAPS: dict[str, str] = {"andesite": "dripstone_block"}


def declutter(m: Model, *, remove: set[str] | None = None, swap: dict[str, str] | None = None,
              keep: set[str] | None = None) -> tuple[Counter, Counter]:
    """In-place. Returns ({removed name: cells}, {(src, dst): cells}).

    `remove` defaults to `CLUTTER`, `swap` to `SWAPS`; `keep` wins over both. Names may be short or
    namespaced. Matching is on the block NAME, so every state of a plant goes with it - a fern's
    `half`, a tulip's nothing, a seagrass's `waterlogged`.
    """
    gone = {_full(n) for n in (CLUTTER if remove is None else remove)}
    subs = {_full(k): _full(v) for k, v in (SWAPS if swap is None else swap).items()}
    held = {_full(n) for n in (keep or set())}
    gone -= held
    for k in list(subs):
        if k in held:
            del subs[k]

    removed: Counter = Counter()
    swapped: Counter = Counter()
    for i, e in list(enumerate(m.palette)):
        name = nbt.state_name(e)
        if name in gone:
            n = int((m.ids == i).sum())
            if n:
                m.ids[m.ids == i] = 0          # index 0 is always air
                removed[name] += n
        elif name in subs:
            dst = subs[name]
            n = int((m.ids == i).sum())
            if n:
                # The properties are NOT carried: these are whole-block swaps between plain blocks,
                # and a property the target does not have reads as a WRONG STATE in `/cscan check`.
                di = m.ensure_state(dst)
                m.ids[m.ids == i] = di
                swapped[(name, dst)] += n
    m.compact_palette()
    return removed, swapped


def report(removed: Counter, swapped: Counter, *, top: int = 12) -> str:
    lines = []
    if removed:
        lines.append(f"clutter hidden: {sum(removed.values()):,} cells in {len(removed)} kinds")
        for name, n in removed.most_common(top):
            lines.append(f"  -{n:>7,}  {name.split(':')[-1]}")
        if len(removed) > top:
            lines.append(f"  ... and {len(removed) - top} more kinds")
    else:
        lines.append("clutter hidden: nothing")
    for (src, dst), n in swapped.most_common():
        lines.append(f"swapped: {n:,} {src.split(':')[-1]} -> {dst.split(':')[-1]}")
    return "\n".join(lines)
