"""The Hamlet - dwellings outside the gate, grown on the ground design's own lantern grid.

WHY HOUSES, AND WHY THERE. Jack's direction for the lowland (2026-08-22): architecture as the
figure, animals incorporated around it. The quarter had monuments - ring, sanctum, watergate,
colonnade - and no DWELLINGS, so it read as a processional way with nobody's town on it. The
pad search over the 15:01 scan found exactly one lit pad big enough once the capybara retired:
the skylight-south blob at X-24192..-24175 / Z30031..30042, 72 of 216 columns open to real sky,
immediately south-west of the ring.

THE LANTERN GRID IS THE STREET PLAN. The ground design places its lanterns on a 9-grid, and in
this pad the columns land at X{-24192,-24183,-24174} x Z{30033,30042}. The gaps between them
are 8 wide - a 7-wide house fits EXACTLY between two lantern columns, so the houses take the
gaps and the ground's own lights become the hamlet's street lamps standing at the corners.
Nothing here places a lantern and nothing may cover one: the grid columns are a FORBID set,
asserted at build time, not merely dodged (the sanctum's rule, made structural).

WHAT "RUIN" MEANS HERE - the quarter's rule, restated for dwellings: the ruin is the FABRIC,
never the doorway, and decay must differ per house or it reads as an algorithm. One house
stands WHOLE (roof, chimney, cold hearth - the once-lived-in proof, the way the sanctum's
facade is the once-impressive proof), one is ROOFLESS (walls up, gables torn, sky for a
ceiling), and one has FALLEN to its door frame - the gatehouse inverted: a complete doorway
standing alone, the house gone. Below ~6 courses architecture dissolves into this moss, so the
whole house carries the register and the fallen one is an accent beside it, its door frame
still full height.

The palette is the quarter's blackstone, mixed HUMBLER: more rough blackstone and cracked
brick, polished brick kept for quoins, jambs and roof - dwellings in the monuments' best stone
would read as more monuments. Same family, same hand, lower grade.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _free, _surface

HAMLET = {
    "under": None,
    # each house: at = [x, z] centre, w across X, l along Z (the ridge runs along Z),
    # door = which face the doorway is in, state = whole | roofless | fallen,
    # floor_y = the stylobate plane, PINNED once built (the ring's seat lesson)
    "houses": [],
    "lane": [],                # polyline [[x, z], ...] of ruined slab pavement
    "lantern_grid": [],        # [[x, z], ...] ground-design lantern columns - FORBIDDEN
    "seed": 0,

    "field": "blackstone",
    "cracked": "cracked_polished_blackstone_bricks",
    "polished": "polished_blackstone_bricks",
    "chiseled": "chiseled_polished_blackstone",
    "gilded": "gilded_blackstone",
    "slab": "polished_blackstone_brick_slab",
    "stair": "polished_blackstone_brick_stairs",
    "wall_h": 4,               # to the eaves; the gable rises w//2 above it
}


def _fabric(p, h) -> str:
    """The humbler mix: mostly rough and cracked, a little polished, one fleck of gild."""
    if h < 0.01:
        return p["gilded"]
    if h < 0.34:
        return p["cracked"]
    if h < 0.62:
        return p["field"]
    return p["polished"]


def _put(w, ctx, forbid, x, y, z, name, **props):
    if (x, z) in forbid:
        return 0
    if _free(ctx, x, y, z) and not w.has(x, y, z):
        w.put(x, y, z, name, **props)
        return 1
    return 0


def _floor(w, ctx, p, forbid, x0, x1, z0, z1, FY, seed) -> int:
    """Level every column up to one plane - a house sits ON something - moss-gapped inside
    the way the sanctum's stylobate is: a ruin floor shows the ground through it."""
    n = 0
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            g, name = _surface(ctx, x, z)
            if g is None or name in ("water", "ice") or g >= FY:
                continue
            edge = x in (x0, x1) or z in (z0, z1)
            for y in range(g + 1, FY + 1):
                if y == FY and not edge and hash01(x, 21, z, seed) < 0.18:
                    continue
                n += _put(w, ctx, forbid, x, y, z, _fabric(p, hash01(x, y, z, seed)))
    return n


def _wall_h(state, face, t, H, seed):
    """How much of this wall run survives. Whole and roofless keep their walls; the fallen
    house keeps stubs - and its DOOR FACE is handled by the caller, frame first."""
    if state == "whole":
        return H
    if state == "roofless":
        if hash01(int(t * 100), 13, face, seed) < 0.18:
            return H - 1                              # a bitten top course here and there
        return H
    # fallen: stubs of nothing much
    return int(hash01(int(t * 100), 17, face, seed) * 2.4)


