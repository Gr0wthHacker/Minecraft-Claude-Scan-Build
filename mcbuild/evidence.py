"""Produce the evidence the four un-derivable promotion gates block on.

`gates.py` names ten gates and answers six of them from the plan alone. The other four -
`mechanics`, `safety`, `night`, `visual` - are about the BUILT world, so they block until somebody
measures it. This is the somebody.

    python -m mcbuild parkevidence <plan>            measure, and write it onto the plan
    python -m mcbuild parkgate <plan>                ...and now ten gates have an answer

**IT MEASURES THE GENERATED ARTIFACTS, NOT THE PLAN.** A plan is a set of intentions; every
question these four gates ask - does the rail carry a cart, is the water sealed, can a mob stand
where a guest walks, does the arrival read - is a question about blocks. So each producer loads the
land's own litematics and works on the composite, and a land whose modules have not been generated
gets a failure that says so rather than an empty pass.

**AND `visual` STILL NEEDS A HUMAN.** The render packet is produced here; the VERDICT is not, and
`visual` stays blocked until one is recorded. This project has the scar: an animal scored GOOD on
every measured dimension and was a spotted table, and *"a panel that is not recorded is one the
next good-looking score quietly overrules"*. A packet is evidence that somebody CAN look; it is not
evidence that they did.
"""
from __future__ import annotations

import os

import numpy as np

from . import circuit, fluids, interfaces as I, nightlight, pathgraph as P, scan as scan_mod

#: A public route cell that a mob can stand on at night is a spawn on a guest path. Light 0 is a
#: spawn; the game's own threshold for a hostile mob is 0 in 1.19 for most, so anything above it
#: is safe and 0 is not.
SPAWN_LIGHT = 0

#: Findings `circuit.inspect` reports for information rather than as faults - its own words, not
#: a paraphrase. Quasi-connectivity is what a piston machine LOOKS like, and an unoriented model
#: is a limit of the reader rather than of the build.
SOFT_FINDINGS = {"quasi-connectivity", "orientation unknown"}

#: Sidecar keys a generator uses to declare where its water is ALLOWED to be. A cascade steps
#: down a course at a time, so every cell's downhill neighbour is a hole - that is the ride, and
#: `fluids.unenclosed` needs telling.
WATER_ENVELOPE_KEYS = ("envelope", "water", "channel", "pool_water", "flow", "basin")


def _artifacts(plan, out_dir: str = "out") -> list:
    """Every generated litematic this plan owns, as (module, Capture). Missing ones are named.

    **A LAND'S NIGHT PASS IS AN ARTIFACT OF THE LAND.** `tools/park_night.py` measures the built
    composite and lights what the street lighting could not reach, which by construction cannot be
    a planned module - it does not exist until the modules do. It is picked up by name here, so
    the gate measures the world that will actually be placed rather than the world before its own
    night pass ran.
    """
    found, missing = [], []
    for module in plan.get("modules", ()):
        path = os.path.join(out_dir, f"{module['name']}.litematic")
        if not os.path.exists(path):
            missing.append(module["name"])
            continue
        found.append((module, scan_mod.load(path)))
    night_name = f"{(plan.get('name') or '').title()} Night"
    night_path = os.path.join(out_dir, f"{night_name}.litematic")
    if found and os.path.exists(night_path):
        cap = scan_mod.load(night_path)
        found.append(({"name": night_name, "at": list(cap.origin), "kind": "night",
                       "size": list(cap.model.shape_xyz), "anchor_offset": [0, 0, 0],
                       "params": {}}, cap))
    return found, missing


def _cells(found) -> dict:
    """The composite as {(x, y, z): name}, first writer winning, in plan order.

    The same precedence `layers.slice_plan` applies - a room owns its own floor and the hall lays
    only the ground between them - so the world these checks measure is the world that gets built.
    """
    out = {}
    for _module, cap in found:
        model = cap.model
        names = [n.split(":")[-1] for n in model.names]
        ox, oy, oz = cap.origin
        for y, z, x in zip(*model.solid().nonzero()):
            pos = (int(x) + ox, int(y) + oy, int(z) + oz)
            if pos not in out:
                out[pos] = names[model.ids[y, z, x]]
    return out


