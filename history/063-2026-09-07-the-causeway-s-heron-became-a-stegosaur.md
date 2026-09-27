## The causeway's heron became a stegosaur (2026-09-07)

Jack: *"i think the heron should be switched to a dinosaure."* Then, on the first build:
***"i dont think this steogasur is acceptable, it feels bad, its asymmetric, theres issues."***
He was right on every count and the second half of this section is worth more than the first.

**THE HERON WAS A LEFTOVER AS WELL AS A PREFERENCE, AND NOTHING WOULD EVER HAVE REPORTED IT.** It
stood at the frontier end of the Frontier Reach under a plaque reading *"stands in the frontier
marsh"* - a land re-themed to the LOST PLATEAU weeks earlier, and a marsh that has never existed
anywhere on this causeway. Physically correct, legal, affordable, one piece, and describing a park
that is gone: the same class as the five Prismworks relays that outlived the modules they named.

**BOTH DINOSAURS THIS PARK ALREADY OWNS ARE IN SIGHT OF THAT PLINTH, so the answer was a new
generator rather than a paste.** Measured off their own sidecars rather than guessed:

| | |
|---|---|
| `PF Pterosaur` | x97604-97637 / z80406-**80449** - ONE BLOCK off the causeway's frontier end, fifteen from where the heron stood |
| `PF Sauropod` | x97681 / z80290-80370 - 117 blocks away, on the same rim walk |

Pasting either is exactly what retired the gecko and the bat from the hollow reach - *"those are
used assets, we want NEW things"* - so `gen/stegosaur.py` is the third bespoke piece written for
these two stops, beside `balloon.py` and `wyrm.py`.

**AND IT IS A STEGOSAUR BECAUSE THIS FILE'S OWN LIST SAYS SO.** The download corpus's amendment
names it directly - *"a stegosaur is a convex mass with planar plates (the ladybird category)"* -
and every part of it lands on the good side of PLANAR/COLUMNAR against VOLUMETRIC: one convex
arched mass, a row of one-block sheets, four columnar tapers, four more off the tail. No joint
anywhere has to be modelled. **1,508 blocks at length 34, one piece, seven materials, all cheap
tier, all 1.19, zero cells asymmetric in shape OR in colour.**

### THE FIRST BUILD WAS REJECTED, AND THE MEASUREMENT AGREED WITH HIM EXACTLY

Told it "feels bad, it's asymmetric", the useful move was to measure rather than guess - and
"asymmetric" turned out to be one number:

    left-right mismatches, block by block:  99 in SHAPE, 0 in COLOUR
    ...and all 99 were CREST cells

**THE CREST ALTERNATED, WHICH IS WHAT THE REAL ANIMAL DOES AND WHICH IS WRONG HERE.** A real
stegosaur is two metres wide and staggers its plates by a hand's breadth. A voxel one nine cells
wide has ONE CELL to say it with, and one cell does not read as a stagger, it reads as a mistake:
head-on the two rows are two chimneys at different depths, and in plan they are a drunk zigzag.
The generator's own docstring had argued the alternation was "6-connectivity and legibility
agreeing". It was 6-connectivity and legibility disagreeing, and only a render said so.

**THE ANSWER IS TWO ROWS PAIRED, NOT ONE ROW CENTRED AND NOT TWO ROWS STAGGERED**, and all three
were built before that was obvious. Centred on the sagittal plane every plate is its own mirror -
symmetric, and head-on the crest becomes a single one-block blade standing out of the spine, which
is a MAST. Paired at the same station either side of the midline is symmetric AND is what the
animal looks like from the front: two pale blades flanking a ridge with the spine between them. In
profile the pair superimposes into one plate, so nothing is lost in the view the walkway gives.

Two more faults came out of the same look, and both are recorded failures of this repo arriving
in a new body:

