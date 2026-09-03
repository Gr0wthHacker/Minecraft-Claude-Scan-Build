# The Midway centre — move the wheel back, and put the Cascade between

Jack: *"move the wheel back and lets fill the area between with something more interesting"*, then
*"we have other lakes though, we cant have tons of lakes and water, its repetitive, it should
instead be a big water fountain sculpture or something unique and enjoyable."*

Measured off `out/Park Complete.litematic` and `configs/park_ways.yaml` on 2026-09-03. Supersedes
`PARK_MIDWAY_BACKLOT.md`.

---

## 1. He is right about the water, and the count says by how much

**The park holds 3,377 water blocks in five places.** A second sheet of water in the Midway would
have been the third, and the nearest one is not the Claim Lake — it is 40 blocks in front of the
proposed site:

| U band | water | what |
|---|---|---|
| U180–224 | **2,268** | the Claim Lake — the "scenic lake as a congregation point" |
| U405–449 | 441 | the Wyrm Garden |
| U360–404 | 273 | Midway column C |
| **U270–314** | **228** | **the Welcome Court's own fountain, and the Sky Lift's water channels** |
| U135–179 | 167 | Frontier |

The lagoon is dropped. What replaces it has to be water used the *other* way — **vertically, on an
object** — and it has to be something you go to rather than something you walk past.

## 2. Moving the wheel back is an improvement, not a cost

The park is composed on one line — `park_ways.yaml`: *"the gate's two doors, the Welcome Court's
walk and the Sky Lift's hub are all on U300."* Moving the wheel along that line lengthens the
composition. It also fixes a real defect in the view:

| | ring centre | from the gate doors (V18) | elevation to the crown |
|---|---|---|---|
| now | V90 | 72 blocks | **46°** — you crane your neck; the whole wheel does not fit the view |
| moved to V130 | V140 | 122 blocks | **31°** — the whole wheel, from the moment you clear the gate |

The Sky Lift crowns at **Y276, 74 courses over the lawn**, and there are currently **7 blocks**
between the back of the Welcome Court and its ring. The park's headline ride is jammed against its
own forecourt.

**Moving it costs one line.** `Sky Lift` is a `KEEP` artifact placed from `tools/park_lots.PLACEMENT`
at `(80, 266)`; it becomes `(130, 266)`. The model is untouched. Its marquee (V78) and `WHEEL LINE`
queue (V68) follow it onto the promenade in front — which is what `PARK_VERTICAL_MASTERPLAN.md`
calls the **Big Wheel Promenade**.

V130 is the park's own grid line: the start of the exit/observation band, where the Frontier Lookout
`(130, 0)` and the Forge Deck `(130, 527)` also begin.

## 3. The depth schedule fits to the block

Column B is V24–153, **130 courses**:

```
V  24- 79   56   Welcome Court            (as built)
V  80-120   41   THE NEW LOT              41 deep x 71 wide = 2,911 columns
V 121-129    9   promenade + its verges   (currently absent - see below)
V 130-151   22   Sky Lift                 (19 as built, 22 declared for clearance)
V 152-153    2   slack before the service lane
            ---
            130  of 130 available
```

**The promenade gap closes.** `promenade_gaps` skips U264–337 because *"the Carousel over the Sky
Lift (130 deep)"* filled column B — a stack that no longer exists. The band V121–129 × U264–337 is
**666 columns carrying 33 moss carpets and nothing else**, and walking the promenade's west end to
its east end currently costs **117 steps around** against ~75 through. With the wheel at V130 the
promenade runs in front of it, which is what a cross walk terminating on a landmark is for.

---

## 4. What goes between: **THE CASCADE**

A single monumental fountain sculpture on the axis at **V87–113 × U287–313 — 27 across, crown at
18 courses** — standing in a formal court that fills the rest of the lot.

### It is a different object from the Welcome Court's fountain, and that is measured

The court's fountain is **11 × 11 with 3 courses of water, 57 cells**, and the whole court tops out
at 11 courses. The Cascade is **27 across and 18 tall** — six times the footprint and nearly twice
the height of anything in the court. They read as a sequence, not a repetition: a small meet-point
basin where you arrive, a monument where you gather.

### The form, bottom to top

