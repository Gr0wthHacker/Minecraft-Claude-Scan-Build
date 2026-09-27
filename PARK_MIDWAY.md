# Midway / Centre Rebuild Specification

## Land promise

Midway is the park's arrival-and-fairground district: it turns a new player into an oriented, ticketed visitor; offers two immediately understandable classic rides; provides games, food, and rest; then deliberately dispatches guests to Frontier and Hollow.

The Big Wheel and Carousel remain the visual and functional anchors. The Arrival Court remains the safe clear spawn node. The unexplained monument must become a useful **Park Fountain & Clock / Meet Here** landmark or move to a plaza edge; it cannot remain a purposeless obstruction.

## Guest route

```text
Arrival Court → map/rules/guest services → Box Office → Entry Queue → Turnstiles
→ welcome threshold → Midway Hub
   ├─ Carousel Court → queue → board → exit → games/prizes
   ├─ Big Wheel Promenade → queue → sky lift → chute exit → food/terrace
   ├─ Games Row → prize counter → food/rest
   ├─ Frontier Arch → existing connector
   └─ Hollow Arch → existing connector
```

No front façade, queue, arch, or ride exit may terminate on unpaved ground or force a player to reverse through the same queue.

## Spatial program

### Arrival and ticketing forecourt

Build a single west-edge sequence: Arrival Court, rules/map and guest services, Box Office, covered entry queue, turnstiles, then a post-gate welcome threshold. Preserve two-way movement: public entry lanes plus distinct exit/re-entry/staff movement. Include lockers, first-aid-style utility, and information here, rather than scattering them around the land. The first post-gate view frames the wheel and carousel.

### Midway hub

The central hub has one 5-wide arrival spine, a 5-wide cross-park spine, four named lit branches, a main fingerpost, patterned circulation paving, seating/planting outside desire lines, and the low meet-point fountain/clock/map. It is the only place where all lands are introduced, but it is not a dumping ground for free-standing game machines.

### Carousel Court

Keep the powered minecart circuit. Add a `CAROUSEL` marquee, short covered switchback queue, distinct exit to games/hub, rear operator door, benches, low boundary planting/rail, and status evidence for the powered rail. It is visible from the hub but set off the through-route.

### Big Wheel Promenade

Keep the wheel as skyline beacon, but label its actual experience accurately (for example, **Sky Lift**) because its functional loop is a bubble-lift/gallery/drop-chute attraction rather than a rotating wheel. Provide 5-wide approach, signed entry plaza, queue, lift entry, gallery, safe dry chute landing, exit route, photo/viewpoint, and night lighting. The exit cannot feed into waiting guests.

### Games Row, prize, food, and terrace

Merge Plinko, High Striker, and arcade functions into a single awning/façade-backed games frontage. Each bay has a standing spot, input, outcome, clear prize or score path, and protected redstone rear. Place the prize counter as the natural next step. The food court follows as a recovery node with ordering frontage, seating behind, circulation around tables, bins/utility detail, and return to the hub. The Terrace faces the wheel/fireworks and has a marked viewing boundary and operator role if fireworks are interactive.

### Land departure thresholds

At both arches, provide a 5-wide continuous paved handoff, destination identity, fingerpost, and map cue. Palette/planting change begins before the arch. The Isthmus itself is unchanged.

## Required anchors and links

| Module | Required anchors |
|---|---|
| Arrival Court | `arrival_spawn`, `to_ticketing`, `map_view` |
| Box Office | `public_entry`, `queue_start`, `service_access` |
| Entry Queue | `queue_start`, `queue_end`, `emergency_exit` |
| Turnstiles | `ticket_input`, `public_entry`, `public_exit`, `staff_exit` |
| Hub | `arrival_in`, `carousel_branch`, `wheel_branch`, `games_branch`, `frontier_departure`, `hollow_departure` |
| Carousel | `queue_entry`, `board`, `ride_exit`, `service_access` |
| Big Wheel | `queue_entry`, `lift_entry`, `gallery`, `chute_exit`, `service_access` |
| Games / Prize / Food | `frontage`, `play_or_queue_entry`, `collection_or_exit`, `service_access` |
| Terrace | `viewing_entry`, `viewing_exit`, `operator_access` |
| Arches | `midway_side`, `connector_side` |

Required links: Arrival Court → Box Office → Entry Queue → Turnstiles → Hub; Hub → each ride queue; each ride exit → recovery/hub; Games → Prize → Food/Hub; Hub → both arches → connector.

## Acceptance

Promotion requires spawn-to-all-destination access, separate entry/queue/board/exit/service interfaces for rides, no queue conflict with a primary route, working carousel rail and safe Sky Lift fluid/chute flow, usable ticket path plus exit/staff route, complete night lighting, and a visual packet covering arrival, post-turnstile, both ride approaches/exits, games, food, and night hub.
