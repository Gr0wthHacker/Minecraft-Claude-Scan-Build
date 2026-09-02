"""Generate every WorldSpec module artifact and report the park against its own contract.

`worldflow` prepares; this builds. One row per lot: blocks against its declared budget, the
material tier split against the policy, connected components, and whether it fits the lot it
owns. A lot that cannot build is a row, not a crash - the point of the table is to see the
whole park at once, and one broken generator must not hide the other twenty-three.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import palette, pipeline, schem  # noqa: E402


def main() -> int:
    configs = sorted((ROOT / "out" / "park_final" / "configs").glob("*.yaml"))
    spec = json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8"))
    lots = {m["name"]: m for m in spec["modules"]}
    only = set(sys.argv[1:])
    rows, tiers = [], Counter()
    for path in configs:
        import yaml
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        name = cfg["name"]
        if only and name not in only:
            continue
        module = lots[name]
        started = time.perf_counter()
        try:
            model, _res = pipeline.run_config(str(path), render_sheet=False, verbose=False)
        except Exception as exc:
            rows.append({"module": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if model is None:
            rows.append({"module": name, "error": "generator emitted nothing"}); continue
        counts = Counter()
        for index, entry in enumerate(model.names):
            if index:
                n = int((model.ids == index).sum())
                if n:
                    counts[entry.split("[")[0].replace("minecraft:", "")] += n
        local = Counter()
        for block, n in counts.items():
            local[palette.tier(block)] += n
        tiers += local
        sy, sz, sx = model.ids.shape
        budget = module["budget"]["blocks"]
        rows.append({"module": name, "blocks": sum(counts.values()), "budget": budget,
                     "pct": round(100 * sum(counts.values()) / budget), "size": [sx, sy, sz],
                     "lot": module["footprint"], "tiers": dict(local),
                     "seconds": round(time.perf_counter() - started, 2)})

    print(f"{'module':<24}{'blocks':>8}{'budget':>8}{'%':>5}  {'size xyz':<16}{'lot':<10}{'s':>6}  notes")
    built = 0
    for row in rows:
        if "error" in row:
            print(f"{row['module']:<24}{'ERROR':>8}{'':>8}{'':>5}  {row['error'][:74]}")
            continue
        built += row["blocks"]
        fits = row["size"][0] <= row["lot"][0] and row["size"][2] <= row["lot"][1]
        note = [] if fits else ["overflows lot"]
        if row["pct"] < 70: note.append("under budget")
        if row["pct"] > 125: note.append("over budget")
        print(f"{row['module']:<24}{row['blocks']:>8}{row['budget']:>8}{row['pct']:>4}%  "
              f"{str(row['size']):<16}{str(row['lot']):<10}{row['seconds']:>6}  {'; '.join(note)}")
    total = sum(tiers.values()) or 1
    print(f"\nmodules built {built:,} of a declared {sum(r.get('budget', 0) for r in rows):,}")
    print("material policy (78-86% cheap / 10-16% ok / 2-5% expensive):")
    for tier in ("cheap", "ok", "expensive"):
        print(f"  {tier:<12}{tiers[tier]:>9}  {100*tiers[tier]/total:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
