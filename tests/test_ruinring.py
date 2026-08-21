"""The ruined ring-gate: geometry, the break, the seam rule, and the accents' anchors.

Everything here is asserted in WORLD coordinates off the design's own config, because the canvas
is sized to its content and shifts between builds with different settings - the deckfloor soffit
tests learned that the hard way.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
import yaml

from mcbuild import nbt, palette, schem
from mcbuild.gen import GENERATORS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(os.path.join(ROOT, "configs", "lowland_portal.yaml")))
PLANNED = os.path.join(ROOT, "out", "lowland_planned.litematic")

MASONRY = {"polished_blackstone_bricks", "cracked_polished_blackstone_bricks", "blackstone",
           "gilded_blackstone", "chiseled_polished_blackstone"}

needs_world = pytest.mark.skipif(not os.path.exists(PLANNED),
                                 reason="needs out/lowland_planned.litematic (run sync first)")


@pytest.fixture(scope="module")
def built():
    c = GENERATORS["ruinring"].build(CFG["params"], None)
    m = c.to_model()
    ox, oy, oz = c.world_origin
    cells = {}
    for i, name in enumerate(m.names):
        short = name.split(":")[-1]
        props = nbt.state_props(m.palette[i])
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            if short in ("air", "cave_air", "void_air"):
                continue
            cells[(x + ox, y + oy, z + oz)] = (short, props)
    return c, cells


def _ring_frame(c):
    cx, cy, cz = c.meta["centre"]
    return cx, cy, cz


def _theta(dy, dz):
    """degrees from the crown, positive toward north (-Z) - the generator's own convention"""
    return math.degrees(math.atan2(-dz, dy))


@needs_world
def test_the_masonry_covers_the_circle_except_the_break(built):
    c, cells = built
    cx, cy, cz = _ring_frame(c)
    a0, a1 = CFG["params"]["break_arc"]
    covered = set()
    for (x, y, z), (name, _) in cells.items():
        if name in MASONRY and abs(x - cx) <= 1:
            covered.add(int(round(_theta(y - cy, z - cz))))
    # everything OUTSIDE the break and above the burial line should be masonry. The ground on
    # the ring line runs to Y~52 against a centre of ~56, so terrain legitimately owns angles
    # past ~100 degrees - judge only the arc that must stand in the air.
    missing = [a for a in range(-100, 101) if not (a0 - 2 <= a <= a1 + 2)
               and a not in covered and min(abs(a - b) for b in covered) > 2]
    assert not missing, f"gaps outside the break at degrees {missing[:8]}"


@needs_world
def test_the_break_is_real_and_the_stubs_step_down(built):
    c, cells = built
    cx, cy, cz = _ring_frame(c)
    a0, a1 = CFG["params"]["break_arc"]
    R_out = CFG["params"]["outer_d"] / 2.0 - 0.01
    for (x, y, z), (name, _) in cells.items():
        if name not in MASONRY or abs(x - cx) > 1:
            continue
        d = math.hypot(z - cz, y - cy)
        if d < R_out - 3.2:
            continue                                   # the fallen chunk lies inside the circle
        th = _theta(y - cy, z - cz)
        assert not (a0 + 2 < th < a1 - 2), f"masonry inside the break at {th:.0f} deg {(x, y, z)}"
        if a1 < th <= a1 + 7 or a0 - 7 <= th < a0:
            assert d > R_out - 1.6, "a break stub kept its inner courses - the fracture is a shear"


@needs_world
def test_the_crown_keystone_survives_the_ruin(built):
    c, cells = built
    cx, cy, cz = _ring_frame(c)
    crown = [n for (x, y, z), (n, _) in cells.items()
             if abs(z - cz) <= 1 and y > cy + 10 and n == "chiseled_polished_blackstone"]
    assert len(crown) >= 4, "the crown keystone is gone - the ruin took the order"


@needs_world
def test_the_ring_reaches_its_extremes(built):
    c, cells = built
    cx, cy, cz = _ring_frame(c)
    D = CFG["params"]["outer_d"]
    mas = [(x, y, z) for (x, y, z), (n, _) in cells.items() if n in MASONRY]
    assert max(y for _, y, _ in mas) - cy >= D // 2, "the crown does not reach the circle's top"
    assert max(z for _, _, z in mas) - cz >= D // 2 - 1, "the south springer is short"
    assert cz - min(z for _, _, z in mas) >= D // 2 - 1, "the north springer is short"


