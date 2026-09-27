## Faces, and the visual audit that found them (2026-08-19)

Jack looked at the renders and said the bear was a cow, the jaguar's face was a mess and the
capybara had "no eyes, just a mask". All three were true and none of them was visible in any score.

- **The eye was the same block as the coat pattern.** A jaguar's eyes are `black_wool` and so are
  its rosettes, so an eye landed among a dozen identical black cells. The pattern is now kept off
  the whole skull (`_face_zone`) — shading is NOT, because on a dark animal the shading is the only
  thing lifting the face clear of the coat, and flattening it cost the bear the eyes it had.
- **The eye was a two-cell bar, not a bead.** With the muzzle painting either side of it the
  capybara's brow read as one continuous stripe. It is now one cell, ringed with every solid
  neighbour forced pale.
- **The ring was the muzzle block, which is often the coat.** `stripped_jungle_log` on `acacia_log`
  is a 2-point difference. `_eye_ring` now takes the muzzle only if it is 35 luminance clear of the
  coat, and otherwise picks the palest plain block in the registry by measurement.
- **The ears were flat slabs at brow height, pushed out sideways** — which is a cow, or a moose. A
  small ear now sits ON the cranium above the eye. An elephant's really is a side-hung fan and keeps
  the old placement, switched on `ear_size >= 1.5`.
- **`drop` did nothing at all.** `rise = 1 - 2*drop` was computed in `_neck` and never used, so the
  neck stepped up one course per segment whatever the pose said. Every grazing, stalking and leaping
  animal ended with its head at the top of a rising neck. This is what the earlier pose diagnostic
  was seeing when it put the prowling jaguar's neck 1.86x and the grazing bear's 2.14x adrift.
- **Moving the ears broke the withers.** `_segment` scans whole courses, so on a cat — whose head
  sits at body height — it measured the head, and then the ears: the jaguar's barrel read 40% too
  deep for a change that never touched the barrel. The withers is now taken inside the recorded
  body window.

**Still wrong: the bear's eyes do not read.** They are built and correctly placed, but `mangrove_wood`
is dark enough that a black bead on it has nowhere to go, and the broad blunt skull hides them from a
straight-on view. The fix is a lighter face mask on the ursid coat, not more geometry.

