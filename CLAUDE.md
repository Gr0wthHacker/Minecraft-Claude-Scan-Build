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
python tools/look.py "<design>"                    # 8. ...and in 3D, from every bearing
python tools/panel.py "<design>"                   # 9. and have it REVIEWED - see below
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

**Amended 2026-08-27 by the download corpus** - see "Reading other people's builds" below. The
line is not the species, it is whether the silhouette decomposes into LIMBS: a curled cat built as
one convex mass reads instantly, and a corpus of 31 outside builds contains no realistically-
proportioned quadruped at all.

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

## Seeing it in 3D: `tools/look.py` (2026-08-28)

```bash
python tools/look.py "X elephant"                     # eight bearings round it, on one sheet
python tools/look.py "Lowland Frog" --sheet panel     # head-on, profile, plan, silhouette, value, distance
python tools/look.py "Lowland Frog" --bearing 0 --dist 0.5 --look-high 0.85 --big    # its face, close
```

`mcbuild/render3d.py` is a voxel raycaster in numpy - perspective camera, Minecraft's own face
ladder, corner AO by the game's rule, and a directional sun with hard cast shadows. No new
dependency: numpy and Pillow, like everything else here.

**IT EXISTS BECAUSE AN ORTHOGRAPHIC VIEW CANNOT SHOW THE THINGS THAT KEEP GOING WRONG.** This file
already records the clearest case and did not draw the conclusion: the axolotl's head read as a blob
in game and correct on every sheet, and the reason is stated here verbatim - *"an orthographic render
along the body axis cannot show this failure - projecting along the diagonal de-jags it by
construction."* Two more of the same shape: *"there is no weight anywhere: the outline is a
constant-depth rectangle"* is a question about OCCLUSION, and depth-shading darkens a recess whether
or not anything occludes it; and *"does it look BUILT"* is a question about how light breaks over
steps, which a flat fill shaded by distance has none of.

**THE BEARING IS RELATIVE TO THE RECORDED FACING**, read off the sidecar exactly as `panel.py`
chooses its profile axis - 0 is head-on, 90 profile, 180 tail-on. Picked by hand this was got wrong
twice in one session, and a design with no recorded facing SAYS SO rather than defaulting quietly.
`tests/test_render3d.py` asserts it: bearing 0 puts the camera nearer the head, 180 nearer the tail,
and the two profiles are mirror images to 99.6%.

**What it costs.** 0.3-0.8s for an animal, **1.4s for the whole island** (110,551 blocks in a
103x335x103 grid), because the march compacts its active set - a ray that has hit or left the box is
dropped, so the arrays shrink every step instead of every ray paying for the longest one. Context
views are therefore affordable, not just the animal alone.

**Calibration, which is the only reason to trust it.** The elephant is *"the control the panel is
calibrated against"* and it reads instantly here - trunk, ear, dome, columnar legs. The jaguar is the
recorded failure and renders as exactly its recorded verdict: a constant-depth slab from shoulder to
rump on four posts at the corners. A renderer that flattered the jaguar would be worthless.

**It found something on the frog the panel had understated.** The recorded verdict was *"MARGINAL in
profile - a low mass with a raised head"*. In 3D the profile is worse and the cause is localised: the
haunch is a **flat-sided box** with a hard vertical rear face, and the value panel shows it as one
untouched mid-grey rectangle. That is the jaguar's own failure - a flat wall painted two colours - in
a build that passes head-on. **FIXED the same day** - see the frog's own section: the cure
was a course-by-course step, not a chamfer.

**The trap inside it, which shipped a clean-looking render.** A ray whose FIRST voxel is solid never
takes a step, so it reported whatever axis the march was initialised with, and every surface touching
the grid's own bounding box shaded as an east/west face. A cropped model touches that box by
definition, so this was wrong for the outermost shell of every design - and it looked fine, because a
wrongly-shaded face is still a face. The entry axis now comes from the slab test. Two of the tests
that caught it were mine and wrong first: a bar viewed down its own axis has no taper to measure
(it occludes itself), and two cubes on the same sightline are one cube.

**What it deliberately does NOT fix.** Colour. Every block is still a flat RGB from the same DB
`nearest()` optimises against, so the circularity this file records is narrowed, not closed: what is
new is GEOMETRY and OCCLUSION. Judge form, mass and silhouette here; judge palette in game. Real jar
textures and real block models (stairs, slabs, trapdoors - 2,657 models and 1,269 textures are
sitting in the client jar) would close the rest and are the obvious next step, but they buy almost
nothing for ANIMALS, which are near-100% full cubes - `shell.py` gets no purchase on six of the
eight. They are worth building the day the question is about the enrichment pass, whose *"payoff is
geometric relief, and that does not show in our renders"*.

**AMENDED 2026-08-29: half of this is now done, and the reasoning above was wrong in a way worth
keeping.** "Animals are near-100% full cubes" was true only while no animal used a shape block. The
frog's toes are stairs - which is what makes a toe TAPER instead of ending at a vertical face - and
the day they went in, every sheet here drew them as cubes. `render3d.subdivide` gives stairs and
slabs their real shape by expanding each block to 2x2x2 half-cells; textures and the rest of the
model zoo are still not done. The lesson generalises: *a renderer that cannot draw a feature is an
argument for not using the feature*, and that is backwards.

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

**~~Pre-existing, found while running the suite:~~ FIXED 2026-08-23** — `configs/store_hall.yaml`
crashed the pipeline with `ValueError: nothing built` (100% built, emitted nothing, `World.canvas`
raised). The day Jack finished placing the Reaching Root it hit the same wall, and the pipeline now
reports such a design COMPLETE (`Result.complete`) instead of raising.

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

## The lowland scene, completed: the ring-gate and the axolotl (2026-08-21)

Two additions off the 13:10 scan, one retirement, and two re-sitings. Everything below was
measured before it was designed, and the numbers picked most of it.

| design | blocks | what it is |
|---|---|---|
| `Lowland Portal` | 488 | a D25 ruined ring of blackstone masonry at (-24171, 30025), Y44-70 |
| `Lowland Axolotl` | 989 | pale pink, curved, head over the shallows at (-24201, 29988), Y39-49 |

**The portal stands in the entrance light.** 628 lowland columns are open to real sky and 493 of
them are ONE blob at X-24186..-24158 / Z30015..30041 - the shaft players descend to enter the
underworld. The ring's footprint is 96% open sky, covers zero lanterns, ground Y45-52, headroom
139, and the sightline from the pond's west bank is clear. Aperture faces east-west: frontal from
the pond, walk-through on the axis of travel. Behind it the massif crests and drops into void, so
the upper aperture frames open sky - the gate appears to open somewhere else, bought entirely by
siting. The vanilla ruined-portal palette is CHEAP here (polished/cracked/chiseled/gilded
blackstone) while obsidian, crying obsidian and gold are expensive; the portal-energy accent is
amethyst clusters (cheap, light 5) and two soul lanterns - the one cold light in a lowland of 122
warm ones. The ruin follows the void tower's rule: regular coursework, ONE broken arc
(upper-north, balancing the bat rock hanging upper-right from the pond view), the crown keystone
surviving, the fallen piece ONE half-buried chunk. Emission is air-only (the courthall rule), so
the bottom arc terminates against the terrain and burial costs zero overlap and zero dig.

**The axolotl won on the planar/columnar rule, not on taste.** Jack offered otter or beaver "etc";
an otter's identity is a pose needing water it cannot legally occupy, a beaver is a rodent barrel
four blocks from a fifty-block rodent, and an axolotl is all hardware - six flat gill fronds, a
tail fin, a wide flat head, splayed limbs, the gecko category - plus it is THE lush-caves mob, so
the naming test is instant. Size came from the gills: a frond needs ~4x2 cells to read as a frill
(the ladybird spot-spacing lesson), three per side need a head ~8 wide, so total length 26. It is
half the capybara and does not dwarf its own pond. Pale leucistic on purpose - the flamingo owns
saturated pink, and the two must not twin across the water. Not one water cell is replaced: the
snout and gills OVERHANG the shallows, belly clamped a course above any wet column.

**The heron is retired, Jack's call: one of heron/capybara, not both.** The capybara stayed - the
flamingo already holds the wading-bird slot and a second bird on the same skeleton in grey was
the redundant one. Retiring it also frees the pond's west bank, which is the main vantage toward
the ring. Never built (zero wool below Y70 in the capture), so nothing is orphaned.

**The massif moved the ground under the scene, and the fixes are worth keeping:**

- **`finish.trim_buried`** (new, opt-in): design cells the terrain already owns are dropped at
  the seam. A cell inside a ground rise can never be placed (a printer places into air), would be
  invisible if it were, and stands as permanent amber in `/cscan check` - the Court Hall's
  unbuildable-cells problem, solved at the seam for designs where terrain wins by intent.
  Same-state cells stay: they are built progress. Capybara yielded 9 cells, flamingo 7.
- **The flamingo stands on a measured knoll now** - (-24165, 29988), a single-column local max at
  42 with neighbours 40-41, so the foot grips and everything drooping a course below the feet
  clears every rise. On rolling ground the foot column must BE the local max, or the plumage digs.
- **The capybara runs at feet 41** - its low cells sat level with the risen massif's top course.
  A mid-gallop animal with a foot or two airborne is the pose, not a floating statue. (The
  quadruped seats its own vertical by probing `under`; `feet[1]` does not move it.)

**Five traps inside the two generators, each of which shipped a clean audit and a wrong build:**

- **The spine walked INTO the gaze.** Stations stepped toward `look_at`, so the body extended
  through the nose and the animal faced away from its own pond. t=0 is the nose; the walk goes
  tail-ward, opposite the heading.
- **Gill fronds rooted at the spine spent themselves inside the skull** - nine red cells reached
  the air. Root anything that fans off a body at the BUILT SURFACE and run its whole length
  outward.
- **The fin floated.** Its base was computed from the float the sections were sampled from; the
  rounded cells drift a course away. It rides `top_at` - the highest cell each column actually
  placed - which is the detached-ossicone rule applied to arithmetic.
- **A tree canopy severed the flank.** Cells placed through gaps in oak leaves belong to the tree,
  not the animal. The site was moved clear of the measured canopy (X-24210..-24206 / Z29981..85),
  and `_prune_severed` now guarantees one component whatever the foliage does.
- **The fallen chunk sheared into three on ground steps.** A rigid fallen arc BRIDGES a dip: each
  column is seated on its own real ground and rises to meet the tallest of its face-neighbours -
  built UP on the low side, because downward filler on the high side lands inside that column's
  own terrain and is silently skipped.

**Panel verdicts, recorded (2026-08-21).** First pass: both panels passed with two criticisms -
far-side gills sparse in plan, and the white dorsal fin reading as a mohawk. Jack said the
axolotl needed work, and both criticisms were the work. **v2, same day:** the fin is MAGENTA -
the Minecraft mob's own tail-membrane colour, and the general rule is that a fin is darker than
the body, never a highlight; the gills went from 38 accent cells to ~140 (length 6.5, vertical
frill, three stitched FILAMENT barbs per frond - barbs are what turn three red sticks into a
frill); the head got a real neck pinch (skull as wide as the body, 0.46W, pinched to 0.36W
behind the gills - without it the animal read as a worm with a face); and the muzzle carries a
7-cell magenta SMILE seam below the eyes, which is half of what names an axolotl and no gill
work substitutes for. The rework pulled the nose a cell back from the waterline - the overhang
test caught it (2 cells over water against a floor of 3) and the site nudged one block pondward.
v2 silhouette breaks at the gill crown, which the first one never did.

**The face took three more passes, and the lesson is about the GRID, not the face.** Jack: "head
on it looks like a blob." The head was flat-topped and correctly shaped - and aimed 40 degrees
off the block grid, so its "flat" face was a diagonal staircase of corners in game: eyes at
different depths, the smile stepping cell by cell. **An orthographic render along the body axis
cannot show this failure** - projecting along the diagonal de-jags it by construction, which is
why every sheet looked right while the game looked wrong. The fix is the classic builder rule,
now in the generator: **the gaze is CARDINAL and the head is straight; all of the body's curve
lives in the tail** (`_spine` ramps curvature from zero through t=0.28). Three more findings from
the passes:

- **The skull section is exponent 6, not 8** - flat across the middle, ONE step down at the
  cheeks. 8 was a slab; "a little more rounded" was the correct review.
- **The face is the full-width plane and the mouth sits ON the chin line.** A two-step nose
  chamfer left a narrow protruding muzzle that the smile filled edge to edge - a magenta blob
  where a face should be - and a mouth at mid-height reads as a nose.
- **The eye bead is the FRONTMOST body cell of its cheek band**, so by construction nothing can
  stand in front of it. Chosen by proximity instead, the tail's curve shifts the centroid, the
  head line drifts half a block south, and one bead landed a cell deep - painted over by its own
  pale ring from exactly the head-on view. Both eyes now read head-on AND from the plan.

Cross-design overlap 0 across all six lowland pieces; nearest approach is the capybara sprinting
4.2 blocks past the gate's pavement, which is the story anyway. `tests/test_ruinring.py` (10) and
`tests/test_axolotl.py` (9) pin the geometry, the break, the seam rule, the anchors, both-sided
gills, dry feet, the wet nose, and the pale eye ring. Tracked: `sync.yaml` progress carries both;
`designs.json` now lists 25.

## The ruins quarter, and the world as master copy (2026-08-21, 19:28 scan)

The scan review found the ring 89% standing, the ground ~95%, the pond broken to real water -
and **the axolotl standing on the pond's WEST bank, rotated 180**, where the design said
north-east. Jack placed it where he wanted it, which is a design decision made in-world, and the
response that works is the one taken for the deck floor's as-found state: **the world is the
master copy.** The placement transform was recovered off the two eye beads (rotation 2x90,
translation solved by matching), and `Lowland Axolotl` was re-derived from the capture itself -
975 cells, as built, 100% clean by construction. The config keeps the design record under an
AS-BUILT header; regenerating it would fight the placed copy cell by cell, forever.

**The same scan moved the ground under the ring, and the seat drifted.** The ring's vertical
seat derives from min-ground; Jack's moss-building raised that by one, and a regen emitted every
remaining cell one course off the standing masonry. `base_y` now pins the seat - and the pin was
taken WRONG once before it was taken right: 44 from the drifted derivation, then 43 read off the
standing crown (proud keystone at Y68 = seat + D/2 + 13). **A pin must come from the world, not
from the code that drifted.** The ruinring tests hit the snapshot trap too - pinning the full
circle against a design whose nature is remaining-work - and now judge what STANDS (design plus
capture masonry) for geometry, the design alone for the seam rule.

**`Lowland Ruinway`** (gen/ruinway.py, 224 blocks, 0 problems, 0 overlap, 0 expensive): the rest
of the ruin complex, one hand with the ring. Ruined pavement from the pond's SE bank THROUGH the
gate to a broken overlook at the rim's true edge (ground ends at X-24151, measured after this
file's own -1-is-truthy bug bit the rim scan a second time). Fragments, each a PART of a
building: a gatehouse whose door outlived its walls, a four-pier colonnade on the overlook
approach, a bridge stub whose last two rows hang over open water, an apse half-ring with one
amethyst bloom in the NORTH skylight - the second beam of daylight gets its own ruin so the two
shafts answer each other. Soul lanterns on wall posts light the way cold.

Three measured facts the quarter is built on:

- **The way crosses UNDER the sprinting capybara.** Its only low cells are the two diagonal leg
  pairs (z30014-18 and z30022-26); the corridor between them at z30019-21 is clear below Y47 the
  whole way across, and `test_the_walk_under_the_capybara_stays_clear` keeps it that way.
- **The pavement decays with distance from the ring** (gap hash grows per block), stairs are
  never gapped (a missing tread breaks the walk; a missing flag is moss showing through), and
  every riser faces its ascent per the stair convention.
- **The pond's SE finger was misread once**: "water reaches east to X" is water's EASTMOST
  column, not its extent - the first bridge siting put the whole deck on dry land and the test
  caught it. The deck is level (a bridge does not conform to ground - that is the reason to
  build one), and its broken end is staggered, not sheared.

Generation order matters and is stated: portal first, ruinway defers to it (21 shared threshold
cells). `designs.json` tracks 26.

**The visual audit of the quarter (2026-08-21), and the scale rule it produced.** Rendered from
every angle a player gets - west-bank money view, landing approach, close-ups of all five
fragments, whole-scene elevations. What passed unchanged: the plan composition, the path craft,
the overlook (a parapet is SUPPOSED to be low - its drama is the void), the bridge stub. What
failed: the gatehouse read as a dark blob beside the path, and the apse was shin-height in
elevation - a mound with a purple dot. Three findings worth keeping:

- **On this moss, under ten-tall trees, architecture below ~6 courses dissolves into ground
  noise.** The fern-and-azalea surface roll eats anything shorter; the bat tower (15), the ring
  (25) and the trees set the register. Fragments were raised to clear it: gate frame to 8, apse
  crest to 6, tall colonnade piers to 6.
- **The ruin is the WALL, never the DOORWAY.** The first gatehouse broke its lintel - damage,
  not architecture. Inverted: a COMPLETE post-and-lintel frame stands alone in the moss, and
  the decay is carried by wall stubs falling to nothing off both sides. The doorway whole, the
  building gone - that is the void tower's rule said forward.
- **A linear height profile peaks on a single column.** The apse's crest read as a stick because
  full height existed only at angle zero; the profile now holds full height across the whole
  back third before decaying. A wall crest is a LINE, not a point.

**And then Jack rejected the quarter's shape itself: "very sparse and vague... too fragmented,
we need at least one more complete actual structure - something that feels real and like it was
once impressive."** He was right - fragments without a mass read as set-dressing. The answer is
**`Lowland Sanctum`** (gen/sanctum.py, 788 blocks, 0 problems, 0 overlap): a basilica-form
ruin in the north skylight - the ONLY zone that can hold a real footprint (a 14x22 pad search
over the whole lowland returned ZERO with everything reserved), and only after the ruinway's
apse fragment yielded its ground, which is the coherent trade: the fragment became the
surviving back wall of the building it was always a fragment of (`apse: null` in the ruinway
config records it).

- **The footprint threads the blocker map**: walls at X-24191/-24181, BETWEEN the ground
  design's lantern columns (X-24192, X-24184) - the ground's own lights are dodged, never
  covered, and the two inside the nave stay standing in the ruin floor. The apse backs onto
  the void breach north of z29964; the roofless nave sits inside the daylight beam.
- **Once-impressive is a CONTRACT, and it is pinned** (`test_sanctum.py`): the facade survives
  whole - open doorway, chiseled jambs, an oculus ringed in chiseled over the lintel, stepped
  pediment to FY+11 - the apse holds a full crest LINE, the SIDE WALLS are the part that fell
  (high at both ends, a course or two mid-run, their tumble in one heap per side), the
  stylobate is one level plane, and a pavement spur joins the way at the gatehouse. Through
  the open door you see the amethyst bloom on the altar - unplanned, and kept.
- **`floor_y` is pinned in the config** for the ring's reason: a seat re-derived from a ground
  that is itself being built drifts a course between placement and regen.

Build order for the printer is now: portal remainder, ruinway, sanctum (each defers to the
ones before it). `designs.json` tracks 27.

**The pond end was wrong and Jack named it exactly (2026-08-21): "the gate and fishing path...
needs to be done differently."** The first ensemble was a door to nowhere and a jetty from
nowhere - the bridge stub genuinely read as a fishing jetty. The fix was to commit to what the
pond IS in this story: **the harbor**. The bridge is gone (`bridge: null` records why); the
pond's SE shore turned out to be a clean diagonal of dry edge columns at exact water level
(measured, not drawn), and the QUAY's dressed lip follows that line - the bank is the water's
own line, never a hand-drawn box. Mooring posts stand on the lip, one carrying the cold light;
two lip cells are landing steps whose flight ascends LANDWARD, because you climb them out of a
boat - the stair convention applied to a shoreline. The gatehouse relocated to mid-arc as the
WATERGATE, its opening facing the landing, and the way now BEGINS at the water: boat - steps -
gate - under the capybara - ring - colonnade - overlook. A path is real when both of its ends
are places.

## The lowland town (2026-08-22, 15:01 scan)

Jack's direction, verbatim intent: no flamingo, "more buildings or architecture", animals
incorporated around them. The audit that preceded it: ground 90%, ruinway 89%, sanctum 89%,
bridge 92%, axolotl 100%, portal remainder 0% - the quarter nearly done, and the two unbuilt
animals the only large claims left on the floor.

**Both mammal-scene animals are RETIRED in their configs** (flamingo, capybara flee - 0 of
7,618 and 0 of 6,813 cells built, so nothing orphaned). Retiring them freed the NE quadrant
and the central strip, and the pad search over the new scan found what fits. Four designs, all
0 problems in context, 0 overlap, generated after the quarter so `defer_to` holds:

| design | blocks | what it is |
|---|---|---|
| `Lowland Hamlet` | 439 | three houses SW of the ring: whole (roof, chimney, cold hearth), roofless, fallen-to-its-doorframe |
| `Lowland Campanile` | 575 | the sanctum's bell tower at (-24197, 29974), Y41-59; a real `bell` (cheap, 1.19) in the belfry; the owl on the SW merlon |
| `Lowland Harbor Light` | 167 | beacon at the quay ROOT (-24204, 30018) - the lip is a 1-3 wide diagonal ribbon, no tower stands on it |
| `Lowland Turtle` | 145 | basking on the N shore at (-24194, 29993), nose one dry cell short of the measured waterline |

**THE LANTERN GRID IS THE STREET PLAN.** The ground design's 9-grid lanterns land at
X{-24192,-24183,-24174} x Z{30033,30042} in the hamlet pad; the gaps between columns are 8
wide and a 7-wide house fits exactly, so the ground's own lights become the street lamps. The
grid columns are a FORBID set asserted at build time - and the first lane was paved straight
through its own lamp row, which is why `_lane` checks it too.

**The turtle is the ladybird's category** (pattern on one convex dome, canonical view the
plan), sited by per-row waterline measurement: dry to X-24203 at z29993 but only to X-24201
one row south - the first site put the nose in the pond. Shell brown_wool/black_wool seams
(full hue flip off the moss, measured; a green turtle vanishes on a green floor), skin
oak_planks. Flippers are ROOTED at the shell edge and placed at ONE level per pad - at their
own ground they came off as four separate components, and on a ground step a two-course pad
splits diagonally.

Traps this session, each of which shipped a clean audit and a wrong build first:

- **A lamp under a slab cap reads "hanging from air"** in the audit, in context too. The cell
  a lantern hangs from is a FULL block; the slab ring keeps the lightroom's silhouette.
- **The owl floated over the shaft.** The parapet ring covers two of its body's four cells;
  the other two hang over the hollow interior. Anything perched on a built edge needs its
  seat placed under the WHOLE footprint, not probed at one corner.
- **The campanile's tumble perched on the sanctum's wall top at Y49** - `_surface` reads any
  standing masonry as footing, and the neighbour is three cells away. Fallen blocks land
  only where `g <= FY + 1`.
- **Blackstone cannot draw value lines on itself**: the family sits within 12 RGB (measured),
  so the cracked/chiseled trick that failed on stone brick fails here too. The tower's lines
  are GEOMETRY - proud string courses, corbel, crenellation gaps - not tone.
- **Pane connections are game-derived and `work.INTENTIONAL` rightly drops them**; the
  north/south=true on the campanile's slits exists for the RENDER. A test that greps
  work.json for them is testing the wrong artifact.

**The world was adopted as master copy twice**: the ground's 1,416 deviations (Jack's massif
rework - dripstone->cobble x1269 - plus lanterns and the axolotl's footprint) and the bat's
263 (dark oak -> planks/wool substitutions) were merged into the design litematics from the
capture, mechanisms excluded. Both now diff 0 deviations; ground 94%, bat 95%.
`out/island_full.litematic` is the full-depth capture the town generates against.

`tests/test_lowland_town.py` (17) pins the contracts: no cell in a lantern column, every
door frame whole with its lintel BETWEEN jamb tops (jambs three high, or the lintel floats
over the opening), the roofed/roofless split, crenellations actually crenellated, the shear
taking NE and leaving SW, the bell on a real ceiling, the owl seated with its eyes leading,
the pond keeping every cell it owns, one-piece turtle, dry-but-near-water, plan-legible shell.

**Still open:** the quarter's remainder is ~220 cells (portal 114, sanctum 70, ruinway 23,
bridge 3) - one `follow` session; the ground's last 10% is west-side scatter plus 137
water-occupied cells; the ground's two unbuilt trees near the campanile (X-24200/29967,
X-24208/29983) clear its footprint by 2-3 and were left in.

## The descent: the spiral continues to the lowland (2026-08-22)

Jack: the spiral staircase continues going down all the way to the lowlands. Two designs:
**`Lowland Root`** (494 - a slim oak braid off the shop islet's SOUTH rim, gripping the
measured one-thick shelf at (-24208..-24207, 30025), toes in the moss at Y41) and
**`Lowland Stair`** (2,192 - the same slab-helix idiom as the Root Stair, wound about it,
Y41-151, ~9 turns, 44 rail lanterns, ONE component, 0 overlap, all cheap). The full walk is
now: deck - workshop stair - root stair - islet shelf - LOWLAND STAIR - harbor moss, then
quay/watergate/way or east to the hamlet.

**The axis is the siting decision, and it was moved twice by measurement.** Concentric with
the taproot's keel at (-24200, 30018), the landing wraps the watergate, the quay lip and the
harbor light; under the south rim at (-24207, 30029) it clears the light's gallery by 9.5,
the quay tip by 13 and the watergate by 17, and the landing arc falls on open moss
(ground histogram Y37-43, 2 wet columns). NOT ONE of the harbor ensemble moved.

Traps, each of which shipped a clean-looking build first:

- **`_smooth` is a running MAX, so one wide feature anywhere in the wrapped design widens
  every course above it.** The root's two-cell toes carried r5.25 up the whole helix and
  parked the outer band on the harbor light's gallery; the grip bend did the same to the top
  and flared the stair past its own step-off. Toes are one cell now, and `spiral.max_inner`
  exists - a clamp on the smoothed profile, with defer_to settling the few cells where the
  core then crosses the band.
- **A twisted strand disconnects at every sideways step** - the join is diagonal-only, the
  ear-tip lesson again. The first braid was 26 components; each step now places a bulge cell
  in the previous course's column, which is also what a real root looks like.
- **The top courses terminate against the shop islet's DESIGNED rock** (its rim skirt,
  ~340 unbuilt cells in the band - burial against a design, not just terrain). So the
  isolated climb gate cannot pass BY CONSTRUCTION and is off in the config; what replaces it
  is the COMPOSITE walk - stair + islet design + capture, the audit's own step rules - pinned
  in `tests/test_lowland_stair.py` (6). `start_angle` was swept over 63 phases SCORING THAT
  WALK: at 1.1 the top courses ride the open south air and reach the shelf at exactly 151.0.
  Build order follows: the stair's top ~29 cells wait for the islet's rim.

