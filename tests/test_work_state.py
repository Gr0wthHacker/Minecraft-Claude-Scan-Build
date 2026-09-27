"""A work cell must carry the orientation the design decided, and nothing else.

`work.json` used to store bare block names, and that made `/cscan check` blind to orientation. It
is not a hypothetical: the taproot entrance places `smooth_stone_slab` as BOTH `type=top` and
`type=bottom`, and `Island Belly Full` places `mossy_stone_brick_slab` as `type=double` (a full
block) next to `type=top`. Every one of them read as built whichever way round it went in — 3,441
stateful cells across the designs, including the stairs whose convention this repo went to some
trouble to settle.

The other half matters as much. Most of a block state is not a decision, it is the game reacting to
the neighbourhood: a stair's `shape` comes from what is beside it, a wall's connections from what it
touches, `waterlogged` from someone pouring water in. Recording those would report a deviation for a
block that is exactly right, and a check that cries wolf is a check nobody runs.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import work                        # noqa: E402


def s(name, **props):
    return work.state_string(name, props)


def test_a_plain_block_stays_a_bare_name():
    """Backward compatibility is the point: the mod falls back to name-only comparison, so a
    design nobody has regenerated keeps reading correctly."""
    assert s("minecraft:stone_bricks") == "stone_bricks"
    assert s("minecraft:smooth_stone") == "smooth_stone"


def test_a_stair_records_facing_and_half_and_not_shape():
    # THE STAIR CONVENTION: a flight ascending toward D has every tread facing=D, half=bottom.
    # `shape` is inner_left/outer_right/... and the game picks it from the neighbours.
    assert s("minecraft:stone_brick_stairs", facing="east", half="bottom",
             shape="straight", waterlogged="false") == "stone_brick_stairs[facing=east,half=bottom]"
    assert s("minecraft:stone_brick_stairs", facing="east", half="bottom",
             shape="inner_left", waterlogged="false") == "stone_brick_stairs[facing=east,half=bottom]"


def test_a_slab_records_its_type():
    assert s("minecraft:smooth_stone_slab", type="top", waterlogged="false") == "smooth_stone_slab[type=top]"
    assert s("minecraft:smooth_stone_slab", type="double", waterlogged="false") == "smooth_stone_slab[type=double]"
    assert s("minecraft:smooth_stone_slab", type="top") != s("minecraft:smooth_stone_slab", type="bottom")


def test_a_wall_records_nothing_because_its_connections_are_derived():
    assert s("minecraft:stone_brick_wall", north="low", east="none", up="true",
             waterlogged="false") == "stone_brick_wall"


def test_a_vine_records_every_face_because_that_is_the_decision():
    """A vine clings to the face BEHIND it, and which face decides whether it hangs at all. For
    multiface blocks the direction flags are the design, not a connection the game made."""
    out = s("minecraft:vine", east="true", north="false", south="false", up="false", west="false")
    assert out == "vine[east=true,north=false,south=false,up=false,west=false]"
    assert s("minecraft:glow_lichen", south="true", waterlogged="false") == "glow_lichen[south=true]"


def test_a_lantern_records_whether_it_hangs():
    assert s("minecraft:lantern", hanging="true", waterlogged="false") == "lantern[hanging=true]"
    assert s("minecraft:lantern", hanging="false", waterlogged="false") == "lantern[hanging=false]"


def test_a_chain_records_its_axis():
    assert s("minecraft:iron_chain", axis="y", waterlogged="false") == "iron_chain[axis=y]"


def test_properties_are_sorted_so_the_string_is_canonical():
    a = s("minecraft:stone_brick_stairs", half="bottom", facing="east")
    b = s("minecraft:stone_brick_stairs", facing="east", half="bottom")
    assert a == b == "stone_brick_stairs[facing=east,half=bottom]"


def test_derived_properties_are_never_recorded():
    for prop in ("waterlogged", "shape", "powered", "lit", "snowy", "distance", "persistent"):
        assert prop not in s("minecraft:oak_stairs", facing="north", half="top", **{prop: "true"})


@pytest.mark.skipif(not os.path.exists("out/Taproot Entrance.litematic"), reason="needs the design")
def test_the_taproot_entrance_really_does_place_both_slab_halves():
    """The concrete case that justifies all of this. If this ever stops being true the argument
    still holds, but it is worth knowing which design proved it."""
    from mcbuild import schem, nbt
    m = schem.load("out/Taproot Entrance.litematic")
    kinds = {work.state_string(nbt.state_name(e), nbt.state_props(e)) for e in m.palette}
    assert "smooth_stone_slab[type=top]" in kinds
    assert "smooth_stone_slab[type=bottom]" in kinds
