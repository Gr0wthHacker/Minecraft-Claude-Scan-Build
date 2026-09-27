## The park, finally looked at (2026-08-31)

The park had grown to 93 module configs across three zones - `frontier` (21, `out/islandleft`),
`midway` (53, `out/newisle`), `hollow` (19, `out/islandright`) - since the section above was
written, and NONE of it had been rendered. Not "looked at in game", which was already known and
recorded; looked at AT ALL, by anything.

### The blocker was real and it was not only in `look.py`

`facing_yaw` reads the sidecar's `facing`, and an ANIMAL records it as a vector - the direction its
own nose points. Every generator built on `gen/park.py` records it as a COMPASS WORD instead -
park.py's own docstring: *"the direction the FRONT looks out; a visitor stands in the +facing
direction"* - which is the identical fact stated the other way round, so a word converts to the
vector `park._STEP` already gives it, imported from there rather than re-typed, because this file
has already recorded getting a bearing convention wrong by hand twice in one session.
`tests/test_render3d.py` gained three cases pinning it, including one built the same way as the
project's other bearing test: a synthetic room, and bearing 0 checked against the DOOR side versus
the back wall for all four compass words, not just one.

**`tools/panel.py` had the same gap and it was not a crash, it was a silent wrong answer.**
`facing[1]` on a two-element vector is a coordinate; on a string it is a CHARACTER, and Python does
not raise - `"east"[1]` is `"a"`, which is truthy. So the profile-axis rule picked `"side"` for
every structure regardless of which way it actually faced, and by the accident of which letter
sits second in each compass word, `"north"` and `"south"` happened to land on the right answer
while `"east"` and `"west"` did not. **Two of the four words a park building can face were silently
scored from the wrong orthogonal view, and nothing about a passing score would have said so.** This
is now converted through the same `park._STEP` map before the axis is chosen.

### `tools/parksheet.py`

Renders the whole park with `mcbuild/render3d.py` - perspective, cast shadows, corner AO, real
stair/slab shapes - never a second renderer. Scope is DISCOVERED from `configs/*.yaml` (any `gen:`
built on `park.py`'s geometry, zone read from `params.under`), not hand-listed, so it cannot go
stale the way this very file's "Still open" list just did. 93/93 modules placed a zone, 93/93
orbit sheets rendered clean in 159s, zero exceptions.

**The whole-zone view is NOT a camera hand-placed at the gate's own world coordinates.** The first
attempt was: stand six blocks in front of the gate, in the `+facing` direction, at head height,
via `_Frame.at` - the exact arithmetic `park.py` places every wall with. It produced a frame that
was 49% solid, near-black, from floor to the top of the image. The camera was not inside anything -
every one of its own voxels tested outside the model's box - it was simply standing a few blocks
from something tall and dark, because the base captures still carry the leftover starter-pad
terrain this file already warned about ("the starter island is in the way... never fully cleared"),
and six blocks of clearance was not enough to know that in advance. **A precise world-coordinate
camera is exactly as fragile here as the hand-placed light and hand-placed origin problems this
project keeps re-deriving rules against.** The fix reuses `r3.orbit`'s own content-box framing,
which every other sheet in this project already trusts for the same reason - it cannot clip into
debris it does not know is there - aimed along the gate's own bearing (`park._STEP` again) so the
camera still sits on the side of the zone the gate is on.

### The verdict, zone by zone

Measured, not guessed: for each zone, the fraction of its real 99x99 plot with a built column at
all (paved), against the fraction with a column 3 or more cells tall (actually furnished, not just
floor):

| zone | paved | furnished (>=3 tall) | blocks |
|---|---|---|---|
| frontier | 72.6% | **24.0%** | 21,813 |
| midway | 81.1% | **48.4%** | 32,657 |
| hollow | 69.5% | **19.3%** | 24,005 |

**The zones are floored, not furnished.** All three are paved across most of their plot - this is
not the earlier "single small structures on a mostly-void lot" complaint the park was rebuilt to
answer - but in frontier and hollow, three-quarters of that paving carries nothing taller than a
curb. The establishing shots read as one dense cluster sitting in a large flat grey yard, which is
visible in `out/parksheets/zone_frontier_view.png` and `zone_hollow_view.png` before any number is
computed. Midway is the one zone where the paved area and the furnished area are close, and it
reads that way - `zone_midway_view.png` and `zone_midway_plan.png` are the strongest single images
in the whole set, with the Big Wheel and the Carousel readable as themselves from the establishing
distance and the plan legible as a real fairground floor.

**What names itself from the silhouette alone, no thumbnail needed:** `Carousel` (striped conical
roof, mounts visible on the platform), `Grand Fountain` (tiered basins, a spout, water), `Windmill`
(the crossed sails read at every one of the eight bearings, including the 90/270 profiles where
they foreshorten to a thin cross and still read as sails rather than as noise), `Prospect Tower`
and `Clock Tower` (crenellations, string courses, window slits - both correctly read as watchtowers
though the "clock" face on `Clock Tower` is a plain pale panel, not a dial), `Haunted Manor` (gabled
roofs, a corner turret, rows of glowing windows - the single strongest building in the park),
`The Graveyard` (headstones at varied height, a central obelisk, an archway - the best piece of
"connective tissue" content anywhere in the set), `Iron Railing` (a fenced gate with headstone-
shaped posts, doing double duty as both a boundary and a theme statement), `Tin Can Alley` (orange
"cans" visible on its counter - a rare case of a fairground GAME actually showing what it is).

**What does not, and specifically why:**

- **`Founders Statue` is not a statue of a founder.** It is a striped obelisk on a pedestal - no
  figure, which is the right call given this repo's own retired-mammal history (a human figure at
  this scale would fail exactly as the jaguar did), but the NAME oversells the object. Either build
  it as a monument and call it one, or accept that a figure is out of reach here the way an animal
  is.
