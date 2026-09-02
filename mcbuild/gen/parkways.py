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
    "frontier": {"land": "frontier", "core": "stone_bricks", "inlay": "spruce_planks",
                 "border": "polished_blackstone_bricks", "accent": "cracked_stone_bricks",
                 "post": "spruce_fence", "light": "lantern", "seat": "spruce_stairs",
                 "plinth": "stone_brick_slab", "foot": "stone_bricks", "arm": "spruce_trapdoor"},
    "midway": {"land": "midway", "core": "smooth_stone", "inlay": "red_wool",
               "border": "polished_blackstone_bricks", "accent": "white_wool",
               "post": "oak_fence", "light": "lantern", "seat": "oak_stairs",
               "plinth": "stone_brick_slab", "foot": "smooth_stone", "arm": "oak_trapdoor"},
    "prismworks": {"land": "prismworks", "core": "polished_deepslate", "inlay": "cyan_wool",
                   "border": "deepslate_tiles", "accent": "light_blue_wool",
                   "post": "polished_blackstone_brick_wall", "light": "soul_lantern",
                   "seat": "spruce_stairs", "plinth": "polished_deepslate_slab",
                   "foot": "polished_deepslate", "arm": "dark_oak_trapdoor"},
}
LAWN, LAWN_TRIM = "moss_block", "moss_carpet"

