> **SUPERSEDED 2026-09-03 by `PARK_MIDWAY_CENTRE.md`.** Jack: *"move the wheel back and
> lets fill the area between with something more interesting."* The proposal in §3 below
> (an exit court and a parterre behind a wheel that does not move) is **not** the plan.
> §1 and §2 — the measurements and the four findings, including the promenade gap and the
> retirement list — still hold and are what the new plan is built on.

# The ground behind the Sky Lift — audit and plan

Jack: *"lets plan putting something behind the ferris wheel, theres a lot of space, we it can be a
mix of functional and visual e.g. continued court yard/pathway, or something else."*

Everything below is measured off `out/Park Complete.litematic` and `configs/park_ways.yaml` as they
stand on 2026-09-03, after the Carousel moved out of column B into the Arrival Court's lot.

---

## 1. What is actually there

**V102–153 × U266–336 — 52 deep by 71 wide, 3,692 columns.** The largest unbuilt ground in the
park, and it is empty to the block:

| | |
|---|---|
| paved cells | **0 of 3,692** |
| light sources | **2 lanterns** |
| anything above the lawn | 181 `moss_carpet` at Y203, one lamp mast reaching Y208 |
| bounded by | Sky Lift V80–101 (front) · street U257–263 (west) · street U338–344 (east) · service lane V154–156 (back) |

It is walkable — 82 steps from the Welcome Court's fountain — but **only by crossing open grass**.
`PF Vantage Midway Belvedere`'s own config already rejected this ground for exactly that, and the
sentence is the brief for this plan:

> *"That is the whole reason for this lot rather than the much larger free ground behind the Sky
> Lift: a vantage a visitor has to cross a lawn to find is a vantage nobody finds."*

## 2. Four things the audit found, in order of how much they decide

### 2.1 The back promenade is severed for 74 columns, and the reason is dead

`configs/park_ways.yaml` carries `promenade_gaps: [[98, 169], [264, 337], [470, 522]]`, with its
own stated reason:

> *"Three columns carry a single build deeper than any promenade can clear — the Mine Coaster (111),
> the Carousel over the Sky Lift (130) and the Prism Array over the Resonance Vault (109)."*

**That schedule no longer exists.** The Sky Lift is 19 deep (22 declared) and the Carousel is in
column A. The gap is a stale reservation against a stack that was never built.

Measured cost of the severance, walking the paved network:

| | steps |
|---|---|
| promenade west end (V125, U263) → east end (V125, U338), **around** | **117** |
| the same, straight through the gap | **~75** |

Measured cost of closing it: the band V121–129 × U264–337 is **666 columns carrying 33 cells of
moss carpet and nothing else.** It is free ground. The Sky Lift's pad ends at V98, twenty-five
courses in front of the promenade line — no clash.

This is the enabling move. Without it the two lots have no frontage and the answer is another
thing you cross a lawn to find.

### 2.2 The wheel discharges onto its own approach, and its rear is already open

`Sky Lift`'s `ride_exit` anchor is on the **west** face — the arrival front. `PARK_MIDWAY.md` is
explicit: *"The exit cannot feed into waiting guests."*

