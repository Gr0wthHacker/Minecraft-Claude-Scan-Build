## Redstone that is VERIFIED, not drawn (2026-08-30)

Jack: autonomous redstone, whole-island transformation from a brief, and up to five alt accounts
building at once. Decisions taken: **5 alts, server-legal · propose -> approve -> build · fully
functional redstone.** That third answer makes one thing mandatory before any of the rest, and
this section is that thing.

### Nothing in this pipeline had ever asked whether a circuit WORKS

`audit` asks whether a block state is legal, supported and non-colliding. `blocks` asks whether
the 1.19 server has it. `palette` asks what it costs. **A redstone circuit passes every one of
those while doing absolutely nothing**, and you find out by flipping the lever an hour later. It is
this project's oldest failure mode - *a clean audit and a wrong build* - aimed at the one subsystem
where the wrongness is invisible in every render, every audit and every BOM.

**THE PRECEDENT WAS ALREADY HERE.** The night pass is trusted because light is PROPAGATED through
the finished model and the spawnable cells are counted. Signal is the same shape of problem: a
value that spreads from sources, decays with distance, and is stopped by geometry. So
`mcbuild/circuit.py` is a simulator, and a circuit is verified before a block is placed.

    wire · redstone_block · torch · lever/button/plate · repeater (delay + LOCK) ·
    comparator (compare/subtract, container fullness) · observer · piston · dispenser (rising edge)

Every component's real state space came out of `blocks.json` - power 0-15, delay 1-4, compare and
subtract - so the numbers are the game's, not remembered. `tests/test_circuit.py` is fifteen
hand-worked cases, each one a fact you can check on a workbench.

**What is NOT modelled, stated because a simulator you trust past its limits is worse than none:**
quasi-connectivity (REPORTED per cell instead - Java also fires a piston from the block above, and
real circuits both use and are broken by that), Java's update order and 0-tick pulses, and
entities. **A container's fullness is an INPUT you state**, never something that fills itself:
pretending otherwise would certify a sorter that has never seen an item.

### Four bugs in the simulator, found by its own tests

The tests did their job before the simulator did. In order:

- **A torch was powering its own support block**, so it read "my attachment is powered", switched
  itself off, and every circuit oscillated every other tick. A torch powers everything around it
  EXCEPT what it is attached to; a lever is the opposite and strongly powers its attachment. **The
  two cases are not symmetric and cannot share a rule.**
- **The power model conflated "this cell radiates" with "this cell is aimed at".** That split is
  the whole model: `emit` is a torch or a lever radiating to six neighbours; `into` is a repeater
  or comparator driving one cell and nothing else - which is the entire reason a repeater is used
  to isolate one line from another. Missing it reported a torch as powering nothing.
- **A cell that emits is itself powered**, which sounds obvious and was missing - so a repeater fed
  directly by a lever never turned on, and the failure looked like the delay logic.
- **And one test was wrong where the code was right**: it put a lever on the block NEXT to a
  torch's support and expected the torch to react. Power does not flow between two solid blocks, so
  that circuit does nothing in Minecraft either. A hand-worked case exists to produce exactly that
  outcome.

### The module library: a contract, or it does not ship

`mcbuild/gen/circuits.py` - clock, latch, pulse, randomiser, payout, lamp_bank. **Every module
states a CONTRACT and `tests/test_circuits.py` asserts it by simulation.** A module whose contract
is not asserted does not belong in the file.

- **The clock's loop must close on the torch's SUPPORT, not on the torch.** The first version
  pointed the repeater at the torch's own cell, which does nothing: four tidy blocks, a clean
  audit, and it never ticked once. Found on this file's own first module.
- **A long lamp bank needs a repeater every 15.** Wire dies at 15 and a twenty-lamp sign lights two
  thirds of the way, which looks like a build somebody abandoned. Only simulation catches that
  before it is placed.
- **A payout fires every dropper exactly once per EDGE.** A dropper that fired every tick would
  empty the bank into the floor - the most expensive bug a casino can have.
- **RANDOMNESS IS NOT A CIRCUIT TRICK AND THE MODULE SAYS SO.** Redstone is deterministic; every
  random build borrows entropy from item routing, which this simulator has no entities to model.
  What is verified is one-lane-per-trigger and reset. The distribution is a property of the game
  and must be checked in world - `RANDOM_NOTE` travels with it.

### Wired into the pipeline, and it found a real bug immediately

