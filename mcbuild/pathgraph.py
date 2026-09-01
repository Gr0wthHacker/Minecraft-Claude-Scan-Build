"""Capacity-aware public circulation: named routes, minimum widths, and the rules between them.

PARK_OVERHAUL.md rule 6 states the geometry the park owes a visitor:

    "Every land has a 5-block minimum main public spine, 3-block secondary circulation,
     separated 2-3-block queues, distinct exits, and hidden service routes."

and rule 4 states the relationship between them:

    "Queues are never used as through-routes. Ride exits never discharge into incoming queues
     or primary promenades."

The path pass already emitted routes with widths. What it did not carry is the ROLE, and without
a role neither of those rules is expressible: a 3-wide run is a secondary street or a queue
depending only on what it is for, and the whole of rule 4 is about which is which.

**A ROLE IS DECLARED, NOT INFERRED FROM WIDTH.** Inferring it would make the capacity gate a
tautology - every 3-wide route would be "secondary" and no queue could ever be caught being used
as a through-route, because no route would ever be a queue.
"""
from __future__ import annotations

#: role -> (minimum width, is it part of the public through-route network, is it concealed)
ROLES = {
    "main_spine": (5, True,  False),
    "secondary":  (3, True,  False),
    "queue":      (2, False, False),
    "exit":       (3, True,  False),
    "service":    (2, False, True),
}

#: The widest a queue may be before it stops reading as a queue and starts reading as a street.
QUEUE_MAX_WIDTH = 3


def normalise(routes: list[dict]) -> list[dict]:
    """Give every route a role, defaulting only where the plan predates roles.

    A route with no declared role is defaulted from its width and MARKED as defaulted, so the
    capacity gate can report "this park has not declared its circulation" rather than silently
    grading an undeclared park as compliant.
    """
    out = []
    for route in routes:
        entry = dict(route)
        if "role" not in entry:
            entry["role"] = "main_spine" if int(entry.get("width", 3)) >= 5 else "secondary"
            entry["role_defaulted"] = True
        out.append(entry)
    return out


def cells(route: dict) -> set:
    """The plan-view footprint of one straight route, at its declared width."""
    (ax, az), (bx, bz) = route["a"], route["b"]
    half = int(route.get("width", 3)) // 2
    out = set()
    if ax == bx:
        for z in range(min(az, bz), max(az, bz) + 1):
            for dx in range(-half, half + 1):
                out.add((ax + dx, z))
    elif az == bz:
        for x in range(min(ax, bx), max(ax, bx) + 1):
            for dz in range(-half, half + 1):
                out.add((x, az + dz))
    else:
        # An L is two straight legs; the corner cell belongs to both and is added twice, which a
        # set makes free.
        out |= cells({"a": [ax, az], "b": [bx, az], "width": route.get("width", 3)})
        out |= cells({"a": [bx, az], "b": [bx, bz], "width": route.get("width", 3)})
    return out


def footprint(routes: list[dict], roles=None) -> set:
    """Every cell claimed by the routes whose role is in `roles` (all of them when None)."""
    out = set()
    for route in routes:
        if roles is None or route.get("role") in roles:
            out |= cells(route)
    return out


def public(routes: list[dict]) -> set:
    """The through-route network: what a visitor may legitimately be routed along.

    Deliberately excludes queues and service corridors. This is the set every `route` gate walks
    over, and excluding queues from it is what makes "public routing never depends on a queue"
    a fact about the graph rather than a hope.
    """
    return footprint(routes, {r for r, (_w, through, _c) in ROLES.items() if through})


def walkable(routes: list[dict]) -> set:
    """Every cell a guest may legitimately stand on - the through-route network plus queues.

    Standing in a queue and being ROUTED along one are different things, and only the second is
    forbidden. An attachment check run against `public` alone would report a correctly-built
    queue mouth as unreachable, which is the check that cries wolf.
    """
    return public(routes) | footprint(routes, {"queue"})