@needs_world
def test_nothing_covers_the_world(built):
    """The seam rule: every cell the design emits sits where the world holds air or a block the
    player clears first. Water, ice, lanterns and the ground are all someone else's."""
    from mcbuild.gen.ruinring import _PASSABLE
    _, cells = built
    world = schem.load(PLANNED)
    o = json.load(open(PLANNED[:-len(".litematic")] + ".scan.json"))["origin"]
    names = [n.split(":")[-1] for n in world.names]
    for (x, y, z) in cells:
        wx, wy, wz = x - o["x"], y - o["y"], z - o["z"]
        if 0 <= wy < world.ids.shape[0] and 0 <= wz < world.ids.shape[1] and 0 <= wx < world.ids.shape[2]:
            wn = names[world.ids[wy, wz, wx]]
            assert wn in _PASSABLE, f"design covers {wn} at {(x, y, z)}"


@needs_world
def test_no_expensive_blocks(built):
    _, cells = built
    tiers = {palette.tier(n) for n, _ in cells.values()}
    assert "expensive" not in tiers


@needs_world
def test_every_stair_faces_the_ascent(built):
    _, cells = built
    stairs = [(k, v) for k, v in cells.items() if v[0].endswith("_stairs")]
    assert stairs, "the threshold lost its steps"
    for (x, y, z), (n, props) in stairs:
        assert props.get("facing") == "east" and props.get("half") == "bottom", \
            f"stair at {(x, y, z)} is {props} - a flight ascending east faces east"


@needs_world
def test_slabs_record_their_half(built):
    _, cells = built
    slabs = [v for v in cells.values() if v[0].endswith("_slab")]
    assert slabs and all(v[1].get("type") == "bottom" for v in slabs)


@needs_world
def test_the_accents_are_anchored(built):
    """A cluster with no support face is the floating-mane failure in miniature."""
    _, cells = built
    world = schem.load(PLANNED)
    o = json.load(open(PLANNED[:-len(".litematic")] + ".scan.json"))["origin"]
    wnames = [n.split(":")[-1] for n in world.names]

    def world_solid(x, y, z):
        wx, wy, wz = x - o["x"], y - o["y"], z - o["z"]
        if 0 <= wy < world.ids.shape[0] and 0 <= wz < world.ids.shape[1] and 0 <= wx < world.ids.shape[2]:
            n = wnames[world.ids[wy, wz, wx]]
            return n not in ("air", "cave_air", "void_air", "vine")
        return False

    FACE = {"up": (0, -1, 0), "down": (0, 1, 0), "north": (0, 0, 1), "south": (0, 0, -1),
            "west": (1, 0, 0), "east": (-1, 0, 0)}
    for (x, y, z), (n, props) in cells.items():
        if n == "amethyst_cluster":
            dx, dy, dz = FACE[props["facing"]]
            s = (x + dx, y + dy, z + dz)
            assert s in cells or world_solid(*s), f"cluster at {(x, y, z)} grows from nothing"
        if n == "glow_lichen":
            faces = [f for f, v in props.items() if v == "true"]
            assert faces, "a lichen with no face clings to nothing"
            for f in faces:
                dx, dy, dz = FACE[f]
                s = (x - dx, y - dy, z - dz)
                assert s in cells or world_solid(*s), f"lichen at {(x, y, z)} clings to air"
        if n == "soul_lantern":
            assert props.get("hanging") == "false"
            assert (x, y - 1, z) in cells, f"lantern at {(x, y, z)} stands on nothing of ours"


@needs_world
def test_the_fallen_chunk_is_one_piece(built):
    """One coherent fragment in the moss - scatter is the 'tossed grouping of vague blocks' the
    void tower was rejected for."""
    c, cells = built
    cx, cy, cz = _ring_frame(c)
    R_out = CFG["params"]["outer_d"] / 2.0
    low = {k for k, (n, _) in cells.items()
           if n in MASONRY and (abs(k[0] - cx) > 1 or math.hypot(k[2] - cz, k[1] - cy) < R_out - 3.2)}
    assert low, "no fallen chunk"
    from collections import deque
    comps = []
    seen = set()
    for start in low:
        if start in seen:
            continue
        q, comp = deque([start]), {start}
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (x + dx, y + dy, z + dz)
                if nb in low and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    q.append(nb)
        comps.append(comp)
    assert len(comps) == 1, f"the fallen arc is {len(comps)} fragments, not one chunk"
