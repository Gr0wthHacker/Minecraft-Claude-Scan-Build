"""District-level composition checks for sophisticated multi-generator builds."""
from __future__ import annotations

from .design_compiler import check_world_links, world_anchors


ROLE_REQUIREMENTS = {
    "arrival": {"public_entry", "public_exit", "visual_front"},
    "landmark": {"public_entry", "visual_front"},
    "building": {"public_entry", "public_exit", "service_access", "visual_front"},
    "ride": {"public_entry", "queue_entry", "boarding", "ride_exit", "service_access"},
    "food": {"public_entry", "public_exit", "service_access", "visual_front"},
    "path": set(),
}


def audit(modules: list[dict], links: list[dict], *, required_routes=None) -> dict:
    """Audit a district contract before generators create blocks.

    Modules are normal composition entries plus a ``role``.  This catches the common expensive
    failure mode: an attractive but inaccessible module is generated and detailed before anyone
    notices it lacks an entrance, exit, or service path.
    """
    failures, all_names = [], set()
    for module in modules:
        name, role = module.get("name"), module.get("role")
        if not name or role not in ROLE_REQUIREMENTS:
            failures.append({"module": name or "?", "reason": "unknown or absent district role"}); continue
        declared = {anchor.get("name") for anchor in module.get("anchors", []) if isinstance(anchor, dict)}
        for required in sorted(ROLE_REQUIREMENTS[role] - declared):
            failures.append({"module": name, "reason": f"missing {required}"})
        if name in all_names: failures.append({"module": name, "reason": "duplicate module name"})
        all_names.add(name)
    try:
        failures.extend({"module": "link", **failure} for failure in check_world_links(modules, links))
        index = world_anchors(modules)
    except ValueError as exc:
        failures.append({"module": "anchors", "reason": str(exc)}); index = {}
    for route in required_routes or []:
        if route.get("from") not in index or route.get("to") not in index:
            failures.append({"module": "route", "reason": f"unknown route endpoint {route}"})
    return {"ok": not failures, "failures": failures, "module_count": len(modules),
            "link_count": len(links), "anchor_count": len(index), "routes": list(required_routes or [])}
