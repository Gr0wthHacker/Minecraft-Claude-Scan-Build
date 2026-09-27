# Full Park Build Specification

This is the detailed construction companion to PARK_FINAL_ARCHITECTED_PLAN.md and park_final.world.json. It turns the program into build cards that a generator, builder, or review agent can use without inventing missing access, purpose, or vertical logic.

## Coordinate convention and registration

Use the local plan coordinate system until the live capture rebases it:

- U = long-axis position, 0 through 599. In the WorldSpec it is local z.
- V = depth from the public/connector edge, 0 through 199. In the WorldSpec it is local x.
- B = final registered public build plane; the provisional WorldSpec uses B=203.
- Public paths are at B. Guests occupy B+1.
- Service runs at B-1 through B-8 unless a module explicitly reserves a deeper band.

The current anchor in park_final.world.json is provisional. It is only a planning registration, never paste authority. Rebase the local U/V lattice against the current island capture before production.

## Whole-park spatial rules

| Requirement | Construction rule |
| --- | --- |
| Main transit | 5-wide minimum on reaches; 7-wide minimum at Welcome Court, Mining Square, Foundry Gate, queue mouths, exits, and observer merges. |
| Queue | 3-wide queue lane, 1-block separation from exit where possible, visible entry sign, no main-path spill. |
| Exit | separate from queue, joins a public return route within 12 blocks of the final ride/puzzle result. |
| Service | starts from V 152 or a concealed rear edge; no guest must cross it to use an attraction. |
| Protected rim | V 170-199 is support, terrain, void safety, sightline protection, and only attached setpiece structure. |
| Landmark rule | only Sky Lift, Mine Ridge/Coaster, and Prism Spire enter crown bands. |
| Social rule | Welcome Court, Mining Square, and Forge Deck remain open-facing; do not fill their floors with stalls or scenery. |
| Setpiece rule | Sloth, Heron, and Wyrm attach to real load-bearing infrastructure and have a named view/job. |
| Payment rule | a payment chest controls one optional repeatable attempt only. It never controls a route, exit, map, free practice, or essential puzzle. |

## Shared circulation

### Primary spine

The public spine runs at V 12, U 2-597. It is the guaranteed all-player route, has no gates, and visibly changes palette at U 170, 215, 385, and 430.

- Frontier: weathered timber edge, stone/dirt core, mine signal lights.
- Midway: clean bright paving, direction colour band, open sightline to Carousel/Sky Lift.
- Prism: stone and dark frame edge, cyan/blue orientation marks used sparingly.
- No side feature narrows this spine below five blocks.

### Public loops

Each land has a 5-7-wide internal loop that attaches to the spine at two points. This is essential: a party can split for a queue, puzzle, or game and reconvene without backtracking through a single door.

| Land | Public loop levels | Required visible decision |
| --- | --- | --- |
| Frontier | U 20, 62, 105, 142 | Mine Coaster versus Prospecting; exit/reward return |
| Midway | U 240, 305, 357 | Carousel versus Sky Lift versus Skill Arcade |
| Prismworks | U 450, 515, 570 | Array versus Ascent versus Vault; practice versus observer/return |

The rear service spine at V 175 is not guest circulation. It supplies Mine Coaster dispatch, game resets, Spire catches/checkpoints, Vault/Wyrm circuits, and payment-chest recovery.

## Lot schedule

All footprints are local V/U rectangles inclusive. The physical module may leave deliberate internal open space; the footprint is ownership, not a demand to fill every cell.

