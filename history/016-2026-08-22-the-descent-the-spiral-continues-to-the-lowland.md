## The descent: the spiral continues to the lowland (2026-08-22)

Jack: the spiral staircase continues going down all the way to the lowlands. Two designs:
**`Lowland Root`** (494 - a slim oak braid off the shop islet's SOUTH rim, gripping the
measured one-thick shelf at (-24208..-24207, 30025), toes in the moss at Y41) and
**`Lowland Stair`** (2,192 - the same slab-helix idiom as the Root Stair, wound about it,
Y41-151, ~9 turns, 44 rail lanterns, ONE component, 0 overlap, all cheap). The full walk is
now: deck - workshop stair - root stair - islet shelf - LOWLAND STAIR - harbor moss, then
quay/watergate/way or east to the hamlet.

**The axis is the siting decision, and it was moved twice by measurement.** Concentric with
the taproot's keel at (-24200, 30018), the landing wraps the watergate, the quay lip and the
harbor light; under the south rim at (-24207, 30029) it clears the light's gallery by 9.5,
the quay tip by 13 and the watergate by 17, and the landing arc falls on open moss
(ground histogram Y37-43, 2 wet columns). NOT ONE of the harbor ensemble moved.

Traps, each of which shipped a clean-looking build first:

- **`_smooth` is a running MAX, so one wide feature anywhere in the wrapped design widens
  every course above it.** The root's two-cell toes carried r5.25 up the whole helix and
  parked the outer band on the harbor light's gallery; the grip bend did the same to the top
  and flared the stair past its own step-off. Toes are one cell now, and `spiral.max_inner`
  exists - a clamp on the smoothed profile, with defer_to settling the few cells where the
  core then crosses the band.
- **A twisted strand disconnects at every sideways step** - the join is diagonal-only, the
  ear-tip lesson again. The first braid was 26 components; each step now places a bulge cell
  in the previous course's column, which is also what a real root looks like.
- **The top courses terminate against the shop islet's DESIGNED rock** (its rim skirt,
  ~340 unbuilt cells in the band - burial against a design, not just terrain). So the
  isolated climb gate cannot pass BY CONSTRUCTION and is off in the config; what replaces it
  is the COMPOSITE walk - stair + islet design + capture, the audit's own step rules - pinned
  in `tests/test_lowland_stair.py` (6). `start_angle` was swept over 63 phases SCORING THAT
  WALK: at 1.1 the top courses ride the open south air and reach the shelf at exactly 151.0.
  Build order follows: the stair's top ~29 cells wait for the islet's rim.

**The Void Ladybird was re-sited** - its parked pocket held 726 cells inside the new shaft
(never built, so nothing orphaned). The distance search re-ran with the stair, root and town
reserved: the new pocket at root (-24238, 63, 29968) keeps 8 clear on every face, belly
overhead, the NW lowland floor twenty below.

**THE ALIGNMENT (same day, Jack's second review): "it doesnt align with the actual stairs -
it should be a straight down, we can break blocks on the floor etc."** He is right and the
offset siting is gone: the stair now screws straight down the taproot's own axis at
(-24200, 30018) - the Root Stair's centre, same spin, one screw deck to floor - through a
WELL dug in the shop islet's lens (121 dig cells, Y144-150, in the sidecar's dig list;
`/cscan dig` shows them). What made that safe to build:

- **`spiral.dig_above` + `dig_only`**: at or above dig_above a tread may claim a world cell
  (the cell and its headroom go on the dig list - the rimstair's "the tread cell is itself a
  dig"); below it nothing is ever dug, so the lowland's watergate, quay and ground thread the
  stair as before. `dig_only` names NATURAL ROCK - the first well rule was "anything
  unprotected", and the old stair's own slabs sit directly over the mouth courses: it would
  have dug the stair it exists to continue. And a dig may never take a protected block OR THE
  CELL ONE STANDS ON - the shop's barrels are one course over the well's north arc.
- **The harbor light is RETIRED** (Jack: "we arent gonna build the harbor light"). It stood
  four blocks inside the new annulus; the west-bank re-site happened and then the whole
  design was retired unbuilt - the stair took its site and most of its job, and the quay
  keeps its cold mooring-post light. Config kept as a record.
- **The Shop Islet design is CARVED to the well** - 287 lens-fill cells removed over the
  stair's tread+headroom envelope (noted in its config; regenerating the islet re-fills the
  well and must be followed by re-carving - `test_the_carved_islet_keeps_out_of_the_well`
  is the tripwire). trim_buried is OFF on the stair on purpose: it strips capture-owned
  cells and would eat the well's own treads; the generator self-trims below dig_above.
