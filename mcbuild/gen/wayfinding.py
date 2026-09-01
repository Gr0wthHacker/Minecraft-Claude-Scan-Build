"""Signage: the layer the park never had. Every attraction, zone and street exists and none of it
says what it is or which way to go - the audit in `tools/park_flow.py` measured it directly: two
of the three zones only reach the transit line across a bare, unlit 1-block seam, the two zone
arches point at open void rather than at the line that actually crosses it, and nothing anywhere
on the plot names an attraction before you are standing in its doorway.

Five kinds, all following `gen/park.py`'s own protocol - a Frame, a LANDS palette, `_sign`'s
support-checked-not-assumed rule - because signage belongs to the same three lands as everything
else and a mismatched post reads as someone else's park:

    mapboard      a framed, coloured layout at a zone's entrance - the plan, not a wall of text
    fingerpost    a junction post with 2-4 arms, each naming and POINTING AT a real destination
    marker        a small nameplate outside one attraction, for when its own facade does not say
    archway       a threshold that names the land or ride you are about to walk into
    noticeboard   park rules / hours at the entrance

**THE DESTINATION IS CHECKED, NOT ASSUMED, AND FOR THE SAME REASON `_sign`'s SUPPORT IS.** A
fingerpost pointing at something that does not exist is worse than no fingerpost - it sends a
visitor looking for a building that was renamed or never built, and nothing about the placement
would look wrong. `known_destinations()` reads the live theme rosters straight out of
`mcbuild.planner.THEMES` plus the three zone names plus whatever the shipped transit line actually
called its stations, so a rename anywhere upstream fails a fingerpost HERE rather than in game.

**THE SIGN'S TEXT AND THE ARM'S DIRECTION MUST AGREE.** A fingerpost arm is built from the post
outward along one cardinal direction and ends in a wall sign whose `facing` is that SAME
direction - the placard "points" the way the arm projects, which is the shape a real fingerpost
is. `meta["arms"]` records both the direction and the sign's facing for every arm built, so a test
can assert the two never drift apart without having to read a render.
"""
from __future__ import annotations

import pathlib

from .canvas import Canvas
from .park import LANDS, SIGN_WIDTH, _STEP, _BACK, _Frame, _pad, _hang_light
from .vertical import Ctx, World

WAYFINDING = {
    "under": None,
    "at": None,                 # world (x, y, z)
    "kind": "fingerpost",
    "facing": "east",           # mapboard/marker/archway/noticeboard: the way the sign faces
    "land": "midway",
    "title": None,
    "sign": True,
    # mapboard
    "zone": None,                # which zone this board stands in - highlighted on the layout
    "width": 9,
    "rows": 5,
    "legend": None,              # up to 3 extra lines under the header
    # fingerpost
    "arms": None,                # [{direction, dest, length}]
    "post_h": None,
    # marker
    "name": None,
    "number": None,
    # WHAT YOU DO THERE, up to two lines under the name. A nameplate that says only "THE VAULT"
    # tells a visitor which building they are looking at and nothing about whether it is worth
    # walking into - which is half of the verdict this zone was rejected on: you arrive and there
    # is nothing to do and no idea where to go. A name answers the second half only.
    "does": None,
    # archway
    "entering": None,
    "arch_width": 5,
    "arch_height": 5,
    # noticeboard
    "rules": None,
}


# ------------------------------------------------------------------------- the destination roster

def _station_titles() -> set:
    """Station names off the shipped transit config - the one place they are actually written
    down. `transit.py` carries no default titles of its own (`STATION["title"]` is a placeholder),
    so this is the only real source. A missing config is an EMPTY set, not a crash: a generator
    must not fail to import because a yaml file has not been emitted yet."""
    import yaml
    out = set()
    p = pathlib.Path("configs/park_line.yaml")
    if not p.exists():
        return out
    try:
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for st in (cfg.get("params", {}).get("stations") or []):
            if st.get("title"):
                out.add(str(st["title"]).upper())
    except Exception:                                            # noqa: BLE001
        pass
    return out


def known_destinations() -> set:
    """Every name a fingerpost, marker or archway may legally point at: every module name in
    every park theme, the three zone names, and the transit line's own station titles.

    Read straight out of `mcbuild.planner.THEMES` rather than kept as a second list here, so a
    module renamed in the planner fails a fingerpost's build immediately instead of shipping a
    sign to nowhere. `mcbuild.planner` is imported here, never edited - this module is a reader
    of the roster, not an owner of it.
    """
    from .. import planner
    names = {"MIDWAY", "FRONTIER", "HOLLOW"}
    for zone in ("midway", "frontier", "hollow"):
        for m in planner.THEMES.get(zone, {}).get("modules", []):
            names.add(str(m["name"]).upper())
    names |= _station_titles()
    return names