- **THE PLAN WAS A SLAB.** `_body` swept SPHERES, so a station's width in plan and its depth in
  profile were the same number by construction - there was no way to say "widest at the shoulder
  and the haunch" at all, and the plan came out as one constant-width mass from shoulder to rump.
  That is the jaguar's retirement verbatim. The spine carries a half-DEPTH and a half-WIDTH
  separately now and the body is lofted station by station: plan width runs 5-9-5-11-5, which is
  a spindle.
- **A LEG WAS BEING COUNTERSHADED AS IF IT WERE ITS OWN ANIMAL.** `_coat` measures each column
  between its own lowest and highest cell, which is right for a barrel and absurd for a leg: four
  courses got the full ladder, pale at the foot and dark at the top, so the animal stood on four
  grey posts and read as a barrel on a stone plinth. Everything below the body's own belly line at
  its station takes the flank tone and nothing else.

**AND THE PALETTE WAS THE "FEELS BAD".** Navy / teal / light blue with traffic-orange plates is
what a saturated primary reads as at this size: a toy. It is a desaturated earth body now with the
one thing on it that is not flesh being the one thing that is not an earth tone - `brown_wool` 79 /
`acacia_planks` 104 / `light_gray_wool` 141 under a `white_wool` 236 crest, which is 157 luminance
clear of the back it stands on and a bigger step than the orange ever gave. The skull and the tail
spikes are `bone_block`, so crest, skull and spikes read as one material family, which is what
they are in life. **And it turned out to unlock the surfacing pass as well** - `shell.slab_for`
refuses a `rotated_pillar`, so a log-coated animal can never be given half blocks, and wool,
planks and stone are uniform on every face. See "super blocky and rough" below.

### FIVE TRAPS, EVERY ONE ALREADY WRITTEN DOWN IN THIS FILE, EVERY ONE FALLEN INTO ANYWAY

- **`round()` IS BANKER'S ROUNDING AND THE FEET CAME OUT AS COMBS.** The legs stand at 0.150 of
  the length, which at length 30 is exactly 4.5 - and `round(4.5) == 4` while `round(5.5) == 6`,
  so every foot sphere skipped alternate columns. Four feet read as EIGHT ground patches, at that
  length and not at its neighbours. **The `_ball` docstring in the same file warns about this trap
  by name while the frame under it was doing it.** Rounding is half away from zero now (`_r`), not
  toward +inf: `floor(v + 0.5)` sends 2.5 to 3 and -2.5 to -2, a shape one cell wider on one
  flank, which is the squid's own mirror fault from a new direction.
- **A TAPER THAT ENDS UNDER ONE CELL CANNOT BE SWEPT INTO EXISTENCE.** The tail spikes detached at
  lengths 26 and 34 and **at neither of their neighbours, and not at the one being looked at**. A
  fine step is not a guarantee, it is a hope that scales; `_thread` lays a one-cell 6-connected
  core first, filling every corner ONE AXIS AT A TIME, and the sweep hangs on that.
- **THE PLATES STACKED ON THEMSELVES.** Probed live, the second course of a plate finds the FIRST
  course of that same plate as its own top and lands one higher again: every plate shipped as
  alternate courses with a hole between them, fifty four-cell strays, and only a component count
  could see it. The back is SNAPSHOTTED before any plate is laid. Same shape as the frog's
  `flank_v`: MEASURE THE MASS, NEVER THE ACCUMULATING BUFFER.
- **THE CREST'S SPACING HAD TO BECOME EXACT INTEGER GEOMETRY, AND TWO TRIES GOT IT WRONG.** Left
  to the width curve, `plate_half` scaled to 2.54 for the plate nearest the peak, `floor(2.54 +
  0.5)` is 3, and that ONE plate went from five cells across to SEVEN and fused with its
  neighbour - four plates read as three. Capping the width against `run / count` fixed that length
  and not the next, because the stations are floats and `_r` rounds them together about half the
  time. The WIDTH is chosen first and the PITCH derived from it as `2 * wi + 2`, which leaves
  exactly one cell of sky between neighbours at any length, count or curve; too many to fit and
  the plates get narrower and then fewer, never closer. **A crest that can merge under any tuning
  is a sail waiting to happen.**
