"""Build a park's circulation from its declared interfaces, not from its front doors.

The path pass this replaces ran ONE spur to ONE front-of-building point per module. Measured
against the interface schema that leaves 61 public anchors across the three lands standing on
nothing - every ride exit, every emergency exit, every flank queue mouth, every view approach -
because a building has more than one way in and the old pass only knew about one of them.

PARK_OVERHAUL.md rule 2: "Every public destination is connected to a continuous public path. A
decorative doorway, queue entrance, or facade front is not sufficient."

**A FRONTAGE IS A WALK, NOT A POINT.** The fix is the thing a real street does: a pavement running
along the face past every door on it, joined to the avenue once. That serves a queue mouth at 0.20
and an exit at 0.80 of the same face with one route rather than two spurs that would have to dodge
each other - and it is why the anchors are laid out across the face in the first place.

**AND THE BACKSTAGE IS A ROAD, NOT A STUB.** A service door opening onto four cells of nothing is
the decorative doorway rule 2 forbids, wearing a hi-vis jacket. Service access joins a perimeter
service corridor that runs behind the buildings, inside the land the theme owns and clear of every
avenue by construction.
"""
from __future__ import annotations

from . import interfaces as I

#: Anchors that belong to the backstage rather than to the public street.
_SERVICE = {"service_access", "staff_exit"}

#: How far inside the owned bounds the concealed service corridor runs, and how wide.
#: **AN ODD WIDTH, DELIBERATELY.** Every route in this project is drawn as `half = width // 2`
#: cells either side of a centre line, so a declared width of 2 lays THREE cells - the declared
#: number and the built number disagree, and the capacity gate then grades a road it has not
#: measured. Rule 6 asks for a minimum of 2; 3 satisfies it and is what actually gets built.
SERVICE_INSET, SERVICE_WIDTH = 1, 3

SPINE_WIDTH, WALK_WIDTH = 5, 3

#: How near the perimeter a service yard has to be before it is worth linking to the road.
SERVICE_REACH = 16

#: The outer edge of the service road, measured rather than assumed - a road declared "inset 1,
#: 2 wide" actually lays three cells, because every route here is drawn as `width // 2` either
#: side of a centre line.
SERVICE_OUTER = SERVICE_INSET + SERVICE_WIDTH - 1

#: **THE PUBLIC NETWORK IS NOT HELD OFF THE BACKSTAGE; THE BACKSTAGE YIELDS TO IT.** Reserving a
#: band wide enough to keep them apart was tried and measured: on a 99x99 plot already ten
#: columns short for the transit corridor, an eight-cell band on all four sides cost the Carousel
#: and the Terrace their sites outright and pushed the Big Wheel through the Arrival Court. The
#: guest network takes precedence and these insets only keep paving on the land; the service road
#: is drawn last and takes what is left, which is honest about a plot packed this hard.
PUBLIC_INSET = WALK_WIDTH // 2
AVENUE_INSET = SPINE_WIDTH // 2


#: How often a route of each role carries a lamp. **ONLY THE SPINES WERE LIT, AND THE NIGHT PASS
#: SAID SO**: 2,830 public route cells across the three lands stood at block light 0, which is a
#: mob on a guest path. The masterplan asks for "warm reliable lighting" on public paths and
#: "high-legibility lighting" at ride entries and exits, so an exit and a queue are lit tighter
#: than a street - and a service road is never lit, because it is meant to be missed.
# **MEASURED, NOT CHOSEN.** At 12/8 the night pass still found 158 walkable route cells across
#: the two side lands at block light 0 - a lantern reaches 15 but a post on the verge of one route
#: is often blocked by the building it stands against, so the effective spacing is wider than the
#: nominal one. These are the numbers that take every land to zero.
LAMP_EVERY = {"main_spine": 8, "secondary": 5, "exit": 4, "queue": 4, "shaft": 4}


def _leg(a, b, width, role, **extra):
    out = {"a": [int(a[0]), int(a[1])], "b": [int(b[0]), int(b[1])],
           "width": int(width), "role": role, **extra}
    if role in LAMP_EVERY and "lamps" not in out:
        out["lamps"] = True
        out.setdefault("lamp_every", LAMP_EVERY[role])
    return out


