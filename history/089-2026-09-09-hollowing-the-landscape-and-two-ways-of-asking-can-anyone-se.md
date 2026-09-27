## HOLLOWING THE LANDSCAPE - AND TWO WAYS OF ASKING "CAN ANYONE SEE THIS" THAT ARE BOTH WRONG (2026-09-09)

Jack: *"edit park complete so that all terraformed grass, mountains, etc are as hollow as possible
so we reduce total blocks... make sure not to change any outer visible placements/layers."*

`mcbuild/ops/unseen.py`, scoped by `park_place.terrain_mask`, run at the composite beside
`declutter`. **Park Complete 524,033 -> 429,972 (-17.9%)**, every removed cell natural rock, the
shipped artifact pixel-identical from eight bearings, printability exactly at baseline (2,755
unreachable cells in 233 clumps, the same as un-hollowed). Provisioning coverage 56% -> 64%,
`moss_block` short 98,953 -> 70,606, `smooth_basalt` out of the shortfall entirely: it was
25,966 to smelt and 45,000 of its cells were inside a mountain.

**IT SHIPPED BROKEN TWICE BEFORE IT SHIPPED RIGHT, and both failures are the same shape: a check
that grades what it can measure in place of the thing that matters.** Both were found by Jack
walking around in game, and neither was visible to the audit, the BOM, the printable survey, eight
rendered bearings, or twenty-odd tests that were all green.

### FIRST WRONG QUESTION: "can the OUTSIDE see it"

Flood from outside the bounding box through everything you can see through; keep what the flood
touches. It is a beautiful invariant - assert the reachable set is bit-for-bit unchanged - and it
is catastrophically weaker than it sounds, because **a park is full of air the outside cannot
reach**: a station room, a coaster's tunnel bore, a cavity in the rock. None of that is exterior,
so every wall LINING one read as buried - and taking the lining exposed the next course, which the
same mask had already condemned, in the same pass. Measured: **8,523 removed cells had air on a
face**, mostly tunnel and station masonry. Jack: *"buildings roofs are missing too"*, *"a ton of
the rollercoaster is missing"*.

The invariant held HONESTLY throughout - gutting a sealed room does not connect it to the outside.

    AN INVARIANT ABOUT THE OUTSIDE CANNOT SPEAK FOR THE INSIDE, however exactly it is asserted,
    AND A RENDER CANNOT SEE A ROOM.

"Reachable from outside" is a GLOBAL property; visibility is LOCAL. The flood went; the rule became
`erode(opaque)` - a block goes only when its neighbours are all opaque full cubes.

### SECOND WRONG QUESTION: "does this block RENDER" - and 6 is not 26

The local rule was then written with 6-connectivity, on solid reasoning: Minecraft culls a face
whose neighbour is an opaque cube, so a block with all six faces covered draws nothing, ever.

**True, and it is the wrong question, because removing it exposes its NEIGHBOURS' faces to the
cavity - and where two blocks meet along an EDGE there is a slit you can see straight through.**
Jack: *"a lot of the rail way on the side of the prism etc is all hollowed out and empty"*, and
before that *"theres also large gaps in the terrain where its air blocks into empty cavities"*.
Measured on that build: **8,500 removed cells had a see-through cell among their 26 neighbours**,
5,820 of them in Prismworks - which is exactly where he was standing.

**The renderer here could not see it either**, and that is worth keeping: `render3d` marches rays
through voxel CENTRES, so a sub-voxel diagonal slit is invisible to it by construction. Eight
bearings came back pixel-identical on a build with thousands of holes in it. **Our renderer is
ground truth about mass and occlusion at voxel resolution and about nothing finer.**

The rule is `erode(opaque, conn=26)`: all twenty-six neighbours opaque, or the cell stays. That is
not a fudge factor, it is the closure - if every 26-neighbour of every removed cell is opaque, then
no see-through cell touches the cavity at a face, an edge or a corner, so no face of the shell is
newly exposed to anything anyone can stand in. `_check` asserts exactly that, per cell, against the
model as it was.

### "I SAID LANDSCAPE TERRAFORMING ETC ONLY"

The other thing wrong with the first run was scope, and it was mine to read narrowly. Jack asked
for terraformed ground; I read "etc" as everything invisible and hollowed buildings, sculptures and
the wyrm with it. `carve_only` is the fix - a mask of what the pass may TOUCH, everything else
CONTEXT: still deciding what is hidden, never itself removed.

`park_place.terrain_mask` is TWO conditions, because either alone is wrong:

