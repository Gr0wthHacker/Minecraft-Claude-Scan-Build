## All six: the audit's plan, done (2026-09-07)

Jack: *"do all"*, against the six-point list the 2026-09-06 autonomy audit closed with. Every claim
below was re-measured after the change, not reasoned.

### 1. Provisioning — `mcbuild/provision.py`

**THE LOOP WAS A LAST MILE WITH NO SUPPLY CHAIN**, and its only way to say so was to fly to the
work, find nothing placeable and report a dead end. `mcbuild provision <design>` answers the
question nothing asked: what must be acquired, and how.

    Park Complete: 308,229 of 526,385 cells have their material (59%)
    materials short, by how they can be got: craft 20, smelt 3, farm 13, none 18
      CRAFT   cobblestone 11,041 . waxed_copper_block 9,048 . black_wool 4,907 ...
      SMELT   stone 2,580
      FARM    moss_block 99,253 . vine 9,609 . jungle_leaves 8,872 ...
      NONE    blackstone 35,415 . basalt 7,022 . tuff 6,408 ...

The audit measured 76% with no reachable source; it is 41% now, and the difference is not new
material — it is the item-name fix in §3 and resolving the SHORTFALL through the recipe tree rather
than the whole design. What is left is CLASSIFIED, which is the part a person can act on.

- **`--package` writes the buildable subset as its own design, at the parent's own origin.**
  `/cscan follow "Park Complete Ready"` can finish; `follow` on the parent cannot and had no way to
  say so. Same origin because a package is a VIEW of one design, not a second thing to keep
  aligned — which is the trap `origin_lock` exists for.
- **IT NEVER GUESSES A SOURCE.** A material with no recipe, no price and no stock is reported as
  having NONE, rather than folded into "farm it" because that sounds like an answer. `FARMED` is
  deliberately short and evidence-based; a long guessed list would turn *we do not know* into a
  confident wrong answer. Same posture as the ten park gates, where a gate with no evidence blocks.
- **Coverage is counted in CELLS, not materials.** A design one block short of one material is not
  half short, and the number that decides whether a session is worth starting is how many cells can
  actually go in.

`prices.json` is still empty, so `buy` can never be the answer yet — the shop has never been
walked, and `/cscan prices on` is what fills it.

### 2. The craft cost model — 3,358 iron pickaxes became 376 ingots

`craft "Park Complete"` proposed smelting **3,358 iron pickaxes** into nuggets for 426 lanterns —
10,074 ingots where 379 would do, on the island whose scarce metal is iron. Three faults, and the
first two compounded:

- **A LEAF PRICE OF 1 WAS A FLOOR UNDER EVERYTHING.** `best` started at the leaf cost and only came
  down, so any item whose recipe cost more than one unit stayed at one: `iron_nugget`, `iron_ingot`
  and `iron_pickaxe` all priced identically and a crafted tool was as cheap as the metal in it. An
  item with a recipe is worth what the recipe costs; a leaf is something you cannot make.
- **THE ARBITRAGE GUARD BARRED THE ONLY SANE ROUTE.** `mark_reversible` bars packing pairs from
  cost-minimisation, which is right for `raw_gold_block` — costing every leaf at 1 makes a block a
  cheaper source of raw gold than raw gold is. But `iron_ingot -> 9 iron_nugget` is a packing pair
  too, so unpacking an ingot was barred as well and smelting a tool was left as the winner. **A
  guard against arbitrage produced arbitrage.**
- **AND THE WASH TEST WAS NOT THE PROBLEM, WHICH TOOK TWO WRONG FIXES TO ESTABLISH.** It looked
  like one - it fires on any stock at all of any ingredient, so a single pickaxe in a chest passes
  it. Bounding it by what the held stock can actually feed reported *"short 424 lantern"* while
  hiding the 379 ingots that make them; replacing it with a margin against extravagance let
  `gold_ingot` be answered with 522 deepslate gold ore again, which is the exact failure it was
  written for. Both were reverted. **With the cost model fixed the absurd route cannot be chosen
  at all**: `_best_recipe(iron_nugget)` picks unpacking an ingot at 0.111 over smelting a pickaxe
  at 3.25, however permissive the guard downstream of it is. Two regressions caught by tests that
  already existed, which is the argument for the guard's own tests being about the ROUTE rather
  than about the guard.

**The two are told apart by where the packed form's price comes from.** An ingot has a real recipe
(smelt raw iron), so unpacking prices a nugget at a ninth of that and the arithmetic is true. A
`raw_gold_block` has no recipe but packing raw gold — the cycle we are inside — so its price falls
back to a leaf, and dividing a made-up number by nine is where the free gold came from. `_cost`
returns *(price, was it DERIVED)* and a reversible recipe is usable exactly when its input's price
was derived.

    iron_nugget 0.111 . iron_ingot 1.0 . iron_pickaxe 3.25 . raw_gold 1.0 (was 1/9)

