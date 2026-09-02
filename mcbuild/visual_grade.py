"""Objective visual review metrics for rendered/assembled Minecraft structures."""
from __future__ import annotations

from . import design


def assess(model, *, required_lights: int = 1, min_height: int = 3) -> dict:
    """Flag simple visual failures before human render review: flatness, darkness, and emptiness."""
    evidence = design.assess(model, {"quality": {"min_height": min_height, "min_lights": required_lights}})
    metrics = evidence["metrics"]
    failures = [f"{check['rule']} below target" for check in evidence["checks"] if not check["ok"]]
    if metrics["massing"]["fill_ratio"] < 0.08: failures.append("visually sparse massing")
    if metrics["materials"] < 2: failures.append("insufficient material contrast")
    return {"ok": not failures, "failures": failures, "metrics": metrics,
            "required_human_views": ["arrival", "facade", "skyline", "interior", "night"]}
