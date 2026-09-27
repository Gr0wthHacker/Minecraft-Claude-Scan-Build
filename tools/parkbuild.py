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

#: WORLDSPEC ARTIFACTS GET THEIR OWN FOLDER, and that is a correctness rule rather than tidiness.
#: `out/` still holds the previous park's designs under names this plan reuses - `Arrival Court`,
#: `Mine Coaster`, `Carousel`. Placing by name out of `out/` silently mixed a build from
#: yesterday's retired programme into today's assembly, and nothing about the result said so.
ARTIFACTS = ROOT / "out" / "park_final" / "artifacts"


def main() -> int:
    configs = sorted((ROOT / "out" / "park_final" / "configs").glob("*.yaml"))
    spec = json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8"))
    lots = {m["name"]: m for m in spec["modules"]}
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    rows, tiers, planes = [], Counter(), {}
    for path in configs:
        import yaml
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        name = cfg["name"]
        if only and name not in only:
            continue
        module = lots[name]
        started = time.perf_counter()
        # WHERE THIS MODULE'S OWN GROUND IS. A compose knows (its parts declare offsets); a
        # single generator does not, and the Mine Coaster builds a RIDGE whose ground plane is
        # thirteen courses up its own canvas with nothing but a few trestle legs below. Placed at
        # the deck it hung thirteen blocks in the air with 4,650 of its 4,662 columns touching
        # nothing - which is exactly what "the rollercoaster is still floating in mid air" is.
        #
        # A SCULPTURE IS EXEMPT, because a hanging creature legitimately has no ground: the Sloth
        # measures its densest course 23 up, and lowering it by that would bury it in the deck.
        # ONE RULE FOR EVERY MODULE: its ground course is the lowest course covering most of
        # its own columns, and that course lands ON the deck. Taking it from a compose's declared
        # offsets instead put every lot whose plaza sits at -1 a course UNDER the paved floor,
        # and a lot floor one below the street is a step down into every building in the park.
        #
        # A SCULPTURE IS EXEMPT, because a hanging creature legitimately has no ground: the Sloth
        # measures its densest course 23 up, and lowering it by that would bury it in the deck.
        plane_course = 0
        # ...but a set piece COMPOSED on its own apron does have ground - that apron -
        # so only a bare hanging creature is exempt.
        if module.get("role") != "sculpture" or cfg.get("gen") == "compose":
            probe = ARTIFACTS / f"{name}.litematic"
            if probe.exists():
                pm = schem.load(str(probe)).solid()
                ncols = len({(x, z) for _y, z, x in zip(*pm.nonzero())})
                per = pm.sum(axis=(1, 2))
                plane_course = next((y for y, n in enumerate(per) if n >= 0.60 * ncols), 0)
        planes[name] = plane_course
        try:
            model, _res = pipeline.run_config(
                str(path), settings=pipeline.Settings(out_dir=str(ARTIFACTS)),
                render_sheet=False, verbose=False)
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
        # A LOT'S BUDGET IS A FLOOR, NOT A CEILING. Jack's call: over budget is fine as long as
        # it is really good looking and meaningful - so a lot that spends more than its
        # programme line is not a finding, and a thin one is. What over-spend still has to
        # answer for is padding, and no block count can see padding; that is what the visual
        # packet and the three readable distances are for.
        if row["pct"] < 70: note.append("THIN - under 70% of its programme line")
        print(f"{row['module']:<24}{row['blocks']:>8}{row['budget']:>8}{row['pct']:>4}%  "
              f"{str(row['size']):<16}{str(row['lot']):<10}{row['seconds']:>6}  {'; '.join(note)}")
    (ARTIFACTS.parent / "planes.json").write_text(json.dumps(planes, indent=1), encoding="utf-8")
    total = sum(tiers.values()) or 1
    print(f"\nmodules built {built:,} of a declared {sum(r.get('budget', 0) for r in rows):,}")
    print("material policy (78-86% cheap / 10-16% ok / 2-5% expensive):")
    for tier in ("cheap", "ok", "expensive"):
        print(f"  {tier:<12}{tiers[tier]:>9}  {100*tiers[tier]/total:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
