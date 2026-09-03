# Prismworks v2: The Well

Jack, 2026-09-03: *"prism in its current state is not a theme park, its a collection of
buildings; this is a failure of design... we should make a highly visual area that has a
spiraling parkour set (downward); as well as other visual + engagement elements."*

v1 is archived whole in `archive/prismworks_v1/` — 14 designs, 14 configs, renders, and the
measured post-mortem. Nothing is lost and nothing regenerates.

## The diagnosis, measured off out/Park Complete.litematic

| | |
|---|---|
| blocks in the land | 56,030 |
| plot | 180 x 200 = 36,000 columns |
| **paved** | **100%** |
| carrying anything 3+ courses tall | 13.0% |
| carrying anything 12+ courses tall — an actual building | **4.6%** |
| Y used | 198–286: **88 courses up, 448 cells below the plane** |
| void underneath, never touched | **261 courses** |
| `polished_blackstone_bricks` + `smooth_basalt` | **54% of the land, two dark greys** |

Half the plot is lawn with a path grid drawn on it. A path that crosses nothing is a diagram,
not circulation. And the land's headline ride is a decorated tower — which its own config says
outright: *"THE PARKOUR COURSE IS NOT IN HERE... This design is the SPIRE the course will be
hung on."* It shipped as the spire and reads as one.

**THE UNUSED DIMENSION IS DOWN.** It is the only dimension in this park nobody has spent, no
other land competes for it, and a lit helix falling into darkness is precisely what this medium
renders natively — planar and columnar, bright points on black. That is not a consolation
prize for a failed land; it is the strongest single image available on this plot.

## The shape: the mouth IS the land

v1's error was 36,000 columns and not enough ideas, so it got sprinkled with buildings. v2 does
not sprinkle. **One hole, one gesture, and the land is the rim around it.**

    a circular mouth ~110 across cut clean through the deck at Y203
    a 30-wide margin all round: arrival spur, rim gallery, practice loop, service edge
    the course hangs in the MIDDLE of that void at radius 18–24, ~30 blocks clear of the wall

From anywhere on the rim you see the entire run at once, hanging free. From under the island
you see a lit column of landings. That is one thing, and one thing is the opposite of a
collection of buildings.

## The five pieces

**1. THE MOUTH — Y203, the land's whole public surface.** The rim gallery is a continuous ring
terrace, not a path grid: every spur off the park spine arrives at it, and standing on it you
are looking down at people playing. It is the spectator stand by construction — runners are
below you and cannot be interfered with, which is the brief's own observer requirement met by
geometry rather than by a rule.

**2. THE DESCENT — Y199 → ~Y95, about 104 courses, three acts.** `gen/parkour.py`'s proven
vocabulary (LEDGE / GATE / PLUNGE / REST), wound as ~3 turns of a helix that hardens as it
falls. Act I keeps the shaft wall in view so nothing is a blind jump; Act II leaves the wall
for free-hanging landings and the first real plunges; Act III is open void, the longest gaps,
and a finale drop. **Calibrated off Island Run — 168 blocks for 151 courses — the course itself
costs on the order of 200 blocks.** A parkour run is almost entirely air; the landings *are*
the design.

**3. THE CATCHES — three full annuli, and they are not optional.** A water-and-slime ring under
each act boundary. A miss costs one act, never the whole run and never the void. Each catch
feeds a side landing with a lift back to that act's checkpoint. This is the anti-frustration
contract the v1 brief demanded and never built, and along with the shaft wall it is where the
block budget actually goes.

**4. THE COLUMN — the way back up, at the centre.** A bubble lift in a lit glass-and-metal core,
floor to rim. It does three jobs: it is the return, it is the spine the helix visibly winds
around, and a player shooting up the middle while others drop around them is the best free
spectacle on the plot.

**5. THE FLOOR — ~Y95, the destination.** A descent with nothing at the bottom is a chore. The
floor is a lit chamber open to void on every side with the park's underside overhead — and it
is where **Resonance Vault moves to.** The Vault is the park's only cooperative loop and v1 put
it in a box on a lawn. At the bottom of the well the descent earns it and it earns the descent.

