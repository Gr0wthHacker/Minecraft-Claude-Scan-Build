# Park Line renewal

## Scope and authority

The railway renewal replaces the five old `transit` entries in
`park_final.world.json` with five crops of one continuous `parkrail` model.
`park_railway_v2.world.json` is the strict railway-only overlay. It retains the
other plots as reservations and passes navigation/composition independently.
The full legacy plan has an unrelated Signal Heron footprint/plot mismatch;
that is not silently repaired or counted as a railway pass.

The line remains V172–186, U0–599, with deck B+12 and stations at U77, U279,
and U505. Entry avenues remain U96, U260, and U524. Both Isthmus reaches,
U170–214 and U385–429, retain their original block states, including track
power sources. No land building or live world is replaced by this workflow.

## Construction and player experience

* Frontier Halt: tall timber depot, supported king-post trusses, pitched roof.
* Midway Central: larger hall and four-faced clock crown below B+35.
* Prismworks End: three sawtooth roof bays, cyan glazing and industrial frames.
* Station-adjacent arches have recessed spandrels and backed projecting rings.
* Seven-wide entrance portals mark the existing avenue approaches.
* Each station has separate marked queue lanes, two boarding edges, an additional
  exit stair, a public return through the arcade, and staff ladder access.
* Each boarding edge names its actual destination. End-facing platforms identify
  the scenic turnback instead of pretending to be the fast inter-land service.
* Six labelled staff reset panels are accessible from the arcade.
* Sign entities include Java 1.19 Text1–Text4, Color and GlowingText fields.

The budget ceiling is 42,000 blocks: 12,000 for each land and 3,000 for each
reach. The reviewed model contained 38,992 blocks against 35,602 in the railway
it replaced; with the dwell it is **39,220**. More than 87% is cheap tier. The
explicit 94-block expensive allowance is 88 cells of station clerestory glazing
and six working occupancy indicator lamps. The line uses **eighteen** detector
rails - arrival, clearance and dwell trigger, one of each per bay - and four
ordinary corner rails; repeaters and comparators are included in the BOM.

## The fleet, and the dwell

**A MINECART IS AN ENTITY, SO NO LITEMATIC IN THIS PROJECT CAN EVER CONTAIN ONE - AND NOTHING
SAID SO.** Measured across the whole shipped park before this pass: zero minecarts, zero
dispensers, zero activator rails. Six brake bays, six departure buttons, twelve detectors and a
complete signalling system, with nothing to run on them; a guest arriving at a platform had no
way to obtain a cart, and no sign anywhere named the omission. The fleet is a stocking contract
now, recorded in the sidecar under `renewal.fleet` and on the staff panel: **one minecart on each
of the six brake bays**, and `run ONE cart round the whole circuit before stocking the rest`. A
cart set down on a bay has not run over its own dwell trigger, so it waits there for a rider
rather than leaving on a clock with nobody aboard; from its first dispatch it circulates.

**AND AN ABANDONED CART STOPPED A RUNNING LINE FOR GOOD.** The occupancy memory is set by the
arrival detector and cleared only by the EXIT detector, which a cart nobody dispatches never
reaches, so the approach hold forty cells back stayed dead - simulated on the shipped model at 20,
100, 400 and 2000 ticks and still counting. The staff panel clears the MEMORY and not the CART, so
the recovery it offered opened the hold in front of a platform that was still blocked. That is not
an edge case; it is what happens the first time a rider walks away.

So each platform now clears itself. A **third detector** on each approach, `dwell_at` = 34 cells
out, feeds a chain of thirty repeaters along the maintenance kerb to a block beside the brake
rail. When it arrives the brake goes live, the cart leaves whether or not anybody is aboard, and
the exit detector then clears the memory and reopens the hold in the ordinary way. **The delay is
the route**: `dwell_delay` ticks per repeater over the cells between the trigger and the platform,
so moving the trigger moves the dwell and there is no second number to keep in step. Measured in
simulation: 120 redstone ticks from the trigger, about 4 s of which is the cart's own run over
those 34 cells, so the platform dwell is around seven seconds. The button remains, and dispatches
early; a bay with no arrival is never released.

