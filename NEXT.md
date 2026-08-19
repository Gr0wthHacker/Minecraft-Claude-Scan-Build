# Paste this into a new chat

Continuing work on `C:\Users\Jack\mctest` — the Minecraft island toolkit. **Read `CLAUDE.md` first**;
the ANIMALS section and its "Known-wrong" list are current and detailed. `README.md` is the public doc.

Last session built the animal system: five families (`data/families.yaml`), eight species
(`data/species.yaml`), per-family leg/head geometry (`gen/anatomy.py`), a quality rubric
(`data/rubric.yaml` + `tools/rubric.py`), and sizing/stance/refine tools. 28 tests green.

## Priorities, roughly in order

1. **Fix the two regressions.** `jaguar` (0.73) and `polar_bear` (0.71) are tuned for the geometry
   that existed before `anatomy.py`. Run `python tools/refine.py /tmp/<sp>.yaml --species <sp>` and
   apply. Should be quick.

2. **Make within-family distinction actually work.** This is the real open problem. Built silhouettes:
   lion vs jaguar **0.024**, bear vs polar bear **0.016** — the shapes are identical by design, so the
   mane and the skull are supposed to carry the difference and neither does. The lion's mane is 304
   cells and still blends into the shoulder instead of having an edge.

3. **Test the tools.** Zero coverage on all seven (`rubric`, `scale`, `stance`, `refine`,
   `proportions`, `smoothness`, `views`) and on `taxonomy`, `coat`, `loft`, `quadruped`.
   `proportions.measure` and `rubric.score` are shared by three tools each and nothing asserts them.

4. **Place something.** Nothing built this session exists in the world, and the validation is circular
   (the renderer uses the same colour DB the palette picker optimises against). The void isle is full;
   the plate's largest flat pad is 13x13; an elephant's contact footprint is 15x29. Needs a decision
   from Jack: level a pad, extend the void isle, or build below the plate.

5. **Deferred by Jack, pick up when he says:** the colour DB samples the TOP face (statues are seen
   from the side — `bone_block`, the giraffe's whole coat, is off by 68) and biome tint is missing
   (20 blocks, including every leaf, extract as grey).

## Things that will bite a fresh session

- **Suspect the reference tables before the code.** The ursid proportions were simply wrong (a bear
  with a cat's leg clearance) and no amount of geometry work fixed the bear until the numbers were.
- **Never optimise one dimension** — use `tools/refine.py`, which scores the whole rubric. Sweeping
  smoothness alone inflated a bear until the silhouette test called it an elephant.
- **Always render and look.** The rubric passed three animals at GOOD that were visibly the same
  animal. `python tools/views.py "<design>" --zoom 10 --views side,face,top`.
- `mcbuild gen` writes to `out/`; `--ship` also copies to the schematics folder. Tools resolve a bare
  name to whichever is newer, so a missing `--ship` used to serve stale files.
