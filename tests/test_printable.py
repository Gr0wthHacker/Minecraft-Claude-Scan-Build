"""A printer clicks a FACE, so a diagonal join is not a join.

The fault these pin is the one this project has now hit in five separate generators - ear tips,
ossicones, a tail, a root braid, a pterosaur's wing - and always found by counting COMPONENTS after
the fact. `mcbuild.printable` asks it the other way round and about the thing that actually
matters: can the printer ever arrive.
"""
from __future__ import annotations

import pytest

from mcbuild import printable as P


def cells(*items) -> dict:
    """{(x, y, z): block} from (x, y, z, block) tuples."""
    return {(x, y, z): b for x, y, z, b in items}


def stair(n: int, block: str = "stone") -> dict:
    """A line of blocks each one east and one up from the last - the exact shape Jack described:
    *"they may have a line of things, but the entire line is diagonal so nothing reaches it."*"""
    return {(i, i, 0): block for i in range(n)}


# ---------------------------------------------------------------- the measurement

def test_a_diagonal_line_is_one_island_per_block():
    s = P.survey("x", cells=stair(6), world_cells={})
    assert s.islands == 6, "every tread stands alone: nothing shares a face with anything"
    assert len(s.orphans) == 5


def test_a_straight_line_is_one_island():
    line = {(i, 0, 0): "stone" for i in range(6)}
    s = P.survey("x", cells=line, world_cells={})
    assert s.islands == 1
    assert s.ok


def test_the_world_is_what_seeds_the_closure():
    d = {(0, 1, 0): "stone", (1, 1, 0): "stone"}
    assert P.survey("x", cells=d, world_cells={(0, 0, 0): "stone"}).ok
    # the same design with the world one block to the side touches nothing
    away = P.survey("x", cells=d, world_cells={(9, 0, 0): "stone"})
    assert away.seeds == 0


def test_a_carpet_carries_nothing_onward():
    """A vine, a carpet or water can be PLACED and is not something to place against - which is
    why a line of them cannot reach anywhere, however long it is."""
    d = {(0, 0, 0): "stone", (1, 0, 0): "moss_carpet", (2, 0, 0): "stone"}
    s = P.survey("x", cells=d, world_cells={})
    assert (2, 0, 0) in s.orphans, "the far stone is behind a carpet, so nothing reaches it"


def test_a_diagonal_orphan_is_counted_as_one():
    s = P.survey("x", cells=stair(6), world_cells={}, stitch=False)
    assert s.orphans == s.by_diagonal, "every one of them would be returned by a corner fill"


# ---------------------------------------------------------------- the fix

def test_a_stair_is_stitched_into_one_printable_piece():
    s = P.survey("x", cells=stair(6), world_cells={})
    assert s.stitches, "a corner fill exists for every step"
    joined = dict(stair(6))
    joined.update(s.stitches)
    assert P.survey("x", cells=joined, world_cells={}).islands == 1
    assert not s.unfixable


def test_a_stitch_never_covers_anything():
    """The one property that makes this safe to run over somebody's half-built park."""
    d = stair(5)
    d[(0, 1, 0)] = "oak_planks"                     # a cell the design already owns
    s = P.survey("x", cells=d, world_cells={(1, 0, 0): "stone"})
    for p in s.stitches:
        assert p not in d
        assert p != (1, 0, 0)


def test_a_stitch_takes_a_material_that_is_already_there():
    s = P.survey("x", cells=stair(6, "deepslate_bricks"), world_cells={})
    assert set(s.stitches.values()) == {"deepslate_bricks"}


def test_a_stitch_is_never_a_falling_block():
    """Rule 13: sand and gravel cannot be used where there is air underneath, and a corner fill in
    a diagonal flight is over air by construction."""
    s = P.survey("x", cells=stair(6, "gravel"), world_cells={})
    assert "gravel" not in set(s.stitches.values())
    assert not s.stitches or all(not __import__("mcbuild").blocks.falls(b)
                                 for b in s.stitches.values())


