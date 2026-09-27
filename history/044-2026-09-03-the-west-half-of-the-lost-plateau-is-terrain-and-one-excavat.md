## THE WEST HALF OF THE LOST PLATEAU IS TERRAIN AND ONE EXCAVATION (2026-09-03)

Jack, on the re-themed land: *"i feel like the frontier area, though it is now changed to jungle or
w/e its called now is still not good, its just buildings, the dig zone is crappy ... i like the
dinosaurs sculptures, i like the roller coaster, i just really dont like this splatter of buildings
that dont look amazing and dont really do anything."*

**EVERY HALF OF THAT IS A MEASUREMENT, AND ALL OF IT CHECKS OUT.** Over the shipped park:

| | blocks | verbs | |
|---|---|---|---|
| Mine Coaster + Mine Ridge + Lost Plateau + Sauropod + Pterosaur | **119,684** | | what he likes - **74% of the land** |
| Trailhead Gate | 4,260 | **0** | |
| Vantage Lookout | 4,154 | 1 | |
| Prospecting Porch | 3,499 | **0** | |
| Mining Square | 2,469 | **0** | |
| Assay & Prize Office | 2,248 | **0** | |
| Works Yard | 1,227 | **0** | |

**Six buildings, 17,857 blocks and ONE interactive block between them**, at 4.3 and 3.1 blocks per
column across columns A and B - 11,310 columns, 40% of the land's ground - against column C's 10.8,
which is the mountain and the coaster.

**AND THE RE-THEME WAS DONE ON THE TERRAIN AND NEVER ON THE ARCHITECTURE.** The ridge's own top
surface went 24% green to 71% and the camp below it stayed a gold-rush mining camp that had been
re-SIGNED for the jungle - THE SCREEN HUT, BASE CAMP, MATRIX TIP - and never re-BUILT. That is why
the land read as a rainforest standing next to a mining town, and it is why adding more to the
buildings could not have fixed it.

Jack's call, given the numbers: **terrain plus ONE big dig, and a single small arch for the front
door** - "no court, no towers, no stockade. The land's identity comes from the terrain behind it."

| design | blocks | what it is |
|---|---|---|
| `PF Plateau Vale` | 23,678 | column A: jungle downland, four trial trenches, and the arch |
| `PF Plateau Bone Bed` | 11,687 | column B: one excavation across two retired lots |

    column A   4.33 b/col -> 6.70,  45.5% of columns 3+ tall -> 73.1%
    column B   3.07 b/col -> 3.82,  44.9% -> 55.9%,  11.8% of columns 6+ tall -> 23.4%
    the land   48.1% of columns 3+ tall -> 55.0%,  27.8% 6+ -> 35.4%

Column B goes DOWN in blocks per column and that is the design working: an excavation is a hole,
and its 6+ band doubled because the spoil around it is real relief.

### A PIT IS A HOLE IN THE SPOIL, NOT A CUT

A litematic cannot express removal, so an excavation sunk below the plane would be a dig list a
hundred columns wide. It does not need to be: the floor stays at the park's own plane and the
ground is RAISED around it - `fossils.reserve`'s own trick at fifty times the size, and `downs.py`'s
"the shaft is a hole in a HILL". Twelve to fourteen courses of relief, nothing to break first.

**THE RECTANGLE A PIT DECLARES IS THE TOP OF THE HOLE, AND THE FIRST BUILD HAD IT INVERTED.**
Written with the rectangle as the FLOOR and benches stepping UP outside it, the wall came out as a
ridge that crested midway across its own bank and fell back to three courses at the lip - the exact
opposite of an open pit, and invisible in a plan. A pit's face is highest AT the edge and steps DOWN
inward, so the benches live inside the declared box.

