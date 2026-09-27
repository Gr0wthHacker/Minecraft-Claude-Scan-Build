## THE LOOP WAS A LATCH: five deadlocks, one shape (2026-09-08, chunkscan 0.9.8)

Jack: *"its really glitchy and at this point i would consider it not functional, it gets stuck,
just sits there, doesnt move from a location, doesnt navigate to chests properly, constantly
redirects itself, misses placements."* Every clause was one fault, all five were the same SHAPE,
and none of them needed a guess — the client had written all of it to disk.

**READ THE LOG FIRST. It is the third session in a row where the answer was in `latest.log` and the
rotated logs beside it, and the first two are already written down on this page.** Twenty minutes
of `zcat ... | grep cscan` named every cause below; the code reading afterwards only confirmed them.
A message-frequency histogram is the single most useful view — `sed -E 's/-?[0-9]+/N/g' | sort |
uniq -c | sort -rn` collapses a session into its repeating cycles:

    2083  N cells at POS — N left in this spot, N more spots after it
    2080  autofly is ON but has nowhere to go
    2077  next spot: N cells around POS, N more after it
    2041  not moving and not placing at POS — giving up on this spot and taking the next one
     533  N spots given up on with nothing placed
      34  RESET #N

**One session: 2,041 identical give-ups, ZERO blocks placed**, against a design the same session's
own analysis reported as holding 23,672 placeable cells. A second session: **41 "cannot open" against
43 "fetch"**, alternating about 1.5 seconds apart, on one chest.

### THE SHAPE: A RECOVERY THAT RE-CREATES ITS OWN TRIGGER IS A LATCH

Every fault below is the same sentence: **a decision is re-made, or a watchdog fires, on the
two-second recount cadence — before the action it commands has had time to finish — and the
recovery it triggers puts the loop back into the state that triggered it.** Once entered it cannot
be left, because leaving requires the very thing the recovery just prevented.

That is the answer to *why so many individually-correct watchdogs add up to a loop that does
nothing*. There are eighteen clocks in `Hud` and every one of them is defensible alone. What was
missing is the idea that **a decision has a lifetime**: nothing marked an action as in flight, so
every clock was free to judge an action that had not started. Each hysteresis added over the last
month — `sameSpot`, `DWELL_MS`, `holdHere`, the station dwell — is a patch on one instance of it.

### 1. THE GOING-NOWHERE CLOCK HAD NO COMMITMENT TERM, AND IT WAS THE LATCH

`Loop.goingNowhere` asks *have I moved in three seconds, and placed nothing*. Nothing else. And
**giving up on a spot leaves the body standing still** — so the next target inherits a clock that
has already expired, and is abandoned before the flight can start. Abandon, re-pick, abandon, four
seconds apart, for ever.

**Its two siblings had it right and it did not.** The look watchdog is
`t - Math.max(movedAt, lookSince)`; the fetch watchdog is `now - Math.max(movedAt, fetchTargetSince)`.
Only this one measured on `movedAt` alone. `targetSince` is stamped in `guide()` and **only when the
destination CHANGES** — re-stamping on every re-guide to the same cell means the watchdog can never
fire at all, which is the opposite bug and just as quiet.

### 2. AVOIDING ONE SPOT AVOIDED EVERY SPOT

`abandonSpot` records the spot and the selector skips anything within **`Plan.MAX_RADIUS` = 48** of
it — while clusters form within **`Loop.NEAR_RADIUS` = 16** of the body. So one entry matched every
cluster in the working area, `next` came out null, and the *"a hard spot is better than no spot"*
fallback then **cleared the whole map and handed back the spot that had just failed.**

**ONE CONSTANT WAS SERVING TWO OPPOSITE QUESTIONS.** `sameSpot` asks *am I still working the same
region*, where a wide radius IS the feature — it is hysteresis, and a drifting centroid must not
read as a new region. `avoided` asks *is this the spot I just gave up on*, where a wide radius is
fatal. `AVOID_RADIUS` is 8, and the fallback no longer wipes the record: taking a hard spot rather
than idling is right, but throwing the record away is how the NEXT recount forgets which spot just
failed.

This is the same line the file already records as having *"been swallowed by the comment above it"*
once. It was restored and then defeated by its own match radius, which nothing measured.

### 3. A CHEST APPROACH CELL WAS BLACKLISTED FROM 1.6 BLOCKS OUTSIDE IT

`Autopilot.EXACT_ARRIVED` is **1.6** and approach candidates are **one block apart**, so a body
parked anywhere near a chest "arrives at" every candidate the instant it is offered, judges it
un-openable without ever entering it, and burns through the 9x5x9 grid at recount speed. A cell is
only proved bad from INSIDE it: `Autopilot.arrivedAt(approach) && me.equals(approach)`.

**And it had mended its own watchdog by accident.** Blacklisting calls `stopGuiding()`, which nulls
the target — so the next recount saw a DIFFERENT approach cell, took the announce branch and reset
`fetchTargetSince`. `FETCH_STUCK_MS` restarted every cycle and could never accumulate, leaving the
arrival flag as the only route to "parked". Holding the cell until the body is genuinely in it keeps
the target stable, which is what lets the six seconds elapse. **One change, both halves** — which is
the tell that they were one bug.

