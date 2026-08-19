"""Tune an animal against the WHOLE rubric, not one dimension of it.

    python tools/refine.py configs/jaguar.yaml
    python tools/refine.py /tmp/bear.yaml --species bear --apply

Why this exists rather than sweeping `tools/smoothness.py`: optimising a single dimension is actively
harmful here, and measurably so. Sweeping the smoothing alone took the bear's surface score from 0.60
to 0.73 and its proportion score from 0.88 to 0.50 - because every smoothing pass rewards thickening,
so the sweep inflated the animal until the silhouette test reported it as an ELEPHANT. Its total fell.

So this sweeps the same parameters and scores each variant with `rubric.score`, which is weighted and
gated. It reports what each variant does to every dimension, so a win can be checked rather than
trusted, and it never proposes a variant that fails a gate.
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import sys

import numpy as np
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import rubric                                              # noqa: E402
from mcbuild import morph, scan                            # noqa: E402
from mcbuild.pipeline import Settings, run_config          # noqa: E402

GRID = {
    "params.relax_rounds": [3, 4, 5],
    "params.relax_fill": [11, 12, 13],
    "params.relax_keep": [10, 11],
    "params.section_n": [2.0, 2.2, 2.4],
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--species")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()

    cfg = yaml.safe_load(pathlib.Path(a.config).read_text(encoding="utf-8"))
    name = cfg.get("name") or pathlib.Path(a.config).stem
    species = a.species or (cfg.get("params") or {}).get("profile") or "giraffe"
    spec = yaml.safe_load(rubric.RUBRIC.read_text(encoding="utf-8"))

    base = _run(a.config, {}, name, species, spec)
    print(f"{name} ({species})   baseline {base[0]:.3f}\n")
    print(f"{'rounds fill keep n':22s} {'total':>6s}  " +
          "  ".join(f"{k[:4]:>5s}" for k in sorted(base[1])))
    rows = [(base[0], {}, base[1])]
    keys = list(GRID)
    for combo in itertools.product(*(GRID[k] for k in keys)):
        over = dict(zip(keys, combo))
        try:
            got = _run(a.config, over, name, species, spec)
        except Exception as exc:
            print(f"  {combo} FAILED {type(exc).__name__}")
            continue
        if got is None:
            continue
        rows.append((got[0], over, got[1]))
        label = " ".join(str(v) for v in combo)
        mark = "  <-- best so far" if got[0] > max(r[0] for r in rows[:-1]) else ""
        print(f"{label:22s} {got[0]:6.3f}  " +
              "  ".join(f"{got[1][k][0]:5.2f}" for k in sorted(got[1])) + mark)

    rows.sort(key=lambda r: -r[0])
    print(f"\nbest {a.top}:")
    for total, over, dims in rows[:a.top]:
        wins = ", ".join(f"{k.split('.')[-1]}={v}" for k, v in over.items()) or "(baseline)"
        print(f"  {total:.3f}  {wins}")
    best = rows[0]
    if best[1]:
        gain = best[0] - base[0]
        print(f"\napply: {best[1]}   (+{gain:.3f} on the total)")
        for k in sorted(best[2]):
            d = best[2][k][0] - base[1][k][0]
            if abs(d) >= 0.02:
                print(f"    {k:11s} {base[1][k][0]:.2f} -> {best[2][k][0]:.2f}  {d:+.2f}")
    else:
        print("\nthe current settings are already the best in this grid.")


def _run(cfg_path, over, name, species, spec):
    m, r = run_config(cfg_path, settings=Settings(out_dir="out/_refine"), overrides=over,
                      render_sheet=False, verbose=False)
    solid = m.solid()
    # gates first: a variant that shatters or floats is not a candidate however it scores
    _lab, sizes = morph.components(solid, conn=6)
    if len(sizes) != 1:
        return None
    if [p for p in r.problems if p.kind != "overlap"]:
        return None
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    try:
        meta = scan.load(str(pathlib.Path("out/_refine") / (name + ".litematic"))).meta or {}
    except Exception:
        meta = {}
    pose = meta.get("pose") or "standing"

    class _H:
        pass
    h = _H()
    h.model = m
    return rubric.score(solid, names, meta, species, pose, model=h, spec=spec)


if __name__ == "__main__":
    main()
