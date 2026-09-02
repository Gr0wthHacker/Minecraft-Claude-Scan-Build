# The park's ground grid: what it leaves, what it cannot, and where a grid is the wrong answer

Step one of the park is the ground and nothing else. This document is the measurement of it: every
block of lawn the street layout leaves, which build goes in which, the problems found and fixed,
and the places where a rectilinear grid is not the right geometry.

Everything below is measured, not asserted. Two tools do the measuring and both are checked in:

```bash
python -m mcbuild gen configs/park_ways.yaml   # the ground layer:  problems 0, one component
python tools/park_lots.py                      # every lot the grid leaves
python tools/park_lots.py --verify             # ...and whether each build fits the lot it is given
python -m tools.park_lamps                     # every lamp mast, by the line it stands on
python -m pytest -q tests/test_parkways.py     # 19 tests, the lot rule first
```

---

## 0. The headline

**The grid as first written could not hold the park.** Measured against the 24 builds in
`park_final.world.json`:

| | before | after |
|---|---|---|
| lots left by the grid | 34 | 22 |
| largest lot anywhere | **34 x 32** | **131 x 72** |
| builds with a lot that holds them | **4 of 24** | **17 of 21** |
| builds with NO LOT AT ALL | **20** | 0 |
| lamp masts standing off every verge line | 44 of 118, on 14 lines | **0**, on 10 lines |
| back promenade lamps | **0** on a 600-block walked route | 27 |
| lots spanning two territories | 1, of 20,097 cells | 0 |

Every check the pipeline already had passed the first version: `problems: 0`, one connected
component, no currency, no expensive tier, no cobblestone, every block state legal. **The failure
is a property of the shape of the holes BETWEEN the cells, and every check in this pipeline is per
cell.** That is why `tools/park_lots.py` exists and why the lot rule is now a test.

The four builds that still do not fit are programme conflicts, not grid faults, and each is listed
with its arithmetic in §5.

---

## 1. What was wrong: a grid laid to a ruler is a car park

The first schedule divided each 170-long land into **four avenues every 42 U**, 9 wide, with a
27-across plaza at each end, plus **one mid-block walk at V62 in every land** and a back promenade
at **V110**. None of those numbers came from anything the park has to hold.

Measured, that produced 34 lots of which 26 were between 32x29 and 34x32 — a uniform tile field.
The park's inventory is not uniform:

    Mine Coaster   111 x 71     Prism Ascent    93 x 72     Carousel Court  68 x 71
    Sky Lift        62 x 71     Mining Square   56 x 46     Boomtown Spine  53 x 46

**Five separate causes, each of which looked reasonable on its own:**

1. **The mid-block walk cut the three deepest things in the park in half.** At V62 it ran through
   the Mine Coaster's column, the Prism Ascent's and the Carousel/Sky Lift stack. A cross walk
   belongs where a *column's own stack of builds* meets, which is a different depth in every land
   and no depth at all in a column carrying one deep ride.
2. **The back promenade sat in the middle of the public floor.** At V110 it split a 104-deep band
   into 81 and 12, so nothing over 81 deep had anywhere to stand — and five builds are deeper.
3. **The avenues fell where the arithmetic put them**, not on the seams between the columns each
   land's programme needs.
4. **Verges were being taken out of the middle of lots.** A lamp two cells outboard of an avenue's
   border stands *inside the building lot behind it*; measured, that cost four blocks of usable
   width on every column — on its own enough to put the Mine Coaster's lot one block under its 71.
5. **Nothing crossed a reach except the spine**, so the Frontier's coaster column, the whole Claim
   Line reach and the Midway's arrival column measured as ONE 20,097-cell lot spanning two
   territories. Two lands were sharing a lot and nothing said so.

---

## 2. The grid as it now stands

### 2.1 Depth — the programme, and the street reserve between its bands

`PARK_FINAL_ARCHITECTED_PLAN.md` programmes the 200 of depth; the streets take the seams between
its bands, and **every street carries its own verge, which is not lot ground.**

