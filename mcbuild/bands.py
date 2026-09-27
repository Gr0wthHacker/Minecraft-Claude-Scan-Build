"""Vertical zoning for the park: six bands, what belongs in each, and the rules between them.

PARK_VERTICAL_MASTERPLAN.md section 3 states the park is not a flat fairground with tunnels under
it - it is one story told across six elevation bands, measured RELATIVE to the declared island
build plane `B`. That relativity is the whole reason this is a module rather than six constants:
the three lands sit on three islands whose build planes are their own, and a band written as an
absolute Y is a band that is wrong on two of them the day the third moves.

    Skyline           B+80 .. 335    landmark peaks, sky lift, fireworks, observation
    Upper attraction  B+28 .. B+80   coaster ridge, clockworks, high decks, lift towers
    Public park       B-8  .. B+28   paths, entries, queues, food, games, primary facades
    Hidden core       B-48 .. B-8    stations, machine galleries, mine approaches
    Deep adventure    B-160 .. B-48  caverns, catacombs, train scenes, puzzles, reward rooms
    Void-edge reserve -64  .. B-160  exceptional finale scenes only

**THE VALUE OF VERTICAL SPACE IS CONTRAST, AND THAT IS A MEASURABLE THING.** The masterplan says
so directly - "maintain large open voids and sightlines between the major bands; do not fill every
altitude with detached towers or caves" - so `occupancy` reports how much of each band a plan
claims, and the check fails a land that has filled the sky rather than composed it.
"""
from __future__ import annotations

#: (name, low, high) as offsets from the build plane. `None` means the server limit.
BANDS = (
    ("void_edge",        None, -160),
    ("deep_adventure",   -160, -48),
    ("hidden_core",      -48,  -8),
    ("public_park",      -8,   28),
    ("upper_attraction", 28,   80),
    ("skyline",          80,   None),
)

#: The absolute range the server allows. A band offset that resolves outside it is a build that
#: cannot exist, not a build that is merely ambitious.
WORLD_FLOOR, WORLD_CEILING = -64, 335

#: What each band is FOR, from the masterplan's own table. A module in a band whose function it
#: does not answer is the "detached towers and caves at every altitude" the plan forbids.
FUNCTION = {
    "skyline":          {"landmark", "ride"},
    "upper_attraction": {"ride", "landmark"},
    "public_park":      {"arrival", "arch", "shop", "ride", "walkthrough",
                         "landmark", "path", "terrain", "sign", "service"},
    "hidden_core":      {"ride", "walkthrough", "service", "path"},
    "deep_adventure":   {"walkthrough", "ride", "landmark", "path"},
    "void_edge":        {"walkthrough", "landmark"},
}

#: How much of a band's own volume its modules' BLOCKS may claim before it stops being sky and
#: starts being a wall.
#:
#: **THESE NUMBERS ARE INVENTED, exactly as the rubric weights and grade thresholds elsewhere in
#: this project are, and they are stated here rather than buried so the next person suspects the
#: table before the code.** What is not invented is the shape: a public park SHOULD be dense and
#: a skyline should not, so one ceiling for all six bands would either forbid a street or permit
#: a wall of sky towers.
MAX_OCCUPANCY = {"skyline": 0.02, "upper_attraction": 0.08, "public_park": 0.45,
                 "hidden_core": 0.30, "deep_adventure": 0.25, "void_edge": 0.02}

#: Rule from section 4: "Vertical public changes: one block per horizontal course; steeper
#: changes are signed stairs/elevators/lifts."
MAX_GRADE = 1.0


def limits(band: str, plane: int) -> tuple[int, int]:
    """The absolute Y range of a band, on an island whose build plane is `plane`.

    **A BAND CAN BE EMPTY, AND THAT IS INFORMATION.** An island whose plane is Y0 has no deep
    adventure band: B-160 is below the world floor. Clamping only the top end produced ranges
    like -64..-224 - a band whose low is above its high, which every consumer would then measure
    as negative volume. An empty band comes back as `(low, low - 1)` and `has_band` says so, so
    a land can be told it has no room beneath it rather than being silently graded against space
    that does not exist.
    """
    for name, low, high in BANDS:
        if name != band:
            continue
        y0 = WORLD_FLOOR if low is None else plane + low
        y1 = WORLD_CEILING if high is None else plane + high
        y0 = min(max(y0, WORLD_FLOOR), WORLD_CEILING)
        y1 = min(max(y1, WORLD_FLOOR), WORLD_CEILING)
        return y0, y1
    raise KeyError(f"unknown band {band!r}; have {', '.join(n for n, _l, _h in BANDS)}")


