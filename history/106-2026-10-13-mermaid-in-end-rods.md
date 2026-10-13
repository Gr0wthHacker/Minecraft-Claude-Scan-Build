# 106 - 2026-10-13 - A mermaid drawn in end rods

`end_rod` is on the skyblock.net allowlist and is a 2x2-pixel post, so it is a LINE: a filled statue
is impossible, a wire cage is exactly right. `gen/mermaid.py` is a lofted wireframe - horizontal
contour rings every `ring_every` courses joined by `ribs` longitudinal lines through one spine of
elliptical stations - plus an outline-and-veins fluke, one-line arms and flowing hair strands.

- Every curve is laid by `_line6` (one axis per step) so the audit's one-component gate holds; the
  first build was 756 rods, 1 component, 0 problems.
- Each rod faces along the axis it has most neighbours on, so a line of rods reads as a line.
- The flat fluke is drawn as outline + veins. Extracting a "shell" from a 1-2 thick sheet fills it.
- First hair spread sideways (x term too large) and read as spider legs from above; it now drapes
  behind the body.
- `configs/mermaid.yaml` carries a PLACEHOLDER `root` ([0,100,0]) because a sidecar needs a world
  position and no site was chosen. Re-site before placing. The animal rubric does not apply.

## Revision: 44 -> 72 blocks
The 44-block build (726 rods) looked like a dense clump in game: head and torso were ~5 wide, so 8 ribs
and a ring every 3 courses left no gaps, and the views tool (nearest-surface) hid it. A wireframe needs
room to open up. Now `height: 72`, `ring_every: 5`, `ribs: 6`, `hair: 9`, `sway: 0.17` (1356 rods, 1
component). Judge wireframes with `tools/look.py`, not `views.py`. Raised hand shortened to sit by the head.

## Revision 2: "hyper detailed" - 120 blocks, 6407 rods
Added: a face drawn on the head's own surface (eyes, lids, brows, nose, lips, cheek lines), tiara,
necklace, scallop-shell top, scalloped scale rows on the tail, dorsal crest, hip fins, double-outline
fluke with ten veins, caged arms with bracelets and five-finger hands, a trident in the raised hand,
~28 hair strands. `_join` bridges any stray detail to the main piece.
- `look.py` renders end rods as full cubes, so it cannot judge a wireframe's face. `/tmp`-style thin-rod
  preview (rod = 1/4 cell wide along its axis) showed what it really is: see-through, so the back half
  of the cage and the hair overlap the face. Fixes: the head is only side contours (no front/back ribs
  or rings), and hair starts at the SIDES of the head (two curtains) with only a few strands at the back.
- The head is ~1.4x the old width and the face is stretched 1.55x vertically; a 12-block head turns every
  facial feature into a 1-rod smear.

## Revision 3: the wireframe is retired - a SOLID block mermaid (gen: mermaid)
Jack's verdict on the 120-block rod wireframe: "crappy". Root cause was structural, not tuning: a
see-through cage shows its own back half through the front, so the face drowned in hair and ribs.
The rod version lives on as `gen/mermaid_rods.py` / `configs/mermaid_rods.yaml`; `gen: mermaid` is now
a filled loft that is then PAINTED:
- body = the same S-spine, elliptical-station loft, filled; tail coat = overlapping-disc fish scales
  (rows offset by half, 3-tone, ramp teal -> violet); thin veined fluke riding the tail's own spine;
- face painted on a FLAT PANEL clipped/filled into the head (an ellipsoid front is stair-steps and
  smears features), found by probing the real skin (`front_z`);
- palette is the CHEAP tier: wool, blue ice, snow, end rod (shaft), ochre froglight. Concrete,
  terracotta, glass and prismarine are all "expensive" here - the first build was 17k expensive blocks;
- a pool underfoot grounds it; lobe tips are stood on it; tiara points anchor to the band cell.
Trap: filling a column down from EVERY fluke cell walled up the notch - only the tips (<=3 above the pool).

## Revision 4: a swimming sea-spirit (gen: mermaid); the standing statue is `mermaid_standing`
Jack: "more mystical than human, and swimming horizontally". `gen: mermaid` is now a horizontal swimmer:
- the body is built UPRIGHT in a scratch frame (loft, scales, veils, fluke, arms) and rotated a quarter
  turn with a transpose (belly toward +z); end-rod facings are remapped (up<->east) or they point wrong;
- the HEAD is built after the rotation, in world axes, upright and turned to the viewer: lying on her
  side puts the face 90 degrees off, and the first build did exactly that;
- mystical, not human: pearl skin with scales climbing the flanks, glowing froglight eyes, brow gem,
  fin-ears, a coral crown, belly line of froglights, long fin veils, a crescent fluke with end-rod
  filaments, hair streaming BEHIND along the body and ending in end-rod wisps;
- a sheet placed per path-point (not per integer course) renders as a comb, not a membrane: raster per y;
- stray pieces (hair wisps) are joined by threads of end rod at the end; one component.
Open: the torso reads as a flat slab from the front and the arms are bars; this direction needs Jack's eye.
