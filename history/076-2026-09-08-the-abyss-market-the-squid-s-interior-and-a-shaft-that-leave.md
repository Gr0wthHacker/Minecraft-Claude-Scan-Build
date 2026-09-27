## The Abyss Market: the squid's interior, and a shaft that leaves the parkour alone (2026-09-08)

Jack: *"the squid is so massive and since its hollow we can technically design the interior ... make
it a place that players want to go to (and maybe buy things from a shop)."* Then, on the two
questions that decide the work: **a deep market in a derelict**, and **the shop is signage pointing
at the server's own `/shops`**.

`configs/abyss_market.yaml`, `mcbuild/gen/abyssmarket.py`, `tests/test_abyss_market.py` (13).
**3,631 blocks, overlap 0, 0 placement problems in context, 0 leaks, all cheap-or-ok, 36 dig cells.**

### THE CAVITY WAS A SIDE EFFECT AND IT IS THE BIGGEST INTERIOR ON THE ISLAND

`finish.hollow` carved the animal at `shell: 2` and the config recorded the trade as *"66,000
blocks nobody would ever have seen"*. Measured off the SHIPPED artifact rather than re-derived from
`squid.SQUID` - the animal that is placed is the one in `out/`, and a fit-out computed from the
parameters is a fit-out for a different animal the day anybody re-tunes one:

    ONE connected sealed void of 54,994 cells, 250 blocks long        Z80494 -> Z80743
    the floor rises                                                   Y104  -> Y145
    11-15 wide at head height, 17-21 higher, 14-20 courses tall, on the axis X97600
    a hard pinch at Z80674                                            see THE GULLET below
    plus TWO sealed 107-cell pods at Y172-182                         one inside each EYE

### THE ENTRANCE IS THE MEASUREMENT, AND THE KEEP-OUT IS UNTOUCHED

The squid's own config exists around one safety rule - nothing may enter r56 of the Prism Well's
fall column, because a surface in a column a runner falls eighty-six courses down does not save
one, it strands one. So the way in does not come off the parkour at all: **Prismworks' own floor
is Y202 over the animal**, and a shaft at **X97600 Z80665** is r150 from the well.

    Y202 -> 45 courses of open void -> a TWO-CELL shell -> the cavity at Y155

It lands on the animal's own mirror axis at the COLLAR, where the mantle meets the head, so the
arrival is a JUNCTION with somewhere to go in both directions rather than the end of a corridor.

**Two better-scoring columns were rejected and both rejections are the finding.**

- **X97600 Z80704 is a DRAIN.** Two cells of shell, 42 courses, and 336 water cells within 22x22
  with the surface at Y202 - it is under a Prismworks pond. Cutting it drops that pond forty-two
  courses into a sealed animal, and this repo has drained 199,959 cells to Y-1908 once already
  doing something less obviously dangerous. The search rejects any column within five of standing
  water, and `test_the_shaft_is_DRY` re-derives it.
- **X97583 Z80739 is a CHIMNEY.** Two cells of shell, twenty-nine courses, and a cavity ceiling at
  Y171 that looks perfect on every number. That cavity is a **TWO-WIDE VERTICAL SLOT** - the inside
  of an arm base, a hollow tube running up into the crown - and a visitor dropped into it lands
  somewhere they cannot get out of. **A LANDING IS CHECKED FOR ROOM, NEVER FOR BEING CAVITY**
  (>=100 cavity cells in a 7x7x5 box), and that check is the whole difference between the two.

### THE GULLET IS A DOORWAY EIGHT COURSES UP, AND A FLOOR-WIDTH PROFILE CALLS IT A WALL

At Z80674 the cavity reads width **0** at floor+1, +3 and +5, which is what a wall looks like in
every profile this design was planned against. It is not a wall: it is a thirteen-wide oval
floating at Y142-154 with the mantle's floor at Y136 underneath it. It is the oesophagus, the only
way through is UP, and a walk laid on the floor simply stops there with nothing to say why.

### WHAT IS IN IT, AND WHY EVERY ROOM HAS A VERB

Jack has thrown work out of this park three times for the same reason - *"we don't want empty
structures that sit there and are mostly useless"*.