## Engagement beyond the run

- **The practice loop** — 8 moves on the rim itself, free, no commitment, no queue. The brief's
  own acceptance test: a first-timer finds it without reading a dense sign.
- **The drop lift** — a slow, safe spectator descent in its own shaft, so a friend can follow a
  runner down and meet them at the bottom without ever entering the route.
- **The light gradient** — warm at the mouth, green through the middle, pale at the floor,
  using the froglight ladder `parkour.py` already carries. **The landing is its own lamp**, so
  the light and the route are the same object and the night pass cannot break a jump by lighting
  it (which is exactly what it did to fourteen of Island Run's).

## What survives from v1

**Resonance Vault** (relocated to the floor) and the **Prism Array's route-choice idea** (folded
into Act II as branch choices, not a separate building). Everything else — Foundry Gate, Forge
Deck, Service Gallery, Vantage Summit, the frontage, the Wyrm arch, the three games — stays
archived and is not rebuilt as-is.

## Palette

v1 was six greys between L38 and L73: a ladder inside one material family, which this repo has
now concluded four separate times cannot draw a line. v2's ladder is measured ACROSS families,
which is the only place contrast exists on this economy — and the shaft's own darkness is what
makes the froglights read. The deck stays pale so the mouth reads as a hole punched in it.

## Cost

v1: 56,030. v2 estimate **18–24k** — the course is ~200, and everything else is rim, shaft
wall, catches, column and floor. A hole is cheaper than buildings. This is an estimate and will
be measured, not asserted, before anything ships.

## What is NOT promised, and why

Per this repo's own rule — two finished casino games were cut rather than ship a machine that
could not be judged — v2 ships **free practice and a free full run only.** No timer, no payment,
no leaderboard until in-game proof. These cannot be certified offline:

- bubble-lift ascent and a dry exit at the top
- whether a jump that is geometrically legal is actually makeable
- any timing, payment or state machine

Block-level geometry *can* be certified here and will be: every landing's gap, drop, headroom,
catch coverage and route reachability, plus one connected walk from rim to floor and back.

## Decisions taken (Jack, 2026-09-03)

1. **Depth: ~104 courses, 3 turns.** Y203 down to ~Y95 - the 2-4 minute run the brief asks for.
   The deeper 160 available courses stay free.
2. **The floor is something new, designed for it.** Resonance Vault stays retired; the payoff is
   `PF Signal Zero` - a lit pool that catches every fall, and a bell you ring that the gallery a
   hundred courses up can hear.
3. **v1 is archived but not yet removed**, so the new work can be verified against the real
   neighbours. `out/park_future.litematic` is Park Complete minus the twelve v1 designs - the
   park as it will be - and everything here is generated and audited against that.

## Build order, which is load-bearing

Each design is generated against a capture the previous one produced, so running them out of
sequence does not merely mis-resolve a shared cell, it verifies against a world that does not
exist. `tools/prismchain.py` runs the whole thing:

```bash
python tools/prismchain.py            # the whole chain
python tools/prismchain.py --from descent
```

    1  PF Prism Well      cut, collar, gallery, balconies, pier, column, mast ring
    2  prism_cut          park_future with the well's DIG applied - the mouth actually open
    3  prism_site         prism_cut + the well - the course's collision world
    4  PF Prism Descent   the parkour, hung inside the mouth
    5  PF Prism Rig       the gantry, derived from the DESCENT'S OWN ROUTE
    6  prism_all          prism_site + descent + rig
    7  PF Signal Zero     the catch pool, the chamber and the bell

## What the build changed about the plan, and why

**THE COURSE READ AS CONFETTI AND ONLY A RENDER SHOWED IT.** `PF Prism Descent` passes every
check it has - 86 moves, 100 courses, 81% of jumps at full sprint distance, none short, zero
placement problems - and 167 blocks scattered through a hundred-wide void is a dusting of single
cells with nothing behind them. The Island Run gets away with it because it winds around an
island and every landing reads against terrain. `PF Prism Rig` is the answer: a lit gantry
following the course's own recorded route, four courses over it (the parkour's headroom is
three, so nothing it places can be clipped mid-jump), with a post at each of the eight rests.
It is overhead rather than beside on purpose - a walkable ribbon at the same radius is a way to
reach the bottom without jumping, which would retire the course it exists to explain.

