## The autopilot flies with real key presses (2026-09-26, chunkscan 0.9.13)

Jack: *"just fix autopilot so its key input"*. He chose this over rebuilding the builder as a
separate mod. The code is on branch `fix/autopilot-key-input`.

**Why.** The quartz miner showed that the server's anti-cheat snaps back any motion no key
combination explains. The miner was twitchy and stuck until it pressed only real keys. The
autopilot wrote velocity directly (`setDeltaMovement` at 12 sites, cruising at 1.5 blocks a
tick), which is the same fault. In flight it is worse: a snap-back can put the body against a block,
and on this server contact ends flight.

**How.** Autopilot's decisions are unchanged: the route, the fence, the ground clearance, and the
swept `avoid` test. Only how the step is applied has changed. Each tick, inside vanilla's own
input sampling, `KeyFlight` tries every key combination a player could hold: eight directions or
none, sprint with W, and jump, sneak or neither. It predicts each combination's motion with
vanilla flight physics (push 0.98 × flySpeed, doubled when sprinting; vertical 3 × flySpeed; air
friction 0.91 horizontal and 0.6 vertical) and presses the one landing nearest the wanted step.
Any combination whose motion `Autopilot.clean` says would leave the fence or touch a block is refused.
"Never send a step that touches anything" now applies to the motion that actually happens.

- **The jump guard.** A fresh press of jump is refused within 10 ticks of the last one, because vanilla
  toggles flight on two presses inside 7. Holding jump down to climb is fine. Only the rescue and
  take-off taps (`hold` → `KeyFlight.raw`) bypass the guard, on purpose.
- **Commands last one tick.** Fly and walk commands expire unless refreshed, so a tick that
  issues nothing leaves the body coasting, as a skipped velocity write used to. Taps persist, and
  so does a stop, which brakes with keys until the body is nearly still and then hands the controls back.
- **`VERTICAL_GAIN`/`liftFor` are gone.** They over-commanded a written y velocity to beat flight
  friction. Held jump climbs for real, with vanilla's own damping.
- **Top speed is now vanilla's:** about 1.09 blocks a tick sprint-flying, against the old 1.5. A
  speed dial above that saturates.

The source-text tests that pinned the velocity design now pin the opposite: `itNeverWritesTheVelocity`.
`KeyFlightTest` covers the key chooser.

**Not proven in game yet.** When merging into `feature/park-overhaul`, the uncommitted `Autopilot`
edits there (the old miner's unfinished rewrite) will conflict. That work is superseded by
`quartzminer` and can be dropped.
