## The frame rate, measured at last (2026-09-07)

Jack: *"the game still is incredibly spazzy/laggy, it twitches and stops and gets stuck and then
jerks out ... will have long gaps where its searching i guess and cant find anything and then
suddenly will find things just below it"*. Then, on the same jar: *"its also still building
completely around itself and getting fully stuck"*.

`/cscan perf`, in game, on the design that is actually being printed:

    recount        mean 262.39 ms   worst 426.74 ms      <- Work.split alone
    loop decide    mean  47.04 ms   worst 260.04 ms
    loop filter    mean  35.39 ms   worst  62.51 ms
    printer scan   mean   1.02 ms   worst   2.74 ms
    autofly        mean   0.02 ms   worst  98.19 ms
    highlight      mean   0.01 ms   worst   1.68 ms

**TWO ROUNDS OF PERFORMANCE WORK WENT TO THE SECOND-BIGGEST COST, AND THE INSTRUMENT THAT WOULD
HAVE SAID SO HAD ALREADY BEEN BUILT.** `Islands.Gate` and the memoised `inLockedProfile` were a real
fault and a real fix - they are `loop filter`, 35 ms - and the thing that freezes the client is the
262 ms next to them. The profiler was written in the round before, specifically so this would not be
argued from reading, and then not run for two more rounds of reading. **A measurement that exists
and is not taken is worth exactly as much as one that does not exist.**

### The instrument was itself wrong, in the direction that hides the truth

The report said `345.86 ms/tick total (692% of a 50ms tick)`, which cannot be true of one thread.
The ring holds the last {@code WINDOW} **CALLS**, not ticks: for `autofly`, called every tick, the
mean is per tick and the label was right; for `recount`, called every fortieth, it is per call, and
summing those into a share of one tick is nonsense. Worse, it flattens the one number that matters
here - a quarter-second freeze twice a second and a millisecond every tick are the same LOAD and
completely different to play with.

It reports **ms per call, the worst call, and a true share of the client thread** now, over a
counted number of ticks. `Perf.tick()` is called once per client tick from the highlight hook.

### Count globally, list locally

`Work.split` at radius 0 built AND SORTED a list of every remaining cell of `Park Complete` - about
two hundred thousand - so that `Hud.advance` could narrow it to the sixteen blocks around the body
and throw the rest away. Twice a second.

- The **counts** still cover the whole design: completion and progress are global questions and
  getting them wrong ends a session early. `Split.todoTotal` carries the real number and everything
  that counts uses it.
- The **list** stops at the loop's own working radius.
- The one global question the loop asks of the list - *where is the nearest work when there is none
  here* - is `Split.nearestTodo`, computed in the same counting pass for nothing.
- **And the sort no longer boxes.** It was `Arrays.sort(Integer[], comparator)`: two hundred
  thousand `Integer` allocations and about three and a half million virtual calls, per call. The
  order is (recipe, course, distance) and all three fit in one primitive key, so it is
  `Arrays.sort(long[])` with no allocation at all. Distance is quantised to a quarter block, which
  can only reorder cells of the same material on the same course within a quarter block.

`split diff` and `split sort` are timed separately, so the next reading says which half is left
rather than costing another round trip.

### The searching gaps were the placeability sweep, spent on the wrong cells

`Printer.everPlaceable` costs up to **seventy-two `getStateForPlacement` calls per cell** - six
faces by four yaws by three pitches - and the frontier asked it about EVERY cell of a course. A
course inside the 200-block working radius is tens of thousands of them, so the 400-per-recount
budget was spent **in course order** on cells a hundred blocks away, and cells past the budget
default to *assume placeable*: the loop went to work that was not there, placed nothing, stalled and
abandoned. The work at the body's own feet was reached by luck, on whichever recount happened to
cover it. Several recounts of that is the gap; the one that reaches the near cells is the sudden
find.

**AND THE FAILING CASE IS THE EXPENSIVE ONE**, which makes it a vicious circle: a cell with
supporting faces and no matching state pays all seventy-two, and that is exactly what a stuck loop
is looking at.

- Nearest first, and stop at `Loop.FRONTIER_ENOUGH` (96) - enough to choose a station, and the
  printer re-scans what is actually in reach on its own tick anyway.
- **Pitch only where it can change the answer.** Looking up or down decides a facing of up or down
  and which of floor/wall/ceiling a button takes. It decides nothing about a stair, a slab or a
  wall: a stair's `half` and a slab's `type` come from WHERE IN THE FACE the click lands, which the
  hit vector already sets. Swept anyway it tripled the cost on the blocks this park is made of.

### Building a box around itself

Every gate in the printer was about the BLOCK - is it legal, supported, affordable, on the plot,
inside the fence - and **none of them was about the person holding the item.** A station chosen
inside its own work builds the last wall of a box around itself, and then nothing can reach
anything.

- `Printer.wouldBoxIn` refuses a placement that would leave the body walled on all four sides with
  no way up. **The cell stays in `todo`**: it is a refusal FROM HERE, not for ever - the station
  moves on its own clock and the block goes in from outside, which is how a person would have built
  it. That is why it lives in `placement` and not in `everPlaceable`, where a false NO would be
  cached against the cell and write the work off for good.
- **And `Burial` can see it now.** It was gated out of building entirely last session, because at
  two walled sides it fired at every station the loop picks - standing beside the wall you are
  putting up - and bounced. That gate then made the one case it exists for invisible: **a printer
  walls its own STATION in, and a station is a destination.** The honest fix is a different
  THRESHOLD, not a blind spot: two sides while digging or idle, all four while building. Four is not
  a doorway, a corridor or a wall going up. It is a box.

### THE BOX GUARD COUNTED WALLS, AND WHAT MATTERS IS EXITS (2026-09-07, chunkscan 0.9.0)

Jack, on the jar that shipped the guard above: *"consistently it will box itself in."* The guard was
real, the reasoning behind it was right, and it was measuring a quantity that is **not** the one the
question is about.

