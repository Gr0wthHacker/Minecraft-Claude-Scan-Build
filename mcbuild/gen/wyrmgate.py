"""THE WYRM GATE - the bone skull straddling the rim railway, mouth open around the track.

Jack: *"are we able to place the skull so that the mouth 'opens' around the railway, the back of
the skeleton is towards the void and the mouth gap is where the railway passes through sideways"*.

**HIS ORIENTATION IS THE ONLY ONE THAT FITS, AND THAT IS A MEASUREMENT.** The skull's mouth is a
real gap - 32 wide, 18 courses tall, between the mandible below, the palate above and the two jaw
rami either side - and it is a tunnel along the FACE'S OWN NORMAL: open front to back, closed left
and right. So there are two ways to put a railway through it, and only one of them fits this park:

* face along the line, train out of the mouth head-on: needs the skull's 54-wide axis across V,
  which is V144-199 at best. It fits nowhere near the rim without eating the midway's inner band,
  and the face then addresses the track rather than the park.
* face across the line, train through the mouth sideways: the 54-wide axis runs along U, the
  40-deep axis across V, the face looks in at the park from V172 and the back of the cranium
  stands at V195, four short of the plot edge. **That is Jack's arrangement**, and it is the one
  that puts the face where the park can see it and the back over the rim.

**AND THE JAW IS EXACTLY AS DEEP AS THE RAILWAY IS WIDE, WHICH DECIDES THE WHOLE DESIGN.** The
corridor is V172-186 - fifteen columns of two tracks, a nine-wide central promenade and two
parapets, with an arcade under the deck - and the jaw rami are thirteen deep. There is no column
of jaw outside the railway to stand on, so:

    THE SKULL TOUCHES NOTHING THE RAILWAY MADE, AND IS CARRIED FROM THE RIM.

Inside the corridor the skull's lowest course is the LINTEL, three courses over the deck's own
standing course, so the track, the promenade, both parapet walks and the arcade under the deck are
all left exactly as the railway built them - `overlap 0` is a property of the construction rather
than something hoped for, and the railway can be regenerated under it. What carries the mass is
the SPUR: a rock bank on the rim at V187-199, outside the corridor, rising from the plate to meet
the skull's own underside and falling away to the plot edge. The back of the skeleton is set into
it, which is what "back towards the void" is when it is built rather than described.

**IT IS SUNK, AND THE SINK IS WHAT PUTS THE TRACK IN THE CLEAN PART OF THE MOUTH.** The low mouth
is full of the export's own ruins - stone brick, mossy brick, dirt, leaves, stairs standing on the
mandible - and driving a railway through those courses costs 1,846 cells of somebody else's build.
Ten courses down, the deck crosses the mouth at the skull's own y18-22, where there is nothing but
the rami and two stray cells: **the cut falls from 1,846 to 625.** What it costs is the mandible
and the diorama base, which fall below the park's plate and are trimmed - so the skull reads as
embedded in the rim to the gum line, and the plate itself is the floor of the mouth's front.

Measured, at the shipped placement: 23,480 of the asset's 38,225 cells stand, 9,305 fall below the
plate, 2,446 fall past the plot edge at V199, 2,624 are the arcade band and 370 are the deck's own
three courses. Not one cell of the railway is taken.

**THE SITE IS THE ONE MAST-FREE WINDOW ON THE REACH.** The line carries a lamp mast every sixty
columns, at U361 and U421 either side, and its three stations at U77/279/505; the skull is 54 wide,
so U366-419 is the window - 33 columns of it in the Prism Reach and 21 on the Midway's own rim,
which is where `Wyrm's Crossing` already stood. Above the deck the corridor in that window is
CLEAN: measured over the shipped park, its tallest cell is Y216.
"""
from __future__ import annotations

import numpy as np

from .. import schem
from . import asset
from .canvas import Canvas, hash01

