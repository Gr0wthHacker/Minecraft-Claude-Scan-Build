"""The eight promotion gates PARK_OVERHAUL.md states, over a planned land.

    "The following are promotion gates, not optional polish: interface, route, capacity,
     mechanics, safety, wayfinding, night, visual."

Each is a named function of the plan returning `{ok, failures, warnings, evidence}`; `run` executes
them all and `promotable` is the single answer. They are deliberately separate rather than one
`validate`, because a land is promoted on its own evidence and a reviewer needs to know WHICH
promise it broke - "the park is not ready" is not a work item.

**A GATE THAT CANNOT BE MEASURED HERE REPORTS THAT, AND DOES NOT PASS QUIETLY.** `visual` is a
render packet a human looks at and `mechanics` is proven by the ride suites and `circuit`; both
return `ok=False` with a stated reason until their evidence is supplied, rather than returning True
because nothing was checked. A gate that grades an unmeasured thing as compliant is worse than no
gate: it converts an unknown into a false assurance.
"""
from __future__ import annotations

from . import bands as B, interfaces as I, pathgraph as P

#: Gate order is the order a reviewer should read them in: geometry first, then behaviour, then
#: judgement. A land that fails `interface` cannot meaningfully be assessed on `wayfinding`.
#:
#: `band` and `grade` come from PARK_VERTICAL_MASTERPLAN.md rather than PARK_OVERHAUL.md, and
#: they are the two that make this a VERTICAL park rather than a flat one with tunnels: what
#: belongs at what altitude, and how steeply a guest may be asked to climb.
ORDER = ("interface", "route", "capacity", "band", "grade", "mechanics",
         "safety", "wayfinding", "night", "visual")

#: Which gates are objectively decided here, and which need evidence from outside this module.
DERIVED = {"interface", "route", "capacity", "band", "grade", "wayfinding"}
EVIDENCE = {"mechanics", "safety", "night", "visual"}


def _result(name, failures, warnings=None, **evidence):
    return {"gate": name, "ok": not failures, "failures": list(failures),
            "warnings": list(warnings or []), "evidence": evidence}


# ------------------------------------------------------------------ the derived gates

def interface(plan: dict) -> dict:
    """Every required anchor exists, is placed, and no two modules own one address."""
    modules = plan["modules"]
    failures = [f"{f['module']}.{f['anchor']}: {f['reason']}" for f in I.missing_anchors(modules)]
    try:
        index = I.anchor_index(modules)
    except ValueError as exc:
        failures.append(str(exc))
        index = {}
    collisions = I.exit_queue_collisions(modules)
    failures.extend(f"{c['module']}.{c['anchor']}: {c['reason']}" for c in collisions)
    typed = {name: I.module_type(m) for m in modules for name in [m.get("name", "?")]}
    return _result("interface", failures, anchors=len(index),
                   modules=len(modules), types=sorted(set(typed.values())))


def route(plan: dict) -> dict:
    """Every public anchor touches the walkable network, and that network is one piece.

    This is rule 2 as a measurement. It is deliberately NOT a walk of the built blocks - that is
    `worldvalidate`'s job and it needs generated artifacts. What it proves is that the plan's own
    circulation reaches every interface the plan declares, which is the thing that has to be true
    before a single block is worth generating.
    """
    modules = plan["modules"]
    routes = P.normalise(plan.get("routes") or [])
    if not routes:
        return _result("route", ["the plan declares no circulation routes"])
    walk = P.walkable(routes)
    hub = next((m for m in modules if m.get("covers") and m["kind"] == "plaza"), None)
    plane = int(hub["at"][1]) if hub else None
    levels = P.levels(routes, plane) if plane is not None else None
    failures = [f"{u['module']}.{u['anchor']} at {u['at']}: {u['reason']}"
                for u in I.unattached(modules, walk, levels)]
    groups = P.components(walk)
    if len(groups) > 1:
        failures.append(f"the walkable network is in {len(groups)} pieces; "
                        "a guest cannot cross between them")
    return _result("route", failures, walkable_cells=len(walk), components=len(groups))


def capacity(plan: dict) -> dict:
    """Widths, roles, queue isolation - `pathgraph.check`, plus how much backstage got built.

    The unserviced-door count is a WARNING, not a failure, and that is a judgement worth stating.
    Rule 5 asks for "protected maintenance access"; the backstage yields to the guest network, so
    on a plot already ten columns short for the transit corridor some rear doors have nothing
    behind them but the neighbour's street. Failing the gate for it would block a promotion on a
    siting decision nobody has been given room to make, and passing it silently would hide the
    one number that says how much backstage the land actually has.
    """
    routes = plan.get("routes") or []
    if not routes:
        return _result("capacity", ["the plan declares no circulation routes"])
    report = P.check(routes)
    warnings = list(report["warnings"])
    from . import circulation
    unserviced = circulation.unserviced_doors(plan["modules"], routes)
    if unserviced:
        warnings.append(f"{len(unserviced)} service doors open onto a guest path with no "
                        "backstage behind them: "
                        + ", ".join(sorted({u["module"] for u in unserviced})))
    return _result("capacity", report["failures"], warnings,
                   unserviced_doors=len(unserviced),
                   **{k: v for k, v in report.items() if k not in {"ok", "failures", "warnings"}})


