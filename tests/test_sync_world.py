"""A design is measured against a world that CONTAINS it, or it is not measured at all.

`sync.yaml` tracked `Park Complete` and scanned `island` - the old island, 121,000 blocks away -
and printed `0/541753 built (0%)` every day for the life of the park. Every cell was out of the
box, and the honest word for that is UNKNOWN; but `oob` was the last clause of a line whose first
clause was a percentage, so the lie led and the reason trailed - and `history.json` recorded the
zero into the velocity slope.
"""
import os

import pytest

from mcbuild import coop, scan


def _p(oob: int, built: int = 0, total: int | None = None) -> coop.Progress:
    p = coop.Progress("fixture")
    p.total = total if total is not None else oob + built
    p.built = built
    p.oob = oob
    return p


def test_a_design_wholly_outside_its_world_is_not_a_zero():
    p = _p(oob=1000)
    assert not p.measured
    r = p.report()
    assert "NOT MEASURED" in r
    assert "0%" not in r, "the percentage is the lie; it must not be printed at all"
    assert "worlds:" in r, "...and the report has to say what would fix it"


def test_a_design_mostly_inside_its_world_is_measured():
    # A capture that clips a few cells at its edge is still a measurement.
    p = _p(oob=10, built=900, total=1000)
    assert p.measured
    assert "NOT MEASURED" not in p.report()
    assert p.coverage == pytest.approx(0.99)


def test_the_threshold_is_stated_rather_than_implied():
    assert 0 < coop.Progress.COVERAGE <= 1.0
    assert _p(oob=49, built=51, total=100).measured
    assert not _p(oob=51, built=49, total=100).measured


def test_an_empty_design_is_not_measured():
    """Nothing to compare is not 100% built - it is nothing to compare."""
    assert not _p(oob=0, built=0, total=0).measured


@pytest.mark.skipif(not os.path.exists("out/island_full.litematic"),
                    reason="no island capture on disk")
def test_a_world_box_is_read_from_the_sidecar_alone():
    b = coop.world_box("out/island_full.litematic")
    assert b is not None and b[0] < b[3] and b[2] < b[5]


@pytest.mark.skipif(not os.path.exists("out/island_full.litematic"),
                    reason="no island capture on disk")
def test_a_design_takes_the_world_whose_box_holds_it():
    worlds = [w for w in ("out/island_full.litematic", "out/island_now.litematic")
              if os.path.exists(w)]
    # A HEURISTIC ON PURPOSE - the honest check is `Progress.measured`, downstream and free. What
    # is pinned is that it never RAISES and always answers with one of the worlds it was given.
    for design in ("Lowland Stair", "Park Complete"):
        try:
            scan.resolve(design)
        except Exception:                                        # noqa: BLE001
            continue
        assert coop.world_for(design, worlds) in worlds


def test_no_world_at_all_is_an_error_rather_than_a_guess():
    with pytest.raises(ValueError):
        coop.world_for("anything", [])