| V | what | width | lot depth left |
|---|---|---|---|
| 0–5 | arrival apron, lawn, against the connector edge | | |
| 6–18 | **SPINE**, all 600 | 13 | |
| 19–23 | spine verge — lamp line V20 | | |
| **24–120** | **public floor LOTS** | | **97** |
| 121 | promenade verge — lamp line V121 | | |
| 122–127 | **BACK PROMENADE** (absent over three columns) | 5 | |
| 128–129 | promenade verge — lamp line V129 | | |
| **130–153** | **exit / observation LOTS** | | **24** |
| 154–156 | **SERVICE LANE** | 3 | |
| **157–169** | **service LOTS** | | **13** |
| 170 | rim edge — one dressed course and a post rhythm | | |
| 171–199 | protected rim and void reserve — **0 paved cells, asserted** | | |

Two numbers here are load-bearing and were each arrived at by measurement, not preference:

- **The spine is at V12, not V14.** At V14 its r13 plazas reached V1–27 and bit four courses off
  the front of every column they stood between — and three of those columns are spoken for to the
  block (Frontier A stacks 96 into 96; the Midway's ride column 130 into 130). At V12 with r11 the
  plaza spans V1–23, entirely inside the programmed threshold band, and not one lot loses a cell.
- **The promenade is 5 wide, not 7.** At 7 the exit-band lots come out 23 deep against a Forge Deck
  programmed at exactly the band's own 24. One block, and it decides whether the Prismworks exit
  route exists.

### 2.2 Length — the avenues sit on the column seams

An avenue is a seam between lots. Column widths below are **usable after verge**.

**FRONTIER** U0–169 · supply 170 · columns 158 · used 157 (**99.4%**)

| | U | usable | holds |
|---|---|---|---|
| col A | 0–39 | 40 | Trailhead Gate (39) · Prospecting Porch (40) |
| avenue | 41–45 | 5 wide | lamp lines U40, U46 |
| col B | 47–93 | 47 | Boomtown Spine (46) · Mining Square (46) · Assay + Prize (46) |
| avenue | 95–97 | 3 wide | lamp lines U94, U98 |
| col C | 99–169 | 71 | **Mine Coaster (71)** |

> The second avenue is 3 wide **on purpose**. At 5 the arithmetic comes out exactly one block short
> and the Mine Coaster loses its 71st column. It is the alley behind Boomtown, and the coaster's
> real approach is the Mining Square in front of it.

**MIDWAY** U215–384 · supply 170 · columns 152 · used 145 (95%)

| | U | usable | holds |
|---|---|---|---|
| col A | 215–255 | 41 | Arrival Court (41) · Snack Window (41) |
| avenue | 257–263 | 7 wide | lamp lines U256, U264 |
| col B | 265–336 | 72 | **Carousel Court (71) over Sky Lift (71)** |
| avenue | 338–344 | 7 wide | lamp lines U337, U345 |
| col C | 346–384 | 39 | Skill Arcade (33) · Prize Point (33) |

**PRISMWORKS** U430–599 · supply 170 · columns 160 · used 159 (**99.4%**)

| | U | usable | holds |
|---|---|---|---|
| col A | 430–465 | 36 | Foundry Gate (36) |
| avenue | 467–469 | 3 wide | lamp lines U466, U470 |
| col B | 471–521 | 51 | Prism Array (51) over Resonance Vault (41) |
| avenue | 523–525 | 3 wide | lamp lines U522, U526 |
| col C | 527–599 | 73 | **Prism Ascent (72)**, Forge Deck (66) in the exit band |

> Both Prismworks avenues are 3 wide because this land's own programme is **159 of its 170** in raw
> column. That is a fact about the programme, not a preference about streets — see §5.4.

**REACHES** — a threshold handoff at each reach's own edge (3 wide), and the causeway between them
is the spine and the promenade running through:

    Claim Line     U170-172 | usable U174-210 (37) | U212-214    holds the Signal Heron garden
    Wyrm's Cross.  U385-387 | usable U389-426 (38) | U427-429    holds Wyrm's Crossing (36)

### 2.3 The promenade stops rather than swerving

Three columns carry a single build deeper than any promenade can clear: the Mine Coaster (111), the
Carousel over the Sky Lift (130), the Prism Array over the Resonance Vault (109). The promenade is
**gapped over U98–169, U264–337 and U470–522**. You walk *around* those three blocks, on the avenues
either side; the loop still closes and the park is still one connected walk.

`promenade_curve` is implemented (piecewise-linear control points, so the promenade can swerve
behind a deep ride instead of being drawn through it) and is **not used** — see §6.4 for why a
swerve was tried and rejected here in favour of a clean stop.

---

## 3. The measured lot table

Every block of lawn the grid leaves, ≥150 cells, inside V0–169. `max rect` is the largest
axis-aligned rectangle that actually fits — a blob's *area* says nothing about capacity, because an
L of 4,000 cells holds no 50x50.

| # | land | band | V span | U span | cells | fill | max rect V×U | at V,U | build(s) it holds |
|---|---|---|---|---|---|---|---|---|---|
| 0 | midway | public floor | 19–153 | 264–337 | 9947 | 1.00 | **131 × 72** | 23,265 | Carousel Court · Sky Lift |
| 1 | frontier | public floor | 19–153 | 98–169 | 9686 | 1.00 | **130 × 71** | 24,99 | Mine Coaster |
| 2 | (all) | service | 157–169 | 0–599 | 7800 | 1.00 | 13 × 600 | 157,0 | Works Yard · Service Gallery |
| 3 | prismworks | public floor | 19–122 | 526–599 | 7660 | 1.00 | **97 × 73** | 24,527 | Prism Ascent |
| 8 | prismworks | public floor | 19–153 | 470–522 | 6939 | 0.97 | 73 × 51 | 81,471 | Prism Array · Resonance Vault |
| 4 | frontier | public floor | 19–122 | 46–94 | 5038 | 0.99 | 97 × 47 | 24,47 | Boomtown Spine · Mining Square |
| 5 | frontier | public floor | 19–122 | 0–40 | 4236 | 0.99 | 98 × 40 | 23,0 | Trailhead Gate · Prospecting Porch |
| 6 | Claim Line reach | public floor | 19–122 | 173–211 | 4053 | 1.00 | 100 × 39 | 21,173 | *heron garden* |
| 7 | Wyrm reach | public floor | 19–122 | 388–426 | 4053 | 1.00 | 100 × 39 | 21,388 | Wyrm's Crossing |
| 10 | midway | public floor | 19–122 | 345–384 | 4019 | 0.97 | 53 × 39 | 23,346 | Skill Arcade · Prize Point |
| 11 | midway | public floor | 19–122 | 215–256 | 4001 | 0.92 | 50 × 41 | 23,215 | Arrival Court · Snack Window |
| 9 | prismworks | public floor | 19–122 | 430–466 | 3816 | 0.99 | 97 × 36 | 24,430 | Foundry Gate |
| 12 | prismworks | exit/obs | 128–153 | 526–599 | 1922 | 1.00 | 24 × 74 | 130,526 | Forge Deck |
| 13 | frontier | exit/obs | 128–153 | 46–94 | 1272 | 1.00 | 24 × 48 | 130,46 | Assay and Prize Office |
| 14 | frontier | exit/obs | 128–153 | 0–40 | 1063 | 1.00 | 24 × 40 | 130,0 | *spare* |
| 15 | midway | exit/obs | 128–153 | 345–384 | 1038 | 1.00 | 24 × 40 | 130,345 | *spare* |
| 16 | Claim Line reach | exit/obs | 128–153 | 173–211 | 1012 | 1.00 | 24 × 39 | 130,173 | *spare* |
| 17 | Wyrm reach | exit/obs | 128–153 | 388–426 | 1013 | 1.00 | 24 × 39 | 130,388 | *spare* |
| 18 | prismworks | exit/obs | 128–153 | 430–466 | 959 | 1.00 | 24 × 36 | 130,430 | *spare* |
| 19 | midway | exit/obs | 128–153 | 215–256 | 869 | 0.80 | 15 × 41 | 139,215 | *spare — the Circus eats its front* |
| 20 | (all) | threshold | 0–5 | 0–599 | 3158 | 0.88 | 1 × 600 | 0,0 | arrival apron |
| 21 | midway | (circus island) | 118–132 | 228–242 | 177 | 0.79 | 11 × 11 | 120,230 | the Aeronaut balloon |

**Six spare lots** in the exit/observation band (24 deep, 36–40 long) are unallocated. That is the
band programmed for "exit, reward, and route-integrated observation" and it is where the surviving
programme has slack — see §7.1.

---

## 4. Which build goes in which lot

Verified cell by cell against the shipped lawn by `python tools/park_lots.py --verify`. Coordinates
are the near corner in (V, U), and the table lives in `tools/park_lots.PLACEMENT` so it is checked
by test rather than transcribed.

| build | footprint V×U | at V,U | lot | verdict |
|---|---|---|---|---|
| Trailhead Gate | 45 × 39 | 24, 0 | Frontier A | fits |
| Prospecting Porch | 51 × 40 | 69, 0 | Frontier A | fits |
| Boomtown Spine | 53 × 46 | 24, 47 | Frontier B | fits |
| Mining Square | 56 × 46 | 78, 47 | Frontier B | **13 deep short** (holds 43 × 47) |
| Assay and Prize Office | 20 × 46 | 130, 47 | Frontier B exit | fits |
| **Mine Coaster** | **111 × 71** | 24, 99 | Frontier C | fits |
| Works Yard | 18 × 36 | 157, 125 | service | **5 deep short** (holds 13 × 56) |
| Signal Heron | 52 × 45 | 34, 174 | Claim Line reach | **7 wide short** (holds 52 × 38) |
| Arrival Court | 48 × 41 | 24, 215 | Midway A | fits |
| Snack Window | 27 × 41 | 77, 215 | Midway A | fits |
| Carousel Court | 68 × 71 | 24, 266 | Midway B | fits |
| Sky Lift | 62 × 71 | 92, 266 | Midway B | fits |
| Skill Arcade | 51 × 33 | 24, 346 | Midway C | fits |
| Prize Point | 20 × 33 | 80, 346 | Midway C | fits |
| Wyrm's Crossing | 63 × 36 | 24, 389 | Wyrm reach | fits |
| Foundry Gate | 53 × 36 | 24, 430 | Prismworks A | fits |
| Prism Array | 53 × 51 | 24, 471 | Prismworks B | fits |
| Resonance Vault | 53 × 41 | 82, 471 | Prismworks B | fits |
| **Prism Ascent** | **93 × 72** | 24, 527 | Prismworks C | fits |
| Forge Deck | 24 × 66 | 130, 527 | Prismworks C exit | fits |
| Service Gallery | 18 × 41 | 157, 550 | service | **5 deep short** (holds 13 × 50) |

**Eight modules need no lot, and the grid IS them.** This is not a dodge — six of the eight are
role `path` in `park_final.world.json`:

| module | why |
|---|---|
| Frontier / Midway / Prismworks / Frontier Reach / Prism Reach Line (6 × 170 or 6 × 45) | these ARE the spine |
| Claim Line (75 × 41) | the plan calls the reach "one safe, 5-wide causeway" — the spine and promenade through it |
| Welcome Court (51 × 41) | "low open meet marker, four decision signs, no stalls in the centre" — the Midway's arrival plaza |
| Sky Lift Sloth (46 × 25) | "hanging from a real Sky Lift outer cable/arch" — it has no ground footprint |

---

## 5. The problems, and what was done about each

### 5.1 Fixed in the grid

| # | problem | measured | fix |
|---|---|---|---|
| 1 | one mid-block walk at V62 cut the three deepest builds in half | 3 columns | walks are per-land, per-column `{v, u0, u1}`; a deep-ride column gets none |
| 2 | back promenade at V110 split the public floor 81 / 12 | 5 builds homeless | moved to the public/exit seam V122–127 |
| 3 | avenues on a uniform 42 rhythm | largest lot 34 × 32 | avenues are declared per land on the column seams |
| 4 | avenue lamps two cells into the lot behind | −4 U of usable width per column | 1-cell verge on an avenue; spine and promenade keep their designed 2 |
| 5 | nothing crossed a reach but the spine | one 20,097-cell lot across two lands | threshold handoffs (`thresholds`) at each reach edge |
| 6 | spine plazas at r13 bit 4 courses off every column front | 6 columns | spine moved to V12, plazas to r11 → the disc fits V1–23 |
| 7 | the promenade's junction "widening" spilled past the last avenue into the *gapped* column beyond | Mine Coaster −14, Sky Lift −31, Resonance Vault −14 | **nothing is drawn** for a promenade junction; the crossing is lit from underfoot |
| 8 | 7-wide promenade left the exit band 23 deep | Forge Deck −1 | promenade narrowed to 5 |
| 9 | the heron's reserved garden was 55 × 51 for a bird measuring **14 × 32**, and it sat squarely on the Mine Coaster's column | −2,805 cells from the largest lot in the park | garden re-sited to the Claim Line reach at 27 × 37, where the plan says the Signal Heron stands |
| 10 | lamps on 14 different V lines, 13 stacked on one and 10 on another; **the back promenade had none at all** over 600 blocks | 44 of 118 off-line | see §5.3 |
| 11 | the Prismworks cross walk reached **neither** avenue — a 51-block walkway between the Prism Array and the Resonance Vault with no way off it | 153 stranded cells | every walk is drawn to the STREETS it joins, not to its column's usable width |

### 5.2 Fault #7 is worth reading twice

The promenade's junctions were drawn as small widened squares (r5 discs). Individually harmless.
But **the last avenue before a promenade gap is always the avenue beside a gapped column** — and
the gapped columns are exactly the three builds in the park with zero slack anywhere. A widening
three cells wider than its own street reached past that avenue and took 14 to 31 courses off the
Mine Coaster, the Sky Lift and the Resonance Vault.

A square two cells wider than its own street was never a square. It is gone; the froglights that
justified it are placed on the crossing itself, which is already paved and costs no ground.

### 5.3 The lamps

Counted off the block list — never from a picture, because `render3d` draws rods, fences, walls and
iron bars all as full cubes and has now hidden six separate faults on this park.

| V line | masts | what |
|---|---|---|
| 4 | 28 | spine west verge |
| 20 | 27 | spine east verge |
| 29 · 51 · 73 · 95 · 117 · 139 | 6 each | the avenue rhythm, 22 apart |
| 121 | 14 | promenade front verge |
| 129 | 13 | promenade back verge |

**118 masts, 10 lines, 0 off-line, 0 refused.** The count is now written into the design's own
sidecar as `lamps_per_line`, so this is a number you read rather than a thing you must go and
measure.

Two rules are now in code rather than emergent:

- **A lamp may move ALONG its own line and never across it.** The nudge that walks a post off
  paving runs in the street's own direction only; the line is decided by the caller and the search
  cannot change it.
- **An avenue's nudge window is capped at half its own rhythm** (`WINDOW_SHORT`). A longer nudge
  lands a lamp nearer its neighbour's station than its own, which is exactly how thirteen ended up
  stacked on one line. Past the window it is **dropped and counted** — a missing lamp is invisible,
  a lamp thirteen blocks off its line is not.

The spine and promenade keep the long window because a 23-across plaza swallows their verge for its
whole length; at a three-block nudge the spine's east verge came out with a 110-block hole.

### 5.4 The four that do not fit, and they are programme conflicts

Each is arithmetic, not a grid fault, and each has a one-line resolution that is **Jack's call, not
a silent edit**.

**(a) Mining Square — 56 × 46 declared, 43 × 47 available (13 deep short).**
Frontier column B has 97 of public floor and owes Boomtown Spine (53) + Mining Square (56) = 109,
before any seam. The column cannot be deepened: gapping the promenade over col B as well would
leave the Frontier's back route covering U0–45 out of 170, which is not a route.
*Recommendation:* **re-spec Mining Square to 43 × 46.** It is role `path` — "open queue decision
point, coaster status, low ore-cart/claim marker" — an open square, not a building, and 43 deep is
still larger than the Arrival Court. *Alternative:* move Assay and Prize Office into the Mine
Coaster's own exit band (V135–153 behind the coaster, 71 wide — it is 19 deep there against 20, so
this needs its own block found) and stack Mining Square into col B's exit band.