And `chute_exit` is a **required** Sky Lift interface (`PARK_VERTICAL_MASTERPLAN.md`: *"lift/gallery/
chute experience, dry landing, photo/viewpoint, wide exit to food"*) that does not exist. The ride
itself is real and built — soul sand at world V87/U300 under 48 courses of bubble column, with
3-deep landing channels at U299/U301 running V84–97. **The lift is built; the landing and the exit
are not.**

The useful fact: the Sky Lift's rear face (module V17–18 = world V97–98) carries **no fence and no
wall** — its west edge does, its east edge does not. A rear exit needs **no change to the Sky Lift
artifact**, which is a `KEEP` module and should not be rebuilt.

### 2.3 The band programme already says what goes here

`park_ways.yaml`'s depth programme splits this ground for us:

```
V 102-120   public floor lot          19 deep x 71
V 121       promenade verge
V 123-127   BACK PROMENADE            5 wide      <- currently absent
V 128-129   promenade verge
V 130-153   exit / observation lot    24 deep x 71
V 154-156   service lane
```

Column B is **the only Midway column whose exit/observation band is empty.** The Frontier's holds
the Lookout, Prismworks' the Forge Deck, column A's the Belvedere.

### 2.4 The obvious answers are all retired, and that is the most useful finding here

| proposal | ruling | source |
|---|---|---|
| Food Court, Terrace | *"low gameplay density, expensive footprint — **RETIRE**. One Midway Snack Window only"* | `PARK_600X200_AUDIT.md` |
| Fireworks Terrace | *"**Remove.** A passive event deck is not a reliable gameplay loop."* | `PARK_FUN_AUDIT.md` |
| a fourth game | the Midway's fun core is *"Carousel, Sky Lift, **3-4 distinct games**"* — it has three plus a prize counter | `PARK_FUN_AUDIT.md` |
| a second viewpoint tower | duplicate verb: the Belvedere is 41 courses up, **38 blocks west** at V139/U228 | the same reasoning that retired Mine Cart Escape |
| a creature set piece | *"visual assets not offerings — RETIRE from connector stops"* | `PARK_600X200_AUDIT.md` |

So this ground may not become an attraction, a food hall, a terrace, a game or a tower. What it
**may** become is stated just as plainly:

> *"Paths, bridges, benches, lamps, gardens — support rather than offerings — **KEEP only when they
> carry circulation, safety, rest, wayfinding, or an edge/view job**."*
>
> *"Standalone galleries/outlooks — **retain only as payoff on an existing exit/return route**."*

---

## 3. The plan

**Governing idea: this is not a new place. It is the Sky Lift's missing second half.** Every piece
below has a job off that permitted list, and nothing here is called an attraction.

### A. Close the promenade gap  *(ground layer)*

Drop `[264, 337]` from `promenade_gaps`. 5-wide walk at V123–127 × U264–337 with its standard
verges and lamp line, joining the Circus and the balloon (U235) to the Skill Arcade and Prize Point
(U346+). Update the stale justification comment in `park_ways.yaml` at the same time.

**This is the expensive move**: it regenerates `Park Ways`, which re-ships `Park Complete`, which
every park design verifies against. Roughly 370 paved cells. Jack's call before anything else.

### B. `Wheel Return` — V102–120 × U266–336, 19 × 71  *(public floor)*

The chute landing and exit court. Class: **circulation + rest, on an exit route.**

| piece | job |
|---|---|
| landing apron, V102–108 × U296–304 | paved, continuous with the Sky Lift's own pad so there is no lawn seam under the step-off |
| `RIDE EXIT` portal at V102/U300 | the park's own exit idiom — no accent colour, plain slab head, one word, so it reads as an exit from twenty blocks without being read |
| two bench exedras flanking it | the Welcome Court's own curved-bench idiom, set **off** the desire line per the spec's *"seating/planting outside desire lines"* |
| fingerpost at V113/U300 | the real decision point: **west** Circus · **east** games and prizes · **north** back to the queue. This is the Orientation class and the junction the wayfinding gate wants |
| the rest | lawn with kerbed beds. Target **~25–30% built**, no more |

### C. `Wheel Garden` — V130–153 × U266–336, 24 × 71  *(exit/observation band)*

Class: **edge/view.** Not a terrace, not a tower — **a low parterre designed to be read from above.**

The Sky Lift crowns at **Y276, 74 courses over the lawn**. Its riders look straight down on this
ground, and that is the one view it gets that nothing else in the park has. So the composition is
made for the **plan** — the view voxels give away free — concentric or radial on U300, echoing the
wheel it stands behind: kerbed beds, hedged compartments, 3-wide walks crossing to the service lane,
benches on the walks, nothing over about four courses.

It earns its place three ways off the permitted list: **rest** (benches), **circulation** (the walks
that carry you from the promenade to the back of the land), and an **edge job** — it is the last
public ground before the V154 service lane, so it marks that boundary instead of a fence doing it.

### D. Light it

Two lanterns in 3,692 columns. `Island Night`'s idiom — lantern on worked stone, flush ochre
froglight in turf where a post cannot stand — solved with `tools/park_night.py` to **zero spawnable
cells on the walking surface**, which is the standard the rest of the park already meets.

### Rough bill

| | blocks |
|---|---|
| promenade closure | ~370 |
| Wheel Return | ~2,500 |
| Wheel Garden | ~3,500 |
| lighting | ~120 |
| | **~6,500 over 3,692 columns** |

All of it cheap tier: stone brick, deepslate brick, moss, oak, wool trim, lanterns, froglight.

---

## 4. What this deliberately does not do

- **No terrace, no food court** — retired twice, by two later audits than the spec that asked for them.
- **No fourth game** — the Midway's fun core is complete.
- **No second observation tower** — the Belvedere is 38 blocks west and 41 courses up.
- **No creature or set piece.**
- **No filling the lot.** Roughly two thirds of the ground stays open. The wheel is the object here;
  a second silhouette behind it would be competing with the thing the whole column is composed about.

## 5. Decisions this needs from Jack

1. **Close the promenade gap?** It is the enabling move and it re-ships the whole park.
2. **Move the wheel's exit to the rear?** It is the strongest functional justification for building
   here at all, and it costs only the frontage design's portals — the Sky Lift artifact is untouched.
3. **How much mass?** The plan above is deliberately light. A denser court is possible and would
   need an argument against the two audits that retired the last two attempts at one.
