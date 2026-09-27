"""Shared quality briefs, visual evidence, journey contracts, and design grammars."""
from __future__ import annotations

import numpy as np
import pytest

from mcbuild import design, journey, nbt, schem
from mcbuild import scenario
from mcbuild import golden
from mcbuild.grammar import facade_profile, path_route, sculpture_masses, terraced_slope


def _model():
    palette = [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone"),
               nbt.block_state("minecraft:lantern", hanging="false")]
    ids = np.zeros((3, 1, 3), dtype=np.int32)
    ids[0, 0, :] = 1
    ids[1, 0, 1] = 2
    return schem.Model(ids, palette)


def test_design_assessment_records_real_massing_material_and_light_evidence():
    result = design.assess(_model(), {"purpose": "path", "hierarchy": "supporting",
                                      "style": "midway", "quality": {"min_blocks": 4,
                                      "min_materials": 2, "min_lights": 1}})
    assert result["ok"]
    assert result["metrics"]["massing"] == {"width": 3, "height": 2, "depth": 1, "fill_ratio": 0.6667}
    assert result["metrics"]["light_blocks"] == 1
    assert result["metrics"]["composition"]["base_middle_crown_mass"] == [0.75, 0.25, 0.0]
    assert result["metrics"]["composition"]["top_silhouette_perimeter"] == 8


def test_only_explicit_enforcement_turns_a_quality_target_into_a_failure():
    assert not design.assess(_model(), {"quality": {"min_height": 9}})["ok"]
    with pytest.raises(ValueError, match="quality brief failed"):
        design.assess(_model(), {"enforce": True, "quality": {"min_height": 9}})


def test_journey_requires_a_standable_entry_and_reaches_each_declared_stop():
    got = journey.evaluate(_model(), {"entry": [0, 1, 0], "destinations": [[2, 1, 0]]}, (10, 60, 20))
    assert got["ok"]
    assert got["entry_world"] == [10, 61, 20]
    assert got["destinations"][0]["world"] == [12, 61, 20]


def test_grammars_make_connectivity_and_hierarchy_explicit():
    assert facade_profile(7, "gable") == [4, 5, 6, 7, 6, 5, 4]
    route = path_route([(0, 0), (2, 0), (2, 2)])
    assert route == [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]
    assert terraced_slope(4, 7) == [0, 1, 1, 2, 2, 3, 4]
    assert sculpture_masses(9, [3, 5, 2]) == [(0, 3), (4, 5), (8, 2)]


def test_visual_packet_has_four_angles_and_a_silhouette(tmp_path):
    paths = design.render_packet(_model(), tmp_path, "review")
    assert len(paths) == 5
    assert all(__import__("pathlib").Path(path).exists() for path in paths)


def test_scenarios_only_certify_the_evidence_they_can_actually_see():
    design_evidence = {"metrics": {"light_blocks": 2}, "journey": {"declared": True, "ok": True}}
    mechanics = {"families": {"rail": ["powered_rail"], "redstone": ["redstone_wire"]}}
    assert scenario.evaluate(["public_visit", "night_visit", "rail_ride", "redstone_interaction"],
                             design_evidence, mechanics)["ok"]
    assert not scenario.evaluate(["public_visit"], {"journey": {"declared": False}}, mechanics)["ok"]


def test_golden_comparison_reports_visual_change_without_judging_it(tmp_path):
    paths = design.render_packet(_model(), tmp_path, "golden")
    same = golden.compare(paths[0], paths[0])
    changed = golden.compare(paths[0], paths[1])
    assert same["changed_fraction"] == 0.0
    assert changed["compatible"] and changed["changed_fraction"] > 0
