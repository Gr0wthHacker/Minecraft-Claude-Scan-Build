## The lowland scene, completed: the ring-gate and the axolotl (2026-08-21)

Two additions off the 13:10 scan, one retirement, and two re-sitings. Everything below was
measured before it was designed, and the numbers picked most of it.

| design | blocks | what it is |
|---|---|---|
| `Lowland Portal` | 488 | a D25 ruined ring of blackstone masonry at (-24171, 30025), Y44-70 |
| `Lowland Axolotl` | 989 | pale pink, curved, head over the shallows at (-24201, 29988), Y39-49 |

**The portal stands in the entrance light.** 628 lowland columns are open to real sky and 493 of
them are ONE blob at X-24186..-24158 / Z30015..30041 - the shaft players descend to enter the
underworld. The ring's footprint is 96% open sky, covers zero lanterns, ground Y45-52, headroom
139, and the sightline from the pond's west bank is clear. Aperture faces east-west: frontal from
the pond, walk-through on the axis of travel. Behind it the massif crests and drops into void, so
the upper aperture frames open sky - the gate appears to open somewhere else, bought entirely by
siting. The vanilla ruined-portal palette is CHEAP here (polished/cracked/chiseled/gilded
blackstone) while obsidian, crying obsidian and gold are expensive; the portal-energy accent is
amethyst clusters (cheap, light 5) and two soul lanterns - the one cold light in a lowland of 122
warm ones. The ruin follows the void tower's rule: regular coursework, ONE broken arc
(upper-north, balancing the bat rock hanging upper-right from the pond view), the crown keystone
surviving, the fallen piece ONE half-buried chunk. Emission is air-only (the courthall rule), so
the bottom arc terminates against the terrain and burial costs zero overlap and zero dig.

**The axolotl won on the planar/columnar rule, not on taste.** Jack offered otter or beaver "etc";
an otter's identity is a pose needing water it cannot legally occupy, a beaver is a rodent barrel
four blocks from a fifty-block rodent, and an axolotl is all hardware - six flat gill fronds, a
tail fin, a wide flat head, splayed limbs, the gecko category - plus it is THE lush-caves mob, so
the naming test is instant. Size came from the gills: a frond needs ~4x2 cells to read as a frill
(the ladybird spot-spacing lesson), three per side need a head ~8 wide, so total length 26. It is
half the capybara and does not dwarf its own pond. Pale leucistic on purpose - the flamingo owns
saturated pink, and the two must not twin across the water. Not one water cell is replaced: the
snout and gills OVERHANG the shallows, belly clamped a course above any wet column.

**The heron is retired, Jack's call: one of heron/capybara, not both.** The capybara stayed - the
flamingo already holds the wading-bird slot and a second bird on the same skeleton in grey was
the redundant one. Retiring it also frees the pond's west bank, which is the main vantage toward
the ring. Never built (zero wool below Y70 in the capture), so nothing is orphaned.

**The massif moved the ground under the scene, and the fixes are worth keeping:**

- **`finish.trim_buried`** (new, opt-in): design cells the terrain already owns are dropped at
  the seam. A cell inside a ground rise can never be placed (a printer places into air), would be
  invisible if it were, and stands as permanent amber in `/cscan check` - the Court Hall's
  unbuildable-cells problem, solved at the seam for designs where terrain wins by intent.
  Same-state cells stay: they are built progress. Capybara yielded 9 cells, flamingo 7.
- **The flamingo stands on a measured knoll now** - (-24165, 29988), a single-column local max at
  42 with neighbours 40-41, so the foot grips and everything drooping a course below the feet
  clears every rise. On rolling ground the foot column must BE the local max, or the plumage digs.
- **The capybara runs at feet 41** - its low cells sat level with the risen massif's top course.
  A mid-gallop animal with a foot or two airborne is the pose, not a floating statue. (The
  quadruped seats its own vertical by probing `under`; `feet[1]` does not move it.)

**Five traps inside the two generators, each of which shipped a clean audit and a wrong build:**

