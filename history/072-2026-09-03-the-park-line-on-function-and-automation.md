## The Park Line, on function and automation (2026-09-03)

Jack: *"lets take a pass at the railway in terms of function and automation, lets make sure its
perfect."* Three things were wrong and every one of them passed the audit, the bill of materials,
the circuit inspection and every render this repo owns.

### THE LINE HAD NO CARTS, AND NOTHING IN THE PARK COULD MAKE ONE

Measured across the whole shipped park: **0 minecarts, 0 dispensers, 0 droppers, 0 activator
rails.** Six brake bays, six departure buttons, twelve detector rails and a complete signalling
system - and no way for a guest to obtain a cart. A minecart is an ENTITY, so no litematic in this
project can ever contain one; what was missing was anybody SAYING so. The park has the convention
already and it was not applied here: the menagerie ships every enclosure empty and each gate names
what to lead in and with what.

`renewal.fleet` in the sidecar and `STOCK THE CARTS` on the staff panel are the contract now:
**one minecart on each of the six brake bays**, and one cart round the whole circuit as the first
live proof before the rest are stocked. A cart set down on a bay has not run over its own dwell
trigger, so it waits there for a rider rather than leaving on a clock with nobody aboard - the
resting state and the stock are the same six cells.

### AN ABANDONED CART STOPPED A RUNNING LINE FOR GOOD

The occupancy memory is set by the arrival detector and cleared only by the EXIT detector, which a
cart nobody dispatches never reaches, so the approach hold forty cells back stayed dead. Simulated
on the shipped model: **still dead at 20, 100, 400 and 2000 ticks.** And the staff panel clears the
MEMORY and not the CART, so the recovery it offered opened the hold in front of a platform that was
still blocked. That is not an edge case - it is what happens the first time a rider walks away.

**THE DELAY IS THE ROUTE.** A third detector on each approach at `dwell_at` = 34 cells feeds a
chain of thirty repeaters along the maintenance kerb into a block beside the brake rail; when it
arrives the cart leaves, empty or not, and the exit detector reopens the hold in the ordinary way.
`dwell_delay` ticks per repeater over the cells between the trigger and the platform, so moving the
trigger moves the dwell and there is no second number to keep in step. 120 redstone ticks measured,
about 4 s of which is the cart's own run, so the platform dwell is about seven seconds. The button
still dispatches early; a bay nothing has arrived at is never released.

- **WHAT IT DOES NOT COVER IS NOW THE STAFF PANEL'S ONLY JOB.** A cart DESTROYED at a platform
  leaves the memory set with nothing left to run over the exit detector, so the dwell fires into an
  empty bay and the hold stays closed - which is exactly the case the labelled reset was written
  for and exactly what its wording says (CHECK LINE OK, CLEAR HOLD ONLY). The reset is no longer
  being asked to recover a platform that is still blocked, which is what it was doing before.
- **THE KERB IS THE ONLY LANE THERE IS**, and that is measured: of the whole fifteen-column
  section, x=1 beside the running rail is the one strip with a contiguous free, solid-supported run
  in all six approach frames. It is clear from -45 to +45 except for the two detector readouts.
- **A REPEATER IS THE ONLY SAFE THING TO LAY BESIDE A LIVE RAIL** - it outputs from its front and
  nowhere else. Dust beside a powered rail can activate it.
- **AND THE BRIDGE OVER THE READOUT MUST COME DOWN ONTO A BLOCK, NEVER ONTO DUST.** Landed on a
  dust cell at -8 the chain released the brake **thirty-five ticks early** by a route nothing in it
  could see: an activated powered rail carries its own state eight rails each way, and -8 plus
  eight is the platform. The cart left before it had stopped, and in simulation it read as a
  perfectly good second pulse. Dust strongly powers the block beneath it, so the descent lands on
  its own support and the next repeater reads that.
  `test_nothing_but_the_release_can_reach_the_brake_through_the_TRACK` pins the general rule: no
  cell of a chain that can power a rail may lie within eight rails of a brake.

### A LITEMATIC ON ITS OWN IS NOT A DESIGN, AND THIS ONE HAD BEEN SHIPPING AS ONE

