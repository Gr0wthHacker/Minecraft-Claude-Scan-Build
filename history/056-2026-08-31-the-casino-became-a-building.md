## The casino became a BUILDING (2026-08-31)

Jack, on the first placed version: *"its not clear what any of the games are, how to play them...
we need signs... lets put them into proper rooms, and design the entire casino around it... this is
just random platforms of shit."* All correct. 29 open bays scattered over a void plot, nothing
saying what any of them was.

**30 designs, 17,138 blocks, 37 signs, 0 overlap and 0 placement problems.**

### THIS PROJECT HAD NEVER PLACED A SIGN

The writer emits tile entities and the pipeline shifts them when a design is padded - both have
worked for a year - and `Canvas` had no way to make one, so nothing above that layer could. A room
with no sign is a room nobody can be told the rules in, which is exactly the complaint.

`Canvas.sign_text` and `World.sign` close it. Three things they had to get right:

- **26.x nests the lines under `front_text`/`back_text` as a `messages` list of JSON strings, and
  there are ALWAYS FOUR.** A sign with two lines still stores four; a shorter list is a sign the
  game refuses to load, so the padding is done in the helper rather than at every caller.
- **The BLOCK and the TEXT are separate things** - a palette entry and a tile entity, in different
  halves of the file - so `put` places the sign and `sign` says what it reads.
- **Text is only carried across if the BLOCK survived.** A design is remaining work and cells get
  deferred or trimmed, so a sign's text can outlive its sign, and a tile entity with no block is a
  corrupt region rather than a harmless leftover.

**FIFTEEN CHARACTERS IS THE LINE.** "lamps show your roll" is twenty and clips mid-word; `_copy`
asserts the width, because the failure only appears in a screenshot after the build is placed.

**The odds are ON the sign** - "1 in 3", "pays 1 prize". A house that will not print its odds is a
house that does not know them, and `RNG_MIXES` holds only the two item mixes with a measured
uniform result.

### A GAME IS A ROOM, NOT A PLATFORM

Four walls, one doorway, a ceiling, a skirting, a cornice, corner pilasters, two lanterns and two
signs. Deliberately ordinary: **what makes voxels read as architecture is regularity and openings**,
which the void tower settled when a jagged ruin was rejected on sight and a plain regular one with a
door and window slits worked immediately.

- **The doorway is left EMPTY by the wall loop, never punched afterwards.** Building the ring and
  cutting a hole repaints cells that already exist - the void tower's crenellations shipped as a
  plain drum for exactly this reason and nothing about the code looked wrong.
- **A CASINO IS DARK WITH BRIGHT TRIM, NOT A WHITE BOX.** Built white-field / grey-wall /
  grey-ceiling it rendered as a bathroom. The field is `black_wool` (21), the border and cornice
  `white_wool` (236), the walls `smooth_stone` (159), the ceiling and pilasters `deepslate_bricks`
  (71) - the 215-point cheap value range this project measured ACROSS families after three separate
  notes here wrongly concluded, from searching WITHIN one family, that this economy has none.
- **Stairs as skirting and cornice.** The corpus says we place stairs at a seventh of the rate
  outside builders do; this is the first generator to use them as trim rather than as a staircase.

### The hall, and why it is built LAST but placed FIRST

`kind: hall` - an 88x88 floor, a perimeter wall with plinth, string course and parapet, a 3-wide
gateway, twelve lanterns and the casino's name over the door. 9,874 blocks.

- **NO ROOF, deliberately.** Every room has its own ceiling, and an 88x88 lid is seven thousand
  blocks nobody inside a room can see. What reads from outside is the WALL and the GATEWAY.
- **It is the last module in the theme, and that order is load-bearing.** `emit` chains `defer_to`
  down the list, so a later module yields any cell an earlier one claimed. Built first, the hall's
  floor would take every room's floor and the rooms would stop being rooms. Built last it lays only
  the ground BETWEEN them, which is what a hall is.
