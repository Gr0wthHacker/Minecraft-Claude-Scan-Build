## The court hall: apocalyptic beauty, and where the glass may go (2026-08-20)

`configs/court_hall.yaml`, `gen/courthall.py`. **265 blocks, 0 problems, overlap 2, 0 expensive.**
Jack laid a deepslate frame on the Y195 course and asked for apocalyptic beauty with glass panes,
plus a water feature in the bay that sits one course down. The audit decided almost all of it.

### The site is a one-block shelf hanging in the void

The single most useful measurement: the column at x-24229 has **exactly one solid course between
Y150 and the plate**, and it is Y194. The court is not a room dug into the island - it is a shelf.
Rock closes it east and west, both ENDS have fallen away into open sky, and the island's own
underside is the ceiling at Y201/202. The room is already a ruin; the design only has to admit it.

That produced the rule the whole file turns on. **Glass in front of rock is a window onto stone**:

| run | outside open at Y196-200 | treatment |
|---|---|---|
| west  x-24234 | **0%** | pilasters |
| east  x-24222 | **8%** | pilasters |
| north end z30006 | **95%** | GLAZED |
| south end z30029 | **96%** | GLAZED |
| divider z30023 | court both sides | balustrade over the water |

So only the two ends get panes - and they are the two places with nothing behind them for hundreds
of blocks. `_kind` probes it rather than being told, the same discipline as the store hall deriving
its doorway.

### Classifying a run took two goes and both failures shipped a clean audit

- **Scoring both perpendicular directions and taking the more open one made EVERY run glazed.** The
  room's own interior is open by definition, so the rock flanks scored as open and came out glazed -
  windows onto stone. Inward has to be resolved first: it is the side carrying the court FLOOR.
- **Then rock and court floor both read as "solid below"** - the island's flank and the room's own
  paving are equally floor - so the flanks came out as internal DIVIDERS and got a balustrade. The
  three cases only separate one course UP: rock is closed above, court is open above and floored
  below, void is open above with nothing under it at all.

### What "apocalyptic" means here, in code

The void tower already paid for this: *what makes voxels read as ARCHITECTURE is regularity and
openings, not damage* - its first jagged attempt was rejected on sight as "a tossed grouping of
vague blocks". So **the ruin takes GLASS, never the order.** Every bay keeps its pier and its
cornice at any `ruin` setting; `test_ruin_takes_glass_and_never_the_order` pins that the pier set is
identical at ruin 0.0 and ruin 1.0. The south screen is intact, the north is broken - one whole bay
open, top course gone in others.

And a rock flank gets **pilasters, not infill**. Filling those bays is 120 blocks of tidy deepslate
laid over the most apocalyptic surface in the room. The surviving order is the piers; the rock
between them is the point.

### The pool is a tank, and it would have frozen

`freeze_guard` in `court.yaml` exists because **this court froze on its first build - 29 ice
blocks.** Snowy biome, and 16 of the sunken bay's 55 columns are open sky. Water needs block light
>= 10. Verified by propagating light through the built model: **every water cell lands at 12-14.**

- Guard lights are plain `lantern` (15). **`soul_lantern` is exactly 10** and is one block of
  falloff from failing, so it is mood only. That distinction is the whole guard.
- A guard lantern is **waterlogged and has its own footing**. Not waterlogged, the water above flows
  down into it; skipping the water there instead punches a hole through the pool's surface at every
  guard - which is what the first build did, nine holes in a 27-cell sheet. And a lantern is not a
  full cube over a floor that is a skin over open VOID, so without a block under it the audit says
  "standing on air".
- The bay's floor is one block over nothing and the Y194 course runs on east past the plinth, so the
  basin is built as a tank: floor at Y193, wall ring, water at Y194. Its top face is exactly the
  sunken bay's own walking level - the "one block down" Jack described. **0 leak faces.**

### Palette: there is only one glass you can afford

`glass_pane` is **ok**; plain `glass`, `tinted_glass` and **every** stained pane are **expensive**.
Store holds **1,060 glass (~2,800 panes)** against 26-49 of each stained pane, so the cheap material
is also the only one there is enough of. The order is `deepslate_bricks` - Jack's own edging block,
`ok` tier, 51 darker than stone brick, and 512 in store against 172 needed.

**Still open:** four supply chests (stone 768, deepslate bricks 256, wool) stand in the north bay.
The design comes within **2** of one and shares a column with none - the plinth line is exempt from
`container_clear` because Jack laid that line himself, past those chests. Move them and the north
screen has more room.

### One load, one trip: the fetch policy, walking, and the goal that blocked motion (2026-08-20)

Four things Jack asked for after the second real flight, and one bug found on the way that explains
more of "it gets stuck" than any of them.

#### The loop went shopping while it had work to do

The fetch decision was made **per SPOT**: if the best cluster was short of anything, fetch. So with a
full pack and hundreds of placeable cells it flew to a chest, took that one spot's shortfall — often
sixty-four blocks — and flew back. On a design of any size that is a session of commuting.

Two questions now, and the ORDER between them is the whole policy:

1. is there anything at all I can place with what I am carrying? → **build**, and do not fetch
2. otherwise: something to fetch, and room to put it? → **fetch until the pack is full**

So a trip ends when the PACK is full or the DESIGN is covered, never when one spot's shortfall is
met, and a fetch only starts when the loop is genuinely out of work — out of stock, or every
remaining cell blocked or sealed. `Plan.anyDoable` and `Plan.nextFetch` are the two predicates and
they are pure, so the policy is tested without a client.

Three details the numbers forced:

- **The shortfall is the DESIGN's, not the spot's.** `Plan.fetchTargets` totals every remaining cell;
  `restockTargets` still answers the per-spot question for the report, which is a different question
  and keeps its own answer.
- **How much to take is `min(still wanted, room in the pack, what the chest holds)`.** `Work.room`
  counts empty slots and the free part of matching stacks over the 36 real slots — armour and offhand
  would read as 320 blocks of room that does not exist.
- **No room for the biggest shortfall is not the end of the trip.** A pack full of stone bricks has
  plenty of space for the deepslate, so `nextFetch` walks the whole list. Judging only the first
  entry is a trip not taken.

Dead ends are now told apart, because they want different answers: *nothing to place and nothing
indexed to fetch* sends you to `bom`; *pack full of what you cannot place here* tells you to store
something. Said once, not every two seconds — a message on a 2-second timer is a reason to turn the
loop off.

#### `/cscan find` is a substring search, and a fetch was using it

`stone_bricks` matches `mossy_stone_bricks`, `cracked_` and `chiseled_`. The loop flew to whichever
was nearest, asked for a block that was not in there, took zero, blacklisted a perfectly good chest
and moved on — **and it looked exactly like the chest being empty**, which is why it survived a
session of watching. `Storage.findExact` is what a TRIP uses; `find` stays fuzzy because
`/cscan find wool` is a question about wool in general.

#### THE GOAL BLOCKED MOTION, so the router could never reach it

The one worth remembering. `Nav.route` never checked that the destination cell was passable, and
**every fetch target is a chest's own cell** — a chest `blocksMotion()`. Every build spot is a
cluster CENTROID, which lands inside rock about as often as not. The goal was therefore never
expanded, the search ran to the end of its budget, returned empty, and the caller fell through to
flying straight at the wall the chest is in. Raising the node budget makes this *slower*, not better.

`GOAL_SLACK` (2) finishes at the nearest passable cell to a solid goal, with a slight bias toward
staying level so a chest in a wall hands you the cell in front of it rather than the one above it. A
genuinely buried goal still has no route, and that is asserted separately — the slack is for a chest
in a wall, not for pretending sealed cells are reachable.

#### The rest of the navigation work

- **`MAX_RANGE` 256 → 512.** The gate is free; what costs is the search, and that is bounded
  separately.
- **`MAX_NODES` 40,000 → 120,000**, plus a **25ms wall-clock budget** checked every 256 expansions.
  The honest limit on the client thread is "how long may I freeze the game", which is a number of
  milliseconds, not of nodes. The raise is worth much less than it looks — see the next two.
- **A clear line costs ZERO nodes.** `route` tries `clear()` first and returns the destination as the
  only waypoint. Across this island's open sky that answers most calls, including most long ones.
- **A long search that fails is re-tried toward a SUB-GOAL** 128 blocks along the line. A* is cubic in
  the distance and staging is linear, the route is recomputed twice a second, so staging turns "no
  route, flying direct" — the thing that flies you into terrain — into real progress and a fresh
  search from closer in. It is NOT a partial route: it is a shorter search that SUCCEEDS, which is
  the honest version of the instinct the partial-route rule rejected.
- **A walking route is a different route.** `Nav.standable` requires footing as well as headroom, with
  one course of slack under the floor for a step DOWN — without that every route breaks at a stair
  lip or a doorway sill. `Nav.of` routes through open air thirty blocks above a floor, which is a
  perfect flight plan and a walk into a hole.

