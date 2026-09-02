"""One deterministic preparation command for strict Skyblock world builds."""
from __future__ import annotations

from pathlib import Path

from . import composition, tickets, worldexport, worldnav, worldrender, worldschema, worldspec
from .greybox import build as greybox_build
from . import schem

#: A greybox is a MASSING STUDY, and AGENTS.md gates detail behind one: "Generate a greybox
#: before expensive detail. Do not detail a rejected layout." Only modules that declared a full
#: blueprint were ever getting one, which on this plan was none of them - so the gate existed
#: and never fired. A module's role and its lot are enough to mass it, so the brief is derived.
#:
#: A path, a plaza and a set piece are deliberately absent: a plaza's massing IS its paving and
#: a sculpture's IS the sculpture, so a box around either would be a preview of nothing.
GREYBOX_PROGRAM = {"ride": "ride_station", "arrival": "hotel_lobby", "building": "shop",
                   "landmark": "gallery", "service": "workshop"}
#: A WorldSpec style pack names a LAND; `blueprint.STYLES` names an architectural genome. The
#: two vocabularies are not the same list, so a land the blueprint compiler has never heard of
#: maps to the genome that describes it - Prismworks is the visual spec's own "high-detail
#: vertical machine landmark", which is `industrial`.
GREYBOX_STYLE = {"prismworks": "industrial", "prism": "industrial"}


def greybox_brief(module: dict) -> dict | None:
    """Derive a massing brief from a module's declared role and lot, or None if it is not a building."""
    if module.get("blueprint"):
        return {"name": module["name"], **module["blueprint"]}
    program = GREYBOX_PROGRAM.get(module.get("role"))
    footprint = module.get("footprint")
    if not program or not footprint:
        return None
    width, depth = int(footprint[0]), int(footprint[1])
    # the lot is ownership; the massing is the part of it a building actually occupies
    style = module.get("style", "civic")
    return {"name": module["name"], "program": program, "style": GREYBOX_STYLE.get(style, style),
            "width": max(7, min(width, 24)), "depth": max(28, min(depth, 40)),
            "floors": 2 if module.get("role") in {"ride", "landmark", "arrival"} else 1}


def prepare(raw: dict, directory: str | Path) -> dict:
    """Compile, gate, greybox, emit strict jobs, render infrastructure, and write tickets."""
    errors = worldschema.validate(raw)
    if errors: raise ValueError("strict WorldSpec invalid: " + "; ".join(errors))
    plan = worldspec.compile(raw); directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    nav, visual = worldnav.audit(plan), composition.assess(plan)
    if not nav["ok"] or not visual["ok"]: raise ValueError("world layout gate failed: " + "; ".join(nav["failures"] + visual["failures"]))
    infrastructure = worldexport.export_chunks(worldrender.infrastructure(plan), directory / "infrastructure", prefix=plan["name"])
    configs = worldspec.emit_configs(plan, directory / "configs")
    greyboxes = []
    for module in plan["modules"]:
        brief = greybox_brief(module)
        if brief:
            model, _brief = greybox_build(brief)
            path = directory / "greyboxes" / (module["name"].replace(" ", "_") + ".litematic")
            path.parent.mkdir(parents=True, exist_ok=True); schem.save(str(path), model, name=module["name"] + " Greybox"); greyboxes.append(str(path))
    return {"plan": plan, "infrastructure": infrastructure, "configs": configs, "greyboxes": greyboxes,
            "tickets": tickets.write(raw, directory / "tickets"), "navigation": nav, "composition": visual}
