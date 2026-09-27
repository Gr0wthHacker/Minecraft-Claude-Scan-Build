## The park overhaul: typed interfaces, capacity-aware streets, and a vertical park (2026-09-01)

Two briefs landed together - `PARK_OVERHAUL.md` with the three land specs, and
`PARK_VERTICAL_MASTERPLAN.md` - and they ask for the same thing from opposite directions: a park
where every public build has a purpose, a reachable entrance, a usable interaction, a safe exit and
a reason to sit where it sits, told across six elevation bands rather than on one plane.

The rebuild's own first instruction is the one that had to be built before anything else:

> "The existing park parallel manifests have module placement data but no typed anchors,
> dependencies, or interface links. The rebuild begins by making those contracts mandatory. A plan
> cannot be prepared or promoted when a public module has empty anchors."

### 61 PUBLIC ANCHORS WERE STANDING ON NOTHING, AND NOTHING COULD SEE IT

The path pass ran ONE spur to ONE front-of-building point per module. Measured against the brief's
own interface table, that leaves - across the three lands - every ride exit, every emergency exit,
every flank queue mouth and every view approach unreached. A building has more than one way in; a
pass that knows about one of them cannot satisfy rule 2, and no check in the project asked.

    mcbuild/interfaces.py    what interfaces a module owes, and where they are
    mcbuild/circulation.py   the streets, built FROM those interfaces
    mcbuild/pathgraph.py     capacity roles, and rules 4 and 6 as geometry
    mcbuild/bands.py         the masterplan's six elevation bands
    mcbuild/gates.py         the ten promotion gates
    python -m mcbuild parkgate <plan>

**AN ANCHOR IS A PLAN-TIME PROMISE, NOT A RENDER-TIME MEASUREMENT.** It has to exist before any
block is generated or it cannot gate generation, which is the whole point of the rule - so the
planner derives every anchor from a module's box, facing and TYPE, and the route gate then proves
the streets honour it. A queue mouth and a discharge are placed on opposite flanks by construction,
because rule 4 is easier to keep than to check.

**A FRONTAGE IS A WALK, NOT A POINT.** The fix is what a real street does: a pavement along the
face past every door on it, joined to the avenue once. One route serves a queue mouth at 0.20 and
an exit at 0.80 of the same face, which is why the anchors are spread across the face at all.

### THINGS THAT ONLY A MEASUREMENT WOULD HAVE CAUGHT

- **A ROLE IS DECLARED, NOT INFERRED FROM WIDTH.** Inferring it makes the capacity gate a
  tautology: every 3-wide route would be "secondary", no route would ever be a queue, and rule 4
  could never fire. A route with no declared role is defaulted LOUDLY, so an undesigned circulation
  reports as undesigned rather than as compliant.
- **A SERVICE ROAD REACHED BY LONG SPURS IS NOT CONCEALED, IT IS THE STREET.** Three designs were
  measured. A perimeter ring reached by the shortest perpendicular puts a building in the middle of
  a 99x99 plot forty cells from any boundary, so the "concealed" road came out laid down the middle
  of a guest path for 87 cells at a stretch. Stepping the spur aside picked a different guest path
  to lie along. A rear yard per building collided with the NEIGHBOUR's join, because buildings
  packed three cells apart leave the land behind one of them under the path to the next. What ships
  is a backstage drawn LAST that yields: it grows outward from each door until it meets a public
  cell and stops there, so `service AND public = 0` is true by construction. What that costs is
  honest and reported: **31 service doors across the three lands and 13 with no yard behind them**
  - and the distribution says where the problem actually is. The Frontier has 3 of 11 and the
  Hollow 2 of 10; the Midway has **8 of 10**, because its whole west edge is the admission
  sequence - Box Office, Entry Queue, Turnstiles, Arrival Court - pinned against the boundary with
  nothing behind it. That is a siting problem with a name, which is the point of measuring it.
