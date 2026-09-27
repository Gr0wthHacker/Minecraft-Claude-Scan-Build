## The Midway entrance: the walk-up from the gate to the wheel (2026-09-02)

Jack, arriving through it: *"gates and a board etc are all overlapping and chaotic with the
entrance to the main center ... carefully just work on making the entrance experience, and the
leading park in front of it before the ferris wheel and surrounding area perfect, highly detailed,
sophisticated, no weird blocks, or overlaps, no bad placements ... we need this to feel premium and
clean"*, and then *"this court also fits the theme of the center island area, and fills the space
nicely, we dont want immediate large amounts of empty green."*

**EVERY ONE OF THOSE WAS A REAL, MEASURABLE DEFECT AND NOT ONE OF THEM FAILED ANY CHECK.** The
designs audited clean, reported zero placement problems, zero overlap and zero clashes, and the
assembly reported `module clashes: none`. Measured off `out/Park Complete.litematic`:

    V13-18   PF Entry Gate       61 wide, towers, a portico, titled THE MIDWAY
    V19                          ONE CELL of lawn
    V20-22   the Circus Gate     41 wide, fifteen courses, titled MIDWAY CIRCUS
    V23                          ONE CELL of lawn
    V24-74   the Welcome Court   the walk-up itself

Three monumental things inside twenty-four courses, all announcing the same land, on the one
sightline the whole park is composed about - the entry gate's two doors, this court and the Sky
Lift's hub are all on U300, and the wheel's densest column IS U300 with 435 cells against 375 at
each neighbour.

### THE AXIS EXISTED AND NOTHING WAS USING IT

- **The Circus Gate is removed**, not moved. It was sited when the gate's lot was six courses deep
  and the axis was open ground; the gate grew to nineteen for the walk-up Jack asked for and this
  was never re-measured. A visitor who has just walked through a gate that names the land should
  meet the vista, not a second gantry two blocks behind the first.
- **Two `Park Ways` apron masts stood IN the walk** - V4/U300, dead centre of the forecourt, and
  V20/U298 between the gate's back face and the court's step. Each is a five-wide timber crossbeam
  at head height. The first was DELIBERATE once: it stood inside the old portico as the gate's own
  lamp, and the docstring still said so twelve blocks after the gate moved away from it.
- **`parkways.keep_clear` is the fix, and it is a different instrument from a `feature_lot`.** A
  feature lot refuses PAVING too, and the approach walks on the spine's own stone. `keep_clear`
  refuses furniture and nothing else. **The whole five-cell arm spread is tested, not just the
  post**: at the post alone a mast one cell outside a walk still hangs a lantern in the middle of
  it, which is how the second of the two came to stand where it did.
- **The Arrival Court's marquee was titled WELCOME COURT** and stands forty-five blocks from the
  Welcome Court, on the far side of the entry gate.

### THE COURT, REBUILT - `midway_builds._welcome_court`

What was there, measured rather than described: 4,613 blocks paved edge to edge on one
world-aligned grid, eleven trees of four species at eleven positions nothing derived, nine
`magenta_wool` and fifteen `light_blue_wool` cells with no other member of their colour near them,
and lamp standards whose head course was **a `yellow_wool` block** under a lantern on twelve
courses of oak. That is the "crappy lamp posts with yellow wool tops" exactly.

    the great walk   U294-306, V24 to V74 - thirteen wide, the spine's own width
    the roundel      r=13 on (V49, U300), where the walk opens out
    the basin        a stepped stone fountain: an eleven-wide pool, a plinth, an upper basin
    two pavilions    V43-55, open, on timber posts under a striped canvas roof
    four parterres   kerbed, hedged, planted - DERIVED, see below
    twelve standards a dark plinth, a stone base, a wall shaft, a dressed head, ONE lantern
    four masts       red and white pennants on the roundel's diagonals
    four swags       bunting across the walk, evenly spaced

