"""The Sanctum: a complete building, whose ruin is in the right places.

What is pinned is the ONCE-IMPRESSIVE contract: the facade survives whole (doorway, oculus,
pediment), the apse holds a full crest, the side walls are the part that fell, the floor is one
level plane, and the ground design's own lanterns are dodged, never covered.
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
from mcbuild.gen.ruinring import _PASSABLE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(os.path.join(ROOT, "configs", "lowland_sanctum.yaml")))
PLANNED = os.path.join(ROOT, "out", "lowland_planned.litematic")

needs_world = pytest.mark.skipif(not os.path.exists(PLANNED),
                                 reason="needs out/lowland_planned.litematic (run sync first)")

AX, AZ = CFG["params"]["at"]
L = CFG["params"]["length"]
FY = CFG["params"]["floor_y"]
ZF = AZ + L // 2
Z_CHORD = AZ - L // 2


@pytest.fixture(scope="module")
def built():
    c = GENERATORS["sanctum"].build(CFG["params"], None)
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


def _wname(world, x, y, z):
    m, o, names = world
    wx, wy, wz = x - o["x"], y - o["y"], z - o["z"]
    if 0 <= wy < m.ids.shape[0] and 0 <= wz < m.ids.shape[1] and 0 <= wx < m.ids.shape[2]:
        return names[m.ids[wy, wz, wx]]
    return "air"


@needs_world
def test_nothing_covers_the_world(built, world):
    """Includes the ground design's lanterns: the footprint was chosen to dodge their columns,
    and a single covered lantern means the walls drifted onto the 9-grid."""
    _, cells = built
    for (x, y, z) in cells:
        wn = _wname(world, x, y, z)
        assert wn in _PASSABLE, f"covers {wn} at {(x, y, z)}"


@needs_world
def test_the_facade_survives_whole(built):
    _, cells = built
    peak = max(y for (x, y, z) in cells if z == ZF)
    assert peak >= FY + 10, f"the pediment tops at {peak} - the front does not read impressive"
    for dx in (-1, 0, 1):                              # the doorway is OPEN, 3 wide, 5 tall
        for k in range(5):
            assert (AX + dx, FY + 1 + k, ZF) not in cells, "the doorway is blocked"
    assert (AX, FY + 7, ZF) not in cells, "the oculus is filled"
    ring = sum(1 for dx, k in ((0, 5), (0, 7), (-1, 5), (-1, 6), (-1, 7), (1, 5), (1, 6), (1, 7))
               if cells.get((AX + dx, FY + 1 + k, ZF)) == "chiseled_polished_blackstone")
    assert ring >= 6, f"only {ring} chiseled cells ring the oculus"


@needs_world
def test_the_torn_apse_stands_tallest_at_the_tear(built):
    _, cells = built
    H = CFG["params"]["wall_h"] + 1
    crest = [(x, z) for (x, y, z) in cells if y == FY + H and z < Z_CHORD]
    assert len(crest) >= 2, f"no torn edge reaches full height ({len(crest)} columns)"


@needs_world
def test_nothing_perches_on_the_breach(built, world):
    """The void hole north of the building is real, and 'stuff hanging off in the void' is
    what Jack called the first apse. No sanctum column may stand 4-adjacent to a no-ground
    column - where the arc meets the breach, the wall is GONE."""
    _, cells = built
    m, o, names = world
    PASS = set(_PASSABLE) | {"water", "ice"}
    ycap = 58 - o["y"]

    def has_ground(wx, wz):
        x, z = wx - o["x"], wz - o["z"]
        if not (0 <= x < m.ids.shape[2] and 0 <= z < m.ids.shape[1]):
            return False
        col = m.ids[:ycap, z, x]
        return any(names[i] not in PASS for i in np.unique(col))

    for (x, y, z) in cells:
        if z >= Z_CHORD:
            continue                                   # the breach is north; south is inland
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            assert has_ground(x + dx, z + dz), \
                f"sanctum cell at {(x, y, z)} perches on the breach lip"


@needs_world
def test_the_walls_fell_asymmetrically(built):
    """A mirrored collapse is an algorithm's signature. West: mostly standing with one breach.
    East: mostly down, one full-height survivor - so the open scene looks into the nave."""
    _, cells = built
    x0, x1 = AX - CFG["params"]["width"] // 2, AX + CFG["params"]["width"] // 2
    H = CFG["params"]["wall_h"]

    def profile(wall_x):
        heights = {}
        for (x, y, z), n in cells.items():
            if x == wall_x and Z_CHORD < z < ZF and y > FY:
                heights[z] = max(heights.get(z, 0), y - FY)
        assert heights, f"no wall at x={wall_x}"
        vals = sorted(heights.values())
        return vals, vals[len(vals) // 2]

    west, west_med = profile(x0)
    east, east_med = profile(x1)
    assert west_med >= 4, f"the west wall fell too (median {west_med}) - nothing stands"
    assert min(west) <= 2, "the west wall has no breach - a fortress, not a ruin"
    assert east_med <= 3, f"the east wall stands (median {east_med}) - the collapse is mirrored"
    assert max(east) >= H, "the east wall lost its lone survivor"


@needs_world
def test_the_west_wall_has_windows(built):
    _, cells = built
    x0 = AX - CFG["params"]["width"] // 2
    sills = 0
    for (x, y, z), n in cells.items():
        if x == x0 and n == "chiseled_polished_blackstone" and Z_CHORD < z < ZF:
            if (x, y + 1, z) not in cells and (x, y + 3, z) in cells:
                sills += 1                             # sill, opening above, wall resumes over
    assert sills >= 2, f"only {sills} window openings - a windowless box is a bunker"


@needs_world
def test_the_building_was_used(built):
    c, _ = built
    f = c.meta["features_built"]
    assert f["bench"] >= 2, "no bench - a monument, not a place"
    assert f["drum"] >= 2, "no fallen drum"
    assert f["threshold"] >= 3, "no worn threshold"


@needs_world
def test_the_floor_is_one_level_plane(built):
    _, cells = built
    floor = [(x, z) for (x, y, z) in cells if y == FY and Z_CHORD <= z <= ZF]
    assert len(floor) >= 100, f"only {len(floor)} floor cells at FY - the stylobate is missing"


@needs_world
def test_the_altar_and_its_bloom(built):
    _, cells = built
    blooms = [(x, y, z) for (x, y, z), n in cells.items() if n == "amethyst_cluster"]
    assert len(blooms) == 1
    bx, by, bz = blooms[0]
    assert cells.get((bx, by - 1, bz)) == "chiseled_polished_blackstone", \
        "the bloom does not grow from the altar"
    lanterns = [k for k, n in cells.items() if n == "soul_lantern"]
    assert len(lanterns) >= 2


@needs_world
def test_the_nave_keeps_its_columns(built):
    c, _ = built
    assert c.meta["features_built"]["columns"] >= 4


@needs_world
def test_the_spur_reaches_the_way(built):
    _, cells = built
    sx, sz = CFG["params"]["spur_to"]
    near = [k for k in cells if math.hypot(k[0] - sx, k[2] - sz) <= 2.5]
    assert near, "the spur never arrives - the sanctum is beside the walk, not on it"


@needs_world
def test_no_expensive_and_no_design_collisions(built):
    _, cells = built
    assert "expensive" not in {palette.tier(n) for n in cells.values()}
    shipped = os.path.join(ROOT, "out", "Lowland Sanctum.work.json")
    if not os.path.exists(shipped):
        pytest.skip("ship the sanctum first")
    mine = {(c[0], c[1], c[2]) for c in json.load(open(shipped))["cells"]}
    for other in ["Lowland Portal", "Lowland Ruinway", "Lowland Capybara Flee",
                  "Lowland Flamingo", "Lowland Axolotl", "Lowland Bat"]:
        theirs = {(c[0], c[1], c[2]) for c in
                  json.load(open(os.path.join(ROOT, "out", f"{other}.work.json")))["cells"]}
        assert not (mine & theirs), f"shares cells with {other}"