- **The composite walk sweep found the top the same way as before** (63 phases): at 6.1 the
  walk runs lowland moss to the islet shelf at 151.0 through the dug well, 572 landing
  cells. The old stair's landing is a short walk across the islet top from the well mouth.
  `tests/test_lowland_stair.py` (12) pins the axis equality with root_stair.yaml, the dig
  contract, replaces-nothing-outside-its-dig, and never-dig-the-old-stair.

**THE CAREFUL AUDIT (same day, Jack: "audit it all carefully now, make sure its perfect").**
Every design regenerated with full output read, plus a scripted battery: pairwise overlap
across all 33 tracked designs, dig-versus-every-design, shipped-file hashes, config
references, ladybird clearance, per-cell support. Five real defects, all fixed:

- **The islet's underside fill claimed the root's anchor cell** (-24200,141,30018), and the
  defer dropped it - leaving all 180 root cells with nothing to place against. A design can
  orphan another design's ANCHOR: check what a defer takes, not just how many. The root wins
  its anchor now; the islet is carved around it.
- **The well dug 21 cells of the Atelier Court's floor.** `dig_only` names materials, and
  stone brick is both "natural rock" and somebody's workshop floor - a dig must know what
  the rock BELONGS to. `spiral.dig_forbid` takes design paths whose cells may never be dug;
  the phase re-swept to 5.4 (zero atelier contact, still walks, 105 dig cells).
- **A deferred cell abandoned its dependants**: a rail wall whose tread went to another
  design shipped standing on air, then a SECOND wall orphaned by cascade. `_defer_to` now
  drops lanterns/torches/walls left with no neighbour, and a post-defer fixpoint sweep
  (`_drop_defer_orphans`) removes any cell with no design neighbour and no world contact.
- **A tread whose only contact was rock its own dig removes** is unbuildable by
  construction - dig first, then nothing to place against. The spiral prunes those to a
  fixpoint, and a pruned tread takes its dig entries with it.
- **A hamlet roof-overhang cell floated** where the weather hash removed its inner
  neighbour: overhangs are placed in a second pass, support-checked against the body.

Also found and left alone, stated: pre-existing overlaps among the OLD designs (Atelier x
Shop Islet 170 cells, 142 same-state; Statue Footings x Rim Hem 7; Void Giraffe x Void Isle
13) and out/-vs-schematics drift on ~8 old designs whose out/ copies were regenerated by
daily syncs but never re-shipped - not this session's work, worth a pass of its own someday.
Final state: 0 problems and 0 overlap in context on every session design, dig touches no
design's cells, zero free-floating cells, all 5,502 lowland-job blocks cheap-or-ok and 1.19.

**The gradient, and the root's honest length (same day, Jack's review).** The stair now
changes stone as it changes world - dithered thirds, measured luminance 122 -> 71 -> 48:
island stone brick at the shelf, deepslate through the twilight, the quarter's blackstone to
the ground - and the light goes cold with it, 28 warm lanterns above, 16 soul lanterns
below. `spiral.bands` is the mechanism (per-cell hash dither over band_blend courses - a
hard line across a helix reads as two stairs stacked); bands=None keeps the Root Stair
bit-identical. And the root no longer runs to the ground: Jack called the full-height root
wrong, and it now thins out inside the deepslate band (tip Y95, 225 blocks against 494) -
the island's reach ends where the underworld's masonry begins, and the helix hangs alone
below the tip. Two things that follow: `min_radius` is PINNED to `max_inner` (below the tip
the profile is empty, and an unpinned floor snaps the ribbon 4.5 -> 3.0 in one course), and
the start_angle had to be RE-SWEPT - a slimmer core changes the pitch, so the phase moves
with the profile; 4.0 reaches the shelf at 151.0 with the widest landing. The design-alone
component count splits at the top weave where trim_buried yields cells to the islet's BUILT
rim rock - connected in the world, cosmetic in isolation; the composite walk is the truth
and is the test.

