"""The axolotl: one piece, gills on both sides, dry feet, wet nose, a pale eye ring.

The properties pinned here are the ones whose failures shipped silently during the build: fronds
spent inside the skull, a fin floating a course above the tail, a body that faced away from its
own pond, and flank cells severed by a tree canopy.
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
CFG = yaml.safe_load(open(os.path.join(ROOT, "configs", "lowland_axolotl.yaml")))
PLANNED = os.path.join(ROOT, "out", "lowland_planned.litematic")

needs_world = pytest.mark.skipif(not os.path.exists(PLANNED),
                                 reason="needs out/lowland_planned.litematic (run sync first)")


@pytest.fixture(scope="module")
def built():
    c = GENERATORS["axolotl"].build(CFG["params"], None)
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
    m = schem.load(PLANNED)
    o = json.load(open(PLANNED[:-len(".litematic")] + ".scan.json"))["origin"]
    names = [n.split(":")[-1] for n in m.names]
    return m, o, names


def _name_at(world, x, y, z):
    m, o, names = world
    wx, wy, wz = x - o["x"], y - o["y"], z - o["z"]
    if 0 <= wy < m.ids.shape[0] and 0 <= wz < m.ids.shape[1] and 0 <= wx < m.ids.shape[2]:
        return names[m.ids[wy, wz, wx]]
    return "air"


@needs_world
def test_the_whole_animal_is_one_piece(built):
    """Gills, fin, legs, toes: 6-connected to the body or they break off in the world."""
    _, cells = built
    todo = set(cells)
    start = next(iter(todo))
    q, seen = deque([start]), {start}
    while q:
        x, y, z = q.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nb = (x + dx, y + dy, z + dz)
            if nb in todo and nb not in seen:
                seen.add(nb)
                q.append(nb)
    assert len(seen) == len(cells), f"{len(cells) - len(seen)} cells are severed from the animal"


@needs_world
def test_the_gills_exist_on_both_sides(built):
    """The frill fed one side into the skull once and the animal came out lopsided. Red is
    gills-only (magenta also serves the fin and the smile), so red is what is counted."""
    _, cells = built
    gills = [(x, y, z) for (x, y, z), n in cells.items() if n == "red_wool"]
    assert len(gills) >= 40, f"only {len(gills)} gill cells - the fronds are inside the head again"
    ax, az = (float(v) for v in CFG["params"]["at"])
    lx, lz = (float(v) for v in CFG["params"]["look_at"])
    hx, hz = lx - ax, lz - az
    n = math.hypot(hx, hz)
    px, pz = -hz / n, hx / n                           # plan-perpendicular to the gaze
    sides = {1: 0, -1: 0}
    for x, y, z in gills:
        s = (x - ax) * px + (z - az) * pz
        if abs(s) > 0.5:
            sides[1 if s > 0 else -1] += 1
    assert min(sides.values()) >= 12, f"gills are lopsided: {sides}"


@needs_world
def test_the_nose_is_over_the_water_and_no_water_is_touched(built, world):
    """Waterfront means OVERHANG: cells above water columns, never inside water cells."""
    _, cells = built
    over_water = 0
    for (x, y, z) in cells:
        below = _name_at(world, x, y - 1, z)
        assert _name_at(world, x, y, z) not in ("water", "ice"), f"cell in the pond at {(x, y, z)}"
        if below in ("water", "ice"):
            over_water += 1
    assert over_water >= 3, "the animal does not reach its own pond"


@needs_world
def test_the_animal_stands_on_the_ground(built, world):
    _, cells = built
    grounded = 0
    for (x, y, z) in cells:
        n = _name_at(world, x, y - 1, z)
        if n not in ("air", "cave_air", "void_air", "vine", "water", "ice",
                     "short_grass", "fern", "moss_carpet"):
            grounded += 1
    assert grounded >= 20, f"only {grounded} cells touch the bank"


@needs_world
def test_the_eyes_are_beads_with_pale_rings(built):
    _, cells = built
    eyes = [(x, y, z) for (x, y, z), n in cells.items() if n == "black_wool"]
    assert len(eyes) == 2, f"{len(eyes)} eye cells - an eye is ONE bead"
    for x, y, z in eyes:
        pale = sum(1 for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0))
                   if cells.get((x + dx, y + dy, z + dz)) == "white_wool")
        assert pale >= 2, f"eye at {(x, y, z)} has no pale ring - it vanishes into the coat"


@needs_world
def test_the_fin_rides_the_tail(built):
    """A MAGENTA membrane crest sitting directly on the body's own top - based on the BUILT top,
    so a drifted float cannot strand it in the air again. (The first fin was white and read as a
    mohawk; a fin is darker than the body, not a highlight.)"""
    _, cells = built
    fin = 0
    for (x, y, z), n in cells.items():
        if n == "magenta_wool" and cells.get((x, y - 1, z)) in ("pink_wool", "magenta_wool") \
                and (x, y + 1, z) not in cells:
            fin += 1
    assert fin >= 15, f"only {fin} crest cells ride the body"


@needs_world
def test_the_animal_smiles(built):
    """Half of what names an axolotl. Skipped silently once the muzzle geometry cannot host it,
    so the count is pinned."""
    c, _ = built
    assert c.meta["features_built"]["smile"] >= 3
    assert c.meta["features_built"]["filaments"] >= 12


@needs_world
def test_all_cheap_tier(built):
    _, cells = built
    assert {palette.tier(n) for n in cells.values()} <= {"cheap"}


@needs_world
def test_it_fits_its_stated_size(built):
    c, cells = built
    xs = [x for x, _, _ in cells]
    zs = [z for _, _, z in cells]
    ys = [y for _, y, _ in cells]
    L = float(CFG["params"]["length"])
    diag = math.hypot(max(xs) - min(xs), max(zs) - min(zs))
    assert L * 0.8 <= diag <= L * 1.25, f"plan diagonal {diag:.1f} vs asked length {L}"
    assert max(ys) - min(ys) <= 11, "taller than an axolotl has any right to be"


@needs_world
def test_the_prune_removed_scraps_not_the_animal(built):
    c, _ = built
    assert c.meta["features_built"]["pruned"] <= 20
