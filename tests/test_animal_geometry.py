"""The primitives every animal is built from: loft sweeps, relax smoothing, coat patterns.

None of these had a test. Each one has a documented failure behind it that a test can hold shut:
relax welding legs into a slab, relax eating thin limbs, features placed at a computed radius
floating clear of a surface that smoothing had already moved.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from mcbuild.gen import coat, loft, smooth

F, S = (0, 1), (1, 0)                      # facing +z, side +x


# ---------------------------------------------------------------- loft

def test_lerp_hits_its_keyframes_and_clamps_outside_them():
    keys = [[0.0, 1.0], [0.5, 3.0], [1.0, 2.0]]
    assert loft.lerp(keys, 0.0) == (1.0,)
    assert loft.lerp(keys, 0.5) == (3.0,)
    assert loft.lerp(keys, 1.0) == (2.0,)
    assert loft.lerp(keys, -5.0) == (1.0,), "below the first key must clamp, not extrapolate"
    assert loft.lerp(keys, 99.0) == (2.0,), "above the last key must clamp"
    assert loft.lerp(keys, 0.25)[0] == pytest.approx(2.0)


def test_disc_is_flat_and_rib_is_upright():
    d = set()
    loft.disc(d, 0, 7, 0, F, S, 3, 3, 2.0)
    assert {c[1] for c in d} == {7}, "a disc is one course - it is the section of a vertical spine"
    r = set()
    loft.rib(r, 0, 7, 0, F, S, 3, 3, 2.0)
    assert len({c[1] for c in r}) > 1, "a rib is a vertical section across the heading"


def test_disc_radius_controls_size_and_n_controls_squareness():
    small, big = set(), set()
    loft.disc(small, 0, 0, 0, F, S, 2, 2, 2.0)
    loft.disc(big, 0, 0, 0, F, S, 5, 5, 2.0)
    assert len(big) > len(small)
    round_, square = set(), set()
    loft.disc(round_, 0, 0, 0, F, S, 4, 4, 2.0)     # n=2 is an ellipse
    loft.disc(square, 0, 0, 0, F, S, 4, 4, 8.0)     # large n approaches a rectangle
    assert len(square) > len(round_), "a higher exponent fills more of the bounding square"


def test_rib_squash_lo_only_moves_the_underside():
    plain, squashed = set(), set()
    loft.rib(plain, 0, 20, 0, F, S, 3, 4, 2.0, squash_lo=1.0)
    loft.rib(squashed, 0, 20, 0, F, S, 3, 4, 2.0, squash_lo=1.6)
    assert max(c[1] for c in squashed) == max(c[1] for c in plain), "the back line must not move"
    assert min(c[1] for c in squashed) < min(c[1] for c in plain), "the belly must drop"


def test_surface_out_finds_the_outermost_cell_not_the_first():
    """The whole point: it reports where the skin IS, so a feature anchors to a relaxed surface
    rather than to the radius someone computed before relaxing."""
    hide = {(0, 0, 2), (0, 0, 4), (0, 0, 7)}
    cell, dist = loft.surface_out(hide, 0, 0, 0, 0, 1, reach=10)
    assert cell == (0, 0, 7) and dist == 7


def test_surface_out_reports_nothing_rather_than_guessing():
    assert loft.surface_out(set(), 0, 0, 0, 0, 1, reach=5) == (None, 0)


def test_crest_is_the_top_of_a_column():
    hide = {(1, 0, 1), (1, 5, 1), (1, 3, 1), (2, 9, 1)}
    assert loft.crest(hide, 1, 1) == 5, "the other column must not contribute"
    assert loft.crest(hide, 8, 8) is None


# ---------------------------------------------------------------- relax

def _slab(w=6, h=6, d=6, x0=0):
    return {(x0 + x, y, z) for x in range(w) for y in range(h) for z in range(d)}


def test_relax_protect_keeps_thin_limbs_that_keep_would_eat():
    """`keep` counts neighbours a slender leg does not have, so legs go in as `protect`."""
    leg = {(0, y, 0) for y in range(8)}                 # one block thick - no neighbours to speak of
    assert not smooth.relax(leg, rounds=2, fill=15, keep=8) & leg, "precondition: bare relax eats it"
    kept = smooth.relax(leg, rounds=2, fill=15, keep=8, protect=leg)
    assert leg <= kept, "a protected limb must survive"


def test_relax_forbid_keeps_the_gap_between_two_legs():
    """Filling is blind to anatomy: two surfaces across a narrow gap look exactly like a dent, and
    the giraffe's four legs welded into one part for the whole lower half."""
    a, b = _slab(3, 8, 3, x0=0), _slab(3, 8, 3, x0=4)
    gap = {(3, y, z) for y in range(8) for z in range(3)}
    welded = smooth.relax(a | b, rounds=2, fill=11, keep=8, protect=a | b)
    assert welded & gap, "precondition: without `forbid` the gap fills"
    apart = smooth.relax(a | b, rounds=2, fill=11, keep=8, protect=a | b, forbid=gap)
    assert not (apart & gap), "`forbid` must keep the air between the legs"


