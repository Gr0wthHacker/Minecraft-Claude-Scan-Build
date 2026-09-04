# Final Park Experience Reality Audit

## Decision

The retained program can become an awe-inspiring Skyblock destination. It is intentionally better than a “fill every plot” theme park: three visually distinct lands, a clear movement story, three skyline anchors, optional skill, a cooperative loop, and no fake retail or dead scenic clutter.

It is **not ready to be described as fully functional or launch-ready**. The physical program is strong; the current evidence and configuration coverage are incomplete. Build the free physical park now, but hold public paid/replay claims until the launch gates below are satisfied.

## What players will actually do

| Land | First-visit hook | Returnable loop | Social value | Verdict |
| --- | --- | --- | --- | --- |
| Midway | Carousel Court, Sky Lift, visible choice | three compact skill games and prize collection | visible queues, regroup point, short shared rides | Strong entry/social hub once rides are live |
| Frontier | Mine Ridge and coaster sightline | coaster replay, aim game, process game | queue watching, station energy, compact counter | Strong high-energy land, but rail/entity proof is essential |
| Prismworks | Spire visible from threshold | practice/timed parkour, Array route choice, Vault cooperation | spectators, party puzzle, comparative skill | Best long-term return land if recovery and state machines prove reliable |
| Claim Line | clear visual transition | none required | fast group movement | Correctly restrained |
| Wyrm’s Crossing | threshold reveal | optional free riddle only | small shared discovery | Good only after its state/reset loop works |

The portfolio has enough variety. Do **not** add more headline rides, food, shops, passive terraces, or animal collections. The remaining gap is not content count; it is proving the existing loops and giving groups a reason to return together.

## The social-destination test

The plan passes the visual and variety tests, but needs these operating rules:

1. Keep Welcome Court, Mining Square, and Forge Deck open and visibly connected to active play. They are the three intentional gathering nodes.
2. Build queues beside—not through—spectator sightlines. A player should be able to watch a coaster dispatch, game result, or Spire runner while deciding whether to join.
3. Make Resonance Vault genuinely 2–4-player first, with a clearly marked solo fallback. It is the only retained cooperative loop and must not devolve into three isolated buttons.
4. Run a small, truthful challenge cadence using existing experiences: a manually curated or server-verified “current challenge” board at Welcome Court and Forge Deck. It may display only an operator-set challenge or a value the installed system can actually verify; never fake a live leaderboard.
5. Keep paid attempts optional and non-random. Grass should buy a timed/replay attempt with a clear result, never basic access, luck, or a hidden reward.

This adds no new land program. It turns the existing routes, Vault, games, and observation decks into a place where groups form, watch, retry, and return.

## Buildability and truth table

| Retained system | Possible in vanilla-style 1.19 blocks | What the generator can prove | What must be proven live | Launch status |
| --- | --- | --- | --- | --- |
| Paths, thresholds, maps, service corridors, setpieces | Yes | legal blocks, anchors, supports, route geometry | group congestion and readability | Build now |
| Animal setpieces | Yes | anatomy, material, connectivity, multi-view packet | in-context human visual approval | Build now after visual approval |
| Bubble lifts and water catches | Yes | source geometry, containment, service access | player ascent, dry exit, collision, recovery | Build physical version; no timed mode yet |
| Prism Array | Yes | physical route/branches/markers | wrong-route recovery and sign comprehension | Build and playtest |
| Prism Ascent practice | Yes | supported course/catches and declared route data | every jump, actual catch, checkpoint/restart, novice run | Build and playtest |
| Resonance Vault | Yes | shell, stations, public/service apertures | three-input logic, visible state, reset, solo fallback | Build shell only; logic is a gate |
| Wyrm riddle | Yes | threshold form and optional alcove | correct/wrong sequence, bypass, reset | Hold until state machine is tested |
| Target/archery game | Yes, if projectile use is allowed | target/circuit geometry | arrows/projectiles, hit signal, reset, abuse handling | Conditional |
| Carousel and Mine Coaster | Rails are legal; a ride needs live minecart entities | rail topology, clearance, station geometry | cart spawning, dispatch, boarding, unload, stuck-cart recovery, entity limits | Conditional—top blocker |
| Grass payment chest | Per confirmed server behavior | only placement/interface around the chest | correct-grass acceptance, rejection, timeout, duplicate payment, refund/recovery | Conditional |
| Timed paid challenge / leaderboard | Only with server support | local gates/panels | timer authority, identity, persistence, abuse/restart handling | Hold |

### Critical entity-policy decision