**THE LOT WENT FROM 41 WIDE TO 61.** The two flanks either side of the old one measured **714
columns of bare moss each** and nothing else, in full view of the gate - which is precisely the
"immediate large amounts of empty green". At U270-330 the court has exactly the entry gate's own
frontage, so the two read as one composition rather than as a gate with a smaller thing behind it.

**EVERY PATCH OF LAWN THE COMPOSITION LEAVES BECOMES A PLANTED BED, DERIVED.** Hand-placing four
beds answers the question only where somebody remembered to, and it answered it for the 41-wide lot
and not for the 61-wide one - which is how the flanks came to be bare in the first place.
`_parterres` floods whatever the walk, roundel, pavilions and queue do not take, and every
connected piece over 36 cells gets a kerb, a clipped hedge on it, and planting on **a lattice
anchored on the court's own centre**. Anchoring on (mid, axis) rather than on each patch is what
keeps it symmetric: two mirrored patches get mirrored trees because the lattice is mirrored, and
nothing is typed twice. A tree is planted only where its whole crown fits inside the patch - the
check a render cannot make, because a leaf over a kerb draws exactly like a leaf over moss.

**THE WHEEL'S QUEUE OWNS THE WEST REAR CORNER AND THE COURT DOES NOT TOUCH IT.** Measured off
`out/PF Front Midway.litematic` it is exactly V65-74 x U270-279 - fifty-four columns, a clean ten
by ten - and it is named in `blocked`, so wanting one of its cells raises rather than shipping as
an overlap nobody can see.

### Six things that shipped a clean audit and a wrong build

- **A SAG IS NOT 6-CONNECTED UNLESS THE STEP IS FILLED.** The bunting dipped one course in the
  middle and the dipped cells were diagonal to their neighbours: four five-cell swags shipped as
  free-floating clusters. The ear-tip rule, in fabric.
- **THE SWAG OVERWROTE THE LAMP IT WAS STRUNG BETWEEN.** Run to the standards' own columns rather
  than between them, it replaced the lantern that is the whole point of a standard - four of them,
  silently. **A lamp that is missing is invisible in a render; a lamp in the wrong place is not.**
- **`_dir` TAKES A UNIT STEP, NOT AN OFFSET.** `_dir(-2, 0)` is a `KeyError`, which is the good
  case; the bad one is a corner cell of a flare, which faces two ways where a stair faces one and
  has to be a slab or it leans along whichever axis was written first.
- **A HALF-AND-HALF CHECKER IS A CHESSBOARD, NOT A FLOOR.** `stone` and `smooth_stone` are 33 apart
  in luminance - a pattern, not a texture - so the light one is the field and the dark one is a
  grid in it every four, measured from the court's own centre.
- **A BASIN IS SEEN INTO, AND THAT SETS ITS HEIGHT AT ONE COURSE.** Two courses with a dressed rim
  measured beautifully and rendered as a dark stone drum: a walker's eye is 1.6 over their feet,
  the rim stood at 2.0 and the water at 1.875 behind it. One course puts the surface below the eye
  from three blocks out.
- **A STEPPED PLINTH, NOT A BOWL ON A STEM.** A 1x1 stem carrying a 3x3 bowl read at walking
  distance as a grey box on a post - the stair flare meant to join them is one course and
  disappears past ten blocks.

### AND A COORDINATE BUG NOTHING IN THIS PIPELINE COULD SEE

`park_entrance._world` did not add `_Lot.front`, so **every world coordinate the entry gate
published was thirteen blocks west of the block it named**: the sidecar said the till stood at
X97504 and the hopper is at X97517. The build audits clean, the circuit simulates, the containment
floods, and a render draws the machine exactly where it is. **The one consumer that cannot look is
the SERVER PAYMENT ADAPTER**, which is handed those numbers to debit a fare against.

### The tests changed with the decisions, which is the rule

