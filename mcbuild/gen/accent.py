"""WEATHERING: the accent tail that makes a voxel mass read as a material rather than a colour.

    over = accent.weather(hide, solid, "moss_block", origin=(ox, oy, oz))
    for cell, name in over.items():
        w.put(*cell, name)

WHY THIS IS NOT `coat.shade`. `shade` answers "where is the light" and paints a value ramp by form.
It is a LIGHT model and this repo already has a good one. This answers a different question - "what
has happened to this surface" - and the corpus says the second is where the gap is.

Measured across 31 outside builds, their sculptures carry 18.5% of their cells in accents beyond the
top three blocks against our 5.8%, at the same dominant share and the same zero detail blocks. But
the accents are NOT a light model: luminance correlates with ambient occlusion at r=-0.15 on their
best statue, which is nothing. They are local material events. The clearest single case is the
`Ancient knight statue`: 829 cells of `moss_block` at +11 luminance from the body - no tonal
contribution at all - sitting on cells whose UP face is open 80% of the time against 4% for the
down face. That is not shading. That is moss growing where rain lands, and it is the whole reason a
70%-one-block statue reads as weathered stone instead of as a grey shape.

FOUR THINGS IT HAS TO GET RIGHT, three of which this repo has already learned elsewhere.

DRIFTS, NEVER CONFETTI. The single most repeated lesson in this project. The deck soffit drew 215
grid runs of which 184 were one or two cells - "it is not a grid, it is confetti". The lowland
thicket's first build was 191 blobs of which 75% were one or two cells. Both had the same cause and
the same fix: THE NOISE BELONGS ON THE PATCH BOUNDARY, NOT ON ITS INTERIOR. Thresholding a noise
field per cell gives spatter; thresholding a smooth field and wobbling its EDGE gives a patch. The
corpus agrees from the other side - 59-91% of every accent's cells there live in blobs of 8 or more.
`min_blob` is the gate and it is asserted, because a confetti pass and a drift pass produce
identical block counts and identical audits.

EXPOSURE IS THE DRIVER, AND IT IS THE UP FACE. Not height - a statue's head is high and its
underarm is high, and only one of them collects moss. Not occlusion either, which is what a light
model would use. The measured signal on the knight is specifically whether the cell's UP face is
open, at 80% against a 26% surface average.

IT MUST NOT EAT THE FACE. The face-zone rule from the animal work applies unchanged: a pattern
placed across a skull buries the eye among a dozen identical cells, and this repo already shipped
that once - "the eye was the same block as the coat pattern". `forbid` is how a caller keeps
weathering off anything it has already decided.

AND IT PAINTS OVER A COAT, NOT UNDER IT. This returns an overlay keyed by cell, in the same shape
`coat.voronoi` and `coat.shade` return, so a generator applies it last and nothing about the coat
has to know it exists.
"""
from __future__ import annotations

import numpy as np

from .. import tone
from .canvas import hash01

# How far a weathering material may sit from the body in LUMINANCE. The knight's moss is +11 from
# its body block and contributes no tonal contrast at all - it is a MATERIAL event, and a block that
# also changes the value is doing shading's job badly. Measured against `stone`, this window admits
# `mossy_stone_bricks` (-7) and `mossy_cobblestone` (-11) and excludes `moss_block`, which is a
# saturated green on neutral grey and reads as paint rather than as weather. That was visible the
# moment it was rendered and is the reason this picker exists at all.
WEATHER_DLUM = 18.0

# And how far it may drift in COLOUR. There is a floor as well as a ceiling, and the floor matters:
# nearest-in-chroma alone picked `light_gray_wool` for `stone` (drift 0.046), which is not weather,
# it is the same grey in another material. Below the floor a pick adds nothing; above the ceiling it
# stops reading as the same object having aged.
#
# THE CEILING IS A DEFAULT, NOT A LAW, and it is worth being honest about why. The knight's own moss
# is 0.575 from its body - far outside this - and it works there, because that body
# (`cyan_terracotta`, 87/91/91) is already olive, so the moss extends a hue the statue has. Our
# elephant is neutral `stone`, and at the same drift `moss_block` read as green paint down the
# topline the moment it was rendered. One example is not a rule, so the default is the conservative
# pick and a caller that wants the bold one names it through `prefer`. That is a design decision.
WEATHER_CHROMA_MIN = 0.08
WEATHER_CHROMA = 0.30