def _envelope(meta) -> list:
    """Every cell a design says its water may occupy, from whichever key it used to say it.

    A generator declares its wet cells under its own name - `channel`, `pool_water`, `basin` -
    because the sidecar is written for a reader, not for this. Reading only `envelope` reported
    the Rapids and the Sluice as leaking one cell each, which is a cascade being a cascade.
    """
    out = []
    for key in WATER_ENVELOPE_KEYS:
        value = meta.get(key)
        if isinstance(value, list):
            for cell in value:
                if isinstance(cell, (list, tuple)) and len(cell) == 3:
                    out.append(tuple(int(v) for v in cell))
    return out


def _result(ok, failures, warnings=None, **extra):
    return {"ok": bool(ok), "failures": list(failures), "warnings": list(warnings or []), **extra}


def _nothing_built(missing):
    return _result(False, [f"{len(missing)} module(s) have not been generated: "
                           + ", ".join(sorted(missing)[:6])
                           + (" ..." if len(missing) > 6 else "")])


# ------------------------------------------------------------------ mechanics

def mechanics(plan, out_dir: str = "out") -> dict:
    """Rails, redstone, fluid containment and collection, per module.

    **AGAINST A BASELINE, NOT AGAINST ZERO.** `circuit.inspect` reports smells, and a real machine
    made by a person has leftovers - the calibration corpus settled that a working build scores
    one informational line and a 185,198-block casino scores 37. So what fails here is a finding
    the inspection itself calls a fault: a dead wire run, a component nothing can drive, a
    direction pointing at air. Quasi-connectivity is counted and reported, never failed: a piston
    machine IS pistons with things over them.
    """
    found, missing = _artifacts(plan, out_dir)
    if not found:
        return _nothing_built(missing or ["every module"])
    failures, warnings, per_module = [], [], {}
    for module, cap in found:
        findings = circuit.inspect(cap.model, cap.origin)
        # **THE KINDS ARE THE INSPECTION'S OWN STRINGS, AND GUESSING THEM READ AS A FAULT.**
        # `circuit.inspect` returns "quasi-connectivity" and "orientation unknown"; filtered
        # against invented spellings, every piston machine in the Frontier came back as a
        # circuit fault - which is the calibration corpus's own finding inverted, since a piston
        # machine IS pistons with things over them.
        hard = [f for f in findings if f[0] not in SOFT_FINDINGS]
        soft = [f for f in findings if f not in hard]
        if hard or soft:
            per_module[module["name"]] = {"faults": len(hard), "notes": len(soft)}
        for kind, pos, detail in hard[:4]:
            failures.append(f"{module['name']}: {kind} at {list(pos)} - {detail}")
        if len(hard) > 4:
            failures.append(f"{module['name']}: ...and {len(hard) - 4} more circuit faults")
    if missing:
        warnings.append(f"{len(missing)} module(s) not generated and therefore not inspected")

    water = _water_report(found)
    failures.extend(water["failures"])
    warnings.extend(water["warnings"])
    return _result(not failures, failures, warnings,
                   modules_inspected=len(found), per_module=per_module, water=water["counts"])


def _water_report(found) -> dict:
    """Every water cell in the land has a bed and sides, or the ride leaks.

    `fluids.unenclosed` is the STATIC check - usable on a finished litematic with no idea what the
    design intended - and it is the one that catches the two unsurvivable shapes: water over a
    hole, and water beside a hole. A design that declares a cascade envelope in its sidecar has
    that honoured; one that declares none has water that is not supposed to be going anywhere,
    which is what the empty default means.
    """
    failures, warnings, counts = [], [], {}
    for module, cap in found:
        names = [n.split(":")[-1] for n in cap.model.names]
        if not any("water" in n for n in names):
            continue
        cells = {}
        ox, oy, oz = cap.origin
        for y, z, x in zip(*cap.model.solid().nonzero()):
            cells[(int(x) + ox, int(y) + oy, int(z) + oz)] = names[cap.model.ids[y, z, x]]
        allow = _envelope(cap.meta)
        loose = fluids.unenclosed(cells, allow=allow)
        counts[module["name"]] = len(loose)
        if loose:
            failures.append(f"{module['name']}: {len(loose)} water cell(s) with no bed or an "
                            f"open side, e.g. {loose[0]}")
    return {"failures": failures, "warnings": warnings, "counts": counts}


# ------------------------------------------------------------------ safety

