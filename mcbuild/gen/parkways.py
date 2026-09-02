"""The park's ground layer: lawn, a path hierarchy, furniture, and graduated land transitions.

**STEP ONE, AND ON ITS OWN.** The park was previously paved edge to edge in one block - Jack:
"the street is all massive amounts of the same stone, no patterns, no actual pathways" - which is
a floor, not a layout. A path only reads as a path if there is something it is NOT. So the ground
is lawn, the paths are laid on it, and every path has a core, an inlay band, a border and a verge.

    lawn        moss, everywhere - cheap, spendable, and the thing a path reads against
    spine       the one route that runs all 600: core, inlay bands, dark border, planted verge
    avenue      cross routes into each land, narrower, the same grammar
    plaza       a widened patterned square where a spine and an avenue meet
    verge       lawn either side, carrying the lamp posts and the benches
    transition  a reach dithers one land's paving into the next over its own whole length

**THE TRANSITION IS THE POINT OF A REACH.** A hard line across a path reads as two paths butted
together; the Lowland Stair settled this on its own gradient - a per-cell hash dither over a band
is what makes one material BECOME another rather than stop. Here the band is the whole reach, so
a walker crosses from frontier timber-and-stone into midway smooth stone without seeing an edge.

Every block is cheap-or-ok tier, 1.19 and spendable. `grass_block` and `podzol` are CURRENCY on
this server, which is why the lawn is moss.
"""
from __future__ import annotations

from .canvas import Canvas, hash01

#: Per-land paving. `core` is what you walk on, `inlay`/`accent` are the pattern in it, `border`
#: draws its edge. Three lands that a walker can tell apart with their eyes shut.
LANDS = {
    "frontier": {"core": "stone_bricks", "inlay": "spruce_planks",
                 "border": "polished_blackstone_bricks", "accent": "cracked_stone_bricks",
                 "post": "spruce_fence", "light": "lantern", "seat": "spruce_stairs"},
    "midway": {"core": "smooth_stone", "inlay": "red_wool",
               "border": "polished_blackstone_bricks", "accent": "white_wool",
               "post": "oak_fence", "light": "lantern", "seat": "oak_stairs"},
    "prismworks": {"core": "polished_deepslate", "inlay": "cyan_wool",
                   "border": "deepslate_tiles", "accent": "light_blue_wool",
                   "post": "cobblestone_wall", "light": "soul_lantern", "seat": "spruce_stairs"},
}
LAWN, LAWN_TRIM = "moss_block", "moss_carpet"

