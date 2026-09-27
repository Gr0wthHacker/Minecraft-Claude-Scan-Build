## Two reference builds, and the mistake they caught (2026-08-30)

Jack supplied a working four-lane `item_filter.schem` and a bonemeal farm with a shulker loader.
They are checked into `reference/` and they earned their place immediately.

### Reading the OTHER schematic format

`mcbuild/sponge.py` reads WorldEdit `.schem`. Everything here speaks Litematica because that is
what chunkscan writes, and **a reference build that cannot be opened is a reference build nobody
learns from** - the same reason `tools/corpus.py` exists. Two things to get right: **the block
array is VARINT-packed, not bit-packed**, and **Sponge's palette is NAME -> INDEX, the reverse of
Litematica's list** and not necessarily in index order, so it is built by position. Read in the
wrong order it silently relabels every block and looks like a clean import of a different build.
`load_any` decides by CONTENT, because a file called `.litematic.gz` is still a litematic.

### THE SORTER'S COMPARATOR WAS RIGHT, AND I TURNED IT ROUND

Earlier the same day the circuit inspection reported `comparator reads nothing` on the item sorter,
and the general rule - *a comparator reads what is behind it* - was applied to flip every lane's
comparator to face away from its hopper. **The rule is true and the inference was wrong.**

The reference settles it in one minute: the comparator sits beside the filter hopper and faces
INTO it. It is not reading the hopper, it is **driving** it - a comparator's output locks a hopper
- and its own input arrives from BEHIND, off a smooth-stone block that a wire bus weakly powers.
The wiki's own rule is what makes that legal: a weakly powered block *"cannot power adjacent
redstone dust, but can still ... power redstone repeaters and redstone comparators facing away from
the block"*.

So the original orientation was correct; the lane's real fault was that it had nothing behind the
comparator and **no lock line at all**. The whole lane is now copied cell for cell from the
reference - torch, repeater, stone, glass, bus - and `tests/test_circuits.py` compares the
generated lane against the reference FILE rather than against anybody's memory.

**Reasoning got this backwards twice and a reference build settled it immediately.** That is the
strongest argument yet for the corpus discipline this file already recorded: outside builds are
the only non-circular evidence this project has.

### Calibrating the inspection against builds known to work

Run over the bonemeal farm - a machine that demonstrably works - the inspection returned **74
findings**. Almost all of it was noise, and fixing that is worth more than any new check:

- **62 quasi-connectivity lines, one per component.** A piston machine is pistons with things over
  them; that is what one looks like. One counted line now, with an example. A per-cell warning that
  fires on every cell of a working build is how a real finding gets scrolled past.
- **Seven "piston is not wired" on pistons a real build fires from above.** QC is MODELLED now, so
  it counts as wired.
- **Five findings within one cell of the file boundary.** Every finite cut truncates something -
  the audit already knows this about captures - so `near_edge` separates a cropping artifact from a
  fault. 74 -> 13, of which 5 are edge.

And the seven that remain are a REAL LIMIT, now written into the module: **anything driven by a
MOVING redstone block is invisible to static inspection.** They are one row at a single course,
no wire, no observer, nothing overhead - a redstone block a piston pushes along, which is how half
the compact farms in the game work. At rest the driver is not next to the thing it drives.

### Still open

**The sorter has not been tested in game, and the lane is a copy rather than an understanding.**
The bus's power path is not derivable from a static snapshot - the inspection still says "dust with
no source" on the REFERENCE itself - so what is shipped is a faithful reproduction of a build that
works, not a mechanism this project can explain. Place it and put an item through it before
trusting it. That is a much better position than the invented lane it replaces, and it is not the
same as verified.

