"""The friend island's twin stairs (2026-09-04).

Two slab helices off the alcoves at each end of a platform arm, meeting under the log spoke in a
stone-brick pier that carries one wider stair down. Pinned here:

- the WALK: from the bottom pad to the deck, in the composite of the design and the capture, with
  the audit's own step rules (half a block up, two clear cells over ceil(surface));
- every alcove cell is floored a half step down, and the flight leaves through it;
- nothing is placed where the world holds anything, and NOTHING under a waterfall column - a
  tread under falling water catches it and spreads it over the stair;
- the design is one piece with the world, and only the platform's own materials are used;
- the two arms are mirror images across the platform's centre column, as the platform is.
"""
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from mcbuild import nbt, schem

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "out", "friendisland.litematic")
WEST = os.path.join(ROOT, "out", "Friend Stair West.litematic")
EAST = os.path.join(ROOT, "out", "Friend Stair East.litematic")

needs_world = pytest.mark.skipif(not all(os.path.exists(p) for p in (CAP, WEST, EAST)),
                                 reason="needs out/friendisland.litematic and both stairs")

DECK = 199.0
PLATFORM_MATERIALS = {"spruce_slab", "stone_brick_slab", "spruce_log", "stone_bricks",
                      "wall_torch"}
SOFT = {"lantern", "torch", "wall_torch", "vine", "glow_lichen", "short_grass", "moss_carpet"}
NOT_ANCHOR = {"water", "lava", "vine", "bubble_column"}


def _cells(path):
    m = schem.load(path)
    sc = json.load(open(path.replace(".litematic", ".scan.json"), encoding="utf-8"))
    o = sc["origin"]
    out = {}
    for i, e in enumerate(m.palette):
        n = nbt.state_name(e).split(":")[-1]
        if n in ("air", "cave_air", "void_air"):
            continue
        pr = dict(nbt.state_props(e))
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            out[(int(x) + o["x"], int(y) + o["y"], int(z) + o["z"])] = (n, pr)
    return out, sc


@pytest.fixture(scope="module")
def world():
    return _cells(CAP)[0]


@pytest.fixture(scope="module", params=["west", "east"])
def stair(request):
    cells, sc = _cells(WEST if request.param == "west" else EAST)
    return request.param, cells, sc


def _surfaces(cells):
    """The audit's walking model: slabs 0.5 or 1.0, full blocks 1.0, soft things nothing."""
    surf = collections.defaultdict(list)
    occ = set()
    for (x, y, z), (n, pr) in cells.items():
        if n == "water":
            continue
        occ.add((x, y, z))
        if n in SOFT or n.endswith("_wall"):
            continue
        if n.endswith("_slab"):
            surf[(x, z)].append(y + (0.5 if pr.get("type") == "bottom" else 1.0))
        else:
            surf[(x, z)].append(y + 1.0)
    return surf, occ


def _walk(cells, start):
    surf, occ = _surfaces(cells)

    def head(x, z, h):
        b = math.ceil(h)
        return not any((x, b + k, z) in occ for k in (0, 1))

    seen = {start}
    q = collections.deque([start])
    while q:
        x, z, h = q.popleft()
        for h2 in surf.get((x, z), []):
            if 0 < h2 - h <= 0.5 and head(x, z, h2) and (x, z, h2) not in seen:
                seen.add((x, z, h2))
                q.append((x, z, h2))
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            for h2 in surf.get((nx, nz), []):
                if h2 - h > 0.5 or h - h2 > 0.5 or not head(nx, nz, h2):
                    continue
                k = (nx, nz, h2)
                if k not in seen:
                    seen.add(k)
                    q.append(k)
    return seen