| | |
|---|---|
| **the basin** | 27 across, one course proud of the court, water two deep, with a coping ring wide enough to sit on |
| **the drum** | a 17-across **arcaded** drum standing in the basin — eight piers, eight arches, open all the way through, so it is a structure you see *into* rather than a plinth |
| **the falls** | water leaves the entablature over **every arch**, so the drum wears a ring of falling water |
| **the chamber** | inside the drum, 11 across and **dry**: a bench ring, a lit floor, and from it you look out through falling water in every direction |
| **the tiers** | above the entablature, two diminishing dishes cascading into each other and finally over the arches |
| **the crown** | an end-rod finial, so it reads at night from the top of the wheel |

### Why this is not more of the same water

- **It is vertical.** Roughly **320 cells of falling and flowing water on an object**, against the
  Claim Lake's 2,268 cells of horizontal sheet. Falling water is also one of the very few things in
  this game that genuinely *moves* — the same reason the lowland thicket's spore blossoms earned
  their place.
- **It is architecture, which is what this repo builds best.** *"What makes voxels read as
  architecture is regularity and openings, not damage"* — the rule the void tower, the sanctum, the
  campanile and the casino hall all arrived at separately. An arcaded drum is exactly that.
- **You go into it.** Nothing in the park lets you stand inside a piece of water. That is the
  "enjoyable" half, and it costs no new mechanism.

### How it sits in the route — you walk ROUND it, never into it

`gen/midway.py` already records the rule for a centrepiece: *"a LOW meet-point — fountain, clock
and map — that you walk round, never into."* The Cascade is not low, so the rule matters more, not
less:

- the 11-wide axis walk **splits into two 5-wide arms** at V85 and rejoins at V115. The main route
  is never obstructed and nobody gets pushed about by falling water on their way to the wheel;
- the chamber's two entrances are on the **cross axis** (east and west), on stepping stones over the
  basin — so stepping inside is a discovery off the route, not a toll on it;
- a **fingerpost** at V121/U300 where the axis meets the promenade: west to the Circus, east to the
  Skill Arcade and Prize Point, north to the wheel's queue.

And the vista it makes: from the gate's doors you look down eleven wide of walk, through the Welcome
Court, at a lit 18-course fountain on the axis — with a 76-course wheel rising behind and above it.
A 122-block vista needs a foreground object or it is just distance; this is that object, and at 18
courses against 76 it cannot compete with the thing it frames.

### The rest of the lot

Paved court on a world-aligned grid so it lines up with the park's own paving where the two meet;
four tree groups at the corners, outside the desire lines; seating on the basin coping and on the
walk arms. Roughly **half the lot stays open**.

### Two constraints, and one of them the lagoon would have had and this does not

1. **No dig list, no bowl under the plate.** The Cascade stands *on* the lawn at Y203 and up. The
   lagoon would have been a sealed tank hanging under a one-block skin over open void, with ~1,000
   lawn cells broken. This is the single biggest reason it is cheaper and safer.
2. **Water freezes, and dead water is worse than no water.** Still source blocks below block light
   10 turn to ice — the Atelier court froze on its first build with 29 ice blocks. The basin bed
   takes flush ochre froglight, the Claim Lake's own answer.
3. **The falls have to actually fall.** `civic._fountain` already paid for this lesson and it is
   quoted here so the next build does not re-learn it: *"three pools of nothing but source blocks
   is the log flume's own failure. It audits clean, costs nothing, looks exactly like a fountain in
   every render here, and never moves."* Every rim gets an open notch with the column under it left
   open, and `fluids.spread` verifies it in the test rather than the render being trusted.

### Rough bill

| | blocks |
|---|---|
| the Cascade — basin, drum, arches, tiers, crown | ~2,600 |
| its water | ~320 |
| court paving, kerbs, seating | ~1,700 |
| trees and planting | ~500 |
| promenade closure | ~370 |
| lighting | ~110 |
| | **~5,600**, and **no dig list at all** |

All cheap or ok tier: stone brick, chiseled stone brick, smooth stone, polished diorite, deepslate
brick, moss, oak, lanterns, ochre froglight, end rod, water.

---

## 5. Build order

1. `PLACEMENT`: `Sky Lift` `(80, 266)` → `(130, 266)`. Re-place, confirm no clashes.
2. `park_ways.yaml`: drop `[264, 337]` from `promenade_gaps` and fix the stale comment; regenerate
   `Park Ways` and re-ship. **This re-ships `Park Complete`, which every park design verifies
   against** — so it happens once, before the new design is generated.
