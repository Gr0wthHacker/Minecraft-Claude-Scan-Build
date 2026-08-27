"""The Lowland Thicket: planting is only planting if it reads as patches.

The design's whole risk is that it becomes noise. This project has measured that failure once
already - the deck floor found 127 vine blobs averaging under two cells and called them
scatter - and the first build of this design reproduced it exactly: 191 blobs of which 75%
were one or two cells, because the drift falloff was thresholded per cell. The fix was to put
the noise on the drift's RADIUS instead of its interior, and the assertion below is what stops
that regressing.

Everything else here pins a rule that was learned the hard way in this file's own history:
a plant roots in the dirt family and nowhere else (173 placement problems), a lily pad floats
on water and nothing may take the cell under it (eight lilies sat on seagrass), and passable
is not empty (a stalagmite grew up through two of Jack's vines).
"""
import collections
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import schem, scan          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "out", "island_full.litematic")
WORK = os.path.join(ROOT, "out", "Lowland Thicket.work.json")
LITE = os.path.join(ROOT, "out", "Lowland Thicket.litematic")

needs = pytest.mark.skipif(not (os.path.exists(FULL) and os.path.exists(WORK)),
                           reason="needs the capture and the generated thicket")

FLOOR = {"azalea", "flowering_azalea", "fern", "short_grass", "moss_carpet"}
SOIL = {"moss_block", "dirt", "grass_block", "coarse_dirt", "podzol", "rooted_dirt",
        "mycelium", "mud", "muddy_mangrove_roots"}
COAT = {c + "_wool" for c in ("white", "orange", "magenta", "light_blue", "yellow", "lime",
                              "pink", "gray", "light_gray", "cyan", "purple", "blue",
                              "brown", "green", "red", "black")} | {"bone_block"}


def _cells():
    return json.load(open(WORK, encoding="utf-8"))["cells"]


def _world():
    cap = schem.load(FULL)
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    pal = [n.split(":")[-1].split("[")[0] for n in cap.names]

    def at(x, y, z):
        iy, iz, ix = y - o["y"], z - o["z"], x - o["x"]
        if not (0 <= iy < cap.ids.shape[0] and 0 <= iz < cap.ids.shape[1]
                and 0 <= ix < cap.ids.shape[2]):
            return "air"
        return pal[cap.ids[iy, iz, ix]]
    return at


def _states():
    """Read the palette PROPERTIES, not `m.names` - the bare name list drops them, which is
    the same trap that hid the stair convention for a whole session."""
    m = schem.load(LITE)
    out = []
    for t in m.palette:
        v = t.value if hasattr(t, "value") else t
        nm = v["Name"]
        nm = nm.value if hasattr(nm, "value") else str(nm)
        pr = v.get("Properties")
        if pr is None:
            out.append(nm.split(":")[-1])
            continue
        d = pr.value if hasattr(pr, "value") else pr
        props = ",".join(f"{k}={(x.value if hasattr(x, 'value') else x)}"
                         for k, x in sorted(d.items()))
        out.append(f"{nm.split(':')[-1]}[{props}]")
    return m, out


@needs
def test_the_drifts_are_patches_not_confetti():
    """The one number that separates planting from noise."""
    pts = {(c[0], c[1], c[2]) for c in _cells() if c[3].split("[")[0] in FLOOR}
    seen, sizes = set(), []
    for p in pts:
        if p in seen:
            continue
        stack, n = [p], 0
        seen.add(p)
        while stack:
            c = stack.pop()
            n += 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        q = (c[0] + dx, c[1] + dy, c[2] + dz)
                        if q in pts and q not in seen:
                            seen.add(q)
                            stack.append(q)
        sizes.append(n)
    assert pts, "nothing planted at all"
    big = sum(s for s in sizes if s >= 8)
    assert big / len(pts) > 0.60, (
        f"only {100*big/len(pts):.0f}% of planted cells live in blobs of 8 or more "
        f"(sizes {sorted(sizes, reverse=True)[:8]}) - that is the deck floor's confetti again")
    assert max(sizes) >= 20, f"largest drift is {max(sizes)} cells; drifts should read as patches"


