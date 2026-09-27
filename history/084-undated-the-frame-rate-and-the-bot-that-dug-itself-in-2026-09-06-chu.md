## The frame rate, and the bot that dug itself in (2026-09-06, chunkscan 0.8.6)

Jack: *"its scanning too fast, you start autofly and its supremely laggy, basically no frames per
second"*, and separately *"we also need to make sure the bot doesnt dig itself into a hole - its
multiple times now sat still and dug completely around itself. If it starts to have sides of itself
covered, e.g. 2/3 sides of body, it should move up etc to start avoiding being stuck."*

### THE RECOUNT WAS THE FREEZE, AND EVERY LINE OF IT LOOKED CHEAP

`Hud` recounts the followed design every 40 ticks with `Work.split(..., radius 0)` - **the whole
design, which on `Park Complete` is 540,862 cells**. That much is by design and has to be: the loop
needs global counts to know it is finished. What was not by design is what each cell cost, and all
four of these are one-line call sites that read as free:

| per cell, ~270,000 times a recount | was |
|---|---|
| `StateContract.parse` | `synchronized`, over an **access-ordered `LinkedHashMap`** - which REWRITES ITS LINKED LIST ON EVERY GET. Every lookup was a structural mutation under a monitor |
| `Work.matches` | `BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath()` - a registry lookup and a substring, per cell |
| `ActionRecipe.order` | **the sort key**, and it parsed the state string and allocated a `HashMap` every call. In a comparator over ~100,000 cells that is about **3.5 MILLION** parses and allocations per recount |
| `Printer.props` | the same parse again, under `order`, `doubleSlab` and the placement sweep |

Plus `digLeft` walked **all 9,846 dig cells** with `isLoaded` + `getBlockState` on every `split` -
and `split` runs on **every printer tick**, so a bound that exists to keep work local was costing
two hundred thousand world lookups a second to produce a list of nothing.

All four are memoised now (a design has a few hundred distinct block states, so it is one parse
each, ever), the sort is DECORATE-SORT-UNDECORATE so the key is computed once per cell rather than
twice per comparison, and `digLeft` takes the radius and filters BEFORE it asks the world - a
distance test is free and a chunk lookup is not.

**AND THE CACHE THAT CAUSED IT WAS SOMEBODY'S FIX FOR SOMETHING ELSE.** An LRU is the obvious shape
for "cache the last N", and an access-ordered `LinkedHashMap` is the obvious LRU - and its eviction
policy costs a WRITE ON EVERY READ, which is the opposite of what a read-mostly cache wants. Both
new caches are bounded and simply stop filling: a world with more distinct states than the cap gets
no caching, which is exactly what it had before.

### `/cscan perf` - because this was diagnosed by reading the code three times

`Perf.java`, and it is the honest lesson of the session. Every subsystem was affordable alone and
the arithmetic between them was the problem; no amount of re-reading was going to settle which one
dominated, and two separate confident guesses - the highlight gizmos, the router's four search
tiers - were wrong. It times whole subsystems (`recount`, `printer scan`, `autofly`, `highlight`)
and prints mean AND worst against a 50 ms tick budget.

**MEAN AND WORST, NEVER ONE OF THEM.** A recount costing two seconds every fortieth tick has a mean
of 50 ms and is the thing you can feel; the mean alone hides it among the ticks that did nothing,
and the worst alone cannot tell a one-off chunk load from a permanent cost. One `nanoTime` pair per
section per tick, no allocation, a fixed ring: a profiler left on overnight cannot grow.

    /cscan perf            what this mod costs the client thread, per subsystem
    /cscan perf reset      ...over the next window only

**Also found: `/cscan auto <name> 0` is a world capture EVERY TICK.** `everyMs = minutes * 60_000`
and the timer is satisfied on the tick it is set and every tick after it. Clamped to a minute
rather than refused - a typo should cost a slower scan, never the session.

### `Burial` - walled in on two sides, and nothing could see it

**EVERY WATCHDOG IN THIS MOD ASKS WHETHER THE LOOP IS TRAVELLING AND FAILING TO ARRIVE.**
`NOWHERE_MS`, the station stall, the thrash detector, the recovery ladder - all of them. A bot
standing exactly where it means to stand, breaking exactly the cells its dig list names, is not
travelling and is not failing: it is succeeding, one block at a time, into a pit of its own making.
The fault exists only in the GEOMETRY around the body, so that is what is measured.

Two halves, and neither is enough alone - a bot can be walled in by a trench it did not dig, and it
can sink through a floor with no walls at all:

- **`Digger.Verdict.UNDERFOOT`.** The floor you are standing on is not a cell to break. Tested
  against the BODY's own 0.6-wide footprint rather than `blockPosition()`, which is a rounded
  centre and says nothing about which blocks are carrying it. **POSITIONAL, so it is SKIPPED and
  never given up**: written off here, the loop could never come back and dig it from the side, and
  the design would carry a cell nobody may ever break.
- **`Burial.lift`.** Two of four sides walled - Jack's own threshold - and it rises. A side counts
  only when BOTH body cells are blocked, or every kerb in the park is a wall.

Three things it has to get right, each of which is a rule this project already paid for:

- **A ROOFED PLACE IS NOT A PIT, however walled it is.** A mine gallery, the undercroft, a tunnel
  the loop is meant to be inside: walled by design and roofed, so rising is grinding a ceiling -
  which `keepAirborne` has done. `canRise` is what makes the whole thing safe underground.
