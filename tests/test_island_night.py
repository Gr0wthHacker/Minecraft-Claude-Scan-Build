"""The Island Night: the island-wide lighting pass holds only if the propagation says so.

Same contract as tests/test_lowland_glow.py and the same reason for existing: the design was
SOLVED - block light propagated through the assumed-final world, fixtures added until no
spawnable surface cell remained - so the test is that computation run again over the finished
design. If a fixture moves, or the world moves under it, this fails here rather than putting a
zombie on the ladybird at midnight.

The classifier is the load-bearing part and it is the one this project keeps getting wrong:
the surface is the TOPMOST standable cell in a column. Grading the LOWEST reports the buried
seams under the massif fill as floor and calls the island 72% dark; it has now misled three
separate passes, so it is asserted directly below.
"""
import collections
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import schem, scan                  # noqa: E402
from mcbuild import nightlight                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "out", "island_full.litematic")
NIGHT = os.path.join(ROOT, "out", "Island Night.work.json")
FALLS = os.path.join(ROOT, "out", "Falls.work.json")
FALLS_SIDE = os.path.join(ROOT, "out", "Falls.scan.json")

needs_world = pytest.mark.skipif(
    not (os.path.exists(FULL) and os.path.exists(NIGHT)),
    reason="needs the capture and the generated night pass")

Y_LO, Y_HI = 20, 215

# The sets and the classifier live in mcbuild/nightlight.py, imported by this test AND by the
# solver that produced the design. They were separate copies for one session and it cost three
# phantom dark cells: the solver's set held `dead_bush` and this one did not, so the two were
# grading different islands. One source, so two tools cannot drift.


@pytest.fixture(scope="module")
def world():
    """The capture with every design this pass assumed final laid over it: the Falls (whose
    cut opens new air and whose water is not spawnable) and the night pass itself."""
    cap = schem.load(FULL)
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    ox, oy, oz = o["x"], o["y"], o["z"]
    pal = [n.split(":")[-1] for n in cap.names]

    NY = Y_HI - Y_LO + 1
    NZ, NX = cap.ids.shape[1], cap.ids.shape[2]
    name = np.empty((NY, NZ, NX), dtype=object)
    for y in range(Y_LO, Y_HI + 1):
        rows = cap.ids[y - oy]
        for z in range(NZ):
            for x in range(NX):
                name[y - Y_LO, z, x] = pal[rows[z, x]]

    def place(path):
        if not os.path.exists(path):
            return
        for x, y, z, b in json.load(open(path, encoding="utf-8"))["cells"]:
            if Y_LO <= y <= Y_HI and 0 <= z - oz < NZ and 0 <= x - ox < NX:
                name[y - Y_LO, z - oz, x - ox] = b

    # the dig FIRST, then the blocks: a froglight is flush, so its own cell is on the dig list
    # and re-filling it in the wrong order would leave the turf standing over the light
    for side, in ((FALLS_SIDE,),):
        if os.path.exists(side):
            for x, y, z in (json.load(open(side, encoding="utf-8")).get("dig") or []):
                if Y_LO <= y <= Y_HI and 0 <= z - oz < NZ and 0 <= x - ox < NX:
                    name[y - Y_LO, z - oz, x - ox] = "air"
    place(FALLS)
    place(NIGHT)
    return name, (ox, oy, oz)


def _tables(name):
    """Palette-free: the fixture holds block-state STRINGS per cell, so classify a de-duplicated
    palette of them and index back."""
    flat = name.reshape(-1)
    states = sorted(set(flat.tolist()))
    ix = {st: i for i, st in enumerate(states)}
    ids = np.array([ix[st] for st in flat], dtype=np.int32).reshape(name.shape)
    opaque, emit, passy, spawn, water = nightlight.classify(states)
    return opaque[ids], emit[ids], passy[ids], spawn[ids], water[ids]


_propagate = nightlight.propagate
_surface = nightlight.surface


@needs_world
def test_zero_spawnable_surface_cells(world):
    name, (ox, oy, oz) = world
    opaque, emit, passy, spawn, water = _tables(name)
    light = _propagate(opaque, emit)
    dark = [c for c in _surface(passy, spawn, water)
            if light[c[1], c[2], c[0]] == 0]
    shown = [(c[0] + ox, c[1] + Y_LO, c[2] + oz) for c in dark[:10]]
    assert not dark, f"{len(dark)} spawnable surface cells, first: {shown}"


