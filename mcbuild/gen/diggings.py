"""THE DIGGINGS - a worked-out landscape you walk THROUGH, with two shops cut into it.

Jack: *"i dont want a bunch of buildings to go into, this is just a village then"* ... *"we can
have a small amount of buildings, but the rest should be other things"* ... *"we can do a
landscape or something with 1 or 2 small shops integrated."*

This replaces `Boomtown Spine` on the Frontier's middle block - 53 x 46 at V24 U47, the largest
lot in the land - which was **seven false-fronted shops and 0 interactive blocks**, and which is
the thing he complained about three separate times.

**THE ROUTE IS A HARD CONSTRAINT AND IT IS MEASURED.** `Park Ways` paves NOTHING inside this lot -
0 of its 2,438 columns - so the walk from the spine to Mining Square lived entirely inside the old
module: its boardwalk at world U68-70, joining the ground layer's own spur at V19-23 / U69-71 in
the west and the V77-79 cross walk in the east. Delete the module and that walk goes with it. So
the trail comes FIRST here and everything else is shaped around it, which is also why the banks
are battered AWAY from it rather than merely kept off it.

    THE TRAIL      three wide, dead straight, at grade, west to east. Both ends land on paving
                   that already exists. Trodden gravel and cobble with a timber kerb.
    THE BANKS      spoil and cut rock either side, rising away from the trail and falling to the
                   lot's own edges so the block still reads open from both cross avenues
    TWO SHOPS      cut INTO the banks rather than standing on the lawn - a rock recess, a timber
                   shopfront, a counter, a sign. Offset along the trail so they do not face
                   each other across it
    THE WORKINGS   a collared shaft with a windlass over it, timber cribbing, tipped ore, and a
                   ground-level cart rail beside the trail

**THE GEOLOGY IS THE RIDGE'S OWN**, imported rather than restated: same materials, same repeating
strata, same `_pick`. Two files each holding a copy of what rock looks like is how one mountain
becomes two different mountains in the same land.

**NOTHING HERE IS AN ELEVATED RAILWAY.** The ore line that used to run this land was deleted on
sight for piercing a building's wall five courses up; the cart rail here lies ON the ground beside
the trail, which is what a diggings tramway actually is, and it is a PROP rather than a third
railway to work out.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .mineridge import ROCK, _BAND, _CRUST, _DARK, _MID, _STRATA, _noise, _pick, _terrace

#: The shops' own kit - the town's timber, so two shops cut into a bank still read as the same
#: hand as the Trailhead Gate and the Assay Office.
SHOP = {
    "post": "spruce_log",
    "beam": "stripped_spruce_log",
    "plank": "spruce_planks",
    "slab": "spruce_slab",
    "stair": "spruce_stairs",
    "fence": "spruce_fence",
    "shutter": "spruce_trapdoor",
    "counter": "spruce_slab",
    "sign": "spruce_wall_sign",
    "glass": "glass_pane",
    "lamp": "lantern",
    "glow": "ochre_froglight",
    "barrel": "barrel",
    "canvas_a": "red_wool",
    "canvas_b": "white_wool",
    "board": "white_wool",
    "base": "stone_bricks",
    "plinth": "polished_blackstone_bricks",
    "trail": "gravel",
    "trail_b": "cobblestone",
    "kerb": "cobblestone_slab",
    "rail": "rail",
    "chain": "iron_chain",
}

DIGGINGS = {
    "kind": "diggings",
    "lot": None,               # [dv, du]
    "at": None,                # [V, U]
    "anchor": [97500, 203, 80300],
    "trail_u": 21,             # the walk's near edge, in LOCAL u
    "trail_w": 3,              # ...and its width. World U68-70, which is where the old one was.
    "verge": 2,                # level ground either side of it before the banks start
    "bank": 11,                # how high the banks go away from the trail
    "mounds": [],              # [[v, u, height, radius], ...] - the high points
    "yard": None,              # [v, u, w, d] - a level working yard off the trail
    "shops": [],               # see `_shop`
    "workings": [],            # [[v, u, kind], ...] - kind: shaft | crib | ore | pine
    "bench": 3,
    "seed": 0,
    "title": "THE DIGGINGS",
}


# --------------------------------------------------------------------------- the ground


def _field(p: dict, dv: int, du: int) -> np.ndarray:
    """The height of the diggings, as a field - and the trail is a VALLEY in it, not a gap.

    **BANKS BATTERED AWAY FROM THE TRAIL, NOT MERELY KEPT OFF IT.** Held at a constant height and
    simply not placed on the walk, spoil either side reads as two walls with a corridor between
    them - which is a trench, and it is the same failure the ridge's first tunnel had. Rising with
    distance, it reads as a way cut through diggings, which is what it is.

    And it FALLS TO THE LOT'S OWN EDGES, because this block is bounded north and south by the
    land's two cross avenues: a bank at full height against them would wall a guest street.
    """
    tu0 = int(p.get("trail_u", 21))
    tw = max(1, int(p.get("trail_w", 3)))
    verge = int(p.get("verge", 2))
    top = float(p.get("bank", 11))
    seed = int(p.get("seed", 0))

    uu = np.arange(du)[None, :].astype(float)
    vv = np.arange(dv)[:, None].astype(float)
    # distance out from the trail's own edges
    below = np.clip(tu0 - verge - uu, 0, None)
    above = np.clip(uu - (tu0 + tw - 1 + verge), 0, None)
    out = np.maximum(below, above)
    h = np.minimum(out * 0.85, top)

    for mv, mu, mh, mr in (p.get("mounds") or []):
        d = np.sqrt((vv - float(mv)) ** 2 + (uu - float(mu)) ** 2) / max(float(mr), 1.0)
        h = np.maximum(h, float(mh) * np.clip(1.0 - d, 0.0, 1.0) ** 0.95)

    # **THE FALL TO THE LOT'S BOUNDARY IS CLAMPED AFTER THE MOUNDS, NOT BEFORE THEM.** Applied
    # first, a `maximum` over the mounds simply overrides it and a twelve-course spoil bank ends up
    # standing three courses proud on the lot's own edge - against the land's cross avenue, which
    # is a guest street. This block is bounded north and south by both of them.
    edge = np.minimum(np.minimum(vv, dv - 1 - vv), np.minimum(uu, du - 1 - uu))
    h = np.minimum(h, edge * 0.9)

    # the trail and its verge are level ground, whatever a mound wanted
    lane = (uu >= tu0 - verge) & (uu <= tu0 + tw - 1 + verge)
    h = np.where(np.broadcast_to(lane, h.shape), 0.0, h)

    # **AND THE YARD, WHICH IS THE ONE THING THAT MAKES THIS A PLACE RATHER THAN A CORRIDOR.** A
    # trail between banks is a route; a route with somewhere to stand on it is somewhere to be.
    # The workings gather round it, so a guest walking the trail arrives at the diggings instead
    # of merely passing them.
    if p.get("yard"):
        yv, yu, yw, yd = (int(x) for x in p["yard"])
        y_mask = ((vv >= yv) & (vv < yv + yw) & (uu >= yu) & (uu < yu + yd))
        h = np.where(np.broadcast_to(y_mask, h.shape), 0.0, h)

    h = h * (0.80 + 0.34 * _noise(dv, du, seed) + 0.12 * (_noise(dv, du, seed + 7, grain=3) - 0.5))
    return _terrace(h, int(p.get("bench", 3)), _noise(dv, du, seed + 101, grain=5))


def _fill(lot: _Lot, h: np.ndarray, seed: int) -> int:
    n = 0
    hi = np.clip(np.floor(h + 0.5), 0, lot.c.sy - 1).astype(int)
    noise = _noise(lot.dv, lot.du, seed)
    for v in range(lot.dv):
        for u in range(lot.du):
            k = int(hi[v, u])
            if k <= 0:
                continue
            lift = (noise[v, u] - 0.5) * 7.0
            for y in range(k):
                if y >= k - 1:
                    key = _pick(_CRUST, v, u, y, seed)
                elif k <= 4:
                    key = _pick(_MID, v, u, y, seed)
                elif y < 2:
                    key = _pick(_DARK, v, u, y, seed)
                else:
                    key = _pick(_STRATA[int((y + lift) // _BAND) % len(_STRATA)], v, u, y, seed)
                if key == "scree" and y < k - 1:
                    key = "rock"          # gravel is a CRUST material; it falls (rule 13)
                n += 1 if lot.put(v, y, u, ROCK[key]) else 0
    return n


def _trail(lot: _Lot, p: dict, seed: int) -> dict:
    """The walk, first and straight. Both ends land on paving that is already there.

    IT STANDS ONE COURSE PROUD OF THE LAWN, like every other made surface in this land, so it
    carries its own kerb and reads as a way rather than as a strip of different grass.
    """
    tu0, tw = int(p["trail_u"]), int(p["trail_w"])
    n = 0
    for v in range(lot.dv):
        for u in range(tu0, tu0 + tw):
            r = hash01(v, u, seed + 5)
            n += 1 if lot.put(v, 0, u, SHOP["trail" if r < 0.45 else "trail_b"]) else 0
    for v in range(lot.dv):                                     # the kerb, both sides
        for u in (tu0 - 1, tu0 + tw):
            lot.slab(v, 0, u, SHOP["kerb"], "bottom")
    # A GROUND-LEVEL TRAMWAY, which is what a diggings has - not an elevated railway. The last
    # one was deleted for piercing a building's wall five courses up.
    for v in range(2, lot.dv - 2):
        lot.put(v, 1, tu0 + tw + 1, SHOP["rail"], shape="east_west", waterlogged="false")
        n += 1
    # flush lights in the trail's own surface: Jack's idiom, and nothing to knock off a path
    for v in range(4, lot.dv - 3, 9):
        lot.put(v, 0, tu0 + tw // 2, SHOP["glow"])
    yard = 0
    if p.get("yard"):
        yv, yu, yw, yd = (int(x) for x in p["yard"])
        for v in range(yv, yv + yw):
            for u in range(yu, yu + yd):
                r = hash01(v, u, seed + 6)
                yard += 1 if lot.put(v, 0, u, SHOP["trail_b" if r < 0.6 else "trail"]) else 0
        for v in range(yv, yv + yw, 6):                  # a lit post rail round its outer edge
            lot.put(v, 0, yu + yd - 1, SHOP["glow"])
        for u in range(yu, yu + yd, 5):
            lot.fence(yv, 1, u, "u", key=SHOP["fence"])
            lot.fence(yv + yw - 1, 1, u, "u", key=SHOP["fence"])
    return {"u": [tu0, tu0 + tw - 1], "cells": n, "yard": yard}


# --------------------------------------------------------------------------- the shops


def _shop_where(spec: dict, p: dict):
    """The shop's own frame: where its front stands and which way it looks.

    ONE FUNCTION ANSWERS IT, because the reserve and the build must agree about it exactly - two
    copies of this arithmetic is how a room gets hollowed out from under a cover that was forced
    somewhere else.
    """
    tu0, tw = int(p["trail_u"]), int(p["trail_w"])
    verge = int(p.get("verge", 2))
    side = int(spec.get("side", 1))
    if side > 0:
        return tu0 + tw - 1 + verge + 1, 1, "north"
    return tu0 - verge - 1, -1, "south"


def _shop_reserve(h: np.ndarray, spec: dict, p: dict) -> None:
    """**THE MASS OVER A SHOP IS FORCED BEFORE ANYTHING IS FILLED.** Written the obvious way -
    hollow the room and frame it after the ground is built - the recess is cut into whatever the
    bank happened to give at that column, which is an open bay with two walls. It is the ridge's
    own tunnel lesson, and the first version of this file had the call in the wrong order so the
    cover was never placed at all."""
    v0 = int(spec["v"])
    w = int(spec.get("width", 7))
    d = int(spec.get("depth", 5))
    ceil = int(spec.get("height", 4))
    u_front, step, _facing = _shop_where(spec, p)
    dv, du = h.shape
    # **FROM THE FRONT FACE INWARD, NEVER ONE CELL IN FRONT OF IT.** Reserving k=-1 as well forces
    # mass into the trail-side verge - which is level ground by construction - and buries the
    # awning and the name board the shopfront hangs there. Measured, both shops shipped with
    # `signed: false`: `_Lot.sign` refuses a cell that is inside rock, so the failure was a
    # MISSING sign rather than a floating one, which is exactly why the count is returned.
    for v in range(v0 - 1, v0 + w + 1):
        for k in range(0, d + 2):
            u = u_front + step * k
            if 0 <= v < dv and 0 <= u < du:
                h[v, u] = max(h[v, u], ceil + 3)


def _shop(lot: _Lot, spec: dict, p: dict, seed: int) -> dict:
    """A shop CUT INTO a bank: a rock recess, a timber front on the trail, a counter and a sign.

    **INTEGRATED MEANS DUG IN, NOT STOOD NEXT TO.** A 7 x 6 hut on the lawn beside a spoil heap is
    an eighth false front; the same hut with rock over its lintel and banks either side of it is
    part of the landscape. So the recess is carved out of the height field's own mass and the only
    thing that projects is the shopfront.
    """
    v0 = int(spec["v"])
    w = int(spec.get("width", 7))
    d = int(spec.get("depth", 5))
    side = int(spec.get("side", 1))                 # +1 = the bank above the trail, -1 = below
    ceil = int(spec.get("height", 4))
    u_front, step, facing = _shop_where(spec, p)
    made = {"at": [v0, u_front], "side": side, "w": w, "d": d}

    # hollow the room (its cover was forced into the field by `_shop_reserve`)
    for v in range(v0, v0 + w):
        for k in range(0, d):
            u = u_front + step * k
            for y in range(1, ceil + 1):
                lot.c.put(v, y, u, 0)
            lot.put(v, 0, u, SHOP["plank"])
    # 3. line it, and frame the opening
    for v in range(v0 - 1, v0 + w + 1):
        for y in range(1, ceil + 1):
            if v in (v0 - 1, v0 + w):
                lot.log(v, y, u_front, SHOP["post"], axis="y")
    for v in range(v0 - 1, v0 + w + 1):
        lot.log(v, ceil + 1, u_front, SHOP["beam"], axis="x")
        lot.put(v, ceil + 2, u_front, SHOP["plank"])
    # the counter across the opening, and shutters over it
    for v in range(v0, v0 + w):
        lot.slab(v, 1, u_front, SHOP["counter"], "top")
        lot.put(v, ceil, u_front, SHOP["shutter"], facing=facing, half="top",
                open="true", powered="false", waterlogged="false")
    # a striped awning over the counter, on the trail side
    for i, v in enumerate(range(v0 - 1, v0 + w + 1)):
        u = u_front - step
        lot.put(v, ceil + 1, u, SHOP["canvas_a" if (i // 2) % 2 else "canvas_b"])
    # goods, light and a name
    for v in range(v0 + 1, v0 + w - 1, 2):
        lot.put(v, 1, u_front + step, SHOP["barrel"], facing="up", open="false")
        lot.hang(v, ceil - 1, u_front + step * 2)
    made["signed"] = bool(lot.sign(v0 + w // 2, ceil + 2, u_front - step, facing,
                                   list(spec.get("lines") or [spec.get("title", "SHOP")])[:4]))
    return made


# --------------------------------------------------------------------------- the workings


def _workings(lot: _Lot, h: np.ndarray, p: dict, seed: int) -> dict:
    """The props: a collared shaft under a windlass, timber cribbing, tipped ore, a pine or two.

    A PROP WITH A JOB, never a heap of vague blocks - the void tower's rule. A shaft has a collar,
    a windlass has a frame and a drum, cribbing is stacked timber holding a bank back.
    """
    hi = np.clip(np.floor(h + 0.5), 0, lot.c.sy - 1).astype(int)
    tally = {"shaft": 0, "crib": 0, "ore": 0, "pine": 0, "refused": 0}
    # **THE LANE IS STATED AND REFUSED**, which is the third time this land has needed the rule: a
    # timber set stood on the coaster's rail, an adit's cross-cut post bricked up its own corridor,
    # and two pines here went straight into the trail - twenty-four cells of trunk and canopy in
    # the one walk this whole module exists to carry. A prop sited by hand near a way will
    # eventually be sited IN it, so the way refuses rather than the hand remembering.
    tu0, tw = int(p["trail_u"]), int(p["trail_w"])
    verge = int(p.get("verge", 2))
    lane = set(range(tu0 - verge, tu0 + tw + verge))
    for spec in (p.get("workings") or []):
        v, u, kind = int(spec[0]), int(spec[1]), str(spec[2])
        reach = 2 if kind in ("shaft", "crib", "ore") else 2
        if any((u + k) in lane for k in range(-reach, reach + 1)):
            tally["refused"] += 1
            continue
        base = int(hi[v, u]) if 0 <= v < lot.dv and 0 <= u < lot.du else 0
        if kind == "shaft":
            # the collar: a fenced ring one course proud, with a lit hole in the middle
            for dv in (-1, 0, 1):
                for du in (-1, 0, 1):
                    if dv or du:
                        lot.put(v + dv, base, u + du, ROCK["rock_c"])
                        lot.fence(v + dv, base + 1, u + du, "u", key=SHOP["fence"])
            for y in range(max(0, base - 3), base):
                lot.c.put(v, y, u, 0)
            lot.put(v, max(0, base - 3), u, SHOP["glow"])
            # the windlass: two legs, a head beam, a drum and a chain into the hole
            for dv in (-2, 2):
                for y in range(base, base + 4):
                    lot.log(v + dv, y, u, SHOP["post"], axis="y")
            for dv in range(-2, 3):
                lot.log(v + dv, base + 4, u, SHOP["beam"], axis="x")
            lot.log(v, base + 3, u, SHOP["beam"], axis="x")
            lot.put(v, base + 2, u, SHOP["chain"], axis="y", waterlogged="false")
            tally["shaft"] += 1
        elif kind == "crib":
            # stacked timber holding a bank back: every course sits on the one under it
            for y in range(0, min(4, max(1, base))):
                for k in range(-2, 3):
                    a, b = (v + k, u) if y % 2 else (v, u + k)
                    lot.log(a, y, b, SHOP["post"], axis="x" if y % 2 else "z")
            tally["crib"] += 1
        elif kind == "ore":
            for dv in range(-2, 3):
                for du in range(-2, 3):
                    if abs(dv) + abs(du) > 2:
                        continue
                    key = "coal" if hash01(v + dv, u + du, seed + 9) < 0.4 else "scree"
                    lot.put(v + dv, base, u + du, ROCK[key])
            tally["ore"] += 1
        elif kind == "pine":
            hgt = 6 + int(hash01(v, u, seed + 11) * 3)
            for y in range(base, base + hgt):
                lot.put(v, y, u, SHOP["post"], axis="y")
            for k, r in ((hgt - 5, 2), (hgt - 4, 2), (hgt - 3, 1), (hgt - 2, 1), (hgt, 0)):
                for dv in range(-r, r + 1):
                    for du in range(-r, r + 1):
                        if dv * dv + du * du > r * r + r or (dv == 0 and du == 0 and k < hgt):
                            continue
                        lot.put(v + dv, base + k, u + du, "spruce_leaves",
                                persistent="true", distance="7", waterlogged="false")
            tally["pine"] += 1
    return tally


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DIGGINGS, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the diggings needs its measured lot: lot: [dv, du]")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    c = Canvas(dv, int(p.get("sy") or 28), du, donors)
    lot = _Lot(c, dv, du, seed=int(p.get("seed", 0)))
    seed = int(p.get("seed", 0))

    h = _field(p, dv, du)
    # ORDER IS THE WHOLE THING HERE: reserve, fill, then cut. The shops force their own cover into
    # the field BEFORE a cell is placed, so a recess is a room with rock over it rather than a bay
    # cut out of whatever the bank happened to give at that column.
    for spec in (p.get("shops") or []):
        _shop_reserve(h, spec, p)
    parts = {"mass": _fill(lot, h, seed)}
    parts["trail"] = _trail(lot, p, seed)
    parts["shops"] = [_shop(lot, spec, p, seed) for spec in (p.get("shops") or [])]
    parts["workings"] = _workings(lot, h, p, seed)

    av, ay, au = (int(v) for v in p["anchor"])
    at_v, at_u = (int(v) for v in (p.get("at") or (0, 0)))
    c.world_origin = (av + at_v, ay, au + at_u)
    c.meta = {
        "kind": "frontier_diggings",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "signs": lot.signs,
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "a worked-out landscape carrying the walk the old module carried: a three-wide trail "
            "dead straight west to east at the same courses, banks that rise AWAY from it and "
            "fall to the lot's own edges so neither cross avenue is walled, two shops cut into "
            "the banks with rock forced over them before anything is filled, and gravel only "
            "ever on a crust that is solid to the ground"),
    }
    return c
