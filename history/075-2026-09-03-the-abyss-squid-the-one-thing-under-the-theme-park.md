## The Abyss Squid: the one thing under the theme park (2026-09-03)

Jack: *"put something big underneath the theme park so the people doing parkour discover it, I
mean LARGE and something that could be viewed as swimming or flying through space, maybe a super
large squid, or something else intense/scary, large killer whale, etc, but has to be hyper
detailed."* Then, on the hollowing question: *"it can be hollow, mobs do not spawn."*

`configs/abyss_squid.yaml`, `mcbuild/gen/squid.py`, `tests/test_squid.py` (19). **46,882 blocks,
ONE connected piece, 0 problems, 0 overlap in context, 0 leaks, seven block types, all cheap.**
275 blocks nose to tail, X97543..97657 / Y101..185 / Z80488..80762.

### THE SITE WAS ALREADY THERE AND NOTHING HAD MEASURED IT

Over `out/Park Complete.litematic`, the park's own 200x600 shadow at Y100-190:

| | |
|---|---|
| columns completely empty | **117,350 of 120,000** |
| the Midway and both causeway gaps, below Y196 | **0 blocks, all three** |
| everything that IS down there | within r60 of the Prism Well, plus twelve columns of the Frontier's shaft |
| columns with something overhead | **114,267 of 120,000 (95.2%)** - 100% under the Frontier, the Midway and both gaps |

**THE PARKOUR ALREADY ENDS IN IT.** The Prism Well is LINED ONLY TO Y187: below that its shaft is
open void with nothing in it but a 27x27 return column at r<=14 and the two descent helices at
r19-23 and r31-35, about 150 cells each, with a landing platform every eight courses. So a runner
on the last **eighty-six courses** of `PF Crown Descent` and `PF Prism Descent` is falling through
open sky looking outward at nothing at all. The discovery frame was built and nobody had used it.

**AND IT IS PITCH DARK, PERMANENTLY** - no sky light reaches any of it at any hour. That is not a
constraint to work around, it is what chose the subject: the animal has to be its own only light
source, which is what a deep-sea cephalopod is.

Measured clearances on the shipped design: **the outer parkour helix passes 27.4 blocks** from the
nearest cell, the sky run 37.6, `Park Line` 15.4, `Park Rail` 40.0.

### WHY A SQUID, AND THE ARITHMETIC THAT DECIDED THE POSE

This file's own line is PLANAR/COLUMNAR against VOLUMETRIC, learned on eight failed mammals. A
squid has no compound muscle anywhere in it: the mantle is a taper (the giraffe's neck, the one
quadruped part that ever worked), the fins are flat sheets (the sky bird, the bat), the arms and
tentacles are columns, and the eyes are convex domes carrying a pattern - the ladybird's category,
and a colossal squid's eye is the largest in nature, so the one feature this medium is best at is
also the animal's headline. An orca was the alternative and is the opposite bet: a smooth fusiform
mass whose identity is a two-tone pattern, which is thin material for "hyper detailed".

**THE COMPOSITION IS DEPTH, AND THE GEOMETRY FORCED IT.** Three layouts fought this before the
arithmetic got written down: **an arm of length L off a head at distance D reaches r = D - L**, so
an 85-block crown on a head 80 blocks out lands inside the shaft every time, whichever way it is
aimed. The head has to stand at r >= 52 + arm_len. That is not a compromise - it puts the ARM TIPS
near and filling the view, the HEAD mid, and the MANTLE receding into black, which is the one
arrangement that gives a voxel sculpture in empty space any sense of scale at all. The ladybird
needed a leaf for the same reason; this needs its own far end.

**THE CROWN IS AN ELLIPSE, NOT A CIRCLE, AND THAT IS A SITE FACT.** A crown of radius R opens 2R
across the plane perpendicular to the body, and this body is nearly horizontal - so a round crown
is 124 courses tall in a band that is 93 deep. The first build clipped its four lower arms against
the canvas floor and still rendered as a plausible squid, which is the sauropod's recorded bug
exactly. Squashed to 0.60 the fan spreads sideways instead, which is both what a lunging squid does
and the better view from a shaft.

### THE KEEP-OUT IS A SAFETY NUMBER AND IT IS REFUSED PER CELL

`keep_out: [97590, 80815, 56]` - the well's own r52 lining plus four. A surface inside the fall
column does not save a runner who misses a landing, it strands one sixty blocks out in the void
with no way back. Every cell goes through one `put` that refuses it, so a part added later cannot
forget - which is how the Lost Plateau stood a timber set's post on a live rail three times.

**AND THE SITING WAS SWEPT UNTIL THE REFUSAL COUNT WAS ZERO.** At Z80491 it was cutting **1,443
cells** off the two tentacle clubs, and reporting `problems: 0`, a correct BOM and one connected
piece while it did it. **A truncated club renders as a perfectly good short club.** Swept back to
80485 the count is 0 and the achieved nearest approach is 58.6, which the sidecar records and a
test re-derives from the blocks - a clearance that is trusted rather than measured is decoration.