**(b) Works Yard 18 × 36 and (c) Service Gallery 18 × 41 — 13 deep available (5 short).**
The service band is V152–169, **exactly 18 deep**, and both modules declare 18. A concealed service
lane inside an 18-deep band is arithmetically impossible if the sheds are also 18.
*Recommendation:* **re-spec both to 13 deep.** They are hidden plant rooms — 13 × 36 and 13 × 41
hold the same equipment, and the width is unconstrained (the service band runs the full 600).
*Alternative:* delete the continuous service lane and reach each shed by a spur off the avenue
tails, which already run to V157; that gives the full 18 and costs the back-of-house road.
*Rejected:* moving the lane to V152–154 gains the sheds 2 and costs Forge Deck its 24th course.

**(d) Signal Heron — 52 × 45 declared, 38 wide available (7 short).**
**The bird measures 14 × 32.** The declared footprint is 3.7× the sculpture. The reserved garden is
27 × 37, which is the bird plus a viewing apron on every side, and it is verified by test that the
heron sits wholly inside it.
*Recommendation:* **re-spec the Signal Heron's footprint to 27 × 37** to match what is reserved.
Nothing needs to move.

### 5.4b The component count on the model says nothing

`python -m mcbuild gen` reports `components: [131111]` — one piece — and that is trivially true of
any ground layer here, because the lawn covers all 120,000 cells. **The question worth asking is
whether the PAVING is one walk**, and asked properly it was not: the Prismworks cross walk was 153
cells reaching neither avenue, because a column's usable width stops one cell short of the avenue
at its lamp line and the walk had been drawn to the column rather than to the streets it joins.

