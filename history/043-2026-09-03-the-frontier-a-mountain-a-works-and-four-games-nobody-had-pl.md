## The Frontier: a mountain, a works, and four games nobody had placed (2026-09-03)

Jack: *"frontier in its current design is useless outside of the rollercoaster, lets think about
this area differently and figure out what we can build that supports the coaster, and is
interesting + visual."* Then: *"do all"*.

### The measurement, before anything was drawn

Flooded over the shipped `out/Park Complete.litematic`, the Frontier band (U0-169, 200 x 170 =
34,000 columns):

| | |
|---|---|
| bare lawn | **66%** - 22,322 columns, and the largest free-lawn rectangle in the land was 8 x 18 |
| interactive inventory, WHOLE LAND | **646 rails, 2 buttons, 2 bells, 2 detector rails** |
| ...dispensers, hoppers, droppers, targets, note blocks, levers, plates, comparators | **zero** |
| ...redstone wire | **zero** |
| columns over 20 courses | 3.8%; exactly two things broke 25 - the Vantage Lookout at 44 and the ride at 42 |

**EVERY VERB IN THE LAND BELONGED TO THE COASTER.** Six modules stood around it and not one was
a thing a guest does; `frontier_builds._porch_lot`'s own docstring says the land's only declared
dwell activity ships as two empty shells. And `tools/look.py --sheet panel` on the ride says the
rest: **its PLAN IS A RECTANGLE** - a timber trestle perimeter round a terraced grey mass with
vertical faces, 10,657 cells of `cracked_stone_bricks`, which is a BRICK. You cannot name it from
the silhouette. The land's own spec promises *"a living gold-rush mining town against a worked-out
mountain"* and **the mountain was never built.**

### THREE GAMES WERE BUILT FOR THIS LAND AND NOBODY HAD PLACED THEM

`out/PF Game Pan Line`, `PF Game Powder Striker` and `PF Game Prize Office` were on disk,
generated, contract-asserted by simulation - and absent from `Park Complete`'s `contains` list.
**And `park_games` was not in `gen/GENERATORS` at all**, so not one of the ten `configs/pf_game_*`
could be regenerated: `mcbuild gen` answered *"unknown generator park_games"* while the module,
its 400-line test file and ten configs all sat in the tree. A generator nobody can reach is
indistinguishable from one nobody wrote, and a design that is built and unplaced is worse - it
looks like work that was done.

### What was built

| design | blocks | what it is |
|---|---|---|
| `PF Mine Ridge` | 32,255 | the mountain the coaster is cut into, and a walk-through adit through its foot |
| `PF Mine Works` | 5,168 | the ore line, a stamp mill a guest FIRES, and the dock the ore leaves by |
| `PF Game The Riffle` | 130 | the Prospecting Porch's second bay, finally given a mechanism |
| + placed | | the three frontier games that were already built |

    interactive inventory   4 -> 971 blocks, and it now contains redstone
                            55 wire, 7 comparators, 5 repeaters, 4 pistons, 14 lamps,
                            1 target, 1 weighted plate, 7 bells, 4 buttons, 98 sources
    columns over 20         3.8% -> 6.6%      tallest thing 44 -> 52
    columns over 3          33.3% -> 39.7%

### THE RIDGE IS THE COMPLEMENT OF THE RIDE, NOT A REPLACEMENT FOR IT

`gen/mineridge.py` LOADS the coaster's own artifact and refuses every cell of it, so `overlap 0`
is a property of the construction rather than a number to hope for. Three parts:

- **TALUS** whose reach and height are both functions of the FACE above them - a forty-course wall
  throws scree fifteen cells and a six-course one throws it three - so the finished outline is
  irregular by construction rather than by noise. A max-first flood carrying each source's own
  slope gives every cell the maximum over all sources at a fraction of an all-pairs scan.
- **A CREST** on the east and south strips, which is where the room is: a capped distance
  transform over the ride's footprint says the notch inside its plan reaches at most 7 cells of
  clearance and mostly 1-6, while V101-123 (behind the lift hill) and the south strip run 7-12.
  The lift hill climbs INTO the mountain's face, which is what a mine coaster is.
- **AN ADIT** - two framed portals on one face, timber sets every third cell, rail underfoot, an
  ore chamber with a gold face and a fenced winze.

**THERE IS NO UNDERGROUND ON THIS ISLAND TO DIG INTO.** Measured: world Y202 is the lawn and all
34,000 columns of it, and Y190-201 hold between 12 and 175 cells in the whole Frontier - the park
is a one-block plate over void. A shaft is not available. An ADIT into a hillside is what a
gold-rush mine on a hill actually is, and it is the one that can be built here.

#### Six things the ridge cost, each of which shipped a clean-looking build

- **CONES ARE THE WRONG PRIMITIVE.** Three point sources with a `(1-d)**1.6` falloff came out as
  three sharp spires - a tent is what that exponent draws - and the terracing then wrapped each in
  concentric contour rings, so the mass read as a stack of grey wedding cakes. A crag is a LINE
  with a shoulder: distance to a SEGMENT, and a near-linear falloff off it. Pushed the other way
  (an exponent well below one) it becomes a mesa, and a terraced mesa is a ziggurat - which was
  the second build.
- **TERRACING APPLIED EVERYWHERE BUILDS A ZIGGURAT.** A cone is uniformly steep so every column
  snapped. The threshold is 2.0 courses per cell - genuinely unclimbable rather than merely
  sloping - the foot is exempt, and the bench height carries a coarse jitter so a shelf wanders
  instead of drawing a contour line.
- **THE VALUE LADDER IS MEASURED ACROSS FAMILIES, NEVER INSIDE ONE**, and this file got it wrong
  first. Measured with `blocks.color(..., "side")`: stone 126, andesite 136, cobblestone 127,
  gravel 128 - **four materials inside ten points of luminance**, below the ~15 at which a tone
  stops being a tone. A mass of those four is one grey whatever the mix, which is the same mistake
  three separate CLAUDE.md notes already record about stone brick and blackstone. Across families
  the rungs are real - `cobbled_deepslate` 77, `moss_block` 101, `tuff` 108, `granite` 112,
  `stone` 126, `diorite` 188 - so the mass is BEDDED rather than speckled, in a six-course cycle
  with MID between every accent. **And the beds REPEAT**: one ladder spread over fifty courses put
  every accent in the bottom third where nothing could see it.
- **THE CRAG GREW THROUGH THE RIDE, and refusing the ride's own cells did not stop it.** A column
  one cell off the track took the crest's full height, so the first build swallowed the coaster
  whole - the mass was there and the thing it exists to support was invisible from three bearings
  out of four. `stand_off` holds the crest down near the ride and lets it reach full height only
  seven cells clear, which leaves a moat the track reads against. The TALUS is deliberately not
  capped: hugging the ride is its entire job.
- **GROUND THAT BELONGS TO SOMEBODY ELSE.** 271 columns of the lot carry `PF Front Frontier`'s
  own work - the coaster's 7 x 30 switchback queue, the Ridge Water Tower, the Ore Road and the
  Trail Ore Cart, all in the south band. **A mountain deferring round a switchback queue is a
  mountain with a rectangular bite out of it**, so those boxes are kept OUT rather than deferred.
- **GRAVEL IS A CRUST MATERIAL** (rule 13). It is the top course of a column that is solid to the
  ground and never a face, so a falling block never has air under it.

And three inside the adit, all invisible to everything but a walk:

- **A TUNNEL IS A VOID WITH ROCK ON TOP, AND THE ROCK HAS TO BE PUT THERE FIRST.** Carved out of
  whatever the talus happened to give, a gallery under a thin part of the apron is an open trench
  with two walls - which audits clean and renders as a tunnel from the one bearing that looks down
  it. The cover is forced into the height field before a single cell is filled.
- **A SET'S POST MAY NOT STAND IN THE GALLERY.** Where the cross-cut meets the corridor its own
  posts land in the lane that feeds it - the same cell is a wall to one lane and a walkway to the
  other - so a leg placed blind bricks up the junction. Nothing in an audit, a BOM or a render can
  see it; the only symptom is a guest who cannot get through.
- **A PORTAL BURIED IN ITS OWN TALUS IS NOT A PORTAL.** The mass is filled before the gallery is
  cut, so without an approach cleared in front of each mouth the scree stands against it - and the
  name board is REFUSED for having no empty cell to hang in, which is how one of the two shipped
  unsigned and the other did not.

**THE DESIGN ALONE IS IN SIX PIECES AND THAT IS CORRECT.** The ride is a hole in it, so a talus
that wraps a ride is disconnected in isolation and one 62,138-cell piece in the composite - the
Lowland Stair's own situation, and the composite is the truth.

### The stamp mill: THE MACHINE LATCHED, TWICE, FROM TWO DIFFERENT CAUSES

`gen/mineworks.py` builds an ore line, a three-step mill and a dock. The mill's stamp battery is
the second thing in the Frontier a guest can operate, and its contract is asserted by
`tests/test_mineworks.py` through `mcbuild.circuit`. It failed three times before it worked, and
**on all three occasions the design audited clean, rendered identically and reported a correct
BOM**:

- **It did nothing at all.** The boost sat two cells past the pulse's output and the drive line
  began past the end of the bay - the run was broken in two places.
- **It latched ON while the button was held** because the drive line's first repeater stood on the
  climb's own DUST, which is not a placement the game allows; the model resolved it by feeding the
  staircase backwards, and the levels rose from 9 at the comparator to 14 at the top.
- **It latched again** because the pulse's own delay leg ends one cell off the comparator's output,
  and the step-across into the climb was laid level with it - so fifteen went straight round the
  gate. **Every module in the chain was individually correct**, which is this file's own rule
  about composing verified modules, met a third time.

A machine that runs for as long as somebody leans on it is the mill's version of a house paying
while a player holds a slot button. `test_A_HELD_BUTTON_GIVES_ONE_STROKE_AND_THE_BATTERY_RESETS`
is deliberately tight - *off within twenty ticks while still HELD* - because a bound looser than
the bug is what let `circuits.pulse` ship as a repeater, and this repo has written that down once
already.

Four more things the works cost:

- **THE ORE LINE'S POWER SOURCES ARE A HAZARD TO ANY CIRCUIT NEAR THEM.** A `redstone_block` every
  eight cells keeps its powered rail alive, and at V160 those ran four cells from the battery's own
  climb. Moved to V165, the nearest source is five cells from the nearest dust - out of reach.
- **A POWERED RAIL CANNOT CURVE**, off the registry rather than off memory, so every corner is
  plain `rail`. On this server gold is farmable and iron is not, so the powered rail is the CHEAP
  one and the plain rail is the expensive one - the reverse of the obvious reading.
- **INSIDE THE MILL THE BUILDING CARRIES THE LINE.** The handrail run down the mill's interior
  overwrote two courses of the battery's climb. The line is generated FIRST so that where the two
  want one cell, the thing with a circuit in it wins.
- **AN AWNING BELONGS TO A STEP, NOT TO A BUILDING** - run at one height across all three it had
  no wall behind it over two of them and shipped as floating wool. And `wool` has no slab in the
  game, which the state audit caught as thirty-three illegal blocks.

### Still open, stated rather than left

- **Nothing has been looked at in game.** All of it is `render3d`, which draws with the same
  colour DB the palette picker optimises against - judge form and mass here, judge palette in
  world. The composite reads as a mining town under a worked mountain from every bearing.
- **The ridge is 32,255 blocks**, which is large against `PARK_VISUAL_AND_BUDGET_SPEC`'s
  36-44k for the coaster INCLUDING its terrain. It is the land's defining feature and 94% of it
  is `cheap` tier; the trade is stated rather than hidden.
- **`verify_against: out/Park Complete.litematic` is now self-referential for these two designs**,
  because the shipped composite contains them. `park_place` rebuilds the merge from the artifacts
  every run so it is self-correcting, but a re-verify reports the delta against the LAST ship
  rather than against a clean world.
- **The gold sluice bay itself still has no mechanism INSIDE it, and both halves of that are a
  measurement.** Its standable-and-clear columns are a ring one to two cells wide round the
  settling pool, with no rectangle in it bigger than 15 x 1 - a console needs a footprint the room
  does not have. And the veranda is not uniformly clear either: `_porch_run` stands a colonnade
  every third cell and rails its outer edge, so the first six sites tried refused between 26 and
  110 cells. **A console missing forty-two cells is a machine that does nothing while auditing
  clean**, which is `test_park_games`' own rule and which caught this before it shipped. `PF Game
  The Riffle` stands at the ONE site that measured zero refusals - V97588 / U80333, on the shared
  veranda between the two bays, which is where a guest queues for both.

- **`test_no_shipped_game_takes_a_cell_the_park_already_owns` was a snapshot trap and is fixed.**
  It read `Park Complete` as "the world before the design", and the moment the three built-but-
  unplaced games were placed, it reported `PF Game Pan Line` as colliding with ITSELF. What rule
  15 actually says is that an overlap is a cell where the world holds something DIFFERENT, so a
  cell a game already occupies with its own state is built progress. That is the fourth time this
  repo has shipped the same trap.

### The ride has to go THROUGH the mountain (2026-09-03)

Jack, on the placed ridge: *"the coaster doesnt even go into the mountain you built."* He was
right, and the cause was a fix of mine one round earlier: `stand_off` held the crest seven cells
clear of the whole ride so the crag would stop swallowing it, and **the track's easternmost point
is V96 while the summit sat at V108-118**. The mountain stood BESIDE the coaster.

**THE TRACK IS A RECTANGLE AND ITS LEGS ARE MEASURED**, in the ridge's own lot coordinates:

    north lift     V8-96   U3-5    y1 -> 39     climbing west to east
    east traverse  V91-96  U6-21   y39          FLAT, at the very top of the ride
    descent        V78-86  U21-57  y39 -> 7
    south return   V8-77   U51-57  y1-15

The east traverse is the tunnel: sixteen cells of level track at the crest of the lift, which is
exactly where a mine coaster dives into the hill. The summit moved to `[88, 10, 96, 40, 50, 20]`
so it straddles it, and `tunnels: [[74, 100, 4, 34]]` is the box where the stand-off is WAIVED.

**A BORE, NOT A MOAT.** Inside a tunnel zone the mass closes over the track and what keeps the
ride running is a swept envelope round the RAIL - ±2 laterally, -1..+4 vertically - cleared before
anything is filled, then dressed in stone brick and timbered with a set every fourth cell. Sized
to the ride's whole MASS it would hollow out the trestles and leave the mountain standing on
nothing, so it is sized to the cart.

**OUTSIDE A TUNNEL THE REFUSAL IS PER COLUMN; INSIDE IT, PER CELL.** That distinction is the whole
mechanism. Refusing the ride's whole column is what stops a talus growing up between two trestle
legs - and it is exactly what makes a tunnel impossible, because the track's own column then stays
open to the sky and the result is a cutting with two walls. `test_NOT_ONE_CELL_THE_RIDE_OWNS_IS_
TAKEN` was written per column first and had to be rewritten per cell: asserted per column, it
forbids the tunnel the design exists to have.

**AND A SET'S POST STOOD ON THE TRACK - the same bug as the adit's cross-cut, met a second time.**
The axis a set straddles is derived from the track's own run, and at a CORNER that derivation is
wrong by construction, so two posts came down on the rail itself. The build audited clean, reported
a correct BOM and rendered as a perfectly good tunnel; the only symptom is a cart that hits rock.
The lane the cart runs in is stated now and refused, and
`test_THE_RIDE_RUNS_THROUGH_THE_MOUNTAIN` asserts both halves - every rail cell inside the zone
carries rock over it (or it is a cutting) and nothing solid stands in its four courses (or it is a
wall). 45 of 45 roofed, 0 blocked.

### THE LAND HAD ZERO TREES (2026-09-03)

Jack: *"i dont want a bunch of buildings to go into, this is just a village then, thats opposite
of what i asked for and is exactly what i complained on"* ... *"find other small things to add in
the area either design or otherwise that complete it."*

He is right, and my own previous suggestion - fill Boomtown with a saloon and a telegraph - was
exactly the answer he had already rejected twice. **Measured, the Frontier's entire flora was:**

    moss_block 29,488 . moss_carpet 731 . mossy_cobblestone 439 . mossy_stone_bricks 2,356

and **ZERO LEAVES.** Not one tree in a land that is 66% bare lawn. That is why 22,000 columns of
it read as a green carpet with things standing on it: nothing GROWS there.

`PF Frontier Scatter` (`gen/frontier_scatter.py`, 3,843 blocks, 0 problems, 0 overlap) is pines
with stepped canopies, dead barkless snags, mossy boulders in the land's own quarried palette, and
what a mine leaves lying about - cross-piled timber, tipped ore, a barrel on a cart axle. **Not one
building in it.** Frontier leaves 0 -> 3,083; columns with something over three courses tall
33.3% -> 42.4%.

- **IT SWEEPS RATHER THAN PLANTING A LIST OF STANDS, AND THAT IS A MEASUREMENT.** Of 11,562 open
  lawn columns only **1,542 survive a three-cell erosion** - the open ground is verges and gaps
  between buildings, and the largest free rectangle in the land is 8 x 18. A hand-picked list of
  stand centres found exactly ONE site. The sweep walks the land on a coarse lattice and plants
  wherever the ground itself allows, with a smooth density field so it comes out as thickets and
  clearings rather than an even spread.
- **A PINE ONE CELL OFF A KERB STILL CROWDS THE WALK.** The lawn test alone puts a trunk against
  every street in the park; `path_clear` holds every planting two cells off anything paved.
- **EVERY COURSE OF A CROSS-PILE SITS ON THE ONE UNDER IT.** Written as three rows at `k//2`
  heights the top row landed on columns the bottom rows never touched - eighteen cells shipped as
  six free-floating clusters, a stack of timber floating over the lawn.

