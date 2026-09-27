## Reading other people's builds: the download corpus (2026-08-27)

Thirty-one `.litematic` files from other builders, in `~/Downloads`. **They are the only evidence in
this project that this project did not produce.** Everything else here is circular in the way this
file already admits — `views.py` renders with the same colour DB the palette picker optimises
against, the rubric scores against tables invented here, and nothing built in this system has been
placed in Minecraft and looked at by a stranger. `tools/corpus.py` reads a folder of them and
reports the measurements below; run it on the next batch rather than doing an afternoon by hand.

```bash
python tools/corpus.py ~/Downloads --vs out            # the gap table
python tools/corpus.py ~/Downloads --render out/corpus # look at them
python tools/ladder.py --like polished_blackstone_bricks
```

It does not score, rank or grade, and it should not. The corpus is evidence about what is
POSSIBLE; turning it into a number would reproduce exactly the failure the panel review exists to
catch — a build that measures well and cannot be named.

### Two disciplines, separated by one number with no judgement in it

`shell %` is the share of solid cells with an air face-neighbour. It splits the corpus cleanly:

| | n | shell % | detail % | distinct blocks | dominant block |
|---|---|---|---|---|---|
| architecture | 18 | 76–100 | 0–61 | 8–133 | 13–65% |
| sculpture | 13 | 21–53 | **0–2** | 13–125 | 44–89% |

A build at ~50% is a sculpture with rooms in it — `Moon Castle`, a crescent moon 111×105×52 with
towers and an arcade built into the mass — and it is the hardest kind. Nothing in the corpus mixes
the two vocabularies: their sculptures use **no** detail blocks at all, and their architecture is
half made of them.

### THE ACCENT TAIL IS THE GAP, AND IT IS THE ONLY ONE

Measured against our own designs, sculpture against sculpture:

| | n | palette (median) | cells beyond the top 3 blocks | detail % | dominant % |
|---|---|---|---|---|---|
| theirs | 13 | **31** | **18.5%** | 0.0 | 56 |
| ours | 34 | **6** | **5.8%** | 0.0 | 53 |

Same discipline, same dominant share, same zero detail blocks — **five times the palette and three
times the accent mass.** That is the whole difference, and it is not scale: `JAG big` is 57,994
blocks with a 4-block palette and an 8% tail, and it failed exactly as the 27-block jaguar did,
which this file already records. It is not shading either — luminance correlates with ambient
occlusion at only r=−0.15 on their best statue, so they are not running a light model; the accents
are local material events (moss on stone, a paler cheek, a darker seam).

**Our two best sculptures are already the two with the biggest tails** — `Lowland Heron` 27%,
`HERON hd` 28% — which is the finding corroborating itself from inside the repo.

### The value-contrast claim was wrong, three times, for one reason

This file states as fact, in three places, that this economy has almost no value contrast:
*"cracked and chiseled stone brick are within 4 RGB of plain"*; *"blackstone cannot draw value lines
on itself — the family sits within 12 RGB"*; *"`deepslate_bricks` — 51 darker, the one real value
contrast this economy has at cheap-or-ok tier."*

Every measurement is correct and the conclusion drawn from them is false. All three searched inside
**one material family**, where a value ladder cannot exist by construction: a family is one material
shown four ways, and dressing a stone does not change how much light it returns. Searched ACROSS
families at the same hue, the cheap neutral ladder is `white_wool` 236 · `smooth_stone` 159 ·
`stone` 126 · `deepslate_bricks` 71 · `black_wool` 21 — **215 of luminance in five cheap stops**
against the 51 we have been calling our only contrast. Against `polished_blackstone_bricks` the
blackstone family offers 6.9; `tools/ladder.py` finds a four-stop ladder with a **59** minimum step.

`ladder.py` scores a ladder on its SMALLEST adjacent gap, never its range — 236/159/151 has a wide
range and two rungs nobody can tell apart. Three things about its pool that are the same traps this
file already documents, arrived at from a new direction:

- **The pool is witnessed, not remembered.** Over the bare registry it proposes `dried_ghast` and
  `chiseled_cinnabar` — rule 12's exact failure, shipped twice here already. It starts from
  `shell._confirmed()` and `--any` opens it up loudly.
- **A capture beats the allowlist.** `server_blocks.json` is 191 blocks and stale: it does not name
  `deepslate_bricks`, which four designs are built from. `out/island_full.litematic` holds 205
  blocks all standing in this world today. Both are unioned.
- **`protect.is_protected` is the WRONG filter here and it holds `wool`.** Used as "may I build
  with this" it deletes every wool in the game, which is most of this island's sculpture material.
  It is the never-OVERWRITE set — the same mistake `Island Night` made and wrote down. The gate is
  the rubric's `plain_blocks_only`.

**Their ladders are unaffordable and the technique is not.** Terracotta, concrete and quartz are all
`expensive` here, and their sculptures are 70–89% one of them. So the ladder must be found rather
than copied, which is what the tool is for.

### The detail vocabulary, and the half of it that is a mirage