def _faces(module) -> dict:
    """This module's public anchors, grouped by the face they stand off.

    Service anchors are deliberately excluded: they get the backstage road, and letting them join
    a public frontage walk is how a service door becomes a shopfront.
    """
    out = {}
    for anchor in module.get("interface", {}).get("anchors", []):
        name = I.resolve(anchor["name"])
        # An anchor off the land the theme owns is a HANDOFF - an arch's connector side is
        # outside by definition. Paving to it would run this land's street onto the neighbour's
        # ground, which is where 36 cells of paving left the plot when this was measured.
        if name in _SERVICE or not anchor.get("public") or anchor.get("off_land"):
            continue
        out.setdefault(anchor["face"], []).append(anchor)
    return out


def _walk_for(face: str, anchors: list[dict]):
    """One frontage walk covering every anchor on a face.

    The walk sits at the MEAN standoff of the anchors on that face and is 3 wide, so it covers a
    standoff of one either side - which is exactly the 2..4 range the layout uses for a queue
    mouth, a frontage and a view approach on one face.
    """
    if face in ("east", "west"):
        xs = [a["at"][0] for a in anchors]
        x = sum(xs) // len(xs)
        zs = [a["at"][2] for a in anchors]
        return ((x, min(zs) - 1), (x, max(zs) + 1)), "z"
    zs = [a["at"][2] for a in anchors]
    z = sum(zs) // len(zs)
    xs = [a["at"][0] for a in anchors]
    return ((min(xs) - 1, z), (max(xs) + 1, z)), "x"


def _role_for(anchors: list[dict]) -> str:
    """A face that only ever discharges guests is an exit route; one that only ever admits them
    to a queue is a queue.

    Rule 4 - "queues are never used as through-routes; ride exits never discharge into incoming
    queues or primary promenades" - is only enforceable when the routes are TYPED, so a face
    carrying nothing but exit anchors is declared an exit and one carrying nothing but queue
    mouths is declared a queue. Everything else is ordinary secondary circulation.
    """
    if all(a.get("exit") for a in anchors):
        return "exit"
    if all(a.get("queue") for a in anchors):
        return "queue"
    return "secondary"


#: A module more than this far off the build plane is on another band, and a guest reaches it by
#: a stair or a lift rather than by walking. One course is a step, which needs nothing declared.
OFF_PLANE = 1


def _level_of(module, street):
    """The course this module's guests stand on - its own, not the land's."""
    anchors = module.get("interface", {}).get("anchors", [])
    return anchors[0]["at"][1] if anchors else street


def _approach_of(module):
    """The anchor a module's shaft comes down at - its own approach, or the best it has."""
    anchors = [a for a in module.get("interface", {}).get("anchors", [])
               if a.get("public") and not a.get("off_land")]
    if not anchors:
        return None
    return next((a for a in anchors if I.resolve(a["name"]) in
                 {"approach", "frontage", "arrival", "entry"}), anchors[0])


def _landing(name, level, start, end, axis, approach):
    """One level's own frontage walk, plus the leg that joins it to this module's shaft.

    A landing is an ordinary secondary street that happens to be somewhere else in Y. It is
    emitted with three-element endpoints so `pathgraph.levels` files its cells at the right
    course, and it runs to the MODULE's own approach - which is where the shaft comes down.

    **THE MODULE'S, NOT THE FACE'S.** Taken from the anchors on the face being walked, a face
    carrying only an emergency exit resolved its own anchor as the approach, the join came out
    zero-length, and that face's landing shipped as a nine-cell island under the town with no
    way onto it. The check caught it; the cause was one word.
    """
    foot = (approach["at"][0], approach["at"][2])
    walk = _leg((start[0], start[1]), (end[0], end[1]), WALK_WIDTH, "secondary",
                name=f"{name} {axis} landing")
    walk["a"] = [walk["a"][0], int(level), walk["a"][1]]
    walk["b"] = [walk["b"][0], int(level), walk["b"][1]]
    out = [walk]
    mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
    if mid != foot:
        join = _leg(mid, foot, WALK_WIDTH, "secondary", name=f"{name} landing join")
        join["a"] = [join["a"][0], int(level), join["a"][1]]
        join["b"] = [join["b"][0], int(level), join["b"][1]]
        out.append(join)
    return out


