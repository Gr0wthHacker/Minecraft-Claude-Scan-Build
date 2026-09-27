## The void ladybird (2026-08-19)

`configs/ladybug.yaml`, `mcbuild/gen/ladybug.py` — a seven-spot ladybird on a leaf, hanging in open
void under the island at **-24207 104 30018**, Y104–121.

**Why this animal passes where eight mammals failed.** The line is not "insects vs mammals", it is
the same PLANAR/COLUMNAR-vs-VOLUMETRIC line as before, with a third case: a ladybird's identity is
a **pattern on a single convex dome**. The dome is a voxel primitive, not a blend of five muscle
groups, and nothing about it has to be measured to a percent — it only has to carry the right
spots. It is the same category as the elephant's trunk and the giraffe's neck. And the canonical
view of a ladybird is the PLAN, which is the view voxels give away free.

**Size comes from the spots, and then from their SPACING.** A spot needs ~3 blocks to read as a
disc, which sets the shell's width floor at ~15. But seven spots also need LENGTH: at 17 long the
elytra behind the pronotum was 12 blocks, four rows of spots sat 3 apart, and 3-block spots at
3-block spacing touch — they merged into one mass and the beetle read as a black beetle with red
veins. **21 long** gives a 16-block elytra, rows 4 apart, and a clear block of red between spots.

**The leaf is the scale reference, not decoration.** A red dome alone in the void is an object of
unknown size; on a leaf it is instantly a beetle. So the blade has to stay visible past it — the
first build put a 17-long beetle on a 26-long leaf, it covered 65% of it, and all that showed was
a green fringe.

**The site was measured, not chosen**, and two things about that generalise:

- **Reserve design CELLS, not bounding boxes.** `Island Belly Full` and `Lowland` each span the
  whole underside while occupying a thin skin of it; box-reserving them says the void is full.
- **Skip the scratch shelf.** Globbing `out/*.litematic` reserves `JAG big` (57,994 cells),
  `X elephant`, `S1.4`, `islet_planned` — parked at the default origin lock and claiming void they
  have no right to. Reserve what `sync.yaml` tracks, plus the lowland scene.
- **Do not take the first box that fits.** It put the leaf 2 blocks under the Shop Islet's raft and
  5 from the void giraffe's neck. A hanging ornament wants the middle of the empty part, so the
  siting used a distance transform (iterative dilation — numpy only, no scipy) over built + designed
  cells. The winner is 15.7 blocks clear of anything, in a free pocket of 35×24×30; the island's
  underside is 34 above and there is nothing at all below. The nearest built block is one of the
  eight old plate vines, 5 away.

### Two traps that produced a clean audit and a wrong build

- **`Canvas.get` returns -1 out of bounds, and -1 is TRUTHY.** Every `if c.get(x, y, z):` in a
  generator therefore reads everything past the edge as solid rock. The ladybird's spots searched
  downward for the top of the shell from two courses above the canvas ceiling, "found" a block
  immediately every time, and painted all seven caps into thin air above the beetle — the shell
  shipped plain red while the audit, the BOM and the component count all said the build was clean.
  **`Canvas.solid()` exists for this**; `bat.py` and `heron.py` carried the same latent bug and are
  converted. `tests/test_ladybug.py` pins both the helper and the truthiness of -1.
- **`round()` is banker's rounding.** The clod's centre landed on x.5, and `round(11.5) ==
  round(12.5) == 12` while `round(13.5) == 14`, so every other column was skipped and the lump came
  out as eighteen separate one-wide towers. Keep centres INTEGER and add offsets to them.

One piece, 2,394 blocks, 0 problems, all cheap tier.