- **THE ANIMAL SHIPPED WITH NO EYES AT LENGTH 24.** The nominal course was one cell above the
  widest part of a small skull, so neither side had anything to sit on; the wyrm shipped with ONE
  eye twice for the neighbouring reason. The probe walks DOWN from the crown for the first course
  carrying a solid cell at the same offset both sides, and RAISES if there is none.

And one instrument rather than a trap: **a refusal below the ground plane is not the same fault as
one off the end.** A foot pad is a sphere centred on the course the animal stands on, so its lower
half is always outside the box; a refusal in f or s is the sauropod's disaster - clipped to 22
blocks of 48 facing north, with a plausible small dinosaur still in the render. `refused` and
`clipped` are counted separately, and `clipped` is 0 at every facing and every length.

**A SCALE SWEEP IS THE ONLY THING THAT FINDS ANY OF THAT.** Lengths 22 to 54, all four facings:
one piece, two eyes, the crest exactly `2 x plates` separate pieces, zero clipped, and zero
asymmetry in shape and in colour. Four of the five traps above were invisible at the length being
looked at and visible two lengths either side of it.

### "Super blocky and rough" - and it was NOT the resolution (2026-09-07)

Jack, on the symmetric rebuild: *"it feels super blocky and rough, how do we make it smooth and
clean."* Four answers, and the order they were found in is the useful part: the two I expected to
be the fix were worth little, and the two that mattered were both bugs.

**THE OBVIOUS ANSWER WAS WRONG, AND MEASURING IT IS WHAT FOUND THE REAL ONE.** "Size sets a
ceiling; tuning sets the plateau" is this file's own rule, so the first move was to build the same
animal at length 44 and compare at the same framing. It is not smoother. It is slightly WORSE -
the lumps scale with it, so they arrive bigger rather than finer. **A defect that survives a 30%
increase in resolution is not a resolution problem**, and that single comparison redirected the
whole session.

#### The lumps were the LEGS, sticking out through the flank

The half-width at the shoulder and the hip was a number chosen by eye. Measured against what has
to fit inside it:

    hip:       stance 2.65 + thigh 2.38 = 5.03      flank half-width 3.67      1.36 PROUD
    shoulder:  stance 2.65 + thigh 1.77 = 4.42      flank half-width 3.57      0.85 PROUD

So every leg pushed a cell and a half out through the side of the animal and read as a lump stuck
on it - four lumps, at the four places a quadruped is supposed to be smoothest. Sized as
`stance + leg radius` the same cells become the HAUNCH and the SHOULDER, which is rule 1 of the
panel review said forward: *"legs must merge into the body as a haunch and a shoulder"*. The flank
goes continuous and the plan keeps its waist (5-9-7-11-5), because the widths are still bimodal -
they are just big enough now.

#### The "roughness" was mostly the COAT, and it was not geometry at all

`_coat` measured every cell's height as a fraction between ITS OWN COLUMN'S lowest and highest
cell. That is right for a barrel of constant section and absurd for a lofted body, where every
column is a different height: the band boundaries follow whatever each column happens to be, so
the three tones come out as **grey blotches wandering a course up and down across the flank**. A
close render reads it as mould on the animal. No amount of smoothing the mass touches it.

Measured against the belly and back lines the keyframes actually describe, the bands are
continuous by construction. Three rules came out of fixing it and all three generalise:

- **A LEG IS NOT ITS OWN ANIMAL.** Countershaded per column, a leg's four courses got the full
  ladder - pale at the foot, dark at the top - so it stood on four grey posts and read as a barrel
  on a stone plinth. Everything below the belly line is one tone.
- **COUNTERSHADING NEEDS THICKNESS.** Three bands want a section deep enough to hold three, and a
  tail two or three cells thick has room for none: every cell lands in a different band and the
  tail comes out as an alternating brown-grey chain, which reads as damage. Below five cells of
  depth a part is one tone.