`pipeline._save_outputs` writes the sidecar and the work list **only when the generator declares a
`world_origin`**, and `parkrail` never did - the review tool had supplied the origin by hand, once.
So every regeneration since replaced `Park Rail.litematic` and left `Park Rail.scan.json` and
`Park Rail.work.json` from **09:01 that morning**, describing a model that no longer existed: in
game `/cscan check` and `/cscan follow` were grading the new railway against the old one, and the
shipped work list still named twelve detector rails when the model had eighteen. The generator
declares its origin now (`params.origin`, and a crop moves it by exactly what it cut), and
`test_the_design_declares_a_world_origin_so_it_ships_a_SIDECAR_AND_A_WORK_LIST` is the tripwire.

### THE SUITE PINNED A MODEL THAT IS NOT THE ONE THAT SHIPS

`tests/test_parkrail.py` overrides the config to `renewal: False, bay_half: 3` and asserts the
legacy level-track contract. **Run against the shipped params, twelve of its thirty-six assertions
fail.** Some of those are retired canopy work and are meant to; the rest are the rail-correctness
ones its own docstring calls *"the only checks that can catch"* a line that cannot be ridden.
`tests/test_parkrail_dwell.py` asserts those against the model that is actually placed - rail state
legality, the corner and detector iron budget, the closed circuit across the humps - plus the dwell
and the fleet contract.

### AND FOUR SIGNS SHIPPED CUT MID-WORD

`BOARD THEN PRES`, `BOARD WHEN CLEA`, `CHECK LINE EMPT`, `> PRISMWORKS 50`. `_Deck.sign` truncated
at fifteen characters silently, and the damage shows only in a screenshot of the placed build -
this park has now done it in three separate generators. **It raises instead of shortening behind
the author's back**, and the boards state the service that actually runs: `BOARD - IT GOES` /
`PRESS TO GO NOW`, because a board telling a rider the ride will not start without them is exactly
what an abandoned cart used to prove false.

`Circuit.press` went the same way. It set an input at any coordinate without checking a control was
there, so a test could press AIR and pass - unlike `set_signal`, which has always validated. It
refuses anything but a button, lever, plate or hook now, and no existing test was pressing air.

**39,220 blocks against the 42,000 ceiling, one piece, 0 problems, 0 circuit findings, 94
expensive (the declared glazing and indicator allowance).** The dwell cost six iron, 180 repeaters
and 228 blocks.

### KNOWN-WRONG, AND IT IS BIGGER THAN THE RAILWAY: OUR REPEATERS AND COMPARATORS FACE BACKWARDS

`mcbuild/circuit.py._front` treats a repeater's `facing` as the direction the signal GOES, and says
so in a comment warning that getting it backwards is the commonest redstone mistake. **The game is
the other way round.** minecraft.wiki, Redstone Repeater block states: *"The direction from the
output side to the input side of a repeater. The opposite from the direction the player faces while
placing the repeater."* `facing` points at the INPUT.

The reference builds Jack supplied settle it without argument, and they are the only non-circular
evidence this project has:

| | at the `facing` cell | at the back |
|---|---|---|
| repeaters beside an unambiguous SOURCE | **29** | 0 |
| repeaters beside an unambiguous SINK | 3 | **48** |

and every comparator in the corpus faces something a comparator READS - hopper 86, lectern 44,
dropper 43, composter 14.

`reference/item_filter.schem` - a working sorter - has 4/4 repeaters with a `redstone_wall_torch`
at their `facing` cell and 4/4 comparators facing the filter hopper they read. **Our railway's
readout repeater is the mirror image of that**: `facing=west` with the detector rail it exists to
read at its BACK. Under the game's rule it reads the dead stone block on its other side and pushes
into a rail, so in game the memory never sets, the hold never closes and the dwell never fires -
the brake and the button still work, and the whole signalling layer is inert.

It is not one design's bug. `out/` holds **1,748 repeaters and 582 comparators**, and roughly
fifteen generators compute a facing - `circuits.py`, `casino.py`, `arcade.py`, `ticketing.py`,
`park_games.py`, `parkrail_signals.py`, `redstone.py` and the rest. The item sorter is the
exception that proves it: its lane was copied cell-for-cell from the reference, so its BLOCKS are
right in game while this file's own prose explaining them ("it is not reading the hopper, it is
driving it") is the inverted convention talking.

**THE FIX IS ONE CHANGE IN TWO HALVES AND IT MUST BE TAKEN TOGETHER**: swap `_front`/`_back` in
`circuit.py` so `facing` means the input, then flip every generator that computes one. Done apart,
the simulator and the emitters disagree about every circuit in the park. It rewrites every redstone
design here, so it is Jack's call and its own job - **not something to slip into a railway pass**,
and the reason the dwell chain above is built to the existing convention: one convention in the
tree, flipped once, everywhere.

