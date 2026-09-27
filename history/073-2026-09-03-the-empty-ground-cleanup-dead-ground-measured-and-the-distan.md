## The empty-ground cleanup: dead ground measured, and the distance IS the density (2026-09-03)

Jack: *"lets do a empty ground cleanup, we want to look and locate all available spaces, make
plans to deal with them or intentionally leave them, we can add shrubbery, flowers, or other
accents, or new objects if appropriate, be thorough."* `tools/park_empty.py`,
`mcbuild/gen/parkgreen.py`, `configs/pf_park_{green,rim_green}.yaml`, `PARK_EMPTY_GROUND.md`,
`tests/test_parkgreen.py` (21).

### NOTHING HAD EVER ASKED WHETHER THE GROUND BETWEEN THE DESIGNS WAS FINISHED

Every check this park has measures a design AGAINST the world - legal state, support, collision,
economy, circuit, connectivity - and **a bare lawn passes all of them, because a bare lawn is what
`Park Ways` is supposed to lay.** The gap only appears if you ask a different question, and this
project had already written the question down about the island: *"the plate has no dead ground -
every walkable cell is within 4 blocks of something built or planted, median 0."* It had never
been pointed at the park. Measured over the shipped composite:

    120,000 lattice columns . 28,023 BARE LAWN (23.4%) . 6,559 four or more from anything
    1,903 eight or more . 1,080 ten or more . the worst column in the park is THIRTEEN

    threshold 630 . public floor 837 . exit 398 . service 990 . RIM RESERVE 3,704

### THE DISTANCE IS THE DENSITY

Every land-dressing pass here so far - `frontier_scatter`, `thicket`, `claimrow` - uses a smooth
noise field, which spreads material evenly over ground that is **not evenly empty**: a two-cell
verge beside a kerb gets the same treatment as the middle of a forty-cell field. `parkgreen`
drives its density from the MEASURED openness of each column, so it puts its material exactly
where the hole is and leaves the verges alone - and the same distance transform finds the holes
and plants them, so the audit and the pass cannot be talking about different parks. Below
`open_min` nothing is placed at all; the drift's SIZE scales with the room as well, because a
dozen small beds in a forty-cell field read as spots on a lawn and three big ones read as
planting.

**Shipped: 5,490 blocks over two designs, 0 overlap, 0 new problems, 0 module clashes, all
cheap-or-ok. Dead ground 6,559 -> 1,346 (-79%), median 2 -> 1, mean 3.21 -> 1.93.**

### Three findings worth keeping

- **THE PARK'S OUTERMOST TWO COURSES WERE UNPLANTABLE BY CONSTRUCTION.** The front threshold V0-5
  measured as the third-largest hole in the park **with a dressing pass nominally covering it**:
  `frontier_scatter.clearing` refuses any candidate whose whole `path_clear` neighbourhood is not
  lawn, and past V0 there is no lawn because there is no lot. Every lot that stops at the plot
  edge has this. `_Green.clearing` treats out of bounds as sky rather than as a refusal, and
  `tests/test_parkgreen.py` pins the two behaviours side by side.
- **RULE 15 REACHES THE DENSITY, NOT ONLY THE GROUND PROBE.** `_Ground.mine` lets a pass re-plant
  its own standing work - without it `frontier_scatter` shipped at 428 blocks against 3,843 on its
  second run. The same failure arrives a second way through a MEASURED density: once shipped,
  `Park Complete` contains the pass, every column it planted reads as built, the openness under
  every drift collapses and the ramp plants nothing. `openness()` takes `mine` and puts those
  columns back to lawn first. Regenerated against the park that now contains it, the pass comes
  out at 3,676 and 1,814 - bit for bit what it was before the ship.
- **ONE DEFINITION, OR THE TOOL AND THE PASS MEASURE DIFFERENT PARKS.** The first draft counted a
  flower or a tuft as still-bare (dressing is what the audit exists to ADD) while `--with`
  counted a design's columns whatever they held. The two readings disagreed **by three thousand
  columns** on the same park - 1,305 dead cells before the pass was shipped and 4,443 after, with
  nothing changed but which file the blocks were in. A tuft counts: the standard is "built OR
  PLANTED". And `--with` composites BLOCKS now, exactly as the shipping pipeline does, so the
  measurement is identical on both sides of a `--ship`.

### A HEDGE IS ALSO A FENCE, AND NOTHING ELSE HERE WOULD SEE IT

A hedge is a legal, supported, affordable, non-colliding run of leaves; two courses of it across a
narrow lawn is a wall. The audit checks blocks, not routes. `park_empty.py --walk` floods the
park's standable surface with and without the dressing: **563 columns the planting occupies, 0 cut
off behind it.** A run shorter than four cells places NOTHING, which is the deck soffit's own gate
in leaves.

### What is deliberately left

- **THE RIM RESERVE V187-199** is 3,919 columns in one blob and holds every column in the park ten
  or more from anything - and `PARK_GRID_PLAN.md` declares it *"protected rim and void reserve - 0
  paved cells, asserted"*, for "support, terrain, void safety, sightline protection". PAVING is
  forbidden and TERRAIN is its stated purpose, and a rail rider on the viaduct is its one
  audience, so `PF Park Rim Green` takes it at a third of the density, **capped at three courses,
  with no trees and no hedges in its kit**. Drop it from `EXTRAS_READY` to leave it bare moss.
