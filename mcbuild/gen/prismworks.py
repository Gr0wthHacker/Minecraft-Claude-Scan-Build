"""Prismworks generators: bounded vertical parkour, signal maze, and co-op vault.

These build physical, auditable play spaces. Server payment, player timing, and
moving-player bubble behavior remain explicitly in-game verification contracts.

WHAT CHANGED, AND WHY IT HAD TO
-------------------------------
The first Prismworks pass shipped 5,988 blocks for a landmark whose locked budget is
32,000-40,000 (PARK_VISUAL_AND_BUDGET_SPEC.md section 4). It read as a wire diagram of a
Spire rather than a Spire: a 1x1 mast at each corner, a bare 2x2 water column with no
casing at all, and thirty-four one-block landings hung off single-cell braces. Every check
in this repo passed it, because every check here asks whether a block is legal, supported,
affordable and connected - and a thin build is all four.

The Spire is now 46,157 blocks in a 69x144x69 box, over the locked band by 15% and kept
there deliberately: the park's standing instruction is that over budget is acceptable when
the blocks are doing real work, and what came OUT on the way here was 10,786 blocks of
stacked podium floor - a seven-course tier with its own full plate and wall ring over a
machine base that already had both. That was padding at any budget. Nothing that carries a
player, a sightline or a load was thinned.

Three rules govern the rebuild, and they are the spec's own "functional truth" clause said
as geometry:

* **Nothing is decoration.** Every rib carries a landing bracket or a balcony, every collar
  is a service deck reaching the bubble casing, every catch ring is the fall coverage for
  the act above it, and the outer lattice is what the landings hang from. There is no cell
  in the Spire whose only job is mass.
* **A route is a LINE, not dots.** The rejection condition is "disconnected parkour dots".
  Landings are bracketed radially inward to the lattice - radially, because the jumps are
  tangential, so a bracket can never bridge the gap it stands beside.
* **Water is enclosed before it is placed.** `fluids.escapes` and `fluids.unenclosed` run
  over the finished canvas inside the generator and RAISE. The log flume drained 199,959
  cells to Y-1908 because only the ride path was ever checked; the bubble shaft here is a
  hundred-and-twenty-course column of source water and is exactly the same shape of risk -
  cutting a boarding hole in its casing drained 53,817 cells on the first attempt at this.

AND IT HAS TO READ AT THREE DISTANCES, which is a separate bar from any of that. The
landmark density table asks for an unmistakable silhouette at 50+, visible structural
rhythm at 15-35, and craft detail at 1-12. Two things here exist only because the renders
said so and no measurement could have: the ribs are TWO-TONE (built black all through, the
skin came out as one opaque dark mass and the bubble core, the masts and every lit landing
were behind it), and every third ring beam is a coloured prism rail, which is what gives
the middle distance its layers. The crown is sized to the tower it caps for the same
reason - a fixed nine-block crown on a fifty-three-wide Spire is not one dominant gesture.

ACT ORDER. `PRISMWORKS_PARKOUR_BRIEF.md`'s altitude table numbers the acts bottom-up while
its own guest sequence is a one-way DESCENT from the launch deck, so the two cannot both be
read literally. The acts here are numbered in the order a runner meets them, which is what
`PARK_FULL_BUILD_SPEC.md` P4/P2 describes: I readable ledges and gates, II lateral transfers
and frame crossings plus the major controlled plunge, III the high-contrast finale ending in
a controlled drop through a lit gate ring into an enclosed catch. The bands are recorded in
the sidecar so a world-level verifier owns the claim rather than this docstring.
"""
from __future__ import annotations

import math

from .. import fluids
from .canvas import Canvas

#: Defaults matching `park_final.world.json`'s own Prism Ascent module, so a bare
#: `build({"kind": "ascent"})` is the Spire the park actually sites rather than a smaller
#: variant that lands under the locked density band. (PRISMWORKS_GENERATOR.md still describes a
#: "nominal 88 block lift"; the WorldSpec has always overridden it, and now the config does too.)
PRISMWORKS = {
    "kind": "ascent",
    "height": 130,
    "radius": 26,
    "seed": 0,
}

CORE = "stone"
FRAME = "polished_blackstone_bricks"  # the machine land's own dark stone, CHEAP tier.
                               # It was `cobblestone`, which was
                               # 11,873 cells of the Spire alone and the single ugliest surface
                               # in the park - a quarry pile standing in for a machine base.
DRESS = "stone_bricks"
DECK = "smooth_stone"          # `ok` tier: collars, kerbs, balconies and the court carry the
                               # okay-accent band the material policy wants at 10-16%.
PAVE = "stone"                 # ...and the big cheap plates that would blow straight through it
DARK = "black_wool"
PRISM = ("cyan_wool", "light_blue_wool", "blue_wool", "white_wool")
LIGHT = "ochre_froglight"
PANE = "glass_pane"            # `ok` tier, and water will not flow into a pane cell
BARS = "iron_bars"             # `ok` tier: observer screens, so a runner cannot be entered upon

#: Sprint-jump reach, from PRISMWORKS_PARKOUR_BRIEF.md's move table. Centre-to-centre.
JUMP_MIN, JUMP_MAX = 3.0, 4.5


# ----------------------------------------------------------------- primitives

def _fill(c, x0, x1, y0, y1, z0, z1, block, **props):
    # `block` may be the integer 0, which is how a generator says AIR - carving is as much a
    # drawing operation here as filling, and every aperture in this file is carved.
    s = block if isinstance(block, int) else (c.state(block, **props) if props else c.state(block))
    for y in range(y0, y1 + 1):
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                c.put(x, y, z, s)


def _plate(c, x0, x1, z0, z1, y, block=CORE):
    _fill(c, x0, x1, y, y, z0, z1, block)


def _ring(c, x0, x1, z0, z1, y, block, t=1):
    """One course of a rectangular ring `t` cells thick."""
    s = c.state(block)
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            if x < x0 + t or x > x1 - t or z < z0 + t or z > z1 - t:
                c.put(x, y, z, s)


def _walls(c, x0, x1, y0, y1, z0, z1, block, t=1):
    for y in range(y0, y1 + 1):
        _ring(c, x0, x1, z0, z1, y, block, t)


def _post(c, x, z, y0, y1, block=CORE, w=1):
    _fill(c, x, x + w - 1, y0, y1, z, z + w - 1, block)


def _rail_x(c, x0, x1, z, y, block=BARS):
    """A straight bar/pane/fence run along X, with its connections actually set.

    A pane or bar with every side false renders as a lone post rather than as a screen -
    CLAUDE.md records that costing a build once already.
    """
    for x in range(x0, x1 + 1):
        c.put(x, y, z, c.state(block, east="true", west="true",
                               north="false", south="false", waterlogged="false"))


def _rail_z(c, z0, z1, x, y, block=BARS):
    for z in range(z0, z1 + 1):
        c.put(x, y, z, c.state(block, north="true", south="true",
                               east="false", west="false", waterlogged="false"))


def _rail_ring(c, x0, x1, z0, z1, y, block=BARS):
    _rail_x(c, x0, x1, z0, y, block)
    _rail_x(c, x0, x1, z1, y, block)
    _rail_z(c, z0, z1, x0, y, block)
    _rail_z(c, z0, z1, x1, y, block)


def _clear(c, x, y0, y1, z):
    for y in range(y0, y1 + 1):
        c.put(x, y, z, 0)


#: the block a wall sign hangs on is the one OPPOSITE the way it faces
_BEHIND = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}
_SIGNS: list = []


def _sign(c, x, y, z, facing, lines):
    """A wall sign, plus the promise that something is behind it.

    A sign on a column that happens to have an opening in it draws exactly like one on a wall,
    and a connectivity check catches only the ones that are not diagonally touching something
    else. `check_signs` is what actually catches it, and it runs before the canvas leaves here.
    """
    c.put(x, y, z, c.state("oak_wall_sign", facing=facing, waterlogged="false"))
    c.sign_text(x, y, z, front=[str(l)[:15] for l in lines])
    _SIGNS.append((c, x, y, z, facing))


def check_signs(c, what: str):
    loose = []
    for cc, x, y, z, facing in _SIGNS:
        if cc is not c:
            continue
        dx, dz = _BEHIND[facing]
        if not c.solid(x + dx, y, z + dz):
            loose.append((x, y, z, facing))
    if loose:
        raise ValueError(f"{what}: {len(loose)} wall sign(s) hang on nothing, first {loose[:3]}")
    return len([1 for cc, *_ in _SIGNS if cc is c])


