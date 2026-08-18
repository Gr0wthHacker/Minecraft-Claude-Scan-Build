"""Any four-legged animal, from a table of numbers.

    quadruped: legs, barrel, neck and head lofted along four spines, smoothed, then dressed.

An animal here is a PROFILE: a handful of proportions, four keyframe tables that say how each part's
section changes along its length, a coat, and which features it wears. `PROFILES` holds the ones built
so far; a new species is a dict, not a new generator.

    python -m mcbuild gen configs/<animal>.yaml       # params.profile: horse | deer | giraffe | ...

The build order is the load-bearing part, and it was learned the hard way:

    1. MASS      legs, body, neck, head - lofted, nothing thin, nothing coloured
    2. RELAX     cellular smoothing over that mass alone (`smooth.relax`)
    3. FEATURES  mane, ears, horns, tail - added AFTER, because the rule that shaves a one-block
                 pimple off a shoulder eats a horn whole
    4. FACE      eyes and muzzle, read off the SMOOTHED skin with `loft.surface_out`
    5. COAT      the pattern, painted over the finished shape

Two traps that are not obvious and cost several rebuilds each:

  * Smoothing WELDS legs together. Two leg surfaces facing each other across a narrow gap look
    exactly like a dent, so the fill pass closes it. `relax(forbid=...)` bars the air between them.
  * Every smoothness metric rewards thickening, so tuning on it alone inflates the animal one run at
    a time. Check `tools/proportions.py` against the real species; when they disagree, anatomy wins.
"""
from __future__ import annotations

from . import coat as coat_mod
from . import loft, smooth
from .canvas import Canvas
from .vertical import Ctx, World

AIRY = ("air", "cave_air", "void_air", "vine")
CARDINALS = {(1, 0): (0, 1), (-1, 0): (0, -1), (0, 1): (-1, 0), (0, -1): (1, 0)}

# Section keyframes shared by every species unless it overrides them. `t` runs 0->1 along the part.
BASE_KEYS = {
    # leg: (t from haunch to hoof, half-width). Flares into the body, narrows at the cannon bone.
    "leg": [[0.00, 1.60], [0.05, 0.90], [0.15, 0.15], [0.46, -0.30], [0.76, 0.05], [1.00, 0.40]],
    # body: (t from rump to chest, half-width delta, back height as a fraction of the hips->withers
    # rise; <0 dips below the hips, 1 is the withers). The drop between hips and withers is what
    # separates a giraffe from a horse, so it is expressed relative to those two and not in blocks.
    "body": [[0.00, -2.1, -0.26], [0.08, -1.0, -0.04], [0.22, -0.2, 0.18],
             [0.45, 0.0, 0.50], [0.72, 0.0, 1.00], [0.88, -0.4, 1.00], [1.00, -1.6, 0.74]],
    # neck: (t from shoulder to jaw, taper 1->0 between r0 and r1, extra flare in blocks).
    # Two numbers because a neck does both at once: it tapers along its length AND swells where it
    # meets the shoulder. Folding them into one delta cannot express that.
    "neck": [[0.00, 1.0, 1.9], [0.05, 1.0, 0.9], [0.15, 1.0, 0.0],
             [0.50, 0.5, 0.0], [1.00, 0.0, 0.0]],
    # head: (t from cranium to nose, half-width, vertical centre, half-height)
    "head": [[0.00, -1.00, 0.40, -0.20], [0.20, 0.00, 0.50, 0.15], [0.42, -0.05, 0.10, -0.10],
             [0.65, -0.50, -0.50, -0.45], [0.88, -0.85, -1.00, -0.70], [1.00, -0.95, -1.25, -0.80]],
}

QUADRUPED = {
    "under": None,
    "feet": None,               # world (x, y, z) the hooves stand on
    "look_at": None,            # world (x, y, z) it faces; snapped to the nearest cardinal
    "profile": None,            # a key of PROFILES; params below override whatever it sets
    # -- proportions (blocks). Check them with `python tools/proportions.py <design>`.
    "leg": 17, "hoof": 2, "leg_r": 1.9,
    "body_len": 22, "withers": 13, "hips": 8, "body_r": 4.9,
    "neck": 26, "neck_r0": 3.4, "neck_r1": 1.95, "neck_lean": 0.40,
    "head_len": 8, "head_r": 2.45,
    "section_n": 2.2,
    # -- features
    "mane": True,               # a ridge down the back of the neck
    "horns": "ossicone",        # ossicone | none
    "ears": True,
    "tail": "tassel",           # tassel | plain | none
    # -- palette and pattern
    "coat_pattern": "voronoi",  # voronoi (patches with grout) | blotches (soft) | plain
    "coat_block": "smooth_sandstone",
    "patch": "smooth_red_sandstone",
    "patch_alt": "cut_red_sandstone",
    "hoof_block": "dark_oak_wood",
    "dark": "black_wool",
    "muzzle": "bone_block",
    "patch_scale": 5.5, "grout": 0.85,
    # -- smoothing (see smooth.py; tune with tools/smoothness.py --sweep)
    "relax_rounds": 4, "relax_fill": 11, "relax_keep": 11,
    "keys": None,               # optional per-part keyframe overrides
    "seed": 0,
}

