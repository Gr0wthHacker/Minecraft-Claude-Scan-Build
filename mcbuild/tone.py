"""VALUE, and the ladders a coat is shaded with. One source for the tool and the generators.

`coat.shade` reads a form's light and paints it with a `ramp` - a list of blocks dark to light. The
ramp is the whole mechanism: shading with a ladder whose rungs are one luminance apart is shading
with one colour. Every ramp in `species.yaml` was hand-written, and when they were finally measured
all five were defective - three out of order, one with a block repeated, minimum adjacent steps of
0.0 to 10.1. The one that is least bad (elephant, 10.1) is also the only animal that passes both
panels, which is the correlation that started this file.

So the ladder is chosen by MEASUREMENT here, and `check_ramp` is the gate that says whether a
hand-written one is honest.

WHAT A LADDER IS SCORED ON. The MINIMUM adjacent gap, never the total range. `[89, 93, 98, 88, 147]`
- the lion's - spans 59 and is two usable stops, one of them out of order so the shader paints the
crevice tone onto a lit cell. A ladder is only as good as the step nobody can see.

THE POOL IS WITNESSED, NOT REMEMBERED. Over the bare registry the search proposes `dried_ghast` and
`chiseled_cinnabar` - real, legal, and not on a 1.19 server, because `blocks.available()` is a no-op
while the allowlist is provisional. Rule 12's exact failure, shipped twice here already. So the pool
starts from what has been WITNESSED on this server and widens only by evidence:

  1. A CAPTURE beats the allowlist. `server_blocks.json` holds 191 blocks and is stale - it does not
     name `deepslate_bricks`, which four designs are built from. A full-depth capture holds 205 and
     every one of them is standing in this world right now.
  2. A DYED FAMILY is complete. The witness set holds `black_terracotta` and `brown_terracotta` but
     not `gray_terracotta`, and Minecraft ships a dyed family whole. Same inference
     `shell.trusted_slabs` makes about a material family, and nothing beyond it is inferred. The
     expansion is a NAME set intersected with the real registry later, so a family that does not
     come in sixteen costs nothing: it proposes `black_tulip`, `blocks.candidates()` has never heard
     of it, and it never reaches an answer.

FUNCTIONAL BLOCKS GO OUT THROUGH `protect.is_protected` PLUS A ONE-ENTRY RE-ADMISSION. The protect
set is this repo's one safe set and it removes exactly the junk a coat search drags in - without it
the lion's ladder came back containing `fletching_table`, `smithing_table` and `cartography_table`.
But used bare it is the mistake `Island Night` already made and wrote down: `is_protected` is the
never-OVERWRITE set, and it holds `wool` because a wool block may be a sculk sensor's silencer. Used
as "may I build with this" it deletes every wool in the game, which is most of this island's
sculpture material.

The fix is not a parallel list - a second copy of "what is a machine" is the drift this repo keeps
writing rules against. It is `is_protected`, minus the one entry that names a MATERIAL rather than a
machine: `wool`. Measured, that re-admits 16 blocks and keeps out 4, which is the whole of the
disagreement.

FACE DEFAULTS TO `side`. A coat is seen in elevation. `blocks.color` answers per face and the two
differ for 155 blocks, so a ladder taken off the top face is the ladder for a floor.
"""
from __future__ import annotations

import colorsys
import functools
import pathlib

from . import blocks

# The sixteen dye names, longest first so `light_gray_wool` is not read as `gray` plus a stray
# `light_`.
DYES = ("light_gray", "light_blue", "magenta", "orange", "yellow", "purple", "brown", "green",
        "white", "black", "blue", "cyan", "gray", "lime", "pink", "red")

# Blocks the gates below let through that nobody can build a surface out of here.
#   shulker_box - `rubric.FUNCTIONAL` does not name it, so the dyed-family expansion admits all
#     sixteen. They are containers with a lid; on this economy they are storage, not material.
#     Excluded here rather than by widening the rubric's gate, which is a scoring decision.
#   bedrock - in every capture, obtainable by nobody. The one block where "witnessed in this world"
#     is not evidence you may place it.
NOT_MATERIAL = ("shulker_box", "bedrock")

