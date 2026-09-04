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
    "frontier": {"land": "frontier", "glow": "ochre_froglight", "core": "stone_bricks", "inlay": "spruce_planks",
                 "border": "polished_blackstone_bricks", "accent": "cracked_stone_bricks",
                 "post": "spruce_fence", "light": "lantern", "seat": "spruce_stairs",
                 "plinth": "stone_brick_slab", "foot": "stone_bricks", "arm": "spruce_trapdoor"},
    "midway": {"land": "midway", "glow": "ochre_froglight", "core": "smooth_stone", "inlay": "red_wool",
               "border": "polished_blackstone_bricks", "accent": "white_wool",
               "post": "oak_fence", "light": "lantern", "seat": "oak_stairs",
               "plinth": "stone_brick_slab", "foot": "smooth_stone", "arm": "oak_trapdoor"},
    "prismworks": {"land": "prismworks", "glow": "pearlescent_froglight", "core": "polished_deepslate", "inlay": "cyan_wool",
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
    "avenue_half": 4,              # 9 wide, unless a land's own avenue names its own half
    "avenue_every": 42,            # FALLBACK ONLY: a uniform division, when a land names none
    "midwalk_v": None,             # FALLBACK ONLY: one mid-block walk at one depth in every land
    "midwalk_half": 2,
    "service_v": 155,              # the concealed service lane, at the FRONT of the service band
    "service_half": 1,             # 3 wide - a staff lane, not a street
    "rim_v": 170,                  # the protected rim's inner face
    #: [U] - a 3-wide walk from the service lane THROUGH the rim to a railway station, and a gap
    #: in the rim edge for it. Jack: "the access to the railways stairs are on the wrong side for
    #: us to actually access." He is right and it was worse than a side: the flight lands on the
    #: reserve lawn at V171, and between there and the service lane are FOURTEEN BLOCKS OF BARE
    #: GRASS with a post every six along the rim - no route at all, and the lane it eventually
    #: reaches is back-of-house. A station has to be entered from the park's own street.
    "rail_stations": None,
    #: [{v, u}] - an attraction's front door. A 3-wide apron carries it across its verge to the
    #: street it addresses, and stops the moment it reaches paving, so a spur is exactly as long
    #: as the gap and never one cell more.
    #:
    #: NO SPUR EXISTED ANYWHERE. The public lots begin at V24 and the spine's paving ends at V18,
    #: so V19-23 is designed verge and TEN attraction doors opened onto five courses of grass -
    #: walkable, because moss is walkable, and not a path. "Clear pathways" was Jack's own first
    #: instruction for this layer. Fifteen spurs are 165 cells.
    "spurs": None,
    #: THE BACK PROMENADE SITS ON THE SEAM, NOT IN THE MIDDLE OF THE PUBLIC FLOOR. At V110 it cut
    #: every 104-deep column into 81 and 12, so nothing over 81 deep had anywhere to stand - and
    #: five of the park's builds are deeper than that. On the public/exit seam at V124 it leaves
    #: the public floor 97 deep in one piece and the exit band its full programmed 24.
    "promenade_v": 124,
    "promenade_half": 3,           # 7 wide: spine 13 > avenue 9 > promenade 7, a real hierarchy
    #: A STRAIGHT ROAD AT ONE DEPTH CANNOT SERVE COLUMNS OF DIFFERENT DEPTHS. Control points
    #: [[u, v], ...] in world U; the centre is linearly interpolated between them, so the
    #: promenade swerves BEHIND a deep ride instead of being drawn through it.
    "promenade_curve": None,
    #: ...and where even a swerve has nowhere to go, the promenade simply stops. [[u0, u1], ...].
    #: The loop is closed by the avenues either side; you walk AROUND that block, not through it.
    "promenade_gaps": None,
    #: [{v0, u0, v1, u1}] - GROUND THAT KEEPS ITS PAVING AND LOSES ITS FURNITURE.
    #:
    #: A `feature_lot` is the wrong instrument for a vista: it refuses paving too, and the park's
    #: entrance walks on the spine's own stone. Measured off the shipped ground layer, two of the
    #: Midway's apron lamp masts stand squarely in the arrival walk - V4/U300 in the middle of the
    #: entry gate's nineteen-deep forecourt, and V20/U298 between the gate's back face and the
    #: Welcome Court's threshold - each of them a five-wide timber crossbeam at head height on the
    #: one sightline the whole park is composed about. Jack, arriving through it: *"gates and a
    #: board etc are all overlapping and chaotic with the entrance."*
    #:
    #: The mast at V4/U300 was DELIBERATE once and stopped being so without anything noticing: the
    #: gate composition used to stand at V3-V5 with the mast inside its portico as the gate's own
    #: lamp, and when the lot grew to nineteen courses to give Jack the walk-up he asked for, the
    #: mast stayed where it was and the gate moved twelve blocks away from it.
    "keep_clear": None,
    "lamp_every": 22,
    "seat_every": 18,
    "plaza_half": 13,
    #: A JUNCTION IS ROUND. A square plaza around a radial thing wastes its four corners and
    #: fights its shape; a disc gives those corners back to the lot as lawn. "round" | "square".
    #: A rasterised disc reads as a disc from r>=9 and as an octagon below it - see PARK_GRID_PLAN.
    "plaza_shape": "round",
    #: [{v, u, r, ring}] - an annular ring road with a lawn island inside it, for a centrepiece
    #: that is genuinely radial. The island is reserved ground exactly as a feature lot is.
    "roundabouts": None,
    #: A LAND BOUNDARY NEEDS A STREET. Measured, the Frontier's coaster column, the whole Claim
    #: Line reach and the Midway's arrival column came out as ONE 20,097-cell lot spanning two
    #: territories, because nothing at all crosses a reach except the spine. `[{at, half}]` -
    #: a cross path at a reach's own edge, laid in the dithered palette of the seam it stands on.
    #: PARK_FINAL_ARCHITECTED_PLAN calls these the "5-wide paved handoffs" (M8).
    "thresholds": None,
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

    # A ROUNDABOUT'S ISLAND IS A FEATURE LOT THAT HAPPENS TO BE ROUND. Reserved by the same rule,
    # so no path, plaza, lamp or bench can land on it - and so the ring road cannot pave its own
    # middle, which is the whole difference between a roundabout and a disc.
    islands = [(int(rb["v"]) - v0, int(rb["u"]) - u0, int(rb["r"]) - int(rb.get("ring", 5)))
               for rb in (p.get("roundabouts") or [])]

    #: The vistas: paved, and furnished by nobody. Held in the canvas' own lattice like `reserved`.
    keep_clear = [(int(k["v0"]) - v0, int(k["u0"]) - u0, int(k["v1"]) - v0, int(k["u1"]) - u0)
                  for k in (p.get("keep_clear") or [])]

    def is_keep_clear(x: int, z: int) -> bool:
        return any(a <= x <= c and b <= z <= d for a, b, c, d in keep_clear)

    def is_reserved(x: int, z: int) -> bool:
        if any(a <= x <= c and b <= z <= d for a, b, c, d in reserved):
            return True
        return any((x - ix) ** 2 + (z - iz) ** 2 < (r - 0.5) ** 2 for ix, iz, r in islands)

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
    #
    # ITS DEPTH IS A FUNCTION OF U, NOT A CONSTANT. Measured against the build inventory, no
    # single depth works: the Mine Coaster wants 111 deep of uninterrupted column and the exit
    # band wants its full 24, and a straight line cannot give both. The curve swerves behind the
    # deep ride; a gap says there is nowhere to swerve to and you walk round that block instead.
    curve = p.get("promenade_curve")
    gaps = [tuple(g) for g in (p.get("promenade_gaps") or [])]

    def prom_at(u: int) -> int:
        """The promenade's centre V at a world U, interpolated between control points."""
        if not curve:
            return p["promenade_v"]
        pts = sorted((int(a), int(b)) for a, b in curve)
        if u <= pts[0][0]:
            return pts[0][1]
        for (ua, va), (ub, vb) in zip(pts, pts[1:]):
            if ua <= u <= ub:
                return va if ub == ua else int(round(va + (vb - va) * (u - ua) / (ub - ua)))
        return pts[-1][1]

    def prom_open(u: int) -> bool:
        return not any(a <= u <= b for a, b in gaps)

    prom_half = p["promenade_half"]
    for z in range(sz):
        u = z + u0
        if not prom_open(u):
            continue
        pal_a, pal_b, t = land_at(u)
        cv = prom_at(u) - v0
        for d in range(-prom_half, prom_half + 1):
            lay(cv + d, z, pal_a, pal_b, t, prom_half, abs(d), z)

    # A LOT 84 DEEP IS NOT A LOT. Audited, the blocks between the spine and the promenade came
    # out 84 x 33-79, and a building is twenty to fifty deep - so every block was one enormous
    # field with a street only at its two ends, which is how things end up packed against each
    # other in the middle.
    #
    # BUT ONE WALK AT ONE DEPTH IN EVERY LAND IS THE SAME MISTAKE UPSIDE DOWN. At V62 it cut the
    # Mine Coaster's column, the Prism Ascent's and the Carousel/Sky Lift stack - the three
    # deepest things the park owns - clean in half. A cross walk belongs where a COLUMN's own
    # stack of builds meets, so it is declared per land as {v, u0, u1}, and a column carrying one
    # deep ride gets none at all.
    for land in lands:
        pal = LANDS[land["name"]]
        walks = land.get("walks")
        if walks is None and p.get("midwalk_v") is not None:
            walks = [{"v": p["midwalk_v"], "u0": land["u0"], "u1": land["u1"]}]
        for w in (walks or []):
            wh = int(w.get("half", p["midwalk_half"]))
            wv = int(w["v"]) - v0
            for u in range(max(land["u0"], int(w["u0"])), min(land["u1"], int(w["u1"])) + 1):
                z = u - u0
                if not (0 <= z < sz):
                    continue
                for d in range(-wh, wh + 1):
                    lay(wv + d, z, pal, pal, 0.0, wh, abs(d), z)

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
    # THE SPURS: every door carried across its verge to the street it addresses.
    #
    # DRAWN BEFORE THE LAMPS, AND THAT IS WHAT FIXES THE MASTS STANDING IN DOORWAYS. Three stood
    # at (20, 69), (20, 300) and (20, 496) - exactly on the spine's east verge at the mouth of
    # Boomtown Spine, Carousel Court and the Prism Array. Nothing had to be special-cased: a lamp
    # already refuses to stand on paving, so the spur simply has to exist first.
    #
    # A SPUR MAY BE AS WIDE AS THE DOOR IT SERVES, and until this it was three cells whatever
    # stood behind it. The Welcome Court's threshold is thirteen wide, on the same axis as the
    # entry gate's own portico - so a three-wide spur between them is a garden path laid across
    # the mouth of a triumphal arch. `half` is per entry and defaults to the old value, so every
    # spur that wanted three still gets three.
    spur_half = 1
    for sp in (p.get("spurs") or []):
        z = int(sp["u"]) - u0
        if not (0 <= z < sz):
            continue
        half = int(sp.get("half", spur_half))
        pal, _b, _t = land_at(int(sp["u"]))
        # walk back toward the street until paving is met - the gap decides the length, not a
        # number in a table that goes stale the moment a verge is retuned
        for x in range(int(sp["v"]) - v0 - 1, max(-1, int(sp["v"]) - v0 - 12), -1):
            if x < 0 or (x, z) in paved:
                break
            for d in range(-half, half + 1):
                lay(x, z + d, pal, pal, 0.0, half, abs(d), x)

    # THE STATION WALKS, and the gap in the rim they need. Drawn BEFORE the rim so the rim knows
    # to leave them alone: a post every six along a boundary is right everywhere except the one
    # cell somebody has to walk through, and a gate you have to jump is not a gate.
    rail_half = 1
    rail_u = {int(x) for x in (p.get("rail_stations") or [])}
    rail_cells = {(x, (ru - u0) + d)
                  for ru in rail_u for d in range(-rail_half, rail_half + 1)
                  for x in range(svc_v - p["service_half"], rim_v + 1)}
    for ru in sorted(rail_u):
        z = ru - u0
        if not (0 <= z < sz):
            continue
        pal, _b, _t = land_at(ru)
        # IT STOPS AT THE RIM AND NOT ONE CELL PAST IT. V171-199 is the protected reserve and the
        # rule holds for a station walk as much as for a lot; what is past the rim is the reserve's
        # own lawn, which is walkable, so the route loses nothing by ending here.
        for x in range(svc_v - p["service_half"], rim_v + 1):
            for d in range(-rail_half, rail_half + 1):
                lay(x, z + d, pal, pal, 0.0, rail_half, abs(d), x)

    for z in range(sz):
        pal, _b, _t = land_at(z + u0)
        if 0 <= rim_v < sx and not is_reserved(rim_v, z) and (rim_v, z) not in rail_cells:
            c.put(rim_v, 1, z, 0)
            c.put(rim_v, 0, z, blk(pal["border"]))
            if z % 6 == 0:
                c.put(rim_v, 1, z, blk(pal["post"]))
                c.put(rim_v, 2, z, blk(pal["post"]))

    # AN AVENUE IS A SEAM BETWEEN LOTS, NOT A TICK ON A RULER. Divided uniformly - four per land
    # every 42 - the avenues fell wherever the arithmetic put them and chopped the lawn into 34x31
    # tiles: a car park. The park's largest build is 111x71. So a land NAMES its own avenues, at
    # the boundaries between the columns its own programme needs, and `avenue_every` survives only
    # as the fallback for a land that has not been programmed yet.
    avenues: list[tuple[int, dict, int, int]] = []       # (u, palette, half, plaza half)
    for land in lands:
        pal = LANDS[land["name"]]
        declared = land.get("avenues")
        if declared:
            for a in declared:
                avenues.append((int(a["at"]), pal, int(a.get("half", p["avenue_half"])),
                                int(a.get("plaza", p["plaza_half"]))))
        else:
            span = land["u1"] - land["u0"] + 1
            count = max(2, span // p["avenue_every"])
            for i in range(count):
                avenues.append((land["u0"] + int(span * (i + 0.5) / count), pal,
                                p["avenue_half"], p["plaza_half"]))
    deep = min(sx, svc_v + p["service_half"] + 1)

    # THE HANDOFFS. A cross path at each reach's own edge, in the dithered seam palette so it
    # reads as belonging to neither land - which is what a threshold is.
    for th in (p.get("thresholds") or []):
        z = int(th["at"]) - u0
        th_half = int(th.get("half", 1))
        pal_a, pal_b, t = land_at(int(th["at"]))
        for x in range(spine_v, deep):
            for d in range(-th_half, th_half + 1):
                lay(x, z + d, pal_a, pal_b, t, th_half, abs(d), x)

    for u, pal, ah, _ph in avenues:
        z = u - u0
        for x in range(spine_v, deep):
            for d in range(-ah, ah + 1):
                lay(x, z + d, pal, pal, 0.0, ah, abs(d), x)

    # ------------------------------------------------------------------ 3. plazas
    round_plaza = str(p.get("plaza_shape", "round")).lower() == "round"

    def plaza_key(dx: int, dz: int, hh: int):
        """The pattern in a plaza, and None for a cell outside a round one."""
        if round_plaza:
            d = (dx * dx + dz * dz) ** 0.5
            if d > hh + 0.5:
                return None
            ring = int(round(d))
        else:
            ring = max(abs(dx), abs(dz))
        if ring >= hh:
            return "border"
        if ring % 4 == 0:
            return "accent"
        # A DIAGONAL INLAY IS ROTATIONALLY SYMMETRIC AND NOT MIRROR SYMMETRIC. `(dx + dz) % 6`
        # draws parallel diagonals running one way across the whole disc, so the plaza's two
        # halves do not match across either axis - 30 to 34 cells out on every square in the
        # park. On the absolute offsets it is a chevron, which is symmetric about both.
        return "inlay" if (abs(dx) + abs(dz)) % 6 == 0 else "core"

    def square(centre_x: int, z: int, pal: dict, hh: int):
        for dx in range(-hh, hh + 1):
            for dz in range(-hh, hh + 1):
                x, zz = centre_x + dx, z + dz
                if not (0 <= x < sx and 0 <= zz < sz) or is_reserved(x, zz):
                    continue
                key = plaza_key(dx, dz, hh)
                if key is None:
                    continue
                c.put(x, 1, zz, 0)
                c.put(x, 0, zz, blk(pal[key]))
                paved.add((x, zz))

    # a plaza at BOTH ends of every avenue: one on the arrival spine, one on the back promenade
    plaza_at: list[tuple[int, int, dict, int]] = []
    for u, pal, _ah, ph in avenues:
        z = u - u0
        square(spine_v, z, pal, ph)
        plaza_at.append((spine_v, z, pal, ph))
        # THE PROMENADE'S JUNCTION IS THE AVENUE CROSSING ITSELF, AND NOTHING IS DRAWN FOR IT.
        # A widened head there was worth 5 froglights and cost real lots: at r9 it reached four
        # courses into the band on either side, and at r5 it still spilled three cells past the
        # last avenue into the column beyond - which on this park is always a GAPPED column, i.e.
        # the Mine Coaster, the Sky Lift and the Resonance Vault, the three builds with no slack
        # anywhere. Measured, that alone put all three of them fourteen to thirty-one courses
        # short. A square two cells wider than its own street was never a square anyway; the
        # crossing is lit from underfoot like every other junction, and takes no ground at all.
        if prom_open(u):
            plaza_at.append((prom_at(u) - v0, z, pal, prom_half))

    # ------------------------------------------------------------------ 3b. roundabouts
    # A RING ROAD ROUND A GREEN ISLAND, where the centrepiece is genuinely radial. The island is
    # left as lawn and reserved, so no path, lamp or bench can land on it - the same guard a
    # feature lot gets, because it is one.
    for rb in (p.get("roundabouts") or []):
        cx, cz = int(rb["v"]) - v0, int(rb["u"]) - u0
        r_out, ring = int(rb["r"]), int(rb.get("ring", 5))
        r_in = r_out - ring
        pal = LANDS[rb["land"]] if rb.get("land") in LANDS else land_at(cz + u0)[0]
        for dx in range(-r_out, r_out + 1):
            for dz in range(-r_out, r_out + 1):
                x, zz = cx + dx, cz + dz
                if not (0 <= x < sx and 0 <= zz < sz) or is_reserved(x, zz):
                    continue
                d = (dx * dx + dz * dz) ** 0.5
                if not (r_in - 0.5 <= d <= r_out + 0.5):
                    continue
                rr = int(round(d))
                key = "border" if rr in (r_in, r_out) else \
                      ("accent" if rr % 3 == 0 else
                       ("inlay" if (abs(dx) + abs(dz)) % 5 == 0 else "core"))
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
        """A TIMBER CROSSBEAM LAMP: stone plinth, fence shaft, a SLAB beam, a chain, a lantern.

        Jack: "you made it with 5 solid oak blocks, and slabs on top of them, we only need the
        slabs with 1 chain where the oak connects to the lamp." Right - the beam is the slab
        course and nothing under it. A doubled beam is twice the timber for a silhouette a slab
        already gives, and it made the head heavy.

        A BOTTOM SLAB'S BOTTOM FACE IS SOLID, which is why the chain can hang from it and why the
        beam is `type=bottom`: a top slab would leave the chain hanging off the ceiling of its own
        cell with a gap under the beam. Then one chain, then the lantern - the same rule that
        broke the trapdoor version, applied in the one direction it works.
        """
        c.put(x, 0, z, blk("smooth_stone"))
        c.put(x, 1, z, blk("chiseled_stone_bricks"))
        for y in (2, 3, 4, 5):
            c.put(x, y, z, blk("dark_oak_fence"))
        c.put(x, 6, z, c.raw_state("dark_oak_slab", type="bottom"))
        for side, _facing in _around(across):
            for step in (1, 2):
                ax, az = _step(x, z, side * step, across)
                if not (0 <= ax < sx and 0 <= az < sz):
                    continue
                c.put(ax, 6, az, c.raw_state("dark_oak_slab", type="bottom"))
                if step == 2:
                    c.put(ax, 5, az, c.raw_state("iron_chain", axis="y"))
                    c.put(ax, 4, az, c.raw_state(pal["light"], hanging="true"))
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
        # A MAST'S ARMS REACH TWO CELLS EITHER SIDE OF IT, so a vista is cleared by testing the
        # WHOLE FIVE-CELL SPREAD against the reserve and not just the post. Tested at the post
        # alone, a mast one cell outside a nine-wide walk still hangs a lantern in the middle of
        # it - which is exactly how the second of these two came to stand where it does.
        if any(is_keep_clear(*_step(x, z, side, across)) for side in (-2, -1, 0, 1, 2)):
            return False
        if not (0 <= x < sx and 0 <= z < sz) or is_reserved(x, z) or (x, z) in paved:
            return False   # counted by the caller: a refusal is a lamp that would have stood
                           # in a walkway, and the count is how the guard is checked at all -
                           # after the fact a lamp's own FOOTING has replaced the lawn under it,
                           # so nothing downstream can tell where it was placed from.
        return LAMPS[pal["land"]](x, z, pal, across)

    lamps = glows = refused = 0
    lamp_at: list[tuple[int, int]] = []
    per_line: dict[int, int] = {}

    #: A LAMP MAY MOVE ALONG ITS OWN LINE AND NEVER ACROSS IT. Jack, on the shipped version:
    #: "still lots of issues with lamp placements, awkward, weird" - and counted off the block
    #: list the masts stood on FOURTEEN different V lines, with thirteen piled on one of them and
    #: ten on another. A street lamp sits on one line per verge; that is the whole of what makes a
    #: row of them read as a row. The nudge below runs along the street's own direction only, so
    #: the line a lamp is on is decided by the caller and cannot be changed by the search.
    #:
    #: SPINE AND PROMENADE need a long window because a plaza swallows their verge for its whole
    #: 23-block length; at a three-block nudge the spine's east verge came out with a 110-block
    #: hole, which is an accident rather than restraint.
    WINDOW_LONG = (0, 2, -2, 4, -4, 6, -6, 8, -8, 10, -10, 12, -12, 14, -14)
    #: AN AVENUE'S WINDOW IS CAPPED AT HALF ITS OWN RHYTHM. Its lamps step down the avenue at
    #: `lamp_every`, so a nudge longer than half that step lands a lamp nearer its NEIGHBOUR'S
    #: station than its own - which is exactly how thirteen of them ended up stacked on one line.
    WINDOW_SHORT = tuple(s for k in range(0, p["lamp_every"] // 2 - 2, 2) for s in ((k,) if not k else (k, -k)))

    #: TWELVE, NOT EIGHT. Eight is the anti-bunching minimum - the closest two street lamps ever
    #: get - and anything allowed to sit at exactly that distance from a junction lamp reads as a
    #: fifth corner rather than as the first post of a run.
    JUNCTION_CLEAR = 12
    junction_at: list = []

    def near_junction(x: int, z: int) -> bool:
        return any(abs(px - x) + abs(pz - z) < JUNCTION_CLEAR for px, pz in junction_at)

    def place_lamp(x: int, z: int, pal: dict, across: str, window=WINDOW_LONG) -> bool:
        """One lamp, nudged ALONG its own verge line until it clears paving - or dropped.

        A MISSING LAMP IS INVISIBLE; A LAMP THIRTEEN BLOCKS OFF ITS LINE IS NOT. Past the window
        it is refused rather than relocated, and the refusal is counted, because after the fact a
        lamp's own FOOTING has replaced the lawn under it and nothing downstream can tell where
        it was placed from."""
        nonlocal lamps, refused
        for shift in window:
            sx_, sz_ = (x, z + shift) if across == "x" else (x + shift, z)
            # A NUDGE MUST NOT BUNCH. Two lamps pushed off the same plaza from opposite verges
            # landed one and two blocks apart - a pair of posts side by side, which reads worse
            # than the gap it was avoiding. Eight is about the closest two street lamps ever get.
            if any(abs(px - sx_) + abs(pz - sz_) < 8 for px, pz in lamp_at):
                continue
            # AND THE NUDGE MUST RESPECT A CROSSING TOO. Blocking the intended cell but not the
            # ones it can be walked to is no guard at all: the promenade run near the Midway's
            # second avenue was pushed to eight blocks off that junction's own mast, which reads
            # as a fifth corner and broke the symmetry of the one junction that was already
            # right. Junction lamps themselves pass, or none of them could ever be laid.
            if window != (0,) and near_junction(sx_, sz_):
                continue
            if lamp(sx_, sz_, pal, across):
                lamps += 1
                lamp_at.append((sx_, sz_))
                per_line[sx_ + v0] = per_line.get(sx_ + v0, 0) + 1
                return True
        refused += 1
        return False

    # ------------------------------------------------------------ a junction lights ITSELF
    #
    # Jack, on the shipped park: "lots of lamp placements around intersections are still weird,
    # non symmetric." Measured against the build, every single crossing was asymmetric and five
    # of the six avenue/spine junctions carried NO LAMP AT ALL:
    #
    #     frontier  U43   spine none          promenade  left [(-4,3)]        right [(8,3)]
    #     midway    U260  spine left only     promenade  left [(2,8),(6,8)]   right [(8,2),(8,6)]
    #     midway    U341  spine none          promenade  left none            right four
    #
    # **A RHYTHM WALKED DOWN A LINE CANNOT KNOW A CROSSING IS THERE.** `(z + phase) % every == 0`
    # lands wherever the counter happens to be when it passes an avenue, so a junction gets
    # nought, one, two or four lamps at arbitrary offsets - and whatever it gets is symmetric
    # only by luck. Nothing about that is fixable by tuning the phase, because one phase serves
    # six hundred blocks and twelve junctions at once.
    #
    # So the junctions are lit FIRST, and by construction: four lamps at the points where the two
    # streets' own verge lines cross, pushed out along the crossing street by ONE offset shared by
    # all four - so a junction is symmetric about both its axes or it has no lamps at all. The
    # offset is PROBED rather than computed, because the thing it has to clear is a round plaza
    # and the arithmetic for "where does a disc of radius r stop covering the line at depth d"
    # is exactly the sort of thing that is right until someone changes the plaza shape.
    def junction(cv: int, halfw: int, cz: int, pal: dict, u_ok=None, v_sides=(-1, 1)) -> int:
        dv = halfw + 2                       # the street's own verge line, both sides
        for du in range(halfw + 2, halfw + 26):
            # A CROSSING'S CORNERS MUST BE ON THE STREET THAT CROSSES. The promenade stops dead
            # at three ride columns, and Frontier's second avenue meets it four blocks before the
            # first of those - so two corners landed PAST the end of the promenade, on ground
            # that belongs to the Mine Coaster, and cost the largest lot in the park fourteen of
            # its depth. A lamp is a single cell and it still moved a 111-block ride out of its
            # own lot: on this park the verges are the whole margin.
            # A T-JUNCTION IS NOT A FAILED CROSSING. The promenade dies at three ride columns
            # and the avenues ARE the column seams, so five of its six meetings have street on
            # one side only - and demanding four corners there lit none of them at all. What must
            # hold everywhere is the symmetry you actually see, which is ACROSS the street; along
            # it there is simply nothing on the far side to match.
            sides = [su for su in (-1, 1) if u_ok is None or u_ok(cz + su * du + u0)]
            if not sides:
                return 0
            pts = [(cv + sv * dv, cz + su * du) for sv in v_sides for su in sides]
            if not all(0 <= x < sx and 0 <= z_ < sz and (x, z_) not in paved
                       and not is_reserved(x, z_) for x, z_ in pts):
                continue
            # AND A JUNCTION THAT WOULD CROWD ANOTHER IS NOT ONE. The Circus sits 25 blocks from
            # the Midway's second avenue and its ring reaches within 8 of that avenue's own
            # promenade junction - so lighting both put two quartets a walking-pace apart and
            # broke the symmetry of the one that was already right. The bigger feature is offered
            # first (avenues, then thresholds, then roundabouts) and a later one stands down.
            if any(near_junction(x, z_) for x, z_ in pts):
                return 0
            if not all(place_lamp(x, z_, pal, "x", (0,)) for x, z_ in pts):
                return 0                     # a partial set is worse than none: see below
            junction_at.extend(pts)
            return du
        return 0

    # WHERE FOUR WILL NOT STAND, NONE DO. A junction with three lamps reads as one with a lamp
    # missing, which is precisely the complaint; a junction with none reads as a crossing lit from
    # its own floor, which is what the plaza froglights are for.
    for u, pal, ah, ph in avenues:
        z = u - u0
        junction(spine_v, p["spine_half"], z, pal)
        if prom_open(u):
            junction(prom_at(u) - v0, prom_half, z, pal, prom_open)

    # A THRESHOLD IS A STREET, AND THE JUNCTION PASS COULD NOT SEE ONE. It walks the `avenues`
    # list, and the four reach handoffs at U171/213/386/428 are not in it - so four real 3-wide
    # streets, each running from the spine to the service lane, crossed both the spine's verge and
    # the promenade with whatever the runs happened to leave: one mast at -3, a pair at -14/+8,
    # nothing at all at U171. Not one matched pair among the eight.
    #
    # A THRESHOLD LEAVES THE SPINE; IT DOES NOT CROSS IT. It starts at the spine's own centre
    # line, so there is no northern quadrant to mirror and its spine junction is a PAIR on the
    # south verge rather than a quartet - written as a crossing it would have asked for two masts
    # in the middle of the spine's own paving.
    for th in (p.get("thresholds") or []):
        tu = int(th["at"])
        z = tu - u0
        if not (0 <= z < sz):
            continue
        tpal = land_at(tu)[0]
        junction(spine_v, p["spine_half"], z, tpal, v_sides=(1,))
        if prom_open(tu):
            junction(prom_at(tu) - v0, prom_half, z, tpal, prom_open)

    # ...and so is the circus. Its ring road meets the promenade on both sides and the east half
    # of it was dark - two masts, both west, because the runs alternate and nothing knew a
    # roundabout was there either.
    for rb in (p.get("roundabouts") or []):
        ru = int(rb["u"])
        z = ru - u0
        if 0 <= z < sz:
            junction(int(rb["v"]) - v0, prom_half, z, land_at(ru)[0], prom_open)

    # A RUN IS SPACED BETWEEN ITS CROSSINGS, NOT ON A PHASE THAT SERVES SIX HUNDRED BLOCKS.
    # With the corners right, what was still asymmetric was the NEXT lamp along: `(z + phase) %
    # every == 0` has no idea a junction is there, so standing at a crossing the next post was
    # eighteen blocks one way and twenty-six the other, at every junction in the park and by a
    # different amount at each. That is what "weird, non symmetric" looks like from the ground.
    #
    # So each verge line is cut at its own junction lamps and each piece is filled EVENLY. The
    # count comes from the desired rhythm and the spacing from the piece, so a lamp is never more
    # than a few blocks off `lamp_every` and the first post after a crossing is the same distance
    # on both sides of it by construction. The domain's own ends act as anchors too, so a run
    # that starts at a land boundary is spaced from it rather than from wherever the phase fell.
    def spaced(z0: int, z1: int, anchors, every: int) -> list:
        """The stations along one run of street, cut at its own crossings.

        ONE RULE FOR EVERY STREET IN THE PARK. The spine and the promenade run along U and an
        avenue runs along V, and they were spaced by two different pieces of arithmetic - which
        is how the avenues ended up alternating east/west down their length and then losing a
        station to the anti-bunching guard, leaving V95 and V139 both on the WEST flank with 44
        blocks and nothing at all on the east. Worse, it fired on three of the six avenues and
        not the other three, so no two of them lit the same way.
        """
        out = []
        # AN ANCHOR OUTSIDE THE RUN STILL ANCHORS IT. An avenue begins at the spine's verge and
        # the lamps only start eleven blocks further down, past the plaza - so the crossing that
        # ought to pin the first setback sits BEFORE the run and was being dropped, leaving the
        # avenue's first post wherever an even fill from the plaza rim happened to land.
        js = sorted(set(anchors))
        stops = sorted({min([z0 - 1] + js), max([z1 + 1] + js)} | set(js))
        jset = set(js)
        for a, b in zip(stops, stops[1:]):
                # THE SETBACK FROM A CROSSING IS FIXED; ONLY THE MIDDLE STRETCHES. Filling the
                # whole piece evenly still left the first post 26 one way and 27 the other,
                # because the runs either side of a junction are different lengths - a rounding
                # difference, but it is exactly the thing you notice standing in the crossing
                # looking both ways. Pinned, the first lamp is `lamp_every` from the junction on
                # every approach in the park and the slack is spent mid-run where nobody stands
                # comparing.
                ja, jb = a in jset, b in jset
                if ja and jb and b - a < every:
                    # NOT A RUN AT ALL. Two anchors closer together than one step are the two
                    # masts of a SINGLE junction, and the midpoint between them is the middle of
                    # that crossing. It put a lamp on the spine's west verge exactly opposite the
                    # mouth of every threshold - facing a pair on the east verge, on a street
                    # that does not continue north, which is the asymmetry read from the crossing.
                    continue
                if ja and jb and b - a < 3 * every:
                    # TOO SHORT FOR TWO SETBACKS, so it gets ONE lamp equidistant from both
                    # crossings - which is still symmetric, and is what the pinned setback
                    # cannot be here. Frontier's promenade runs 53 blocks between junctions
                    # against a rhythm of 28: pinned from both ends the two posts landed three
                    # apart, the anti-bunching guard dropped whichever came second, and the run
                    # came out as an 8-9-8 clump - denser than the rhythm it was meant to keep.
                    out.append((a + b) // 2)
                    continue
                lo = a + every if ja else a + 1
                hi = b - every if jb else b - 1
                if hi < lo:
                    continue
                if ja:
                    out.append(lo)
                if jb and hi != lo:
                    out.append(hi)
                n = max(0, int(round((hi - lo) / every)) - 1)
                for i in range(n):
                    out.append(lo + int(round((hi - lo) * (i + 1) / (n + 1))))
        return [z for z in sorted(set(out)) if z0 <= z <= z1]

    def run(vline: int, spans, every: int, mates=()) -> None:
        # A STREET'S TWO VERGES ARE SPACED FROM THE SAME CROSSINGS. A threshold leaves the spine
        # southward, so it lights the south verge only - and spacing each verge from its own
        # lamps then pinned one run and not the other, and the two rows came apart. The anchors
        # are the crossings of the STREET, whichever verge happens to carry their masts.
        lines = set(mates) | {vline}
        anchors = [pz for px, pz in junction_at if px in lines]
        for z0, z1 in spans:
            for z in spaced(z0, z1, anchors, every):
                if 0 <= z < sz and not near_junction(vline, z):
                    place_lamp(vline, z, land_at(z + u0)[0], "x")

    prom_v = {prom_at(z + u0) for z in range(sz) if prom_open(z + u0)}
    spans_prom, open_run = [], None
    for z in range(sz + 1):
        opened = z < sz and prom_open(z + u0)
        if opened and open_run is None:
            open_run = z
        elif not opened and open_run is not None:
            spans_prom.append((open_run, z - 1)); open_run = None
    sp_lines = (spine_v - p["spine_half"] - 2, spine_v + p["spine_half"] + 2)
    for side in (-1, 1):
        run(spine_v + side * (p["spine_half"] + 2), [(0, sz - 1)], p["lamp_every"], sp_lines)
        # A CURVED PROMENADE HAS NO ONE VERGE LINE, so it keeps the old per-cell rhythm. It is
        # switched off in the shipped park (a swerve has to ramp somewhere and every place the
        # ramp could go is spoken for), and this is the branch that says so rather than silently
        # spacing a curve against a line it does not have.
        if len(prom_v) == 1:
            pc = next(iter(prom_v)) - v0
            run(pc + side * (prom_half + 2), spans_prom, p["lamp_every"] + 6,
                (pc - prom_half - 2, pc + prom_half + 2))
    # THE CROSS WALKS WERE COMPLETELY UNLIT, and they are the entire street access for three
    # attractions - the Snack Window, the Prize Point and the Resonance Vault. Measured, not one
    # mast stood within two cells of any of the three. They are streets and they are lit like
    # streets, from their own verges, spaced from their own ends.
    for land in lands:
        wpal = LANDS[land["name"]]
        for wk in (land.get("walks") or []):
            if not wk.get("lit", True):
                continue                     # a column with no slack has no room for a verge post
            wv, wh = int(wk["v"]) - v0, int(wk.get("half", 1))
            wz0, wz1 = int(wk["u0"]) - u0, int(wk["u1"]) - u0
            for side in (-1, 1):
                # ONE CELL OF VERGE, NOT TWO - the rule an avenue already follows, for the reason
                # this park keeps re-teaching. At two the walk's mast stood on V71 and Arrival
                # Court, whose lot is V24-71, measured a course short. A walk runs between two
                # lots and the single cell between it and each of them is all the verge there is.
                vline = wv + side * (wh + 1)
                # A WALK IS SHORT AND NARROW AND TAKES A CLOSER RHYTHM. At the spine's own 22 a
                # forty-block walk gets ONE post a side, which is a lamp rather than a lit street.
                for z in spaced(wz0, wz1, [], max(8, p["lamp_every"] - 8)):
                    if 0 <= z < sz and not near_junction(vline, z):
                        place_lamp(vline, z, wpal, "x")

    if len(prom_v) != 1:
        for z in range(sz):
            u = z + u0
            if not prom_open(u):
                continue
            every = p["lamp_every"] + 6
            for side in (-1, 1):
                if (z + (0 if side < 0 else every // 2)) % every == 0:
                    v = prom_at(u) - v0 + side * (prom_half + 2)
                    if not near_junction(v, z):
                        place_lamp(v, z, land_at(u)[0], "x")

    for u, pal, ah, ph in avenues:
        z = u - u0
        # AN AVENUE'S OWN RHYTHM STOPS SHORT OF ITS CROSSINGS TOO. Without this the junction
        # lamps trip the anti-bunching guard and the avenue's next post is NUDGED - which put six
        # of them on V113 and V115, two lines that exist nowhere else in the park. A lamp dropped
        # beside a lit crossing is invisible; a lamp four blocks off its own rhythm is not.
        # THE SPINE'S ANCHOR IS ITS VERGE, NOT ITS CENTRE. An avenue crosses the promenade, so
        # that junction is pinned from the middle; it LEAVES the spine, so the setback is
        # measured from the edge the walk actually starts at.
        anchors = ([spine_v + p["spine_half"] + 2]
                   + ([prom_at(u) - v0] if prom_open(u) else []))
        stations = spaced(spine_v + ph + 6, deep - 2, anchors, p["lamp_every"])
        for k, x in enumerate(stations):
            # ALTERNATE BY POSITION IN THE RUN, NOT BY THE COORDINATE. Keyed on `x // every` the
            # side flips with the coordinate, so a station dropped anywhere leaves two neighbours
            # on the same flank - V95 and V139 both west, 44 apart, with nothing on the east side
            # of the avenue's back half. It fired on three of the six avenues and not the other
            # three, so no two of them lit the same way. Keyed on the INDEX the alternation
            # survives whatever the spacing does.
            # (the short window: an avenue lamp may not wander into the next station's stretch)
            for side in ((-1,) if k % 2 == 0 else (1,)):
                if not near_junction(x, z + side * (ah + 1)):
                    # ONE CELL OF VERGE, NOT TWO. A lamp two cells out from an avenue's
                    # border stands INSIDE the building lot behind it, and measured against the
                    # inventory that cost four blocks of usable width on every column - enough,
                    # on its own, to put the Mine Coaster's 71-wide lot one block short. The
                    # spine and the promenade have designed verges (V19-23, V120/V130) and keep
                    # their two; an avenue runs between two lots and gets one.
                    place_lamp(x, z + side * (ah + 1), pal, "z", WINDOW_SHORT)

    # ...and the squares themselves: a FEW froglights set flush in the paving. Flush, because a
    # froglight IS the floor - an opaque emitter a course down - so it reaches one less than its
    # own light and takes no room at all. Five to a plaza, on the pattern rather than scattered.
    for centre, z, pal, hh in plaza_at:
        step = max(3, hh - 5)
        for dx, dz in ((0, 0), (-step, -step), (step, -step), (-step, step), (step, step)):
            px, pz = centre + dx, z + dz
            if 0 <= px < sx and 0 <= pz < sz and not is_reserved(px, pz) and (px, pz) in paved:
                c.put(px, 0, pz, blk(pal["glow"]))
                glows += 1

    c.meta = {"kind": "parkways", "lands": [land["name"] for land in lands],
              "avenues": len(avenues), "lamps": lamps, "square_glows": glows,
              "lamps_refused_on_paving": refused,
              # THE LINES THE MASTS ACTUALLY STAND ON, so the thing Jack looked at and called
              # "awkward, weird" is a number in the sidecar rather than something you must
              # count off a block list. `render3d` draws a rod, a fence, a wall and iron bars
              # all as full cubes, so a picture cannot answer this.
              "lamps_per_line": dict(sorted(per_line.items())),
              "feature_lots": [f["name"] for f in (p.get("feature_lots") or [])],
              "contract": "lawn, a path hierarchy of core/inlay/border/verge, furniture, and a "
                          "dithered transition through every reach - the ground layer, only"}
    return c


def avenue_stations(params: dict) -> list:
    """The V depths an avenue's lamps stand at, for whoever needs to CHECK them.

    ONE SOURCE. `tools/park_lamps.py` had this as `range(start, service_v, lamp_every)`, which was
    right only while an avenue was spaced by a bare step; the moment the runs were cut at their
    crossings the tool called every correctly-placed avenue lamp "OFF EVERY LINE". This is the
    same arithmetic the build uses, run without building anything.
    """
    p = {**PARKWAYS, **params}
    sv, sh, ph = p["spine_v"], p["spine_half"], p["plaza_half"]
    every = p["lamp_every"]
    deep = p["service_v"] + p["service_half"] + 1
    anchors = [sv + sh + 2, p["promenade_v"]]
    z0, z1 = sv + ph + 6, deep - 2
    js = sorted(set(anchors))
    stops = sorted({min([z0 - 1] + js), max([z1 + 1] + js)} | set(js))
    jset, out = set(js), []
    for a, b in zip(stops, stops[1:]):
        ja, jb = a in jset, b in jset
        if ja and jb and b - a < 3 * every:
            out.append((a + b) // 2); continue
        lo = a + every if ja else a + 1
        hi = b - every if jb else b - 1
        if hi < lo:
            continue
        if ja:
            out.append(lo)
        if jb and hi != lo:
            out.append(hi)
        n = max(0, int(round((hi - lo) / every)) - 1)
        for i in range(n):
            out.append(lo + int(round((hi - lo) * (i + 1) / (n + 1))))
    return [z for z in sorted(set(out)) if z0 <= z <= z1]


DEFAULTS = PARKWAYS
