## The chunkscan audit (2026-08-27) — a scan had eaten a design

A full read of the mod: 33 client classes, 15,537 lines, 364 Java tests green before it started.
The build was healthy and the shipped SCHEMATICS FOLDER was not.

### A SCAN AND A DESIGN SHARE ONE NAMESPACE, AND THE SCAN WINS

`/cscan Falls` had been run. `ScanRunner` resolves `<name>.litematic` and writes unconditionally, so
it overwrote the design of the same name:

| | the design (`out/`) | what was in the schematics folder |
|---|---|---|
| litematic | 44×114×53, **30 blocks**, 4 palette | 103×335×103, **111,631 blocks**, 594 palette |
| sidecar | `kind: falls`, **41 dig cells** | a capture sidecar, **0 dig** |

`Falls.work.json` survived, so the mod's own state was internally inconsistent: `/cscan follow`
still saw 30 cells of real work while `/cscan dig Falls` reported nothing to clear. The 41 lost
cells include the notch that has to be cut LAST — pull it early and you flood the trench you are
standing in. And `Falls` was in `designs.json`, so **bare `/cscan place` would have pasted a
111,631-block island capture onto the island.**

**Nine more captures were sitting in the same folder** under the names `clear`, `off`, `on`, `wand`,
`islan`, `_fill here` and `AtelierCourt`. Every one is a mistyped or not-yet-existing subcommand:
the bare `/cscan <name>` scan form is the last alternative in the command tree, so anything
Brigadier does not recognise falls through to it and writes a multi-hundred-kilobyte world capture
under that word. `Designs.list` then offered all of them as designs — its docstring said it "skips
the raw scans" and it never did.

**Restored and quarantined.** `Falls` is back from `out/` (the clobbering capture survives as
`scans/falls_20260827-1813.*`, so nothing was lost either way); the nine junk captures moved to
`schematics/_junk/` rather than deleted, because they are Jack's files.

**Three guards, and the last of them is the one that matters:**

- `Designs.isDesign` / `designExists` tell a design from a capture. **The CAPTURE markers are what
  is tested, not a positive design marker** — that distinction is not pedantry. Testing for `kind` /
  `generated_by` / `dig` looked equivalent and hid `Lowland Axolotl`, whose sidecar is a
  hand-written as-built record carrying only `file`, `name`, `note`, `origin`. Absence of evidence
  that a file is a capture is good evidence it is a design; the reverse does not hold. The scan
  guard is more cautious still: an unparseable sidecar blocks a scan, because the cost of being
  wrong there is a design and its dig list and the cost the other way is picking another name.
- `ScanRunner` refuses to write over a design and says so. Re-scanning `island` over yesterday's
  `island` is the daily loop and still works, because a capture is recognisable.
- `ChunkScanClient.RESERVED` holds every command word — plus words that are NOT commands yet
  (`scan`, `undo`, `progress`, `help`, `list`, `status`), because the failure mode is reaching for a
  command that does not exist, which is exactly how `islan` and `clear` got there. `/cscan scan
  <name>` is the explicit spelling for a scan name that collides on purpose.

`SidecarSafetyTest` pins all of it, including that **every registered literal is reserved**, read
from the command tree's own source so the list cannot drift behind a newly added verb.

### THE DIG LIST WAS NOT WORK

`Work.Split.complete()` was `todo.isEmpty() && unseen == 0` — placements only. A litematic cannot
express removal, so "break this" lives in the sidecar, and nothing in the loop read it. `/cscan dig`
could SHOW the list; showing is not the same as knowing.

Measured on the tracked designs: **`Falls` is 58% dig** (30 to place, 41 to break) and **`Island
Night` is 22%**. The loop would have placed thirty blocks, reported the design complete, and left
the channel it exists to cut standing in solid rock.

**Two questions, not one, and separating them is load-bearing.** A client mod cannot break a block —
the printer places, and digging is Jack with a pickaxe. Had the loop's advance condition demanded an
empty dig list it would have sat on `Falls` for ever waiting for something it can never do, and
`follow all` would never have reached the next design: the "a thing that does nothing, quietly"
failure this file keeps writing rules about. So `complete()` is the truth and `placementComplete()`
is what the loop advances on, and every completion message now names what it is handing back.

