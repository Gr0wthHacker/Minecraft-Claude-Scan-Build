## The steak wand (2026-08-20)

Mark two corners with a piece of cooked beef, name a material, and the box is written as a design and
handed to Litematica for the **printer** to build. `Wand.java` (state + the click), `Fill.java` (box
→ `Capture`), `Rules.java` (what it must not cover), commands in `ChunkScanClient`.

```
/cscan wand on              arm the steak; off gives you your dinner back
/cscan mat stone_bricks     ...or just `/cscan mat` while holding the block
/cscan fill porch           writes `_fill porch` and places it at the box corner
```

**Nothing here places a block.** A client mod cannot, and should not: the schematic goes to
Litematica and the printer builds it, which is what makes the whole thing undoable and what lets the
existing `LitematicWriter` / `SidecarWriter` / `Litematica.place` carry it unchanged. `Capture` is a
plain record, so a one-material box is a `Capture` with a two-entry palette and nothing new to write.

**Right-click sets both corners** (first, second, then back to first) rather than the WorldEdit
left/right split. This is a client mod on a real server: a left-click is an attack and suppressing it
means suppressing a swing the server is about to hear about, where a right-click we consume never
leaves the client. It also means one gesture and one thing to cancel — and the thing being cancelled
is the wand's own use, which matters because **the wand is food**. Armed, a right-click with steak on
a block takes no bite and opens no chest. Unarmed, steak is steak.

### The three questions it has to ask, and where the answers come from

A fill is drawn in a world people are using, so it asks exactly what every Python generator asks —
is this a mechanism, is this material currency, does the 1.19 server have it. **Those answers are
not retyped in Java.** `tools/export_rules.py` emits `chunkscan_rules.json` from `protect.MECHANISM`,
`blocks.ECONOMY` and `data/server_blocks.json`, and `tests/test_wand_rules.py` fails if the shipped
file drifts. Same discipline as `proportions.measure` and `rubric.score` sharing one entry point:
one source, so two tools cannot disagree.

- **Protected cells are skipped, never covered**, and reported by kind. A fill that swallows a hopper
  is a loss, not a fill — and the substring match is what makes `gray_wool` protected, which is the
  whole reason `protect.py` exists.
- **Cells already holding the material are not work.** Designs here are REMAINING WORK, so a
  half-built box costs half, and the count you are told is the count you have to place.
- **A skipped cell comes out as AIR in the schematic.** A litematic cannot express removal, so air is
  how "nothing to do here" is spelt; write the material there instead and the printer covers the
  hopper after all. `FillTest` pins it by reading the hopper's own index back out of `ids`.
- **Currency and the 1.19 allowlist WARN, they do not refuse** — the allowlist is provisional (191
  blocks, would reject `allium`), which is the same posture `audit.report` takes. Dirt draws a loud
  line because every other check in the pipeline passes it silently.

### Two traps, both already set once elsewhere in this repo

- **A 32,768-cell cap.** Two corners 200 apart is 8M cells and the walk alone would freeze the
  client. There is no lazy path here — `plan` and `capture` both walk every cell.
- **Scratch fills are prefixed `_fill ` and skipped by `Designs.list`.** Bare `/cscan place` places
  everything with a sidecar, and a shelf of one-off fills is exactly the pile that already caught
  this project once with the scratch animals. Naming one explicitly still places it.

### The pre-upload audit (2026-08-20)

Four things fixed, three added, before the jar went up. Two of the four were bugs in the wand as
first written, which is the argument for auditing before uploading rather than after.

- **Path traversal on the fill name.** `/cscan fill ../../x` resolved straight out of the schematics
  folder. A fill name becomes a filename and is now validated.
- **Wand state survived a disconnect.** Corners are coordinates and coordinates mean nothing without
  a world: mark a box, reconnect somewhere else, and `/cscan fill` writes that box at those numbers
  in the new world. Cleared on `DISCONNECT` now, and two corners in two dimensions restarts the
  selection instead of building nonsense.
- **The selection was invisible.** `Highlight` was already there. Corners show as you pick them, the
  full edge outline when the box closes, and a box too big to outline falls back to eight corner
  markers — a PARTIAL outline would read as a wrong selection, which is worse than none.
- **`/cscan fill hollow | walls | outline`**, and **`/cscan replace <from> <to>`** — the deck floor's
  wood reclaim, by hand, inside the box. `replace` matches `from` by NAME, not by state, because you
  want every facing of a stair gone rather than one of them; and naming a block explicitly buys no
  exemption from the safe set.

#### `/cscan check` was blind to orientation, and the stair convention fell through the hole

`work.json` stored bare block names. Measured: **3,441 stateful cells** across the designs — 923
slabs, 241 walls, 97 stairs, 221 lanterns, 25 chains, 1,694 vines — whose orientation the in-game
check could not see at all.

Not hypothetical, and the designs prove it themselves:

| | |
|---|---|
| `Taproot Entrance` | places `smooth_stone_slab` as **both** `type=top` and `type=bottom` |
| `Island Belly Full` | places `mossy_stone_brick_slab` as `type=double` — a FULL BLOCK — beside `type=top` |

Build either of those the wrong way round and check reported 100% built. And it lands squarely on
the stair rule this repo went to trouble to settle: a flight built backwards cannot be walked up,
*our renderer draws both identically*, and it turns out the in-game check could not see facing
either. Litematica's overlay was the only thing that could catch it.

**The properties were in the palette the whole time** — `work.py` dropped them at
`names = [n.split(":")[-1] for n in m.names]`.

**But recording ALL of them would have been worse than recording none.** Most of a block state is
not a decision, it is the game reacting to the neighbourhood: a stair's `shape` comes from what is
beside it, a wall's connections from what it touches, `waterlogged` from someone pouring water in.
Comparing those reports a deviation for a block that is exactly right, and a check that cries wolf
is a check nobody runs. So `work.INTENTIONAL` names the properties a design DECIDES — facing, half,
type, axis, rotation, hanging, face, hinge, part, attachment — and nothing else is written:

    stone_brick_stairs[facing=east,half=bottom]      not shape, not waterlogged
    smooth_stone_slab[type=top]                      not waterlogged
    stone_brick_wall                                 bare: every connection is derived
    vine[east=true,north=false,...]                  ALL faces: see below

**A vine is the exception that proves the rule.** For `vine`, `glow_lichen`, `sculk_vein` the
direction flags are not connections the game made — they are which face the thing clings to, which
decides whether it hangs at all. `work.MULTIFACE` holds those, and for them the faces are recorded.

**The mod holds no policy.** It compares exactly the properties it is given and ignores the rest, so
a bare name still compares by name — which is what every `work.json` written before this looks like,
so an un-regenerated design keeps reading correctly instead of failing wholesale. A property named
on a block that does not have it reads as WRONG, deliberately: that is a design bug and should
surface rather than pass quietly.

**And a tally counts ITEMS, not states.** `/cscan need` briefly wanted
"12x stone_brick_stairs[facing=east,half=bottom]", which is not a shopping list — four facings of one
stair are one stack of one item.

53 work lists regenerated; 3,219 cells now carry their orientation. The payoff shows in the counts
that were previously one number: `stone_brick_slab` is 201 bottom and 178 top.

`tests/test_work_state.py` (10) pins the Python encoding, `WorkStateTest` (8) the Java comparison,
`FillTest` (17) the modes and replace, `WandTest` (6) the outline.

