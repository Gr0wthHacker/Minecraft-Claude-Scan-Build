## THE PARK HAD NO SKY, AND THE TWO LANDS NEEDED OPPOSITE ANSWERS (2026-09-13)

Jack: *"audit entire area and make sure all design elements are sophisticated visually, impactful,
and we should look to add more sky elements that are disconnected e.g. maybe a high up plane or
something interesting"* - then, mid-build: *"this applies to carnival area as well."*

### THE MEASUREMENT, and it is one number per land

Cells standing above Y250, over the park as placed, against a build limit of 320:

| land | total | >Y250 | >Y280 | tallest | what is up there |
|---|---|---|---|---|---|
| Lost Plateau | 169,640 | **1,260 (0.88%)** | 0 | Y279 | 538 of it the ridge's own canopy, 691 the pterosaur - and it is PERCHED |
| Midway | 82,319 | 5,515 (6.70%) | **0** | Y276 | Wyrm Gate 4,488, Sky Lift 730 |
| Prismworks | 164,997 | 6,054 | 1,405 | Y302 | Prism Well, Prism Rig, Crown Descent |

**THE LOST PLATEAU'S WHOLE MASS SITS IN A THIRTY-COURSE BAND** - 87% of it below Y230 - and its
measured skyline runs Y211 to Y252 the entire way across with a single spike at x97600-97620, which
is the pterosaur's crag. Every render from every bearing is the same picture: a dense green strip
across the bottom third and two thirds of empty blue over it.

**AND THE GROUND CANNOT FIX IT.** 27 free pads of 8x8 or better in the whole 600x200, and this land
already holds the park's two largest terrain designs. What it has none of is anything a guest looks
UP at.

### THE TWO LANDS ARE SHORT OF DIFFERENT THINGS, so they got different designs

- **The Lost Plateau is short of MASS**: one object in 34,000 columns. `gen/skies.py` gives it
  the aircraft Jack asked for and a **flock of four pteranodons on the wing** around it - see
  "the floating isles were built and thrown out", below, for what that replaced and why.
- **The Midway is short of ALTITUDE**: it already has a middle sky (a skull you ride a train
  through, a wheel topping Y276) and then fifty courses of nothing. A second floating mountain here
  would crowd what is already up there. `gen/carnivalsky.py` gives it the fair's **airship** and
  **three firework bursts** - the first things in the land higher than the wheel.