def test_relax_never_returns_a_forbidden_cell_even_if_protected():
    cells = _slab()
    banned = {next(iter(cells))}
    assert not (smooth.relax(cells, protect=cells, forbid=banned) & banned)


def test_relax_of_nothing_is_nothing():
    assert smooth.relax(set(), rounds=3) == set()


def test_relax_rounds_zero_is_a_no_op():
    cells = _slab()
    assert smooth.relax(cells, rounds=0) == cells


def test_roughness_sees_a_spike_and_a_smooth_solid_does_not():
    smoothish = smooth.roughness(_slab(8, 8, 8))
    spiked = smooth.roughness(_slab(8, 8, 8) | {(4, 8 + k, 4) for k in range(3)})
    assert spiked["spikes"] > smoothish["spikes"], "a three-block pimple must register"


# ---------------------------------------------------------------- coat

def test_shade_paints_every_cell_from_the_ramp_and_nothing_else():
    cells = _slab(8, 8, 8)
    ramp = ["a", "b", "c", "d", "e"]
    got = coat.shade(cells, ramp, strength=1.0)
    assert set(got) <= cells
    assert set(got.values()) <= set(ramp), "shading may only use blocks from its ramp"
    assert len(got) > len(cells) * 0.5, "most of the solid should be painted"


def test_shade_lights_the_top_and_darkens_the_underside():
    """The whole point of `form`: a back is lit, a belly is not. If this inverts, every animal
    reads as lit from below and the rubric's shading trend goes negative."""
    cells = _slab(9, 9, 9)
    ramp = ["dark", "mid1", "mid2", "mid3", "light"]
    got = coat.shade(cells, ramp, strength=1.0, jitter=0.0)
    rank = {b: i for i, b in enumerate(ramp)}
    top = [rank[got[c]] for c in cells if c[1] == 8 and c in got]
    bottom = [rank[got[c]] for c in cells if c[1] == 0 and c in got]
    assert sum(top) / len(top) > sum(bottom) / len(bottom), "the sky-facing course must be lighter"


def test_shade_with_no_ramp_paints_nothing():
    assert coat.shade(_slab(), []) == {}


def test_voronoi_and_rosettes_stay_inside_the_skin():
    cells = _slab(10, 10, 10)
    for got in (coat.voronoi(cells, "patch", "grout", scale=4.0),
                coat.rosettes(cells, "ring", "ground", scale=4.0),
                coat.blotches(cells, "patch", "ground", scale=4.0)):
        assert set(got) <= cells, "a coat may only paint cells that exist"
        assert got, "a coat that paints nothing is not a coat"


def test_patterns_are_deterministic():
    """Same seed, same coat - or a design changes every time it is regenerated and `progress`
    reports the whole animal as a deviation."""
    cells = _slab(8, 8, 8)
    assert coat.blotches(cells, "p", "g", seed=3) == coat.blotches(cells, "p", "g", seed=3)
    assert coat.shade(cells, ["a", "b", "c"], seed=3) == coat.shade(cells, ["a", "b", "c"], seed=3)


def test_patch_scale_changes_the_pattern():
    cells = _slab(12, 12, 12)
    fine = coat.voronoi(cells, "p", "g", scale=3.0)
    coarse = coat.voronoi(cells, "p", "g", scale=9.0)
    assert fine != coarse, "patch_scale must actually reach the pattern"