| | Z | |
|---|---|---|
| THE COLLAR | 80658-80672 | where you land; a board naming both ways |
| THE GULLET | 80668-80684 | the throat stair into the head |
| THE BAZAAR | 80684-80718 | **eight stalls, all signed.** The shop |
| THE ARCADE | 80572-80658 | 86 blocks of descending gallery, lay-bys, distance signs |
| THE SOUNDING HALL | 80518-80572 | the fin band, the widest room, and a **BELL** |
| THE TAIL | 80500-80518 | the deepest cell you can stand in, marked and left raw |

**The shop holds nothing.** A counter, a back board and the server's own shop command - no
container anywhere, asserted, because a barrel standing empty in a public build reads as a shop
somebody has already looted and a chest anyone can reach is a chest anyone can empty.

### NOT ONE CELL OF THE ANIMAL IS TAKEN, AND THAT IS STRUCTURAL

Every placement goes through one refusal that drops any cell the squid's artifact owns and counts
it (272 refusals - so the guard is not decorative). A fit-out hanging inside another design cannot
be checked for overlap afterwards and then patched: the two fight cell by cell in game and the
loser is whoever places second. The squid can be regenerated under this.

**The dig is the mouth and nothing else** - 3x3, two courses of Prismworks paving and two of the
animal's skin, thirty-six cells, asserted. It is also the one place a cell is both dug and built,
and that is not a clash: a ladder needs a rung in every course of a climb, `rimstair` settled the
same thing on a flight cut into a cliff (*"the tread cell is itself a dig"*), and the boxes are
declared so the context audit sees them as what they will be when the printer arrives, which is air.

### Eight defects, and every one shipped a clean audit

- **`_W.sign` DESCRIBED THE SUPPORT CHECK IN ITS DOCSTRING AND DID NOT MAKE IT.** Two signs shipped
  floating in open air, which the game refuses to place, so the line is lost with nothing to say
  so. Writing the check dropped the count 14 -> 2 and told me where the other twelve wanted to be:
  **a docstring is not a guard**, and the drop is the check working.
- **A RAW CAVITY SPAN IS THE WRONG MEASUREMENT AND THE FIN BAND PROVES IT.** At Z80534 the void is
  forty-five cells across, because the fins are hollow too and their inside is a wedge closing to
  nothing at the wings. Deck laid to that span put isolated cells where the ceiling is one course
  over the floor. `_room_span` is the contiguous run with real HEADROOM, and a floor you cannot
  stand on is not a floor.
- **THE LADDER WAS ASSEMBLED FROM TWO PASSES THAT EACH STOPPED AT THEIR OWN END**, so the two
  courses of skin between them - the dig - had no rung at all. A climb with a two-block gap in the
  middle is not a climb, and **a ladder that stops looks exactly like a ladder that starts**.
- **...AND THE REASON IT COULD NOT BE FIXED WAS THE ORDER OF TWO LINES.** `free()` checked the
  animal BEFORE the dig exemption, so the exemption reached the park's paving and never the
  squid's own skin - the only cells of the animal this design is allowed to touch refused every
  rung. The guard that raised on the gap is what found it.
- **THE SLAB RING REPAINTED THE LADDER'S OWN SPINE** every fourth course, hanging four rungs on
  half a block in the only way down.
- **THE BELL WAS FIVE AND A HALF BLOCKS OVER THE DAIS AGAINST A REACH OF FOUR AND A HALF.** Hung
  from the cavity's own ceiling it is a picture of a bell: the one verb in the biggest room, and
  every offline check passed it, because a bell nobody can touch is a legal, supported, affordable,
  correctly-stated bell. It hangs from its own FRAME now, which is also what makes it read as one.
- **THE STALL BOARDS WERE ONE CELL IN FROM THE WALL** - the span is the last CAVITY cell, so the
  wall is one further out - and both flanks shipped as seventeen-cell clusters floating clear of
  what they are bolted to.
- **AND THE STALL SIGNS FACED THE WALL.** `face = "east" if side > 0` is the obvious way round and
  it is backwards: the aisle is toward the AXIS.

### LIGHT IS PROPAGATED, AND THE SCOPE IS THE DECK

A lamp every six courses is a rhythm and was not an answer: propagated over the finished composite,
**912 of 4,064 walkable cells came out at block light 3 or under, 622 of them in the room a visitor
is meant to shop in.** A sealed cavity under a park with no sky light at any hour has no dim
corners, only invisible ones.

