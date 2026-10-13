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
