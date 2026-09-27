"""Safe incremental bridge from legacy generator configs to shared building blueprints."""
from __future__ import annotations

from . import blueprint


def apply(config: dict) -> tuple[dict, dict | None]:
    """Compile optional ``blueprint`` config and fill only absent composition metadata.

    It never mutates generator parameters or guesses geometry, so legacy generators can adopt the
    shared contract now and render blueprint-controlled shells in later, scoped migrations.
    """
    brief = config.get("blueprint")
    if not brief: return config, None
    if not isinstance(brief, dict): raise ValueError("blueprint must be an inline object")
    plan = blueprint.compile({"name": config.get("name", brief.get("name", "building")), **brief})
    merged = dict(config)
    merged.setdefault("anchors", plan["anchors"])
    merged.setdefault("design", {})
    merged["design"] = {**merged["design"], "purpose": merged["design"].get("purpose", plan["program"]),
                        "style": merged["design"].get("style", plan["style"])}
    return merged, plan