PROFILES = {
    # Height lives in the NECK, the back drops hard from withers to hips, legs are slender.
    "giraffe": {
        "leg": 17, "leg_r": 1.9, "body_len": 22, "withers": 10, "hips": 6, "body_r": 4.9,
        "neck": 26, "neck_r0": 3.4, "neck_r1": 1.95, "head_len": 8, "head_r": 2.45,
        "mane": True, "horns": "ossicone", "tail": "tassel", "coat_pattern": "voronoi",
        # Sandstone does not exist on this skyblock, so the coat is bone + acacia. Both are the
        # nearest cheap colours to the originals out of all 1193 real block colours, and the two
        # acacias are the same hue with different grain - tonal variety without colour noise.
        "coat_block": "bone_block",              # pale straw
        "patch": "acacia_planks",                # ochre
        "patch_alt": "stripped_acacia_log",
        "muzzle": "white_wool",                  # must read paler than a bone_block coat
    },
    # Deep chest, level back, short thick neck, heavy legs. A mane but no horns.
    "horse": {
        "leg": 16, "leg_r": 1.6, "body_len": 27, "withers": 10, "hips": 9, "body_r": 3.9,
        "neck": 12, "neck_r0": 3.0, "neck_r1": 2.2, "neck_lean": 0.55,
        "head_len": 10, "head_r": 2.2,
        "mane": True, "horns": "none", "tail": "plain", "coat_pattern": "plain",
        "coat_block": "brown_terracotta", "patch": "brown_terracotta",
    },
    # Light and short-bodied, neck carried high, no mane.
    "deer": {
        "leg": 12, "leg_r": 1.2, "body_len": 22, "withers": 8, "hips": 7, "body_r": 2.9,
        "neck": 8, "neck_r0": 2.2, "neck_r1": 1.5, "neck_lean": 0.5,
        "head_len": 7, "head_r": 1.7,
        "mane": False, "horns": "none", "tail": "plain", "coat_pattern": "blotches",
        "coat_block": "terracotta", "patch": "white_wool", "patch_scale": 3.0,
    },
}