def _check_dest(dest: str) -> str:
    dest = str(dest)
    known = known_destinations()
    if dest.upper() not in known:
        raise ValueError(f"wayfinding: {dest!r} names no real module, zone or station - "
                         f"have {sorted(known)}")
    return dest


# ------------------------------------------------------------------------------- shared signage

def _sign(w, x, y, z, facing, wood, front, back=()) -> bool:
    """A wall sign in the cell IN FRONT of its support, its text facing away from it.

    `park._sign`'s rule, restated for raw world coordinates because a fingerpost's arms are not
    all on one `_Frame` axis. **THE SUPPORT IS CHECKED, NOT ASSUMED** - four of the park's own
    seven kinds shipped a sign hung on a column with nothing behind it before this guard existed,
    and the mistake is invisible in every render: a floating sign draws exactly like a mounted one.

    Returns True if the sign was placed. A caller that ignores a False is asking the bug back.
    """
    fdx, fdz = _STEP[facing]
    if not w.has(x - fdx, y, z - fdz):
        return False
    lines = [str(s)[:SIGN_WIDTH] for s in list(front)[:4]]
    lines += [""] * (4 - len(lines))
    w.put(x, y, z, f"{wood}_wall_sign", facing=facing, waterlogged="false")
    w.sign(x, y, z, front=lines,
           back=[str(s)[:SIGN_WIDTH] for s in list(back)[:4]], colour="white", glowing=True)
    return True


# ------------------------------------------------------------------------------------- mapboard

