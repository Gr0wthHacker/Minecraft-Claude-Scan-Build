# mcbuild

Generate, downscale, cheapen, hollow, audit and render Litematica schematics for a
skyblock island. Everything we built for the island lives here as reproducible
configs; new designs are a YAML file or an image away.

Zero exotic dependencies: numpy, Pillow, PyYAML.

```
python -m mcbuild --help
```

## Quickstart

```bash
# regenerate a design from its config, audit it, write out/<name>.litematic + .png
python -m mcbuild gen configs/fox.yaml

# ...and copy it straight into the Litematica schematics folder
python -m mcbuild gen configs/tower.yaml --ship

# tweak a parameter without editing the file
python -m mcbuild gen configs/tree.yaml --set params.trunk_height=20 --set params.lantern_strings=24

# derive from a download: downscale 2x, swap expensive blocks, hollow, audit
python -m mcbuild downscale "C:/.../schematics/Some Statue.litematic" --factor 2 --cheapen --hollow

# what is this file made of, is it valid, what would it cost?
python -m mcbuild info  file.litematic
python -m mcbuild audit file.litematic          # exit 1 if anything is wrong

# look at it
python -m mcbuild render file.litematic --views face,side,top
python -m mcbuild render file.litematic --ascii face   # block map: ground truth for faces

# statue from an image reference
python -m mcbuild fromimage ref.png --height 27 --depth 10 --hollow 2
```

## What the audit checks (every time)

* **placement validity** — vines have an attachment, chains/lanterns hang from
  something, ladders have a wall behind, carpets/plants sit on the right block,
  dripstone/roots hang from solid, torches on solid
* **geometry** — connected components (floating fragments), sealed cavities
* **cost** — bill of materials split into `cheap` / `ok` / `expensive`
  (terracotta, concrete, quartz, glass…) with the expensive list called out
* **symmetry** (optional) — mirror symmetry of the front face

`gen` fails (exit 1) if the audit has problems. Nothing ships broken.

## Skyblock economics baked in

`palette.tier()` knows what's cheap here (wool, snow, moss, wood, stone family,
vines, lanterns) versus expensive (terracotta = 10 grass each, concrete, quartz,
glass). `cheapen` swaps expensive → cheap **preserving hue** so the look survives
(`orange_terracotta → orange_wool`, `white_concrete → snow_block`,
`lime_concrete → moss_block`, `quartz → snow`, …). Every config runs it by
default; use `finish.keep: [orange_concrete]` for a 4-block beak you want to keep.

## Configs

Two kinds:

**Generated** (`gen: <name>` + `params`) — parametric designs: `tree`, `fox`,
`tower`, `underside`. Every constant that used to be hardcoded is a param; run
`--set params.key=value` to override.

**Derived** (`source: <file>` + `downscale` + `polish` steps) — a download
turned into something usable. See `configs/owl.yaml`.

Both then run the same finish chain: `cheapen → hollow → drop floaters → audit
→ save (+ contact sheet)`.

### Underside: fit to what you already built

The `underside` generator has an `under:` mode. Save the area beneath your island
(Litematica: select the box from the surface down ~25 blocks, include air, save),
then:

```yaml
gen: underside
params:
  under: island_under.litematic     # your saved area, in the schematics folder
  cap_depth: 16
```

