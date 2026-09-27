"""Small, honest cross-cutting visitor scenarios over generated evidence."""
from __future__ import annotations


SCENARIOS = {"public_visit", "night_visit", "rail_ride", "redstone_interaction"}


def evaluate(spec, design: dict, mechanics: dict) -> dict:
    """Evaluate declared scenarios without claiming entity simulation we do not perform."""
    if not spec:
        return {"declared": [], "checks": [], "ok": True}
    names = spec if isinstance(spec, list) else spec.get("requires", [])
    if not isinstance(names, list) or any(name not in SCENARIOS for name in names):
        raise ValueError(f"scenarios must be from {', '.join(sorted(SCENARIOS))}")
    journey = design.get("journey", {})
    metrics = design.get("metrics", {})
    families = mechanics.get("families", {})
    checks = []
    for name in names:
        if name == "public_visit":
            ok = bool(journey.get("declared")) and bool(journey.get("ok"))
            detail = "declared journey reaches each destination"
        elif name == "night_visit":
            ok = metrics.get("light_blocks", 0) > 0
            detail = "design contains light sources; propagation remains nightlight's contract"
        elif name == "rail_ride":
            ok = "rail" in families and bool(journey.get("declared"))
            detail = "rail system and visitor access declared; motion remains ride-specific"
        else:
            ok = "redstone" in families
            detail = "redstone system declared; circuit behavior remains circuit-specific"
        checks.append({"scenario": name, "ok": ok, "detail": detail})
    return {"declared": names, "checks": checks, "ok": all(check["ok"] for check in checks)}
