# The empty-ground audit, and what was done about it

Jack: *"lets do a empty ground cleanup, we want to look and locate all available spaces, make
plans to deal with them or intentionally leave them, we can add shrubbery, flowers, or other
accents, or new objects if appropriate, be thorough."*

```bash
python tools/park_empty.py                 # the inventory
python tools/park_empty.py --map out/e.png # a plan of it
python tools/park_empty.py --walk          # did the dressing wall anything in?
```

---

## 1. The measurement

**NOTHING IN THIS PIPELINE HAD EVER ASKED WHETHER THE GROUND BETWEEN THE DESIGNS WAS FINISHED.**
Every check the park has measures a design against the world — is the state legal, is it
supported, does it collide, is it affordable, does the circuit work — and a bare lawn passes all
of them, because a bare lawn is exactly what `Park Ways` is supposed to lay. The gap only shows
up if you ask a different question, and this project had already written down what that question
is, about the island: *"the plate has no dead ground — every walkable cell is within 4 blocks of
something built or planted, median 0."* It had never been pointed at the park.

Two definitions, and they are the whole tool:

| | |
|---|---|
| **bare lawn** | a column whose ground course is `moss_block` carrying nothing above it but air and the lawn's own moss trim. Paving is not bare. **A tuft of grass is not bare either** — the standard is "built OR PLANTED". |
| **openness** | a bare column's distance, in the plane, to the nearest column that is not bare. This is the number that separates a two-cell verge beside a kerb — which is DESIGNED lawn and wants nothing — from the middle of a forty-cell field, which is a hole. |

Over the shipped park, **before** any of this:

```
120,000 lattice columns
 28,023 BARE LAWN                                             23.4%
  6,559 DEAD - four or more blocks from anything
  1,903 eight or more.  1,080 ten or more.  The worst is THIRTEEN.
```

### The one definition that matters, and the drift it nearly caused

