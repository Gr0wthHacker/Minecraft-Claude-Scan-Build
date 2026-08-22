"""The ruins quarter: a decaying blackstone way from the pond to the void overlook.

The ring made the SE corner the ruins quarter; this is the rest of the complex, all one hand
with it - the same blackstone family, the same cold light, the same rule that ruin is REGULAR
COURSEWORK WITH OPENINGS, never scatter. Every site below is measured off the 19:28 capture.

THE WAY. Ruined pavement from the pond's south-east bank, THROUGH the ring, up the crest to a
broken overlook on the rim - the walk the whole quarter exists for. It crosses UNDER the
sprinting capybara: measured, the animal's only low cells are its two diagonal leg pairs
(z30014-18 and z30022-26), and the corridor between them at z30019-21 is clear below Y47 the
whole way across. The pavement DECAYS with distance from the ring: whole near the gate, gapped
and moss-bitten at its ends - the ruin fades into the scene instead of stopping at a line.

THE FRAGMENTS, each a part of a building rather than a building:
- a GATEHOUSE at the pond end - two piers and half a lintel, the door still standing when the
  wall is long gone. Framed from the west bank, the ring sits inside its opening.
- a COLONNADE flanking the way behind the ring - four piers at four heights, the processional
  approach to the overlook.
- the OVERLOOK itself: a paved half-circle at the rim's true edge (ground ends at X-24151,
  measured), broken parapet, two soul lanterns - the balcony over the void that the walk
  through the gate promises.
- a BRIDGE STUB off the south bank: three rows of deck, the last two over open water, ending
  broken. A bridge to nowhere is the most legible ruin there is.
- an APSE fragment in the NORTH skylight (blob 1, 105 columns of real sky at -24185,29972):
  a half-ring of wall, tallest at its back, collapsing to nothing at both ends, one amethyst
  bloom inside. The second beam of daylight gets its own ruin, so the two light shafts answer
  each other across the scene.

Everything is air-only (the courthall rule), defer_to hands shared cells to the designs that
own them, and every clinging thing is anchored to a cell this design placed.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _PASSABLE, _free, _surface, _weathered

RUINWAY = {
    "under": None,
    "path": [],                # world [x, z] polyline, pond end first
    "width": 2,
    "decay_from": None,        # [x, z] the pavement is whole here and decays away from it
    "gap_base": 0.07,
    "gap_per_block": 0.008,    # decay rate with distance from decay_from
    "seed": 0,

    "gatehouse": None,         # {"at": [x, z]} - piers flank the path, lintel half-fallen
    "colonnade": [],           # [{"at": [x, z], "h": n}, ...] free-standing piers
    "overlook": None,          # {"at": [x, z], "r": 3} at the measured rim edge
    "bridge": None,            # {"from": [x, z], "dir": [dx, dz], "len": 5, "width": 3}
    "quay": None,              # {"from": [x, z], "to": [x, z]} dressed lip on the bank edge
    "apse": None,              # {"at": [x, z], "r": 4, "h": 5, "open_deg": 200}
    "lanterns": [],            # [x, z] wall-post + soul lantern, skipped where occupied

    "field": "polished_blackstone_bricks",
    "cracked": "cracked_polished_blackstone_bricks",
    "rough": "blackstone",
    "gilded": "gilded_blackstone",
    "chiseled": "chiseled_polished_blackstone",
    "slab": "polished_blackstone_brick_slab",
    "stair": "polished_blackstone_brick_stairs",
    "wall": "polished_blackstone_brick_wall",
    "gild_rate": 0.03,
}


def _facing_of(dx: float, dz: float) -> str:
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def _emit_path(w: World, ctx: Ctx, p, seed) -> dict:
    """Ruined pavement following the ground. A riser of exactly one course is a stair FACING
    THE ASCENT (test_stairhead); anything taller stays a step in the moss. Gaps are hashed per
    cell and grow with distance from `decay_from` - and a stair is never gapped, because a
    missing tread breaks the walk where a missing flag is just moss showing through."""
    pts = [(float(x), float(z)) for x, z in p["path"]]
    dfx, dfz = (float(v) for v in (p["decay_from"] or p["path"][0]))
    lanes = {}                                         # (x, z) -> walk order index
    order = 0
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, bz - az)
        n = max(1, int(seg * 2))
        px, pz = -(bz - az) / seg, (bx - ax) / seg
        for i in range(n + 1):
            t = i / n
            cx, cz = ax + (bx - ax) * t, az + (bz - az) * t
            for u in (-0.5, 0.5):
                key = (int(round(cx + px * u)), int(round(cz + pz * u)))
                if key not in lanes:
                    lanes[key] = order
                    order += 1
        # remember the segment direction for stair facing at these columns
    stats = {"slabs": 0, "stairs": 0, "gaps": 0}
    cols = sorted(lanes, key=lambda k: lanes[k])
    heights = {}
    for x, z in cols:
        g, name = _surface(ctx, x, z)
        if g is not None and name not in ("water", "ice"):
            heights[(x, z)] = g
    for j, (x, z) in enumerate(cols):
        if (x, z) not in heights:
            continue
        g = heights[(x, z)]
        if not _free(ctx, x, g + 1, z) or w.has(x, g + 1, z):
            continue
        # the next path column along the walk, for the riser test
        nxt = next(((x2, z2) for (x2, z2) in cols[j + 1:j + 4] if (x2, z2) in heights
                    and abs(x2 - x) + abs(z2 - z) == 1), None)
        rise = nxt and heights[nxt] == g + 1
        dist = math.hypot(x - dfx, z - dfz)
        gap = hash01(x, 7, z, seed) < min(0.30, float(p["gap_base"]) + float(p["gap_per_block"]) * dist)
        if rise:
            w.put(x, g + 1, z, p["stair"], facing=_facing_of(nxt[0] - x, nxt[1] - z), half="bottom")
            stats["stairs"] += 1
        elif gap:
            stats["gaps"] += 1
        else:
            w.put(x, g + 1, z, p["slab"], type="bottom")
            stats["slabs"] += 1
    return stats


def _emit_pier(w: World, ctx: Ctx, p, x, z, h, seed, cap=True) -> int:
    g, name = _surface(ctx, x, z)
    if g is None or name in ("water", "ice"):
        return 0
    placed = 0
    for k in range(h):
        y = g + 1 + k
        if not _free(ctx, x, y, z) or w.has(x, y, z):
            break
        top = cap and k == h - 1 and h >= 4
        w.put(x, y, z, p["chiseled"] if top else _weathered(p, hash01(x, y, z, seed)))
        placed += 1
    return placed


def _emit_gatehouse(w: World, ctx: Ctx, p, seed) -> int:
    """A COMPLETE doorframe standing alone in the moss - and the ruin is everything around it.

    The first version broke the lintel and kept it small, and the visual audit read it as a
    dark blob beside the path: five-tall piers are furniture next to ten-tall trees, and a
    broken doorway is damage, not architecture. The void tower's rule, applied properly: the
    ORDER survives whole - two 2x2 piers, chiseled imposts, a full lintel - and the decay is
    carried by the wall stubs trailing off both sides, broken to nothing."""
    gx, gz = (int(v) for v in p["gatehouse"]["at"])
    g, _ = _surface(ctx, gx, gz)
    if g is None:
        return 0
    n = 0
    H = 7                                              # to the impost; the lintel rides at +8
    for zz in (gz - 3, gz + 2):                        # the piers, 2x2 and full height
        for dx in (0, 1):
            for dz in (0, 1):
                x, z = gx + dx, zz + dz
                g2, name2 = _surface(ctx, x, z)
                if g2 is None or name2 in ("water", "ice"):
                    continue
                for k in range(H):
                    y = g2 + 1 + k
                    if not _free(ctx, x, y, z) or w.has(x, y, z):
                        break
                    impost = k == H - 1
                    w.put(x, y, z, p["chiseled"] if impost else _weathered(p, hash01(x, y, z, seed)))
                    n += 1
    lin_y = g + 1 + H
    for z in range(gz - 3, gz + 4):                    # the lintel, COMPLETE, pier to pier
        for dx in (0, 1):
            x = gx + dx
            if _free(ctx, x, lin_y, z) and not w.has(x, lin_y, z):
                w.put(x, lin_y, z, p["chiseled"])
                n += 1
    for zz, step in ((gz - 4, -1), (gz + 4, 1)):       # the broken wall, falling to nothing
        h_wall = 3
        z = zz
        while h_wall > 0:
            g2, name2 = _surface(ctx, gx, z)
            if g2 is None or name2 in ("water", "ice"):
                break
            for k in range(h_wall):
                y = g2 + 1 + k
                if _free(ctx, gx, y, z) and not w.has(gx, y, z):
                    w.put(gx, y, z, _weathered(p, hash01(gx, y, z, seed)))
                    n += 1
            z += step
            h_wall -= 1
    for dx, dz in ((2, 1), (3, 0), (2, -2)):           # fallen blocks off the collapsed wall
        x, z = gx + dx, gz + dz
        g2, name2 = _surface(ctx, x, z)
        if g2 is not None and name2 not in ("water", "ice") and _free(ctx, x, g2 + 1, z) and not w.has(x, g2 + 1, z):
            w.put(x, g2 + 1, z, _weathered(p, hash01(x, 3, z, seed)))
            n += 1
    return n


def _emit_overlook(w: World, ctx: Ctx, p, seed) -> int:
    """A paved half-circle at the rim's true edge with a broken parapet on the void side.
    Parapet cells exist only over real ground - the rim is ragged, and a wall over air is the
    floating-tread failure all over again."""
    ox, oz = (int(v) for v in p["overlook"]["at"])
    r = float(p["overlook"].get("r", 3))
    n = 0
    for dx in range(-int(r) - 1, int(r) + 2):
        for dz in range(-int(r) - 1, int(r) + 2):
            d = math.hypot(dx, dz)
            if d > r + 0.4:
                continue
            x, z = ox + dx, oz + dz
            g, name = _surface(ctx, x, z)
            if g is None or name in ("water", "ice"):
                continue
            if d <= r - 0.8:                           # the paving
                if _free(ctx, x, g + 1, z) and not w.has(x, g + 1, z):
                    if hash01(x, 9, z, seed) > 0.18:
                        w.put(x, g + 1, z, p["slab"], type="bottom")
                        n += 1
            elif dx >= 0:                              # the parapet, void side only
                if hash01(x, 11, z, seed) < 0.30:
                    continue                           # the break
                if _free(ctx, x, g + 1, z) and not w.has(x, g + 1, z):
                    w.put(x, g + 1, z, p["wall"])
                    n += 1
                    if abs(dz) >= int(r) - 1 and _free(ctx, x, g + 2, z):
                        w.put(x, g + 2, z, "soul_lantern", hanging="false")
                        n += 1
    return n


def _emit_bridge(w: World, ctx: Ctx, p, seed) -> int:
    """A level deck off the bank, the last rows over open water, the end broken. The deck is
    CONSTANT height - a bridge does not conform to the ground, that is the whole reason to
    build one - and nothing below it is touched: the water rows are cantilever."""
    b = p["bridge"]
    bx, bz = (int(v) for v in b["from"])
    dx, dz = (int(v) for v in b["dir"])
    width = int(b.get("width", 3))
    length = int(b.get("len", 5))
    g0, _ = _surface(ctx, bx, bz)
    if g0 is None:
        return 0
    deck = g0 + 1
    px, pz = -dz, dx
    n = 0
    for i in range(length):
        for u in range(-(width // 2), width // 2 + 1):
            x = bx + dx * i + px * u
            z = bz + dz * i + pz * u
            if i == length - 1 and hash01(x, 13, z, seed) < 0.6:
                continue                               # the broken end, staggered
            if _free(ctx, x, deck, z) and not w.has(x, deck, z):
                w.put(x, deck, z, p["slab"], type="bottom")
                n += 1
        if i == 0:                                     # rail stubs at the bank end only
            for u in (-(width // 2), width // 2):
                x, z = bx + px * u, bz + pz * u
                if _free(ctx, x, deck + 1, z) and w.has(x, deck, z):
                    w.put(x, deck + 1, z, p["wall"])
                    n += 1
    return n


def _emit_quay(w: World, ctx: Ctx, p, seed) -> dict:
    """The harbor the pond always was: a dressed lip along the REAL bank edge (every dry
    column touching water, found at build time - the bank is the water's own line, never a
    hand-drawn box), mooring posts, and landing steps whose flight ascends LANDWARD, because
    you climb them out of a boat. Nothing enters the water; the lip rides one course above."""
    q = p["quay"]
    fx, fz = (int(v) for v in q["from"])
    tx, tz = (int(v) for v in q["to"])
    x0, x1 = min(fx, tx) - 1, max(fx, tx) + 1
    z0, z1 = min(fz, tz) - 1, max(fz, tz) + 1
    feats = {"lip": 0, "posts": 0, "steps": 0}
    lip_cells = []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            g, name = _surface(ctx, x, z)
            if g is None or name in ("water", "ice"):
                continue
            wdir = None
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                _g2, n2 = _surface(ctx, x + dx, z + dz)
                if n2 in ("water", "ice"):
                    wdir = (dx, dz)
                    break
            if wdir is None:
                continue
            if _free(ctx, x, g + 1, z) and not w.has(x, g + 1, z):
                dressed = hash01(x, 51, z, seed) < 0.55
                w.put(x, g + 1, z, p["chiseled"] if dressed else _weathered(p, hash01(x, g, z, seed)))
                feats["lip"] += 1
                lip_cells.append((x, g + 1, z, wdir))
    lip_cells.sort(key=lambda c: (c[0], c[2]))
    mid = len(lip_cells) // 2
    for i, (x, y, z, wdir) in enumerate(lip_cells):
        if i in (mid - 1, mid):                        # the landing: steps up out of the water
            away = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}[wdir]
            w.put(x, y, z, p["stair"], facing=away, half="bottom")
            feats["steps"] += 1
        elif i % 5 == 2:                               # mooring posts on the lip
            if _free(ctx, x, y + 1, z) and not w.has(x, y + 1, z):
                w.put(x, y + 1, z, "polished_blackstone_brick_wall")
                top = "soul_lantern" if feats["posts"] == 1 else None
                if top and _free(ctx, x, y + 2, z):
                    w.put(x, y + 2, z, top, hanging="false")
                elif _free(ctx, x, y + 2, z):
                    w.put(x, y + 2, z, p["slab"], type="bottom")
                feats["posts"] += 1
    return feats


def _emit_apse(w: World, ctx: Ctx, p, seed) -> int:
    """A half-ring of wall in the north skylight: tallest at its back, collapsing to nothing
    at both ends, open toward the scene. One amethyst bloom inside - the same cold spark as
    the ring, so the two skylights read as one story."""
    a = p["apse"]
    ax, az = (int(v) for v in a["at"])
    r = float(a.get("r", 4))
    hmax = int(a.get("h", 5))
    open_deg = float(a.get("open_deg", 200))           # the western opening, degrees of arc
    n = 0
    back = []
    half = (360 - open_deg) / 2
    for dx in range(-int(r) - 2, int(r) + 3):
        for dz in range(-int(r) - 2, int(r) + 3):
            d = math.hypot(dx, dz)
            ang = math.degrees(math.atan2(dz, dx))     # 0 = east = the apse's back
            rib = abs(abs(ang) - 40) < 8 or abs(ang) < 8
            in_wall = r - 0.5 <= d <= r + 0.5
            in_plinth = r + 0.5 < d <= r + 1.4
            in_rib = rib and r + 0.5 < d <= r + 1.5
            if not (in_wall or in_plinth or in_rib):
                continue
            if abs(ang) > half:
                continue                               # the opening faces west, at the scene
            x, z = ax + dx, az + dz
            g, name = _surface(ctx, x, z)
            if g is None or name in ("water", "ice"):
                continue
            f = 1.0 - abs(ang) / half
            # the audit's scale rule: on this moss, under these trees, architecture below ~6
            # dissolves into ground noise. Full height at the back, TWO courses even at the
            # broken ends, and buttress ribs give the elevation a rhythm - regularity, again.
            if in_wall:
                # FULL height across the whole back third, then decay: a linear peak put the
                # crest on a single column and the audit read a stick, not a wall
                h = hmax if f > 0.60 else max(2, int(round(hmax * (0.30 + 1.15 * f))))
            elif in_rib:
                h = max(2, int(round(hmax * (0.25 + 0.60 * f))))
            else:
                h = 1                                  # the plinth course, stepped out
            for k in range(h):
                y = g + 1 + k
                if not _free(ctx, x, y, z) or w.has(x, y, z):
                    break
                band = in_wall and k == 3 and h >= 5
                w.put(x, y, z, p["chiseled"] if band else _weathered(p, hash01(x, y, z, seed)))
                n += 1
                if in_wall and k == 1 and abs(ang) < 35:
                    back.append((x, y, z))
    # the bloom goes in AFTER the wall stands: picked inside the loop, its cell kept being
    # claimed by a later wall course and the apse shipped bloomless
    for x, y, z in back:
        if _free(ctx, x - 1, y, z) and not w.has(x - 1, y, z):
            w.put(x - 1, y, z, "amethyst_cluster", facing="west")
            n += 1
            break
    for dx, dz in ((-1, 2), (0, 3), (-2, -2)):         # rubble where the ends collapsed
        x, z = ax + dx, az + dz
        g, name = _surface(ctx, x, z)
        if g is not None and name not in ("water", "ice") and _free(ctx, x, g + 1, z) and not w.has(x, g + 1, z):
            w.put(x, g + 1, z, _weathered(p, hash01(x, 5, z, seed)))
            n += 1
    return n


def build_ruinway(cfg: dict, donors=None) -> Canvas:
    p = {**RUINWAY, **cfg}
    if not p.get("under") or not p.get("path"):
        raise ValueError("ruinway needs params.under and params.path")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    w = World()
    feats = {}
    feats.update(_emit_path(w, ctx, p, seed))
    if p.get("gatehouse"):
        feats["gatehouse"] = _emit_gatehouse(w, ctx, p, seed)
    piers = 0
    for c in p.get("colonnade", []):
        piers += _emit_pier(w, ctx, p, int(c["at"][0]), int(c["at"][1]), int(c["h"]), seed)
    feats["colonnade"] = piers
    if p.get("overlook"):
        feats["overlook"] = _emit_overlook(w, ctx, p, seed)
    if p.get("bridge"):
        feats["bridge"] = _emit_bridge(w, ctx, p, seed)
    if p.get("quay"):
        feats.update(_emit_quay(w, ctx, p, seed))
    if p.get("apse"):
        feats["apse"] = _emit_apse(w, ctx, p, seed)
    posts = 0
    for x, z in p.get("lanterns", []):
        g, name = _surface(ctx, int(x), int(z))
        if g is None or name in ("water", "ice"):
            continue
        if _free(ctx, x, g + 1, z) and _free(ctx, x, g + 2, z) and not w.has(x, g + 1, z):
            w.put(x, g + 1, z, p["wall"])
            w.put(x, g + 2, z, "soul_lantern", hanging="false")
            posts += 1
    feats["lantern_posts"] = posts
    return w.canvas({"kind": "ruinway", "profile_view": "top", "facing": [1, 0],
                     "features_built": feats})
