## PF Games Row: the Skill Arcade and the Prize Point retired, and the self-reference that gutted a machine (2026-09-03)

Jack, on the two buildings at the head of Midway column C: *"i dont like these and they feel out
of place/useless unclear."*

**MEASURED BEFORE EITHER WAS RETIRED**, over the shipped park:

| | | |
|---|---|---|
| Skill Arcade | 6,364 blocks, 51 x 33 | 84% of its footprint solid, 21 courses, **three** games inside |
| Prize Point | 1,927 blocks, 20 x 33 | a nine-barrel counter, forty courses from the games it redeems |

Both were sound - reachable, signed, 30.5% and 42.5% detail blocks against the outside corpus's
17.3% median, 42 and 40 in palette against its 37. **Neither was broken and Jack was still right**,
and the three reasons are all numbers:

- **THE ARCADE WAS A CLOSED HALL** - the shape the Arrival Court and Boomtown Spine were both
  retired for. Its inside was good (a lit aisle, timber trusses, three working bays, 1,160
  standable cells) and NOTHING on the street said so. A hall reads as a building; a counter
  reads as a game.
- **ITS OWN MARQUEE SAID "five games" OVER THREE.** `PF Front Midway` had been advertising two
  games that did not exist since the frontage was written.
- **AND THE COLUMN HAD NO ROUTE THROUGH IT.** `Park Ways` paves nothing in V24-99 but the V77
  cross walk and two door spurs, because the hall filled the column wall to wall. Every other
  column in this park has a spine; this one had a door.

**`PARK_MIDWAY.md` HAD ASKED FOR THE REPLACEMENT IN ITS OWN WORDS ALL ALONG** and nobody had read
it: *"Merge Plinko, High Striker, and arcade functions into a single awning/facade-backed games
frontage. Each bay has a standing spot, input, outcome, clear prize or score path, and protected
redstone rear. Place the prize counter as the natural next step."* A FRONTAGE, not a hall.

### `gen/gamesrow.py` builds no building, and that is the whole design

`arcade._shell` gives every `park_games` console its own corner posts, back wall, roof beam and
fascia, and `_signs` signs it. **They are self-contained open-fronted booths.** So the module is
the STREET: the walk the column never had, the screen that fills the gaps between the consoles,
the bunting over it and the planting behind it.

    -U flank, front U357   TARGET WALL V26-37 . THE MARK V41-51 . THE STRIKER V55-66
                           PRIZE POINT V85-97, past the cross walk - the natural next step
    +U flank, front U371   THE DOUBLE V28-42 . THE SIGNAL V48-63
    between them           the walk, U358-370, V24 -> V99, into the helter skelter's forecourt

**FIVE GAMES NOW, AND THE MARQUEE STOPS LYING.** The Striker and the Signal are two kinds
`park_games` already had and the Midway never built - and the spec names the high striker by name.
The sign was made true rather than toned down.

### THE FRONTAGE WAS BUILT BACKWARDS TWICE, AND ONE RENDER SETTLED EACH

- **A COLONNADE PUTS ITS POSTS BETWEEN THE WALKER AND THE GAMES.** The first attempt carried a
  striped canopy three cells out over the walk on posts down each kerb - and every console stands
  BEHIND that line, so what it actually built was a covered arcade with the games hidden behind
  its own posts. Exactly the fault being fixed, in a new material. A booth already has a roof
  beam and a fascia; it does not need a second roof and it must not have anything in front of it.
- **AT SIX COURSES THE SCREEN WAS A CANYON.** The replacement - a wall on the bay front line with
  the consoles as its openings - is right, and at the consoles' own height either side of a
  thirteen-wide walk it read as two blank walls with the games behind them. **A frontage a visitor
  SEES OVER is a frontage; one they cannot is a fence.** Four courses, dark plinth, white field,
  red top rail.

### THE CONSOLE'S CONTEXT WAS THE COMPOSITE THAT ALREADY CONTAINED IT

The worst of this session, and it shipped a clean audit. `park_games` **refuses every cell its
`under` capture owns** - deliberately, because a console is fitted into a room that exists and a
cell the building owns is an overlap. All six configs pointed `under` at `out/Park Complete
.litematic`.

The moment they were placed, that composite contained them. A regenerate then found each machine's
own standing copy in its own world and refused nearly all of it:

    PF Game The Double    556 blocks  ->  a 9x3x1 stub of FOUR, `problems: 0`, sidecar written

