## The store hall got a room, and the court got a way in (2026-08-20)

Two jobs off the 09:16 capture. Both are small; the measuring is the part worth keeping.

### The store hall was furniture, not a room

`configs/store_hall.yaml`, `gen/storehall.py`. The banks were built and Jack had moved **76
containers** into them - and there were no walls. From outside you were looking at the backs of a
freestanding ring of chests standing on open deck.

The shell is the wall course-for-course behind the banks: the 9x9 perimeter at x-24195..-24187 /
z30022..30030, Y195-199. Measured first - **158 of 160 cells free**, 0 protected, floor already
`deepslate_bricks`. **176 blocks, 0 problems, overlap 0, all cheap-or-ok.**

- **It carries NO ceiling, deliberately.** The Deck Vault already owns Y200 over this footprint (49
  designed cells, 32 already placed). Two designs drawing one surface is exactly what
  `finish.defer_to` exists to stop, and the raw cobblestone at Y201 is *above* the vault, so it is
  not a soffit problem - it is hidden.
- **The doorway is DERIVED, and the config was wrong about it.** `door: west, door_width: 3` asks
  for three cells; the world has **one** (z30026), because Jack filled the other two with chests
  when he moved in. Walling to the config would have bricked up the only way in and put a doorway
  into the back of a chest. It is now the INTERSECTION of "where a door was asked for" and "where
  the banks are really open" - and that intersection matters both ways, because
  "wherever the banks are open" alone turns **every cell a fixture happened to block into a second
  hole in the wall**. A gap in the banks is not a door. `tests/test_storehall_shell.py` pins it.
- Bank CORNERS carry no chest (a corner chest faces two ways and can face only one), so they are
  gaps by construction. Filled solid - four holes become four piers.
- Plinth and cornice are `deepslate_bricks`, field is `stone_bricks` weathered per CELL. Hashed on
  the course instead, a course comes out all one material and the wall is horizontal stripes - the
  deck soffit shipped that once.

### The sky-well court had no way in: `gen/rimstair.py`, `configs/court_stair.yaml`

**72 blocks, 22 dig cells, one component, 0 problems, overlap 0, all cheap.**

Jack picked the side and asked for it to be audited. His instinct was right; the reason I first gave
for it was **wrong, and the error is worth keeping**. I claimed a surface walk from the island centre
could not reach the owl lobe at all. Re-measured with a proper walk - every standable surface in a
column, not just the topmost; slabs and stairs as half-steps; climb 1.25 - the owl lobe IS reachable,
altar included. The first model took ONE node per column over Y199-206 and stepped at most 1, so it
could not see a route that changes level or uses a slab, and it reported a 4-5 block scramble as no
route. **A reachability number means nothing without the movement model stated beside it** - the same
site read 1,268 cells in 49 components on a fixed course, 36 steps allowing 4-block falls, and 248 on
a true walk. What actually justifies the stair is the DISTANCE, which was measured properly.

**Measured with a TRUE walk** - step down at most 1, climb at most 1.25, so no falling and every
route reversible:

| | before | after |
|---|---|---|
| island centre -> court foot | 248 | **46** |
| -> court, mid | 247 | **51** |
| -> court, far NW | 258 | **56** |
| -> court, south | 43 | 43 (already reachable along the deck) |
| court -> plate ledge (getting OUT) | 108 | **10** |

**Do not trust a reachability number without stating the movement model.** The same site measured
1,268 standable cells in 49 components on a FIXED course (no vertical movement at all), 36 steps
when 4-block FALLS are allowed - that route jumps down the tree trunk, 204 -> 200 -> 196, taking the
damage - and 248 on a true walk. Three different answers to "can you get there", all correct for
what they asked. The fixed-course version is what first said the court was orphaned, and it was
overstating the case.

Five things the build cost, each of which produced a clean audit and a wrong result:

- **The rim is not where the surface scan says it is.** A column scan reads the edge at Y201 at
  x-24222 - but that Y201 cell is a **vine**, hanging in open air. The rock stops at x-24221. Worse,
  `Ctx.name_at` returns the vine BY NAME, so the standard "is this cell empty" test written as
  `name not in AIRY` reads the curtain as footing: every stringer stopped at the top of the cliff
  and the flight came out as twelve floating treads, with the audit reporting 0 problems. There is a
  `PASSABLE` set now. Same shape as the `Canvas.get` returns -1 bug.
- **The flight was ONE-WAY and nothing but a walk test could see it.** The rim ledge stands at
  **202.0** and the land bridge behind it at 203.0, so a top tread at Y201 tops out at 201.5 - a
  1.5 step. A player climbs **1.25**. You could get down and not back up. `y_top: 202` fixes it;
  both approaches are now a half step. **Audit clean, geometry legal, build unusable.**
- **A two-wide flight in open air is impossible here** and the reason is the pool: the court's water
  reaches x-24223 at z30017-30018 and x-24225 at z30015-30017, and **x-24222 is the only column free
  of it across the whole run**. Hence one lane cut into the rim rock at x-24221 instead. The
  stringer fills DOWN until it meets something real - ice and water included, which are protected -
  so it never drives a pier through the pond.
- **The tread cell is itself a dig.** Listing only the courses above a tread says the flight is
  clear while the stair is still inside the cliff.
- **Facing comes from the geometry.** The flight ascends toward +Z, so every tread is `facing=south,
  half=bottom` - the rule pinned in `test_stairhead.py`. Our renderer draws both directions
  identically, so this is asserted, never eyeballed.

Site choice: z30013-30019 has **six consecutive rows of Y201 rim** against the south lobe's three
irregular ones (Y200/195/195) boxed in by void at z30029. It sits immediately south of the land
bridge - the crossing you take walking from the farm toward the owl - so the head is on the route
and you descend facing the owl lobe. The south lobe is where the farm-to-owl line literally crosses,
which is what Jack described, and it is the worse edge; he took the north lobe on the numbers.