Now: **one paved walk of 18,195 cells, 98.8% of all paving**, plus the 600-cell rim edge course
(a dressed edge, not a route) and 74 single-cell lamp footings standing on their verges.
`test_the_paving_is_ONE_CONNECTED_WALK` pins it.

### 5.5 One thing measured and deliberately left alone

The **service band is a single 13 × 600 lot** — the avenues reach V157 and stop, so nothing breaks
it into per-land yards. That is correct for a back-of-house strip and was left. If service yards
ever need to be told apart, extend the avenues to the rim course.

---

## 6. Where a grid is the wrong answer

A rectilinear grid everywhere is a car park. Four geometries were considered; **two are implemented**
and two are recommended with their costs stated.

### 6.1 IMPLEMENTED — round plazas at every avenue head

`plaza_shape: round`, r11 (23 across), twelve of them: one at each avenue's spine end.

**This is the free win, and it is worth stating why.** A round plaza and a square one at the same
radius occupy the same *reserve*; the difference is that the disc does not pave its four corners,
and those corners go back to the lawn as lot ground. The plaza fights the shape of nothing and
gives ground back. There is no version of this trade that loses.

`test_a_round_plaza_gives_its_corners_back_to_the_lawn` asserts the corner of the plaza's own
bounding square is still lawn — which is what distinguishes a disc from a square with a curved
pattern painted on it.

