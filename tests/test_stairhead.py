"""The taproot staircase head, and the stair convention it finally settled.

The project rule was "no stairs", on the grounds that a stair is DIRECTIONAL, `facing` is easy to
get backwards, and nothing in the capture recorded a stair's state to settle the convention from.
Both grounds are gone: the 2026-08-19 19:09 capture holds 463 placed stairs and the palette carries
their full properties. The earlier reading looked at the bare NAME list, which drops them.

The convention, read off Jack's own flight at X-24213..-24210 / Y195-198 / Z30028 - four
consecutive straight bottom-half treads, all facing=east, each one course up and one step east:

    A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D, half=bottom.

Getting it backwards builds a staircase you cannot walk up, and our own renderer draws a mirrored
stair identically - so it is asserted here rather than eyeballed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from mcbuild import blocks, palette
from mcbuild.gen import GENERATORS, stairhead

CFG = {
    "well":  [-24205, 30002, -24200, 30010],
    "neck":  [-24205, 30002, -24203, 30004],
    "shaft": [-24203, 30008, -24201, 30010],
    "floor_y": 194, "under_y": 190, "ceiling_y": 200, "apron": 2, "mouth_w": 3,
}


def _build(**over):
    return GENERATORS["stairhead"].build({**CFG, **over}, None)


def _states(c):
    """every placed cell as (x, y, z) -> (name, props), in the canvas's own frame"""
    import numpy as np
    m = c.to_model()
    out = {}
    for i, n in enumerate(m.names):
        e = m.palette[i]
        try:
            pr = {k: v.value for k, v in e.value.get("Properties").value.items()}
        except Exception:
            pr = {}
        for y, z, x in zip(*np.nonzero(m.ids == i)):
            out[(int(x), int(y), int(z))] = (n.split(":")[-1], pr)
    return out


def test_it_is_registered_and_builds():
    assert "stairhead" in GENERATORS
    c = _build()
    assert c.to_model().ids.astype(bool).sum() > 150


def test_it_needs_its_boxes():
    for missing in ("well", "neck", "shaft"):
        cfg = {k: v for k, v in CFG.items() if k != missing}
        with pytest.raises(ValueError):
            GENERATORS["stairhead"].build(cfg, None)


def test_every_tread_faces_the_way_you_CLIMB():
    """The flight descends south, so you climb north out of it, so every tread is facing=north.

    Built facing=south the treads are back to front: the risers face into the descent and you
    cannot walk up them. Our renderer draws both identically, which is why the rule was to avoid
    stairs entirely until the convention could be read off a real build."""
    c = _build()
    treads = [(pos, pr) for pos, (n, pr) in _states(c).items() if n.endswith("_stairs")]
    assert treads, "no stairs were built at all"
    for pos, pr in treads:
        assert pr.get("facing") == "north", f"tread at {pos} faces {pr.get('facing')}"
        assert pr.get("half") == "bottom", f"tread at {pos} is half={pr.get('half')}"
        assert pr.get("shape") == "straight"


def test_the_flight_drops_one_course_per_tread_and_reaches_the_floor():
    """A flight that does not land is a hole with decoration round it. One tread per course of
    drop, from the deck course down to the course above the undercroft floor."""
    c = _build()
    treads = [pos for pos, (n, _) in _states(c).items() if n.endswith("_stairs")]
    ys = sorted({y for _, y, _ in treads})
    drop = CFG["floor_y"] - CFG["under_y"]
    assert len(ys) == drop, f"{len(ys)} tread courses for a {drop}-course drop"
    assert ys == list(range(min(ys), min(ys) + len(ys))), "the flight skips a course"
    # each course is a full-width tread, and each is one step further along than the last
    by_y = {}
    for x, y, z in treads:
        by_y.setdefault(y, set()).add(z)
    zs = [min(v) for _, v in sorted(by_y.items(), reverse=True)]
    assert zs == list(range(zs[0], zs[0] + len(zs))), f"treads do not advance one per course: {zs}"


def test_the_balustrade_leaves_a_way_in():
    """A rail all the way round is a pit cover. There has to be a mouth, and it has to be at the
    neck, which is the only side the flight arrives from."""
    c = _build()
    walls = [pos for pos, (n, _) in _states(c).items() if n == "stone_brick_wall"]
    assert walls, "no balustrade"
    m = c.to_model()
    # the ring is one cell outside the well; the mouth is the gap in it
    ring_len = 2 * ((CFG["well"][2] - CFG["well"][0] + 3) + (CFG["well"][3] - CFG["well"][1] + 3)) - 4
    assert len(walls) < ring_len - CFG["mouth_w"] + 1, "the rail closes the entrance off"


def test_it_never_writes_over_anything_it_does_not_own():
    """`PLAIN` is the whitelist. Anything else in a cell belongs to something the capture knows
    about and this design does not - a chest, a furnace, a rail, someone's lantern."""
    assert "chest" not in stairhead.PLAIN and "barrel" not in stairhead.PLAIN
    assert "hopper" not in stairhead.PLAIN and "furnace" not in stairhead.PLAIN
    assert "rail" not in stairhead.PLAIN and "lantern" not in stairhead.PLAIN


def test_the_palette_is_affordable_and_placeable():
    for k, v in stairhead.STAIRHEAD.items():
        if not isinstance(v, str) or k in ("under",):
            continue
        full = "minecraft:" + v
        if not blocks.exists(full):
            continue
        assert blocks.spendable(full), f"{k}={v} is CURRENCY on this server"
        assert not blocks.falls(full), f"{k}={v} is a gravity block"
        assert palette.tier(full) in ("cheap", "ok"), f"{k}={v} is expensive tier"