- **A fixture that pins a snapshot fails the moment the design improves.** `park_band` excluded
  `0 <= v <= 5`, which was the whole lot when the composition was six deep; `Park Complete`
  correctly contains this gate now, so it collided with the candidate over its own thirteen new
  columns and reported **2,866 overlaps against itself**. It derives the lot from the generator's
  own defaults now. Two more tests hard-coded V5 and V2 for the back face and the cornice.
- **A CORRIDOR TEST IS NOT A SIGHTLINE TEST.** `the assembled midway axis stays clear until the
  ferris wheel` demanded that eighty-six courses of the park hold no block at all in two courses -
  which forbade the fountain Jack asked the centre for, forbade the gate's own doors, and read the
  courses ABOVE a walker rather than the two a walker occupies. It is two tests now: **the walk**,
  which follows the surface a course at a time and allows the one-course step every lot in this
  park stands on, and **the view**, which is a ray from a visitor's eye to the wheel's hub and
  stops at the wheel's own face.

### ...and then it was a cul-de-sac (2026-09-03)

Jack, on the finished court: *"it needs to have paths or ways to connect to the other pathways
surrounding it otherwise its disconnected and not an actual welcome."* Measured off the shipped
ground he was right three times over, and every one of them is the park's OWN grammar not being
used rather than a new thing being needed:

- **THE SPUR WAS THREE CELLS WIDE AND ONE OFF THE AXIS.** `spurs` had a hard-coded `spur_half = 1`,
  so every door in the park got three cells whatever stood behind it - and the entry gate's
  portico, this spur and the court's threshold are the SAME DOORWAY, thirteen wide. `half` is per
  entry now and the court's is 6. Its `u` was 301 as well, against an axis of 300, so the one
  connection on the park's centre line was a garden path laid off-centre across the mouth of a
  triumphal arch.
- **THE MIDWAY'S CENTRE COLUMN HAD NO CROSS WALK.** `walks` already exists, already runs avenue to
  avenue, and its own comment already says *"A WALK MUST TOUCH THE STREETS AT BOTH ENDS OR IT IS
  NOT A WALK"* - and column B was written off as "130 deep, one ride" when the Carousel stood over
  the Sky Lift. The front 56 of it is the Welcome Court now, its flanks faced 714 columns of lawn
  each, and the avenues at U260 and U341 lay beyond them with nothing joining the two.
- **IT IS DECLARED OVER THE TWO GAPS, NOT ACROSS THE COLUMN.** The court's own cross axis is paved
  between them - a roundel with a pavilion at each end - so a street drawn through it would be a
  second surface under a finished one, which is the thing this park was rebuilt to stop. Each half
  overlaps the avenue it joins and finishes on the court's kerb.
- **AND THE PAVILION HAD A POST IN THE DOORWAY.** Its post rhythm is every three from its own
  corner and its centre landed exactly on the cross axis. A pavilion standing on a walk has to be
  something you go THROUGH, so the centre bay is left open on that axis.

**THE TEST IS A WALK, NOT A LOOK.** `test_the_welcome_court_is_reachable_from_the_spine_and_from_
both_avenues` floods the finished park on foot - one course up, one down, four ways, no jumps and
no falls - and demands the walk's head, its foot at the wheel and both pavilion openings, then
floods again from each avenue and demands the walk. A kerb, a post or a one-course ledge fails
here rather than in game.

**IT STARTS BEHIND THE GATE'S DOORS AND THAT IS NOT A DODGE.** Flooded from the spine it cannot
get through at all, correctly: U300 is the grille BETWEEN the two lanes and the doors are shut at
rest, because this is a toll gate. `test_park_entrance.py` owns the question of whether a visitor
could have got that far without paying; this one owns where they can go once they have.

### Where it stands, and what is left

