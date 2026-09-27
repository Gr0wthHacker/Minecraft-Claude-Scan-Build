"""`render3d` draws stairs and slabs at their REAL shape, and leans them the right way.

THIS EXISTS BECAUSE THE RENDERER COULD NOT SEE THE THING IT WAS BEING ASKED ABOUT. Jack, on the
frog's feet against his reference: *"this one had feet done by using stairs."* He was right - a
stair is what makes a toe taper to the ground instead of ending at a vertical face - and when the
feet were rebuilt with stairs, every 3-D sheet in the repo drew them as full cubes. The change was
unjudgeable, which is the same failure as rendering an animal orthographically along its own axis:
the tool cannot show the class of error being hunted.

CLAUDE.md said real block models "buy almost nothing for ANIMALS, which are near-100% full cubes".
That was true only while no animal used a shape block. The moment one did, it was wrong.

The stair convention is the load-bearing part and it is the one thing a picture cannot check: A
STAIR'S TALL SIDE IS ITS `facing`, settled off Jack's own flight and already pinned for the
BUILDER in `test_stairhead.py`. Until now the RENDERER drew both directions identically, so a
backwards flight and a correct one produced the same image. These tests are the other half.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import nbt, render3d as r3
from mcbuild.schem import Model


def _mask(name, **props):
    return r3._shape_mask(name, props)


def test_a_full_block_fills_all_eight():
    assert _mask("stone").sum() == 8
    assert _mask("jungle_planks").sum() == 8


def test_a_slab_fills_the_half_it_says():
    lo = _mask("stone_slab", type="bottom")
    hi = _mask("stone_slab", type="top")
    assert lo.sum() == hi.sum() == 4
    assert lo[0].all() and not lo[1].any(), "a bottom slab is not the LOWER half"
    assert hi[1].all() and not hi[0].any(), "a top slab is not the UPPER half"
    assert _mask("stone_slab", type="double").sum() == 8, "a double slab is a full block"


def test_a_stair_is_six_eighths_and_its_tall_side_is_its_facing():
    """The whole point. A stair is a slab plus a step, and the step is on the side the block
    FACES - which is what makes a flight walkable in the direction it was built for."""
    for facing, axis, idx in (("east", 2, 1), ("west", 2, 0),
                              ("south", 1, 1), ("north", 1, 0)):
        m = _mask("oak_stairs", facing=facing, half="bottom")
        assert m.sum() == 6, f"{facing}: a stair is six half-cells, got {m.sum()}"
        assert m[0].all(), f"{facing}: the lower half is not solid"
        top = m[1]
        want = np.zeros((2, 2), bool)
        if axis == 2:
            want[:, idx] = True
        else:
            want[idx, :] = True
        assert (top == want).all(), (
            f"{facing}: the step is on the wrong side - a stair's TALL side is its facing, and "
            f"drawn the other way a backwards flight renders identically to a correct one")


def test_an_upside_down_stair_is_the_same_shape_flipped():
    lo = _mask("oak_stairs", facing="east", half="bottom")
    hi = _mask("oak_stairs", facing="east", half="top")
    assert hi.sum() == 6
    assert (hi[::-1] == lo).all(), "half=top is not half=bottom mirrored in y"


def _model(entries, ids):
    return Model(np.array(ids, np.int32), [nbt.block_state(n, **p) for n, p in entries])


def test_subdivide_doubles_the_grid_and_removes_only_the_stair_quarter():
    m = _model([("air", {}), ("stone", {}), ("oak_stairs", {"facing": "east",
                                                            "half": "bottom"})],
               [[[0, 1, 2]]])                       # one air, one full block, one stair
    d = r3.subdivide(m)
    assert d.ids.shape == (2, 2, 6), f"the grid did not double: {d.ids.shape}"
    assert int(d.solid().sum()) == 8 + 6, "a full block is 8 half-cells and a stair is 6"


def test_subdivide_leaves_a_model_of_full_cubes_alone():
    """It is applied only where it changes something, so a build with no shape block must come
    out with exactly eight times the solid cells - otherwise every existing sheet in the repo
    would move for no reason."""
    m = _model([("air", {}), ("stone", {})], [[[0, 1, 1]]])
    assert not r3.has_shapes(m)
    assert int(r3.subdivide(m).solid().sum()) == 2 * 8


def test_has_shapes_ignores_a_double_slab():
    """A double slab IS a full block, so a model whose only 'shape' is one must not be
    subdivided - the cost and the finer AO would be bought for no change in the picture."""
    assert not r3.has_shapes(_model([("air", {}), ("stone_slab", {"type": "double"})],
                                    [[[0, 1]]]))
    assert r3.has_shapes(_model([("air", {}), ("stone_slab", {"type": "top"})], [[[0, 1]]]))


def test_the_frog_is_what_prompted_this_and_it_subdivides():
    from mcbuild import scan
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "out", "Lowland Frog.litematic")
    if not os.path.exists(path):
        import pytest
        pytest.skip("needs out/Lowland Frog.litematic")
    m = scan.load(path).model
    assert r3.has_shapes(m), "the frog's toes are supposed to be stairs"
    d = r3.subdivide(m)
    lost = int(m.solid().sum()) * 8 - int(d.solid().sum())
    assert lost > 0 and lost % 2 == 0, (
        f"every stair should lose exactly two half-cells; lost {lost}")
