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


# ---------------------------------------------------------------- pose-aware reference

def _meta(**over):
    m = {"origin": {"x": 0, "y": 0, "z": 0}, "feet": [5, 3, 5], "facing": [0, 1],
         "anat_top_y": 23, "belly_y": 8, "back_y": 16, "rump_y": 8, "chest_y": 8,
         "neck_top_y": 18, "shoulder_at": [5, 16, 8], "neck_top_at": [5, 18, 12],
         "along": {"body": [-10, 10], "head": [10, 16]}, "features_built": {}}
    m.update(over)
    return m


def test_designed_reads_the_generators_own_intent():
    """The audit must not re-derive what a pose does. A parallel first-order model was out by 3x
    on a folded limb and 1.9x on a dropped neck, and it was biased per FAMILY besides."""
    assert pr.designed({}) == {}
    assert pr.designed({"designed": {}}) == {}
    got = pr.designed({"designed": {"body length": 1.25, "leg width": 0.1, "junk": "x"}})
    assert got == {"body length": 1.25, "leg width": 0.1}, "non-numeric entries must be dropped"


def test_a_freshly_built_animal_records_what_it_intended():
    """Builds made BEFORE the generator recorded its intent fall back to `posed()`, which is why
    that model is kept - so this checks a fresh build rather than everything in `out/`."""
    from mcbuild.gen import quadruped
    c = quadruped.build_quadruped({"profile": "bear", "pose": "couchant",
                                   "feet": [0, 0, 0], "look_at": [0, 0, 40]})
    d = (c.meta or {}).get("designed")
    assert d, "the generator must state its own intent"
    for k in ("body length", "leg width", "withers height", "body depth", "neck length"):
        assert k in d and d[k] > 0, k


def test_the_old_model_is_still_there_for_builds_that_predate_this():
    """`designed()` returning nothing must fall through, not crash - `out/` holds older animals."""
    assert pr.designed({"kind": "bear"}) == {}
    assert pr.posed(pr.reference("bear"), "couchant"), "the fallback must still produce a reference"


def test_verticals_are_measured_from_the_FEET_not_the_model_origin():
    """Legs seek their own ground, so on rolling terrain the downhill limbs reach BELOW the nominal
    feet and the model's origin sits under them. Measuring from the origin compared two different
    zeroes and inflated every vertical - while the horizontals matched exactly, which is the tell."""
    solid = _beast(20)
    flat = pr.measure(solid, _meta(feet=[5, 0, 5], origin={"x": 0, "y": 0, "z": 0}), 20)
    # same model, but its origin recorded 3 blocks BELOW the feet
    sunk = pr.measure(solid, _meta(feet=[5, 3, 5], origin={"x": 0, "y": 0, "z": 0}), 20)
    assert sunk["leg (ground->belly)"] < flat["leg (ground->belly)"], (
        "a lower origin must not inflate the leg clearance")


def test_tilt_slack_has_a_fold_term_as_well_as_a_tilt_term():
    """Couchant folds BOTH legs almost equally, so a slack built only on the fore/hind difference
    saw 0.09 and allowed 34% where the build was 46-60% off - every couchant animal was marked
    deformed for lying down correctly."""
    assert pr.tilt_slack("standing") == 0.0, "standing must get no slack at all"
    assert pr.tilt_slack("couchant") > 0.4, "a folded pose needs real slack"
    assert pr.tilt_slack("sitting") > 0.4
    assert pr.tilt_slack("couchant") > pr.tilt_slack("prowling"), "more folded, more slack"
    for p in ("standing", "sitting", "couchant", "prowling", "grazing"):
        assert 0.0 <= pr.tilt_slack(p) <= 0.55, p


def test_leg_width_is_omitted_when_the_pose_leaves_no_band_to_measure():
    """A couchant animal's floor is two courses up, so the window that should hold only legs holds
    the barrel too. Reporting a number there gave 2.6-3.2x the leg that was asked for."""
    tall = pr.measure(_beast(30), _meta(rump_y=9, chest_y=9), 30)
    assert "leg width" in tall, "a standing animal's leg IS measurable"
    flat = pr.measure(_beast(30), _meta(rump_y=1, chest_y=1), 30)
    assert "leg width" not in flat, "an unmeasurable leg must be absent, not zero"


def test_proportion_skips_measures_the_pose_cannot_yield():
    """An absent measure must not score as 100% out of tolerance."""
    solid = _beast(30)
    m = _meta(rump_y=1, chest_y=1, designed={"body length": 0.7, "leg width": 0.1})
    _score, detail = rubric._proportion(None, solid, m, "bear", "couchant")
    # the DENOMINATOR is the point: one of the two measures could not be taken, so the dimension is
    # scored out of the one that could, not out of both with the other counted as a failure.
    assert "/1 measures" in detail, detail
    assert "1 not measurable in this pose" in detail, detail


def test_a_mane_does_not_get_measured_as_back():
    """A lion's mane is a 1000-cell ball centred over the withers. Taking the greater of shape and
    design measured mane and called the barrel 50% too deep."""
    solid = _beast(30)
    plain = pr.measure(solid, _meta(), 30)
    maned = pr.measure(solid, _meta(features_built={"mane": 900}), 30)
    assert maned["withers height"] <= plain["withers height"] + 1e-9, (
        "with a ruff recorded, the withers must fall back to the designed back line")
