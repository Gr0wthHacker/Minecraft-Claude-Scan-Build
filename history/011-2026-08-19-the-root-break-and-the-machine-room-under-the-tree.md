## The root break, and the machine room under the tree (2026-08-19)

`configs/root_break.yaml`. **82 blocks.** It closes the one-course gap between the taproot's head
at Y188 and the island's belly skin at Y190, and stops there.

**It started much bigger and had to be cut back, which is the useful part.** The story is right —
the plate hands you to an interior which hands you down the taproot, and the taproot *topped out at
Y188, six courses below the deck floor*, so the room whose whole purpose is that handover never
showed the root. The first build carried it all the way up through the undercroft, the deck floor,
the room and the ceiling to the tree at Y203.

**The site could not take it. The tree's base is a MACHINE ROOM.** 66 redstone parts spanning
X-24209..-24195 / Y191–203 / Z30005..30030 — 13 pistons, 7 repeaters, 6 observers, 2 dispensers,
and a **sculk sensor at (-24199, 201, 30019) shielded by 68 wool cells within 3 blocks**. Wool is
the only block that stops a vibration; that wool is the shield on a hidden-door trigger, not
decoration. The tree trunk's own centroid (-24199, 30019) sits *inside* that spread, and **no
4-radius column anywhere clears the mechanism by 5**. The first build put 256 cells within 8 of the
sensor and came within 1 of it, and heaved 57 cells of the shielding on the way.

Closing the gap at Y189–190 gets the thing that actually mattered — the root reads continuous into
the island's underside — from the view where it counts, which is **from below, descending the root
stair**. Nearest mechanism part is now **5 blocks**, cells near the sensor **0**.

### What this cost, and what it is worth keeping

- **`gen/protect.py`.** `BREAKABLE` was a whitelist and it was still wrong, because `gray_wool` and
  `black_wool` looked like ceiling decoration. The safe set is now stated ONCE and every generator
  consults it *in addition to* its own whitelist — redstone, containers, machines, rails, doors,
  signs, fluids, farm blocks, player-placed light. A block that looks like fabric may be a
  silencer; a stray slab may be a timing floor; a generator cannot tell by looking.
- **`protect.is_used` and rule 10.** 44 structural cells sat within one block of something you
  stand at and use. Honoured *above the floor course only* — paving the floor beside a chest is
  still floor. 44 → 20, all of which are paving.
- **`finish.defer_to`.** The four deck designs shared 39 cells. Overlap between designs is a WORK
  problem: you place a block, the next placement says it is wrong, you break it and place it again.
  Precedence runs Root Break > Taproot Entrance > Deck Gallery > Deck Floor, which makes generation
  ORDER significant — build the winner first.

### The flow audit, which found what no palette metric could

- **The moss room had 23 wall columns, all full height, and no doorway.** The door must be chosen
  from the columns that will actually be BUILT: 18 of the 41 wall cells are skipped for the farm's
  own water and lichen, and the first fix removed one that never existed.
- **The moss farm was ALREADY unreachable** before any of this — 0 of its 262 standable cells
  connect to the entrance in the base world. Not caused here, but worth knowing.
- **87% of the deck is reachable** from the entrance mouth; 105 cells sit in 27 isolated pockets.
- **One 3-wide neck at Z30000 carries the whole south deck** — removing any of (-24199..-24201,
  30000) splits ~128 cells from ~582. That gap is both the entrance approach and the only route to
  a third of the floor.