- **A COVERING MODULE IS NOT COMPETING FOR SPACE, IT IS THE SPACE.** Asked to find a free bay it
  correctly reported NO SITE, because by then the plane is full of rooms. `anchor: cover` centres it
  on the plot and claims nothing.
- It is also the fix for *nothing to place against*: the plot is void, and that is why every design
  reported free-floating cells.

### Four faults, all caught by checks that already existed

- **Carpet laid IN the floor course had nothing under it** - six floating carpets per room, rule 9,
  and the audit caught it exactly as designed. The carpet goes ON the floor.
- **A REDSTONE LAMP IS A DARK BLOCK UNTIL SOMETHING POWERS IT.** Two per room, wired to nothing;
  the circuit inspection said so on the first run. Lanterns hung from the ceiling need no signal
  and cost an iron ingot and a torch.
- **The spread report read `at` as a minimum corner.** A game runs from at-6 to at+9 and the hall
  from at-87 to at, so the report claimed the casino spilled 80 blocks past the plot and used 113%
  of it while every module was inside. A boundary report that cries wolf is one nobody reads.
- **Three of my own tests measured the MODEL BOX rather than the room.** The box is 16x10 because
  the machine and payout run out under the floor; the room is 10x6. A ceiling test sampling the
  box's centre column, and a wall test checking the box's far edge, both failed on a correct build.

### THE HALL WAS DRAWN OVER EVERY ROOM, AND ALL THIRTY DESIGNS REPORTED `overlap 0`

Jack, on the placed casino: *"lots of empty boxes, and then things arent shown right."* The cause
was one line in `planner.emit`:

    if prev: cfg["finish"]["defer_to"] = [f"out/{prev}.litematic"]      # the PREVIOUS one only

Chained one-to-one that is correct for a line of modules that touch their neighbour, and wrong for
a hall that touches all of them. The hall deferred to `House Bank 3` alone and laid its floor
across all eighteen room floors - **60 cells each, the whole floor of every room** - so in game two
placements fought over one cell.

**NOTHING CAUGHT IT, AND THE REASON GENERALISES.** `finish.verify_against` audits a design against
the CAPTURE, and the capture does not contain the other designs. Every module honestly reported
`overlap 0` against the world while colliding with its neighbours. Cross-design overlap is a
DIFFERENT question and needs its own check; `test_no_two_modules_of_a_plan_share_a_cell` is it, and
it compares every pair of a plan's designs in world coordinates. The measured tell was in the
material counts all along: the union held **64 black_wool where eighteen room floors needed 558**.

Three more things came out of the same look:

- **SEVEN THOUSAND IDENTICAL CELLS IS NOT A FLOOR, IT IS A SLAB.** The hall was 68% smooth_stone
  and read exactly like the platforms it replaced. A world-aligned grid of dark lines every eight,
  a stone/smooth-stone checker between them and a red aisle on the entrance axis takes the
  dominant block to 43% and costs nothing - all four materials are cheap.
- **A GAME ROOM IS A SHOPFRONT, NOT A CELL.** With a two-wide door the floor was eighteen sealed
  grey cubes: you could not tell one from another or see a game being played. The opening is four
  wide now, and the wall survives as a frame and a lintel - which is what carries the sign.
- **`defer_to` IS APPLIED AFTER THE GENERATOR RUNS.** An aisle drawn as carpet at floor+1 shipped
  ten floating cells: at build time the floor was there, and by the time the design was written
  the cells yielded to a room were gone and the carpet was standing on air. The aisle is a floor
  MATERIAL now - a cell in the floor course cannot outlive its support, because it is the support.

### FORTY-SIX PIECES, AND EVERY DESIGN SAID 0 PROBLEMS

Jack: *"lots of things floating."* A 6-connected component count over the whole plan plus the
island found **one building of 15,710 cells and 45 fragments hanging in open air.** Two causes,
neither of them visible to a per-design check:

