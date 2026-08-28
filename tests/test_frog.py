"""The frog: one piece, two eyes that break the head line, a knee that clears the back, feet on
the ground, and a back nothing can spawn on.

Every property here failed at least once while it was being built, and every one of those
failures shipped a clean audit - 0 problems, 0 overlap, one component - which is precisely why
they are pinned rather than eyeballed:

  * the hind legs read the whole of what had been built so far to find the flank, so each pass
    answered one cell further out than the last and the animal crept from 15 wide to 19;
  * the forelegs were built after the hind FOOT, which lies exactly where the hand goes, so
    every cell found the ground course taken and it shipped with `forelegs: 0` in its own
    sidecar - a frog with no arms is still one connected piece with no placement problem;
  * the eye dome and the knee both sat UNDER the back line, so the two features that say frog
    were swallowed by the outline and the panel could not name the animal;
  * 129 of the 149 air cells over its back stood at block light zero, and the island night
    pass cannot see them - its classifier takes each column's topmost standable cell, and this
    lot is 113 courses under the island's belly.
"""
import json
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
import yaml

from mcbuild import blocks, palette, plot, schem
from mcbuild.gen import GENERATORS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(os.path.join(ROOT, "configs", "lowland_frog.yaml"), encoding="utf-8"))
FULL = os.path.join(ROOT, "out", "island_full.litematic")

needs_world = pytest.mark.skipif(not os.path.exists(FULL),
                                 reason="needs out/island_full.litematic (run sync first)")
pytestmark = needs_world


@pytest.fixture(scope="module")
def built():
    c = GENERATORS["frog"].build(CFG["params"], None)
    m = c.to_model()
    ox, oy, oz = c.world_origin
    cells = {}
    for i, name in enumerate(m.names):
        short = name.split(":")[-1].split("[")[0]
        if short in ("air", "cave_air", "void_air"):
            continue
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            cells[(int(x) + ox, int(y) + oy, int(z) + oz)] = short
    return c, cells


@pytest.fixture(scope="module")
def world():
    m = schem.load(FULL)
    o = json.load(open(FULL[:-len(".litematic")] + ".scan.json", encoding="utf-8"))["origin"]
    names = [n.split(":")[-1].split("[")[0] for n in m.names]

    def at(x, y, z):
        ix, iy, iz = x - o["x"], y - o["y"], z - o["z"]
        if not (0 <= ix < m.ids.shape[2] and 0 <= iy < m.ids.shape[0] and 0 <= iz < m.ids.shape[1]):
            return "air"
        return names[m.ids[iy, iz, ix]]
    return at


PASSABLE = {"air", "cave_air", "void_air", "vine", "short_grass", "tall_grass", "fern",
            "large_fern", "moss_carpet", "azalea", "flowering_azalea", "poppy", "dandelion",
            "glow_lichen", "hanging_roots"}


def test_the_whole_animal_is_one_piece(built):
    """6-connectivity, which is the only kind that counts: a limb whose cells meet the body at
    a corner is a separate build, and that is how the first cats lost their ear tips."""
    _, cells = built
    start = next(iter(cells))
    seen, q = {start}, deque([start])
    while q:
        x, y, z = q.popleft()
        for n in ((x+1, y, z), (x-1, y, z), (x, y+1, z), (x, y-1, z), (x, y, z+1), (x, y, z-1)):
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    assert len(seen) == len(cells), f"{len(cells) - len(seen)} cells are not attached"


def test_every_part_got_built(built):
    """`forelegs: 0` shipped TWICE - a frog with no arms is still one connected piece with no
    placement problem and a clean BOM, so nothing else in the pipeline noticed either time."""
    c, _ = built
    feats = c.meta["features_built"]
    for part in ("body", "haunch", "forelegs", "toes", "eyes", "mouth", "throat"):
        assert feats[part] > 0, f"{part} was not built at all: {feats}"


def test_the_gaze_is_cardinal_and_the_face_is_flat(built):
    """A head aimed off the grid renders its 'flat' face as a diagonal staircase of corners -
    the axolotl paid three passes for this, and no orthographic render can show it."""
    c, cells = built
    fx, fz = c.meta["facing"]
    assert abs(fx) + abs(fz) == 1, f"facing {c.meta['facing']} is not one cardinal unit"
    # the frontmost cells all share one x (or one z), which is what "flat" means on a grid
    axis = 0 if fx else 2
    front = min(k[axis] for k in cells) if (fx or fz) < 0 else max(k[axis] for k in cells)
    nose = [k for k in cells if k[axis] == front]
    assert len(nose) >= 3, f"the snout is {len(nose)} cell(s) - too narrow to be a face"


