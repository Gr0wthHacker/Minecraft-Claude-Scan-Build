"""The producers that answer the four gates which are about the BUILT world.

The property that matters most is the one about refusing: a producer handed a land nobody has
generated must FAIL and say so, never pass on an empty measurement. That is the same rule the
gates themselves live by, one layer down - a gate that grades an unmeasured thing as compliant
converts an unknown into a false assurance, and so does a producer.
"""
import pytest

from mcbuild import evidence, gates

ZONES = ("park_centre", "park_left", "park_right")


def _plan(name):
    from mcbuild import planner
    return dict(planner.Plan.load(name).__dict__)


def _have(name):
    import os
    return os.path.exists(f"out/plans/{name}.json")


def test_every_evidence_gate_has_a_producer():
    """A gate the suite cannot answer is a promise nobody can keep."""
    assert set(evidence.PRODUCERS) == gates.EVIDENCE


def test_a_producer_refuses_a_land_nobody_has_built():
    """The load-bearing property. Handed a plan with no artifacts, every producer must fail and
    name the reason - an empty measurement is not a clean one."""
    plan = {"name": "nothing", "modules": [{"name": "Ghost Module", "gen": "park", "kind": "gate",
                                            "at": [0, 64, 0], "size": [3, 3, 3],
                                            "anchor_offset": [0, 0, 0], "params": {}}],
            "routes": []}
    for name, producer in evidence.PRODUCERS.items():
        block = producer(plan, out_dir="out/does-not-exist")
        assert not block["ok"], f"{name} passed with nothing built"
        assert block["failures"], f"{name} failed and named no reason"
        assert "generated" in block["failures"][0]


def test_the_soft_findings_are_the_inspections_own_words():
    """**GUESSING THEM READ AS A FAULT.** `circuit.inspect` returns "quasi-connectivity" and
    "orientation unknown"; filtered against invented spellings, every piston machine in the
    Frontier came back as a circuit fault - which is the calibration corpus's own finding
    inverted, since a piston machine IS pistons with things over them."""
    from mcbuild import circuit
    import inspect as _inspect
    source = _inspect.getsource(circuit.inspect) + _inspect.getsource(circuit)
    for kind in evidence.SOFT_FINDINGS:
        assert f'"{kind}' in source, f"{kind!r} is not a string the inspection ever emits"


def test_a_water_envelope_is_read_from_whichever_key_declared_it():
    """A generator declares its wet cells under its own name - `channel`, `pool_water`, `basin` -
    because a sidecar is written for a reader. Reading only `envelope` reported the Rapids and
    the Sluice as leaking one cell each, which is a cascade being a cascade."""
    meta = {"channel": [[1, 2, 3]], "pool_water": [[4, 5, 6]], "unrelated": [[7, 8]]}
    got = evidence._envelope(meta)
    assert (1, 2, 3) in got and (4, 5, 6) in got
    assert len(got) == 2, "a two-element entry is not a cell"


@pytest.mark.parametrize("zone", ZONES)
def test_the_three_lands_are_mechanically_sound(zone):
    if not _have(zone):
        pytest.skip(f"{zone} has not been planned")
    block = evidence.mechanics(_plan(zone))
    assert block["ok"], block["failures"][:4]


@pytest.mark.parametrize("zone", ZONES)
def test_no_guest_route_is_blocked_or_over_a_hole(zone):
    if not _have(zone):
        pytest.skip(f"{zone} has not been planned")
    block = evidence.safety(_plan(zone))
    assert block["ok"], block["failures"][:4]


@pytest.mark.parametrize("zone", ZONES)
def test_paving_under_a_building_is_not_a_route_a_guest_walks(zone):
    """The street is laid even under a building on purpose - skipping obstacle cells can SPLIT a
    route, and a network that is not connected is not a network. Measured without that
    exclusion, 834 route cells across the three lands read as obstructed by the very walls they
    run beneath, which is the design working rather than a safety fault."""
    if not _have(zone):
        pytest.skip(f"{zone} has not been planned")
    block = evidence.safety(_plan(zone))
    assert block["headroom_blocked"] == 0


def test_visual_refuses_to_pass_on_a_render_alone():
    """**A PACKET IS EVIDENCE THAT SOMEBODY CAN LOOK. IT IS NOT EVIDENCE THAT THEY DID.** This
    project has the scar: an animal scored GOOD on every measured dimension and was a spotted
    table, and the rule written afterwards is that a panel which is not recorded is one the next
    good-looking score quietly overrules."""
    if not _have("park_left"):
        pytest.skip("park_left has not been planned")
    plan = _plan("park_left")
    plan.pop("evidence", None)
    block = evidence.visual(plan, sheet_dir="out/packets-test")
    assert not block["ok"]
    assert any("verdict" in f for f in block["failures"])


def test_a_recorded_verdict_is_what_lets_visual_pass():
    if not _have("park_left"):
        pytest.skip("park_left has not been planned")
    plan = _plan("park_left")
    plan["evidence"] = {"visual": {"verdict": "read it and it reads"}}
    block = evidence.visual(plan, sheet_dir="out/packets-test")
    assert block["ok"]
    assert block["verdict"] == "read it and it reads"


@pytest.mark.parametrize("zone", ZONES)
def test_the_night_pass_judges_the_guest_path_and_not_the_floor_of_a_room(zone):
    """**376 OF THE MIDWAY'S 387 "DARK GUEST PATHS" WERE THE FLOOR OF ROOMS.** Paving is laid
    even under a building on purpose and the building wins the cell, so a route cell inside a
    footprint is not somewhere a guest stands - and the kerb, where the lamp posts go, is not
    either. A night pass measured across both grades a correctly lit park as a mob farm.
    """
    if not _have(zone):
        pytest.skip(f"{zone} has not been planned")
    from mcbuild import pathgraph as P
    plan = _plan(zone)
    block = evidence.night(plan)
    hub = next(m for m in plan["modules"] if m.get("covers") and m["kind"] == "plaza")
    every = P.levels(P.normalise(plan["routes"]), int(hub["at"][1]))
    total = sum(len(v) for v in every.values())
    assert block["route_cells"] < total, (
        "the night pass is judging every route cell, including the ones under buildings")


@pytest.mark.parametrize("zone", ZONES)
def test_nothing_can_spawn_where_a_guest_walks(zone):
    if not _have(zone):
        pytest.skip(f"{zone} has not been planned")
    block = evidence.night(_plan(zone))
    assert block["ok"], block["failures"][:3]
