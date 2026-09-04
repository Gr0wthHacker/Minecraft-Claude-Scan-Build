# Final Architected Park Plan

## Authority and fixed decisions

This is the build inventory. Do not add offerings, food venues, shops, extra
rides, casino games, fireworks, or decorative stops outside this document.

The park occupies a 600 by 200 planning envelope. U is the 600-block long axis;
V is the 200-block depth measured from the public/connector edge toward the
protected outer rim. Exact world coordinates are assigned by WorldSpec, but the
allocation and adjacency are fixed here.

| U range | Width | Land |
|---|---:|---|
| 0-169 | 170 | Frontier |
| 170-214 | 45 | Frontier Reach / Claim Line |
| 215-384 | 170 | Midway |
| 385-429 | 45 | Prism Reach / Wyrm's Crossing |
| 430-599 | 170 | Prismworks |

Every land uses its 200 depth with the same operating structure: V 0-23 is
threshold/orientation; V 24-127 is playable public floor; V 128-151 is exit,
reward, and route-integrated observation; V 152-169 is concealed service; V
170-199 is protected rim, terrain, structural support, and void-view reserve.
This fully programs the envelope without covering it in buildings.

## Payment primitive

The approved grass-payment chest is a server-validated payment mechanism. It
is the only payment primitive used by this park.

Each paid attempt has: a sign stating grass price and exact attempt; payment
chest; a visible paid/ready indication; one attempt gate or operator release;
a clear failure/refund instruction supplied by the server mechanism; a free
observer/demo path; and a service access point. Comparator or observer outputs
may drive a local acknowledgement lamp or reset display, but grass validation
comes from the server payment chest itself.

No payment chest controls a main path, exit, map, connector, or essential puzzle.
It is limited to optional repeatable challenge attempts.

## Island map

Frontier Gate ← Claim Line ← Midway ← Wyrm's Crossing ← Prismworks Gate

Midway is the only distribution land. Frontier is the ride/skill land.
Prismworks is the vertical skill/cooperation land. The two reaches are fast,
safe transitions with one identity beat each, not mini-parks.

## Midway: arrival, family rides, and dispatch

| ID | Build | Exact role |
|---|---|---|
| M1 | Admission sequence | Arrival Court, map/rules, ticketing, turnstiles, re-entry and staff side route. |
| M2 | Welcome Court | low open meet marker, four decision signs, limited seats, no stalls in the centre. |
| M3 | Carousel Court | retained Carousel with queue, board, operator rear, exit to Midway return. |
| M4 | Sky Lift | retained Big Wheel structure used honestly as bubble lift/gallery/descent experience; queue, launch, safe landing, exit. |
| M5 | Skill Arcade | exactly three bays: High Striker, a deterministic Plinko/target board, and one ring/aim game. Each is one action, one result, one reset. |
| M6 | Prize Point | compact collection/display counter directly downstream of arcade; no retail street. |
| M7 | Midway Snack Window | one optional small counter with 4-6 seats only. No food hall, terrace, or second food venue. |
| M8 | Frontier and Prism thresholds | 5-wide paved handoffs, real map/fingerpost, palette transition, and public return continuity. |
| M9 | Sky Lift Sloth | one supported visual set piece hanging from a real Sky Lift outer cable/arch, framing the vertical ride from Midway. It has no fake interaction claim. |

Midway paid candidates are only explicitly repeatable arcade attempts if the
server payment chest is desired. Carousel, Sky Lift, routes, maps, and exits
remain free.

Vertical use: public floor B-8 through B+28; Sky Lift gallery and supported
Sloth B+28 through B+65; one Wheel/Sky Lift crown B+65 through B+100; service
only to B-24. Midway has no deep attraction.

## Frontier: working mine expedition

| ID | Build | Exact role |
|---|---|---|
| F1 | Trailhead Gate | arrival map, visible Mine Ridge sightline, route to Main Street and Coaster. |
| F2 | Compact Boomtown Spine | 5-wide street with only real doors: Assay/Prize, compact Saloon Counter, coaster station frontage, and service access. |
| F3 | Mining Square | open queue decision point, coaster status, low ore-cart/claim marker, clear exit routes. |
| F4 | Mine Coaster | retained headline: real queue, board, powered dispatch, lift/ridge/tunnels, unload, exit, service and emergency route. |
| F5 | Prospecting Porch | exactly two games: Shooting Range and Gold Sluice. They are aim and process verbs, distinct from Midway arcade. |
| F6 | Assay and Prize Office | score/reward collection and optional grass-paid replay chest. |
| F7 | Saloon Counter | small social pause with 6-10 seats and one ambience interaction; no kitchen or restaurant footprint. |
| F8 | Mine Ridge and Surveyor Pull-out | coaster support, tunnels, terrain, one route-integrated view point; not another attraction. |
| F9 | Works Yard | hidden reset, rail, storage, and controls, with one deliberate guest-visible working glimpse. |
| F10 | Signal Heron | one supported Heron set piece perched on a real Claim Line signal/trestle at Frontier arrival. It marks direction and frames Mine Ridge. |

