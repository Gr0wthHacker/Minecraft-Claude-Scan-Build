"""The empty-ground cleanup: the palette, the openness gate, and what the two passes shipped.

`gen/parkgreen.py` is the first pass in this repo whose DENSITY is a measurement rather than a
noise field, so the thing most worth pinning is that the measurement and the pass cannot drift
apart - `tools/park_empty.py` finds the holes with the same distance transform the generator
plants from, and if the two ever disagreed the audit would be reporting on a park nobody built.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pytest
import yaml

from mcbuild import blocks, palette, schem
from mcbuild.gen import parkgreen as pg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
PARK = os.path.join(OUT, "Park Complete.litematic")
GREEN = os.path.join(OUT, "PF Park Green.litematic")
RIM = os.path.join(OUT, "PF Park Rim Green.litematic")


def _cfg(name):
    return yaml.safe_load(open(os.path.join(ROOT, "configs", name), encoding="utf-8"))


def _shipped(path):
    """(cells by world coordinate, names) for a shipped design, or None if it is not there."""
    side = os.path.splitext(path)[0] + ".scan.json"
    if not (os.path.exists(path) and os.path.exists(side)):
        return None
    o = json.load(open(side))["origin"]
    m = schem.load(path)
    names = [n.split(":")[-1] for n in m.names]
    ys, zs, xs = m.ids.nonzero()
    return [(int(x) + o["x"], int(y) + o["y"], int(z) + o["z"], names[m.ids[y, z, x]])
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())], o


class _FakeCtx:
    """A world of exactly what the test says it is - `test_frontier_scatter`'s own idiom."""

    def __init__(self, cells):
        self.cells = dict(cells)

    def name_at(self, x, y, z):
        return self.cells.get((x, y, z), "air")


def _ground(cells, dv=8, du=8, clear=0, land="midway", **kw):
    """**THE PALETTE TRAVELS WITH THE GROUND PROBE**, so a test has to hand it one too: the
    default is `frontier_scatter.FLORA`, which knows nothing about ferns or flowers."""
    kw.setdefault("flora", pg.flora_for(land))
    return pg._Green(_FakeCtx(cells), (0, 203, 0), dv, du, (0, 0), clear, **kw)


class _FakeLot:
    def __init__(self):
        self.cells = {}
        self.refused = 0

    def put(self, v, y, u, key, **props):
        self.cells[(int(v), int(y), int(u))] = (key, props)
        return True

    def has(self, v, y, u):
        return (int(v), int(y), int(u)) in self.cells


# --------------------------------------------------------------------------- the palette


def test_every_planting_material_is_legal_spendable_and_cheap():
    """Rule 16 - and dirt and grass being CURRENCY on this server is exactly why a park cannot be
    fixed with lawn. Every one of these has to be something you can actually spend."""
    for key, val in pg.GREEN.items():
        names = ([f for pair in val for f in pair] if key == "flowers"
                 else [val] if isinstance(val, str) else list(val))
        for name in names:
            assert blocks.exists(name), f"{key}={name} is not a block"
            assert blocks.spendable(name), f"{key}={name} is CURRENCY on this server"
            assert palette.tier(name) != "expensive", f"{key}={name} is expensive tier"


def test_every_land_palette_is_legal_spendable_and_cheap():
    for land, pal in pg.PALETTES.items():
        for key, val in pal.items():
            names = ([f for pair in val for f in pair] if key == "flowers" else [val])
            for name in names:
                assert blocks.exists(name), f"{land}.{key}={name} is not a block"
                assert blocks.spendable(name), f"{land}.{key}={name} is CURRENCY"
                assert palette.tier(name) != "expensive", f"{land}.{key}={name} is expensive"


