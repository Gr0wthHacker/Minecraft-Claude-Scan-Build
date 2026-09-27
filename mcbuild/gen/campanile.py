"""The Campanile - the sanctum's bell tower, standing west of the basilica, with its tenant.

WHY A TOWER, AND WHY THERE. The sanctum's facade carries an EMPTY bell-cote - "the arch a bell
is missing from" - and a campanile is the building that answers it: the bell survived, the
cote did not. Towers are also the one architectural form this medium renders best (the void
tower and the bat tower are the two builds that passed review on sight). The pad is measured:
14x22 free at X-24209..-24196 / Z29962..29983 off the 15:01 scan, needing no retirement at
all, and the tower takes the 7-wide gap in the ground design's lantern 9-grid between the
X-24201 and X-24192 columns - three blocks clear of the sanctum's west pilasters, which is
where a campanile stands.

HEIGHT IS THE HIERARCHY. The sanctum's pediment peaks at Y52 and the trees crown at ~Y52; the
campanile's parapet rides at ~Y59, so it reads over both from the entrance shaft, which is the
view that matters - players arrive from above. The dark zone (2 sky columns) is the point: the
tower carries its own cold light, one soul glow in the belfry beside the bell.

WHAT THE VOID TOWER TAUGHT, APPLIED IN A ONE-TONE FAMILY. Blackstone's grades sit within 12
RGB of each other (measured), so a value line cannot be drawn with material here the way
deepslate draws on stone - the lines are GEOMETRY instead: a flared plinth, string courses
PROUD by one cell, a corbelled overhang under the belfry, and crenellations whose course is
left EMPTY by the wall loop (the crown trap, pinned once already). Texture still separates -
chiseled for the dressed lines, gilded flecks in the fabric - but nothing relies on it.

THE RUIN IS ONE PLANE. The parapet and top courses shear on the north-east corner - a plane,
never a cosine - with the fallen masonry in one heap at the foot. Everything else stands:
a building that has taken damage, not damage suggesting a building.

THE OWL is the quarter's animal-on-architecture, perched on the south-west merlon: upright
barrel, two ear tufts, a pale face with black bead eyes - silhouette-first, greys on
near-black so the value step carries it. It sits ON placed parapet cells by construction,
which is the anchoring rule every clinging feature in this repo has paid for once.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _free, _surface, _weathered

CAMPANILE = {
    "under": None,
    "at": None,                # [x, z] centre of the shaft
    "side": 7,                 # exterior; odd, so faces have a centre
    "base_y": None,            # plinth top course - PIN once built (the ring's seat lesson)
    "shaft_h": 12,             # courses of shaft above the plinth
    "belfry_h": 4,
    "door": "south",           # faces the sanctum spur and the way
    "bird": True,
    "seed": 0,

    "field": "polished_blackstone_bricks",
    "cracked": "cracked_polished_blackstone_bricks",
    "rough": "blackstone",
    "gilded": "gilded_blackstone",
    "chiseled": "chiseled_polished_blackstone",
    "slab": "polished_blackstone_brick_slab",
    "stair": "polished_blackstone_brick_stairs",
    "gild_rate": 0.03,

    "body": "gray_wool",       # the owl
    "breast": "light_gray_wool",
    "face": "white_wool",
    "eye": "black_wool",
}


def _put(w, ctx, x, y, z, name, **props):
    if _free(ctx, x, y, z) and not w.has(x, y, z):
        w.put(x, y, z, name, **props)
        return 1
    return 0


def _sheared(p, x, y, z, ax, az, r, top_y):
    """The ruin plane: TRUE where the NE-corner shear has taken this cell. A plane falling
    away north-east - the witch's-hat lesson says never a cosine."""
    depth = (x - (ax + r)) + ((az - r) - z)            # grows toward the NE corner
    return depth > -2 and y > top_y - 3 + max(0, -depth)


