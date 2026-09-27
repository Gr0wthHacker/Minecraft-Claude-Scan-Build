## The leftovers audit: apparatus for machinery that was removed (2026-09-03)

Jack: *"we have random left over arches and other objects scattered across the map, i noticed some
near prism, etc, audit all areas and lets clean up weird left behinds."* Everything he saw was real,
**and none of it failed a single check this repo has** - every piece is a legal, supported,
affordable, 1.19, non-colliding block standing exactly where its config puts it.

### A MODULE CAN BE RETIRED; THE THINGS THAT POINT AT IT ARE NOT

That is the whole class. A building leaves `park_lots.PLACEMENT` or `park_place.EXTRAS_READY` in one
line, and every marquee, relay, plaque and threshold that names it goes on standing - correct in
every measurable way and describing a park that no longer exists. Prismworks had five:

| piece | at | its sign said | names a module that is |
|---|---|---|---|
| SIGNAL 1 | V58 U435 | "foundry relay" | `Foundry Gate` - not in the park |
| SIGNAL 2 | V86 U435 | "foundry relay" | `Foundry Gate` - not in the park |
| SPARE LENS | V110 U435 | "cast for the array, unused" | `Prism Array` - not in the park |
| SIGNAL 3 | V30 U534 | "array relay" | `Prism Array` - not in the park |
| SIGNAL 6 | V70 U590 | "ascent relay" | `Prism Ascent` - **retired** for the Prism Well |

**THE NUMBERING IS THE TELL, AND IT IS A GENERAL ONE.** It ran **1, 2, 3, 6** - signals 4 and 5 went
with their modules and nothing renumbered what was left. A gap in a series is the cheapest evidence
there is that a set has been cut down, and it costs nothing to look for.

The second tell is a grammar the survivors no longer obey. `pf_front_prismworks.yaml` states its own
rule - *"a relay is a LINE of the same thing... each line ends on a lens"* - and the foundry line is
a proper three, while the array and ascent "lines" are single stubs. **A design that states its own
grammar can be checked against it**, and a member that no longer satisfies it is a member whose
siblings were deleted.

**RE-SIGNED, NOT DEMOLISHED, AND THE REASON IS MEASURED.** SIGNAL 3 and SIGNAL 4 stand in this land's
two empty bands (U520-539 carries 25 built columns against 1,668 free; U580-599 carries 168 against
1,812) - deleting them re-opens both. Only the captions were stale, so the series now starts at `PF
Signal Zero`, which is the Well's own floor and genuinely IS signal zero, and every relay names
something a guest can walk to: the Well, the Rig over it, the Crown Descent that carries the column
on to Y300. **The structure was doing real work and the words were the only thing wrong with it.**

### Four more of the same shape, in the other two lands

- **`Foundry Gate` marquee** (V20 U448) - retitled PRISMWORKS and doing the land's threshold job for
  as long as the Well has stood behind it. Physically right, internally named for a retired module.
- **`Prize Counter` marquee** (V79 U362) titled PRIZE COUNTER while the thing at the end of its own
  walk is `PF Game Prize Point`, whose board reads PRIZE POINT. **Two names for one counter** - the
  Prize Counter building left with the Skill Arcade.
- **The Welcome Court's threshold** read *"carousel and arcade beyond"*. The Skill Arcade - a 51x33
  closed hall - was replaced by `PF Games Row`, and the sign kept sending guests to it.
- **THE ASSAY OFFICE'S PRIZE WINDOW SAID "win at the range or sluice" AND NEITHER EXISTS.** The
  Shooting Range was tried on the Claim Line and withdrawn; the Gold Sluice was never placed. So the
  one board that tells a guest where to WIN what it redeems named two buildings that are not
  standing, while the land's three real games - Pan Line, Powder Striker, Riffle - sit within sixty
  columns of it. **This is the worst of the six**: the others merely misdirect, this one breaks the
  loop between playing and redeeming.

And one stale RESERVATION rather than a stale sign: **`Signal Heron` held a 27x37 lot** while the
bird is built by `park_ways.yaml` itself (`gen: heron, offset: [26, 1, 176]`) into the `heron garden`
feature lot - the same ground. A lot held for a module nobody places is ground nothing else may use,
and it is what `test_worldrender.py` already failed on.

### The sweep that found them, which is worth keeping

Geometry found nothing. Clustering standing columns and ranking by isolation returned the Circus
balloon and the Signal Heron - both legitimate feature-lot pieces - because **a leftover in a park is
not physically isolated; it is standing exactly where it was meant to stand, next to a hole where its
reason used to be.**

What worked is that **A SIGN NAMES ITS OWN PURPOSE.** Dump every sign in the shipped composite, take
every proper noun, and check it against `contains`. That found all six in one pass, plus the
numbering gap, and it needs no knowledge of any generator. `tools/park_place.py` already prints the
roster; the signs are already in the artifact.

### And five signs were shipped cut mid-word

    MINE CART ESCAP   keep to the wal   112-cell circui   wade in and hol   prismworks: eas

