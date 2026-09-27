## The lowland glow: lighting solved by propagation (2026-08-22)

Jack: find a way to add more light in smart ways; everything as built is final, mismatches
accepted. The audit PROPAGATED block light through the assumed-final composite (capture +
every tracked design, standing water never displaced) - the court hall's freeze-guard
method, scene-wide - and classified the walking surface. What it found reframed the job:

- **The floor was never the problem.** 250 spawnable columns out of 6,321 - the ground's
  lantern grid plus 39 ochre froglights JACK HAD ALREADY SCATTERED (his own lighting idiom,
  measured at one per ~15 blocks) carry the open moss. 92 of the ground design's 212
  lanterns are lost to accepted mismatches; the froglights are what replaced them.
- **The dark was ON TOP of things**: the axolotl's back (90 wool cells), the ring's crown,
  the sanctum's crests, the campanile's deck and its owl's head, house A's roof, tree
  canopies, four stair treads mid-gap between rail lanterns. Light placed at eye level
  never reaches a crown, and a spawnable crown puts a zombie on the portal at night.
- **The pond's lighting was never coming**: the ground design planned a FROZEN pond -
  1,007 ice with 92 lanterns under it - and Jack built the open-water harbor instead.
  Dead letters, all of it, and the harbor sat dark.
- **~3,700 columns hide dark buried seams UNDER the massif fill** - real spawn spaces,
  sealed, unlightable from outside. Reported, out of scope: a mob-cap leak for another day.

**`Lowland Glow`** (gen/lowglow.py, 29 blocks, 0 problems and 0 overlap in an 8-capture
context): the solver placed story fixtures first, then greedily covered - the right tool
per surface, full re-propagation each round - until ZERO spawnable surface cells remained.
The per-surface rules are the design: froglight flush in turf (dig the turf cell - Jack's
idiom continued), soul flames on ruin crests (light 10 covers what five amethysts cannot;
they trace the crest strip behind the ring), glow lichen face-down on canopies and the
AXOLOTL'S BACK (a lush cave grows light on what stands still; nothing else ever lands on
an animal), sea pickles in the harbor shallows (the water lights itself), one warm chimney
lamp on house A, one soul lantern HUNG in the watergate arch, one on the campanile crown
beside the owl, one on a stair rail post. `tests/test_lowland_glow.py` re-runs the
propagation over the finished composite and asserts the zero - the test, not a player at
night, is what finds a regression.

Traps, all of which produced a wrong number or a broken build before the right one:

- **The lowest-standable classifier struck a THIRD time**: it graded buried seams and
  called 72% of the floor dark; the true surface (topmost standable) was 4% dark.
- **A config key named `on` does not exist**: YAML 1.1 parses on/off/yes/no as BOOLEANS
  and the key silently vanished. It is `footing` now.
- **The fixture overlay defers to nobody, deliberately**: the ground design's litematic
  holds ALL its cells, built included, so defer_to dropped fixtures standing over built
  turf - and the new deferral-orphan sweep then ate the cross-design-supported lamps. A
  solved overlay contests no live work; its config says so instead of deferring.
- **Overlaying the dead ice into the test's composite shadowed the axolotl's fin** into a
  false dark - ice is opaque, the pond is water, mismatches are accepted BOTH ways.
- **`waterlogged` is not in work.INTENTIONAL**, so a test that greps work.json for it
  tests the wrong artifact (the pane lesson, again). The water at the position is the
  assertion.

### The world moved mid-session, and what it broke (2026-08-23, 14:32 scan)

Jack rescanned while the glow was being solved: the town is BUILT (hamlet 97%, campanile
93%, turtle 96%, root 100%, stair 74%), and three things broke at once, each instructive:

- **The belly's vines hung from TRIPWIRE.** Jack strung string lines under the plate; the
  vine walk skipped those cells (tripwire is rightly not solid) and kept emitting BELOW
  them - orphan strands in context. `_already_built` now returns an OCCUPIED mask too, and
  a strand stops at any world-occupied cell it cannot claim. Same family as vine-as-footing
  and -1-is-truthy: "not solid enough to cling to" does not mean "not there".
- **The town tests hit the snapshot trap at scene scale**: they regenerated designs against
  the fresh capture, and remaining-work regen strips every built cell - the door-frame test
  failed because the door frame is BUILT. Fixtures read the SHIPPED litematics now (the
  full intent, what the printer places), the ruinring tests' lesson generalised.
- **Jack substituted a neighbouring band's slab on 22 stair cells** - accepted mismatch on
  his own stair, which the replaces-nothing contract must not read as a collision. The
  stair's own material family is exempt.

`out/island_full.litematic` and `island_deep` are re-cut from the newest scan; the glow
re-validated against it (every fixture still stands, the propagation zero still holds).