**The Void Ladybird was re-sited** - its parked pocket held 726 cells inside the new shaft
(never built, so nothing orphaned). The distance search re-ran with the stair, root and town
reserved: the new pocket at root (-24238, 63, 29968) keeps 8 clear on every face, belly
overhead, the NW lowland floor twenty below.

**THE ALIGNMENT (same day, Jack's second review): "it doesnt align with the actual stairs -
it should be a straight down, we can break blocks on the floor etc."** He is right and the
offset siting is gone: the stair now screws straight down the taproot's own axis at
(-24200, 30018) - the Root Stair's centre, same spin, one screw deck to floor - through a
WELL dug in the shop islet's lens (121 dig cells, Y144-150, in the sidecar's dig list;
`/cscan dig` shows them). What made that safe to build:

- **`spiral.dig_above` + `dig_only`**: at or above dig_above a tread may claim a world cell
  (the cell and its headroom go on the dig list - the rimstair's "the tread cell is itself a
  dig"); below it nothing is ever dug, so the lowland's watergate, quay and ground thread the
  stair as before. `dig_only` names NATURAL ROCK - the first well rule was "anything
  unprotected", and the old stair's own slabs sit directly over the mouth courses: it would
  have dug the stair it exists to continue. And a dig may never take a protected block OR THE
  CELL ONE STANDS ON - the shop's barrels are one course over the well's north arc.
- **The harbor light is RETIRED** (Jack: "we arent gonna build the harbor light"). It stood
  four blocks inside the new annulus; the west-bank re-site happened and then the whole
  design was retired unbuilt - the stair took its site and most of its job, and the quay
  keeps its cold mooring-post light. Config kept as a record.
- **The Shop Islet design is CARVED to the well** - 287 lens-fill cells removed over the
  stair's tread+headroom envelope (noted in its config; regenerating the islet re-fills the
  well and must be followed by re-carving - `test_the_carved_islet_keeps_out_of_the_well`
  is the tripwire). trim_buried is OFF on the stair on purpose: it strips capture-owned
  cells and would eat the well's own treads; the generator self-trims below dig_above.
- **The composite walk sweep found the top the same way as before** (63 phases): at 6.1 the
  walk runs lowland moss to the islet shelf at 151.0 through the dug well, 572 landing
  cells. The old stair's landing is a short walk across the islet top from the well mouth.
  `tests/test_lowland_stair.py` (12) pins the axis equality with root_stair.yaml, the dig
  contract, replaces-nothing-outside-its-dig, and never-dig-the-old-stair.

**THE CAREFUL AUDIT (same day, Jack: "audit it all carefully now, make sure its perfect").**
Every design regenerated with full output read, plus a scripted battery: pairwise overlap
across all 33 tracked designs, dig-versus-every-design, shipped-file hashes, config
references, ladybird clearance, per-cell support. Five real defects, all fixed:

- **The islet's underside fill claimed the root's anchor cell** (-24200,141,30018), and the
  defer dropped it - leaving all 180 root cells with nothing to place against. A design can
  orphan another design's ANCHOR: check what a defer takes, not just how many. The root wins
  its anchor now; the islet is carved around it.
- **The well dug 21 cells of the Atelier Court's floor.** `dig_only` names materials, and
  stone brick is both "natural rock" and somebody's workshop floor - a dig must know what
  the rock BELONGS to. `spiral.dig_forbid` takes design paths whose cells may never be dug;
  the phase re-swept to 5.4 (zero atelier contact, still walks, 105 dig cells).
- **A deferred cell abandoned its dependants**: a rail wall whose tread went to another
  design shipped standing on air, then a SECOND wall orphaned by cascade. `_defer_to` now
  drops lanterns/torches/walls left with no neighbour, and a post-defer fixpoint sweep
  (`_drop_defer_orphans`) removes any cell with no design neighbour and no world contact.
- **A tread whose only contact was rock its own dig removes** is unbuildable by
  construction - dig first, then nothing to place against. The spiral prunes those to a
  fixpoint, and a pruned tread takes its dig entries with it.
- **A hamlet roof-overhang cell floated** where the weather hash removed its inner
  neighbour: overhangs are placed in a second pass, support-checked against the body.

Also found and left alone, stated: pre-existing overlaps among the OLD designs (Atelier x
Shop Islet 170 cells, 142 same-state; Statue Footings x Rim Hem 7; Void Giraffe x Void Isle
13) and out/-vs-schematics drift on ~8 old designs whose out/ copies were regenerated by
daily syncs but never re-shipped - not this session's work, worth a pass of its own someday.
Final state: 0 problems and 0 overlap in context on every session design, dig touches no
design's cells, zero free-floating cells, all 5,502 lowland-job blocks cheap-or-ok and 1.19.

**The gradient, and the root's honest length (same day, Jack's review).** The stair now
changes stone as it changes world - dithered thirds, measured luminance 122 -> 71 -> 48:
island stone brick at the shelf, deepslate through the twilight, the quarter's blackstone to
the ground - and the light goes cold with it, 28 warm lanterns above, 16 soul lanterns
below. `spiral.bands` is the mechanism (per-cell hash dither over band_blend courses - a
hard line across a helix reads as two stairs stacked); bands=None keeps the Root Stair
bit-identical. And the root no longer runs to the ground: Jack called the full-height root
wrong, and it now thins out inside the deepslate band (tip Y95, 225 blocks against 494) -
the island's reach ends where the underworld's masonry begins, and the helix hangs alone
below the tip. Two things that follow: `min_radius` is PINNED to `max_inner` (below the tip
the profile is empty, and an unpinned floor snaps the ribbon 4.5 -> 3.0 in one course), and
the start_angle had to be RE-SWEPT - a slimmer core changes the pitch, so the phase moves
with the profile; 4.0 reaches the shelf at 151.0 with the widest landing. The design-alone
component count splits at the top weave where trim_buried yields cells to the islet's BUILT
rim rock - connected in the world, cosmetic in isolation; the composite walk is the truth
and is the test.

## Build & test

