## Four reference builds calibrated the inspection: 74 findings -> 1 (2026-08-30)

Jack sent two more working contraptions (`reference/contraption_31323.litematic`,
`contraption_24829.litematic`) on top of the item filter and the bonemeal farm. Run against builds
that DEMONSTRABLY WORK, the circuit inspection was mostly shouting at itself:

| build | findings before | after |
|---|---|---|
| bonemeal farm + shulker loader | **74** | 1 |
| contraption 31323 | 2 | 1 |
| contraption 24829 | 9 | 1 |
| item filter | 2 | 1 |

and the one that remains on each is the informational quasi-connectivity line, except the item
filter's - which is the bus question, now the ONLY real finding across four independent builds and
therefore much more likely to be a fact about that exported region than noise.

**THE ONLY QUESTION THAT DECIDES WHETHER A TOOL GETS USED IS WHETHER IT STAYS QUIET ON A MACHINE
THAT WORKS.** This project already learned that on the audit and again on the deck soffit - *a
check that cries wolf is a check nobody runs* - and a redstone inspector has more chances to cry
wolf than anything else here. `tests/test_circuit_calibration.py` pins a CEILING per build, so a
future change that starts shouting fails.

### Four false-positive classes, each a real bug in the tool

- **SEEDS ARE NOT SOURCES**, and this was a genuine defect. The walk that measures "how far is this
  dust from power" collected the EMITTER - which may be two cells away, through a block it powers -
  and then seeded from dust ADJACENT TO THAT EMITTER. The two never match: a dust cell fed through
  a stone block is not adjacent to the torch under it. So the walk seeded nothing, every cell
  measured as unreachable, and six runs of a working build were reported as dying. It collects the
  cells power ARRIVES AT now. This one was also mis-reporting our own designs and nobody had
  noticed.
- **A MOVING REDSTONE BLOCK DRIVES HALF THE COMPACT MACHINES IN THE GAME.** At rest the driver is
  not next to the thing it drives, so a static inspection calls a working machine unwired - seven
  "unwired" pistons in one row of the farm, and a repeater pointing at empty air with a redstone
  block sitting on a sticky piston one cell above. `moving_driver_near` is deliberately generous: a
  false negative costs a real finding, a false positive costs a warning nobody needed.
- **An OBSERVER pulses rather than holding**, and what it watches for may only exist while
  something moves. Two repeaters came back as "reads nothing" with observers on two sides.
- **62 quasi-connectivity lines, one per component.** A piston machine is pistons with things over
  them; that is what one looks like. One counted line now.

**And the calibration was checked for blindness**, which matters more than the numbers: a stranded
comparator, a 30-cell run with no repeater and an orphaned dust group are all still reported, and
`test_our_own_broken_lane_is_still_caught` pins it. Buying quiet by going blind would be worse than
the noise.

Our own item sorter, generated from the reference lane, now reports **nothing suspicious** - which
is not the same as working, and the docstring still says so.

