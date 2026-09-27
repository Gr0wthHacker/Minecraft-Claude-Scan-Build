## Full automation: the loop closes (2026-08-30, chunkscan 0.5.0)

Seven more, and the first of them is a SUBTRACTION.

| | |
|---|---|
| the loop asks the printer | a placement is progress and a refusal is proof, both immediately |
| `/cscan autodig <design>` | break the cells the dig list names, and only those |
| `/cscan smelt <item> <n>` | drive a furnace or a stonecutter |
| `/cscan buy <design> [cap]` | quote the shortfall; with a cap, buy it |
| `/cscan farm <seed> <crop>` | place-wait-harvest over the wand's box |
| `/cscan photo <design>` | fly eight bearings and photograph each |
| auto-sampled income | a rate exists without anyone remembering to ask for one |

### The clocks were a workaround, and now there is a signal

Every stall clock in this mod descends from one sentence in these notes: *"the printer never
reports back, so `todo` shrinking is the only honest evidence a block was placed"*. Four clocks, an
abandoned-station set, a thrashing detector and a recovery ladder, all inferring from silence.

`Printer` reports now, and `Loop.stationFromReport` uses it. **The difference is not speed, it is
a different KIND of answer:**

- **a placement is progress immediately** — no waiting to see whether a count moves;
- **A REFUSAL IS PROOF IMMEDIATELY.** The clock could only ever say "nothing for five seconds" and
  guess why. A refused cell is the world saying no, and there is nothing to wait for, so the bin is
  abandoned on the spot;
- **and silence still means silence.** Nothing attempted is not evidence of anything, so it falls
  through to the clock exactly as before. That fallback is what keeps it honest — the report
  answers only what it actually observed, and litematica-printer is still an option.

### `autodig`: the one operation with no undo

A litematic cannot express removal, so "break this" has always lived in the sidecar and always
meant a human with a pickaxe. `Falls` is 58% dig. **Every gate here is a REFUSAL rather than a
warning** — the opposite posture to the rest of the mod, where a provisional list only ever warns:

- **only cells the design's own dig list names.** Not "anything in the way";
- **never a protected block** — `Rules` holds `wool` because wool may be a sculk sensor's silencer,
  and this is precisely the pass that would find out the hard way. **THE LIST IS NOT THE AUTHORITY
  ON SAFETY:** a dig list naming one is reported and skipped, not obeyed;
- **never over open void.** `VoidRisk` already knows what falls forever, and a lost drop is the
  skyblock-specific loss no undo can reach;
- **one block at a time, watched**, giving up rather than swinging at bedrock all night.

It does not pick up what it breaks, and says so.

### The furnace, the stonecutter, and a wait that is not a stall

`make` drove a crafting grid and reported the rest as out of scope, which was honest and still left
you doing it. `Smelter` closes it — and the clay farm needs the furnace leg specifically: clay to
terracotta is 1,968 smelts.

**A FURNACE DOING ITS JOB LOOKS EXACTLY LIKE A STALL** for ten seconds an item, so there is no
clock here at all, and `AutomationTest.aFurnaceWaitIsNotAStall` exists to stop someone adding one.
**Fuel is handled before input**, because an input with no fuel is not a stall either — it is a
furnace that will never start, and it looks identical to one that is working.

**The stonecutter is a button, not a grid**, so there is no arrangement to get right — and that
means the index is the ONLY thing naming the recipe, in an order the server chooses. It reads the
output back and checks it is what was asked for. Trusting the index turns stone bricks into the
wrong stair.

### Buying, which is the only thing here that spends something

Everything needed already existed; what is new is the part that cannot be undone by breaking a
block. So it is almost entirely refusals:

- **THE CAP IS AN ARGUMENT AND HAS NO DEFAULT.** `/cscan buy <design>` QUOTES; only
  `/cscan buy <design> <cap>` spends. There is no form that spends an amount nobody chose, and a
  test reads the command tree to keep it that way — a default, however conservative, is a number
  someone else picked for money that is not theirs.
- **It spends against the SHORTFALL, not the design.** Buying 518 powered rails when 167 sit in a
  chest is 167 rails of waste, and knowing that difference is what the craft resolver is for.
- **An unpriced item is never bought**, and **the price comes from the slot in front of you**, not
  from the book — the book is a memory of a menu seen at some point in the past, and prices move.

### The farm loop, and the photo tour

`Farm` is deliberately generic — a seed, a crop and a box — because the shape is the same for clay,
mud, ice or anything that converts in place. Nothing about clay is written into it. **It only ever
breaks the CROP, and only inside its box**, so pointing it at a wall by mistake does nothing at all.
And **it waits rather than deciding**: a conversion that has not happened yet is indistinguishable
from one that never will, so it reports its rate and lets you judge.

`Photo` closes the largest known-wrong in this file. The notes say it plainly: *"Validation is
circular FOR COLOUR"*, and *"nothing built in this system has been placed in Minecraft and looked
at"*. **A screenshot is the one image in the pipeline that owes nothing to our colour database** —
the game's textures, the game's light, and the biome tint the extractor had to ASSUME. Eight
bearings, the same eight `look.py --sheet orbit` renders, **relative to the recorded facing** so
bearing 0 really is head-on; a design with no facing SAYS SO rather than defaulting quietly. It
flies rather than teleporting.

**A 26.x API note, found by javap rather than by memory:** there is no
`Minecraft.getMainRenderTarget()`, so `Screenshot.grab`'s naming overload cannot be reached — its
RenderTarget argument has nowhere to come from. `grab(mc, true)` is the F2 path: the game names the
file and prints that name in chat, which is why the bearing is announced immediately before. The two
lines together are the caption.

### Income samples itself now

`/cscan income sample` was manual, so the rate only existed if you remembered. It samples after every
container the watcher indexes — but on **both** conditions, not either: ten minutes must have passed
AND the totals must have moved. A pure timer fills the log with identical rows overnight and makes
the "the index grew" caveat meaningless; sampling on every change writes a row per chest opened,
which is a rate measured over thirty seconds of walking.

### Still open

- **None of the placing, breaking, smelting or buying has run in game.** Every piece is unit-tested
  and every API was checked against the jar rather than remembered, but a stair being walkable and a
  purchase costing what the lore said are reasoning until they happen. Start each on something small.
- **Two printers will fight.** `/cscan print` warns when litematica-printer also has the design
  enabled; it cannot turn the other one off.
- **`make` and `smelt` do not open their own block**, on purpose — the same refusal `Prices` makes
  about the shop. Whether that survives an overnight run is Jack's call.
- **`tests/test_designs.py::test_all_configs`** still fails on `shop_islet.yaml` (`short_grass on
  cobblestone`), unchanged and pre-existing.

