"""Find TONAL LADDERS - sets of blocks in one hue far enough apart in value to draw a line.

    python tools/ladder.py                          the best ladder in every hue band
    python tools/ladder.py --like stone_bricks      what can draw a line against stone brick
    python tools/ladder.py --hue 210 --stops 3      three stops of blue
    python tools/ladder.py --tier cheap,ok,expensive --stops 4

WHY THIS EXISTS. Three separate designs in this project reached the same wrong conclusion and wrote
it down as fact: that this economy has almost no value contrast. "cracked and chiseled stone brick
are within 4 RGB of plain, so weathering a wall with them is invisible"; "blackstone cannot draw
value lines on itself - the family sits within 12 RGB"; "deepslate_bricks - 51 darker, the one real
value contrast this economy has at cheap-or-ok tier".

Each of those measurements is correct and the conclusion drawn from them is false. They all searched
inside ONE MATERIAL FAMILY, where a value ladder cannot exist by construction: a family is one
material shown four ways, and dressing a stone does not change how much light it returns. Searched
ACROSS families at the same hue, the cheap neutral ladder runs white_wool 236 -> smooth_stone 159 ->
stone 126 -> deepslate_bricks 71 -> black_wool 21. That is 215 of luminance in five cheap stops,
against the 51 this repo has been calling its only contrast.

A 31-build corpus of other people's work is what forced the point: their sculptures are one body
block at 50-90% plus three to six accent shades spanning ~150 of luminance, and those accents are
what make a voxel mass read as a form rather than as a coloured shape. See the corpus notes in
CLAUDE.md. Their ladders are terracotta and concrete, which are EXPENSIVE here - so the ladder has
to be found rather than copied, which is what this tool is for.

WHAT A LADDER IS SCORED ON. The MINIMUM adjacent gap, never the total range. A ladder of 236/159/151
has a 85 range and its bottom two stops are indistinguishable in game, so it is a two-stop ladder
wearing three blocks. Maximising the smallest step is what makes every stop do work.

HUE IS BANDED, NOT MATCHED. Two blocks 20 degrees apart in hue read as the same colour once either
is dark, and demanding an exact match throws away most of the registry. `--band` widens or narrows
it. Anything under `--grey` saturation is filed as neutral, which is where the useful ladders are.

FACE MATTERS AND DEFAULTS TO `side`. A ladder is nearly always wanted for something seen in
elevation - a wall, a statue, a tower. `blocks.color` answers per face and the two differ for 155
blocks, so a ladder taken off the top face is the ladder for a FLOOR.

THE POOL IS WITNESSED, NOT REMEMBERED. Searched over the bare registry this tool proposes
`dried_ghast`, `chiseled_cinnabar` and `test_instance_block` - all real, all legal, none of them on
a 1.19 server - because `blocks.available()` is a no-op while the allowlist is provisional. That is
rule 12's exact failure and this repo has already shipped it twice (`_eye_ring` picked
`stripped_pale_oak_log`). So the pool starts from `shell._confirmed()`, the blocks the allowlist has
actually WITNESSED in a capture off this server, and `--any` opens it to the whole registry while
saying loudly what that costs.

WITNESSED ALONE IS TOO NARROW, AND WIDENING IT TAKES TWO STEPS - both evidence, neither memory.

  1. A CAPTURE beats the allowlist. `server_blocks.json` holds 191 blocks and is stale: it does not
     name `deepslate_bricks`, which four of this island's designs are built from and Jack has
     placed by the thousand. `out/island_full.litematic` holds 205 distinct blocks and every one of
     them is standing in this world right now, which is the strongest evidence there is. The
     allowlist and the capture are unioned; `--witness` names a different capture.
  2. A DYED FAMILY is complete. The witness set holds `black_terracotta` and `brown_terracotta` but
     not `gray_terracotta`, and Minecraft ships a dyed family whole - a server with one terracotta
     has sixteen. So a witnessed member admits its colour family: 79 blocks, mostly the concretes
     and terracottas. Same inference `shell.trusted_slabs` makes about a material family, and
     nothing beyond it is inferred. The expansion is a NAME set intersected with the real registry
     later, so a family that does not actually come in sixteen costs nothing - it proposes
     `black_tulip`, `blocks.candidates()` has never heard of it, and it never reaches an answer.

FUNCTIONAL BLOCKS GO OUT THROUGH `rubric.FUNCTIONAL`, NOT `protect.is_protected`. Reaching for the
protect set here is the mistake `Island Night` already made and wrote down: `is_protected` is the
never-OVERWRITE set, and it holds `wool` because a wool block may be a sculk sensor's silencer.
Used as "may I build with this" it deletes every wool in the game - which is most of this island's
sculpture. The question here is the rubric's `plain_blocks_only` gate, so that is the set consulted.
"""
from __future__ import annotations

