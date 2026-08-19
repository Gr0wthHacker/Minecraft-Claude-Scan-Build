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
from . import anatomy, loft, smooth, taxonomy
from .canvas import Canvas
from .vertical import Ctx, World

AIRY = ("air", "cave_air", "void_air", "vine")
CARDINALS = {(1, 0): (0, 1), (-1, 0): (0, -1), (0, 1): (-1, 0), (0, -1): (1, 0)}

# Section keyframes shared by every species unless it overrides them. `t` runs 0->1 along the part.
BASE_KEYS = {
    # leg: (t from haunch to hoof, half-width). Flares into the body, narrows at the cannon bone.
    "leg": [[0.00, 1.60], [0.05, 0.90], [0.15, 0.15], [0.46, -0.30], [0.76, 0.05], [1.00, 0.40]],
    # body: (t from rump to chest, half-width delta, back height as a fraction of the hips->withers
    # rise, DEPTH taper as a fraction of body depth). The drop between hips and withers is what
    # separates a giraffe from a horse, so it is expressed relative to those two and not in blocks.
    #
    # THE FOURTH COLUMN IS LOAD-BEARING and was missing. Expressing the back line only as a fraction
    # of the hips->withers rise means it VANISHES for any level-backed animal: `withers - hips` is
    # 0 blocks for an ursid or a caviomorph (hip_drop 1.00) and 1 block for a felid, so keyframes
    # spanning "-0.26 to 1.00 of that rise" quantised to nothing and every barrel came out a
    # flat-topped, flat-bottomed, square-ended prism. Measured back-line range over ~35 courses:
    # bear 3, capybara 3, jaguar 3, elephant 4 - against the giraffe's 15, the only family whose
    # hip_drop (0.60) gave the term anything to work with.
    #
    # So the ENDS taper as a fraction of the body's own DEPTH, which no family has zero of. It
    # shortens the section at both ends, and `rib` centres on floor + back/2 - so it lifts the belly
    # and drops the back together, which is what rounds an end rather than merely lowering it.
    "body": [[0.00, -2.1, -0.26, -0.34], [0.08, -1.0, -0.04, -0.16], [0.22, -0.2, 0.18, -0.04],
             [0.45, 0.0, 0.50, 0.0], [0.72, 0.0, 1.00, 0.0], [0.88, -0.4, 1.00, -0.10],
             [1.00, -1.6, 0.74, -0.30]],
    # neck: (t from shoulder to jaw, taper 1->0 between r0 and r1, extra flare in blocks).
    # Two numbers because a neck does both at once: it tapers along its length AND swells where it
    # meets the shoulder. Folding them into one delta cannot express that.
    "neck": [[0.00, 1.0, 1.9], [0.05, 1.0, 0.9], [0.15, 1.0, 0.0],
             [0.50, 0.5, 0.0], [1.00, 0.0, 0.0]],
    # head: (t from cranium to nose, half-width, vertical centre, half-height)
    "head": [[0.00, -1.00, 0.40, -0.20], [0.20, 0.00, 0.50, 0.15], [0.42, -0.05, 0.10, -0.10],
             [0.65, -0.50, -0.50, -0.45], [0.88, -0.85, -1.00, -0.70], [1.00, -0.95, -1.25, -0.80]],
}

# A pose is a set of MULTIPLIERS on the skeleton, not a separate build path. Front and hind legs
# shorten independently, the belly line tilts, and the neck can be re-aimed - which between them
# cover every resting posture a four-legged animal actually takes.
#
#   fore / hind    leg length as a fraction of standing
#   fold           extra girth on a shortened leg: a folded limb is bunched, not a shrunken post
#   pitch          belly rise from rump to chest, as a fraction of standing leg length. Positive is
#                  head-up (sitting); negative is head-down (drinking, stalking downhill).
#   lean / from    overrides on the neck's forward lean and where it leaves the barrel
#   drop           head lowered by this fraction of the neck's length (grazing, stalking)
POSES = {
    "standing": {},
    # haunches folded under, forelegs straight, chest lifted - a cat or a dog at rest, alert
    "sitting": {"fore": 1.00, "hind": 0.32, "fold": 1.25, "pitch": 0.42, "from": 0.92},
    # all four folded, belly close to the ground, head still up. A resting big cat.
    "couchant": {"fore": 0.26, "hind": 0.22, "fold": 1.35, "pitch": 0.05, "from": 0.88},
    # everything lowered and lengthened, head carried low and forward - hunting
    "prowling": {"fore": 0.74, "hind": 0.70, "fold": 1.12, "pitch": -0.05, "from": 0.72,
                 "lean": 1.35, "drop": 0.30},
    # head down to the ground; the rest stands normally
    "grazing": {"drop": 1.15, "lean": 1.30, "from": 0.80},
}