- **`Deep Mine` has a door and the door does not read.** `out/parksheets/orbit_Deep_Mine.png`, at
  thumbnail size, looks like a plain roofed shed with no opening at all - which is what an earlier
  pass of this review first wrote down, and it was wrong. A close single shot
  (`--bearing 0 --dist 0.6`) shows a real doorway cut into the front wall. The problem is contrast,
  not geometry: it is a dark opening in an unlit dark-brown wall, with no lintel, frame, or sign to
  catch the eye, so it is invisible at exactly the distance and size everything else in this review
  was judged at. **A door nobody can see is not a door for the purposes of a stranger naming the
  building.**
- **The casino's game machines stand bare.** `High Roller 1`, `Duel 1`, and the rest of that family
  are, in isolation, a marquee board on a post over a small redstone contraption on a platform -
  no booth, no rail, no wall, no sign readable from outside. The section above this one
  ("The casino became a BUILDING") describes exactly this problem being solved once already, with
  rooms, doors and rules signs built around each game - that solution does not appear to carry into
  this newer, park-sited batch of games. Standing alone in `zone_midway_plan.png` they read as
  loose machinery scattered across the plaza floor rather than as fairground games someone would
  walk up to and play.
- **The zone's own headline ride is its weakest silhouette.** `distance_Mine_Coaster.png` shows
  the coaster degrading from "a wooden scaffold with a switchback shape" at full size to an
  indistinct brown lattice at 1/4 - the TRACK itself is not visually differentiated from its own
  support posts, so at any distance it reads as scaffolding rather than as a ride.
  `distance_The_Plummet.png` is worse: at every distance it is a tall dark tower with window slits,
  which is also the exact silhouette of `Clock Tower` and `Prospect Tower` in the same two zones.
  Nothing about it - no visible car, no drop mechanism, no distinguishing mass - says "ride" rather
  than "watchtower". `The Big Wheel` is the one headline attraction that is unmistakable at every
  distance in its own ladder, including 1/4 scale, and it is the standard the other two should be
  measured against.
- **Hollow's palette has almost no reserve for a small building.** `black_wool` is the field colour
  for the whole land, so a small booth that does not get a second, lighter material working for it
  (the way `Iron Railing` and `The Graveyard` both do) goes nearly featureless. `Curio Shop 1` is
  one dark box with a single cyan accent visible from only some bearings - the same booth kind that
  reads perfectly well in `midway`'s white-and-red palette (`Midway Booth 1`, with its striped
  canopy and lit counter) goes flat the moment it is re-skinned in one dark tone with nothing to
  contrast against.
- **A linear structure only has one good axis, and that is fine as long as it is spent
  correctly.** `Trestle Walk` reads as a real braced bridge at bearing 0/180 and collapses to a
  bare post at 90/270 - not a defect, a property of anything meant to be walked along rather than
  around, but worth remembering before adding more of them: this park cannot afford many things
  that only work from one side.

### Three fixes, in the order they would move the most

1. **Give the two headline rides a silhouette a watchtower cannot share.** `Mine Coaster` needs
   its track to read as ONE continuous element distinct from its posts (a solid rail colour, or a
   cart, would do more than any amount of extra scaffolding); `The Plummet` needs a visible car or
   drop mechanism, not just height, or rename it - right now it is a fourth tower in a park that
   already has three.
2. **Put the casino games back in something.** Whatever wrapped `High Roller` et al. into rooms
   with doors and rules signs in the section above this one needs to run again over the current
   batch, or these games need their own booth kind the way every other fairground attraction here
   has one.
3. **Furnish frontier and hollow, not just floor them.** Both zones are three-quarters paved and
   barely a quarter furnished; the paving budget is already spent, so this is a siting/count
   problem rather than a new-generator problem - more of what already exists (frontier's trading
   posts, hollow's curio shops and dead trees) spread across more of the plot each zone already
   claims.

### What this did NOT judge, and why

Colour. `render3d` draws with the same colour DB the palette picker optimises against - this file's
own long-standing circularity note - so every verdict above is about FORM, SILHOUETTE, MASS and
OCCLUSION, which are ground truth whatever the colours are, and none of it is a claim about whether
a material choice looks right in game. And nothing here replaces standing in the world: the "Still
open" item above this section - placing it and looking - is still open.

`out/parksheets/` holds 102 images: one 8-bearing orbit sheet per module (93), a whole-zone view
and plan per zone (6), and a full/half/quarter distance ladder for each zone's headline ride (3).