### 6.2 IMPLEMENTED — the Midway Circus, a ring road round a green

`roundabouts: [{v: 125, u: 235, r: 13, ring: 5}]` — an annulus at r8–13 on the back promenade, with
a **reserved lawn island 15 across** carrying the moored Aeronaut balloon.

The balloon is the one genuinely radial centrepiece the park has; a square lot round it wastes its
corners and fights its shape. The island is reserved by exactly the rule a feature lot is, so no
path, plaza, lamp or bench can land on it — which is also the whole difference between a roundabout
and a disc. The balloon's own plan is 177 cells with a maximum radius of **7.28** from the circus
centre against an island radius of 7.5: it fits, verified by test, with the green showing round the
basket and the envelope overhead.

**It is on the promenade and not the spine, and that was forced by measurement.** The Midway's spine
has a 41-wide and a 72-wide column hard against it, both spoken for to the block (the ride column
stacks 130 into 130). A 27-across circus there takes four courses off the front of each. On the back
promenade, Midway column A has 19 courses of slack and the exit lot behind it is unallocated — so
the circus costs one *spare* lot's front (lot 19, fill 0.80) and nothing that is programmed.

### 6.3 The voxel craft — minimum radius, measured

A rasterised circle is an octagon at small radius. The honest measure is **the longest straight flat
on the rim as a fraction of the diameter** — that flat is what the eye reads as a polygon edge:

