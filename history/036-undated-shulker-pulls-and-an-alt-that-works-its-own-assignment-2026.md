## Shulker pulls, and an alt that works its own assignment (2026-08-30, chunkscan 0.7.0)

### "A client mod cannot unpack a box for you" was the same kind of claim as the last one

This file has said for a long time that a boxed block *"is not placeable until you set the box
down"* and that *"a client mod cannot unpack one for you"*. The first half is true; the second was
a POLICY WRITTEN AS A FACT, exactly like *"a client mod cannot place a block"* before it. Placing,
opening, emptying and breaking a box are four things this mod already did separately.

It matters because **bulk storage on this island IS boxes in chests**. The index already read
their contents into `inBoxes`, `Plan.notInAPack` already subtracted them from a shortfall so you
were not sent shopping for something you owned - and then the loop stopped and told you to do the
last step by hand. It does it itself now, inside the fetch phase.

**Placed shulker boxes needed NO new code and that is worth recording.** `Storage.CONTAINERS`
matches by substring, so a shulker box standing in the world has always been indexed, findable and
withdrawable exactly like a chest. `UnboxTest` asserts it so nobody "adds" it later and breaks the
substring match.

**A SHULKER BOX IS THE MOST DANGEROUS BLOCK IN THE GAME TO AUTOMATE.** Everything else here risks
one block; this risks a whole inventory, and the failure is silent - a box left on the ground looks
exactly like one that was picked up. So the rules are refusals rather than warnings:

- **Never over the void.** A dropped block is a block; a dropped shulker is everything in it.
- **Only ever break a box THIS ROUTINE PLACED, at the exact cell it placed it.** The island is full
  of boxes that are somebody's storage, and "a shulker box nearby" is not a thing it may touch.
- **The box must come back**, checked against the pack afterwards. An unrecovered box is not a
  failed step, it is a lost chest, so it stops everything and says where the box is.

### `/cscan fleet work` - an alt that picks up its own assignment

`follow all` walks every tracked design, which is right for one player and wrong for a fleet: five
alts all starting at the top of the same list is five printers fighting over one design. `fleet
work` walks only what this account holds, keeps the lease alive while it builds, and hands a design
back the moment its placements are done.

### Three defects found auditing this session's own work

- **The Crafter's race, again, in `Unbox`.** `st.getCount()` is what the server is being ASKED to
  move; a full pack moves less. Counted from the pack on a later tick now. The same bug twice in
  one day is the argument for the rule rather than the fix.
- **FIVE CLIENTS SHARE `fleet.json` AND IT WAS WRITTEN IN PLACE.** A plain write leaves a window
  where the file on disk is truncated, and a client reading in that window sees an EMPTY fleet -
  then claims a design another account is already building, which is the one thing the file exists
  to prevent. Atomic temp-then-move on both sides now. **The remaining read-modify-write race is
  documented rather than implied away**: two clients that both read and both write still lose one
  change, and what carries it is that claims are near-idempotent and heartbeats repeat. A real lock
  is the fix the day this assigns something that cannot be repeated.
- **A tautological test** (`assertTrue(x || true)`) was removed. A test that cannot fail is worse
  than no test, because it is counted.

### Still open

- **None of the unbox routine has run in game.** It is the one automation whose failure costs an
  inventory rather than a block, so run it once by hand - `/cscan unbox <item> <n>` - on a box you
  would not mind losing, before the loop is left to call it unattended.

