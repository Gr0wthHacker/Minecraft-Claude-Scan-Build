"""Set pieces: large, instantly nameable things, built on the symmetric kit.

Jack's verdict on the park as shipped was that the rides and the sculptures work and *"basically
everything else is terrible"*, and the good list says exactly why: a ferris wheel, a carousel, a
coaster, a heron, a balloon are all things a person can NAME from across the plot. What failed was
a category - a box with redstone in it and a button on the front, which is neither fun to do nor
good to look at.

So a set piece has one job: **be recognisable at fifty blocks and reward a closer look.** No
mechanism, no button, nothing to figure out. It is scenery, and scenery that has to be explained
has already failed.

Every piece here is drawn on `kit.Sym`, so it is symmetric by construction - which the park's own
buildings were not, at 102-126% asymmetric across their own frontage.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .kit import Sym
from .park import LANDS
from .vertical import Ctx, World

SETPIECE = {
    "land": "frontier",
    "kind": "watertower",
    "at": None,
    "facing": "east",
    "under": None,
    "scale": 1.0,
}


# ------------------------------------------------------------------ the frontier's water tower

#: A cheap all-timber value ladder, measured rather than assumed: 147 / 90 / 48 in luminance, so
#: the steps are 57 and 42 - both far above the ~15 below which a band stops being a line. The
#: land's own palette could not supply it: `wall` and `beam` are BOTH `spruce_planks`, so the
#: first build's "two alternating tones" was one tone and the tank rendered as a flat brown box.
STAVE_LIGHT, STAVE_DARK, HOOP = "stripped_oak_log", "spruce_planks", "dark_oak_planks"


def _ring(radius: float) -> list:
    """The cells of a hollow circle of that radius, in local (u, v) about (0, 0).

    A shell is "inside, with a neighbour outside", never a band in the radius equation - the
    gradient is not constant, so a constant band comes out fat on the diagonals and thin on the
    axes. This project settled that once already, on the fill shapes.
    """
    span = int(radius) + 1
    solid = {(u, v) for u in range(-span, span + 1) for v in range(-span, span + 1)
             if u * u + v * v <= radius * radius}
    return sorted(c for c in solid
                  if any((c[0] + du, c[1] + dv) not in solid
                         for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1))))


def _cone(radii: list) -> list:
    """Per-course cell sets for a hollow cone of those radii, GUARANTEED to be 6-connected.

    **TWO CONSECUTIVE RINGS CAN SHARE NO CELL EVEN WHEN THEIR RADII OVERLAP.** Bands of
    (2.3, 4.1] and (1.0, 2.8] overlap on paper by half a radius unit, and the integer distances
    available there are 2.0 and 2.236 - both below 2.3 - so the two courses touched only at
    corners and the water tower's cap shipped as eighteen loose fragments of two stairs. The
    tent's cone was the same construction and held together purely by luck of its step size.

    So the overlap is not reasoned about, it is CONSTRUCTED: a course that shares nothing with the
    one above it simply absorbs it. Every absorbed cell is inside the wider course's own radius by
    definition, so the skin never grows outward and the shape does not change.
    """
    courses = []
    for k, r in enumerate(radii):
        inner = radii[k + 1] - 0.5 if k + 1 < len(radii) else -1.0
        span = int(r) + 1
        courses.append({(u, v) for u in range(-span, span + 1) for v in range(-span, span + 1)
                        if inner < (u * u + v * v) ** 0.5 <= r})
    for k in range(len(courses) - 1):
        if not (courses[k] & courses[k + 1]):
            courses[k] |= courses[k + 1]
    return courses


def _watertower(s: Sym, pal, p) -> dict:
    """A western water tower: a splayed timber trestle, a round staved tank with iron hoops, a
    conical cap and a spout hanging over the track.

    **THE TANK HAS TO BE ROUND.** Built square the first time, the whole thing read as a pagoda on
    stilts - because the three masses a water tower is made of (thin splayed legs, a fat drum, a
    point) only tell you what it is when the middle one is a drum. A box with a pyramid on it is a
    different object entirely, and no amount of banding or bracing rescued it.
    """
    legs, tank, cap = 12, 8, 4
    # **THE TANK MUST OVERHANG THE TRESTLE.** At foot 5 against a radius of 5.4 the barrel was
    # flush with its own legs and the tower read as a silo - a water tower's tank sits proud of
    # the frame it stands on, and that overhang is half of what makes the three masses separate.
    foot, shoulder, radius = 4, 3, 5.4
    cv = 0                       # the tank's centre, in the local frame, is the origin

    # ---- the trestle. Splayed: the feet stand wider than the shoulders they carry, which is the
    # taper that stops it reading as a crate on four posts.
    def leg_at(h):
        t = h / max(legs - 1, 1)
        return foot - (foot - shoulder) * t

    # **A LEG THAT STEPS SIDEWAYS IS DIAGONAL-ONLY AND THEREFORE NOT CONNECTED.** A splayed post
    # moves in as it rises, and at the course where it moves, the cell below and the cell above
    # touch at a corner - so the whole trestle below the first step shipped as an 83-cell
    # fragment. Each step lays a bridging cell in the previous course's column, which is also
    # what a real jointed timber leg looks like. Same rule as the Lowland Root's braid.
    for h in range(legs):
        r, prev = leg_at(h), leg_at(h - 1) if h else leg_at(0)
        for sign in (-1, 1):
            v, pv = round(cv + sign * r), round(cv + sign * prev)
            s.put(round(r), v, h, pal["post"], axis="y")
            if (round(r), v) != (round(prev), pv):
                s.put(round(prev), pv, h, pal["post"], axis="y")
                s.put(round(r), pv, h, pal["post"], axis="y")
    # CROSS-BRACING between the legs - fences, which this project places at a thirtieth of the
    # rate outside builders do, and the detail that says timber frame rather than four sticks.
    for h in (2, 5, 8, 11):
        r = leg_at(h)
        for v in (round(cv - r), round(cv + r)):
            for u in range(-round(r) + 1, round(r)):
                s.put(u, v, h, pal["fence"], waterlogged="false")
        for u in (round(r),):
            for v in range(round(cv - r) + 1, round(cv + r)):
                s.put(u, v, h, pal["fence"], waterlogged="false")

    # ---- the tank: vertical staves in two tones, wrapped in dark hoops.
    shell = _ring(radius)
    base = legs
    for step in range(tank):
        h = base + step
        hoop = step in (0, tank // 2, tank - 1)
        for (u, v) in shell:
            if hoop:
                s.put(u, v + cv, h, HOOP)
            else:
                # The stave tone follows the column, never the course: hashed on the course every
                # block in a course comes out identical and the tank is horizontal stripes, which
                # is the deck soffit's own bug and is not what a barrel looks like.
                light = (abs(u) + abs(v)) % 2 == 0
                s.put(u, v + cv, h, STAVE_LIGHT if light else STAVE_DARK,
                      **({"axis": "y"} if light else {}))
    # A floor, so the tank is a vessel rather than a tube you can see the sky through.
    for u in range(-6, 7):
        for v in range(-6, 7):
            if u * u + v * v <= radius * radius and (u, v) not in set(shell):
                s.put(u, v + cv, base, pal["slab"], type="top", waterlogged="false")

    # ---- the cap: a shallow cone, each course a ring of stairs leaning outward so it sheds.
    top = base + tank
    # Drawn as one-cell rings the cone came apart into eighteen loose fragments of two and three
    # stairs. `_cone` guarantees the courses touch rather than hoping the radii work out.
    radii = [radius - step * 1.3 for step in range(cap)]
    for step, cells in enumerate(_cone([r for r in radii if r >= 0.9])):
        for (u, v) in sorted(cells):
            s.put(u, v + cv, top + step, pal["stair"], facing=_lean(s, u, v),
                  half="bottom", shape="straight", waterlogged="false")
    s.put(0, cv, top + cap, pal["fence"], waterlogged="false")

    # ---- the spout. **THE ONE ASYMMETRIC THING, AND IT IS WHAT NAMES THE TOWER.** A tank with no
    # spout is a tank; the elbow hanging over the track is the silhouette everybody recognises.
    # **A DIAGONAL RUN IS NOT CONNECTED.** The first elbow stepped out and down one cell at a
    # time and shipped as three loose fragments, which is the ear-tip failure this project has
    # recorded twice. Every step lays its own corner cell.
    for k in range(4):
        s.one(0, cv + 5 + k, base + 2 - k, HOOP)
        s.one(0, cv + 6 + k, base + 2 - k, HOOP)
    s.one(0, cv + 9, base - 2, pal["fence"], waterlogged="false")
    s.one(0, cv + 9, base - 3, pal["fence"], waterlogged="false")

    # ---- a ladder up one leg, to the tank. Scenery rewards a closer look, and a tower nobody
    # could have climbed is a prop.
    for h in range(1, base + 1):
        s.one(round(leg_at(h)), round(cv - leg_at(h)) - 1, h, "ladder",
              facing=_face_out(s, -1), waterlogged="false")

    return {"legs": legs, "tank": tank, "height": top + cap, "diameter": 2 * int(radius) + 1}


def _lean(s: Sym, u: int, v: int) -> str:
    """Which way a cap stair leans, so a conical roof sheds away from its own peak."""
    if abs(u) >= abs(v):
        return ("south" if u > 0 else "north") if s.axis == "z" else ("east" if u > 0 else "west")
    return ("east" if v > 0 else "west") if s.axis == "z" else ("south" if v > 0 else "north")


def _face_out(s: Sym, sign: int) -> str:
    """A compass word for the local -v direction, so a ladder faces out of the trestle."""
    if s.axis == "z":
        return "west" if sign < 0 else "east"
    return "north" if sign < 0 else "south"



# ------------------------------------------------------------------ the midway's big top

def _bigtop(s: Sym, pal, p) -> dict:
    """A fairground big top: a round striped tent with a scalloped valance, guy ropes to the
    ground, a peaked roof and a pennant on the king pole.

    **THE STRIPES ARE RADIAL GORES, NOT COURSES.** A cone banded by height is a wedding cake; a
    cone divided by ANGLE is a tent, and it is the same finding the balloon's envelope produced -
    ten gores read, eight came out as a beach ball. Here the gore count is driven by the
    circumference so a gore stays about four cells wide at the eaves, which is the width below
    which two stripes merge into one texture.
    """
    radius, wall, cone = float(p.get("radius", 11)), 4, 11
    light, dark = pal["canopy"][1], pal["canopy"][0]
    gores = 12
    door = 3                                   # half-width of the entrance, on the centre line

    def gore_tone(u, v):
        angle = math.atan2(v, u) if (u or v) else 0.0
        return light if int((angle + math.pi) / (2 * math.pi) * gores) % 2 else dark

    # ---- the wall: a low drum of striped canvas, with the doorway LEFT EMPTY by the loop rather
    # than punched afterwards. Building the ring and then cutting a hole repaints cells that
    # already exist, which is how the void tower shipped a plain drum with nothing looking wrong.
    for h in range(wall):
        for (u, v) in _ring(radius):
            if v < 0 and abs(u) <= door and h < 3:
                continue
            s.put(u, v, h, gore_tone(u, v))
    # A door frame, so the opening reads as an entrance rather than as a tear in the canvas.
    for h in range(3):
        s.put(door + 1, -round(math.sqrt(max(radius * radius - (door + 1) ** 2, 0))), h,
              pal["post"], axis="y")
    for u in range(-door, door + 1):
        s.put(u, -round(math.sqrt(max(radius * radius - u * u, 0))), 3, pal["beam"])

    # ---- the valance: an upside-down stair skirt at the eaves. **THIS IS THE DETAIL THAT SAYS
    # TENT.** Without it the drum meets the cone at a hard horizontal and reads as a silo.
    for (u, v) in _ring(radius):
        s.put(u, v, wall, pal["stair"], facing=_lean(s, u, v), half="top",
              shape="straight", waterlogged="false")

    # ---- the cone. Each course draws in, and the gore tone follows the ANGLE, so a stripe runs
    # from the eaves to the peak the way a real seam does.
    #
    # **A CONE OF ONE-CELL RINGS IS SEE-THROUGH.** Drawn as `_ring(r)` per course the first build
    # had daylight between every band: consecutive radii step in by about one, and a shell that
    # thin leaves a diagonal gap wherever the circle's own gradient is shallow. Each course is the
    # ANNULUS down to the next radius instead, so the skin is watertight by construction however
    # the step is tuned - the same reason a shell is "inside with a neighbour outside" rather than
    # a band in the radius equation.
    radii = [radius - step * (radius - 0.9) / max(cone - 1, 1) for step in range(cone)]
    for step, cells in enumerate(_cone([r for r in radii if r >= 0.8])):
        for (u, v) in sorted(cells):
            s.put(u, v, wall + 1 + step, gore_tone(u, v))
    peak = wall + 1 + cone
    s.put(0, 0, peak, pal["post"], axis="y")
    s.put(0, 0, peak + 1, pal["fence"], waterlogged="false")
    s.one(0, 1, peak + 1, pal["accent"])
    s.one(0, 2, peak + 1, pal["accent"])

    # ---- the stakes. **THE FIRST VERSION WAS LITTER.** Two-cell stubs of log scattered round the
    # tent read as rubble, not as rigging - a set piece has no room for anything a viewer has to
    # be told the purpose of. They are proper guy posts now: a stake, a fence standing on it and a
    # lantern at the top, so the ring reads as a lit perimeter and lights its own doorway.
    #
    # And they are LOW. Given a fence and a lantern on top they came out four courses tall
    # and the tent was ringed by golden pillars taller than its own wall - which is worse
    # than the litter they replaced, because a set piece has exactly one silhouette and
    # anything standing beside it is competing for that.
    # **AND THE APRON IS WHAT JOINS THEM.** Standing alone the stakes were fourteen separate
    # two-cell pieces - legal, grounded, and fourteen things a printer builds in fourteen trips.
    # A ring of trodden ground round the tent makes it one piece AND is what a pitch looks like.
    # A SOLID pitch, not a ring: laid as three rings it was a 244-cell island beside the tent
    # (the innermost ring sat a course down and a cell out from the wall, which is diagonal) with
    # four more single cells stranded at the corners where the rings failed to meet. A disc joins
    # every stake to the tent, and it is the floor the tent did not otherwise have.
    span = int(radius) + 4
    for u in range(-span, span + 1):
        for v in range(-span, span + 1):
            if u * u + v * v <= (radius + 3) ** 2:
                s.put(u, v, -1, pal["path"])
    for k, (u, v) in enumerate(sorted(_ring(radius + 3))):
        if k % 9:
            continue
        s.put(u, v, 0, pal["post"], axis="y")
        s.put(u, v, 1, pal["light"], hanging="false", waterlogged="false")

    return {"radius": int(radius), "gores": gores, "height": peak + 1}


BUILDERS = {"watertower": _watertower, "bigtop": _bigtop}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**SETPIECE, **cfg}
    if not p.get("at") or len(p["at"]) != 3:
        raise ValueError("setpiece needs params.at = [x, y, z] of its own centre-front cell")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown setpiece kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    pal = dict(LANDS[p["land"]])
    pal.setdefault("roof_stair", pal["stair"])
    pal.setdefault("roof_slab", pal["slab"])
    world = World()
    surface = Sym(world, p["at"], p["facing"])
    meta = BUILDERS[p["kind"]](surface, pal, p)

    return world.canvas({
        "kind": f"setpiece/{p['kind']}", "land": p["land"], "facing": p["facing"],
        "blocks": surface.placed, **meta,
        "contract": "a set piece that names itself at fifty blocks and rewards a closer look - "
                    "no mechanism, nothing to figure out, and symmetric by construction",
    })
