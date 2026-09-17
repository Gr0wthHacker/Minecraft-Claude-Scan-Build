# The auto-fly / auto-build loop: a full audit (2026-09-17)

Jack: *"auto placing and auto building is still essentially not functional, lots of stopping,
twitching, tons of issues; commit a full audit of it all and lets make this work once and all."*

This is that audit. It is a **static** audit: every finding is read off the code with a file and a
line, and the one change shipped in this pass (§F1) is validated by unit tests and by reasoning.
**None of it has been run in game, and the Fabric toolchain will not resolve in the sandbox this was
written in** (`fabric-loom:1.17-SNAPSHOT` is refused by the proxy), so `./gradlew build test` was not
run here either. That matters, because this loop's entire history — the whole `## The park`/autofly
saga in `CLAUDE.md` — is a record of fixes that looked right and were wrong until Jack flew them, and
*"a change you have just made is exactly the suspect that gets convicted without evidence."* So the
shape of the deliverable is deliberate: **one structural fix that cannot make things worse, plus a
ranked list of the remaining suspects for you to confirm in game one at a time**, which is the method
that has actually worked on this file.

Run `cd chunkscan && ./gradlew build test -q` before flying it.

---

## How the loop is actually wired

Three `END_CLIENT_TICK` handlers run every tick, in **registration order** (`ChunkScanClient
.onInitializeClient`):

1. **`Hud.tick`** (registered L110). Drives `Withdraw.tick`; every `EVERY_TICKS = 40` (2 s) runs
   `advance()` — the recount that reads the work list, picks a spot and a station, and calls
   `guide()` to move `Hud.target`, the thing the flight chases.
2. **`Autopilot.tick`** (registered L113). Every tick: reads `Hud.target()`, and steers toward it —
   sets `player.setDeltaMovement(...)` and `player.setYRot/​setXRot(...)`.
3. **The build/machine handler** (registered ~L2247). Runs `Printer.verify` then, for the followed
   design, finds the nearest in-reach unbuilt cell and calls `Printer.place`, which **also** sets
   `setYRot/​setXRot` and sends a `ServerboundMovePlayerPacket.Rot`.

So in one tick the **player's look angle is written twice** — once by the autopilot (aim at the next
waypoint), once by the printer (aim at the block) — by two handlers that do not know about each
other. The only thing that keeps them apart is `AutomationControl.blocksMovement()`, which the
autopilot checks (`Autopilot.tick` L747) and which returns `true` while `Printer.busy()`.

`Printer.busy()` is `!pending.isEmpty()` — true from the moment `place()` sends its interaction until
`verify()` confirms the placement, and `verify()` will not confirm until the **server acknowledges**
the block-change sequence (`ClientLevelMixin` → `handleBlockChangedAck`). That is a network
round-trip. So the two controllers are supposed to take turns: the printer owns the tick while a
placement is in flight, the autopilot owns it otherwise.

The seam leaks in exactly the phase that matters — the approach to a station — and that leak is the
twitch. The rest of this audit is that, and the four other things around it.

---

## F1 — TWO CAMERA WRITERS, NO ARBITER  *(the twitch; fixed in this pass)*

**Symptom.** Camera whipping and the flight stuttering as it comes in to build.

**Evidence.**
- `Printer.place` (`Printer.java:341-342`): `p.setYRot(plan.yaw()); p.setXRot(plan.pitch());` and a
  `Rot` packet — every tick it places.
- `Autopilot.tick` aim section (`Autopilot.java`, `// ---- aim`): `p.setYRot(approach(...))` — every
  tick it steers.
- The build handler's placement guard (`ChunkScanClient.java` ~L2291) gated on `printDesign`,
  `warmingUp`, `Printer.busy`, `ready`, container, `Withdraw.busy`, `Unbox.running` — but **not** on
  whether the autopilot was mid-flight.
- `Printer.REACH = 4.2`; the handler places any cell within `REACH + 1 = 5.2`. The flight's arrival
  ceiling is `ARRIVED = 3.0`. **Those windows overlap.** So while the flight is still 3–5 blocks out
  and steering the camera at its waypoint, the printer already sees a cell in reach, snaps the camera
  at it, places, and goes `busy`. Next tick the autopilot is frozen (busy); the tick after, busy
  clears and it snaps the camera back to the waypoint and moves a little; the printer grabs another
  cell and snaps again. Camera whip + one server-round-trip pause per opportunistic placement =
  *"twitching, lots of stopping."*

**Fix (shipped).** Establish a single camera owner per tick. `Autopilot` now carries a `navigating`
flag: reset at the top of every `tick()`, set true only where it actually steers (the aim section,
and the two recovery moves that drive the body and early-return before the aim). `Autopilot
.navigating()` returns `on && navigating`. The build handler now also returns early
`|| Autopilot.navigating()`, so **the printer holds its placement until the flight is parked**.

Why this is safe rather than a guess:
- It only defers the *opportunistic mid-flight* placement. The loop already flies you to a standing
  spot and expects you to build from there (`Hud.stand`), so nothing the loop relies on is lost.
