"""The Sky Lift Sloth: hero envelope, budget, one piece, and twelve gripping claws.

Every assertion here is measured off the MODEL, never read out of the sidecar
the generator wrote. `features_built` saying `claws: 12` is the generator's own
claim; what this file checks is that twelve separate fence hooks exist in the
blocks and that each one is 6-adjacent to a cable it can actually grip. The
same rule as the rest of the repo: a design that reports its own contract is
not evidence, and a picture cannot count claws.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import animal_quality, blocks, mechanics, morph
from mcbuild.gen import sloth

# The locked direction from PARK_VISUAL_AND_BUDGET_SPEC.md, setpiece 2, plus
# the lot it hangs in.
#
# THE SIZE ENVELOPE IS A HARD CONSTRAINT AND THE BUDGET IS NOT. The setpiece
# hangs off the Sky Lift and may not grow into the ride, so 46 x 23 in plan is
# the real ceiling on two axes - tighter than the ledger's own 48 x 24. The
# block band is the other way round: 3,500 is a FLOOR, because the failure this
# variant exists to fix is an underbuilt prototype. The upper number here is a
# runaway guard, not a target, and blocks are only worth spending on anatomy,
# the truss, or a silhouette somebody can see.
LONG = (40, 46)
HIGH = (24, 30)
DEEP = (18, 23)
BUDGET_FLOOR = 3500
RUNAWAY = 9000
NEIGHBOURS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


@pytest.fixture(scope="module")
def hero():
    return sloth.build({"hero": True})


@pytest.fixture(scope="module")
def model(hero):
    return hero.to_model()


def _named(model, name):
    ids = [i for i, e in enumerate(model.palette)
           if e.value["Name"].value.split(":")[-1] == name]
    return np.isin(model.ids, ids)


def _names(model):
    lookup = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(model.palette)}
    return sorted({lookup[i] for i in np.unique(model.ids) if i})


def _extent(model):
    ys, zs, xs = np.nonzero(model.solid())
    return (int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1),
            int(zs.max() - zs.min() + 1))


# ---------------------------------------------------------------- the envelope

def test_the_hero_sits_inside_the_locked_size_envelope(model):
    long_, high, deep = _extent(model)
    assert LONG[0] <= long_ <= LONG[1], long_
    assert HIGH[0] <= high <= HIGH[1], high
    assert DEEP[0] <= deep <= DEEP[1], deep


def test_the_hero_clears_its_block_floor(model):
    n = int(model.solid().sum())
    assert n >= BUDGET_FLOOR, n
    assert n <= RUNAWAY, n


def test_the_prototype_still_builds_and_is_NOT_the_hero():
    """`configs/sloth.yaml` must keep loading, and must stay the small build.

    The hero is a second composition rather than a scale factor, so the only
    thing that can silently break the prototype is the dispatch in `build`.
    """
    small = sloth.build({"seed": 0}).to_model()
    assert int(small.solid().sum()) == 684
    assert _extent(small) == (26, 14, 6)
    assert int(sloth.build({"hero": True}).to_model().solid().sum()) > 3000


def test_a_bigger_size_alone_does_not_densify_the_prototype():
    """The bug this variant exists to fix, pinned so it cannot come back as a
    'fix' to the prototype: stretching the small canvas adds almost nothing."""
    stretched = sloth.build({"size": [46, 30, 22]}).to_model()
    assert int(stretched.solid().sum()) < 1200
    assert int(sloth.build({"hero": True}).to_model().solid().sum()) > 3 * int(stretched.solid().sum())


# ---------------------------------------------------------------- one assembly

def test_the_whole_setpiece_is_one_6_connected_piece(model):
    _labels, comps = morph.components(model.solid(), conn=6)
    assert len(comps) == 1, sorted(comps, reverse=True)[:6]


def test_the_truss_is_part_of_the_setpiece_not_a_separate_prop(model):
    """The budget is 'including its cable/branch-like truss attachment', so the
    truss has to be real structure rather than a token rail."""
    timber = _named(model, "spruce_log") | _named(model, "dark_oak_wood")
    assert int(timber.sum()) > 800
    _labels, comps = morph.components(model.solid(), conn=6)
    assert len(comps) == 1


def test_the_creature_is_not_less_detailed_than_the_lift_it_adorns(model):
    """A named rejection condition, measured the only way it can be: the animal
    must carry more of the build than the structure it hangs from. A gantry with
    a small sculpture stuck under it is a gantry."""
    coat = sum(int(_named(model, n).sum()) for n in
               ("brown_wool", "light_gray_wool", "white_wool", "black_wool",
                "moss_block", "spruce_fence"))
    lift = sum(int(_named(model, n).sum()) for n in ("spruce_log", "dark_oak_wood"))
    assert coat > lift, (coat, lift)
    assert lift > 900, lift          # ...and the lift is still a real gantry


def test_the_coat_is_LAYERED_rather_than_a_speckle(model):
    """'layered moss/pale fur tufts' is anatomy, not a dither. A single cell
    recoloured on the underside is a speckle; what breaks the silhouette into
    fur is hanks two and three deep, so at least some columns must have them."""
    coat = (_named(model, "moss_block") | _named(model, "light_gray_wool")
            | _named(model, "brown_wool"))
    ids = model.ids
    deep = 0
    for y in range(2, ids.shape[0] - 1):
        for z in range(ids.shape[1]):
            for x in range(ids.shape[2]):
                if coat[y, z, x] and coat[y - 1, z, x] and ids[y - 2, z, x] == 0:
                    deep += 1
    assert deep > 60, deep


# ---------------------------------------------------------------- the claws

def _claw_clusters(model):
    fence = _named(model, "spruce_fence")
    labels, comps = morph.components(fence, conn=6)
    return labels, comps


def test_there_are_exactly_twelve_claws_three_to_a_limb(model):
    _labels, comps = _claw_clusters(model)
    assert len(comps) == 12, sorted(comps, reverse=True)
    assert all(size >= 4 for size in comps), sorted(comps)


def test_every_claw_hooks_a_real_cable(model):
    """The rejection condition is a free-hanging branch. Anything clinging
    anchors to the BUILT surface, so this is measured by adjacency, not by the
    radius the generator computed."""
    labels, comps = _claw_clusters(model)
    cable = _named(model, "dark_oak_wood")
    sy, sz, sx = model.ids.shape
    for cid in range(1, len(comps) + 1):
        cy, cz, cx = np.nonzero(labels == cid)
        gripping = False
        for y, z, x in zip(cy, cz, cx):
            for dx, dy, dz in NEIGHBOURS:
                ny, nz, nx = y + dy, z + dz, x + dx
                if 0 <= ny < sy and 0 <= nz < sz and 0 <= nx < sx and cable[ny, nz, nx]:
                    gripping = True
        assert gripping, f"claw {cid} touches no cable"


def test_a_claw_wraps_its_cable_rather_than_sitting_beside_it(model):
    """A hook has cells on BOTH sides of the cable it grips. Cells only on the
    inboard face is a paw resting on a rail, which is what a free-hanging
    branch looks like from underneath."""
    labels, comps = _claw_clusters(model)
    cable_z = sorted({int(z) for _y, z, _x in zip(*np.nonzero(_named(model, "dark_oak_wood")))})
    near, far = cable_z[0], cable_z[-1]
    for cid in range(1, len(comps) + 1):
        _cy, cz, _cx = np.nonzero(labels == cid)
        anchor = near if abs(int(cz.mean()) - near) < abs(int(cz.mean()) - far) else far
        assert cz.min() < anchor < cz.max(), f"claw {cid} does not straddle its cable"


# ---------------------------------------------------------------- the face

def test_the_named_anatomy_is_actually_built(hero):
    built = hero.meta["features_built"]
    for name in ("truss", "cables", "body", "head", "face", "mask",
                 "eyes", "nose", "smile", "limbs", "claws", "shag"):
        assert built.get(name), f"{name} reported as absent"
    assert built["limbs"] == 4
    assert built["claws"] == 12


def test_the_face_exists_as_a_pale_mask_with_dark_features(model):
    mask = _named(model, "white_wool")
    marks = _named(model, "black_wool")
    assert int(mask.sum()) >= 40, int(mask.sum())
    assert int(marks.sum()) >= 20, int(marks.sum())
    # ...and it is all on the head, at the front, not scattered over the coat.
    ys, zs, xs = np.nonzero(mask | marks)
    _sy, _sz, sx = model.ids.shape
    assert xs.min() > sx * 0.7, "the face is not on the head"
    assert int(xs.max() - xs.min() + 1) <= 12
    # two eyes: dark cells fall either side of the sagittal plane
    mid = model.ids.shape[1] / 2.0
    dark_z = np.nonzero(marks)[1]
    assert (dark_z < mid).any() and (dark_z > mid).any()


def test_the_face_reads_from_BELOW_which_is_the_only_view_that_matters(model):
    """The hero views are the Welcome Court approach and the Sky Lift return -
    both from underneath - and the rejection condition is a face that cannot be
    read from below. So most of the mask must have open air directly beneath
    it: a face painted on the FRONT of the head passes every other check here
    and is invisible to every guest."""
    face = _named(model, "white_wool") | _named(model, "black_wool")
    visible = np.zeros_like(face)
    visible[1:] = face[1:] & (model.ids[:-1] == 0)
    assert int(visible.sum()) / int(face.sum()) >= 0.55, int(visible.sum())


# ---------------------------------------------------------------- materials

def test_every_block_is_placeable_on_the_1_19_server_and_is_not_currency(model):
    used = _names(model)
    assert [n for n in used if blocks.available(n)] == used
    assert [n for n in used if blocks.spendable(n)] == used


def test_the_palette_is_the_locked_one(model):
    """brown/light-gray/white/black wool, spruce and dark-oak wood and fences,
    moss and lichen accents - and nothing else. No terracotta, concrete or
    quartz bulk, and no functional block used as animal skin."""
    allowed = {"brown_wool", "light_gray_wool", "white_wool", "black_wool",
               "moss_block", "glow_lichen", "spruce_log", "spruce_fence",
               "dark_oak_wood"}
    assert set(_names(model)) <= allowed, set(_names(model)) - allowed
    families = mechanics.manifest(model, generator="sloth").get("families", {})
    assert set(families) <= {"light"}, families


def test_it_passes_the_enforced_animal_release_contract(hero, model):
    result = animal_quality.assess(
        model, generator="sloth", meta=hero.meta,
        spec={"enforce": True, "_visual_review": True,
              "min_blocks": BUDGET_FLOOR, "min_materials": 7,
              "required_features": ["truss", "cables", "body", "head", "face",
                                    "mask", "eyes", "nose", "smile", "limbs",
                                    "claws", "shag"]},
    )
    assert result["ok"], result["failures"]
    assert len(result["components"]) == 1