- **RESERVING LAND FOR THE BACKSTAGE COST MORE THAN IT BOUGHT.** An eight-cell band on all four
  sides of a plot already ten columns short for the transit corridor cost the Carousel and the
  Terrace their sites outright and pushed the Big Wheel through the Arrival Court. Reverted: the
  guest network takes precedence and the backstage takes what is left.
- **A MODULE THAT SPANS BANDS IS A CONNECTOR, NOT A VIOLATION.** The first vertical gate checked
  every band a module touched and failed the Mine Head for reaching the hidden core - which is the
  entire point of a headframe - and the Haunted Manor for being three storeys tall. The masterplan
  forbids "detached towers or caves at every altitude": a module sited WHOLLY in a band whose
  function it does not answer. The function test is against the band a module mostly stands in.
- **A BOUNDING BOX IS NOT A BUILDING.** The Big Wheel is 19 x 85 x 77 and mostly the air a wheel
  turns in; counted as its box it filled 22% of the upper band alone and failed a ceiling meant to
  catch a wall of towers. Occupancy reads a module's real block count where there is one - and
  where there is not, the estimate WARNS rather than failing, because a bounding box may not block
  a plan for the shape of a wheel.
- **A GATE THAT CANNOT BE MEASURED HERE REPORTS THAT, AND DOES NOT PASS QUIETLY.** `mechanics`,
  `safety`, `night` and `visual` need evidence produced elsewhere; all four BLOCK until it arrives.
  A gate that grades an unmeasured thing as compliant converts an unknown into a false assurance,
  which is worse than having no gate.

### THE ONE THAT MATTERS MOST: A PLAN VIEW SAYS AN UNDERGROUND RIDE IS ON THE STREET

It is on the street's SHADOW. Every attachment, connectivity and capacity check in this project was
two-dimensional, which was harmless while every module sat on the build plane and became wrong the
moment one did not.

**And the moment came from the masterplan's own arithmetic.** Measured, the Frontier's declared
program is 6,709 cells of module footprint against 8,811 of owned land - 76% before a single street
is drawn - and a land with a 5-wide spine, 3-wide frontage walks and a service road cannot pack
much past 60%. Every reordering simply changed WHICH module was squeezed out; the Saloon and the
Gold Sluice took turns reporting NO SITE. Section 6 already answers it: the mine journey belongs
under the town. The Mine Cart Escape now stands 24 courses down in the hidden core, directly under
the Mine Head that is its entrance, and the town fits.

**ONE MODULE LEAVING THE PLANE EXPOSED EVERY REMAINING TWO-DIMENSIONAL ASSUMPTION IN THE PARK**,
and that is the most useful thing this session found. Each was correct while everything stood on
one course and silently wrong the moment one thing did not:

- **THE FLOOR'S LIFT HAS TO REACH THE COLLISION TEST.** `_clear` has always compared boxes in three
  dimensions and the lift was applied afterwards, so a ride 24 courses down still claimed its
  surface footprint and moving the mine underground bought the town exactly nothing.
- **AN ANCHOR STANDS ON THE COURSE ITS OWN MODULE STANDS ON**, not on the land's plane. Pinned to
  the plane, the mine's queue mouth was reported at street level and the route gate saw a ride
  nobody could reach as perfectly served.
- **A MODULE ON ANOTHER BAND GETS ITS OWN LEVEL'S CIRCULATION.** Its frontage walks carry a Y, one
  `shaft` route joins them to the street, and `pathgraph.levels` is what lets the attachment check
  tell a street from its shadow. One course is a step and needs nothing declared; more than that
  needs a stair, which is section 4's rule.
- **THE SHAFT HEAD HAS TO BE ON THE STREET.** A shaft stands in its module's own column, which on
  the surface is not anywhere the town paved - so the network came out in two pieces, correctly: a
  guest could reach the landing only by already being on it.
- **A ROUTE MAY CARRY ITS OWN COURSE.** `park._paths` drew every route at the paths module's plane,
  so the mine's landing was paved on top of the town.
- **A TURN MAY NOT FLATTEN A MODULE ONTO THE BUILD PLANE.** Both orientation passes re-placed a
  module at `plane`, which is right for everything standing on the ground and silently undid the
  floor lift for anything that is not: the mine ride was sited 24 courses down, turned to address
  its street, and came back up into the town it had just been moved out of.