`park._sign` truncated at `SIGN_WIDTH` silently, and **every offline check passes a clipped sign**:
the block is legal, supported, affordable and in 1.19, and `render3d` draws it identically to a whole
one. The damage shows only in a screenshot of the placed build. They arrived by FOUR different
routes - a config title, a config line an author had already shortened by hand, a computed line
(`"%d-cell circuit" % len(track)`) that crossed the width when its number gained a digit, and two
literals - so guarding any one route leaves the class open.

`park._fit` RAISES now. **A TITLE IS STILL CLIPPED BY ITS CALLER, DELIBERATELY**: a title comes from
a config a human wrote, twenty-three of them already run over, and making those raise is a park-wide
decision rather than a helper's to take - `tests/test_civic.py` pins the clipping as the contract for
exactly that case. Removing it park-wide was tried in this pass and reverted: 57 sites across 13
generators, and it breaks designs that are working.

**SO THE GUARD READS THE SHIPPED COMPOSITE, WHICH IS THE ONE PLACE EVERY ROUTE CAN BE SEEN AT ONCE.**
`tests/test_park_signs.py` does it two ways, because neither alone is enough:

- a line at exactly `SIGN_WIDTH` whose last word is a strict PREFIX of a word spelt out whole
  somewhere else in the park - `wal` of `wall`, `eas` of `east`, `hol` of `hold`;
- ...and the CONFIG side, for a cut word the park never spells out: nothing else says "escape", so
  `MINE CART ESCAP` was invisible to the first check.

Two things that check had to learn, both of them the same lesson - **a check that cries wolf on a
correct build is a check nobody runs**:

- **AN INFLECTION IS NOT A CLIP.** `THE CRUSHER` says "five heads", so "ran to the head" - a
  deliberate two-line split - read as `head` cut out of `heads`. `+s`, `+es` and `+ing` are excluded.
- **A CONFIG STRING OVER THE WIDTH IS ONLY A FAULT IF IT REACHES A BOARD CUT.**
  `pf_lost_plateau.yaml` declares `THE LOST PLATEAU` at sixteen and its generator SPLITS it - the
  shipped sign reads "THE LOST / PLATEAU" and nothing is lost. The test is whether the string's first
  `SIGN_WIDTH` characters stand on a board verbatim: `MINE CART ESCAP` does, `THE LOST PLATEA` does
  not.

### A trap that cost an hour, and has nothing to do with the park

**`pathlib.read_text()` / `write_text()` ROUND-TRIP THROUGH UNIVERSAL NEWLINES.** A patch script that
reads a file, replaces a string and writes it back rewrites EVERY LINE of a file whose endings differ
from the platform default - `git diff --stat` said *2,025 insertions, 2,025 deletions* on a file where
one string had changed. It also silently broke every multi-line anchor in the next script, because
the file on disk was now CRLF and the anchor had been written with bare newlines.

Read and write BYTES when patching (`read_bytes().decode()` / `.encode()` back), and anchor on SINGLE
lines rather than multi-line blocks. `git diff --ignore-cr-at-eol --numstat` is what tells a real
content change from line-ending damage, and it is the only way to find out which files a bad patch
actually touched.

### The suite already knew, and nobody had read it

Run across the whole park selection the audit came to **58 failures and 28 errors**, and the useful
part is not the number - it is that **THE SAME CLASS ACCOUNTS FOR MOST OF THEM.** A retirement is
made in one list and the other places that name it are left standing, and a test naming a retired
module fails in a way that reads as a MISSING BUILDING rather than as a RETIRED one, which sends the
next reader looking for the wrong thing.

**`test_parkways::test_every_module_is_either_placed_or_declared_not_to_need_ground` IS THIS AUDIT,
ALREADY WRITTEN.** Its own docstring names the three ways a module may be accounted for - it has a
lot, the grid draws it, or it is RETIRED with a reason written beside it - and it was failing on
seven modules with no lot and no reason:

    Boomtown Spine · Foundry Gate · Prism Array · Prism Ascent · Resonance Vault · Forge Deck

...which is, to the name, the retired roster the frontage signs were still announcing. They are
filed in `park_lots.RETIRED` now with what happened to each. `Signal Heron` joined them - it is
SUPERSEDED rather than retired, because the bird still stands and what left is the artifact and the
lot this table held for it, and the set keeps that distinction.

**What this session fixed in the suite**, all of it the same defect:

