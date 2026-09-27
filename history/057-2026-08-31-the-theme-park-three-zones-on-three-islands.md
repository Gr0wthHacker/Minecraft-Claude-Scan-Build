## The theme park: three zones on three islands (2026-08-31)

Jack asked for a zoo across three 99x99 plots, expandable to 200x200 each and connecting into
600x200, with enclosures, animals and a gate. The zoo is not what got built, and the reason is
worth more than the park is.

### A ZOO IS THE ONE THING THIS SYSTEM CANNOT DO

A zoo makes one promise about twenty times - *a stranger walks up and names the animal* - and this
repo can keep it about eight times. The live roster is elephant, giraffe and capybara plus a
handful of bespoke sculptures; every cat and both bears are RETIRED on panel evidence, and the
failure is structural rather than a matter of effort or scale. Two more measurements settled it:

- **Animals here are enormous.** `X elephant` is 21x49 and 39 tall, `X lion` is 17x69, a prowling
  jaguar 13x59. At honest zoo proportions an elephant paddock is ~34x62 - a quarter of a 99x99
  plot for ONE animal - and `tools/scale.py`'s floors (proboscid 30, giraffid 59) mean you cannot
  shrink your way out of it.
- **GRASS IS CURRENCY.** `blocks.spendable("grass_block")` is False, as is every form of dirt. A
  park of lawns and naturalistic paddocks is not expensive, it is unbuildable in bulk. The lowland
  already uses moss for exactly this reason and nobody had connected it to a zoo brief.

What replaced it takes its variety from ARCHITECTURE and LAYOUT, which is the strongest thing in
this repo - the void tower, sanctum, campanile and casino hall all settled one rule and the park
inherits it whole: **what makes voxels read as architecture is regularity and openings, not
damage.** Every attraction is a structure, so there is no sculpture risk anywhere in it.

(The honest alternative, if the zoo feel is ever wanted back, is a PREHISTORIC park: a sauropod is
a neck on columnar legs, a pterosaur is a membrane wing, a stegosaur is a convex mass with planar
plates, and fossils are pure planar - every one a shape voxels render natively. It is a better fit
than a modern zoo, and it costs 6-10 new bespoke generators.)

### `gen/park.py` - seven kinds, three lands

    gate  arch  plaza  tower  stall  booth  walkthrough

    midway     wool and stone brick        the entrance, the plaza, the carnival
    frontier   spruce and cobble           the mine, the saloon, the prospect tower
    hollow     blackstone and deepslate    the haunted manor, the crypt, the clock tower

Bright / warm / dark, wool / wood / stone - three places you could tell apart from a screenshot.
Every block was checked against `palette.tier`, `blocks.spendable` and `blocks.available` before
it was written down; nothing is currency, nothing is expensive, everything is 1.19.

**THE HOLLOW'S WALL WAS ITS OWN GROUND.** Written first as `polished_blackstone_bricks` for both,
the land had no value step at all - which is this file's most-repeated palette mistake, now made
a fourth time. Three separate notes here conclude that this economy has almost no value contrast,
and every one of them measured inside ONE material family, where a ladder cannot exist by
construction. Measured across families the rungs are real:

    black_wool 21  ->  polished_blackstone_bricks 45  ->  deepslate_bricks 71

steps of 24 and 26, against the ~15 below which a trim course stops being a line. Pinned by
`test_every_land_can_actually_draw_a_line`, which measures rather than trusting the table.

### THE FAULT WORTH REMEMBERING: A SIGN ON A COLUMN THAT HAS AN OPENING IN IT

Three of the seven kinds shipped a stray cell and a fourth shipped a sign the game would refuse,
and all four were the same mistake: a gate's map board hung behind a LANE, a tower's nameplate
behind a WINDOW SLIT, a walkthrough's EXIT sign behind its own EXIT, a stall's nameplate on an
open shopfront. The wall exists everywhere except the one column somebody chose to sign.

It is invisible in every render - a wall sign floating in air draws exactly like one on a wall -
and **a connectivity check catches only three of the four**: the stall's sign was 6-adjacent to
the canopy above it and so counted as connected while still having nothing to hang from. The
support test catches all four, and it lives in `_sign` rather than at the call sites, so the next
kind cannot forget it. `_sign` returns False when it refuses, and
`test_every_kind_that_should_be_named_is_named` exists because a silently-refused sign is this
project's most-repeated failure shape wearing a new hat.

The stall's fix is architectural rather than a nudge: an open front has no wall to hang a sign
from, so it got a FASCIA - the board a shop's name actually goes on.

### Two planner faults, both of which produced a perfectly reasonable wrong answer

- **A GENERIC KEYWORD SHADOWED EVERY LATER THEME'S OWN NAME.** `_theme_for` tested each theme's
  name and its keywords together and returned on the first that passed either, so `midway`'s
  keyword "theme park" swallowed "theme park frontier" and "theme park hollow" alike and all
  three zones planned as the centre. It was caught only because two different briefs produced
  byte-identical 10,403-block plans. An explicit name is now resolved first, across all themes,
  before any keyword is considered.