GATE = {
    "kind": "wyrm_gate",
    #: the outside builder's skull - 54 x 66 x 40, 38,235 cells at 26.8% fill
    "source": "reference/bone_ruins_skull.litematic",
    #: 90 PUTS THE FACE AT LOW V, which is the park. As loaded the skull faces along U - down the
    #: line - and a visitor gets the profile, which on a skull is thin and reads as flat. Asserted
    #: rather than eyeballed: `tests/test_wyrmgate.py` measures which end of the model the eye
    #: sockets open to, because our renderer draws a wrong facing exactly like a right one.
    "rotate": 90,
    #: the export's own crop debris - four fragments in its `z <= 5` slice
    "prune": 8,
    "lot": None,                     # [dv, du]
    "at": None,                      # [V, U] of the lot's own corner; the face stands at V = at[0]
    "anchor": [97500, 203, 80300],
    #: HOW FAR THE SKULL'S OWN y0 SITS BELOW THE PLANE. See the module docstring: the sink is what
    #: moves the track out of the ruins in the low mouth and into the clean upper mouth, and it is
    #: bounded at both ends - under 6 the deck crosses the ruins, over 13 the cranium's underside
    #: drops into the rider's own clearance.
    "sink": 10,
    "rail": None,                    # the railway artifact, loaded and refused cell for cell
    "rail_at": None,                 # [V, Y, U] - the railway model's own origin, from its sidecar
    "corridor": None,                # [V0, V1] - the band the railway owns, in world V
    #: THE GIRDER BAND: the courses the skull may not occupy ANYWHERE across the corridor - the
    #: box girder itself and the clearance over the deck it carries. A walker on the promenade
    #: occupies two courses and a rider in a cart needs two over the rail, so the band runs from
    #: the girder's own soffit to deck + 2. The railway's cells are refused separately: a design
    #: that trusted only the artifact would happily wall up the promenade, which holds no blocks
    #: at all, and the arcade, which is the space under an arch.
    "girder": None,                  # [Y0, Y1]; defaults to [deck - 4, deck + 2]
    #: HOW MANY COURSES THE CLEARANCE RISES AT THE CORRIDOR'S CENTRE. A flat band cut through a
    #: jaw leaves a flat soffit, and a rider looking down the line at a horizontal plane spanning
    #: fifteen columns is looking at a SAWN BEAM, not at a portal through a jaw. The band is a
    #: semi-ellipse instead: level at the parapets, `arch` courses higher in the middle, so what
    #: the cut leaves behind reads as an arch. It costs bone and buys the only view a rider gets.
    "arch": 3,
    "deck": 215,                     # world Y of the deck's standing course
    #: WALKS THIS DESIGN CROSSES AND MUST NOT CLOSE, as [{v0, v1, y0, y1}] in world V and Y.
    #: Two of them, and neither is optional. The line's own arcade runs the length of the viaduct
    #: at the plate, threading past each pier's five-wide core, so its lane has to be one of the
    #: two passages the pier already leaves - a jaw across it is fifty-four columns of wall. And
    #: `Park Ways` draws the rim's own boundary line in front of the viaduct: a paved course with
    #: fence posts on it, which the jaw's front lip stands astride.
    "keep_clear": None,
    "arcade": None,                  # kept for configs written before `keep_clear`
    #: THE SPUR on the rim: {v0, v1, top, fall, jitter}. v0 must be outside the corridor.
    "spur": None,
    #: froglights set INTO the tunnel's roof and the spur's crust - never laid on top of either
    "lamp_every": 9,
    "spur_lamp_every": 13,
    #: LAMPS ON THE GROUND THIS DESIGN SHADES, both sides of the corridor. Measured over the finished composite, the rim strip
    #: behind the railway was already the darkest ground here - 460 standable cells at block light
    #: zero before this design existed, because the park's night pass grades a column by its
    #: TOPMOST standable cell and the rim is not a guest path. Putting the skull over it makes the
    #: shadow deeper, so the design lights the ground it shades: on the ground, which is the cheap
    #: place for a fixture, and never on the coat.
    "rim_lamp_every": 7,
    "min_component": 12,
    #: BLOCKS THE ASSET CARRIES THAT THIS SITE MAY NOT HAVE, refused by name and reported. The
    #: bone ruins' garden is a BOOBY-TRAPPED treasure: 77 TNT and eight stone pressure plates
    #: round a chest and a gold block. That is a fine thing in somebody's own diorama and it is
    #: not a thing to hang over a working railway in a theme park - the trap is armed the moment
    #: the printer places it, the park's own circuit inspection reports every charge as unwired,
    #: and the blast would take the viaduct with it. Nothing else in the diorama is touched.
    "drop": ["tnt", "stone_pressure_plate"],
    "seed": 0,
}