# The one entry of `protect.MECHANISM` that names a MATERIAL rather than a machine. Wool is in the
# protect set because it silences a sculk sensor, and it is also most of this island's sculpture -
# so it must be re-admitted here or a coat search returns nothing to build with. Every other
# MECHANISM entry is correctly refused: measured, the bare set also throws out `fletching_table`,
# `smithing_table`, `cartography_table` and `ochre_froglight`, all of which a colour search reaches
# for. `ice` was briefly on this list and is not a coat block - it is translucent and it melts.
MATERIAL_ANYWAY = ("wool",)

# How far a rung may drift in CHROMA from the coat's own colour before it stops being the same
# material seen brighter. Beyond this a rung is a different animal: at 0.30 a white bear's light
# rung came back `yellow_wool`, which is the nearest warm block at that brightness and visibly wrong.
MAX_CHROMA_DRIFT = 0.16

CAPTURE = pathlib.Path(__file__).resolve().parent.parent / "out/island_full.litematic"

# Below this, two rungs are one rung. Chosen from the corpus rather than invented: their sculptures
# carry three to six accents spanning ~150 of luminance, which is ~30 a step, and the worst ramp
# that still reads here (elephant, 10.1) passes both panels while the four below it do not. 15 is
# the midpoint and the value `check_ramp` fails under.
MIN_STEP = 15.0

# How much luminance a coat ramp may span, centred on the coat's own block. Derived from the corpus
# rather than invented: their sculptures carry their accents across ~150 of luminance with the body
# block sitting mid-range, so +-60 is the same window. Confirmed by looking - swept at 90/120/150
# and unbounded on the elephant, 120 is where the shoulder, flank and trunk separate while the
# animal is still unmistakably grey stone. Unbounded put `snow_block` on its back and built a
# marble elephant; 90 was still flat. A species may narrow it (species.yaml records that the polar
# bear needs a narrow ramp, "spanning tan to white made the shading paint the back snow").
DEFAULT_SPREAD = 120.0


def lum(rgb) -> float:
    """Rec.709 luminance - the weighting the rubric's `form` dimension already uses."""
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def luminance(name: str, face: str = "side") -> float | None:
    c = blocks.color(name, face)
    return None if c is None else lum(c)


def hue_sat(rgb) -> tuple[float, float]:
    h, _, s = colorsys.rgb_to_hls(*[v / 255 for v in rgb])
    return h * 360.0, s


def hue_near(a: float, b: float, band: float) -> bool:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d) <= band


def dye_family(name: str) -> str | None:
    """`light_blue_concrete` -> `concrete`; None for a block carrying no dye colour."""
    for d in DYES:
        if name.startswith(d + "_"):
            return name[len(d) + 1:]
    return None


@functools.lru_cache(maxsize=4)
def witnessed_blocks(capture: str | None = None) -> frozenset:
    """The allowlist, plus a capture's palette, plus the rest of every dyed family in either."""
    from .gen import shell
    conf = set(shell._confirmed())
    path = pathlib.Path(capture) if capture else CAPTURE
    if path.exists():
        from . import schem
        conf |= {n.split(":")[-1] for n in schem.load(str(path)).names}
    fams = {f for f in (dye_family(n) for n in conf) if f}
    return frozenset(conf | {f"{d}_{f}" for d in DYES for f in fams})


def is_material(name: str) -> bool:
    """May a surface be built out of this? `protect.is_protected` minus `MATERIAL_ANYWAY`."""
    from .gen import protect
    s = name.split(":")[-1]
    if any(f in s for f in NOT_MATERIAL):
        return False
    if any(f in s for f in MATERIAL_ANYWAY):
        return True
    return not protect.is_protected(s)


def pool(tiers=("cheap", "ok"), face: str = "side", full_only: bool = True,
         witnessed: bool = True, capture: str | None = None) -> list[tuple]:
    """(name, rgb, luminance, hue, saturation) for every block a surface may honestly be made of."""
    conf = witnessed_blocks(capture) if witnessed else None
    out = []
    for n in blocks.candidates(full_only=full_only, tier=set(tiers)):
        s = n.split(":")[-1]
        if conf is not None and s not in conf:
            continue
        if not is_material(s):
            continue
        c = blocks.color(n, face)
        if not c:
            continue
        h, sat = hue_sat(c)
        out.append((s, tuple(c), lum(c), h, sat))
    return out


