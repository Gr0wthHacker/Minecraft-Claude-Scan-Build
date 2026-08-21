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
    """Two 2x2 piers astride the way and HALF a lintel - the north half holds, the south fell,
    and the fallen half lies in the moss below. A doorway standing alone is the part of a
    building that says building loudest."""
    gx, gz = (int(v) for v in p["gatehouse"]["at"])
    n = 0
    tops = []
    for sz, zz in (("N", gz - 3), ("S", gz + 2)):
        for dx in (0, 1):
            for dz in (0, 1):
                placed = _emit_pier(w, ctx, p, gx + dx, zz + dz, 5, seed, cap=False)
                n += placed
                tops.append((gx + dx, zz + dz, placed))
    g, _ = _surface(ctx, gx, gz)
    if g is None:
        return n
    lin_y = g + 6
    for dz in range(-1, 2):                            # the surviving NORTH half of the lintel
        for dx in (0, 1):
            x, z = gx + dx, gz - 1 + dz
            if dz > 0:
                continue                               # the south half is the one that fell
            if _free(ctx, x, lin_y, z) and (w.has(x, lin_y - 1, z) or dz > -1):
                w.put(x, lin_y, z, p["chiseled"] if dz == -1 else _weathered(p, hash01(x, lin_y, z, seed)))
                n += 1
    for i, (dx, dz) in enumerate(((0, 1), (1, 1), (1, 2))):   # the fallen half, half-buried
        x, z = gx + dx, gz + dz
        g2, name2 = _surface(ctx, x, z)
        if g2 is not None and name2 not in ("water", "ice") and _free(ctx, x, g2 + 1, z) and not w.has(x, g2 + 1, z):
            w.put(x, g2 + 1, z, p["chiseled"] if i == 0 else _weathered(p, hash01(x, 3, z, seed)))
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
    for dx in range(-int(r) - 1, int(r) + 2):
        for dz in range(-int(r) - 1, int(r) + 2):
            d = math.hypot(dx, dz)
            if not (r - 0.5 <= d <= r + 0.5):
                continue
            ang = math.degrees(math.atan2(dz, dx))     # 0 = east = the apse's back
            if abs(ang) > (360 - open_deg) / 2:
                continue                               # the opening faces west, at the scene
            x, z = ax + dx, az + dz
            g, name = _surface(ctx, x, z)
            if g is None or name in ("water", "ice"):
                continue
            f = 1.0 - abs(ang) / ((360 - open_deg) / 2)
            h = max(1, int(round(hmax * (0.35 + 0.65 * f))))
            for k in range(h):
                y = g + 1 + k
                if not _free(ctx, x, y, z) or w.has(x, y, z):
                    break
                band = k == 2 and h >= 4
                w.put(x, y, z, p["chiseled"] if band else _weathered(p, hash01(x, y, z, seed)))
                n += 1
                if k == 1 and abs(ang) < 35:
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
