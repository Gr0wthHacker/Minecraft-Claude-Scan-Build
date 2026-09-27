"""Fold per-land lot fragments into the WorldSpec.

Lot composition is designed land by land, in parallel, so each land writes its own fragment
under ``out/lots/<land>.json`` as ``{"<Module Name>": {"generator": ..., "params": {...}}}``.
Only ONE writer touches ``park_final.world.json`` - this one - so parallel design work cannot
produce a lost update on the plan every other tool reads.

A fragment naming a module the plan does not have is an ERROR, not a skip: a params block that
silently applies to nothing is exactly the "does nothing, quietly" failure this repo keeps
writing rules about.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "park_final.world.json"


def main() -> int:
    fragments = sorted((ROOT / "out" / "lots").glob("*.json"))
    if not fragments:
        print("no fragments under out/lots"); return 1
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    modules = {m["name"]: m for m in spec["modules"]}
    applied, unknown = [], []
    for path in fragments:
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, entry in data.items():
            if name not in modules:
                unknown.append(f"{path.name}: {name}"); continue
            module = modules[name]
            # A fragment may re-point a lot at `compose`; the generator is part of the design.
            if isinstance(entry, dict) and "params" in entry:
                if entry.get("generator"):
                    module["generator"] = entry["generator"]
                module["params"] = entry["params"]
            else:
                module["params"] = entry
            # PARAMS THAT DECLARE `parts` ARE A COMPOSITION, whatever the fragment said about a
            # generator. A fragment that supplies parts and forgets to re-point the generator
            # leaves the lot on its old single-generator, which then raises "needs params.at"
            # and looks like the composition was never written.
            if isinstance(module.get("params"), dict) and module["params"].get("parts"):
                module["generator"] = "compose"
            applied.append(name)
    if unknown:
        print("fragment names no such module:", *unknown, sep="\n  "); return 1
    missing = [m["name"] for m in spec["modules"] if not m.get("params")]
    SPEC.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"applied {len(applied)} lots from {len(fragments)} fragments")
    if missing:
        print("still without params:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
