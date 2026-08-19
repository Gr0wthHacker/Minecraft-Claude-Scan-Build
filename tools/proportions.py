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
    """Real-animal measurements as fractions of total height.

    The FAMILY table is authoritative where one exists: it is the same table the build was derived
    from, so measuring against it asks the only useful question - did the build come out as what it
    was asked to be. `animals.yaml` remains for species not yet given a family.
    """
    import yaml
    from mcbuild.gen import taxonomy
    fam = taxonomy.proportions(species)
    if fam:
        return fam
    table = yaml.safe_load(ANIMALS.read_text(encoding="utf-8"))
    if species not in table:
        raise SystemExit(f"no reference for {species!r}; have {sorted(table)}")
    row = dict(table[species])
    h = float(row.pop("total_m"))
    row.pop("poses", None)                              # behaviour weights live here too
    return {k: float(v) / h for k, v in row.items()}


def posed(ref: dict, pose: str) -> dict:
    """Reference proportions ADJUSTED for the stance, so a pose is not audited as a deformity.

    A sitting animal's visible leg really is short and its haunch really is bunched - measuring that
    against a standing reference reports correct work as broken, which is worse than not measuring.

    The adjustment uses the SAME multipliers the generator poses with, so the two cannot drift:

      leg        the belly line follows the LOWER of the two leg lengths
      withers    chest height plus any pitch, plus the body's own depth
      leg width  a folded limb bunches - `fold` widens it
      the rest   a pose does not change how long a body or a head is

    Everything is then renormalised by the POSED total height, because the fractions are of total
    height and the pose changes that too.
    """
    from mcbuild.gen.quadruped import POSES
    q = POSES.get(pose, {})
    fore, hind = float(q.get("fore", 1.0)), float(q.get("hind", 1.0))
    pitch, fold, drop = float(q.get("pitch", 0.0)), float(q.get("fold", 1.0)), float(q.get("drop", 0.0))
    leg, depth = ref["leg (ground->belly)"], ref["body depth"]
    out = dict(ref)
    out["leg (ground->belly)"] = leg * min(fore, hind)
    out["withers height"] = leg * fore + pitch * leg + depth
    out["leg width"] = ref["leg width"] * fold
    # the neck and head stack above the withers, shortened in height if the head is carried down
    above = max(0.12, (1.0 - ref["withers height"]) * (1.0 - 1.4 * drop))
    total = out["withers height"] + above
    return {k: v / total for k, v in out.items()}


# Measures whose VERTICAL extent a tilted barrel changes in ways this first-order model does not
# capture: once the body is pitched, "belly to withers" is measured through a slope, not a section.
# They get a looser tolerance under pitch rather than a wrong number stated confidently.
TILT_SENSITIVE = ("withers height", "body depth", "body width")


def tilt_slack(pose: str) -> float:
    from mcbuild.gen.quadruped import POSES
    q = POSES.get(pose, {})
    tilt = abs(float(q.get("pitch", 0.0))) + abs(1.0 - float(q.get("fore", 1.0))
                                                 - (1.0 - float(q.get("hind", 1.0))))
    return min(0.55, 1.6 * tilt)


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
        # THICK extent only. A cat's tail is 22 blocks long and one wide; counting it made the
        # barrel measure 48 blocks and the head 38. Only z-slices with real width count as body.
        per_z = np.bincount(zs, minlength=m.shape[0])
        thick = np.where(per_z >= max(2, per_z.max() * 0.3))[0]
        zext.append(int(thick.max() - thick.min() + 1) if len(thick) else 0)

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


def _neck_len(land, head, withers) -> float:
    """Along the neck's OWN axis, not the height it gains.

    A giraffe's neck is nearly vertical so the two agree; a jaguar's is nearly horizontal, and the
    height difference reported a 4-block neck on one twice that length."""
    a, b = land.get("shoulder_at"), land.get("neck_top_at")
    if a and b:
        return sum((float(p) - float(qq)) ** 2 for p, qq in zip(a, b)) ** 0.5
    return max(0, head - withers)


