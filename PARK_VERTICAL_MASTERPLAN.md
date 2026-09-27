# Vertical Park Masterplan — Skyblock Theme Park

## 1. Vision

The park is a suspended Skyblock destination with three public lands and a shared hidden core. It is not a flat fairground with extra tunnels. Its visible skyline, guest streets, ride systems, service infrastructure, and underground adventures are one coherent story:

> A celebrated old amusement park built onto a floating island, whose mining works, clockwork foundations, caves, and forgotten vaults extend beneath the bright public fairgrounds.

Scope: Midway/Centre, Frontier/Left, and The Hollow/Right. The existing Isthmus is retained and not rebuilt under this plan.

## 2. Non-negotiable experience contract

Every public module must have a purpose, approach, readable entrance, usable interaction or view role, clear exit, and public return route. Every operational module also has protected service access.

```text
arrival → admission → orientation → visible choice → queue/experience
→ distinct exit → recovery/reward/discovery → signed return route → next land or departure
```

No route may depend on a queue, cross a ride exit, end against a decorative façade, or expose essential mechanics as guest circulation.

## 3. Vertical zoning

Use the declared island build plane as `B`; actual elevations are assigned per WorldSpec and must remain within the server range `-64..335`.

| Band | Relative elevation | Function | Visual character |
|---|---:|---|---|
| Skyline | `B+80..335` | landmark peaks, sky lift, fireworks, balloons, observation | sparse, iconic silhouettes against open sky |
| Upper attraction | `B+28..B+80` | coaster ridge, clockworks, high decks, lift towers | kinetic and visible from across the island |
| Public park | `B-8..B+28` | paths, entries, queues, food, games, primary façades | legible, accessible, richly detailed but open |
| Hidden core | `B-48..B-8` | stations, machine galleries, mine approaches, show transitions | controlled reveal, service separation |
| Deep adventure | `B-160..B-48` | caverns, catacombs, train scenes, puzzles, reward rooms | immersive, story-led, optional discovery |
| Void-edge reserve | `-64..B-160` | exceptional finale scenes only | rare, dramatic, never generic filler |

The value of vertical space is contrast: maintain large open voids and sightlines between the major bands. Do not fill every altitude with detached towers or caves.

## 4. Island-wide circulation

### Public hierarchy

- Main promenades: minimum 5 blocks wide, lit, mapped, unobstructed.
- Secondary loops: minimum 3 blocks wide, connect supporting attractions and recovery nodes.
- Queues: 2–3 blocks wide, fenced/marked, never public through-routes.
- Exits: 3 blocks wide minimum, join a return loop beyond the queue entrance.
- Service routes: concealed 2 blocks minimum, connect controls, storage, fluids, rail, and staff-only doors.
- Vertical public changes: one block per horizontal course; steeper changes are signed stairs/elevators/lifts.

### Required cross-land flow

```text
Arrival Court → ticketing → Midway Hub
                         ├→ Frontier Arch → Frontier arrival/transit landing
                         └→ Hollow Arch → Hollow arrival court/Clock Street
```

Each land has one obvious arrival, one clear flagship choice, one recovery/reward node, one deep optional loop, and a signed return to its arrival/transit spine.

## 5. Midway / Centre — Arrival and Sky Fairground

### Purpose

The Midway turns a new player into an oriented visitor. It holds admission, classic rides, games, food, night spectacle, and visible departures to the other lands.

### Surface program

1. **Arrival Court:** safe spawn/arrival clearing, rules, park map, guest service, lockers/utility façade.
2. **Admission sequence:** Box Office → covered Entry Queue → Turnstiles → welcome threshold. Public entry, re-entry/exit, and staff movement are separate.
3. **Midway Clock/Fountain:** low central meet-point, benches, map, event lighting, and four clear path branches. The previous unexplained monument is retired or repurposed into this function.
4. **Carousel Court:** family ride, marquee, queue, board, exit to games/hub, operator rear door, seating ring.
5. **Big Wheel Promenade:** major skyline approach, Sky Lift queue, lift/gallery/chute experience, dry landing, photo/viewpoint, wide exit to food.
6. **Games Row:** Plinko, High Striker, and arcade bays under one shared frontage/awning, then Prize Counter.
7. **Food Court + Terrace:** order frontage, seating set back from routes, event/fireworks viewing edge, return to hub.
8. **Land departures:** Frontier and Hollow arches have destination identity, map cue, 5-wide paved handoff, and palette transition. The Isthmus beyond remains unchanged.

