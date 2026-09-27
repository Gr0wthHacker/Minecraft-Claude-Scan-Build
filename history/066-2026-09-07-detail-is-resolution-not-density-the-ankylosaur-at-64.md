## DETAIL IS RESOLUTION, NOT DENSITY: the ankylosaur at 64 (2026-09-07)

Jack: *"we need this as detailed and perfect as the squid but it cant be so massive, so whats the
compromise."* The premise turned out to be wrong, and measuring it is what produced the answer.

| | Abyss Squid | ankylosaur at 40 |
|---|---|---|
| accent tail (cells past the top 3 blocks) | 15.9% | **20.9%** |
| dominant block | 59.0% | **48.4%** |
| palette | 7 | 8 |
| stairs and slabs per thousand cells | **0** | 62 |
| **surface cells** | **44,104** | **1,078** |

**THE SQUID IS NOT MORE DETAILED THAN THIS ANIMAL. IT IS FORTY-ONE TIMES THE SURFACE.** On every
density measure this repo owns, the smaller animal already wins. What reads as detail at 275 blocks
is RESOLUTION: a feature that is 2% of the squid is five blocks and reads, and the same fraction at
40 blocks is one cell and does not exist. So the question is not what to add, it is how much
surface the site can afford - and then how to spend it.

### AND SCALING ALONE MADE IT WORSE, WHICH IS THE HALF THAT MATTERS

Built at 40, 56 and 64 and rendered side by side, the bigger ones are EMPTIER: a wide brown field
with sparse dots. `spike_len`, the club, the horns and the head are all fractions of the length and
`_knobs` placed **one cell at every size**, so the carapace's pattern density fell as the square of
the animal. That is this file's own "feature sizes must scale" trap running backwards - an absolute
too small at large scale rather than too big at small - and it is why a bigger build of the same
generator reads worse rather than better. **Size buys resolution; the pattern has to spend it.**

### The compromise, as a number

**L=64: 10,428 cells, 37 x 17 x 73, 7,148 surface.** More surface than `X elephant` (3,015), which
is this repo's own control that "reads instantly"; a sixth of the squid's, which is the honest
ceiling for a walkway stop rather than a landmark. The span fits it at t=0.38-0.50 without the
clamp firing, and the causeway grew by 92 blocks of terrace to carry it.

What was built into that resolution, all of it absent or one cell before:

- **graded scutes** - `knob_r` is a fraction of the length now, and `knob_grade` makes the flank
  scutes 1.45x and the spine ones 0.85x, because a field of identical studs is riveted plate at any
  size;
- **a keel down the midline** - **A LINE SURVIVES DISTANCE AND A FIELD OF DOTS DOES NOT.** The
  jaguar's rosettes "turn to noise rather than pattern" at a quarter scale and that is the recorded
  reason its coat failed; the keel is the only thing on the back that still reads as a smudge;
- **transverse half-rings** over the shoulder - the feature an ankylosaur is actually diagnosed on,
  and the one thing that breaks a uniform field of scutes into a structure;
- **four horns, not two** - the squamosal pair off the skull roof and the quadratojugal pair under
  them at the cheek, the lower pair aimed DOWN as well as back so head-on it widens the jaw rather
  than doubling the upper pair;
- **three toes a foot, tapered with stairs** - the frog's own recorded fix. A toe built of full
  blocks ends at a vertical face, which is a plate, and that is why four arrangements of cubes on
  that animal read as a rake, a comb, a plus sign and a set of random lines. **And the gaps are the
  feature**: three prongs with air between them are a foot, the same three filled in are a boot;
- **ossified tendon rings** along the tail, which is what makes it a rigid club-carrier;
- **a keel along the club's own seam**, so the two lobes read as two rather than as a mallet.

### IT READ AS AN ALLIGATOR, AND THE CAUSE WAS A RULE APPLIED ONE STEP TOO FAR

Jack: *"i feel like this looks like a sea monster or something, alligator, not what we're trying to
build."* He is right, and "alligator" turns out to be a measurable silhouette rather than a mood.
Off the built model:

    ground clearance of the barrel   0 courses
    back line                        flat, 13-16, over the animal's whole length
    tail                             dragging at y=3 for its entire length

**Belly on the floor, flat back, tail down: that is a crocodilian term for term**, and it is not
what an ankylosaur is - a DOMED carapace carried CLEAR on four short pillars with the tail held
horizontally off the ground.

**AND IT WAS MY OWN EARLIER DECISION.** `_legs`' docstring said it outright: *"four short columns,
and they are meant to be nearly invisible - a leg that shows is a limb the silhouette decomposes
into, which is the one thing this animal is chosen to avoid."* That is the download corpus's
finding, and it is true of a barrel slung between LONG legs, which is the jaguar and the eight
retired mammals. **Four short thick pillars under a wide dome is the TURTLE, and the turtle works
in this repo.** Applying the rule to the ankylosaur's stance did not prevent a jaguar; it built a
crocodile.

