"""The craft resolver's cost model.

It planned **3,358 iron pickaxes** - 10,074 iron ingots where 379 would do - to make 426 lanterns,
on the island whose scarce metal is iron. Two faults compounded: a leaf price of 1 was a FLOOR
under everything, so a crafted tool cost the same as the metal in it; and `mark_reversible` barred
`iron_ingot -> 9 iron_nugget` from the cost model along with the packing arbitrage it was written
for, leaving smelting a tool as the only route to a nugget.
"""
from mcbuild import recipes


def test_a_crafted_tool_is_not_as_cheap_as_the_metal_in_it():
    # THE FLOOR. `best` started at the leaf cost and only came down, so anything whose recipe cost
    # more than one unit stayed at one.
    assert recipes.raw_cost("iron_pickaxe") > recipes.raw_cost("iron_ingot")
    assert recipes.raw_cost("iron_pickaxe") >= 3 * recipes.raw_cost("iron_ingot")


def test_a_nugget_is_a_ninth_of_an_ingot():
    # The legitimate unpacking that the arbitrage guard had barred.
    assert recipes.raw_cost("iron_nugget") == recipes.raw_cost("iron_ingot") / 9


def test_unpacking_is_never_a_free_source_of_the_thing_it_packs():
    # THE ARBITRAGE THE GUARD EXISTS FOR. `raw_gold_block` has no recipe but packing raw gold -
    # the cycle we are inside - so its price falls back to a leaf, and dividing a made-up number
    # by nine is where the free gold came from.
    assert recipes.raw_cost("raw_gold") == 1.0
    assert recipes.raw_cost("raw_gold_block") >= recipes.raw_cost("raw_gold")


def test_a_lantern_is_planned_from_ingots_rather_than_from_smelted_tools():
    """426 lanterns want about 379 ingots. It planned 10,074, through 3,358 pickaxes.

    Given the ingots, since crafting from NOTHING is honestly reported as being short of the
    lantern - which is the wash test doing its job, and a separate question from which route the
    cost model picks once there is anything to work with."""
    plan = recipes.plan({"lantern": 426}, {"iron_ingot": 500, "torch": 500})
    made = {s["item"] for s in plan.steps}
    assert "iron_pickaxe" not in made, "smelting tools for nuggets is the bug this pins"
    ingots = sum(n for s in plan.steps for k, n in s["from"].items() if k == "iron_ingot")
    assert 0 < ingots < 500, f"426 lanterns want ~379 ingots, planned {ingots}"


def test_smelting_a_tool_is_never_the_cheapest_route_to_a_nugget():
    """The route the cost model must not pick, whatever the stock.

    A pickaxe is 3.25 and unpacking an ingot is a ninth of one; the bug was that the leaf floor
    priced them the same."""
    assert recipes.raw_cost("iron_nugget") < recipes.raw_cost("iron_pickaxe") / 10


def test_holding_one_is_not_permission_to_make_thousands():
    # The wash escape used to fire on ANY stock of ANY ingredient, so a single iron pickaxe in a
    # chest authorised manufacturing 3,358 more of them.
    plan = recipes.plan({"iron_nugget": 9000}, {"iron_pickaxe": 1})
    picks = sum(s["made"] for s in plan.steps if s["item"] == "iron_pickaxe")
    assert picks == 0, f"planned {picks} pickaxes off one held pickaxe"
