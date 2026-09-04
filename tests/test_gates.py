"""The eight promotion gates, and the one thing they must never do.

The gate that matters most here is the one that CANNOT be measured offline. `mechanics`, `safety`,
`night` and `visual` need evidence produced elsewhere, and the whole value of naming them as gates
is that an unmeasured land is BLOCKED rather than quietly promotable. A gate that grades an
unknown as compliant is worse than no gate at all: it converts an unknown into a false assurance.
"""
import pytest

from mcbuild import gates, interfaces as I

ZONES = ("midway", "frontier", "hollow")


@pytest.fixture(scope="module")
def planned():
    import sys
    sys.path.insert(0, "tests")
    import test_park_plan as T
    return {zone: dict(T._planned(zone).__dict__) for zone in ZONES}


def test_every_gate_the_two_briefs_name_exists_and_runs():
    """PARK_OVERHAUL.md lists eight by name; PARK_VERTICAL_MASTERPLAN.md adds the two that make
    this a vertical park rather than a flat one with tunnels - what belongs at what altitude,
    and how steeply a guest may be asked to climb. A missing one is a promise nobody is
    checking."""
    assert set(gates.ORDER) == {"interface", "route", "capacity", "band", "grade",
                                "mechanics", "safety", "wayfinding", "night", "visual"}
    assert set(gates.GATES) == set(gates.ORDER)
    assert gates.DERIVED | gates.EVIDENCE == set(gates.ORDER)
    assert not (gates.DERIVED & gates.EVIDENCE)


def test_an_unmeasured_gate_blocks_rather_than_passing():
    """The load-bearing property of the whole module."""
    plan = {"name": "empty", "modules": [], "routes": []}
    result = gates.run(plan)
    assert not result["ok"]
    for name in sorted(gates.EVIDENCE):
        gate = next(g for g in result["gates"] if g["gate"] == name)
        assert not gate["ok"], f"{name} passed with nothing measured"
        assert gate["failures"], f"{name} failed and named no reason"


def test_evidence_that_says_it_is_not_ok_and_names_nothing_still_fails():
    """A supplier that hands back `{ok: False}` and no failure has said nothing; the gate must
    not accept that as either a pass or an empty failure list."""
    plan = {"name": "p", "modules": [], "routes": [],
            "evidence": {"night": {"ok": False}}}
    gate = gates.night(plan)
    assert not gate["ok"] and gate["failures"]


def test_supplied_evidence_is_honoured():
    plan = {"name": "p", "modules": [], "routes": [],
            "evidence": {"night": {"ok": True, "spawnable_public_cells": 0}}}
    gate = gates.night(plan)
    assert gate["ok"]
    assert gate["evidence"]["spawnable_public_cells"] == 0


def test_a_land_with_no_circulation_fails_route_and_capacity():
    plan = {"name": "p", "modules": [], "routes": []}
    assert not gates.route(plan)["ok"]
    assert not gates.capacity(plan)["ok"]


def test_a_nameplate_on_every_facade_fails_wayfinding():
    """PARK_HOLLOW.md: signage belongs at decision points, "not at every facade". A land that
    labels every building has replaced wayfinding with noise, and no COUNT of signs tells them
    apart - which is why the gate measures the ratio to destinations."""
    modules = [{"name": f"Ride {n}", "gen": "attractions", "kind": "ghosttrain",
                "at": [n * 30, 64, 0], "size": [12, 8, 12], "anchor_offset": [0, 0, 0],
                "params": {"facing": "east"}} for n in range(5)]
    modules += [{"name": f"Sign {n}", "gen": "wayfinding", "kind": "marker",
                 "at": [n * 30, 64, 20], "size": [3, 5, 3], "anchor_offset": [0, 0, 0],
                 "params": {"facing": "east"}} for n in range(5)]
    modules += [{"name": "Map", "gen": "wayfinding", "kind": "mapboard",
                 "at": [0, 64, 40], "size": [3, 9, 11], "anchor_offset": [0, 0, 0],
                 "params": {"facing": "east"}}]
    I.annotate(modules)
    gate = gates.wayfinding({"name": "p", "modules": modules, "routes": []})
    assert not gate["ok"]
    assert any("per-facade" in f for f in gate["failures"])


def test_a_land_with_no_map_at_all_fails_wayfinding():
    modules = [{"name": "Ride", "gen": "attractions", "kind": "ghosttrain",
                "at": [0, 64, 0], "size": [12, 8, 12], "anchor_offset": [0, 0, 0],
                "params": {"facing": "east"}}]
    I.annotate(modules)
    gate = gates.wayfinding({"name": "p", "modules": modules, "routes": []})
    assert not gate["ok"]


# ------------------------------------------------------------------ against the real lands

@pytest.mark.parametrize("zone", ZONES)
def test_the_three_lands_pass_every_gate_that_can_be_derived(planned, zone):
    """The whole point of building the derived gates was to make the lands answer them. Anything
    still failing here is a real defect with a named module, not a tooling gap."""
    result = gates.run(planned[zone], only=gates.DERIVED)
    assert result["ok"], gates.report(result)


@pytest.mark.parametrize("zone", ZONES)
def test_no_land_is_promotable_without_its_evidence(planned, zone):
    """A land is not finished because its geometry is right."""
    assert not gates.promotable(planned[zone])


def test_the_report_names_the_blocking_gates():
    """"The park is not ready" is not a work item."""
    text = gates.report(gates.run({"name": "p", "modules": [], "routes": []}))
    assert "BLOCKED on" in text
    for name in sorted(gates.EVIDENCE):
        assert name in text
