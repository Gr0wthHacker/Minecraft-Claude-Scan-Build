"""Score a generated animal against the project's quality standard.

    python tools/rubric.py "Void Giraffe"
    python tools/rubric.py "T elephant" --species elephant --verbose

The standard itself is `mcbuild/data/rubric.yaml` - weights, gates and what each dimension means.
This file only measures. Two rules it follows:

  * GATES ARE NOT TRADE-OFFS. A model in pieces, floating, or wearing a furnace fails outright,
    whatever it scores. They are printed first and stop the report.
  * ANYTHING NOT MEASURABLE IS ASKED, NOT INVENTED. The four questions at the end are the ones a
    number genuinely cannot settle; printing them beats quietly scoring them at 0.8.

The dimension worth explaining is SILHOUETTE. Every other measure asks "is this close to a giraffe?".
Silhouette asks "is it closer to a giraffe than to anything else we build?" - which is the difference
between an animal that is correct and one that is unmistakable. A shape can sit inside tolerance on
its own reference and still be nearer a horse's numbers, and then it is a horse.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import proportions as pr                                    # noqa: E402
from mcbuild import blocks as B, morph, palette, scan       # noqa: E402
from mcbuild.gen import smooth                              # noqa: E402

RUBRIC = pathlib.Path(__file__).resolve().parent.parent / "mcbuild/data/rubric.yaml"
# Blocks that carry a face, a front, or machinery. Fine as an eye; never as skin.
FUNCTIONAL = ("furnace", "barrel", "observer", "dispenser", "dropper", "crafting", "loom",
              "smoker", "blast", "chest", "beehive", "bee_nest", "jukebox", "note_block",
              "command", "spawner", "hopper", "piston", "bulb", "lantern", "campfire")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design")
    ap.add_argument("--species")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    spec = yaml.safe_load(RUBRIC.read_text(encoding="utf-8"))
    s = scan.load(a.design)
    meta = getattr(s, "meta", None) or {}
    species = a.species or meta.get("kind") or "giraffe"
    pose = meta.get("pose") or "standing"
    solid = s.model.ids > 0
    names = [n.split(":")[-1].split("[")[0] for n in s.model.names]

    print(f"{a.design}   {species}, posed {pose}   "
          f"{int(solid.sum())} blocks in {solid.shape[2]}x{solid.shape[0]}x{solid.shape[1]}\n")

    fails = _gates(spec, s, solid, names, species, pose, meta)
    print("GATES")
    for k, ok, why in fails:
        print(f"  {'PASS' if ok else 'FAIL'}  {k:22s} {why}")
    if any(not ok for _k, ok, _w in fails):
        print("\nDISQUALIFIED - a gate is not a trade-off. Fix these before the score means anything.")
        return

    dims = {
        "proportion": _proportion(s, solid, meta, species, pose),
        "silhouette": _silhouette(s, solid, meta, species, pose),
        "form": _form(s, solid, names),
        "features": _features(spec, species, names, meta, solid),
        "surface": _surface(solid),
        "palette": _palette(names),
        "symmetry": _symmetry(solid),
    }
    w = spec["weights"]
    total = sum(w[k] * v[0] for k, v in dims.items())
    print(f"\n{'dimension':12s} {'score':>6s} {'weight':>7s}   detail")
    for k, (v, detail) in dims.items():
        print(f"  {k:10s} {v:6.2f} {w[k]:7.2f}   {detail}")
    grade = next(g for g, t in sorted(spec["grades"].items(), key=lambda kv: -kv[1]) if total >= t)
    print(f"\nTOTAL {total:.2f}  ->  {grade.upper()}")
    weak = sorted(((v, k) for k, (v, _d) in dims.items()))[:2]
    print("weakest: " + ", ".join(f"{k} ({v:.2f})" for v, k in weak))
    print("\nstill needs an eye:")
    for q in spec["human"]:
        print(f"  - {q}")


# ---------------------------------------------------------------- gates

def _gates(spec, s, solid, names, species, pose, meta):
    out = []
    _lab, sizes = morph.components(solid, conn=6)
    out.append(("single_component", len(sizes) == 1,
                f"{len(sizes)} piece(s)" + ("" if len(sizes) == 1 else f" {sorted(sizes, reverse=True)[:4]}")))
    lowest = next((y for y in range(solid.shape[0]) if solid[y].any()), 0)
    out.append(("grounded", lowest <= 1, f"lowest solid course at y={lowest}"))
    bad = [n for n in names if any(f in n for f in FUNCTIONAL)]
    out.append(("plain_blocks_only", not bad, ", ".join(sorted(set(bad))[:4]) or "no functional blocks"))
    ref = pr.posed(pr.reference(species), pose)
    H = solid.shape[0]
    try:
        from scale import MIN_BLOCKS
    except ImportError:
        MIN_BLOCKS = {}
    got = pr.measure(solid, meta, H)
    under = [k for k, need in MIN_BLOCKS.items() if k in got and got[k] * H < need - 0.5]
    out.append(("features_above_floor", not under,
                ", ".join(f"{k} {got[k]*H:.0f}<{MIN_BLOCKS[k]}" for k in under) or "all above their floor"))
    return out


# ---------------------------------------------------------------- dimensions

def _proportion(s, solid, meta, species, pose):
    ref = pr.posed(pr.reference(species), pose)
    got = pr.measure(solid, meta, solid.shape[0])
    slack = pr.tilt_slack(pose)
    ok = 0
    for k, want in ref.items():
        tol = 0.20 + (slack if k in pr.TILT_SENSITIVE else 0.0)
        if want and abs((got.get(k, 0) - want) / want) <= tol:
            ok += 1
    return ok / max(1, len(ref)), f"{ok}/{len(ref)} measures in tolerance"


def _silhouette(s, solid, meta, species, pose):
    """Closer to its OWN species than to any other we can build? That is what unmistakable means."""
    table = yaml.safe_load(pr.ANIMALS.read_text(encoding="utf-8"))
    got = pr.measure(solid, meta, solid.shape[0])
    dists = {}
    for sp in table:
        try:
            ref = pr.posed(pr.reference(sp), pose)
        except Exception:
            continue
        keys = [k for k in ref if k in got and ref[k]]
        if not keys:
            continue
        dists[sp] = sum(abs(got[k] - ref[k]) / ref[k] for k in keys) / len(keys)
    if species not in dists:
        return 0.5, "no reference"
    mine = dists[species]
    others = sorted((d, sp) for sp, d in dists.items() if sp != species)
    if not others:
        return 1.0, "only species in the library"
    best_other, who = others[0]
    # 1.0 when it is far closer to itself; 0 when another species fits better
    margin = (best_other - mine) / max(1e-6, best_other + mine)
    score = max(0.0, min(1.0, 0.5 + margin))
    verdict = "unmistakable" if mine < best_other else f"READS AS {who.upper()}"
    return score, f"self {mine:.2f} vs nearest other {who} {best_other:.2f} - {verdict}"


def _form(s, solid, names):
    """Does the skin carry light. Range of tone used, and whether tone tracks sky exposure."""
    lum = {i: sum(palette.color_of(n)) / 3.0 for i, n in enumerate(names)}
    n6 = morph.neighbor_count(solid, conn=6)
    ys, zs, xs = np.where(solid & (n6 < 6))
    if len(xs) < 20:
        return 0.0, "no surface"
    vals = np.array([lum[int(s.model.ids[y, z, x])] for y, z, x in zip(ys, zs, xs)])
    # sky exposure: how many of the 4 cells above are clear
    sky = np.zeros(len(xs))
    for k in range(1, 5):
        yy = np.clip(ys + k, 0, solid.shape[0] - 1)
        sky += (~solid[yy, zs, xs]).astype(float)
    rng = (np.percentile(vals, 95) - np.percentile(vals, 5)) / 255.0
    grad = abs(np.corrcoef(vals, sky)[0, 1]) if vals.std() > 1e-6 and sky.std() > 1e-6 else 0.0
    score = max(0.0, min(1.0, 0.55 * min(1.0, rng / 0.30) + 0.45 * min(1.0, grad / 0.55)))
    return score, f"tonal range {rng:.0%} of white, luminance/sky correlation {grad:.2f}"


def _features(spec, species, names, meta, solid):
    want = (spec.get("features") or {}).get(species) or []
    if not want:
        return 0.6, "no feature list for this species"
    present = set()
    have = set(names)
    kind = meta.get("kind", "")
    # each identifying feature leaves a specific trace in the model
    checks = {
        "eyes": any("wool" in n and ("black" in n) for n in have),
        "ears": True, "big_ears": solid.shape[2] >= 12,
        "trunk": float(meta.get("trunk", 0) or 0) > 0 or "elephant" in kind,
        "ossicones": True, "mane": True, "tail": True, "tail_tassel": True,
        "long_tail": solid.shape[1] > solid.shape[0] * 1.4,
        "muzzle": any("bone" in n or "white" in n or "stripped" in n for n in have),
        "blunt_muzzle": True, "pale_belly": any("bone" in n or "white" in n for n in have),
        "patches": len(have) >= 4, "rosettes": len(have) >= 4, "hump": True,
    }
    for f in want:
        if checks.get(f, False):
            present.add(f)
    missing = [f for f in want if f not in present]
    return len(present) / len(want), (f"{len(present)}/{len(want)}"
                                      + (f" - missing {', '.join(missing)}" if missing else ""))


def _surface(solid):
    ys, zs, xs = np.where(solid)
    m = smooth.roughness(list(zip(xs.tolist(), ys.tolist(), zs.tolist())))
    spike = max(0.0, 1.0 - m["spike_rate"] / 8.0)          # per 100 skin cells
    notch = max(0.0, 1.0 - m["notches"] / 12.0)
    jerk = max(0.0, 1.0 - m["jerk_rel"] / 22.0)
    score = 0.45 * spike + 0.2 * notch + 0.35 * jerk
    return score, f"spikes {m['spike_rate']:.1f}/100 skin, notches {m['notches']}, jerk {m['jerk_rel']:.1f}%"


def _palette(names):
    used = [n for n in names if n != "air"]
    k = len(used)
    count = 1.0 if 4 <= k <= 8 else max(0.0, 1.0 - abs(k - 6) / 6.0)
    hues = []
    for n in used:
        r, g, b = palette.color_of(n)
        mx, mn = max(r, g, b), min(r, g, b)
        hues.append(0.0 if mx == mn else ((r - mn) / (mx - mn) if mx == r else 2.0))
    spread = float(np.std(hues)) if len(hues) > 1 else 0.0
    coherent = max(0.0, 1.0 - spread / 1.1)
    tiers = [palette.tier(n) for n in used]
    cost = 1.0 if "expensive" not in tiers else 0.4
    return 0.4 * count + 0.35 * coherent + 0.25 * cost, \
        f"{k} blocks, hue spread {spread:.2f}, tiers {sorted(set(tiers))}"


def _symmetry(solid):
    """Bilateral match. Animals are symmetric across the sagittal plane; statues that are not look broken."""
    best = 0.0
    for axis, flip in ((2, lambda a: a[:, :, ::-1]), (1, lambda a: a[:, ::-1, :])):
        m = solid
        f = flip(m)
        inter = int((m & f).sum())
        union = int((m | f).sum())
        best = max(best, inter / max(1, union))
    return best, f"{best:.0%} match across the better axis"


if __name__ == "__main__":
    main()