#### Two more bugs, both found because the world moved under the tests

Jack placed the deck floor fix mid-session and rescanned, so 54 of the 70 dark oak blocks were gone
and three soffit tests went red. Two were my tests pinning a SNAPSHOT — `assert reclaimed >= 70` is
wrong by construction for a design whose whole nature is REMAINING WORK: it fails the moment the fix
starts working. They derive the expected count from the capture now. The third was real, and so was
a fourth the regenerate then exposed:

- **An intersection belongs to BOTH grid lines, and only one was tested.** A cell with `x%g==0` and
  `z%g==0` was scored along Z only; if its Z-run was short but its X-run long, it demoted — punching
  a hole through the X line and orphaning the cell beside it. Two orphans, on a gate whose entire
  purpose is that there are none. It survives if EITHER line runs.
- **The reclaim manufactured `gray_wool`.** The heal material is the commonest solid neighbour, and
  by the tree that neighbour is the sculk sensor's shielding. The filter checked `KEEP` but not
  `protect.is_protected` — so a pass written to remove wood was placing wool. It now runs the same
  safe set every generator consults, and falls back to the panel material. It was also healing dark
  oak into `oak_wood` (the root break's, legitimately through that ceiling); the whole wood family
  is barred.

**And a test lesson worth keeping: assert in WORLD coordinates.** The canvas is sized to its own
content, so it shifts between two builds with different settings and anything comparing them lines
up against nothing. `Canvas.world_origin` exists for this. The same test was also reading
`room_plinth` cells — deepslate, on the floor course, isolated by design — and calling them grid
confetti.

#### Two traps in the tooling, both of which corrupted a source file

- **A UNICODE ESCAPE IN A PATCH PAYLOAD BECOMES THE CHARACTER.** A separator written as a
  backslash-u-0000 escape landed in `Digger.java` as a real NUL byte - which compiles, passes
  every test, and makes git treat the file as BINARY, so the diff reads `Bin 12017 -> 13942 bytes`
  and nobody can review it. The same mechanism turned a backslash-n into a real newline
  mid-string-literal in `cli.py` and broke the parse - and then broke the script written to record
  this note, which is as clear a demonstration as the trap deserves. Patch payloads carry no
  escapes; a sweep for NUL bytes over every source file is two lines and is worth running after
  any scripted edit.
- **`pathlib.read_text()` / `write_text()` ROUND-TRIP THROUGH UNIVERSAL NEWLINES**, so a script
  that reads a CRLF file, replaces one string and writes it back rewrites EVERY LINE. This file
  already records it; it happened again this session in a parallel stream, where
  `mcbuild/gen/isthmus.py` shows 3,006 changed lines and `git diff --ignore-cr-at-eol --numstat`
  says 76. Read and write BYTES when patching, and use that flag to tell a real content change
  from line-ending damage.

### Still open

- ~~**Bare `/cscan place` now places 61 designs.**~~ FIXED — `designs.json` gave it the tracked
  list, and the 2026-08-27 audit stopped `Designs.list` offering world CAPTURES as designs.
- ~~**The scans archive is unbounded**~~ — 24 files and 1.6 MB when this was written, 56 and 4.4 MB
  when it was measured again. Capped at twelve per scan name; see the audit below.
- **Untested outside the game:** whether consuming `UseBlockCallback` really suppresses the eat
  animation on a live server. The packet should never leave the client, but that is reasoning, not
  evidence.

### Clipboard, undo, and a storage index that was half wrong (2026-08-20)

```
/cscan copy <name>            the wand's box, captured as it stands
/cscan paste <name> [90|180|270|cw|ccw]     placed where you are LOOKING
/cscan clips                  what is on the clipboard
/cscan prune                  drop storage entries that are not containers
```

**Copy/paste is the speed-building multiplier and it cost almost nothing**, because every piece
already existed: `WorldCapture.captureBox` is what `/cscan sel` uses on a Litematica selection, and
`Litematica.place` already registers placements. Build a window bay once, then repeat it round the
rim rotated 90° each time. Nothing is placed by the mod — the schematic goes to Litematica and the
printer builds it, so a paste in the wrong spot costs one placement deletion.

**Rotation goes through a synthesised no-op.** `SchematicPlacement.setRotation` takes an
`IMessageConsumer` for feedback and there is no public no-op to hand it. Passing `null` is the
obvious move and risks an NPE inside a soft dependency, which would surface as *"paste silently did
nothing"*; a one-line `java.lang.reflect.Proxy` is honest instead. The rotation NAME is handed to
`Enum.valueOf` by reflection, so a typo is a crash in game and nothing sooner — `UndoAndStorageTest`
asserts every word maps to a real `Rotation` constant.

#### Undo: a litematic cannot express removal, so an undo is two halves

Every fill now writes `_undo <name>` beside it, and it is **not** an inverse:

- where the fill COVERS a block, that block is recorded, and re-placing it restores the cell
- where the fill puts something into AIR there is nothing to record, so the cell goes into the
  sidecar's **`dig`** list, which `/cscan dig` already reads

Both halves are needed or the undo half-works, which is worse than no undo because you would
believe it. `assertEquals(p.place(), undo.nonAirCount() + dig.size())` is the test that says so.
The undo follows the SHAPE, not the box — a hollow fill's undo is the shell — and it ignores cells
the fill skipped, or undoing a protected cell would re-place a hopper that was never covered.

#### `/cscan need` counts what is in your pockets first

It used to send you across the island for something already in your hotbar. Loose stacks only — the
contents of a shulker in your pack are not counted, because they are not placeable until you set the
box down. That under-reports rather than over-reports, which is the safe direction.

#### The storage index was 52% junk, and the cause is worth remembering

**141 of 269 entries were filed against blocks that are not containers** — 15 warped wall signs, 15
stone bricks, 11 slabs, walls, moss — holding 1,028 items between them at coordinates that point at
a sign. `/cscan find` is the "which chest has X" feature and half its answers were wrong.

`ContainerWatcher` recorded `lastUsed` on EVERY right-click and attributed the next container screen
within four seconds to it. So: right-click a sign, press E, and **your own inventory is filed as a
chest at the sign's position.** Two guards, both narrow:

- the clicked block must be one that actually opens a container
- the player's own inventory and the creative menu are `AbstractContainerScreen`s and are never
  containers, whatever was clicked

`Storage.isContainer` (opens a screen) and `Storage.stores` (actually holds items) are separate on
purpose: a crafting table passes the first and must fail the second, or `/cscan find` starts
offering a workbench as a source of stone. `/cscan prune` drops the bad entries — they are removed
rather than repaired, because the POSITION is the thing that was wrong and there is nothing to
repair it to. Reopening the real chest re-indexes it in one click.

**Clips and undos are scratch, like fills** — `_clip `/`_undo ` are skipped by `Designs.list`, so a
bare `/cscan place` still never sweeps them up.

43 Java tests. **Two things found by javap rather than by memory, again:** `Inventory` is not
`Iterable` but `Container` is, and it is `Container` that `Inventory` implements.

#### Unrelated, but found while checking the Litematica API

**There are two Litematica jars in `custom_mods/nextgen-26.2/`** —
`litematica-fabric-1.21.11-0.26.12.jar` and `litematica-fabric-26.2-0.28.4.jar`. Same mod id, two
versions, and the 1.21.11 one is obfuscated (`class_2470`) so it is not built for this client at all.
That is the same duplicate-mod-id situation the chunkscan jar is warned about. Probably wants
deleting; not deleted here, because it is Jack's mods folder.

### The chest move (2026-08-20)

```
/cscan move          what is left, what stays, whether the hall can take it
/cscan move next     nearest source marked AMBER, its destination marked GREEN
/cscan move done     mark the one you are standing at as emptied
/cscan move reset
```

The top open item on the island for three sessions running. **Nothing here moves an item** — a
client mod cannot, and should not. It answers the two questions that make the job tedious: which
chest next, and which slot does this belong in. `Highlight` draws both, so a trip is a walk between
two boxes you can see.

**Measured against the live index and capture:**

| | |
|---|---|
| general storage to move | **37** |
| stay with their machines | **18** (16 hoppers, 2 stonecutters) |
| hall slots standing | 76, of which **39** are free or never opened |

**A chest within three blocks of a hopper is that hopper's output**, and it looks exactly like
general storage from its contents. Moving one breaks a farm. That is rule 10 from the other side —
the same clearance that stops a design building next to a chest decides here which chests are not
yours to move.

**The machine list is deliberately NOT `protect.MECHANISM`**, which contains `chest` — every source
would have disqualified its own neighbours and nothing would ever move.

Three things the design had to get right, and each has a test:

- **Slots come from the WORLD, not from the design.** The hall is built, so it emits nothing:
  `chests: 0`. A tool reading the design to find the "food and crops" wall would learn nothing at
  exactly the point it matters. `storehall.py` now records `banks` — wall, label and cells — as
  INTENT, whether or not anything was placed this run.
- **A slot the index has never seen counts as free.** The index only knows containers you have
  opened, so "empty" and "never opened" are the same evidence. Free is the useful error: you walk
  there, find it full, and press on.
- **A source inside the hall is not a source**, or the plan moves a chest into itself.

#### The hall's labels do not match what Jack actually stores

The taxonomy lives in `tools/export_rules.py` and ships through `chunkscan_rules.json`, the same
one-source route as the protection and economy rules — `tests/test_storehall_banks.py` fails if a
bank label has no category feeding it, because that failure is otherwise SILENT: every container
would quietly overflow to "whatever slot is free" and the hall would stop being sorted at all.

Running it against the real index says the labels are the wrong four:

| category | containers | matching slots free | |
|---|---|---|---|
| ore and stone | 16 | 10 | overflow |
| food and crops | 8 | 11 | |
| **dyes and wool** | **7** | **0** | no wall at all |
| wood and saplings | 4 | 11 | over-provisioned |
| tools and redstone | 1 | 0 | no wall |
| moss and plants | 1 | 4 | |

`dyes and wool` is ~42,000 items — 11,840 ink sacs and ~30,000 wool in eight colours — and there is
no bank for it, while `wood and saplings` holds eleven free slots for four containers. **Relabelling
one bank would fix most of it**, and that is Jack's call, not a silent edit. Until then the overflow
is placed and REPORTED rather than jammed into the nearest wall.

### The colour foundation was wrong twice over (2026-08-20)

Every palette in this project is chosen by `blocks.nearest()` over one RGB per block, and every
render draws with the same numbers. That one number was wrong in two independent ways.

**Biome tint was never applied.** The colormaps are sitting in the client jar — `grass.png`,
`foliage.png`, `dry_foliage.png` — unused, so every block the game tints extracted as the grey its
texture actually is:

| | recorded | really |
|---|---|---|
| `vine` (13,611 on the island) | `[116,116,116]` | `[54,78,21]` |
| `oak_leaves` (3,066) | `[144,144,144]` | `[67,97,27]` |
| `grass_block` | `[147,147,147]` | `[84,109,51]` |
| `water` | `[177,177,177]` | `[44,82,158]` |

**18,006 of the island's 56,739 blocks — 31.7% — were a tint-affected block recorded as grey.**

**And one face cannot serve two kinds of build.** A floor is read from above, a statue from the
side; 155 blocks differ between them, `cherry_log` by 131 and `pale_oak_log` by 112. Switching
everything to the side would simply have broken the floors instead, so both are recorded and the
caller says which it means: `blocks.color(name, face)`, `nearest(..., face="side")`. `top` stays the
default, so no existing caller moved.

#### What it was actually costing

`green_concrete` — **expensive tier** — was the nearest block to leaf green, because no leaf had a
green to be near. Same shape of error elsewhere:

    leaf green (60,100,30)      green_concrete          ->  oak_leaves
    bone pale  (230,226,205)    chiseled_quartz_block   ->  bone_block     [side]
    bark brown (110,85,50)      oak_wood                ->  oak_log        [side]

Two of those three were expensive-tier picks made because the cheap natural block was mis-measured.

**And it means some of the analysis in this file was computed on bad numbers.** The grey-fraction
comparison that justified the gallery timber and then the soffit wood — *"the deck is 62% grey and
7% wood against the plate's 36% and 23%"* — counted every leaf and vine as stone. Both designs were
reverted for other reasons; the number that motivated them was never trustworthy either.

#### What was changed, and what deliberately was not

- **`tools/recolour.py`** owns colour now, and needs only the client jar — no datagen run.
  `tools/extract_blocks.py` keeps the REGISTRY half and delegates, so a full re-extract and a
  colour-only refresh cannot disagree.
- **30 blocks' `rgb` moved**, and exactly one of those is not explained by tint (`honey_block`, by
  5, rounding). The change is surgical by construction.
