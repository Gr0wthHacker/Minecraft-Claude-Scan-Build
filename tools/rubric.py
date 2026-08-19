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


def score(solid, names, meta, species, pose, model=None, spec=None):
    """Every dimension plus the weighted total. Shared with tools/refine.py.

    Exposed because optimising a single dimension is actively harmful: sweeping the smoothing on its
    own made the bear 0.73 on surface and 0.50 on proportion, because smoothing rewards thickening -
    it inflated the animal until it measured as an elephant. Anything that tunes must tune the total.
    """
    spec = spec or yaml.safe_load(RUBRIC.read_text(encoding="utf-8"))
    class _M:                                            # `_form` only needs .model.ids
        pass
    holder = model
    if holder is None:
        holder = _M()
        holder.model = _M()
    dims = {
        "proportion": _proportion(holder, solid, meta, species, pose),
        "silhouette": _silhouette(holder, solid, meta, species, pose),
        "form": _form(holder, solid, names),
        "features": _features(spec, species, names, meta, solid),
        "surface": _surface(solid),
        "palette": _palette(names),
        "symmetry": _symmetry(solid),
    }
    w = spec["weights"]
    return sum(w[k] * v[0] for k, v in dims.items()), dims


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

    total, dims = score(solid, names, meta, species, pose, model=s, spec=spec)
    w = spec["weights"]
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
    """Two levels, because identity works at two levels.

    FAMILY: is the shape unmistakably a cat rather than a bear? This is a proportion question and the
    family table answers it - every member of a family shares it, which is what stops a bear drifting
    into cat numbers when it is tuned on its own.

    SPECIES: within a family, proportion says NOTHING - a lion, a leopard and a jaguar are the same
    animal in shape, and the first version of this test duly scored them 0.50 for being identical to
    each other. That was the metric asking the wrong question. Inside a family, species are separated
    by COAT and FEATURES, so that is what gets measured here.
    """
    from mcbuild.gen import taxonomy
    got = pr.measure(solid, meta, solid.shape[0])
    mine_fam = taxonomy.family_of(species)
    fams = taxonomy.families()
    if not mine_fam or mine_fam not in fams:
        return 0.5, "no family"

    def dist(table):
        keys = [k for k in table if k in got and table[k]]
        return sum(abs(got[k] - table[k]) / table[k] for k in keys) / max(1, len(keys))

    d_self = dist(fams[mine_fam]["proportions"])
    others = sorted((dist(f["proportions"]), n) for n, f in fams.items() if n != mine_fam)
    if not others:
        return 1.0, "only family"
    d_other, who = others[0]
    margin = (d_other - d_self) / max(1e-6, d_other + d_self)
    fam_score = max(0.0, min(1.0, 0.5 + margin))

    # within the family: how distinct is this species' dressing from its siblings'
    sibs = [n for n, v in taxonomy.species().items()
            if v.get("family") == mine_fam and n != species]
    me = taxonomy.species().get(species) or {}
    if sibs:
        def dressing(d):
            # coat values include lists (a shading ramp), so flatten before making a set
            out = set()
            for v in (d.get("coat") or {}).values():
                out |= set(v) if isinstance(v, list) else {str(v)}
            return out | set(d.get("features") or [])
        mine_coat = dressing(me)
        best = 0.0
        for n in sibs:
            o = taxonomy.species()[n]
            oc = dressing(o)
            shared = len(mine_coat & oc) / max(1, len(mine_coat | oc))
            best = max(best, shared)
        sp_score = 1.0 - best
        detail = (f"family {mine_fam} {d_self:.2f} vs nearest {who} {d_other:.2f}; "
                  f"within family {sp_score:.0%} distinct from {len(sibs)} sibling(s)")
    else:
        sp_score, detail = 1.0, f"family {mine_fam} {d_self:.2f} vs nearest {who} {d_other:.2f}; only member"
    verdict = "" if d_self < d_other else f"  READS AS {who.upper()}"
    return 0.65 * fam_score + 0.35 * sp_score, detail + verdict


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
    from mcbuild.gen import taxonomy
    want = taxonomy.required_features(species) or (spec.get("features") or {}).get(species) or []
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
    # Real hue, on the colour circle, weighted by how saturated the block is. The first version
    # used a crude proxy that returned 2.0 whenever green or blue was the max channel, so a set of
    # pure greys scored a hue spread of 1.00 - it was measuring which channel won a tie.
    import colorsys
    hs, ws = [], []
    for n in used:
        r, g, b = (c / 255.0 for c in palette.color_of(n))
        h, _l, sat = colorsys.rgb_to_hls(r, g, b)
        hs.append(h * 2 * np.pi)
        ws.append(sat)                                   # grey has no hue worth counting
    if sum(ws) < 1e-6:
        coherent = 1.0                                   # a monochrome palette is perfectly coherent
    else:
        cx = float(np.average(np.cos(hs), weights=ws))
        cy = float(np.average(np.sin(hs), weights=ws))
        coherent = float(np.hypot(cx, cy))               # 1 = one hue, 0 = scattered round the wheel
    spread = 1.0 - coherent
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