3. `pf_front_midway.yaml`: the Sky Lift's marquee and `WHEEL LINE` queue move onto the promenade.
4. `PF Midway Cascade` at `(80, 266)`, footprint 41 × 71. New `civic` kind — it borrows
   `_fountain`'s cascade rules (the notch, the annulus rim, the distance-test circle) rather than
   restating them, because two modules with their own copy of "how does a basin not leak" is how a
   leak becomes two leaks.
5. Night pass to zero spawnable cells, and re-verify no water cell can freeze.

## 6. What needs Jack's call

1. **The wheel to V130.** Confirmed by the measurements above, but it is the park's headline object
   and moving it 50 blocks is not a silent change.
2. **Sound, or not.** The park contains **zero note blocks** in 273,356 — sound is a whole dimension
   nothing here has used, and a short chime you set off from inside the chamber would make the
   Cascade the one thing in the park you can *play*. It costs: `note_block` is **expensive** tier, so
   this is a declared allowance of about 8 of them plus a verified circuit — the same posture
   `island_run.yaml` takes for its 13 slime blocks, where the expensive material *is* the feature.
   Left out by default; say the word and it goes in.
3. **Whether the chamber is dry or a grotto.** Dry as drawn — a bench ring you look out from. The
   alternative is a shallow floor pool so you stand ankle-deep, which is more fun and makes the
   lighting harder.

---

## AS BUILT (2026-09-03)

All of it shipped. `PLACEMENT`: `Sky Lift` (80, 266) -> **(130, 266)**, `Midway Cascade` at
**(80, 266)**. `promenade_gaps` lost `[264, 337]`. `PF Midway Cascade` is
**2,150 blocks, one component, 0 problems, 0 buildability faults, 2,145 cheap + 5 declared
expensive**; `tests/test_cascade.py` is 9 cases and green.

### Four defects the build found, each of which passed every other check

- **A ONE-CELL NOTCH WORKS ON AN AXIS AND FAILS ON A DIAGONAL.** `_annulus` is one RADIUS wide,
  which on a diagonal is more than one CELL wide: the notch at (7,7) sits at r 9.90 and all four
  of its orthogonal neighbours are at 9.22 - still rim - so the bowl's water never reached it.
  **Four of the six waterfalls existed only in the block count.** A notch is a channel now.
- **A WATERFALL INTO A ONE-DEEP KERBED POOL RUNS STRAIGHT OVER THE KERB.** Falling water landing
  on a pool becomes a flowing sheet one course ABOVE it, and a rim level with the water has
  nothing standing in that course. It leaked 3,283 cells across the court and into the Welcome
  Court fifty blocks away. The moat is sunk and both rings are two courses.
- **A CAUSEWAY IS A GAP IN THE RIM AT EXACTLY THE SHEET'S LEVEL.** Laid flush it was an open
  channel from the moat into the chamber and out over the plaza. It is a humped bridge with
  parapets now - and the parapets are structural, not decoration.
- **THE CROWN STOOD ON THE DISH'S WATER**, which is not a support, and shipped as a fifteen-cell
  floating component. The dish is a ring around a jet column, which is what `_fountain` already
  says a top dish is.

### The one thing that could not be verified offline, stated rather than implied

`fluids.spread` **is not sound for a waterfall landing in a pool.** Falling water that lands on an
existing water level does not fall again in the model - it spreads sideways one course above, and
the fall above it then does the same thing one course higher, upward without limit. The evidence
that this is the model and not a hole: **raising the rim a course made the reported leak worse,
not better** (964 -> 1,823), and **a real hole does not climb.**

What IS proved: the basin flooded on its own is perfectly contained - **92 sources, 92 cells
reached, nothing outside its envelope** - and the falls genuinely fall (126 FALLING cells, nine
courses, six bays). Whether the plaza is dry underfoot is the one thing here that has to be looked
at in game.

### Also not verified: the chime's pitch

A note block's INSTRUMENT comes from the block underneath and is guaranteed - packed ice gives
`chime`. Its PITCH is a right-click, not a placement, so a printer puts all five down at note 0,
and `work.INTENTIONAL` does not compare `note` either. `chime_notes` is in the sidecar and tuning
it is a hand step, like clearing a dig list.

### Open

- The Cascade is **27 across against 19 tall**, which reads a little squat in `tools/look.py`.
  Worth a look in game before deciding whether to raise the drum.
- No night pass has been run over the new lot.