def _leg_probe(land, oy, belly) -> int:
    """Halfway up to the LOWEST body floor - the only band where nothing but legs exists.

    Probing at half the tallest leg put the sample inside a sitting animal's rump, where body and
    haunches are one mass, and reported an 11-block leg. Under the lowest floor there is nothing but
    limbs, whatever the pose."""
    if oy is not None and "rump_y" in land and "chest_y" in land:
        lowest = min(float(land["rump_y"]), float(land["chest_y"])) - oy
        return max(1, int(round(lowest / 2.0)))
    return belly // 2


def _along_extent(solid, land, part, H):
    """The real solid extent inside the window the generator recorded for a part.

    A window, not a value: the design says roughly where its head is, and this measures how much of
    it actually got built there. Without it, `head length` on a jaguar measured 38 blocks - the whole
    back - because the head is at body height and no height-based rule can separate them.
    """
    win = ((land.get("along") or {}).get(part))
    if not win:
        return (0, 0)
    facing = land.get("facing") or [0, 1]
    sy, sz, sx = solid.shape
    # `along` is measured from the feet; the feet sit at the model's own origin offset
    ys, zs, xs = np.where(solid)
    along = (xs - xs.mean()) * facing[0] + (zs - zs.mean()) * facing[1]
    lo, hi = min(win), max(win)
    mid = (lo + hi) / 2.0
    sel = (along >= (lo - mid)) & (along <= (hi - mid))
    if not sel.any():
        return (0, 0)
    a = along[sel]
    return (int(a.max() - a.min() + 1), int(sel.sum()))


def _barrel_width(solid, land, body) -> float:
    """The ribcage, sampled where no leg reaches it."""
    win = (land.get("along") or {}).get("body")
    facing = land.get("facing") or [0, 1]
    widths = []
    for y in body:
        m = solid[y] if y < solid.shape[0] else None
        if m is None or not m.any():
            continue
        zs, xs = np.where(m)
        if win:
            # keep only the middle third along the body axis - clear of both leg pairs
            axis = zs if abs(facing[1]) else xs
            lo, hi = axis.min(), axis.max()
            mid_lo, mid_hi = lo + (hi - lo) * 0.36, lo + (hi - lo) * 0.64
            sel = (axis >= mid_lo) & (axis <= mid_hi)
            if sel.any():
                xs = xs[sel]
        if len(xs):
            widths.append(int(xs.max() - xs.min() + 1))
    return float(np.median(widths)) if widths else 0.0


def _leg_width(solid, y):
    """The width of a STRAIGHT leg: the median of the separate limbs at this height, not the widest.

    Two traps, one per version. Taking the span across all four legs measured the stance, not a leg.
    Taking the widest component then measured a sitting animal's folded haunch - which is bunched by
    design - and reported a 13-block leg. The median across the limbs present is what a leg is."""
    from mcbuild import morph
    m = solid[y]
    if not m.any():
        return 0
    lab, sizes = morph.components(m[None, :, :], conn=6)
    widths = []
    for i in range(1, len(sizes) + 1):
        zs, xs = np.where(lab[0] == i)
        if len(xs):
            widths.append(int(xs.max() - xs.min() + 1))
    return int(np.median(widths)) if widths else 0