One more thing it cost:

- **ONE UNPACKING HOP PER CHAIN, or the resolver does not finish.** A packing pair is an edge in
  BOTH directions, so admitting them doubled the branching of a search already exponential in its
  path set: individually every material resolved in under a tenth of a second and the fourteen
  together did not finish in ninety-five. One hop is all any real chain needs, and it is bounded
  back to what it was. `_cost`, `_best_recipe` and `_per_unit` are memoised on top of that.

### 3. One block-identity source — `mcbuild/items.py`

Three things were written twice, once in each language, and all three had drifted.

- **THE ITEM NAME.** `ActionRecipe.itemFor` knew a wall sign is placed from `oak_sign`; Python had
  no such map at all, so `craft`, `shop` and `analyze` asked chests for `water`, `oak_wall_sign` and
  `redstone_wire` — **7,965 cells reported as unobtainable raw material**, which is not a material
  shortage, it is the wrong NAME for a material. `items.item_for` is the rule, `exceptions()`
  derives the map from the registry (128 blocks) so a family added to the game cannot be silently
  missing, and `tools/export_rules.py` ships it into `chunkscan_rules.json` beside the protection
  and economy rules. Java consults the file first and keeps its own rules as the fallback for a jar
  older than its file.
- **THE PROPERTY SET, and the split that fixes it.** Java's `INTENTIONAL` carried four properties
  Python's did not. Adding them to Python broke six tests immediately, which is the finding:
  **DECIDED and COMPLETE are two different questions.** `INTENTIONAL` is what a design chose and is
  what gets written into a cell string; `COMPLETION` — `waterlogged`, `powered`, `persistent`,
  `open` — is what must ALSO be true before a cell is finished. Both ship; `role()` takes the union
  because it only ever asks whether a property must match.
- **AND 147 CELLS COULD NEVER MATCH.** Nothing in the mod opens a trapdoor, so `open=true` kept
  `todo` non-empty for ever, `placementComplete()` was never true and `follow all` never moved on.
  It is DECLINED now, like the redstone commissioning pass: work the builder hands back, reported
  and excluded, never retried.

`analyze.clickable` was already ported from `Printer.support` by the audit itself.

### 4. Dig and place, ordered — and it needed no token

2,970 cells of `Park Complete` are in the design AND on its dig list (2,933 of them the ground plane
a lake and a well are cut through), and nothing expressed which came first: `split` put the cell in
`todo` while `digLeft` returned it as still standing, on the same tick, under the same radius. An
unattended session could place a block and break it again for ever.

**Two rules, both of which follow from what the lists MEAN:**

- a dig cell that is still solid is an obstruction, so it is not placeable yet — it goes to
  `manual` and leaves by itself the moment it is broken;
- a cell already holding what the design wants is the FINISHED BUILD, not the obstruction, and is
  never dug. Without the second the pair loops.

`Digger.design()` gives the digger the design's own cells so it can tell one from the other.

### 5. `sync` measures a world the design is actually in

`sync.yaml` tracked `Park Complete` and scanned `island` — the old island, 121,000 blocks away — and
printed `0/541753 built (0%)` every day for the life of the park. Every cell was out of the box, and
the honest word for that is UNKNOWN; but `oob` was the last clause of a line whose first clause was
a percentage, so the lie led and the reason trailed, and `history.json` recorded the zero into the
velocity slope.

- **`Progress.measured`**: under half its cells inside the world and it prints NOT MEASURED with the
  count, rather than a number nobody can compute. Same rule as a park gate with no evidence.
- **`worlds:`** in `sync.yaml` is the list of captures available; `world_for` picks the one whose box
  holds each design's origin. **A heuristic on purpose** — getting it exactly right means loading
  half a million cells to compute a box, and the honest check is downstream and free.
- **An unmeasured design is never recorded in history**, and is shopped WHOLE, because "we do not
  know what is built" is not "nothing is left" and the safe direction for a shopping list is to
  assume the work.

**THE PARK IS STILL NOT MEASURABLE, AND THAT IS NOW THE REPORT RATHER THAN A ZERO.** The only park
captures are the three bare starter pads from 2026-08-31 — 189, 144 and 192 blocks. Scan the plots
at plot scale and add them to `worlds:`.

#### ...and `work.json` became a manifest

21 MB of cell lists that nothing read: `Work.cached` takes the LITEMATIC whenever one exists beside
the sidecar, which is always. It was also written at 2 of the 21 places a design gets written, so
`Park Buildings.work.json` was a day older than its own litematic.

- **`scan.save_pair` emits it**, so it cannot go stale — the same move `finish.carve_for` made when
  re-carving stopped being a note in a config and became a pipeline step. **A step that has to be
  remembered is a step that gets lost.**
- **It carries what the mod cannot get from a litematic** — origin, dig list, count — and the cells
  only when there is no schematic to read them from. `Casino Complete.work.json` is 142 bytes.
