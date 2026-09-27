## THE CANOPY WALK - the park's first upward addition (2026-09-13)

`configs/pf_canopy_walk.yaml`, `mcbuild/gen/canopywalk.py`, `tests/test_canopywalk.py` (8).
**1,138 blocks, ONE connected piece, 0 problems, 0 new problems in context, all cheap.** A timber
walkway at Y228 across the Lost Plateau's ridge, x97555-97645 at z80402-80417, with a flight down
to the rock at either end.

**IT IS UPWARD BECAUSE THE GROUND IS FULL** - 27 free pads of 8x8 or better in the whole 600x200 -
and a canopy walk is the one upward thing that needs no ground at all: it stands on piers in the
verges, which is the park's one surplus.

### THE ROUTE IS FOUND, AND THAT IS THE WHOLE DESIGN

The ridge's top surface runs Y202-250 with a median of 219, and both naive answers fail on those
numbers: a CONSTANT deck collides with the four peaks over Y237, and a deck that FOLLOWS the
surface undulates Y210-252, which is a staircase. What works is to hold the deck level and move the
ROUTE - a least-cost line over the corridor, where being inside the rock is fatal, being far above
it is a cost, and every sideways cell is paid for so the walk wanders only where the rock makes it.

**RE-DERIVED ON EVERY BUILD, never hard-coded.** `PF Mine Ridge` is 36% built: waypoints would be a
snapshot of one day's rock, and the mountain under this walk is going to keep arriving.

### Five faults, and each one is a rule this repo already carries

- **ONE CELL OF SIDEWAYS PER CELL OF FORWARD.** Left free, the least-cost path jumped several cells
  of u between adjacent columns of v - and a deck whose next course starts three cells over is not
  joined to it. The first build came out in **SIX pieces**. A walkway does not teleport.
- **THE SADDLE IS A SPAN, AND IT IS THE TERRAIN'S ANSWER.** x97618-97635 has no ground a pier could
  stand on within reach of the deck at ANY corridor width - swept at `u_slack` 9, 12, 15 and 18,
  the route is forced across the same eighteen columns every time. So it is BUILT as a bridge:
  `max_span` is raised deliberately rather than by accident, and a pylon at each end with a fence
  catenary between them makes the span read as carried.
- **THE CABLE IS ONE CELL WIDE, SO EVERY STEP IT TAKES HAS TO BE THREADED.** The deck gets away
  with a sideways step because it is three wide and the courses overlap; a single line of fence
  does not, and neither does a change of sag. Both shipped as diagonal-only joins - the ear-tip
  rule, on a mane, a pair of ossicones, a tail and now a bridge cable. The sag is gone: a catenary
  is worth nothing if it arrives as a stray.
- **`width` IS THE WALKABLE WIDTH, AND THE RAIL STANDS OUTSIDE IT.** Laid with the rail on the
  deck's own kerb, a three-wide walk has ONE clear lane: 128 standable cells for 91 columns of
  deck, which is a plank rather than a walk. Only `test_..._can_actually_be_WALKED` could see it -
  every other check is about blocks and this one is about a person.
- **A KERB NEEDS THE LANE CELL BESIDE IT**, not merely a lane somewhere in its column. Where the
  rock refuses the outermost plank the kerb has nothing to be the edge of and ships as a one-cell
  island of slab.

`_prune_strays` guarantees the single piece and **reports its own count (6 of 1,144)**, with the
bound asserted - `stegosaur`'s rule that a geometry needing a lot of stitching is a geometry that
is wrong, and that the net must never become how the contract is met.

### Still open, and stated rather than hidden

**The setting is 31% built.** `PF Lost Plateau` (the jungle canopy, 10,558 cells left) and
`PF Mine Ridge` under it (27,029 left) are what make this read as a walk through TREETOPS rather
than as a gantry beside a hill - and in the context render that is exactly what it still is. The
walk lands on real built rock either way; it will not look like its own name until the canopy is in.

It is shipped and placeable by name. It is **not** in `park_place.EXTRAS_READY`, so it is not in
`Park Complete` - that is a decision about the composite, not about the design.

### The merge grew a second AIR entry, and it poisoned everything that asked `ids != 0`

Found while pointing the canopy walk at the merged world, and it is the most transferable bug of
the session. `coop.merge_scans` seeds its palette with `pal = [scans[0].model.palette[0]]` - air at
index 0 - and left `key_index` EMPTY, so the first scan's air matched nothing and was appended as a
**second air entry holding 2.3 million cells**.

`Model.solid()` knows both and is right. **Everything that asks the ordinary question is wrong:**

    merged world   ids != 0  ->  33,021,122        solid()  ->  379,768
    the sidecar's own `non_air_blocks`             33,021,122

...and `finish.verify_against` reported **every cell** of a design verified against a cut of it as
an overlap, which is what surfaced it. `compact_palette` cannot help: the two tags are genuinely
different objects with the same key.

Fixed at the seed (`key_index = {state_key(pal[0]): 0}`) and belt-and-braces in `_paste_columns`,
which now maps any air-like state to 0 whatever its NBT. `non_air_blocks` is `m.solid().sum()`.
**The first attempt at the guard silently did nothing**, because `state_key` returns a TUPLE and
`str(...).split(":")[-1]` of one is `"air', ())"` - a membership test that can only ever be false,
which is this file's own most-repeated failure shape.