**THE START PIER CHANGED THE WHOLE GEOMETRY.** Starting the run off the rim forced it to begin
at r45, and that one number cost three things: the fall zone became the whole hundred-wide disc,
so the catch had to be seven thousand cells; the same 86 moves bought only 1.84 turns, because a
four-block jump is a small angle at a big radius; and the helix hugged the collar instead of
hanging clear. Walking out on a pier to r33 first lets the course live inside r30 - a third of
the catch, more turns for the same effort, and a wide band of empty void between the run and the
wall.

**PRISMWORKS LOST ITS SKYLINE WITH THE SPIRE, and that needed answering rather than shrugging
at.** A well is entirely at and below deck level. The answer is not another tower: eight masts
on the gallery's outer edge, one over each balcony, which read as one ring at distance and as a
rhythm close up - the relay pylons the land's frontage already called SIGNAL 1 to 6, turned into
the thing they were pointing at. Eighteen courses, against the Sky Lift's seventy-four, so the
park keeps the two dominants it has rather than gaining a competing third.

**SLIME AND STAINED GLASS PANES ARE NOT EXPENSIVE** (Jack, 2026-09-03). The tier table is
invented and was wrong about both. Slime is the only block that cancels a fall outright, so
every plunge and every catch in this repo was being rationed against a price that is not real.
`mcbuild/palette.py` carries the correction and the reasoning.

## Still open

- **Nothing has been placed in game.** Three things cannot be certified offline and are recorded
  as `requires_in_game` on the designs that own them: the bubble column's ascent and a dry exit
  at the top; whether a jump that is geometrically legal is actually makeable; and whether
  one-deep water cancels a hundred-course fall as expected.
- **The signal is not built.** Running a light a hundred courses up the shaft to fire the mast
  ring is the obvious next payoff, and a vertical transmitter that tall is its own machine with
  its own contract. The bell does the job today with no redstone in it at all.
- **v1 is still standing.** Removing the twelve archived designs is one command once v2 is
  placed and walked.

---

**FOR WHOEVER FOLDS THIS INTO `CLAUDE.md`:** everything below is written in that file's voice
and belongs there. It is here instead because CLAUDE.md was being appended to in parallel
while this was built, and this repo's own rule is to commit only your own files.

## Traps, each of which shipped a clean audit


- **A NAME COLLISION IN THE GENERATOR REGISTRY.** `"well"` was already registered to
  `garden.build_well`; a second entry with the same key silently shadowed it, and a dict literal
  gives the later one. Renamed `prismwell`. Nothing warns about this.
- **THE CUT'S WHITELIST LEFT 61 CELLS HANGING OVER THE HOLE.** A whitelist has to enumerate every
  block the park might have placed inside a hundred-wide circle, and it cannot: `Park Ways` puts
  a lamp mast on the verge every 22 cells and none of its four materials was on the list, so the
  moss under them was dug and the masts left standing on air. **`protect.is_protected` is not the
  gate either** - it is the never-OVERWRITE set and holds `wool`, `carpet`, `lantern`, `end_rod`
  and `iron_bars`, true of a wool block on the main island and false of a lamp post inside the
  hole that replaces it. It is a BLACKLIST of machines now, and a machine inside the mouth RAISES
  rather than being worked around: measured, there are zero.
- **A LIFT YOU CANNOT GET OUT OF.** The water column was cased on four sides for its whole height
  including the head. Then the fix was undone by the head deck, which paved every cell of the
  nine-by-nine that was not already taken - including the exit that had just been left open. A
  sealed shaft and a working one are the same picture in every render.
- **FIVE FLOATING OBJECTS, THEN 168.** The return column and its four posts came out as separate
  components hanging in mid-void; tie rings fixed that. Then the gantry came out in 168 pieces,
  because sampling a line and rounding each sample steps DIAGONALLY and a diagonal neighbour is
  not a neighbour - the ear tips, the ossicones and the braided root all over again.
