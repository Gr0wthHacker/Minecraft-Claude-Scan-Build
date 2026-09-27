## Baritone reads a litematic's air as MUST-BE-AIR, and the loop's three audits (2026-09-05)

Jack, trying Baritone's builder on a design: *"baritone says the schematic has 101 air blocks
treated as physical"*. The exact wording is not in any installed jar or in `latest.log` (client
messages are not logged), so the number is unexplained; the MECHANISM is not, and it is worse than
the message.

**A LITEMATIC CANNOT EXPRESS "DON'T CARE", AND BARITONE READS EVERY AIR CELL INSIDE A REGION AS A
PLACEMENT TO SATISFY.** Read off `BuilderProcess.valid()` and `assemble()` rather than remembered:
only a cell outside every sub-region is `null` (skipped); a desired `air` with a world block under
it goes into `breakable`. Our designs are REMAINING WORK padded to `origin_lock` - one region of
mostly air lying over the finished island - so fed as they stand Baritone digs the world back to
the design's air. Measured with `mcbuild baritone <design> --world <capture>`: the four Friend
Stairs sit over **1,064 / 2,159 / 2,118 / 4,111** blocks of the platform they hang off.

```
python -m mcbuild baritone "Friend Stair NW" --world friendisland --copy
```
prints the three settings that make the design additive, off Baritone's own `Settings.java`:
`#buildSkipBlocks air` ("a list of blocks to be treated as correct"), `#buildIgnoreExisting true`
("will only place new blocks"), `#allowBreak false` (the guarantee under the other two) - plus
`#buildInLayers true`, `#layerOrder false` and `#startAtLayer <lowest unbuilt course>`, the exact
`#build <file> x y z` line from the sidecar's origin (every region we write sits at Position
0,0,0, so the min corner IS the origin), and the dig count. Two things it had to know:
**`startAtLayer` is schematic-relative** (Jack's `settings.txt` had 199, which on `Park Complete`
- origin Y94 - is world Y293), and **`#build` reads ONE token as the file**, so `Park
Complete.litematic` is looked up as `Park`; `--copy` writes a space-free twin. Baritone itself
lives in the LiquidLauncher profile's `mods/` (`Baritone.jar`, 26.2-1.11.1), not in `custom_mods`.
`tests/test_baritone.py` (3) pins the dig count, the settings and the copy.

### The audit: three readers over 20k lines, 23 fixes, and what a printer would look like

Jack: *"so many issues with its item seeking, movement, etc, it needs to be a printer - we need
to be organized, and not get stuck."* Three parallel read-only audits (decision layer, movement,
materials) against the in-flight tree, each finding verified in the code before it was touched.
**The single worst finding was in that day's uncommitted work**: `AutomationControl.enter`
refused any WITHDRAW unless `BuildJob.phase == FETCH`, and ChestScan (at a DEAD_END) and Unbox
(mid-BUILD) both open chests outside FETCH - so `Withdraw.tick` never ran its own timer, `busy()`
was true for ever, `Hud.advance` returned early ABOVE every clock, and the body hovered at the
chest in silence until `/cscan stop` (Unbox worse: the shulker left on the ground). **The job
phase gates the PRINTER and nothing else now.**

Fixed, each with the reason in the code:

- **The anchor did not survive a trip.** Back at the store hall with the work unloaded, the
  look-for-unseen ran first and `goLook` re-anchored on the unseen cell nearest the PLAYER; or
  the radius grew to reach whatever was loaded round the chest and a spot formed there. The
  shopping list sized at the work then came back somewhere else - "fetches, comes back, fails
  to place". The look and the radius growth both wait while the anchor is unloaded.
- **"Back to the work" had no give-up**: an anchor whose chunk never loads was guided to every
  two seconds for ever, and the 90s stall struck nothing because there was no spot. `RETURN_MS`
  (45s) or an Ignored anchor drops it and re-anchors; a stall with no spot strikes the target.
- **`Printer.relax()` manufactured a false frontier every 30s**: clearing the placeability cache
  outright made every cell past the 400-per-recount budget read as placeable again, so cells the
  printer had proved impossible came back as the frontier, a station was chosen on them, nothing
  placed, the spot struck. The old verdicts are kept as the fallback until re-asked.
- **`LAYER_LOOKAHEAD = 8` turned real work into a DEAD_END**: eight courses of printer-refused
  cells (lanterns waiting on posts, vines) emptied the frontier with work one course higher, and a
  dead end on a design with unseen cells goes to LOOK elsewhere - the wandering. Every course.
- **A-B-A ping-pong ran all night**: `avoidSpot` held ONE spot so B's abandonment un-avoided A,
  and one block placed per leg reset the thrash count. It is a map with expiry, and fewer than
  `THRASH_TRICKLE` (5) blocks between abandonments is nothing placed.
