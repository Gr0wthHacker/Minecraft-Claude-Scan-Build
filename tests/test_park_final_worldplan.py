"""The final park plan stays bounded, connected, phaseable - and fully programmed."""
import json
from pathlib import Path

from mcbuild import composition, worldnav, worldschema, worldspec


ROOT = Path(__file__).resolve().parents[1]

#: Every build named in PARK_FINAL_ARCHITECTED_PLAN.md's own inventory tables, plus the two the
#: WorldSpec first shipped without: the Claim Line (the whole Frontier Reach programme) and the
#: Sky Lift Sloth (one of exactly three locked creature moments in the visual ledger).
#:
#: This is a ROSTER, not a count. A bare `== 22` pins a number, and a number cannot say which
#: build went missing when somebody drops one - which is how the reach had no module at all.
PROGRAMME = {
    # Frontier F1-F10
    "Trailhead Gate", "Signal Heron", "Boomtown Spine", "Mining Square", "Mine Coaster",
    "Prospecting Porch", "Assay and Prize Office", "Works Yard",
    # Frontier Reach
    "Claim Line",
    # Midway M1-M9
    "Arrival Court", "Welcome Court", "Snack Window", "Carousel Court", "Sky Lift",
    "Sky Lift Sloth", "Skill Arcade", "Prize Point",
    # Prism Reach
    "Wyrm's Crossing",
    # Prismworks P1-P7
    "Foundry Gate", "Prism Array", "Resonance Vault", "Prism Ascent", "Forge Deck",
    "Service Gallery",
}


def _raw() -> dict:
    return json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8"))


def test_final_park_worldspec_is_strict_connected_and_composed():
    raw = _raw()
    assert worldschema.validate(raw) == []
    plan = worldspec.compile(raw)
    assert plan["site"]["bounds"] == [0, 0, 199, 599]
    assert {m["name"] for m in plan["modules"]} == PROGRAMME
    assert worldnav.audit(plan)["ok"]
    assert composition.assess(plan)["ok"]


def test_live_mechanics_are_recorded_as_gates_not_faked_build_completion():
    gates = _raw()["build_notes"]["gated_systems"]
    assert "runtime minecart/projectile policy" in gates
    assert "grass-payment adapter acceptance" in gates
    assert "Prism Ascent live physics" in gates


def test_final_plan_has_a_large_cheap_first_visual_budget():
    notes = _raw()["build_notes"]
    assert notes["target_block_budget"] >= 200_000
    assert "no decorative terracotta" in notes["budget_policy"]


def test_module_budgets_spend_the_declared_programme():
    """PARK_VISUAL_AND_BUDGET_SPEC.md's table is 265,000 total: 42,000 shared infrastructure and
    11,000 held as a reviewed detail reserve, which leaves 212,000 for the lots themselves. A
    budget that does not add up is a target nobody is actually building to."""
    raw = _raw()
    lots = sum(m["budget"]["blocks"] for m in raw["modules"])
    assert lots == raw["build_notes"]["target_block_budget"] - 42_000 - 11_000


def test_every_public_module_declares_typed_anchors():
    """AGENTS.md: 'Every public module needs ... typed anchors.' An empty anchor list is not a
    module that happens to be simple, it is a module whose interfaces nobody has designed - and
    `worldspec.emit_configs` refuses to emit one, so this failing is a build that cannot start."""
    from mcbuild.design_compiler import anchors as parse

    for module in _raw()["modules"]:
        declared = parse(module["anchors"])
        assert declared, f"{module['name']}: no typed anchors"
        kinds = {a.kind for a in declared}
        assert "visual_front" in kinds, module["name"]
        if module["role"] == "sculpture":
            # a set piece is looked at, not entered - but it must seat on real structure
            assert "support" in kinds, module["name"]
            continue
        assert {"entry", "exit", "maintenance"} <= kinds, module["name"]
        if module["role"] == "ride":
            assert {"queue", "board", "ride_exit"} <= kinds, module["name"]