**Two of the Nav tests were pinning the implementation rather than the property**, and the
line-of-sight shortcut failed them: their doorway was dead ahead, so the straight line went through
it and there was nothing to search. Moved off-axis, they test the search again — and
`itDoesNotCutTheCornerOfADoorFrame` had been passing VACUOUSLY over a one-element list.

#### It walks when it cannot fly

Indoors is where routing matters most and where flight is least likely to be on, and the autopilot's
answer there was to warn once and do nothing — parked in exactly the case it was built for. It walks
now: horizontal delta only (the vertical belongs to gravity), a jump on horizontal collision or when
the next waypoint is above you, never mid-air, and the look angle stays level because a walking
player does not stare at the floor.

#### NO KEY INTERRUPTS IT

`playerIsDriving` handed control back on any movement key. That reads as a safety property and
behaves as a fault: **an unattended loop is unattended precisely because you are typing in chat or
looking at another window**, and a key left down through a focus change disarmed an hour of work
silently. It is gone, `stop()` went with it (no callers — which is the honest shape of the decision),
and `/cscan stop` is the off switch.

`Screens.anyOpen()` went the same way: it paused the flight for chat, the map and the pause menu.
Only a **container** pauses it now, because flying off mid-withdrawal half-empties a chest and then
blacklists it.

Both are pinned by reading the SOURCE, because what is being asserted is the ABSENCE of something and
there is no state to look at. The first version of those tests failed on the comments EXPLAINING why
the rule was removed — a check that forbids naming a thing forbids explaining it — so it strips
comments first, and there is a test that the stripper strips comments and not code.

### What the second flight found: one frame a second, and pressing on the wall (2026-08-20)

Four reports off a live run, and every one is a bug the tests could not have caught as written.

#### `autofly on` dropped the client to 1 FPS, and nothing about it was slow

The route was invalidated by `walkRoute != flying`, where `walkRoute` had just been set to
`!flying`. **That expression is true whenever `flying` is true**, so an A* ran EVERY TICK instead of
twice a second — twenty searches a second, each allowed 25ms, plus the allocation churn of a
120,000-node budget.

The lesson is the shape of it. **A stale-check that is accidentally always-true is invisible**: the
routing is correct, the steering is correct, every test passes, and the only symptom is the frame
rate. It is now stored as the stance itself (`routedFlying = flying`) rather than as its negation,
pulled out into a pure `needsRepath` with tests on it, and floored by `MIN_REPATH_TICKS` so that no
invalidation rule — this one or a future one — can produce a per-tick search again.

Raising `MAX_NODES` is what made this catastrophic rather than merely wasteful. A budget is only ever
spent by a search that FAILS, so it is safe right up until something makes searches run constantly.

#### "Still trying to go directly through blocks"

The no-route fallback was to fly at the goal and add a little upward velocity. That does not lift you
over anything — it grinds you along the wall at an angle, because the forward component never stops
pushing. Two replacements:

- **`Nav.escape`** — when there is no route, flood outward from where you stand and take the
  reachable cell that gets CLOSEST to the goal. Up, down, left, right, behind: whichever actually
  helps. Breadth-first, bounded by cells rather than by geometry, and only ever run after a real
  search has already failed. Re-run at each repath it is a wall-follower that keeps making progress.
  **Getting round an obstacle is a search, not a nudge.**
- **`unstick`** — for the genuinely-shut-in case, zero the components of a direct guess that press
  into a block, tested at the feet AND the head. A ceiling then slides you sideways and a wall slides
  you up. All three blocked and it rises, which beats vibrating against a corner.

A test of mine was wrong here too, and instructively: *"a sealed box has no escape"* is false —
crossing the room really does get you closer to something outside it. What matters is that it never
leaves the box and that it CONVERGES, so that is what is asserted.

#### `MAX_RANGE` 512, and staging that shortens

One 25ms budget is now shared across the whole `route()` call, so the staged retries cannot multiply
the cost, and staging halves its distance on each try — a sub-goal 128 blocks along the line lands
inside the island as easily as in front of it.

#### "It needs to move faster"

`SPEED` 0.35 → **0.75**. Vanilla sprint-flight is about 1.0, so it is still under what a player does
by holding a key, and 0.35 on a 240-block island was a long time watching yourself travel.

**Everything that makes speed safe is a function of it, not a constant beside it.** At 0.75 you cross
the old 1.0-block waypoint radius in under two ticks — past the turn before the next waypoint is even
selected — so `waypointRadius` is 2.5 ticks of travel and the approach taper scales with it. A fixed
radius and a raised speed is how a router that works becomes a router that clips every corner.

#### "Fetch says it took 0x even when it actually took"

It did take them. The message was about a **second, pointless withdrawal**: the first finished, the
phase left `busy()`, the next recount two seconds later saw itself still standing at the chest and
began again — finding nothing of what it asked for, reporting `took 0x`, and then **blacklisting a
chest that had just worked**.

A chest is now left alone for the cooling-off period after ANY completed withdrawal, not only a
failed one. There is no version of "go straight back to the chest I have just been through" that is
useful. And taking nothing no longer reports as `took 0`: it says the index was out of date and names
the chest, because "took 0" reads as a failure of the taking rather than of the record that sent you
there.

### A SPOT IS A TRIP, NOT A PLACE TO STAND (2026-08-20)

Jack: *"when its flying to place make sure it moves around the placement area in a radius flying
different angles… printer wont work if it just stays in a small place the entire time it wont ever
move on."* Exactly right, and it is the biggest gap in the loop so far.

**`radiusFor` sizes a spot to one INVENTORY LOAD** — 24 blocks carrying a shulker, 96 carrying six —
which is correct for deciding where to make a trip to. The loop then guided you to that spot's
CENTROID and stopped, because arriving is not disarming. **The printer reaches about four and a
half blocks.** So it placed whatever happened to lie near the middle of a region up to 96 across, ran
out, and sat there until the ninety-second stall watch abandoned a spot that was almost entirely
unbuilt — and then the next recount picked the same region again.

Two levels of hysteresis now, and they answer different questions:

- **the SPOT** — am I still working this region? Matched by PROXIMITY, not equality: a cluster's
  centre is the centroid of the cells still to do, so it drifts a block or two every time you place
  some, and comparing it exactly would call every recount a new spot and re-announce twice a second.
- **the STATION** — where in it do I float? The cells binned at the printer's reach; you are sent to
  the fullest bin, nearest on a tie. There is no state to keep: as those cells get placed the bin
  empties and the next call moves you on.

Four things that had to be right, each of which produces a loop that looks like it is working:

- **A station RE-CENTRES as its cells get built.** A bin is a 4-cube, so its far corner is 3.46 from
  the middle and the printer's slack over that is about a block. Standing where you first arrived
  builds the near face and stops; re-aiming at the centroid of what is LEFT walks you round the group
  from a new angle each time some of it goes in. That is the "different angles", and it falls out of
  re-centring rather than needing an orbit.
- **`Nav.standoff`, not `Nav.reachable`.** `reachable` answers "may a route END here" and takes the
  first free cell it finds, which beside a wall is the crevice between two blocks. A place to work
  FROM is scored on OPENNESS — at least three of six neighbours clear — before distance, and biased
  toward the side you came from. This island is a deck under a plate full of hoppers, chests, rails
  and roots; a spot wedged between two of them is one the printer never finishes.
- **A per-station stall of 20s**, against the spot's 90. They ask different questions: *is there
  anything left here the printer will take* versus *is this loop doing anything at all*. A bin the
  printer will not take — wrong chunk, blocked by an entity, obstructed by something the design does
  not know about — must not cost a minute and a half. Abandoned bins are remembered, and when every
  bin has been tried the set is cleared rather than stranding the spot for good.
- **The spot-level stall has to drop the SPOT.** It cleared the arrow and left `spotCentre` set, so
  the proximity hysteresis chose the same region straight back and the stall repeated for as long as
  you left it running.

`ARRIVED` 3.0 → **1.5**, because stopping three blocks short of where you were sent spends the whole
reach budget before you start — and a SOLID destination is arrived at from outside it, or the flight
noses at the face of a chest trying to satisfy a radius no route can reach. `tests/PlanTest` pins the
arithmetic (`half-diagonal of a bin + standoff + arrival < printer reach`), because that relationship
breaks silently the moment anyone tunes one of its three numbers.

#### `/cscan autofly speed <n>`

0.10 to 1.00 blocks per tick, default 0.75, reported in the HUD beside the mode (`[route 3 @0.75]`).
The cap is AT vanilla sprint-flight rather than above it: "no faster than a player can actually go"
is the one bound that is defensible without knowing the server's rules.

**The walk scales with the same dial.** A speed setting that only changes flight stops working the
moment you go indoors, which is where you would most want to slow it down.

