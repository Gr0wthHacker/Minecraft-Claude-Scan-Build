"""The ruins quarter: the walk works, the fragments stand on real ground, nothing is covered.

Asserted in WORLD coordinates off the config, against the same composite the design verifies
against - the deckfloor soffit rule.
"""
import json
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
import yaml

from mcbuild import nbt, palette, schem
from mcbuild.gen import GENERATORS
from mcbuild.gen.ruinring import _PASSABLE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(os.path.join(ROOT, "configs", "lowland_ruinway.yaml")))
PLANNED = os.path.join(ROOT, "out", "lowland_planned.litematic")

needs_world = pytest.mark.skipif(not os.path.exists(PLANNED),
                                 reason="needs out/lowland_planned.litematic (run sync first)")


@pytest.fixture(scope="module")
def built():
    c = GENERATORS["ruinway"].build(CFG["params"], None)
    m = c.to_model()
    ox, oy, oz = c.world_origin
    cells = {}
    for i, name in enumerate(m.names):
        short = name.split(":")[-1]
        if short in ("air", "cave_air", "void_air"):
            continue
        props = nbt.state_props(m.palette[i])
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            cells[(x + ox, y + oy, z + oz)] = (short, props)
    return c, cells


@pytest.fixture(scope="module")
def world():
    m = schem.load(PLANNED)
    o = json.load(open(PLANNED[:-len(".litematic")] + ".scan.json"))["origin"]
    names = [n.split(":")[-1] for n in m.names]
    return m, o, names


def _wname(world, x, y, z):
    m, o, names = world
    wx, wy, wz = x - o["x"], y - o["y"], z - o["z"]
    if 0 <= wy < m.ids.shape[0] and 0 <= wz < m.ids.shape[1] and 0 <= wx < m.ids.shape[2]:
        return names[m.ids[wy, wz, wx]]
    return "air"


@needs_world
def test_nothing_covers_the_world(built, world):
    _, cells = built
    for (x, y, z) in cells:
        assert _wname(world, x, y, z) in _PASSABLE, f"covers {_wname(world, x, y, z)} at {(x, y, z)}"


@needs_world
def test_pavement_rests_on_ground_and_stairs_face_the_ascent(built, world):
    """A tread with air under it is the rimstair's floating flight; a stair facing away from
    its climb cannot be walked up (test_stairhead)."""
    _, cells = built
    FACE = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
    stairs = 0
    for (x, y, z), (n, props) in cells.items():
        # a LANDING stair is one standing at the water's edge - judged by the water itself,
        # not by a bounding box: the way's own first steps share the quay's box
        landing = any(_wname(world, x + dx, y - 1, z + dz) in ("water", "ice")
                      for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if n.endswith("_slab") or n.endswith("_stairs"):
            below = _wname(world, x, y - 1, z)
            assert (x, y - 1, z) in cells or below not in \
                ("air", "cave_air", "void_air", "vine", "water"), \
                f"{n} floats at {(x, y, z)} over {below}"
        if n.endswith("_stairs"):
            stairs += 1
            assert props.get("half") == "bottom"
            dx, dz = FACE[props["facing"]]
            ahead = _wname(world, x + dx, y, z + dz)
            if landing:                                # a landing step ascends out of the WATER:
                behind = _wname(world, x - dx, y - 1, z - dz)
                assert behind in ("water", "ice"), \
                    f"landing stair at {(x, y, z)} does not rise from the water"
            else:
                assert ahead not in ("air", "cave_air", "void_air"), \
                    f"stair at {(x, y, z)} ascends toward open air - it faces away from its climb"
    assert stairs >= 15, "the climb to the rim lost its steps"


@needs_world
def test_the_quay_holds_the_waterline(built, world):
    """Every lip cell touches real water; the posts stand ON the lip; nothing enters the pond."""
    _, cells = built
    q = CFG["params"].get("quay")
    if not q:
        pytest.skip("no quay configured")
    lip = 0
    posts = 0
    for (x, y, z), (n, _) in cells.items():
        if _wname(world, x, y, z) in ("water", "ice"):
            raise AssertionError(f"quay cell inside the pond at {(x, y, z)}")
        if n == "polished_blackstone_brick_wall" and (x, y - 1, z) in cells:
            posts += 1
        if n in ("chiseled_polished_blackstone", "polished_blackstone_bricks", "blackstone",
                 "cracked_polished_blackstone_bricks"):
            near_water = any(_wname(world, x + dx, y - 1, z + dz) in ("water", "ice")
                             for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if near_water and min(q["from"][0], q["to"][0]) - 1 <= x <= max(q["from"][0], q["to"][0]) + 1:
                lip += 1
    assert lip >= 8, f"only {lip} lip cells hold the waterline"
    assert posts >= 2, f"only {posts} mooring posts"


@needs_world
def test_the_pavement_is_ruined_but_walkable(built):
    c, _ = built
    f = c.meta["features_built"]
    total = f["slabs"] + f["stairs"] + f["gaps"]
    assert 0.03 <= f["gaps"] / total <= 0.30, f"decay {f['gaps']}/{total} out of range"


@needs_world
def test_the_bridge_ends_over_open_water_broken(built, world):
    _, cells = built
    b = CFG["params"]["bridge"]
    if not b:
        pytest.skip("the bridge yielded to the quay - it read as a fishing jetty (2026-08-21)")
    deck = [(x, y, z) for (x, y, z), (n, _) in cells.items()
            if n.endswith("_slab") and abs(x - b["from"][0]) <= 2 and b["from"][1] - 6 <= z <= b["from"][1]]
    over_water = [c for c in deck if _wname(world, c[0], c[1] - 1, c[2]) in ("water", "ice")]
    assert len(over_water) >= 3, "the bridge never leaves the bank"
    assert len({y for _, y, _ in deck}) == 1, "a bridge deck is LEVEL"
    far_row = min(z for _, _, z in deck)
    near_row = max(z for _, _, z in deck)
    n_far = sum(1 for _, _, z in deck if z == far_row)
    n_near = sum(1 for _, _, z in deck if z == near_row)
    assert n_far < n_near, "the broken end is not broken"


@needs_world
def test_the_apse_stands_in_its_skylight_open_to_the_scene(built):
    _, cells = built
    a = CFG["params"]["apse"]
    if not a:
        pytest.skip("the apse yielded its ground to the Lowland Sanctum (2026-08-21)")
    ax, az = a["at"]
    r = a["r"]
    wallish = [(x, y, z) for (x, y, z), (n, _) in cells.items()
               if r - 0.6 <= math.hypot(x - ax, z - az) <= r + 1.2 and n != "amethyst_cluster"]
    assert len(wallish) >= 35, f"the apse is {len(wallish)} cells of wall - a stub, not a fragment"
    for x, y, z in wallish:                            # rubble lies INSIDE the ring and is exempt
        ang = math.degrees(math.atan2(z - az, x - ax))
        assert abs(ang) <= 85, f"apse wall inside its own opening at {(x, y, z)} ({ang:.0f} deg)"
    blooms = [(x, y, z) for (x, y, z), (n, _) in cells.items() if n == "amethyst_cluster"]
    assert len(blooms) == 1
    bx, by, bz = blooms[0]
    assert any((bx + d[0], by + d[1], bz + d[2]) in cells for d in
               ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))), \
        "the bloom grows from nothing"


