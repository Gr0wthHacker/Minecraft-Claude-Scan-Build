## The causeway's two new sculptures (2026-09-01)

Jack, on the four stops the isthmus shipped with: *"get rid of the gecko and bat - those are
used assets, we want NEW things, identiy and buiild new scuiptures in those places"*. The heron
and the sloth stay. The hollow reach's two stops are now `gen/balloon.py` and `gen/wyrm.py`,
written for those two spots and for nothing else.

| | blocks | what it is |
|---|---|---|
| `THE AERONAUT` | 2,299 | a moored show balloon - envelope, four rope lines, a basket. t=0.26 |
| `THE PALE WYRM` | 985 | a hooded serpent reared off a black milestone. t=0.80 |

Both are all cheap tier bar 97 `deepslate_bricks`; both are one 6-connected piece at BOTH
orientations they can be sited at; neither places one block of light.

### The rule they were chosen against, and what it ruled out

CLAUDE.md's measured line is PLANAR/COLUMNAR against VOLUMETRIC, plus the third case the
download corpus added - **one convex mass carrying a pattern**, which is the ladybird and
`Warm Snooze`. A balloon is that third case with a column of rigging under it and nothing else
in it; a snake is the purest taper in nature and a hood is a flat plate. **Neither has a joint
anywhere**, which is the whole of what killed eight mammals here.

**A THEME PARK'S LANDMARKS DO NOT HAVE TO BE CREATURES, AND THIS REPO HAD NEVER TRIED ONE.**
The balloon is the first thing in `gen/` that is not an animal, a building or terrain, and it
is the easier of the two to name from a thumbnail by a wide margin.

Rejected, and why, so nobody re-derives it: an insect with planar wings (`dragonfly.py` is FIVE
components by construction and a new one would have the same trapdoor-gap problem); a moth or a
raven (too near the bat this replaces, and the heron); an armillary sphere or any ring form (a
voxel ring at this size is a jagged octagon, and it is diagonal-heavy exactly where
6-connectivity bites).

### THE WYRM'S FIRST BUILD WAS A COIL ROUND A COLUMN AND IT FAILED

Two and a quarter turns of banded body up a twenty-course obelisk. It was a real helix, one
connected piece, correctly tapered, correctly banded, and its **silhouette was a lumpy vertical
mass with a hook on the top** - a totem, or a chess piece. Nothing about it was nameable.

The cause is structural rather than tuning, and it is worth keeping because the idea will look
attractive again: **a coil round a column reads through COLOUR AND DEPTH, and its OUTLINE is a
bumpy column.** On this causeway there is nothing behind a sculpture but open sky, so the
outline is the whole of what survives, and every one of those 154 stations was being spent on
the one channel that does not carry.

Rebuilt: the coil is **one and a half turns at the BASE ONLY**, where it anchors the animal and
gives the plan a pair of concentric rings, and everything above it is spent on outline - a free
S of sixteen courses, a flared hood 11 wide and 9 tall with a dark rim and two eyespots, and a
head standing three blocks proud of the plate with an open jaw.
`test_the_coil_stays_at_the_BASE_and_the_rise_carries_the_outline` fails if that trade is ever
reversed.

Three smaller things came out of the same rebuild:

- **THE S SWINGS IN Z AS WELL AS IN X.** Kept in one plane the curve foreshortens into a
  straight vertical from the exact bearing a visitor standing on the spine has, and the animal
  reads as a post with a disc on it. A lateral weave costs nothing and keeps the profile's S.
- **THE HOOD'S RIM IS DARK BECAUSE A PALE PLATE AGAINST A PALE SKY HAS NO EDGE.** The rim is
  also what stops the plate reading as a paddle, and `black_wool` against `bone_block` is 175
  points of luminance - measured ACROSS families, which is the only place this economy's
  contrast has ever been.
- **THE MILESTONE MUST NOT BE BURIED.** The first coil started two courses up and swallowed the
  stone it was wound round, so the "pale animal on a black post" idea existed only in the
  docstring. The coil starts at 3.6 now and three banded courses show under it.

### Two faults that shipped clean and were caught only by looking

- **THE WYRM SHIPPED WITH ONE EYE. TWICE.** The eye was a computed offset onto a course where
  the skull is two cells wide, and the half-cell centring makes those two ASYMMETRIC about the
  midline - one side found a block, the other found air. No error, nothing in the audit,
  nothing in the component count, nothing in the bill. The probe now SEARCHES for a row wide
  enough to carry a pair and takes that row's outermost cells. **A feature that can silently
  half-exist has to be measured, not computed.**
- **A ONE-CELL SECOND COMPONENT.** The first tail was a thin dark tip laid over a thicker
  sweep, and the tip's last sphere came out at radius 0.62 detached - the ear-tip failure, in a
  build clean everywhere else. One path, one taper, banding chosen per station.

