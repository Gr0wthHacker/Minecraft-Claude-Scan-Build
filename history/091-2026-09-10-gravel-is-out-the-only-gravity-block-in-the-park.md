## GRAVEL IS OUT: THE ONLY GRAVITY BLOCK IN THE PARK (2026-09-10)

Jack: *"remove all gravel and swap for something else."* It went through `declutter.SWAPS`, beside
`andesite` and `tuff`, and it fails BOTH of the rules that killed those two.

    gravel -> cobblestone     2,209 cells in Park Complete, 2,281 in Park Buildings, now 0

### RULE 13, AND IT IS THE PARK PLATE THAT MAKES IT UNFIXABLE UPSTREAM

A generator that uses gravel is careful with it. `mineridge` places it as *"a crust material: the
top course of a column that is solid to the ground and never a face, so a falling block never has
air under it"* - and that invariant belongs to ONE generator over ITS OWN model, which is not the
model that ships. Measured on the shipped composite, **eleven gravel cells stand on air**.

**TEN OF THE ELEVEN ARE ON THE PARK PLATE, which is the case no generator can be careful about:
the park is ONE COURSE OF GROUND AT Y202 OVER OPEN VOID**, so every cell of it has air beneath it
by construction and a gravity block laid on the ground falls off the world. They are the Claim
Lake Menagerie's pond bed at V135-142 / U197-210. The eleventh is high in the terrain at
(97553, 214, 80456) and **no source module owns that cell** - it arrives from the composite's own
passes, which is the other half of the same point. Nothing re-checks a gravity block after
composition and nothing can; the cure is not to carry one into a composite at all.

**That measurement was nearly got wrong the same way twice in one session.** Air under a cell at
Y202 is NORMAL for this park - it is what a one-block plate over void looks like, and the first
task of the day had already caught me reading it as a fault. It is normal for a SOLID block and
fatal for a gravity block, and those are different questions about the same reading.

### RULE 12, AND IT IS `tuff`'s CASE EXACTLY

Cheap by the economy table, in the provisional 1.19 allowlist, spendable - so every check in the
pipeline passed it. Measured against the real captures it stands in **SIXTEEN cells of the whole
world**, against cobblestone's 15,897. `mcbuild provision` put it **1,793 short with no recipe and
no price**, classified FARM, which is the resolver saying there is no route to it at all.

### `cobblestone` COSTS NOTHING TO TAKE, AND ONE THING IS LOST THAT CANNOT BE MEASURED HERE

It is what `palette.affordable_like("gravel")` answers - the closest block that is cheap, WITNESSED
here and not a machine - at **4.1 RGB** on the side face, L127.3 against gravel's L128.1. Gravel
was never a rung in any bedded ladder: the Mine Ridge's runs `cobbled_deepslate` 77 / `moss_block`
101 / `granite` 112 / `stone` 126 / `diorite` 188 and gravel is not in it, and the claim row's own
ladder already had gravel 128 and cobblestone 127 as two names for one tone. Nothing collapses.

**What is lost is TEXTURE, which is the one thing the colour DB cannot see.** Gravel is visibly
granular and cobblestone is visibly lumpy and both average to the same grey - this file's oldest
recorded circularity, arriving in a new place. Judge that in world.

**And it is a SWAP, not a removal**, because a crust is the top COURSE of a mass: taken out rather
than replaced it leaves 2,209 holes in the surface of the terrain it was covering.

**The park's cobblestone goes 2.27% -> 2.77%.** The ban is on BUILDINGS - Jack threw out a park
that was 17.7% of it - and every one of these cells is terrain: Mine Ridge 997, the coaster's
ballast 518, the Diggings 576, the Bone Bed 407, the Plateau Vale 233.

### The swap runs BEFORE the hollow pass, which matters

`park_place` runs declutter -> `unseen` -> the printable stitch. `unseen`'s gravity guard is
derived from `blocks.falls` over the model's OWN palette, so once the swap has run it correctly
finds nothing under a gravity block and the ~348 cells it was holding back become hollowable. Both
`gravel` and `cobblestone` are in `TERRAIN_BLOCKS`, so the carve mask does not move.

`tests/test_declutter.py` gained the guard for the NEXT swap somebody adds, which is where this
would actually happen again: **no swap target may itself be a gravity block**, and every target
must be cheap and reachable by `palette.affordable_like`.

### Still open, measured rather than acted on

- **SEVENTEEN SAND CELLS, ALL OF THEM STANDING ON AIR**, in the same Menagerie pond bed as the ten
  gravel ones. It is the identical fault in a different block and one line to fix
  (`"sand": "..."` in `SWAPS`) - but sand is a BEACH and cobblestone is not, so what it should
  become is a look decision rather than a mechanical one. Jack's call.
- **`test_two_lamps_never_bunch` FAILS AT HEAD** and is not this work's: run against
  `git show HEAD:configs/park_ways.yaml` it reports the identical seven bunched pairs. Two walk
  verges four apart both take a lamp at the same U (V72/V76 at U228 and U243, V75/V79 at U357 and
  U371), and the eight-block anti-bunch rule is only consulted by the NUDGE - a lamp placed at its
  own station never asks. The Prism Well's keep-clear disc takes it from **seven pairs to four**.
- `Park Complete Ready` was regenerated with the composite (301,793 cells, 70% coverage); it is
  written by `mcbuild provision --package --ship` rather than by `park_place`, so it does NOT
  follow a reship on its own and will go stale again the next time the park is shipped.
