"""Visitor-journey contracts for a generated schematic.

Coordinates in a brief are local ``[x, y, z]`` positions in the finished schematic.  This keeps a
contract stable when a plan is re-sited; the pipeline applies the world origin only for reporting.
"""
from __future__ import annotations

from . import walk


def evaluate(model, spec, origin=(0, 0, 0)) -> dict:
    if not spec:
        return {"declared": False, "ok": True, "destinations": []}
    entry = spec.get("entry")
    destinations = spec.get("destinations", [])
    if not (isinstance(entry, (list, tuple)) and len(entry) == 3):
        raise ValueError("design.journey.entry must be a local [x, y, z]")
    if not isinstance(destinations, list) or not destinations:
        raise ValueError("design.journey.destinations must be a non-empty list of local [x, y, z]")
    ox, oy, oz = origin or (0, 0, 0)
    names = [n.split(":")[-1] for n in model.names]
    world = {}
    for y, z, x in zip(*model.solid().nonzero()):
        world[(int(x) + ox, int(y) + oy, int(z) + oz)] = names[model.ids[y, z, x]]
    start = tuple(int(v) + d for v, d in zip(entry, (ox, oy, oz)))
    reached = walk.reachable(world, start, limit=int(spec.get("limit", 250000))) if walk.stands(world, start) else set()
    results = []
    for target in destinations:
        if not isinstance(target, (list, tuple)) or len(target) != 3:
            raise ValueError("every design.journey destination must be a local [x, y, z]")
        point = tuple(int(v) + d for v, d in zip(target, (ox, oy, oz)))
        results.append({"local": list(target), "world": list(point), "reachable": point in reached})
    return {"declared": True, "entry_local": list(entry), "entry_world": list(start),
            "entry_standable": walk.stands(world, start), "reachable_cells": len(reached),
            "destinations": results, "ok": bool(reached) and all(r["reachable"] for r in results)}