- **THE THEME DECLARED A MEZZANINE AND NOTHING EVER BUILT ONE.** `floors: [{Gaming Floor, +0},
  {Mezzanine, +12}]` lifted eleven modules eleven blocks and left them there - no deck, no
  balustrade, no flight. **A floor entry is a LIFT, and a lift is only legitimate once something
  carries what is lifted.** A gallery is a fine thing to build and it is a BUILD; until it exists
  everything stands on the ground. `test_the_whole_plan_is_one_connected_piece` and a check on
  `THEMES` both pin it.
- **A WALL SIGN GOES IN THE CELL IN FRONT OF A WALL.** The rules sign was placed in the middle of
  each room, attached to nothing - eighteen single-cell strays, one per game - and the door sign
  was written INSIDE the wall plane, overwriting the lintel it was meant to hang from. `facing` is
  the direction the text LOOKS, which is away from the block it is fixed to. The door sign is on
  the outside face now, where a shop sign goes; the rules are on the back wall facing whoever has
  walked in.

**A DESIGN IS JUDGED IN CONTEXT, AND THE CONTEXT FOR A PLAN IS THE REST OF THE PLAN.** Rule 2 has
said "verify in context, never in isolation" since the first island, and `verify_against` has only
ever meant *against the capture*. For a thirty-module plan that is the wrong context twice over -
it misses cross-design collisions and it misses floating work. Both now have their own test, and
both found real defects the moment they were written.

Final state: **one component, 16,028 cells, 0 clashes, 0 placement problems**, dominant block 43%.

**Still open:** the interior has been verified by audit, simulation, cross-design overlap,
connectivity and block counts, not by eye -
`tools/look.py` cannot render these because the casino sidecar records `facing` as a word and it
wants a vector. Place one room and look at it before building thirty.

### The casino ships as FOUR LAYERS, not thirty fragments (2026-08-31)

Jack, after three rounds of fixes: *"its still showing basically empty floors with holes in it for
redstone etc, and nothing above it, can we instead just make this simple and split this into steps,
e.g. floor, redstone, design."* He is right, and the diagnosis is his: **a design that DEFERS is
incomplete on its own.**

`finish.defer_to` settles which design owns a shared cell. That is exactly right for ownership and
exactly wrong for looking at the result - every module becomes a fragment with holes in it where a
neighbour won, and thirty of them loaded together are thirty overlapping boxes each missing pieces.
"Empty floors with holes for redstone and nothing above it" is a precise description of the hall
on its own.

    python -m mcbuild layers casino --floor 203 --ship

    Casino 1 Floor      7,640    the walking surface
    Casino 2 Machines   2,951    everything under it: pits, wire, droppers
    Casino 3 Walls      4,925    everything over it: rooms, ceilings, the perimeter
    Casino 4 Fittings     368    signs, lanterns, buttons, carpet

**LAYERS CANNOT COLLIDE, SO NOTHING DEFERS.** `_which(name, y, floor_y)` is a function of the CELL
- what it is and where it sits - so every cell lands in exactly one layer by construction. There
is no ownership question left to settle and no design is missing anything. Each loads on its own
and the four together are the whole casino with nothing hidden. Verified as a partition rather than
asserted: 0 shared cells, 0 lost, 0 invented, **0 block-state changes** (a stair's facing and a
sign's facing are decisions, and a slice that dropped `Properties` would look identical in every
render here and be wrong in game).

Two rules inside it:

- **A MACHINE STAYS WHOLE WHEREVER IT SITS.** Material wins over height: a mechanism half under the
  floor and half above it is one machine, and splitting it by height gives two layers neither of
  which works. A lamp above the floor is a display and goes to Fittings; the wire that drives it
  does not.
- **A SIGN'S TEXT FOLLOWS ITS BLOCK.** Left in another layer it would be a tile entity with no
  block, which is a corrupt region rather than a lost line. All 37 land in Fittings.