PARKWAYS = {
    "bounds": [0, 0, 199, 599],   # V0..V199 by U0..U599 - the whole envelope
    "lands": None,                 # [{name, u0, u1}] in U order; the gaps between them are reaches
    #: A SET PIECE GETS A LOT, IT DOES NOT GET WHAT IS LEFT. Jack: "the air balloon is in the
    #: dead center of one of the walkways ... same with the bird" - because both were placed by a
    #: hand-typed offset that nothing checked against the paths. A reserved rectangle is kept
    #: clear of every path, plaza, lamp and bench, so a sculpture cannot land in a walkway.
    "feature_lots": None,          # [{name, v0, u0, v1, u1}]
    "spine_v": 14,                 # centre line of the grand spine
    "spine_half": 6,               # 13 wide overall
    "avenue_half": 4,              # 9 wide
    "avenue_every": 42,            # roughly one cross avenue per this much U inside a land
    "midwalk_v": 62,               # a mid-block walk, so a lot is not 84 deep
    "midwalk_half": 2,             # 5 wide
    "service_v": 158,              # the concealed service lane behind the observation band
    "service_half": 2,
    "rim_v": 170,                  # the protected rim's inner face
    "promenade_v": 110,            # the back promenade the avenues run to
    "promenade_half": 5,           # 11 wide
    "avenue_to": 132,              # how deep into the land an avenue runs
    "lamp_every": 22,
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
    c = Canvas(sx, 12, sz)
    seed = int(p["seed"])
    state: dict[str, int] = {}

    reserved = [(f["v0"] - v0, f["u0"] - u0, f["v1"] - v0, f["u1"] - u0)
                for f in (p.get("feature_lots") or [])]

    paved: set[tuple[int, int]] = set()

    def is_reserved(x: int, z: int) -> bool:
        return any(a <= x <= c and b <= z <= d for a, b, c, d in reserved)

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
        if not (0 <= x < sx and 0 <= z < sz) or is_reserved(x, z):
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
        paved.add((x, z))

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

    # A LOT 84 DEEP IS NOT A LOT. Audited, the blocks between the spine and the promenade came
    # out 84 x 33-79, and a building is twenty to fifty deep - so every block was one enormous
    # field with a street only at its two ends, which is how things end up packed against each
    # other in the middle. A mid-block walk halves them into two bands a building actually fits.
    mid_v = p["midwalk_v"] - v0
    for land in lands:
        for u in range(land["u0"], land["u1"] + 1):
            z = u - u0
            if not (0 <= z < sz):
                continue
            pal = LANDS[land["name"]]
            for d in range(-p["midwalk_half"], p["midwalk_half"] + 1):
                lay(mid_v + d, z, pal, pal, 0.0, p["midwalk_half"], abs(d), z)

    # THE SERVICE LANE, behind the observation band. The audit found V116-199 as ONE unbroken
    # lawn 84 x 600 - two fifths of the envelope with no route in it at all - and the concealed
    # service band is where staff reach the back of everything. Plainer paving on purpose: it is
    # meant to be missed, so it carries the border material and no inlay, and no lamps.
    svc_v = p["service_v"] - v0
    for z in range(sz):
        pal_a, pal_b, t = land_at(z + u0)
        for d in range(-p["service_half"], p["service_half"] + 1):
            x = svc_v + d
            if 0 <= x < sx and not is_reserved(x, z):
                c.put(x, 1, z, 0)
                c.put(x, 0, z, blk(paving(pal_a, pal_b, t, "border" if abs(d) == p["service_half"]
                                          else "accent", x, z)))
                paved.add((x, z))

    # THE RIM'S INNER FACE. V170-199 is protected reserve, and a park whose lawn simply runs out
    # into the void has no edge. One border course and a post rhythm is what says "the ground
    # stops here" without building a wall around the park.
    rim_v = p["rim_v"] - v0
    for z in range(sz):
        pal, _b, _t = land_at(z + u0)
        if 0 <= rim_v < sx and not is_reserved(rim_v, z):
            c.put(rim_v, 1, z, 0)
            c.put(rim_v, 0, z, blk(pal["border"]))
            if z % 6 == 0:
                c.put(rim_v, 1, z, blk(pal["post"]))
                c.put(rim_v, 2, z, blk(pal["post"]))

    avenues: list[tuple[int, dict]] = []
    for land in lands:
        span = land["u1"] - land["u0"] + 1
        count = max(2, span // p["avenue_every"])
        for i in range(count):
            avenues.append((land["u0"] + int(span * (i + 0.5) / count), LANDS[land["name"]]))
    deep = min(sx, svc_v + p["service_half"] + 1)
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
                if not (0 <= x < sx and 0 <= zz < sz) or is_reserved(x, zz):
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
                paved.add((x, zz))

    # ------------------------------------------------------------------ 4. furniture
    def _hang(x: int, y: int, z: int, light: str, drop: int = 1) -> None:
        """A light on a chain under a bracket. The bracket above must already be solid: a chain
        hangs from a block or from another chain, and an OPEN TRAPDOOR is neither - hanging them
        off one was 652 placement problems, one per chain."""
        for d in range(drop):
            c.put(x, y - d, z, c.raw_state("iron_chain", axis="y"))
        c.put(x, y - drop, z, c.raw_state(light, hanging="true"))

    def lamp_frontier(x: int, z: int, pal: dict, across: str) -> bool:
        """TWO STACKED LIGHTNING RODS AND A LANTERN ON TOP - Jack's design, on a stone plinth.

        A fence was wrong because A FENCE CONNECTS TO ITS NEIGHBOURS, so a mast with an arm read
        as a piece of railing. A lightning rod is the slimmest vertical block in the game and
        joins to nothing.

        THE PLINTH IS A FULL BLOCK, NOT A SLAB. A bottom slab's surface is halfway up its own
        cell, so the rod standing in the cell above it floated a half block clear with daylight
        under it - which is what "lightning rods are floating above the slabs" is. Anything a
        post stands on has to fill its cell.
        """
        c.put(x, 0, z, blk("stone_bricks"))
        c.put(x, 1, z, blk("chiseled_stone_bricks"))
        for y in (2, 3):
            c.put(x, y, z, c.raw_state("lightning_rod", facing="up", powered="false"))
        c.put(x, 4, z, c.raw_state(pal["light"], hanging="false"))
        return True

    def lamp_midway(x: int, z: int, pal: dict, across: str) -> bool:
        """A WROUGHT-IRON FAIRGROUND STANDARD: a striped plinth, an iron column, a capital.

        The three lands need three lamps, and this one was borrowing the Frontier's rods. The
        Midway is the bright social land, so its standard is the one from a promenade: a banded
        red-and-white base in the land's own paving colours, a slender iron column, and a small
        capital carrying the light. Slim - the shaft is `iron_bars` - but a different object.

        The capital is a TOP slab so the lantern sits on its surface rather than half a block
        above it, and so that a lantern is not asked to stand on bars, which is what put 104
        placement problems in the Prism lamp the first time round.
        """
        c.put(x, 0, z, blk("smooth_stone"))
        c.put(x, 1, z, blk(pal["inlay"]))          # the land's own red
        c.put(x, 2, z, blk(pal["accent"]))         # ...and its white, so the base is striped
        for y in (3, 4, 5):
            c.put(x, y, z, blk("iron_bars"))
        c.put(x, 6, z, c.raw_state("stone_brick_slab", type="top"))
        c.put(x, 7, z, c.raw_state(pal["light"], hanging="false"))
        return True

    def lamp_prismworks(x: int, z: int, pal: dict, across: str) -> bool:
        """A SIGNAL MAST: slim, dark, one cold light in a cage.

        Prismworks is the machine land and its light is a SIGNAL, not a mood - so the lamp is the
        thinnest thing on the park: a deepslate pad, a wall shaft (a wall renders as a slender
        post, not a block), and a single soul lantern caged in iron at head height with a rod
        above it. Nothing hangs, nothing is timber, and it reads as equipment.
        """
        c.put(x, 0, z, blk("polished_deepslate"))
        c.put(x, 1, z, blk("deepslate_tiles"))
        for y in (2, 3, 4, 5):
            c.put(x, y, z, blk("polished_blackstone_brick_wall"))
        # A LANTERN CANNOT STAND ON IRON BARS - 104 placement problems, one per Prism lamp. The
        # collar under the light is a solid block; the bars are a cage BESIDE it, which is what
        # bars are for and what makes a cold light read as caged equipment.
        c.put(x, 6, z, blk("deepslate_tiles"))
        c.put(x, 7, z, blk(pal["light"]))
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= x + dx < sx and 0 <= z + dz < sz:
                c.put(x + dx, 7, z + dz, blk("iron_bars"))
        c.put(x, 8, z, c.raw_state("end_rod", facing="up"))
        return True

    def _around(across: str):
        return [(-1, "west"), (1, "east")] if across == "x" else [(-1, "north"), (1, "south")]

    def _step(x: int, z: int, side: int, across: str):
        return (x + side, z) if across == "x" else (x, z + side)

    #: ONE LAMP PER LAND, NEVER ONE LAMP EVERYWHERE. Jack: "we cant copy and paste same lamp post
    #: across every single land, it needs to change based on the area." A land is told apart by
    #: what its street furniture is made of and shaped like as much as by its paving, and a lamp
    #: is the object a walker passes most often.
    LAMPS = {"frontier": lamp_frontier, "midway": lamp_midway, "prismworks": lamp_prismworks}

    def lamp(x: int, z: int, pal: dict, across: str) -> bool:
        """A LAMP STANDS ON LAWN, NEVER ON A PATH. Jack: "several areas have lamp posts on walk
        ways and in weird places" - the verge is two cells outboard of the spine's own border,
        but where an avenue, a plaza, the mid-block walk or the service lane crosses that line
        the cell is paving, and a post was going down in the middle of it. The mast's cell and
        both arm cells are checked; an arm may reach OVER a path, a post may not stand in one."""
        if not (0 <= x < sx and 0 <= z < sz) or is_reserved(x, z) or (x, z) in paved:
            return False   # counted by the caller: a refusal is a lamp that would have stood
                           # in a walkway, and the count is how the guard is checked at all -
                           # after the fact a lamp's own FOOTING has replaced the lawn under it,
                           # so nothing downstream can tell where it was placed from.
        return LAMPS[pal["land"]](x, z, pal, across)

    lamps = seats = refused = 0
    for z in range(sz):
        pal, _b, _t = land_at(z + u0)
        for side in (-1, 1):
            x = spine_v + side * (p["spine_half"] + 2)
            if not (0 <= x < sx):
                continue
            # ONE VERGE AT A TIME, ALTERNATING. Jack: "theres too many overall lamps, we dont
            # need hundreds to cover an area." A lamp on both verges every fourteen blocks is a
            # picket fence: 326 of them. Staggered at 22 the walk is still lit end to end - a
            # lantern is light 15, so the darkest point between two is about 5 - and the avenue
            # reads as an avenue rather than as a corridor of poles.
            if (z + (0 if side < 0 else p["lamp_every"] // 2)) % p["lamp_every"] == 0:
                # A REFUSAL LEAVES A HOLE IN THE RHYTHM, so a lamp that lands on paving is
                # NUDGED along the verge until it finds lawn rather than dropped: 41 of them
                # were being dropped outright, which is a dark gap wherever a path crosses.
                for shift in (0, 1, -1, 2, -2, 3, -3, 4, -4):
                    if lamp(x, z + shift, pal, "x"):
                        lamps += 1
                        break
                else:
                    refused += 1
            elif z % p["seat_every"] == p["seat_every"] // 2:
                for shift in (0, 1, -1, 2, -2):
                    zz = z + shift
                    if (0 <= zz < sz and not is_reserved(x, zz) and (x, zz) not in paved):
                        # a bench faces the path it is beside, which is why it is there at all
                        c.put(x, 1, zz, c.raw_state(pal["seat"],
                                                    facing="east" if side < 0 else "west",
                                                    half="bottom", shape="straight"))
                        seats += 1
                        break
    for u, pal in avenues:
        z = u - u0
        for i, x in enumerate(range(spine_v + half + 4, deep, p["lamp_every"])):
            for side in ((-1,) if i % 2 == 0 else (1,)):
                zz = z + side * (p["avenue_half"] + 2)
                if 0 <= zz < sz:
                    for shift in (0, 1, -1, 2, -2, 3, -3, 4, -4):
                        if lamp(x + shift, zz, pal, "z"):
                            lamps += 1
                            break
                    else:
                        refused += 1

    c.meta = {"kind": "parkways", "lands": [land["name"] for land in lands],
              "avenues": len(avenues), "lamps": lamps, "seats": seats,
              "lamps_refused_on_paving": refused,
              "feature_lots": [f["name"] for f in (p.get("feature_lots") or [])],
              "contract": "lawn, a path hierarchy of core/inlay/border/verge, furniture, and a "
                          "dithered transition through every reach - the ground layer, only"}
    return c


DEFAULTS = PARKWAYS
