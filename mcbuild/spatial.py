"""Explainable placement/orientation intelligence for world modules."""
from __future__ import annotations

FACES = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def choose(module: dict, candidates: list[dict], *, route_cells=(), protected=(), view_cells=()) -> dict:
    """Rank placements, rejecting bad access/overlap/void choices before block generation."""
    routes, views = set(map(tuple, route_cells)), set(map(tuple, view_cells))
    protected = [tuple(box) for box in protected]
    ranked = []
    for candidate in candidates:
        x, z = candidate["at"]; w, d = module["footprint"]; face = candidate.get("facing", "north")
        dx, dz = FACES[face]; entrance = (x + w // 2 + dx * (w // 2 + 1), z + d // 2 + dz * (d // 2 + 1))
        occupied = {(xx, zz) for xx in range(x, x + w) for zz in range(z, z + d)}
        hard, notes, score = [], [], 0
        if any(box[0] <= xx <= box[2] and box[1] <= zz <= box[3] for xx, zz in occupied for box in protected): hard.append("occupies protected area")
        if occupied & views: hard.append("blocks protected view corridor")
        if entrance not in routes and not any((entrance[0] + ax, entrance[1] + az) in routes for ax, az in FACES.values()):
            hard.append("entrance does not meet public route")
        else: score += 50; notes.append("entrance meets public route")
        service = candidate.get("service")
        if module.get("requires_service") and (not service or tuple(service) in routes): hard.append("service access missing or public")
        elif module.get("requires_service"): score += 15; notes.append("service access separated")
        for near in module.get("near", []):
            target = tuple(near)
            distance = abs(x - target[0]) + abs(z - target[1]); score += max(0, 20 - distance); notes.append(f"adjacency distance {distance}")
        score -= int(candidate.get("foundation_cost", 0)); score -= int(candidate.get("void_risk", 0)) * 10
        ranked.append({"at": [x, z], "facing": face, "entrance": list(entrance), "score": score,
                       "hard_failures": hard, "notes": notes,
                       "repair": _repair(hard, routes, entrance)})
    valid = sorted((item for item in ranked if not item["hard_failures"]), key=lambda item: -item["score"])
    return {"ok": bool(valid), "best": valid[0] if valid else None, "candidates": ranked,
            "repairs": [item["repair"] for item in ranked if item["repair"]]}


def _repair(failures, routes, entrance):
    if "entrance does not meet public route" in failures and routes:
        nearest = min(routes, key=lambda p: abs(p[0] - entrance[0]) + abs(p[1] - entrance[1]))
        return f"rotate or move entrance toward public route at {nearest}"
    if "blocks protected view corridor" in failures: return "move footprint outside protected view corridor"
    if "occupies protected area" in failures: return "move footprint outside protected island infrastructure"
    if "service access missing or public" in failures: return "add a backstage service edge away from public paving"
    return None
