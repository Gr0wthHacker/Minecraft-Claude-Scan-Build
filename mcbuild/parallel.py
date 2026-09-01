"""Agent-safe parallel generation for approved large build plans.

Agents do not edit shared configs or write into ``out/``.  The coordinator freezes an approved
plan into a manifest, assigns its modules to independent lanes, and emits read-only configs below
``out/parallel/<plan>/``.  Each worker writes only to its lane's staging directory.  A single,
deterministic assembler is the only process allowed to publish the combined design.

This is intentionally separate from :mod:`mcbuild.fleet`: fleet assigns *players* to place already
published designs; this module assigns *generation workers* without sharing mutable artifacts.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
from collections import defaultdict

import numpy as np

from . import audit, nbt, scan, schem
from .mechanics import manifest as mechanics_manifest
from .pipeline import Settings, run_config
from .planner import Plan, emit

ROOT = pathlib.Path("out/parallel")
MANIFEST = "parallel.json"
EVIDENCE = "evidence.json"


def _slug(value: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in value).strip("_") or "general"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _file_digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(plan_name: str) -> pathlib.Path:
    return ROOT / _slug(plan_name)


def _load(plan_name: str) -> tuple[pathlib.Path, dict]:
    root = _path(plan_name)
    path = root / MANIFEST
    if not path.exists():
        raise FileNotFoundError(f"no parallel manifest for {plan_name!r}; run parallel --prepare {plan_name}")
    return root, json.loads(path.read_text(encoding="utf-8"))


def _lanes(modules: list[dict]) -> dict[str, list[dict]]:
    """Group by world/land: park zones become independent lanes by construction."""
    grouped = defaultdict(list)
    for index, module in enumerate(modules):
        params = module.get("params", {})
        # A land is a real spatial partition in the theme park.  Other plans remain one coherent
        # lane unless their modules explicitly name a lane, avoiding guessed geometry boundaries.
        lane = module.get("lane") or params.get("land") or "general"
        grouped[_slug(str(lane))].append({"index": index, "name": module["name"]})
    return dict(sorted(grouped.items()))


def prepare(plan_name: str) -> pathlib.Path:
    """Freeze an approved plan into isolated configs and lane ownership metadata.

    Refuses to replace an existing staging manifest.  Regenerate a plan under a new name when its
    layout changes; mutating the inputs beneath agents is exactly the race this workflow prevents.
    """
    plan = Plan.load(plan_name)
    if not plan.approved:
        raise PermissionError(f"plan {plan_name} is not approved")
    root = _path(plan_name)
    manifest_path = root / MANIFEST
    if manifest_path.exists():
        raise FileExistsError(f"{manifest_path} already exists; its plan is frozen")
    configs = root / "configs"
    configs.mkdir(parents=True, exist_ok=False)
    written = emit(plan_name, out_dir=str(configs))
    lane_map = _lanes(plan.modules)
    from .design_compiler import check_world_links
    links = list(getattr(plan, "links", ()))
    interface_failures = check_world_links(plan.modules, links)
    if interface_failures:
        raise ValueError(f"plan has invalid typed interface links: {interface_failures}")
    # **A PARK PLAN WITH EMPTY ANCHORS IS NOT PREPARABLE.** PARK_OVERHAUL.md: "A plan cannot be
    # prepared or promoted when a public module has empty anchors." Freezing configs is the point
    # of no return - agents start generating against them - so the contract is checked HERE
    # rather than at promotion, where the cost of the answer is a park already built.
    if plan.theme in {"midway", "frontier", "hollow"}:
        from . import gates
        blocking = gates.run(dict(plan.__dict__), only={"interface", "route", "capacity"})
        if not blocking["ok"]:
            raise ValueError(
                "plan fails its own interface contract:\n" + gates.report(blocking)
                + "\n  run: python -m mcbuild plan --upgrade-interfaces " + plan_name)
    modules = []
    if len(written) != len(plan.modules):
        raise RuntimeError("emitter did not write exactly one config per planned module")
    for index, (module, config_path) in enumerate(zip(plan.modules, written)):
        lane = next(key for key, entries in lane_map.items() if any(e["index"] == index for e in entries))
        dependencies = list(module.get("depends_on", module.get("requires", ())))
        modules.append({"index": index, "name": module["name"], "lane": lane,
                        "config": str(pathlib.Path(config_path).relative_to(root)), "artifact": module["name"],
                        "config_digest": _file_digest(pathlib.Path(config_path)),
                        "depends_on": dependencies,
                        "owned_files": list(module.get("owned_files", ())),
                        "anchors": list(module.get("anchors", ()))})
    names = {m["name"] for m in modules}
    unknown = {d for m in modules for d in m["depends_on"]} - names
    if unknown:
        raise ValueError(f"plan names unknown dependency module(s): {', '.join(sorted(unknown))}")
    payload = {
        "format": 2,
        "plan": plan.name,
        "plan_digest": _digest(plan.__dict__),
        "modules": modules,
        "lanes": {lane: [entry["name"] for entry in entries] for lane, entries in lane_map.items()},
        "interface_links": links,
        "rule": "workers write only to lanes/<lane>/out; assembly is single-writer and plan-ordered",
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def scope(plan_name: str, lane: str) -> dict:
    """The only files an agent assigned to ``lane`` may modify or produce."""
    root, manifest = _load(plan_name)
    lane = _slug(lane)
    if lane not in manifest["lanes"]:
        raise KeyError(f"unknown lane {lane!r}; have {', '.join(manifest['lanes'])}")
    modules = [m for m in manifest["modules"] if m["lane"] == lane]
    return {
        "lane": lane,
        "read_only_configs": [m["config"] for m in modules],
        "write_root": str(pathlib.Path("lanes") / lane / "out"),
        "owned_source_files": sorted({p for m in modules for p in m.get("owned_files", ())}),
        "dependencies": sorted({d for m in modules for d in m.get("depends_on", ())}),
        "rule": "do not edit frozen configs, shared out/, or files owned by another lane",
    }


def check_paths(plan_name: str, lane: str, paths) -> list[str]:
    """Return paths outside a lane's declared source/output ownership.

    An orchestrator can pass changed paths from an agent's git diff before accepting work.  Staged
    output must remain below the lane root; source edits are opt-in per module through
    ``owned_files`` in the approved plan.
    """
    root, _manifest = _load(plan_name)
    rules = scope(plan_name, lane)
    write_root = (root / rules["write_root"]).resolve()
    owned = {pathlib.PurePosixPath(p).as_posix() for p in rules["owned_source_files"]}
    bad = []
    for raw in paths:
        path = pathlib.Path(raw)
        resolved = path.resolve()
        normal = pathlib.PurePosixPath(str(path).replace("\\", "/")).as_posix()
        if resolved == write_root or write_root in resolved.parents or normal in owned:
            continue
        bad.append(str(raw))
    return bad


def _evidence_path(root: pathlib.Path, lane: str) -> pathlib.Path:
    return root / "lanes" / lane / EVIDENCE


def _evidence(root: pathlib.Path, lane: str) -> dict:
    path = _evidence_path(root, lane)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"artifacts": []}


def _dependency_ready(root: pathlib.Path, manifest: dict, dependency: str) -> bool:
    module = next(m for m in manifest["modules"] if m["name"] == dependency)
    artifact = root / "lanes" / module["lane"] / "out" / f"{module['artifact']}.litematic"
    return artifact.exists() and artifact.with_suffix(".scan.json").exists()


def run_lane(plan_name: str, lane: str, *, render_sheet: bool = False) -> list[str]:
    """Generate one frozen lane. No path outside its stage directory is writable by this call."""
    root, manifest = _load(plan_name)
    lane = _slug(lane)
    if lane not in manifest["lanes"]:
        raise KeyError(f"unknown lane {lane!r}; have {', '.join(manifest['lanes'])}")
    out_dir = root / "lanes" / lane / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    evidence = []
    for module in manifest["modules"]:
        if module["lane"] != lane:
            continue
        config = root / module["config"]
        if not config.is_file() or root not in config.resolve().parents:
            raise RuntimeError(f"unsafe or missing frozen config {config}")
        if _file_digest(config) != module.get("config_digest"):
            raise RuntimeError(f"{module['name']}: frozen config changed; prepare a new plan instead")
        waiting = [d for d in module.get("depends_on", ()) if not _dependency_ready(root, manifest, d)]
        if waiting:
            raise RuntimeError(f"{module['name']}: waiting for dependency artifact(s): {', '.join(waiting)}")
        run_config(str(config), settings=Settings(out_dir=str(out_dir)), render_sheet=render_sheet,
                   verbose=False)
        artifact = out_dir / f"{module['artifact']}.litematic"
        if not artifact.exists() or not artifact.with_suffix(".scan.json").exists():
            raise RuntimeError(f"{module['name']}: generation did not create its sidecar pair")
        staged = scan.load(str(artifact))
        result = audit.audit(staged.model, ground=False)
        evidence.append({"name": module["name"], "artifact": artifact.name,
                         "litematic_sha256": _file_digest(artifact),
                         "sidecar_sha256": _file_digest(artifact.with_suffix(".scan.json")),
                         "audit": {"ok": result.ok, "problems": len(result.problems),
                                   "leaks": result.leaks, "blocks": result.blocks,
                                   "components": sorted(result.components, reverse=True)},
                         "mechanics": mechanics_manifest(staged.model, generator=None),
                         "design": staged.meta.get("design", {}),
                         "design_system": staged.meta.get("design_system", {}),
                         "rendered": bool(render_sheet)})
        written.append(str(artifact))
    _evidence_path(root, lane).write_text(json.dumps({"format": 1, "plan": plan_name,
        "lane": lane, "artifacts": evidence}, indent=2), encoding="utf-8")
    return written


def _world_cells(item: scan.Scan):
    """Yield world position and state tag for each placed cell in a staged artifact."""
    ox, oy, oz = item.origin
    for y, z, x in np.argwhere(item.model.ids > 0):
        index = int(item.model.ids[y, z, x])
        yield (int(x) + ox, int(y) + oy, int(z) + oz), item.model.palette[index]


def validate(plan_name: str) -> dict:
    """Check stage completeness and reject collisions between independently-owned lanes."""
    root, manifest = _load(plan_name)
    owners: dict[tuple, tuple[str, str]] = {}
    missing, cross_lane, evidence_failures = [], [], []
    loaded = []
    for module in manifest["modules"]:
        artifact = root / "lanes" / module["lane"] / "out" / f"{module['artifact']}.litematic"
        if not artifact.exists() or not artifact.with_suffix(".scan.json").exists():
            missing.append(module["name"])
            continue
        item = scan.load(str(artifact))
        loaded.append((module, item))
        for pos, _state in _world_cells(item):
            previous = owners.get(pos)
            if previous and previous[0] != module["lane"]:
                cross_lane.append({"position": list(pos), "first": previous[1], "second": module["name"]})
            else:
                owners.setdefault(pos, (module["lane"], module["name"]))
    for lane in manifest["lanes"]:
        records = {r.get("name"): r for r in _evidence(root, lane).get("artifacts", ())}
        for module in (m for m in manifest["modules"] if m["lane"] == lane):
            record = records.get(module["name"])
            if record is None:
                evidence_failures.append({"name": module["name"], "reason": "missing evidence"})
            elif not record.get("audit", {}).get("ok"):
                evidence_failures.append({"name": module["name"], "reason": "artifact audit failed"})
    return {"plan": plan_name, "expected": len(manifest["modules"]), "staged": len(loaded),
            "missing": missing, "cross_lane_conflicts": cross_lane, "evidence_failures": evidence_failures,
            "ok": not missing and not cross_lane and not evidence_failures}


def gate(plan_name: str) -> dict:
    """Return the evidence required before a staged plan can be promoted.

    The gate certifies what is mechanically knowable here: every artifact is present, immutable
    evidence exists, its local audit passed, and lane boundaries do not collide.  Route endpoints,
    ride kinematics, and visual judgement remain explicit plan-specific requirements rather than
    being falsely inferred from a block union.
    """
    root, manifest = _load(plan_name)
    status = validate(plan_name)
    families = set()
    quality_warnings = []
    for lane in manifest["lanes"]:
        for record in _evidence(root, lane).get("artifacts", ()):
            families.update(record.get("mechanics", {}).get("families", {}))
            assessment = record.get("design", {})
            if assessment and not assessment.get("ok", True):
                quality_warnings.append(record["name"])
    # **THE EIGHT PROMOTION GATES, FOR A PARK PLAN.** Staging evidence answers "did the agents
    # produce what they were told to"; it says nothing about whether the thing produced is a park
    # a guest can use. PARK_OVERHAUL.md names eight gates and calls them "promotion gates, not
    # optional polish", so a park plan is promotable only when both are satisfied - and the four
    # that need outside evidence BLOCK until it is supplied rather than passing quietly.
    park = None
    plan = Plan.load(plan_name)
    if plan.theme in {"midway", "frontier", "hollow"}:
        from . import gates as park_gates
        park = park_gates.run(dict(plan.__dict__))
    return {**status, "mechanics_families": sorted(families),
            "verified": ["frozen configs", "artifact hashes", "local audit", "cross-lane ownership"],
            "quality_warnings": quality_warnings,
            "park_gates": park,
            "requires_plan_specific_review": [
                "visitor routes and endpoints", "ride/entity behaviour", "visual composition and sightlines"],
            "promotable": status["ok"] and (park is None or park["ok"])}


def _shift_tile(tag, dx: int, dy: int, dz: int):
    """Copy a local tile entity into a composite-local coordinate system."""
    value = dict(tag.value)
    for key, delta in (("x", dx), ("y", dy), ("z", dz)):
        if key in value:
            old = value[key]
            value[key] = nbt.Tag(old.id, int(old.value) + delta)
    return nbt.Tag(tag.id, value, subtype=tag.subtype)


def assemble(plan_name: str, *, out_dir: str = "out", name: str | None = None) -> str:
    """Publish one plan-ordered composite after a clean cross-lane validation.

    Intentional overlaps within a lane are resolved first-writer-wins in the approved plan order,
    matching ``layers.slice_plan``. Cross-lane overlaps are always rejected: independent agents
    have no authority to decide one another's ownership.
    """
    status = validate(plan_name)
    if not status["ok"]:
        raise ValueError(f"parallel stage is not assemblable: missing={status['missing']}, "
                         f"cross-lane conflicts={len(status['cross_lane_conflicts'])}")
    root, manifest = _load(plan_name)
    cells, tile_entities, contested = {}, {}, 0
    for module in manifest["modules"]:
        artifact = root / "lanes" / module["lane"] / "out" / f"{module['artifact']}.litematic"
        item = scan.load(str(artifact))
        won = set()
        for pos, state in _world_cells(item):
            if pos in cells:
                contested += 1
                continue
            cells[pos] = state
            won.add(pos)
        ox, oy, oz = item.origin
        for tile in item.model.tile_entities:
            value = tile.value
            try:
                world_pos = (int(value["x"].value) + ox, int(value["y"].value) + oy,
                             int(value["z"].value) + oz)
            except (KeyError, TypeError, ValueError):
                continue
            if world_pos in won:
                tile_entities[world_pos] = tile
    if not cells:
        raise ValueError("parallel stage contains no blocks")
    xs, ys, zs = zip(*cells)
    origin = min(xs), min(ys), min(zs)
    xmax, ymax, zmax = max(xs), max(ys), max(zs)
    ids = np.zeros((ymax - origin[1] + 1, zmax - origin[2] + 1, xmax - origin[0] + 1), np.int32)
    palette = [nbt.block_state("minecraft:air")]
    states = {nbt.state_key(palette[0]): 0}
    for (x, y, z), state in cells.items():
        key = nbt.state_key(state)
        index = states.get(key)
        if index is None:
            index = len(palette); states[key] = index; palette.append(state)
        ids[y - origin[1], z - origin[2], x - origin[0]] = index
    tiles = [_shift_tile(tile, -origin[0], -origin[1], -origin[2]) for _pos, tile in tile_entities.items()]
    composite = schem.Model(ids, palette, tile_entities=tiles)
    output_name = name or f"{plan_name.title()} Complete"
    out = pathlib.Path(out_dir) / f"{output_name}.litematic"
    out.parent.mkdir(parents=True, exist_ok=True)
    scan.save_pair(str(out), composite, {
        "origin": {"x": origin[0], "y": origin[1], "z": origin[2]},
        "size": {"x": composite.shape_xyz[0], "y": composite.shape_xyz[1], "z": composite.shape_xyz[2]},
        "generated_by": "mcbuild.parallel",
        "parallel_plan": plan_name,
        "parallel_manifest": str((root / MANIFEST).as_posix()),
        "staged_modules": [m["name"] for m in manifest["modules"]],
        "contested_within_lane": contested,
        "assembly": "first writer wins in approved plan order",
    }, name=output_name)
    return str(out)


def promote(plan_name: str, *, out_dir: str = "out", name: str | None = None) -> str:
    """Publish only after the parallel acceptance gate is clean."""
    result = gate(plan_name)
    if not result["promotable"]:
        park = result.get("park_gates")
        if park and not park["ok"]:
            from . import gates as park_gates
            raise ValueError("promotion refused by the park gates:\n"
                             + park_gates.report(park))
        raise ValueError("parallel promotion refused; inspect `mcbuild parallel --validate`")
    return assemble(plan_name, out_dir=out_dir, name=name)


def dashboard(plan_name: str) -> str:
    """Write a static reviewer dashboard from staged lane evidence."""
    from .design_compiler import write_dashboard
    root, manifest = _load(plan_name)
    records = {}
    for lane in manifest["lanes"]:
        records.update({record.get("name"): record for record in _evidence(root, lane).get("artifacts", ())})
    modules = []
    for module in manifest["modules"]:
        record = records.get(module["name"], {})
        system = record.get("design_system", {})
        modules.append({"name": module["name"], "lane": module["lane"],
                        "fingerprint": system.get("fingerprint", ""),
                        "capabilities": system.get("capabilities", {})})
    return write_dashboard(root / "review.html", f"Parallel review: {plan_name}", modules)
