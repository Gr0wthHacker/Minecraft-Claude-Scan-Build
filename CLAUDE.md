# mctest — Minecraft island tooling

Two halves that share one file format:

- **`chunkscan/`** — a client-side Fabric mod (MC 26.2). Captures the world you can see into
  `.litematic` + `.scan.json`, places designs in Litematica, marks coordinates, highlights dig lists,
  indexes containers.
- **`mcbuild/`** — Python. Generates, audits, costs and diffs schematics against those captures.

Everything is anchored in **world coordinates** carried by the `.scan.json` sidecar next to every
`.litematic`. That sidecar is the contract between the two halves. No sidecar → no world position.

## Environment

| | |
|---|---|
| Game | Minecraft **26.2**, Fabric Loader 0.19.3, **LiquidLauncher** (CCBlueX) |
| Server | `skyblock.net`, **Minecraft 1.19**, `minecraft:overworld`, player `Enroniti` |
| ⚠ Version split | The client is **26.2**, the server is **1.19**. A block added after 1.19 is in the client registry, has legal states, renders in a card, passes every audit — and **cannot be placed**. `mcbuild/data/server_blocks.json` is the allowlist; `blocks.available()` is the check. |
| Mods folder | `%APPDATA%/CCBlueX/LiquidLauncher/data/custom_mods/nextgen-26.2/` |
| Schematics | `%APPDATA%/CCBlueX/LiquidLauncher/data/gameDir/nextgen/schematics/` |
| Java | no system JDK — `JAVA_HOME=%APPDATA%/CCBlueX/LiquidLauncher/data/runtimes/temurin_25/jdk-25.0.3+9-jre`; Gradle provisions JDK 25 into `~/.gradle/jdks` |
| Python | numpy, Pillow, PyYAML only. Run `python -m mcbuild <cmd>` from the repo root |

Paths live in **`profile.yaml`** (`mcbuild/profile.py` holds the defaults). Never hard-code them again.

**MC 26.x is unobfuscated** — mods use Mojang names directly, no yarn. Things that differ from older
guides: `ChunkPos` is a record (`x()`/`z()`), `Level.isClientSide()` is a method, chains are
`iron_chain`, Fabric client commands come from `ClientCommands.literal/argument`, there is no
`Minecraft.screen` accessor (use `ScreenEvents.AFTER_INIT`), chat via `player.sendSystemMessage`.
**Always `javap` the real jar before assuming an API** — it is faster than a failed build:
```bash
javap -cp ~/.gradle/caches/fabric-loom/26.2/minecraft-client.jar net.minecraft.world.level.Level | grep -i something
```

## The block knowledge base

Nothing about blocks is remembered — it is extracted from the game and checked in:

```bash
# 1. Mojang's own data generator: registry + every legal block state
java -cp "<client.jar>;<every jar under ~/.gradle/caches/modules-2>" net.minecraft.data.Main --reports --output <dir>
# 2. that, plus the client jar's textures, into mcbuild/data/blocks.json
python tools/extract_blocks.py --reports <dir>
```

