## The park becomes a place: purpose, packing, and the bugs that were silent (2026-09-01)

Jack looked at the shipped park and gave the verdict the pipeline could not: *"im unclear what the
centyer monument fountain thing is or what purpose it serves"*, *"we dont need a bakery or that
building"*, *"the water rides are mostly not functional or leak water"*, *"park_right ... serves low
function and feels confusing"*, and the line that governs the rest - **"we don't want empty
structures that sit there and are mostly useless"**.

The park went from 81,000 blocks of buildings to ~126,000 blocks of buildings, games, a show, a
railway and a causeway. The more useful half of the session is the defects found on the way, every
one of which passed every check this repo had.

### THE THINGS THAT DID NOTHING, QUIETLY

- **`circuits.pulse` WAS A REPEATER, AND A REPEATER DOES NOT PULSE.** It delays both edges, so a
  held input gave a held output: a lever left on drove the output high for **21 of 24 ticks**
  against a contract promising two. Every casino game runs its button through it, so the house
  paid for as long as a player leaned on the button. It survived because its own test asserted
  `high < 20` out of twenty - **a bound looser than the bug**, which a permanent delay satisfies
  as easily as a pulse. It is a comparator-subtract monostable now.
- **THE MONUMENT'S RISERS SAT ON EVERY TREAD.** The cell tying each spiral step to the last was
  placed one course ABOVE the previous tread - the cell a player standing there occupies. All 39
  steps were unwalkable. Legality, economy, connectivity, the tread-path check and the
  stair-facing check all passed, **because every one asks about BLOCKS and the failure was in the
  air.** Assert headroom, not just treads.
- **A POST RESTING ON A RAIL DRAWS EXACTLY LIKE A POST RESTING ON THE GROUND.** The teacups' six
  canopy posts sat at a radius that put four of them on the loop's own rectangle; the loop is laid
  afterwards, so it overwrote each post's ground cell with rail and left the post in the course
  above. The Ghost Train had it worse - a solid block over **eleven of fifty** track cells, which
  is a suffocation tunnel - and shipped with **zero light sources**, because both lamp calls
  returned False into a variable nobody read.
- **THE LOG FLUME DRAINED 199,959 CELLS TO Y-1908.** The generator self-checked with
  `fluids.carries`, which asks whether the ride PATH is wet and moving. Whether every water cell
  is ENCLOSED is a different question and nothing asked it. `fluids.escapes` and
  `fluids.unenclosed` exist now - and the "count the open faces" audit that preceded them was too
  weak by four orders of magnitude.
- **THE PLAZA'S OBSTACLE LIST SILENCED IT COMPLETELY.** Handed the fifteen buildings standing in
  it, `_plaza` found no legal slot for a bed, a tree, a terrace or a pool, planted NOTHING, and
  reported `trees: 0, beds: 0` while shipping 6,405 cells of bare paving. **A guard strict enough
  to produce silence is indistinguishable from a feature nobody wrote.**
- **`circuits.randomiser` READ `dy` WHERE IT MEANT `dz`** - broken at north and south facings,
  which the casino's own Colour Wheel uses.
- **`_paste` COPIED BLOCK STATES AND NOT SIGN TEXT.** A sign is two things in two halves of a
  litematic; the pasted archways would have shipped blank.
- **A SHOOTING GALLERY WITH ELEVEN TARGET BLOCKS AND ZERO REDSTONE.** A `target` emits a signal
  proportional to accuracy and nothing read it.

### THE PACKER WAS LYING ABOUT CAPACITY, FIVE WAYS

The midway reported NO SITE for its carousel, its swings AND its teacups - every ride in a
fairground - **with the plot 43% used**. Five independent causes:

- **The Big Wheel was parked mid-plot**, casting a 19x77 strip that split the zone into three bands
  none of which was 33 wide. A landmark belongs on an edge.
- **The fine scan started three cells in from the boundary.** A monument pinned to the plot centre
  leaves exactly two 33-deep bands, so every candidate overhung it. Three cells of politeness cost
  three rides.
- **The scan stepped by two, and a stride has a PARITY.** The free band began on an even cell and
  the scan tried only odd ones. **The third time in this file a stride has hidden the answer it
  was searching for.**