The fix is three numbers and no new machinery - raise the spine's centre line so the belly clears
the ground, arch it so the back is highest over the hips, and carry the tail at hip height rather
than at the old belly's:

    profile floor between the leg pairs   mean 1.87 -> 4.33 courses
    midline clearance                     3.18 -> 6.33
    barrel depth                          11.00 -> 11.59      (so the mass still dominates)

#### The test that guarded this was measuring the wrong thing, and passed both builds

`test_it_is_ONE_MASS_and_its_legs_do_not_show` was the contract behind the whole decision, and it
passed the crocodile and the dinosaur identically. Two faults, and the second is the transferable
one:

- it measured air BETWEEN the highest and lowest solid cell of each profile column, which is a
  test for internal voids and not for daylight under an animal;
- and the replacement, written on the MIDLINE, still passed the crocodile by a hair - because
  **what a walker sees in profile is the FLANK**, and on the old build the flank reached the ground
  while the midline did not. The midline said 3.18 against 6.33 and neither number was the one that
  mattered. **A test for how something READS has to measure the view it is read in.**

`test_the_barrel_is_CARRIED_CLEAR_but_the_mass_still_dominates` replaces it and is deliberately
two-sided, because this animal has now been wrong in both directions: there must be real daylight
under the barrel, AND the barrel must still be deeper than the legs are long. It was run against
the old spine to prove it fails there - a contract that passes the fault it was written for is
worth less than no contract, and this file has three of those on record already.

    Isthmus  44,001 blocks, 0 problems, 0 leaks, 0 expensive
    64 builds - 16 lengths x 4 facings - one piece, four feet, 12 toes, 4 horns, 2 eyes,
    0 clipped, 0 asymmetric

### Six defects, and the last one had been silent since the stegosaur

- **THE TOES DETACHED AT THREE LENGTHS OUT OF NINE.** Spaced by a multiple of the toe's radius the
  outer pair walked off the pad; spaced across the foot they still missed it, because the pad is a
  ball and the relax pass shaves it, so at the outer offset the ground course is sometimes not
  there at all. Five components and a perfectly clean audit - **a detached toe is still a legal
  block on a floor.** Each toe walks back to the pad's own frontmost solid cell and a toe with no
  foot is skipped.
- **THE CANVAS MARGINS WERE CONSTANTS.** Fixed at 3 and 5 they are generous at 40 and gone by 76:
  everything that scales needs room past the nominal body that scales with it, and `clipped` came
  back off zero above 70 while every other contract still passed. They are a fraction of the length
  now, and the sweep is clean over 22 lengths x 4 facings.
- **THE TAIL BANDS REPAINTED INSTEAD OF RAISING.** Written at the top course they recolour the cell
  already there and add nothing: the part count read 0 while the pass reported success, which is
  the horns-inside-the-skull failure in a second body. **A band you can only see in colour is not a
  tendon ring, it is a stripe.**
- **THE CHEEK HORN BURIED THE EYE**, because `_bead_pair` takes the outermost solid cell at its
  course and the horn is now the outermost thing on the skull.
- **A LAMP TARGET INSIDE A STOP WAS COUNTED AS A LAMP THAT COULD NOT BE PLACED.** The causeway's
  light pass slides a lamp to the nearest free column - which is right for a bench or a fence in
  the way - and its own docstring already says a stop lights itself. It tried to slide OUT of the
  stop's footprint, could not, and counted three misses. **That could never fire while every stop
  was narrower than the slide radius**; the first stop bigger than it turned a design decision into
  a reported fault.
- **`nbt.state_name` RETURNS ONLY THE NAME, so the mirror test has been comparing bare names since
  it was written.** Its own docstring says it compares FULL BLOCK STATES with the facing mirrored
  and exists to catch a stair leaning the wrong way on one flank - which is the frog's 60-of-134
  defect, invisible in every sheet until `render3d.subdivide` learned to expand a stair. The
  properties are in `state_props` and have to be asked for. `_full()` is the accessor; with it the
  test genuinely checks what it claims, and the build passes.

### And three tests were the wrong shape

`test_the_face_is_DRAWN_and_reads_head_on` has now been written three ways to find the eyes
geometrically - "the outermost black cells", then "black with no black above or below" - and both
times it picked the MOUTH's own carry-back along the jaw, which is black, isolated vertically, and
further out than the bead. **A BEAD IS FOUND BY ITS RING**, which is what makes it an eye; nothing
else on the animal has one. That is the same lesson as the plate-rooting and head-pinch contracts:
a threshold standing in for a property is a test that fails the fix rather than the fault.

    Isthmus  43,761 blocks, 0 problems, 0 leaks, 0 expensive, 0 lamps unplaceable
    the animal 10,428 cells, 7,148 surface, one piece, four feet, 12 toes, 4 horns,
               2 eyes, 0 clipped, 0 asymmetric - over 22 lengths and all four facings
    the stop   t 0.30 -> 0.42, plinth 8 -> 13, room 16 -> 21, flatten 11 -> 16, reach 28 -> 38

