## The casino, rebuilt against the reference — and it does not fit (2026-08-30)

### THE REFERENCE CASINO IS BIGGER THAN A SKYBLOCK PLOT

135 x 105 against a 99 x 99 plot: **36 over on X and 6 over on Z.** Jack: *"it cant be bigger than
99x99 ... but we can go vertically higher and much lower"*, and that is the whole shape of the
answer - the same volume is **1.45 floors** stacked, and Y-64 to Y320 is 384 courses of room.

So the theme carries a `floors` plan rather than sprawling, and **a module wider than the plot is
reported as impossible up front** rather than after a full pad search: "NO SITE" reads like awkward
ground, when the truth is that the design can never fit at any position.

### The game, rebuilt

The first `slot` was 24 blocks. One of the reference's games is 16x12x16 with 97 wire, 27
comparators, 27 repeaters, 22 observers, 29 lamps, 16 note blocks and 27 signs. Three structural
things were wrong and all three are fixed: **the machine lives under the floor** (the reference has
two redstone layers with a play floor over them), **the display is the game** (nearly half of a
machine is coloured wool and lamps), and **sound** (303 note blocks there, none here).

**A quarter of the reference cannot be built on this economy** - 46,609 expensive blocks, almost
all quartz and stained glass - so the palette is re-derived through `palette.affordable_like`:
`quartz_block -> white_wool` (24), `black_stained_glass -> black_wool` (10). The board COLOURS
needed no substitution; they were already cheap, and the board is the part that matters.

**Two things are budgeted rather than substituted.** `redstone_lamp` and `note_block` are both
expensive, and their nearest cheap colours are `acacia_planks` and `soul_sand` - a lamp that does
not light and a note block that makes no sound. **A light cannot be substituted by colour.** They
are counted into `budget` and the count reaches the plan: 120 lamps priced out as 480 redstone (in
stock) plus 120 glowstone, of which **214 dust was short**. A shopping list, not a shrug.

### THE BAR DISPLAY DOES NOT SHIP, AND THAT IS THE POINT

The idea is sound - the outcome is an analog level, wire loses one per block, so a dust run reads
it off as a bar. Three attempts did not get a signal from the pit to the board:

1. **`connect` IS PLANAR and said so nowhere.** It lays an L path at ONE height and quietly never
   climbed the six-course pit. `circuits.climb` was written for this and is keeping regardless: a
   vertical run is a staircase of step blocks with dust on each, and it needed to exist.
2. **The lamps sat on the back wall, diagonal from the bus.** Diagonal is not adjacent.
3. **The riser shared cells with links already laid**, so `w.has` skipped its STEP BLOCKS and left
   dust stacked on dust, which connects to nothing. Rerouting it sideways did not fix it either.

At that point the honest move is to stop. `display: False`, the reason recorded in the config, and
a test that asserts the build SAYS the board is not wired. **A display that looked like a readout
and was not would be exactly the failure this subsystem exists to prevent** - it would pass the
audit, the bill of materials and the eye. What ships is the machine, and its contract is verified
by simulation: one press, one payout, never zero and never twice.

### Planning onto another island

`mcbuild plan --island <name>` takes the plot from the island REGISTRY rather than from the
capture's own bedrock, so a capture holding two islands cannot pick the wrong square. The games
report NO SITE on the main island, which is correct - CLAUDE.md has said for weeks that the plate's
largest genuinely flat area is 13x13, and a game wants 12x10 clear.

### The runbook for the fresh plot

    /cscan casinoisle                                   # in game, on the NEW island
    python -m mcbuild islands --add casino --from <capture> --owner <alt>
    python -m mcbuild plan "redstone casino" --world <capture> --island casino
    python -m mcbuild plan --approve casino             # THE GATE
    python -m mcbuild plan --emit casino
    python -m mcbuild fleet --assign casino --accounts A,B,C
    # then on each alt:  /cscan fleet work