def _mapboard(w: World, p: dict, ctx) -> dict:
    """A framed, coloured layout at a zone's entrance - a PLAN, not a paragraph.

    Three columns, one per zone, each in that zone's own `wall` tone (frontier/midway/hollow left
    to right along the board's own width - the same order the arches and the transit board already
    use), with the zone this board actually stands in picked out by its own accent colour as a
    "YOU ARE HERE" cell. A visitor reads a floor plan faster than four lines of a sign, and this is
    the one piece of signage in the whole park that draws one.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    width = max(7, int(p["width"]) | 1)
    rows = max(4, int(p["rows"]))
    legs_h = 2
    board_h = rows
    top = legs_h + board_h + 1                     # + one header course

    _pad(w, f, pal, width, 1, margin=1)

    for i in (0, width - 1):
        for h in range(legs_h):
            w.put(*f.at(i, 0, h), pal["post"])
    for i in range(width):
        for h in range(legs_h, top):
            edge = i in (0, width - 1) or h in (legs_h, top - 1)
            w.put(*f.at(i, 0, h), pal["trim"] if edge else pal["wall"])

    # THE LAYOUT, three columns coloured by land - frontier / midway / hollow, matching the
    # islands' own north-to-south order (CLAUDE.md: "the islands run along Z: left is NORTH,
    # right is SOUTH"). Interior only, so the frame stays a frame.
    order = ["frontier", "midway", "hollow"]
    zone = p.get("zone") or p["land"]
    inner_w = width - 2
    seg = max(1, inner_w // 3)
    here_i = None
    for col, land_name in enumerate(order):
        i0 = 1 + col * seg
        i1 = (width - 2) if col == 2 else i0 + seg - 1
        blk = LANDS[land_name]["wall"]
        for i in range(i0, i1 + 1):
            for h in range(legs_h + 1, top - 1):
                w.put(*f.at(i, 0, h), blk)
        if land_name == zone:
            here_i = (i0 + i1) // 2
    if here_i is not None:
        here_h = legs_h + 1 + board_h // 2
        w.put(*f.at(here_i, 0, here_h), pal["accent"])

    title = str(p.get("title") or f"{p['land'].upper()} MAP").upper()
    # h = top - 1, NOT top: the frame's own top border row is at top - 1 (the loop that builds it
    # runs `range(legs_h, top)`, so `top` itself is one course of open air with nothing behind it -
    # the exact "sign on a column with an opening in it" bug `_sign`'s guard exists to catch.
    signed = _sign(w, *f.at(width // 2, -1, top - 1), f.facing, pal["wood"],
                   [title[:SIGN_WIDTH], "", "", ""])
    legend = list(p.get("legend") or [])
    if legend:
        _sign(w, *f.at(width // 2, -1, legs_h + 1), f.facing, pal["wood"], legend)

    return {"kind": "mapboard", "width": width, "height": top, "zone": zone, "signed": signed,
            "contract": "a coloured three-zone layout at the entrance, with the zone you are "
                        "standing in picked out - read as a plan, not a paragraph"}


# ------------------------------------------------------------------------------------ fingerpost

def _arm(w, at, direction, dest, length, h, wood, pal):
    x0, y0, z0 = at
    dx, dz = _STEP[direction]
    length = max(3, int(length))
    for k in range(1, length - 1):
        w.put(x0 + dx * k, y0 + h, z0 + dz * k, pal["fence"])
    cap = (x0 + dx * (length - 1), y0 + h, z0 + dz * (length - 1))
    w.put(*cap, pal["trim"])
    sign_pos = (x0 + dx * length, y0 + h, z0 + dz * length)
    placed = _sign(w, *sign_pos, direction, wood,
                   [str(dest).upper()[:SIGN_WIDTH], "", "", ""])
    return {"direction": direction, "dest": dest, "sign_facing": direction,
            "placed": placed, "sign_at": list(sign_pos)}


def _fingerpost(w: World, p: dict, ctx) -> dict:
    """A junction post with 2-4 arms, each an outward beam ending in a sign that names and
    POINTS AT a real destination.

    **THE ARM AND ITS SIGN MUST AGREE ON DIRECTION.** Built any other way - a sign mounted facing
    back toward the post, say - the placard would be readable only by someone already walking away
    from the destination it names. The sign's `facing` is set to the same cardinal the arm was
    built along, and `meta["arms"]` carries both so a test can check them without a render.
    """
    pal = LANDS[p["land"]]
    x, y, z = (int(v) for v in p["at"])
    arms_in = list(p.get("arms") or [])
    if not (2 <= len(arms_in) <= 4):
        raise ValueError("wayfinding/fingerpost needs 2-4 params.arms")
    dirs = [a["direction"] for a in arms_in]
    if len(set(dirs)) != len(dirs):
        raise ValueError(f"wayfinding/fingerpost: two arms share a direction - {dirs}")
    for a in arms_in:
        if a["direction"] not in _STEP:
            raise ValueError(f"wayfinding/fingerpost: bad direction {a['direction']!r}")
        _check_dest(a["dest"])

    post_h = int(p.get("post_h") or (3 + len(arms_in) + 1))
    # a small paved circle at the foot, so a fingerpost dropped mid-plaza still stands on
    # something of its own rather than assuming the ground under it belongs to this design
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            w.put(x + dx, y - 1, z + dz, pal["path"])
    for h in range(post_h):
        w.put(x, y + h, z, pal["post"])
    w.put(x, y + post_h, z, pal["light"], hanging="false", waterlogged="false")

    built = []
    for i, a in enumerate(arms_in):
        h = 3 + i
        built.append(_arm(w, (x, y, z), a["direction"], a["dest"],
                          a.get("length", 4), h, pal["wood"], pal))

    if not all(m["placed"] for m in built):
        raise ValueError("wayfinding/fingerpost: an arm's sign had nothing to hang from - "
                         "check its length")
    return {"kind": "fingerpost", "arms": built, "post_h": post_h,
            "contract": "2-4 arms, each pointing the direction its own sign faces, each naming "
                        "a real module, zone or transit station"}


# ---------------------------------------------------------------------------------------- marker

def _marker(w: World, p: dict, ctx) -> dict:
    """A small nameplate outside one attraction - so a building says what it is even when its
    own facade does not."""
    pal = LANDS[p["land"]]
    name = p.get("name")
    if not name:
        raise ValueError("wayfinding/marker needs params.name")
    _check_dest(name)
    x, y, z = (int(v) for v in p["at"])
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            w.put(x + dx, y - 1, z + dz, pal["path"])
    height = 3
    for h in range(height):
        w.put(x, y + h, z, pal["post"])
    w.put(x, y + height, z, pal["trim"])
    lines = [str(name).upper()[:SIGN_WIDTH]]
    if p.get("number") is not None:
        lines.append(f"NO {p['number']}"[:SIGN_WIDTH])
    # ...then what you DO there. Clipped rather than refused, because a nameplate is worth
    # standing whatever its second line says - but the clip is at SIGN_WIDTH, which is where a
    # line stops rendering rather than where it stops being sensible, so a caller that writes
    # nineteen characters gets fifteen and no warning. `tests/test_wayfinding.py` pins the width.
    does = p.get("does")
    if does:
        lines += [str(t)[:SIGN_WIDTH] for t in ([does] if isinstance(does, str) else does)]
    lines = (lines + [""] * 4)[:4]
    # ONE CELL OUT FROM THE POST, not on it: `_sign` overwrites whatever is at its own cell, so
    # signing the post's own top block would replace the post with a sign and leave the sign with
    # nothing behind it. Offset outward by the facing direction, the post itself is the support.
    fdx, fdz = _STEP[p["facing"]]
    signed = _sign(w, x + fdx, y + height - 1, z + fdz, p["facing"], pal["wood"], lines)
    if not signed:
        raise ValueError("wayfinding/marker: the nameplate had nothing to hang from")
    return {"kind": "marker", "name": name, "signed": signed,
            "contract": "a nameplate for one attraction, standing beside its door"}


# --------------------------------------------------------------------------------------- archway

def _archway(w: World, p: dict, ctx) -> dict:
    """A threshold that names what you are about to walk into - `park._arch`'s geometry, built
    small and put to work purely as signage rather than as a land's own front gate."""
    f = _Frame(p)
    pal = LANDS[p["land"]]
    entering = p.get("entering")
    if not entering:
        raise ValueError("wayfinding/archway needs params.entering")
    _check_dest(entering)
    width = max(3, int(p["arch_width"]) | 1)
    height = max(3, int(p["arch_height"]))
    depth = 2

    _pad(w, f, pal, width, depth, margin=1, block=pal["path"])
    for d in range(depth):
        for h in range(height):
            w.put(*f.at(0, d, h), pal["post"])
            w.put(*f.at(width - 1, d, h), pal["post"])
    for i in range(width):
        for d in range(depth):
            w.put(*f.at(i, d, height), pal["trim"])
    for i in (0, width - 1):
        _hang_light(w, f, pal, i, -1, height - 2)

    signed = _sign(w, *f.at(width // 2, -1, height), f.facing, pal["wood"],
                   [f"ENTERING"[:SIGN_WIDTH], str(entering).upper()[:SIGN_WIDTH], "", ""])
    return {"kind": "archway", "width": width, "height": height, "entering": entering,
            "signed": signed,
            "contract": "a threshold you walk through, naming the land or ride on the other side"}


# ---------------------------------------------------------------------------------- noticeboard

def _noticeboard(w: World, p: dict, ctx) -> dict:
    """Park rules and hours at the entrance - a frame carrying one to three signs, each capped at
    four lines. Purely informational: nothing it prints is a destination, so nothing here is
    checked against `known_destinations()`."""
    f = _Frame(p)
    pal = LANDS[p["land"]]
    rules = list(p.get("rules") or ["OPEN 9AM-9PM", "HAVE FUN", "MIND THE GAP"])
    width = 5
    height = 6

    _pad(w, f, pal, width, 1, margin=1)
    for i in (0, width - 1):
        for h in range(height):
            w.put(*f.at(i, 0, h), pal["post"])
    for i in range(1, width - 1):
        for h in range(height):
            w.put(*f.at(i, 0, h), pal["trim"] if h in (0, height - 1) else pal["wall"])

    title = str(p.get("title") or "PARK RULES").upper()
    header = _sign(w, *f.at(width // 2, -1, height - 1), f.facing, pal["wood"],
                   [title[:SIGN_WIDTH], "", "", ""])
    # up to three more signs, four lines each, stacked down the board
    signed = 1 if header else 0
    body = [rules[k:k + 4] for k in range(0, min(len(rules), 12), 4)]
    for k, lines in enumerate(body):
        h = height - 3 - k
        if h < 1:
            break
        if _sign(w, *f.at(width // 2, -1, h), f.facing, pal["wood"], lines):
            signed += 1

    return {"kind": "noticeboard", "width": width, "height": height, "signed": signed,
            "rules": rules,
            "contract": "park rules and hours on a board at the entrance, header plus body signs"}


BUILDERS = {
    "mapboard": _mapboard,
    "fingerpost": _fingerpost,
    "marker": _marker,
    "archway": _archway,
    "noticeboard": _noticeboard,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**WAYFINDING, **cfg}
    if not p.get("at"):
        raise ValueError("wayfinding needs params.at = [x, y, z]")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown wayfinding kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"wayfinding/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        **{k: v for k, v in meta.items() if k not in ("contract",)},
    })
