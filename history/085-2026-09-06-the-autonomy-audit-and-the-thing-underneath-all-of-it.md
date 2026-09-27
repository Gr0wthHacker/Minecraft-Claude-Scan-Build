## The autonomy audit (2026-09-06) — and the thing underneath all of it

Jack: *"audit carefully and identify how we improve this all functionally."* Four parallel read-only
audits — the loop's decisions, movement, placement and materials, the Python pipeline — plus a
measurement pass over the design that is actually being printed. Everything below was verified in
the code or against the artifact before it was written down; findings that could not be verified are
marked as such rather than listed.

### THE LOOP IS A LAST MILE WITH NO SUPPLY CHAIN

Measured against `Park Complete` (541,753 cells, 182 materials) and the live container index:

| | |
|---|---|
| materials the PARK-LOCAL chests can cover | **9 of 180** |
| blocks with no reachable source | **413,685 (76%)** |
| materials not indexed anywhere at all | 86, 69,281 blocks |
| worst single line | `moss_block`: **103,089 short** — and it has no recipe, because moss is a bone-meal FARM |
| the old island's chests | 180 containers, **~121,000 blocks away** — `Loop.FETCH_RADIUS` is 400 and `Nav.MAX_RANGE` is 512 |

**Every stall, every spam, every flight fix this month has been the last mile of a journey whose
goods were never made.** The mod can already `craft`, `smelt`, `buy`, `farm` and `take`; nothing
plans acquisition as part of a build, so the loop's honest answer to most of this design is a shrug.
The single highest-value thing that could be built is a PROVISIONING phase: given a design, resolve
what must be made, bought or farmed, drive those commands until a park-local work package is
covered, and only then start placing. Until then a "build the park" instruction is 76% unbuildable
and the loop cannot say so.

Two supporting facts, both measured:

- **A trip is sized in stacks, never in boxes.** `Work.loadCapacity` is `empty slots x 64`, so the
  biggest possible load is 2,304 blocks and the park needs **235 of them**. A shulker box holds
  1,728, the mod already takes boxes and already unpacks them — sizing a trip in boxes is ~9 trips
  instead of 235. Nothing does the arithmetic in boxes.
- **`prices.json` does not exist**, so `/cscan buy` and `cheapen --by-price` are inert: the shop has
  never been walked.

### The craft resolver plans 3,358 IRON PICKAXES

`python -m mcbuild craft "Park Complete"` proposes smelting 3,358 iron pickaxes into nuggets for 426
lanterns — **10,074 iron ingots where 379 would do**, on the island whose scarce metal is iron.

The cause is two faults compounding, and the first is a FIX FOR SOMETHING ELSE. `mark_reversible`
bars packing pairs from cost-minimisation because costing every leaf at 1 makes `raw_gold_block` a
cheaper source of raw gold than raw gold. True — and `iron_ingot -> 9 iron_nugget` is a packing pair
too, so the CORRECT and only sane route to a nugget is barred, leaving "smelt a tool" as the winner.
On top of that `raw_cost` returns **1.0 for `iron_nugget`, `iron_ingot` and `iron_pickaxe` alike**:
anything not derivable more cheaply is a leaf costing one, so a crafted tool is as cheap as an
ingot. A guard against arbitrage produced arbitrage.

### Python and Java disagree about what a block IS

Three separate drifts, all of them the repo's own one-source rule broken across the language
boundary, and all three now measured:

- **The item name.** `ActionRecipe.itemFor` maps `water -> water_bucket`, `oak_wall_sign ->
  oak_sign`, `water_cauldron -> cauldron`. Python has no such map, so `craft`, `analyze` and `shop`
  ask for items that cannot exist and report them as unobtainable: **7,965 cells**, 7,803 of them
  water.