def service_overlaps(routes: list[dict]) -> list[dict]:
    """Where the concealed network shares cells with the public one, and by how much.

    **A CROSSING IS NOT A CONFLICT.** A service road reaching a building's back door has to get
    there from the perimeter, and the guest paths lie between: real parks cross them at marked
    points. What is forbidden is a service road that RUNS ALONG a public one - a backstage route
    that is really just the street, which is neither concealed nor separate.

    So the measure is per PAIR of routes, and the bound is the size of a crossing patch: two
    routes at right angles share at most `w1 * w2` cells, and anything larger is a shared axis.
    """
    public_routes = [r for r in routes if ROLES.get(r.get("role"), (0, False, False))[1]]
    out = []
    for service in [r for r in routes if r.get("role") == "service"]:
        service_cells = cells(service)
        for other in public_routes:
            shared = service_cells & cells(other)
            if not shared:
                continue
            patch = int(service.get("width", 3)) * int(other.get("width", 3))
            out.append({"service": service.get("name"), "public": other.get("name"),
                        "cells": len(shared), "crossing_limit": patch,
                        "parallel": len(shared) > patch})
    return out


def components(cell_set: set) -> list[set]:
    """Connected components of a cell set, 4-connected - a diagonal is not a step."""
    remaining, out = set(cell_set), []
    while remaining:
        seed = remaining.pop()
        group, frontier = {seed}, [seed]
        while frontier:
            x, z = frontier.pop()
            for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if (nx, nz) in remaining:
                    remaining.discard((nx, nz))
                    group.add((nx, nz))
                    frontier.append((nx, nz))
        out.append(group)
    return out


def check(routes: list[dict]) -> dict:
    """The capacity gate: widths, roles, queue isolation, and one connected public network."""
    routes = normalise(routes)
    failures, warnings = [], []

    defaulted = [r for r in routes if r.get("role_defaulted")]
    if defaulted:
        warnings.append(f"{len(defaulted)} of {len(routes)} routes have no declared capacity role")

    for index, route in enumerate(routes):
        role = route.get("role")
        if role not in ROLES:
            failures.append(f"route {index}: unknown capacity role {role!r}")
            continue
        minimum, _through, _concealed = ROLES[role]
        width = int(route.get("width", 0))
        if width < minimum:
            failures.append(f"route {index} ({role}): width {width} under the {minimum}-block minimum")
        if role == "queue" and width > QUEUE_MAX_WIDTH:
            failures.append(f"route {index} (queue): width {width} exceeds {QUEUE_MAX_WIDTH} "
                            "and reads as a street")

    # RULE 4, AS GEOMETRY. A queue cell that is also a through-route cell IS the queue being used
    # as a through-route; there is no other way for that to happen.
    through = public(routes)
    queue_cells = footprint(routes, {"queue"})
    shared = through & queue_cells
    if shared:
        failures.append(f"{len(shared)} cells are both queue and through-route "
                        "(a queue may not carry a public route)")

    exit_cells = footprint(routes, {"exit"})
    spine = footprint(routes, {"main_spine"})
    if exit_cells & queue_cells:
        failures.append(f"{len(exit_cells & queue_cells)} cells are both an exit and a queue")
    if exit_cells & spine:
        warnings.append(f"{len(exit_cells & spine)} exit cells land on the main spine - "
                        "an exit should meet the spine, not run along it")

    overlaps = service_overlaps(routes)
    parallel = [o for o in overlaps if o["parallel"]]
    for o in parallel:
        failures.append(f"service route {o['service']!r} runs along public route {o['public']!r} "
                        f"for {o['cells']} cells: it is the street, not a backstage route")

    groups = components(through)
    if len(groups) > 1:
        failures.append(f"the public network has {len(groups)} disconnected components")

    return {"ok": not failures, "failures": failures, "warnings": warnings,
            "routes": len(routes), "roles": {role: sum(1 for r in routes if r.get("role") == role)
                                             for role in ROLES},
            "public_cells": len(through), "queue_cells": len(queue_cells),
            "service_cells": len(footprint(routes, {"service"})),
            "service_crossings": len(overlaps) - len(parallel),
            "components": len(groups)}
