## The wiki closes the odds question (2026-08-30)

Jack sent minecraft.wiki's Tutorials index and pwouik's advanced-redstone resource gist. The gist
is an INDEX of learning material rather than data, and nothing was taken from it; the wiki's
`Tutorial:Randomizers` and `Tutorial:Item_sorting` both changed real code.

### A casino that does not know its own odds

`circuits.randomiser` took any N up to 8 and said, in writing, that it could not tell you the
distribution. **For a slot machine that is not a caveat, it is a bug** - a house that does not know
its odds cannot know whether it is losing money, and the whole point of `gen/casino.py` is that
the house must not be able to lose by accident.

The wiki gives an equal-probability figure for exactly two item mixes, and **the odds are a
property of the MIX, not of the wiring**: a dropper ejects a uniformly random one of its OCCUPIED
slots.

    2 outcomes, EQUAL   one stackable + one non-stackable            -> power 1 or 3
    3 outcomes, EQUAL   64-stackable + 16-stackable + non-stackable  -> power 1, 2 or 4

and, quoting the same page, extras make it lopsided: *"with two different stackable items and three
different non-stackable items, the RNG will output power level 1 40% of the time and power level 3
60% of the time"*. So those two mixes are the only ones on offer, **anything else RAISES**, and the
required items travel in the build's sidecar exactly as the sorter's filter stock does. A machine
built right and loaded wrong pays wrong.

### Two bugs the rewrite exposed, and one test that had been passing for the wrong reason

- **The randomiser's comparator was not reading its hopper.** Placed by hand, its BACK pointed away
  from the container it exists to read, so the machine could never have paid out. It is placed one
  step along its own facing from the hopper now, which makes the relationship automatic rather than
  remembered.
- **`test_a_press_pays_exactly_once` had been passing without stating a win.** The old randomiser
  passed the trigger straight through, so the test proved nothing about the machine; with a
  randomiser that genuinely gates on items it went red immediately. The win is STATED now, through
  `fill` - which is exactly the contract the simulator documents: *a container's fullness is an
  INPUT you state*. **The simulator has no entities and a test that hides that is worse than no
  test.**

### What the sorting tutorial confirmed, and what it did not settle

Confirmed, and now sourced rather than remembered: the filter hopper takes **1 target + 4 filler**;
the comparator's reading rises when the target arrives; the torch-and-repeater chain drives a dust
line that **locks the hopper below the filter**; and the mechanism rests on the rule that *"hoppers
search for an item to be taken from the input side BEFORE outputting an item to another
container"*.

Not settled: **what powers the bus in Jack's reference filter.** The inspection still reports "dust
with no source" on the reference ITSELF, which is either my model missing a path or the power
arriving from outside the exported region. The shipped lane remains a faithful copy of a build that
works rather than a mechanism this project can explain, and that distinction stays in the docstring.

