## A DIAGONAL JOIN IS NOT A JOIN: `printable` (2026-09-06)

Jack: *"a lot of the schematic has blocks that are diagonal to each other but hollow, meaning it's
impossible to print on them since there's nothing attached to any one side of them ... they may
have a line of things, but the entire line is diagonal so nothing reaches it when printed below or
from above."* Every word of that was measurable and none of it was measured.

    python -m mcbuild printable "Park Complete"                # what a printer can never reach
    python -m mcbuild printable "Park Complete" --fix          # ...and close the corners

**A PRINTER CLICKS A FACE, SO PRINTABILITY IS A CLOSURE OVER 6-CONNECTIVITY, SEEDED BY THE WORLD.**
That is a different question from every check this project had. `audit.check_supports` asks whether
a block can EXIST; `pipeline._floating` asks whether a cell has anything under it; `analyze` asks
what can go in TODAY. None of them asks whether the chain ever arrives, and a design can pass all
three while being unbuildable.

Measured on the shipped `Park Complete` - 540,862 cells:

| | |
|---|---|
| separate printing islands | **2,009** - each one a block a human must place by hand |
| cells a printer could NEVER reach | **18,721 (3.5%)** |
| ...orphaned by a DIAGONAL rather than genuinely floating | **16,062** |
| the largest single casualty | the **14,393-cell undercrypt**, whose only contacts with the rest of the park are (1,1,1) corners |

**THE FAULT IS TINY AND THE DAMAGE IS NOT**, which is the whole reason this is a pass rather than
something to eyeball: **889 corner fills returned 15,597 cells**, and the undercrypt came back for
about ten blocks. 18,721 unreachable -> 3,129, islands 2,009 -> 1,913.

### What a stitch is allowed to be

- **A CORNER FILL, NEVER A SCAFFOLD.** `REACH` is 2 because a two-axis diagonal needs ONE cell and
  a three-axis one needs TWO. Anything further is a bridge, and a lump of blocks alone in the void
  is REPORTED rather than reached - that one is a person with a stack of dirt, and inventing it
  here would hide the finding that matters under a pile of invented terrain.
- **It never covers anything.** Only cells empty in BOTH the design and the world, which is the one
  property that makes it safe to run over a build somebody is halfway through.
- **Its material is the commonest clickable, NON-FALLING material already touching it** -
  `deckfloor`'s heal rule, so a stitch cannot introduce a block the design was not already
  spending, and rule 13 cannot be broken by a fill that is over air by construction.
- **Of the two corners that close a step, it takes the one UNDER the upper block.** That is a
  STRINGER - the course the arc stair and every flight in this project build by hand - and not a
  lump on a finished surface. 615 of 889 land that way; the rest have only one legal corner.
- **A cell a player could stand in is a last resort and is COUNTED.** A fill in a doorway is the
  fault this repo has shipped three times (a timber set on a live rail, an adit's post bricking up
  its own corridor, two pines in the one walk a module exists to carry). 121 landed in one, so the
  walk was flooded before and after: **105,397 cells reachable from the gate, both times.**

**AND IT IS INVISIBLE IN PRACTICE, WHICH IS NOT THE SAME AS BURIED.** Jack asked for the fills to
be *"pretty much always invisible... placed on the inside of hollow objects"*, and measured
literally only 44 of 889 are sealed inside the build - the park is 95% open air, and a diagonal
join is by its nature on a SURFACE (a helix's rim, a stair's corner), so there is usually no buried
option to choose. What settles it is a render: the densest cluster - **175 fills in one 44-cube** -
is indistinguishable from the original at all eight bearings, because a one-block fill in the notch
of a rough surface reads as nothing. Judge this one by looking, not by the exposure count.

### What is left, and why it is not stitched

    1,062  the Prism Well descent, Y105-205    hanging in an open shaft, 3,409 air neighbours
       35  a birch at X97500 Y204-210          a tree whose trunk never reaches the ground
      ~12  x6 lamp standards, Y203-210         a base at Y203 with no lawn under it at Y202
    1,716  pond and plant dressing             lily pads, seagrass, vines, water surfaces

**THE DRESSING IS REPORTED APART AND MUST BE.** A lily pad is placed against WATER and a vine
against a leaf, so the closure cannot chain through either - correctly - and calling two thousand
single cells of pond furniture "unprintable masses" would bury the one real finding. `DECOR` names
them and `Survey.split_unfixable` separates them; **a solid block filled into a pond is not a
repair, it is a filled pond.**

The descent is the one structural hole left and it is a DESIGN decision, not a stitch: a helix in
an open shaft whose lining stops at Y187 has nothing to attach to at any reach.

### Where it runs

**`tools/park_place.py` stitches the composite at the moment it writes it**, because a break
BETWEEN two modules belongs to neither and no generator or per-design pass can see it - the same
reason `finish.carve_for` became a pipeline step rather than a note. A step that has to be
remembered is a step that gets lost, and this file has recorded that once already.

`tests/test_printable.py` (18) pins the shape rather than a snapshot: a diagonal line is one island
per block, a straight one is one island, a carpet carries nothing onward, a stitch never covers,
never falls, and hides under its tread - and **the shipped composite has no diagonal break a corner
fill could still close**. Asserting a cell COUNT would be the snapshot trap this repo has now
recorded five times; asserting "nothing the pass could fix is still open" cannot go stale.

**Two things worth keeping for whoever runs this next.** The three park plot captures
(`islandleft`, `newisle`, `islandright`) are **bare starter pads - 189, 144 and 192 blocks** - so
the park prints onto void and a survey against any one of them reads the other two lands as
unreachable; composite them with `coop.merge_scans` first, or run with no world at all, which seeds
from the design's own largest mass and answers in ISLANDS. And a per-module survey is the wrong
context by construction: `PF Park Green` reads as 2,599 islands alone because every flower stands
on `Park Ways`' ground, which is a different design. Rule 2, in a new place.