- **THE FRONTIER above V6** - five designs already dress that land, and two planting passes on one
  strip is the clash no single design can see. 479 dead columns left there on purpose.
- **THE VERGES** - 24,680 columns are still bare lawn and that is the design. A path only reads as
  a path if there is something it is NOT.

### Still open, and stated rather than quietly left

The front approach V0-5 / U270-330 is the first ground a guest walks on and now carries rough
meadow because that is what a sweep puts there; an avenue is the one place in this park where
formal beats naturalistic. **The Mine Ridge's own lot has a 158-column hole** at V100-134 /
U156-166, inside `frontier_scatter`'s keep-out and past the ridge's talus, so nobody owns it.
And nothing here has been placed in game - judge form offline, palette in world.

### The rim rookery: the strip behind the railway, and a walk under the dinosaur (2026-09-03)

Jack: *"what about the area behind the railway where the dinosaur is, that whole area needs to be
refined, i like the eggs and the idea of other small things there."* `mcbuild/gen/rookery.py`,
`configs/pf_frontier_rim.yaml`, `tests/test_rookery.py` (18). **3,982 blocks, 0 problems, 0 module
clashes, all cheap-or-ok.**

**THE MEASUREMENT IS ONE NUMBER.** The Frontier's rim is V187-199 x U0-172, split at the sauropod:

    sauropod end U0-70    923 columns . 57% carry something . tallest 50 . 504 over 6 courses
    colony end  U71-172  1,326 columns . 37% carry something . TALLEST 5 . ZERO over 6

**A hundred and two blocks of nesting colony with nothing over three courses tall**, at 0.6 blocks
per column - and this file already had the rule about this exact land: *"on this moss, under
ten-tall trees, architecture below ~6 courses dissolves into ground noise."* The old design (a
3-wide walk, four scrapes, two snags) was entirely under it. After: colony end **79% / tallest 14 /
287 columns over 6**; sauropod end 84%.

What is there: six **perch stacks** 9-14 courses, guano-capped (the skyline, and isolated COLUMNS
so they frame the void view the reserve protects rather than walling it); eight **nests, 19 eggs**,
some full and some HATCHED with the shell still in them, so the colony reads over a season rather
than as one photograph; three **hatchlings**; an **observation hide**; a **bone find**; a **cliff
rail** in gaps; and a railed **deck under the sauropod's belly**.

#### THE WALK GOES UNDER THE ANIMAL, AND THE LEGS DECIDE HOW WIDE IT IS

Measured off `PF Sauropod`'s own artifact at the ground course, the animal occupies **U28-32 and
U46-50 and nothing else** - two rows of feet, near leg V188-192, far leg V194-198, **V193 clear
straight through** - and U33-45 is thirteen blocks of open lawn twenty courses under a fifty-block
dinosaur, which was bare grass with nothing leading to it. So the middle walk segment is DECLARED
five wide and the feet carve it to one for three rows, twice; the squeeze is what the world gives
rather than something special-cased.

**NOTHING KEEPS OUT OF THE SAUROPOD BY BOX.** Its silhouette is 11 of the band's 13 courses, so a
keep-out would forfeit 63 blocks of strip. Every piece asks the ground probe per CELL as it rises
and a stack demands two clear courses over its crown, so the animal stops the tall things and lets
the low ones stand under it.

#### Five that shipped clean and were wrong

- **A WALK NEEDS HEADROOM, NOT SKY.** `_Ground.lawn` demands NINE clear courses - right for a tree,
  wrong for a path. The sauropod's legs merge into its barrel as they rise, so V193 is open at the
  ground and closed nine up: `lawn` refused it and put **a one-cell hole in the only route to half
  the strip**. `rookery.underfoot` asks the ground course and three courses of headroom instead.
- **A GATE IN THE WRONG WALL IS A WALL.** The belly deck's rail put its openings on the SIDES, so
  it ran a complete fence across both ends of the walk it stands in the middle of. Only a flood
  sees this: all 173 columns are reachable on foot now, and the test is a flood rather than a count.
- **BOTH OF ITS SIGNS WERE REFUSED IN SILENCE** - the hide's board written at the doorway's own
  column, which is the one column of that wall with nothing in it, and the deck's post landed in
  the cell its own sign then needed. Fifth time in this park.
- **A STRICT SUPPORT RULE CANNOT WIDEN A COLUMN**, so no stack ever grew a crown and every one came
  out a spike - a one-wide shaft with a white cap, which reads as a smokestack. **The crown is
  CORBELLED**: each course is laid centre-outward so a cell may lean on the one already placed
  beside it. Profile is a flared foot, a waist, and a head that overhangs it.
- **A SKELETON LAID FLAT ON MOSS IS A FLOOR DECAL.** The bones stand a course proud of a rock
  matrix now, with the ribs arcing off the spine.

...and one in the tests: counting "any solid cell" made the stack's waist read as **wider than its
foot**, because a jungle crown from the planting sweep hangs over the shaft at exactly that height.
That is the mane-measured-as-barrel error, in a different subsystem.

**A PIECE NEVER OVERWRITES A PIECE.** `Canvas.put` overwrites, so two footprints that touch corrupt
each other silently - a nest rim reappearing as the base course of a stack, with nothing in the
audit, the BOM or the component count to say so. The colony is laid BEFORE the skyline and the
skyline yields, because a scrape with eggs in it is the thing that was asked for.

