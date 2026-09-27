"""Typed composition contracts for high-quality, efficient generated builds.

This is a coordination layer, not a replacement for generator craft.  It turns the information
agents otherwise leave in prose into stable metadata: anchors, compatible interfaces, style
genomes, deterministic variation, capability coverage, cache keys, and change impact.
"""
from __future__ import annotations

import hashlib
import html
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ANCHOR_KINDS = {
    "entry", "exit", "door", "path", "deck", "bridge_end", "queue", "board", "ride_exit",
    "support", "water_edge", "redstone_input", "redstone_output", "visual_front", "maintenance",
}
FACING = {"north", "south", "east", "west", "up", "down"}
COMPATIBLE = {
    "entry": {"path", "exit", "queue"}, "exit": {"path", "entry"}, "door": {"path", "queue"},
    "path": {"entry", "exit", "door", "deck", "bridge_end", "queue", "ride_exit"},
    "deck": {"bridge_end", "path"}, "bridge_end": {"deck", "path", "bridge_end"},
    "queue": {"entry", "door", "board", "path"}, "board": {"queue"}, "ride_exit": {"path"},
    "redstone_input": {"redstone_output"}, "redstone_output": {"redstone_input"},
}
GENOMES = {
    "frontier": {"facades": ["gable", "stepped", "bracketed"], "height_ratio": [0.35, 0.8],
                 "materials": ["warm_timber", "dusty_stone", "dark_hardware"], "light_density": "sparse-warm"},
    "hollow": {"facades": ["gable", "stepped"], "height_ratio": [0.6, 1.5],
               "materials": ["dark_stone", "oxidised_metal", "warm_lantern"], "light_density": "pools-of-light"},
    "midway": {"facades": ["flat", "stepped", "bracketed"], "height_ratio": [0.3, 1.2],
               "materials": ["painted_structure", "light_trim", "accent_colour"], "light_density": "bright-nodes"},
    "natural": {"facades": [], "height_ratio": [0.15, 0.9],
                "materials": ["strata", "soil", "vegetation", "water"], "light_density": "trail-nodes"},
    "prismworks": {"facades": ["stepped", "bracketed"], "height_ratio": [0.8, 2.4],
                   "materials": ["structural_stone", "black_recess", "signal_wool"],
                   "light_density": "signal-nodes"},
}


@dataclass(frozen=True)
class Anchor:
    name: str
    kind: str
    position: tuple[int, int, int]
    facing: str | None = None
    width: int = 1


def anchors(spec) -> list[Anchor]:
    """Parse local-space anchor declarations and reject ambiguous module interfaces."""
    if not spec:
        return []
    if not isinstance(spec, list):
        raise ValueError("anchors must be a list")
    out, names = [], set()
    for item in spec:
        if not isinstance(item, dict) or item.get("kind") not in ANCHOR_KINDS:
            raise ValueError("every anchor needs a known kind")
        name = item.get("name")
        position = item.get("position")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("anchors need unique non-empty names")
        if not isinstance(position, (tuple, list)) or len(position) != 3:
            raise ValueError(f"anchor {name}: position must be [x, y, z]")
        facing = item.get("facing")
        if facing is not None and facing not in FACING:
            raise ValueError(f"anchor {name}: unknown facing {facing!r}")
        width = int(item.get("width", 1))
        if width < 1:
            raise ValueError(f"anchor {name}: width must be positive")
        names.add(name)
        out.append(Anchor(name, item["kind"], tuple(map(int, position)), facing, width))
    return out


def compatible(left: Anchor, right: Anchor) -> bool:
    """True only for a declared interface pairing with matching usable width."""
    return right.kind in COMPATIBLE.get(left.kind, set()) and left.width == right.width


def check_links(source: list[Anchor], links, available: dict[str, Anchor]) -> list[dict]:
    """Validate named external links without guessing coordinates or ownership."""
    by_name = {a.name: a for a in source}
    failures = []
    for link in links or []:
        left_name, right_name = link.get("from"), link.get("to")
        left, right = by_name.get(left_name), available.get(right_name)
        if left is None or right is None:
            failures.append({"link": link, "reason": "unknown anchor"})
        elif not compatible(left, right):
            failures.append({"link": link, "reason": "incompatible kind or width"})
    return failures


def genome(name: str) -> dict:
    if name not in GENOMES:
        raise ValueError(f"unknown design genome {name!r}; have {', '.join(sorted(GENOMES))}")
    return {"name": name, **GENOMES[name]}