| r | across | longest flat | flat / diameter | reads as |
|---|---|---|---|---|
| 5 | 11 | 5 | **0.45** | a diamond |
| 6–7 | 13–15 | 5 | 0.33–0.38 | an octagon |
| 8 | 17 | 5 | 0.29 | borderline |
| 9–10 | 19–21 | 7 | 0.33–0.37 | an octagon again |
| **11** | 23 | 7 | **0.30** | a circle |
| 13 | 27 | 7 | 0.26 | clearly a circle |
| 15–20 | 31–41 | 7–9 | 0.22–0.23 | unambiguous |

**Rules that follow, and they are what the two implemented pieces are built to:**

- **r ≥ 11 for a filled disc** to stop reading as a polygon. The plazas are r11.
- **A ring reads better than a disc at the same radius**, because the eye has two concentric
  boundaries to integrate rather than one. The Circus is r13.
- **A ring band must be at least 4.** Measured on an r13 ring, the real walkable thickness is
  `ring + 1` and its variation round the bearings is: band 2 → 2.75–3.25, band 3 → 4.00–4.50,
  band 4 → 4.25–**5.50** (the widest variance — it visibly pinches), band 5 → 5.50–6.50,
  band 6 → 7.00–7.25. **Band 5 is the first that is both wide enough to walk and even enough not to
  pinch.** The Circus uses 5, which matches the promenade it stands on.
