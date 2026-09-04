"""Universal admission contract for modules entering a composed Skyblock world."""
from __future__ import annotations

from .design_compiler import anchors


def assess(config: dict, model, *, mechanics: dict, design: dict) -> dict:
    """Make absent composition evidence visible; enforce only when requested by a world plan."""
    declared = anchors(config.get("anchors"))
    roles = set(config.get("roles", []))
    failures = []
    if not config.get("name"): failures.append("missing stable module name")
    if not config.get("gen") and not config.get("source"): failures.append("missing generator/source")
    if not design.get("brief", {}).get("purpose"): failures.append("missing design purpose")
    if not declared and config.get("world_contract", False): failures.append("missing typed anchors")
    if "ride" in roles:
        names = {a.name for a in declared}
        for required in ("queue_entry", "boarding", "ride_exit", "service_access"):
            if required not in names: failures.append(f"ride missing {required} anchor")
    return {"ok": not failures, "failures": failures, "anchors": len(declared),
            "roles": sorted(roles), "blocks": int(model.solid().sum()),
            "mechanic_families": sorted(mechanics.get("families", {}))}
