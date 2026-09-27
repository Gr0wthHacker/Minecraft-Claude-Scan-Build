## The loop audit: every way the unattended build could sit still (2026-09-04)

Jack: *"do a deep audit of all aspects of the autonomous work flows, navigation, fetching, etc"*,
with two reports from the field: *"it doesnt get close enough to chests, chests need to be within
2 blocks"* and *"it seems to stack up with random resources vs things it logically might need
based on the radius around it"*. Three parallel audits — the router, the decision layer, the
material handling — came back with 68 findings; 40 are fixed here, all 591 Java tests pass, and
`AuditFixesTest` pins the ones that can be pinned without a client.

**THE SHAPE OF ALMOST EVERY DEFECT WAS THE SAME: A CLOCK THAT COULD NOT SEE A PHASE.** The stall
clock skips while fetching; the going-nowhere clock skips while fetching; the LOOK phase reset
its own target every recount. So a chest the flight parked short of, and a chunk that never
loaded, were both an infinite silent hover — the "does nothing, quietly" failure this file has
written rules about a dozen times, in the two phases none of those rules covered.

### The chest (Jack's first report) was three faults stacked

- **The approach cell was chosen NEAREST THE PLAYER**, up to 4.5 from the chest, and it moved as
  the player moved. `ContainerInteraction.approach` now ranks by distance to the CHEST — within
  two blocks preferred outright — and takes a set of cells already tried.
- **The flight could not descend to it.** `keepAirborne` holds the body 2.5 blocks off any floor,
  and chests stand on floors, so it hovered over the cell it was sent to and the opening test never
  passed. An approach cell must now have a clear cell UNDER it, and a target the body must actually
  occupy (`Hud.guideExact`) is flown with `EXACT_CLEAR` 1.05 — still over the block of air this
  server ends flight inside of — and an arrival ceiling of 1.6 instead of 3.0.
- **Nothing timed it out.** `FETCH_STUCK_MS` (6s parked, or the flight reporting arrival, with no
  opening ray) moves to the next approach cell; no cell left cools the chest off like an empty one.

### The pack (Jack's second report) was sized to the design

The shortfall was totalled over the WHOLE design and rotated 256 at a time across every material,
so a forty-material park filled the pack with whatever its far end wanted. `Plan.nearDemand` sizes
the fetch from the working anchor outward — the frontier first, then the nearest remaining cells
until they would fill the pack (`Work.loadCapacity`), and never a cell nothing can ever place.
The chest being flown to is latched for the trip, so two chests at nearly the same distance no
longer take turns being the target mid-flight.

### The router

- **A sloped leg was checked as a two-cell body at a rounded y.** Between courses the body is
  THREE cells tall; `clear` now spans floor(py+0.1)..floor(py+1.9). The old check passed a leg
  whose head went through a ceiling block, and `simplify` then straightened routes through it.
- **`escape` parked the body flush against the wall it was escaping** — the nearest cell to the
  goal is by definition the one touching the obstacle. A roomy cell (six clear neighbours) that
  improves at all is taken first; the flush one only inside a corridor, where nothing is roomy.
- **Staged and escape routes are PARTIAL, and were consumed as complete**: the flight reached the
  stage's end, flew DIRECT at the thing that had no route, and struck the spot for it. `Nav.Route`
  carries `complete`; `route()` returns complete routes only; the autopilot re-searches at the end
  of a stage and strikes only on `noRoute` — and strikes the SPOT CENTRE the loop filters by
  (`Hud.strikeKeyFor`), not the stand position fifty blocks from it that nothing looked up.
- **Staging was dead code** — the direct search spent the whole shared budget and staging broke
  on its first iteration. The direct search gets 60% when the goal is far.
- **A start cell the body did not fit in failed every search** (a slab, a carpet, a lip): the step
  box included the cell being left. The origin is excluded and an unfit start relaxes to the
  nearest fit cell.
- **`pocket`/`escape` marked a cell seen BEFORE the corner rule** rejected the step, so an L-bend
  read as a sealed pocket and the recovery ladder typed `/is` from inside a good corridor.
- **`reachable` broke ties by iteration order**, aiming at the far side of a chest in a wall about
  half the time. Ties go to the player's side.
- **Passability is the COLLISION SHAPE now, not `blocksMotion()`**: carpets and snow layers have a
  box the feet land on and no motion flag; an open door has the flag and nothing in the doorway.
- **One deadline for the roomy search, the tight search and the escape flood**; the stale-entry
  skip in A*; the deadline checked every 32 expansions rather than 256; `sees` cast from the eyes.
  A roomy route is simplified with the roomy predicate, or the chords threw the elbow room away.

### The loop

- **`follow all` shuttled between two FINISHED designs** — each read as "has work" because its
  cells were out of view from the other. Designs seen complete, handed back, or whose unseen cells
  would not load twice are never returned to; real work beats unseen-only.
- **DEAD_END, PACK_FULL and every-spot-ignored never advanced** under `follow all`. They park the
  design and move on. A `follow` that throws on the switch parks that design instead of dying.
- **A chunk unloading counted as placement** (todo shrank), inflating the report and blinding the
  thrash detector. Progress is the shrink `unseen` does not account for.
- **The going-nowhere clock fired with autofly OFF** every three seconds a manual follower paused;
  it is gated on the autopilot. STALL, the all-bins-tried retry and the cluster cap ejecting the
  current spot all go through `abandonSpot` now, so they count and are passed over.
