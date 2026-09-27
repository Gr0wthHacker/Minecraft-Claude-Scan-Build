## The Wyrm Gate: the skull straddling the rim railway (2026-09-03)

Jack: *"are we able to place the skull so that the mouth 'opens' around the railway, the back of
the skeleton is towards the void and the mouth gap is where the railway passes through sideways"*
- then *"do it"*, and then, on the first build, ***"the skull is oriented the wrong way, we can be
looking at the back of a flat skull, it loses its meaning."*** `configs/pf_wyrm_gate.yaml`,
`mcbuild/gen/wyrmgate.py`, `tests/test_wyrmgate.py` (15). **27,857 blocks, 0 problems, 0 overlap
in context, 0 expensive, and NOT ONE CELL OF THE RAILWAY TAKEN.** `Wyrm's Crossing` keeps the
paved crossing and no longer carries a skull, so the skull is in one place.

### THE FACING WAS WRONG AND THE TEST UNDER IT PASSED

The worst thing here, and the most useful. `rotate: 90` shipped, with a test asserting **that the
CRANIUM starts at the model's low-V edge** - which is true of that turn and says *nothing about
which end of the cranium the face is on*. It is the turn that points the face at the void, so a
visitor in the park got the open back of the vault: a hollow shell with a garden inside it.

**RENDERED FROM BOTH SIDES THE ANSWER IS NOT ARGUABLE** - from one side a brow, two socketed eyes
with planted terraces in them, a nasal and a palate over a garden; from the other, the inside of
the same skull. What went wrong is that I derived the facing from plan printouts of the ORIGINAL
model and never rendered the two candidates side by side, which takes eight seconds. **Our
renderer draws a skull facing either way identically, so the only checks that can catch this are a
picture of each candidate and arithmetic - and the arithmetic has to measure the FEATURE.** It
measures the EYE SOCKETS now: they are cavities, so along the socket courses the model is empty on
the side you look in from and solid where the nasal and the socket's back wall stand, and the
shipped turn must leave that mass in the far half of the depth. 20 cells against 528.

### AND THE MOUTH IS A RECESS, NOT A TUNNEL - WHICH ALSO CAME FROM READING PLANS

The first build's whole argument was that the mouth is "a tunnel along the face's own normal, open
front to back", from which followed "his orientation is the only one that fits". **Both were
wrong.** Measured column by column over the turned model, the skull's body starts at its own V+19
and the mouth's band is open for about eleven columns behind the face and solid behind that: a
RECESS. The emptiness further back that read as a through-tunnel is the diorama's own stepped
forecourt, which is in FRONT of the face, not behind it.

So the railway's fifteen-wide corridor cannot sit inside the mouth: at `at: [153, 366]` the recess
covers V172-183, which is twelve of the fifteen and includes the near track at V174 in open air,
and the far track at V184 runs through a bore in the jaw's own mass. Measured over the finished
build, the roof over the two tracks says exactly that: **the near track is roofed seven to
fourteen courses up with no portal at all, and the far one ducks under a five-course portal at
each ramus and opens out to eighteen between them.** The nineteen columns in front (V157-171) are
the diorama's forecourt, and they land on the lawn in front of the face where an approach belongs.

### THE JAW IS AS DEEP AS THE RAILWAY IS WIDE, AND THAT IS WHAT MAKES THIS DELICATE

- **Every cell of the railway is refused**, loaded from `out/Park Rail.litematic` - so `overlap 0`
  is a property of the construction and the line can be regenerated under it.
- **Seven courses across the WHOLE corridor** (Y211-217) are refused: the box girder, the rails,
  and the headroom a walker on the promenade and a rider in a cart each need. **REFUSING ONLY THE
  ARTIFACT'S CELLS WOULD HAVE WALLED UP THE PROMENADE AND PASSED EVERY CHECK, because a promenade
  is made of air.** Same shape as the deck soffit's lesson: what a design must not cover is not
  always a block. Verified on the shipped park: 108 of 108 rail cells standing, 0 cells in the
  rider clearance, 0 in the promenade, and the arcade under the viaduct still floods end to end.
- **The two walks it crosses are bored**: the line's arcade at the plate (the park-side passage
  each pier already leaves beside its five-wide core) and `Park Ways`' rim boundary line at V170,
  a paved course carrying fence posts.