**AND THE BOX IS ONLY THE BRIEF.** Built as its literal rectangle the north bay read in plan as a
swimming pool: four straight benched edges inside a green rectangular frame. The wobble is coarse
noise on the SIGNED DISTANCE to the box, which is the lowland thicket's own rule - *the noise
belongs on the drift's RADIUS, never on its interior* - arrived at from a new direction.

**RUN 1, RISE 4, NOT RUN 2 / RISE 3.** The bench zone eats the pit from both sides: at two cells of
tread a twenty-four-wide pit had sixteen cells of bench and eight of floor, narrower than the rib
cage that has to lie on it. One cell of tread to four of riser is what a worked quarry face looks
like at this scale and it leaves the floor eighteen wide.

### THE STREET IS THE WAY IN, NOT AN OBSTACLE

`Park Ways` runs a three-wide cross walk at V77-79 from U41 to U97 - measured, not assumed -
straight through this lot, and it must stay level. So it is not fought, it is USED: the walk arrives
at the pit's own floor course and becomes the causeway between the north bay (the excavation) and
the south bay (the working camp). **You do not look at this dig over a fence; the park's own path
delivers you into the bottom of it.**

The lot's four edges are level for the same reason (u0-1 the U41-45 avenue's verge, u44-45 the
U92-99 cross avenue's, v0-1 the spine band, v97-98 the V123-127 avenue) - and that is a geometric
CONSTRAINT rather than a style: with both u edges easing to grade, the bank between the avenue and
the pit lip is eleven cells, so its crest is `11 * slope`. At `downs.py`'s 0.62 that is six courses
and the gallery has nothing to stand on; at **0.85** it is nine, which is a real overlook, and it is
still under the 1.25 a player climbs.

### THE MONEY VIEW IS THE PLAN AND IT IS ON THE MAIN ROUTE

A dig is read from above - the one view voxels give away free, and the reason the ladybird and the
turtle work - so a timber gallery runs the crest of the avenue bank with the skeleton laid out below
it, railed on the pit side ONLY (a rail on the street side fences the deck off the avenue it is
entered from). **A DECK IS LEVEL AND THE GROUND UNDER IT IS NOT**: seated per column it stepped four
courses over its own length, which is a path up a hill; one course is taken for the whole run and
the posts make up what each column is short.

### Six things that shipped a clean audit and a wrong build

- **A SKULL IS LAID FROM THE SPINE'S LAST POINT AND NEEDS SEVEN CELLS PAST IT.** At length 40 in a
  pit ending at v52 the skull reached v52-58 and the bound clipped it to **THREE CELLS** - a
  450-cell skeleton with no head, which is the one part a stranger looks for, in a build reporting
  0 problems and a correct BOM. `fossils` records this trap from the diggings and it was hit again
  the moment a number moved. Only `skull.cells` in the sidecar can see it, so that is what the test
  reads. **And a thirteen-deep trench cannot hold a small one either**: three vertebrae and one pair
  of ribs is a scatter, not an animal, so the camp's find is a SKULL AND NECK - which is what a
  working trench has in it anyway, and what a gantry is rigged over.
- **A WORKING EXCAVATION GREW A LINE OF TREES DOWN THE MIDDLE OF ITSELF.** The benches are flat
  enough to hold soil, so they were turfed and then planted. Passes every check there is; makes no
  sense at all to anybody standing in it.
- **THE LAND'S SECOND RIDE STOOD INSIDE THE NEW LOT.** `PF Mine Cart Escape` is 23 x 26 of track at
  V98-120 / U66-91, sited when Mining Square held that ground, and the first build put **646 cells
  of excavation through it**. A ride is the half of this land Jack likes, so the pit gives way:
  `reserve` is ground another design stands on, and **RESERVED GROUND IS LEVEL GROUND** - the mass
  and the floor still form under a game, but a bank rising under half a ride is a ride buried in a
  hillside. Six cells of the causeway's own kerb landed inside a game's footprint too, which no
  audit can see, because a slab beside a console is a legal slab.
