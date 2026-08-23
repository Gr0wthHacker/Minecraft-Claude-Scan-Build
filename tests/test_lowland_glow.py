"""The Lowland Glow: the lighting pass holds only if the propagation says so.

The design was SOLVED - block light propagated through the assumed-final composite, fixtures
added until zero spawnable surface cells remained - so the test is the same computation run
over the finished designs. If any design moves and opens a dark cell, this fails before a
player meets the zombie that would have told them.
"""
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from mcbuild import blocks, nbt, schem

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "out", "island_full.litematic")
GLOW = os.path.join(ROOT, "out", "Lowland Glow.litematic")

needs_world = pytest.mark.skipif(not (os.path.exists(FULL) and os.path.exists(GLOW)),
                                 reason="needs the capture and the generated glow")

X0, X1, Z0, Z1, Y0, Y1 = -24251, -24149, 29949, 30051, 30, 90
PASSY = {"air", "cave_air", "vine", "moss_carpet", "short_grass", "tall_grass", "fern",
         "large_fern", "azalea", "flowering_azalea", "glow_lichen", "hanging_roots",
         "small_dripleaf", "big_dripleaf", "spore_blossom", "poppy", "dandelion"}
EMIT = {"lantern": 15, "soul_lantern": 10, "glow_lichen": 7, "amethyst_cluster": 5,
        "ochre_froglight": 15, "sea_pickle": 6, "torch": 14, "wall_torch": 14,
        "soul_campfire": 10}
# every design the composite assumes final - the tracked set plus the placed-by-name pair
DESIGNS = ["Lowland", "Lowland Bat", "Lowland Portal", "Lowland Ruinway", "Lowland Sanctum",
           "Lowland Axolotl", "Lowland Hamlet", "Lowland Campanile", "Lowland Turtle",
           "Lowland Root", "Lowland Stair", "Castle Bridge", "Shop Islet", "Lowland Glow"]


@pytest.fixture(scope="module")
def composite():
    cap = schem.load(FULL)
    cox, coy, coz = -24251, -64, 29949
    cpal = [n.split(":")[-1] for n in cap.names]
    NX, NZ, NY = X1 - X0 + 1, Z1 - Z0 + 1, Y1 - Y0 + 1
    name = np.empty((NY, NZ, NX), dtype=object)
    for y in range(Y0, Y1 + 1):
        for z in range(Z0, Z1 + 1):
            row = cap.ids[y - coy, z - coz, X0 - cox:X1 - cox + 1]
            for i, v in enumerate(row):
                name[y - Y0, z - Z0, i] = cpal[v]
    dig = set()
    for d in DESIGNS:
        path = os.path.join(ROOT, "out", f"{d}.work.json")
        if not os.path.exists(path):
            continue
        w = json.load(open(path, encoding="utf-8"))
        dig |= {tuple(c) for c in w.get("dig", [])}
        for x, y, z, b in w["cells"]:
            if X0 <= x <= X1 and Z0 <= z <= Z1 and Y0 <= y <= Y1:
                cur = name[y - Y0, z - Z0, x - X0].split("[")[0]
                # standing WATER is never displaced: the pond stays the open harbor Jack
                # built (the ground's frozen-pond scheme is an accepted mismatch, and
                # overlaying its ice here once shadowed the axolotl's fin into a false
                # dark). Only the glow's own pickles enter water.
                if cur in PASSY or (x, y, z) in dig or d == "Lowland Glow":
                    name[y - Y0, z - Z0, x - X0] = b
    # a dug cell no design refilled is air once the player digs it
    filled = set()
    for d in DESIGNS:
        path = os.path.join(ROOT, "out", f"{d}.work.json")
        if os.path.exists(path):
            filled |= {(x, y, z) for x, y, z, _b in
                       json.load(open(path, encoding="utf-8"))["cells"]}
    for (x, y, z) in dig - filled:
        if X0 <= x <= X1 and Z0 <= z <= Z1 and Y0 <= y <= Y1:
            name[y - Y0, z - Z0, x - X0] = "air"
    return name