- **The block state.** `work.INTENTIONAL` (Python) and `StateContract.INTENTIONAL` (Java) are the
  same list written twice and have drifted: Java additionally requires `waterlogged`, `powered`,
  `persistent` and `open`. Measured on the shipped composite: `persistent=true` 14,808,
  `powered=true` 1,184, **`open=true` 147**. The rails are already declined as commissioning, and a
  placed leaf IS persistent — but nothing in the mod opens a trapdoor, so **147 cells can never
  match, `todo` never empties, and `placementComplete()` is never true.** A design that cannot
  finish is a `follow all` that never moves on.
- **`analyze.clickable` vs `Printer.support`.** Two hand-written lists, drifted badly: Python said
  yes to every chest, barrel, furnace, hopper, door, trapdoor, fence gate, bed, note block, jukebox,
  cauldron, lectern, bell and flower pot — and to bare `torch`, which `endswith("_torch")` never
  caught. That is not a reporting nicety: `printable.closure` chains through it and
  `printable.stitch_model` WRITES the result into the shipped composite. **FIXED by porting
  `Printer.support` rather than paraphrasing it**, and the corrected rule immediately exposed
  diagonal breaks the loose one had hidden.

### Six defects fixed in this pass

- **THE SPOT COOLING-OFF WAS COMMENTED OUT.** `Hud.java:1249` had two statements on one line, so
  everything after the first `//` was a comment and `Loop.avoided` was never called — populated,
  cleared, never read. `abandonSpot` nulls `spotCentre`, so the next recount re-picked the SAME best
  cluster, flew at the same wall and stuck again: abandon, re-pick, abandon, every two seconds, until
  `THRASH_LIMIT` killed a design that had one awkward spot in it. The whole `AVOID_MS` machinery has
  never run.
- **The vicinity hold forbade its own printer.** The hold returns before `BuildJob.decide`, so the
  phase stayed whatever the last recount set — `PARKED` after a dead end or a look — and
  `AutomationControl.enter(PRINT)` refuses unless the phase is `BUILD`. The loop announced it was
  staying until the cells were in, placed nothing because it had forbidden itself, and blamed the
  world five seconds later.
- **A SUCCESSFUL look counted as a look FAILURE.** `Autopilot.arrivedAt` is true precisely when the
  flight REACHED the cell; two successful hops onto already-built ground therefore wrote the design
  off as finished. The failure is arriving and the chunk STILL not being loaded, which is what it
  tests now. And with autofly off `parked` was permanently false, so the look branch returned true
  every recount for ever — no placement, no fetch, no message, and no clock able to see it.
- **`Burial` was a regression I shipped in 0.8.6.** `Nav.standoff` prefers a spot with headroom, so
  `canRise` is true at EVERY station it picks; two walled sides is standing beside the wall you are
  building. Fired there it outranked arrival and steering: rise, sides open, fly back down, for ever.
  It is gated to the case it was written for — the digger working, or no destination at all — and a
  body walled in WITH somewhere to go is the recovery ladder's case, which already escalates from
  not-moving. Its step also set velocity directly, bypassing `Bounds.clamp` and `avoid`: the one
  movement path never tested against a block, on a server where contact ends flight. The caller owns
  the step now; `Burial` owns only the decision.
