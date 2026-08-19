"""How big does this animal have to BE before it can look right?
    python tools/scale.py jaguar
    python tools/scale.py --all
    python tools/scale.py giraffe --target 0.9 --pose standing
There is a hard floor under every statue and it is not a matter of taste. Each feature needs a
minimum number of BLOCKS before it reads as itself - a leg thinner than 3 is a line, a head shorter
than 5 cannot carry a muzzle and an eye. And each feature is a fixed FRACTION of the animal's height.
Divide the one by the other and you get the height below which that feature cannot be built:
    minimum height  =  min_blocks(feature) / reference_fraction(feature)
Take the largest such height over all features and you have the animal's critical size. It explains
why a giraffe has to be enormous and a bee does not: a giraffe's leg is 5% of its height, so a
3-block leg forces 59 blocks of animal. A jaguar's leg is 13% of its height, so the same 3-block leg
only forces 23. The animal with the finest features relative to its size is the one that must be big.
`--target` asks for a height at which some FRACTION of features clear their floor with margin, rather
than the height at which the worst one barely does.
"""
from __future__ import annotations
import argparse
import pathlib
import sys
import yaml
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from proportions import ANIMALS, posed, reference          # noqa: E402
# The smallest block count at which each feature still reads as itself. These are properties of
# VOXELS, not of any animal - which is why one table serves every species.
MIN_BLOCKS = {
    # 1 is a line and 2 has no centre; 3 is the first width that reads as a round limb
    "leg width": 3,
    # under 5 there is no room for a muzzle, an eye and a brow - the head becomes a knob
    "head length": 5,
    # a barrel shallower than this cannot show a back line separate from a belly line
    "body depth": 4,
    # below 6 the body has no length to carry a shoulder and a haunch as different things
    "body length": 6,
    # 3 lets a body be rounded across; 2 is a slab
    "body width": 3,
    # a neck needs to be visibly longer than it is wide, or it is just a join
    "neck length": 3,
    # the legs must be long enough to show daylight under the animal
    "leg (ground->belly)": 4,
    "withers height": 6,
}
# Building a feature at exactly its floor is not the same as building it well. This is the margin at
# which a feature stops being a compromise.
COMFORT = 1.45
def floors(species: str, pose: str = "standing") -> dict:
    """{feature: minimum total height that lets this feature exist}, largest last."""
    ref = posed(reference(species), pose)
    out = {}
    for k, need in MIN_BLOCKS.items():
        frac = ref.get(k)
        if frac:
            out[k] = need / frac
    return dict(sorted(out.items(), key=lambda kv: kv[1]))
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("species", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--pose", default="standing")
    ap.add_argument("--target", type=float, default=0.80,
                    help="share of features that must clear their floor with margin (default 0.80)")
    ap.add_argument("--measure", metavar="CONFIG",
                    help="BUILD the animal at a range of scales and report the real score curve")
    ap.add_argument("--scales", default="0.4,0.55,0.7,0.85,1.0,1.25,1.6")
    a = ap.parse_args()

    if a.measure:
        return _measure(a)
    table = yaml.safe_load(ANIMALS.read_text(encoding="utf-8"))
    names = sorted(table) if a.all or not a.species else [a.species]
    if a.all:
        print(f"{'species':10s} {'viable':>7s} {'good':>6s} {'binding feature':22s} reason")
        for sp in names:
            f = floors(sp, a.pose)
            worst, h = list(f.items())[-1]
            good = _target_height(f, a.target)
            print(f"{sp:10s} {h:7.0f} {good:6.0f} {worst:22s} "
                  f"{MIN_BLOCKS[worst]} blocks at {1/(h/MIN_BLOCKS[worst]):.3f} of height")
        return
    sp = names[0]
    f = floors(sp, a.pose)
    worst, h = list(f.items())[-1]
    good = _target_height(f, a.target)
    print(f"{sp}, posed {a.pose}\n")
    print(f"{'feature':22s} {'needs':>6s} {'is':>7s} {'-> min height':>14s}")
    for k, mh in f.items():
        print(f"{k:22s} {MIN_BLOCKS[k]:6d} {MIN_BLOCKS[k]/mh:7.3f} {mh:14.0f}")
    print(f"\nviable at {h:.0f} blocks tall - below this, `{worst}` cannot be built at all")
    print(f"quality {a.target:.0%} {good:6.0f} tall - {a.target:.0%} of features have real margin")
    print(f"comfortable {max(f.values()) * COMFORT:6.0f} tall - every feature with margin")
    print(f"\nbinding feature: {worst} - it needs {MIN_BLOCKS[worst]} blocks and is only "
          f"{MIN_BLOCKS[worst]/h:.1%} of the animal's height")
def _measure(a) -> None:
    """Build at a range of scales and measure what really comes out.

    The analytic floor says where an animal STOPS being possible. Only building it says where it
    stops improving - and those are different numbers. Quality climbs with size and then plateaus,
    and the plateau is set by how well the proportions are tuned, not by how many blocks there are.
    You cannot tune past the size floor, and you cannot size past a tuning error.
    """
    import yaml as y
    from mcbuild import scan
    from mcbuild.pipeline import Settings, run_config
    import proportions as pr

    cfg = y.safe_load(pathlib.Path(a.measure).read_text(encoding="utf-8"))
    name = cfg.get("name") or pathlib.Path(a.measure).stem
    species = (cfg.get("params") or {}).get("profile") or "giraffe"
    pose = (cfg.get("params") or {}).get("pose") or "standing"
    ref = posed(reference(species), pose)
    predicted = max(floors(species, pose).values())

    print(f"{name} ({species}, {pose}) - analytic floor {predicted:.0f} blocks tall")
    print(f"{'scale':>6s} {'tall':>5s} {'score':>7s} {'blocks':>7s}   failing")
    rows = []
    for sc in [float(x) for x in a.scales.split(",")]:
        try:
            m, _r = run_config(a.measure, settings=Settings(out_dir="out/_scale"),
                               overrides={"params.scale": sc}, render_sheet=False, verbose=False)
        except Exception as exc:
            print(f"{sc:6.2f}  FAILED {type(exc).__name__}")
            continue
        solid = m.solid()
        sy = solid.shape[0]
        try:
            land = scan.load(str(pathlib.Path("out/_scale") / (name + ".litematic"))).meta or {}
        except Exception:
            land = {}
        got = pr.measure(solid, land, sy)
        slack = pr.tilt_slack(pose)
        bad = []
        for k, want in ref.items():
            tol = 0.20 + (slack if k in pr.TILT_SENSITIVE else 0.0)
            if want and abs((got.get(k, 0) - want) / want) > tol:
                bad.append(k)
        score = 1.0 - len(bad) / max(1, len(ref))
        rows.append((sc, sy, score))
        print(f"{sc:6.2f} {sy:5d} {score:6.0%}  {int(solid.sum()):7d}   "
              + (", ".join(_short(b) for b in bad) or "-"))
    if not rows:
        return
    hit = [r for r in rows if r[2] >= a.target]
    best = max(r[2] for r in rows)
    print()
    if hit:
        sc, sy, sco = min(hit)
        print(f"smallest build reaching {a.target:.0%}: scale {sc} = {sy} blocks tall ({sco:.0%})")
    else:
        print(f"NOTHING reaches {a.target:.0%} at any size - it plateaus at {best:.0%}.")
        print("That is a PROPORTION problem, not a size one: more blocks cannot fix a wrong ratio.")
        print("Fix it with `tools/proportions.py` and the profile, then re-run this.")


def _short(k: str) -> str:
    """Distinct short labels - `leg width` and `leg (ground->belly)` both start "leg"."""
    return {"leg (ground->belly)": "leglen", "leg width": "legwid",
            "withers height": "withers", "body length": "bodylen",
            "body width": "bodywid", "body depth": "bodydep",
            "head length": "head", "neck length": "neck"}.get(k, k)


def _target_height(f: dict, target: float) -> float:
    """Height at which `target` of the features are COMFORTABLE - never below the viable floor.
    The clamp is the whole point. Taking the target quantile on its own recommended a giraffe 27
    blocks tall for "8 out of 10", because a giraffe's two worst features are its legs and dropping
    them buys a lot of height. But a giraffe with one-block legs is not eight-tenths of a giraffe,
    it is a broken one. Nothing below the viable height is ever a trade worth making.
    """
    need = sorted(mh * COMFORT for mh in f.values())
    idx = min(len(need) - 1, max(0, int(round(target * len(need))) - 1))
    return max(max(f.values()), need[idx])
if __name__ == "__main__":
    main()
