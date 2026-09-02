"""Deterministic dependency graph for safely parallel world generation."""
from __future__ import annotations


def schedule(tasks: list[dict]) -> dict:
    """Topologically order owned tasks; cycles and conflicting chunk owners are hard failures."""
    by_name = {task.get("name"): task for task in tasks}
    if len(by_name) != len(tasks) or None in by_name: raise ValueError("tasks need unique names")
    owners, failures = {}, []
    for task in tasks:
        for chunk in task.get("chunks", []):
            key = tuple(chunk)
            if key in owners and owners[key] != task["name"]:
                failures.append(f"chunk {key} owned by both {owners[key]} and {task['name']}")
            owners[key] = task["name"]
    pending = {name: set(task.get("depends_on", [])) for name, task in by_name.items()}
    unknown = sorted({dep for deps in pending.values() for dep in deps if dep not in by_name})
    if unknown: failures.append("unknown dependencies: " + ", ".join(unknown))
    levels = []
    while pending and not failures:
        ready = sorted(name for name, deps in pending.items() if not deps)
        if not ready:
            failures.append("dependency cycle: " + ", ".join(sorted(pending))); break
        levels.append(ready)
        for name in ready: pending.pop(name)
        for deps in pending.values(): deps.difference_update(ready)
    return {"ok": not failures, "failures": failures, "levels": levels,
            "task_count": len(tasks), "owned_chunks": len(owners)}
