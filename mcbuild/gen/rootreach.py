"""The Reaching Root - a feeder root off the shop islet's south rim, down to the lowland earth.

WHY IT EXISTS. Jack: the spiral staircase continues all the way down to the lowlands. The Root
Stair winds the taproot from the islet (Y152) up to the deck; below the islet is ~100 blocks of
measured open void, then the lowland floor at Y37-40 - and the stair's own idiom needs a core
to wind. The taproot's main mass ends in the islet's keel; this is the root that kept going:
a slim braid off the islet's SOUTH rim, reaching the underworld's ground and gripping it.

WHY THE SOUTH RIM AND NOT THE KEEL. The keel sits at (-24200, 30018), and a concentric helix
landing there wraps the watergate, the quay lip and the harbor light - the busiest ground in
the lowland, all measured. The south rim at (-24207/-24208, 30025) is solid shelf one course
thick, the axis under it clears the whole harbor ensemble (light at r8.6, watergate at r13+,
quay tip r11), and the landing arc falls on open moss south of the quay. The stair follows THIS
root, so the root's position is the stair's siting decision.

ANCHOR RULES, both paid for elsewhere: the top cells are placed directly under SOLID islet
cells (the bat's vines, the entrance chains - anything hanging finds a real ceiling first).
Strand courses are BRIDGED face-adjacent - a twist whose cells touch only diagonally is not
connected, which is how ear tips broke off once.

THE ROOT ENDS AT THE TRANSITION, NOT AT THE GROUND (Jack, 2026-08-22: the length has to
make sense - it can end earlier, at the transition point). The stair's stone darkens as it
descends - island stone brick, then deepslate, then the quarter's blackstone - and the root
is the ISLAND's reach: it thins through the deepslate band and is gone before the blackstone
begins. Below the tip the helix hangs alone, the underworld's own masonry rising to meet
the root - which is why the stair's min_radius is pinned to its running radius, so the
ribbon does not snap tighter the course after the profile ends.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _free

ROOTREACH = {
    "under": None,
    "at": None,                # [x, z] the root's axis (and the stair's centre)
    "grip": None,              # [x, z] solid shelf cell whose underside the root grips
    "y_top": 149,              # course of the topmost root cell, under the shelf
    "y_tip": 95,               # where the root gives out, mid-air, at the material seam
    "taper": 14,               # courses over which the braid thins to a single strand
    "strands": 3,
    "seed": 0,
    "wood": "oak_wood",
    "moss": "moss_block",
    "moss_rate": 0.08,
    "vines": 5,
}


def _put(w, ctx, x, y, z, name, **props):
    if _free(ctx, x, y, z) and not w.has(x, y, z):
        w.put(x, y, z, name, **props)
        return 1
    return 0


def _mat(p, x, y, z, seed):
    return p["moss"] if hash01(x, y, z, seed) < float(p["moss_rate"]) else p["wood"]


def build_rootreach(cfg: dict, donors=None) -> Canvas:
    p = {**ROOTREACH, **cfg}
    if not p.get("under") or not p.get("at") or not p.get("grip"):
        raise ValueError("rootreach needs params.under, params.at and params.grip")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    ax, az = (int(v) for v in p["at"])
    gx, gz = (int(v) for v in p["grip"])
    y_top = int(p["y_top"])
    yg = int(p["y_tip"])
    taper = int(p["taper"])

    w = World()
    feats = {"spine": 0, "strands": 0, "vines": 0}

    # ---- the spine: grip point at the top, easing onto the axis within eight courses ----
    bend = 8
    centres = {}
    for y in range(y_top, yg - 1, -1):
        t = min(1.0, (y_top - y) / float(bend))
        cx = gx + (ax - gx) * t
        cz = gz + (az - gz) * t
        centres[y] = (cx, cz)

    # ---- strands: a slim braid twisted about the spine, each course bridged to the last ----
    S = int(p["strands"])
    prev = {}
    for y in range(y_top, yg - 1, -1):
        cx, cz = centres[y]
        depth = y_top - y
        r = 1.25 if depth > 3 else max(0.4, depth * 0.35)   # converges into the grip at the top
        left = y - yg
        if left < taper:                                    # ...and thins out toward the tip
            r *= max(0.0, left / float(taper))
        for k in range(S):
            a = 2 * math.pi * k / S + depth * 0.13
            x = int(round(cx + r * math.cos(a)))
            z = int(round(cz + r * math.sin(a)))
            feats["strands"] += _put(w, ctx, x, y, z, _mat(p, x, y, z, seed))
            if k in prev:
                px, pz = prev[k]
                if (px, pz) != (x, z):
                    # the strand stepped sideways: WITHOUT a cell in the previous course's
                    # column the join is diagonal-only, and the first build came out as 26
                    # separate pieces. The bulge under each step is what a real root has.
                    feats["strands"] += _put(w, ctx, px, y, pz, _mat(p, px, y, pz, seed))
                    if abs(px - x) + abs(pz - z) > 1:
                        feats["strands"] += _put(w, ctx, x, y, pz,
                                                 _mat(p, x, y, pz, seed))
            prev[k] = (x, z)
        feats["spine"] += _put(w, ctx, int(round(cx)), y, int(round(cz)),
                               _mat(p, int(round(cx)), y, int(round(cz)), seed))

    # ---- a few vines off the braid, each hanging from a root cell above it ----
    hung = 0
    for (x, y, z) in sorted(w.cells):
        if hung >= int(p["vines"]):
            break
        if hash01(x, 71, z, seed) < 0.05 and not w.has(x, y - 1, z) and \
                _free(ctx, x, y - 1, z) and y - 1 > yg + 2:
            w.put(x, y - 1, z, "vine", up="true", north="false", south="false",
                  east="false", west="false")
            hung += 1
    feats["vines"] = hung

    return w.canvas({"kind": "rootreach", "profile_view": "side", "facing": [0, 1],
                     "y_ground": yg, "features_built": feats})
