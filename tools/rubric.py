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
import functools
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
        "silhouette": _silhouette(holder, solid, names, meta, species, pose),
        "form": _form(holder, solid, names),
        "features": _features(spec, species, names, meta, solid),
        "surface": _surface(solid),
        "roundness": _roundness(solid, meta, _occupancy(holder, solid, names)),
        "palette": _palette(names),
        "symmetry": _symmetry(solid, meta),
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
    # THE FLOOR FOLLOWS THE POSE. A sitting animal's belly is ON THE GROUND - that is what sitting
    # is - so measuring its leg clearance against a standing floor of 4 blocks failed the gate on
    # every sitting or couchant build ever made, including the one pose the ursid family likes best.
    # Every other measure here is pose-adjusted; this one was not. The floor is scaled by exactly
    # the ratio `proportions.posed` applies to the same measure, so the two cannot drift, and it
    # never scales below 1 - a feature still has to exist.
    try:
        std = pr.reference(species)
        adj = pr.posed(std, pose)
    except Exception:
        std, adj = {}, {}
    floors = {}
    for k, need in MIN_BLOCKS.items():
        r = (adj.get(k, 0) / std[k]) if std.get(k) else 1.0
        floors[k] = max(1.0, need * min(1.0, r))
    under = [k for k, need in floors.items() if k in got and got[k] * H < need - 0.5]
    out.append(("features_above_floor", not under,
                ", ".join(f"{k} {got[k]*H:.0f}<{floors[k]:.0f}" for k in under)
                or f"all above their floor (posed {pose})"))
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


def _silhouette(s, solid, names, meta, species, pose):
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

    # within the family: how distinct is this BUILD from its siblings' BUILDS
    sibs = [n for n, v in taxonomy.species().items()
            if v.get("family") == mine_fam and n != species]
    sp_score, sp_detail = _within_family(solid, names, species, sibs)
    detail = (f"family {mine_fam} {d_self:.2f} vs nearest {who} {d_other:.2f}; {sp_detail}")
    verdict = "" if d_self < d_other else f"  READS AS {who.upper()}"
    return 0.65 * fam_score + 0.35 * sp_score, detail + verdict