- **AND THE DITHER MUST BE HASHED ON THE DISTANCE FROM THE MIDLINE.** Keyed on the column, the
  jitter is a different number on each flank, so the boundary wobbles independently either side
  and the animal came out **sixteen cells asymmetric IN COLOUR while its shape was exact** - the
  frog's own recorded fault, where each coat drift carried its own signed offset.

#### The two passes this repo already had, that this animal never ran

CLAUDE.md's ANIMALS section states the order as `mass -> relax -> features -> face -> coat` and
every quadruped here runs it. The stegosaur went straight from a lofted mass to its features.

- **`relax` is now step 2**, with both recorded guards: legs, neck and tail as `protect` (the rule
  that shaves a pimple off a shoulder eats a limb whole), and every air cell below the belly line
  as `forbid` EXCEPT the air inside a leg's own cylinder - because a dent in a leg is worth
  filling, and barring those would keep the legs as lumpy as they were. It is worth less here than
  on a smoothed loft: this mass measured **zero notches before and after**, which is the tell that
  it was never dented, only stepped.
- **`shell.slab_shell` halves every cell that sits proud of its neighbours**, and **`_chamfer`
  turns every one-course step into a ramp with a stair**. 99 shape blocks on a 1,570-block animal,
  which against the download corpus's 4.51 stairs per thousand cells is the first build in this
  repo to be in the right order of magnitude.

**AND THE HALF-BLOCK PASS REPORTED ZERO FOR AN HOUR WHILE LOOKING LIKE A PASS WITH NOTHING TO
DO.** A palette entry is an NBT Tag, and `str(Tag(10, {'Name': ...}))` is a repr - so every block
name read that way matched nothing, every colour lookup failed and `slab_shell` returned an empty
dict. `nbt.state_name` is the accessor and every test in this repo already uses it.

**IT WORKS HERE ONLY BECAUSE THE PALETTE CHANGED.** `shell.slab_for` refuses any `rotated_pillar`,
because the colour DB samples a block's TOP face and a log's top is end grain - matching
`acacia_log`'s orange top to `acacia_slab` once drew a bright orange line down a bear's back. Six
of this repo's eight quadrupeds are coated in LOGS and get no half blocks at all, and CLAUDE.md's
own note says the unlock is to build coats out of uniform-textured blocks instead. This animal's
coat became wool, planks and stone in the palette rebuild one complaint earlier, so the match is
not merely legal but close: `acacia_planks -> acacia_slab` at distance **0**, `stone -> stone_slab`
at **0**, `light_gray_wool -> andesite_slab` at 9, `brown_wool -> spruce_slab` at 15.

Every shape block actually placed is acacia or spruce - both witnessed in bulk on this server -
because `trusted_slabs` already makes rule 12's inference rather than trusting a table: Minecraft
ships a material family COMPLETE, so a server that has `acacia_planks` has `acacia_slab`.

#### What it measures

    body-skin spike_rate   28.7 -> 9.4      "a limb that seems to have gravel stuck to it"
    notches                0                no one-block dents anywhere
    shape blocks           0 -> 99          slabs 64, stairs 35
    left-right asymmetry   0 shape, 0 colour, comparing FULL states with the facing mirrored
    Isthmus                41,230 blocks, 0 problems, 0 leaks, 0 expensive

`tests/test_causeway_sculptures.py` gained `test_the_SURFACE_IS_SMOOTHED_and_not_merely_stacked`
(the three passes all fail SILENTLY - a build with every one switched off is legal, one piece,
correctly proportioned and audits clean) and `test_the_LEGS_do_not_stick_out_THROUGH_the_flank`,
which asserts the arithmetic rather than the picture. `_lr` compares full block states with the
facing mirrored now, not bare names: a stair facing the wrong way is a real defect and a bare-name
comparison cannot see it - the frog shipped 60 of 134 that way.