### Making it survive the night (2026-08-20)

Six things, two of which were the loop doing something actively wrong.

#### A chest that WORKED was blacklisted like one that failed

My own regression, from the fix two commits earlier. To stop a second withdrawal opening the same
chest two seconds later and reporting `took 0x`, EVERY completed withdrawal was marked for the full
minute. The store hall is piles of thousands of one item, so after building out a pack the loop came
back, skipped the best chest, and either flew somewhere worse or reported nothing fetchable.

Two windows now, because they are two different facts: **60s** for a chest that was empty or came up
short — it has no more, leave it alone — and **5s** for one that handed over what was asked for. It
cannot be zero: the only reason to mark a successful chest at all is to outlast one recount.

#### The fetch could still navigate to chests that are gone

`Storage.findExact` had no world filter. The index only ever grows — it is written when you OPEN a
container and cannot be told about one you broke — and it measured **179 dead records out of 339**.
Harmless while `find` was advice; not harmless once `fetch` and `follow` NAVIGATE to those
coordinates. `Storage.live` filters the index against the loaded world on the way past, and
**unloaded is still not absent** — a chunk you cannot see is not evidence the chest went.

#### The loop re-derived everything every two seconds

`Storage.load` is a file read and a JSON parse; the scaffold and seal probes are a six-neighbour
lookup on every remaining cell, which on a few thousand cells is tens of thousands of world lookups.
Both ran every two seconds for the whole session, whether or not anything had changed.

- **The index is cached on the file's MTIME**, not on a timer. A timed cache would walk you to a
  chest the loop still believes is empty — you open a chest precisely so it can be told. And the
  cached map is **unmodifiable**, because two other callers of `load` do `removeIf` on their copy;
  a shared mutable map here is a cache that silently loses containers.
- **The scaffold/seal probe is memoised on the todo COUNT**, which is the only honest evidence
  anything moved: the printer never reports, so a count that has not changed means nothing was
  placed and the answer cannot have changed either. That makes flying to a chest and waiting at a
  station free, and that is most of a session.

#### It resumes after a disconnect

Everything the loop knows lived in static fields, so a drop at three in the morning ended it
silently. `session.json` holds four things — design, autofly, follow-all, speed — and the JOIN event
picks them up.

- **The intent is restored, not the state.** The abandoned-station set, the cooling-off chests and
  the session counters are all judgements about a world that has moved on while you were away.
- **A grace period of five seconds before anything moves.** On the tick you join, most of the world
  is unloaded, and `Nav` counts unloaded as passable — which is right for a route in progress and
  quite wrong as the first thing you do after arriving.
- **`/cscan stop` deletes the note.** Leaving it would have the loop start itself again the next
  time you joined, which is the one behaviour a panic button must not have.
- It does resume MOVEMENT AUTOMATION by itself. Announced loudly, held off, and one word to stop —
  the alternative, restoring the design but not the flying, restores the half that does nothing.

#### `/cscan follow all`

Works every tracked design in turn. A loop that finishes the deck floor at 2am and then idles until
morning is half a loop, and `plan` with no argument already ranked work across all 23 — only
`follow` insisted on being told which. A design whose work list will not load is SKIPPED rather than
fatal: one un-regenerated sidecar must not end an overnight run.

#### The routes stopped hugging walls

The search's only cost is distance, so the cheapest route grazes every corner. It is legal and it
flies like something nervous.

**The obvious fix is a clearance term in the search and it is the wrong one** — scoring openness per
node is six more world lookups on every one of up to 120,000, which is the cost that has bitten this
file twice now. `simplify` has already thrown away everything but the CORNERS, so `Nav.loosen` nudges
those few points toward open air afterwards, for nothing. A nudge is kept only when both legs through
the moved point are still `clear`, which is what stops it widening a doorway waypoint out of its
doorway.

**And a test of mine stopped being a control rather than starting to fail.** `escapeGoesAround...`
built a tall finite wall and asserted no route existed; with staging and the raised budget the router
now finds its way round the end of it. That is the router getting better. The control is a sealed
room now — *a wall in the open is not sealed*, which is the third time these tests have learned it.

### The island is the test ground (2026-08-20)

Jack: *"realistically this testing should be using my island design as the testing ground, it has all
of the variances and variables, randomness, etc."* Right, and it found two bugs in the first run.

`NavTest`'s fixtures are a wall with a hole in it, a tunnel, an L-bend — worlds I invented, testing
the cases I thought of. `tools/export_navfixture.py` exports the capture's own geometry instead:
**103x121x103 at the origin lock, 41,455 solid cells, 15 KB gzipped**, checked in at
`chunkscan/src/test/resources/island_nav.bin.gz` and read by twenty lines of bit-shifting in
`IslandNavTest`. Regenerate it after a rescan — every assertion is derived from the fixture, so a new
capture moves the numbers and not the expectations.

    python tools/export_navfixture.py

**The solidity model is STATED, not assumed.** We have no client here, so `blocks_motion` reads the
registry TYPE: air, fluids, plants, vines, wiring, signs and carpets do not stop you; everything
else does. It is close, not exact — a snow layer's height and a repeater's two pixels are not in the
registry — and it is applied to BOTH sides of every test, so the connectivity a test asserts is
connectivity under the rule the route is found under. Where it differs it errs toward SOLID, which
makes a router refuse a route it could have flown rather than fly one it could not.

#### The bug the real island found in the first run

**A route came back whose every waypoint was in open air and one of whose LEGS went through the
rock.** A single diagonal step, (+1,−1,+1), at −24207 219 30009.

The no-corner-cutting rule tested the three ORTHOGONAL components of a diagonal — beside, below, in
front — which is the standard formulation and is not enough in three dimensions. It never tests the
cell diagonally ACROSS, and that is exactly where a body sweeping between the two corners passes. So
the search and `clear` disagreed about what one step costs: the search said yes, the flight clipped
it, and `simplify` faithfully preserved the illegal leg because `clear` refused to merge it away.

`stepFits` requires the whole BOX a step spans. That makes the two agree by construction — every
cell `clear` samples on a one-cell step lies inside the box — at about twice the neighbour cost,
bounded by the same millisecond budget as everything else. **No hand-written fixture produced this**;
it needs a diagonal gap between two blocks, which real terrain is full of and a test author is not.

The second was mine: `GOAL_SLACK` is a BOX radius, and two assertions measured it as a sphere. Slack
2 permits (2,2,2), which is 3.46 away as the crow flies. It passed on the synthetic fixtures because
the answer there was always on an axis.

#### What the island tests actually assert

- **Every route it returns is legal** — every waypoint passable, every LEG clear, over 60 sampled
  pairs. Then the same again through `simplify` and `loosen`, because what the autopilot flies is
  the composition and each stage can undo the last one's care.
- **Places that are connected always get a route.** The hard direction, and the one that flies you
  into terrain when it fails. A flood finds what is GENUINELY connected under the router's own
  predicate — including its corner rule, or the flood claims a connectivity the route cannot deliver
  and the test blames the wrong thing — and then a route is demanded between pairs of it.
- **A chest-sized target in the geometry is still reachable**, sampled from real solid cells rather
  than from a chest I placed for the purpose.
- **A standoff can see its work**, on real surfaces, within the reach budget; most are roomy and the
  tight ones are the tunnels, which are real.
- **Walking routes never float**, and **escape always makes progress or admits it cannot**.
- **No single search hitches the client**, measured where the frontier meets real geometry rather
  than an empty box.

### The pre-upload audit of the whole cycle (2026-08-20)

Fetch -> fly -> take -> fly -> stand -> print -> move on, read end to end before the jar went up.
Eight findings; the last two are the ones that would have cost a night.

- **The arrival was a RACE between two files.** Autofly stopped at 4.0 from a solid goal and the loop
  started the withdrawal at 4.0 — measured slightly differently, an entity's position against a
  block's. The losing outcome is a loop that hovers at a chest for ever without opening it, which is
  the same bug this project already shipped once at 5.0 against 4.5. `ARRIVED_SOLID` is 3.0 now, a
  clear block inside where the loop acts, and `AutopilotTest` asserts the margin across both files.
- **A station that placed nothing moved on too readily.** A bin is a 4-cube, so its far corner is
  3.46 from the middle and the printer has 4.5 — a standoff a few blocks out spends the rest. Now it
  moves in CLOSER first (`standoff` at radius 1) and only abandons the bin on the second stall.
  Abandoning a bin you could have reached leaves those cells for a later pass that makes the same
  mistake.
- **A re-offered bin kept its old clock**, so it stalled again on the very next recount and the spot
  span through its bins as fast as the loop could count them.
- **Arriving was announced every couple of seconds.** The station re-centres as cells go in, so the
  target moves constantly — and every move said "arrived". Silent while following; the HUD says it.
