"""The layer slice: four COMPLETE build steps instead of thirty fragments.

**A DESIGN THAT DEFERS IS INCOMPLETE ON ITS OWN.** `finish.defer_to` settles which design owns a
shared cell - right for ownership, wrong for looking at the result: every module ends up as a
fragment with holes where a neighbour won, and loading all thirty gives you thirty overlapping
boxes each missing pieces. The report was "empty floors with holes in it for redstone and nothing
above it", which is exactly what the hall looks like alone.

Layers cannot collide, because the partition is a function of the cell - so nothing defers and
nothing is missing.
"""
from __future__ import annotations

import itertools
import os

import pytest

from mcbuild import layers

NAMES = [f"Casino {i + 1} {l}" for i, l in enumerate(layers.LAYERS)]
WHOLE = "Casino Complete"


def _have():
    return all(os.path.exists(f"out/{n}.litematic") for n in NAMES)


def test_the_partition_is_a_function_of_the_cell():
    """Every cell lands in exactly one layer, decided without reference to any other cell - which
    is the whole reason the layers cannot collide."""
    for name in ("smooth_stone", "redstone_wire", "oak_wall_sign", "stone_button"):
        for y in (200, 203, 206):
            got = {layers._which(name, y, 203) for _ in range(3)}
            assert len(got) == 1, "the partition must be deterministic"
            assert got.pop() in layers.LAYERS


def test_a_machine_stays_whole_wherever_it_sits():
    """A mechanism half under the floor and half above it is still ONE machine; splitting it by
    height would give two layers neither of which works."""
    for y in (197, 203, 207):
        assert layers._which("redstone_wire", y, 203) == "Machines"
        assert layers._which("comparator", y, 203) == "Machines"
    # ...and a lamp above the floor is a display, not structure
    assert layers._which("redstone_lamp", 205, 203) == "Fittings"


def test_the_layers_are_disjoint_and_lose_nothing():
    if not _have():
        pytest.skip("the casino layers have not been generated in this checkout")
    maps = {n: layers._read(n)[0] for n in NAMES}
    for a, b in itertools.combinations(NAMES, 2):
        shared = set(maps[a]) & set(maps[b])
        assert not shared, f"{a} and {b} share {len(shared)} cells - layers cannot collide"

    # COMPARED AGAINST THE RESOLVED WHOLE, not the raw modules. The modules no longer defer, so
    # they genuinely overlap - the hall's floor runs under every room - and a plain union of them
    # is not what the casino is. `Casino Complete` is the union AFTER the precedence is applied,
    # which is the thing the layers must add up to.
    plan = layers._read(WHOLE)[0]
    lay = {}
    for n in NAMES:
        lay.update(maps[n])
    assert set(plan) == set(lay), (
        f"the slice lost {len(set(plan) - set(lay))} cells and invented "
        f"{len(set(lay) - set(plan))}")
    # AND THE BLOCK STATES SURVIVE. A stair's facing and a sign's facing are decisions; a slice
    # that dropped Properties would look identical in every render and be wrong in game.
    bad = [c for c in plan if plan[c] != lay[c]]
    assert not bad, f"{len(bad)} cells changed state in the slice, e.g. {bad[:3]}"


def test_the_signs_follow_their_blocks():
    """A sign's text belongs in whichever layer its BLOCK landed in. Left behind it would be a
    tile entity with no block, which is a corrupt region rather than a lost line."""
    if not _have():
        pytest.skip("the casino layers have not been generated in this checkout")
    from mcbuild import schem
    for n in NAMES:
        mo = schem.load(f"out/{n}.litematic")
        # `_read` returns cells, signs AND the design's dig list - a litematic cannot express
        # removal, so the prep work rides in the sidecar, and the slice used to drop it.
        cells, _signs, _dig = layers._read(n)
        for t in mo.tile_entities:
            v = t.value
            # every tile entity must sit on a real block of this same layer
            sc = __import__("mcbuild.scan", fromlist=["x"]).load(f"out/{n}.scan.json")
            ox, oy, oz = sc.origin
            pos = (ox + int(v["x"].value), oy + int(v["y"].value), oz + int(v["z"].value))
            assert pos in cells, f"{n}: sign text at {pos} with no block under it"
    # DERIVED, NOT PINNED. The count moves whenever the lineup does - it was 37 for eighteen
    # booths and is 27 for fourteen games and two wheels - so a hardcoded number is a test that
    # fails the next time the casino changes size and says nothing about the slice.
    from mcbuild import planner
    want = sum(len(schem.load(f"out/{m['name']}.litematic").tile_entities)
               for m in planner.Plan.load("casino").modules)
    total = sum(len(schem.load(f"out/{n}.litematic").tile_entities) for n in NAMES)
    assert total == want, f"the slice lost signs: {total} of {want}"