- It cannot starve building. `hasArrived`'s *"stopped getting closer"* branch parks the flight within
  `CLOSING_PATIENCE = 12` ticks of ceasing progress even against a wall, so `navigating` goes false
  and placement resumes; and `navigating()` is false whenever autofly is off, so manual building is
  untouched.
- It also removes most of F2's damage for free: with no mid-flight placements, the printer never goes
  `busy` mid-flight, so the approach no longer freezes.

Pinned by `AutopilotTest`: `theTickClaimsTheCameraWhereItSteers`,
`theBuildPrinterHoldsWhileTheAutopilotSteers`, `navigatingIsFalseWhenAutoflyIsOff`.

**Still owed:** fly it. Expect a smooth glide to the standing spot, a pause on arrival, then a burst
of placement with the camera flicking between blocks (that last part is normal printer behaviour and
is unchanged).

---

## F2 — PLACEMENT FREEZES THE WHOLE FLIGHT FOR A SERVER ROUND-TRIP  *(stopping; partly relieved by F1)*

**Symptom.** On a public server (skyblock.net has real latency) the flight moves in short jerks, worst
when it should be gliding between work.

**Evidence.** `Printer.busy()` (`Printer.java:435-437`) stays true from `place()` until the ack lands
(`verify()` gate, L379). `AutomationControl.blocksMovement()` (`AutomationControl.java`) returns
`Printer.busy() || …`. The autopilot, seeing `blocksMovement()` true (`Autopilot.java:747`), zeroes
delta movement and releases keys and returns — for the **entire ack latency of every single block**.
At ~200 ms ping that is ~4 ticks frozen per block; interleaved with `interval = 2` ticks of placing,
the flight is stationary most of a build session.

While *parked at a station* that is exactly right — you want to hold still and place. The damage is in
the phases where the flight should be moving: coming in to a spot, and hopping between stations. F1
removes the coming-in case (no placement until parked). The between-stations case remains: when a
station is exhausted the autopilot wants to fly to the next `bestStand` cell, but if the last
placement is still un-acked it is frozen until the ack.

**Proposed fix (needs in-game validation).** `blocksMovement()` should not freeze the autopilot for
`PRINT` the way it does for `WITHDRAW`/`CRAFT`/etc. Those own the player because flying off mid-action
breaks a chest or a craft; a `PRINT` in flight does not — F1 already keeps placement to the parked
phase, so if the autopilot is moving, the printer is by construction not placing. Concretely: drop
`Printer.busy()` from `blocksMovement()`'s disjunction (keep the `ActionGate` owner clauses). The
autopilot's own `arrive()`/hold logic already keeps it still while parked, so nothing starts flying
away mid-placement.

**Risk.** If for any reason the printer *does* place while the autopilot thinks it is still moving,
you get F1 back. So ship F1 first, confirm no mid-flight placement, *then* try this. Validate by
watching the between-station hops: they should be one smooth flight, not a stutter.

---

## F3 — THE STANDING TARGET IS RE-PICKED EVERY RECOUNT  *(twitch when adjusting)*

**Symptom.** *"getting too close when adjusting and then stopping flight"* — the flight lurches every
couple of seconds while building.

**Evidence.** `Hud.stand` recomputes `Plan.bestStand` on every 2 s recount and, on `RECENTRE`,
`guide()`s a new cell (`Hud.java` ~L640). When `target` changes, `Autopilot.tick` resets
`bestDist`/`sinceCloser` (L791) and `needsRepath` fires (L1275) — a fresh approach, i.e. a lurch.
This is damped by two guards already: `allWithinReach → return` (L633, don't re-aim while the printer
can still touch everything left) and `DWELL_MS = 4000` (hold a freshly-reached station 4 s). The
residual is real when cells fall out of reach and `bestStand` genuinely moves — which is the intended
*"walk around the work as it gets built"* and mostly wanted.

**Proposed fix (low priority, needs validation).** Only re-`guide` when the new stand cell differs
from the current `target` by more than a small threshold (e.g. > 1.5 blocks), so a centroid that
drifts a block as cells go in does not command a new approach. Today the guard is `!re.equals(target)`
(`Hud.java` ~L642), which fires on a one-block move. Damp it. Low risk, small win; do it after F1/F2
are confirmed so its effect is observable rather than lost in the bigger twitch.

---

## F4 — THE PREDICTION-ACK GATE CAN HANG THE ENTIRE LOOP  *(the most likely "not functional"; unconfirmed)*

**This is the finding to check first in game, because if it is real it is the whole complaint.**

**Evidence.** `Printer.verify` (`Printer.java:379-387`) will not confirm a placement until
`acknowledged(pendingSequence, ((PredictionAccess) mc.level).chunkscan$acknowledged())`. That ack is
maintained by `ClientLevelMixin.chunkscan$afterAck`, injected at `RETURN` of
`ClientLevel.handleBlockChangedAck(int sequence)`. If that ack never advances past the placement's
sequence — because the mixin does not apply on MC 26.2 (wrong method name/descriptor in the refmap),
or the server does not send `ClientboundBlockChangedAck` the way the client expects — then **every
placement hangs `busy` for 100 ticks and then calls `Hud.off()`** with *"printer paused: no server
placement acknowledgement after 5 seconds."* One block placed, five seconds frozen (F2), loop dead.
That is *"essentially not functional."*

