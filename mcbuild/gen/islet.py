"""A sheared-off chunk of the island hanging in the void, with a trading post on it.

    islet:  rock that reads as fallen rather than placed - an elliptical raft, thickest at the middle,
            ragged and undercut around the rim so the bottom looks torn. A flat shelf on top carries
            the shop: a slab counter, barrels behind it, an awning on fence posts, lanterns.

Sited under the taproot's foot so the root has somewhere to arrive. `spike` raises a small boss of
rock to meet it, otherwise the root ends in mid-air two blocks above the ground.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .ground import AIRY, holds, is_soil
from .vertical import Ctx, World, rock_name

ISLET = {
    "under": None,               # capture, so the site can be checked for collisions
    "center": None,              # world (x, z)
    "top_y": 150,                # the shelf the shop stands on
    "rx": 8.0, "rz": 7.0,        # raft radii
    "depth": 9,                  # rock below the shelf at the thickest point
    "wobble": 2.2,               # how ragged the rim is
    "spike": None,               # world (x, z) raised one course to meet a root; None to skip
    "moss": 0.55,                # share of the top course that is moss rather than bare rock
    "grass": 0.10, "carpet": 0.18,
    "vine_rate": 0.16, "vine_len": [2, 7],
    "shop": True,
    "shop_offset": [0, 3],       # keep the counter clear of the centre - that is where the root lands
    "counter_len": 5,
    "labels": [],                # sign text, one per barrel
    "lanterns": 4,
    "seed": 0,
}

TOP = [("moss_block", 0.62), ("mossy_cobblestone", 0.26), ("cobblestone", 0.12)]


def build_islet(cfg: dict, donors=None) -> Canvas:
    p = {**ISLET, **cfg}
    if not p.get("center"):
        raise ValueError("islet needs params.center = [x, z]")
    ctx = Ctx(p["under"]) if p.get("under") else None
    cx, cz = (int(v) for v in p["center"])
    ty, seed = int(p["top_y"]), int(p["seed"])
    w = World()

    shelf = _raft(w, cx, cz, ty, p, seed)
    _dress(w, shelf, ty, p, seed, ctx)
    if p["shop"]:
        ox, oz = (int(v) for v in p["shop_offset"])
        _shop(w, shelf, cx + ox, cz + oz, ty, p, seed)
    if p["spike"]:                                     # after the shop, so nothing overwrites the boss
        sx, sz = (int(v) for v in p["spike"])
        w.put(sx, ty + 1, sz, "mossy_cobblestone")     # one course only: the root's tip lantern owns ty+2
    _vines(w, shelf, ty, p, seed, ctx)
    _prune_vines(w, ctx)

    hits = _collisions(ctx, w)
    return w.canvas({"kind": "islet", "center": [cx, cz], "top_y": ty, "shelf_cells": len(shelf),
                     "collisions": hits})


# ------------------------------------------------------------------ rock

def _raft(w: World, cx: int, cz: int, ty: int, p: dict, seed: int) -> list:
    """Elliptical raft: full depth in the middle, thinning and tearing toward the rim."""
    rx, rz, depth, wob = float(p["rx"]), float(p["rz"]), int(p["depth"]), float(p["wobble"])
    shelf = []
    for x in range(cx - int(rx) - 3, cx + int(rx) + 4):
        for z in range(cz - int(rz) - 3, cz + int(rz) + 4):
            d = (((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2) ** 0.5
            edge = 1.0 + 0.10 * wob * (hash01(x, z, 11, seed) - 0.5)
            if d > edge:
                continue
            # thickness falls off with distance and gets bitten into near the rim
            t = depth * (1.0 - d ** 1.7)
            t += wob * (hash01(x, z, 13, seed) - 0.45)
            n = max(1, int(round(t)))
            if d > 0.82 and hash01(x, z, 17, seed) < 0.22:
                continue                                # a piece that sheared away
            for k in range(n):
                w.put(x, ty - k, z, rock_name(x, ty - k, z, seed))
            shelf.append((x, z))
    if not shelf:
        raise ValueError("islet came out empty - check rx/rz/depth")
    return shelf


def _dress(w: World, shelf, ty: int, p: dict, seed: int, ctx=None):
    """Top course: mostly moss, with grass and carpet so the shelf is not a flat slab of one block."""
    for (x, z) in shelf:
        h = hash01(x, z, 23, seed)
        acc = 0.0
        for name, weight in TOP:
            acc += weight
            if h < acc:
                w.put(x, ty, z, name if name != "moss_block" or h < p["moss"] else "mossy_cobblestone")
                break
    for (x, z) in shelf:
        # plant against what will REALLY be underfoot: where the world already holds something the
        # design does not, that block is what the grass has to root in.
        under = w.name(x, ty, z)
        if ctx is not None and ctx.name_at(x, ty, z) not in AIRY:
            under = ctx.name_at(x, ty, z)
        if not is_soil(under) or w.has(x, ty + 1, z):
            continue
        h = hash01(x, z, 29, seed)
        if h < p["grass"]:
            w.put(x, ty + 1, z, "short_grass")
        elif h < p["grass"] + p["carpet"]:
            w.put(x, ty + 1, z, "moss_carpet")


def _vines(w: World, shelf, ty: int, p: dict, seed: int, ctx=None):
    """Strands off the torn rim, so the raft reads as hanging rather than floating."""
    lo, hi = p["vine_len"]
    edge = set(shelf)
    rim = [(x, z) for (x, z) in shelf
           if any((x + dx, z + dz) not in edge for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    on = set(shelf)
    # (dx, dz) is where the vine hangs; the property names the side facing BACK at the rock, so a
    # strand one cell east of the raft clings WEST. Getting this backwards attaches it to thin air.
    for (x, z) in rim:
        for dx, dz, facing in ((1, 0, "west"), (-1, 0, "east"), (0, 1, "north"), (0, -1, "south")):
            if (x + dx, z + dz) in on or hash01(x, z, 31, seed) >= p["vine_rate"]:
                continue
            anchor = w.name(x, ty, z)
            if ctx is not None and ctx.name_at(x, ty, z) not in AIRY:
                anchor = ctx.name_at(x, ty, z)
            if not holds(anchor):
                continue                                # a slab or a wall will not hold a strand
            base = _lowest(w, x, ty, z)
            L = lo + int(hash01(x, z, 37, seed) * (hi - lo + 1))
            for k in range(L):
                y = base - k
                if w.has(x + dx, y, z + dz):
                    break
                # the strand may only continue while something REAL is beside it or a vine is above
                beside = w.name(x, y, z) or (ctx.name_at(x, y, z) if ctx is not None else "air")
                above = w.name(x + dx, y + 1, z + dz)
                if not holds(beside) and above != "vine":
                    break
                props = {"east": "false", "north": "false", "south": "false", "west": "false", "up": "false"}
                props[facing] = "true"
                w.put(x + dx, y, z + dz, "vine", **props)
            break


def _prune_vines(w: World, ctx=None):
    """Drop any vine that nothing holds.

    A strand is legal if the face it names is a full block, or a vine hangs directly above it. Neither
    can be settled while placing - the block above may be something the WORLD has and this design does
    not know about - so sweep afterwards, top down, until nothing more falls."""
    face = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
    changed = True
    while changed:
        changed = False
        for (x, y, z), (name, props) in sorted(w.cells.items(), key=lambda kv: -kv[0][1]):
            if name != "vine":
                continue
            held = False
            for d, (dx, dz) in face.items():
                if props.get(d) != "true":
                    continue
                nb = w.name(x + dx, y, z + dz)
                if nb is None and ctx is not None:
                    nb = ctx.name_at(x + dx, y, z + dz)
                if nb and holds(nb):
                    held = True
            # a vine above only saves it if the WORLD leaves room for that vine: where the world
            # already holds a block there, the capture wins the merge and the strand is orphaned.
            above_ok = w.name(x, y + 1, z) == "vine" and (
                ctx is None or ctx.name_at(x, y + 1, z) in AIRY)
            if not held and not above_ok:
                del w.cells[(x, y, z)]
                changed = True


def _lowest(w: World, x: int, ty: int, z: int) -> int:
    y = ty
    while w.has(x, y - 1, z):
        y -= 1
    return y


# ------------------------------------------------------------------ the shop

def _shop(w: World, shelf, cx: int, cz: int, ty: int, p: dict, seed: int):
    """A counter facing south, barrels behind it, an awning over both."""
    on = set(shelf)
    half = int(p["counter_len"]) // 2
    y = ty + 1
    counter = [(cx + i, cz) for i in range(-half, half + 1) if (cx + i, cz) in on]
    back = [(x, cz - 1) for (x, _) in counter if (x, cz - 1) in on]
    for (x, z) in counter:
        w.put(x, y, z, "stone_brick_slab", type="top", waterlogged="false")
    for i, (x, z) in enumerate(back):
        w.put(x, y, z, "barrel", facing="south", open="false")
        label = p["labels"][i] if i < len(p["labels"]) else ""
        if label and (x, z - 1) in on:
            w.put(x, y + 1, z, "oak_wall_sign", facing="south", waterlogged="false")
    # a lectern at the west end of the counter, so the post reads as staffed
    if counter and (counter[0][0] - 1, cz) in on:
        w.put(counter[0][0] - 1, y, cz, "lectern", facing="east", has_book="false", powered="false")
    _awning(w, on, counter, ty, int(p["lanterns"]))


def _awning(w: World, on: set, counter: list, ty: int, lanterns: int):
    """Fence posts at the counter's ends carrying a slab roof, lanterns hung underneath."""
    if len(counter) < 2:
        return
    y = ty + 1
    x0, z0 = counter[0]
    x1, _ = counter[-1]
    posts = [(x0, z0 + 1), (x1, z0 + 1)]
    for (px, pz) in posts:
        if (px, pz) not in on:
            continue
        for k in (0, 1, 2):
            w.put(px, y + k, pz, "oak_fence", north="false", south="false", east="false",
                  west="false", waterlogged="false")
    roof_y = y + 3
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for z in (z0, z0 + 1):
            if (x, z) in on:
                w.put(x, roof_y, z, "spruce_slab", type="bottom", waterlogged="false")
    hung = 0
    for x in range(min(x0, x1), max(x0, x1) + 1):
        if hung >= lanterns:
            break
        if (x, z0 + 1) in on and w.has(x, roof_y, z0 + 1) and not w.has(x, roof_y - 1, z0 + 1):
            w.put(x, roof_y - 1, z0 + 1, "lantern", hanging="true", waterlogged="false")
            hung += 1


def _collisions(ctx, w: World) -> int:
    if ctx is None:
        return 0
    return sum(1 for (x, y, z) in w.cells
               if ctx.name_at(x, y, z) not in ("air", "cave_air", "void_air", "vine"))
