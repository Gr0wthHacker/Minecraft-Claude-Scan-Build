"""The analysis tools: scale, stance and compare.

These decide how big an animal is built, which pose it is built in, and whether it is a different
animal from its sibling. None of them was asserted, and all three are the kind of tool whose output
gets believed because it is printed as a number.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import numpy as np
import pytest
import compare
import scale
import stance
from mcbuild.gen import taxonomy


# ---------------------------------------------------------------- scale

def test_the_floor_is_min_blocks_over_the_reference_fraction():
    """The whole claim of the tool, restated: a feature that is a small fraction of its animal
    forces a big animal. If this drifts, every 'viable height' in the docs is wrong."""
    f = scale.floors("giraffe")
    # against the POSED reference - even `standing` renormalises by the posed total height, so the
    # raw table is about a tenth of a percent out and the identity looks broken when it is not
    ref = scale.posed(scale.reference("giraffe"), "standing")
    for k, h in f.items():
        assert h == pytest.approx(scale.MIN_BLOCKS[k] / ref[k]), k


def test_floors_come_back_largest_last():
    """`main` reads the binding feature off the end of the dict."""
    for sp in ("bear", "jaguar", "giraffe"):
        vals = list(scale.floors(sp).values())
        assert vals == sorted(vals), f"{sp} floors are not ordered"


def test_a_slender_feature_forces_a_bigger_animal_than_a_stout_one():
    """The documented headline: a giraffe's leg is 5% of its height so 3 blocks force 59 blocks of
    giraffe; a jaguar's is 13%, so the same leg forces 23."""
    assert max(scale.floors("giraffe").values()) > max(scale.floors("jaguar").values())


def test_the_binding_feature_is_the_one_with_the_smallest_fraction():
    f = scale.floors("giraffe")
    worst = list(f)[-1]
    ref = scale.posed(scale.reference("giraffe"), "standing")
    ratios = {k: scale.MIN_BLOCKS[k] / ref[k] for k in f}
    assert worst == max(ratios, key=ratios.get)


def test_pose_changes_the_floor():
    """A sitting animal's visible leg is shorter, so the height that leg forces is different."""
    assert scale.floors("jaguar", "sitting") != scale.floors("jaguar", "standing")


# ---------------------------------------------------------------- stance

def test_behaviour_reads_the_family_table():
    """A sitting giraffe is a sick animal, not a style choice - the number must come from the
    family, and a pose the family never takes must score near zero."""
    giraffid = taxonomy.pose_weights("giraffe")
    felid = taxonomy.pose_weights("jaguar")
    assert stance._behaviour(giraffid, "sitting") < stance._behaviour(felid, "sitting")
    assert stance._behaviour(giraffid, "standing") > stance._behaviour(giraffid, "couchant")


def test_an_unknown_pose_scores_a_neutral_half_not_a_zero_or_a_one():
    assert stance._behaviour({}, "anything") == 0.5


def test_legibility_falls_with_distance_and_rises_with_height():
    """Past about 30 blocks a couchant animal is a lump - that is the claim being pinned."""
    assert stance._legibility(30, 10) > stance._legibility(30, 60)
    assert stance._legibility(40, 30) > stance._legibility(10, 30)
    assert stance._legibility(10, 200) < 0.2, "a small animal far away must score badly"


def test_legibility_is_bounded():
    for h, d in [(1, 1000), (500, 1), (30, None), (0, 5)]:
        assert 0.0 <= stance._legibility(h, d) <= 1.0


def test_the_weights_sum_to_one():
    """Four factors that 'disagree often, which is the point' - but they must still be a mean."""
    assert sum(stance.WEIGHTS.values()) == pytest.approx(1.0)
    assert set(stance.WEIGHTS) == {"behaviour", "site", "legibility", "anatomy"}


# ---------------------------------------------------------------- compare

def _prof(h, d):
    """A profile as `rubric._profile` would return one, for a box h tall and d long."""
    import rubric
    s = np.zeros((h + 2, d + 2, 4), bool)
    s[0:h, 0:d, 1:3] = True
    return rubric._profile(s)


def test_identical_builds_measure_as_identical():
    a = (_prof(20, 30), ["stone"] * 10)
    assert compare._dist(a, a) == (pytest.approx(0.0), pytest.approx(0.0))


def test_shape_and_coat_are_measured_independently():
    """The reason they are printed apart: an animal carried entirely by paint must be visible
    as such, not averaged into a single passing number."""
    same_shape_new_coat = (_prof(20, 30), ["snow_block"] * 10)
    mine = (_prof(20, 30), ["mangrove_wood"] * 10)
    shape, coat = compare._dist(mine, same_shape_new_coat)
    assert shape == pytest.approx(0.0) and coat == pytest.approx(1.0)

    new_shape_same_coat = (_prof(30, 10), ["mangrove_wood"] * 10)
    shape, coat = compare._dist(mine, new_shape_same_coat)
    assert shape > 0.3 and coat == pytest.approx(0.0)


def test_coat_distance_is_bounded_and_symmetric():
    a = (_prof(20, 30), ["a"] * 6 + ["b"] * 4)
    b = (_prof(20, 30), ["b"] * 5 + ["c"] * 5)
    s1, c1 = compare._dist(a, b)
    s2, c2 = compare._dist(b, a)
    assert (s1, c1) == (pytest.approx(s2), pytest.approx(c2))
    assert 0.0 <= c1 <= 1.0


def test_the_same_shape_threshold_is_below_a_real_sibling_gap():
    """SAME is the line at which compare.py shouts. It has to sit under the gap two genuinely
    different species reach, or it fires on everything - and over the gap two identical ones
    reach, or it never fires at all."""
    assert 0.0 < compare.SAME < 0.2


# ---------------------------------------------------------------- views

def test_each_view_axis_renders_a_different_projection():
    """`face` looks from the FAR z end and `rear` from z=0. Getting these backwards means
    auditing an animal's backside, which the tool's own help warns about - so pin that they are
    genuinely different images rather than the same one relabelled."""
    import views
    ids = np.zeros((10, 14, 6), np.int32)
    ids[0:8, 2:12, 1:5] = 1
    ids[6:10, 10:14, 2:4] = 1                 # a head at the +z end, to break front/back symmetry
    cols = {0: (255, 255, 255), 1: (120, 90, 60)}
    sy, sz, sx = ids.shape
    got = {ax: views._render(ids, cols, 0, sy, sx, sz, ax, 2)
           for ax in ("side", "face", "rear", "top")}
    for ax, img in got.items():
        assert img.width > 0 and img.height > 0, ax
    assert got["face"].tobytes() != got["rear"].tobytes(), "face and rear must not be the same view"
    assert got["side"].tobytes() != got["top"].tobytes()


def test_zoom_scales_the_render():
    import views
    ids = np.zeros((6, 8, 4), np.int32)
    ids[0:5, 1:7, 1:3] = 1
    cols = {0: (255, 255, 255), 1: (10, 20, 30)}
    sy, sz, sx = ids.shape
    small = views._render(ids, cols, 0, sy, sx, sz, "side", 2)
    big = views._render(ids, cols, 0, sy, sx, sz, "side", 6)
    assert big.width == small.width * 3 and big.height == small.height * 3
