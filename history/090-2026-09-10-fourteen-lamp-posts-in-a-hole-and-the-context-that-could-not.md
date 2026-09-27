## FOURTEEN LAMP POSTS IN A HOLE, AND THE CONTEXT THAT COULD NOT SEE THEM (2026-09-10)

Jack: *"the prism parkour area has floating full lamp posts in its area."* Measured off the shipped
composite before anything was changed:

| | |
|---|---|
| Prismworks signal masts standing inside the Prism Well's r50 mouth | **14** |
| ...with NOT ONE solid cell in the 5x5 box at their own course | **9** |
| what each one is | a pad, four wall cells, a caged soul lantern and an end rod, over ~200 courses of void |

All nine sit between r17 and r47 of the well's axis - the middle of the shaft a parkour runner
descends, which is the one place in this park anybody is looking sideways at open air.

### THE CUT COULD NOT SEE THEM, AND IT IS STRUCTURAL RATHER THAN STALE

`prismwell.cut` is careful and its own comment records why: an earlier WHITELIST *"shipped
sixty-one cells hanging over the hole"* because `Park Ways` puts a mast on the verge every
twenty-two cells and the four materials it is made of were not on the list. It was replaced by a
blacklist of machines, which is right.

**It reads `park_future`, and `prismchain.build_park_future` EMPTIES the well's whole cylinder to
r62 - deliberately, so the well is never measured against its own previous self - keeping only the
DECK COURSE.** So the cut sees exactly one block per mast column, digs the pad, and the eight
courses above it survive in `Park Complete` **however many times the chain is rebuilt**. The dig
list is correct about the context it was computed from, and the context is not the park.

> **A CONTEXT THAT IS HONEST ABOUT A DESIGN'S GEOMETRY CAN BE BLIND ABOUT ITS DIG LIST.** The
> sweep's own comment already says the deck course is kept *"because a context that has already
> removed it cannot tell you whether the dig is right"* - and that reasoning is true of everything
> else in the cylinder and was not extended to it.

### THE FIX IS THAT THE GROUND LAYER DOES NOT PUT A MAST IN A HOLE

`parkways.keep_clear` already exists for exactly this and its distinction is the right one: a
feature lot refuses PAVING too, and `keep_clear` refuses furniture and nothing else. **The paving
must stay** - the well digs the deck, and a context that has already lost it cannot say whether
that dig is right - so only the furniture goes.

- **A KEEP-CLEAR MAY BE ROUND, BECAUSE A HOLE IS.** As a bounding square the mouth's corners reach
  r70, where the deck is real and a lamp on it is a lamp doing its job; a disc is 79% of its
  square, so the rectangle-only version puts out about a fifth of a land's lighting to solve a
  problem that exists only inside r50. `is_reserved` already handled circles for roundabout
  islands - the grammar was half there.
- **A VISTA IS A CORRIDOR AND A HOLE IS NOT, SO THEY GET DIFFERENT ANSWERS.** Nudging a mast along
  its own street until it clears a sightline is a real fix - it still lights the street, which is
  why both vista bands carry a cell of tolerance so a nudged mast *"cannot arrive back in the
  vista from the end"*. There is no along-the-street inside a hole: the street stops. **It cost
  the rhythm to find out** - refusing the mouth and letting the nudge run moved the avenue mast at
  V42/U522 two cells to V40, out of the disc by half a block and off its own rhythm station, which
  is the one thing `test_a_lamp_stands_on_one_line` exists to forbid. A disc refuses outright.
- **AND THE DECLARATION IS DERIVED, OR IT GOES STALE IN SILENCE.**
  `test_the_prism_well_mouth_is_kept_clear_AND_MATCHES_THE_WELL_S_OWN_CONFIG` reads the centre and
  the radius out of `configs/pf_prism_well.yaml`, so moving the well fails a test rather than
  putting fourteen masts back over the void.

### A test was encoding the decision that had just been reversed

`test_every_crossing_the_street_reaches_actually_gets_its_four` failed on the crossing at
**V125/U524 - which is inside the mouth**, r36 from the axis. The well digs the deck out from
under it, so the four corners the test asks for are four masts in open air. A crossing inside a
hole is not a crossing; it stays in `_crossings` only because the PAVING is deliberately left for
the well to dig. Same class as the frog's proportions and the stegosaur's plate rooting: **a test
that pins a decision has to change in the same commit, or the suite quietly enforces the thing
that was just rejected.**

    masts standing with nothing beside them   9 of 43  ->  0 of 28
    ground-layer mast material inside r50     14 masts ->  0 cells
    Park Ways 128,913 blocks, 0 problems      Park Complete 429,762

**Still open, and deliberately not touched.** One `iron_bars` cage cell at (97541, 209, 80822),
r49.5, belongs to a mast standing on real deck at r50.5 and reaching one cell over the lip - which
is the module's own stated rule, *"an arm may reach OVER a path, a post may not stand in one"*.
`prismwell`'s cut still cannot see anything the ground layer puts in its cylinder; this closes the
one case that exists today rather than the class, and the class's real fix is either a cut that
reads the true composite or a sweep of what a dig leaves standing on air. And
`test_every_module_is_either_placed_or_declared_not_to_need_ground` still fails on `Wyrm's
Crossing`, which is pre-existing and another stream's.