**WHAT THE DWELL DOES NOT COVER, and it is the staff panel's real job.** A cart *destroyed* at a
platform - a player breaks it - leaves the memory set with nothing left to run over the exit
detector, so the dwell fires into an empty bay and the hold stays closed. That is exactly the case
the labelled reset was written for and the case its wording describes: CHECK LINE OK, CLEAR HOLD
ONLY. What changed is that the COMMON failure - a rider walking away - no longer needs a human at
all, and the reset is no longer being asked to recover a platform that is still blocked.

**And the hold is thirty cells of margin, not a headway guarantee.** It closes when the leader
passes the arrival detector ten cells out, so a follower already inside forty cells has passed the
hold before it shuts. `renewal.fleet.min_separation_cells` records the thirty and the live test
card still governs multi-cart running.

Three things this cost, each of which built cleanly and would have been invisible in game:

* **THE BRIDGE MUST COME DOWN ONTO A BLOCK, NEVER ONTO DUST.** The chain crosses the arrival
  readout at -10 on a three-block bridge a course up. Landed on a dust cell at -8 it released the
  brake **thirty-five ticks early**, by a route nothing in the chain could see: dust beside a
  powered rail activates that rail, an activated powered rail carries its own state eight rails
  each way, and -8 plus eight is the platform. The cart left before it had stopped, and in
  simulation it read as a perfectly good second pulse. Dust strongly powers the block beneath it,
  so the descent lands on its own support and the next repeater reads that.
  `test_nothing_but_the_release_can_reach_the_brake_through_the_TRACK` pins the general rule.
* **THE KERB IS THE ONLY LANE THERE IS**, and that was measured rather than chosen: of the whole
  fifteen-column section, the strip at x=1 beside the running rail is the one place with a
  contiguous free, solid-supported run in all six approach frames. It is clear from -45 to +45
  except for the two detector readouts.
* **A REPEATER IS THE ONLY SAFE THING TO LAY BESIDE A LIVE RAIL**, because it outputs from its
  front and nowhere else. The four dust cells the bridge needs are all a course above the rail.

The dwell costs six detector rails (six iron), 180 repeaters and 228 blocks: 39,220 against the
42,000 ceiling.

## The signs said the wrong thing, and four of them were cut mid-word

`_Deck.sign` truncated silently at fifteen characters, so the line shipped `BOARD THEN PRES`,
`BOARD WHEN CLEA`, `CHECK LINE EMPT` and `> PRISMWORKS 50` on a design that had had a formal
review - the damage shows only in a screenshot of the placed build. **It raises now instead of
shortening behind the author's back**, and every board states the service that actually runs:
`BOARD - IT GOES` / `PRESS TO GO NOW` rather than `BOARD THEN PRESS`, because a board telling a
rider the ride will not start without them is exactly what an abandoned cart used to prove false.

## Operating design and proof boundary

Each platform's stop rail slopes downward in the intended direction of travel.
A powered approach hump raises the preceding cell one course. The momentary
boarding button powers this stop rail; slope-start behaviour is an in-game
proof gate, not a consequence of a successful redstone test.

Each approach has another sloping holding rail forty cells before the platform.
The arrival detector ten cells before the platform sets a comparator feedback
memory. Occupancy survives after the cart leaves that detector. The exit
detector ten cells after the platform clears it. An inverter powers the holding
rail only when the memory is clear. The departure button does not clear occupancy.
Staff can reset an inspected empty block from its labelled panel.

The dwell chain is a THIRD input to the brake, and it is the one that makes this a service: the
memory closes the approach, the chain reopens the platform, and the exit detector reopens the
approach. This is an approach-holding system, **not a claim of collision-free operation
at arbitrary headways**. The gap between the holding rail and arrival detector,
plus signal propagation delay, means closely following carts may already have
passed the hold before it closes. Operate the first proof with one cart and do
not release unrestricted multi-cart service until headway trials pass. Chunk
unloading, simultaneous detector events, entry in the wrong direction, empty
carts and manual resets also require server trials. There is no assumption
that decorative geometry enforces one-way travel.

