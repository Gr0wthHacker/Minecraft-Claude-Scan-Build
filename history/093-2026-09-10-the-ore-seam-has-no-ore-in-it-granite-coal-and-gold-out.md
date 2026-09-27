## THE ORE SEAM HAS NO ORE IN IT: granite, coal and gold out (2026-09-10)

Jack: *"remove granite and ore blocks e.g. coal ore gold ore etc"*. They went through
`declutter.SWAPS` beside `andesite`, `tuff` and `gravel`, and they are the last three blocks in
the park that fail rule 12 - the ores fail it harder than anything swapped before them.

    granite  2,973 -> dripstone_block      gold_ore 1,422 -> dripstone_block
    coal_ore 2,396 -> smooth_basalt        Park Complete and Park Buildings: 0 of each

**BOTH ORES CLASSIFY `NONE`, WHICH IS THE RESOLVER SAYING THERE IS NO ROUTE AT ALL** - no recipe,
no price, no stock, no farm. That is the correct answer for an ore on a skyblock: ore generates in
stone, and there is no stone to generate it in. `granite` classifies CRAFT and its recipe is
diorite plus QUARTZ, which is itself short and comes from a dimension this park cannot reach - a
route on paper. All three stand in ZERO cells of the real captures, and every check in the
pipeline passed them: cheap-or-`ok` by the table, in the 1.19 allowlist, spendable, legal,
supported, non-colliding. **Nothing but `provision` could see it and nothing but a shipped
composite could count it.** Coverage 70% -> 71%, unroutable materials 14 -> 12.

### `affordable_like` OPTIMISES ONE BLOCK AND KNOWS NOTHING ABOUT WHAT IS BESIDE IT

The transferable finding, and it nearly shipped. `palette.affordable_like` answers
`granite -> dripstone_block` (28.2), `coal_ore -> mossy_cobblestone` (29.5),
`gold_ore -> cobblestone` (44.9) - all three through its three gates, and it is the function this
file took at its word for `tuff` and for `gravel`. Taken all three at once it DESTROYS the Mine
Ridge's ore seam. Measured over `mineridge._SEAM` and `_MID` with the existing swaps applied:

    seam, affordable_like   dripstone 112 .44 . mossy_cobble 115 .20 . stone 126 .24 . cobble 127 .12
    mid,  already           dripstone 112 .16 . mossy_cobble 115 .12 . stone 126 .48 . cobble 127 .24

**THE SAME FOUR MATERIALS IN DIFFERENT PROPORTIONS**, inside 15 points of luminance: the seam
stops being a bed at all. That is the "five materials inside twenty-one points is one grey" trap
this file has recorded five times, arriving through a HELPER rather than by hand - which is why
three separate correct answers add up to a wrong one.

**SO THE MAPPING IS CHOSEN AGAINST THE LADDER, AND AN ORE SEAM IN REAL ROCK IS DARK:**

    seam, chosen            smooth_basalt 73 .20 . dripstone 112 .56 . stone 126 .24

- a warm bed with a dark fleck, 53 points below anything in `_MID`, smallest step 13.6 against the
mid band's 1.3. `granite` and `gold_ore` were the seam's warm pair and its pale glint, so both take
`dripstone_block`, which the Mine Ridge's own table already calls *"L112 - and its second tone"*;
`coal_ore` was the dark fleck at L106 and takes `smooth_basalt` at L73, **a BIGGER step than the ore
it replaces rather than a smaller one**. `smooth_basalt` is the only CHEAP dark rock (`cobbled_
deepslate` 77 and `deepslate` 80 are both `ok`); it stands in none of the old island's captures and
in 10,844 cells of this park, and `provision` does not list it short - **the container index is
better evidence about what can be GOT than a capture of an island 121,000 blocks away.**

The ores' other uses take the same swap and want it: the coaster's ballast speckle becomes dark
crushed rock, and the tipped-ore spoil in `claimrow`, `frontier_scatter`, `mineworks` and the
Diggings becomes dark spoil.

### THE REST OF THE FAMILY IS NOT MAPPED, AND A TEST CATCHES IT INSTEAD

`iron_ore`, `copper_ore`, `redstone_ore`, `lapis_ore` and the raw-ore blocks appear only in RETIRED
modules (`The Mine Head`'s `frontiertown.VEINS`, `The Mine Works`, the Gold Sluice) and in no
shipped composite. **Mapping a block nobody is looking at is a design decision made blind** - what a
"vein" should read as without ore in it is a question for whoever re-sites that module.
`test_NO_ORE_BLOCK_REACHES_A_SHIPPED_COMPOSITE` reads the two artifacts, so a re-sited module fails
and forces the decision rather than being silently swapped or silently shipped. And
`test_THE_SWAPS_KEEP_THE_MINE_RIDGE_S_SEAM_A_DISTINCT_BED` derives the bands from the generator's
own tables and asserts the seam holds a tone the mid band does not, 15 luminance clear - **it is red
for exactly the answers a future session is most likely to take.**

**Still open:** `Park Complete Ready` was regenerated with the composite (303,208 cells) - it is
written by `mcbuild provision --package --ship` and does NOT follow a reship on its own. And nine
`test_worldrender` failures are PRE-EXISTING (`module Signal Heron footprint does not fit its
plot`), verified by re-running with this change stashed.