Java `@argfile` needs **forward slashes** — it treats `\` as an escape. The JDK is `~/.gradle/jdks`
(the launcher's runtime is a JRE: no `javap`, no `jar`).

`audit` now validates every emitted state against this, so an illegal block state fails a test here
instead of Litematica silently refusing it in game an hour later. Wiring it up immediately found five
generators emitting `chain` (renamed `iron_chain` in 26.x), barrels carrying chest properties
(`type`/`waterlogged` instead of `facing`/`open`), and `lily_pad[rotation=0]` — lily pads have no
properties at all in 26.2.

# ANIMALS

Everything below concerns `gen/quadruped.py` and the taxonomy around it. It is the largest subsystem
and the one with the most hard-won detail, so it is documented as a whole rather than in pieces.

## The shape of the system

```
mcbuild/data/families.yaml   proportions + geometry choices, ONE table per family
mcbuild/data/species.yaml    a species = family + height + a coat + a few deltas (~6 lines)
mcbuild/gen/taxonomy.py      resolve(species) -> params, DERIVED as proportion x height
mcbuild/gen/quadruped.py     the build: mass -> relax -> features -> face -> coat
mcbuild/gen/anatomy.py       per-family LEG and HEAD geometry
mcbuild/gen/loft.py          superellipse sections swept along a spine; surface probing
mcbuild/gen/coat.py          voronoi / rosettes / blotches / shade
mcbuild/gen/smooth.py        relax + roughness metrics
mcbuild/data/rubric.yaml     the quality standard
```

A config only says WHERE the animal stands:

```yaml
gen: quadruped
params: {profile: jaguar, pose: sitting, feet: [...], look_at: [...], under: <capture>}
```

**Proportions belong to the FAMILY, not the species**, and block dimensions are DERIVED from them, so
a species is correct by construction rather than by tuning. Per-species tuning does not scale and does
not work: every animal tuned alone drifted toward whatever shape the smoothing and the block grid
preferred, and the silhouette test kept catching it — a bear that measured as a jaguar. Nothing in a
per-species dict says "a bear must sit where bears sit relative to cats". A family table says it once.

**Within a family, species differ by feature and colour, not by proportion.** A lion is a leopard with
a mane. So `silhouette` in the rubric is two-level — family separation by proportion, species
separation by coat and features — and scoring a lion and a jaguar as identical SHAPES is the metric
being right. Their distinction has to come from the mane, and it must be built big enough to break
the outline or it does nothing.

**But numbers alone build one animal five times.** Family proportions were not enough: a lion and a
jaguar came out 0.032 apart on silhouette. Each family also picks its own LEG and HEAD geometry from
`anatomy.py` — `plantigrade` legs put a bear on a long flat foot, `broad` gives it a wide skull with a
step down to the muzzle. That structure is what the numbers cannot reach.

## The build order (load-bearing)

1. **mass** — legs, body, neck, head lofted; nothing thin, nothing coloured
2. **relax** — cellular smoothing over that mass alone
3. **features** — mane, ears, horns, tail, trunk; *after*, because the rule that shaves a one-block
   pimple off a shoulder eats a horn whole
4. **face** — read off the SMOOTHED skin with `loft.surface_out`, never from a computed radius
5. **coat** — the pattern, over the finished shape

Anything derived from the standing skeleton must follow the POSED one: leg length sets the belly line,
and the belly line sets the countershading. Getting that wrong leaves legs floating under a hovering
barrel, or pale bands round a sitting cat's knees.

## Stance

`POSES` holds standing / sitting / couchant / prowling / grazing as multipliers — fore and hind legs
shorten independently, the belly line tilts, the neck is re-aimed. No pose is a separate build path.

`tools/stance.py <config> --from X Y Z` scores every pose on four measured things and says why:
**behaviour** (what the species does, from the family table — a sitting giraffe is a sick animal, not
a style choice), **site** (each pose is BUILT and its real contact footprint tested against the relief
under it), **legibility** (silhouette height against viewing distance; past ~30 blocks a couchant
animal is a lump), and **anatomy** (does it survive the build). They disagree often, which is the
point.

`leg_phase` and `head_turn` add deliberate asymmetry and are RECORDED, so the rubric relaxes its
symmetry expectation by exactly what was asked for. A diagonal leg phase is genuinely left-right
asymmetric and costs ~25 points of symmetry — rarely worth it; a head turn costs ~3.

## How big it has to be

`tools/scale.py <species>` — every feature needs a minimum block count to read, and every feature is a
fixed fraction of height, so `min_blocks / fraction` gives the height below which it cannot exist.
The largest such height is the animal's critical size.

    felid 23 · ursid 26 · caviomorph 23 · proboscid 30 · giraffid 59

(ursid was 24 under the old, wrong ursid proportions; correcting them moved it to 26. The floors
move when the tables do, so read them from the tool, not from here.)

**It is not the biggest animal that must be built big, but the one with the finest features relative
to its own size.** A giraffe's leg is 5% of its height so a 3-block leg forces 59 blocks of giraffe;
a jaguar's is 13%, so the same leg forces 23.

`--measure <config>` builds at a range of scales and reports the real curve. **Size sets a ceiling;
tuning sets the plateau.** You cannot tune past the size floor and you cannot size past a wrong ratio.

A second floor matters as much: a feature at its minimum EXISTS but carries no structure. A bear at
24 has a 6-block head — one above the floor — with no room for a broad skull and a stepped muzzle. It
took 30 before the family geometry could show.

## The quality standard

`mcbuild/data/rubric.yaml`; `python tools/rubric.py <design>` scores against it.

**Gates first, and they are not trade-offs**: one connected piece, grounded, no placement problems, no
functional blocks used as skin, every feature above its legible block floor. Fail one and no score is
printed.

Then seven weighted dimensions — **proportion** .22 · **silhouette** .16 · **form** .16 ·
**features** .15 · **surface** .12 · **palette** .10 · **symmetry** .09 → reference ≥.90, good ≥.78,
acceptable ≥.65.

**The reference is the BUILD'S OWN INTENT, not a standing table.** The generator records a
`designed` block in every sidecar — its target proportions as fractions of its own posed height —
and `proportions.designed()` reads it. Before this the audit re-derived what a pose does with a
parallel first-order model, and the two diverged badly: measured-over-wanted hit **2.97** on a
sitting bear's leg width and **1.86** on a prowling jaguar's neck, because `fold` widens a limb
about three times as much as the model assumed and `drop`/`lean` re-aim the neck without it
knowing. There was a per-FAMILY bias on top — a standing bear read +10..20% where a standing
jaguar read −5% — so no single standing table could serve both. It is the same rule
`proportions.measure` and `rubric.score` already follow: one source, so two tools cannot drift.
`posed()` remains as the fallback for older builds and for the sizing tools, which must answer
"how big must this be" with no build in hand.

Three things had to follow from it:

- **Verticals are measured from the FEET.** Legs seek their own ground, so on rolling terrain the
  downhill limbs reach below the nominal feet and the model's origin sits under them. Measuring
  from the origin compared two different zeroes and inflated every vertical on the lowland jaguar,
  while the horizontals matched exactly — that asymmetry is the tell.
- **`tilt_slack` has a FOLD term, not just a tilt term.** Couchant folds both legs almost equally,
  so a slack built only on the fore/hind difference saw 0.09 and allowed 34% where the build was
  46–60% off. Every couchant animal was marked deformed for lying down correctly.
- **A measure the pose cannot yield is OMITTED, not zeroed.** A couchant animal's floor is two
  courses up, so the window that should hold only legs holds the barrel too; `leg width` is absent
  rather than wrong, and the dimension is scored out of what could be taken.

And one that is not about pose at all: **a mane is not back.** A lion's mane is a 1000-cell ball
centred over the withers, and taking the greater of shape and design measured the mane and called
the barrel 50% too deep. Where a ruff is recorded, the withers falls back to the designed back
line — the same reason `anat_top_y` already excludes crown features.

- **form** asks whether the skin carries light — tonal range, and whether luminance follows sky
  exposure. Measured on BINNED means so a coat pattern does not destroy it. It is what separates a
  statue from a coloured shape.
- **features** reads `features_built` from the model's own sidecar — the generator counts cells as it
  emits them. It caught the giraffe's 6-cell ossicones and 3-cell mane as too small to see.
- **symmetry** mirrors across the sagittal plane the recorded FACING defines, and allows for
  asymmetry that was deliberately asked for.

Four questions are printed rather than scored, because a number cannot settle them. Answer them
yourself before shipping.

## The process, in order

```bash
python tools/scale.py <species>                    # 1. how big does it have to be
# ... write ~6 lines in species.yaml ...
python -m mcbuild gen configs/<x>.yaml --ship      # 2. build
python tools/stance.py configs/<x>.yaml --from ... # 3. which pose
python tools/rubric.py "<design>"                  # 4. score it; read the WEAKEST dimensions
python tools/refine.py configs/<x>.yaml            # 5. sweep, scored by the WHOLE rubric
python tools/compare.py --family <family>          # 6. against its SIBLINGS, not just the table
python tools/views.py "<design>" --zoom 10         # 7. LOOK at it. Always.
python tools/panel.py "<design>"                   # 8. and have it REVIEWED - see below
```

**Never tune one dimension.** Sweeping `smoothness.py` alone took the bear's surface 0.60 → 0.73 and
its proportion 0.88 → 0.50: every smoothing pass rewards thickening, so it inflated the animal until
the silhouette test called it an elephant, and the total *fell*. `refine.py` sweeps the same
parameters against the weighted rubric and prints what each dimension gained or lost.

**And always look.** The rubric passed a bear, a lion and a polar bear at GOOD when all three were
visibly the same animal — because `silhouette` compares each model to a reference TABLE and nothing
compared the models to EACH OTHER. Numbers did not catch it; one glance did.

## Traps, each of which cost a rebuild

- Smoothing **welds legs together** — two surfaces across a narrow gap look exactly like a dent.
  `relax(forbid=...)` bars the air between them, but the reach must cover the leg's *widest* section
  or it carves the haunch off instead, and it must be clamped to half the leg spacing or it protects
  nothing. `fold` widens a leg, so spacing must be computed from the FOLDED radius.
- Smoothing **eats thin limbs**: `keep` counts neighbours a slender leg does not have. Legs go in as
  `protect`.
- **Feature sizes must scale.** A tail hardcoded at 13 blocks was longer than a deer's legs and broke
  the model in two. Anything in absolute blocks has this latent.
- **Anything clinging must be ANCHORED to the built surface**, never placed at a computed radius —
  relax moves the surface. The mane came off as seven floating fragments, the ossicones detached, the
  tail floated 45 cells clear. `loft.surface_out` and `loft.crest` exist for this.
- **6-connectivity**: a swept feature whose cells are only diagonal neighbours is not connected. Ear
  tips broke off this way.
- **Palette by measurement** — `blocks.nearest()` over all 1193 real colours. Avoid functional blocks
  (`bee_nest` is the closest golden tan in the game and carries a face texture and bee states).
  Sandstone does not exist on this skyblock.

## The lowland scene (2026-08-19)

Three animals on the lowland floor, in `configs/lowland_{jaguar,capybara_alert,bear}.yaml`, verified
against `out/lowland_planned.litematic` (the lowland composited onto `island_lower` with
`tools/plan_merge.py`, because the ground they stand on is a DESIGN and not yet built).

**Why these species.** The lowland is Minecraft's lush-caves palette — moss, azalea, fern, dripstone,
71 lanterns, no daylight — which is a cave-mouth jungle floor. Jaguar and capybara is the real
predator/prey pair of the Pantanal, jaguars den in caves, and bears den in caves by definition. The
lion, polar bear and giraffe were rejected on habitat; the giraffe also does not physically fit
(57 tall against 46 blocks of headroom under the void isle, whose lowest block over the main pad is
Y86). The **elephant was rejected on measurement**: it is built from `deepslate`/`tuff`/`stone`,
which is the lowland's own rock palette — min ΔRGB **0** to the ground it would stand on.

**The site is smaller than it looks, and that governed everything.**
- Of 5,851 ground columns, **154 are open to the sky** (2.6%) — the outline IS the island's shadow.
  Nobody sees this from above; it is a walk-in underworld, so faces and poses matter and the
  top-down silhouette does not.
- The models are enormous next to it: a couchant jaguar is 15x60, a standing capybara is 14x50
  because its head projects 31 blocks past its feet. **The lowland holds three animals of this
  size**, measured by greedy fill — a fourth has nowhere to go. The three-capybara group and the
  bear-beside-a-tree in the original sketch both had to go.
- `stance.py` overrode two pose choices, and the whole gap was SITE: prowling scored 0.69 against
  couchant's 0.83 because a prowling cat's contact footprint is 13x63 and the ground under it rolls
  8 blocks. Sitting cost the bear the same way. There is **one** flat patch big enough for a sitting
  bear and the stalk needs it.

**The couchant penalty is gone.** It was never a property of the pose: `proportion` was scoring
against a re-derivation of what the pose does, and that model was wrong. With the audit reading the
build's own recorded intent, the lowland jaguar went 0.68 → **0.79** and the bear 0.68 → **0.81**,
both at 8/8 measures in tolerance. The poses `stance.py` picked on site grounds are now the ones
the rubric likes too, which is what agreement between two honest tools should look like.

## What this system can and cannot build (2026-08-19)

Settled by PLAYER RECEPTION, not by the rubric and not by my renders. The builds players picked out
are the **sky bird** (an 83-block wingspan of layered primaries) and the **giraffe** (a neck); the
**gecko** — splayed limbs on a wall — is the next best thing in the repo. Every animal that reads
badly is a mammal.

**The line is PLANAR/COLUMNAR against VOLUMETRIC.** A spread wing, a neck, a stilt leg, a splayed
limb: flat sheets and straight tapers, which is what voxels render natively. A cat's shoulder or a
bear's haunch is compound volumetric muscle, which voxels render worst of anything — and no amount
of scale rescues it. The jaguar at 2.6x and 60,000 blocks failed exactly as the 27-block one did.

This is not the same as "hardware vs muscle", which was my earlier guess and was the wrong cut. An
elephant's trunk is hardware AND a taper; a caiman's body is hardware and still a volume.

**Build these:** birds, bats, wading birds, reptiles with splayed limbs, anything whose identity is
an outline. `heron.py` and `bat.py` are the two worked examples, both bespoke — the quadruped family
system is built around a mammal barrel and should not be used for them.

**Do not build:** cats, bears, or anything whose species is carried by muscle mass. `quadruped.py`
still holds eight of them and they score GOOD; the score is measuring the wrong thing.

## The lowland scene, as shipped (2026-08-19)

Four designs, all one piece, none sharing a cell with another. `/cscan place` each by name — do NOT
use the bare form, it places all 54 designs including a shelf of scratch animals.

| design | blocks | what it is |
|---|---|---|
| `Lowland` | 35,197 | the ground itself, Y24–47 |
| `Lowland Heron` | 8,168 | grey heron, standing, Y41–124 |
| `Lowland Flamingo` | 7,625 | pink, one leg tucked, kinked bill, body tilted, Y41–133 |
| `Lowland Capybara Flee` | 6,725 | running, Y38–59 |
| `Lowland Bat` | 2,409 | roosting on its OWN floating rock, a stone tower on its crown, Y112–153 |

The mammal predators were **retired**, not moved: the jaguar and the bear are the two shapes this
system cannot build, they took the floor the birds needed, and keeping them would have been keeping
a spotted table because it was already made.

Three siting facts that cost time and are worth keeping:

- **Headroom is not 46 blocks, it is a median of 151.** The earlier figure was measured only under
  the void isle's footprint, which is 1,504 of the lowland's 5,851 columns. A 90-block bird fits
  almost anywhere; it just must not be under the isle.
- **The birds stand at Y42, not Y40.** The ground rolls 4–5 blocks under a splayed foot, so standing
  on the MEDIAN height buries the toes on the high side. Stand clear of the maximum.
- **The bat carries its own ceiling.** It no longer hangs over the lowland at all: `perch` builds a
  ragged lump of the island's own stone above the claws, mossed on top with vines off the rim, so
  the design is self-contained and can hang in open air. That freed it from competing with the
  birds for airspace — it now roosts in the gap between the bee farm (X −24213..−24186 /
  Z 29995..30048) and the mushroom lobe (X −24158 / Z 30040), at Y112–138 with the grip at Y130.
  **Fifty-two** blocks under the plate, in a column that is genuinely open sky: 0 of the
  ruin's 121 columns have island overhead, and only 16 of the rock's 195 do. The config
  said "twenty blocks under the plate, the plate's lowest block is Y150" — Y150 was the
  CAPTURE'S FLOOR, not the island's underside, which over this gap is Y200. Read a
  clearance off the capture's content, never off its bounding box.
- **Wingspan is a function of how far away it hangs.** At 106 wide it was absurd; that was a
  consequence of hanging it 109 blocks up, where anything smaller could not read. Roosting close
  and furled (`spread: 0.5`) it is 46 wide and still shows its finger struts.
- **The rock carries a TOWER, and its shape was decided by the viewing angle.** The perch reads as
  a piece that broke off the plate, so it carries a piece of what was BUILT on the plate. It sits in
  open sky 52 blocks below the rim, seen from steeply above as much as in profile, so it had to work
  in PLAN — which ruled out an arch (negative space you cannot look through does nothing from
  overhead) and a bare snag (a few scattered pixels). From above it is a ring of dark merlons round
  a lit deck.

  The first attempt was a sheared stub with a jagged top and it was rejected on sight as *"a tossed
  grouping of vague blocks"* — correctly. **What makes voxels read as ARCHITECTURE is regularity and
  openings, not damage.** It now stands full height and regular: a flared plinth, a door with a
  lintel, three glazed slits with sills, a string course, a corbelled overhang, a parapet and
  crenellations — and the ruin is ONE broken arc with its merlons on the moss below. A building that
  has taken damage, rather than damage that vaguely suggests a building. Five things it cost:

  - **The shear must be a PLANE, not a cosine** — a cosine falls away smoothly in every direction
    from the high point, which is a cone, and it built a witch's hat. (Kept for the broken arc.)
  - **`cracked` and `chiseled` stone brick are within 4 RGB of plain**, so weathering a wall with
    them is invisible: it gave the tower no tone and no horizontal at all. Every band that reads is
    `deepslate_bricks` — 51 darker, and the island's own stone dressed. Plinth, string course,
    corbel and merlons all take it, which is also what makes them look like one building.
  - **The weathering hash must be on the CELL.** Hashed on the course, every block in a course came
    out identical and the wall was horizontal stripes of one material.
  - **The crenellation course must be left EMPTY by the wall loop.** Building a full ring there
    first and then alternating merlons over it repaints cells that already exist — it alternated
    perfectly and changed nothing, and the crown was a plain drum. `test_the_crenellations_are_
    actually_crenellated` pins it, because nothing about the code looked wrong.
  - **From directly above, a merlon in the parapet's own block is invisible** — a plan view sees
    only the topmost cell, and a merlon and the course under it were the same colour. Dark merlons
    are the only reason the crown reads from the angle that matters.

  A `glass_pane` needs its connection state set ALONG the wall; with every side false it renders as
  a lone post rather than as glazing. Plain panes are `ok` tier — every stained pane and plain
  `glass` are `expensive` on this economy, which is odd given a pane is made from glass.

- **A flamingo does not stand level.** Its body slopes down to the breast with the tail carried high
  and the neck leaving from a low point at the front. The body used to be one upright ellipsoid,
  which cannot lean however the rest of the bird is posed — it is swept along a tilted spine now,
  and `body_tilt` is 3.0 for a flamingo against 1.2 for a heron. Level, it read as a pink heron.

### Cost: the whole scene is cheap tier

It was not. The first palettes came to **6,893 expensive blocks** — the heron alone was 45% concrete
and terracotta — for tones that wool and plain stone give away. `light_gray_concrete` → `stone` is 11
in RGB; `gray_concrete` → `gray_wool` is 15; a flamingo is the one animal whose colour needs no clay
at all, because sheep come in pink, red and magenta. **Now 0 expensive across all four**, and the
bat's 210 `ok` are the deepslate in its perch.

Two traps worth remembering, both hit while fixing this:

- **`_eye_ring` was picking out of the whole registry.** It chose `quartz_block` (expensive here),
  and once filtered to cheap it chose `stripped_pale_oak_log` — a **1.21 block**, because
  `blocks.available()` is a no-op while the allowlist is provisional and cannot say no. A decorative
  ring of four cells does not need the registry; it now picks from a short known-safe list.
- **Three tones of the same colour beat two tones and a third hue.** `magenta_wool` banded between
  red and pink read as a bruise. Red coverts over pink with BLACK primaries is both cheaper and
  correct — black flight feathers are the flamingo detail.

## The void ladybird (2026-08-19)

`configs/ladybug.yaml`, `mcbuild/gen/ladybug.py` — a seven-spot ladybird on a leaf, hanging in open
void under the island at **-24207 104 30018**, Y104–121.

**Why this animal passes where eight mammals failed.** The line is not "insects vs mammals", it is
the same PLANAR/COLUMNAR-vs-VOLUMETRIC line as before, with a third case: a ladybird's identity is
a **pattern on a single convex dome**. The dome is a voxel primitive, not a blend of five muscle
groups, and nothing about it has to be measured to a percent — it only has to carry the right
spots. It is the same category as the elephant's trunk and the giraffe's neck. And the canonical
view of a ladybird is the PLAN, which is the view voxels give away free.

**Size comes from the spots, and then from their SPACING.** A spot needs ~3 blocks to read as a
disc, which sets the shell's width floor at ~15. But seven spots also need LENGTH: at 17 long the
elytra behind the pronotum was 12 blocks, four rows of spots sat 3 apart, and 3-block spots at
3-block spacing touch — they merged into one mass and the beetle read as a black beetle with red
veins. **21 long** gives a 16-block elytra, rows 4 apart, and a clear block of red between spots.

**The leaf is the scale reference, not decoration.** A red dome alone in the void is an object of
unknown size; on a leaf it is instantly a beetle. So the blade has to stay visible past it — the
first build put a 17-long beetle on a 26-long leaf, it covered 65% of it, and all that showed was
a green fringe.

**The site was measured, not chosen**, and two things about that generalise:

- **Reserve design CELLS, not bounding boxes.** `Island Belly Full` and `Lowland` each span the
  whole underside while occupying a thin skin of it; box-reserving them says the void is full.
- **Skip the scratch shelf.** Globbing `out/*.litematic` reserves `JAG big` (57,994 cells),
  `X elephant`, `S1.4`, `islet_planned` — parked at the default origin lock and claiming void they
  have no right to. Reserve what `sync.yaml` tracks, plus the lowland scene.
- **Do not take the first box that fits.** It put the leaf 2 blocks under the Shop Islet's raft and
  5 from the void giraffe's neck. A hanging ornament wants the middle of the empty part, so the
  siting used a distance transform (iterative dilation — numpy only, no scipy) over built + designed
  cells. The winner is 15.7 blocks clear of anything, in a free pocket of 35×24×30; the island's
  underside is 34 above and there is nothing at all below. The nearest built block is one of the
  eight old plate vines, 5 away.

### Two traps that produced a clean audit and a wrong build

- **`Canvas.get` returns -1 out of bounds, and -1 is TRUTHY.** Every `if c.get(x, y, z):` in a
  generator therefore reads everything past the edge as solid rock. The ladybird's spots searched
  downward for the top of the shell from two courses above the canvas ceiling, "found" a block
  immediately every time, and painted all seven caps into thin air above the beetle — the shell
  shipped plain red while the audit, the BOM and the component count all said the build was clean.
  **`Canvas.solid()` exists for this**; `bat.py` and `heron.py` carried the same latent bug and are
  converted. `tests/test_ladybug.py` pins both the helper and the truthiness of -1.
- **`round()` is banker's rounding.** The clod's centre landed on x.5, and `round(11.5) ==
  round(12.5) == 12` while `round(13.5) == 14`, so every other column was skipped and the lump came
  out as eighteen separate one-wide towers. Keep centres INTEGER and add offsets to them.

One piece, 2,394 blocks, 0 problems, all cheap tier.

## The panel review — the last step before shipping

`python tools/panel.py "<design>"`. The rubric measures proportion, surface, palette, symmetry, and
an animal can score GOOD on every one of them and still be a spotted table. That happened. Nothing in
the pipeline asked the only question that finally matters: **would a stranger name this animal?**

It cannot be measured, so it is asked — but asking it fairly needs the right evidence, from more than
one direction. The sheet shows the profile (axis chosen from the RECORDED FACING, because picking it
by hand was got wrong twice in one session), a flat **silhouette**, a greyscale **value** panel, the
plan, **distance thumbnails** at 1/2, 1/4 and 1/8, and a 2-block **player bar** for scale. Then two
panels, because they catch different things — the visual critic on silhouette, mass, line and value;
the Minecraft player on distance legibility, whether it looks BUILT, scale against a person, and the
three or four angles a path actually allows.

**Write both verdicts down.** A panel that is not recorded is one the next good-looking score quietly
overrules.

### First verdicts (2026-08-19)

**X elephant — PASSES both.** The silhouette alone names it: trunk curve, ear, domed head, columnar
legs. The value panel shows real rounding. It still reads as an elephant at the 1/8 thumbnail. This
is the control the panel is calibrated against.

**X jaguar — FAILS both, badly.**

*Visual critic.* You cannot name it from the silhouette — it reads as a low table, or a bull; the
only cat cue is the tail. There is no weight anywhere: the outline is a constant-depth rectangle from
shoulder to rump, so the animal has no centre of gravity. No line of action — the spine is a straight
rule and the belly is a second straight rule parallel to it, which is the most inert shape available.
The value panel is flat, and the pale belly is a hard-edged band that *reinforces* the slab rather
than describing a form. Fix first: **the legs** — constant-width posts at the extreme corners are
exactly what makes it a table.

*Minecraft player.* At 1/4 and 1/8 it is a brown smudge with a line coming off it; the spots turn to
noise rather than pattern. It does not look built — one wood tone with black wool speckles, no block
variety doing any work, no stairs or slabs breaking the grid. Scale is fine, ~15 player-heights long.
Of the three angles a path gives you, only the side is even attempted, and the plan view reads better
than the profile, which is backwards for something standing on the ground. The comment it would get:
*"why does your jaguar have four table legs and a flat back?"*

### Second pass — what fixing all five did (2026-08-19)

All five were done. The jaguar is no longer a table and no longer a deer; the silhouette reads as a
cat. The specific changes, and what each was actually worth:

1. **The belly got its own line.** `_body` now takes a fifth keyframe column, `lift`, so the
   underside is set independently of the floor. High through the loin, near zero under the chest.
   This is the one that stopped the profile being two parallel horizontals.
2. **Legs got a thigh, a cannon and a foot.** The visible part ran near-constant at +0.15, -0.30,
   +0.05, +0.40 — a post. It now tapers 1.05 → -0.20 → 0.30.
3. **The barrel went bimodal** — mass over haunch and shoulder, waist between. Fixes the plan view
   outright.
4. **The back got a shoulder rise**, via the depth-taper column.
5. **The felid skull was wrong in two ways at once.** Its half-width tapered steadily to a point
   while its centre drooped, which is a SNOUT — the panel read it as a deer and was right. And
   `head length` was 0.329 of shoulder height where a cat's is about a quarter. Now blunt, wide
   through the cheeks, and 0.258.

**Size is still the ceiling.** At 27 blocks the barrel is ~10 deep, so a 0.15 tuck is one and a half
blocks and most of this is sub-block. It reads as a cat, marginally. At 2.6x it reads clearly, the
rosettes resolve into actual rings rather than speckle, and the tuck and the taper are all visible.
**If a cat matters, build it big** — that is what the emerging half-figure is for.

No animal regressed: bear .84, lion .86, capybara .83, leopard .82, elephant .81, giraffe .80,
jaguar .80, polar_bear .78.

**Still open:** the back is flat across the middle (a cat's rather is, so this may be fine); the
legs still read as posts at 27 blocks; and the bear's eyes still do not read against `mangrove_wood`.

### What the two panels agree on, in order

1. **Legs must merge into the body as a haunch and a shoulder**, and taper to a slim cannon. Posts at
   the corners are the single biggest failure.
2. **The belly line must not be parallel to the back.** It is `floor = rump + (chest - rump) * t` —
   a straight line by construction, so a deep chest and a tucked loin cannot be expressed at all.
3. **The back line needs a shoulder rise and a rump fall** to break the horizontal.
4. **The barrel is a spindle** — widest mid-body, tapering to both ends. A quadruped is widest at the
   shoulder and haunch with a waist between. A bimodal width profile was tested and fixes the PLAN
   view immediately; it does nothing for the profile, which is governed by (2).
5. **The surface must look built** — a 3-tone coat and real use of the slab shell, not one tone plus
   speckles.

**The pattern across all eight animals:** this system succeeds where identity is HARDWARE — the
elephant's trunk and ears, the giraffe's neck, the capybara genuinely being a blocky rodent — and
fails where identity is MUSCLE AND PROPORTION, which is every cat and both bears. Scaling does not
help: the jaguar at scale 1.7 with 8,349 blocks fails exactly as the 27-block one does.

## Faces, and the visual audit that found them (2026-08-19)

Jack looked at the renders and said the bear was a cow, the jaguar's face was a mess and the
capybara had "no eyes, just a mask". All three were true and none of them was visible in any score.

- **The eye was the same block as the coat pattern.** A jaguar's eyes are `black_wool` and so are
  its rosettes, so an eye landed among a dozen identical black cells. The pattern is now kept off
  the whole skull (`_face_zone`) — shading is NOT, because on a dark animal the shading is the only
  thing lifting the face clear of the coat, and flattening it cost the bear the eyes it had.
- **The eye was a two-cell bar, not a bead.** With the muzzle painting either side of it the
  capybara's brow read as one continuous stripe. It is now one cell, ringed with every solid
  neighbour forced pale.
- **The ring was the muzzle block, which is often the coat.** `stripped_jungle_log` on `acacia_log`
  is a 2-point difference. `_eye_ring` now takes the muzzle only if it is 35 luminance clear of the
  coat, and otherwise picks the palest plain block in the registry by measurement.
- **The ears were flat slabs at brow height, pushed out sideways** — which is a cow, or a moose. A
  small ear now sits ON the cranium above the eye. An elephant's really is a side-hung fan and keeps
  the old placement, switched on `ear_size >= 1.5`.
- **`drop` did nothing at all.** `rise = 1 - 2*drop` was computed in `_neck` and never used, so the
  neck stepped up one course per segment whatever the pose said. Every grazing, stalking and leaping
  animal ended with its head at the top of a rising neck. This is what the earlier pose diagnostic
  was seeing when it put the prowling jaguar's neck 1.86x and the grazing bear's 2.14x adrift.
- **Moving the ears broke the withers.** `_segment` scans whole courses, so on a cat — whose head
  sits at body height — it measured the head, and then the ears: the jaguar's barrel read 40% too
  deep for a change that never touched the barrel. The withers is now taken inside the recorded
  body window.

**Still wrong: the bear's eyes do not read.** They are built and correctly placed, but `mangrove_wood`
is dark enough that a black bead on it has nowhere to go, and the broad blunt skull hides them from a
straight-on view. The fix is a lighter face mask on the ursid coat, not more geometry.

## Known-wrong, for whoever picks this up

- **The reference proportions are estimates, uncited.** One was simply wrong: the ursid table gave a
  bear a cat's leg clearance (0.469) and a short body, and no amount of geometry work fixed the
  result until the numbers were corrected to 0.346 / 1.230. Suspect the tables before the code.
- **`MIN_BLOCKS`, `COMFORT`, the rubric weights and the grade thresholds are all invented.** Every
  "viable height" and every grade rests on them.
- **The colour DB samples the TOP face; statues are seen from the SIDE.** `oak_log` differs by 101,
  `bone_block` (the giraffe's whole coat) by 68. And **biome tint is missing** — 20 tinted blocks,
  including every leaf, extract as grey. Both deliberately deferred.
- **Validation is circular**: `views.py` renders with the same colour DB the palette picker optimises
  against. Nothing built in this system has been placed in Minecraft and looked at.
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

## The taproot staircase head (2026-08-19)

`configs/taproot_entrance.yaml`, `mcbuild/gen/stairhead.py`. Jack cut a well through the deck floor
and left it raw; this turns the hole into a front door. 263 blocks, 0 new problems in context.

**The site, all measured off the 19:09 capture:**

| | |
|---|---|
| Y200–201 | ceiling over the well — 6–7 courses of headroom |
| Y194 | the deck floor, well cut through it at X-24205..-24200 / Z30002..30010, narrowing to a 3-wide neck at X-24205..-24203 for Z30002..30004 |
| Y191–193 | open undercroft; the shaft cased at Z30010–30011 |
| Y190 | the belly skin you land on, with a 3×3 hole at X-24203..-24201 / Z30008..30010 |
| Y189 ↓ | the existing workshop stairwell, then the root stair |

So the entrance has exactly one job in the vertical — carry you four courses from the deck to the
undercroft floor and hand you to the shaft that is already built. The neck is 3 wide, which is a
flight. Everything else is what makes it read as architecture rather than as a hole with steps in
it: an apron ringed out of the deck paving, a dark `deepslate_bricks` lip that draws the opening, a
revetment lining the cut faces (or the handsome opening looks down onto a building site), a
balustrade of wall-plus-slab at 1.5 blocks, four corner piers carrying lanterns, and lanterns on
chains hung over the well so the light falls down the shaft rather than onto the deck.

**A chain hangs from the block ABOVE it**, so each string finds a real ceiling first — placed blind
one of the four came away as loose links and the audit called it out as a cluster with nothing to
place against. Same failure as the bat perch's vines.

The palette is the atelier's four greys on purpose — the court below, the workshop above and this
head between them should read as one hand. `deepslate_bricks` is the one addition, for the reason
the void tower needed it: cracked/chiseled/plain stone brick are all within 4 RGB of each other, so
they carry texture but no tone and cannot draw a line.

**It repaves 52 cells of existing deck** for the apron. That is intentional — the apron is what
stops the opening reading as a rectangle punched in a field of stone brick — but it is 52 blocks to
break, so it is stated here rather than discovered.

## The deck floor (2026-08-19)

`configs/deck_floor.yaml`, `mcbuild/gen/deckfloor.py`. 701 blocks, 0 new problems in context.

**The entrance audit is what produced this.** The taproot stair head walks correctly — deck 195.0 →
four treads → undercroft 191.0 → 7 standing cells at the shaft lip — but it does not READ, and no
amount of further detail on it would fix that. Its apron is grey on a grey field. **An entrance
cannot be the figure when the ground is the same tone and equally busy**, so quieting the floor is
the other half of building the entrance, not a separate job.

**The deck, measured.** 2,145 columns on the Y194 course:

| | cells | blobs | |
|---|---|---|---|
| dressed brick | 1,060 | — | the intended floor |
| green | 499 | **63** | ONE real 269-cell moss farm + 230 cells of scatter |
| rough stone/cobble | 266 | **63** | biggest blob 58; the rest scatter |
| vine | 236 | **127** | 127 blobs averaging under two cells |

~730 cells in 113 blobs are noise, not design; only **44%** of the floor is walkable with three
courses clear; **120 chests** still stand on it; lighting is **37 torches to 10 lanterns**.

Three things this cost, each of which produced a plausible wrong answer:

- **The deck is the biggest connected BLOB of the course, not the course.** Taking every cell sweeps
  in 97×93 of island underside — belly scraps, rim shelves — and the edge course alone came to 819
  cells with **59 free-floating clusters** drawn round islands two cells wide. Deriving the blob
  (2,145 → 1,725) keeps it a deck design with no hand-written box.
- **A rectangle will not wall the moss farm.** It is a WORKING farm — 29 ice, 12 water, glow lichen —
  and it sits on an irregular lobe: the box one cell out is **58% air**, two cells out **70%**. A
  rectangular room floats over holes and cuts the water. The wall follows the farm's own dilated
  edge and lays only where there is floor under it — which comes to **41 cells**, because most of
  the farm's boundary is against open air at the deck's edge, and you cannot walk in from a drop.
- **`plan_merge` fills empty cells only.** Comparing before and after through it showed a 30-cell
  change, *all of them `air -> something`* — that is the tell. A design whose job is to REPLACE is
  invisible to it. Composite with overwrite to see a repaving design; the real change is 492 cells.

`deepslate_bricks` again for the edge and the zone bands, for the same reason as the void tower and
the stair head: cracked, chiseled and smooth stone are all within 4 RGB of plain, so they carry
texture but no tone. It is the only strong value contrast this economy offers at cheap-or-ok tier.

**Still open on the deck:** the 120 chests (the Store Hall's 68 slots are built and waiting), the
37 torches, and the 44% walkable figure — all of which want the chest move done first.

## Build & test

```bash
python -m pytest -q                                   # 187 tests, keep green
cd chunkscan && ./gradlew build test -q                # writes build/libs/chunkscan-<ver>.jar
python chunkscan/verify_synthetic.py                   # Java writer vs Python reader, block for block
```
Jack uploads the jar through the launcher himself — **do not copy it into `custom_mods/`**, that
creates a duplicate mod id and Fabric refuses to start.

## The daily loop

```bash
python -m mcbuild sync            # cut the newest scan, regenerate ground designs, progress + shop, learn
```
`sync.yaml` says which designs regenerate and which get reported. After that:

```bash
python -m mcbuild progress <design...> --world out/island_now.litematic
python -m mcbuild shop <design...> --world out/island_now.litematic --have
python -m mcbuild card <design> --world out/island_now.litematic     # one PNG for chat
python -m mcbuild diff <old scan> <new scan>
```
In game: `/cscan island` to scan, `/cscan place` to place every design at its recorded origin.
While building:
```
/cscan need <design>     materials for the unbuilt cells within 48 blocks + which chest holds each
/cscan next <design>     the next 24 cells, marked green, lowest first so you never build past reach
/cscan check <design>    cells where the world holds something else, marked amber
```
These read `<design>.work.json`, so run `python -m mcbuild work <design> --ship` if you hand-edit a
design without regenerating it.

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
  shade), `smooth.py` (relax + roughness), `shell.py` (half-block surfacing: which cells earn a
  slab, and which blocks may supply one). Data in `data/families.yaml`, `data/species.yaml`,
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
| `heron.py`, `bat.py` | in `gen/` — the two builds that play to what the medium is good at |
| `views.py` | …and it draws slabs at half height, so half-block work is visible here |
| `plan_merge.py` | composite designs onto a capture |

`proportions.measure` and `rubric.score` are shared entry points — `stance`, `refine` and `scale` all
call them, so a change to how something is measured cannot drift between tools.

**`chunkscan/`** (client only, `src/client/java/dev/jack/chunkscan/`)
`ChunkScanClient` (commands) · `WorldCapture` (chunks → `Capture`) · `LitematicWriter` (NBT out) ·
`SidecarWriter` · `ScanRunner` (glue + archive) · `Litematica` (reflection bridge, soft dependency) ·
`Markers` · `Storage` + `ContainerWatcher` (container index) · `Highlight` (particles) · `AutoScan` ·
`Designs` · `Work` (reads `.work.json`, diffs against the live world).

## Rules that were learned the hard way

1. **One origin for everything.** Every design is padded to `origin_lock` (currently `-24251 150 29949`)
   so regeneration can never move it. Before this, a design's origin was its content bounding box and it
   shifted a block or two between runs — that produced hours of "the placement is misaligned", posts
   floating over slabs, etc. If a design must sit elsewhere, set `origin_lock: false` in its config and
   say so loudly.
2. **Verify in context, never in isolation.** `finish.verify_against: <capture>` composites the design
   onto the real world and audits *that*: overlap must be 0, placement problems 0. It also reports
   free-floating clusters (blocks with nothing to place against — they need scaffolding).
3. **The audit learns.** `python -m mcbuild learn <capture>` mines what the server actually allows
   (lanterns on fences, carpet on leaves, upper-half tall grass) into `observed.json`. Hand-written
   placement rules were wrong about real builds ~28 times on the first island. Feed it new captures.
4. **Designs are remaining-work.** Ground-level designs regenerate against the newest scan and emit only
   what is not built yet. Anything placed by *spacing* rather than per-cell (light posts) must seed its
   spacing from what already exists, or it re-picks new positions and doubles up.
5. **`progress` distinguishes three things**: built (loose families — any rock variant, any decorative
   slab counts), *clear first* (a plant/carpet/vine occupies the cell), and a real deviation.
6. **Prep lists live in the sidecar**: `dig` (blocks to remove), `clear` (whole categories, e.g. vines),
   `exclude_boxes` (decor to re-hang). `/cscan dig <design>` shows them in game.
7. **The capture frame is correct** — verified against Litematica's own recorded placement origins
   (Dragonfly matched 86/89 blocks). If coordinates look wrong, suspect a stale file, a remembered
   rotation/mirror on the placement, or a locked placement — not the frame.
8. **`mcbuild place` needs the game closed** (Litematica rewrites its config on exit). `/cscan place`
   in game does not — prefer it.
9. **Anything that clings needs a FULL block, tested against the world as it is today.** Belly hung
   three vines off the vault's wall railings because "solid" meant "not air" and the anchor test ran
   against the pre-build baseline. Use `audit._is_solid_name`, and test against `world`, not `under`.
10. **Leave ~3 blocks of working room around anything you use.** Unless a design is deliberately
   about storage, it must not come within about 3 blocks of a chest, barrel, furnace, hopper or
   workbench — you need room to stand, open the thing and walk past it. Derive that clearance from
   the capture (`container_clear`), never from a hand-written box: the storage moves and the box
   goes stale the same day.
11. **Ask the game, not your memory.** `blocks.py` beats a hand-written table every time. The
   `palette.COLORS` list had ~150 typed-in RGBs and everything outside it rendered **magenta** —
   three renders in one session were silently wrong. `_is_solid_name` had a suffix heuristic that
   called a slab solid, which hid a vine hung off a slab roof in `farm`. Both now defer to the
   registry. When a rule and the game disagree, the game is right: chains were being audited for
   support they do not need (`ChainBlock` never overrides `canSurvive`), while lanterns standing on
   slabs were being rejected even though `canSupportCenter` accepts them.
   **And beware type names that read like a category.** `NOT_FULL` listed `"grass"` among the growing
   things — but in 26.2 the grass PLANT is type `tall_grass`/`double_plant`, and `grass` belongs to
   exactly one block: `grass_block`, a full cube. So the commonest ground block in the game counted as
   not-solid project-wide; nothing could stand on a lawn or cling to one, and `lowland` was told its 27
   lanterns were floating. The exclusion list is keyed on TYPE, so one wrong entry silently disables a
   whole block — `tests/test_blocks.py` now pins this one.
12. **Build for the SERVER's version, not the client's.** 26.2 client, 1.19 server. `pink_petals`
   sailed through every check in the pipeline and is a 1.20 block. `blocks.candidates()` filters to
   the server list by default. The allowlist is currently **provisional** — built from what the
   captures happen to contain plus a curated seed, so it holds ~191 of 1.19's blocks and would reject
   `allium`. Because of that the audit only *reports* unavailable blocks; it does not fail on them
   until a real 1.19 registry dump is supplied:
   ```bash
   # download a 1.19 server jar, then, as with 26.2:
   java -cp "<1.19 server jar>;<libs>" net.minecraft.data.Main --reports --output <dir>
   python tools/server_blocks.py --reports <dir>     # flips it to authoritative; the gate goes hard
   ```
13. **Gravity blocks cannot be used in anything with air under it.** `red_sand` is the best ochre in
   the game and cheap — and it would have poured the giraffe into the void. `blocks.falls` keeps sand,
   gravel, concrete powder and the rest out of `candidates()` unless you ask for them.
14. **Proportion names an animal, and it must be MEASURED — but proportion alone is not enough.**
   Every animal tuned by eye was wrong somewhere. Every animal tuned by NUMBER alone came out as
   the same animal with different numbers. Both halves are in the ANIMALS section above; that is
   where animal work belongs, not here.
15. **Overlap means the world holds something DIFFERENT.** A design cell the world already matches is
   built, not a collision — otherwise every design reports hundreds of overlaps the moment you build it.
16. **"Placeable" is not "affordable" — DIRT IS CURRENCY here.** On skyblock.net dirt and every one of
   its forms (`coarse_dirt`, `rooted_dirt`, `podzol`, `grass_block`, `mycelium`, `mud`, `farmland`,
   `dirt_path`) is money. The blocks are real, legal, in 1.19 and placeable, so every check in the
   pipeline passed them — and the lion shipped with a coat of 5,173 dirt, the capybara 4,690, and a
   ground layer wanted 14,568. **Moss is used instead.** This is a THIRD axis beside `exists` (is it
   real) and `available` (does the server's version have it): `blocks.spendable()` / `blocks.ECONOMY`,
   filtered out of `candidates()` by default so no colour-picked palette can reach it, with
   `allow_economy=True` as the escape hatch. `audit.report()` prints a loud `CURRENCY` line, because
   the first three offenders were all designs that had already audited clean.

## Where things stand (2026-08-18)

**Island designs** — see `python -m mcbuild sync`. Belly ~46% built, rim hem ~50%, paths ~43%,
light posts 24 standing, altar started; taproot, shard, chimneys, ride lights, apiary, bird lanterns
and statue footings not started.

**Animals** — eight species across five families, none placed. Scores from `tools/rubric.py`:

| | family | height | score | |
|---|---|---|---|---|
| elephant | proboscid | 34 | 0.87 | good |
| capybara | caviomorph | 25 | 0.85 | good |
| giraffe | giraffid | 57 | 0.84 | good — the one built in the world; under its floor of 59 |
| bear | ursid | 30 | 0.83 | good |
| jaguar | felid | 27 | 0.82 | good — was 0.73 with a hardcoded `body_r` |
| lion | felid | 32 | 0.81 | good — the mane now reads |
| leopard | felid | 26 | 0.80 | good — was 22, under the felid floor |
| polar_bear | ursid | 32 | 0.79 | good — was 0.71 at height 26, the ursid floor exactly |

**Placement is the open problem.** Measured contact footprints against both captures: the void isle
is full (the giraffe and jaguar hold its two good pads) and the main plate's largest genuinely flat
area is 13x13. An elephant needs 15x29. Nothing new fits without levelling a pad, extending the void
isle, or building below the plate.

## The island (as of 2026-08-18)

Plate at **Y201/202**, ~4,100 columns, one main lobe plus NW tree island, NE shrine lobe, SE mushroom
lobe. A working deck hangs at **Y190–199** (spawners, hoppers, chests, rail loop) and a rail line runs
out to the east lobes. Sky bird at **Y251–268**. Everything below the plate now gets the belly.

Landmarks: tree trunk `-24207..-24192 / 30012..30024` · pond `-24205..-24193 / 30002..30010` ·
deck ladder (vines) `-24190, 29991` · owl `-24248..-24230 / 30011..30031` (hollow, contains the altar) ·
fox `-24240..-24230 / 30000..30011` · bee house `z30036..30048` · gecko on the deck's east face
`-24177..-24173`.

Designs and where they stand: see `python -m mcbuild sync`. Belly ~46% built, rim hem ~50%, paths ~43%,
light posts 24 standing, altar started; taproot, shard, chimneys, ride lights, apiary, bird lanterns and
statue footings not started. ~5,400 blocks left, 3.1 shulkers, all cheap tier + 133 iron chain.

## Working style for this project

- **Design decisions are Jack's.** Propose, give numbers, recommend one option, then build what he picks.
  He cut the clouds and stepping stones after an audit said they were clutter — that judgement was right.
- The island is at **focal-point saturation**. New work should be connective tissue (paths, lighting,
  rim, dressing), not new large objects, and never more sky.
- Verify before claiming. Every design gets an in-context audit; every claim about the world comes from a
  capture, not from memory.
- Prefer generating from the capture over hand-placing coordinates. When a coordinate is needed, ask Jack
  to `/cscan mark <label>` it rather than guessing from a scan — guessing put a chimney on a torch once.
