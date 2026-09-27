"""Strict production schema for versioned Skyblock WorldSpecs."""
from __future__ import annotations


REQUIRED_SITE = {"anchor", "bounds", "build_plane", "entry_points", "protected"}
REQUIRED_MODULE = {"name", "plot", "generator", "role", "footprint", "at", "access_points", "anchors",
                   "depends_on", "budget", "scenarios", "review_views"}
REQUIRED_VIEWS = {"arrival", "facade", "skyline", "interior", "night"}


def validate(spec: dict) -> list[str]:
    """Return all missing production-contract fields without inventing design choices."""
    errors = []
    if int(spec.get("format", 0)) != 1: errors.append("format must be 1")
    site = spec.get("site", {})
    errors.extend(f"site missing {field}" for field in sorted(REQUIRED_SITE - set(site)))
    if not spec.get("server_profile"): errors.append("missing server_profile")
    if not spec.get("style_packs"): errors.append("missing style_packs")
    for module in spec.get("modules", []):
        missing = REQUIRED_MODULE - set(module)
        errors.extend(f"{module.get('name', '?')}: missing {field}" for field in sorted(missing))
        if not missing and not REQUIRED_VIEWS <= set(module["review_views"]):
            errors.append(f"{module['name']}: review_views must include {', '.join(sorted(REQUIRED_VIEWS))}")
    return errors
