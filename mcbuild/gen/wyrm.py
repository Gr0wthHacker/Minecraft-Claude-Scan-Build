"""WYRM'S CROSSING - the Prism Reach threshold. A partial skull and a ribcage you walk through.

THE FREE-STANDING SERPENT WAS REJECTED OUTRIGHT, AND THE REJECTION IS THE DESIGN. The build that
used to live here was a reared snake: a coil at the base of a milestone, a free S-curve, a
flared hood and a head. It was one connected piece, correctly banded, and it named itself in a
thumbnail - and `PARK_VISUAL_AND_BUDGET_SPEC.md` lists "full free-standing snake coil" first
among this setpiece's rejection conditions, because the park does not need another object. It
needs the Midway-to-Prismworks transition to READ as a threshold:

    Form            partial skull/head plus 4-6 articulated ribs, broken spine segments,
                    dark recesses, one visible rune panel
    Size            52-68 long, 20-28 high, 14-20 deep - low enough to FRAME rather than
                    create another crown
    Budget          7,000-10,000 blocks INCLUDING rim anchors, rune alcove and service
    Attachment      ribs root into the bridge rim and the Foundry approach
    Rejection       a free-standing coil, random bones, any blocked main route, riddle cues
                    unreadable from the public approach

`PARK_FINAL_ARCHITECTED_PLAN.md` adds the operating half: main transit is a continuous 5-wide
path, the three rune inputs sit in a SIDE alcove at player height with the public bypass always
visible, and service/reset lives behind the rim.

**SO THE ANIMAL IS THE ARCHITECTURE.** You walk down the middle of it. The ribs spring off the
two rim walls and arch clear over the path; the skull straddles the arrival end, so the crossing
is entered under its jaws; the spine survives only where a rib holds it up, which is what makes
it BROKEN rather than merely dotted. Every one of those is a structural fact rather than a
decorative one, and that is the difference between a skeleton and scattered bones - the second
rejection condition.

**THE SPINE IS BROKEN BY CONSTRUCTION AND STILL ONE PIECE.** A gap between vertebrae is what
says "broken", and a gap is also how this project has shipped detached ear tips, ossicones, a
tail tip and a whole dragonfly. Each vertebra is seated on a rib apex read off the BUILT surface
with a downward probe, never a computed radius, because the sweep's own rounding moves that
surface a course either way. The segments are separated from EACH OTHER and every one of them is
attached to the thing under it: the brokenness is in the silhouette, the connectivity is in the
geometry.

**THE 5-WIDE BYPASS IS A HOLE THIS BUILD IS NOT ALLOWED TO FILL, AND IT IS MEASURED.** Nothing
drawn here may enter the path's own prism - five columns wide, three courses tall, the whole
length. The rib feet stand out on the rim and the arch is nineteen courses up by the time it
crosses the path's edge; the skull's chin is clear of head height; the alcove, its screen and
the rune panel all live beyond the verge. The prism is walked at the end of the build and an
intrusion RAISES, because "any blocked main route" is a rejection condition and a rejection
condition that is only ever hoped for is not one.

**THE ALCOVE IS OFF THE ROUTE AND ITS CUES FACE ONTO IT.** A riddle you cannot see from the
public walk is the fourth rejection condition, so the panel hangs on the alcove's back wall
looking straight across the crossing, lit, with the three inputs on it at player height. The bay
has a 2-wide entry and a 2-wide rejoin further along - the optional reconnection the plan asks
for - screened from the verge by a low wall that never touches the path.

PALETTE, and it is the material policy rather than taste. Cobblestone/stone/stone-brick layers
for the rim and the deck; `bone_block` and `light_gray_wool` for the skeleton, which stands 127
of luminance clear of its own masonry; `black_wool` for every void recess, which is the biggest
cheap value step this economy has - measured ACROSS families, because the three notes in
CLAUDE.md concluding this park has no value contrast were all measured INSIDE one family, where
a ladder cannot exist by construction. The rune light is sparse light-blue/cyan/blue wool and
two soul lanterns. Nothing above `ok` tier anywhere, and nothing out of the dirt family, which
is CURRENCY on this server and must never be bulk.

SYMMETRY IS BY CONSTRUCTION AND THE ASYMMETRY IS DECLARED. Rim, deck, colonnade, ribs, spine and
skull are drawn once per side from a signed multiplier, and a MIRROR FLIPS A FACING rather than
copying it - the corbels lean into the wall they grow from on both flanks, which is the whole of
what the mirror may touch here. The alcove, its screen, the rune fittings and the service hatch
are deliberately one-sided; the band they occupy is recorded as `asym_box`, so a symmetry check
can excuse exactly that and nothing else.

AND A FACING IS A TURN, NOT A FLIP - see the rotation block below. `facing` was accepted and
inert for a while, which is this repo's most repeated failure shape and here decides whether the
module fits its own lot: the Prism Reach is 45 blocks along U against 63 along V, so a 60-long
crossing only fits with its length on x.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01

# ---------------------------------------------------------------------------- cardinal turns
#
# `facing` is the direction the crossing's FRONT - its skull end - looks out. The build is drawn
# once, canonically, running along z with the skull at the low-z end, which is a front looking
# NORTH; every other facing is that build turned about the vertical.
#
# **A FACING ROTATES, IT DOES NOT COPY.** Every directional property has to turn with the
# geometry or the corbels lean out of the wall they grow from, the levers hang on nothing and
# the sign faces the block it is nailed to - and `render3d` draws a wrong facing exactly like a
# right one, so nothing offline in this repo would show it.
#
# THIS IS NOT `kit.flip`, and reaching for it here would be a real bug rather than a style
# choice: a mirror REVERSES HANDEDNESS, so it turns an `inner_left` stair into an `inner_right`
# one and swaps a door's hinge. A rotation preserves both, which is why `shape` and `hinge` are
# untouched below and `axis` - which a mirror leaves alone - is the one a rotation must swap.
# What the two do share is that a HALF turn is exactly both of kit's mirrors, and
# `test_a_half_turn_is_exactly_kit_s_two_mirrors` asserts that so the tables cannot drift apart.
_YAW = ("north", "east", "south", "west")
_QUARTER = {d: i for i, d in enumerate(_YAW)}
_VEC = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}
#: the legacy spelling `isthmus.py` and the old configs pass. +1 was the unturned build.
_FACE_SIGN = {1: "north", -1: "south"}


def turn_props(props: dict, k: int) -> dict:
    """One block's state, turned `k` quarter turns clockwise about the vertical."""
    out = dict(props)
    k %= 4
    if not k:
        return out
    if out.get("facing") in _QUARTER:
        out["facing"] = _YAW[(_QUARTER[out["facing"]] + k) % 4]
    if k % 2 and out.get("axis") in ("x", "z"):
        out["axis"] = "z" if out["axis"] == "x" else "x"
    if k % 2 and any(d in out for d in _YAW):
        # a multiface block (vine, glow lichen) names the faces it clings to, and each of them
        # takes the value of whichever face turns INTO it
        out.update({d: out.get(_YAW[(_QUARTER[d] - k) % 4], "false") for d in _YAW if d in out})
    return out