| | |
|---|---|
| 28 errors | `test_park_vantage` could not load `pf_vantage_midway_belvedere.yaml` - commit ad49844 moved it to `archive/` and left the test opening it from `configs/`, so EVERY test in the file had been erroring on `FileNotFoundError`. It reads the archive now: 21 pass |
| 7 | `test_parkways`, above - down to one (`Wyrm's Crossing`, another stream's in-flight siting) |
| 1 | `test_park_frontage`'s roster, which named six retired modules |
| 1 | `test_prismworks_builds`'s ascent test, skipped with its reason |

**And what is PRE-EXISTING, each verified by running the same test with this session's changes
stashed** - the discipline matters, because three of them looked like mine at first glance:

| | |
|---|---|
| 16 | `test_park.py::test_every_kind_is_one_connected_piece[*-paths]`, already recorded above |
| 10 | `test_park_vantage`, once it runs: two of its three vantages are retired, and `PARK_ORIGIN` is typed as 190 where the composite now starts at 94 |
| 9 | `test_worldrender` - identical with and without the `park_lots` change |
| 8 | `test_isthmus` + `test_overgrowth`: `wayfinding.known_destinations()` has no PRISMWORKS zone |
| 7 | `test_evidence` - identical at baseline |
| 6 | `test_frontier`: `KeyError: 'prismworks'` in `frontiertown.py`, and 109 cells of escaping water |
| 5 | `test_park_final_worldplan` |
| 1 | `test_wayfinding`: 'Haunted Manor' names no real module |
| 1 | `test_park_games`: `PF Game Ascent Signal`, already recorded above |

**THE WAYFINDING ROSTER IS THE NEXT ONE TO FIX AND IT IS THE SAME SHAPE.**
`wayfinding.known_destinations()` still answers FRONTIER / MIDWAY / HOLLOW when the third land has
been Prismworks for weeks, and it does not know the Haunted Manor - so `_check_dest` RAISES, which
is the right instinct wired to a stale list. It is nine failures across three files and it was not
touched here because the roster is `planner.THEMES`'s to fix, not a signage pass's.

**And a working-practice note, because it cost most of the time.** `pytest tests/ -q -k "..."` over
this selection takes **sixteen minutes**, and a background task is reaped before it finishes - so
the result was read three times from a run that had been killed at 38%. Run it per FILE, or in
batches small enough to finish inside a foreground call, and never conclude "green" from a subset:
the first report of this session said green off targeted runs, and the broad run said 58.

### Still open, and deliberately not changed

- **The rail stations say `EXIT / DOWN TO ARCADE / PARK RETURN`** on all three platforms. That
  "arcade" is the ARCHITECTURAL passage under the viaduct and it genuinely exists - but the park also
  had a games Arcade until recently and no longer does, so a guest reading it on a station has no way
  to know which is meant. Renaming it is a wayfinding decision, not a leftover.
- **The Mine Coaster and the Rapids were not regenerated.** Their two shortened lines
  (`board at end`, `climb the tower`) are preventive - neither sign is in the shipped park - and the
  coaster is 31,197 blocks to rebuild for a string nobody can currently read.
- **`wayfinding.known_destinations()` HAS NO PRISMWORKS ZONE**, and it is the same defect one
  level up: the roster answers FRONTIER / MIDWAY / HOLLOW when the third land has been Prismworks
  for weeks, and does not know the Haunted Manor - so `_check_dest` RAISES, which is the right
  instinct wired to a stale list. Nine failures across `test_isthmus`, `test_wayfinding` and
  `test_overgrowth`. It belongs to `planner.THEMES`, not to a signage pass.
- **`Wyrm's Crossing` IS THE ONE MODULE LEFT WITH NO LOT AND NO REASON.** It is in
  `park_place.KEEP` so somebody intends it, it is not in `PLACEMENT`, and `PF Wyrm Gate` now
  carries the skull - another stream's in-flight siting, so it is not filed here.

- **247 designs have a config and are not in the park.** That is the retired record and it is
  correct; what matters is only whether something STANDING still points at one of them.

- **`test_every_measured_trough_gains_something_to_look_at` FAILS ON U520-539, AND IT IS THE SAME
  FINDING.** The band holds 37 cells against a threshold of 100, because the array relay line was
  cut down to ONE pylon when the Prism Array was retired - signals 4 and 5, the numbers missing
  from the series, were that line's second relay and its lens. Re-signing cannot fill a band;
  restoring the line means BUILDING two more pieces, which is content rather than cleanup, so it is
  left. Verified pre-existing by running the test against the unmodified config.
- **`test_the_ascent_tops_out_over_the_tallest_thing_already_in_the_park` IS SKIPPED, SAME CLASS.**
  It pinned a contract only a PLACED module can have, and the Prism Ascent left the park with
  Prismworks v1 - so it was asking a retired design to out-top `PF Crown Descent`, which carries
  the column to Y300. It also hard-codes 190 for the composite's origin, which is 94.
- **THE MIDWAY RETIRED ITS GAMES ROW WHILE THIS AUDIT WAS RUNNING**, and reproduced the whole class
  in twenty minutes: `PF Games Row` and its six consoles left `EXTRAS_READY`, `PF Midway Garden`
  took the lot, and the frontage was not touched - so a GAMES ROW gantry promising "five games" and
  a PRIZE POINT gantry saying "redeem here" stood over ground that is now a garden. Both are
  re-pointed (the first names the garden; the second is REMOVED, because there is no honest caption
  for a redemption sign with nothing to redeem at), and the Welcome Court's threshold now names THE
  GROUND ("the garden") rather than whatever is standing on it this week - which is the durable
  form, and the reason the first fix ("the games row") went stale within the hour.