- **A TENT PITCHES ITSELF A PAD.** Seated on the height field at ONE corner, the shelter's bench
  came away as a four-cell free-floating cluster the moment the ground under its far side fell a
  course - which is what ground on a bank does everywhere. Levelling the footprint to its own lowest
  column is both what happens in the field and the only way every part of it is supported by
  construction.
- **`at` IS NOT THE MIN CORNER FOR A GAME.** Re-sited by hand, `PF Game Pan Line` and `PF Game
  Powder Striker` came out nine and thirteen cells off, because their anchor is a reference corner
  rather than the box's origin. The fix is not to guess it: build once, read the artifact's own
  world bounds, and derive the offset.
- **`jungle_log` IS NOT EVIDENCE OF A TREE.** It is also the camp's post - the gantry's legs, the
  shelter's uprights and every board - so the first version of the no-planting test failed on a
  correct build. A test that names the wrong evidence teaches the next reader the wrong lesson.

### What was retired, and the tests that had to move with it

Out of `tools/park_lots.PLACEMENT`: Trailhead Gate, Prospecting Porch, Mining Square. Out of
`park_place.EXTRAS_READY`: `PF Frontier Diggings` (5,577 - a 30x16 trench with a 25-block spine in a
53x46 lot, which IS the dig zone Jack called crappy; the bone bed is 99 x 46), `PF Frontier Claim
Row` and `PF Frontier Muster Yard` (ground dressing written to fill the holes the gate and the porch
left inside their own lots).

**THE ASSAY AND PRIZE OFFICE STAYS AND IT IS THE LAND'S ONE BUILDING IN THE WEST** - Jack: "we can
have a small amount of buildings". It sits north of the V123-127 cross avenue, a separate block from
the excavation, and it is where `PF Game Prize Office` lives, so retiring it would orphan a working
game to remove 2,248 blocks.

**THE OTHER THREE GAMES MOVED INTO THE CAMP.** `Pan Line`, `The Riffle` and `Powder Striker` were
built into the Prospecting Porch's bays and Mining Square, and **a game whose building is gone is a
game nobody can reach**. A washing line, a riffle table and a striker belong in a working dig camp
anyway.

**Two marquees went with the two buildings they named, and it was not only that they named
nothing:** THE SCREENS stood at V70 U20 and BASE CAMP at V80 U66, both deep INSIDE the lots the two
terrain designs now hold. A board on posts in the middle of a hillside is a clash, not a sign - and
the frontage is a threshold band, V20-22, for exactly this reason. The other two were retitled.

**And `tests/test_claimrow.py` skips its two build fixtures with the reason in the marker.** Both
retired designs read `Park Complete` for the ground they stand on, and the ground has moved: a claim
board's post no longer finds a level flat, so the board is correctly refused. That is the snapshot
trap this repo has now recorded five times - *a test that pins a design against a world it no longer
belongs to fails the moment the world improves* - and the generator is SHARED with `PF Plateau
Plaques` and `PF Frontier Rim`, so everything testing the module itself still runs.

### Still open

- **Nothing has been placed in game.** All of it is `render3d`, which draws with the same colour DB
  the palette picker optimises against - judge form and mass here, palette in world.
- **`PF Frontier Scatter` and `PF Frontier Overgrowth` now keep out of the whole west half.** Both
  terrain designs plant their own jungle and hang their own vines; two drifts on one hillside is the
  confetti failure this repo has recorded four times. What that costs is that the vale's planting is
  `bonebed._plant`'s and not `frontier_scatter`'s richer kit - snags, boulders, tipped ore,
  cross-piled timber. Widening the bone bed's dressing rather than re-admitting a second pass is the
  honest next step.
- **The Vantage Lookout is kept and untouched** - 4,154 blocks, 56 courses, ONE verb - and it now
  stands in jungle rather than beside a row of brown huts, which is an improvement it got for free.
  Whether a 56-course tower is what that corner wants is a separate decision.


