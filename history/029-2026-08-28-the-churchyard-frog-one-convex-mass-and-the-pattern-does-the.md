## The churchyard frog (2026-08-28) - ONE CONVEX MASS, and the pattern does the work

`configs/lowland_frog.yaml`, `mcbuild/gen/frog.py` - **2,079 blocks, one piece, 0 problems, 0
overlap in context, all cheap.** Jack: *"build a frog, put it opposite end from axo, on the far
empty lot left of the church"*.

### The first build was a smooth mass and it did not read

It was a lofted superellipse - the axolotl's and the turtle's machinery - and Jack said flatly
that it did not read as a frog. It did not. He sent three references: the **Minecraft frog mob**,
a **frog-shaped house**, and an outside builder's **voxel frog**. NOT ONE OF THEM IS A SMOOTH
MASS. All three are assembled rectangular parts - a flat-topped head box, a lower body box,
blocky haunches, splayed feet with separate toes - and all three read instantly.

**That is the void tower's rule said again for a creature: what makes voxels legible is
REGULARITY AND SEPARATION, not smoothing.** A loft averages every part into one hill, and a hill
is what the panel could not name; the parts here are boxes with air between them, and the air
does as much work as the blocks - under the chin, between the arms, between the knee and the
back. `gen/frog.py` has no `loft` import at all: it has a `box()` with a corner **chamfer**,
which is all the rounding a voxel animal wants.

**AND THE PROPORTIONS ARE THE MOB'S, NOT THE ANIMAL'S.** The naming test is *would a stranger
say frog*, and on a Minecraft server the stranger's reference is the mob: a HEAD nearly half the
length, eyes bulging off the top of it past the outline, a small low body behind, a pale throat,
feet that splay. Anatomically-correct proportions gave a toad. This gives the thing people have
seen a thousand times.

**THE PLAN NEEDS A WAIST.** At head 11, body 9 and haunches 13 the envelope was a constant
rectangle 17x15 and the animal read as a brick from above - which is the view this medium gives
away free, so it is the one that must not be a box. Head 9, body 7, haunches 13, with the eyes
AND the feet standing outside the head's own width: that is what puts a notch in the outline.

### The lot was measured before it was drawn

Standing in the sanctum's doorway looking out (the facade faces south), the lot on its LEFT is
the east one - and it is the far end of the lowland from the axolotl, which lies ~50 blocks west
on the harbor bank, so the two never share a view. It is also the largest genuinely empty ground
left down here: a flat plain at **Y39**, **0 blocks standing above it**, no lantern of the ground
design's 9-grid inside it, 113 courses of headroom. At 15x13 the lot yields six placements at
roll <= 1; at **17x13 it yields none**, so the animal sits at `at: [-24167, 29976]` on ground
that rolls three courses (176 columns at Y39, 42 below it) and the SKIRT - every ground-course
column filled down to its own turf - is what carries that. Nose 3 clear of the church wall,
which is a test.

