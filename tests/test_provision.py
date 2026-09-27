"""Provisioning: what a design needs before anyone can build it.

THE LOOP IS A LAST MILE WITH NO SUPPLY CHAIN. Every stall, message-spam and flight fix of the last
month was the end of a journey whose goods were never made: park-local chests covered 9 of 180
materials and three quarters of the design had no reachable source, and the loop's only way to say
so was to fly there, find nothing placeable and report a dead end.
"""
import collections

import pytest

from mcbuild import provision, recipes


def _pkg(want, have=None):
    """A Package built straight from a want-list, with no design on disk."""
    p = provision.Package("fixture")
    p.want = collections.Counter(want)
    p.cells_total = sum(p.want.values())
    p.have = collections.Counter(have or {})
    short = collections.Counter()
    for item, n in p.want.items():
        if n > p.have.get(item, 0):
            short[item] = n - p.have.get(item, 0)
    p.short = short
    for item in short:
        p.source[item] = provision._classify(item, {})
    p.cells_ready = sum(max(0, n - short.get(i, 0)) for i, n in p.want.items())
    return p


def test_coverage_is_cells_not_materials():
    # A design one block short of one material is not a design that is 50% short: the number that
    # decides whether a session is worth starting is how many CELLS can go in.
    p = _pkg({"stone": 100, "oak_planks": 100}, {"stone": 100, "oak_planks": 99})
    assert p.cells_ready == 199
    assert 0.99 < p.coverage < 1.0


def test_a_shortfall_is_classified_by_how_it_can_actually_be_got():
    assert provision._classify("stone_bricks", {}) == "craft"
    assert provision._classify("moss_block", {}) == "farm"
    # PRICED IS BUYABLE, and only then: `prices.json` does not exist until somebody walks the shop.
    assert provision._classify("obsidian", {}) == "none"
    assert provision._classify("obsidian", {"obsidian": 12}) == "buy"


def test_it_never_guesses_a_source():
    """A material with no recipe, no price and no stock is reported as having NONE.

    Folding it into "farm it" would turn "we do not know" into a confident wrong answer, which is
    the failure this module exists to avoid - and it is what the ten park gates already do with
    evidence they do not have."""
    assert provision._classify("bedrock", {}) == "none"
    assert "bedrock" not in provision.FARMED


def test_smelting_is_told_apart_from_crafting():
    # Both are "you can make it", and they are different trips: one wants a furnace and fuel.
    if recipes.available():
        assert provision._classify("stone", {}) == "smelt"


def test_a_covered_design_says_so_rather_than_listing_nothing():
    p = _pkg({"stone": 10}, {"stone": 10})
    assert "nothing is short" in p.report()


def test_the_report_names_every_source_that_has_anything_in_it():
    p = _pkg({"moss_block": 10, "stone_bricks": 4, "bedrock": 1})
    r = p.report()
    assert "FARM" in r and "CRAFT" in r and "NONE" in r


@pytest.mark.skipif(not recipes.available(), reason="no recipe data - run tools/extract_recipes.py")
def test_crafting_from_stock_counts_as_covered():
    """The whole point of resolving the SHORTFALL rather than the design.

    Sixty-four planks you can make from sixteen logs you own are not a shortfall, and reporting
    them as one sends you shopping for something already in a chest."""
    p = provision.Package("x")
    p.want = collections.Counter({"oak_planks": 64})
    p.cells_total = 64
    p.have = collections.Counter({"oak_log": 64})
    made = recipes.plan(collections.Counter({"oak_planks": 64}), p.have)
    assert not made.short, f"still short: {dict(made.short)}"
