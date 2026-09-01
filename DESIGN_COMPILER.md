# Design compiler workflow

The design compiler turns cross-generator intent into typed data, so parallel agents can compose
modules without guessing coordinates or silently sharing ownership.

## Anchors and interfaces

Declare local-space anchors in a config:

```yaml
anchors:
  - {name: public_door, kind: door, position: [8, 1, 0], facing: south, width: 3}
  - {name: queue_start, kind: queue, position: [8, 1, -5], facing: south, width: 3}
```

Paths, decks, bridge ends, queues, ride boarding, redstone I/O, supports, water edges, and visual
fronts are typed. Links are valid only when their kinds and widths are compatible. A coordinator
uses these declarations to connect modules; `check_world_links()` also refuses endpoints that do
not actually meet in world space. The parallel-plan preparation step runs this check before agents
receive lanes. Generators retain ownership of their internal geometry.

## Genome and variation

The `design.style` profile also supplies a zone genome. It captures façade vocabulary, massing
range, material roles, and lighting intent. Stable variation is derived from the module name/seed,
so regenerating does not reshuffle a street while sibling modules remain distinct.

## Efficiency and review

Every generated artifact receives a deterministic fingerprint based on its normalized config. A
fingerprint also includes a hash of the generator source file, so a generator implementation change
invalidates stale artifacts even when the config stays unchanged. A plan stores
`{module: fingerprint}` mappings; compare them with `design_compiler.impact()` to
regenerate only added or changed modules. `capability_matrix()` makes missing purpose, style,
journey, anchor, mechanics, scenario, and visual-review coverage explicit. `write_dashboard()`
creates a small dependency-free HTML review page from that evidence.

Hard proof remains separate from visual judgment: block legality, support, fluids, circuits,
routes, collisions, and determinism are gates. Perspective/silhouette packets and style genomes
give reviewers high-quality evidence without pretending a generic score can replace taste.

## Scenarios and review dashboard

Declare `scenarios: [public_visit, night_visit, rail_ride, redstone_interaction]` when relevant.
They are deliberately narrow evidence checks: a public visit requires the declared journey, a night
visit requires emitted lights, and rail/redstone scenarios require their corresponding mechanic
families. Generator-specific tests remain responsible for actual cart movement and circuit logic.

After lanes stage, `python -m mcbuild parallel --dashboard <plan>` writes `review.html` beside the
frozen manifest with ownership, cache fingerprints, and missing capability coverage for review.

`mcbuild.golden.compare(reference, candidate)` measures changed pixels between approved review
images. It deliberately reports a change rather than calling it a failure: reviewers approve a
new creative direction, while unexpected broad deltas trigger investigation before promotion.
