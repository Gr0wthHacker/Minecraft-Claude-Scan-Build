"""A broken walkway between two floating pieces - the castle bridge.

Jack: "should we connect the small islands in any way, e.g. broken cute walk ways from the
center taproot island to the castle." Measured, the bat tower's parapet and the island's SE rim
sit at the SAME height - Y151 both sides, 21 blocks apart - which is what makes a broken bridge
believable: both ends are real architecture at matching height, and the tower's ruin already
implies it was once reached from the island.

THE GAP IS THE DESIGN. Two stubs reach toward each other and stop: the middle is missing. That
one absence does three jobs - it is the ruin, it is a jumpable gap for anyone walking the rim,
and it makes both halves printable, because each stub anchors to its own end and nothing needs
scaffolding. The rule that keeps a void-hanging thing legible (this file's whole family learned
it on the sanctum's breach): a real endpoint at real architecture, regular rhythm, matching
height. One bridge only - a second span starts turning the void into a rope-park.

Each stub is two courses - a structural bed of full blocks with slab pavement riding on it -
because a floating single-course line of slabs reads as a floating line of slabs, not as the
remains of a bridge. The torn ends stagger, and one block dangles a course BELOW each torn end,
the way a broken deck actually breaks. Rails and a lantern post stand at the anchored ends
only: the middle of a ruined span keeps nothing.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _weathered

RUINBRIDGE = {
    "under": None,             # the FULL capture - the ends live at Y151, far above island_lower
    "a": None,                 # [x, y, z] anchor on the island rim (deck rides at y+1)
    "b": None,                 # [x, y, z] anchor on the castle parapet
    "gap": 5,                  # the missing middle, in blocks along the line
    "width": 2,
    "seed": 0,

    "field": "polished_blackstone_bricks",
    "cracked": "cracked_polished_blackstone_bricks",
    "rough": "blackstone",
    "gilded": "gilded_blackstone",
    "chiseled": "chiseled_polished_blackstone",
    "slab": "polished_blackstone_brick_slab",
    "wall": "polished_blackstone_brick_wall",
    "gild_rate": 0.02,
}


def _airy(ctx: Ctx, x, y, z) -> bool:
    return ctx.name_at(int(x), int(y), int(z)) in ("air", "cave_air", "void_air", "vine")


def build_voidbridge(cfg: dict, donors=None) -> Canvas:
    p = {**RUINBRIDGE, **cfg}
    for k in ("under", "a", "b"):
        if not p.get(k):
            raise ValueError(f"voidbridge needs params.{k}")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    ax, ay, az = (int(v) for v in p["a"])
    bx, by, bz = (int(v) for v in p["b"])
    deck_y = max(ay, by) + 1                           # LEVEL - a bridge does not conform
    span = math.hypot(bx - ax, bz - az)
    gap = float(p["gap"])
    stub_t = (span - gap) / 2.0 / span                 # each stub covers this fraction of the line
    ux, uz = (bx - ax) / span, (bz - az) / span
    px, pz = -uz, ux
    w = World()
    feats = {"deck": 0, "bed": 0, "rails": 0, "dangles": 0}

    def put_bed(x, y, z, prev):
        """bed cell with the path from prev stitched one axis at a time - a diagonal step is a
        corner, not a face, and a corner over the void is a floating fragment (the ear-tip
        lesson, at Y151)."""
        cur = (int(round(x)), int(y), int(round(z)))
        if prev is not None and cur != prev:
            sx_, sy_, sz_ = prev
            while (sx_, sy_, sz_) != cur:
                if sx_ != cur[0]:
                    sx_ += 1 if cur[0] > sx_ else -1
                elif sz_ != cur[2]:
                    sz_ += 1 if cur[2] > sz_ else -1
                else:
                    sy_ += 1 if cur[1] > sy_ else -1
                if _airy(ctx, sx_, sy_, sz_) and not w.has(sx_, sy_, sz_):
                    w.put(sx_, sy_, sz_, _weathered(p, hash01(sx_, sy_, sz_, seed)))
                    feats["bed"] += 1
        elif _airy(ctx, *cur) and not w.has(*cur):
            w.put(*cur, _weathered(p, hash01(cur[0], cur[1], cur[2], seed)))
            feats["bed"] += 1
        return cur

    def lay(t0, t1):
        """one stub, walked from its anchored end toward the torn middle. Each lane's bed is a
        stitched run rooted at its own end; the pavement rides the bed; only the FINAL step
        staggers per lane, so the break is ragged but nothing is orphaned."""
        n_steps = max(2, int(span * abs(t1 - t0) * 2))
        last = {}
        for u in (-0.5, 0.5):
            prev = None
            for i in range(n_steps + 1):
                t = t0 + (t1 - t0) * i / n_steps
                x = int(round(ax + (bx - ax) * t + px * u))
                z = int(round(az + (bz - az) * t + pz * u))
                if i == n_steps and hash01(x, 3, z, seed) < 0.5:
                    break                              # this lane tears one step earlier
                prev = put_bed(x, deck_y - 1, z, prev)
                last[u] = prev
            if u in last:                              # one block dangling under the torn end,
                x, _y, z = last[u]                     # the way a broken deck actually breaks
                if _airy(ctx, x, deck_y - 2, z) and not w.has(x, deck_y - 2, z) \
                        and hash01(x, 9, z, seed) < 0.6:
                    w.put(x, deck_y - 2, z, p["rough"])
                    feats["dangles"] += 1

    lay(0.0, stub_t)
    lay(1.0, 1.0 - stub_t)
    for (x, y, z), (name, _pr) in list(w.cells.items()):
        if y == deck_y - 1 and _airy(ctx, x, deck_y, z) and not w.has(x, deck_y, z):
            if hash01(x, 7, z, seed) > 0.12:           # the pavement, moss-bitten
                w.put(x, deck_y, z, p["slab"], type="bottom")
                feats["deck"] += 1

    # springers at the ANCHORED ends - the middle of a ruined span keeps nothing, and a 2-wide
    # deck carries no rails (they would block the walk it exists for). The collar is what makes
    # the stub BUILDABLE: the line runs diagonally, so its first cell touches the anchor solid
    # only corner-to-corner, and a diagonal neighbour is not a face to place against - the
    # ear-tip lesson, at Y151 over the void.
    for (ex, ez, sign) in ((ax, az, 1), (bx, bz, -1)):
        for dx2, dz2 in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, z = ex + dx2, ez + dz2
            toward = (dx2 * ux + dz2 * uz) * sign
            if toward > 0.2 and _airy(ctx, x, deck_y - 1, z) and not w.has(x, deck_y - 1, z):
                w.put(x, deck_y - 1, z, p["chiseled"])
                feats["bed"] += 1
        for u in (-0.5, 0.5):
            x = int(round(ex + ux * sign * 1.0 + px * u))
            z = int(round(ez + uz * sign * 1.0 + pz * u))
            if w.has(x, deck_y - 1, z):
                w.put(x, deck_y - 1, z, p["chiseled"])
    # one cold light at the island end, ON THE RIM'S OWN SOLID beside the springer - a post on
    # the deck blocks the deck, and a post beside it needs real footing, not a lane that may
    # not exist at its rounded position
    for r in (1, 2, 3):
        if feats.get("lantern"):
            break
        for ddx in range(-r, r + 1):
            for ddz in range(-r, r + 1):
                if max(abs(ddx), abs(ddz)) != r:
                    continue
                lx, lz = ax + ddx, az + ddz
                if not _airy(ctx, lx, deck_y - 1, lz) and _airy(ctx, lx, deck_y, lz) \
                        and _airy(ctx, lx, deck_y + 1, lz) and not w.has(lx, deck_y, lz):
                    w.put(lx, deck_y, lz, p["wall"])
                    w.put(lx, deck_y + 1, lz, "soul_lantern", hanging="false")
                    feats["lantern"] = 1
                    break
            if feats.get("lantern"):
                break

    return w.canvas({"kind": "voidbridge", "profile_view": "face", "facing": [1, 0],
                     "deck_y": deck_y, "features_built": feats})
