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
`Minecraft.screen` accessor (use `ScreenEvents.AFTER_INIT`), chat via `player.sendSystemMessage`,
`ResourceLocation` is **`Identifier`**, and **`Blocks.GRAY_WOOL` does not exist** — the sixteen
dyed families are `ColorCollection`s now, so it is `Blocks.WOOL.pick(DyeColor.GRAY)`.
`InteractionResult` is a **sealed interface**, not an enum (`SUCCESS`/`FAIL`/`PASS` are constants
on it), and both `UseBlockCallback` and `AttackBlockCallback` return one.
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
- **~~The colour DB samples the TOP face and has no biome tint.~~ FIXED 2026-08-20** — see
  "The colour foundation" below. `blocks.color(name, face)` now answers per face and the tint is
  applied; `tools/recolour.py` owns it and `tools/extract_blocks.py` delegates to it.
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

`configs/deck_floor.yaml`, `mcbuild/gen/deckfloor.py`. 427 blocks, 84 of which replace something; 0 new problems in context.

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

- **The deck is the biggest connected BLOB of the course, not the course.** Taking every cell
  sweeps in 97×93 of island underside — belly scraps, rim shelves — and the edge course alone came
  to 819 cells with **59 free-floating clusters** drawn round islands two cells wide. Deriving the
  blob (2,145 → 1,725) keeps it a deck design with no hand-written box.
- **A rectangle will not wall the moss farm.** It is a WORKING farm — 29 ice, 12 water, glow lichen —
  and it sits on an irregular lobe: the box one cell out is **58% air**, two cells out **70%**. A
  rectangular room floats over holes and cuts the water. The wall follows the farm's own dilated
  edge and lays only where there is floor under it — **41 cells**, because most of the farm's
  boundary is against open air at the deck's edge, and you cannot walk in from a drop.
- **`plan_merge` fills empty cells only.** Comparing before and after through it showed a 30-cell
  change, *all of them `air -> something`* — that is the tell. A design whose job is to REPLACE is
  invisible to it. Composite with overwrite to see a repaving design.

### The border was wrong twice, and there is now no border

Jack placed the first build and said the floor was "all messed up". It was, for two reasons that
only a real placement exposes:

- **"Every floor cell with a missing neighbour" is NOT the deck's outline.** This deck has **25
  interior holes**, so 269 of the 529 rim cells were HOLE edges and the border came out as dark
  rings round **94 separate interior gaps** — scribbles across the whole floor. The outline is the
  boundary against the flooded OUTSIDE, which is 260 cells, not 529.
- **The deck's edge is planted, and the border was eating it.** 111 vine cells sit on the floor
  course and 107 of them are on the rim; 92 of the 260 outer cells are vine and 64 more are moss.
  The first build turned them into solid dark blocks — stripping the hem's planting and filling a
  see-through edge with stone. **`vine` is in `KEEP` now**, never resolved and never bordered.

With both fixed, a hard edge course lands on **82 of 260** outer cells — the rest are planted or
carry fixtures. A third of a line is a dashed scribble, so `border_ring: 0` and the deck has no
border at all. What survives is what was always doing the work: **252 scatter cells resolved, 64
cells of zone band, and the moss room** — 427 blocks, and only **84 of them replace anything**,
against 701 and 492 in the first build.

**The lesson worth keeping: a remedial design's damage is measured in what it REPLACES, not in what
it places.** 492 replacements read as vandalism; 84 read as a repair.

