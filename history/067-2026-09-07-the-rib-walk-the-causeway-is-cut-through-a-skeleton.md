## THE RIB WALK: the causeway is cut THROUGH a skeleton (2026-09-07)

`configs/pf_rib_walk.yaml`, `mcbuild/gen/ribwalk.py`, `tests/test_ribwalk.py` (10).
**3,647 blocks, 0 problems, overlap 0 in context, 0 leaks, all cheap-or-ok.**

### SEVEN SUBJECTS WERE REJECTED, AND THE FAULT THEY SHARED WAS THE REGISTER

The ankylosaur, then an ammonite, a pterosaur skull, a hatching egg, a giant dragonfly, a claw and
a tree fern. Jack, on the last three: *"i dont think any of these are unique or interesting, we
want something that is as awe inspiring as the other island elements."*

**EVERY ONE OF THEM WAS AN OBJECT STANDING BESIDE THE WALK**, because I had sized them to the two
stops already there - the balloon at 2,299 and the wyrm at 985. Nothing on this island that
inspires awe is that shape of thing:

    Abyss Squid    46,882 blocks hanging in the VOID under the park, found by parkour runners
    Wyrm Gate      27,857 blocks straddling a LIVE RAILWAY, the train through its mouth
    Mine Ridge     41,948 blocks of mountain with a COASTER CUT THROUGH IT

**What they share is that each one USES ITS SITE**, and the causeway's own unused resource is that
it is a walkway over nothing at all. So the sculpture is the corridor: a colossal ribcage, 75 long,
the spine arched over the deck, the ribs coming down outside the walk - and, the move only this
bridge can offer, **CARRYING ON PAST THE DECK INTO THE VOID**, so a guest at the rail looks down
and the cage is still there with nothing under it.

**AND A SKELETON IS THE ONE SHAPE THIS MEDIUM CANNOT GET WRONG.** This file's own words, from the
bone bed: *"a spine is a line, a rib is a curve one block thick, a skull is a small box with holes
in it."* No barrel, no haunch, no compound muscle and above all NO LIMBS - so the failure that
retired eight mammals, then the stegosaur after four rounds of polish, then the ankylosaur after
six, cannot occur here. That is a property of the subject rather than a hope about the execution.

### THE CAUSEWAY IS REFUSED CELL BY CELL, AND THE REFUSAL IS THE EFFECT

`loft.Frame.taken` is new and general: cells another design owns, declined and counted rather than
clipped or refused, because it is neither a mistake nor an edge - it is this build correctly giving
way. A rib arrives at the paving, stops, and picks up again underneath, so the bridge reads as
having been cut through a fossil rather than as a hoop over a path. 424 cells declined; `overlap 0`
is a property of the construction and the causeway can be regenerated under it.

**It also means the design alone is in six pieces, and that is CORRECT** - the Mine Ridge's own
recorded situation, where *"the design alone is in six pieces... the composite is the truth"*. A
test demanding one piece from the design alone would be demanding that the causeway not pass
through it, so what is asserted is that it builds whole when nothing is refused.

### Five defects, and three of them were invisible in the render

- **THE FRAME'S ORIGIN WENT WHERE THE CONTENT IS.** `Frame.at` maps forward as `cu + fz * f`, so
  for a north-facing piece u DECREASES with f - and this design's content is entirely at POSITIVE
  f, unlike an animal, which straddles its own origin. Set to the back margin the way an animal
  sets it, every cell of a 128-long cage mapped off the canvas: **25,565 clipped, a skull that
  placed NOTHING, and a render that still showed a plausible ribcage**, because what survived was
  the near end.
- **THE DECK'S HEIGHT IS DERIVED FROM THE DROP, NOT PASSED IN.** The ribs carry BELOW the walk -
  that is the whole idea - so a deck at a fixed 7 puts nineteen courses of cage under the canvas
  floor. Same 25,565, same clean-looking picture.
- **A THIN CURVE HAS TO BE THREADED, NOT SWEPT.** Thinning the ribs from four cells to one - which
  is what turns a culvert with stripes into a cage - took the model from seven pieces to **THREE
  HUNDRED AND SIXTY**. Below about r=0.9 a ball is one cell, and two consecutive cells whose
  centres moved on two axes at once are diagonal neighbours. It cost the pterosaur three spans and
  the stegosaur its tail spikes before the rule was written down.
- **AND THE CROWN LINE TOO**, because `sin(pi*t)**0.42` falls away VERTICALLY at both ends: its
  derivative is unbounded as t approaches 0 or 1, so the last two spine stations differ by more
  than a course. One 21-cell vertebra floating off the tail, one piece out of two, and it audits
  clean because a detached vertebra is a legal block.
- **THE PART COUNTS WERE `put()` CALLS**, reading 20,258 ribs on a 13,978-cell model. Counted as
  unique cells they partition the build - the squid's lesson, and the thing that exposed the
  ankylosaur's horns placing 124 blocks and gaining none.

### The skull is OFF, and that is a decision

Built, it came out a filled oval plate with a slot in it: consecutive rings overlap and fill, and a
skull is a box with HOLES in it or it is nothing. More to the point **this park already has a
walk-through skull at the Wyrm Gate**, and repeating it is precisely the reason the gecko and the
bat were removed from the hollow reach. The machinery stays with the reason beside it; the cage
alone is the stronger object.

### And a test that measured the wrong band

`test_it_is_a_CAGE_and_not_a_tunnel` first sampled six courses under the crown and reported 31%
sky, which is true and is not the question: near the spine every rib converges on it by
construction and the neural spines fill what is left. **A test for how something reads has to
measure the band it is read in** - at a walker's own eye height it is 21 ribs across 85 columns,
three quarters of it open. Same lesson as the ankylosaur's belly, which passed on the midline and
failed on the flank.

    the cage   75 long, 45 wide, 24 courses over the deck and 16 below it
    z 80458..80533 of the Frontier Reach's 80450..80550, clear of the sloth at t=0.82

**AND IT CAME DOWN 15% ON SIGHT.** Jack, on the 88-long build: *"can it be just maybe 15%
smaller."* One number - every dimension here is a fraction of the length, which is this file's own
named trap read the useful way round - and the siting followed from it: the cage keeps the same
CENTRE on the reach (z 80496) and gains margin at both landfalls. 5,237 blocks -> 3,647.

**Still open:** the ankylosaur is retired from `GAPS` and kept, exactly as the stegosaur is - both
still build and keep every test. Nothing here has been placed in game. And the hatching-egg
block-out is worth a home somewhere: measured, every dig site on the Lost Plateau is full - the
largest clear rectangle in the bone bed, the diggings or the vale is a 3-wide strip - so a big one
needs the Frontier's west verge (13 x 201 free at Y202), while a CLUTCH of small ones would fit the
north pit's 15 x 3 beside the skeleton.

