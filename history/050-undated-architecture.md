## Architecture

**`mcbuild/`**
- `nbt.py` / `schem.py` — Litematica v7 NBT, straddling bit-packed block states, `Model(ids[y,z,x], palette)`.
- `scan.py` — `.scan.json` sidecars: `load`, `cut` (world-coord sub-box), `merge`, `save_pair`.
- `coop.py` — `progress`, `remaining`, `diff`, `merge_scans`, `shop`, `card`, `place`, `sync`, `storage`.
- `blocks.py` — **what the game says about blocks**, from `data/blocks.json`: 1196 blocks, all 32366
  legal states, and the real colour of 1193 of them. `validate` (is this state legal), `is_full_cube` /
  `supports_top` / `falls`, `nearest` / `ramp` (pick blocks by colour out of the whole registry).
  Regenerate with `tools/extract_blocks.py` when the game updates — see below.
- `audit.py` — placement validity, geometry, cost tiers. Rules **learn from real captures**.
- `learn.py` — mines (block, relation, support) triples into `mcbuild/data/observed.json`.
- `gen/` — one module per generator, registered in `gen/__init__.py`; `belly.py` (island underside),
  `vertical.py` (taproot, shard + the `World`/`Ctx` helpers), `dressing.py` (hem, paths, lightposts,
  entrance, ridelights, apiary, birdlanterns, chimney, footing, altar), `interior.py` (the deck vault),
  `courtyard.py` (the sky-well court), `redstone.py` (item sorter), `lowland.py` (the ground layer at
  Y40, outline traced off the island's own column shadow), plus the older statue generators.
- **Animals** — see the ANIMALS section above; it is the largest subsystem. `quadruped.py` (build),
  `taxonomy.py` (family + height → params), `anatomy.py` (per-family leg and head geometry),
  `loft.py` (superellipse sweeps, surface probing), `coat.py` (voronoi / rosettes / blotches /
  shade), `smooth.py` (relax + roughness), `shell.py` (half-block AND STAIR surfacing: which cells earn a
  partial, and which blocks may supply one). Data in `data/families.yaml`, `data/species.yaml`,
  `data/rubric.yaml`; `data/animals.yaml` is the older per-species reference, still used for
  species that have no family.
- `work.py` — `<design>.work.json`: the design flattened to world-coordinate cells so the mod can diff
  it against the live world without an NBT reader. Written on every `gen`, shipped with the design.
- `history.py` — `out/history.json`, one row per sync, so `progress` has a slope: blocks per sync and
  how many syncs are left.
- `pipeline.py` — `run_config` → source → polish → finish → save; handles `verify_against` and `origin_lock`.

**`tools/`** — analysis, none of it imported by the build

| | |
|---|---|
| `extract_blocks.py` | build `data/blocks.json` from the game's own datagen + jar textures |
| `server_blocks.py` | the server-version allowlist (currently `enforce: false`) |
| `views.py` | shaded orthographic renders at any zoom — `side` / `face` / `rear` / `top` |
| `proportions.py` | measure a build against its family's reference, pose-adjusted |
| `smoothness.py` | spikes / notches / jerk, and a parameter sweep |
| `scale.py` | minimum viable size, and `--measure` for the real quality-vs-size curve |
| `stance.py` | rank poses on behaviour, site, legibility and anatomy |
| `rubric.py` | score against `data/rubric.yaml` |
| `refine.py` | sweep parameters against the WHOLE rubric — use this, not `smoothness --sweep` |
| `compare.py` | built models against EACH OTHER, per family: shape gap and coat gap, kept apart |
| `emerge.py` | cut a design at a plane so a figure comes OUT of a surface, and trim to what is left |
| `panel.py` | the review sheet: silhouette, value, distance thumbs, player bar + both panels' questions |
| `look.py` | the 3D view: eight bearings, cast shadows, corner AO - the working loop for SHAPING |
| `heron.py`, `bat.py` | in `gen/` — the two builds that play to what the medium is good at |
| `views.py` | …and it draws slabs at half height, so half-block work is visible here |
| `plan_merge.py` | composite designs onto a capture |
| `export_navfixture.py` | the island's geometry as a bitmap, for the Java routing tests |
| `corpus.py` | read OTHER people's schematics: shell/detail/palette/state vocabulary, and `--vs` ours |
| `ladder.py` | tonal ladders - which cheap blocks can actually draw a value line against a given one |

`proportions.measure` and `rubric.score` are shared entry points — `stance`, `refine` and `scale` all
call them, so a change to how something is measured cannot drift between tools.

**`chunkscan/`** (client only, `src/client/java/dev/jack/chunkscan/`)
`ChunkScanClient` (commands) · `WorldCapture` (chunks → `Capture`) · `LitematicWriter` (NBT out) ·
`SidecarWriter` · `ScanRunner` (glue + archive) · `Litematica` (reflection bridge, soft dependency) ·
`Markers` · `Storage` + `ContainerWatcher` (container index) · `Highlight` (particles) · `AutoScan` ·
`Wand` + `Fill` + `Rules` (the steak wand — see below) ·
`Designs` (sidecars, design-vs-CAPTURE, build order) · `Work` (reads `.work.json`, diffs against
the live world, and counts the dig list as work) · `Ignored` · `Session`.

