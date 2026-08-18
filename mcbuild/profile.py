"""Machine/server profile: where Litematica lives, which server, which dimension.

Looked up in order: $MCBUILD_PROFILE, ./profile.yaml, ./profile.example.yaml, built-in defaults.

Copy profile.example.yaml to profile.yaml and edit the paths for your machine - profile.yaml is
gitignored, so your own paths never end up in a commit. Nothing else in the tooling is
machine-specific; if you find a hard-coded path anywhere else, it is a bug.
"""
from __future__ import annotations

import os

import yaml

def _default_schem_dir() -> str:
    """Best guess at a Litematica schematics folder, so a fresh clone does something sensible."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, ".minecraft", "schematics").replace("\\", "/")
    return os.path.expanduser("~/.minecraft/schematics")


DEFAULTS = {
    "schem_dir": _default_schem_dir(),
    "game_dir": os.path.dirname(_default_schem_dir()),
    "server": "localhost",
    "dim": "minecraft:overworld",
    "scan": "island",
    "cut": [-24251, 150, 29949, -24149, 270, 30051],
    "baseline": "out/island_top.litematic",
    "world_out": "out/island_now.litematic",
    "origin_lock": [-24251, 150, 29949],   # every design is padded to this corner: ONE paste origin for everything
}
_cache = None


def load() -> dict:
    global _cache
    if _cache is None:
        path = os.environ.get("MCBUILD_PROFILE")
        if not path:
            for cand in ("profile.yaml", "profile.example.yaml"):
                if os.path.exists(cand):
                    path = cand
                    break
        data = {}
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        _cache = {**DEFAULTS, **data}
    return _cache
