"""Shared design briefs and measurable visual-quality evidence.

This module does not claim taste can be reduced to a number.  It records the measurable evidence
that lets an agent and a reviewer discuss the same build: massing, silhouette occupancy, material
hierarchy, light, and the stated purpose/journey.  A config may opt into ``design.enforce`` to
turn its own declared thresholds into a generation gate.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

from . import blocks

PURPOSES = {"landmark", "arrival", "path", "bridge", "ride", "shop", "service", "sculpture", "terrain", "building"}
HIERARCHIES = {"landmark", "supporting", "filler"}
LIGHT_KINDS = {"lantern", "torch", "light", "glowstone", "sea_lantern", "froglight", "redstone_lamp"}
STYLE_PROFILES = {
    "frontier": {"massing": "false fronts, deep porches, tall signs", "palette": "warm timber, dusty stone, dark hardware"},
    "hollow": {"massing": "vertical gothic silhouettes, recesses, broken rhythm", "palette": "dark stone, oxidised metal, restrained warm light"},
    "midway": {"massing": "open facades, bright landmarks, generous plazas", "palette": "painted structure, light trim, concentrated colour"},
    "natural": {"massing": "asymmetric terrain-led forms and planted edges", "palette": "stone strata, soil, vegetation, water"},
    # PARK_VISUAL_AND_BUDGET_SPEC's own words for the land that replaced the Hollow: a
    # "high-detail vertical machine landmark and night identity". It is not the Hollow renamed -
    # its silhouette is structural rather than gothic, and its light is a signal, not a mood.
    "prismworks": {"massing": "structural masts, external ribs, exposed machine core, one open crown",
                   "palette": "stone and cobblestone foundation, black recesses, cyan/blue signal wool"},
}


def style_profile(name: str) -> dict:
    if name not in STYLE_PROFILES:
        raise ValueError(f"unknown style profile {name!r}; have {', '.join(sorted(STYLE_PROFILES))}")
    return dict(STYLE_PROFILES[name])


def _short(name: str) -> str:
    return name.split(":")[-1].split("[")[0]


def validate_brief(brief) -> dict:
    """Validate and normalise a declarative build brief without inventing missing intent."""
    if not brief:
        return {}
    if not isinstance(brief, dict):
        raise ValueError("design brief must be a mapping")
    out = dict(brief)
    for field, allowed in (("purpose", PURPOSES), ("hierarchy", HIERARCHIES)):
        if field in out and out[field] not in allowed:
            raise ValueError(f"design.{field} must be one of {', '.join(sorted(allowed))}")
    for field in ("narrative", "style", "focal_face"):
        if field in out and not isinstance(out[field], str):
            raise ValueError(f"design.{field} must be text")
    if "style" in out:
        style_profile(out["style"])
    for field in ("palette_roles", "journey", "composition", "quality"):
        if field in out and not isinstance(out[field], dict):
            raise ValueError(f"design.{field} must be a mapping")
    return out


def _silhouette(solid: np.ndarray, axis: int) -> tuple[int, float]:
    """Area and occupancy of an orthographic silhouette along a model axis."""
    projection = solid.any(axis=axis)
    area = int(projection.sum())
    return area, area / max(1, projection.size)


def _perimeter(cells: np.ndarray) -> int:
    """Count exposed 2-D cell edges: a stable silhouette-articulation signal."""
    padded = np.pad(cells, 1, constant_values=False)
    return int(((padded[1:-1, 1:-1] != padded[:-2, 1:-1]).sum()
                + (padded[1:-1, 1:-1] != padded[2:, 1:-1]).sum()
                + (padded[1:-1, 1:-1] != padded[1:-1, :-2]).sum()
                + (padded[1:-1, 1:-1] != padded[1:-1, 2:]).sum()))


def _surface_faces(solid: np.ndarray) -> int:
    """Count air-facing block faces without assigning an aesthetic judgement."""
    padded = np.pad(solid, 1, constant_values=False)
    core = padded[1:-1, 1:-1, 1:-1]
    return int(sum((core & ~neighbor).sum() for neighbor in (
        padded[:-2, 1:-1, 1:-1], padded[2:, 1:-1, 1:-1],
        padded[1:-1, :-2, 1:-1], padded[1:-1, 2:, 1:-1],
        padded[1:-1, 1:-1, :-2], padded[1:-1, 1:-1, 2:],
    )))


def metrics(model) -> dict:
    """Return stable, renderer-independent quality evidence for one finished model."""
    solid = model.solid()
    blocks_count = int(solid.sum())
    if not blocks_count:
        return {"blocks": 0, "materials": 0, "silhouette": {}, "massing": {}, "light_blocks": 0}
    ys, zs, xs = np.where(solid)
    dx, dy, dz = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1), int(zs.max() - zs.min() + 1)
    names = [_short(n) for n in model.names]
    bom = Counter(names[i] for i in model.ids[solid].tolist())
    front_area, front_fill = _silhouette(solid, axis=1)  # y,z? front-like x/y projection is below
    xz_area, xz_fill = _silhouette(solid, axis=0)
    xy_area, xy_fill = _silhouette(solid, axis=1)
    yz_area, yz_fill = _silhouette(solid, axis=2)
    lights = sum(count for name, count in bom.items() if _kind(name) in LIGHT_KINDS or name == "redstone_lamp")
    # References consistently use a legible base, main body, and crown rather
    # than distributing equal mass at every elevation.  This records that
    # evidence; a brief/human reviewer decides whether its shape is appropriate.
    vertical = np.array_split(solid, 3, axis=0)
    elevation = [round(int(band.sum()) / blocks_count, 4) for band in vertical]
    top = solid.any(axis=0)
    return {
        "blocks": blocks_count,
        "materials": len(bom),
        "dominant_material_share": round(max(bom.values()) / blocks_count, 4),
        "light_blocks": lights,
        "massing": {"width": dx, "height": dy, "depth": dz,
                    "fill_ratio": round(blocks_count / (dx * dy * dz), 4)},
        "silhouette": {
            "top": {"area": xz_area, "fill_ratio": round(xz_fill, 4)},
            "front": {"area": xy_area, "fill_ratio": round(xy_fill, 4)},
            "side": {"area": yz_area, "fill_ratio": round(yz_fill, 4)},
        },
        "composition": {
            "base_middle_crown_mass": elevation,
            "top_silhouette_perimeter": _perimeter(top),
            "surface_faces_per_block": round(_surface_faces(solid) / blocks_count, 4),
        },
        "material_counts": dict(sorted(bom.items(), key=lambda kv: (-kv[1], kv[0]))[:12]),
    }


def _kind(name: str) -> str:
    try:
        return blocks.kind(name)
    except (KeyError, TypeError):
        return ""


def assess(model, brief=None) -> dict:
    """Combine a stated brief with measured evidence and only enforce declared thresholds."""
    brief = validate_brief(brief)
    got = metrics(model)
    quality = brief.get("quality", {})
    checks = []
    for key, actual in (("min_blocks", got["blocks"]), ("min_materials", got["materials"]),
                        ("min_lights", got["light_blocks"]), ("min_height", got["massing"].get("height", 0))):
        if key in quality:
            checks.append({"rule": key, "actual": actual, "required": quality[key],
                           "ok": actual >= quality[key]})
    result = {"brief": brief, "metrics": got, "checks": checks,
              "ok": all(check["ok"] for check in checks)}
    if brief.get("enforce") and not result["ok"]:
        failed = ", ".join(c["rule"] for c in checks if not c["ok"])
        raise ValueError(f"design quality brief failed: {failed}")
    return result


def render_packet(model, directory: str | Path, name: str) -> list[str]:
    """Write four visitor-scale perspective views plus a silhouette review.

    This is opt-in because it is evidence for a human review, not a substitute for the normal
    lightweight contact sheet emitted for every config.
    """
    from . import render3d
    from PIL import Image
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    out = []
    for yaw in (0, 90, 180, 270):
        image = render3d.render(model, render3d.orbit(model, yaw=yaw, pitch=16), 360, 260, ground=False)
        path = directory / f"{name}_yaw{yaw}.png"
        Image.fromarray(image).save(path); out.append(str(path))
    silhouette = render3d.render(model, render3d.orbit(model, yaw=45, pitch=12), 360, 260,
                                 ground=False, silhouette=True)
    path = directory / f"{name}_silhouette.png"
    Image.fromarray(silhouette).save(path); out.append(str(path))
    return out
