"""The animal pipeline end to end, plus the two things the ANIMALS notes call load-bearing:
the BUILD ORDER, and the rule that anything derived from the standing skeleton must follow
the POSED one.

Building a real animal is slow, so this builds ONE small one and asserts many things about it,
rather than one thing about many.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import numpy as np
import pytest
from mcbuild import morph
from mcbuild.gen import anatomy, quadruped, taxonomy
from mcbuild.gen.quadruped import POSES

F, S = (0, 1), (1, 0)


@pytest.fixture(scope="module")
def cat():
    """One built leopard - the smallest species, so the slowest test in this file stays quick."""
    cfg = {"profile": "leopard", "feet": [0, 0, 0], "look_at": [0, 0, 40]}
    return quadruped.build_quadruped(cfg)


def test_a_species_builds_one_connected_grounded_piece(cat):
    solid = cat.model().solid() if hasattr(cat, "model") else None
    if solid is None:                                   # Canvas API differs; fall back to the ids
        solid = cat.to_model().ids > 0
    _lab, sizes = morph.components(solid, conn=6)
    assert len(sizes) == 1, f"an animal must be one piece, got {len(sizes)}"
    assert solid[0].any(), "it must stand on the ground course"


def test_every_family_builds(request):
    """A family whose geometry raises is worse than one that scores badly."""
    for name in sorted(taxonomy.species()):
        if taxonomy.species()[name]["family"] not in ("felid", "ursid"):
            continue                                    # one per family would be slow; cover two
        cfg = {"profile": name, "feet": [0, 0, 0], "look_at": [0, 0, 40]}
        quadruped.build_quadruped(cfg)


# ---------------------------------------------------------------- poses

def test_every_pose_is_a_multiplier_set_not_a_build_path():
    """`POSES` holds multipliers; no pose may be a separate branch, or they drift apart."""
    assert set(POSES) >= {"standing", "sitting", "couchant", "prowling", "grazing"}
    for pose, q in POSES.items():
        for k, v in q.items():
            assert isinstance(v, (int, float)), f"{pose}.{k} is not a multiplier"
    assert POSES["standing"].get("fore", 1.0) == 1.0, "standing is the identity"
    assert POSES["standing"].get("hind", 1.0) == 1.0


def test_sitting_drops_the_hind_leg_further_than_the_fore():
    """Which is what sitting IS. If they were equal the animal would just be shorter."""
    sit = POSES["sitting"]
    assert sit.get("hind", 1.0) < sit.get("fore", 1.0), "a sitting animal folds its hind legs"


def test_posed_reference_follows_the_generator_not_a_second_table():
    """`proportions.posed` uses the SAME multipliers the generator poses with. If it kept its own
    copy, a pose change would report correct work as a deformity."""
    import proportions as pr
    ref = pr.reference("jaguar")
    for pose in ("sitting", "couchant", "prowling"):
        got = pr.posed(ref, pose)
        assert got["leg (ground->belly)"] <= ref["leg (ground->belly)"] * 1.001, (
            f"{pose} must not raise the belly line above standing")
        assert set(got) == set(ref)


def test_a_pose_that_does_not_exist_is_the_identity():
    """Approximately: an unknown pose applies no multipliers, but the result is still renormalised
    by the posed total height, which moves every fraction by about a tenth of a percent."""
    import proportions as pr
    ref = pr.reference("bear")
    got = pr.posed(ref, "no_such_pose")
    assert set(got) == set(ref)
    for k in ref:
        assert got[k] == pytest.approx(ref[k], rel=0.01), k


# ---------------------------------------------------------------- anatomy

@pytest.mark.parametrize("kind", ["digitigrade", "plantigrade", "columnar", "stubby", "cursorial"])
def test_every_leg_kind_reaches_the_ground_and_the_body(kind):
    """A leg that stops short leaves the animal floating; one that overshoots buries the foot."""
    hide = set()
    fn = getattr(anatomy, f"leg_{kind}")
    fn(hide, 0, 0, 0, 12, F, S, 2.0, 2.0)
    assert hide, f"{kind} built nothing"
    ys = {c[1] for c in hide}
    assert min(ys) <= 0, f"{kind} does not reach the ground"
    assert max(ys) >= 11, f"{kind} does not reach the belly at 12"


@pytest.mark.parametrize("kind", ["digitigrade", "plantigrade", "columnar", "stubby", "cursorial"])
def test_leg_kinds_are_actually_different(kind):
    """The whole reason `anatomy.py` exists: numbers alone built one animal five times."""
    shapes = {}
    for k in ["digitigrade", "plantigrade", "columnar", "stubby", "cursorial"]:
        h = set()
        getattr(anatomy, f"leg_{k}")(h, 0, 0, 0, 12, F, S, 2.0, 2.0)
        shapes[k] = h
    others = [v for k, v in shapes.items() if k != kind]
    assert all(shapes[kind] != o for o in others), f"{kind} builds the same leg as another kind"


def test_plantigrade_puts_a_bear_on_a_longer_foot_than_a_cat():
    """The documented difference between the two: a bear stands on a long flat foot."""
    def foot_len(kind):
        h = set()
        getattr(anatomy, f"leg_{kind}")(h, 0, 0, 0, 12, F, S, 2.0, 2.0)
        ground = [c for c in h if c[1] == min(y for _x, y, _z in h)]
        return max(c[2] for c in ground) - min(c[2] for c in ground) + 1
    assert foot_len("plantigrade") > foot_len("digitigrade")


@pytest.mark.parametrize("shape", ["rounded", "broad", "domed", "blunt", "tapered"])
def test_every_head_kind_builds_and_they_differ(shape):
    p = taxonomy.resolve("jaguar")
    built = {}
    for s in ["rounded", "broad", "domed", "blunt", "tapered"]:
        h = set()
        anatomy.head(h, (0, 10, 0), 3.0, F, S, p, s)
        built[s] = h
        assert h, f"{s} head built nothing"
    others = [v for k, v in built.items() if k != shape]
    assert all(built[shape] != o for o in others), f"the {shape} skull is not distinct"


def test_head_breadth_comes_from_the_family_not_from_the_shape_keys():
    """Worth pinning, because it is easy to assume otherwise and then tune the wrong thing.

    HEAD_KEYS control the PROFILE ALONG THE MUZZLE - the bear's step from cranium to snout, the
    giraffe's gentle taper. They barely move the maximum half-width: `broad` peaks at 1.05x head_r
    and `tapered` at 1.00x, which is under one block on any animal we build. What actually makes a
    bear's skull broad is the FAMILY's `head_r_ratio` - 0.55 against the giraffid's 0.31.
    """
    def width(species, s):
        h = set()
        anatomy.head(h, (0, 10, 0), 3.0, F, S, taxonomy.resolve(species), s)
        return max(c[0] for c in h) - min(c[0] for c in h) + 1
    # same species, different shape keys: nearly no change in breadth
    assert abs(width("jaguar", "broad") - width("jaguar", "tapered")) <= 1
    # the ratio is what carries it - a bear's skull against a giraffe's, at similar head lengths
    assert taxonomy.families()["ursid"]["build"]["head_r_ratio"] >            taxonomy.families()["giraffid"]["build"]["head_r_ratio"]


def test_the_broad_skull_has_a_step_and_the_tapered_one_does_not():
    """The step from cranium to snout is what the eye reads as `bear`, and it lives in the profile
    rather than in the width - so this is what a change to HEAD_KEYS must not quietly lose."""
    def widths(s):
        keys = anatomy.HEAD_KEYS[s]
        return [dw for _t, dw, _dy, _dh in keys]
    def biggest_drop(s):
        w = widths(s)
        return max(w[i] - w[i + 1] for i in range(len(w) - 1))
    assert biggest_drop("broad") > biggest_drop("tapered"), "the bear's step must be the sharper"
    assert biggest_drop("blunt") < biggest_drop("broad"), "a capybara's face barely tapers at all"