@needs
def test_a_plant_roots_in_the_dirt_family_and_nowhere_else():
    """173 placement problems came from listing mossy cobble and mossy stone brick as soil
    because they look like ground. Moss carpet is the exception: a carpet sits on anything."""
    at = _world()
    for x, y, z, b in _cells():
        k = b.split("[")[0]
        if k in ("azalea", "flowering_azalea", "fern", "short_grass"):
            assert at(x, y - 1, z) in SOIL, f"{k} at {(x, y, z)} roots in {at(x, y-1, z)}"


@needs
def test_a_lily_pad_floats_on_water():
    """Where the pond is one deep the bed IS the surface, and seagrass planted there left
    eight lily pads sitting on seagrass instead of on water."""
    at = _world()
    own = {(c[0], c[1], c[2]): c[3].split("[")[0] for c in _cells()}
    lilies = [(c[0], c[1], c[2]) for c in _cells() if c[3].split("[")[0] == "lily_pad"]
    assert lilies, "no lily pads"
    for (x, y, z) in lilies:
        below = own.get((x, y - 1, z)) or at(x, y - 1, z)
        assert below == "water", f"lily pad at {(x, y, z)} sits on {below}"


@needs
def test_nothing_is_planted_on_an_animal():
    """The night pass's rule, kept: a coat may take a lichen and nothing else. A fern growing
    out of the axolotl is the same mistake as a lantern standing on it."""
    at = _world()
    for x, y, z, b in _cells():
        assert at(x, y, z) not in COAT, f"{b} replaces a coat block at {(x, y, z)}"
        assert at(x, y - 1, z) not in COAT, f"{b} is planted on a coat block at {(x, y, z)}"


@needs
def test_it_plants_in_air_and_never_replaces_what_stands():
    """PASSABLE IS NOT EMPTY. Vine and grass pass light and a body, so the headroom test says
    yes to them - and used as the test for `may I build here` it grew a stalagmite up through
    two of Jack's vines. Water is the single exception: an aquatic plant carries its own."""
    at = _world()
    for x, y, z, b in _cells():
        here = at(x, y, z)
        if here in ("air", "cave_air", "void_air"):
            continue
        assert here == "water" and b.split("[")[0] in ("seagrass", "small_dripleaf"), \
            f"{b} at {(x, y, z)} would replace {here}"


@needs
def test_the_hanging_gardens_carry_glow_berries():
    """The cave vines earn their place by lighting themselves - light 14 - which is also why
    the night pass is solved AFTER this design. Read off the litematic's palette properties;
    `berries` is not in work.INTENTIONAL, so work.json does not carry it."""
    m, states = _states()
    berry = [i for i, s in enumerate(states) if "berries=true" in s]
    assert berry, "no berry states in the palette at all"
    n = int(np.isin(m.ids, berry).sum())
    assert n > 80, f"only {n} glow-berry cells; the hanging gardens do not light themselves"


@needs
def test_dripstone_tapers_to_a_tip_at_its_free_end():
    """A single `tip` block is a spike. Real dripstone narrows, and the sequence from the
    attached end is base-middle-frustum-tip in both directions."""
    # From the LITEMATIC: `thickness` is not in work.INTENTIONAL, so work.json carries only
    # `vertical_direction` and this test would be asserting against a stripped state - the
    # third time in one session that the wrong artifact was nearly tested.
    m, states = _states()
    sc = scan.load(LITE.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    cols = collections.defaultdict(list)
    ys, zs, xs = np.nonzero(m.ids != 0)
    for iy, iz, ix in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        st = states[m.ids[iy, iz, ix]]
        if not st.startswith("pointed_dripstone"):
            continue
        d = "up" if "vertical_direction=up" in st else "down"
        cols[(ix + o["x"], iz + o["z"], d)].append((iy + o["y"], st))
    assert cols, "no dripstone"
    for (x, z, d), run in cols.items():
        run.sort()
        free = run[-1] if d == "up" else run[0]     # the end away from the rock
        assert "thickness=tip" in free[1], \
            f"the free end of the {d} dripstone at {(x, z)} is {free[1]}"


@needs
def test_it_keeps_out_of_the_falls():
    """The Falls' cut channel and the column its water falls down are a live feature; a fern
    in the spillway is a fern in a waterfall."""
    for x, y, z, b in _cells():
        assert not (x in (-24213, -24212, -24211) and 29996 <= z <= 30003), \
            f"{b} at {(x, y, z)} stands in the Falls"