Every piece of both is on the good side of this file's own measured line. An isle is one convex
mass carrying a pattern (the ladybird's category); an aeroplane is sheets, a taper and columns; an
airship hull is one convex mass; a burst is pure radial columns. **Nothing in either has a joint
that describes compound muscle**, which is what retired eight mammals and then a stegosaur.

    PF Plateau Skies   3,729 blocks, 5 pieces (the aircraft + 4 pteranodons), 0 problems
    PF Midway Skies    7,110 blocks, 4 pieces (the airship + 3 bursts), 0 problems
    ...and ZERO cells contended with any of the 44 modules in the park. They hang in open air

    Lost Plateau >Y250   1,260 -> 4,917      Midway >Y280   0 -> 7,044
    Lost Plateau tallest Y279  -> Y300       Midway tallest Y276 -> Y311

### **DISCONNECTED IS THE DESIGN, SO THE USUAL CONTRACT IS EXACTLY BACKWARDS**

One connected component would mean two of them were touching, which is the one thing a sky
composition must not do. `finish.drop_floaters` is off and every check that normally demands one
piece demands N instead - and then demands that each piece is WHOLE, which is where the real bugs
were. All four of these shipped with a clean audit, a correct bill of materials and a plausible
render:

- **SEVEN TREE CROWNS AS 29-CELL ISLANDS.** The crown skipped its own centre cell at dy=0 - the
  obvious way to keep the trunk visible - and that cell is the crown's ONLY join to the trunk.
- **THE UNDERCARRIAGE HANGING OFF THE AIR BEHIND THE WING.** Placed at f = L*0.16 it is past the
  trailing edge; a strut hanging from nothing renders exactly like one hanging from something.
- **THE AXLE ONE CELL SHORT OF ITS OWN LEGS.** `range(int(-span*0.13), int(span*0.13)+1)` against
  legs placed at the unrounded value.
- **THE AIRSHIP'S GONDOLA AS A 199-CELL ISLAND UNDER ITS OWN AIRSHIP.** Its struts were a fixed
  height and **the hull's underside is a course higher at the flanks than on the centreline,
  because a hull is a sphere.** `loft.Frame.solid` is the only honest witness; this repo has had a
  mane, a pair of ossicones and a tail come away from computed radii.

### THE BANK WAS BUILT, SWEPT AND THROWN AWAY

The aeroplane was rolled into a turn, because level it is a CROSS - which is exactly how the
pterosaur reads from the ground, a small dark crucifix on a rock. **A banked wing is a STAIRCASE**,
and at 46 cells of span every one of its steps is visible edge-on. Two courses of thickness made it
worse, not better: each step became a chunky tread and the wing read as venetian blinds.

Rendered at 0, 7 and 16 degrees side by side the answer is not close - at 16 it is a flight of
stairs, at 7 it is slats, at 0 it is two clean sheets with a fuselage between them and the aircraft
reads instantly from every bearing including from directly below. **The composition carries the
motion instead**: it is flying through the gap between two of the isles.

`test_a_level_wing_is_a_SHEET_and_a_banked_one_is_a_STAIRCASE` pins the ARITHMETIC - how many
distinct courses the aircraft occupies at each angle - because a render of a banked wing and a
level one are both perfectly good renders and only one of them reads as a wing.

### Four more, each a rule this file already carries

- **A PART COUNT IS CHANGED CELLS. NOT `put` CALLS, AND NOT `Frame.placed`.** `placed` counts
  WRITES, so two sweeps that overlap increment it twice: measured that way the aircraft's body and
  wings came to 5,437 cells in a 2,124-cell aeroplane. Counted as NEW cells instead, a roundel and
  a cockpit read 0 - they are PAINT, they recolour the wing and the fuselage they sit on - which is
  indistinguishable from the part not having been placed, and that ambiguity is the whole reason
  the count exists. The ankylosaur's horns reported 124 placements and gained ZERO cells.
- **A PROPELLER IS ABOUT A FIFTH OF THE SPAN ACROSS, NOT HALF.** At 0.24 of the span each way the
  blades were a 22-course vertical bar off the nose - a mast, and in a render of the whole land the
  tallest thing on the aircraft by a factor of three. Anything in absolute or near-absolute
  fractions has this latent.
- **A STRIPE ALONG THE LENGTH IS WHAT READS BROADSIDE, AND BROADSIDE IS THE VIEW.** Five one-cell
  rings round a fifty-six block airship came out 78% white and read as unpainted: a band seen
  end-on is a band nobody sees. The identity of a convex mass is the pattern on it - the ladybird's
  own claim - and the pattern has to run the way the eye does.
- **A FIN'S CHORD SHRINKS WITH ITS REACH; ITS REACH DOES NOT SHIFT WITH ITS CHORD.** Built the
  other way - each ring of the fin stepping forward as it went out - all four came out as a ragged
  red lump at the tail, because every cell was offset from its neighbour on two axes at once.

### THE FLOATING ISLES WERE BUILT, SHIPPED, AND THROWN OUT ON THEME

The first version of the Lost Plateau's sky hung three lenses of the ridge's own rock over the
land - jungle on their backs, vines off their rims, dark keels underneath. They built clean, they
hollowed clean, they passed every contract, and they read as floating islands from every bearing.
Jack: *"I don't think floating islands are on theme in this case. I like the plane and maybe we
can add other elements."*

**A FLOATING ISLAND IS A FANTASY TROPE AND THE LOST PLATEAU IS NOT A FANTASY.** It is a
palaeontology expedition camp on a remote tableland - Conan Doyle, not Skyblock - and the whole
premise of such a place is that it is REAL and merely unreachable. Rock that defies gravity says
"magic realm" and undoes the one thing the land is built on. Nothing about the build was wrong;
the SUBJECT was, and no amount of further craft would have found that.

> **A MEASUREMENT CAN TELL YOU A SKY IS EMPTY. IT CANNOT TELL YOU WHAT BELONGS IN IT.** Everything
> in this file's audit - 0.88% above Y250, one perched object in 34,000 columns, a skyline flat
> from Y211 to Y252 - was true and was the right reason to build something. Which something is a
> question about the FICTION, and the fiction is Jack's.

`isles:` is empty in the config rather than gone from the generator, and
`test_an_isle_is_a_LENS_AND_A_KEEL_even_though_nothing_ships_one_any_more` builds one to keep the
contract exercised. **They would suit Prismworks**, whose own fiction is a crystal that does
exactly this.

### WHAT REPLACED THEM IS THE LAND'S OWN ANIMAL

Four pteranodons on the wing around the biplane - the creatures the camp below came to find and
the machine that got it there, sharing the sky. It is the Lost World's own image and it needed
nothing invented for it: `gen/pterosaur.py` builds a flying one straight off with `perch: False`,
one component, zero strays, at every span from 28 to 80.

**AND THE REUSED-ASSET LINE IS ABOUT THE OBJECT, NOT THE SPECIES.** Jack refused two on the
causeway - *"get rid of the gecko and bat - those are used assets, we want NEW things"* - and both
were creatures lifted out of the lowland into a place with no claim on them. This land already has
a pteranodon roosting on its summit and a nesting colony on its rim; adults on the wing over it is
that story FINISHED. What would have been the repeat is the perched animal again, so none of these
carries a crag and every one is spread 0.84-0.92 against the roosting one's 0.72 - the difference
has to be the ATTITUDE, not only the altitude, and the test asserts both.

**THE BIGGEST THING IN THAT SKY IS NOW AN ANIMAL, WHICH IS THE WHOLE POINT.** The flock runs 68,
40, 28 and 24 blocks of span against the aircraft's 46 - a real azhdarchid out-spans a light
aeroplane - so the size ladder does the job the floating rock was doing badly, and on theme.
`test_the_flock_IS_THE_LAND_S_OWN_ANIMAL_and_none_of_them_is_PERCHED` pins the ladder, the poses
and the absence of a crag.

**And one test stopped testing anything while staying green.** The bank measurement counts how
many distinct courses the design occupies at 0, 7 and 16 degrees; with the flock left in the
picture the birds swamp it and all three read 41. Scoped to the aircraft alone it works again -
the same failure shape as `MenuTest`'s exemption list and the store hall's own vacuous doorway
check, and worth looking for whenever a fixture grows.

### AND THE AEROPLANE MOVED TO THE CARNIVAL END (2026-09-13)

Jack, on the placed park: *"the park complete plane should be moved towards the carnival and not
be in the center of all the dinosaurs."* Both halves are one fault, and it is a COMPOSITION fault
rather than a siting error: at z80358 the machine sat in the middle of a band whose ground carries
the sauropod, the bone bed and the nesting rim, with the flock spread around it - so **the one
thing in that sky that is not an animal read as one more animal in the group.** The two elevations
from the Midway say it in one glance: before, the plane is a small side-on shape among four birds;
after, it is the near, large, unmistakable object and the birds are behind it.

**THE OPEN SKY AT THAT END IS 22 COLUMNS WIDE AND THE AIRCRAFT NEEDED 51, SO THE HEADING HAD TO
CHANGE AND THAT IS WHAT MADE IT BETTER.** Measured off the land's own skyline, the crag's mass runs
to u147 at Y277 and beyond it the land falls to Y219-238 - u148-169, twenty-two columns. Nose east
or west the 51-cell span lies along Z and does not fit; turned, the span lies along X and the
aircraft wants 30 columns of Z. What the turn buys is the view a guest actually gets: they arrive
from the fair walking north, and the full wingspan is now spread across that sightline rather than
pointing away down it. **The config's old note - "facing WEST so it crosses the view of a guest
walking north" - was reasoning about a crossing MOTION and forgot that a crossing aircraft presents
its narrow 28-block length.**

Two numbers keep it honest, both measured over OCCUPIED cells rather than over the bounding box:
the nearest ground under any cell of the aircraft is **47 courses** down (its tail passes east of
the crag's shoulder, not over its peak), and the causeway's own tallest thing in that band - the
Rib Walk's cage at Y228 - is 54 below. It stays inside the land: z80439-80468 against a boundary of
z80469, so `test_it_stays_under_the_BUILD_LIMIT_and_inside_the_LAND` needed no relaxing, which is
the cheaper outcome than moving a design out over the causeway and rewriting the contract for it.

**And the flock did not follow it**, which is the better composition anyway: three pteranodons hold
the sky over the plateau and the smallest - already at [168,150] - is now 11 blocks off the
aeroplane's starboard wing, so the machine is not alone and the land is not emptied. The config's
narrative and two comments were rewritten in the same edit; a design whose prose still describes
where a thing used to be is this file's most-repeated defect.

### The visual audit that came with it, measured against the download corpus

Outside architecture runs 17.3% detail families (slab/stair/wall/fence/pane/trapdoor) and a palette
of 37. Split by what a design IS - because terrain does not take stairs and comparing it against
architecture is comparing the wrong things:

| | cells | palette | detail |
|---|---|---|---|
| Lost Plateau, TERRAIN | 120,300 | 58 | 2.7% |
| Lost Plateau, ARCHITECTURE | 43,613 | 64 | **7.9%** |
| Lost Plateau, SCULPTURE | 5,727 | 11 | 0.0% |
| the Midway, whole | 82,319 | 119 | **8.9%** |

**The palettes are healthy and the detail is half the corpus's**, and the architecture figure is
itself dragged down by the Mine Coaster - 31,197 cells of timber trestle at 4.1%. The actual
BUILDINGS measure 13-36% (Assay and Prize Office 36.5%, Snack Window 35.6%, Works Yard 27.5%,
Midway Row 20.1%). `gen/park.py` was taken from 2.05% to 13.46% at an identical cell count a
session ago; the modules that have not had that pass are where the remaining gap is, and
`smooth_basalt` - 15.4% of `Park Buildings`, with no slab or stair at any price - is the one
material that blocks it outright.

**Still open:** nothing here has been placed in game, and `render3d` has no emission - the bursts'
froglight cores and the isles' lamps draw as cream blocks in every sheet above. Judge form and mass
offline; judge the light in world.

