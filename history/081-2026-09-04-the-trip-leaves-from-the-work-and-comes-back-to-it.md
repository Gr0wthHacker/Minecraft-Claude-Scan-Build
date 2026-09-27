## The trip leaves from the work and comes back to it (2026-09-04)

Jack: *"autofly etc basically infinitely wanders fetching small amounts of shit, finding
somewhere to put it, often failing to put it, coming back, repeating infinitely, its highly
inefficient, chaotic, and doesnt check inventory, area, or fill inventory based on needs at
all."* Every clause of that is one defect, and they were all the same defect: **the loop had no
idea where the work was once it left it.**

    the working area      focus(eligible, ME, radius)        me = the chest, mid-fetch
    the shopping list     nearDemand(eligible, frontier, ME) re-sized every recount, at the chest
    the trip's end        canWork, measured where I stand    "nothing placeable" at a store hall
    out of view           todo empty -> LOOK                 mid-trip, then back to the trip
    the pack              loadCapacity = empty slots         never emptied of anything

So a fetch flew to the store hall, re-planned the load for the cells nearest the STORE HALL,
came back to those cells rather than to the spot it had left, found nothing placeable, read
that as a dead end or a reason to shop again, and did it all with a pack that a previous design's
leftovers had shrunk to a stack or two of room. Nothing in `LoopTest` could see it, because the
phase function is right for every combination of its inputs and the inputs were being measured
in the wrong place.

- **`Hud.workAnchor`.** Set to the nearest work on the first recount, moved to the spot being
  built as it drifts, moved deliberately when an area is finished (to the nearest remaining cell
  to the AREA, so the work walks across the design) or when the loop goes to look at unseen
  cells - and never by a fetch. The working area is `focus(eligible, anchor, radius)`. When the
  anchor's chunk is not loaded and the loop is not mid-trip, it goes BACK there and decides
  nothing until it arrives.
- **`Plan.loadPlan`: the shopping list is made ONCE, at the work, and held for the trip.** In
  BUILD ORDER: the frontier first, then the area's cells lowest course first and nearest the
  anchor within a course, up to what the pack can hold. Sorted by 3D distance instead, the pack
  filled with roof for a wall whose ground course still wanted stone. `Plan.shortfalls` is the
  list minus what is carried, with addresses; the amount taken is the list's, not four stacks.
- **`Loop.phase`: a trip with somewhere still to go is not interrupted by the work going out of
  view.** `todo == 0` with cells unseen used to mean LOOK, mid-trip too: the chunks under the
  anchor unloaded on the way to the chest, the loop turned round to look at them, then turned
  round again to finish the trip. That is the ping-pong.
- **`Work.dumpable`: the pack is CHECKED, and what it holds for no reason is put away.** A stack
  that places a block, holds nothing itself, and is wanted by no cell of the WHOLE design goes
  into the chest the trip is at before anything comes out of it (`Withdraw` deposits by the same
  shift-click and reconciles it the same way, one stack a pass). Never a tool, food, a bucket or
  a shulker box; never a material for the far end. Those slots count as room when the list is
  sized, so a pack full of the last design reads as a full trip rather than as PACK_FULL. A full
  chest stops the putting-away and says so; nothing is ever dropped.
- **The trip ends where it ends, and then goes home.** When the phase leaves FETCH with the
  anchor out of view, the loop flies back to the anchor rather than deciding anything about the
  chest's surroundings.

`/cscan why` now says the anchor (and whether it is loaded), the shopping list of the trip in
progress, and what is in the pack for no reason. `PackTest` (5) pins the dumping rule,
`AuditFixesTest` the build-order list and the shortfalls, `LoopTest` the uninterrupted trip.
**652 Java tests, 0 failures.** `chunkscan-0.8.1.jar` is built and not uploaded.

**Not flown in game**, and two things to watch when it is: the deposit is a shift-click INTO a
chest through the same reconciliation as taking, which has been exercised offline only; and
"often failing to put it" is the printer's refusal path, which this pass does not touch beyond
sending the loop back to the spot it left - if refusals persist AT the anchor, that is the next
audit and it is a different subsystem.

