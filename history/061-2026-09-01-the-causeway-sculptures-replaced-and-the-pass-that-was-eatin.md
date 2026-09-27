## The causeway sculptures, replaced - and the pass that was eating them (2026-09-01)

Jack, on the shipped isthmus: *"ladybug sucks and is all glowing etc, we need a new sculpture
there, similarly i think we dont need 2 standing birds, lets replace flamingo with something
else that works really nicely and will fit"*. Two complaints, two unrelated causes, and the
first of them was not the ladybird's fault at all.

### THE GLOW WAS `_delight`, AND IT WAS TURNING THE SCULPTURES INTO LAMPS

Measured on the shipped design before anything was changed: **1,138 `ochre_froglight` cells
placed by the night sweep, and every single one of them inside a creature's coat.** Not one
landed on terrain.

    black_wool 299 . red_wool 295 . lime_wool 147 . pink_wool 129 . stone 82 .
    light_gray_wool 71 . white_wool 35 . green_wool 25 . dark_oak_planks 16 . yellow_wool 11

That is the ladybird's shell, its spots and its leaf; the flamingo's body; the heron's neck.
1,352 froglights in a 41,079-block design - **3.3% of the whole causeway was a lamp** - and the
ladybird, being a broad convex dome with a big flat leaf under it, caught more of them than
anything else. "All glowing" is a precise description.

`isthmus._delight` patched every dark spawnable cell by replacing the block UNDER it with a
froglight. For terrain that is exactly right and is this island's own idiom. For a sculpture it
is vandalism, and the docstring cited `frog.py`'s *"in the skin, not on it"* for it - **a rule
about a HANDFUL of lamps a designer chose and placed, not a licence to perforate a coat
wholesale.** The rule that governs is `Island Night`'s, and this file simply had no cost model
to state it with: *a fixture ON a sculpture damages it - ordinary ground is cheap, a coat is
dear.*

The fix is that a sculpture's cells are RECORDED as it is pasted and handed to the sweep:

- a dark cell over **ordinary ground** still gets the flush froglight, unchanged;
- a dark cell over a **coat** gets `glow_lichen` in the AIR above it - `Lowland Glow`'s own
  answer, arrived at for exactly this problem on exactly this kind of surface (it is what lit
  the axolotl's back). It emits 7, it is passable, cheap and 1.19, and it **adds** to the
  sculpture instead of eating it: not one creature cell is replaced;
- and because 7 carries six blocks through air, the lichen is thinned to a 5-block separation
  and the model re-propagated, so a handful settles a whole flank.

**1,352 froglights -> 253. Fifty-six lichen. `delight_in_coat` is 0 and asserted, and
`spawnable_dark` is still 0.** The count is cross-checked without the bookkeeping as well:
every block a creature generator emitted must still be standing in the finished causeway, so a
shortfall in any of its own palette is a coat cell something overwrote.

**And it exposed a second bug the moment the stops grew.** `exclude` was one radius doing two
jobs - keeping ambient drifts off a stop, and keeping ambient LAMPS off it. Sized to the new
structures it left **534 columns of moss unlit** at a stroke, which the sweep then filled one
lamp per cell. *"A stop lights itself"* is only ever true of the stop's own FOOTPRINT, never of
twenty blocks of open shoulder around it; they are two radii now.

### FOUR SCULPTURES, FOUR SHAPES, AND NOT ONE GENERATOR USED TWICE

The old lineup was a heron and a flamingo - one generator and one body plan, differing by
colour and two curves, which `heron.py`'s own docstring says outright - plus a ladybird on each
span. **Four pieces showing two shapes.** `test_the_two_spans_use_different_creatures` could
never catch it, because two spans can differ while each repeats a shape the other already used;
the new check is on the KIND, across the whole causeway.

Chosen on this file's own measured line, PLANAR/COLUMNAR against VOLUMETRIC, not on taste:

| span | t | | shape |
|---|---|---|---|
| Frontier Reach | 0.14 | **heron** (kept, scale 0.9) | an upright column |
| | 0.82 | **sloth** on a bough | a body slung UNDER a line |
| Hollow Reach | 0.26 | **bat** under a gantry (scale 0.7) | a horizontal membrane sheet |
| | 0.80 | **gecko** on a stele | a vertical plane |

**A creature is sited with the thing it stands on, hangs from or clings to**, and that is all
the new work: a stele of the land's own masonry for the gecko (its own docstring asks for a
cliff), a two-pier gantry for the bat, and two posts under the sloth's own branch - both are
hanging animals and a causeway has no ceiling anywhere. Not one line of any creature generator
was touched. `dragonfly.py` was tried and dropped again for the recorded reason: its trapdoor
wings are five components by construction at any scale, and bridging them would be editing a
tested generator's silhouette to suit this file. `turtle.py`, `frog.py` and `axolotl.py` are
out because all three take a world CAPTURE and probe a ground band that assumes the lowland's.

### Three faults inside the siting, each of which shipped a clean audit

