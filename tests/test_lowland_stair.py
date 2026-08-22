"""The lowland stair and the reaching root (2026-08-22).

The one that matters is the COMPOSITE walk: the stair's top courses terminate against the
shop islet's DESIGNED rock - burial is free, the ruinring's rule - so the isolated climb
gate cannot pass by construction and is off in the config. What replaces it is here: build
the surface map of stair + shop islet design + capture and walk it, lowland moss to shelf,
with the audit's own step rules (0.5 up, 3.5 down, two clear above the head). If either
design or the capture moves and the walk breaks, this fails - which is the point.
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
FULL = os.path.join(ROOT, "out", "island_full.litematic")
STAIR = os.path.join(ROOT, "out", "Lowland Stair.litematic")
RROOT = os.path.join(ROOT, "out", "Lowland Root.litematic")
ISLET = os.path.join(ROOT, "out", "Shop Islet.litematic")

needs_world = pytest.mark.skipif(
    not all(os.path.exists(p) for p in (FULL, STAIR, RROOT, ISLET)),
    reason="needs the generated designs and out/island_full.litematic")

PASS = {"air", "cave_air", "vine", "moss_carpet", "tall_grass", "fern", "large_fern",
        "azalea", "flowering_azalea", "glow_lichen", "hanging_roots", "small_dripleaf",
        "big_dripleaf", "spore_blossom", "short_grass", "lantern", "soul_lantern"}
SOFT = {"lantern", "torch", "wall_torch", "vine", "glow_lichen", "short_grass",
        "moss_carpet", "tall_grass", "fern", "large_fern", "azalea", "flowering_azalea",
        "hanging_roots"}


def _design(path):
    m = schem.load(path)
    sc = json.load(open(path.replace(".litematic", ".scan.json"), encoding="utf-8"))
    o = sc.get("world_origin") or sc.get("origin")
    out = {}
    for i, e in enumerate(m.palette):
        n = nbt.state_name(e).split(":")[-1]
        if n in ("air", "cave_air"):
            continue
        pr = dict(nbt.state_props(e))
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            out[(int(x) + o["x"], int(y) + o["y"], int(z) + o["z"])] = (n, pr)
    return out


def _add(surf, occ, x, y, z, n, pr):
    occ.add((x, y, z))
    if n in SOFT or n.endswith("_wall"):
        return
    if n.endswith("_slab"):
        surf[(x, z)].append(y + (0.5 if (pr or {}).get("type") == "bottom" else 1.0))
    elif n.endswith("_stairs"):
        surf[(x, z)] += [y + 0.5, y + 1.0]
    else:
        surf[(x, z)].append(y + 1.0)


@pytest.fixture(scope="module")
def walk():
    stair = _design(STAIR)
    islet = _design(ISLET)
    rroot = _design(RROOT)
    cap = schem.load(FULL)
    cox, coy, coz = -24251, -64, 29949
    cpal = [n.split(":")[-1] for n in cap.names]
    X0, X1, Z0, Z1, Y0, Y1 = -24222, -24190, 30012, 30044, 34, 156
    surf = collections.defaultdict(list)
    occ = set()
    for src in (stair, islet, rroot):
        for (x, y, z), (n, pr) in src.items():
            if X0 <= x <= X1 and Z0 <= z <= Z1 and Y0 <= y <= Y1:
                _add(surf, occ, x, y, z, n.split("[")[0], pr)
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            for y in range(Y0, Y1 + 1):
                full = cpal[cap.ids[y - coy, z - coz, x - cox]]
                n = full.split("[")[0]
                if n in PASS:
                    continue
                pr = {"type": "bottom"} if (n.endswith("_slab") and "type=bottom" in full) \
                    else {}
                _add(surf, occ, x, y, z, n, pr)

    def head(x, z, h):
        b = math.ceil(h)
        return not any((x, b + k, z) in occ for k in (0, 1))

    treads = [(x, y, z, pr) for (x, y, z), (n, pr) in stair.items() if "slab" in n]
    sy = min(t[1] for t in treads)
    x0, y0, z0, pr0 = [t for t in treads if t[1] == sy][0]
    start = (x0, z0, y0 + (0.5 if pr0.get("type") == "bottom" else 1.0))
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
                if h2 - h > 0.5 or h - h2 > 3.5 or not head(nx, nz, h2):
                    continue
                k = (nx, nz, h2)
                if k not in seen:
                    seen.add(k)
                    q.append(k)
    return stair, rroot, seen


@needs_world
def test_the_composite_walk_reaches_the_shelf(walk):
    _stair, _root, seen = walk
    assert max(h for _, _, h in seen) >= 150.5, \
        "the stair no longer reaches the islet shelf"


@needs_world
def test_the_composite_walk_reaches_the_lowland_moss(walk):
    _stair, _root, seen = walk
    assert sum(1 for c in seen if c[2] <= 42) >= 50, \
        "you cannot walk off the bottom of the stair onto the lowland"


@needs_world
def test_the_treads_are_slabs_and_nothing_else(walk):
    stair, _root, _seen = walk
    for (x, y, z), (n, pr) in stair.items():
        base = n.split("[")[0]
        assert base.endswith(("_slab", "_wall")) or base == "lantern", (x, y, z, n)


@needs_world
def test_the_stair_clears_the_harbor_ensemble(walk):
    """The siting decision, pinned: no tread inside the harbor light's box, the watergate's
    box, or the quay lip's diagonal."""
    stair, _root, _seen = walk
    boxes = [(-24206, -24202, 30016, 30020),   # harbor light plinth and gallery
             (-24201, -24195, 30008, 30015)]   # watergate
    for (x, y, z) in stair:
        for (a, b, c, d) in boxes:
            assert not (a <= x <= b and c <= z <= d), (x, y, z)


@needs_world
def test_the_root_is_one_braid(walk):
    _stair, rroot, _seen = walk
    wood = {c for c, (n, _p) in rroot.items() if n.startswith(("oak", "moss"))}
    todo = set(wood)
    comps = []
    while todo:
        s = todo.pop()
        comp, q = {s}, collections.deque([s])
        while q:
            x, y, z = q.popleft()
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (x + d[0], y + d[1], z + d[2])
                if nb in todo:
                    todo.remove(nb)
                    comp.add(nb)
                    q.append(nb)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    # the main braid, plus at most two toe-tips surfacing from the moss on their own
    assert len(comps[0]) >= len(wood) - 4, sorted(len(c) for c in comps)


@needs_world
def test_the_rail_carries_its_lanterns(walk):
    stair, _root, _seen = walk
    lanterns = [c for c, (n, _p) in stair.items() if n.split("[")[0] == "lantern"]
    assert len(lanterns) >= 20
    for (x, y, z) in lanterns:
        assert (x, y - 1, z) in stair, ("lantern off its rail", x, y, z)
