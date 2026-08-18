"""Composite design(s) onto a capture to make a PLANNED world file.

`mcbuild merge` is for merging captures - it keys on chunk coverage, which a design does not have, so
it silently drops them. This uses the same compositing the in-context audit uses.

    python tools/plan_merge.py out/island_deep.litematic "out/Shop Islet.litematic" -o out/islet_planned.litematic

Use it when one design has to be laid out against another that is not built yet: the atelier court
needs the enlarged islet, or it designs onto the raft as it stands today.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import scan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="capture to composite onto")
    ap.add_argument("designs", nargs="+", help="design .litematic files, applied in order")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()

    s = scan.load(a.base)
    for d in a.designs:
        other = scan.load(d)
        merged, overlap = scan.merge(s, other.model, other.origin)
        print(f"  + {os.path.basename(d)}: {overlap} cells already present")
        s = scan.Scan(merged, s.meta, s.litematic_path, s.sidecar_path)
    name = os.path.splitext(os.path.basename(a.out))[0]
    sx, sy, sz = s.model.shape_xyz
    meta = {**s.meta, "name": name,
            "origin": {"x": s.origin[0], "y": s.origin[1], "z": s.origin[2]},
            "size": {"x": sx, "y": sy, "z": sz},
            "planned_from": [os.path.basename(a.base)] + [os.path.basename(d) for d in a.designs]}
    scan.save_pair(a.out, s.model, meta, name=name)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