The local suite checks every emitted rail, bed and rider clearance; all six
station circuits over repeated 10-redstone-tick detector pulses; persistence,
clearance, opposite-track isolation, departure isolation and manual recovery;
continuous route geometry; structure connectivity; cost; sign text; and exact
reach preservation. The rail simulator now matches rail endpoints across slopes
and excludes side-by-side tracks from power propagation. It does not simulate
cart entities or Java's exact update order.

## Workflow and review evidence

Run from the repository root:

```powershell
python tools/railway_review.py prepare
python tools/railway_review.py greybox
python tools/railway_review.py detail
python tools/railway_review.py packet
python tools/railway_review.py assemble
python -m pytest tests/test_parkrail.py tests/test_parkrail_v2.py tests/test_circuit.py tests/test_circuits.py tests/test_park_walk.py -q
```

Preparation runs strict WorldSpec/worldflow. Greyboxes are generated from the
actual station massing with neutral materials and no signal detail. The massing
review accepted the three distinct silhouettes, registered entrances, B+35
height cap and separated exit flights before detail. Follow-up review caught
and corrected exposed cable runs, detached arch-ring cells, unsupported sign
locations, and one dark cell at the far turnback.

Detail runs the strict pipeline and cache. Cache inputs include the renewal
helper source hashes so an imported helper edit cannot reuse stale detail.
`out/railway_v2` contains the greyboxes, BOM/contract sidecar, three station
overview renders, arrival/facade/skyline/interior/void-side sheets, a measured
night-light heatmap, chunk packet, and `worldvalidate.json`.

Assembly reads the **current** Park Complete, removes only cells exactly matching
the old railway, and rejects conflicting replacement cells. It preserves other
tile entities, installs the new sign entities, and exports a combined candidate.
The chunk packet retains sign text. The worldvalidate report includes the hash
of the park used for that assembly and validates the existing avenue connection,
platforms, queues, exit stairs, service entries and six reset panels. Passing
walk validation does not substitute for the live ride tests below.

## Live test card and promotion

All live cases below are pending. No callable Minecraft control is available in
this task, and no live-world placement or operating claim has been made.

1. In Java 1.19 on the target server, update the track and verify its derived
   rail shapes/power. Check all signs, lamps, buttons and detector events.
2. With one occupied cart, approach every platform from normal running speed,
   stop within the sloped rail, board and depart with the button alone. Repeat
   with an empty cart and partial-speed arrivals, including the holding rail.
3. Hold a cart at the station. Approach with a second cart at generous spacing;
   verify it stops forty cells back, waits through a boarding-button press,
   and proceeds only after the first passes the clearance detector.
4. Test progressively shorter headways and stacked-cart cases. Establish and
   physically enforce a safe dispatch interval before multi-cart promotion;
   redesign the admission mechanism if the required interval is impractical.
5. Test both tracks concurrently, stop/start at chunk boundaries, unload/reload
   occupied sections, disconnect/rejoin, and interrupt power. A lost occupancy
   state or unintended release blocks promotion.
6. Verify queue boarding, cart dismount position, exit stair separation, staff
   ladder/hatch reach and manual recovery with multiple players.
7. Review in-game day/night views and replace provisional render assumptions
   about fences, glass, rails and redstone with actual screenshots.

Only after those cases pass should the candidate replace the current railway
and its assembled park output. The candidate is complete for local review;
live promotion remains gated on the listed evidence.

## In-game schematic delivery

At Jack's request, the reviewed geometry is now delivered under the normal
`Park Complete.litematic` and `Park Rail.litematic` filenames in the configured
game schematic folder. The complete park was reassembled against the latest
park output before delivery, and previous files were backed up under
`out/railway_v2/backups`. The active `configs/park_rail.yaml` now generates the
renewal, so a subsequent park assembly retains it. This enables in-game viewing
and testing; it does not mark the pending live-mechanics cases as passed.