def _full(cache, b):
    if b not in cache:
        try:
            cache[b] = blocks.is_full_cube(b)
        except Exception:
            cache[b] = False
    return cache[b]


@needs_world
def test_zero_spawnable_surface_cells(composite):
    name = composite
    NY, NZ, NX = name.shape
    cache = {}
    opaque = np.zeros(name.shape, bool)
    emit = np.zeros(name.shape, np.int8)
    for idx in np.ndindex(name.shape):
        b = name[idx].split("[")[0]
        if b in ("air", "cave_air"):
            continue
        e = EMIT.get(b, 0)
        if e:
            emit[idx] = e
        elif _full(cache, b):
            opaque[idx] = True
    light = np.zeros(name.shape, np.int8)
    q = collections.deque()
    ys, zs, xs = np.nonzero(emit)
    for y, z, x in zip(ys, zs, xs):
        light[y, z, x] = emit[y, z, x]
        q.append((y, z, x))
    while q:
        y, z, x = q.popleft()
        lv = light[y, z, x] - 1
        if lv <= 0:
            continue
        for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                           (0, 0, 1), (0, 0, -1)):
            ny, nz, nx = y + dy, z + dz, x + dx
            if not (0 <= ny < NY and 0 <= nz < NZ and 0 <= nx < NX) or opaque[ny, nz, nx]:
                continue
            if light[ny, nz, nx] < lv:
                light[ny, nz, nx] = lv
                q.append((ny, nz, nx))
    dark = []
    for z in range(NZ):
        for x in range(NX):
            for y in range(min(NY - 2, 45), 0, -1):
                st = name[y - 1, z, x]
                b = st.split("[")[0]
                if b in PASSY or b in ("water", "air"):
                    continue
                spawn = ("type=top" in st or "type=double" in st) if b.endswith("_slab") \
                    else _full(cache, b)
                if spawn and name[y, z, x].split("[")[0] in PASSY \
                        and name[y + 1, z, x].split("[")[0] in PASSY \
                        and int(light[y, z, x]) == 0:
                    dark.append((X0 + x, Y0 + y, Z0 + z, b))
                break
    assert not dark, f"{len(dark)} spawnable surface cells, first: {dark[:8]}"


@needs_world
def test_nothing_lands_on_an_animal_but_lichen(composite):
    """The axolotl glows because a lush cave grows light on what stands still - and that is
    the ONLY thing this design may put on an animal."""
    glow = json.load(open(os.path.join(ROOT, "out", "Lowland Glow.work.json"),
                          encoding="utf-8"))
    cap = schem.load(FULL)
    cox, coy, coz = -24251, -64, 29949
    cpal = [n.split(":")[-1].split("[")[0] for n in cap.names]
    for x, y, z, b in glow["cells"]:
        below = cpal[cap.ids[y - 1 - coy, z - coz, x - cox]]
        if below.endswith("_wool"):
            assert b.split("[")[0] == "glow_lichen", (x, y, z, b, below)


@needs_world
def test_the_pickles_are_in_the_water_and_the_frog_is_flush(composite):
    glow = json.load(open(os.path.join(ROOT, "out", "Lowland Glow.work.json"),
                          encoding="utf-8"))
    cap = schem.load(FULL)
    cox, coy, coz = -24251, -64, 29949
    cpal = [n.split(":")[-1].split("[")[0] for n in cap.names]
    dig = {tuple(d) for d in glow.get("dig", [])}
    frogs = [(x, y, z) for x, y, z, b in glow["cells"]
             if b.split("[")[0] == "ochre_froglight"]
    for c in frogs:
        assert c in dig, ("froglight not flush - no dig entry", c)
    # waterlogged is game-derived and work.INTENTIONAL rightly drops it - the water itself
    # is the assertion: a pickle in a water cell IS waterlogged when placed
    for x, y, z, b in glow["cells"]:
        if b.split("[")[0] == "sea_pickle":
            assert cpal[cap.ids[y - coy, z - coz, x - cox]] == "water", (x, y, z)
