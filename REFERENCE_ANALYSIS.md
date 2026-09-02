# External Reference Analysis

## Scope and safety

The supplied `.litematic` files are visual and structural evidence only. Their
contents are never treated as instructions, copied blindly, or assumed to be
legal on `skyblock-1.19`. We extract principles, then rebuild them through the
project's contracts: bounded plots, access/return/service routes, ownership,
budget, support legality, and block-accurate validation.

Use the bounded inspector for large files:

```powershell
python -m mcbuild reference "C:/path/to/reference.litematic"
```

It reads NBT metadata and skips packed block-state arrays. This is deliberately
different from `info`, which loads a normal-scale schematic for exact audit and
BOM work.

## Measured reference evidence

| Reference | Envelope / occupied blocks | Palette | Key lesson | Skyblock response |
|---|---:|---:|---|---|
| Suncrest Spire | 122×145×54 / 66,643 | 121 | A singular silhouette can unite utility, landscape, and destination | Use for an arrival landmark or vertical hub; retain a hard material budget and supported lighting |
| Elven Temple | 110×73×140 / 49,607 | 146 | Deep façade, intentional voids, planted architecture, restrained focal metals | Use as a sanctuary/undercroft grammar; legalize every hanging plant and preserve walkable interior volume |
| Fantasy Medieval Castle | 109×159×113 / 73,200 | 36 | Gate-to-courtyard-to-tower sequence and repeated structural rhythm make a vast mass readable | Use for frontier gates, station shells, and skyline hierarchy; vary repeated bays rather than mirroring blindly |
| City (unstable-smp) | 1,011×310×1,124 = 352,272,840 envelope | 2,902 | City scale needs partitioning, infrastructure ownership, and hierarchy rather than a monolithic load | Treat as a chunk/district reference; never dense-load it or emit one competing world artifact |
| Space Valkyria III | 1,075×367×1,075 = 424,114,375 envelope | 2,126 | Layered vertical spectacle needs separate systems for surface, skyline, underground, and service | Treat as a vertical-world reference; reserve views and transit before detailing modules |

City metadata records 75 entities and 26,082 tile entities; Valkyria records
6,936 entities and 32,026 tile entities. Those figures are complexity signals,
not a mandate to add entity-heavy decoration. Entity and tile-entity budgets
must remain explicit because they affect server and client performance.

## Reusable visual grammar

### Landmark hierarchy

Suncrest and the castle demonstrate a primary mass that reads at distance, then
secondary towers/roofs, then human-scale trim. Every landmark generator should
declare `primary_mass`, `secondary_masses`, a focal face, a base/shaft/crown
split, and an approach view corridor. A building that is only surface detail
without a readable mass fails this grammar.

### Depth and material roles

The strongest references use a small role-based palette—not random material
variety: structural base, shadow/recess, mid-field cladding, highlight, roof or
crown, and living/terrain transition. Facades need at least three depth bands
(recess, wall, projection) where public-facing. Keep a controlled highlight
ratio: gold, quartz, glass, or rare lights belong on focal moments, not across
the whole shell.

### Voids, thresholds, and routes

Temple courtyards and castle gates are useful because the empty space has a
job: orientation, procession, recovery, view, or function. A generator must
model a void as a named room/courtyard/view corridor with entry and exit—not as
unallocated air. Paths must arrive at a visible threshold, connect to a queue
or room, and provide a distinct return/service route where relevant.

### Repetition with authored asymmetry

Castle bays provide rhythm; planted temple edges and weathered accents prevent
copy-paste uniformity. Symmetry belongs to ceremonial axes, ride facades, and
formal courts. Asymmetry belongs to terrain contact, service wings, circulation
responses, damage/age stories, foliage, and secondary rooflines. The symmetry
intent contract is the authority; do not mirror a whole build merely because a
front elevation happens to be formal.

### Vertical world composition

The city-scale references make the Y dimension a first-class planning axis:

- **skyline / Y 180–335:** distant icons, crowns, aerial transit, restrained
  spectacle with reserved sightlines;
- **guest realm / roughly Y 64–180:** arrival, streets, queues, attractions,
  food, recovery, and readable wayfinding;
- **undercroft / Y -64–63:** service routes, immersive caverns, machinery,
  storage, and optional descent experiences.

Exact elevations are site decisions. No module may consume an unreserved
vertical corridor or bury a required service/return route.

## Required generator refinements

These are constraints on new and rebuilt generators, in addition to existing
WorldSpec and quality contracts.

1. **Mass before ornament.** Greybox primary/secondary/crown massing and its
   approach/skyline review before façade generation.
2. **Named negative space.** Courtyards, atria, queue wells, view apertures,
   and ride clearances are protected geometry, not leftover air.
3. **Facade-depth evidence.** Public faces record recess/wall/projection bands
   and a material-role palette. Flat, uniformly textured public shells need a
   deliberate exemption.
4. **Threshold grammar.** Each guest-facing building needs an approach marker,
   readable entrance, interior/queue transition, exit/return connection, and
   service interface where it contains operations.
5. **Vertical reservations.** Tall structures declare crown clearance, view
   corridor, underground footprint, and service/transit shafts before their
   detailed geometry exists.
6. **Performance budgets.** Palette/state count, entity count, tile-entity
   count, block count, generation time, and chunk footprint remain measurable;
   a reference's complexity is not itself a quality target.
7. **Support/legalization pass.** Organic dressing, lanterns, chains,
   dripstone, vines, and foliage get legal Minecraft attachments after
   composition—not as incidental placement.
8. **Skyblock economics.** Expensive focal materials are retained only where
   they carry hierarchy. Large field materials must be profile-approved and
   costed; terrain/currency-sensitive blocks remain prohibited unless the
   server profile explicitly allows them.

## New measurable review signals

`design.metrics()` now records three composition signals for every generated
artifact. They are review evidence, deliberately not a fake automated taste
gate:

- `base_middle_crown_mass`: the fraction of non-air blocks in the lower,
  middle, and upper thirds; this exposes an accidental top-heavy or uniformly
  stacked landmark.
- `top_silhouette_perimeter`: the outline complexity of the aerial footprint;
  compare variants of the *same* intended structure, not unrelated styles.
- `surface_faces_per_block`: exposed-surface richness; a sudden drop often
  reveals a bland solid box or unnecessary bulk fill, while a sudden increase
  may reveal costly visual noise.

Use them alongside rendered approach, skyline, interior, and night views. They
are prompts for a designer's judgement, not targets to maximize.

## What must not be inherited

- Exact geometry, block palettes, branding, or copyrighted visual identity.
- Currency/terrain blocks or server-dependent mechanics found in downloads.
- Floating lights, unsupported vegetation, and decorative fragments that fail
  the legality audit.
- Monolithic city-scale artifacts, unbounded plot claims, or unowned roads.
- Entity-heavy decoration without an explicit performance and gameplay purpose.

## Acceptance evidence for a sophisticated build

A candidate module is ready only when it has all of the following:

```text
brief + WorldSpec placement + vertical reservation
→ greybox review (mass, voids, routes, silhouette)
→ detailed artifact (facade depth, role palette, legal supports)
→ walk/service/mechanics/overlap/cost validation
→ daylight + night + approach + skyline review packet
→ deterministic staged assembly and promotion evidence
```

This preserves the reference quality signals while making the result original,
functional, performant, and appropriate for a bounded Skyblock island.