**`Burial.walled` COUNTED SIDES WHERE BOTH BODY CELLS WERE SOLID.** Its own comment defended that:
*"a block at the feet alone is a step to walk up and a block at the head alone is an overhang to duck
under."* The first half is true. The second is not — **a player is 1.8 tall and no crouch in this game
fits under a one-block gap** — and the case it lets through is not exotic, it is the commonest thing a
printer builds:

    the body hovers a course over the floor
    the next course of the design is at HEAD height
    four blocks go in, one per side

Four sides shut, the body cannot move an inch, and `walled` returns **ZERO**. Every consumer of it was
therefore blind in exactly the situation it exists for: `Burial.wants` saw a completely free player and
never fired, and `Printer.wouldBoxIn` — which is `walled >= 4 && !canRise` — never refused a single one
of those four blocks. The guard was correct code over the wrong measurement, which is why reading it
twice did not find it.

**A side is a way out or it is not**, and there are exactly two ways out: walk straight through (both
cells clear), or step up onto one block — which needs somewhere to put your head over there AND
headroom in your own column to make the jump. `Burial.canLeave` is that, `exits` counts them, and
`walled` is `4 - exits`, so a wall, an overhang and a two-course face all count the same.

Three things followed, and each was a separate hole:

- **THE RESCUE WAS GATED OUT OF THE ONE CASE THAT IS ACTUALLY FATAL.** `boxedIn` required `canRise`,
  written for the right reason — a mine gallery is walled by design and roofed, and rising there is
  grinding a ceiling — but it means a body that has built itself a **lid** measures as fine and
  nothing fires at all. Sealed is the emergency, not the exemption. `Burial.sealed` is its own answer
  (`Move.LEAVE`), and the roofed-gallery case needs no exemption any more because a gallery has
  EXITS: with `canLeave` doing the measuring, `walled` never reaches four in one.
- **THE PRINTER ONLY REFUSED THE LID.** `walled >= 4 && !canRise` allows the block that leaves the
  body standing in a one-wide open-top shaft — and the next course of the same design then builds
  that shaft taller with the body still in it. The rule is not *do not seal yourself in*, it is
  **keep a way out**: refuse any placement after which `exits == 0`. A shaft you can only fly up is
  not a place a printer can work from.
- **AND A LIFT THAT KEEPS BEING NEEDED IS NOT A FIX.** Rising re-opens the sides, the autopilot flies
  the body back down to the same station, the same walls close round it: a one-second cycle placing
  nothing that **no clock in this mod can see, because the body is moving the whole time.**
  `LIFT_LIMIT` (3, over a minute) turns the fourth lift into `Move.LEAVE`.

`Move.LEAVE` goes straight to the recovery ladder's **last rung** — `stage = GO_HOME`, which is
`/is`, or giving the spot up when a fence is set. That is the shortcut `Recovery.stageFor` already
makes for a sealed pocket, taken directly rather than through `trouble`, because **a body that has
built itself in usually has no destination at all**, and with no destination the ladder never runs.
Which is, again, precisely why nothing noticed.

Two tests changed with the decision, which is this file's own rule about tests pinning decisions:
`aBlockAtTheHEADALONEisAnOverhangAndNotAWall` was the bug written as a contract, and
`aROOFEDplaceIsNotAPitHoweverWalledItIs` asserted the exemption that hid the sealed body. In their
place `aRingAtHEADHEIGHTisABOXandTheOldCountCalledItOpenGround` is the failure Jack kept hitting, and
`aROOFEDplaceWITHAWAYOUTisNotAPit` keeps the loop out of the undercroft for the honest reason.

697 Java tests, 0 failures. **Not flown in game** — the geometry is unit-tested with no client in it,
and whether the printer now leaves itself a door is a thing only a session can say.

### A STUCK LOOP RESETS ITSELF INSTEAD OF STOPPING (2026-09-07, chunkscan 0.9.1)

Jack: *"need to fix bot stalling, if it gets stuck permanently it needs to do /visit enroz and reset
itself, if it loses location or cant find, do the same and restart with new materials after a cscan
analyze ... make it highly crash resistant so its always doing things."*

**EVERY TERMINAL PATH IN THIS LOOP ENDED THE SAME WAY: `following = false` AND A SENTENCE.** A dead
end held for two minutes, four spots abandoned with nothing placed, every spot struck twice, twenty
exceptions in a row - all of them honest, all of them correct, and all of them a bot that switches
itself off at 2am and waits for somebody to type. `mcbuild/../Rally.java` is the alternative:
teleport to where the work is, throw away every judgement this session has made, LOOK again, and
come back with materials chosen for what the build can take today.

    /cscan rally                 reset now, by hand
    /cscan home [command]        what a reset types to get back; `visit enroz` by default
    /cscan why                   ...says how many resets, how many fruitless, when the next is due

#### `/is` WAS THE WRONG TELEPORT, AND IT WAS THE RESCUE

The recovery ladder's top rung has typed `/is` since it was written. On a fleet of alts building
**somebody else's plot** that lands you on YOUR island - a bare starter pad **121,000 blocks** from
the park, where every route is past `Nav.MAX_RANGE` and no chunk of the design will ever load - and
it hands the flight straight back holding a shopping list made beside a chest that is no longer
there and an anchor whose chunks cannot load. **The rescue was itself the way the loop most reliably
lost its location.** The home command goes where the WORK is, and it is a SETTING rather than a
literal because it is a fact about a server rather than about this mod.

**The fall rescue KEEPS its `/is`, and that asymmetry is deliberate**: a fall is the whole inventory,
`/is` cannot fail, and a `/visit` can (a closed island, a name that has changed). Landing on the
wrong island is survivable and the lost-location check brings you back; falling past the bottom of
the world is not. `RallyTest` pins both halves by reading the source, because it is asserting the
ABSENCE of something and there is no state to look at.

#### What a reset actually is

