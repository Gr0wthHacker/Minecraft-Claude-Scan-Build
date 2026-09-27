# Frontage placement audit — 14 September 2026

## Result

The entrance grammar had survived several replacements of the things it named.
Renaming boards had not moved their openings. The old building spurs at U19,
U70, U448, U496 and U563 led into landscape rather than an avenue or entrance.

The correction uses existing structures and roads. No new attraction, terrain,
ride mechanism or Isthmus structure is introduced.

Coordinates below are **V/U**. World X = 97500 + V; world Z = 80300 + U.
The ground is Y202 and the walking plane is Y203.

`Park Complete.litematic` and the four affected component schematics have been
rebuilt and copied to the configured Minecraft schematics folder. The complete
file retains its origin **97500, 94, 80300**. The result has 440,740 blocks,
1,649 fewer than before; 2,578 cells change. Both Isthmus reaches are identical
to the previous complete schematic.

| Frontage | Previous V/U | Decision / current V/U |
|---|---|---|
| Broken Plateau arch | 20/19 | Move to **24/43**, across the avenue. Remove outer wings. |
| Bone Bed arch | 20/70 | Move to **23/96**, spanning the avenue mouth outside its round plaza. Board directs left to the excavation and ahead to the coaster. |
| Fossil Lab board | 129/62 | Retain: roadside board, not a pass-through entrance. |
| Mine Coaster porch | 25/112 | Retain: the opening is in its offset boarding bay, not the porch centre. Its own queue/exit interfaces remain. |
| Works Yard staff gate | 151/136 | Retain: approach connects to the service lane. |
| Carousel arch | 20/235 | Move to **20/227**, north of the central fence. Single-depth arch. |
| Carousel entrance portal | 21/227 | Remove duplicate: the relocated marquee marks this entrance. |
| Carousel exit portal | 21/243 | Retain. Give it a separate paved spur. |
| Garden arch | 20/362 | Retain: aligned with the garden's paved approach. |
| Snack Window arch | 76/235 | Retain: addresses its short spur and raised counter apron. |
| Sky Lift arch | 128/274 | Convert to a **direction board** at the same verge. An opening here wrongly implies passage through the ride fence. |
| Sky Lift queue | 111/270 | Retain: its exit returns to the promenade; this audit does not certify ride mechanics. |
| Prismworks arch | 20/448 | Move to **24/468**, over the surviving avenue. |
| Prism Well arch | 20/496 | Move to **24/524**, over the other surviving avenue. |
| Descent arch | 20/563 | Remove: obsolete remote entrance into the Downs. |
| Descent queue | 26/585 | Remove: disconnected v1 switchback in the landscape. |
| Well entry portal | 21/486 | Remove: not a current Well entrance. |
| Well exit portal | 21/506 | Remove: points into the rim/terrain, not an exit. |
| Service Gallery staff gate | 151/570 | Retain: crosses the verge to the service lane. |

Prismworks arches have five clear cells, thin piers and six clear courses under
the beam. They fit the three-wide avenues without competing with the Well.
The two land arches face along each avenue, rather than toward former plots.
The obsolete five-block spurs are retired. The Carousel gains separate entry
and exit spurs, and its former centre spur is retired. A lone lamp opposite the
former Foundry spur is removed to keep the verge balanced.

## Evidence and limits

- Sources: `stitch1`, `stitch2`, `stitch3`, captured at 23:11–23:12 local time,
  merged newest-loaded-chunk first into `out/park_stitch_audit.litematic`.
- Coverage: 536 of the 546 chunks intersecting the park envelope. Ten edge
  chunks remain unobserved; air in these areas is not evidence of an empty site.
- Inventory: all 19 frontage arches, boards, portals, porch and queue records
  above were inspected. Landscape relays remain accents rather than entrances.
- The separate Entry Gate already uses the U300 arrival axis. The Wyrm Gate
  is a railway setpiece with bored promenade passages, not a land-entry arch;
  neither is relocated by this frontage correction.
- Four avenue frames have regression checks for a paved three-wide approach,
  three clear courses over the next 16 blocks, orientation, and collision with
  a separately assembled context that excludes the frontage itself.
- 62 focused tests pass. One existing park-roster test fails because the old
  WorldSpec still lists Wyrm's Crossing without a lot or retirement entry.
  This task does not change that programme or the Isthmus.
- No updated frontage module appears in the assembly collision report. The
  report still has five existing landscape/ride overlap pairs elsewhere.
- This is an incremental placement correction using the current assembly;
  it is not a new full-park WorldSpec or live-mechanics certification.
- The 16-cell straight-line diagnostic in `approaches.json` is a review aid,
  not a general navigation test: raised aprons, offset porch bays and turns
  require interpretation. It must not be used to declare every non-air sample
  an inaccessible attraction.

## Visual packet and existing-world cleanup

- `out/arch_audit/before_schematic.png`: numbered original frontage plan.
- `out/arch_audit/capture_annotated.png`: numbered capture comparison.
- `out/arch_audit/avenue_views.png`: four street-level views of the correction.
- `out/arch_audit/before.litematic`: preserved original complete schematic.
- `out/arch_audit/retired_cells.json`: 2,189 old blocks requiring removal or
  replacement across the frontage and related paving/furniture corrections.
  **758 match the exact old block state in the new captures.** Each record
  carries old/new states, world coordinates and observation/match flags.

Updating a schematic does not remove already placed blocks from Minecraft.
The cleanup list is evidence for removal/replacement, not an executed dig job.
Check the recorded old state before removing a block, especially after further
building. No in-game blocks were changed by this audit.
The existing `Park Complete Ready` inventory-specific subset was not regenerated;
use the corrected **Park Complete** rather than that older subset for this layout.

## Walking-area aesthetic additions worth making next

These are recommendations, not additional generated modules.

1. **Midway avenue bunting:** short overhead strings across the U260 and U341
   avenues, set back from the junctions. Vary the drops, repeat the existing
   red/white palette, keep at least five clear courses and put supports beyond
   the paving. Avoid the U300 arrival–fountain–wheel sightline.
2. **Plateau expedition markers:** small fossil silhouettes or survey-number
   inlays beside the U43 and U96 routes, with one paired timber banner at a
   real turn. Use the existing warm stone and timber; avoid another big arch
   between each attraction.
3. **Prismworks directional paving:** restrained cyan chevrons at actual avenue
   turns toward the rim gallery. Keep the skyline for the Well; more isolated
   pylons would repeat the problem of objects without a route relationship.
4. **Occasional seating pockets:** recessed pairs of benches with a low planted
   edge at widened walking areas. Choose places with a view of the lake, garden
   or rim; maintain the full path width and existing lighting rhythm.
5. **One sign at each decision point:** identify real destinations and turns.
   Reserve a pass-through frame for a route that continues through it. Use a
   side-mounted board for information about a view or a nearby attraction.

For any future addition, review its footprint and sightline against the current
roads and captured terrain before detailing it. The useful standard is where
the guest goes after passing it, not just whether its blocks fit.