**Still open, and it is a decision rather than a defect:** Boomtown Spine (53 x 46, seven
false-front shops) and Trailhead Gate still have 0 interactive blocks between them. Filling them
with interiors is the village answer and is rejected; what they are FOR - a second ride, or
nothing - is Jack's call.

### The cleanup: three things that made no sense, and all three were mine (2026-09-03)

Jack, on the placed land: *"the 2nd strange mining track placement that goes through the building
should be deleted"* and *"the entrances/exits/mineshafts whatever they are cut into the
rollercoaster mountain make no sense at the bottom and are just a broken weird circle, and on the
other side of the rollercoaster the 'queue' area is weird, in the wrong area."*

**THE RIDE ALREADY DECLARED EVERYTHING I WAS GUESSING AT.** `Mine Coaster.scan.json` carries its
own anchors and its own counts, and nothing that added to this land had read them:

    queue_entry V24 U126 . public_entry V24 U134 . public_exit V24 U142 . ride_exit V24 U146
    boarding V79 U134 . service_access V134 U167
    queue_rows 22 . queue_cells 67 . station_blocks 902 . tunnels 1 . tunnel_mouths 2

Every guest anchor is on the ride's WEST flank at V24. Three separate faults followed from nobody
looking:

- **MY TALUS WALLED UP THE RIDE'S FRONT DOOR.** Measured against the placed park, the ridge's
  apron formed a continuous three-cell wall at V26-28 across U122-150 - directly in front of all
  four public anchors. A guest walking the ground layer's own spur to the ride's entrance met
  rock. `keep_out` now holds V24-32 / U116-154 clear, and that is not a loss: a moat on the guest
  side is what lets the ride read AGAINST the mountain rather than merge into it. **The talus
  belongs on the faces nobody enters by**, and there is no way to know which those are without
  reading the ride's own anchors.
- **THE FRONTAGE BUILT A SECOND QUEUE, ON THE WRONG SIDE, HALF OF IT OUTSIDE THE LAND.** A 7 x 30
  switchback at V27-33 / U161-190 - thirty-five cells south of the ride's own queue entry, on the
  far flank from all four anchors, and past U169 into the Claim Line reach. Its own comment said
  it stood "down the Mine Coaster's EAST flank" and V27 is the WEST one. **It was sited from the
  biggest empty strip in the land rather than from where the ride's door is**, which is exactly
  how a queue ends up pointing away from the thing it queues for. Deleted; the coaster builds its
  own 3-wide, 22-row queue. Its thresholds moved from U116/U152 to U126/U146 - the anchors.
- **THE ADIT WAS ON THE BACK OF THE MOUNTAIN AND DUPLICATED THE RIDE'S OWN TUNNEL.** Its mouths
  opened east at V145-146, and the only thing on that side is the service lane and the works
  corridor: an entrance whose approach is back-of-house is scenery nobody reaches. Two mouths ten
  cells apart read as damage rather than as a gallery. And the ride already declares `tunnels: 1`
  with `tunnel_mouths: 2` - a third set of holes in one mountain is not more mine, it is noise.
  Deleted. The interior a guest experiences is the COASTER'S tunnel.
- **AND THE ORE LINE PIERCED THE MILL'S OWN WALL FIVE COURSES UP.** Routing it through the stamp
  mill was deliberate - ore arriving on a trestle over the stamp floor is what a real mill looks
  like - and what it reads as from outside is a railway through a building. The land already has
  two railways; a third elevated track is a third thing to work out. `line: false`.

**A TEST WHOSE SUBJECT IS SWITCHED OFF SKIPS WITH THE REASON, RATHER THAN PASSING VACUOUSLY.**
The four ore-line assertions and the three adit assertions are guarded on the config rather than
deleted: the machinery and its contract stay, and a suite that reported green because there was
nothing left to check would be worse than one that failed.


### Boomtown retired: THE DIGGINGS (2026-09-03)

Jack, three times over: *"they are visually great - but all serve no actual defined purpose"*;
*"i dont want a bunch of buildings to go into, this is just a village then, thats opposite of what
i asked for and is exactly what i complained on"*; and then the shape of the answer - *"we can
have a small amount of buildings, but the rest should be other things ... we can do a landscape or
something with 1 or 2 small shops integrated."*

**MY OWN PREVIOUS SUGGESTION WAS THE THING HE HAD ALREADY REJECTED TWICE.** Asked what to do with
Boomtown Spine I proposed filling its seven false fronts with a saloon and a telegraph - which is
more buildings to go into, which is a village. Worth recording, because the wrong answer was
arrived at by taking the land's own spec ("social spine") as the brief rather than the complaint.

`Boomtown Spine` is out of `tools/park_lots.PLACEMENT`: 53 x 46, the biggest lot in the Frontier,
seven false-fronted shops and **0 interactive blocks**. `PF Frontier Diggings`
(`gen/diggings.py`, 5,792 blocks) takes the lot - a worked landscape with a trail, a working yard,
two shafts under windlasses, cribbing, tipped ore, pines, and **TWO shops cut into its banks**.

- **THE ROUTE WAS THE HARD CONSTRAINT AND IT IS MEASURED.** `Park Ways` paves **0 of that lot's
  2,438 columns**, so the land's only walk from the spine to Mining Square lived INSIDE the old
  module - its boardwalk at world U68-70, meeting the ground layer's spur at V19-23 / U69-71 and
  the V77-79 cross walk. Retire the module without carrying that and the Frontier is cut in half.
  The trail is laid on the same courses and everything else is shaped round it.
- **BANKS BATTERED AWAY FROM THE TRAIL, NOT MERELY KEPT OFF IT.** Held at one height and simply
  not placed on the walk, spoil either side is two walls with a corridor between them.
- **AND THE LINEAR RISE MUST NOT DOMINATE.** At `bank: 10` the block came out as a symmetric
  terraced amphitheatre - two mirrored ramps of regular contour steps with a road down the middle,
  which is the ziggurat failure in a new shape. At 4 with eight mounds it was wall-to-wall grey
  rock: a rock garden with a corridor, which is not better than a street of shops, only greyer.
  At **2, with four mounds and a working yard**, most of the lot is open ground and the trail
  arrives somewhere. **A ROUTE WITH SOMEWHERE TO STAND ON IT IS SOMEWHERE TO BE.**
- **INTEGRATED MEANS DUG IN, NOT STOOD NEXT TO.** A 7 x 5 hut on the lawn beside a spoil heap is
  an eighth false front; the same hut with rock forced over its lintel is part of the landscape.
  The reserve runs FROM the front face inward - reserving one cell in front of it too forces mass
  into the trail-side verge, buries the awning and the name board, and both shops shipped
  `signed: false`.
- **THE FALL TO THE LOT'S EDGE IS CLAMPED AFTER THE MOUNDS, NOT BEFORE THEM.** Before, a
  `maximum` over the mounds simply overrides it and a twelve-course bank stands proud on the
  boundary - against the land's cross avenue, which is a guest street.
- **AND THE LANE IS STATED AND REFUSED. Third time in this land.** A timber set stood on the
  coaster's rail; an adit's cross-cut post bricked up its own corridor; and two pines went
  straight into the trail - twenty-four cells of trunk and canopy in the one walk the module
  exists to carry. **A prop sited by hand near a way will eventually be sited IN it**, so the way
  refuses rather than the hand remembering.

### The scatter's two self-references, which pull opposite ways (2026-09-03)

`PF Frontier Scatter` reads `Park Complete` to find plantable lawn, and once it is placed the
composite CONTAINS it. Measured, the second run refused nearly every cell the first had planted
and came out at **428 blocks against 3,843**. That is the snapshot trap for the third time in one
session, and the fix is rule 15: a cell this design itself placed is built progress, so its own
materials are allowed in the "is this column clear" test.

**BUT THE DIGGINGS AND THE RIDGE ARE BUILT FROM THE SAME ROCK AND THE SAME TIMBER**, so that
allowance immediately let a canopy spread over a neighbour: 33 clashing cells inside the Diggings,
Mining Square and the Assay Office. Two more things were needed and they are different mechanisms:

- **A COLUMN TEST IS NOT A CELL TEST, AND A CANOPY IS CELLS.** `lawn` asks about a whole column,
  which is right for where a trunk may STAND and wrong for where a leaf may go. Every spreading
  part asks per cell now: 33 -> 18.
- **AND A LOT LIST FOR EVERYBODY ELSE'S GROUND.** No material test can tell my pine from the
  Diggings' pine, so the nine module lots are keep-out. 18 -> 0. Land dressing goes on the ground
  BETWEEN modules, and the density is set against what is actually available - the same density
  over a third of the area came out at 1,881 blocks.


### A SECOND RIDE, in the emptiest lot in the land (2026-09-03)

Jack: *"what about the rest of frontier though, outside of the rollercoaster and now this little
mine-shop area, its so much wasted empty crap."*