def has_band(band: str, plane: int) -> bool:
    """Does this island's build plane leave any room in that band at all?"""
    low, high = limits(band, plane)
    return high > low


def band_of(y: int, plane: int) -> str:
    """Which band a course sits in. Bands are half-open upward so a boundary has one owner."""
    offset = y - plane
    for name, low, high in BANDS:
        if (low is None or offset >= low) and (high is None or offset < high):
            return name
    return "skyline" if offset >= 0 else "void_edge"


def span_of(module: dict, plane: int) -> list[str]:
    """Every band a module passes through, low to high.

    A drop tower is not "in" one band - it is the thing that CONNECTS two, which is exactly what
    the masterplan means by kinetic and visible from across the island. Reading a module's band
    off its `at` alone would file a 77-block wheel by the course its foot stands on.
    """
    y0 = int(module["at"][1]) + int(module.get("anchor_offset", (0, 0, 0))[1])
    y1 = y0 + int(module["size"][1]) - 1
    order = [name for name, _l, _h in BANDS]
    return [b for b in order if any(band_of(y, plane) == b for y in (y0, y1))
            or (order.index(band_of(y0, plane)) < order.index(b) < order.index(band_of(y1, plane)))]


def _mass(module: dict) -> int:
    """How much of a module is actually SOLID.

    **A BOUNDING BOX IS NOT A BUILDING, AND FOR A FERRIS WHEEL IT IS NOT EVEN CLOSE.** The Big
    Wheel measures 19 x 85 x 77 and is mostly the air a wheel turns in; counted as its box it
    filled 22% of the upper band on its own and failed a ceiling meant to catch a land that had
    built a wall of towers. This project already learned to reserve design CELLS rather than
    boxes when siting the void ladybird; the same distinction decides whether a skyline reads
    as sparse.

    A planned module carries its real block count once it has been built. Before that there is
    nothing to read, so the box is the fallback - which errs toward over-full, and that is the
    safe direction for a ceiling.
    """
    blocks = module.get("blocks")
    if isinstance(blocks, int) and blocks > 0:
        return blocks
    return module["size"][0] * module["size"][1] * module["size"][2]


def occupancy(modules: list[dict], plane: int, footprint: int) -> dict:
    """The share of each band's volume that modules' mass claims, over `footprint` ground cells.

    A module's mass is split between the bands it crosses in proportion to the COURSES it has in
    each, so a tower crossing three bands is counted once, spread over where it stands.
    """
    out = {}
    for name, _low, _high in BANDS:
        y0, y1 = limits(name, plane)
        if y1 <= y0:                      # this plane leaves no room in that band at all
            out[name] = {"low": y0, "high": y1, "cells": 0, "share": 0.0}
            continue
        volume = footprint * max(1, y1 - y0 + 1)
        used = 0.0
        for module in modules:
            if module.get("covers") or module["kind"] in {"paths", "plaza"}:
                continue
            my0 = int(module["at"][1]) + int(module.get("anchor_offset", (0, 0, 0))[1])
            my1 = my0 + int(module["size"][1]) - 1
            height = max(1, my1 - my0 + 1)
            overlap = max(0, min(my1, y1) - max(my0, y0) + 1)
            if overlap:
                used += _mass(module) * overlap / height
        out[name] = {"low": y0, "high": y1, "cells": int(round(used)),
                     "share": used / volume if volume else 0.0}
    return out


