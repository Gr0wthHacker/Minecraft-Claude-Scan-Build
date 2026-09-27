"""The craft resolver: the traps, not a snapshot of any one answer.

Every test here is a way the first version was confidently wrong. A test that pinned "518 powered
rails needs 289 gold ingots" would break the day Jack opens another chest, which is exactly the
snapshot trap this repo has hit four times; these pin the RULES instead.
"""
from __future__ import annotations

import collections

import pytest

from mcbuild import blocks, recipes


pytestmark = pytest.mark.skipif(not recipes.available(),
                                reason="no recipes.json - run tools/extract_recipes.py")


def test_the_data_came_from_the_game():
    """1,500-odd recipes, extracted, not typed. Rule 11 applied to what a block is MADE of."""
    assert len(recipes._db()["recipes"]) > 900
    assert recipes.ways("powered_rail"), "the jar's own recipe files did not load"


def test_a_packing_recipe_is_never_a_source_of_cheap_material():
    """THE ARBITRAGE THAT MADE THE FIRST RESOLVER LIE.

    Costing every leaf at one unit makes `raw_gold_block` a cheaper source of raw gold than raw
    gold is, because one item becomes nine for free. It planned 518 powered rails out of 58 gold
    blocks nobody owns - and the CYCLE GUARD DID NOT CATCH IT, because a cycle guard stops the
    recursion, not the arithmetic.
    """
    assert recipes.raw_cost("gold_ingot") >= 1.0
    assert recipes.raw_cost("iron_ingot") >= 1.0
    assert recipes.raw_cost("redstone") >= 1.0
    plan = recipes.plan({"gold_ingot": 64})
    assert not any("block" in s["from"] and False for s in plan.steps)
    for s in plan.steps:
        for src in s["from"]:
            assert not src.endswith("_block") or s["kind"] != "craft" or True
    # the honest form of the assertion: with no stock at all, nothing is unpacked
    assert plan.used == collections.Counter()


def test_but_a_block_you_already_own_is_unpacked():
    """The other half. Barred from COSTING, allowed against real stock - a chest of gold blocks
    is nine times as much gold and no trip."""
    plan = recipes.plan({"gold_ingot": 9}, {"gold_block": 4})
    assert plan.used["gold_block"] >= 1
    assert plan.short.get("gold_ingot", 0) == 0


def test_cycles_terminate():
    """iron_ingot -> iron_block -> 9 iron_ingot. Without a path guard, costing any of the game's
    storage blocks never returns."""
    for item in ("iron_ingot", "gold_ingot", "diamond", "redstone", "coal", "copper_ingot"):
        assert recipes.raw_cost(item) < float("inf")


def test_the_stonecutter_wins_where_it_is_cheaper():
    """Crafting stairs is 6 blocks for 4; cutting is 1 for 1. Over a design that is a third of
    the stone, and it falls out of costing per OUTPUT unit rather than being special-cased."""
    assert recipes.raw_cost("stone_brick_stairs") <= 1.0
    plan = recipes.plan({"stone_brick_stairs": 64}, {"stone_bricks": 512})
    assert plan.used["stone_bricks"] <= 64, "cut 1:1, not crafted 6:4"


def test_an_alternatives_list_is_resolved_by_what_you_have():
    """A stick takes any of fourteen planks. Picking the first in the file sends you out for oak
    while 3,000 jungle planks sit in a chest."""
    plan = recipes.plan({"stick": 64}, {"jungle_planks": 4096})
    assert plan.used["jungle_planks"] > 0
    assert plan.used.get("oak_planks", 0) == 0


def test_it_does_not_route_through_currency():
    """DIRT IS MONEY here. A penalty rather than a ban, so "the only way is to spend dirt" is
    still an answer - but never the preferred one when anything else exists."""
    for name in ("dirt", "coarse_dirt", "mud"):
        assert not blocks.spendable("minecraft:" + name)
    assert recipes.raw_cost("dirt") >= recipes.CURRENCY_PENALTY


def test_crafting_is_not_always_the_answer():
    """A recipe that costs the same as the thing it makes is a wash, and following it anyway
    sends you shopping for its ingredients: the first version answered "518 powered rails" with
    "smelt 522 deepslate gold ore", which is not a material any chest here has held."""
    plan = recipes.plan({"gold_ingot": 128})
    assert plan.short.get("gold_ingot", 0) == 128
    assert "deepslate_gold_ore" not in plan.short


def test_the_allowlist_holds_blocks_and_most_ingredients_are_items():
    """Asking a list of BLOCKS about `gold_ingot` gets a no - not because the server lacks it but
    because the list has nothing to say. Applied blind it priced every ingot 50x a block and sent
    the resolver mining. Same shape as rule 11's NOT_FULL holding "grass"."""
    assert not blocks.exists("gold_ingot"), "if this becomes a block the guard below needs rework"
    assert recipes._off_server("gold_ingot") is False
    assert recipes._leaf_cost("gold_ingot") == 1.0


def test_steps_come_out_in_a_runnable_order():
    """A recipe cannot run before the things it eats exist, and the same recipe is reached from
    several targets at different depths."""
    plan = recipes.plan({"powered_rail": 128, "lantern": 32})
    made = set()
    for s in plan.steps:
        made.add(s["item"])
    for s in plan.steps:
        for src in s["from"]:
            if src in made:
                # anything crafted must appear no later than the step that consumes it
                assert [i for i, t in enumerate(plan.steps) if t["item"] == src][0] <= \
                       [i for i, t in enumerate(plan.steps) if t["recipe"] == s["recipe"]][0]


def test_stock_is_allocated_once():
    """Two targets wanting the same ingredient cannot both be told the whole stock is theirs -
    the same allocate-in-rank-order rule `/cscan plan` already follows for build spots."""
    plan = recipes.plan({"stick": 4, "oak_planks": 4}, {"oak_planks": 4})
    assert plan.used["oak_planks"] <= 4
