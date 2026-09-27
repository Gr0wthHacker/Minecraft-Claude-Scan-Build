## The Ankylosaur: the quadruped that does not decompose (2026-09-07)

`configs/isthmus.yaml` (the Frontier Reach's first stop), `mcbuild/gen/ankylosaur.py`.
**2,300 blocks, one piece, four feet, 0 clipped, 0 asymmetric, all cheap-or-ok.** Chosen off the
full candidate field rather than by taste: of thirteen dinosaurs, it is the one whose OWN ANATOMY
is the shape that survives here - a low armoured shield with the legs tucked under it, so the
silhouette never breaks into posts however it is lit or turned. It is not a stegosaur with better
smoothing; it is the animal that does not need the smoothing to rescue it.

Everything below found a defect that shipped a clean audit, a correct bill of materials, one
connected piece and a plausible render.

### THE PART COUNTS WERE `put()` CALLS, AND MAKING THEM CELLS FOUND TWO MISSING FEATURES

The squid's own recorded lesson - *"the sidecar reported 251,264 arm blocks in a 116,000-block
animal, which reads as a measurement"* - was applied here on the way past, and it paid for itself
inside a minute:

    spikes 1440 -> 118    head 1479 -> 114    HORNS 124 -> 0

**The horns placed 124 blocks and gained ZERO cells: they were entirely inside the skull.** Rooted
at a computed half-width rather than on the surface the relax pass actually left, they were the
frog's `forelegs: 0` exactly - a build with a part missing is still one piece with a clean audit -
and no call count could ever have shown it. `loft.surface_out`'s rule, which has now cost this
project a mane, a pair of ossicones, a tail that floated 45 cells clear and a pair of horns.

### FOUR MORE FEATURES THAT HALF-EXISTED, AND THE SWEEP IS WHY THEY ARE NOT SHIPPED

- **THE CLUB WAS A ONE-COURSE PADDLE BELOW LENGTH 34.** Its radii are fractions of the length, and
  a fraction goes under one cell long before the animal stops being buildable: at 26 the vertical
  radius is 0.73, `ball` fills a single course, and the club came out THINNER THAN THE TAIL
  CARRYING IT - at two lengths out of five, and not the one that was being looked at. Radii have a
  floor in BLOCKS now. It is `MIN_BLOCKS` said again: **a feature below its own legible size does
  not shrink gracefully, it stops existing.**
- **THE SKULL CAME TO A POINT.** The head is built as MASS, so the relax pass runs over it - and it
  fills a narrow trough and shaves a thin tip, so a deep pinch and a fine taper bought a defect at
  both ends: measured, the last five stations ran 7, 5, 5, 3, 1 and the animal had a SNOUT. An
  Ankylosaurus skull is famously wider than it is long. The taper stops short of the tip and a
  flattened wide ellipsoid caps it, which is what a beak is, and the pinch is shallow because a
  deep one is filled anyway. **Which primitive a part is, not what number it is set to.**
- **THE TAIL WAS A STUB, AND THEN A LOLLIPOP.** At 0.115 of the length past the rump the profile
  silhouette read as an armadillo; lengthened to a real 38% and left thin, it read as a THREAD
  WITH A LUMP ON IT. A club has to look carried, not hung, so the tail leaves the hip at nearly
  the rump's own girth.
- **AND THE KNOBS WERE POLKA DOTS.** In the PLAN - this animal's money view, and the one voxels
  give away free - a field of stark `bone_block` osteoderms on a brown back is a regular grid of
  white spots. The row-stagger test passed the entire time, because **staggered dots are still
  dots**. They are `dripstone_block` now, 33 of luminance over the back rather than 146: a raised
  bump catching light rather than a rivet. That leaves the bone to mean exactly one thing, which
  is the features that stand PAST the animal's outline - the fringe, the horns and the club. The
  frog's rule read backwards: *a mark that means something different is a different block*, so a
  mark that means the SAME thing must not be.

### Three test faults, and one of them deleted two tests silently

- **A MIRRORED PAIR OF ROWS IS NOT TWO ROWS.** The knob-lattice test keyed on the COLUMN, and this
  animal is exactly symmetric - so the row at +0.46 of the half-width and the row at -0.46 carry
  identical stations by construction, and every correct build failed for being a lattice. It is
  keyed on the distance from the spine.
- **A KNOB SITS ON THE BODY AND A SPIKE STANDS PAST IT.** Masked as "armour above the belly" the
  fringe came in too, and the fringe runs every station of the rim. The two are told apart by what
  is UNDER them, which is what they actually are.
- **TWO OF MY TEST NAMES COLLIDED WITH THE STEGOSAUR'S AND PYTHON SILENTLY SHADOWED THEM.** The
  count stayed at 65 while I added three tests, which is the only reason it was caught -
  `test_it_survives_EVERY_LENGTH_it_can_be_built_at` defined twice in one module is not an error,
  it is two deleted tests. **A suite's own collected count is evidence and should be read.**

### THE FACE WAS THE ONE THING NOTHING TESTED, AND IT SHIPPED AS A THUMB

Jack, on the finished animal: *"the face sucks."* It did, and the head had passed every geometric
contract this file had written for it - blunt, wide, a run of stations narrower than the shield,
carrying a pair of eyes, symmetric. **All of those are true of a smooth brown lump.** A face is a
DRAWN feature and nothing was asserting the drawing.

- **THE SURFACING PASS WAS RUNNING OVER THE MUZZLE.** `shell.py` chamfers a step by replacing the
  cell with a stair of the nearest colour, and on the head it picked a green-grey slab and an
  orange stair out of the coat's own colour families - so the face was a staircase in three tones
  nothing else on the animal uses. The frog states the rule for its own build - *only the skin,
  and only single steps; the face, the belly, the eyes and the feet are drawn features and a stair
  through one of them is a hole in a drawing* - and it belongs in `_skin` rather than in each
  caller, or the next pass added here forgets it.
- **THE EYES WERE ON THE SKULL ROOF.** Walking down from the crown for the first course carrying a
  pair puts the beads on TOP of the head, where no bearing but the plan can see them. An eye
  belongs on the skull's front corner - visible head-on at the silhouette's edge and in profile -
  and that is where a real one is.
- **AND THE HEAD HAD NO MOUTH.** The frog's own recorded finding is that five passes of eye work
  went into a front that was a pale rectangle and what fixed it was ONE DARK LINE across it.
  `_face` draws four marks: a pale keratin beak on the front cap, that line where the jaws meet
  and carried three stations back along each jaw, two nostrils, and the bead.

Five things it cost, in order:

- **A BEAK IS THE FRONT CAP, ONE CELL DEEP.** Painted as every cell of the front three stations it
  is not a beak, it is a grey HEAD - 84 cells, and the animal came out with a robot's face. It is
  FOUND (the frontmost solid cell of each line through the skull) rather than filled: 8 cells.
- **A MOUTH IS ONE COURSE.** Laid on the lowest cell of every beak column it read head-on as a
  black cavern under a grey mask.
- **A DRAWN FEATURE MUST NOT REPAINT ANOTHER ONE.** `Frame.put` records `fixed` and does not
  enforce it, so the beak pass would happily paint over an eye - and an eye that has been painted
  out is a build with a part missing that audits perfectly clean.
- **THE EYE MERGED WITH THE MOUTH.** The jaw line runs back along the cheek, and at 0.30 down from
  the crown the bead landed one course above it: two black cells touching are one black blob,
  which is the axolotl's *"a two-cell bar, not a bead"* and the frog's sunglasses arrived at from a
  third direction. Two courses of hide between them.
- **A NOSTRIL IS NOT BLACK AND IT IS NOT THE FACE'S OWN TONE EITHER.** Black, two of them under two
  black pupils read as a second pair of eyes - the frog shipped exactly that. Moved to the head's
  own `dripstone_block` they were invisible, and reported 2 while placing nothing anybody could
  find. They are the back's brown on the face's dripstone: 33 of luminance, a dimple.

**AND THE FACE MOVED THE ANIMAL'S SIZE FLOOR.** `_eyes` began raising at length 26: the relax pass
leaves a skull one course tall there, which cannot hold a bead either side of a midline. Two bugs
came out of chasing it - a pinned eye STATION (at 26 and 30 the skull is one cell wide at the
corner, so it must search back toward the cheek and take the frontmost station that carries a
pair), and a course range whose start fell BELOW its own floor, so `range(1, 1, -1)` was EMPTY and
**a loop that cannot execute looks exactly like a loop that found nothing.** With both fixed the
floor is a real one and the declared minimum is **28**, not 26: `tools/scale.py`'s doctrine is that
an animal's critical size is the largest of its features' own floors, and the face is now one of
the features.

`test_the_face_is_DRAWN_and_reads_head_on` and `test_the_SURFACING_pass_keeps_off_the_face` are
what stop it going back. Two of that first test's assertions were weaker than they looked and both
are worth keeping as a shape: **"the outermost black cells are the eyes"** picks the mouth's own
jaw line about as often, so a bead is defined as black with no black above or below it; and
**"the bead is not the top of its column"** fails a correct build, because at the skull's tapering
front corner it is both the top of its column and on a side face - and the side face is the whole
reason it reads. The property is that it faces OUTWARD.

### The visual audit: eight bearings, a value panel and a distance ladder

Rendered rather than reasoned about, and it found three things - one of which is a defect in
`gen/shell.py` that every future animal would have inherited.

**THE TAIL WAS 23% OF THE ANIMAL WHERE A REAL ONE IS ABOUT 38%.** Counted off the built model
station by station: head 8, body 24, tail and club 10. The profile silhouette read as a hedgehog
or an armadillo, because **the club is the feature that names this animal alongside the armour and
a club needs a length of tail to be on the end of.** At `tail_f -0.560L` and `club_f -0.610L` it is
32%, which is what a stranger reads as a clubbed tail. Two supporting measurements: the tail
necked to a SINGLE CELL at two stations before the club - the lollipop again, the join showing as a
stem between two masses - so its tip radius went up and the gap it has to be threaded across came
down; and the reservation had to follow, because `_CREATURE_ZHALF` was 24 while the animal now
reaches 27 rows back. **A stop that does not cover its own creature is a plinth with a tail hanging
off it**, and the clamp exists as a safety net for short spans rather than as a licence, so the
shipped `t` moved 0.25 -> 0.30 to keep it un-clamped.

#### `shell.py` WAS PAINTING A WARM ANIMAL GREEN, AND EUCLIDEAN DISTANCE CANNOT SEE IT

The plan - this animal's money view - came out mottled grey-green over a warm brown coat, and the
surface histogram says why: 5% of the visible cells were `mossy_stone_brick_slab` and
`mossy_stone_brick_stairs`. They are what `slab_for` picks for `dripstone_block`, which is the
coat's dominant tone, and the pick is not close to wrong by its own measure - 26 apart in RGB, well
inside the shift budget.

**IT IS WRONG IN KIND.** `dripstone_block` is (134,108,93): red over blue by 41, a warm tan.
`mossy_stone_brick_slab` is (115,121,105): red over blue by 10, and GREEN is the winning channel.
Euclidean distance has no idea which channel is winning, so it will happily answer a warm block
with a cool one and paint a fifth of an animal's most-seen surfaces the wrong hue family. **A
partial is the same material seen thinner; it must not change what the material IS.** `MAX_HUE_SHIFT`
compares red-minus-blue and is the cheapest test that catches it - and it turns down nothing that
was ever right: `brown_wool -> spruce_slab` differs by 7 and `light_gray_wool -> andesite_slab` by
8, while the mossy pick differs by 31.

It is in `shell.py` rather than in this generator on purpose. Every animal that grows a coat
outside the log families inherits the same pick, and a private guard here would have left the trap
armed for the next one. What it costs is honest and small: `dripstone_block` now has NO trusted
warm slab within budget, so the flank loses its chamfers - 155 shape blocks instead of 194, about
5% of the surface - and the whole animal is one hue family.

#### The negative result: STACKING THE VALUE LADDER WITH THE LIGHT IS WORSE

The value panel showed one flat dark mass with the bone fringe as the only event in it, and the
arithmetic behind that is real: a renderer - and Minecraft - shades a top face brightest, a side
face mid and a bottom face darkest, so a countershaded ladder (dark back, pale belly) multiplies
out to **the same rendered value at every course.** Widening the ladder cancels harder rather than
helping. So the obvious move is to invert it - pale carapace, mid flanks, dark underside, which is
also what a bony shield looks like - and it was built and rendered and is WORSE:

- **the PROFILE got darker, not lighter**, because what a profile shows is almost entirely SIDE
  faces and the inversion had just made the side band the darkest tone. The walkway gives you the
  profile;
- **and the plan went grey-green**, because the surfacing pass picks its slabs off the coat and a
  paler back drew cooler ones. The skyway gives you the plan.

Reverted, and recorded in the palette table so nobody re-derives it. The flatness is real and it is
mostly a property of an armoured animal that is 21% bone at L225 against a body clustered between
L79 and L141; the two views that matter are both better with the ladder the way round an animal
actually wears it.

    Isthmus  42,650 blocks, 0 problems, 0 leaks, 0 expensive, 0 lamps in any coat
    head 8 stations . body 24 . tail and club 15 (32%)
    the stop moved t 0.25 -> 0.30 and its reservation 24 -> 28, to cover the longer tail

**What the audit did NOT fix, stated rather than left.** The head still merges into the shield in
profile, which is anatomically right for an animal with no neck and does mean the profile's front
end is its weakest quarter. At a quarter scale it is a dark smudge with pale dots rather than a
nameable animal - expected for 43 blocks, and the plan holds up much further than the profile does.
And nothing here has been placed in game: `render3d` draws with the same colour DB the palette
picker optimises against, so every verdict above is about form, silhouette, mass and occlusion.

### The head is BLUNT, and the contract had to change with it

`test_the_head_is_PINCHED_off_the_shell` demanded a local minimum in the width profile. The relax
pass correctly removes one - a shallow waist between two masses that each keep their neighbours is
what survives four rounds - so the contract is not a dip. It is that the head is a RUN of stations
markedly narrower than the shield, wide enough to carry a pair of eyes, and blunt rather than
pointed. Same class as the plate-rooting test one animal earlier: **a threshold standing in for a
property is a test that fails the fix rather than the fault.**

    Isthmus  42,650 blocks, 0 problems, 0 leaks, 0 expensive, 0 lamps in any coat
    lengths 28..56 x all four facings: one piece, 4 feet, 2 eyes, 0 clipped, 0 asymmetric,
             every feature placing real cells
    the stop moved t 0.22 -> 0.25 - the longer tail reaches 24 rows back, and at 0.22 the
             clamp fired. A clamped stop is a safety net for short spans, never a licence

**Still open:** nothing has been placed in game - `render3d` draws with the same colour DB the
palette picker optimises against, so judge form and mass off the sheets and the palette in world.
The club is still a boxy mass close up and reads best in plan. And the seven pre-existing
`test_isthmus.py::test_every_land_pair_builds_legally[*-prismworks]` failures are still the stale
`wayfinding.known_destinations()` roster, unrelated and unfixed.