The teleport is the cheap half. What makes it a reset is that **every OPINION goes and every
MEASUREMENT stays**: struck spots, cooled-off chests, refused cells, chunks written off as
unloadable, parked designs, the shopping list, the anchor, the station tries, the recovery ladder's
own trouble counter. All of those are correct about the world they were formed in and worthless
about a world we have just been teleported into - left standing, a reset lands somewhere new and
immediately refuses the same spots and skips the same chests. What is KEPT is how much has been
placed, how long we have been at it, and which designs are genuinely FINISHED (`doneThisSession`) -
because a finished design is a measurement, not an opinion.

Then it runs the analysis and sets `topUp`, so the next phase is a FETCH sized to what the build can
actually take. `Analyze.java` is `/cscan analyze` lifted out of the command so the loop and the
command read the same answer - a report that exists twice is a report two callers can disagree
about, the same rule `proportions.measure` and `rubric.score` already share an entry point under.

#### Three rules, and two of them are about not making it worse

- **A reset that fixes nothing must not repeat at speed.** Resetting every thirty seconds for ever
  is the same infinite loop with a teleport in it, and a louder one. The interval DOUBLES while
  nothing is placed between attempts, capped at five minutes; **one block placed since the last one
  puts it back to the beginning**, because that is the evidence it worked.
- **A teleport cannot be fenced.** With `autofly bounds` set the reset does the FORGETTING half and
  skips the flight, and says so - degrading silently would strand the loop outside its own fence.
- **Landing is not instant.** 120 ticks before anything is decided: on the tick a teleport lands
  most of the world is unloaded, `Nav` treats unloaded as passable, and the first question asked
  afterwards is *is the work unreachable* - which would answer yes about every chunk still on its
  way. `Rally.pending()` holds the whole loop until then.

#### "Loses location" is a MEASUREMENT, not a feeling

The distance from the body to the nearest cell the design still wants, held over 30 seconds.
**Twice `Nav.MAX_RANGE`**, so a leg the router could plan never reads as lost - what it catches is
the wrong island. A single far reading is not evidence: one recount taken mid-teleport, or while a
chunk loads, measures far and means nothing.

**And a teleport that did not teleport is a silent no-op**, which is the shape of failure the reset
exists to end: a wrong command name, a closed island, a permission that has lapsed. The body's
position is recorded when the command is sent and compared on landing, so `/visit enroz` failing
says so instead of resetting, not moving, backing off and repeating all night.

#### The trip limit: the flight nothing could see

Found on the way. `Loop.byTrip` sorts far containers to the BACK rather than dropping them - *if the
only stock in the world is far away, going is still better than stopping* - and that reasoning had
no floor under it. Past twice `Nav.MAX_RANGE` no route can be searched for at all, so the flight
falls through to going **direct** and simply keeps going, at a container index entry left over from
another world. **The body is moving the whole time, so no clock and no rung of the ladder can see
it** - `Recovery.inTrouble` is about movement, and this is a flight that never stops moving.
`Loop.TRIP_LIMIT` drops them and counts them.

#### And a stuck container screen closes itself

A container screen nobody here opened parks the loop, correctly - clicking slots underneath somebody
is worse than waiting. A screen that never closes is a loop that is alive, announcing itself once a
minute, and doing nothing at all until morning. Three minutes and it closes it, which is what a
person would do and is one packet.

#### Where the resets fire, in the order they are tried

| | |
|---|---|
| two 90-second stalls in a row with nothing placed | one stall is an awkward spot and the next spot fixes it |
| a dead end held for two minutes | ...after `follow all` has tried every other design |
| four spots given up on with nothing placed | ...after the next design, for the same reason |
| every spot struck twice | ...after the next design: moving on is cheaper than crossing the world |
| twenty exceptions in a row inside the loop | a state problem, and a reset is what replaces state |
| the work measures over 1,024 blocks away for 30s | the wrong island |
| the flight ladder's top rung | replaces the bare `/is` |

**A broken work list deliberately does NOT rally** - a teleport does not fix a file - but it parks
the design and takes the next one instead of ending the session, and stops only when it is the last
one there is.

**Still open:** none of this has been flown. The one thing to check before leaving it overnight is
that **`/visit enroz` is the right command on this server** - run `/cscan rally` once by hand and
watch what happens; if the body does not move it will say so, and `/cscan home <command>` fixes it.
715 Java tests, 0 failures.

#### ...and the reason it was stalling was ONE BIT (2026-09-07, chunkscan 0.9.2)

Jack, on the jar above: *"now getting an index 8772104 out of bounds"*. Off `latest.log`:

    [cscan] Index 8772104 out of bounds for length 425726

**`Work.split` HAS BEEN THROWING ON EVERY RECOUNT OF A LARGE DESIGN**, which is every command that
reads a work list and every tick of the loop. The recount's sort packs (recipe, course, distance,
index) into one long - the 0.8.6 change that took it off a boxed comparator - and the index gets
**23 bits**:

    key[i] = (recipe << 55) | (y << 43) | (dist << 23) | i;    // pack: 23 bits of index
    flat[(int) (k & 0xFFFFFF)]                                  // unpack: TWENTY-FOUR

Bit 23 is the low bit of DISTANCE, so any cell at an odd quarter-block distance from `near` - about
half of them, in every design - came back as `i + 8388608`. The arithmetic in the report is exact:
8,772,104 - 8,388,608 = 383,496, inside a list of 425,726.

**AND THE SUITE WAS GRADING ITS OWN COPY.** `SplitOrderTest.fast` re-implemented the packing
line-for-line rather than calling it - and the copy masked `0x7FFFFF`, correctly. So the test
asserted that the order MEANS what it says, proved it against an implementation that only exists
in the test, and stayed green while production threw on every call. That is this repo's own
one-source rule, broken inside the file whose whole job is to check the thing it duplicated:
`proportions.measure` and `rubric.score` share an entry point for exactly this reason.