QUADRUPED = {
    "under": None,
    "feet": None,               # world (x, y, z) the hooves stand on
    "look_at": None,            # world (x, y, z) it faces; snapped to the nearest cardinal
    "profile": None,            # a key of PROFILES; params below override whatever it sets
    "pose": "standing",         # a key of POSES - see `python tools/stance.py` to choose one
    "scale": 1.0,               # multiplies every block dimension. `python tools/scale.py <species>`
                                # says how big this animal has to be before its features can exist
    # -- proportions (blocks). Check them with `python tools/proportions.py <design>`.
    "leg": 17, "hoof": 2, "leg_r": 1.9,
    "body_len": 22, "withers": 13, "hips": 8, "body_r": 4.9,
    "neck": 26, "neck_r0": 3.4, "neck_r1": 1.95, "neck_lean": 0.40,
    "neck_from": 1.0,           # where the neck leaves the barrel, as a fraction of the withers.
                                # 1.0 is the top of the shoulder (a giraffe); a cat is nearer 0.75,
                                # which is what carries its head level with its back instead of above it.
    "head_len": 8, "head_r": 2.45,
    "section_n": 2.2,
    # -- features
    "mane": True,               # a ridge down the back of the neck
    "mane_volume": 0.0,         # a lion's mane is a COLLAR OF VOLUME, not a ridge. Without it a lion
                                # is a jaguar - the two built 0.032 apart on silhouette, which is to
                                # say identical. This is the feature that separates them.
    "hump": 0.0,                # shoulder hump as a fraction of body depth (bear, bison)
    "horns": "ossicone",        # ossicone | none
    "ears": True,
    "ear_size": 1.0,            # multiplier on ear reach and height
    # PER-FAMILY GEOMETRY. A shared loft with different numbers builds one animal five times; these
    # pick the structure that actually separates the families. See `anatomy.py`.
    "legs_kind": "cursorial",   # digitigrade | plantigrade | columnar | stubby | cursorial
    "head_kind": "tapered",     # rounded | broad | domed | blunt | tapered
    # Deliberate asymmetry. Four legs in identical phase and a head aimed straight down the spine is
    # what makes a statue read as planted rather than alive - no animal stands like that. Both are
    # opt-in and both are RECORDED, so the rubric relaxes its symmetry expectation by exactly as much
    # as was asked for rather than penalising the thing that makes the animal look real.
    "leg_phase": 0,             # blocks to advance one leg of each pair along the body axis
    "head_turn": 0,             # blocks to swing the head off the spine
    "tail": "tassel",           # tassel | plain | long (a cat's) | none
    "tail_len": 0.75,           # `long` only: length as a fraction of body length
    "trunk": 0.0,               # length as a multiple of head length; 0 = none. An elephant's trunk
                                # is the same sweep as a cat's tail, hung off the face instead of the
                                # rump - which is why it needed no new machinery, only a new anchor.
    # -- palette and pattern
    "coat_pattern": "voronoi",  # voronoi | blotches | rosettes | shaded | plain
    "coat_ramp": None,          # `shaded` only: blocks dark -> light. Shading by FORM is what makes
                                # a big single-colour animal read as a sculpture instead of a blob.
    "shade_strength": 1.0,
    "belly_block": None,        # pale underside; None leaves the coat alone
    "belly_frac": 0.30,         # share of the body's depth counted as underside
    "coat_block": "smooth_sandstone",
    "patch": "smooth_red_sandstone",
    "patch_alt": "cut_red_sandstone",
    "hoof_block": "dark_oak_wood",
    "dark": "black_wool",
    "muzzle": "bone_block",
    "patch_scale": 5.5, "grout": 0.85,
    # rosettes only: ring radius / band width / how much of each ring is left open
    "ring_radius": 0.60, "ring_thickness": 0.34, "ring_broken": 0.34,
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
    # A jaguar is the giraffe's opposite in every dimension: LONGER THAN IT IS TALL, head carried
    # level with the back on a short thick neck, heavy forequarters, and a tail as long as the body.
    # The rosette coat is what separates it from a leopard - broken rings, not solid spots.
    "jaguar": {
        "leg": 10, "leg_r": 1.8, "hoof": 0,
        "body_len": 26, "withers": 9, "hips": 8, "body_r": 3.6,
        "neck": 2, "neck_r0": 3.4, "neck_r1": 2.9, "neck_lean": 0.9, "neck_from": 0.78,
        "head_len": 7, "head_r": 2.8,
        "mane": False, "horns": "none", "ears": True, "tail": "long", "tail_len": 0.62,
        "coat_pattern": "rosettes", "patch_scale": 4.6,
        # Plain, low-noise blocks only - a statue's coat wants flat colour, and every near-miss the
        # colour search offers here is a trap: bee_nest carries a face texture and bee states,
        # copper_bulb is a light source, bamboo postdates the server. The oak/jungle family is the
        # cleanest golden tan the game has. The rings are BLACK because a jaguar's rosettes are
        # near-black; in dark_oak they were a brown ring on a brown coat, which at any distance is
        # just noise - the contrast is what makes them read as rings rather than as speckle.
        "coat_block": "stripped_oak_wood",       # golden tan
        "patch": "black_wool",                   # the rosette rings
        "patch_alt": "stripped_jungle_log",      # rosette centres: warmer, a shade darker
        "belly_block": "bone_block", "belly_frac": 0.20,
        "muzzle": "bone_block", "dark": "black_wool", "hoof_block": "dark_oak_wood",
        "section_n": 2.1,
    },
    # The ideal voxel animal: limbs so heavy relative to its height that nothing about it is too
    # fine to build. Viable at 30 blocks where a giraffe needs 59.
    "elephant": {
        "leg": 16, "leg_r": 3.0, "hoof": 0,
        "body_len": 28, "withers": 13, "hips": 12, "body_r": 6.6,
        "neck": 3, "neck_r0": 5.2, "neck_r1": 4.6, "neck_lean": 0.7, "neck_from": 0.86,
        "head_len": 8, "head_r": 4.2, "trunk": 1.6,
        # the ears are the most identifying thing about an elephant - bigger than its head
        "mane": False, "horns": "none", "ears": True, "ear_size": 2.6,
        "tail": "plain", "tail_len": 0.4,
        # An elephant has no markings at all, so ALL of its quality has to come from form. Shaded
        # by exposure: creases and the belly fall to deepslate, the back and the top of the head
        # come up to smooth_stone. Flat cobblestone made a perfectly-proportioned grey blob.
        "coat_pattern": "shaded",
        "coat_ramp": ["deepslate", "tuff", "stone", "andesite", "smooth_stone"],
        "shade_strength": 1.15,
        "coat_block": "stone", "patch": "stone", "patch_alt": "andesite",
        "muzzle": "tuff", "dark": "black_wool", "hoof_block": "andesite",
        "belly_block": None,        "section_n": 2.0,
        # smoothing chosen by `tools/refine.py`, which maximises the RUBRIC TOTAL. Sweeping
        # smoothness alone made this animal fatter and better-surfaced and worse overall (elephant); the defaults were tuned on a giraffe
        "relax_rounds": 4, "relax_fill": 11, "relax_keep": 11,
    },
    # Heavy forequarters, short thick neck, small round ears. Sits like a person.
    "bear": {
        "leg": 11, "leg_r": 1.6, "hoof": 0,
        "body_len": 20, "withers": 8, "hips": 8, "body_r": 3.2,
        "neck": 2, "neck_r0": 2.8, "neck_r1": 2.5, "neck_lean": 0.7, "neck_from": 1.0,
        "head_len": 6, "head_r": 3.4,
        "mane": False, "horns": "none", "ears": True, "tail": "plain", "tail_len": 0.15,
        # A bear is one colour, so like the elephant all its quality is form. Five browns from
        # dark_oak in the creases to coarse_dirt along the lit back - a range wide enough to model
        # the shoulders without ever looking painted.
        "coat_pattern": "shaded",
        "coat_ramp": ["dark_oak_planks", "stripped_dark_oak_wood", "mangrove_wood",
                      "spruce_planks", "coarse_dirt"],
        "shade_strength": 1.1, "patch_scale": 7.0,
        "coat_block": "mangrove_wood", "patch": "mangrove_wood",
        "patch_alt": "stripped_dark_oak_wood", "muzzle": "oak_log",
        "dark": "black_wool", "hoof_block": "black_wool",
        "belly_block": None,        "section_n": 2.4,
        # smoothing chosen by `tools/refine.py`, which maximises the RUBRIC TOTAL. Sweeping
        # smoothness alone made this animal fatter and better-surfaced and worse overall (bear); the defaults were tuned on a giraffe
        "relax_rounds": 5, "relax_fill": 12, "relax_keep": 11,
    },
    # Barely any neck at all, a blunt head and a barrel on short legs - the smallest thing here that
    # still reads as an animal, and the right scale for something you come across rather than see.
    "capybara": {
        "leg": 6, "leg_r": 1.0, "hoof": 0,
        "body_len": 17, "withers": 5, "hips": 5, "body_r": 2.9,
        "neck": 1, "neck_r0": 2.4, "neck_r1": 2.2, "neck_lean": 0.6, "neck_from": 0.92,
        "head_len": 5, "head_r": 2.1,
        "mane": False, "horns": "none", "ears": True, "tail": "none",
        "coat_pattern": "shaded",
        "coat_ramp": ["spruce_planks", "coarse_dirt", "dirt", "jungle_log", "stripped_jungle_log"],
        "shade_strength": 1.1,
        "coat_block": "jungle_log", "patch": "jungle_log", "patch_alt": "stripped_jungle_log",
        "muzzle": "stripped_jungle_log", "dark": "black_wool", "hoof_block": "black_wool",
        "belly_block": None,        "section_n": 2.0,
        # smoothing swept per animal (capybara); the defaults were tuned on a giraffe
        "relax_rounds": 5, "relax_fill": 10, "relax_keep": 11,
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
        name = cfg["profile"]
        # Prefer the TAXONOMY: proportions come from the family table x the species height, so the
        # build is correct by construction. `PROFILES` is the older hand-tuned form, kept only for
        # anything not yet moved across.
        if name in taxonomy.species():
            p.update(taxonomy.resolve(name))
        elif name in PROFILES:
            p.update(PROFILES[name])
        else:
            raise ValueError(f"unknown profile {name!r}; have "
                             f"{sorted(set(taxonomy.species()) | set(PROFILES))}")
    p.update(cfg)                                        # explicit params always win
    for k in ("feet", "look_at"):
        if p.get(k) is None:
            raise ValueError(f"quadruped needs params.{k}")
    # SCALE every linear dimension together. Scaling only some of them changes the animal's
    # proportions, which is a different operation and one the audit would rightly complain about.
    sc = float(p.get("scale", 1.0))
    if abs(sc - 1.0) > 1e-6:
        for k in ("leg", "body_len", "withers", "hips", "neck", "head_len"):
            p[k] = max(1, int(round(float(p[k]) * sc)))
        for k in ("leg_r", "body_r", "neck_r0", "neck_r1", "head_r", "patch_scale"):
            p[k] = float(p[k]) * sc
        p["hoof"] = max(0, int(round(float(p["hoof"]) * sc)))
    keys = {**BASE_KEYS, **{k: [list(r) for r in v] for k, v in (p.get("keys") or {}).items()}}
    if p.get("pose") not in POSES:
        raise ValueError(f"unknown pose {p.get('pose')!r}; have {sorted(POSES)}")
    pose = POSES[p["pose"]]

    ctx = Ctx(p["under"]) if p.get("under") else None
    fx, fy, fz = (int(v) for v in p["feet"])
    tx, _ty, tz = (int(v) for v in p["look_at"])
    dx, dz = tx - fx, tz - fz
    f = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dz) else (0, 1 if dz > 0 else -1)
    s = CARDINALS[f]

    # 1. mass
    hide: set = set()
    accent: dict = {}
    legs_only: set = set()
    hoofs = _legs(legs_only, ctx, fx, fy, fz, f, s, p, keys, pose)
    hide |= legs_only
    belly = fy + int(p["leg"])
    # The belly line is derived from where the legs actually END - it is not a free parameter.
    # Shortening a leg without lowering the body over it leaves the leg hanging in the air, which is
    # exactly what the first sitting jaguar did: four detached stumps under a floating barrel.
    rump = fy + max(2, int(round(int(p["leg"]) * float(pose.get("hind", 1.0)))))
    chest = fy + max(2, int(round(int(p["leg"]) * float(pose.get("fore", 1.0)))))
    shoulder = _body(hide, fx, (rump, chest), fz, f, s, p, keys, pose)
    belly = min(rump, chest)
    neck_top, neck_r = _neck(hide, shoulder, f, s, p, keys, pose)
    turn = int(p.get("head_turn", 0) or 0)
    if turn:
        neck_top = (neck_top[0] + s[0] * turn, neck_top[1], neck_top[2] + s[1] * turn)
    head_at = anatomy.head(hide, neck_top, neck_r, f, s, p, p.get("head_kind", "tapered"))

    # 2. relax, with the air between the legs barred from filling
    if int(p["relax_rounds"]):
        # The legs are PROTECTED from shaving. `keep` counts solid neighbours, and a slender leg
        # section simply does not have that many - on a deer (leg_r 1.2) relax ate three of the four
        # legs outright. Smoothing parameters tuned on one animal are too aggressive for a smaller
        # one, and a limb that is thin BY DESIGN must not be judged by the same rule as a shoulder.
        hide = smooth.relax(hide, rounds=int(p["relax_rounds"]), fill=int(p["relax_fill"]),
                            keep=int(p["relax_keep"]), protect=legs_only,
                            forbid=_leg_gap(hoofs, belly,
                                            float(p["leg_r"]) * float(pose.get("fold", 1.0)), keys))

    # 3. features, 4. face, 5. coat
    for (lx, lz, gy, lrad) in hoofs:
        for c in hide:
            if gy <= c[1] < gy + int(p["hoof"]) and abs(c[0] - lx) <= lrad and abs(c[2] - lz) <= lrad:
                accent[c] = p["hoof_block"]
    # RECORD what each feature actually contributed. The rubric used to assert most features were
    # present because it had no way to look - seven of its fourteen checks were hardcoded True, so
    # a feature shaved off by relax still scored full marks. Counting cells at the moment of
    # emission is the only honest way to know, and it also catches a feature that built as one block.
    built: dict = {}

    def _count(label, fn):
        before, before_a = len(hide), len(accent)
        fn()
        # face features RECOLOUR rather than add, so count whichever the feature actually changed
        built[label] = max(len(hide) - before, len(accent) - before_a)

    # the top of the HEAD MASS, before any crown feature - this is the animal's anatomical height,
    # as opposed to its bounding box. Measuring proportions against the box needed a `crown_bias`
    # fudge per family; measuring against this needs nothing.
    anat_top = max(y for (_x, y, _z) in hide)
    if float(p.get("mane_volume", 0)) > 0:
        _count("mane", lambda: _ruff(hide, accent, shoulder, head_at, f, s, p))
    elif p["mane"]:
        _count("mane", lambda: _mane(hide, shoulder, f, s, p))
    _count("crown", lambda: _crown(hide, accent, head_at, f, s, p))
    _count("face", lambda: _face(hide, accent, head_at, f, s, p))
    if float(p.get("trunk", 0)) > 0:
        _count("trunk", lambda: _trunk(hide, accent, head_at, f, s, p))
    if p["tail"] != "none":
        _count("tail", lambda: _tail(hide, accent, fx, belly, fz, f, s, p))
    built["eyes"] = sum(1 for c, b in accent.items() if b == p["dark"] and c[1] >= head_at[1] - 1)

    skin = _coat(hide, p)
    if p.get("belly_block"):
        _underside(hide, accent, (rump, chest), float(p["withers"]), p, fx, fz, f,
                   int(p["body_len"]) // 2)
    w = World()
    for cell in sorted(hide):
        w.put(*cell, accent.get(cell) or skin.get(cell, p["coat_block"]))

    hi = max(y for (_x, y, _z) in hide)
    hits = 0 if ctx is None else sum(1 for c in hide if ctx.name_at(*c) not in AIRY)
    return w.canvas({"kind": p.get("profile") or "quadruped", "pose": p.get("pose", "standing"),
                     "feet": [fx, fy, fz],
                     "facing": list(f), "height": hi - fy, "top_y": hi,
                     # the joints, so an audit does not have to infer them from shape. On a cat the
                     # head, neck and barrel are one continuous mass and no shape heuristic can.
                     "features_built": built, "anat_top_y": anat_top,
                     "asymmetry": {"leg_phase": int(p.get("leg_phase", 0) or 0),
                                   "head_turn": int(p.get("head_turn", 0) or 0)},
                     "belly_y": belly, "withers_y": shoulder[1], "rump_y": rump, "chest_y": chest,
                     # the TOP OF THE BARREL, which is not the same as where the neck leaves it -
                     # on a cat the neck leaves well below the back, and shape cannot find the back
                     # either because the neck is nearly as wide as the body.
                     "back_y": belly + int(p["withers"]), "neck_top_y": neck_top[1],
                     # both ENDPOINTS, so neck length can be measured along its own axis. Taking it
                     # as a difference in height reads near zero on any animal that carries its head
                     # forward rather than up, which is every cat.
                     "shoulder_at": [round(float(v), 1) for v in shoulder],
                     "neck_top_at": [round(float(v), 1) for v in neck_top],
                     # WINDOWS along the heading for each part, measured from `feet`. A tall animal
                     # can have its parts told apart by height; a long low one cannot - a cat's head
                     # sits at body height, so "the extent above the neck" measures its whole back.
                     # The audit measures the real solid extent INSIDE each window.
                     "along": {"body": [-(int(p["body_len"]) // 2),
                                        int(p["body_len"]) - int(p["body_len"]) // 2],
                               "head": [int((head_at[0] - fx) * f[0] + (head_at[2] - fz) * f[1]),
                                        int((head_at[0] - fx) * f[0] + (head_at[2] - fz) * f[1])
                                        + int(p["head_len"])]},
                     "collisions": hits})


def _underside(hide, accent, belly, withers, p, fx, fz, f, half):
    """Countershading: a pale belly with a BROKEN edge, on the barrel only.

    Three attempts. A flat y-cut painted a dead-straight stripe along the flank - the giveaway that a
    statue was coloured by a rule. Following each column's floor instead climbed the sides and turned
    the whole flank pale. What actually reads right is a waterline, roughly level, with its boundary
    broken up by noise, and confined to the body: legs and tail keep the coat.
    """
    from .canvas import hash01
    seed = int(p["seed"])
    # The waterline follows the POSED floor line, sloping with it from rump to chest. Holding it at
    # the standing belly height put pale bands round the legs of a sitting cat, because the body had
    # dropped below the line and the legs were the only thing still crossing it.
    rump, chest = belly if isinstance(belly, tuple) else (belly, belly)
    for c in hide:
        along = (c[0] - fx) * f[0] + (c[2] - fz) * f[1]
        if not (-half - 1 <= along <= half + 2):
            continue                                     # tail and neck keep the coat
        t = min(1.0, max(0.0, (along + half) / max(1, 2 * half)))
        floor = rump + (chest - rump) * t
        if c[1] < floor:
            continue                                     # legs too
        edge = floor + withers * float(p["belly_frac"]) + 1.6 * (hash01(c[0], 0, c[2], 61, seed) - 0.4)
        if c[1] <= edge and c not in accent:
            accent[c] = p["belly_block"]


def _coat(hide, p) -> dict:
    kind = p["coat_pattern"]
    if kind == "plain":
        return {}
    if kind == "shaded":
        return coat_mod.shade(hide, list(p["coat_ramp"] or []), seed=int(p["seed"]),
                              strength=float(p["shade_strength"]))
    if kind == "rosettes":
        return coat_mod.rosettes(hide, p["patch"], p["coat_block"], centre=p.get("patch_alt"),
                                 scale=float(p["patch_scale"]), radius=float(p["ring_radius"]),
                                 thickness=float(p["ring_thickness"]), broken=float(p["ring_broken"]),
                                 seed=int(p["seed"]))
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
    # Clamp the reach to HALF the closest leg spacing. On a jaguar the legs sit 4 apart while
    # leg_r + flare came to 3.6, so every cell between them was inside some leg's reach, nothing was
    # forbidden, and the fill pass welded the legs into a slab exactly as before. A protective radius
    # wider than the gap it is protecting protects nothing.
    pairs = [((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
             for i, a in enumerate(hoofs) for b in hoofs[i + 1:]]
    closest = min(pairs) if pairs else 99.0
    reach = min(leg_r + flare + 0.6, max(leg_r + 0.3, closest / 2.0 - 0.5))
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

def _legs(hide, ctx, fx, fy, fz, f, s, p, keys, pose=None) -> list:
    """Four legs, each finding its OWN ground - terrain rolls, and a level hoof line either floats on
    the high side or buries its feet on the low.

    The top flares and carries four courses UP INSIDE the barrel, so a leg meets the body as a haunch
    rather than a post pushed into a wall; relax then blends that corner."""
    bl, br, lr = int(p["body_len"]), float(p["body_r"]), float(p["leg_r"])
    n = float(p["section_n"])
    pose = pose or {}
    fold = float(pose.get("fold", 1.0))
    KEYS = [[t, lr * fold + d] for t, d in keys["leg"]]
    out = []
    phase = int(p.get("leg_phase", 0) or 0)
    for idx, (along, side) in enumerate(((bl // 2 - 3, 1), (bl // 2 - 3, -1),
                                         (-(bl // 2 - 3), 1), (-(bl // 2 - 3), -1))):
        # diagonal pairs move together, as a walking animal's do
        along += phase if idx in (0, 3) else -phase
        # fore and hind shorten independently - that difference IS the pose. A sitting animal has
        # straight forelegs and folded haunches; shortening all four equally just makes it small.
        scale = float(pose.get("fore" if along > 0 else "hind", 1.0))
        top = fy + max(2, int(round(int(p["leg"]) * scale)))
        # Under the barrel's edge, but never closer together than the legs are wide. `br - lr - 0.4`
        # collapses to 1 on a narrow-bodied animal, putting a jaguar's legs 2 apart when each is 3
        # wide - they merged into a slab whatever the smoothing did. Giraffe lands on 3 either way.
        # `fold` widens a leg, so the spacing must be computed from the FOLDED radius, and the
        # clearance term grows with fold too - a bunched limb needs more room than its own width.
        # Without it a sitting jaguar's legs sat 6 apart while each was 5 wide and the pairs welded
        # laterally: two 13-block slabs where four legs should be. Scaling the term by `fold` leaves
        # an unfolded animal exactly where it was, so the giraffe does not move.
        off = max(1, round(max(lr * fold + 1.0 + (fold - 1.0) * 2.4, br * 0.62)))
        lx = int(fx + f[0] * along + s[0] * off * side)
        lz = int(fz + f[1] * along + s[1] * off * side)
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(lx, probe, lz) not in AIRY:
                    hoof = probe + 1
                    break
        builder = anatomy.LEGS.get(p.get("legs_kind", "cursorial"), anatomy.leg_cursorial)
        builder(hide, lx, lz, hoof, top, f, s, lr, n, fold)
        out.append((lx, lz, hoof, lr * fold + 0.8))
    return out


def _body(hide, fx, belly, fz, f, s, p, keys, pose=None) -> tuple:
    """A barrel whose back line and belly line are set independently, so it deepens toward the chest.

    The withers-to-hips drop is what separates a giraffe from a horse; it is a profile number."""
    bl, br = int(p["body_len"]), float(p["body_r"])
    withers, hips = float(p["withers"]), float(p["hips"])
    n = float(p["section_n"])
    half = bl // 2
    # rows may be 3 or 4 wide - the depth taper was added later and an override written against the
    # old shape must keep working
    KEYS = [[r[0], br + r[1], hips + (withers - hips) * r[2] + withers * (r[3] if len(r) > 3 else 0.0)]
            for r in keys["body"]]
    # a shoulder hump lifts the back line over the withers only - a bear's and a bison's profile
    hump = float(p.get("hump", 0.0)) * withers
    if hump:
        KEYS = [[t, dw, hh + (hump if 0.55 <= t <= 0.85 else 0.0)] for t, dw, hh in KEYS]
    pose = pose or {}
    # The floor line runs from where the HIND legs end to where the FORE legs end. It is derived,
    # not chosen: shortening a leg without lowering the body over it leaves the leg hanging, which is
    # exactly what the first sitting jaguar did - four detached stumps under a floating barrel.
    rump, chest = belly if isinstance(belly, tuple) else (belly, belly)
    extra = float(pose.get("pitch", 0.0)) * int(p["leg"])
    for a in range(-half, bl - half):
        t = (a + half) / max(1, bl - 1)
        rb, back = loft.lerp(KEYS, t)
        floor = rump + (chest - rump) * t + extra * t
        loft.rib(hide, fx + f[0] * a, floor + back / 2.0, fz + f[1] * a, f, s,
                 rb, back / 2.0, n, squash_lo=1.12)
    frm = float(pose.get("from", p.get("neck_from", 1.0)))
    rise = chest + extra + max(1.0, withers * frm) - 1.0
    return (fx + f[0] * (half - 2), rise, fz + f[1] * (half - 2))


def _neck(hide, shoulder, f, s, p, keys, pose=None):
    """Tapers smoothly and leans forward. The lean is carried as a FLOAT and the section re-centred
    every course, so the neck is a clean diagonal rather than a staircase."""
    sx, sy, sz = shoulder
    ln, r0, r1 = int(p["neck"]), float(p["neck_r0"]), float(p["neck_r1"])
    pose = pose or {}
    n = float(p["section_n"])
    lean = float(pose.get("lean", p["neck_lean"]))
    # `drop` carries the head DOWN the neck's length instead of up - grazing, drinking, stalking.
    # Without it every pose still ends with the head at the top of a rising neck, which is the one
    # thing a resting or feeding animal never does.
    rise = 1.0 - 2.0 * float(pose.get("drop", 0.0))
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

def _ruff(hide, accent, shoulder, head_at, f, s, p):
    """A lion's mane: a mass CENTRED ON THE NECK, big enough to break the silhouette.

    Two failed attempts before this. Swept up the neck it added 32 cells; swept back over the
    shoulders with a downward offset it added 16, because the offset buried the whole thing inside
    the barrel. A felid's neck is only about four blocks long, so there is no length to sweep along -
    the mane has to be a BALL around the neck, sized against the body rather than the neck, or it
    disappears into the animal it is supposed to be sitting on.

    THIRD failure, and the reason for the rest of this function: a ball of 306 cells that scored
    `features` 1.00 and was INVISIBLE in a render. Two causes, and each alone was enough.

      * It was never COLOURED. The mane only ever added cells to `hide`, so `_coat` painted them
        the body colour. 306 cells of lion-coloured mane on a lion is nothing at all.
      * It had no EDGE. R came out barely over `body_r`, centred halfway between shoulder and head,
        so most of the ball was inside the barrel it was meant to sit on.

    So the mane is now sized against the body it must CLEAR, seated toward the head where a real
    mane frames the skull, and painted with `mane_block`. A mane is a silhouette break and a tonal
    break at once; either on its own reads as a lump.
    """
    sx, sy, sz = shoulder
    hx, hy, hz = head_at[0], head_at[1], head_at[2]
    # seated toward the HEAD - a mane frames the skull, it does not sit on the shoulders. At the
    # midpoint half the ball was buried in the barrel and only the top of it ever showed.
    w = 0.62
    cx, cy, cz = sx + (hx - sx) * w, sy + (hy - sy) * w, sz + (hz - sz) * w
    body_r = float(p["body_r"])
    # it must CLEAR the barrel, not merely match it: `mane_volume` is now the number of blocks the
    # mane stands PROUD of the body, which is the only measure that makes it visible at any size.
    R = body_r + max(1.5, float(p["mane_volume"]))
    n = float(p["section_n"])
    mane_block = p.get("mane_block")
    for k in range(-int(R) - 1, int(R) + 2):
        u = abs(k) / max(1.0, R)
        if u > 1.0:
            continue
        r = R * (1.0 - u * u) ** 0.5
        # slightly deeper below the jaw than above the crown, as a real mane hangs
        before = set(hide) if mane_block else None
        loft.disc(hide, cx, cy + k * 0.9, cz, f, s, r * 0.85, r, n)
        if mane_block:
            for cell in hide - before:
                accent[cell] = mane_block


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
                # `ear_size` scales both the reach and the height. An elephant's ears are bigger
                # than its head and are the single most identifying thing about it; at the default
                # size it read as a grey horse with a hosepipe.
                reach = max(2, int(round(2 * float(p.get("ear_size", 1.0)))))
                tall = max(2, int(round(2 * float(p.get("ear_size", 1.0)))))
                for dyk in range(tall):
                    if dyk >= tall - 1 and a == 1:
                        continue
                    for b in range(1, (reach + 1) if a != 1 else reach):
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


def _trunk(hide, accent, head_at, f, s, p):
    """A trunk: a tapering column hung from the front of the face, curving down and back.

    Structurally identical to the long tail - a swept, tapering appendage - so it reuses that idea
    rather than inventing another. The differences are only that it hangs from the muzzle, tapers
    much harder, and curls at the tip.

    It is ANCHORED to the smoothed face for the same reason everything else is: at a computed offset
    it would hang a block clear of a muzzle that relax had pulled back."""
    hx, hy, hz, hl, hr, _ax, _az = head_at
    length = max(4, int(round(float(p["trunk"]) * int(p["head_len"]))))
    # find the real front of the face at muzzle height
    x = int(round(hx + f[0] * (hl - 1)))
    z = int(round(hz + f[1] * (hl - 1)))
    for d in range(hl + 3, 0, -1):
        probe = (int(round(hx + f[0] * d)), int(round(hy - 1)), int(round(hz + f[1] * d)))
        if probe in hide:
            x, z = probe[0], probe[2]
            break
    y = float(hy - 1)
    prev = int(round(y))
    px, pz = x, z
    for k in range(length):
        t = k / max(1, length - 1)
        r = max(0.6, (hr - 0.9) * (1.0 - 0.62 * t))       # tapers hard toward the tip
        y -= 0.55 + 1.5 * t                               # falls away, steeper as it goes
        fwd = 1.0 - 0.75 * t * t                          # and curls back under at the end
        cy = int(round(y))
        cx = int(round(x + f[0] * k * fwd))
        cz = int(round(z + f[1] * k * fwd))
        # Fill the whole run since the last segment. Near the tip it descends more than a block per
        # step, and stepping straight there left the trunk in five floating pieces - exactly the bug
        # the long tail had, because it is exactly the same sweep.
        for yy in range(min(cy, prev), max(cy, prev) + 1):
            loft.disc(hide, cx, yy, cz, f, s, r, r, float(p["section_n"]))
        for step in range(1, max(abs(cx - px), abs(cz - pz)) + 1):
            loft.disc(hide, px + (1 if cx > px else -1 if cx < px else 0) * step,
                      cy, pz + (1 if cz > pz else -1 if cz < pz else 0) * step,
                      f, s, r, r, float(p["section_n"]))
        prev, px, pz = cy, cx, cz
    return


def _tail_long(hide, accent, x, z, top, f, s, p):
    """A cat's tail: as long as the body, leaving the rump roughly level and drooping toward the tip.

    The hanging tail every hoofed animal here uses is wrong for a cat - it is the single feature that
    most says "big cat" in silhouette, and it has to carry BACKWARD before it falls."""
    length = max(6, int(round(float(p["tail_len"]) * int(p["body_len"]))))
    y = float(top)
    prev = int(round(y))
    for k in range(length):
        t = k / max(1, length - 1)
        y -= 0.05 + 0.75 * t * t                         # level at the root, falling at the tip
        cy = int(round(y))
        cx = int(round(x - f[0] * k))
        cz = int(round(z - f[1] * k))
        # fill the whole vertical run since the last segment: near the tip the drop exceeds one block
        # per step, and stepping straight to the new height left the tail in disconnected pieces.
        for yy in range(min(cy, prev), max(cy, prev) + 1):
            hide.add((cx, yy, cz))
        prev = cy
        if t < 0.45:                                     # thick at the base
            hide.add((cx, cy + 1, cz))
        if k >= length - 2:
            accent[(cx, cy, cz)] = p["dark"]


def _tail(hide, accent, fx, belly, fz, f, s, p):
    """One block wide a tail is invisible - the rump slice held exactly 11 cells and rendered as
    nothing. Two wide at the root, and a dark switch on the end."""
    half = int(p["body_len"]) // 2
    top = int(belly + int(p["hips"]) - 2)
    # ANCHOR to the rump's real surface. Placed at the computed body length it hung a block clear of
    # a rump that relax had shaved back, and came out as a 45-cell floating tail - the same mistake
    # as the mane and the eyes, which is why `loft.surface_out` exists.
    x, z = int(fx - f[0] * (half + 1)), int(fz - f[1] * (half + 1))
    for d in range(half + 2, 0, -1):
        probe = (int(fx - f[0] * d), top, int(fz - f[1] * d))
        if probe in hide:
            x, z = int(probe[0] - f[0]), int(probe[2] - f[1])
            break
    if p["tail"] == "long":
        return _tail_long(hide, accent, x, z, top, f, s, p)
    tassel = p["tail"] == "tassel"
    # SCALE the tail with the animal. At a fixed 13 blocks it was longer than a deer's legs, ran into
    # the ground and broke the model into two components. Every feature measured in absolute blocks
    # has this bug latent in it - the giraffe just happened to be the size the constant was tuned on.
    length = max(4, int(round(0.75 * int(p["leg"]))))
    switch = max(2, int(round(length * 0.25)))
    # RE-PROBE THE SURFACE AT EVERY COURSE. Anchoring once at the top and then dropping straight
    # down assumes a vertical rump. Once the barrel's ends taper, the rump slopes backward as it
    # descends, so a plumb tail is INSIDE the body for most of its length - the bear's went from 10
    # cells to 2, and `features` called it absent. The tail is a clinging feature like the mane and
    # the eyes, and the rule is the same for all of them: measure the skin, never assume it.
    prev = None
    for k in range(length):
        y = top - k
        cx, cz = x, z
        for d in range(half + 2, 0, -1):
            probe = (int(fx - f[0] * d), y, int(fz - f[1] * d))
            if probe in hide:
                cx, cz = int(probe[0] - f[0]), int(probe[2] - f[1])
                break
        cells = [(cx, y, cz)]
        # 6-CONNECTIVITY: if the surface stepped back a block since the course above, the two cells
        # are only diagonal neighbours and the tail is not connected. Bridge the step.
        if prev is not None and (prev[0] != cx or prev[2] != cz):
            cells.append((prev[0], y, prev[2]))
        if k < max(2, length // 4):
            cells.append((int(cx - f[0]), y, int(cz - f[1])))
        if tassel and length - switch <= k < length - 1:
            cells += [(int(cx + s[0] * b), y, int(cz + s[1] * b)) for b in (-1, 1)]
        for c in cells:
            hide.add(c)
            if k >= length - switch:
                accent[c] = p["dark"]
        prev = (cx, y, cz)
