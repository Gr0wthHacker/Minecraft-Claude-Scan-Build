## THE DRESSING AUDIT: a third of the park's planting was eating itself (2026-09-13)

Jack: *"audit all placements of things like trees and lamp posts, make sure its artistic, it makes
sense, doesnt obstruct pathways or buildings, etc, we need this to feel really sophisticated and
amazing."*

**EVERY CHECK THIS PARK HAS IS ABOUT A BLOCK, AND EVERY FAULT BELOW IS ABOUT A PIECE.** A tree
floating one course over a flower is legal, supported, affordable, 1.19 and non-colliding; the
audit passes, the bill of materials is right, `render3d` draws it exactly as it draws a planted
one, and `provision` can buy it. Nothing anywhere could see it. The only symptom is a park full of
half-eaten planting - which is what "doesn't feel sophisticated" turns out to mean once measured.

    python tools/park_dressing.py            ROOTED . STANDING . SPACED . CLEAR . OPEN . LIT

    trees floating on a tuft, a rock or a hedge   139 of 481  ->  10 of 351
    trees with NOTHING AT ALL under the trunk       8          ->   0
    ornamental trunks within 2 of another          74 of 193   ->   0
    cells a pass wrote over its own earlier work   4,522 (31%) ->   0 structural, 2,454 turned away

### `Canvas.put` OVERWRITES, AND A PASS THAT DRAWS DRIFTS NEVER ASKED WHAT IT HAD ALREADY DRAWN

One cause, two generators, and it is this file's own recorded rule arriving for the third time -
*"A PIECE NEVER OVERWRITES A PIECE... two footprints that touch corrupt each other silently."*

`parkgreen` draws meadows, beds, shrubs, hedges, trees and boulders one after another over a shared
canvas. `frontier_scatter._Ground.free` cannot help, and it is worth being precise about why: **it
asks the WORLD, which is the capture, and the capture does not contain what this pass laid ten
iterations ago.** A DESIGN'S OWN CANVAS IS NOT THE WORLD. So a meadow drifting past a tree replaced
the tree's own bottom log with a tuft of grass and the tree shipped one course in the air with a
flower jammed under it; a boulder went through a crown; a trunk went through another tree's canopy.

Isolated by building one kind at a time, which is the measurement that settles it:

    trees alone       1,089 trees, 1,088 with their base   <- correct
    tree + meadow       482 trees,   266 with their base
    tree + bed          478 trees,   226 with their base
    tree + rock         501 trees,   393 with their base

**AND THE DENSITY RETUNE EARLIER THE SAME DAY TURNED A LATENT FAULT INTO A VISIBLE ONE.** At the
pre-retune settings it was 1 tree in 15; at the shipped settings, 69 in 159. More drifts is more
overwrites - and nothing reported the collision, because a collision INSIDE one design is invisible
to `park_place.clashes`, which compares MODULES.

`parkgreen._Soft` is the fix: one proxy through which every piece writes, refusing a cell that
already holds something. Three things about it are load-bearing:

- **MOSS CARPET, TUFTS AND FLOWERS MAY STILL BE DRAWN OVER, and that is the design's own
  declaration rather than a loophole** - `verify_replaceable: [moss_carpet]` in both configs. A
  carpet, a tuft, a fern and a flower are one class: the lowest layer, one cell deep on the plane.
  A tree rooting through a tuft is a tree standing in a meadow. Everything with STRUCTURE stands.
- **THE SOFT SET IS DERIVED FROM THE PALETTES, NEVER TYPED.** A land that swapped its grass for
  another tuft would otherwise have that tuft silently promoted to something a tree cannot root
  through - the same fault wearing the next costume.
- **A REFUSED BASE IS STILL A FLOATING TREE.** With `put` honest, a tree whose base cell already
  held a hedge or a boulder simply lost its bottom log exactly as before - sixteen of them. So
  `rootable` tests the SITE before a cell is laid: no tree is better than a floating one, and this
  park's ground is not short of candidates.

### A STAND OF TREES, NOT A THICKET OF POLES

Nothing ever asked where the last tree went. A crown is radius 2, so trunks three or four apart
touch canopies - a copse, and wanted - while the shipped park had a **median gap of THREE with 74
of 193 trunks within two of another**, and clusters of four trunks inside a 5x3 patch under one
blob of leaves. `tree_clear` is 3, and the gate is on the PIECE rather than on the scan, because
the scan cannot know which kind a candidate will become until after it has passed every other
test. Swept, with the cost stated in the config: 0 -> 13,104 cells and a thicket, 3 -> 12,181,
5 -> an orchard and 30% less of the mass the park is short of.

