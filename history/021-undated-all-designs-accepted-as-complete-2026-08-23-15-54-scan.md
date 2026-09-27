## All designs accepted as complete (2026-08-23, 15:54 scan)

**Jack's call, wholesale: every tracked design is COMPLETE AS IT STANDS in the world.** The
world is the master copy applied all at once - whatever a design still listed as remaining
work is no longer wanted. From here the island takes NEW projects only; nothing old is live.

What changed in the repo:

- **`sync.yaml`: `regen: []` and `progress: []`**, both deliberate. Regen off means the
  ground designs stop re-emitting remainders - and stop re-planting the vines Jack removed
  by hand (32,369 of them between the Aug 21 and Aug 23 scans; the purge is his, and the
  designs were fighting it). Progress empty means `designs.json` says "you track nothing":
  the mod places, plans and follows nothing, and bare `/cscan place` still refuses the
  61-design folder sweep. A new project resumes tracking by being added back to the lists.
- **Litematics, sidecars, configs and work.json files are untouched** - they stay as the
  record of what was designed, exactly as retired designs always have.
- `tests/test_tracked.py` now derives its expectations from the cfg (empty is a legal,
  deliberate state); the name-stripping property runs on a synthetic cfg so it stays tested.
- `test_lowland_glow.py::test_zero_spawnable_surface_cells` is SKIPPED with the reason in
  the marker: the glow (0 of 29 fixtures ever placed) is closed, and the world then moved
  past its solution - the 15:54 scan removed the 40 drowned pond lanterns
  (`lantern->water:40`) and re-lit 28 elsewhere, which opens **15 spawnable cells on the
  axolotl's back at Y43-45** that the solved fixtures never covered. That gap is ACCEPTED.
  A night-pass re-solve against the as-accepted world is a new project if Jack wants one,
  with its own design and its own test.

Final standing state at acceptance (full-depth 15:54 capture, 110,551 blocks, 56/56 chunks):
Root Stair, Lowland Root, Lowland Axolotl 100% - Hamlet 97% - Atelier Court, Turtle 96% -
Campanile 93% - Castle Bridge, Deck Vault 92% - Void Isle, Ruinway, Sanctum 89% - Taproot
84% - Court Stair 82% - Belly 79% - Lowland Stair 74% - Court Hall 65% - Shop Islet 44% -
Entry Hall 41% - and never started: Lowland Portal (114), Lowland Glow (29), Undercroft
Store (77), Shed Shard (198), Chimneys (10), plus the plate dressing remainders (paths 69,
hem 149, light posts 36, bird lanterns 59, footings 49, ride lights 17, apiary 12,
entrance 5). All of it accepted; none of it owed.

Questions this closes, so nobody reopens them by accident:

- **The Void Giraffe record mismatch is moot.** The giraffe stands complete (~4,120 cells,
  material budget matching the design) 6 blocks south of the design's recorded origin, with
  coat differences beyond a rigid shift - the record was stale, and untracked it can no
  longer misdirect a build loop. If it is ever re-tracked, adopt as-built first.
- **Court Hall's 58-cell replace question**: closed, the stone brick stays.
- **Entry Hall's 40 deviations**: closed, they were Jack's substitutions.
- **The chest move**: was already done - 86 chests in the Store Hall, 21 with machines,
  16 elsewhere (12 of those a deliberate ring on the east lobe at Y200).
- **The sync-below-Y150 blindness** (history and shop read the Y150+ cut, so every lowland
  design reported 0 forever and velocity was ~4x off) is now inert with tracking empty,
  but still latent: give sync a full-depth world before tracking any below-plate project.