def weathering_for(base: str, *, face: str = "side", prefer: tuple = (),
                   dlum: float = WEATHER_DLUM, max_chroma: float = WEATHER_CHROMA,
                   min_chroma: float = WEATHER_CHROMA_MIN, ranked: bool = False):
    """A material that reads as `base` weathered, chosen by measurement rather than by taste.

    Nearest in CHROMA among blocks close enough in value - so the pick is "the same stone, aged",
    not "a green block". `prefer` names blocks to try first if they qualify, for a design that has
    already decided its own vocabulary.

    Returns None when nothing qualifies, which is a real answer: not every material has a weathered
    form in this economy, and inventing one is how `moss_block` ends up painted on an elephant.
    `ranked=True` returns every candidate instead, nearest first, so a config can choose.
    """
    c = tone.blocks.color(base, face)
    if c is None:
        return None
    bl = tone.lum(c)
    ok = []
    for n, rgb, l, _h, _s in tone.pool(face=face):
        if n == base.split(":")[-1]:
            continue
        d = tone._chroma_dist(c, rgb)
        if abs(l - bl) <= dlum and min_chroma <= d <= max_chroma:
            ok.append((n, d))
    ok.sort(key=lambda t: t[1])
    if ranked:
        return [n for n, _d in ok]
    if not ok:
        return None
    by_name = {n for n, _d in ok}
    for p in prefer:
        if p.split(":")[-1] in by_name:
            return p.split(":")[-1]
    return ok[0][0]


def _smooth_field(shape, scale: float, seed: int, origin) -> np.ndarray:
    """Value noise on a lattice of side `scale`, trilinearly interpolated.

    Smooth is the entire point. A per-cell hash thresholded at 20% is 20% spatter; a smooth field
    thresholded at the same level is patches with soft edges, and the patches are what read.
    """
    oy, oz, ox = origin
    sy, sz, sx = shape
    gy = int(sy / scale) + 2
    gz = int(sz / scale) + 2
    gx = int(sx / scale) + 2
    lat = np.empty((gy + 1, gz + 1, gx + 1), float)
    for j in range(gy + 1):
        for k in range(gz + 1):
            for i in range(gx + 1):
                lat[j, k, i] = hash01(i, j, k, 977, seed)
    ys = (np.arange(sy) + oy) / scale
    zs = (np.arange(sz) + oz) / scale
    xs = (np.arange(sx) + ox) / scale
    # index into the lattice from the design's own origin, so a patch does not slide when the
    # canvas is cropped - the same reason `deckfloor` sets its coffer grid in world coordinates.
    def axis(v, n):
        i0 = np.floor(v).astype(int) % n
        f = v - np.floor(v)
        return i0, (f * f * (3 - 2 * f))          # smoothstep, so patch edges are not diamonds
    jy, fy = axis(ys, gy)
    kz, fz = axis(zs, gz)
    ix, fx = axis(xs, gx)
    out = np.zeros(shape, float)
    for dy in (0, 1):
        wy = (fy if dy else 1 - fy)[:, None, None]
        for dz in (0, 1):
            wz = (fz if dz else 1 - fz)[None, :, None]
            for dx in (0, 1):
                wx = (fx if dx else 1 - fx)[None, None, :]
                out += wy * wz * wx * lat[np.ix_(jy + dy, kz + dz, ix + dx)]
    return out


def up_open(solid: np.ndarray) -> np.ndarray:
    """True where the cell directly above is air. The measured driver, not height or occlusion."""
    above = np.zeros_like(solid)
    above[:-1] = solid[1:]
    return ~above


