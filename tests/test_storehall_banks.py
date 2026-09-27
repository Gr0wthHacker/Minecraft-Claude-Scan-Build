"""The store hall's banks, and the categories that feed them.

`/cscan move` sends a chest to a wall by matching the container's dominant CATEGORY against a bank's
LABEL. Those two strings live in different files — the categories in `tools/export_rules.py`, the
labels in `configs/store_hall.yaml` — and if they drift the match silently stops working: every
container overflows to "whatever slot is free" and the hall stops being sorted at all.

Nothing crashes when that happens, which is exactly why it needs a test.
"""
import json
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "chunkscan", "src", "main", "resources", "chunkscan_rules.json")
CONFIG = os.path.join(ROOT, "configs", "store_hall.yaml")

from mcbuild.gen import GENERATORS                # noqa: E402

UNDER = "out/island_now.litematic"


def _labels():
    with open(CONFIG, encoding="utf-8") as fh:
        return list(yaml.safe_load(fh)["params"]["labels"])


def _categories():
    with open(RULES, encoding="utf-8") as fh:
        return json.load(fh)["categories"]


@pytest.mark.skipif(not os.path.exists(RULES), reason="run tools/export_rules.py")
def test_every_bank_label_has_a_category_that_feeds_it():
    """A label with no matching category takes no traffic at all, and the failure is silent."""
    cats = _categories()
    missing = [l for l in _labels() if l not in cats]
    assert not missing, f"labels with no category in export_rules.py: {missing}"


@pytest.mark.skipif(not os.path.exists(RULES), reason="run tools/export_rules.py")
def test_the_extra_categories_are_deliberate():
    """`dyes and wool` and `tools and redstone` have no wall yet - measured against the real index,
    they are ~42,000 items with nowhere to go. They exist so the overflow can be REPORTED as
    something rather than as 'other'. If a wall is ever labelled for them this test is the record
    of why they were added."""
    cats = set(_categories())
    labels = set(_labels())
    extra = cats - labels
    assert extra == {"dyes and wool", "tools and redstone"}, (
        f"the set of category-without-a-wall changed: {extra}")


@pytest.mark.skipif(not os.path.exists(RULES), reason="run tools/export_rules.py")
def test_a_category_never_claims_a_pattern_another_one_owns():
    """Categories are tried in declaration order, so an overlap means the later one never sees the
    item. `_wood` rather than `wood` is why: bare `wood` would swallow every wool block."""
    cats = _categories()
    assert "wood" not in cats["wood and saplings"], "bare 'wood' would claim wool"
    assert "_wood" in cats["wood and saplings"]
    # `chest` is wood here on purpose - an empty chest IS a wooden item worth banking with planks
    assert "chest" in cats["wood and saplings"]


@pytest.mark.skipif(not os.path.exists(UNDER), reason="needs a capture")
def test_the_hall_records_its_banks_even_when_nothing_is_left_to_build():
    """The hall is built, so it emits nothing - `chests: 0`. A tool that read the DESIGN to find
    the 'food and crops' wall would learn nothing at exactly the point it matters, so the labels
    are recorded as intent rather than as remaining work."""
    cfg = yaml.safe_load(open(CONFIG, encoding="utf-8"))["params"]
    cfg["under"] = UNDER
    c = GENERATORS["storehall"].build(cfg, None)
    banks = c.meta.get("banks")
    assert banks, "no banks recorded"
    assert set(b["label"] for b in banks.values()) >= set(_labels()[:len(banks)])
    for wall, b in banks.items():
        assert wall in ("north", "south", "east", "west")
        assert b["cells"], f"{wall} bank has no cells"
    assert c.meta.get("tiers"), "tiers must be recorded: the mod needs the slot height range"


@pytest.mark.skipif(not os.path.exists(RULES), reason="run tools/export_rules.py")
def test_the_real_index_is_mostly_categorised():
    """Not a guess: measured against the containers actually indexed in game. If this falls a long
    way the taxonomy has stopped tracking what Jack really stores."""
    sd = os.path.expandvars(r"%APPDATA%/CCBlueX/LiquidLauncher/data/gameDir/nextgen/schematics")
    path = os.path.join(sd, "storage.json")
    if not os.path.exists(path):
        pytest.skip("no storage index")
    cats = _categories()

    def cat(item):
        n = item.split(":")[-1]
        for c, keys in cats.items():
            if any(k in n for k in keys):
                return c
        return None

    with open(path, encoding="utf-8") as fh:
        cs = json.load(fh)
    cs = cs.get("containers") or cs
    if isinstance(cs, dict):
        cs = list(cs.values())
    holding = [c for c in cs if (c.get("items") or {})
               and any(k in (c.get("block") or "") for k in ("chest", "barrel", "shulker_box"))]
    if not holding:
        pytest.skip("index holds nothing")
    placed = sum(1 for c in holding if any(cat(i) for i in c["items"]))
    assert placed / len(holding) > 0.85, (
        f"only {placed}/{len(holding)} containers have a category — the taxonomy has drifted")
