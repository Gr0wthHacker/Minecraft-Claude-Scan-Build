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
#:
#: `tuff` IS A BLOCK THIS SERVER CANNOT SUPPLY, which is a different fault and the more serious
#: one - rule 12, ASK THE WORLD AND NOT THE TABLE. It is `ok` by the economy table and present in
#: the provisional 1.19 allowlist, so every check in the pipeline passed it; measured against the
#: real captures (`island_full`, `island_now`) it stands in **ZERO** cells, because tuff generates
#: in deep cave and there is no deep cave on a skyblock. `mossy_cobblestone` is what
#: `palette.affordable_like("tuff")` answers - the closest block that is cheap, WITNESSED here
#: (9,172 cells standing) and not a machine - at 22.3 RGB, and it keeps tuff's job in every body
#: it appears in: tuff is the LIGHT tone against dark rock (the Mine Ridge's mid band, the Prism
#: Downs' pale bed, the Cutting Yard's tread) and mossy cobble is lighter still, 115 against 108.
#: It is hue-distinct from the two tones it now stands beside - 43 RGB from `granite`, 55 from the
#: `moss_block` turf - so nothing in those ladders collapses into it.
#:
#: **THE PARK'S COBBLESTONE BAN IS ABOUT BUILDINGS, NOT TERRAIN**, and this does not breach
#: it. Jack threw out a park that was 17.7% cobblestone, and every building generator carries
#: that ban in its own tests; the cells this swap touches are all ROCK BODY - the Mine Ridge,
#: Prism Downs, the Plateau Vale and Bone Bed, the Cutting Yard, the Diggings and the
#: coaster's ballast - where the park already spends 18,185 cobblestone as `rock_c`.
#:
#: `gravel` IS THE ONLY GRAVITY BLOCK IN THE PARK'S TERRAIN, AND IT FAILS BOTH OF THE RULES THAT
#: KILLED THE OTHER TWO. Jack, 2026-09-10: "remove all gravel and swap for something else."
#:
#: RULE 13 first, and it is not hypothetical. A generator that uses gravel is careful with it -
#: `mineridge` places it as "a crust material: the top course of a column that is solid to the
#: ground and never a face, so a falling block never has air under it" - and that invariant
#: belongs to ONE generator over ITS OWN model, which is not the model that ships. Measured on
#: the shipped park, ELEVEN gravel cells stand on air and fall the moment they are placed.
#:
#: TEN OF THE ELEVEN ARE ON THE PARK PLATE, which is the case no generator can be careful about:
#: the park is ONE COURSE OF GROUND AT Y202 OVER OPEN VOID, so every cell of it has air beneath
#: it by construction and a gravity block laid on the ground falls off the world. They are the
#: Claim Lake Menagerie's pond bed at V135-142 / U197-210. The eleventh is high in the terrain at
#: (97553, 214, 80456), and NO SOURCE MODULE OWNS THAT CELL - it arrives from the composite's own
#: passes, which is the other half of the same point.
#:
#: So this is not a generator to fix. Nothing re-checks a gravity block after composition and
#: nothing can: the cure is not to carry one into a composite at all.
#:
#: RULE 12 second, and it is `tuff`'s case exactly. Gravel is cheap by the table, in the 1.19
#: allowlist and spendable, so every check in the pipeline passes it - and measured against the
#: real captures it stands in SIXTEEN cells of the whole world, against cobblestone's 15,897.
#: `mcbuild provision` puts it 1,793 short with no recipe and no price, which is the classifier
#: saying there is no route to it at all.
#:
#: `cobblestone` is what `palette.affordable_like("gravel")` answers, and it costs NOTHING to
#: take: 4.1 RGB on the side face, L127.3 against gravel's L128.1. Gravel was never a rung in
#: any of the bedded ladders - the Mine Ridge's runs cobbled_deepslate 77 / moss 101 / granite
#: 112 / stone 126 / diorite 188 and gravel is not in it - so nothing collapses. What is lost is
#: TEXTURE, which is the one thing the colour DB cannot measure: gravel is visibly granular and
#: cobblestone is visibly lumpy, and both average to the same grey. Judge that in world.
#:
#: IT IS A SWAP AND NOT A REMOVAL, because a crust is the top COURSE of a mass. Taken out rather
#: than replaced it leaves 2,209 holes in the surface of the terrain it was covering.
#:
#: The park's cobblestone goes 2.27% -> 2.79% - the ban Jack imposed was on a park that was
#: 17.7% of it, it is a ban on BUILDINGS, and every one of these cells is terrain: Mine Ridge
#: 997, the coaster's ballast 518, the Diggings 576, the Bone Bed 407, the Plateau Vale 233.
#: `granite`, `coal_ore` AND `gold_ore` ARE THE ORE SEAM, and Jack, 2026-09-10: "remove granite
#: and ore blocks e.g. coal ore gold ore etc". They are the last three blocks in the park that
#: fail rule 12, and the ores fail it harder than tuff or gravel ever did.
#:
#: Measured: `granite`, `coal_ore` and `gold_ore` stand in ZERO cells of the real captures
#: (`island_full`, `island_now`), and `mcbuild provision` classifies both ores **NONE** - no
#: recipe, no price, no stock, no farm, which is the resolver saying there is no route to them at
#: all. That is the correct answer for an ore on a skyblock: ore generates in stone, and there is
#: no stone to generate it in. `granite` classifies CRAFT and its recipe is diorite plus QUARTZ,
#: which is itself short and comes from a dimension this park cannot reach - a route on paper.
#:
#: Every check in the pipeline passed all three: cheap-or-`ok` by the economy table, in the
#: provisional 1.19 allowlist, spendable, legal, supported, non-colliding. Nothing but provisioning
#: could see it, and nothing but a shipped composite could count it.
#:
#: **THE MAPPING IS CHOSEN AGAINST THE LADDER, NOT PER BLOCK, AND THAT IS THE WHOLE DIFFICULTY.**
#: `palette.affordable_like` answers `granite -> dripstone_block` (28.2), `coal_ore ->
#: mossy_cobblestone` (29.5), `gold_ore -> cobblestone` (44.9), and all three pass its three
#: gates - it is the function this file took at its word for `tuff` and for `gravel`. Taken all
#: three at once it DESTROYS the Mine Ridge's ore seam, because it optimises each block alone and
#: knows nothing about what is already standing beside it. Measured over `mineridge._SEAM` and
#: `_MID` with the existing swaps applied:
#:
#:     seam, affordable_like    dripstone 112 .44 . mossy_cobble 115 .20 . stone 126 .24 . cobble 127 .12
#:     mid,  already            dripstone 112 .16 . mossy_cobble 115 .12 . stone 126 .48 . cobble 127 .24
#:
#: - THE SAME FOUR MATERIALS IN DIFFERENT PROPORTIONS, inside 15 points of luminance. The seam
#: stops being a bed at all, which is the "five materials inside twenty-one points is one grey"
#: trap CLAUDE.md has now recorded five times, arriving through a helper rather than by hand.
#:
#: So the seam keeps a tone the mid band does not have, and an ore seam in real rock is DARK:
#:
#:     seam, chosen             smooth_basalt 73 .20 . dripstone 112 .56 . stone 126 .24
#:
#: - a warm bed with a dark fleck, 53 points below anything in `_MID`, smallest step 13.6 against
#: the mid band's 1.3. `granite` and `gold_ore` were the seam's warm pair and its pale glint, so
#: both go to `dripstone_block`, which the Mine Ridge's own table already calls "L112 - and its
#: second tone"; `coal_ore` was the dark fleck at L106 and goes to `smooth_basalt` at L73, which
#: is a BIGGER step than the ore it replaces rather than a smaller one.
#:
#: `smooth_basalt` is the only CHEAP dark rock, which is why it rather than `cobbled_deepslate`
#: (L77) or `deepslate` (L80), both `ok`. It stands in none of the old island's captures and in
#: **10,844 cells of this park**, and `mcbuild provision` does not list it short - the container
#: index covers it, which is better evidence about what can be GOT than a capture of a different
#: island 121,000 blocks away.
#:
#: The two ores' other uses take the same swap and want it: the Mine Coaster's ballast speckle
#: (`coaster.py` - "black_wool if r < 0.045 else coal_ore") becomes dark crushed rock, and the
#: tipped-ore spoil heaps in `claimrow`, `frontier_scatter`, `mineworks` and the Diggings become
#: dark spoil. Neither reads as ore now and neither is meant to.
#:
#: **THE REST OF THE ORE FAMILY IS NOT MAPPED, DELIBERATELY.** `iron_ore`, `copper_ore`,
#: `redstone_ore`, `lapis_ore` and the raw-ore blocks appear only in RETIRED modules (`The Mine
#: Head`'s `frontiertown.VEINS`, `The Mine Works`, the Gold Sluice) and in no shipped composite.
#: Mapping a block nobody is looking at is a design decision made blind - what a "vein" should
#: read as without ore in it is a question for whoever re-sites that module.
#: `test_NO_ORE_BLOCK_REACHES_A_SHIPPED_COMPOSITE` is what catches it instead, so the next one
#: forces a decision rather than being silently swapped or silently shipped.
SWAPS: dict[str, str] = {"andesite": "dripstone_block", "tuff": "mossy_cobblestone",
                         "gravel": "cobblestone", "granite": "dripstone_block",
                         "gold_ore": "dripstone_block", "coal_ore": "smooth_basalt"}


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