- **TWO SIDES IS ALSO A DOORWAY**, a corridor, and a trench between two spoil heaps. The geometry
  cannot tell those from a grave and TIME can, so it must hold for `HOLD_TICKS` (one second). A bot
  that lifts out of every doorway it steps into cannot build anywhere narrow.
- **IT ONLY EVER RISES, AND NEVER VIA THE JUMP KEY.** Which way is *out* is a search, and the
  recovery ladder owns searches; up is the one direction always right in a pit, and one course of
  it re-opens the sides, which ends it by itself. `jumpFromGround`, not the key - driving that key
  is a double tap inside seven ticks, which is the mistake that once revoked Jack's flight in
  mid-air.

It is checked in `Autopilot.tick` immediately after the fall rescue and ABOVE the destination
check, for the same reason the fall rescue is there: a bot digging itself in usually has nowhere it
is trying to go, which is precisely why nothing noticed.

`BurialTest` (8) is pure geometry with no client in it; 671 Java tests, 0 failures.

**Still open, and it needs a flight to settle.** The fixes above are reasoned from what each call
site costs multiplied by how often it runs, and the memoisation is certain to help - but WHICH
subsystem dominates has not been measured in game. Run `/cscan perf` while it is laggy; if
`recount` is still the top line, the next move is to stop building a fully-materialised todo list
for the whole design on every recount and give `Split` a global COUNT with a bounded cell list.

### The shopping list shouted loudest while achieving nothing (2026-09-06, chunkscan 0.8.7)

Jack: *"shopping list keeps getting spammed."*

`loadPlan` is cleared at the end of every recount that is not a fetch — *the list belongs to the
trip*, which is correct and is what stops a chest across the island re-sizing a list that was made
at the work. But the ANNOUNCEMENT was tied to the list being BUILT, and the list is rebuilt every
time it is missing. So whenever the loop wanted to fetch and could not — nothing indexed holds the
material, no room in the pack, every candidate chest still cooling off — it rebuilt an identical
list and said it again, **every two seconds, for as long as that stayed true.**

**IT WAS LOUDEST EXACTLY WHILE IT WAS ACHIEVING NOTHING**, which is this file's own rule about a
message on a two-second timer being a reason to turn the loop off, arrived at from a new direction:
the guard was on the wrong event. Building a list is not news; a trip changing is.

`saidLoadPlan` holds the last announced list and it is keyed on the **item SET, never the counts** —
the counts drift by a few every recount as the pack changes, so a signature carrying them is a
signature that always differs. What a trip IS, is what it is going to fetch. Reset when a new job
starts (`off`, a new design), never on the per-recount trip end, or the guard would clear itself on
exactly the tick it exists for.

**And the rest of the recount's messages were audited rather than assumed.** Every
`sendSystemMessage` inside `advance` was checked for a guard: three read as unguarded and all three
are one-shot state transitions that clear the condition as they fire (`topUp = false`, the
re-anchor, the design-complete hand-off). This was the only one that could repeat.

### ...and it was still spamming, because the list itself was never the same twice (chunkscan 0.8.9)

Jack, on 0.8.7: *"shopping list is getting constantly spammed and stopping all progress."* The
guard was right and it was guarding a thing that genuinely changed on every recount, and **the
same line that made it change is what stopped the progress**:

    if (!fetching) loadPlan = null;                      // the list belongs to the trip

**A TRIP IS NOT ONE RECOUNT.** Cleared on any phase that was not a FETCH, the list was thrown away
and remade every two seconds in exactly the states where the loop is oscillating — PACK_FULL, a
DEAD_END, every candidate chest still cooling off. A remade list is a DIFFERENT list, and the list
picks the chest: a new target every two seconds, a flight redirected before it arrives, and the
announcement again each time. One line, both halves of the report.

**AND THE CUT POINT OF A CELL BUDGET IS UNSTABLE BY CONSTRUCTION.** `loadPlan` filled to
`empty slots x 64` cells, ordered by course and then by distance to the anchor — and the anchor
drifts as cells go in while the budget shrinks as the pack fills, so **which materials fell either
side of the line moved on every recount.** The signature is the item SET, so it changed too. A
budget that reaches into forty materials is also the "stacks up with random resources" complaint
from two sessions ago: a trip for forty things finishes none of them.

Three changes, in that order of importance:

- **A trip is a handful of materials.** `Plan.MAX_MATERIALS` is 6 — enough that a course of
  masonry with its trim and its lighting is one journey. A material past the cap is SKIPPED rather
  than ending the walk, or the list would depend on the order the area happened to arrive in.
  Capped at MATERIALS the list is a decision rather than an accident, and it changes only when the
  WORK does: the same area at two different budgets is now the same list.
- **The list is kept until the trip is actually over** — `Hud.tripOver`: the pack holds it
  (`Plan.covered`), the anchor moved more than 24, the design changed, or it is five minutes old.
  Plus the healthy case, which is what the old line was reaching for: the phase came back BUILD
  with something to place, so the trip was declined.
- **And it is said at most once a minute** whatever else happens. A signature is a guard against
  repeating yourself; a clock is a guard against a future list finding a new way to differ.

675 Java tests, `chunkscan-0.8.9.jar` built, not flown.

