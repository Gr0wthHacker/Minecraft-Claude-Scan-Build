# Paste this into a new chat

Continuing work on `C:\Users\Jack\mctest` — the Minecraft island toolkit. **Read `CLAUDE.md` first**;
the ANIMALS section and its "Known-wrong" list are current. `README.md` is the public doc.

Last session fixed the two animal regressions, made within-family distinction measure the models
rather than the config text, and took the animal subsystem from 0 tests to 97. All eight species now
score GOOD; 125 tests green.

| | family | height | score |
|---|---|---|---|
| elephant | proboscid | 34 | 0.87 |
| capybara | caviomorph | 25 | 0.85 |
| giraffe | giraffid | 57 | 0.84 |
| bear | ursid | 30 | 0.83 |
| jaguar | felid | 27 | 0.82 |
| lion | felid | 32 | 0.81 |
| leopard | felid | 26 | 0.80 |
| polar_bear | ursid | 32 | 0.79 |

## Priorities, roughly in order

1. **The bears are boxes.** This is the biggest gap between what the numbers say and what the eye
   sees. Both ursids build as a rectangular slab on four posts — flat top, flat bottom, square
   corners — and `form` scores the brown bear 0.81 because it measures TONE (range, and whether
   luminance follows sky exposure) and nothing measures ROUNDNESS. Render them and you will see it
   at once. Either `form` grows a curvature term or the ursid loft does; probably both.

2. **Place something.** Still the open problem, and now measured rather than remembered:
   - the plate has **no window of even 9x21 entirely at plate level** (Y199–205). Its largest pad
     at relief ≤2 is **5x35**. Nothing fits, including the smallest animal.
   - the void isle's largest pad at relief ≤2 is **11x23**, and the giraffe and jaguar already hold
     the isle's usable ground.
   - `out/island_lower.litematic` has 8 ground columns — it is void.

   Ground-contact pads each animal needs (lowest 4 courses, either orientation):
   giraffe 9x21 · leopard 9x25 · jaguar 9x27 · capybara 11x33 · lion 13x35 · elephant 15x31 ·
   bear 13x36 · polar_bear 15x39.

   **Jack was mid-way through a `lowland` generator** (`configs/lowland.yaml`, `mcbuild/gen/lowland.py`,
   `out/island_lower.*`) when the last session ended — that looks like his answer to this. Ask before
   doing anything else here.

3. **`refine` and `smoothness` are the last two animal tools with no test**, and `quadruped` is
   covered only through the primitives and one end-to-end build.

4. **Deferred by Jack, pick up when he says:** the colour DB samples the TOP face (statues are seen
   from the side — `bone_block`, the giraffe's whole coat, is off by 68) and biome tint is missing
   (20 blocks, including every leaf, extract as grey).

## Things that will bite a fresh session

- **Suspect the reference tables before the code.** Twice now. The ursid proportions were simply
  wrong; and the brown bear's shoulder hump — its real field mark — cannot be built because the
  tables state `withers height` WITHOUT one, so building it drops proportion from 6/8 to 4/8.
- **Never put an absolute block count in a species `build`.** It overrides the derived value and
  the error grows with height. All three felids carried one; `tests/test_taxonomy.py` now forbids it.
- **Never optimise one dimension, or one species.** `refine.py` scores the whole rubric. And a
  family setting must be checked against every member: `relax_fill: 12` gained polar_bear 0.006 and
  cost bear 0.064.
- **Always render and look.** `python tools/views.py "<design>" --zoom 10 --views side,face`. The
  lion's mane was 306 cells, scored `features` 1.00, and was invisible.
- **`tools/compare.py` is the model-against-model check** — shape gap and coat gap per family pair,
  printed apart on purpose. A species carried entirely by paint shows up there and nowhere else.
- **Jack works in the repo in parallel.** Commit only your own files; `git add -A` will sweep up his
  in-flight work. Check `git status` before staging.
- **Line endings:** most files are CRLF, a few (`species.yaml`, `refine.py`) are LF. Writing a file
  with Python's text mode flips them and produces a whole-file diff. Match what is stored.
