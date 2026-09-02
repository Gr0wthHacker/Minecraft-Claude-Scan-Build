"""World-scale facilities remain bounded, sparse, and Skyblock-safe."""
from __future__ import annotations

import pytest

from mcbuild import (asset_catalog, blueprint_adapter, buildgraph, cache, composition, nbt, scan, schem,
                     world, worldassembly, worldexport, worldnav, worldspec)
import numpy as np


def _spec():
    return {"name": "Sky Park", "seed": 17,
            "site": {"anchor": [100, 72, -50], "build_plane": 72, "bounds": [0, 0, 96, 96],
                     "protected": [[46, 70, 50, 74]], "entry_points": [[2, 48]]},
            "regions": [{"name": "midway", "bounds": [0, 0, 48, 96]}, {"name": "frontier", "bounds": [49, 0, 96, 96]}],
            "plots": [{"name": "wheel", "region": "midway", "bounds": [5, 20, 30, 55], "style": "midway"},
                      {"name": "mine", "region": "frontier", "bounds": [55, 10, 90, 65], "style": "frontier"}],
            "routes": [{"name": "main", "kind": "path", "width": 5, "points": [[2, 48], [94, 48]]}],
            "modules": [{"name": "Wheel Landmark", "plot": "wheel", "generator": "bigwheel", "access_points": [[5, 48]]},
                        {"name": "Mine Coaster", "plot": "mine", "generator": "coaster", "access_points": [[55, 48]]}]}


def test_worldspec_is_bounded_to_a_skyblock_site_and_composes_routes():
    plan = worldspec.compile(_spec())
    assert plan["site"]["mode"] == "skyblock" and plan["site"]["build_plane"] == 72
    assert plan["routes"][0]["cells"][0] == [2, 48]
    assert composition.assess(plan)["ok"]
    assert worldnav.audit(plan)["ok"]
    bad = _spec(); bad["regions"][0]["bounds"] = [-1, 0, 48, 96]
    with pytest.raises(ValueError, match="outside the Skyblock"):
        worldspec.compile(bad)


def test_worldspec_rejects_wasteful_or_impossible_site_allocations():
    bad = _spec(); bad["plots"].append({"name": "duplicate-space", "region": "midway", "bounds": [5, 20, 30, 55]})
    with pytest.raises(ValueError, match="overlaps"):
        worldspec.compile(bad)
    bad = _spec(); bad["routes"][0]["points"] = [[0, 0], [96, 0]]
    with pytest.raises(ValueError, match="leaves the Skyblock"):
        worldspec.compile(bad)
    bad = _spec(); bad["modules"][0].update({"at": [25, 50], "footprint": [10, 10]})
    with pytest.raises(ValueError, match="does not fit"):
        worldspec.compile(bad)
    bad = _spec(); bad["view_corridors"] = [{"name": "wheel-view", "width": 3, "points": [[2, 48], [30, 48]]}]
    bad["modules"][0].update({"at": [5, 45], "footprint": [10, 10]})
    with pytest.raises(ValueError, match="blocks protected view"):
        worldspec.compile(bad)


def test_sparse_world_only_stores_occupied_chunks_and_hashes_them():
    w = world.SparseWorld(); w.put(0, 72, 0, "minecraft:stone"); w.put(65, 72, 0, "minecraft:lantern")
    assert w.summary()["chunks"] == 2 and w.get(1, 72, 0) == "minecraft:air"
    before = w.digest(); w.put(0, 72, 0, "minecraft:air")
    assert before != w.digest() and w.summary()["blocks"] == 1


def test_navigation_rejects_a_module_without_reachable_door_and_sparse_chunks_export(tmp_path):
    plan = worldspec.compile(_spec()); plan["modules"][0]["access_points"] = [[5, 5]]
    assert not worldnav.audit(plan)["ok"]
    w = world.SparseWorld(); w.put(0, 72, 0, "minecraft:oak_stairs[facing=north,half=top]")
    paths = worldexport.export_chunks(w, tmp_path, prefix="sky")
    assert len(paths) == 1 and __import__("pathlib").Path(paths[0]).exists()
    assert __import__("pathlib").Path(paths[0].replace(".litematic", ".scan.json")).exists()


def test_asset_cache_and_task_graph_make_incremental_parallel_work_safe():
    assert asset_catalog.resolve("station", "hollow")["roof"] == "gable"
    graph = buildgraph.schedule([{"name": "platform", "chunks": [[0, 4, 0]]},
                                 {"name": "station", "chunks": [[1, 4, 0]], "depends_on": ["platform"]}])
    assert graph["ok"] and graph["levels"] == [["platform"], ["station"]]
    old = {"artifacts": {"platform": {"key": "a"}, "station": {"key": "a", "depends_on": ["platform"]}}}
    new = {"artifacts": {"platform": {"key": "b"}, "station": {"key": "a", "depends_on": ["platform"]}}}
    assert cache.impacted(old, new)["dirty"] == ["platform", "station"]


def test_worldspec_emits_strict_generator_configs_with_blueprint_contracts(tmp_path):
    raw = _spec()
    raw["modules"][0].update({"role": "landmark", "params": {"radius": 14},
                                "blueprint": {"program": "gallery", "width": 11, "depth": 17, "style": "midway"}})
    raw["modules"][1].update({"role": "ride",
                                "blueprint": {"program": "ride_station", "width": 13, "depth": 17, "style": "frontier"}})
    plan = worldspec.compile(raw)
    paths = worldspec.emit_configs(plan, tmp_path)
    text = __import__("pathlib").Path(paths[0]).read_text(encoding="utf-8")
    assert "world_contract: true" in text and "public_entry" in text and "radius: 14" in text


def test_worldspec_accepts_a_real_elevation_aware_bridge_route():
    raw = _spec(); raw["routes"] = [{"name": "bridge", "kind": "bridge", "width": 3,
                                      "points": [[2, 70, 48], [20, 73, 48]], "support_every": 4}]
    plan = worldspec.compile(raw)
    assert plan["routes"][0]["geometry"]["supports"]
    assert plan["routes"][0]["geometry"]["anchors"]["end"] == [20, 73, 48]


def test_legacy_config_can_adopt_blueprint_and_assembled_world_uses_real_walk_rules(tmp_path):
    cfg, plan = blueprint_adapter.apply({"name": "Station", "gen": "coaster",
                                         "blueprint": {"program": "ride_station", "width": 11, "depth": 17}})
    assert plan["quality"]["ok"] and cfg["anchors"]
    ids = np.zeros((2, 1, 3), dtype=np.int32); ids[0, 0, :] = 1
    model = schem.Model(ids, [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone")])
    lit = tmp_path / "walk.litematic"
    scan.save_pair(str(lit), model, {"origin": {"x": 10, "y": 70, "z": 20}})
    report = worldassembly.validate([lit], entry=[10, 71, 20], destinations=[[12, 71, 20]])
    assert report["ok"] and report["reachable_cells"] == 3
