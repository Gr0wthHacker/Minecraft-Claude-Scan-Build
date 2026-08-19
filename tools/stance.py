"""Which pose suits this animal, on this spot, seen from there.

    python tools/stance.py configs/jaguar.yaml --from -24206 150 30010

Stance is most of what makes a statue read as an animal rather than a specimen on a plinth, and the
right one is not a matter of taste alone - three things about it are measurable, and they disagree
often enough to be worth checking:

  BEHAVIOUR   what the species actually does. A giraffe sitting is not a stylistic choice, it is
              wrong: they sleep standing and go down only when sick or calving. A cat spends most of
              its life not standing, so a standing jaguar is the odd one. From `animals.yaml`.
  SITE        what the ground can hold. Every pose is BUILT and measured, then its real footprint is
              tested against the relief under it. A lying animal is long and needs flat ground; a
              sitting one is compact and tolerates a slope.
  LEGIBILITY  what survives the viewing distance. Silhouette height falls away with a low pose, and
              past about 30 blocks a couchant animal is a lump. Standing keeps its outline.

The score is a weighted sum, and the reasons are printed alongside so a call can be argued with.
It recommends; the choice stays yours.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys

import numpy as np
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcbuild import scan                                    # noqa: E402
from mcbuild.gen.quadruped import POSES                     # noqa: E402
from mcbuild.pipeline import Settings, run_config           # noqa: E402

ANIMALS = pathlib.Path(__file__).resolve().parent.parent / "mcbuild/data/animals.yaml"
WEIGHTS = {"behaviour": 0.45, "site": 0.30, "legibility": 0.25}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--from", dest="eye", nargs=3, type=int, metavar=("X", "Y", "Z"),
                    help="the viewpoint the statue is composed for")
    a = ap.parse_args()

    cfg = yaml.safe_load(pathlib.Path(a.config).read_text(encoding="utf-8"))
    species = (cfg.get("params") or {}).get("profile") or "giraffe"
    feet = (cfg.get("params") or {}).get("feet")
    table = yaml.safe_load(ANIMALS.read_text(encoding="utf-8"))
    natural = (table.get(species) or {}).get("poses") or {}
    if not natural:
        print(f"no `poses:` for {species} in animals.yaml - behaviour will not be scored")

    eye = a.eye or (cfg.get("params") or {}).get("look_at")
    dist = math.dist(feet, eye) if (feet and eye) else None
    under = (cfg.get("params") or {}).get("under")
    ctx = scan.load(under) if under else None

    print(f"{species} at {feet}, viewed from {eye}"
          + (f" ({dist:.0f} blocks away)" if dist else "") + "\n")
    rows = []
    for pose in sorted(POSES):
        try:
            m, _r = run_config(a.config, settings=Settings(out_dir="out/_stance"),
                               overrides={"params.pose": pose}, render_sheet=False, verbose=False)
        except Exception as exc:
            print(f"  {pose:10s} FAILED {type(exc).__name__}")
            continue
        solid = m.solid()
        sy, sz, sx = solid.shape
        b = _behaviour(natural, pose)
        s_site, relief = _site(ctx, feet, m)
        legible = _legibility(sy, dist)
        score = WEIGHTS["behaviour"] * b + WEIGHTS["site"] * s_site + WEIGHTS["legibility"] * legible
        rows.append((score, pose, b, s_site, legible, sx, sy, sz, relief, int(solid.sum())))

    print(f"{'pose':11s} {'score':>6s} {'behav':>6s} {'site':>5s} {'legib':>6s} "
          f"{'footprint':>11s} {'tall':>5s} {'relief':>7s} {'blocks':>7s}")
    for r in sorted(rows, reverse=True):
        score, pose, b, ss, lg, sx, sy, sz, relief, n = r
        print(f"{pose:11s} {score:6.2f} {b:6.2f} {ss:5.2f} {lg:6.2f} "
              f"{sx:4d}x{sz:<6d} {sy:5d} {relief:7.1f} {n:7d}")
    if rows:
        best = max(rows)
        print(f"\nrecommend: {best[1]}")
        for line in _why(best, natural, dist):
            print(f"  - {line}")


def _behaviour(natural: dict, pose: str) -> float:
    """How much time the species really spends like this. Zero means do not build it."""
    return float(natural.get(pose, 0.5))


def _site(ctx, feet, model) -> tuple[float, float]:
    """Can the ground hold what actually TOUCHES it. Returns (score, relief in blocks under it).

    The footprint is taken from the statue's lowest courses, not its bounding box. A jaguar's box is
    51 long because of the tail - which floats - so measuring under the box sampled terrain 25 blocks
    behind the animal, ran off the edge of the isle, and scored every pose a flat zero.

    A long low pose still needs flatter ground than a compact one: it meets the terrain along its
    whole belly, so a ridge under the middle either floats it or buries it."""
    if ctx is None or not feet:
        return 0.7, 0.0
    # ONLY the lowest course, and only its biggest clusters. A tail tip that happens to curve down
    # near the ground is not a foot, and counting it stretched the sampled footprint 20 blocks behind
    # the animal, off the edge of the isle, where the relief is a cliff - every pose scored zero.
    from mcbuild import morph
    ms = model.solid()
    base = None
    for y in range(ms.shape[0]):
        if ms[y].any():
            base = ms[y]
            break
    if base is None:
        return 0.5, 0.0
    lab, sizes = morph.components(base[None, :, :], conn=6)
    keep = {i for i, n in enumerate(sizes, 1) if n >= max(2, max(sizes) * 0.25)}
    zs, xs = np.where(np.isin(lab[0], list(keep)))
    pads = {(int(x), int(z)) for x, z in zip(xs.tolist(), zs.tolist())}
    if not pads:
        return 0.5, 0.0
    px = [c[0] for c in pads]
    pz = [c[1] for c in pads]
    span = max(1.0, ((max(px) - min(px) + 1) * (max(pz) - min(pz) + 1)) ** 0.5)
    ids = ctx.model.ids
    names = [n.split(":")[-1].split("[")[0] for n in ctx.model.names]
    airy = {i for i, n in enumerate(names) if n in ("air", "cave_air", "void_air")}
    ox, oy, oz = ctx.origin
    my, mz, mx = ids.shape
    solid = ~np.isin(ids, list(airy))
    cx, cz = (min(px) + max(px)) // 2, (min(pz) + max(pz)) // 2
    fx, _fy, fz = feet
    heights = []
    for (ax, az) in pads:
        x, z = fx + (ax - cx) - ox, fz + (az - cz) - oz
        if not (0 <= x < mx and 0 <= z < mz):
            continue
        col = np.where(solid[:, z, x])[0]
        if len(col):
            heights.append(int(col.max()))
    if not heights:
        return 0.0, 99.0
    relief = float(np.percentile(heights, 90) - np.percentile(heights, 10))
    tol = 2.0 + 6.0 / max(1.0, span / 6.0)              # longer footprint, less forgiving
    return max(0.0, min(1.0, 1.0 - relief / max(1.0, tol))), relief


def _legibility(height: int, dist: float | None) -> float:
    """Does the silhouette survive the distance it is seen from.

    Apparent size falls with distance, and a low pose starts with less to lose - past ~30 blocks a
    couchant animal is a lump on the ground, whatever else it has going for it."""
    if not dist:
        return min(1.0, height / 30.0)
    apparent = height / max(1.0, dist)
    return max(0.0, min(1.0, apparent / 0.55))


def _why(best, natural, dist) -> list:
    score, pose, b, ss, lg, sx, sy, sz, relief, n = best
    out = []
    if b >= 0.85:
        out.append(f"the species really does this - behaviour {b:.2f}")
    elif b <= 0.2:
        out.append(f"WARNING: rare or unnatural for this animal ({b:.2f}) - override deliberately")
    out.append(f"footprint {sx}x{sz} over ground with {relief:.1f} blocks of relief (site {ss:.2f})")
    if dist:
        out.append(f"{sy} blocks tall at {dist:.0f} away - legibility {lg:.2f}"
                   + ("; a lower pose would be lost at this range" if lg < 0.5 else ""))
    weak = [k for k, v in (("behaviour", b), ("site", ss), ("legibility", lg)) if v < 0.45]
    if weak:
        out.append("weakest on: " + ", ".join(weak))
    return out


if __name__ == "__main__":
    main()