`Work.sortKey` and `Work.sortIndex` are that entry point now, the mask is derived from
`SORT_INDEX_MAX` so the two cannot differ, and the test walks every quarter-block distance from 0
to 16 against four indices rather than trusting one. **Verified by putting the bug back**: with
`0xFFFFFF` restored the suite fails; with it fixed, 717 pass.

Two things worth keeping beyond the fix:

- **A CONSTANT AND A MASK ARE ONE FACT WRITTEN TWICE.** `SORT_INDEX_MAX` was `1 << 23` and the
  unpack was a hand-typed hex literal five lines away. Nothing connected them, and nothing ever
  will unless one is derived from the other.
- **A TEST THAT RE-IMPLEMENTS ITS SUBJECT MEASURES NOTHING.** It is the most convincing kind of
  green there is: the assertions are real, the reasoning is real, and the artefact under test is
  a copy. If a test file contains the same arithmetic as the code, that arithmetic belongs in the
  code and the test should call it.

**And the home command is confirmed**: `============ Welcome to Enroz's Island ============` in
the log, seconds before the error. `/visit enroz` works.

### THE SHOPPING LIST CHOSE SIX THINGS NOBODY HAD (2026-09-08, chunkscan 0.9.3)

Jack: *"the autonomous collection, pathing etc now constantly breaks because i guess the objects
are further than rendered, also is not detecting things it can 100% place e.g. moss blocks when
right next to tons of placeable ones."*

**BOTH HALVES WERE DIAGNOSED OFF `latest.log` RATHER THAN BY READING THE CODE, AND THAT IS THE
LESSON.** Three sessions of this file have been spent reasoning about which of the loop's
judgements could be wrong; the client writes every one of them to disk with a timestamp, and
twenty minutes of it named two causes exactly. `%APPDATA%/CCBlueX/LiquidLauncher/data/gameDir/
nextgen/logs/latest.log`, `grep cscan`. **Read the log first.**

    23:49:50  park complete: 422846 left in loaded chunks, 23106 placeable, 0 out of view
    23:49:50    placeable / left / carrying / indexed
    23:49:50    5096 / 53692 / 0 / 15040  smooth_basalt
    23:49:50    1403 / 62998 / 0 /  4057  moss_block
    23:49:50     935 / 15098 / 0 / 40545  stone_bricks
    23:49:50     908 /  2938 / 0 /     0  chiseled_stone_bricks
    23:49:50  shopping list for 90 cells around 97600 208 80600: 7x ochre_froglight,
              16x chiseled_stone_bricks, 23x oak_fence, 9x smooth_stone_slab,
              32x cracked_stone_bricks, 3x oak_planks
    23:49:50  nothing indexed to fetch - building with what you have
    23:49:50  no usable support/material combination
    23:51:51  RESET #3 - parked at a dead end for 2 minutes with nothing else to do

**THE ANALYSIS AND THE TRIP WERE ANSWERING DIFFERENT QUESTIONS, TWELVE LINES APART.** `Rally`
prints the right answer at every reset - 23,106 placeable cells, 40,545 stone brick and 4,057 moss
in chests - and then `Plan.loadPlan` picks the first six materials it meets in course-and-distance
order round the anchor, of which the index holds **none**. `shortfalls` comes back empty, the phase
is DEAD_END, two minutes later the loop resets, re-anchors in the same place, chooses the same six,
and does it again. **0 placed in five minutes**, three times over.

`MAX_MATERIALS` is right and stays - a trip for forty things finishes none of them - but six is a
CHOICE, and choosing six things nobody has is choosing not to go. The selection runs in two passes
now, obtainable first, in exactly the order it had before; `Storage.stocked` is the one question it
had to ask and never did. With nothing obtainable the list is bit-for-bit what it was, so *"nothing
indexed to fetch"* still gets to be TRUE rather than being manufactured by a bad list - which is
what `test_theShoppingListPrefersMaterialsThereIsSomewhereToGet` pins from both sides.

That is Jack's *"not detecting things it can 100% place, e.g. moss blocks"* in full: the moss was
detected, was placeable, and had four thousand blocks of stock indexed. Nothing ever asked for it.

#### A CHEST STANDING ON A FLOOR HAD NO APPROACH CELL AT ALL WHILE FLYING

The other half, from the same log:

    23:42:36  fetch: 64x cobbled_deepslate from #432 Found shops - flying there first
    23:42:42  cannot find anywhere to open #432 Found shops from - skipping it for a minute
    23:42:44  cannot find anywhere to open #427 Found shops from - skipping it for a minute
    23:42:46  fetch: 64x cobbled_deepslate from #428 Found shops (3264 there)
    23:42:52  took 64x cobbled_deepslate
    ...
    23:43:36  cannot find anywhere to open #428 Found shops from - skipping it for a minute

**THE SAME CHEST, OPENED AT 23:42 AND UNOPENABLE AT 23:43.** The chest did not change; whether the
body was FLYING did. `ContainerInteraction.hoverable` asks for two clear cells UNDER the approach
cell - the right rule, added because *"it can't be within 1 block beneath when flying to place
because it will auto stop flying"* - and **a chest stands on a floor**. The only cell that can
satisfy it is two courses above the floor beside the chest, so a chest under any ceiling lower than
three has no hovering approach, and the whole index became unopenable the moment autofly was on.
`approach` had no fallback and answered null, and the caller reads null as *"this chest's
problem"* and cools it off for a minute - so the loop toured its own index blacklisting it.

**Landing beside a chest is what a player does**, and it is safe in the one way that matters: there
is a floor under you by construction, so losing flight costs a double-tap rather than the void.
Hovering is still first choice; standing is the fallback. `ContainerInteraction.mustLand` tells the
caller which it got, because a flight guided at a cell it cannot hover in holds its ground
clearance two blocks above it and never arrives - which is the six-second `FETCH_STUCK_MS` wait,
firing on a cell that was correct.

#### Two more, both of them a clock that could not see a phase

