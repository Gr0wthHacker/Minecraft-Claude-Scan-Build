"""Typed interfaces for park modules: named anchors, declared links, and the checks over them.

`park_contracts` already names WHAT a module is for.  This names WHERE a visitor meets it, and it
is the thing PARK_OVERHAUL.md makes mandatory before a plan may be prepared or promoted:

    "The existing park parallel manifests have module placement data but no typed anchors,
     dependencies, or interface links.  The rebuild begins by making those contracts mandatory.
     A plan cannot be prepared or promoted when a public module has empty anchors."

**AN ANCHOR IS A PLAN-TIME PROMISE, NOT A RENDER-TIME MEASUREMENT.** It has to exist before any
block is generated, or it cannot gate generation - which is the whole point of the rule. So the
planner derives every anchor from the module's box, facing and TYPE, and a separate route gate then
proves the built world honours it. The nearest paved coordinate is not an interface: an anchor is
named, typed, and owned by exactly one module.

**THE FACE IS DECIDED BY THE ROLE, NOT BY CONVENIENCE.** A queue entry and a ride exit on the same
cell is the failure rule 4 exists to stop - "ride exits never discharge into incoming queues" - so
the two are placed on opposite flanks by construction and the capacity gate re-checks the result
rather than trusting this.
"""
from __future__ import annotations

# ------------------------------------------------------------------ the schema, from the brief
#
# Verbatim from PARK_OVERHAUL.md's "Required interface schema" table, plus the two land specs'
# own additions (PARK_FRONTIER lists `queue_merge`/`maintenance_access`/`viewpoint`; PARK_HOLLOW
# lists `service_boundary`).  Where a land spec renames the same thing - `boarding_or_entry` for
# `boarding`, `public_approach` for `approach` - the park-wide name wins and the land's name is
# recorded as an alias, so one validator serves all three lands.

REQUIRED = {
    "arrival":      ("arrival", "public_entry", "public_exit", "map_view"),
    "ride":         ("approach", "queue_entry", "boarding", "ride_exit",
                     "emergency_exit", "service_access"),
    "walkthrough":  ("approach", "entry", "exit", "service_access"),
    "shop":         ("frontage", "customer_entry", "queue_entry",
                     "collection_or_exit", "service_access"),
    "landmark":     ("view_approach", "frontage"),
    "path":         (),          # a path declares endpoints and a capacity role instead
    "arch":         ("land_side", "connector_side", "departure_sign"),
    # **A SIGN YOU CANNOT STAND IN FRONT OF IS NOT SIGNAGE.** Rule 7 makes wayfinding part of
    # the path graph, so a map board owes exactly one interface - the cell it is read from - and
    # the circulation has to reach it like any other destination. Three of them across the three
    # lands were standing off the street when this was measured.
    "sign":         ("read_from",),
    "service":      (),          # benches and planters: dressing, not a destination
    "terrain":      (),
}

#: Anchors that are legitimate but not required - generated when the geometry supports them.
OPTIONAL = {
    "ride":        ("viewpoint", "queue_merge"),
    "walkthrough": ("reward",),
    "landmark":    ("interior_entry",),
    "arrival":     ("staff_exit", "ticket_input", "queue_start", "queue_end"),
}

#: A land spec's own name for an anchor a module already declares.  One validator, three lands.
ALIASES = {
    "public_approach":     "approach",
    "boarding_or_entry":   "boarding",
    "ride_entry":          "boarding",
    "board":               "boarding",
    "lift_entry":          "boarding",
    "service_boundary":    "service_access",
    "maintenance_access":  "service_access",
    "operator_access":     "service_access",
    "chute_exit":          "ride_exit",
    "wet_exit":            "ride_exit",
    "play_or_queue_entry": "queue_entry",
    "viewing_entry":       "entry",
    "viewing_exit":        "exit",
    "counter":             "collection_or_exit",
}

