## More than one island, and the last red tests (2026-08-30, chunkscan 0.8.0)

**599 Python and 447 Java tests, 0 failures** — the first time in this session the suite has been
entirely green.

### Alt 2 can build on alt 1's island

Everything here assumed ONE island, because there was one: `plot.find` reads the bedrock out of a
capture, the mod carried a single square baked in at export time, and `fleet.json` claimed designs
with no idea where they were. All of it holds right up until a second account has its own island.

**AN ISLAND IS IDENTIFIED BY ITS BEDROCK, NOT BY WHOSE IT IS.** Every skyblock island has exactly
one bedrock at its origin, which is already how the plot is found — so the bedrock coordinate IS
the identity: stable, discoverable from any capture, and indifferent to who is standing on it.
Keying off the account would break the moment an alt walks next door, which is the entire case
being built.

    python -m mcbuild islands --add main --from out/island_now.litematic --owner Enroniti
    python -m mcbuild islands --where -24200 30000        # -> main
    /cscan plot                                            # ...whichever island you are ON

**OWNERSHIP IS A LABEL, NOT A PERMISSION.** It makes a report read sensibly and never decides who
may build; a tool that refused alt 2 on alt 1's island would be enforcing a rule the server does
not have. What IS enforced is that every boundary check — the wand, the printer, the digger, the
unbox siting — now asks about the island under THAT CELL rather than the one that happened to be
exported. Judged against the wrong square, every build on a second island reads as four thousand
blocks off-plot.

Two refusals carried over deliberately: **an unknown place is not an off-plot one** (somewhere the
registry has never been told about answers "I cannot say", the same posture `Plot` already takes
when no bedrock was found), and **with no registry at all it falls back to the single plot**, so a
setup that has never heard of a second island is unchanged.

A claim is keyed by ISLAND AND DESIGN now, because two alts can be building designs of the same
name in two places and a bare name would hand one account's work to the other.

### Three bugs, and two of them were latent for months

- **THE GENERATOR ASKED A DIFFERENT WORLD FROM THE ONE THE AUDIT VERIFIES AGAINST.** `shop_islet`
  consulted `island_deep` (which reads air at Y150) while `verify_against` used deep AND
  `island_now` — which holds the cobblestone Jack placed in the massif rework. So it planted
  short_grass believing its own moss would be underneath, and the moss is never placed, because
  `ROCK_FAMILY` counts cobblestone as satisfying it. Grass rooted in stone, one failing test, and
  the cause three files away. `Ctx` takes a LIST now and later captures win where they hold
  something. One design, two worlds, two answers: the same drift `proportions` and `rubric` share
  an entry point to avoid.
- **"REGENERATING THIS DESIGN MUST BE FOLLOWED BY RE-CARVING" WAS THE BUG, NOT THE FIX.** The shop
  islet's lens fill sits where the Lowland Stair screws down through it; the well was cut by hand
  once, with that note in the config and a test as the tripwire. Regenerating the islet to fix the
  grass re-filled the well and the tripwire fired — exactly as predicted, months later, by an
  unrelated change. **A step that has to be remembered is a step that gets lost.** `finish.carve_for`
  is a pipeline step now: dig cells plus headroom over whatever you stand on, re-derived on every
  run. 250 cells, by construction, for ever.
- **A cache keyed on the clock alone.** `Islands.all` cached per 30 seconds and not per DIRECTORY,
  so a second schematics folder silently got the first one's islands. Benign today — there is one
  folder — and precisely the latent bug that bites the day there are two. Its own test found it.

### Still open, and deliberately not guessed at

**The item sorter's threshold.** With the comparators reading correctly, the lock never flips: the
signal path from comparator to the torch that locks each filter hopper does not exist. The
simulator confirms the comparator reads the hopper (out == fill) and that nothing reaches the
torch. The correct topology is a THRESHOLD — unlock at signal >= 2, not >= 1, because the baseline
of 1 target + 4 filler already reads 1 — and I do not have a verified design for it. It is the one
thing here I am not willing to invent, because a sorter that looks right and voids items is worse
than one that plainly does not run.

**And none of the multi-island work has been exercised with a second island**, because there is
only one recorded. The fallbacks are tested; the two-island case is tested against a synthetic
registry. Record alt 2's island with `--add` and walk over before trusting it.

