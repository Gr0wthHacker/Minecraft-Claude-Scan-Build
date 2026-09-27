## THE BROKEN PLATEAU: the north end, and the axis the park had not used (2026-09-12)

Jack, looking north from the middle of the Lost Plateau: *"this area of the map for park complete
feels very weak, the buildings have unclear purposes, and i think the tower is a cop out and feels
lazy ... we need to redo this area so it matches the wow factors of the other 2 sides."*

**EVERY HALF OF THAT WAS A MEASUREMENT.** Off the shipped composite, before anything was drawn:

| | b/col | >=3 tall | >=12 tall | tallest |
|---|---|---|---|---|
| Lost Plateau, mountain end | 6.10 | 63% | 45% | Y279 |
| Lost Plateau, north end | 3.45 | 54% | 22% | Y253 |
| ...the far end alone, tower out | 2.68 | 61% | **11%** | Y242 |

`PF Vantage Frontier Lookout` was 4,154 blocks, 17 x 17, 56 courses and **100% of its own footprint
at full height** - a shaft, one interactive block in it - standing at the LAND'S CLIMAX, because a
guest enters from the Midway at U169 and walks north.

**AND THE STRUCTURAL FINDING: both wow factors are terrain-scale geology with a route driven
through it.** The Mine Ridge (41,948) with a coaster bored through it, the Prism Well (36,503) with
a descent down it. UP is taken and DOWN is taken; the axis nobody had used is **OUT** - and the land
is called the Lost Plateau, which is by definition flat land that ENDS IN CLIFFS, with the park's
own rim sitting unused at U0 and open void past it.

    far end U0-20:  >=12 tall 11% -> 37.5%,  b/col 2.68 -> 3.42,  and the tallest thing is a mast
    on a cantilever over a 28-course gorge instead of a solid shaft

### IT IS `bonebed.py` AT MOUNTAIN SCALE, NOT A NEW HILLSIDE

A gorge is a very deep pit whose floor is the plane and whose relief is spoil, which that generator
already builds - and it also already had the gallery, the ramps, the skeletons, the gantry and the
arch. Four things were added and every one is opt-in, so the Vale and the Bone Bed rebuild
**bit-identical**, asserted as the first test in `tests/test_broken_plateau.py`:

    brink       a lot edge that gets NO dead-level apron: the mass runs to the boundary and BREAKS
    seams       fossil beds exposed in the pit walls - the dig moves INTO the scarp
    bridge      a LEVEL deck on sagging cables, at the crest, over the gorge
    belvedere   the cantilever at the brink - what the tower is replaced BY

**A BRINK IS ABOUT WHO STANDS AT THE FOOT OF IT, NOT ABOUT THE GEOMETRY.** Dropping the WEST apron
too was tried: at the lot's own boundary the mass simply stops, so V24 came out as a thirty-course
sawn plane facing the west promenade - a retaining wall. At U0 the identical cut is right, because
that is the park's edge and there is nothing beyond it. Same arithmetic, opposite verdict.

**THE SEQUENCE IS THE DESIGN, and it falls out of the slope rule.** `soft` binds on distance from
the nearest street, and the nearest street is the avenue at U41-45, so the mass CLIMBS northward
and is highest at the rim - which is also how a real canyon forms, cutting back from the edge. So
the gorge is deepest at the mouth and shallows to nothing at its head, and the walk gets better the
further you go: the arch on the avenue, a ramp down into a notch, the walls rising to thirty
courses around you, the bridge crossing overhead against the sky, and the gorge opening at the rim
with the belvedere cantilevered over your head. Walk-tested from the avenue, no jumps, every step
reversible.

### FIVE BUGS, EACH OF WHICH SHIPPED A CLEAN AUDIT

- **A VINE HANGS ON A BLOCK, NOT ON A HEIGHT FIELD.** The belvedere, the bridge and the gallery all
  CLEAR courses above their own decks, so a face the field calls solid is air by the time the
  planting runs - six vines on nothing. Then two more survived, clinging to a `jungle_fence`:
  `lot.has` is the canvas's own "is anything here". Rule 11 - `blocks.is_full_cube` is the question.
- **AN ARCH'S PIERS MUST BOTH BE BUILT UP TO THE LINTEL, not each to its own height.** Latent in the
  shared generator since it was written; it only shows when the two feet stand on different ground,
  and the far half of the gate shipped as a 21-cell stray.
- **A FLIPPED GALLERY'S FLIGHT RUNS THE OTHER WAY** - that is what the flip means - and at rising u
  from that deck was the AVENUE. Eight courses of deck is eight cells of run, so the stair came down
  into the street's own lanes at four places. The deck is one course over the mesa at both ends, so
  it needs no flight at all.
