## The casino, the planner and the fleet (2026-08-30, chunkscan 0.6.0)

Built on the circuit simulator, which is the only reason any of it can claim to work.

    python -m mcbuild plan "redstone casino"      # sited, costed, circuit-verified
    python -m mcbuild plan --approve casino       # THE GATE
    python -m mcbuild plan --emit casino          # configs, only after approval
    python -m mcbuild fleet --assign casino --accounts A,B,C
    /cscan fleet                                  # in game: who holds what

### Casino modules, out of verified circuits only

`gen/casino.py` - slot, prize_wall, marquee, counter. **Nothing in it invents a circuit**; every
mechanism comes from `gen/circuits.py`, whose modules each state a contract asserted by
simulation. THE HOUSE MUST NOT BE ABLE TO LOSE BY ACCIDENT, so: every button goes through a pulse
(a player HOLDS a button), the bank is a barrel a human stocks rather than something the machine
can reach past, and the randomiser's distribution is carried forward as UNVERIFIED all the way
into the plan.

**And the contract travels with the build**, in the sidecar - inputs, outputs, what it promises,
what it cannot. A machine whose promise lives only in a chat message is one nobody can audit a
month later, which this project has been bitten by before.

### COMPOSING VERIFIED MODULES DOES NOT GIVE YOU A VERIFIED MACHINE

The single most useful thing learned here. The first slot machine was a correct pulse, a correct
randomiser and a correct payout **sitting near each other with nothing between them**. Every part
passed its own test. The machine did nothing, and the plan's circuit inspection said so on the
first run: *wire dies before the end*, *dropper is not wired*, *repeater drives nothing*.

`circuits.connect` is the fix - an L path with a repeater every 14, because **wire dies at 15** and
that is the rule which turns a working bench test into a build that stops halfway.

**Then the connectors ate the components.** `World.put` overwrites, and a path that starts AT its
endpoint replaces the very thing it is connecting: the wired slot had a redstone wire where its
button should be and another where its payout dropper should be, and simulated as firing **zero**.
A connector runs BETWEEN two things and may not stand on either. `tests/test_casino.py` now
presses the button and asserts the dropper fires exactly once, which is the only form of this
check worth having - "no smells" is not "it works".

### The planner: propose, verify, approve, build

`mcbuild/planner.py`. **THE PLANNER DOES NOT UNDERSTAND ENGLISH AND DOES NOT PRETEND TO.** A brief
selects a THEME from a catalogue. That is an honest split: what a casino should contain is a
judgement, and whether it fits, collides, can be afforded and actually works is measurement.
Wiring a model to the first half is a one-line change and it still cannot skip the second, which
is the point - a model that could approve its own plan could build a spotted table at island scale.
An unmatched brief RAISES rather than defaulting to the only theme in the catalogue.

**The gate lives in `emit`, not in the CLI**, so no other caller can route around it.

Two real bugs it caught on its first two runs, both in siting:

- **THE TOPMOST SOLID CELL IS NOT THE GROUND.** The first plan sited the whole casino at **Y264,
  on top of the sky bird**, because a naive height map takes the highest block in each column.
  `ground_band` takes the MODAL surface height instead - a 2,000-column plate dominates any number
  of sculptures, and it needs no hand-written Y. It now sites at Y204, on the deck. This is the
  night pass's own lesson ("the lowest-standable classifier struck a THIRD time") arriving from the
  opposite direction.
- **A footprint is a box, so both corners are boundary-checked.** Checking only the origin sites a
  module that starts inside the plot and finishes over the line - exactly how the Island Run put
  120 cells past the edge.

And it refuses honestly: the marquee (20x5) and the prize wall (6x12) report **NO SITE**, which
matches this file's own note that the plate's largest genuinely flat area is 13x13.

### The fleet: five alts, one folder

Jack runs up to five alts, server-legal, all reading the SAME schematics directory on one machine.
**That removes almost everything a fleet would otherwise be about** - no per-account profile, no
separate design set, nothing to sync. What is left is the only hard part: who builds what.

- **FIVE IS A CAP, NOT A DEFAULT.** It is a server rule, so it is enforced in `assign()` rather
  than written in a comment. A tool that quietly allowed a sixth is a tool that gets an account
  banned.
- **TWO ACCOUNTS MUST NEVER SHARE A DESIGN** - not because the files collide (they are the same
  file) but because two printers placing into the same cells fight: each sees the other's block as
  already-built or as a deviation, and `Printer`'s report, the only honest signal this loop has,
  becomes noise. `/cscan print` REFUSES a design another account holds.
- **A CLAIM IS A LEASE, BECAUSE AN ALT CAN DIE.** A claim that never expires strands a design for
  ever; one with no expiry lets a second account grab it the moment the first is slow. Fifteen
  minutes, refreshed by a heartbeat while the loop runs - the same reasoning the chest cooling-off
  already carries, and it has to expire for the same reason.

### Two more of this session's own bugs, worth keeping

- **`Set.of` REFUSES DUPLICATES AT CLASS-INIT TIME.** Re-adding `"take"` to `RESERVED` turned every
  command in the mod into an `ExceptionInInitializerError` - six unrelated tests went red at once
  and none of them mentioned the list. The stack trace names the initialiser, never the duplicate.
- **A test fixture that is wrong twice for the same reason.** The connector's test drove it from
  one cell OUTSIDE the endpoint, which after the endpoint-skip left it adjacent to nothing. Same
  shape as the torch test earlier in the day: when a simulator and a fixture disagree, check which
  one models Minecraft.

### Still open

- **None of the casino has been placed in game.** The machines simulate correctly and the API was
  checked against the jar, but a slot machine paying out is reasoning until someone presses it.
- **The randomiser's distribution is unverified by construction** and says so at every level -
  module, build sidecar, and plan. Check the odds in world before anyone plays for stakes.
- **`gen/redstone.py`'s sorter still has no signal path** from its comparators to the torches that
  lock its hoppers. Reported by the inspection, not invented.
- **`tests/test_designs.py::test_all_configs`** still fails on `shop_islet.yaml`, unchanged and
  pre-existing.