def _house(w, ctx, p, forbid, h, seed) -> dict:
    ax, az = (int(v) for v in h["at"])
    W, L = int(h["w"]), int(h["l"])
    state = h.get("state", "whole")
    x0, x1 = ax - W // 2, ax + W // 2
    z0, z1 = az - L // 2, az + L // 2
    FY = int(h["floor_y"])
    H = int(p["wall_h"])
    door = h.get("door", "north")
    dz_face = z0 if door == "north" else z1
    feats = {"floor": _floor(w, ctx, p, forbid, x0, x1, z0, z1, FY, seed + ax)}

    # ---- walls: perimeter ring, door face carries the frame WHOLE whatever the state ----
    walls = 0
    faces = [("west", [(x0, z) for z in range(z0, z1 + 1)], 0),
             ("east", [(x1, z) for z in range(z0, z1 + 1)], 1),
             ("north", [(x, z0) for x in range(x0 + 1, x1)], 2),
             ("south", [(x, z1) for x in range(x0 + 1, x1)], 3)]
    for fname, cells, fi in faces:
        span = max(1, len(cells) - 1)
        for i, (x, z) in enumerate(cells):
            t = i / span
            hh = _wall_h(state, fi, t, H, seed + ax)
            corner = (x in (x0, x1)) and (z in (z0, z1))
            if state == "fallen" and corner:
                hh = max(hh, 2)                        # the corners outlast the runs
            is_door_col = fname == door and abs(x - ax) <= 1 and z == dz_face
            window = (state != "fallen" and fname in ("west", "east")
                      and hh >= H and (z - z0) % 3 == 2 and z not in (z0, z1))
            for k in range(hh):
                y = FY + 1 + k
                if is_door_col and x == ax and k < 2:
                    continue                           # the doorway - cut only the centre col
                if window and k == 2:
                    continue                           # a 1x1 window
                sill = window and k == 1
                jamb = fname == door and abs(x - ax) == 1 and z == dz_face and k <= 2
                lintel = is_door_col and x == ax and k == 2
                mat = p["chiseled"] if (sill or lintel) else \
                    (p["polished"] if (corner or jamb)
                     else _fabric(p, hash01(x, y, z, seed + ax)))
                walls += _put(w, ctx, forbid, x, y, z, mat)
    feats["walls"] = walls

    # ---- the door frame stands WHOLE in every state - jambs three high so the lintel has
    # a neighbour to sit against, never floating over the opening ----
    frame = 0
    for dx in (-1, 1):
        for k in range(3):
            frame += _put(w, ctx, forbid, ax + dx, FY + 1 + k, dz_face, p["polished"])
    frame += _put(w, ctx, forbid, ax, FY + 3, dz_face, p["chiseled"])   # the lintel
    feats["door_frame"] = frame

    # ---- gables and roof ----
    rise = W // 2
    if state == "whole":
        gables = 0
        for zg in (z0, z1):
            for x in range(x0, x1 + 1):
                peak = H + max(0, rise - abs(x - ax))
                for k in range(H, peak):
                    if zg == dz_face and abs(x - ax) == 0 and k == H:
                        continue                       # a vent over the door
                    gables += _put(w, ctx, forbid, x, FY + 1 + k, zg,
                                   _fabric(p, hash01(x, k, zg, seed + ax)))
        feats["gables"] = gables
        roof = 0
        for z in range(z0 - 1, z1 + 2):                # overhangs one at each gable end
            for x in range(x0 - 1, x1 + 2):
                d = abs(x - ax)
                if d > rise + 1:
                    continue
                if d == rise + 1 and not (x0 - 1 <= x <= x1 + 1):
                    continue
                y = FY + 1 + H + (rise - d)
                if hash01(x, 51, z, seed + ax) < 0.05:
                    continue                           # weather took a few
                if d == 0:
                    roof += _put(w, ctx, forbid, x, y, z, p["slab"], type="bottom")
                else:
                    facing = "east" if x < ax else "west"   # treads ascend toward the ridge
                    roof += _put(w, ctx, forbid, x, y, z, p["stair"],
                                 facing=facing, half="bottom")
        feats["roof"] = roof
        # the chimney, on the south gable's east shoulder, and the cold hearth inside it
        cx = x1 - 1
        for k in range(H + rise + 2):
            feats["chimney"] = feats.get("chimney", 0) + _put(
                w, ctx, forbid, cx, FY + 1 + k, z1, _fabric(p, hash01(cx, k, z1, seed)))
        feats["chimney"] = feats.get("chimney", 0) + _put(
            w, ctx, forbid, cx, FY + 1 + H + rise + 2, z1, "polished_blackstone_wall")
        # the hearth and bench stand on real floor: their FY cells are placed first, because
        # the stylobate is moss-gapped by hash and a lantern on a gap is standing on air
        _put(w, ctx, forbid, cx, FY, z1 - 1, p["polished"])
        feats["hearth"] = _put(w, ctx, forbid, cx, FY + 1, z1 - 1, "soul_lantern",
                               hanging="false")
        bench = 0
        for dz in (-1, 0, 1):
            _put(w, ctx, forbid, x0 + 1, FY, az + dz, p["polished"])
            bench += _put(w, ctx, forbid, x0 + 1, FY + 1, az + dz, p["slab"], type="bottom")
        feats["bench"] = bench
    elif state == "roofless":
        # one gable survives whole, the other is torn to a diagonal
        gables = 0
        for gi, zg in enumerate((z0, z1)):
            for x in range(x0, x1 + 1):
                peak = H + max(0, rise - abs(x - ax))
                if gi == 1:
                    peak = min(peak, H + max(0, (x - ax)))   # the tear: one side kept
                for k in range(H, peak):
                    gables += _put(w, ctx, forbid, x, FY + 1 + k, zg,
                                   _fabric(p, hash01(x, k, zg, seed + ax)))
        feats["gables"] = gables
    else:
        # fallen: the tumble, one heap where the east wall went
        tumble = 0
        for dz in range(-1, 2):
            for do in range(1, 3):
                x2, z2 = x1 + do, az + dz
                g2, nm = _surface(ctx, x2, z2)
                if g2 is not None and nm not in ("water", "ice") and \
                        hash01(x2, 31, z2, seed) < 0.7 - 0.2 * do:
                    tumble += _put(w, ctx, forbid, x2, g2 + 1, z2,
                                   _fabric(p, hash01(x2, 5, z2, seed)))
        feats["tumble"] = tumble
    return feats


