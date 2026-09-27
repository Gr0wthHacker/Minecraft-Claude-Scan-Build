## The Helter Skelter: the Midway's third ride, and the four machines nobody had placed (2026-09-03)

Jack, standing in the lot: *"theres a strip here before the prism area that has these buildings and
this empty plot, i think we can do more with this area thats more impactful to the player, and
cooler."*

**THE STRIP IS MIDWAY COLUMN C'S REAR AND IT WAS THE EMPTIEST GROUND OF ITS SIZE IN THE PARK.**
Measured off `out/Park Complete.litematic` before anything was drawn - V100-153 x U345-384, with
streets on all four sides:

| | |
|---|---|
| columns | 2,160 |
| blocks per column | **0.09** - 1,953 of 2,160 surface cells bare moss |
| standing three courses tall | **0.9%** (twenty columns, all of them lamp masts) |
| light sources | **13 lanterns**, in the whole thing |
| tallest cell | **Y208**, against Y223 for the Skill Arcade beside it and Y276 for the wheel |

Mining Square - the lot Jack had replaced in the Frontier for being a car park - measured **1.4**
blocks per column. This was fifteen times emptier, and a hole in the skyline as well as on the
ground. `PARK_GRID_PLAN.md`'s own lot table had already said so twice and nobody had read it: lot
10's programme stops at V99 and lot 15 is listed *spare*.

### AND THE TWO BUILDINGS IN FRONT OF IT WERE EMPTY SHELLS

This is the Frontier's own recorded failure, in the Midway, eight days later. Four machines were
built, circuit-simulated, sitting in `out/` and **absent from the shipped park**:

    PF Game Target Wall  172   PF Game The Double  560
    PF Game The Mark     389   PF Game Prize Point 197     = 1,318 blocks

...while the whole land carried **four buttons across 170 columns**. A design that is built and
unplaced is indistinguishable from one nobody wrote, and the only thing that decides it is a name
in `park_place.EXTRAS_READY`. All four are in it now.

### What a RIDE can be here, which is the constraint the design turns on

A ride in this park can only be a **rail circuit**, a **bubble column** or a **walk-through**;
anything else is a sculpture with a queue, and this repo has retired eight of those. So:

    UP    a 3x3 soul-sand bubble column inside the drum, 30 courses
    DOWN  2.75 turns of BLUE ICE helix wound round the outside

**THE DESCENT IS DRY ON PURPOSE.** A helical open water chute is the shape that drained 199,959
cells to Y-1908 the one time this repo built one, and `fluids.escapes` exists because of it. Blue
ice carries a rider down a graded ramp with no fluid at all, and its worst case is a walkable
spiral ramp - which is still a helter-skelter. All the water in the design is ONE sealed vertical
shaft: **0 escapes, 0 unenclosed**, verified against the generator's own recorded envelope.

**AND IT IS BOARDED FROM A POOL, WHICH IS THE ONLY LEAK-FREE WAY INTO A WATER COLUMN.** A doorway
into the side of one at the water's own level is a hole in the side of one. There is no doorway:
the trough IS the bottom two courses of the same body, kerbed all round, and a rider steps down off
a boarding deck into it.

**THE TWO NUMBERS THAT WERE NOT FREE:**

- **The axis is V142 because of the ground layer's lamps.** Three mast lines stand at U345, U363
  and U382 and their arms reach four courses into this lot on both promenade verges. At V141 the
  chute's outer wall reaches (V133, U363) and takes one; at V142 it clears them. They are in
  `blocked` as well, so wanting one RAISES rather than shipping as an overlap no render can show.
- **`turns` must be a quarter short of a whole one.** The head is on the drum's -V face, so only
  0.75, 1.75, 2.75... land the foot pointing +U - the opposite side of the tower from the queue.
  `PARK_MIDWAY.md`: *"The exit cannot feed into waiting guests."* A ride whose run-out is a
  function of wherever the arithmetic happened to land is a ride whose exit walks into its queue.

### Nine things that shipped a clean audit and a wrong build

Every one of these passed `problems: 0`, `overlap 0`, a correct BOM and a plausible render.

- **THE DRUM HAD NO DOOR.** Thirty courses of shell, a bubble lift, a helix wrapped round it, and
  no way out of the top onto the chute - a rider carried to the top of a tower with nowhere to go.
  Nothing about a sealed drum looks wrong from outside, and the only check that finds it is a walk.
- **A SPIRAL DRAWN IN THE MASS'S OWN TWO COLOURS IS NOT A SPIRAL.** The first build gave the drum
  eight broad red bands and eight white ones and wrapped a white-walled chute round it. Every
  bearing read as lumps of foam stuck to a barber's pole, because the one element that has to be
  legible from across the park was the same value as the thing behind it. The tower is
  `white_wool` with a narrow `red_wool` pinstripe now and the helix carries the red, with
  `polished_blackstone_bricks` under it - 45 against 236, the deepest cheap step this economy has -
  drawing the ramp's underside as one continuous shadow line.