#: The spur's bedding, cheap tier and witnessed on this server. MEASURED ACROSS FAMILIES, because
#: inside one there is no ladder: stone 126, mossy brick 114, dripstone 112 and moss 101 span 25
#: points between them, which is nearly a single tone, and `deepslate` at 80 is the only real step
#: this palette can buy. It is the one `ok`-tier entry and it is spent on the bottom two courses.
SPUR = {"deep": "deepslate", "rock": "stone", "bed": "mossy_stone_bricks",
        "brown": "dripstone_block", "crust": "moss_block"}
LAMP = "ochre_froglight"


def build(cfg: dict, donors=None) -> Canvas:
    p = {**GATE, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("a wyrm gate needs its measured lot: lot: [dv, du]")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    at_v, at_u = (int(v) for v in (p.get("at") or (0, 0)))
    av, ay, au = (int(v) for v in p["anchor"])
    sink = int(p["sink"])
    deck = int(p["deck"])
    g0, g1 = (int(v) for v in (p.get("girder") or (deck - 4, deck + 2)))
    if not p.get("corridor"):
        raise ValueError("a wyrm gate needs the railway's corridor: corridor: [V0, V1]")
    c0, c1 = (int(v) for v in p["corridor"])

    skull = asset.build({"source": p["source"], "rotate": p["rotate"], "prune": p["prune"]})
    sky, sku, skv = skull.ids.shape                  # (y, U, V) once turned
    sy = max(sky - sink + 8, 40)
    c = Canvas(dv, sy, du, donors)
    rail = _Rail(p)

    # ------------------------------------------------------------------ the skull
    arch = int(p.get("arch") or 0)
    drop = {str(n).split(":")[-1] for n in (p.get("drop") or ())}
    dropped: dict = {}
    names = [n.split("[")[0].split(":")[-1] for n in
             (e.value["Name"].value for e in skull.palette)]
    lanes = list(p.get("keep_clear") or ())
    if p.get("arcade"):
        lanes.append(p["arcade"])
    refused = {"railway": 0, "girder": 0, "walk_lane": 0, "below_plate": 0, "off_plot": 0}
    keep = np.zeros(skull.ids.shape, bool)
    for y, zu, xv in zip(*(skull.ids > 0).nonzero()):
        V, U, Y = at_v + xv, at_u + zu, ay - sink + y
        name = names[int(skull.ids[y, zu, xv])]
        if name in drop:
            dropped[name] = dropped.get(name, 0) + 1
            continue
        if xv >= dv:
            refused["off_plot"] += 1
            continue
        if Y < ay:
            refused["below_plate"] += 1
            continue
        if rail.at(V, Y, U):
            refused["railway"] += 1
            continue
        if c0 <= V <= c1 and g0 <= Y <= g1 + _arch(V, c0, c1, arch):
            refused["girder"] += 1
            continue
        if any(int(l["v0"]) <= V <= int(l["v1"]) and int(l["y0"]) <= Y <= int(l["y1"])
               for l in lanes):
            refused["walk_lane"] += 1
            continue
        keep[y, zu, xv] = True

    _drop_strays(keep, int(p["min_component"]))
    # THE SKULL'S PALETTE IS NOT THIS CANVAS'S PALETTE. Copying an index straight across writes a
    # number that means a different block here and nothing at all past the end of the registry -
    # which is not a wrong block, it is a file the writer cannot compact.
    remap = {i: c.reg._add(skull.palette[i]) for i in range(1, len(skull.palette))}
    placed = 0
    for y, zu, xv in zip(*keep.nonzero()):
        if c.put(int(xv), int(y - sink), int(zu), remap[int(skull.ids[y, zu, xv])]):
            placed += 1

    # ------------------------------------------------------------------ the spur
    spur = _spur(c, p, keep, dv, du, at_v, ay, sink, c1)

    # ------------------------------------------------------------------ one piece
    # THE STRAY PRUNE HAS TO RUN AFTER THE SPUR, NOT BEFORE IT. Pruned on the skull's own mask it
    # cannot see what the spur is about to connect, and pruned only there it leaves whatever the
    # spur failed to reach - two clods of the diorama's own garden, 44 and 12 cells, hanging over
    # a railway with a clean audit behind them.
    strays = _prune_canvas(c, int(p["min_component"]))

    # ------------------------------------------------------------------ light
    lamps = _light(c, p, keep, dv, du, at_v, ay, sink, c0, c1, g1 + 1, spur["top"])

    c.world_origin = (av + at_v, ay, au + at_u)
    c.meta = {
        "kind": "wyrm_gate",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "prism_reach",
        "facing": "west",
        "profile_axis": "u",
        "sink": sink,
        "girder": [g0, g1],
        "arch": arch,
        "skull_cells": placed,
        "refused": refused,
        "dropped": dropped,
        "spur_cells": spur["cells"],
        "strays_pruned": strays,
        "lamps": lamps,
        "contract": (
            "the bone skull straddling the rim railway with the track through its mouth: the "
            "face looks in at the park from the corridor's own near edge, the back of the cranium "
            "stands on the rim over the void, and not one cell of the railway - track, promenade, "
            "parapet, arch or arcade - is taken. Inside the corridor the skull's lowest course is "
            "the lintel, three over the deck; the mass is carried by a rock spur on the rim"),
    }
    return c


# --------------------------------------------------------------------------- the railway


class _Rail:
    """Every cell the railway owns, in world coordinates, and nothing else.

    THE ARTIFACT IS THE AUTHORITY ON WHERE THE RAILWAY IS AND IT IS SILENT ON WHERE A PLAYER
    GOES. Its deck is a solid course with two rails on top and nine columns of promenade between
    them, and a promenade holds no blocks at all - so a design that refused only the cells in this
    model would wall up the walk and pass every check it has. The lintel is what answers that, and
    this class answers only the other half: do not cover what somebody else built.
    """

    def __init__(self, p: dict):
        self.ok = bool(p.get("rail"))
        if not self.ok:
            return
        m = schem.load(str(p["rail"]))
        self.sol = m.solid()                                    # [y, U, V]
        rv, ry, ru = (int(v) for v in (p.get("rail_at") or (0, 0, 0)))
        self.rv, self.ry, self.ru = rv, ry, ru
        self.sy, self.su, self.sv = self.sol.shape

    def at(self, V: int, Y: int, U: int) -> bool:
        if not self.ok:
            return False
        v, y, u = V - self.rv, Y - self.ry, U - self.ru
        if not (0 <= v < self.sv and 0 <= y < self.sy and 0 <= u < self.su):
            return False
        return bool(self.sol[y, u, v])


def _prune_canvas(c: Canvas, floor: int) -> int:
    """The same rule as `_drop_strays`, run on the finished canvas so the spur counts as support."""
    solid = c.ids > 0
    keep = solid.copy()
    dropped = _drop_strays(keep, floor)
    for cell in map(tuple, np.argwhere(solid & ~keep)):
        c.ids[cell] = 0
    return dropped


def _drop_strays(keep: np.ndarray, floor: int) -> int:
    """Drop 6-connected fragments under `floor` cells from the kept mask.

    Cutting a jaw off at the deck leaves stubs: a course of ramus whose support went to the
    corridor, a two-cell clod of the ruins that stood on the mandible. They audit clean - legal,
    supported by nothing an audit measures, affordable - and read as bone hanging over a railway.
    """
    if floor <= 0:
        return 0
    nb = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    seen = np.zeros(keep.shape, bool)
    dropped = 0
    for start in map(tuple, np.argwhere(keep)):
        if seen[start]:
            continue
        stack, cells = [start], []
        seen[start] = True
        while stack:
            cur = stack.pop()
            cells.append(cur)
            for d in nb:
                q = (cur[0] + d[0], cur[1] + d[1], cur[2] + d[2])
                if all(0 <= q[i] < keep.shape[i] for i in range(3)) and keep[q] and not seen[q]:
                    seen[q] = True
                    stack.append(q)
        if len(cells) < floor:
            for cell in cells:
                keep[cell] = False
            dropped += len(cells)
    return dropped


# --------------------------------------------------------------------------- the spur


def _under(keep: np.ndarray, dv: int, du: int) -> np.ndarray:
    """The lowest kept course of every column of the skull, or -1. This is what the spur meets."""
    low = np.full((dv, du), -1, int)
    for y, zu, xv in zip(*keep.nonzero()):
        if xv < dv and zu < du and (low[xv, zu] < 0 or y < low[xv, zu]):
            low[xv, zu] = y
    return low


def _arch(V: int, c0: int, c1: int, rise: int) -> int:
    """A semi-elliptical rise over the corridor: 0 at either parapet, `rise` at the centre."""
    if rise <= 0 or c1 <= c0:
        return 0
    t = (2.0 * (V - (c0 + c1) / 2.0)) / (c1 - c0)
    return int(round(rise * max(0.0, 1.0 - t * t) ** 0.5))


def _ceiling(keep: np.ndarray, dv: int, du: int, base: int, floor_y: int) -> np.ndarray:
    """The lowest kept course of each column that stands at or above `floor_y` (world Y), or -1."""
    low = np.full((dv, du), -1, int)
    for y, zu, xv in zip(*keep.nonzero()):
        if xv >= dv or zu >= du or base + y < floor_y:
            continue
        if low[xv, zu] < 0 or y < low[xv, zu]:
            low[xv, zu] = y
    return low


def _spur(c: Canvas, p: dict, keep, dv, du, at_v, ay, sink, c1) -> dict:
    """A rock bank on the rim, from the plate up to the skull's own underside.

    **IT IS STRUCTURAL, NOT DRESSING.** With the jaw cut off at the deck the whole upper skull -
    23,000 cells of it - has nothing under it inside the corridor and nothing may be put there, so
    without this the design is a head hanging in mid-air over a working railway. The spur's top
    FOLLOWS the skull: `min(cap, underside - 1)`, so it rises to meet the mass and can never poke
    into it, and the cap falls away toward the plot edge, so what stands on the rim is a bank
    rather than a wall.

    THE SPUR MAY NOT ENTER THE CORRIDOR, and that is asserted rather than assumed: it is the one
    part of this design with a free hand, and one column of it inside V172-186 would be a block in
    the railway's own arcade.
    """
    s = p.get("spur")
    if not s:
        return {"cells": 0, "top": np.full((dv, du), -1, int)}
    v0 = int(s.get("v0", c1 + 1 - at_v))
    v1 = int(s.get("v1", dv - 1))
    if at_v + v0 <= c1:
        raise ValueError(f"the spur starts at V{at_v + v0}, inside the railway's corridor")
    top_h = int(s["top"]) - ay                       # courses over the plane
    fall = float(s.get("fall", 1.6))
    jitter = float(s.get("jitter", 1.2))
    seed = int(p.get("seed", 0))
    ladder = [SPUR["deep"], SPUR["deep"], SPUR["rock"], SPUR["rock"], SPUR["bed"],
              SPUR["rock"], SPUR["brown"], SPUR["rock"], SPUR["bed"], SPUR["rock"]]
    tops = np.full((dv, du), -1, int)
    cells = 0
    for v in range(v0, min(v1 + 1, dv)):
        cap = top_h - fall * (v - v0)
        for u in range(du):
            wob = (hash01(v * 5 + 1, u * 11 + 3, 7, seed) - 0.5) * 2.0 * jitter
            h = int(np.floor(cap + wob))
            if h < 0:
                continue
            # IT FILLS WHAT IS EMPTY, WHICH IS THE WHOLE POINT AND WAS THE FIRST BUILD'S BUG. A
            # spur clamped to "one under the column's LOWEST cell" cannot bridge a gap ABOVE
            # something: on the rim the skull's own base already stands on the plate, so every
            # column read as satisfied, 731 cells went in, and the cranium stayed a separate piece
            # hanging over a working railway. What is needed is the void between the base's top
            # and the cranium's underside - so it fills every empty cell up to the cap and never
            # overwrites one the skull owns.
            top = -1
            for y in range(0, h + 1):
                if c.solid(v, y, u):
                    continue
                key = SPUR["crust"] if y == h else ladder[y % len(ladder)]
                if c.put(v, y, u, c.state(key)):
                    cells += 1
                    top = y
            if top >= 0:
                tops[v, u] = top
    return {"cells": cells, "top": tops}


# --------------------------------------------------------------------------- light


def _light(c: Canvas, p: dict, keep, dv, du, at_v, ay, sink, c0, c1, lintel, tops) -> dict:
    """Froglights set INTO the tunnel's roof and the spur's crust.

    The mouth over the track is a covered tunnel fifty-four columns long, and a covered tunnel over
    live rails is a mob standing on the deck at night. The lamp REPLACES a cell of the roof rather
    than hanging under it - the rule the frog's own back settled: a fixture laid on a coat is a
    hole in the sculpture - and it is only ever put in the lintel course, which is above every
    clearance the railway needs.
    """
    every = int(p.get("lamp_every") or 0)
    roof = 0
    if every > 0:
        # THE CEILING IS THE LOWEST CELL ABOVE THE GIRDER, NOT THE LOWEST CELL. Measured off the
        # skull's own underside the answer is the garden in its jaw, which stands UNDER the deck -
        # so the pass lit the garden's floor and left the tunnel over the rails with one lamp in
        # fifty-four columns. Twice.
        low = _ceiling(keep, dv, du, ay - sink, lintel)
        for u in range(du):
            if u % every:
                continue
            # THE ROOF IS NOT ONE PLANE, and twice this pass shipped a fifty-four-column tunnel
            # over live rails with ONE froglight in it. A skull's palate steps: measured, the
            # corridor's ceiling runs Y218-229 along the mouth and only six columns of it sit on
            # the lintel course exactly. Take the lowest ceiling this column has, anywhere within
            # reach of the deck, rather than demanding a plane the geometry does not have.
            best = None
            for v in range(dv):
                V = at_v + v
                if not (c0 <= V <= c1):
                    continue
                y = int(low[v, u])
                if y < 0:
                    continue
                cy = y - sink
                if lintel <= ay + cy <= lintel + 6 and (best is None or cy < best[1]):
                    best = (v, cy)
            if best and c.solid(best[0], best[1], u) and c.put(best[0], best[1], u, c.state(LAMP)):
                roof += 1
    rim_every = int(p.get("rim_lamp_every") or 0)
    rim = 0
    if rim_every > 0:
        floor = max(0, (lintel - 7) - ay)            # the ground band, under the girder
        for v in range(dv):
            V = at_v + v
            if c0 <= V <= c1 or (V - at_v) % rim_every:
                continue
            for u in range(du):
                if u % rim_every:
                    continue
                # THE GROUND HERE IS THE DIORAMA'S OWN, and the lamp goes IN it: the rim under the
                # cranium is either bare plate - which belongs to the ground layer and may not be
                # touched - or the skull's own base slab. So the fixture takes the base's top
                # course where there is one and the course over the plate where there is not.
                top = next((y for y in range(floor, -1, -1) if c.solid(v, y, u)), None)
                if top is None:
                    if c.solid(v, 0, u):
                        continue
                    target = 0
                else:
                    target = top
                if not any(c.solid(v, y, u) for y in range(target + 2, min(c.sy, target + 30))):
                    continue                          # nothing overhead: daylight lights this
                if c.put(v, target, u, c.state(LAMP)):
                    rim += 1
    spur_every = int(p.get("spur_lamp_every") or 0)
    crust = 0
    if spur_every > 0:
        vs = [v for v in range(dv) if (tops[v] >= 0).any()]
        v0 = min(vs) if vs else 0
        for v in range(dv):
            for u in range(du):
                h = int(tops[v, u])
                if h < 0 or (v - v0) % spur_every or u % spur_every:
                    continue
                if c.put(v, h, u, c.state(LAMP)):
                    crust += 1
    return {"roof": roof, "rim": rim, "spur": crust}
