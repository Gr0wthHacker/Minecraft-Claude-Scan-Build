"""A ruined ring-gate - the nether portal as a circle of blackstone masonry.

WHY A RING, AND WHY THERE. The scene plan (2026-08-21) measured 628 lowland columns open to real
sky, 493 of them one blob at X-24186..-24158 / Z30015..30041 - the shaft players descend to enter
the underworld. The ring stands in that beam at (-24171, 30025): 96% of its footprint in daylight,
zero lanterns under it, ground Y45-52, headroom 139. Arriving means landing at a ruined gate and
stepping through it into the scene. Behind it the massif crests and falls off the rim into void,
so through the aperture from the pond you see green earth below and open sky above - the aperture
genuinely appears to open somewhere else, which is the whole portal trick, bought by siting.

WHAT "RUIN" MEANS HERE - the void tower's lesson, verbatim: what makes voxels read as ARCHITECTURE
is regularity and openings, not damage. The masonry is regular coursework; the ruin is ONE broken
arc on the upper-north shoulder, with the crown keystone surviving ("the keystone held"), and the
fallen piece lying as ONE coherent chunk half-buried in the moss below the gap. No scatter.

THE PALETTE IS FOREIGN ON PURPOSE. Blackstone is the vanilla ruined-portal family, it reads 40+ RGB
off the moss and 25 darker than the island's own deepslate dressing, and every block of it is cheap
tier here (polished/cracked/chiseled/gilded) while obsidian, crying obsidian and gold - the obvious
portal blocks - are all expensive. The one cold light in a lowland of 122 warm lanterns: amethyst
clusters (cheap, light 5) on the inner reveal and a few soul lanterns in the rubble. Colour
temperature is what separates the gate from the scene.

BURIAL IS FREE. Cells are emitted only where the world holds air or a plant the player clears
first (the courthall rule: never cover what is already standing), so the bottom arc terminates
against the terrain and the moss laps it - zero overlap and zero dig by construction, and the
uphill side buries deeper than the downhill side, which is what a thing that has stood a long
time looks like.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

RUINRING = {
    "under": None,             # capture/composite the ground is read from - required
    "at": None,                # [x, z] of the ring's centre column - required
    "outer_d": 25,             # outer diameter. 25 reads as a circle; below ~15 it is an octagon
    "thickness": 3.0,          # radial. 3 survives the break stubs without reading flimsy
    "depth": 3,                # along the aperture axis (X). 2 vanishes edge-on; 3 casts a reveal
    "sink": 1,                 # courses below the LOWEST ground on the ring line - the burial
    # the missing arc, in degrees from the crown, positive toward north (-Z). 20..58 keeps the
    # crown keystone and puts the gap upper-left from the pond view, balancing the bat rock
    # hanging upper-right. Ends are stepped, not sheared - a coherent fracture.
    "break_arc": [20.0, 58.0],
    "seed": 0,

    "field": "polished_blackstone_bricks",
    "cracked": "cracked_polished_blackstone_bricks",
    "rough": "blackstone",
    "gilded": "gilded_blackstone",
    "chiseled": "chiseled_polished_blackstone",
    "slab": "polished_blackstone_brick_slab",
    "stair": "polished_blackstone_brick_stairs",
    "gild_rate": 0.04,         # the vanilla ruined-portal gold fleck, without gold blocks
    "keystones": True,         # chiseled crown (proud by one cell) and springers at 3 and 9

    "clusters": 5,             # amethyst on the lower inner reveal - crystallised portal energy
    "soul_lanterns": 3,
    "lichen": 5,               # glow lichen on the shaded inner reveal
    "fallen": True,
    "threshold": True,         # slab pavement through the aperture; a stair where it climbs
}

# What the design may build THROUGH: air, and the plants the player clears wholesale first
# (finish.context_clear must name the same set). Water, ice, lanterns and lichen are absent on
# purpose - they are protected, and a cell holding one simply stays the world's.
_PASSABLE = {"air", "cave_air", "void_air", "vine", "short_grass", "tall_grass", "fern",
             "large_fern", "moss_carpet", "azalea", "flowering_azalea", "poppy", "dandelion"}


def _free(ctx: Ctx, x: int, y: int, z: int) -> bool:
    return ctx.name_at(x, y, z) in _PASSABLE


def _surface(ctx: Ctx, x: int, z: int, y_top: int = 58, y_bot: int = 24):
    """Topmost REAL footing at a column, and its name. Plants and vines are not footing - the
    rimstair's stringers once stopped on a vine hanging in open air because `name_at` answers
    by name and 'not air' looked like rock."""
    for y in range(y_top, y_bot - 1, -1):
        n = ctx.name_at(x, y, z)
        if n not in _PASSABLE:
            return y, n
    return None, None


def _weathered(p, h) -> str:
    """Per-CELL material hash. Hashed on the course, every block in a course comes out identical
    and the wall is horizontal stripes - the deck soffit shipped that once."""
    if h < float(p["gild_rate"]):
        return p["gilded"]
    if h < 0.16:
        return p["cracked"]
    if h < 0.30:
        return p["rough"]
    return p["field"]


def _ring_cells(p, R_out: float, R_in: float):
    """(dz, dy, theta) for every cell of the annulus, break applied with stepped ends.

    theta is degrees from the crown, positive toward -Z (north). The break removes the full
    band; within a few degrees of each edge only the OUTER course survives, so the fracture
    steps down instead of shearing flat."""
    a0, a1 = (float(v) for v in p["break_arc"])
    cells = []
    rng = int(R_out) + 1
    for dz in range(-rng, rng + 1):
        for dy in range(-rng, rng + 1):
            d = math.hypot(dz, dy)
            if not (R_in < d <= R_out):
                continue
            th = math.degrees(math.atan2(-dz, dy))     # crown 0, north positive, south negative
            if a0 <= th <= a1:
                continue                               # the missing arc
            if a0 - 7.0 <= th < a0 or a1 < th <= a1 + 7.0:
                if d <= R_out - 1.4:                   # stepped stub: outer course only
                    continue
            cells.append((dz, dy, th))
    return cells


def _emit_ring(w: World, ctx: Ctx, p, cx, cz, cy, R_out, R_in, seed) -> int:
    """The annulus, weathered per cell, keystones chiseled. Placed only through _free cells."""
    depth = int(p["depth"])
    x0 = cx - depth // 2
    placed = 0
    for dz, dy, th in _ring_cells(p, R_out, R_in):
        y, z = cy + dy, cz + dz
        d = math.hypot(dz, dy)
        keystone = bool(p["keystones"]) and d > R_out - 1.6 and \
            (abs(th) <= 5.0 or abs(abs(th) - 90.0) <= 4.0)
        for i in range(depth):
            x = x0 + i
            if not _free(ctx, x, y, z):
                continue                               # terminate against terrain: the burial
            mat = p["chiseled"] if keystone else _weathered(p, hash01(x, y, z, seed))
            w.put(x, y, z, mat)
            placed += 1
    if p["keystones"]:                                 # the crown keystone stands proud one cell
        for dz in (-1, 0, 1):
            y = cy + int(round(math.sqrt(max(0.0, R_out * R_out - dz * dz)))) + 1
            for i in range(depth):
                if _free(ctx, x0 + i, y, cz + dz):
                    w.put(x0 + i, y, cz + dz, p["chiseled"])
    return placed


def _emit_fallen(w: World, ctx: Ctx, p, cx, cz, seed):
    """The broken arc, down in the moss below the gap: ONE half-buried chunk, curved like the
    piece it was, two courses at the middle tapering to one at the ends."""
    a0, a1 = (float(v) for v in p["break_arc"])
    mid = math.radians((a0 + a1) / 2.0)
    R = float(p["outer_d"]) / 2.0
    fz = cz - int(round(R * math.sin(mid)))            # under the gap it fell from
    fx = cx - 4                                        # and a little west, off the ring plane
    cols = {}                                          # (x, z) -> (its own ground, its top)
    for t in range(8):
        z = fz - 3 + t
        xw = fx + int(round(1.6 * math.sin(t / 7.0 * math.pi)))  # the chunk keeps its curve
        courses = 2 if 2 <= t <= 5 else 1
        for dx in (0, 1):                              # the ring's depth, lying on its side
            g, _ = _surface(ctx, xw + dx, z)
            if g is not None:
                cols[(xw + dx, z)] = (g, g + courses)
    cells = []
    for (x, z), (g, top) in cols.items():
        # a RIGID fallen arc bridges a dip rather than conforming to it: each column rises to
        # meet the tallest of its face-neighbours, or the chunk shears into fragments wherever
        # the ground steps under it. Seated per REAL column - the two x-columns of the chunk
        # stand on different ground, and a shared height sheared exactly there once.
        reach = max([top] + [t2 for (nx, nz), (_, t2) in cols.items()
                             if abs(nx - x) + abs(nz - z) == 1])
        for y in range(g + 1, reach + 1):
            if _free(ctx, x, y, z):
                w.put(x, y, z, _weathered(p, hash01(x, y, z, seed + 7)))
                cells.append((x, y, z))
    return cells


def _emit_threshold(w: World, ctx: Ctx, p, cx, cz) -> int:
    """Slab pavement through the aperture, 3 wide, following the ground. Where the walk climbs
    exactly one course the riser is a stair FACING THE ASCENT - a flight that ascends toward D
    has every tread facing=D, half=bottom (test_stairhead). A taller step stays a step: this is
    a moss slope, not a staircase."""
    heights = {}
    for x in range(cx - 5, cx + 6):
        for z in (cz - 1, cz, cz + 1):
            g, name = _surface(ctx, x, z)
            if g is not None and name not in ("water", "ice"):
                heights[(x, z)] = g
    placed = 0
    for (x, z), g in heights.items():
        if not _free(ctx, x, g + 1, z) or w.has(x, g + 1, z):
            continue                                   # a lantern or the ring itself is here
        east = heights.get((x + 1, z))
        if east is not None and east == g + 1 and x < cx + 5:
            w.put(x, g + 1, z, p["stair"], facing="east", half="bottom")
        else:
            w.put(x, g + 1, z, p["slab"], type="bottom")
        placed += 1
    return placed


def _emit_accents(w: World, ctx: Ctx, p, cx, cz, cy, R_in, fallen_cells, seed) -> dict:
    """Amethyst on the lower inner reveal, soul lanterns on the rubble, lichen in the shade.
    Everything clinging is anchored to a cell this design actually put down - the mane that came
    off as seven floating fragments is why."""
    depth = int(p["depth"])
    x0 = cx - depth // 2
    feats = {"clusters": 0, "lanterns": 0, "lichen": 0}

    for i in range(28):                                # amethyst: lower inner reveal
        if feats["clusters"] >= int(p["clusters"]):
            break
        th = math.radians(118.0 + (i * 29) % 120) * (1 if i % 2 else -1)
        dz, dy = -math.sin(th) * (R_in + 0.6), math.cos(th) * (R_in + 0.6)
        sz, sy = cz + int(round(dz)), cy + int(round(dy))
        if abs(dy) >= abs(dz):                         # step radially INWARD off the ring cell
            step, facing = ((0, -1), "down") if dy > 0 else ((0, 1), "up")
        else:
            step, facing = ((1, 0), "south") if dz < 0 else ((-1, 0), "north")
        az, ay = sz + step[0], sy + step[1]
        x = x0 + (i % depth)
        if w.has(x, sy, sz) and not w.has(x, ay, az) and _free(ctx, x, ay, az):
            w.put(x, ay, az, "amethyst_cluster", facing=facing)
            feats["clusters"] += 1

    # soul lanterns: STANDING (hanging=false is a decision and is recorded), and only ever on a
    # cell THIS design placed - stood on bare terrain the standalone audit reads them as floating,
    # because the terrain is not in the canvas
    spots = [(x, y + 1, z) for x, y, z in
             sorted(fallen_cells, key=lambda c: (-c[1], c[0], c[2]))[:9:3]]
    for x, y, z in spots:
        if feats["lanterns"] >= int(p["soul_lanterns"]):
            break
        if not w.has(x, y, z) and _free(ctx, x, y, z) and w.has(x, y - 1, z):
            w.put(x, y, z, "soul_lantern", hanging="false")
            feats["lanterns"] += 1

    for i in range(24):                                # lichen: the face flag points at support
        if feats["lichen"] >= int(p["lichen"]):
            break
        th = math.radians(155.0 + i * 31.0)
        dz, dy = -math.sin(th) * (R_in + 0.6), math.cos(th) * (R_in + 0.6)
        sz, sy = cz + int(round(dz)), cy + int(round(dy))
        x = x0 + (i % depth)
        ly = sy - 1 if dy > 0 else sy + 1
        face = "up" if dy > 0 else "down"              # up=true clings to the block above
        if w.has(x, sy, sz) and not w.has(x, ly, sz) and _free(ctx, x, ly, sz):
            w.put(x, ly, sz, "glow_lichen", **{face: "true"})
            feats["lichen"] += 1
    return feats


def build_ruinring(cfg: dict, donors=None) -> Canvas:
    p = {**RUINRING, **cfg}
    if not p.get("under") or not p.get("at"):
        raise ValueError("ruinring needs params.under and params.at [x, z]")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    cx, cz = (int(v) for v in p["at"])                 # INTEGER centres - round() is banker's
    D = int(p["outer_d"])
    R_out = D / 2.0 - 0.01
    R_in = R_out - float(p["thickness"])

    grounds = []                                       # seat on the ground the ring line crosses
    for dz in range(-(D // 2), D // 2 + 1):
        g, _ = _surface(ctx, cx, cz + dz)
        if g is not None:
            grounds.append(g)
    if not grounds:
        raise ValueError("ruinring: no ground under the ring line - wrong site or wrong capture")
    y_bot = min(grounds) - int(p["sink"])
    cy = y_bot + D // 2

    w = World()
    ring_n = _emit_ring(w, ctx, p, cx, cz, cy, R_out, R_in, seed)
    fallen = _emit_fallen(w, ctx, p, cx, cz, seed) if p["fallen"] else []
    thresh_n = _emit_threshold(w, ctx, p, cx, cz) if p["threshold"] else 0
    feats = _emit_accents(w, ctx, p, cx, cz, cy, R_in, fallen, seed)

    return w.canvas({"kind": "ruinring", "profile_view": "face", "facing": [1, 0],
                     "centre": [cx, cy, cz], "aperture_d": int(R_in * 2),
                     "features_built": {"ring": ring_n, "fallen": len(fallen),
                                        "threshold": thresh_n, **feats}})
