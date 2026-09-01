"""`tools/redstone_audit.py` - the folder-wide check that did not exist.

`circuit.inspect` has been callable per design since the simulator was written, and nothing ever
ran it over `out/`. Seven real faults sat in the shipped park across three zones until a human read
a render and said the redstone looked broken. A checker nobody runs is a checker that does not
exist, so this pins the two things that decide whether it gets run: that it finds a real fault, and
that it stays QUIET on the things that are not faults.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib

import pytest

from mcbuild import circuit
from mcbuild.gen import GENERATORS

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "redstone_audit", ROOT / "tools" / "redstone_audit.py")
audit_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit_tool)


CASINO_KINDS = ["high_roller", "double_or_none", "lucky_number", "duel", "wheel",
                "prize_wall", "marquee", "counter"]


def _real(findings):
    """QUASI-CONNECTIVITY IS A NOTE, NOT A FAULT. It is modelled rather than merely warned about,
    so its one line says which cells depend on a mechanic most people do not expect - and on a
    piston or dispenser machine it fires on every cell of a build that demonstrably works.
    Counting it as a fault is how a checker stops being read; see `test_circuit_calibration`."""
    return [f for f in findings if f[0] != "quasi-connectivity"]


def _casino(kind, **kw):
    return GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "outcomes": 3,
                                       "pit": 2, "check": False, "title": "T", **kw}, [])


@pytest.mark.parametrize("kind", CASINO_KINDS)
def test_every_casino_kind_inspects_clean(kind):
    """The same bar `tests/test_arcade.py` holds the arcade to, and nothing is exempt.

    The arcade's version of this test used to allow `repeater reads nothing`, on the grounds that
    `circuits.window`'s side repeater has a back which is "deliberately empty" - it was not
    deliberate, it was the bug that made every exact-value gate a threshold. An exemption written
    into a check is a blindfold.
    """
    c = _casino(kind)
    findings = _real(circuit.inspect(c.to_model(), c.world_origin))
    assert not findings, f"{kind}: {findings}"


@pytest.mark.parametrize("kind", ["high_roller", "double_or_none", "lucky_number", "duel",
                                  "wheel"])
@pytest.mark.parametrize("facing", ["east", "west", "north", "south"])
def test_every_game_inspects_clean_at_every_orientation(kind, facing):
    """A rotation table is where this kind of fault hides: `circuits.randomiser` once read `dy`
    where it meant `dz`, which is correct for east and west by coincidence and puts the comparator
    on top of its own hopper for north and south."""
    c = _casino(kind, facing=facing)
    findings = _real(circuit.inspect(c.to_model(), c.world_origin))
    assert not findings, f"{kind}/{facing}: {findings}"


def test_the_census_counts_what_a_player_can_do_and_see():
    c = _casino("wheel")
    r = audit_tool.Report("wheel", c.to_model(), dict(c.meta, origin=list(c.world_origin)))
    assert r.inputs["button"] == 1, "the wheel has exactly one button"
    assert r.indicators["lamp"] == 3, "three pockets, three lamps"
    assert r.n_inputs and r.n_indicators >= 2
    assert not r.thin, r.thin
    assert r.has_redstone


def test_a_machine_with_nothing_to_press_is_named_as_thin():
    """The rule the complaint was about: wiring a player cannot start is an ornament."""
    c = _casino("high_roller")
    side = dict(c.meta, origin=list(c.world_origin))
    r = audit_tool.Report("high roller", c.to_model(), side)
    assert r.n_inputs == 1 and r.wiring["wire"], "the control: a button and real wiring"
    assert not r.thin, r.thin

    # ...and the same machine with its input taken away, which is what "very simple" looks like
    # from the aisle: a wall you cannot start.
    stripped = audit_tool.Report("stripped", c.to_model(), side)
    stripped.inputs = {k: 0 for k in stripped.inputs}
    assert any("nothing to press" in t for t in stripped.thin)


def test_a_single_indicator_is_not_a_readout():
    c = _casino("high_roller")
    r = audit_tool.Report("hr", c.to_model(), dict(c.meta, origin=list(c.world_origin)))
    r.indicators = {k: 0 for k in r.indicators}
    r.indicators["lamp"] = 1
    assert any("indicator" in t for t in r.thin)


def test_a_capture_is_not_a_design_and_a_slice_is_not_a_machine():
    """**RULE 2, APPLIED TO OUR OWN SLICING.** A layer holds the part of every circuit that landed
    in it, so the wire under the floor reads as dust with no source and the dropper above it reads
    as unwired. Inspecting the four layers of one park zone reported 301 findings and not one was a
    defect. And a world capture carries somebody else's farms, which are not ours to grade.
    """
    assert audit_tool.is_capture({"cut_from": "x", "origin": {}})
    assert audit_tool.is_capture({"planned_from": "x"})
    assert not audit_tool.is_capture({"generated_by": "casino", "kind": "wheel"})
    assert audit_tool.is_slice({"generated_by": "mcbuild.layers", "slice": True})
    assert not audit_tool.is_slice({"generated_by": "mcbuild.layers", "slice": False})
    assert not audit_tool.is_slice({"generated_by": "casino"})


def test_the_tool_runs_over_the_folder_and_says_something():
    """It has to survive whatever is in `out/` on the day, including designs from other sessions."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = audit_tool.main(["--quiet"])
    text = buf.getvalue()
    assert "redstone audit:" in text
    assert code in (0, 1)


def test_the_layer_writer_records_that_a_slice_is_a_slice():
    """Without it the audit has no way to tell a build STEP from a machine, and the only signal
    available is a name suffix - which is exactly the kind of thing that drifts."""
    import json
    for name in ("Casino Complete", "Casino 2 Machines"):
        path = ROOT / "out" / f"{name}.scan.json"
        if not path.exists():
            pytest.skip("the casino has not been sliced in this checkout")
        side = json.loads(path.read_text(encoding="utf-8"))
        assert "slice" in side, f"{name}: the layer writer must say whether this is a slice"
    whole = json.loads((ROOT / "out" / "Casino Complete.scan.json").read_text(encoding="utf-8"))
    part = json.loads((ROOT / "out" / "Casino 2 Machines.scan.json").read_text(encoding="utf-8"))
    assert whole["slice"] is False and part["slice"] is True


def test_the_whole_casino_inspects_clean():
    """The composite, not the layers - which is the only frame in which a sliced circuit is whole.

    Skipped rather than failed when the folder has not been sliced, because `out/` is shared with
    whatever else is being generated that day and a test that grades another session's work in
    progress is a test that gets deleted.
    """
    name = "Casino Complete"
    r = audit_tool.load(name, str(ROOT / "out"))
    if r is None:
        pytest.skip("the casino has not been sliced in this checkout")
    assert not r.real, [f for f in r.real]
