"""WHERE THE 600x200 PARK ACTUALLY GOES, derived from the islands rather than typed.

Jack, on the shipped preview: "we are out of range on the 600x200, check alignments and shift it
further in the direction of the bird as its aligned the other way further."

He is right, and the arithmetic leaves no room for judgement. The three plots are 200x200 when
expanded, centred on their own bedrock at Z 80400 / 80600 / 80800 and all three at X 97600:

    islandleft   X97500..97699  Z80300..80499
    newisle      X97500..97699  Z80500..80699
    islandright  X97500..97699  Z80700..80899
    ---------------------------------------------------------------
    union        X97500..97699  Z80300..80899   =  200 x 600, EXACTLY

**SO THE ENVELOPE IS NOT ROUGHLY THIS SIZE, IT IS THIS SIZE**, and the anchor is forced: V0 at
X97500 and U0 at Z80300, with no slack on any edge to absorb an error. Two were shipped anyway -
`park_final.world.json` recorded Z80349 (49 over the far end) and the preview shipped X97551/Z80351
(51 over both). Both put the park's rim band and its last land off the plots entirely.

The direction of the correction is the check Jack made by eye: the Signal Heron stands at low V,
and low V is low X, so a park hanging off the high edge has to move TOWARD the bird. It does -
X-51, Z-51.

**NOTHING HERE IS TYPED FROM A DOCUMENT.** The plots come from the island registry the mod and
`mcbuild islands` already share, which is the same one-source rule `proportions.measure` and
`rubric.score` follow: a spec file and a registry that disagree cannot both be right, and only one
of them is measured off a capture.

    python tools/park_anchor.py                 the anchor, and every shipped design checked
    python tools/park_anchor.py --ship          ...and re-ship the tracked designs onto it
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import profile as mcprofile, schem  # noqa: E402

#: The park's own axes. V is the 200-deep axis and U the 600-long one; the three plots are strung
#: out along Z, so U is Z and V is X. Getting this round the other way is not a subtle error - it
#: makes the park 600 wide across a 200-wide island - but it IS silent, so it is stated once here.
V_AXIS, U_AXIS = "x", "z"
V_DEEP, U_LONG = 200, 600
#: The floor blocks occupy the course BELOW the plane you stand on. `tools/parkship.py` says the
#: same thing; a design's own y=0 is its floor course.
BUILD_PLANE = 203
PLOT = 200                      # a plot expanded, per side of its bedrock


def islands(schem_dir: Path | None = None) -> dict:
    d = Path(schem_dir or mcprofile.load()["schem_dir"])
    f = d / "islands.json"
    if not f.exists():
        raise SystemExit(f"no island registry at {f} - run `python -m mcbuild islands --add ...`")
    return json.loads(f.read_text(encoding="utf-8"))["islands"]


def envelope(names=("islandleft", "newisle", "islandright"), schem_dir=None) -> dict:
    """The union of the three expanded plots, and the anchor it forces."""
    reg = islands(schem_dir)
    missing = [n for n in names if n not in reg]
    if missing:
        raise SystemExit(f"island registry has no {', '.join(missing)}")
    half = PLOT // 2
    xs = [(reg[n]["cx"] - half, reg[n]["cx"] + half - 1) for n in names]
    zs = [(reg[n]["cz"] - half, reg[n]["cz"] + half - 1) for n in names]
    x0, x1 = min(a for a, _ in xs), max(b for _, b in xs)
    z0, z1 = min(a for a, _ in zs), max(b for _, b in zs)
    return {"plots": {n: {"x": list(xs[i]), "z": list(zs[i])} for i, n in enumerate(names)},
            "x": [x0, x1], "z": [z0, z1],
            "size": [x1 - x0 + 1, z1 - z0 + 1],
            "anchor": [x0, BUILD_PLANE - 1, z0]}


def check(anchor, env) -> list[str]:
    """Every way the park can hang off the plots, named with its overrun."""
    ax, _ay, az = anchor
    (x0, x1), (z0, z1) = env["x"], env["z"]
    out = []
    if ax < x0: out.append(f"V0 is {x0 - ax} west of the plots")
    if ax + V_DEEP - 1 > x1: out.append(f"V{V_DEEP-1} is {ax + V_DEEP - 1 - x1} east of the plots")
    if az < z0: out.append(f"U0 is {z0 - az} north of the plots")
    if az + U_LONG - 1 > z1: out.append(f"U{U_LONG-1} is {az + U_LONG - 1 - z1} south of the plots")
    return out


def tracked() -> list[str]:
    import yaml
    cfg = yaml.safe_load((ROOT / "sync.yaml").read_text(encoding="utf-8"))
    return list(cfg.get("progress") or [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ship", action="store_true",
                    help="rewrite each tracked design's shipped sidecar onto the correct anchor")
    args = ap.parse_args()

    env = envelope()
    ax, ay, az = env["anchor"]
    print(f"plots (expanded to {PLOT}x{PLOT}):")
    for n, p in env["plots"].items():
        print(f"  {n:<13} X{p['x'][0]}..{p['x'][1]}  Z{p['z'][0]}..{p['z'][1]}")
    print(f"union          X{env['x'][0]}..{env['x'][1]}  Z{env['z'][0]}..{env['z'][1]}"
          f"   {env['size'][0]} x {env['size'][1]}")
    if env["size"] != [V_DEEP, U_LONG]:
        print(f"  !! the union is not {V_DEEP}x{U_LONG}; the anchor below is a corner, not a fit")
    print(f"\nANCHOR  X{ax}  Y{ay}  Z{az}      V0 -> X{ax},  U0 -> Z{az}\n")

    dest = Path(mcprofile.load()["schem_dir"])
    bad = 0
    for name in tracked():
        side = dest / f"{name}.scan.json"
        if not side.exists():
            print(f"  {name:<14} not shipped"); continue
        meta = json.loads(side.read_text(encoding="utf-8"))
        o = meta["origin"]
        have = [o["x"], o["y"], o["z"]]
        model = schem.load(str(dest / f"{name}.litematic"))
        _sy, _sz, _sx = model.ids.shape
        off = check(have, env)
        mark = "OK " if have[0] == ax and have[2] == az else "OFF"
        if mark == "OFF": bad += 1
        print(f"  {mark} {name:<14} at X{have[0]} Y{have[1]} Z{have[2]}"
              f"{'' if not off else '   ' + '; '.join(off)}")
        if args.ship and mark == "OFF":
            meta["origin"] = {"x": ax, "y": have[1], "z": az}
            meta["anchor_note"] = ("derived by tools/park_anchor.py from the island registry - the "
                                   "600x200 fits the three expanded plots exactly, so this is "
                                   "forced rather than chosen")
            side.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            local = ROOT / "out" / f"{name}.scan.json"
            if local.exists():
                lm = json.loads(local.read_text(encoding="utf-8"))
                lm["origin"] = {"x": ax, "y": have[1], "z": az}
                local.write_text(json.dumps(lm, indent=2), encoding="utf-8")
            print(f"      -> moved to X{ax} Z{az}")
    if bad and not args.ship:
        print(f"\n{bad} design(s) off the anchor. `--ship` moves them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
