"""Measure a WorldSpec lot's composition against its own contract.

The budget spec exists to stop two opposite failures - thin generators that look like prototypes,
and expensive bulk that buys nothing. Neither is visible from a generator call; both are visible
from one table. For every module this prints:

    blocks vs its declared budget . plan footprint vs its declared lot . connected components
    cheap/ok/expensive share . currency blocks . blocks the 1.19 server cannot place

Usage:
    python tools/lotfit.py                      every module in park_final.world.json
    python tools/lotfit.py "Trailhead Gate"     one module
    python tools/lotfit.py --json               machine-readable, for a gate or a test
"""
from __future__ import annotations

import json
import sys
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import blocks, palette  # noqa: E402
from mcbuild.gen import GENERATORS  # noqa: E402


def components(model) -> int:
    """6-connected components. Diagonal adjacency is NOT connectivity: this repo has shipped
    detached ear tips, floating ossicones and a three-piece rail line from exactly that."""
    solid = model.solid()
    seen = solid.copy() & False
    total = 0
    ys, zs, xs = solid.nonzero()
    cells = set(zip(ys.tolist(), zs.tolist(), xs.tolist()))
    while cells:
        start = cells.pop()
        total += 1
        todo = deque([start])
        while todo:
            y, z, x = todo.popleft()
            for n in ((y+1, z, x), (y-1, z, x), (y, z+1, x), (y, z-1, x), (y, z, x+1), (y, z, x-1)):
                if n in cells:
                    cells.discard(n); todo.append(n)
    del seen
    return total


def measure(name: str, params: dict) -> dict:
    canvas = GENERATORS[name].build(params or {}, None)
    model = canvas.to_model()
    sy, sz, sx = model.ids.shape
    counts = Counter()
    for index, entry in enumerate(model.names):
        n = int((model.ids == index).sum()) if index else 0
        if n:
            counts[entry.split("[")[0].replace("minecraft:", "")] += n
    tiers = Counter()
    currency, illegal = {}, {}
    for block, n in counts.items():
        tiers[palette.tier(block)] += n
        if not blocks.spendable(block):
            currency[block] = n
        if not blocks.available(block):
            illegal[block] = n
    total = sum(counts.values())
    return {"blocks": total, "size_xyz": [sx, sy, sz], "components": components(model),
            "tiers": dict(tiers), "currency": currency, "not_1_19": illegal,
            "top_blocks": dict(counts.most_common(8))}


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv[1:]
    spec = json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8"))
    wanted = set(args)
    rows = []
    for module in spec["modules"]:
        if wanted and module["name"] not in wanted:
            continue
        budget = module["budget"]["blocks"]
        fw, fd = module["footprint"]
        try:
            result = measure(module["generator"], module.get("params") or {})
        except Exception as exc:  # a lot that cannot build is the finding, not a crash
            rows.append({"module": module["name"], "error": f"{type(exc).__name__}: {exc}",
                         "budget": budget, "footprint": [fw, fd]})
            continue
        sx, sy, sz = result["size_xyz"]
        rows.append({"module": module["name"], "generator": module["generator"], "budget": budget,
                     "footprint": [fw, fd], "fits": sx <= fw and sz <= fd, **result,
                     "budget_pct": round(100 * result["blocks"] / budget)})
    if as_json:
        print(json.dumps(rows, indent=2)); return 0
    print(f"{'module':<24}{'gen':<13}{'blocks':>8}{'budget':>8}{'%':>5}  {'size xyz':<16}"
          f"{'lot':<10}{'fit':<5}{'cmp':>4}  issues")
    short = 0
    for row in rows:
        if "error" in row:
            print(f"{row['module']:<24}{'-':<13}{'ERROR':>8}{row['budget']:>8}{'':>5}  {row['error'][:70]}")
            continue
        bad = []
        if row["currency"]: bad.append("CURRENCY " + ",".join(row["currency"]))
        if row["not_1_19"]: bad.append("NOT-1.19 " + ",".join(row["not_1_19"]))
        if row["components"] != 1: bad.append(f"{row['components']} components")
        if not row["fits"]: bad.append("overflows lot")
        # the budget is a floor: thin is the failure, generous is not
        if row["budget_pct"] < 70: bad.append("THIN"); short += 1
        print(f"{row['module']:<24}{row['generator']:<13}{row['blocks']:>8}{row['budget']:>8}"
              f"{row['budget_pct']:>4}%  {str(row['size_xyz']):<16}{str(row['footprint']):<10}"
              f"{'y' if row['fits'] else 'N':<5}{row['components']:>4}  {'; '.join(bad)}")
    built = sum(r.get("blocks", 0) for r in rows)
    print(f"\ntotal built {built:,} of declared module budget "
          f"{sum(r['budget'] for r in rows):,}  ({short} lots under 70% of budget)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