- **AN OVERLAP TEST IS A BOX TEST, AND A BOX HAS THREE DIMENSIONS.** Both turn passes and the
  plan-view test called the Mine Head standing over the Mine Cart Escape a collision - which is
  what a headframe IS - and refused to turn the headframe away from the railway because of it.
- **BEING OFF THE LAND EXCUSES A HANDOFF AND NOTHING ELSE.** Applied to every anchor, `off_land`
  also excused the Mine Head presenting its shopfront to the transit corridor: the front was off
  the owned land, so the route gate stopped asking for a path to it and reported a building nobody
  can enter as served.
- **A TURN MOVES EVERY ANCHOR, NOT ONLY THE FRONT.** The repair pass tests one interface of eight;
  turned, a ride at the eastern boundary put its emergency exit two cells into the transit
  corridor - a fire exit onto a railway, which no facing fixes. Siting refuses such a spot now
  (`_anchors_on_land`), and so do both turn passes.
- **A CONNECTIVITY FLOOD OVER EVERY CELL DRAWN FLOODS THE BACKSTAGE.** A concealed service road
  that does not join the street is the backstage WORKING; 51 cells of the Reliquary's yard read as
  a broken street until the flood was scoped to the public network.
- **THE SURFACE ACCESS CHECK ANSWERS ABOUT THE SURFACE.** `park_contracts.inaccessible` compares
  one access point against one course; `interfaces.unattached` is the authority for anything on
  another band, and the two disagreeing about one module is the drift a shared entry point exists
  to prevent.

### DISTRICTS, AND THE COLLISION THAT PROVED THEY WORKED

PARK_HOLLOW.md: *"Keep five major experiences; stop treating eleven small modules as equal
attractions."* The reason the Hollow read as eleven machines on paving is that the packer sorts by
CONTACT with anything already there, which hugs whichever neighbour is nearest and scatters a
market across the plot. A module now names a `district`, the biggest member decides where the
district starts, and **the rest of the district is sited immediately behind it** - sorted by area
alone the Assay Office was the Frontier's third module and the Prize Office its fourteenth, and the
pair came out 78 cells apart on a 99-cell plot.

Grouping them made the Reliquary discharge into the Vault's queue - which is not a regression, it
is the arrangement problem becoming visible, because a district is precisely a set of buildings
standing close together. So rule 4 became a SITING constraint rather than a report. **Its first
version was vacuous and the count said so**: interfaces are annotated after siting, so a
freshly-annotated candidate was compared against modules carrying no anchors at all - nineteen
checks, zero refusals, and the collision still there. Both sides are annotated now.

**A turn may not create the collision siting refused.** The orientation pass flips a building and
moves every anchor with it, so the Reliquary was sited clear, turned to address its street, and
came to rest one cell off the Vault's queue. Both turn passes check it - through `_sitable`, the
same predicate siting uses, because three call sites with two checks each is how the third one
gets forgotten - and a building that keeps its back to the street now RECORDS why
(`turn_declined`), since declining silently is how a trade becomes a defect.

**AND GROUPING IS A PREFERENCE, WHICH IS ALSO MEASURED.** Four of the seven districts still span
more than 60 cells - the Crypt Market 68, Boomtown Main Street 75 - because a plot already holding
a 47x47 coaster has no contiguous land left for a three-building frontage. Each one says so in the
plan's own notes rather than claiming a street it does not have; the fix is a smaller program or a
bigger plot, and both are decisions rather than bugs.

### WHAT THE THREE LANDS SAY NOW

All three pass every gate that can be derived offline. What is still open is stated rather than
hidden:

