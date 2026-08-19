"""The rubric's two shared entry points, and the fake check that got past the last one.

`rubric.score` is called by tools/refine.py and `proportions.measure` by stance, refine and scale,
so an unasserted change here drifts silently through three tools each.

The regression that matters most: `silhouette`'s within-family half used to compare the two species'
YAML ENTRIES - the set of block names spelled in species.yaml - and never looked at the model. bear
and polar_bear scored "86% distinct" on identical statues because their coat blocks have different
names, and adding one key to a config raised the score without moving a block.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import numpy as np
import pytest
import rubric
import proportions as pr


def _box(h=20, d=30, w=8, y0=0):
    """A solid [y, z, x] block - the array layout Model.solid() returns."""
    s = np.zeros((h + y0 + 2, d + 4, w + 4), bool)
    s[y0:y0 + h, 2:2 + d, 2:2 + w] = True
    return s


# ---------------------------------------------------------------- the silhouette profile

def test_profile_is_scale_invariant():
    """A 20x30 box and a 40x60 box are the SAME SHAPE. If the profile disagrees, every
    within-family number is really just comparing sizes."""
    a = rubric._profile(_box(20, 30, 8))
    b = rubric._profile(_box(40, 60, 16))
    inter, union = np.minimum(a, b).sum(), np.maximum(a, b).sum()
    assert 1.0 - inter / union < 0.05, "same shape at two sizes must measure as the same shape"


def test_profile_separates_different_shapes():
    tall = rubric._profile(_box(40, 10, 8))
    long_ = rubric._profile(_box(10, 40, 8))
    inter, union = np.minimum(tall, long_).sum(), np.maximum(tall, long_).sum()
    assert 1.0 - inter / union > 0.4, "a tall box and a long box must not measure alike"


def test_profile_ignores_translation():
    a = rubric._profile(_box(20, 30, 8, y0=0))
    b = rubric._profile(_box(20, 30, 8, y0=9))
    assert np.array_equal(a, b), "the profile is of the bounding box, so position must not matter"


def test_profile_of_empty_is_empty():
    assert rubric._profile(np.zeros((5, 5, 5), bool)).sum() == 0


# ---------------------------------------------------------------- the coat mix

def test_palette_mix_is_a_distribution_and_drops_air():
    mix = rubric._palette_mix(["air", "stone", "stone", "dirt"])
    assert "air" not in mix
    assert mix["stone"] == pytest.approx(2 / 3)
    assert sum(mix.values()) == pytest.approx(1.0)


def test_palette_mix_of_nothing():
    assert rubric._palette_mix(["air", "air"]) == {}


# ---------------------------------------------------------------- within-family

def test_within_family_of_a_lone_species_is_not_a_free_pass_by_accident():
    sc, why = rubric._within_family(_box(), ["stone"], "x", [])
    assert sc == 1.0 and "only member" in why


def test_missing_sibling_builds_are_reported_not_scored_as_a_win(monkeypatch):
    """The whole failure being guarded against is a number that looks like proof and is not.
    A sibling that was never generated must not read as 'distinct'."""
    monkeypatch.setattr(rubric, "_sibling_build", lambda n: None)
    sc, why = rubric._within_family(_box(), ["stone"], "lion", ["jaguar", "leopard"])
    assert sc == 0.5, "an uncompared sibling must score neutral, not 1.0"
    assert "NO sibling build" in why and "not passed" in why


def test_within_family_reads_the_model_not_the_config(monkeypatch):
    """Two identical statues in identical blocks must measure as identical, whatever their
    configs say. This is the exact case the old config-text check scored 0.86."""
    twin = (rubric._profile(_box()), ["stone"] * 100)
    monkeypatch.setattr(rubric, "_sibling_build", lambda n: twin)
    sc, why = rubric._within_family(_box(), ["stone"] * 100, "polar_bear", ["bear"])
    assert sc == pytest.approx(0.0), "identical builds must not score as distinct"
    assert "SHAPE CARRIES NOTHING" in why


def test_within_family_credits_a_real_coat_difference(monkeypatch):
    """Same shape, completely different blocks - which is genuinely how you tell a polar bear
    from a brown one. It should score, and the detail must still show the shape carried nothing."""
    twin = (rubric._profile(_box()), ["snow_block"] * 100)
    monkeypatch.setattr(rubric, "_sibling_build", lambda n: twin)
    sc, why = rubric._within_family(_box(), ["mangrove_wood"] * 100, "polar_bear", ["bear"])
    assert sc == 1.0
    assert "SHAPE CARRIES NOTHING" in why, "a build carried purely by paint must say so"


def test_within_family_credits_a_real_shape_difference(monkeypatch):
    """Same blocks, different shape - a mane. This is what the lion's mane has to earn."""
    other = (rubric._profile(_box(10, 40, 8)), ["stone"] * 100)
    monkeypatch.setattr(rubric, "_sibling_build", lambda n: other)
    sc, why = rubric._within_family(_box(40, 10, 8), ["stone"] * 100, "lion", ["jaguar"])
    assert sc == 1.0 and "SHAPE CARRIES NOTHING" not in why


# ---------------------------------------------------------------- score() as a whole

def test_score_returns_every_weighted_dimension():
    solid = _box()
    names = ["air", "stone"]
    total, dims = rubric.score(solid, names, {}, "bear", "standing")
    spec_w = rubric.yaml.safe_load(rubric.RUBRIC.read_text(encoding="utf-8"))["weights"]
    assert set(dims) == set(spec_w), "a dimension without a weight silently vanishes from the total"
    assert sum(spec_w.values()) == pytest.approx(1.0), "weights must sum to 1 or grades are meaningless"
    assert 0.0 <= total <= 1.0
    for k, (v, detail) in dims.items():
        assert 0.0 <= v <= 1.0, f"{k} out of range"
        assert detail, f"{k} must explain itself"