**MEASURED, IT WAS NOT VOIDS - IT WAS DENSITY.** 56% of the land was built and the biggest empty
rectangle in it was 10 x 12. What the numbers actually say is blocks per column, and how much of
each lot stands three courses tall:

    Vantage Lookout        289 cols   14.3   100%
    Mine Coaster + Ridge  8804 cols    7.8    63%
    Assay & Prize Office   920 cols    2.9    71%
    Works Yard             468 cols    2.6    65%
    Trailhead Gate        1755 cols    2.5    38%
    Frontier Diggings     2438 cols    2.4    30%
    Mine Works            2200 cols    2.2    33%
    Prospecting Porch     2040 cols    2.1    45%
    MINING SQUARE         1886 cols    1.4    10%    <- a car park

**Mining Square was the second-biggest lot in the land and 39 x 44 of flat stone paving** with an
ore cart on it - 1.4 blocks a column, 90% of it nothing taller than a kerb. And the land had
exactly ONE ride.

`PARK_FRONTIER.md` asks for the missing one by name - *"Runaway Mine -> rework as family-scale
Mine Cart Escape, mechanically and visually distinct from coaster"* - and `gen/attractions.py`
already builds it, with a contract that generator verifies rather than claims: a closed powered
circuit out of a roofed station, under two timbered portals, seven courses up the east side on
trestles, across the crest level with the headframe's hoist beam, seven down the west, back to the
platform. 62 cells, 4 corners, every run powered at both ends, every corner flat on both sides,
every elevated cell on piers, two clear courses over every rail. **The headframe stands INSIDE the
loop**, which is that file's own recorded rebuild: a ride's content is what you PASS.

- **AND THE SQUARE'S TWO ARCHES ARE TRUE NOW.** They read COASTER QUEUE and RIDE EXIT and stood
  forty cells north of a coaster whose four guest anchors are all on its WEST flank at V24. They
  are the cart ride's queue and exit, because the ride is actually in this square.
- **A RESERVE, A FLAT AND A TERRACE ARE THREE DIFFERENT ANSWERS** and conflating any two breaks
  one. `reserve` means another design owns the ground - the ride brings its own apron and piers,
  so paving under it is two designs on one surface. `flat` means pave it but never RAISE it -
  `PF Game Powder Striker` is a console standing on the square's own floor, so reserving it leaves
  the console floating and terracing it leaves the console buried. The terrace itself is the fix
  for 1.4 blocks a column: one plane reads as a car park however well it is inlaid.
- **THE GROUND STOPPED BEING ONE NUMBER, AND EVERYTHING STANDING ON IT HAD TO ASK.** With a
  terrace over the west third, `base = ter` is right on the terrace and two courses wrong off it:
  the show board spans v15-25, the terrace stops at v13, and the board shipped as a 140-cell
  fragment floating two courses over the paving with the claim marker as another thirty.

### The adit, third siting: THE RIDE'S FOOTPRINT IS NOT ITS LOT (2026-09-03)

A parallel session re-added the adit with `mouths: 1` - the right answer to *"a broken weird
circle"*, and to a later note that *"basically none of the mountain is used except the top peak"* -
sited two cells off the coaster's own `ride_exit` anchor. **`park_place` reported 102 contested
cells between the ridge and the ride**, because local v14 is world V38 and **the Mine Coaster's own
low track runs world V32-44**. An anchor is a door in a face; the footprint behind it is not free
ground.

Mapping the ride's footprint across the whole guest band showed there was no fixing it by a cell or
two: on that flank the only free ground is the 5-wide moat at world V24-28, which this design
deliberately keeps out of so the ride's four anchors stay open.

**THE SITE THAT WORKED CAME OUT OF DELETING SOMETHING ELSE.** The ridge's `keep_out` was one box
over the whole south band because the frontage had put a 7 x 30 coaster queue at V27-33/U161-190.
That queue is gone (the ride builds its own), and the band actually holds three props - the Ridge
Water Tower, the Ore Road and the Trail Ore Cart. Narrowing one box to three freed **~1,100
columns of empty ground south of the ride**, which is a fair part of the "wasted empty crap": the
mass now has a real south flank instead of stopping dead at the ride's own south edge, and the
adit is bored into it at world V40-52 / U160-168, reached off the lawn a guest walks round the
ride's south side.

**AND THE REFUSAL IS STRUCTURAL RATHER THAN THE NUMBERS BEING RIGHT.** `_fill` refuses `occ` per
cell and the adit's own placements did not, so whatever an adit is pointed at, a cell the ride
occupies is swept back out afterwards and the count is REPORTED. It read 102 on the old site and
reads 0 on this one - which is how you tell a guard that fired from a guard that is decorative.


### The row from the pennant to the tower: the ground the modules never built (2026-09-03)

Jack, on a Litematica overlay looking down Frontier column A: *"basically everything on this row
from the orange flag to the tower is useless/waste of usage of space."*

**MEASURED, AND HE WAS RIGHT FOUR TIMES OVER.** The row - the Prospecting Porch's orange pennant to
the Vantage Lookout, V24-146 x U0-39, 5,840 columns:

| | cols | b/col | bare moss | things a guest can operate |
|---|---|---|---|---|
| Trailhead Gate V24-68 | 1800 | 3.4 | **63%** | **0** |
| Prospecting Porch V69-118 | 2000 | 3.1 | **54%** | 2 consoles, both at V88-90 |
| the gap V119-129 | 440 | **1.1** | 52% | **0** |
| Vantage Lookout V130-146 | 680 | 7.9 | 34% | 1 barrel, 3 rails |

**3,153 of 5,840 columns bare**, in two 1,000-cell holes plus a 29x19 void in front of the tower.

**AND THE CAUSE IS TWO CORRECT RULES MEETING.** The holes are not BETWEEN the modules, they are
INSIDE them:

- `_trailhead` builds a portal, two towers, an office, a porch, a stockade, a water tower and a
  store, and leaves its own ~24 x 31 court as lawn. That is *"a large rectangular building with an
  open center"* - the exact shape the Arrival Court was retired for - still standing, in a
  different land. **And there was no paved route through the gate at all**: a guest came through a
  monumental portal and walked on moss to the exit arch.
- `_porch_lot`'s own docstring says why it does not fill its lot: its declared west door *"opens
  into the BACK OF TRAILHEAD GATE"*, so it is a strip on the avenue flank and U0-18 is its unbuilt
  back - **two buildings' backsides facing each other across twenty columns of lawn.**
- `frontier_scatter` cannot reach either, correctly: it KEEPS OUT of every module lot, because a
  material test cannot tell its own pine from the Diggings'.