@needs_world
def test_the_whole_stair_walks_from_the_pad_to_the_deck_in_context(stair, world):
    side, cells, sc = stair
    arm = sc["arms"][0]
    tx, tz = arm["tail"]
    comp = dict(world)
    comp.update(cells)
    # start on the bottom pad, wherever it is
    pad = [(x, z) for (x, y, z), (n, _) in cells.items() if n == "stone_bricks"
           and y + 1.0 == arm["pad_h"] and max(abs(x - tx), abs(z - tz)) > 1]
    assert pad, "no pad"
    seen = _walk(comp, (pad[0][0], pad[0][1], arm["pad_h"]))
    heights = {h for _, _, h in seen}
    assert DECK in heights, f"{side}: the walk from the pad never reaches the deck (max {max(heights)})"
    # ...and it reaches the deck THROUGH BOTH ALCOVES, not one
    for t in arm["twins"]:
        px, pz = t["post"]
        near = [(x, z) for (x, z, h) in seen if h == DECK - 0.5 and max(abs(x - px), abs(z - pz)) <= 3]
        assert len(near) >= 4, f"{side}: the alcove by post {t['post']} is not on the walk"


@needs_world
def test_every_alcove_cell_is_floored_a_half_step_down(stair):
    side, cells, sc = stair
    for t in sc["arms"][0]["twins"]:
        assert t["alcove_floor"] == 4, f"{side}: alcove by {t['post']} has {t['alcove_floor']} of 4 floor cells"


@needs_world
def test_nothing_is_placed_in_the_world_or_under_a_waterfall(stair, world):
    side, cells, _ = stair
    taken = set(cells) & set(world)
    assert not taken, f"{side}: {len(taken)} cells the world already holds, e.g. {sorted(taken)[:3]}"
    water_cols = {(x, z) for (x, y, z), (n, _) in world.items() if n == "water"}
    wet = [c for c in cells if (c[0], c[2]) in water_cols]
    assert not wet, f"{side}: {len(wet)} cells in a waterfall column, e.g. {wet[:3]}"


@needs_world
def test_it_is_one_piece_with_the_platform(stair, world):
    side, cells, _ = stair
    solid = {c for c, (n, _) in world.items() if n not in NOT_ANCHOR} | set(cells)
    start = next(iter(cells))
    seen = {start}
    q = [start]
    while q:
        x, y, z = q.pop()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    missing = set(cells) - seen
    assert not missing, f"{side}: {len(missing)} design cells not connected, e.g. {sorted(missing)[:3]}"


@needs_world
def test_only_the_platforms_own_materials(stair):
    side, cells, _ = stair
    used = {n for n, _ in cells.values()}
    assert used <= PLATFORM_MATERIALS, f"{side}: {used - PLATFORM_MATERIALS}"


@needs_world
def test_the_two_arms_mirror_across_the_platforms_centre_column():
    w, _ = _cells(WEST)
    e, _ = _cells(EAST)
    mirror = {(-44800 - x, y, z): v for (x, y, z), v in w.items()}
    # the east-north notch is missing three deck cells in the capture, so its outer frame is
    # not there to anchor against; allow that corner a handful of cells either way
    only_w = set(mirror) - set(e)
    only_e = set(e) - set(mirror)
    assert len(only_w) + len(only_e) <= 12, (len(only_w), len(only_e), sorted(only_w)[:4], sorted(only_e)[:4])


@needs_world
def test_the_twins_hand_off_at_one_height_into_a_whole_stone_landing(stair):
    side, cells, sc = stair
    arm = sc["arms"][0]
    a, b = arm["twins"]
    assert a["meet_h"] == b["meet_h"] == arm["meet_h"]
    assert arm["landing_h"] == arm["meet_h"] - 1.0
    tx, tz = arm["tail"]
    y = int(arm["landing_h"]) - 1
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            assert cells.get((tx + dx, y, tz + dz), ("", {}))[0] == "stone_bricks", (side, dx, dz)


@needs_world
def test_every_tread_has_the_audits_headroom_in_context(stair, world):
    side, cells, _ = stair
    comp = dict(world)
    comp.update(cells)
    # treads only: a post or a pier course is structure, and of course has structure over it
    treads = {c: v for c, v in cells.items() if v[0].endswith("_slab")}
    surf, occ = _surfaces(treads)
    bad = []
    for (x, z), hs in surf.items():
        for h in hs:
            b = math.ceil(h)
            if any((x, b + k, z) in comp and comp[(x, b + k, z)][0] != "water" for k in (0, 1)):
                bad.append((x, h, z))
    assert not bad, f"{side}: {len(bad)} treads with no headroom, e.g. {bad[:4]}"
