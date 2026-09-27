## The casino, and the four faults that cancelled each other out (2026-08-31)

`configs/` via `planner.make("casino")`, `mcbuild/gen/casino.py`, `mcbuild/gen/circuits.py`,
`mcbuild/circuit.py`. Jack: *"games are unique, creative, and interesting... this must come off as
a highly refined - perfect experience"*, on a **99x99** plot with the vertical free.

**32 modules on two floors, 22 of them games, 22% of the plot's cells.** Every game's contract is
asserted by SIMULATION, not drawn.

### What ships, and what does not

    high_roller     the level IS the display. Bar at the comparator; roll k lights k lamps.
    double_or_none  the level is DECIDED in the pit; only a win reaches the payout.

At 2 and at 3 outcomes that is four distinct games. **`chase` and `vault` were written, built
cleanly, and REMOVED** - `chase` lit every lamp on every roll, `vault` never opened its door. Every
tool in this project passed them, because they place legal, supported, affordable blocks in the
right shape. A casino with two games that work and two that look like they work is not a refined
experience, it is a trap.

### AN ANALOG VALUE CANNOT TRAVEL

The rule the whole subsystem turns on, and seven failed displays paid for it. A roll of 4 reaches
**four blocks** of dust. Any link, climb or fan-out spends that reach before the display gets it,
and a repeater carries the signal only by DESTROYING the value (it outputs 15). So there are
exactly two legal shapes, and both surviving games are one of them: the display sits AT the
comparator, or the decision is made where the value still exists and only a BOOLEAN travels.

### Four faults, none visible to anything but simulation

Every one of these placed legal, supported, affordable blocks and passed the audit, the BOM and
every render. Two of them CANCELLED EACH OTHER, which is the most expensive kind to have.

- **A HELD INPUT MUST BECOME AN EDGE BEFORE IT TRAVELS.** The pulse was built in the pit, so the
  run from the button carried the button's own line down the climb - a held button parked a
  permanent 15 on dust beside the comparator's path, the threshold's side input read it, and the
  machine paid nothing until the player let go. It fired correctly on a 4-tick press, which is
  exactly why it survived: **the machine worked for the input a test sends and failed for the
  input a player gives.**
- **A THRESHOLD IS A DISTANCE, so nothing may be laid in front of it.** The gate was joined to the
  comparator with `_link`, and that run decays the very quantity the gate exists to measure. The
  gate now sits ON the comparator's own output cell. Moving the pulse revealed this, because the
  held 15 had been subtracting every loss away - fix one and the other appears.
- **TWO SIGNALS MUST NOT SHARE A LANE.** With both fixed the machine paid on EVERY roll: the
  button's descent ran along the very cells the threshold occupies, so the gate's dust and the
  button's dust were the same dust and a press delivered a level of 8 straight into the boost. The
  cause was one level down again - **`connect` cannot make a pure vertical drop** (a dust staircase
  needs a block of run per course), and given no room to descend backwards it descended FORWARDS
  through the gate. The descent starts five blocks behind the pit now and lands on its target.
- **ANYTHING DOWNSTREAM OF A VARIABLE-LENGTH RUN MUST BE MEASURED FROM ITS END.** The collection
  barrel was at a fixed offset: behind the dropper at 3 outcomes, ON it at 2. The two-outcome game
  had no payout at all while the three-outcome one worked - one config value apart, both clean.
  And that barrel is **not decoration**: it is the solid block carrying the boosted signal into the
  dropper. Moved aside "to avoid a collision", every payout at every set of odds stopped at once.

### The one hazard that is asserted rather than fixed

**A stuck item in the randomiser's hopper pays continuously.** The comparator reads the hopper the
whole time; the button only makes the dropper eject, so at rest the hopper is empty and nothing
fires. An item LEFT there is a winning level standing for ever against an edge that never falls,
and the house pays until the barrel is empty. `test_A_STUCK_ITEM_IN_THE_HOPPER_PAYS_CONTINUOUSLY`
pins it deliberately: the fix is a latch-and-reset stage that has not been built, and a hazard
nobody has written down is one nobody checks for. **Load the dropper, never the hopper.**

### Also worth keeping

- **The odds are known, or the game does not exist.** minecraft.wiki gives an equal-probability
  item mix for exactly two fan-outs, so `RNG_MIXES` holds 2 and 3 and `randomiser` RAISES on
  anything else. A house that cannot state its own odds cannot know whether it is losing money.
  The mix is recorded on the build in `stock`, because the simulator has no entities and cannot
  check that the dropper was loaded right - the one thing it can do is say exactly what to put in.
- **The layout is a centre-out grid** (`planner.bays`), not first-fit: first-fit used 6% of the
  plot and left House Bank 3 with NO SITE. All 32 modules place now.
- **The reference casino is 135x105 and does not fit.** It is 185,198 blocks in
  `reference/casino_chirurg.litematic` and the palette is derived from it by measurement
  (`palette.affordable_like`: quartz -> white_wool at 24 RGB, black glass -> black_wool at 10),
  because its own materials are expensive here. The plot is 99x99; the answer is to STACK.