def prune_orphans(c, what: str, max_size: int = 8) -> int:
    """Drop cells the route's own headroom carve stranded, and RAISE if a real piece breaks off.

    The route is built last on purpose - a playable landing has to win any cell it shares - and
    carving three courses of headroom over a pad can cut a louvre fin or a ring beam in two. The
    stranded piece is one or two cells and is not structure; a large orphan is a structural
    break and must not be silently deleted, which is the difference between a sweep and a
    cover-up.
    """
    import numpy as np

    from .. import morph
    labels, sizes = morph.components(c.ids > 0, conn=6)
    if len(sizes) <= 1:
        return 0
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    keep = int(np.argmax(counts))
    dropped = 0
    for lab in range(1, len(counts)):
        n = int(counts[lab])
        if lab == keep or not n:
            continue
        if n > max_size:
            ys, zs, xs = np.where(labels == lab)
            raise ValueError(f"{what}: a {n}-cell piece at "
                             f"({int(xs[0])}, {int(ys[0])}, {int(zs[0])}) is not connected to the "
                             f"rest of the design - that is a structural break, not a stray")
        c.ids[labels == lab] = 0
        dropped += n
    return dropped


def _water_cells(c):
    out = []
    for y in range(c.sy):
        for z in range(c.sz):
            for x in range(c.sx):
                if c.get(x, y, z) > 0 and c.get_name(x, y, z).split(":")[-1] == "water":
                    out.append((x, y, z))
    return out


def _cell_map(c):
    cells = {}
    for y in range(c.sy):
        for z in range(c.sz):
            for x in range(c.sx):
                if c.get(x, y, z) > 0:
                    cells[(x, y, z)] = c.get_name(x, y, z).split(":")[-1]
    return cells


def check_water(c, what: str):
    """Every water cell is enclosed, and the flood reaches nowhere it was not meant to.

    Called by every kind that places water, BEFORE the canvas leaves the generator. `escapes`
    and `unenclosed` answer different questions and a water design needs both: the first says
    the flood stayed inside the geometry that was drawn for it, the second says each cell has
    a bed and no open side over a hole. An empty answer from both is the only acceptable one.
    """
    wet = _water_cells(c)
    if not wet:
        return {"water": 0, "escapes": 0, "unenclosed": 0}
    cells = _cell_map(c)
    bounds = (0, 0, 0, c.sx - 1, c.sy - 1, c.sz - 1)
    out = fluids.escapes(cells, wet, wet, bounds)
    if out:
        raise ValueError(f"{what}: water escapes its envelope at {len(out)} cell(s), "
                         f"first {out[:3]} - an unenclosed shaft drains the whole design")
    loose = fluids.unenclosed(cells, allow=wet)
    if loose:
        raise ValueError(f"{what}: {len(loose)} water cell(s) have no bed or an open side, "
                         f"first {loose[:3]}")
    return {"water": len(wet), "escapes": 0, "unenclosed": 0}


# =================================================================== the ascent

def _ascent_levels(H):
    """The Spire's fixed vertical programme, in canvas courses.

    THE BASE IS ONE ROOM WITH A SETBACK, NOT TWO STACKED PODIUMS. It was a machine base, a
    seven-course tier and a court deck on top - three full-footprint plates and two full wall
    rings for one usable room, which at the WorldSpec's 130x26 Spire came to about 7,800 blocks
    of floor nobody stands on. A setback gives the same stepped profile for the cost of a
    terrace ring, and the eight courses it gives back go to the parkour route.
    """
    return {
        "found": 0,                 # foundation plate
        "base_lo": 1, "base_hi": 8,   # machine base: catches, service gallery, return run
        "mezz": 5,                  # service mezzanine inside the base
        "terrace": 9,               # the setback shelf, and the base's outer observer terrace
        "set_hi": 11,
        "court": 12,                # Calibration Court deck - the datum, "B"
        "spire_lo": 13,
        "water_top": H - 6,         # top of the bubble column and the launch deck course
        "crown_lo": H - 3,
        "crown_hi": H + 11,
    }


def _cage_half(y, L, R):
    """Half-width of the tapering outer lattice at course `y`.

    The Spire narrows as it rises, which is what makes the ribs read as TAPERED and what puts
    every fall line from an act inside the catch ring beneath it: the route above a ring is
    always at a smaller radius than the ring itself. The taper stops at R-6 rather than running
    in to the mast cage - a landing circle that reaches the masts puts a pad and its carved
    headroom inside a structural column.
    """
    lo, hi = L["spire_lo"], L["water_top"]
    t = 0.0 if hi <= lo else max(0.0, min(1.0, (y - lo) / (hi - lo)))
    return int(round(R - t * max(4, R - 10)))


def _bracket(c, x, y, z, cx, cz, block=FRAME, limit=14):
    """Tie an outer landing back to the Spire, RADIALLY.

    Radially, because the jumps are tangential: a bracket laid the other way would bridge the
    very gap it stands beside and the act would stop being parkour. One course below the pad,
    so it never eats the landing's headroom.
    """
    yy = y - 1
    if yy < 1:
        return 0
    s = c.state(block)
    n = 0
    px, pz = x, z
    for _ in range(limit):
        if (px, pz) != (x, z) and c.solid(px, yy, pz):
            return n
        c.put(px, yy, pz, s)
        n += 1
        if px == cx and pz == cz:
            return n
        if abs(px - cx) >= abs(pz - cz) and px != cx:
            px += 1 if px < cx else -1
        elif pz != cz:
            pz += 1 if pz < cz else -1
        else:
            px += 1 if px < cx else -1
    return n


def _catch_ring(c, cx, cz, y, half_in, half_out):
    """A collar that catches a fall from anywhere in the act above it.

    Two courses: a solid bed, and over it a rim laid by Chebyshev radius - a solid outer kerb, a
    THREE-WIDE water gutter, then walkable deck in to the inner edge. Three wide because a plunge
    is aimed at it from twelve courses up and a one-cell gutter is not a catch, it is a target.

    Every water cell's four side neighbours are therefore either water or a solid kerb, and the
    bed under it is the course below, so the gutter cannot leak - which is the whole reason it is
    built by radius rather than as three separate rings that can drift apart when the caller
    changes a thickness.
    """
    _ring(c, cx - half_out, cx + half_out, cz - half_out, cz + half_out, y - 1, FRAME,
          half_out - half_in + 1)
    water = c.state("water", level="0")
    kerb, deck = c.state(DECK), c.state(DRESS)
    for z in range(cz - half_out, cz + half_out + 1):
        for x in range(cx - half_out, cx + half_out + 1):
            d = max(abs(x - cx), abs(z - cz))
            if d > half_out or d < half_in:
                continue
            if d == half_out:
                c.put(x, y, z, kerb)
            elif half_out - 3 <= d <= half_out - 1:
                c.put(x, y, z, water)
            else:
                c.put(x, y, z, deck)


