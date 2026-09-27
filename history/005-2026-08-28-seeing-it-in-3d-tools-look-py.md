## Seeing it in 3D: `tools/look.py` (2026-08-28)

```bash
python tools/look.py "X elephant"                     # eight bearings round it, on one sheet
python tools/look.py "Lowland Frog" --sheet panel     # head-on, profile, plan, silhouette, value, distance
python tools/look.py "Lowland Frog" --bearing 0 --dist 0.5 --look-high 0.85 --big    # its face, close
```

`mcbuild/render3d.py` is a voxel raycaster in numpy - perspective camera, Minecraft's own face
ladder, corner AO by the game's rule, and a directional sun with hard cast shadows. No new
dependency: numpy and Pillow, like everything else here.

**IT EXISTS BECAUSE AN ORTHOGRAPHIC VIEW CANNOT SHOW THE THINGS THAT KEEP GOING WRONG.** This file
already records the clearest case and did not draw the conclusion: the axolotl's head read as a blob
in game and correct on every sheet, and the reason is stated here verbatim - *"an orthographic render
along the body axis cannot show this failure - projecting along the diagonal de-jags it by
construction."* Two more of the same shape: *"there is no weight anywhere: the outline is a
constant-depth rectangle"* is a question about OCCLUSION, and depth-shading darkens a recess whether
or not anything occludes it; and *"does it look BUILT"* is a question about how light breaks over
steps, which a flat fill shaded by distance has none of.

**THE BEARING IS RELATIVE TO THE RECORDED FACING**, read off the sidecar exactly as `panel.py`
chooses its profile axis - 0 is head-on, 90 profile, 180 tail-on. Picked by hand this was got wrong
twice in one session, and a design with no recorded facing SAYS SO rather than defaulting quietly.
`tests/test_render3d.py` asserts it: bearing 0 puts the camera nearer the head, 180 nearer the tail,
and the two profiles are mirror images to 99.6%.

**What it costs.** 0.3-0.8s for an animal, **1.4s for the whole island** (110,551 blocks in a
103x335x103 grid), because the march compacts its active set - a ray that has hit or left the box is
dropped, so the arrays shrink every step instead of every ray paying for the longest one. Context
views are therefore affordable, not just the animal alone.

**Calibration, which is the only reason to trust it.** The elephant is *"the control the panel is
calibrated against"* and it reads instantly here - trunk, ear, dome, columnar legs. The jaguar is the
recorded failure and renders as exactly its recorded verdict: a constant-depth slab from shoulder to
rump on four posts at the corners. A renderer that flattered the jaguar would be worthless.

**It found something on the frog the panel had understated.** The recorded verdict was *"MARGINAL in
profile - a low mass with a raised head"*. In 3D the profile is worse and the cause is localised: the
haunch is a **flat-sided box** with a hard vertical rear face, and the value panel shows it as one
untouched mid-grey rectangle. That is the jaguar's own failure - a flat wall painted two colours - in
a build that passes head-on. **FIXED the same day** - see the frog's own section: the cure
was a course-by-course step, not a chamfer.

**The trap inside it, which shipped a clean-looking render.** A ray whose FIRST voxel is solid never
takes a step, so it reported whatever axis the march was initialised with, and every surface touching
the grid's own bounding box shaded as an east/west face. A cropped model touches that box by
definition, so this was wrong for the outermost shell of every design - and it looked fine, because a
wrongly-shaded face is still a face. The entry axis now comes from the slab test. Two of the tests
that caught it were mine and wrong first: a bar viewed down its own axis has no taper to measure
(it occludes itself), and two cubes on the same sightline are one cube.

**What it deliberately does NOT fix.** Colour. Every block is still a flat RGB from the same DB
`nearest()` optimises against, so the circularity this file records is narrowed, not closed: what is
new is GEOMETRY and OCCLUSION. Judge form, mass and silhouette here; judge palette in game. Real jar
textures and real block models (stairs, slabs, trapdoors - 2,657 models and 1,269 textures are
sitting in the client jar) would close the rest and are the obvious next step, but they buy almost
nothing for ANIMALS, which are near-100% full cubes - `shell.py` gets no purchase on six of the
eight. They are worth building the day the question is about the enrichment pass, whose *"payoff is
geometric relief, and that does not show in our renders"*.

**AMENDED 2026-08-29: half of this is now done, and the reasoning above was wrong in a way worth
keeping.** "Animals are near-100% full cubes" was true only while no animal used a shape block. The
frog's toes are stairs - which is what makes a toe TAPER instead of ending at a vertical face - and
the day they went in, every sheet here drew them as cubes. `render3d.subdivide` gives stairs and
slabs their real shape by expanding each block to 2x2x2 half-cells; textures and the rest of the
model zoo are still not done. The lesson generalises: *a renderer that cannot draw a feature is an
argument for not using the feature*, and that is backwards.