The first draft of `park_empty.py` counted a flower or a tuft of grass as still-bare ground, on
the reasoning that dressing is what the audit exists to ADD. That reading and the `--with` reading
(which counts a design's columns whatever they hold) then disagreed **by three thousand columns**
on the same park: 1,305 dead cells before the dressing was shipped and 4,443 after, with nothing
having changed but which file the blocks were in. One definition, or the tool that finds the hole
and the pass that fills it are talking about different parks — the same rule
`proportions.measure` and `rubric.score` share an entry point to avoid.

---

## 2. The inventory, and the decision on every part of it

`before` and `after` are dead columns — bare and more than four from anything.

| # | region | before | after | decision |
|---|---|---|---|---|
| A | **rim reserve** V187–199, all lands | 3,704 | 1,020 | **light terrain only** — see below |
| B | **service band** V157–169 | 990 | 72 | dress, roughly — it is back-of-house |
| C | **front threshold** V0–5, all lands | 630 | 66 | dress — it is the first ground a guest sees |
| D | **midway public floor**, mostly the balloon field V84–152 / U216–255 | 531 | 22 | dress heavily |
| E | **midway exit band** V128–151 | 364 | 0 | dress |
| F | **claim reach**, the lakeside V87–122 / U173–211 | 366 | 7 | dress |
| G | **prismworks + prism reach** | 237 | 42 | dress lightly — the land is already 97% built |
| H | **the Frontier above V6** | 593 | 479 | **LEFT ALONE — five designs already dress it** |

```
                threshold     public       exit    service        rim     total
  before              630        837        398        990      3,704     6,559
  after                66        155         33         72      1,020     1,346
```

**Median distance 2 → 1. Mean 3.21 → 1.93. Dead ground down 79%.** The worst column in the park
is still 13, and every column that bad is in the rim reserve.

---

## 3. What was built

Two designs, one generator, **5,490 blocks, all cheap-or-ok tier, 0 overlap, 0 new placement
problems in context, and 0 clashes with any other module.**

| design | blocks | what it is |
|---|---|---|
| `PF Park Green` | 3,676 | V0–186, every land but the Frontier: meadow, flower beds, shrubs, hedge runs, ornamental trees, boulders |
| `PF Park Rim Green` | 1,814 | V187–199, the protected reserve: rough moor only, capped at three courses |

### THE DISTANCE IS THE DENSITY

Every land-dressing pass in this repo so far — `frontier_scatter`, `thicket`, `claimrow` — uses a
smooth noise field, which spreads material evenly over ground that is not evenly empty: a two-cell
verge beside a kerb gets the same treatment as the middle of a forty-cell field. `gen/parkgreen.py`
drives its density from the **measured openness of each column instead**, so the pass puts its
material exactly where the hole is and leaves the verges alone. It is the one thing a cleanup pass
has to get right, and it falls out of the same distance transform that found the holes.

```
openness < 3     nothing at all - a verge is designed lawn and stays a verge
openness 3-4     flat pieces only: meadow, a bed, a shrub
openness 5-6     ...and hedge runs, ornamental trees, boulders
openness 7+      the drift grows: one step of radius for every three blocks past the ramp's top
```

The size scales as well as the odds, because a dozen small beds in a forty-cell field read as
spots on a lawn and the same material in three big ones reads as planting.

### The rules it inherits, each from something this repo got wrong once

- **DRIFTS, NEVER CONFETTI** — the noise goes on the drift's RADIUS, never on the cell. The
  Lowland Thicket shipped the per-cell version once (191 blobs, 75% of them one or two cells) and
  the deck soffit shipped it again in the loudest block available.
- **A HEDGE SHORTER THAN FOUR CELLS PLACES NOTHING.** The deck soffit's run gate, in leaves: a
  line too short to read as a line is not a shorter line, it is scatter.
- **ONE HUE PER BED** — a family is a flower and its own second tone. Three tones of one colour
  beat two tones and a third hue (the flamingo), and a bed of eight species reads as a seed packet
  emptied on the ground.
- **EVERY LAND PLANTS ITS OWN SPECIES.** Oak and red beds on the Midway, jungle on the Lost
  Plateau, birch and azalea over blue flowers in Prismworks, mixed and wilder in the reaches. The
  dressing is the one layer that could have read the same everywhere.
- **NOTHING ON PAVING AND NOTHING NARROWING A WALK** — `path_clear: 2`, and `Park Ways` owns every
  paved cell in the park.
- **RULE 12** — `pink_petals` is the obvious flower for a bed, is cheap, exists in the client
  registry and passes every other check in this pipeline. It is a **1.20** block on a 1.19 server,
  and this repo has shipped exactly that mistake once. It is named and excluded by test.
- **RULE 16** — every block is `spendable`. Dirt and grass are CURRENCY on this server, which is
  the whole reason a park cannot be fixed with lawn in the first place.

### Two findings worth keeping

**THE PARK'S OUTERMOST TWO COURSES WERE UNPLANTABLE BY CONSTRUCTION.** The front threshold V0–5
measured as the third-largest hole in the park **with a dressing pass nominally covering it**:
`frontier_scatter.clearing` refuses any candidate whose whole `path_clear` neighbourhood is not
lawn, and past V0 there is no lawn because there is no lot. Every lot that stops at the plot edge
has this. Here the lattice IS the plot, so a neighbour past its edge is sky rather than a refusal
— `_Green.clearing`, and `tests/test_parkgreen.py` pins both behaviours side by side.

**RULE 15 REACHES THE DENSITY, NOT JUST THE GROUND PROBE.** `_Ground.mine` lets a pass re-plant
its own standing work — without it `PF Frontier Scatter` shipped at 428 blocks against 3,843 on
its second run. The same failure arrives a second way here: once the pass is shipped,
`Park Complete` CONTAINS it, so every column it planted measures as *built*, the openness under
every drift collapses, and the ramp plants nothing. `openness()` takes `mine` and puts those
columns back to lawn before the transform runs. **Regenerated against the park that now contains
it, the pass comes out at 3,676 blocks — bit for bit what it was before the ship.**

### It does not wall anything in

A hedge is a legal, supported, affordable, non-colliding run of leaves. Two courses of it across a
narrow lawn is also a fence, and **nothing else in this repo would see that** — the audit checks
blocks, not routes. So `park_empty.py --walk` floods the park's standable surface with and without
the dressing and compares:

```
walk from the spine at U290 V19:
  reachable before 96,788   after 96,691
  columns the planting OCCUPIES  563   (expected - a shrub is not a hole)
  columns cut off behind it        0   OK
```

---

## 4. What is deliberately left, and why

### THE RIM RESERVE — the biggest hole in the park, and the one that may not be paved

V187–199 is **3,919 columns in one blob**, ten deep and four hundred and thirty long, and it holds
every column in the park that is ten or more from anything. It is also a declared reserve:
`PARK_GRID_PLAN.md` — *"171–199 | protected rim and void reserve — 0 paved cells, asserted"* —
for "support, terrain, void safety, sightline protection", with
`tests/test_parkways.py::test_the_protected_rim_reserve_carries_nothing` holding the ground layer
to it.

The honest reading is that **paving is forbidden and terrain is the reserve's own stated
purpose**, and a rail rider on the V172–186 viaduct spends the whole journey looking out over this
strip, which is the one audience it has. So `PF Park Rim Green` takes it at a third of the main
pass's density, **capped at three courses, with no trees and no hedges in its kit** — rough moor
rather than lawn, and the outward sightline the reserve exists to protect survives it.

**To leave the reserve as bare moss instead**, drop `PF Park Rim Green` from `EXTRAS_READY` in
`tools/park_place.py`. That is a defensible choice; it should be a deliberate one.

The Frontier's own rim is not touched at all — `PF Sauropod` stands at U8–70 and `PF Frontier Rim`
lays the cliff walk and the pterosaur nesting colony at U75–172 — and neither is a 66-column
margin either side of `PF Wyrm Gate`, whose whole job is a 36-block skull read against empty sky.
Those two exclusions are most of the 1,020 dead columns left in the band.

### THE FRONTIER above V6 — 479 dead columns, left on purpose

`PF Frontier Scatter`, `PF Frontier Overgrowth`, `PF Frontier Rim`, `PF Plateau Vale` and
`PF Plateau Bone Bed` already dress that land. **Two planting passes on one strip is the clash no
single design can see** — each honestly reports `overlap 0` against the capture, because the
capture does not contain the other — and this repo has recorded that failure four times. The one
exception is the front threshold V0–5, which the scatter structurally cannot reach.

### THE VERGES — 24,680 columns of bare lawn are still bare, and that is the design

A path only reads as a path if there is something it is NOT. `Park Ways`' own docstring says so,
and its verges carry the lamp posts and the benches. Anything under `open_min: 3` is left
untouched by construction.

---

## 5. Still open — Jack's call, not a silent edit

1. **The front approach could be a composition rather than a scatter.** V0–5 at U270–330 is the
   first ground a guest walks on and it now carries rough meadow because that is what a sweep
   puts there. An avenue — clipped beds and a paired line of trees flanking the entry road — is
   the one place in the park where formal beats naturalistic, and it is perhaps 400 blocks.
2. **The Mine Ridge's own lot has a 158-column hole** at V100–134 / U156–166, eight from anything,
   between the coaster and the works. It is inside `PF Frontier Scatter`'s keep-out (the ridge's
   lot) and the ridge's talus does not reach it, so nobody owns it. That belongs to whoever owns
   the ridge, not to a dressing pass.
