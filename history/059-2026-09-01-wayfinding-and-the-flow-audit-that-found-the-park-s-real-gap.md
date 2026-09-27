## Wayfinding, and the flow audit that found the park's real gap (2026-09-01)

Jack: *"make sure that each of these areas has clear pathways, link to eachother, and clearly
demonstrate a flow"* and *"we don't want empty structures that sit there and are mostly
useless."* `mcbuild/gen/wayfinding.py` is five signage kinds - `mapboard`, `fingerpost`,
`marker`, `archway`, `noticeboard` - built on `park.py`'s own protocol. **The audit that came
with it is worth more than the signage**, because it is the first time anything in this project
asked, of the REAL SHIPPED PARK, whether a visitor can actually get from the gate to every
attraction - not the planned routes `test_park_plan.py` already proves connected, but the four
litematics on disk.

### The audit: `tools/park_flow.py`

Loads `Park_Left Complete`, `Park_Centre Complete`, `Park_Right Complete` and `Park Line` off
`out/`, builds a standable-cell graph (a cell one course above solid ground with two clear
courses over it, Y199-213 - street level 203 and the transit deck 207 both fall inside it) and
floods it from a seed just inside the Park Gate. Two models, because the gap between them IS the
finding:

    gap=0 (strict floor)   10,285 / 33,460 standable cells reached (31%)
                            frontier 262, hollow 252, midway 8,743, transit deck 1,028
    gap=1 (one jumpable
           column allowed)  26,717 / 33,460 (80%) - 36 / 36 real attraction doors, all zones

**A ONE-BLOCK GAP IS TRIVIALLY JUMPABLE IN MINECRAFT**, so 80% (not 31%) is the honest figure for
whether a visitor can actually get around - the remaining 20% at gap=1 is legitimate elevated
surface (coaster track, tower parapets, ride platforms) nobody is meant to walk to from the
ground, not a connectivity fault. Both numbers are reported because the GAP between them is real
and measured, not assumed.

### THE SEAM: two of three zones need a blind jump to reach the transit line

Measured directly at each station, and at every X column between each zone's own paving and the
transit corridor:

    x=97636..97638   every zone's own plaza floor, unbroken, y=203
    x=97639           frontier: EMPTY.  midway: y=203 (paved through).  hollow: EMPTY.
    x=97640+          the transit station's stair/landing pad begins

**Midway's own seam is fully paved - no gap at all.** Frontier and hollow both have a genuine
one-block-wide unfloored column at X=97639, confirmed empty not just at the station's own centre
(z=80433 for frontier, z=80776 for hollow) but across the whole run either side of it. Anyone
short-hopping it lands fine; anyone who does not clear it falls into open void with no floor
below for a very long way. It is jumpable, not a hard blocker - the gap=1 numbers above prove
that - but it is an unmarked, asymmetric hazard, and it is a design fact this audit measured
rather than something wayfinding signage can fix on its own. **Recommended: either pave X=97639
at both stations to match midway, or mark both sides of the jump plainly.** `park_line.yaml`'s
own comments already call this out as accepted ("one cell from the zone's own paving") - what
was missing was the measurement of how large a hazard that "one cell" actually is, and that it
is not symmetric across the three zones.

### THE BIGGER PROBLEM: the zone arches point at open void, and always have

`gen/transit.py`'s own docstring says the centre zone's Frontier Arch and Hollow Arch "lead to
nothing at all" - written before the transit line existed, as the reason the line had to be
built. **It is still true after the line was built**, because the line's corridor runs down the
EAST edge of every plot while the arches sit on the NORTH and SOUTH edges - two different edges
entirely, with no relationship between them. The voxel audit confirms it independently:
`Frontier Arch`, `Hollow Arch`, `Frontier Gate` and `Hollow Gate` all measure as literal dead
ends (open void immediately past their threshold) once their own door point is checked rather
than a point beyond it. A visitor reading "FRONTIER" over an arch and walking through it reaches
the edge of the island and stops; the real way to Frontier is the Midway Central transit station,
on a different wall of the same zone, unsignposted from anywhere near the arch. **This is the
single biggest legibility problem in the park**, and it predates this session - wayfinding
signage can only paper over it (a fingerpost beside each arch redirecting to the real station);
fixing it properly is retiring or relabelling the arches, which is Jack's call, not a silent one.

### How far the walk actually is

Unweighted BFS hop-count (gap=1) from the Park Gate to every real attraction door:

    436  Fortune Wheel      hollow
    416  The Graveyard      hollow
    406  The Plummet        hollow
    405  Prospect Row       frontier
    380  Hollow Gate        hollow
    379  Dead Tree          hollow
    379  Shooting Gallery   frontier

