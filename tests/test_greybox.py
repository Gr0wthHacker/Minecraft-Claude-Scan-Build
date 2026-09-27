from __future__ import annotations

from mcbuild import audit, greybox


def test_greybox_is_a_fast_auditable_layout_preview():
    model, plan = greybox.build({"name": "Station", "program": "ride_station", "width": 13, "depth": 17,
                                 "style": "frontier"})
    assert plan["quality"]["ok"] and model.solid().sum() > 0
    assert audit.audit(model, ground=False).ok
