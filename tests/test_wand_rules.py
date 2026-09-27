"""The mod's copy of the placement rules must not drift from the Python's.

`chunkscan_rules.json` is what the steak wand consults before it fills a box: what it must not
write over, what is currency on this server, what the 1.19 server actually has. All three already
exist in Python, and a Java retype of any of them is a second list that disagrees the first time
either is edited.

This project has been bitten by that exact shape before, which is why `proportions.measure` and
`rubric.score` are shared entry points rather than two tools each measuring for themselves. Here
the same discipline is enforced from the other end: one generator, one test, and the export cannot
be quietly forgotten.

    python tools/export_rules.py        # if this test fails, that is the fix
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "chunkscan", "src", "main", "resources", "chunkscan_rules.json")

from mcbuild import blocks                      # noqa: E402
from mcbuild.gen import protect                 # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(RULES),
                                reason="run tools/export_rules.py")


def _shipped():
    with open(RULES, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_protected_set_matches_protect_py():
    assert _shipped()["protected"] == sorted(protect.MECHANISM)


def test_the_currency_set_matches_blocks_py():
    """DIRT IS CURRENCY here. The blocks are real, legal, in 1.19 and placeable, so every other
    check the wand makes passes them - this list is the only thing that can say no."""
    assert _shipped()["economy"] == sorted(blocks.ECONOMY)


def test_the_server_allowlist_matches_and_stays_provisional():
    src = json.load(open(os.path.join(ROOT, "mcbuild", "data", "server_blocks.json"), encoding="utf-8"))
    shipped = _shipped()
    assert shipped["server_blocks"] == sorted(src["blocks"])
    # The mod only WARNS while this is false. If a real 1.19 registry dump ever flips it, the mod's
    # posture has to be revisited deliberately - not inherited by accident.
    assert shipped["server_authoritative"] == bool(src.get("authoritative", False))


def test_the_export_is_reproducible():
    """Re-running the exporter must not change the file - otherwise 'is it stale?' is unanswerable."""
    before = open(RULES, encoding="utf-8").read()
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "export_rules.py")],
                   cwd=ROOT, check=True, capture_output=True)
    assert open(RULES, encoding="utf-8").read() == before, "export_rules.py is not deterministic"


def test_wool_is_protected_because_a_wool_block_may_be_a_silencer():
    """The rule that produced protect.py: `gray_wool` looked like ceiling decoration and was the
    sound shielding on the tree's sculk sensor. Substring matching is what makes that hold."""
    assert protect.is_protected("minecraft:gray_wool[color=gray]")
    assert any("wool" == k for k in _shipped()["protected"])


def test_a_plain_building_block_is_not_protected():
    for n in ("minecraft:stone_bricks", "minecraft:deepslate_bricks", "minecraft:smooth_stone"):
        assert not protect.is_protected(n), f"{n} would be unfillable"
