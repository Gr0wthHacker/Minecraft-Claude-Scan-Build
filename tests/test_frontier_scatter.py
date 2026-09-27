"""The Frontier's planting, and the ground probe every land-dressing design shares.

`frontier_scatter`'s own docstring has claimed since it was written that "every entry checked by
`tests/test_frontier_scatter.py` against `blocks.available`, `blocks.spendable` and `palette.tier`"
- and that file did not exist. It does now, because `_Ground` grew a second consumer
(`gen/claimrow.py`) and a shared helper with one caller and no test is a helper that drifts.
"""
from __future__ import annotations

import os

import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import frontier_scatter as fs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "pf_frontier_scatter.yaml")
OUT = os.path.join(ROOT, "out")


class _FakeCtx:
    """A world of exactly what the test says it is. `Ctx` reads a capture; this reads a dict, so a
    ground-probe test states its own world instead of depending on whatever was last shipped."""

    def __init__(self, cells):
        self.cells = dict(cells)

    def name_at(self, x, y, z):
        return self.cells.get((x, y, z), "air")


def _ground(cells, **kw):
    return fs._Ground(_FakeCtx(cells), (0, 203, 0), 8, 8, (0, 0), kw.pop("clear", 0), **kw)


def test_every_planting_material_is_legal_spendable_and_cheap():
    """Rule 16 - and dirt and grass being CURRENCY here is exactly why a park cannot be lawns."""
    for key, name in fs.FLORA.items():
        assert blocks.spendable(name), f"{key}={name} is CURRENCY on this server"
        assert palette.tier(name) != "expensive", f"{key}={name} is expensive tier"


def test_lawn_is_moss_and_nothing_else():
    """`Park Ways` owns every paved cell in the park. A tree in a street is not dressing."""
    assert fs.LAWN == {"moss_block", "moss_carpet"}


def test_a_column_with_something_standing_on_it_is_not_lawn():
    g = _ground({(0, 202, 0): "moss_block", (0, 203, 0): "stone_bricks"})
    assert not g.lawn(0, 0)


def test_a_column_over_paving_is_not_lawn_however_clear_it_is():
    g = _ground({(0, 202, 0): "stone_bricks"})
    assert not g.lawn(0, 0)


def test_own_lets_a_design_replant_its_own_standing_work():
    """RULE 15, the heuristic half: a cell this design placed is built progress."""
    world = {(0, 202, 0): "moss_block", (0, 203, 0): "spruce_log"}
    assert not _ground(world, own=frozenset()).lawn(0, 0)
    assert _ground(world, own=frozenset({"spruce_log"})).lawn(0, 0)


def test_mine_is_exact_where_own_is_a_guess():
    """**THE POINT OF `mine`.** In a land where every module is stone brick, blackstone and spruce,
    a material list cannot tell a neighbour's plinth from this design's own - so a wide `own`
    walks straight through the neighbour and a narrow one refuses the design's own work. Naming
    the CELLS separates the two, and it is the only thing that can."""
    world = {(0, 202, 0): "moss_block", (0, 203, 0): "polished_blackstone_bricks",
             (1, 202, 0): "moss_block", (1, 203, 0): "polished_blackstone_bricks"}
    # the wide material set cannot tell them apart - both columns read free
    wide = _ground(world, own=frozenset({"polished_blackstone_bricks"}))
    assert wide.lawn(0, 0) and wide.lawn(1, 0)
    # naming this design's own cell frees exactly that one and leaves the neighbour's standing
    exact = _ground(world, own=frozenset(), mine=frozenset({(0, 203, 0)}))
    assert exact.lawn(0, 0)
    assert not exact.lawn(1, 0)


def test_free_is_a_cell_test_where_lawn_is_a_column_test():
    """A canopy is cells. Asked as a column, a pine two cells from a neighbour spread its leaves
    straight over that neighbour's roof - measured at 33 cells before this split existed."""
    world = {(0, 202, 0): "moss_block", (0, 207, 0): "dark_oak_stairs"}
    g = _ground(world)
    assert not g.lawn(0, 0), "something in the column blocks a trunk"
    assert g.free(0, 0, 0), "...and the cell at the plane is still free"
    assert not g.free(0, 0, 4), "...and the cell the roof is in is not"


def test_keep_out_wins_over_a_perfectly_good_lawn():
    world = {(0, 202, 0): "moss_block"}
    assert _ground(world).lawn(0, 0)
    assert not _ground(world, keep_out=[(0, 1, 0, 1)]).lawn(0, 0)


def test_shipped_cells_absent_is_empty_not_an_error():
    """A first run has nothing standing, and empty is the correct answer for that - not a crash,
    and not a refusal to build."""
    assert fs.shipped_cells(None) == frozenset()
    assert fs.shipped_cells(os.path.join(OUT, "nothing here.litematic")) == frozenset()


def test_the_scatter_keeps_out_of_every_module_lot():
    """**IT HAS TO, AND THAT IS ALSO WHY THE CLAIM ROW EXISTS.** The scatter cannot tell its own
    pine from the Diggings', so it refuses every module's lot - and the modules do not fill their
    own lots, so the ground inside a lot and outside a building belonged to nobody. That overlap
    is 3,153 columns of Frontier column A, which `gen/claimrow.py` now owns."""
    with open(CONFIG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    boxes = cfg["params"]["keep_out"]
    assert len(boxes) >= 9, "every lot in the land is named, or the scatter builds on a neighbour"
    for box in boxes:
        assert len(box) == 4 and box[0] <= box[1] and box[2] <= box[3], f"bad keep-out {box}"
