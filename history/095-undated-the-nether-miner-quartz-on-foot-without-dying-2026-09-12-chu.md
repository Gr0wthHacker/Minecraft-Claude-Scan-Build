## The Nether miner: quartz, on foot, without dying (2026-09-12, chunkscan 0.9.11)

Jack: *"we need an autonomous miner so we can mine quartz in the nether, fill our inventory
(avoiding lava + dying); we can only walk/run/jump in nether (and place blocks as necessary) but
cant fly; find quartz, fill inventory with it, store it, and do it again."* Branch tunnel and a
teleport escape were his calls, taken over the safer options offered.

```
/cscan mine <radius>          start where you stand, facing where you face
/cscan mine off               stop, and say what it got
/cscan mine escape <command>  how it gets out of trouble; defaults to Rally's home
```

**EVERYTHING IT NEEDS ALREADY EXISTED.** `Nav.standable` is a grounded router, `Autopilot` walks,
`Digger` breaks one watched block at a time, `Printer` places one, `ContainerInteraction` opens a
chest. `Digger.tick` even takes a `List<BlockPos>` — a design's dig list is only what the caller
passes it — so the miner feeds it a scan-derived list and inherits every existing refusal rather
than getting a second, weaker digger. What was missing was the CYCLE and **three gates that would
each have made it do nothing, in silence.**

### TWO OF THE THREE ARE NOT ABOUT MINING, AND ONE IS WRONG ON THE ISLAND TOO

- **`VoidRisk.under` SEARCHED FOR A BLOCK THAT `blocksMotion()`, AND LAVA DOES NOT.** `Nav`'s own
  comment says so in as many words. The search walked straight past a lava lake, found the bedrock
  underneath it and returned CAUGHT — so `Digger`'s one loss-preventing gate cheerfully approved
  every block whose drop burns. On the island that was nearly unreachable; in the Nether it is the
  normal case. `Verdict.BURNED` now, refused like the void, and `warn()` says which. It is the same
  class as the three separate times this file records a classifier reading "not air" as "solid" — a
  fourth costume for it.
- **`Islands.Gate` AUTHORIZES ONLY THE RECORDED PLOTS, AND AN ISLAND IS AN X/Z RECTANGLE WITH NO
  DIMENSION ON IT.** In the Nether every cell is outside every plot, so `judge` answers OFF_PLOT for
  all of them: no swing, no error, nothing to read. The fix is NOT to weaken the plot gate — on the
  island it is the only thing between a dig list and somebody's build — it is to make the
  authorization explicit where the registry has nothing to say. `Digger.authorize(min, max, dim)`
  replaces the plot gate while it is set, **and only in its own dimension**: a box is coordinates,
  and coordinates mean nothing without a world. `reset()` clears it, so a design dig can never
  inherit a miner's box.
- **The walk gate refused.** `Autopilot.walk` steers on foot only toward a fetch or a landing. That
  rule's real content is *only walk where there is ground*, and the void is the ISLAND's hazard
  rather than a universal one — in the Nether what kills you is lava, which no amount of refusing to
  walk would have helped with. A mining stand is the third floor, and the ground condition the gate
  actually turns on still runs for all three.

### The lava model: the client can see behind the wall

**THAT IS THE ENTIRE EDGE OVER A HUMAN.** A person branch-mining dies to a pocket they had no way to
know about; this mod holds every block of every loaded chunk, the ones behind the rock included. So
the guard is not "react to lava" — by then you have ten ticks. Three layers:

1. **Segment pre-clear.** `LavaGuard.scan` over the next `LOOKAHEAD` cells of corridor before any of
   them is committed to. Lava within `SEGMENT_CLEAR` → turn, and say what it saw.
2. **Per swing.** Six neighbours plus the cell above, re-checked in `Digger.judge` immediately
   before every break, because chunks load and the world moves between one plan and the next.
3. **Reaction**, which has to be immediate: **Nether lava spreads one block every 10 ticks against
   the Overworld's 30.** Half a second of deciding is two blocks of flow.

Three rules inside it, and the middle one is the opposite of what the router does:

- **`lava` IS MATCHED EXACTLY, NEVER AS A SUBSTRING.** `Rules.isProtected` matches substrings on
  purpose — `gray_wool` is protected because `wool` is in the list — and the same trick here makes
  `lava_cauldron`, a decoration, read as lethal and refuses every corridor near a brewing room.
- **UNLOADED IS UNSAFE HERE.** `Nav` counts an unloaded chunk as PASSABLE, deliberately, because
  refusing to route through one fails every long flight. For DIGGING the identical fact means the
  opposite: a cell we cannot see is a cell whose lava we cannot see. **Routing is optimistic because
  a wasted flight is cheap; mining is pessimistic because a wrong answer is the inventory.**