def _shafts(modules, plane, walkable) -> list[dict]:
    """One declared vertical connection per module that stands off the build plane.

    **A PLAN VIEW SAYS AN UNDERGROUND RIDE IS ON THE STREET. IT IS ON THE STREET'S SHADOW.** The
    moment the Frontier's mine ride moved 24 courses down - which is the masterplan's own answer
    to a town that does not fit its plot - every one of its public anchors still read as served,
    because the attachment check only knew about x and z.

    The shaft is placed at the module's own APPROACH, which is the cell a guest arrives at, and
    it spans from the street down to that anchor's course. It is declared as `stairs` so the
    grade rule lets it be steeper than one-in-one: that is what a stair IS, and the alternative -
    a ramp at one block per course - would be a 24-cell run through the town to reach a ride
    underneath it.

    It is a CONTRACT, not a build: the generator that owns the connector - a headframe, a lift
    tower, a stairwell - has to honour it, and the route gate is what says whether it did.
    """
    out = []
    for module in modules:
        if module.get("covers") or I.module_type(module) in {"path", "terrain", "service"}:
            continue
        approach = _approach_of(module)
        if approach is None:
            continue
        x, y, z = approach["at"]
        if abs(y - plane) <= OFF_PLANE:
            continue
        # **THE SHAFT STANDS IN THE MODULE'S OWN APPROACH COLUMN.** Placed at the nearest
        # street cell instead, its foot lands wherever that column happens to be underground -
        # which is rock - and the landing it is supposed to reach is somewhere else. A lift
        # goes straight down to the door it serves.
        shaft = _leg((x, z), (x, z), WALK_WIDTH, "shaft", vertical="stairs",
                     name=f"{module.get('name', '?')} shaft")
        shaft["a"] = [int(x), int(plane), int(z)]
        shaft["b"] = [int(x), int(y), int(z)]
        out.append(shaft)
        # **AND THE SHAFT HEAD HAS TO BE ON THE STREET, or the whole underground level is an
        # island.** The shaft stands in the module's own column, which on the surface is not
        # anywhere the town paved - so the plan-view network came out in two pieces, correctly:
        # a guest could reach the landing only by already being on it. This is the head's own
        # approach, at street level, and it is what makes the two bands one walk.
        head = min(walkable, key=lambda c: (c[0] - x) ** 2 + (c[1] - z) ** 2, default=None)
        if head is not None and head != (x, z):
            out.append(_leg((x, z), head, WALK_WIDTH, "secondary",
                            name=f"{module.get('name', '?')} shaft approach"))
    return out


