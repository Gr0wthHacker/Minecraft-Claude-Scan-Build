"""WHERE THE LAMPS ACTUALLY STAND.

Jack: "still lots of issues with lamp placements, awkward, weird." A picture cannot settle it -
`render3d` draws a rod, a fence, a wall and iron bars all as full cubes, and it has now hidden
five separate faults on this park. So the lamps are counted off the block list.

A street lamp sits on ONE line per verge; that is what makes a row of them read as a row. This
groups every mast by the line it stands on, and says which street's verge each line IS.

    python tools/park_lamps.py
"""
from __future__ import annotations

import sys
from collections import Counter

import numpy as np
import yaml

sys.path.insert(0, ".")
from mcbuild.gen import parkways  # noqa: E402
from tools.park_lots import params_from_config  # noqa: E402

#: the shaft of each land's own lamp, read at y3 - the one course every design has a mast in
MASTS = {"lightning_rod", "dark_oak_fence", "polished_blackstone_brick_wall"}


def masts(p: dict):
    c = parkways.build(dict(p))
    names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(c.palette)}
    ids = {i for i, n in names.items() if n in MASTS}
    layer = c.ids[3]                      # [z, x]
    zs, xs = np.nonzero(np.isin(layer, list(ids)))
    return [(int(x), int(z)) for x, z in zip(xs, zs)], c


def verges(p: dict) -> dict[int, str]:
    """The V line every lamp SHOULD be on, and whose verge it is."""
    out = {}
    sv, sh = p["spine_v"], p["spine_half"]
    out[sv - sh - 2] = "spine west verge"
    out[sv + sh + 2] = "spine east verge"
    pv, ph = p["promenade_v"], p["promenade_half"]
    out[pv - ph - 2] = "promenade front verge"
    out[pv + ph + 2] = "promenade back verge"
    return out


def main():
    p = params_from_config()
    pts, c = masts(p)
    lines = verges(p)
    step = p.get("lamp_every", 22)
    start = p["spine_v"] + p.get("plaza_half", 11) + 6
    rhythm = list(range(start, p["service_v"] - 2, step))
    print(f"{len(pts)} lamp masts\n")
    print(f"{'V line':>7} {'n':>4}  what")
    for v, n in sorted(Counter(x for x, _ in pts).items()):
        if v in lines:
            what = lines[v]
        elif v in rhythm:
            what = f"avenue rhythm ({rhythm.index(v) + 1} of {len(rhythm)})"
        else:
            what = "*** OFF EVERY LINE ***"
        print(f"{v:>7} {n:>4}  {what}")
    on = sum(n for v, n in Counter(x for x, _ in pts).items()
             if v in lines or v in rhythm)
    print(f"\non a named line: {on}/{len(pts)}   "
          f"lines used: {len(set(x for x, _ in pts))}")
    print(f"meta: {c.meta.get('lamps')} placed, "
          f"{c.meta.get('lamps_refused_on_paving')} refused, "
          f"{c.meta.get('lamps_per_line')}")


if __name__ == "__main__":
    main()
