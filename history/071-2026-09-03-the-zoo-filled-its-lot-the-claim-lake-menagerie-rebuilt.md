## The zoo filled its lot: the Claim Lake Menagerie, rebuilt (2026-09-03)

Jack: *"the zoo on the park is tiny and doesnt look good, we want to use the full space and make
it much more visually interesting."* Both halves were true and both are measurable, which is the
useful part - **nothing in this pipeline asks whether a design uses the ground it was given.**

| | before | after |
|---|---|---|
| columns of its lot occupied | 455 of 1,014 (45%) | **936** (the whole lot bar the frontage verge) |
| tallest cell | **3 courses** | 17 |
| columns 3 or more courses tall | ~8% | **32%** |
| blocks / column | 1.7 | 2.9 |
| distinct kinds of enclosure | 1, drawn four times | **4** |

`tools/park_lots.py` had the lot's real size all along - `frontier|midway / exit-observation,
V128-153 x U173-211`, 26 x 39 with a park walk on all four sides. The zoo was a 13 x 35 strip
inside it. Every offline check passed: 0 problems, 0 overlap, one piece, all cheap.

### FOUR IDENTICAL RECTANGLES READ AS ONE RECTANGLE HOWEVER LARGE YOU DRAW THEM

The old design was four 7x10 fenced squares in a row with an identical 3x3 lean-to in each. That
is `gen/casino.py`'s finding in a new body - eighteen game rooms that measured 94-99% alike and
turned out to be two games wearing four names - and the fix is the same: each quadrant has to be
a DIFFERENT KIND OF THING, not the same thing relabelled. A red timber **barn** you walk through
(four railed stalls off a cross aisle, a stair-slope gable roof), a sunken **pond**, an open
**meadow**, a cage **aviary**, and a raised **lookout** terminating the spine.
`test_the_four_habitats_are_four_different_things` compares every pair's block multiset and fails
above 60% shared, because "they are all pens" is exactly the answer a bigger row would give.

Two rules this repo had already written and this design had not obeyed: **architecture below ~6
courses dissolves into ground noise** (the Frontier's ruin fragments), and **a route with
somewhere to stand on it is somewhere to be** (`gen/claimrow.py`) - you walked PAST the old pens
along one edge and there was nothing to walk INTO.

### THE VERGE IN FRONT OF IT IS NOT SPARE GROUND

`Park Ways` stands three lamp standards on V129 at U175, U192 and U209, and **U192 is the lot's
own midline**. Built one row further forward the gateway would have had a lamp post in its
doorway. Starting at V130 costs 39 columns and the three lamps light the frontage for nothing -
which is the same trade the Welcome Court's `keep_clear` makes, arrived at from the other side.

### Five things that shipped a clean audit and a wrong build

- **FIVE SIGNS WERE REFUSED IN SILENCE.** `park._sign` returns False when there is nothing behind
  the board, and four stall signs were written over a fence GATE - which is one course tall with
  nothing above it. `_pen_sign` builds the post it hangs on, because a pen rail is fences and a
  fence line has no cell a board can hang from until one is put there. The only symptom was
  `signed: false` in a sidecar nobody reads.
- **THE LOOKOUT'S BALUSTRADE WAS BUILT INSIDE ITS OWN DECK.** `_rail` had no base course, so
  every post and fence went in at h0 - three courses under the deck's top - and the canopy that
  stood on them shipped as a **32-cell free-floating cluster**. A rail helper that cannot be told
  what it stands on is a rail helper that only works at ground level.
- **A TIE BEAM IS NOT ONE CELL.** The barn's aisle lanterns each hung from a single beam block at
  plate height, and a barn is open from its floor to its plate - so the four of them came out as
  two floating clusters. They span wall to wall now, which is what a barn has there anyway.
- **A GATE MUST OPEN ONTO SOMETHING.** The paddock's side gate was moved to a `d` past the end of
  the spine and came to rest against the lookout deck's own solid flank: a gate that leads
  nowhere, and neither the audit nor a render can tell. `test_every_enclosure_has_a_gate_onto_a_
  path` demands two standable sides.
- **PLANTING IS LAID BEFORE THE RAILS, SO A DRIFT LANDS IN THE DOORWAY.** A fern is passable and
  the audit is right to allow it; a tuft in the one cell you step through still reads as an
  obstruction. The ground cover is swept out of every gate's four neighbours as the last act of
  the build - `gen/claimrow.py`'s rule that the way refuses rather than the hand remembering.

### And the aviary was a crate until its frame changed families

Built with `oak_log` posts and `oak_fence` bars it rendered as one solid brown box at all eight
bearings - 88 against 134 in luminance, which is not a frame, it is a wall. The frame is the
land's **wall** colour now (`white_wool` 236) with a `polished_blackstone_bricks` cornice (45)
oversailing one cell proud on every side, and the cage reads as a cage. **This is the same
mistake this file records four times already** - searching for a value ladder INSIDE one material
family, where one cannot exist by construction.

**2,933 blocks, one piece, 0 problems, 0 new problems in context, 0 clashes with any other
module, all cheap bar five hay bales.** `tests/test_menagerie.py` (11) pins the lot coverage, the
lamp row, the four-habitat contract, the skyline, connectivity, every sign PLACED, the pond
bedded and enclosed, the soil rule, the material policy, the gates, and the sidecar still saying
what it has always said: **a litematic is blocks, not entities.** Every enclosure ships empty and
each gate names what to lead in and with what; stocking them is Jack's job in world.

**Still open, stated rather than hidden:** none of it has been placed in game, and `render3d`
draws a fence as a full cube - so the aviary's bars are the one element these sheets genuinely
cannot judge. And `tests/test_park.py` has 16 pre-existing failures in
`test_every_kind_is_one_connected_piece[*-paths]`, all in `park._paths`, which this work does not
touch.