The mixin looks correct on paper (`handleBlockChangedAck` is the Mojmap name; `currentSequence()` is
monotonic and read after `useItemOn`, so `pendingSequence` is the sent sequence; `chunkscan$ack` is a
running max). But *"always `javap` the real jar before assuming an API"* — this is exactly the case
that rule is for, and it has not been done for this method on 26.2.

**How to confirm (in game, cheap).**
1. `/cscan place <small design>` + `/cscan follow` and watch chat. If you see *"no server placement
   acknowledgement after 5 seconds"*, F4 is real.
2. If unsure, temporarily log `chunkscan$sequence()` vs `chunkscan$acknowledged()` around a placement
   and confirm the ack climbs to meet the sequence within a tick or two.

**Proposed fix if real.** Two independent hardenings:
- **Do not kill the loop on ack timeout.** A missing ack should fall back to *client-predicted*
  verification — the placed block is already visible client-side (`getBlockState` returns it via
  prediction), so `Work.matches` can confirm it without waiting for the server ack, at the cost of
  occasionally counting a placement the server later rolls back (rare, and self-corrects on the next
  recount). Turning the whole loop off on a latency hiccup is the wrong trade for an unattended run.
- **Confirm the mixin applies** (`javap` the 26.2 `ClientLevel`; check the built refmap names
  `handleBlockChangedAck`). If it does not, that alone is the bug.

---

## F5 — THE CONTROLLER IS FOURTEEN BEHAVIOURS FIGHTING OVER SHARED STATE  *(the meta-cause)*

`Autopilot.tick` runs, in order, every tick: fall-rescue, flight-regain, arrival, flight-revoked
emergency, bump handling, `Nav.escape` flooding, wedged-give-up, the recovery ladder
(`BACK_OFF`/`CLIMB_OUT`/`GO_HOME`), repath, waypoint advance, pure-pursuit aim, `cruiseSpeed` taper,
`keepAirborne`, `align`, `blind`/`unstick`/`sidestep`. Each mutates shared statics — `path`,
`pathTo`, `bumps`, `wedged`, `trouble`, `stage`, `bestDist`, `sinceCloser`, `legFrom`,
`announcedArrival`. Every one was added to fix a specific symptom Jack saw in game, and each is
individually reasonable; the *interactions* between them are where twitch is born (the file already
documents two such cases: *"two mechanisms fighting"* on the shaft loop, and the *"moves like 5
degrees and gets stuck"* bump handler).

**This is not something to rewrite speculatively** — that would throw away a year of in-game-validated
detail. It is a standing hazard to name, and the rule that falls out of it is the one this project
already lives by everywhere else: **the next fix to this file should REMOVE a layer or a piece of
shared state, not add one.** F1 adds a flag but subtracts a conflict (it makes camera ownership
exclusive, which is a simplification of the coupling, not a new heuristic in the steering).

---

## F6 — THE STANDING-SPOT CONSTRAINTS CAN BE UNSATISFIABLE  *(situational stalls; needs validation)*

A parked build spot must satisfy three things at once: ≥ `GROUND_CLEAR = 2.5` of air below (or the
server ends flight — `Autopilot.GROUND_CLEAR`), within `Plan.reach() = 4.2` of the work, and inside
the `ARRIVED = 3.0` ceiling of where the autopilot will actually stop. On rolling terrain, under the
plate, or in a two-course room these can leave `Plan.bestStand`/`Nav.standoff` with no cell that is
both high enough off the floor and close enough to the work. When that happens the flight either never
parks (so, with F1, placement never starts) or oscillates between "too close to a wall" and "too far
to reach." This is consistent with *"either not getting close enough, or getting too close when
adjusting and then stopping flight."*

**How to confirm.** Watch whether the stalls cluster in specific terrain (rolling ground, low
ceilings, under-plate) rather than everywhere. If so, F6 is a contributor.

**Proposed direction (needs validation).** When no spot satisfies all three, prefer *reach over
altitude* by a measured amount and let `keepAirborne` hold the altitude, rather than refusing the
spot — the printer reaches 4.2, so a spot 3 blocks off the work with 2 of air below builds fine and
`keepAirborne` keeps you off the floor. This is a `Plan.bestStand` scoring change; test it against the
existing `PlanTest` fixtures first.

---

## Priority, and the method

Confirm and fix in this order, **one at a time, flown between each** (the only method that has ever
worked on this file):

1. **F4** — check for the ack-timeout message. If present, it is the "not functional." Cheapest to
   confirm, highest impact.
2. **F1** — shipped. Fly it; confirm the approach glides and does not stutter.
3. **F2** — drop `Printer.busy()` from `blocksMovement()`; confirm between-station hops are smooth.
4. **F6** — if stalls cluster in bad terrain, retune `bestStand`.
5. **F3** — damp the re-guide threshold once the bigger motion is gone and its effect is visible.

Everything past F1 is a hypothesis with a code citation, not a change made blind. F5 is the standing
warning that governs all of them: subtract, don't add.