def _ascent(p):
    H = max(54, min(140, int(p["height"])))
    R = max(12, min(28, int(p["radius"])))
    side = R * 2 + 17
    cx = cz = side // 2
    L = _ascent_levels(H)
    c = Canvas(side, L["crown_hi"] + 3, side)

    f0, f1 = cx - R - 4, cx + R + 4             # podium footprint, sized to the cage
    g0, g1 = cx - R - 1, cx + R + 1             # court footprint (the setback)
    YW = L["water_top"]

    # ---------------------------------------------------------- machine base
    # "Broad lower machine base": the thing the whole Spire stands in, holding the catch hall,
    # the service gallery, the checkpoint bays and the one-way return run. It is the reason a
    # failed player never walks back up through the course.
    _plate(c, f0, f1, f0, f1, L["found"], CORE)
    _walls(c, f0, f1, L["base_lo"], L["base_hi"], f0, f1, DRESS, t=2)
    for i in range(4):                          # corner buttresses, and they carry the setback
        bx = f0 if i in (0, 1) else f1 - 3
        bz = f0 if i in (0, 2) else f1 - 3
        _fill(c, bx, bx + 3, L["base_lo"], L["terrace"], bz, bz + 3, FRAME)
    # two service spines with doorways: the gallery reaches every catch bay without crossing
    # the public return run down the middle.
    for sx in (cx - 10, cx + 10):
        _fill(c, sx, sx, L["base_lo"], L["base_hi"] - 1, f0 + 2, f1 - 2, DRESS)
        for gz in (cz - 9, cz, cz + 9):
            _clear(c, sx, L["base_lo"], L["base_lo"] + 2, gz)
            _clear(c, sx, L["base_lo"], L["base_lo"] + 2, gz + 1)
    _plate(c, cx - 9, cx + 9, f0 + 3, f1 - 3, L["mezz"], PAVE)      # service mezzanine
    _plate(c, cx - 9, f1 - 2, cz - 2, cz + 2, L["base_lo"], DECK)   # the return run itself
    _rail_x(c, cx - 9, f1 - 2, cz - 3, L["base_lo"] + 1, BARS)
    _rail_x(c, cx - 9, f1 - 2, cz + 3, L["base_lo"] + 1, BARS)
    for yy in (L["base_lo"] + 1, L["base_lo"] + 2):    # the service door out of the base
        for zz in (cz - 1, cz, cz + 1):
            c.put(f1, yy, zz, 0)
            c.put(f1 - 1, yy, zz, 0)
    _sign(c, f1 - 2, L["base_lo"] + 2, cz + 2, "west", ["RETURN", "to Forge Deck", "practice ->"])
    # RECOVERY STAIR. A failed player lands in the catch hall, and until this existed there was
    # no way back up to the Calibration Court except the course they had just fallen off. Twenty
    # courses of stone-brick flight in a walled core, which is also the operator's way down.
    stx, stz = cx - 9, f0 + 4
    _walls(c, stx - 1, stx + 5, L["base_lo"], L["court"] - 1, stz - 1, stz + 5, DRESS, t=1)
    for k in range(L["court"] - L["base_lo"] - 1):
        yy = L["base_lo"] + k
        side = (k // 4) % 4
        i = k % 4
        px, pz, face = ((stx + i, stz, "south"), (stx + 4, stz + i, "west"),
                        (stx + 4 - i, stz + 4, "north"), (stx, stz + 4 - i, "east"))[side]
        c.put(px, yy, pz, c.state("stone_brick_stairs", facing=face, half="bottom",
                                  shape="straight", waterlogged="false"))
    _fill(c, stx, stx + 4, L["court"], L["court"], stz, stz + 4, 0)

    # ------------------------------------------------- setback and the terrace
    # The base's roof outside the setback is a public terrace at the foot of the Spire, which
    # is what makes the podium read as stepped without paying for a second full storey.
    _plate(c, f0, f1, f0, f1, L["terrace"], PAVE)
    _fill(c, g0 + 1, g1 - 1, L["terrace"], L["terrace"], g0 + 1, g1 - 1, 0)
    _rail_ring(c, f0, f1, f0, f1, L["terrace"] + 1, BARS)
    _walls(c, g0, g1, L["terrace"], L["set_hi"], g0, g1, DRESS, t=2)
    for k in range(8):                          # setback pilasters, and the observer stair bays
        ang = math.radians(45 * k)
        px = cx + int(round((g1 - g0) / 2 * 0.98 * math.cos(ang)))
        pz = cz + int(round((g1 - g0) / 2 * 0.98 * math.sin(ang)))
        _post(c, px - 1, pz - 1, L["terrace"], L["set_hi"], FRAME, w=3)
    # The court is paved as a GRID - stone field, smooth-stone bands on a four-cell pitch. It
    # marks the bypass lanes across the concourse, and it is where the okay-accent band lives:
    # a Spire of stone, cobble and wool has nowhere else to put 10-16% without inventing a
    # reason to spend it.
    _plate(c, g0, g1, g0, g1, L["court"], PAVE)
    for zz in range(g0, g1 + 1):
        for xx in range(g0, g1 + 1):
            if xx % 4 == 0 or zz % 4 == 0:
                c.put(xx, L["court"], zz, c.state(DECK))

    # ---------------------------------------------------- Calibration Court
    # Free practice, the bypass concourse, and the timed-run desk - which is deliberately NOT
    # the first thing a guest meets (PARK_FULL_BUILD_SPEC P1/P4).
    _ring(c, g0, g1, g0, g1, L["court"] + 1, DRESS, 1)
    _rail_ring(c, g0, g1, g0, g1, L["court"] + 2, BARS)
    for k in range(12):
        ang = math.radians(30 * k)
        px = cx + int(round((g1 - g0) / 2 * 0.9 * math.cos(ang)))
        pz = cz + int(round((g1 - g0) / 2 * 0.9 * math.sin(ang)))
        _post(c, px, pz, L["court"] + 1, L["court"] + 5, FRAME, w=2)
        c.put(px, L["court"] + 6, pz, c.state(PRISM[k % 4]))
    practice = []
    for i in range(8):                          # the free 6-10 move sample, at court level
        ang = math.radians(20 * i - 40)
        px = cx + int(round((R + 1) * math.cos(ang)))
        pz = cz + int(round((R + 1) * math.sin(ang)))
        py = L["court"] + 1 + (i % 3)
        _post(c, px, pz, L["court"] + 1, py - 1, FRAME)
        c.put(px, py, pz, c.state(LIGHT))
        practice.append([px, py, pz])
    _fill(c, g0 + 2, g0 + 7, L["court"] + 1, L["court"] + 4, cz - 3, cz + 3, DRESS)
    _fill(c, g0 + 3, g0 + 6, L["court"] + 1, L["court"] + 3, cz - 2, cz + 2, 0)
    _sign(c, g0 + 8, L["court"] + 2, cz, "east", ["TIMED RUN", "optional, paid", "free run ->"])
    _sign(c, g0 + 8, L["court"] + 2, cz + 2, "east", ["PRACTICE", "free, always", "no payment"])

    # ------------------------------------------------------------- four masts
    # The four structural masts run the whole height and are the only thing in the Spire that
    # does. Everything else - collars, ribs, catch rings, balconies - hangs off them.
    masts = [(cx - 8, cz - 8), (cx + 6, cz - 8), (cx - 8, cz + 6), (cx + 6, cz + 6)]
    for mx, mz in masts:
        _post(c, mx, mz, L["base_lo"], L["crown_lo"], CORE, w=3)
        for dx, dz in ((-1, 0), (0, -1)):       # two fins, not four: the outer pair is what
            for yy in range(L["base_lo"], L["crown_lo"] + 1):   # reads from outside the Spire
                c.put(mx + dx + (1 if dx == 0 else 0), yy, mz + dz + (1 if dz == 0 else 0),
                      c.state(DARK if (yy // 4) % 2 else FRAME))

    # ------------------------------------------------- bubble core and collars
    # Service collars every six courses: a walkable annulus round the casing, which is how an
    # operator reaches the water containment the brief makes a field proof.
    collars = list(range(L["court"] + 6, YW - 2, 6))
    for y in collars:
        _plate(c, cx - 5, cx + 5, cz - 5, cz + 5, y, DECK)
        _fill(c, cx - 2, cx + 2, y, y, cz - 2, cz + 2, 0)
        _rail_ring(c, cx - 5, cx + 5, cz - 5, cz + 5, y + 1, BARS)
        for mx, mz in masts:                    # spokes: a collar is reachable from a mast
            _bracket(c, mx + 1, y + 1, mz + 1, cx, cz, FRAME, limit=12)
    # service ladder, base to launch, on the inner face of one mast
    lx, lz = masts[0][0] + 3, masts[0][1] + 1
    for y in range(L["court"] + 1, YW):
        c.put(lx - 1, y, lz, c.state(CORE))
        c.put(lx, y, lz, c.state("ladder", facing="east", waterlogged="false"))

    # ----------------------------------------------------- outer lattice cage
    # The landings hang off this. Posts are BATTERED - they step inward as the tower narrows -
    # so the taper is structural rather than drawn on.
    # THE LATTICE IS THE MIDDLE-DISTANCE READING, so its rhythm is not a budget line. At 15-35
    # blocks what a landmark has to show is "layers, supports, ribs, frames"
    # (PARK_VISUAL_AND_BUDGET_SPEC, landmark construction density), and that is exactly what the
    # ring beams every six courses, the full-height louvre skin and the X-braced bays between
    # them are. Thinning them to make a number smaller was tried and it cost the rhythm without
    # removing one block that was not doing a job. What DID come out was stacked floor - a
    # seven-course podium tier with its own plate and wall ring over a base that already had
    # both - and that is padding whatever the budget says.
    rings = list(range(L["spire_lo"] + 3, YW - 1, 6))
    w_prev = _cage_half(L["spire_lo"], L, R)
    for y in range(L["spire_lo"], YW + 1):
        w = _cage_half(y, L, R)
        wt = max(1, int(round(1 + 3 * (YW - y) / max(1, YW - L["spire_lo"]))))   # rib taper
        for sgn in (-1, 1):
            # Four cardinal ribs: tapered external blades, and the only thing a landing bracket
            # ever has to reach on the cardinal faces.
            #
            # TWO-TONE, because the palette says black wool is a RECESS and not a skin. Built
            # black all through, the ribs plus the louvres plus the bracing came out as one
            # opaque dark mass forty blocks away: no visible bubble core, no masts, and the lit
            # landings the whole silhouette is supposed to be a spiral of were behind it. The
            # OUTER cell of each blade is stone, the inner one is the recess.
            a = cx + sgn * w - (1 if sgn > 0 else 0)
            b = cz + sgn * w - (1 if sgn > 0 else 0)
            ao = a + 1 if sgn > 0 else a
            bo = b + 1 if sgn > 0 else b
            _fill(c, a, a + 1, y, y, cz - wt, cz + wt, DARK)
            _fill(c, cx - wt, cx + wt, y, y, b, b + 1, DARK)
            _fill(c, ao, ao, y, y, cz - wt, cz + wt, FRAME)
            _fill(c, cx - wt, cx + wt, y, y, bo, bo, FRAME)
        for sx in (-1, 1):                      # corner posts
            for sz in (-1, 1):
                _post(c, cx + sx * w - (1 if sx > 0 else 0), cz + sz * w - (1 if sz > 0 else 0),
                      y, y, FRAME, w=2)
        # Louvre fins, and they run the WHOLE height of the band they are in. Placed every third
        # course they were 336 single cells with no face neighbour in any direction - the
        # "disconnected dots" failure one surface out from the one the route was written to
        # avoid. A fin is a vertical line tying every ring beam to the next, or it is confetti.
        # A fin's own column MOVES as the tower narrows, and a cell one course up and one cell
        # in is a diagonal, which is not a neighbour. Each course therefore steps across from
        # the last course's face, so a fin is one line from the court to the launch deck.
        for t in range(-w + 3, w - 2, 6):
            for sgn in (-1, 1):
                a, b = cx + sgn * w, cx + sgn * w_prev
                _fill(c, min(a, b), max(a, b), y, y, cz + t, cz + t, DARK)
                a, b = cz + sgn * w, cz + sgn * w_prev
                _fill(c, cx + t, cx + t, y, y, min(a, b), max(a, b), DARK)
        w_prev = w
    for i, y in enumerate(rings):               # ring beams, and the radial spokes to the masts
        w = _cage_half(y, L, R)
        # Every third beam is a PRISM RAIL: the colour-coded band the palette asks for, on the
        # element a player actually reads the tower's layers from. Colour on structure, never
        # scattered - the rejection condition is "neon scattered everywhere".
        _ring(c, cx - w, cx + w, cz - w, cz + w, y, FRAME if i % 3 else PRISM[(i // 3) % 3], 1)
        for sgn in (-1, 1):
            _fill(c, cx + sgn * 6, cx + sgn * w, y, y, cz, cz, FRAME)
            _fill(c, cx, cx, y, y, cz + sgn * 6, cz + sgn * w, FRAME)
        # X-BRACING, AND IT IS DRAWN AS A STAIRCASE. A diagonal placed one cell per course is
        # eight isolated blocks per bay - diagonal-only adjacency is not adjacency, which is the
        # ear-tip lesson this repo has paid for more than once - so each course fills the run
        # from the previous tangential offset to this one, and the brace is a single line.
        for sgn in (-1, 1):
            prev = {}
            for k in range(7):
                yk = y + k
                if yk >= YW:
                    break
                wk = _cage_half(yk, L, R)
                for name, t in (("up", -wk + 4 * k), ("down", wk - 4 * k)):
                    t = max(-wk, min(wk, t))
                    t0 = prev.get(name, t)
                    lo, hi = min(t0, t), max(t0, t)
                    _fill(c, cx + sgn * wk, cx + sgn * wk, yk, yk, cz + lo, cz + hi, FRAME)
                    _fill(c, cx + lo, cx + hi, yk, yk, cz + sgn * wk, cz + sgn * wk, FRAME)
                    prev[name] = t

    # ------------------------------------------------------------ launch deck
    _plate(c, cx + 3, cx + R - 2, cz - 4, cz + 4, YW, DECK)
    _plate(c, cx - 4, cx + 4, cz + 3, cz + 6, YW, DECK)
    _ring(c, cx + 3, cx + R - 2, cz - 4, cz + 4, YW + 1, DRESS, 1)
    _clear(c, cx + 3, YW + 1, YW + 1, cz)
    _rail_x(c, cx + 4, cx + R - 3, cz - 4, YW + 2, BARS)
    _rail_x(c, cx + 4, cx + R - 3, cz + 4, YW + 2, BARS)
    for k in range(cz - 3, cz + 4, 3):
        c.put(cx + R - 2, YW + 1, k, c.state(LIGHT))
    # the start gate: two posts and a lintel, so the run has a threshold you step through and
    # the launch sign has a wall to hang on rather than a coordinate to float at.
    for sgn in (-1, 1):
        _post(c, cx + 4, cz + sgn * 4, YW + 1, YW + 3, DARK)
    _fill(c, cx + 4, cx + 4, YW + 4, YW + 4, cz - 4, cz + 4, PRISM[0])
    _sign(c, cx + 4, YW + 2, cz + 3, "north", ["LAUNCH", "one way down", "catches below"])

    # ------------------------------------------------------------------ crown
    # ONE dominant crown, open, entirely above the launch deck so it never competes with the
    # course for readability. Every ring is taken from the SAME taper the pinnacles follow -
    # rings and pinnacles chosen independently agreed nowhere and the crown shipped as five
    # floating hoops, which is exactly the "arbitrary crystals/towers" rejection condition.
    crown_span = L["crown_hi"] - L["crown_lo"]
    crown_base = max(7, R // 2 + 1)             # a crown sized to the tower it caps: at radius
    #                                             26 a fixed 9 read as a cap somebody forgot to
    #                                             finish, and "one dominant crown" is the spec's
    #                                             single strongest instruction about this build.

    def crown_r(k):
        return int(round(crown_base - (k / max(1, crown_span)) * (crown_base - 2)))

    _ring(c, cx - crown_base, cx + crown_base, cz - crown_base, cz + crown_base,
          L["crown_lo"], FRAME, 1)
    for sgn in (-1, 1):                         # the spider that ties the ring to the finial
        _fill(c, cx, cx + sgn * crown_base, L["crown_lo"], L["crown_lo"], cz, cz, FRAME)
        _fill(c, cx, cx, L["crown_lo"], L["crown_lo"], cz, cz + sgn * crown_base, FRAME)
    for k in range(crown_span + 1):
        rr = crown_r(k)
        y = L["crown_lo"] + k
        if k and k % 4 == 0:                    # a signal band, on the pinnacles' own radius
            _ring(c, cx - rr, cx + rr, cz - rr, cz + rr, y, PRISM[(k // 4) % 4], 1)
        for sx in (-1, 1):                      # four pinnacles, 2x2 so a step is still a face
            for sz in (-1, 1):
                for a in (rr - 1, rr):
                    for b in (rr - 1, rr):
                        c.put(cx + sx * a, y, cz + sz * b, c.state(FRAME))
    _post(c, cx, cz, L["crown_lo"], L["crown_hi"] + 2, PRISM[3])
    c.put(cx, L["crown_hi"] + 2, cz, c.state(LIGHT))
    _ring(c, cx - 2, cx + 2, cz - 2, cz + 2, L["crown_hi"], PRISM[3], 1)
    _fill(c, cx - 2, cx + 2, L["crown_hi"], L["crown_hi"], cz, cz, PRISM[3])

    # --------------------------------------------------------- observer decks
    # Outside the route, screened from it with iron bars: guests see the runner's line and
    # cannot enter it or interfere with a timed state.
    balconies = []
    for k, by in enumerate((L["court"] + 12, L["court"] + 30, L["court"] + 48)):
        if by > YW - 4:
            break
        w = _cage_half(by, L, R)
        sgn = 1 if k % 2 == 0 else -1
        x0, x1 = (cx + sgn * (w + 1), cx + sgn * (w + 5)) if sgn > 0 else (cx + sgn * (w + 5), cx + sgn * (w + 1))
        _plate(c, min(x0, x1), max(x0, x1), cz - 6, cz + 6, by, DECK)
        _rail_ring(c, min(x0, x1), max(x0, x1), cz - 6, cz + 6, by + 1, BARS)
        _rail_ring(c, min(x0, x1), max(x0, x1), cz - 6, cz + 6, by + 2, BARS)
        for zz in (cz - 6, cz, cz + 6):
            _bracket(c, cx + sgn * (w + 1), by, zz, cx, cz, FRAME, limit=6)
        balconies.append([cx + sgn * (w + 3), by + 1, cz])

    # ------------------------------------------------------------- catch hall
    # Enclosed pools under the finale and under the Act II plunge. A tank, never an open pond:
    # floor, wall ring, water, so nothing can drain into the machine base.
    def pool(px, pz, py, half, depth=2):
        _fill(c, px - half - 1, px + half + 1, py - depth - 1, py, pz - half - 1, pz + half + 1, DRESS)
        _fill(c, px - half, px + half, py - depth, py, pz - half, pz + half, "water")
        return [px, py, pz]

    finale_pool = pool(cx - R + 3, cz, L["court"], 3)
    _clear(c, cx - R + 3, L["court"] + 1, L["court"] + 4, cz)
    finish_sign = (cx - R + 3 - 3, L["court"] + 2, cz - 4)

    # ---------------------------------------------------------------- the run
    # ONE WAY, DOWNWARD, in three acts. A move is a LEDGE unless it is a gate (a framed jump),
    # a transfer (a lateral leap across a face, so the angle steps further and the radius
    # changes) or a plunge - and a plunge is never called a jump: it ends in the act's own
    # enclosed catch ring, twelve courses down, visible from the pad it leaves.
    mast_cells = {(mx + a, mz + b) for mx, mz in masts for a in range(3) for b in range(3)}
    route, acts = [], []
    plan = (("I", 10, "readable ledges and gates"),
            ("II", 10, "lateral transfers, frame crossings, and the major plunge"),
            ("III", 8, "high-contrast finale into an enclosed catch"))
    # THE MOVE COUNT IS SET BY THE VERTICAL BUDGET, not by taste. From the launch deck to the
    # last pad is sixty courses; the plunge takes twelve of them, the Act I checkpoint six, the
    # two step-offs eight, and the finale drop eight, which leaves twenty-six for the ledges.
    # Ask for forty moves and the last act ends below the Calibration Court it is supposed to
    # finish on - the first version of this loop did exactly that, and buried a catch ring
    # inside the podium.
    y = YW - 2
    y_floor = L["court"] + 8
    plunge_drop = 12
    angle = math.radians(20.0)
    move, last_xz = 0, None
    total_moves = sum(n for _, n, _ in plan) - 1
    step_drop = max(1, (y - y_floor - plunge_drop - 6 - 8) // total_moves)
    for act_index, (act_name, moves, note) in enumerate(plan):
        act_from = y
        for i in range(moves):
            plunge = (act_name == "II" and i == moves - 1)
            if plunge:
                break                     # the plunge IS the drop onto this act's catch ring
            y = max(y_floor, y - step_drop)
            w = _cage_half(y, L, R)
            transfer = (act_name == "II" and i % 4 == 3)
            # a chord of ~4.0 blocks at this radius: the brief's 3.0-4.5 sprint-jump band. A
            # transfer takes a wider bite of the circle, which is what makes it a lateral leap
            # across a face rather than one more step round it.
            # THE BAND IS MEASURED ON THE ROUNDED CELL, NOT ON THE ARC. A chord of 3.7 blocks
            # rounds to integer coordinates that can be 2.83 apart - dx 2, dz 2 - and a jump
            # the brief calls a sprint jump is then a step. The angle is opened until the pad
            # the player actually lands on is in band.
            step = 2.0 * math.asin(min(0.95, (2.1 if transfer else 1.85) / max(3.0, w)))
            prev = next((r for r in reversed(route)
                         if r[3] in ("ledge", "gate", "transfer")), None)
            for attempt in range(24):
                a = angle + step * (1.0 + 0.08 * attempt)
                x = cx + int(round(w * math.cos(a)))
                z = cz + int(round(w * math.sin(a)))
                while (x, z) in mast_cells:   # never land a pad inside a structural column
                    x += 1 if x >= cx else -1
                if prev is None:
                    break
                gap = math.dist((x, z), (prev[0], prev[2]))
                if JUMP_MIN <= gap <= JUMP_MAX:
                    break
            angle = a
            kind = "transfer" if transfer else ("gate" if move % 5 == 3 else "ledge")
            c.put(x, y, z, c.state(LIGHT if kind != "transfer" else PRISM[1]))
            _bracket(c, x, y, z, cx, cz, FRAME, limit=16)
            _clear(c, x, y + 1, y + 3, z)
            if kind == "gate":
                dx = 1 if abs(math.cos(angle)) < 0.5 else 0
                dz = 1 - dx
                # THE FRAME NEEDS A SILL, or it is an arch standing two cells clear of the pad
                # with nothing between them - eleven cells of second component, and a gate you
                # cannot tell from scenery. The sill runs ACROSS the approach, so it widens the
                # landing without shortening the jump.
                for s in (-1, 1):
                    c.put(x + dx * s, y, z + dz * s, c.state(FRAME))
                for s in (-2, 2):
                    for yy in range(y, y + 4):
                        c.put(x + dx * s, yy, z + dz * s, c.state(DARK))
                _fill(c, x + dx * -2, x + dx * 2, y + 4, y + 4, z + dz * -2, z + dz * 2, PRISM[0])
            route.append([x, y, z, kind, act_name])
            last_xz = (x, z)
            move += 1
        # ---- act boundary. Acts I and II end on their own catch ring, which is the checkpoint
        # and the fall coverage for everything above it; Act III ends on the Calibration Court,
        # so it gets no ring - one below the court deck is a ring buried in the podium.
        if act_index == len(plan) - 1:
            acts.append({"name": act_name, "note": note, "from_y": act_from, "to_y": y,
                         "moves": moves, "catch_ring_y": None,
                         "ends_on": "calibration court"})
            break
        ring_y = y - (plunge_drop if act_name == "II" else 6)
        w = _cage_half(ring_y, L, R)
        half_out, half_in = w + 1, max(4, w - 5)
        _catch_ring(c, cx, cz, ring_y, half_in, half_out)
        if act_name == "II" and last_xz:
            # A TWELVE-COURSE PLUNGE IS AIMED, not hoped for. The gutter is three wide and the
            # fall line drifts as the tower tapers, so the plunge gets its own sunk basin under
            # the pad it leaves from - five by five, four deep, walled, and part of the ring.
            px, pz = last_xz
            _fill(c, px - 3, px + 3, ring_y - 4, ring_y, pz - 3, pz + 3, DRESS)
            _fill(c, px - 2, px + 2, ring_y - 3, ring_y, pz - 2, pz + 2, "water", level="0")
            _bracket(c, px, ring_y - 4, pz, cx, cz, FRAME, limit=20)
            route.append([px, ring_y, pz, "plunge", act_name])
        rx = cx + int(round((half_in + 1) * math.cos(angle)))
        rz = cz + int(round((half_in + 1) * math.sin(angle)))
        _plate(c, rx - 1, rx + 1, rz - 1, rz + 1, ring_y, DECK)
        c.put(rx, ring_y + 1, rz, c.state("redstone_lamp", lit="false"))
        _rail_ring(c, cx - half_out, cx + half_out, cz - half_out, cz + half_out,
                   ring_y + 1, BARS)
        for mx, mz in masts:                      # the ring is reachable for service and restart
            _bracket(c, mx + 1, ring_y + 1, mz + 1, cx, cz, FRAME, limit=16)
        route.append([rx, ring_y, rz, "rest", act_name])
        acts.append({"name": act_name, "note": note, "from_y": act_from, "to_y": ring_y,
                     "moves": moves, "catch_ring_y": ring_y,
                     "catch_ring_half": [half_in, half_out]})
        # step-off: four courses out over the kerb to the next act's start pad, which sits
        # OUTSIDE the ring so its carved headroom can never punch a hole in the catch. The rail
        # gets a gate at the same bearing, or the checkpoint is a pen.
        for k in range(0, 5):
            sxp = cx + int(round((half_out + k) * math.cos(angle)))
            szp = cz + int(round((half_out + k) * math.sin(angle)))
            if k == 0:
                _clear(c, sxp, ring_y + 1, ring_y + 1, szp)
                continue
            _plate(c, sxp - 1, sxp + 1, szp - 1, szp + 1, ring_y - k, DECK)
            _bracket(c, sxp, ring_y - k, szp, cx, cz, FRAME, limit=20)
        y = ring_y - 4
    # the finale: a controlled drop through the crown-lit gate ring into the enclosed pool at
    # court level, and you step straight out east onto the return run.
    route.append([finale_pool[0], finale_pool[1], finale_pool[2], "plunge", "III"])
    _ring(c, finale_pool[0] - 4, finale_pool[0] + 4, cz - 4, cz + 4, L["court"] + 5, PRISM[0], 1)
    for k in range(4):
        _post(c, finale_pool[0] - 4 + (8 if k % 2 else 0), cz - 4 + (8 if k // 2 else 0),
              L["court"] + 1, L["court"] + 5, DARK)
    _sign(c, *finish_sign, "east", ["FINISH", "step out east", "Forge Deck"])

    # ------------------------------------------------- bubble core, built LAST
    # Last, so nothing above can punch a hole in the casing. 3x3 of source water over soul
    # sand; the column's motion is a field proof, the containment is not.
    water, soul = c.state("water", level="0"), c.state("soul_sand")
    for x in range(cx - 1, cx + 2):
        for z in range(cz - 1, cz + 2):
            c.put(x, L["found"], z, soul)
            for yy in range(L["base_lo"], YW + 1):
                c.put(x, yy, z, water)
    for yy in range(L["base_lo"], YW + 1):
        solid_band = (yy - L["base_lo"]) % 6 == 0 or yy in (L["base_lo"], YW)
        for x in range(cx - 2, cx + 3):
            for z in range(cz - 2, cz + 3):
                if abs(x - cx) < 2 and abs(z - cz) < 2:
                    continue
                corner = abs(x - cx) == 2 and abs(z - cz) == 2
                if corner or solid_band:
                    c.put(x, yy, z, c.state(CORE if corner else DRESS))
                elif abs(x - cx) == 2:
                    c.put(x, yy, z, c.state(PANE, north="true", south="true",
                                            east="false", west="false", waterlogged="false"))
                else:
                    c.put(x, yy, z, c.state(PANE, east="true", west="true",
                                            north="false", south="false", waterlogged="false"))
    # THE BOARDING APERTURE IS A HATCH, NOT A HOLE. A gap cut in the casing at court level
    # drains a ninety-course column of source water into the machine base - `check_water` caught
    # exactly that, at 53,817 cells. An OPEN trapdoor is a vertical panel that holds water and
    # that a player closes to step through, which is how a water lock is built in game and the
    # one piece of trapdoor vocabulary the corpus says this repo never uses.
    for zz in (cz - 1, cz, cz + 1):
        for yy in (L["court"] + 1, L["court"] + 2):
            c.put(cx - 2, yy, zz, c.state("oak_trapdoor", facing="east", half="bottom",
                                          open="true", powered="false", waterlogged="false"))
    _sign(c, cx - 3, L["court"] + 2, cz + 2, "west", ["BUBBLE LIFT", "close hatch,", "step in"])

    orphans = prune_orphans(c, "prism ascent")
    water_report = check_water(c, "prism ascent")
    signs = check_signs(c, "prism ascent")
    meta = {
        "kind": "prismworks/ascent", "route": route, "acts": acts,
        # The hero view, matching this module's `visual_front` anchor in park_final.world.json.
        # `tools/look.py` and `tools/panel.py` both read it: bearing 0 is the Foundry Gate
        # approach, not world +z. A design with no recorded facing says so and guesses, which
        # is how a review sheet ends up auditing a landmark's back.
        "facing": "west",
        "practice": practice, "observer_decks": balconies,
        "masts": [[mx + 1, L["court"], mz + 1] for mx, mz in masts],
        "levels": L, "water": water_report, "signs": signs, "pruned": orphans,
        "jump_band": [JUMP_MIN, JUMP_MAX],
        "requires_in_game": ["bubble_ascent", "parkour_catches", "checkpoint_behavior",
                             "timed_run_payment"],
        "interfaces": ["queue_entry", "bubble_entry", "launch_deck", "ride_exit",
                       "service_access", "observer"],
        "expensive_functional": {"redstone_lamp": "checkpoint state panel, one per act boundary"},
    }
    return c, meta


# ==================================================================== the array

#: 17x17 logical maze cells at world x = MZ0 + 2*i. Corridors are one cell wide, walls one
#: cell thick, and the border ring is closed except at the entry and the exit.
_GRID = 17
_MZ0 = 4

#: The solved route, as logical grid cells. Hand-authored rather than carved, because the
#: brief's requirement is about the SHAPE of the branches, not about maze entropy.
_ROUTE = ([(i, 0) for i in range(0, 5)] + [(4, j) for j in range(1, 5)]
          + [(i, 4) for i in range(5, 11)] + [(10, j) for j in range(5, 9)]
          + [(i, 8) for i in range(11, 17)] + [(16, j) for j in range(9, 13)]
          + [(i, 12) for i in range(15, 7, -1)] + [(8, j) for j in range(13, 17)]
          + [(i, 16) for i in range(9, 17)])

#: Wrong branches. EVERY ONE IS A LOOP: it leaves a choice point on the route and comes back
#: to a route cell, so a wrong turn costs time and never strands anybody. That is the whole
#: requirement - "wrong branches return to a known choice point, not a dead end or staff
#: route" - and it is why this maze has no cell with exactly one open neighbour.
_BRANCHES = (
    ("cyan", (4, 0), [(5, 0), (6, 0), (7, 0), (7, 1), (7, 2), (6, 2), (5, 2), (4, 2)]),
    ("light_blue", (10, 4), [(10, 3), (11, 3), (12, 3), (13, 3), (13, 4), (13, 5), (12, 5),
                             (11, 5), (11, 6), (11, 7), (11, 8)]),
    ("blue", (16, 8), [(16, 7), (15, 7), (14, 7), (14, 6), (15, 6), (16, 6), (16, 5), (15, 5),
                       (14, 5), (14, 6), (13, 6), (13, 7), (13, 8)]),
    ("white", (8, 12), [(8, 11), (7, 11), (6, 11), (5, 11), (5, 12), (5, 13), (6, 13), (7, 13),
                        (8, 13)]),
    ("cyan", (12, 12), [(12, 13), (12, 14), (13, 14), (14, 14), (14, 15), (14, 16), (13, 16),
                        (12, 16), (11, 16), (10, 16)]),
    ("light_blue", (4, 4), [(3, 4), (2, 4), (2, 5), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6),
                            (6, 7), (6, 8), (5, 8), (4, 8), (3, 8), (2, 8), (2, 9), (2, 10),
                            (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10), (9, 10),
                            (9, 11), (9, 12)]),
)

_MARKER = {"cyan": "cyan_wool", "light_blue": "light_blue_wool",
           "blue": "blue_wool", "white": "white_wool"}


def _array_open_cells():
    """World cells the maze leaves open, plus the choice points and branch membership."""
    route = list(dict.fromkeys(_ROUTE))
    branch_cells: dict[tuple, str] = {}
    paths = [route]
    for colour, join, cells in _BRANCHES:
        seq = [join] + list(cells)
        # a branch must END on the route: it comes back to a known choice point.
        paths.append(seq)
        for cell in cells:
            branch_cells[cell] = colour
    opens: set[tuple] = set()
    for seq in paths:
        for a, b in zip(seq, seq[1:]):
            # A DIAGONAL STEP IS NOT A STEP. Written as one it opens the two grid cells and a
            # bogus "connector" halfway between them, which lands on a wall corner and ships as
            # a one-cell stub with a single neighbour - a dead end, in the one design whose
            # whole contract is that it has none.
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
                raise ValueError(f"maze path steps diagonally from {a} to {b}")
            ax, az = _MZ0 + 2 * a[0], _MZ0 + 2 * a[1]
            bx, bz = _MZ0 + 2 * b[0], _MZ0 + 2 * b[1]
            opens.add((ax, az))
            opens.add((bx, bz))
            opens.add(((ax + bx) // 2, (az + bz) // 2))
    return route, branch_cells, opens


def _array_choice_points():
    """Cells where a player has to pick, and the colour that marks the correct exit."""
    route = list(dict.fromkeys(_ROUTE))
    out = []
    for colour, join, cells in _BRANCHES:
        nxt = route[route.index(join) + 1] if route.index(join) + 1 < len(route) else join
        out.append({"colour": colour, "cell": list(join), "branch_len": len(cells),
                    "correct_next": list(nxt),
                    "world": [_MZ0 + 2 * join[0], 1, _MZ0 + 2 * join[1]]})
    return out


def _array(p):
    wall_h = 5
    m0, m1 = 3, _MZ0 + 2 * (_GRID - 1) + 1        # maze bounding box, border included
    side = m1 + 6                                  # + service strip and the observer gallery
    c = Canvas(side, 14, side)
    route, branch_cells, opens = _array_open_cells()

    _plate(c, 0, side - 1, 0, side - 1, 0, CORE)                  # foundation
    _plate(c, m0, m1, m0, m1, 0, DRESS)                           # the maze floor proper
    # the solved route is paved in a different stone so a walkthrough can be read afterwards
    for x, z in sorted(opens):
        c.put(x, 0, z, c.state(FRAME if (x, z) in
                               {(_MZ0 + 2 * a[0], _MZ0 + 2 * a[1]) for a in route} else DRESS))

    wall = c.state(DARK)
    for z in range(m0, m1 + 1):
        for x in range(m0, m1 + 1):
            if (x, z) in opens:
                continue
            for y in range(1, wall_h + 1):
                c.put(x, y, z, wall)
            # the cap is the maze's one pale line, and it is `ok` tier on purpose: the material
            # policy wants 10-16% okay accents and a maze of black wool on stone brick has
            # nowhere else to put them.
            c.put(x, wall_h + 1, z, c.state("smooth_stone_slab", type="bottom",
                                            waterlogged="false"))
    # the enclosing wall, and its two apertures
    _walls(c, m0 - 1, m1 + 1, 1, wall_h + 1, m0 - 1, m1 + 1, DRESS, t=1)
    _ring(c, m0 - 1, m1 + 1, m0 - 1, m1 + 1, wall_h + 1, DECK, 1)      # coping
    entry = (m0 - 1, 1, _MZ0)
    exit_ = (m1 + 1, 1, _MZ0 + 2 * 16)
    # THE APERTURE PIERCES BOTH WALLS. The enclosing wall is at m0-1 and the maze's own border
    # column is at m0, so carving one of them leaves a door that opens onto a wall - and the
    # first cell of the solved route reads as a dead end because its only way out is blocked.
    for y in range(1, 4):
        for wall_x in (entry[0], entry[0] + 1):
            c.put(wall_x, y, entry[2], 0)
        for wall_x in (exit_[0], exit_[0] - 1):
            c.put(wall_x, y, exit_[2], 0)
    for wall_x in (entry[0], entry[0] + 1):
        c.put(wall_x, 0, entry[2], c.state(FRAME))
    for wall_x in (exit_[0], exit_[0] - 1):
        c.put(wall_x, 0, exit_[2], c.state(FRAME))

    # colour markers: ATTACHED to the wall corner at each choice point, never a floating accent
    choice_points = _array_choice_points()
    for cp in choice_points:
        wx, _, wz = cp["world"]
        blk = _MARKER[cp["colour"]]
        placed = 0
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            if c.solid(wx + dx, 1, wz + dz) and placed < 2:
                for y in range(1, wall_h + 1):
                    c.put(wx + dx, y, wz + dz, c.state(blk))
                placed += 1
        cp["markers"] = placed

    # observer / wayfinding gallery: above wall height, alongside, never into the maze
    gy = wall_h + 3
    _plate(c, m0 - 3, m1 + 3, m0 - 3, m1 + 3, gy, PAVE)
    _fill(c, m0 - 1, m1 + 1, gy, gy, m0 - 1, m1 + 1, 0)
    # THE INNER RAIL GOES ON THE DECK, NOT OVER THE HOLE. Set one cell further in it stood on
    # the void the gallery is cut around - 144 iron bars as a second component, and a railing
    # you would walk straight through.
    _rail_ring(c, m0 - 3, m1 + 3, m0 - 3, m1 + 3, gy + 1, BARS)
    _rail_ring(c, m0 - 2, m1 + 2, m0 - 2, m1 + 2, gy + 1, BARS)
    for k in range(m0 - 3, m1 + 4, 4):           # the piers the gallery stands on
        for a, b in ((k, m0 - 3), (k, m1 + 3), (m0 - 3, k), (m1 + 3, k)):
            _post(c, a, b, 1, gy - 1, FRAME)
    for k in range(m0 - 2, m1 + 3, 6):
        c.put(k, gy, m0 - 3, c.state(LIGHT))
        c.put(k, gy, m1 + 3, c.state(LIGHT))

    # rear service strip: reaches every reset/sign panel, and touches the public route nowhere
    sx0, sx1 = m1 + 2, m1 + 4
    _plate(c, sx0, sx1, m0 - 3, m1 + 3, 0, PAVE)
    _fill(c, sx1, sx1, 1, 3, m0 - 3, m1 + 3, DRESS)
    panels = []
    for i, cp in enumerate(choice_points):
        pz = m0 + 4 + i * 5
        _fill(c, m1 + 1, m1 + 1, 1, 3, pz - 1, pz + 1, DRESS)
        c.put(m1 + 1, 2, pz, c.state(_MARKER[cp["colour"]]))
        c.put(m1 + 1, 1, pz, c.state("redstone_lamp", lit="false"))
        _sign(c, sx1 - 1, 2, pz, "west", ["RESET", cp["colour"][:15], "service only"])
        panels.append([m1 + 1, 2, pz])
    _sign(c, m0 - 1, 2, _MZ0 + 1, "west", ["PRISM ARRAY", "follow colour", "wrong = loop"])
    orphans = prune_orphans(c, "prism array")
    signs = check_signs(c, "prism array")

    return c, {
        "kind": "prismworks/array", "signs": signs, "pruned": orphans, "facing": "west",
        "solved_entry": list(entry), "solved_exit": list(exit_),
        "solved_route": [[_MZ0 + 2 * a[0], 1, _MZ0 + 2 * a[1]] for a in route],
        "choice_points": choice_points, "service_panels": panels,
        "branch_cells": len(branch_cells),
        "interfaces": ["approach", "entry", "exit", "service_access", "observer"],
        "requires_in_game": ["walkthrough_route", "signage_rules"],
        "expensive_functional": {"redstone_lamp": "one reset-state panel per choice point"},
    }


# ==================================================================== the vault

def _vault(p):
    side = 39
    c = Canvas(side, 24, side)
    cx = cz = side // 2
    f0, f1 = 1, side - 2
    roof = 13

    _plate(c, f0, f1, f0, f1, 0, CORE)
    _walls(c, f0, f1, 1, roof - 1, f0, f1, DRESS, t=2)
    _plate(c, f0, f1, f0, f1, roof, DRESS)
    # A COFFERED CEILING, and it is where the okay-accent band lives. A vault of stone brick on
    # cobblestone measured 2.2% `ok` against a policy floor of 10%, and the honest place to
    # spend that is the surface everybody standing at a station is looking up at.
    for z in range(f0, f1 + 1):
        for x in range(f0, f1 + 1):
            if x % 3 == 1 or z % 3 == 1:
                c.put(x, roof, z, c.state(DECK))
    # A BUTTRESS INSIDE THE WALL IS NOT A BUTTRESS. Built flush with the shell these read as
    # nothing at all from fifteen blocks: ten courses of stone brick with no relief anywhere,
    # which is precisely the "visible structural rhythm" the landmark density table asks for and
    # the one thing the first vault render did not have. They PROJECT a cell now, and the plinth
    # and cornice project with them, so the box has a base, a top and a beat along its length.
    _ring(c, f0 - 1, f1 + 1, f0 - 1, f1 + 1, 1, FRAME, 1)                    # plinth
    _ring(c, f0 - 1, f1 + 1, f0 - 1, f1 + 1, 2, DECK, 1)
    _ring(c, f0 - 1, f1 + 1, f0 - 1, f1 + 1, roof - 2, FRAME, 1)             # cornice
    _ring(c, f0 - 1, f1 + 1, f0 - 1, f1 + 1, roof - 1, DRESS, 1)
    for k in range(f0 + 4, f1 - 3, 6):
        for a, b in ((k, f0 - 1), (k, f1 - 1), (f0 - 1, k), (f1 - 1, k)):
            _fill(c, a, a + 2, 1, roof - 2, b, b + 2, FRAME)
    # clerestory: the room's own daylight, and the thing that stops the roof reading as a lid
    _walls(c, cx - 8, cx + 8, roof + 1, roof + 4, cz - 8, cz + 8, DRESS, t=2)
    for k in range(cx - 6, cx + 7):
        for y in (roof + 2, roof + 3):
            c.put(k, y, cz - 8, c.state(PANE, east="true", west="true",
                                        north="false", south="false", waterlogged="false"))
            c.put(k, y, cz + 8, c.state(PANE, east="true", west="true",
                                        north="false", south="false", waterlogged="false"))
            c.put(cx - 8, y, k, c.state(PANE, north="true", south="true",
                                        east="false", west="false", waterlogged="false"))
            c.put(cx + 8, y, k, c.state(PANE, north="true", south="true",
                                        east="false", west="false", waterlogged="false"))
    _plate(c, cx - 8, cx + 8, cz - 8, cz + 8, roof + 5, DECK)

    # SERVICE RING between the shell and the room: maintenance isolation is a wall, not a rule.
    s0, s1 = f0 + 4, f1 - 4
    _walls(c, s0, s1, 1, roof - 1, s0, s1, FRAME, t=1)

    # Guest vestibules cross the service ring in a walled tunnel, so nobody wanders into it.
    def vestibule(x0, x1, z):
        _fill(c, x0, x1, 1, 4, z - 2, z + 2, DRESS)
        _fill(c, x0, x1, 1, 3, z - 1, z + 1, 0)
        _plate(c, x0, x1, z - 1, z + 1, 0, DECK)

    vestibule(f0, s0, cz)
    vestibule(s1, f1, cz)
    # THE DOOR PIERCES THE PLINTH TOO. A projecting plinth is a wall in front of a doorway;
    # carving only the shell leaves a threshold you step into rather than through.
    for y in range(1, 4):
        for zz in (cz - 1, cz, cz + 1):
            for xx in (f0 - 1, f0, f0 + 1, f1 - 1, f1, f1 + 1):
                c.put(xx, y, zz, 0)
    # service door, on the third face, into the ring and nowhere else
    for y in range(1, 4):
        for zz in (f1 - 1, f1, f1 + 1):
            c.put(cx, y, zz, 0)

    # ------------------------------------------------------- the three stations
    # Individually testable, physically separated, and every one of them can see the shared
    # state panel in the middle. The completion CIRCUIT is a later redstone ticket; what is
    # built here is the geometry that circuit needs, and the sidecar says so.
    stations = []
    for i, (sx, sz, facing) in enumerate(((cx - 8, cz - 6, "south"),
                                          (cx + 8, cz - 6, "south"),
                                          (cx, cz + 9, "north"))):
        _plate(c, sx - 2, sx + 2, sz - 2, sz + 2, 1, DECK)          # a raised, lit plinth
        # `back` is the station's own wall; `out` is the way its face looks, which is also the
        # way its button and its sign face. Written the other way round the button pointed INTO
        # the wall it is mounted on - legal state, wrong hardware, and nothing here checks it.
        out = 1 if facing == "south" else -1
        back = sz - 3 * out
        _fill(c, sx - 2, sx + 2, 2, 5, back, back, DRESS)
        c.put(sx, 4, back, c.state(_MARKER[("cyan", "light_blue", "blue")[i]]))
        c.put(sx, 3, back, c.state("redstone_lamp", lit="false"))
        c.put(sx, 3, back + out,
              c.state("stone_button", face="wall", facing=facing, powered="false"))
        c.put(sx - 1, 1, sz, c.state("target", power="0"))
        c.put(sx + 1, 1, sz, c.state("stone_pressure_plate", powered="false"))
        # THE SCREEN GOES OUTBOARD. Placed on both sides it stood squarely between station one
        # and the shared state panel - two courses of black wool at exactly body height - so the
        # room separated the players from the one thing all three of them have to read.
        sides = (-2, 2) if sx == cx else ((-2,) if sx < cx else (2,))
        for dx in sides:
            _fill(c, sx + dx, sx + dx, 2, 3, sz - 2, sz + 2, DARK)
        _sign(c, sx + 1, 3, back + out, facing,
              ["STATION %d" % (i + 1), "hold, then", "watch centre"])
        stations.append({"index": i + 1, "input": [sx, 3, back + out],
                         "stand": [sx, 1, sz], "facing": facing})

    # ------------------------------------------------- the shared state panel
    # One panel, four faces, tall enough that all three stations read it from where they
    # stand. "One obvious completion", not an invisible comparator state.
    _fill(c, cx - 2, cx + 2, 1, 7, cz - 2, cz + 2, DRESS)
    _fill(c, cx - 1, cx + 1, 1, 6, cz - 1, cz + 1, FRAME)
    for face, (dx, dz) in (("north", (0, -3)), ("south", (0, 3)), ("west", (-3, 0)), ("east", (3, 0))):
        for k in (-1, 0, 1):
            for y in (4, 5, 6):
                px = cx + dx + (k if dx == 0 else 0)
                pz = cz + dz + (k if dz == 0 else 0)
                c.put(px, y, pz, c.state("redstone_lamp", lit="false"))
    _fill(c, cx - 3, cx + 3, 8, 8, cz - 3, cz + 3, DECK)
    _post(c, cx, cz, 9, 9, PRISM[3])

    # ------------------------------------------------------- the solo fallback
    # Mandatory, and posted where a lone player standing in the door can read it.
    _fill(c, s0 + 2, s0 + 6, 1, 3, s1 - 4, s1 - 2, DRESS)
    _fill(c, s0 + 3, s0 + 5, 1, 2, s1 - 4, s1 - 3, 0)
    _sign(c, s0 + 3, 2, s1 - 3, "north", ["SOLO MODE", "3 in order:", "1 - 2 - 3"])
    _sign(c, s0 + 4, 2, s1 - 3, "north", ["no group?", "run the", "short sequence"])
    solo = [s0 + 4, 1, s1 - 3]
    orphans = prune_orphans(c, "resonance vault")
    signs = check_signs(c, "resonance vault")

    # lighting that is a fitting, never a floating accent
    for k in range(f0 + 6, f1 - 5, 6):
        for a, b in ((k, s0 + 1), (k, s1 - 1), (s0 + 1, k), (s1 - 1, k)):
            c.put(a, roof - 1, b, c.state(LIGHT))

    return c, {
        "kind": "prismworks/vault", "signs": signs, "pruned": orphans, "facing": "west",
        "interfaces": ["approach", "entry", "exit", "service_access"],
        "stations": stations,
        "puzzle_inputs": [s["input"] for s in stations],
        "state_panel": [cx, 5, cz],
        "solo_fallback": solo,
        "requires_in_game": ["three_input_completion_circuit", "reset_behavior",
                             "solo_fallback_sequence", "maintenance_isolation"],
        "expensive_functional": {"redstone_lamp": "shared state panel and per-station indicator"},
    }


def build(cfg: dict, donors=None):
    p = {**PRISMWORKS, **(cfg or {})}
    kind = p["kind"]
    if kind not in {"ascent", "array", "vault"}:
        raise ValueError(f"unknown Prismworks kind {kind!r}; have ascent, array, vault")
    if kind == "ascent":
        canvas, meta = _ascent(p)
    elif kind == "array":
        canvas, meta = _array(p)
    else:
        canvas, meta = _vault(p)
    canvas.meta = meta
    return canvas