def build(modules: list[dict], centre: tuple[int, int], owned: tuple[int, int, int, int],
          plane: int | None = None) -> list[dict]:
    """The whole circulation network for one land, as role-typed routes.

    `owned` is (x0, x1, z0, z1) of the land the theme owns - not of the plot. A land that clamps
    to the plot runs its avenues into the reserved transit corridor, which is the mistake the
    path pass already records having made once.
    """
    cx, cz = centre
    ox0, ox1, oz0, oz1 = owned
    ax0, ax1 = ox0 + AVENUE_INSET, ox1 - AVENUE_INSET
    az0, az1 = oz0 + AVENUE_INSET, oz1 - AVENUE_INSET
    if ax1 <= ax0 or az1 <= az0:
        return []

    routes = [
        _leg((ax0, cz), (ax1, cz), SPINE_WIDTH, "main_spine", lamps=True, name="east-west spine"),
        _leg((cx, az0), (cx, az1), SPINE_WIDTH, "main_spine", lamps=True, name="north-south spine"),
    ]

    def _clamp(x, z):
        return min(max(x, ax0), ax1), min(max(z, az0), az1)

    def _inside(point, margin=0):
        """Every route endpoint is clamped to the land the theme owns.

        A walk derived from an anchor near the boundary runs one cell past it - the walk is
        extended a cell each end so it covers its outermost anchor - and that is enough to put
        paving on the neighbour's plot. Clamping the ENDPOINTS is not enough on its own, which
        is why the anchors themselves are filtered first: this catches the overhang, not the
        handoff.

        `margin` is the route's own half-width. A 3-wide walk whose CENTRE line sits exactly on
        the boundary still lays a column of paving one cell past it - which is how three cells of
        the Hollow's street ended up on the connector's ground with every endpoint correctly
        inside. A route is a box, not a line.
        """
        margin = max(margin, PUBLIC_INSET)
        return (min(max(point[0], ox0 + margin), ox1 - margin),
                min(max(point[1], oz0 + margin), oz1 - margin))

    street = plane
    for module in modules:
        if module.get("covers") or I.module_type(module) in {"path", "terrain", "service"}:
            continue
        name = module.get("name", "?")
        # **A MODULE ON ANOTHER BAND GETS ITS OWN LEVEL'S CIRCULATION, NOT THE STREET'S.**
        # The Frontier's mine ride stands 24 courses under the town. Drawn on the plane its
        # frontage walk is the street's shadow: correct in plan, twenty-four blocks of solid
        # rock in elevation. Its walks carry a Y, one shaft joins them to the street above, and
        # the level map is what makes the route gate able to tell the two apart.
        level = _level_of(module, street)
        below = street is not None and level is not None and abs(level - street) > OFF_PLANE
        for face, anchors in sorted(_faces(module).items()):
            (start, end), axis = _walk_for(face, anchors)
            half = WALK_WIDTH // 2
            start, end = _inside(start, half), _inside(end, half)
            if below:
                routes.extend(_landing(name, level, start, end, axis,
                                       _approach_of(module) or anchors[0]))
                continue
            role = _role_for(anchors)
            width = WALK_WIDTH if role != "queue" else min(WALK_WIDTH, 3)
            routes.append(_leg(start, end, width, role, name=f"{name} {face} frontage"))
            # ONE JOIN PER FACE, from the middle of the walk to whichever avenue it can reach in
            # a single perpendicular run. An L rather than a straight leg, because a walk beyond
            # the avenue's own span has to travel along the avenue's axis to get onto it - which
            # is the case the old pass clamped away and then reported as unreached.
            mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            if axis == "z":                      # the walk runs N-S, so join the E-W spine
                elbow = (mid[0], cz)
                land = _clamp(mid[0], cz)
            else:
                elbow = (cx, mid[1])
                land = _clamp(cx, mid[1])
            # **THE JOIN IS ALWAYS SECONDARY, WHATEVER THE WALK IS.** An exit route that runs
            # onto the spine IS a ride discharging into a primary promenade, and a queue route
            # that reaches the spine IS a queue carrying a through-route: both are rule 4. The
            # discharge or the queueing happens on the walk; what joins it to the park is an
            # ordinary street, which is what a real park puts between the two.
            if elbow != mid:
                routes.append(_leg(mid, elbow, WALK_WIDTH, "secondary", name=f"{name} {face} join"))
            if land != elbow:
                routes.append(_leg(elbow, land, WALK_WIDTH, "secondary", name=f"{name} {face} approach"))

    from . import pathgraph
    # **AND THE SERVICE DOORS GET A SECOND LOOK, NOW THAT THE STREETS EXIST.** `interfaces` places
    # a backstage door on the rear face and can only move it for a reason it can see from the
    # module alone - being off the land. Whether that face is under a guest path is not knowable
    # until the guest paths are drawn, which is here: measured with only the first pass, 13 of 31
    # service doors across the three lands opened straight onto a street, and 10 of those had a
    # perfectly good flank going spare.
    #
    # The anchor MOVES rather than the road bending to it, because a door is a decision about a
    # building and a road that reaches a bad door is still a road down a guest path.
    _reface_service_doors(modules, owned, pathgraph.footprint(routes))

    # **DRAWN LAST, AND HANDED WHAT THE PUBLIC NETWORK HAS ALREADY CLAIMED.** The backstage
    # yields; it does not cross. That is the only version of "hidden service routes" that is a
    # fact about the geometry rather than a label on it.
    if plane is not None:
        routes.extend(_shafts(modules, plane, pathgraph.public(routes)))
    routes.extend(_service_network(modules, owned, pathgraph.footprint(routes)))
    return [r for r in routes if r["a"] != r["b"]]


