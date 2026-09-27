"""The outline arithmetic behind `gen/lowland.py`.

These are the parts that actually went wrong while building it, so they are the parts worth pinning:
holes, connectivity after the rim is bitten, the distance transform the taper rides on, and the
largest-level-rectangle measurement that answers "does an elephant fit".
"""
import numpy as np

from mcbuild.gen import lowland as L


def _grid(rows):
    return np.array([[c == "#" for c in r] for r in rows], bool)


def test_fill_holes_closes_an_enclosed_gap_but_not_a_notch():
    """A pond is a hole in the island; it is not a hole in the ground BELOW the island."""
    g = _grid([
        "#####",
        "##.##",
        "#...#",       # enclosed
        "#####",
        "##.##",       # a notch open to the south edge - must stay open
    ])
    out = L._fill_holes(g)
    assert out[1, 2] and out[2, 1] and out[2, 2] and out[2, 3]
    assert not out[4, 2], "a notch reaching the border is not interior"


def test_largest_piece_drops_detached_crumbs():
    g = _grid([
        "###..",
        "###..",
        ".....",
        "....#",       # a speck
    ])
    out = L._largest_piece(g)
    assert out.sum() == 6
    assert not out[3, 4]


def test_edge_distance_is_one_at_the_boundary_and_grows_inward():
    g = _grid([
        "#####",
        "#####",
        "#####",
        "#####",
        "#####",
    ])
    d = L._edge_distance(g)
    assert d[0, 0] == 1 and d[0, 2] == 1
    assert d[1, 1] == 2
    assert d[2, 2] == 3, "the middle of a 5x5 is three in from the edge"


def test_edge_distance_ignores_cells_outside_the_mask():
    g = _grid([
        ".###.",
        "#####",
        ".###.",
    ])
    d = L._edge_distance(g)
    assert d[0, 0] == 0, "not ground, so no distance"
    assert d[1, 2] == 2


def test_max_rect_returns_x_then_z_extents():
    g = _grid([
        ".###.",
        ".###.",
    ])
    ax, az, rows, cols = L._max_rect(g)
    assert (cols, rows) == (3, 2), "3 wide in x, 2 deep in z"
    assert (ax, az) == (1, 0)


def test_max_rect_of_empty_is_none():
    assert L._max_rect(_grid(["...", "..."])) is None


def test_flat_pads_finds_the_biggest_LEVEL_area():
    """Statues need level ground, not merely ground - a pad spanning two heights is not a pad."""
    surf = {}
    for x in range(10):
        for z in range(10):
            surf[(100 + x, 200 + z)] = 40 if x < 6 else 41
    pads = L._flat_pads(surf)
    best = pads[0]
    assert best["y"] == 40
    assert best["size"] == [6, 10]
    assert best["at"] == [100, 200]


def test_flat_pads_of_nothing_is_empty():
    assert L._flat_pads({}) == []


def test_pick_is_deterministic_in_world_coordinates():
    """A rebuild must place the same block in the same cell, or every regen churns the diff."""
    table = [("stone", 0.5), ("andesite", 0.5)]
    a = [L._pick(table, x, 40, 7, 0) for x in range(50)]
    b = [L._pick(table, x, 40, 7, 0) for x in range(50)]
    assert a == b
    assert set(a) == {"stone", "andesite"}, "both entries of the table get used"