@needs_world
def test_the_surface_is_the_topmost_standable_not_the_lowest(world):
    """The classifier that has misled this project three times. Reading the LOWEST standable
    cell grades the buried seams under the massif fill as floor; the two answers must differ
    by a lot, or the test above is measuring the wrong island."""
    name, _ = world
    _, _, passy, spawn, water = _tables(name)
    top = _surface(passy, spawn, water)
    NY, NZ, NX = passy.shape
    low = {}
    for z in range(NZ):
        for x in range(NX):
            for iy in np.nonzero(spawn[:, z, x])[0]:
                if iy + 2 < NY and passy[iy + 1, z, x] and passy[iy + 2, z, x] \
                        and not water[iy + 1, z, x]:
                    low[(x, iy + 1, z)] = True
                    break
    assert len(top) > 3000, f"only {len(top)} walkable cells - the surface scan is broken"
    # Counting COLUMNS makes these trivially equal: every column with a topmost hit has a
    # lowest one too, which is why the first version of this assertion passed vacuously at
    # 6838 < 6838. What separates the two scans is WHICH CELL, so compare positions.
    assert len(top) == len(low), "one scan found columns the other did not"
    differ = sum(1 for c in top if c not in low)
    assert differ > 200, (f"only {differ} columns differ between topmost and lowest standable"
                          " - on an island with a hollow belly, a deck under a plate and a"
                          " lowland under that, they should differ a great deal, so the"
                          " surface scan is probably not doing what it claims")


@needs_world
def test_nothing_lands_on_an_animal_but_lichen(world):
    """The lowland glow's rule, kept island-wide: a coat may take a lichen and nothing else.
    A lantern or a froglight on the owl or the ladybird would be a hole punched in a
    sculpture - and the froglight is the dangerous one, because it REPLACES what it sits in."""
    cells = json.load(open(NIGHT, encoding="utf-8"))["cells"]
    cap = schem.load(FULL)
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    pal = [n.split(":")[-1].split("[")[0] for n in cap.names]
    wools = {c + "_wool" for c in ("white", "orange", "magenta", "light_blue", "yellow",
                                   "lime", "pink", "gray", "light_gray", "cyan", "purple",
                                   "blue", "brown", "green", "red", "black")}
    coats = wools | {"bone_block"}
    for x, y, z, b in cells:
        iy, iz, ix = y - o["y"], z - o["z"], x - o["x"]
        if not (0 <= iy < cap.ids.shape[0] and 0 <= iz < cap.ids.shape[1]
                and 0 <= ix < cap.ids.shape[2]):
            continue
        here = pal[cap.ids[iy, iz, ix]]
        below = pal[cap.ids[iy - 1, iz, ix]] if iy > 0 else "air"
        block = b.split("[")[0]
        if here in coats:
            assert block == "glow_lichen", f"{block} REPLACES a coat block at {(x, y, z)}"
        if below in coats:
            assert block == "glow_lichen", f"{block} stands on a coat block at {(x, y, z)}"


@needs_world
def test_a_flush_froglight_replaces_real_turf_and_is_on_the_dig_list(world):
    """Flush means the turf goes first. A froglight emitted without its cell on the dig list
    is a light buried under the block it was meant to become."""
    side = json.load(open(os.path.join(ROOT, "out", "Island Night.scan.json"), encoding="utf-8"))
    dig = {tuple(c) for c in (side.get("dig") or [])}
    cells = json.load(open(NIGHT, encoding="utf-8"))["cells"]
    frog = [(x, y, z) for x, y, z, b in cells if b.split("[")[0] == "ochre_froglight"]
    assert frog, "no froglights at all?"
    for c in frog:
        assert c in dig, f"froglight at {c} is not on the dig list"

    cap = schem.load(FULL)
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    pal = [n.split(":")[-1].split("[")[0] for n in cap.names]
    for (x, y, z) in frog:
        here = pal[cap.ids[y - o["y"], z - o["z"], x - o["x"]]]
        assert here not in ("air", "cave_air"), f"froglight at {(x, y, z)} replaces nothing"


@needs_world
def test_the_underworld_is_lit_cold_and_the_island_warm(world):
    """The gradient is the point, and it is the one thing here a propagation cannot check:
    warm lanterns and froglights above the waterline, soul flame below it."""
    cells = json.load(open(NIGHT, encoding="utf-8"))["cells"]
    by = collections.Counter()
    for x, y, z, b in cells:
        by[(b.split("[")[0], "low" if y < 100 else "high")] += 1
    assert by[("soul_lantern", "high")] == 0, "soul flame above the waterline breaks the gradient"
    assert by[("lantern", "low")] == 0, "a warm lantern in the underworld breaks the gradient"
    assert by[("soul_lantern", "low")] > 10, "the underworld should carry the cold light"