### RULE 12 AGAIN, AND A SHARPER VERSION OF IT

**`nether_wart_block` was 78% of the first build - 90,766 cells - and it has NEVER BEEN SEEN in
this world.** Cheap by the tier table, legal in 1.19, and no evidence behind it at all.

Then the fix for it made the same mistake one level down. The first photophore was
`verdant_froglight`, which IS "witnessed" - in `out/Park Complete.litematic`, because one of our
own designs places it there. **A WITNESS SET BUILT FROM `out/` IS CIRCULAR.** Checked against
`island_full` and `island_now`, which are captures of the real world, `ochre_froglight` is the only
froglight that exists here - 39 of them, scattered by Jack himself - and this file already recorded
verdant and pearlescent stock as zero, in the rail spiral's own section, and I reached for them
anyway.

The palette is now witnessed in a CAPTURE, block by block, and `tests/test_squid.py` pins it:

    mangrove_planks 33 . red_wool 3720 . magenta_wool 111 . pink_wool 682
    black_wool 2815 . bone_block 4007 . ochre_froglight 39

**THE BULK IS PLANKS RATHER THAN WOOL, AND THAT IS AN ECONOMY DECISION.** 27,000 of anything is a
real ask on a skyblock; mangrove is four planks a log off a tree that replants itself, where the
same count in wool is 27,000 shears plus 3,400 red dye. It is also the right colour - a deep-sea
squid is a dull brick red, and red is the first colour to vanish at depth, so a red animal in the
dark is a black animal with lights on it.

The ladder is measured ACROSS families, which this file has now got wrong four times by searching
inside one: `black_wool` 21 . `mangrove_planks` 73 / `red_wool` 75 . `magenta_wool` 118 .
`pink_wool` 173 . `bone_block` 227 - steps of 52, 45, 55, 54. **Mangrove and red sit at the SAME
value on purpose**: they are 48 apart in RGB and identical in luminance, which is what a
chromatophore is - a change of colour across a skin that does not break the form.

### THE MIRROR PLANE IS THE CENTRE OF A COLUMN, NOT ITS EDGE

The most transferable find of the session. `Canvas` tests a ball against cell CENTRES at
`x + 0.5`, so a limb swept from `float(XC)` is mirrored about the column's own EDGE - **5,375
cells, a tenth of the animal, came out different left to right**, every one of them in the arm
crown and the tentacles, which are the only parts swept as balls. The mantle and the head are drawn
in cell indices about XC and were exact all along. `base = XC + 0.5` fixes it: shape asymmetry
3.0% of the model -> 0.4%, and the test's bound is a FRACTION so it scales with the animal and
still fails the fault it was written for.

What is left is decoration and the enforcement owns it: an arm's stripe and its suckers are found
by walking a ray that can start exactly on a cell boundary, and `round()` is banker's rounding,
which does not mirror at a .5 tie - this repo's own recorded trap, *keep centres integer and add
offsets to them*. So the mirror is ENFORCED at the end and **reports its two halves separately**,
because they are different facts: `mirror_shape_fixed` must stay near zero and is what catches a
real fault, `mirror_paint_fixed` is bounded. A single enforcement count would have let the
half-block hide behind it for good.

### THE CONFETTI RULE, IN A SIXTH BODY

The first coat computed one number - `v = h + 0.88 * (drift - 0.5)` - and read as black-and-red
static over the whole mantle. **THE BAND AND THE MOTTLE ARE TWO DIFFERENT DECISIONS.** The band is
the value gradient and a COARSE drift wobbles its boundary; the mottle is the chromatophore and
never touches it. Noise on a boundary is an outline, noise on an interior is static - the deck
soffit's grid, the thicket's drifts, the frog's blotches and the claim row's ground all said so
first.

**AND THE LICHEN WAS REVERSED OUT ENTIRELY.** 1,443 face-attached `glow_lichen` cells went in for
light 7 and a little texture; a close render settled it as GREY POX. Two other things were wrong
with it and neither is about density: **a live animal does not have lichen growing on it** - that
happens to a statue, and this one is swimming - and **`render3d` draws a lichen as a full opaque
cube**, so it was the one element on the build these sheets could not judge at all, which is how
the axolotl's head happened. The 450 froglights carry the light on their own at 15 against 7.

### SMALLER, AND EACH ONE SHIPPED A CLEAN AUDIT

- **THE MANTLE WAS A CIGAR.** Its profile peaked at 0.60 of its own length and narrowed again
  toward the head; the panel read it as a constant-depth wedge with no line in it, which is the
  jaguar's own recorded failure. A squid's mantle is a CONE whose base is the mantle opening. The
  test measures the built model's girth at the centre column rather than its bounding width,
  because the fins are a sheet 45 cells out and a width profile reports them as the mantle.
- **THE HEAD HAD NO NECK** and read as a worm with a face - the axolotl's finding. The step from
  the collar's full girth to the head's 0.74 is not a cliff to smooth away: it IS the mantle
  opening, which is a hard rim on a real squid.