### Smaller defects, each one a rule this repo already wrote

- **`Ignored` survived a disconnect** — and its own docstring said "a relog is the accidental
  [clear]". That sentence was there before it was true. `Wand` states the rule these keys live
  under, *coordinates mean nothing without a world*, and a strike list is nothing but coordinates.
  Now cleared on DISCONNECT, along with the withdrawal's position-keyed cooling-off, the HUD's
  arrow and the autopilot's approach. The loop's INTENT still resumes from `session.json`; the
  positions do not.
- **`Highlight.tick` had no try/catch**, and the pre-upload audit had already written down that *a
  throw out of a tick event is a client CRASH*. It guarded the movement and looting ticks and missed
  the busiest one — every highlight layer redraws there every tick over block lists a caller
  supplied. Guarded, and it clears the batches rather than throwing again next tick. `Menu` too.
- **Fourteen of sixteen path-resolving commands never validated the name.** `fill` and `copy` were
  checked when the wand was audited because they WRITE; the read paths were not, so
  `/cscan paste ../../../x` would load a schematic from anywhere on disk. The gate is now at the two
  functions that turn a name into a path — `Work.file` and `Designs.load` — not at the sixteen
  callers, so the next command to want a design name cannot forget it.
- **The archive was unbounded**: 24 files and 1.6 MB when first noted, 56 and 4.4 MB when measured
  again, and `/cscan auto` adds one per tick for ever. Capped at twelve per NAME — per name, so a
  chatty auto-scan cannot evict the one hand-made capture a design was verified against — and sorted
  by filename, because the name carries the timestamp and mtime moves when a folder is copied.
- **The command sheet omitted five real verbs** (`chunks`, `sel`, `unmark`, `label`, `auto`) and
  `MenuTest` named them in its `modifiers` exemption list, so the check written to catch a stale
  sheet was configured not to see them. Rows added; the exemption list now holds only words you
  would never type first, and the assertion is `isEmpty()` rather than `size() <= 2`.

### What was added, because the audit kept finding built things with no door

- **`/cscan undo <name>`** and **`/cscan undos`**. Every fill has always written `_undo <name>`,
  `UndoAndStorageTest` has always asserted both of its halves, and `Designs.list` deliberately hides
  them so a bare `place` cannot sweep one up — and nothing ever offered one. Both halves or it
  half-works: re-placing restores what the fill covered, and the cells the fill made from AIR are
  highlighted to break, because a litematic cannot express removal.
- **`/cscan progress`** — every tracked design, how far along, what is left to place AND to break,
  in build order. `python -m mcbuild progress` has always answered this and only offline.
- **Build order reaches the game.** `finish.defer_to` settled precedence at generation time and
  CLAUDE.md stated the sequences in prose; the sidecar carried neither, so `follow all` walked the
  tracked list as written. `pipeline._after` derives an `after` list from `defer_to` — deferring IS
  the ordering, since a design that yields a shared cell cannot be built first — and
  `Designs.inBuildOrder` topologically sorts the run. A design with no `after` keeps its place, so a
  folder written before this exists is ordered exactly as it was, and a cycle still builds something
  rather than refusing everything.
  **`Island Night` now records `after: [Falls, Lowland Thicket]`**, which was the one hard ordering
  on the island written down only in prose: the night pass is a fixpoint solved against the finished
  world, and the Thicket's dripstone is the one plant that is not passable, so it moves the surface
  classifier under the solution.

**Still open, deliberately:** `Lowland Thicket` has no `after` recorded — its config belongs to
another session that was editing it, and the ordering it needs (`after: [Falls]`) is a one-line
addition for whoever owns it next. And the two legitimate captures, `island` and `islandlow`, still
live beside the designs; they are now correctly excluded from `Designs.list`, but a `scans/` home
for them would be tidier than a rule that knows to skip them.

384 Java tests, 0 failures.