- **THE ORDERING WAS DECLARED RATHER THAN MEASURED.** `bays` packs in list order and the biggest
  module must go first or it starves - the rule the Colour Wheel's three NO SITEs established.
  Ordered by the hand-typed `size` all three zones looked correct and all three were wrong: a
  tower declared 15x15 MEASURES 13x13 while a walkthrough declared 15x15 measures 15x15, so the
  tower led every zone while being the smaller module. The test measures through
  `measured_footprint` now, which is what the planner actually packs with.

### `anchor: "edge"`

`cover` already existed for a module that IS the ground. A gate needed the opposite: a module
whose POSITION IS ITS MEANING. Sited by `bays` a gatehouse lands wherever there is a free bay,
which is a gate in the middle of a field - you walk round it - and an arch to the west that is not
on the western edge does not lead anywhere. `edge` pins to a named side and centres along it, and
unlike `cover` it DOES claim its box, because everything else must keep out of the doorway.
`test_every_edge_module_names_the_side_it_is_pinned_to` also asserts each one FACES outward.

### The centre zone, planned and costed

`newisle` is the middle island and the entrance; bedrock (97600, 200, 80600), starter pad top
Y202, so the build plane is **Y203**. 16 modules, one gate on the south edge, an arch on each of
the east and west edges pointing at the neighbours.

    10,403 blocks · 21 materials · 4 short (849 black_wool, 25 signs)

Everything else comes out of stock. `plan --approve park_centre` is the gate and has NOT been
passed.

**EACH ZONE IS PLANNED AGAINST ITS CORE, AND THE EXPANSION IS A SECOND PLAN.** Jack builds the
inner 100x100 first and grows to 200x200 later, so nothing in the outer band may be load-bearing
for the core. Planning against the island's CURRENT radius gets that for free: everything sites
inside the ring that already exists and the expansion ADDS modules rather than moving them. A plan
spread over the full 200 would put the plaza's centre and the gate's approach on ground that does
not exist yet, and expanding would cost a rebuild rather than an addition.

### The three plots, and the streets (2026-08-31)

All three islands are registered. **They run along Z, not X** - bedrock at (97600, 200, 80400),
(97600, 200, 80600) and (97600, 200, 80800), which is 200 apart and confirms the 600x200 endgame
outright. So "left" is NORTH and "right" is SOUTH, and the first theme geometry - arches east and
west - was pointing them at empty void on the wrong axis entirely.

    islandleft   80351..80449   frontier   north
    newisle      80551..80649   midway     centre, and the entrance
    islandright  80751..80849   hollow     south

The main gate takes the free axis, west. Each side zone leads back along Z toward the centre.
Starter pad tops are Y202 on all three, so the build plane is **Y203** everywhere.

#### `park/paths` - and why the planner owns the routes

A path connects things, so the only thing that can draw one is the thing that knows where
everything ended up - and a generator is handed one module's `at` and nothing else. So
`planner._add_paths` reads the sited plan and passes a route network in; `gen/park._paths` draws
it. Without this the park was PACKED rather than COMPOSED: `bays` fills a grid, everything fit,
nothing collided, and there was no street. A visitor arrived at a gate and faced a field.

**BOTH AVENUES SPAN THE WHOLE PARK, AND THAT IS WHAT MAKES THE NETWORK CONNECTED.** Written the
obvious way - an avenue from each EDGE module to the hub - the paving came out in three to five
separate islands and missed six doors outright, for one cause with two faces: an avenue that
stops at the hub covers only the half of its axis its gate is on, so a spur from a door on the far
side runs out to a coordinate where there is no avenue to land on; and a SIDE zone has only one
edge module, so one of the two axes never existed at all. Full-length cross axes fix both by
construction - every front lies inside the spanned rectangle, so a perpendicular spur ALWAYS
terminates on an avenue, and the two avenues cross at the hub. That also makes every spur a
single straight run with no corner.

Three more faults, each of which drew a plausible-looking wrong network:

- **`_plot_bounds` returns (x0, x1, z0, z1)** - both X values, THEN both Z. Unpacked as
  (x0, z0, x1, z1) the axes scramble into each other and the avenues span the diagonal of the
  world: **170,191 cells of paving**, which is the only reason it was caught on sight.
- **AN EDGE MODULE IS JOINED ON ITS INSIDE FACE.** A gate faces OUT of the park - that is what
  makes it a gate - so its front approach is a cell beyond the plot boundary, which the clamp
  correctly threw away. All three edge modules read as unreached, which looks like a routing bug
  and is the geometry being right. You walk THROUGH a threshold, so the street meets it on the
  side the park is on. `_inside_of` is the counterpart to `_front_of`.
