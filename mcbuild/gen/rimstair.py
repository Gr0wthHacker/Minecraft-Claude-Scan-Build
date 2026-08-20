"""An open flight cut into the island's rim, descending to a court below it.

    rimstair: a straight stair on a cliff edge. One lane is CUT into the rock, the other is BUILT
              out into the air beside it, so the flight is two wide without either destroying the
              whole edge or standing on stilts in the middle of the court.

Why not a cased shaft. The sky-well court exists to get real daylight, and gen/stairwell drops a
stone tube through it: you arrive having seen nothing and a blind column stands in the light. The
descent here is the view - you come down the rim facing the owl lobe with the court opening up.

Three things this file gets right that cost measurement to find, all specific to a rim:

1. **The rim is not where the surface says it is.** A column scan says the edge stands at Y201, but
   at x-24222 that Y201 cell is a VINE hanging in open air - the rock stops one column east. Take
   the lane positions off the solid rock, never off a topmost-non-air scan, or the whole flight is
   built one column out into space.

2. **The outer lane's stringer rests on whatever it finds, and stops.** The court floor under this
   rim is Y194 in places and Y195 in others, with the court's own pool in between. Filling to a
   nominal floor either leaves a gap or drives a stone pier through the pond. It fills DOWN until it
   meets something solid - ice and water included, which are protected and are not replaced.

3. **The cut lane is a dig, and a litematic cannot express removal.** Every rock cell over a tread
   goes to the sidecar's dig list, which is what `/cscan dig` reads. Placing the tread without
   listing the cells above it builds a stair inside solid rock.

The tread convention is the one pinned in tests/test_stairhead.py: A FLIGHT THAT ASCENDS TOWARD D
HAS EVERY TREAD facing=D, half=bottom. Our renderer draws both directions identically, so getting
this from the geometry rather than by eye is the only way it is ever right.
"""
from __future__ import annotations

from . import protect
from .canvas import Canvas, hash01
from .vertical import Ctx, World