def _turn_point(pt, k: int, dims):
    """(x, y, z) through `k` quarter turns of a canvas whose (sx, sz) is `dims`."""
    x, y, z = (int(v) for v in pt)
    nx, nz = dims
    for _ in range(k % 4):
        x, z, nx, nz = nz - 1 - z, x, nz, nx
    return (x, y, z)


def _turn_box(a, b, k: int, dims):
    """A 2-D (x, z) box through the same turns, re-cornered - a rotated box's `min` corner is
    not the rotation of its old `min` corner, and taking it as one is how a box quietly ends up
    inside out."""
    pts = [_turn_point((px, 0, pz), k, dims) for px, pz in (a, b)]
    xs, zs = [q[0] for q in pts], [q[2] for q in pts]
    return [[min(xs), min(zs)], [max(xs), max(zs)]]


def _turn(c: Canvas, k: int) -> None:
    """Turn a whole built canvas: cells, block states and sign text together.

    The states are turned through the canvas's OWN registry, so a state that already exists in
    the palette is reused rather than duplicated, and the whole remap is computed against a
    snapshot before anything is written - registering a turned state appends to the very list
    being read.
    """
    k %= 4
    if not k:
        return
    import numpy as _np
    from .. import nbt as _nbt

    snapshot = list(c.reg.palette)
    remap = _np.arange(len(snapshot), dtype=_np.int32)
    for i, entry in enumerate(snapshot):
        if i == 0:
            continue
        pr = entry.value.get("Properties")
        props = {kk: vv.value for kk, vv in pr.value.items()} if pr else {}
        remap[i] = c.reg.raw(_nbt.state_name(entry), **turn_props(props, k))

    ids = c.ids
    for _ in range(k):
        ids = _np.transpose(ids, (0, 2, 1))[:, :, ::-1]
    c.ids = remap[_np.ascontiguousarray(ids)]
    dims = (c.sx, c.sz)
    c.sx, c.sz = (c.sz, c.sx) if k % 2 else (c.sx, c.sz)
    c.tiles = {_turn_point(pos, k, dims): v for pos, v in c.tiles.items()}

WYRM = {
    "seed": 0,
    "scale": 1.0,
    # "crossing" is the locked W1 threshold and the only form this setpiece may ship as.
    # "serpent" is the RETIRED causeway ornament, kept reachable for one caller and one reason:
    # `isthmus.GAPS` still sites it on the Hollow Reach, `test_isthmus` requires two creatures a
    # span, and the two assets Jack removed from that file are the only replacements that exist.
    # Retiring the causeway stop is a program decision, not a maintenance one, so it is left
    # standing and named rather than deleted underneath somebody. Nothing defaults to it.
    "form": "crossing",
    # world coordinate of the canvas corner - a bespoke generator states this itself or the
    # pipeline writes no sidecar, and without one there is no origin and no `/cscan place`.
    "at": None,
    # ...or give `stand`, the world cell the crossing's OWN LOWEST COURSE occupies, at the
    # middle of its width and the middle of its length.
    "stand": None,
    # +1 puts the skull at the low-z end, -1 at the high-z end. `facing` takes the same signs
    # and also accepts a compass word; it wins over `face` when both are given.
    "face": 1,
    "facing": None,

    "length": 60,            # along the crossing - the spec's 52-68
    "path_w": 5,             # THE PUBLIC BYPASS. Never built into, and measured.
    "verge_w": 3,
    "rim_w": 3,              # ...so depth is 5 + 2*3 + 2*3 = 17, inside the spec's 14-20
    "deck_y": 5,             # courses of abutment under and including the deck
    "pier_h": 3,             # the rim's colonnade, between deck and cap
    "head_room": 3,          # courses of the path prism nothing may enter

    # SIX, THE TOP OF THE SPEC'S 4-6. The reference-grammar skull is hollow and shallower
    # than the ellipsoid it replaced, so the head alone came in under the ledger floor -
    # and the honest way to put mass back is another bay of ribcage, which is what a
    # visitor walks through, rather than thickening something to protect a number.
    "ribs": 6,
    "rib_rise": 12,
    "rib_r": 1.85,
    "knuckles": 5,           # articulation: bulges along a rib, never gaps in one
    "rib_bow": 1.7,          # how far a rib bows along the crossing, so it is not a flat hoop

    "skull_r": 6.0,

    "alcove_len": 13,        # the riddle bay, off the +x verge
    "svc_len": 7,            # the service crawl, inside the -x rim
    "abutment": 4,           # the rim anchors: solid full-width ends into the approaches

    "foot": "cobblestone",
    "wall": "stone",
    "course": "cracked_stone_bricks",
    "deck": "stone_bricks",
    "path": "stone",
    "verge": "cobblestone",
    "cap": "stone_bricks",
    "trim": "stone_brick_stairs",
    "chis": "chiseled_stone_bricks",
    "screen": "stone_brick_wall",
    "bone": "bone_block",
    "pale": "light_gray_wool",
    "teeth": "white_wool",
    "void": "black_wool",
    "rune_a": "light_blue_wool",
    "rune_b": "cyan_wool",
    "rune_c": "blue_wool",
    "lamp": "soul_lantern",
    "input": "lever",
    "hatch": "iron_trapdoor",
    "sign": "oak_wall_sign",
    "moss": "moss_block",

    # --- form "serpent" only, and none of it is reachable from the crossing --------------
    "stone_h": 8,            # courses of milestone above its own footing
    "turns": 1.55,           # ...and the last of them lands the body pointing along +face
    "body_r": 1.85,
    "rise": 16,              # courses of free S between the coil and the hood
    "band_every": 26,        # STATIONS between the body's dark bands
    "band_wide": 4,
    "hood_w": 5.4,           # half the hood, across the walk
    "hood_h": 4.6,
    "post": "deepslate_bricks",
    "band": "polished_blackstone_bricks",
    "body": "bone_block",
    "belly": "light_gray_wool",
    "mark": "black_wool",
    "eye": "red_wool",
}


def _rib_path(a: float, foot_y: float, rise: float, z0: float, bow: float, n: int):
    """One rib arch, foot to foot, as a dense list of stations.

    DENSE ON PURPOSE. A swept feature whose cells are only DIAGONAL neighbours is not connected
    in this project's sense, and that has cost it ear tips, ossicones, a tail tip and a whole
    dragonfly. The station spacing here is well under half a block.
    """
    out = []
    for i in range(n + 1):
        t = i / float(n)
        th = math.pi * t
        out.append((-a * math.cos(th),                       # across, foot to foot
                    foot_y + rise * math.sin(th),            # up
                    z0 + bow * math.sin(th),                 # bowed along the crossing
                    t))
    return out


