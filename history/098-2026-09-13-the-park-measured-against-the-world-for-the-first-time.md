## THE PARK, MEASURED AGAINST THE WORLD FOR THE FIRST TIME (2026-09-13)

Jack captured the whole park in three scans - `dinoisland` z80299-80545, `carnivalisland` z80494-80769,
`prismisland1` z80670-80901 - and `python -m mcbuild merge` unions them into
**`out/park_world.litematic`**, 203x369x603 at (97499, -64, 80299). **Every design cell is inside
it**: `progress` reports `0 outside the scan box`, which is the first time that has been true.
CLAUDE.md has asked for a plot-scale capture for weeks; this is it, and it changed three answers.

- **379,768 blocks standing, 73% of the design** (311,089 of 426,548), 1,710 deviations.
- **98.5% of what is built belongs to a design.** Only 5,569 cells are unaccounted for, most of
  them one hand-built thing in acacia and water at x97520-97535 / z80688-80719. There has been no
  drift from plan at all.
- **THE SIDECAR'S `non_air_blocks` IS WRONG ON A MERGE** - it read 33,021,122. The union carries
  TWO air palette entries and only `Model.solid()` knows both. Count the model, never the meta.

### THE PARK IS SPARSE, NOT EMPTY, AND THAT DECIDES WHAT CAN BE ADDED

| | park, built | park, design FINISHED | `reference/amazingsteal` |
|---|---|---|---|
| blocks per occupied column | **3.29** | **3.69** | **10.30** |
| ground columns carrying 3+ courses above the lawn | **17.3%** | - | **65%** |

**FINISHING THE PARK DOES NOT CLOSE THE GAP** - 3.29 to 3.69 against 10.30. That is a fact about
the DESIGN, not about the building, and it is why more of the same plan is not the answer.

And there is nowhere left to put a new module on the ground. Of 82,482 bare lawn columns only
20,769 are two clear of anything standing, and a maximal-rectangle search over those finds
**27 free pads of 8x8 or better in the whole 600x200** - one at 15x54, six with a short side of 13.
**The lawn is a mesh of verges, not a set of plots.**

What IS empty is the air. 78% of everything built sits in the twelve courses above the lawn;
**the Lost Plateau has 21 cells above Y250 in the entire land**, and the median column's headroom
to the build limit is 117 courses. The railway is already an elevated spine at Y214 - down the
EAST edge only.

