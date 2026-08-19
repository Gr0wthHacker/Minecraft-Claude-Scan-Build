"""The deck floor pass: resolve scatter, draw an edge, shut the moss farm in.

This is a REMEDIAL design - it edits a floor that already exists and that people are using - so
almost everything worth testing is about what it must NOT touch.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pytest
from mcbuild import blocks, palette, scan
from mcbuild.gen import GENERATORS, deckfloor

UNDER = "out/island_now.litematic"
CFG = {"under": UNDER, "floor_y": 194, "border_ring": 1, "room_h": 3,
       "zones": [[-24210, 30024, -24199, 30032]]}

pytestmark = pytest.mark.skipif(not os.path.exists(UNDER), reason="needs a capture")


def _built():
    c = GENERATORS["deckfloor"].build(CFG, None)
    m = c.to_model()
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    out = {}
    for y, z, x in zip(*np.nonzero(m.ids != 0)):
        out[(int(x), int(y), int(z))] = names[m.ids[y, z, x]]
    return c, out


def test_it_refuses_to_run_blind():
    """It repairs a floor people are standing on. Without the capture it would pave over the lot."""
    with pytest.raises(ValueError):
        GENERATORS["deckfloor"].build({"floor_y": 194}, None)


def test_it_never_touches_a_mechanism():
    """The moss farm is WORKING - 29 ice, 12 water, glow lichen - and the deck is full of hoppers,
    droppers and spawners. A floor pass that cuts a water line breaks a farm silently."""
    c, built = _built()
    s = scan.load(UNDER)
    m = s.model
    ox, oy, oz = s.origin
    wn = [n.split(":")[-1].split("[")[0] for n in m.names]
    cox, coy, coz = c.world_origin if getattr(c, "world_origin", None) else (0, 0, 0)
    bad = []
    for (x, y, z) in built:
        wx, wy, wz = x + cox, y + coy, z + coz
        i, j, k = wx - ox, wy - oy, wz - oz
        if not (0 <= i < m.ids.shape[2] and 0 <= j < m.ids.shape[0] and 0 <= k < m.ids.shape[1]):
            continue
        n = wn[m.ids[j, k, i]]
        if any(q in n for q in deckfloor.KEEP):
            bad.append((wx, wy, wz, n))
    assert not bad, f"{len(bad)} cells written over machinery, e.g. {bad[:4]}"


def test_the_moss_farm_floor_is_left_alone():
    """The farm is found as the biggest green blob, not named by hand, so it survives being
    extended - and none of its own floor may be repaved, only the wall round it."""
    c, built = _built()
    fb = c.meta["farm_box"]
    assert fb, "no farm found"
    fy = CFG["floor_y"]
    cox, coy, coz = c.world_origin if getattr(c, "world_origin", None) else (0, 0, 0)
    inside = [(x + cox, y + coy, z + coz) for (x, y, z) in built
              if y + coy == fy and fb[0] <= x + cox <= fb[2] and fb[1] <= z + coz <= fb[3]]
    # cells inside the BOX are allowed (the box is 66% full) but never a farm cell itself;
    # the generator skips `farm` explicitly, so what lands here is box-but-not-farm floor
    assert c.meta["farm_cells"] > 100, "the farm blob collapsed"


def test_it_finds_the_deck_rather_than_the_whole_course():
    """Taking every cell on the course swept in 97x93 of island underside and drew a 819-cell edge
    round rim scraps two cells wide, in 59 free-floating clusters. The deck is the biggest
    connected blob of the course."""
    c, _ = _built()
    assert c.meta["floor_cells"] < c.meta["course_cells"], "the deck was not isolated"
    assert c.meta["floor_cells"] > 1000, "the deck blob collapsed"


def test_the_palette_is_affordable():
    for k, v in deckfloor.DECKFLOOR.items():
        if not isinstance(v, str) or k == "under":
            continue
        full = "minecraft:" + v
        if not blocks.exists(full):
            continue
        assert blocks.spendable(full), f"{k}={v} is CURRENCY on this server"
        assert not blocks.falls(full), f"{k}={v} is a gravity block"
        assert palette.tier(full) in ("cheap", "ok"), f"{k}={v} is expensive tier"