**Followed up the same day** - see `shell.stair_shell` below. The chamfer moved into `shell.py`,
grew an UNDERSIDE case, and went from 35 ramps to 106. What it turned out NOT to be is an
outer-corner problem: a stair ramps a cell's top or bottom, so a cell in the middle of a flank has
no face to treat and no stair can help it. What is left is the section changing in whole cells,
which is geometry rather than surfacing.

### `shell.stair_shell` - stairs, and the note that said they were impossible (2026-09-07)

Jack: *"attempt it, we should be always pushing the limits of our generators to make complex shapes
so we can make really clean and sophisticated representations."*

**IT IS IN `gen/shell.py`, NOT IN THE ANIMAL, AND THAT IS THE POINT OF DOING IT.** The module
already owned "which cells earn a slab" and its own docstring said the geometry was "ready for"
stairs; writing a second private copy inside one generator is how two rules for one question start
disagreeing. `stair_shell` is now available to the elephant, the giraffe, the frog and everything
after them, and `stair_for` derives its answer from `slab_for` rather than matching colour a second
time - so the two can never disagree about what a coat is nearest to, and the `rotated_pillar`
refusal that stops a log-coated animal getting partials at all is inherited rather than
re-implemented.

**BOTH REASONS `shell.py` GAVE FOR NOT DOING THIS WERE ALREADY FALSE, AND THE PARAGRAPH OUTLIVED
THEM BY WEEKS.** It said a stair is directional with no evidence to settle the convention from,
because *"the capture holds ten stair blocks and none of them records its state"*. CLAUDE.md
records the correction on its own page: the capture holds **463** stairs and their states are in
the palette NBT - the earlier reading looked at the bare NAME list, which drops properties. And it
said a mirrored stair would be invisible in our own renderer, which was true when it was written
and stopped being true the day `render3d.subdivide` went in for the frog's toes. **A stale
"cannot" is more expensive than a stale "should": nobody re-reads it, because it reads as settled.**

#### The rule, and where the cells actually are

    TOP    the top is open and EXACTLY ONE lateral neighbour is solid one course UP
           -> half=bottom, facing that neighbour
    UNDER  the bottom is open and exactly one lateral neighbour is solid one course DOWN
           -> half=top, facing that neighbour

Counted over the animal's own skin before anything was written, which is what decided the shape of
the pass:

    834  interior, walled both ways        no face to treat
    102  UNDER: flat underside
     87  TOP: plateau or proud             -> slab_shell's job, already done
     82  TOP: one higher                   -> a ramp, and only 35 were being placed
     67  UNDER: one lower                  -> A RAMP, AND NONE WERE BEING PLACED
     35  UNDER: two or more lower
     32  TOP: two higher, perpendicular    an inside corner: a stair there reads as damage

**THE UNDERSIDE WAS THE BIGGEST UNTAPPED CASE AND IT IS THE ONE THE CORPUS NAMES.** 27% of outside
builders' stairs are `half=top` - eaves, soffits, corbels, the underside of an overhang - against
none of ours. On an animal that is the belly line and the jaw, which together with the back line
is the whole of what a profile silhouette IS.

**AND `slab_shell`'s UNDERSIDE PASS IS OFF FOR A REASON THAT DOES NOT APPLY TO A STAIR.** A top
SLAB removes half a cell and reads as a gap wherever the thing being cut is thin - it once cut
visible slots through the elephant's ears. A `half=top` STAIR removes a QUARTER and leaves the full
depth on the side the mass continues, so it fills a corner rather than opening one. The thickness
guard is kept anyway and the ground course is never touched, or a foot hovers.

**A VERTICAL STEP IN A FLANK CANNOT BE CHAMFERED BY A STAIR AT ALL**, and that is worth knowing
before anyone tries: a stair ramps a cell's TOP or its BOTTOM, and a cell in the middle of a wall
has solid above and below. Measured, every stair this pass places faces along the body, because
those are the cells with an open face. The only tool for a vertical step is a vertical panel - an
open trapdoor, which is the corpus's other big finding and is architecture rather than anatomy.
What remains blocky on this animal is the flank's section changing in whole cells, and that is
geometry, not surfacing.

