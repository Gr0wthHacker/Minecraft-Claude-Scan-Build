## The skyblock pass: cost, craft, income, boundary, void, warps (2026-08-30)

The mod knew WHERE everything is and HOW to build it. It could not say what anything COSTS or
whether you can MAKE it — and on a server where nothing is mined those are the only two questions.
Six features, all shipped, plus a backup, plus `chunkscan 0.4.0`.

| | |
|---|---|
| `python -m mcbuild craft <design>` · `/cscan craft` | resolve a design to RAW materials against your containers |
| `/cscan prices on` | read the server's own shop prices while you browse it |
| `/cscan income` | production per hour, from the container index over time |
| `/cscan plot` | the 99x99 boundary, and a warning when a fill crosses it |
| `/cscan dig` | now warns when what you break falls into the void |
| `/cscan warp add` | teleports as a routing primitive, not only as a fall rescue |
| `python -m mcbuild backup` | a full VERIFIED rotated backup, and it runs inside `sync` |

### The BOM stopped at the block, and the recipes were in the jar the whole time

**1,585 recipe files and 191 item tags sit inside `minecraft-client.jar`**, under
`data/minecraft/recipe/` (singular in 26.x — it was `recipes/` up to 1.20) and
`data/minecraft/tags/item/`. That is the same jar `tools/extract_blocks.py` already opens for
textures, so `tools/extract_recipes.py` needed no datagen run and no new dependency. Rule 11 — ask
the game, not your memory — had never been applied to what a block is MADE of.

`mcbuild/recipes.py` and `Recipes.java` resolve a want-list down to raw materials against the
container index. **Four traps, and every one of them shipped a plausible wrong answer first:**

- **PACKING RECIPES ARE ARBITRAGE, NOT ROUTES.** Costing every leaf at one unit makes
  `raw_gold_block` a *cheaper* source of raw gold than raw gold is, because one item becomes nine
  for free. The first resolver answered "518 powered rails" with "unpack 58 gold blocks" — blocks
  nobody owns — and **the cycle guard did not catch it, because a cycle guard stops the recursion,
  not the arithmetic.** Packing recipes are barred from costing and offered only against stock you
  actually hold, where they are exactly right: a chest of gold blocks is nine times the metal and
  no trip.
- **CRAFTING IS NOT ALWAYS THE ANSWER.** A recipe that costs the same as the thing it makes is a
  wash, and following it anyway sends you shopping for its ingredients instead: the second version
  answered the same question with "smelt 522 deepslate gold ore", which is not a material any chest
  on this island has ever held. Craft when it is genuinely cheaper, or when you already hold an
  ingredient; otherwise report the ITEM short, which is the thing you would go and buy.
- **THE ALLOWLIST HOLDS BLOCKS, AND MOST INGREDIENTS ARE ITEMS.** `blocks.available("gold_ingot")`
  is False — not because the server lacks gold but because a list of BLOCKS has nothing to say
  about an item. Applied blind it priced every ingot 50x a block and sent the resolver mining. This
  is rule 11's `NOT_FULL` holding `"grass"` in a new costume: one list, asked the wrong question.
- **AN ALTERNATIVES LIST IS RESOLVED BY WHAT YOU HAVE.** A stick takes any of fourteen planks and a
  torch takes coal or charcoal. Picking the first in the file sends you out for oak while 3,000
  jungle planks sit in a chest.

**And the stonecutter wins on its own merits.** Crafting stairs is 6 blocks for 4; cutting is 1 for
1. Costing per OUTPUT unit gets that for free rather than special-casing it — over a design that is
a third of the stone.

**The two resolvers drifted the moment they existed, and the fix is the repo's own rule.** The
`reversible` flag was computed at Python load time, so the exported JSON carried no flag and the
Java port happily priced a gold block as cheap gold — the same shape as `proportions.measure` and
`rubric.score` needing one entry point. It is written into `recipes.json` by the EXTRACTOR now, so
both languages read one source, and `SkyblockTest.theJavaAnswerMatchesThePython` pins three cases
that `tests/test_recipes.py` asserts identically.

Measured, against the live index: `Rail Spiral` resolves to **289 gold ingots short** and everything
else already owned; 58 lanterns are fully craftable from iron already in the hall; 2,000 terracotta
is 1,968 clay short — which is the clay-farm conversation, answered by the tool instead of by hand.

### Prices: the tier table was invented and the server has real numbers

`palette.tier()` sorts the whole registry into cheap/ok/expensive with prices noted in a COMMENT
("terracotta, 10 grass each"). Every palette this project has picked rests on it.

**A shop menu IS a container screen**, which is why this was cheap: `ContainerWatcher` already
hooks `ScreenEvents` and walks `menu.slots`. The price is not in the item, it is in the item's
LORE, as text a human reads — so `Prices.java` is a text scraper and is honest about it:

- **a slot with no readable price is skipped and counted, never defaulted to zero** — a missing
  price must never read as "free", which is how a palette picker learns to love the one block
  nobody can afford;
- **buy and sell are kept apart**, because costing a build with a sell price understates it by the
  spread, which on most servers is most of the price;
- **a price is per ITEM, not per stack** — a menu offering 64 for 320 is 5 each, and recording 320
  makes stone look like quartz;
- **it never opens a menu by itself.** You walk the shop; this reads what you look at. Automating a
  shop walk is a trading bot, which is a different thing.