`_relight` is `Island Night`'s fixpoint - propagate, take every walkable cell under the threshold,
set a froglight INTO the floor at a spread of them, propagate again - and it reports the remainder
rather than stopping on a round cap, because **a solver that returns only what it placed says a
floor is lit when it is not.** 144 lamps, `dark_left: 0`.

**Two things about the scope.** The animal's own 450 skin froglights are IN the model, because the
shell is two thick and some of that genuinely reaches the inside - modelling the cavity as unlit
puts lamps where the animal has already lit itself. And what is lit is the DECK THIS DESIGN LAID,
not the whole cavity: the raw trough either side of the walkway stays dark on purpose, and Jack's
own note that mobs do not spawn here - which is why the squid was hollowed at all - is what makes
that atmosphere rather than a hazard.

### THE RIBS ARE WHAT TURNED A FLOOR INTO A ROOM

The Sounding Hall came out a flat plank plain with a small bell on it and the arcade a bare
corridor - a hundred blocks of floor with a lamp in it, which is the complaint this park has been
rebuilt around three times. **A room this shape cannot be given mass by furniture, because the mass
is the BODY.** A rib is traced on the cavity's REAL boundary at that station - up each flank and
over the crown - so it is a rib of this animal here and every one differs by construction. 508
cells, and it is the single biggest change in how the interior reads.

**And the shaft was a barber pole.** Four-course bands of copper against deepslate is the largest
hue contrast in the palette at the largest pitch. One dark course in four is a string course, which
is what every other tower in this park draws with.

### The palette, measured ACROSS families

    polished_blackstone_bricks  45 . deepslate_bricks 71 . spruce_planks 89
    cut_copper                 123 . smooth_stone    159 . ochre_froglight 232

Steps of 26, 18, 34, 36, 73. CLAUDE.md records four separate times that this economy has no value
contrast and all four searched INSIDE one family, where a ladder cannot exist by construction. The
rung that matters is the structure against the FLESH: `mangrove_planks` is 67 and `red_wool` 65, so
deepslate at 71 vanishes into the walls it is bolted to and copper at 123 does not - and it is the
only warm hue in a cold room. It is also Prismworks' own material, from the land directly overhead,
which is what makes the fiction read.

**AND IT IS UNWAXED, ON JACK'S WORD, SO IT AGES - WHICH THE PALETTE SURVIVES.** That was the thing
to check before agreeing rather than after: a waxed block is pinned to its stage for ever, and the
whole interior was measured against fresh copper.

    cut_copper           123  (191,107,81)     fresh: 56 clear of the flesh
    exposed_cut_copper   128  (155,122,101)
    weathered_copper     140  (108,153,110)
    oxidized_cut_copper  136  ( 80,154,126)    green: 71 clear of the flesh

**The contrast RISES, 56 -> 71**, and green against red flesh is complementary where warm against
warm was not - so the design gets better on the way rather than merely tolerating the journey. It
arrives patchy, through the two middle stages, because oxidation is per-block and random, which is
what makes it read as age rather than as a repaint. A derelict going green inside a dead animal is
also the story the whole fit-out is telling.

### AND THE ECONOMY TABLE WAS WRONG ABOUT COPPER

The design briefly carried `expensive_allowance: 94` for its `copper_block` posts. Jack: *"copper is
not expensive, we can use it."*

**IT HAD NEVER BEEN MEASURED.** `copper_block` sat in `palette.EXPENSIVE_NAMES` among
`netherite_block`, `diamond_block`, `gold_block` and `emerald_block` - filed by LOOKING LIKE AN ORE
BLOCK rather than by what it costs on this server. And **the table contradicted itself in a way that
needs nobody's word to see**: every CUT form of copper was already cheap, and `cut_copper` is crafted
FROM `copper_block` - one block into FOUR cut in a stonecutter. A table that prices an input dearer
than four of its own output is wrong on its own terms.

That is **rule 12 pointed at the ECONOMY rather than at the registry**. Cheap, available and
spendable are three different axes and only the last two were ever derived from evidence; the rest
of that set has the same provenance and simply has not been challenged yet, which is what CLAUDE.md
already says about every reference table here - *suspect the tables before the code.*