- **A CABLE AND A RAKING STRUT STEPPED DIAGONALLY.** The ear-tip rule, in ironwork and in timber.
- **AND THE SHOP'S TERRACE PAVED TO ITS OWN DECLARED DEPTH RATHER THAN TO THE PLINTH** - one empty
  course between them, and ninety cells of legal, supported, perfectly clean paving that nothing
  joins.

### THE FIRST PLOT-SCALE CAPTURE OF A PARK ISLAND

`/cscan islandplateau` - this file has asked for one for weeks (*"the park has no capture at plot
scale, so its progress is honestly unknown"*). It changed the decision twice:

- the tower was **345 of 4,943 built (7%)**, so retiring it cost about three hundred placed blocks;
- of the Vale's 4,542 built cells on this ground **4,046 are the Y202 moss lawn**, which is
  `Park Ways`' and stays - so a replacement on the same lot costs almost nothing;
- and the whole design's overlap against the real world is **283 cells, every one at Y203-205 and
  every one grey rock for grey rock.**

It is also the right `verify_against` for a design that REPLACES another: `Park Complete` still
contained the Vale, and verifying against a composite that holds the thing being replaced is the
self-reference trap for the eighth time.

### THE FIELD SHOP, on the lot the tower left (`gen/plateaushop.py`, 577 blocks)

Jack: *"the lot where the tower was is empty, just hanging vines - what can go there ... maybe we
keep 1 building and put another shop there"*, and on where: *"tower lot"*.

**THE VINES WERE A LEFTOVER OF MY OWN**: 450 of them, every one hanging on nothing, because
`PF Frontier Overgrowth` had clung them to the tower's masonry and was not regenerated when the
tower was retired. Same class as the frontage marquees the signage audit found - and the stale
keep-out that had been reserving the lot for a module nobody places any more went with it.

The lot is 17 x 17 at the land's climax on the V123-127 avenue, and its own north edge is the
park's rim - so it is a shop AND the terrace the belvedere is seen from, which is the second thing
for free. It is OPEN-FRONTED, which is the argument this park has already had three times:
`Arrival Court`, `Boomtown Spine` and the `Skill Arcade` were all retired for being a hall on a lot.
A hall reads as a building; a counter reads as a shop. **And it holds NOTHING** - the Abyss Market's
rule - so the board names the server's own `/shops` and the counter carries a bell somebody can
ring.

Its palette is `bonebed.CAMP`, not `park.py`'s `frontier`, which is still the spruce-and-cobble
mining town this land was re-themed away from. **Two buildings in one land in two woods is how a
re-theme leaks**, and `test_plateau_shop.py` fails on any spruce but a sign.

    the tower lot: 289 moss + 450 floating vines, 0 verbs
              ->   875 blocks, 3.03 b/col, 65% of columns 3+ tall, a bell and three boards

### THE MINE WORKS IS RE-THEMED, NOT RETIRED - and the recommendation changed once it was measured

I recommended retiring it before measuring what it was. It is **7,598 blocks, 37% BUILT (2,806
placed), and it carries the land's only moving mechanism** - a five-head battery with an enforced
`fun_contract`. Retiring it would have cost both. Jack: *"retheme it."*

**`PF Mine Works` -> `PF Prep Works`, and NOT ONE BLOCK MOVED** - same origin, same shape, **0 cells
whose block state differs**, asserted before the rename shipped. A crusher is exactly what a fossil
lab uses to free bone from matrix, so the structure, the redstone and the contract all keep working
under a name that fits. What changed is the design name, the prose, and three boards - one of which
still said *"shipped by rail"* for an ore line the config had already switched OFF.

**THE MODULE FILE KEEPS ITS NAME.** `gen/mineworks.py` builds a generic stepped works with a machine
in it and a loading dock; renaming the file would touch the registry, the tests and every import for
nothing a guest can see. Its docstring says what it builds now, which is the part that goes stale.

**AND ITS BUTTON IS REACHABLE, which was measured rather than assumed** - and the first test of it
was WRONG in a way worth keeping. Asked about the button's OWN column it reported NOT REACHED: that
column is inside the machine bay, and a button at Y207 is pressed from a floor at Y206 one or two
cells over. Asked properly - every standable cell whose EYE is within four and a half blocks, which
is how the printer asks the same question - the nearest is **Y206 U50 V159, two blocks away and on
the guest network**. A machine nobody can reach is a prop, and a reachability answer means nothing
without the movement model stated beside it.

**And the Assay + Prize Office stays**: 20 x 46, 73% of its footprint three courses tall, and it
houses `PF Game Prize Office`, the redemption counter for the land's three games. Retiring it would
orphan a working game, which this park has done to itself before.

**Nothing here has been placed in game.** All of it is `render3d`, which draws with the same colour
DB the palette picker optimises against - judge form and mass off the sheets, palette in world.