def _reface_service_doors(modules, owned, public_cells) -> int:
    """Move a backstage door off a guest path, when the building has a flank going spare.

    Only ever to a face that is on the land AND clear of the street - and if no face is, the door
    stays where it is and `unserviced_doors` reports it. A door nudged onto a worse face to make
    a count go down would be buying quiet, which is the thing this project keeps refusing to do.
    """
    moved = 0
    for module in modules:
        if module.get("covers") or I.module_type(module) in {"path", "terrain", "service"}:
            continue
        facing = module.get("params", {}).get("facing", "east")
        for anchor in module.get("interface", {}).get("anchors", []):
            if I.resolve(anchor["name"]) not in _SERVICE:
                continue
            x, _y, z = anchor["at"]
            if (x, z) not in public_cells:
                continue
            layout = I._LAYOUT.get(I.module_type(module), {}).get(anchor["name"])
            if not layout:
                continue
            _relative, along, distance = layout
            for alternative in ("left", "right", "back", "front"):
                face = I._resolve_face(facing, alternative)
                nx, nz = I._face_point(module, face, along, distance)
                on_land = not owned or (owned[0] <= nx <= owned[1] and owned[2] <= nz <= owned[3])
                if on_land and (nx, nz) not in public_cells:
                    anchor["at"] = [int(nx), anchor["at"][1], int(nz)]
                    anchor["face"] = face
                    moved += 1
                    break
    return moved