#### AND THE RENDERER DREW ALL 106 OF THEM AS CUBES

`render3d.render` does not subdivide - `tools/look.py` calls `r3.subdivide(m)` when
`r3.has_shapes(m)`, and the throwaway sheets I was judging from called `render` directly. So the
first look after adding the stairs was **identical to the look before adding them**, and the honest
conclusion from that picture would have been that the pass does nothing.

That is the frog's own trap, recorded on this page in capitals - *"the feet were rebuilt with
stairs and every sheet here drew them as full cubes, so the change was unjudgeable"* - fallen into
by the person who had just read it. **Judge shape work through `tools/look.py`, or subdivide by
hand; a scratch render script is not the renderer.**

#### What it measures

    shape blocks       99 -> 177 on 1,266 skin cells = 14%   (corpus median for detail: 17.3%)
                       stairs 106 (55 top, 51 under), slabs 71
    stair rate         0.64 per thousand cells across this repo -> 67 on this animal
    left-right         0 shape, 0 colour, comparing FULL states with the facing mirrored
    Isthmus            41,229 blocks, 0 problems, 0 leaks, 0 expensive

Every partial placed is acacia or spruce, both witnessed in bulk on this server, because
`trusted_slabs` already makes rule 12's inference rather than trusting a table: Minecraft ships a
material family COMPLETE, so a server that has `acacia_planks` has `acacia_slab`. `stair_for` then
checks the registry for the stair rather than carrying a hand-written map - `petrified_oak_slab`
and `smooth_stone_slab` have no stair, and remembering which do is rule 11's exact failure.

### Measured against the giraffe, which is the only way this got fixed (2026-09-07)

Jack: *"I feel like this is very rough and the face etc are less smooth than they should be, we
want this to feel like the giraffe."* **A reference beats an adjective**, and the first move was to
render the two side by side and put the repo's own roughness numbers on both:

                    spike_rate   notches   jerk_rel
    GIRAFFE               4.03         0        8.4
    stegosaur            28.97        10       20.5

That is not taste, and every one of the three names a defect you can see once you know to look:
`spike_rate` is "a limb that seems to have gravel stuck to it", a notch is a one-block dent "the
eye reads as damage", and `jerk` is the one that catches "it goes in and out".

#### THE PARAMETERS WERE THERE ALL ALONG AND I HAD UNDER-SET THEM

`quadruped.py` relaxes **four times at fill 11 and keep 11**. This ran ONCE at fill 15 and keep 8 -
weaker on every one of the three axes - because of an over-reading of this file's own warning that
*"every smoothing pass rewards thickening"*. **That warning is about tuning smoothing ALONE against
the rubric**, which took the bear's proportion 0.88 -> 0.50; it is not an argument for
under-smoothing, and the giraffe was standing in the world as the counter-example the whole time.
Swept against every contract at once, four rounds costs 21% more cells and keeps the plan waist,
the four feet, the eight crest pieces and exact symmetry.

**AND ONLY THE LEGS ARE PROTECTED, which is also what `quadruped.py` does.** A protected cell is
never shaved, so protecting the neck and the tail as well left them exactly as lumpy as they were
built while the barrel smoothed around them - the two parts that read worst against the giraffe. A
leg genuinely has too few neighbours to survive `keep`; a tail three cells thick does not.

    relaxed mass:   spike_rate 8.6 -> 3.92     BETTER than the giraffe's 4.03
                    notches 0, jerk_rel 20.5 -> 12.4

The finished model still measures 25 because the CREST is one-block sheets and scores that way by
construction; the giraffe has no such feature. The body skin is the fair comparison.

#### THE FACE WAS A BALL WITH A BEAD ON IT

