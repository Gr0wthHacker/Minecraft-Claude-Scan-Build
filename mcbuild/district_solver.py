"""District-scale alternative layouts built from explainable spatial scores."""
from __future__ import annotations

from .spatial import choose


def alternatives(modules, candidates, *, route_cells=(), protected=(), view_cells=()):
    """Return best flow, skyline, cost, and balanced options without silently picking one."""
    results = []
    for module in modules:
        result = choose(module, candidates[module["name"]], route_cells=route_cells, protected=protected, view_cells=view_cells)
        if not result["ok"]: return {"ok": False, "module": module["name"], "repairs": result["repairs"]}
        results.append(result["best"])
    def score(kind):
        if kind == "flow": return sum(item["score"] for item in results)
        if kind == "cost": return -sum(item["score"] - 50 for item in results)
        if kind == "skyline": return sum(1 for item in results if item["facing"] in {"north", "south"})
        return sum(item["score"] for item in results) - len(results) * 5
    return {"ok": True, "alternatives": {kind: {"placements": results, "score": score(kind)}
                                             for kind in ("flow", "skyline", "cost", "balanced")}}