- Every ring from band 2 up is 4-connected, so a ring road never breaks — that is not the failure
  mode; pinching is.

### 6.4 IMPLEMENTED BUT NOT USED — the curved promenade

`promenade_curve: [[u, v], ...]` interpolates the promenade's centre depth between control points,
so it can swerve behind a deep ride instead of being drawn through it. The machinery is in and
tested by construction; **it is switched off, and the reason is worth keeping.**

A swerve from V125 to V140 to clear the Mine Coaster has to ramp somewhere. Ramping over the
column's own front eats the coaster's corner; ramping over the avenue before it is a 45° dogleg on
a 5-wide road; ramping earlier eats Boomtown's exit band. **Every place the ramp can go is already
spoken for**, which is the same finding as everything else in §5.4 wearing a different hat. A clean
stop is honest and a swerve into a lot is not.

Point it at a land with slack and turn it on.

### 6.5 RECOMMENDED, NOT BUILT — three more, with costs

**(a) A crescent approach to the Mine Coaster.** Frontier's second avenue is 3 wide and runs dead
into the coaster's 71-wide flank. A gently curved approach that meets the coaster's station off
axis would read far better than a straight alley into a wall. *Cost:* about 300 cells of lawn from
column B's rear, which is the Mining Square's ground — so this is only affordable if Mining Square
is re-specced per §5.4(a) anyway. **Do these two together or neither.**

**(b) A widened arrival forecourt at each land's gate.** The three spine plazas at r11 are 23
across, and a theme-park entrance crowd wants more. Enlarging the Frontier's first plaza (U43) and
Prismworks' first (U468) to r15 costs nothing at the front (V1–23 has room), but reaches V27 at the
back — 4 courses off Trailhead Gate and Foundry Gate. Both have slack (Foundry Gate has 44 courses
spare; Trailhead has 1). *Recommendation:* **do Prismworks, not Frontier.**

**(c) A narrowed intimate lane on Boomtown Spine.** `PARK_FINAL` calls Boomtown "a 5-wide street
with only real doors". The grid currently gives column B a 47-wide lot and no internal street; the
Boomtown street is inside the module and belongs to whoever builds it. *No grid change wanted* —
recorded so nobody adds one.

---

## 7. What the numbers say about the programme

### 7.1 Every land is between half and two thirds raw footprint

| land | programme footprint | land area (V0–169) | share |
|---|---|---|---|
| Frontier | 18,258 | 28,900 | **63%** |
| Prismworks | 15,802 | 28,900 | 55% |
| Midway | 14,648 | 28,900 | 51% |

In **column** terms, which is what actually binds, the picture is tighter: Frontier uses 157 of its
158 usable U (99.4%) and Prismworks 159 of 160 (99.4%). **There is no room in either land for a
fourth column, a wider avenue, or a circus on the spine**, and that is why several of the answers
above are "narrow the street" rather than "move the building".

The Midway is the one land with real slack — 145 of 152 usable U, and 19–23 courses spare in two of
its three columns.

### 7.2 The exit band has six spare lots

24 deep × 36–40 long, at V130–153, in every land and both reaches. That is the band programmed for
"exit, reward, and route-integrated observation" and only two of eight lots are allocated (Assay and
Prize, Forge Deck). **If anything in the programme needs re-homing, that is where the room is.**

### 7.3 Materials

| | blocks | share of all | share of BUILT |
|---|---|---|---|
| lawn (moss block + carpet) | 106,231 | 84.0% | — |
| cheap tier | 120,487 | 95.3% | 70.5% |
| ok tier | 5,975 | 4.7% | **29.5%** |
| expensive tier | **0** | 0.0% | 0.0% |

`ok` is entirely `deepslate_tiles` (2,246), `smooth_stone` (2,009), `polished_deepslate` (1,498),
`iron_bars` (140) and `iron_chain` (82) — the Prismworks paving and two lamp fittings.

**The 78–86% / 10–16% policy band cannot be read against a design that is 84% lawn**, and both
figures are given above so the right one can be chosen. Against BUILT material the mix is 70/30,
which is *above* the ok band; against all blocks it is 95/5, which is below it. Nothing is currency,
nothing is expensive, and there is **no cobblestone anywhere** — all four asserted by test.

