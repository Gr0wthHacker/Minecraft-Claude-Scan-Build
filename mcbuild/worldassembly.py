"""Assemble generated artifacts into a block-accurate world for final Skyblock checks."""
from __future__ import annotations

from . import scan, walk


def load_artifacts(paths) -> dict:
    """Return placed world cells and hard conflicts. Same-position cells are never silently merged."""
    cells, owners, conflicts = {}, {}, []
    for path in paths:
        item = scan.load(str(path)); ox, oy, oz = item.origin
        names = item.model.names
        for y, z, x in zip(*item.model.solid().nonzero()):
            pos = (int(x) + ox, int(y) + oy, int(z) + oz)
            state, prior = names[int(item.model.ids[y, z, x])], owners.get(pos)
            if prior is not None:
                conflicts.append({"position": list(pos), "first": prior, "second": item.litematic_path})
            else:
                cells[pos] = state; owners[pos] = item.litematic_path
    return {"cells": cells, "conflicts": conflicts, "artifacts": len(paths)}


def validate(paths, *, entry, destinations=()) -> dict:
    """Run the repository's real block/headroom/stair walk model across assembled artifacts."""
    assembled = load_artifacts(paths)
    start = tuple(entry)
    reached = walk.reachable(assembled["cells"], start)
    stops = []
    for destination in destinations:
        point = tuple(destination)
        stops.append({"point": list(point), "standable": walk.stands(assembled["cells"], point),
                      "reachable": point in reached})
    failures = []
    if assembled["conflicts"]: failures.append(f"{len(assembled['conflicts'])} cross-artifact block conflicts")
    if not reached: failures.append("entry is not a standable cell in assembled world")
    failures.extend(f"unreachable destination {item['point']}" for item in stops if not item["reachable"])
    return {"ok": not failures, "failures": failures, "artifacts": assembled["artifacts"],
            "conflicts": assembled["conflicts"], "reachable_cells": len(reached), "destinations": stops}