#: Which anchors a visitor must be able to STAND on. The rest - a sign, a service door, a view
#: corridor - are legitimately unwalkable, and demanding paving at all of them is the check that
#: cries wolf.
PUBLIC = {"arrival", "public_entry", "public_exit", "approach", "queue_entry", "entry", "exit",
          "ride_exit", "emergency_exit", "frontage", "customer_entry", "collection_or_exit",
          "view_approach", "land_side", "connector_side", "queue_start", "queue_end", "read_from"}

#: Anchors that belong to a queue and must therefore never be part of a through-route.
QUEUE = {"queue_entry", "queue_start", "queue_merge"}

#: Anchors that discharge guests. Rule 4 forbids these sharing a cell with anything in QUEUE.
EXIT = {"ride_exit", "public_exit", "exit", "emergency_exit", "collection_or_exit"}

#: Anchors that belong on the far side of a threshold, where this land's paving may not go.
HANDOFF = {"connector_side"}


def resolve(name: str) -> str:
    """A land spec's own anchor name, in park-wide terms."""
    return ALIASES.get(name, name)


def module_type(module: dict) -> str:
    """The interface type of a planned module: which row of the brief's table it answers to.

    Derived from (gen, kind) exactly as `park_contracts._purpose` derives a purpose, and kept
    beside it rather than merged into it because they answer different questions: a purpose says
    what a module is FOR, a type says what interfaces it owes.
    """
    gen, kind = module.get("gen"), module.get("kind")
    # **A STAIR IS CIRCULATION, NOT A DESTINATION.** Typed by the fallback it came out a shop,
    # owed a shopfront and a service counter, and stood in a band that admits neither - which is
    # three failures for a flight of steps whose whole job is to be walked down.
    if kind in {"paths", "stairwell"}:
        return "path"
    if kind == "plaza":
        return "terrain"
    if gen == "wayfinding":
        return "sign"
    if gen == "streetfurniture":
        return "service"
    if kind in {"arch", "gate"}:
        return "arch"
    # A ticketing sequence is the arrival contract spread over four modules that each own a
    # different part of it. Typed as shops they would owe a service counter from a turnstile.
    if gen in {"arrival", "ticketing"}:
        return "arrival"
    if gen in {"coaster", "bigwheel"} or kind in {"ghosttrain", "runawaymine", "carousel", "drop"}:
        return "ride"
    # An undercroft journey is a WALKTHROUGH: a guest walks it, chamber to chamber, and what it
    # owes is an approach, an entry, an exit and a way in for maintenance - not a shopfront.
    if gen == "undercroft" or kind in {"mirrormaze", "manor", "ossuary", "seance", "walkthrough"}:
        return "walkthrough"
    if kind in {"foodcourt", "saloon", "shopstreet", "market", "guestservices",
                "gamesrow", "sluice", "minehead", "powderhouse"}:
        return "shop"
    if gen == "arcade":
        return "shop"
    if gen in {"monument", "spectacle"} or kind in {"clocktower", "tower"}:
        return "landmark"
    return "shop"


# ------------------------------------------------------------------ deriving the anchor points

_STEP = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
_BACK = {"east": "west", "west": "east", "north": "south", "south": "north"}
_LEFT = {"east": "north", "north": "west", "west": "south", "south": "east"}


def _box(module) -> tuple[int, int, int, int]:
    ax, _ay, az = module["at"]
    ox, _oy, oz = module.get("anchor_offset", (0, 0, 0))
    w, _h, d = module["size"]
    return (ax + ox, az + oz, ax + ox + w - 1, az + oz + d - 1)


def _face_point(module, facing: str, along: float, out: int):
    """A point `out` cells clear of the named face, `along` of the way across it.

    `along` runs across the face, so 0.25 and 0.75 are two distinct flanks of one frontage -
    which is what lets a queue and an exit share a face without sharing a cell.
    """
    x0, z0, x1, z1 = _box(module)
    dx, dz = _STEP[facing]
    if dx:
        x = (x1 + out) if dx > 0 else (x0 - out)
        return (x, z0 + int(round((z1 - z0) * along)))
    z = (z1 + out) if dz > 0 else (z0 - out)
    return (x0 + int(round((x1 - x0) * along)), z)


