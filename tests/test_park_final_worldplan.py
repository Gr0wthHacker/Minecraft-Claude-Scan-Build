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
    """"The two reaches are fast, safe transitions with ONE IDENTITY BEAT EACH, not mini-parks."

    So a reach is not "exactly one module" - the architected plan's own Frontier Reach paragraph
    lists the causeway AND the Signal Heron on it, and the Prism Reach is a causeway and the
    Wyrm. What a reach may never carry is a second park: a ride, a game, a shop, a food venue,
    a paid chest or a collection of set pieces. One way through, and one thing to look at."""
    raw = _raw()
    region = {p["name"]: p["region"] for p in raw["plots"]}
    for name in ("frontier_reach", "prism_reach"):
        modules = [m for m in raw["modules"] if region[m["plot"]] == name]
        roles = [m["role"] for m in modules]
        assert roles.count("path") == 1, f"{name} has {roles.count('path')} ways through"
        beats = [r for r in roles if r != "path"]
        assert len(beats) <= 1, f"{name} carries {len(beats)} identity beats"
        assert set(beats) <= {"sculpture"}, f"{name} carries a {beats} - that is a mini-park"