def chroma(rgb) -> tuple[float, float, float]:
    """Colour with brightness divided out, so two tones of one material sit on top of each other.

    This is what makes a ramp a SHADING ramp. Comparing raw RGB pulls the search toward whatever is
    nearest overall, which for a dark brown is another dark brown - so the ladder never gets
    lighter. Dividing by luminance asks the only question a shading rung has to answer: is this the
    same MATERIAL, seen brighter or darker.
    """
    l = max(1.0, lum(rgb))
    return (rgb[0] / l, rgb[1] / l, rgb[2] / l)


def _chroma_dist(a, b) -> float:
    ca, cb = chroma(a), chroma(b)
    return sum((ca[i] - cb[i]) ** 2 for i in range(3)) ** 0.5


def best_ladder(cands: list[tuple], stops: int) -> tuple[list[tuple], float]:
    """The `stops` blocks whose SMALLEST adjacent luminance gap is largest, DARKEST FIRST.

    Dark first because that is the order `coat.shade` wants a ramp in, and handing it a bright-first
    list silently inverts every animal's lighting.

    Exact rather than greedy: sort by luminance and binary-search the achievable gap, taking the
    first block at or above each threshold. Greedy-from-one-end agrees on most inputs and quietly
    loses the ladder whenever one end of the range is crowded.
    """
    if len(cands) < 2:
        return sorted(cands, key=lambda t: t[2]), 0.0
    by = sorted(cands, key=lambda t: t[2])

    def fits(gap: float):
        picked = [by[0]]
        for c in by[1:]:
            if c[2] - picked[-1][2] >= gap:
                picked.append(c)
        return picked if len(picked) >= stops else None

    lo, hi = 0.0, by[-1][2] - by[0][2]
    best = fits(0.0) or by
    for _ in range(40):
        mid = (lo + hi) / 2
        got = fits(mid)
        if got:
            best, lo = got, mid
        else:
            hi = mid
    best = best[:stops]
    gaps = [best[i + 1][2] - best[i][2] for i in range(len(best) - 1)]
    return best, (min(gaps) if gaps else 0.0)


def anchored_ladder(cands: list[tuple], stops: int, anchor: tuple) -> tuple[list[tuple], float]:
    """`stops` rungs with the largest possible smallest step, GUARANTEED to contain `anchor`.

    Two things force this over plain `best_ladder`:

    THE COAT BLOCK MUST BE IN ITS OWN RAMP. It is the colour the species is defined by, and a ladder
    free to drop it returns a ramp for some other animal - `stripped_oak_log` fell out of the lion's
    and the lion stopped being oak.

    AND IT IS WHAT KEEPS TWO SIBLINGS APART. Unanchored, the lion (oak_log) and the bear
    (mangrove_wood) came back with the SAME five blocks, because both are brown and the search only
    ever saw "brown". `compare.py` measures within-family distinction and already reports the bears
    at coat gap 0.86 doing the work the shape cannot; handing two species one ramp would delete
    that. Anchoring on the coat block is what makes the ladders differ by the thing that differs.

    The chain is grown outward from the anchor in both directions, which is optimal for a fixed
    point: below it take the brightest candidate at least `gap` darker each time, above it the
    darkest candidate at least `gap` brighter.
    """
    if not cands:
        return [anchor], 0.0
    by = sorted(cands, key=lambda t: t[2])

    def chain(gap: float):
        down = []
        cur = anchor[2]
        for c in reversed(by):
            if c[2] <= cur - gap and c[0] != anchor[0]:
                down.append(c)
                cur = c[2]
        up = []
        cur = anchor[2]
        for c in by:
            if c[2] >= cur + gap and c[0] != anchor[0]:
                up.append(c)
                cur = c[2]
        return list(reversed(down)) + [anchor] + up

    lo, hi = 0.0, (by[-1][2] - by[0][2]) or 1.0
    best = chain(0.0)
    for _ in range(40):
        mid = (lo + hi) / 2
        got = chain(mid)
        if len(got) >= stops:
            best, lo = got, mid
        else:
            hi = mid
    # Trim to `stops` around the anchor, keeping the widest span - dropping from the crowded end
    # would shorten the ramp rather than the list.
    while len(best) > stops:
        i = best.index(anchor)
        drop_low = best[1][2] - best[0][2] if i > 0 else 1e9
        drop_high = best[-1][2] - best[-2][2] if i < len(best) - 1 else 1e9
        best.pop(0 if drop_low <= drop_high else -1)
    gaps = [best[i + 1][2] - best[i][2] for i in range(len(best) - 1)]
    return best, (min(gaps) if gaps else 0.0)