- **An absent cell list is an ERROR on the Java side, never an empty design.** Read as "no work" it
  would report every design complete, which is the one failure worse than a stale file.
- **A CAPTURE IS NOT A DESIGN**, and the markers tested are the CAPTURE's — `Designs.isDesign`'s own
  asymmetry: absence of evidence that a file is a capture is good evidence it is a design, and the
  reverse does not hold.

The 367 existing fat work lists are left to shrink as their designs regenerate; converting them in
one pass is 92 MB of churn in tracked files and is Jack's call, not a silent one.

### 6. The movement and accounting list

- **`overTop` was unbudgeted and unranged.** It ran before any tier deadline was consulted, so a
  cross-park hop walked thousands of heightmap lookups and tens of thousands of `Nav.clear` samples
  FIRST — and every tier then "failed" on a deadline that had already passed, reporting no route
  where the geometry was never examined. It has its own share (15%), stops past `Nav.MAX_RANGE`, and
  samples the corridor at 128 points however long it is. **Under-sampling cannot cause a collision**,
  only a crossing height too low, which `Nav.clear` then rejects — an honest failure.
- **`Ignored` had no expiry**, and two of the three paths that strike it are not about the place: a
  search that runs out of its millisecond budget returns the same empty list as one that proved
  there is no way through. Two slow ticks deleted an eight-block cube of the park for the session.
  Ten minutes, expiring lazily.
- **A moving destination reset the recovery ladder.** A station re-centres on the cells still to
  place, so in follow mode the target drifts on every recount and `trouble` was zeroed twice a
  second — the whole escalation was dead code in the one mode it was written for. A target inside
  `SAME_TARGET` is the same destination, which is `Loop.sameSpot`'s hysteresis and its reasoning.
- **`Work.room` assumed a 64 stack** for any item the pack was not already carrying, so a trip for
  buckets, signs or shulker boxes was sized at up to sixty-four times the truth: the withdrawal
  over-asked, took what was there, and blacklisted the chest that actually had the material.
  `maxStack` asks the game (rule 11, applied to a number nobody thought of as a block property).
- **`Work.tally` was wrong in both directions**: a door and a bed are two cells and one item, a
  double slab is one cell and two slabs. One sends you shopping for what you have, the other sends
  you back for what you ran out of.
- **A blank board counted as a built sign.** The block lands, `matches` says yes, and the text is a
  second action that can time out — so `SignWriter.verification`, `written` and `report` had no
  callers at all. A board still waiting for its words goes to `manual`, never to `wrong`: it is an
  outstanding ACTION, not the world holding something else.
- **`everCache` is keyed on the cell being judged and the judgement is about the world AROUND it**,
  so placing a block never invalidated the verdicts that placing it had just changed. A lantern
  waiting on a wall stayed written off until the thirty-second `relax`. `Printer.forgetNear` drops
  six neighbours on the one event that can change the answer; `forgetPlaceability` had no callers
  at all and stays as the blunt version.
- **Slicing a plan dropped the back of every sign, its colour, and every non-sign tile entity**, and
  `scan.merge` dropped tile entities entirely. Both carry the whole compound now, re-addressed
  rather than mutated, and only where the BLOCK survived — a tile entity with no block is a corrupt
  region rather than a lost line.

### And the frame rate, which the audit could not see

Four parallel readers went through the loop's decisions and none of them measured what a decision
COSTS. Two per-cell filters in `Hud.advance` were doing a path normalisation, two monitor
acquisitions and a stream allocation on every one of half a million cells, twice a second — on the
tick that also prints the chat line, which is why *"every time there's a chat update there's major
lag"* is a precise diagnosis. It survived four readings because it reads as a boolean.

`Islands.Gate` resolves the plot lookup once per pass, `Rules.inLockedProfile` is memoised per
block, and the predicates are ordered by what they cost. `Perf` now times `loop decide` and
`loop filter` as well as the diff — it timed only `Work.split`, so the report would have blamed the
wrong half.

**An audit that reads the logic should include a measurement pass over the hot ticks.**

### Still open

- **Nothing here has been flown or placed in game.** 687 Java tests and the Python suite pass; the
  jar is built and not uploaded.
- **`prices.json` is empty**, so `buy` is never an available source and `cheapen --by-price` is
  inert. One shop walk fixes it.
- **The park has no capture at plot scale**, so its progress is honestly unknown rather than zero.
- **Eight of the nine lot modules still have no sidecar**, so they exist only inside the composite.
  Untouched: `park_lots` is another session's live area.
- **`tests/test_frontier.py` fails with `KeyError: 'prismworks'`** in `frontiertown.py`, and
  `test_worldrender` / `test_park_vantage` / `test_evidence` / `test_park_games` carry their own
  pre-existing failures. All verified against a clean tree before this work and none of them touched.

