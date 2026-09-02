# Generation Platform — Complex, Accurate Minecraft Builds

The project now has a program-driven architecture layer in addition to individual generators. It is designed for bounded Skyblock islands: buildings, rides, bridges, paths, and vertically layered districts can become more impressive and operationally believable without pretending the island is an infinite terrain world.

## Build workflow

```text
Skyblock site → platform/infrastructure → blueprint → district contract → themed generator → mechanics/route checks → renders → promotion
```

1. Declare the island anchor, build plane, bounded envelope, and protected cells/areas from the world capture.
2. Write a JSON building brief: purpose, dimensions, style, floors, and optional room program.
2. Compile it with `python -m mcbuild blueprint brief.json --out building.blueprint.json --enforce`.
3. Give the resulting footprint, room program, façade/roof decision, structural grid, and named anchors to a themed generator.
4. Assemble generator modules through `mcbuild.district.audit` and the existing typed composition/link checks.
5. Run the existing mechanics, journey, scenario, render, and parallel promotion gates.

## Included building programs

`shop`, `restaurant`, `ride_station`, `haunted_walkthrough`, `hotel_lobby`, `workshop`, and `gallery` include real public rooms, service/backstage rooms, circulation, façade/roof direction, structural support rhythm, and world-link-ready anchors.

Ride stations and walkthroughs explicitly require queue, boarding, ride-exit, public entry/exit, and service interfaces. This stops a structurally attractive ride façade from being generated without a usable player flow.

## Quality contracts

The compiler checks minimum footprint/headroom, a public purpose, backstage provision, bounded structural spans, and required public/service/ride interfaces. District audit adds role-specific requirements and validates typed world-space links and required journey endpoints before block generation.

The next generator work should consume compiled blueprints rather than manually inventing doors, rooms, queues, and support placement. For example, a Frontier saloon consumes `restaurant`; Ghost Train station consumes `ride_station`; a Hollow Manor consumes `haunted_walkthrough`; a bridge generator consumes declared deck/path anchors and structural span limits.

## How to extend it

Add a program only when its function recurs. Give it rooms, public/service access, a minimum viable footprint, and acceptance checks. Add styles as controlled palette/roof/façade grammars. Keep decorative variation in themed generators; keep human movement, structural logic, and interfaces in the shared compiler.