- **155 blocks gained a distinct `rgb_side`.**
- **No design was regenerated and no score moved** — the jaguar is still 0.80. The animal coats name
  blocks directly rather than picking by colour, so the drift is in renders and in what future
  picks will choose. `tools/colour_drift.py` reports it: `island_now` renders 30.5% differently,
  `Island Belly` 60.4%, `island_lower` 100%.

**THE BIOME IS AN ASSUMPTION.** Nothing offline can say what biome skyblock.net's island sits in, so
the colormap is sampled at PLAINS (temperature 0.8, downfall 0.4) — grass `(145,189,89)`, foliage
`(119,171,47)`. If the island is somewhere else that is the one number to change, in
`recolour.PLAINS_TEMPERATURE`.

Two traps worth keeping:

- **`spruce_leaves` and `birch_leaves` ignore the biome entirely** and use fixed colours
  (`0x619961`, `0x80A755`). Tinting them through the colormap makes a birch wood read like an oak
  one. `lily_pad` is fixed too — `BlockColors.LILY_PAD_IN_WORLD`.
- **A block with no top face must fall back to its SIDE, not to an arbitrary slot.** A grindstone's
  texture slots are `leg/pivot/round/side`; ordering `top` first and then sorting the rest picked
  `leg`, the dark wooden strut, and called a grey stone block `[60,47,26]`.

`tests/test_colour.py` pins the shape rather than the values — foliage is green, water is blue,
nothing tinted is neutral, a log's two faces differ, a uniform block's do not, the picker can reach
a leaf, and no block lost its colour.

### Finishing the colour work, and retiring the mammals (2026-08-20)

#### The renderer was still drawing the wrong face

Adding `rgb_side` to the database did nothing on its own: `views.py` and `render.py` both built one
palette per design and used it for every view, so every ELEVATION drew top-face colours. Measured:

| design | cells drawn with the wrong face |
|---|---|
| Void Giraffe | **46.1%** (`bone_block`) |
| X jaguar | 19.3% |
| island_now | 1.1% |
| Lowland Heron · X elephant | **0%** |

