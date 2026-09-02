"""Versioned world briefs: regions, infrastructure, plots, and generator-facing modules."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from .grammar import path_route
from .infrastructure import route as compile_route

FORMAT = 1


def _box(item: dict, name: str) -> tuple[int, int, int, int]:
    box = item.get("bounds")
    if not isinstance(box, list) or len(box) != 4 or not all(isinstance(v, int) for v in box):
        raise ValueError(f"{name}.bounds must be [x0,z0,x1,z1]")
    x0, z0, x1, z1 = box
    if x1 < x0 or z1 < z0: raise ValueError(f"{name}.bounds is inverted")
    return tuple(box)


def _intersects(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _route_footprint(cells, width: int) -> list[list[int]]:
    """All paved cells, not merely the deceptive centreline used for route planning."""
    low = -(width // 2); high = low + width - 1
    return [list(point) for point in sorted({(x + dx, z + dz) for x, z in cells
                                             for dx in range(low, high + 1)
                                             for dz in range(low, high + 1)})]


def compile(spec: dict) -> dict:
    """Normalize and validate a world brief without generating blocks.

    A world has named regions, plots contained by one region, and named infrastructure routes.
    Module generation remains delegated to the existing themed generators or blueprint adapters.
    """
    if not isinstance(spec, dict): raise ValueError("world spec must be an object")
    name = spec.get("name")
    if not isinstance(name, str) or not name: raise ValueError("world spec needs a name")
    # Worlds in this project are Skyblock developments, not infinite terrain maps.  Coordinates
    # are local to a declared island anchor and every region must fit a known build envelope.
    site = spec.get("site", {})
    if not isinstance(site, dict): raise ValueError("site must be an object")
    anchor = site.get("anchor", [0, 0, 0])
    if not isinstance(anchor, list) or len(anchor) != 3 or not all(isinstance(v, int) for v in anchor):
        raise ValueError("site.anchor must be [x,y,z]")
    mode = site.get("mode", "skyblock")
    if mode != "skyblock": raise ValueError("this compiler currently supports skyblock sites only")
    plane = int(site.get("build_plane", anchor[1]))
    entries = site.get("entry_points", [])
    if not isinstance(entries, list) or any(not isinstance(p, list) or len(p) != 2 for p in entries):
        raise ValueError("site.entry_points must be [[x,z], ...]")
    regions, plots = spec.get("regions", []), spec.get("plots", [])
    if not isinstance(regions, list) or not regions: raise ValueError("world spec needs regions")
    region_boxes, names = {}, set()
    for region in regions:
        if not isinstance(region, dict) or not isinstance(region.get("name"), str) or region["name"] in names:
            raise ValueError("regions need unique names")
        names.add(region["name"]); region_boxes[region["name"]] = _box(region, f"region {region['name']}")
    envelope = site.get("bounds")
    if envelope is None:
        envelope = [min(b[0] for b in region_boxes.values()), min(b[1] for b in region_boxes.values()),
                    max(b[2] for b in region_boxes.values()), max(b[3] for b in region_boxes.values())]
    sx0, sz0, sx1, sz1 = _box({"bounds": envelope}, "site")
    for region_name, (x0, z0, x1, z1) in region_boxes.items():
        if not (sx0 <= x0 <= x1 <= sx1 and sz0 <= z0 <= z1 <= sz1):
            raise ValueError(f"region {region_name} is outside the Skyblock site envelope")
    protected = [list(_box({"bounds": item}, "protected")) for item in site.get("protected", [])]
    checked_plots, plot_names = [], set()
    for plot in plots:
        if (not isinstance(plot, dict) or plot.get("region") not in region_boxes or not plot.get("name")
                or plot["name"] in plot_names):
            raise ValueError("plots need name and known region")
        plot_names.add(plot["name"])
        x0, z0, x1, z1 = _box(plot, f"plot {plot['name']}")
        rx0, rz0, rx1, rz1 = region_boxes[plot["region"]]
        if not (rx0 <= x0 <= x1 <= rx1 and rz0 <= z0 <= z1 <= rz1):
            raise ValueError(f"plot {plot['name']} is outside region {plot['region']}")
        bounds = [x0, z0, x1, z1]
        if any(_intersects(bounds, item) for item in protected):
            raise ValueError(f"plot {plot['name']} consumes a protected Skyblock area")
        if any(_intersects(bounds, other["bounds"]) for other in checked_plots):
            raise ValueError(f"plot {plot['name']} overlaps an existing plot")
        checked_plots.append({"name": plot["name"], "region": plot["region"], "bounds": bounds,
                              "zone": plot.get("zone", "mixed"), "style": plot.get("style", "civic")})
    routes = []
    route_names = set()
    for route in spec.get("routes", []):
        name_ = route.get("name") if isinstance(route, dict) else None
        points = route.get("points") if isinstance(route, dict) else None
        width = int(route.get("width", 3)) if isinstance(route, dict) else 0
        if not name_ or name_ in route_names or width < 1 or not isinstance(points, list):
            raise ValueError("routes need unique name, positive width, and points")
        route_names.add(name_)
        route_points = [tuple(map(int, p)) for p in points]
        if any(len(p) not in {2, 3} for p in route_points) or len({len(p) for p in route_points}) != 1:
            raise ValueError(f"route {name_} points are consistently [x,z] or [x,y,z]")
        geometry = None
        if len(route_points[0]) == 3:
            infra_spec = {"kind": route.get("kind", "path"), "width": width,
                          "points": [list(p) for p in route_points], "support_every": route.get("support_every", 6)}
            if "rails" in route: infra_spec["rails"] = route["rails"]
            geometry = compile_route(infra_spec)
            cells = [(x, z) for x, _y, z in geometry["courses"]]
        else:
            cells = path_route(route_points)
        footprint = _route_footprint(cells, width)
        if any(not (sx0 <= x <= sx1 and sz0 <= z <= sz1) for x, z in footprint):
            raise ValueError(f"route {name_} leaves the Skyblock site envelope at its declared width")
        if any(any(item[0] <= x <= item[2] and item[1] <= z <= item[3] for item in protected)
               for x, z in footprint):
            raise ValueError(f"route {name_} crosses a protected Skyblock area")
        routes.append({"name": name_, "kind": route.get("kind", "path"), "width": width,
                       "cells": [list(point) for point in cells], "footprint": footprint,
                       **({"geometry": geometry} if geometry else {})})
    corridors = []
    corridor_names = set()
    for corridor in spec.get("view_corridors", []):
        name_ = corridor.get("name") if isinstance(corridor, dict) else None
        points = corridor.get("points") if isinstance(corridor, dict) else None
        width = int(corridor.get("width", 1)) if isinstance(corridor, dict) else 0
        if not name_ or name_ in corridor_names or width < 1 or not isinstance(points, list):
            raise ValueError("view corridors need unique name, positive width, and points")
        corridor_names.add(name_)
        cells = path_route([tuple(map(int, p)) for p in points])
        footprint = _route_footprint(cells, width)
        if any(not (sx0 <= x <= sx1 and sz0 <= z <= sz1) for x, z in footprint):
            raise ValueError(f"view corridor {name_} leaves the Skyblock site envelope")
        corridors.append({"name": name_, "width": width, "cells": [list(p) for p in cells], "footprint": footprint})
    modules = []
    module_names = set()
    for module in spec.get("modules", []):
        if (not isinstance(module, dict) or not module.get("name") or module["name"] in module_names
                or module.get("plot") not in {p["name"] for p in checked_plots}):
            raise ValueError("modules need name and known plot")
        module_names.add(module["name"])
        entry = {"name": module["name"], "plot": module["plot"], "generator": module.get("generator"),
                 "params": dict(module.get("params", {})), "role": module.get("role", "building"),
                 "blueprint": module.get("blueprint"), "depends_on": sorted(module.get("depends_on", [])),
                 "style": module.get("style"), "access_points": [list(map(int, p)) for p in module.get("access_points", [])]}
        if module.get("anchors"):
            entry["anchors"] = list(module["anchors"])
        if any(len(point) != 2 for point in entry["access_points"]):
            raise ValueError(f"module {module['name']} access_points are [x,z]")
        if module.get("footprint"):
            fp = module["footprint"]
            at = module.get("at")
            if not isinstance(fp, list) or len(fp) != 2 or not isinstance(at, list) or len(at) != 2:
                raise ValueError(f"module {module['name']} footprint needs [width,depth] and at [x,z]")
            w, d = map(int, fp); x, z = map(int, at)
            plot = next(p for p in checked_plots if p["name"] == module["plot"])
            if w < 1 or d < 1 or not (plot["bounds"][0] <= x <= x + w - 1 <= plot["bounds"][2]
                                       and plot["bounds"][1] <= z <= z + d - 1 <= plot["bounds"][3]):
                raise ValueError(f"module {module['name']} footprint does not fit its plot")
            occupied = {(xx, zz) for xx in range(x, x + w) for zz in range(z, z + d)}
            blocked = [c["name"] for c in corridors if occupied & {tuple(p) for p in c["footprint"]}]
            if blocked:
                raise ValueError(f"module {module['name']} blocks protected view corridor(s): {', '.join(blocked)}")
            entry.update({"at": [x, z], "footprint": [w, d]})
        modules.append(entry)
    payload = {"format": FORMAT, "name": name, "seed": int(spec.get("seed", 0)),
               "site": {"mode": mode, "anchor": anchor, "build_plane": plane, "bounds": [sx0, sz0, sx1, sz1],
                        "entry_points": [list(map(int, point)) for point in entries],
                        "protected": protected},
               "regions": [{"name": n, "bounds": list(b)} for n, b in sorted(region_boxes.items())],
               "plots": checked_plots, "routes": routes, "view_corridors": corridors, "modules": modules,
               "world_rules": {"chunk_size": int(spec.get("chunk_size", 16)),
                               "build_phases": ["platform", "infrastructure", "shell", "interior", "detail", "review"]}}
    payload["digest"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


#: A WorldSpec role says what a module IS to the park; a mechanics role says which construction
#: contract its blocks are judged against. They are two vocabularies for one concept, and letting
#: a config carry the first into the second is how a plan compiles and then refuses to build:
#: `landmark`, `arrival` and `service` have no mechanics contract, so every such module raised
#: "unknown mechanics role" at the very last step of its own pipeline. Mapped in ONE place, the
#: way `proportions.measure` and `rubric.score` share an entry point, so the two cannot drift.
MECHANICS_ROLE = {
    "landmark": ["building"],      # a landmark is a building whose job is its silhouette
    "arrival": ["building", "path"],  # a threshold is circulation with a roof on it
    "service": ["building"],
    "building": ["building"], "ride": ["ride"], "path": ["path"], "sculpture": ["sculpture"],
}


def emit_configs(plan: dict, directory: str | Path) -> list[str]:
    """Emit strict, frozen generator configs from a compiled WorldSpec.

    Generator parameters stay explicit in the WorldSpec. A module without a generator cannot be
    emitted: decorative intent must never become a silently empty artifact.
    """
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for module in plan.get("modules", []):
        if not module.get("generator"):
            raise ValueError(f"{module['name']}: WorldSpec module has no generator")
        blueprint = module.get("blueprint")
        anchors = list(module.get("anchors", []))
        if blueprint:
            from .blueprint import compile as compile_blueprint
            anchors = compile_blueprint({"name": module["name"], **blueprint})["anchors"]
        if not anchors:
            raise ValueError(f"{module['name']}: strict WorldSpec emission needs blueprint or typed anchors")
        role = module.get("role", "building")
        cfg = {"name": module["name"], "gen": module["generator"], "params": module.get("params", {}),
               "roles": MECHANICS_ROLE.get(role, ["building"]), "world_contract": True,
               "depends_on": module.get("depends_on", []), "anchors": anchors,
               "blueprint": blueprint,
               "design": {"purpose": module.get("role", "building"),
                          **({"style": module["style"]} if module.get("style") else {})}}
        safe = "".join(c.lower() if c.isalnum() else "_" for c in module["name"]).strip("_")
        path = directory / f"{safe}.yaml"
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        paths.append(str(path))
    return paths