### Vertical program

- **Upper:** Big Wheel visual crown, a limited elevated viewing promenade, fireworks launch/service point, occasional balloon/flag accents.
- **Hidden core:** controlled Midway machine gallery beneath food/games or terrace; accessible only as a guided visual feature or service route, not a confusing shortcut.
- **No deep generic dungeon:** Midway remains bright and public. Its underground content is operational wonder, not a competing horror/mining land.

### Midway required interfaces

Arrival Court: `arrival_spawn`, `to_ticketing`, `map_view`.

Ticketing: `public_entry`, `queue_start`, `queue_end`, `ticket_input`, `public_exit`, `staff_exit`.

Hub: `arrival_in`, `carousel_branch`, `wheel_branch`, `games_branch`, `frontier_departure`, `hollow_departure`.

Rides: `queue_entry`, `boarding`, `ride_exit`, `service_access`; Sky Lift also `lift_entry`, `gallery`, `chute_exit`.

## 6. Frontier / Left — Boomtown and Mine Depths

### Purpose

Frontier is a gold-rush town built beneath an active mine ridge. Surface streets support food, games, and orientation; the mine creates the park’s strongest descent-and-emergence adventure.

### Surface program

1. **Frontier Landing:** gate, map/trailhead, covered waiting porch, immediate view to Mine Head and coaster ridge.
2. **Boomtown Main Street:** 5-wide social spine with Saloon, Assay & Prize Office, service/rest façade, benches, warm lamp rhythm.
3. **Mining Square:** Mine Head landmark, queue split for Mine Coaster and Mine Cart Escape, status/show board.
4. **Mine Ridge:** visibly contrasting rail and supports, stone/timber massing, lift, tunnel portals, station, queue, exit, viewing point, backstage boundary.
5. **Canyon/River Camp:** Rapids forecourt, visible splash zone, stairs/start box, spectator deck, dry return route.
6. **Prospecting Row:** Gold Sluice, Shooting Range, Nugget Chute under one covered porch, then Assay/Prize redemption.

### Underground mine journey

```text
Mine Head queue → station → visible ridge lift → tunnel portal
→ worked ore chamber → broken trestle / cavern reveal → flooded lower works
→ powered return or mine-elevator exit → Prospecting Row / Saloon return loop
```

Deep areas are layered: worked stone and timber near surface; darker soot-stained tunnels lower down; flooded/collapsed chambers below; one exceptional crystal/ore or void-edge reveal at the deepest point.

### Functional requirements

- Mine Coaster: powered dispatch, detector/arrival state, observable train, station/exit separation, service route.
- Mine Cart Escape: distinct family mechanic and story; never a second generic coaster.
- Rapids: sealed water, explicitly downhill travel, dry exit, no fake uphill flow.
- Gold Sluice: player input → water/hopper collection → comparator/bell outcome → prize path.
- Powder House: non-destructive operator show only, with hard guest separation.

## 7. The Hollow / Right — Manor, Clockworks, and Undercrypt

### Purpose

The Hollow is a haunted manor district whose public streets lead to a much older world below: crypts, forgotten rail tunnels, and a final founder’s vault.

### Surface program

1. **Hollow Gate and Arrival Court:** map, services, queue-free decision space; gate frames Clock Tower.
2. **Clock Street:** 5-wide main spine, Manor turn on one side and Tower Quarter on the other.
3. **Manor Quarter:** Haunted Manor entry court and queue, graveyard scenery, separate lower exit loop, Seance as narrative pre/post-show parlor.
4. **Tower Quarter:** Clock Tower landmark/view role plus Plummet queue, spectator edge, wet exit, service boundary.
5. **Ghost Train Station:** visible track, queue, genuine boarding platform, status board, distinct exit toward Crypt Market.
6. **Crypt Market:** Mirror Maze, Ossuary, merged Vault game, Reliquary prize/curio shop, and Mourning Parlour food/rest node.

