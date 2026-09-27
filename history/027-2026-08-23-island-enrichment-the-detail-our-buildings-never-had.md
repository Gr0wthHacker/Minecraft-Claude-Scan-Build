## Island Enrichment: the detail our buildings never had (2026-08-23)

Jack, comparing our scenes to other people's: *"i dont think our area is nearly as detailed or
up to snuff"*. He is right, and `tools/corpus.py` says by how much. Against 31 outside builds:

| architecture | palette (median) | detail % (median) |
|---|---|---|
| theirs | 37 | 17.3 |
| ours | 14 | 11.4 |

and per building it was far worse than the median. The **Campanile was 575 cells of 12 block
types at 1.4% detail** - a bell tower of three blackstone variants stacked - against their
comparable watchtower at 45 types and 48.9%. The Sanctum, "the quarter's one complete
building", was nine block types. Court Hall was 0.0%.

**THE MISSING VOCABULARY IS SPECIFIC.** Per thousand cells, ours against theirs:

    stairs    0.64 vs 4.51     seven times under
    fences    0.07 vs 2.22     thirty times under
    trapdoors 0.00 vs 1.07     we have never placed one
    panes     0.08 vs 0.49

while we OVER-use the chunky families: walls 1.8x, carpet 9.9x, lanterns 3.0x. That is the whole
diagnosis - **we build in full blocks, slabs and walls and skip the three families that make a
surface read as built.** An open trapdoor is the vertical slab Minecraft never shipped; an
upside-down stair is an eave; a fence is a railing.

**And the economy is not the constraint.** 350 detail blocks are 1.19-legal and spendable, 38 of
them stone-family ones already in the quarter's own palette. This was self-imposed.

`configs/island_enrichment.yaml`, `gen/enrich.py` - **416 blocks, 0 problems, OVERLAP 0.**

**ADDITIVE ONLY.** Every zone is 89-97% built, so the pass writes into AIR and never over
anything standing - the deck floor's rule that a remedial design is judged by what it REPLACES.
The cost is that it cannot deepen the palette of an existing wall, only of the detail hung on
it, which is why palette moves 12 -> 14 while detail moves 1.4% -> 15.9%.

| design | detail% before | after |
|---|---|---|
| Lowland Campanile | 1.4 | **15.9** |
| Court Hall | 0.0 | **15.4** |
| Lowland Sanctum | 9.7 | **18.4** |
| Deck Vault | 11.5 | **20.9** |
| Lowland Ruinway | 48.0 | 61.9 |

**RUNS, NOT CELLS** is the rule that decides whether it reads, and it is the deck soffit's
lesson in a new place: that pass drew a coffer grid per cell and produced 215 runs of which 184
were one or two cells - confetti, in the loudest block available. A cornice on scattered cells
is the same mistake. So a course shorter than `min_run` gets nothing.

Three things this cost, each of which shipped a clean-looking build first:

- **The gate has to run on what is PLACED, not on the candidates.** Filtering after grouping
  let a five-cell run with two blocked cells ship three scattered stairs: the run passed the
  threshold and the placement did not. That is the soffit's bug wearing a different hat.
- **One record per cell.** An inside corner has masonry on two sides, so it enters as two
  candidates with two normals; left in, it counted toward a run on BOTH axes while only ever
  being placed once, and three stairs shipped in runs of one because the other axis' span had
  been emptied by the first.
- **A SILL IS NOT A COURSE, so the run gate must not touch it.** The gate exists to stop a
  course appearing on scattered cells; a sill is anchored to one opening, and an opening here
  is one to three cells wide, so gating it by length deleted all 46 of them. And the first
  opening test looked for masonry above and below a FACE cell, which asks whether the air
  OUTSIDE a wall is boxed in - it never is, so it emitted nothing at all.

**A stair leans INTO the wall it grows from** - its tall side is its `facing`, per the
convention pinned in `test_stairhead`, and our renderer draws both directions identically, so
`test_enrich` asserts it rather than trusting the eye.

**Honest limitation: the payoff is geometric relief, and that does not show in our renders.**
Blackstone on blackstone is within 12 RGB of itself, so an orthographic view of the enriched
Campanile looks almost like the plain one. Projecting stairs cast shadows in game and read
strongly there; offline this is the circularity CLAUDE.md already admits. Look at it in world
before extending the pass.

**Still open, and deliberately not built:** fences (30x under) and trapdoors (never used) are
the two biggest remaining gaps in the vocabulary. A trapdoor shutter is the strongest single
move in the corpus. Both want their own look at the geometry rather than being bolted onto
this pass - `rail: false` is in the config for that reason.

