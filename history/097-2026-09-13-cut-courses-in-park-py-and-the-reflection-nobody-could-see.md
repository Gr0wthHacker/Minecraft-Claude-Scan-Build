## Cut courses in `park.py`, and the reflection nobody could see (2026-09-13)

`park.py` generates more cells than any other module in the park and was the only one with **no
detail floor in its tests at all**, which is why it drifted to 2.05%. It is **13.46% now, at exactly
the same cell count** - 11,121 across all kinds and lands, before and after, which is the
cost-neutral claim verified rather than asserted.

    _cut(name, suffix)          `stone_bricks` -> `stone_brick_slab`, `spruce_planks` -> `spruce_stairs`
    _ring_and_core(f, lo, hi)   a proud square split into its ring - each cell with its lean - and its core
    _coping(...)                the ring as stairs: `half=top` is a corbel, `half=bottom` a plinth splay
    _lid(...)                   a roof or ceiling as `type=top` slabs

- **THE COURSE KEEPS ITS OWN FAMILY.** `pal["stair"]` is NOT `pal["trim"]` - on the midway the trim
  is `polished_blackstone_bricks` (45) and the stair is `stone_brick_stairs` (128) - so laying a
  trim ring out of `pal["stair"]` erases the one dark line the trim exists to draw. `_cut` asks the
  REGISTRY for the family's own partial (rule 11), with a plural stem for the bricks and a
  `_planks` stem for the woods, and anything the game does not have - `smooth_basalt`, every wool,
  `dripstone_block` - answers None so the caller keeps its full cube. **A cornice in the wrong
  material is worse than a cornice in full blocks.**
- **A `type=top` SLAB'S TOP FACE IS THE CELL BOUNDARY**, so a roof laid as one is still walked on
  and the merlons still stand on it. That is what makes a lid free rather than a trade.
- **BUT A LANTERN UNDER A SLAB HANGS FROM AIR** - this file's own lowland finding, and the lid runs
  straight over the walkthrough's ceiling. `_hang_light` re-puts a full block at its own anchor and
  runs after the lid, so it self-heals; the test asserts the OUTCOME (every `hanging=true` cell has
  a full cube above it) rather than the ordering, so moving either call fails here instead of
  shipping a room of floating lanterns.

### THE SAWTOOTH: a coordinate-space bug wearing a facing bug's clothes

The first build rendered every string course as a **serrated sawtooth** instead of one continuous
moulding. The facings were uniform along each run, which is what a correct course looks like - so it
read as a facing bug and was not one.

**`_Frame`'s i-AXIS IS A REFLECTION OF ITS d-AXIS, NOT A ROTATION.** `sx, sz = -dz, -dx`. So the
hand-written `left = {"east": "north", ...}` table inside `_Frame.inward` is right for north and
south and **inverted for east and west** - and east is the facing every test defaults to, so every
test agreed with the bug. Two consequences:

- my ring leaned outward on half its runs, putting each stair's step profile ALONG its own run
  instead of across it, which is exactly what draws a sawtooth;
- and **every cornice `_cornice` has ever laid on an east- or west-facing building leaned the wrong
  way** - pre-existing, on half the park.

It was invisible until `render3d.subdivide` learned to draw a stair's real shape: before that, this
repo's own recorded rule was that *our renderer draws a stair the wrong way round identically to a
right one*. The renderer earning its keep for the third time.

`inward` derives the i-axis from the frame's own `(sx, sz)` now (`_DIR` is the inverse of `_STEP`)
rather than from a table, and `_ring_and_core` REUSES `inward` rather than carrying a second copy of
the rotation - which is what I should have done first and is the whole of why this happened.

**Three new tests, each verified RED against HEAD before being kept**: a 10% detail floor over every
kind and land, the lid-and-lantern pair, and `..._leans_INTO_the_mass_at_every_facing` parametrised
over all four facings, because the facing is where it was wrong. The lid test's first version was
VACUOUS - it asserted that *some* `type=top` slab existed, which the gate's six-cell ticket counter
already satisfied on the old code; it asserts a whole COURSE of at least 40 now.

**No new test failures.** The 22 in the affected suites are all pre-existing and verified so by
running with these changes reverted: 16 `test_park.py::...[*-paths]`, one
`test_every_measured_trough_gains_something_to_look_at`, and five lamp-arm tests belonging to
another stream's in-flight `parkways.py` work.

### Still open

- **`smooth_basalt` is 15.4% of `Park Buildings` and has NO slab or stair at any price.** It is
  `path`/`trim` in prismworks and the `KERB` in two more modules, so a sixth of the build cannot
  take detail at all. Swapping it for `polished_deepslate` or `deepslate_bricks` would open it up -
  that is a look change across a whole land and is Jack's call, not a silent one.
- **The other building modules were surveyed and not touched**: `civic.py` (`_plinth` base and cap),
  `arcade.py` (fascia boards, plinths), `frontiertown.py` (fascia, boardwalk kerb) all still lay
  full-cube trim. `prismworks_builds.py:_cornice`/`_skirt` and `midway_builds.py` were already
  correct and are the pattern to copy.
- **Nothing here has been placed in game.** Judge form off `render3d`, palette in world.