import argparse
import colorsys
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcbuild import blocks, palette            # noqa: E402
from mcbuild.gen import shell                  # noqa: E402
from rubric import FUNCTIONAL                  # noqa: E402  the plain_blocks_only gate, one source

TIERS = ("cheap", "ok", "expensive")

# The sixteen dye names. A family witnessed in ANY colour is witnessed in all of them - Minecraft
# ships a dyed family complete, which is the same inference `shell.trusted_slabs` makes about a
# material family. Nothing beyond this is inferred.
DYES = ("white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
        "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black")

# Blocks the gates above let through that are not material anyone can build with here.
#   shulker_box - `rubric.FUNCTIONAL` does not name it, so the dyed-family expansion admits all
#     sixteen as surface blocks. They are containers with a lid, and on this economy they are
#     storage. Excluded here rather than by widening the rubric's gate, which is a scoring decision
#     and Jack's - but the gap is real and worth closing there one day.
#   bedrock - present in every capture, obtainable by nobody. It is the one block where "witnessed
#     in this world" is not evidence that you may place it.
NOT_MATERIAL = ("shulker_box", "bedrock")

# Strongest witness available offline: blocks standing in this world today. Beats the allowlist,
# which is provisional and already stale.
CAPTURE = pathlib.Path(__file__).resolve().parent.parent / "out/island_full.litematic"


def dye_family(name: str) -> str | None:
    """`light_blue_concrete` -> `concrete`; None for a block that carries no dye colour."""
    for d in sorted(DYES, key=len, reverse=True):
        if name.startswith(d + "_"):
            return name[len(d) + 1:]
    return None


def witnessed_blocks(capture: pathlib.Path | None = CAPTURE) -> set[str]:
    """The allowlist, plus a capture's palette, plus the rest of every dyed family in either."""
    conf = set(shell._confirmed())
    if capture and capture.exists():
        from mcbuild import schem
        conf |= {n.split(":")[-1] for n in schem.load(str(capture)).names}
    fams = {f for f in (dye_family(n) for n in conf) if f}
    return conf | {f"{d}_{f}" for d in DYES for f in fams}


def lum(rgb) -> float:
    """Rec.709 luminance - the same weighting the rubric's `form` dimension uses."""
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def hue_sat(rgb) -> tuple[float, float]:
    h, _, s = colorsys.rgb_to_hls(*[v / 255 for v in rgb])
    return h * 360.0, s


def pool(tiers: set[str], face: str = "side", full_only: bool = True,
         witnessed: bool = True, capture: pathlib.Path | None = CAPTURE) -> list[tuple]:
    """(name, rgb, luminance, hue, saturation) for every block a surface may honestly be made of.

    `witnessed` restricts to `witnessed_blocks()` - the allowlist, a capture of this world, and the
    dyed families either of them proves. Same starting source as `shell.trusted_slabs`, so a ladder
    and a slab shell cannot disagree about what exists.
    """
    conf = witnessed_blocks(capture) if witnessed else None
    out = []
    for n in blocks.candidates(full_only=full_only, tier=tiers):
        s_name = n.split(":")[-1]
        if conf is not None and s_name not in conf:
            continue
        if any(f in s_name for f in FUNCTIONAL) or any(f in s_name for f in NOT_MATERIAL):
            continue
        c = blocks.color(n, face)
        if not c:
            continue
        h, s = hue_sat(c)
        out.append((s_name, tuple(c), lum(c), h, s))
    return out


def hue_near(a: float, b: float, band: float) -> bool:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d) <= band