- **A falling block overhead is the same class of death** — gravel is common down there and a column
  of it on your head in a one-wide corridor is suffocation. Asked of the GAME (`FallingBlock`)
  rather than of a name list.

Distance is **Chebyshev**, a cube rather than a sphere: it over-refuses slightly at the corners, and
that is the correct direction to be wrong in.

### Three bugs found reviewing my own work, all the same shape

Each is a job that sits perfectly still while every watchdog in the mod reports it healthy, because
nothing is travelling and nothing is failing.

- **THE CORRIDOR HAD NO REASON TO TURN AT THE EDGE OF ITS OWN BOX.** Past the boundary the digger
  answers OFF_PLOT for every cell — correctly — so the plan stays full, no swing lands, and only a
  LAVA threat could turn the corridor. The miner would have stood at the edge of its own working
  area refusing its own work for the rest of the session. The box edge turns it now, exactly as lava
  does.
- **A CORRIDOR THAT OPENS INTO A DROP IS ONE THE MINER WALKS DOWN.** A tunnel breaking into a cavern
  is the normal way a Nether corridor ends, and what is at the bottom of one is routinely the lava
  the rest of the class exists to avoid. It bridges, and after `BRIDGE_TRIES` it treats the drop
  exactly like lava and turns.
- **ENTERING THE STASH LEFT THE DIGGER HOLDING ITS BLOCK.** Nothing ticks the digger while the stash
  runs, so its target stayed set, and `AutomationControl.blocksMovement` pins the body while the
  digger is busy — right for a swing, fatal for a trip. The miner would have stood at the face with
  a full pack, unable to walk to the chest it was trying to reach.

### Smaller decisions worth keeping

- **The deposit rule is a KEEP list, not a deposit list.** A deposit list silently leaves behind
  anything nobody thought of, which over a night is a pack of gold nuggets and a miner that believes
  it is full and cannot empty itself. Tools, food, buckets, boxes and one stack of netherrack stay;
  everything else goes in.
- **The face goes LAST in the dig list.** `Digger` takes the first cell in reach and never the last
  while any other remains, so ore is always stripped before the corridor moves past it — which is
  the whole point of a branch tunnel, and it needed no new code.
- **A vein unravels itself.** Only EXPOSED ore is offered, so taking the front block exposes the one
  behind it on the next pass: no vein-following, no dig-in depth to tune, and no way to chase a seam
  out of the working box.
- **THE ESCAPE IS PROVED.** Jack picked the teleport over walling in, and the one thing that can go
  wrong with a command is that it silently does nothing. `Rally` has that scar already — *"a
  teleport that did not teleport is a silent no-op"* — so this records where the body was, compares
  after the landing, and a command proved twice not to move us is not sent a third time. The
  fallback is then the thing that needs no server at all: wall in where it stands, and SAY that,
  rather than reporting an escape that did not happen.
- **A turn re-origins on the STAND the corridor reached, never on the body.** The body lags the plan
  — it is walking, and may be most of a corridor behind after a stash trip — so re-origining on it
  would start a branch in the middle of the last one, from a different place every time the same
  decision was taken.
- **It is deliberately NOT persisted across a relog.** Every other job here resumes its intent from
  `session.json`; this one holds a box, a heading and a stash position, and all three are
  coordinates. Resuming a job that swings a pickaxe into a world that has moved is the dangerous
  direction, and typing the command again costs nothing.

`LavaGuardTest` (15) is pure geometry with no client in it — `Cells` is a functional interface, the
shape `Nav.Passable` and `Burial.Solid` already use. `MinerTest` (29) covers the corridor geometry,
the fullness reserve, the keep rule, the turn order, the escape proof and the digger's
dimension-scoped authorization. **805 Java tests, 0 failures.**

`AutopilotTest.buildingRequiresFlightAndOnlyAFetchMayWalk` failed on the walk-gate change, which is
its job — it pins a DECISION and this session reversed part of it. It moved in the same commit and
got stronger rather than looser: it now asserts the list is still CLOSED and that the ground
condition survived, which is the half that actually keeps anybody alive.

### Still open

- **NOT FLOWN. Not one line of this has been in the game.** Everything is unit-tested and every API
  was read out of the real source rather than remembered, but a corridor that is actually walkable
  and a chest that actually takes a shift-click are things only a session can say.
- **Run `/cscan mine escape <command>` once by hand before leaving it.** Whether a warp works from
  the Nether on this server is the one fact nothing offline can settle. The proof makes a failure
  loud rather than fatal, but a command that works is better than a fallback that fires.
- **The stash must be a chest within 12 blocks of where you start**, or it refuses and says so. It
  finds one itself rather than making you name it.
- **Ghasts and piglins are not modelled.** A corridor is inherently safe from both; the open cavern
  a tunnel breaks into is not, and the only answer there is the health gate and the escape.