### AND `PF Lost Plateau` HAD BEEN DELETING ITSELF ON EVERY REBUILD

The same fault in the canopy over the mountain, plus a worse one underneath it.

- **`_vines` RUNS AFTER `_trees`**, so where a face fell away beside a planted column the curtain
  was written straight down through the moss cap and the bottom two logs standing on it - **eight
  trees hanging three to five courses over the rock with a rope of green in the gap.** A curtain
  hangs into AIR by definition, so refusing an occupied cell costs it nothing it was entitled to -
  but a curtain meeting ANOTHER CURTAIN is not a collision, and broken on that too the pass lost
  1,112 vines of 4,103, a quarter of the greenery on the ridge.
- **RULE 15 WAS ANSWERED IN THE DOCSTRING AND NOT IN THE CODE.** The module's own notes say *"RULE
  15 IS ANSWERED BY `previous:`"*; `_Relief` took `mine` from the shipped artifact, stored it, and
  **read it nowhere**. So the surface it probed was the world WITH this pass standing on it, every
  column it had capped last time read as `moss_block` rather than as ROCK, `dressable` refused it -
  and regenerating a shipped design collapsed it from **15,374 cells to 3,440**: the canopy quietly
  deleting itself on any rebuild, with nothing anywhere to say so. **A FIELD THAT IS STORED AND
  NEVER READ IS A RULE NOBODY IS KEEPING**, and a docstring is not a guard.
- **`(a, b) in caps` SAYS THE CAP WAS LAID, NOT THAT IT IS STILL THERE.** A crown drawn earlier in
  the same sweep overwrites the cap it spreads across, and the next trunk stands on leaves.
  `loft.surface_out`'s rule: read the surface the build actually left.

### What was measured and found CLEAN, which is worth as much as a fault

- **THE PATHS ARE CLEAR.** 16 dressing cells stand in a street across the whole park, every one of
  them `PF Prism Downs` terrain the street runs through rather than furniture. `path_clear: 2`
  works, and `mast_ok`'s rule - *a lamp stands on lawn, never on a path* - holds.
- **NO DOORWAY IS BLOCKED**, by anything, anywhere.
- **EVERY ONE OF THE 127 STREET LAMPS CARRIES A LIGHT** and none is buried in a canopy.

### Two false findings the tool had to be taught, because each named a correct build

- **A LAMP'S OWN PLINTH IS PAVING-COLOURED AND IS NOT A STREET.** Taken as "any non-moss cell the
  ground layer owns at the paving course", every lamp on open lawn reads as a one-cell street with
  its own post in the middle of it: **810 false findings**, and the three worst in the list were
  one lamp seen three ways. A street cell has street either side of it.
- **A LOG COLUMN IS NOT A TREE, AND A TUB IS NOT A FAULT.** Without a crown test this counts 1,291
  trestle posts, pergola uprights and corner posts against 481 real trees; with a crown test that
  reaches two cells it still counts the Mine Coaster's trestle, because the Lost Plateau's canopy
  hangs over it. A crown SITS ON its trunk and belongs to the design that placed it. And the
  Welcome Court's four planters are masonry under a tree ON PURPOSE - the discriminator is the rim.
  A tool that cries wolf on a correct build is a tool nobody runs.

**Still open, stated rather than left:**

- **`PF Lost Plateau` STILL ERODES ~13% PER SHIP CYCLE** (13,153 shipped, 11,469 on the next
  build), down from 78%. The residue is structural and general: `mine` comes from the SHIPPED
  artifact, the pipeline trims cells between the canvas and the artifact, and every trimmed cell is
  then indistinguishable from world rock on the next run. Any design with `previous:` and a
  trimming `finish` has this. It is its own job.
- **Ten trees in six designs are still not rooted in soil** - singles in `PF Water Claim Lake`,
  `PF Water Wyrm Garden`, `PF Prism Downs`, `PF Frontier Scatter`, `Welcome Court` and the
  plateau's own canopy. Each is one tree in one generator rather than a class.
- **43 trunks stand within 2 of a neighbour and every one is a WOODLAND pass** - the Broken
  Plateau, the Lost Plateau, Frontier Scatter, Prism Downs. A canopy is meant to be dense; the tool
  says so, and prints per design so the ornamental passes can be judged by it.
- **Nothing here has been placed in game.** `render3d` draws a floating tree exactly as it draws a
  planted one, which is half of why this survived so long - judge form offline, palette in world.