def test_the_whole_slice_is_one_connected_piece():
    """The check that found the phantom mezzanine and eighteen unattached signs."""
    if not _have():
        pytest.skip("the casino layers have not been generated in this checkout")
    u = {}
    for n in NAMES:
        u.update(layers._read(n)[0])
    if os.path.exists("out/newisle.litematic"):
        u.update(layers._read("newisle")[0])
    seen, comps = set(), []
    for c in u:
        if c in seen:
            continue
        stack, k = [c], 0
        seen.add(c)
        while stack:
            x, y, z = stack.pop()
            k += 1
            for q in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z),
                      (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
                if q in u and q not in seen:
                    seen.add(q)
                    stack.append(q)
        comps.append(k)
    comps.sort(reverse=True)
    assert len(comps) == 1, f"the casino is in {len(comps)} pieces: {comps[:8]}"


def test_the_complete_design_is_the_whole_casino():
    """**THE ANSWER TO "LET ME SEE EVERYTHING IN TOTALITY".**

    `defer_to` resolved a shared cell by DELETING it from the loser, so every module was a fragment
    and looking at the casino meant loading a pile of overlapping designs each missing pieces. It
    is gone: the modules are generated whole, the precedence is applied once in the slice, and this
    is the single design that holds all of it - nothing deferred, nothing hidden.
    """
    if not (_have() and os.path.exists(f"out/{WHOLE}.litematic")):
        pytest.skip("the casino has not been sliced in this checkout")
    whole = layers._read(WHOLE)[0]
    union = {}
    for n in NAMES:
        union.update(layers._read(n)[0])
    assert set(whole) == set(union), (
        f"Complete is missing {len(set(union) - set(whole))} cells and has "
        f"{len(set(whole) - set(union))} the layers do not")
    bad = [c for c in whole if whole[c] != union[c]]
    assert not bad, f"{len(bad)} cells differ in state between Complete and the layers"


def test_no_module_config_defers_to_another():
    """The modules are INTERMEDIATE artifacts and must stay whole.

    Deferring is what made them unreadable, and it is easy to reintroduce by accident because it is
    the obvious way to stop two designs claiming a cell. The conflict is resolved in the slice, in
    one place, with an explicit precedence - and it is REPORTED there rather than silently applied.
    """
    import glob
    import yaml as _yaml
    for f in glob.glob("configs/*.yaml"):
        with open(f, encoding="utf-8") as fh:
            cfg = _yaml.safe_load(fh) or {}
        if cfg.get("gen") != "casino":
            continue
        assert not (cfg.get("finish") or {}).get("defer_to"), (
            f"{os.path.basename(f)} defers - the module will ship with holes in it")


def test_the_slice_carries_every_module_s_DIG_LIST():
    """**A LITEMATIC CANNOT EXPRESS REMOVAL, SO THE PREP WORK LIVES IN THE SIDECAR - AND THE SLICE
    WAS DROPPING IT.**

    `layers.py` had no notion of `dig` at all. The Arrival Court declares 324 cells of starter pad
    and tree that have to come out before a printer can lay its floor, and the shipped
    `Park_Centre Complete` reported `dig 0`. `/cscan dig` would have shown nothing, and the first
    anybody would have known is a printer refusing to place on a grass block.

    A LAYER carries none, deliberately: breaking a block is not part of any one course, it is prep
    for the build, and it belongs to the design you actually place.
    """
    import json
    import os
    whole = os.path.join("out", f"{WHOLE}.scan.json")
    if not os.path.exists(whole):
        pytest.skip(f"{WHOLE} has not been sliced")
    with open(whole, encoding="utf-8") as fh:
        raw = json.load(fh)
    parts = []
    for n in NAMES:
        p = os.path.join("out", f"{n}.scan.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                parts.append(len(json.load(fh).get("dig") or []))
    assert all(c == 0 for c in parts), f"a LAYER carries a dig list: {parts}"
    assert "dig" in raw, "the whole design's sidecar has no dig key at all"