- **`park_place.py --ship` silently withdrew the mod's permission to build.** `Designs
  .requireAutonomousApproval` refuses any design whose `anchor_status` says preview/provisional/
  rebase and demands `automation_approved: true`. **No Python in this repo has ever written either
  key** — they were set by hand — and `save_pair` replaces a sidecar rather than merging, so the next
  ship would have reverted both and the mod would have refused the park with a message about a
  status string nobody set. A ship re-states geometry; it does not withdraw consent.
- **`/cscan auto <name> 0` is a world capture every tick.** Clamped to a minute.

### Found, verified, NOT fixed — these need a decision, not a patch

- **2,988 cells are in the design AND on the dig list.** Measured: 2,082 of them water, 2,933 at
  Y202, the ground plane. The mod has no way to express "break this, then place that" — `split` puts
  the cell in `todo` and `digLeft` returns the same cell as still standing, on the same tick, under
  the same radius. An unattended printer can place and re-break one block for ever. `park_place
  .complete()` honours the dig list for the ground and the railway but not module-against-module.
- **`work.json` is 21 MB that nothing reads.** `Work.cached` takes the litematic path whenever a
  `.litematic` exists, which is always; `loadWork` is a dead fallback. It is also written at only 2
  of 21 places a design is written — `Park Buildings.work.json` on disk is a day older than its own
  litematic. The structural answer is to make it a small MANIFEST (origin, digest, dig list, `after`,
  approval, the needs-a-hand set) emitted by `scan.save_pair`, and to ship the print ORDER that
  `printable.closure` already computes and throws away.
- **`overTop` is unbudgeted and unranged.** It runs before any tier deadline is consulted and is
  gated only on distance >= 4, so a cross-park hop walks thousands of heightmap lookups and ~20k
  `Nav.clear` samples before the first search starts — then every tier "fails" on a deadline that had
  already passed, and reports no route where the geometry was never examined.
- **A budget failure is indistinguishable from "no route", and two of them delete an 8-block cube of
  the park for the session.** `Ignored` has no expiry, and three unrelated give-up paths all strike
  the same key.
- **A moving destination resets the recovery ladder**, so in follow mode — where the target re-aims
  as cells are placed — `trouble` is zeroed before it reaches the first rung and the whole
  escalation is dead code.
- **`Work.room` assumes a 64 stack** for any item the pack is not already carrying, and the shared
  `dumpFree` slot budget is credited to EVERY item independently — so `PACK_FULL` is unreachable
  while one junk stack is held, and a withdrawal over-asks and then blacklists the chest that
  actually had the material for 60s.
- **`Work.tally` counts a double slab as one item and a door as two.** Small here (0 double slabs, 6
  door cells, 97 two-cell plants) but wrong in both directions.
- **The printer places outside the autofly fence and off-plot.** The loop filters its work by
  `Bounds` and `Islands`; the printer's own candidate loop applies neither.
- **A sign is "built" the moment the blank board lands** — `SignWriter.verification()`, `written()`
  and `report()` have no callers, so a timed-out text update is invisible to completion.
- **`Printer.forgetPlaceability()` is dead code** and `everCache` is keyed on position alone, so
  placing a block does not invalidate its neighbours' verdicts.
- **Slicing a plan drops back-of-sign text, sign colour, and every non-sign tile entity**, and
  `scan.merge` drops tile entities and entities entirely.
- **Eight of the nine lot modules have no sidecar anywhere**, so they exist only inside the composite
  and cannot be placed, checked or progressed on their own; the one that does have a sidecar records
  a world origin 48 blocks from where the composite puts it.

### And the daily loop has been measuring the wrong world

`sync.yaml` tracks `Park Complete` and scans `island` — the OLD island, 121,000 blocks away. Run
today:

    Park Complete: 0/541753 built (0%), 541753 outside the scan box (unknown)

Progress, the velocity slope in `history.json` and the shop list have been answering about a world
the park is not in, for as long as the park has been tracked. It is the same shape as the
below-Y150 blindness this file already records, and the fix is the same: `sync` needs the world the
tracked design is actually in.

### What to build next, in order

1. **Provisioning.** Nothing else matters at 76% unsupplied. Resolve a design to what must be made,
   bought or farmed; drive the commands that already exist; report a work package the loop can
   actually finish.
2. **Fix the craft cost model** (unbar legitimate unpacking; stop treating every underivable item as
   cost 1) before anyone acts on its output.
3. **One block-identity source.** `itemFor`, `INTENTIONAL` and `support`/`clickable` generated into
   `chunkscan_rules.json` the way the protection and economy rules already are, rather than written
   twice.
4. **Make `dig` and `cells` disjoint by construction**, or carry an explicit order token per cell.
5. **Point `sync` at the park**, and make `save_pair` emit the work manifest so it cannot go stale.
6. Then the movement and accounting items above, which are real but are polish until 1–5 land.