Verified per block: every one of the 34 materials passes `blocks.available`, `blocks.spendable`,
`palette.tier != expensive` and carries no `cobble` in its name. (`python -m mcbuild gen` prints a
warning that 12 blocks are "not in the provisional 1.19 list" — that list is the ~191-block
provisional allowlist CLAUDE.md already records as incomplete; `blocks.available` accepts all 34.)

---

## 8. What the tests pin

`tests/test_parkways.py`, 19 tests. The first is the one this whole exercise exists for.

| test | what it stops coming back |
|---|---|
| `every_build_the_park_owes_has_a_lot_that_holds_it` | the 20-of-24-homeless failure |
| `the_known_shortfalls_are_a_ceiling_and_never_get_worse` | the four residuals growing — a **ceiling**, not a snapshot, so a fix passes and a regression fails |
| `every_module_is_either_placed_or_declared_not_to_need_ground` | a module nobody noticed |
| `the_biggest_lot_in_each_land_is_bigger_than_a_car_park_tile` | any future return to a ruler grid |
| `a_lamp_stands_on_one_line_and_never_wanders_across_it` | the 14-line scatter |
| `the_back_promenade_is_actually_lit` | a 600-block route silently unlit |
| `no_lamp_stands_on_paving_or_inside_reserved_ground` · `two_lamps_never_bunch` | Jack's two original lamp complaints |
| `the_protected_rim_reserve_carries_nothing` | anything creeping into V171–199 |
| `the_lot_bands_are_lawn_and_the_street_bands_are_paved` | a band quietly sliding a course |
| `the_promenade_stops_over_the_three_columns_with_no_slack` | a street redrawn through a ride |
| `a_reach_separates_the_lands_it_joins` | two lands sharing one lot |
| `a_round_plaza_gives_its_corners_back_to_the_lawn` | a square wearing a curved pattern |
| `the_circus_is_a_RING_with_a_green_in_it` | a roundabout becoming a disc |
| `the_balloon_sits_wholly_on_the_circus_island` · `the_heron_sits_wholly_inside_its_own_garden` | "the air balloon is in the dead center of one of the walkways" |
| `nothing_in_the_ground_layer_is_currency_expensive_or_cobblestone` | the economy and the banned block |
| `the_paving_is_ONE_CONNECTED_WALK` | a walkway with no way off it — invisible to the model's own component count |
| `the_lawn_covers_the_whole_envelope` | void |

**Test suite: 26 failures before this work and 26 after. 0 introduced.** 4,518 pass, 34 skip.

All 26 are pre-existing and in files that never import `parkways`: `test_park.py` (12),
`test_evidence.py` (6), `test_park_plan.py` (2), `test_vertical_park.py` (2), `test_frontier.py`,
`test_wayfinding.py`, `test_designs.py`. Confirmed two ways — by stashing this work and re-running
the affected files (identical 18 failures), and because `test_designs.py::test_all_configs` aborts
inside `wayfinding.py` on `'Haunted Manor' names no real module` long before it ever reaches
`park_ways.yaml`. Do not fix them here; they belong to work in flight elsewhere.

---

## 9. Open, and Jack's call

1. **Re-spec four footprints** — Mining Square 43 × 46, Works Yard 13 × 36, Service Gallery 13 × 41,
   Signal Heron 27 × 37. All four are in `park_final.world.json`, which another process owns and
   which this work has not touched. Until they move, `KNOWN_SHORT` in the test records them.
2. **`park_final.world.json`'s own `at` positions are incompatible with any street grid** and were
   not used. **Eight modules have their declared `at` inside the arrival spine band (V < 24)** —
   Trailhead Gate, Boomtown Spine, Arrival Court, Carousel Court, Wyrm's Crossing and Foundry Gate
   all at V18, Skill Arcade at V20, Claim Line at V6 — and the Carousel/Sky Lift stack at V18–151
   needs 134 of depth, which exists only if the spine is built over. The gaps between its columns
   are 1 to 9 blocks wide, so there are no streets in it at all. The placement table in §4
   supersedes those positions; the footprints and roles are taken from it unchanged.
3. **Nothing here has been looked at in game.** Every geometric claim is from the block list or a
   measurement, deliberately — `render3d` draws rods, fences, walls and bars as full cubes and has
   hidden six faults on this park. Colour and the read of the paving patterns can only be judged in
   world.
4. **The three recommended geometry changes in §6.5** — the crescent coaster approach, the enlarged
   Prismworks forecourt, and leaving Boomtown's internal street alone.