mcbuild/server_profile.py currently declares allow_entities: False. The repository also documents that litematics cannot place minecarts or arrows as entities. Therefore the schematics can build rails and targets, but they cannot independently create a working cart ride or prove an archery shot.

Resolve one question before declaring the ride plan viable:

> Does Skyblock.net permit and reliably manage runtime minecarts, arrows/projectiles, and their cleanup in this park zone?

If yes, define the runtime spawning/reset procedure and live-test it. If no, Carousel and Mine Coaster need explicitly approved non-entity replacements; they must not retain ride names based on static rails.

## Architecture findings

### Strong and should remain frozen

- One clear distribution land, with Frontier and Prismworks as distinct destinations.
- Three skyline dominants only: Sky Lift, Mine Ridge/Coaster, Prism Spire.
- Limited food and no fake retail.
- A free practice/bypass route before any paid skill attempt.
- Setpieces attached to actual infrastructure: Sloth to Sky Lift, Heron to signal trestle, Wyrm to threshold.
- Deep vertical reserve remains empty until a distinct, proven experience earns it.

### Required corrections before detailed assembly

| Finding | Why it matters | Required correction |
| --- | --- | --- |
| No frozen WorldSpec maps the U/V plan to exact world plots, protected cells, and Y bands | modules can collide despite a good document | freeze WorldSpec and route/service/skyline reservations before any final placement |
| Legacy configs mostly have narrative park_contract fields, not enforced public interfaces | a visual generator can still ship without a usable queue, exit, or service path | migrate retained modules to world_contract, typed anchors, fun contract, and scenario checks |
| The current Prism Ascent generator has physical geometry but not a completed checkpoint/timer system | it must not be sold as a timed challenge yet | certify free practice first; add one state machine only after live catch tests |
| Vault stations are intentionally nonfunctional placeholders | social claim would be false | create and test the bounded three-input circuit before opening Vault |
| Existing Isthmus generator is the older overfull program | it conflicts with the final reduced reach design | replace it with separate Claim Line and Wyrm Crossing modules; do not paste old Isthmus output |
| 5-wide transit is a safe minimum, not enough at every social choke point | groups, queues, and observers can collide | keep 5-wide connectors, but make decision courts, queue entrances, and exits at least 7-wide clear zones |
| Payment behavior is known server-side but not represented as an integration contract | currency loss or duplicate entry destroys trust | write success/reject/cancel/timeout/refund/manual-recovery acceptance cases before use |

## Vertical reality check

The vertical plan is viable within Java 1.19’s -64 to 335 height range only after the site build plane is frozen. The planned high anchors stay deliberately below the stated crown reservation. The unbuilt deep bands are a strength, not unfinished content: they protect spectacle, avoid confusing vertical routes, and leave room for one future experience only if it has a unique verb and a safe return.

The key constraint is operational, not height: every high route needs a visible recovery route, a service route that does not intersect guests, and a return to the public surface. Every below-grade room needs a reason to exist; Prism catches and Vault machinery qualify, generic dungeon filler does not.

## Non-negotiable launch gates

1. Freeze and validate the 600 by 200 WorldSpec, including all paths, queues, exits, service strips, protected rim, and view corridors.
2. Resolve runtime entity/projectile policy. Run a full minecart and target-shot test on the actual server.
3. Assemble and walk the free public route end-to-end with a new player and a group; correct bottlenecks before decoration.
4. Prove bubble ascent, top exit, every parkour landing, every catch, and recovery from each failure.
5. Prove each game’s input, result, single-award/reset behavior, and abuse recovery.
6. Implement Vault and Wyrm only as small tested state machines with visible state, bypass, timeout, and service reset.
7. Test the grass chest success, non-grass rejection, cancellation, duplicate input, timeout, refund/recovery, and staff recovery.
8. Run day/night visual packets and human review for all skyline pieces and animal setpieces in their actual plots.
9. Open free practice and spectator loops first. Enable paid replay only after its free version works reliably.
10. Run an actual group session before public launch; retain only the activities players choose to repeat without being told.

## Final assessment

**Experience design: green, with disciplined scope.** The park can feel complete because each land has a distinct purpose and the connectors do not waste the program.

**Functional readiness: amber.** The core physical builds can proceed, but live mechanics, entity policy, WorldSpec placement, and public-interface migration remain essential.

**Paid/community launch readiness: red until the ten gates pass.** The correct route to an impressive community destination is not more decoration. It is a visibly excellent physical build whose rides, recovery, payment, cooperative state, and group flow work honestly every time.

