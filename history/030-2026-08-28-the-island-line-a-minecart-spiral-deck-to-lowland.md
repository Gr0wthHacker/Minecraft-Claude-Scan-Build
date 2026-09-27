## The Island Line: a minecart spiral, deck to lowland (2026-08-28)

`configs/rail_spiral.yaml`, `mcbuild/gen/railspiral.py` - **3,300 blocks, 673 track cells, 0
problems, 0 overlap, one component, all cheap-or-ok, 1 dig cell.** Jack: delete the connecting
train tracks, run a spiral all the way down to the lowlands that can also return, and use MORE
POWERED RAILS THAN NORMAL ONES because of iron costs.

### The iron premise is right and the reason is inverted

    rail          6 iron -> 16 rails    0.375 iron each      iron_ingot  90 in store
    powered_rail  6 gold ->  6 rails    1.0   gold each      gold       ~62, and FARMABLE

A powered rail is ~7x a normal one in ingots, so the obvious reading is that powered rail is the
expensive one - which is what I told Jack first, and it was wrong about this server. Gold is easy
here and iron is not, so **the cheap rail is the gold one**. Lay powered rail everywhere and spend
iron only where the game refuses.

**IT REFUSES AT CORNERS, and that is the fact the whole design turns on.** Off `blocks.json`
rather than off memory:

    powered_rail  shape = north_south, east_west, ascending_{n,s,e,w}
    rail          shape = ...those six, PLUS south_east, south_west, north_west, north_east

A POWERED RAIL CANNOT CURVE. So every direction change is iron, and **the plan shape of the spiral
becomes an iron decision rather than an aesthetic one**. At r=30 a square lap turns 4 times; a
rasterised circle turns 60. Round is fifteen times the iron - more than is in store. Hence a square
helix: four straight flights a lap with a landing at each corner, which is the void tower's rule
again (regularity and openings, not curves).

The shipped line is **11 corner rails, ~4 iron**. The whole railway's iron cost is four ingots.

### The first radius sweep asked the wrong question, and Jack caught the result

I scored whether the whole RING was clear at each course, concluded r=12 was the only workable
radius and everything wider was 105-152 courses blocked. Jack: *"this doesnt make sense, it should
be a much wider circle than the small staircase, these are separate things."*

He was right and the sweep was what was wrong. **A helix occupies ONE CELL PER COURSE, not the
ring** - a blocked ring only means the helix must arrive at a different PHASE. That is the same
start-angle sweep `Lowland Stair` already documents, and I did not run it. Swept over centre,
radius and phase together, wide radii are fine: r=30 at (-24206, 30014) threads the whole descent
and stands **15 clear of the stair's outer edge** instead of 3.

Wider is not better past that, and both limits are measured:

| r | turns | ride | under island | to the deck rail head |
|---|---|---|---|---|
| 12 | 6.3 | 76s | 70% | 28 - and 3 from the stair: one tangled column |
| **30** | **2.8** | **~84s** | **70%** | **43** |
| 36 | 3.1 | 113s | **42%** | **85** |

At r=36 most of the ride is a viaduct in open sky rather than one threading the island's underside,
and the boarding platform ends up 85 blocks from the deck.

### Five things that shipped a clean audit and a broken railway

Every one of these passed `problems: 0`, `overlap 0` and a correct BOM. The audit can only see that
a design is one connected solid; it has no idea what a rail is *for*.