def variation(seed: object, family: str, options: list[str]) -> str:
    """Stable controlled variation: same seed/family always selects the same legal option."""
    if not options:
        raise ValueError("variation family has no options")
    digest = hashlib.sha256(f"{seed}|{family}".encode()).digest()
    return options[int.from_bytes(digest[:4], "big") % len(options)]


def fingerprint(config: dict, *, generator_source: str = "") -> str:
    """Cache key for reproducible artifacts, independent of YAML formatting or dict order."""
    payload = {"config": config, "generator_source": generator_source}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_digest(path: str | Path | None) -> str:
    """Content hash for a generator implementation; missing source is explicit, never cached as it."""
    if not path:
        return ""
    source = Path(path)
    return hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else ""


def world_anchors(modules: list[dict]) -> dict[str, Anchor]:
    """Index module-local anchors in world coordinates under unambiguous ``module.anchor`` names."""
    out = {}
    for module in modules:
        module_name = module.get("name")
        at = module.get("at", (0, 0, 0))
        if not module_name or not isinstance(at, (tuple, list)) or len(at) != 3:
            raise ValueError("every composed module needs name and world at [x, y, z]")
        for anchor in anchors(module.get("anchors")):
            key = f"{module_name}.{anchor.name}"
            if key in out:
                raise ValueError(f"duplicate world anchor {key}")
            out[key] = Anchor(anchor.name, anchor.kind,
                              tuple(int(a) + int(b) for a, b in zip(at, anchor.position)),
                              anchor.facing, anchor.width)
    return out


def check_world_links(modules: list[dict], links) -> list[dict]:
    """Check composition links: typed endpoints must meet or be cardinally adjacent."""
    index = world_anchors(modules)
    failures = []
    for link in links or []:
        left, right = index.get(link.get("from")), index.get(link.get("to"))
        if left is None or right is None:
            failures.append({"link": link, "reason": "unknown world anchor"}); continue
        distance = sum(abs(a - b) for a, b in zip(left.position, right.position))
        if not compatible(left, right):
            failures.append({"link": link, "reason": "incompatible kind or width"})
        elif distance > 1:
            failures.append({"link": link, "reason": f"endpoints are {distance} blocks apart"})
    return failures


def impact(previous: dict, current: dict) -> dict:
    """Report only modules whose stable input/cache key changed."""
    old = previous.get("modules", {})
    new = current.get("modules", {})
    added = sorted(set(new) - set(old)); removed = sorted(set(old) - set(new))
    changed = sorted(name for name in set(old) & set(new) if old[name] != new[name])
    return {"added": added, "removed": removed, "changed": changed,
            "unaffected": sorted(set(old) & set(new) - set(changed))}


def capability_matrix(*, mechanics: dict, design: dict, anchors_: list[Anchor], scenario=None) -> dict:
    """An honest maturity matrix: absent metadata remains visibly absent rather than implied."""
    brief = design.get("brief", {}) if design else {}
    journey = design.get("journey", {}) if design else {}
    families = mechanics.get("families", {}) if mechanics else {}
    return {
        "purpose": bool(brief.get("purpose")), "style": bool(brief.get("style")),
        "palette_roles": bool(brief.get("palette_roles")), "visual_review": bool(brief.get("visual_review")),
        "journey": bool(journey.get("declared")) and bool(journey.get("ok")),
        "anchors": bool(anchors_), "mechanics": sorted(families),
        "redstone_declared": "redstone" in families,
        "scenario": bool(scenario and scenario.get("ok")),
    }


def write_dashboard(path: str | Path, title: str, modules: list[dict]) -> str:
    """Write a dependency-free review dashboard for agents and human reviewers."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for module in modules:
        caps = module.get("capabilities", {})
        missing = [k for k, v in caps.items() if v is False or v == []]
        rows.append(f"<tr><td>{html.escape(str(module.get('name','?')))}</td><td>{html.escape(str(module.get('lane','-')))}</td>"
                    f"<td>{html.escape(str(module.get('fingerprint',''))[:12])}</td><td>{html.escape(', '.join(missing) or 'covered')}</td></tr>")
    page = (f"<!doctype html><title>{html.escape(title)}</title><h1>{html.escape(title)}</h1>"
            "<p>Generated review evidence; absent capabilities require an explicit decision.</p>"
            "<table border=1><tr><th>module</th><th>lane</th><th>fingerprint</th><th>missing/review</th></tr>"
            + "".join(rows) + "</table>")
    path.write_text(page, encoding="utf-8")
    return str(path)