- **One 25ms clock for every route tier** let the first search that fails BY BUDGET spend it all:
  beside a row of shops the safe tiers fail that way as a matter of course, the tight search that
  finds the indoor route got ~30 nodes, and "no route and no way round" was the clock. Each tier
  has its own slice (`CRUISE_SHARE`..`TIGHT_SHARE`, ordered and pinned).
- **A ROUTE WAS THE ONE THING THAT BYPASSED THE GROUND CLEARANCE.** Roomy keeps one block of air
  off a floor; this server has ended flight at a block's distance, which is why `GROUND_CLEAR` is
  2.5 - and the routed step skips that clamp on purpose (indoors it grinds the ceiling). A CRUISE
  tier is searched first: roomy AND `CRUISE_BELOW` (3) clear under the body, relaxed within `ENDS`
  of either end, so a flight over the plate stays at the hover's own height.
- **A waypoint popped early chorded the corner it was there to round**: at cruise the radius is
  ~1.9, `legFrom` jumped ahead of the body, and the pursuit aimed along a leg the body had not
  reached - a line `clear` never validated, at every shop corner. `popped()` pops early only once
  the body is PAST the plane through the waypoint perpendicular to the next leg.
- **The recovery ladder belonged to no destination**: `trouble` was never reset when the target
  changed, so a new station inherited the last wedge; and CLIMB_OUT ended at `trouble =
  BACK_OFF_AT`, so it re-entered at back-off, climbed again, and never reached GO_HOME - 25 blocks
  up each time. Reset per destination; a second climb gives the spot up instead.
- Stale state on `follow`: `deadEndSince`, `unboxRetryAt`, the orbit leg.

**Still open, from the same audits and NOT guessed at** - each is a decision or a subsystem:

- **The chest approach hovers at 1.1 blocks of air** (`HOVER_CLEAR + FOOT_OFFSET`) against the
  2.5 the plugin has been measured to need, because Jack asked for "within 2 blocks". Either the
  fetch becomes a deliberate LANDING beside the chest, or the number is his to confirm in game.
- **Landing is one-way unless the server keeps `mayfly`**: `regain` gives up after four taps and
  never types `/fly`. `/fly` is a TOGGLE, so it is only safe when `!mayfly` - untested here.
- **A chest outside render distance is blacklisted before the flight starts** (`fetchTo` asks
  `approach()` of an unloaded chunk and reads null as "nowhere to open it from") - so the loop
  only ever fetches from chests already loaded near the work.
- **The frontier and the printer disagree about three block kinds**: replaceable plants (in todo,
  refused by `placement()`), water pools two cells wide (`contained()` deadlocks), door hinges.
  Each is a silent station stall, not a refusal.
- **Litematic state strings carry every property and `StateContract` treats world-derived ones
  as REQUIRED** (`age`, `berries`, `thickness`, `chest type`, `snowy`...) - the Python side's
  `work.INTENTIONAL` filter, not applied on the Java read.
- **The shopping list is sized to the lowest course within a radius that can grow to 200**, so
  in a three-level park it fills with the undercroft's blackstone while the surface is paved; and
  `loadCapacity` counts every slot as 64 (a pool of water asks for one bucket per cell).
- **Double chests are indexed twice** (151 pairs live); the stale twin sends the loop back.
- **`Work.split` runs over all 540,862 cells every TICK while printing**, and the journal fsyncs
  twice per placement. That stutter is part of what reads as freezing at chests.
- **A printer-mode rewrite of the spot logic** - one ordered queue per course, next bin in sweep
  order rather than fullest, refusals per bin, the shopping list = the next N bins - is the shape
  all three audits converged on. It replaces `Plan.clusters`/`Loop.sameSpot`/`stand` and is a
  session of its own.

**Nothing here has been flown in game.** 654 Java tests green (652 at the start of the session); `chunkscan-0.8.1.jar` not rebuilt.

Two working-practice notes: **the Bash tool fails with `unexpected EOF` on scripts past ~100
lines** - write the script with the Write tool and run the file; and **a whitespace-tolerant
patch anchor must start at its first TOKEN**, or `\s+` swallows the newline before it and the code
lands on the end of the comment above - twice in one session, both compile errors.

### Two more, on Jack's next two notes (same day)