Any design containing redstone is now inspected on generation: dead wire runs measured by true path
length from the nearest source, orphaned dust, components nothing can drive, repeaters pointing at
air, and QC risk. It runs over the whole island in **0.1s**.

Two corrections the integration needed, both of them rules this repo already knew:

- **Verify in CONTEXT, never in isolation** (rule 2). A design here is REMAINING WORK, so half a
  circuit may already be standing; inspecting the design alone called four of the sorter's
  comparators unwired. It inspects the composite now.
- **Diff against a BASELINE**, as the audit does. The island already carries twelve
  quasi-connectivity risks and seven orphaned dust groups of its own, and reporting those against a
  new design sends you hunting faults you did not cause. `circuit (new):` is what prints.
- And the "is it wired" test had to accept a component driven by a powered BLOCK rather than by
  dust - half the machines on this island are - because **a check that cries wolf is a check nobody
  runs.**

#### THE SORTER'S COMPARATORS WERE BACKWARDS, IN EVERY LANE, SINCE IT WAS WRITTEN

The first run against real work in this repo reported `comparator reads nothing x4`. It was right.
`gen/redstone.py` had a helper called `_toward`, whose own docstring said *"points a comparator back
at the filter hopper"* - and **a comparator reads what is BEHIND it and outputs where it FACES**, so
every lane read air and pushed its signal into the container.

Nothing else could have seen it. The state is legal, supported, affordable, in 1.19, and **our
renderer draws both directions identically** - which is the stair convention's exact failure mode,
in a subsystem where it costs the whole machine rather than one step. It is `_away_from_hopper` now,
and `test_the_sorters_comparators_read_the_hopper_rather_than_facing_it` pins all four runs.

**Still open on the sorter, and NOT guessed at:** with the comparators reading correctly, the
inspection now says `comparator drives nothing` - the design never routes their output to the
torches that lock the hoppers. That is a real gap in the signal path and a redesign, not a
one-line fix, so it is reported rather than invented. The simulator will judge whatever replaces it.

### What is NOT built yet

The simulator and the module library are the foundation; the two things Jack actually asked for sit
on top of them and are not written:

- **The island planner** - brief ("a redstone casino") -> module selection -> siting -> cost ->
  circuit verification -> a PLAN artifact for approval -> build. Almost every piece it needs
  already exists (`plot`, the distance-transform siting, `defer_to`, `after` ordering, `craft`,
  `print`, `autodig`); what is new is the planner itself and the approval gate.
- **The fleet** - up to five alts, which is a server-legal cap Jack confirmed and which must be
  encoded as a hard limit rather than a default. Needs a per-account profile (its own schematics
  dir, island and plot) and a coordinator that assigns designs.

### Checked against the source, not against itself (2026-08-30)

Jack supplied minecraft.wiki's Redstone mechanics and components pages. The model was built from
reasoning plus hand-worked cases, which is exactly the situation rule 11 is about, so it was
checked against them. **The power model held**, in its own words:

- *"Redstone power component, a powered redstone repeater, or a powered redstone comparator"*
  strongly power a block, and a strongly powered block *"can power adjacent redstone dust"* -- that
  is `into`.
- *"Redstone dust"* only weakly powers, and a weakly powered block *"cannot power adjacent redstone
  dust, but can still activate adjacent redstone mechanisms, and power redstone repeaters and
  comparators facing away from the block"* -- that is `emit` plus the wire-adjacency rule, and it
  is why `_solve_wire` takes `into` from opaque neighbours and never `emit`.
- *"the signal strength decreases by 1 for every block of redstone dust"*, and *"does not decrease
  when transmitted from redstone dust to a block or a redstone component"*.

**And it settled one thing the file had only DISCLAIMED.** QC was reported rather than modelled
because it was unverified; the wiki states it plainly -- a piston *"can also be activated if a
redstone signal is supplied to the block above them, even if that block is air"*, dispensers and
droppers too. It is modelled now, on by default, with `qc=False` available to prove a circuit does
not secretly depend on it. `quasi_connectivity_risk()` stops being a disclaimer and becomes a list
of places whose behaviour rests on a mechanic most people do not expect.

**The test for it was wrong first, and instructively.** It put dust DIRECTLY on the piston -- which
powers it by ordinary adjacency and proves nothing about QC. The real fixture is dust that never
touches the piston at all: the cell above is AIR and the dust is beside that air. A test that
passes for the wrong reason is worse here than one that fails.

(redstone.build is a tutorial site rather than a schematic or mechanics source -- no exportable
designs -- so nothing was taken from it.)