`Park Complete` is 352,900 blocks, `module clashes: none`, the court is one connected piece with 0
placement problems and 0 leaks, and all 32 entrance tests pass. Nothing here has been placed in
game, and colour is still judged by the same database the palette picker optimises against - so
judge form here and palette in world. `tools/entview.py` renders the named plan-coordinate views
this pass was worked from; **its eye heights are h2, because a camera at h5 is three courses over a
player's head and renders the bunting as a wall across the view.**

**Still open, and deliberately not touched:**

- **The `Park Ways` midway street lamp is unchanged** - a dark-oak fence shaft under a five-wide
  slab crossbeam with two hanging lanterns. It is the only dark-oak furniture in a land of smooth
  stone, white and red, and it reads heavy. It is also the shape Jack himself specified ("we only
  need the slabs with 1 chain where the oak connects to the lamp"), and changing it is a park-wide
  decision about all three lands rather than an entrance fix.
- `tests/test_parkways.py::test_every_build_the_park_owes_has_a_lot_that_holds_it` fails on
  **Wyrm's Crossing (58x44 in a lot that holds 1x0)**. Pre-existing, and it is the 39,504-block
  skull another stream is siting.

### The court, third time: a grand fountain and a floor with no rings in it (2026-09-03)

Jack, on the formal version: *"nah this is shite, we have a center fountain, and then it just leads
to a bigger fountain, this feels crappy, we need something else to fill this space even if its
funky design, fields of flowers, whatever"*, then *"the court should have a large fountain ideally
sophisticated/intricate of stone(s), and then the trees/flower areas are cute with the pagodas on
the sides etc, but we need to have enough interesting visually and walkable space etc that covers
entrance all the way to the path before the ferris wheel"*, and *"make sure we get rid of the other
fountain there, we should only have 1."*

**"A CENTER FOUNTAIN THAT LEADS TO A BIGGER FOUNTAIN" WAS TWO SEPARATE THINGS, BOTH TRUE.**

- **The floor.** A blue basin inside a stone ring inside a red-and-white ring inside another stone
  ring can only read from above as a second, larger fountain drawn round the first. Every band on
  that floor was concentric on the basin, which is the one thing it must not be.
- **The park.** Measured, the Midway held exactly two water designs and both were on U300: this
  court's basin at V51 and the **Midway Cascade** at V80-116, forty blocks behind it. Walking in
  through the gate you met one and then the other.

#### THE FLOOR IS RADIAL AND HAS NO RING ANYWHERE IN IT

Sixteen spokes from the fountain to the lot's own kerb, running straight across the great walk
rather than stopping at a roundel's edge.

- **A SPOKE IS A CONSTANT WIDTH, NOT A CONSTANT ANGLE.** Drawn as an angular slice it is a wedge -
  two cells at the hub and nine at the lot edge - so sixteen of them meeting in the middle is a
  dark blot with a scalloped edge. The test is the PERPENDICULAR distance from the ray.
- **AND IT HAD TO BE THE WHOLE FLOOR.** Confined to the ring of paving between the basin and a
  r=15 rim, the spokes had FOUR CELLS to run in and came out as sixteen dashes. A grand fountain
  is nineteen across; there is no annulus left to pattern, so the pattern is the court.

#### THE FOUNTAIN: NINETEEN ACROSS, TEN COURSES, FOUR STONES, WATER AT THREE LEVELS

A dark blackstone kerb, a stone-brick body, chiseled at every step, a diorite bowl. **"Intricate"
at voxel scale is where one material stops and another starts**, not detail inside a material - so
each tier is a different stone and reads as a separate piece. A sitting ledge of slabs one ring
outside the wall, a plinth stepped 5-4-3 with a stair moulding at each step, a lower bowl with the
stem rising through its water, a cantilevered upper bowl, and a lantern on the finial.

Every water cell is enclosed BY CONSTRUCTION - the shell rule for the wall, a solid course under
each pool, a ring of its own stone at each bowl's level. **A fountain that drains is the one
failure this cannot be looked at to check.** Its height is bounded by a MEASURED sightline: the
ray from a visitor's eye at the gate to the wheel's hub passes Y222 over this cell and the finial
stands at Y213, which `test_the_wheel_is_visible_from_inside_the_gate` re-derives.

#### THE GROUND RULE INVERTED: A PAVED COURT WITH GARDENS IN IT

It was a formal garden with paths through it - four beds filling the quadrants - so of 3,416 cells
barely a third could be stood on. Everything is walkable now except four corner beds, the two
pavilions and whatever `blocked` reserves. The paving carries twelve lamp standards, eight benches
on the fountain's rim, four raised planters, four masts and four bunting swags, because a big paved
court with nothing on it is a car park.

**AND THE BEDS ARE A PINWHEEL.** Radial wedges measured from the COURT'S centre rather than each
bed's, so the four together are one pattern about the fountain. Radial for the same reason the
floor is: concentric colour would have made the ring mistake four times larger. Six degrees a
wedge - at twelve a bed only ever caught one or two and read as a block of colour with a hedge
round it.

**THE BOLD HALF IS WOOL AND THE PLANTED HALF IS FLOWERS, and that is about what can be JUDGED.**
`render3d` draws every block as one flat RGB and a flower's texture is mostly transparent, so the
database has `poppy` at (129,65,38) - the average of a red petal and a green stem over empty
pixels. A bed of poppies renders here as brown-green mush and reads scarlet in game. Wool reads at
any distance in either place; the flowers are planted in the moss wedges between it.

#### THE CASCADE IS WITHDRAWN FROM PLACEMENT, NOT DELETED

The court's fountain is the one that stays, because it is the one Jack asked for by name in the
same breath. The Cascade's config and its 2,096-block artifact are untouched on disk, because it
was built against a DIFFERENT instruction - *"move the wheel back and lets fill the area between
with something more interesting ... it should instead be a big water fountain sculpture"* - and
whoever owns that band needs to see what was there before choosing what replaces it. **V80-120 x
U266-336 is empty ground now and that is 41 by 71 of it.**

The Sky Lift's own 171 water cells at V134-147 are NOT a third fountain: they are a column 48
courses tall standing on soul sand, which is the bubble lift that carries riders to the wheel.

#### A GENERATOR THAT HARD-CODES ANOTHER DESIGN'S FOOTPRINT CANNOT BE TOLD WHEN IT MOVES

The court reserved the Sky Lift queue's corner as a literal - V65 to the lot's end by the first
ten columns. The wheel moved from V80 to V130, its queue went with it, the config's `blocked`
entry was correctly removed by the stream that moved it, and the literal stayed: a ten-by-fifteen
hole carved out of a court for something fifty blocks away. **NOTHING REPORTS THAT - a cell nobody
built looks exactly like a cell nobody wanted.** It reads `blocked` now, so the config is the one
source and the two cannot disagree.

Found the same day and worth the same note: `out/PF Front Midway.litematic` still held the queue at
the OLD address because that stream had edited its config without regenerating it, and the court
clashed with a queue that no longer exists in its own config. **A config change is not landed until
the artifact is rebuilt.**

### The Midway Row: the land was called the Midway and had no midway (2026-09-03)

Jack: *"lots of empty space still between the court now and the ferris wheel, we need to fill that
gap somehow."* Measured off the shipped park, **V80-122 x U264-337 was 3,180 columns of bare lawn**
- forty-three deep by seventy-four wide, bigger than most lots here - and it existed because the
water feature that filled it was withdrawn when he asked for one fountain rather than two.

So the filler could not be water, and the pass before this one had already ruled out more lawn.

**A MIDWAY IS NOT A GARDEN OR A PLAZA.** It is the strip of stalls and sideshows you walk BETWEEN
on the way from one ride to the next, and this park had counters at its edges - the Snack Window at
U235, the Prize Point at U348 - and nothing at all on its own centre line, which is the one piece
of ground every visitor crosses. `configs/pf_midway_row.yaml`, `midway_builds._midway_row`: 5,383
blocks, one piece, 0 problems, 0 clashes.

    the avenue     U294-306, V80-120 - the Welcome Court's own walk, carried to the promenade
    eight stalls   four a side facing each other, each with its own trade and its own sign
    two terraces   U270-282 and U318-330 behind the rows: trees, benches, somewhere to eat
    the bunting    strung across the avenue in every gap, on its own pair of posts

**THE VISTA SURVIVES IT.** Nothing stands in the avenue, so the line from the entry gate through
the court's fountain still ends at the wheel's hub - which is now 122 blocks from the doors rather
than 72, and reads at 31 degrees of elevation rather than 46.

#### Three things it shipped wrong first, and all three are about the GAP

- **PITCH IS WIDTH PLUS THE GAP.** At pitch 9 and width 8 there is no gap: stall k ended at a+8 and
  stall k+1 began at a+9, so four booths a side came out as one continuous terrace. **A row of
  shops with no space between them is a wall**; the space is what makes it a street.
- **AND THE BUNTING WAS STRUNG WHERE THE ARITHMETIC SAID THE GAP WAS**, which was the roof of the
  next stall along. With the pitch fixed it had nothing to hang from instead - the gap is exactly
  where there is no awning - and three swags shipped as three free-floating thirteen-cell
  components. A line needs two ends, so each gap carries its own pair of posts.
- **A GUARD COVERS THE GROUP, NOT THE THING IT IS WRITTEN NEXT TO.** The terrace's keep-out check
  tested the TREE's four corners and passed; the two BENCHES three courses behind it landed in the
  wheel queue's ground. Four cells, and the only reason they were caught is that `blocked` raises
  rather than dropping them.

#### The queue was standing in a garden, and a composite's origin is nobody's constant

Jack: *"theres some left over queue pieces or something strange on the left corner of the court
right near the ferris wheel."* They were not leftovers. The Sky Lift's line runs down this lot's
west flank at V108-123 x U269-279 on its way to the ride, and the Midway Row laid a seating
terrace the whole depth of that flank - so a fenced queue and its red-and-white canopy stood in
the middle of a lawn with trees, which is exactly what "strange" looks like.

- **THE GARDENS STOP AT V105 AND THE BACK OF BOTH FLANKS IS PAVED.** The west lane is what the
  queue stands in, which is what a queue should stand in; the east mirrors it as an open apron
  onto the promenade, so the two read as a pair rather than as one garden with a fault in it.
- **AND THE RESERVED GROUND IS KERBED.** This design may not place a cell inside `blocked`, so the
  queue stands one course below the row's own paving on the ground layer's lawn - and an unedged
  hole in a paved lane reads as a trench. The court frames its own reserved ground the same way.
- **A GARDEN THAT IS SYMMETRIC EXCEPT WHERE SOMEBODY ELSE'S DESIGN FALLS READS AS A MISTAKE.** On
  the stall pitch the third tree group sat at V105 and its crown reached V107, one cell short of
  the queue's ground, so the guard correctly refused it on the WEST side only and the terraces
  came out with three trees and two. They run on their own rhythm now.

**AND A COMPOSITE'S ORIGIN IS A FUNCTION OF THE DEEPEST THING IN IT.**
`tests/test_park_entrance.py` had `PARK_ORIGIN = (97500, 190, 80300)` typed as a literal. The day
another stream placed an underground design in the Prismworks, `Park Complete`'s y went **190 ->
94**, every lookup in that file was ninety-six courses out, and eight tests reported that a
visitor spawns with no ground under them - a containment failure that was entirely the test's.
The x and z are the park lattice's own anchor and never move; the y is nobody's constant, and it
is read from the sidecar now.