def weather(cells, solid: np.ndarray, material: str, *, origin=(0, 0, 0), coverage: float = 0.22,
            scale: float = 5.0, up_bias: float = 0.80, min_blob: int = 8, seed: int = 0,
            forbid=(), edge_noise: float = 0.35, bleed: float = 0.25) -> dict:
    """Drifts of `material` on the up-facing parts of a surface. Returns {(x, y, z): name}.

    coverage    share of eligible surface cells to reach, before the blob gate
    scale       average drift width in blocks
    up_bias     0..1. How much of the selection is decided by the up face being open. 0.80 is the
                knight's measured figure; 0 makes it a plain drift with no weather in it
    min_blob    a patch smaller than this is dropped rather than placed. This is the gate, and
                without it the pass is confetti with a good docstring
    edge_noise  per-cell wobble applied ONLY to the threshold, which moves the patch BOUNDARY.
                Raising it does not add spatter; it makes the coastline rougher
    bleed       chance a surface cell beside or below a weathered one is taken too, so a drift runs
                down a face instead of ending in a line along the top

    `cells` is the iterable of surface cells to consider (a coat's `hide`), in world coordinates.
    """
    cells = [tuple(c) for c in cells]
    if not cells or coverage <= 0:
        return {}
    banned = {tuple(c) for c in forbid}
    oy, oz, ox = origin[1], origin[2], origin[0]

    field = _smooth_field(solid.shape, scale, seed, (oy, oz, ox))
    up = up_open(solid)

    # score = smooth patch field, pulled up where the sky is open. The up term is a MULTIPLIER on
    # eligibility rather than an addition, so a downward face cannot collect moss just by sitting
    # in the middle of a patch.
    scored = []
    for (x, y, z) in cells:
        if (x, y, z) in banned:
            continue
        iy, iz, ix = y - oy, z - oz, x - ox
        if not (0 <= iy < solid.shape[0] and 0 <= iz < solid.shape[1] and 0 <= ix < solid.shape[2]):
            continue
        if not solid[iy, iz, ix]:
            continue
        f = field[iy, iz, ix]
        f += edge_noise * (hash01(x, y, z, 613, seed) - 0.5)
        lit = 1.0 if up[iy, iz, ix] else (1.0 - up_bias)
        scored.append(((x, y, z), f * lit))
    if not scored:
        return {}

    scored.sort(key=lambda t: -t[1])
    take = max(1, int(round(coverage * len(scored))))
    chosen = {c for c, _v in scored[:take]}

    # BLEED. Weather runs down a face; it does not stop dead at the course it landed on. The knight
    # measures 4% down-face against 80% up-face, so this is small by construction - enough to stop
    # a drift reading as a stripe painted along the topline, which is what the first render looked
    # like in profile. A bled cell must still be surface and still not be forbidden.
    if bleed > 0:
        surface = {c for c, _v in scored}
        for (x, y, z) in list(chosen):
            for d in ((0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + d[0], y + d[1], z + d[2])
                if q in surface and q not in chosen and hash01(*q, 811, seed) < bleed:
                    chosen.add(q)

    for c in _small_blobs(chosen, min_blob):
        chosen.discard(c)
    return {c: material for c in chosen}


def _small_blobs(chosen: set, min_blob: int) -> set:
    """Cells belonging to a 6-connected group smaller than `min_blob`.

    Face-connected, not 26-connected: two cells touching only at a corner do not read as one patch,
    which is the same 6-connectivity rule that broke the ear tips and the vine strands.
    """
    if min_blob <= 1:
        return set()
    seen, drop = set(), set()
    for start in chosen:
        if start in seen:
            continue
        group, stack = [], [start]
        seen.add(start)
        while stack:
            x, y, z = stack.pop()
            group.append((x, y, z))
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + d[0], y + d[1], z + d[2])
                if q in chosen and q not in seen:
                    seen.add(q)
                    stack.append(q)
        if len(group) < min_blob:
            drop.update(group)
    return drop


def blob_sizes(cells) -> list[int]:
    """6-connected group sizes of a cell set - what the drift gate is asserted on."""
    cells = {tuple(c) for c in cells}
    seen, out = set(), []
    for start in cells:
        if start in seen:
            continue
        n, stack = 0, [start]
        seen.add(start)
        while stack:
            x, y, z = stack.pop()
            n += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + d[0], y + d[1], z + d[2])
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
        out.append(n)
    return sorted(out, reverse=True)
