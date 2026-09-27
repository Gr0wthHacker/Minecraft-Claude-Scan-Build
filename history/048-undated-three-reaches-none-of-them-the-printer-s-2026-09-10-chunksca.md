## THREE REACHES, NONE OF THEM THE PRINTER'S (2026-09-10, chunkscan 0.9.10)

Jack: *"constantly the bot when trying to place is 1 or 2 blocks out of reach and cant place and
just sits there."* Diagnosed off `latest.log` in twenty minutes - the fourth session running where
the answer was already written to disk - and the cycle is in it verbatim, at four-second intervals
for ninety seconds:

    15:49:00  2 cell(s) placeable from right here - staying until they are in
    15:49:03  built-in printer: enabled; 0 placed, 0 wrong state, 0 refused
    15:49:03  target 97587 204 80451  0m                     <- AT the target
    15:49:06  2 cell(s) in reach but nothing placed for 5s - moving
    15:49:12  nothing placed here in 5s - moving in closer
    15:49:18  9 cell(s) placeable from right here - staying until they are in
    ...
    15:50:20  every angle on this spot has been tried and nothing was placed - giving up on it
    15:51:02  STALLED - nothing placed in 90s. 0 spot(s) finished

### THE WORD "REACH" MEANT FOUR DIFFERENT THINGS, AND ONLY ONE OF THEM WAS THE PRINTER'S

    the vicinity hold   Loop.focus(me, VICINITY=4)      a sphere on the FEET, no eye, no face
    the stand chooser   Plan.coveredFrom, eye -> CENTRE  at reach - slack
    the orbit ring      w.pos().distSqr(c)               FEET to centre, no sight line at all
    THE PRINTER         eye -> the click point           on the SUPPORT'S FACE, at REACH 4.2

**A CLICK LANDS ON THE SUPPORT, NOT ON THE CELL.** `placement()` clicks the neighbour that holds the
cell up, on the face they share - so the point that has to be inside the arm is on the cell's
BOUNDARY, and which boundary depends on which neighbour is solid. Every other measure used the
centre, which is up to half a block wrong in whichever direction happens to matter.

**And `everPlaceable`'s own docstring says why nobody noticed.** It is documented as `placement()`
*"with the two things that depend on WHERE YOU STAND removed - the reach and the eye ray - so it
answers about the cell rather than about the moment"*, which is correct and is what the frontier
needs. What it left is a MOMENT owned by nobody: three callers each invented one, and the hold's
list - named `inReach` - applied no reach test at all.

**Measured over the vicinity sphere the hold actually uses** (257 cells, r=4 on the feet):

| | |
|---|---|
| reachable if the support is on the best face | 248 (96%) |
| reachable whichever face the support is on | **191 (74%)** |
| no face reachable at all | **9 (4%)** |

So a quarter of the sphere is a coin toss on which neighbour is solid, and 4% is never right. And
**the commonest case is worse than any of that**: a floor course is supported from BELOW, so the
click lands on the cell's own BOTTOM face, a whole block further from the eye than its top -
**three courses down is already out of the arm and VICINITY reaches four**. A body hovering over
paving it has come to lay is exactly the shape of "sitting there": the cells are real, carried,
supported, and a metre past the fingertips.

That is also why the two mechanisms fought. The hold said *stay, these are placeable*; the station
said *nothing placed, move in closer* - and moved to another spot chosen by the same centre
measure. Neither was wrong about what it measured. **When two correct mechanisms produce a loop the
fix is to notice they are answering the same question**, and here the question was one neither of
them was asking.

### ONE SOURCE, WHICH IS THE RULE THAT WAS HALF-KEPT

`Printer.clickPoint` is the geometry, factored OUT of `placement()` rather than paraphrased beside
it, so the loop measures against the identical point the printer clicks. `clickPoints` answers per
CELL and does not depend on where you stand, which is what makes a real test affordable inside a
search over several hundred candidate positions - the caller memoises it per cell and the stand
chooser then costs distances, not block lookups.

- **the hold** filters by it, so `inReach` means it and the station machinery gets its turn at once
  instead of after a five-second dead hold;
- **`Plan.coveredFrom`, `bestStand`, `groundStand` and `ring`** take the same predicate, so "move in
  closer" and "the next angle" land somewhere that works. `ring` had a THIRD measure - feet to
  centre, no sight line, no reach - and now shares `coveredFrom` with the rest;
- **a null predicate is the old measure exactly**, so no other caller moved.

**THE CHEAP BOUND IS KEPT AND IS SOUND.** The scan still rejects a cell whose CENTRE is beyond
`REACH + 1` before asking the real question, because no point on a cell's surface is more than a
half-diagonal (0.867) from its centre - swept over a 19-cube rather than argued.

### AND THE DIAGNOSTIC COULD NOT SAY "OUT OF REACH"

The scan's own gate was that 5.2-to-centre bound, so everything between it and the true 4.2 fell
into `no legal placement from here`. **Measured: 30% of the cells the scan looks at.** That reads
as a cell that can never be built when it is a cell a metre out of the arm - the first is the
design's problem and the second is the loop's, and the printer had no way to say which.

The stall message was two guesses (*"Out of reach, or the spot cannot be built"*) printed directly
under a comment claiming the tick knows which. It does, and it says so now.

`tests/ReachTest.java` (9) pins the arithmetic rather than the behaviour, because the arithmetic is
the whole of it: the eye offset, the four-courses-down case, the floor case, the far-side straddle,
the slab clamp, the soundness of the cheap bound, and that the predicate is actually consulted -
**verified red by putting the fix back out**, which is this file's own standing rule about a
contract that passes the fault it was written for. 761 Java tests, 0 failures.

**Still open, and it needs a flight rather than a guess.** The same log has the printer reporting
`0 placed, 0 refused` while its own scan recorded no rejected cell, which can only happen if
`place()` returned before `attempts++` - the `slot >= 9` hotbar-swap path is the one branch that
does, and `swapSlot` always picks the FIRST hotbar slot holding a block, so two materials both
wanted can in principle ping-pong one stack in and out for ever placing nothing. It was not the
cause of the window above (the swap message is timestamped seven minutes later) and it is not
guessed at here. `/cscan why` while it is sitting still now names the reason; read that first.

