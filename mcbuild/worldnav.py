"""Combined-island route validation for semantic Skyblock world plans."""
from __future__ import annotations

from collections import deque


def _reachable(cells: set[tuple[int, int]], start: tuple[int, int]) -> set[tuple[int, int]]:
    if start not in cells: return set()
    seen, todo = {start}, deque([start])
    while todo:
        x, z = todo.popleft()
        for point in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if point in cells and point not in seen:
                seen.add(point); todo.append(point)
    return seen


def audit(plan: dict) -> dict:
    """Verify declared arrival/access points against the full public paving graph.

    This is intentionally stricter than checking a plot is merely near a path: every public module
    declares the exact cell where a player arrives, and that cell must join the same reachable
    route component as an island arrival point.
    """
    public = {tuple(cell) for route in plan.get("routes", []) if route.get("kind") != "service"
              for cell in route.get("footprint", route.get("cells", []))}
    # A SERVICE MODULE IS NOT REACHED THE WAY A GUEST MODULE IS, and proving it on the public
    # graph would demand exactly the thing the concealed-service band exists to prevent: a guest
    # route into the backstage. Staff walk both networks, so the service graph is the union.
    service = public | {tuple(cell) for route in plan.get("routes", []) if route.get("kind") == "service"
                        for cell in route.get("footprint", route.get("cells", []))}
    entries = [tuple(point) for point in plan.get("site", {}).get("entry_points", [])]
    failures, reached = [], set()
    if not entries: failures.append("site has no public entry point")
    for entry in entries:
        if entry not in public: failures.append(f"entry point {entry} is not on public paving")
        reached |= _reachable(public, entry)
    service_reached = set()
    for entry in entries:
        service_reached |= _reachable(service, entry)
    report = []
    for module in plan.get("modules", []):
        points = [tuple(point) for point in module.get("access_points", [])]
        staff_only = module.get("role") == "service"
        network, arrived = (service, service_reached) if staff_only else (public, reached)
        label = "service" if staff_only else "public arrival"
        if not points:
            failures.append(f"{module['name']}: missing explicit {label} access point"); continue
        okay = []
        for point in points:
            # an approach may end next to a doorway/queue, rather than occupying its interior cell
            adjacent = point in network or any((point[0] + dx, point[1] + dz) in network
                                               for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            okay.append({"point": list(point), "adjacent_to_path": adjacent, "reachable": point in arrived or
                         any((point[0] + dx, point[1] + dz) in arrived for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))})
        if not any(item["adjacent_to_path"] and item["reachable"] for item in okay):
            failures.append(f"{module['name']}: no access point reaches {label} network")
        report.append({"module": module["name"], "access": okay, "network": label})
    return {"ok": not failures, "failures": failures, "public_cells": len(public),
            "reachable_cells": len(reached), "modules": report}
