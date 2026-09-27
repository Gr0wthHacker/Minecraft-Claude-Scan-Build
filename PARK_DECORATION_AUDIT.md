# Park decoration audit — 15 September 2026

## Changes

- Repaired five street-lamp bases/shafts where landscape or planting had
  overwritten six intended fixture cells. Lamp positions and the established
  street rhythm remain intact.
- Cleared 27 landscape cells from the three-course walking clearance above
  paved routes. This includes narrow handoff paths which the Downs had partly
  covered. No ride, railway or Isthmus structure was moved.
- Added seven soil pockets beneath ornamental trunks that stood on flowers,
  stone or coloured paving.
- Restored six missing log segments in three trees. Neighbouring crowns had
  overwritten their lower trunks; these were not merely branches to ignore.
- Added two single-bay bunting strings over the Midway avenues, at V58/U260
  and V40/U341. Each uses two supports on the verges, 12 blocks apart, with
  six clear courses beneath the lowest pennant. They also add four lanterns.
  The central U300 arrival sightline is untouched.
- Cleared one moss-carpet cell beneath a new support.

## Audit results

The independent ground-layer roster contains 133 intended street-lamp stations.
Every mast is checked, including those whose plinth was overwritten and which
the previous detector consequently omitted. After repair, **zero intended mast
cells are overwritten**. The 130 plinths recognised directly in the assembled
scene all have lights; the other stations have differing surrounding base
materials and are covered by the independent roster check.

All **351 detected trees** now have soil or a raised planter beneath their
trunks, with no unsupported trunk gaps. No decorative cells remain in the
audited paved walking clearance or doorways, and no lights are buried in leaves.

43 trunks remain within three blocks of another trunk. These occur in terrain
groves, canopy groups and the menagerie; proximity alone does not justify
removing them. The audit does not equate dense woodland with bad ornamental
spacing. Existing benches, boards, landscape relays and setpieces were retained
where the checks gave no obstruction or support defect. No new filler trees,
animal sculptures or monuments were added.

The new frontage adds 74 blocks. It introduces no hard overlap with another
module; one soft moss-carpet overlap was explicitly cleared. Five unrelated
pre-existing assembly overlap pairs remain elsewhere in the park.

## Reproducibility and validation

`configs/park_dressing_repairs.json` records 47 small source-owner repairs.
`tools/park_dressing_repairs.py` applies these to the loaded module models before
assembly. Every repair checks its exact original block state and bounds. If a
module changes, assembly stops for review rather than silently editing whatever
now occupies the old coordinate. Source artifacts are preserved; the corrected
composite is **Park Complete**.

The frontage generator now supports one bunting bay without inserting a third
post in the road. The new strings are in `configs/pf_front_midway.yaml`.

38 focused tests passed across decoration repairs, frontage geometry and avenue
alignment. Checks include rejecting stale repair coordinates, tree support,
lamp completeness, doorway/path clearance and bunting headroom. The corrected
avenues were also reviewed in `out/dressing_audit/avenue_bunting.png`.

The latest stitch1/2/3 captures remain the real-world comparison. They cover
536/546 park-envelope chunks, so missing edge coverage is not treated as empty
ground. This is an offline placement and decoration audit, not an in-game light
simulation or a live-mechanics certification.

## Deliverables

- Rebuilt `out/Park Complete.litematic`, copied to the Minecraft schematics
  folder using the existing assembly/declutter/printability workflow.
- `out/dressing_audit/before.litematic`: complete schematic before this pass.
- `out/dressing_audit/avenue_bunting.png`: street-level addition review.
- `out/dressing_audit/lamps_before.json`: original damaged-mast inventory.

Updating the schematic does not remove old blocks in Minecraft. No in-game
blocks were changed. Use **Park Complete**, not the older inventory-specific
**Park Complete Ready** subset.
