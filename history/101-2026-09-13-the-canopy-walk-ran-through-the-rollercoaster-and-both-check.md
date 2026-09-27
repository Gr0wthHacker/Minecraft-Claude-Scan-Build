## THE CANOPY WALK RAN THROUGH THE ROLLERCOASTER, AND BOTH CHECKS MISSED IT (2026-09-13)

Jack: *"canopy and the rollercoaster intersect? audit all."* They did. **81 cells**, and five of
them stood in the two courses over live track.

    canopy x Mine Coaster   81 shared    36 spruce_log (the trestle) + 39 stone_bricks (lift hill)
    on the track             0
    in the rider clearance   5    x97532 y205-206, over rail at y204 - planks, stairs and fence
    ...and two of the walk's PIERS driven down through the ride's own trestle at x97615, x97621

### THE FIRST MEASUREMENT WAS WRONG BY 48 BLOCKS, AND IT WAS THE SIDECAR THAT LIED

Read straight off `out/Mine Coaster.scan.json` the answer came out **248 cells including a
`powered_rail` replaced by a jungle plank** - a much more alarming finding, and false.

**A LOT MODULE IS NOT PLACED AT ITS OWN SIDECAR ORIGIN.** `park_place.modules()` puts it at its
lot `(v, u)` and at the park's own build plane; only a `PF ` design in `extras()` is placed from
the origin its sidecar records. There are THREE coaster artifacts in `out/` and they are not the
same thing:

| | shape | solid | placed? |
|---|---|---|---|
| `out/Mine Coaster.litematic` | 69x94x97 | 56,635 | **no** - legacy, and its sidecar origin is 48 blocks off |
| `out/park_final/artifacts/Mine Coaster.litematic` | 56x61x101 | 31,196 | only if the `PF ` file is missing |
| `out/PF Mine Coaster.litematic` | 56x61x101 | 31,197 | **yes**, at lot (v24, u99), plane 13 |

A design's own sidecar answers *where was this generated*; only the composite answers *where does
the park put it*. Auditing a lot module against its sidecar measures a ride that is not in the
park - and it looks exactly like a real answer, because every coordinate in it is plausible.

### BOTH CHECKS THAT EXIST MISSED IT, FOR DIFFERENT REASONS

- **`finish.verify_against` AUDITS AGAINST A CAPTURE, AND A CAPTURE HOLDS ONLY WHAT IS BUILT.** The
  coaster is **62% placed** (19,342 of 31,197) and **every one of the 81 contested cells is in the
  unbuilt 38%**. The audit reported overlap 0 honestly. Third costume for the finding this file
  already records about the Prism Well's stale cut and about `park_place.clashes` itself: *a
  context that is honest about a design's geometry can be blind about what is not built yet.*
- **`park_place.clashes` ASKS THE RIGHT QUESTION AND NEVER SAW THIS DESIGN.** It compares the
  modules in the composite, and `PF Canopy Walk` is not in `EXTRAS_READY` - deliberately, because
  it has not landed. So the one check that could have caught this is the one a not-yet-shipped
  design is exempt from, which is exactly when it is cheapest to fix.

### The fix, and it is `gen/mineridge.py`'s own idiom

That generator already solved this: *"it reads the coaster's own artifact, and a cell the ride owns
is refused"*. The canopy walk does the same now, in the SAME lot frame - which is what makes
`ride_at` derivable rather than typed: the coaster's lot is (v24, u99) off the park anchor and this
lot's anchor IS the park anchor.

    ride: out/PF Mine Coaster.litematic   ride_at: [24, 99]   ride_plane: 13   ride_clear: 2

**THE RIDE'S CELLS AND THE RIDER'S CLEARANCE ARE KEPT APART AND REPORTED APART**, because they are
different faults: one is two designs contending for a cell, the other is a beam in the face of
somebody riding past at speed. `route.legal` refuses a column the ride stands in - the DECK is the
thing that cannot move cell by cell - and `_Walk.put` refuses everything else.

