"""Animal setpieces require anatomy evidence and a human-review packet."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import animal_quality
from mcbuild.gen import sloth


def test_hero_sloth_is_one_connected_anatomically_declared_setpiece():
    canvas = sloth.build({"seed": 0})
    result = animal_quality.assess(
        canvas.to_model(), generator="sloth", meta=canvas.meta,
        spec={"enforce": True, "_visual_review": True, "min_blocks": 650,
              "min_materials": 5,
              "required_features": ["branch", "face", "eyes", "mask", "limbs", "claws", "shag"]},
    )
    assert result["ok"], result["failures"]
    assert result["components"] == [684]


def test_an_enforced_animal_cannot_skip_visual_evidence():
    canvas = sloth.build({"seed": 0})
    result = animal_quality.assess(
        canvas.to_model(), generator="sloth", meta=canvas.meta,
        spec={"enforce": True, "min_blocks": 650, "min_materials": 5,
              "required_features": ["face"]},
    )
    assert not result["ok"]
    assert any("visual_review" in failure for failure in result["failures"])

