"""The lost Prismworks abyssal research vessel behind the Abyss Squid.

It is a WRECK, and the palette has to say so before the silhouette does. Two lessons drive the
skin: colour blooms at DAMAGE, never in a stripe - verdigris is what corrodes through a hull
where the sea got in, so the green is clustered at the crush craters and the scars and is dark
everywhere else; and a wreck is BROKEN - crush craters, torn deck plating, a snapped conning
tower, a shattered viewport and a single dented ducted rotor, not a clean sub with one dent.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01


WRECK = {
    "at": [97505, 100, 80365], "size": [185, 75, 90], "seed": 31,
    "greybox": False, "shell": 2,
    "hull": "deepslate_bricks", "hull_crack": "cracked_deepslate_bricks",
    "dark": "polished_blackstone_bricks", "dark_crack": "cracked_polished_blackstone_bricks",
    "cu1": "cut_copper", "cu2": "exposed_cut_copper",
    "cu3": "weathered_cut_copper", "cu4": "oxidized_cut_copper",
    "glass": "cyan_stained_glass", "crack": "black_wool",
    "light": "pearlescent_froglight", "scar": "bone_block",
    # Expensive accents, confined to fine instruments - a Prismworks vessel is trimmed in the
    # prismarine it is named for. Declared in the config's expensive_reason.
    "alloy": "dark_prismarine", "optic": "tinted_glass",
    "lens": "amethyst_block", "lantern": "sea_lantern",
    # Interior finish (all placeable on the 1.19 server): a derelict, powered-down, walkable wreck.
    "i_deck": "deepslate_tiles", "i_wall": "deepslate_bricks", "i_mezz": "iron_block",
    "i_rail": "iron_bars", "i_pipe": "cut_copper", "i_pipe2": "oxidized_cut_copper",
    "i_machine": "iron_block", "i_panel": "polished_deepslate", "i_debris": "cobbled_deepslate",
    "i_bunk": "cyan_wool", "i_lamp": "verdant_froglight", "i_lamp2": "sea_lantern",
    "water": "water", "mark": "bone_block", "trim": "prismarine_bricks",
}

# A minimal 3x5 block font for hull markings (rows top->bottom).
GLYPHS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    "P": ["111", "101", "111", "100", "100"], "W": ["101", "101", "101", "111", "101"],
    "-": ["000", "000", "111", "000", "000"],
}

# interior part -> finish material key
IFINISH = {
    "deck": "i_deck", "bulkhead": "i_wall", "mezz": "i_mezz", "rail": "i_rail",
    "pipe": "i_pipe", "pipe2": "i_pipe2", "machine": "i_machine", "panel": "i_panel",
    "debris": "i_debris", "bunk": "i_bunk", "ilight": "i_lamp", "ilight2": "i_lamp2",
    "console": "i_panel", "water": "water", "stair": "i_deck", "leaf": "i_rail",
}

# Damage volumes: x, y, z, rx, ry, rz, zmin. Caved into the visible south flank by the squid.
CRUSH = [
    (120, 34, 62, 15, 11, 13, 51),   # the main grab - a deep caved crater
    (151, 40, 59, 9, 8, 10, 50),     # a second grip aft
    (92, 30, 61, 7, 6, 8, 53),       # a smaller puncture forward
]
# Torn deck plating: shallow gashes peeling the top skin, clear of the tower's own footprint
# so they cannot sever it. Kept thin (ry 2) and high so they bite only the upper hull.
TEARS = [
    (52, 51, 46, 11, 2, 3),
    (132, 49, 41, 8, 2, 3),
    (150, 47, 55, 7, 2, 4),
]
# Where verdigris blooms - the crush craters (broadly) and the sucker-scars (tight gouges,
# brown not green). Kept small so the green concentrates at the caved metal, not across the flank.
WOUNDS = [(c[0], c[1], c[2], (c[3] + c[5]) * 0.42) for c in CRUSH] + \
         [(83, 39, 63, 4), (105, 29, 63, 4), (137, 43, 63, 4)]


def _ellipsoid(solid, parts, cx, cy, cz, rx, ry, rz, part, exp=2.0):
    for x in range(math.floor(cx - rx - 1), math.ceil(cx + rx + 2)):
        for y in range(math.floor(cy - ry - 1), math.ceil(cy + ry + 2)):
            for z in range(math.floor(cz - rz - 1), math.ceil(cz + rz + 2)):
                q = (abs((x - cx) / max(rx, .1)) ** exp + abs((y - cy) / max(ry, .1)) ** exp +
                     abs((z - cz) / max(rz, .1)) ** exp)
                if q <= 1:
                    solid.add((x, y, z)); parts[(x, y, z)] = part


def _line(solid, parts, a, b, r, part):
    n = max(1, math.ceil(math.dist(a, b)))
    for i in range(n + 1):
        t = i / n
        p = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
        _ellipsoid(solid, parts, *p, r, r, r, part)


def _carve(solid, parts, cx, cy, cz, rx, ry, rz, zmin=None):
    n = 0
    for q in list(solid):
        x, y, z = q
        if zmin is not None and z < zmin:
            continue
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1:
            solid.discard(q); parts.pop(q, None); n += 1
    return n


def _viewport(solid, parts, cx=59, cy=37, rx=15, ry=9):
    """Glaze a window SET INTO the bow flank, following the pressure hull's own curve.

    Not a blister stuck on top: the inner panel is dished one course into the existing hull
    surface and the rim is left proud as a frame, so the glass reads as a viewport recessed
    into the plating - the way a real pressure hull carries one."""
    for x in range(cx - rx, cx + rx + 1):
        for y in range(cy - ry, cy + ry + 1):
            e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if e > 1.0:
                continue
            col = [z for (qx, qy, z) in solid if qx == x and qy == y]
            if not col:
                continue
            zmax = max(col)
            if e <= 0.80:                                    # the glazed panel: recess a course
                solid.discard((x, y, zmax)); parts.pop((x, y, zmax), None)
                if (x, y, zmax - 1) in solid:
                    parts[(x, y, zmax - 1)] = "viewport"
            else:                                            # the surrounding frame lip, flush
                parts[(x, y, zmax)] = "viewport_frame"


def _hull(solid, parts):
    # Long pressure hull along X, broadside to the squid-tail overlook.
    for x in range(8, 169):
        t = (x - 8) / 160
        end = min(t / .14, (1 - t) / .16, 1.0)
        ry = 8 + 14 * max(0, end) ** .55
        rz = 7 + 13 * max(0, end) ** .55
        cy = 32 + 1.5 * math.sin(t * math.pi); cz = 43
        for y in range(round(cy - ry - 1), round(cy + ry + 2)):
            for z in range(round(cz - rz - 1), round(cz + rz + 2)):
                if abs((y - cy) / ry) ** 2.35 + abs((z - cz) / rz) ** 2.35 <= 1:
                    solid.add((x, y, z)); parts[(x, y, z)] = "hull"

    # Conning tower, snapped and leaning aft where the sea took it.
    for x in range(86, 116):
        for y in range(49, 65):
            lz = int((y - 49) * 0.4)          # leans toward +z with height
            for z in range(36 + lz, 52 + lz):
                zz = z - lz
                edge = min(x - 86, 115 - x, y - 49, 64 - y, zz - 36, 51 - zz)
                if edge < 0:
                    continue
                if y > 57 and x > 112 - (y - 57) * 3:   # sheared-off top, aft
                    continue
                if y > 60 and zz > 48:                  # torn upper corner
                    continue
                solid.add((x, y, z)); parts[(x, y, z)] = "tower"
    # Snapped mast, bent and drooping rather than standing proud.
    _line(solid, parts, (98, 63, 49), (101, 68, 52), 1.6, "antenna")
    _line(solid, parts, (101, 68, 52), (106, 66, 56), 1.3, "antenna")
    # The periscope/scope head at the mast elbow: a prismarine housing, a tinted optic on its
    # forward face and one live glint - the instrument reads as an INSTRUMENT, not a dark stick.
    _ellipsoid(solid, parts, 101, 68, 52, 2.2, 2.2, 2.2, "alloy")
    _ellipsoid(solid, parts, 101, 68, 55, 1.2, 1.2, 1.4, "optic")   # the lens, aimed forward
    solid.add((101, 70, 52)); parts[(101, 70, 52)] = "lantern"      # the one glint still lit

    # A single dented ducted rotor at the stern centreline - the dead engine.
    cx, cy, cz = 178, 32, 43
    _line(solid, parts, (159, 32, 43), (cx, cy, cz), 3, "shaft")
    _ellipsoid(solid, parts, cx, cy, cz, 3, 3, 3, "rotor")
    ring = []
    for deg in range(0, 360, 5):
        if 38 <= deg <= 92:        # a caved-in gap in the shroud
            continue
        a = math.radians(deg)
        ring.append((cx, cy + 12 * math.sin(a), cz + 12 * math.cos(a)))
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if math.dist(a, b) < 4:
            _line(solid, parts, a, b, 1.8, "rotor")
    for deg in (10, 145, 205, 300):            # four surviving blades, not a clean set
        a = math.radians(deg)
        tip = (cx - 1, cy + 10.5 * math.sin(a), cz + 10.5 * math.cos(a))
        _line(solid, parts, (cx, cy, cz), tip, 1.4, "rotor")

    # Articulated bow survey arms; one hangs snapped to make the wreck unmistakable.
    _line(solid, parts, (15, 29, 53), (4, 24, 66), 3, "survey_arm")
    _line(solid, parts, (4, 24, 66), (10, 17, 74), 2, "survey_arm")
    _line(solid, parts, (18, 38, 55), (3, 43, 68), 3, "survey_arm")
    _line(solid, parts, (3, 43, 68), (-2, 39, 76), 2, "survey_arm")
    # Sensor optics on the arm tips: the upright arm's still glows (sea lantern); the snapped,
    # hanging arm's is a dead amethyst lens - one eye lit, one gone dark.
    _ellipsoid(solid, parts, 4, 43, 69, 1.7, 1.7, 1.7, "lantern")   # upright arm, still live
    _ellipsoid(solid, parts, 10, 17, 74, 1.7, 1.7, 1.7, "lens")     # hanging arm, dead optic

    # Control surfaces - the hardware that reads as SUBMARINE. Thin flattened blades, rooted
    # into the skin so they cannot shed, tips proud enough to break the outline.
    # Bow foreplanes (port + starboard), a hair below the axis on the tapering nose.
    _ellipsoid(solid, parts, 28, 30, 63, 6, 1.4, 9, "fin")   # starboard, the visible side
    _ellipsoid(solid, parts, 28, 30, 23, 6, 1.4, 9, "fin")   # port
    # Stern cruciform - two sternplanes and the rudder pair, on the shaft ahead of the rotor.
    _ellipsoid(solid, parts, 172, 40, 43, 4, 7, 1.4, "fin")  # upper (rudder)
    _ellipsoid(solid, parts, 172, 24, 43, 4, 7, 1.4, "fin")  # lower (rudder)
    _ellipsoid(solid, parts, 172, 32, 51, 4, 1.4, 7, "fin")  # starboard sternplane
    _ellipsoid(solid, parts, 172, 32, 35, 4, 1.4, 7, "fin")  # port sternplane
    # Fairwater (sail) planes on the conning tower, the small forward pair every sub carries.
    _ellipsoid(solid, parts, 96, 56, 53, 3, 1.2, 5, "fin")

    # Dish the observation viewport into the bow flank (after the flank exists, before it is
    # damaged) so the glass is recessed into the hull rather than bulging off it.
    _viewport(solid, parts)

    # Caved craters and torn deck plating.
    for cx, cy, cz, rx, ry, rz, zmin in CRUSH:
        _carve(solid, parts, cx, cy, cz, rx, ry, rz, zmin)
    for cx, cy, cz, rx, ry, rz in TEARS:
        _carve(solid, parts, cx, cy, cz, rx, ry, rz)

    # Limber holes: the dashed row of flood slots along the lower south flank that every
    # submarine carries. Small notches through the shell, clear of the crush craters, low on
    # the visible side - a line of dark ticks that says 'pressure hull' at a glance.
    limber = 0
    for lx in range(80, 158, 8):                       # aft of the observation blister (x<76)
        if any(abs(lx - cx) < rx for cx, _, _, rx, _, _, _ in CRUSH):
            continue                                  # do not nibble the crater rims
        limber += _carve(solid, parts, lx, 26, 60, 1.3, 2.4, 5, zmin=54)
    return limber


def _shell(solid, depth):
    inner = set(solid)
    for _ in range(depth):
        inner = {p for p in inner if all((p[0] + dx, p[1] + dy, p[2] + dz) in inner
                 for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))}
    return set(solid) - inner


# The walkable interior. The hull already ships as a thin shell over air, so the deck, the
# bulkheads and the ladders are added INTO that cavity; the crush breach is the only way in.
DECK_Y = 27                                     # floor top; a player stands at 28-29
BULKHEADS = (44, 78, 112, 140)                  # -> bow trim | lounge | control | quarters | engine
COMPARTMENTS = ("bow_trim", "observation_lounge", "control_room", "crew_quarters", "engine_room")


def _interior(solid, shell):
    """Deck plates and bulkheads dropped into the hull cavity, with doorways on the centreline.

    The deck is the cavity cross-section at one height (so it always meets the curved wall and
    stays one piece); a bulkhead is the cavity cross-section at one station, floor to overhead,
    with a doorway punched at deck level so the compartments walk through into each other."""
    inner = solid - shell
    if not inner:
        return set(), {}
    by_x = {}
    for q in inner:
        by_x.setdefault(q[0], []).append(q)
    cells, parts = set(), {}
    door_z = set(range(41, 46)); door_y = set(range(DECK_Y + 1, DECK_Y + 4))   # 28..30, 3 high
    for x, col in by_x.items():
        colset = set(col)
        for (qx, qy, qz) in col:
            if qy == DECK_Y and (qx, DECK_Y + 2, qz) in colset:      # deck only where headroom
                cells.add((qx, qy, qz)); parts[(qx, qy, qz)] = "deck"
        if x in BULKHEADS:
            for (qx, qy, qz) in col:
                if qy >= DECK_Y and not (qz in door_z and qy in door_y):
                    cells.add((qx, qy, qz)); parts[(qx, qy, qz)] = "bulkhead"

    inside = {q for q in inner}

    def plate(x0, x1, y, z0, z1, part):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if (x, y, z) in inside:
                    cells.add((x, y, z)); parts[(x, y, z)] = part

    def stair(x, z, y0, y1):                       # a solid stepped ramp - each column touches
        for i, y in enumerate(range(y0, y1 + 1)):  # its neighbour and the deck (no diagonal gaps)
            for yy in range(y0, y + 1):
                q = (x + i, yy, z)
                if q in inside:
                    cells.add(q); parts[q] = "stair"

    MEZZ_Y = DECK_Y + 8                            # a raised platform, 8 up from the main deck
    # Control-room periscope stand and engine-room catwalk (solid iron - 1.19 has no safe grate
    # block, and a trapdoor floor is a player-openable fall hazard on a walkway).
    plate(92, 108, MEZZ_Y, 38, 48, "mezz"); stair(88, 40, DECK_Y + 1, MEZZ_Y)
    plate(144, 160, MEZZ_Y, 39, 47, "mezz"); stair(140, 41, DECK_Y + 1, MEZZ_Y)
    # Rails around the two mezzanine edges so they read as platforms, not slabs.
    for (x0, x1, z0, z1) in ((92, 108, 38, 48), (144, 160, 39, 47)):
        for x in range(x0, x1 + 1):
            for z in (z0, z1):
                q = (x, MEZZ_Y + 1, z)
                if q in inside:
                    cells.add(q); parts[q] = "rail"
    # Watertight-hatch frames: iron jambs and a lintel around each bulkhead doorway.
    for bx in BULKHEADS:
        for yy in range(DECK_Y + 1, DECK_Y + 4):
            for zz in (40, 46):
                if parts.get((bx, yy, zz)) == "bulkhead":
                    parts[(bx, yy, zz)] = "rail"
        for zz in range(41, 46):
            if parts.get((bx, DECK_Y + 4, zz)) == "bulkhead":
                parts[(bx, DECK_Y + 4, zz)] = "rail"
        for yy in range(DECK_Y + 1, DECK_Y + 4):             # an open grille door-leaf, folded back
            if parts.get((bx, yy, 39)) == "bulkhead":
                parts[(bx, yy, 39)] = "leaf"
    return cells, parts


def _furnish(inner):
    """Dress each compartment: sonar, an observation gallery at the viewport, the control-room
    periscope and consoles, crew bunks and the breach inrush, and a flooded engine room."""
    inside = set(inner)
    cells, parts = set(), {}
    D = DECK_Y

    def put(x, y, z, part):
        if (x, y, z) in inside:
            cells.add((x, y, z)); parts[(x, y, z)] = part

    def box(x0, x1, y0, y1, z0, z1, part):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    put(x, y, z, part)

    def overhead(x0, x1, zs, part="pipe"):
        # hung from the overhead: the topmost cavity cell touches the shell, so the run is anchored
        for x in range(x0, x1 + 1):
            for z in zs:
                ys = [y for y in range(D + 3, 62) if (x, y, z) in inside]
                if ys:
                    put(x, max(ys), z, part)

    # Emergency lighting: a sparse overhead strip still burning in one bay per compartment.
    # Powered down, so it is thin - just enough to navigate a derelict, not a lit vessel.
    for lx in range(20, 160, 11):
        if 86 <= lx <= 115:
            continue                                  # the tower shaft is open above - no ceiling here
        for ly in range(52, D + 2, -1):
            if (lx, ly, 43) in inside and (lx, ly + 1, 43) not in inside:
                put(lx, ly, 43, "ilight"); break      # only where a ceiling is directly above

    # Wall conduits: cable/pipe risers run floor-to-overhead against both flanks.
    for cx in range(30, 160, 18):
        if 86 <= cx <= 115:
            continue
        for z in (34, 52):
            ys = [y for y in range(D + 1, 58) if (cx, y, z) in inside]
            if ys:
                for y in range(min(ys), max(ys) + 1):
                    put(cx, y, z, "pipe2")

    # BOW TRIM - sonar station, forward pipe runs, a little debris
    box(15, 18, D + 1, D + 3, 41, 45, "console"); put(16, D + 1, 43, "ilight")
    box(20, 41, D + 1, D + 1, 31, 32, "pipe"); box(20, 41, D + 1, D + 1, 54, 55, "pipe")
    box(22, 26, D + 1, D + 2, 34, 36, "debris")

    # OBSERVATION LOUNGE - a viewing gallery facing the recessed viewport (south, high z)
    for x in range(48, 74):
        put(x, D + 1, 53, "panel"); put(x, D + 2, 53, "rail")     # bench + rail before the glass
    box(52, 70, D + 1, D + 1, 40, 42, "panel")                    # a central plinth
    put(60, D + 1, 43, "ilight2")                                 # uplight on the window
    overhead(46, 76, (37, 49))

    # CONTROL ROOM - periscope column, mezzanine consoles, helm and chart tables below
    for y in range(D + 1, 62):
        put(101, y, 43, "pipe2")                                  # the scope column up into the sail
    box(95, 105, D + 9, D + 9, 42, 44, "console"); put(100, D + 10, 43, "ilight2")
    box(82, 90, D + 1, D + 2, 38, 40, "console"); box(82, 90, D + 1, D + 2, 46, 48, "console")
    put(86, D + 1, 39, "ilight"); overhead(80, 110, (35, 51))

    # CREW QUARTERS - stacked bunks, a mess table, and the squid inrush at the breach (x114-126)
    for zside in (30, 55):
        box(128, 137, D + 1, D + 1, zside, zside + 1, "bunk")     # lower mattress, on the deck
        box(128, 137, D + 3, D + 3, zside, zside + 1, "bunk")     # upper mattress
        for ex in (128, 137):                                    # end frames tie the bunks together
            box(ex, ex, D + 1, D + 4, zside, zside + 1, "bunk")
    box(129, 135, D + 1, D + 1, 42, 44, "panel"); put(132, D + 1, 43, "ilight")
    box(116, 125, D + 1, D + 3, 42, 54, "debris")                # rubble driven in by the breach
    overhead(112, 139, (36, 50))

    # ENGINE ROOM - machinery banks, the drive-shaft line, and flooding (the derelict aft)
    box(146, 160, D + 1, D + 4, 38, 40, "machine"); box(146, 160, D + 1, D + 4, 46, 48, "machine")
    for x in range(141, 164):
        put(x, D + 5, 43, "pipe2")                               # the drive shaft
        if x % 4 == 0:                                           # shaft bearings down to the deck
            box(x, x, D + 1, D + 4, 43, 43, "machine")
    box(143, 162, D + 6, D + 6, 41, 45, "pipe"); put(150, D + 2, 43, "ilight")
    for q in inside:                                             # flood the aft compartment
        x, y, z = q
        if 141 <= x <= 163 and 14 <= y <= D + 2:
            cells.add(q); parts.setdefault(q, "water")

    # ---- HYPER-DETAIL: the fittings that give each compartment its job ----
    # Bow: two torpedo tubes on the centreline, breeches facing aft, round doors.
    for zc in (39, 47):
        box(16, 26, D + 1, D + 3, zc - 1, zc + 1, "machine")
        box(18, 26, D + 2, D + 2, zc, zc, "debris")             # the bore
        box(26, 26, D + 1, D + 3, zc - 1, zc + 1, "pipe")       # the breech door ring
    # Observation lounge: a dedication plaque set beside the rail, and an overhead cable run.
    box(58, 62, D + 2, D + 2, 52, 52, "console"); put(60, D + 2, 52, "ilight2")
    overhead(49, 73, (40, 44))                                  # cable run hung from the deckhead
    # Control room: captain's chair, a ballast board forward, gauge banks on the aft bulkhead.
    put(86, D + 1, 43, "panel"); box(85, 85, D + 1, D + 3, 43, 43, "machine")   # chair + backrest
    box(79, 79, D + 1, D + 4, 38, 48, "console")               # ballast board (fwd bulkhead face)
    for gz in range(39, 48, 2):
        put(79, D + 2, gz, "ilight")                           # its gauges
    box(111, 111, D + 1, D + 4, 38, 48, "console")            # gauge bank (aft bulkhead face)
    for gz in range(39, 48, 2):
        put(111, D + 3, gz, "ilight")
    # Crew quarters: a locker bank, and torn plating hung around the breach.
    for lz in range(32, 54, 3):
        box(139, 139, D + 1, D + 4, lz, lz, "machine")
    box(115, 126, D + 3, D + 4, 40, 41, "machine")             # peeled deckhead by the hole
    # Engine room: the reactor core - a lit core ringed in iron and copper valves, above the flood.
    box(148, 153, D + 3, D + 6, 41, 45, "machine")
    box(150, 151, D + 4, D + 5, 42, 44, "ilight2")             # the glowing core
    for vx in (147, 154):
        box(vx, vx, D + 3, D + 6, 42, 44, "pipe")             # valve stacks
    return cells, parts


def _corrosion(x, y, z, seed):
    """Dark almost everywhere; brown rust in scattered patches; verdigris only at the wounds.

    The bloom is kept TIGHT (sigma = 0.5 * wound radius) so the green rings each breach as a
    corrosion halo instead of pooling into one soft camo cloud across the mid-hull - the note
    Jack gave twice: the colour has to say 'the sea got in HERE', not 'someone painted a patch'.
    """
    v = 0.34 * hash01(x, y, z, seed) + 0.32 * hash01(x // 4, y // 5, z // 4, seed + 7)
    for wx, wy, wz, wr in WOUNDS:
        d = math.dist((x, y, z), (wx, wy, wz))
        v += 0.90 * math.exp(-(d / (wr * 0.5)) ** 2)
    return v


def _markings(shown):
    """Paint hull number, draft marks and the Prismworks insignia onto the outer south skin.

    These relabel existing surface cells (they add no volume), so the vessel reads as a
    commissioned ship rather than a generic hull - the one C-grade gap in the exterior audit."""
    surf = {}
    for (x, y, z) in shown:
        if z > surf.get((x, y), -1):
            surf[(x, y)] = z
    parts = {}

    def at(x, y, part):
        if (x, y) in surf:
            parts[(x, y, surf[(x, y)])] = part

    def text(s, x0, ytop, part="mark", step=4):
        cx = x0
        for ch in s:
            g = GLYPHS.get(ch)
            if g:
                for gy, row in enumerate(g):
                    for gx, c in enumerate(row):
                        if c == "1":
                            at(cx + gx, ytop - gy, part)
            cx += step

    text("PW-07", 24, 41)                                   # hull number on the bow flank
    text("07", 150, 40)                                     # repeated at the stern
    for yy in range(30, 45):                                # draft marks up the bow stem
        at(14, yy, "mark") if yy % 2 == 0 else None
        if yy % 4 == 0:
            at(15, yy, "mark")
    # Prismworks insignia on the sail: a prismarine prism with an amethyst core.
    cx, cy = 105, 55
    for dx, dy in ((0, -2), (-1, -1), (0, -1), (1, -1), (-2, 0), (-1, 0), (1, 0), (2, 0),
                   (-1, 1), (0, 1), (1, 1), (0, 2)):
        at(cx + dx, cy + dy, "insignia")
    at(cx, cy, "insignia_core")
    return parts


def build(cfg: dict, donors=None) -> Canvas:
    p = {**WRECK, **(cfg or {})}; sx, sy, sz = map(int, p["size"]); seed = int(p["seed"])
    solid = set(); parts = {}; limber = _hull(solid, parts)
    solid = {q for q in solid if 0 <= q[0] < sx and 0 <= q[1] < sy and 0 <= q[2] < sz}
    parts = {q: parts[q] for q in solid}
    interior = bool(p.get("interior")); walk = bool(p.get("walk"))
    if interior:
        shell = _shell(solid, int(p["shell"]))
        icells, iparts = _interior(solid, shell)
        if not walk:                                       # furnish the compartments (skip for greybox)
            fcells, fparts = _furnish(solid - shell)
            for q, pt in fparts.items():
                if pt == "water":
                    if q not in iparts or iparts[q] == "deck":
                        iparts[q] = "water"; icells.add(q)
                else:
                    iparts[q] = pt; icells.add(q)
        parts.update(iparts); shown = shell | icells       # hollow hull + fitted interior
        # Open the crush breach through to the deck: remove the south wall above the floor at the
        # main crater so the torn hole is a real, walkable entrance and the ONLY way in.
        for q in list(shown):
            qx, qy, qz = q
            if 114 <= qx <= 126 and DECK_Y + 1 <= qy <= 41 and 48 <= qz <= 74:
                shown.discard(q); parts.pop(q, None)
    elif p["greybox"]:
        shown = solid                                       # exterior silhouette review, filled
    else:
        shown = _shell(solid, int(p["shell"]))
    if not p["greybox"]:
        parts.update(_markings(shown))                      # hull number, draft marks, insignia
    grey_mode = p["greybox"] or walk

    c = Canvas(sx, sy, sz, donors); grey = c.raw_state("light_gray_wool")
    st = {k: c.raw_state(p[k]) for k in ("hull", "hull_crack", "dark", "dark_crack",
          "cu1", "cu2", "cu3", "cu4", "glass", "crack", "light", "scar",
          "alloy", "optic", "lens", "lantern",
          "i_deck", "i_wall", "i_mezz", "i_rail", "i_pipe", "i_pipe2", "i_machine",
          "i_panel", "i_debris", "i_bunk", "i_lamp", "i_lamp2", "water", "mark", "trim")}
    cracked = {st["hull"]: st["hull_crack"], st["dark"]: st["dark_crack"]}
    counts = {k: 0 for k in ("hull", "viewport", "viewport_frame", "tower", "antenna", "shaft",
              "rotor", "survey_arm", "fin", "scar", "breach", "glass", "corrosion",
              "alloy", "optic", "lens", "lantern")}
    counts["limber"] = limber

    for x, y, z in shown:
        part = parts.get((x, y, z), "hull"); counts[part] = counts.get(part, 0) + 1
        if grey_mode:
            c.put(x, y, z, grey); continue
        if part in IFINISH:                              # the fitted interior
            c.put(x, y, z, st[IFINISH[part]])
            if part in ("ilight", "ilight2"):
                counts["light"] = counts.get("light", 0) + 1
            continue
        if part in ("alloy", "optic", "lens", "lantern"):
            c.put(x, y, z, st[part]); continue          # expensive instrument accents, clean
        if part == "mark":
            c.put(x, y, z, st["mark"]); continue        # hull number / draft marks
        if part == "insignia":
            c.put(x, y, z, st["trim"]); continue        # Prismworks prism
        if part == "insignia_core":
            c.put(x, y, z, st["lens"]); continue        # amethyst core
        if part == "tower" and y >= 62:
            c.put(x, y, z, st["alloy"]); counts["alloy"] += 1; continue   # prismarine bridge coaming
        if part in ("viewport", "viewport_frame"):
            continue                                    # the viewport gets its own pass
        base = st["dark"] if (part in ("tower", "antenna", "shaft", "rotor", "survey_arm", "fin")
                              or y > 43 or (x // 9) % 5 == 0) else st["hull"]
        v = _corrosion(x, y, z, seed)
        rib = part == "hull" and x % 13 == 0                 # a transverse frame line
        if v > 1.32:
            mat = st["cu4"]; counts["corrosion"] += 1        # verdigris, rare, at wound cores
        elif v > 0.98:
            mat = st["cu3"]; counts["corrosion"] += 1        # weathered green, tight rings
        elif v > 0.62:
            mat = st["cu2"]; counts["corrosion"] += 1        # brown rust, scattered - the norm
        elif rib or v > 0.50 or hash01(x * 2, y, z, seed + 13) < 0.13:
            mat = cracked.get(base, base)                    # cracked plating: frame ribs + damage
        else:
            mat = base
        c.put(x, y, z, mat)

    if not grey_mode:
        # The recessed viewport: a corroded frame lip, a mullioned pane grid dished into the
        # flank, a shattered wedge at the top and one dim glow still bleeding from behind it.
        for x, y, z in shown:
            pt = parts.get((x, y, z))
            if pt == "viewport_frame":
                counts["viewport_frame"] += 1
                v = _corrosion(x, y, z, seed)
                c.put(x, y, z, st["cu3"] if v > 0.9 else st["dark"])  # the framed lip of the port
                continue
            if pt != "viewport":
                continue
            counts["viewport"] += 1
            mullion = x % 6 == 0 or y % 6 == 0               # the glazing bars of the grid
            h = hash01(x, y, z, seed + 3)
            if y >= 43 and (h < .55 or (x + y) % 7 == 0):
                c.put(x, y, z, st["crack"])                  # spidered shatter at the top edge
            elif mullion:
                c.put(x, y, z, st["dark"])                   # a real window grid, not TV static
            elif y <= 39 and hash01(x, y, z, seed + 21) < 0.10:
                c.put(x, y, z, st["light"])                  # a lit pane - power in one bay
                counts["light"] = counts.get("light", 0) + 1
            elif h < 0.08:
                c.put(x, y, z, st["crack"])                  # a few cracked panes
            else:
                c.put(x, y, z, st["glass"]); counts["glass"] += 1

        # Jagged illuminated breach rims around the caved craters.
        for cx, cy, cz, rx, ry, rz, zmin in CRUSH:
            for x, y, z in shown:
                if z < zmin - 1:
                    continue
                near = ((x - cx) / (rx + 1)) ** 2 + ((y - cy) / (ry + 1)) ** 2 + ((z - cz) / (rz + 1)) ** 2
                if .85 <= near <= 1.2 and hash01(x, y, z, seed) < .5:
                    c.put(x, y, z, st["cu4"]); counts["breach"] += 1

        # Three sucker-scar rings gouged into the visible south pressure hull.
        for cx, cy, r in ((83, 39, 5), (105, 29, 4), (137, 43, 5)):
            for x in range(cx - r - 1, cx + r + 2):
                for y in range(cy - r - 1, cy + r + 2):
                    if not r - .7 <= math.hypot(x - cx, y - cy) <= r + .7:
                        continue
                    zs = [z for xx, yy, z in shown if xx == x and yy == y
                          and parts.get((xx, yy, z)) == "hull"]
                    if zs:
                        c.put(x, y, max(zs), st["scar"]); counts["scar"] += 1

        # One dying compartment: past the lit panes of the viewport, a faint residual glow also
        # leaks from the main breach. Mostly dark, just enough to read in the void.
        for x, y, z in shown:
            if (110 <= x <= 130 and 29 <= y <= 41 and z >= 58
                    and hash01(x, y, z, seed + 31) < 0.07):
                c.put(x, y, z, st["light"]); counts["light"] = counts.get("light", 0) + 1

    c.world_origin = tuple(map(int, p["at"]))
    c.meta = {"kind": "prismworks_abyssal_wreck", "features_built": counts,
              "reservation": [97505, 100, 80365, 97689, 174, 80454],
              "view_target": [97563, 137, 80435], "public_access": False,
              "purpose": "Lost Prismworks Sounder wreck; evidence of the squid encounter",
              "review_views": ["overlook", "broadside", "bow", "stern", "top", "night"]}
    return c


DEFAULTS = WRECK