def safety(plan, out_dir: str = "out") -> dict:
    """No blocked landing, no unreachable control, no headroom collision over a public route.

    The three that can be measured off the blocks are checked; the two that cannot are named. A
    guest's head is the second cell of the pair they occupy, so a public route with something in
    it is a route you walk into rather than along - and that is a property of the composite, which
    is why it cannot be answered from the plan.
    """
    found, missing = _artifacts(plan, out_dir)
    if not found:
        return _nothing_built(missing or ["every module"])
    cells = _cells(found)
    routes = P.normalise(plan.get("routes") or [])
    hub = next((m for m in plan["modules"] if m.get("covers") and m["kind"] == "plaza"), None)
    plane = int(hub["at"][1]) if hub else None
    levels = P.levels(routes, plane) if plane is not None else {}

    failures, warnings = [], []

    # **PAVING UNDER A BUILDING IS NOT A ROUTE A GUEST WALKS.** The street is laid even under a
    # building on purpose - skipping obstacle cells can SPLIT a route, and a network that is not
    # connected is not a network - and the building wins the cell in the slice. Measured without
    # that exclusion, 834 route cells across the three lands read as obstructed by the very walls
    # they run beneath, which is the design working rather than a safety fault.
    footprints = [_box_of(m) for m in plan["modules"]
                  if not m.get("covers") and m["kind"] not in {"paths", "plaza"}]

    def _indoors(x, z):
        return any(x0 <= x <= x1 and z0 <= z <= z1 for (x0, z0, x1, z1) in footprints)

    # HEADROOM. Two clear cells over every WALKABLE route cell, at the course that route is on.
    # The kerb is excluded: it is where the trim and the lamp posts go, and measuring across it
    # reports a correctly lit avenue as obstructed by its own lighting.
    walk_cells = P.interior(routes)
    blocked = []
    for cell, courses in levels.items():
        if _indoors(cell[0], cell[1]) or cell not in walk_cells:
            continue
        for y in courses:
            for h in (0, 1):
                name = cells.get((cell[0], y + h, cell[1]))
                # **A STEP IS NOT AN OBSTRUCTION, AND ONLY AT FOOT HEIGHT.** A stair or a slab in
                # the course a guest's feet are in is something they walk UP; the same block at
                # head height is something they walk INTO. One rule for both read a correctly
                # stepped street as blocked.
                if name and not _passable(name, foot=(h == 0)):
                    blocked.append((cell[0], y + h, cell[1], name))
                    break
    if blocked:
        failures.append(f"{len(blocked)} public route cell(s) have something in the two courses a "
                        f"guest occupies, e.g. {blocked[0][3]} at {list(blocked[0][:3])}")

    # A LANDING A GUEST DROPS INTO must be water or have a floor. Every ride_exit and every
    # boarding point is a place somebody arrives at; arriving into a hole is the failure.
    holes = []
    for module in plan["modules"]:
        for anchor in module.get("interface", {}).get("anchors", []):
            if I.resolve(anchor["name"]) not in {"ride_exit", "boarding", "arrival"}:
                continue
            x, y, z = anchor["at"]
            if anchor.get("off_land"):
                continue
            under = cells.get((x, y - 1, z))
            if under is None:
                holes.append((module.get("name", "?"), anchor["name"], [x, y, z]))
    if holes:
        failures.append(f"{len(holes)} landing(s) have nothing under them, e.g. "
                        f"{holes[0][0]}.{holes[0][1]} at {holes[0][2]}")

    # PUBLIC MACHINERY. A mechanism a guest can stand on is a mechanism a guest can break.
    exposed = []
    machine = {"redstone_wire", "repeater", "comparator", "piston", "sticky_piston", "observer",
               "dispenser", "dropper", "redstone_torch", "redstone_block", "tnt"}
    for cell, courses in levels.items():
        if _indoors(cell[0], cell[1]) or cell not in walk_cells:
            continue
        for y in courses:
            name = cells.get((cell[0], y, cell[1]))
            if name in machine:
                exposed.append((cell[0], y, cell[1], name))
    if exposed:
        failures.append(f"{len(exposed)} public route cell(s) are standing ON exposed machinery, "
                        f"e.g. {exposed[0][3]} at {list(exposed[0][:3])}")

    if missing:
        warnings.append(f"{len(missing)} module(s) not generated and therefore not checked")
    warnings.append("water-lift seals and essential-control reach are per-ride contracts; the "
                    "ride suites own them, this checks the land")
    return _result(not failures, failures, warnings,
                   route_cells=len(levels), headroom_blocked=len(blocked),
                   landings_over_air=len(holes), exposed_machinery=len(exposed))