Set beside the giraffe's head the gap is obvious: the giraffe has a pale muzzle narrowing to a
nose, an eye set in it, a jaw. This had a SPHERE of radius 2.4 with a black cube stuck on it.
**A skull is a TAPER** - a stegosaur's is long, low and narrow, ending in a toothless beak - and
none of that survives being drawn as a ball. Two more things had to follow:

- **THE NECK STOPS WHERE THE SKULL BEGINS.** Swept on to the nose it buried the head: only the
  last four pale cells showed past the russet, so the animal read as a neck with a chip on the end.
- **A NOSTRIL IS NOT BLACK, and it gets its OWN MATERIAL.** Black, two nostrils between two black
  pupils read as a second pair of eyes - the frog shipped exactly that. And drawn in the plates'
  own root stone, the crest mask counted each nostril as a one-cell PLATE with no back under it,
  so the plate-count, the plate-rooting and the "the nose is all bone" contracts all failed on a
  correct build. **A mark that means something different is a different block**, or every test that
  masks by material is measuring two things at once.

#### FIVE BUGS THE SCALE SWEEP FOUND, EVERY ONE SILENT AT LENGTH 34

Turning the smoothing up and un-protecting the neck and tail destabilised four things that had been
held together by under-smoothing. **Not one of them was visible at the length being looked at.**

- **THE LEG-GAP GUARD WAS TRUE FOR EVERY CELL ON THE MIDLINE.** `abs(sd) - stance < r` is negative
  at `sd = 0`, so the entire space between the legs counted as "inside a leg", was never forbidden,
  and the fill pass welded the feet - two instead of four at most lengths. It is
  `abs(abs(sd) - stance)`, the distance from the leg's own axis.
- **...AND THE REACH HAD TO BE CLAMPED TO HALF THE LEG SPACING**, which is this file's own sentence
  ("or it protects nothing"). At `r + 0.6` alone, a thigh 1.86 wide standing 2.34 off the midline
  reaches the midline anyway: three feet instead of four.
- **THE THAGOMIZER CAME AWAY AS ONE PIECE** at four lengths of seventeen. Un-protecting the tail is
  what smoothed it, and the same shave MOVES ITS SURFACE - the spikes still rooted at
  `_tail_y_at`, which is arithmetic. `loft.surface_out`'s rule, and it has already cost this
  project a mane, a pair of ossicones and a tail that floated 45 cells clear.
- **THE SKULL DETACHED AT LENGTHS 22 AND 26** for the same reason at the other end: the neck's thin
  tip is shaved by an amount that depends on the length, so a skull abutted to its DESIGNED tip
  ships headless. It threads back to whatever is actually there - and the THREAD reaches back while
  the SWEEP does not, because moving the sweep's own start stretches its taper and the cheek came
  out too narrow to carry a pair of eyes.
- **A PLATE'S OUTER WING CAME AWAY** at length 30 and not at 26 or 34. Each column roots on its own
  patch of back, and where the back drops two courses between one column and the next their ranges
  stop overlapping. Each column now reaches down to its lower neighbour's root.

**And the plate rows moved from one cell either side of the spine to two**, because at one the
trough between them measured as TWELVE NOTCHES - every notch in the animal - and the crest read as
a cracked ridge rather than as two rows. At two it is zero, which is what the giraffe measures.

#### Two tests were the wrong SHAPE, not the wrong number

- **"a plate meets the back at three or more cells"** failed the smallest plate of a correct build,
  whose root row is two columns wide where the back has narrowed. The exact property is that EVERY
  CELL OF A PLATE'S LOWEST COURSE sits on body - a threshold standing in for a property, which is
  what this repo keeps having to unlearn.
- **"the skin has zero notches"** cannot distinguish a crotch from damage. Four remain and all four
  are on the midline under the belly, in the gap the forbid set deliberately keeps open; the
  giraffe scores zero only because its legs are far apart and its belly is high. The assertion is
  now that every dent IS that gap, which is exact and still catches a dent anywhere else.