### 4. A DEAD END IS A FACT ABOUT AN ANCHOR, NOT ABOUT A DESIGN

The frontier is one course of a window round the anchor, so *"nothing I can place here"* says
nothing at all about the other half a million cells. The log has the reset printing **23,672
placeable** from `Analyze` and reporting a dead end on the very next line — then parking beside it
for two minutes, teleporting, landing in the same place, and repeating until morning.

`Analyze.nearestPlaceable` answers *where IS the work* from the same whole-design pass `report`
already makes, restricted to what is CARRIED — flying to work we have no material for is the trip
that started the dead end. Asked ONCE per episode, because it is a full scan and the answer cannot
change while we stand still, and acted on only when the answer is genuinely outside the working
radius. **The reset was computing the one number that would have told it where to go, and printing
it rather than using it.**

### 5. A DETECTION THAT CHANGES NO BEHAVIOUR IS NOT A FIX

`Rally.land` has always NOTICED that the home teleport did not move the body, and said so — and then
printed the analysis and restarted the loop exactly as if it had worked. Three resets in one session,
each announcing `/visit enroz did not move us`, each followed by **byte-identical** analysis output,
on a doubling backoff. That is verbatim the failure its own docstring says it exists to end.

Two proofs and it stops sending the command: the forgetting still happens, the flight does not, and
the one thing that would fix it is named. `deadHome` clears the moment a teleport works, or one bad
minute disables the recovery for the session.

### And the printer's report was being thrown away by eleven early returns

`Printer.drainReport()` is **destructive** and is called at the top of `advance`; the station verdict
that consumes it is six hundred lines below, behind eleven `return`s. Every one of them discarded
real placements and refusals, and the next recount overwrote the field with a fresh empty drain — so
`Loop.stationFromReport` saw 0/0/0 and fell through to the stopwatch, **which is exactly the guess
the report exists to replace**. A station the printer was actively working could be abandoned and
then struck on that guess. Accumulated into `pendingReport` now, cleared only where it is CONSUMED.

### What the tests pin, and the trap inside writing them

`tests/StuckLoopTest.java` (9). Several assertions read the SOURCE, which is the honest form for a
rule whose whole content is *"this term is present"*: there is no state to inspect, and a snapshot of
the behaviour would pass a build in which the term had been quietly dropped again.

**And the first version failed on its own explanation.** The assertion forbidding `avoided.clear()`
matched the comment left behind to say why the call had been removed — *a check that forbids naming a
thing forbids explaining it*, which this file already records about the walk-gate tests. Comments are
stripped first, exactly as `RallyTest` and `AutopilotTest` already do.

Two working notes, both already on this page and both paid for again: **`Rally.java` is pure LF where
`Hud.java` is 2,269 CRLF against 474 LF**, so a patch anchor written with the wrong ending matches
nothing — the patcher fails loudly rather than silently no-op'ing, which is the only reason it was
caught. And a **heredoc past ~100 lines fails in this shell**; write the file, then run it.

### 737 Java tests, 0 failures. NOT FLOWN.

Everything above is unit-tested and log-diagnosed; not one line of it has been in the game. The
first thing to do with `chunkscan-0.9.8.jar` is watch whether the four-message cycle is gone — if
`next spot` / `not moving` / `giving up` still alternate at four-second intervals, the commitment
clock is not the whole story and the next evidence is `/cscan why` taken WHILE it is stuck.

### Still open, and it is the vision rather than a defect

Jack's actual goal, stated the same day: *"i give an account park complete, it goes and it builds the
entire thing including `/shops find owned (material)` purchases etc when it runs out of supplies."*

Two things stand between here and that, and the deadlocks above were only the first:

- **THE LOOP CAN ONLY GET MATERIALS FROM CHESTS IT HAS ALREADY SEEN.** `Loop.phase` has FETCH and
  DEAD_END and nothing between them. `craft`, `make`, `smelt`, `buy` and `farm` all exist and every
  one of them is a command a human types — none is reachable from the autonomous loop. The missing
  piece is an ACQUIRE phase: out of X, resolve how X is obtained, drive it, come back.
- **`provision` says 291,285 of 524,033 cells have their material.** The other 44% has no source at
  all, and `prices.json` is empty because the shop has never been walked, so `/cscan buy` is inert
  today. `Prices` is a passive lore-scraper that needs a human to browse a shop; `/shops find owned`
  is a server command and a far better mechanism. **Jack: it is a GUI**, which is the good case -
  `Withdraw`, `Crafter`, `Smelter` and `Prices` all already drive container screens, so a shop menu
  is the same shape as everything already built.

  What is NOT guessable is what is IN it: slot indices, item ids, and the exact lore a price and a
  location are hidden in. `/cscan screen` (`ScreenDump`) writes all of that down, once, so the
  driver is written against real slots rather than against a description - which is how every menu
  driver in this mod was written. **It snapshots on CLOSE, not on command, and that is not a
  convenience:** a container screen takes the keyboard so the command cannot be typed while one is
  open, and the contents arrive some ticks after the screen does, so a snapshot at open time is an
  empty menu. Both are the same reason `Prices` hooks `ScreenEvents.remove`. It never clicks - a
  shop menu is somebody's money - and its title is sanitised before it becomes a filename, which is
  the hole `/cscan fill ../../x` once opened.

