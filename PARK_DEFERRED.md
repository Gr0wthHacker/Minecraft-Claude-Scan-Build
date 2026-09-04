# Deferred to the orientation pass — after everything is placed

Jack: "also the orientation is off, label that as something to fix when everything is placed so
we make it face a more reasonable direction to the users."

**THIS IS A LIST, NOT A NOTE.** Every item here was found while the park was still being built and
is deliberately NOT fixed yet, because a facing is only judgeable against the finished thing.
Turning a module changes what stands in front of it, which spur reaches it, and which lamp is
beside its door — and this project has already recorded the specific trap: **a turn swaps width
for depth**, so a module that fits its lot at one facing can overflow it at the next, and a turn
moves EVERY anchor rather than just the front. Do them in one pass, together, at the end.

## The rule to apply

A module must address the street a visitor arrives from. The measured convention in this park is
that every lot fronts WEST onto the spine (V6-18) or onto its own cross walk, because the columns
are deep in V and narrow in U by design — `PARK_ATTRACTIONS_PLAN.md` §1.4 measured that **19 of 21
modules fail at 90 degrees**, so most of these are not free turns and each needs its lot re-checked.

## Open items

| module | what is wrong | what it needs |
|---|---|---|
| ~~Wyrm's Crossing~~ | ~~the skull faces the wrong way~~ | **DONE** — `rotate: 180` on the asset, so the face meets the Midway approach. Only 0 and 180 fit: at 90 the module is 54 across against a 45-column reach. `tests/test_asset_rotate.py` pins it. |
| *(nothing else yet)* | | |

## How to run the pass

1. Place everything. Nothing here is judgeable before that.
2. For each item, stand at the arrival point and look — `python tools/look.py "<design>" --bearing 0`
   reads the RECORDED facing, and a design with none says so rather than defaulting quietly.
3. Turn, then RE-VERIFY the lot: `python tools/park_place.py` crops anything outside a lot and
   reports the crop, so a turn that overflows shows up as cells lost rather than as a silent
   truncation.
4. Re-check the spur: `configs/park_ways.yaml`'s `spurs` list carries one door per module, and a
   turned module's door is somewhere else.