3. **The Frontier's remaining 479** could be closed by raising `PF Frontier Scatter`'s density —
   a one-line config change — but it re-plants a land already signed off, so it is not made here.
4. **A screening hedge along V157** would hide the back-of-house lane from the exit band. The
   sweep puts random planting there now; a deliberate line is a different thing and a better one.
5. **Nothing here has been placed in game.** Everything above is `render3d`, which draws with the
   same colour DB the palette picker optimises against — judge form and mass offline, judge
   PALETTE in world. This is the check this pipeline does not have.

---

## 6. The rim rookery — the strip behind the railway, rebuilt

Jack, after the cleanup pass: *"what about the area behind the railway where the dinosaur is, that
whole area needs to be refined, i like the eggs and the idea of other small things there."*

`mcbuild/gen/rookery.py`, `configs/pf_frontier_rim.yaml`, `tests/test_rookery.py` (18).

### THE MEASUREMENT, AND IT IS ONE NUMBER

The Frontier's rim is V187–199 by U0–172: the only band in the land with real room, the only one
against the void, and the only one a guest reaches **by train**. Split at the sauropod:

| | columns | carry something | tallest | over 6 courses |
|---|---|---|---|---|
| sauropod end U0–70 | 923 | 57% | 50 | 504 |
| **colony end U71–172** | **1,326** | **37%** | **5** | **ZERO** |

**A hundred and two blocks of nesting colony with nothing over three courses tall**, at 0.6 blocks
per column. That is not a shortage of ideas, it is a shortage of HEIGHT — and this repo already had
the rule written down about this exact land: *"on this moss, under ten-tall trees, architecture
below ~6 courses dissolves into ground noise."* The old design (a 3-wide walk, four scrapes, two
snags) was entirely under it.