| | |
|---|---|
| `mechanics` `safety` `night` `visual` | no evidence supplied on any land - they BLOCK, by design |
| 10 of 31 service doors | no backstage behind them. The fix is siting room, not path drawing |
| Midway | still one band: the masterplan's own answer for it is a machine gallery under the food court, and it is not built |
| Frontier, Hollow | one shaft each - the Mine Cart Escape 24 courses under its headframe, the Ossuary 20 under its market. Both lands' programs needed 65-76% of their plot as raw footprint before a street was drawn, and going down is what made them fit |
| the crossroads | the Midway's and the Frontier's own crossing is boxed in - by the Arrival Court on one, by the coaster, the headframe and the range on the other - so neither has a sign within reach of it. `anchor: junction` takes the nearest free bay and on those two plots that is not near enough. The warning is truthful and the fix is a smaller program at the centre, not a wider threshold |

The masterplan's section 6 and 7 journeys - the mine's ore chamber, flooded works and crystal
reveal, the Hollow's catacombs, train show chambers and founder's vault - are the largest remaining
piece of work and they are generator work, not planner work.

### Finalised, after the first pass (2026-09-01)

Three things were left open and all three are closed.

**THE LAYER SLICE IS PER BAND NOW.** `_which` put everything below `floor_y` into "Machines",
which was right while the only thing under a park's floor WAS its wiring - and a vertical park has
ROOMS down there. Sliced against one global floor the Frontier's mine ride came out as the
mechanism's basement: a printer would have been handed a Machines layer containing a station, its
walls and its track. Each cell is judged against the floor of the MODULE it came from, which is
the plan's floor shifted by that module's lift, recorded at the moment the cell is claimed because
first-writer-wins runs across modules and the loser's floor is not the one the cell was built to.
The plane comes off the plaza - the one module that IS the ground - because deriving it from the
modules' average or their lowest cell would move it every time a ride went underground, which is
the very thing it has to measure the lift against.

**A SERVICE DOOR ON A FACE THAT IS OFF THE LAND CAN NEVER HAVE A YARD.** The interface layout puts
the backstage on the REAR by construction, which is right until the rear is the plot boundary: the
Midway's whole admission sequence is pinned to its west edge facing east, so five of its rear doors
opened onto the neighbour's ground and no backstage road could legally reach them. A service door
now takes the first flank that is actually on the land - and a SHOPFRONT never does, which is the
asymmetry that matters: where a customer entrance faces is a design decision, and silently turning
it to suit the plot is how a building ends up addressing nothing. 13 yardless doors to 10; the rest
are the packing problem, and their fix is siting room.

**AND THE WAYFINDING GATE CARRIED THE SAME TWO-DIMENSIONAL BUG IT WAS WRITTEN TO CATCH.**
`_junctions` unpacked a route endpoint as `point[0], point[1]`, which for a three-element endpoint
is x and **Y** - so the moment a land grew an underground landing, every junction it reported was a
coordinate pair that exists nowhere, no sign was ever within reach of one, and both side lands
warned that all of their decision points were unserved. It also missed the one junction that
matters: the point where the two main spines CROSS is a decision point by construction and is an
endpoint of nothing, being the middle of both.

`anchor: junction` was the third attempt at the siting. `anchor: centre` claims its box in the
FIRST siting group, so a 9x9 fingerpost took the middle of the Hollow before its rides were placed
and cost it the Ghost Train and the Plummet. A preference keeps the module in its ordinary place in
the size order and takes the free bay nearest the crossing, so on a full plot it degrades to where
it used to be rather than starving anything.

**The three plans are re-planned and approved**, and the pre-overhaul ones are kept beside them as
`out/plans/park_*.json.pre-overhaul`. What changed in them: the Hollow lost its nine per-facade
nameplates and gained two decision-point fingerposts and a Mourning Parlour; the Frontier's Pay
Window became the Prize Office on Main Street and the Runaway Mine became the Mine Cart Escape,
underground. All three site fully - no NO SITE anywhere - and pass every gate that can be derived
offline.

### The four gates that are about the BUILT world (2026-09-01)

`gates.py` names ten and answers six from the plan alone. `mechanics`, `safety`, `night` and
`visual` are about blocks, so they blocked - by design, and correctly, because a gate that grades
an unmeasured thing as compliant converts an unknown into a false assurance. `mcbuild/evidence.py`
is the somebody who measures:

    python -m mcbuild parkevidence <plan>      measure and record it on the plan
    python -m mcbuild parkgate <plan>          ...and now ten gates have an answer