```bash
python -m pytest -q                                   # 456 tests, keep green
cd chunkscan && ./gradlew build test -q                # 384 tests; writes build/libs/chunkscan-<ver>.jar
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

### The recovery ladder: what to do when it is genuinely impossible (2026-08-21)

Jack: *"theres going to be times where its literally impossible to reach and it causes an infinite
loop, e.g. if its in the center of many layers because we built the wrong way in."*

Every stuck loop before this was fixed by understanding ONE situation — the shaft, the ceiling, the
unloaded chunk, the wall the route thought was clear. **That approach has a floor under it.** There
will always be a situation nobody thought of, and no amount of cleverness about flying reaches a cell
in the middle of a solid mass. So the last resort is not another special case; it is a ladder, and
the only thing it knows is how long things have been going badly.

    5s    BACK_OFF     fly to a breadcrumb — somewhere we were definitely open
    10s   CLIMB_OUT    abandon the destination, rise into open sky
    20s   GO_HOME      /is

`Recovery.stageFor` is pure and `RecoveryTest` argues with the order rather than the behaviour. Three
things about it are load-bearing:

- **Trouble is defined by MOVEMENT, not by cause.** The specific handlers upstream have already had
  their turn; if the flight is still not covering ground after all of them, the reason has stopped
  mattering. A flight that is moving is fine whatever else is true of it.
- **Each rung gets long enough to work** before the next interrupts it. Backing off and climbing out
  are several seconds of flying each.
- **SEALED is a shortcut, not a rung.** `Nav.pocket` counts reachable cells up to a cap: fewer than
  60 and you are in a hole rather than a room. Backing off, climbing and going round are all about
  getting somewhere else IN THIS WORLD, and when you have been built into something there is nowhere
  else to get to — so it goes straight to `/is`.

**The boundary matters as much as the detection.** The loop works indoors — the store hall is nine by
nine — and a recovery that teleported you home every time you flew into a building would be worse
than no recovery. `aROOMIsNotAPocket` pins it, and the first version of the sealed test WAS a room,
which is how the threshold got chosen honestly.

#### And the slow version of the same loop

No watchdog catches this one, because every individual decision in it is correct: abandon spot A,
take B, abandon B, take A again once its minute expires, for ever. `Loop.thrashing` looks at the PAIR
— several spots given up on, and NOTHING placed while it happened. Either alone is normal; a design
has awkward corners and a slow printer is still a printer.

Four abandonments with nothing built and the design is not buildable from here right now: it moves to
the next design under `follow all`, or stops and says which commands would explain why. **A loop that
runs all night achieving nothing is worse than one that stops at 2am and says so.**

### Two strikes and a place is ignored (2026-08-21)

Jack: *"it shouldnt spam no route and no way around, if it does it twice, just find a new location,
it should notice if an area gets flagged twice it gets flagged as an ignore (red)."*

**The spam and the infinite loop are one fault seen from two angles.** Every watchdog in this loop is
a TIMER — the spot avoid expires after a minute, the station retries clear when every bin has been
tried, a chest's cooling-off lapses — and a timer forgets, which is right for a world that changes and
wrong for a place that has beaten the router twice. Returning there for ever is what produced both
the repeated message and the cycle.

- **One failure is a bad moment**: a chunk that had not arrived, a block the printer had just placed,
  a route computed from the wrong side of a wall. Writing a place off for that shrinks the island for
  no reason.
- **Two is a property of the place.** It goes on the list, is drawn RED, and is never chosen again
  this session — not avoided for a minute, not retried when the list is cleared, not on the table.
- **Announced exactly once**, because `strike` returns true only on the strike that writes it off.

**Held by AREA, not by coordinate.** The loop aims at a centroid that drifts as cells are placed, so a
per-cell list would never see the same failure twice — it would collect near-misses for ever and
ignore nothing. Eight blocks is about the size of a spot the flight can fail to reach for one reason.

**Session-scoped, and deliberately not written to disk.** Breaking one block can change the answer,
and a file would quietly shrink the buildable island over weeks with nothing to say why.
`/cscan ignore` lists and re-draws them, `/cscan ignore clear` puts them back on the table, and
`/cscan why` says how many there are — because a loop that silently stops trying somewhere is a loop
you cannot argue with.

Both the flight and the loop feed the same list: a route that cannot be found and a spot that has been
given up on are the same evidence about the same place.

## The lowland glow: lighting solved by propagation (2026-08-22)

Jack: find a way to add more light in smart ways; everything as built is final, mismatches
accepted. The audit PROPAGATED block light through the assumed-final composite (capture +
every tracked design, standing water never displaced) - the court hall's freeze-guard
method, scene-wide - and classified the walking surface. What it found reframed the job:

- **The floor was never the problem.** 250 spawnable columns out of 6,321 - the ground's
  lantern grid plus 39 ochre froglights JACK HAD ALREADY SCATTERED (his own lighting idiom,
  measured at one per ~15 blocks) carry the open moss. 92 of the ground design's 212
  lanterns are lost to accepted mismatches; the froglights are what replaced them.
- **The dark was ON TOP of things**: the axolotl's back (90 wool cells), the ring's crown,
  the sanctum's crests, the campanile's deck and its owl's head, house A's roof, tree
  canopies, four stair treads mid-gap between rail lanterns. Light placed at eye level
  never reaches a crown, and a spawnable crown puts a zombie on the portal at night.
- **The pond's lighting was never coming**: the ground design planned a FROZEN pond -
  1,007 ice with 92 lanterns under it - and Jack built the open-water harbor instead.
  Dead letters, all of it, and the harbor sat dark.
- **~3,700 columns hide dark buried seams UNDER the massif fill** - real spawn spaces,
  sealed, unlightable from outside. Reported, out of scope: a mob-cap leak for another day.

**`Lowland Glow`** (gen/lowglow.py, 29 blocks, 0 problems and 0 overlap in an 8-capture
context): the solver placed story fixtures first, then greedily covered - the right tool
per surface, full re-propagation each round - until ZERO spawnable surface cells remained.
The per-surface rules are the design: froglight flush in turf (dig the turf cell - Jack's
idiom continued), soul flames on ruin crests (light 10 covers what five amethysts cannot;
they trace the crest strip behind the ring), glow lichen face-down on canopies and the
AXOLOTL'S BACK (a lush cave grows light on what stands still; nothing else ever lands on
an animal), sea pickles in the harbor shallows (the water lights itself), one warm chimney
lamp on house A, one soul lantern HUNG in the watergate arch, one on the campanile crown
beside the owl, one on a stair rail post. `tests/test_lowland_glow.py` re-runs the
propagation over the finished composite and asserts the zero - the test, not a player at
night, is what finds a regression.

Traps, all of which produced a wrong number or a broken build before the right one:

- **The lowest-standable classifier struck a THIRD time**: it graded buried seams and
  called 72% of the floor dark; the true surface (topmost standable) was 4% dark.
- **A config key named `on` does not exist**: YAML 1.1 parses on/off/yes/no as BOOLEANS
  and the key silently vanished. It is `footing` now.
- **The fixture overlay defers to nobody, deliberately**: the ground design's litematic
  holds ALL its cells, built included, so defer_to dropped fixtures standing over built
  turf - and the new deferral-orphan sweep then ate the cross-design-supported lamps. A
  solved overlay contests no live work; its config says so instead of deferring.
- **Overlaying the dead ice into the test's composite shadowed the axolotl's fin** into a
  false dark - ice is opaque, the pond is water, mismatches are accepted BOTH ways.
- **`waterlogged` is not in work.INTENTIONAL**, so a test that greps work.json for it
  tests the wrong artifact (the pane lesson, again). The water at the position is the
  assertion.

### The world moved mid-session, and what it broke (2026-08-23, 14:32 scan)

Jack rescanned while the glow was being solved: the town is BUILT (hamlet 97%, campanile
93%, turtle 96%, root 100%, stair 74%), and three things broke at once, each instructive:

- **The belly's vines hung from TRIPWIRE.** Jack strung string lines under the plate; the
  vine walk skipped those cells (tripwire is rightly not solid) and kept emitting BELOW
  them - orphan strands in context. `_already_built` now returns an OCCUPIED mask too, and
  a strand stops at any world-occupied cell it cannot claim. Same family as vine-as-footing
  and -1-is-truthy: "not solid enough to cling to" does not mean "not there".
- **The town tests hit the snapshot trap at scene scale**: they regenerated designs against
  the fresh capture, and remaining-work regen strips every built cell - the door-frame test
  failed because the door frame is BUILT. Fixtures read the SHIPPED litematics now (the
  full intent, what the printer places), the ruinring tests' lesson generalised.
- **Jack substituted a neighbouring band's slab on 22 stair cells** - accepted mismatch on
  his own stair, which the replaces-nothing contract must not read as a collision. The
  stair's own material family is exempt.

`out/island_full.litematic` and `island_deep` are re-cut from the newest scan; the glow
re-validated against it (every fixture still stands, the propagation zero still holds).

## All designs accepted as complete (2026-08-23, 15:54 scan)

**Jack's call, wholesale: every tracked design is COMPLETE AS IT STANDS in the world.** The
world is the master copy applied all at once - whatever a design still listed as remaining
work is no longer wanted. From here the island takes NEW projects only; nothing old is live.

What changed in the repo:

- **`sync.yaml`: `regen: []` and `progress: []`**, both deliberate. Regen off means the
  ground designs stop re-emitting remainders - and stop re-planting the vines Jack removed
  by hand (32,369 of them between the Aug 21 and Aug 23 scans; the purge is his, and the
  designs were fighting it). Progress empty means `designs.json` says "you track nothing":
  the mod places, plans and follows nothing, and bare `/cscan place` still refuses the
  61-design folder sweep. A new project resumes tracking by being added back to the lists.
- **Litematics, sidecars, configs and work.json files are untouched** - they stay as the
  record of what was designed, exactly as retired designs always have.
- `tests/test_tracked.py` now derives its expectations from the cfg (empty is a legal,
  deliberate state); the name-stripping property runs on a synthetic cfg so it stays tested.
- `test_lowland_glow.py::test_zero_spawnable_surface_cells` is SKIPPED with the reason in
  the marker: the glow (0 of 29 fixtures ever placed) is closed, and the world then moved
  past its solution - the 15:54 scan removed the 40 drowned pond lanterns
  (`lantern->water:40`) and re-lit 28 elsewhere, which opens **15 spawnable cells on the
  axolotl's back at Y43-45** that the solved fixtures never covered. That gap is ACCEPTED.
  A night-pass re-solve against the as-accepted world is a new project if Jack wants one,
  with its own design and its own test.

Final standing state at acceptance (full-depth 15:54 capture, 110,551 blocks, 56/56 chunks):
Root Stair, Lowland Root, Lowland Axolotl 100% - Hamlet 97% - Atelier Court, Turtle 96% -
Campanile 93% - Castle Bridge, Deck Vault 92% - Void Isle, Ruinway, Sanctum 89% - Taproot
84% - Court Stair 82% - Belly 79% - Lowland Stair 74% - Court Hall 65% - Shop Islet 44% -
Entry Hall 41% - and never started: Lowland Portal (114), Lowland Glow (29), Undercroft
Store (77), Shed Shard (198), Chimneys (10), plus the plate dressing remainders (paths 69,
hem 149, light posts 36, bird lanterns 59, footings 49, ride lights 17, apiary 12,
entrance 5). All of it accepted; none of it owed.

Questions this closes, so nobody reopens them by accident:

- **The Void Giraffe record mismatch is moot.** The giraffe stands complete (~4,120 cells,
  material budget matching the design) 6 blocks south of the design's recorded origin, with
  coat differences beyond a rigid shift - the record was stale, and untracked it can no
  longer misdirect a build loop. If it is ever re-tracked, adopt as-built first.
- **Court Hall's 58-cell replace question**: closed, the stone brick stays.
- **Entry Hall's 40 deviations**: closed, they were Jack's substitutions.
- **The chest move**: was already done - 86 chests in the Store Hall, 21 with machines,
  16 elsewhere (12 of those a deliberate ring on the east lobe at Y200).
- **The sync-below-Y150 blindness** (history and shop read the Y150+ cut, so every lowland
  design reported 0 forever and velocity was ~4x off) is now inert with tracking empty,
  but still latent: give sync a full-depth world before tracking any below-plate project.

## The Falls, and the Island Night (2026-08-23) — the two new projects

Jack, after the acceptance: *"Do Falls, night pass"*. Both are designed against the 15:54
scan, both are tracked in `sync.yaml`, and they are the only live work on the island.

| design | blocks | dig | what it is |
|---|---|---|---|
| `Falls` | 30 | 41 | the channel that lets the isle's cistern spill to the lowland |
| `Island Night` | 105 | 30 | every walkable surface on the island taken to zero spawnable cells |

### The Falls: the phenomenon was already there and it was an accident

The plate's pond drains through a surface stream along X-24209 at Y203, steps to Y202 at
Z29992, and at Z29991 runs out of island — **one column of water falling 107 courses**, Y202
to Y96, landing in the void isle's pond. It is the only long fall on the island and nothing
about it read as intended: no lip, no basin, no outlet, water leaving over moss.

So the design **builds nothing that falls. It builds the things that let water fall** — which
is why 30 blocks and 41 dug cells buy an element that crosses all three levels. The chain is
now plate pond → stream → dressed head → 107-course fall → the isle's pond → a cut channel →
a notch → **a second fall of ~60 courses into the lowland harbor at Y37**. The lowland's water
now arrives from the island above it rather than simply being there, and the descent walks
beside it.

**Four measurements decided the site, none of them guessable:**

- The isle's pond is **fully enclosed** — 132 cells at Y99 and not one edge cell has a clear
  drop beneath it. There is nowhere it spills by itself; it has to be cut.
- The isle's south rim is a thin **shelf**: rock at Y96–99 with open void below Y95. Four
  courses to cut through, against the ten the pond's own bed would have cost — which is why
  the tail leaves from the rim and not from under the pond.
- The axolotl lies along the harbor's **west** bank (X-24246..-24221), so every spill west of
  X-24216 lands within 5 blocks of the animal. The tail leaves from the SE corner instead.
- At X-24212 the fall hangs **~13 blocks off the Lowland Stair**, far enough not to crowd the
  helix and close enough to descend beside.

**Hydraulics, and the thing that would have made it decorative.** Flowing water dies seven
blocks from its source and the cut channel is seven long — exactly the distance at which the
flow arrives at the lip as nothing. So the channel bed carries **water SOURCES**, cell by
cell, and the last stand at the apron. A source is infinite, so the pond is not drained and
the fall does not stop. The whole chain is verified end to end before a block is dug: bed
solid under every water cell, no wall leaks, the notch open Y94–99, and a clear drop to
harbor water at Y37 in all three lanes.

**One lane wide for the run, three at the apron.** A 60-course thread one block wide does not
read from the lowland floor, and for the tail to fall three wide the water has to arrive
already spread — which is what the apron is for, and it costs no extra digging in the run.

**The notch is the plug: cut it LAST.** Pull it before the channel is dressed and you flood
the trench you are standing in. `/cscan dig` lists all 41 cells.

### The Island Night: the dark was not where anyone would have put a lamp

Block light propagated through the whole assumed-final world and the walking surface
classified. Of **6,851 walkable cells, 1,420 were spawnable** — 1,067 open to the sky (dark
only at night) and **353 enclosed** (dark day and night). And the dark was mostly **not floor**:

    ladybird 361 cells · owl 121 · bat 38 · gecko 20 · the axolotl's back · tree canopies

**A fixture ON a sculpture damages it, and light reaches 14 blocks** — so almost every
sculpture top can be lit from ordinary ground standing near it. That is the whole design, and
it is encoded as COST rather than as a rule: ordinary ground is cheap, a coat is dear, and
greedy maximises newly-covered-per-cost, so it lands on an animal only where nothing else can
reach. 105 fixtures take the island to **zero spawnable surface cells**, re-verified by
propagation in `tests/test_island_night.py`.

One idiom per surface, all of them already spoken here: **froglight flush in turf** (Jack's
own, 39 already placed), **lantern** on worked stone above Y100, **soul lantern** on
blackstone below it — the warm-above/cold-below gradient the stair already carries — and
**glow lichen** face-down on a living coat.

**Four things this cost, each of which produced a clean-looking answer and a wrong one:**

- **`is_protected` is the never-OVERWRITE set, not a keep-CLEAR radius.** It holds `wool`
  because wool may be a sculk sensor's silencer; used as a two-block radius it swallowed every
  wool sculpture on the island plus the air around it, so the very cells the pass exists to
  light had no candidate position left and **523 stayed dark**. Keep-clear is `is_used` only
  (rule 10); `is_protected` applies to the one fixture that REPLACES what it sits in.
- **A lichen is only as rude as it is VISIBLE, and that is measured.** The guess was that
  lichen hides on the ladybird's black spots. `blocks.color` says the opposite: `glow_lichen`
  is a mid grey-green (112,131,122), a pale blotch on black wool (ΔLum 105) and invisible on
  the leaf it sits on (lime 32, green 27). Cost rises with the square of that contrast, which
  is what moved the lichen off the shell and onto the leaf.
- **REACH IS ONE LESS THAN THE LIGHT for a flush froglight.** It is not in the air cell, it IS
  the floor — an opaque emitter a course down — so the cell a mob stands in reads 14, not 15.
  Crediting it 15 left **21 cells** dark at the edges of its coverage.
- **IT IS A FIXPOINT, NOT ONE PASS.** A lantern standing in a surface cell makes that cell
  impassable, so the column's topmost standable block is no longer that one — the classifier
  walks DOWN and finds the next, which is a real spawn spot that was hidden under the one being
  lit. Solving once left **3** such cells. Solve, PLACE the fixtures, classify again: round 1
  placed 102, round 2 placed 3, round 3 found nothing.

And one rule that generalises past this design: **turf lying on a coat is dressing on a
sculpture, not ground.** The gecko is lime wool with a single moss block capping its back; read
as turf it earned a flush froglight, which would have glowed out of the animal.

**`mcbuild/nightlight.py` is the one source** for what light passes through, what emits it, and
what a mob can stand on. The solver and the test each kept their own copy for one session and
that was long enough: the solver's set held `dead_bush` and the test's did not, so the test saw
walkable cells the solver had never considered and reported three dark spots in a design the
solver called finished. Neither was wrong; they were grading different islands. Same rule as
`proportions.measure` / `rubric.score`.

**The one group to delete if you dislike it:** 14 of the 26 lichen are on the ladybird and its
leaf, because it hangs in the void with no ground within reach of its shell. Empty that part of
`lichen` in the config and 361 cells go dark again — stated in the config so the trade is
Jack's and not silent.

### And the sync blindness is fixed

`sync` measured progress against `world_out`, the **Y150+ plate cut**, so every cell of a
below-island design counted as *"outside the scan box (unknown)"* and read as unbuilt. It
reported the whole lowland scene at 0% for that scene's entire life — a stair 74% built came
out as 6/2139 — and the velocity slope was out by about four times. `full_out:` in `sync.yaml`
names a full-depth capture and progress and the shop list are measured against it; without one
it falls back to the old behaviour, so nothing else moved.

## Reading other people's builds: the download corpus (2026-08-27)

Thirty-one `.litematic` files from other builders, in `~/Downloads`. **They are the only evidence in
this project that this project did not produce.** Everything else here is circular in the way this
file already admits — `views.py` renders with the same colour DB the palette picker optimises
against, the rubric scores against tables invented here, and nothing built in this system has been
placed in Minecraft and looked at by a stranger. `tools/corpus.py` reads a folder of them and
reports the measurements below; run it on the next batch rather than doing an afternoon by hand.

```bash
python tools/corpus.py ~/Downloads --vs out            # the gap table
python tools/corpus.py ~/Downloads --render out/corpus # look at them
python tools/ladder.py --like polished_blackstone_bricks
```

It does not score, rank or grade, and it should not. The corpus is evidence about what is
POSSIBLE; turning it into a number would reproduce exactly the failure the panel review exists to
catch — a build that measures well and cannot be named.

### Two disciplines, separated by one number with no judgement in it

`shell %` is the share of solid cells with an air face-neighbour. It splits the corpus cleanly:

| | n | shell % | detail % | distinct blocks | dominant block |
|---|---|---|---|---|---|
| architecture | 18 | 76–100 | 0–61 | 8–133 | 13–65% |
| sculpture | 13 | 21–53 | **0–2** | 13–125 | 44–89% |

A build at ~50% is a sculpture with rooms in it — `Moon Castle`, a crescent moon 111×105×52 with
towers and an arcade built into the mass — and it is the hardest kind. Nothing in the corpus mixes
the two vocabularies: their sculptures use **no** detail blocks at all, and their architecture is
half made of them.

### THE ACCENT TAIL IS THE GAP, AND IT IS THE ONLY ONE

Measured against our own designs, sculpture against sculpture:

| | n | palette (median) | cells beyond the top 3 blocks | detail % | dominant % |
|---|---|---|---|---|---|
| theirs | 13 | **31** | **18.5%** | 0.0 | 56 |
| ours | 34 | **6** | **5.8%** | 0.0 | 53 |

Same discipline, same dominant share, same zero detail blocks — **five times the palette and three
times the accent mass.** That is the whole difference, and it is not scale: `JAG big` is 57,994
blocks with a 4-block palette and an 8% tail, and it failed exactly as the 27-block jaguar did,
which this file already records. It is not shading either — luminance correlates with ambient
occlusion at only r=−0.15 on their best statue, so they are not running a light model; the accents
are local material events (moss on stone, a paler cheek, a darker seam).

**Our two best sculptures are already the two with the biggest tails** — `Lowland Heron` 27%,
`HERON hd` 28% — which is the finding corroborating itself from inside the repo.

### The value-contrast claim was wrong, three times, for one reason

This file states as fact, in three places, that this economy has almost no value contrast:
*"cracked and chiseled stone brick are within 4 RGB of plain"*; *"blackstone cannot draw value lines
on itself — the family sits within 12 RGB"*; *"`deepslate_bricks` — 51 darker, the one real value
contrast this economy has at cheap-or-ok tier."*

Every measurement is correct and the conclusion drawn from them is false. All three searched inside
**one material family**, where a value ladder cannot exist by construction: a family is one material
shown four ways, and dressing a stone does not change how much light it returns. Searched ACROSS
families at the same hue, the cheap neutral ladder is `white_wool` 236 · `smooth_stone` 159 ·
`stone` 126 · `deepslate_bricks` 71 · `black_wool` 21 — **215 of luminance in five cheap stops**
against the 51 we have been calling our only contrast. Against `polished_blackstone_bricks` the
blackstone family offers 6.9; `tools/ladder.py` finds a four-stop ladder with a **59** minimum step.

`ladder.py` scores a ladder on its SMALLEST adjacent gap, never its range — 236/159/151 has a wide
range and two rungs nobody can tell apart. Three things about its pool that are the same traps this
file already documents, arrived at from a new direction:

- **The pool is witnessed, not remembered.** Over the bare registry it proposes `dried_ghast` and
  `chiseled_cinnabar` — rule 12's exact failure, shipped twice here already. It starts from
  `shell._confirmed()` and `--any` opens it up loudly.
- **A capture beats the allowlist.** `server_blocks.json` is 191 blocks and stale: it does not name
  `deepslate_bricks`, which four designs are built from. `out/island_full.litematic` holds 205
  blocks all standing in this world today. Both are unioned.
- **`protect.is_protected` is the WRONG filter here and it holds `wool`.** Used as "may I build
  with this" it deletes every wool in the game, which is most of this island's sculpture material.
  It is the never-OVERWRITE set — the same mistake `Island Night` made and wrote down. The gate is
  the rubric's `plain_blocks_only`.

**Their ladders are unaffordable and the technique is not.** Terracotta, concrete and quartz are all
`expensive` here, and their sculptures are 70–89% one of them. So the ladder must be found rather
than copied, which is what the tool is for.

### The detail vocabulary, and the half of it that is a mirage

Across the corpus, weighted by cells. The left column is a placement DECISION; the right is
computed by the game from the neighbourhood and **must not be implemented**:

| decided | cells | derived — do not build this | cells |
|---|---|---|---|
| `slab type=bottom` | 7,935 | `stairs shape=*` | 9,292 |
| `slab type=top` | **5,841** | `wall up` + connections | 7,896 |
| `slab type=double` | 3,049 | `waterlogged` | 198,303 |
| `stairs half=bottom` | 6,781 | `distance` (leaves) | 160,019 |
| `stairs half=top` | **2,505** | pane connections | — |
| `trapdoor open=true` | **1,743** | | |
| `trapdoor open=false` | 455 | | |

The derived column is why the ~190 inner/outer corner stairs in the corpus are **not** a technique to
copy: the game resolves `shape` on placement, so our blanket `shape="straight"` is already correct
and nothing needs writing. This file settled the same fact for `work.INTENTIONAL`; `corpus.py`
splits the histogram so nobody re-derives it by reading a block count.

What IS new vocabulary, and we emit none of it:

- **`slab type=top`** — 42% of their non-double slabs. `shell.py` places bottom slabs only.
- **`stairs half=top`** — 27% of their stairs: eaves, soffits, corbels, the underside of an
  overhang. One line in `interior.py` is the only place we do this.
- **`trapdoor open=true`** — **79%** of their trapdoors. An open trapdoor is a thin vertical panel on a
  block face, which is the vertical-slab Minecraft never shipped. Our three trapdoor uses are all
  `open=false`, as wing sheets and planter sides.
- **Entities and tile entities as decoration** — 19 paintings, 5 item frames, 5 armour stands, 120
  signs, 89 banners, 61 chiseled bookshelves. `schem.py` already reads and writes the `Entities`
  and `TileEntities` lists, so this costs no format work; we have simply never used it.

**Already right, confirmed rather than learned:** every one of their 159,983 leaf cells is
`persistent=true`, and so is every leaf we place. Ours would not have decayed.

### A CAT THAT WORKS, and what it does to the retirement rule

`Warm Snooze` is a sleeping ginger tabby: 35×19×36, 10,323 blocks, and it reads as a cat instantly
from all three views. This file's central sculpture finding is *"do not build cats, bears, or
anything whose species is carried by muscle mass"* — and that rule, as written, is too strong.

The corpus contains **no realistically-proportioned quadruped at all**. Every animal in it is one of
three things, and all three are categories this file has already named as ones that work:

- a **single convex mass** — the curled cat, `Stump Perched Owl` (56×54×56), `Holding Flowers
  Rabbit` (31×57×40, an upright chibi). This is the ladybird's category: *"a pattern on one convex
  dome... the dome is a voxel primitive, not a blend of five muscle groups"*;
- a **membrane** — `dragon_slaying`, a 172-block wingspan at 96.6% shell and ten blocks total, a
  one-thick wing sheet with lighter struts. Our sky bird and bat;
- a **columnar figure** — the knight statue, 70% one block with moss weathering.

So the failing variable was never the species. **It is whether the silhouette decomposes into
limbs.** A cat on four legs with a barrel between them is the shape voxels render worst; the same
cat folded into one mass is the shape they render best, and the curl also makes the PLAN the money
view — the view voxels give away free. `Warm Snooze` is 35×36 in plan and 19 tall: wide, low, and
read from above.

**This is a note, not a change.** Nothing in `species.yaml` moved and no retirement was lifted — the
retired list is *"a record, not a threshold"* and reversing it is Jack's call. What the corpus
settles is that the door is narrower than "no mammals" and differently shaped: a curled or seated
mammal whose legs are tucked into the mass is worth one attempt, at a wide low footprint, judged on
its plan.

### Open, and deliberately not acted on

- **The accent tail is the one change that would move every sculpture we have**, and it changes how
  all of them look, so it is Jack's call — the same standing as the "build coats out of
  uniform-textured blocks" question this file already parks.
- **`shell.py` may now take `type=top` slabs and `half=top` stairs.** Its docstring still says
  stairs are barred because *"the capture holds ten stair blocks and none of them records its
  state"* — that was corrected in the stairhead work (463 stairs, states in the palette NBT) and
  the docstring is stale.
- **`rubric.FUNCTIONAL` does not name `shulker_box`**, so a dyed-family expansion admits sixteen
  containers as surface material. `ladder.py` excludes them locally; widening the rubric's gate is
  a scoring change and was not made here.
- **The corpus is a different Minecraft.** Data versions run 2730 to 4903 — roughly 1.17 to 1.21.x,
  with 21 of the 31 at 3955 (1.21) — and the
  builders reach for `pale_oak`, `tuff_bricks`, `chiseled_tuff`, `cherry_*`, `copper_bulb` and the
  `light` block — 267 of them in one build, an invisible light source that would have been ideal
  for `Island Night`. None of it is on a 1.19 server. `corpus.py --vs` flags every block they use
  that no design of ours contains and marks the ones we cannot spend.

## The Lowland Thicket: the cave was quarried but never planted (2026-08-23)

The audit that produced it was a sweep of every area for what to add next. Two of the answers
were negative and are worth keeping, because they say where NOT to spend effort:

- **The plate has no dead ground.** Every walkable cell on it is within **4 blocks** of
  something built or planted, median 0. "Focal-point saturation" is now measured, not asserted:
  nothing new belongs up there.
- **The descent is the emptiest band on the island** - Y51-99 at 1.47% density, and in the
  slice Y70-79 there are 163 blocks within 30 of the helix axis of which **zero** are anything
  but the staircase itself. The Falls now crosses it at r=20, which is most of the fix; the
  band is still the one place a new hanging piece would be seen.

And the positive one, which is the largest single gap on the island. The lowland is called
"Minecraft's lush-caves palette - moss, azalea, fern, dripstone" throughout this file. Measured
against the 15:54 scan it holds 38 block types and its entire flora is

    moss_block 3986 · dripstone_block 4141 · vine 1098 · moss_carpet 56

with ZERO azalea, fern, grass, dripleaf, spore blossom, cave vine, lily pad - and, despite
4,141 dripstone BLOCKS, not one pointed dripstone. **A cave of rock and moss is not a lush
cave.** It was never removed either: the `Lowland` ground design's own cell list contains
moss_block and vine and no other plant, so this is unbuilt work. The 32,369 vines Jack purged
were vines, and only vines.

`configs/lowland_thicket.yaml`, `gen/thicket.py` - **1,424 plants, 0 problems, all cheap.**
11,478 ceiling cells, 6,803 floor cells and 617 shallow water columns were available, so the
design problem was restraint, not room.

**PLANT IN DRIFTS, NEVER IN CONFETTI**, and the first build failed exactly this test: 191 blobs
of which **75% were one or two cells**, because the drift falloff was thresholded per cell.
That is the deck floor's scatter reproduced in green. **The noise belongs on the drift's
RADIUS, not on its interior** - the middle then fills solid and only the boundary wobbles.
After the fix, 76% of planted cells live in blobs of 8 or more and the largest patches are
30-36 cells. `test_thicket.py` pins the ratio.

What each species is for: **cave vines** carry glow berries, so the hanging gardens light
themselves (207 cells at light 14) - kept clustered and moderate on purpose, because Jack has
just removed 32,369 vines and this must not read as the vines coming back. **Spore blossoms**
are rare, large and they DRIP: one of the few sources of motion this island can have.
**Dripstone** is what 4,141 dripstone blocks were promising, built as real tapers
(base-middle-frustum-tip) rather than single spikes. **Azalea and fern** drift on the moss with
a moss-carpet fringe so a patch fades instead of ending on a hard edge.

Four traps, each of which shipped a clean-looking build first:

- **A plant roots in the DIRT FAMILY and nowhere else.** Listing mossy cobble and mossy stone
  brick as soil because they look like ground returned **173 placement problems** - fern on
  mossy_cobblestone, azalea on mossy_stone_bricks. Rule 11 again. Moss carpet is the exception:
  a carpet sits on anything, which is what lets a drift fade off its soil onto the rock.
- **PASSABLE IS NOT EMPTY.** `air()` answers "can a body or light pass through this" and says
  yes to vine and grass. Used as the test for *may I build here* it grew a stalagmite up
  through two of Jack's vines: the design claimed cells the world still fills, the composite
  kept the vine, and the audit correctly reported a spike floating above it. This is the mirror
  of the rim stair's "vine is not footing".
- **`is_protected` holds "water"**, rightly - a generator must never overwrite a fluid - and
  applied to the survey it banned every water cell, so the whole harbor margin came out empty
  in silence: 0 lily pads, 0 seagrass, 0 dripleaf. A waterlogged plant does not remove water;
  the BED is what must be checked.
- **A lily pad floats on water**, so nothing may take the cell under it. Where the pond is one
  deep the bed IS the surface, and seagrass planted there left eight lilies sitting on seagrass.

And the artifact trap, hit **twice more** in one session: `work.json` carries only
`work.INTENTIONAL` properties, so grepping it for `berries` or `thickness` tests the wrong
file - both live in the litematic's palette. `m.names` drops properties too, which is why the
palette looks like it holds duplicates. Read the palette NBT.

**Build order is now Falls, then Thicket, then Island Night**, and the night pass was re-solved
against a world containing both: pointed dripstone is the one plant here that is not passable,
so a stalagmite moves the surface classifier down a course and can open a spawn spot under
itself. 107 fixtures now, still zero spawnable surface cells.

### Still open, and measured - the island is built but unfurnished

The pattern the audit kept finding: the last one or two percent of several designs is exactly
the props that make a place feel inhabited, and all of it was accepted as complete.

| | | |
|---|---|---|
| Atelier Court | 14 | a workshop with **no tools** - 9 workstations unbuilt |
| Lowland Campanile | 42 | a bell tower with **no bell** (the island has zero bells) |
| Undercroft Store | 77 | a storeroom with **no barrels** (39) |
| Lowland Portal | 114 | the lowland's ICON, never started, amethyst and all |
| Chimneys | 10 | campfire + soul campfire: the only smoke the island can have |
| Statue Footings · Apiary Flowers | 61 | the planting round the statues and for the bees |

That is **~318 blocks that turn built into inhabited**, and none of it is new design work -
only a decision to re-track designs that were accepted as finished.

## The chunkscan audit (2026-08-27) — a scan had eaten a design

A full read of the mod: 33 client classes, 15,537 lines, 364 Java tests green before it started.
The build was healthy and the shipped SCHEMATICS FOLDER was not.

### A SCAN AND A DESIGN SHARE ONE NAMESPACE, AND THE SCAN WINS

`/cscan Falls` had been run. `ScanRunner` resolves `<name>.litematic` and writes unconditionally, so
it overwrote the design of the same name:

| | the design (`out/`) | what was in the schematics folder |
|---|---|---|
| litematic | 44×114×53, **30 blocks**, 4 palette | 103×335×103, **111,631 blocks**, 594 palette |
| sidecar | `kind: falls`, **41 dig cells** | a capture sidecar, **0 dig** |

`Falls.work.json` survived, so the mod's own state was internally inconsistent: `/cscan follow`
still saw 30 cells of real work while `/cscan dig Falls` reported nothing to clear. The 41 lost
cells include the notch that has to be cut LAST — pull it early and you flood the trench you are
standing in. And `Falls` was in `designs.json`, so **bare `/cscan place` would have pasted a
111,631-block island capture onto the island.**

**Nine more captures were sitting in the same folder** under the names `clear`, `off`, `on`, `wand`,
`islan`, `_fill here` and `AtelierCourt`. Every one is a mistyped or not-yet-existing subcommand:
the bare `/cscan <name>` scan form is the last alternative in the command tree, so anything
Brigadier does not recognise falls through to it and writes a multi-hundred-kilobyte world capture
under that word. `Designs.list` then offered all of them as designs — its docstring said it "skips
the raw scans" and it never did.

**Restored and quarantined.** `Falls` is back from `out/` (the clobbering capture survives as
`scans/falls_20260827-1813.*`, so nothing was lost either way); the nine junk captures moved to
`schematics/_junk/` rather than deleted, because they are Jack's files.

**Three guards, and the last of them is the one that matters:**

- `Designs.isDesign` / `designExists` tell a design from a capture. **The CAPTURE markers are what
  is tested, not a positive design marker** — that distinction is not pedantry. Testing for `kind` /
  `generated_by` / `dig` looked equivalent and hid `Lowland Axolotl`, whose sidecar is a
  hand-written as-built record carrying only `file`, `name`, `note`, `origin`. Absence of evidence
  that a file is a capture is good evidence it is a design; the reverse does not hold. The scan
  guard is more cautious still: an unparseable sidecar blocks a scan, because the cost of being
  wrong there is a design and its dig list and the cost the other way is picking another name.
- `ScanRunner` refuses to write over a design and says so. Re-scanning `island` over yesterday's
  `island` is the daily loop and still works, because a capture is recognisable.
- `ChunkScanClient.RESERVED` holds every command word — plus words that are NOT commands yet
  (`scan`, `undo`, `progress`, `help`, `list`, `status`), because the failure mode is reaching for a
  command that does not exist, which is exactly how `islan` and `clear` got there. `/cscan scan
  <name>` is the explicit spelling for a scan name that collides on purpose.

`SidecarSafetyTest` pins all of it, including that **every registered literal is reserved**, read
from the command tree's own source so the list cannot drift behind a newly added verb.

### THE DIG LIST WAS NOT WORK

`Work.Split.complete()` was `todo.isEmpty() && unseen == 0` — placements only. A litematic cannot
express removal, so "break this" lives in the sidecar, and nothing in the loop read it. `/cscan dig`
could SHOW the list; showing is not the same as knowing.

Measured on the tracked designs: **`Falls` is 58% dig** (30 to place, 41 to break) and **`Island
Night` is 22%**. The loop would have placed thirty blocks, reported the design complete, and left
the channel it exists to cut standing in solid rock.

**Two questions, not one, and separating them is load-bearing.** A client mod cannot break a block —
the printer places, and digging is Jack with a pickaxe. Had the loop's advance condition demanded an
empty dig list it would have sat on `Falls` for ever waiting for something it can never do, and
`follow all` would never have reached the next design: the "a thing that does nothing, quietly"
failure this file keeps writing rules about. So `complete()` is the truth and `placementComplete()`
is what the loop advances on, and every completion message now names what it is handing back.

### Smaller defects, each one a rule this repo already wrote

- **`Ignored` survived a disconnect** — and its own docstring said "a relog is the accidental
  [clear]". That sentence was there before it was true. `Wand` states the rule these keys live
  under, *coordinates mean nothing without a world*, and a strike list is nothing but coordinates.
  Now cleared on DISCONNECT, along with the withdrawal's position-keyed cooling-off, the HUD's
  arrow and the autopilot's approach. The loop's INTENT still resumes from `session.json`; the
  positions do not.
- **`Highlight.tick` had no try/catch**, and the pre-upload audit had already written down that *a
  throw out of a tick event is a client CRASH*. It guarded the movement and looting ticks and missed
  the busiest one — every highlight layer redraws there every tick over block lists a caller
  supplied. Guarded, and it clears the batches rather than throwing again next tick. `Menu` too.
- **Fourteen of sixteen path-resolving commands never validated the name.** `fill` and `copy` were
  checked when the wand was audited because they WRITE; the read paths were not, so
  `/cscan paste ../../../x` would load a schematic from anywhere on disk. The gate is now at the two
  functions that turn a name into a path — `Work.file` and `Designs.load` — not at the sixteen
  callers, so the next command to want a design name cannot forget it.
- **The archive was unbounded**: 24 files and 1.6 MB when first noted, 56 and 4.4 MB when measured
  again, and `/cscan auto` adds one per tick for ever. Capped at twelve per NAME — per name, so a
  chatty auto-scan cannot evict the one hand-made capture a design was verified against — and sorted
  by filename, because the name carries the timestamp and mtime moves when a folder is copied.
- **The command sheet omitted five real verbs** (`chunks`, `sel`, `unmark`, `label`, `auto`) and
  `MenuTest` named them in its `modifiers` exemption list, so the check written to catch a stale
  sheet was configured not to see them. Rows added; the exemption list now holds only words you
  would never type first, and the assertion is `isEmpty()` rather than `size() <= 2`.

### What was added, because the audit kept finding built things with no door

- **`/cscan undo <name>`** and **`/cscan undos`**. Every fill has always written `_undo <name>`,
  `UndoAndStorageTest` has always asserted both of its halves, and `Designs.list` deliberately hides
  them so a bare `place` cannot sweep one up — and nothing ever offered one. Both halves or it
  half-works: re-placing restores what the fill covered, and the cells the fill made from AIR are
  highlighted to break, because a litematic cannot express removal.
- **`/cscan progress`** — every tracked design, how far along, what is left to place AND to break,
  in build order. `python -m mcbuild progress` has always answered this and only offline.
- **Build order reaches the game.** `finish.defer_to` settled precedence at generation time and
  CLAUDE.md stated the sequences in prose; the sidecar carried neither, so `follow all` walked the
  tracked list as written. `pipeline._after` derives an `after` list from `defer_to` — deferring IS
  the ordering, since a design that yields a shared cell cannot be built first — and
  `Designs.inBuildOrder` topologically sorts the run. A design with no `after` keeps its place, so a
  folder written before this exists is ordered exactly as it was, and a cycle still builds something
  rather than refusing everything.
  **`Island Night` now records `after: [Falls, Lowland Thicket]`**, which was the one hard ordering
  on the island written down only in prose: the night pass is a fixpoint solved against the finished
  world, and the Thicket's dripstone is the one plant that is not passable, so it moves the surface
  classifier under the solution.

**Still open, deliberately:** `Lowland Thicket` has no `after` recorded — its config belongs to
another session that was editing it, and the ordering it needs (`after: [Falls]`) is a one-line
addition for whoever owns it next. And the two legitimate captures, `island` and `islandlow`, still
live beside the designs; they are now correctly excluded from `Designs.list`, but a `scans/` home
for them would be tidier than a rule that knows to skip them.

384 Java tests, 0 failures.

## Island Enrichment: the detail our buildings never had (2026-08-23)

Jack, comparing our scenes to other people's: *"i dont think our area is nearly as detailed or
up to snuff"*. He is right, and `tools/corpus.py` says by how much. Against 31 outside builds:

| architecture | palette (median) | detail % (median) |
|---|---|---|
| theirs | 37 | 17.3 |
| ours | 14 | 11.4 |

and per building it was far worse than the median. The **Campanile was 575 cells of 12 block
types at 1.4% detail** - a bell tower of three blackstone variants stacked - against their
comparable watchtower at 45 types and 48.9%. The Sanctum, "the quarter's one complete
building", was nine block types. Court Hall was 0.0%.

**THE MISSING VOCABULARY IS SPECIFIC.** Per thousand cells, ours against theirs:

    stairs    0.64 vs 4.51     seven times under
    fences    0.07 vs 2.22     thirty times under
    trapdoors 0.00 vs 1.07     we have never placed one
    panes     0.08 vs 0.49

while we OVER-use the chunky families: walls 1.8x, carpet 9.9x, lanterns 3.0x. That is the whole
diagnosis - **we build in full blocks, slabs and walls and skip the three families that make a
surface read as built.** An open trapdoor is the vertical slab Minecraft never shipped; an
upside-down stair is an eave; a fence is a railing.

**And the economy is not the constraint.** 350 detail blocks are 1.19-legal and spendable, 38 of
them stone-family ones already in the quarter's own palette. This was self-imposed.

`configs/island_enrichment.yaml`, `gen/enrich.py` - **416 blocks, 0 problems, OVERLAP 0.**

**ADDITIVE ONLY.** Every zone is 89-97% built, so the pass writes into AIR and never over
anything standing - the deck floor's rule that a remedial design is judged by what it REPLACES.
The cost is that it cannot deepen the palette of an existing wall, only of the detail hung on
it, which is why palette moves 12 -> 14 while detail moves 1.4% -> 15.9%.

| design | detail% before | after |
|---|---|---|
| Lowland Campanile | 1.4 | **15.9** |
| Court Hall | 0.0 | **15.4** |
| Lowland Sanctum | 9.7 | **18.4** |
| Deck Vault | 11.5 | **20.9** |
| Lowland Ruinway | 48.0 | 61.9 |

**RUNS, NOT CELLS** is the rule that decides whether it reads, and it is the deck soffit's
lesson in a new place: that pass drew a coffer grid per cell and produced 215 runs of which 184
were one or two cells - confetti, in the loudest block available. A cornice on scattered cells
is the same mistake. So a course shorter than `min_run` gets nothing.

Three things this cost, each of which shipped a clean-looking build first:

- **The gate has to run on what is PLACED, not on the candidates.** Filtering after grouping
  let a five-cell run with two blocked cells ship three scattered stairs: the run passed the
  threshold and the placement did not. That is the soffit's bug wearing a different hat.
- **One record per cell.** An inside corner has masonry on two sides, so it enters as two
  candidates with two normals; left in, it counted toward a run on BOTH axes while only ever
  being placed once, and three stairs shipped in runs of one because the other axis' span had
  been emptied by the first.
- **A SILL IS NOT A COURSE, so the run gate must not touch it.** The gate exists to stop a
  course appearing on scattered cells; a sill is anchored to one opening, and an opening here
  is one to three cells wide, so gating it by length deleted all 46 of them. And the first
  opening test looked for masonry above and below a FACE cell, which asks whether the air
  OUTSIDE a wall is boxed in - it never is, so it emitted nothing at all.

**A stair leans INTO the wall it grows from** - its tall side is its `facing`, per the
convention pinned in `test_stairhead`, and our renderer draws both directions identically, so
`test_enrich` asserts it rather than trusting the eye.

**Honest limitation: the payoff is geometric relief, and that does not show in our renders.**
Blackstone on blackstone is within 12 RGB of itself, so an orthographic view of the enriched
Campanile looks almost like the plain one. Projecting stairs cast shadows in game and read
strongly there; offline this is the circularity CLAUDE.md already admits. Look at it in world
before extending the pass.

**Still open, and deliberately not built:** fences (30x under) and trapdoors (never used) are
the two biggest remaining gaps in the vocabulary. A trapdoor shutter is the strongest single
move in the corpus. Both want their own look at the geometry rather than being bolted onto
this pass - `rail: false` is in the config for that reason.

## The Island Run: a parkour descent, and two things it got wrong first (2026-08-23)

Jack's idea: jump pads from the top that wind all the way around, all the way down.

**THE FIRST BUILD WAS A STAIRCASE AND HE SAID SO** - *"this is a jumpable staircase, not
parkour, theres nothing challenging etc about it, no jump pads etc, this is crappy done"*. It
was: 77 landings of 3x3, four blocks apart, two-course drop every time. Every jump identical,
every landing forgiving, no failure mode, and no slime anywhere - because I had argued myself
out of jump pads on a physics point about winding. **A ramp with gaps in it is not parkour.**

What makes a descent a course is a VOCABULARY, in a rhythm, getting harder as it goes:

| move | what it is |
|---|---|
| LEDGE | a **one-block** landing, 3 to 4.5 out and nearly level - the sprint jump is the game |
| PLUNGE | a real 8-16 course fall onto a **slime** pad, which bounces and cancels the damage |
| GATE | a wall on the landing, so the jump clears something as well as reaching it |
| REST | a 3x3 lit checkpoint - the only place the run lets go of you |

**The plunges are what make the ledges hard.** Steering a fall buys ~2.0 blocks of reach for a
two-course drop and ~5.0 for a thirteen-course one; one turn of this island is ~270 blocks of
travel against ~150 courses to spend. Descend by little drops and you spend all the height on
distance and every jump is trivial - which is exactly what the first build did. Spend the
height in a handful of plunges and the ledges stay level, so they have to be JUMPED.

`configs/island_run.yaml`, `gen/parkour.py` - **97 moves, 273 blocks, 0 problems, overlap 0.**
Y194 to Y48, **2.1 turns**, 62 ledges, 13 slime jump pads, 15 gates, 7 checkpoints. Ledge gaps
2.2-4.5 with **42% at full sprint distance**, and no move anywhere costs health.

### The plot is a square, it is FOUND, and the first build went over it

Jack: *"some go over the edge of our 99x99 boundary, no blocks should go further out than
something we've placed, you can find the 99x99 area by locating the bedrock and moving around
it."* The run had **120 cells outside it**, up to 51 out.

The guard was checking the CAPTURE box - 103x103, two blocks wider on every side. **The capture
is how much of the world we photographed; the plot is how much of it is ours.** `mcbuild/plot.py`
now finds the island's bedrock at **(-24200, 200, 30000)** and measures 49 out on each axis, and
the evidence agrees exactly: all placed content spans X -24249..-24151 and Z 29951..30049, 99 by
99. It is a SQUARE, not a circle - a route at radius 52 is legal on the diagonals (49*sqrt2 = 69)
and three blocks over the line at the cardinals, so a radius check would either waste the corners
or overrun the sides.

### Three more things this cost

- **PASSABLE IS NOT EMPTY - for the second time in one session.** The landing test allowed vine
  and grass because the HEADROOM test does, and two pads shipped on top of Jack's vines. The
  landing course is tested for AIR now and the courses above it for passability.
- **TWO DESIGNS CANNOT SEE EACH OTHER.** A 1x1 ledge in the void is a walkable surface, so the
  night pass solved it - by putting **14 lanterns in the cells you have to land on**, breaking
  fourteen jumps. Neither design was wrong on its own. The fix is that the landing IS the lamp:
  every ledge is a froglight, which needs no extra fixture, removes the conflict, and lets you
  see the next jump in the dark. The night pass went 120 -> **105** fixtures as a result.
- **SLIME IS EXPENSIVE HERE**, and 13 blocks blows the repo's 8-block ceiling on expensive
  materials. It is declared rather than smuggled: `expensive_allowance: 13` sits in the config
  with the reason beside it, because slime IS the jump pad and no cheap block cancels a fall
  (hay cuts damage 80%, honey 20%). 13 blocks is 117 slimeballs against the 193 in store.

## The churchyard frog (2026-08-28) - ONE CONVEX MASS, and the pattern does the work

`configs/lowland_frog.yaml`, `mcbuild/gen/frog.py` - **2,079 blocks, one piece, 0 problems, 0
overlap in context, all cheap.** Jack: *"build a frog, put it opposite end from axo, on the far
empty lot left of the church"*.

### The first build was a smooth mass and it did not read

It was a lofted superellipse - the axolotl's and the turtle's machinery - and Jack said flatly
that it did not read as a frog. It did not. He sent three references: the **Minecraft frog mob**,
a **frog-shaped house**, and an outside builder's **voxel frog**. NOT ONE OF THEM IS A SMOOTH
MASS. All three are assembled rectangular parts - a flat-topped head box, a lower body box,
blocky haunches, splayed feet with separate toes - and all three read instantly.

**That is the void tower's rule said again for a creature: what makes voxels legible is
REGULARITY AND SEPARATION, not smoothing.** A loft averages every part into one hill, and a hill
is what the panel could not name; the parts here are boxes with air between them, and the air
does as much work as the blocks - under the chin, between the arms, between the knee and the
back. `gen/frog.py` has no `loft` import at all: it has a `box()` with a corner **chamfer**,
which is all the rounding a voxel animal wants.

**AND THE PROPORTIONS ARE THE MOB'S, NOT THE ANIMAL'S.** The naming test is *would a stranger
say frog*, and on a Minecraft server the stranger's reference is the mob: a HEAD nearly half the
length, eyes bulging off the top of it past the outline, a small low body behind, a pale throat,
feet that splay. Anatomically-correct proportions gave a toad. This gives the thing people have
seen a thousand times.

**THE PLAN NEEDS A WAIST.** At head 11, body 9 and haunches 13 the envelope was a constant
rectangle 17x15 and the animal read as a brick from above - which is the view this medium gives
away free, so it is the one that must not be a box. Head 9, body 7, haunches 13, with the eyes
AND the feet standing outside the head's own width: that is what puts a notch in the outline.

### The lot was measured before it was drawn

Standing in the sanctum's doorway looking out (the facade faces south), the lot on its LEFT is
the east one - and it is the far end of the lowland from the axolotl, which lies ~50 blocks west
on the harbor bank, so the two never share a view. It is also the largest genuinely empty ground
left down here: a flat plain at **Y39**, **0 blocks standing above it**, no lantern of the ground
design's 9-grid inside it, 113 courses of headroom. At 15x13 the lot yields six placements at
roll <= 1; at **17x13 it yields none**, so the animal sits at `at: [-24167, 29976]` on ground
that rolls three courses (176 columns at Y39, 42 below it) and the SKIRT - every ground-course
column filled down to its own turf - is what carries that. Nose 3 clear of the church wall,
which is a test.

**SIZE FROM THE EYE.** A bulge needs 3x3 and a clear cell between the pair or the two read as one
brow (the ladybird's spot spacing), so the skull cannot be under 11 wide - and the eyes then take
the animal to 13 across, which is what the lot holds.

**COLOUR.** The moss floor is (89,110,45), so a green frog is the green-turtle mistake. This is
the TEMPERATE (orange) frog: three tones of one hue, which the flamingo proved beats two tones
and a third - `orange_wool` (241,118,20) over `acacia_planks` (168,90,50) over `brown_wool`
(114,72,41) - with a birch throat, a gold iris, a black pupil. `tests/test_frog.py` asserts the
ladder is a ladder (>= 20 luminance a rung) and that the top tone is >= 40 clear of the moss.

**NO BLOTCHES.** Three attempts at mottling produced, in order: brown confetti; regular crosses
(a radius of 1.4 in `dx^2+dv^2 <= r^2` yields the five-cell orthogonal plus, not a disc); and a
diamond stamped on the flat back of the box build. The animal reads better plain. The
dorsolateral line down each flank is the one marking that is a LINE rather than a stain.

### The night pass cannot see this animal, and that is a hole in the whole island

Propagated through the finished world, **129 of the 149 air cells over the first build's back
stood at block light ZERO** - a zombie on the sculpture every night. `Island Night` reports zero
spawnable surface cells with the frog in place, and it is wrong to be reassured by that: its
classifier takes each column's **topmost standable cell**, and this lot lies 113 courses under
the island's belly, so the frog, the lot and everything in it are invisible to it.

| | |
|---|---|
| lowland columns with a standable cell under Y60 | 6,852 |
| ...that the night pass's classifier ever grades | **1,624** |
| ...invisible to it because island stands overhead | **5,228 (76%)** |
| lowland walking-surface cells actually at light 0 | **480 of 6,783 (7%)** |

The Lowland Glow solved to zero because it ran on a LOWLAND-ONLY composite, where the floor IS
the topmost standable cell; the island-wide pass then swallowed it. **Those 480 cells are open
and are not this design's to fix** - a night re-solve scoped per LEVEL rather than per column is
its own project, and Jack's call.

The frog answers for its own back with six `ochre_froglight` **in the skin, not on it**: three
down the spine, one on the crown, one in each hind foot. In the skin, because a fixture laid over
a coat is the hole in a sculpture the night pass's own rule forbids. On the crown, because the
EYES are the highest cells on the animal and the back lamps sit four courses below them. In the
feet, because light has to travel round the body to reach the toes and no spacing of the spine
lamps ever got there. `test_nothing_can_spawn_on_its_back` re-runs the propagation rather than
trusting it. It is also the one animal on the island that glows, which for the mob froglights are
made from is the right animal to do it.

### Traps, every one of which shipped a clean audit and a wrong build

- **A CHAMFER EATS A PART TWO CELLS WIDE.** `chamfer=("uv",)` drops the cells where a u-edge
  meets a v-edge; on the shin - three stations long, two cells wide - *every* cell is on both
  edges at its end stations, so it came out as a 2x3 slab floating beside the body. Seven cells,
  caught by the component count and by nothing else.
- **The eye sits directly over the hind foot in plan** - it is as wide as the haunch, which is
  what the mob looks like - so asking for the topmost cell of that column to make it a lamp
  returns an EYE, `paint` correctly refuses to recolour it, and both foot lamps were silently
  never placed. A fixture that belongs to a part must be addressed at that part's own course.
- **The nostrils were painted onto the head box's own chamfered edge**, so they were `paint`s
  over air: `nostril: 0` in the sidecar, and a face with no nose that still audits clean.
- **The lofted build's legs read their own output.** `flank_v` scanned everything built so far to
  find the body's widest offset, so each pass answered one cell further out and the animal crept
  from 15 wide to 19. (Gone with the loft, kept here because the shape of the bug is general:
  measure the MASS, never the accumulating buffer.)
- **The forelegs were built after the hind FOOT, which lies exactly where the hand goes.** Every
  cell found the ground course taken and it shipped with `forelegs: 0` **in its own sidecar** -
  and nothing noticed, because a frog with no arms is still one connected piece with no placement
  problem and a clean BOM. `test_it_has_arms` is four lines and now checks every part.
- **`profile_view` in the sidecar OVERRODE panel.py's own rule** and pointed it at the head-on
  view, which is the one view a profile must not be. The key is simply not written now.
  `Lowland Turtle` records `profile_view: side` with the same facing and has been reviewed
  head-on ever since - worth a look when someone next opens it.

### Audited against the three references, block by block (2026-08-28)

Jack: *"audit again, fix it, I want it to be more like reference."* Six differences between the
box build and the frog mob / the frog house / the outside voxel frog, all of them fixed:

- **THE EYE WAS GOLD-DOMINANT AND IT SHOULD BE DARK.** On the mob and on the house the eye is a
  dark eyeball with a bright ring around it; the build had a gold 3x3 with one black cell on
  top, which reads as two gold cubes on the corners of a box. Same cells, opposite emphasis:
  gold ring below, one raised black pupil above. **One cell, not five** - a black plus on top of
  the ring covers its whole middle row and column, and in PLAN, which is this animal's best
  view, the eye came out as a crosshair on a gold square.
- **THE PALE BAND WAS A SEAM.** One course of birch under a dark line is a joint; the house
  carries a band you can see from across the water, and it is half of what makes a blocky orange
  box read as a face. Two courses now, with the mouth line sitting on top of it and running back
  along the jaw.
- **THE HANDS WERE FOUR CELLS TUCKED UNDER THE CHIN.** The house and the voxel frog both give the
  front feet three splayed prongs with gaps, and they are the detail that says ANIMAL rather than
  ornament. Three toes now, of three different lengths, reaching to the line of the snout - and
  INBOARD of the hind feet, because out at the animal's own widest there is no room and the nose
  is three blocks off a church wall.
- **THE BODY WAS A HARD BOX.** The reference bodies are rounded; the top edges are chamfered now,
  which costs 12 cells.
- **THE HEAD HAD NO BROW.** The house's roof overhangs its eye band, and the overhang is most of
  what stops the face reading as the end of a crate. The head's TOP course now runs out to the
  nose at full width over a face inset one cell on three sides. It costs no length, which
  matters here. **The nostrils had to move onto the brow with it** - left on the skull behind
  the overhang they were invisible from the only view that shows them.
- **IT WAS STRETCHED.** 17 long against 11 tall; the references are near 1:1 (the house) and
  1.3:1 (the voxel frog). **15 x 13 x 11** now, which is also the footprint the lot takes at
  roll <= 1 rather than roll 3 - the proportion fix and the siting fix turned out to be the
  same fix.

**832 blocks, one piece, 0 problems, 0 overlap, all cheap.** The stray-component check earned
its keep twice more in this pass: the inner toe at `hw - 3` had no neighbour, so both hands
shipped as three-cell strays.

### Rebuilt again, with `tools/look.py` (2026-08-28)

The whole animal up to this point had been judged from orthographic elevations and a plan, and
the 3-D pass proved that was not enough. Its own note said so before I looked: *"the haunch is a
flat-sided box with a hard vertical rear face, and the value panel shows it as one untouched
mid-grey rectangle - the jaguar's own failure, in a build that passes head-on."* It was right,
and the orbit sheet found more of the same at 45, 135 and 225 - the bearings an orthographic
tool cannot render at all.

**A CHAMFERED BOX IS STILL A CRATE.** Fixing the loft by going to boxes fixed the head and left
the body as three unarticulated slabs; what rounds a mass at voxel scale is a course-by-course
STEP, which is what the reference builds do and what a single dropped corner cell does not. The
generator has a `mass()` now - a stack of boxes, each course inset at the nose end, the tail end
or the outboard side - and it is what turns the haunch into a folded thigh and the rump into a
fall rather than a wall.

**AND THE STEP RATE IS A REAL PARAMETER.** At one inset every second course the taper reaches
nothing before the top on an animal only eight courses tall: the haunch shipped as a flat shelf
at half height with a single lone column standing on it, which every check passed. Every third
course rounds it and still arrives.

Four more things the 3-D views decided, none of which any flat render could have:

- **THE HAUNCH IS AS TALL AS THE HEAD.** Built at 0.80 of the skull height the rear was lower
  than the front all the way back, so the profile was a head on a loaf. A sitting frog is two
  masses of about one height with a dip between them, and that dip is the whole line.
- **THE EYE IS A DOME, NOT A PAD.** Two courses read as a gold plate on the corner of the skull
  from every bearing except head-on - which is exactly the view the flat sheets had been showing
  me. Three courses give it a top.
- **THE NOSTRILS WENT FROM BLACK TO THE MID TONE.** Two black cells on the brow between two black
  pupils read as a second pair of eyes head-on, and head-on is the only view that shows them.
- **The animal is 15 blocks and it does not hold up at 6x.** That is a fact about its size, not
  its shape, and the lot is what it is: a 22-block frog does not fit the flat ground east of the
  church at roll <= 1.

**1,029 blocks, one piece, 0 problems, 0 overlap, all cheap.** The working loop is now generate →
`look.py --sheet orbit` → change one thing → look again, and it costs about a second a pass.

### The frog, rebuilt from the reference's CONSTRUCTION (2026-08-28)

Jack, six times over one build: the eyes are obnoxious; don't love it; we are getting further
and further; still not like the reference; the eyes are giant; *"you are slipping and letting
this low quality pass when you should be auditing it more thoroughly than I am."* All fair. The
record of what went wrong is worth more than the frog.

**I KEPT REFINING MY FROG WITH THE REFERENCE'S FEATURES BOLTED ON, instead of reading how the
reference is BUILT.** Four references in the end, and the last one - Coldrobin's - is
unambiguous. The construction:

    ONE BIG BOX for the body, flat-fronted, haunches stepping down at the rear
    THE EYES ARE SEPARATE BOXES ON TOP: a flat LID in the body's own colour, and the box's
      FRONT FACE a BLACK BAND with a single bright block set in it at the inner end
    ONE HUGE PALE PANEL for mouth and belly together, ground up, about two thirds of the
      height, with a narrow tongue of body colour cut into its top - the upper lip
    FLAT FEET on the ground in a BRIGHTER tone, three toes FANNING from a pad

Every one of those is a shape, and I had built the wrong shape for each: a bright square in a
dark ring (four times, resized and recoloured every way and never once the right shape); a
mouth band, a dark line and a separate belly; and three parallel prongs of equal length at
equal spacing, which is a RAKE - nothing radiates, nothing tapers, and the eye reads a tool.

**THE PALETTE, matched by measurement.** The statue's body is mud brick; `mud_bricks`
(137,104,79) and `packed_mud` are both CURRENCY on this server, and `jungle_planks` (160,115,81)
is 23 RGB off the first and cheap. The saturated orange this build carried for four passes was
picked against the moss on LUMINANCE, and it is most of why it never looked like the reference.
Against moss (89,110,45) the new body is 80 apart in RGB - a full hue flip, which is what the
turtle proved carries on this floor. The ground test is colour DISTANCE now: measured the old
way it would have failed the reference's own palette and passed a green frog.

#### The audit I should have run before showing him anything

- **A LAMP THAT SILENTLY DID NOTHING.** Moved off a toe (where a white block reads as damage)
  and aimed at the pad at `face` - but the BODY owns that column at the ground course, so
  `paint` refused a cell that was never foot. No error, no lamp, sixteen cells over the toes
  still at block light zero. The pad is the course in FRONT of the body.
- **EYE BOXES HANGING OVER AIR.** 26 of 46 lid cells had nothing under them: the crown drew in a
  cell for rounding and the boxes that sit on it did not. The crown is the one place this mass
  stays square; its rounding belongs at the back corners, which it has.
- **HAUNCHES AS CRATES.** Two separate blocks of different widths standing off the flank - from
  behind, luggage. One mass per side, flush with the body, stepping down toward the rump. A
  haunch is not something you can see daylight behind.
- **THE PANEL RAN TO 80% OF THE HEIGHT**, leaving the head a narrow band above it.
- **ONE FLAT TONE OVER 1,300 CELLS** - the flattest surface in the build, against a reference
  whose brick varies across the mass. Patches of the mid tone now, on the flanks where they can
  be seen rather than only on the crown.
- **THE SNOUT TEST WAS READING THE BOUNDING BOX**, whose front plane is now two splayed toe
  tips. A test that reads the bounding box measures whatever sticks out furthest, which is not
  the question; it reads the pale panel's own plane now.


#### Three more shapes, after "overly square, the feet are random lines, the eyes are
strange giant boxes"

- **A FOOT IS A PAD WITH THE GAPS BETWEEN THE TOES.** Three one-cell prongs splayed wide with
  air between them are three strokes on the ground. Then a solid pad with its TIP CORNERS
  notched off is a PLUS SIGN, which is what a corner notch makes. The web runs the toes' whole
  length: pad first, then prongs.
- **A CHAMFER IS A RULE ABOUT AN EDGE, AND AN EDGE IS ONE AXIS AT A TIME.** The first attempt
  at rounding the box measured the distance from both ends at once and cut slots up the flanks.
  Every vertical arris and the top edge step in now - except the crown's FRONT edge, which
  stays square on purpose, because the eye boxes stand on it and rounding it away is exactly
  what left them hanging over air a pass earlier.
- **AND IT IS A LOAF, NOT A CUBE.** The reference is clearly deeper front-to-back than it is
  wide; at 15 deep against 13 wide mine was close to cubic, which is the other half of "overly
  square". 19 deep. Both that and the toe length come off `length`, so one number moved them.

#### The tests changed with the reference, deliberately

They pinned 1.0:0.75:0.5 and a knee, a haunch and a shin - the mob's proportions and my own
invented anatomy. **A test that pins a proportion is pinning a DECISION about which reference is
being copied**, so it has to change in the same commit or the suite quietly enforces the thing
that was rejected. They pin the CONSTRUCTION now: one pupil per eye set in a dark band under a
body-coloured lid, the boxes resting on the head, the panel continuous in height with a lip cut
into it. The next pass cannot drift back to a ring.

#### The blind alley, recorded because it was confidently wrong for three passes

The house and the mob both look like ONE MASS rather than an articulated head-waist-haunch, so I
rebuilt the animal as a single box on that reading. It came out a crate twice - as a plain
cuboid, and as a per-station taper, which insets every station independently and ribs the
flanks. **The error was taking the HOUSE as evidence about a creature**: it works because a big
box plus an eye band, a belly band and separate legs says frog-BUILDING. Two references agreeing
on a feature does not mean they agree for the same reason.

**1,584 blocks, one piece, 0 problems, 0 overlap, all cheap, sanctum clearance 4.** Still not
matched: the reference's body is BRICK with real texture across it and ours is plain planks in
flat colour, and `render3d` has no emission, so the pupils and the toe pads read dull in every
sheet here when in game they glow.

### The panel verdict, recorded (2026-08-28)

**Lofted build - FAILED, and Jack failed it before the panel did.** *A lumpy wedge; could be a
rock or a shrew.* Two measurable causes: the eye dome sat two courses UNDER the back line and the
knee three under it, so the only features that say frog were inside the outline.

**Box build - PASSES head-on and in plan, MARGINAL in profile.** Head-on it is unmistakable and
it is the view a frog is actually known by: a wide flat skull, two gold eyes bulging off the top
corners with black pupils, nostrils, a dark mouth line straight across, a pale chin under it. In
plan the eyes lead, the head is a clean box, the waist shows and the feet splay. The profile is
still the weakest - a low mass with a raised head and an eye bump, and at 17 blocks a stranger
might say toad. **If it has to read from the ruin path 40 blocks off it wants building at 1.5x**;
every number in the generator is a fraction of L, W or H, so that costs one line.

**Still open:** the frog defers 6 cells to `Lowland Thicket` (plant drifts inside its footprint),
so build the Thicket first - which is what `defer_to` records and what the build order derives.

### The last deep pass: BOXES WERE ALSO WRONG (2026-08-28)

Jack: *"still can be improved significantly, please audit in full and compare against
references, last deep visual pass across all angles to fix."* Rendered every bearing and the
review sheet, and the verdict was worse than the previous one recorded here - because the
previous verdict was taken from ORTHOGRAPHIC sheets and this one was not:

| | |
|---|---|
| profile silhouette | unnameable - a lumpy stepped box with a tab on it |
| value panel | one flat grey ZIGGURAT, four horizontal ledges, no rounding anywhere |
| plan | a rectangle: no waist, no head, the haunches two bolted-on crates |
| head-on | a pale rectangle between two sunglasses - **there was no mouth** |
| palette | 81% one block, 6% accent tail against the corpus median of 18.5% |

**THE FINDING, AND IT REVERSES THIS FILE'S OWN ADVICE ONE LEVEL DOWN.** Going from a loft to
BOXES was right about the head and the eyes and wrong about everything else, and each fix made
it worse in the same way. Four correct pieces of frog anatomy, four pieces of luggage:

    a haunch and a shoulder bolted on  ->  crates you could see daylight behind, four ledges a flank
    a waist dip two courses deep       ->  a head crate and a rump crate with a slot between them
    the haunch raised across the back  ->  a flat-topped box: a rucksack
    the knee raised at the flanks only ->  a rectangle floating above the outer wall

**AT THIRTEEN WIDE AND EIGHT COURSES TALL THERE IS NO RESOLUTION FOR ANATOMY.** Every feature is
one or two cells, and a one-cell step at this scale is not modelled form - it is THE SEAM BETWEEN
TWO OBJECTS. That is what the download corpus already said about exactly this scale and what this
file already recorded twice without applying it: a sculpture reads when it is **one convex mass
with a pattern on it** - the ladybird, `Warm Snooze`, and Coldrobin's frog, which is one
flat-fronted box and nothing else.

So: `col_top` is CONVEX and monotonic - the back line and the plan may rise to one peak and must
fall from there, never twice - and every frog cue moved into the COAT.
`test_the_mass_only_ever_falls_away_from_the_head` pins it, because the next person with a good
idea about anatomy will re-invent all four.

#### Two features were missing in every view, and no geometry substituted for either

- **THERE WAS NO MOUTH.** Five passes of eye work on a front that was a pale rectangle. A dark
  line across the panel that TURNS UP at the corners is what makes a blocky front read as a
  FACE, and it is the single biggest change in the whole rebuild. Graysun's statue draws
  exactly this and I had been reading it as a band rather than as a line.
- **THE EYE WAS BLACK ON ITS OUTER FACE**, so it existed in exactly ONE view: every bearing but
  head-on had two dark tabs and no eye at all. One iris cell on the outer face fixes the
  profile. And the front band needs TWO - the reference's single bright block is right at the
  scale it is drawn, but on a thirteen-wide head one cell in a four-cell band is a GLINT, and
  the orbit sheet read the pair as sunglasses.
- **AND THE MOUTH CARRIES ON ROUND THE JAW.** Drawn on the front plane alone it was a
  head-on-only feature; three cells back along each flank and the profile has a mouth too.

#### The coat, and the corpus number

Blotches are **DARK**, and that was measured wrong first: pale drifts read as WEAR - bleached
patches on the flank and dead centre of the rump. A real frog's markings are dark on a lighter
skin. Drifts have a **LOBED radius** (noise on the boundary, never on the cell - the thicket's
rule) and are painted only on cells with a face to the air, because a painted interior cell buys
a number and shows nobody anything.

Dominant block 81% -> 73%, and the value panel went from one untouched grey to a mass that
carries light. The accent tail is 8.9% against the corpus's 18.5%, and **it is not being chased
further**: this file already deleted "move a palette number" as a reason to put a block
anywhere, when the deck gallery and then the deck soffit both did it.

#### Four traps, each of which shipped a clean audit

- **A FROGLIGHT LANDED ON AN EYE.** The lamp's `over` list takes the body's own block and an eye
  box's LID is the body's own block, so it painted one white square in the middle of an eye. A
  lamp may not touch a column whose top stands above the body.
- **The lamps were read off `length`, not the body's own DEPTH.** `_f(0.88, 17)` is fifteen
  stations into a twelve-station body, so the late spots never landed at all and the pair meant
  for the hips ended up on the last course - tail-on, two pale squares side by side on a dark
  rump are a second pair of eyes.
- **Five lamps scattered on the back are a DICE-FIVE in plan**, and the loudest thing on the
  animal. Landed in the middle of a dark drift each one is a spot with a lit centre, which is a
  marking. (They are dull in every sheet here and glow in game - `render3d` has no emission.)
- **Five bands terraced where four do not.** Each of the last four stations stepped in and down
  by one and the rump came out as a flight of little ledges - which is the exact failure a
  coarse band table exists to prevent, reintroduced by making the bands narrow.

#### And three tests had to change in the same commit

They pinned a `haunch` part, a single pupil per eye, and a lip notch in the belly panel - all
three of which are decisions this pass reversed. **A test that pins a proportion or a part is
pinning a DECISION about which reference is being copied**, so it changes with the decision or
the suite quietly enforces the thing that was just rejected. This file has said that once
already, about the mob's proportions; it applies to a construction as much as to a ratio.

The monotonic test needed two corrections of its own, both instructive. Measured from the
BOUNDING BOX, station zero is a lamp in a toe pad and every animal fails - the body begins at
the pale panel's plane. And plain non-increasing was too strong: it failed the front corner's
own chamfer, which is a rounding of the mass and not a second object. The property wanted is
CONVEX - one peak - not monotonic.

#### And the eyes were a station too far forward

Jack, on the rebuilt animal: *"its eyes are pushed further vs the reference images which have it
set a block back."* Correct, and it is an error the whole rebuild inherited without questioning -
the boxes had overhung the front plane since the box build, where they were meant to read as a
brow. **A cell is a sixth of this head's depth.** Proud of the face they give the animal a jutting
brow with a shadow under it; the reference's eyes sit ON the head with their front in the SAME
PLANE as the face. Set back one station, the head-on view gains a clean brow course in front of
them and nothing else moves.

It also let a test get stronger: `test_the_eye_boxes_sit_on_the_head` tolerated half its lid cells
standing over nothing, because the overhang made that unavoidable. Flush, the answer is ZERO, and
that is what it pins now.

#### THE FEET ARE STAIRS, and the renderer could not see it

Jack, sending the Graysun statue back a third time: *"i think the feet still are crappy, this one
had feet done by using stairs."* That is the whole answer to four failed foot shapes, and I had
been re-arranging cubes instead of reading the material.

**A CUBE TOE ENDS. A STAIR TOE TAPERS.** A toe built of full blocks stops at a vertical face one
block high, which is a plate - and that is why every arrangement of them read as a rake, a comb, a
plus sign or a set of random lines however the prongs were spaced. Half height at the tip, sloping
to the ground, is what a toe actually does, and it is one block per toe.

It is also a gap the whole repo has and had already measured: against the download corpus we place
stairs at **0.64 per thousand cells against their 4.51** - seven times under - and this design had
none at all. `CLAUDE.md` listed "fences and trapdoors" as the biggest remaining vocabulary gaps and
put stairs on the *already-solved* side, because `gen/stairhead.py` uses them. One generator using
them for a staircase is not a vocabulary.

Two more things came out of the same note:

- **THE FEET BELONG AT THE BODY'S OUTER CORNERS.** At `bw - 2` they were inboard, tucked under the
  belly with a slot between them; the reference's sit at the foot of the arms with the whole pale
  front showing between them down to the ground.
- **THE ANKLE RISES TWO COURSES and steps down to the pad**, so the foot has something to taper
  FROM. Flat on the ground at one course there is no fall to describe, and the reference's feet are
  plainly two blocks at the heel and one at the toes.

Four stations deep and no more. At five - three toes two cells long - they read beautifully close
up and **took over the head-on view**: 38% of a thirteen-deep animal's length was foot. The taper
does the work the length was trying to.

#### `render3d` now draws stairs and slabs at their real shape

**THE FEET WERE REBUILT WITH STAIRS AND EVERY SHEET HERE DREW THEM AS FULL CUBES.** The change was
unjudgeable - which is the same failure as rendering an animal orthographically along its own axis,
the one this file already records: *the tool cannot show the class of error being hunted*. Shipping
a change nobody can look at is how the axolotl's head happened.

`render3d.subdivide` expands every block to **2x2x2 half-cells** and fills them from the block's
shape: a slab is four, a stair is six, everything else is eight. Nothing in the raycaster changed -
it still marches a boolean grid - so this cost about forty lines and roughly 2x the march, which on
an animal is tenths of a second.

- **Applied only to models that actually contain a shape block.** AO is computed on the half-cell
  grid, so it is finer, and the image genuinely moves; applied to everything it would silently
  shift every sheet in the repo. Six of the eight animals contain no shape block and render
  bit-identically. `look.py --no-shapes` is the way back.
- **AFTER the scale figure**, or the player marker subdivides separately and stops being 2 blocks
  tall.
- **The stair convention is the load-bearing part and a picture cannot check it.** A stair's TALL
  side is its `facing`; until now this renderer drew both directions identically, so a backwards
  flight and a correct one produced the same image. `tests/test_render3d_shapes.py` pins the mask
  per facing, and `test_the_toes_taper_and_they_lean_the_right_way` pins the frog's own toes -
  which lean BACK toward the body, because a toe tapers down and forward.

**This corrects a claim in this file.** It said real block models "buy almost nothing for ANIMALS,
which are near-100% full cubes". That was true only while no animal used a shape block; the moment
one did it was wrong, and it was the reason the gap went unfixed.

#### A HAND IS MOSTLY AIR

Jack, on the first stair version: *"hands are now really thick and strange, how do we make the
replica which is a bit more refined and feels cleaner."* They were - **twenty cells apiece, and
solid**: a 3x2 pad, a five-wide web laid over it, and a two-course ankle behind that. Three courses
of stacked mass with a taper stuck on the front is a boot with claws.

The reference's hands are the opposite thing. They are almost entirely **NEGATIVE SPACE** - a flat
wrist ONE course deep and ONE station deep, and thin toes with a clear cell of air between them.
Eleven cells, and nothing stacked on anything except where the wrist meets the body.

**The gaps are the feature.** That is the same rule as the eye pair needing a clear cell between
them, and the ladybird's spots needing four courses of spacing rather than three - and filling them
in to make the shape read stronger is the same mistake, made a fifth time. Adding the stairs was
right and it was not enough on its own, because a taper on the front of a solid lump still leaves
a solid lump.

The animal is 16 long now rather than 17, and the church clearance went 4 -> 5.

##### The wrist light: three candidates, and the economy picked

The hands need their own light and that is MEASURED, not assumed - `hand_lamp: false` and six
cells over them stand at block light zero, because the back lamps are seven courses up and five
forward and light does not turn corners.

But `ochre_froglight` is 209 RGB from `acacia_planks`, so at the hand's leading edge it read
head-on as a pale CHIP knocked out of the toe. Measured against the foot:

| | ΔRGB | tier | |
|---|---|---|---|
| `glowstone` | 53 | **expensive** | |
| `jack_o_lantern` | 46 | cheap | a FACE texture - the `bee_nest` trap |
| `shroomlight` | 95 | **expensive** | the right block on any other economy |
| `ochre_froglight` | 209 | cheap | what we have |

Two expensive blocks for a cosmetic is not a trade this design makes, so the fix is PLACEMENT: the
wrist's inner corner, shaded by the body's own front, which is the least-read cell of the hand.

**And a light must keep AIR OVER IT.** Tucking it under the wrist's rise would have switched it
off - light travels through air, and a lamp walled in by its own foot lights nothing at all.

**1,278 blocks, one piece, 0 problems, 0 overlap in context, all cheap, 16/16 frog + 9 renderer.**


### IT IS UPRIGHT, and the rule that stopped it being so was mine (2026-08-29)

Jack, on the finished loaf: *"no, this isnt good, i need you to really think about this, and
audit carefully, visually this sucks."* He was right, and the audit found something bigger than
the frog.

**THIS FILE STATES, IN CAPITALS, THAT A SCULPTURE AT THIS SCALE MUST BE ONE CONVEX MASS WITH A
PATTERN ON IT. That is a SCALE law and it was written down as a universal one.** It was measured
at eight courses of body height, where every feature is one or two cells and a one-cell step is
not modelled form but the seam between two objects. The reference does not delete the anatomy -
it makes the animal TALL ENOUGH TO HOLD IT. At twenty-two courses a head is seven cells, an arm
fourteen, a haunch five: those are masses.

And the evidence was already in this file. *"It came out a crate twice"* is recorded here about
the two earlier one-mass builds; the third was called a crate by Jack. **A rule that produces a
crate three times running is the rule that is wrong**, not the execution.

The lot was re-measured before anything was drawn: **15x13 is the largest pad at roll <= 1 and it
carries 107 COURSES OF HEADROOM.** Height was always free here; the footprint was the only
constraint, and the loaf was using 12 of the 107.

#### Four things the rebuild got wrong first, each a general lesson

- **UPRIGHT IS NOT THE SAME AS TALL.** The first attempt was a twenty-six course column with a
  head at 15% of the height: a gravestone with a frog on top. Measured off the picture the head
  and eyes are about **40%** of the total and the body below is **wider than it is tall**. A
  statue is not a measurement of an animal.
- **A PALE RECTANGLE INSET IN A DARKER FRAME IS A DOOR.** Four passes went into making the mass
  squatter, tapering it, darkening the arms and shortening the torso, and the front stayed
  architecture until the BELLY ITSELF stopped being a rectangle. It is a lens now - widest at
  the middle, closing top and bottom. The straight line is what says architecture; the curve is
  what says creature.
- **THE HEAD MUST BE SHORT FRONT-TO-BACK.** Given the body's own depth, the whole rear was one
  flat wall from crown to ground and the profile read as a BOOT. A sitting frog is head forward
  and high, rump back and low: the head is the shallowest band and the haunches the deepest.
- **THE ARMS HANG IN FRONT OF THE CHEST, not out at its sides.** Beside the body they are
  swallowed by the haunches, which are wider - the first pass had arms visible over six courses
  out of twenty-four. They also follow the body's own outline, because at a fixed offset they
  filled the waist back out and HID the pinch: the body read as a straight-sided box because its
  own silhouette was covered by its arms.

#### The relief pass: every hard step gets a stair

The last gap the corpus measured, and it was not close - outside sculpture runs about **17%
detail blocks** and this animal ran **0.5%**. Every plane met the next at a hard right angle,
which is what makes a voxel mass read as a crate however well it is proportioned, and it is why
the reference looks like carved stone and ours looked like a box.

The rule is general and places no cell by hand: **wherever a course steps IN, the shelf it leaves
takes a stair leaning into the wall above it; wherever it steps OUT, the overhang takes an
upside-down stair tucked under it.** Every hard ledge becomes a cove. `shell.py` has done exactly
this for years and was never pointed at an animal.

- **Only the skin, and only single steps.** The face, the belly, the eyes and the feet are drawn
  features and a stair through one of them is a hole in a drawing; and a stair cut into a
  two-course jump leaves a gap rather than a chamfer.
- **The relief is the body's OWN material.** A chamfer is geometry; a stair in a different tone
  is a stripe.
- **It found that the head was the flattest thing left**, because a band of constant width has
  no step to chamfer. Giving the crown a one-cell draw-in put relief on the head - and the eye
  pair had to narrow from five cells to four to keep every lid over solid crown, which is the
  third time on this animal that a box has been caught standing over air.

#### And two colour findings

- **`bone_block` alone reads cool grey** next to a warm body - 21 apart in R minus B where birch
  is 71. The belly is two tones now: the bright core, and a warmer birch rim that stops the oval
  reading as a cut-out pasted on the chest.
- **`chiseled_sandstone` measures better than either and is NOT WITNESSED anywhere in this
  world.** The tier table calls it cheap, which is a gap in the TABLE, not evidence the server
  can supply it - and this file already recorded "sandstone does not exist on this skyblock".
  Rule 12 from a new direction: ask the world, not the table.

#### And then the legs and feet, which were three faults in one

Jack: *"we're much closer with the frog but the legs/feet arent right."* A close look at the
bottom found three, and the first is the one worth keeping:

- **THE HANDS AND THE HIND FEET HAD MERGED INTO ONE L-SHAPED PLATE** round each front corner,
  and the animal read as standing on a PLINTH rather than on four feet. Both were correct on
  their own; they simply ran to the same stations. The separation has to be in DEPTH, not in
  width - the hands live in front of the body's face, the hind feet start behind it, and the
  arm's own station is the clear course between them.
- **A HAND IS MOSTLY AIR, and it was two solid courses.** A wrist row and a web row under three
  toe stubs is a flat PLATE with notches in its front edge, which is what four foot shapes on
  the loaf were as well. One course of wrist and three toes with a clear cell between them is
  eleven cells and reads as a webbed hand.
- **THE LOW LIGHT GOES ON THE HOCK, NOT IN THE HAND.** The hands genuinely need lighting -
  without it the air over them measures block light ZERO, because the body's lamps are high on
  the back and light does not turn corners - but a cream froglight set in an acacia wrist is a
  pale CHIP, and at the bottom of the animal it was the loudest thing on it. Moved to the
  haunch's outer face a course off the ground it is a lit spot on a flank; it still reaches the
  hand round the corner, because light floods air and needs no line of sight, and it lights the
  hind foot on the way.

#### One side was lumpier than the other, and the mass was symmetric by construction

Jack read it straight off the render, and he was right: **104 of 1,615 cells differed across the
sagittal plane.** Every part of this animal is built for `s in (1, -1)` and every span is centred,
so construction was never the problem. Two other things were:

- **THE COAT'S DRIFTS EACH CARRIED THEIR OWN SIGNED OFFSET**, so the dark blotches landed in
  different places left and right. **A dark patch reads as a RECESS**, which is exactly why an
  unmirrored coat looks like a body dented down one side rather than like markings. A real frog's
  blotches are not symmetric; a STATUE of one is, the reference is, and the rubric has a whole
  dimension for this that allows asymmetry only where it was deliberately asked for.
- **`put` REFUSES A CELL THE TERRAIN OWNS**, and this lot rolls a course, so a foot cell existed
  on one side and not the other. One cell - it only takes one. The mirror is ENFORCED now rather
  than assumed, and dropping is the only safe direction: the missing cell is missing because
  something real is already there.

**And a facing MIRRORS, it does not COPY.** Written the obvious way the sweep assigned each cell's
state verbatim to its twin and **60 of the 134 stairs came out facing the same way on both sides** -
a chamfer leaning into the wall on one flank and out of it on the other. Only the ACROSS axis flips;
a stair leaning fore or aft leans the same way both sides. **`render3d` had learned to draw a stair
as anything but a cube the same day**, so a day earlier this would have been invisible in every
sheet here and wrong in game for ever. That is the second defect the sub-block renderer has caught
in one session, and it is the argument for having built it.

**AND THE SKIRT WAS THE REST OF IT, which the first fix explicitly waived.** It fills each column
down to its own ground; the ground under this site rolled THREE courses; and **all 34 of its
columns came out on one flank**, in the body's own dark tone. That is a fringe hanging off one set
of feet, and it is what Jack saw the second time.

A fill CANNOT be mirrored downward - `put` refuses a cell the terrain owns, so the high side can
never be given what the low side needs, and equalising the other way leaves the low side floating.
Two things could be fixed and both were:

- **RESEATED on the flattest ground the lot allows.** A search over every placement of the real
  13x15 footprint that still clears the church by 3 found roll **2** at (-24169, 29976) - 161 of
  195 columns at Y39. There is no roll-0 site: the lot has none for a footprint this size.
- **EVERY FILL CELL TAKES THE MATERIAL OF THE CELL IT CARRIES.** Built as a proper base in the
  church's own `polished_blackstone_bricks` it put a black post under every separate toe and the
  animal looked like it was wearing BOOTS - **a plinth that follows the outline of a splayed foot
  is not a plinth, it is a shadow.** Matched to what it carries, the fill reads as the toe
  REACHING the ground, which is what it is.

**42 unmirrored cells down to 23, all below the belly plane, all colour-matched.** Zero at or
above it, geometry and colour, and the test now bounds the fill as well as forbidding the rest.

**1,614 blocks, one piece, 0 problems, 0 overlap in context, all cheap, 18/18 - and 0 geometry and
0 colour mismatches across the mirror above the belly plane.** Five tests
changed with the decision - they pinned h/w 0.55-0.92, a monotonic mass, gold-in-black eyes, a
rectangular panel and one-way stairs, and every one of those is a thing this pass reversed. One
of them was measuring the CHIN rather than the belly, because the head's front plane stands
forward of the chest's and `min(along)` picks the wrong plane.

## The Island Line: a minecart spiral, deck to lowland (2026-08-28)

`configs/rail_spiral.yaml`, `mcbuild/gen/railspiral.py` - **3,300 blocks, 673 track cells, 0
problems, 0 overlap, one component, all cheap-or-ok, 1 dig cell.** Jack: delete the connecting
train tracks, run a spiral all the way down to the lowlands that can also return, and use MORE
POWERED RAILS THAN NORMAL ONES because of iron costs.

### The iron premise is right and the reason is inverted

    rail          6 iron -> 16 rails    0.375 iron each      iron_ingot  90 in store
    powered_rail  6 gold ->  6 rails    1.0   gold each      gold       ~62, and FARMABLE

A powered rail is ~7x a normal one in ingots, so the obvious reading is that powered rail is the
expensive one - which is what I told Jack first, and it was wrong about this server. Gold is easy
here and iron is not, so **the cheap rail is the gold one**. Lay powered rail everywhere and spend
iron only where the game refuses.

**IT REFUSES AT CORNERS, and that is the fact the whole design turns on.** Off `blocks.json`
rather than off memory:

    powered_rail  shape = north_south, east_west, ascending_{n,s,e,w}
    rail          shape = ...those six, PLUS south_east, south_west, north_west, north_east

A POWERED RAIL CANNOT CURVE. So every direction change is iron, and **the plan shape of the spiral
becomes an iron decision rather than an aesthetic one**. At r=30 a square lap turns 4 times; a
rasterised circle turns 60. Round is fifteen times the iron - more than is in store. Hence a square
helix: four straight flights a lap with a landing at each corner, which is the void tower's rule
again (regularity and openings, not curves).

The shipped line is **11 corner rails, ~4 iron**. The whole railway's iron cost is four ingots.

### The first radius sweep asked the wrong question, and Jack caught the result

I scored whether the whole RING was clear at each course, concluded r=12 was the only workable
radius and everything wider was 105-152 courses blocked. Jack: *"this doesnt make sense, it should
be a much wider circle than the small staircase, these are separate things."*

He was right and the sweep was what was wrong. **A helix occupies ONE CELL PER COURSE, not the
ring** - a blocked ring only means the helix must arrive at a different PHASE. That is the same
start-angle sweep `Lowland Stair` already documents, and I did not run it. Swept over centre,
radius and phase together, wide radii are fine: r=30 at (-24206, 30014) threads the whole descent
and stands **15 clear of the stair's outer edge** instead of 3.

Wider is not better past that, and both limits are measured:

| r | turns | ride | under island | to the deck rail head |
|---|---|---|---|---|
| 12 | 6.3 | 76s | 70% | 28 - and 3 from the stair: one tangled column |
| **30** | **2.8** | **~84s** | **70%** | **43** |
| 36 | 3.1 | 113s | **42%** | **85** |

At r=36 most of the ride is a viaduct in open sky rather than one threading the island's underside,
and the boarding platform ends up 85 blocks from the deck.

### Five things that shipped a clean audit and a broken railway

Every one of these passed `problems: 0`, `overlap 0` and a correct BOM. The audit can only see that
a design is one connected solid; it has no idea what a rail is *for*.

- **NEVER DESCEND INTO A CORNER.** A curve has no ascending shape either, so a corner and both its
  neighbours must share one height - drop into one and the game re-derives the turn as a slope, the
  turn is lost and the line dead-ends. Invisible in the model, because `shape` is DERIVED (it is
  not in `work.INTENTIONAL`, exactly as a stair's is not). The grade skips the cell before a corner
  as well as the corner itself.
- **AN UNPOWERED POWERED_RAIL IS A BRAKE**, so every one has to carry signal - a `redstone_block`
  in the bed every 8 cells. And the runs are counted **between corners**, because a normal rail
  does not propagate the chain: a flat spacing leaves a dead rail past every turn, and a dead rail
  is a cart that stops in mid-air a hundred blocks up.
- **A TRACK CELL IS NOT OPTIONAL.** The first build let two track cells yield to other designs and
  shipped 0 problems, 0 overlap and **three components** - the audit caught it only because a
  broken line happens also to be a broken solid. Structural cells are now fatal-or-claimed and
  never silently skipped: anything the WORLD holds is an error naming the cell, a cell only an
  unbuilt DESIGN claims is taken and reported (nothing old is live on this island).
- **THE LINE MUST END ON GROUND.** Ending at a fixed `y_bottom` put the terminus in the ONE 33-cell
  stretch of the ring with no floor under it - a platform 43 blocks over open void that you step
  out of the cart and fall off. 185 of the 240 ring columns have lowland floor and 55 do not, so
  the line asks: it descends only where there is something to descend toward, holds level over
  void, and lands the moment floor comes back under it.
- **A TERMINUS NEEDS A STOP BLOCK.** A stationary cart on a powered rail launches AWAY from the
  adjacent solid block. Written with the indices inverted it placed neither, silently, and the line
  would have run only whichever way you happened to shove the cart.

And two of the repo's standing traps, both hit again:

- **`dict.get(x, z)` reads `z` as the DEFAULT**, so the tuple-keyed ground table returned a Z
  coordinate as a height and the route terminated on its first cell.
- **A fixture that belongs BESIDE a thing must be excluded from the thing by construction.** The
  perpendicular flips through a corner, so the dressing offset walked back onto the line and stood
  a lantern on a powered rail - the frog's "the eye sits over the hind foot in plan" in a hard hat.

### The lighting was ten times the metal of the railway

58 lanterns came to **~52 iron** against the eleven corner rails' 4. On the island whose scarce
metal is iron, the lights cost more than the line. **61 ochre froglights set flush INTO the deck
edge** cost none, use the idiom this island already lights itself with (Island Night, the lowland
turf), cannot be knocked off a walkway 150 blocks up, and leave the 3-wide deck clear to walk. A
flush froglight reaches 14, not 15 - it IS the floor, an opaque emitter a course down - and the
spacing is set against that.

The stone still carries the Lowland Stair's gradient (island stone brick, deepslate, the quarter's
blackstone) so the two read as one hand. **The light does not go cold with it**: verdant and
pearlescent froglight stock is zero and soul lanterns are iron. One tone, stated in the config.

### What it costs, and what is still open

The only real purchase is **518 powered rails = 518 gold**; stone brick, blackstone brick and
deepslate brick wall all craft from stock, and 2,251 of the 3,300 blocks are already in containers.

- **The existing east line is KEPT, not deleted.** Its 104 cells run deck -> east lobes -> bee
  house and the spiral is affordable without salvaging them.
- **THE DECK SPUR IS NOT BUILT, AND THE TOP STATION FLOATS.** The top terminus stands at
  (-24231, 192, 29984): **43 blocks** from the deck rail head at (-24197, 192, 29993), and the
  nearest island block of ANY kind is 22 away. **128 design cells sit at Y>=186 and not one of them
  touches the island** - so the line is complete, printable (it builds upward off its own chain from
  the lowland end) and not reachable on foot. Until the spur is built you can ride UP to the top
  station and be stranded there. That junction is the next piece of work; it crosses the busiest
  part of the deck, which is why it was not guessed at here.
- **The ~1-in-8 power spacing and the corner deceleration are the two numbers still unverified.**
  Everything else here is read off the registry or measured off a capture; these are reasoned. A
  24-block test ramp with one corner answers both before 518 gold is committed.

`tests/test_railspiral.py` (18) pins all of it: the registry fact about curves, corners flat on both
sides, slopes ascending toward the higher neighbour, every run powered at both ends and never past
the spacing, no source wasted on a corner, inside the plot, clear of the stair, the terminus on real
ground with a stop block, nothing standing on the track, one piece, no iron-cost lights, and that a
blocked track cell RAISES rather than leaving a gap.

## The skyblock pass: cost, craft, income, boundary, void, warps (2026-08-30)

The mod knew WHERE everything is and HOW to build it. It could not say what anything COSTS or
whether you can MAKE it — and on a server where nothing is mined those are the only two questions.
Six features, all shipped, plus a backup, plus `chunkscan 0.4.0`.

| | |
|---|---|
| `python -m mcbuild craft <design>` · `/cscan craft` | resolve a design to RAW materials against your containers |
| `/cscan prices on` | read the server's own shop prices while you browse it |
| `/cscan income` | production per hour, from the container index over time |
| `/cscan plot` | the 99x99 boundary, and a warning when a fill crosses it |
| `/cscan dig` | now warns when what you break falls into the void |
| `/cscan warp add` | teleports as a routing primitive, not only as a fall rescue |
| `python -m mcbuild backup` | a full VERIFIED rotated backup, and it runs inside `sync` |

### The BOM stopped at the block, and the recipes were in the jar the whole time

**1,585 recipe files and 191 item tags sit inside `minecraft-client.jar`**, under
`data/minecraft/recipe/` (singular in 26.x — it was `recipes/` up to 1.20) and
`data/minecraft/tags/item/`. That is the same jar `tools/extract_blocks.py` already opens for
textures, so `tools/extract_recipes.py` needed no datagen run and no new dependency. Rule 11 — ask
the game, not your memory — had never been applied to what a block is MADE of.

`mcbuild/recipes.py` and `Recipes.java` resolve a want-list down to raw materials against the
container index. **Four traps, and every one of them shipped a plausible wrong answer first:**

- **PACKING RECIPES ARE ARBITRAGE, NOT ROUTES.** Costing every leaf at one unit makes
  `raw_gold_block` a *cheaper* source of raw gold than raw gold is, because one item becomes nine
  for free. The first resolver answered "518 powered rails" with "unpack 58 gold blocks" — blocks
  nobody owns — and **the cycle guard did not catch it, because a cycle guard stops the recursion,
  not the arithmetic.** Packing recipes are barred from costing and offered only against stock you
  actually hold, where they are exactly right: a chest of gold blocks is nine times the metal and
  no trip.
- **CRAFTING IS NOT ALWAYS THE ANSWER.** A recipe that costs the same as the thing it makes is a
  wash, and following it anyway sends you shopping for its ingredients instead: the second version
  answered the same question with "smelt 522 deepslate gold ore", which is not a material any chest
  on this island has ever held. Craft when it is genuinely cheaper, or when you already hold an
  ingredient; otherwise report the ITEM short, which is the thing you would go and buy.
- **THE ALLOWLIST HOLDS BLOCKS, AND MOST INGREDIENTS ARE ITEMS.** `blocks.available("gold_ingot")`
  is False — not because the server lacks gold but because a list of BLOCKS has nothing to say
  about an item. Applied blind it priced every ingot 50x a block and sent the resolver mining. This
  is rule 11's `NOT_FULL` holding `"grass"` in a new costume: one list, asked the wrong question.
- **AN ALTERNATIVES LIST IS RESOLVED BY WHAT YOU HAVE.** A stick takes any of fourteen planks and a
  torch takes coal or charcoal. Picking the first in the file sends you out for oak while 3,000
  jungle planks sit in a chest.

**And the stonecutter wins on its own merits.** Crafting stairs is 6 blocks for 4; cutting is 1 for
1. Costing per OUTPUT unit gets that for free rather than special-casing it — over a design that is
a third of the stone.

**The two resolvers drifted the moment they existed, and the fix is the repo's own rule.** The
`reversible` flag was computed at Python load time, so the exported JSON carried no flag and the
Java port happily priced a gold block as cheap gold — the same shape as `proportions.measure` and
`rubric.score` needing one entry point. It is written into `recipes.json` by the EXTRACTOR now, so
both languages read one source, and `SkyblockTest.theJavaAnswerMatchesThePython` pins three cases
that `tests/test_recipes.py` asserts identically.

Measured, against the live index: `Rail Spiral` resolves to **289 gold ingots short** and everything
else already owned; 58 lanterns are fully craftable from iron already in the hall; 2,000 terracotta
is 1,968 clay short — which is the clay-farm conversation, answered by the tool instead of by hand.

### Prices: the tier table was invented and the server has real numbers

`palette.tier()` sorts the whole registry into cheap/ok/expensive with prices noted in a COMMENT
("terracotta, 10 grass each"). Every palette this project has picked rests on it.

**A shop menu IS a container screen**, which is why this was cheap: `ContainerWatcher` already
hooks `ScreenEvents` and walks `menu.slots`. The price is not in the item, it is in the item's
LORE, as text a human reads — so `Prices.java` is a text scraper and is honest about it:

- **a slot with no readable price is skipped and counted, never defaulted to zero** — a missing
  price must never read as "free", which is how a palette picker learns to love the one block
  nobody can afford;
- **buy and sell are kept apart**, because costing a build with a sell price understates it by the
  spread, which on most servers is most of the price;
- **a price is per ITEM, not per stack** — a menu offering 64 for 320 is 5 each, and recording 320
  makes stone look like quartz;
- **it never opens a menu by itself.** You walk the shop; this reads what you look at. Automating a
  shop walk is a trading bot, which is a different thing.

Written to `schematics/prices.json` — beside the storage index rather than baked into the jar,
because these change when the SERVER changes. That is the same test that put the rules and the
recipes IN the jar and `designs.json` outside it.

### Income: "289 short" is a different sentence depending on the farm

The container index is a snapshot of everything you own; a series of them is a rate, and nothing had
ever kept the series. `Income.java` samples on demand and `/cscan craft` now prints
`~7.2h of production` beside a shortfall that something is actually making.

Three rules, two of which are ways to report a farm that does not exist:

- **A snapshot is only evidence for containers you OPENED.** A total that rises because you finally
  looked in the gold chest is not production; every sample records its container count and a
  comparison across a different set says so instead of dividing.
- **Spending is not negative income.** Taking 500 bricks out to build with looks exactly like a farm
  running backwards, so rises and falls are reported separately.
- **Two samples ten minutes apart is a rate; two a minute apart is noise**, and below that the pair
  is not divided at all.

Capped at 240 samples: this is a rate meter, not an archive, and the scans folder has already been
an unbounded-growth bug once.

### The plot, the void, and the warps

- **THE PLOT IS 99x99 AND THE MOD COULD NOT SEE IT.** `mcbuild/plot.py` derived it from the island's
  own bedrock and only the generators consulted it, so the Island Run shipped 120 cells over the
  line and a HUMAN caught it. The bounds now ride in `chunkscan_rules.json` with everything else and
  `/cscan fill` warns when a box crosses them. **NOT FOUND is not the same as INSIDE** — with no
  bedrock in any capture every check answers "I cannot say" rather than "fine", because a boundary
  guard that silently passes everything is the failure it exists to prevent wearing the opposite hat.
- **BREAKING A BLOCK OVER THE VOID LOSES THE DROP** — not scattered, not despawned in five minutes,
  gone the moment it passes the bottom of the world. `Falls` lists 41 dig cells and some are a
  hundred blocks up, and `/cscan dig` walked you there in silence. `VoidRisk` searches DOWN to the
  world floor (an item falls until something stops it), demands a **solid** catch — vine and grass
  do not stop an item, and this file has been bitten twice by "not air" read as "solid" — and treats
  an unloaded column as UNKNOWN rather than as void, or the whole lowland reads as a hazard from the
  deck.
- **WARPS ARE A ROUTING PRIMITIVE.** `Autopilot` already types `/is`, but only when falling; using
  the same command because it is SHORTER is the same call in a different place and was never made.
  The one thing that makes it work: **a warp is recorded by standing where it DROPS you**, so the
  saving is measured against an observed position rather than an assumed one. Under 80 blocks saved
  it is theatre and is not offered.

### The backup, because none of this was backed up

Three stores hold the island and only one is in git: the repo, the **schematics folder** (18 MB, not
in git, and the only copy of every capture ever taken), and the game dir. `sync` regenerates designs
from configs; it cannot regenerate a CAPTURE, because a capture is a photograph of a world that has
moved on.

`python -m mcbuild backup` writes a working-tree zip, a `git bundle` of all history, and a zip of
the schematics — **29 MB, five seconds, 1,486 files.** It runs at the end of `sync` (the moment a new
scan exists is the moment worth backing up) and a Windows task `mctest-backup` fires it daily at
03:30. `$MCTEST_BACKUP_DIR` points it at OneDrive or a second drive and the same command becomes an
offsite backup.

Four rules, each of which is the difference between a backup and a folder of hope:

- **A BACKUP THAT IS NOT VERIFIED IS NOT A BACKUP.** Every archive is re-opened and CRC-walked and
  the bundle is handed to `git bundle verify`. A write that failed halfway still produces a valid
  zip — with fewer entries in it.
- **NOTHING IS PRUNED BEFORE THE NEW ONE VERIFIES**, never below one, and never a FAILED backup:
  that one is the evidence of what went wrong.
- **THE DESTINATION MUST BE OUTSIDE EVERYTHING IT COPIES**, or each run archives the last one and the
  size doubles daily with nothing to say why.
- **HISTORY IS A BUNDLE, NOT A COPY OF `.git`** — copying an object store while a gc runs copies a
  torn one.

### And the command sheet caught itself going stale, as designed

`MenuTest` failed the moment the six commands existed, which is its whole job. Fixing it made it
stronger rather than looser: `offered()` read only the FIRST word of a row, so `/cscan income sample`
did not count as offering `sample` and every real sub-verb had to go in the exemption list — the one
thing that test's own comment calls its weak point. It reads the whole command string now, so the
exemption shrank instead of growing.

### Still open

- **`tests/test_designs.py::test_all_configs` fails on `shop_islet.yaml`** (`short_grass on
  cobblestone`). PRE-EXISTING — it fails with this session's Python changes stashed, and comes in
  with the newer `observed.json` already in the tree. Not this pass's to fix.
- **`prices.json` is empty until someone walks the shop.** The scraper's patterns are written
  against the common lore shapes and have never met skyblock.net's actual menu; expect one round of
  pattern tuning, and `/cscan prices` reports how many slots it could not read so you can tell.
- **The 1.19 recipe question is open the same way the block allowlist is.** These are 26.2 recipes
  and a skyblock server may customise them. Provisional; report, never refuse.

## The automation pass: the mod places its own blocks (2026-08-30, chunkscan 0.4.0)

Four more, off the back of Jack confirming automation is allowed on skyblock.net.

| | |
|---|---|
| `/cscan print <design>` | place the design OURSELVES, and verify every block landed |
| `/cscan make <item> <n>` | craft it, with a crafting screen open |
| `mcbuild cheapen --by-price` | palette by the shop's real prices, not the invented tier table |
| `tools/timelapse.py` | the island being built, from the captures you already took |

### The printer, and the signal this loop has never had

This file said, as a technical fact, that *"a client mod cannot place a block, and should not"*.
**Only the second half was ever true**, and it was a statement about server rules rather than about
the client — litematica-printer places blocks from a client exactly as `Printer.java` now does.

**THE POINT IS NOT SPEED, IT IS FEEDBACK.** Delegating placement left the loop with no signal at
all — this file's own words: *"the printer never reports back, so `todo` shrinking is the only
honest evidence a block was placed"* — and FOUR stall clocks, an abandoned-station set, a
thrashing detector and a whole recovery ladder exist to paper over that silence. A placement made
here is read back off the world a few ticks later, so the loop finally knows the difference between
*it did not work* and *I have not looked yet*.

**Placement and verification are separated by ticks on purpose.** The server has to answer first;
reading the same cell in the same tick would report every placement as a failure.

Three things it has to get right, and the first is the one a picture cannot check:

- **THE STATE IS VERIFIED, NOT ASSUMED.** `facing` comes from where the player is LOOKING at the
  moment of placement and `half`/`type` from where in the clicked face the hit landed — so both are
  computed and the look angle is set before the click. A stair aimed the obvious way comes out
  BACKWARDS (the game derives a stair's facing as the player's own direction reversed), and **our
  renderer draws both directions identically**, which is why `PrinterTest` asserts the yaw table
  rather than anyone eyeballing a flight. A cell whose block is right and whose state is wrong is
  reported as a MISMATCH and never counted as built.
- **It never breaks anything.** Placement goes into air only; `Rules` and the 99×99 `Plot` still
  apply. Replacing stays a separate, explicit job with its own dig list, because breaking the wrong
  block on a lived-in island is the one mistake with no undo.
- **A cell that fails twice is left alone and reported** — `Ignored`'s rule for places, applied to
  cells. One failure is a bad moment; two is a property of the cell.

It uses what is in your **hotbar**, because that is what a click places, and says so once per
material rather than once per tick.

### `/cscan make`, and the data that could not craft

`craft` said *"craft 87x powered_rail from 522 gold, 87 sticks, 87 redstone"* and then left you
clicking for twenty minutes.

**THE GRID IS THE WHOLE DIFFICULTY AND THE COST DATA DID NOT HAVE IT.** `needs` is an aggregate —
six stone bricks — which is everything a COST needs and not enough to CRAFT: six bricks anywhere in
the grid do not make stairs. The extractor keeps the real 3×3 layout now, for **1,056 of the 1,524
recipes**, anchored top-left where the game matches a shaped recipe from.

`Crafter` drives the screen the way `Withdraw` drives a chest — a state machine, because opening a
menu is not synchronous. Four rules: one craft at a time with the result read back; **shift-click
the result, never pick it up** (`QUICK_MOVE` crafts everything the grid can make and puts it away,
where picking it up leaves it on the cursor); the grid is emptied back to you first, because what
somebody left in it is not ours to consume; and a missing ingredient stops the round and names it.

**Stonecutting and smelting are deliberately NOT done here and are REPORTED rather than skipped.** A
stonecutter is one button and a furnace is two slots and a wait; both are worth having and neither
is this state machine. A stopped-early craft that reports success is the "does nothing, quietly"
failure this file keeps writing rules about.

### Palette by price

`mcbuild cheapen --by-price` asks the shop instead of the tier table: *of the blocks that would
still look right, which is the least money.* **THE TOLERANCE IS THE WHOLE DESIGN** — nearest-by-
colour ignores cost, cheapest-overall ignores the build, and 30 is about the gap this file already
calls invisible (`light_gray_concrete` → `stone` is 11, `gray_concrete` → `gray_wool` is 15).

Two refusals matter more than the feature:

- **It does nothing without a price book.** Falling back to the tier table would make `--by-price`
  a synonym for `cheapen` that merely sounds better informed, and you would never learn the shop
  had not been walked.
- **It only moves for a REAL, PRICED saving.** Swapping one unpriced block for another unpriced one
  is churn dressed as economy, and it changes how the build looks for nothing.

`face` defaults to **side**, not top: a statue is read in elevation, 155 blocks differ between their
two faces, and the top-face default is right for a floor and wrong for everything this is pointed at.

### The timelapse was sitting in the archive

`tools/timelapse.py` — nineteen `island` captures going back to the first one, and `render3d` has
been able to draw a capture since it was written. What was missing was the observation that a folder
of dated captures of the same box IS a timelapse. **16 frames, 18–28 August, +42,266 blocks.**

Three things it had to get right, and two of them are about honesty rather than rendering:

- **THE FRAME MUST BE FIXED.** `orbit` sizes the camera to each model's own content, which is right
  for one animal and wrong here: the island grows, so every frame would re-frame to its own bounding
  box and the whole thing would swim. One camera, computed once, from the union of every frame's
  content in WORLD coordinates.
- **A CAPTURE THAT LOST A THIRD OF THE ISLAND IN AN HOUR SAW LESS OF IT.** All twenty cover the same
  56 chunks, so chunk count says nothing — what differs is DEPTH: a scan taken from the deck never
  receives the lowland's sections, and the archive ranges 49,762 to 137,857 blocks over the same
  ground. Played straight, the underworld blinks in and out. Frames under 70% of the running peak
  are skipped, **reported, and overridable** — because a big drop CAN be real: Jack removed 32,369
  vines by hand between two of these scans, and a filter that quietly hid that would be editing the
  history it exists to show.
- **Ordered by the capture's own timestamp, never mtime** — copying a folder rewrites every one of
  them, and the backup now copies that folder nightly.

### Still open

- **The printer has not been run in game.** Every piece of it is unit-tested and the API was checked
  against the jar rather than remembered, but the aiming rules are reasoning until a stair goes in
  and gets walked up. Start it on something small and forgiving.
- **Two printers will fight** over the same cells. `/cscan print` warns when litematica-printer also
  has the design enabled; it cannot turn the other one off.
- **`make` does not open the crafting table**, on purpose — the same refusal `Prices` makes about
  the shop. Whether that survives contact with an overnight run is Jack's call.

## Full automation: the loop closes (2026-08-30, chunkscan 0.5.0)

Seven more, and the first of them is a SUBTRACTION.

| | |
|---|---|
| the loop asks the printer | a placement is progress and a refusal is proof, both immediately |
| `/cscan autodig <design>` | break the cells the dig list names, and only those |
| `/cscan smelt <item> <n>` | drive a furnace or a stonecutter |
| `/cscan buy <design> [cap]` | quote the shortfall; with a cap, buy it |
| `/cscan farm <seed> <crop>` | place-wait-harvest over the wand's box |
| `/cscan photo <design>` | fly eight bearings and photograph each |
| auto-sampled income | a rate exists without anyone remembering to ask for one |

### The clocks were a workaround, and now there is a signal

Every stall clock in this mod descends from one sentence in these notes: *"the printer never
reports back, so `todo` shrinking is the only honest evidence a block was placed"*. Four clocks, an
abandoned-station set, a thrashing detector and a recovery ladder, all inferring from silence.

`Printer` reports now, and `Loop.stationFromReport` uses it. **The difference is not speed, it is
a different KIND of answer:**

- **a placement is progress immediately** — no waiting to see whether a count moves;
- **A REFUSAL IS PROOF IMMEDIATELY.** The clock could only ever say "nothing for five seconds" and
  guess why. A refused cell is the world saying no, and there is nothing to wait for, so the bin is
  abandoned on the spot;
- **and silence still means silence.** Nothing attempted is not evidence of anything, so it falls
  through to the clock exactly as before. That fallback is what keeps it honest — the report
  answers only what it actually observed, and litematica-printer is still an option.

### `autodig`: the one operation with no undo

A litematic cannot express removal, so "break this" has always lived in the sidecar and always
meant a human with a pickaxe. `Falls` is 58% dig. **Every gate here is a REFUSAL rather than a
warning** — the opposite posture to the rest of the mod, where a provisional list only ever warns:

- **only cells the design's own dig list names.** Not "anything in the way";
- **never a protected block** — `Rules` holds `wool` because wool may be a sculk sensor's silencer,
  and this is precisely the pass that would find out the hard way. **THE LIST IS NOT THE AUTHORITY
  ON SAFETY:** a dig list naming one is reported and skipped, not obeyed;
- **never over open void.** `VoidRisk` already knows what falls forever, and a lost drop is the
  skyblock-specific loss no undo can reach;
- **one block at a time, watched**, giving up rather than swinging at bedrock all night.

It does not pick up what it breaks, and says so.

### The furnace, the stonecutter, and a wait that is not a stall

`make` drove a crafting grid and reported the rest as out of scope, which was honest and still left
you doing it. `Smelter` closes it — and the clay farm needs the furnace leg specifically: clay to
terracotta is 1,968 smelts.

**A FURNACE DOING ITS JOB LOOKS EXACTLY LIKE A STALL** for ten seconds an item, so there is no
clock here at all, and `AutomationTest.aFurnaceWaitIsNotAStall` exists to stop someone adding one.
**Fuel is handled before input**, because an input with no fuel is not a stall either — it is a
furnace that will never start, and it looks identical to one that is working.

**The stonecutter is a button, not a grid**, so there is no arrangement to get right — and that
means the index is the ONLY thing naming the recipe, in an order the server chooses. It reads the
output back and checks it is what was asked for. Trusting the index turns stone bricks into the
wrong stair.

### Buying, which is the only thing here that spends something

Everything needed already existed; what is new is the part that cannot be undone by breaking a
block. So it is almost entirely refusals:

- **THE CAP IS AN ARGUMENT AND HAS NO DEFAULT.** `/cscan buy <design>` QUOTES; only
  `/cscan buy <design> <cap>` spends. There is no form that spends an amount nobody chose, and a
  test reads the command tree to keep it that way — a default, however conservative, is a number
  someone else picked for money that is not theirs.
- **It spends against the SHORTFALL, not the design.** Buying 518 powered rails when 167 sit in a
  chest is 167 rails of waste, and knowing that difference is what the craft resolver is for.
- **An unpriced item is never bought**, and **the price comes from the slot in front of you**, not
  from the book — the book is a memory of a menu seen at some point in the past, and prices move.

### The farm loop, and the photo tour

`Farm` is deliberately generic — a seed, a crop and a box — because the shape is the same for clay,
mud, ice or anything that converts in place. Nothing about clay is written into it. **It only ever
breaks the CROP, and only inside its box**, so pointing it at a wall by mistake does nothing at all.
And **it waits rather than deciding**: a conversion that has not happened yet is indistinguishable
from one that never will, so it reports its rate and lets you judge.

`Photo` closes the largest known-wrong in this file. The notes say it plainly: *"Validation is
circular FOR COLOUR"*, and *"nothing built in this system has been placed in Minecraft and looked
at"*. **A screenshot is the one image in the pipeline that owes nothing to our colour database** —
the game's textures, the game's light, and the biome tint the extractor had to ASSUME. Eight
bearings, the same eight `look.py --sheet orbit` renders, **relative to the recorded facing** so
bearing 0 really is head-on; a design with no facing SAYS SO rather than defaulting quietly. It
flies rather than teleporting.

**A 26.x API note, found by javap rather than by memory:** there is no
`Minecraft.getMainRenderTarget()`, so `Screenshot.grab`'s naming overload cannot be reached — its
RenderTarget argument has nowhere to come from. `grab(mc, true)` is the F2 path: the game names the
file and prints that name in chat, which is why the bearing is announced immediately before. The two
lines together are the caption.

### Income samples itself now

`/cscan income sample` was manual, so the rate only existed if you remembered. It samples after every
container the watcher indexes — but on **both** conditions, not either: ten minutes must have passed
AND the totals must have moved. A pure timer fills the log with identical rows overnight and makes
the "the index grew" caveat meaningless; sampling on every change writes a row per chest opened,
which is a rate measured over thirty seconds of walking.

### Still open

- **None of the placing, breaking, smelting or buying has run in game.** Every piece is unit-tested
  and every API was checked against the jar rather than remembered, but a stair being walkable and a
  purchase costing what the lore said are reasoning until they happen. Start each on something small.
- **Two printers will fight.** `/cscan print` warns when litematica-printer also has the design
  enabled; it cannot turn the other one off.
- **`make` and `smelt` do not open their own block**, on purpose — the same refusal `Prices` makes
  about the shop. Whether that survives an overnight run is Jack's call.
- **`tests/test_designs.py::test_all_configs`** still fails on `shop_islet.yaml` (`short_grass on
  cobblestone`), unchanged and pre-existing.

## Redstone that is VERIFIED, not drawn (2026-08-30)

Jack: autonomous redstone, whole-island transformation from a brief, and up to five alt accounts
building at once. Decisions taken: **5 alts, server-legal · propose -> approve -> build · fully
functional redstone.** That third answer makes one thing mandatory before any of the rest, and
this section is that thing.

### Nothing in this pipeline had ever asked whether a circuit WORKS

`audit` asks whether a block state is legal, supported and non-colliding. `blocks` asks whether
the 1.19 server has it. `palette` asks what it costs. **A redstone circuit passes every one of
those while doing absolutely nothing**, and you find out by flipping the lever an hour later. It is
this project's oldest failure mode - *a clean audit and a wrong build* - aimed at the one subsystem
where the wrongness is invisible in every render, every audit and every BOM.

**THE PRECEDENT WAS ALREADY HERE.** The night pass is trusted because light is PROPAGATED through
the finished model and the spawnable cells are counted. Signal is the same shape of problem: a
value that spreads from sources, decays with distance, and is stopped by geometry. So
`mcbuild/circuit.py` is a simulator, and a circuit is verified before a block is placed.

    wire · redstone_block · torch · lever/button/plate · repeater (delay + LOCK) ·
    comparator (compare/subtract, container fullness) · observer · piston · dispenser (rising edge)

Every component's real state space came out of `blocks.json` - power 0-15, delay 1-4, compare and
subtract - so the numbers are the game's, not remembered. `tests/test_circuit.py` is fifteen
hand-worked cases, each one a fact you can check on a workbench.

**What is NOT modelled, stated because a simulator you trust past its limits is worse than none:**
quasi-connectivity (REPORTED per cell instead - Java also fires a piston from the block above, and
real circuits both use and are broken by that), Java's update order and 0-tick pulses, and
entities. **A container's fullness is an INPUT you state**, never something that fills itself:
pretending otherwise would certify a sorter that has never seen an item.

### Four bugs in the simulator, found by its own tests

The tests did their job before the simulator did. In order:

- **A torch was powering its own support block**, so it read "my attachment is powered", switched
  itself off, and every circuit oscillated every other tick. A torch powers everything around it
  EXCEPT what it is attached to; a lever is the opposite and strongly powers its attachment. **The
  two cases are not symmetric and cannot share a rule.**
- **The power model conflated "this cell radiates" with "this cell is aimed at".** That split is
  the whole model: `emit` is a torch or a lever radiating to six neighbours; `into` is a repeater
  or comparator driving one cell and nothing else - which is the entire reason a repeater is used
  to isolate one line from another. Missing it reported a torch as powering nothing.
- **A cell that emits is itself powered**, which sounds obvious and was missing - so a repeater fed
  directly by a lever never turned on, and the failure looked like the delay logic.
- **And one test was wrong where the code was right**: it put a lever on the block NEXT to a
  torch's support and expected the torch to react. Power does not flow between two solid blocks, so
  that circuit does nothing in Minecraft either. A hand-worked case exists to produce exactly that
  outcome.

### The module library: a contract, or it does not ship

`mcbuild/gen/circuits.py` - clock, latch, pulse, randomiser, payout, lamp_bank. **Every module
states a CONTRACT and `tests/test_circuits.py` asserts it by simulation.** A module whose contract
is not asserted does not belong in the file.

- **The clock's loop must close on the torch's SUPPORT, not on the torch.** The first version
  pointed the repeater at the torch's own cell, which does nothing: four tidy blocks, a clean
  audit, and it never ticked once. Found on this file's own first module.
- **A long lamp bank needs a repeater every 15.** Wire dies at 15 and a twenty-lamp sign lights two
  thirds of the way, which looks like a build somebody abandoned. Only simulation catches that
  before it is placed.
- **A payout fires every dropper exactly once per EDGE.** A dropper that fired every tick would
  empty the bank into the floor - the most expensive bug a casino can have.
- **RANDOMNESS IS NOT A CIRCUIT TRICK AND THE MODULE SAYS SO.** Redstone is deterministic; every
  random build borrows entropy from item routing, which this simulator has no entities to model.
  What is verified is one-lane-per-trigger and reset. The distribution is a property of the game
  and must be checked in world - `RANDOM_NOTE` travels with it.

### Wired into the pipeline, and it found a real bug immediately

Any design containing redstone is now inspected on generation: dead wire runs measured by true path
length from the nearest source, orphaned dust, components nothing can drive, repeaters pointing at
air, and QC risk. It runs over the whole island in **0.1s**.

Two corrections the integration needed, both of them rules this repo already knew:

- **Verify in CONTEXT, never in isolation** (rule 2). A design here is REMAINING WORK, so half a
  circuit may already be standing; inspecting the design alone called four of the sorter's
  comparators unwired. It inspects the composite now.
- **Diff against a BASELINE**, as the audit does. The island already carries twelve
  quasi-connectivity risks and seven orphaned dust groups of its own, and reporting those against a
  new design sends you hunting faults you did not cause. `circuit (new):` is what prints.
- And the "is it wired" test had to accept a component driven by a powered BLOCK rather than by
  dust - half the machines on this island are - because **a check that cries wolf is a check nobody
  runs.**

#### THE SORTER'S COMPARATORS WERE BACKWARDS, IN EVERY LANE, SINCE IT WAS WRITTEN

The first run against real work in this repo reported `comparator reads nothing x4`. It was right.
`gen/redstone.py` had a helper called `_toward`, whose own docstring said *"points a comparator back
at the filter hopper"* - and **a comparator reads what is BEHIND it and outputs where it FACES**, so
every lane read air and pushed its signal into the container.

Nothing else could have seen it. The state is legal, supported, affordable, in 1.19, and **our
renderer draws both directions identically** - which is the stair convention's exact failure mode,
in a subsystem where it costs the whole machine rather than one step. It is `_away_from_hopper` now,
and `test_the_sorters_comparators_read_the_hopper_rather_than_facing_it` pins all four runs.

**Still open on the sorter, and NOT guessed at:** with the comparators reading correctly, the
inspection now says `comparator drives nothing` - the design never routes their output to the
torches that lock the hoppers. That is a real gap in the signal path and a redesign, not a
one-line fix, so it is reported rather than invented. The simulator will judge whatever replaces it.

### What is NOT built yet

The simulator and the module library are the foundation; the two things Jack actually asked for sit
on top of them and are not written:

- **The island planner** - brief ("a redstone casino") -> module selection -> siting -> cost ->
  circuit verification -> a PLAN artifact for approval -> build. Almost every piece it needs
  already exists (`plot`, the distance-transform siting, `defer_to`, `after` ordering, `craft`,
  `print`, `autodig`); what is new is the planner itself and the approval gate.
- **The fleet** - up to five alts, which is a server-legal cap Jack confirmed and which must be
  encoded as a hard limit rather than a default. Needs a per-account profile (its own schematics
  dir, island and plot) and a coordinator that assigns designs.

### Checked against the source, not against itself (2026-08-30)

Jack supplied minecraft.wiki's Redstone mechanics and components pages. The model was built from
reasoning plus hand-worked cases, which is exactly the situation rule 11 is about, so it was
checked against them. **The power model held**, in its own words:

- *"Redstone power component, a powered redstone repeater, or a powered redstone comparator"*
  strongly power a block, and a strongly powered block *"can power adjacent redstone dust"* -- that
  is `into`.
- *"Redstone dust"* only weakly powers, and a weakly powered block *"cannot power adjacent redstone
  dust, but can still activate adjacent redstone mechanisms, and power redstone repeaters and
  comparators facing away from the block"* -- that is `emit` plus the wire-adjacency rule, and it
  is why `_solve_wire` takes `into` from opaque neighbours and never `emit`.
- *"the signal strength decreases by 1 for every block of redstone dust"*, and *"does not decrease
  when transmitted from redstone dust to a block or a redstone component"*.

**And it settled one thing the file had only DISCLAIMED.** QC was reported rather than modelled
because it was unverified; the wiki states it plainly -- a piston *"can also be activated if a
redstone signal is supplied to the block above them, even if that block is air"*, dispensers and
droppers too. It is modelled now, on by default, with `qc=False` available to prove a circuit does
not secretly depend on it. `quasi_connectivity_risk()` stops being a disclaimer and becomes a list
of places whose behaviour rests on a mechanic most people do not expect.

**The test for it was wrong first, and instructively.** It put dust DIRECTLY on the piston -- which
powers it by ordinary adjacency and proves nothing about QC. The real fixture is dust that never
touches the piston at all: the cell above is AIR and the dust is beside that air. A test that
passes for the wrong reason is worse here than one that fails.

(redstone.build is a tutorial site rather than a schematic or mechanics source -- no exportable
designs -- so nothing was taken from it.)

## The casino, the planner and the fleet (2026-08-30, chunkscan 0.6.0)

Built on the circuit simulator, which is the only reason any of it can claim to work.

    python -m mcbuild plan "redstone casino"      # sited, costed, circuit-verified
    python -m mcbuild plan --approve casino       # THE GATE
    python -m mcbuild plan --emit casino          # configs, only after approval
    python -m mcbuild fleet --assign casino --accounts A,B,C
    /cscan fleet                                  # in game: who holds what

### Casino modules, out of verified circuits only

`gen/casino.py` - slot, prize_wall, marquee, counter. **Nothing in it invents a circuit**; every
mechanism comes from `gen/circuits.py`, whose modules each state a contract asserted by
simulation. THE HOUSE MUST NOT BE ABLE TO LOSE BY ACCIDENT, so: every button goes through a pulse
(a player HOLDS a button), the bank is a barrel a human stocks rather than something the machine
can reach past, and the randomiser's distribution is carried forward as UNVERIFIED all the way
into the plan.

**And the contract travels with the build**, in the sidecar - inputs, outputs, what it promises,
what it cannot. A machine whose promise lives only in a chat message is one nobody can audit a
month later, which this project has been bitten by before.

### COMPOSING VERIFIED MODULES DOES NOT GIVE YOU A VERIFIED MACHINE

The single most useful thing learned here. The first slot machine was a correct pulse, a correct
randomiser and a correct payout **sitting near each other with nothing between them**. Every part
passed its own test. The machine did nothing, and the plan's circuit inspection said so on the
first run: *wire dies before the end*, *dropper is not wired*, *repeater drives nothing*.

`circuits.connect` is the fix - an L path with a repeater every 14, because **wire dies at 15** and
that is the rule which turns a working bench test into a build that stops halfway.

**Then the connectors ate the components.** `World.put` overwrites, and a path that starts AT its
endpoint replaces the very thing it is connecting: the wired slot had a redstone wire where its
button should be and another where its payout dropper should be, and simulated as firing **zero**.
A connector runs BETWEEN two things and may not stand on either. `tests/test_casino.py` now
presses the button and asserts the dropper fires exactly once, which is the only form of this
check worth having - "no smells" is not "it works".

### The planner: propose, verify, approve, build

`mcbuild/planner.py`. **THE PLANNER DOES NOT UNDERSTAND ENGLISH AND DOES NOT PRETEND TO.** A brief
selects a THEME from a catalogue. That is an honest split: what a casino should contain is a
judgement, and whether it fits, collides, can be afforded and actually works is measurement.
Wiring a model to the first half is a one-line change and it still cannot skip the second, which
is the point - a model that could approve its own plan could build a spotted table at island scale.
An unmatched brief RAISES rather than defaulting to the only theme in the catalogue.

**The gate lives in `emit`, not in the CLI**, so no other caller can route around it.

Two real bugs it caught on its first two runs, both in siting:

- **THE TOPMOST SOLID CELL IS NOT THE GROUND.** The first plan sited the whole casino at **Y264,
  on top of the sky bird**, because a naive height map takes the highest block in each column.
  `ground_band` takes the MODAL surface height instead - a 2,000-column plate dominates any number
  of sculptures, and it needs no hand-written Y. It now sites at Y204, on the deck. This is the
  night pass's own lesson ("the lowest-standable classifier struck a THIRD time") arriving from the
  opposite direction.
- **A footprint is a box, so both corners are boundary-checked.** Checking only the origin sites a
  module that starts inside the plot and finishes over the line - exactly how the Island Run put
  120 cells past the edge.

And it refuses honestly: the marquee (20x5) and the prize wall (6x12) report **NO SITE**, which
matches this file's own note that the plate's largest genuinely flat area is 13x13.

### The fleet: five alts, one folder

Jack runs up to five alts, server-legal, all reading the SAME schematics directory on one machine.
**That removes almost everything a fleet would otherwise be about** - no per-account profile, no
separate design set, nothing to sync. What is left is the only hard part: who builds what.

- **FIVE IS A CAP, NOT A DEFAULT.** It is a server rule, so it is enforced in `assign()` rather
  than written in a comment. A tool that quietly allowed a sixth is a tool that gets an account
  banned.
- **TWO ACCOUNTS MUST NEVER SHARE A DESIGN** - not because the files collide (they are the same
  file) but because two printers placing into the same cells fight: each sees the other's block as
  already-built or as a deviation, and `Printer`'s report, the only honest signal this loop has,
  becomes noise. `/cscan print` REFUSES a design another account holds.
- **A CLAIM IS A LEASE, BECAUSE AN ALT CAN DIE.** A claim that never expires strands a design for
  ever; one with no expiry lets a second account grab it the moment the first is slow. Fifteen
  minutes, refreshed by a heartbeat while the loop runs - the same reasoning the chest cooling-off
  already carries, and it has to expire for the same reason.

### Two more of this session's own bugs, worth keeping

- **`Set.of` REFUSES DUPLICATES AT CLASS-INIT TIME.** Re-adding `"take"` to `RESERVED` turned every
  command in the mod into an `ExceptionInInitializerError` - six unrelated tests went red at once
  and none of them mentioned the list. The stack trace names the initialiser, never the duplicate.
- **A test fixture that is wrong twice for the same reason.** The connector's test drove it from
  one cell OUTSIDE the endpoint, which after the endpoint-skip left it adjacent to nothing. Same
  shape as the torch test earlier in the day: when a simulator and a fixture disagree, check which
  one models Minecraft.

### Still open

- **None of the casino has been placed in game.** The machines simulate correctly and the API was
  checked against the jar, but a slot machine paying out is reasoning until someone presses it.
- **The randomiser's distribution is unverified by construction** and says so at every level -
  module, build sidecar, and plan. Check the odds in world before anyone plays for stakes.
- **`gen/redstone.py`'s sorter still has no signal path** from its comparators to the torches that
  lock its hoppers. Reported by the inspection, not invented.
- **`tests/test_designs.py::test_all_configs`** still fails on `shop_islet.yaml`, unchanged and
  pre-existing.

## Shulker pulls, and an alt that works its own assignment (2026-08-30, chunkscan 0.7.0)

### "A client mod cannot unpack a box for you" was the same kind of claim as the last one

This file has said for a long time that a boxed block *"is not placeable until you set the box
down"* and that *"a client mod cannot unpack one for you"*. The first half is true; the second was
a POLICY WRITTEN AS A FACT, exactly like *"a client mod cannot place a block"* before it. Placing,
opening, emptying and breaking a box are four things this mod already did separately.

It matters because **bulk storage on this island IS boxes in chests**. The index already read
their contents into `inBoxes`, `Plan.notInAPack` already subtracted them from a shortfall so you
were not sent shopping for something you owned - and then the loop stopped and told you to do the
last step by hand. It does it itself now, inside the fetch phase.

**Placed shulker boxes needed NO new code and that is worth recording.** `Storage.CONTAINERS`
matches by substring, so a shulker box standing in the world has always been indexed, findable and
withdrawable exactly like a chest. `UnboxTest` asserts it so nobody "adds" it later and breaks the
substring match.

**A SHULKER BOX IS THE MOST DANGEROUS BLOCK IN THE GAME TO AUTOMATE.** Everything else here risks
one block; this risks a whole inventory, and the failure is silent - a box left on the ground looks
exactly like one that was picked up. So the rules are refusals rather than warnings:

- **Never over the void.** A dropped block is a block; a dropped shulker is everything in it.
- **Only ever break a box THIS ROUTINE PLACED, at the exact cell it placed it.** The island is full
  of boxes that are somebody's storage, and "a shulker box nearby" is not a thing it may touch.
- **The box must come back**, checked against the pack afterwards. An unrecovered box is not a
  failed step, it is a lost chest, so it stops everything and says where the box is.

### `/cscan fleet work` - an alt that picks up its own assignment

`follow all` walks every tracked design, which is right for one player and wrong for a fleet: five
alts all starting at the top of the same list is five printers fighting over one design. `fleet
work` walks only what this account holds, keeps the lease alive while it builds, and hands a design
back the moment its placements are done.

### Three defects found auditing this session's own work

- **The Crafter's race, again, in `Unbox`.** `st.getCount()` is what the server is being ASKED to
  move; a full pack moves less. Counted from the pack on a later tick now. The same bug twice in
  one day is the argument for the rule rather than the fix.
- **FIVE CLIENTS SHARE `fleet.json` AND IT WAS WRITTEN IN PLACE.** A plain write leaves a window
  where the file on disk is truncated, and a client reading in that window sees an EMPTY fleet -
  then claims a design another account is already building, which is the one thing the file exists
  to prevent. Atomic temp-then-move on both sides now. **The remaining read-modify-write race is
  documented rather than implied away**: two clients that both read and both write still lose one
  change, and what carries it is that claims are near-idempotent and heartbeats repeat. A real lock
  is the fix the day this assigns something that cannot be repeated.
- **A tautological test** (`assertTrue(x || true)`) was removed. A test that cannot fail is worse
  than no test, because it is counted.

### Still open

- **None of the unbox routine has run in game.** It is the one automation whose failure costs an
  inventory rather than a block, so run it once by hand - `/cscan unbox <item> <n>` - on a box you
  would not mind losing, before the loop is left to call it unattended.

## More than one island, and the last red tests (2026-08-30, chunkscan 0.8.0)

**599 Python and 447 Java tests, 0 failures** — the first time in this session the suite has been
entirely green.

### Alt 2 can build on alt 1's island

Everything here assumed ONE island, because there was one: `plot.find` reads the bedrock out of a
capture, the mod carried a single square baked in at export time, and `fleet.json` claimed designs
with no idea where they were. All of it holds right up until a second account has its own island.

**AN ISLAND IS IDENTIFIED BY ITS BEDROCK, NOT BY WHOSE IT IS.** Every skyblock island has exactly
one bedrock at its origin, which is already how the plot is found — so the bedrock coordinate IS
the identity: stable, discoverable from any capture, and indifferent to who is standing on it.
Keying off the account would break the moment an alt walks next door, which is the entire case
being built.

    python -m mcbuild islands --add main --from out/island_now.litematic --owner Enroniti
    python -m mcbuild islands --where -24200 30000        # -> main
    /cscan plot                                            # ...whichever island you are ON

**OWNERSHIP IS A LABEL, NOT A PERMISSION.** It makes a report read sensibly and never decides who
may build; a tool that refused alt 2 on alt 1's island would be enforcing a rule the server does
not have. What IS enforced is that every boundary check — the wand, the printer, the digger, the
unbox siting — now asks about the island under THAT CELL rather than the one that happened to be
exported. Judged against the wrong square, every build on a second island reads as four thousand
blocks off-plot.

Two refusals carried over deliberately: **an unknown place is not an off-plot one** (somewhere the
registry has never been told about answers "I cannot say", the same posture `Plot` already takes
when no bedrock was found), and **with no registry at all it falls back to the single plot**, so a
setup that has never heard of a second island is unchanged.

A claim is keyed by ISLAND AND DESIGN now, because two alts can be building designs of the same
name in two places and a bare name would hand one account's work to the other.

### Three bugs, and two of them were latent for months

- **THE GENERATOR ASKED A DIFFERENT WORLD FROM THE ONE THE AUDIT VERIFIES AGAINST.** `shop_islet`
  consulted `island_deep` (which reads air at Y150) while `verify_against` used deep AND
  `island_now` — which holds the cobblestone Jack placed in the massif rework. So it planted
  short_grass believing its own moss would be underneath, and the moss is never placed, because
  `ROCK_FAMILY` counts cobblestone as satisfying it. Grass rooted in stone, one failing test, and
  the cause three files away. `Ctx` takes a LIST now and later captures win where they hold
  something. One design, two worlds, two answers: the same drift `proportions` and `rubric` share
  an entry point to avoid.
- **"REGENERATING THIS DESIGN MUST BE FOLLOWED BY RE-CARVING" WAS THE BUG, NOT THE FIX.** The shop
  islet's lens fill sits where the Lowland Stair screws down through it; the well was cut by hand
  once, with that note in the config and a test as the tripwire. Regenerating the islet to fix the
  grass re-filled the well and the tripwire fired — exactly as predicted, months later, by an
  unrelated change. **A step that has to be remembered is a step that gets lost.** `finish.carve_for`
  is a pipeline step now: dig cells plus headroom over whatever you stand on, re-derived on every
  run. 250 cells, by construction, for ever.
- **A cache keyed on the clock alone.** `Islands.all` cached per 30 seconds and not per DIRECTORY,
  so a second schematics folder silently got the first one's islands. Benign today — there is one
  folder — and precisely the latent bug that bites the day there are two. Its own test found it.

### Still open, and deliberately not guessed at

**The item sorter's threshold.** With the comparators reading correctly, the lock never flips: the
signal path from comparator to the torch that locks each filter hopper does not exist. The
simulator confirms the comparator reads the hopper (out == fill) and that nothing reaches the
torch. The correct topology is a THRESHOLD — unlock at signal >= 2, not >= 1, because the baseline
of 1 target + 4 filler already reads 1 — and I do not have a verified design for it. It is the one
thing here I am not willing to invent, because a sorter that looks right and voids items is worse
than one that plainly does not run.

**And none of the multi-island work has been exercised with a second island**, because there is
only one recorded. The fallbacks are tested; the two-island case is tested against a synthetic
registry. Record alt 2's island with `--add` and walk over before trusting it.

## Two reference builds, and the mistake they caught (2026-08-30)

Jack supplied a working four-lane `item_filter.schem` and a bonemeal farm with a shulker loader.
They are checked into `reference/` and they earned their place immediately.

### Reading the OTHER schematic format

`mcbuild/sponge.py` reads WorldEdit `.schem`. Everything here speaks Litematica because that is
what chunkscan writes, and **a reference build that cannot be opened is a reference build nobody
learns from** - the same reason `tools/corpus.py` exists. Two things to get right: **the block
array is VARINT-packed, not bit-packed**, and **Sponge's palette is NAME -> INDEX, the reverse of
Litematica's list** and not necessarily in index order, so it is built by position. Read in the
wrong order it silently relabels every block and looks like a clean import of a different build.
`load_any` decides by CONTENT, because a file called `.litematic.gz` is still a litematic.

### THE SORTER'S COMPARATOR WAS RIGHT, AND I TURNED IT ROUND

Earlier the same day the circuit inspection reported `comparator reads nothing` on the item sorter,
and the general rule - *a comparator reads what is behind it* - was applied to flip every lane's
comparator to face away from its hopper. **The rule is true and the inference was wrong.**

The reference settles it in one minute: the comparator sits beside the filter hopper and faces
INTO it. It is not reading the hopper, it is **driving** it - a comparator's output locks a hopper
- and its own input arrives from BEHIND, off a smooth-stone block that a wire bus weakly powers.
The wiki's own rule is what makes that legal: a weakly powered block *"cannot power adjacent
redstone dust, but can still ... power redstone repeaters and redstone comparators facing away from
the block"*.

So the original orientation was correct; the lane's real fault was that it had nothing behind the
comparator and **no lock line at all**. The whole lane is now copied cell for cell from the
reference - torch, repeater, stone, glass, bus - and `tests/test_circuits.py` compares the
generated lane against the reference FILE rather than against anybody's memory.

**Reasoning got this backwards twice and a reference build settled it immediately.** That is the
strongest argument yet for the corpus discipline this file already recorded: outside builds are
the only non-circular evidence this project has.

### Calibrating the inspection against builds known to work

Run over the bonemeal farm - a machine that demonstrably works - the inspection returned **74
findings**. Almost all of it was noise, and fixing that is worth more than any new check:

- **62 quasi-connectivity lines, one per component.** A piston machine is pistons with things over
  them; that is what one looks like. One counted line now, with an example. A per-cell warning that
  fires on every cell of a working build is how a real finding gets scrolled past.
- **Seven "piston is not wired" on pistons a real build fires from above.** QC is MODELLED now, so
  it counts as wired.
- **Five findings within one cell of the file boundary.** Every finite cut truncates something -
  the audit already knows this about captures - so `near_edge` separates a cropping artifact from a
  fault. 74 -> 13, of which 5 are edge.

And the seven that remain are a REAL LIMIT, now written into the module: **anything driven by a
MOVING redstone block is invisible to static inspection.** They are one row at a single course,
no wire, no observer, nothing overhead - a redstone block a piston pushes along, which is how half
the compact farms in the game work. At rest the driver is not next to the thing it drives.

### Still open

**The sorter has not been tested in game, and the lane is a copy rather than an understanding.**
The bus's power path is not derivable from a static snapshot - the inspection still says "dust with
no source" on the REFERENCE itself - so what is shipped is a faithful reproduction of a build that
works, not a mechanism this project can explain. Place it and put an item through it before
trusting it. That is a much better position than the invented lane it replaces, and it is not the
same as verified.

## The wiki closes the odds question (2026-08-30)

Jack sent minecraft.wiki's Tutorials index and pwouik's advanced-redstone resource gist. The gist
is an INDEX of learning material rather than data, and nothing was taken from it; the wiki's
`Tutorial:Randomizers` and `Tutorial:Item_sorting` both changed real code.

### A casino that does not know its own odds

`circuits.randomiser` took any N up to 8 and said, in writing, that it could not tell you the
distribution. **For a slot machine that is not a caveat, it is a bug** - a house that does not know
its odds cannot know whether it is losing money, and the whole point of `gen/casino.py` is that
the house must not be able to lose by accident.

The wiki gives an equal-probability figure for exactly two item mixes, and **the odds are a
property of the MIX, not of the wiring**: a dropper ejects a uniformly random one of its OCCUPIED
slots.

    2 outcomes, EQUAL   one stackable + one non-stackable            -> power 1 or 3
    3 outcomes, EQUAL   64-stackable + 16-stackable + non-stackable  -> power 1, 2 or 4

and, quoting the same page, extras make it lopsided: *"with two different stackable items and three
different non-stackable items, the RNG will output power level 1 40% of the time and power level 3
60% of the time"*. So those two mixes are the only ones on offer, **anything else RAISES**, and the
required items travel in the build's sidecar exactly as the sorter's filter stock does. A machine
built right and loaded wrong pays wrong.

### Two bugs the rewrite exposed, and one test that had been passing for the wrong reason

- **The randomiser's comparator was not reading its hopper.** Placed by hand, its BACK pointed away
  from the container it exists to read, so the machine could never have paid out. It is placed one
  step along its own facing from the hopper now, which makes the relationship automatic rather than
  remembered.
- **`test_a_press_pays_exactly_once` had been passing without stating a win.** The old randomiser
  passed the trigger straight through, so the test proved nothing about the machine; with a
  randomiser that genuinely gates on items it went red immediately. The win is STATED now, through
  `fill` - which is exactly the contract the simulator documents: *a container's fullness is an
  INPUT you state*. **The simulator has no entities and a test that hides that is worse than no
  test.**

### What the sorting tutorial confirmed, and what it did not settle

Confirmed, and now sourced rather than remembered: the filter hopper takes **1 target + 4 filler**;
the comparator's reading rises when the target arrives; the torch-and-repeater chain drives a dust
line that **locks the hopper below the filter**; and the mechanism rests on the rule that *"hoppers
search for an item to be taken from the input side BEFORE outputting an item to another
container"*.

Not settled: **what powers the bus in Jack's reference filter.** The inspection still reports "dust
with no source" on the reference ITSELF, which is either my model missing a path or the power
arriving from outside the exported region. The shipped lane remains a faithful copy of a build that
works rather than a mechanism this project can explain, and that distinction stays in the docstring.

## Four reference builds calibrated the inspection: 74 findings -> 1 (2026-08-30)

Jack sent two more working contraptions (`reference/contraption_31323.litematic`,
`contraption_24829.litematic`) on top of the item filter and the bonemeal farm. Run against builds
that DEMONSTRABLY WORK, the circuit inspection was mostly shouting at itself:

| build | findings before | after |
|---|---|---|
| bonemeal farm + shulker loader | **74** | 1 |
| contraption 31323 | 2 | 1 |
| contraption 24829 | 9 | 1 |
| item filter | 2 | 1 |

and the one that remains on each is the informational quasi-connectivity line, except the item
filter's - which is the bus question, now the ONLY real finding across four independent builds and
therefore much more likely to be a fact about that exported region than noise.

**THE ONLY QUESTION THAT DECIDES WHETHER A TOOL GETS USED IS WHETHER IT STAYS QUIET ON A MACHINE
THAT WORKS.** This project already learned that on the audit and again on the deck soffit - *a
check that cries wolf is a check nobody runs* - and a redstone inspector has more chances to cry
wolf than anything else here. `tests/test_circuit_calibration.py` pins a CEILING per build, so a
future change that starts shouting fails.

### Four false-positive classes, each a real bug in the tool

- **SEEDS ARE NOT SOURCES**, and this was a genuine defect. The walk that measures "how far is this
  dust from power" collected the EMITTER - which may be two cells away, through a block it powers -
  and then seeded from dust ADJACENT TO THAT EMITTER. The two never match: a dust cell fed through
  a stone block is not adjacent to the torch under it. So the walk seeded nothing, every cell
  measured as unreachable, and six runs of a working build were reported as dying. It collects the
  cells power ARRIVES AT now. This one was also mis-reporting our own designs and nobody had
  noticed.
- **A MOVING REDSTONE BLOCK DRIVES HALF THE COMPACT MACHINES IN THE GAME.** At rest the driver is
  not next to the thing it drives, so a static inspection calls a working machine unwired - seven
  "unwired" pistons in one row of the farm, and a repeater pointing at empty air with a redstone
  block sitting on a sticky piston one cell above. `moving_driver_near` is deliberately generous: a
  false negative costs a real finding, a false positive costs a warning nobody needed.
- **An OBSERVER pulses rather than holding**, and what it watches for may only exist while
  something moves. Two repeaters came back as "reads nothing" with observers on two sides.
- **62 quasi-connectivity lines, one per component.** A piston machine is pistons with things over
  them; that is what one looks like. One counted line now.

**And the calibration was checked for blindness**, which matters more than the numbers: a stranded
comparator, a 30-cell run with no repeater and an orphaned dust group are all still reported, and
`test_our_own_broken_lane_is_still_caught` pins it. Buying quiet by going blind would be worse than
the noise.

Our own item sorter, generated from the reference lane, now reports **nothing suspicious** - which
is not the same as working, and the docstring still says so.

## A real casino, and the third schematic format (2026-08-30)

`reference/` now holds six outside builds. Two of them changed the picture.

### `casino_chirurg.litematic` — what a redstone casino actually is

**135x75x105, 185,198 blocks, 774 palette states, 5,000 redstone cells.** Ours was a 24-block
"slot machine". Theirs has 513 repeaters, 468 comparators, 404 hoppers, 329 observers, 300
droppers and **303 note blocks** - sound is a whole dimension of a casino and `gen/casino.py` had
none of it.

**AND A QUARTER OF IT CANNOT BE BUILT HERE.** Priced against this server's economy: 67.5% cheap,
7.4% ok, and **25.2% expensive - 46,609 blocks**, almost all of it quartz (25,054) and stained
glass (14,500). The aesthetic of a casino is quartz and coloured glass, and on this island that is
not a palette, it is a wish.

So the substitution has to be done properly, and doing it exposed two traps this file already
knew about:

    quartz_block          -> pearlescent_froglight   CHEAP BY THE TABLE, and this island holds ZERO
    black_stained_glass   -> black_shulker_box       a CONTAINER, admitted as skin

The first is rule 12 - *ask the world, not the table* - and the second is the `bee_nest` trap, via
the `shulker_box` gap this file has had listed as open under `rubric.FUNCTIONAL` for weeks. Both
are closed: `shulker_box` is in FUNCTIONAL now, and `palette.affordable_like` applies **three**
gates rather than one - cheap by the table, WITNESSED on this server, and not a machine. It
returns `(None, None)` rather than a bad substitute when nothing survives.

    quartz_block         -> white_wool   (24)
    black_stained_glass  -> black_wool   (10)
    snow                 -> snow_block   (0)

**A LIGHT CANNOT BE SUBSTITUTED BY COLOUR.** `sea_lantern -> birch_log` at distance 85 and
`redstone_lamp -> acacia_planks` at 50 are what a pure colour match gives you, and both are wrong
in KIND. A lamp is replaced by a lamp or not at all.

### The pre-1.13 format, and a reader that admits what it cannot see

`mcedit_1216.schematic` is the OLD MCEdit format: numeric block ids, no palette, orientation in a
parallel `Data` nibble array. `sponge.load_mcedit` reads it against a table of ~80 ids, and **an id
outside the table becomes `unknown_<id>` rather than a guess** - a reader that renders an unknown
id as stone produces a build that looks imported and is wrong, and nothing downstream can tell.
This file had exactly one (id 128) and it is named.

**But the orientation is not decoded**, and run blind that produced **66 direction findings, every
one of them about the reader rather than the build**. Rather than guess the nibble convention -
this session has been bitten twice already by guessing an orientation rule - the inspection now
DETECTS the situation: if not one directional component in a model carries a facing, the direction
checks are skipped and **the reason becomes the finding**. 73 -> 2, and the one that matters names
the reader's own limit.

### Where the calibration stands

| build | findings |
|---|---|
| item filter | 1 |
| bonemeal farm | 1 |
| contraption 31323 | 1 |
| contraption 24829 | 1 |
| casino (185,198 blocks, 5,000 redstone) | 37 |
| mcedit (orientation unknown) | 2 |

37 on the casino is **0.7% of its redstone components**, and a human-made build that size genuinely
has leftovers. Chasing it to zero would be buying quiet by going blind, which is what
`test_our_own_broken_lane_is_still_caught` exists to prevent.

### Still open

**The casino theme is still my invented module list**, now known to be a toy beside the reference.
Rebuilding it on what a real casino contains - and on a palette this server can actually buy - is
the next piece of work, and it is a design decision rather than a bug fix.

## The casino, rebuilt against the reference — and it does not fit (2026-08-30)

### THE REFERENCE CASINO IS BIGGER THAN A SKYBLOCK PLOT

135 x 105 against a 99 x 99 plot: **36 over on X and 6 over on Z.** Jack: *"it cant be bigger than
99x99 ... but we can go vertically higher and much lower"*, and that is the whole shape of the
answer - the same volume is **1.45 floors** stacked, and Y-64 to Y320 is 384 courses of room.

So the theme carries a `floors` plan rather than sprawling, and **a module wider than the plot is
reported as impossible up front** rather than after a full pad search: "NO SITE" reads like awkward
ground, when the truth is that the design can never fit at any position.

### The game, rebuilt

The first `slot` was 24 blocks. One of the reference's games is 16x12x16 with 97 wire, 27
comparators, 27 repeaters, 22 observers, 29 lamps, 16 note blocks and 27 signs. Three structural
things were wrong and all three are fixed: **the machine lives under the floor** (the reference has
two redstone layers with a play floor over them), **the display is the game** (nearly half of a
machine is coloured wool and lamps), and **sound** (303 note blocks there, none here).

**A quarter of the reference cannot be built on this economy** - 46,609 expensive blocks, almost
all quartz and stained glass - so the palette is re-derived through `palette.affordable_like`:
`quartz_block -> white_wool` (24), `black_stained_glass -> black_wool` (10). The board COLOURS
needed no substitution; they were already cheap, and the board is the part that matters.

**Two things are budgeted rather than substituted.** `redstone_lamp` and `note_block` are both
expensive, and their nearest cheap colours are `acacia_planks` and `soul_sand` - a lamp that does
not light and a note block that makes no sound. **A light cannot be substituted by colour.** They
are counted into `budget` and the count reaches the plan: 120 lamps priced out as 480 redstone (in
stock) plus 120 glowstone, of which **214 dust was short**. A shopping list, not a shrug.

### THE BAR DISPLAY DOES NOT SHIP, AND THAT IS THE POINT

The idea is sound - the outcome is an analog level, wire loses one per block, so a dust run reads
it off as a bar. Three attempts did not get a signal from the pit to the board:

1. **`connect` IS PLANAR and said so nowhere.** It lays an L path at ONE height and quietly never
   climbed the six-course pit. `circuits.climb` was written for this and is keeping regardless: a
   vertical run is a staircase of step blocks with dust on each, and it needed to exist.
2. **The lamps sat on the back wall, diagonal from the bus.** Diagonal is not adjacent.
3. **The riser shared cells with links already laid**, so `w.has` skipped its STEP BLOCKS and left
   dust stacked on dust, which connects to nothing. Rerouting it sideways did not fix it either.

At that point the honest move is to stop. `display: False`, the reason recorded in the config, and
a test that asserts the build SAYS the board is not wired. **A display that looked like a readout
and was not would be exactly the failure this subsystem exists to prevent** - it would pass the
audit, the bill of materials and the eye. What ships is the machine, and its contract is verified
by simulation: one press, one payout, never zero and never twice.

### Planning onto another island

`mcbuild plan --island <name>` takes the plot from the island REGISTRY rather than from the
capture's own bedrock, so a capture holding two islands cannot pick the wrong square. The games
report NO SITE on the main island, which is correct - CLAUDE.md has said for weeks that the plate's
largest genuinely flat area is 13x13, and a game wants 12x10 clear.

### The runbook for the fresh plot

    /cscan casinoisle                                   # in game, on the NEW island
    python -m mcbuild islands --add casino --from <capture> --owner <alt>
    python -m mcbuild plan "redstone casino" --world <capture> --island casino
    python -m mcbuild plan --approve casino             # THE GATE
    python -m mcbuild plan --emit casino
    python -m mcbuild fleet --assign casino --accounts A,B,C
    # then on each alt:  /cscan fleet work

## The daily loop

```bash
python -m mcbuild sync            # cut the newest scan, regenerate ground designs, progress + shop, learn, BACK UP
python -m mcbuild backup --status # what backups exist and how old the newest is
python -m mcbuild craft <design>  # what it is MADE of, against your containers
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