def _box_of(module) -> tuple:
    ax, _ay, az = module["at"]
    ox, _oy, oz = module.get("anchor_offset", (0, 0, 0))
    w, _h, d = module["size"]
    return (ax + ox, az + oz, ax + ox + w - 1, az + oz + d - 1)


def _passable(name: str, foot: bool = False) -> bool:
    if name in nightlight.PASSY or name.endswith("_sign") or "carpet" in name:
        return True
    return foot and (name.endswith("_slab") or name.endswith("_stairs"))


# ------------------------------------------------------------------ night

def night(plan, out_dir: str = "out") -> dict:
    """Propagate block light over the land and count what can spawn where guests walk.

    **SCOPED PER LEVEL, WHICH IS THE WHOLE DIFFICULTY.** `nightlight.surface` takes each column's
    TOPMOST standable cell, which is right for an island and wrong for a park with rooms under it:
    the Frontier's mine landing is invisible under the town, so a column-wise pass would grade the
    land clean while a mob stood on the station platform. This project already measured that from
    the other side - 5,228 of the lowland's 6,852 standable columns were invisible to the
    island-wide sweep - and recorded a per-LEVEL re-solve as its own job. This is that job.

    What is judged is the PUBLIC ROUTE, not every cell of the land: a dark corner behind a ride is
    not a guest's problem, and grading the whole plot would report a park that lights its streets
    correctly as failing.
    """
    found, missing = _artifacts(plan, out_dir)
    if not found:
        return _nothing_built(missing or ["every module"])
    routes = P.normalise(plan.get("routes") or [])
    hub = next((m for m in plan["modules"] if m.get("covers") and m["kind"] == "plaza"), None)
    if hub is None:
        return _result(False, ["the plan has no plaza, so it declares no build plane"])
    plane = int(hub["at"][1])
    levels = P.levels(routes, plane)
    if not levels:
        return _result(False, ["the plan declares no circulation to light"])

    # **THE SAME TWO EXCLUSIONS THE SAFETY PASS MAKES, FOR THE SAME REASON.** Paving is laid
    # even under a building on purpose and the building wins the cell, so a route cell inside a
    # footprint is not somewhere a guest stands; and the kerb is where the lamp posts go. Measured
    # without them, 376 of the Midway's 387 "dark guest paths" were the floor of rooms.
    footprints = [_box_of(m) for m in plan["modules"]
                  if not m.get("covers") and m["kind"] not in {"paths", "plaza"}]

    def _indoors(x, z):
        return any(x0 <= x <= x1 and z0 <= z <= z1 for (x0, z0, x1, z1) in footprints)

    walk_cells = P.interior(routes)
    light, origin = _light_field(found)
    dark = []
    for (x, z), courses in levels.items():
        if _indoors(x, z) or (x, z) not in walk_cells:
            continue
        for y in courses:
            value = _at(light, origin, x, y, z)
            if value is not None and value <= SPAWN_LIGHT:
                dark.append((x, y, z))
    failures = []
    if dark:
        failures.append(f"{len(dark)} public route cell(s) are at block light {SPAWN_LIGHT} and "
                        f"can spawn a mob, e.g. {list(dark[0])}")
    return _result(not failures, failures,
                   [] if not missing else
                   [f"{len(missing)} module(s) not generated and therefore not lit"],
                   route_cells=sum(len(v) for cell, v in levels.items()
                                   if not _indoors(*cell) and cell in walk_cells),
                   spawnable_public_cells=len(dark), levels=len({y for v in levels.values()
                                                                 for y in v}))


def _light_field(found):
    """Block light over the composite, as a (y, z, x) array plus its world origin."""
    xs, ys, zs = [], [], []
    for _m, cap in found:
        ox, oy, oz = cap.origin
        w, h, d = cap.model.shape_xyz
        xs += [ox, ox + w]
        ys += [oy, oy + h]
        zs += [oz, oz + d]
    # Two courses of margin so a light just outside the box still reaches in.
    x0, x1 = min(xs) - 2, max(xs) + 2
    y0, y1 = min(ys) - 2, max(ys) + 2
    z0, z1 = min(zs) - 2, max(zs) + 2
    shape = (y1 - y0, z1 - z0, x1 - x0)
    opaque = np.zeros(shape, bool)
    emit = np.zeros(shape, np.int16)
    for _m, cap in found:
        model = cap.model
        op, em, _pa, _sp, _wa = nightlight.classify(list(model.names))
        ox, oy, oz = cap.origin
        for y, z, x in zip(*model.solid().nonzero()):
            i = model.ids[y, z, x]
            gy, gz, gx = int(y) + oy - y0, int(z) + oz - z0, int(x) + ox - x0
            if em[i] > emit[gy, gz, gx]:
                emit[gy, gz, gx] = em[i]
            if op[i]:
                opaque[gy, gz, gx] = True
    return nightlight.propagate(opaque, emit), (x0, y0, z0)


