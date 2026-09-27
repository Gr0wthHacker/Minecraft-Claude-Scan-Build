# Frontier / Park Left Rebuild Specification

## Land promise

Frontier is a living gold-rush mining town against a worked-out mountain. Guests enter a civic frontier street, choose a headline mine adventure or family canyon ride, then return through games, dining, and a clear transit spine.

The Mine Head, Mine Coaster, and Saloon are the visible anchors. The current collection of modules must stop reading as individual machines across paving.

## Spatial program and flow

| District | Role | Required content |
|---|---|---|
| Transit Landing | Arrival/orientation | Frontier Gate, map/trailhead, covered waiting porch, visible headframe/coaster |
| Boomtown Main Street | social spine | Saloon, Assay & Prize Office, rest/service frontage, 5-wide street, benches/lamps |
| Mining Square | choice point | Mine Head, coaster and Mine Cart Escape queue split, show board |
| Mine Ridge | headline adventure | coaster ridge, trestles/tunnels, station, queue/exit, viewing point, backstage edge |
| Canyon / River Camp | family loop | Rapids forecourt, splash/viewing deck, stairs/start, dry exit |
| Prospecting Row | dwell activity | Gold Sluice, Shooting Range, Nugget Chute, shared shaded porch and prize office |

```text
Frontier Gate → Transit Landing → 5-wide Main Street → Mining Square
   ├─ Mine Coaster / Mine Cart Escape → rear return path
   ├─ Rapids canyon loop → splash-view return → Prospecting Row
   └─ Saloon / games / services → return spine → Gate
```

No public door, sign, arch, or queue may lead to a void, a ride wall, or unpaved ground. Backstage controls/storage form a concealed service strip and have no public dead end.

## Keep, rework, and retire

| Existing component | Decision and rebuild role |
|---|---|
| Mine Coaster | Headline; distinct rail versus supports, ridge/tunnel story, real station, queue, exit, view, service access |
| Mine Head | Promote to literal mine-district entrance and vertical landmark |
| Runaway Mine | Rework as family-scale **Mine Cart Escape**, mechanically and visually distinct from coaster |
| Frontier Rapids | Keep as contained downhill canyon ride with stairs/start, splash pool, viewing, dry exit; never imply uphill water travel |
| Gold Sluice | Hands-on prospecting: water → hopper → comparator/bell reward, sheltered observation/queue |
| Shooting Range + Nugget Chute | One covered Prospecting & Games porch with rules, input, result, reset, prize direction |
| Pay Window + Assay Office | Merge into **Assay & Prize Office** between games and Main Street |
| Saloon | Expand into dining/social anchor with entrance, bar/tables, kitchen/service door, ambience interaction, rear loop exit |
| Powder House | Safe timed show: guest forecourt, operator kiosk, piston/light/bell blast; never TNT or public machinery |
| Detached false-front filler | Remove or absorb only where it supplies a real porch, service, shop, restroom, or interior purpose |

## Anchors and mechanics

All public modules declare `public_entry`, `public_exit`, `frontage`, and `service_access`. Rides also declare `queue_entry`, `queue_merge`, `boarding`, `ride_exit`, `emergency_exit`, `maintenance_access`, and `viewpoint`. Paths declare `arrival_spine`, `town_square`, `mine_loop`, `canyon_loop`, and `return_spine` endpoints.

Mine Coaster needs a powered station, detector-rail departure/arrival state, dispatch interlock, visible train/cart, safe loop/return. Mine Cart Escape needs a different input-to-cart/light/sound story. Rapids must be watertight and only flow down its intended run. Sluice/games must expose input, outcome, collection/reward, and reset. The Powder House is non-destructive. Saloon supplies usable interior circulation and controllable ambience.

## Detail grammar and acceptance

Use layered stone base, weathered timber trestles, contrasting rail, dark tunnel portals, sparse pines/rubble/ore, warm town lights and cool mine accents. Large paving is reserved to Mining Square and Rapids forecourt; the rest resolves into street, porches, terrain, buildings, fences, planting, props, or routes.

Promotion requires a first-time guest to identify the coaster at arrival, reach every experience on continuous paving, understand every queue and exit, find food/games/transit, and return safely. The overview must read as town below a mine ridge. Test routes, queue/exit separation, station and fluid mechanics, night lighting, collisions, and day/night approach renders.
