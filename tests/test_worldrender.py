from __future__ import annotations

from mcbuild import visual_grade, worldrender, worldspec, worldexport


def test_worldspec_routes_render_to_chunked_skyblock_artifacts(tmp_path):
    spec = {"name": "Route", "site": {"anchor": [0, 70, 0], "bounds": [0, 0, 20, 20], "entry_points": [[2, 10]]},
            "regions": [{"name": "land", "bounds": [0, 0, 20, 20]}], "plots": [],
            "routes": [{"name": "bridge", "kind": "bridge", "width": 3, "points": [[2, 70, 10], [18, 72, 10]]}], "modules": []}
    world = worldrender.infrastructure(worldspec.compile(spec))
    paths = worldexport.export_chunks(world, tmp_path)
    from mcbuild import schem
    assert paths and visual_grade.assess(schem.load(paths[0]), required_lights=0)["ok"]


# --------------------------------------------------------------------- the park's own layer 1

def _park_plan():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    return worldspec.compile(json.loads((root / "park_final.world.json").read_text(encoding="utf-8")))


def _cells(world):
    return [(pos, state) for chunk in world.chunks.values() for pos, state in chunk.items()]


def test_the_shared_infrastructure_spends_its_declared_programme():
    """PARK_VISUAL_AND_BUDGET_SPEC gives 42,000 blocks to "shared paths, retaining edges,
    service, lighting, safety". A deck-only render was 17,501 - a floating ribbon with no edge,
    nothing under it and no light, which is exactly the "objects on void" that line exists to
    prevent."""
    world = worldrender.infrastructure(_park_plan())
    total = sum(len(chunk) for chunk in world.chunks.values())
    assert 36_000 <= total <= 48_000, total


def test_every_infrastructure_block_is_cheap_1_19_and_not_currency():
    from mcbuild import blocks, palette
    world = worldrender.infrastructure(_park_plan())
    used = {state.split("[")[0].replace("minecraft:", "") for _pos, state in _cells(world)}
    assert not [b for b in used if not blocks.available(b)]
    # dirt and grass are CURRENCY on this server: paving 600 blocks of park in them is spending
    # money on a floor.
    assert not [b for b in used if not blocks.spendable(b)]
    assert not [b for b in used if palette.tier(b) == "expensive"]


def test_public_paving_stands_on_something():
    """Layer 1 is the platform. A deck course over open void is a ribbon a player falls off."""
    world = worldrender.infrastructure(_park_plan())
    plane = _park_plan()["site"]["build_plane"]
    deck = [(x, y, z) for (x, y, z), _s in _cells(world) if y == plane]
    assert deck
    missing = [p for p in deck[:2000] if world.get(p[0], p[1] - 1, p[2]) == "minecraft:air"]
    assert not missing, missing[:5]


def test_the_spine_carries_an_edge_on_its_own_perpendicular():
    """The park spine runs along z, so its width is in x. Offsetting the kerb always in z put
    the edge ahead of and behind a walker - on the deck - where the deck test then swallowed it,
    so the main spine of the park silently had no edge at all."""
    plan = _park_plan()
    world = worldrender.infrastructure(plan)
    plane = plan["site"]["build_plane"]
    for z in (60, 100, 300, 500):
        assert world.get(9, plane, z) != "minecraft:air", z
        assert world.get(15, plane, z) != "minecraft:air", z


def test_the_spine_visibly_changes_palette_at_every_land_edge():
    """PARK_FULL_BUILD_SPEC: the spine "visibly changes palette at U 170, 215, 385, and 430".
    A spine that reads the same for 600 blocks tells a player nothing about where they are."""
    plan = _park_plan()
    world = worldrender.infrastructure(plan)
    plane = plan["site"]["build_plane"]
    seen = [world.get(12, plane, z) for z in (100, 190, 300, 400, 500)]
    assert len(set(seen)) > 1
    # frontier and midway differ across U215; prism reach and prismworks share one dark palette
    assert seen[0] != seen[2]
    assert seen[2] != seen[3]


def test_the_public_network_is_lit_at_a_stated_interval():
    world = worldrender.infrastructure(_park_plan())
    lights = [p for p, s in _cells(world) if s in ("minecraft:lantern", "minecraft:soul_lantern")]
    assert len(lights) > 400, len(lights)


def test_the_protected_rim_is_a_retaining_edge_not_a_wall_round_the_park():
    """V170-199 is "support, terrain, void safety, sightline protection". Only its inner face is
    built: a solid 600-block wall would be a wall around the park, and would consume the
    sightlines the same band exists to protect."""
    plan = _park_plan()
    world = worldrender.infrastructure(plan)
    plane = plan["site"]["build_plane"]
    assert world.get(worldrender.RIM_FROM, plane, 300) != "minecraft:air"
    for x in (worldrender.RIM_FROM + 6, 185, 198):
        assert world.get(x, plane, 300) == "minecraft:air", x
