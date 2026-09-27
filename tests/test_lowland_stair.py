"""The lowland stair, the reaching root, and the well (2026-08-22).

The stair screws straight down the taproot's own axis - Jack's alignment call - through a
WELL dug in the shop islet's floor. Three contracts pinned here, each of which shipped wrong
or nearly wrong once:

- the COMPOSITE walk (stair + carved islet + old Root Stair + capture-minus-dig) runs from
  the lowland moss to the islet shelf with the audit's own step rules. The isolated climb
  gate cannot pass by construction and is off in the config; this is what replaces it.
- the DIG list touches only the islet's floor (Y >= 140), only natural rock, and never a
  protected block or the cell one stands on - the shop's barrels sit one course over the
  well's north arc.
- the stair never REPLACES standing masonry outside its own dig list.
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
from mcbuild.gen.protect import is_protected

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "out", "island_full.litematic")
STAIR = os.path.join(ROOT, "out", "Lowland Stair.litematic")
RROOT = os.path.join(ROOT, "out", "Lowland Root.litematic")
ISLET = os.path.join(ROOT, "out", "Shop Islet.litematic")
OLD = os.path.join(ROOT, "out", "Root Stair.litematic")

needs_world = pytest.mark.skipif(
    not all(os.path.exists(p) for p in (FULL, STAIR, RROOT, ISLET, OLD)),
    reason="needs the generated designs and out/island_full.litematic")

PASS = {"air", "cave_air", "vine", "moss_carpet", "tall_grass", "fern", "large_fern",
        "azalea", "flowering_azalea", "glow_lichen", "hanging_roots", "small_dripleaf",
        "big_dripleaf", "spore_blossom", "short_grass", "lantern", "soul_lantern"}
SOFT = {"lantern", "soul_lantern", "torch", "wall_torch", "vine", "glow_lichen",
        "short_grass", "moss_carpet", "tall_grass", "fern", "large_fern", "azalea",
        "flowering_azalea", "hanging_roots"}


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


def _dig():
    w = json.load(open(STAIR.replace(".litematic", ".work.json"), encoding="utf-8"))
    return {tuple(d) for d in w.get("dig", [])}


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
def world():
    return {"stair": _design(STAIR), "islet": _design(ISLET), "root": _design(RROOT),
            "old": _design(OLD), "dig": _dig(), "cap": schem.load(FULL)}


@pytest.fixture(scope="module")
def walk(world):
    stair, islet, rroot, old, dig = (world["stair"], world["islet"], world["root"],
                                     world["old"], world["dig"])
    cap = world["cap"]
    cox, coy, coz = -24251, -64, 29949
    cpal = [n.split(":")[-1] for n in cap.names]
    X0, X1, Z0, Z1, Y0, Y1 = -24214, -24186, 30004, 30032, 34, 162
    env = set(dig)
    for (x, y, z), (n, _pr) in stair.items():
        if "slab" in n:
            for k in range(4):
                env.add((x, y + k, z))
    surf = collections.defaultdict(list)
    occ = set()
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            for y in range(Y0, Y1 + 1):
                full = cpal[cap.ids[y - coy, z - coz, x - cox]]
                n = full.split("[")[0]
                if n in PASS or (x, y, z) in dig or (x, y, z) in stair:
                    continue
                pr = {"type": "bottom"} if (n.endswith("_slab") and "type=bottom" in full) \
                    else {}
                _add(surf, occ, x, y, z, n, pr)
    for src, carved in ((islet, True), (rroot, False), (old, False)):
        for (x, y, z), (n, pr) in src.items():
            if not (X0 <= x <= X1 and Z0 <= z <= Z1 and Y0 <= y <= Y1):
                continue
            if (x, y, z) in stair or (carved and (x, y, z) in env):
                continue
            _add(surf, occ, x, y, z, n.split("[")[0], pr)
    for (x, y, z), (n, pr) in stair.items():
        _add(surf, occ, x, y, z, n.split("[")[0], pr)

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
    return seen


@needs_world
def test_the_composite_walk_reaches_the_shelf(walk):
    assert max(h for _, _, h in walk) >= 150.5, "the stair no longer reaches the islet shelf"


@needs_world
def test_the_composite_walk_reaches_the_lowland_moss(walk):
    assert sum(1 for c in walk if c[2] <= 42) >= 50, \
        "you cannot walk off the bottom of the stair onto the lowland"


@needs_world
def test_the_stair_shares_the_actual_stairs_axis(world):
    """Jack's alignment call, pinned: both helices turn about the taproot's own line."""
    import yaml
    new = yaml.safe_load(open(os.path.join(ROOT, "configs", "lowland_stair.yaml")))
    old = yaml.safe_load(open(os.path.join(ROOT, "configs", "root_stair.yaml")))
    assert new["params"]["center"] == old["params"]["center"]
    assert new["params"]["direction"] == old["params"]["direction"]


@needs_world
def test_the_dig_takes_only_the_islet_floor_and_only_rock(world):
    cap = world["cap"]
    cox, coy, coz = -24251, -64, 29949
    cpal = [n.split(":")[-1].split("[")[0] for n in cap.names]

    def cap_at(x, y, z):
        return cpal[cap.ids[y - coy, z - coz, x - cox]]

    assert world["dig"], "no dig list - the well is gone"
    for (x, y, z) in world["dig"]:
        assert y >= 140, ("dig below the islet", x, y, z)
        n = cap_at(x, y, z)
        assert not is_protected(n), ("dug a protected block", x, y, z, n)
        above = cap_at(x, y + 1, z)
        assert not is_protected(above), \
            ("dug the floor under a protected block", x, y, z, above)


@needs_world
def test_the_stair_replaces_nothing_outside_its_dig(world):
    cap = world["cap"]
    cox, coy, coz = -24251, -64, 29949
    cpal = [n.split(":")[-1].split("[")[0] for n in cap.names]
    own = {"stone_brick_slab", "mossy_stone_brick_slab", "deepslate_brick_slab",
           "cobbled_deepslate_slab", "polished_blackstone_brick_slab", "blackstone_slab",
           "stone_brick_wall", "deepslate_brick_wall", "polished_blackstone_brick_wall",
           "lantern", "soul_lantern"}
    for (x, y, z), (dn, _pr) in world["stair"].items():
        n = cpal[cap.ids[y - coy, z - coz, x - cox]]
        if n in PASS or n == dn.split("[")[0] or n in own:
            continue   # empty, built as designed, or built in a neighbouring band's stone -
                       # Jack substituted on 22 cells and mismatches are accepted
        assert (x, y, z) in world["dig"], ("tread replaces standing world", x, y, z, n)


@needs_world
def test_the_old_stair_is_never_dug(world):
    hits = world["dig"] & set(world["old"])
    assert not hits, sorted(hits)[:5]


@needs_world
def test_the_treads_are_slabs_and_nothing_else(world):
    for (x, y, z), (n, pr) in world["stair"].items():
        base = n.split("[")[0]
        assert base.endswith(("_slab", "_wall")) or base in ("lantern", "soul_lantern"), \
            (x, y, z, n)


@needs_world
def test_the_root_is_one_braid_from_the_keel(world):
    wood = {c for c, (n, _p) in world["root"].items() if n.startswith(("oak", "moss"))}
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
    assert len(comps[0]) >= len(wood) - 4, sorted(len(c) for c in comps)


@needs_world
def test_the_root_ends_at_the_transition_not_the_ground(world):
    tip = min(y for (x, y, z) in world["root"])
    assert 78 <= tip <= 114, tip
    per = collections.Counter(y for (x, y, z) in world["root"])
    body = sum(per[y] for y in range(130, 140)) / 10.0
    tail = sum(per[y] for y in range(tip, tip + 5)) / 5.0
    assert tail < body, (tail, body)


@needs_world
def test_the_rail_carries_its_lanterns(world):
    lanterns = [c for c, (n, _p) in world["stair"].items()
                if n.split("[")[0] in ("lantern", "soul_lantern")]
    assert len(lanterns) >= 20
    for (x, y, z) in lanterns:
        assert (x, y - 1, z) in world["stair"], ("lantern off its rail", x, y, z)


@needs_world
def test_the_stone_darkens_and_the_light_goes_cold_on_the_way_down(world):
    stair = world["stair"]

    def mean_y(prefix):
        ys = [y for (x, y, z), (n, _p) in stair.items() if n.startswith(prefix)]
        return sum(ys) / len(ys) if ys else None

    stone = mean_y("stone_brick_slab")
    deep = mean_y("deepslate_brick_slab")
    black = mean_y("polished_blackstone_brick_slab")
    assert stone is not None and deep is not None and black is not None
    assert stone > deep > black, (stone, deep, black)
    warm = [y for (x, y, z), (n, _p) in stair.items() if n.split("[")[0] == "lantern"]
    cold = [y for (x, y, z), (n, _p) in stair.items() if n.split("[")[0] == "soul_lantern"]
    assert warm and cold
    assert sum(warm) / len(warm) > sum(cold) / len(cold)


@needs_world
def test_the_carved_islet_keeps_out_of_the_well(world):
    """The shop islet design yields the stair's envelope - re-carve after regenerating it."""
    env = set(world["dig"])
    for (x, y, z), (n, _pr) in world["stair"].items():
        if "slab" in n:
            for k in range(4):
                env.add((x, y + k, z))
    hits = env & set(world["islet"])
    assert not hits, sorted(hits)[:5]
