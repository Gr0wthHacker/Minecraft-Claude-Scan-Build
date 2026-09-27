"""The park cannot create a public thing without naming its purpose and access."""
from __future__ import annotations

import os

import pytest

from mcbuild import park_contracts


def _front(module):
    return (10, 20)


def _inside(module):
    return (9, 20)


def test_every_public_type_receives_a_clear_purpose_and_access_candidates():
    modules = [
        {"name": "Ride", "gen": "coaster", "kind": "coaster", "at": [0, 203, 0], "params": {"land": "frontier"}},
        {"name": "Gate", "gen": "park", "kind": "gate", "at": [0, 203, 0], "edge": "north", "params": {"land": "midway"}},
        {"name": "Paths", "gen": "park", "kind": "paths", "at": [0, 203, 0], "params": {"land": "hollow"}},
    ]
    park_contracts.annotate(modules, _front, _inside)
    assert modules[0]["park_contract"]["purpose"] == "ride"
    assert modules[0]["park_contract"]["access_candidates"] == [[10, 204, 20]]
    assert modules[1]["park_contract"]["access_candidates"] == [[10, 204, 20], [9, 204, 20]]
    assert not modules[2]["park_contract"]["requires_path"]
    assert park_contracts.missing(modules) == []
    assert park_contracts.inaccessible(modules, {(10, 20)}) == []


def test_access_validator_names_the_public_module_with_no_paved_candidate():
    modules = [{"name": "Ride", "gen": "coaster", "kind": "coaster", "at": [0, 203, 0],
                "params": {"land": "frontier"}}]
    park_contracts.annotate(modules, _front, _inside)
    assert park_contracts.inaccessible(modules, set()) == ["Ride"]


@pytest.mark.parametrize("zone,island,world", [
    ("midway", "newisle", "out/newisle.litematic"),
    ("frontier", "islandleft", "out/islandleft.litematic"),
    ("hollow", "islandright", "out/islandright.litematic"),
])
def test_every_real_park_public_contract_has_a_generated_paved_approach(zone, island, world):
    """Purpose/access metadata must describe the actual path network, not a hand-waved doorway."""
    if not os.path.exists(world):
        pytest.skip(f"missing captured park world {world}")
    from mcbuild import planner
    from mcbuild.gen import park
    from mcbuild.gen.vertical import World
    plan = planner.make(zone, world, name=f"_contract_{zone}", theme=zone, island=island, plane=203)
    paths = next(module for module in plan.modules if module["kind"] == "paths")
    drawn = World()
    park.BUILDERS["paths"](drawn, {**park.PARK, **paths["params"], "at": paths["at"]}, None)
    y = paths["at"][1] - 1
    paving = {(x, z) for (x, yy, z) in drawn.cells if yy == y}
    # The surface check answers about the surface. A module on another band - the Hollow's
    # Ossuary is twenty courses under its market - has its approach on its own landing, and
    # `test_vertical_park` is what proves a shaft reaches it.
    assert not park_contracts.inaccessible(plan.modules, paving, plane=paths["at"][1])