- **THE PAVING IS INSERTED BEFORE THE PLAZA, NOT APPENDED AFTER IT.** `layers.slice_plan` resolves
  a contested cell first-writer-wins in plan order, and the paving and the plaza occupy the same
  course - appended last, every avenue would be overwritten by the plaza it crosses and the park
  would have invisible streets. Buildings still come first and still win: building over path over
  plaza is the order actually wanted.

The paving is laid even UNDER a building, deliberately: skipping obstacle cells can SPLIT a route,
and a network that is not connected is not a network. The building's own pad occupies the same
course and wins in the slice, so the overlap is invisible and the connectivity is guaranteed. Only
LAMP POSTS are skipped inside a footprint, and lamps are only placed on avenues - a lit spur to
every food stall is a lamp every four blocks, which reads as a fence rather than as a street.

`tests/test_park_plan.py` pins the network against all three real plots: one connected walk, every
door on the street, and nothing off the plot.

#### The three zones as planned

    park_centre   17 modules   11,419 blocks    short: 1,325 black_wool + 25 signs
    park_left     14 modules   10,884 blocks    short: 380 spruce_log + 17 signs
    park_right    13 modules   11,383 blocks    short: blackstone family ~5,400 + 16 signs
                  ---------    ------------
                  44 modules   33,686 blocks

**The Hollow is the expensive one and the reason is structural, not a mistake**: it is the only
land whose ground, wall and trim are all stone rather than wool, and none of the blackstone family
is in stock in quantity. It is all `cheap`-or-`ok` tier, so it is a crafting and buying job rather
than an affordability problem - but build the centre first.

None of the three is approved.

#### Buildings that address the street (2026-08-31)

`facing` was a theme constant, so a booth sited north of the avenue faced exactly the same way as
one sited south of it and about half the park showed a blank rear wall to the street its own spur
ran to. A shopfront that cannot be seen into is a shed.

**ORIENTATION IS DECIDED AFTER SITING, WHICH MEANS SITING MUST RESERVE A SQUARE.** The answer
depends on where a module landed relative to the hub, and turning a 9x7 building through 90
degrees makes it 7x9 - which no longer fits the slot booked for it. `orient: True` on a theme
makes the siting loop book `max(w, d)` on both axes, so any of the four facings fits the same
slot and the turn can never push a building into its neighbour. It costs a little packing
efficiency; the plots are 13% used.

**AND THE DECISION MUST BE MEASURED FROM SOMETHING THE TURN CANNOT MOVE.** Taken from the built
box, turning a module moves its centre, which can flip the very decision that turned it - one
module per zone came out facing one avenue while the recomputed answer named the other, so its
shopfront addressed one street and its spur ran to another. `_street_axis` reads the RESERVED BAY
instead, which does not move, so the answer is a fixpoint. The same function decides both the
facing and which avenue the spur runs to: asking that question twice in two places is exactly how
the two disagree.

Edge modules are left alone - a gate faces OUT of the park by definition, which is the whole
reason it is on the edge.

#### Shipped (2026-08-31)

    Park_Centre Complete   9,544 blocks   origin 97551 202 80551
    Park_Left Complete     9,145 blocks   origin 97564 202 80357
    Park_Right Complete    9,326 blocks   origin 97564 202 80751

All three approved, emitted, generated, sliced and shipped; tracked in `sync.yaml`. Each zone is
one connected walk with every door on the street, no module overlaps, nothing off the plot.

**`layers --floor` IS THE COURSE THE FLOOR BLOCKS OCCUPY, NOT THE PLANE YOU STAND ON.** The park
declares a build plane of Y203 and every module lays its pad at Y202, so `--floor 203` filed the
entire park as MACHINES - 5,549 blocks of paving in the basement layer of a park with no machines
in it, and a Floor layer of 462. It is `--floor 202`.

**The starter island is in the way, by about 54 cells per zone** - a 6x6 grass pad, two dirt, and
the centre's tree. A printer places into AIR, so those cells simply will not fill and the paving
will show a small green patch. Clear the pad and the tree before printing, or keep it.

### Still open

- ~~The left and right islands are not registered.~~ DONE - all four islands are in the registry.
- ~~The layout is PACKED, not COMPOSED.~~ DONE - see the street network above.
- ~~The buildings are not oriented toward the streets.~~ DONE - see above.
- **Nothing has been looked at in game yet.** All three zones are shipped and placeable; that is
  the next thing, and it is the only check this pipeline does not have.
- ~~Nothing has been looked at in game, or rendered. `tools/look.py` cannot draw these yet - it
  wants a facing VECTOR and the park sidecar records a word, the same gap the casino has.~~
  RENDERED - see "The park, finally looked at" below. `tools/look.py` and `tools/panel.py` both
  read a compass word now, through `park._STEP`. In-game is still open; nothing here replaces it.
- **The gate's lanes are fence gates, deliberately.** `circuit.py` has no model of a DOOR, so a
  plate-and-iron-door turnstile could not be asserted by simulation, and this repo cut two
  finished casino games rather than ship a machine it could not judge. A powered turnstile is a
  fine thing to add the day the simulator can judge one.