### The balloon: the gap is the feature, and eight gores was a beach ball

- **FOUR COURSES OF OPEN AIR** between the basket's rim and the envelope's mouth, crossed by
  nothing but four rope lines. Fill them and the silhouette is a blob on a stick. Same rule as
  the ladybird's spot spacing and the frog's hand: the negative space does as much work as the
  blocks, and `test_the_gap_under_the_envelope_is_REAL` asserts those courses hold exactly four
  cells.
- **THE RIGGING IS DEAD VERTICAL AND THAT DECIDED THE THROAT.** A real balloon's lines splay
  out to a much wider hem, and a splayed line is a DIAGONAL, which is not connected here. So
  the envelope pinches to a mouth no wider than the basket and the lines drop straight from its
  own corner columns. It is also what a balloon under inflation actually looks like.
- **EIGHT GORES IS FOUR FACES HEAD-ON, and it read as a beach ball.** A gore wants about four
  cells at the equator; a 16-wide dome has ~50 there, so ten gores is five cells. Ten it is.
- **THE CROWN VALVE IS ONE COURSE.** Given the top two it covered a disc of radius 5.5 out of
  7.5 and the PLAN - a view every visitor gets off the skyway - was a black hole with a
  red-and-white fringe round it. One course, and the gores are left to converge at the top the
  way a real envelope's do, which is exactly what a balloon looks like from above.
- **THE SCATTERED "WEATHERED PANELS" WERE DELETED.** They went in for tonal variety and read as
  dirty rectangles on clean fabric - the deck soffit's confetti in a third body. The tone comes
  from the gore, which is already a 158-point step; the one horizontal element is one band.

### The verdicts, recorded

**THE AERONAUT - PASSES both panels, at every bearing, and still reads at 6x.** It is the
strongest-reading thing on either span and the reason is not craft, it is category: a big
convex mass with a two-tone pattern is what this medium is best at, and everybody alive can
name a balloon. The value panel shows real rounding rather than a flat shape with a pattern on
it, and the plan shows gores converging - the money view a lot of sculpture here throws away.
*Minecraft player:* the basket, the sandbags and the rope gap are what make it read as a thing
somebody flies rather than a lollipop, and they are 77 blocks out of 2,299.

**THE PALE WYRM - PASSES at six of eight bearings, MARGINAL head-on and tail-on.** The
three-quarter views are the best: coil, weave, hood, head, in that order down the outline. The
profile silhouette is nameable on its own - a reared serpent. Head-on and tail-on the hood
dominates and it reads as a tall figure with a disc; the lateral weave stops that being a post
and does not fix it, and that is the price of a hood, which has to be square to *somebody*. At
6x it is a marker rather than a nameable animal - the balloon beats it there and always will,
because a taper is thin and a dome is not.

**Still open on it, and not guessed at:** it is 985 blocks against the balloon's 2,299 and it
shows at distance. Building it half again as big would fix the 6x reading and is a `scale`
away, but the stop's own room (`_CREATURE_ROOM` 13) has to grow with it and that widens the
causeway's bulge. Jack's call.

**Judge the palette in game.** Everything above is `render3d`, which draws every block as one
flat RGB out of the same database the palette picker optimises against - this file's oldest
recorded circularity. These renders are ground truth about GEOMETRY and OCCLUSION only.

### What the swap cost

**43,151 -> 39,903 blocks (-3,248, -8%), 0 problems, 0 expensive, 38,892 cheap and 1,011 ok**,
0 lamps in any coat, 0 spawnable cells dark.

    polished_blackstone_bricks   1999 ->  294    -1705    the gecko's stele, gone
    brown_wool                    674 ->  425     -249    the bat, gone
    moss_block                  13416 -> 11884   -1532    two much smaller stop bulges
    white_wool                      0 -> 1227    +1227    the balloon
    red_wool                        0 ->  942     +942    the balloon
    bone_block                      0 ->  572     +572    the wyrm

**IT GOT CHEAPER BECAUSE A SELF-CARRYING SCULPTURE NEEDS NO STRUCTURE.** A stele is 33 rows of
a 101-row span and a gantry is two piers and a 37-block lintel; a balloon's basket is five
cells across and a milestone is seven. That is the argument for writing a sculpture that brings
its own ground rather than borrowing one that has to be given some - `_site_standing` is three
lines where `_site_bat` is thirty, and there is no pier left that can miss its footing.

`_site_bat` and `_site_gecko` are KEPT and are no longer sited. A gantry and a stele are
general answers to "this creature hangs" and "this creature clings" and both are covered by
their own tests; deleting them narrows what the file can do without fixing anything. Putting
either back into `GAPS` is a decision about reusing an asset, not maintenance.