PARKWAYS = {
    "bounds": [0, 0, 199, 599],   # V0..V199 by U0..U599 - the whole envelope
    "lands": None,                 # [{name, u0, u1}] in U order; the gaps between them are reaches
    "spine_v": 14,                 # centre line of the grand spine
    "spine_half": 6,               # 13 wide overall
    "avenue_half": 4,              # 9 wide
    "avenue_every": 42,            # roughly one cross avenue per this much U inside a land
    "promenade_v": 110,            # the back promenade the avenues run to
    "promenade_half": 5,           # 11 wide
    "avenue_to": 132,              # how deep into the land an avenue runs
    "lamp_every": 14,
    "seat_every": 18,
    "plaza_half": 13,
    "seed": 0,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PARKWAYS, **cfg}
    v0, u0, v1, u1 = p["bounds"]
    lands = p["lands"]
    if not lands:
        raise ValueError("parkways needs params.lands = [{name, u0, u1}, ...] in U order")
    for land in lands:
        if land["name"] not in LANDS:
            raise ValueError(f"unknown land {land['name']!r}; have {sorted(LANDS)}")
    sx, sz = v1 - v0 + 1, u1 - u0 + 1
    c = Canvas(sx, 8, sz)
    seed = int(p["seed"])
    state: dict[str, int] = {}

    def blk(name: str) -> int:
        if name not in state:
            state[name] = c.state(name)
        return state[name]

    def land_at(u: int):
        """(from-palette, to-palette, t) at a U. Inside a land t is 0; across a reach it ramps."""
        for land in lands:
            if land["u0"] <= u <= land["u1"]:
                pal = LANDS[land["name"]]
                return pal, pal, 0.0
        for a, b in zip(lands, lands[1:]):
            if a["u1"] < u < b["u0"]:
                t = (u - a["u1"]) / max(1, b["u0"] - a["u1"])
                return LANDS[a["name"]], LANDS[b["name"]], t
        pal = LANDS[lands[0]["name"]] if u < lands[0]["u0"] else LANDS[lands[-1]["name"]]
        return pal, pal, 0.0

    def paving(pal_a: dict, pal_b: dict, t: float, key: str, x: int, z: int) -> str:
        """One material, dithered across a reach. A hard line is two paths butted together."""
        return pal_b[key] if hash01(x, z, seed + 7) < t else pal_a[key]

    # ------------------------------------------------------------------ 1. the lawn
    for z in range(sz):
        for x in range(sx):
            c.put(x, 0, z, blk(LAWN))
            if hash01(x, z, seed + 3) < 0.05:
                c.put(x, 1, z, blk(LAWN_TRIM))

    # ------------------------------------------------------------------ 2. paths
    def lay(x: int, z: int, pal_a: dict, pal_b: dict, t: float, half: int, off: int, banding: int):
        """One cell of a path: border at the edge, an inlay band inside it, core in the middle."""
        if not (0 <= x < sx and 0 <= z < sz):
            return
        if off >= half:
            key = "border"
        elif off >= half - 2:
            key = "inlay" if (banding // 3) % 2 else "accent"
        else:
            key = "core"
        name = paving(pal_a, pal_b, t, key, x, z)
        c.put(x, 1, z, 0)            # the lawn trim never survives under paving
        c.put(x, 0, z, blk(name))

    spine_v = p["spine_v"] - v0
    for z in range(sz):
        pal_a, pal_b, t = land_at(z + u0)
        for d in range(-p["spine_half"], p["spine_half"] + 1):
            lay(spine_v + d, z, pal_a, pal_b, t, p["spine_half"], abs(d), z)

    # THE BACK PROMENADE. With only a spine and avenues the plan reads as a ladder: every cross
    # route runs one way into open lawn and stops, so there is no loop and no block of ground with
    # a street on both sides - which is where buildings go. A second promenade at the back of the
    # public floor turns the ladder into a network.
    prom_v = p["promenade_v"] - v0
    for z in range(sz):
        pal_a, pal_b, t = land_at(z + u0)
        for d in range(-p["promenade_half"], p["promenade_half"] + 1):
            lay(prom_v + d, z, pal_a, pal_b, t, p["promenade_half"], abs(d), z)

    avenues: list[tuple[int, dict]] = []
    for land in lands:
        span = land["u1"] - land["u0"] + 1
        count = max(2, span // p["avenue_every"])
        for i in range(count):
            avenues.append((land["u0"] + int(span * (i + 0.5) / count), LANDS[land["name"]]))
    deep = min(sx, prom_v + p["promenade_half"] + 1)
    for u, pal in avenues:
        z = u - u0
        for x in range(spine_v, deep):
            for d in range(-p["avenue_half"], p["avenue_half"] + 1):
                lay(x, z + d, pal, pal, 0.0, p["avenue_half"], abs(d), x)

    # ------------------------------------------------------------------ 3. plazas
    # a plaza at BOTH ends of every avenue: one on the arrival spine, one on the back promenade
    half = p["plaza_half"]
    for u, pal in avenues:
        z = u - u0
        for centre, hh in ((spine_v, half), (prom_v, half - 4)):
          for dx in range(-hh, hh + 1):
            for dz in range(-hh, hh + 1):
                x, zz = centre + dx, z + dz
                if not (0 <= x < sx and 0 <= zz < sz):
                    continue
                ring = max(abs(dx), abs(dz))
                if ring == hh:
                    key = "border"
                elif ring % 4 == 0:
                    key = "accent"
                elif (dx + dz) % 6 == 0:
                    key = "inlay"
                else:
                    key = "core"
                c.put(x, 1, zz, 0)
                c.put(x, 0, zz, blk(pal[key]))

    # ------------------------------------------------------------------ 4. furniture
    lamps = seats = 0
    for z in range(sz):
        pal, _b, _t = land_at(z + u0)
        for side in (-1, 1):
            x = spine_v + side * (p["spine_half"] + 2)
            if not (0 <= x < sx):
                continue
            if z % p["lamp_every"] == 0:
                for y in (1, 2, 3, 4):
                    c.put(x, y, z, blk(pal["post"]))
                c.put(x, 5, z, blk(pal["light"]))
                lamps += 1
            elif z % p["seat_every"] == p["seat_every"] // 2:
                # a bench faces the path it is beside, which is the whole reason it is there
                c.put(x, 1, z, c.raw_state(pal["seat"], facing="east" if side < 0 else "west",
                                           half="bottom", shape="straight"))
                seats += 1
    for u, pal in avenues:
        z = u - u0
        for x in range(spine_v + half + 4, deep, p["lamp_every"]):
            for side in (-1, 1):
                zz = z + side * (p["avenue_half"] + 2)
                if 0 <= zz < sz:
                    for y in (1, 2, 3, 4):
                        c.put(x, y, zz, blk(pal["post"]))
                    c.put(x, 5, zz, blk(pal["light"]))
                    lamps += 1

    c.meta = {"kind": "parkways", "lands": [land["name"] for land in lands],
              "avenues": len(avenues), "lamps": lamps, "seats": seats,
              "contract": "lawn, a path hierarchy of core/inlay/border/verge, furniture, and a "
                          "dithered transition through every reach - the ground layer, only"}
    return c


DEFAULTS = PARKWAYS