- **THE FLIGHT TO A CHEST WHOSE CHUNK HAS NOT ARRIVED HAD NO CLOCK OVER IT AT ALL.** Both
  `Loop.goingNowhere` and the ninety-second `Loop.stalled` skip while fetching, and `FETCH_STUCK_MS`
  only runs once an approach cell has been chosen - which needs the chunk. So the one branch that
  handles a chest beyond render distance was `guide(at); return;` for ever. **Past `Nav.MAX_RANGE`
  no route can even be searched** (`TRIP_LIMIT` is twice that, deliberately, so one direct leg can
  bring the goal into range) - the flight goes direct and keeps going, and because the body is
  moving the whole time nothing upstream can see it either. `FETCH_REACH_MS` (45s) gives it up.
- **A LOAD WORTH BUILDING IS NOT FOUR STACKS.** `WORK_LOAD` is the right threshold for *do not go
  shopping, you already have plenty* and the wrong one for *am I stuck*: a trip that came back with
  ONE stack of cobbled deepslate, for a design with 545 placeable cells of it, found nothing on the
  frontier course holding four stacks and reported `pack is full of what you cannot place here`
  three seconds after `pack loaded`. It tries `WORK_LOAD` first and then any quantity at all -
  build-before-shop, at whatever the trip actually brought.

**718 Java tests, 0 failures. `chunkscan-0.9.3.jar` built, not flown.**

**Still open, and it needs the next session's log rather than a guess.** Nothing was placed in that
entire five minutes, and there is one window in it the fixes above do not explain: at 23:43:06 the
loop reported *"22 cell(s) placeable from right here - staying until they are in"*, carrying those
materials, and six seconds later *"3 cell(s) in reach but nothing placed for 5s"*. The printer was
armed (`follow` sets `printDesign`) and the vicinity hold sets the phase to BUILD, so
`AutomationControl` was not refusing it. That leaves `Printer.placement` refusing every cell -
`wouldBoxIn` while the body sits in the middle of a floor course it is laying is the first suspect,
and `Islands.outside` the second. **`/cscan why` while it is holding, and `/cscan perf`, would
settle it in one line each**; guessing at it here would be the fourth round of exactly the reading
this section is about.

#### ...and it says what the design can take, before it goes shopping (chunkscan 0.9.4)

Jack: *"we need, when it starts, for it to analyze entire schematic and provide a list of top 5
materials that are immediately placeable."*

`Analyze` already answered exactly this and only `Rally` ever called it - so **the report existed,
and a session that never reset never saw it.** The loop's own first act is a top-up trip, and the
only thing it said about that was the shopping list, which is scoped to the working area round the
anchor and says nothing about the design. Five rows at the start, because this is the answer to
*what should be in the pack* and a pack holds a handful (`Plan.MAX_MATERIALS`); fifteen stays as
the reset's diagnostic, read when the question is why nothing worked.

    [cscan] what park complete can take right now - fill the pack from the top of this list:
    [cscan] park complete: 422846 left in loaded chunks, 23106 placeable, 0 out of view
    [cscan]   placeable / left / carrying / indexed  - fill the pack top-down
    [cscan]   5096 / 53692 / 0 / 15040  smooth_basalt
    [cscan]   2391 /  5951 / 0 /  9746  light_gray_wool
    [cscan]   1403 / 62998 / 0 /  4057  moss_block
    ...

**DEFERRED TO THE FIRST RECOUNT RATHER THAN RUN INSIDE `follow`, AND THAT IS NOT TIDINESS.**
`follow` is also how a session RESUMES after a join, where most of the world has not arrived and
every cell would be counted out of view - a report that is wrong at exactly the moment it is most
useful. The grace period is already the wait for that, so it is the one both share; the flag is
armed in `follow` and read on the far side of it. It fires per design under `follow all`, which is
right - a new design deserves its own analysis - and `restartAfterRally` does not go through
`follow`, so a reset still prints its own fifteen rather than both.

And it never throws at its caller. `Analyze.report` already catches for the same reason - the loop
cannot afford an exception on the tick that starts it - and the call site catches again, because a
REPORT must not be able to end a session.

### A FIFTH OF EVERY PLACEMENT WAS BEING DROPPED, AND NOTHING SAID SO (2026-09-08, chunkscan 0.9.5)

Jack, asked what would make it a proper full-cycle build: *"fix all"*. What follows came out of
reading `.cscan-build-journal.jsonl`, which has recorded every attempt since the printer was
written and which nothing had ever summarised.

    1,215 placement attempts  ->  951 PLACED, 258 STILL_AIR, 6 MISMATCH
    P(fail | previous succeeded) = 16.5%      P(fail | previous failed) = 40.5%
    failure runs: 20, 20, 19, 17, 9, 8 ...

**ONE ATTEMPT IN FIVE IS SILENTLY DROPPED BY THE SERVER, IN RUNS OF UP TO TWENTY.** That is a
CONDITION lasting seconds, not per-cell geometry - and every clock in `Hud` read those seconds of
nothing as *this spot cannot be built* and moved on. **An actuator failure was being diagnosed as a
geometry failure, at every station**, which is most of the thrashing four sessions of watchdogs had
been added to chase.

Three causes, and the first two compound:

- **THE PACE WAS TWICE THE FASTEST RATE A PLAYER CAN ACHIEVE.** `INTERVAL_MIN` was 2 ticks because
  the docstring said *"vanilla holding right-click is one per tick; this is gentler"*. Read off the
  jar rather than remembered - `javap -c net.minecraft.client.Minecraft | grep -B4 putfield.*rightClickDelay`
  - it is **4**. Rule 11, in the one place a number is a rate rather than a block property.
- **AND THE PACE FORGOT WHAT IT LEARNED.** It adapted - +1 on a refusal, doubled on a missing ack -
  and then **snapped back to the minimum on the very next success**. So it re-discovered the
  server's ceiling continuously and paid cells to do it, which is why the loss held steady at a
  fifth instead of settling. `paceFloor` is sticky now and only comes down after 24 clean
  placements; `paceAfterSuccess`/`paceAfterDrop` are pure so the ladder can be argued with rather
  than watched.
