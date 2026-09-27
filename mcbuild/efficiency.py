"""Measurable efficiency budgets for high-quality Skyblock generation."""
from __future__ import annotations


def assess(model, seconds: float, spec=None) -> dict:
    spec = spec or {}; blocks = int(model.solid().sum())
    failures = []
    if "max_blocks" in spec and blocks > int(spec["max_blocks"]): failures.append("block budget exceeded")
    if "max_seconds" in spec and seconds > float(spec["max_seconds"]): failures.append("generation-time budget exceeded")
    if "min_materials" in spec and len(set(model.ids[model.ids > 0].tolist())) < int(spec["min_materials"]):
        failures.append("material-contrast budget missed")
    return {"ok": not failures, "failures": failures, "seconds": round(seconds, 6), "blocks": blocks,
            "blocks_per_second": round(blocks / max(seconds, 0.000001), 2)}