**So the ground that is inside a lot and outside a building belonged to nobody.** `gen/claimrow.py`
owns it: `PF Frontier Claim Row` (1,070) works the porch's back and the gap; `PF Frontier Muster
Yard` (905) furnishes the gate's court and gives the threshold its route. **0 problems, 0 overlap,
all cheap-or-ok, no water and not one building** - Jack ruled both out for this land, and a
played-out placer claim is dry by definition, so the constraint and the subject agree.

Coverage: the claim row dresses **83%** of its workable lot and the yard **78%**, and what is left
is moss showing through - which is what makes a working stop raggedly instead of being a rectangle.

#### A MATERIAL TEST CANNOT ANSWER RULE 15 IN A LAND WITH ONE PALETTE

`frontier_scatter`'s `OWN` set exists so a second run re-lays its own standing work rather than
refusing it - the 428-blocks-against-3,843 bug - and its own comment warns the set must be narrow.
In this lot **neither width works**, and both failures shipped a clean audit:

- **wide** (the full kit): the marquee's plinth is `polished_blackstone_bricks` and so is this
  design's, so a claim's board post went straight through the Prospecting Porch's marquee and 39
  cells of pine canopy grew into the Trailhead Gate;
- **narrow**: this design's own stakes, posts, planks and barrels are the same spruce every building
  in the land is framed in, so a re-run refuses its own props.

**A DESIGN'S OWN CELLS ARE KNOWABLE EXACTLY - THEY ARE IN ITS OWN LITEMATIC.** `shipped_cells`
reads them in world coordinates and `_Ground` takes them as `mine=`; `OWN` shrinks to
`{"moss_carpet"}`, the one thing in this park that is genuinely ground cover rather than somebody's
build. Material identity never decides an overlap again, and `test_mine_is_exact_where_own_is_a_
guess` pins the difference on a two-column fixture.

What still needs naming by hand is a NEIGHBOUR standing on the lawn, and that is measured rather
than guessed - three things inside the claim row's lot, listed in its config with their cell counts.

#### FIVE MATERIALS INSIDE TWENTY-ONE POINTS OF LUMINANCE IS ONE GREY

The first worked flat was gravel 128, cobblestone 127, andesite 136, stone 126 and mossy cobble
115, and it rendered as a pale slab. **That is the fourth time this file records the same mistake**
- stone brick, blackstone, the Mine Ridge, and now this - and every one was made by searching
WITHIN a family, where a ladder cannot exist by construction. Measured across families,
cheap-or-ok and 1.19:

    cobbled_deepslate  77   spoil, and what a shaft throws up
    dripstone_block   112   turned earth, and WARM, so it is not a fifth grey
    cobblestone       127   the wash
    gravel            128   the crust - rule 13, top course only
    diorite           188   the pale washed bars

Smallest step 15, biggest 60. `test_the_worked_ground_is_a_real_value_ladder` re-derives it rather
than trusting the table.

Three more things the flat needed, each a rule this file already carries:

- **THE MATERIAL IS DRAWN ON A COARSE LATTICE, NOT PER CELL.** Per cell, five materials over a
  thousand columns is static - a slab with speckles on it. Three quarters of the draw comes from a
  3x3 block of ground and a quarter from the cell, so it comes out as patches with ragged edges.
- **THE MIX IS A FUNCTION OF HOW WORKED THE CELL IS**, read off the SAME score that decides how far
  the working reaches - so the tone gradient and the outline are one thing and cannot drift apart.
  The middle is spoil and turned earth; the edge is gravel and moss showing through.
- **A BOUNDARY MUST BE A DIFFERENT VALUE FROM THE GROUND IT BOUNDS.** 150 claim-kerb slabs at 127
  against a working running 77-128 drew no line at all from the one view a claim is read from,
  which is the plan. `cobbled_deepslate_slab` at 77 is the same 50-point step the island's own
  masonry gets from `deepslate_bricks`.

#### Four traps, each of which shipped a clean audit

- **`no:` IS NOT AN INTEGER KEY, IT IS `False`.** YAML 1.1 parses on/off/yes/no as booleans, so a
  claim written `no: 1` came out keyed `False` - the number silently lost, and then the design
  fingerprint's `sort_keys` exploded on a dict holding a bool and a str. The Lowland Glow shipped
  this with a key called `on`. `test_no_config_key_is_a_yaml_boolean` walks both configs.
- **A SIGN GOES IN A CELL AND `_Lot.sign` ONLY ASKS THE CANVAS.** It checks the board is behind it
  and the cell is empty - both true of a cell inside a NEIGHBOUR's keep-out box, because the canvas
  is this design's own and knows nothing of the world. A claim's post stood legally at U13 and hung
  its sign at U14, one cell inside the marquee, and the sign refused SILENTLY. The board asks the
  ground probe about its sign's cell now - **and tries the claim's far corner when the near one is
  refused**, because a hand-tuned offset per claim is a number that goes stale the first time a
  claim moves.
- **`free(v, u, y)`, NOT `(v, y, u)`.** The fix above was first written with the arguments
  transposed, so it checked a cell that does not exist: the guard read as working and the overlap
  stayed exactly where it was.
- **A YARD IS BEATEN GROUND WITH A ROUTE THROUGH IT, NOT A LAWN WITH A PATH ON IT.** The muster
  yard's first build paved its two legs and stopped - 116 cells of route in a nine-hundred-column
  court, which leaves the court exactly as bare as the complaint found it.

#### The bays were not shells, and the docstring saying so was stale

`_porch_lot` has said since it was written that both its bays are *"built with their counter,
backboard, result panel and reset hatch in place and NO circuit behind them."* The machines were
added afterwards by `gen/park_games.py` and nobody came back. Measured: `PF Game Pan Line` (a
`mark` console - load the pan to exactly three) stands INSIDE bay A at V81-90/U22-31, and
`PF Game The Riffle` on the shared veranda at V88/U33.

**WHAT WAS ACTUALLY WRONG IS THAT BAY A PROMISED A GAME IT DOES NOT HAVE** - signed SHOOTING RANGE,
with a target backboard and a firing counter, holding a washing scale. It is **THE WASH HOUSE** now,
which is what is in it. (And "prizes at the assay" is nineteen characters, so it shipped clipped to
"prizes at the a" - **fifteen characters is the line**, and this file has recorded that once
already.)

**And bay B has no machine because it has no room.** With everything standing, its largest box clear
to head height is **4 x 6**, inside its own dry settling pool, against a smallest console of 10 x 4;
the wash house's is 3 x 11. That is a siting fact rather than an omission - a game cannot go in
without deleting the launder, trestles and pool that make the bay a sluice.

#### Still open on this row

- **Trailhead Gate's zero interactive blocks is now one** - the muster bell, which is the only verb
  the yard adds. The whole row still carries three.
- **The Vantage Lookout is a 56-course tower beside 5-7 course sheds**, and in elevation the row
  reads as a strip of brown huts and then a skyscraper. Not touched; it is a massing decision.
- **Nothing here has been placed in game.** Judge form and mass off `render3d`, palette in world.

### THE LOST PLATEAU - the Frontier re-themed, and the number that condemned it (2026-09-03)

Jack: *"I just think this theme is boring and dull and doesnt represent well - its confusing to the
end user ... lets take the same color schemes potentially so we dont change the coaster, but I think
'frontier' needs to change and we need to represent something more interesting here - looking at the
rest of the park, this falls so short."*

**ONE NUMBER IS THE WHOLE COMPLAINT.** Show material - wool, concrete, copper, glass, lamps, carpet,
anything MADE and coloured - as a share of each land:

| land | blocks | show | verbs | reads as |
|---|---|---|---|---|
| Midway | 87,967 | **24.0%** | 335 | red/white fairground |
| Prismworks | 96,576 | **21.7%** | 316 | copper and cyan |
| Wyrm reach | 31,738 | **31.7%** | 12 | a 40-block bone skull |
| **Frontier** | **144,620** | **1.3%** | 349 | moss 20%, stone 15%, brick 10%, cobble 9% |

**IT WAS THE BIGGEST LAND IN THE PARK AND THE ONE WITH THE MOST TO DO**, so it was never short on
effort - it was short on IDENTITY, at one twentieth the colour of its neighbours. **And a gold-rush
mining camp cannot be fixed by adding colour, because timber and stone IS the theme.** That is why
the theme went and the execution stayed, and it is worth keeping as a general test: when a land
measures fine on every axis but reads as nothing, ask what its palette is FOR before adding to it.

**THE EXPENSIVE PART SURVIVES ANY RE-THEME, AND THAT DECIDED WHICH ONE.** `Mine Coaster` (56,635)
and `PF Mine Ridge` (41,948) are 98,583 blocks - **72% of the land's mass** - and a mountain with a
rail ride cut through it works under any story: a cave tunnel and a mine tunnel are the same tunnel,
and a timber trestle over a gorge is a timber trestle. Every other building is under 5,800, so the
cost of a re-theme is almost entirely in the remaining 28%.

Of three directions costed - Lost World, volcano, alpine - the Lost World wins on measurement rather
than taste:

- **highest reuse in the park**: a mining camp and a palaeontology field camp are the SAME
  BUILDINGS, so the gate, works yard, assay office, wash house and lookout rename rather than
  rebuild, and `PF Frontier Diggings` is already literally a dig site;
- **it owns a colour nothing else in the park has** - jungle green and bone - where a volcano's
  orange fights the Midway's red and an alpine white fights the Wyrm reach's 25% light grey;
- **and it is the one content type this repo can build.** CLAUDE.md's own line is planar/columnar
  against volumetric: a sauropod is a neck on columnar legs (the giraffe, which works), a pterosaur
  is a membrane wing (the bat, which works), a stegosaur is a convex mass with planar plates (the
  ladybird category), and a fossil is pure planar. The Wyrm skull proves bone-work reads at 40
  blocks. **A T-REX IS THE ONE EVERYBODY WANTS AND THE ONE THIS SYSTEM IS WORST AT** - a heavy biped
  is volumetric muscle, which is what retired eight mammals - so if it is ever built it is built as
  a SKELETON, which is planar and which the Wyrm already proves.

#### `gen/plateau.py` - the canopy, and why it is the cheapest possible change

**15,374 blocks, 0 overlap, 0 new problems in context, all cheap tier, and not one cell of the
coaster or the mountain touched.** Everything goes into AIR above the ridge's own surface, so the
pass is reversible by breaking what it placed - the deck floor's rule that a remedial design is
judged by what it REPLACES, applied to a mountain.

The ridge was the lever because it is the biggest grey object in the park: 8,804 columns, **5,776 of
them standing at Y206 or above**, top surface stone 14% / gravel 13% / cobble 9% / andesite 4%.

    THE RIDGE'S TOP SURFACE, 8,804 columns:   24.2% green  ->  71.0% green
      stone 13.8% -> 5.2% . cobblestone 8.8% -> 3.7% . gravel 12.9% -> under 3%
      jungle_leaves 17.6% . vine 9.4% . fern 6.4% . azalea 3.3% . moss 19.8% -> 29.0%

Four pieces, in the order they must run: a **moss cap one course over the rock** (which is the
colour AND the soil - a plant roots in the dirt family and nowhere else, and the Lowland Thicket
returned 173 placement problems for treating mossy cobble as ground); **jungle canopies** on the
cap; **vine curtains** down the faces; **ferns and lichen** under them.

Four things it cost:

- **A JUNGLE CROWN IS WIDE AND FLAT, NOT CONICAL.** A spruce narrows in steps and reads as a fir;
  what says jungle is a crown wider than it is tall carried clear of the ground on a bare trunk, so
  you see UNDER it - which is also what makes it read from the ride, which passes below the crest.
- **THE SKY CLEARANCE TEST IS NOT OPTIONAL.** The coaster's trestles are 14.9% of this lot's top
  surface, so a tree on a bench beside the track grows straight through it - invisible in a plan
  view and obvious from the ride.
- **A FACE IS FOUND, NOT DRAWN.** A vine curtain hangs where the ground falls away - a column whose
  neighbour is three or more courses lower shows that much rock. Drawn as a rule about position it
  lands on flat ground and reads as green string in mid-air.
- **CHECK THE SOIL, DO NOT ASSUME IT.** The cap is at top+1 and a fern at top+2, so the soil looks
  guaranteed - until a neighbouring tree whose ground is one course lower drops a canopy leaf into
  that very cell. Six ferns shipped standing on `jungle_leaves`: a placement problem in context and
  invisible in isolation.

**AND THE DESIGN ALONE REPORTS 1,310 PROBLEMS, ALL OF THEM VINES WITH "no attachment".** That is the
Mine Ridge's own situation and it is correct: a vine clings to the ridge's rock, which belongs to the
WORLD and not to this design, so in isolation it hangs on nothing. In context it is 0. **The
composite is the truth** - and a pass whose whole purpose is dressing somebody else's surface can
never be judged alone.

#### The re-theme, carried through: the signs, the trees and the landmark (2026-09-03)

**THE SIGNS.** A land whose signs contradict its ground is worse than one that is merely grey, and
28 of them plus 11 frontage marquees still said Frontier. All of them now name what is actually
there - the gate is **LOST PLATEAU / "camp and dig"**, the marquees are **BASE CAMP GATE**,
**THE SCREENS**, **PLATEAU RUN**, **BASE CAMP**, **THE FOSSIL LAB**, **THE HAUL ROAD**,
**MATRIX TIP**, the porch's bays are **THE SCREEN HUT** and **THE SORTING RUN**, the stamp mill is
**THE CRUSHER** (which is what a stamp battery is), the claim posts read **DIG No 1 / THE BONE
BED**, and the Diggings keeps its name because a dig site is a dig site.

**Two signs were already clipped mid-word before this pass touched them** - "and prize windo" and
"ore from the ad" - so a width check now runs over every config sign line in the land. **FIFTEEN
CHARACTERS IS THE LINE**, and this file has recorded that twice now.

**THE TREES.** `frontier_scatter` planted spruce, which is the single most frontier-looking thing
left on the open ground. **A PALETTE SWAP IS NOT A SHAPE SWAP**, and that is the whole reason
`_jungle` exists beside `_pine`: `_pine` narrows in steps, which is what makes a voxel conifer
read, and built out of jungle wood it is a fir painted green. The broadleaf carries a crown wider
than it is tall on a bare trunk - the same shape `gen/plateau.py` puts on the ridge, so the canopy
above and the trees below read as one wood.

Three things that change made necessary, each one a rule:

- **THE PALETTE TRAVELS WITH THE GROUND PROBE, NOT AS A MODULE GLOBAL** - `gen/claimrow.py` shares
  these props, so two lands with two species have to run in one process.
- **`OWN` IS THE UNION ACROSS EVERY PALETTE.** Keyed to one, the re-theme would have refused every
  spruce still standing and planted on top of it.
- **AN UNKNOWN KIND RAISES; IT DOES NOT BECOME A ROCK.** The claim row's dispatcher swallowed any
  name it did not recognise in an else-branch, so the day the config asked for `jungle` it would
  have planted boulders and the only symptom would have been a suspiciously stony landscape.

**AND `previous:` WAS BUILT AND NEVER WIRED UP.** The claim row reads `Park Complete`, and once it
is placed that composite CONTAINS it - so on the first run after shipping it read its own worked
ground as somebody else's build and **1,070 blocks came out as 8**. The mechanism was right and
the config never named the file. Both configs carry it now.

#### `gen/sauropod.py` - and the land has no room for it

**2,323 blocks, ONE piece, 0 problems, all cheap.** A brachiosaur: four columnar tapered legs with
the FRONT pair longer, a spindle barrel falling away to the hip, a neck rising nearly vertical to a
crested head, and a tail as long as the neck.

**IT IS BUILT BECAUSE OF THIS FILE'S RULE, NOT IN SPITE OF IT.** The neck is a column - the giraffe
is the one quadruped here that works, and it works because its identity is a neck. The legs are
columns. The silhouette carries it entirely, which is the panel review's only real question. **A
diplodocid was rejected**: it carries its neck level, which foreshortens to nothing from three of
four bearings and reads as a log on legs.

**THE COAT IS A MEASURED HUE FLIP FROM THE CANOPY.** Against `jungle_leaves` (73,103,27),
`brown_wool` is 53 RGB away and `gray_wool` 58 - both vanish, which is the green-turtle mistake.
The ladder is `gray_wool` 67 / `light_gray_wool` 141 / `white_wool` 236, and the flank sits 134 RGB
clear of the leaves it stands against.

Three defects, and two of them were invisible:

- **A CANVAS SIZED FOR THE WRONG AXIS.** The box was always long in X. Built facing north the
  animal's length ran along Z and it was **clipped to 22 blocks of 48** - head, neck and half the
  tail simply refused - while the render still showed a plausible small dinosaur. The only symptom
  was a refusal count nobody was reading. The frame maps forward and side onto the world; the box
  has to be mapped the same way.
- **A PROTECTION SET KEYED ON MATERIAL PROTECTS EVERY CELL MADE OF THAT MATERIAL.** The crest is
  `light_gray_wool` and so is the flank the whole animal is swept in, so "keep the crest" kept all
  2,323 cells: the countershading ran, skipped everything, and returned a tally of four zeros. **It
  is the same mistake as answering rule 15 with a material list, one level down** - a set of things
  is not a set of cells - and it shipped a monochrome animal.
- **AN EYE IS FOUND, NOT COMPUTED.** Placed at a calculated half-width it floated a cell proud of a
  head the sweep had already moved, ringed in five cells of white on a head three wide - a clown
  patch, 169 points of luminance where 35 is enough. It reads the built surface back now and its
  ring is `light_gray_wool`.

**AND THE LAND HAS NO SITE FOR IT.** Searched over the whole Frontier band plus the Claim Line
reach, water allowed and roll tolerated to ten courses:

    open lawn with 36 courses of sky        8,724 columns
    LARGEST CLEAR RECTANGLE IN ALL OF IT      6 x 49
    sites holding 42 x 13, its footprint           0
    ...on the plateau's own soil, roll <= 10       0

**The land is full: its open ground is verges and strips six wide.** Jack: *"we can put it
somewhere on the far left side; against the void where the tower and other frontier objects
currently are"* - and that is the one band with room, the outer rim past the railway at
**V187-199, which rolls two courses in its entire length**. 132 windows of 13 x 42 fit there; it
stands at the lowest-U one, the corner the Vantage Lookout is in, facing north into the park so a
guest sees the head and neck rather than the tail.

**A SEARCH THAT RETURNS ZERO IS NOT ALWAYS A FULL LAND.** This one returned zero four times and the
fourth was an off-by-one: `range(dv - L)` never tries the row the band actually starts on, so the
rim - flat, empty and 13 deep against a 13-deep animal - was the one window never tested.

#### Still open

- **The fossil dig and the pterosaur are not built.** The Diggings is already a dig site and wants
  bones in its trenches; a pterosaur is `gen/bat.py`'s category and would hang off the plateau's
  face.
- **The land measures 1.4% show material still**, because its colour is now FOLIAGE rather than
  wool - the ridge's top surface went 24.2% green to 71.0%, which the show-material metric cannot
  see. Whether that reads as an identity is a question for a walk, not a number.
- **Nothing placed in game.**

#### The dinosaurs: a dig, a bigger sauropod, and a pterosaur (2026-09-03)

Jack: *"do the dig site first, make the existing dino bigger, and then lets do the pterosaur
after"* - and, opening the ground up: *"we also will need to replace the frontier buildings etc so
its OK for us to put things there."*

**`gen/fossils.py` - THE BONE BED.** A skeleton is the one animal shape this medium cannot get
wrong. The central sculpture rule is planar and columnar against volumetric, and a skeleton is
nothing BUT sheets and tapers: a spine is a line, a rib is a curve one block thick, a skull is a
small box with holes in it. The plan is the money view, which voxels give away free, and a dig is
looked INTO.

**A TRENCH IS A HOLE IN THE SPOIL, NOT A DIG.** A litematic cannot express removal - but the
diggings' ground stands eleven courses above the plane, so forcing the height field to ZERO inside
a box leaves a real cut with real walls at no cost and nothing to break first. It runs alongside
the trail, which is the viewing gallery.

**`gen/sauropod.py` GREW BY HALF, AND THE LEGS ARE WHY IT COULD.** The rim it stands on is thirteen
rows deep and the animal's width is 2 x (stance + leg radius) - so the LEGS were the cap, not the
body, and at 0.0853H of radius a leg was 0.17H in diameter where a real graviportal limb is nearer
0.12H. Slimmed to a true gauge it is 11 wide at h=48 instead of 15: **63 long, 50 tall, 5,036
blocks against 2,323**, on the same rim, with a clear column of ground each side.

Finding it needed four searches and the fourth was an off-by-one: **`range(dv - L)` never tries the
row a band actually starts on**, so the rim - flat, empty, and exactly as deep as the animal is
wide - was the one window never tested. Three searches returning zero is not proof a land is full.

**`gen/pterosaur.py` IS THE OTHER HALF OF THE SAME RULE.** The sauropod is columns; this is the
PLANE - one membrane hung from one hugely elongated finger. It is NOT `bat.py` re-coloured, which
Jack ruled out on the causeway: a bat's wing is a mammal's, four fingers over four spans with the
body slung under it. And it carries its own crag, so it stands on the plateau's summit at **Y257,
the highest ground in the Frontier** - the obvious perch, the Vantage Lookout, is measured and
refused, because its deck is 8 x 15 and a 38-span animal on it reaches eight cells past the park's
own boundary.

##### Seven defects, and only one of them was visible

- **A CANVAS SIZED FOR THE WRONG AXIS.** The sauropod's box was always long in X, so built facing
  north its length ran along Z and it was **clipped to 22 blocks of 48** - head, neck and half the
  tail simply refused - while the render still showed a plausible small dinosaur. The only symptom
  was a refusal count nobody was reading.
- **A PROTECTION SET KEYED ON MATERIAL PROTECTS EVERY CELL MADE OF THAT MATERIAL.** The crest is
  `light_gray_wool` and so is the flank the whole animal is swept in, so "keep the crest" kept all
  2,323 cells: the countershading ran, skipped everything, returned a tally of four zeros, and
  shipped a monochrome animal. **It is the same mistake as answering rule 15 with a material list,
  one level down: a set of things is not a set of cells.**
- **THE SCALE PARAMETER DID NOT SCALE.** The leg radii and the whole head were absolute blocks -
  this file's own named trap - so a bigger animal grew a bigger body on the same legs and kept a
  toy head.
- **THE TRENCH RESERVE RAN AFTER THE SHOPS.** A bench LOWERS the height field and a shop's cover
  RAISES it, so whichever runs last wins: the trench took the rock off a lintel and the shop
  shipped as a hut standing in a bank rather than a room cut into one.
- **A WORKING SITED FOR THE OLD GROUND CAME OUT FLOATING** three courses over the new bench - 107
  cells, one stray component. A prop checks its own footing now; the field is the authority on
  where the ground is.
- **A BROADLEAF CROWN IS RADIUS 3 WHERE A CONIFER'S WAS 2**, which put leaves on the lot's own edge
  and refused fifty canopy cells at the boundary. **A re-theme that changes a tree's SHAPE changes
  where a tree may stand.**
- **AND A BONE OUTSIDE THE TRENCH DOES NOT OVERFLOW, IT VANISHES.** A femur landed nine cells
  sideways in the TRAIL first; the bound then clipped 45 cells of rib, half of each girdle, and
  half the SKULL - the part a stranger looks for - all silently. The bound lives in `_bone` and
  nowhere else, which is `_Lot.put`'s own discipline: guarded per feature, the loose limbs were
  confined and the ribs were not.

##### CHASING EACH ARITHMETIC CORNER DID NOT CONVERGE

The pterosaur came apart three separate times and **never at the size last tested**: the head at
span 38 while 34 and 40 were whole, then both wingtips at 30 and 46. Every fix that patched one
rounding corner left another - and a bug that passes the example you tried is the worst kind there
is.

So the contract is GUARANTEED rather than hoped for. `_stitch` measures the components the build
actually produced and bridges the strays, and the bridged count is REPORTED rather than swallowed,
because a build needing twenty cells of stitching is a build whose geometry is wrong. Swept over
**168 builds - fourteen spans, three perch heights, four facings - none split, and the worst stitch
is two cells.** The test asserts that ceiling, so the safety net cannot quietly become the design.

Three joins are worth keeping as rules in their own right:

- **A JOIN IS MADE BY OVERLAPPING, NEVER BY ABUTTING A COMPUTED EDGE** - the neck runs from the
  body's CENTRE, not from its face.
- **A CHAIN STEPPED BY HAND IS A ROW OF DIAGONAL NEIGHBOURS.** `f + k * 0.8, y + k * 0.7` is not
  connected; `_run` steps finely and fills the corner where two axes change at once.
- **A CORNER FILL THAT MENDS ONE AXIS MENDS ONE AXIS.** The wing's finger patched a change in
  height and came apart wherever the sweep and the lift moved together.

##### Still open

- **The dig is one design in isolation and two in the world's own terms**, because the trail's
  verge is `Park Ways`' lawn rather than this design's ground - the Mine Ridge's recorded
  situation, and the composite is the truth.
- **The pterosaur's profile is its weak bearing.** A spread-wing animal seen along its own span
  foreshortens to a lump on a rock; head-on and in plan it is unmistakable, which is the same
  trade the bat records. Nothing to fix - it is what a wing IS - but worth knowing before siting a
  second one.
- **Nothing placed in game.**

#### "Can we improve further": three passes, and the one that changed the whole land (2026-09-03)

Jack, after the re-theme. I measured the land, offered three, and he took all three.

| design | blocks | what it is |
|---|---|---|
| `PF Frontier Overgrowth` | 5,146 | the jungle taking the camp back - vines, roof moss, ferns, hanging roots |
| `PF Frontier Rim` | 2,215 | the cliff walk and a pterosaur nesting colony on the land's outer edge |
| the Vantage Lookout | +4 | an orientation board and a bell, on a 56-course tower that had NO verbs at all |

    the town (U0-98)      foliage 30.3% -> 35.2%
    the Vantage Lookout   0 interactive blocks -> 4 (three signs and a bell)
    the rim (V187-199)    2,249 columns at 3.8 b/col carrying one animal -> a walk and four nests

**THE RE-THEME WAS DONE ON THE TERRAIN AND NEVER ON THE ARCHITECTURE**, and one render said so:
the plateau's own surface went to 71% green while the camp below it stayed grey - stone 13%, stone
brick 9%, cracked stone brick 8%, cobblestone 8% - so the land read as a rainforest standing next
to a mining town. **No amount of further planting on the LAWN fixes that, because the grey is the
BUILDINGS**, and `frontier_scatter` correctly keeps out of every module lot.

**AND THE OBVIOUS FIX IS UNBUILDABLE.** Swapping stone brick for its mossy variant is what a
builder would do by hand; **a litematica printer places into AIR and never replaces**, so every
swapped cell would stand as permanent amber in `/cscan check` for the life of the park. The deck
floor's rule says it from the other side - a remedial design's damage is measured in what it
REPLACES. `gen/overgrowth.py` adds and never covers, and `test_it_never_replaces_a_standing_block`
asserts it against the artifact rather than against a log line.

**IT STARTS THREE COURSES UP**, which is a doorway rule rather than an aesthetic one: a vine at a
wall's foot is exactly where a guest walks past it, and beginning above head height keeps every
door, street and queue clear BY CONSTRUCTION rather than by a list of exceptions. Ferns are the
one growth at ground level and they root only in soil - rule 11 again - never on `Park Ways`'
paving.

##### Four faults, each of which shipped a design that audited perfectly clean

- **A VINE'S FLAGS NAME THE FACE IT CLINGS TO, NOT THE WAY IT FACES.** Written as the back of the
  side it grew from, **2,948 of 3,000 vines named a face with open air behind it** - and a vine
  hanging in air renders identically to one on a wall in every sheet this repo has. It is the one
  block whose connection flags are a DECISION rather than something the game derives
  (`work.MULTIFACE` exists for exactly this), so it is the one that can be silently wrong.
  `props[side] = "true"`, not `props[_BACK[side]]`.
- **A ROOF IS NOT A WALL.** The first build asked the WALL question about a roof, and this land's
  roofs are stairs and slabs, which cannot carry a vine and can perfectly well carry a carpet:
  moss landed on **486 cells of the ~35,000 it was aiming at** and reported a number. `ROOF` is
  derived through `blocks.supports_top` now, never typed out.
- **A WAY RUNS ALONG THE LOT'S LENGTH, AND THE LENGTH IS NOT ALWAYS V.** `claimrow._way` was
  written for the claim row, whose lot is 54 deep in V, so the walk was laid along V at a fixed U
  and nobody had to say so. Pointed at the rim - 13 in V and 98 in U - the same code laid a
  **3 x 13 patch instead of a 98-block cliff walk**: 38 cells where 294 were wanted, and it audits
  perfectly clean, because a patch of path is a legal path. `axis` is explicit and RAISES on
  anything else.
- **A SIGN LINE OVER FIFTEEN CHARACTERS CLIPS MID-WORD**, and this park has shipped that twice.
  The lookout's board asked for "nests on the top" (16) and the guard fired; it reads "nests up
  top". A width check at the point of placement is the only thing that catches it before a
  screenshot does.

##### TWO LAND-DRESSING PASSES ON ONE STRIP IS A CLASH NO SINGLE DESIGN CAN SEE

The ship reported the session's first clashes - `Overgrowth x Rim: 3 cells`, `Rim x Scatter: 1` -
and **every one of the three designs reported `overlap 0` against the world**, correctly, because
`finish.verify_against` audits against the CAPTURE and the capture does not contain the other two.
This is the casino's own recorded lesson at land scale: cross-design overlap is a DIFFERENT
question from world overlap and needs its own check, which `tools/park_place.py` is. Both
neighbours reserve the rim's box by name now.

##### Why a clifftop, and why a nest

The rim is the only band in the Frontier with real room and the only one against the void - and it
is **the part a guest is least likely to reach**, because it sits past the railway, which is
exactly why it gets a WAY rather than only scenery. A strip with things on it and no route to them
is a strip nobody sees; the sauropod was already out there and nothing led to it. The nests are
`gen/pterosaur.nest` - a scrape of the ridge's own rock with pale eggs in it - because a nest
belongs to the ANIMAL rather than to the ground, and an egg is a dome whose canonical view is the
PLAN: the ladybird's category, and the two reasons it works here. **The way runs at the band's
inner edge so the colony sits between it and the drop** - you walk past a colony rather than
through it.

##### And the tower had nothing in it

`PF Vantage Frontier Lookout` is 17.8 blocks per column and 56 courses tall - the densest thing in
its land - and carried **zero interactive blocks**: you climb it and there is nothing there. That
is the complaint Jack has now made of this park three separate times, and for an observation tower
the answer is not a game, it is the board that tells you what you are looking AT and the bell a
lookout rings. **The module is shared with Prismworks, so both are opt-in** - a shared generator
that changes under its other callers is a different bug.

##### Still open

- **Nothing here has been placed in game.** All of it is `render3d`, which draws with the same
  colour DB the palette picker optimises against - judge form and mass here, palette in world.
- **`render3d` draws a vine as a full cube**, so the one thing these sheets genuinely cannot judge
  is how heavy the overgrowth reads. The density is 0.16 because 11,855 vines was 92% of a first
  build and read as a curtain over everything; growth is a DRIFT, and the point is that some walls
  are taken and some are not.


#### EVERY SIGN IN THE PARK WAS BLANK, FOR A YEAR (2026-09-03)

Jack: *"I see hanging lamps in weird places and theres still no sense of what to do or why any of
its there."* The second half had a cause nobody had looked for.

**A sign is TWO THINGS IN TWO HALVES OF A LITEMATIC** - a palette entry and a tile entity - and
`park_place.merge` built a bare `schem.Model(ids, pal)`. Measured:

| | tile entities |
|---|---|
| `PF Front Frontier` | 16 |
| `PF Claim Lake Menagerie` | 19 |
| `PF Trailhead Gate` | 6 |
| `Park_Left Complete` | 29 |
| **`Park Buildings`** | **0** |
| **`Park Complete`** | **0** |

Every module wrote its signs correctly and **the one artifact anybody actually places dropped all
of them.** Nothing in the pipeline could see it: the blocks are right, the audit passes, the BOM is
right, `/cscan check` is happy, and **`render3d` draws a sign identically whether or not it says
anything.** The only symptom is a guest walking a park where nothing is named - which is exactly
the complaint, arriving three sessions after the signs were written.

**`layers.slice_plan` had it right the whole time** and states the rule the merge was missing: *a
tile entity whose block was won by another module is a tile entity with no block, which is a
corrupt region rather than a lost line.* So text travels only when its own cell survived the
contest, and `_shift_tile` REWRITES the coordinates rather than mutating the source - a module
merged into two composites in one run would otherwise carry the first merge's coordinates into the
second, which is a whole land's signs landing on the wrong blocks with nothing reporting it.

**And position alone was not enough.** Two tile entities landed on an `oak_log` and a
`stone_bricks` - a source design whose sign block had since moved while its text stayed behind,
which a litematic stores perfectly happily and the game reads as corruption. **The block at the
destination is the authority, not the coordinate.** `tests/test_park_signs.py` pins all of it.

    Park Complete signs carrying text:   0  ->  177

#### THE LAMPS WERE FINE, AND MY FIRST MEASUREMENT SAID THEY WERE NOT

Worth recording because the wrong answer was confident and nearly shipped a fix.

`Park Ways` **paves at Y202 and stands its furniture at Y203+**. Measuring lamp-to-street distance
on the Y203 course therefore measures the lamps against the MODULES' floors rather than against the
streets, and it reported *"11 of 35 masts 8 to 25 blocks from any paving"* - posts alone in the
grass. I wrote a `lamp_needs_street` gate for it, wired it into the config, regenerated, and it
**blocked nothing at all**: the debug counter read `gated 37, blocked 0`, which is the tell.
Measured on the real course, **every one of the 35 masts is exactly 2 blocks from a street.** The
gate was reverted.

**A guard that fires zero times on the case it was written for is evidence about the MEASUREMENT,
not about the world.** And the specific trap generalises: this park has three courses that all
look like "the floor" - the lawn at Y202, the build plane at Y203, and the modules' own floors -
and `tools/parkship.py` already says so in as many words. Read the course off the artifact.

#### The land's scenery was 88% of its mass and eight signs

The measurement that stands, over the shipped Lost Plateau:

| design | blocks | verbs | signs |
|---|---|---|---|
| Mine Coaster | 56,635 | 0 | 5 |
| PF Mine Ridge | 41,948 | 1 | 1 |
| PF Lost Plateau | 15,374 | 0 | 0 |
| PF Frontier Diggings | 5,577 | 10 | 2 |
| PF Frontier Overgrowth | 5,146 | 0 | 0 |
| PF Sauropod | 5,036 | 0 | 0 |
| PF Frontier Scatter | 2,215 | 3 | 0 |
| PF Pterosaur | 691 | 0 | 0 |
| PF Frontier Rim | 548 | 0 | 0 |
| **total** | **133,170** | **14** | **8** |

A guest walks past a forty-thousand-block mountain and a fifty-block dinosaur and is told nothing
about either. **That is not a shortage of content, it is a shortage of LABELS** - and this land is
the one theme where the label is also correct in-world, because a working dig labels its finds.

**`PF Plateau Plaques`** (`claimrow._plaque`, 47 blocks, 0 problems, 0 overlap, all cheap): seven
specimen posts - a stone footing, a stake, a board angled to the walk - naming what stands in front
of them and what a guest can do about it. **Every site is MEASURED, not chosen**: the nearest cell
to its subject's own centroid that is lawn, four courses clear and within two of paving. The three
that sit twenty-plus blocks from their subject are the mountain, the canopy and the pterosaur, and
that distance is the point - there is no walk up a mountain, so you read those at its foot.

Four things it cost, each a rule this file already carries somewhere else:

- **`mine` LAUNDERS A BAD CELL.** `_Ground.free` accepts a cell this design shipped last time,
  which is the honest answer to rule 15 everywhere else and exactly wrong for a footing: ship one
  slab over the street's stone and the design's own artifact reports that cell as its own progress
  for ever, so the collision can never be un-shipped. The footing asks the WORLD directly.
- **A COLUMN TEST IS NOT A CELL TEST**, one level down from where this file first recorded it.
  `lawn` asks whether the course UNDER the plane is turf - which it is right beside a street, whose
  own paving is in the cell the footing wants.
- **A DESIGN WITH NO WAY MUST BE ABLE TO SAY SO.** `_way`'s `max(1, w)` gave a width of 0 a
  one-cell walk running the whole lot: 67 slabs of path down a land for a design that asked for
  none, and **a one-wide path audits perfectly clean** because it is a legal path.
- **FIFTEEN CHARACTERS, and the generator RAISES rather than truncating.** This park has now
  shipped "MINE CART ESCAP", "and prize windo" and "ore from the ad"; the sign dump that found
  them was only possible once the composite carried text at all.

##### Still open

- **`MINE CART ESCAP`, `BOARD WHEN CLEA`, `CLEAR LINE EMPT` and `BOARD THEN PRES`** are real clips
  in the ride and transit signage, now visible in the shipped composite for the first time. They
  belong to those modules, not to this pass.
- **The scenery still carries 14 verbs.** Naming a thing is not giving somebody something to do
  with it, and the plaques are the cheap half. What the coaster, the mountain and the two dinosaurs
  should let a guest DO is a design decision rather than a defect.
- **Nothing placed in game.**