**"It shouldn't be pulling things out of chests if it has a 90% inventory of a single item."**
The fetch decision asked only about the LOWEST COURSE near the anchor, so a pack of stone brick
beside a course of slabs read as "nothing I can place" and became a trip for one stack of slabs;
and the top-up at every session start asked no question about the pack at all. `Loop.WORK_LOAD`
(four stacks) is a working load: carrying that much of a material the design still wants, the loop
builds it first - no top-up if the frontier course has cells for it, a higher course near the
anchor becomes the frontier if that is where they are, and if they are elsewhere in the loaded
design it re-anchors there rather than opening a chest. Only when nothing carried can be placed
anywhere loaded is a chest worth the trip. `LoopTest` pins the predicate.

**"If I type moss_block it only does that material until it's filled every potential place of
it on the schematic."** `/cscan only moss_block` (one or more item names; `off` lifts it). Every
cell of another material is not the session's work: filtered out of the frontier, the shopping
list and the PRINTER's own in-reach pick, so a pack of slabs places nothing while the filter is
set. The session ends - stopped, and said, never "complete" - when no loaded cell of the material
is left and every chunk has been seen. The filter rides in `session.json` and is restored FIRST on
resume, because a resumed `follow` that forgot it would place everything. `Loop.itemName`
normalises `minecraft:`, case and a `[state]`; it is the ITEM name, so `stone_brick_slab` is both
halves and every facing.

**And the chest approach hovered at one block of air** (`HOVER_CLEAR` 1, `EXACT_CLEAR` 1.05) -
the one place the body was flown to exactly the height this server ends flight at, on the
reasoning that 2.5 would put a floor chest out of reach. It would not: from two clear cells up the
eyes are ~3.4 from a chest one block over, inside `Withdraw.REACH`. Two now, and a routed step
keeps the ground clearance whenever the next waypoint itself has it - the bypass stays only for
routes that genuinely go low. `AuditFixesTest` re-derives the reach arithmetic.

**`chunkscan-0.8.2.jar` is built** (`build/libs/`), 656 Java tests green, not uploaded - Jack
uploads through the launcher himself. Nothing in it has been flown yet.

### 0.8.3: it stays where the work is, and it flies over the top (same night)

Jack flew 0.8.2 - every fix above was in it - and reported the same two things in sharper words:
*"its path finding and flying is still really bad, constant collisions, running right into
objects"*, and *"if its actively placing idk why it keeps instantly seeking and then flies off ...
sometimes it has a massive patch, will place 5, then go fly away from it ... it should look in
its immediate vicinity and just keep placing as much as possible always."*

**THE STATION WAS RE-CHOSEN EVERY RECOUNT AS THE FULLEST BIN.** Place five blocks and another bin
is the fullest; the flight left with work still in reach, and every flight is a chance to touch
something. `Loop.holdHere` runs BEFORE any question about anchors, courses, spots or stations:
while anything placeable that I carry is within `Loop.VICINITY` of the body, guidance is dropped
and the printer places on its own tick. The hold ends only when nothing in reach is left, or when
it has held for `STATION_MS` with nothing placed - then the station machinery gets its turn and the
hold is disarmed for `HOLD_COOL_MS`, or it wins the next recount straight back.

