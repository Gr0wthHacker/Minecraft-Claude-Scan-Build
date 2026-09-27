## The deck floor (2026-08-19)

`configs/deck_floor.yaml`, `mcbuild/gen/deckfloor.py`. 427 blocks, 84 of which replace something; 0 new problems in context.

**The entrance audit is what produced this.** The taproot stair head walks correctly — deck 195.0 →
four treads → undercroft 191.0 → 7 standing cells at the shaft lip — but it does not READ, and no
amount of further detail on it would fix that. Its apron is grey on a grey field. **An entrance
cannot be the figure when the ground is the same tone and equally busy**, so quieting the floor is
the other half of building the entrance, not a separate job.

**The deck, measured.** 2,145 columns on the Y194 course:

| | cells | blobs | |
|---|---|---|---|
| dressed brick | 1,060 | — | the intended floor |
| green | 499 | **63** | ONE real 269-cell moss farm + 230 cells of scatter |
| rough stone/cobble | 266 | **63** | biggest blob 58; the rest scatter |
| vine | 236 | **127** | 127 blobs averaging under two cells |

~730 cells in 113 blobs are noise, not design; only **44%** of the floor is walkable with three
courses clear; **120 chests** still stand on it; lighting is **37 torches to 10 lanterns**.

Three things this cost, each of which produced a plausible wrong answer:

- **The deck is the biggest connected BLOB of the course, not the course.** Taking every cell
  sweeps in 97×93 of island underside — belly scraps, rim shelves — and the edge course alone came
  to 819 cells with **59 free-floating clusters** drawn round islands two cells wide. Deriving the
  blob (2,145 → 1,725) keeps it a deck design with no hand-written box.
- **A rectangle will not wall the moss farm.** It is a WORKING farm — 29 ice, 12 water, glow lichen —
  and it sits on an irregular lobe: the box one cell out is **58% air**, two cells out **70%**. A
  rectangular room floats over holes and cuts the water. The wall follows the farm's own dilated
  edge and lays only where there is floor under it — **41 cells**, because most of the farm's
  boundary is against open air at the deck's edge, and you cannot walk in from a drop.
- **`plan_merge` fills empty cells only.** Comparing before and after through it showed a 30-cell
  change, *all of them `air -> something`* — that is the tell. A design whose job is to REPLACE is
  invisible to it. Composite with overwrite to see a repaving design.

### The border was wrong twice, and there is now no border

Jack placed the first build and said the floor was "all messed up". It was, for two reasons that
only a real placement exposes:

- **"Every floor cell with a missing neighbour" is NOT the deck's outline.** This deck has **25
  interior holes**, so 269 of the 529 rim cells were HOLE edges and the border came out as dark
  rings round **94 separate interior gaps** — scribbles across the whole floor. The outline is the
  boundary against the flooded OUTSIDE, which is 260 cells, not 529.
- **The deck's edge is planted, and the border was eating it.** 111 vine cells sit on the floor
  course and 107 of them are on the rim; 92 of the 260 outer cells are vine and 64 more are moss.
  The first build turned them into solid dark blocks — stripping the hem's planting and filling a
  see-through edge with stone. **`vine` is in `KEEP` now**, never resolved and never bordered.

With both fixed, a hard edge course lands on **82 of 260** outer cells — the rest are planted or
carry fixtures. A third of a line is a dashed scribble, so `border_ring: 0` and the deck has no
border at all. What survives is what was always doing the work: **252 scatter cells resolved, 64
cells of zone band, and the moss room** — 427 blocks, and only **84 of them replace anything**,
against 701 and 492 in the first build.

**The lesson worth keeping: a remedial design's damage is measured in what it REPLACES, not in what
it places.** 492 replacements read as vandalism; 84 read as a repair.