def dominant_band(module: dict, plane: int) -> str:
    """The band a module mostly stands in - where it belongs, rather than what it reaches."""
    y0 = int(module["at"][1]) + int(module.get("anchor_offset", (0, 0, 0))[1])
    y1 = y0 + int(module["size"][1]) - 1
    counts = {}
    for y in range(y0, y1 + 1):
        band = band_of(y, plane)
        counts[band] = counts.get(band, 0) + 1
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def check(modules: list[dict], plane: int, footprint: int, module_type) -> dict:
    """The vertical zoning gate: right function, inside the world, and sky left in the sky.

    **A MODULE THAT SPANS BANDS IS A CONNECTOR, NOT A VIOLATION, AND THE FIRST VERSION OF THIS
    GATE HAD THAT BACKWARDS.** Checking every band a module touches failed the Mine Head for
    reaching the hidden core - which is the entire point of a headframe - and the Haunted Manor
    for being three storeys tall. What the masterplan forbids is "detached towers or caves at
    every altitude": a module sited WHOLLY in a band whose function it does not answer. So the
    function test is against the band a module mostly stands in, and the spans are reported,
    because a park that connects its bands is the thing being asked for.
    """
    failures, warnings, connectors = [], [], []
    for module in modules:
        name = module.get("name", "?")
        kind_type = module_type(module)
        y0 = int(module["at"][1]) + int(module.get("anchor_offset", (0, 0, 0))[1])
        y1 = y0 + int(module["size"][1]) - 1
        if y0 < WORLD_FLOOR or y1 > WORLD_CEILING:
            failures.append(f"{name}: spans Y {y0}..{y1}, outside the server's {WORLD_FLOOR}"
                            f"..{WORLD_CEILING}")
            continue
        crossed = span_of(module, plane)
        if len(crossed) > 1:
            connectors.append({"module": name, "bands": crossed})
        band = dominant_band(module, plane)
        allowed = FUNCTION.get(band, set())
        if kind_type not in allowed:
            failures.append(f"{name} ({kind_type}) stands in the {band} band, which is for "
                            + ", ".join(sorted(allowed)))
    shares = occupancy(modules, plane, footprint)
    # **AN ESTIMATE MAY NOT FAIL A BUILD.** Before a module is generated there is no block count
    # to read and `_mass` falls back to the bounding box, which for the Big Wheel is 124,355
    # cells of mostly air. Failing an occupancy ceiling on that number would block a plan for
    # the shape of a wheel rather than for anything anyone built - so an unbuilt plan is WARNED
    # and a built one is judged.
    estimated = [m.get("name", "?") for m in modules
                 if not (m.get("covers") or m["kind"] in {"paths", "plaza"})
                 and not isinstance(m.get("blocks"), int)]
    for band, entry in shares.items():
        ceiling = MAX_OCCUPANCY[band]
        if entry["share"] <= ceiling:
            continue
        message = (f"the {band} band is {entry['share']:.0%} full against a {ceiling:.0%} "
                   "ceiling: vertical space reads as contrast, not as more building")
        if estimated:
            warnings.append(message + f" (estimated: {len(estimated)} modules have no block count "
                                       "yet, so this is their bounding boxes)")
        else:
            failures.append(message)
    used = [b for b, e in shares.items() if e["cells"]]
    if len(used) < 2:
        warnings.append("the land occupies one vertical band: it is a flat fairground, "
                        "not a vertical park")
    return {"ok": not failures, "failures": failures, "warnings": warnings,
            "plane": plane, "bands": shares, "bands_used": sorted(used),
            "connectors": connectors, "estimated_modules": len(estimated)}


def grade_failures(routes: list[dict]) -> list[str]:
    """Public routes that climb faster than one block per horizontal course.

    Section 4's rule, and the one vertical thing that is about MOVEMENT rather than composition:
    a guest walks up a slope, and past one-in-one they cannot. A steeper change is legitimate -
    it is simply a different thing, and has to be declared as a stair, a lift, or a ramp so the
    build knows to put treads on it.
    """
    from . import pathgraph
    out = []
    for index, route in enumerate(pathgraph.normalise(routes)):
        if not pathgraph.ROLES.get(route.get("role"), (0, False, False))[1]:
            continue
        a, b = route["a"], route["b"]
        if len(a) < 3 or len(b) < 3:
            continue                      # a level route has no grade to check
        rise = abs(int(b[1]) - int(a[1]))
        run = abs(int(b[0]) - int(a[0])) + abs(int(b[2]) - int(a[2]))
        if rise and rise > run * MAX_GRADE:
            kind = route.get("vertical")
            if kind in {"stairs", "lift", "ramp", "elevator"}:
                continue
            out.append(f"route {index} ({route.get('name') or route.get('role')}): rises {rise} "
                       f"over {run} and is not declared as stairs, a ramp or a lift")
    return out