**Nothing asserted anywhere broke**, which is the tell that the entry was load-bearing for nothing:
the two Prismworks tests that mention it only require copper NOT to be expensive, and
`test_prismwell` forbids expensive blocks outright. What had to change was two DOCSTRINGS stating
the wrong fact as evidence - the failure mode this file keeps recording, where a stale claim outlives
the thing it described and the next reader believes it.

### THE PROW, AND THE ANIMAL'S OWN OPEN MOUTH (2026-09-09)

Jack: *"wondering if we swap the eye balls themselves for glass e.g. black glass so interior can
see out ... theres also some gap left unused towards the mouth of the squid from the inside."* Both
observations were right; neither was right in the place he expected, and the measuring is the part
worth keeping. **3,793 blocks, overlap 0, 0 problems, 0 leaks, 15 tests.**

#### THE EYES ARE THE WRONG WINDOW, AND IT IS A MEASUREMENT NOT AN OPINION

    pod centroid  X97561 Y176 Z80755        eye centroid  X97574 Y169 Z80747
    pod cells whose outward wall contains an eye cell:  2 of 111

The eye pods sit thirteen blocks further out and eight further back than the eyes. Glazing an eye
gives that chamber nothing, and the pods still have no way in. The eye DOES back onto the main
cavity - twelve cells at X97581-84 / Y166-171, one cell of shell - but thirty courses above the
head chamber's floor: something to look at, not through.

#### AND A NINE-BY-SEVEN WINDOW IN THE FORWARD WALL IS A BLACK RECTANGLE

    71 dig cells.  57 of its 63 sightlines end on NOTHING.  0 end on a light.

The arm crown carries forty froglights and they are off to the SIDES, not in the forward cone. The
limit on the whole idea was never the glass or the wall - the cavity wall is two cells thick across
75-85% of every zone, so a window is cheap anywhere. **The limit is that there is nothing out
there**, and the only honest answer to "can we see out" is to go and measure what is in the cone.

#### THE GAP WAS REAL, WAS NOT WHERE THE VOLUME SAID, AND THE ANIMAL'S MOUTH IS OPEN

Counted as volume the unused space looked like 2,260 cells reaching to Z80745 - four times the
prow, and it would have been the biggest room in the animal. **Sliced, it is a dozen separate tubes
two to five cells across**: the hollow insides of the ten arms and two tentacles, fanning out with
the midline solid between them. A volume total is not a room, and this file has now made that
mistake from both directions in one design - once believing a two-wide arm base was a landing, once
believing a fan of arm bases was a hall.

What IS there is better. Classified cell by cell rather than counted:

    #  rock     M  the sealed body cavity     .  OPEN VOID
    Y150  .......##MMMMMM###.....###MMMMMM##.......
    Y149  #.......##MMMMM###.....###MMMMM##.......#

**The squid's mouth is open.** A shaft of outside runs down the axis from Z80706, widening forward,
and the body cavity forms a RING around it - one to three cells of rock at the closest. So the
front of the market is two galleries either side of a hole that goes to the sea, and the window
Jack wanted has been there since the animal was built.

#### THE DECK STOPPED BECAUSE MY WIDTH DID, NOT BECAUSE THE ROOM DID

`_bazaar` lays its aisle through `_room_span`, which asks about the run of cavity containing the
AXIS. From Z80705 the axis is not cavity, so the deck stopped at Z80704 and about 1,300 reachable
cells sat behind a measurement that could not see them. `_runs` asks the other question - every
contiguous run at a course, not only the one through the middle - and the prow is 125 cells of deck
in two galleries, entered by ten steps DOWN from the market, because `_profile` is a running maximum
and the ring's own floor is two to three courses under the bazaar's.

#### FOUR DEFECTS IN THE WINDOWS, EACH CAUGHT BY A TEST RATHER THAN A RENDER

- **THE WALK STARTED IN THE GALLERY AND CROSSED THE WHOLE ANIMAL.** Written as "walk from the
  gallery toward the axis", at a course where the mouth has not opened yet the cavity is CONTINUOUS
  across the body - so the walk crossed the room and cut out through the far FLANK. That is a hole
  in the animal's skin rather than a window onto its mouth, and it looks identical in every render
  this repo can make. The axis is checked for being open void FIRST.
