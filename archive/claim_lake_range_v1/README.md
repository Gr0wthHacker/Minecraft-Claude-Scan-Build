# PF Claim Lake Range - archived 2026-09-03, never shipped to the live park

Jack, after placing it and looking: "this looks terrible in current state, the blocks are
sticking out the back etc, i dont think we can do this in a clean way as specified."

He is right, and the cause was structural, not a siting mistake. `arcade._range`'s own
`_pit_floor` call lays a concealed award-delivery floor 12 courses BEHIND the visible 12-deep
booth - a 24-26 deep footprint on a generator built for `gen/park.py`'s indoor/pit-friendly lot
geometry. Turning it to keep that depth inside the reach's own V-band (see the superseded
`configs/claim_lake_range.yaml` here) got the bounding box to fit on paper, but the actual
placed shape is a shooting-booth front with a long bare service slab trailing off its back -
correct by every offline check (`problems: 0`, `overlap` against only lawn and the ground
layer) and visibly wrong the moment it stood in the world. Offline geometry checks catch
illegal states and collisions; they do not catch "does the back of this look designed."

Withdrawn before being added to `EXTRAS_READY` in `tools/park_place.py` - it was never part of
a shipped `Park Complete`. Kept here, config and litematic both, as the record of why `arcade`'s
`range`/`plinko`/similar pit-backed kinds want a lot with real depth behind the visible front,
not a narrow reach shoulder.

Replaced by a small paddock/menagerie concept - see `configs/claim_lake_menagerie.yaml` (or
successor) for what actually went in this square.