def test_score_total_is_the_weighted_sum():
    solid = _box()
    total, dims = rubric.score(solid, ["air", "stone"], {}, "bear", "standing")
    w = rubric.yaml.safe_load(rubric.RUBRIC.read_text(encoding="utf-8"))["weights"]
    assert total == pytest.approx(sum(w[k] * v[0] for k, v in dims.items()))


# ---------------------------------------------------------------- proportions.measure

def _beast(H):
    """A crude quadruped, scaled entirely off H: four legs, a barrel, a narrow neck and a head.

    Every part earns its place in `_segment`. A solid box has no belly line, so the leg measures one
    course; a barrel on legs with nothing above it never narrows, so the withers fall back to
    belly+1 and the body measures one course deep. The neck has to be NARROWER than the barrel and
    the head has to SWELL along the body axis, because that is exactly what the segmenter looks for.
    """
    leg, depth = int(H * 0.40), int(H * 0.30)
    length, width, legw = int(H * 1.10), int(H * 0.30), max(2, int(H * 0.10))
    neck_w, neck_h = max(1, width // 3), int(H * 0.12)
    s = np.zeros((H + 2, length + 4, width + 4), bool)
    s[leg:leg + depth, 2:2 + length, 2:2 + width] = True                  # barrel
    for z0 in (2, 2 + length - legw):                                     # fore and hind legs
        s[0:leg, z0:z0 + legw, 2:2 + legw] = True
        s[0:leg, z0:z0 + legw, 2 + width - legw:2 + width] = True
    top = leg + depth
    nz, nx = 2 + length - neck_w - 1, 2 + (width - neck_w) // 2
    s[top:top + neck_h, nz:nz + neck_w, nx:nx + neck_w] = True            # neck, narrower
    hz, hl = max(2, nz - int(H * 0.10)), int(H * 0.22)                    # head, swelling in z
    s[top + neck_h:top + neck_h + max(2, int(H * 0.12)),
      hz:hz + hl, nx:nx + neck_w] = True
    return s


def test_measure_is_scale_invariant():
    """Proportions are FRACTIONS of height, so doubling the animal must not move them."""
    small = pr.measure(_beast(20), {}, 20)
    big = pr.measure(_beast(40), {}, 40)
    shared = [k for k in set(small) & set(big) if small[k]]
    assert shared, "nothing measured to compare"
    for k in shared:
        assert abs(big[k] - small[k]) / small[k] < 0.15, f"{k} moved with scale: {small[k]} -> {big[k]}"


def test_measure_finds_the_parts_it_can_get_from_shape_alone():
    """Belly, withers, depth and width are found from the COURSE PROFILE, so a bare solid is
    enough for them. These are the measures that must never need the generator's help."""
    got = pr.measure(_beast(30), {}, 30)
    for k in ("leg (ground->belly)", "body depth", "body width", "withers height"):
        assert got.get(k, 0) > 0, f"{k} not measured from shape"
    assert 0.2 < got["leg (ground->belly)"] < 0.6, f"leg clearance {got['leg (ground->belly)']}"
    assert got["withers height"] > got["leg (ground->belly)"], "the back is above the belly"


def test_length_measures_need_recorded_landmarks():
    """`body length` and `head length` come from the `along` windows the generator records, because
    on a cat the head sits at body height and no shape rule separates them. Without landmarks they
    report 0 - which is the honest answer, and worth pinning so it stays honest rather than
    becoming a guess."""
    got = pr.measure(_beast(30), {}, 30)
    assert got["body length"] == 0
    assert got["head length"] == 0


def test_reference_and_posed_agree_on_keys():
    ref = pr.reference("bear")
    assert ref, "no reference for bear"
    for pose in ("standing", "sitting", "couchant"):
        assert set(pr.posed(ref, pose)) == set(ref), f"{pose} changed which measures exist"


def test_posed_standing_is_the_identity():
    ref = pr.reference("jaguar")
    assert pr.posed(ref, "standing") == ref


# ---------------------------------------------------------------- the pose-aware feature floor

def test_the_feature_floor_follows_the_pose():
    """A sitting animal's belly is ON THE GROUND - that is what sitting is. Measuring its leg
    clearance against a STANDING floor of 4 blocks failed the gate on every sitting or couchant
    build, including the pose the ursid family likes best. Every other measure in the rubric is
    pose-adjusted; this one was not."""
    import scale
    std = pr.reference("bear")
    sit = pr.posed(std, "sitting")
    assert sit["leg (ground->belly)"] < std["leg (ground->belly)"], "sitting must shorten the leg"
    ratio = sit["leg (ground->belly)"] / std["leg (ground->belly)"]
    assert ratio < 0.6, "if sitting barely shortens the leg this test proves nothing"
    # the floor the gate applies must fall by the same ratio, and never below 1
    floor = max(1.0, scale.MIN_BLOCKS["leg (ground->belly)"] * min(1.0, ratio))
    assert floor < scale.MIN_BLOCKS["leg (ground->belly)"]
    assert floor >= 1.0


def test_a_standing_animal_keeps_the_full_floor():
    """The relaxation must not quietly let a badly-built STANDING animal through."""
    import scale
    std = pr.reference("bear")
    same = pr.posed(std, "standing")
    r = same["leg (ground->belly)"] / std["leg (ground->belly)"]
    assert min(1.0, r) == pytest.approx(1.0, abs=0.02), "standing must not scale the floor down"
