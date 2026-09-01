"""Parallel generation uses isolated stages and a single deterministic publisher."""
from __future__ import annotations

import json

import pytest

from mcbuild import parallel, planner, scan
from mcbuild.gen.canvas import Canvas


def _approved_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(planner, "PLANS", tmp_path / "plans")
    monkeypatch.setattr(parallel, "ROOT", tmp_path / "parallel")
    plan = planner.Plan("Park Test", "midway", "parallel test")
    plan.approved = True
    plan.modules = [
        {"name": "Alpha Gate", "gen": "lamp", "kind": "lamp", "at": [0, 64, 0],
         "size": [1, 1, 1], "params": {"land": "alpha"}},
        {"name": "Beta Path", "gen": "lamp", "kind": "lamp", "at": [10, 64, 0],
         "size": [1, 1, 1], "params": {"land": "beta"}},
    ]
    plan.save()
    return plan


def _stage(root, lane, name, origin):
    out = root / "park_test" / "lanes" / lane / "out"
    out.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(1, 1, 1)
    canvas.put(0, 0, 0, canvas.raw_state("stone"))
    scan.save_pair(str(out / f"{name}.litematic"), canvas.to_model(), {
        "origin": {"x": origin[0], "y": origin[1], "z": origin[2]},
        "size": {"x": 1, "y": 1, "z": 1}, "generated_by": "test",
    }, name=name)
    artifact = out / f"{name}.litematic"
    (root / "park_test" / "lanes" / lane / parallel.EVIDENCE).write_text(json.dumps({
        "format": 1, "plan": "Park Test", "lane": lane,
        "artifacts": [{"name": name, "artifact": artifact.name,
                       "litematic_sha256": parallel._file_digest(artifact),
                       "sidecar_sha256": parallel._file_digest(artifact.with_suffix(".scan.json")),
                       "audit": {"ok": True, "problems": 0, "leaks": 0, "blocks": 1,
                                 "components": [1]}, "mechanics": {}, "rendered": False}],
    }), encoding="utf-8")


def test_prepare_freezes_configs_and_partitions_theme_lands(tmp_path, monkeypatch):
    _approved_plan(tmp_path, monkeypatch)
    manifest_path = parallel.prepare("Park Test")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["lanes"] == {"alpha": ["Alpha Gate"], "beta": ["Beta Path"]}
    assert all((manifest_path.parent / m["config"]).exists() for m in manifest["modules"])
    with pytest.raises(FileExistsError, match="frozen"):
        parallel.prepare("Park Test")


def test_scope_rejects_files_outside_the_assigned_lane(tmp_path, monkeypatch):
    _approved_plan(tmp_path, monkeypatch)
    parallel.prepare("Park Test")
    assert parallel.check_paths("Park Test", "alpha", ["mcbuild/gen/park.py"]) == ["mcbuild/gen/park.py"]
    assert parallel.check_paths("Park Test", "alpha",
                                [parallel.ROOT / "park_test" / "lanes" / "alpha" / "out" / "Alpha Gate.litematic"]) == []


def test_validate_rejects_cross_lane_collisions(tmp_path, monkeypatch):
    _approved_plan(tmp_path, monkeypatch)
    parallel.prepare("Park Test")
    _stage(parallel.ROOT, "alpha", "Alpha Gate", (0, 64, 0))
    _stage(parallel.ROOT, "beta", "Beta Path", (0, 64, 0))
    result = parallel.validate("Park Test")
    assert not result["ok"]
    assert result["cross_lane_conflicts"] == [{"position": [0, 64, 0], "first": "Alpha Gate", "second": "Beta Path"}]
    with pytest.raises(ValueError, match="cross-lane conflicts=1"):
        parallel.assemble("Park Test", out_dir=str(tmp_path / "published"))


def test_assemble_publishes_one_deterministic_composite(tmp_path, monkeypatch):
    _approved_plan(tmp_path, monkeypatch)
    parallel.prepare("Park Test")
    _stage(parallel.ROOT, "alpha", "Alpha Gate", (0, 64, 0))
    _stage(parallel.ROOT, "beta", "Beta Path", (10, 64, 0))
    decision = parallel.gate("Park Test")
    assert decision["promotable"]
    assert "local audit" in decision["verified"]
    path = parallel.promote("Park Test", out_dir=str(tmp_path / "published"), name="Park Complete")
    published = scan.load(path)
    assert published.origin == (0, 64, 0)
    assert published.model.shape_xyz == (11, 1, 1)
    assert int((published.model.ids > 0).sum()) == 2
    assert published.meta["staged_modules"] == ["Alpha Gate", "Beta Path"]