def build_wyrm(cfg: dict, donors=None) -> Canvas:
    p = {**WYRM, **cfg}
    form = str(p.get("form", "crossing"))
    if form == "serpent":
        return _build_serpent(p, donors)
    if form != "crossing":
        raise ValueError(f"wyrm form must be 'crossing' or 'serpent', not {form!r}")
    sc = float(p.get("scale", 1.0))
    seed = int(p.get("seed", 0))

    # --- the parameter surface. `facing` wins, `face` is the legacy spelling, and a compass
    # word is accepted because every other park generator speaks one. Anything unreadable is a
    # hard error rather than a quiet default: a threshold pointing the wrong way is the one
    # mistake no render in this repo can see.
    fw = p.get("facing")
    if fw is None:
        facing = _FACE_SIGN[1 if int(p.get("face", 1)) >= 0 else -1]
    elif isinstance(fw, str):
        if fw not in _QUARTER:
            raise ValueError(f"facing must be one of {sorted(_QUARTER)} or +-1, not {fw!r}")
        facing = fw
    else:
        facing = _FACE_SIGN[1 if int(fw) >= 0 else -1]

    L = max(52, int(round(float(p["length"]) * sc)))
    path_w = max(5, int(p["path_w"]))
    verge_w, rim_w = max(2, int(p["verge_w"])), max(2, int(p["rim_w"]))
    W = path_w + 2 * verge_w + 2 * rim_w
    y_deck = max(3, int(round(float(p["deck_y"]) * sc)))
    pier_h = max(2, int(round(float(p["pier_h"]) * sc)))
    y_cap = y_deck + 1 + pier_h
    rise = max(8.0, float(p["rib_rise"]) * sc)
    rib_r = float(p["rib_r"]) * sc
    n_rib = max(4, min(6, int(p["ribs"])))
    head_room = max(3, int(p["head_room"]))

    cx = W // 2
    half_path = path_w // 2                      # the bypass is x in [cx-hp, cx+hp]
    # captured BEFORE the turn, because `cx` is re-derived from the turned canvas and by then
    # the canonical path columns no longer mean anything
    cx_path0, cx_path1 = cx - half_path, cx + half_path
    x_rim_in = half_path + verge_w               # inner face of the rim, as an offset from cx
    x_rim_out = x_rim_in + rim_w - 1             # ...and its outer skin
    a_rib = float(x_rim_in + 1)                  # rib feet stand one course inside the cap
    # THE MIRROR AXIS OF A CONTINUOUS SHAPE IS NOT `cx`, IT IS `cx + 0.5`. `sphere` measures from
    # a cell's own CENTRE (`x + 0.5`), so a sweep centred on the integer column comes out a cell
    # wider on one flank than the other - the exact half-cell asymmetry that once shipped this
    # generator with ONE eye, twice, with nothing in the audit or the component count to say so.
    # Integer `put` offsets keep using `cx`, where +-dx already mirrors exactly.
    mx = cx + 0.5

    SY = int(y_cap + rise + 6)
    c = Canvas(W, SY, L, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("foot", "wall", "course", "deck", "path", "verge", "cap",
                               "chis", "bone", "pale", "teeth", "void", "moss",
                               "rune_a", "rune_b", "rune_c")}
    S["screen"] = st(p["screen"])
    S["lamp"] = st(p["lamp"], hanging="false", waterlogged="false")

    def stair(facing):
        """A corbel under the cap. The stair's TALL side is its `facing` and it leans INTO the
        wall it grows from - the convention pinned in `test_stairhead.py`, asserted rather than
        eyeballed because this repo's renderer draws both directions identically."""
        return st(p["trim"], facing=facing, half="top", shape="straight", waterlogged="false")

    # ---------------------------------------------------------------- the rim and the deck
    # THE RIM IS THE THING THE RIBS ROOT INTO, so it is built first and it runs the whole
    # length. Layered by course - footing, wall, band, deck - which is the three-depth grammar
    # the visual spec asks for and the reason a plain cobble box does not read.
    rim_cells = 0
    for zz in range(L):
        for s in (-1, 1):
            for d in range(rim_w):
                x = cx + s * (x_rim_in + d)
                for y in range(y_deck + 1):
                    blk = (S["foot"] if y == 0 else
                           S["course"] if y == y_deck - 1 else
                           S["deck"] if y == y_deck else S["wall"])
                    rim_cells += 1 if c.put(x, y, zz, blk) else 0

    # the deck itself: the public path in one tone and the verges in another, so the 5-wide
    # bypass reads as a route rather than as the middle of a floor. It costs no extra blocks.
    deck_cells = 0
    for zz in range(L):
        for dx in range(-(x_rim_in - 1), x_rim_in):
            blk = S["path"] if abs(dx) <= half_path else S["verge"]
            deck_cells += 1 if c.put(cx + dx, y_deck, zz, blk) else 0

    # THE RIM ANCHORS. Both ends are solid full-width abutments rather than a deck stopping in
    # mid-air: the spec's attachment clause is that this thing roots into the bridge rim AND the
    # Foundry approach, and an approach you can see daylight under is a prop, not a threshold.
    abut = max(2, int(round(float(p["abutment"]) * sc)))
    anchors = 0
    for zz in list(range(abut)) + list(range(L - abut, L)):
        for dx in range(-x_rim_out, x_rim_out + 1):
            for y in range(y_deck + 1):
                blk = (S["foot"] if y == 0 else
                       S["course"] if y == y_deck - 1 else
                       S["deck"] if y == y_deck else S["wall"])
                anchors += 1 if c.put(cx + dx, y, zz, blk) else 0

    # the colonnade: piers with air between them, capped by a course that runs the whole
    # length. The cap is what keeps the rim continuous whatever rhythm the piers take, and it
    # is also the course every rib foot lands on.
    pier_cells, pier_zs = 0, []
    for zz in range(L):
        on = (zz % 5) in (0, 1, 2)
        if on:
            pier_zs.append(zz)
        for s in (-1, 1):
            for d in range(rim_w):
                x = cx + s * (x_rim_in + d)
                if on:
                    for y in range(y_deck + 1, y_cap):
                        pier_cells += 1 if c.put(
                            x, y, zz, S["wall"] if y == y_cap - 1 else S["foot"]) else 0
                pier_cells += 1 if c.put(x, y_cap, zz, S["cap"]) else 0

    # a corbel off each pier, under the cap. Only beside a pier - a cornice drawn on scattered
    # cells is the deck soffit's confetti, and one hung between two piers stands on nothing.
    trim_cells = 0
    for zz in pier_zs:
        for s in (-1, 1):
            # the wall it grows from is at cx + s*x_rim_in, OUTBOARD of the corbel, so the tall
            # side points that way. THE MIRROR FLIPS IT: east on the +x side, west on the -x.
            if c.put(cx + s * (x_rim_in - 1), y_cap, zz, stair("east" if s > 0 else "west")):
                trim_cells += 1

    # dark recesses in the outer skin - a rhythm of shadow rather than a flat wall face
    recess = 0
    for zz in range(2, L - 2):
        if zz % 5 != 3:
            continue
        for s in (-1, 1):
            for y in (y_deck - 3, y_deck - 2):
                if y >= 1 and c.put(cx + s * x_rim_out, y, zz, S["void"]):
                    recess += 1

    # ---------------------------------------------------------------- the ribs
    # 4-6 ARTICULATED ribs. The articulation is a knuckle rhythm in the RADIUS, never a gap: a
    # rib with real gaps in it is several components and the audit would call it clean.
    sr = float(p["skull_r"]) * sc
    # the skull's own back plane, so the first rib clears it. Stated rather than derived
    # from a radius, because the head is course bands now and has no radius to derive from.
    z_head = 9
    z_first, z_last = z_head + 5, L - 4
    span = (z_last - z_first) / float(max(1, n_rib - 1))
    knk = max(2, int(p["knuckles"]))
    bow = float(p["rib_bow"]) * sc
    rib_apex = []
    for i in range(n_rib):
        z0 = z_first + span * i
        # both halves come off one signed sweep, so a rib is a mirror rather than a copy - and
        # `sphere` carries no facing, so there is nothing here that could need re-aiming.
        for ox, oy, oz, t in _rib_path(a_rib, y_cap, rise, z0, bow, 150):
            r = rib_r * (1.0 + 0.34 * (0.5 + 0.5 * math.cos(2 * math.pi * knk * t)))
            r *= (0.84 + 0.16 * math.sin(math.pi * t))     # thinner at the feet
            c.sphere(mx + ox, oy, oz, r, S["bone"])
        rib_apex.append(int(round(z0 + bow)))

    # the pale course along each rib's crown, read off the BUILT SURFACE - and swept over whole
    # COLUMNS of the rib's own z band rather than over the path's rounded stations. A band
    # computed from the sweep's own arithmetic lands a course off wherever the rounding went the
    # other way, and it inherits the station list's own half-cell bias, so one flank of every
    # rib comes out banded and the other bare.
    for i in range(n_rib):
        z0 = z_first + span * i
        for iz in range(max(0, int(z0 - 3)), min(L, int(z0 + bow + 4))):
            for ix in range(W):
                for y in range(SY - 1, y_cap, -1):
                    if c.solid(ix, y, iz):
                        if c.get(ix, y, iz) == S["bone"]:
                            c.put(ix, y, iz, S["pale"])
                        break

    # ---------------------------------------------------------------- the broken spine
    # ONE VERTEBRA PER RIB APEX AND NOTHING BETWEEN THEM. The gaps are the feature; each segment
    # is seated on the surface its own rib actually built, so no gap is ever a break in the
    # model. Probed downward from the ceiling - a computed apex is a course out as often as not,
    # and this repo has shipped a floating dorsal fin from exactly that.
    spine = 0
    for zc in rib_apex:
        for dz in (-2, -1, 0, 1, 2):
            # EVERY CELL OF A VERTEBRA IS SEATED ON THE COLUMN IT STANDS IN, not on the one the
            # middle of the segment happened to find. A rib bows along the crossing, so its
            # crown falls away either side of the apex and a segment laid at one height has its
            # ends in mid-air - which is a floating cell in a build the audit calls clean.
            for y in range(SY - 3, y_cap, -1):
                if not c.solid(cx, y, zc + dz):
                    continue
                spine += 1 if c.put(cx, y + 1, zc + dz, S["pale"]) else 0
                if abs(dz) <= 1:
                    spine += 1 if c.put(cx, y + 2, zc + dz, S["bone"]) else 0
                if dz == 0:
                    for dx in (-1, 1):                     # the neural spine's own dark seam
                        c.put(cx + dx, y + 1, zc, S["void"])
                break

    # ---------------------------------------------------------------- the partial skull
    # BUILT AGAINST A REAL REFERENCE, NOT OUT OF AN ELLIPSOID.
    # `reference/bone_ruins_skull.litematic` is an outside builder's 54 x 66 x 40 skull ruin, and
    # measuring it settled every proportion and every feature this head had been missing:
    #
    #   H/W 1.22, D/W 0.74     a skull is TALLER than wide and noticeably SHALLOWER than wide.
    #                          The lofted ellipsoid here was near-cubic, which is most of why it
    #                          rendered as a pale mound with markings painted on it.
    #   26.8% fill             it is HOLLOW - the mouth is a room you can stand in. Ours is a
    #                          fraction of the size and still borrows the rule: a dark recess
    #                          where the mouth is beats a solid block of bone.
    #   the feature ORDER      brow over sockets over cheek shelf over jaw over mandible, with a
    #                          nasal aperture between the sockets. Every one of those is a LEDGE
    #                          or a RECESS - a band that projects, or a hole that goes in.
    #
    # **THE SOCKETS READ BECAUSE THEY ARE DEEP, DARK AND OVERHUNG - never because of an outline
    # painted round them.** Two courses of real recess with a black back, under a brow standing
    # proud of them, is the whole trick; both earlier passes here painted a flat socket onto a
    # curved face and neither read from the approach.
    #
    # WHAT IS NOT INHERITED IS THE PALETTE. The reference is 19,877 `light_gray_concrete` plus
    # terracotta - all expensive on this server - and 1,538 dirt and grass, which are CURRENCY
    # here. What is taken is the FORM; the bone/pale/void ladder already in this file carries it,
    # and the moss is `moss_block`, which is cheap and spendable.
    hw = min(5, x_rim_in)                       # half width - the skull lands on the rim's line
    zf = 1                                      # the front plane, at the arrival end
    z0, z1 = zf + 1, zf + 7                     # the main mass: 7 deep against 11 wide
    base = y_deck + head_room + 2               # chin well clear of the path prism

    def _course(dy, half, za, zb, blk, round_ends=True):
        """One course of the head. `round_ends` drops the four corner cells, because a square
        corner at this scale reads as a crate - and the projecting ledges keep their full width
        but still lose their two FRONT corners, which is what stops a shelf reading as a plank
        nailed across the face."""
        n = 0
        for dx in range(-half, half + 1):
            for zz in range(za, zb + 1):
                corner = abs(dx) == half and (zz in (za, zb) if round_ends else zz == za)
                if corner:
                    continue
                n += 1 if c.put(cx + dx, base + dy, zz, blk) else 0
        return n

    # THE MANDIBLE, a U open in the middle: two rami down the flanks and a chin bar across the
    # front. The open middle IS the mouth, and it is the cheapest dark recess in the build.
    # THE CHIN BAR IS ONE COURSE, NOT TWO. Given both, the front of the mandible was a solid
    # pale block and the mouth - the biggest dark recess on the whole head - could not be seen
    # from the approach at all. With the upper course open, the void between the teeth and the
    # chin reads as a mouth, which is the reference's own 26.8% fill said at this scale.
    for dy in (0, 1):
        for dx in range(-hw, hw + 1):
            for zz in range(z0, z1 + 1):
                if abs(dx) >= 3 or (dy == 0 and zz <= z0 + 1):
                    c.put(cx + dx, base + dy, zz, S["bone"])
    # ...hinged to the upper jaw at the BACK, which is where a real mandible hangs from and, more
    # to the point here, the only thing that keeps it one piece with the rest of the head.
    for dx in range(-hw, hw + 1):
        if abs(dx) >= 4:
            for zz in range(z1 - 2, z1 + 1):
                c.put(cx + dx, base + 2, zz, S["bone"])

    # the upper jaw, a bar across the width, with the teeth hanging off its underside into the
    # mouth void - alternating, so the jaw carries a comb rather than a straight lip
    _course(3, hw, z0, z1 - 1, S["bone"])
    _course(4, hw, z0, z1 - 1, S["bone"])
    teeth = 0
    for dx in range(-3, 4):
        for zz in range(z0, z0 + 3):
            if (dx + zz) % 2 == 0:
                teeth += 1 if c.put(cx + dx, base + 2, zz, S["teeth"]) else 0

    # THE CHEEK SHELF: a horizontal band projecting a course FORWARD of everything under it. It
    # is the reference's zygomatic shelf, and it is what stops a head reading as one lump - the
    # sockets sit on it and the jaw hangs below it.
    _course(5, hw, zf, z1, S["pale"], round_ends=False)

    for dy in (6, 7, 8, 9):                      # the cranium, up to the brow
        _course(dy, hw, z0, z1, S["bone"])
    for dy in (7, 8, 9, 10, 11):                 # ...hollow, so the break shows dark inside
        for dx in range(-2, 3):
            for zz in range(z0 + 2, z1):
                c.put(cx + dx, base + dy, zz, S["void"])

    # THE BROW, proud of the sockets and casting into them. The same idiom as the shelf, one
    # course forward of the face, and the second half of what makes a socket read at all.
    _course(10, hw, zf, z1, S["pale"], round_ends=False)

    # the crown, falling away over the last three courses exactly as the reference's does
    _course(11, hw, z0, z1, S["bone"])
    _course(12, hw - 1, z0 + 1, z1 - 1, S["bone"])
    _course(13, hw - 2, z0 + 1, z1 - 2, S["pale"])

    # THE SOCKETS: cut TWO COURSES DEEP into the face and backed with black. Rounded by dropping
    # the corners - a square hole reads as a window - and separated by a real nasal bridge,
    # because at a closer spacing the pair merged into one dark bar and the face read head-on as
    # a pair of sunglasses. That is the frog's own recorded failure and the ladybird's
    # spot-spacing rule underneath it: two features closer than their own width become one.
    sockets = 0
    for s in (-1, 1):
        for dy in (7, 8, 9):
            for off in (2, 3, 4):
                if abs(dy - 8) == 1 and off == 4:
                    continue                     # the corners: a socket is not a square
                x = cx + s * off
                for zz in (z0, z0 + 1):
                    sockets += 1 if c.put(x, base + dy, zz, 0) else 0
                c.put(x, base + dy, z0 + 2, S["void"])

    # THE NASAL APERTURE, an inverted triangle between and below the sockets - wide at the top,
    # one cell at the bottom. Small, dark, and the third thing after the sockets and the brow
    # that a stranger actually reads as a skull rather than as a dome.
    # ONE CELL WIDE, AND THAT IS THE POINT. Drawn three wide it TOUCHED the sockets either side
    # of it and the three recesses merged into a single dark mask - the sunglasses failure a
    # third time, from a new direction. The bone columns at |dx| = 1 are the nasal bridge and
    # they have to survive, or there are not two eyes there any more.
    for dy in (6, 7):
        c.put(cx, base + dy, z0, 0)
        c.put(cx, base + dy, z0 + 1, S["void"])

    # THE BREAK: the back of the braincase is gone, ragged, showing the dark hollow. Taken off
    # the BACK rather than off a flank, so the head is still a mirror of itself and there is
    # something left for a symmetry check to measure - and hashed on the MIRRORED column, or the
    # two flanks break in different places and the one feature the piece is read by is the one
    # thing about it that is lopsided.
    skull_open = 0
    for dy in range(8, 14):
        for dx in range(-hw, hw + 1):
            for zz in range(z1 - 2, z1 + 1):
                if c.get(cx + dx, base + dy, zz) in (S["bone"], S["void"], S["pale"]):
                    if zz > z1 - 2 + 1.6 * hash01(seed, abs(dx), dy) - 0.6:
                        c.put(cx + dx, base + dy, zz, 0)
                        skull_open += 1

    # WEATHERING LIVES IN THE RECESSES AND ON THE CROWN, which is what makes the reference read
    # as a ruin rather than as a prop - never scattered across the face, where it would read as
    # damage to the one surface that has to stay legible.
    brow = 0
    for dx in range(-hw, hw + 1):
        for dy in (11, 12, 13):
            for zz in range(z0, z1 + 1):
                if c.get(cx + dx, base + dy, zz) in (S["bone"], S["pale"]) \
                        and not c.solid(cx + dx, base + dy + 1, zz) \
                        and hash01(seed + 7, abs(dx), dy * 31 + zz) < 0.30:
                    brow += 1 if c.put(cx + dx, base + dy, zz, S["moss"]) else 0

    # THE ZYGOMATIC BUTTRESSES. The head already lands on the rim's own line at |dx| = hw, so
    # these are not what holds it up - they are what makes the seating READ: a cheekbone gripping
    # the parapet either side of the opening you walk through. Mirrored off one signed multiplier.
    butt = 0
    for s in (-1, 1):
        for yy in range(y_cap + 1, base + 6):
            for zz in range(z0 + 1, z1 - 1):
                c.put(cx + s * (hw + 1), yy, zz, S["bone"])
        butt += 1

    # ---------------------------------------------------------------- the rune alcove
    # OFF THE ROUTE, WITH ITS CUES FACING ONTO IT. Cut back into the +x rim, screened from the
    # verge with a 2-wide entry and a 2-wide rejoin - the optional reconnection the plan asks
    # for - and not one cell of it inside the bypass.
    a_len = max(9, int(round(float(p["alcove_len"]) * sc)))
    z_al0 = max(z_first + 2, (L - a_len) // 2)
    z_al1 = min(L - 3, z_al0 + a_len - 1)
    x_al_back = cx + x_rim_out                    # the outer skin stays: the panel hangs on it
    alcove = 0
    for zz in range(z_al0, z_al1 + 1):
        for d in range(rim_w - 1):                # everything but the outer skin
            x = cx + x_rim_in + d
            for y in range(y_deck + 1, y_deck + 1 + head_room):
                if c.solid(x, y, zz):
                    c.put(x, y, zz, 0)
                    alcove += 1
            c.put(x, y_deck, zz, S["chis"])       # a floor band, so the bay reads as a room

    # the screen: a low wall along the verge's outer edge, open 2 wide at each end
    screen = 0
    for zz in range(z_al0 - 1, z_al1 + 2):
        if zz - (z_al0 - 1) < 2 or (z_al1 + 1) - zz < 2:
            continue                                       # the entry and the rejoin
        if c.put(cx + half_path + verge_w - 1, y_deck + 1, zz, S["screen"]):
            screen += 1

    # THE RUNE PANEL, one of them, on the back wall, looking straight across the approach.
    z_pan = (z_al0 + z_al1) // 2
    panel = 0
    for dz in (-2, -1, 0, 1, 2):
        for y in range(y_deck + 1, y_deck + 1 + head_room):
            blk = S["void"] if (abs(dz) == 2 or y == y_deck + head_room) else S["rune_a"]
            panel += 1 if c.put(x_al_back, y, z_pan + dz, blk) else 0
    c.put(x_al_back, y_deck + 2, z_pan, S["rune_c"])
    c.put(x_al_back, y_deck + 1, z_pan - 1, S["rune_b"])
    c.put(x_al_back, y_deck + 1, z_pan + 1, S["rune_b"])
    lamps = 0
    for dz in (-3, 3):
        lamps += 1 if c.put(x_al_back, y_deck + head_room, z_pan + dz, S["lamp"]) else 0

    # THE THREE INPUTS, at player height on the panel's own wall. A lever occupies the AIR cell
    # in front of what it is attached to and `facing` is the way it LOOKS - away from that wall,
    # which here is -x, west.
    inputs = []
    for dz in (-1, 0, 1):
        cell = (x_al_back - 1, y_deck + 2, z_pan + dz * 2)
        if c.put(*cell, st(p["input"], face="wall", facing="west", powered="false")):
            inputs.append([int(v) for v in cell])

    # the cue, readable before committing - "riddle cues unreadable from public approach" is a
    # rejection condition, so the crossing says what it wants in words as well as in runes
    sx_sign, sy_sign = x_al_back - 1, y_deck + 3
    if c.put(sx_sign, sy_sign, z_pan, st(p["sign"], facing="west", waterlogged="false")):
        c.sign_text(sx_sign, sy_sign, z_pan,
                    front=["WYRM'S CROSSING", "three runes", "the wyrm knows", "the order"])

    # ---------------------------------------------------------------- the service enclosure
    # HIDDEN INSIDE THE RIM, on the far side from the riddle, reached by a hatch in the verge.
    # The outer skin and the inner face both survive the carve, so the rim is never severed and
    # nothing below the deck is left standing on air.
    s_len = max(5, int(round(float(p["svc_len"]) * sc)))
    z_sv0 = max(1, z_pan - s_len // 2)
    x_svc = cx - (x_rim_in + 1)
    svc = 0
    for zz in range(z_sv0, z_sv0 + s_len):
        for y in range(1, y_deck):
            if c.put(x_svc, y, zz, 0):
                svc += 1
        c.put(x_svc, 0, zz, S["deck"])                     # a lined floor: it is a room
    c.put(x_svc, y_deck, z_sv0,
          st(p["hatch"], facing="west", half="bottom", open="false",
             powered="false", waterlogged="false"))

    # ---------------------------------------------------------------- WHICH WAY IT FACES
    # Everything above is the CANONICAL build: the crossing runs along z with the skull at the
    # low-z end, so its front looks NORTH. Any other facing is that build TURNED about the
    # vertical - geometry, block states, sign text and every recorded coordinate together.
    #
    # The version this replaced flipped the array along z and called that a facing, and it was
    # wrong twice over. A mirror is not a rotation: it reverses handedness, so it would turn an
    # inner_left stair into an inner_right one, which is why `kit._FLIP_SHAPE` has no business
    # here even though `kit.flip` is the obvious helper to reach for. And a z flip can never put
    # the crossing's LENGTH on x, which is the only orientation that fits the Prism Reach - 45
    # blocks along U against a lot 63 along V. **A `facing` that is accepted and does nothing is
    # this repo's most repeated failure shape**, and on this module it decides whether the thing
    # fits its own plot at all.
    k = _QUARTER[facing]
    dims = (W, L)
    _turn(c, k)
    cx, _y0, cz = _turn_point((cx, 0, L // 2), k, dims)
    inputs = [list(_turn_point(tuple(i), k, dims)) for i in inputs]
    path_box = _turn_box((cx_path0, 0), (cx_path1, L - 1), k, dims)
    alcove_box = _turn_box((x_al_back - (rim_w - 1), z_al0), (x_al_back, z_al1), k, dims)
    skull_box = _turn_box((cx - (hw + 1), zf), (cx + (hw + 1), z1), k, dims)
    panel_pt = _turn_point((x_al_back, y_deck + 2, z_pan), k, dims)
    # THE ASYMMETRY IS A BAND ACROSS THE WHOLE WIDTH, not a patch on one flank: the alcove is
    # cut into the +x rim and the service crawl into the -x one at the same stations, so the
    # band a symmetry check must excuse spans the full section and exactly those rows.
    asym_box = _turn_box((0, min(z_al0, z_sv0) - 2),
                         (W - 1, max(z_al1, z_sv0 + s_len - 1) + 2), k, dims)

    # ---------------------------------------------------------------- the bypass, MEASURED
    # ...AFTER the turn, so this also proves the turn. An intrusion RAISES, because "any blocked
    # main route" is a rejection condition and one that is only ever hoped for is not one.
    (px0, pz0), (px1, pz1) = path_box
    intrusions = [(x, y, z)
                  for z in range(pz0, pz1 + 1) for x in range(px0, px1 + 1)
                  for y in range(y_deck + 1, y_deck + 1 + head_room)
                  if c.solid(x, y, z)]
    if intrusions:
        raise AssertionError(
            f"Wyrm's Crossing built into its own public bypass at {intrusions[:4]}")

    if p.get("stand"):
        wx, wy, wz = (int(round(float(v))) for v in p["stand"])
        c.world_origin = (wx - cx, wy, wz - cz)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {
        "kind": "wyrm", "form": "wyrm_crossing", "scale": sc,
        "facing": facing, "facing_vec": list(_VEC[facing]), "quarter": k,
        # THE LENGTH LIES ON x AFTER AN ODD QUARTER TURN, and it is recorded rather than left to
        # be inferred: the one caller that has to know - a lot 63 along V by 36 along U - cannot
        # read it off a bounding box without already knowing the answer.
        "long_axis": "z" if k % 2 == 0 else "x",
        "across_axis": "x" if k % 2 == 0 else "z",
        "centre": [int(cx), int(cz)],
        "size": [int(c.ids.shape[2]), int(c.ids.shape[0]), int(c.ids.shape[1])],
        # everything a check needs, so nothing downstream has to re-derive the geometry it is
        # meant to be judging - the drift two tools measuring the same thing always produce
        "path": {"x_lo": px0, "x_hi": px1, "z_lo": pz0, "z_hi": pz1,
                 "y_lo": y_deck + 1, "y_hi": y_deck + head_room, "deck_y": y_deck},
        "asym_box": asym_box,
        "rune_inputs": inputs,
        "alcove": {"box": alcove_box, "floor_y": y_deck, "panel": list(panel_pt)},
        # the head's own footprint, RECORDED, because its chin lands on the same courses a rib
        # foot does and nothing looking at block names alone can tell the two apart
        "skull_box": skull_box, "skull_base_y": base,
        "features_built": {
            "rim_anchors": rim_cells, "abutments": anchors, "deck": deck_cells, "colonnade": pier_cells,
            "corbels": trim_cells, "recesses": recess,
            "ribs": n_rib, "spine_segments": len(rib_apex), "spine": spine,
            "skull": 1, "skull_break": skull_open, "eye_sockets": sockets, "brow": brow,
            "teeth": teeth, "jaw_buttresses": butt,
            "alcove": alcove, "screen": screen,
            "rune_panel": 1, "rune_panel_cells": panel, "rune_inputs": len(inputs),
            "rune_lamps": lamps, "service_enclosure": 1, "service_void": svc,
            "path_clear": True,
        },
    }
    return c


# ----------------------------------------------------------------------------- form "serpent"
# THE RETIRED CAUSEWAY ORNAMENT, kept verbatim and reachable only by name.
#
# It is a pale wyrm reared off a black milestone: a coil at the base of a stub, a free S-curve
# spent entirely on the outline, a flared hood, and a head standing proud of it. Everything about
# it was right for the job it had - the isthmus's Hollow Reach, where there is nothing behind a
# sculpture but open sky, so the SILHOUETTE is the only channel that survives the distance and a
# hood is a plane, which is the shape this medium gives away free.
#
# It is not right for Wyrm's Crossing, and `PARK_VISUAL_AND_BUDGET_SPEC.md` says so in the first
# line of that setpiece's rejection conditions: "full free-standing snake coil". W1 needs a
# threshold you walk through, which is what `build_wyrm`'s default form now builds. This one
# survives because `isthmus.GAPS` still sites it and `test_isthmus` requires two creatures a
# span, and the two assets Jack removed from that file are the only replacements that exist -
# so deleting it here would silently cost the causeway a stop. That is a program decision.
def _build_serpent(p: dict, donors=None) -> Canvas:
    sc = float(p.get("scale", 1.0))
    fx = 1 if int(p.get("face", 1)) >= 0 else -1
    stone_h = max(4, int(round(float(p["stone_h"]) * sc)))
    body_r = float(p["body_r"]) * sc
    rise = max(8, int(round(float(p["rise"]) * sc)))
    hw_hood = float(p["hood_w"]) * sc
    hh_hood = float(p["hood_h"]) * sc

    y_stone = 2 + stone_h - 1                  # the milestone's own last shaft course
    y_hood = y_stone + rise + 4
    SX, SZ = 35, 25
    SY = int(y_hood + hh_hood + 4)
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("post", "band", "body", "belly", "mark", "eye")}
    cx, cz = SX // 2, SZ // 2

    # ---- THE MILESTONE: a 7x7 footing, a banded 5x5 stub, a 3x3 cap. Plain on purpose.
    for y in (0, 1):
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                c.put(cx + dx, y, cz + dz, S["band"])
    for y in range(2, y_stone + 1):
        blk = S["band"] if (y - 2) % 3 == 0 else S["post"]
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                c.put(cx + dx, y, cz + dz, blk)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            c.put(cx + dx, y_stone + 1, cz + dz, S["band"])

    ce, cw = max(6, int(p["band_every"])), max(1, int(p["band_wide"]))
    marks = 0

    def _sweep(path, r_of, phase=0):
        """One tapering tube, drawn as a dense sweep of spheres.

        DENSE, because a swept feature whose cells are only DIAGONAL neighbours is not
        connected in this project's sense, and that has cost it ear tips, ossicones, a whole
        dragonfly and - on this very generator's first pass - a one-cell tail tip that shipped
        as a second component while everything else audited clean.
        """
        nonlocal marks
        for i, (px, py, pz, t) in enumerate(path):
            dark = ((i + phase) % ce) < cw
            c.sphere(px, py, pz, r_of(t), S["mark"] if dark else S["body"])
            marks += 1 if dark else 0

    # ---- THE COIL, one and a half turns at the base. It anchors the animal, it gives the PLAN
    # view a pair of concentric rings, and it is deliberately not asked to carry the outline.
    turns = float(p["turns"])
    theta0 = -turns * 2 * math.pi               # ...so the last station points along +x
    y0c, y1c = 3.6, y_stone + 0.6
    steps = max(50, int(round((y1c - y0c) * 11)))
    coil = []
    for i in range(steps + 1):
        t = i / float(steps)
        y = y0c + (y1c - y0c) * t
        rad = 2 + body_r * 0.62 + 0.55
        th = theta0 + turns * 2 * math.pi * t
        coil.append((cx + fx * rad * math.cos(th), y, cz + rad * math.sin(th), t))
    _sweep(coil, lambda t: body_r * (0.72 + 0.28 * t))

    # the belly: the lowest cell of each of the coil's own columns, so the tube has an
    # underside and does not read as one flat tone wrapped round a stone
    for (px, py, pz, _t) in coil[::2]:
        ix, iz = int(round(px)), int(round(pz))
        for iy in range(int(py - body_r - 2), int(py + body_r + 2)):
            if c.solid(ix, iy, iz) and not c.solid(ix, iy - 1, iz):
                if c.get(ix, iy, iz) == S["body"]:
                    c.put(ix, iy, iz, S["belly"])
                break

    # ---- THE FREE TAIL, off the bottom of the coil, out past the footing and flicked up. It
    # is what stops the base being a symmetrical doughnut, and it is grown from the coil's own
    # first station so it cannot arrive detached.
    tx, ty, tz, _ = coil[0]
    tail = []
    for i in range(41):
        t = i / 40.0
        a, b, d = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        tail.append((a * tx + b * (tx + fx * 2.6) + d * (tx + fx * 5.4),
                     a * ty + b * (ty - 1.4) + d * (ty + 2.6),
                     a * tz + b * (tz - 2.6) + d * (tz - 4.4), t))
    _sweep(tail, lambda t: max(0.85, body_r * (0.66 - 0.30 * t)))

    # ---- THE S. Nineteen courses of free rise, forward then back then forward, in the plane
    # the body actually bends in - which is the plane a visitor still walking toward the stop
    # is looking straight at. This is the whole outline of the piece.
    nx, ny, nz, _ = coil[-1]
    hx, hy, hz = cx + fx * 1.2, y_hood, cz
    # THE S SWINGS IN Z AS WELL AS IN X, and that is not decoration. Kept purely in the x-y
    # plane the curve is invisible from the one bearing a visitor standing on the spine
    # actually has - it foreshortens into a straight vertical, and the animal reads as a post
    # with a disc on it. A lateral weave costs nothing, keeps the profile's S intact, and gives
    # the head-on view a body that moves.
    P = [(nx, ny, nz),
         (nx + fx * 5.6, ny + rise * 0.34, nz + 6.0),
         (cx - fx * 3.4, ny + rise * 0.72, cz - 5.6),
         (hx, hy - hh_hood * 0.35, hz)]
    esses = []
    n = 76
    for i in range(n + 1):
        t = i / float(n)
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        d = 3 * (1 - t) * t * t
        e = t ** 3
        esses.append((a * P[0][0] + b * P[1][0] + d * P[2][0] + e * P[3][0],
                      a * P[0][1] + b * P[1][1] + d * P[2][1] + e * P[3][1],
                      a * P[0][2] + b * P[1][2] + d * P[2][2] + e * P[3][2], t))
    _sweep(esses, lambda t: body_r * (1.0 - 0.22 * t), phase=7)

    # ---- THE HOOD: a flared plate, two thick, square to the walkway. Its DARK RIM is what
    # draws the outline at distance - a pale plate against a pale sky is a shape with no edge -
    # and the two eyespots are the pattern that makes it a hood rather than a paddle.
    hood, rim, spots = 0, 0, 0
    for dz in range(-int(hw_hood) - 1, int(hw_hood) + 2):
        for dy in range(-int(hh_hood) - 1, int(hh_hood) + 2):
            q = (dz / hw_hood) ** 2 + (dy / hh_hood) ** 2
            if q > 1.0:
                continue
            blk = S["mark"] if q > 0.84 else S["body"]
            for k in range(2):
                if c.put(int(round(hx)) - fx * k, int(round(hy)) + dy, cz + dz, blk):
                    hood += 1
                    rim += 1 if blk == S["mark"] else 0
    for side in (-1, 1):
        ez = cz + int(round(side * hw_hood * 0.46))
        for dz in range(-1, 2):
            for dy in range(-1, 2):
                # a PLUS, not a square: a 3x3 of dark on a 2-thick plate is a hole punched
                # through it, and the pair then reads as two windows rather than as markings
                if abs(dz) + abs(dy) > 1:
                    continue
                if c.get(int(round(hx)), int(round(hy)) + dy, ez + dz) == S["body"]:
                    c.put(int(round(hx)), int(round(hy)) + dy, ez + dz, S["mark"])
                    spots += 1

    # ---- THE NECK THROUGH THE HOOD, AND THE HEAD IN FRONT OF IT. The head has to stand PROUD
    # of the plate or the whole thing reads as a paddle with a bump on it.
    c.line((hx, hy - hh_hood * 0.4, hz), (hx + fx * 2.0, hy + hh_hood * 0.34, hz),
           body_r * 0.82, S["body"])
    ex_h, ey_h = hx + fx * 4.4, hy + hh_hood * 0.52
    c.ellipsoid(ex_h, ey_h, hz, 2.9, 1.8, 2.1, S["body"])
    # the snout, a straight taper forward off the skull - the elephant's trunk primitive
    c.line((ex_h + fx * 1.0, ey_h + 0.1, hz), (ex_h + fx * 3.4, ey_h - 0.7, hz), 1.30, S["body"])
    c.line((ex_h + fx * 2.6, ey_h - 0.5, hz), (ex_h + fx * 4.4, ey_h - 1.1, hz), 0.80, S["body"])
    # THE OPEN JAW, hung under the snout with air between them. The gap is the feature: a closed
    # muzzle at this size is a blunt end, and a blunt end is what made the felid skull read as
    # a deer.
    c.line((ex_h + fx * 0.6, ey_h - 1.9, hz), (ex_h + fx * 3.8, ey_h - 3.0, hz), 1.00, S["belly"])

    # ---- EYES, taken off the BUILT surface rather than from a radius. The OUTERMOST solid cell
    # of the row, so by construction nothing stands in front of one.
    #
    # IT SEARCHES FOR A ROW WIDE ENOUGH TO CARRY A PAIR, and that is not fussiness. Fixed at
    # one computed offset it landed on a course where the skull is two cells across and the
    # half-cell centring made those two ASYMMETRIC about the midline - so one side found a
    # block, the other found air, and the wyrm shipped with ONE eye, twice, with no error
    # anywhere and nothing in the audit, the component count or the bill of materials to say
    # so. A feature that can silently half-exist has to be measured, not computed.
    eyes = 0
    seat = None
    for dy in (0, 1, -1):
        for step in (1.2, 0.4, 2.0):
            ex, ey = int(round(ex_h + fx * step)), int(round(ey_h)) + dy
            zs = [z for z in range(int(round(hz)) - 4, int(round(hz)) + 5) if c.solid(ex, ey, z)]
            if len(zs) >= 3:
                seat = (ex, ey, zs)
                break
        if seat:
            break
    if seat:
        ex, ey, zs = seat
        for z in (min(zs), max(zs)):
            c.put(ex, ey, z, S["eye"])
            eyes += 1

    if p.get("stand"):
        wx, wy, wz = (int(round(float(v))) for v in p["stand"])
        c.world_origin = (wx - cx, wy, wz - cz)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    # `hood_plane` is RECORDED because the hood's rim and the body's bands are the same block,
    # so nothing downstream can tell one from the other by looking - and the one thing worth
    # checking about this animal is that the head stands forward of the plate rather than
    # buried in it. A test that took every `black_wool` cell would be measuring the tail.
    c.meta = {"kind": "wyrm", "form": "serpent", "scale": sc,
              "facing": [fx, 0], "hood_plane": int(round(hx)),
              "features_built": {"coil_stations": len(coil), "tail": 1, "rise": len(esses),
                                 "hood": hood, "hood_rim": rim, "eyespots": spots,
                                 "bands": marks, "skull": 1, "jaw": 1, "eyes": eyes}}
    return c


build = build_wyrm
DEFAULTS = WYRM
