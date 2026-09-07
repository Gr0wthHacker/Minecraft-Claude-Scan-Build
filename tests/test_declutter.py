"""The clutter pass hides ground dressing and swaps a block that draws no line.

The rules that matter are the EXCLUSIONS: a moss block is the ground, a leaf is a canopy, and a
plant that emits light is a fixture the night pass placed. Each of those was a wrong answer first.
"""
import numpy as np
import pytest

from mcbuild import nbt, schem
from mcbuild.ops.declutter import CLUTTER, LIT, NOT_CLUTTER, SWAPS, declutter


def _model(names):
    """A 1x1xN bar, one cell per name, in order."""
    pal = [nbt.block_state("minecraft:air")] + [nbt.block_state(n if ":" in n else "minecraft:" + n)
                                                for n in names]
    ids = np.arange(1, len(names) + 1, dtype=np.int32).reshape(1, 1, len(names))
    return schem.Model(ids, pal)


def _names(m):
    return [m.name_at(x, 0, 0) for x in range(m.ids.shape[2])]


def test_moss_carpet_goes_and_the_moss_block_stays():
    m = _model(["moss_carpet", "moss_block"])
    removed, _ = declutter(m)
    assert removed["minecraft:moss_carpet"] == 1
    assert _names(m) == ["minecraft:air", "minecraft:moss_block"]


def test_the_azalea_bush_goes_and_its_leaves_stay():
    m = _model(["azalea", "flowering_azalea", "azalea_leaves", "flowering_azalea_leaves"])
    declutter(m)
    assert _names(m) == ["minecraft:air", "minecraft:air",
                         "minecraft:azalea_leaves", "minecraft:flowering_azalea_leaves"]


@pytest.mark.parametrize("name", sorted(LIT))
def test_a_plant_that_emits_light_is_never_clutter(name):
    """Removing one re-opens a spawnable cell the night pass solved, and nothing would report it."""
    assert name not in CLUTTER
    m = _model([name])
    removed, _ = declutter(m)
    assert not removed


def test_a_canopy_is_not_a_shrub():
    m = _model(["jungle_leaves", "oak_leaves", "birch_leaves", "vine"])
    before = _names(m)
    removed, _ = declutter(m)
    assert not removed and _names(m) == before


def test_masonry_that_is_merely_called_mossy_is_left_alone():
    m = _model(["mossy_cobblestone", "mossy_stone_bricks"])
    removed, _ = declutter(m)
    assert not removed


def test_andesite_becomes_the_warm_rock_and_polished_andesite_is_untouched():
    m = _model(["andesite", "polished_andesite", "stone"])
    _, swapped = declutter(m)
    assert swapped[("minecraft:andesite", "minecraft:dripstone_block")] == 1
    assert _names(m) == ["minecraft:dripstone_block", "minecraft:polished_andesite",
                         "minecraft:stone"]


def test_every_state_of_a_plant_goes_with_it():
    """Matching is on the NAME: a fern's `half`, a seagrass's `waterlogged`, a tulip's nothing."""
    pal = [nbt.block_state("minecraft:air"),
           nbt.block_state("minecraft:fern"),
           nbt.block_state("minecraft:fern", half="upper"),
           nbt.block_state("minecraft:seagrass", waterlogged="true")]
    m = schem.Model(np.array([[[1, 2, 3]]], np.int32), pal)
    removed, _ = declutter(m)
    assert sum(removed.values()) == 3
    assert not m.solid().any()


def test_keep_wins_over_both_lists():
    m = _model(["fern", "andesite"])
    removed, swapped = declutter(m, keep={"fern", "andesite"})
    assert not removed and not swapped
    assert _names(m) == ["minecraft:fern", "minecraft:andesite"]


def test_nothing_in_the_kept_list_is_also_in_the_clutter_list():
    """NOT_CLUTTER is the record of WHY each exclusion exists; a name in both would be a lie."""
    assert not (set(NOT_CLUTTER) & CLUTTER)
    for name, why in NOT_CLUTTER.items():
        assert why.strip(), name


def test_a_swap_never_targets_something_the_pass_would_then_hide():
    assert not (set(SWAPS.values()) & {("minecraft:" + n) for n in CLUTTER} | (set(SWAPS.values()) & CLUTTER))
