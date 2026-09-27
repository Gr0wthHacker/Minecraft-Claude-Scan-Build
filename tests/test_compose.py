"""A lot is a place, so a lot may be several generators - merged without losing a decision."""
import pytest

from mcbuild import compose
from mcbuild.gen import GENERATORS
from mcbuild.gen.canvas import Canvas


def _one(block="minecraft:stone", size=(2, 2, 2), **props):
    c = Canvas(*size)
    blk = c.state(block, **props)
    for x in range(size[0]):
        for y in range(size[1]):
            for z in range(size[2]):
                c.put(x, y, z, blk)
    return c


def test_a_merge_places_every_cell_of_every_part():
    a, b = _one(), _one()
    merged = compose.merge([(a, (0, 0, 0)), (b, (0, 0, 5))])
    assert int(merged.to_model().solid().sum()) == 16
    assert merged.meta["contested_cells"] == 0


def test_block_state_is_carried_and_never_re_derived():
    """A stair's facing and a sign's facing are DECISIONS, and this renderer draws a wrong one
    identically to a right one. A merge that dropped Properties would look correct in every
    sheet in this repo and be wrong in game."""
    a = _one("minecraft:stone_brick_stairs", facing="east", half="bottom")
    b = _one("minecraft:stone_brick_stairs", facing="west", half="top")
    merged = compose.merge([(a, (0, 0, 0)), (b, (0, 0, 5))])
    model = merged.to_model()
    assert model.props_at(0, 0, 0)["facing"] == "east"
    assert model.props_at(0, 0, 5)["facing"] == "west"
    assert model.props_at(0, 0, 5)["half"] == "top"


def test_the_first_writer_wins_and_the_contest_is_counted_not_hidden():
    a, b = _one("minecraft:stone"), _one("minecraft:cobblestone")
    merged = compose.merge([(a, (0, 0, 0)), (b, (0, 0, 0))])
    assert merged.to_model().name_at(0, 0, 0) == "minecraft:stone"
    assert merged.meta["contested_cells"] == 8


def test_a_negative_offset_shifts_the_result_to_its_own_origin():
    a, b = _one(), _one()
    merged = compose.merge([(a, (0, 0, 0)), (b, (-4, 0, 0))])
    model = merged.to_model()
    assert model.ids.shape[2] == 6  # -4..1 inclusive
    assert int(model.solid().sum()) == 16


def test_sign_text_only_survives_where_its_sign_block_did():
    """A tile entity with no block is a corrupt region, not a lost line."""
    a = _one("minecraft:oak_sign", size=(1, 1, 1))
    a.sign_text(0, 0, 0, front=["KEEP"])
    b = _one("minecraft:stone", size=(1, 1, 1))
    b.sign_text(0, 0, 0, front=["LOSE"])
    merged = compose.merge([(a, (0, 0, 0)), (b, (0, 0, 0))])
    assert [t["front"][0] for t in merged.tiles.values()] == ['{"text": "KEEP"}']


def test_the_generator_entry_point_builds_declared_parts_in_order():
    canvas = GENERATORS["compose"].build({"parts": [
        {"gen": "park", "params": {"kind": "plaza", "land": "midway", "at": [0, 0, 0],
                                   "facing": "east", "width": 20, "depth": 20}, "offset": [0, 0, 0]},
        {"gen": "park", "params": {"kind": "booth", "land": "midway", "at": [0, 0, 0],
                                   "facing": "east"}, "offset": [2, 0, 2]},
    ]}, None)
    assert canvas.meta["part_generators"] == ["park", "park"]
    assert int(canvas.to_model().solid().sum()) > 0


@pytest.mark.parametrize("params, message", [
    ({}, "parts"),
    ({"parts": [{"gen": "nope", "params": {}}]}, "unknown generator"),
    ({"parts": [{"gen": "park", "params": {}, "offset": [0, 0]}]}, "offset"),
])
def test_a_malformed_composition_says_so_rather_than_building_nothing(params, message):
    with pytest.raises(ValueError, match=message):
        GENERATORS["compose"].build(params, None)