- **NEVER DESCEND INTO A CORNER.** A curve has no ascending shape either, so a corner and both its
  neighbours must share one height - drop into one and the game re-derives the turn as a slope, the
  turn is lost and the line dead-ends. Invisible in the model, because `shape` is DERIVED (it is
  not in `work.INTENTIONAL`, exactly as a stair's is not). The grade skips the cell before a corner
  as well as the corner itself.
- **AN UNPOWERED POWERED_RAIL IS A BRAKE**, so every one has to carry signal - a `redstone_block`
  in the bed every 8 cells. And the runs are counted **between corners**, because a normal rail
  does not propagate the chain: a flat spacing leaves a dead rail past every turn, and a dead rail
  is a cart that stops in mid-air a hundred blocks up.
- **A TRACK CELL IS NOT OPTIONAL.** The first build let two track cells yield to other designs and
  shipped 0 problems, 0 overlap and **three components** - the audit caught it only because a
  broken line happens also to be a broken solid. Structural cells are now fatal-or-claimed and
  never silently skipped: anything the WORLD holds is an error naming the cell, a cell only an
  unbuilt DESIGN claims is taken and reported (nothing old is live on this island).
- **THE LINE MUST END ON GROUND.** Ending at a fixed `y_bottom` put the terminus in the ONE 33-cell
  stretch of the ring with no floor under it - a platform 43 blocks over open void that you step
  out of the cart and fall off. 185 of the 240 ring columns have lowland floor and 55 do not, so
  the line asks: it descends only where there is something to descend toward, holds level over
  void, and lands the moment floor comes back under it.
- **A TERMINUS NEEDS A STOP BLOCK.** A stationary cart on a powered rail launches AWAY from the
  adjacent solid block. Written with the indices inverted it placed neither, silently, and the line
  would have run only whichever way you happened to shove the cart.

And two of the repo's standing traps, both hit again:

- **`dict.get(x, z)` reads `z` as the DEFAULT**, so the tuple-keyed ground table returned a Z
  coordinate as a height and the route terminated on its first cell.
- **A fixture that belongs BESIDE a thing must be excluded from the thing by construction.** The
  perpendicular flips through a corner, so the dressing offset walked back onto the line and stood
  a lantern on a powered rail - the frog's "the eye sits over the hind foot in plan" in a hard hat.

### The lighting was ten times the metal of the railway

58 lanterns came to **~52 iron** against the eleven corner rails' 4. On the island whose scarce
metal is iron, the lights cost more than the line. **61 ochre froglights set flush INTO the deck
edge** cost none, use the idiom this island already lights itself with (Island Night, the lowland
turf), cannot be knocked off a walkway 150 blocks up, and leave the 3-wide deck clear to walk. A
flush froglight reaches 14, not 15 - it IS the floor, an opaque emitter a course down - and the
spacing is set against that.

The stone still carries the Lowland Stair's gradient (island stone brick, deepslate, the quarter's
blackstone) so the two read as one hand. **The light does not go cold with it**: verdant and
pearlescent froglight stock is zero and soul lanterns are iron. One tone, stated in the config.

### What it costs, and what is still open

The only real purchase is **518 powered rails = 518 gold**; stone brick, blackstone brick and
deepslate brick wall all craft from stock, and 2,251 of the 3,300 blocks are already in containers.

- **The existing east line is KEPT, not deleted.** Its 104 cells run deck -> east lobes -> bee
  house and the spiral is affordable without salvaging them.
- **THE DECK SPUR IS NOT BUILT, AND THE TOP STATION FLOATS.** The top terminus stands at
  (-24231, 192, 29984): **43 blocks** from the deck rail head at (-24197, 192, 29993), and the
  nearest island block of ANY kind is 22 away. **128 design cells sit at Y>=186 and not one of them
  touches the island** - so the line is complete, printable (it builds upward off its own chain from
  the lowland end) and not reachable on foot. Until the spur is built you can ride UP to the top
  station and be stranded there. That junction is the next piece of work; it crosses the busiest
  part of the deck, which is why it was not guessed at here.
- **The ~1-in-8 power spacing and the corner deceleration are the two numbers still unverified.**
  Everything else here is read off the registry or measured off a capture; these are reasoned. A
  24-block test ramp with one corner answers both before 518 gold is committed.

`tests/test_railspiral.py` (18) pins all of it: the registry fact about curves, corners flat on both
sides, slopes ascending toward the higher neighbour, every run powered at both ends and never past
the spacing, no source wasted on a corner, inside the plot, clear of the stair, the terminus on real
ground with a stop block, nothing standing on the track, one piece, no iron-cost lights, and that a
blocked track cell RAISES rather than leaving a gap.

