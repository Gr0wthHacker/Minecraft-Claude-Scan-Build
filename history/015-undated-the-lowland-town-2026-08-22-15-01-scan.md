## The lowland town (2026-08-22, 15:01 scan)

Jack's direction, verbatim intent: no flamingo, "more buildings or architecture", animals
incorporated around them. The audit that preceded it: ground 90%, ruinway 89%, sanctum 89%,
bridge 92%, axolotl 100%, portal remainder 0% - the quarter nearly done, and the two unbuilt
animals the only large claims left on the floor.

**Both mammal-scene animals are RETIRED in their configs** (flamingo, capybara flee - 0 of
7,618 and 0 of 6,813 cells built, so nothing orphaned). Retiring them freed the NE quadrant
and the central strip, and the pad search over the new scan found what fits. Four designs, all
0 problems in context, 0 overlap, generated after the quarter so `defer_to` holds:

| design | blocks | what it is |
|---|---|---|
| `Lowland Hamlet` | 439 | three houses SW of the ring: whole (roof, chimney, cold hearth), roofless, fallen-to-its-doorframe |
| `Lowland Campanile` | 575 | the sanctum's bell tower at (-24197, 29974), Y41-59; a real `bell` (cheap, 1.19) in the belfry; the owl on the SW merlon |
| `Lowland Harbor Light` | 167 | beacon at the quay ROOT (-24204, 30018) - the lip is a 1-3 wide diagonal ribbon, no tower stands on it |
| `Lowland Turtle` | 145 | basking on the N shore at (-24194, 29993), nose one dry cell short of the measured waterline |

**THE LANTERN GRID IS THE STREET PLAN.** The ground design's 9-grid lanterns land at
X{-24192,-24183,-24174} x Z{30033,30042} in the hamlet pad; the gaps between columns are 8
wide and a 7-wide house fits exactly, so the ground's own lights become the street lamps. The
grid columns are a FORBID set asserted at build time - and the first lane was paved straight
through its own lamp row, which is why `_lane` checks it too.

**The turtle is the ladybird's category** (pattern on one convex dome, canonical view the
plan), sited by per-row waterline measurement: dry to X-24203 at z29993 but only to X-24201
one row south - the first site put the nose in the pond. Shell brown_wool/black_wool seams
(full hue flip off the moss, measured; a green turtle vanishes on a green floor), skin
oak_planks. Flippers are ROOTED at the shell edge and placed at ONE level per pad - at their
own ground they came off as four separate components, and on a ground step a two-course pad
splits diagonally.

Traps this session, each of which shipped a clean audit and a wrong build first:

- **A lamp under a slab cap reads "hanging from air"** in the audit, in context too. The cell
  a lantern hangs from is a FULL block; the slab ring keeps the lightroom's silhouette.
- **The owl floated over the shaft.** The parapet ring covers two of its body's four cells;
  the other two hang over the hollow interior. Anything perched on a built edge needs its
  seat placed under the WHOLE footprint, not probed at one corner.
- **The campanile's tumble perched on the sanctum's wall top at Y49** - `_surface` reads any
  standing masonry as footing, and the neighbour is three cells away. Fallen blocks land
  only where `g <= FY + 1`.
- **Blackstone cannot draw value lines on itself**: the family sits within 12 RGB (measured),
  so the cracked/chiseled trick that failed on stone brick fails here too. The tower's lines
  are GEOMETRY - proud string courses, corbel, crenellation gaps - not tone.
- **Pane connections are game-derived and `work.INTENTIONAL` rightly drops them**; the
  north/south=true on the campanile's slits exists for the RENDER. A test that greps
  work.json for them is testing the wrong artifact.

**The world was adopted as master copy twice**: the ground's 1,416 deviations (Jack's massif
rework - dripstone->cobble x1269 - plus lanterns and the axolotl's footprint) and the bat's
263 (dark oak -> planks/wool substitutions) were merged into the design litematics from the
capture, mechanisms excluded. Both now diff 0 deviations; ground 94%, bat 95%.
`out/island_full.litematic` is the full-depth capture the town generates against.

`tests/test_lowland_town.py` (17) pins the contracts: no cell in a lantern column, every
door frame whole with its lintel BETWEEN jamb tops (jambs three high, or the lintel floats
over the opening), the roofed/roofless split, crenellations actually crenellated, the shear
taking NE and leaving SW, the bell on a real ceiling, the owl seated with its eyes leading,
the pond keeping every cell it owns, one-piece turtle, dry-but-near-water, plan-legible shell.

**Still open:** the quarter's remainder is ~220 cells (portal 114, sanctum 70, ruinway 23,
bridge 3) - one `follow` session; the ground's last 10% is west-side scatter plus 137
water-occupied cells; the ground's two unbuilt trees near the campanile (X-24200/29967,
X-24208/29983) clear its footprint by 2-3 and were left in.

