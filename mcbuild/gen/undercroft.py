"""The deep journeys: the Frontier's mine works and the Hollow's undercrypt.

PARK_VERTICAL_MASTERPLAN.md sections 6 and 7 name two routes, and both are the same SHAPE - a
descent, a sequence of chambers that each do one thing, a reveal, a reward, and a return that does
not come back the way it went:

    mine       station -> worked ore chamber -> broken trestle over a cavern -> flooded lower
               works -> crystal reveal -> hoist back to the surface
    crypt      catacomb transition -> ossuary branch -> train show chamber -> drowned crypt ->
               founder's vault -> a return that surfaces somewhere else

**IT IS ONE GENERATOR BECAUSE IT IS ONE PROBLEM.** Two land specs, two palettes and two stories -
and identical geometry: a corridor of a declared width and headroom, joined chambers, a floor you
can walk end to end, and a light level that does not let anything spawn behind you. Written twice
it would drift twice; the difference between a mine and a crypt is which chambers are in the list
and what they are built out of, which is data.

**THE ROUTE IS THE CONTRACT, AND IT IS WALKABLE OR IT IS NOTHING.** The masterplan's own words:
the deep route "must not simply be a long dark corridor below surface attractions". So every
chamber is entered and left through a real doorway on the spine, the spine is continuous, and
`tests/test_undercroft.py` walks it rather than trusting the arithmetic - which is the one check
that cannot be satisfied by a corridor that looks right in a render.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World

UNDERCROFT = {
    "land": "frontier",
    "kind": "mine",
    "at": None,                  # world [x, y, z] of the spine's start - the foot of the shaft
    "facing": "east",            # the direction the spine runs
    "width": 3,                  # the corridor a guest walks
    "height": 4,                 # courses of headroom over its floor
    "chambers": None,            # override the story; None takes the kind's own
    "under": None,               # capture, so the dig list is honest
    "lamp_every": 6,
}

_STEP = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
_LEFT = {"east": (0, -1), "west": (0, 1), "south": (1, 0), "north": (-1, 0)}

# ------------------------------------------------------------------ the two stories
#
# A chamber is (name, length, width, what it holds). Length runs along the spine, width across it;
# both are what the ROOM is, not what its walls occupy. The order is the journey, and it is the
# masterplan's own order rather than a shuffle: a reveal that comes before the work it rewards is
# not a reveal.

STORIES = {
    "mine": [
        ("Ore Chamber", 11, 11, "ore"),
        ("Broken Trestle", 15, 9, "chasm"),
        ("Flooded Works", 13, 11, "water"),
        ("Crystal Reveal", 13, 13, "crystal"),
    ],
    "crypt": [
        ("Catacombs", 13, 9, "niches"),
        ("Ossuary Branch", 11, 11, "puzzle"),
        ("Train Chamber", 15, 11, "scene"),
        ("Drowned Crypt", 11, 11, "water"),
        ("Founders Vault", 11, 11, "reward"),
    ],
}

# **PALETTES ARE THE LAND'S OWN, ONE STEP DARKER.** A deep chamber lit like a street is a
# basement; what makes it read as underground is that the rock is the rock you dug through and
# the light is sparse and cold. Every block here is cheap-or-ok tier and 1.19.
PALETTES = {
    "mine": {"rock": "cobblestone", "rough": "andesite", "floor": "gravel",
             "beam": "spruce_log", "plank": "spruce_planks", "trim": "stone_bricks",
             "light": "lantern", "accent": "raw_iron_block", "rail": "rail"},
    "crypt": {"rock": "deepslate_bricks", "rough": "cracked_deepslate_bricks",
              "floor": "polished_deepslate", "beam": "dark_oak_log", "plank": "dark_oak_planks",
              "trim": "chiseled_deepslate", "light": "soul_lantern", "accent": "amethyst_block",
              "rail": "rail"},
}


def _fill(w, x0, y0, z0, x1, y1, z1, block, carved=None, **props):
    """Lay rock, and NEVER into a cell something has already carved.

    **CLEARED HAS TO BE STICKY OR THE ROOMS BRICK UP THE CORRIDOR.** `_hollow` clears by removing
    a cell, which is indistinguishable from a cell nobody ever built - so the next chamber's
    shell, which legitimately extends a cell past its own wall, poured rock straight back into
    the spine it was supposed to open off. The corridor is VOID, not absence, and the difference
    is the whole journey: the walk test found four cells of cobblestone standing in it.
    """
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                if carved is not None and (x, y, z) in carved:
                    continue
                w.put(x, y, z, block, **props)


def _hollow(w, x0, y0, z0, x1, y1, z1, carved=None):
    """Clear a room's interior, and REMEMBER that it is clear."""
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                w.cells.pop((x, y, z), None)
                if carved is not None:
                    carved.add((x, y, z))


