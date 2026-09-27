# Theme Park Overhaul — Master Design and Delivery Brief

## Purpose and scope

This is the rebuild contract for the three park lands: **Midway / Centre**, **Frontier / Left**, and **The Hollow / Right**. It turns the existing collection of generators into a legible, functional theme park with a complete guest journey. The Isthmus and its existing connector work are deliberately out of scope.

The target is not more structures. It is a park in which every public-facing build has an understandable role, reachable entrance, usable interaction, safe exit, and a reason to sit where it sits.

The detailed zone specifications are:

- [Midway / Centre](PARK_MIDWAY.md)
- [Frontier / Left](PARK_FRONTIER.md)
- [The Hollow / Right](PARK_HOLLOW.md)

## Park-wide operating model

```text
Arrival Court → ticketing → entry gates → Midway hub
                                       ├─ Frontier departure → mining-town adventure loop → return
                                       └─ Hollow departure → haunted-district adventure loop → return
```

The Midway is the park's arrival, orientation, family-rides, games, food, and distribution heart. Frontier and Hollow are fully formed lands, each with a different headline experience, secondary loop, recovery node, and unambiguous return to the park network.

### Non-negotiable design rules

1. A public-facing module needs a named purpose. Pure scenery is allowed only when it improves a view, boundary, story, or orientation.
2. Every public destination is connected to a continuous public path. A decorative doorway, queue entrance, or façade front is not sufficient.
3. Every major ride declares separate `approach`, `queue_entry`, `boarding` or `ride_entry`, `ride_exit`, and `service_access` interfaces.
4. Queues are never used as through-routes. Ride exits never discharge into incoming queues or primary promenades.
5. Every interactive claim has an input, a visible state/output, reset behaviour, and protected maintenance access.
6. Every land has a 5-block minimum main public spine, 3-block secondary circulation, separated 2–3-block queues, distinct exits, and hidden service routes.
7. Lighting and wayfinding are part of the path graph: every decision point has a sign/map or landmark cue, and every public route is safely legible at night.
8. Ticketing happens once at park arrival unless an experience has a genuine, working ticket/checkpoint mechanic. Decorative pay windows must not impersonate access control.

## Required interface schema

The existing park parallel manifests have module placement data but no typed anchors, dependencies, or interface links. The rebuild begins by making those contracts mandatory. A plan cannot be prepared or promoted when a public module has empty anchors.

| Module type | Mandatory named anchors |
|---|---|
| Arrival / gate | `arrival`, `public_entry`, `public_exit`, `map_view` |
| Major ride | `approach`, `queue_entry`, `boarding`, `ride_exit`, `emergency_exit`, `service_access` |
| Walkthrough / puzzle | `approach`, `entry`, `exit`, `reward` where applicable, `service_access` |
| Food / retail / games | `frontage`, `customer_entry`, `queue_entry`, `collection_or_exit`, `service_access` |
| Landmark | `view_approach`, `frontage`, `interior_entry` if usable |
| Path / plaza | named endpoints and capacity role: `main_spine`, `secondary`, `queue`, `exit`, or `service` |
| Cross-land arch | `land_side`, `connector_side`, `departure_sign` |

Links are explicit, type-compatible, world-space checked, and route checked. The nearest paved coordinate does not constitute an interface.

## Park-wide guest journey

| Stage | Guest need | Required park response |
|---|---|---|
| Arrive | Understand where they are | Clear spawn court, map, landmark, sightline to entry sequence |
| Enter | Buy/validate admission without confusion | Box office → covered queue → turnstiles → welcome threshold; a distinct re-entry/staff route |
| Choose | See what is worth doing | Midway landmark, destination arches, maps and named spines |
| Experience | Find queue, use mechanism, exit safely | Separate approach/queue/board/exit, readable instructions, functional output |
| Recover | Eat, rest, regroup | Food, seating, water/utility detail, toilets/service façade, meet-point |
| Explore | Discover variety without getting lost | Land loops, visible landmark, secondary attractions grouped by story |
| Depart / return | Rejoin transit without backtracking through queues | Signed return spine and connector handoff |

## Functional and visual acceptance gates

The following are promotion gates, not optional polish:

- `interface`: every required anchor exists, is attached to the public paving graph, and has a compatible declared link.
- `route`: arrival can reach every public entry, boarding point, service counter, seating node, ride exit, and land departure; every ride exit can reach the return spine.
- `capacity`: queue cells are not part of through-routing; queue/exit/main-spine overlap is rejected.
- `mechanics`: rails, redstone, fluid containment, inputs/outputs, collection containers, and reset paths are verified per ride.
- `safety`: no blocked landing, unsealed water lift, inaccessible essential control, unsafe public machinery, or headroom collision.
- `wayfinding`: maps and signs exist at genuine decision points and point to actual walkable approach anchors.
- `night`: public paths, queue starts, exits, and decision points meet the lighting rule.
- `visual`: render packet includes arrival, approach, queue, exit, return loop, landmark sightline, and night overview for each land.

## Delivery sequence

1. Freeze revised spatial programs and typed interface graphs for all three lands.
2. Replace path layers with named capacity-aware spines, loops, queues, exits, and service corridors.
3. Rebuild Midway's admission sequence and distribution hub first; it is the dependency for the other lands' departures.
4. Rebuild Frontier's Mine Ridge, Main Street, and water-ride loop.
5. Rebuild Hollow's gate-to-clock-street sequence, major ride stations, and Crypt Market consolidation.
6. Add supporting service, food, retail, scenery, landscaping, and night passes only after movement and mechanisms pass.
7. Produce and review zone render/scenario packets; promote zones independently only when their gates pass.

## Parallel-generation rules

Each land has its own frozen plan, lane-owned module set, and output directory. The owning land may not modify another land’s modules or the Isthmus. Cross-land work is limited to declared edge anchors at the Midway and connector boundaries.

Each rebuild lane must submit: frozen config hashes, its anchor/link manifest, route and mechanic evidence, visual packet, and a scoped change list. Assembly rejects overlaps, out-of-scope writes, incompatible links, stale source configs, and incomplete evidence.