## The casino, and the four faults that cancelled each other out (2026-08-31)

`configs/` via `planner.make("casino")`, `mcbuild/gen/casino.py`, `mcbuild/gen/circuits.py`,
`mcbuild/circuit.py`. Jack: *"games are unique, creative, and interesting... this must come off as
a highly refined - perfect experience"*, on a **99x99** plot with the vertical free.

**32 modules on two floors, 22 of them games, 22% of the plot's cells.** Every game's contract is
asserted by SIMULATION, not drawn.

### What ships, and what does not

    high_roller     the level IS the display. Bar at the comparator; roll k lights k lamps.
    double_or_none  the level is DECIDED in the pit; only a win reaches the payout.

At 2 and at 3 outcomes that is four distinct games. **`chase` and `vault` were written, built
cleanly, and REMOVED** - `chase` lit every lamp on every roll, `vault` never opened its door. Every
tool in this project passed them, because they place legal, supported, affordable blocks in the
right shape. A casino with two games that work and two that look like they work is not a refined
experience, it is a trap.

### AN ANALOG VALUE CANNOT TRAVEL

The rule the whole subsystem turns on, and seven failed displays paid for it. A roll of 4 reaches
**four blocks** of dust. Any link, climb or fan-out spends that reach before the display gets it,
and a repeater carries the signal only by DESTROYING the value (it outputs 15). So there are
exactly two legal shapes, and both surviving games are one of them: the display sits AT the
comparator, or the decision is made where the value still exists and only a BOOLEAN travels.