def _shell(w, x0, y0, z0, x1, y1, z1, pal, seed=0.0, carved=None):
    """Rock around a room, then the room hollowed out of it, then a floor under it.

    Built solid and then cleared rather than laid as six faces: a face-by-face wall leaves the
    corners to arithmetic, and every corner this project has built by arithmetic has been wrong
    at least once. Solid-then-hollow has no corners to get wrong.
    """
    _fill(w, x0 - 1, y0 - 1, z0 - 1, x1 + 1, y1 + 1, z1 + 1, pal["rock"], carved)
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            for y in range(y0 - 1, y1 + 2):
                if hash01(x, y, z, seed) < 0.22 and (carved is None or (x, y, z) not in carved):
                    w.put(x, y, z, pal["rough"])
    _hollow(w, x0, y0, z0, x1, y1, z1, carved)
    # The floor is laid UNDER the room and is not carved, so it may overwrite - a floor is what
    # a guest stands on and a corridor arriving at a room shares it.
    _fill(w, x0, y0 - 1, z0, x1, y0 - 1, z1, pal["floor"])
    if carved is not None:
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                carved.discard((x, y0 - 1, z))


def _light(w, x, y, z, pal):
    """A lantern hanging from a real ceiling block, or standing on a real floor.

    A lantern needs one or the other and this project has shipped both mistakes - a lamp under a
    slab cap reading as "hanging from air", and a floating one over a hollow. Checked here rather
    than hoped for.
    """
    if w.has(x, y + 1, z):
        w.put(x, y, z, pal["light"], hanging="true", waterlogged="false")
        return True
    if w.has(x, y - 1, z):
        w.put(x, y, z, pal["light"], hanging="false", waterlogged="false")
        return True
    return False


