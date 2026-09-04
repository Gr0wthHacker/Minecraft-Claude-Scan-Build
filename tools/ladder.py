"""Find TONAL LADDERS - sets of blocks far enough apart in value to draw a line. A CLI over `tone`.

    python tools/ladder.py                          the best ladder in every hue band
    python tools/ladder.py --like stone_bricks      what can draw a line against stone brick
    python tools/ladder.py --coat oak_log           the SHADING ramp for a coat of that block
    python tools/ladder.py --audit                  every coat_ramp in species.yaml, checked
    python tools/ladder.py --hue 210 --stops 3 --tier cheap,ok,expensive

WHY THIS EXISTS. Three separate designs in this project reached the same wrong conclusion and wrote
it down as fact: that this economy has almost no value contrast. "cracked and chiseled stone brick
are within 4 RGB of plain"; "blackstone cannot draw value lines on itself - the family sits within
12 RGB"; "deepslate_bricks - 51 darker, the one real value contrast this economy has".

Each measurement is correct and the conclusion is false. All three searched inside ONE MATERIAL
FAMILY, where a value ladder cannot exist by construction - a family is one material shown four
ways, and dressing a stone does not change how much light it returns. Across families at the same
hue the cheap neutral ladder runs white_wool 236 / smooth_stone 159 / stone 126 / deepslate_bricks
71 / black_wool 21: 215 of luminance in five cheap stops, against the 51 we called our only one.

THE MEASUREMENT AND THE PICKER LIVE IN `mcbuild/tone.py`, NOT HERE. `coat.shade` needs the same
ladders at build time and `tools/` is not importable from `mcbuild/`, so a copy here would be two
implementations of one idea - exactly the drift `proportions.measure` and `rubric.score` share an
entry point to avoid. This file is argument parsing and printing.

TWO DIFFERENT QUESTIONS, TWO DIFFERENT ANSWERS. `--like` asks "what can draw a line AGAINST this
block" and maximises the smallest step over a whole hue band; that is right for a string course or
a merlon. `--coat` asks "what is this block, seen brighter and darker" and is leashed to the
material's own chroma; unleashed it proposed a lion of `cut_red_sandstone` and `yellow_wool`, which
has the largest possible steps and no lion in it.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcbuild import blocks, palette, tone       # noqa: E402

TIERS = ("cheap", "ok", "expensive")


def show(title: str, rungs: list[tuple], gap: float) -> None:
    print(f"\n### {title}   min step {gap:.0f}")
    for n, c, lm, _h, _s in rungs:
        print(f"    lum {lm:6.1f}  {palette.tier(n):9s} {n:30s} {c}")


def show_names(title: str, names: list[str], face: str) -> None:
    ls = [tone.luminance(n, face) or 0.0 for n in names]
    gaps = [ls[i + 1] - ls[i] for i in range(len(ls) - 1)] or [0.0]
    print(f"\n### {title}   {len(names)} rungs, min step {min(gaps):.0f}")
    for n, lm in zip(names, ls):
        print(f"    lum {lm:6.1f}  {palette.tier(n):9s} {n}")
    probs = tone.check_ramp(names, face=face)
    print("    " + ("OK" if not probs else "; ".join(probs)))


def audit(face: str) -> None:
    """Every `coat_ramp` in species.yaml against `check_ramp`, and what would replace it.

    When this was first run it failed 5 of 5 - three out of order, one with a block repeated,
    minimum adjacent steps from 0.0 to 10.1. The least bad (elephant, 10.1) is the only animal that
    passes both panels.
    """
    import yaml
    data = pathlib.Path(__file__).resolve().parent.parent / "mcbuild/data/species.yaml"
    sp = yaml.safe_load(data.read_text(encoding="utf-8"))
    bad = 0
    for name, cfg in sp.items():
        coat = (cfg or {}).get("coat") or {}
        ramp = coat.get("coat_ramp")
        if not ramp:
            continue
        probs = tone.check_ramp(ramp, face=face)
        base = coat.get("coat_block") or ramp[len(ramp) // 2]
        print(f"\n{name}  ({'OK' if not probs else 'DEFECTIVE'})   coat block {base}")
        for n in ramp:
            print(f"    lum {tone.luminance(n, face):6.1f}  {n}")
        for p in probs:
            print(f"    ! {p}")
        if probs:
            bad += 1
            better = tone.coat_ladder(base, max(5, len(ramp)), extra=tuple(ramp), face=face)
            print(f"    -> {better}")
            print(f"       lums {[round(tone.luminance(n, face)) for n in better]}"
                  f"   {tone.check_ramp(better, face=face) or 'OK'}")
    print(f"\n{bad} defective ramp(s).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--like", help="a block: the ladder that can draw a line against it")
    ap.add_argument("--coat", help="a block: the SHADING ramp for a coat made of it")
    ap.add_argument("--audit", action="store_true", help="check every coat_ramp in species.yaml")
    ap.add_argument("--hue", type=float, help="hue in degrees 0-360; omit for every band")
    ap.add_argument("--band", type=float, default=25.0, help="hue half-width in degrees")
    ap.add_argument("--grey", type=float, default=0.12, help="saturation below which a block is neutral")
    ap.add_argument("--stops", type=int, default=4)
    ap.add_argument("--spread", type=float, default=tone.DEFAULT_SPREAD,
                    help="--coat only: luminance the ramp may span, centred on the block")
    ap.add_argument("--tier", default="cheap,ok")
    ap.add_argument("--face", default="side", help="side for elevation, top for a floor")
    ap.add_argument("--partials", action="store_true", help="include slabs, stairs and the rest")
    ap.add_argument("--any", action="store_true",
                    help="search the whole registry instead of blocks witnessed on this server - "
                         "proposes blocks that do not exist in 1.19, so read the names")
    a = ap.parse_args()

    if a.audit:
        audit(a.face)
        return

    tiers = {t.strip() for t in a.tier.split(",") if t.strip()}
    bad = tiers - set(TIERS)
    if bad:
        ap.error(f"unknown tier(s) {sorted(bad)}; pick from {TIERS}")

    if a.coat:
        names = tone.coat_ladder(a.coat, a.stops, spread=a.spread, tiers=tuple(tiers),
                                 face=a.face, witnessed=not a.any)
        show_names(f"coat ramp for {a.coat}", names, a.face)
        return

    cands = tone.pool(tiers=tuple(tiers), face=a.face, full_only=not a.partials,
                      witnessed=not a.any)
    neutral = [c for c in cands if c[4] < a.grey]
    src = ("the WHOLE 26.2 registry - unverified against the 1.19 server, check every name"
           if a.any else "blocks witnessed on this server")
    print(f"{len(cands)} blocks from {src}; tier {sorted(tiers)}, face={a.face} "
          f"({len(neutral)} neutral under sat {a.grey})")

    if a.like:
        name = a.like.split(":")[-1]
        c = blocks.color(name, a.face)
        if not c:
            ap.error(f"no colour recorded for {name}")
        h, s = tone.hue_sat(c)
        lm = tone.lum(c)
        band = neutral if s < a.grey else [x for x in cands if tone.hue_near(x[3], h, a.band)]
        where = "NEUTRAL" if s < a.grey else f"hue band {h:.0f}+-{a.band:.0f}"
        print(f"\n{name} is lum {lm:.0f}, hue {h:.0f}, sat {s:.2f} -> {where}, {len(band)} blocks")
        rungs, gap = tone.best_ladder(band, a.stops)
        show(f"ladder around {name}", list(reversed(rungs)), gap)
        close = [x for x in band if x[0] != name and abs(x[2] - lm) < 20]
        print(f"\n  cannot draw a line against {name} (within 20 lum) - {len(close)} blocks:")
        for n, _cc, ll, _h, _s in sorted(close, key=lambda t: abs(t[2] - lm))[:8]:
            print(f"    {abs(ll - lm):5.1f} apart   {n}")
        return

    bands: list[tuple[str, list[tuple]]] = []
    if a.hue is None:
        bands.append(("neutral", neutral))
        for h0 in range(0, 360, 30):
            sel = [c for c in cands
                   if c[4] >= a.grey and tone.hue_near(c[3], h0 + 15, 15 + a.band / 2)]
            if len(sel) >= a.stops:
                bands.append((f"hue {h0:3d}-{h0 + 30:3d}", sel))
    else:
        bands.append((f"hue {a.hue:.0f}+-{a.band:.0f}",
                      [c for c in cands if tone.hue_near(c[3], a.hue, a.band)]))

    for title, sel in bands:
        if len(sel) < 2:
            continue
        rungs, gap = tone.best_ladder(sel, a.stops)
        show(f"{title}  [{len(sel)} blocks]", list(reversed(rungs)), gap)


if __name__ == "__main__":
    main()