def _profile(solid, bins=24, span=2):
    """A build's side silhouette, normalised by HEIGHT so two sizes compare but two shapes do not.

    Down the WIDTH axis, because that is the view a statue is seen from and the view the family
    proportions are stated in.

    Scaled by height ALONE and pasted into a fixed canvas `span` times as wide as it is tall, so a
    22-block leopard and a 32-block lion are comparable without either being rescaled in the world -
    and a long animal still occupies more of the canvas than a short one. Fitting the bounding box
    to the grid instead, which is what this did first, divides the length out as well as the height:
    every solid box becomes the same full rectangle, and a jaguar twice as long as it is tall
    measures identical to one as long as it is tall. The test caught it; the animals hid it, because
    no animal is a solid box.
    """
    side = solid.any(axis=2)                              # solid is [y, z, x] -> (y, z)
    ys, zs = np.nonzero(side)
    out = np.zeros((bins, bins * span))
    if not len(ys):
        return out
    side = side[ys.min():ys.max() + 1, zs.min():zs.max() + 1]
    h, d = side.shape
    w = min(bins * span, max(1, int(round(d * bins / h))))     # height -> bins, length to match
    yi = (np.arange(bins) * h // bins).clip(0, h - 1)
    zi = (np.arange(w) * d // w).clip(0, d - 1)
    out[:, :w] = side[np.ix_(yi, zi)].astype(float)            # anchored at the tail end
    return out


def _within_family(solid, names, species, sibs):
    """How different is this STATUE from its siblings' statues?

    This used to compare the two species' YAML entries - the set of block names and feature names
    written in `species.yaml` - and never looked at the model at all. It was a fake check of exactly
    the kind this rubric already got caught on once: bear and polar_bear scored "86% distinct"
    because their coat blocks are spelled differently, while the built silhouettes were 0.016 apart.
    Adding one key to a config raised the score without changing a single block.

    So it compares BUILDS, and it will only compare builds it can actually find. A sibling that has
    never been generated is reported as uncompared rather than silently scored as a win - the whole
    failure being guarded against is a number that looks like proof and is not.
    """
    if not sibs:
        return 1.0, "only member of its family"
    mine_shape = _profile(solid)
    mine_coat = _palette_mix(names)
    worst, who, seen = None, None, 0
    for n in sibs:
        got = _sibling_build(n)
        if got is None:
            continue
        seen += 1
        # shape: 1 - IoU over the normalised side silhouette
        other_shape, other_names = got
        inter = np.minimum(mine_shape, other_shape).sum()
        union = np.maximum(mine_shape, other_shape).sum()
        shape_d = 1.0 - (inter / union if union else 1.0)
        # coat: total-variation distance between the two block mixes
        coat = _palette_mix(other_names)
        keys = set(mine_coat) | set(coat)
        coat_d = 0.5 * sum(abs(mine_coat.get(k, 0.0) - coat.get(k, 0.0)) for k in keys)
        # A species is distinct if EITHER separates it - a lion and a jaguar are MEANT to be the
        # same shape, so demanding shape would penalise the family table for working. But the two
        # are reported separately, because an animal carried entirely by its paint is a fact worth
        # seeing rather than one worth averaging away.
        if worst is None or max(shape_d, coat_d) < max(worst):
            worst, who = (shape_d, coat_d), n
    if not seen:
        return 0.5, (f"NO sibling build found for {', '.join(sibs)} - generate them to measure "
                     f"within-family distinction; scored neutral, not passed")
    shape_d, coat_d = worst
    # 0.35 of separation from the nearest sibling is treated as fully distinct: two cats SHOULD
    # share most of their outline, and demanding more would penalise the family table working.
    sp = min(1.0, max(shape_d, coat_d) / 0.35)
    missing = len(sibs) - seen
    note = f", {missing} not built" if missing else ""
    flag = "  SHAPE CARRIES NOTHING" if shape_d < 0.08 else ""
    return sp, (f"vs built {who}: shape {shape_d:.2f}, coat {coat_d:.2f} "
                f"({seen} sibling build(s){note}){flag}")


def _palette_mix(names):
    """Block name -> fraction of the skin, ignoring air."""
    total = sum(1 for n in names if n != "air")
    if not total:
        return {}
    out = {}
    for n in names:
        if n == "air":
            continue
        out[n] = out.get(n, 0.0) + 1.0 / total
    return out


def _sibling_build(name):
    """The newest build of a species, as (silhouette, block names), or None if it has never run."""
    return _builds_by_species().get(name)


@functools.lru_cache(maxsize=1)
def _builds_by_species():
    """{species: (silhouette, block names)} for the newest build of each, scanned ONCE.

    Looks wherever designs land - `out/` and the shipped schematics folder - and matches on the
    sidecar's own recorded `kind`, so a design's file name does not have to encode its species.

    Cached for the process because it is called from inside `score`, and `tools/refine.py` calls
    `score` once per grid variant. Without this, a 54-variant sweep re-parses every litematic in
    `out/` a hundred-odd times - the NBT parse dominated the sweep and the whole test suite slowed
    by an order of magnitude. Nothing regenerates a SIBLING mid-sweep, so a per-process snapshot is
    the right granularity; `_builds_by_species.cache_clear()` if that ever stops being true.
    """
    out, when = {}, {}
    for d in _design_dirs():
        if not d.is_dir():
            continue
        for f in d.glob("*.litematic"):
            try:
                mt = f.stat().st_mtime
                s = scan.load(str(f))
                kind = (getattr(s, "meta", None) or {}).get("kind")
                if not kind or mt <= when.get(kind, -1.0):
                    continue
                out[kind] = (_profile(s.model.ids > 0),
                             [n.split(":")[-1].split("[")[0] for n in s.model.names])
                when[kind] = mt
            except Exception:
                continue
    return out


@functools.lru_cache(maxsize=1)
def _design_dirs():
    dirs = [pathlib.Path("out")]
    try:
        from mcbuild import profile
        p = profile.load()
        for k in ("schematics", "schematics_dir"):
            v = (p or {}).get(k) if isinstance(p, dict) else getattr(p, k, None)
            if v:
                dirs.append(pathlib.Path(v))
    except Exception:
        pass
    return tuple(dirs)


def _form(s, solid, names):
    """Does the skin carry light: how much tone it uses, and whether tone follows exposure.

    The gradient is measured on BINNED MEANS rather than on raw cells. A raw correlation is destroyed
    by any coat pattern - a giraffe's patches swing luminance far harder than its shading does, so a
    patterned animal scored near zero whether or not it was shaded, and the metric was really
    detecting "is it patterned". Averaging within each exposure bin cancels the pattern, because a
    patch is equally likely at any exposure, and leaves the trend that shading actually creates.
    """
    lum = {i: sum(palette.color_of(n)) / 3.0 for i, n in enumerate(names)}
    n6 = morph.neighbor_count(solid, conn=6)
    ys, zs, xs = np.where(solid & (n6 < 6))
    if len(xs) < 20:
        return 0.0, "no surface"
    ids = getattr(getattr(s, "model", None), "ids", None)
    if ids is None:
        # form is a question about COLOUR on the skin, and without the block ids there is no
        # colour to ask about. Say so rather than crashing or inventing a number - `score` used
        # to advertise `model` as optional and then raise AttributeError right here.
        return 0.0, "no block data - form cannot be measured without the model"
    vals = np.array([lum[int(ids[y, z, x])] for y, z, x in zip(ys, zs, xs)])
    sky = np.zeros(len(xs))
    for k in range(1, 5):
        yy = np.clip(ys + k, 0, solid.shape[0] - 1)
        sky += (~solid[yy, zs, xs]).astype(float)
    rng = (np.percentile(vals, 95) - np.percentile(vals, 5)) / 255.0
    means = [vals[sky == b].mean() for b in range(5) if (sky == b).sum() >= 8]
    if len(means) < 3:
        grad = 0.0
    else:
        m = np.array(means)
        # monotone rise from buried to open, scaled by how much of the tonal range it spans
        steps = np.diff(m)
        mono = float((steps > 0).sum()) / max(1, len(steps))
        span = (m.max() - m.min()) / 255.0
        grad = mono * min(1.0, span / 0.12)
    score = max(0.0, min(1.0, 0.45 * min(1.0, rng / 0.30) + 0.55 * grad))
    return score, f"tonal range {rng:.0%}, shading trend {grad:.2f} over {len(means)} exposure bins"


# Corner fill of known sections, so the band below is calibrated rather than chosen: a filled
# ellipse reads 0.06, exponent 3 reads 0.31, exponent 4 reads 0.56, exponent 8 reads 0.88, a solid
# rectangle 1.00. A real torso in side view is fuller than an ellipse, so ROUND is set at 0.35 -
# about a superellipse of exponent 3 - rather than at the ellipse itself.
ROUND, BRICK = 0.35, 0.90


def _occupancy(s, solid, names):
    """Per-cell FILL FRACTION, so a half block counts as half.

    Every other dimension works off `ids > 0`, where a slab is exactly as solid as a cube. Without
    this, adding half-block surfacing would smooth the model visibly and score precisely zero.
    """
    from mcbuild.gen import shell
    ids = getattr(getattr(s, "model", None), "ids", None)
    if ids is None or not names:
        return None
    frac = np.array([shell.volume_fraction(n) for n in names], float)
    if (frac >= 1.0).all():
        return None                                   # no partial blocks: the boolean is the truth
    return np.where(solid, frac[ids], 0.0)


def _roundness(solid, meta, occ=None):
    """Is the BARREL a body or a brick?

    `form` cannot answer this. It measures tone - range, and whether luminance follows sky exposure -
    and a rectangular prism with a good shading ramp scores well on all of it. Every animal in the
    set passed `form` while its barrel was a flat-topped, square-ended box.

    Measured on the barrel ALONE, between the recorded belly line and the recorded body window.
    Measuring the whole model instead rewards an animal for the gaps between its legs and for having
    a long tail, which is how the first version of this ranked a leggy cat 'round' and a squat
    capybara 'square' when their barrels were equally brick-shaped.
    """
    need = ("origin", "feet", "along", "belly_y")
    if not all(k in (meta or {}) for k in need):
        return 0.5, "no landmarks recorded - roundness needs the barrel's own extent"
    o = meta["origin"]
    f = meta.get("facing") or [0, 1]
    lo, hi = meta["along"]["body"]
    belly = int(meta["belly_y"]) - o["y"]
    sy, sz, sx = solid.shape
    vol = solid.astype(float) if occ is None else occ
    if f[1]:
        a0, a1 = meta["feet"][2] - o["z"] + lo, meta["feet"][2] - o["z"] + hi
        side = vol[max(0, belly):, max(0, a0):min(sz, a1 + 1), :].max(axis=2)
    else:
        a0, a1 = meta["feet"][0] - o["x"] + lo, meta["feet"][0] - o["x"] + hi
        side = vol[max(0, belly):, :, max(0, a0):min(sx, a1 + 1)].max(axis=1)
    ys, zs = np.nonzero(side)
    if len(ys) < 8:
        return 0.5, "barrel too small to measure"
    sub = side[ys.min():ys.max() + 1, zs.min():zs.max() + 1]
    h, d = sub.shape
    k = max(1, min(h, d) // 3)
    corner = float(np.mean([c.mean() for c in
                            (sub[:k, :k], sub[:k, -k:], sub[-k:, :k], sub[-k:, -k:])]))
    score = max(0.0, min(1.0, (BRICK - corner) / (BRICK - ROUND)))
    like = ("an ellipse" if corner < 0.15 else "a superellipse n~3" if corner < 0.40 else
            "a superellipse n~4" if corner < 0.65 else "a BRICK")
    return score, f"barrel corner fill {corner:.2f} - {like}"


def _features(spec, species, names, meta, solid):
    """Verified from what the generator RECORDED emitting, not asserted.

    The previous version hardcoded seven of its fourteen checks to True - ears, ossicones, mane,
    tail, tassel, blunt muzzle, hump - so a feature that relax had shaved off still scored full
    marks, and 15% of the rubric's weight was noise. `features_built` counts cells at the moment of
    emission, and each feature has a size below which it exists but cannot be seen.
    """
    from mcbuild.gen import taxonomy
    want = taxonomy.required_features(species) or (spec.get("features") or {}).get(species) or []
    if not want:
        return 0.6, "no feature list for this species"
    built = meta.get("features_built") or {}
    if not built:
        return 0.5, "generator recorded no features (rebuild to populate)"
    coat_blocks = len({n for n in names if n != "air"})
    # (which recorded group backs it, how many cells it needs to be legible)
    NEED = {
        "eyes": ("eyes", 2), "ears": ("crown", 4), "big_ears": ("crown", 16),
        "ossicones": ("crown", 8), "mane": ("mane", 4), "tail": ("tail", 4),
        "tail_tassel": ("tail", 8), "long_tail": ("tail", 12), "trunk": ("trunk", 12),
        "muzzle": ("face", 3), "blunt_muzzle": ("face", 3), "pale_belly": ("face", 3),
    }
    present, missing = 0, []
    for f in want:
        if f in ("patches", "rosettes"):
            ok = coat_blocks >= 3
        else:
            key, need = NEED.get(f, (f, 1))
            ok = built.get(key, 0) >= need
        if ok:
            present += 1
        else:
            got = coat_blocks if f in ("patches", "rosettes") else built.get(NEED.get(f, (f, 1))[0], 0)
            missing.append(f"{f}({got})")
    return present / len(want), (f"{present}/{len(want)}"
                                 + (f" - too small or absent: {', '.join(missing)}" if missing else ""))


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
    # COUNT COLOURS, NOT NAMES. A palette is a set of colours; how many SHAPES each colour comes in
    # is a different question and not this one. Counting names meant that surfacing a back with
    # `oak_slab` - the same colour as the `oak_log` beside it, in half the height - registered as
    # palette bloat and cost more than the smoothing gained. Colours are binned rather than compared
    # exactly, so two near-identical browns do not count twice either.
    seen = {}
    for n in used:
        seen.setdefault(tuple(c // 16 for c in palette.color_of(n)), n)
    k = len(seen)
    count = 1.0 if 4 <= k <= 8 else max(0.0, 1.0 - abs(k - 6) / 6.0)
    # Real hue, on the colour circle, weighted by how saturated the block is. The first version
    # used a crude proxy that returned 2.0 whenever green or blue was the max channel, so a set of
    # pure greys scored a hue spread of 1.00 - it was measuring which channel won a tie.
    import colorsys
    hs, ws = [], []
    for n in seen.values():
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
        f"{k} colours in {len(used)} blocks, hue spread {spread:.2f}, tiers {sorted(set(tiers))}"


def _symmetry(solid, meta=None):
    """Bilateral match across the SAGITTAL plane - the one the facing defines.

    Taking the best of both axes was wrong: for an animal facing +z, mirroring in z compares its head
    with its tail, and a shape that happened to score well there would have passed on a symmetry it
    does not possess. The heading is recorded; use it."""
    facing = ((meta or {}).get("facing")) or [0, 1]
    across_x = abs(facing[1]) >= abs(facing[0])          # facing along z -> mirror in x
    f = solid[:, :, ::-1] if across_x else solid[:, ::-1, :]
    inter, union = int((solid & f).sum()), int((solid | f).sum())
    v = inter / max(1, union)
    # Asymmetry that was ASKED FOR is not a defect. A turned head and an advanced leg are what stop a
    # statue looking planted, and penalising them would make the rubric argue for a worse animal.
    asym = (meta or {}).get("asymmetry") or {}
    allow = 0.02 * (abs(int(asym.get("leg_phase", 0))) + abs(int(asym.get("head_turn", 0))))
    note = f" (+{allow:.0%} allowed for deliberate asymmetry)" if allow else ""
    return min(1.0, v + allow), f"{v:.0%} across the sagittal plane, facing {facing}{note}"


if __name__ == "__main__":
    main()