def _at(light, origin, x, y, z):
    x0, y0, z0 = origin
    gy, gz, gx = y - y0, z - z0, x - x0
    if not (0 <= gy < light.shape[0] and 0 <= gz < light.shape[1] and 0 <= gx < light.shape[2]):
        return None
    return int(light[gy, gz, gx])


# ------------------------------------------------------------------ visual

#: The views PARK_OVERHAUL.md's `visual` gate names, in the order a reviewer reads them.
PACKET = ("arrival", "approach", "queue", "exit", "return_loop", "landmark_sightline",
          "night_overview")

#: A player's eye above the course they stand on, and how far back from an interface a camera has
#: to be for the interface to be IN the picture rather than to be the whole of it.
EYE_HEIGHT, STAND_BACK = 2, 26


def visual(plan, out_dir: str = "out", sheet_dir: str = "out/packets") -> dict:
    """Render the packet the gate asks for, and refuse to call it a pass.

    **A PACKET IS EVIDENCE THAT SOMEBODY CAN LOOK. IT IS NOT EVIDENCE THAT THEY DID.** This
    project has the scar: an animal scored GOOD on every measured dimension and was a spotted
    table, and the rule written down afterwards is that a panel which is not recorded is one the
    next good-looking score quietly overrules. So this produces the seven views and returns
    `ok=False` with the reason until a verdict is written onto the plan under
    `evidence.visual.verdict` - at which point it passes and the verdict travels with the land.
    """
    found, missing = _artifacts(plan, out_dir)
    if not found:
        return _nothing_built(missing or ["every module"])
    supplied = ((plan.get("evidence") or {}).get("visual") or {})
    verdict = supplied.get("verdict")
    rendered = _render_packet(plan, found, sheet_dir)
    if not verdict:
        return _result(False, ["the packet is rendered and nobody has recorded a verdict on it: "
                               f"look at {sheet_dir} and write one to evidence.visual.verdict"],
                       views=rendered, packet_dir=sheet_dir)
    return _result(True, [], [], views=rendered, packet_dir=sheet_dir, verdict=verdict)


def _render_packet(plan, found, sheet_dir: str) -> dict:
    """One render per named view, standing AT the anchor the view is named after.

    **THE CAMERA COMES FROM THE PLAN, NOT FROM A HAND.** A view called "queue" that does not show
    a queue mouth is a view of something else, and this project has twice put a camera at the
    wrong bearing by choosing it by hand in one session. Each view stands at its own anchor, at a
    player's eye height, looking at the middle of the land - so the packet is reproducible and a
    reviewer can check the camera against the coordinate printed beside it.

    A view whose anchor the land does not have is RECORDED AS ABSENT rather than quietly skipped.
    A park with no ride exit has not produced a six-view packet; it has failed to produce a
    seven-view one, and that is what a reviewer needs to be told.
    """
    from PIL import Image

    from . import render3d as r3
    os.makedirs(sheet_dir, exist_ok=True)
    model, origin = _composite_model(found)
    lo, hi = r3.content_box(model)
    centre = (lo + hi) / 2
    # **THE OVERVIEW FRAMES THE PARK, NOT THE MINE UNDER IT.** With a deep journey sited the
    # content box spans 140 courses, so framing all of it pushes the camera far enough back that
    # the land a guest walks is a thumbnail in the corner of a sky. `tools/timelapse.py` records
    # the same lesson from the other side: a camera sized to whatever a model happens to contain
    # swims. The surface is what an overview is OF.
    surface = [mc for mc in found if _on_surface(mc[0], plan)]
    top_model, _top_origin = _composite_model(surface or found)

    anchors = {}
    for module in plan["modules"]:
        for anchor in module.get("interface", {}).get("anchors", []):
            anchors.setdefault(I.resolve(anchor["name"]), []).append(
                (module.get("name", "?"), anchor["at"], anchor.get("face", "east")))
    picks = {
        "arrival": anchors.get("arrival") or anchors.get("land_side"),
        "approach": anchors.get("approach"),
        "queue": anchors.get("queue_entry"),
        "exit": anchors.get("ride_exit") or anchors.get("public_exit"),
        "return_loop": anchors.get("land_side") or anchors.get("connector_side"),
        "landmark_sightline": anchors.get("view_approach"),
        "night_overview": None,
    }
    name = plan.get("name", "land")
    out = {}
    for view in PACKET:
        spot = (picks.get(view) or [None])[0]
        entry = {"from": spot[0] if spot else "the whole land",
                 "at": list(spot[1]) if spot else None,
                 "face": spot[2] if spot else None,
                 "present": spot is not None or view == "night_overview"}
        try:
            if spot is None:
                camera = r3.orbit(top_model, yaw=215, pitch=20, dist=1.15, look_high=0.35)
                pixels = r3.render(top_model, camera, 960, 640)
            else:
                camera = _eye_at(r3, spot[1], spot[2], origin, centre)
                pixels = r3.render(model, camera, 900, 560)
            path = os.path.join(sheet_dir, f"{name}_{view}.png")
            Image.fromarray(pixels).save(path)
            entry["image"] = path
        except Exception as exc:            # a renderer failure is a missing view, not a verdict
            entry["image"] = None
            entry["error"] = f"{type(exc).__name__}: {exc}"
        out[view] = entry
    return out


