"""The Diggings, against the one thing it must not lose: the walk the module it replaced carried.

`Park Ways` paves 0 of this lot's 2,438 columns, so the route from the spine to Mining Square
lived entirely inside `Boomtown Spine`. Retiring that module without carrying its boardwalk would
cut the Frontier in half, and it is not a fault any render, audit or BOM can see - a trail with a
pine standing in it draws exactly like a trail.
"""
from __future__ import annotations

import os

import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import diggings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "pf_frontier_diggings.yaml")

#: A guest walks THROUGH these. `PASSABLE IS NOT EMPTY` and the converse has bitten this repo
#: twice, so the trail test names what may stand in a walk rather than demanding bare air.
PASSABLE = {"air", "rail", "ochre_froglight", "moss_carpet"}


@pytest.fixture(scope="module")
def cfg():
    with open(CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def built(cfg):
    canvas = diggings.build(cfg["params"])
    return canvas, canvas.to_model()


def test_every_material_is_legal_spendable_and_not_expensive():
    """Rule 16: real, in 1.19, and still CURRENCY here is three different questions."""
    for key, name in diggings.SHOP.items():
        assert blocks.exists(name), f"{key} -> {name} is not a block"
        assert blocks.spendable(name), f"{key} -> {name} is currency on this server"
        assert palette.tier(name) in ("cheap", "ok"), f"{key} -> {name} is {palette.tier(name)}"


def test_THE_TRAIL_IS_WALKABLE_END_TO_END(built, cfg):
    """**THE ASSERTION THIS FILE EXISTS FOR.** The old module's boardwalk was the land's only walk
    from the spine to Mining Square, and this trail is laid on the same courses. Two pines were
    sited by hand at u20 and u22 during the build and put twenty-four cells of trunk and canopy
    straight into it - so the lane is stated and REFUSED now rather than remembered, and this is
    what proves the refusal fired.
    """
    canvas, _model = built
    tu0, tu1 = canvas.meta["parts"]["trail"]["u"]
    for v in range(canvas.sx):
        for u in range(tu0, tu1 + 1):
            assert canvas.solid(v, 0, u), f"the trail has no floor at ({v},{u})"
            for y in (1, 2):
                name = canvas.get_name(v, y, u).split(":")[-1]
                assert name in PASSABLE, f"the trail is blocked by {name} at ({v},{y},{u})"


def test_the_trail_runs_the_whole_length_of_the_lot(built, cfg):
    """Both ends have to land on paving that already exists - the ground layer's spur in the west
    and the V77-79 cross walk in the east - so a trail that stops short is a route that stops."""
    canvas, _model = built
    tu0, tu1 = canvas.meta["parts"]["trail"]["u"]
    for v in (0, canvas.sx - 1):
        assert any(canvas.solid(v, 0, u) for u in range(tu0, tu1 + 1)), \
            f"the trail does not reach the lot's edge at V{v}"


def test_the_trail_sits_where_the_old_boardwalk_sat(cfg):
    """World U68-70. Measured, not chosen: it is where `Park Ways` lays its spur to, and moving it
    would leave the ground layer's own paving pointing at a bank."""
    p = cfg["params"]
    u0 = int(p["at"][1]) + int(p["trail_u"])
    assert (u0, u0 + int(p["trail_w"]) - 1) == (68, 70), \
        f"the trail is at world U{u0}, and the spur it must meet lands on U68-70"


def test_the_banks_never_wall_a_cross_avenue(built):
    """This block is bounded north and south by the land's two cross avenues. The field falls to
    the lot's own edges for exactly that reason, and this is the assertion that it still does."""
    canvas, _model = built
    for u in (0, canvas.sz - 1):
        for v in range(canvas.sx):
            tall = sum(1 for y in range(canvas.sy) if canvas.solid(v, y, u))
            assert tall <= 2, f"the bank stands {tall} courses tall on the lot's own edge at V{v}"


def test_BOTH_SHOPS_ARE_CUT_IN_AND_NAMED(built):
    """**INTEGRATED MEANS DUG IN, NOT STOOD NEXT TO** - a hut on the lawn beside a spoil heap is an
    eighth false front. So each shop must have rock over its lintel, and it must be NAMED: the
    first build reserved one cell too far forward, buried the name board in the bank, and
    `_Lot.sign` refused it - a MISSING sign rather than a floating one, which is exactly why the
    count is returned and asserted.
    """
    canvas, _model = built
    shops = canvas.meta["parts"]["shops"]
    assert len(shops) == 2, f"the brief asked for one or two shops; this has {len(shops)}"
    for shop in shops:
        assert shop["signed"], f"the shop at {shop['at']} has no name board"
        v, u = shop["at"]
        # THE COVER IS THE TWO COURSES OVER THE ROOM'S OWN CEILING, not everything above it: the
        # reserve forces the field to ceiling + 3, so cells above that are open air by design.
        ceil = shop.get("height", 4)
        over = sum(1 for y in range(ceil + 1, ceil + 3)
                   if canvas.solid(v + shop["w"] // 2, y, u + shop["side"] * 2))
        assert over >= 1, f"the shop at {shop['at']} has no rock over it - it is a hut, not a cut"


def test_the_shops_do_not_face_each_other_across_the_trail(built):
    canvas, _model = built
    a, b = canvas.meta["parts"]["shops"]
    assert a["side"] != b["side"], "both shops are on the same bank"
    assert abs(a["at"][0] - b["at"][0]) >= 10, \
        "the two shopfronts stare at each other across the trail"


def test_the_workings_refuse_the_walk_rather_than_remembering_it(built):
    """A prop sited by hand near a way will eventually be sited IN it. This is the third time this
    land has needed the rule - a timber set stood on the coaster's rail, an adit's cross-cut post
    bricked up its own corridor - and the count of refusals is what proves the guard is live."""
    canvas, _model = built
    w = canvas.meta["parts"]["workings"]
    assert "refused" in w, "the workings do not check the lane at all"
    assert w["shaft"] >= 1 and w["pine"] >= 4, f"the diggings has almost nothing in it: {w}"


def test_gravel_is_only_ever_a_crust(built):
    """Rule 13: a falling block may not be used with air under it."""
    canvas, _model = built
    for v in range(canvas.sx):
        for u in range(canvas.sz):
            for y in range(canvas.sy):
                if canvas.get_name(v, y, u).split(":")[-1] != "gravel":
                    continue
                assert y == 0 or canvas.solid(v, y - 1, u), \
                    f"gravel at ({v},{y},{u}) has air under it"


def test_it_is_a_landscape_and_not_a_seventh_building(built):
    """The complaint this replaces was seven false fronts. Rock and ground must dominate what is
    placed, or the shops have quietly become the module again."""
    canvas, model = built
    names = [n.split("[")[0].split(":")[-1] for n in model.names]
    total = int(model.solid().sum())
    timber = 0
    for i, n in enumerate(names):
        if n.startswith("spruce") or n in ("red_wool", "white_wool", "glass_pane"):
            timber += int((model.ids == i).sum())
    assert timber < 0.30 * total, \
        f"{timber} of {total} cells are building materials - this is a building again"


def test_nothing_is_built_outside_the_lot(built):
    canvas, _model = built
    assert canvas.meta["refused"] == 0
