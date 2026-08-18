"""Machine/server profile: where Litematica lives, which server, which dimension.

Looked up in order: $MCBUILD_PROFILE, ./profile.yaml (repo root), built-in defaults (Jack's LiquidLauncher).
Teammates copy profile.yaml and edit paths; nothing else in the tooling is machine-specific.
"""
from __future__ import annotations

import os

import yaml

DEFAULTS = {
    "schem_dir": r"C:/Users/Jack/AppData/Roaming/CCBlueX/LiquidLauncher/data/gameDir/nextgen/schematics",
    "game_dir": r"C:/Users/Jack/AppData/Roaming/CCBlueX/LiquidLauncher/data/gameDir/nextgen",
    "server": "skyblock.net",
    "dim": "minecraft:overworld",
    "scan": "island",
    "cut": [-24251, 150, 29949, -24149, 270, 30051],
    "baseline": "out/island_top.litematic",
    "world_out": "out/island_now.litematic",
}
_cache = None


def load() -> dict:
    global _cache
    if _cache is None:
        path = os.environ.get("MCBUILD_PROFILE") or ("profile.yaml" if os.path.exists("profile.yaml") else None)
        data = {}
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        _cache = {**DEFAULTS, **data}
    return _cache