### Undercrypt journey

```text
Manor basement / Ghost Train tunnel → catacomb transition
→ Ossuary puzzle branch → haunted train show chambers
→ drowned crypt / founder story reveal → reward vault
→ Crypt Market or graveyard return loop
```

The deep route is optional and meaningful. It offers a puzzle, a reveal, a reward, and a different return location. It must not simply be a long dark corridor below surface attractions.

### Functional requirements

- Manor scares: reachable inputs, legible instructions, resettable state, protected mechanisms.
- Ghost Train: powered loop, station queue/board/exit, headroom, visible frontage run, scene lighting.
- Plummet: sealed lift, guarded jump platform, clear chute, safe water landing, wet exit.
- Ossuary: three-input puzzle, driven doors, reward beyond, machinery inaccessible to guests.
- Mirror Maze: solvable route, true dead ends, clear exit.

## 8. Skyline, silhouette, and night plan

Only five island-wide silhouettes may dominate the skyline:

1. Big Wheel/Sky Lift.
2. Mine Head and coaster ridge.
3. Clock Tower.
4. Plummet/condemned clockworks.
5. One restrained island-wide spectacle: fireworks, balloon cluster, or suspended observation emblem.

At night, public paths use warm reliable lighting; ride entries/exits use high-legibility lighting; mines use cooler industrial highlights; Hollow uses sparse warm pools and controlled scare effects. Never use darkness as the only haunted aesthetic.

## 9. Visual grammar

| Land | Structure | Palette | Detail rule |
|---|---|---|---|
| Midway | painted pavilions, canopies, bright ride structure | painted colors, light trim, metal, warm lamps | open sightlines; concentrated marquee/light nodes |
| Frontier | false fronts, porches, trestles, mine ridge | weathered timber, dusty stone, dark metal, ore accents | detail clusters on porches, ridge, props; avoid flat grey paving |
| Hollow | gothic massing, crypts, ironwork, broken rhythm | deepslate/stone, dark timber, oxidised metal, warm lanterns | negative space, graveyard lawns, controlled redstone effects |

Every major view needs foreground detail, middle-distance activity, and a landmark/background. Decorative structures must support a room, view, boundary, or story; otherwise remove them.

## 10. Build phases

1. Freeze strict WorldSpec: site bounds, vertical bands, protected areas, plots, 3D paths, view corridors, anchors, budgets.
2. Render and validate platforms, main routes, bridges, supports, safety rails, and public entry points.
3. Build Midway admission/hub and the three/five island-wide silhouettes.
4. Build Frontier surface and Mine Ridge, then mine-depth loop.
5. Build Hollow surface and major stations, then Undercrypt loop.
6. Add food, prizes, services, interiors, mechanics, and protected backstage access.
7. Add landscaping, water, props, signage, lighting, and night pass.
8. Assemble chunks; run collision, block legality, support, route, mechanics, and cost gates.
9. Generate and approve required visual packets: arrival, façade, skyline, interior, night, queue, exit, and deep-reveal views.
10. Validate against real Skyblock capture after placement and create only scoped correction tickets.

## 11. Promotion gate

The park promotes only when all of the following are true:

- Skyblock 1.19 profile and allowed-block gate pass.
- Every module has purpose, footprint, typed anchors, access, service path, budget, scenarios, and review views.
- All public entries and exits are reachable from Arrival Court across assembled blocks.
- Queue, board, exit, service, and main-route cells do not conflict.
- Every ride’s declared mechanics, fluids, rails, inputs, outputs, and reset paths pass.
- No artifact overlaps another lane, protected area, view corridor, or existing required infrastructure.
- Required day/night render packet passes human review.
- A real world capture confirms placed blocks, usable routes, lighting, and mechanisms.
