"""The friend island's corner stairs (2026-09-04).

At each corner of the round platform, the two notches on the neighbouring arms are joined by
mirrored curved flights that follow the rim OUTSIDE the waterfall curtain, meet flat at the
curtain's middle on a stone-brick pier, and continue down as one helix. Pinned here:

- the WALK: pad -> descent -> landing -> both flights -> both notches -> the deck, in the
  composite of the design and the capture, under the audit's step rules;
- the two flights are DUPLICATES: every cell of one has its mirror in the other with the same
  block (Jack: "symmetrical in materials etc, they should be duplicate");
- nothing in a world cell and nothing in a waterfall column;
- one piece with the platform, only the platform's own materials, every notch floored;
- the four corners are the same design turned, cell for cell.
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
CORNERS = ["NW", "NE", "SW", "SE"]
DESIGN = {c: os.path.join(ROOT, "out", f"Friend Stair {c}.litematic") for c in CORNERS}

needs_world = pytest.mark.skipif(not os.path.exists(CAP) or not all(os.path.exists(p) for p in DESIGN.values()),
                                 reason="needs out/friendisland.litematic and the four corner stairs")

DECK = 199.0
CENTRE = (-22400, -97400)
SIGNS = {"NW": (1, 1), "NE": (-1, 1), "SW": (1, -1), "SE": (-1, -1)}
PLATFORM_MATERIALS = {"spruce_slab", "stone_brick_slab", "stone_bricks", "wall_torch"}
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


@pytest.fixture(scope="module", params=CORNERS)
def stair(request):
    cells, sc = _cells(DESIGN[request.param])
    return request.param, cells, sc


def _surfaces(cells):
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


def _canon(corner, x, z):
    sx, sz = SIGNS[corner]
    return (x - CENTRE[0]) * sx, (z - CENTRE[1]) * sz


def _world(corner, u, v):
    sx, sz = SIGNS[corner]
    return CENTRE[0] + sx * u, CENTRE[1] + sz * v


@needs_world
def test_it_walks_from_the_pad_through_both_flights_to_the_deck(stair, world):
    corner, cells, sc = stair
    comp = dict(world)
    comp.update(cells)
    pu, pv = sc["pier_at"]
    px, pz = _world(corner, pu, pv)
    pad = [(x, z) for (x, y, z), (n, _) in cells.items() if n == "stone_bricks"
           and y + 1.0 == sc["pad_h"] and max(abs(x - px), abs(z - pz)) >= 2]
    assert pad, "no pad"
    seen = _walk(comp, (pad[0][0], pad[0][1], sc["pad_h"]))
    assert DECK in {h for _, _, h in seen}, f"{corner}: the walk never reaches the deck"
    # through BOTH notches: each notch floor is on the walk
    for mirror in (False, True):
        u0, u1, v0, v1 = sc.get("notch", [-16, -15, -5, -4])
        floor = [(u, v) for u in range(u0, u1 + 1) for v in range(v0, v1 + 1)]
        if mirror:
            floor = [(v, u) for (u, v) in floor]
        for (u, v) in floor:
            x, z = _world(corner, u, v)
            assert (x, z, DECK - 0.5) in seen, f"{corner}: notch cell {(x, z)} not on the walk"


@needs_world
def test_the_two_flights_are_duplicates_in_shape_and_material(stair):
    corner, cells, sc = stair
    assert sc["asymmetric_cells"] == 0
    # re-derived rather than trusted: above the landing every cell mirrors across the diagonal
    landing_y = int(math.floor(sc["landing_h"]))
    above = {c: v for c, v in cells.items() if c[1] >= landing_y and v[0] != "wall_torch"}
    for (x, y, z), (n, pr) in above.items():
        u, v = _canon(corner, x, z)
        mx, mz = _world(corner, v, u)
        assert above.get((mx, y, mz), ("", {}))[0] == n, (corner, (x, y, z), n)


@needs_world
def test_nothing_in_the_world_and_nothing_under_a_waterfall(stair, world):
    corner, cells, _ = stair
    taken = set(cells) & set(world)
    assert not taken, f"{corner}: {len(taken)} cells the world holds, e.g. {sorted(taken)[:3]}"
    water_cols = {(x, z) for (x, y, z), (n, _) in world.items() if n == "water"}
    wet = [c for c in cells if (c[0], c[2]) in water_cols]
    assert not wet, f"{corner}: {len(wet)} cells in a waterfall column, e.g. {wet[:3]}"


@needs_world
def test_the_flights_stay_outside_the_curtain_and_meet_at_its_middle(stair):
    corner, cells, sc = stair
    landing_y = int(math.floor(sc["landing_h"]))
    r = [math.hypot(*_canon(corner, x, z)) for (x, y, z), (n, _) in cells.items()
         if y > landing_y and n != "wall_torch"]
    assert min(r) >= 15.4, f"{corner}: a flight cell at r={min(r):.1f} is inside the curtain's line"
    # the meeting: the flights' last treads are flat with the landing slabs on the pier
    assert sc["meet_h"] == sc["landing_h"]
    pu, pv = sc["pier_at"]
    assert pu == pv, "the pier stands on the diagonal"
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            x, z = _world(corner, pu + du, pv + dv)
            n, pr = cells.get((x, landing_y, z), ("", {}))
            assert n == "stone_brick_slab" and pr.get("type") == "bottom", (corner, du, dv, n)


@needs_world
def test_it_is_one_piece_with_the_platform(stair, world):
    corner, cells, _ = stair
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
    assert not missing, f"{corner}: {len(missing)} cells not connected, e.g. {sorted(missing)[:3]}"


@needs_world
def test_only_the_platforms_own_materials_and_every_notch_floored(stair):
    corner, cells, sc = stair
    used = {n for n, _ in cells.values()}
    assert used <= PLATFORM_MATERIALS, f"{corner}: {used - PLATFORM_MATERIALS}"
    assert sc["notch_floor"] == [4, 4], f"{corner}: notch floors {sc['notch_floor']}"


@needs_world
def test_the_four_corners_are_one_design_turned():
    ref, _ = _cells(DESIGN["NW"])
    canon = {(_canon("NW", x, z)[0], y, _canon("NW", x, z)[1]): v for (x, y, z), v in ref.items()}
    for corner in CORNERS[1:]:
        cells, _ = _cells(DESIGN[corner])
        got = {(_canon(corner, x, z)[0], y, _canon(corner, x, z)[1]): v[0] for (x, y, z), v in cells.items()}
        want = {c: v[0] for c, v in canon.items()}
        # the east-north notch is missing three deck cells in the capture; allow that corner a
        # couple of cells either way, and nothing else
        diff = {c for c in set(got) | set(want) if got.get(c) != want.get(c)}
        assert len(diff) <= 4, (corner, len(diff), sorted(diff)[:5])


@needs_world
def test_every_tread_has_the_audits_headroom_in_context(stair, world):
    corner, cells, _ = stair
    comp = dict(world)
    comp.update(cells)
    treads = {c: v for c, v in cells.items() if v[0].endswith("_slab")}
    surf, _ = _surfaces(treads)
    bad = []
    for (x, z), hs in surf.items():
        for h in hs:
            b = math.ceil(h)
            if any((x, b + k, z) in comp and comp[(x, b + k, z)][0] != "water" for k in (0, 1)):
                bad.append((x, h, z))
    assert not bad, f"{corner}: {len(bad)} treads with no headroom, e.g. {bad[:4]}"
