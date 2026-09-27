## Park Complete: no tuff, and no heron (2026-09-07)

Jack: *"park complete cant have tuff and we need to remove the heron"*. Two unrelated faults, both
of a class this file already names.

**TUFF IS A BLOCK THIS SERVER CANNOT SUPPLY, AND EVERY CHECK IN THE PIPELINE PASSED IT.** It is
`ok` by the economy table, it is in the provisional 1.19 allowlist, `blocks.available` says yes -
and measured against the captures of the real world (`island_full`, `island_now`) it stands in
**ZERO cells**, because tuff generates in deep cave and a skyblock has no deep cave. That is rule
12 from a fourth direction: *ask the WORLD, not the table*. 6,408 cells of it were shipped, all of
them ROCK BODY - `PF Mine Ridge` 2,103, `PF Prism Downs` 2,829, `PF Plateau Vale` 1,050, the Bone
Bed, the Cutting Yard, the Diggings and the coaster's ballast.

`mossy_cobblestone` is what `palette.affordable_like("tuff")` answers on its own - the closest
block that is cheap, WITNESSED here (9,172 cells standing in the world) and not a machine, at 22.3
RGB - and it keeps tuff's JOB in every body it appears in. Tuff was always the LIGHT tone against
dark rock (the ridge's mid band at 12%, the downs' "pale bed and the only real highlight", the
Cutting Yard's tread) and mossy cobble is lighter still, 115 against 108. It is hue-distinct from
the two tones it now stands beside - 43 RGB from `granite`, 55 from the `moss_block` turf - so no
ladder collapses into it. **The park's cobblestone ban is about BUILDINGS, not terrain**: Jack
threw out a park that was 17.7% cobblestone and every building generator carries that ban in its
own tests, while the cells this touches are rock body, where the park already spends 18,185
cobblestone as `rock_c`.

**IT IS A COMPOSITE SWAP, BESIDE THE ANDESITE ONE**, for the reason `declutter.py` was written:
seven generators emit tuff, and turning it off upstream is one decision taken seven times and
remembered seven. `SWAPS` is now `{andesite: dripstone_block, tuff: mossy_cobblestone}`, applied by
`tools/park_place.py` at the moment it writes `Park Complete` and `Park Buildings`, and reversible
in one line.

**THE SIGNAL HERON IS RETIRED, AND IT HAD NO LOT TO DELETE.** The bird was a single `gen: heron`
source inside `configs/park_ways.yaml` at offset [26, 1, 176] - 1,790 cells of wool on the Claim
Line reach - so the ground layer was the only place it existed. `mcbuild/gen/heron.py` is
untouched and still builds; the lowland flamingo runs on it and `isthmus.py` still lists it as a
siteable creature. **A retirement is a RECORD, not a deletion**, and one line is exactly the kind
of thing that gets put back, so `test_the_ground_layer_builds_NO_HERON` is the tripwire.

Three things still pointed at it and all three are the leftover class the signage audit was
written about:

- **`park_lots.py` said the bird "still stands"** in two places, having been written when only its
  old artifact and its lot were superseded.
- **`parkpacket.py` carried two camera views named for it.** A camera named for a retired module
  renders an empty lawn under its own caption, which reads as a broken renderer rather than as a
  module nobody placed.
- **THE FEATURE LOT IS KEPT, AND ITS JOB CHANGED RATHER THAN LAPSING.** V34-60 x U174-210 lies
  wholly inside `PF Water Claim Lake` (V24-112 x U173-211), and `park_water.put` treats a paved
  cell, a lamp mast or a bench inside the lake as an ERROR naming the cell rather than a silent
  skip - so deleting it with the bird would have freed the ground layer to furnish the middle of a
  lake. Renamed `lake garden` for what it now protects.

**Still open, and deliberately not touched:** the lake's own `heron_feet` (two columns kept dry on
its shoal) and `heron_clear` (a 16 x 13 rectangle kept unplanted) now reserve ground for nothing.
They are one line each to zero - `pf_water_wyrm_garden.yaml` already carries them empty - but the
lake's `world:` is `Park Complete`, which CONTAINS the lake, so regenerating it is the
self-reference trap and wants a pre-lake context rather than a config edit. `park_attractions.MAJOR`
also still lists the heron among fifteen names, nine of which were already retired modules; that
roster is its own audit.

    Park Complete   526,385 -> 524,033 blocks . tuff 6,408 -> 0 . heron box EMPTY
    Park Buildings  tuff 0