@needs_world
def test_lanterns_stand_on_this_designs_own_cells(built):
    _, cells = built
    lanterns = [(x, y, z) for (x, y, z), (n, props) in cells.items() if n == "soul_lantern"]
    assert len(lanterns) >= 4
    for x, y, z in lanterns:
        assert (x, y - 1, z) in cells, f"lantern at {(x, y, z)} stands on nothing of ours"
        assert cells[(x, y, z)][1].get("hanging") == "false"


@needs_world
def test_no_expensive_and_no_design_collisions(built):
    """Collisions judged on the SHIPPED work list, because defer_to runs in the pipeline's
    finish pass - a raw generator build has not yielded its shared cells yet and reads as
    colliding with the very designs it defers to."""
    _, cells = built
    assert "expensive" not in {palette.tier(n) for n, _ in cells.values()}
    shipped = os.path.join(ROOT, "out", "Lowland Ruinway.work.json")
    if not os.path.exists(shipped):
        pytest.skip("ship the ruinway first")
    mine = {(c[0], c[1], c[2]) for c in json.load(open(shipped))["cells"]}
    for other in ["Lowland Portal", "Lowland Capybara Flee", "Lowland Flamingo",
                  "Lowland Axolotl", "Lowland Bat"]:
        theirs = {(c[0], c[1], c[2]) for c in
                  json.load(open(os.path.join(ROOT, "out", f"{other}.work.json")))["cells"]}
        assert not (mine & theirs), f"shares cells with {other}"


@needs_world
def test_the_walk_under_the_capybara_stays_clear(built, world):
    """The way crosses at z30019-21 because the animal's belly is above Y46 there - so nothing
    this design adds in that corridor may rise past Y45, or the player hits their head on the
    thing the crossing was measured for."""
    _, cells = built
    cap = {(c[0], c[1], c[2]) for c in
           json.load(open(os.path.join(ROOT, "out", "Lowland Capybara Flee.work.json")))["cells"]}
    for (x, y, z) in cells:
        if -24192 <= x <= -24178 and 30014 <= z <= 30026:
            assert y <= 45, f"ruinway cell at {(x, y, z)} rises into the capybara's belly room"
            for k in range(1, 3):
                assert (x, y + k, z) not in cap, f"no head-room under the capybara at {(x, y, z)}"