Three things it cost, each a rule this repo already carries:

- **THE CORRIDOR CLOSED AT ONE COLUMN.** With the ride refused, v118 has only u101-102 legal
  against a v117 whose lowest choice is u104 - and a walkway may only step one cell of u per cell
  of v. `u_slack` 9 -> **10**; swept at 10, 11, 12, 13 and 14 the route that comes out is
  IDENTICAL (u100-117, an 18-column worst span), so ten is the width the terrain and the ride
  actually ask for rather than a number picked to make an error go away.
- **A STAIRHEAD WALKS UNTIL THE ROCK STOPS IT, AND FROM v55 THE ROCK DOES NOT STOP IT.** It
  descended twenty-three courses past the coaster's western structure to the park floor - a ramp
  beside a rollercoaster rather than a way off a canopy walk - and the keep-out then cut it in two,
  leaving its foot as a 17-cell island. Swept over every v0 from 45 to 100, the westmost head whose
  whole descent is clear of the ride is **65**: seven courses down to rock at y221, ON THE RIDGE,
  which is where a walk through treetops should put you. The collision fix and the design fix turn
  out to be the same fix.
- **A PYLON IS ALL OR NOTHING, AND A CABLE RUNS THE WHOLE SPAN OR IS NOT STRUNG.** Refusing cell by
  cell holes a mast and breaks a one-wide line, and the prune then removes the fragments - which
  hides the fact that the truss is short (15 cells pruned against a bound of 12, which is the test
  that caught it). `_piers` already states the rule for the other end of the same post (*"nothing
  to stand on: take the post back out"*); this is it upward. **And the cable genuinely cannot be
  strung here**: the coaster's lift hill climbs y236 to y244 through u101-103 across this very
  span, above any mast worth building - so the masts stand, the deck passes UNDER the ride, and
  `truss_cables_declined` says so rather than leaving it to be inferred from a block count.

    826 blocks, ONE piece, 0 problems, 0 cells of the ride, 0 in the rider's clearance,
    pruned 4 of 830 against a bound of 12, 10/10 tests

`test_the_walk_takes_NOT_ONE_CELL_OF_THE_RIDE_and_nothing_a_rider_passes_through` is the tripwire,
and it derives the coaster's placed position from the config's own `ride_at`, so it cannot drift
from what the generator refuses. **Verified RED**: with the guard off and the old `v0`/`u_slack`
the design takes 81 ride cells and 5 clearance cells, exactly the fault.

### And the rest of the sweep, because "audit all" was the other half

Every design with cells in the Lost Plateau band, pairwise, against the park AS PLACED, plus every
ride's track and the two courses over it:

- **NOTHING IN THE SHIPPED PARK STANDS IN ANY TRACK OR ANY RIDER'S CLEARANCE.** The Mine Coaster,
  the Mine Cart Escape, the Carousel and `Park Rail` (1,206 rails) are all clear. The only
  intrusions anywhere are **vines** - 8 in the coaster's clearance from `PF Lost Plateau`, 8 in the
  railway's from `PF Frontier Overgrowth` - and a vine is passable, so a cart goes through it.
- **`PF Rib Walk` is the other unshipped design and it has the same blind spot**: 36 cells shared
  with `PF Park Green`, 16 with `PF Water Claim Lake` (two of them WATER), 2 with `PF Mine Ridge`.
  Small, and unaudited for the same reason - it is not in `EXTRAS_READY` either.
- Shipped contention in the band is dressing only: `PF Frontier Scatter` x `PF Park Green` 76 (41
  the same block), `PF Park Green` x `PF Water Claim Lake` 11.
- The canopy walk still shares **95 cells with `PF Lost Plateau`** - jungle leaves and vines - and
  that is LEFT, because a canopy walk passing through a canopy is the design.

**THE GENERAL RULE:** a design that crosses another design's ground must refuse that design's
ARTIFACT, not the world under it. The world is a photograph of what has been built; the artifact is
what will be. Between the two sits every module that is half-placed, which on this park is most of
them.

