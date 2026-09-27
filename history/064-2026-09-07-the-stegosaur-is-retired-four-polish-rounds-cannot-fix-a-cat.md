## THE STEGOSAUR IS RETIRED: FOUR POLISH ROUNDS CANNOT FIX A CATEGORY (2026-09-07)

Jack rejected it four times running, in four different words - *"it feels bad, its asymmetric,
theres issues"*, *"it feels super blocky and rough"*, *"very rough and the face etc are less smooth
then they should be, we want this to feel like the giraffe"*, and finally *"I think its an issue
still, it doesnt look good"* - and every round I answered with a better version of the same thing:
symmetry to zero, a plan spindle, legs that stop pushing through the flank, a skull that is a taper
rather than a ball, `spike_rate` 28.97 -> 3.92 (BETTER than the giraffe's 4.03), a whole new stair
surfacing pass in `shell.py`. Every one of those was a real improvement and it measured as one.
**None of them touched what was wrong.**

**IT IS A STANDING QUADRUPED, AND THIS FILE HAS SAID FOR WEEKS THAT THIS SYSTEM CANNOT BUILD ONE.**
The download corpus's own finding, recorded here under "Reading other people's builds": *the line
is not the species, it is whether the silhouette decomposes into LIMBS - a corpus of 31 outside
builds contains no realistically-proportioned quadruped at all.* Eight mammals were retired on that
evidence. I then read *"a stegosaur is a convex mass with planar plates (the ladybird category)"* -
which this file also says, in the Lost Plateau's re-theme - and sited one, and the two sentences
are about different halves of the same animal. **THE PLATES ARE THE LADYBIRD CATEGORY AND THE
ANIMAL UNDER THEM IS A JAGUAR**, and the plates are 12% of the cells.

The general lesson, and it is the expensive one:

> **WHEN FOUR ROUNDS OF POLISH EACH MEASURE BETTER AND STILL LOOK WRONG, THE FAULT IS THE
> CATEGORY, NOT THE EXECUTION.** A rejection that repeats in different words is evidence about
> the CHOICE; only a rejection that moves is evidence about the craft.

That is the same shape as this file's own note about the jaguar - *"the jaguar at 2.6x and 60,000
blocks failed exactly as the 27-block one did"* - and I had it in front of me each time and treated
the next round as a tuning problem. What broke the loop was not another render: it was stopping and
laying out the whole field of candidates, at which point the answer was obvious from the rule.

`gen/stegosaur.py` is kept, still builds, and keeps all of its tests. `taxonomy.live()`'s rule
applies to a bespoke sculpture exactly as it does to a species: **a retirement is a RECORD, not a
deletion** - it is out of `GAPS` and out of nothing else, because the eleven bugs its scale sweep
found are eleven bugs the next animal inherits the moment somebody copies its machinery.

### And the machinery came out into `loft.py` before it was copied

`Frame`, `r()`, `ball`, `sweep`, `thread` and `STEP` were all private to `stegosaur.py` and were
about to be pasted into a second file. Every one of them carries a bug this repo has already paid
for once - `r()` is half-away-from-zero because `round()` is banker's rounding and turned four feet
into eight combs; `thread` exists because a taper under one cell is a chain of DIAGONAL neighbours
and cost the pterosaur three spans and the stegosaur its spikes; `Frame.clipped` is counted apart
from `refused` because the sauropod shipped clipped to 22 blocks of 48 with nothing to say so. A
private second copy is a second place for all of those to come back.

