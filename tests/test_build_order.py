"""Build order, recorded in the sidecar so the mod can read it.

`finish.defer_to` has always settled which design owns a shared cell, and CLAUDE.md has always
stated the sequences in prose — "portal first, ruinway defers to it", "the notch is the plug: cut it
LAST". None of that reached the game: the sidecar carried no ordering, so `/cscan follow all` walked
the tracked list exactly as written and could start a design whose ground another one still owes.

Deferring IS the ordering, so `after` is derived from `defer_to` rather than restated — a design
that yields a cell cannot be built before the design it yielded to. `finish.after` is the escape
hatch for an order that is real but not expressed as a shared cell, which is what `Island Night`
needs: it is a fixpoint solved against the finished world, and the Thicket's dripstone moves the
surface under it.
"""
import os
import pathlib
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import pipeline                        # noqa: E402

CONFIGS = pathlib.Path(__file__).resolve().parent.parent / "configs"


def test_deferring_to_a_design_means_building_after_it():
    assert pipeline._after({"finish": {"defer_to": ["out/Lowland Portal.litematic"]}}) \
        == ["Lowland Portal"]


def test_the_extension_is_stripped_whichever_one_it_is():
    got = pipeline._after({"finish": {"defer_to": ["out/A.litematic", "out/B.scan.json"]}})
    assert got == ["A", "B"]


def test_an_explicit_after_is_kept_alongside():
    got = pipeline._after({"finish": {"defer_to": ["out/A.litematic"], "after": ["B"]}})
    assert got == ["A", "B"]


def test_no_duplicates_when_both_name_the_same_design():
    got = pipeline._after({"finish": {"defer_to": ["out/A.litematic"], "after": ["A"]}})
    assert got == ["A"]


def test_a_config_with_no_finish_block_has_no_order():
    """Every design written before this existed. Absent must mean unordered, not an error."""
    assert pipeline._after({}) == []
    assert pipeline._after({"finish": {}}) == []
    assert pipeline._after({"finish": {"defer_to": None}}) == []


def test_island_night_records_that_it_is_solved_last():
    """The one ordering on the island that is a hard dependency rather than a preference, and the
    one that was only ever written in prose. If this list is edited away, the night pass can be
    solved against a world two designs short of finished and the fixpoint is wrong."""
    cfg = yaml.safe_load((CONFIGS / "island_night.yaml").read_text(encoding="utf-8"))
    after = pipeline._after(cfg)
    assert "Falls" in after and "Lowland Thicket" in after, after


def test_every_config_that_defers_would_emit_an_order():
    """A sweep rather than a fixture: if a config gained a `defer_to` and this stopped deriving an
    `after` from it, the mod would silently go back to building in list order."""
    checked = 0
    for p in sorted(CONFIGS.glob("*.yaml")):
        try:
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(cfg, dict):
            continue
        if (cfg.get("finish") or {}).get("defer_to"):
            checked += 1
            assert pipeline._after(cfg), f"{p.name} defers but records no order"
    assert checked > 0, "no config defers any more - re-point this test"
