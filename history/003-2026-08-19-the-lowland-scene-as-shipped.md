## The lowland scene, as shipped (2026-08-19)

Four designs, all one piece, none sharing a cell with another. `/cscan place` each by name — do NOT
use the bare form, it places all 54 designs including a shelf of scratch animals.

| design | blocks | what it is |
|---|---|---|
| `Lowland` | 35,197 | the ground itself, Y24–47 |
| `Lowland Heron` | 8,168 | grey heron, standing, Y41–124 |
| `Lowland Flamingo` | 7,625 | pink, one leg tucked, kinked bill, body tilted, Y41–133 |
| `Lowland Capybara Flee` | 6,725 | running, Y38–59 |
| `Lowland Bat` | 2,409 | roosting on its OWN floating rock, a stone tower on its crown, Y112–153 |

The mammal predators were **retired**, not moved: the jaguar and the bear are the two shapes this
system cannot build, they took the floor the birds needed, and keeping them would have been keeping
a spotted table because it was already made.

Three siting facts that cost time and are worth keeping:

- **Headroom is not 46 blocks, it is a median of 151.** The earlier figure was measured only under
  the void isle's footprint, which is 1,504 of the lowland's 5,851 columns. A 90-block bird fits
  almost anywhere; it just must not be under the isle.
- **The birds stand at Y42, not Y40.** The ground rolls 4–5 blocks under a splayed foot, so standing
  on the MEDIAN height buries the toes on the high side. Stand clear of the maximum.
- **The bat carries its own ceiling.** It no longer hangs over the lowland at all: `perch` builds a
  ragged lump of the island's own stone above the claws, mossed on top with vines off the rim, so
  the design is self-contained and can hang in open air. That freed it from competing with the
  birds for airspace — it now roosts in the gap between the bee farm (X −24213..−24186 /
  Z 29995..30048) and the mushroom lobe (X −24158 / Z 30040), at Y112–138 with the grip at Y130.
  **Fifty-two** blocks under the plate, in a column that is genuinely open sky: 0 of the
  ruin's 121 columns have island overhead, and only 16 of the rock's 195 do. The config
  said "twenty blocks under the plate, the plate's lowest block is Y150" — Y150 was the
  CAPTURE'S FLOOR, not the island's underside, which over this gap is Y200. Read a
  clearance off the capture's content, never off its bounding box.
- **Wingspan is a function of how far away it hangs.** At 106 wide it was absurd; that was a
  consequence of hanging it 109 blocks up, where anything smaller could not read. Roosting close
  and furled (`spread: 0.5`) it is 46 wide and still shows its finger struts.
- **The rock carries a TOWER, and its shape was decided by the viewing angle.** The perch reads as
  a piece that broke off the plate, so it carries a piece of what was BUILT on the plate. It sits in
  open sky 52 blocks below the rim, seen from steeply above as much as in profile, so it had to work
  in PLAN — which ruled out an arch (negative space you cannot look through does nothing from
  overhead) and a bare snag (a few scattered pixels). From above it is a ring of dark merlons round
  a lit deck.

  The first attempt was a sheared stub with a jagged top and it was rejected on sight as *"a tossed
  grouping of vague blocks"* — correctly. **What makes voxels read as ARCHITECTURE is regularity and
  openings, not damage.** It now stands full height and regular: a flared plinth, a door with a
  lintel, three glazed slits with sills, a string course, a corbelled overhang, a parapet and
  crenellations — and the ruin is ONE broken arc with its merlons on the moss below. A building that
  has taken damage, rather than damage that vaguely suggests a building. Five things it cost:

  - **The shear must be a PLANE, not a cosine** — a cosine falls away smoothly in every direction
    from the high point, which is a cone, and it built a witch's hat. (Kept for the broken arc.)
  - **`cracked` and `chiseled` stone brick are within 4 RGB of plain**, so weathering a wall with
    them is invisible: it gave the tower no tone and no horizontal at all. Every band that reads is
    `deepslate_bricks` — 51 darker, and the island's own stone dressed. Plinth, string course,
    corbel and merlons all take it, which is also what makes them look like one building.
  - **The weathering hash must be on the CELL.** Hashed on the course, every block in a course came
    out identical and the wall was horizontal stripes of one material.
  - **The crenellation course must be left EMPTY by the wall loop.** Building a full ring there
    first and then alternating merlons over it repaints cells that already exist — it alternated
    perfectly and changed nothing, and the crown was a plain drum. `test_the_crenellations_are_
    actually_crenellated` pins it, because nothing about the code looked wrong.
  - **From directly above, a merlon in the parapet's own block is invisible** — a plan view sees
    only the topmost cell, and a merlon and the course under it were the same colour. Dark merlons
    are the only reason the crown reads from the angle that matters.

  A `glass_pane` needs its connection state set ALONG the wall; with every side false it renders as
  a lone post rather than as glazing. Plain panes are `ok` tier — every stained pane and plain
  `glass` are `expensive` on this economy, which is odd given a pane is made from glass.

- **A flamingo does not stand level.** Its body slopes down to the breast with the tail carried high
  and the neck leaving from a low point at the front. The body used to be one upright ellipsoid,
  which cannot lean however the rest of the bird is posed — it is swept along a tilted spine now,
  and `body_tilt` is 3.0 for a flamingo against 1.2 for a heron. Level, it read as a pink heron.

### Cost: the whole scene is cheap tier

It was not. The first palettes came to **6,893 expensive blocks** — the heron alone was 45% concrete
and terracotta — for tones that wool and plain stone give away. `light_gray_concrete` → `stone` is 11
in RGB; `gray_concrete` → `gray_wool` is 15; a flamingo is the one animal whose colour needs no clay
at all, because sheep come in pink, red and magenta. **Now 0 expensive across all four**, and the
bat's 210 `ok` are the deepslate in its perch.

Two traps worth remembering, both hit while fixing this:

- **`_eye_ring` was picking out of the whole registry.** It chose `quartz_block` (expensive here),
  and once filtered to cheap it chose `stripped_pale_oak_log` — a **1.21 block**, because
  `blocks.available()` is a no-op while the allowlist is provisional and cannot say no. A decorative
  ring of four cells does not need the registry; it now picks from a short known-safe list.
- **Three tones of the same colour beat two tones and a third hue.** `magenta_wool` banded between
  red and pink read as a bruise. Red coverts over pink with BLACK primaries is both cheaper and
  correct — black flight feathers are the flamingo detail.