It also gives the build ORDER that matches how you would actually build it: stand the floor, hang
the machines under it, raise the walls, fit it out. `sync.yaml` tracks the four, so `/cscan place`
places four complete designs rather than thirty fragments.

**The thirty module designs are kept**, because they are what the plan, the circuit verification
and the cross-design checks are written against. They are simply no longer what you place.

### The games were two games wearing four names (2026-08-31)

Jack: *"audit all the games and make sure theyr unique, different."* Measured cell-for-cell, they
were not:

| | identical machine cells |
|---|---|
| High Roller vs Coin Toss | **98.7%** |
| One In Three vs Even Money | **94.6%** |

**`threshold` PAYS ON A MAXIMUM, AND A MAXIMUM IS THE SAME GAME WHATEVER NUMBER YOU PUT IN IT.**
Changing `outcomes` from 3 to 2 changes the odds and nothing else; shipping that under a different
name over a different door is what made the floor read as one room eighteen times. Both odds
variants are deleted.

**MEASURE THE MACHINE, NOT THE ROOM.** The first comparison ran over whole designs and reported
everything as 94-99% alike including games that are genuinely different - because a room is ~330
cells and a machine ~150, so the metric was measuring the walls. Sliced to the mechanism the four
survivors sit at 68-89%, and the shared part is exactly right: they all roll dice. What differs is
the resolution.

Two new mechanics, each a new primitive verified by simulation before any of it was built:

- **`circuits.window(low, high)` - an exact-value gate**, and the first mechanic here that is not
  a maximum. An AND-NOT: two perpendicular taps off one dust line, `low-1` and `high-1` along, into
  a comparator in SUBTRACT mode. 15 - 0 = 15 when only the low tap fired, 15 - 15 = 0 when both
  did. `Lucky Two` pays on exactly 2 out of {1,2,4} - the middle wins and the top LOSES, which no
  threshold can express.
- **`circuits.duel()` - two rolls compared.** A comparator in COMPARE mode passes its back signal
  when back >= side, so out of {1,2,4} there are nine equally likely pairs and six have A >= B:
  **2 in 3, countable**, which is this file's bar for shipping a game at all.

Three faults inside them, each of which built cleanly and simulated wrong:

- **A SIDE INPUT IS READ AS A LEVEL, so it must arrive at FULL STRENGTH.** The window's HIGH tap
  was routed to the gate as plain dust, decayed on the way, and the subtract gave 15 - 13 = **2**:
  the gate "passed" a level it exists to block, quietly and by two. A repeater at the side delivers
  a clean 15.
- **The first window put both taps on one perpendicular** and the side input landed TWO cells from
  the comparator, so it never arrived and the window was a threshold with extra parts.
- **THE DUEL PAID ON ALL NINE COMBINATIONS.** The house's randomiser was placed on its own lane and
  `_link`ed to the comparator's side - and **an analog value cannot travel**, so the side read 0
  and `A >= 0` is true for every A. Both rolls are produced ADJACENT to the gate now, and the
  geometry is derived from that rather than chosen: a randomiser's comparator sits at `pos + dx`
  and fires along `facing`, so the house goes two cells back along the side's own line.

**A PLAYER CANNOT SEE A CIRCUIT.** Four verified mechanics in four identical grey rooms are four
identical rooms, so `KIND_ACCENT` gives each one its border, carpet and pilasters: High Roller
yellow, One In Three red, Lucky Two lime, Duel light blue. That is what tells them apart from the
aisle, which is the distance most of them are read from.

The lineup is now **18 games over 4 mechanics** - 5 High Roller, 5 One In Three, 4 Lucky Two,
4 Duel - every contract asserted by simulation, every one stating its odds on its own sign.

### The Colour Wheel, and what a redstone casino CANNOT be (2026-08-31)

Jack: *"majority of the games look like theyre identical, what about things like roulette, or other
games, blackjack."* The first half is right for a reason colour could not fix: a bar, a threshold,
a window and a comparator all read as **a button in a grey box**. Four verified mechanics in four
identical booths are four identical rooms.