**AND THE ROUTER IS NO LONGER HOW A LONG LEG IS FLOWN.** Every collision in a day of router fixes
was a flight THROUGH built space - between shops, under awnings, past corners - and each fix made
the threading a little better without making it safe. A player with /fly goes UP, crosses in open
sky, and comes DOWN. `Autopilot.overTop` builds exactly that for any leg over `OVERTOP_MIN` (4)
blocks: the corridor's highest MOTION_BLOCKING surface (heightmap, margin 2 each side) plus
`OVERTOP_CLEAR` (3) is the crossing height, never below where the body already is; three
waypoints, each leg verified with `Nav.clear`; NEVER simplified (the chord from the ascent's foot
to the descent's head is the diagonal through the buildings it exists to fly over). A roofed
descent stops on the roof and the router does the last few blocks, which is the one place it has
ever been good; a ceiling over the ascent hands the whole leg to the router. The heightmap answers
the world's own minimum for an unloaded chunk, so an unseen tall building raises the crossing as
its chunk arrives, and the blind-speed rule still covers the approach.

`AutopilotTest` pins the legs and the height arithmetic; `LoopTest` the hold. 658 Java tests
green, `chunkscan-0.8.3.jar` built, not flown.

### 0.8.4: the scan that ran twenty times a second (2026-09-06)

Jack: *"it also scans too frequently, i think it uses a full radius based on current position vs
set positions."* It did. The printer's tick asked `Work.split` for the cells within reach of the
body, and `split` answered by walking ALL 540,862 cells of the park - a distance test each - and
re-parsing the design's sidecar JSON for the dig list, on every call, twenty times a second. That
is the stutter that reads as freezing at chests and as jerky flight.

- **The work list is BINNED BY CHUNK when it is loaded**, cached with the list and the dig list.
  A radius question touches only the chunks the radius covers (`Work.binNear`, a box test per
  bin), and an unloaded chunk costs one `hasChunk` with its cells counted unseen, rather than a
  world lookup per cell. The HUD's full recount every two seconds skips the unloaded 80% of the
  park the same way.
- **A placement sweep that found no angle is not re-run every tick** for ten ticks
  (`Printer.recentlyUnplaceable`): yaw by pitch by face for every in-reach cell that fails was the
  other half of the tick.
- **No fsync per placement.** Two disk syncs per block (attempt, verdict) were up to forty
  milliseconds on the client thread each time; `reconcile()` already survives a torn last line.
- **And the vicinity hold targets the body's own cell**, not "no target": with no target the
  autopilot said "autofly is ON but has nowhere to go" at every hold, and would have lifted a
  landed body off good paving.

659 Java tests green, `chunkscan-0.8.4.jar` built, not flown.

### 0.8.5: the open list, closed (2026-09-06)

Jack: *"fix all."* The items the audits had left as decisions, each now taken:

- **A chest out of view is flown to, not blacklisted.** `fetchTo` asked `approach()` of an
  unloaded chunk, read null as "nowhere to open it from" and cooled the chest for a minute - so
  the loop could only ever fetch from chests already loaded near the work. It flies toward the
  chest now and picks the approach cell once the chunk is here.
- **Only DECIDED properties have to match.** `StateContract.role` is the Python side's
  `work.INTENTIONAL` on the Java read, plus four this side keeps as completion requirements
  (`waterlogged`, `powered`, `persistent`, `open`) and a rail's `shape`. Before, `sugar_cane
  [age=7]`, `cave_vines[berries]`, `chest[type=left]`, `grass_block[snowy]` had to match exactly:
  the cell silently left the frontier, or placed correctly and was reported WRONG STATE.
- **A double chest is one record**, filed under its lower half (`Storage.canonical`, from
  `ChestBlock.FACING`/`TYPE`); the stale twin of an old record is dropped by `stillThere`.
- **Flight revoked by the server is asked back**: `regain` sends `/fly` (bounded to three per
  destination) while `mayfly` is FALSE - the one state in which a toggle can only go on - then
  double-taps as before; and the tries reset per destination rather than per session.
- **A replaceable block is placed into**: grass, ferns and snow layers were in todo and refused by
  `placement()`, a silent station stall with no refusal ever reported.
- **A pool wider than one cell can be placed**: `contained()` accepts a neighbour that is the
  design's own water (`Printer.setDesignWater`, from the followed design), and flowing water in
  the cell is not "a block in the way". The rim still has to be solid.
- **A bucket is not a stack**: a shopping list asks for at most `Plan.BUCKETS_PER_TRIP` (4).

662 Java tests green, `chunkscan-0.8.5.jar` built, not flown. The one thing here that touches
a server command is `/fly`, and it is only ever sent while the server itself says flight is off.

### `analyze`: what a build can TAKE today, not what it is made of (2026-09-06)

Jack: *"analyze schematics automatically, identify most used materials, and most placeable based on
no air blocks around it based on currently placed, so we can efficiently spread resources in large
builds."* A bill of materials answers the wrong question for a trip: a pack of the commonest block
is a pack with nothing to place against, if the commonest block is the roof.

```
python -m mcbuild analyze "Park Complete" --world newisle --have     # offline, against a capture
/cscan analyze <design>                                              # in game, against the live world
```

Per material: **placeable** (remaining cells with a clickable face-neighbour standing), **unlocks**
(cells that cannot go in yet which a placeable cell of this material would give a face to), left,
stacks, have/short against the container index, and the 16-region holding the most placeable
cells. Ranked placeable first. On a fresh Friend Stair the answer is eight slab cells - the notches
- and nothing else, which is exactly right: everything else hangs off them.

**And the loop's shopping list is led by it.** `Plan.loadPlan` used to lead with the frontier
course only; it leads with EVERY placeable cell near the anchor on any course now (`Plan.usable`
is the same ranking as a list), so the trip that comes back places the most and opens the most.

**Clickable is the printer's rule, not the audit's.** The first offline pass counted only full
cubes as something to place against and called every cell of the stair unplaceable: the friend
platform is top slabs. `analyze.clickable` mirrors `Printer.support` by name - a slab, a stair, a
wall, a chest is a face; a vine, a tuft, a torch, a carpet, a rail, water is not. `tests/test_
analyze.py` (2) and `PlanTest` pin the ranking: 20 placeable planks outrank 300 wool of roof.

663 Java tests green, `chunkscan-0.8.5.jar` includes the command.