Frontier paid candidate is a clearly priced Mine Coaster replay or one
Prospecting attempt, never the main route and never a random prize.

Vertical use: public town B-8 through B+24; Coaster station/ridge B+24 through
B+72; Mine Ridge peak B+72 through B+100; hidden dispatch/service B-32 through
B-8. Do not build a deep mine until this surface program proves sufficient.

## Frontier Reach: Claim Line

The 45 by 200 reach is one safe, 5-wide causeway between Frontier and Midway.
It contains structural rim, lighting, palette transition, transit separation,
and the Signal Heron at its Frontier end. There is no pool, garden, animal
collection, paid chest, or mandatory micro-game. A small off-spine protected
void look is allowed only where it also improves rim safety and does not become
a destination.

## Prismworks: vertical skill and cooperation

| ID | Build | Exact role |
|---|---|---|
| P1 | Foundry Gate and Calibration Court | entry map, visible Prism Spire, challenge rules/demo, water/rest point, free public bypass. |
| P2 | Prism Spire | island-wide vertical landmark and real structural core for launch, parkour, signals, service and catches. |
| P3 | Prism Array | Mirror Maze rework: free colour/signal route-choice challenge with real wrong branches, safe return, completion state and rear reset. |
| P4 | Prism Ascent | headline parkour: free practice loop; bubble elevator to high launch; descending ledges, gates, transfers, plunges, checkpoints and safe catches; Forge Deck exit. |
| P5 | Resonance Vault | compact 2-4 player cooperative puzzle: three separated inputs, visible shared states, one clear completion, solo-safe fallback or posted player requirement. |
| P6 | Forge Deck and Archive | route-integrated observer rail, completion display, challenge selection, 6-10 seats/lean rails, no food or shop. |
| P7 | Service Gallery | all bubble sources, catches, redstone, paid entry chests, reset controls and storage behind public interfaces. |
| P8 | Prism rockwork | sparse boundary/support treatment only; no decorative maze or passive plaza. |

Prism Ascent has a free practice route. Its timed premium attempt uses a signed,
server-validated grass chest at the start. Successful payment enables exactly
one timed entry; local panel shows ready/running/complete/reset. The ordinary
free route, observer path, exits, and all public circulation bypass that gate.

Resonance Vault may use the same payment chest only after its free rules/demo
is visible and its three-input reset loop works in game. Prism Array stays free.

Vertical use: service/catches/Vault core B-48 through B-8; concourse, Array,
Vault entry/exit B-8 through B+28; bubble launch and descending parkour B+28
through B+95; one restrained Spire crown B+95 through B+133. B-160 through
B-48 remains empty reserve unless a later proven challenge needs a safe,
meaningful climax and distinct return.

## Prism Reach: Wyrm's Crossing

This 45 by 200 reach is the Midway-to-Prismworks transition. Main transit is a
continuous 5-wide path. The only feature is Wyrm's Crossing:

- A stone/bone rib and head are physically tied to rim and Foundry Gate.
- Three rune inputs in a side alcove form an optional free riddle.
- Correct sequence changes an obvious panel and opens a 2-wide optional rejoin.
- Normal travel bypasses it completely.
- The riddle may gain a server-validated grass chest only as an optional
  challenge mode, never to use the path or shortcut.
- Service/reset lives behind the rim; failure resets safely.

The Wyrm is a functional threshold set piece. It replaces the old detached
Python/snake and all other connector sculptures.

## Vertical and visual hierarchy

Only these silhouettes reach the high/crown bands: Sky Lift, Mine Ridge/Coaster,
and Prism Spire. The Heron, Sloth, and Wyrm are secondary visual anchors tied
to real infrastructure. The lower world is deliberately sparse: service,
catches, and one compact Vault core only. This keeps the entire 600 by 200
territory legible from above and from street level.

## Build order

The Park Line renewal is specified in `PARK_RAILWAY_RENEWAL.md` and
`park_railway_v2.world.json`. Its five main-WorldSpec entries now crop one
continuous V172–186 railway, retaining both Isthmus reaches and the existing
station avenues. Three renewed stations remain secondary landmarks below B+35.
The detailed candidate is locally reviewable; live minecart proof gates remain.

1. Freeze the 600 by 200 WorldSpec, all land/reach edges, public paths, service
   spines, plot ownership, and vertical reservations.
2. Generate and approve greyboxes for all listed components before detail.
3. Build Midway admission and both thresholds, then Carousel and Sky Lift.
4. Build Frontier route, station, Mine Ridge, Coaster, and two Prospecting games.
5. Rebuild both reaches as Claim Line and Wyrm's Crossing.
6. Build Prismworks surface, Prism Array, bubble elevator, practice parkour,
   catches, and observer routes.
7. Add timed paid entry, Resonance Vault, Wyrm state machine, and replay chests
   only after their free physical versions pass local and in-game proof.
8. Add limited set pieces, lighting, signage, and final visual review.

## Promotion conditions

Every item above must pass access, queue/exit separation, service access,
mechanics, safety, night, support, cost, and visual review. Paid attempts also
must pass real server chest verification for correct grass payment, rejected
payment, completed attempt, reset, and staff recovery.
