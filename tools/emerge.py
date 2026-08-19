"""Cut a design down to the part that EMERGES past a plane, for a figure coming out of a surface.

    python tools/emerge.py "out/Lunging Jaguar.litematic" --axis z --keep-above 30012 \
        --out "out/Lunging Jaguar.litematic"

Why a tool and not a `finish` option: this is a sculptural decision, not a build rule. A relief
figure breaking out of a rock face is one of the few things a voxel statue does better than a
free-standing one - the cut edge is hidden by the surface it comes out of, so the half that is
never modelled is never missed, and every block saved goes into the half you can see.

The cut is a PLANE in world coordinates, so it can be lined up with the actual face of the thing the
figure emerges from - the lowland's rim, a cliff, a wall - rather than with the model's own box.

`--taper` fades the cut rather than slicing it square: cells within N of the plane are kept only if
they are deep inside the body, so the figure appears to dissolve into the surface instead of ending
at a guillotine edge. Without it the flat cut face reads as exactly what it is, a model cut in half.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import morph, scan, schem                      # noqa: E402

AXES = {"x": 2, "y": 0, "z": 1}                              # ids are [y, z, x]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design")
    ap.add_argument("--axis", choices=list(AXES), required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--keep-above", type=int, help="keep cells at or beyond this world coordinate")
    g.add_argument("--keep-below", type=int, help="keep cells at or under this world coordinate")
    ap.add_argument("--taper", type=int, default=3,
                    help="courses over which the cut fades into the surface (0 = square cut)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name")
    a = ap.parse_args()

    s = scan.load(a.design)
    m = s.model
    ids = m.ids.copy()
    ax = AXES[a.axis]
    o = s.meta["origin"]
    base = {"x": o["x"], "y": o["y"], "z": o["z"]}[a.axis]
    n = ids.shape[ax]
    world = np.arange(n) + base

    if a.keep_above is not None:
        keep = world >= a.keep_above
        edge = a.keep_above
        depth = world - edge                                 # 0 at the cut, growing inward
    else:
        keep = world <= a.keep_below
        edge = a.keep_below
        depth = edge - world

    shape = [1, 1, 1]
    shape[ax] = n
    ids *= keep.reshape(shape)

    # TAPER: near the cut, keep only what is well inside the body, so the figure melts into the
    # surface rather than ending on a flat face. "Well inside" is measured by how many solid
    # neighbours a cell has - a cell on the skin at the cut is the giveaway, one deep in the chest
    # is not.
    if a.taper > 0:
        solid = ids > 0
        n26 = morph.neighbor_count(solid, conn=26)
        d = np.broadcast_to(depth.reshape(shape), ids.shape)
        near = (d >= 0) & (d < a.taper)
        # the closer to the cut, the more enclosed a cell must be to survive
        need = 26 - (d.astype(float) / max(1, a.taper)) * 12.0
        ids = np.where(near & (n26 < need) & solid, 0, ids)

    solid = ids > 0
    if not solid.any():
        raise SystemExit("the cut removed everything - check the axis and the plane")
    # keep only the largest piece: a taper can shave off islands, and a design must be one piece
    lab, sizes = morph.components(solid, conn=6)
    if len(sizes) > 1:
        big = int(np.argmax(sizes)) + 1
        ids = np.where(lab == big, ids, 0)

    kept = int((ids > 0).sum())
    # TRIM TO WHAT IS LEFT, and move the origin to match. Cutting only zeroes cells; without this
    # the design keeps the whole original box, so half of it is empty air that every renderer,
    # every audit and every `progress` count has to carry around - and the paste origin still points
    # at a corner the figure no longer reaches.
    ys, zs, xs = np.nonzero(ids > 0)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    z0, z1 = int(zs.min()), int(zs.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    ids = ids[y0:y1, z0:z1, x0:x1]
    name = a.name or os.path.splitext(os.path.basename(a.out))[0]
    meta = {**s.meta, "name": name, "emerged": {"axis": a.axis, "plane": edge, "taper": a.taper},
            "origin": {"x": o["x"] + x0, "y": o["y"] + y0, "z": o["z"] + z0}}
    out = schem.Model(ids, m.palette)
    sx, sy, sz = out.shape_xyz
    meta["size"] = {"x": sx, "y": sy, "z": sz}
    scan.save_pair(a.out, out, meta, name=name)
    print(f"{os.path.basename(a.out)}: kept {kept} of {int((m.ids > 0).sum())} blocks "
          f"({kept / max(1, int((m.ids > 0).sum())):.0%}), cut at {a.axis}={edge}, taper {a.taper}")


if __name__ == "__main__":
    main()
