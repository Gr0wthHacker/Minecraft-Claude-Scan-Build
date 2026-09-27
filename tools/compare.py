"""Compare built animals against EACH OTHER, which no other tool in this repo does.

    python tools/compare.py                     every family, every pair
    python tools/compare.py --family felid
    python tools/compare.py --views             also write a side-by-side render per family

This exists because of a specific failure. The rubric passed a bear, a lion and a polar bear at GOOD
while all three were visibly the same animal, and it could not have caught it: `silhouette` compared
each model to a reference TABLE, so three models equally close to three different tables all scored
well. Nothing measured model against model. One glance caught what the numbers could not.

Two distances, kept apart on purpose:

  SHAPE  1 - IoU of the normalised side silhouette. Within a family this SHOULD be small - a lion
         and a jaguar are the same animal in outline and the family table is doing its job when
         they measure alike. What must not happen is for it to be small everywhere INCLUDING where
         a feature is supposed to break it: the lion's mane and the bear's skull are the two places
         the shape is meant to separate, and if they read 0.02 the feature is not being built.

  COAT   total-variation distance between the two block mixes. This is what actually separates a
         brown bear from a polar bear, and there is nothing wrong with that - but it is paint, and
         a statue carried entirely by paint fails the question the rubric asks last: would you know
         the species with the colour removed?
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np                                          # noqa: E402
import rubric                                               # noqa: E402
from mcbuild.gen import taxonomy                            # noqa: E402

# Below this, two builds are the same shape. Fine between siblings with no distinguishing
# structure; a failure for a pair whose whole difference is meant to be a mane or a skull.
SAME = 0.08


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family")
    ap.add_argument("--retired", action="store_true",
                    help="include RETIRED species (the cats and bears). They still build; they are "
                         "simply not live work - see the note at the foot of species.yaml.")
    ap.add_argument("--all-pairs", action="store_true",
                    help="also compare ACROSS families, which should always be far apart")
    a = ap.parse_args()

    sp = taxonomy.species() if a.retired else taxonomy.live()
    fams = {}
    for name, v in sp.items():
        fams.setdefault(v.get("family"), []).append(name)

    built, missing = {}, []
    for name in sp:
        got = rubric._sibling_build(name)
        if got is None:
            missing.append(name)
        else:
            built[name] = got
    if missing:
        print(f"not built, so not compared: {', '.join(sorted(missing))}\n")
    if len(built) < 2:
        print("need at least two built animals to compare")
        return

    for fam in sorted(fams) if not a.family else [a.family]:
        members = sorted(n for n in fams.get(fam, []) if n in built)
        if len(members) < 2:
            continue
        print(f"{fam}")
        for x, y in itertools.combinations(members, 2):
            shape, coat = _dist(built[x], built[y])
            flag = "   <-- SAME SHAPE" if shape < SAME else ""
            print(f"  {x:12s} vs {y:12s}  shape {shape:.3f}   coat {coat:.3f}{flag}")
        print()

    if a.all_pairs:
        print("across families (these should all be large)")
        for x, y in itertools.combinations(sorted(built), 2):
            if taxonomy.family_of(x) == taxonomy.family_of(y):
                continue
            shape, coat = _dist(built[x], built[y])
            flag = "   <-- SAME SHAPE, DIFFERENT FAMILY" if shape < SAME else ""
            print(f"  {x:12s} vs {y:12s}  shape {shape:.3f}   coat {coat:.3f}{flag}")


def _dist(a, b):
    sa, na = a
    sb, nb = b
    inter, union = np.minimum(sa, sb).sum(), np.maximum(sa, sb).sum()
    shape = 1.0 - (inter / union if union else 1.0)
    ca, cb = rubric._palette_mix(na), rubric._palette_mix(nb)
    coat = 0.5 * sum(abs(ca.get(k, 0.0) - cb.get(k, 0.0)) for k in set(ca) | set(cb))
    return shape, coat


if __name__ == "__main__":
    main()