- **THE WINDOWS WERE AT KNEE HEIGHT AND THE MOUTH IS NOT.** Searched at floor+1..+3, where a window
  obviously goes, the rule found nothing and reported zero on a correct build. Measured, the axis is
  open at Y147-152 against a ring floor of Y142-144: it is a CLERESTORY, four to eight courses up.
- **A WINDOW IS A RUN ON ONE PLANE, NOT A SET OF CELLS.** Placed one at a time wherever the rule
  allowed, forty-six panes came out as a scatter of black blobs at three different depths - the
  mouth's wall is jagged, so each pane sat where its own cut happened to end. It rendered as damage.
  The deck soffit's confetti, in glass, for the sixth time.
- **AND A RUN OF COURSES IS NOT A RUN ON A PLANE.** With the run gate in, three qualifying courses
  still left panes at three different x - a run of one each. The plane is chosen once per window and
  the run re-checked against it. `tests/test_abyss_market.py` asserts the run rather than a count,
  which is why it caught this: the count was fine both times.

**Forty-six panes became fourteen on a shared plane and EIGHT in real runs** - two tall slit windows
with copper caps, which is what the geometry supports. The test's floor is six and says so: a bigger
number would be asserting a wish.

#### The dig, and one thing that had already gone stale

    36  the shaft's mouth      20  the prow's windows      56 total, budget 60

`exclude_boxes` was two boxes drawn round the shaft by hand, written before the prow existed, and it
silently did not cover it: thirty panes came out as thirty overlaps. It is DERIVED from the dig list
now, one box per cell. **A declaration that has to be kept in step with the thing it declares is a
declaration that goes stale**, which is this file's most-repeated finding pointed at itself.

### THE STAIRS: FOUR BUILDERS, FOUR RISERS, AND ONLY ONE OF THEM RIGHT (2026-09-09)

Jack, on the placed market: *"the stairs arent aligned, so theres a bunch that are placed wrongly or
dont connect to lead to the upper areas as we progress towards mouth."* Measured over the shipped
design, **six transitions were wrong with three different causes**, and two of the three were
invisible to every check the design already had.

    Z80561/66/70   the Sounding Hall lays deck course by course and placed NO tread at all
    Z80703         a TWO-course drop with nothing in it: you can fall it, not climb it
    Z80705/80710   the prow, which DESCENDS toward the mouth, given south-facing treads

**All 197 stairs in the build faced south.** That is right for the arcade, which climbs toward the
head, and backwards for the prow, which falls away into it - and this repo has recorded since
`test_stairhead` that **our renderer draws a backwards flight identically to a correct one**. The
only reason the convention has ever held here is that it is asserted.

#### THE FIX IS ONE POST-PASS, NOT FOUR PATCHES

`_walkway`, `_gullet`, `_sounding` and `_prow` each had their own riser logic. `_treads` runs over
the FINISHED deck instead and states the rule once: **a tread sits at the HIGHER of the two courses,
in the column on that side of the step, with its tall side facing the higher deck.** CLAUDE.md's "a
flight that ascends toward D has every tread facing=D" falls out of that rather than being applied
by hand, and a room added later gets correct treads for free. It runs to a fixpoint, because the
cure for a two-course drop is an intermediate landing and that landing is itself a step wanting a
tread.

#### I PUT THE TREAD AT THE LOWER COURSE, AND MY OWN TEST AGREED WITH ME

Jack walked the fixed build: *"you inserted a bunch of full blocks on tops of stairs right above the
entrance and so you walk up stairs, have to jump then walk then jump its very strange."* He is
describing the fix, not the original fault.

**A tread at the LOWER course drops you half a block and then asks for a whole one.** Surface
heights, which is what a body actually stands on:

    deck Y+1 -> tread at the LOW course, top Y+1 -> deck Y+2      one 1.0 rise: A JUMP
    deck Y+1 -> tread at the HIGH course, front Y+1.5, back Y+2.0  two 0.5s: a walk

The convention was on this page, read off Jack's own flight, and says so exactly - *"four
consecutive straight bottom-half treads, each ONE COURSE UP AND ONE STEP east"*. **The tread climbs
WITH the step**; a riser laid beside the lower deck is a step you fall off before you climb it.

