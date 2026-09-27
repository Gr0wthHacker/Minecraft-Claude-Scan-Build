## Rules that were learned the hard way

1. **One origin for everything.** Every design is padded to `origin_lock` (currently `-24251 150 29949`)
   so regeneration can never move it. Before this, a design's origin was its content bounding box and it
   shifted a block or two between runs — that produced hours of "the placement is misaligned", posts
   floating over slabs, etc. If a design must sit elsewhere, set `origin_lock: false` in its config and
   say so loudly.
2. **Verify in context, never in isolation.** `finish.verify_against: <capture>` composites the design
   onto the real world and audits *that*: overlap must be 0, placement problems 0. It also reports
   free-floating clusters (blocks with nothing to place against — they need scaffolding).
3. **The audit learns.** `python -m mcbuild learn <capture>` mines what the server actually allows
   (lanterns on fences, carpet on leaves, upper-half tall grass) into `observed.json`. Hand-written
   placement rules were wrong about real builds ~28 times on the first island. Feed it new captures.
4. **Designs are remaining-work.** Ground-level designs regenerate against the newest scan and emit only
   what is not built yet. Anything placed by *spacing* rather than per-cell (light posts) must seed its
   spacing from what already exists, or it re-picks new positions and doubles up.
5. **`progress` distinguishes three things**: built (loose families — any rock variant, any decorative
   slab counts), *clear first* (a plant/carpet/vine occupies the cell), and a real deviation.
6. **Prep lists live in the sidecar**: `dig` (blocks to remove), `clear` (whole categories, e.g. vines),
   `exclude_boxes` (decor to re-hang). `/cscan dig <design>` shows them in game.
7. **The capture frame is correct** — verified against Litematica's own recorded placement origins
   (Dragonfly matched 86/89 blocks). If coordinates look wrong, suspect a stale file, a remembered
   rotation/mirror on the placement, or a locked placement — not the frame.
8. **`mcbuild place` needs the game closed** (Litematica rewrites its config on exit). `/cscan place`
   in game does not — prefer it.
9. **Anything that clings needs a FULL block, tested against the world as it is today.** Belly hung
   three vines off the vault's wall railings because "solid" meant "not air" and the anchor test ran
   against the pre-build baseline. Use `audit._is_solid_name`, and test against `world`, not `under`.
10. **Leave ~3 blocks of working room around anything you use.** Unless a design is deliberately
   about storage, it must not come within about 3 blocks of a chest, barrel, furnace, hopper or
   workbench — you need room to stand, open the thing and walk past it. Derive that clearance from
   the capture (`container_clear`), never from a hand-written box: the storage moves and the box
   goes stale the same day.
11. **Ask the game, not your memory.** `blocks.py` beats a hand-written table every time. The
   `palette.COLORS` list had ~150 typed-in RGBs and everything outside it rendered **magenta** —
   three renders in one session were silently wrong. `_is_solid_name` had a suffix heuristic that
   called a slab solid, which hid a vine hung off a slab roof in `farm`. Both now defer to the
   registry. When a rule and the game disagree, the game is right: chains were being audited for
   support they do not need (`ChainBlock` never overrides `canSurvive`), while lanterns standing on
   slabs were being rejected even though `canSupportCenter` accepts them.
   **And beware type names that read like a category.** `NOT_FULL` listed `"grass"` among the growing
   things — but in 26.2 the grass PLANT is type `tall_grass`/`double_plant`, and `grass` belongs to
   exactly one block: `grass_block`, a full cube. So the commonest ground block in the game counted as
   not-solid project-wide; nothing could stand on a lawn or cling to one, and `lowland` was told its 27
   lanterns were floating. The exclusion list is keyed on TYPE, so one wrong entry silently disables a
   whole block — `tests/test_blocks.py` now pins this one.
12. **Build for the SERVER's version, not the client's.** 26.2 client, 1.19 server. `pink_petals`
   sailed through every check in the pipeline and is a 1.20 block. `blocks.candidates()` filters to
   the server list by default. The allowlist is currently **provisional** — built from what the
   captures happen to contain plus a curated seed, so it holds ~191 of 1.19's blocks and would reject
   `allium`. Because of that the audit only *reports* unavailable blocks; it does not fail on them
   until a real 1.19 registry dump is supplied:
   ```bash
   # download a 1.19 server jar, then, as with 26.2:
   java -cp "<1.19 server jar>;<libs>" net.minecraft.data.Main --reports --output <dir>
   python tools/server_blocks.py --reports <dir>     # flips it to authoritative; the gate goes hard
   ```
13. **Gravity blocks cannot be used in anything with air under it.** `red_sand` is the best ochre in
   the game and cheap — and it would have poured the giraffe into the void. `blocks.falls` keeps sand,
   gravel, concrete powder and the rest out of `candidates()` unless you ask for them.
14. **Proportion names an animal, and it must be MEASURED — but proportion alone is not enough.**
   Every animal tuned by eye was wrong somewhere. Every animal tuned by NUMBER alone came out as
   the same animal with different numbers. Both halves are in the ANIMALS section above; that is
   where animal work belongs, not here.
15. **Overlap means the world holds something DIFFERENT.** A design cell the world already matches is
   built, not a collision — otherwise every design reports hundreds of overlaps the moment you build it.
16. **"Placeable" is not "affordable" — DIRT IS CURRENCY here.** On skyblock.net dirt and every one of
   its forms (`coarse_dirt`, `rooted_dirt`, `podzol`, `grass_block`, `mycelium`, `mud`, `farmland`,
   `dirt_path`) is money. The blocks are real, legal, in 1.19 and placeable, so every check in the
   pipeline passed them — and the lion shipped with a coat of 5,173 dirt, the capybara 4,690, and a
   ground layer wanted 14,568. **Moss is used instead.** This is a THIRD axis beside `exists` (is it
   real) and `available` (does the server's version have it): `blocks.spendable()` / `blocks.ECONOMY`,
   filtered out of `candidates()` by default so no colour-picked palette can reach it, with
   `allow_economy=True` as the escape hatch. `audit.report()` prints a loud `CURRENCY` line, because
   the first three offenders were all designs that had already audited clean.