- **MASTS OUTSIDE THEIR OWN PAVING.** At `g1 + 1` the mast ring stood one cell beyond the gallery
  and four of the eight were detached 28-cell components. A mast needs a floor like anything else.
- **A CONTEXT THAT IS NOT A POSSIBLE WORLD.** `park_future` is Park Complete minus the twelve v1
  designs, and subtracting a building leaves the ground cover that sat ON it hanging: 31 moss
  carpets over nothing, where Park Complete has none. Every design verified against it inherited
  those 31 as its own. `tools/prismchain.py` sweeps them.

## The pipeline was reporting the capture's own problems as new

`run_config` compared the context audit's baseline against the composite in LOCAL coordinates,
and `scan.merge` sizes the composite to the UNION of both boxes - so a design that reaches
outside its capture (anything hanging below a floating park, every void build in this repo)
shifts the merged origin and every local coordinate with it. Compared locally the baseline
matched nothing, and `Park Complete`'s 28 pre-existing state problems were all reported as the
Prism Well's own, taking it to a non-zero exit. **Both are compared in world coordinates now.**
A check that cries wolf is a check nobody runs - which this file has said about the audit, the
soffit and the circuit inspection, and had not noticed about itself.

## Slime and stained glass panes are not expensive

Jack, correcting the table: *"slime blocks are not expensive, glass panes are also not
expensive."* `palette.tier` is invented and was wrong about both. **Slime is the only block in
the game that cancels a fall outright**, so every parkour plunge and every catch floor in this
repo was rationed against a price that is not real - `Island Run` carries
`expensive_allowance: 13` purely for it. Plain `glass` and the solid stained blocks are
deliberately NOT moved: nothing Jack said touches them, and a table that quietly widens past its
evidence is how four separate palette conclusions here have already gone wrong.

## The build order is load-bearing

Each design is generated against a capture the previous one produced, so running them out of
sequence does not merely mis-resolve a shared cell - it verifies against a world that does not
exist. `tools/prismchain.py` runs the whole thing:

    1  PF Prism Well      verified against park_future
    2  prism_cut          park_future with the well's DIG applied - the mouth actually open
    3  prism_site         prism_cut + the well - the course's collision world
    4  PF Prism Descent   the parkour
    5  PF Prism Rig       the gantry, from the descent's own route
    6  prism_all          prism_site + descent + rig
    7  PF Signal Zero     the catch, the chamber and the bell

`gen/parkour.py` gained three options, all defaulting to None so the Island Run is bit-identical:
`centre` and `bounds` (a course sited anywhere but the home island has no bedrock to find a plot
from), `radius_bottom` (a CONE rather than a cylinder), and `gap_rotate` (the search takes the
first advance angle whose chord fits UNDER the gap target, so a fixed target makes every jump the
same jump - and on a cone the same angular list is 3.9 blocks at r45 and 1.7 at r20, which
collapsed the bottom of the first run into two-block steps: a staircase, which is exactly what
Jack rejected the first Island Run for).

## What is NOT claimed

Three things cannot be certified offline and are recorded as `requires_in_game` on the designs
that own them: the bubble column's ascent and a dry exit at the top; whether a jump that is
geometrically legal is actually makeable; and whether one-deep water cancels a hundred-course
fall. **There is no timer, no payment and no leaderboard** - the same rule that cut two finished
casino games rather than ship a machine that could not be judged.

**The signal is not built.** Running a light a hundred courses up the shaft to fire the rim's
mast ring is the obvious next payoff and a vertical transmitter that tall is its own machine with
its own contract. The bell at the bottom does the job today with no redstone in it at all: cheap,
1.19, nothing to desynchronise, and audible from the gallery - so ringing it tells everyone
watching that somebody just finished.

**Still open:** nothing has been placed in game; the four designs are not folded into the park's
own assembly or `sync.yaml` (that pipeline is being edited in parallel); and the twelve v1
designs are still standing, one command from removal once v2 is walked.