- **`TERRAIN_MODULES`** - the five modules that ARE ground (`PF Mine Ridge`, `PF Prism Downs`,
  `PF Plateau Vale`, `PF Plateau Bone Bed`, `PF Lost Plateau`). The module list alone would still
  offer a terrain pass's own lanterns, timber sets and rails.
- **`TERRAIN_BLOCKS`** - natural rock and soil only. The material list alone would offer a
  building's cobblestone core, and a station is exactly what this may not touch.

Verified per module on the shipped composite: **0 cells removed from Mine Coaster, Mine Works, Wyrm
Gate, Helter Skelter, Sky Lift, Prism Well, the Lookout and Mine Cart Escape**; 0 removed cells
outside the mask; 0 non-ground materials. `Park Buildings` gets NO hollow pass - it is the
buildings, and there is nothing in it the pass is allowed to touch.

### A PRINTER CLICKS A FACE - Jack, mid-turn

*"for printability we still need something on the inside attaching between layers so we cant easily
print without manual diagonal placements etc."* Right, and at the time it was systematic: with the
rule at 6, a one-deep skin took the park's printing islands from **1,582 to 3,409**, because a
hollow slope is a staircase whose treads touch only along an edge.

| | blocks | printing islands |
|---|---|---|
| as shipped | 524,033 | 1,582 |
| one-deep skin at conn 6, nothing else | 356,918 | **3,409** |
| a blanket two-deep skin | 433,461 | 1,587 |
| **conn 26 + `_connect`, landscape only** | 429,972 | **1,584** |

**At 26 the rule mostly carries this by itself** - nothing is taken beside a slit, so a staircase's
corners survive anyway, and no synthetic fixture breaks with `connect` off any more. `_connect`
still fires (130 cells on the shipped park) and is KEPT as the guarantee rather than the mechanism;
the tests assert the PROPERTY (one connected piece) and test the mechanism directly on a join built
by hand, so neither can stop being exercised.

**And it was visiting every join twice.** An unordered pair appears in `EDGE12` as both `B - A` and
`A - B`, so walking all twelve put BOTH corners back where one does the job. `EDGE_PAIRS` is the
six whose leading step is +1, asserted as a partition of the twelve.

### Six guards, each a way a hidden block is still load-bearing

- **A GRAVITY BLOCK NEEDS THE BLOCK UNDER IT** - the Mine Ridge's gravel crust is skin and stays;
  the cell beneath it is hidden. Rule 13 from underneath.
- **A MECHANISM IS MORE THAN ITS OWN CELL** - what a repeater reads, what a torch stands on, the
  block above a piston.
- **...AND `protect.MECHANISM` HOLDS `wool`, WHICH IS 12,500 CELLS OF DINOSAUR.** The never-
  OVERWRITE set read as a general keep-out, which this file already records twice. The first run
  held **23,533** cells for the radius; narrowing the set to MACHINES - `water` alone was keeping
  7,803 cells of lake bed three deep, and it has its own tighter guard - took it to ~4,000.
  **Narrowing a set is not loosening a rule when what replaces it is the more precise one.**
- **A FLUID FLOWS INTO WHAT YOU OPEN**, and `waterlogged` is a STATE, read off the palette entry.
- **ANYTHING NOT A FULL CUBE IS ATTACHED TO SOMETHING.** Both of these are subsumed by the local
  rule and kept anyway: they are what would still hold if `opaque` ever widened.
- **A BLOCK THAT EMITS IS A FIXTURE**, against re-opening a spawnable cell nothing would report.

### And the fixtures are why both bugs got through

Every test was a property and every fixture was a solid cube or a smooth heightmap - so a sealed
cavity could not arise, and neither could a buried air cell with a diagonal slit off it. The two
that would have caught them are four lines each: `test_A_SEALED_ROOM_KEEPS_ITS_WALLS` (a mass with
a room in it and no way in) and `test_A_CELL_VISIBLE_THROUGH_A_DIAGONAL_SLIT_IS_KEPT` (one cell of
air buried in a mass). **A property is only as good as the geometry you hand it.**

The sealed-room assertion had to be narrowed once on the way: a room's EDGE and CORNER cells really
are invisible - every face of an edge cell is covered by a wall cell - so only the six wall planes
are lining.

### What it does NOT decide

**A SEALED CAVITY IS DARK.** 94,080 cells of it, and nothing will ever reach them to light them.
The squid was hollowed on exactly that trade, on Jack's own word that mobs do not spawn here, and
the lowland already carries ~3,700 columns of the same thing recorded as an accepted mob-cap leak.
The volume is REPORTED on every run. `python -m mcbuild unseen <design> --dry-run` runs it on
anything.