def test_a_stitch_prefers_the_tread_it_can_hide_under():
    """Of the two corners closing a step there is one UNDER the upper block - a stringer, which no
    plan view ever sees - and one ON TOP of the lower one, which is a lump on a finished surface."""
    s = P.survey("x", cells=stair(6), world_cells={})
    tucked = sum(1 for p in s.stitches if P.tucked(p, s.cells, s.stitches))
    assert tucked == len(s.stitches), "every fill sits under the tread above it"


def test_nothing_within_reach_is_reported_rather_than_bridged():
    """A stitch is a corner fill and not a scaffold: a lump of blocks alone in the void has to be
    named, because reaching it is a person with a stack of dirt."""
    d = {(0, 0, 0): "stone", (0, 1, 0): "stone"}
    d.update({(40, 0, 0): "stone", (41, 0, 0): "stone"})
    s = P.survey("x", cells=d, world_cells={})
    assert s.unfixable, "the far pair cannot be reached from the near one"
    assert sum(c.n for c in s.unfixable) == 2
    assert max(abs(p[0]) for p in s.stitches) <= P.REACH if s.stitches else True


def test_reach_is_two_because_a_corner_can_need_two_cells():
    """A two-axis diagonal needs one cell; a three-axis one needs two, and the park's undercrypt
    hung on exactly that - every contact between it and the rest of the park was (1, 1, 1)."""
    d = {(0, 0, 0): "stone", (1, 1, 1): "stone"}
    assert P.survey("x", cells=d, world_cells={}).ok is False
    s = P.survey("x", cells=d, world_cells={})
    assert len(s.stitches) == 2 and not s.unfixable
    s1 = P.survey("x", cells=d, world_cells={}, reach=1)
    assert s1.unfixable, "one cell cannot close a corner-to-corner join"


# ---------------------------------------------------------------- the shipped park

@pytest.mark.parametrize("design", ["Friend Stair NW", "Friend Stair NE",
                                    "Friend Stair SW", "Friend Stair SE"])
def test_the_friend_stairs_print_from_the_platform(design):
    pytest.importorskip("numpy")
    try:
        s = P.survey(design, "friendisland", stitch=False)
    except FileNotFoundError:
        pytest.skip(f"{design} is not shipped here")
    assert s.ok, s.report()


def test_the_tracked_composite_has_no_diagonal_break_left_open():
    """`Park Complete` is the one design `sync.yaml` tracks, so it is the one somebody prints.

    The contract is NOT a cell count - a snapshot of what was orphaned on some particular day is
    the trap this project has recorded five times over. It is that nothing a CORNER FILL could
    close is still open: if the pass would fix it, the shipped file should already have it fixed.
    What remains after that is masses hanging in the void, which want a pillar and a person, and
    pond dressing, which is placed against water rather than against a face. Both are reported by
    the tool and neither is this check's to demand.
    """
    pytest.importorskip("numpy")
    try:
        s = P.survey("Park Complete")
    except FileNotFoundError:
        pytest.skip("Park Complete is not shipped here")
    assert not s.stitches, (
        f"{len(s.stitches)} diagonal joins would be closed by a corner fill and are still open -"
        f" run `python -m mcbuild printable \"Park Complete\" --fix`:\n{s.report()}")


def test_the_composite_names_what_it_cannot_reach():
    """A pass that quietly reported everything fixed would be worse than none: the descent hangs
    in an open shaft and no corner fill reaches it, and that has to stay VISIBLE."""
    pytest.importorskip("numpy")
    try:
        s = P.survey("Park Complete")
    except FileNotFoundError:
        pytest.skip("Park Complete is not shipped here")
    hard, soft = s.split_unfixable()
    if hard:
        assert "STILL UNREACHABLE" in s.report()
    if soft:
        assert "dressing" in s.report()