| ID | Module | V/U footprint | Elevation reservation | Generator/build owner | Build state |
| --- | --- | --- | --- | --- | --- |
| F1 | Trailhead Gate | V18-50 / U5-35 | B-2 to B+18 | frontier town/gate shell | build now |
| F10 | Signal Heron | V55-80 / U5-35 | B+12 to B+54 | heron + signal trestle | build now after visual review |
| F2 | Boomtown Spine | V18-70 / U40-85 | B-4 to B+24 | frontier façades/interiors | build now |
| F3 | Mining Square | V75-130 / U40-85 | B-2 to B+18 | plaza/path module | build now |
| F5 | Prospecting Porch | V145-195 / U40-85 | B-8 to B+24 | arcade + sluice modules | shell/circuits separately |
| F4 | Mine Coaster | V30-140 / U90-160 | B-16 to B+100 | coaster + station/works | rail proof gated |
| F6 | Assay/Prize | V145-195 / U90-120 | B-4 to B+22 | office/reward shell | build free version |
| F9 | Works Yard | V145-195 / U125-160 | B-24 to B+18 | service/dispatch | staff-only |
| M1 | Arrival Court | V18-65 / U220-260 | B-2 to B+22 | arrival/ticketing | build now |
| M2 | Welcome Court | V70-120 / U220-260 | B to B+16 | open plaza/path | build now |
| M7 | Snack Window | V125-155 / U220-260 | B to B+16 | small counter | build last; max 6 seats |
| M3 | Carousel Court | V18-85 / U270-340 | B-8 to B+50 | carousel/station | cart proof gated |
| M4/M9 | Sky Lift/Sloth | V90-155 / U270-370 | B-8 to B+100 | lift shell + sloth support | free lift proof gated |
| M5 | Skill Arcade | V160-195 / U270-340 | B-8 to B+24 | three arcade bays | circuit proof gated |
| M6 | Prize Point | V160-195 / U345-370 | B to B+16 | compact counter | build free version |
| W1 | Wyrm’s Crossing | V18-80 / U390-425 | B-10 to B+30 | wyrm/riddle threshold | shell now, riddle gated |
| P1 | Foundry Gate | V18-70 / U435-470 | B-4 to B+28 | Prism entry/concourse | build now |
| P3 | Prism Array | V75-130 / U435-485 | B-8 to B+28 | prismworks array | build/playtest |
| P5 | Resonance Vault | V135-195 / U435-490 | B-32 to B+18 | prismworks vault | shell now, circuit gated |
| P4/P2 | Prism Ascent/Spire | V35-125 / U500-585 | B-48 to B+133 | prismworks ascent | practice first |
| P6 | Forge Deck | V135-195 / U495-545 | B-2 to B+35 | observer/return deck | build with Ascent |
| P7 | Service Gallery | V160-195 / U550-590 | B-32 to B+8 | service-only spine/rooms | build with Ascent/Vault |

## Detailed build cards

### F1 — Trailhead Gate

**Guest sequence:** frontier threshold → map/readable choice → Mining Square or Boomtown Spine. The gate must not be a façade with a dead doorway.

- Put a 7-wide arrival apron on the public side, map at eye level, and two readable route signs: Mine Coaster and Prospecting.
- Leave the Mine Ridge/Coaster silhouette visible above the gate. The gate roof cannot consume that corridor.
- Give staff a 2-wide concealed rear door into the service spine.
- Use one tall frontier sign, timber framing, and a low stone foundation. Do not add shops.
- Exit condition: a first-time player can choose the coaster or public street in one glance.

### F10 — Signal Heron

**Job:** a Frontier beacon and transition marker, not an attraction.

- Perch it on a real signal trestle anchored to the Claim Line/Trailhead support structure.
- Heron feet and talons touch the trestle; the bird does not stand on a decorative stump.
- Intended hero views: Midway-to-Frontier approach and Mining Square looking back toward the threshold.
- Use the high-detail Heron generator only at scale where feather courses, eye, beak, neck curve, toes, and wing layers remain legible.
- Reject if it masks Mine Ridge or competes with the coaster crown.

### F2/F3 — Boomtown Spine and Mining Square

**Guest sequence:** Gate → real doors → square decision point → coaster/prospecting/return.

- Boomtown contains only coaster frontage, Assay/Prize, compact social counter, and service access. Every false front requires a real use.
- Mining Square is 7-wide around its central decision zone, with the coaster queue entrance visibly separated from its exit.
- Use a low ore-cart/claim marker only if it points toward a real destination; never turn the square into a sculpture garden.
- Saloon Counter is a lean/social pause: 6-10 seats, one small ambience interaction, no kitchen and no second food venue.

### F4 — Mine Coaster

**Guest sequence:** visible status → queue → board → live rail ride → unload → exit through Mining Square/Assay.