- **An exception inside the decision ended the session.** One catch covered both the work-list read
  (permanently fatal — no work.json) and every judgement after it (transient, about a world other
  mods are changing). Now separated: a hiccup costs a tick and is reported three times, twenty in a
  row gives up. The two tick handlers that drive movement and looting are guarded too, because a
  throw out of a tick event is a client CRASH — the worst possible outcome for a loop whose whole
  point is running unwatched.
- **Nothing checked that there was anything to print.** The printer prints a Litematica PLACEMENT, so
  a design never placed, or toggled off, is a session of flying to the right spots and putting
  nothing down. `Litematica.enabled(name)` answers three ways — yes, no, and *could not ask* — and
  the third is not reported as the second: a soft dependency that changed shape is a different
  problem from a placement you forgot to make. Said once at the start, and again when the loop has
  placed nothing at all after two stalls.

#### OUT OF VIEW IS NOT FINISHED

`Work.split` can only diff cells in chunks the client HAS, and it silently skipped the rest — so an
empty `todo` means "nothing left within sight", not "the design is done". On a 240-block island that
is routinely most of a design.

The consequence was worse than a wrong percentage. **Start `follow all` at the far end of the island
and every tracked design reads complete in turn** — `nextDesign` asked the same question — so the
loop announces that all 23 are finished, in about a second, and stops. An overnight run that ends
before it starts.

`Split.unseen` counts them and `Split.complete()` is the question the loop now asks. When there is
nothing left in sight but cells out of view, it FLIES TO THE NEAREST ONE: going to look loads the
chunks, and the next recount has real work. That trip also resets the stall clock, because crossing
the island is not a stall.

`unseen` is deliberately not counted as built — the tempting shortcut reports a design finished and
quietly leaves it half-standing.

#### Smaller things

`/cscan follow` now says when autofly is OFF. `follow` points and `autofly` moves; starting
half-armed looks exactly like the loop being broken.

### Flight was lost because it LANDED (2026-08-20)

Jack ran it and it *"turned off fly and almost fell into the void and lost everything"*. The worst
thing this mod has done, and the diagnosis is worth more than the fix.

**I blamed the speed, and the speed was innocent.** `SPEED` had just been raised 0.35 -> 0.75 in this
session, so it was the obvious suspect, and I convicted it: dropped the constant, capped the dial,
and wrote a note into this file stating as fact that *"the first flight at 0.75 had the server revoke
flight in mid-air"*. Jack had watched it happen. **It landed on a block.** On a server where flight
is a plugin grant rather than creative mode, touching the ground ends it — no anticheat, no speed, no
mystery.

**A change you have just made is exactly the suspect that gets convicted without evidence**, and a
wrong cause written down confidently is worse than no note at all: everything downstream of it is
tuned against a fiction. The speed is back at 0.75 and the cap at 1.0.

The real fix is `keepAirborne`: the flying step never DESCENDS inside a block and a half of the
floor, and climbs off one it has already met. Nothing had ever said the autopilot must stay off the
ground — it was flown to a standing spot beside the work, and a standing spot is on a floor.

- **Unless there is a ceiling.** Indoors a room is two courses high, and forcing a climb there grinds
  you along the ceiling for ever. Landing on a floor inside a building is not the failure being
  guarded against; landing on the deck with the void one step away is.
- **The clearance is not decoration.** A block and a half clears a slab, a stair or a lip, and still
  leaves a station a course above the floor well inside the printer's reach.

#### What stays, because it is right for any cause of losing flight

The walking rules from the first, wrong diagnosis are kept — they are what turned a lost flight into
a near-disaster, whatever caused it. **Building requires flight; walking is only ever a fetch**, and
only with ground under it. That is Jack's rule and it is better than "walk whenever you cannot fly":
where the loop BUILDS is out over the work — the belly, the underside of the plate, a lowland eighty
blocks down — and on foot every one of those is the air over the void. Where it FETCHES is a
container somebody walked to, which is a floor.

- Losing flight while off the ground is an EMERGENCY, not a mode change: hands off, say so, disarm.
  Resuming automatically into whatever took it away is how you lose the inventory a second time.
- Falling with nothing below and autofly does nothing at all. Steering a fall never improves it.

### It highlighted cells that cannot be built yet (2026-08-20)

Same session, same root: `Plan.station` was picked over EVERY cell left in a spot, and a spot's cells
include the ones with nothing to place against. So a station could be made entirely of mid-air: you
are flown to it, the printer places none of it, and twenty seconds later the loop moves to the next
bin of mid-air. That is also most of "it got stuck immediately".

`Cluster` carries `ready` now — the cells that are not floating and not sealed in — and everything
that POINTS A PLAYER AT THE WORK uses it: the station, the highlight, the count. `cells` stays as
what is left in the region, because those cells are real work; they are just not this pass's work,
and their supports have to go in first.

`doable()` is derived from `ready` rather than computed as `cells - blocked - sealed - short`. Same
number by a different route, which is exactly how the count you are told and the cells you are sent
to drift apart.

### "It detected tuff as the same as deepslate" (2026-08-20)

