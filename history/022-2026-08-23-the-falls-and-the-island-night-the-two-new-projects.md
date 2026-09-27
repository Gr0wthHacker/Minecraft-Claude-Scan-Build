## The Falls, and the Island Night (2026-08-23) — the two new projects

Jack, after the acceptance: *"Do Falls, night pass"*. Both are designed against the 15:54
scan, both are tracked in `sync.yaml`, and they are the only live work on the island.

| design | blocks | dig | what it is |
|---|---|---|---|
| `Falls` | 30 | 41 | the channel that lets the isle's cistern spill to the lowland |
| `Island Night` | 105 | 30 | every walkable surface on the island taken to zero spawnable cells |

### The Falls: the phenomenon was already there and it was an accident

The plate's pond drains through a surface stream along X-24209 at Y203, steps to Y202 at
Z29992, and at Z29991 runs out of island — **one column of water falling 107 courses**, Y202
to Y96, landing in the void isle's pond. It is the only long fall on the island and nothing
about it read as intended: no lip, no basin, no outlet, water leaving over moss.

So the design **builds nothing that falls. It builds the things that let water fall** — which
is why 30 blocks and 41 dug cells buy an element that crosses all three levels. The chain is
now plate pond → stream → dressed head → 107-course fall → the isle's pond → a cut channel →
a notch → **a second fall of ~60 courses into the lowland harbor at Y37**. The lowland's water
now arrives from the island above it rather than simply being there, and the descent walks
beside it.

**Four measurements decided the site, none of them guessable:**

- The isle's pond is **fully enclosed** — 132 cells at Y99 and not one edge cell has a clear
  drop beneath it. There is nowhere it spills by itself; it has to be cut.
- The isle's south rim is a thin **shelf**: rock at Y96–99 with open void below Y95. Four
  courses to cut through, against the ten the pond's own bed would have cost — which is why
  the tail leaves from the rim and not from under the pond.
- The axolotl lies along the harbor's **west** bank (X-24246..-24221), so every spill west of
  X-24216 lands within 5 blocks of the animal. The tail leaves from the SE corner instead.
- At X-24212 the fall hangs **~13 blocks off the Lowland Stair**, far enough not to crowd the
  helix and close enough to descend beside.

**Hydraulics, and the thing that would have made it decorative.** Flowing water dies seven
blocks from its source and the cut channel is seven long — exactly the distance at which the
flow arrives at the lip as nothing. So the channel bed carries **water SOURCES**, cell by
cell, and the last stand at the apron. A source is infinite, so the pond is not drained and
the fall does not stop. The whole chain is verified end to end before a block is dug: bed
solid under every water cell, no wall leaks, the notch open Y94–99, and a clear drop to
harbor water at Y37 in all three lanes.

**One lane wide for the run, three at the apron.** A 60-course thread one block wide does not
read from the lowland floor, and for the tail to fall three wide the water has to arrive
already spread — which is what the apron is for, and it costs no extra digging in the run.

**The notch is the plug: cut it LAST.** Pull it before the channel is dressed and you flood
the trench you are standing in. `/cscan dig` lists all 41 cells.

### The Island Night: the dark was not where anyone would have put a lamp

Block light propagated through the whole assumed-final world and the walking surface
classified. Of **6,851 walkable cells, 1,420 were spawnable** — 1,067 open to the sky (dark
only at night) and **353 enclosed** (dark day and night). And the dark was mostly **not floor**:

    ladybird 361 cells · owl 121 · bat 38 · gecko 20 · the axolotl's back · tree canopies

**A fixture ON a sculpture damages it, and light reaches 14 blocks** — so almost every
sculpture top can be lit from ordinary ground standing near it. That is the whole design, and
it is encoded as COST rather than as a rule: ordinary ground is cheap, a coat is dear, and
greedy maximises newly-covered-per-cost, so it lands on an animal only where nothing else can
reach. 105 fixtures take the island to **zero spawnable surface cells**, re-verified by
propagation in `tests/test_island_night.py`.

One idiom per surface, all of them already spoken here: **froglight flush in turf** (Jack's
own, 39 already placed), **lantern** on worked stone above Y100, **soul lantern** on
blackstone below it — the warm-above/cold-below gradient the stair already carries — and
**glow lichen** face-down on a living coat.

**Four things this cost, each of which produced a clean-looking answer and a wrong one:**

- **`is_protected` is the never-OVERWRITE set, not a keep-CLEAR radius.** It holds `wool`
  because wool may be a sculk sensor's silencer; used as a two-block radius it swallowed every
  wool sculpture on the island plus the air around it, so the very cells the pass exists to
  light had no candidate position left and **523 stayed dark**. Keep-clear is `is_used` only
  (rule 10); `is_protected` applies to the one fixture that REPLACES what it sits in.
- **A lichen is only as rude as it is VISIBLE, and that is measured.** The guess was that
  lichen hides on the ladybird's black spots. `blocks.color` says the opposite: `glow_lichen`
  is a mid grey-green (112,131,122), a pale blotch on black wool (ΔLum 105) and invisible on
  the leaf it sits on (lime 32, green 27). Cost rises with the square of that contrast, which
  is what moved the lichen off the shell and onto the leaf.
- **REACH IS ONE LESS THAN THE LIGHT for a flush froglight.** It is not in the air cell, it IS
  the floor — an opaque emitter a course down — so the cell a mob stands in reads 14, not 15.
  Crediting it 15 left **21 cells** dark at the edges of its coverage.
- **IT IS A FIXPOINT, NOT ONE PASS.** A lantern standing in a surface cell makes that cell
  impassable, so the column's topmost standable block is no longer that one — the classifier
  walks DOWN and finds the next, which is a real spawn spot that was hidden under the one being
  lit. Solving once left **3** such cells. Solve, PLACE the fixtures, classify again: round 1
  placed 102, round 2 placed 3, round 3 found nothing.

And one rule that generalises past this design: **turf lying on a coat is dressing on a
sculpture, not ground.** The gecko is lime wool with a single moss block capping its back; read
as turf it earned a flush froglight, which would have glowed out of the animal.

**`mcbuild/nightlight.py` is the one source** for what light passes through, what emits it, and
what a mob can stand on. The solver and the test each kept their own copy for one session and
that was long enough: the solver's set held `dead_bush` and the test's did not, so the test saw
walkable cells the solver had never considered and reported three dark spots in a design the
solver called finished. Neither was wrong; they were grading different islands. Same rule as
`proportions.measure` / `rubric.score`.

**The one group to delete if you dislike it:** 14 of the 26 lichen are on the ladybird and its
leaf, because it hangs in the void with no ground within reach of its shell. Empty that part of
`lichen` in the config and 361 cells go dark again — stated in the config so the trade is
Jack's and not silent.

### And the sync blindness is fixed

`sync` measured progress against `world_out`, the **Y150+ plate cut**, so every cell of a
below-island design counted as *"outside the scan box (unknown)"* and read as unbuilt. It
reported the whole lowland scene at 0% for that scene's entire life — a stair 74% built came
out as 6/2139 — and the velocity slope was out by about four times. `full_out:` in `sync.yaml`
names a full-depth capture and progress and the shop list are measured against it; without one
it falls back to the old behaviour, so nothing else moved.

