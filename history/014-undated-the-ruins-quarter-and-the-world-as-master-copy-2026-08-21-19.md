## The ruins quarter, and the world as master copy (2026-08-21, 19:28 scan)

The scan review found the ring 89% standing, the ground ~95%, the pond broken to real water -
and **the axolotl standing on the pond's WEST bank, rotated 180**, where the design said
north-east. Jack placed it where he wanted it, which is a design decision made in-world, and the
response that works is the one taken for the deck floor's as-found state: **the world is the
master copy.** The placement transform was recovered off the two eye beads (rotation 2x90,
translation solved by matching), and `Lowland Axolotl` was re-derived from the capture itself -
975 cells, as built, 100% clean by construction. The config keeps the design record under an
AS-BUILT header; regenerating it would fight the placed copy cell by cell, forever.

**The same scan moved the ground under the ring, and the seat drifted.** The ring's vertical
seat derives from min-ground; Jack's moss-building raised that by one, and a regen emitted every
remaining cell one course off the standing masonry. `base_y` now pins the seat - and the pin was
taken WRONG once before it was taken right: 44 from the drifted derivation, then 43 read off the
standing crown (proud keystone at Y68 = seat + D/2 + 13). **A pin must come from the world, not
from the code that drifted.** The ruinring tests hit the snapshot trap too - pinning the full
circle against a design whose nature is remaining-work - and now judge what STANDS (design plus
capture masonry) for geometry, the design alone for the seam rule.

**`Lowland Ruinway`** (gen/ruinway.py, 224 blocks, 0 problems, 0 overlap, 0 expensive): the rest
of the ruin complex, one hand with the ring. Ruined pavement from the pond's SE bank THROUGH the
gate to a broken overlook at the rim's true edge (ground ends at X-24151, measured after this
file's own -1-is-truthy bug bit the rim scan a second time). Fragments, each a PART of a
building: a gatehouse whose door outlived its walls, a four-pier colonnade on the overlook
approach, a bridge stub whose last two rows hang over open water, an apse half-ring with one
amethyst bloom in the NORTH skylight - the second beam of daylight gets its own ruin so the two
shafts answer each other. Soul lanterns on wall posts light the way cold.

Three measured facts the quarter is built on:

- **The way crosses UNDER the sprinting capybara.** Its only low cells are the two diagonal leg
  pairs (z30014-18 and z30022-26); the corridor between them at z30019-21 is clear below Y47 the
  whole way across, and `test_the_walk_under_the_capybara_stays_clear` keeps it that way.
- **The pavement decays with distance from the ring** (gap hash grows per block), stairs are
  never gapped (a missing tread breaks the walk; a missing flag is moss showing through), and
  every riser faces its ascent per the stair convention.
- **The pond's SE finger was misread once**: "water reaches east to X" is water's EASTMOST
  column, not its extent - the first bridge siting put the whole deck on dry land and the test
  caught it. The deck is level (a bridge does not conform to ground - that is the reason to
  build one), and its broken end is staggered, not sheared.

Generation order matters and is stated: portal first, ruinway defers to it (21 shared threshold
cells). `designs.json` tracks 26.

**The visual audit of the quarter (2026-08-21), and the scale rule it produced.** Rendered from
every angle a player gets - west-bank money view, landing approach, close-ups of all five
fragments, whole-scene elevations. What passed unchanged: the plan composition, the path craft,
the overlook (a parapet is SUPPOSED to be low - its drama is the void), the bridge stub. What
failed: the gatehouse read as a dark blob beside the path, and the apse was shin-height in
elevation - a mound with a purple dot. Three findings worth keeping:

- **On this moss, under ten-tall trees, architecture below ~6 courses dissolves into ground
  noise.** The fern-and-azalea surface roll eats anything shorter; the bat tower (15), the ring
  (25) and the trees set the register. Fragments were raised to clear it: gate frame to 8, apse
  crest to 6, tall colonnade piers to 6.
- **The ruin is the WALL, never the DOORWAY.** The first gatehouse broke its lintel - damage,
  not architecture. Inverted: a COMPLETE post-and-lintel frame stands alone in the moss, and
  the decay is carried by wall stubs falling to nothing off both sides. The doorway whole, the
  building gone - that is the void tower's rule said forward.
- **A linear height profile peaks on a single column.** The apse's crest read as a stick because
  full height existed only at angle zero; the profile now holds full height across the whole
  back third before decaying. A wall crest is a LINE, not a point.

**And then Jack rejected the quarter's shape itself: "very sparse and vague... too fragmented,
we need at least one more complete actual structure - something that feels real and like it was
once impressive."** He was right - fragments without a mass read as set-dressing. The answer is
**`Lowland Sanctum`** (gen/sanctum.py, 788 blocks, 0 problems, 0 overlap): a basilica-form
ruin in the north skylight - the ONLY zone that can hold a real footprint (a 14x22 pad search
over the whole lowland returned ZERO with everything reserved), and only after the ruinway's
apse fragment yielded its ground, which is the coherent trade: the fragment became the
surviving back wall of the building it was always a fragment of (`apse: null` in the ruinway
config records it).

- **The footprint threads the blocker map**: walls at X-24191/-24181, BETWEEN the ground
  design's lantern columns (X-24192, X-24184) - the ground's own lights are dodged, never
  covered, and the two inside the nave stay standing in the ruin floor. The apse backs onto
  the void breach north of z29964; the roofless nave sits inside the daylight beam.
- **Once-impressive is a CONTRACT, and it is pinned** (`test_sanctum.py`): the facade survives
  whole - open doorway, chiseled jambs, an oculus ringed in chiseled over the lintel, stepped
  pediment to FY+11 - the apse holds a full crest LINE, the SIDE WALLS are the part that fell
  (high at both ends, a course or two mid-run, their tumble in one heap per side), the
  stylobate is one level plane, and a pavement spur joins the way at the gatehouse. Through
  the open door you see the amethyst bloom on the altar - unplanned, and kept.
- **`floor_y` is pinned in the config** for the ring's reason: a seat re-derived from a ground
  that is itself being built drifts a course between placement and regen.

Build order for the printer is now: portal remainder, ruinway, sanctum (each defers to the
ones before it). `designs.json` tracks 27.

**The pond end was wrong and Jack named it exactly (2026-08-21): "the gate and fishing path...
needs to be done differently."** The first ensemble was a door to nowhere and a jetty from
nowhere - the bridge stub genuinely read as a fishing jetty. The fix was to commit to what the
pond IS in this story: **the harbor**. The bridge is gone (`bridge: null` records why); the
pond's SE shore turned out to be a clean diagonal of dry edge columns at exact water level
(measured, not drawn), and the QUAY's dressed lip follows that line - the bank is the water's
own line, never a hand-drawn box. Mooring posts stand on the lip, one carrying the cold light;
two lip cells are landing steps whose flight ascends LANDWARD, because you climb them out of a
boat - the stair convention applied to a shoreline. The gatehouse relocated to mid-arc as the
WATERGATE, its opening facing the landing, and the way now BEGINS at the water: boat - steps -
gate - under the capybara - ring - colonnade - overlook. A path is real when both of its ends
are places.

