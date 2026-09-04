# The major attractions against the shipped ground, and an audit of the pathways

Step two of the park: the ground is placed, and this is the measurement of whether the headline
rides can actually stand in it, be walked to, and be entered — plus the pathway audit Jack asked
for ("make sure they dont end weird, are symmetrical, and lead to properly carved areas").

Everything below is counted off the block list of the shipped litematic. Nothing is read off a
render: `render3d` draws a fence, a wall, a lightning rod and iron bars all as full cubes and has
already hidden six faults on this park.

```bash
python tools/park_attractions.py            # all four sections
python tools/park_attractions.py --lots     # does each attraction fit
python tools/park_attractions.py --access   # can it be reached and entered
python tools/park_attractions.py --paths    # dead ends, connectivity, mirror symmetry
python tools/park_attractions.py --lamps    # intersection lighting, and the rule for it
```

---

## 0. What was measured, and the one caveat that governs the lamp numbers

| | |
|---|---|
| artifact | `out/Park Ways.litematic`, **md5 `addbdc1dc030702d446b80aacb468d50`** |
| read at | y=0 (the ground course) and y=3 (the one course every land's lamp has a mast in and no rim post reaches) |
| frame | origin X97500 Y202 Z80300; **V = local x = world X**, **U = local z = world Z**, so V+ is east and U+ is south, and a module "facing west" faces **decreasing V, toward the spine** |
| programme | `park_final.world.json`, 29 modules; placement corners from `tools/park_lots.PLACEMENT` |

**THE GROUND LAYER MOVED THREE TIMES WHILE THIS WAS BEING MEASURED**, and that has to be stated
because it decides which numbers are durable:

    12:43  26,444 B                       118 masts on 10 lines, NO junction lighting at all
    13:20  26,964 B  md5 7ef4f96…         128 masts, all twelve avenue junctions quartered
    13:2x  26,781 B  md5 293756…          115 masts, junction work partly gone again
    13:26  26,9xx B  md5 addbdc1…         committed as 53f0e2a — the state measured below

Another stream owns `mcbuild/gen/parkways.py` and `configs/park_ways.yaml` and landed
`53f0e2a "a crossing is lit by the crossing"` in the middle of this audit — having independently
arrived at the same junction rule this audit derived, and at one clause this audit had got *wrong*
(see §3.4). **Sections 1, 2 and 3.1–3.3 are structural: they depend on the street schedule, which
has not changed across any of those four builds, and they hold.** §3.4 is a snapshot plus a rule;
the rule and its coordinate table are the durable part, because they are derived from the street
schedule rather than from where a rhythm counter happened to land.

---

## 1. The lots, and whether the major attractions fit them

### 1.1 First: four of the attractions in the brief do not exist in this programme

Searched by name through `park_final.world.json`: there is **no Big Wheel module, no Haunted Manor,
no Ghost Train and no Plummet.** Those four are configs of the *earlier* three-plot park
(`configs/the_big_wheel.yaml`, `haunted_manor.yaml`, `ghost_train.yaml`, `the_plummet.yaml`,
lots in `out/lots/midway.json`) and nothing in the 600×200 programme refers to them.

**The ferris wheel in this park is the SKY LIFT.** Its build parts are `gen: bigwheel, kind:
wheel`, its neighbour Carousel Court is `gen: bigwheel, kind: carousel`, and the park's own
wayfinding markers already name the Sky Lift *"THE BIG WHEEL"* on four signs. So the wheel is
present, at 62 × 71, under a different name — and the name mismatch between the module and its own
signage is worth resolving before anyone builds signs.

### 1.2 The measured table

`lot at that corner` is the largest all-lawn rectangle the placement corner actually commands in
the shipped ground, depth and width probed **independently** — probing width at a depth that is
already blocked reports "46 WIDE short" for a lot that is 47 wide and merely 14 shallow, which is
a report nobody can act on.

| attraction | role | declared V×U | at V,U | lot at that corner | verdict |
|---|---|---|---|---|---|
| **Mine Coaster** | ride | 111 × 71 | 24, 99 | **130 × 71** | fits |
| **Prism Ascent** | ride | 93 × 72 | 24, 527 | **97 × 73** | fits |
| **Carousel Court** | ride | 68 × 71 | 24, 266 | **130 × 71** | fits |
| **Sky Lift** (the wheel) | ride | 62 × 71 | 92, 266 | **62 × 71** | fits, with **zero slack in depth** |
| **Prism Array** | ride | 53 × 51 | 24, 471 | 54 × 51 | fits (1 course of depth spare) |
| **Resonance Vault** | ride | 53 × 41 | 82, 471 | 72 × 51 | fits |
| **Skill Arcade** | ride | 51 × 33 | 24, 346 | 52 × 39 | fits |
| **Prospecting Porch** | ride | 51 × 40 | 69, 0 | 52 × 40 | fits (1 course spare) |
| Trailhead Gate | landmark | 45 × 39 | 24, 0 | 97 × 40 | fits |
| Arrival Court | arrival | 48 × 41 | 24, 215 | 49 × 41 | fits |
| Foundry Gate | arrival | 53 × 36 | 24, 430 | 97 × 36 | fits |
| Boomtown Spine | building | 53 × 46 | 24, 47 | 97 × 47 | fits |
| Wyrm's Crossing | path | 63 × 36 | 24, 389 | 97 × 38 | fits |
| Forge Deck | path | 24 × 66 | 130, 527 | 24 × 73 | fits |
| Snack Window · Prize Point · Assay and Prize Office | | | | | fit |
| **Mining Square** | path | 56 × 46 | 78, 47 | **43 × 47** | **13 DEEP short**, and it crosses the back promenade |
| **Signal Heron** | sculpture | 52 × 45 | 34, 174 | **0 × 38** | **52 DEEP / 7 WIDE short**; crosses midway walk 1 and threshold U213 |
| **Works Yard** | service | 18 × 36 | 157, 125 | **13 × 475** | **5 DEEP short**, crosses the rim edge, **enters the protected rim V170–199** |
| **Service Gallery** | service | 18 × 41 | 157, 550 | **13 × 50** | **5 DEEP short**, crosses the rim edge, **enters the protected rim V170–199** |

**All eight headline rides fit. The four that do not are one path module, one sculpture and the two
service sheds** — the same four `PARK_GRID_PLAN.md` records, plus two facts that document does not
state and that change what they are:

### 1.3 The arithmetic on each of the four, and what is new

**(a) Mining Square — 56 × 46 declared, 43 × 47 available.** Frontier column B has 97 courses of
public floor (V24–120) and owes Boomtown Spine 53 + Mining Square 56 = **109** before any seam.
*New here:* the declared 56 does not merely overrun the lot, it **runs V78–133, straight through
the back promenade (V121–129) and 184 cells into the Assay and Prize Office behind it** — and the
Assay office's own front door at (130, 70) is one of the cells Mining Square claims. So this is
not a shortfall, it is a three-way collision.

**(b) and (c) Works Yard and Service Gallery — 18 deep declared, 13 available.** The service band
is V157–169, thirteen deep. *New here:* 18 from V157 reaches **V174**, which is across the rim
edge course at V170 and **four courses into the protected rim reserve V171–199** — a band
`PARK_FULL_BUILD_SPEC.md` reserves for "support, terrain, void safety, sightline protection", and
which the ground layer asserts by test as carrying zero paved cells. Calling this "5 deep short"
understates it: at the declared depth both sheds are a rule break, not a squeeze.

**(d) Signal Heron — 52 × 45 declared, and the bird itself measures 14 × 32.** The declared
footprint is 3.7× the sculpture. Placed at (34, 174) it reaches U218, **four columns into the
Midway**, overlapping the Arrival Court by 152 cells and the Snack Window by 36; it also crosses
midway walk 1 and the U213 threshold. The reserved garden it is verified to sit inside is
27 × 37 at V34–60 / U174–210.

### 1.4 NO ATTRACTION IN THIS PARK CAN BE TURNED, and that is a property of the grid

CLAUDE.md records the failure where a turn swaps width for depth and pushes a module into its
neighbour. Measured here at every placement corner, against pure lawn:

| turned footprint fits its own lot | 2 of 21 (Carousel Court, Prize Point) |
|---|---|
| does not fit | **19 of 21** |

The cause is structural rather than a packing accident: **a column is deep in V and narrow in U by
design** — Frontier column A is 97 × 40, column C is 130 × 71, Prismworks column A is 97 × 36 — so
a 51 × 40 module turned to 40 × 51 needs 51 columns of a 40-column band. There is no orientation
freedom anywhere in this park, and none is needed: every module in the programme already declares
its front on the low-V face, which is the side the spine is on. **The facing is correct as declared
and must not be turned by any later pass.**

---

## 2. Access: can each attraction be reached and entered

### 2.1 The convention, confirmed by measurement

Every one of the 29 modules puts `public_entry`, `queue_entry`, `public_exit` and `ride_exit` on
its **V = 0 face facing west**, and `service_access` on its far corner facing east. In this frame
west is decreasing V — toward the spine — and east is toward the service band. That is exactly
right for this grid and it is uniform across the whole programme; nothing needs re-facing.

### 2.2 The table

Spur = the 3-wide apron that would carry the door across the verge to the street, and where it
would land. Measured against the shipped ground, with lamps and other modules checked.

| attraction | at V,U | faces | entry (V,U) | street it addresses | gap | spur, and where it lands | clear? |
|---|---|---|---|---|---|---|---|
| Trailhead Gate | 24, 0 | west | 24, 19 | **spine** | 5 lawn | V19–23 × U18–20 → **V18** | clear |
| Boomtown Spine | 24, 47 | west | 24, 70 | **spine** | 5 lawn | V19–23 × U69–71 → **V18** | **lamp mast at (20, 69)** |
| Mine Coaster | 24, 99 | west | 24, 134 | **spine** | 5 lawn | V19–23 × U133–135 → **V18** | clear |
| Arrival Court | 24, 215 | west | 24, 235 | **spine** | 5 lawn | V19–23 × U234–236 → **V18** | clear |
| Carousel Court | 24, 266 | west | 24, 301 | **spine** | 5 lawn | V19–23 × U300–302 → **V18** | **lamp mast at (20, 300)** |
| Skill Arcade | 24, 346 | west | 24, 362 | **spine** | 5 lawn | V19–23 × U361–363 → **V18** | clear |
| Wyrm's Crossing | 24, 389 | west | 24, 407 | **spine** | 5 lawn | V19–23 × U406–408 → **V18** | clear |
| Foundry Gate | 24, 430 | west | 24, 448 | **spine** | 5 lawn | V19–23 × U447–449 → **V18** | clear |
| Prism Array | 24, 471 | west | 24, 496 | **spine** | 5 lawn | V19–23 × U495–497 → **V18** | **lamp mast at (20, 496)** |
| Prism Ascent | 24, 527 | west | 24, 563 | **spine** | 5 lawn | V19–23 × U562–564 → **V18** | clear |
| Snack Window | 77, 215 | west | 77, 235 | midway walk 1 | 1 lawn | V76 × U234–236 → **V75** | clear |
| Prize Point | 80, 346 | west | 80, 362 | midway walk 2 | 1 lawn | V79 × U361–363 → **V78** | clear |
| Resonance Vault | 82, 471 | west | 82, 491 | prism walk | 1 lawn | V81 × U490–492 → **V80** | clear |
| Forge Deck | 130, 527 | west | 130, 560 | back promenade | 2 lawn | V128–129 × U559–561 → **V127** | clear |
| Works Yard | 157, 125 | west | 157, 143 | service lane | 0 | adjacent, none needed | clear |
| Service Gallery | 157, 550 | west | 157, 570 | service lane | 0 | adjacent, none needed | clear |
| Signal Heron | 34, 174 | west | 34, 196 | spine | 15 lawn | *(a sculpture; a viewing apron, not a door)* | clear |
| **Prospecting Porch** | 69, 0 | west | 69, 20 | **none** | — | — | **the back of TRAILHEAD GATE is in front of this door** |
| **Mining Square** | 78, 47 | west | 78, 70 | **none** | — | — | **no paving within 24 courses; BOOMTOWN SPINE is in front of it** |
| **Sky Lift** | 92, 266 | west | 92, 301 | **none** | — | — | **the back of CAROUSEL COURT is in front of this door** |
| **Assay and Prize Office** | 130, 47 | west | 130, 70 | back promenade | 2 lawn | V128–129 × U69–71 → V127 | **inside MINING SQUARE's declared footprint** |

### 2.3 The three findings that matter

**(i) NO SPUR EXISTS ANYWHERE, AND EVERY SPINE-FRONTING DOOR IS FIVE COURSES OF LAWN FROM THE
STREET.** The public floor lots begin at V24 and the spine's paving ends at V18; V19–23 is the
designed verge, and there is no paved connection from any street to any building front in the
whole park. It is walkable (moss is walkable) so this is not a blocker — but ten attraction doors
currently open onto grass, and "clear pathways" is Jack's own first instruction. The spurs are
tabulated above: **ten across the spine verge at 5 × 3 = 150 cells**, three across a walk verge
at 1 × 3, and two across the promenade verge at 2 × 3 — **165 cells in fifteen spurs**, total.

**(ii) THREE ENTRANCES OPEN INTO THE BACK OF THE BUILDING IN FRONT OF THEM.** Every column that
stacks two builds with no cross walk between them puts the rear module's declared front door
against the front module's rear wall:

| column | stack | slack | cross walk possible? |
|---|---|---|---|
| Frontier A, U0–39 | Trailhead Gate V24–68 + Prospecting Porch V69–119 | 97 − (45+51) = **1** | no — a 3-wide walk costs 2 courses off one build |
| Frontier B, U47–92 | Boomtown Spine V24–76 + Mining Square V78–133 | 97 − 109 = **−12** | **yes, and for free** — see below |
| Midway B, U266–336 | Carousel Court V24–91 + Sky Lift V92–153 | 130 − 130 = **0** | no — the column is spoken for to the block |

**Frontier B is the one that resolves cleanly by arithmetic:** with Mining Square re-specced to
**41 × 46**, the column reads Boomtown V24–76 (53) + **walk V77–79 (3)** + Mining Square V80–120
(41) = **exactly 97**, the Mining Square's front door then addresses a real street, and the Assay
office behind it stops being overrun. That is one number and one walk declaration.

For the other two, the zero-cost answer is to move the entry to a **flank facing an avenue**,
which the grid already supports:

| attraction | flank | avenue | gap | note |
|---|---|---|---|---|
| Prospecting Porch | east, U39 | frontier avenue U41–45 | 2 lawn cells | avoid V95 — a lamp stands at (95, 40) |
| Sky Lift | east, U336 | midway avenue U338–344 | 2 lawn cells | avoid V95 and V139 — lamps at (95, 337) and (139, 337) |

**(iii) THE THREE CROSS WALKS ARE COMPLETELY UNLIT, and they are the only street three attractions
have.** Measured: zero lamp masts within two cells of midway walk 1 (V73–75, U215–257), midway
walk 2 (V76–78, U344–384) or the prism walk (V78–80, U469–523). Those three walks are the entire
street access for the Snack Window, Prize Point and the Resonance Vault. All three walks *do*
reach paving at both ends — verified cell by cell — so they are connected; they are simply dark.

---

## 3. The pathway audit

### 3.1 Connectivity, and there are no stubs

    18,163 walkable paved cells in ONE 4-connected component

(the rim edge course at V170 excluded — it is a dressed edge, not a route; lamp footings excluded,
because a footing is not a street).

**Every path termination in the park, and none of them is a stub.** A termination is a face at
least 3 wide whose corridor behind it is deeper than the face is wide — without that test the long
*side* of every street reports as an end, which is 335 findings and no signal.

| terminations found | 18 |
|---|---|
| **stubs ending in open lawn** | **0** |
| plaza rims at the park's front edge (V1, six avenue heads) | 6 |
| the Midway Circus island's own edge | 12 |

The six at V1 are the round plazas' northern rims, one course short of the envelope edge, against
the V0–5 arrival apron. The twelve at the circus are the ring road meeting its reserved green
island. Both are intentional and neither reads as a path that stops.

The three **promenade gaps** deserve their own line, because they are the most likely thing to
look like a dead end and are not: the promenade stops at U97, U263 and U469 and resumes at U170,
U338 and U523 — and **every one of those six ends lands on an avenue** (U95–97, U257–263, U338–344,
U467–469, U523–525) or a threshold (U170–172). You turn onto a cross street; you never walk into
grass. Measured, not asserted.

### 3.2 Symmetry: the geometry is perfect, the pattern is not

`geom` counts cells that are paved on one side of an axis and lawn on the other; `material` counts
cells that are paved on both sides but with a different block.

| axis | pairs | geom mismatch | material mismatch |
|---|---|---|---|
| spine V6–18 about V12 | 3,600 | **0** | 346 |
| back promenade V123–127 about V125 | 1,200 | **0** | 87 |
| service lane V154–156 about V155 | 600 | **0** | 39 |
| all six avenues about their own axis | 1,595 | **0** | 3–5 each |
| all six plazas, mirrored in U | 253 each | **0** | **30–34 each** |
| all six plazas, mirrored in V | 253 each | **0** | **30 each** |
| the Midway Circus, both axes | 351 each | **0** | **20 each** |

**Every street and every plaza is geometrically symmetric about its own axis — zero mismatches
anywhere.** The shape of the paving is right.

**What is not symmetric is the PATTERN inside the plazas and the circus, and it has one cause.**
`parkways.plaza_key` picks the inlay with `(dx + dz) % 6 == 0`, and the roundabout with
`(dx + dz) % 5 == 0`. That expression is invariant under `(dx, dz) → (-dx, -dz)` but **not** under
`dx → -dx`, so the pattern is a diagonal stripe with 180° rotational symmetry rather than a
mirror-symmetric rosette. On a round plaza the eye reads the rim as a circle and the inlay as
crooked. **30–34 of 253 mirrored cells differ in each plaza, and 20 of 351 in the circus** — and
that number is stable across every build of the ground so far.

The fix is one character each: `(dx + dz) % 6` → `(abs(dx) + abs(dz)) % 6`, and `% 5` likewise.
That is mirror-symmetric in both axes by construction and changes nothing else about the pattern's
density.

### 3.3 Five of the six promenade crossings are T-junctions, and that is by design

| avenue | promenade west | promenade east | |
|---|---|---|---|
| frontier U43 | yes | yes | crossroads |
| frontier U96 | yes | **no** | T-junction |
| midway U260 | yes | **no** | T-junction |
| midway U341 | **no** | yes | T-junction |
| prismworks U468 | yes | **no** | T-junction |
| prismworks U524 | **no** | yes | T-junction |

This is the promenade gap over the three deep ride columns, working as documented. It is not a
fault — but it *is* what a walker sees, and it is why a junction-lighting rule that assumes four
approaches has to be told that one of them is not there.

### 3.4 The lamps around intersections — measured, and the rule

**The state as measured** (md5 `addbdc1…`, which matches commit `53f0e2a` *"a crossing is lit by
the crossing"* — landed by the stream that owns this file **while this audit was running**):

    121 masts on 10 V lines: V4 (28) V20 (28) V29/51/73/95/139 (6 each) V117 (3) V121 (16) V129 (16)

| junction family | state |
|---|---|
| spine × avenue, all 6 | **complete** — four masts, setback 9, paired on both V4 *and* V20, and V4 and V20 now carry **identical U lists** (the two verge rows are opposed, not staggered by 11 as they were) |
| promenade × avenue, U43 (the one true crossroads) | **complete** — four masts, setback 4 |
| promenade × avenue, the other 5 | **two masts, and that is correct** — see below |
| **promenade × threshold, all 4** | **U171 has no lamp at all within 16 blocks; U213/U386/U428 carry one or two at −14/+9, −13 and +8 — not one matched pair** |
| **spine × threshold, all 4** | one mast each at −3, −4/+16, −14/+8, −13/+9 — **not one matched pair** |
| **the Midway Circus** | two masts, both on the **west** side at −13; the east half of the ring road is dark |

**THE FIVE TWO-MAST PROMENADE JUNCTIONS ARE RIGHT, AND THE OBVIOUS "FIX" WOULD BE A REGRESSION.**
This audit's first draft called them incomplete; measured properly they are not. The back promenade
is gapped over the three deep ride columns, and the avenues *are* those columns' seams — so at
five of its six meetings the promenade has street on one side only. **A corner on the far side
would stand past the end of the street, on ground that belongs to the ride**: at U96 that corner
is (121, 100) and (129, 100), and U100 is inside the Mine Coaster's own 71-wide column, where a
single lamp cell stops the depth probe at V121 and reads the 111-deep coaster as 14 courses short
of its lot. *(This audit measured exactly that on the 13:11 build, before the fix landed.)*

So the invariant is narrower than "four corners" and it is the one you can actually see:

> **A crossing is symmetric ACROSS the street it crosses.** Along the street there may be nothing
> on the far side to match. What must hold at every junction is that its two verge lines carry the
> *same* answer — V121 and V129 identical, V4 and V20 identical — which is what a walker standing
> in the crossing and looking left and right compares.

Measured on the shipped build, that invariant holds at all twelve avenue junctions and at none of
the five remaining ones.

**WHY IT LOOKS WEIRD, IN ONE SENTENCE:** a rhythm walked down a verge line — `(z + phase) % every
== 0` — has no idea a crossing is there, so a junction gets nought, one, two or four masts at
whatever offset the counter happened to be carrying, and one phase serves 600 blocks and sixteen
crossings at once. No amount of phase tuning fixes that, because the offsets it produces at
different junctions are unrelated by construction.

#### THE RULE

> **A junction is lit by its own four corners, or not at all.** Place one mast per quadrant at the
> point where the two streets' **own verge lines** cross, pushed outward along the crossed street
> by **one setback shared by all four**. The setback is **probed** outward from the street's own
> verge offset (`half + 2`) until all four cells are clear of paving and of any reserved lot —
> probed rather than computed, because the thing it has to clear is a round plaza and "where does
> a disc of radius r stop covering the line at depth d" is arithmetic that stays correct only
> until somebody changes the plaza's shape.
>
> Four supporting clauses, each of which is a fault that has already shipped:
>
> 1. **A corner only goes where the crossing street actually reaches.** At a T the far corner
>    would stand past the end of the street, in the lot behind it — and on this park the verges
>    are the whole margin, so one lamp cell moved a 111-block ride out of its own lot.
> 2. **Symmetry is required ACROSS the street, not along it.** Both verge lines of a junction must
>    carry the same answer; whether that answer is a pair or a single is decided by clause 1.
> 3. **The junction masts are placed FIRST and the runs are spaced between them**, not the other
>    way round. A run filled on a phase and then trimmed leaves the first post 18 blocks one way
>    and 26 the other at every crossing.
> 4. **The junction masts are exempt from the 8-block anti-bunching guard** — their own members are
>    2 × setback apart (8 to 26), and the guard exists to stop a *rhythm* lamp being shoved off
>    its line, not to stop a designed pair.

#### EVERY COORDINATE THE RULE PRODUCES

`*` = a mast already stands there in the measured build.

**spine × avenue — setback 9 on both V4 and V20** (all 24 already correct):

| U43 | (4,34)* (4,52)* (20,34)* (20,52)* |
|---|---|
| U96 | (4,87)* (4,105)* (20,87)* (20,105)* |
| U260 | (4,251)* (4,269)* (20,251)* (20,269)* |
| U341 | (4,332)* (4,350)* (20,332)* (20,350)* |
| U468 | (4,459)* (4,477)* (20,459)* (20,477)* |
| U524 | (4,515)* (4,533)* (20,515)* (20,533)* |

**promenade × avenue — setback 4 on both V121 and V129, corners only where the promenade reaches**
(all correct as shipped; nothing to add):

| U43 (crossroads) | (121,39)* (121,47)* (129,39)* (129,47)* |
|---|---|
| U96 (T) | (121,92)* (129,92)* — U100 is inside the Mine Coaster's column |
| U260 (T) | (121,256)* (129,256)* — U264 is past the promenade's end |
| U341 (T) | (121,345)* (129,345)* |
| U468 (T) | (121,464)* (129,464)* |
| U524 (T) | (121,528)* (129,528)* |

**promenade × threshold — setback 4** (all 14 missing; every cell verified free of paving. U171's
west corner is inside the U98–169 promenade gap, so that one is a T and takes two):

| U171 | (121,175) (129,175) |
|---|---|
| U213 | (121,209) (121,217) (129,209) (129,217) |
| U386 | (121,382) (121,390) (129,382) (129,390) |
| U428 | (121,424) (121,432) (129,424) (129,432) |

**spine × threshold — a PAIR on V20 only, setback 8.** A threshold runs V12–156: it leaves the
spine at its own centre line, so there is no northern quadrant to light and the symmetric answer
is two masts, not four. (7 of 8 missing.)

| U171 | (20,163) (20,179) |
|---|---|
| U213 | (20,205) (20,221) |
| U386 | (20,378) (20,394)* |
| U428 | (20,420) (20,436) |

**the Midway Circus — setback 13, the first cell clear of the r13 ring** (2 of 4 missing):

| circus | (121,222)* **(121,248)** (129,222)* **(129,248)** |
|---|---|

**Total: 23 masts to add, 0 to move, 0 refused** — 14 at the four threshold × promenade crossings,
7 at the four threshold × spine crossings, 2 on the circus's east side. Every one was measured
against the shipped ground and is open lawn, outside every reserved feature lot and outside the
circus island.

**The cause of the gap is one line, and it is worth naming:** the junction pass walks the `avenues`
list, and a *threshold* is not in that list — so the four handoffs at U171/213/386/428, which are
real 3-wide streets running V12–156 and crossing both the spine's south verge and the promenade,
have never been offered a junction at all. The Circus is missed for the same reason.

#### One more asymmetry, on the runs rather than the junctions

An avenue's own posts alternate sides down its length — east at V29, west at V51, east at V73,
west at V95, east at V117, west at V139 — which is a real street idiom. But V117 is four blocks
from the V121 junction quartet and is being dropped by the anti-bunching guard, and when it goes
**V95 and V139 are both on the west side**: two consecutive posts 44 apart on the same flank, with
nothing at all on the east side of the avenue's back half.

Measured on the current build this fires on **three of six avenues** (frontier U43, midway U341,
prismworks U524) and not on the other three — which is worse than either, because the six avenues
no longer light the same way as each other. The fix is the rule's own clause 3: **space the avenue
run between its junction anchors** exactly as the spine and promenade runs now are, instead of
dropping a station and leaving the alternation broken.

---

## 4. What to change, in priority order

### (a) For me to implement — measured, unambiguous, no design decision in them

1. **The 23 junction masts in §3.4.** The junction pass is correct and already lights all twelve
   avenue crossings; what it never sees are the **four threshold handoffs** (U171, U213, U386,
   U428) and the **Midway Circus**, because it walks the `avenues` list and neither is in it. Feed
   the thresholds in as crossings of both the promenade (setback 4, four corners, T-clause applied
   at U171) and the spine's south verge (a **pair** on V20 at setback 8 — a threshold leaves the
   spine at its own centre line, so there is no northern quadrant), and the Circus as a crossing at
   setback 13. **Do NOT "complete" the five two-mast promenade junctions — that is a regression**,
   and §3.4 says why. *`mcbuild/gen/parkways.py` — another stream owns it; this is written as a
   recommendation, and the coordinate table above is the whole specification.*
2. **Space the avenue runs between their junction anchors**, so V95/V139 stop landing on the same
   flank and all six avenues light identically. Same file, same owner.
3. **Make the plaza and roundabout inlay mirror-symmetric**: `(dx + dz) % 6` → `(abs(dx) +
   abs(dz)) % 6` in `plaza_key`, and `% 5` likewise in the roundabout. Removes 30–34 mismatched
   cells per plaza and 20 in the circus; changes nothing else. Same file, same owner.
4. **Draw the entry spurs.** 3-wide aprons at the fifteen coordinates in §2.2 — ten across the
   spine verge (V19–23, landing on V18), three across a walk verge, two across the promenade
   verge. That is 165 cells and it is the difference between "buildings on lawn" and "clear
   pathways". Same file, same owner.
5. **Light the three cross walks.** Zero masts on them today, and they are the only street the
   Snack Window, Prize Point and Resonance Vault have.
6. **Move three masts out of three doorways**: (20, 69) at Boomtown Spine's entry, (20, 300) at
   Carousel Court's, (20, 496) at Prism Array's. A mast may move along its own line, never across
   it — the existing rule already says so; these three simply need the entry U values fed to the
   run as anchors the way a junction is.

### (b) Jack's call — each is a programme decision, stated with its arithmetic, not silently edited

7. **Mining Square: re-spec to 41 × 46 and give Frontier column B a 3-wide cross walk at V77–79.**
   53 + 3 + 41 = exactly the column's 97. It fixes three things at once — the 13-course shortfall,
   the 184-cell collision with the Assay and Prize Office, and Mining Square's own door having no
   street. *Alternative:* leave the footprint and move Assay and Prize into the Mine Coaster's exit
   band, which needs its own block found.
8. **Works Yard and Service Gallery: re-spec both to 13 deep** (13 × 36 and 13 × 41). At the
   declared 18 they cross the rim edge and put four courses inside the protected rim reserve, which
   is a rule break rather than a squeeze. *Alternative:* delete the continuous service lane and
   reach each shed by a spur off the avenue tails, which already run to V156 — that gives the full
   18 and costs the back-of-house road.
9. **Signal Heron: re-spec to 27 × 37** to match the garden already reserved for it. At 52 × 45 it
   overlaps the Arrival Court by 152 cells and the Snack Window by 36, and the bird itself is
   14 × 32.
10. **Prospecting Porch and Sky Lift: re-anchor the public entry to the east flank** (U39 and U336
    respectively, both two cells from an avenue), or buy a cross walk by shortening a build. The
    flank move costs no ground; the walk costs 2–3 courses off Frontier column A or Midway column
    B, neither of which has them. **These two doors currently open into a wall.**
11. **The Sky Lift is signposted "THE BIG WHEEL" on four of the park's own wayfinding markers.**
    Decide which name is the real one before any sign is built.

---

## 5. What I could not determine

- **Nothing here has been looked at in game, and nothing here judges colour.** Every claim is a
  block count. The read of the paving patterns, the palette and whether five courses of moss
  between a door and the street *feels* like a front garden or a mistake can only be settled in
  world.
- **The lamp state is a snapshot of a layer that was rewritten as this was measured.** Sections 1,
  2 and 3.1–3.3 are structural and stable across all four builds observed; §3.4's counts are pinned
  to md5 `addbdc1dc030702d446b80aacb468d50` (commit `53f0e2a`) and will move again. The rule and
  its coordinates are derived from the street schedule and are not affected.
- **`tests/test_parkways.py`: 23 passed, 0 failed** — run last, after `53f0e2a` landed. Mid-audit,
  while that commit's generator was in flight, the suite showed 22 passed / 1 failed
  (`test_every_crossing_in_the_shipped_park_actually_gets_its_four`, *"only 7 of 12 crossings
  lit"*); that was confirmed to be the other stream's own test against its own half-written
  generator by removing `tools/park_attractions.py` and reproducing it exactly. **0 introduced by
  this work.**
- **The four modules the brief named that are not in this programme** (Big Wheel, Haunted Manor,
  Ghost Train, The Plummet) were searched for by name across `park_final.world.json`; whether they
  are meant to return to the 600 × 200 park is not something a measurement can answer.
