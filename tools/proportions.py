"""Measure a built statue's proportions and compare them with the real animal's.

    python tools/proportions.py "Void Giraffe"

Everything is expressed as a fraction of TOTAL HEIGHT, which is the only measurement that survives a
change of scale, and is how anatomy references quote animals anyway.

Reference figures are for an adult giraffe, ~5.5 m to the top of the head:

    withers height   3.2 m    the shoulder. The single most telling number - it is what makes a
                              giraffe look like it stands on stilts rather than on legs.
    leg              1.9 m    ground to belly
    body depth       1.3 m    belly to withers
    body length      2.3 m    chest to rump - about as long as the leg
    body width       0.9 m    NARROW. A giraffe is a deep, slab-sided animal, not a barrel.
    neck             2.2 m
    head length      0.65 m
    leg width        0.28 m

The width numbers are the ones a voxel build gets wrong, because thickening a shape makes it smoother
and every smoothness metric quietly rewards that. Anatomy has to be checked separately or the animal
inflates one sweep at a time.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcbuild import scan                                    # noqa: E402

ANIMALS = pathlib.Path(__file__).resolve().parent.parent / "mcbuild/data/animals.yaml"


def reference(species: str) -> dict:
    """Real-animal measurements as fractions of total height, from mcbuild/data/animals.yaml."""
    import yaml
    table = yaml.safe_load(ANIMALS.read_text(encoding="utf-8"))
    if species not in table:
        raise SystemExit(f"no reference for {species!r}; have {sorted(table)}")
    row = dict(table[species])
    h = float(row.pop("total_m"))
    return {k: float(v) / h for k, v in row.items()}


def _segment(solid, sy):
    """Find belly, withers and the base of the head from each COURSE's shape.

    Area thresholds were not good enough: they clipped the top and bottom off the barrel and put the
    base of the head four courses above the withers, which would be a neck of four blocks. Spans and
    part-counts are what actually mark the joints:

      belly    the last course going up that still has the legs as separate PARTS
      withers  the first course above the belly whose width has collapsed to neck width
      head     the first course above that where the length along the body axis swells again
    """
    from mcbuild import morph
    parts, area, xext, zext = [], [], [], []
    for y in range(sy):
        m = solid[y]
        if not m.any():
            parts.append(0); area.append(0); xext.append(0); zext.append(0); continue
        _lab, sizes = morph.components(m[None, :, :], conn=6)
        parts.append(len(sizes))
        area.append(int(m.sum()))
        zs, xs = np.where(m)
        xext.append(int(xs.max() - xs.min() + 1))
        zext.append(int(zs.max() - zs.min() + 1))

    filled = [y for y in range(sy) if area[y]]
    lo, hi = filled[0], filled[-1]
    # belly: above the last course where the legs are still separate parts
    belly = max((y for y in range(lo, hi) if parts[y] > 1 and y < sy * 0.6), default=lo) + 1
    body_w = max(xext[belly:], default=1)
    # withers: where the section narrows to neck width and stays there
    narrow = 0.62 * body_w
    withers = next((y for y in range(belly + 1, hi) if xext[y] <= narrow), belly + 1)
    # head: above the neck's THINNEST point, the first swell in length along the body axis.
    # Searching up from the withers instead found the swell three courses along - but that is the
    # neck still being thick where it leaves the shoulder, and it reported a 3-block neck.
    # ...and not counting the crown: ossicones and ear tips are the thinnest sections on the whole
    # model, so an unrestricted search finds one of those and reports a 1-block head.
    crown = [y for y in range(withers, hi + 1) if area[y] and area[y] < 8]
    ceiling = min(crown) if crown else hi
    above = [y for y in range(withers, ceiling) if zext[y]]
    waist = min(above, key=lambda y: zext[y]) if above else withers
    head = next((y for y in range(waist, ceiling) if zext[y] > zext[waist] * 1.5), waist)
    return belly, withers, head, xext, zext, parts, area


def _leg_width(solid, y):
    """The width of ONE leg, not the span across all four - which is what the first version measured."""
    from mcbuild import morph
    m = solid[y]
    if not m.any():
        return 0
    lab, sizes = morph.components(m[None, :, :], conn=6)
    best = 0
    for i in range(1, len(sizes) + 1):
        zs, xs = np.where(lab[0] == i)
        if len(xs):
            best = max(best, int(xs.max() - xs.min() + 1))
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("design")
    ap.add_argument("--species", help="which row of animals.yaml to compare against; "
                                      "defaults to the design's own `kind`")
    ap.add_argument("--tol", type=float, default=0.20, help="fractional tolerance before flagging")
    a = ap.parse_args()

    s = scan.load(a.design)
    species = a.species or (getattr(s, "meta", None) or {}).get("kind") or "giraffe"
    REF = reference(species)
    ids = s.model.ids
    solid = ids > 0
    sy, sz, sx = ids.shape
    H = sy

    belly, withers, head, xext, zext, _parts, _area = _segment(solid, sy)
    # The neck/head boundary is genuinely hard to find by shape - and it is hard precisely BECAUSE
    # the model is smoothly blended, which is what we wanted. Where the generator recorded the
    # landmark, use it: guessing at a joint the design already knows the answer to is silly.
    land = getattr(s, "meta", None) or {}
    oy = (land.get("origin") or {}).get("y")
    if "neck_top_y" in land and oy is not None:
        head = int(round(float(land["neck_top_y"]) - oy))
    body = range(belly, withers + 1)
    got = {
        "withers height": withers / H,
        "leg (ground->belly)": belly / H,
        # belly-to-withers, a VERTICAL measure. The first version used the z-extent here, which is
        # the body's LENGTH, and so reported the barrel as 46% too deep when it was not.
        "body depth": (withers - belly) / H,
        "body length": max((zext[y] for y in body), default=0) / H,
        # median across the barrel, not max: the max catches the belly course where the
        # haunches are still spreading and reports the leg span as the body width
        "body width": float(np.median([xext[y] for y in body] or [0])) / H,
        "neck length": max(0, head - withers) / H,
        "head length": max((zext[y] for y in range(head, sy)), default=0) / H,
        "leg width": _leg_width(solid, max(1, belly // 2)) / H,
    }

    print(f"{a.design}: {int(solid.sum())} blocks, {H} courses tall, against a real {species}\n")
    print(f"{'measure':22s} {'built':>7s} {'real':>7s} {'blocks':>7s} {'want':>7s}   verdict")
    bad = []
    for k, ref in REF.items():
        mine = got[k]
        delta = (mine - ref) / ref if ref else 0
        want = ref * H
        if abs(delta) <= a.tol:
            verdict = "ok"
        else:
            verdict = f"{'TOO BIG' if delta > 0 else 'TOO SMALL'}  {delta:+.0%}"
            bad.append((k, delta, want))
        print(f"{k:22s} {mine:7.3f} {ref:7.3f} {mine*H:7.1f} {want:7.1f}   {verdict}")
    if bad:
        print("\nout of tolerance:")
        for k, d, want in sorted(bad, key=lambda t: -abs(t[1])):
            print(f"  {k:22s} {d:+.0%}  -> aim for about {want:.0f} blocks")


if __name__ == "__main__":
    main()