def coat_ladder(base: str, stops: int = 5, *, spread: float | None = DEFAULT_SPREAD,
                tiers=("cheap", "ok"),
                face: str = "side", extra: tuple = (), witnessed: bool = True,
                min_step: float = MIN_STEP) -> list[str]:
    """A shading ramp for `base`: same material, `stops` brightnesses, dark to light.

    NOT `best_ladder` over a hue band. Maximising the smallest step is the right objective for
    "what can draw a line against this block" and the wrong one for a coat - unleashed over the
    brown band it proposed a lion of `spruce_log`, `cut_red_sandstone` and `yellow_wool`, which is a
    ladder with the largest possible steps and no lion in it. A coat ramp is one material seen at
    several brightnesses, so VALUE is the axis and everything else is a leash.

    So: put `stops` targets evenly along a window of `spread` luminance centred on the base, and at
    each target take the block nearest the base in CHROMA - colour with brightness divided out.
    Ties and near-ties go to the smaller luminance error, so a rung lands where it was asked for.

    The window is clipped to what the candidate set can actually reach, and rungs are forced
    distinct: a ramp that lands on one block twice reads as a flat band, and `polar_bear` shipped
    with `bone_block` listed at both index 0 and index 1.

    `extra` forces blocks into the candidate set - the animal's own coat blocks belong there, since
    a ramp that cannot include the colour the species is defined by is a ramp for another animal.
    """
    c = blocks.color(base, face)
    if c is None:
        raise ValueError(f"no colour recorded for {base}")
    cands = list(pool(tiers=tiers, face=face, witnessed=witnessed))
    have = {x[0] for x in cands}
    for n in (base, *extra):
        n = n.split(":")[-1]
        cc = blocks.color(n, face)
        if cc is not None and n not in have:
            hh, ss = hue_sat(cc)
            cands.append((n, tuple(cc), lum(cc), hh, ss))
            have.add(n)
    if len(cands) < stops:
        raise ValueError(f"only {len(cands)} candidate blocks for a {stops}-stop ramp")

    # 1. LEASH by chroma - only blocks that still read as this material. This is what stops a
    #    shading ramp turning into a rainbow. Widened until there is something to work with rather
    #    than raising: `jungle_log` sits in a corner of colour space with almost nothing beside it,
    #    and a hard failure there would mean a species could not be shaded at all.
    kin: list[tuple] = []
    drift = MAX_CHROMA_DRIFT
    while len(kin) < stops and drift <= 1.0:
        kin = [x for x in cands if _chroma_dist(c, x[1]) <= drift]
        drift *= 1.5
    if len(kin) < 2:
        raise ValueError(f"{base}: nothing close enough in colour to shade it with")

    # 2. WINDOW by value, centred on the base - OPTIONAL, and off by default. The chroma leash is
    #    the real constraint; a value window on top of it cuts off the bright end, and at the 110 it
    #    was first given it dropped `stripped_oak_log` out of the lion's ramp and collapsed the
    #    minimum step from 13 to 5. It is kept because one species genuinely wants it: species.yaml
    #    records that the polar bear needs "a NARROW ramp. Spanning tan to white made the shading
    #    paint the back snow." That is a deliberate per-species choice, not a default.
    window = kin
    if spread is not None:
        base_l = lum(c)
        reach_lo = min(x[2] for x in kin)
        reach_hi = max(x[2] for x in kin)
        half = spread / 2
        # SPEND THE WINDOW ON LUMINANCE THAT EXISTS. A white coat sits near the top of the range -
        # bone_block is 225 against a ceiling of 253 - so half a window above it is 28 of real
        # headroom and 32 of empty number line. Taken literally that left the polar bear a TWO-rung
        # ramp, which is not shading. What is unreachable on one side is spent on the other.
        #
        # This is a bounded slide, not the unbounded one that was tried first and removed: that
        # version kept the window's width no matter what and dragged a white animal down to
        # mid-grey. Here the window can only grow into tones the material actually has, and it
        # still cannot pull the coat past its own chroma leash.
        lo = base_l - half - max(0.0, (base_l + half) - reach_hi)
        hi = base_l + half + max(0.0, reach_lo - (base_l - half))
        narrowed = [x for x in kin if lo <= x[2] <= hi]
        if len(narrowed) >= 2:
            window = narrowed

    # 3. Inside the leash, MAXIMISE THE SMALLEST STEP. Picking each rung nearest to an evenly spaced
    #    target looks equivalent and is not: where candidates clump, consecutive targets grab two
    #    blocks a couple of luminance apart and the ramp quietly shortens - that is how the first
    #    version of this produced a polar bear with a 2.1 step. The objective and the gate
    #    `check_ramp` applies have to be the same quantity.
    anchor = next((x for x in window if x[0] == base.split(":")[-1]), None)
    if anchor is None:
        h, sat = hue_sat(c)
        anchor = (base.split(":")[-1], tuple(c), lum(c), h, sat)
        window = window + [anchor]

    # `stops` IS A MAXIMUM, NOT A TARGET. Measured, the brown wood families cannot supply five tones
    # more than 13 apart at any setting - they clump at 88/89/93 and leave holes elsewhere - while
    # stone reaches 38. Padding brown to five rungs is how `species.yaml` ended up with four rungs
    # inside a ten-luminance band. `blocks.ramp` already states the principle for duplicates: it is
    # "better to know the palette only had four usable rungs than to pretend it had six". This
    # applies it to rungs the eye cannot separate, which is the same failure one step less obvious.
    for n in range(stops, 1, -1):
        rungs, gap = anchored_ladder(window, n, anchor)
        if len(rungs) == n and gap >= min_step:
            return [r[0] for r in rungs]
    # Nothing clears the gate. Return the widest-stepped ladder there is and let `check_ramp` say
    # so - a caller that silently got two rungs would not know the material was the problem.
    rungs, _gap = anchored_ladder(window, stops, anchor)
    return [r[0] for r in rungs]