def band(plan: dict) -> dict:
    """Vertical zoning: the right things at the right altitude, and sky left in the sky.

    PARK_VERTICAL_MASTERPLAN.md section 3. The plane and the land's own footprint come off the
    plan's plaza, which is the one module that IS the ground - deriving them from the modules'
    bounding box would shrink the denominator every time a land got emptier and make an
    under-built park read as over-full.
    """
    modules = plan["modules"]
    hub = next((m for m in modules if m.get("covers") and m["kind"] == "plaza"), None)
    if hub is None:
        return _result("band", ["the plan has no plaza, so it declares no build plane"])
    plane = int(hub["at"][1])
    ox, _oy, oz = hub.get("anchor_offset", (0, 0, 0))
    footprint = max(1, hub["size"][0] * hub["size"][2])
    report = B.check(modules, plane, footprint, I.module_type)
    return _result("band", report["failures"], report["warnings"],
                   **{k: v for k, v in report.items() if k not in {"ok", "failures", "warnings"}})


def grade(plan: dict) -> dict:
    """One block of rise per horizontal course, unless the route says it is stairs or a lift.

    Section 4. A route with no Y on its endpoints is level and has no grade to check - which is
    every route this planner draws today, so the gate passes and SAYS it passed vacuously rather
    than implying the park has been checked for climbs it does not yet have.
    """
    routes = plan.get("routes") or []
    failures = B.grade_failures(routes)
    vertical = [r for r in routes if len(r.get("a", ())) > 2 or len(r.get("b", ())) > 2]
    warnings = []
    if routes and not vertical:
        warnings.append("every route is level: this land has no vertical public circulation "
                        "to check, which is a flat park rather than a passing one")
    return _result("grade", failures, warnings,
                   routes=len(routes), vertical_routes=len(vertical))


def wayfinding(plan: dict) -> dict:
    """A sign or map at every genuine decision point, and nowhere near every facade.

    PARK_HOLLOW.md: "Wayfinding is located at Gate/Arrival Court, Manor/Tower split, Ghost
    Train/Market split, and return loop - not at every facade." So this gate has TWO halves and
    the second one is the unusual direction: a land with a nameplate on every building has not
    solved wayfinding, it has replaced it with noise, and no count of signs can tell them apart.
    A decision point is where the public network branches.
    """
    modules = plan["modules"]
    routes = P.normalise(plan.get("routes") or [])
    signs = [m for m in modules if m.get("gen") == "wayfinding"]
    directional = [m for m in signs if m.get("kind") in {"mapboard", "fingerpost", "noticeboard"}]
    nameplates = [m for m in signs if m.get("kind") == "marker"]
    destinations = [m for m in modules
                    if I.module_type(m) in {"ride", "walkthrough", "shop", "landmark", "arch"}]

    failures, warnings = [], []
    if not directional:
        failures.append("no map, fingerpost or notice board anywhere in the land")

    junctions = _junctions(routes)
    served = 0
    for point in junctions:
        if any(abs(m["at"][0] - point[0]) <= SIGN_REACH and abs(m["at"][2] - point[1]) <= SIGN_REACH
               for m in directional):
            served += 1
    if junctions and served < len(junctions):
        warnings.append(f"{len(junctions) - served} of {len(junctions)} decision points "
                        "have no map or fingerpost within reach")

    # THE NOISE HALF. One nameplate per destination is a land that has given up on wayfinding.
    if destinations and len(nameplates) >= max(3, len(destinations) * 0.6):
        failures.append(f"{len(nameplates)} nameplates for {len(destinations)} destinations: "
                        "signage is per-facade, not at decision points")
    return _result("wayfinding", failures, warnings, directional=len(directional),
                   nameplates=len(nameplates), decision_points=len(junctions),
                   decision_points_served=served)


#: How far a map or fingerpost may stand from a junction and still be read at it.
SIGN_REACH = 12


def _horizontal(point) -> tuple:
    """The (x, z) of a route endpoint, which may be `[x, z]` or `[x, y, z]`.

    **THIS GATE CARRIED THE SAME TWO-DIMENSIONAL BUG IT WAS WRITTEN TO CATCH.** Unpacked as
    `point[0], point[1]`, a three-element endpoint hands back x and Y - so the moment a land grew
    an underground landing, every junction it reported was a coordinate pair that exists nowhere,
    no sign was ever within reach of one, and both side lands warned that all of their decision
    points were unserved. The reading has to be by position, exactly as `pathgraph.cells` does it.
    """
    return (int(point[0]), int(point[2])) if len(point) > 2 else (int(point[0]), int(point[1]))