def _chamber(w, pal, kind, spot, size, holds, seed, carved=None, lane=1, axis="x"):
    """One room on the spine, hollowed out of rock and given the one thing it is for.

    **A CHAMBER DOES ONE THING.** The masterplan's deep route "offers a puzzle, a reveal, a reward,
    and a different return location", which is four rooms with four jobs - not one long room with
    four kinds of decoration in it. So each `holds` is a single readable idea and the room is
    otherwise empty, because negative space is what makes the thing in it read.
    """
    (cx, cy, cz) = spot
    (length, width) = size
    x0, x1 = cx - length // 2, cx + length // 2
    z0, z1 = cz - width // 2, cz + width // 2
    y1 = cy + 5
    _shell(w, x0, cy, z0, x1, y1, z1, pal, seed, carved)

    if holds == "ore":
        # Veins in the working face, and the timber that holds the roof up over them.
        for i in range(4):
            ox = x0 + 1 + int(hash01(cx, cz, i, seed) * (length - 2))
            oz = z0 + 1 + int(hash01(cz, cx, i, seed + 1) * (width - 2))
            for k in range(3):
                w.put(ox, cy + k, z1 + 1, pal["accent"])
        for bx in range(x0 + 2, x1, 4):
            for by in range(cy, y1):
                w.put(bx, by, z0, pal["beam"], axis="y")
                w.put(bx, by, z1, pal["beam"], axis="y")
            for bz in range(z0, z1 + 1):
                w.put(bx, y1, bz, pal["beam"], axis="z")
    elif holds == "chasm":
        # The floor falls away and a timber deck carries you over it. The hole is the feature.
        _hollow(w, x0 + 2, cy - 8, z0 + 1, x1 - 2, cy - 1, z1 - 1, carved)
        for bx in range(x0 + 2, x1 - 1):
            for bz in range(cz - 1, cz + 2):
                w.put(bx, cy - 1, bz, pal["plank"])
            w.put(bx, cy, cz - 2, pal["beam"], axis="x")
            w.put(bx, cy, cz + 2, pal["beam"], axis="x")
    elif holds == "water":
        # A flooded floor you walk the EDGE of. **THE SPINE'S OWN LANE STAYS DRY**, which is not
        # decoration: filled corner to corner, the flooded chamber flooded the corridor through
        # it and the walk test found water standing in the walkway. A guest looks at the flood;
        # they do not swim the journey.
        #
        # **SEALED, WITH A BED AND SIDES** - the shell already gave it both, so the water sits in
        # a real basin rather than pouring out, which is what `fluids.unenclosed` exists to catch.
        for x in range(x0 + 2, x1 - 1):
            for z in range(z0 + 2, z1 - 1):
                if _on_lane(x, z, cx, cz, axis, lane + 1):
                    continue
                w.put(x, cy, z, "water", level="0")
        for x in range(x0 + 1, x1):
            for z in (z0 + 1, z1 - 1):
                w.put(x, cy, z, pal["trim"])
    elif holds == "crystal":
        # The reveal: one lit mass, seen from a doorway before you reach it.
        for k in range(4):
            for x in range(cx - 2 + k, cx + 3 - k):
                for z in range(cz - 2 + k, cz + 3 - k):
                    w.put(x, cy + k, z, pal["accent"])
        for x in (cx - 3, cx + 3):
            _light(w, x, cy + 1, cz, pal)
    elif holds == "niches":
        # Catacombs: a wall of shelves, which is what makes a corridor read as a burial place.
        for z in (z0, z1):
            for x in range(x0 + 1, x1):
                for y in (cy + 1, cy + 3):
                    w.cells.pop((x, y, z), None)
                    w.put(x, y - 1, z, pal["trim"])
    elif holds == "puzzle":
        # Three inputs on three walls - the shape the Ossuary already uses, sited rather than
        # rebuilt: what belongs here is the ROOM, and the mechanism is its own module's business.
        for (px, pz) in ((x0 + 1, cz), (x1 - 1, cz), (cx, z0 + 1)):
            w.put(px, cy + 1, pz, pal["accent"])
    elif holds == "scene":
        # The train's own chamber: a track through it, and the frontage a rider sees.
        for x in range(x0, x1 + 1):
            w.put(x, cy, cz, pal["rail"], shape="east_west")
        for x in range(x0 + 2, x1, 5):
            _light(w, x, cy + 3, cz + 3, pal)
    elif holds == "reward":
        # The founder's vault: a plinth, a light on it, and nothing else in the room.
        for x in range(cx - 1, cx + 2):
            for z in range(cz - 1, cz + 2):
                w.put(x, cy, z, pal["trim"])
        w.put(cx, cy + 1, cz, pal["accent"])
        _light(w, cx, cy + 2, cz, pal)
    return {"name": None, "box": [x0, cy, z0, x1, y1, z1]}


def _clear_lane(w, spot, size, half, height, axis, carved=None):
    """Open the corridor's own lane through a chamber, at the courses a guest occupies."""
    cx, cy, cz = spot
    length, width = size
    x0, x1 = cx - length // 2, cx + length // 2
    z0, z1 = cz - width // 2, cz + width // 2
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if not _on_lane(x, z, cx, cz, axis, half):
                continue
            for h in range(height):
                w.cells.pop((x, cy + h, z), None)
                if carved is not None:
                    carved.add((x, cy + h, z))
            if not w.has(x, cy - 1, z):
                w.put(x, cy - 1, z, "cobblestone")


def _on_lane(x, z, cx, cz, axis, half) -> bool:
    """Is this cell in the corridor's own lane through a chamber?"""
    return abs(z - cz) <= half if axis == "x" else abs(x - cx) <= half


def _spine(w, pal, start, facing, width, height, length, seed, carved=None):
    """The corridor between chambers: rock, hollowed, floored, and lit at a stated interval."""
    dx, dz = _STEP[facing]
    lx, lz = _LEFT[facing]
    half = width // 2
    x, y, z = start
    for step in range(length):
        cx, cz = x + dx * step, z + dz * step
        for o in range(-half - 1, half + 2):
            for h in range(-1, height + 1):
                cell = (cx + lx * o, y + h, cz + lz * o)
                if carved is None or cell not in carved:
                    w.put(*cell, pal["rock"])
        for o in range(-half, half + 1):
            for h in range(height):
                cell = (cx + lx * o, y + h, cz + lz * o)
                w.cells.pop(cell, None)
                if carved is not None:
                    carved.add(cell)
            w.put(cx + lx * o, y - 1, cz + lz * o, pal["floor"])
            if carved is not None:
                carved.discard((cx + lx * o, y - 1, cz + lz * o))
    return length