### What is there now

**3,982 blocks, 0 placement problems, 0 module clashes, all cheap-or-ok.**

| | |
|---|---|
| **perch stacks** ×6 | sea stacks of the rim's own rock, 9–14 courses, guano-capped. The skyline the strip measured zero of, and isolated COLUMNS — they frame the void view the reserve protects rather than walling it |
| **nests** ×8, **19 eggs** | full clutches, and hatched scrapes with the shell still in them, so the colony reads over a season rather than as one photograph repeated |
| **hatchlings** ×3 | juveniles beside a nest: one convex mass with a crest on it, the ladybird's category |
| **the hide** | a timber observation hut on the walk, doorway to the path, viewing slit to the colony, and a destination the walk never had |
| **the bone find** | a partial skeleton weathering out of the rim, ribs arcing off a raised spine |
| **the cliff rail** | a fence along the drop, in gaps — a continuous one is a wall and the view is the point |
| **the belly deck** | a railed plank deck under the sauropod, and a walk that gets you to it |
| plus | two plaques, ranger kit, jungle scrub |

```
                       columns   carry something   tallest   over 6
colony end   before      1,326               37%         5        0
             after       1,326               79%        14      287
sauropod end before        923               57%        50      504
             after         923               84%        50      571
```

### THE WALK GOES UNDER THE ANIMAL, AND THE LEGS DECIDE HOW WIDE IT IS

Measured off `PF Sauropod`'s own artifact at the ground course, the animal occupies **U28–32 and
U46–50 and nothing else** — two rows of feet, near leg V188–192, far leg V194–198, **V193 clear
straight through**. Everything under the barrel is open lawn, and U33–45 is thirteen blocks of it
twenty courses below a fifty-block dinosaur. It was bare grass with nothing leading to it.

So the middle walk segment is DECLARED five wide and the feet carve it to one for three rows,
twice. That squeeze is what the world gives, not something special-cased — and **nothing keeps out
of the sauropod by box**: its silhouette is 11 of the band's 13 courses, so a keep-out would forfeit
63 blocks of strip. Every piece asks the ground probe per CELL as it rises.

### Five things that shipped clean and were wrong

- **A WALK NEEDS HEADROOM, NOT SKY.** `_Ground.lawn` demands nine clear courses — right for a tree,
  wrong for a path. The sauropod's legs merge into its barrel as they rise, so V193 is open at the
  ground and closed nine up: `lawn` refused it and put a **one-cell hole in the only route to half
  the strip**. `rookery.underfoot` asks for three courses instead.
- **A GATE IN THE WRONG WALL IS A WALL.** The belly deck's rail left its openings on the sides, so
  it ran a complete fence across both ends of the walk it stands in the middle of. A flood, not a
  count, is the only check that sees this: **all 173 columns are now reachable on foot** from either
  end, and the test asserts it.
- **BOTH OF ITS SIGNS WERE REFUSED IN SILENCE.** The hide's board was written at the doorway's own
  column — the one column of that wall with nothing in it — and the deck's post landed in the cell
  its own sign then needed. A refused sign draws exactly like no sign at all; this park has shipped
  that in four building kinds already. All four boards now place, and `signed` is asserted.
- **A STRICT SUPPORT RULE CANNOT WIDEN A COLUMN**, so the crown never formed and every stack came
  out a spike — a one-wide shaft with a white cap, which reads as a smokestack. The crown is
  corbelled (each course laid centre-outward so a cell leans on the one beside it), and the profile
  is a flared foot, a waist and a head that overhangs it.
- **A SKELETON LAID FLAT ON MOSS IS A FLOOR DECAL.** The bones sit a course proud of a rock matrix
  now, with the ribs arcing off the spine.

And one measurement bug in the tests: counting "any solid cell" made the stack's waist read as
**wider than its foot**, because a jungle crown from the planting sweep hangs over the shaft at
exactly that height — the same shape of error as measuring an animal's barrel and getting its mane.

### Still open

- The rim is reached from the Frontier Halt at U96 and by walking the service band. There is no
  spur from the guest street to it; the transit line is the intended arrival and nothing says so.
- Nothing has been placed in game. `render3d` draws with the same colour DB the palette picker
  optimises against — judge form and mass here, judge palette in world.