Both now pick per view — `top` for the plan, `side` for everything else.

**And the hand-tuned `palette.COLORS` table was shadowing the whole thing.** It is checked first and
has no concept of faces, so `color_of(n, "side")` on a log returned the top value and the split did
nothing at all. It now speaks only for blocks whose two faces AGREE — where there is no face
question, its deliberate render choices (water, a little brighter than its average) still stand.

Worth noting what this says about scope: the biggest beneficiaries are the log- and bone-coated
mammals, and the birds, the lowland and the elephant were already at 0%. The giraffe is the reason
it was worth doing — 46% wrong, and it is the only animal standing in the world.

#### `/cscan stack` and `/cscan scaffold`

```
/cscan stack <clip> <count> <dir> [step]     repeat a module along an axis
/cscan scaffold <design>                     cells with nothing to place against
```

`step` defaults to the clip's own size along that axis so copies sit flush; give it explicitly to
leave gaps — a 3-wide bay on a step of 6 is the cloister rhythm the gallery wanted.

**The scaffold check is only useful because of one rule: any EARLIER neighbour counts.** The
worklist is sorted bottom-up, so a wall builds against itself course by course and only its first
block needs something under it. Without that, most of every design reads as floating.

A neighbour in an unloaded chunk counts as SOLID, deliberately: claiming a cell needs scaffolding
because the chunk behind it has not loaded would send you to build a tower against terrain that is
already there.

**And a test of mine was wrong where the code was right** — you can place a block *under* an
existing one by clicking its underside, so a top-down column is self-supporting too and only its
first cell is ever the question. Which is exactly why the bottom-up sort matters: the same grounded
column reports 0 floating built upward and 1 built downward, because at the moment you place that
top block, it is in mid-air.

#### The cats and bears are retired IN CODE now, not only in prose

They score 0.79–0.86 on every dimension the rubric has. The panel is what retired them —
*"you cannot name it from the silhouette — it reads as a low table, or a bull"* — and the scores are
what failed to notice. Until now `species.yaml` still carried all eight as live work, `compare.py`
still ranked them, and every session was invited to tune the ones that cannot work. This one was.

    retired   jaguar · leopard · lion · bear · polar_bear      identity is MUSCLE
    live      elephant · giraffe · capybara                    identity is HARDWARE

`retired: true` is a **record, not a threshold** — nothing computes it, and nothing should. They
still resolve and still build (`X jaguar` is in `out/` and must keep loading); what they no longer
do is appear as live work. `taxonomy.live()` is the filter, `compare.py --retired` overrides it,
`configs/jaguar.yaml` uses the first-line RETIRED marker the test suite already understood.

`tests/test_retired.py` pins the split, that a retired species still resolves, and — deliberately —
that the REASON survives in `species.yaml`, including the evidence that scale does not rescue it
(the jaguar at 2.6x and 60,000 blocks failed exactly as the 27-block one did). A flag with no reason
beside it gets removed by whoever finds it inconvenient.

### Shapes, darkness, and a readout (2026-08-20)

```
/cscan around <r>                        set the selection to a cube of that radius
/cscan fill ball|sphere|dome|cylinder|tube|disc|ring <name>
/cscan dark [radius]                     standable cells the light does not reach
/cscan bom <design>                      the whole design in stacks and shulkers
/cscan hud <design> | off                a two-line readout while you build
```

#### The shapes are predicates, which is why they were nearly free

Every mode is one function — `Mode.wants(x, y, z, sx, sy, sz)` — so a sphere runs through the same
plan, capture, protection, economy, undo and printer path as a cuboid, and none of that had to learn
what a sphere is. Eleven shapes for about eighty lines.

**THE BOX IS THE BOUNDING BOX, not a radius.** A sphere in 21x21x21 has radius 10; in 21x11x21 it is
a squashed ellipsoid, which is what a build usually wants and what a fixed radius cannot say. That
is also why no shape takes a radius argument: `/cscan around 8` sets the selection and then every
shape, `copy`, and `replace` all compose with it. Eleven radius parameters would have been eleven
ways to say one thing.

Three pieces of voxel geometry worth keeping:

- **The half-axis is `sx/2`, not `(sx-1)/2`.** The extreme cell sits at `(sx-1)/2` from centre, so
  dividing by the larger radius keeps it inside. Get it wrong and the ball comes out with its poles
  shaved flat — the classic voxel-sphere bug, and `aBallReachesEveryFaceOfItsBox` is the test.
- **A shell is "inside, with a neighbour outside" — never a band in the radius equation.** The
  gradient of an ellipsoid is not constant, so a constant band is fat at the poles and thin at the
  equator. The neighbour rule gives an even skin by construction, and it is the same rule the box
  HOLLOW already used.
- **A DOME's equator is the box FLOOR.** Taking the top half of an ellipsoid inscribed in the box
  gives a dome standing on a circle the size of its own waist, floating clear of the rim — you then
  hand-fill a ring underneath. The half-height is the full box height and y is measured from 0.

`tube` and `ring` are open-ended on purpose: a tube with caps is a hollow cylinder, and what you
reach for `tube` to build is a chimney or a well.

**`shell` still means a hollow BOX.** It was tempting to give it to the sphere; it shipped meaning
the box, and silently repurposing a live alias is a behaviour change for anyone who typed it
yesterday. `orb` is the sphere alias.

#### `/cscan fill spiral` — a staircase out of the same predicate (2026-09-04)

```
/cscan fill spiral <name>       treads winding clockwise-up round a central post
/cscan fill spiralccw <name>    the mirror twin
/cscan fill helix <name>        the same flight round an OPEN core (a well, or a root)
/cscan fill helixccw <name>
```

Hold **stairs** and every tread faces the ascent (the stair convention, asserted rather than
eyeballed — our renderer draws a backwards flight identically); hold **slabs** and each tread is a
bottom half and a top half, so the flight rises half a block a course and can be WALKED. Any other
material is a jump staircase. The post takes the material exactly as held.

Three things that decided the shape:

- **A TREAD IS A SECTOR, AND EVERY RING CELL BELONGS TO EXACTLY ONE COURSE PER TURN.** A cell's
  angle round the post picks its course modulo courses-per-turn, so consecutive treads tile the
  ring with no gap and no overlap and the flight touches itself at the rim by construction.
  Courses per turn is derived so a tread is ~2 cells at the rim (a 5x5 is the classic 8-step
  spiral round a 1x1 post) — ~3 for slabs, because each HALF has to land at least one cell on a
  grid that samples a wedge unevenly, or one course somewhere is a whole-block rise and the
  "walkable" flight has a jump in it. `SpiralTest` climbs every size from 3 to 15 with a 0.5
  rise and fails on the first one that needs a jump.
- **THE FIRST SHAPE WHOSE CELLS ARE NOT INTERCHANGEABLE**, so `Mode.state(material, cell)`
  replaced the bare `wants` in plan, capture and undo, and the palette is first-use order rather
  than `{air, material}`. A standing tread with the RIGHT facing is built; the same block facing
  the wrong way is work — which `/cscan check` could not see before states were recorded.
- **AN OPEN CORE IS STILL A CORE.** Written as "no post", the centre cell of a helix became a
  tread. The core is the same footprint either way; `post` only says whether it is filled.

And one that cost 41 red tests in ten files: **a `static final BlockState` in a test class loads
the registries at class-load time, before `@BeforeAll` bootstraps them**, and every test class
that runs after it in the same JVM fails with *Not bootstrapped*. Block states in tests are
read lazily.

