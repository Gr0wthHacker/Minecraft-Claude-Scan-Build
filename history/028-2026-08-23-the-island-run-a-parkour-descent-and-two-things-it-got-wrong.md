## The Island Run: a parkour descent, and two things it got wrong first (2026-08-23)

Jack's idea: jump pads from the top that wind all the way around, all the way down.

**THE FIRST BUILD WAS A STAIRCASE AND HE SAID SO** - *"this is a jumpable staircase, not
parkour, theres nothing challenging etc about it, no jump pads etc, this is crappy done"*. It
was: 77 landings of 3x3, four blocks apart, two-course drop every time. Every jump identical,
every landing forgiving, no failure mode, and no slime anywhere - because I had argued myself
out of jump pads on a physics point about winding. **A ramp with gaps in it is not parkour.**

What makes a descent a course is a VOCABULARY, in a rhythm, getting harder as it goes:

| move | what it is |
|---|---|
| LEDGE | a **one-block** landing, 3 to 4.5 out and nearly level - the sprint jump is the game |
| PLUNGE | a real 8-16 course fall onto a **slime** pad, which bounces and cancels the damage |
| GATE | a wall on the landing, so the jump clears something as well as reaching it |
| REST | a 3x3 lit checkpoint - the only place the run lets go of you |

**The plunges are what make the ledges hard.** Steering a fall buys ~2.0 blocks of reach for a
two-course drop and ~5.0 for a thirteen-course one; one turn of this island is ~270 blocks of
travel against ~150 courses to spend. Descend by little drops and you spend all the height on
distance and every jump is trivial - which is exactly what the first build did. Spend the
height in a handful of plunges and the ledges stay level, so they have to be JUMPED.

`configs/island_run.yaml`, `gen/parkour.py` - **97 moves, 273 blocks, 0 problems, overlap 0.**
Y194 to Y48, **2.1 turns**, 62 ledges, 13 slime jump pads, 15 gates, 7 checkpoints. Ledge gaps
2.2-4.5 with **42% at full sprint distance**, and no move anywhere costs health.

### The plot is a square, it is FOUND, and the first build went over it

Jack: *"some go over the edge of our 99x99 boundary, no blocks should go further out than
something we've placed, you can find the 99x99 area by locating the bedrock and moving around
it."* The run had **120 cells outside it**, up to 51 out.

The guard was checking the CAPTURE box - 103x103, two blocks wider on every side. **The capture
is how much of the world we photographed; the plot is how much of it is ours.** `mcbuild/plot.py`
now finds the island's bedrock at **(-24200, 200, 30000)** and measures 49 out on each axis, and
the evidence agrees exactly: all placed content spans X -24249..-24151 and Z 29951..30049, 99 by
99. It is a SQUARE, not a circle - a route at radius 52 is legal on the diagonals (49*sqrt2 = 69)
and three blocks over the line at the cardinals, so a radius check would either waste the corners
or overrun the sides.

### Three more things this cost

- **PASSABLE IS NOT EMPTY - for the second time in one session.** The landing test allowed vine
  and grass because the HEADROOM test does, and two pads shipped on top of Jack's vines. The
  landing course is tested for AIR now and the courses above it for passability.
- **TWO DESIGNS CANNOT SEE EACH OTHER.** A 1x1 ledge in the void is a walkable surface, so the
  night pass solved it - by putting **14 lanterns in the cells you have to land on**, breaking
  fourteen jumps. Neither design was wrong on its own. The fix is that the landing IS the lamp:
  every ledge is a froglight, which needs no extra fixture, removes the conflict, and lets you
  see the next jump in the dark. The night pass went 120 -> **105** fixtures as a result.
- **SLIME IS EXPENSIVE HERE**, and 13 blocks blows the repo's 8-block ceiling on expensive
  materials. It is declared rather than smuggled: `expensive_allowance: 13` sits in the config
  with the reason beside it, because slime IS the jump pad and no cheap block cancels a fall
  (hay cuts damage 80%, honey 20%). 13 blocks is 117 slimeballs against the 193 in store.