#: Which way is "out" from each face, so a camera can stand in front of what it photographs.
_OUT = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}


def _eye_at(r3, at, face, origin, centre):
    """A player's eye standing in front of an interface, looking at it.

    Model coordinates, not world ones: `render` works in the composite's own frame and handing it
    a world point puts the camera tens of thousands of blocks away, which renders a blank sky and
    looks exactly like a build that is not there.

    **IT STANDS BACK ALONG THE ANCHOR'S OWN FACE, NOT ALONG THE LINE TO THE LAND'S CENTRE.**
    Backing away from the centre works until the anchor IS near the centre - the Midway's arrival
    court is pinned to the island's bedrock, so the direction degenerated, the camera barely moved
    and the view came out from inside a wall. An anchor already records which way it faces; that
    is the direction you photograph a doorway from.
    """
    import numpy as np

    eye = np.array([at[0] - origin[0], at[1] - origin[1] + EYE_HEIGHT, at[2] - origin[2]], float)
    dx, dz = _OUT.get(face or "east", (1, 0))
    eye[0] += dx * STAND_BACK
    eye[2] += dz * STAND_BACK
    eye[1] += STAND_BACK * 0.30
    target = np.array([at[0] - origin[0], at[1] - origin[1] + 2.0, at[2] - origin[2]], float)
    return r3.Camera(tuple(eye), tuple(target))


def _on_surface(module, plan) -> bool:
    """Is this module on the land's own build plane, rather than on a band under it?"""
    hub = next((m for m in plan["modules"] if m.get("covers") and m["kind"] == "plaza"), None)
    if hub is None:
        return True
    return int(module["at"][1]) == int(hub["at"][1])


def _composite_model(found):
    """Every module folded into one model, plus its world origin.

    Paths LAST, which is not a detail: paving is laid even under a building on purpose, so for a
    picture to show a building rather than the street painted through it the street has to lose
    the tie - and a merge gives the tie to whatever was folded in first.
    """
    from . import scan as sc
    ordered = sorted(found, key=lambda mc: "Paths" in mc[0].get("name", ""))
    base = ordered[0][1]
    merged, origin = base.model, tuple(base.origin)
    for _module, cap in ordered[1:]:
        holder = sc.Scan(merged, {"origin": {"x": origin[0], "y": origin[1], "z": origin[2]}},
                         base.litematic_path, base.sidecar_path)
        merged, _overlap = sc.merge(holder, cap.model, cap.origin)
        origin = tuple(min(a, b) for a, b in zip(origin, cap.origin))
    return merged, origin


PRODUCERS = {"mechanics": mechanics, "safety": safety, "night": night, "visual": visual}


def measure(plan, only=None, out_dir: str = "out") -> dict:
    """Run the producers and return an `evidence` block ready to attach to a plan."""
    names = [n for n in PRODUCERS if not only or n in only]
    return {name: PRODUCERS[name](plan, out_dir) for name in names}