**A design whose context contains itself does not fail, it evaporates** - and the sidecar, the
audit and the BOM all agreed with the result. This repo has now recorded the self-reference trap
six times (the ruin ring's seat, the town's door frames, the scatter's own lawn, the frog's
plaques, the helter skelter's walk test, and this) and this is the first time it silently destroyed
a machine rather than merely under-reporting one.

**THE FIX IS THAT A CONSOLE'S CONTEXT IS THE GROUND LAYER, NOT THE COMPOSITE.** `under` is now
`[Park Ways, PF Park Green, PF Front Midway]` - what paves, plants and signs the ground it stands
on - and its own bay is reserved by the row, so nothing else in the park can be in the way. That is
permanent, where holding the design out of `EXTRAS_READY` and re-shipping is a dance somebody has
to remember.

### Four more, each of which passed everything

- **A DECORATION ORPHANED A MACHINE.** `PF Front Midway`'s Arcade Bunting ran up U380 from V24 to
  V48 - which is where The Double now stands - and took four of its cells. Bunting belongs over a
  walk in any case; the row carries its own now, and the frontage's stamp is gone.
- **THE RESERVATION MUST BE PINNED TO THE ARTIFACT.** The six bay boxes are `blocked`, so the
  street raises if it wants one - but a box measured off a console and left behind when the console
  moves guards nothing at all, and it fails silently because a box round empty ground raises on
  nothing. `test_every_bay_box_matches_the_console_it_reserves` reads the six shipped litematics.
- **A ROW HAS NO DOOR.** The Arcade's two portal gantries stood over its entrance and exit spurs;
  a gantry naming a door that is not there is the same orphaning, so both are removed and the
  marquee does the naming.
- **`verify_replaceable` AND `park_place.clashes` ASK DIFFERENT QUESTIONS.** Three of the row's
  sixteen trees stood their trunks in `PF Park Green`'s moss carpet and ferns. The audit allowed
  it - the row declares that ground cover replaceable - and the cross-design check counted three
  cells shared between two designs, which is a WORK problem rather than a rendering one: you place
  a block, the next placement says it is wrong, you break it and place it again. **A site with
  another design's ground cover in it is not a free site.** The three are dropped; thirteen stand.
- **AND A GAMES ROW IS NOT A FOOD ROW.** `Midway Row` is eight free-standing stalls with gaps and
  bunting on the avenue eighty blocks away; this is a continuous frontage with openings cut into
  it, which is the spec's own distinction and what keeps two rows in one land from reading as one
  idea twice.

### AND THEN THE ROW WAS RETIRED TOO, BECAUSE THE CONSOLES ARE SEALED CABINETS

Jack, on it as built: *"the games arent playable as they are facing, theyre ugly, and just not
working, these have been a consistent issue, either identify and make them really look good, or
trash the idea and lets put something else there."*

**THE FAULT IS IN `park_games`, NOT IN THE SITING.** Dumped block for block off
`out/PF Game Target Wall.litematic`:

    Y206   ############   the lid
    Y205   ##B#######T#   the BELL and the TARGET - the game's own INPUT
           ###LLLLLL###   the six score lamps
    Y204   ############   the plinth
           front face U357: solid at Y204, Y205 and Y206

**A CONSOLE IS A THREE-COURSE SEALED CABINET.** Its score lamps - the thing that tells a player
what happened - are buried in the lid course in EVERY kind. The `aim` and `striker` targets are
entirely enclosed, so they cannot be shot. `pair`'s two buttons sit on top of a three-course lid,
above a standing player's head, with their lamp buried eleven cells away at the far end. Only
`counter`'s barrels are on a face a player can touch.

**AND EVERY ONE OF THEM SIMULATES CORRECTLY.** The circuits are right, the contracts pass, the
audit is clean. That is this repo's own cardinal sin - *a machine that looks like it works* - in
the one subsystem written to prevent it, and it is why the games have been "a consistent issue" for
as long as they have existed. `park_games`' own docstring states the assumption that makes it
happen: *"a console is furniture ... it needs no ceiling because the building already has one."*
**The Skill Arcade was that building. Retiring it did not cause the fault, it revealed it.**

Three attempts to make the row read all failed for the same reason and each is worth keeping:

- **A COLONNADE PUTS ITS POSTS BETWEEN THE WALKER AND THE GAMES.** Posts on the walk's kerb
  carrying a canopy out over it - and every console stands behind that line.
- **AT SIX COURSES A FRONTAGE SCREEN IS A CANYON.** A frontage a visitor SEES OVER is a frontage;
  one they cannot is a fence.
- **AND A BOOTH ROUND A SEALED CABINET IS A BOOTH ROUND A SEALED CABINET.** The third attempt
  raised each bay on a deck so the counter would be waist high - correct, and it changes nothing
  about lamps that are inside the lid.

### What is there now

`PF Midway Garden` - **2,455 blocks**, 0 problems, 0 overlap, 0 clashes, nothing expensive. The
walk is the one thing kept from the row, because it is the one thing the column actually needed:
a thirteen-wide spine from the east avenue to the helter skelter's forecourt, with a kerbed
parterre either side under a clipped hedge, a lozenge motif in wool with flowers between it, a
specimen tree at the centre of each bed, benches on the verges and four striped pergolas over the
walk. **No building anywhere in it, and nothing that pretends to be a machine.**

    the lot V24-99 x U345-384   3.5 b/col, 78% standing 3+ tall  ->  0.93 and 8%
    the column's spine          none  ->  76 courses, avenue to the tower's forecourt
    what a visitor can DO here  three sealed cabinets  ->  nothing, honestly

**AND THE BEDS STOP AT U377 BY MEASUREMENT.** `PF Park Green` holds 105 cells in this lot and 98
of them are at U378-384 - it dresses the outer band of the east flank. Beds drawn to the lot edge
would have contested every one, which is a WORK problem rather than a rendering one: you place a
block, the next placement says it is wrong, you break it and place it again. The wild edge stays
wild, which is what a pleasure garden's outer walk looks like anyway.

**A PARTERRE IS A MOTIF, NOT A SCATTER.** Hashed per cell the beds came out as random patches of
colour - the deck floor's confetti, in wool. The lozenge is a function of the DISTANCE from each
bed's own midline, so the pair either side of the walk mirror each other for free.

### AND THEN IT WAS FIXED (2026-09-03)

Jack: *"fix it"*. `mcbuild/gen/park_games.py`, and the four consoles standing in the Frontier are
fixed with it.

**THREE FAULTS, ONE CAUSE.** A console was designed as furniture for a room - its own docstring:
*"it needs no ceiling because the building already has one"* - so its front was a wall, its works
were sealed behind that wall, and its controls sat on the lid where a room's own lighting would
have shown them. Nothing about that survives contact with a player standing in front of it.

    THE WINDOW        the machine course's front row is GLAZED, not walled
    THE SIGHTLINES    a channel carved from every lamp and every input out to the front
    THE CONTROLS      moved off the lid onto the front face, at the machine course

**THE WINDOW IS AT EYE LEVEL BY ARITHMETIC, NOT BY LUCK.** A player's eye is 1.62 above the floor
they stand on, which is the console's own base course - so the machine course IS their eye line.
Opened, they look straight into the works; the lid stays on, so the slot is one course and nobody
can climb in.

**GLAZED, NOT OPEN, AND THAT DISTINCTION IS THE WHOLE OF IT.** Left as air the window is a hole a
hand reaches through: measured, nine of eleven consoles then had a wire, a repeater or a comparator
with a clear line to the outside, which is the leak `_ring` is a wall to prevent. A pane stops the
hand and not the eye - which is exactly what a shopfront is - and `_daylight` cuts it back to air
only in the columns an ARROW has to pass through, because glass stops one of those too.

**AND THE CONTROL IS THE SAME MECHANIC TURNED NINETY DEGREES.** `_press` relied on a floor button
strongly powering the block BENEATH it with dust under that block; `_face_control` puts a wall
button on the outside, strongly powering the block BEHIND it, with dust behind that. The machine
stays sealed, the hand and the eye both find the control, and no kind needed rewiring.

#### Five things it cost, and every one was caught by a test rather than by a render

- **THE CARVE MUST WORK OFF A WHITELIST, NOT A BLOCKLIST.** Written to skip "the works" it ate the
  counter's own call button and the striker's rules sign - neither is wire nor lamp. It removes the
  cabinet's own wall, trim, floor and glazing and nothing else, because the next part somebody adds
  will not be on anybody's blocklist either.
- **A BUTTON CANNOT HANG ON A PANE.** The counter's call button ended up bolted to glass: the bell
  it rings is an OUTPUT, and the sightline carved for that bell ran straight through the button's
  own backing. Two passes each correct alone and wrong together. `_reattach` is the last word.
- **A WIRE IS NOT A BARRIER.** `_seal` bailed on any occupied cell, and a long dust run points at
  the front - so it bailed on every wire in the design and placed not one pane while the front-most
  cell of each run was still open. Only something a hand cannot pass counts as cover.
- **DUST DOES NOT BLOCK SIGHT.** It is a sixteenth of a block tall and you look straight over it;
  leaving it out of the test's sight set reported five of the Signal's lamps as walled in by the
  very wire that lights them. Sight and reach are two sets, and the pane is the difference.
- **AND THE TEST'S OWN WALK STOPPED AT THE FIRST EMPTY CELL** and called it daylight, so a wire
  with one course of air in front of it and a pane beyond read as exposed. A cell absent from a
  model inside its own box is AIR. Two consoles were reported unsafe that were not.

#### The check that had never existed

`tests/test_park_games_visible.py` (43) asks the question `mcbuild.circuit` cannot: **a simulated
contract is a claim about the CIRCUIT, not about the PLAYER.** For every kind - can every score
lamp be seen from the front, can every target, button, lever and plate be reached from it, is no
wire within a hand's reach, and is every control within one course of the floor rather than on the
roof. All 43 pass; `tests/test_park_games.py` still passes its 144 circuit contracts, so nothing
was traded for it.

    PF Game Pan Line, course 2 (Y206)      PF Game Pan Line, course 3 (Y207)
      z7  #...wwwwP#   the scale               z3  #####L####   the lamp
      z8  #ooooooo.#   glazed, and OPEN        z4  #####o####   glazed channel
                       at the scale's column    ...  out to the front

#### Still open

**`PF Game Ascent Signal` is orphaned and it is not this pass's**: its building is `PF Prism
Ascent`, one of the four modules removed for the Prism Well, so it clashes with the `PF Prism
Downs` terrain that replaced it. `tests/test_park_games.py` fails on it and on nothing else.

And **the six Midway consoles stay retired** - `PF Midway Garden` holds that lot by Jack's own
choice - but they now build correctly, so putting them back is a decision rather than a repair.