**Still open on the deck:** the 120 chests (the Store Hall's 68 slots are built and waiting), the
37 torches, and the 44% walkable figure — all of which want the chest move done first.

### The workshop pass (2026-08-19)

A full audit of the deck with both designs applied produced three moves, ranked by effect per
block. All three are built.

**What the audit found.** 989 floor columns. The floor was already fixed (80% stone brick + 9%
deepslate = 89% in two materials, walkable 44% -> 62%), which left the two surfaces that actually
say *unfinished*: **29% of what is overhead was raw cobblestone** and another 8% moss, and the deck
was lit by **20 torches against 8 lanterns** — with 95% of the floor already within 7 of a light,
so the torches were costing nothing but the impression. And standing at the entrance mouth looking
north there were **seven blocks of nothing at head height**: the entrance was the only vertical
event in the room, so you did not discover it, you simply arrived at it.

| | before | after |
|---|---|---|
| raw cobble overhead | 29% | **0%** |
| designed soffit overhead | — | **32%** (20% panels, 12% grid) |
| lanterns : torches | 8 : 20 | **18 : 14** |

- **The soffit is NOT flattened deck-wide.** Across 1,725 columns the ceiling genuinely steps, and
  forcing one plane would either bury the structures under it or leave a shelf. What is fixed is
  the MATERIAL, and the coffer grid is set in WORLD coordinates so it stays aligned across a step.
  Finished ceilings are left alone; only the quarry ones are replaced. (Inside the entrance, which
  is one room, the soffit *is* one flat plane — that is the difference between a room and a deck.)
- **A wall torch cannot become a lantern.** A lantern does not mount on a wall, so it is only
  swapped where there is a block overhead to hang from — **14 are left standing** rather than
  deleting someone's light, and the count is reported.
- **`KEEP` protects torches from the FLOOR pass and the relight replaces them anyway.** That is a
  real exemption, so it is narrow and asserted: a cell written over a torch must be a lantern and
  nothing else. Widening `KEEP` would be the wrong fix — it is what stops the next pass eating a
  hopper.

**Still open:** the 112 chests (Store Hall's 68 slots are built and waiting), the 14 wall torches,
and 62% walkable — all three of which are the chest move.

### The soffit was the worst thing on the deck, and every check passed it (2026-08-20)

Jack placed the workshop pass, looked at it and said the wood lines wrapping the workshop were
awful. They were. The soffit's coffer grid was `dark_oak_wood`, and measured off the 03:55 capture:

| | |
|---|---|
| grid runs drawn | 215 |
| …of one or two cells | **184** |
| …lone blocks with no grid neighbour at all | 168 |
| dark oak standing in world | 70, **all** on a grid line (43.75% would be chance) |
| …with no wood neighbour | 27 |

**It is not a grid, it is confetti** — and in the loudest block available, because dark oak against
`smooth_stone` is the largest hue contrast on this deck.

**Nothing in the pipeline could see it, and that is the transferable part.** Every check the design
had is PER-BLOCK — is the state legal, is it in 1.19, is it spendable, is it affordable, does it
have support — and it passed all of them, 376 cells, zero problems, zero expensive. The failure is
PER-RUN. A block is only as good as the line it is part of, and nothing measured lines.

**A SOFFIT BELONGS TO A ROOM, NOT TO A DECK.** That is the actual error; the block was a symptom.
The pass drew over whatever happened to be overhead, and off the capture that is not a ceiling: of
1,224 columns with a real underside, 421 are raw enough to treat, and those 421 are **25 lacy
patches at SIX heights** (Y197–202). The largest is 92 cells and fills **40% of its own bounding
box**. The taproot entrance already had this right — *"inside the entrance, which is one room, the
soffit IS one flat plane — that is the difference between a room and a deck"* — and the deck-wide
pass ignored it.

It is also the same finding as `border_ring: 0` one surface up: **a third of a line is a dashed
scribble, so do not draw the line.** The design had already learned it on the floor and then made
the identical mistake on the ceiling.

**And it is the same mistake `gallery.py` made and REMOVED, one file over, for the same stated
reason** — to move a palette number (wood 7% against the plate's 23%). The gallery's own comment
says it: *"the timber was only ever here to move a palette number, which is the wrong reason to put
a block anywhere."* The number then reappeared in the soffit's docstring as the justification.
**The wood-percentage target is deleted as a goal.** The deck's ceiling is the island's own rock, so
it is dressed in the island's own rock: `smooth_stone` panel, `deepslate_bricks` line — 51 darker,
the one real value contrast this economy has at cheap-or-ok tier, and the block the stair head, the
zone bands and the void tower already draw with, which is what makes them one hand.

#### What is now in the code

- **`soffit: False` deck-wide**, with the measurement above in the docstring. The machinery stays
  and is correct — point it at a ROOM and turn it on.
- **A run gate** (`soffit_min_run`, default 4). A grid cell whose run along its own axis is too
  short demotes to PANEL, never to a lone dark block. This is `gallery._MIN_RUN`, one surface up.
- **A patch gate** (`soffit_min_patch`, default 8). Re-materialising a 3-cell island of cobble into
  smooth stone is scatter, which is what this same design's floor pass exists to remove.
- **A reclaim pass** (§6b), because the fix had to undo the damage and could not.

#### Four traps inside the fix, each of which produced a clean audit and a wrong build

- **A litematic cannot express removal, and the pass could not SEE its own mistake.** `dark_oak_wood`
  is not in `soffit_raw`, so the 70 blocks were invisible to every gate; and 50 of them have since
  had moss placed under them, so they fail the two-clear-courses room test as well. Left alone they
  would have stood for good. They are healed directly into their commonest **solid** same-course
  neighbour — 57 `smooth_stone` and 10 `stone_bricks` against the wood's own 28 — so each turns back
  into the plane it interrupted rather than becoming a hole in a ceiling.
- **The run gate's AXIS was inverted, and the inversion shipped.** A line at constant X runs along
  **Z**; scoring it along X measures each cell ACROSS its own line, so every run came out as 1 —
  and isolated cells then sailed through the threshold. It also made the *diagnosis* too
  pessimistic: the first sweep said no grid works at any spacing, and with the axis right a grid on
  the one big patch is 29 cells with runs up to 16. **A measurement and the code that acts on it
  sharing a bug agree with each other perfectly.**
- **Reclaim scope is not build scope.** `floor` is where you can stand (892 cells); the deck is
  every column of the course (1,779). Anything about what is OVERHEAD must use the deck — scoping
  the reclaim to `floor` reached 17 of 70. Eleven more sit above rim columns carrying no floor
  block at all (the pass placed them when the floor below them still existed), five of those out on
  the east arm past any sane dilation, so it sweeps the deck's bounding **box**. That is safe only
  because **the gate is the SIGNATURE, not the footprint**: a cell on the grid line.
- **A fix must not be coupled to the setting it is fixing.** The reclaim read `soffit_grid_at`, so
  retuning the grid to 5 silently dropped it from 70 blocks to 26 — the wood is on a 4-grid and
  nothing else knew that. `reclaim_grid_at` is history and does not move.

`tests/test_deckfloor_soffit.py` pins all of it: no wood anywhere, no drawn grid cell without a
grid neighbour, both gates firing, all 70 reclaimed, and the reclaim finding nothing when the
signature is moved off every real coordinate.

**Shipped: 79 blocks, all remedial** — 70 wood healed to stone, 6 zone band, 3 relit. 0 new problems
in context, 0 wood placed, 0 expensive.

**Still open — Jack's call.** The soffit works on exactly ONE patch: 92 cells at **Y201**, over
X−24205..−24194 / Z29994..30012, which is the entrance hall — the room. At `soffit_min_patch: 30`,
`soffit_grid_at: 5`, `soffit_min_run: 4` it draws 63 `smooth_stone` panels and **29
`deepslate_bricks`** grid cells, runs up to 16, only 7 demoted, and takes the design to 171 blocks.
That is a real coffered ceiling over the one place that has a ceiling. Everywhere else stays rock.

**~~Pre-existing, found while running the suite:~~ FIXED 2026-08-23** — `configs/store_hall.yaml`
crashed the pipeline with `ValueError: nothing built` (100% built, emitted nothing, `World.canvas`
raised). The day Jack finished placing the Reaching Root it hit the same wall, and the pipeline now
reports such a design COMPLETE (`Result.complete`) instead of raising.