def check_ramp(ramp, *, face: str = "side", min_step: float = MIN_STEP) -> list[str]:
    """Problems with a hand-written ramp, worst first. Empty means it is honest.

    Three things go wrong and all three shipped in `species.yaml`:
      * a rung with no recorded colour - it cannot be reasoned about at all;
      * rungs OUT OF ORDER, which makes `coat.shade` paint the crevice tone onto a lit cell;
      * rungs closer than `min_step`, which is a shorter ladder wearing more blocks.
    """
    out = []
    ls = [luminance(n, face) for n in ramp]
    missing = [n for n, v in zip(ramp, ls) if v is None]
    if missing:
        out.append(f"no colour recorded for {', '.join(sorted(set(missing)))}")
        return out
    dupes = {n for n in ramp if ramp.count(n) > 1}
    if dupes:
        out.append(f"repeated rung(s): {', '.join(sorted(dupes))}")
    if any(ls[i + 1] < ls[i] for i in range(len(ls) - 1)):
        order = ", ".join(f"{n}={v:.0f}" for n, v in zip(ramp, ls))
        out.append(f"out of order (must run dark->light): {order}")
    srt = sorted(ls)
    gaps = [srt[i + 1] - srt[i] for i in range(len(srt) - 1)]
    if gaps and min(gaps) < min_step:
        pairs = [f"{a:.0f}/{b:.0f}" for a, b in zip(srt, srt[1:]) if b - a < min_step]
        out.append(f"rungs the eye cannot separate (min step {min(gaps):.1f} < {min_step:.0f}): "
                   + ", ".join(pairs))
    return out