**Still open on the deck:** the 120 chests (the Store Hall's 68 slots are built and waiting), the
37 torches, and the 44% walkable figure — all of which want the chest move done first.

### The workshop pass (2026-08-19)

A full audit of the deck with both designs applied produced three moves, ranked by effect per
block. All three are built.

**What the audit found.** 989 floor columns. The floor was already fixed (80% stone brick + 9%
deepslate = 89% in two materials, walkable 44% -> 62%), which left the two surfaces that actually
say *unfinished*: **29% of what is overhead was raw cobblestone** and another 8% moss, and the deck
was lit by **20 torches against 8 lanterns** — with 95% of the floor already within 7 of a light,
so the torches were costing nothing but the impression. And standing at the entrance mouth looking
north there were **seven blocks of nothing at head height**: the entrance was the only vertical
event in the room, so you did not discover it, you simply arrived at it.

| | before | after |
|---|---|---|
| raw cobble overhead | 29% | **0%** |
| designed soffit overhead | — | **32%** (20% panels, 12% grid) |
| lanterns : torches | 8 : 20 | **18 : 14** |

- **The soffit is NOT flattened deck-wide.** Across 1,725 columns the ceiling genuinely steps, and
  forcing one plane would either bury the structures under it or leave a shelf. What is fixed is
  the MATERIAL, and the coffer grid is set in WORLD coordinates so it stays aligned across a step.
  Finished ceilings are left alone; only the quarry ones are replaced. (Inside the entrance, which
  is one room, the soffit *is* one flat plane — that is the difference between a room and a deck.)
- **A wall torch cannot become a lantern.** A lantern does not mount on a wall, so it is only
  swapped where there is a block overhead to hang from — **14 are left standing** rather than
  deleting someone's light, and the count is reported.
- **`KEEP` protects torches from the FLOOR pass and the relight replaces them anyway.** That is a
  real exemption, so it is narrow and asserted: a cell written over a torch must be a lantern and
  nothing else. Widening `KEEP` would be the wrong fix — it is what stops the next pass eating a
  hopper.

**Still open:** the 112 chests (Store Hall's 68 slots are built and waiting), the 14 wall torches,
and 62% walkable — all three of which are the chest move.

### The soffit was the worst thing on the deck, and every check passed it (2026-08-20)

Jack placed the workshop pass, looked at it and said the wood lines wrapping the workshop were
awful. They were. The soffit's coffer grid was `dark_oak_wood`, and measured off the 03:55 capture:

| | |
|---|---|
| grid runs drawn | 215 |
| …of one or two cells | **184** |
| …lone blocks with no grid neighbour at all | 168 |
| dark oak standing in world | 70, **all** on a grid line (43.75% would be chance) |
| …with no wood neighbour | 27 |

**It is not a grid, it is confetti** — and in the loudest block available, because dark oak against
`smooth_stone` is the largest hue contrast on this deck.

**Nothing in the pipeline could see it, and that is the transferable part.** Every check the design
had is PER-BLOCK — is the state legal, is it in 1.19, is it spendable, is it affordable, does it
have support — and it passed all of them, 376 cells, zero problems, zero expensive. The failure is
PER-RUN. A block is only as good as the line it is part of, and nothing measured lines.

**A SOFFIT BELONGS TO A ROOM, NOT TO A DECK.** That is the actual error; the block was a symptom.
The pass drew over whatever happened to be overhead, and off the capture that is not a ceiling: of
1,224 columns with a real underside, 421 are raw enough to treat, and those 421 are **25 lacy
patches at SIX heights** (Y197–202). The largest is 92 cells and fills **40% of its own bounding
box**. The taproot entrance already had this right — *"inside the entrance, which is one room, the
soffit IS one flat plane — that is the difference between a room and a deck"* — and the deck-wide
pass ignored it.

It is also the same finding as `border_ring: 0` one surface up: **a third of a line is a dashed
scribble, so do not draw the line.** The design had already learned it on the floor and then made
the identical mistake on the ceiling.

**And it is the same mistake `gallery.py` made and REMOVED, one file over, for the same stated
reason** — to move a palette number (wood 7% against the plate's 23%). The gallery's own comment
says it: *"the timber was only ever here to move a palette number, which is the wrong reason to put
a block anywhere."* The number then reappeared in the soffit's docstring as the justification.
**The wood-percentage target is deleted as a goal.** The deck's ceiling is the island's own rock, so
it is dressed in the island's own rock: `smooth_stone` panel, `deepslate_bricks` line — 51 darker,
the one real value contrast this economy has at cheap-or-ok tier, and the block the stair head, the
zone bands and the void tower already draw with, which is what makes them one hand.

#### What is now in the code

- **`soffit: False` deck-wide**, with the measurement above in the docstring. The machinery stays
  and is correct — point it at a ROOM and turn it on.
- **A run gate** (`soffit_min_run`, default 4). A grid cell whose run along its own axis is too
  short demotes to PANEL, never to a lone dark block. This is `gallery._MIN_RUN`, one surface up.
- **A patch gate** (`soffit_min_patch`, default 8). Re-materialising a 3-cell island of cobble into
  smooth stone is scatter, which is what this same design's floor pass exists to remove.
- **A reclaim pass** (§6b), because the fix had to undo the damage and could not.

#### Four traps inside the fix, each of which produced a clean audit and a wrong build

- **A litematic cannot express removal, and the pass could not SEE its own mistake.** `dark_oak_wood`
  is not in `soffit_raw`, so the 70 blocks were invisible to every gate; and 50 of them have since
  had moss placed under them, so they fail the two-clear-courses room test as well. Left alone they
  would have stood for good. They are healed directly into their commonest **solid** same-course
  neighbour — 57 `smooth_stone` and 10 `stone_bricks` against the wood's own 28 — so each turns back
  into the plane it interrupted rather than becoming a hole in a ceiling.
- **The run gate's AXIS was inverted, and the inversion shipped.** A line at constant X runs along
  **Z**; scoring it along X measures each cell ACROSS its own line, so every run came out as 1 —
  and isolated cells then sailed through the threshold. It also made the *diagnosis* too
  pessimistic: the first sweep said no grid works at any spacing, and with the axis right a grid on
  the one big patch is 29 cells with runs up to 16. **A measurement and the code that acts on it
  sharing a bug agree with each other perfectly.**
- **Reclaim scope is not build scope.** `floor` is where you can stand (892 cells); the deck is
  every column of the course (1,779). Anything about what is OVERHEAD must use the deck — scoping
  the reclaim to `floor` reached 17 of 70. Eleven more sit above rim columns carrying no floor
  block at all (the pass placed them when the floor below them still existed), five of those out on
  the east arm past any sane dilation, so it sweeps the deck's bounding **box**. That is safe only
  because **the gate is the SIGNATURE, not the footprint**: a cell on the grid line.
- **A fix must not be coupled to the setting it is fixing.** The reclaim read `soffit_grid_at`, so
  retuning the grid to 5 silently dropped it from 70 blocks to 26 — the wood is on a 4-grid and
  nothing else knew that. `reclaim_grid_at` is history and does not move.

`tests/test_deckfloor_soffit.py` pins all of it: no wood anywhere, no drawn grid cell without a
grid neighbour, both gates firing, all 70 reclaimed, and the reclaim finding nothing when the
signature is moved off every real coordinate.

**Shipped: 79 blocks, all remedial** — 70 wood healed to stone, 6 zone band, 3 relit. 0 new problems
in context, 0 wood placed, 0 expensive.

**Still open — Jack's call.** The soffit works on exactly ONE patch: 92 cells at **Y201**, over
X−24205..−24194 / Z29994..30012, which is the entrance hall — the room. At `soffit_min_patch: 30`,
`soffit_grid_at: 5`, `soffit_min_run: 4` it draws 63 `smooth_stone` panels and **29
`deepslate_bricks`** grid cells, runs up to 16, only 7 demoted, and takes the design to 171 blocks.
That is a real coffered ceiling over the one place that has a ceiling. Everywhere else stays rock.

**Pre-existing, found while running the suite:** `configs/store_hall.yaml` crashes the pipeline with
`ValueError: nothing built` — it is 100% built, so it emits nothing and `World.canvas` raises. It
fails identically against the pre-session capture, so it is not from this work. A finished design
should report complete, not raise.

## The root break, and the machine room under the tree (2026-08-19)

`configs/root_break.yaml`. **82 blocks.** It closes the one-course gap between the taproot's head
at Y188 and the island's belly skin at Y190, and stops there.

**It started much bigger and had to be cut back, which is the useful part.** The story is right —
the plate hands you to an interior which hands you down the taproot, and the taproot *topped out at
Y188, six courses below the deck floor*, so the room whose whole purpose is that handover never
showed the root. The first build carried it all the way up through the undercroft, the deck floor,
the room and the ceiling to the tree at Y203.

**The site could not take it. The tree's base is a MACHINE ROOM.** 66 redstone parts spanning
X-24209..-24195 / Y191–203 / Z30005..30030 — 13 pistons, 7 repeaters, 6 observers, 2 dispensers,
and a **sculk sensor at (-24199, 201, 30019) shielded by 68 wool cells within 3 blocks**. Wool is
the only block that stops a vibration; that wool is the shield on a hidden-door trigger, not
decoration. The tree trunk's own centroid (-24199, 30019) sits *inside* that spread, and **no
4-radius column anywhere clears the mechanism by 5**. The first build put 256 cells within 8 of the
sensor and came within 1 of it, and heaved 57 cells of the shielding on the way.

Closing the gap at Y189–190 gets the thing that actually mattered — the root reads continuous into
the island's underside — from the view where it counts, which is **from below, descending the root
stair**. Nearest mechanism part is now **5 blocks**, cells near the sensor **0**.

### What this cost, and what it is worth keeping

- **`gen/protect.py`.** `BREAKABLE` was a whitelist and it was still wrong, because `gray_wool` and
  `black_wool` looked like ceiling decoration. The safe set is now stated ONCE and every generator
  consults it *in addition to* its own whitelist — redstone, containers, machines, rails, doors,
  signs, fluids, farm blocks, player-placed light. A block that looks like fabric may be a
  silencer; a stray slab may be a timing floor; a generator cannot tell by looking.
- **`protect.is_used` and rule 10.** 44 structural cells sat within one block of something you
  stand at and use. Honoured *above the floor course only* — paving the floor beside a chest is
  still floor. 44 → 20, all of which are paving.
- **`finish.defer_to`.** The four deck designs shared 39 cells. Overlap between designs is a WORK
  problem: you place a block, the next placement says it is wrong, you break it and place it again.
  Precedence runs Root Break > Taproot Entrance > Deck Gallery > Deck Floor, which makes generation
  ORDER significant — build the winner first.

### The flow audit, which found what no palette metric could

- **The moss room had 23 wall columns, all full height, and no doorway.** The door must be chosen
  from the columns that will actually be BUILT: 18 of the 41 wall cells are skipped for the farm's
  own water and lichen, and the first fix removed one that never existed.
- **The moss farm was ALREADY unreachable** before any of this — 0 of its 262 standable cells
  connect to the entrance in the base world. Not caused here, but worth knowing.
- **87% of the deck is reachable** from the entrance mouth; 105 cells sit in 27 isolated pockets.
- **One 3-wide neck at Z30000 carries the whole south deck** — removing any of (-24199..-24201,
  30000) splits ~128 cells from ~582. That gap is both the entrance approach and the only route to
  a third of the floor.

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

#### Still open

- **Bare `/cscan place` now places 61 designs.** The mod cannot see `sync.yaml`, so it has no idea
  which ~14 are actually tracked. The `_fill ` prefix keeps scratch fills out; the rest of the pile
  is untouched.
- **The scans archive is unbounded** — 24 files, 1.6 MB today, and `/cscan auto` adds one per tick
  forever.
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

**THIS IS MOVEMENT AUTOMATION ON A LIVE SERVER.** Most servers' rules treat it as a bot whatever it
is for, and smooth constant-velocity flight is the exact signature anticheat is built to catch. That
is a decision about Jack's account rather than about this code — recorded here so the next person to
read it knows it was made deliberately and not stumbled into. What the code can do is be
conservative and be trivially interruptible:

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

## Build & test

```bash
python -m pytest -q                                   # 304 tests, keep green
cd chunkscan && ./gradlew build test -q                # writes build/libs/chunkscan-<ver>.jar
python chunkscan/verify_synthetic.py                   # Java writer vs Python reader, block for block
```
Jack uploads the jar through the launcher himself — **do not copy it into `custom_mods/`**, that
creates a duplicate mod id and Fabric refuses to start.

## The store hall got a room, and the court got a way in (2026-08-20)

Two jobs off the 09:16 capture. Both are small; the measuring is the part worth keeping.

### The store hall was furniture, not a room

`configs/store_hall.yaml`, `gen/storehall.py`. The banks were built and Jack had moved **76
containers** into them - and there were no walls. From outside you were looking at the backs of a
freestanding ring of chests standing on open deck.

The shell is the wall course-for-course behind the banks: the 9x9 perimeter at x-24195..-24187 /
z30022..30030, Y195-199. Measured first - **158 of 160 cells free**, 0 protected, floor already
`deepslate_bricks`. **176 blocks, 0 problems, overlap 0, all cheap-or-ok.**

- **It carries NO ceiling, deliberately.** The Deck Vault already owns Y200 over this footprint (49
  designed cells, 32 already placed). Two designs drawing one surface is exactly what
  `finish.defer_to` exists to stop, and the raw cobblestone at Y201 is *above* the vault, so it is
  not a soffit problem - it is hidden.
- **The doorway is DERIVED, and the config was wrong about it.** `door: west, door_width: 3` asks
  for three cells; the world has **one** (z30026), because Jack filled the other two with chests
  when he moved in. Walling to the config would have bricked up the only way in and put a doorway
  into the back of a chest. It is now the INTERSECTION of "where a door was asked for" and "where
  the banks are really open" - and that intersection matters both ways, because
  "wherever the banks are open" alone turns **every cell a fixture happened to block into a second
  hole in the wall**. A gap in the banks is not a door. `tests/test_storehall_shell.py` pins it.
- Bank CORNERS carry no chest (a corner chest faces two ways and can face only one), so they are
  gaps by construction. Filled solid - four holes become four piers.
- Plinth and cornice are `deepslate_bricks`, field is `stone_bricks` weathered per CELL. Hashed on
  the course instead, a course comes out all one material and the wall is horizontal stripes - the
  deck soffit shipped that once.

### The sky-well court had no way in: `gen/rimstair.py`, `configs/court_stair.yaml`

**72 blocks, 22 dig cells, one component, 0 problems, overlap 0, all cheap.**

Jack picked the side and asked for it to be audited. His instinct was right; the reason I first gave
for it was **wrong, and the error is worth keeping**. I claimed a surface walk from the island centre
could not reach the owl lobe at all. Re-measured with a proper walk - every standable surface in a
column, not just the topmost; slabs and stairs as half-steps; climb 1.25 - the owl lobe IS reachable,
altar included. The first model took ONE node per column over Y199-206 and stepped at most 1, so it
could not see a route that changes level or uses a slab, and it reported a 4-5 block scramble as no
route. **A reachability number means nothing without the movement model stated beside it** - the same
site read 1,268 cells in 49 components on a fixed course, 36 steps allowing 4-block falls, and 248 on
a true walk. What actually justifies the stair is the DISTANCE, which was measured properly.

**Measured with a TRUE walk** - step down at most 1, climb at most 1.25, so no falling and every
route reversible:

| | before | after |
|---|---|---|
| island centre -> court foot | 248 | **46** |
| -> court, mid | 247 | **51** |
| -> court, far NW | 258 | **56** |
| -> court, south | 43 | 43 (already reachable along the deck) |
| court -> plate ledge (getting OUT) | 108 | **10** |

**Do not trust a reachability number without stating the movement model.** The same site measured
1,268 standable cells in 49 components on a FIXED course (no vertical movement at all), 36 steps
when 4-block FALLS are allowed - that route jumps down the tree trunk, 204 -> 200 -> 196, taking the
damage - and 248 on a true walk. Three different answers to "can you get there", all correct for
what they asked. The fixed-course version is what first said the court was orphaned, and it was
overstating the case.

Five things the build cost, each of which produced a clean audit and a wrong result:

- **The rim is not where the surface scan says it is.** A column scan reads the edge at Y201 at
  x-24222 - but that Y201 cell is a **vine**, hanging in open air. The rock stops at x-24221. Worse,
  `Ctx.name_at` returns the vine BY NAME, so the standard "is this cell empty" test written as
  `name not in AIRY` reads the curtain as footing: every stringer stopped at the top of the cliff
  and the flight came out as twelve floating treads, with the audit reporting 0 problems. There is a
  `PASSABLE` set now. Same shape as the `Canvas.get` returns -1 bug.
- **The flight was ONE-WAY and nothing but a walk test could see it.** The rim ledge stands at
  **202.0** and the land bridge behind it at 203.0, so a top tread at Y201 tops out at 201.5 - a
  1.5 step. A player climbs **1.25**. You could get down and not back up. `y_top: 202` fixes it;
  both approaches are now a half step. **Audit clean, geometry legal, build unusable.**
- **A two-wide flight in open air is impossible here** and the reason is the pool: the court's water
  reaches x-24223 at z30017-30018 and x-24225 at z30015-30017, and **x-24222 is the only column free
  of it across the whole run**. Hence one lane cut into the rim rock at x-24221 instead. The
  stringer fills DOWN until it meets something real - ice and water included, which are protected -
  so it never drives a pier through the pond.
- **The tread cell is itself a dig.** Listing only the courses above a tread says the flight is
  clear while the stair is still inside the cliff.
- **Facing comes from the geometry.** The flight ascends toward +Z, so every tread is `facing=south,
  half=bottom` - the rule pinned in `test_stairhead.py`. Our renderer draws both directions
  identically, so this is asserted, never eyeballed.

Site choice: z30013-30019 has **six consecutive rows of Y201 rim** against the south lobe's three
irregular ones (Y200/195/195) boxed in by void at z30029. It sits immediately south of the land
bridge - the crossing you take walking from the farm toward the owl - so the head is on the route
and you descend facing the owl lobe. The south lobe is where the farm-to-owl line literally crosses,
which is what Jack described, and it is the worse edge; he took the north lobe on the numbers.

## The court hall: apocalyptic beauty, and where the glass may go (2026-08-20)

`configs/court_hall.yaml`, `gen/courthall.py`. **265 blocks, 0 problems, overlap 2, 0 expensive.**
Jack laid a deepslate frame on the Y195 course and asked for apocalyptic beauty with glass panes,
plus a water feature in the bay that sits one course down. The audit decided almost all of it.

### The site is a one-block shelf hanging in the void

The single most useful measurement: the column at x-24229 has **exactly one solid course between
Y150 and the plate**, and it is Y194. The court is not a room dug into the island - it is a shelf.
Rock closes it east and west, both ENDS have fallen away into open sky, and the island's own
underside is the ceiling at Y201/202. The room is already a ruin; the design only has to admit it.

That produced the rule the whole file turns on. **Glass in front of rock is a window onto stone**:

| run | outside open at Y196-200 | treatment |
|---|---|---|
| west  x-24234 | **0%** | pilasters |
| east  x-24222 | **8%** | pilasters |
| north end z30006 | **95%** | GLAZED |
| south end z30029 | **96%** | GLAZED |
| divider z30023 | court both sides | balustrade over the water |

So only the two ends get panes - and they are the two places with nothing behind them for hundreds
of blocks. `_kind` probes it rather than being told, the same discipline as the store hall deriving
its doorway.

### Classifying a run took two goes and both failures shipped a clean audit

- **Scoring both perpendicular directions and taking the more open one made EVERY run glazed.** The
  room's own interior is open by definition, so the rock flanks scored as open and came out glazed -
  windows onto stone. Inward has to be resolved first: it is the side carrying the court FLOOR.
- **Then rock and court floor both read as "solid below"** - the island's flank and the room's own
  paving are equally floor - so the flanks came out as internal DIVIDERS and got a balustrade. The
  three cases only separate one course UP: rock is closed above, court is open above and floored
  below, void is open above with nothing under it at all.

### What "apocalyptic" means here, in code

The void tower already paid for this: *what makes voxels read as ARCHITECTURE is regularity and
openings, not damage* - its first jagged attempt was rejected on sight as "a tossed grouping of
vague blocks". So **the ruin takes GLASS, never the order.** Every bay keeps its pier and its
cornice at any `ruin` setting; `test_ruin_takes_glass_and_never_the_order` pins that the pier set is
identical at ruin 0.0 and ruin 1.0. The south screen is intact, the north is broken - one whole bay
open, top course gone in others.

And a rock flank gets **pilasters, not infill**. Filling those bays is 120 blocks of tidy deepslate
laid over the most apocalyptic surface in the room. The surviving order is the piers; the rock
between them is the point.

### The pool is a tank, and it would have frozen

`freeze_guard` in `court.yaml` exists because **this court froze on its first build - 29 ice
blocks.** Snowy biome, and 16 of the sunken bay's 55 columns are open sky. Water needs block light
>= 10. Verified by propagating light through the built model: **every water cell lands at 12-14.**

- Guard lights are plain `lantern` (15). **`soul_lantern` is exactly 10** and is one block of
  falloff from failing, so it is mood only. That distinction is the whole guard.
- A guard lantern is **waterlogged and has its own footing**. Not waterlogged, the water above flows
  down into it; skipping the water there instead punches a hole through the pool's surface at every
  guard - which is what the first build did, nine holes in a 27-cell sheet. And a lantern is not a
  full cube over a floor that is a skin over open VOID, so without a block under it the audit says
  "standing on air".
- The bay's floor is one block over nothing and the Y194 course runs on east past the plinth, so the
  basin is built as a tank: floor at Y193, wall ring, water at Y194. Its top face is exactly the
  sunken bay's own walking level - the "one block down" Jack described. **0 leak faces.**

### Palette: there is only one glass you can afford

`glass_pane` is **ok**; plain `glass`, `tinted_glass` and **every** stained pane are **expensive**.
Store holds **1,060 glass (~2,800 panes)** against 26-49 of each stained pane, so the cheap material
is also the only one there is enough of. The order is `deepslate_bricks` - Jack's own edging block,
`ok` tier, 51 darker than stone brick, and 512 in store against 172 needed.

**Still open:** four supply chests (stone 768, deepslate bricks 256, wool) stand in the north bay.
The design comes within **2** of one and shares a column with none - the plinth line is exempt from
`container_clear` because Jack laid that line himself, past those chests. Move them and the north
screen has more room.

### One load, one trip: the fetch policy, walking, and the goal that blocked motion (2026-08-20)

Four things Jack asked for after the second real flight, and one bug found on the way that explains
more of "it gets stuck" than any of them.

#### The loop went shopping while it had work to do

The fetch decision was made **per SPOT**: if the best cluster was short of anything, fetch. So with a
full pack and hundreds of placeable cells it flew to a chest, took that one spot's shortfall — often
sixty-four blocks — and flew back. On a design of any size that is a session of commuting.

Two questions now, and the ORDER between them is the whole policy:

1. is there anything at all I can place with what I am carrying? → **build**, and do not fetch
2. otherwise: something to fetch, and room to put it? → **fetch until the pack is full**

So a trip ends when the PACK is full or the DESIGN is covered, never when one spot's shortfall is
met, and a fetch only starts when the loop is genuinely out of work — out of stock, or every
remaining cell blocked or sealed. `Plan.anyDoable` and `Plan.nextFetch` are the two predicates and
they are pure, so the policy is tested without a client.

Three details the numbers forced:

- **The shortfall is the DESIGN's, not the spot's.** `Plan.fetchTargets` totals every remaining cell;
  `restockTargets` still answers the per-spot question for the report, which is a different question
  and keeps its own answer.
- **How much to take is `min(still wanted, room in the pack, what the chest holds)`.** `Work.room`
  counts empty slots and the free part of matching stacks over the 36 real slots — armour and offhand
  would read as 320 blocks of room that does not exist.
- **No room for the biggest shortfall is not the end of the trip.** A pack full of stone bricks has
  plenty of space for the deepslate, so `nextFetch` walks the whole list. Judging only the first
  entry is a trip not taken.

Dead ends are now told apart, because they want different answers: *nothing to place and nothing
indexed to fetch* sends you to `bom`; *pack full of what you cannot place here* tells you to store
something. Said once, not every two seconds — a message on a 2-second timer is a reason to turn the
loop off.

#### `/cscan find` is a substring search, and a fetch was using it

`stone_bricks` matches `mossy_stone_bricks`, `cracked_` and `chiseled_`. The loop flew to whichever
was nearest, asked for a block that was not in there, took zero, blacklisted a perfectly good chest
and moved on — **and it looked exactly like the chest being empty**, which is why it survived a
session of watching. `Storage.findExact` is what a TRIP uses; `find` stays fuzzy because
`/cscan find wool` is a question about wool in general.

#### THE GOAL BLOCKED MOTION, so the router could never reach it

The one worth remembering. `Nav.route` never checked that the destination cell was passable, and
**every fetch target is a chest's own cell** — a chest `blocksMotion()`. Every build spot is a
cluster CENTROID, which lands inside rock about as often as not. The goal was therefore never
expanded, the search ran to the end of its budget, returned empty, and the caller fell through to
flying straight at the wall the chest is in. Raising the node budget makes this *slower*, not better.

`GOAL_SLACK` (2) finishes at the nearest passable cell to a solid goal, with a slight bias toward
staying level so a chest in a wall hands you the cell in front of it rather than the one above it. A
genuinely buried goal still has no route, and that is asserted separately — the slack is for a chest
in a wall, not for pretending sealed cells are reachable.

#### The rest of the navigation work

- **`MAX_RANGE` 256 → 512.** The gate is free; what costs is the search, and that is bounded
  separately.
- **`MAX_NODES` 40,000 → 120,000**, plus a **25ms wall-clock budget** checked every 256 expansions.
  The honest limit on the client thread is "how long may I freeze the game", which is a number of
  milliseconds, not of nodes. The raise is worth much less than it looks — see the next two.
- **A clear line costs ZERO nodes.** `route` tries `clear()` first and returns the destination as the
  only waypoint. Across this island's open sky that answers most calls, including most long ones.
- **A long search that fails is re-tried toward a SUB-GOAL** 128 blocks along the line. A* is cubic in
  the distance and staging is linear, the route is recomputed twice a second, so staging turns "no
  route, flying direct" — the thing that flies you into terrain — into real progress and a fresh
  search from closer in. It is NOT a partial route: it is a shorter search that SUCCEEDS, which is
  the honest version of the instinct the partial-route rule rejected.
- **A walking route is a different route.** `Nav.standable` requires footing as well as headroom, with
  one course of slack under the floor for a step DOWN — without that every route breaks at a stair
  lip or a doorway sill. `Nav.of` routes through open air thirty blocks above a floor, which is a
  perfect flight plan and a walk into a hole.

**Two of the Nav tests were pinning the implementation rather than the property**, and the
line-of-sight shortcut failed them: their doorway was dead ahead, so the straight line went through
it and there was nothing to search. Moved off-axis, they test the search again — and
`itDoesNotCutTheCornerOfADoorFrame` had been passing VACUOUSLY over a one-element list.

#### It walks when it cannot fly

Indoors is where routing matters most and where flight is least likely to be on, and the autopilot's
answer there was to warn once and do nothing — parked in exactly the case it was built for. It walks
now: horizontal delta only (the vertical belongs to gravity), a jump on horizontal collision or when
the next waypoint is above you, never mid-air, and the look angle stays level because a walking
player does not stare at the floor.

#### NO KEY INTERRUPTS IT

`playerIsDriving` handed control back on any movement key. That reads as a safety property and
behaves as a fault: **an unattended loop is unattended precisely because you are typing in chat or
looking at another window**, and a key left down through a focus change disarmed an hour of work
silently. It is gone, `stop()` went with it (no callers — which is the honest shape of the decision),
and `/cscan stop` is the off switch.

`Screens.anyOpen()` went the same way: it paused the flight for chat, the map and the pause menu.
Only a **container** pauses it now, because flying off mid-withdrawal half-empties a chest and then
blacklists it.

Both are pinned by reading the SOURCE, because what is being asserted is the ABSENCE of something and
there is no state to look at. The first version of those tests failed on the comments EXPLAINING why
the rule was removed — a check that forbids naming a thing forbids explaining it — so it strips
comments first, and there is a test that the stripper strips comments and not code.

### What the second flight found: one frame a second, and pressing on the wall (2026-08-20)

Four reports off a live run, and every one is a bug the tests could not have caught as written.

#### `autofly on` dropped the client to 1 FPS, and nothing about it was slow

The route was invalidated by `walkRoute != flying`, where `walkRoute` had just been set to
`!flying`. **That expression is true whenever `flying` is true**, so an A* ran EVERY TICK instead of
twice a second — twenty searches a second, each allowed 25ms, plus the allocation churn of a
120,000-node budget.

The lesson is the shape of it. **A stale-check that is accidentally always-true is invisible**: the
routing is correct, the steering is correct, every test passes, and the only symptom is the frame
rate. It is now stored as the stance itself (`routedFlying = flying`) rather than as its negation,
pulled out into a pure `needsRepath` with tests on it, and floored by `MIN_REPATH_TICKS` so that no
invalidation rule — this one or a future one — can produce a per-tick search again.

Raising `MAX_NODES` is what made this catastrophic rather than merely wasteful. A budget is only ever
spent by a search that FAILS, so it is safe right up until something makes searches run constantly.

#### "Still trying to go directly through blocks"

The no-route fallback was to fly at the goal and add a little upward velocity. That does not lift you
over anything — it grinds you along the wall at an angle, because the forward component never stops
pushing. Two replacements:

- **`Nav.escape`** — when there is no route, flood outward from where you stand and take the
  reachable cell that gets CLOSEST to the goal. Up, down, left, right, behind: whichever actually
  helps. Breadth-first, bounded by cells rather than by geometry, and only ever run after a real
  search has already failed. Re-run at each repath it is a wall-follower that keeps making progress.
  **Getting round an obstacle is a search, not a nudge.**
- **`unstick`** — for the genuinely-shut-in case, zero the components of a direct guess that press
  into a block, tested at the feet AND the head. A ceiling then slides you sideways and a wall slides
  you up. All three blocked and it rises, which beats vibrating against a corner.

A test of mine was wrong here too, and instructively: *"a sealed box has no escape"* is false —
crossing the room really does get you closer to something outside it. What matters is that it never
leaves the box and that it CONVERGES, so that is what is asserted.

#### `MAX_RANGE` 512, and staging that shortens

One 25ms budget is now shared across the whole `route()` call, so the staged retries cannot multiply
the cost, and staging halves its distance on each try — a sub-goal 128 blocks along the line lands
inside the island as easily as in front of it.

#### "It needs to move faster"

`SPEED` 0.35 → **0.75**. Vanilla sprint-flight is about 1.0, so it is still under what a player does
by holding a key, and 0.35 on a 240-block island was a long time watching yourself travel.

**Everything that makes speed safe is a function of it, not a constant beside it.** At 0.75 you cross
the old 1.0-block waypoint radius in under two ticks — past the turn before the next waypoint is even
selected — so `waypointRadius` is 2.5 ticks of travel and the approach taper scales with it. A fixed
radius and a raised speed is how a router that works becomes a router that clips every corner.

#### "Fetch says it took 0x even when it actually took"

It did take them. The message was about a **second, pointless withdrawal**: the first finished, the
phase left `busy()`, the next recount two seconds later saw itself still standing at the chest and
began again — finding nothing of what it asked for, reporting `took 0x`, and then **blacklisting a
chest that had just worked**.

A chest is now left alone for the cooling-off period after ANY completed withdrawal, not only a
failed one. There is no version of "go straight back to the chest I have just been through" that is
useful. And taking nothing no longer reports as `took 0`: it says the index was out of date and names
the chest, because "took 0" reads as a failure of the taking rather than of the record that sent you
there.

### A SPOT IS A TRIP, NOT A PLACE TO STAND (2026-08-20)

Jack: *"when its flying to place make sure it moves around the placement area in a radius flying
different angles… printer wont work if it just stays in a small place the entire time it wont ever
move on."* Exactly right, and it is the biggest gap in the loop so far.

**`radiusFor` sizes a spot to one INVENTORY LOAD** — 24 blocks carrying a shulker, 96 carrying six —
which is correct for deciding where to make a trip to. The loop then guided you to that spot's
CENTROID and stopped, because arriving is not disarming. **The printer reaches about four and a
half blocks.** So it placed whatever happened to lie near the middle of a region up to 96 across, ran
out, and sat there until the ninety-second stall watch abandoned a spot that was almost entirely
unbuilt — and then the next recount picked the same region again.

Two levels of hysteresis now, and they answer different questions:

- **the SPOT** — am I still working this region? Matched by PROXIMITY, not equality: a cluster's
  centre is the centroid of the cells still to do, so it drifts a block or two every time you place
  some, and comparing it exactly would call every recount a new spot and re-announce twice a second.
- **the STATION** — where in it do I float? The cells binned at the printer's reach; you are sent to
  the fullest bin, nearest on a tie. There is no state to keep: as those cells get placed the bin
  empties and the next call moves you on.

Four things that had to be right, each of which produces a loop that looks like it is working:

- **A station RE-CENTRES as its cells get built.** A bin is a 4-cube, so its far corner is 3.46 from
  the middle and the printer's slack over that is about a block. Standing where you first arrived
  builds the near face and stops; re-aiming at the centroid of what is LEFT walks you round the group
  from a new angle each time some of it goes in. That is the "different angles", and it falls out of
  re-centring rather than needing an orbit.
- **`Nav.standoff`, not `Nav.reachable`.** `reachable` answers "may a route END here" and takes the
  first free cell it finds, which beside a wall is the crevice between two blocks. A place to work
  FROM is scored on OPENNESS — at least three of six neighbours clear — before distance, and biased
  toward the side you came from. This island is a deck under a plate full of hoppers, chests, rails
  and roots; a spot wedged between two of them is one the printer never finishes.
- **A per-station stall of 20s**, against the spot's 90. They ask different questions: *is there
  anything left here the printer will take* versus *is this loop doing anything at all*. A bin the
  printer will not take — wrong chunk, blocked by an entity, obstructed by something the design does
  not know about — must not cost a minute and a half. Abandoned bins are remembered, and when every
  bin has been tried the set is cleared rather than stranding the spot for good.
- **The spot-level stall has to drop the SPOT.** It cleared the arrow and left `spotCentre` set, so
  the proximity hysteresis chose the same region straight back and the stall repeated for as long as
  you left it running.

`ARRIVED` 3.0 → **1.5**, because stopping three blocks short of where you were sent spends the whole
reach budget before you start — and a SOLID destination is arrived at from outside it, or the flight
noses at the face of a chest trying to satisfy a radius no route can reach. `tests/PlanTest` pins the
arithmetic (`half-diagonal of a bin + standoff + arrival < printer reach`), because that relationship
breaks silently the moment anyone tunes one of its three numbers.

#### `/cscan autofly speed <n>`

0.10 to 1.00 blocks per tick, default 0.75, reported in the HUD beside the mode (`[route 3 @0.75]`).
The cap is AT vanilla sprint-flight rather than above it: "no faster than a player can actually go"
is the one bound that is defensible without knowing the server's rules.

**The walk scales with the same dial.** A speed setting that only changes flight stops working the
moment you go indoors, which is where you would most want to slow it down.

### Making it survive the night (2026-08-20)

Six things, two of which were the loop doing something actively wrong.

#### A chest that WORKED was blacklisted like one that failed

My own regression, from the fix two commits earlier. To stop a second withdrawal opening the same
chest two seconds later and reporting `took 0x`, EVERY completed withdrawal was marked for the full
minute. The store hall is piles of thousands of one item, so after building out a pack the loop came
back, skipped the best chest, and either flew somewhere worse or reported nothing fetchable.

Two windows now, because they are two different facts: **60s** for a chest that was empty or came up
short — it has no more, leave it alone — and **5s** for one that handed over what was asked for. It
cannot be zero: the only reason to mark a successful chest at all is to outlast one recount.

#### The fetch could still navigate to chests that are gone

`Storage.findExact` had no world filter. The index only ever grows — it is written when you OPEN a
container and cannot be told about one you broke — and it measured **179 dead records out of 339**.
Harmless while `find` was advice; not harmless once `fetch` and `follow` NAVIGATE to those
coordinates. `Storage.live` filters the index against the loaded world on the way past, and
**unloaded is still not absent** — a chunk you cannot see is not evidence the chest went.

#### The loop re-derived everything every two seconds

`Storage.load` is a file read and a JSON parse; the scaffold and seal probes are a six-neighbour
lookup on every remaining cell, which on a few thousand cells is tens of thousands of world lookups.
Both ran every two seconds for the whole session, whether or not anything had changed.

- **The index is cached on the file's MTIME**, not on a timer. A timed cache would walk you to a
  chest the loop still believes is empty — you open a chest precisely so it can be told. And the
  cached map is **unmodifiable**, because two other callers of `load` do `removeIf` on their copy;
  a shared mutable map here is a cache that silently loses containers.
- **The scaffold/seal probe is memoised on the todo COUNT**, which is the only honest evidence
  anything moved: the printer never reports, so a count that has not changed means nothing was
  placed and the answer cannot have changed either. That makes flying to a chest and waiting at a
  station free, and that is most of a session.

#### It resumes after a disconnect

Everything the loop knows lived in static fields, so a drop at three in the morning ended it
silently. `session.json` holds four things — design, autofly, follow-all, speed — and the JOIN event
picks them up.

- **The intent is restored, not the state.** The abandoned-station set, the cooling-off chests and
  the session counters are all judgements about a world that has moved on while you were away.
- **A grace period of five seconds before anything moves.** On the tick you join, most of the world
  is unloaded, and `Nav` counts unloaded as passable — which is right for a route in progress and
  quite wrong as the first thing you do after arriving.
- **`/cscan stop` deletes the note.** Leaving it would have the loop start itself again the next
  time you joined, which is the one behaviour a panic button must not have.
- It does resume MOVEMENT AUTOMATION by itself. Announced loudly, held off, and one word to stop —
  the alternative, restoring the design but not the flying, restores the half that does nothing.

#### `/cscan follow all`

Works every tracked design in turn. A loop that finishes the deck floor at 2am and then idles until
morning is half a loop, and `plan` with no argument already ranked work across all 23 — only
`follow` insisted on being told which. A design whose work list will not load is SKIPPED rather than
fatal: one un-regenerated sidecar must not end an overnight run.

#### The routes stopped hugging walls

The search's only cost is distance, so the cheapest route grazes every corner. It is legal and it
flies like something nervous.

**The obvious fix is a clearance term in the search and it is the wrong one** — scoring openness per
node is six more world lookups on every one of up to 120,000, which is the cost that has bitten this
file twice now. `simplify` has already thrown away everything but the CORNERS, so `Nav.loosen` nudges
those few points toward open air afterwards, for nothing. A nudge is kept only when both legs through
the moved point are still `clear`, which is what stops it widening a doorway waypoint out of its
doorway.

**And a test of mine stopped being a control rather than starting to fail.** `escapeGoesAround...`
built a tall finite wall and asserted no route existed; with staging and the raised budget the router
now finds its way round the end of it. That is the router getting better. The control is a sealed
room now — *a wall in the open is not sealed*, which is the third time these tests have learned it.

### The island is the test ground (2026-08-20)

Jack: *"realistically this testing should be using my island design as the testing ground, it has all
of the variances and variables, randomness, etc."* Right, and it found two bugs in the first run.

`NavTest`'s fixtures are a wall with a hole in it, a tunnel, an L-bend — worlds I invented, testing
the cases I thought of. `tools/export_navfixture.py` exports the capture's own geometry instead:
**103x121x103 at the origin lock, 41,455 solid cells, 15 KB gzipped**, checked in at
`chunkscan/src/test/resources/island_nav.bin.gz` and read by twenty lines of bit-shifting in
`IslandNavTest`. Regenerate it after a rescan — every assertion is derived from the fixture, so a new
capture moves the numbers and not the expectations.

    python tools/export_navfixture.py

**The solidity model is STATED, not assumed.** We have no client here, so `blocks_motion` reads the
registry TYPE: air, fluids, plants, vines, wiring, signs and carpets do not stop you; everything
else does. It is close, not exact — a snow layer's height and a repeater's two pixels are not in the
registry — and it is applied to BOTH sides of every test, so the connectivity a test asserts is
connectivity under the rule the route is found under. Where it differs it errs toward SOLID, which
makes a router refuse a route it could have flown rather than fly one it could not.

#### The bug the real island found in the first run

**A route came back whose every waypoint was in open air and one of whose LEGS went through the
rock.** A single diagonal step, (+1,−1,+1), at −24207 219 30009.

The no-corner-cutting rule tested the three ORTHOGONAL components of a diagonal — beside, below, in
front — which is the standard formulation and is not enough in three dimensions. It never tests the
cell diagonally ACROSS, and that is exactly where a body sweeping between the two corners passes. So
the search and `clear` disagreed about what one step costs: the search said yes, the flight clipped
it, and `simplify` faithfully preserved the illegal leg because `clear` refused to merge it away.

`stepFits` requires the whole BOX a step spans. That makes the two agree by construction — every
cell `clear` samples on a one-cell step lies inside the box — at about twice the neighbour cost,
bounded by the same millisecond budget as everything else. **No hand-written fixture produced this**;
it needs a diagonal gap between two blocks, which real terrain is full of and a test author is not.

The second was mine: `GOAL_SLACK` is a BOX radius, and two assertions measured it as a sphere. Slack
2 permits (2,2,2), which is 3.46 away as the crow flies. It passed on the synthetic fixtures because
the answer there was always on an axis.

#### What the island tests actually assert

- **Every route it returns is legal** — every waypoint passable, every LEG clear, over 60 sampled
  pairs. Then the same again through `simplify` and `loosen`, because what the autopilot flies is
  the composition and each stage can undo the last one's care.
- **Places that are connected always get a route.** The hard direction, and the one that flies you
  into terrain when it fails. A flood finds what is GENUINELY connected under the router's own
  predicate — including its corner rule, or the flood claims a connectivity the route cannot deliver
  and the test blames the wrong thing — and then a route is demanded between pairs of it.
- **A chest-sized target in the geometry is still reachable**, sampled from real solid cells rather
  than from a chest I placed for the purpose.
- **A standoff can see its work**, on real surfaces, within the reach budget; most are roomy and the
  tight ones are the tunnels, which are real.
- **Walking routes never float**, and **escape always makes progress or admits it cannot**.
- **No single search hitches the client**, measured where the frontier meets real geometry rather
  than an empty box.

### The pre-upload audit of the whole cycle (2026-08-20)

Fetch -> fly -> take -> fly -> stand -> print -> move on, read end to end before the jar went up.
Eight findings; the last two are the ones that would have cost a night.

- **The arrival was a RACE between two files.** Autofly stopped at 4.0 from a solid goal and the loop
  started the withdrawal at 4.0 — measured slightly differently, an entity's position against a
  block's. The losing outcome is a loop that hovers at a chest for ever without opening it, which is
  the same bug this project already shipped once at 5.0 against 4.5. `ARRIVED_SOLID` is 3.0 now, a
  clear block inside where the loop acts, and `AutopilotTest` asserts the margin across both files.
- **A station that placed nothing moved on too readily.** A bin is a 4-cube, so its far corner is
  3.46 from the middle and the printer has 4.5 — a standoff a few blocks out spends the rest. Now it
  moves in CLOSER first (`standoff` at radius 1) and only abandons the bin on the second stall.
  Abandoning a bin you could have reached leaves those cells for a later pass that makes the same
  mistake.
- **A re-offered bin kept its old clock**, so it stalled again on the very next recount and the spot
  span through its bins as fast as the loop could count them.
- **Arriving was announced every couple of seconds.** The station re-centres as cells go in, so the
  target moves constantly — and every move said "arrived". Silent while following; the HUD says it.
- **An exception inside the decision ended the session.** One catch covered both the work-list read
  (permanently fatal — no work.json) and every judgement after it (transient, about a world other
  mods are changing). Now separated: a hiccup costs a tick and is reported three times, twenty in a
  row gives up. The two tick handlers that drive movement and looting are guarded too, because a
  throw out of a tick event is a client CRASH — the worst possible outcome for a loop whose whole
  point is running unwatched.
- **Nothing checked that there was anything to print.** The printer prints a Litematica PLACEMENT, so
  a design never placed, or toggled off, is a session of flying to the right spots and putting
  nothing down. `Litematica.enabled(name)` answers three ways — yes, no, and *could not ask* — and
  the third is not reported as the second: a soft dependency that changed shape is a different
  problem from a placement you forgot to make. Said once at the start, and again when the loop has
  placed nothing at all after two stalls.

#### OUT OF VIEW IS NOT FINISHED

`Work.split` can only diff cells in chunks the client HAS, and it silently skipped the rest — so an
empty `todo` means "nothing left within sight", not "the design is done". On a 240-block island that
is routinely most of a design.

The consequence was worse than a wrong percentage. **Start `follow all` at the far end of the island
and every tracked design reads complete in turn** — `nextDesign` asked the same question — so the
loop announces that all 23 are finished, in about a second, and stops. An overnight run that ends
before it starts.

`Split.unseen` counts them and `Split.complete()` is the question the loop now asks. When there is
nothing left in sight but cells out of view, it FLIES TO THE NEAREST ONE: going to look loads the
chunks, and the next recount has real work. That trip also resets the stall clock, because crossing
the island is not a stall.

`unseen` is deliberately not counted as built — the tempting shortcut reports a design finished and
quietly leaves it half-standing.

#### Smaller things

`/cscan follow` now says when autofly is OFF. `follow` points and `autofly` moves; starting
half-armed looks exactly like the loop being broken.

### Flight was lost because it LANDED (2026-08-20)

Jack ran it and it *"turned off fly and almost fell into the void and lost everything"*. The worst
thing this mod has done, and the diagnosis is worth more than the fix.

**I blamed the speed, and the speed was innocent.** `SPEED` had just been raised 0.35 -> 0.75 in this
session, so it was the obvious suspect, and I convicted it: dropped the constant, capped the dial,
and wrote a note into this file stating as fact that *"the first flight at 0.75 had the server revoke
flight in mid-air"*. Jack had watched it happen. **It landed on a block.** On a server where flight
is a plugin grant rather than creative mode, touching the ground ends it — no anticheat, no speed, no
mystery.

**A change you have just made is exactly the suspect that gets convicted without evidence**, and a
wrong cause written down confidently is worse than no note at all: everything downstream of it is
tuned against a fiction. The speed is back at 0.75 and the cap at 1.0.

The real fix is `keepAirborne`: the flying step never DESCENDS inside a block and a half of the
floor, and climbs off one it has already met. Nothing had ever said the autopilot must stay off the
ground — it was flown to a standing spot beside the work, and a standing spot is on a floor.

- **Unless there is a ceiling.** Indoors a room is two courses high, and forcing a climb there grinds
  you along the ceiling for ever. Landing on a floor inside a building is not the failure being
  guarded against; landing on the deck with the void one step away is.
- **The clearance is not decoration.** A block and a half clears a slab, a stair or a lip, and still
  leaves a station a course above the floor well inside the printer's reach.

#### What stays, because it is right for any cause of losing flight

The walking rules from the first, wrong diagnosis are kept — they are what turned a lost flight into
a near-disaster, whatever caused it. **Building requires flight; walking is only ever a fetch**, and
only with ground under it. That is Jack's rule and it is better than "walk whenever you cannot fly":
where the loop BUILDS is out over the work — the belly, the underside of the plate, a lowland eighty
blocks down — and on foot every one of those is the air over the void. Where it FETCHES is a
container somebody walked to, which is a floor.

- Losing flight while off the ground is an EMERGENCY, not a mode change: hands off, say so, disarm.
  Resuming automatically into whatever took it away is how you lose the inventory a second time.
- Falling with nothing below and autofly does nothing at all. Steering a fall never improves it.

### It highlighted cells that cannot be built yet (2026-08-20)

Same session, same root: `Plan.station` was picked over EVERY cell left in a spot, and a spot's cells
include the ones with nothing to place against. So a station could be made entirely of mid-air: you
are flown to it, the printer places none of it, and twenty seconds later the loop moves to the next
bin of mid-air. That is also most of "it got stuck immediately".

`Cluster` carries `ready` now — the cells that are not floating and not sealed in — and everything
that POINTS A PLAYER AT THE WORK uses it: the station, the highlight, the count. `cells` stays as
what is left in the region, because those cells are real work; they are just not this pass's work,
and their supports have to go in first.

`doable()` is derived from `ready` rather than computed as `cells - blocked - sealed - short`. Same
number by a different route, which is exactly how the count you are told and the cells you are sent
to drift apart.

### "It detected tuff as the same as deepslate" (2026-08-20)

**There is no block-equivalence table anywhere in the mod** — `Work.matches` compares names exactly
and the Java side has no family list at all. What actually happened is a generator decision:
`courthall._put` refuses to place where anything is already standing (*"never cover what is already
standing"*), so wherever the island's own rock occupies a cell of the order, that cell is dropped
from the design and the loop never hears about it.

Measured on `Court Hall` against the 12:38 capture — 90 design cells whose world block differs:

| design wants | world holds | cells |
|---|---|---|
| `deepslate_bricks` | `stone_bricks` | 28 |
| `deepslate_bricks` | air (real work) | 23 |
| `deepslate_bricks` | `cracked_stone_bricks` | 7 |
| `deepslate_bricks` | `moss_block` / `mossy_stone_bricks` / `mossy_cobblestone` | 17 |
| `lantern` | `deepslate_bricks` | 4 |

**A litematica printer places into AIR; it never replaces.** So those cells can never be completed by
the loop however long it runs, and the loop's only signal was getting quieter. It says so once now,
and points at `/cscan check`, which marks them amber.

**Whether the order should REPLACE Jack's stone brick is his call, not a silent one** — it is
`_put(..., force=True)` plus dig cells, and it means breaking 58 placed blocks.

### And a third meaning of "cannot be placed" (2026-08-20)

Same session: *"its still choosing clusters that cant be placed"*, after `ready` had already fixed
the first two. There are THREE questions and the loop was answering the wrong one each time:

    cells   everything left in this region, floating and sealed included
    ready   minus those two - but `floating` counts an EARLIER cell of the same design as support,
            which is right for "does this design need scaffolding" and wrong for "can I place it
            now": that support may not be built, and may not even be in this bin
    now     has a real face to click, in the WORLD, this second

`Work.placeableNow` asks the third, and the station is picked over that. `floating` keeps its own
rule, because taking the design's own earlier cells out of THAT would report every wall in the
project as needing scaffolding.

### It crashed into a block at the lowlands (2026-08-20)

Flight lost again, and a different cause from landing on the deck: it flew into terrain **that was
not loaded yet**.

**`Nav` counts an unloaded chunk as PASSABLE, on purpose** — refusing to route through one would fail
every long flight on a 240-block island, and the route is recomputed twice a second so it sharpens as
the world arrives. That is right for ROUTING and dangerous for FLYING, and nothing had ever separated
the two: the autopilot took that route at cruise into blocks nobody had seen.

**The lowland is the worst case by construction.** It is 150 blocks below the deck, so the whole
descent is into chunks arriving on the way down — and `keepAirborne`'s clearance check read open air
the entire time, because **an absent chunk answers "air" to every question you ask it**. The floor of
the lowland is indistinguishable from open void until you are standing on it.

- **`BLIND_SPEED` (0.12) when the next 8 blocks are not loaded**, ahead or two below.
- **No descending at all while blind.** Slow is recoverable; a landing is not.
- **An unloaded cell under you counts as GROUND** — the exact opposite of what `Nav` does with one,
  and right for the opposite reason.

`clearanceBelow` and `loadedAhead` were pulled behind an `Autopilot.View` so they can be tested:
they are entirely about the difference between *there is nothing there* and *I cannot see*, and that
cannot be exercised against a live client.

### The fixture now spans the whole island (2026-08-20)

Jack captured `islandlow` from inside the lowland: **103x335x103 at Y-64..270**, the full vertical
rather than the plate. 71,815 solid cells, 26 KB packed. The old fixture started at Y150, so the
descent that crashed was not in the test ground at all.

And the sampling was wrong even where it had coverage. **Uniform sampling over a capture that is 2%
solid is mostly a test that empty sky is empty**: two random open cells usually have nothing between
them and every router passes. `nearTerrain` samples cells within three blocks of a surface — under
the deck, inside the lowland, against the plate — which is where routing is actually hard, and the
legality property runs over those as well as over the uniform sample.

### The fly audit, and the whole island in the fixture (2026-08-20)

**The lowland is in the test ground and it routes.** Measured off `islandlow`, solid cells by band:

| | |
|---|---|
| Y24–48 (lowland) | **17,971** — the biggest band in the capture |
| Y190–215 (deck + plate) | 27,088 |
| Y48–190 (belly, taproot, rim) | 18,759 |
| Y215–271 (sky bird) | 7,806 |

`theDeckCanBeRoutedDownToTheLowland` now ASSERTS its endpoints instead of returning when it cannot
find them — a test that skips quietly when its own fixture is wrong reports success and proves
nothing, which is how a suite stops meaning anything.

**And the sampling was measuring the wrong island.** Uniform sampling over a capture that is 2%
solid is mostly a test that empty sky is empty. `nearTerrain` samples within three blocks of a
surface, which is where routing is hard.

#### Every way a flight can end, and what now handles it

| how it goes wrong | what stops it |
|---|---|
| lands on a block, plugin flight ends | `keepAirborne` — never descend inside 1.5 of a floor, climb off one |
| descends into chunks not loaded yet | an unloaded cell below counts as GROUND |
| flies at cruise into unseen terrain | `BLIND_SPEED` 0.12 when the next 8 blocks are unloaded |
| **flies into a wall the route thought was clear** | **`horizontalCollision` forces a repath THIS tick and backs off** |
| **routes through lava or water** | **`Nav.open` refuses anything with a fluid state** |
| corner clipped at speed | waypoint radius and approach taper scale with the speed |
| route stale as the printer builds | repathed twice a second, floored at 5 ticks |
| no route at all | `escape`, then direct with `unstick`, never a partial |
| flight lost while airborne | emergency halt, hands back, disarm |
| on foot over the void | building requires flight; walking is only ever a fetch, with ground |

The two new ones are the ones this audit added:

- **`blocksMotion` is FALSE FOR LAVA.** The router would have flown straight through it, and on this
  island the lowland has water and the court has a tank. Both are cheap to go round, so both are
  simply not passable. The nav fixture had to change with it, or the island tests would be about a
  different island — 811 more solid cells, and `kelp`/`seagrass`/`lily_pad` went with the water they
  stand in.
- **Bumping into something is evidence the route is wrong**, not something to push through. Grinding
  along a face is how a flight slides down a wall onto a ledge, and landing is how flight is lost.
  It re-routes on the tick and pushes back out of the face first, so the next search starts from
  open air rather than from inside the wall.

### The loop's judgements, taken out of the loop (2026-08-20)

`gen/Loop.java`, and `LoopTest` is 24 cases over it. **Every bug in the unattended loop has lived in
four decisions**, and none of them could be tested, because they were written inline in a method
that also opens chests, draws particles and flies a player. The list, in the order they shipped:

- fetching whenever a spot was short of anything, so it went shopping with a full pack and hundreds
  of placeable cells;
- a spot stall that cleared the arrow but not the SPOT, so the hysteresis chose the same region
  straight back and stalled again for as long as you left it;
- a station re-offered after every bin had been tried, keeping the clock that had just abandoned it;
- an empty todo list reported as complete when most of the design was in chunks the client did not
  have, which ended a `follow all` run in about a second.

None of those is a hard problem. All of them are invisible inside a method with a world attached. So
`Loop.phase`, `Loop.sameSpot`, `Loop.station` and `Loop.stalled` are pure functions over plain
values, `Hud` does what they say, and the awkward questions get asked directly:

    itDoesNotGoShoppingWhileItHasWorkInFrontOfIt
    aTripKeepsGoingUntilThePackIsFull
    aDriftingCentroidIsStillTheSameSpot
    aStationThatPlacesNothingMovesInCloserBeforeGivingUp
    outOfViewIsNotFinished
    aWholeSessionOfPhasesTerminates          # all 64 combinations, no silent do-nothing state

The last one is the property that matters for leaving it running: from any starting point the loop
either does something or says why. It cannot sit in a phase with nothing to do and no message.

### What is in a shulker box is not what you are carrying (2026-08-20)

`Work.boxed` reads the `CONTAINER` component of every stack in the pack. It is deliberately **NOT**
added to `carrying`, and the distinction is the whole feature:

- **a boxed block is not placeable** — you would have to set the box down, open it, take the stack
  and break the box again, none of which this mod does. Counted as carried, the loop flies to a spot,
  finds it can place nothing, and stalls there;
- **but it is absolutely a reason not to fly across the island for more.** `Plan.notInAPack` drops
  any shortfall the boxes already cover, and says so once per material rather than silently doing
  nothing.

Half a box is not a solution and is still a trip: you would set it down, take 64, and still be short.

### "It moves like 5 degrees and gets stuck" (2026-08-20)

The collision handler added one round earlier, doing three things wrong at once:

- **`pathTo = null` bypasses the repath floor.** `needsRepath` checks it FIRST, before
  `MIN_REPATH_TICKS`, so it ran a full A* every tick for as long as you were touching the wall —
  the same shape as the one-frame-a-second bug, from a different direction.
- **It RETURNED before the aim.** The yaw never updated while colliding, so it turned one eased
  step — about five degrees — and then froze. That is the whole reported symptom.
- **It backed off along that frozen yaw**, into whatever was behind, and collided again.

Now a bump keeps steering: ease off the forward push to a quarter, climb, and ask for a route
through the normal gate that respects the floor. Only after two seconds of solid contact is the
route declared wrong rather than stale, and only then is it dropped — once.

### THE JUMP KEY IS A FLIGHT TOGGLE, NOT A CLIMB CONTROL (2026-08-20)

Written the other way round for about twenty minutes, and in that time **the mod revoked its own
flight in mid-air** and then reported the fall as though something had been done to it. Jack: *"its
also self revoking flight on accident and saying im in control when im not even touching."*

The reasoning that got there was sound and the conclusion was dangerous. A set y velocity IS damped
by `travelFlying` every tick, so a commanded climb does arrive as a drift; holding JUMP is how a
player climbs. But **vanilla toggles flying on a DOUBLE TAP of jump** — `LocalPlayer.aiStep` opens a
seven-tick window on the first press and flips `abilities.flying` on the second — and driving the key
to climb presses and releases it as the desired vertical crosses a deadzone. Inside seven ticks, that
is a double tap.

The vertical is a velocity again, scaled by `VERTICAL_GAIN` to survive the friction rather than
pressed. `hold` survives for exactly one job: the rescue taps, where toggling flight is the POINT.

Worth keeping anyway, since it cost a javap and is not written down elsewhere: driving
`LocalPlayer.input.keyPresses` does not work at all — `ClientInput.tick()` runs inside the player's
own tick and overwrites it before movement, so anything set from a Fabric tick event is gone before
it is read. `KeyMapping.setDown` is the only mechanism that survives.

**And the message was wrong as well as the behaviour.** "You have control" reads as "you took over",
which is both confusing when the player is not touching anything and, on the occasion it was this
mod's own doing, false. It says *not by you* now.

### Air underneath, and air overhead (2026-08-20)

Jack, watching it work: *"it cant be within 1 block beneath when flying to place because it will auto
stop flying."* Whatever the server's plugin measures, it looks further down than the block you are
touching.

- `Nav.standoff` now REFUSES a standing spot with less than two clear cells under it, keeping such a
  cell only as a last resort and never preferring one.
- `GROUND_CLEAR` 1.5 → **2.5**, so the flight cannot descend below the altitude the standoff was
  chosen for.

It is bought out of the printer's reach budget, which is exactly why the station moves in CLOSER on
its first stall instead of giving up: altitude first, reach second.

**And the same over the head.** *"we bump our head a lot."* `Passable` guarantees the two cells a
player OCCUPIES, which is enough to be somewhere and not enough to work there — because the flight
holds altitude by CLIMBING, so a spot with the ceiling on its head grinds upward into it for as long
as it stands there. `Nav.AIR_ABOVE` requires one clear cell over the head, and `keepAirborne` clamps
every upward push to zero when there is something directly overhead. There are three places that
raise y — the ground clearance, the bump handler and the direct-flight unstick — and one clamp for
all of them, because that is the kind of rule that gets added to two of three.

### Falling is an emergency with two rescues (2026-08-20)

Jack: *"if it detects falling suddenly it needs to automatically start flying (tap space twice) or
just instant type in chat /is"*.

A fall is four things at once: not flying, not on the ground, dropping faster than 0.6 a tick, and
nothing under you. All four, or every trip down to the lowland ends with the loop teleporting you
home.

1. **Double-tap jump.** Costs nothing and re-enters flight — but only when the server still says you
   MAY fly.
2. **`/is`.** Always works, and moves you across the island, so it is the fallback rather than the
   first move, and it is rate-limited to once every ten seconds because it is a teleport.

**Below Y100 it skips straight to `/is`.** The plate is Y201 and the deck Y190–199, so above that
line a fall has island under it and the taps have both time to work and something to land on. Below
it you are under the belly and what is beneath you is the void: the taps cost a third of a second
and buy nothing there, because if flight were available you would not be falling. The lowland floor
at Y24–47 is under the line too — landing on it is survivable and being teleported home from above
it is merely inconvenient, while the fall that MISSES it is the one that is not.

It is checked before everything else in the tick, including having a destination: the whole point is
that it fires when the loop is not in control of what is happening.

### `/cscan why`

The answer to "it got stuck", without a round trip through a description. Design, counts, how many
cells have something to build against RIGHT NOW, the materials and what you carry of each, whether
the Litematica placement is loaded and enabled, the phase, the spot, the arrow, the session report,
and then everything the autopilot knows: flying or not, on the ground or not, speed, bumping, the
route length or that there is none, and the distance to the target.

The loop computes all of this every two seconds and says almost none of it, because a loop that
narrates itself continuously is one nobody reads. Asked, it answers completely.

### Three clocks, and why one number cannot serve them (2026-08-20)

Jack, in two instructions: *"if nothing is placed in 5 seconds, move on immediately"* and *"if it
says it needs to reroute and doesnt move or doesnt perform action within 3 seconds, move to next
cluster"*. They are different questions and they now have different clocks:

| clock | asks | fires after |
|---|---|---|
| `NOWHERE_MS` | am I actually travelling? | **3s** of no movement AND no placement, while en route |
| `STATION_MS` | is the printer taking anything from where I stand? | **5s**, and only once ARRIVED |
| `STALL_MS` | is this loop doing anything at all? | 90s |

They must stay in that order or the slow one fires first and the fast one never does;
`theThreeClocksAreOrderedByWhatTheyAskAbout` asserts it.

**Five seconds is only safe because the station clock starts on ARRIVAL.** Timed from when the
station is chosen — which is what it did — anything more than a few seconds' flight away would be
abandoned before the printer ever had a chance at it, and the loop would tour bins placing nothing:
exactly the failure the clock exists to catch, caused by the clock.

**And the travel watchdog is sampled every TICK, not every recount.** The recount is every two
seconds, and a three-second watchdog read at two-second intervals cannot tell three seconds from
five.

Standing still is only wrong while TRAVELLING: at the work you hover while the printer takes blocks
off you, and at a chest you stand while the withdrawal runs. Both are the loop doing its job, which
is why the test is movement AND placement AND having somewhere else to be.

**Giving up on a spot has to make the next choice different.** The first version cleared the arrow
and let the next recount choose — which picked the same region, because it was still the best one,
flew at the same wall and stuck again. The spot is now passed over for a minute, and the route is
dropped with it (`Autopilot.forget`), because a route is computed from a destination and keeping it
after the destination is abandoned is keeping a plan to fly at the thing that just stuck. If
everything left is near the spot that failed, it takes it anyway: a hard spot beats idling until the
avoid expires.

### Shulkers, on both sides of the wall (2026-08-20)

*"make sure it detects shulkers also."* Audited every list on both sides that decides whether
something is a container, and the ones that exist were already right — `Storage.CONTAINERS` and
`STORES` match `shulker_box` by substring so `white_shulker_box` counts, `protect.MECHANISM` and
`protect.USED` cover it, and the shipped `chunkscan_rules.json` carries it. A placed shulker box has
never been at risk of being built over.

**The gap was the one that is not in any of those lists: a shulker box inside a chest.** The index
records what the container screen holds, so a chest of six boxes was filed as *"6x
white_shulker_box"* — true, and useless. The ten thousand blocks inside were invisible to `find`, to
the bill of materials and to the build loop, which would fly past them to a chest with sixty-four
loose ones. **Bulk storage on this island IS boxes in chests.**

- `ContainerWatcher` now reads the `CONTAINER` component of every stack it indexes, into a separate
  `inBoxes` map on the record.
- **Kept apart from `items`, deliberately.** Getting at a boxed block is a DIFFERENT job — take the
  box, set it down, open it — and a plan that says "500 bricks, 22m NE" when it means "a box you must
  unpack" has lied about the only number that mattered. `findExact` takes a flag; the plan passes it,
  a bare lookup does not.
- `Withdraw` will take a BOX that holds what it came for, and `carrying` counts boxed ones toward
  the target — without that it keeps taking boxes for ever. `Work.boxed` then tells you to set it
  down, because a client mod cannot unpack one for you.
- `/cscan find` falls back to searching inside boxes when nothing loose matches, and always says how
  many of a hit are boxed.

`inBoxes` is absent from every record written before today, which reads correctly as "no boxes known
here" — the entry is rewritten from the screen the next time you open that container.

### "Climbing over it" is one instinct applied to five situations (2026-08-20)

Jack: *"need better solution than only climbing over it when often climbing up is the problem in the
first place."* Right, and the ceiling rule one section up is the proof — the bump handler climbed
into the thing that was already on its head, and kept climbing.

**A bump now asks the geometry instead of guessing.** `Nav.escape` already knows how to answer this:
flood outward from where you stand and take the reachable cell that gets CLOSEST to the goal,
whichever direction that turns out to be. It runs at a short radius (10) and on a timer
(`BUMP_LOOK_EVERY`), because a flood on every tick of contact is the cost this file has paid twice
already. When it finds something, the loop flies that instead, easing round the corner at 40% speed.

**And when there is no way round at all, `sidestep` SCORES every direction by whether it actually
helps** — the dot of each open way against the heading, with a thumb on the scale for sliding.

It was a fixed ladder first (sideways, up, down, back) and that was the same mistake one level down:
`down` sat at the bottom, so it was only ever taken when climbing was BLOCKED. On this island most of
the work is below you — the lowland, the belly, half the deck — so every bump on the way there went
the wrong way over the obstacle. Scored, a downhill heading escapes downwards, an uphill one climbs,
and a level one slides, which is what the bias is for: a perpendicular scores zero against a level
aim whichever way it points.

**And the descent may use SHIFT.** Only JUMP toggles flight — that is what revoked Jack's flight in
mid-air — so sneak is safe, stronger than a y velocity `travelFlying` is busy damping, and is what a
player does. The movement path is handed a `sink` that can only touch shift, so it CANNOT press the
other one.

**Found while doing it: the bumped-step handling had been silently deleted.** An earlier edit in this
session replaced the whole flying-step block to add the vertical gain and took the collision slowdown
with it, so for several commits a bump did not slow the flight at all. That is the second silent
no-op edit today; the patch scripts now hard-fail on a missing anchor instead of quietly changing
nothing.

### `/cscan off` was not a command, and `stop` was not a stop (2026-08-20)

Two faults behind one report.

**`off` did not exist.** The only spelling was `stop`, so `/cscan off` failed as an unknown command —
which looks exactly like a stop that did not work, and `off` is the word that gets typed. Both run
`stopAll` now, and `MenuTest` asserts they run the SAME thing: two commands that stop different
amounts is worse than one command.

**And `stop` left four things running:**

- **Six highlight layers kept drawing.** It cleared `goto`, `next` and `scaffold` — the three the
  build loop uses — and left `find`, `check`, `dig`, `dark`, `mark` and `marks`. A panic button that
  leaves the screen covered in particles reads as one that did nothing. `Highlight.clear()` with no
  argument was there the whole time.
- **`Hud.off()` kept `followAll`**, so a later `/cscan follow <one design>` silently became "follow
  all of them".
- **...and the spot, the abandoned stations and the avoid list**, inherited by a run that has nothing
  to do with them.
- **Auto-scan carried on**, writing a capture per tick into an archive this file already notes is
  unbounded.

Half a stop is the kind that is discovered an hour later.

### Getting flight back, when it is merely absent (2026-08-20)

Jack: *"it needs to also activate fly again if its purely not moving because its not in fly anymore
because it bumped into something etc."*

The walk gate — building requires flight, walking is only ever a fetch — stops the loop doing
anything DANGEROUS without flight, and stopping there is only the right answer if nothing can be done
about it. Usually something can: **the same double tap that rescues a fall turns flight back on while
standing on a floor.** From the ground the first tap is a jump and the second lands while airborne,
which is exactly the gesture a player makes.

Tried whenever the loop has somewhere to be, is not flying, and the server still says it MAY fly.
Three guards, each of which is the difference between a fix and a nuisance:

- **`mayfly` false and it does not try at all** — tapping will not change the server's mind — and it
  says so once rather than every two seconds.
- **Four attempts, then it stops.** A tap that has not worked will not work the fortieth time, and a
  player watching their character hop twice a second is watching a bug.
- **A minute between attempts**, for the same reason.

### Threading a one-wide gap (2026-08-20)

Jack: *"we also need to do better at being able to locate areas we can fly through e.g. 1x open
spaces we can fly up through if we align correctly, it gets stuck quite a lot still."*

**The routes through those are already found.** `Nav` models a body 0.8 wide and a one-wide shaft
passes it; `NavTest` has had `aVerticalShaftIsFlyable` and the highway cases since the tunnel work.
The island is full of them — the taproot, the workshop necks, the well — and what fails is not the
finding, it is the FLYING: steering at a waypoint centre from off to one side arrives at the mouth
still carrying that lateral drift, catches the lip, and bumps. Then the bump handler goes round
something it was already lined up with.

**So it lines up first.** When the way ahead is walled on both sides of an axis, that lane is
CENTRED before any progress is made along the passage — and no progress at all until it is, because
creeping forward while still off to one side is exactly how you catch the lip you were threading. It
is what a player does without thinking.

- Measured at the TARGET, not at the player: the point is to be lined up before arriving.
- Only the WALLED lanes are corrected. Centring the open one would drag the flight to the middle of
  every corridor it passes down, which is not alignment, it is a detour.
- The correction is capped by the error and by the speed, or overshooting the middle of a one-wide
  shaft puts you against the far wall — the same bump from the other side.
- And a gap you have to be lined up for is flown at `TIGHT_SPEED`, because the alternative is
  arriving correctly aligned and too fast to stay that way.

### The bumping was structural, and the heuristics were standing in for it (2026-08-21)

*"still lots of bumping, and turning off fly by touching blocks, we really need to fix this."*
Everything added over the previous rounds — climb over it, slide round it, get flight back, tap it on
again — is a response to CONTACT. None of it asks why the flight is touching blocks at all. Two
reasons, both structural.

#### 1. It flew a leg nobody had checked

`clear` validates waypoint-to-WAYPOINT. What actually gets flown is *wherever-I-am* to waypoint, and
the moment drift, a bump or a corner puts the body off that line, the leg being flown is a CHORD
across whatever the route was going round. The route was fine; the flight was not on it.

`pursue` is plain pure pursuit: steer at the nearest point on the validated segment, a block and a
half ahead. On the line it changes nothing; off it, it pulls back on. **A route is a set of
corridors, not a set of points.**

#### 2. A* minimises distance, so every route skims

The cheapest path runs along the surface it is passing. Fine for a pathfinder, wrong for a server
where flight is a plugin grant and **touching a block ends it**. `Nav.roomy` requires a clear cell on
all six sides, and the route is searched in that world FIRST.

**Measured on the island, it failed more than half the time — and the reason was the ends, not the
middle.** 14 of 32 routes near terrain had a fully roomy answer; the other 18 were not threading
tunnels, they were LEAVING one surface and arriving at another, because every endpoint this loop uses
is a standing spot beside the work or a chest in a wall. So `roomyBetween` drops the clearance rule
within `ENDS` (6) of either end and keeps it for the long middle, which is where a flight spends its
speed. The island test asserts three quarters of them now keep their distance where it matters.

#### And the arrival precision was being bought with contact

Jack: *"the focus should be getting within a 3 block radius of the point since we know we reach+place
further."* Right, and it is the same lesson a third time. `ARRIVED` had been tightened 3.0 → 1.5 to
protect the printer's reach budget — so the last two blocks of every approach were threaded, slowly,
between whatever the standing spot was beside, with the alignment fighting the drift. **Every one of
those is a chance to touch a block and lose flight, spent buying a precision the printer does not
need.**

What pays for it: `Plan.reach()` asks litematica-printer for `Configs.PRINTING_RANGE` instead of
assuming four blocks. That is the same "ask the game, not your memory" rule this project applies to
every block property — and then never applied to the mod it is driving.

### Half speed everywhere, and the aim is not the waypoint (2026-08-21)

*"why does it fly very slowly when going towards a location, its like its going half speed."* An hour
old, and caused by the pure-pursuit fix in the section above.

`pursue` returns a point **`LOOKAHEAD` blocks ahead by construction** — that is the entire idea. The
approach taper was still measuring against `aim`, so on every tick of a two-hundred-block flight it
was told there were 1.5 blocks to go, and held the whole journey at `max(0.06, 1.5/12)` = **0.125
against a cruise of 0.75**. The bend check read off the same point and saw a permanent corner on top
of that.

**The waypoint is the thing being approached; the aim is only where to point.** Two different
questions that had been one variable, and merging them was invisible the moment the aim stopped being
the waypoint.

`cruiseSpeed` is pure now, and takes both distances separately — the destination's for the final
slow-down, the waypoint's for the corner.

**And there was a second half to it, which is why the first fix did not settle it.** The taper was
applied to EVERY waypoint, not just the last. A route through cluttered terrain is made of dozens of
them — on the deck they land about four blocks apart — so `toWaypoint` was never more than four, the
taper fired on every tick, and the flight ran at `4/12` = **0.33 against a cruise of 0.75**. Exactly
half speed, which is what it looked like.

A corner does not need slowing down for its own sake: `bend` already handles TURNING, which is about
the angle rather than the distance. Flying past an intermediate waypoint quickly is not overshooting
anything. **Only the last waypoint is a place to stop.**

**And the HUD was showing the DIAL.** Two separate taper bugs held the flight at a third of its speed
across hours of testing, and either would have been a glance to spot if the readout had said what was
actually being flown. It shows `@0.33/0.75 arriving` now — applied, dial, and which clamp is doing
it: `corner`, `arriving`, `threading`, `chunks not loaded`.

### Three blocks is a ceiling, not a target (2026-08-21)

Jack, immediately after asking for the three-block rule: *"if we always are 3 blocks its hard to
reach all blocks since we lose 3 blocks to air"* — and then the other half of it — *"this needs to
balance against safe landing and stopping fly, we need to be smart about this when its possible, and
when we should just be floating a bit closer."*

Both are right and they pull opposite ways. Three blocks of standoff is three blocks off the FAR
CORNER of the bin as well, and the printer's reach has to cover both; but closing the gap by pressing
up to a surface buys that reach with contact, and on this server contact ends the flight. **A flight
is worth more than the block it was reaching for.**

So neither number is decided in advance:

- it keeps closing until it **physically cannot** — `bestDist` and `sinceCloser` measure whether the
  approach is still making progress, which is what *"the actual space after stopping"* means. A
  flight wedged against a shelf 2.4 blocks from the work has arrived; waiting for 1.2 there is
  waiting for ever;
- it stops a block short of anything it is approaching (`SAFE_GAP`), at the feet AND the head,
  because an approach that clears one and not the other is the head-bumping by another name;
- and `ARRIVE_MIN` (1.2) is where it ends up in open air, because past that nothing is gained.

In open air it floats right up to the work. Against a wall it stops where the wall says. The
difference between those is measured rather than guessed, which is the whole of it.

### The fall safety outlives the autopilot (2026-08-21)

Jack, after it happened twice: *"if we turn off auto fly because of w/e, we still need to for the
next 30 seconds have active /is auto usage or auto fly to save falling in case its a momentum
mistake."*

**Switching off is the most dangerous moment, not the safest.** Whatever the reason — the emergency
disarm, a `/cscan stop`, flight revoked in mid-air — the body keeps whatever velocity it had, and the
one thing that was watching for a fall has just stopped.

The rescue is the part with no business being tied to whether the loop is driving. It does not steer,
it does not build; it notices a fall and does something about it. So it now runs for
{@code GUARD_MS} = 30s after autofly goes off, and the tests pin BOTH halves: that it still runs, and
that it steers nothing while it does.

Thirty seconds covers the arc of any fall this island can produce, and is short enough that it is not
quietly on for ever — which would make it a mode rather than a safety. `/cscan why` and the
mid-air-revocation message both say how long is left.

### Neither close enough nor safely far: fixing both at the source (2026-08-21)

*"still its either not getting close enough, or getting too close when adjusting and then stopping
flight."* Two halves, two different causes, both in how the standing spot was chosen and held.

#### Too close: it kept adjusting

The station re-aimed every time a few blocks went in — which sounded like a feature ("walks you round
the work") and is a fresh APPROACH every couple of seconds, each one a chance to nudge a wall and
lose flight. The question was being asked wrongly: not *is the aim still ideal* but **can the printer
still reach what is left**. While it can, holding still beats improving, and now it holds.

#### Not close enough: the standing spot was chosen for the wrong quantity

It was picked by proximity to the bin's centroid — and then the flight parked short of it, so the
number deciding everything was a distance to a point nobody cared about. Worse, `STANDOFF` was 3 in
CHEBYSHEV, which is 5.2 as the crow flies, and a bin's far corner is already 3.5 from its middle.

`Plan.bestStand` scores every open cell near the work by **how many of the remaining cells the
printer could touch from it**, discounted by how far short the flight is expected to park. Ties go to
the nearest, because two spots that build the same wall are the same spot.

**Clearance is a filter, not a term in the score.** A spot that touches something is not a worse
spot, it is not a spot at all — on this server it ends the flight. `AIR_BELOW`, `AIR_ABOVE` and
`SAFE_GAP` are what keep the approach safe now, rather than standing further back and hoping, which
is what let `STANDOFF` come down from 3 to 2.

### Arrive, and then stay a moment (2026-08-21)

Jack: *"when we reach an area we dont instantly run away if we are placing blocks, we should reach an
area, stay for a few seconds, then move on unless something e.g. blocked."*

The bin is re-chosen on every recount, and the fullest one changes as cells elsewhere become
placeable — so a station could be abandoned two seconds after arriving, before the printer had taken
a single block, in favour of somewhere that merely looked better. **All of the flying, none of the
building.**

`DWELL_MS` (4s) holds the spot from the moment it is actually REACHED, not from the moment it is
chosen — the flight there can take longer than the dwell. `Plan.stationOf` is what makes that
expressible: it answers *"what about the bin I am standing in"*, where `Plan.station` only ever
answered *"where is the best work"*. Staying put must not mean re-deciding every two seconds that
staying put is still best.

**Just under `STATION_MS` on purpose.** The dwell holds the spot; if nothing has been placed by the
time the stall fires, the stall is what moves it on. A dwell longer than the stall would be a loop
that cannot leave somewhere it cannot build — which is the failure this whole layer exists to avoid.
And an empty bin is not a station, so the dwell ends honestly when there is nothing left to build
rather than running out a clock.

There are now four clocks and they compose in one order, each shorter than the one it can interrupt:

    3s   going nowhere      told to travel and not travelling
    4s   dwell              having arrived, stay and let the printer work
    5s   station stall      arrived, dwelt, and nothing was placed
    90s  session stall      the whole loop has done nothing

### Two mechanisms fighting: the shaft loop (2026-08-21)

Jack: *"stuck in a loop of going up a 1x hole hitting a bump and needing to find a way around and
repeating."*

Both halves were working correctly, which is what made it a loop:

1. the route picks the one-wide shaft, because it is the way through;
2. the flight clips the lip on the way in and bumps;
3. the bump handler looks for a way ROUND — and a way round a shaft is the way back OUT of it;
4. it flies out, re-routes, correctly picks the shaft again, and repeats.

**A bump inside a gap you are threading is not an obstacle, it is a nudge.** While threading, contact
now means line up better and creep — the escape search is not consulted at all. Only after
`WEDGED_TICKS` of that has plainly failed is the passage itself treated as the problem.

Two supporting changes:

- **The tightness is read from the next WAYPOINT as well as the aim.** Aligning only once the aim is
  inside the gap is aligning after the first contact with it, which is too late by definition.
- **`Hud.abandonSpot`.** Threaded, aligned, crept and still nowhere: the shaft stops being the
  problem to solve and the spot beyond it is not worth this. The FLIGHT is the only thing that knows
  a way is not flyable, and the LOOP owns where to work — so the flight asks rather than decides, and
  the spot is passed over for a minute exactly as the three-second watchdog does it.

The general shape is worth keeping: when two correct mechanisms produce a loop, the fix is almost
never to make one of them cleverer. It is to notice that they are answering the same question and
decide which one owns it.

### The navigation audit (2026-08-21)

Read `Autopilot.tick` and `Nav` end to end after a day of patches. Four defects, and three of them
were **invisible in the code and only visible in the arithmetic between constants** — which is what
an audit is for.

- **The approach tracker belonged to the ROUTE, not the target.** `bestDist` and `sinceCloser` were
  reset when `pathTo` changed, and the route is often null at exactly the moment the destination
  changes — a fetch ending, a station moving. So the tracker carried over from the last place: the
  new target looked like something that had already stopped getting nearer, `sinceCloser` ran up, and
  it "arrived" at the ceiling instead of closing in. **The third distinct cause of "not getting close
  enough".**
- **`wedged` accumulated only by accident.** It incremented inside `if (threading && bumps <
  WEDGED_TICKS)`, and `bumps` is reset every `STUCK_TICKS` — so it counted at all only because
  STUCK_TICKS (40) happens to be smaller than WEDGED_TICKS (60). Raise that one constant and the
  give-up would silently never fire again. It is counted in its own right now.
- **Staging could not run at the distances this island uses.** `for (stage = STAGE; stage >= 16 &&
  stage < d; stage /= 2)` does not execute at all when `d` is shorter than STAGE: the condition fails
  on the first evaluation and never reaches 64 or 32. Staging exists for searches that FAIL, and it
  was unavailable for every distance between 16 and 128 — which is where this island's routes live.
- **Arriving did not clear the contact state**, so the next leg began with a bump count inherited
  from the last one and gave up early.

The pattern in three of the four: a constant's value silently deciding whether another mechanism runs
at all. None of them would have failed a code review; all of them are arithmetic.

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
| `export_navfixture.py` | the island's geometry as a bitmap, for the Java routing tests |

`proportions.measure` and `rubric.score` are shared entry points — `stance`, `refine` and `scale` all
call them, so a change to how something is measured cannot drift between tools.

**`chunkscan/`** (client only, `src/client/java/dev/jack/chunkscan/`)
`ChunkScanClient` (commands) · `WorldCapture` (chunks → `Capture`) · `LitematicWriter` (NBT out) ·
`SidecarWriter` · `ScanRunner` (glue + archive) · `Litematica` (reflection bridge, soft dependency) ·
`Markers` · `Storage` + `ContainerWatcher` (container index) · `Highlight` (particles) · `AutoScan` ·
`Wand` + `Fill` + `Rules` (the steak wand — see below) ·
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