def test_a_ride_never_discharges_into_its_own_queue():
    """Rule 4 as geometry: queue mouth and discharge sit on opposite flanks of the public face,
    so a queue can never spill into an exit."""
    for module in _raw()["modules"]:
        if module["role"] != "ride":
            continue
        at = {a["name"]: a["position"] for a in module["anchors"]}
        assert at["queue_entry"][2] < at["public_entry"][2] < at["ride_exit"][2], module["name"]


def test_the_reaches_are_transitions_and_carry_no_second_park():
    """'The two reaches are fast, safe transitions with one identity beat each, not mini-parks.'"""
    raw = _raw()
    region = {p["name"]: p["region"] for p in raw["plots"]}
    for name in ("frontier_reach", "prism_reach"):
        modules = [m for m in raw["modules"] if region[m["plot"]] == name]
        assert len(modules) == 1, f"{name} carries {len(modules)} builds"
        assert modules[0]["role"] == "path"


#: PARK_FINAL_ARCHITECTED_PLAN.md programmes the 200 depth once, for every land.
BANDS = {"threshold": (0, 23), "public": (24, 127), "exit": (128, 151),
         "service": (152, 169), "reserve": (170, 199)}


def test_nothing_is_built_into_the_protected_reserve():
    """"V 170-199 is protected rim, terrain, structural support, and void-view reserve."

    Eight lots were originally drawn to V195 and the service spine ran at V175 - through the
    concealed-service band and into the reserve. PARK_FULL_BUILD_SPEC's own whole-park rules
    table agrees with the architected plan ("Service | starts from V 152", "Protected rim |
    V 170-199"); only its LOT SCHEDULE table disagreed, so that table is the error. Building
    into a declared reserve is the harder mistake to undo, which is why it is pinned here."""
    raw = _raw()
    floor = BANDS["reserve"][0]
    for plot in raw["plots"]:
        assert plot["bounds"][2] < floor, f"{plot['name']} reaches V{plot['bounds'][2]}"
    for route in raw["routes"]:
        assert max(p[0] for p in route["points"]) < floor, route["name"]


def test_a_guest_never_has_to_cross_the_service_band_to_use_an_attraction():
    """"Service | starts from V 152 or a concealed rear edge; no guest must cross it to use an
    attraction." A public route inside the service band is that crossing."""
    raw = _raw()
    lo = BANDS["service"][0]
    public = [r for r in raw["routes"] if r["kind"] != "service"]
    for route in public:
        assert max(p[0] for p in route["points"]) < lo, f"{route['name']} enters the service band"


def test_every_lot_sits_in_the_band_its_own_role_belongs_to():
    raw = _raw()
    plots = {p["name"]: p for p in raw["plots"]}
    for module in raw["modules"]:
        x0, _z0, x1, _z1 = plots[module["plot"]]["bounds"]
        if module["role"] == "service":
            assert BANDS["service"][0] <= x0 and x1 <= BANDS["service"][1], module["name"]
        else:
            # a public lot may straddle threshold/public/exit, and never enters service
            assert x1 <= BANDS["exit"][1], f"{module['name']} reaches V{x1}"


def test_a_modules_declared_access_point_is_the_end_of_its_own_access_route():
    """worldnav proves that exact cell joins the island arrival network. The two drifting apart
    is a module nobody can reach, reported as served."""
    raw = _raw()
    routes = {r["name"]: r for r in raw["routes"]}
    for module in raw["modules"]:
        safe = "".join(c.lower() if c.isalnum() else "_" for c in module["name"]).strip("_")
        route = routes.get("access_" + safe)
        assert route, f"{module['name']} has no access route"
        assert module["access_points"] == [list(route["points"][-1])], module["name"]


def test_every_module_footprint_fits_the_lot_it_owns():
    raw = _raw()
    plots = {p["name"]: p for p in raw["plots"]}
    for module in raw["modules"]:
        x0, z0, x1, z1 = plots[module["plot"]]["bounds"]
        ax, az = module["at"]
        w, d = module["footprint"]
        assert x0 <= ax and ax + w - 1 <= x1, module["name"]
        assert z0 <= az and az + d - 1 <= z1, module["name"]