#### `/cscan dark` — the one question only the client can answer

The desktop has always approximated lighting by DISTANCE: *"95% of the deck is within 7 of a
light"*. That is a lower bound on darkness, because light does not pass through walls and this
island is nothing but walls. Off the capture: **462 light sources over 14,457 standable cells, ~10%
more than 7 blocks from any source before geometry is considered at all.** The real figure has never
been measured, because only the client has the light engine.

`/cscan dark` reads it directly, marks the cells red, and bins them into clusters so the report says
"a dark room" rather than listing three hundred cells.

**Sky light is reported but not judged.** A cell open to the sky is bright by day and dark at night;
counting it as lit hides every outdoor spawn and counting it as dark flags the whole plate. Block
light is what a torch changes, so that is what is scored, and the sky value rides along so an unlit
room can be told from an unlit lawn.

#### The HUD, and two more 26.x API changes

`/cscan hud <design>` puts a two-line readout on screen: built/total, percent, how many are left,
how many deviate, and how far the nearest one is — because "247 to place" does not tell you where to
stand.

**It recomputes on a TIMER, not per frame.** `Work.split` walks every cell of the design and diffs
it against the world; `Island Belly Full` is 8,210 of them, and doing that sixty times a second to
draw two lines of text costs more than the information is worth. Every 40 ticks is faster than you
can place a block.

Both API notes came from javap rather than from a guide, again:

- **`HudRenderCallback` does not exist in 26.2.** The HUD is built by EXTRACTING RENDER STATE:
  `HudElementRegistry.addLast(id, element)` and `element.extractRenderState(extractor, delta)`,
  with `extractor.text(font, s, x, y, argb)`. Any older HUD guide is wrong here.
- **`Options.hideGui` and `Minecraft.screen` are both gone**, and no guard is needed anyway — an
  element in the HUD layer stack is hidden with the rest of the GUI by vanilla.

### `/cscan plan` — where to stand, given what is in your pockets (2026-08-20)

```
/cscan plan <design>     the spots worth walking to, ranked by what you can actually place
/cscan goto <n>          marks that spot green and puts an arrow on the HUD
/cscan goto              stop guiding
```

`next` answers *what is nearest*. `need` answers *what should I fetch*. Neither answers the question
a several-thousand-cell design actually poses — **where can I stand right now and place a hundred
blocks without moving or running out** — and that is the difference between a build session and an
afternoon of walking.

Three things have to be true before a spot is worth walking to, and all three are measured:

- **You are carrying the material.** Not "it is in a chest somewhere"; that is `need`'s question.
- **You have ENOUGH of it.** Stock is allocated to clusters IN RANK ORDER, so the second spot is
  told what the first one leaves it. Two piles of 20 and 25 bricks in your pack is 20 and then 5 —
  a plan that promised 20 and 20 would have lied about the only number that mattered.
- **It is within reach of one standing spot.** Clusters form around a centre at a WORKING RADIUS,
  not by connectivity: a wall is one connected component and forty trips.

Scaffold-blocked cells are subtracted too, so `doable()` is the number of blocks you can place
standing there — not the number of cells that happen to be nearby.

Clusters are seeded by binning at the working radius rather than by an all-pairs density scan. A
few thousand cells all-against-all is not worth the wait for a number that coarse.

#### `/cscan follow <design>` — the plan without the typing between

```
/cscan follow <design>   walk me through the whole thing
/cscan follow            stop
```

The arrow moves to the next spot as each one finishes, so a session is `follow` once rather than
`plan` and `goto` over and over.

**With HYSTERESIS, which is the whole difficulty.** The plan is recomputed on every recount, and the
best spot genuinely changes as you place blocks and burn stock — repointing at whatever is best THIS
second would swing the arrow around while you stand still doing exactly what it asked. So the
current target is kept while it still has anything doable, and only when it is exhausted is the next
one picked. Chat announces a change of spot and nothing else: "spot 2" every two seconds for as long
as you stand there is not guidance, it is noise.

**Running out of blocks is not the same as finishing**, and saying the wrong one sends you to stare
at a completed wall. An empty plan while cells remain reports "nothing left you are carrying the
blocks for" and points at `bom`; only an empty `todo` reports the design complete.

#### `/fly` changes two things, and one of them is not obvious

Jack has `/fly` on this server. That settles the open question about ranking spots by WALKABLE
distance rather than straight-line: with flight the straight line IS the route, and the pathfinder
that would have been the next big job is not needed. `Plan` already ranks on 3D `distSqr`, so it was
right by accident.

**But it makes the vertical leg free to travel and therefore free to ignore — right up until you
are hunting for a floor.** This island is 240 blocks tall: the lowland is Y24, the deck Y194, the
sky bird Y268. A compass bearing cannot carry that, so a chest 150 blocks below reads as "18m NE" on
any horizontal-only arrow. `Hud.climb` states it separately — `up 154`, `down 154` — and anything
under 3 is left unsaid, because two blocks is a jump rather than a leg of a journey.

#### FETCH FIRST, then build

`follow` is two-phase now. If the best spot is short of stock and the index knows where the material
is, **that trip comes first** — amber highlight on the container, arrow onto it, and the note turns
into "take 56x stone_bricks" once you are standing there. Only when nothing is fetchable does it
send you to do the part you can.

A spot you cannot finish is a spot you walk to twice, which is the whole argument.

`/cscan fetch <design>` is the same trip on demand, for topping up before you start rather than
being interrupted halfway — and it costs the WHOLE remaining design rather than one spot, because
that is the trip you make before a session.

**The fetch target is the biggest shortfall THAT HAS AN ADDRESS.** A material with nowhere to fetch
it from must never become the trip, or the arrow points at a chest that does not exist; it is
reported in words and skipped for navigation.

#### A shortfall now comes with an address

`plan` used to say "64 short of stock" and stop, leaving you to run `need` and join the two in your
head. The container index already knows where the bricks are, so it says so:

    2) 120 cells at -24203 194 30012   18m NE  (56 short of stock)
       120x stone_bricks (have 64)
       fetch 56 more stone_bricks — 500 in #37 Store Hall 22m NE

Silence when something is short would read as "you have enough", so a material with no indexed
container says that in words rather than being left out.

#### The arrow is in YOUR frame, not the compass's

`Storage.direction` says "NE", which is something you translate while walking. `/cscan goto` puts
`^ ahead` / `< left` / `v behind` on the HUD instead, computed from the angle between where you are
LOOKING and where you are going, so it swings as you turn.

**It updates every frame, not on the HUD's timer.** The design recount walks every cell and stays on
its 2-second clock; the arrow is a subtraction and a bearing, and a direction that refreshes every
two seconds is a direction that is wrong every time you turn around.

Worth writing down because it is the sign error that would send you consistently the wrong way and
that nothing but walking would reveal: **yaw 0 faces +Z (south), so east (+X) is on your LEFT.**
`leftAndRightAreNotMirrored` asserts exactly that, having first been written the lazy way — asserting
only that left and right differed, which every mirrored implementation also passes.

### The command sheet, on a key (2026-08-20)

**V** opens it (rebindable under Controls, "ChunkScan command sheet"). Thirty-nine subcommands is
more than anyone remembers, and the ones you forget are the ones that would have saved the trip.

Two decisions worth keeping:

- **Clicking a row does NOT run it.** It drops the command into the chat box with the cursor after
  it, because almost every one takes a design name or a radius, and a menu that fires
  `/cscan fill` with no argument wastes a click. A row that takes an argument therefore ends in a
  TRAILING SPACE - without it you get `/cscan planIsland Belly` and wonder what happened. Both
  halves of that are asserted.
- **The sheet leads with live state** - wand armed, current box, current material, what the HUD is
  following - so it says where you ARE before it says what you could do.

**A menu's failure mode is not crashing, it is going quietly stale.** A command gets renamed, the
sheet still lists the old name, and clicking it types something inert; nobody notices until they
need the command they had forgotten, which is the entire point of the sheet. So `MenuTest` checks
the sheet against the SOURCE OF THE COMMAND TREE - every `/cscan x` it offers must appear as a
`literal("x")` in `ChunkScanClient` - rather than against a second hand-written list, which would
be one more thing to forget to update.

#### Four more 26.x API changes, all found by javap rather than by a guide

The GUI is where 26.x has moved furthest from every tutorial written before it:

| written from memory | actually 26.2 |
|---|---|
| `KeyBindingHelper` in `fabric-key-binding-api-v1` | **`KeyMappingHelper`** in `fabric-key-mapping-api-v1` |
| `new KeyMapping(name, key, "category string")` | `KeyMapping.Category.MISC` - a **record**, not a string |
| `Minecraft.setScreen(screen)` | **`setScreenAndShow(screen)`** |
| `mouseClicked(double, double, int)` | **`mouseClicked(MouseButtonEvent, boolean)`** |

That last one is the dangerous one: written the old way it compiles as a private method nobody
calls, `@Override` is the only thing that catches it, and without the annotation you would have a
menu whose rows silently do nothing.

Screens extract render state exactly as the HUD does - there is no `render(GuiGraphics, ...)`, only
`extractRenderState(GuiGraphicsExtractor, mouseX, mouseY, delta)`.

### The mod now knows which designs you actually track (2026-08-20)

`sync.yaml`'s `progress:` list is the only place that records it — 23 designs against the **61**
sitting in the schematics folder — and the mod could not see it: gson and no YAML parser, and
`sync.yaml` lives in the repo rather than beside the schematics. So bare `/cscan place` placed all
61, including the scratch shelf this file already warns about (`JAG big` is 57,994 cells of jaguar
parked at the origin lock), and `plan` could only ever be asked about one design at a time.

`python -m mcbuild sync` now writes `designs.json` beside the schematics and the mod reads it at
runtime. Same one-source route as `chunkscan_rules.json`, with one difference that decides where it
lives: **those rules are baked into the JAR because they change when the GAME does; this list
changes whenever Jack edits a yaml file**, so it cannot be a build-time resource.

Two payoffs:

- **`/cscan place`** with no argument means the 23, and says so. Without the file it still places
  everything, but complains and tells you which command records the list.
- **`/cscan plan`** with no argument answers *where can I work, ANYWHERE* — the best spot in each
  tracked design, ranked by what you can place with what you are carrying, with the count still
  left and the bearing to it.

**Reported per design rather than pooled into one cluster list**, because a cluster has to belong to
a design for `follow` to have anything to follow. "Where can I work" and "which job am I doing" are
different questions, and only the second has an answer that fits on a HUD.

**A MISSING file is `null`, not an empty list.** "We do not know" and "you track nothing" are
different answers and `place` branches on which — collapsing them would make a fresh checkout
silently place all 61 rather than complain. Both cases are asserted, on both sides.

### The storage index had no way to forget (2026-08-20)

Jack: *"the updating of storage isnt accurate, its saying blocks are active that arent"*. Measured
against the 16:33 capture, against 339 indexed containers:

| | |
|---|---|
| still a container in world | 108 |
| **no container there any more** | **179** |
| …of which the position is now air | 63 |
| …now stone brick, wall, slab, moss | the rest |
| items claimed in containers that do not exist | **36,088** |

**The index is written when you OPEN a container, and you cannot open one that has been broken.**
Every other part of this project regenerates against the newest capture — designs are
remaining-work, `progress` diffs against the world — and this is the one thing that only ever
accumulates. Two causes with two different shapes: the watcher's old sign/inventory bug filed
records that were never real, and the chest move broke chests that were.

It was harmless while `/cscan find` was advice. It stopped being harmless the moment `fetch` and
`follow` started NAVIGATING to those coordinates.

- `Storage.stillThere` checks a record against the live world, and `find` skips what the world
  disproves rather than deleting it — a lookup is not the place to throw away someone's data.
- `/cscan prune` is where that decision is made deliberately, and now drops both kinds.
- **UNLOADED IS NOT ABSENT.** A chunk you cannot see is not evidence the chest went, and treating
  it as such would delete the whole index the first time you pruned from across the island. So
  `prune` says how much it checked, and asks you to fly the island and run it again.

### `follow` was sending you to places you cannot build (2026-08-20)

Two more gates, and they are opposite failures:

- **`scaffold`** — nothing to place against. Already there.
- **`sealed`** — no way to REACH it: every one of the six neighbours is solid. A cell buried in a
  mass has plenty to place against and no way in, and you cannot put a block inside a sealed volume.

Together they bracket what "buildable right now" means: at least one solid neighbour to click, at
least one open one to reach through. Six of either and it is not this trip's work. A cell of the
same design placed EARLIER counts as neither an opening nor a hole — it will be solid when you get
there, which is the same reason it already counted for scaffolding.

### A TRIP IS BOUNDED BY WHAT YOU CARRY, NOT BY YOUR REACH (2026-08-20)

Jack: *"a 30k block project shouldnt doing follow by 64 blocks"*. He is right and the first version
was reasoning about WALKING — every spot sized at one standing radius, which on a thirty-thousand
cell design is a plan made of five hundred trips.

**With flight, moving forty blocks inside a region costs nothing and flying back to a chest costs
the session.** So the unit is one INVENTORY LOAD: the radius grows until the spot holds about as
many cells as you are carrying blocks for.

| carrying | radius |
|---|---|
| 16 | 6 — arm's length, as before |
| 64 | 12 |
| 1,728 (a shulker) | 24 |
| 13,824 (six) | 48 |
| 30,000 | 96 — capped |

Two details that keep it honest: the **budget is capped by what the design NEEDS**, so 3,000
cobblestone does not open the radius for a design wanting forty of it; and the **bin size grows with
the radius**, or the seeds are found at the wrong grain and the clusters come out as fragments of
the region they should be.

`MAX_RADIUS` is 96 because past that it is not a trip, it is the island — a "spot" you cannot see
the far side of is a compass bearing to a region, not guidance.

### `/cscan autofly` — it flies you there (2026-08-20)

```
/cscan autofly on | off
```

It steers toward whatever the HUD arrow is pointing at, so `follow` becomes hands-off: the plan
picks the spot, the arrow points, and this closes the distance.

**THIS IS MOVEMENT AUTOMATION ON A LIVE SERVER.** ~~Most servers' rules treat it as a bot whatever
it is for, and smooth constant-velocity flight is the exact signature anticheat is built to catch.~~

**AMENDED 2026-08-30 — Jack: automation is ALLOWED AND ENCOURAGED on skyblock.net.** That retires
the constraint the rest of this section was written under, and several deliberate limitations
elsewhere in the mod exist ONLY because of it and should be re-decided on their merits rather than
inherited:

