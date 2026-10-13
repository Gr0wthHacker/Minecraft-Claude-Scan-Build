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