def test_no_block_here_is_newer_than_the_server():
    """RULE 12, and it is named rather than inferred. `pink_petals` is the obvious flower for a
    bed, it is cheap, it exists in the client registry, it passes every other check in this
    pipeline - and it is a 1.20 block on a 1.19 server. This repo shipped exactly that once."""
    every = {v for k, v in pg.GREEN.items() if isinstance(v, str)}
    every |= {v for pal in pg.PALETTES.values() for v in pal.values() if isinstance(v, str)}
    every |= {f for pal in [pg.GREEN, *pg.PALETTES.values()]
              for pair in pal.get("flowers", []) for f in pair}
    for name in every - {"short_grass"}:          # the 26.x rename of 1.19's `grass`
        assert blocks.available(name), f"{name} is not on the 1.19 allowlist"
    assert "pink_petals" not in every
    assert "torchflower" not in every and "cherry_leaves" not in every


def test_a_bed_is_one_hue():
    """Three tones of one colour beat two tones and a third hue - the flamingo settled it, and a
    bed of eight species reads as a seed packet emptied on the ground."""
    for pal in [pg.GREEN, *pg.PALETTES.values()]:
        for pair in pal.get("flowers", []):
            assert len(pair) == 2, f"a flower family is a pair, got {pair}"


def test_an_unknown_palette_raises_rather_than_falling_back():
    """A silent fallback is how a land keeps the wrong species through a re-theme."""
    with pytest.raises(ValueError):
        pg.flora_for("gold_rush")
    assert pg.flora_for("midway")["trunk"] == "oak_log"
    assert pg.flora_for("prismworks")["trunk"] == "birch_log"


def test_each_land_gets_its_own_species():
    """The dressing is the one layer that could read the same everywhere, and it must not."""
    trunks = {name: pg.flora_for(name)["trunk"] for name in pg.PALETTES}
    assert len(set(trunks.values())) >= 3, trunks


# --------------------------------------------------------------------------- the ground probe


def test_a_column_over_paving_is_never_planted():
    """`Park Ways` owns every paved cell in the park. A shrub in a street is an obstruction."""
    g = _ground({(0, 202, 0): "smooth_stone"})
    assert not g.lawn(0, 0)


def test_a_column_with_something_standing_on_it_is_never_planted():
    g = _ground({(0, 202, 0): "moss_block", (0, 205, 0): "oak_planks"})
    assert not g.lawn(0, 0)


def test_the_plot_edge_is_sky_and_not_a_refusal():
    """**THE PARK'S OUTERMOST TWO COURSES ARE UNPLANTABLE FOR ANY LOT THAT STOPS AT THEM**, which
    is why the front threshold V0-5 measured as the third-largest hole in the park with a dressing
    pass nominally covering it. `_Ground.clearing` refuses a candidate whose whole `path_clear`
    neighbourhood is not lawn, and past the lot edge there is no lawn because there is no lot."""
    from mcbuild.gen import frontier_scatter as fs
    world = {(x, 202, z): "moss_block" for x in range(4) for z in range(4)}
    strict = fs._Ground(_FakeCtx(world), (0, 203, 0), 4, 4, (0, 0), 2)
    loose = _ground(world, dv=4, du=4, clear=2)  # noqa: E501
    assert not strict.clearing(0, 0), "the old probe should refuse at its own lot edge"
    assert loose.clearing(0, 0), "the plot edge is sky, and sky is not an obstruction"


def test_the_openness_gate_leaves_a_verge_alone():
    """A two-cell verge beside a kerb is DESIGNED lawn. The whole point of driving density from a
    measured distance is that it does not get planted."""
    cfg = _cfg("pf_park_green.yaml")["params"]
    assert cfg["open_min"] >= 3, "a verge narrower than the path clearance would be planted"
    assert cfg["open_full"] > cfg["open_min"], "the ramp has to ramp"


def test_a_hedge_shorter_than_its_minimum_places_nothing():
    """The deck soffit drew a coffer grid per cell and shipped 215 runs of which 184 were one or
    two cells - confetti in the loudest block available. A line that is too short to read as a
    line is not a shorter line, it is scatter, and the answer is to place nothing."""
    world = {(x, 202, 0): "moss_block" for x in range(3)}     # three cells of lawn, then nothing
    g = _ground(world, dv=3, du=1)
    lot = _FakeLot()
    assert pg._hedge(lot, g, 0, 0, 7, 4) == 0
    assert not lot.cells


