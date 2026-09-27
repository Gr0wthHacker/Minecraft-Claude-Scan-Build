## A real casino, and the third schematic format (2026-08-30)

`reference/` now holds six outside builds. Two of them changed the picture.

### `casino_chirurg.litematic` — what a redstone casino actually is

**135x75x105, 185,198 blocks, 774 palette states, 5,000 redstone cells.** Ours was a 24-block
"slot machine". Theirs has 513 repeaters, 468 comparators, 404 hoppers, 329 observers, 300
droppers and **303 note blocks** - sound is a whole dimension of a casino and `gen/casino.py` had
none of it.

**AND A QUARTER OF IT CANNOT BE BUILT HERE.** Priced against this server's economy: 67.5% cheap,
7.4% ok, and **25.2% expensive - 46,609 blocks**, almost all of it quartz (25,054) and stained
glass (14,500). The aesthetic of a casino is quartz and coloured glass, and on this island that is
not a palette, it is a wish.

So the substitution has to be done properly, and doing it exposed two traps this file already
knew about:

    quartz_block          -> pearlescent_froglight   CHEAP BY THE TABLE, and this island holds ZERO
    black_stained_glass   -> black_shulker_box       a CONTAINER, admitted as skin

The first is rule 12 - *ask the world, not the table* - and the second is the `bee_nest` trap, via
the `shulker_box` gap this file has had listed as open under `rubric.FUNCTIONAL` for weeks. Both
are closed: `shulker_box` is in FUNCTIONAL now, and `palette.affordable_like` applies **three**
gates rather than one - cheap by the table, WITNESSED on this server, and not a machine. It
returns `(None, None)` rather than a bad substitute when nothing survives.

    quartz_block         -> white_wool   (24)
    black_stained_glass  -> black_wool   (10)
    snow                 -> snow_block   (0)

**A LIGHT CANNOT BE SUBSTITUTED BY COLOUR.** `sea_lantern -> birch_log` at distance 85 and
`redstone_lamp -> acacia_planks` at 50 are what a pure colour match gives you, and both are wrong
in KIND. A lamp is replaced by a lamp or not at all.

### The pre-1.13 format, and a reader that admits what it cannot see

`mcedit_1216.schematic` is the OLD MCEdit format: numeric block ids, no palette, orientation in a
parallel `Data` nibble array. `sponge.load_mcedit` reads it against a table of ~80 ids, and **an id
outside the table becomes `unknown_<id>` rather than a guess** - a reader that renders an unknown
id as stone produces a build that looks imported and is wrong, and nothing downstream can tell.
This file had exactly one (id 128) and it is named.

**But the orientation is not decoded**, and run blind that produced **66 direction findings, every
one of them about the reader rather than the build**. Rather than guess the nibble convention -
this session has been bitten twice already by guessing an orientation rule - the inspection now
DETECTS the situation: if not one directional component in a model carries a facing, the direction
checks are skipped and **the reason becomes the finding**. 73 -> 2, and the one that matters names
the reader's own limit.

### Where the calibration stands

| build | findings |
|---|---|
| item filter | 1 |
| bonemeal farm | 1 |
| contraption 31323 | 1 |
| contraption 24829 | 1 |
| casino (185,198 blocks, 5,000 redstone) | 37 |
| mcedit (orientation unknown) | 2 |

37 on the casino is **0.7% of its redstone components**, and a human-made build that size genuinely
has leftovers. Chasing it to zero would be buying quiet by going blind, which is what
`test_our_own_broken_lane_is_still_caught` exists to prevent.

### Still open

**The casino theme is still my invented module list**, now known to be a toy beside the reference.
Rebuilding it on what a real casino contains - and on a palette this server can actually buy - is
the next piece of work, and it is a design decision rather than a bug fix.