- **AND A DROPPED PACKET SPENT THE CELL'S TRIES.** `MAX_TRIES` is two and drops come in runs of
  twenty, so **a single burst wrote about ten good cells off the frontier for the session** - and
  the loop then reported the spot unbuildable, correctly, about a spot it had broken itself. A
  drop only counts against a cell when it is ISOLATED (`spendsATry`): among landings it is evidence
  about the CELL, inside a run it is evidence about the CHANNEL.

`stationFromReport` and `holdHere` take a third number now. Placed is progress, REFUSED is the
world saying no and there is nothing to wait for, DROPPED is the link saying wait - hold the
station and let the pace back off. The ninety-second session stall is still the backstop, so a link
that never recovers cannot park the loop for ever.

**And it is reported.** `/cscan why` and every session report now print
`951 placed, 258 dropped by the server (21% of 1215 attempts), 6 wrong state, 0 given up - pacing at
4 ticks/block`. A dropped share that climbs is throttling, wrong states are a slot bug, given-up
cells are the design: three different problems that all used to look like *it is not placing*.

#### THE PREVIOUS SESSION'S FIX WAS A SILENT NO-OP, AND THE LOG PROVED IT

`Storage.stocked` was added so the shopping list would prefer materials there is somewhere to get.
It returned the index's own keys - `minecraft:stone_bricks` - and `Plan.loadPlan` tests a design
cell's item, `stone_bricks`. **It matched nothing.** The obtainable pass admitted nothing, the list
came out bit-for-bit the broken one it replaced, and 0.9.4's log showed the identical six
unfetchable materials with 38,909 stone bricks and 2,582 moss sitting in park containers.

`findExact` has always normalised both sides; this did not. **A no-op that looks like a fix is
worse than no fix** - it reads as evidence the theory was wrong, and the next session starts over
somewhere else. `whatIsInStockIsMatchedAgainstDesignCellNamesNotNamespacedIds` pins it.

#### "IT WILL START TO FLY SOMEWHERE THEN TURN AROUND"

`everPlaceableCached` treats a cell it has not had the budget to look at as PLACEABLE. That is the
safe direction while SCANNING - a wasted trip beats silently dropping real work - and it is the
wrong answer when the loop is about to COMMIT. Off the log: *"carrying 1024x moss_block - placing
that before any trip: 49 cells, nearest at 97600 203 80575"*, then two seconds later *"no usable
support/material combination"*, which cancels the flight, and then the same announcement again from
somewhere else.

The 49 cells were guesses made after the 400-per-recount budget ran out; the next recount held real
verdicts and disagreed with itself. `Printer.confirmPlaceable` answers for certain whatever the
budget says, and the nearest `CONFIRM` (24) cells of a commitment are asked with it - which is
exactly the cell `reanchor` then flies to. **An optimistic guess is fine to search with and must
never be flown at.**

#### The supply chain, and the design that can finish

    Park Complete: 291,285 of 524,033 cells have their material (56%)
      FARM   moss_block 98,953 . vine 9,609 . jungle_leaves 8,872 . water_bucket 7,801
      CRAFT  polished_blackstone_bricks 31,439 . cobblestone 11,491 . deepslate_bricks 8,415
      SMELT  smooth_basalt 25,966 . stone 3,702
      NONE   honeycomb 8,121 . blackstone 4,295 . ores

44% of the design cannot be built by any means the loop has, so its honest answer is a dead end -
which is what Jack kept watching. `mcbuild provision "Park Complete" --package --ship` wrote
**`Park Complete Ready`, 295,893 cells**, at the parent's own origin, and it inherits the parent's
`automation_approved` through `{**d.meta}` - so `/cscan follow "Park Complete Ready"` is a job that
can actually finish, where the parent could not and could not say so.

**Still open, and both need something only the game can give:** a moss farm loop (`/cscan farm` is
already generic, and moss alone is 19% of the park), and a plot-scale capture of the three park
islands so `sync` can measure progress at all - it currently answers NOT MEASURED, correctly,
because the only park captures are the three bare starter pads.

### THE PRINTER PLACED TWO BLOCKS IN THREE MINUTES, AND NO GATE SAID WHY (2026-09-08, chunkscan 0.9.6)

Jack: *"still a very glitchy experience, it flies back and forth, it doesnt make it to destination
and goes back to get more materials, it doesnt say it has placeable stuff but when loaded it does
say stuff is placeable."* Four symptoms, four separate causes, all named off the log and the journal.

**THE PACING FIX IS WORKING** - the drop rate is down from 21% to about 9% - and it did not matter,
because in that whole session the printer **attempted two placements**. The journal total went
1,215 -> 1,217 while the loop said *"2 cells placeable from right here"* and the analysis said
24,718 placeable in the design.

#### EIGHT SILENT RETURNS GUARD THE PRINTER, AND ONE OF THEM WAS CLOSED

The printer's tick begins with eight bare `return`s - no design, warming up, busy, pacing, a
container screen, a withdrawal, an unbox, following something else - and then
`Fleet.heldByOther(dir, printDesign, Fleet.me(mc))`. **`fleet.json` had `park complete` claimed by
the account `Enroz`, refreshed a minute earlier**, while this client's `mc.getUser().getName()` is
whatever the launcher logged in as. A design held by another account is indistinguishable, from
outside, from a printer that has nothing to do: no message, no counter, nothing in `/cscan why`.

That is this file's oldest failure shape - *a thing that does nothing, quietly* - in the one place
where it costs the entire session. `ChunkScanClient.printerBlocked` names the gate in words, and it
is reported in `/cscan why` and in the STALL, which used to guess: *"Printer off, out of reach, or
the spot cannot be built"* is three possibilities where the tick knows which. **A guard that stops
everything must say so; the two HEALTHY waits (mid-placement, and pacing between placements) are
deliberately not reasons and stay silent.**