And `test_the_plates_are_PAIRED` reads the offset out of `_dims` instead of carrying the literal
`1`, or it would have failed the fix rather than the fault.

    Isthmus  41,461 blocks, 0 problems, 0 leaks, 0 expensive
    lengths 22..54, all four facings: one piece, 4 feet, 2 eyes, crest = 2 x plates, 0 clipped,
    0 asymmetric in shape and in colour

### The panel verdict, recorded (2026-09-07)

Cut out of the FINISHED causeway as well as alone, at the bearings the walkway actually gives.

**SILHOUETTE - PASSES, and it is the only question that finally matters.** With the colour taken
away it is an arched back carrying four separated plates, four columnar legs, a tail held clear of
the ground with spikes on it, and a small head low at the front. A stranger names it.

**PROFILE - PASSES, and it is the view the stop is built for.** The walk runs along Z and every
creature stop is offset in X, so a visitor stands ABREAST of this animal at about twenty blocks -
which is exactly the view a stegosaur's plates exist for. Both profiles are mirror images.

**PLAN - PASSES, and it is the second view rather than a spare one.** The skyway passes overhead,
and from there the two plate rows, the four splayed pads and the thagomizer all read. That is the
ladybird's own argument for this category: the plan is the view voxels give away free.

**HEAD-ON - MARGINAL, and honestly so.** Eleven cells wide, so head-on it is a narrow mass with two
pale blades over it. That is what a stegosaur looks like from the front and it is not a bearing
anybody is routed to here - but it is the weakest of the four and no arrangement of a paired crest
improves it further.

**At half distance it still reads. At a fifth it is a low dark mass with a bumpy pale crest** -
still a plated dinosaur and nothing else.

**The one real gap: there is not a single shape block in it.** The download corpus measures us at
0.64 stairs per thousand cells against their 4.51, and this animal is full cubes throughout. A
stair under each plate's outer wing and at the toes is the obvious next pass, and `render3d` can
now draw both - which is the argument for doing it rather than against.

### What it cost, and what is still open

    Isthmus  39,903 -> 41,171 blocks, 0 problems, 0 leaks, 0 expensive, 0 lamps in any coat
    the stop moved t 0.14 -> 0.24, because the animal reaches 22 rows back and 19 forward
             against a heron's 7, and at 0.14 its tail would have been CLAMPED - a clamped stop
             is one whose far end lands where `cols` has no column at all

`_site_heron` is `_site_footed` now and serves both; `SELF_CARRYING` in
`tests/test_causeway_sculptures.py` keeps the stegosaur out of the balloon's and the wyrm's
own-ground contract, because it stands on four feet on the causeway's plinth and its lowest course
is four separate pads.

**Two TESTS were wrong where the build was right, and both are worth keeping.**
`test_the_rim_carries_a_fence_wherever_the_ground_actually_ends` read the highest cell in a column
as its cap - and a sited creature is free to reach out over open air past its plinth, so a rim
column carries the ground, its fence, several courses of sky, then a bone spike hanging seven
above. Read that way the fence four courses below looked missing and **the causeway was reported
unfenced at the one place it is most obviously fenced**; the ground's cap is the top of the
column's own UNBROKEN RUN. And the plate-rooting test was written per COLUMN, where a kite's outer
wings legitimately overhang - it is per PLATE now. The right way round to discover a contract had
been written as "nothing overhangs" when what was meant was "nothing floats".

**Still open:** nothing here has been placed in game - `render3d` draws with the same colour DB the
palette picker optimises against, so judge form and mass off the sheets and the palette in world.
The night pass hangs **23 `glow_lichen` in the air over the animal** (`delight_in_coat` is 0, so
not one coat cell was eaten) and on a bone-white plate those read as green flecks rather than as
the patina they read as on a dark coat - correct by the causeway's own rule, and a causeway-wide
decision to change. And the seven pre-existing
`test_isthmus.py::test_every_land_pair_builds_legally[*-prismworks]` failures are still the stale
`wayfinding.known_destinations()` roster, unrelated and unfixed.