### The miner, audited before it ever flew (2026-09-12, chunkscan 0.9.12)

Jack: *"audit and make improvements."* Nine findings, read adversarially off code written an hour
earlier. **Every one would have shipped**, and the three worst are the same shape this project keeps
writing rules about: a job standing still while every watchdog reports it healthy.

- **THE EMERGENCY FALLBACK PLACED ONE BLOCK OF NINE.** `wallIn` looped over the shell calling
  `Printer.place` — and `place` opens with `if (busy() || ...) return REFUSED` where `busy()` is
  `!pending.isEmpty()`. **The second call in a tick and every call after it is a no-op until the
  first placement is acknowledged.** Nine calls in a for-loop read exactly like a wall going up and
  built a single block, in the one routine whose entire job is to work when everything else has
  failed. It is one block per tick now, re-deriving what is still open each time so it cannot
  double-place or stop early.
- **GOING AND OPENING FLIPPED BETWEEN EACH OTHER FOR EVER, IN SILENCE.** `GOING` sees the body is
  already within reach of the approach cell and hands to `OPENING`; `OPENING` cannot get a hit on
  the chest — broken, blocked, or an approach cell that is not actually in reach — and hands
  straight back. Every tick, for the rest of the session. **No watchdog in this mod can see that,
  because the job believes it is making progress the whole time.** Every leg of the trip has a clock
  on it now and `step()` is the only way to change leg, so a leg cannot be entered without starting
  one.
- **NOTHING HAD A CLOCK ON THE DIGGING.** The stash got one and the escape had one; the actual
  mining had none at all. A body that cannot reach its own stand, or a face the digger refuses for a
  reason that is neither lava nor the boundary — a protected block, a tool that will not break it —
  is a miner standing still with a full plan and a healthy-looking state. It turns away after 45
  seconds of producing nothing, and `TURN_LIMIT` is what eventually calls the box finished.

Three more that were wrong rather than silent:

- **THE PLAN OUTRAN THE BODY.** In an open cavern every face is already air, so `depth` advanced
  once per replan — four ticks — while the body walked half a block. The corridor ran off into
  unexplored dark dragging a target the body could never catch, and because a turn re-origins on
  the STAND, the next branch would have started somewhere nobody had ever been. The advance is
  gated on arriving.
- **THE TURN SEQUENCE NEVER TRIED ONE OF THE FOUR CARDINALS.** It rotated from the heading it had
  just abandoned, so clockwise-then-anticlockwise from the NEW heading is the ORIGINAL one again:
  the run went `cw, back-to-start, opposite` and inside `TURN_LIMIT` the anticlockwise heading was
  never reached. It rotates from a base fixed at the first turn of the run.
- **THE TOOL SWAP WAS RE-SENT EVERY REPLAN.** A `SWAP` is not synchronous, so a swap still in
  flight looked exactly like one that had not been asked for — which is how a stack ping-pongs in
  and out of the pack for ever without a block being broken, a failure this project already has on
  record for the printer's own hotbar swap. Rate-limited, and the miner no longer swings while the
  hotbar has nothing but a bare hand in it: `usablePick` asks the hotbar and the pack as separate
  questions.

And three smaller ones:

- **A SUCCESSFUL ESCAPE REPORTED AS A FAILURE.** The dimension check runs first, so a teleport that
  worked well enough to leave the Nether halted as an unexplained dimension change and the command
  never got the credit — which matters, because two failures retire it. A new world while a
  teleport is in flight is the proof it worked.
- **A REFUSED BRIDGE BURNED AN ATTEMPT.** `Printer.place` returns `REFUSED` while it is still
  holding the last placement; counted as a try, three in a row gave up on a drop nothing had
  actually tried to bridge yet.
- **THE FOOD RULE CARRIED A DEAD CLAIM.** `keep` said food stays *"because eating is how the health
  gate is survived"* and **nothing anywhere eats.** Implementing it needs the use-key held with a
  food item selected and nothing targetable in front of you, which is a real risk of right-clicking
  something by accident for a feature nobody asked for. The claim is corrected instead: food stays
  because it is yours and not the miner's to spend, and a long run ending on health is now in the
  open list rather than hidden behind a comment that described behaviour that did not exist.

**And one that was only ever a cost.** `LavaGuard` asked the world for a block NAME per cell — a
registry lookup and a string compare — over ~800 cells per replan and 150 per tick for the body
check. Nothing in it ever needed to know which block it was looking at, so `Cells` is three
booleans now (`loaded`, `lava`, `falls`), the body check is the twelve faces of the two cells a
player occupies rather than a radius-2 box, and `isLava(BlockState)` is the single definition that
`VoidRisk` asks too — so the digger and the drop check cannot come to disagree about what lava is,
and neither pays a lookup to find out.

**816 Java tests, 0 failures** (55 of them the miner's). Still NOT FLOWN.

