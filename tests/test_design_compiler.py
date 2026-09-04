"""Typed composition interfaces and deterministic quality-coordination metadata."""
from __future__ import annotations

from mcbuild.design_compiler import (Anchor, anchors, capability_matrix, check_links, check_world_links, compatible,
                                     fingerprint, genome, impact, variation, write_dashboard, world_anchors)


def test_anchor_interfaces_are_typed_and_width_compatible():
    source = anchors([{"name": "gate", "kind": "door", "position": [1, 2, 3], "width": 3}])
    path = Anchor("main_path", "path", (0, 0, 0), width=3)
    narrow = Anchor("narrow", "path", (0, 0, 0), width=2)
    assert compatible(source[0], path)
    assert not compatible(source[0], narrow)
    assert check_links(source, [{"from": "gate", "to": "main_path"}], {"main_path": path}) == []
    assert check_links(source, [{"from": "gate", "to": "narrow"}], {"narrow": narrow})[0]["reason"] == "incompatible kind or width"


def test_genome_variation_and_fingerprint_are_stable():
    assert genome("frontier")["facades"]
    assert variation("Mine Head", "facade", ["gable", "stepped"]) == variation("Mine Head", "facade", ["gable", "stepped"])
    assert fingerprint({"a": 1, "b": [2]}) == fingerprint({"b": [2], "a": 1})


def test_world_links_reject_unconnected_or_incompatible_modules():
    modules = [
        {"name": "Hall", "at": [10, 64, 10], "anchors": [{"name": "door", "kind": "door", "position": [0, 1, 0], "width": 3}]},
        {"name": "Path", "at": [11, 64, 10], "anchors": [{"name": "end", "kind": "path", "position": [0, 1, 0], "width": 3}]},
    ]
    assert world_anchors(modules)["Hall.door"].position == (10, 65, 10)
    assert check_world_links(modules, [{"from": "Hall.door", "to": "Path.end"}]) == []
    modules[1]["at"] = [20, 64, 10]
    assert "apart" in check_world_links(modules, [{"from": "Hall.door", "to": "Path.end"}])[0]["reason"]


def test_impact_and_capability_matrix_make_missing_work_visible(tmp_path):
    assert impact({"modules": {"A": "one", "B": "same"}}, {"modules": {"B": "same", "C": "new", "A": "two"}}) == {
        "added": ["C"], "removed": [], "changed": ["A"], "unaffected": ["B"]}
    caps = capability_matrix(mechanics={"families": {"redstone": ["redstone_wire"]}},
                             design={"brief": {"purpose": "ride"}, "journey": {"declared": True, "ok": True}},
                             anchors_=[Anchor("entry", "entry", (0, 0, 0))])
    assert caps["purpose"] and caps["journey"] and caps["redstone_declared"]
    path = write_dashboard(tmp_path / "dashboard.html", "Plan", [{"name": "A", "capabilities": caps}])
    assert "Plan" in (tmp_path / "dashboard.html").read_text(encoding="utf-8") and path.endswith("dashboard.html")