#: (face, along, out) per anchor, per type. `face` is relative: "front" is the module's own
#: facing, "back" the opposite, "left"/"right" the flanks.
_LAYOUT = {
    "arrival": {
        "arrival":      ("front", 0.50, 2),
        "public_entry": ("front", 0.35, 2),
        "public_exit":  ("front", 0.65, 2),
        "map_view":     ("front", 0.50, 3),
        "staff_exit":   ("back",  0.50, 2),
        "ticket_input": ("front", 0.50, 1),
        "queue_start":  ("front", 0.20, 2),
        "queue_end":    ("front", 0.80, 2),
    },
    "ride": {
        # THE QUEUE AND THE EXIT ARE ON OPPOSITE FLANKS BY CONSTRUCTION. Rule 4: a ride exit
        # never discharges into an incoming queue. Placing them at 0.20 and 0.80 of one face
        # keeps them apart on a small booth and on a 57-block coaster alike.
        "approach":       ("front", 0.50, 3),
        "queue_entry":    ("front", 0.20, 2),
        "boarding":       ("front", 0.20, 1),
        "ride_exit":      ("front", 0.80, 2),
        "emergency_exit": ("left",  0.50, 2),
        "service_access": ("back",  0.50, 2),
        "viewpoint":      ("right", 0.50, 3),
        "queue_merge":    ("front", 0.10, 2),
    },
    "walkthrough": {
        "approach":       ("front", 0.50, 3),
        "entry":          ("front", 0.30, 2),
        "exit":           ("back",  0.70, 2),
        "reward":         ("back",  0.30, 2),
        "service_access": ("left",  0.50, 2),
    },
    "shop": {
        "frontage":           ("front", 0.50, 2),
        "customer_entry":     ("front", 0.35, 2),
        "queue_entry":        ("front", 0.15, 2),
        "collection_or_exit": ("front", 0.75, 2),
        "service_access":     ("back",  0.50, 2),
    },
    "landmark": {
        "view_approach":  ("front", 0.50, 4),
        "frontage":       ("front", 0.50, 2),
        "interior_entry": ("front", 0.50, 1),
    },
    "arch": {
        # An arch is a threshold: you walk THROUGH it, so its two sides are its interfaces, and
        # `_front_of`'s outward face is the connector side by definition.
        "land_side":      ("back",  0.50, 2),
        "connector_side": ("front", 0.50, 2),
        "departure_sign": ("back",  0.50, 1),
    },
    "sign": {
        "read_from": ("front", 0.50, 2),
    },
}


def _resolve_face(facing: str, relative: str) -> str:
    if relative == "front":
        return facing
    if relative == "back":
        return _BACK[facing]
    if relative == "left":
        return _LEFT[facing]
    return _BACK[_LEFT[facing]]


#: Anchors that belong to the backstage. Their FACE is a consequence rather than a decision, so
#: they may move to a flank when the rear is off the land - a shopfront may not.
_SERVICE_FACES = {"service_access", "staff_exit"}


def _on(x: int, z: int, owned) -> bool:
    return bool(owned) and owned[0] <= x <= owned[1] and owned[2] <= z <= owned[3]


