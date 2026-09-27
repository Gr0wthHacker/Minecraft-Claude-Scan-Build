## The clutter pass: the park stops asking the printer to plant a garden (2026-09-06)

Jack: *"hide all moss, azalea, shrubs, etc from the schematic, also replace andesite with something
else"*, then *"moss carpet, keep moss blocks please"*.

    python -m mcbuild declutter "Park Complete" --dry-run     # any design, by name or path
    python -m mcbuild declutter <design> --in-place [--also vine] [--keep fern] [--swap a=b]

`mcbuild/ops/declutter.py`, run at the moment `tools/park_place.py` writes the two shipped
composites - **15,446 cells hidden and 8,086 andesite swapped in `Park Complete`** (541,764 ->
526,385), 13,428 and 8,086 in `Park Buildings`. 0 clutter and 0 andesite left in either.

**IT RUNS AT THE COMPOSITE, NOT IN TWELVE CONFIGS.** The clutter is planted by a dozen passes -
`parkgreen`, `frontier_scatter`, `thicket`, `plateau`, `claimrow` and every `_Ground` helper - so
turning it off upstream is one decision taken twelve times and remembered twelve. The module
artifacts keep their planting exactly as designed, which is what makes this reversible: delete two
lines in `park_place` and the next ship has the garden back.

**AND A LITEMATIC CANNOT EXPRESS REMOVAL, so this HIDES rather than clears.** A fern taken out of
the design is a fern the printer never places and `/cscan check` never reports; one already standing
in the world is untouched. That is what "hide it from the schematic" means and it is why this is
safe to run over a half-built park.

Three exclusions, each of which was the wrong answer first and is pinned by a test:

- **MOSS BLOCK IS GROUND; MOSS CARPET IS CLUTTER** - Jack's own correction, and the numbers say why:
  107,067 moss blocks are the park's lawn and 7,500 carpets were a frill over it.
- **A LEAF IS NOT A SHRUB.** The azalea BUSH (`azalea`, `flowering_azalea`) goes; `azalea_leaves`,
  `jungle_leaves`, `oak_leaves` stay, because they are the canopies of trees whose trunks are logs -
  strip them and every tree in the park is a bare post. Vines stay for the same reason: they are the
  Overgrowth pass's vertical mass on a wall, not floor dressing. Both are one flag (`--also vine`).
- **A PLANT THAT EMITS LIGHT IS A FIXTURE.** `glow_lichen`, `sea_pickle` and berried cave vines are
  what the night pass solved a dark surface with, and removing one re-opens a spawnable cell that
  nothing would report. `LIT` names them; `NOT_CLUTTER` records the reason for every exclusion, so
  nobody re-adds one by accident.

**`andesite` -> `dripstone_block`, and it is the repo's OWN recorded swap** rather than a new
opinion: `lowland.py` made it once already, for the reason that applies here too. Andesite is 136 in
luminance against `stone` 126, `cobblestone` 127 and `gravel` 128 - four materials inside ten points,
which is one grey however they are mixed, and this file has now recorded that mistake five times.
Dripstone is warm (134,108,93) against every grey in that body, is natural cave rock rather than
something quarried, and is `cheap` tier where andesite is `ok`. All 8,086 cells were terrain -
Mine Coaster ballast 4,494, Mine Ridge 4,320, the Plateau, the lake beds - so nothing masonry moved.
The 16 `polished_andesite_stairs` inside the downloaded Wyrm Gate asset are LEFT: swapping another
builder's own trim for sixteen cells is not worth it, and `--swap polished_andesite_stairs=...` is
there if it ever is.

**A FILL CAN OPEN A JOIN OF ITS OWN.** Removing 15,000 cells changed the composite's 6-connectivity
enough that the single-pass corner stitch left two `waxed_copper_block` breaks open, and
`test_printable` caught it. `printable.stitch_model` runs to a FIXPOINT now (bounded at 3 rounds,
stopping the moment a round writes nothing) rather than being a one-shot that is usually enough:
969 fills, and the invariant is true by construction instead of by luck.

**Two failures on the shipped park are PRE-EXISTING and were verified as such**, not caused here:
`test_park_water::test_not_one_cell_of_this_design_stands_on_anything_but_lawn` reads `Park Complete`
as the lake's context and that composite CONTAINS the lake - 4,699 of its 5,530 "clashes" are the
lake's own water, bed and froglights, the self-reference trap for the seventh time - and
`test_overgrowth`'s three vines name a face at (97622, 204..206, 80316), which is air in a composite
built with the pass switched off.

