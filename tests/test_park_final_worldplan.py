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
    # The transit railway, restored. Jack: "our transportation railway which made sense is
    # completely gone" - and it was: `Park Line` belonged to the retired three-island programme
    # and this WorldSpec had no transit module at all, so a 600-block park offered only walking.
    # One segment per region, on the park's outer edge, because the observation band is fully let
    # and the service band is backstage by contract.
    "Frontier Line", "Frontier Reach Line", "Midway Line", "Prism Reach Line", "Prismworks Line",
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
    # the railway is programme the visual spec never costed, so the target carries it rather than
    # the reserve - which exists for review-led detail - quietly paying for a whole ride system
    assert raw["build_notes"]["target_block_budget"] > 265_000


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
    """"The two reaches are fast, safe transitions with ONE IDENTITY BEAT EACH, not mini-parks."

    So a reach is not "exactly one module" - the architected plan's own Frontier Reach paragraph
    lists the causeway AND the Signal Heron on it, and the Prism Reach is a causeway and the
    Wyrm. What a reach may never carry is a second park: a ride, a game, a shop, a food venue,
    a paid chest or a collection of set pieces. One way through, and one thing to look at."""
    raw = _raw()
    region = {p["name"]: p["region"] for p in raw["plots"]}
    for name in ("frontier_reach", "prism_reach"):
        modules = [m for m in raw["modules"] if region[m["plot"]] == name]
        # the causeway, and the railway that now runs the length of the park past it
        ways = [m for m in modules if m["role"] == "path"]
        assert len(ways) == 2, f"{name} has {len(ways)} ways through"
        assert sum(1 for m in ways if m["generator"] == "transit") == 1, name
        beats = [m["role"] for m in modules if m["role"] != "path"]
        assert len(beats) <= 1, f"{name} carries {len(beats)} identity beats"
        assert set(beats) <= {"sculpture"}, f"{name} carries a {beats} - that is a mini-park"


def test_the_park_declares_its_own_continuous_ground():
    """"Big gaps that lead to void because nothing has been placed."

    The park was route ribbons and lot islands over 17,726 void columns, and because every street
    was a DRAWN LINE, one of them - a "programme loop" sweeping the full 200 depth at ten U-lines
    - crossed all twenty-four buildings. A park has continuous ground and the streets are whatever
    is not a building. The floor is declared here, not merely rendered, or every check keeps
    measuring ribbons: composition was reporting "no route approach" for plots standing in the
    middle of a paved floor."""
    raw = _raw()
    floor = next((r for r in raw["routes"] if r["name"] == "park_floor"), None)
    assert floor, "the park has no declared ground"
    assert floor["width"] >= 128, floor["width"]
    assert not any(r["name"] == "public_program_loop" for r in raw["routes"])


def test_no_public_route_is_drawn_through_a_building():
    """Every one of the twenty-four modules had a route running through its own footprint. That is
    what a building blocking a walkway IS, and nothing checked it: the clash test compared modules
    to modules and never to routes."""
    from mcbuild import worldspec
    plan = worldspec.compile(_raw())
    floor = {"park_floor", "park_backstage"}
    cells = {}
    for route in plan["routes"]:
        if route["name"] in floor or route["kind"] == "service":
            continue          # the ground is under everything by design; backstage is not a guest way
        for cell in route.get("footprint", route.get("cells", [])):
            cells.setdefault(tuple(cell), set()).add(route["name"])
    for module in plan["modules"]:
        if module["role"] == "path":
            continue          # a causeway IS the way through it; a route crossing one is the point
        x0, z0 = module["at"]; w, d = module["footprint"]
        through = {r for c, rs in cells.items()
                   if x0 + 2 <= c[0] < x0 + w - 2 and z0 + 2 <= c[1] < z0 + d - 2 for r in rs}
        assert not through, f"{module['name']} has {sorted(through)} drawn through it"