**The furthest attraction is ~436 blocks of walking from the gate** - which is most of a trip
across all three islands and the whole skyway. That is an argument for the transit CART, not
just the walkway beside it: the line exists so a visitor need not walk this, and nothing in the
park currently tells a visitor that. A fingerpost at the entrance naming the ride time saved by
boarding would do more for "clear pathways" than any amount of paving.

### The five kinds, measured

`planner.measured_footprint` against representative params (X x Y x Z, offset from `at`):

    mapboard      3 x 9 x 11   offset (-1,-1,-9)    a coloured 3-land layout, "you are here" lit
    fingerpost    6 x 9 x 9    offset (-1,-1,-4)    a post, 2-4 arms, up to 4 destinations
    marker        3 x 5 x 3    offset (-1,-1,-1)    a small nameplate beside one attraction
    archway       7 x 7 x 4    offset (-5,-1,-2)    a threshold naming what is on the other side
    noticeboard   3 x 7 x 7    offset (-1,-1,-5)    park rules/hours, header + up to 3 body signs

**The destination roster is read live, not hand-copied.** `wayfinding.known_destinations()`
pulls every module name straight out of `planner.THEMES`, the three zone names, and the transit
line's own station titles off `configs/park_line.yaml` - so a fingerpost, marker or archway
pointing at a name that does not exist RAISES at build time rather than shipping a sign to
nowhere, and a module renamed upstream fails a wayfinding build immediately instead of in game.
`fingerpost` additionally records, per arm, that the sign's `facing` equals the direction the arm
was built along - `tests/test_wayfinding.py::test_every_arms_direction_matches_its_own_signs_facing`
pins it so a placard can never point one way while naming a destination in another.

### Where these should go - not wired into any config, by design

Nothing here touches `mcbuild/planner.py` or any zone's config; several sessions are already
editing that file. What follows is the sites this audit's own numbers point at.

**Every zone, at its hub crossing** (`park paths`'s own centre - frontier 97594/80400, midway
97594/80600, hollow 97594/80800): one `fingerpost`, 3-4 arms. Midway's should carry an arm toward
**MIDWAY CENTRAL**, not toward the Frontier/Hollow arches - the fingerpost is the honest signpost
the arches cannot be until the arch/corridor mismatch above is resolved.

**Just inside the Park Gate** (midway, west edge): one `noticeboard` (rules/hours) and one
`mapboard` (`zone: midway`) - the first two things a visitor should see, in that order, before
the first hub decision.

**At each transit station's platform**: a `marker` naming the station, reinforcing the
departure board `transit.py` already builds - useful from a distance the board is not read at.

**At both sides of the frontier and hollow jump** (X=97638 and X=97640, at z~80433 and z~80776):
a `marker` or the noticeboard's own "MIND THE GAP" idiom, until the seam itself is resolved.

**Beside Frontier Arch, Hollow Arch, Frontier Gate and Hollow Gate**: a `fingerpost` or `marker`
redirecting to the real transit station - the one piece of signage that is not optional, because
without it these four thresholds actively mislead rather than merely doing nothing.

**One `archway` per zone**, at the point each zone's own plaza floor meets the transit corridor
(roughly X=97636-97638, at the zone's own hub Z) - "ENTERING THE SKYWAY," the one place in the
whole audit where two different designs' floors actually meet and a visitor needs telling they
have crossed from one to the other.

### What this pass did not do, stated rather than hidden

- **Nothing is placed in any config.** `emit`/`plan --approve` never ran on this; the sites above
  are coordinates and counts for wiring in, not a shipped design.
- **The flood model is a heuristic, not the mod's real `Nav`.** It has no corner-cutting rule, no
  fluid check, no `standoff`/`escape` logic - it is deliberately the simplest model that could
  answer "does a floor connect these two points," calibrated against the fact this project has
  learned twice already: vine and grass are not footing, and a chunk with nothing in it is not
  evidence of a hole. `Y_BAND` and the gap-1 rule are stated in `tools/park_flow.py`'s own
  docstring rather than assumed.
- **`known_destinations()` depends on `configs/park_line.yaml` existing on disk** for the station
  names half of its roster; it degrades to an empty set rather than crashing if that file is
  missing, and `tests/test_wayfinding.py::test_a_transit_station_name_is_accepted_as_a_destination`
  skips (not fails) when it is.
- **2,667 Python tests, 0 failures, 12 skipped** (`python -m pytest -q`), the 12 pre-dating this
  session. `tests/test_wayfinding.py` is 238 of the 2,667: every kind at every land and facing,
  connectivity, legality, economy, sign support, the roster, and the arm/sign-facing agreement.

