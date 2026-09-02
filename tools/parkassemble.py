"""Place every generated module at its WorldSpec position and prove the assembled park.

`worldflow` prepares and `parkbuild` generates, but each module is built in its OWN local space
with no world origin - deliberately, because PARK_BUILD_EXECUTION.md is explicit that the anchor
in park_final.world.json is "a provisional registration value" and "not authorization to paste
into the live island unchanged". So placement happens HERE, in the plan's own local lattice, for
review and for walk checks - never by writing a world coordinate into a module's sidecar.

    python tools/parkassemble.py            place every module, write sidecars, report clashes
    python tools/parkassemble.py --merge    ...and fold the whole park into one artifact

Output goes to ``out/park_final/placed/``. Each module gets a sidecar whose origin is its plan
position, which is what makes the result readable by `mcbuild worldvalidate` and by the renderer.

**A CLASH IS REPORTED PER PAIR, NOT COUNTED.** Two designs contending for one cell is a work
problem - you place a block, the next placement says it is wrong, you break it and place it
again - and a single number cannot tell you which two lots to move.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from pathlib import Path as pathlib_Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import profile as mcprofile, schem, scan, worldexport, worldrender, worldspec  # noqa: E402

PLACED = ROOT / "out" / "park_final" / "placed"
#: Built by `tools/parkbuild.py`. NOT `out/` - that still holds the previous park's designs under
#: names this plan reuses, and placing by name out of it mixes a retired programme's build into
#: today's assembly with nothing to say so.
ARTIFACTS = ROOT / "out" / "park_final" / "artifacts"


def plan() -> dict:
    return worldspec.compile(json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8")))


def place(compiled: dict) -> tuple[list[dict], list[str]]:
    """Write each built module at its plan position. Returns (placed, missing)."""
    PLACED.mkdir(parents=True, exist_ok=True)
    plane = int(compiled["site"]["build_plane"])
    placed, missing = [], []
    for module in compiled["modules"]:
        source = ARTIFACTS / f"{module['name']}.litematic"
        if not source.exists():
            missing.append(module["name"]); continue
        model = schem.load(str(source))
        x, z = module["at"]
        # A module's own y=0 is its build plane. Everything in this lattice is local to the
        # WorldSpec anchor, which is provisional - see the module docstring.
        origin = (int(x), plane, int(z))
        target = PLACED / f"{module['name']}.litematic"
        scan.save_pair(str(target), model,
                       {"origin": {"x": origin[0], "y": origin[1], "z": origin[2]},
                        "kind": module.get("generator"), "role": module.get("role"),
                        "plot": module.get("plot"), "local_to": "park_final.world.json anchor",
                        "anchor_status": "provisional; rebase before any live paste"},
                       name=module["name"])
        sy, sz, sx = model.ids.shape
        placed.append({"module": module["name"], "origin": list(origin), "size": [sx, sy, sz],
                       "blocks": int(model.solid().sum()), "path": str(target)})
    return placed, missing


def clashes(placed: list[dict]) -> list[dict]:
    """Which two lots contend for which cells. Occupancy is built once and owners recorded."""
    owner: dict[tuple[int, int, int], str] = {}
    pairs: Counter = Counter()
    for item in placed:
        model = schem.load(item["path"])
        ox, oy, oz = item["origin"]
        for y, z, x in zip(*model.solid().nonzero()):
            pos = (int(x) + ox, int(y) + oy, int(z) + oz)
            prior = owner.get(pos)
            if prior is None:
                owner[pos] = item["module"]
            elif prior != item["module"]:
                pairs[tuple(sorted((prior, item["module"])))] += 1
    return [{"between": list(pair), "cells": n} for pair, n in pairs.most_common()]


def infrastructure_model(compiled: dict):
    """WorldSpec layer 1+2 as ONE artifact rather than 300 chunk files.

    `worldexport.export_chunks` is right for a build graph and wrong for a human: nobody previews
    a park by loading three hundred schematics. The sparse world is dense-packed once here, and
    its origin is the plan lattice, exactly like a placed module's.
    """
    import numpy as np
    from mcbuild import nbt
    world = worldrender.infrastructure(compiled)
    cells = [(pos, state) for chunk in world.chunks.values() for pos, state in chunk.items()]
    xs = [p[0] for p, _ in cells]; ys = [p[1] for p, _ in cells]; zs = [p[2] for p, _ in cells]
    ox, oy, oz = min(xs), min(ys), min(zs)
    sx, sy, sz = max(xs) - ox + 1, max(ys) - oy + 1, max(zs) - oz + 1
    palette = [nbt.block_state("minecraft:air")]
    index = {}
    ids = np.zeros((sy, sz, sx), np.int32)
    for (x, y, z), state in cells:
        key = index.get(state)
        if key is None:
            key = index[state] = len(palette); palette.append(nbt.block_state(state))
        ids[y - oy, z - oz, x - ox] = key
    return schem.Model(ids, palette), (ox, oy, oz)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--merge", action="store_true", help="also fold the park into one artifact")
    ap.add_argument("--no-clash", action="store_true", help="skip the pairwise clash report")
    ap.add_argument("--ship", action="store_true",
                    help="copy the placed modules and the assembled park into the game's schematics folder")
    args = ap.parse_args()

    compiled = plan()
    placed, missing = place(compiled)
    print(f"placed {len(placed)} of {len(compiled['modules'])} modules")
    for item in placed:
        print(f"  {item['module']:<24}{item['blocks']:>8} at {item['origin']}  size {item['size']}")
    if missing:
        print(f"\nnot built yet ({len(missing)}): {', '.join(missing)}")
    if not args.no_clash and placed:
        found = clashes(placed)
        print("\nlot clashes:", "none" if not found else "")
        for item in found:
            print(f"  {item['between'][0]} x {item['between'][1]}: {item['cells']} cells")
    if (args.merge or args.ship) and placed:
        infra, infra_origin = infrastructure_model(compiled)
        infra_path = PLACED / "Park Infrastructure.litematic"
        scan.save_pair(str(infra_path), infra,
                       {"origin": {"x": infra_origin[0], "y": infra_origin[1], "z": infra_origin[2]},
                        "kind": "infrastructure", "local_to": "park_final.world.json anchor",
                        "anchor_status": "provisional; rebase before any live paste"},
                       name="Park Infrastructure")
        print(f"infrastructure {int(infra.solid().sum()):,} blocks at {infra_origin}")
        # infrastructure FIRST so a building wins a contested cell: the paving is laid under a
        # building on purpose, and a picture of the street painted through a wall helps nobody.
        base = scan.load(str(infra_path))
        for item in placed:
            other = scan.load(item["path"])
            merged, _overlap = scan.merge(base, other.model, other.origin)
            ox, oy, oz = base.origin; mx, my, mz = other.origin
            new = (min(ox, mx), min(oy, my), min(oz, mz))
            base = scan.Scan(merged, {**base.meta, "origin": {"x": new[0], "y": new[1], "z": new[2]}},
                             base.litematic_path, base.sidecar_path)
        out = ROOT / "out" / "park_final" / "Park Complete.litematic"
        scan.save_pair(str(out), base.model, base.meta, name="Park Complete")
        sy, sz, sx = base.model.ids.shape
        print(f"wrote {out}  {sx}x{sy}x{sz}  {int(base.model.solid().sum()):,} blocks")
        if args.ship:
            import shutil
            dest = Path(mcprofile.load()["schem_dir"])
            dest.mkdir(parents=True, exist_ok=True)
            shipped = []
            for src in [out] + sorted(PLACED.glob("*.litematic")):
                for suffix in (".litematic", ".scan.json"):
                    side = src.with_suffix(suffix)
                    if side.exists():
                        shutil.copy2(side, dest / side.name)
                        if suffix == ".litematic": shipped.append(side.stem)
            print(f"shipped {len(shipped)} schematics to {dest}")
            for name in shipped: print(f"  {name}")


if __name__ == "__main__":
    raise SystemExit(main())
