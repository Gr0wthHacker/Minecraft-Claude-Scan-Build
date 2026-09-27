"""Implementation tickets generated directly from strict WorldSpec modules."""
from __future__ import annotations

from pathlib import Path


def write(plan: dict, directory: str | Path) -> list[str]:
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for module in plan.get("modules", []):
        name = module["name"]; safe = "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")
        lines = [f"# {name}", "", "## Contract", "",
                 f"- Generator: `{module.get('generator')}`", f"- Role: `{module.get('role')}`",
                 f"- Plot: `{module.get('plot')}`", f"- Placement: `{module.get('at')}`",
                 f"- Footprint: `{module.get('footprint')}`", f"- Dependencies: `{module.get('depends_on', [])}`",
                 f"- Budget: `{module.get('budget')}`", "", "## Interfaces", "",
                 f"- Public access: `{module.get('access_points', [])}`", f"- Typed anchors: `{module.get('anchors', [])}`",
                 "", "## Acceptance", "", f"- Scenarios: `{module.get('scenarios', [])}`",
                 f"- Required review views: `{module.get('review_views', [])}`", "- Strict server profile, world route, mechanics, collision, and visual gates must pass."]
        path = directory / f"{safe}.md"; path.write_text("\n".join(lines) + "\n", encoding="utf-8"); paths.append(str(path))
    return paths