- **A SWEPT LIMB SHEDS ITS TIP.** A ball of radius 0.55 covers one cell, and two consecutive
  centres can round to cells that are only DIAGONAL neighbours: four cells came off three arm tips
  and the component count was the only thing that could see it. `_core` lays a one-cell connected
  thread down each limb's path first and fills every corner one axis at a time - prevention rather
  than a stitch.
- **A NEGATIVE RAISED TO A FRACTIONAL POWER IS A COMPLEX NUMBER, NOT AN ERROR.** Twice, both times
  from a fraction that came out a hair outside [0,1]: `1.0 - 0.16` is not `0.84` in binary. It
  surfaces as a comparison failure twenty lines from the cause.
- **THE TENTACLE CLUBS WERE ORBS ON STRINGS.** Jack, on the first shipped build: *"the random
  orbs its grabbing... doesnt seem to make sense"*. He was reading them exactly right - swept as
  balls they are spheres on stalks, and the stalk ended at radius 2.2 while the club opened at
  4.6, so there was no wrist either. A tentacular club is a flattened PADDLE: `_blade` sweeps an
  ellipse that leaves the stalk's own width, swells about two thirds along and comes to a point.
  **Its thin axis is world X exactly, and that is for the MIRROR rather than for the shape** - on
  a general frame the section is a rotated ellipse whose rounding cannot mirror, and the shape
  asymmetry went 36 -> 410 cells the moment it went in. A tentacle leaves the head along +-X, so
  its paddle's face normal IS X, the thin offsets are integer steps off a rounded column, and the
  wide ones have no X component at all.
- **AND THE MIRROR ENFORCEMENT COULD HAVE BROKEN THE KEEP-OUT.** It writes cells straight into
  the array, bypassing the one `put` every other cell goes through - and **the fall column is not
  symmetric about the animal's own sagittal plane**, because the well's axis sits ten blocks off
  it. A cell mirrored from the safe side can land inside it. Nothing does, at 58 blocks of
  margin; the keep-out is re-applied after the mirror and the clearance re-measured from the
  FINAL grid, because a guard that runs before the last thing to touch the model is not a guard.
- **THE FEATURE COUNTS WERE `put()` CALLS.** The sidecar reported 251,264 arm blocks in a
  116,000-block animal, which reads as a measurement and is an artefact of how an arm is drawn.
  They are unique cells now, and they partition the total exactly.

### HOLLOW, ON JACK'S WORD

Solid it was 116,611 blocks. A 2-block shell carves 65,932 interior cells and it is **still one
connected piece** - nothing thinner than five across is touched, so every arm, both tentacles and
both fins stay solid and only the mantle and head have an inside. The argument against was that it
leaves a 66,000-cell sealed dark cavity, which on a spawning server is an unreachable mob farm
holding down the entity cap - this file already records ~3,700 columns of exactly that under the
lowland massif. **Jack: mobs do not spawn here**, so that argument is gone and 66,000 blocks nobody
could ever have seen go with it.

    solid 116,611  .  shell 4  78,062  .  shell 3  66,532  .  shell 2  46,882

### The panel verdict, recorded (2026-09-03)

**PASSES both panels.** The SILHOUETTE alone names it - a tapering mantle with fins at the rear, a
head, a spray of eight arms and two long tentacles - which is the only question this repo says
finally matters. The PLAN is the strongest view and that matters here, because a runner on the
well's upper landings looks down into it: a symmetric arm spray, the fin as a broad delta, the
mantle as a spine with a dark dorsal line down it. The VALUE panel shows real rounding rather than
a flat shape with a pattern on it. Head-on, the crown, the eye and both tentacle clubs read.

The **accent tail is 17.8%** - cells beyond the top three blocks - against the download corpus's
18.5% median for outside sculpture and our own 5.8%. That is the first sculpture in this repo to
reach it, and it was not chased: it fell out of the arms' pale inner stripe, the suckers, the
photophore rows and the ventral band all being structure rather than decoration.

**Still open, and stated rather than left:**

- **Nothing has been placed in game.** `render3d` draws with the same colour DB the palette picker
  optimises against, and it has NO EMISSION - so the 450 froglights that are the entire reason this
  animal is visible at all are drawn here as cream blocks. Judge form and mass off these sheets and
  judge the light in world; that is the one thing about this design the offline pipeline cannot see.
- **It is NOT in `Park Complete`.** `park_place.extras()` globs `PF *.litematic` and computes a
  y-offset from the park's build plane, which would lift a deep design a hundred courses. It ships
  as its own design at its own recorded origin - `/cscan place "Abyss Squid"` - exactly as the Void
  Ladybird and the bat do. **The consequence is that the composite still reports that void as
  empty**, so anyone siting a new deep design must read this section rather than the shadow.
- **46,882 blocks is a real trip.** 27,647 mangrove planks is about 6,900 logs; everything else is
  wool off sheep and one froglight type Jack already farms.

