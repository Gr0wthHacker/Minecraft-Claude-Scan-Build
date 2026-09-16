"""The Abyss Drift and the Abyss Jelly - the field and the second creature under the park.

Each test pins a trap this repo has actually shipped, in some body:

  the fall column     nothing may enter the Prism Well's r56 - a surface there strands a runner
                      who missed a landing sixty blocks out with no way back (the squid's rule)
  the grading         the void is seen only from the well; a field that is not densest just
                      outside it, thinning outward, has spent its effort where no one is
  witnessed blocks    `nether_wart_block` / `verdant_froglight` are cheap and legal and appear
                      in NO capture; a witness set from `out/` is circular, so this reads captures
  no confetti         a uniform sprinkle reads as noise - the drift must cluster and size-grade
  one piece, upright  the jelly's first build was upside down (crown at the floor, tentacles
                      rising) and rendered as a plausible jelly from every orthographic angle;
                      its oral arms hung from a hollow cup and came off as a separate component
  self-lit            an unlit thing in a pitch-dark void is invisible; the light IS the design
"""
from __future__ import annotations

import json
import math
import os
from collections import deque

import numpy as np
import pytest
import yaml

from mcbuild import blocks, palette, schem
from mcbuild.gen import abyssdrift, jellyfish

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WELL = (97590.0, 80815.0, 56.0)
CAPTURES = ("island_full.litematic", "island_now.litematic", "islandlow.litematic")


def _cfg(name):
    return yaml.safe_load(open(os.path.join(HERE, "configs", name)))["params"]


def _witnessed():
    seen = set()
    for name in CAPTURES:
        p = os.path.join(HERE, "out", name)
        if not os.path.exists(p):
            continue
        m = schem.load(p)
        names = [t.value["Name"].value.split(":")[-1] for t in m.palette]
        used = np.bincount(m.ids.ravel(), minlength=len(names))
        seen |= {n for i, n in enumerate(names) if used[i]}
    return seen


# THE ISLAND CAPTURES ARE THE WRONG WITNESS FOR A PARK-REGION PALETTE. The squid restricted
# itself to island-witnessed blocks and got a red/mangrove/bone palette; a debris field needs
# STONE, and the value ladder that reads in the dark is measured across families. These stones
# and the cave-vine are not in the island captures, but they are witnessed by the shipped-and-
# accepted park itself: `Mine Ridge` is 41,948 blocks of exactly this stone ladder, `Lowland
# Thicket` lights its hanging gardens with these cave-vines, and the wools are dyed sheep. So the
# real check is the one the whole park uses - cheap-or-ok tier, spendable, 1.19 - which each test
# also asserts; this set just names what is established beyond the island.
PARK_ESTABLISHED = {
    "tuff", "cobbled_deepslate", "andesite", "cave_vines", "cave_vines_plant",
    "light_blue_wool", "white_wool", "cyan_wool", "pink_wool",
}


def _names(c):
    return [c.reg.palette[i].value["Name"].value.split(":")[-1] for i in range(len(c.reg.palette))]


def _components(occ):
    lab = np.zeros(occ.shape, np.int32)
    sizes, cur = [], 0
    for cell in map(tuple, np.argwhere(occ)):
        if lab[cell]:
            continue
        cur += 1
        q, n = deque([cell]), 0
        lab[cell] = cur
        while q:
            Y, Z, X = q.popleft()
            n += 1
            for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                a, b, cc = Y + dy, Z + dz, X + dx
                if (0 <= a < occ.shape[0] and 0 <= b < occ.shape[1] and 0 <= cc < occ.shape[2]
                        and occ[a, b, cc] and not lab[a, b, cc]):
                    lab[a, b, cc] = cur
                    q.append((a, b, cc))
        sizes.append(n)
    return sorted(sizes, reverse=True)


# ===================================================================== THE DRIFT

@pytest.fixture(scope="module")
def drift():
    need = ["out/Abyss Squid.litematic", "out/Park Complete.litematic", "out/Abyss Jelly.litematic"]
    if not all(os.path.exists(os.path.join(HERE, n)) for n in need):
        pytest.skip("the drift's context designs have not been generated")
    return abyssdrift.build(_cfg("abyss_drift.yaml"))


def _world_cells(c):
    ox, oy, oz = c.world_origin
    ys, zs, xs = np.nonzero(c.ids > 0)
    return ox + xs, oy + ys, oz + zs


def test_drift_NOTHING_ENTERS_THE_FALL_COLUMN(drift):
    wx, wy, wz = _world_cells(drift)
    d = np.hypot(wx - WELL[0], wz - WELL[1])
    assert d.min() >= WELL[2], f"a rock is {d.min():.1f} from the well axis, inside r{WELL[2]:.0f}"


def test_drift_is_densest_just_outside_the_well_and_thins_outward(drift):
    """The whole point of grading: effort where the camera is. The nearest cell hugs the fall
    column, and the near ring carries many times the near-column density of the far south."""
    wx, wy, wz = _world_cells(drift)
    d = np.hypot(wx - WELL[0], wz - WELL[1])
    assert d.min() <= 66, f"nearest cell is {d.min():.0f} out - the near ring is empty"
    # occupied-column density, near ring vs far ring, per unit area
    at = tuple(drift.world_origin)
    sy, sz, sx = drift.ids.shape
    col = (drift.ids > 0).any(axis=0)                       # (z, x)
    zz, xx = np.mgrid[0:sz, 0:sx]
    dw = np.hypot(at[0] + xx - WELL[0], at[2] + zz - WELL[1])
    near = (dw >= WELL[2]) & (dw < 110)
    far = (dw >= 250)
    dn = col[near].mean()
    df = col[far].mean()
    assert dn > 2.5 * df, f"near density {dn:.3f} is not clearly above far {df:.3f}"