**`wheel` is the first game here with a different SHAPE as well as a different circuit** - a sunken
round bowl with a rail, read from above, no walls at all - and the first that is a DECODER: one
roll, three outputs, exactly one live. Red/green/black, 1 in 3, `test_the_wheel_lights_exactly_one_
pocket_in_every_orientation` asserts it at all four facings.

Four faults inside it, each of which built cleanly and simulated wrong:

- **A SPUR OFF THE SOURCE DUST DOES NOT WORK.** Three branches off the comparator's output cell
  left every pocket dark, because dust adjacent to that cell is already a level down and every gate
  is off by one. A hopper has four horizontal sides; three comparators read the container itself.
- **DUST BELOW A LAMP DOES NOT LIGHT IT.** Every gate fired correctly and not one lamp came on. A
  repeater into a solid block lights a lamp above it; simpler still, sinking the bowl to the
  machine's own course puts every pocket in the cell NEXT to its gate, so there is no journey.
- **DECORATION LAID BEFORE STRUCTURE EATS STRUCTURE.** The first pocket's colour ring was painted
  into cells the third gate had not reached, `_lay` skipped them as occupied, and the level-4 gate
  shipped with its subtract comparator replaced by red wool - so a roll of 4 lit the level-1
  pocket. Every gate is built before any pocket now.
- **ADJACENT DUST IS ONE NETWORK: CLEARANCE, NOT JUST NO OVERLAP.** The gate arrangement was
  SEARCHED, and the first search demanded only that no two gates share a cell. The winner put gate
  1's output one block from gate 4's dust; a roll of 4 pushed 15 into the level-1 pocket. The
  search requires a real gap now and the test re-derives it, so a change to `window`'s footprint
  fails here rather than in game.

**And the biggest module must be sited FIRST.** `bays` packs in list order, so the booths filled the
grid and the 23x21 wheel reported NO SITE three times. A module is not unsiteable because it is
late.

#### What cannot be built, and why it is not a matter of effort

- **BLACKJACK IS OUT OF REACH.** It needs card identity, a running total, a dealer rule and a hit/
  stand decision - state that has to be held and compared across turns. Redstone can do it with
  enough hardware, but nothing in `circuits.py` could verify it and this file's rule is that a game
  ships only with a contract asserted by simulation. Building it unverified is how `chase` and
  `vault` happened.
- **A 37-POCKET ROULETTE IS OUT OF REACH FOR THE ODDS, NOT THE WIRING.** `RNG_MIXES` holds only the
  two item mixes whose distribution minecraft.wiki gives as uniform. A wheel with more pockets
  would be a wheel whose odds we are inventing, and **a house that cannot state its odds does not
  know them**. Three pockets is what three measured outcomes buys - so it is a COLOUR bet, which is
  a real roulette bet at odds we can print on the sign.
- Two rolls would give nine uniform outcomes and a proper wheel; it needs nine AND gates and is a
  genuine piece of work rather than a tweak. That is the honest next step if a bigger wheel matters.

The lineup is **14 games over 5 mechanics** - 3 High Roller, 3 One In Three, 3 Lucky Two, 3 Duel,
2 Colour Wheel - every contract asserted by simulation, every one stating its odds on its own sign.

### `defer_to` is gone from the casino (2026-08-31)

Jack: *"can we stop with the defer crap so i can actually see everything in totality in the place
simulation."* Yes, and it should have gone two rounds earlier.

**`defer_to` RESOLVES A SHARED CELL BY DELETING IT FROM THE LOSER.** That is correct for cell
ownership and it means every module ships as a fragment with holes in it - so looking at the casino
meant loading a pile of overlapping designs each missing pieces. Three separate rounds of confusion
came out of that and none of them was ever about the casino.

    python -m mcbuild layers casino --floor 203 --ship

    Casino Complete   14,874    the whole thing, one design - this is what you place and look at
    Casino 1 Floor     7,636    the build steps, if you want to place it in stages
    Casino 2 Machines  2,988
    Casino 3 Walls     4,019
    Casino 4 Fittings    231

