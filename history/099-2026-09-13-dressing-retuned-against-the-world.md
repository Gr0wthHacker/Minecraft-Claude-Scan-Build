## Dressing, retuned against the world (2026-09-13)

Jack: *"we can add and dress more from where we are and build upwards in smart ways."* The dressing
half first, because it needed no new design at all.

**THE DIAL WAS NEVER THE PROBLEM.** `PF Park Green` covered 3,575 of the ~20,769 plantable columns
at 1.2 cells each - ground COVER, not the mass the park is short of. The cause is two gates in
`parkgreen`: `open_min` refused to plant within THREE of anything built, and a column below
`(open_min + open_full) // 2` could only draw a FLAT kind. **On a park whose lawn IS verges, almost
every column was one or the other.** Swept:

    o_min o_full dens step    cells   cols  3+tall
        3      7 0.75    3     4246   3575     184     <- as shipped
        2      5 0.90    3     7449   5221     682
        2      4 0.95    2    18152   8849    2895     <- taken

| | before | after |
|---|---|---|
| `PF Park Green` | 3,706 | **17,799** |
| `PF Park Rim Green` | 1,814 | **3,733** |
| `PF Frontier Scatter` | 2,310 | 2,578 |
| dead ground the passes remove (columns 4+ from anything) | 4,928 -> ~1,700 | **4,928 -> 514** |

0 NEW problems in context on all three, and `tools/park_empty.py --walk` reports **0 columns cut
off** behind the denser planting.

- **A KERB IS PROTECTED BY `path_clear`, NOT BY `open_min`**, and that is why lowering `open_min`
  is safe: `_Ground.clearing` refuses any candidate whose whole `path_clear` neighbourhood is not
  lawn, so a column two from a path is refused whatever the openness gate says. What `open_min`
  alone governs is the gap between BUILDINGS - and a narrow gap still draws only a flat kind.
- **`PF Frontier Scatter` BARELY MOVED** (2,310 -> 2,578) and the reason is worth keeping: it is
  limited by its KEEP-OUTS, not its density. It reserves all nine module lots, because a material
  test cannot tell its own jungle tree from the Diggings' one. `claimrow` solved that exact problem
  with `shipped_cells` - exact cells from the artifact rather than a lot - and pointing Scatter at
  the same mechanism is the obvious next gain.
- **THE RIM RESERVE GOT A MODEST LIFT AND KEPT ITS KIT** - no trees, no hedges, capped at three
  courses. Its job is an OUTWARD SIGHTLINE, and the one thing that would spoil it is mass tall
  enough to close the view.

### Two tests moved WITH the decision, and one of them was a snapshot

- `test_the_openness_gate_leaves_a_verge_alone` asserted `open_min >= 3`, which is the decision
  this pass reversed on measurement. It asserts the surviving property instead - a ONE-cell verge
  is never planted, the ramp ramps, and the kerb keeps its own guard - and names the real check for
  passage, which is the walk flood rather than a constant.
- `test_the_cleanup_actually_cleans_up` guarded its ratio with `before > 5000`, **a snapshot of one
  day's park**: the baseline legitimately falls as the park gets denser, and it hit 4,928 the day
  the dressing improved - a magic number failing for the very improvement it exists to witness. It
  is a share of the bare ground now. Its `without=` list had also been leaking: it excluded two
  dressing designs and not the third, so the "before" moved when something it was not measuring
  got denser.

**Still open:** `PF Frontier Overgrowth`'s two vines naming a face that is air in a pass-disabled
composite is PRE-EXISTING - verified by running against HEAD's artifacts.

