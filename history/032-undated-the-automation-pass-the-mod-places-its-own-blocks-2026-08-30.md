## The automation pass: the mod places its own blocks (2026-08-30, chunkscan 0.4.0)

Four more, off the back of Jack confirming automation is allowed on skyblock.net.

| | |
|---|---|
| `/cscan print <design>` | place the design OURSELVES, and verify every block landed |
| `/cscan make <item> <n>` | craft it, with a crafting screen open |
| `mcbuild cheapen --by-price` | palette by the shop's real prices, not the invented tier table |
| `tools/timelapse.py` | the island being built, from the captures you already took |

### The printer, and the signal this loop has never had

This file said, as a technical fact, that *"a client mod cannot place a block, and should not"*.
**Only the second half was ever true**, and it was a statement about server rules rather than about
the client — litematica-printer places blocks from a client exactly as `Printer.java` now does.

**THE POINT IS NOT SPEED, IT IS FEEDBACK.** Delegating placement left the loop with no signal at
all — this file's own words: *"the printer never reports back, so `todo` shrinking is the only
honest evidence a block was placed"* — and FOUR stall clocks, an abandoned-station set, a
thrashing detector and a whole recovery ladder exist to paper over that silence. A placement made
here is read back off the world a few ticks later, so the loop finally knows the difference between
*it did not work* and *I have not looked yet*.

**Placement and verification are separated by ticks on purpose.** The server has to answer first;
reading the same cell in the same tick would report every placement as a failure.

Three things it has to get right, and the first is the one a picture cannot check:

- **THE STATE IS VERIFIED, NOT ASSUMED.** `facing` comes from where the player is LOOKING at the
  moment of placement and `half`/`type` from where in the clicked face the hit landed — so both are
  computed and the look angle is set before the click. A stair aimed the obvious way comes out
  BACKWARDS (the game derives a stair's facing as the player's own direction reversed), and **our
  renderer draws both directions identically**, which is why `PrinterTest` asserts the yaw table
  rather than anyone eyeballing a flight. A cell whose block is right and whose state is wrong is
  reported as a MISMATCH and never counted as built.
- **It never breaks anything.** Placement goes into air only; `Rules` and the 99×99 `Plot` still
  apply. Replacing stays a separate, explicit job with its own dig list, because breaking the wrong
  block on a lived-in island is the one mistake with no undo.
- **A cell that fails twice is left alone and reported** — `Ignored`'s rule for places, applied to
  cells. One failure is a bad moment; two is a property of the cell.

It uses what is in your **hotbar**, because that is what a click places, and says so once per
material rather than once per tick.

### `/cscan make`, and the data that could not craft

`craft` said *"craft 87x powered_rail from 522 gold, 87 sticks, 87 redstone"* and then left you
clicking for twenty minutes.

**THE GRID IS THE WHOLE DIFFICULTY AND THE COST DATA DID NOT HAVE IT.** `needs` is an aggregate —
six stone bricks — which is everything a COST needs and not enough to CRAFT: six bricks anywhere in
the grid do not make stairs. The extractor keeps the real 3×3 layout now, for **1,056 of the 1,524
recipes**, anchored top-left where the game matches a shaped recipe from.

`Crafter` drives the screen the way `Withdraw` drives a chest — a state machine, because opening a
menu is not synchronous. Four rules: one craft at a time with the result read back; **shift-click
the result, never pick it up** (`QUICK_MOVE` crafts everything the grid can make and puts it away,
where picking it up leaves it on the cursor); the grid is emptied back to you first, because what
somebody left in it is not ours to consume; and a missing ingredient stops the round and names it.

**Stonecutting and smelting are deliberately NOT done here and are REPORTED rather than skipped.** A
stonecutter is one button and a furnace is two slots and a wait; both are worth having and neither
is this state machine. A stopped-early craft that reports success is the "does nothing, quietly"
failure this file keeps writing rules about.

### Palette by price

`mcbuild cheapen --by-price` asks the shop instead of the tier table: *of the blocks that would
still look right, which is the least money.* **THE TOLERANCE IS THE WHOLE DESIGN** — nearest-by-
colour ignores cost, cheapest-overall ignores the build, and 30 is about the gap this file already
calls invisible (`light_gray_concrete` → `stone` is 11, `gray_concrete` → `gray_wool` is 15).

Two refusals matter more than the feature:

- **It does nothing without a price book.** Falling back to the tier table would make `--by-price`
  a synonym for `cheapen` that merely sounds better informed, and you would never learn the shop
  had not been walked.
- **It only moves for a REAL, PRICED saving.** Swapping one unpriced block for another unpriced one
  is churn dressed as economy, and it changes how the build looks for nothing.

`face` defaults to **side**, not top: a statue is read in elevation, 155 blocks differ between their
two faces, and the top-face default is right for a floor and wrong for everything this is pointed at.

### The timelapse was sitting in the archive

`tools/timelapse.py` — nineteen `island` captures going back to the first one, and `render3d` has
been able to draw a capture since it was written. What was missing was the observation that a folder
of dated captures of the same box IS a timelapse. **16 frames, 18–28 August, +42,266 blocks.**

Three things it had to get right, and two of them are about honesty rather than rendering:

- **THE FRAME MUST BE FIXED.** `orbit` sizes the camera to each model's own content, which is right
  for one animal and wrong here: the island grows, so every frame would re-frame to its own bounding
  box and the whole thing would swim. One camera, computed once, from the union of every frame's
  content in WORLD coordinates.
- **A CAPTURE THAT LOST A THIRD OF THE ISLAND IN AN HOUR SAW LESS OF IT.** All twenty cover the same
  56 chunks, so chunk count says nothing — what differs is DEPTH: a scan taken from the deck never
  receives the lowland's sections, and the archive ranges 49,762 to 137,857 blocks over the same
  ground. Played straight, the underworld blinks in and out. Frames under 70% of the running peak
  are skipped, **reported, and overridable** — because a big drop CAN be real: Jack removed 32,369
  vines by hand between two of these scans, and a filter that quietly hid that would be editing the
  history it exists to show.
- **Ordered by the capture's own timestamp, never mtime** — copying a folder rewrites every one of
  them, and the backup now copies that folder nightly.

### Still open

- **The printer has not been run in game.** Every piece of it is unit-tested and the API was checked
  against the jar rather than remembered, but the aiming rules are reasoning until a stair goes in
  and gets walked up. Start it on something small and forgiving.
- **Two printers will fight** over the same cells. `/cscan print` warns when litematica-printer also
  has the design enabled; it cannot turn the other one off.
- **`make` does not open the crafting table**, on purpose — the same refusal `Prices` makes about
  the shop. Whether that survives contact with an overnight run is Jack's call.