def build(cfg: dict, donors=None) -> Canvas:
    """Spine, chambers, lights - one walkable journey with a doorway into every room.

    The chambers are threaded ALONG one spine rather than scattered and joined afterwards. A
    corridor that reaches every room by construction cannot be disconnected, which is the failure
    a deep route has no defence against: nobody notices a sealed chamber in a render, and the
    walk test is what finds it.
    """
    p = {**UNDERCROFT, **cfg}
    if not p.get("at") or len(p["at"]) != 3:
        raise ValueError("undercroft needs params.at = [x, y, z] of the spine's start")
    if p["kind"] not in STORIES:
        raise ValueError(f"unknown undercroft kind {p['kind']!r}; have {sorted(STORIES)}")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be a cardinal, one of {sorted(_STEP)}")

    pal = PALETTES[p["kind"]]
    story = p.get("chambers") or STORIES[p["kind"]]
    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    dx, dz = _STEP[p["facing"]]
    x, y, z = (int(v) for v in p["at"])
    seed = float(len(story))

    carved: set = set()
    built, cursor = [], 0
    for index, (name, length, width, holds) in enumerate(story):
        # A run of spine, then the room it leads to. The run is what makes the journey a walk
        # rather than a suite of rooms sharing a wall.
        run = 6 if index else 4
        _spine(w, pal, (x + dx * cursor, y, z + dz * cursor), p["facing"],
               p["width"], p["height"], run, seed, carved)
        cursor += run
        centre = (x + dx * (cursor + length // 2), y, z + dz * (cursor + length // 2))
        _chamber(w, pal, p["kind"], centre, (length, width), holds, seed + index, carved,
                 lane=p["width"] // 2, axis="x" if dx else "z")
        # **THE LANE THROUGH A ROOM IS CLEARED LAST, AND THAT IS ONE RULE RATHER THAN SEVEN.**
        # Each chamber type put its own thing in the middle of its own room - the crystal mass,
        # the vault plinth, the flood - and the middle of the room is where the corridor runs, so
        # the walk test found the journey blocked by the very features it exists to show. Patched
        # per chamber it would be got wrong again by the eighth one somebody writes; swept once,
        # after the room is built, a new chamber type cannot forget it.
        #
        # A guest walks PAST the reveal. Standing inside it, they cannot see it anyway.
        _clear_lane(w, centre, (length, width), p["width"] // 2, p["height"],
                    "x" if dx else "z", carved)
        built.append({"name": name, "holds": holds,
                      "at": [int(centre[0]), int(centre[1]), int(centre[2])]})
        cursor += length

    # **THE LIGHTS GO IN LAST, AND EVERY ONE OF THEM IS CHECKED.** A lantern needs a ceiling to
    # hang from or a floor to stand on; placed while the rock was still being carved, half of
    # them would have been hung off a block the next `_hollow` took away.
    lit = 0
    for step in range(0, cursor, int(p["lamp_every"])):
        for side in (-1, 1):
            lx, lz = _LEFT[p["facing"]]
            cx = x + dx * step + lx * side * (p["width"] // 2)
            cz = z + dz * step + lz * side * (p["width"] // 2)
            if _light(w, cx, y + p["height"] - 1, cz, pal):
                lit += 1

    dig = []
    if ctx is not None:
        # Anything the world already holds where the journey goes has to come out first: a
        # printer places into AIR, so a cell the terrain owns is a cell that never gets built.
        for (cx, cy, cz) in list(w.cells):
            if ctx.occupied(cx, cy, cz):
                dig.append([cx, cy, cz])

    return w.canvas({
        "kind": f"undercroft/{p['kind']}",
        "land": p["land"], "facing": p["facing"],
        "chambers": built, "spine_length": cursor, "lights": lit,
        "dig": dig,
        "contract": "one continuous spine with a doorway into every chamber, each chamber doing "
                    "exactly one thing, lit end to end so nothing spawns behind you",
        "unverified": [
            "NOTHING HERE IS A RIDE. The chambers are the rooms a ride or a walkthrough happens "
            "IN; what moves through them is the module that owns the journey, and its own "
            "mechanics are its own contract.",
        ],
    })