**AND THE TEST I WROTE FOR IT ENCODED THE SAME WRONG RULE, so it passed on an unwalkable build** -
276 transitions, 0 bad, and you cannot walk up it. It asserted a tread AT THE LOWER COURSE, which
is where I had put them: **a test that re-states the rule the code states cannot catch that rule
being wrong.** This repo already records the shape of that (`SplitOrderTest` grading its own copy of
the packing arithmetic); this is the same failure written in geometry.

So the test no longer asserts a convention at all. `test_the_walk_can_be_WALKED_without_jumping`
models SURFACE HEIGHTS - a full block is 1.0, a bottom stair is 0.5 at the front and 1.0 at the
back - and demands nothing on the walk rises more than half a block in either direction. Whatever
the right arrangement of treads is, that is the thing it has to ACHIEVE, and it fails on the wrong
one. **Assert the property, never the mechanism.**

**Scoped wrongly it was far worse than the disease.** Pointed at `_floors` - every standable cell
the design placed - it read a lay-by BENCH beside the walk, a rib top and the collar's platform as
courses of the same route, found steps of nine and ten courses between them, and started inserting
landings in mid-air: **six bad transitions became thirty-three.** A walk is its own material.

#### THE GULLET WAS A SEVEN-COURSE WALL AND NOTHING COULD SEE IT

The worst of it, and the one Jack actually walked into. The mantle's deck ends at Y137 down in the
throat's narrow notch; the head's begins at Y144 up in the wide part; **the design laid nothing
between them.** The cause was not a missing builder - `_gullet` laid its deck at `deck[z]`, the
running-max profile, and `_room_span` correctly refuses that because at Y137 the throat is a
one-cell notch with no headroom. It returned None for six courses running and the builder shrugged.

Measured, the cavity above is thirteen wide from Y140 up. **There was never a wall, only a floor
nobody built.** The gullet climbs now, one course per block, meeting the head's deck exactly.

#### AND A TREAD CHECK CANNOT SEE A STRETCH WITH NO TREADS IN IT

`test_..._RIGHT_TREAD` validates the steps that EXIST. It reported **0 bad** while the tail still
had an eleven-block hole - Z80507-80517, between `_vault`'s five-course landing and the Sounding
Hall's deck, belonging to no builder at all. The walk flood passed too, because **scrambling over
the animal's raw rock IS walking.**

`test_the_whole_walk_is_on_BUILT_FLOOR_not_the_animal_s_raw_rock` floods from the shaft's foot over
cells whose floor THIS DESIGN PLACED. It found the tail at nine cells and named it. That is the
test that matches what Jack said - *"dont connect"* - and the tread test is the one that matches
*"placed wrongly"*; neither alone covers the complaint.

#### Three smaller ones, each caught by the previous fix

- **A stair may not take a lamp, and the fix for that had three bugs of its own.** `_relight` sets
  a froglight INTO a floor cell, and after `_treads` a whole flight is floor cells - so with no
  guard it un-builds the flight it is lighting, and with only four orthogonal candidates it gives
  up on a flight and reports itself finished with treads at block light 6. Each of the three fixes
  below shipped, was believed, and left the same three cells dark; see below.
- **The prow took each course's own local floor** and wobbled 143, 142, 143, 142 - every wobble a
  step down immediately followed by a step up, which is two treads where the animal meant one
  slope. It runs a running MINIMUM forward, the mirror of `_profile`'s maximum.
- **And `surf.py` lied three separate times** by reading the LOWEST standable cell in a column,
  which finds the animal's raw throat *under* a built deck and reports the deck as missing.
  CLAUDE.md already records that classifier being wrong three times; this is the fourth and fifth.

#### A LIGHT SOLVER THAT IS OPTIMISTIC IS THE ONE KIND THAT MUST NOT EXIST

Three cells of the gullet's climb stayed at block light 6 through five separate fixes, and every one
of them was a guess. What settled it in twenty minutes was instrumenting the placement branch - not
the search, which was the part I kept re-writing.

