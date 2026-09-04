"""Hard release evidence for animal and creature setpieces.

A sculpture can be abstract; an animal cannot. This records the minimum evidence
that an animal is one intentional, materially readable object with named anatomy.
It does not pretend automatic metrics can decide whether a face is beautiful:
a visual packet is still required for enforced contracts.
"""
from __future__ import annotations

from . import mechanics, morph

ANIMAL_GENERATORS = {
    "axolotl", "bat", "dragonfly", "fox", "frog", "gecko", "heron",
    "ladybug", "quadruped", "sloth", "turtle",
}


def assess(model, *, generator: str | None, meta: dict | None = None, spec=None) -> dict:
    declared = generator in ANIMAL_GENERATORS or bool(spec)
    if not declared:
        return {"declared": False, "ok": True, "failures": []}
    spec = spec or {}
    if not isinstance(spec, dict):
        raise ValueError("animal_contract must be a mapping")
    solid = model.solid()
    _labels, components = morph.components(solid, conn=6)
    features = (meta or {}).get("features_built", {})
    failures = []
    minimum = int(spec.get("min_blocks", 500))
    if int(solid.sum()) < minimum:
        failures.append(f"animal has {int(solid.sum())} blocks; needs {minimum}")
    if len(components) != 1:
        failures.append(f"animal has {len(components)} disconnected components")
    material_count = len({int(v) for v in model.ids[solid]})
    if material_count < int(spec.get("min_materials", 4)):
        failures.append(f"animal uses {material_count} materials; needs {spec.get('min_materials', 4)}")
    required = spec.get("required_features", [])
    if not isinstance(required, list) or not all(isinstance(v, str) and v for v in required):
        failures.append("required_features must be a list of feature names")
    else:
        absent = [name for name in required if not features.get(name)]
        if absent:
            failures.append("missing declared anatomy: " + ", ".join(absent))
    profile = (meta or {}).get("profile_view")
    if not isinstance(profile, str) or not profile:
        failures.append("animal lacks a declared best review view")
    if spec.get("enforce") and not spec.get("_visual_review"):
        failures.append("enforced animal needs design.visual_review for multi-angle evidence")
    used = mechanics.manifest(model, generator=generator).get("families", {})
    disallowed = sorted(set(used) - {"light"})
    if disallowed:
        failures.append("animal uses functional families: " + ", ".join(disallowed))
    return {
        "declared": True, "ok": not failures, "failures": failures,
        "blocks": int(solid.sum()), "components": sorted(components, reverse=True),
        "materials": material_count, "features": features, "profile_view": profile,
    }