The belly is generated per column **directly below the lowest existing block in
that column** — it hugs walkways, dips under stairs, and never overlaps a block
you placed. Output has the same x/z origin and width as your saved area; paste it
at the same corner (it's taller: the extra rows are below).

## Capturing the real island (chunkscan)

`chunkscan/` is a client-side Fabric mod: in game, `/cscan island` saves every loaded chunk
around you as `island.litematic` (air included) + `island.scan.json` (server, dimension, world
origin, chunk coverage). Then:

```bash
python -m mcbuild scan island --info                       # what's there, is coverage complete
python -m mcbuild scan island --cut X1 Y1 Z1 X2 Y2 Z2 --out out/piece.litematic   # world-coord sub-box
```

The audit's placement rules learn from real captures: `python -m mcbuild learn island` mines
every (block, relation, support) triple the server allowed into `mcbuild/data/observed.json`
(lanterns on fences, carpets on leaves, upper-half tall grass…). Anything seen for real passes;
anything attached to air is reported as an anomaly, never learned. Feed it more captures as you
visit more builds.

Build/deploy instructions in `chunkscan/README.md`. Point `underside under:` at the scan file
instead of a manual Litematica selection.

### Belly: rock mass fitted to the real island

`gen: belly` (see `configs/belly.yaml`) reads a capture and hangs an eroded, hollow rock shell under
it. Default `mode: hug`: rock follows the built underside — plate, lower deck, bee house, rail
supports — hanging from the lowest built block in each column after a `side_gap` min-filter, so rock
never rises beside anything that hangs lower and never fronts a wall build. Depth by distance to the
real footprint edge (`depth_min` at the rim → `depth_max` inland, low-frequency noise); anything above
the plate band (`encase_below` + `plate_band`) is a surface build and ignored. `mode: encase` instead
turns what hangs below the plate into a padded cavern (lumpy on busy undersides — you probably want
hug). Trim knobs: `sub_plate: none|skin|full` (+ `skin_boxes`, `skin_depth`) for what hangs below the
plate, `min_plate_width` and `cut_boxes` to leave bridges/necks bare, `depth_min`/`wall` for the rim
and shell thickness. `exclude_boxes` skips decor you'll re-hang. `finish.verify_against` composites the result onto
the capture and audits **that** (overlap must be 0). Output ships with a `.scan.json` paste origin.

### Vertical set (fitted to the capture)

`gen: taproot | shard | stream` (configs of the same names; `clouds` exists but was cut in the design audit). All take `under` (+ `belly`
where they hang from it) and world coordinates, and verify in context; `verify_against` accepts a list
(capture + already-designed belly). `stream` reports a `dig` list in its sidecar (moss/plants the player
removes so the water sits at lawn level) and refuses routes over air or non-diggable blocks.

## Co-op tooling (mcbuild + chunkscan 0.2)

```bash
python -m mcbuild progress "out/Island Belly Full.litematic" out/Taproot.litematic --world island   # % built, what's left, deviations
python -m mcbuild remaining out/Taproot.litematic --world island                                   # export only the unbuilt cells (same origin)
python -m mcbuild diff schematics/scans/island_20260817-2126.litematic island                       # what changed between two scans
python -m mcbuild merge scanA scanB scanC --out out/master.litematic                                # union; newest scan wins per loaded chunk
python -m mcbuild shop out/Taproot.litematic "out/Shed Shard.litematic" --world island              # stacks / shulkers, minus what's built
python -m mcbuild place out/Taproot.litematic --server skyblock.net                                 # Litematica placements at the right origin (game closed!)
```

chunkscan 0.3 also captures entities (item frames, armor stands, paintings, boats) and archives every scan
as `schematics/scans/<name>_<yyyyMMdd-HHmm>.litematic` so history can be diffed. Dressing kits: `chimney`,
`footing` (configs `chimneys.yaml`, `footings.yaml`).

## Daily loop

```bash
python -m mcbuild sync            # after /cscan: cut latest scan, regenerate remaining belly, progress + shop for every design, learn
python -m mcbuild card <design> --world out/island_now.litematic   # one PNG for chat
python -m mcbuild place <designs...>                                # Litematica placements (game closed)
```

`profile.yaml` holds the machine/server paths (teammates edit that, nothing else). `sync.yaml` lists which
designs get regenerated / reported. Optional `prices.yaml` ({block: coins}) turns `shop` into a cost sheet.
Verification also reports free-floating clusters (need a temporary scaffold) for every design.
`python -m mcbuild storage` shows what the mod has indexed inside your containers; `shop --have`
subtracts it from the shopping list. See `CLAUDE.md` for the full picture.

Dressing kits: `hem` (rim), `paths` (+ `lightposts`, terrain-following, MST over A* routes that reuse existing
path fragments; sidecar has the dig list and torches to pull), `entrance`, `ridelights`, `apiary`,
`birdlanterns`, `chimney`, `footing`.

## Image references — honest scope

A single image gives a **silhouette and colours**, not depth. `fromimage` builds a
correctly-proportioned, correctly-coloured, cheap-material statue *starting point*:
silhouette extrusion with a lofted (rounded) depth profile, pixels quantised to
the nearest cheap block by colour, optional mirror, optional hollow shell. It's a
20-minute head start, not a finished model — expect to repaint the face with the
`polish` ops (`paint`, `fill`, `mirror`, `clean_body`) using coordinates read
off `render --ascii face`.

For a real 3-D read give it two orthogonal images (`ops.imageref.from_images`):
front × side silhouettes are intersected, front colours win. That's how the
photo-to-voxel tools work too.

## Layout

```
mcbuild/
  nbt.py        NBT read/write (gzip, round-trip faithful)
  schem.py      Model, load/save/crop, bit-packing
  morph.py      flood_outside (pad/ground/ceiling), dilate/erode, components
  palette.py    colours, cost tiers, hue-preserving substitutions, donor Registry
  audit.py      the audit
  render.py     elevations, slices, ascii maps, contact sheets
  pipeline.py   YAML config runner
  cli.py        python -m mcbuild
  ops/          downscale, hollow, cheapen, polish, imageref
  gen/          canvas (shapes/hash) + tree, fox, tower, underside
configs/        one YAML per design
tests/          regenerate every design, assert audit passes
out/            outputs (gitignored)
```

## Adding a new generated design

1. `mcbuild/gen/<name>.py` with `DEFAULTS = {...}` and
   `build(cfg, donors) -> Canvas`. Use `Canvas.state()` to borrow valid block
   states from donor schematics; `raw_state()` only for blocks no donor has.
2. Register it in `mcbuild/gen/__init__.py`.
3. `configs/<name>.yaml` with `gen: <name>`.
4. `python -m mcbuild gen configs/<name>.yaml` — read the audit, look at the png,
   iterate with `--set`.

## Lessons encoded (so you don't relearn them)

* Downscaling by majority vote fails on skinned builds — the filler wins. Split
  geometry from material and vote among *visible surface* blocks only.
* Hollowing needs a padded array and the right exterior context (ground vs
  ceiling); verify by re-flooding, fail loudly on leaks.
* A render can lie (depth shading); the ascii block map cannot.
* Faces at small scale need to be *designed*, not filtered — repaint them.
* If a build wraps around something the user built, measure that thing; don't
  guess its shape.