- Queue: 3-wide, 14-24 player capacity, covered only where it improves the station silhouette; do not box the entire queue indoors.
- Board/unload: separate sides of station; each has an operator/service reach and a cart-removal path.
- Ridge: station at B through B+24, lift/trestle/tunnel scenes B+24 through B+72, crest B+72 through B+100.
- Every track cell needs rider headroom, return topology, powered-rail coverage, accessible stuck-cart recovery, and a visible public-safe support story.
- The generator can create rails and clearance. Live server proof must establish minecart entities, spawn/reset policy, rider boarding, unload, lag behavior, and cleanup.
- Do not enable a grass replay chest until the free ride completes repeated live runs without recovery intervention.

### F5/F6/F9 — Prospecting, Assay, Works

**Prospecting Porch:** exactly two playable bays: Shooting Range and Gold Sluice.

- Shooting Range is a real target-input game. Give it a 3-wide firing position, clear safety backboard, lamp ladder/result panel, prize/reset access from the rear, and spectator side rail.
- Gold Sluice is a visible process chain. Its input, measurement/result, collection, reset, and item-clear path must be physically distinct. No decorative hopper is a “game.”
- Assay/Prize receives players after both bays. It has one service rear, result display, and optional future replay chest, but no shop street.
- Works Yard is behind V145+, hidden from normal guest view except one controlled glimpse of track/reset work.

### M1 — Arrival Court

**Guest sequence:** arrival → rules/map → turnstile/re-entry choice → Welcome Court.

- This is the only ticketing/administrative threshold. It must be free to pass unless the server separately controls park admission.
- Include a re-entry route and staff route independent of public queue.
- Signs explain the park’s three lands and distinguish free play from optional grass challenges.
- Keep the centre visually open. No food, prize, or vendor clutter belongs here.

### M2 — Welcome Court

**Job:** social distribution, orientation, and regrouping.

- Clear 7-wide decision space faces Carousel Court, Sky Lift, Frontier threshold, and Prism threshold.
- Install a truthful “current challenge” board here only if manually curated or backed by an installed server system.
- Provide limited perimeter seating/lean rails, not a café.
- Preserve direct sky view to the Sky Lift and one framed view toward Prism Spire.

### M3 — Carousel Court

- The carousel reads as a ride from all four approaches: circular canopy, mounts, boarding rail, exit rail, operator rear.
- Queue and exit are adjacent but cannot cross. The exit returns to Welcome Court/Prize Point loop.
- A minecart carousel requires live entity policy. Until that is proven, construct the shell, queue, operator access, and observation edge but do not market it as moving.
- One small photo/meeting edge is allowed because it supports actual ride waiting; do not build a detached photo plaza.

### M4/M9 — Sky Lift and Sloth

**Guest sequence:** visible lift → entry water/bubble channel → dry gallery/launch → safe descent/landing → exit to Midway loop.

- The water entry remains below the casing’s water level; no door may drain the column across guest paving.
- Top departure has guard rail, headroom, clear instructions, and no return fall into the shaft.
- Landing has a safe water/catch zone and a visible return path; queue never passes through it.
- Sloth hangs from a real external Lift cable/arch or support truss. It receives a close underside view and is never a detached tree-hanger.
- Use the animal release contract: connected body, named anatomy, material depth, multi-angle packet, human in-context approval.

### M5/M6 — Skill Arcade and Prize Point

- Exactly three bays: High Striker, deterministic target/Plinko replacement, and one ring/aim game.
- Each bay has one stated player action, one visible result, one bounded reset, a service hatch, and a spectator edge.
- No luck wheel, chance payout, shared hidden randomizer, or unverified prize.
- Prize Point is downstream, small, and open to public circulation. It is a collection/result place, not retail.

### W1 — Wyrm’s Crossing

**Guest sequence:** normal 5-wide Prism transit continues; optional side alcove offers a riddle and reconnects ahead.

- Wyrm is a stone/bone rib and head physically tied to rim and Foundry threshold; it cannot be a free-standing snake.
- Three inputs sit at player height with clues readable before committing. The public bypass is always visible.
- Correct state opens only an optional 2-wide rejoin or acknowledgement panel; it never grants essential access.
- The shell can build now. Add state machine only when correct/wrong/reset/timeout/service scenarios are tested.

### P1 — Foundry Gate

**Job:** explain Prismworks at a glance.

