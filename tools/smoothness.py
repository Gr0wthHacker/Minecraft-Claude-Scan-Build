"""Measure how smooth a design's form is, and sweep parameters to make it smoother.

    python tools/smoothness.py configs/giraffe.yaml                 # just measure
    python tools/smoothness.py configs/giraffe.yaml --sweep         # try combinations, rank them

Three numbers (see `mcbuild.gen.smooth.roughness`), all lower-is-better:

    spikes    solid cells with few solid neighbours - single blocks poking out of a surface
    notches   air cells nearly surrounded by solid - one-block dents
    jerk      mean |second difference| of cross-section area up the body. A cone is ~0; a stack of
              boxes spikes at every step. This is the one that catches "it goes in and out".

`score` weights them into one number so a sweep can rank. Connectivity is a HARD gate: a variant that
breaks the model into pieces is rejected outright however smooth its numbers look, because relaxing a
shape can detach exactly the thin features (ossicone, ear, mane) the smoothing was not meant to touch.
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcbuild import morph                                   # noqa: E402
from mcbuild.gen import smooth                              # noqa: E402
from mcbuild.pipeline import Settings, run_config           # noqa: E402

# what a sweep is allowed to vary, and over what
GRID = {
    "params.relax_rounds": [3, 5],
    "params.relax_fill": [10, 12],
    "params.relax_keep": [10, 11],
    "params.section_n": [2.0, 2.3],
}


def measure(cfg_path: str, over: dict | None = None) -> dict:
    m, r = run_config(cfg_path, settings=Settings(out_dir="out/_sweep"), overrides=over or {},
                      render_sheet=False, verbose=False)
    solid = m.solid()
    ys, zs, xs = np.where(solid)
    cells = list(zip(xs.tolist(), ys.tolist(), zs.tolist()))
    got = smooth.roughness(cells)
    _lab, sizes = morph.components(solid, conn=6)
    got["pieces"] = len(sizes)
    # overlap is the design meeting the world it stands on, not a defect - same rule as
    # tests/test_designs.py. Counting it here rejected every single variant.
    got["problems"] = len([x for x in r.problems if x.kind != "overlap"])
    # rank on the SCALE-FREE numbers, or the sweep just rewards whichever variant is smallest
    got["score"] = round(got["spike_rate"] + got["jerk_rel"] + got["notches"] * 0.5, 3)
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args()

    base = measure(a.config)
    print(f"baseline  {base}")
    if not a.sweep:
        return

    keys = list(GRID)
    rows = []
    for combo in itertools.product(*(GRID[k] for k in keys)):
        over = dict(zip(keys, combo))
        try:
            got = measure(a.config, over)
        except Exception as exc:
            print(f"  {combo} -> FAILED {type(exc).__name__}")
            continue
        # a variant that shatters the model is not a candidate, whatever its numbers say
        ok = got["pieces"] == 1 and got["problems"] == 0
        rows.append((got["score"], ok, over, got))
        flag = "" if ok else "  REJECTED (pieces/problems)"
        print(f"  {[f'{k.split(chr(46))[-1]}={v}' for k, v in over.items()]} "
              f"score={got['score']:7.2f} spike_rate={got['spike_rate']:6.2f} jerk_rel={got['jerk_rel']:6.2f} "
              f"pieces={got['pieces']}{flag}")

    good = sorted((r for r in rows if r[1]), key=lambda r: r[0])
    print(f"\nbest {a.top} of {len(good)} valid variants:")
    for score, _ok, over, got in good[:a.top]:
        print(f"  score {score:7.2f}  {over}   {got}")


if __name__ == "__main__":
    main()