def test_two_bright_eyes_in_dark_frames(built):
    """The statue's loudest feature. A pale square on an orange head is a patch; the dark ring
    is what turns it into an eye, and it is what every earlier version of this face was missing.
    Two of them, separated, each fully surrounded on its own plane by the frame block."""
    c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    # THE EYES' OWN PLANE, found from the blocks rather than from the bounding box: the toes
    # reach further forward than the face does, and the same block lights the crown - a lamp in
    # the back is not an eye and is not framed.
    lamps = [k for k, v in cells.items() if v == p["lamp"]]
    assert lamps, "no bright blocks at all"
    fx, _fz = c.meta["facing"]
    plane = min(k[0] for k in lamps) if fx < 0 else max(k[0] for k in lamps)
    bright = sorted(k for k in lamps if abs(k[0] - plane) <= 1)
    assert bright, "no bright eye blocks"
    zs = sorted({k[2] for k in bright})
    runs = [[zs[0]]]
    for z in zs[1:]:
        (runs[-1].append(z) if z == runs[-1][-1] + 1 else runs.append([z]))
    assert len(runs) == 2, f"expected two separated eyes, got {len(runs)}: {zs}"
    assert min(runs[1]) - max(runs[0]) - 1 >= 2, "the eyes will read as one bar"
    x0 = min(k[0] for k in bright)
    loose = [k for k in bright if k[0] == x0 and not all(
        cells.get((k[0], k[1] + dy, k[2] + dz)) in (p["mark"], p["lamp"])
        for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    assert not loose, f"{len(loose)} bright cells are not framed, e.g. {loose[:3]}"


def test_the_eye_rests_on_the_skull(built):
    """Jack: "the eyes feel weird." They overhung the head by two cells with open air beneath,
    so each read as a lamp on a bracket. On the mob the bulge is ATTACHED - it clears the
    outline by about a cell and the rest of it is resting on the head."""
    _, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    eye = {k for k, v in cells.items() if v in (p["pupil"], p["mark"], p["iris"])}
    top = max(y for (_, y, _) in cells)
    bulge = {k for k in eye if k[1] >= top - 1}
    assert bulge, "no eye bulge found"
    floor = min(k[1] for k in bulge)
    base = [k for k in bulge if k[1] == floor]
    loose = [k for k in base if (k[0], k[1] - 1, k[2]) not in cells]
    # a cell of overhang is the bulge; a third of the footprint in mid-air is a bracket
    assert len(loose) * 3 <= len(base), (
        f"{len(loose)} of {len(base)} eye-base cells hang over nothing, e.g. {loose[:3]}")


def test_it_is_an_upright_statue(built):
    """THE REFERENCE CHANGED, and this test changed with it - deliberately, and it is worth
    saying why rather than quietly editing a number. The mob is a flat crouching creature,
    about 1.0 long : 0.75 wide : 0.5 tall, and this test used to pin that. Jack then gave a
    third reference, Graysun's Frog Statue, and asked for THAT: an upright sitting statue,
    about as tall as it is wide, whose whole front is a face. Those are two different animals
    and no build satisfies both.

    A test that pins a proportion is pinning a DECISION about which reference is being copied.
    Change the reference and you must change the test in the same commit, or the suite is
    quietly enforcing the thing that was rejected."""
    c, cells = built
    zs = [k[2] for k in cells]
    W = max(zs) - min(zs) + 1
    H = max(k[1] for k in cells) - c.meta["base_y"] + 1
    assert 0.85 <= H / W <= 1.6, f"height/width is {H / W:.2f}; the statue is about 1.1"


def test_the_front_is_a_face_stacked_in_this_order(built):
    """Eyes, then the mouth band, then the belly - that stack IS the statue, and the courses
    have to be budgeted rather than each placed from its own fraction of the height. Placed
    that way once, the eye frame and the mouth band overlapped and the whole face came out as
    one pale slab from the brow to the belly."""
    c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    fx, _fz = c.meta["facing"]
    pales = [k for k, v in cells.items() if v == p["belly"]]
    assert pales, "no pale blocks at all"
    front = min(k[0] for k in pales) if fx < 0 else max(k[0] for k in pales)
    plane = {k: v for k, v in cells.items() if abs(k[0] - front) <= 1}
    eyes = [k[1] for k, v in plane.items() if v == p["lamp"]]
    pale = [k[1] for k, v in plane.items() if v == p["belly"]]
    assert eyes and pale, f"face plane has {len(eyes)} eye and {len(pale)} pale cells"
    assert min(eyes) > max(pale), "the eyes are not above the pale mouth and belly"
    # ...and the pale is in two bands, the mouth and the belly, not one slab
    band = sorted(set(pale))
    gaps = [b - a for a, b in zip(band, band[1:]) if b - a > 1]
    assert gaps, f"the mouth and the belly have merged into one panel: courses {band}"


def test_every_foot_sits_on_its_own_ground(built, world):
    """One level per foot AND filled down to the turf. Held at the belly plane over ground that
    rolls away a pad floats; seated per column, its neighbours land on two courses and touch
    only diagonally - the turtle's flippers came off as four pieces that way."""
    _, cells = built
    floor = min(y for (_, y, _) in cells)
    for (x, y, z) in cells:
        if y != floor:
            continue
        assert world(x, y - 1, z) not in PASSABLE, f"the lowest cell at {(x, y, z)} stands on air"


def test_nothing_stands_in_water_and_nothing_is_covered(built, world):
    _, cells = built
    for (x, y, z), b in cells.items():
        here = world(x, y, z)
        assert here in PASSABLE, f"{b} at {(x, y, z)} covers {here}"


def test_it_keeps_off_the_church(built):
    """Nose 3 clear of the sanctum's east wall: a frog with its face against a wall is not
    looking at the building, it is stuck to it."""
    _, cells = built
    sanctum = os.path.join(ROOT, "out", "Lowland Sanctum.work.json")
    if not os.path.exists(sanctum):
        pytest.skip("needs the sanctum's work list")
    wall = {(c[0], c[2]) for c in json.load(open(sanctum, encoding="utf-8"))["cells"]}
    near = min(max(abs(x - sx), abs(z - sz)) for (x, _, z) in cells for (sx, sz) in wall)
    assert near >= 3, f"the frog comes within {near} of the sanctum"


def test_it_stays_on_the_plot(built):
    _, cells = built
    pl = plot.find(FULL)
    off = [k for k in cells if not pl.contains(k[0], k[2])]
    assert not off, f"{len(off)} cells outside the plot, e.g. {off[:3]}"


def test_every_block_is_cheap_spendable_and_1_19(built):
    _, cells = built
    for b in sorted(set(cells.values())):
        assert palette.tier(b) == "cheap", f"{b} is {palette.tier(b)} tier"
        assert blocks.spendable(b), f"{b} is currency on this server"
        assert blocks.available(b), f"{b} is not in the 1.19 allowlist"


def test_the_coat_is_a_ladder_and_it_is_not_the_ground(built):
    """Three tones of one hue beat two tones and a third - the flamingo's bruise - and the
    ladder has to be a ladder: every step visible.

    AND THE GROUND TEST IS COLOUR DISTANCE, NOT LUMINANCE. The turtle already proved the point
    on this floor: `brown_wool` is within five of moss in luminance and reads perfectly, because
    what separates them is a full hue flip. Testing luminance would have failed the reference's
    own palette and passed a green frog.
    """
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    lum = [sum(blocks.color(p[k])) / 3 for k in ("back", "flank", "mark")]
    assert lum[0] > lum[1] > lum[2], f"back/flank/mark are not a descending ladder: {lum}"
    assert min(lum[i] - lum[i + 1] for i in range(2)) >= 20, f"two rungs look alike: {lum}"
    assert sum(blocks.color(p["belly"])) / 3 > lum[0] + 30, "the belly does not read as pale"
    moss = blocks.color("moss_block")
    body = blocks.color(p["back"])
    dist = sum((a - b) ** 2 for a, b in zip(moss, body)) ** 0.5
    assert dist >= 60, f"the body is {dist:.0f} from the moss it sits on - it will vanish"


def test_nothing_can_spawn_on_its_back(built):
    """THE ISLAND NIGHT PASS CANNOT SEE THIS ANIMAL. Its classifier takes the topmost standable
    cell in a column, and this lot lies 113 courses under the island's belly - so the frog, the
    lot and everything in it are invisible to it. Measured directly instead: block light
    propagated through the finished world, over every cell the frog itself puts a top on."""
    from mcbuild import nightlight
    c, cells = built
    Y_LO, Y_HI = 20, 60
    cap = schem.load(FULL)
    o = json.load(open(FULL[:-len(".litematic")] + ".scan.json", encoding="utf-8"))["origin"]
    ox, oy, oz = o["x"], o["y"], o["z"]
    pal = [n.split(":")[-1] for n in cap.names]
    x0 = max(ox, min(k[0] for k in cells) - 18)
    x1 = min(ox + cap.ids.shape[2] - 1, max(k[0] for k in cells) + 18)
    z0 = max(oz, min(k[2] for k in cells) - 18)
    z1 = min(oz + cap.ids.shape[1] - 1, max(k[2] for k in cells) + 18)
    NY, NZ, NX = Y_HI - Y_LO + 1, z1 - z0 + 1, x1 - x0 + 1
    name = np.empty((NY, NZ, NX), dtype=object)
    for y in range(Y_LO, Y_HI + 1):
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                name[y - Y_LO, z - z0, x - x0] = pal[cap.ids[y - oy, z - oz, x - ox]]
    for (x, y, z), b in cells.items():
        if Y_LO <= y <= Y_HI:
            name[y - Y_LO, z - z0, x - x0] = b

    flat = name.reshape(-1)
    states = sorted(set(flat.tolist()))
    ix = {st: i for i, st in enumerate(states)}
    ids = np.array([ix[st] for st in flat], np.int32).reshape(name.shape)
    opaque, emit, _passy, _spawn, _water = nightlight.classify(states)
    light = nightlight.propagate(opaque[ids], emit[ids])

    tops = {}
    for (x, y, z) in cells:
        tops[(x, z)] = max(tops.get((x, z), -999), y)
    dark = [(x, y + 1, z) for (x, z), y in tops.items()
            if Y_LO <= y + 1 <= Y_HI and light[y + 1 - Y_LO, z - z0, x - x0] == 0]
    assert not dark, f"{len(dark)} cells over the frog are at block light 0, e.g. {dark[:5]}"
