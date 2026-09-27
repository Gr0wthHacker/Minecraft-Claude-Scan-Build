"""Objective composition checks for world/district briefs before render review."""
from __future__ import annotations


def assess(world: dict) -> dict:
    """Check landmark hierarchy, density, and route coverage from semantic world data."""
    failures, warnings = [], []
    plots = world.get("plots", []); modules = world.get("modules", []); routes = world.get("routes", [])
    by_plot = {p["name"]: p for p in plots}
    for region in world.get("regions", []):
        rx0, rz0, rx1, rz1 = region["bounds"]
        area = (rx1 - rx0 + 1) * (rz1 - rz0 + 1)
        used = sum((p["bounds"][2] - p["bounds"][0] + 1) * (p["bounds"][3] - p["bounds"][1] + 1)
                   for p in plots if p["region"] == region["name"])
        ratio = used / area if area else 1
        if ratio > 0.85: failures.append(f"{region['name']}: plot density {ratio:.0%} leaves too little open space")
        elif ratio < 0.12: warnings.append(f"{region['name']}: plot density {ratio:.0%} may feel under-programmed")
    served = set()
    route_cells = {tuple(cell) for route in routes for cell in route.get("footprint", route["cells"])}
    for module in modules:
        plot = by_plot[module["plot"]]
        x0, z0, x1, z1 = plot["bounds"]
        if not any(x0 - 2 <= x <= x1 + 2 and z0 - 2 <= z <= z1 + 2 for x, z in route_cells):
            failures.append(f"{module['name']}: plot has no route approach")
        else: served.add(module["name"])
    # A landmark is a DECLARED role or plot zone, never a word that happens to be in a module's
    # name: read off the name this check could never fire, because no build is called "landmark".
    landmark_regions = {by_plot[m["plot"]]["region"] for m in modules
                        if m.get("role") == "landmark" or by_plot[m["plot"]].get("zone") in {"landmark", "sculpture"}}
    missing = {r["name"] for r in world.get("regions", [])} - landmark_regions
    if missing: warnings.append("regions with no named landmark: " + ", ".join(sorted(missing)))
    # Separate disconnected route components strand players even when every individual plot is
    # near *some* paving.  A component is deliberate only when declared as service/backstage.
    public = [set(map(tuple, r.get("footprint", r["cells"]))) for r in routes if r.get("kind") != "service"]
    components = []
    while public:
        current = public.pop(); changed = True
        while changed:
            changed = False
            for other in list(public):
                if current & other:
                    current |= other; public.remove(other); changed = True
        components.append(current)
    if len(components) > 1: failures.append(f"public routes have {len(components)} disconnected components")
    actual_area = sum((m.get("footprint", [0, 0])[0] * m.get("footprint", [0, 0])[1]) for m in modules)
    plot_area = sum((p["bounds"][2] - p["bounds"][0] + 1) * (p["bounds"][3] - p["bounds"][1] + 1) for p in plots)
    return {"ok": not failures, "failures": failures, "warnings": warnings,
            "route_cells": len(route_cells), "served_modules": sorted(served),
            "route_components": len(components), "declared_module_area": actual_area,
            "unallocated_plot_area": max(0, plot_area - actual_area)}
