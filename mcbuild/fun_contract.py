"""Semantic player-value contract for public generator configs."""
from __future__ import annotations

CLASSES = {"experience", "recovery", "orientation", "route", "scenic_support"}


def assess(spec) -> dict:
    if not spec:
        return {"declared": False, "ok": True, "failures": []}
    if not isinstance(spec, dict):
        raise ValueError("fun_contract must be a mapping")
    failures = []
    kind = spec.get("class")
    if kind not in CLASSES:
        failures.append("class must be experience, recovery, orientation, route, or scenic_support")
    verbs = spec.get("player_verbs", [])
    if not isinstance(verbs, list) or not verbs or not all(isinstance(v, str) and v for v in verbs):
        failures.append("player_verbs must be a non-empty list of text")
    if not isinstance(spec.get("outcome"), str) or not spec["outcome"].strip():
        failures.append("missing visible outcome")
    if kind == "experience":
        for field in ("reset", "service_access", "bypass"):
            if not isinstance(spec.get(field), str) or not spec[field].strip():
                failures.append(f"experience missing {field}")
    else:
        if not isinstance(spec.get("spatial_job"), str) or not spec["spatial_job"].strip():
            failures.append("non-experience missing spatial_job")
    return {"declared": True, "class": kind, "player_verbs": verbs,
            "outcome": spec.get("outcome"), "ok": not failures, "failures": failures}
