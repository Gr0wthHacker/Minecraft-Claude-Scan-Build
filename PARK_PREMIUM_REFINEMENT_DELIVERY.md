# Premium refinement delivery

## Built and shipped

This restrained first refinement package adds **136 blocks** to the current park:

- Eight small flowering accents in the existing arrival parterres.
- A two-panel orientation board beside the arrival approach.
- Two timber and planting backdrops near the existing garden seating, with four integrated lanterns.
- A specimen display beside the Fossil Lab and a field-kit display beside the coaster, each with one lantern and a short label.

**Park Complete now contains 441,087 blocks.** Every one of the previous 440,951 block states is preserved. Zero removals, replacements, or paving changes. Neither Isthmus reach receives additions. The six new accent lanterns remain below the plan's eight-light cap.

The separate **Park Premium Additions** schematic contains only the 136 new cells and an empty dig list. Both deliveries and their origin/work sidecars were copied to the configured game schematics folder; hashes are recorded in `out/premium_refinement/delivery.json`.

## Placement and review

The generated greybox was checked in context before detail generation. The delivery uses existing bed and verge spaces rather than new public modules. Piece contracts and exact coordinates are in `configs/pf_premium_refinement.yaml`. Access, return, and maintenance use adjacent existing walks.

A proposed Prism display was rejected: air in the printable schematic was inside hollowed terrain in the raw assembly. No Prism display was shipped. Larger arrival planters were also rejected because the existing parterres are already densely occupied. Further gateway trim, tables, and bunting changes from the broader design menu are not part of this package.

The additive layer is applied after the existing assembly's decluttering and terrain finish. It fails on overlaps rather than overwriting the park. Eight raw source flower/carpet cells occupy some selected sites, but those cells were already absent from both the delivered baseline and latest capture; no new removals are required.

## Verification

- All 136 added cells are air in the baseline and latest merged stitch capture.
- Full state comparison preserves every baseline non-air cell.
- World validation: zero artifact conflicts; five approach/viewing destinations reachable from the arrival spine.
- All materials pass the generator's locked 1.19 check and are cheap tier.
- Existing frontage, lamp, and dressing regression checks plus addition tests: **41 passed**.
- `out/premium_refinement/greybox.png` is the footprint review.
- `out/premium_refinement/before_after.png` shows four paired views. Lab/coaster views are raised inspection views; render geometry simplifies Minecraft block shapes.

This is a schematic delivery, not an in-game placement. Day/night appearance still needs a Minecraft walk-through. The existing whole-park printability issues documented by earlier audits are not repaired by this decorative pass.