**IT MEASURES THE GENERATED ARTIFACTS, NOT THE PLAN**, and a land whose modules do not exist gets
a failure that says so. Four things it found, each of which was a real defect rather than a
tooling gap:

- **THE BUILD PLANE IS THE COURSE YOU STAND ON, NOT THE COURSE UNDER YOUR FEET.**
  `tools/parkship.py` has said so all along - "the FLOOR is the course the floor blocks occupy,
  one under it" - and `interfaces` put every anchor one course higher. That was consistent with
  everything which only ever compared anchors to other anchors, and wrong the moment anything
  compared one to a BLOCK: the safety pass read a guest's feet as their head and reported 671
  route cells across the three lands as obstructed by their own paving, and every ride's boarding
  point as a landing over a hole.
- **PAVING UNDER A BUILDING IS NOT A ROUTE A GUEST WALKS.** The street is laid even under a
  building on purpose - skipping obstacle cells can SPLIT a route - and the building wins the cell
  in the slice. Measured without that exclusion, 834 route cells read as obstructed by the very
  walls they run beneath.
- **A SHAFT IS A CONTRACT AND SOMETHING HAS TO HONOUR IT.** `circulation` declares a vertical
  connection wherever a module stands off the plane, and nothing built one: the safety pass walked
  the Frontier's shaft course by course and found twelve cells of solid rock between the town and
  the mine landing it was supposed to reach. `gen/stairwell.py` already did exactly that job, so
  it is a siting rather than a new generator - and a stair is typed as CIRCULATION, because typed
  by the fallback it came out a shop, owed a shopfront and a service counter, and stood in a band
  that admits neither.
- **ONLY THE SPINES WERE LIT.** 2,830 public route cells stood at block light 0, which is a mob on
  a guest path. The masterplan asks for "warm reliable lighting" on public paths and
  "high-legibility lighting" at ride entries and exits, so an exit and a queue are lit tighter than
  a street and a service road is never lit, because it is meant to be missed.

**AND `visual` STILL BLOCKS UNTIL A HUMAN LOOKS.** The packet is rendered here - seven views, each
standing AT the anchor it is named after rather than at a camera somebody chose - and the gate
returns `ok=False` with the reason until a verdict is written to `evidence.visual.verdict`. This
project has the scar: an animal scored GOOD on every measured dimension and was a spotted table.
A packet is evidence that somebody CAN look; it is not evidence that they did.

### The deep journeys: `gen/undercroft.py`

Sections 6 and 7 name two routes, and they are the same SHAPE - a descent, chambers that each do
one thing, a reveal, a reward, and a return. So it is ONE generator: two land specs, two palettes
and two stories over identical geometry, because written twice it would drift twice.

    mine    ore chamber -> broken trestle over a cavern -> flooded works -> crystal reveal
    crypt   catacombs -> ossuary branch -> train chamber -> drowned crypt -> founder's vault

They sit in the DEEP ADVENTURE band, under the hidden core rather than in it - the Undermine at
B-24 is the station a guest boards at, and a station under a town and a cavern under a station are
not the same kind of place. Both lands now build across three levels.

**THE ROUTE IS WALKED, NOT MEASURED**, and that is the only check worth having: a sealed chamber
looks exactly like an open one from outside. Three things the walk found that nothing else could:

- **CLEARED HAS TO BE STICKY OR THE ROOMS BRICK UP THE CORRIDOR.** Hollowing clears by REMOVING a
  cell, which is indistinguishable from a cell nobody built - so the next chamber's shell, which
  legitimately extends a cell past its own wall, poured rock straight back into the spine it was
  supposed to open off.
- **THE FLOODED CHAMBER FLOODED THE WALKWAY.** A guest looks at the flood; they do not swim the
  journey.