**SIZE FROM THE EYE.** A bulge needs 3x3 and a clear cell between the pair or the two read as one
brow (the ladybird's spot spacing), so the skull cannot be under 11 wide - and the eyes then take
the animal to 13 across, which is what the lot holds.

**COLOUR.** The moss floor is (89,110,45), so a green frog is the green-turtle mistake. This is
the TEMPERATE (orange) frog: three tones of one hue, which the flamingo proved beats two tones
and a third - `orange_wool` (241,118,20) over `acacia_planks` (168,90,50) over `brown_wool`
(114,72,41) - with a birch throat, a gold iris, a black pupil. `tests/test_frog.py` asserts the
ladder is a ladder (>= 20 luminance a rung) and that the top tone is >= 40 clear of the moss.

**NO BLOTCHES.** Three attempts at mottling produced, in order: brown confetti; regular crosses
(a radius of 1.4 in `dx^2+dv^2 <= r^2` yields the five-cell orthogonal plus, not a disc); and a
diamond stamped on the flat back of the box build. The animal reads better plain. The
dorsolateral line down each flank is the one marking that is a LINE rather than a stain.

### The night pass cannot see this animal, and that is a hole in the whole island

Propagated through the finished world, **129 of the 149 air cells over the first build's back
stood at block light ZERO** - a zombie on the sculpture every night. `Island Night` reports zero
spawnable surface cells with the frog in place, and it is wrong to be reassured by that: its
classifier takes each column's **topmost standable cell**, and this lot lies 113 courses under
the island's belly, so the frog, the lot and everything in it are invisible to it.

| | |
|---|---|
| lowland columns with a standable cell under Y60 | 6,852 |
| ...that the night pass's classifier ever grades | **1,624** |
| ...invisible to it because island stands overhead | **5,228 (76%)** |
| lowland walking-surface cells actually at light 0 | **480 of 6,783 (7%)** |

The Lowland Glow solved to zero because it ran on a LOWLAND-ONLY composite, where the floor IS
the topmost standable cell; the island-wide pass then swallowed it. **Those 480 cells are open
and are not this design's to fix** - a night re-solve scoped per LEVEL rather than per column is
its own project, and Jack's call.

The frog answers for its own back with six `ochre_froglight` **in the skin, not on it**: three
down the spine, one on the crown, one in each hind foot. In the skin, because a fixture laid over
a coat is the hole in a sculpture the night pass's own rule forbids. On the crown, because the
EYES are the highest cells on the animal and the back lamps sit four courses below them. In the
feet, because light has to travel round the body to reach the toes and no spacing of the spine
lamps ever got there. `test_nothing_can_spawn_on_its_back` re-runs the propagation rather than
trusting it. It is also the one animal on the island that glows, which for the mob froglights are
made from is the right animal to do it.

### Traps, every one of which shipped a clean audit and a wrong build

- **A CHAMFER EATS A PART TWO CELLS WIDE.** `chamfer=("uv",)` drops the cells where a u-edge
  meets a v-edge; on the shin - three stations long, two cells wide - *every* cell is on both
  edges at its end stations, so it came out as a 2x3 slab floating beside the body. Seven cells,
  caught by the component count and by nothing else.
- **The eye sits directly over the hind foot in plan** - it is as wide as the haunch, which is
  what the mob looks like - so asking for the topmost cell of that column to make it a lamp
  returns an EYE, `paint` correctly refuses to recolour it, and both foot lamps were silently
  never placed. A fixture that belongs to a part must be addressed at that part's own course.
- **The nostrils were painted onto the head box's own chamfered edge**, so they were `paint`s
  over air: `nostril: 0` in the sidecar, and a face with no nose that still audits clean.
- **The lofted build's legs read their own output.** `flank_v` scanned everything built so far to
  find the body's widest offset, so each pass answered one cell further out and the animal crept
  from 15 wide to 19. (Gone with the loft, kept here because the shape of the bug is general:
  measure the MASS, never the accumulating buffer.)
- **The forelegs were built after the hind FOOT, which lies exactly where the hand goes.** Every
  cell found the ground course taken and it shipped with `forelegs: 0` **in its own sidecar** -
  and nothing noticed, because a frog with no arms is still one connected piece with no placement
  problem and a clean BOM. `test_it_has_arms` is four lines and now checks every part.
- **`profile_view` in the sidecar OVERRODE panel.py's own rule** and pointed it at the head-on
  view, which is the one view a profile must not be. The key is simply not written now.
  `Lowland Turtle` records `profile_view: side` with the same facing and has been reviewed
  head-on ever since - worth a look when someone next opens it.

### Audited against the three references, block by block (2026-08-28)

Jack: *"audit again, fix it, I want it to be more like reference."* Six differences between the
box build and the frog mob / the frog house / the outside voxel frog, all of them fixed:

- **THE EYE WAS GOLD-DOMINANT AND IT SHOULD BE DARK.** On the mob and on the house the eye is a
  dark eyeball with a bright ring around it; the build had a gold 3x3 with one black cell on
  top, which reads as two gold cubes on the corners of a box. Same cells, opposite emphasis:
  gold ring below, one raised black pupil above. **One cell, not five** - a black plus on top of
  the ring covers its whole middle row and column, and in PLAN, which is this animal's best
  view, the eye came out as a crosshair on a gold square.
- **THE PALE BAND WAS A SEAM.** One course of birch under a dark line is a joint; the house
  carries a band you can see from across the water, and it is half of what makes a blocky orange
  box read as a face. Two courses now, with the mouth line sitting on top of it and running back
  along the jaw.
- **THE HANDS WERE FOUR CELLS TUCKED UNDER THE CHIN.** The house and the voxel frog both give the
  front feet three splayed prongs with gaps, and they are the detail that says ANIMAL rather than
  ornament. Three toes now, of three different lengths, reaching to the line of the snout - and
  INBOARD of the hind feet, because out at the animal's own widest there is no room and the nose
  is three blocks off a church wall.
- **THE BODY WAS A HARD BOX.** The reference bodies are rounded; the top edges are chamfered now,
  which costs 12 cells.
- **THE HEAD HAD NO BROW.** The house's roof overhangs its eye band, and the overhang is most of
  what stops the face reading as the end of a crate. The head's TOP course now runs out to the
  nose at full width over a face inset one cell on three sides. It costs no length, which
  matters here. **The nostrils had to move onto the brow with it** - left on the skull behind
  the overhang they were invisible from the only view that shows them.
- **IT WAS STRETCHED.** 17 long against 11 tall; the references are near 1:1 (the house) and
  1.3:1 (the voxel frog). **15 x 13 x 11** now, which is also the footprint the lot takes at
  roll <= 1 rather than roll 3 - the proportion fix and the siting fix turned out to be the
  same fix.

**832 blocks, one piece, 0 problems, 0 overlap, all cheap.** The stray-component check earned
its keep twice more in this pass: the inner toe at `hw - 3` had no neighbour, so both hands
shipped as three-cell strays.

### Rebuilt again, with `tools/look.py` (2026-08-28)

The whole animal up to this point had been judged from orthographic elevations and a plan, and
the 3-D pass proved that was not enough. Its own note said so before I looked: *"the haunch is a
flat-sided box with a hard vertical rear face, and the value panel shows it as one untouched
mid-grey rectangle - the jaguar's own failure, in a build that passes head-on."* It was right,
and the orbit sheet found more of the same at 45, 135 and 225 - the bearings an orthographic
tool cannot render at all.

**A CHAMFERED BOX IS STILL A CRATE.** Fixing the loft by going to boxes fixed the head and left
the body as three unarticulated slabs; what rounds a mass at voxel scale is a course-by-course
STEP, which is what the reference builds do and what a single dropped corner cell does not. The
generator has a `mass()` now - a stack of boxes, each course inset at the nose end, the tail end
or the outboard side - and it is what turns the haunch into a folded thigh and the rump into a
fall rather than a wall.

**AND THE STEP RATE IS A REAL PARAMETER.** At one inset every second course the taper reaches
nothing before the top on an animal only eight courses tall: the haunch shipped as a flat shelf
at half height with a single lone column standing on it, which every check passed. Every third
course rounds it and still arrives.

Four more things the 3-D views decided, none of which any flat render could have:

- **THE HAUNCH IS AS TALL AS THE HEAD.** Built at 0.80 of the skull height the rear was lower
  than the front all the way back, so the profile was a head on a loaf. A sitting frog is two
  masses of about one height with a dip between them, and that dip is the whole line.
- **THE EYE IS A DOME, NOT A PAD.** Two courses read as a gold plate on the corner of the skull
  from every bearing except head-on - which is exactly the view the flat sheets had been showing
  me. Three courses give it a top.
- **THE NOSTRILS WENT FROM BLACK TO THE MID TONE.** Two black cells on the brow between two black
  pupils read as a second pair of eyes head-on, and head-on is the only view that shows them.
- **The animal is 15 blocks and it does not hold up at 6x.** That is a fact about its size, not
  its shape, and the lot is what it is: a 22-block frog does not fit the flat ground east of the
  church at roll <= 1.

**1,029 blocks, one piece, 0 problems, 0 overlap, all cheap.** The working loop is now generate →
`look.py --sheet orbit` → change one thing → look again, and it costs about a second a pass.

### The frog, rebuilt from the reference's CONSTRUCTION (2026-08-28)

Jack, six times over one build: the eyes are obnoxious; don't love it; we are getting further
and further; still not like the reference; the eyes are giant; *"you are slipping and letting
this low quality pass when you should be auditing it more thoroughly than I am."* All fair. The
record of what went wrong is worth more than the frog.

**I KEPT REFINING MY FROG WITH THE REFERENCE'S FEATURES BOLTED ON, instead of reading how the
reference is BUILT.** Four references in the end, and the last one - Coldrobin's - is
unambiguous. The construction:

    ONE BIG BOX for the body, flat-fronted, haunches stepping down at the rear
    THE EYES ARE SEPARATE BOXES ON TOP: a flat LID in the body's own colour, and the box's
      FRONT FACE a BLACK BAND with a single bright block set in it at the inner end
    ONE HUGE PALE PANEL for mouth and belly together, ground up, about two thirds of the
      height, with a narrow tongue of body colour cut into its top - the upper lip
    FLAT FEET on the ground in a BRIGHTER tone, three toes FANNING from a pad

Every one of those is a shape, and I had built the wrong shape for each: a bright square in a
dark ring (four times, resized and recoloured every way and never once the right shape); a
mouth band, a dark line and a separate belly; and three parallel prongs of equal length at
equal spacing, which is a RAKE - nothing radiates, nothing tapers, and the eye reads a tool.

**THE PALETTE, matched by measurement.** The statue's body is mud brick; `mud_bricks`
(137,104,79) and `packed_mud` are both CURRENCY on this server, and `jungle_planks` (160,115,81)
is 23 RGB off the first and cheap. The saturated orange this build carried for four passes was
picked against the moss on LUMINANCE, and it is most of why it never looked like the reference.
Against moss (89,110,45) the new body is 80 apart in RGB - a full hue flip, which is what the
turtle proved carries on this floor. The ground test is colour DISTANCE now: measured the old
way it would have failed the reference's own palette and passed a green frog.

#### The audit I should have run before showing him anything

- **A LAMP THAT SILENTLY DID NOTHING.** Moved off a toe (where a white block reads as damage)
  and aimed at the pad at `face` - but the BODY owns that column at the ground course, so
  `paint` refused a cell that was never foot. No error, no lamp, sixteen cells over the toes
  still at block light zero. The pad is the course in FRONT of the body.
- **EYE BOXES HANGING OVER AIR.** 26 of 46 lid cells had nothing under them: the crown drew in a
  cell for rounding and the boxes that sit on it did not. The crown is the one place this mass
  stays square; its rounding belongs at the back corners, which it has.
- **HAUNCHES AS CRATES.** Two separate blocks of different widths standing off the flank - from
  behind, luggage. One mass per side, flush with the body, stepping down toward the rump. A
  haunch is not something you can see daylight behind.
- **THE PANEL RAN TO 80% OF THE HEIGHT**, leaving the head a narrow band above it.
- **ONE FLAT TONE OVER 1,300 CELLS** - the flattest surface in the build, against a reference
  whose brick varies across the mass. Patches of the mid tone now, on the flanks where they can
  be seen rather than only on the crown.
- **THE SNOUT TEST WAS READING THE BOUNDING BOX**, whose front plane is now two splayed toe
  tips. A test that reads the bounding box measures whatever sticks out furthest, which is not
  the question; it reads the pale panel's own plane now.


#### Three more shapes, after "overly square, the feet are random lines, the eyes are
strange giant boxes"

- **A FOOT IS A PAD WITH THE GAPS BETWEEN THE TOES.** Three one-cell prongs splayed wide with
  air between them are three strokes on the ground. Then a solid pad with its TIP CORNERS
  notched off is a PLUS SIGN, which is what a corner notch makes. The web runs the toes' whole
  length: pad first, then prongs.
- **A CHAMFER IS A RULE ABOUT AN EDGE, AND AN EDGE IS ONE AXIS AT A TIME.** The first attempt
  at rounding the box measured the distance from both ends at once and cut slots up the flanks.
  Every vertical arris and the top edge step in now - except the crown's FRONT edge, which
  stays square on purpose, because the eye boxes stand on it and rounding it away is exactly
  what left them hanging over air a pass earlier.
- **AND IT IS A LOAF, NOT A CUBE.** The reference is clearly deeper front-to-back than it is
  wide; at 15 deep against 13 wide mine was close to cubic, which is the other half of "overly
  square". 19 deep. Both that and the toe length come off `length`, so one number moved them.

#### The tests changed with the reference, deliberately

They pinned 1.0:0.75:0.5 and a knee, a haunch and a shin - the mob's proportions and my own
invented anatomy. **A test that pins a proportion is pinning a DECISION about which reference is
being copied**, so it has to change in the same commit or the suite quietly enforces the thing
that was rejected. They pin the CONSTRUCTION now: one pupil per eye set in a dark band under a
body-coloured lid, the boxes resting on the head, the panel continuous in height with a lip cut
into it. The next pass cannot drift back to a ring.

#### The blind alley, recorded because it was confidently wrong for three passes

The house and the mob both look like ONE MASS rather than an articulated head-waist-haunch, so I
rebuilt the animal as a single box on that reading. It came out a crate twice - as a plain
cuboid, and as a per-station taper, which insets every station independently and ribs the
flanks. **The error was taking the HOUSE as evidence about a creature**: it works because a big
box plus an eye band, a belly band and separate legs says frog-BUILDING. Two references agreeing
on a feature does not mean they agree for the same reason.

**1,584 blocks, one piece, 0 problems, 0 overlap, all cheap, sanctum clearance 4.** Still not
matched: the reference's body is BRICK with real texture across it and ours is plain planks in
flat colour, and `render3d` has no emission, so the pupils and the toe pads read dull in every
sheet here when in game they glow.

### The panel verdict, recorded (2026-08-28)

**Lofted build - FAILED, and Jack failed it before the panel did.** *A lumpy wedge; could be a
rock or a shrew.* Two measurable causes: the eye dome sat two courses UNDER the back line and the
knee three under it, so the only features that say frog were inside the outline.

**Box build - PASSES head-on and in plan, MARGINAL in profile.** Head-on it is unmistakable and
it is the view a frog is actually known by: a wide flat skull, two gold eyes bulging off the top
corners with black pupils, nostrils, a dark mouth line straight across, a pale chin under it. In
plan the eyes lead, the head is a clean box, the waist shows and the feet splay. The profile is
still the weakest - a low mass with a raised head and an eye bump, and at 17 blocks a stranger
might say toad. **If it has to read from the ruin path 40 blocks off it wants building at 1.5x**;
every number in the generator is a fraction of L, W or H, so that costs one line.

**Still open:** the frog defers 6 cells to `Lowland Thicket` (plant drifts inside its footprint),
so build the Thicket first - which is what `defer_to` records and what the build order derives.

### The last deep pass: BOXES WERE ALSO WRONG (2026-08-28)

Jack: *"still can be improved significantly, please audit in full and compare against
references, last deep visual pass across all angles to fix."* Rendered every bearing and the
review sheet, and the verdict was worse than the previous one recorded here - because the
previous verdict was taken from ORTHOGRAPHIC sheets and this one was not:

| | |
|---|---|
| profile silhouette | unnameable - a lumpy stepped box with a tab on it |
| value panel | one flat grey ZIGGURAT, four horizontal ledges, no rounding anywhere |
| plan | a rectangle: no waist, no head, the haunches two bolted-on crates |
| head-on | a pale rectangle between two sunglasses - **there was no mouth** |
| palette | 81% one block, 6% accent tail against the corpus median of 18.5% |

**THE FINDING, AND IT REVERSES THIS FILE'S OWN ADVICE ONE LEVEL DOWN.** Going from a loft to
BOXES was right about the head and the eyes and wrong about everything else, and each fix made
it worse in the same way. Four correct pieces of frog anatomy, four pieces of luggage:

    a haunch and a shoulder bolted on  ->  crates you could see daylight behind, four ledges a flank
    a waist dip two courses deep       ->  a head crate and a rump crate with a slot between them
    the haunch raised across the back  ->  a flat-topped box: a rucksack
    the knee raised at the flanks only ->  a rectangle floating above the outer wall

**AT THIRTEEN WIDE AND EIGHT COURSES TALL THERE IS NO RESOLUTION FOR ANATOMY.** Every feature is
one or two cells, and a one-cell step at this scale is not modelled form - it is THE SEAM BETWEEN
TWO OBJECTS. That is what the download corpus already said about exactly this scale and what this
file already recorded twice without applying it: a sculpture reads when it is **one convex mass
with a pattern on it** - the ladybird, `Warm Snooze`, and Coldrobin's frog, which is one
flat-fronted box and nothing else.

So: `col_top` is CONVEX and monotonic - the back line and the plan may rise to one peak and must
fall from there, never twice - and every frog cue moved into the COAT.
`test_the_mass_only_ever_falls_away_from_the_head` pins it, because the next person with a good
idea about anatomy will re-invent all four.

#### Two features were missing in every view, and no geometry substituted for either

- **THERE WAS NO MOUTH.** Five passes of eye work on a front that was a pale rectangle. A dark
  line across the panel that TURNS UP at the corners is what makes a blocky front read as a
  FACE, and it is the single biggest change in the whole rebuild. Graysun's statue draws
  exactly this and I had been reading it as a band rather than as a line.
- **THE EYE WAS BLACK ON ITS OUTER FACE**, so it existed in exactly ONE view: every bearing but
  head-on had two dark tabs and no eye at all. One iris cell on the outer face fixes the
  profile. And the front band needs TWO - the reference's single bright block is right at the
  scale it is drawn, but on a thirteen-wide head one cell in a four-cell band is a GLINT, and
  the orbit sheet read the pair as sunglasses.
- **AND THE MOUTH CARRIES ON ROUND THE JAW.** Drawn on the front plane alone it was a
  head-on-only feature; three cells back along each flank and the profile has a mouth too.

#### The coat, and the corpus number

Blotches are **DARK**, and that was measured wrong first: pale drifts read as WEAR - bleached
patches on the flank and dead centre of the rump. A real frog's markings are dark on a lighter
skin. Drifts have a **LOBED radius** (noise on the boundary, never on the cell - the thicket's
rule) and are painted only on cells with a face to the air, because a painted interior cell buys
a number and shows nobody anything.

Dominant block 81% -> 73%, and the value panel went from one untouched grey to a mass that
carries light. The accent tail is 8.9% against the corpus's 18.5%, and **it is not being chased
further**: this file already deleted "move a palette number" as a reason to put a block
anywhere, when the deck gallery and then the deck soffit both did it.

#### Four traps, each of which shipped a clean audit

- **A FROGLIGHT LANDED ON AN EYE.** The lamp's `over` list takes the body's own block and an eye
  box's LID is the body's own block, so it painted one white square in the middle of an eye. A
  lamp may not touch a column whose top stands above the body.
- **The lamps were read off `length`, not the body's own DEPTH.** `_f(0.88, 17)` is fifteen
  stations into a twelve-station body, so the late spots never landed at all and the pair meant
  for the hips ended up on the last course - tail-on, two pale squares side by side on a dark
  rump are a second pair of eyes.
- **Five lamps scattered on the back are a DICE-FIVE in plan**, and the loudest thing on the
  animal. Landed in the middle of a dark drift each one is a spot with a lit centre, which is a
  marking. (They are dull in every sheet here and glow in game - `render3d` has no emission.)
- **Five bands terraced where four do not.** Each of the last four stations stepped in and down
  by one and the rump came out as a flight of little ledges - which is the exact failure a
  coarse band table exists to prevent, reintroduced by making the bands narrow.

#### And three tests had to change in the same commit

They pinned a `haunch` part, a single pupil per eye, and a lip notch in the belly panel - all
three of which are decisions this pass reversed. **A test that pins a proportion or a part is
pinning a DECISION about which reference is being copied**, so it changes with the decision or
the suite quietly enforces the thing that was just rejected. This file has said that once
already, about the mob's proportions; it applies to a construction as much as to a ratio.

The monotonic test needed two corrections of its own, both instructive. Measured from the
BOUNDING BOX, station zero is a lamp in a toe pad and every animal fails - the body begins at
the pale panel's plane. And plain non-increasing was too strong: it failed the front corner's
own chamfer, which is a rounding of the mass and not a second object. The property wanted is
CONVEX - one peak - not monotonic.

#### And the eyes were a station too far forward

Jack, on the rebuilt animal: *"its eyes are pushed further vs the reference images which have it
set a block back."* Correct, and it is an error the whole rebuild inherited without questioning -
the boxes had overhung the front plane since the box build, where they were meant to read as a
brow. **A cell is a sixth of this head's depth.** Proud of the face they give the animal a jutting
brow with a shadow under it; the reference's eyes sit ON the head with their front in the SAME
PLANE as the face. Set back one station, the head-on view gains a clean brow course in front of
them and nothing else moves.

It also let a test get stronger: `test_the_eye_boxes_sit_on_the_head` tolerated half its lid cells
standing over nothing, because the overhang made that unavoidable. Flush, the answer is ZERO, and
that is what it pins now.

#### THE FEET ARE STAIRS, and the renderer could not see it

Jack, sending the Graysun statue back a third time: *"i think the feet still are crappy, this one
had feet done by using stairs."* That is the whole answer to four failed foot shapes, and I had
been re-arranging cubes instead of reading the material.

**A CUBE TOE ENDS. A STAIR TOE TAPERS.** A toe built of full blocks stops at a vertical face one
block high, which is a plate - and that is why every arrangement of them read as a rake, a comb, a
plus sign or a set of random lines however the prongs were spaced. Half height at the tip, sloping
to the ground, is what a toe actually does, and it is one block per toe.

It is also a gap the whole repo has and had already measured: against the download corpus we place
stairs at **0.64 per thousand cells against their 4.51** - seven times under - and this design had
none at all. `CLAUDE.md` listed "fences and trapdoors" as the biggest remaining vocabulary gaps and
put stairs on the *already-solved* side, because `gen/stairhead.py` uses them. One generator using
them for a staircase is not a vocabulary.

Two more things came out of the same note:

- **THE FEET BELONG AT THE BODY'S OUTER CORNERS.** At `bw - 2` they were inboard, tucked under the
  belly with a slot between them; the reference's sit at the foot of the arms with the whole pale
  front showing between them down to the ground.
- **THE ANKLE RISES TWO COURSES and steps down to the pad**, so the foot has something to taper
  FROM. Flat on the ground at one course there is no fall to describe, and the reference's feet are
  plainly two blocks at the heel and one at the toes.

Four stations deep and no more. At five - three toes two cells long - they read beautifully close
up and **took over the head-on view**: 38% of a thirteen-deep animal's length was foot. The taper
does the work the length was trying to.

#### `render3d` now draws stairs and slabs at their real shape

**THE FEET WERE REBUILT WITH STAIRS AND EVERY SHEET HERE DREW THEM AS FULL CUBES.** The change was
unjudgeable - which is the same failure as rendering an animal orthographically along its own axis,
the one this file already records: *the tool cannot show the class of error being hunted*. Shipping
a change nobody can look at is how the axolotl's head happened.

`render3d.subdivide` expands every block to **2x2x2 half-cells** and fills them from the block's
shape: a slab is four, a stair is six, everything else is eight. Nothing in the raycaster changed -
it still marches a boolean grid - so this cost about forty lines and roughly 2x the march, which on
an animal is tenths of a second.

- **Applied only to models that actually contain a shape block.** AO is computed on the half-cell
  grid, so it is finer, and the image genuinely moves; applied to everything it would silently
  shift every sheet in the repo. Six of the eight animals contain no shape block and render
  bit-identically. `look.py --no-shapes` is the way back.
- **AFTER the scale figure**, or the player marker subdivides separately and stops being 2 blocks
  tall.
- **The stair convention is the load-bearing part and a picture cannot check it.** A stair's TALL
  side is its `facing`; until now this renderer drew both directions identically, so a backwards
  flight and a correct one produced the same image. `tests/test_render3d_shapes.py` pins the mask
  per facing, and `test_the_toes_taper_and_they_lean_the_right_way` pins the frog's own toes -
  which lean BACK toward the body, because a toe tapers down and forward.

**This corrects a claim in this file.** It said real block models "buy almost nothing for ANIMALS,
which are near-100% full cubes". That was true only while no animal used a shape block; the moment
one did it was wrong, and it was the reason the gap went unfixed.

#### A HAND IS MOSTLY AIR

Jack, on the first stair version: *"hands are now really thick and strange, how do we make the
replica which is a bit more refined and feels cleaner."* They were - **twenty cells apiece, and
solid**: a 3x2 pad, a five-wide web laid over it, and a two-course ankle behind that. Three courses
of stacked mass with a taper stuck on the front is a boot with claws.

The reference's hands are the opposite thing. They are almost entirely **NEGATIVE SPACE** - a flat
wrist ONE course deep and ONE station deep, and thin toes with a clear cell of air between them.
Eleven cells, and nothing stacked on anything except where the wrist meets the body.

**The gaps are the feature.** That is the same rule as the eye pair needing a clear cell between
them, and the ladybird's spots needing four courses of spacing rather than three - and filling them
in to make the shape read stronger is the same mistake, made a fifth time. Adding the stairs was
right and it was not enough on its own, because a taper on the front of a solid lump still leaves
a solid lump.

The animal is 16 long now rather than 17, and the church clearance went 4 -> 5.

##### The wrist light: three candidates, and the economy picked

The hands need their own light and that is MEASURED, not assumed - `hand_lamp: false` and six
cells over them stand at block light zero, because the back lamps are seven courses up and five
forward and light does not turn corners.

But `ochre_froglight` is 209 RGB from `acacia_planks`, so at the hand's leading edge it read
head-on as a pale CHIP knocked out of the toe. Measured against the foot:

| | ΔRGB | tier | |
|---|---|---|---|
| `glowstone` | 53 | **expensive** | |
| `jack_o_lantern` | 46 | cheap | a FACE texture - the `bee_nest` trap |
| `shroomlight` | 95 | **expensive** | the right block on any other economy |
| `ochre_froglight` | 209 | cheap | what we have |

Two expensive blocks for a cosmetic is not a trade this design makes, so the fix is PLACEMENT: the
wrist's inner corner, shaded by the body's own front, which is the least-read cell of the hand.

**And a light must keep AIR OVER IT.** Tucking it under the wrist's rise would have switched it
off - light travels through air, and a lamp walled in by its own foot lights nothing at all.

**1,278 blocks, one piece, 0 problems, 0 overlap in context, all cheap, 16/16 frog + 9 renderer.**


### IT IS UPRIGHT, and the rule that stopped it being so was mine (2026-08-29)

Jack, on the finished loaf: *"no, this isnt good, i need you to really think about this, and
audit carefully, visually this sucks."* He was right, and the audit found something bigger than
the frog.

**THIS FILE STATES, IN CAPITALS, THAT A SCULPTURE AT THIS SCALE MUST BE ONE CONVEX MASS WITH A
PATTERN ON IT. That is a SCALE law and it was written down as a universal one.** It was measured
at eight courses of body height, where every feature is one or two cells and a one-cell step is
not modelled form but the seam between two objects. The reference does not delete the anatomy -
it makes the animal TALL ENOUGH TO HOLD IT. At twenty-two courses a head is seven cells, an arm
fourteen, a haunch five: those are masses.

And the evidence was already in this file. *"It came out a crate twice"* is recorded here about
the two earlier one-mass builds; the third was called a crate by Jack. **A rule that produces a
crate three times running is the rule that is wrong**, not the execution.

The lot was re-measured before anything was drawn: **15x13 is the largest pad at roll <= 1 and it
carries 107 COURSES OF HEADROOM.** Height was always free here; the footprint was the only
constraint, and the loaf was using 12 of the 107.

#### Four things the rebuild got wrong first, each a general lesson

- **UPRIGHT IS NOT THE SAME AS TALL.** The first attempt was a twenty-six course column with a
  head at 15% of the height: a gravestone with a frog on top. Measured off the picture the head
  and eyes are about **40%** of the total and the body below is **wider than it is tall**. A
  statue is not a measurement of an animal.
- **A PALE RECTANGLE INSET IN A DARKER FRAME IS A DOOR.** Four passes went into making the mass
  squatter, tapering it, darkening the arms and shortening the torso, and the front stayed
  architecture until the BELLY ITSELF stopped being a rectangle. It is a lens now - widest at
  the middle, closing top and bottom. The straight line is what says architecture; the curve is
  what says creature.
- **THE HEAD MUST BE SHORT FRONT-TO-BACK.** Given the body's own depth, the whole rear was one
  flat wall from crown to ground and the profile read as a BOOT. A sitting frog is head forward
  and high, rump back and low: the head is the shallowest band and the haunches the deepest.
- **THE ARMS HANG IN FRONT OF THE CHEST, not out at its sides.** Beside the body they are
  swallowed by the haunches, which are wider - the first pass had arms visible over six courses
  out of twenty-four. They also follow the body's own outline, because at a fixed offset they
  filled the waist back out and HID the pinch: the body read as a straight-sided box because its
  own silhouette was covered by its arms.

#### The relief pass: every hard step gets a stair

The last gap the corpus measured, and it was not close - outside sculpture runs about **17%
detail blocks** and this animal ran **0.5%**. Every plane met the next at a hard right angle,
which is what makes a voxel mass read as a crate however well it is proportioned, and it is why
the reference looks like carved stone and ours looked like a box.

The rule is general and places no cell by hand: **wherever a course steps IN, the shelf it leaves
takes a stair leaning into the wall above it; wherever it steps OUT, the overhang takes an
upside-down stair tucked under it.** Every hard ledge becomes a cove. `shell.py` has done exactly
this for years and was never pointed at an animal.

- **Only the skin, and only single steps.** The face, the belly, the eyes and the feet are drawn
  features and a stair through one of them is a hole in a drawing; and a stair cut into a
  two-course jump leaves a gap rather than a chamfer.
- **The relief is the body's OWN material.** A chamfer is geometry; a stair in a different tone
  is a stripe.
- **It found that the head was the flattest thing left**, because a band of constant width has
  no step to chamfer. Giving the crown a one-cell draw-in put relief on the head - and the eye
  pair had to narrow from five cells to four to keep every lid over solid crown, which is the
  third time on this animal that a box has been caught standing over air.

#### And two colour findings

- **`bone_block` alone reads cool grey** next to a warm body - 21 apart in R minus B where birch
  is 71. The belly is two tones now: the bright core, and a warmer birch rim that stops the oval
  reading as a cut-out pasted on the chest.
- **`chiseled_sandstone` measures better than either and is NOT WITNESSED anywhere in this
  world.** The tier table calls it cheap, which is a gap in the TABLE, not evidence the server
  can supply it - and this file already recorded "sandstone does not exist on this skyblock".
  Rule 12 from a new direction: ask the world, not the table.

#### And then the legs and feet, which were three faults in one

Jack: *"we're much closer with the frog but the legs/feet arent right."* A close look at the
bottom found three, and the first is the one worth keeping:

- **THE HANDS AND THE HIND FEET HAD MERGED INTO ONE L-SHAPED PLATE** round each front corner,
  and the animal read as standing on a PLINTH rather than on four feet. Both were correct on
  their own; they simply ran to the same stations. The separation has to be in DEPTH, not in
  width - the hands live in front of the body's face, the hind feet start behind it, and the
  arm's own station is the clear course between them.
- **A HAND IS MOSTLY AIR, and it was two solid courses.** A wrist row and a web row under three
  toe stubs is a flat PLATE with notches in its front edge, which is what four foot shapes on
  the loaf were as well. One course of wrist and three toes with a clear cell between them is
  eleven cells and reads as a webbed hand.
- **THE LOW LIGHT GOES ON THE HOCK, NOT IN THE HAND.** The hands genuinely need lighting -
  without it the air over them measures block light ZERO, because the body's lamps are high on
  the back and light does not turn corners - but a cream froglight set in an acacia wrist is a
  pale CHIP, and at the bottom of the animal it was the loudest thing on it. Moved to the
  haunch's outer face a course off the ground it is a lit spot on a flank; it still reaches the
  hand round the corner, because light floods air and needs no line of sight, and it lights the
  hind foot on the way.

#### One side was lumpier than the other, and the mass was symmetric by construction

Jack read it straight off the render, and he was right: **104 of 1,615 cells differed across the
sagittal plane.** Every part of this animal is built for `s in (1, -1)` and every span is centred,
so construction was never the problem. Two other things were:

- **THE COAT'S DRIFTS EACH CARRIED THEIR OWN SIGNED OFFSET**, so the dark blotches landed in
  different places left and right. **A dark patch reads as a RECESS**, which is exactly why an
  unmirrored coat looks like a body dented down one side rather than like markings. A real frog's
  blotches are not symmetric; a STATUE of one is, the reference is, and the rubric has a whole
  dimension for this that allows asymmetry only where it was deliberately asked for.
- **`put` REFUSES A CELL THE TERRAIN OWNS**, and this lot rolls a course, so a foot cell existed
  on one side and not the other. One cell - it only takes one. The mirror is ENFORCED now rather
  than assumed, and dropping is the only safe direction: the missing cell is missing because
  something real is already there.

**And a facing MIRRORS, it does not COPY.** Written the obvious way the sweep assigned each cell's
state verbatim to its twin and **60 of the 134 stairs came out facing the same way on both sides** -
a chamfer leaning into the wall on one flank and out of it on the other. Only the ACROSS axis flips;
a stair leaning fore or aft leans the same way both sides. **`render3d` had learned to draw a stair
as anything but a cube the same day**, so a day earlier this would have been invisible in every
sheet here and wrong in game for ever. That is the second defect the sub-block renderer has caught
in one session, and it is the argument for having built it.

**AND THE SKIRT WAS THE REST OF IT, which the first fix explicitly waived.** It fills each column
down to its own ground; the ground under this site rolled THREE courses; and **all 34 of its
columns came out on one flank**, in the body's own dark tone. That is a fringe hanging off one set
of feet, and it is what Jack saw the second time.

A fill CANNOT be mirrored downward - `put` refuses a cell the terrain owns, so the high side can
never be given what the low side needs, and equalising the other way leaves the low side floating.
Two things could be fixed and both were:

- **RESEATED on the flattest ground the lot allows.** A search over every placement of the real
  13x15 footprint that still clears the church by 3 found roll **2** at (-24169, 29976) - 161 of
  195 columns at Y39. There is no roll-0 site: the lot has none for a footprint this size.
- **EVERY FILL CELL TAKES THE MATERIAL OF THE CELL IT CARRIES.** Built as a proper base in the
  church's own `polished_blackstone_bricks` it put a black post under every separate toe and the
  animal looked like it was wearing BOOTS - **a plinth that follows the outline of a splayed foot
  is not a plinth, it is a shadow.** Matched to what it carries, the fill reads as the toe
  REACHING the ground, which is what it is.

**42 unmirrored cells down to 23, all below the belly plane, all colour-matched.** Zero at or
above it, geometry and colour, and the test now bounds the fill as well as forbidding the rest.

**1,614 blocks, one piece, 0 problems, 0 overlap in context, all cheap, 18/18 - and 0 geometry and
0 colour mismatches across the mirror above the belly plane.** Five tests
changed with the decision - they pinned h/w 0.55-0.92, a monotonic mass, gold-in-black eyes, a
rectangular panel and one-way stairs, and every one of those is a thing this pass reversed. One
of them was measuring the CHIN rather than the belly, because the head's front plane stands
forward of the chest's and `min(along)` picks the wrong plane.

