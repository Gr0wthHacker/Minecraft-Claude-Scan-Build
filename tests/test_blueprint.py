"""Program-driven architecture and district composition contracts."""
from __future__ import annotations

import pytest

from mcbuild import blueprint, district


def test_ride_station_has_real_rooms_interfaces_and_supports():
    plan = blueprint.compile({"name": "Ghost Station", "program": "ride_station", "style": "hollow",
                              "width": 13, "depth": 17, "floors": 2})
    assert plan["quality"]["ok"]
    assert {room["name"] for room in plan["rooms"]} == {"queue", "boarding", "control", "exit"}
    assert {anchor["name"] for anchor in plan["anchors"]} >= {
        "public_entry", "public_exit", "service_access", "queue_entry", "boarding", "ride_exit"}
    assert plan["facade"]["profile"][6] > plan["facade"]["profile"][0]
    assert plan["structure"]["max_clear_span"] <= 6


def test_program_compiler_rejects_too_shallow_or_unknown_buildings():
    with pytest.raises(ValueError, match="needs"):
        blueprint.compile({"name": "Tiny Diner", "program": "restaurant", "width": 9, "depth": 8})
    with pytest.raises(ValueError, match="unknown building program"):
        blueprint.compile({"name": "Unknown", "program": "anything", "width": 9, "depth": 20})


def test_district_contract_rejects_ride_without_player_flow_interfaces():
    station = blueprint.compile({"name": "Station", "program": "ride_station", "width": 13, "depth": 17})
    module = {"name": "Station", "role": "ride", "at": [0, 64, 0], "anchors": station["anchors"]}
    path = {"name": "Promenade", "role": "path", "at": [6, 64, -1],
            "anchors": [{"name": "end", "kind": "path", "position": [0, 1, 0], "width": 3}]}
    report = district.audit([module, path], [{"from": "Station.public_entry", "to": "Promenade.end"}],
                            required_routes=[{"from": "Station.public_entry", "to": "Promenade.end"}])
    assert report["ok"]
    broken = district.audit([{"name": "Broken", "role": "ride", "at": [0, 64, 0], "anchors": []}], [])
    assert not broken["ok"] and any("queue_entry" in item["reason"] for item in broken["failures"])
