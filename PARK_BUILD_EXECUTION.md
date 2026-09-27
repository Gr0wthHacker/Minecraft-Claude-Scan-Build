# Park Build Execution Handoff

The authoritative program is PARK_FINAL_ARCHITECTED_PLAN.md. The machine-checkable translation is park_final.world.json. Its local x coordinate is the plan V depth and its local z coordinate is the plan U length.

## Produced base

- 5 bounded regions: Frontier, Frontier Reach, Midway, Prism Reach, and Prismworks.
- 22 named modules with plot ownership, public access, role, dependencies, review views, and budget.
- A connected public circulation system plus a separate service spine.
- Chunk-safe infrastructure artifacts generated from the WorldSpec under out/_test/park_final_infrastructure during plan verification.

The WorldSpec compiles under strict schema, navigation, and composition checks. It is a placement plan, not authorization to paste into the live island unchanged.

## Registration boundary

The anchor [97500, 203, 80349] is a provisional registration value inferred from the current park config convention. Before any live paste:

1. load the current island capture;
2. rebase the anchor and build plane against the real marked point;
3. add protected transit, existing completed structures, and protected rim cells;
4. regenerate the plan and infrastructure;
5. compare the re-based chunk artifacts against the capture.

Do not paste provisional local coordinates into the live world.

## Build phases

| Phase | Build | Must be true before promotion |
| --- | --- | --- |
| 1 | infrastructure, safe main paths, thresholds, service spine, protected rims | WorldSpec rebased; paths, exits, and service routes pass assembled-world walk checks |
| 2 | Arrival/Welcome, Trailhead/Mining Square, Foundry Gate, skyline shells, setpiece supports | plots do not consume protected views; animal and skyline visual packets approved |
| 3 | free Carousel/Sky Lift shells, Mine Coaster station/track, games, Array, Prism Ascent practice geometry | each queue/exit/bypass is physically walkable; no paid lock exists |
| 4 | bubbles/catches, cart/projectile test rigs, each game circuit | live player proof for every stated input/output/recovery loop |
| 5 | Vault and Wyrm bounded state machines | visible state, wrong-input recovery, timeout, bypass, and staff reset work |
| 6 | optional grass-payment integration and timed replay | server acceptance/rejection/refund/recovery cases pass |
| 7 | night pass, group session, challenge cadence | players voluntarily retry and gather without circulation failure |

## Live gates intentionally retained

- Runtime minecart and projectile policy.
- Grass payment chest acceptance and recovery behavior.
- Prism Ascent bubble, landing, catch, checkpoint, and new-player proof.
- Resonance Vault and Wyrm state machines.

These are intentionally not substituted with decorative blocks, fake scoreboards, or redstone that has not been tested in the actual server environment.