def build_campanile(cfg: dict, donors=None) -> Canvas:
    p = {**CAMPANILE, **cfg}
    if not p.get("under") or not p.get("at"):
        raise ValueError("campanile needs params.under and params.at")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    ax, az = (int(v) for v in p["at"])
    S = int(p["side"])
    r = S // 2
    x0, x1, z0, z1 = ax - r, ax + r, az - r, az + r
    if p.get("base_y") is not None:
        FY = int(p["base_y"])
    else:
        gs = sorted(g for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)
                    for g, nm in [_surface(ctx, x, z)]
                    if g is not None and nm not in ("water", "ice"))
        FY = gs[len(gs) // 2] + 1                      # then PIN it in the config

    w = World()
    feats = {}

    # ---- plinth: one course wider all round, every column seated on its own ground ----
    n = 0
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            g, nm = _surface(ctx, x, z)
            if g is None or nm in ("water", "ice") or g >= FY:
                continue
            for y in range(g + 1, FY + 1):
                mat = p["chiseled"] if y == FY else _weathered(p, hash01(x, y, z, seed))
                n += _put(w, ctx, x, y, z, mat)
    feats["plinth"] = n

    H = int(p["shaft_h"])
    BH = int(p["belfry_h"])
    top = FY + H + BH + 2                              # parapet course
    door_face = p.get("door", "south")
    dz_face = z1 if door_face == "south" else z0

    # ---- shaft: hollow square, chiseled quoins, proud string courses at thirds ----
    n = 0
    strings = (FY + 1 + H // 3, FY + 1 + (2 * H) // 3)
    for k in range(H):
        y = FY + 1 + k
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                on_ring = x in (x0, x1) or z in (z0, z1)
                if not on_ring:
                    continue
                if _sheared(p, x, y, z, ax, az, r, top):
                    continue
                # the doorway: centre column of the door face, two courses, lintel above
                if z == dz_face and x == ax and k < 2:
                    continue
                # glazed slits, sills below: east and west faces at two heights,
                # pane connections set ALONG the wall or it renders as a lone post
                slit = (x in (x0, x1) and z == az and k in (4, 5, 8, 9))
                if slit:
                    n += _put(w, ctx, x, y, z, "glass_pane",
                              north="true", south="true", east="false", west="false")
                    continue
                corner = x in (x0, x1) and z in (z0, z1)
                lintel = z == dz_face and x == ax and k == 2
                sill = x in (x0, x1) and z == az and k in (3, 7)
                mat = p["chiseled"] if (corner or lintel or sill) \
                    else _weathered(p, hash01(x, y, z, seed))
                n += _put(w, ctx, x, y, z, mat)
        if y in strings:                               # proud by one cell, a drawn line
            for x in range(x0 - 1, x1 + 2):
                for z in range(z0 - 1, z1 + 2):
                    edge = x in (x0 - 1, x1 + 1) or z in (z0 - 1, z1 + 1)
                    if edge and not _sheared(p, x, y, z, ax, az, r, top):
                        n += _put(w, ctx, x, y, z, p["chiseled"])
    feats["shaft"] = n
    # jambs beside the doorway
    feats["door"] = sum(_put(w, ctx, ax + dx, FY + 1 + k, dz_face, p["chiseled"])
                        for dx in (-1, 1) for k in range(2))

    # ---- corbel: the overhang the belfry sits on ----
    n = 0
    yc = FY + H + 1
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            if _sheared(p, x, yc, z, ax, az, r, top):
                continue
            edge = x in (x0 - 1, x1 + 1) or z in (z0 - 1, z1 + 1)
            ring = x in (x0, x1) or z in (z0, z1)
            if edge or ring:
                n += _put(w, ctx, x, yc, z, p["chiseled"] if edge
                          else _weathered(p, hash01(x, yc, z, seed)))
    feats["corbel"] = n

    # ---- belfry: corner piers and open arches, a cap, THE BELL hanging inside ----
    n = 0
    for k in range(BH - 1):
        y = yc + 1 + k
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                on_ring = x in (x0, x1) or z in (z0, z1)
                if not on_ring or _sheared(p, x, y, z, ax, az, r, top):
                    continue
                # the arches: middle three cells of every face are OPEN for the bell to show
                mid = (abs(x - ax) <= 1 and z in (z0, z1)) or \
                      (abs(z - az) <= 1 and x in (x0, x1))
                if mid:
                    continue
                n += _put(w, ctx, x, y, z, _weathered(p, hash01(x, y, z, seed)))
    yc2 = yc + BH
    for x in range(x0, x1 + 1):                        # the cap the bell hangs from
        for z in range(z0, z1 + 1):
            if not _sheared(p, x, yc2, z, ax, az, r, top):
                n += _put(w, ctx, x, yc2, z, _weathered(p, hash01(x, yc2, z, seed)))
    feats["belfry"] = n
    feats["bell"] = 0
    if w.has(ax, yc2, az):
        feats["bell"] = _put(w, ctx, ax, yc2 - 1, az, "bell",
                             attachment="ceiling", facing="north")
    # the cold glow, hanging from the cap beside the bell - a chain hangs from the block
    # ABOVE it, and the cap is that block, so the string finds a real ceiling
    feats["light"] = _put(w, ctx, ax - 1, yc2 - 1, az - 1, "soul_lantern", hanging="true") \
        if w.has(ax - 1, yc2, az - 1) else 0

    # ---- parapet and crenellations: the merlon course left EMPTY by everything above ----
    n = 0
    yp = yc2 + 1
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            on_ring = x in (x0, x1) or z in (z0, z1)
            if on_ring and not _sheared(p, x, yp, z, ax, az, r, top):
                n += _put(w, ctx, x, yp, z, _weathered(p, hash01(x, yp, z, seed)))
    merlons = 0
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            on_ring = x in (x0, x1) or z in (z0, z1)
            if not on_ring or (x + z) % 2:
                continue                               # the gaps ARE the crenellation
            if _sheared(p, x, yp + 1, z, ax, az, r, top):
                continue
            merlons += _put(w, ctx, x, yp + 1, z, p["chiseled"])
    feats["parapet"] = n
    feats["merlons"] = merlons

    # ---- the tumble: what the shear threw down, one heap at the NE foot. Fallen masonry
    # lands on the FLOOR - _surface reads the sanctum's standing wall top as footing three
    # cells east, and the first heap perched two blocks on it at Y49 ----
    n = 0
    for dx in range(1, 4):
        for dz in range(-3, 1):
            x2, z2 = x1 + dx, z0 + dz
            g2, nm = _surface(ctx, x2, z2)
            if g2 is not None and nm not in ("water", "ice") and g2 <= FY + 1 and \
                    hash01(x2, 31, z2, seed) < 0.75 - 0.18 * (dx - 1):
                n += _put(w, ctx, x2, g2 + 1, z2, _weathered(p, hash01(x2, 5, z2, seed)))
    feats["tumble"] = n

    # ---- the owl, on the south-west parapet ----
    if p.get("bird"):
        bx, bz = x0, z1                                # the SW corner, clear of the shear
        base = yp + 1
        # a corner flag under the whole 2x2 body: the parapet ring covers only two of the
        # four cells and the other two hang over the hollow shaft - the first owl floated
        for dx in (0, 1):
            for dz in (-1, 0):
                _put(w, ctx, bx + dx, yp, bz + dz, p["chiseled"])
        body = 0
        for k in range(3):                             # barrel 2x2, three courses
            for dx in (0, 1):
                for dz in (-1, 0):
                    mat = p["breast"] if (dz == 0 and k < 2) else p["body"]
                    body += _put(w, ctx, bx + dx, base + k, bz + dz, mat)
        # head: one course, with the face on the south side
        for dx in (0, 1):
            for dz in (-1, 0):
                body += _put(w, ctx, bx + dx, base + 3, bz + dz,
                             p["face"] if dz == 0 else p["body"])
        # eyes: black beads ON the face cells - frontmost by construction
        eyes = sum(_put(w, ctx, bx + dx, base + 3, bz + 1, p["eye"]) for dx in (0, 1))
        # ear tufts on the outer top corners
        tufts = _put(w, ctx, bx, base + 4, bz - 1, p["body"]) + \
            _put(w, ctx, bx + 1, base + 4, bz - 1, p["body"])
        feats["owl"] = {"body": body, "eyes": eyes, "tufts": tufts}

    return w.canvas({"kind": "campanile", "profile_view": "face", "facing": [0, 1],
                     "base_y": FY, "features_built": feats})
