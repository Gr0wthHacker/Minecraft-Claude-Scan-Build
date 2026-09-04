"""The castle bridge: two anchored stubs, a real gap, a level deck, nothing floating.

Everything a broken span over the void can get wrong quietly: a fragment with only corner
contact (unbuildable and it LOOKS snapped-off wrong), a deck that sags a course mid-span, a
gap that closed because two stubs rounded into each other.
"""
import json
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
import yaml

from mcbuild import palette, schem
from mcbuild.gen import GENERATORS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(os.path.join(ROOT, "configs", "castle_bridge.yaml")))
ZONE = os.path.join(ROOT, "out", "bridge_zone.litematic")

needs_world = pytest.mark.skipif(not os.path.exists(ZONE),
                                 reason="needs out/bridge_zone.litematic (see the config header)")

A = CFG["params"]["a"]
B = CFG["params"]["b"]


@pytest.fixture(scope="module")
def built():
    c = GENERATORS["voidbridge"].build(CFG["params"], None)
    m = c.to_model()
    ox, oy, oz = c.world_origin
    cells = {}
    for i, name in enumerate(m.names):
        short = name.split(":")[-1]
        if short in ("air", "cave_air", "void_air"):
            continue
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            cells[(x + ox, y + oy, z + oz)] = short
    return c, cells


@pytest.fixture(scope="module")
def world():
    m = schem.load(ZONE)
    o = json.load(open(ZONE[:-len(".litematic")] + ".scan.json"))["origin"]
    names = [n.split(":")[-1] for n in m.names]
    return m, o, names


def _wsolid(world, x, y, z):
    m, o, names = world
    wx, wy, wz = x - o["x"], y - o["y"], z - o["z"]
    if 0 <= wy < m.ids.shape[0] and 0 <= wz < m.ids.shape[1] and 0 <= wx < m.ids.shape[2]:
        return names[m.ids[wy, wz, wx]] not in ("air", "cave_air", "void_air", "vine")
    return False


@needs_world
def test_every_component_is_anchored(built, world):
    _, cells = built
    todo = set(cells)
    seen = set()
    for start in sorted(todo):
        if start in seen:
            continue
        q, comp = deque([start]), {start}
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (x + d[0], y + d[1], z + d[2])
                if nb in todo and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    q.append(nb)
        anchored = any(_wsolid(world, x + d[0], y + d[1], z + d[2]) for x, y, z in comp
                       for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))
        assert anchored, f"floating fragment of {len(comp)} cells at {sorted(comp)[0]}"


@needs_world
def test_the_gap_is_real_and_the_stubs_are_not(built):
    _, cells = built
    ux, uz = B[0] - A[0], B[2] - A[2]
    L2 = ux * ux + uz * uz
    ts = sorted(((x - A[0]) * ux + (z - A[2]) * uz) / L2 for (x, y, z) in cells)
    mid = [t for t in ts if 0.45 < t < 0.55]
    assert not mid, f"{len(mid)} cells inside the gap - the break healed itself"
    near = sum(1 for t in ts if t <= 0.45)
    far = sum(1 for t in ts if t >= 0.55)
    assert near >= 10 and far >= 8, f"stubs too small ({near}/{far}) to read as a broken span"


@needs_world
def test_the_deck_is_level(built):
    c, cells = built
    deck_y = c.meta["deck_y"]
    slabs = {(x, y, z) for (x, y, z), n in cells.items() if n.endswith("_slab")}
    assert slabs and all(y == deck_y for _, y, _ in slabs), "a bridge deck is LEVEL"


@needs_world
def test_the_lantern_marks_the_island_end(built):
    """WARM light: this is the island's bridge, not the quarter's - cold soul-fire stays in
    the lowland with the blackstone."""
    _, cells = built
    lanterns = [(x, y, z) for (x, y, z), n in cells.items() if n == "lantern"]
    assert len(lanterns) == 1
    x, y, z = lanterns[0]
    assert cells.get((x, y - 1, z), "").endswith("_wall"), "the lantern has no post"
    assert math.hypot(x - A[0], z - A[2]) <= 4, "the light belongs at the island end"


@needs_world
def test_no_blackstone_above_the_lowland(built):
    """The palette boundary: blackstone is the gate cult's foreign masonry and it never climbs
    past the lowland. Everything at island level is the island's grey."""
    _, cells = built
    assert not any("blackstone" in n for n in cells.values())


@needs_world
def test_no_expensive_and_no_cover_and_no_bat_collision(built, world):
    _, cells = built
    assert "expensive" not in {palette.tier(n) for n in cells.values()}
    for (x, y, z) in cells:
        assert not _wsolid(world, x, y, z), f"covers the world at {(x, y, z)}"
    bat = {(c[0], c[1], c[2]) for c in
           json.load(open(os.path.join(ROOT, "out", "Lowland Bat.work.json")))["cells"]}
    assert not (set(cells) & bat), "shares cells with the bat's own design"
