## The Lowland Thicket: the cave was quarried but never planted (2026-08-23)

The audit that produced it was a sweep of every area for what to add next. Two of the answers
were negative and are worth keeping, because they say where NOT to spend effort:

- **The plate has no dead ground.** Every walkable cell on it is within **4 blocks** of
  something built or planted, median 0. "Focal-point saturation" is now measured, not asserted:
  nothing new belongs up there.
- **The descent is the emptiest band on the island** - Y51-99 at 1.47% density, and in the
  slice Y70-79 there are 163 blocks within 30 of the helix axis of which **zero** are anything
  but the staircase itself. The Falls now crosses it at r=20, which is most of the fix; the
  band is still the one place a new hanging piece would be seen.

And the positive one, which is the largest single gap on the island. The lowland is called
"Minecraft's lush-caves palette - moss, azalea, fern, dripstone" throughout this file. Measured
against the 15:54 scan it holds 38 block types and its entire flora is

    moss_block 3986 · dripstone_block 4141 · vine 1098 · moss_carpet 56

with ZERO azalea, fern, grass, dripleaf, spore blossom, cave vine, lily pad - and, despite
4,141 dripstone BLOCKS, not one pointed dripstone. **A cave of rock and moss is not a lush
cave.** It was never removed either: the `Lowland` ground design's own cell list contains
moss_block and vine and no other plant, so this is unbuilt work. The 32,369 vines Jack purged
were vines, and only vines.

`configs/lowland_thicket.yaml`, `gen/thicket.py` - **1,424 plants, 0 problems, all cheap.**
11,478 ceiling cells, 6,803 floor cells and 617 shallow water columns were available, so the
design problem was restraint, not room.

**PLANT IN DRIFTS, NEVER IN CONFETTI**, and the first build failed exactly this test: 191 blobs
of which **75% were one or two cells**, because the drift falloff was thresholded per cell.
That is the deck floor's scatter reproduced in green. **The noise belongs on the drift's
RADIUS, not on its interior** - the middle then fills solid and only the boundary wobbles.
After the fix, 76% of planted cells live in blobs of 8 or more and the largest patches are
30-36 cells. `test_thicket.py` pins the ratio.

What each species is for: **cave vines** carry glow berries, so the hanging gardens light
themselves (207 cells at light 14) - kept clustered and moderate on purpose, because Jack has
just removed 32,369 vines and this must not read as the vines coming back. **Spore blossoms**
are rare, large and they DRIP: one of the few sources of motion this island can have.
**Dripstone** is what 4,141 dripstone blocks were promising, built as real tapers
(base-middle-frustum-tip) rather than single spikes. **Azalea and fern** drift on the moss with
a moss-carpet fringe so a patch fades instead of ending on a hard edge.

Four traps, each of which shipped a clean-looking build first:

- **A plant roots in the DIRT FAMILY and nowhere else.** Listing mossy cobble and mossy stone
  brick as soil because they look like ground returned **173 placement problems** - fern on
  mossy_cobblestone, azalea on mossy_stone_bricks. Rule 11 again. Moss carpet is the exception:
  a carpet sits on anything, which is what lets a drift fade off its soil onto the rock.
- **PASSABLE IS NOT EMPTY.** `air()` answers "can a body or light pass through this" and says
  yes to vine and grass. Used as the test for *may I build here* it grew a stalagmite up
  through two of Jack's vines: the design claimed cells the world still fills, the composite
  kept the vine, and the audit correctly reported a spike floating above it. This is the mirror
  of the rim stair's "vine is not footing".
- **`is_protected` holds "water"**, rightly - a generator must never overwrite a fluid - and
  applied to the survey it banned every water cell, so the whole harbor margin came out empty
  in silence: 0 lily pads, 0 seagrass, 0 dripleaf. A waterlogged plant does not remove water;
  the BED is what must be checked.
- **A lily pad floats on water**, so nothing may take the cell under it. Where the pond is one
  deep the bed IS the surface, and seagrass planted there left eight lilies sitting on seagrass.

And the artifact trap, hit **twice more** in one session: `work.json` carries only
`work.INTENTIONAL` properties, so grepping it for `berries` or `thickness` tests the wrong
file - both live in the litematic's palette. `m.names` drops properties too, which is why the
palette looks like it holds duplicates. Read the palette NBT.

**Build order is now Falls, then Thicket, then Island Night**, and the night pass was re-solved
against a world containing both: pointed dripstone is the one plant here that is not passable,
so a stalagmite moves the surface classifier down a course and can open a spawn spot under
itself. 107 fixtures now, still zero spawnable surface cells.

### Still open, and measured - the island is built but unfurnished

The pattern the audit kept finding: the last one or two percent of several designs is exactly
the props that make a place feel inhabited, and all of it was accepted as complete.

| | | |
|---|---|---|
| Atelier Court | 14 | a workshop with **no tools** - 9 workstations unbuilt |
| Lowland Campanile | 42 | a bell tower with **no bell** (the island has zero bells) |
| Undercroft Store | 77 | a storeroom with **no barrels** (39) |
| Lowland Portal | 114 | the lowland's ICON, never started, amethyst and all |
| Chimneys | 10 | campfire + soul campfire: the only smoke the island can have |
| Statue Footings · Apiary Flowers | 61 | the planting round the statues and for the bees |

That is **~318 blocks that turn built into inhabited**, and none of it is new design work -
only a decision to re-track designs that were accepted as finished.

