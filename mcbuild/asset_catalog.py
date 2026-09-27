"""Small declarative catalog for reusable architectural and infrastructure assets."""
from __future__ import annotations

STYLES = {
    "frontier": {"palette_roles": ["weathered_timber", "dusty_stone", "dark_metal", "warm_light"], "roof": "gable"},
    "hollow": {"palette_roles": ["dark_stone", "aged_timber", "oxidised_metal", "warm_light"], "roof": "gable"},
    "midway": {"palette_roles": ["painted_structure", "light_trim", "accent", "bright_light"], "roof": "flat"},
    "civic": {"palette_roles": ["masonry", "trim", "glass", "warm_light"], "roof": "hip"},
    "industrial": {"palette_roles": ["brick", "steel", "concrete", "utility_light"], "roof": "sawtooth"},
}
ASSETS = {
    "path": {"anchors": ["start", "end"], "max_span": 999},
    "bridge": {"anchors": ["deck_a", "deck_b"], "max_span": 24},
    "facade_bay": {"anchors": ["frontage"], "max_span": 6},
    "roof": {"anchors": ["wall_ring"], "max_span": 12},
    "station": {"anchors": ["entry", "queue", "board", "exit", "service"], "max_span": 12},
}


def resolve(asset: str, style: str) -> dict:
    if asset not in ASSETS: raise ValueError(f"unknown asset {asset!r}")
    if style not in STYLES: raise ValueError(f"unknown style {style!r}")
    return {"asset": asset, **ASSETS[asset], "style": style, **STYLES[style]}