- **A `Work.split` exception killed the loop silently** on the first hit — `following` stayed true
  with a null design. Three in a row stops properly and says so.
- **The printer's "never placeable" cache was never re-asked** while a design was followed; a wall
  torch judged before its wall existed stayed out of the frontier for the night. `Printer.relax`
  every 15 recounts.
- **A chest that WORKED was skipped for targeting** by the 5-second OK window (one map for two
  facts); `coolingOff` is failures only, `recentlyFailed` covers both. And the withdrawal's stop
  test counted boxed stock while the target handed to it did not, so a pack holding a shulker of
  the material took nothing and blacklisted a full chest.

### Placement and the things that ended the night

- **One missing placement ack ended the session.** It is a refusal of that cell and a slower pace;
  five in a row stop. Refusals ease the interval off, placements restore it.
- **A transfer whose answer never came ended the session**; the PACK is the truth, so the gain is
  counted from it, journalled UNCERTAIN, and only a run of three stops.
- **An OPENING failure left the chest GUI open**, which halts the autopilot, the loop and the
  printer until a human presses Escape. Our own screens are closed on failure and cancel.
- **The water bucket path was inert** — `BucketItem` overrides only `use()`, so `useItemOn` did
  nothing and every water cell was written off twice. It aims at the placement ray and uses
  `useItem`, and only where every horizontal neighbour and the cell below is already solid or
  water IN THE WORLD, or it pours the design's own basin away.
- **The printer placed nearest-first**, taking a ceiling before the wall that needed its face.
  It walks the design's own order and takes the first placeable cell in reach.
- **The digger dug nearest-first with whatever was held**: the Falls' notch — "cut it LAST" — could
  be cut first, and deepslate by hand passed a flat 120-tick give-up as "wrong tool". It digs in
  list order, never the last cell while another remains, holds the fastest hotbar tool, and gives
  up at twice the block's own expected time.
- **Unbox could only recover a box that landed within pickup range**, and searched three cells
  out; a site is adjacent, at foot level, with its lid cell clear. Soft failures no longer end the
  session; a box left out in the world does, through `Hud.stopForSafety`, which also clears the
  saved session so the next join does not resume into it.

**Deliberately not changed:** legacy index records with no dimension stay excluded from automatic
withdrawal — `BuildAuditTest` pins it as a rule, and it is one. Double chests are still indexed
per half and double-counted. `standoff`'s last-resort fallback still returns a cell the autopilot
cannot descend to (the station ladder handles it). None of this has been flown in game yet.

### Landing: work on a floor has no hovering stand (2026-09-04)

Jack, after the first jar: *"it is hovering above a group thats not placeable; i think we need
to also analyze area and identify when it can land and it should take off by itself"*.

**THE HOVER WAS STRUCTURAL.** A flying stand needs three clear cells under it (`Nav.AIR_BELOW`)
and the flight holds two and a half off any floor — both right for work on a wall, and both
impossible for work ON a floor: paving, a lawn, the bottom course of anything. Over a plate no
cell qualified, the fallback was the centroid, the flight parked three blocks over it, and the
printer reached nothing. Every station stalled, moved in closer (to another hover), abandoned,
and the next bin did the same. And it was worse than it looked: the stand's coverage was measured
from the FEET, so a stand four courses up "covered" paving its eyes were 4.6 blocks from, and a
stand UNDER the plate covered the paving on top of it, through the floor.

- **`Plan.groundStand`** — a cell the body fits in, with a real floor under it (a 3x3 pad, not a
  ledge over the void), that is not itself work still to place, from which the eyes are within
  reach of the most cells. `Hud.standAt` computes both stands and takes the ground when it
  covers at least as much as the air, because a body on a floor does not drift, holds no
  altitude, and cannot lose flight by touching something.
- **Coverage is from the EYES and only of cells the eyes can SEE** (`Plan.coveredFrom` with a
  `Passable`), for both kinds of stand. `Nav.sees` lost its "adjacent is always seen" shortcut,
  because the cell directly above the eyes' own ceiling is adjacent.
- **A landing is a target mode** (`Hud.Mode.LAND`). The flight descends onto the floor and lets
  flight end — on this server that is what contact does, and here it is the plan, so the
  mid-air-revocation emergency is suspended inside the last two and a half blocks. Arrival is
  standing on the cell.
- **It takes off by itself** through the existing double-tap (`Autopilot.regain`), now gated on
  `needsFlight`: a hovering station or a chest approach always needs the air; a landing does not
  if it can be WALKED to — a body standing beside the next patch of paving walks over, and only
  takes off when the walk is long (`WALK_AT_MOST` 24) or there is no walking route.
- **A landing that still reaches something of what is left is not re-aimed**: the orbit that
  moves a hovering station round its work would otherwise take off from a good floor because it
  placed something.

`tests/LandingTest.java` (5) and the rewritten `aSpotWithNoAirUnderItIsNotASpot` pin it: a
row of paving on a plate has no hovering stand and a landing that reaches it; a one-wide ledge
is not a floor; reach is the eyes' reach; the walk-or-fly rule.

**Not done, and worth knowing before the next flight:** the printer still needs the standing
body to have a line to each cell's face, and `groundStand` checks the eye line to the cell
centre, not to a face — a landing beside a cell whose only open face is away from it will stall
the station the usual way. And nothing here has been flown in game.