- Gate opens to an unobstructed Prism Spire view. It contains challenge rules, free-practice direction, water/rest point, and a public bypass.
- Array, Vault, practice Ascent, and observer route must be legible as separate choices.
- Do not put payment at the first thing a player sees. Payment belongs only beside an already-understood optional timed run.

### P3 — Prism Array

**Guest sequence:** free entry → colour/rule read → branch choices → safe wrong returns → visible exit/result → Foundry/Forge return.

- Physical maze is compact, not tall; preserve observer/wayfinding sightlines above/alongside it.
- Wrong branches return to a known choice point, not a dead end or staff route.
- Colour marker blocks are attached to wall/floor structures, never floating accents.
- A rear service strip reaches every reset/sign panel without entering public route.

### P4/P2 — Prism Ascent and Prism Spire

**Guest sequence:** Calibration Court → free 6-10 move practice → enclosed bubble lift → dry launch → one-way descending course → catch/checkpoint/recovery → Forge Deck.

- Core: bubble shaft, water containment, service mast, structural ribs, observer connections, and catches all belong to the same Spire assembly.
- Acts: Act I readable ledges/gates; Act II lateral transfer/frame crossing plus major controlled plunge; Act III high-contrast crown finale.
- Standard ledges use 3.0-4.5 block horizontal jumps. Major drops use their own enclosed water catch; never call them normal jumps.
- Every route cell gets headroom, next-move visibility, catch coverage, and recovery to a checkpoint or practice return.
- Observer balconies see active runners but cannot enter the course or interfere with paid/timed state.
- First opening is free practice only. Timed mode needs proven checkpoint authority, timeout, reset, server payment result, and clear public bypass.
- Crown rises only after free route is genuinely fun. No deep dungeon is added below catches until it proves a distinct outcome and return.

### P5 — Resonance Vault

**Guest sequence:** visible rule/demo → three separated input roles → shared state → one obvious completion → exit/Forge return.

- Shell supports 2-4 players standing apart but seeing a common state panel.
- Inputs must be individually testable; final result must be obvious (door/panel/light) and not an invisible comparator state.
- A posted solo fallback is mandatory if no group is available. It may be a simplified sequence, not an AFK wait.
- Build shell/stations now; do not imply completion until the real three-input circuit, timeout, reset, and service isolation pass.

### P6/P7 — Forge Deck and Service Gallery

- Forge Deck is a return/observer/social rail, not a shop or food venue. It contains completion display, next-challenge direction, 6-10 lean/seating positions, and separated exits.
- Service Gallery is concealed and reaches bubble sources, catches, checkpoint wiring, Vault/Wyrm resets, payment chest recovery, and storage.
- It must never become a public shortcut, a decorative basement, or a required route for a failed player.

## Detailed mechanics ownership

| System | Public owner | Service owner | Free-mode proof | Paid/advanced proof |
| --- | --- | --- | --- | --- |
| Carousel | Midway operator point | rear station bay | entity/cart dispatch and unload | optional replay only after stable |
| Mine Coaster | Frontier station | Works Yard | full ride, evacuation, cart recovery | optional replay only after stable |
| Target Range | firing line | Porch rear hatch | projectile hit, output, one reset | optional attempt pricing |
| Gold Sluice | public input/result | Assay/Works rear | input/result/collection/reset | optional replay pricing |
| Sky Lift | public entry/landing | lift shaft rear | bubble entry/ascent/exit/catch | none required |
| Prism Ascent | Calibration Court | Service Gallery | practice/catches/checkpoints | timer/payment/identity/reset |
| Prism Array | public entry | Array rear strip | branches/return/exit | none |
| Resonance Vault | Vault panel | gallery rear | cooperative/solo result/reset | optional only after free loop works |
| Wyrm | optional alcove | rim service | correct/wrong/bypass/reset | no paid passage |

## Completion definition

The park is not “complete” when every lot has blocks. It is complete when:

1. every build card has its public, exit, and service interface physically reachable;
2. every retained animal/setpiece passes visual and structural release;
3. every free experience passes live input, outcome, recovery, and group-flow proof;
4. every social node is visibly useful rather than filled with vendor clutter;
5. every optional paid attempt has verified grass acceptance, failure handling, reset, and public bypass;
6. the assembled day/night and group-session review says players choose to return.

Until then, build only the next phase that reduces uncertainty. Do not decorate around an unproven mechanic.

