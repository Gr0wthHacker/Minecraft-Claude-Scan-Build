"""Non-editing design critic: turns measurable evidence into prioritized fixes."""
from __future__ import annotations


def review(*, navigation: dict | None = None, visual: dict | None = None, efficiency: dict | None = None) -> list[dict]:
    findings = []
    if navigation and not navigation.get("ok", True):
        findings.append({"priority": 0, "area": "player-flow", "finding": navigation["failures"][0],
                         "action": "repair route/access before adding detail"})
    if visual and not visual.get("ok", True):
        findings.append({"priority": 1, "area": "visual", "finding": visual["failures"][0],
                         "action": "revise massing/material/light before render approval"})
    if efficiency and not efficiency.get("ok", True):
        findings.append({"priority": 2, "area": "efficiency", "finding": efficiency["failures"][0],
                         "action": "reduce hidden detail or split into cached chunks"})
    return sorted(findings, key=lambda item: item["priority"])