Written to `schematics/prices.json` — beside the storage index rather than baked into the jar,
because these change when the SERVER changes. That is the same test that put the rules and the
recipes IN the jar and `designs.json` outside it.

### Income: "289 short" is a different sentence depending on the farm

The container index is a snapshot of everything you own; a series of them is a rate, and nothing had
ever kept the series. `Income.java` samples on demand and `/cscan craft` now prints
`~7.2h of production` beside a shortfall that something is actually making.

Three rules, two of which are ways to report a farm that does not exist:

- **A snapshot is only evidence for containers you OPENED.** A total that rises because you finally
  looked in the gold chest is not production; every sample records its container count and a
  comparison across a different set says so instead of dividing.
- **Spending is not negative income.** Taking 500 bricks out to build with looks exactly like a farm
  running backwards, so rises and falls are reported separately.
- **Two samples ten minutes apart is a rate; two a minute apart is noise**, and below that the pair
  is not divided at all.

Capped at 240 samples: this is a rate meter, not an archive, and the scans folder has already been
an unbounded-growth bug once.

### The plot, the void, and the warps

- **THE PLOT IS 99x99 AND THE MOD COULD NOT SEE IT.** `mcbuild/plot.py` derived it from the island's
  own bedrock and only the generators consulted it, so the Island Run shipped 120 cells over the
  line and a HUMAN caught it. The bounds now ride in `chunkscan_rules.json` with everything else and
  `/cscan fill` warns when a box crosses them. **NOT FOUND is not the same as INSIDE** — with no
  bedrock in any capture every check answers "I cannot say" rather than "fine", because a boundary
  guard that silently passes everything is the failure it exists to prevent wearing the opposite hat.
- **BREAKING A BLOCK OVER THE VOID LOSES THE DROP** — not scattered, not despawned in five minutes,
  gone the moment it passes the bottom of the world. `Falls` lists 41 dig cells and some are a
  hundred blocks up, and `/cscan dig` walked you there in silence. `VoidRisk` searches DOWN to the
  world floor (an item falls until something stops it), demands a **solid** catch — vine and grass
  do not stop an item, and this file has been bitten twice by "not air" read as "solid" — and treats
  an unloaded column as UNKNOWN rather than as void, or the whole lowland reads as a hazard from the
  deck.
- **WARPS ARE A ROUTING PRIMITIVE.** `Autopilot` already types `/is`, but only when falling; using
  the same command because it is SHORTER is the same call in a different place and was never made.
  The one thing that makes it work: **a warp is recorded by standing where it DROPS you**, so the
  saving is measured against an observed position rather than an assumed one. Under 80 blocks saved
  it is theatre and is not offered.

### The backup, because none of this was backed up

Three stores hold the island and only one is in git: the repo, the **schematics folder** (18 MB, not
in git, and the only copy of every capture ever taken), and the game dir. `sync` regenerates designs
from configs; it cannot regenerate a CAPTURE, because a capture is a photograph of a world that has
moved on.

`python -m mcbuild backup` writes a working-tree zip, a `git bundle` of all history, and a zip of
the schematics — **29 MB, five seconds, 1,486 files.** It runs at the end of `sync` (the moment a new
scan exists is the moment worth backing up) and a Windows task `mctest-backup` fires it daily at
03:30. `$MCTEST_BACKUP_DIR` points it at OneDrive or a second drive and the same command becomes an
offsite backup.

Four rules, each of which is the difference between a backup and a folder of hope:

- **A BACKUP THAT IS NOT VERIFIED IS NOT A BACKUP.** Every archive is re-opened and CRC-walked and
  the bundle is handed to `git bundle verify`. A write that failed halfway still produces a valid
  zip — with fewer entries in it.
- **NOTHING IS PRUNED BEFORE THE NEW ONE VERIFIES**, never below one, and never a FAILED backup:
  that one is the evidence of what went wrong.
- **THE DESTINATION MUST BE OUTSIDE EVERYTHING IT COPIES**, or each run archives the last one and the
  size doubles daily with nothing to say why.
- **HISTORY IS A BUNDLE, NOT A COPY OF `.git`** — copying an object store while a gc runs copies a
  torn one.

### And the command sheet caught itself going stale, as designed

`MenuTest` failed the moment the six commands existed, which is its whole job. Fixing it made it
stronger rather than looser: `offered()` read only the FIRST word of a row, so `/cscan income sample`
did not count as offering `sample` and every real sub-verb had to go in the exemption list — the one
thing that test's own comment calls its weak point. It reads the whole command string now, so the
exemption shrank instead of growing.

### Still open

- **`tests/test_designs.py::test_all_configs` fails on `shop_islet.yaml`** (`short_grass on
  cobblestone`). PRE-EXISTING — it fails with this session's Python changes stashed, and comes in
  with the newer `observed.json` already in the tree. Not this pass's to fix.
- **`prices.json` is empty until someone walks the shop.** The scraper's patterns are written
  against the common lore shapes and have never met skyblock.net's actual menu; expect one round of
  pattern tuning, and `/cscan prices` reports how many slots it could not read so you can tell.
- **The 1.19 recipe question is open the same way the block allowlist is.** These are 26.2 recipes
  and a skyblock server may customise them. Provisional; report, never refuse.

