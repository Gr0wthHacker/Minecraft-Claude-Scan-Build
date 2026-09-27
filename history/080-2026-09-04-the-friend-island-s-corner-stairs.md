## The friend island's corner stairs (2026-09-04)

`configs/friend_stair_{nw,ne,sw,se}.yaml`, `mcbuild/gen/arcstair.py`, `tests/test_arcstair.py`
(29). Jack, in three steps: *"alcoves cut with slabs, want to put spiral staircases on each end
of the slab which then meet at a lower center point combining into a single staircase"*; then
*"instead i want to connect two ends, so that they circle and meet in the center of where the
multiple water streams are"*; and *"the stairs are symmetrical in materials etc, they should be
duplicate and then meet in the middle"*. Materials are the platform's own: spruce slabs, stone
brick.

**The site, measured off `friendisland` (in `out/`, bedrock box origin -22421 -64 -97421):** a
round deck of spruce TOP slabs at Y198 (surface 199.0) over open void, centre cell
(-22400, -97400) where the log spokes cross, a cobblestone house on it, and a 2x2 notch framed
in stone-brick top slabs on either flank of each arm's tip - eight notches, the north-west pair
at u,v offsets [-16..-15, -5..-4] and its mirror, every other corner a sign flip. **Between
neighbouring arms a two-wide waterfall falls along the diagonal from Y198 to bedrock** - 70
columns, its outer row at r 14.8-16.2 from the centre - and every one is refused at every
course, because a tread under falling water catches it and spreads it seven cells over the
stair. The east-north notch is missing its three outer deck cells in this capture.

**Per corner: 451 blocks, 0 problems, 0 overlap, ONE piece with the platform, all cheap, both
flights mirror cell for cell and block for block (`asymmetric_cells: 0`), and it WALKS from the
pad through both notches to the deck under the audit's own rules.** The four notch cells become
bottom slabs a half step down; from each notch an ARC of eight treads follows the rim at
r 17-19.5 - OUTSIDE the curtain - one 3.26-degree sector per half step, a stone-brick block for
a whole-number surface and a spruce slab on a stone-brick stringer for a half one; the two arcs
end flat on the diagonal at 194.5 against a landing of stone-brick slabs on a solid 3x3 pier
standing 21 out along the diagonal, in the curtain's middle; a slab helix winds ten courses down
round the pier to a stone pad, because nothing is below it yet. `/cscan place "Friend Stair NW"`
by NAME - they are not in `sync.yaml`, whose captures are the main island's.

**THE SECOND FLIGHT IS THE FIRST REFLECTED, NOT THE FIRST REBUILT.** It is laid with the same
sectors on mirrored angles, the tread rhythm is fixed by HEIGHT (block, slab, block, slab) and
never by a per-cell hash, and the mirror is then measured over every cell above the landing and
written to the sidecar. A duplicate that is asserted is a duplicate; one that is merely likely
drifts the first time a hash or a world cell differs.

Five things that shipped `problems: 0` and were wrong, each caught by a walk or a component count:

- **THE COURSES JUST UNDER A TOP-SLAB DECK HAVE NO HEADROOM.** The audit wants two clear cells
  over ceil(surface), so the flight leaves the notch OUTWARD, off the rim, and never runs under
  the deck. (The first design, twin helices hung under the arm, spent its top five half-steps
  finding open sky for exactly this reason.)
- **A FLIGHT WITH NO POST IS CONNECTED ONLY IN COURSE-MATE PAIRS.** A bottom slab and the block a
  course down beside it are diagonal neighbours - walkable, and not one piece. The stringer under
  every slab tread is what makes the arc a solid.
- **A PIER'S BOTTOM COURSE HAS A SURFACE TOO, AND IT IS COVERED.** `audit.check_climb` started its
  walk at the lowest surface in the model, tied with the pad, and by x-then-z tie-break began
  inside the masonry on two corners of four - a walkable stair reported unclimbable. It starts on
  the lowest surface a player can STAND on now; nothing that passed before can fail by it.
- **A HELIX BUILT OF BLOCKS AND STRINGERS RENDERS AS A LUMP.** The descent has the pier to hang
  from, so it is slabs only (bottom, then top), which is what a slab helix is for.
- **THE PROBE MUST SCORE THE WALK, NOT THE CELL COUNT.** The descent's start and spin are tried
  sixteen ways; scored by cells placed, the winner's third wedge was empty and the walk died
  under the landing. Scored by the longest walkable chain, it does not.

`render3d` cannot judge the palette; judge form here (`out/friend_orbit.png`) and colour in world.