def test_a_hedge_long_enough_is_one_unbroken_run():
    world = {(x, 202, z): "moss_block" for x in range(20) for z in range(20)}
    g = _ground(world, dv=20, du=20)
    lot = _FakeLot()
    n = pg._hedge(lot, g, 0, 0, 7, 4)
    assert n >= 4
    # the run picks its own axis; whichever it took, it has to be unbroken along it
    vs = sorted({v for v, _y, _u in lot.cells})
    us = sorted({u for _v, _y, u in lot.cells})
    along = vs if len(vs) > len(us) else us
    assert along == list(range(along[0], along[-1] + 1)), f"the run has a gap in it: {along}"


def test_the_height_cap_is_honoured():
    """The rim reserve is a VOID-VIEW reserve. A cap that only some pieces read is not a cap."""
    world = {(x, 202, z): "moss_block" for x in range(12) for z in range(12)}
    g = _ground(world, dv=12, du=12)
    for kind, fn in pg.KINDS.items():
        lot = _FakeLot()
        fn(lot, g, 5, 5, 3, 3)
        top = max([y for _v, y, _u in lot.cells], default=0)
        assert top < 3, f"{kind} reached course {top} under a cap of 3"


def test_the_rim_pass_plants_nothing_tall_and_nothing_paved():
    cfg = _cfg("pf_park_rim_green.yaml")["params"]
    assert cfg["max_height"] <= 3, "the reserve's whole job is the outward sightline"
    assert "tree" not in cfg["kinds"] and "hedge" not in cfg["kinds"]
    assert cfg["density"] < _cfg("pf_park_green.yaml")["params"]["density"]


# --------------------------------------------------------------------------- rule 15


def test_the_openness_field_treats_this_designs_own_planting_as_open_ground():
    """**THE ONE PLACE `_Ground.mine` CANNOT REACH.** Once the pass is shipped, `Park Complete`
    contains it, so every column it planted measures as built, the openness under each drift
    collapses and the next run plants almost nothing - which is `PF Frontier Scatter`'s recorded
    428-blocks-against-3,843 failure, arriving through the density instead of the ground probe."""
    if not os.path.exists(PARK):
        pytest.skip("the park is not shipped")
    anchor = [97500, 203, 80300]
    plain = pg.openness(PARK, anchor, 40, 40, (60, 240))
    faked = pg.openness(PARK, anchor, 40, 40, (60, 240),
                        mine=[(97500 + 60 + v, 203, 80300 + 240 + u)
                              for v in range(40) for u in range(40)])
    assert (faked >= plain).all(), "claiming a column as our own can only ever open it up"
    assert faked.max() > plain.max(), "a whole lot of our own cells should read as open ground"


# --------------------------------------------------------------------------- what shipped


@pytest.mark.skipif(not os.path.exists(GREEN), reason="PF Park Green is not shipped")
def test_nothing_shipped_stands_anywhere_but_on_the_parks_own_lawn():
    """The contract, checked against the artifact rather than against a log line: every cell of
    the pass stands over a column whose ground course in the world is moss."""
    park = schem.load(PARK)
    po = json.load(open(os.path.splitext(PARK)[0] + ".scan.json"))["origin"]
    names = [n.split(":")[-1] for n in park.names]
    bad = []
    for path in (GREEN, RIM):
        got = _shipped(path)
        if not got:
            continue
        cells, _o = got
        for x, _y, z, _n in cells:
            gx, gz = x - po["x"], z - po["z"]
            gy = 202 - po["y"]
            if not (0 <= gx < park.ids.shape[2] and 0 <= gz < park.ids.shape[1]):
                bad.append((x, z, "off the lattice"))
                continue
            under = names[park.ids[gy, gz, gx]]
            if under != "moss_block":
                bad.append((x, z, under))
    assert not bad, f"{len(bad)} planted columns are not over lawn, e.g. {bad[:5]}"


