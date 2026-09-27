## Known-wrong, for whoever picks this up

- **The reference proportions are estimates, uncited.** One was simply wrong: the ursid table gave a
  bear a cat's leg clearance (0.469) and a short body, and no amount of geometry work fixed the
  result until the numbers were corrected to 0.346 / 1.230. Suspect the tables before the code.
- **`MIN_BLOCKS`, `COMFORT`, the rubric weights and the grade thresholds are all invented.** Every
  "viable height" and every grade rests on them.
- **~~The colour DB samples the TOP face and has no biome tint.~~ FIXED 2026-08-20** — see
  "The colour foundation" below. `blocks.color(name, face)` now answers per face and the tint is
  applied; `tools/recolour.py` owns it and `tools/extract_blocks.py` delegates to it.
- **Validation is circular FOR COLOUR. It is no longer circular for SHAPE** - `tools/look.py`
  renders real perspective, cast shadows and corner AO, which are ground truth about the form
  whatever the colours are. The colours are still ours: `views.py` and `look.py` both draw with
  the same DB the palette picker optimises against, so judge form and mass offline and judge
  PALETTE in game. Nothing built in this system has been placed in Minecraft and looked at.
- **`giraffe` stands at 57 against a floor of 59** — under-size, which is why `features` scores it
  0.83 (the ossicones and mane are the parts that lose). It is the only animal built in the world,
  so raising it would orphan placed blocks. Listed in `UNDERSIZED` in `tests/test_taxonomy.py`;
  the fix is Jack's call, not a silent one.
- **`refine` and `smoothness` are the only animal tools with no test of their own**, and the two
  build generators (`quadruped`, `coat` patterns) are covered only through the primitives and one
  end-to-end build. Everything else now has one: `tests/test_taxonomy.py` (derivation and the
  no-absolutes rule), `test_rubric.py` (both shared entry points), `test_animal_geometry.py`
  (loft, relax, coat), `test_animal_build.py` (build, poses, anatomy), `test_animal_tools.py`
  (scale, stance, compare, views).
- **Every barrel is still boxy, and now it is measured.** `roundness` (0.10 of the rubric) reads
  the corner fill of the barrel's side silhouette, calibrated against known sections: ellipse 0.06,
  exponent 3 0.31, exponent 4 0.56, exponent 8 0.88, rectangle 1.00. The eight animals sit at
  0.57–0.75 — better than the 0.58–0.83 they started at, but still nearer a brick than a body. The
  cause found so far was the back line being expressed only as a fraction of the hips→withers rise,
  which is 0 blocks for a level-backed family; the body keyframes now carry a depth taper too. What
  remains is the flat TOP and the cross-section, neither of which the taper touches.
- **Half-block surfacing exists but barely applies, and the reason is the coats.** `gen/shell.py`
  halves cells that sit proud of their neighbours, and it works — but it refuses any `rotated_pillar`
  (log, wood, `bone_block`), because the colour DB samples the TOP face and a log's top is end grain
  while its side is bark. Matching `acacia_log`'s orange top to `acacia_slab` drew a bright orange
  line down the bear's back; that is the deferred top-face problem turning real. Most coats ARE
  logs, so only the elephant (112 slabs, all stone) and the giraffe (11) get any at all — the other
  six get none. **The unlock is to build coats out of uniform-textured blocks** (planks, stone)
  instead of logs: `stripped_oak_log` → `oak_planks` costs 3 in RGB and `stripped_acacia_log` →
  `acacia_planks` costs 3, but a naive nearest-match also proposes `glowstone` and `redstone_lamp`,
  which the `plain_blocks_only` gate rejects — so it needs doing properly. It changes how every
  animal looks, so it is Jack's call.
- **The underside pass is off by default** (`shell_under`). Halving an under-surface is the same
  operation but reads as a gap wherever the thing being cut is thin: the elephant's ears are
  flanges and it cut slots through them. The thickness guard catches a sheet lying flat and not one
  standing on edge. It was 17 cells against the top surface's 112, so little is lost.
- **~~No stairs.~~ SETTLED 2026-08-19 — the convention is now known and stairs are in use.** The
  rule rested on two claims and both were false. The capture does not hold ten stair blocks, it
  holds **463**; and their states are not missing, they are in the palette NBT — the earlier
  reading looked at the bare NAME list, which drops properties. Reading them properly off Jack's
  own flight at X-24213..-24210 / Y195–198 / Z30028 (four consecutive straight bottom-half treads,
  all `facing=east`, each one course up and one step east) gives:

      A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D, half=bottom.

  So a flight *descending south* is built `facing=north` — you climb north out of it. Built the
  other way the risers face into the descent and you cannot walk up it, and **our renderer draws
  both identically**, so this is asserted in `tests/test_stairhead.py` rather than eyeballed.
  `gen/stairhead.py` is the first user. `shell.py` can now take them for convex corners, which is
  what it was always ready for.
- **A brown bear cannot have its shoulder hump.** It is the real field mark separating it from a
  polar bear, `hump` exists in the generator, and building one MEASURED WORSE: proportion 6/8 → 4/8
  in tolerance, total −0.06, and the gap to the polar bear SHRANK 0.134 → 0.104. The cause is the
  bounding box again — a hump lifts the back over the withers, and `withers height` is stated in the
  reference tables WITHOUT one. The tables have to state it before the feature can be built.
- **Within-family distinction now measures the models, but only two things carry it.** The lion's
  mane works (shape 0.30 from its nearest sibling, against 0.11 for jaguar-vs-leopard, which is
  correct — they are the same animal). The bears do not: shape 0.16, coat 0.86, so a polar bear is
  a brown bear painted white. `tools/compare.py` prints both halves for every pair.

