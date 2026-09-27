## EVERY LAMP POST IN THE PARK, MEASURED (2026-09-10)

Jack: *"analyze every single lamp post in park complete, identify which need to be there, which are
badly placed, and remove any that arent placed, or dont need to be there, look for bad placements,
bad symmetry, bad symmetry or spacing to objects around it."*

**134 street lamps** - 48 frontier, 61 midway, 25 prismworks - plus **40 standards belonging to
seven other designs**. Read off `out/Park Ways.litematic` and `out/Park Complete.litematic` block
by block, never off a render: `render3d` draws a lightning rod, a fence, a wall and iron bars all
as full cubes and has hidden six separate faults on this park already.

### THE SYMMETRY TEST EXCLUDED THE ENTIRE SPINE, AND THAT IS WHY SIXTEEN UNPAIRED MASTS SHIPPED

`test_the_two_verges_of_a_street_carry_the_same_lamps` skipped `half + 26` either side of every
threshold AND every spur. Seventeen columns at thirty-two blocks each, and the union of those
windows covers **609 cells of a 600-cell street**: it compared an empty list against an empty list
and passed. The spine's fifty-four masts were never looked at, on the one street the whole park is
composed about.

    spine V4 vs V20, as shipped   19 matched . 3 OFFSET BY TWO . 10 with no partner
    mid-block walks V74 and V77   0 of 4 pairs matched - every one STAGGERED BY FOUR
    back promenade V121/V129      23 of 23 matched - the system works where nothing interferes

It is `MenuTest`'s own failure in a new place - *a check configured not to see the thing it was
written for*. The windows are `JUNCTION_CLEAR` and three cells now, which excuses 27% of the spine
rather than 101%, and `test_the_exclusions_cannot_swallow_the_street` is the guard on the guard: an
excuse wider than 40% of a street fails outright. Run against the shipped park the new assertions
raise **six** times; against the rebuilt one, none.

### THE NUDGE WAS THE ONE THING THAT COULD STILL BREAK A PAIR

`run` drives both verges from one list of stations, so the two rows leave it identical - and then
`place_lamp` stepped each mast along its own line, on its own, with no idea the other verge
existed. `place_pair` settles the pair first: one shift that clears BOTH, or each verge takes the
unshifted station and neither nudges alone. **What is forbidden is nudging alone, not standing
alone** - a spur is on one side of its street, so the spine's east verge is paved at U407 and its
west verge is not, and dropping the good verge for the blocked one's sake cost two lamps and opened
a **95-block hole** where there had been two of 40 and 43.

**AND THE ANTI-BUNCH RULE IS WHY BOTH WALKS STAGGERED, not a plaza in the way.** `MAST_CLEAR` is 8
and a `half: 1` walk is 4 wide, so the second verge's mast was ALWAYS within eight of the first and
could never stand opposite its own partner: nudged four along, every time, on both walks. The
stagger was the collision being avoided, not a rhythm.

**Then pairing them made it worse, which is what settled the shape of the answer.** A midway lamp's
arms reach two cells either side, so two facing masts four apart SHARE their beam: one nine-wide
gantry over a three-wide path, three lanterns, the outer two hanging over the lots. A street
narrower than a crossbeam alternates instead - one post per station, sides by INDEX - which is what
an avenue already does and for the same reason. **An alternating street halves its stations**, so
every other one falls on a given verge and each verge keeps exactly the rhythm it was designed for;
at the paired spacing a 43-block walk came out with two posts, which is a lamp rather than a lit
street.

    spine        22 matched . 0 offset . 10 unpaired - the 8 threshold masts, U407's spur, U447
    promenade    23 of 23
    walks        alternating at their own per-verge rhythm, 5 posts each
    closest two masts 8 . 0 incomplete lamps . 0 cells claimed by two lamps at once

### A STATION THAT CANNOT TAKE ITS OWN SIDE TAKES THE OTHER, RATHER THAN GOING DARK

**`PF Plateau Vale`'s talus stands on 73 of the frontier avenue's 131 west-verge columns**
(V28..V120 at U40) while the avenue's own paving at U43 carries nothing at all and its east verge
carries three cells. The mast at V83/U40 had its collar and its lower rod REPLACED by cobbled
deepslate and moss - a lightning rod and a lantern sticking out of a scree mound, which is not a
lamp post - and every one of the 23 columns its nudge window can reach is buried, so there is
nowhere on that verge to step to. A `keep_clear` declines the ground and the station takes the
avenue's clear EAST verge: the run keeps all five of its lamps and none of them is in the mountain.
Both verges are real lines, so a lamp on the far one is not a lamp off its line.

### WHAT IS LEFT, MEASURED AND NOT ACTED ON

- **THE SPINE'S NORTH VERGE HAS FOUR HOLES OF 58, 46, 43 AND 40 BLOCKS AGAINST A RHYTHM OF 22, AND
  EACH SITS EXACTLY OVER A THRESHOLD.** A threshold leaves the spine southward, so `junction` lights
  the south verge only - correctly, there is no northern quadrant to mirror - and `run` then anchors
  BOTH verges on those masts, because that is what keeps their setbacks equal. Two rules that are
  each right, and together they silence the far verge for two rhythms. Mirroring the pair onto V4
  puts two masts 16 apart on a plain verge against a rhythm of 22, which reads as a crossing that is
  not there; filling the middle puts one mast opposite the mouth, which is the asymmetry the module
  removed on purpose. **It wants a decision, not a patch.**
- **A PRISMWORKS SIGNAL MAST DOES A QUARTER OF A LAMP'S WORK.** Its soul lantern is light 10 and it
  is mounted at foot+7, six courses over the walking surface, so it arrives at the street at 4.
  Median street cells lit by one lamp: **midway 143, frontier 105, prismworks 37**, and Prismworks
  is the darkest land at 66% lit with 1,337 pitch-dark street cells. The mast is deliberately a cold
  signal rather than a mood - dropping the light to foot+4, or a second one at the collar, is a look
  decision and Jack's.
- **`midway V121/U308` keeps one arm inside a lot module's wall.** The wall runs U308-318 at V119 and
  the midway-axis vista covers U294-306, so there is no station within `WINDOW_LONG` for the pair to
  move to; moving it means losing the pair and a 73-block gap on the promenade. Left, and stated.
- **Six masts stand on another design's plinth** - five prism masts whose pad is `PF Prism Well`'s
  or `PF Prism Downs`' floor block, one midway collar that is `PF Midway Garden`'s. One cell each,
  cosmetic, and the mast, its light and its rod all stand.
- **Four lamps have another design's light within three blocks**, and three of them are the same
  thing: each land's own frontage lights the spine's south verge, which is the band the street lamps
  use. Systematic rather than three accidents.
- **The Prism Well's keep-clear disc refuses 15 masts and costs almost nothing** - the street inside
  it is **98% lit** because the well lights its own approach. Verified rather than assumed. What it
  does cost is the prismworks mid-block walk at V79, whose six stations are all inside the disc:
  a 54-block walk with no lighting at all.