- **SPACING WAS COUNTED TWICE** - every reserved box carried it and every candidate added it again,
  so buildings sat four cells apart where two was asked.
- **Candidates were sorted by distance from the CENTRE**, so everything packed inward and the
  leftover was a ring - wide, thin, never square. Sorting by CONTACT with what is already there
  keeps the free space in one piece, and is also what a street looks like.

### A FOOTPRINT IS NOT THE SAME AT EVERY FACING

Siting reserves a square so a turn decided afterwards is safe - which assumes a turn swaps width
for depth and nothing else. The Fortune Wheel's booth grew a roof on one side: 21 wide facing east,
23 facing west. It turned two cells into a dead tree with every check upstream correct. Three
reservation rules were tried and each fixed one zone and broke another. **The fix that worked is
local: the turn TRIES ITSELF and declines when the result collides**, which no future generator can
break. A building keeping its back to the street is a smaller fault than one built through its
neighbour.

### A RESERVED STRIP HAS TO SHRINK EVERYTHING THAT READS THE PLOT

The transit corridor is ten columns down the east of every park plot. Seeding it into `taken` stops
the PACKER and nothing else. Four more fixes:

    the edge branch     slid along an edge it did not own   (Big Wheel and Clock Tower on the rails)
    the cover branch    centred an 88-wide plaza across it  (claims nothing, so nothing objected)
    the streets         clamped avenues to the PLOT         (every zone reached X 97646)
    street furniture    checked `plot.contains`             (a bench on the railway)
    the turn pass       re-placed a sited module into it    (the Mine Head, two cells over)

`_owned_bounds` is the one source now. And **`width` is the FRONTAGE, which on an east-facing
module is Z** - written 88x96 the plaza came out 96 across X, paved ten columns of railway, and
left the carousel on bare void because Z was three short.

### The flow audit, and the gateways that led nowhere

Flooded over the SHIPPED litematics rather than the planned routes: strict floor-only walking
reaches **31%** of standable surface; allowing one jumpable gap reaches **80%** and all 36
attraction doors. The cause was a one-block unmarked gap at X 97639 where two of three zones fail
to meet the transit pad. The furthest attraction is **~436 walking blocks** from the gate.

And the finding that mattered most: **Frontier Arch, Hollow Arch, Frontier Gate and Hollow Gate all
led to nothing at all.** They sit on the north and south plot edges; the railway runs down the east.
`transit.py`'s own docstring had said so and nobody drew the conclusion. The geometry was right -
all four sit on X 97591..97599 facing each other across the gaps - and what was missing was LAND.
`gen/isthmus.py` is that land: a shell rather than a slab, flared at each plot and pinched to a neck
at the midpoint, 41,079 blocks with a sculpture trail, and a flood fill proves the walk end to end.
**Its shape was seeded from Python's `hash()`, which is salted per process** - every rebuild would
have produced a different, untested causeway.

### What replaced what

The rule applied throughout: **a structure that answers "what can a player DO here?" with "look at
it" is either given a function or replaced.**

| out | in | because |
|---|---|---|
| Guest Services | Hall of Fame | an information counter is a fitting nobody can use |
| The Arcade (a pavilion), Hoopla | plinko, high striker, prize counter | the old games were watch-a-randomiser; these take a PLAYER INPUT |
| The Riverboat | Gold Sluice | a hull you walk onto, against a launder you drop items into that rings a bell |
| Shooting Gallery | Shooting Range | eleven targets nothing read, against one that scores by accuracy |
| The Graveyard, The Chapel | Ghost Train and The Plummet fit | the hollow had two things to look at and needed two things to ride |
| the bakery | two shops with real interiors | `_deal` hands out `options[0], options[1]` before shuffling, so the head of the table IS the two-shop street |

**The eight arcade machines are the first games here where what the player does decides the
outcome.** `target` gives an analog signal by accuracy; an `item_frame` is an eight-position dial a
comparator reads; a `lectern` reports its page; a weighted plate is a scale; a `sculk_sensor` hears
you. None of that vocabulary had been used before.