Across the corpus, weighted by cells. The left column is a placement DECISION; the right is
computed by the game from the neighbourhood and **must not be implemented**:

| decided | cells | derived — do not build this | cells |
|---|---|---|---|
| `slab type=bottom` | 7,935 | `stairs shape=*` | 9,292 |
| `slab type=top` | **5,841** | `wall up` + connections | 7,896 |
| `slab type=double` | 3,049 | `waterlogged` | 198,303 |
| `stairs half=bottom` | 6,781 | `distance` (leaves) | 160,019 |
| `stairs half=top` | **2,505** | pane connections | — |
| `trapdoor open=true` | **1,743** | | |
| `trapdoor open=false` | 455 | | |

The derived column is why the ~190 inner/outer corner stairs in the corpus are **not** a technique to
copy: the game resolves `shape` on placement, so our blanket `shape="straight"` is already correct
and nothing needs writing. This file settled the same fact for `work.INTENTIONAL`; `corpus.py`
splits the histogram so nobody re-derives it by reading a block count.

What IS new vocabulary, and we emit none of it:

- **`slab type=top`** — 42% of their non-double slabs. `shell.py` places bottom slabs only.
- **`stairs half=top`** — 27% of their stairs: eaves, soffits, corbels, the underside of an
  overhang. One line in `interior.py` is the only place we do this.
- **`trapdoor open=true`** — **79%** of their trapdoors. An open trapdoor is a thin vertical panel on a
  block face, which is the vertical-slab Minecraft never shipped. Our three trapdoor uses are all
  `open=false`, as wing sheets and planter sides.
- **Entities and tile entities as decoration** — 19 paintings, 5 item frames, 5 armour stands, 120
  signs, 89 banners, 61 chiseled bookshelves. `schem.py` already reads and writes the `Entities`
  and `TileEntities` lists, so this costs no format work; we have simply never used it.

**Already right, confirmed rather than learned:** every one of their 159,983 leaf cells is
`persistent=true`, and so is every leaf we place. Ours would not have decayed.

### A CAT THAT WORKS, and what it does to the retirement rule

`Warm Snooze` is a sleeping ginger tabby: 35×19×36, 10,323 blocks, and it reads as a cat instantly
from all three views. This file's central sculpture finding is *"do not build cats, bears, or
anything whose species is carried by muscle mass"* — and that rule, as written, is too strong.

The corpus contains **no realistically-proportioned quadruped at all**. Every animal in it is one of
three things, and all three are categories this file has already named as ones that work:

- a **single convex mass** — the curled cat, `Stump Perched Owl` (56×54×56), `Holding Flowers
  Rabbit` (31×57×40, an upright chibi). This is the ladybird's category: *"a pattern on one convex
  dome... the dome is a voxel primitive, not a blend of five muscle groups"*;
- a **membrane** — `dragon_slaying`, a 172-block wingspan at 96.6% shell and ten blocks total, a
  one-thick wing sheet with lighter struts. Our sky bird and bat;
- a **columnar figure** — the knight statue, 70% one block with moss weathering.

So the failing variable was never the species. **It is whether the silhouette decomposes into
limbs.** A cat on four legs with a barrel between them is the shape voxels render worst; the same
cat folded into one mass is the shape they render best, and the curl also makes the PLAN the money
view — the view voxels give away free. `Warm Snooze` is 35×36 in plan and 19 tall: wide, low, and
read from above.

**This is a note, not a change.** Nothing in `species.yaml` moved and no retirement was lifted — the
retired list is *"a record, not a threshold"* and reversing it is Jack's call. What the corpus
settles is that the door is narrower than "no mammals" and differently shaped: a curled or seated
mammal whose legs are tucked into the mass is worth one attempt, at a wide low footprint, judged on
its plan.

### Open, and deliberately not acted on

- **The accent tail is the one change that would move every sculpture we have**, and it changes how
  all of them look, so it is Jack's call — the same standing as the "build coats out of
  uniform-textured blocks" question this file already parks.
- **`shell.py` may now take `type=top` slabs and `half=top` stairs.** Its docstring still says
  stairs are barred because *"the capture holds ten stair blocks and none of them records its
  state"* — that was corrected in the stairhead work (463 stairs, states in the palette NBT) and
  the docstring is stale.
- **`rubric.FUNCTIONAL` does not name `shulker_box`**, so a dyed-family expansion admits sixteen
  containers as surface material. `ladder.py` excludes them locally; widening the rubric's gate is
  a scoring change and was not made here.
- **The corpus is a different Minecraft.** Data versions run 2730 to 4903 — roughly 1.17 to 1.21.x,
  with 21 of the 31 at 3955 (1.21) — and the
  builders reach for `pale_oak`, `tuff_bricks`, `chiseled_tuff`, `cherry_*`, `copper_bulb` and the
  `light` block — 267 of them in one build, an invisible light source that would have been ideal
  for `Island Night`. None of it is on a 1.19 server. `corpus.py --vs` flags every block they use
  that no design of ours contains and marks the ones we cannot spend.