def build_quadruped(cfg: dict, donors=None) -> Canvas:
    p = dict(QUADRUPED)
    if cfg.get("profile"):
        if cfg["profile"] not in PROFILES:
            raise ValueError(f"unknown profile {cfg['profile']!r}; have {sorted(PROFILES)}")
        p.update(PROFILES[cfg["profile"]])
    p.update(cfg)                                        # explicit params always win
    for k in ("feet", "look_at"):
        if p.get(k) is None:
            raise ValueError(f"quadruped needs params.{k}")
    keys = {**BASE_KEYS, **{k: [list(r) for r in v] for k, v in (p.get("keys") or {}).items()}}

    ctx = Ctx(p["under"]) if p.get("under") else None
    fx, fy, fz = (int(v) for v in p["feet"])
    tx, _ty, tz = (int(v) for v in p["look_at"])
    dx, dz = tx - fx, tz - fz
    f = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dz) else (0, 1 if dz > 0 else -1)
    s = CARDINALS[f]

    # 1. mass
    hide: set = set()
    accent: dict = {}
    belly = fy + int(p["leg"])
    legs_only: set = set()
    hoofs = _legs(legs_only, ctx, fx, fy, fz, f, s, p, keys)
    hide |= legs_only
    shoulder = _body(hide, fx, belly, fz, f, s, p, keys)
    neck_top, neck_r = _neck(hide, shoulder, f, s, p, keys)
    head_at = _head(hide, neck_top, neck_r, f, s, p, keys)

    # 2. relax, with the air between the legs barred from filling
    if int(p["relax_rounds"]):
        # The legs are PROTECTED from shaving. `keep` counts solid neighbours, and a slender leg
        # section simply does not have that many - on a deer (leg_r 1.2) relax ate three of the four
        # legs outright. Smoothing parameters tuned on one animal are too aggressive for a smaller
        # one, and a limb that is thin BY DESIGN must not be judged by the same rule as a shoulder.
        hide = smooth.relax(hide, rounds=int(p["relax_rounds"]), fill=int(p["relax_fill"]),
                            keep=int(p["relax_keep"]), protect=legs_only,
                            forbid=_leg_gap(hoofs, belly, float(p["leg_r"]), keys))

    # 3. features, 4. face, 5. coat
    for (lx, lz, gy, lrad) in hoofs:
        for c in hide:
            if gy <= c[1] < gy + int(p["hoof"]) and abs(c[0] - lx) <= lrad and abs(c[2] - lz) <= lrad:
                accent[c] = p["hoof_block"]
    if p["mane"]:
        _mane(hide, shoulder, f, s, p)
    _crown(hide, accent, head_at, f, s, p)
    _face(hide, accent, head_at, f, s, p)
    if p["tail"] != "none":
        _tail(hide, accent, fx, belly, fz, f, s, p)

    skin = _coat(hide, p)
    w = World()
    for cell in sorted(hide):
        w.put(*cell, accent.get(cell) or skin.get(cell, p["coat_block"]))

    hi = max(y for (_x, y, _z) in hide)
    hits = 0 if ctx is None else sum(1 for c in hide if ctx.name_at(*c) not in AIRY)
    return w.canvas({"kind": p.get("profile") or "quadruped", "feet": [fx, fy, fz],
                     "facing": list(f), "height": hi - fy, "top_y": hi,
                     "neck_top_y": neck_top[1], "collisions": hits})


def _coat(hide, p) -> dict:
    kind = p["coat_pattern"]
    if kind == "plain":
        return {}
    if kind == "blotches":
        return coat_mod.blotches(hide, p["patch"], p["coat_block"],
                                 scale=float(p["patch_scale"]), seed=int(p["seed"]))
    return coat_mod.voronoi(hide, p["patch"], p["coat_block"], scale=float(p["patch_scale"]),
                            grout_width=float(p["grout"]), seed=int(p["seed"]),
                            tones=[p["patch"], p["patch_alt"]])


def _leg_gap(hoofs, belly, leg_r, keys) -> set:
    """The air between the legs, which smoothing must not fill.

    Left alone the fill pass sees two leg surfaces facing each other across a narrow gap as a dent
    and welds them: the giraffe's four legs merged into one part for the whole lower half, measuring
    11 blocks wide against an anatomical 3.

    TWO things have to be right or this cure is worse than the disease. The reach must cover the
    leg's WIDEST section, not its nominal radius - the haunch flare is the widest part, and banning
    cells inside it made relax carve the top off each leg. On a deer that severed a leg from the body
    outright. And the band must stop below the haunch, where the legs are meant to merge anyway.
    """
    flare = max(d for _t, d in keys["leg"])
    reach = leg_r + flare + 0.6
    gap = set()
    lowest = min(g for (_a, _b, g, _c) in hoofs) - 1
    span = int(reach) + 5
    top = max(lowest + 1, belly - int(round(flare)) - 2)
    for (lx, lz, _gy, _r) in hoofs:
        for y in range(lowest, top):
            for dx in range(-span, span + 1):
                for dz in range(-span, span + 1):
                    c = (lx + dx, y, lz + dz)
                    if all(((c[0] - ax) ** 2 + (c[2] - az) ** 2) ** 0.5 > reach
                           for (ax, az, _g, _rr) in hoofs):
                        gap.add(c)
    return gap


# ------------------------------------------------------------------ mass

