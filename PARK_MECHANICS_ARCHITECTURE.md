# Park Mechanics Architecture

## Principle

Use mechanics only when they create a player-facing decision, movement, state
change, or result. Every mechanism has one owner, a public interface, service
access, a safe failure state, and an in-game proof run.

| Tier | Purpose | Examples | Rule |
|---|---|---|---|
| 0 | structure | paths, views, supports | no redstone |
| 1 | passive motion | bubble elevator, slime catch, water containment | simple geometry; prove player motion in game |
| 2 | single state | button to lamp/bell, checkpoint panel | local circuit proof |
| 3 | bounded state machine | puzzle, dispatch, checkpoint chain | state table, timeout, reset, service route |
| 4 | external integration | grass payment, persistent score | approved adapter and server proof |

No initial module combines more than one tier-3 system with tier-4 integration.
Build the free mechanically complete experience before payment or persistence.

## Prism Ascent: bubble launch and descending parkour

The ascent is an enclosed bubble elevator, not an uncontrolled water cannon.
A player enters at Foundry base, rises through a 2-wide water-source shaft over
soul-sand bubble columns, exits onto a dry protected launch deck, then descends
the Spire course to Forge Deck and Prism Concourse.

Sequence: Calibration Court offers free practice. A ready queue enters the
bubble shaft. A 3-wide dry launch deck supplies rail/edge protection,
instructions, and staff hatch. Parkour descends through ledge, gate, transfer,
plunge, and checkpoint acts. Every fall line ends in enclosed slime or water
catch feeding recovery/checkpoint flow. Final trigger exits away from queue.

| Bubble requirement | Constraint |
|---|---|
| Column | fully enclosed 2-wide water-source column with soul-sand base and no spill beside public route |
| Entry | clear 3-wide approach; gate outside water; water works without redstone |
| Exit | dry top landing with headroom, guard rail, and no fall back into shaft |
| Recovery | bottom escape plus top service hatch; player may leave without finishing |
| Service | source blocks and soul-sand reachable only from Service Gallery |
| Proof | local containment/support audit; actual ascent, exit timing, and collision proof in game |

The elevator is tier 1. Do not add dispensers, piston water gates, complex timers,
or paid locks to its first version. An always-working launch beats a brittle one.

### Parkour state

| State | Public signal | Transition | Safe failure |
|---|---|---|---|
| Ready | entry lamp/clear gate | player starts | public bypass stays open |
| Running | runner lamp/checkpoint panel | plate or target reaches checkpoint | nearest catch/restart |
| Checkpoint | matching lit panel | player reaches next stage | recover to last confirmed stage |
| Complete | crown/result panel | final pad/target | exit to Forge Deck |
| Reset | panel cleared by service or timeout | bounded reset | no locked player or route |

Initial Prism Ascent uses local checkpoint lights and completion display only.
Timers, payment, persistent scores, and rewards are separate optional layers.
Pressure plates prove contact; they do not prove player identity or a fair timer.

## Zone mechanics budget

| Zone | Tier 1 | Tier 2 | Tier 3 | Tier 4 boundary |
|---|---|---|---|---|
| Midway | Sky Lift bubble/chute | game lamps/bells | Carousel station | games payment only after adapter proof |
| Frontier | coaster geometry/return | target and sluice feedback | dispatch plus one prospecting loop | optional replay, never route access |
| Prismworks | bubble launch, catches, parkour | checkpoint/Array panels | Vault sequence and checkpoint chain | timed paid run/leaderboard optional |
| Frontier Reach | bridge/rim/light | one optional target result | none by default | none |
| Prism Reach | bridge/Wyrm form | rune state panel | three-input Wyrm riddle | no paid passage or shortcut |

This is a ceiling, not an obligation to fill every cell. If tier 3 is not more
fun than tier 1 movement, remove it.

## Zone contracts

### Midway

- Carousel: powered-rail station, visible board/unload, detector arrival signal,
  manual service stop, and exit separate from queue.
- Sky Lift: sealed bubble lift, dry exit, contained chute/landing, no route
  through water or waiting guests.
- Games: exactly one readable action and result per bay. Target to score lights
  and button pulse to lamp are good; hidden randomizers and shared wiring banks
  are not.

### Frontier

- Mine Coaster: powered departure, detector arrival, visible status, service
  route, full ride proof. Avoid quasi-connectivity and entity-timing logic.
- Prospecting: only two or three distinct verbs: aim, timing, and visible
  process chain. Each has clear reset.
- Assay/Prize: displays real results and later approved payment adapter only;
  a decorative hopper must not impersonate a transaction.

### Prismworks

- Prism Array: free route-choice puzzle. State panels describe valid routes;
  wrong choice returns safely to a prior branch; no deadlock.
- Prism Ascent: bubble and state contract above. It is the visual anchor.
- Resonance Vault: at most three independently testable inputs and one obvious
  result. Prefer buttons/levers, lamps, doors, note/bell output over a hidden
  redstone computer.
- Forge Deck/Archive: display only completion the installed system can honestly
  know. No fake leaderboard or payment counter.

### Isthmus

- Causeway stays tier 0/1: route, safe rim, lighting, and skyway separation.
- Claim Line micro-game exists only if distinct from Prospecting; otherwise no
  game there.
- Wyrm Crossing is one bounded riddle: three input runes, state panel, optional
  rejoin gate, staff reset. Main connector never depends on it.

## Build and evidence order

1. Greybox queues, water shaft, launch deck, course, catches, exits, observers,
   service paths, and all bypasses.
2. Build tier-1 physics first. In-game test bubble ascent, launch exit, every
   catch, rail ride, and fluid destination before redstone.
3. Add tier-2 outputs and run a stated circuit input/output test.
4. Add one tier-3 system at a time with state table, timeout, reset, and service.
5. Only then integrate tier-4 payment/persistence. Test success, failure,
   cancellation, duplicate input, reset, and manual recovery.
6. Run assembled route, safety, night, cost, entity/tile, and visual gates.

| Claim | Local proof | Required in-game proof |
|---|---|---|
| Redstone | circuit input/output test | player uses intended input |
| Rail | circuit/rail topology | full ride, boarding, exit, stuck-cart recovery |
| Water/bubble | containment/support audit | ascent, top exit, fall/catch recovery |
| Parkour | makeability, headroom, catch and route audit | skilled and new-player representative run |
| Puzzle | state table/circuit tests | success, wrong input, reset |
| Payment/score | adapter contract only | approved transaction, refund/rejection, duplicate/outage recovery |

No render, audit, or schematic proves moving-player physics or a server
transaction. Those claims remain blocked until named in-game proof is recorded.