### Four faults, none visible to anything but simulation

Every one of these placed legal, supported, affordable blocks and passed the audit, the BOM and
every render. Two of them CANCELLED EACH OTHER, which is the most expensive kind to have.

- **A HELD INPUT MUST BECOME AN EDGE BEFORE IT TRAVELS.** The pulse was built in the pit, so the
  run from the button carried the button's own line down the climb - a held button parked a
  permanent 15 on dust beside the comparator's path, the threshold's side input read it, and the
  machine paid nothing until the player let go. It fired correctly on a 4-tick press, which is
  exactly why it survived: **the machine worked for the input a test sends and failed for the
  input a player gives.**
- **A THRESHOLD IS A DISTANCE, so nothing may be laid in front of it.** The gate was joined to the
  comparator with `_link`, and that run decays the very quantity the gate exists to measure. The
  gate now sits ON the comparator's own output cell. Moving the pulse revealed this, because the
  held 15 had been subtracting every loss away - fix one and the other appears.
- **TWO SIGNALS MUST NOT SHARE A LANE.** With both fixed the machine paid on EVERY roll: the
  button's descent ran along the very cells the threshold occupies, so the gate's dust and the
  button's dust were the same dust and a press delivered a level of 8 straight into the boost. The
  cause was one level down again - **`connect` cannot make a pure vertical drop** (a dust staircase
  needs a block of run per course), and given no room to descend backwards it descended FORWARDS
  through the gate. The descent starts five blocks behind the pit now and lands on its target.