- **The spine walked INTO the gaze.** Stations stepped toward `look_at`, so the body extended
  through the nose and the animal faced away from its own pond. t=0 is the nose; the walk goes
  tail-ward, opposite the heading.
- **Gill fronds rooted at the spine spent themselves inside the skull** - nine red cells reached
  the air. Root anything that fans off a body at the BUILT SURFACE and run its whole length
  outward.
- **The fin floated.** Its base was computed from the float the sections were sampled from; the
  rounded cells drift a course away. It rides `top_at` - the highest cell each column actually
  placed - which is the detached-ossicone rule applied to arithmetic.
- **A tree canopy severed the flank.** Cells placed through gaps in oak leaves belong to the tree,
  not the animal. The site was moved clear of the measured canopy (X-24210..-24206 / Z29981..85),
  and `_prune_severed` now guarantees one component whatever the foliage does.
- **The fallen chunk sheared into three on ground steps.** A rigid fallen arc BRIDGES a dip: each
  column is seated on its own real ground and rises to meet the tallest of its face-neighbours -
  built UP on the low side, because downward filler on the high side lands inside that column's
  own terrain and is silently skipped.

**Panel verdicts, recorded (2026-08-21).** First pass: both panels passed with two criticisms -
far-side gills sparse in plan, and the white dorsal fin reading as a mohawk. Jack said the
axolotl needed work, and both criticisms were the work. **v2, same day:** the fin is MAGENTA -
the Minecraft mob's own tail-membrane colour, and the general rule is that a fin is darker than
the body, never a highlight; the gills went from 38 accent cells to ~140 (length 6.5, vertical
frill, three stitched FILAMENT barbs per frond - barbs are what turn three red sticks into a
frill); the head got a real neck pinch (skull as wide as the body, 0.46W, pinched to 0.36W
behind the gills - without it the animal read as a worm with a face); and the muzzle carries a
7-cell magenta SMILE seam below the eyes, which is half of what names an axolotl and no gill
work substitutes for. The rework pulled the nose a cell back from the waterline - the overhang
test caught it (2 cells over water against a floor of 3) and the site nudged one block pondward.
v2 silhouette breaks at the gill crown, which the first one never did.

**The face took three more passes, and the lesson is about the GRID, not the face.** Jack: "head
on it looks like a blob." The head was flat-topped and correctly shaped - and aimed 40 degrees
off the block grid, so its "flat" face was a diagonal staircase of corners in game: eyes at
different depths, the smile stepping cell by cell. **An orthographic render along the body axis
cannot show this failure** - projecting along the diagonal de-jags it by construction, which is
why every sheet looked right while the game looked wrong. The fix is the classic builder rule,
now in the generator: **the gaze is CARDINAL and the head is straight; all of the body's curve
lives in the tail** (`_spine` ramps curvature from zero through t=0.28). Three more findings from
the passes:

- **The skull section is exponent 6, not 8** - flat across the middle, ONE step down at the
  cheeks. 8 was a slab; "a little more rounded" was the correct review.
- **The face is the full-width plane and the mouth sits ON the chin line.** A two-step nose
  chamfer left a narrow protruding muzzle that the smile filled edge to edge - a magenta blob
  where a face should be - and a mouth at mid-height reads as a nose.
- **The eye bead is the FRONTMOST body cell of its cheek band**, so by construction nothing can
  stand in front of it. Chosen by proximity instead, the tail's curve shifts the centroid, the
  head line drifts half a block south, and one bead landed a cell deep - painted over by its own
  pale ring from exactly the head-on view. Both eyes now read head-on AND from the plan.

Cross-design overlap 0 across all six lowland pieces; nearest approach is the capybara sprinting
4.2 blocks past the gate's pavement, which is the story anyway. `tests/test_ruinring.py` (10) and
`tests/test_axolotl.py` (9) pin the geometry, the break, the seam rule, the anchors, both-sided
gills, dry feet, the wet nose, and the pale eye ring. Tracked: `sync.yaml` progress carries both;
`designs.json` now lists 25.