@pytest.mark.skipif(not os.path.exists(GREEN), reason="PF Park Green is not shipped")
def test_the_main_pass_keeps_out_of_the_frontier_above_its_threshold():
    """Five designs already dress that land. Two planting passes on one strip is the clash no
    single design can see: each honestly reports `overlap 0` against a capture that does not
    contain the other."""
    cells, _o = _shipped(GREEN)
    inside = [(x, z) for x, _y, z, _n in cells
              if 80300 <= z <= 80300 + 169 and x >= 97500 + 6]
    assert not inside, f"{len(inside)} cells inside the Frontier, e.g. {inside[:5]}"


@pytest.mark.skipif(not os.path.exists(RIM), reason="PF Park Rim Green is not shipped")
def test_the_rim_pass_stays_inside_the_reserve_and_under_three_courses():
    cells, _o = _shipped(RIM)
    assert cells
    for x, y, _z, name in cells:
        assert x - 97500 >= 187, f"{name} at V{x - 97500} is not in the reserve"
        assert y <= 205, f"{name} reaches Y{y}, over the reserve's three-course cap"


@pytest.mark.skipif(not os.path.exists(RIM), reason="PF Park Rim Green is not shipped")
def test_the_rim_pass_leaves_the_wyrm_gate_and_the_frontiers_own_rim_alone():
    """`PF Sauropod` stands at U8-70 and `PF Frontier Rim` lays the cliff walk and the nesting
    colony at U75-172; the Wyrm Gate's whole job is a silhouette read against empty sky."""
    cells, _o = _shipped(RIM)
    for x, _y, z, name in cells:
        u = z - 80300
        assert u > 174, f"{name} at U{u} is on the Frontier's own rim"
        assert not (360 <= u <= 425), f"{name} at U{u} is inside the Wyrm Gate's margin"


@pytest.mark.skipif(not os.path.exists(GREEN), reason="PF Park Green is not shipped")
def test_the_two_passes_never_share_a_cell():
    """They are one generator run twice over disjoint bands, and disjoint is a claim to check."""
    a, _ = _shipped(GREEN)
    b, _ = _shipped(RIM)
    A = {(x, y, z) for x, y, z, _n in a}
    B = {(x, y, z) for x, y, z, _n in b}
    assert not (A & B), f"{len(A & B)} shared cells"


@pytest.mark.skipif(not os.path.exists(GREEN), reason="PF Park Green is not shipped")
def test_the_cleanup_actually_cleans_up():
    """**THE ONLY NUMBER THAT SAYS WHETHER ANY OF THIS WORKED**, measured the way the island's own
    standard is stated: dead ground is a bare column four or more blocks from anything built or
    planted.

    **THE BEFORE STATE IS DERIVED, NOT REMEMBERED.** Once these passes are shipped the park
    CONTAINS them, so a "before" read off `Park Complete` is the after, and an assertion that the
    numbers improved fails the moment the improvement lands - which is the snapshot trap this repo
    has recorded five times. `masks(without=...)` takes the two designs' own cells back out.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "park_empty", os.path.join(ROOT, "tools", "park_empty.py"))
    pe = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        spec.loader.exec_module(pe)
        bare0, built0 = pe.masks(without=[GREEN, RIM])
        before = int((bare0 & (pe.openness(built0) > 4)).sum())
        # ...and the AFTER is composited the same way whether or not it has been shipped, so
        # this test says the same thing on both sides of a `park_place --ship`.
        bare, built = pe.masks([GREEN, RIM], without=[GREEN, RIM])
        after = int((bare & (pe.openness(built) > 4)).sum())
    finally:
        os.chdir(cwd)
    assert before > 5000, f"the park used to have thousands of dead columns, measured {before}"
    assert after < before * 0.35, f"dead ground {before} -> {after}: the pass is not earning its place"
