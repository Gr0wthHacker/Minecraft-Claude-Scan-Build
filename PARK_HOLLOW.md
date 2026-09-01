# The Hollow / Park Right Rebuild Specification

## Land promise

The Hollow is a cursed old-manor district: guests enter a clock-gate, choose a major haunted experience, then discover games, secrets, and a night market along a looping graveyard street. Keep five major experiences; stop treating eleven small modules as equal attractions.

Flagships are the Hollow Gate, Clock Tower, Haunted Manor, Ghost Train, and The Plummet. Mirror Maze, Ossuary, Vault, Reliquary, and rest/service functions become one purposeful Crypt Market. The Quiet Room becomes a seated food/rest space (**Mourning Parlour**) or is removed.

## Spatial program and player journey

```text
Centre / connector → Hollow Gate → Arrival Court + map/services → Clock Street
       ├─ Manor Quarter: Manor → graveyard-loop exit → Seance/photo beat
       ├─ Tower Quarter: Plummet queue → lift/jump/pool → wet return
       └─ Ghost Train station → Crypt Market (maze, puzzle, prize, rest) → return loop → Gate
```

The gate frames the Clock Tower. The tower is the forward visual pull. The path system is a 5-wide gate-to-station Clock Street plus a perimeter return loop, not a set of separate spur paths.

| District | Purpose | Required content |
|---|---|---|
| Arrival Court | commitment/orientation | map, wait board, guest services/lockers/rest point, broad queue-free court, Manor/Tower choices |
| Manor Quarter | flagship walkthrough | entry court, 3–5-wide queue, lower graveyard exit loop, Seance as narrative parlor, cemetery photo beat |
| Tower Quarter | vertical thrill | Clock Tower landmark/observation, Plummet side plaza, queue, spectator rail, wet exit, service boundary |
| Ghost Train Station | kinetic capacity ride | queue, distinct boarding platform, exit toward market, status board, visible track segments |
| Crypt Market | discovery/recovery | Mirror Maze, Ossuary puzzle/reward, Vault merged as game, Reliquary prize/curio shop, Mourning Parlour seating/rest |

## Retention and recontextualization

- Retain Haunted Manor’s functional scares as the premium story experience, but create a real entry courtyard and distinct graveyard exit.
- Retain Ghost Train’s powered rail route; rebuild its station into visible queue, boarding, exit, status, and street-facing kinetic show.
- Retain The Plummet’s bubble lift/drop core; make it condemned clockworks with a dedicated queue, guarded platform, water landing, spectator edge, and wet exit.
- Retain Mirror Maze as a compact Crypt Market side attraction and Ossuary as a secret three-input reward crypt.
- Merge Vault into the market/reliquary story. Place Seance at Manor. Consolidate scattered signs into a map plus decision-point wayfinding.

## Mandatory interfaces and path rules

Every major ride declares `public_approach`, `queue_entry`, `boarding_or_entry`, `ride_exit`, and `service_boundary`. Walkthroughs/puzzles declare `approach`, `entry`, `exit`, and reward endpoint if present. Shops declare `frontage`, `customer_entry`, `counter`, `exit`, and `service_access`.

At minimum, generate anchors named `hollow.arrival_gate.outbound`, `hollow.clock_street.manor_turn`, `hollow.manor.queue_entry`, `hollow.manor.exit_to_graveyard_loop`, `hollow.ghost_train.queue_entry`, `hollow.ghost_train.boarding`, `hollow.ghost_train.exit`, `hollow.plummet.queue_entry`, `hollow.plummet.wet_exit`, `hollow.crypt_market.entry`, `hollow.ossuary.entry`, `hollow.reliquary.counter`, and `hollow.return_loop.to_gate`.

Main spine is at least 5 blocks wide. Secondary paths and exits are at least 3 blocks; queues are 2–3 blocks and fenced; service routes are a concealed minimum 2 blocks. Public routing never depends on a queue. Wayfinding is located at Gate/Arrival Court, Manor/Tower split, Ghost Train/Market split, and return loop—not at every façade.

## Mechanics, atmosphere, and acceptance

Verify Manor triggers/reset/instructions; Ghost Train’s closed powered loop, platform, headroom, and scene lighting; Plummet’s sealed lift, clear chute, gated jump, safe water landing; Ossuary’s three inputs, driven doors, reward, and machinery separation; Maze solvability and true dead ends; and all game feedback/collection logic. Add ride-status indicators, protected service corridors, a rest/service point, reward path, and emergency bypass for each major queue.

Use deepslate/stone/tuff/dark timber structure, aged cracked/mossy/vine accents, iron/chain/weathered copper, warm path lighting, controlled scare effects, and deliberate negative space: courtyard, graveyard lawn, alleys. Sculptures act only as story/navigation beats, such as an angel at the Manor turn and a cursed reliquary in the market.

Promotion requires gate-to-every-major-attraction access, all exits returning to the main loop, no queue/exit collision, arrival sightline to landmark, clear land hierarchy, safe service separation, complete night lighting, and render/scenario review for gate, Manor, Plummet, Train, Market, return loop, and night skyline.