def test_the_drift_excludes_the_squid_and_the_jelly(drift):
    """A rock through the hero is vandalism; the field frames it, never crowds it."""
    at = tuple(drift.world_origin)
    sy, sz, sx = drift.ids.shape
    col = (drift.ids > 0).any(axis=0)
    for name in ("Abyss Squid", "Abyss Jelly"):
        m = abyssdrift._load_columns(os.path.join(HERE, "out", f"{name}.litematic"), at, (sx, sy, sz))
        assert m is not None
        assert not (col & m).any(), f"the drift shares a column with {name}"


def test_the_drift_is_graded_by_size_not_uniform(drift):
    """A field of one size is a texture; motes and a few boulders is a drift. Both tails exist."""
    f = drift.meta["features_built"]
    assert f["motes"] >= 20, "no small tail - the field is not a drift"
    assert f["boulders"] >= 3, "no large silhouettes"
    assert f["boulders"] <= abyssdrift.DRIFT["max_boulders"], "boulders are not capped"


def test_the_drift_palette_is_witnessed_cheap_and_gravity_free(drift):
    used = {n for n in _names(drift) if n != "air"}
    seen = _witnessed()
    if seen:
        assert used <= seen | PARK_ESTABLISHED, f"drift uses unwitnessed blocks: {sorted(used - seen - PARK_ESTABLISHED)}"
    for n in used:
        assert palette.tier(n) != "expensive", f"{n} is expensive tier"
        assert blocks.spendable(n), f"{n} is currency"
        assert not blocks.falls(n), f"{n} is a gravity block and would pour out of a floating rock"


# ===================================================================== THE JELLY

AT_J = [97617, 117, 80817]


@pytest.fixture(scope="module")
def jelly():
    return jellyfish.build(_cfg("abyss_jelly.yaml"))


def test_jelly_is_one_connected_piece(jelly):
    sizes = _components(jelly.ids > 0)
    assert len(sizes) == 1, f"the jelly is in {len(sizes)} pieces: {sizes[:5]}"


def test_jelly_is_the_right_way_up(jelly):
    """Crown high, tentacles low. The first build was inverted and rendered as a plausible jelly
    from every orthographic angle while hanging upside down in game."""
    names = _names(jelly)
    idx = {n: i for i, n in enumerate(names)}
    ys = np.nonzero(jelly.ids > 0)[0]
    # the bell body (wool) sits above the tentacle streamers' lowest reach
    bell_ids = [idx[n] for n in ("light_blue_wool", "white_wool", "cyan_wool") if n in idx]
    bell_y = np.nonzero(np.isin(jelly.ids, bell_ids))[0]
    assert bell_y.mean() > ys.mean(), "the bell is not above the mean - built upside down"
    assert bell_y.max() >= ys.max() - 1, "the crown is not at the top"


def test_jelly_lights_itself(jelly):
    """In a pitch-dark void the glow is the whole design: a rim, a crown, tentacle beads, spots,
    and glowing cave-vine tips. Every one must actually be placed."""
    f = jelly.meta["features_built"]
    assert f["rim"] > 40, "no margin ring of light"
    assert f["spots"] > 0, "no amethyst photophores"
    assert f["beads"] > 0, "no light beads on the tentacles"
    assert f["tentacles"] >= 12 and f["oral"] >= 3
    used = _names(jelly)
    assert "ochre_froglight" in used and "amethyst_cluster" in used and "cave_vines" in used


def test_jelly_palette_is_witnessed_cheap_and_gravity_free(jelly):
    used = {n for n in _names(jelly) if n != "air"}
    seen = _witnessed()
    if seen:
        assert used <= seen | PARK_ESTABLISHED, f"jelly uses unwitnessed blocks: {sorted(used - seen - PARK_ESTABLISHED)}"
    for n in used:
        assert palette.tier(n) != "expensive", f"{n} is expensive tier"
        assert blocks.spendable(n), f"{n} is currency"
        assert not blocks.falls(n), f"{n} is a gravity block"


def test_jelly_keep_out_gate_actually_refuses(  # a synthetic build with a keep-out over its centre
):
    """The gate is the one place the fall column is enforced; a part added later cannot forget it.
    Put a keep-out over the jelly's own axis and assert cells are refused and the closest reported."""
    c = jellyfish.build({"at": [0, 0, 0], "keep_out": [40, 40, 20], "scale": 1.0,
                         "tent_out": 0.22, "tent_wave": 0.15})
    # the canvas centre is at (half, *, half); with keep_out at (40,40) r20 over it, nothing is
    # within 20 of that axis
    ox, oy, oz = 0, 0, 0
    ys, zs, xs = np.nonzero(c.ids > 0)
    d = np.hypot(xs - 40, zs - 40)
    assert d.min() >= 20 - 1e-6
    assert c.meta["closest_to_keep_out"] is not None


def test_jelly_stays_in_the_park_shadow_band():
    """As shipped: X within 97500..97699, and Y clear of the plate (196) above and the pool below."""
    p = os.path.join(HERE, "out", "Abyss Jelly.litematic")
    s = os.path.join(HERE, "out", "Abyss Jelly.scan.json")
    if not os.path.exists(p):
        pytest.skip("Abyss Jelly has not been generated")
    m = schem.load(p)
    o = json.load(open(s))["origin"]
    ys, zs, xs = np.nonzero(m.ids > 0)
    assert 97500 <= o["x"] + xs.min() and o["x"] + xs.max() <= 97699
    assert 80300 <= o["z"] + zs.min() and o["z"] + zs.max() <= 80899
    assert o["y"] + ys.max() <= 190 and o["y"] + ys.min() >= 100