#### "IT FLIES BACK AND FORTH" IS A CIRCLE WITH NO DAMPING IN IT

From the log, one recount apart, for minutes:

    course Y203 done - up to Y202 (56 cells)
    course Y202 done - up to Y203 (85 cells)
    course Y203 done - up to Y202 (50 cells)

**Nothing was finished either time.** The frontier is the lowest course of `here`; `here` is a
window round the ANCHOR; the anchor is the spot being built - which is derived from the frontier.
The body moves, the window moves with it, the lowest course flips, a new spot is chosen, and it
flies there. Two seconds later, again.

Spots and stations have both had hysteresis for months and the COURSE never did. `Loop.courseOrder`
puts the course in hand first and the rest behind it in the old bottom-up order. It costs almost
nothing in build order, because every cell in a frontier has already been proved to have a real
face to click TODAY - bottom-up is a preference here, not a correctness rule - and it is the
difference between working a course and touring one. The message only says a course is done when it
yielded nothing, which is the only honest use of the word.

#### "IT DOESNT MAKE IT TO DESTINATION AND GOES BACK TO GET MORE MATERIALS"

A spot is chosen because it holds work we carry; two seconds later the body is still in the air,
the window has moved with it, `canWork` reads false **about a place we have not reached** - and the
loop turns round for a chest. The trip already has this rule in the other direction (*"the trip is
over and the work is out of view: go back, and decide there"*) and it was never applied on the way
out. `headingToWork` suppresses the fetch question while travelling; the three-second going-nowhere
clock and the ninety-second stall both still run, so a spot that cannot be REACHED is still given
up on - what cannot happen any more is abandoning one that simply has not been reached yet.

#### A REMAINDER IS NOT A TRIP

    fetch: 2x white_wool from #430 Found shops (1984 there, 2 still wanted, room for 131)

A flight across the park, an approach, a chest and a withdrawal, for two blocks, because the list
wanted sixty-six and the pack held sixty-four. `Plan.covered` allows a `REMAINDER` now - and
PROPORTIONALLY, which the first version got wrong: an absolute threshold of sixteen calls a list of
four lanterns covered while carrying none, and the loop would never fetch a lantern again. Four
missing out of four is not a remainder, it is the whole reason the loop is going anywhere.

#### And the mismatch Jack named directly

*"it doesnt say it has placeable stuff but when loaded it does say stuff is placeable."* Both
numbers are true and they answer different questions: the start report is the WHOLE design at
radius 0, and the loop's frontier is one course of a window round the anchor. The gap is not a bug -
it is the working area doing its job - but the dead-end message read as a statement about the
design. It is not fixed here beyond the course stickiness, which removes most of the churn that
made the two disagree so visibly; saying it in words is the obvious next line.

**727 Java tests, 0 failures. Not flown.**

### FOLLOW ARMED THE PRINTER AND NEVER TOOK THE CLAIM (2026-09-08, chunkscan 0.9.7)

Jack: *"fix all"*, on the list the last session closed with.

**THE ASYMMETRY IS THE WHOLE BUG.** `/cscan print` has always refused a design held by another
account, loudly, at the moment you type it - *"two printers on one design fight ... refused rather
than warned, because by the time you notice it has already cost both accounts their feedback"*.
`/cscan follow`, which is what actually arms the printer for the LOOP, never asked: it set
`printDesign` and the printer's tick refused it silently on every tick for the whole session.

Following a design IS asserting that you are the one building it, so `follow` claims it now. Your
own claim and one whose lease has lapsed both self-heal in silence; a genuine conflict is said ONCE,
at the moment you asked for it, with the way out - not discovered ninety seconds later as a stall
with three guesses attached.

#### THE VICINITY HOLD PROMISED CELLS THE PRINTER CANNOT TOUCH

Off the log, five seconds apart, over and over:

    1 cell(s) placeable from right here - staying until they are in
    1 cell(s) in reach but nothing placed for 5s - moving

`Loop.VICINITY` was **5** and the printer's reach is 4.2 from the EYE. For a cell level with the
feet at horizontal distance d, the nearest face is at `d - 0.5` and the eye sits 1.62 up against a
face centre 0.5 up:

    (d - 0.5)^2 + 1.12^2 <= 4.2^2   ->   d <= 4.55

So four is inside the reach and five is not: **the hold was standing the body over work it could
not reach, holding it there for five seconds, and then blaming the spot.** Four now, and
`theVicinityHoldOnlyPromisesWhatThePrinterCanTouch` re-derives both bounds rather than trusting the
comment - it also asserts the radius is not needlessly timid, because one block less would have the
body sitting on top of its own work.

`Autopilot.SAME_TARGET` came down 4.0 -> 3.0 with it, and the test that caught that is a better
test than it was: bounding the drift tolerance by VICINITY started meaning something the moment
VICINITY became the printer's real reach, because a drift of the full reach carries the body out of
touch of the cells the station was chosen for.

#### And the dead end says where it looked

*"it doesnt say it has placeable stuff but when loaded it does say stuff is placeable"* - both
numbers were always true and they answer different questions. The start report is the WHOLE design
at radius 0; the frontier is one course of a window round the anchor. Worded as a fact about the
design (*"no usable support/material combination"*) it read as the loop contradicting itself two
lines apart. It now names the radius, the anchor and the course, and says the design has more
elsewhere.

**728 Java tests, 0 failures. Not flown.**

#### Not built, and the reason is a hazard rather than effort

**The moss farm.** `Farm` is a generic place-wait-harvest loop and moss does not have that shape:
it spreads from BONE MEAL used on a moss block, which is a use-item rather than a placement - a
`fertilise` mode is a fair generalisation and would serve saplings, kelp and grass too. What stops
it being written blind is that **bone meal spread is not bounded by the box**: it converts a blob of
whatever is in range, and on a park plot the thing in range is the park. The existing farm's safety
rule - only ever break the crop, only inside the box - cannot cover a mechanic whose EFFECT leaves
the box. It needs a sited medium with a margin, which is a wand box Jack draws, not a number this
file can invent.

**Four `stone` -> `smooth_stone` MISMATCHes** remain in the journal out of 1,217 attempts.
`inventorySlot` matches the item path exactly so it cannot pick the wrong stack; the likelier
explanation is another design or the declutter swap having moved the cell under us. Six in total,
recorded rather than chased.

### A TRIP IS WORTH WHAT YOU CAN PLACE AT THE FAR END (2026-09-09, chunkscan 0.9.9)

Jack: *"the pathfinding and priorities are screwed, i had a full inventory of copper blocks and
deepl slate, placed right next to the prism park complete structure, and it flew away to do
something else, so stupid"*. The whole session is in `latest.log` and it is nine lines long:

    22:33:44  park complete: 308498 left in loaded chunks, 18418 placeable, 0 out of view
    22:33:44    placeable / left / carrying / indexed
    22:33:44    2407 / 5951 / 0 / 9746   light_gray_wool
    22:33:44    1358 / 8503 / 0 / 15872  smooth_basalt        <- carrying 0, on every row
    22:33:44  shopping list ... 18x oak_stairs, 12x oak_log, 6x chiseled_stone_bricks ...
    22:33:44  nothing indexed to fetch - building with what you have
    22:33:44  nothing I can place within 16 of 97594 209 80627 on course Y204
    22:33:44  nothing here, but park complete has work I can place at 97599 201 80690 - going there
    22:34:12  shut in on 4 sides at 97599 200 80690 - climbing out before it becomes a hole
    22:35:45  STALLED - nothing placed in 90s.   0 placed in 3 min, 2 stalls, RESET #1

**IT FLEW SIXTY-THREE BLOCKS TO PLACE ONE SUBMERGED FROGLIGHT.** Measured against the shipped
composite, `97599 201 80690` is an `ochre_froglight` with `water` directly over it - a lamp in the
bed of a lake. Meanwhile the pack was full of copper and deepslate, and the design wants **9,048
`waxed_copper_block` and 11,643 `deepslate_bricks`** from Z80754 onward. It got shut in inside the
pond, climbed out, stalled twice, and reset with nothing placed all session.

**THE CAUSE IS ONE COMPARISON.** `Analyze.nearestPlaceable` - the dead-end escape, and the only
thing in the loop that can see past the 32-block detail sphere - ranked candidates by
`c.pos().distSqr(me)` and nothing else. One cell and a region are not comparable quantities, and
ranking them together always picks the cell: there is nearly always *something* nearer than the
place your pack is full of.

    a candidate is a REGION (Analyze.REGION = 2 x Loop.NEAR_RADIUS), scored by Analyze.worth:
    how many cells the pack could ACTUALLY put in there - cells, capped per material by what
    is carried - and the NEAREST region within Analyze.ENOUGH (half) of the best score wins.

The cap is what makes two places comparable: nine thousand cells of copper is not nine thousand
blocks of work with seventeen hundred in the pack, and without it one abundant material outranks
the place holding everything you are carrying. The band is what stops the fix becoming *always
cross the park*: a marginal gain never buys a long flight and a large one always does.

**A CANDIDATE IS A NEIGHBOURHOOD, NOT A BIN**, and the first version got that wrong. Scored on its
own bin, a grid cuts a long wall into a dozen fragments that each look like a poor trip: four
hundred cells of wall scored 32 and lost to a compact heap of forty. The score is the bin and its
twenty-six neighbours, so a mass is measured whole wherever the grid falls across it - the bins
exist to make that cheap and are not themselves what is ranked. **Both of the two tests that
failed on the first run were my own fixtures straddling the grid**, and the honest reading of that
was that the rule was wrong, not the fixture.

And it aims at the middle of the mass rather than at whichever of its cells is nearest, because
the loop's own window is `NEAR_RADIUS`: an anchor on the near edge of a region covers half of it
and re-anchors again on the very next recount.

#### THE REPORT SAID `carrying 0` ON EVERY ROW WHILE THE PACK WAS FULL

The other half of "priorities are screwed", and it is a reporting failure with teeth. `/cscan
analyze` ranks by placeable cells and says nothing at all about the inventory - so a session that
begins with a full pack of copper is told, in its own header, to *"fill the pack from the top of
this list"* and handed six materials it has none of. It then built a shopping list for them,
found nothing indexed, and called that a dead end.

The report leads with what the pack can already do now:

    CARRYING WORK: 1728x waxed_copper_block, 640x deepslate - 2311 cell(s) of it placeable now;
    best group is 1728 at 97590 210 80755

...or says plainly that nothing in the pack can be placed anywhere loaded, which is the only
honest reason to go shopping while carrying a full inventory.

#### And "nothing left within 200" was said about a cell one block away

`Loop.WORK_RADIUS` printed while `workRadius` - usually 16 - is the window actually looked in.
Both the radius and the anchor are named now. A message that overstates where it looked reads as
the loop contradicting itself two lines apart, which is exactly what Jack was reading.

**752 Java tests, 0 failures.** `AnalyzeTest` pins the rule as arithmetic - `bestOf` is pure over a
cell list, an inventory and a position - including the flight that started this: one froglight at
60 blocks against a building at 300, and the pack decides.

**Still open, and stated rather than guessed at.** `waxed_copper_block` and `copper_block` are
different items, and so are `deepslate` and `cobbled_deepslate`/`deepslate_bricks`; if the pack
holds the unwaxed or the wrong dressing, the loop is right that it can place none of it and only
`/cscan analyze` will say so. Nothing here has been flown. And the session's own log carries a
separate, unfixed line - *"There is no ENABLED Litematica placement called park complete"* - which
is a diagnostic written when litematica-printer did the placing; this mod places its own blocks
now, so that message names a cause that no longer applies and should be re-worded or removed.