- **A HELIX IS NOT 6-CONNECTED TO ITSELF.** Consecutive cells along it sit one cell apart
  horizontally AND one course apart vertically, which is a diagonal neighbour - the rule that once
  broke a pair of ear tips off a cat. The course under the ice is what joins them.
- **`Canvas.get_name` IS NAMESPACED.** `"minecraft:stone"` against a bare palette entry matches
  NOTHING, so the yard's lighting loop silently placed zero lamps and reported a count of eight
  that all came from the forecourt. A membership test that can only ever be false is invisible.
- **A SIGN ON THE ONE COLUMN OF A WALL THAT HAS AN OPENING IN IT.** The top board hung on the cell
  over the doorway and `_Lot.sign` refused it in silence - four of an earlier park's seven building
  kinds shipped exactly this. The count is what is asserted, because a wall sign floating in air
  draws exactly like one on a wall.
- **BENCHES ON GROUND THE WALK NEVER PAVED.** The forecourt's beds sat two columns clear of the
  walk's border and the seats went in the gap - twelve cells of free-floating stair, caught by the
  buildability line and by nothing else.
- **THE HAND-OFF BETWEEN THE HELIX AND THE RUN-OUT WAS A LITERAL IN TWO PLACES**, and they
  disagreed by two courses. The join was walkable only because the run-out is built last and
  overwrites what the helix left: a ride that works by accident. It is one parameter now.
- **A COMPOSITE'S Y IS NOBODY'S CONSTANT.** The test file typed 190 for `Park Complete`'s origin;
  it is 94, because another stream put a design under Prismworks. Thirteen courses of empty sky
  read as the world, the whole lot reported as disconnected, and `tests/test_park_entrance.py`
  already records the identical failure. It is read from the sidecar.
- **AND THE COMPOSITE CONTAINS THE DESIGN.** The day this went into `EXTRAS_READY`, a walk test
  over `Park Complete` would pass on the SHIPPED copy however broken the generator became. The
  fixture takes from the park only what the park actually owns in these columns - the lawn a course
  below, the promenade, and the masts `blocked` names - and the design under test supplies the
  rest. **Fifth time this repo has recorded the self-reference trap.**

### A LOT STANDING ONE COURSE ABOVE THE STREET IS DIAGONAL TO IT

The first connectivity test demanded that the design and the park be one 6-connected solid and
reported 3,219 of 3,953 cells. That is not a fault: every building lot in this park paves at Y203
while the streets pave at Y202, so a lot and the street beside it are diagonal by construction -
correct architecture and disconnected arithmetic. `tests/test_park_entrance.py` already allows for
it by name. **The right question is a WALK**, and what is asserted now is that from the back
promenade a guest reaches the forecourt walk, the queue, the boarding deck and the exit apron.

### What it moved

**5,057 blocks, 0 problems, 0 overlap in context, 0 clashes with any other module, 6 expensive**
(the run-out's hay-bale buffer, declared).

    blocks per column   0.09  ->  2.43
    3+ courses tall     0.9%  ->  24.8%
    tallest             Y208  ->  Y249   (clear of the Arcade's Y223, well under the wheel's Y276)
    the Midway's rides  2     ->  3

`tests/test_helter.py` (13) pins the contract by SIMULATION rather than by eye: the lift sealed,
every water cell a SOURCE over unbroken soul sand, a walk from the queue to the boarding deck in
context, **100% of the chute walkable from the top**, the discharge opposite the queue, no cell on
ground the park owns, the promenade untouched, the value ladder measured, and every sign placed.

### Still open

- **Nothing has been placed in game.** All of it is `render3d`, which draws with the same colour DB
  the palette picker optimises against - judge form and mass here, palette in world. In particular
  the blue channel is only visible from above and obliquely, which is what a real helter-skelter's
  slide does, but it has not been walked.
- **The rear lot is 75% open ground still.** That is deliberate - a fully paved lot is a car park,
  and this park has replaced one for being one - but whether the two yards want more than a queue
  and an apron is a decision rather than a defect.
- **`tests/test_park_games.py::test_no_shipped_game_takes_a_cell_the_park_already_owns` fails on
  `PF Game Ascent Signal`**, which is PRE-EXISTING and belongs to Prismworks v2: its building is
  `PF Prism Ascent`, one of the four modules removed for the Prism Well, so the game is orphaned
  and now clashes with the `PF Prism Downs` terrain that replaced it. Not this pass's to fix, and
  worth fixing before somebody places it.