def ladder(cands: list[tuple], stops: int) -> tuple[list[tuple], float]:
    """The `stops` blocks whose SMALLEST adjacent luminance gap is largest, brightest first.

    Exact rather than greedy: sort by luminance and binary-search the achievable gap, taking the
    first block at or above each threshold. Greedy-from-the-brightest agrees on most inputs and
    quietly loses the ladder whenever one end of the range is crowded.
    """
    if len(cands) < 2:
        return sorted(cands, key=lambda t: -t[2]), 0.0
    by = sorted(cands, key=lambda t: t[2])

    def fits(gap: float):
        picked = [by[0]]
        for c in by[1:]:
            if c[2] - picked[-1][2] >= gap:
                picked.append(c)
        return picked if len(picked) >= stops else None

    lo, hi, best = 0.0, by[-1][2] - by[0][2], fits(0.0)
    if best is None:                       # fewer blocks than stops asked for
        best = by
    for _ in range(40):
        mid = (lo + hi) / 2
        got = fits(mid)
        if got:
            best, lo = got, mid
        else:
            hi = mid
    best = best[:stops]
    gaps = [best[i + 1][2] - best[i][2] for i in range(len(best) - 1)]
    return list(reversed(best)), (min(gaps) if gaps else 0.0)


def show(title: str, rungs: list[tuple], gap: float) -> None:
    print(f"\n### {title}   min step {gap:.0f}")
    for n, c, lm, _h, _s in rungs:
        print(f"    lum {lm:6.1f}  {palette.tier(n):9s} {n:30s} {c}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--like", help="a block: report the ladder in ITS hue band, and where it sits")
    ap.add_argument("--hue", type=float, help="hue in degrees 0-360; omit for every band")
    ap.add_argument("--band", type=float, default=25.0, help="hue half-width in degrees")
    ap.add_argument("--grey", type=float, default=0.12,
                    help="saturation below which a block is filed as neutral")
    ap.add_argument("--stops", type=int, default=4)
    ap.add_argument("--tier", default="cheap,ok", help="comma list of cheap,ok,expensive")
    ap.add_argument("--face", default="side",
                    help="side for anything seen in elevation, top for a floor")
    ap.add_argument("--partials", action="store_true",
                    help="include slabs, stairs and the rest, not only full cubes")
    ap.add_argument("--witness", help=f"capture whose palette counts as evidence "
                                      f"(default {CAPTURE.name})")
    ap.add_argument("--any", action="store_true",
                    help="search the whole registry instead of blocks witnessed on this server - "
                         "proposes blocks that do not exist in 1.19, so read the names")
    a = ap.parse_args()

    tiers = {t.strip() for t in a.tier.split(",") if t.strip()}
    bad = tiers - set(TIERS)
    if bad:
        ap.error(f"unknown tier(s) {sorted(bad)}; pick from {TIERS}")

    cands = pool(tiers, face=a.face, full_only=not a.partials, witnessed=not a.any,
                 capture=pathlib.Path(a.witness) if a.witness else CAPTURE)
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
        h, s = hue_sat(c)
        lm = lum(c)
        band = neutral if s < a.grey else [x for x in cands if hue_near(x[3], h, a.band)]
        where = "NEUTRAL" if s < a.grey else f"hue band {h:.0f}+-{a.band:.0f}"
        print(f"\n{name} is lum {lm:.0f}, hue {h:.0f}, sat {s:.2f} -> {where}, {len(band)} blocks")
        rungs, gap = ladder(band, a.stops)
        show(f"ladder around {name}", rungs, gap)
        close = [x for x in band if x[0] != name and abs(x[2] - lm) < 20]
        print(f"\n  cannot draw a line against {name} (within 20 lum) - {len(close)} blocks:")
        for n, _cc, ll, _h, _s in sorted(close, key=lambda t: abs(t[2] - lm))[:8]:
            print(f"    {abs(ll - lm):5.1f} apart   {n}")
        return

    bands: list[tuple[str, list[tuple]]] = []
    if a.hue is None:
        bands.append(("neutral", neutral))
        for h0 in range(0, 360, 30):
            sel = [c for c in cands if c[4] >= a.grey and hue_near(c[3], h0 + 15, 15 + a.band / 2)]
            if len(sel) >= a.stops:
                bands.append((f"hue {h0:3d}-{h0 + 30:3d}", sel))
    else:
        bands.append((f"hue {a.hue:.0f}+-{a.band:.0f}",
                      [c for c in cands if hue_near(c[3], a.hue, a.band)]))

    for title, sel in bands:
        if len(sel) < 2:
            continue
        rungs, gap = ladder(sel, a.stops)
        show(f"{title}  [{len(sel)} blocks]", rungs, gap)


if __name__ == "__main__":
    main()