- **ANYTHING DOWNSTREAM OF A VARIABLE-LENGTH RUN MUST BE MEASURED FROM ITS END.** The collection
  barrel was at a fixed offset: behind the dropper at 3 outcomes, ON it at 2. The two-outcome game
  had no payout at all while the three-outcome one worked - one config value apart, both clean.
  And that barrel is **not decoration**: it is the solid block carrying the boosted signal into the
  dropper. Moved aside "to avoid a collision", every payout at every set of odds stopped at once.

### The one hazard that is asserted rather than fixed

**A stuck item in the randomiser's hopper pays continuously.** The comparator reads the hopper the
whole time; the button only makes the dropper eject, so at rest the hopper is empty and nothing
fires. An item LEFT there is a winning level standing for ever against an edge that never falls,
and the house pays until the barrel is empty. `test_A_STUCK_ITEM_IN_THE_HOPPER_PAYS_CONTINUOUSLY`
pins it deliberately: the fix is a latch-and-reset stage that has not been built, and a hazard
nobody has written down is one nobody checks for. **Load the dropper, never the hopper.**

### Also worth keeping

- **The odds are known, or the game does not exist.** minecraft.wiki gives an equal-probability
  item mix for exactly two fan-outs, so `RNG_MIXES` holds 2 and 3 and `randomiser` RAISES on
  anything else. A house that cannot state its own odds cannot know whether it is losing money.
  The mix is recorded on the build in `stock`, because the simulator has no entities and cannot
  check that the dropper was loaded right - the one thing it can do is say exactly what to put in.