- **THE LANE THROUGH A ROOM IS CLEARED LAST, AND THAT IS ONE RULE RATHER THAN SEVEN.** Every
  chamber put its own thing in the middle of its own room - the crystal mass, the vault plinth -
  and the middle of the room is where the corridor runs. Patched per chamber it would be got wrong
  again by the eighth chamber somebody writes; swept once, after the room is built, a new chamber
  type cannot forget it. A guest walks PAST the reveal: standing inside it, they cannot see it.

### And the backstage got a second look

`interfaces` places a service door on the rear face and can only move it for a reason it can see
from the module alone. Whether that face is under a guest path is not knowable until the guest
paths are drawn - so `circulation` re-faces them once the streets exist, and only ever onto a face
that is on the land AND clear of the street. 13 yardless doors of 31 became 6 of 33. The remainder
have no free flank at all, and a door nudged onto a worse face to make a count go down would be
buying quiet.

### The night pass, and the last of the dark (2026-09-01)

`gen/park._paths` puts a lamp post on the verge, falls back to the kerb, and gives up when a walk
is squeezed between two buildings - which is exactly the tightest, most enclosed street in a land
and the one a guest most wants lit. After every spacing and fallback change that could be made, 45
walkable route cells across the two side lands were still at block light 0.

`tools/park_night.py` does the last of it the way this island already lights itself: **an ochre
froglight set FLUSH into the paving**. It is the floor rather than something standing on it, so it
needs no side room at all, cannot be knocked off a walkway, and is Jack's own idiom - 39 were
scattered by hand across the lowland before any tool did it. **REACH IS ONE LESS THAN THE LIGHT**,
because a flush froglight is an opaque emitter a course down; and it is a FIXPOINT, not one pass,
because placing a light changes what is dark. Six froglights closed the Hollow over three rounds.

Four measurement bugs had to be fixed before any of those numbers meant anything, and all four are
the same shape - a check judging cells that are not a guest path:

- **376 OF THE MIDWAY'S 387 "DARK GUEST PATHS" WERE THE FLOOR OF ROOMS.** Paving is laid even under
  a building on purpose and the building wins the cell, so a route cell inside a footprint is not
  somewhere a guest stands.
- **THE KERB IS WHERE THE FURNITURE GOES.** Measured across a route's full width, a correctly lit
  avenue reads as obstructed by its own lamp posts.
- **A LAMP ON ONE STREET'S KERB CAN STAND IN THE CROSSING STREET'S WALKWAY.** Every route knows its
  own kerb; none knows that another crosses it there. 39 posts stood in a street they did not
  belong to.
- **A STEP IS NOT AN OBSTRUCTION, AND ONLY AT FOOT HEIGHT.** A stair in the course a guest's feet
  are in is something they walk up; the same block at head height is something they walk into.

### Where the park stands

**All three lands are PROMOTABLE: every one of the ten gates passes.**

| | |
|---|---|
| interface, route, capacity, band, grade, wayfinding | derived from the plan |
| mechanics, safety, night | measured off the generated blocks - 0 circuit faults, 0 loose water, 0 blocked headroom, 0 landings over air, 0 spawnable guest-path cells |
| visual | a seven-view packet per land, and a recorded verdict on each |

The lands build across three levels - surface, hidden core, deep adventure - and the two side lands
carry a real vertical journey with a stair down to it.

Standing warnings, which are honest rather than failures: 6 of 33 service doors have no backstage
behind them and no free flank to move to; the Midway's and the Frontier's own crossroads are boxed
in, so neither has a sign within reach of it; and the Midway is still one band, its machine gallery
unbuilt. Every one of those is a program decision - a smaller footprint at the centre, more room
between buildings - rather than something a pass can conjure.

**The visual verdicts, recorded** (`evidence.visual.verdict` on each plan): all three PASS at street
level and the two bright lands are MARGINAL from above, for the same reason - the packer sorts by
contact and clusters its buildings into a third of the plot while the rest is bare paving. The
Hollow is the best composed of the three. What no surface view shows is the undercrypt, 56 courses
down: **the deep journeys need a packet of their own before anybody can say they read.**