- **THE SOLVER CROPPED ITS OWN LIGHT MODEL** to a padded box round the deck, so light behaved
  differently at the crop edge than it does in the world, and it reported **`dark_left: 0` while
  three treads sat at 6**. It says a floor is lit when it is not, which is the whole failure the
  pass exists to prevent. The crop is gone: it propagates over the full canvas, which is what the
  test does anyway, **and the two agreeing is the point** - the same drift `proportions.measure` and
  `rubric.score` share an entry point to avoid.
- **THE FALLBACK BURIED THE LAMP UNDER THE FLOOR.** It searches `dy` in (0, -1, +1) so it can reach
  a neighbouring deck one course down - and on a flight, where every `dy=0` candidate is a stair, it
  took the STRINGER at `dy=-1` instead: a froglight sealed beneath an opaque deck block, placed,
  counted, lighting nothing. **A flush lamp must BE a floor**, so a candidate now has to have air
  over it. Nothing else in the code could see this: `put` succeeded, the grid was updated, the
  round reported progress.
- **AND RE-PLACING THE SAME LAMP COUNTED AS PROGRESS.** `got > 0` is the "nothing left I can reach"
  break, so choosing the same useless cell every round kept the solver alive for its whole
  24-round budget re-placing one lamp. A cell used once is not a candidate again, and with that the
  fixpoint converges in **4 rounds**.
- **THEN THE LAST RESORT HUNG A LANTERN OUT OF RANGE.** The gullet's climb is one cell wide with the
  animal's rock either side, so there is no floor to take and its ceiling is **eighteen courses up**
  - four more than a lantern reaches. It is chained down to four over the step now (`iron_chain`,
  not `chain`, in 26.x), which is the taproot entrance's own idiom for the same reason: light that
  falls DOWN a shaft rather than onto its rim. 14 chains, and the two "hanging from air" problems
  the flush version left went with them.

    286 transitions, 0 needing a jump . 0 steps over one course . 825 treads . 21 landings
    dark_left 0 in 4 rounds . 17 tests . 3,934 blocks . 0 new problems in context

#### AND A SLICE BETWEEN TWO ANCHORS DELETED TWO FUNCTIONS

Worth writing down because it cost more than any of the above. Replacing `_gullet` with
`b[:b.index('def _gullet(')] + new + b[b.index('def _prow('):]` silently deleted **`_runs`,
`_ribs` and `_bazaar`**, which lived between the two anchors - and the file is untracked, so there
was no git copy to recover from. It surfaced as `NameError: _bazaar is not defined` two builds
later.

**A slice replacement must be bounded by the END of the function being replaced, not by the next
anchor somebody remembers.** The safe form is to find the target's own terminator - the next
top-level `def` AFTER it - and assert that nothing else was removed by counting `def` before and
after.

### Still open

- **Nothing has been placed in game.** `render3d` has NO EMISSION, so the 144 froglights that are
  the entire reason anything down there is visible draw as cream blocks here. Judge form and mass
  off `out/market_*.png`; judge the light in world.
- **THE TWO EYE PODS ARE NOT REACHED, AND THE PRICE IS MEASURED.** 107 cells each, at Y172-182,
  one inside each eye - and a shaft from Prismworks lands on the crown with only TWO cells of shell
  over the left pod at X97558 Z80754, which is the best reveal available on this island: you
  descend eighteen blocks and arrive inside the squid's eye. What stops it is the other end - the
  cheapest internal bore from a pod to the main cavity is **27 solid cells** one wide, so a
  walkable 2x3 passage is roughly 150-200 dig cells through the head's own mass. That is a
  decision about digging into the sculpture, not a defect, and it is Jack's.
- **The arcade's deck is one flat plank field for 86 blocks.** The ribs give it a rhythm; a floor
  pattern would give it a grain.
- **The prow has TWO windows and the animal allows about that many.** A wider aperture needs a
  thinner wall than the mouth's ring has, and a forward one has nothing in its cone. If more light
  is wanted there it has to be put OUTSIDE - which is decorating the animal, and is Jack's call.
- `walk.ducked` is 4 - four Z values where the cavity leaves under three courses over a deck. They
  are at the tail taper and the walk closes over them; a fifth would be a hole.
- **The market is NOT in `Park Complete`.** Like the squid it ships at its own recorded origin, so
  `park_place.extras()` never lifts it to the park's build plane. Place it by name.