def _junctions(routes) -> list:
    """Where the public network branches - the places a guest has to choose.

    Two things count, and the second one is the one that matters most. A cell shared by three or
    more routes' ENDPOINTS is a branch; and the point where the two main spines CROSS is the
    land's own crossroads, which is a decision point by construction and is an endpoint of
    nothing - it is the middle of both of them. Measured on the route graph rather than on the
    paved cells, because every cell in the middle of a 5-wide avenue has four paved neighbours
    and would otherwise read as a junction.
    """
    from collections import Counter
    ends = Counter()
    spines = []
    for r in routes:
        if r.get("role") not in {"main_spine", "secondary", "exit"}:
            continue
        a, b = _horizontal(r["a"]), _horizontal(r["b"])
        ends[a] += 1
        ends[b] += 1
        if r.get("role") == "main_spine":
            spines.append((a, b))
    out = [point for point, count in ends.items() if count >= 3]
    for i, (a1, b1) in enumerate(spines):
        for a2, b2 in spines[i + 1:]:
            cross = _crossing(a1, b1, a2, b2)
            if cross and cross not in out:
                out.append(cross)
    return out


def _crossing(a1, b1, a2, b2):
    """Where two axis-aligned segments cross, or None."""
    for (p0, p1), (q0, q1) in ((((a1, b1)), (a2, b2)), ((a2, b2), (a1, b1))):
        if p0[0] == p1[0] and q0[1] == q1[1]:          # one vertical, one horizontal
            x, z = p0[0], q0[1]
            if (min(p0[1], p1[1]) <= z <= max(p0[1], p1[1])
                    and min(q0[0], q1[0]) <= x <= max(q0[0], q1[0])):
                return (x, z)
    return None


# ------------------------------------------------------------------ the evidence gates

def _needs_evidence(name: str, plan: dict, what: str) -> dict:
    supplied = (plan.get("evidence") or {}).get(name)
    if not supplied:
        return _result(name, [f"no {name} evidence supplied: {what}"])
    failures = list(supplied.get("failures") or [])
    if not supplied.get("ok", False) and not failures:
        failures.append(f"{name} evidence reports not ok and names no failure")
    # **THE PRODUCER'S OWN VERDICT KEYS ARE NOT EVIDENCE ABOUT ITSELF.** Splatted whole, an
    # evidence block's `ok`/`failures`/`warnings` collide with this function's own three
    # arguments and the call raises - which is a gate that cannot read the measurement it exists
    # to read. What travels into the report is everything the producer MEASURED.
    measured = {k: v for k, v in supplied.items() if k not in {"ok", "failures", "warnings"}}
    return _result(name, failures, supplied.get("warnings"), **measured)


def mechanics(plan: dict) -> dict:
    """Rails, redstone, fluid containment, inputs/outputs, collection, reset - per ride.

    Proven by `mcbuild circuit`, `fluids`, and the per-ride suites; recorded here so a promotion
    cannot happen without them. A schematic union cannot prove a ride works, and this gate says so
    rather than pretending.
    """
    return _needs_evidence("mechanics", plan,
                           "run the ride suites and `mcbuild circuit` and record the result")


def safety(plan: dict) -> dict:
    return _needs_evidence("safety", plan,
                           "no blocked landing, unsealed water lift, inaccessible essential "
                           "control, unsafe public machinery, or headroom collision")


def night(plan: dict) -> dict:
    return _needs_evidence("night", plan,
                           "propagate block light over the finished land and record the "
                           "spawnable public-path cells")


def visual(plan: dict) -> dict:
    return _needs_evidence("visual", plan,
                           "render arrival, approach, queue, exit, return loop, landmark "
                           "sightline and night overview, and record the review")


GATES = {"interface": interface, "route": route, "capacity": capacity, "band": band,
         "grade": grade, "wayfinding": wayfinding,
         "mechanics": mechanics, "safety": safety, "night": night, "visual": visual}


def run(plan: dict, only=None) -> dict:
    """Every gate, in reading order."""
    names = [n for n in ORDER if not only or n in only]
    results = [GATES[n](plan) for n in names]
    return {"plan": plan.get("name"), "gates": results,
            "ok": all(r["ok"] for r in results),
            "blocking": [r["gate"] for r in results if not r["ok"]]}


def promotable(plan: dict) -> bool:
    return run(plan)["ok"]


def report(result: dict) -> str:
    lines = [f"{result['plan']}: " +
             ("PROMOTABLE" if result["ok"] else "BLOCKED on " + ", ".join(result["blocking"]))]
    for gate in result["gates"]:
        mark = "pass" if gate["ok"] else "FAIL"
        lines.append(f"  {gate['gate']:<11} {mark}")
        for failure in gate["failures"][:12]:
            lines.append(f"      x {failure}")
        if len(gate["failures"]) > 12:
            lines.append(f"      x ... and {len(gate['failures']) - 12} more")
        for warning in gate["warnings"][:6]:
            lines.append(f"      ! {warning}")
    return "\n".join(lines)