- the speed cap at vanilla sprint-flight — *"no faster than a player can actually go"* was chosen as
  the one bound defensible without knowing the server's rules, and now the rules are known;
- `Prices` refusing to open a shop menu by itself;
- and above all **the rule that the mod never places a block.** That is stated here as a technical
  fact — *"a client mod cannot, and should not"* — and only the second half was ever true.
  litematica-printer places blocks from a client exactly as this mod could. It is the reason the
  loop has no feedback signal at all (*"the printer never reports back, so `todo` shrinking is the
  only honest evidence a block was placed"*), which is why there are four stall clocks.

What stays true whatever the rules say is the property that made it safe to leave running: it is
trivially interruptible, it sets delta movement rather than teleporting, and `/cscan stop` is one
word. What the code can do is be conservative and be trivially interruptible:

- **Any movement key hands control straight back.** The one property that makes it safe to leave
  switched on: you never have to fight it, or go hunting for the off switch while it flies you into
  a wall.
- **It sets DELTA MOVEMENT, never position.** A position write is a teleport, which is both what
  anticheat catches and what rubber-bands you into terrain.
- **Capped at 0.35 blocks/tick**, under vanilla creative flight, and it eases into the target rather
  than overshooting and wobbling.
- **The turn is eased, not snapped** — a camera that jumps to a bearing is not a player. Shortest
  way round, so 350° to 10° is twenty degrees clockwise rather than three hundred and forty back.
- **It lifts over obstacles.** Flying straight at terrain just presses you into it and the server
  hauls you back.
- **It stops while a screen is open**, or it would carry you away from the chest you are looting.

And one more instance of the same lesson: **there is no `Minecraft.screen` in 26.2** — this file
already said so, in the 26.x notes, and I reached for it anyway. The open-screen flag is tracked
from `ScreenEvents` exactly as `ContainerWatcher` does it.

### `Nav` — routing, because the client knows every block (2026-08-20)

Jack: *"since we have actual updates via scan it should also have perfect navigation through
doorways etc since it knows all placements"*. Right, and flying at a bearing only ever worked in
open air — on this island most destinations are inside something, and "lift over what you hit"
presses you into the outside of the wall the room is behind.

Plain A* in three dimensions over the live world. Three things matter more than the algorithm:

- **Clearance, not emptiness.** A player is two blocks tall, so a cell is passable only if the one
  above it is too. Checking a single cell finds "doorways" a head high and walks you into the
  lintel. And it is `blocksMotion()` rather than `isAir()`, so a slab or a fence is judged by what
  it actually stops.
- **NO CORNER CUTTING.** A diagonal step is legal only when the orthogonal cells it passes between
  are clear as well. Without that the route squeezes the corner of a door frame — geometrically
  shorter, and you snag on the jamb every time. This is the single thing that makes doorways work.
- **Unloaded is passable.** A chunk that has not arrived is not a wall, and refusing to route
  through it would fail every long flight. The route is recomputed twice a second, so it sharpens
  as the world loads.

`simplify` then drops every waypoint you can fly straight through: A* returns each cell it stepped
on, which through open air is a bead chain of forty points and a visible zig-zag between them. What
survives is the corners — which is to say, the doorways.

#### Two wrong turns worth recording

**I wrote a partial-route fallback and it was worse than nothing.** The idea was that when the node
budget runs out, the best progress so far beats no answer. It does not, for a reason specific to
this problem: **in open sky the search never exhausts** — there is always more air to expand into —
so the budget ALWAYS runs out and the partial ALWAYS fired, including when the destination was
sealed and there was no route at all. Worse, a partial reads to the caller as a real route, which
switches off the straight-line fallback that might actually have got there. Empty now means "I could
not find a way", the autopilot says so once and flies direct: a worse route honestly labelled rather
than a wrong one confidently followed.

**And two of my tests were wrong, not the code.** They built a finite WALL in open sky and asserted
no route existed — the router simply flew over the top of it, correctly. A wall in the open is not
sealed. They build a closed six-sided room now, with the door-and-no-door pair as controls.

### `/cscan tidy` — one item, one home (2026-08-20)

Measured off the real index rather than guessed: **96 containers holding 244 distinct items, and 206
of those 244 live in more than one container.** White wool is 12,729 spread over 27 chests and would
fit in eight. Cobblestone is 11,830 over 26. Thirty-seven items have eight or fewer in total and are
STILL split across two or more.

    135 piles worth consolidating, 328 slots to reclaim

The tedious part of that job was never the shift-clicking, it is knowing WHICH twenty-seven chests
and in what order. `tidy` computes it; `/cscan tidy <n>` hands the job to the same guidance
`follow` uses, so `autofly` walks you round the sources.

Three decisions the numbers forced:

- **The home is wherever most of it already is.** Moving 200 into a chest holding 12,000 beats
  moving 12,000 into one holding 200, and picking the NEAREST container — the obvious first
  instinct — would routinely choose the second.
- **Ranked by SLOTS FREED, not by item count.** Twelve thousand wool in two chests and twelve
  thousand in twenty-seven are the same pile; only the second is a mess. Ranking by count puts wool
  top and buries the four-way split of redstone that actually costs you space.
- **A tiny pile is not a trip.** Two chests holding four sticks between them is not a problem to
  solve, so `MIN_TOTAL` is 32.

It also runs the index through `Storage.stillThere` first, or it would send you to chests that were
broken during the chest move.

**It plans and points; it does not move items.** Slot manipulation is a separate piece of work — see
the note below.

#### `/cscan take` — and the loop closes

```
/cscan take                    empty the container you are looking at
/cscan take <item> <count>     take just that much
```

Built for the chest move and for `tidy`'s 135 piles; it is ALSO what `follow`'s fetch phase now
calls when it arrives at a chest still short of stock. Both uses are real and both are stated here,
because a file that describes what it does honestly is the only kind worth trusting later.

With it, `follow` runs unattended: pick the spot, fly the route, take the materials, fly back, let
the printer place, advance. Before, it flew you to the chest and waited for a human to shift-click.

A state machine rather than a loop — opening a chest is not synchronous. You send a use-item, the
server decides, the screen arrives some ticks later, and its CONTENTS arrive later still; clicking
slots before the server has filled them takes nothing and looks like a desync. One stack per pass,
two ticks apart, re-reading the screen each time.

**Every name in it was checked against the jar, and 26.2 had renamed most of them:**

    handleInventoryMouseClick(...)  ->  MultiPlayerGameMode.handleContainerInput(
                                            containerId, slotIndex, button, ContainerInput, player)
    ClickType.QUICK_MOVE            ->  ContainerInput.QUICK_MOVE      (the shift-click)
    Player.closeContainer()         ->  PROTECTED - but LocalPlayer overrides it public

That last one would have compiled nowhere and looked like a mistake in the caller.

**And `Screens` exists now** because 26.2 has no `Minecraft.screen` accessor — this file said so, in
its own 26.x notes, and I reached for it twice in one session anyway. It is tracked from
`ScreenEvents` in one place, which is what `ContainerWatcher` had been doing alone.

#### Superseded: "not built: automated withdrawal"

Repeated attempts to look up the 26.2 inventory-slot API were declined by the tooling in this
session — five times, across `javap` on `Slot`, on `Player`, a jar listing, and a Fabric screen
event. What WAS established before that, and is worth keeping so the next attempt starts further on:

    handleInventoryMouseClick(...)  ->  MultiPlayerGameMode.handleContainerInput(
                                            containerId, slotIndex, button, ContainerInput, player)
    ClickType.QUICK_MOVE            ->  ContainerInput.QUICK_MOVE      (this is the shift-click)

and `ContainerWatcher` already compiles against `menu.slots`, `menu.containerId`, `Slot.container`
and `Slot.getItem()`, so those four are proven. The gaps are `Slot.index` (avoidable — iterate
`menu.slots` and use the loop index, which IS the slot id), `Player.closeContainer`, and a
screen-level key hook.

### Making the loop safe to LEAVE (2026-08-20)

The loop worked when watched. Nothing in it was safe to walk away from, which is the only way Jack
actually wants to use it — and the bug that proved it was one I had just shipped.

**`Withdraw.phase()` stayed FAILED forever.** `Hud.advance()` gated auto-restock on
`phase() != FAILED`, so ONE failed withdrawal disabled restocking for the whole session: the loop
flew to a chest and sat there indefinitely with nothing in the log to say why. On an alt you are not
watching, that is an hour of nothing.

**Failure is a property of a CHEST, not of the withdrawer.** Each failure is now recorded against
its position with a 60-second cooling-off, so a bad chest is skipped and every other chest still
works. An EMPTY chest counts as a failure too — the index said it was there and it was not, and
without that the loop returns to it every two seconds forever. The window has to expire: a chest can
be refilled and a timeout can be lag, so permanent blacklisting turns a hiccup into a dead session.

**A STALL WATCH, because the printer never reports back.** `todo` shrinking is the only honest
evidence a block was placed — litematica-printer does the placing and tells us nothing — so the
world is the report. Ninety seconds with nothing placed, while following and not fetching, and the
loop says so and abandons that spot rather than pressing on it:

    STALLED — nothing placed in 90s at -24203 194 30012. Printer off, out of
    reach, or the spot cannot be built. 412 placed in 22 min (18/min), 3 spots
    finished, 2 restocks, 1 stall

**And a session report**, on completion and on `/cscan follow` off. A loop you leave alone has to be
able to say what it did, or the whole exercise is an act of faith.

### What the first real flight found (2026-08-20)

Jack ran it. Everything below came from that, and every one is a bug reading the code had missed or
that reading the code had introduced. Recorded because the pattern is the lesson: an unattended loop
fails by SITTING STILL, and nothing in a test suite notices a thing that does nothing.

**"if it fails to fetch it doesnt move on to a new chest, it just freezes."** `restockTargets` took
`hits.get(0)` — always the nearest container. Once a chest went into its cooling-off period the loop
was pointed at it, refused to open it, and sat there forever. A shortfall usually has several
containers holding it; the failed ones are skipped now and the next is taken.

**"it expects exact quantity... if only 64 are left it should just take all 64 and complete
elsewhere."** The index is a MEMORY of the last time a chest was opened, so it routinely promises
more than the chest holds. Withdraw takes what is there, puts that chest in the cooling-off set —
emptied or merely short, there is no reason to return this trip — and leaves the remainder in the
plan for the next recount to find somewhere else.

**"its trying to fly through walls."** Two causes, and neither was the steering:

- **The node budget was too small.** A* over open 3D air expands a SPHERE, so the frontier grows
  with the cube of the distance; 12,000 nodes could not reach across the island even with a clear
  line. The route came back empty and the caller fell through to flying STRAIGHT AT the terrain.
  Now 40,000 nodes and a **weighted heuristic** (×1.4) — greed finds a route in a fraction of the
  nodes and a few blocks of extra path costs nothing when you are flying.
- **`clear()` only sampled the centre line.** A line running diagonally between two blocks touched
  neither of their centres, so `simplify` straightened the route through the gap. It samples every
  quarter block now and checks the four cells a 0.6-wide body actually covers.

**And the flight was too fast to steer.** Movement is set directly along the aim vector, so the
eased turn is COSMETIC and nothing was limiting entry speed into a corner: at cruise the flight
covers 1.75 blocks in five ticks, against a waypoint radius of 1.8 — it passed the corner before it
could react. Waypoint radius is 1.0, it crawls when the next leg bends more than ~40°, and it slows
approaching any waypoint.

**Three more found by reading, all of the same kind:**

- **`Autopilot.stop()` was called on ARRIVAL**, and it sets `on = false`. Autofly switched itself
  off at the first chest and the unattended loop never flew again. Arriving is not disarming: it
  holds still, stays armed, and resumes when the target moves. Only the player takes it off.
- **`here` was 5.0 blocks against `Withdraw.REACH` of 4.5**, so between the two the withdrawal
  began, could never fire the use-item, timed out, and blacklisted a perfectly good chest.
- **`spotsDone` was never incremented**, so the session report said 0 spots however long it ran.

**And a stop.** `/cscan stop` cancels the withdrawal, the flight, the follow loop and every
highlight; `/cscan fetch` with no argument cancels just the fetch and skips that chest. An
automation you cannot stop in one word is one you have to fight.

### `autofly on` did nothing, and it was RIGHT to (2026-08-20)

Jack turned it on and nothing happened. Nothing was broken. **`autofly` is a MODIFIER, not an
action** — it reads its destination from `Hud.target()`, which only exists once `follow` or `goto`
has set one. On its own it armed, printed `autofly ON`, and sat there.

That is the same failure shape as everything else on this page: *a thing that does nothing, quietly*.
`tick()` had **three** silent early returns — no target, a screen open, and not actually in flight
mode (`/fly` permission is not the same as being airborne; you must still double-tap jump). Each one
returned without a word, and the one warning that did exist was a once-per-session flag that stayed
tripped after it had fired.

- `Autopilot.stalledBecause()` names the reason, and it is printed **by the command when you type
  it**, and shown live in the HUD as `[autofly idle: …]`.
- `set()` resets every one-shot warning, or a session that has already said its piece is silent
  forever after.

**A switch that reports success and then does nothing is worse than one that fails.** Report the
STATE, not the switch.

### The node budget: what it costs, and why it is not the lever (2026-08-20)

Asked whether `MAX_NODES` could just be 100,000. It could, and it would buy nothing.

**Where the cost is.** Expanding one node tests 26 neighbours, each needing up to 4 `free.at()`
calls (the cell plus three orthogonal corner-cut checks), each of those 1–3 world lookups. Call it
~300 lookups per node at the ceiling. So 40,000 nodes is up to ~12M lookups; 100,000 is ~30M, on
the client thread.

**But that ceiling is only ever reached on FAILURE.** With the weighted heuristic (`GREED` 1.4) a
route that exists is found in hundreds to low thousands of nodes — the budget is never touched.
Raising it only buys *searching harder before admitting there is no route*, and `NO_ROUTE_BACKOFF`
already bounds how often that happens (once per 3 s). 100,000 would turn each genuinely-impossible
route into a visible hitch and change nothing else. **Left at 40,000.**

**`MAX_RANGE` was the real one, and it was measured.** Beyond it `route()` refuses outright — no
nodes expanded, empty list, caller falls through to flying straight at the terrain, indistinguishable
from a broken router. It was **160**. The deck-to-lowland hop is **152**. Eight blocks of margin on
a route the loop actually asks for, and any design placed lower fails instantly and silently. Now
**256**; the gate is free, and the budget bounds the cost separately.

**The general rule: when a search "does not work", check what refuses it before the thing that
throttles it.** A cap that returns empty is invisible; a budget that runs out at least burns CPU
first.