def _legs(hide, ctx, fx, fy, fz, f, s, p, keys) -> list:
    """Four legs, each finding its OWN ground - terrain rolls, and a level hoof line either floats on
    the high side or buries its feet on the low.

    The top flares and carries four courses UP INSIDE the barrel, so a leg meets the body as a haunch
    rather than a post pushed into a wall; relax then blends that corner."""
    bl, br, lr = int(p["body_len"]), float(p["body_r"]), float(p["leg_r"])
    n = float(p["section_n"])
    top = fy + int(p["leg"])
    KEYS = [[t, lr + d] for t, d in keys["leg"]]
    out = []
    for along, side in ((bl // 2 - 3, 1), (bl // 2 - 3, -1), (-(bl // 2 - 3), 1), (-(bl // 2 - 3), -1)):
        off = max(1, round(br - lr - 0.4))               # tucked under the barrel, not splayed past it
        lx = int(fx + f[0] * along + s[0] * off * side)
        lz = int(fz + f[1] * along + s[1] * off * side)
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(lx, probe, lz) not in AIRY:
                    hoof = probe + 1
                    break
        span = max(1, top - hoof)
        for y in range(hoof, top + 4):
            (r,) = loft.lerp(KEYS, max(0.0, 1.0 - (y - hoof) / span))
            loft.disc(hide, lx, y, lz, f, s, r, r, n)
        out.append((lx, lz, hoof, lr + 0.8))
    return out


def _body(hide, fx, belly, fz, f, s, p, keys) -> tuple:
    """A barrel whose back line and belly line are set independently, so it deepens toward the chest.

    The withers-to-hips drop is what separates a giraffe from a horse; it is a profile number."""
    bl, br = int(p["body_len"]), float(p["body_r"])
    withers, hips = float(p["withers"]), float(p["hips"])
    n = float(p["section_n"])
    half = bl // 2
    KEYS = [[t, br + dw, hips + (withers - hips) * hh] for t, dw, hh in keys["body"]]
    for a in range(-half, bl - half):
        rb, back = loft.lerp(KEYS, (a + half) / max(1, bl - 1))
        loft.rib(hide, fx + f[0] * a, belly + back / 2.0, fz + f[1] * a, f, s,
                 rb, back / 2.0, n, squash_lo=1.12)
    return (fx + f[0] * (half - 2), belly + withers - 1.0, fz + f[1] * (half - 2))


def _neck(hide, shoulder, f, s, p, keys):
    """Tapers smoothly and leans forward. The lean is carried as a FLOAT and the section re-centred
    every course, so the neck is a clean diagonal rather than a staircase."""
    sx, sy, sz = shoulder
    ln, r0, r1 = int(p["neck"]), float(p["neck_r0"]), float(p["neck_r1"])
    n, lean = float(p["section_n"]), float(p["neck_lean"])
    KEYS = [[t, r1 + (r0 - r1) * taper + flare] for t, taper, flare in keys["neck"]]
    x, z = float(sx), float(sz)
    top = (sx, sy, sz)
    for k in range(-3, ln):                              # starts inside the shoulder: no seam
        (r,) = loft.lerp(KEYS, max(0.0, k / max(1, ln - 1)))
        x += f[0] * lean
        z += f[1] * lean
        loft.disc(hide, x, sy + k, z, f, s, r, r * 0.94, n)
        top = (x, sy + k, z)
    return top, loft.lerp(KEYS, 1.0)[0]


def _head(hide, top, neck_r, f, s, p, keys) -> tuple:
    """The skull, lofted along the muzzle. Starts at the NECK's radius so the join is continuous - an
    early version stepped from 9 cells to 34 in one course and read as a pinhead on a stick."""
    hx, hy, hz = top
    hl, hr, n = int(p["head_len"]), float(p["head_r"]), float(p["section_n"])
    KEYS = [[t, max(neck_r, hr + dw) if t == 0.0 else hr + dw, dy, hr + dh]
            for t, dw, dy, dh in keys["head"]]
    brow = (hx, hz)
    for i in range(hl):
        t = i / max(1, hl - 1)
        rb, dy, rv = loft.lerp(KEYS, t)
        cx, cz = hx + f[0] * i, hz + f[1] * i
        loft.rib(hide, cx, hy + dy, cz, f, s, rb, rv, n, squash_lo=0.92)
        if abs(t - 0.42) < 0.5 / hl:
            brow = (cx, cz)
    return (hx, hy, hz, hl, hr, brow[0], brow[1])


# ------------------------------------------------------------------ features (post-relax)

def _mane(hide, shoulder, f, s, p):
    """A ridge behind whatever the neck surface actually IS. Relax shrinks the neck, so a mane placed
    at the pre-relax radius hangs in the air - it came out as seven floating fragments once."""
    sx, sy, sz = shoulder
    reach = int(p["neck_r0"]) + 3
    for k in range(int(p["neck"]) - 1):
        y = int(round(sy + k))
        back = None
        for d in range(reach, 0, -1):
            probe = (int(round(sx - f[0] * d)), y, int(round(sz - f[1] * d)))
            if probe in hide:
                back = probe
                break
        if back is not None:
            hide.add((int(back[0] - f[0]), y, int(back[2] - f[1])))


def _crown(hide, accent, head_at, f, s, p):
    """Ears and horns, GROWN OUT OF the smoothed skull rather than placed at a guessed radius."""
    hx, hy, hz, _hl, hr, _bx, _bz = head_at
    for side in (1, -1):
        if p["ears"]:
            for a in (-1, 0, 1):
                _c, b0 = loft.surface_out(hide, hx + f[0] * (a + 1), hy + 1, hz + f[1] * (a + 1),
                                          s[0] * side, s[1] * side, int(hr) + 2)
                if not b0:
                    continue
                # a CONTIGUOUS outward run at one height: sweeping it back and down as it went out
                # made consecutive cells diagonal neighbours, which is not 6-connected - tips broke off
                for dyk in (0, 1):
                    if dyk and a == 1:
                        continue
                    for b in range(1, 3 if a != 1 else 2):
                        c = (int(round(hx + f[0] * (a + 1) + s[0] * (b0 + b) * side)),
                             int(round(hy + 1 + dyk)),
                             int(round(hz + f[1] * (a + 1) + s[1] * (b0 + b) * side)))
                        hide.add(c)
                        accent[c] = p["coat_block"]
        if p["horns"] == "ossicone":
            ox = int(round(hx + f[0] * 2 + s[0] * 1.2 * side))
            oz = int(round(hz + f[1] * 2 + s[1] * 1.2 * side))
            top = loft.crest(hide, ox, oz)
            if top is None:
                continue
            for k in (1, 2):
                hide.add((ox, top + k, oz))
                accent[(ox, top + k, oz)] = p["coat_block"]
            hide.add((ox, top + 3, oz))
            accent[(ox, top + 3, oz)] = p["dark"]


def _face(hide, accent, head_at, f, s, p):
    """Pale muzzle, nostrils and eyes - read off the SMOOTHED skin, never assumed."""
    hx, hy, hz, hl, hr, ax, az = head_at
    nose_x = int(round(hx + f[0] * (hl - 1)))
    nose_z = int(round(hz + f[1] * (hl - 1)))
    for c in list(hide):
        along = (c[0] - hx) * f[0] + (c[2] - hz) * f[1]
        if along >= hl - 3 and c[1] <= hy:               # the LOWER front only: a pale lip, not a slab
            accent[c] = p["muzzle"]
    for b in (-1, 0, 1):
        for dy in (-1, 0):
            c = (int(nose_x + s[0] * b), int(round(hy + dy - 1)), int(nose_z + s[1] * b))
            if c in hide and abs(b) + abs(dy) < 2:
                accent[c] = p["dark"]
    for side in (1, -1):
        # a dark bead on the OUTER skin of the brow. Assuming a width merged both eyes into a band
        # right across the face - a bandit mask - because the brow is only about five cells wide.
        for k in (0, 1):
            edge, _b = loft.surface_out(hide, ax, hy + k, az, s[0] * side, s[1] * side, int(hr) + 2)
            if edge is None:
                continue
            accent[edge] = p["dark"]
            for dy in (-1, 2):
                ring = (edge[0], int(round(hy + dy)), edge[2])
                if ring in hide and ring not in accent:
                    accent[ring] = p["muzzle"]


def _tail(hide, accent, fx, belly, fz, f, s, p):
    """One block wide a tail is invisible - the rump slice held exactly 11 cells and rendered as
    nothing. Two wide at the root, and a dark switch on the end."""
    half = int(p["body_len"]) // 2
    x = int(fx - f[0] * (half + 1))
    z = int(fz - f[1] * (half + 1))
    top = int(belly + int(p["hips"]) - 2)
    tassel = p["tail"] == "tassel"
    # SCALE the tail with the animal. At a fixed 13 blocks it was longer than a deer's legs, ran into
    # the ground and broke the model into two components. Every feature measured in absolute blocks
    # has this bug latent in it - the giraffe just happened to be the size the constant was tuned on.
    length = max(4, int(round(0.75 * int(p["leg"]))))
    switch = max(2, int(round(length * 0.25)))
    for k in range(length):
        cells = [(x, top - k, z)]
        if k < max(2, length // 4):
            cells.append((int(x - f[0]), top - k, int(z - f[1])))
        if tassel and length - switch <= k < length - 1:
            cells += [(int(x + s[0] * b), top - k, int(z + s[1] * b)) for b in (-1, 1)]
        for c in cells:
            hide.add(c)
            if k >= length - switch:
                accent[c] = p["dark"]