- **The modules are INTERMEDIATE artifacts now.** Each is generated WHOLE, overlaps and all, and no
  casino config carries a `defer_to` - `test_no_module_config_defers_to_another` keeps it that way,
  because deferring is the obvious way to stop two designs claiming a cell and is easy to
  reintroduce by accident.
- **THE PRECEDENCE LIVES IN ONE PLACE AND IS REPORTED.** `layers.slice_plan` applies first-writer-
  wins in plan order - the same precedence `defer_to` used to enforce - and prints the count:
  **923 contested cells**, which is the hall's floor under the rooms. Silently applied it is the
  same trap; printed, it is a number you can check.
- `Casino Complete` is verified to equal the union of the four layers exactly: same cells, same
  block states, and one connected component with the island.

**Two tests changed with the decision**, which is the rule this file keeps relearning: one asserted
that no two modules share a cell, and the other compared the layers against a raw union of the
modules. Both were true only because of deferring. They now assert that the overlap EXISTS, that it
is resolved deterministically, and that the resolved result is exactly the design you place - and
the first of them fails if anything quietly starts deferring again.

`sync.yaml` tracks **one** design, so `/cscan place` puts down the whole casino with nothing hidden.
The layers stay in the folder and can be placed by name when it is time to build in stages.

### "A lot of this feels useless" - the purpose audit (2026-08-31)

Jack, on the placed casino: *"what are the random dispensers and yellow wool etc."* Both were real,
and one of them was a module that had never worked.

**THE PRIZE WALL WAS DEAD, AND IT WAS THE ONE MODULE WITH NO SIMULATED CONTRACT.** Every dispenser
had a `redstone_block` stuck permanently to its back, so all twenty across four walls were LIVE AT
REST. A dispenser fires on a RISING EDGE: powered for ever means it dispensed once when the chunk
loaded and never again - and the buttons were mounted a cell out in front, diagonal from the
dispenser, touching nothing. It is driven by its button now (a button on a solid block strongly
powers it, and a block above a dispenser fires it), verified at rest and per button.

Every game has had a contract asserted by simulation since `chase` and `vault` were cut for
precisely this; the furniture did not, and the gap is exactly where the dead module was.

**THE YELLOW WOOL WAS TWO DIFFERENT THINGS, one fine and one not.** Button pads and the High Roller
accent are deliberate. The stray **three pink and three blue** wool in the whole casino were the
bar's lamp CAPS, cycling an eight-colour board list - on a four-lamp bar that is four arbitrary
colours, which reads as confetti rather than as a scale. The caps are the kind's own accent now,
one colour per instrument.

**A FLOOR BUTTON WAS STANDING ON WIRE.** The wheel's link ran from the button itself, so `connect`
descended through the cell underneath and turned its pad into redstone dust - not a placement the
game allows, invisible in every render, and the audit passed it. The wire starts one cell further
out and the button powers it from the side.

`test_every_material_in_the_casino_has_a_purpose` closes the palette: 28 materials, every one on a
stated list, and a new block that nothing explains fails the suite.

**And a correction worth keeping, because it was mine.** Counting the wheel's materials I wrote
`cnt[name] = k` instead of `+=`, so two palette entries of the same block with different facings
overwrote each other - the wheel appeared to have ONE comparator where it has six, and I nearly
went hunting a bug that did not exist. **A block is a NAME PLUS ITS STATE, and any tally that keys
on the name alone must accumulate.**

**Not fixed, and stated rather than quietly left:** the whole casino carries **14 stubs of dead
dust and 3 repeaters reading nothing** - one or two cells apiece in `double_or_none`, `lucky_number`
and `duel`, left where a link and a module's own `in` cell both wrote. Every contract still passes,
so they are leftovers rather than faults; they are 20-odd cells out of 14,874 and worth a pass of
their own, not a rushed one.

