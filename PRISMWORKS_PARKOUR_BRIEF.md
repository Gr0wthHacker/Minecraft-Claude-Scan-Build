# Prism Ascent: High-Intensity Parkour Brief

## Role

Prism Ascent is the visible kinetic centerpiece of Prismworks. It starts from a
safe enclosed bubble-elevator launch and replaces the proposed Skyfall traversal
with a skill-based vertical descent. Players
see other players moving across the Spire, learn the route from public
observation paths, practice for free, then choose whether a timed premium run
is worth grass. It does not use or require PvP.

The course must read as a machine under tension: a visible water ascent, lit launch pads, narrow
stepping points, gates, moving-looking prism frames, safe plunge catches, and
a rising crown. It is a playable landmark, not a tower decorated with random
blocks.

## Player loops

| Loop | Entry | Challenge | Outcome | Exit |
|---|---|---|---|---|
| Practice | free, from Calibration Court | short 6-10 move sample at ground/low Spire | teaches two core moves, shows personal completion light | return to Concourse |
| Standard Ascent | free or server-configured | full fixed course with checkpoints | clear completion panel/time, Archive milestone | Forge Deck return |
| Timed Ascent | optional paid run only | same understandable movement rules with timer and fixed checkpoints | published time/result plus configured non-random acknowledgement | Forge Deck return |
| Observer | public, free | watches active runners from separated balconies | learns route and sees results | Concourse return |

Payment never unlocks geometry that a player cannot inspect. A timed attempt
starts only after successful payment confirmation. It must fail closed: payment
failure leaves the gate open to the public bypass and consumes nothing.

## Course grammar

Use the proven move vocabulary from the existing Island Run generator, adapted
to a bounded Spire rather than its full-island descent:

| Move | Purpose | Guardrail |
|---|---|---|
| Ledge | 1x1 sprint-jump landing | 3.0-4.5 block gap; actual landing is one block, not a ramp |
| Gate | sprint jump with overhead/side frame | clear player headroom and a visible approach |
| Plunge | 8-16 block controlled fall to slime catch | catch always cancels fall damage; visible from launch |
| Transfer | short lateral leap between Spire faces | landing, destination, and safe catch are legible |
| Rest | 3x3 checkpoint platform | light, checkpoint state, observer separation, restart path |
| Finale | final jump or controlled drop through crown | clear result trigger and immediate safe exit |

The sequence gets harder by combining moves, not by hiding landings, making
blind jumps, using damage, or forcing a long run-back after failure. A first
run should take roughly 2-4 minutes; practice should take under 45 seconds.

## Vertical and spatial layout

| Spire level | Content | Public safety |
|---|---|---|
| B through B+12 | Calibration Court, practice loop, timer/payment desk, main bypass | broad 5-wide concourse, no queue spill |
| B+12 through B+35 | Act I: legible ledges and gates | lower observer path; safe net/catch below every fall line |
| B+35 through B+60 | Act II: transfers, visible frame crossings, first major plunge | checkpoint at both act boundaries; service gallery behind frame |
| B+60 through B+80 | Act III: high-contrast crown route and finale | protected observer balcony below crown; no route overlaps |
| B-8 through B | catch/restart/service | recovery lift/stairs, reset wiring, staff-only controls |

The route is one-way. It never crosses the queue, observer balcony, service
strip, or main concourse. Falling sends a player to the nearest safe catch and
restart/checkpoint path, not into void, a public route, or a redstone bay.

## Visual direction

- The main silhouette is a spiralling line of lit landings around a restrained
  Prism Spire, readable from Midway and the Prism Reach.
- Use base, recess, and projection layers: stone/metal machine core; dark
  recess frames; colour-coded prism rails/pads; limited bright emitters on
  landings, never in the landing cell if they obstruct movement.
- Each act has a different visual rhythm: broad calibration geometry, angular
  side transfers, then a high bright crown. Do not scatter unrelated crystals
  or towers around it.
- Observation is visual drama: guests see the next runner's line without being
  able to collide with or grief it.

## Mechanical and anti-frustration contract

1. Checkpoint and timer logic are isolated from public path wiring.
2. Each landing has required headroom and is physically makeable from its prior
   move. Validate horizontal gap, vertical drop, safe-catch coverage, and
   route reachability at block level.
3. Any pressure plate, target, or tripwire trigger has protected wiring and a
   service-access reset path.
4. Use no player-versus-player premise, forced combat, damage challenge, or
   inventory-risk mechanic.
5. Practice and observer paths remain usable while a paid timed run is active.
6. A stalled run times out to a safe recovery point; it cannot reserve the
   course forever.
7. Entity use is optional and budgeted; signs/lights/redstone are sufficient
   for score state unless a server-approved leaderboard exists.

## Acceptance scenarios

- A first-time player finds practice without reading a dense sign.
- A player completes each movement type safely and can recover after a miss.
- A spectator watches active movement and exits without entering a queue.
- A timed-run payment succeeds, fails, and times out without trapping or
  consuming currency incorrectly.
- Checkpoint/restart, every trigger, every catch, and every service control
  work while normal public circulation remains open.
- Day, night, Midway approach, Prism Reach approach, mid-course, crown, catch,
  and observer renders confirm both spectacle and legibility.