RIMSTAIR = {
    "under": None,
    "axis": "z",               # the flight runs along this axis; the other carries the two lanes
    "cut_lane": None,          # world coord on the lane axis: the lane CUT into the rock
    "air_lane": None,          # ... and the lane BUILT out into the air beside it
    "top": None,               # coord on `axis` of the top tread
    "bottom": None,            # ... and of the last tread. The sign gives the direction of descent
    "y_top": None,             # tread Y at `top`; each step descends one course
    "floor_y": None,           # court floor: the stringer never fills below this
    "tread": "stone_brick_stairs",
    "stringer": "stone_bricks",
    "trim": "deepslate_bricks",     # threshold and landing - the one real value contrast here
    "rail": "stone_brick_wall",
    "rail_side": True,              # railing on the open side of the air lane
    "weather": 0.16,
    "lantern_every": 3,
    "landing": 2,              # rows of platform past the last tread, on the court floor
    "landing_wide": 2,         # ... and how far it reaches out across the court skin
    "threshold": 2,            # cells of paving before the first tread, on the plate
    "headroom": 2,             # courses that must be clear over every tread (the cut lane's dig)
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air")
# Things a flight may be built straight through. A VINE is the one that matters: the rim's whole
# west face is a vine curtain hanging in open air, and `Ctx.name_at` reports it by name, so a
# "is this cell empty" test written as `name not in AIRY` reads the curtain as footing and every
# stringer stops dead at the top of the cliff. Rule 11: ask the registry, not the name.
PASSABLE = set(AIRY) | {"vine", "glow_lichen", "moss_carpet", "short_grass", "tall_grass", "fern"}


def _passable(ctx, x, y, z) -> bool:
    return ctx is None or ctx.name_at(x, y, z) in PASSABLE


def build_rimstair(cfg: dict, donors=None) -> Canvas:
    p = {**RIMSTAIR, **cfg}
    for k in ("cut_lane", "air_lane", "top", "bottom", "y_top", "floor_y"):
        if p.get(k) is None:
            raise ValueError("rimstair needs params.%s" % k)
    ctx = Ctx(p["under"]) if p.get("under") else None
    w = World()
    seed = int(p["seed"])
    axis = p["axis"]
    a0, a1 = int(p["top"]), int(p["bottom"])
    step = 1 if a1 > a0 else -1
    n = abs(a1 - a0) + 1
    y_top, floor_y = int(p["y_top"]), int(p["floor_y"])
    cut_l, air_l = int(p["cut_lane"]), int(p["air_lane"])

    # the flight DESCENDS along `step`, so it ASCENDS along -step. facing is the ascent direction.
    facing = _facing(axis, -step)
    out_dir = 1 if air_l > cut_l else -1        # from the rock toward open air

    def xz(a, lane):
        return (lane, a) if axis == "z" else (a, lane)

    dig, treads, rails, lit = [], 0, 0, 0
    used = 0
    for i in range(n):
        a = a0 + i * step
        ty = y_top - i
        if ty < floor_y:
            break
        used = i
        for lane in (cut_l, air_l):
            x, z = xz(a, lane)
            w.put(x, ty, z, p["tread"], facing=facing, half="bottom",
                  shape="straight", waterlogged="false")
            treads += 1
        # --- the cut lane: the tread cell AND everything over it come out -------------------------
        # The tread's own cell is rock too. Listing only the courses above it says the flight is
        # clear when the stair is still inside the cliff.
        x, z = xz(a, cut_l)
        if ctx is not None and not _passable(ctx, x, ty, z):
            dig.append((x, ty, z, ctx.name_at(x, ty, z)))
        dig.extend(_dig_column(ctx, x, z, ty + 1, int(p["headroom"])))
        # --- the air lane: a stringer down to whatever is really there ---------------------------
        x, z = xz(a, air_l)
        _stringer(ctx, w, x, z, ty - 1, floor_y, p, seed)
        # --- railing on the open side ------------------------------------------------------------
        if p.get("rail_side") and p.get("rail"):
            x, z = xz(a, air_l + out_dir)
            if _free(ctx, w, x, ty, z):
                w.put(x, ty, z, p["rail"], up="true", north="none", south="none",
                      east="none", west="none", waterlogged="false")
                rails += 1
            _stringer(ctx, w, x, z, ty - 1, floor_y, p, seed)
            if int(p["lantern_every"]) and i % int(p["lantern_every"]) == 0 and _free(ctx, w, x, ty + 1, z):
                w.put(x, ty + 1, z, "lantern", hanging="false", waterlogged="false")
                lit += 1

    # --- threshold on the plate and landing on the court floor -----------------------------------
    thr = _cap(ctx, w, xz, a0 - step, -step, int(p["threshold"]), y_top, (cut_l, air_l), p)
    a_end = a0 + used * step
    # the landing reaches OUT across the court's own skin, not just down the two lanes: the floor it
    # arrives on is Y194 in one column and Y195 in the next, so a two-cell cap leaves you stepping
    # off a stair into a hole. Levelling the patch is the landing's whole job.
    lanes = tuple(air_l + k * out_dir for k in range(-1, int(p["landing_wide"]) + 1))
    lnd = _cap(ctx, w, xz, a_end + step, step, int(p["landing"]),
               y_top - used - 1, lanes, p)

    return w.canvas({"kind": "rimstair", "treads": treads, "rails": rails, "lanterns": lit,
                     "threshold": thr, "landing": lnd, "facing": facing,
                     "dig": [list(d) for d in dig]})


def _dig_column(ctx, x, z, y0, headroom):
    """Rock standing over a tread. Stops at the first run of `headroom` clear courses - past that
    the flight is out in the open and there is nothing left to cut."""
    if ctx is None:
        return []
    out, clear = [], 0
    y = y0
    while clear < max(headroom, 1) and y < y0 + 40:
        nme = ctx.name_at(x, y, z)
        if nme in PASSABLE:
            clear += 1
        else:
            clear = 0
            out.append((x, y, z, nme))
        y += 1
    return out


def _stringer(ctx, w: World, x, z, y_from, floor_y, p, seed):
    """Fill DOWN from under a tread until it meets something solid, or the court floor."""
    for y in range(y_from, floor_y - 1, -1):
        if not _passable(ctx, x, y, z):
            return                                  # found its footing - pool and ice included
        if not w.has(x, y, z):
            w.put(x, y, z, _weathered(p["stringer"], x, y, z, float(p["weather"]), seed))


def _cap(ctx, w, xz, a_start, step, count, y, lanes, p) -> int:
    """Paving at either end, so the flight arrives somewhere rather than just stopping."""
    n = 0
    for k in range(max(count, 0)):
        a = a_start + k * step
        for lane in lanes:
            x, z = xz(a, lane)
            if w.has(x, y, z):
                continue
            if not _passable(ctx, x, y, z):
                continue                            # never pave over what is already standing
            w.put(x, y, z, p["trim"])
            n += 1
    return n


def _free(ctx, w: World, x, y, z) -> bool:
    if w.has(x, y, z):
        return False
    return _passable(ctx, x, y, z)


def _facing(axis: str, ascent: int) -> str:
    """north is -Z, south is +Z, east is +X, west is -X."""
    if axis == "z":
        return "south" if ascent > 0 else "north"
    return "east" if ascent > 0 else "west"


def _weathered(field: str, x, y, z, rate: float, seed: int) -> str:
    if rate <= 0:
        return field
    h = hash01(x, y, z, seed + 613)
    if h < rate * 0.6:
        return "mossy_stone_bricks"
    if h < rate:
        return "cracked_stone_bricks"
    return field
