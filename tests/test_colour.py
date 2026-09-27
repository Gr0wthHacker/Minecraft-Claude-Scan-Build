"""Block colour: the biome tint, and the two faces.

`blocks.json` held one RGB per block, sampled from the TOP face with no tint applied, and both
halves were wrong. Measured off the real capture at the time: 18,006 of the island's 56,739 blocks
- 31.7% - were a tint-affected block recorded as GREY. 13,611 vines at [116,116,116]. Every leaf.
`grass_block` itself at [147,147,147].

Every palette in this project is picked by `blocks.nearest()` over those numbers and every render
draws with them, so the picker could not reach a leaf to get green - it chose `green_concrete`,
which is expensive tier - and a third of every island render came out grey.

These tests pin the shape of the fix rather than exact values, because the values move when the
game updates and the SHAPE is what must not regress.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import blocks                          # noqa: E402


def _green(rgb):
    """Green channel clearly dominant - what a plant must look like."""
    return rgb[1] > rgb[0] + 15 and rgb[1] > rgb[2] + 15


def test_foliage_is_green_not_grey():
    """The whole point. A greyscale texture that the game tints must not be recorded as grey."""
    for n in ("oak_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves", "vine",
              "grass_block", "short_grass", "fern", "lily_pad"):
        c = blocks.color(n)
        assert c is not None, f"{n} has no colour at all"
        assert _green(c), f"{n} is {c} — still reading as grey"


def test_nothing_tinted_is_neutral_grey():
    for n in ("oak_leaves", "vine", "grass_block", "tall_grass", "large_fern"):
        r, g, b = blocks.color(n)
        assert not (abs(r - g) < 8 and abs(g - b) < 8), f"{n} is neutral {(r, g, b)}"


def test_water_is_blue():
    """Water is tinted by the biome's water colour, default 0x3F76E4. It was [177,177,177]."""
    r, g, b = blocks.color("water")
    assert b > r + 40 and b > g + 40, f"water is {(r, g, b)}"


def test_spruce_and_birch_ignore_the_biome():
    """Those two use a FIXED colour rather than the colormap — the game does not tint them by biome
    and neither may we, or a birch wood reads like an oak one."""
    assert _green(blocks.color("spruce_leaves"))
    assert _green(blocks.color("birch_leaves"))
    assert blocks.color("spruce_leaves") != blocks.color("oak_leaves")
    assert blocks.color("birch_leaves") != blocks.color("oak_leaves")


def test_a_log_has_two_different_faces():
    """End grain is not bark. `oak_log` differs by 42 between them and `cherry_log` by 131 — one
    number could only ever be right for one kind of build."""
    top, side = blocks.color("oak_log"), blocks.color("oak_log", "side")
    assert top != side
    assert max(abs(a - b) for a, b in zip(top, side)) > 25


def test_top_is_the_default_so_no_existing_caller_moved():
    for n in ("oak_log", "bone_block", "stone_bricks", "grass_block"):
        assert blocks.color(n) == blocks.color(n, "top")


def test_a_uniform_block_reads_the_same_either_way():
    for n in ("stone_bricks", "smooth_stone", "deepslate_bricks", "black_wool"):
        assert blocks.color(n) == blocks.color(n, "side"), f"{n} is not uniform"


def test_a_block_with_no_top_face_falls_back_to_its_side():
    """A grindstone's texture slots are leg/pivot/round/side and it has no top at all. Before the
    fallback was ordered, the sorted-key fallback picked `leg` — the dark wooden strut — and called
    a grey stone block [60,47,26]."""
    r, g, b = blocks.color("grindstone")
    assert abs(r - g) < 20 and abs(g - b) < 20, f"grindstone is {(r, g, b)}, not stone-coloured"
    assert r > 100, "grindstone went dark: the leg texture won again"


def test_the_picker_can_now_reach_a_leaf_for_green():
    """It could not before, and chose `green_concrete` — which is expensive tier — for leaf green."""
    pick = blocks.nearest((60, 100, 30))
    assert pick is not None
    from mcbuild import palette
    assert palette.tier(pick) in ("cheap", "ok"), f"{pick} is expensive"


def test_face_changes_what_the_picker_returns():
    """If it never did, the two-face split would be decoration."""
    diff = [t for t in [(110, 85, 50), (230, 226, 205), (190, 150, 90)]
            if blocks.nearest(t) != blocks.nearest(t, face="side")]
    assert diff, "no target picks differently by face — the side colours are not being used"


def test_every_block_still_has_a_colour():
    """The recolour must not lose any block. Only the three airs may have none."""
    missing = [n for n in blocks._db() if "rgb" not in blocks._db()[n]]
    assert set(missing) <= {"air", "cave_air", "void_air"}, f"lost colours: {missing[:8]}"


def test_ramp_still_returns_distinct_blocks():
    r = blocks.ramp((40, 60, 30), (200, 220, 190), 4)
    assert len(r) == len(set(r)), "a ramp that repeats a block reads as a flat band"