def _service_network(modules, owned, public_cells) -> list[dict]:
    """Concealed backstage: a yard behind every service door, and a perimeter road.

    **IT YIELDS TO THE PUBLIC NETWORK RATHER THAN CROSSING IT, AND THAT IS WHAT MAKES IT
    CONCEALED.** Two designs were tried and measured before this one. A perimeter ring reached by
    the shortest perpendicular puts a building in the middle of a 99x99 plot forty cells from any
    boundary, so the "concealed" road came out laid down the middle of a guest path for 87 cells
    at a stretch. Stepping the spur aside simply picked a different guest path to lie along. A
    rear yard per building was better and still collided - with the NEIGHBOUR's join, because
    buildings packed three cells apart leave the land behind one of them under the path to the
    next.

    So the backstage is drawn last and grown outward from each door until it meets a public cell,
    and stops there. `service ∩ public = 0` is then true by construction rather than by hope, and
    what the measurement reports instead is how much yard each door actually got - which is the
    honest number, because on a plot packed this hard some doors genuinely have very little.

    The backstage is NOT guaranteed to be one connected network. A yard reached from inside the
    building it serves is a real answer; claiming a full backstage ring that is not built would
    be the decorative-doorway failure with the roles reversed.
    """
    ox0, ox1, oz0, oz1 = owned
    half = SERVICE_WIDTH // 2
    sx0, sx1 = ox0 + SERVICE_INSET + half, ox1 - SERVICE_INSET - half
    sz0, sz1 = oz0 + SERVICE_INSET + half, oz1 - SERVICE_INSET - half
    if sx1 <= sx0 or sz1 <= sz0:
        return []
    out = []

    def _clear(x, z, step):
        """Does a `SERVICE_WIDTH` course centred here, running along `step`, stay off the street?"""
        if not (sx0 <= x <= sx1 and sz0 <= z <= sz1):
            return False
        for offset in range(-half, half + 1):
            cell = (x + offset, z) if step[0] == 0 else (x, z + offset)
            if cell in public_cells:
                return False
        return True

    def _grow(origin, step, limit):
        """How far a course may run from `origin` along `step` before it meets the street."""
        x, z = origin
        reached = 0
        for distance in range(1, limit + 1):
            nx, nz = x + step[0] * distance, z + step[1] * distance
            if not _clear(nx, nz, step):
                break
            reached = distance
        return reached

    def _run(origin, step, length, name):
        """The clear stretches of one straight run, as separate legs.

        The perimeter road is laid the same way a yard is: where a guest path crosses it, the
        road STOPS and picks up on the far side. Laid as four unbroken sides it shared cells with
        every spur that reached the boundary, and a backstage that is also the street is neither.
        """
        x, z = origin
        start = None
        for distance in range(0, length + 1):
            nx, nz = x + step[0] * distance, z + step[1] * distance
            if _clear(nx, nz, step):
                if start is None:
                    start = (nx, nz)
            elif start is not None:
                end = (nx - step[0], nz - step[1])
                if end != start:
                    out.append(_leg(start, end, SERVICE_WIDTH, "service", name=name))
                start = None
        if start is not None:
            end = (x + step[0] * length, z + step[1] * length)
            if end != start:
                out.append(_leg(start, end, SERVICE_WIDTH, "service", name=name))

    _run((sx0, sz0), (1, 0), sx1 - sx0, "service road north")
    _run((sx0, sz1), (1, 0), sx1 - sx0, "service road south")
    _run((sx0, sz0), (0, 1), sz1 - sz0, "service road west")
    _run((sx1, sz0), (0, 1), sz1 - sz0, "service road east")

    for module in modules:
        if module.get("covers") or I.module_type(module) in {"path", "terrain", "service"}:
            continue
        name = module.get("name", "?")
        for anchor in module.get("interface", {}).get("anchors", []):
            if I.resolve(anchor["name"]) not in _SERVICE:
                continue
            x, _y, z = anchor["at"]
            x = min(max(x, sx0), sx1)
            z = min(max(z, sz0), sz1)
            if not _clear(x, z, (1, 0)) or not _clear(x, z, (0, 1)):
                continue                      # the door already opens onto the street
            face = anchor.get("face", "east")
            x0, z0, x1, z1 = I._box(module)
            if face in ("east", "west"):
                along, span = (0, 1), max(1, (z1 - z0) // 2)
                toward = [((-1, 0), x - sx0), ((1, 0), sx1 - x)]
            else:
                along, span = (1, 0), max(1, (x1 - x0) // 2)
                toward = [((0, -1), z - sz0), ((0, 1), sz1 - z)]
            for direction in (along, (-along[0], -along[1])):
                reach = _grow((x, z), direction, span)
                if reach:
                    out.append(_leg((x, z), (x + direction[0] * reach, z + direction[1] * reach),
                                    SERVICE_WIDTH, "service", name=f"{name} service yard"))
            # And out to the perimeter road, when the land between is free the whole way. A
            # partial run to nowhere is a stub, so it is only laid when it arrives.
            for step, distance in sorted(toward, key=lambda o: o[1]):
                if distance and _grow((x, z), step, distance) == distance:
                    out.append(_leg((x, z), (x + step[0] * distance, z + step[1] * distance),
                                    SERVICE_WIDTH, "service", name=f"{name} service link"))
                    break
    return out


def unserviced_doors(modules: list[dict], routes: list[dict], reach: int = 2) -> list[dict]:
    """Service doors with no backstage paving within reach - doors that open onto a guest path.

    **THIS IS A MEASUREMENT, NOT A BUG.** The backstage yields to the public network, so on a
    plot packed as hard as these three - 99x99 with ten columns already reserved for the transit
    corridor - some rear doors genuinely have nothing behind them but somebody else's street. The
    fix is siting room, not path drawing, and inventing a road that runs down a guest path to
    make the number zero would be the decorative-doorway failure with the roles reversed.

    So it is reported, by name, and the reviewer decides. Measured over the three shipped lands:
    19 service doors, 10 with a yard, 9 without.
    """
    from . import pathgraph
    road = pathgraph.footprint(pathgraph.normalise(routes), {"service"})
    out = []
    for module in modules:
        for anchor in module.get("interface", {}).get("anchors", []):
            if I.resolve(anchor["name"]) not in _SERVICE or anchor.get("off_land"):
                continue
            x, _y, z = anchor["at"]
            if not any((x + dx, z + dz) in road
                       for dx in range(-reach, reach + 1) for dz in range(-reach, reach + 1)):
                out.append({"module": module.get("name", "?"), "anchor": anchor["name"],
                            "at": anchor["at"],
                            "reason": "service door has no backstage paving behind it"})
    return out