def _lane(w, ctx, p, forbid, pts, seed) -> int:
    """Ruined slab pavement between the given points - the ruinway's own idiom, gap hash and
    all, so the hamlet's lane and the way it joins read as one paving. It respects the
    lantern forbid set like everything else: a street lamp stands IN the lane line."""
    n = 0
    for (a, b) in zip(pts, pts[1:]):
        ax, az = float(a[0]), float(a[1])
        bx, bz = float(b[0]), float(b[1])
        steps = int(math.hypot(bx - ax, bz - az) * 2)
        for i in range(steps + 1):
            t = i / max(1, steps)
            for u in (-0.5, 0.5):
                dxn, dzn = bz - az, -(bx - ax)
                dn = math.hypot(dxn, dzn) or 1.0
                x = int(round(ax + (bx - ax) * t + dxn / dn * u))
                z = int(round(az + (bz - az) * t + dzn / dn * u))
                g, nm = _surface(ctx, x, z)
                if (x, z) in forbid or g is None or nm in ("water", "ice") \
                        or not _free(ctx, x, g + 1, z) or w.has(x, g + 1, z):
                    continue
                if hash01(x, 41, z, seed) < 0.22:
                    continue
                w.put(x, g + 1, z, p["slab"], type="bottom")
                n += 1
    return n


def build_hamlet(cfg: dict, donors=None) -> Canvas:
    p = {**HAMLET, **cfg}
    if not p.get("under") or not p.get("houses"):
        raise ValueError("hamlet needs params.under and params.houses")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    forbid = {(int(a), int(b)) for a, b in p.get("lantern_grid", [])}
    w = World()
    feats = {}
    for i, h in enumerate(p["houses"]):
        feats[f"house_{i}_{h.get('state', 'whole')}"] = _house(w, ctx, p, forbid, h, seed)
    feats["lane"] = _lane(w, ctx, p, forbid, p.get("lane", []), seed)
    # the forbid set is a CONTRACT: nothing this design built may stand in a lantern column
    for (x, y, z) in w.cells:
        assert (x, z) not in forbid, f"hamlet cell in lantern column at {(x, y, z)}"
    return w.canvas({"kind": "hamlet", "profile_view": "face", "facing": [0, -1],
                     "features_built": feats})