- **The layout is a centre-out grid** (`planner.bays`), not first-fit: first-fit used 6% of the
  plot and left House Bank 3 with NO SITE. All 32 modules place now.
- **The reference casino is 135x105 and does not fit.** It is 185,198 blocks in
  `reference/casino_chirurg.litematic` and the palette is derived from it by measurement
  (`palette.affordable_like`: quartz -> white_wool at 24 RGB, black glass -> black_wool at 10),
  because its own materials are expensive here. The plot is 99x99; the answer is to STACK.

## The casino became a BUILDING (2026-08-31)

Jack, on the first placed version: *"its not clear what any of the games are, how to play them...
we need signs... lets put them into proper rooms, and design the entire casino around it... this is
just random platforms of shit."* All correct. 29 open bays scattered over a void plot, nothing
saying what any of them was.

**30 designs, 17,138 blocks, 37 signs, 0 overlap and 0 placement problems.**

### THIS PROJECT HAD NEVER PLACED A SIGN

The writer emits tile entities and the pipeline shifts them when a design is padded - both have
worked for a year - and `Canvas` had no way to make one, so nothing above that layer could. A room
with no sign is a room nobody can be told the rules in, which is exactly the complaint.

`Canvas.sign_text` and `World.sign` close it. Three things they had to get right:

- **26.x nests the lines under `front_text`/`back_text` as a `messages` list of JSON strings, and
  there are ALWAYS FOUR.** A sign with two lines still stores four; a shorter list is a sign the
  game refuses to load, so the padding is done in the helper rather than at every caller.
- **The BLOCK and the TEXT are separate things** - a palette entry and a tile entity, in different
  halves of the file - so `put` places the sign and `sign` says what it reads.
- **Text is only carried across if the BLOCK survived.** A design is remaining work and cells get
  deferred or trimmed, so a sign's text can outlive its sign, and a tile entity with no block is a
  corrupt region rather than a harmless leftover.

**FIFTEEN CHARACTERS IS THE LINE.** "lamps show your roll" is twenty and clips mid-word; `_copy`
asserts the width, because the failure only appears in a screenshot after the build is placed.

**The odds are ON the sign** - "1 in 3", "pays 1 prize". A house that will not print its odds is a
house that does not know them, and `RNG_MIXES` holds only the two item mixes with a measured
uniform result.

### A GAME IS A ROOM, NOT A PLATFORM

Four walls, one doorway, a ceiling, a skirting, a cornice, corner pilasters, two lanterns and two
signs. Deliberately ordinary: **what makes voxels read as architecture is regularity and openings**,
which the void tower settled when a jagged ruin was rejected on sight and a plain regular one with a
door and window slits worked immediately.

- **The doorway is left EMPTY by the wall loop, never punched afterwards.** Building the ring and
  cutting a hole repaints cells that already exist - the void tower's crenellations shipped as a
  plain drum for exactly this reason and nothing about the code looked wrong.
- **A CASINO IS DARK WITH BRIGHT TRIM, NOT A WHITE BOX.** Built white-field / grey-wall /
  grey-ceiling it rendered as a bathroom. The field is `black_wool` (21), the border and cornice
  `white_wool` (236), the walls `smooth_stone` (159), the ceiling and pilasters `deepslate_bricks`
  (71) - the 215-point cheap value range this project measured ACROSS families after three separate
  notes here wrongly concluded, from searching WITHIN one family, that this economy has none.
- **Stairs as skirting and cornice.** The corpus says we place stairs at a seventh of the rate
  outside builders do; this is the first generator to use them as trim rather than as a staircase.

### The hall, and why it is built LAST but placed FIRST

`kind: hall` - an 88x88 floor, a perimeter wall with plinth, string course and parapet, a 3-wide
gateway, twelve lanterns and the casino's name over the door. 9,874 blocks.

- **NO ROOF, deliberately.** Every room has its own ceiling, and an 88x88 lid is seven thousand
  blocks nobody inside a room can see. What reads from outside is the WALL and the GATEWAY.
- **It is the last module in the theme, and that order is load-bearing.** `emit` chains `defer_to`
  down the list, so a later module yields any cell an earlier one claimed. Built first, the hall's
  floor would take every room's floor and the rooms would stop being rooms. Built last it lays only
  the ground BETWEEN them, which is what a hall is.
- **A COVERING MODULE IS NOT COMPETING FOR SPACE, IT IS THE SPACE.** Asked to find a free bay it
  correctly reported NO SITE, because by then the plane is full of rooms. `anchor: cover` centres it
  on the plot and claims nothing.
- It is also the fix for *nothing to place against*: the plot is void, and that is why every design
  reported free-floating cells.

### Four faults, all caught by checks that already existed

- **Carpet laid IN the floor course had nothing under it** - six floating carpets per room, rule 9,
  and the audit caught it exactly as designed. The carpet goes ON the floor.
- **A REDSTONE LAMP IS A DARK BLOCK UNTIL SOMETHING POWERS IT.** Two per room, wired to nothing;
  the circuit inspection said so on the first run. Lanterns hung from the ceiling need no signal
  and cost an iron ingot and a torch.
- **The spread report read `at` as a minimum corner.** A game runs from at-6 to at+9 and the hall
  from at-87 to at, so the report claimed the casino spilled 80 blocks past the plot and used 113%
  of it while every module was inside. A boundary report that cries wolf is one nobody reads.
- **Three of my own tests measured the MODEL BOX rather than the room.** The box is 16x10 because
  the machine and payout run out under the floor; the room is 10x6. A ceiling test sampling the
  box's centre column, and a wall test checking the box's far edge, both failed on a correct build.

### THE HALL WAS DRAWN OVER EVERY ROOM, AND ALL THIRTY DESIGNS REPORTED `overlap 0`

Jack, on the placed casino: *"lots of empty boxes, and then things arent shown right."* The cause
was one line in `planner.emit`:

    if prev: cfg["finish"]["defer_to"] = [f"out/{prev}.litematic"]      # the PREVIOUS one only

Chained one-to-one that is correct for a line of modules that touch their neighbour, and wrong for
a hall that touches all of them. The hall deferred to `House Bank 3` alone and laid its floor
across all eighteen room floors - **60 cells each, the whole floor of every room** - so in game two
placements fought over one cell.

**NOTHING CAUGHT IT, AND THE REASON GENERALISES.** `finish.verify_against` audits a design against
the CAPTURE, and the capture does not contain the other designs. Every module honestly reported
`overlap 0` against the world while colliding with its neighbours. Cross-design overlap is a
DIFFERENT question and needs its own check; `test_no_two_modules_of_a_plan_share_a_cell` is it, and
it compares every pair of a plan's designs in world coordinates. The measured tell was in the
material counts all along: the union held **64 black_wool where eighteen room floors needed 558**.

Three more things came out of the same look:

- **SEVEN THOUSAND IDENTICAL CELLS IS NOT A FLOOR, IT IS A SLAB.** The hall was 68% smooth_stone
  and read exactly like the platforms it replaced. A world-aligned grid of dark lines every eight,
  a stone/smooth-stone checker between them and a red aisle on the entrance axis takes the
  dominant block to 43% and costs nothing - all four materials are cheap.
- **A GAME ROOM IS A SHOPFRONT, NOT A CELL.** With a two-wide door the floor was eighteen sealed
  grey cubes: you could not tell one from another or see a game being played. The opening is four
  wide now, and the wall survives as a frame and a lintel - which is what carries the sign.
- **`defer_to` IS APPLIED AFTER THE GENERATOR RUNS.** An aisle drawn as carpet at floor+1 shipped
  ten floating cells: at build time the floor was there, and by the time the design was written
  the cells yielded to a room were gone and the carpet was standing on air. The aisle is a floor
  MATERIAL now - a cell in the floor course cannot outlive its support, because it is the support.

### FORTY-SIX PIECES, AND EVERY DESIGN SAID 0 PROBLEMS

Jack: *"lots of things floating."* A 6-connected component count over the whole plan plus the
island found **one building of 15,710 cells and 45 fragments hanging in open air.** Two causes,
neither of them visible to a per-design check:

- **THE THEME DECLARED A MEZZANINE AND NOTHING EVER BUILT ONE.** `floors: [{Gaming Floor, +0},
  {Mezzanine, +12}]` lifted eleven modules eleven blocks and left them there - no deck, no
  balustrade, no flight. **A floor entry is a LIFT, and a lift is only legitimate once something
  carries what is lifted.** A gallery is a fine thing to build and it is a BUILD; until it exists
  everything stands on the ground. `test_the_whole_plan_is_one_connected_piece` and a check on
  `THEMES` both pin it.
- **A WALL SIGN GOES IN THE CELL IN FRONT OF A WALL.** The rules sign was placed in the middle of
  each room, attached to nothing - eighteen single-cell strays, one per game - and the door sign
  was written INSIDE the wall plane, overwriting the lintel it was meant to hang from. `facing` is
  the direction the text LOOKS, which is away from the block it is fixed to. The door sign is on
  the outside face now, where a shop sign goes; the rules are on the back wall facing whoever has
  walked in.

**A DESIGN IS JUDGED IN CONTEXT, AND THE CONTEXT FOR A PLAN IS THE REST OF THE PLAN.** Rule 2 has
said "verify in context, never in isolation" since the first island, and `verify_against` has only
ever meant *against the capture*. For a thirty-module plan that is the wrong context twice over -
it misses cross-design collisions and it misses floating work. Both now have their own test, and
both found real defects the moment they were written.

Final state: **one component, 16,028 cells, 0 clashes, 0 placement problems**, dominant block 43%.

**Still open:** the interior has been verified by audit, simulation, cross-design overlap,
connectivity and block counts, not by eye -
`tools/look.py` cannot render these because the casino sidecar records `facing` as a word and it
wants a vector. Place one room and look at it before building thirty.

### The casino ships as FOUR LAYERS, not thirty fragments (2026-08-31)

Jack, after three rounds of fixes: *"its still showing basically empty floors with holes in it for
redstone etc, and nothing above it, can we instead just make this simple and split this into steps,
e.g. floor, redstone, design."* He is right, and the diagnosis is his: **a design that DEFERS is
incomplete on its own.**

`finish.defer_to` settles which design owns a shared cell. That is exactly right for ownership and
exactly wrong for looking at the result - every module becomes a fragment with holes in it where a
neighbour won, and thirty of them loaded together are thirty overlapping boxes each missing pieces.
"Empty floors with holes for redstone and nothing above it" is a precise description of the hall
on its own.

    python -m mcbuild layers casino --floor 203 --ship

    Casino 1 Floor      7,640    the walking surface
    Casino 2 Machines   2,951    everything under it: pits, wire, droppers
    Casino 3 Walls      4,925    everything over it: rooms, ceilings, the perimeter
    Casino 4 Fittings     368    signs, lanterns, buttons, carpet

**LAYERS CANNOT COLLIDE, SO NOTHING DEFERS.** `_which(name, y, floor_y)` is a function of the CELL
- what it is and where it sits - so every cell lands in exactly one layer by construction. There
is no ownership question left to settle and no design is missing anything. Each loads on its own
and the four together are the whole casino with nothing hidden. Verified as a partition rather than
asserted: 0 shared cells, 0 lost, 0 invented, **0 block-state changes** (a stair's facing and a
sign's facing are decisions, and a slice that dropped `Properties` would look identical in every
render here and be wrong in game).

Two rules inside it:

- **A MACHINE STAYS WHOLE WHEREVER IT SITS.** Material wins over height: a mechanism half under the
  floor and half above it is one machine, and splitting it by height gives two layers neither of
  which works. A lamp above the floor is a display and goes to Fittings; the wire that drives it
  does not.
- **A SIGN'S TEXT FOLLOWS ITS BLOCK.** Left in another layer it would be a tile entity with no
  block, which is a corrupt region rather than a lost line. All 37 land in Fittings.

It also gives the build ORDER that matches how you would actually build it: stand the floor, hang
the machines under it, raise the walls, fit it out. `sync.yaml` tracks the four, so `/cscan place`
places four complete designs rather than thirty fragments.

**The thirty module designs are kept**, because they are what the plan, the circuit verification
and the cross-design checks are written against. They are simply no longer what you place.

### The games were two games wearing four names (2026-08-31)

Jack: *"audit all the games and make sure theyr unique, different."* Measured cell-for-cell, they
were not:

| | identical machine cells |
|---|---|
| High Roller vs Coin Toss | **98.7%** |
| One In Three vs Even Money | **94.6%** |

**`threshold` PAYS ON A MAXIMUM, AND A MAXIMUM IS THE SAME GAME WHATEVER NUMBER YOU PUT IN IT.**
Changing `outcomes` from 3 to 2 changes the odds and nothing else; shipping that under a different
name over a different door is what made the floor read as one room eighteen times. Both odds
variants are deleted.

**MEASURE THE MACHINE, NOT THE ROOM.** The first comparison ran over whole designs and reported
everything as 94-99% alike including games that are genuinely different - because a room is ~330
cells and a machine ~150, so the metric was measuring the walls. Sliced to the mechanism the four
survivors sit at 68-89%, and the shared part is exactly right: they all roll dice. What differs is
the resolution.

Two new mechanics, each a new primitive verified by simulation before any of it was built:

- **`circuits.window(low, high)` - an exact-value gate**, and the first mechanic here that is not
  a maximum. An AND-NOT: two perpendicular taps off one dust line, `low-1` and `high-1` along, into
  a comparator in SUBTRACT mode. 15 - 0 = 15 when only the low tap fired, 15 - 15 = 0 when both
  did. `Lucky Two` pays on exactly 2 out of {1,2,4} - the middle wins and the top LOSES, which no
  threshold can express.
- **`circuits.duel()` - two rolls compared.** A comparator in COMPARE mode passes its back signal
  when back >= side, so out of {1,2,4} there are nine equally likely pairs and six have A >= B:
  **2 in 3, countable**, which is this file's bar for shipping a game at all.

Three faults inside them, each of which built cleanly and simulated wrong:

- **A SIDE INPUT IS READ AS A LEVEL, so it must arrive at FULL STRENGTH.** The window's HIGH tap
  was routed to the gate as plain dust, decayed on the way, and the subtract gave 15 - 13 = **2**:
  the gate "passed" a level it exists to block, quietly and by two. A repeater at the side delivers
  a clean 15.
- **The first window put both taps on one perpendicular** and the side input landed TWO cells from
  the comparator, so it never arrived and the window was a threshold with extra parts.
- **THE DUEL PAID ON ALL NINE COMBINATIONS.** The house's randomiser was placed on its own lane and
  `_link`ed to the comparator's side - and **an analog value cannot travel**, so the side read 0
  and `A >= 0` is true for every A. Both rolls are produced ADJACENT to the gate now, and the
  geometry is derived from that rather than chosen: a randomiser's comparator sits at `pos + dx`
  and fires along `facing`, so the house goes two cells back along the side's own line.

**A PLAYER CANNOT SEE A CIRCUIT.** Four verified mechanics in four identical grey rooms are four
identical rooms, so `KIND_ACCENT` gives each one its border, carpet and pilasters: High Roller
yellow, One In Three red, Lucky Two lime, Duel light blue. That is what tells them apart from the
aisle, which is the distance most of them are read from.

The lineup is now **18 games over 4 mechanics** - 5 High Roller, 5 One In Three, 4 Lucky Two,
4 Duel - every contract asserted by simulation, every one stating its odds on its own sign.

### The Colour Wheel, and what a redstone casino CANNOT be (2026-08-31)

Jack: *"majority of the games look like theyre identical, what about things like roulette, or other
games, blackjack."* The first half is right for a reason colour could not fix: a bar, a threshold,
a window and a comparator all read as **a button in a grey box**. Four verified mechanics in four
identical booths are four identical rooms.

**`wheel` is the first game here with a different SHAPE as well as a different circuit** - a sunken
round bowl with a rail, read from above, no walls at all - and the first that is a DECODER: one
roll, three outputs, exactly one live. Red/green/black, 1 in 3, `test_the_wheel_lights_exactly_one_
pocket_in_every_orientation` asserts it at all four facings.

Four faults inside it, each of which built cleanly and simulated wrong:

- **A SPUR OFF THE SOURCE DUST DOES NOT WORK.** Three branches off the comparator's output cell
  left every pocket dark, because dust adjacent to that cell is already a level down and every gate
  is off by one. A hopper has four horizontal sides; three comparators read the container itself.
- **DUST BELOW A LAMP DOES NOT LIGHT IT.** Every gate fired correctly and not one lamp came on. A
  repeater into a solid block lights a lamp above it; simpler still, sinking the bowl to the
  machine's own course puts every pocket in the cell NEXT to its gate, so there is no journey.
- **DECORATION LAID BEFORE STRUCTURE EATS STRUCTURE.** The first pocket's colour ring was painted
  into cells the third gate had not reached, `_lay` skipped them as occupied, and the level-4 gate
  shipped with its subtract comparator replaced by red wool - so a roll of 4 lit the level-1
  pocket. Every gate is built before any pocket now.
- **ADJACENT DUST IS ONE NETWORK: CLEARANCE, NOT JUST NO OVERLAP.** The gate arrangement was
  SEARCHED, and the first search demanded only that no two gates share a cell. The winner put gate
  1's output one block from gate 4's dust; a roll of 4 pushed 15 into the level-1 pocket. The
  search requires a real gap now and the test re-derives it, so a change to `window`'s footprint
  fails here rather than in game.

**And the biggest module must be sited FIRST.** `bays` packs in list order, so the booths filled the
grid and the 23x21 wheel reported NO SITE three times. A module is not unsiteable because it is
late.

#### What cannot be built, and why it is not a matter of effort

- **BLACKJACK IS OUT OF REACH.** It needs card identity, a running total, a dealer rule and a hit/
  stand decision - state that has to be held and compared across turns. Redstone can do it with
  enough hardware, but nothing in `circuits.py` could verify it and this file's rule is that a game
  ships only with a contract asserted by simulation. Building it unverified is how `chase` and
  `vault` happened.
- **A 37-POCKET ROULETTE IS OUT OF REACH FOR THE ODDS, NOT THE WIRING.** `RNG_MIXES` holds only the
  two item mixes whose distribution minecraft.wiki gives as uniform. A wheel with more pockets
  would be a wheel whose odds we are inventing, and **a house that cannot state its odds does not
  know them**. Three pockets is what three measured outcomes buys - so it is a COLOUR bet, which is
  a real roulette bet at odds we can print on the sign.
- Two rolls would give nine uniform outcomes and a proper wheel; it needs nine AND gates and is a
  genuine piece of work rather than a tweak. That is the honest next step if a bigger wheel matters.

The lineup is **14 games over 5 mechanics** - 3 High Roller, 3 One In Three, 3 Lucky Two, 3 Duel,
2 Colour Wheel - every contract asserted by simulation, every one stating its odds on its own sign.

### `defer_to` is gone from the casino (2026-08-31)

Jack: *"can we stop with the defer crap so i can actually see everything in totality in the place
simulation."* Yes, and it should have gone two rounds earlier.

**`defer_to` RESOLVES A SHARED CELL BY DELETING IT FROM THE LOSER.** That is correct for cell
ownership and it means every module ships as a fragment with holes in it - so looking at the casino
meant loading a pile of overlapping designs each missing pieces. Three separate rounds of confusion
came out of that and none of them was ever about the casino.

    python -m mcbuild layers casino --floor 203 --ship

    Casino Complete   14,874    the whole thing, one design - this is what you place and look at
    Casino 1 Floor     7,636    the build steps, if you want to place it in stages
    Casino 2 Machines  2,988
    Casino 3 Walls     4,019
    Casino 4 Fittings    231

- **The modules are INTERMEDIATE artifacts now.** Each is generated WHOLE, overlaps and all, and no
  casino config carries a `defer_to` - `test_no_module_config_defers_to_another` keeps it that way,
  because deferring is the obvious way to stop two designs claiming a cell and is easy to
  reintroduce by accident.
- **THE PRECEDENCE LIVES IN ONE PLACE AND IS REPORTED.** `layers.slice_plan` applies first-writer-
  wins in plan order - the same precedence `defer_to` used to enforce - and prints the count:
  **923 contested cells**, which is the hall's floor under the rooms. Silently applied it is the
  same trap; printed, it is a number you can check.
- `Casino Complete` is verified to equal the union of the four layers exactly: same cells, same
  block states, and one connected component with the island.

**Two tests changed with the decision**, which is the rule this file keeps relearning: one asserted
that no two modules share a cell, and the other compared the layers against a raw union of the
modules. Both were true only because of deferring. They now assert that the overlap EXISTS, that it
is resolved deterministically, and that the resolved result is exactly the design you place - and
the first of them fails if anything quietly starts deferring again.

`sync.yaml` tracks **one** design, so `/cscan place` puts down the whole casino with nothing hidden.
The layers stay in the folder and can be placed by name when it is time to build in stages.