def anchors_for(module: dict, plane: int | None = None, owned=None) -> list[dict]:
    """Every named anchor this module owes, as world-space points on the walking course.

    Y is the course a visitor stands ON - one above the module's own build plane - so an anchor
    can be compared against paving and against a walk without the caller re-deriving it.

    `owned` is (x0, x1, z0, z1) of the land the theme owns. An anchor outside it is marked
    `off_land` rather than dropped: an arch's connector side is outside the land BY DEFINITION -
    that is what makes it a handoff - and dropping it would hide the interface, while demanding
    paving for it would ask this land to build the connector's half of the threshold.

    **BEING OFF THE LAND EXCUSES A HANDOFF AND NOTHING ELSE.** Applied to every anchor it also
    excused the Mine Head presenting its shopfront to the transit corridor: the front was off the
    owned land, so the route gate stopped asking for a path to it and reported a building nobody
    can enter as served. `HANDOFF` names the two anchors that legitimately live on the far side
    of a threshold; anything else off the land is a module facing the wrong way.
    """
    kind_type = module_type(module)
    layout = _LAYOUT.get(kind_type)
    if not layout:
        return []
    facing = module.get("params", {}).get("facing", "east")
    # **AN ANCHOR STANDS ON THE COURSE ITS OWN MODULE STANDS ON, NOT ON THE LAND'S PLANE.**
    # Pinning every anchor to the plane was harmless while every module sat on it, and became
    # wrong the moment one did not: the Frontier's mine ride is 24 courses down and its queue
    # mouth was reported at street level, so the route gate saw a ride nobody could reach as
    # perfectly served. `plane` is the fallback for a module with no elevation of its own.
    #
    # **AND THE BUILD PLANE IS THE COURSE YOU STAND ON, NOT THE COURSE UNDER YOUR FEET.**
    # `tools/parkship.py` states it: "The build PLANE is the course you stand on; the FLOOR is the
    # course the floor blocks occupy, one under it." An anchor a course above that was consistent
    # with everything that only ever compared anchors to other anchors, and wrong the moment
    # anything compared one to a BLOCK - the safety pass read a guest's feet as their head and
    # reported 671 route cells across the three lands as obstructed by their own paving.
    y = module["at"][1] if module.get("at") else plane
    wanted = list(REQUIRED.get(kind_type, ())) + list(OPTIONAL.get(kind_type, ()))
    out = []
    for name in wanted:
        if name not in layout:
            continue
        relative, along, distance = layout[name]
        face = _resolve_face(facing, relative)
        x, z = _face_point(module, face, along, distance)
        # **A SERVICE DOOR ON A FACE THAT IS OFF THE LAND CAN NEVER HAVE A YARD.** The layout puts
        # the backstage on the REAR by construction, which is right until the rear is the plot
        # boundary: the Midway's whole admission sequence is pinned to its west edge facing east,
        # so five of its rear doors opened onto the neighbour's ground and no backstage road could
        # legally reach them. A shopfront's direction is a decision and stays where it is put; a
        # service door only has to be somewhere a road can get to, so it takes the first flank
        # that is actually on the land.
        if owned and name in _SERVICE_FACES and not _on(x, z, owned):
            for alternative in ("left", "right", "front"):
                other = _resolve_face(facing, alternative)
                ox, oz = _face_point(module, other, along, distance)
                if _on(ox, oz, owned):
                    face, x, z = other, ox, oz
                    break
        off_land = (name in HANDOFF and bool(owned)
                    and not (owned[0] <= x <= owned[1] and owned[2] <= z <= owned[3]))
        out.append({"name": name, "at": [int(x), int(y), int(z)], "face": face,
                    "public": name in PUBLIC, "queue": name in QUEUE, "exit": name in EXIT,
                    "off_land": off_land,
                    "required": name in REQUIRED.get(kind_type, ())})
    return out


def annotate(modules: list[dict], plane: int | None = None, owned=None) -> None:
    """Attach `interface` to every planned module, in place."""
    for module in modules:
        kind_type = module_type(module)
        module["interface"] = {
            "type": kind_type,
            "required": list(REQUIRED.get(kind_type, ())),
            "anchors": anchors_for(module, plane, owned),
        }


def anchor_index(modules: list[dict]) -> dict[str, dict]:
    """Every anchor in the plan, keyed `<module>.<anchor>` - the address a link names.

    A duplicate address is a hard error rather than a warning: two modules owning one anchor name
    is how a link silently resolves to the wrong end of the park.
    """
    index, clashes = {}, []
    for module in modules:
        name = module.get("name", "?")
        for anchor in module.get("interface", {}).get("anchors", []):
            key = f"{name}.{anchor['name']}"
            if key in index:
                clashes.append(key)
            index[key] = {**anchor, "module": name, "type": module_type(module)}
    if clashes:
        raise ValueError("duplicate anchor addresses: " + ", ".join(sorted(set(clashes))))
    return index