- **EVERY PASTED CREATURE NEEDS A QUARTER TURN AND TWO OF THEM DID NOT GET ONE.** `_paste` only
  offsets, so a generator keeps its long axis on world X - and a creature stop is itself offset
  along world X, which is the axis a walker on the spine looks straight down. A 39-block
  wingspan and a 28-block bough both shipped **EDGE-ON from the only place anybody stands**: a
  post and a lump. Invisible in a plan view and obvious the first time `tools/look.py` was
  pointed at the bearing the walkway actually gives you. The gecko had been turned by hand for
  exactly this and the rule was not generalised. `_turn` re-aims an `axis`, carries a vertical
  property through and REFUSES anything naming a horizontal direction - our renderer draws a
  wrong facing and a right one identically, which is the stair convention's own failure.
- **A GANTRY SHIPPED WITH ONE LEG.** A span is 101 rows and a stele is 33 of them; at t=0.86
  the far end lands PAST the plot the causeway stops against, `cols` has no column out there,
  and `_ground_pier` therefore built precisely nothing - no error, no missing-cell report, and
  the design still audits as ONE PIECE because the lintel carries it across. `_CREATURE_ZHALF`
  states each structure's own reach, the centre is clamped into the span and the clamp is
  recorded, and a test asserts no shipped stop ever needs the clamp.
- **THE GANTRY'S LAMPS WERE NEVER PLACED.** The beam's band went in first and the lamp loop was
  guarded by `w.has`, which was then true at every one of those cells - seventy dark spawnable
  cells fifteen blocks over the walkway, silently. The froglights ARE part of the beam's own far
  course now, not something laid on it afterwards. `transit._lamps`'s rule, in a new body.

And one thing only a render decides: **a hanging creature wants a marker stone, not a
pedestal.** Given the heron's own five-block plinth, the bat and the sloth each stood over a
two-course disc of the land's trim with nothing on it, and an empty plinth reads as a statue
somebody has taken away. Three blocks, enough to carry the name plaque.

### The rendered verdicts, recorded (2026-09-01)

`tools/look.py --sheet panel`, cut out of the FINISHED causeway so each is judged with its own
plinth, ground and lighting, at the bearing the walkway actually gives you.

**GECKO ON A STELE - PASSES, and it is the best thing on the causeway.** Head-on it is
unmistakable: head down, four limbs splayed with fanned toes, big orange eyes with black
pupils, the tail curling up and over, all on a black slab with a lit coping and two banded
courses. The value panel is a flat dark ground with a bright figure on it, which is what a
relief IS. Two honest limits: **you cannot name it from the silhouette, because the silhouette
is the wall** - that question does not apply to a figure read against a plane - and it is a
smudge by 6x. It is also the one stop with no glow problem at all, and by construction: a
sculpture on a vertical face has almost no upward-facing surface for a mob to stand on, so
there is next to nothing for the night pass to want to light.

**Its back is a blank 33x34 wall and that is left as it is, deliberately.** The stele's face is
turned toward the spine, so a walker on the walkway only ever sees the lizard; the blank side
is what you get looking at the stop from the far shoulder, which is a place nobody goes. It
carries the same banded courses as the front and it is not worth another two thousand blocks
of relief to dress a face with no audience - the deck gallery's own lesson, that a block placed
to move a number is a block placed for the wrong reason.

**HERON - PASSES, unchanged, and it is the control.** Stilt legs, S-neck, dagger bill, layered
wing; still reads at 3x. Kept for that reason and no other.

**BAT UNDER A GANTRY - PASSES close and at 3x, MARGINAL beyond it.** A gantry with a wide dark
membrane slung beneath it, two bone claws gripping the beam, the body and legs hanging below.
`spread` 0.75 beats 1.0 and that was measured, not assumed: fully spread the wing is one flat
plate, half-furled it keeps a stepped outline and the finger struts and black tips are the
tell. **Scale 0.7 is the largest that is still one piece** - 0.6 sheds two wisps, 0.8 and 0.9
shed three or four, 1.0 is whole again but 56 blocks wide, which forces a `t` between 0.30 and
0.70 and collides with the pool, the garden and the overlook. From fifty blocks it is a frame
with a dark mass in it.

**SLOTH ON A BOUGH - PASSES close, MARGINAL at 3x.** Close it is instant: a hammock body under
the branch, four limbs angling up to it, the pale mask and black eyes, moss on the back. It is
the smallest of the four (26 blocks) and it sits inside a timber frame, so at distance it is a
lump between two posts. Worth building bigger if it ever matters - `sloth.py` has no scale
parameter, so that is a change to the generator, not to the siting.

**Judge the palette in game.** Everything above is `render3d`, which draws every block as one
flat RGB out of the same database the palette picker optimises against - this file's oldest
recorded circularity. What these renders are ground truth about is GEOMETRY and OCCLUSION.

### The bill

**41,079 -> 43,151 blocks (+2,072, +5%), 0 problems, 0 expensive, 42,311 cheap and 840 ok.**

    ochre_froglight              1352 ->  253    -1099    the glow
    red_wool                     1606 ->    0    -1606    the two ladybirds
    pink_wool                    1090 ->    0    -1090    the flamingo
    polished_blackstone_bricks    126 -> 1999    +1873    the gecko's stele
    moss_block                  11854 -> 13416   +1562    the bigger stop bulges
    brown_wool                      0 ->  674     +674    the sloth and the bat
    glow_lichen                     0 ->   56      +56

