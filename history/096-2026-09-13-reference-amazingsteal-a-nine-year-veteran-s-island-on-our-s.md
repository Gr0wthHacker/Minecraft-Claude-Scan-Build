## `reference/amazingsteal`: a nine-year veteran's island, on OUR server (2026-09-13)

A `/cscan` capture of another player's island on skyblock.net. **204x384x204, 604,686 blocks, 665
distinct block names, 3,353 tile entities.** It is the first evidence this project has that was made
by somebody else *under our own constraints* - the download corpus is a different Minecraft with a
different economy, and everything else here is ours. Filed in `reference/` beside the other outside
builds; `tools/corpus.py` and `tools/look.py` both read it.

### WHAT DOES NOT TRANSFER, AND JACK NAMED IT BEFORE I BUILT ON IT

**17.5% of that build is `expensive` tier** - 105,502 cells: 39,940 gold blocks, 13,463 amethyst,
7,230 lapis, terracotta and concrete used freely. Jack: *"this is a very long time player who has
more grass blocks economical access to materials than we do, theyve been playing for 9 years."*

That is a fact about a WALLET and it transfers to nothing. I was one measurement away from
concluding our austerity was self-imposed. **A capture proves what a player HAS, never what a
player can AFFORD**, and the two look identical in a block count.

### WHAT DOES: AVAILABILITY, AND IT IS 665 ANSWERS TO RULE 12 AT ONCE

Every name in it is a block the 1.19 server has actually sent a client. Diffed against every capture
of Jack's own island (204 names), **474 were blocks we had never witnessed** - and the provisional
allowlist held 191, so it was rejecting most of the game.

- **"Sandstone does not exist on this skyblock" IS FALSE.** ~10,000 cells of `sandstone` and
  `sandstone_slab` stand in it, plus `end_stone`, `netherrack`, `nether_bricks`, crimson and warped.
  That claim has been in this file for weeks and was never evidence, only absence of it.
- **THE 1.19 CLAIM IS NOW INDEPENDENTLY CONFIRMED.** 665 distinct blocks from a veteran using
  everything he can reach, and **not one post-1.19 block**: no cherry, bamboo blocks, suspicious
  sand, tuff bricks, copper bulbs, trial chambers, vault, crafter or pale oak. A witness set that
  large with a clean cut at exactly one version is much stronger evidence than the server MOTD.
- `tools/server_blocks.py` takes it as a capture: **191 -> 680 blocks**, and `allium` and
  `deepslate_bricks` - the two this file already recorded as wrongly rejected while four designs
  were built from them - are in.

**Two bugs in that tool, both found before using it, both the shape this file keeps recording:**

- **REGENERATING WOULD HAVE SILENTLY SWITCHED THE GATE ON.** `blocks.available` reads
  `srv.get("enforce", True)` - defaulting to TRUE - and the writer emitted only
  `version/source/authoritative/blocks`. So the one command that improves the list would have
  dropped the `enforce: false` Jack set and started rejecting blocks across every generator, with a
  `note` beside it explaining a decision that was no longer in force. The policy keys are carried
  across now and `test_the_allowlist_keeps_its_policy_keys` is the tripwire.
- **A capture that failed to load was skipped in SILENCE**, so the list quietly shrank to whatever
  happened to parse and nobody learned which witness went missing. It prints `SKIPPED <name>`.

`POST_1_19` was defined INSIDE one test and a second test needed it; it is module-level now, because
two copies of that set is the drift the one-source rule exists to stop.

### AND WHAT ELSE TRANSFERS IS FREE

| | theirs | our `Park Buildings` |
|---|---|---|
| detail families (slab/stair/wall/pane/trapdoor/fence/carpet) | **12.0%** | 3.4% |
| `type=top` slabs, of non-double slabs | **66%** | 10% |
| `half=top` (upside-down) stairs | **46%** | 21% |
| `open=true` trapdoors | 55% | 52% - we already match |
| accent tail past the top 3 blocks | 78% | 68.7% - we already match |
| dominant block | 8.0% | 15.4% |

**CUT BLOCKS ARE CHEAPER THAN FULL ONES, WHICH INVERTS THE WHOLE ARGUMENT.** Off the stonecutter
recipes rather than from memory: **1 block -> 2 slabs, 1 block -> 1 stair.** Slabs are 43% of their
detail. So closing that gap is cost-neutral at worst and halves the material wherever a slab does
the job - and a `type=top` slab is the same item as a `type=bottom` one, so 10% -> 66% is free by
definition. It is the one finding here with no budget attached at all.

### DENSITY, measured against an outside reference for the first time

| | amazingsteal | `Park Complete` |
|---|---|---|
| columns >= 3 courses tall | **65%** | 42% |
| blocks per occupied column | **10.3** | 3.59 |
| columns >= 4 from any 3+ tall mass | **4.7%** | **25.9%** |
| columns >= 10 away | 0.2% | 4.0% |

Our park is 99% paved and 42% furnished; a quarter of it is four blocks from anything with height.
That is Jack's repeated complaint - *"so much wasted empty crap"*, *"buildings with unclear
purposes"* - with a number and an outside benchmark against it at last.

**And the composition is FOUR MASSES WITH REAL AIR BETWEEN THEM**: a ground plate, gothic spires, a
dense main island, a floating colonnade and a crown, across 384 courses with Y73-78, Y199-213 and
Y262-269 empty. The Prism Well and the Broken Plateau are the same bet; this is the first
confirmation it is what a good builder here actually does.

