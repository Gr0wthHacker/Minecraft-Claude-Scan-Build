"""Public-purpose and access contracts for the three theme-park zones.

The planner already knows where its streets meet a module.  This module names that relationship so
the result is reviewable, testable, and available to downstream generators/agents rather than
remaining an implementation detail of the path pass.
"""
from __future__ import annotations


def _purpose(module: dict) -> tuple[str, str, bool]:
    gen, kind = module["gen"], module["kind"]
    if kind == "paths": return "path", "supporting", False
    if kind == "plaza": return "terrain", "supporting", False
    if gen == "wayfinding": return "service", "supporting", False
    if gen == "streetfurniture": return "service", "filler", False
    if kind in {"gate", "arch", "boxoffice", "queue", "turnstile", "court"}: return "arrival", "landmark", True
    if gen in {"coaster", "bigwheel", "attractions"}: return "ride", "landmark", True
    if gen == "arcade": return "ride", "supporting", True
    if kind in {"foodcourt", "saloon", "shopstreet", "sluice", "minehead"}: return "shop", "supporting", True
    if gen in {"monument", "spectacle"}: return "landmark", "landmark", True
    return "building", "supporting", True


def annotate(modules: list[dict], front_of, inside_of) -> None:
    """Annotate every planned module in-place with a purpose and access candidates.

    Edge thresholds face outward, while an edge ride may face inward. Both the outside-facing front
    and park-side candidate are retained so the route validator can choose the owned, paved one
    without guessing which type of edge asset it is.
    """
    for module in modules:
        purpose, hierarchy, needs_access = _purpose(module)
        contract = {"purpose": purpose, "hierarchy": hierarchy,
                    "land": module.get("params", {}).get("land"), "requires_path": needs_access}
        if needs_access:
            front = front_of(module)
            candidates = [front]
            if module.get("edge"):
                inside = inside_of(module)
                if inside not in candidates:
                    candidates.append(inside)
            contract["access_candidates"] = [[x, module["at"][1] + 1, z] for x, z in candidates]
        module["park_contract"] = contract


def missing(modules: list[dict]) -> list[str]:
    """Names of modules that lack a complete public-purpose contract."""
    out = []
    for module in modules:
        contract = module.get("park_contract", {})
        if not contract.get("purpose") or not contract.get("hierarchy"):
            out.append(module.get("name", "?")); continue
        if contract.get("requires_path") and not contract.get("access_candidates"):
            out.append(module.get("name", "?"))
    return out


def inaccessible(modules: list[dict], paving: set[tuple[int, int]]) -> list[str]:
    """Public modules must have at least one declared approach on the generated paving network."""
    out = []
    for module in modules:
        contract = module.get("park_contract", {})
        if not contract.get("requires_path"):
            continue
        candidates = contract.get("access_candidates", [])
        if not any((int(point[0]), int(point[2])) in paving for point in candidates):
            out.append(module.get("name", "?"))
    return out
