# Agent Operating Guide

## Mission

This repository generates sophisticated, functional Minecraft Java 1.19 Skyblock builds. Treat the target as a bounded Skyblock island, not an infinite overworld. Preserve existing user work and the Isthmus unless a task explicitly includes it.

## Authoritative workflow

For substantial work, follow:

```text
strict WorldSpec → spatial/district solve → greybox → review → detailed generation
→ cache → chunk assembly → worldvalidate → visual packet → promotion
```

Use `python -m mcbuild worldflow <strict-world.json> --out <directory>` to prepare infrastructure, greyboxes, strict module configs, and tickets.

## Hard rules

- Target the locked `skyblock-1.19` profile. Never assume locally available newer blocks are placeable.
- Every public module needs purpose, footprint, plot, typed anchors, access point, return route, service access, scenarios, budget, and review views.
- Every ride needs separate queue, boarding, exit, and maintenance interfaces.
- Generate a greybox before expensive detail. Do not detail a rejected layout.
- Use WorldSpec routes/plots/protected areas/view corridors; do not place into them ad hoc.
- Keep public paths, queues, exits, and service corridors distinct.
- Run focused tests after edits. Preserve unrelated changes.

## Core documents

- `PARK_VERTICAL_MASTERPLAN.md`: park visual and vertical direction.
- `PARK_COMPLETION_MASTERPLAN.md`: the final land-by-land build inventory, balance targets, dependencies, and completion gates.
- `PARK_FUN_AUDIT.md`: mandatory player-verb/outcome audit, reduced passive program, and Isthmus/Wyrm redesign brief.
- `PARK_REPROGRAM_PLAN.md`: current authoritative park program; retires Hollow for Prismworks and includes the full Isthmus/grass-spend plan.
- `PRISMWORKS_PARKOUR_BRIEF.md`: detailed no-PvP Prism Ascent contract, mechanics, safety, visibility, and paid-run boundaries.
- `PARK_MECHANICS_ARCHITECTURE.md`: park-wide mechanics tiers, bubble-launch parkour contract, per-zone budgets, and local versus in-game proof gates.
- `PARK_600X200_AUDIT.md`: authoritative offering audit, keep/rework/retire portfolio, 600×200 allocation, vertical reservations, and build-now/proof-later cut line.
- `PARK_FINAL_ARCHITECTED_PLAN.md`: final authoritative build inventory and placement program for all three lands and both Isthmus reaches; use this before generating park artifacts.
- `PRISMWORKS_GENERATOR.md`: generator boundary, configs, required public-module contracts, and in-game proof obligations for Prismworks.
- `ANIMAL_SETPIECE_STANDARD.md`: required anatomy, connectivity, material, and human multi-view release standards for all animal setpieces.
- `PARK_EXPERIENCE_REALITY_AUDIT.md`: final player-value, social, buildability, server-mechanics, and launch-gate audit for the retained park program.
- `park_final.world.json`: machine-checkable 200×600 free-first site plan with 22 modules, public/service circulation, budgets, dependencies, and explicit live-mechanics gates.
- `PARK_BUILD_EXECUTION.md`: registration boundary and exact phased construction/proof handoff for the WorldSpec plan.
- `PARK_FULL_BUILD_SPEC.md`: detailed lot-by-lot construction cards, vertical reservations, guest flows, interfaces, visual direction, and mechanics ownership for every retained module.
- `PARK_VISUAL_AND_BUDGET_SPEC.md`: locked statue/setpiece inventory, landmark visual rules, material policy, and 265k-block target budget.
- `REFERENCE_ANALYSIS.md`: external-reference grammar, scale limits, and what may or may not be inherited.
- `PARK_OVERHAUL.md`, `PARK_MIDWAY.md`, `PARK_FRONTIER.md`, `PARK_HOLLOW.md`: land rebuild contracts.
- `WORLDSPEC.md`: bounded Skyblock world format.
- `GENERATION_WORKFLOW.md`: performance and promotion workflow.
- `DESIGN_COMPILER.md`, `DESIGN_QUALITY.md`, `PARALLEL_GENERATION.md`, `MECHANICS.md`, `REDSTONE.md`: implementation contracts.