- **A FLAT CLEARANCE BAND LEAVES A SAWN PLANE.** A rider's whole view is the soffit over the
  track; cut level it is a horizontal plate fifteen columns wide - a beam, not a jaw. The band is
  a semi-ellipse: level at the parapets, three courses higher at the centre.

### THE ASSET IS NOT A BARE SKULL, AND THAT SET THE SINK

Its jaw holds a diorama - terraces, trees, a pond, steps and a golden shrine - and that garden is
exactly where a railway wants to be. Driving the deck through it costs **1,846 cells of somebody
else's build**; six courses down it sits at Y204-210, the whole of it UNDER the girder, intact and
visible from the line's own arcade. Any less and the deck slices its trees off; any more and the
palate drops into the rider's clearance. What the sink costs is the bottom six courses of the
diorama's base, which fall below the park's plate and are trimmed.

**AND THE TRAP IN THE GARDEN IS NOT SHIPPED.** The ruins are booby-trapped: **77 TNT and eight
stone pressure plates** round the chest and the gold block. Fine in somebody's own diorama; not a
thing to hang over a working railway, where the printer arms it on placement. Both are dropped by
name and the count is recorded in the sidecar. The park's own circuit inspection reported the 54
that reached the first build as unwired charges, which is how they were found.

### Four more traps, each of which built cleanly and was wrong

- **THE ASSET'S PALETTE IS NOT THE CANVAS'S PALETTE.** Copying an index straight across writes a
  number that means a different block here and, past the end of the registry, nothing at all -
  which is not a wrong block, it is a file the writer cannot compact.
- **THE CEILING IS THE LOWEST CELL ABOVE THE GIRDER, NOT THE LOWEST CELL.** Measured off the
  skull's own underside the answer is the garden in its jaw, which stands UNDER the deck - so the
  lamp pass lit the garden's floor and left a fifty-four column tunnel over live rails with ONE
  froglight in it. Twice: the second time because the palate STEPS, and only six of its columns
  sit on the lintel course exactly.
- **A SPUR CLAMPED TO "ONE UNDER THE COLUMN'S LOWEST CELL" CANNOT BRIDGE A GAP ABOVE SOMETHING.**
  A 5,900-cell rock spur was written to carry the skull when the first placement left it hanging;
  on the rim the skull's own base already stood on the plate, so every column read as satisfied,
  731 cells went in, and the cranium stayed a separate piece. **The spur is off in the shipped
  design** - turning the skull round put its own forecourt on the ground in front of it, which
  does the same job with the asset's own stone. The machinery stays, unused, with the reason.
- **A PLANT ROOTS IN THE DIRT FAMILY AND NOWHERE ELSE** (rule 11). The diorama carries tufts of
  short grass standing on its own `smooth_stone` paving - legal in the builder's world only
  because nobody asked, and placement problems here the moment those courses came inside the plot.
  They are dropped rather than re-bedded: moving somebody else's paving to suit a tuft of grass is
  the worse answer.

### The night side, measured rather than assumed

Propagated over the finished composite: **460 standable cells inside this footprint stood at block
light zero BEFORE the design existed** - the rim behind the railway is nobody's guest path, and the
park's night pass grades a column by its TOPMOST standable cell, so it never saw it. The gate
leaves 80 at the old placement: 54 in deep shade on the ground and 26 on the skull's own crown,
which is open to the sky, and **NONE on the deck**. The lamps are set INTO the mouth's roof and
INTO the ground the skull shades - never laid on the coat, which is the frog's own rule.

### Still open, stated rather than left

- **Nothing has been looked at in game.** All of it is `render3d`, which draws with the same colour
  DB the palette picker optimises against - judge form here and palette in world.
- **The design is three grounded pieces in isolation**, deliberately: the arcade bore separates the
  forecourt from the skull, and the rim lamps are one cell each on the plate. The test asserts what
  actually matters - the body is one piece and **nothing floats**.
- **`polished_andesite_stairs` warns as "not in the provisional 1.19 list"**; it is a real 1.19
  block and the allowlist is the stale thing, which `audit` only ever reports.
- **`tests/test_parkways.py`** still fails on `Wyrm's Crossing (58x44) does not fit its lot` and on
  five modules with no lot and no reason, and **`tests/test_worldrender.py`** on `module Signal
  Heron footprint does not fit its plot`. All three pre-date this work; the last is the mismatch
  `PARK_RAILWAY_RENEWAL.md` already declines to repair silently.