**There is no block-equivalence table anywhere in the mod** — `Work.matches` compares names exactly
and the Java side has no family list at all. What actually happened is a generator decision:
`courthall._put` refuses to place where anything is already standing (*"never cover what is already
standing"*), so wherever the island's own rock occupies a cell of the order, that cell is dropped
from the design and the loop never hears about it.

Measured on `Court Hall` against the 12:38 capture — 90 design cells whose world block differs:

| design wants | world holds | cells |
|---|---|---|
| `deepslate_bricks` | `stone_bricks` | 28 |
| `deepslate_bricks` | air (real work) | 23 |
| `deepslate_bricks` | `cracked_stone_bricks` | 7 |
| `deepslate_bricks` | `moss_block` / `mossy_stone_bricks` / `mossy_cobblestone` | 17 |
| `lantern` | `deepslate_bricks` | 4 |

**A litematica printer places into AIR; it never replaces.** So those cells can never be completed by
the loop however long it runs, and the loop's only signal was getting quieter. It says so once now,
and points at `/cscan check`, which marks them amber.

**Whether the order should REPLACE Jack's stone brick is his call, not a silent one** — it is
`_put(..., force=True)` plus dig cells, and it means breaking 58 placed blocks.

### And a third meaning of "cannot be placed" (2026-08-20)

Same session: *"its still choosing clusters that cant be placed"*, after `ready` had already fixed
the first two. There are THREE questions and the loop was answering the wrong one each time:

    cells   everything left in this region, floating and sealed included
    ready   minus those two - but `floating` counts an EARLIER cell of the same design as support,
            which is right for "does this design need scaffolding" and wrong for "can I place it
            now": that support may not be built, and may not even be in this bin
    now     has a real face to click, in the WORLD, this second

`Work.placeableNow` asks the third, and the station is picked over that. `floating` keeps its own
rule, because taking the design's own earlier cells out of THAT would report every wall in the
project as needing scaffolding.

### It crashed into a block at the lowlands (2026-08-20)

Flight lost again, and a different cause from landing on the deck: it flew into terrain **that was
not loaded yet**.

**`Nav` counts an unloaded chunk as PASSABLE, on purpose** — refusing to route through one would fail
every long flight on a 240-block island, and the route is recomputed twice a second so it sharpens as
the world arrives. That is right for ROUTING and dangerous for FLYING, and nothing had ever separated
the two: the autopilot took that route at cruise into blocks nobody had seen.

**The lowland is the worst case by construction.** It is 150 blocks below the deck, so the whole
descent is into chunks arriving on the way down — and `keepAirborne`'s clearance check read open air
the entire time, because **an absent chunk answers "air" to every question you ask it**. The floor of
the lowland is indistinguishable from open void until you are standing on it.

- **`BLIND_SPEED` (0.12) when the next 8 blocks are not loaded**, ahead or two below.
- **No descending at all while blind.** Slow is recoverable; a landing is not.
- **An unloaded cell under you counts as GROUND** — the exact opposite of what `Nav` does with one,
  and right for the opposite reason.

`clearanceBelow` and `loadedAhead` were pulled behind an `Autopilot.View` so they can be tested:
they are entirely about the difference between *there is nothing there* and *I cannot see*, and that
cannot be exercised against a live client.

### The fixture now spans the whole island (2026-08-20)

Jack captured `islandlow` from inside the lowland: **103x335x103 at Y-64..270**, the full vertical
rather than the plate. 71,815 solid cells, 26 KB packed. The old fixture started at Y150, so the
descent that crashed was not in the test ground at all.

And the sampling was wrong even where it had coverage. **Uniform sampling over a capture that is 2%
solid is mostly a test that empty sky is empty**: two random open cells usually have nothing between
them and every router passes. `nearTerrain` samples cells within three blocks of a surface — under
the deck, inside the lowland, against the plate — which is where routing is actually hard, and the
legality property runs over those as well as over the uniform sample.

### The fly audit, and the whole island in the fixture (2026-08-20)

**The lowland is in the test ground and it routes.** Measured off `islandlow`, solid cells by band:

| | |
|---|---|
| Y24–48 (lowland) | **17,971** — the biggest band in the capture |
| Y190–215 (deck + plate) | 27,088 |
| Y48–190 (belly, taproot, rim) | 18,759 |
| Y215–271 (sky bird) | 7,806 |

`theDeckCanBeRoutedDownToTheLowland` now ASSERTS its endpoints instead of returning when it cannot
find them — a test that skips quietly when its own fixture is wrong reports success and proves
nothing, which is how a suite stops meaning anything.

**And the sampling was measuring the wrong island.** Uniform sampling over a capture that is 2%
solid is mostly a test that empty sky is empty. `nearTerrain` samples within three blocks of a
surface, which is where routing is hard.

#### Every way a flight can end, and what now handles it

| how it goes wrong | what stops it |
|---|---|
| lands on a block, plugin flight ends | `keepAirborne` — never descend inside 1.5 of a floor, climb off one |
| descends into chunks not loaded yet | an unloaded cell below counts as GROUND |
| flies at cruise into unseen terrain | `BLIND_SPEED` 0.12 when the next 8 blocks are unloaded |
| **flies into a wall the route thought was clear** | **`horizontalCollision` forces a repath THIS tick and backs off** |
| **routes through lava or water** | **`Nav.open` refuses anything with a fluid state** |
| corner clipped at speed | waypoint radius and approach taper scale with the speed |
| route stale as the printer builds | repathed twice a second, floored at 5 ticks |
| no route at all | `escape`, then direct with `unstick`, never a partial |
| flight lost while airborne | emergency halt, hands back, disarm |
| on foot over the void | building requires flight; walking is only ever a fetch, with ground |

The two new ones are the ones this audit added:

- **`blocksMotion` is FALSE FOR LAVA.** The router would have flown straight through it, and on this
  island the lowland has water and the court has a tank. Both are cheap to go round, so both are
  simply not passable. The nav fixture had to change with it, or the island tests would be about a
  different island — 811 more solid cells, and `kelp`/`seagrass`/`lily_pad` went with the water they
  stand in.
- **Bumping into something is evidence the route is wrong**, not something to push through. Grinding
  along a face is how a flight slides down a wall onto a ledge, and landing is how flight is lost.
  It re-routes on the tick and pushes back out of the face first, so the next search starts from
  open air rather than from inside the wall.

### The loop's judgements, taken out of the loop (2026-08-20)

`gen/Loop.java`, and `LoopTest` is 24 cases over it. **Every bug in the unattended loop has lived in
four decisions**, and none of them could be tested, because they were written inline in a method
that also opens chests, draws particles and flies a player. The list, in the order they shipped:

- fetching whenever a spot was short of anything, so it went shopping with a full pack and hundreds
  of placeable cells;
- a spot stall that cleared the arrow but not the SPOT, so the hysteresis chose the same region
  straight back and stalled again for as long as you left it;
- a station re-offered after every bin had been tried, keeping the clock that had just abandoned it;
- an empty todo list reported as complete when most of the design was in chunks the client did not
  have, which ended a `follow all` run in about a second.

None of those is a hard problem. All of them are invisible inside a method with a world attached. So
`Loop.phase`, `Loop.sameSpot`, `Loop.station` and `Loop.stalled` are pure functions over plain
values, `Hud` does what they say, and the awkward questions get asked directly:

    itDoesNotGoShoppingWhileItHasWorkInFrontOfIt
    aTripKeepsGoingUntilThePackIsFull
    aDriftingCentroidIsStillTheSameSpot
    aStationThatPlacesNothingMovesInCloserBeforeGivingUp
    outOfViewIsNotFinished
    aWholeSessionOfPhasesTerminates          # all 64 combinations, no silent do-nothing state

The last one is the property that matters for leaving it running: from any starting point the loop
either does something or says why. It cannot sit in a phase with nothing to do and no message.

### What is in a shulker box is not what you are carrying (2026-08-20)

`Work.boxed` reads the `CONTAINER` component of every stack in the pack. It is deliberately **NOT**
added to `carrying`, and the distinction is the whole feature:

- **a boxed block is not placeable** — you would have to set the box down, open it, take the stack
  and break the box again, none of which this mod does. Counted as carried, the loop flies to a spot,
  finds it can place nothing, and stalls there;
- **but it is absolutely a reason not to fly across the island for more.** `Plan.notInAPack` drops
  any shortfall the boxes already cover, and says so once per material rather than silently doing
  nothing.

Half a box is not a solution and is still a trip: you would set it down, take 64, and still be short.

### "It moves like 5 degrees and gets stuck" (2026-08-20)

The collision handler added one round earlier, doing three things wrong at once:

- **`pathTo = null` bypasses the repath floor.** `needsRepath` checks it FIRST, before
  `MIN_REPATH_TICKS`, so it ran a full A* every tick for as long as you were touching the wall —
  the same shape as the one-frame-a-second bug, from a different direction.
- **It RETURNED before the aim.** The yaw never updated while colliding, so it turned one eased
  step — about five degrees — and then froze. That is the whole reported symptom.
- **It backed off along that frozen yaw**, into whatever was behind, and collided again.

Now a bump keeps steering: ease off the forward push to a quarter, climb, and ask for a route
through the normal gate that respects the floor. Only after two seconds of solid contact is the
route declared wrong rather than stale, and only then is it dropped — once.

### THE JUMP KEY IS A FLIGHT TOGGLE, NOT A CLIMB CONTROL (2026-08-20)

Written the other way round for about twenty minutes, and in that time **the mod revoked its own
flight in mid-air** and then reported the fall as though something had been done to it. Jack: *"its
also self revoking flight on accident and saying im in control when im not even touching."*

The reasoning that got there was sound and the conclusion was dangerous. A set y velocity IS damped
by `travelFlying` every tick, so a commanded climb does arrive as a drift; holding JUMP is how a
player climbs. But **vanilla toggles flying on a DOUBLE TAP of jump** — `LocalPlayer.aiStep` opens a
seven-tick window on the first press and flips `abilities.flying` on the second — and driving the key
to climb presses and releases it as the desired vertical crosses a deadzone. Inside seven ticks, that
is a double tap.

The vertical is a velocity again, scaled by `VERTICAL_GAIN` to survive the friction rather than
pressed. `hold` survives for exactly one job: the rescue taps, where toggling flight is the POINT.

Worth keeping anyway, since it cost a javap and is not written down elsewhere: driving
`LocalPlayer.input.keyPresses` does not work at all — `ClientInput.tick()` runs inside the player's
own tick and overwrites it before movement, so anything set from a Fabric tick event is gone before
it is read. `KeyMapping.setDown` is the only mechanism that survives.

**And the message was wrong as well as the behaviour.** "You have control" reads as "you took over",
which is both confusing when the player is not touching anything and, on the occasion it was this
mod's own doing, false. It says *not by you* now.

### Air underneath, and air overhead (2026-08-20)

Jack, watching it work: *"it cant be within 1 block beneath when flying to place because it will auto
stop flying."* Whatever the server's plugin measures, it looks further down than the block you are
touching.

- `Nav.standoff` now REFUSES a standing spot with less than two clear cells under it, keeping such a
  cell only as a last resort and never preferring one.
- `GROUND_CLEAR` 1.5 → **2.5**, so the flight cannot descend below the altitude the standoff was
  chosen for.

It is bought out of the printer's reach budget, which is exactly why the station moves in CLOSER on
its first stall instead of giving up: altitude first, reach second.

**And the same over the head.** *"we bump our head a lot."* `Passable` guarantees the two cells a
player OCCUPIES, which is enough to be somewhere and not enough to work there — because the flight
holds altitude by CLIMBING, so a spot with the ceiling on its head grinds upward into it for as long
as it stands there. `Nav.AIR_ABOVE` requires one clear cell over the head, and `keepAirborne` clamps
every upward push to zero when there is something directly overhead. There are three places that
raise y — the ground clearance, the bump handler and the direct-flight unstick — and one clamp for
all of them, because that is the kind of rule that gets added to two of three.

### Falling is an emergency with two rescues (2026-08-20)

Jack: *"if it detects falling suddenly it needs to automatically start flying (tap space twice) or
just instant type in chat /is"*.

A fall is four things at once: not flying, not on the ground, dropping faster than 0.6 a tick, and
nothing under you. All four, or every trip down to the lowland ends with the loop teleporting you
home.

1. **Double-tap jump.** Costs nothing and re-enters flight — but only when the server still says you
   MAY fly.
2. **`/is`.** Always works, and moves you across the island, so it is the fallback rather than the
   first move, and it is rate-limited to once every ten seconds because it is a teleport.

**Below Y100 it skips straight to `/is`.** The plate is Y201 and the deck Y190–199, so above that
line a fall has island under it and the taps have both time to work and something to land on. Below
it you are under the belly and what is beneath you is the void: the taps cost a third of a second
and buy nothing there, because if flight were available you would not be falling. The lowland floor
at Y24–47 is under the line too — landing on it is survivable and being teleported home from above
it is merely inconvenient, while the fall that MISSES it is the one that is not.

It is checked before everything else in the tick, including having a destination: the whole point is
that it fires when the loop is not in control of what is happening.

### `/cscan why`

The answer to "it got stuck", without a round trip through a description. Design, counts, how many
cells have something to build against RIGHT NOW, the materials and what you carry of each, whether
the Litematica placement is loaded and enabled, the phase, the spot, the arrow, the session report,
and then everything the autopilot knows: flying or not, on the ground or not, speed, bumping, the
route length or that there is none, and the distance to the target.

The loop computes all of this every two seconds and says almost none of it, because a loop that
narrates itself continuously is one nobody reads. Asked, it answers completely.

### Three clocks, and why one number cannot serve them (2026-08-20)

Jack, in two instructions: *"if nothing is placed in 5 seconds, move on immediately"* and *"if it
says it needs to reroute and doesnt move or doesnt perform action within 3 seconds, move to next
cluster"*. They are different questions and they now have different clocks:

| clock | asks | fires after |
|---|---|---|
| `NOWHERE_MS` | am I actually travelling? | **3s** of no movement AND no placement, while en route |
| `STATION_MS` | is the printer taking anything from where I stand? | **5s**, and only once ARRIVED |
| `STALL_MS` | is this loop doing anything at all? | 90s |

They must stay in that order or the slow one fires first and the fast one never does;
`theThreeClocksAreOrderedByWhatTheyAskAbout` asserts it.

**Five seconds is only safe because the station clock starts on ARRIVAL.** Timed from when the
station is chosen — which is what it did — anything more than a few seconds' flight away would be
abandoned before the printer ever had a chance at it, and the loop would tour bins placing nothing:
exactly the failure the clock exists to catch, caused by the clock.

**And the travel watchdog is sampled every TICK, not every recount.** The recount is every two
seconds, and a three-second watchdog read at two-second intervals cannot tell three seconds from
five.

Standing still is only wrong while TRAVELLING: at the work you hover while the printer takes blocks
off you, and at a chest you stand while the withdrawal runs. Both are the loop doing its job, which
is why the test is movement AND placement AND having somewhere else to be.

**Giving up on a spot has to make the next choice different.** The first version cleared the arrow
and let the next recount choose — which picked the same region, because it was still the best one,
flew at the same wall and stuck again. The spot is now passed over for a minute, and the route is
dropped with it (`Autopilot.forget`), because a route is computed from a destination and keeping it
after the destination is abandoned is keeping a plan to fly at the thing that just stuck. If
everything left is near the spot that failed, it takes it anyway: a hard spot beats idling until the
avoid expires.

### Shulkers, on both sides of the wall (2026-08-20)

*"make sure it detects shulkers also."* Audited every list on both sides that decides whether
something is a container, and the ones that exist were already right — `Storage.CONTAINERS` and
`STORES` match `shulker_box` by substring so `white_shulker_box` counts, `protect.MECHANISM` and
`protect.USED` cover it, and the shipped `chunkscan_rules.json` carries it. A placed shulker box has
never been at risk of being built over.

**The gap was the one that is not in any of those lists: a shulker box inside a chest.** The index
records what the container screen holds, so a chest of six boxes was filed as *"6x
white_shulker_box"* — true, and useless. The ten thousand blocks inside were invisible to `find`, to
the bill of materials and to the build loop, which would fly past them to a chest with sixty-four
loose ones. **Bulk storage on this island IS boxes in chests.**

- `ContainerWatcher` now reads the `CONTAINER` component of every stack it indexes, into a separate
  `inBoxes` map on the record.
- **Kept apart from `items`, deliberately.** Getting at a boxed block is a DIFFERENT job — take the
  box, set it down, open it — and a plan that says "500 bricks, 22m NE" when it means "a box you must
  unpack" has lied about the only number that mattered. `findExact` takes a flag; the plan passes it,
  a bare lookup does not.
- `Withdraw` will take a BOX that holds what it came for, and `carrying` counts boxed ones toward
  the target — without that it keeps taking boxes for ever. `Work.boxed` then tells you to set it
  down, because a client mod cannot unpack one for you.
- `/cscan find` falls back to searching inside boxes when nothing loose matches, and always says how
  many of a hit are boxed.

`inBoxes` is absent from every record written before today, which reads correctly as "no boxes known
here" — the entry is rewritten from the screen the next time you open that container.

### "Climbing over it" is one instinct applied to five situations (2026-08-20)

Jack: *"need better solution than only climbing over it when often climbing up is the problem in the
first place."* Right, and the ceiling rule one section up is the proof — the bump handler climbed
into the thing that was already on its head, and kept climbing.

**A bump now asks the geometry instead of guessing.** `Nav.escape` already knows how to answer this:
flood outward from where you stand and take the reachable cell that gets CLOSEST to the goal,
whichever direction that turns out to be. It runs at a short radius (10) and on a timer
(`BUMP_LOOK_EVERY`), because a flood on every tick of contact is the cost this file has paid twice
already. When it finds something, the loop flies that instead, easing round the corner at 40% speed.

**And when there is no way round at all, `sidestep` SCORES every direction by whether it actually
helps** — the dot of each open way against the heading, with a thumb on the scale for sliding.

It was a fixed ladder first (sideways, up, down, back) and that was the same mistake one level down:
`down` sat at the bottom, so it was only ever taken when climbing was BLOCKED. On this island most of
the work is below you — the lowland, the belly, half the deck — so every bump on the way there went
the wrong way over the obstacle. Scored, a downhill heading escapes downwards, an uphill one climbs,
and a level one slides, which is what the bias is for: a perpendicular scores zero against a level
aim whichever way it points.

**And the descent may use SHIFT.** Only JUMP toggles flight — that is what revoked Jack's flight in
mid-air — so sneak is safe, stronger than a y velocity `travelFlying` is busy damping, and is what a
player does. The movement path is handed a `sink` that can only touch shift, so it CANNOT press the
other one.

**Found while doing it: the bumped-step handling had been silently deleted.** An earlier edit in this
session replaced the whole flying-step block to add the vertical gain and took the collision slowdown
with it, so for several commits a bump did not slow the flight at all. That is the second silent
no-op edit today; the patch scripts now hard-fail on a missing anchor instead of quietly changing
nothing.

### `/cscan off` was not a command, and `stop` was not a stop (2026-08-20)

Two faults behind one report.

**`off` did not exist.** The only spelling was `stop`, so `/cscan off` failed as an unknown command —
which looks exactly like a stop that did not work, and `off` is the word that gets typed. Both run
`stopAll` now, and `MenuTest` asserts they run the SAME thing: two commands that stop different
amounts is worse than one command.

**And `stop` left four things running:**

- **Six highlight layers kept drawing.** It cleared `goto`, `next` and `scaffold` — the three the
  build loop uses — and left `find`, `check`, `dig`, `dark`, `mark` and `marks`. A panic button that
  leaves the screen covered in particles reads as one that did nothing. `Highlight.clear()` with no
  argument was there the whole time.
- **`Hud.off()` kept `followAll`**, so a later `/cscan follow <one design>` silently became "follow
  all of them".
- **...and the spot, the abandoned stations and the avoid list**, inherited by a run that has nothing
  to do with them.
- **Auto-scan carried on**, writing a capture per tick into an archive this file already notes is
  unbounded.

Half a stop is the kind that is discovered an hour later.

### Getting flight back, when it is merely absent (2026-08-20)

Jack: *"it needs to also activate fly again if its purely not moving because its not in fly anymore
because it bumped into something etc."*

The walk gate — building requires flight, walking is only ever a fetch — stops the loop doing
anything DANGEROUS without flight, and stopping there is only the right answer if nothing can be done
about it. Usually something can: **the same double tap that rescues a fall turns flight back on while
standing on a floor.** From the ground the first tap is a jump and the second lands while airborne,
which is exactly the gesture a player makes.

Tried whenever the loop has somewhere to be, is not flying, and the server still says it MAY fly.
Three guards, each of which is the difference between a fix and a nuisance:

- **`mayfly` false and it does not try at all** — tapping will not change the server's mind — and it
  says so once rather than every two seconds.
- **Four attempts, then it stops.** A tap that has not worked will not work the fortieth time, and a
  player watching their character hop twice a second is watching a bug.
- **A minute between attempts**, for the same reason.

### Threading a one-wide gap (2026-08-20)

Jack: *"we also need to do better at being able to locate areas we can fly through e.g. 1x open
spaces we can fly up through if we align correctly, it gets stuck quite a lot still."*

**The routes through those are already found.** `Nav` models a body 0.8 wide and a one-wide shaft
passes it; `NavTest` has had `aVerticalShaftIsFlyable` and the highway cases since the tunnel work.
The island is full of them — the taproot, the workshop necks, the well — and what fails is not the
finding, it is the FLYING: steering at a waypoint centre from off to one side arrives at the mouth
still carrying that lateral drift, catches the lip, and bumps. Then the bump handler goes round
something it was already lined up with.

**So it lines up first.** When the way ahead is walled on both sides of an axis, that lane is
CENTRED before any progress is made along the passage — and no progress at all until it is, because
creeping forward while still off to one side is exactly how you catch the lip you were threading. It
is what a player does without thinking.

- Measured at the TARGET, not at the player: the point is to be lined up before arriving.
- Only the WALLED lanes are corrected. Centring the open one would drag the flight to the middle of
  every corridor it passes down, which is not alignment, it is a detour.
- The correction is capped by the error and by the speed, or overshooting the middle of a one-wide
  shaft puts you against the far wall — the same bump from the other side.
- And a gap you have to be lined up for is flown at `TIGHT_SPEED`, because the alternative is
  arriving correctly aligned and too fast to stay that way.

### The bumping was structural, and the heuristics were standing in for it (2026-08-21)

*"still lots of bumping, and turning off fly by touching blocks, we really need to fix this."*
Everything added over the previous rounds — climb over it, slide round it, get flight back, tap it on
again — is a response to CONTACT. None of it asks why the flight is touching blocks at all. Two
reasons, both structural.

#### 1. It flew a leg nobody had checked

`clear` validates waypoint-to-WAYPOINT. What actually gets flown is *wherever-I-am* to waypoint, and
the moment drift, a bump or a corner puts the body off that line, the leg being flown is a CHORD
across whatever the route was going round. The route was fine; the flight was not on it.

`pursue` is plain pure pursuit: steer at the nearest point on the validated segment, a block and a
half ahead. On the line it changes nothing; off it, it pulls back on. **A route is a set of
corridors, not a set of points.**

#### 2. A* minimises distance, so every route skims

The cheapest path runs along the surface it is passing. Fine for a pathfinder, wrong for a server
where flight is a plugin grant and **touching a block ends it**. `Nav.roomy` requires a clear cell on
all six sides, and the route is searched in that world FIRST.

**Measured on the island, it failed more than half the time — and the reason was the ends, not the
middle.** 14 of 32 routes near terrain had a fully roomy answer; the other 18 were not threading
tunnels, they were LEAVING one surface and arriving at another, because every endpoint this loop uses
is a standing spot beside the work or a chest in a wall. So `roomyBetween` drops the clearance rule
within `ENDS` (6) of either end and keeps it for the long middle, which is where a flight spends its
speed. The island test asserts three quarters of them now keep their distance where it matters.

#### And the arrival precision was being bought with contact

Jack: *"the focus should be getting within a 3 block radius of the point since we know we reach+place
further."* Right, and it is the same lesson a third time. `ARRIVED` had been tightened 3.0 → 1.5 to
protect the printer's reach budget — so the last two blocks of every approach were threaded, slowly,
between whatever the standing spot was beside, with the alignment fighting the drift. **Every one of
those is a chance to touch a block and lose flight, spent buying a precision the printer does not
need.**

What pays for it: `Plan.reach()` asks litematica-printer for `Configs.PRINTING_RANGE` instead of
assuming four blocks. That is the same "ask the game, not your memory" rule this project applies to
every block property — and then never applied to the mod it is driving.

### Half speed everywhere, and the aim is not the waypoint (2026-08-21)

*"why does it fly very slowly when going towards a location, its like its going half speed."* An hour
old, and caused by the pure-pursuit fix in the section above.

`pursue` returns a point **`LOOKAHEAD` blocks ahead by construction** — that is the entire idea. The
approach taper was still measuring against `aim`, so on every tick of a two-hundred-block flight it
was told there were 1.5 blocks to go, and held the whole journey at `max(0.06, 1.5/12)` = **0.125
against a cruise of 0.75**. The bend check read off the same point and saw a permanent corner on top
of that.

**The waypoint is the thing being approached; the aim is only where to point.** Two different
questions that had been one variable, and merging them was invisible the moment the aim stopped being
the waypoint.

`cruiseSpeed` is pure now, and takes both distances separately — the destination's for the final
slow-down, the waypoint's for the corner.

**And there was a second half to it, which is why the first fix did not settle it.** The taper was
applied to EVERY waypoint, not just the last. A route through cluttered terrain is made of dozens of
them — on the deck they land about four blocks apart — so `toWaypoint` was never more than four, the
taper fired on every tick, and the flight ran at `4/12` = **0.33 against a cruise of 0.75**. Exactly
half speed, which is what it looked like.

A corner does not need slowing down for its own sake: `bend` already handles TURNING, which is about
the angle rather than the distance. Flying past an intermediate waypoint quickly is not overshooting
anything. **Only the last waypoint is a place to stop.**

**And the HUD was showing the DIAL.** Two separate taper bugs held the flight at a third of its speed
across hours of testing, and either would have been a glance to spot if the readout had said what was
actually being flown. It shows `@0.33/0.75 arriving` now — applied, dial, and which clamp is doing
it: `corner`, `arriving`, `threading`, `chunks not loaded`.

### Three blocks is a ceiling, not a target (2026-08-21)

Jack, immediately after asking for the three-block rule: *"if we always are 3 blocks its hard to
reach all blocks since we lose 3 blocks to air"* — and then the other half of it — *"this needs to
balance against safe landing and stopping fly, we need to be smart about this when its possible, and
when we should just be floating a bit closer."*

Both are right and they pull opposite ways. Three blocks of standoff is three blocks off the FAR
CORNER of the bin as well, and the printer's reach has to cover both; but closing the gap by pressing
up to a surface buys that reach with contact, and on this server contact ends the flight. **A flight
is worth more than the block it was reaching for.**

So neither number is decided in advance:

- it keeps closing until it **physically cannot** — `bestDist` and `sinceCloser` measure whether the
  approach is still making progress, which is what *"the actual space after stopping"* means. A
  flight wedged against a shelf 2.4 blocks from the work has arrived; waiting for 1.2 there is
  waiting for ever;
- it stops a block short of anything it is approaching (`SAFE_GAP`), at the feet AND the head,
  because an approach that clears one and not the other is the head-bumping by another name;
- and `ARRIVE_MIN` (1.2) is where it ends up in open air, because past that nothing is gained.

In open air it floats right up to the work. Against a wall it stops where the wall says. The
difference between those is measured rather than guessed, which is the whole of it.

### The fall safety outlives the autopilot (2026-08-21)

Jack, after it happened twice: *"if we turn off auto fly because of w/e, we still need to for the
next 30 seconds have active /is auto usage or auto fly to save falling in case its a momentum
mistake."*

**Switching off is the most dangerous moment, not the safest.** Whatever the reason — the emergency
disarm, a `/cscan stop`, flight revoked in mid-air — the body keeps whatever velocity it had, and the
one thing that was watching for a fall has just stopped.

The rescue is the part with no business being tied to whether the loop is driving. It does not steer,
it does not build; it notices a fall and does something about it. So it now runs for
{@code GUARD_MS} = 30s after autofly goes off, and the tests pin BOTH halves: that it still runs, and
that it steers nothing while it does.

Thirty seconds covers the arc of any fall this island can produce, and is short enough that it is not
quietly on for ever — which would make it a mode rather than a safety. `/cscan why` and the
mid-air-revocation message both say how long is left.

### Neither close enough nor safely far: fixing both at the source (2026-08-21)

*"still its either not getting close enough, or getting too close when adjusting and then stopping
flight."* Two halves, two different causes, both in how the standing spot was chosen and held.

#### Too close: it kept adjusting

The station re-aimed every time a few blocks went in — which sounded like a feature ("walks you round
the work") and is a fresh APPROACH every couple of seconds, each one a chance to nudge a wall and
lose flight. The question was being asked wrongly: not *is the aim still ideal* but **can the printer
still reach what is left**. While it can, holding still beats improving, and now it holds.

#### Not close enough: the standing spot was chosen for the wrong quantity

It was picked by proximity to the bin's centroid — and then the flight parked short of it, so the
number deciding everything was a distance to a point nobody cared about. Worse, `STANDOFF` was 3 in
CHEBYSHEV, which is 5.2 as the crow flies, and a bin's far corner is already 3.5 from its middle.

`Plan.bestStand` scores every open cell near the work by **how many of the remaining cells the
printer could touch from it**, discounted by how far short the flight is expected to park. Ties go to
the nearest, because two spots that build the same wall are the same spot.

**Clearance is a filter, not a term in the score.** A spot that touches something is not a worse
spot, it is not a spot at all — on this server it ends the flight. `AIR_BELOW`, `AIR_ABOVE` and
`SAFE_GAP` are what keep the approach safe now, rather than standing further back and hoping, which
is what let `STANDOFF` come down from 3 to 2.

### Arrive, and then stay a moment (2026-08-21)

Jack: *"when we reach an area we dont instantly run away if we are placing blocks, we should reach an
area, stay for a few seconds, then move on unless something e.g. blocked."*

The bin is re-chosen on every recount, and the fullest one changes as cells elsewhere become
placeable — so a station could be abandoned two seconds after arriving, before the printer had taken
a single block, in favour of somewhere that merely looked better. **All of the flying, none of the
building.**

`DWELL_MS` (4s) holds the spot from the moment it is actually REACHED, not from the moment it is
chosen — the flight there can take longer than the dwell. `Plan.stationOf` is what makes that
expressible: it answers *"what about the bin I am standing in"*, where `Plan.station` only ever
answered *"where is the best work"*. Staying put must not mean re-deciding every two seconds that
staying put is still best.

**Just under `STATION_MS` on purpose.** The dwell holds the spot; if nothing has been placed by the
time the stall fires, the stall is what moves it on. A dwell longer than the stall would be a loop
that cannot leave somewhere it cannot build — which is the failure this whole layer exists to avoid.
And an empty bin is not a station, so the dwell ends honestly when there is nothing left to build
rather than running out a clock.

There are now four clocks and they compose in one order, each shorter than the one it can interrupt:

    3s   going nowhere      told to travel and not travelling
    4s   dwell              having arrived, stay and let the printer work
    5s   station stall      arrived, dwelt, and nothing was placed
    90s  session stall      the whole loop has done nothing

### Two mechanisms fighting: the shaft loop (2026-08-21)

Jack: *"stuck in a loop of going up a 1x hole hitting a bump and needing to find a way around and
repeating."*

Both halves were working correctly, which is what made it a loop:

1. the route picks the one-wide shaft, because it is the way through;
2. the flight clips the lip on the way in and bumps;
3. the bump handler looks for a way ROUND — and a way round a shaft is the way back OUT of it;
4. it flies out, re-routes, correctly picks the shaft again, and repeats.

**A bump inside a gap you are threading is not an obstacle, it is a nudge.** While threading, contact
now means line up better and creep — the escape search is not consulted at all. Only after
`WEDGED_TICKS` of that has plainly failed is the passage itself treated as the problem.

Two supporting changes:

- **The tightness is read from the next WAYPOINT as well as the aim.** Aligning only once the aim is
  inside the gap is aligning after the first contact with it, which is too late by definition.
- **`Hud.abandonSpot`.** Threaded, aligned, crept and still nowhere: the shaft stops being the
  problem to solve and the spot beyond it is not worth this. The FLIGHT is the only thing that knows
  a way is not flyable, and the LOOP owns where to work — so the flight asks rather than decides, and
  the spot is passed over for a minute exactly as the three-second watchdog does it.

The general shape is worth keeping: when two correct mechanisms produce a loop, the fix is almost
never to make one of them cleverer. It is to notice that they are answering the same question and
decide which one owns it.

### The navigation audit (2026-08-21)

Read `Autopilot.tick` and `Nav` end to end after a day of patches. Four defects, and three of them
were **invisible in the code and only visible in the arithmetic between constants** — which is what
an audit is for.

- **The approach tracker belonged to the ROUTE, not the target.** `bestDist` and `sinceCloser` were
  reset when `pathTo` changed, and the route is often null at exactly the moment the destination
  changes — a fetch ending, a station moving. So the tracker carried over from the last place: the
  new target looked like something that had already stopped getting nearer, `sinceCloser` ran up, and
  it "arrived" at the ceiling instead of closing in. **The third distinct cause of "not getting close
  enough".**
- **`wedged` accumulated only by accident.** It incremented inside `if (threading && bumps <
  WEDGED_TICKS)`, and `bumps` is reset every `STUCK_TICKS` — so it counted at all only because
  STUCK_TICKS (40) happens to be smaller than WEDGED_TICKS (60). Raise that one constant and the
  give-up would silently never fire again. It is counted in its own right now.
- **Staging could not run at the distances this island uses.** `for (stage = STAGE; stage >= 16 &&
  stage < d; stage /= 2)` does not execute at all when `d` is shorter than STAGE: the condition fails
  on the first evaluation and never reaches 64 or 32. Staging exists for searches that FAIL, and it
  was unavailable for every distance between 16 and 128 — which is where this island's routes live.
- **Arriving did not clear the contact state**, so the next leg began with a bump count inherited
  from the last one and gave up early.

The pattern in three of the four: a constant's value silently deciding whether another mechanism runs
at all. None of them would have failed a code review; all of them are arithmetic.

### The recovery ladder: what to do when it is genuinely impossible (2026-08-21)

Jack: *"theres going to be times where its literally impossible to reach and it causes an infinite
loop, e.g. if its in the center of many layers because we built the wrong way in."*

Every stuck loop before this was fixed by understanding ONE situation — the shaft, the ceiling, the
unloaded chunk, the wall the route thought was clear. **That approach has a floor under it.** There
will always be a situation nobody thought of, and no amount of cleverness about flying reaches a cell
in the middle of a solid mass. So the last resort is not another special case; it is a ladder, and
the only thing it knows is how long things have been going badly.

    5s    BACK_OFF     fly to a breadcrumb — somewhere we were definitely open
    10s   CLIMB_OUT    abandon the destination, rise into open sky
    20s   GO_HOME      /is

`Recovery.stageFor` is pure and `RecoveryTest` argues with the order rather than the behaviour. Three
things about it are load-bearing:

- **Trouble is defined by MOVEMENT, not by cause.** The specific handlers upstream have already had
  their turn; if the flight is still not covering ground after all of them, the reason has stopped
  mattering. A flight that is moving is fine whatever else is true of it.
- **Each rung gets long enough to work** before the next interrupts it. Backing off and climbing out
  are several seconds of flying each.
- **SEALED is a shortcut, not a rung.** `Nav.pocket` counts reachable cells up to a cap: fewer than
  60 and you are in a hole rather than a room. Backing off, climbing and going round are all about
  getting somewhere else IN THIS WORLD, and when you have been built into something there is nowhere
  else to get to — so it goes straight to `/is`.

**The boundary matters as much as the detection.** The loop works indoors — the store hall is nine by
nine — and a recovery that teleported you home every time you flew into a building would be worse
than no recovery. `aROOMIsNotAPocket` pins it, and the first version of the sealed test WAS a room,
which is how the threshold got chosen honestly.

#### And the slow version of the same loop

No watchdog catches this one, because every individual decision in it is correct: abandon spot A,
take B, abandon B, take A again once its minute expires, for ever. `Loop.thrashing` looks at the PAIR
— several spots given up on, and NOTHING placed while it happened. Either alone is normal; a design
has awkward corners and a slow printer is still a printer.

Four abandonments with nothing built and the design is not buildable from here right now: it moves to
the next design under `follow all`, or stops and says which commands would explain why. **A loop that
runs all night achieving nothing is worse than one that stops at 2am and says so.**

### Two strikes and a place is ignored (2026-08-21)

Jack: *"it shouldnt spam no route and no way around, if it does it twice, just find a new location,
it should notice if an area gets flagged twice it gets flagged as an ignore (red)."*

**The spam and the infinite loop are one fault seen from two angles.** Every watchdog in this loop is
a TIMER — the spot avoid expires after a minute, the station retries clear when every bin has been
tried, a chest's cooling-off lapses — and a timer forgets, which is right for a world that changes and
wrong for a place that has beaten the router twice. Returning there for ever is what produced both
the repeated message and the cycle.

- **One failure is a bad moment**: a chunk that had not arrived, a block the printer had just placed,
  a route computed from the wrong side of a wall. Writing a place off for that shrinks the island for
  no reason.
- **Two is a property of the place.** It goes on the list, is drawn RED, and is never chosen again
  this session — not avoided for a minute, not retried when the list is cleared, not on the table.
- **Announced exactly once**, because `strike` returns true only on the strike that writes it off.

**Held by AREA, not by coordinate.** The loop aims at a centroid that drifts as cells are placed, so a
per-cell list would never see the same failure twice — it would collect near-misses for ever and
ignore nothing. Eight blocks is about the size of a spot the flight can fail to reach for one reason.

**Session-scoped, and deliberately not written to disk.** Breaking one block can change the answer,
and a file would quietly shrink the buildable island over weeks with nothing to say why.
`/cscan ignore` lists and re-draws them, `/cscan ignore clear` puts them back on the table, and
`/cscan why` says how many there are — because a loop that silently stops trying somewhere is a loop
you cannot argue with.

Both the flight and the loop feed the same list: a route that cannot be found and a spot that has been
given up on are the same evidence about the same place.

