# Design quality system

Every generated sidecar can carry a top-level YAML `design` brief. It gives a build an explicit
purpose, visual hierarchy, style profile, palette roles, composition notes, optional visitor
journey, and only the quality thresholds that are meaningful for that design.

```yaml
design:
  purpose: ride
  hierarchy: landmark
  narrative: A visible mine-head coaster station that draws guests from the frontier street.
  style: frontier
  focal_face: south
  palette_roles:
    structure: spruce_log
    shadow: dark_oak_planks
    highlight: lantern
  quality:
    min_blocks: 900
    min_materials: 6
    min_lights: 8
  journey:
    entry: [10, 1, 0]
    destinations: [[10, 1, 8], [4, 1, 12]]
  enforce: true
  visual_review: true
```

Journey coordinates are local to the finished schematic, so the same contract remains valid when
the planner moves it. When `enforce` is enabled, only declared numeric thresholds and journey
reachability can fail generation. Silhouette, palette, material hierarchy, massing, and lighting
remain recorded evidence for human review rather than fake taste scores.

Set `visual_review: true` for a five-image review packet in `out/design_reviews`: four visitor-scale
perspective views and one silhouette view. Parallel lane evidence carries the brief, measured
quality evidence, journey result, and these review paths forward to the acceptance gate.

The shared grammar module provides deterministic building blocks for new generators:

- `facade_profile`: readable flat, stepped, gabled, or bracketed fronts;
- `path_route`: gap-free 4-connected route geometry;
- `terraced_slope`: stable terrain steps;
- `sculpture_masses`: silhouette-first body-mass bands.

Style profiles currently cover `frontier`, `hollow`, `midway`, and `natural`. They establish
massing and palette intent; individual generators remain responsible for Minecraft-valid blocks,
support, mechanics, and their own richer contracts.
