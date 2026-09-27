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


def test_gravel_becomes_a_block_that_does_not_fall():
    """Jack: "remove all gravel and swap for something else." Gravel was the only gravity block in
    the park's terrain, and eleven cells of the shipped composite stood on air."""
    m = _model(["gravel", "stone"])
    _, swapped = declutter(m)
    assert swapped[("minecraft:gravel", "minecraft:cobblestone")] == 1
    assert _names(m) == ["minecraft:cobblestone", "minecraft:stone"]


def test_NO_SWAP_TARGET_IS_ITSELF_A_GRAVITY_BLOCK():
    """The whole point of the gravel swap is rule 13, so a target that falls would be the fault
    moved rather than removed - and this is the guard for the NEXT swap somebody adds, which is
    where it would actually happen."""
    from mcbuild import blocks
    for src, dst in SWAPS.items():
        assert not blocks.falls(dst), f"{src} -> {dst}, which is itself a gravity block"


def test_a_swap_target_is_cheap_witnessed_and_not_a_machine():
    """Rule 12 - ASK THE WORLD, NOT THE TABLE. `tuff` and `gravel` were both cheap by the economy
    table and both stand in almost none of the real world; a target chosen the same way would be
    the same fault. `palette.affordable_like` applies all three gates, so a target it would not
    itself return has to be justified rather than assumed."""
    from mcbuild import palette
    for src, dst in SWAPS.items():
        best, _d = palette.affordable_like(src)
        assert best is not None, f"nothing cheap and witnessed is near {src}"
        assert palette.tier(dst) == "cheap", f"{src} -> {dst} is {palette.tier(dst)}"


def test_the_ore_seam_becomes_a_rock_seam():
    """Jack: "remove granite and ore blocks e.g. coal ore gold ore etc". All three stand in ZERO
    cells of the real captures and `mcbuild provision` classifies both ores NONE - no recipe, no
    price, no stock, no farm. Rule 12, and harder than tuff or gravel."""
    m = _model(["granite", "coal_ore", "gold_ore", "stone"])
    _, swapped = declutter(m)
    assert swapped[("minecraft:granite", "minecraft:dripstone_block")] == 1
    assert swapped[("minecraft:gold_ore", "minecraft:dripstone_block")] == 1
    assert swapped[("minecraft:coal_ore", "minecraft:smooth_basalt")] == 1
    assert "minecraft:granite" not in _names(m)
    assert not [n for n in _names(m) if n.endswith("_ore")]


def test_THE_SWAPS_KEEP_THE_MINE_RIDGE_S_SEAM_A_DISTINCT_BED():
    """The mapping is chosen against the LADDER, never per block, and this is the guard on that.

    `palette.affordable_like` optimises one block in isolation and knows nothing about what is
    already standing beside it. Its three answers here - granite/gold to the mid band's own greys
    and coal to `mossy_cobblestone` - leave `_SEAM` and `_MID` holding THE SAME FOUR MATERIALS in
    different proportions, all inside 15 points of luminance, and the seam stops being a bed at
    all. That is CLAUDE.md's "one grey" trap arriving through a helper rather than by hand.

    Derived from the generator's own tables so it cannot go stale, and it fails the fix rather
    than the fault: it is red for the answers a future session is most likely to take.
    """
    from mcbuild import blocks
    from mcbuild.gen import mineridge

    def lum(n):
        r, g, b = blocks.color(n, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    sub = {k.split(":")[-1]: v.split(":")[-1] for k, v in SWAPS.items()}

    def bed(entries):
        out = {}
        for key, frac in entries:
            n = mineridge.ROCK[key]
            n = sub.get(n, n)
            out[n] = out.get(n, 0.0) + frac
        return out

    seam, mid = bed(mineridge._SEAM), bed(mineridge._MID)

    # A bed is only a bed if it holds a tone the band beside it does not.
    assert set(seam) - set(mid), "the seam is made of nothing the mid band does not already have"

    # ...and that tone has to be far enough off the mid band to read as one.
    gap = max(min(abs(lum(n) - lum(o)) for o in mid) for n in set(seam) - set(mid))
    assert gap >= 15, f"the seam's own tone is only {gap:.1f} luminance off the mid band"


def test_NO_ORE_BLOCK_REACHES_A_SHIPPED_COMPOSITE():
    """The rest of the ore family is NOT in `SWAPS`, on purpose: it appears only in retired
    modules, and mapping a block nobody is looking at is a design decision made blind. This is
    what catches the next one instead - a re-sited `The Mine Head` fails here and forces a
    decision, rather than being silently swapped or silently shipped."""
    import pathlib

    from mcbuild import nbt, schem

    for name in ("Park Complete", "Park Buildings"):
        p = pathlib.Path("out") / f"{name}.litematic"
        if not p.exists():
            pytest.skip(f"{name} is not shipped here")
        m = schem.load(str(p))
        found = sorted({
            n for i, e in enumerate(m.palette)
            for n in [nbt.state_name(e).split(":")[-1]]
            if (n.endswith("_ore") or n == "granite") and (m.ids == i).any()
        })
        assert not found, f"{name} still ships {', '.join(found)}"