# ------------------------------------------------------------------ the gate itself

def missing_anchors(modules: list[dict]) -> list[dict]:
    """Public modules whose required anchors are absent or unplaced.

    "A plan cannot be prepared or promoted when a public module has empty anchors." An anchor
    that exists in name with no world point is empty in exactly the sense that rule means.
    """
    out = []
    for module in modules:
        kind_type = module_type(module)
        required = set(REQUIRED.get(kind_type, ()))
        if not required:
            continue
        declared = {resolve(a["name"]): a
                    for a in module.get("interface", {}).get("anchors", [])}
        for name in sorted(required - set(declared)):
            out.append({"module": module.get("name", "?"), "anchor": name,
                        "reason": "required anchor not declared"})
        for name in sorted(required & set(declared)):
            point = declared[name].get("at")
            if not (isinstance(point, (list, tuple)) and len(point) == 3):
                out.append({"module": module.get("name", "?"), "anchor": name,
                            "reason": "anchor has no world point"})
    return out


#: How far above or below the paving an anchor may stand and still be reached from it. One
#: course is a step; anything more needs a stair, a lift or a ramp, which is `pathgraph`'s
#: `shaft` role and section 4's rule about vertical public changes.
STEP_UP = 1


def unattached(modules: list[dict], paving: set, levels=None) -> list[dict]:
    """Public anchors that do not touch the public paving graph.

    Checked as a 1-cell neighbourhood, not as an exact hit: an anchor is the cell a visitor
    STANDS in to use the interface, and a doorway two cells off a 5-wide avenue is served. An
    exact-match rule would report a correctly-built park as unreachable, which is the check
    nobody runs.

    **AND IT HAS TO SEE ELEVATION, OR A VERTICAL PARK PASSES VACUOUSLY.** The moment a module
    could sit on a floor below the plane - the Frontier's mine ride is 24 courses down - a plan
    view of the paving said its queue mouth was on the street. It was on the street's SHADOW.
    `levels` maps a paved cell to the courses reachable there; an anchor more than one step from
    any of them is unreached, and the fix is a declared shaft rather than a wider tolerance.
    """
    out = []
    for module in modules:
        for anchor in module.get("interface", {}).get("anchors", []):
            if not anchor.get("public") or anchor.get("off_land"):
                continue
            x, y, z = anchor["at"]
            near = [(x + dx, z + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)
                    if (x + dx, z + dz) in paving]
            if not near:
                out.append({"module": module.get("name", "?"), "anchor": anchor["name"],
                            "at": anchor["at"], "reason": "public anchor off the paving graph"})
                continue
            if levels is None:
                continue
            if not any(abs(y - level) <= STEP_UP
                       for cell in near for level in levels.get(cell, ())):
                out.append({"module": module.get("name", "?"), "anchor": anchor["name"],
                            "at": anchor["at"],
                            "reason": "public anchor is on the paving in plan but not in "
                                      "elevation: it needs a stair, ramp or lift"})
    return out


def exit_queue_collisions(modules: list[dict], radius: int = 1) -> list[dict]:
    """Rule 4, measured: a discharge anchor within `radius` of somebody else's queue.

    Within ONE module the layout already keeps them apart; what this catches is the arrangement
    problem - a ride sited so its exit empties into the neighbour's queue - which no single
    module can see about itself.
    """
    queues = [(m.get("name", "?"), a) for m in modules
              for a in m.get("interface", {}).get("anchors", []) if a.get("queue")]
    out = []
    for module in modules:
        name = module.get("name", "?")
        for anchor in module.get("interface", {}).get("anchors", []):
            if not anchor.get("exit"):
                continue
            ex, _ey, ez = anchor["at"]
            for other, queue in queues:
                if other == name:
                    continue
                qx, _qy, qz = queue["at"]
                if abs(ex - qx) <= radius and abs(ez - qz) <= radius:
                    out.append({"module": name, "anchor": anchor["name"],
                                "reason": f"discharges into {other}.{queue['name']}",
                                "at": anchor["at"]})
    return out
