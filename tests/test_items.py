"""A block name is not an item name, and both languages must agree about it.

`ActionRecipe.itemFor` on the Java side has always known a wall sign is placed from `oak_sign`;
the Python side had no such map, so `craft`, `shop` and `analyze` asked for items that do not
exist and reported 7,965 cells of the park as unobtainable raw material. This pins the rule, and
pins that the file the jar reads is the one this module generates.
"""
import json
import pathlib

from mcbuild import items

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = ROOT / "chunkscan" / "src" / "main" / "resources" / "chunkscan_rules.json"


def test_a_block_is_usually_its_own_item():
    for b in ("stone", "oak_planks", "iron_block", "lantern", "glow_lichen", "vine"):
        assert items.item_for(b) == b


def test_the_cases_that_cost_the_park_seven_thousand_cells():
    assert items.item_for("water") == "water_bucket"
    assert items.item_for("oak_wall_sign") == "oak_sign"
    assert items.item_for("warped_wall_sign") == "warped_sign"
    assert items.item_for("redstone_wire") == "redstone"
    assert items.item_for("water_cauldron") == "cauldron"
    assert items.item_for("redstone_wall_torch") == "redstone_torch"


def test_it_reads_a_full_state_string():
    assert items.item_for("minecraft:oak_wall_sign[facing=east]") == "oak_sign"


def test_it_never_invents_an_item_it_cannot_justify():
    # A block with no placing item comes back UNCHANGED, so the caller reports it as unobtainable
    # rather than being handed something plausible and wrong.
    for b in ("fire", "nether_portal", "piston_head", "end_gateway"):
        assert items.item_for(b) == b


def test_the_shipped_rules_file_carries_this_map():
    # ONE SOURCE. `tools/export_rules.py` writes it; a jar built against a stale file falls back to
    # its own constants, and this fails the moment the two could disagree.
    d = json.loads(RULES.read_text(encoding="utf-8"))
    shipped = d["items"]
    for block, item in items.exceptions().items():
        assert shipped.get(block) == item, f"{block} drifted: shipped {shipped.get(block)!r}"


def test_the_shipped_intentional_set_is_the_python_one():
    from mcbuild import work
    d = json.loads(RULES.read_text(encoding="utf-8"))
    assert set(d["intentional"]) == set(work.INTENTIONAL)
    assert set(d["completion"]) == set(work.COMPLETION)
    assert set(d["multiface"]) == set(work.MULTIFACE)


def test_decided_and_complete_are_kept_apart():
    """Conflating them WAS the drift.

    A design decides a stair's facing; whether it is waterlogged is a bucket somebody has to use
    afterwards. Java carried the second four inside its own INTENTIONAL and this side carried none
    of them, so the same list written twice diverged by exactly those four."""
    from mcbuild import work
    assert not (work.INTENTIONAL & work.COMPLETION)
    assert "facing" in work.INTENTIONAL and "facing" not in work.COMPLETION
    assert "waterlogged" in work.COMPLETION and "waterlogged" not in work.INTENTIONAL