def measure(solid, land, sy) -> dict:
    """Every proportion, as a fraction of total height. Shared with tools/stance.py so the
    pose comparison and the audit can never drift apart.

    Height means ANATOMICAL height - feet to the top of the head mass - not the bounding box. A
    trunk, a set of ears or a pair of ossicones changes the box without changing the animal, and
    normalising by the box made every proportion read low on exactly those species. That was papered
    over with a per-family `crown_bias` multiplier, which was a fudge: it inflated the animal until
    the numbers came right. Measuring the same quantity the derivation uses needs no correction."""
    oy_ = (land.get("origin") or {}).get("y")
    if oy_ is not None and land.get("anat_top_y") is not None and land.get("feet"):
        H = max(4, int(round(float(land["anat_top_y"]) - float(land["feet"][1]))))
    else:
        H = sy
    belly, withers, head, xext, zext, _parts, _area = _segment(solid, sy)
    # The neck/head boundary is genuinely hard to find by shape - and it is hard precisely BECAUSE
    # the model is smoothly blended, which is what we wanted. Where the generator recorded the
    # landmark, use it: guessing at a joint the design already knows the answer to is silly.
    oy = (land.get("origin") or {}).get("y")
    # Landmarks ONLY where shape cannot tell. Belly and withers are found reliably from the
    # course profile, and they measure what was BUILT; the recorded values are what was DESIGNED,
    # which is a different question and under-reported the giraffe's barrel by a third.
    # Each joint from whichever source is actually authoritative for it:
    #   belly    the DESIGN knows exactly - it is where the legs stop (feet + leg length). Shape
    #            detection guesses it from part counts and misfires badly on a low-slung animal,
    #            where the barrel nearly touches the legs; on a jaguar it under-read the body depth
    #            by 88%.
    #   withers  must be MEASURED, since relax changes how deep the built barrel ends up.
    #   head     recorded, because on a cat head and body sit at the same height and no height rule
    #            can separate them.
    if oy is not None:
        if "belly_y" in land:
            belly = max(0, int(round(float(land["belly_y"]) - oy)))
            withers = max(withers, belly + 2)
        if "back_y" in land:
            # the greater of measured and designed: relax can deepen the barrel, and on a low animal
            # the shape rule under-reads it badly
            withers = max(withers, int(round(float(land["back_y"]) - oy)))
        if "neck_top_y" in land:
            head = int(round(float(land["neck_top_y"]) - oy))
    # clamp: a pitched pose can put the recorded back line above the model's own top course
    withers = min(max(withers, belly + 1), sy - 1)
    body = range(belly, withers + 1)
    got = {
        "withers height": withers / H,
        "leg (ground->belly)": belly / H,
        # belly-to-withers, a VERTICAL measure. The first version used the z-extent here, which is
        # the body's LENGTH, and so reported the barrel as 46% too deep when it was not.
        "body depth": (withers - belly) / H,
        "body length": _along_extent(solid, land, "body", H)[0] / H,
        # measured MID-BARREL, between the leg pairs. Every leg carries four courses up inside the
        # body as a haunch, so anywhere near a leg the "body" is really body-plus-shoulder: the
        # jaguar's ribcage is 8 wide and measured 15 everywhere the haunches reach.
        "body width": _barrel_width(solid, land, body) / H,
        "neck length": _neck_len(land, head, withers) / H,
        "head length": _along_extent(solid, land, "head", H)[0] / H,
        # measured halfway up the LONGEST leg - on a posed animal the short pair is folded and its
        # bunched haunch is not a leg width
        "leg width": _leg_width(solid, max(1, _leg_probe(land, oy, belly))) / H,
    }
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("design")
    ap.add_argument("--species", help="which row of animals.yaml to compare against; "
                                      "defaults to the design's own `kind`")
    ap.add_argument("--pose", help="stance to audit against; defaults to the design's own")
    ap.add_argument("--tol", type=float, default=0.20, help="fractional tolerance before flagging")
    a = ap.parse_args()

    s = scan.load(a.design)
    species = a.species or (getattr(s, "meta", None) or {}).get("kind") or "giraffe"
    pose = a.pose or (getattr(s, "meta", None) or {}).get("pose") or "standing"
    REF = posed(reference(species), pose)
    ids = s.model.ids
    solid = ids > 0
    sy, sz, sx = ids.shape
    H = sy

    got = measure(solid, getattr(s, 'meta', None) or {}, sy)

    print(f"{a.design}: {int(solid.sum())} blocks, {H} courses tall, against a real {species}\n")
    print(f"{'measure':22s} {'built':>7s} {'real':>7s} {'blocks':>7s} {'want':>7s}   verdict")
    bad = []
    slack = tilt_slack(pose)
    for k, ref in REF.items():
        mine = got[k]
        delta = (mine - ref) / ref if ref else 0
        want = ref * H
        tol = a.tol + (slack if k in TILT_SENSITIVE else 0.0)
        if abs(delta) <= tol:
            # `~` means it only passes because a pitched barrel widened the tolerance
            verdict = "ok~" if (abs(delta) > a.tol and k in TILT_SENSITIVE) else "ok"
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
