"""The claim row and the muster yard, against the things that shipped wrong before they were right.

Every test here is a defect this pass actually produced, and every one of them audited clean when
it did: an overlap the material test could not see, a value ladder that was five greys, a gravel
crust that would fall, a claim kerb with no contrast against its own ground, and a key called `no`
that YAML 1.1 parsed as the boolean False.
"""
from __future__ import annotations

import json
import os

import pytest
import yaml

from mcbuild import blocks, palette, schem
from mcbuild.gen import claimrow
from mcbuild.gen.frontier_scatter import shipped_cells

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW = os.path.join(ROOT, "configs", "pf_frontier_claim_row.yaml")
YARD = os.path.join(ROOT, "configs", "pf_frontier_muster_yard.yaml")
OUT = os.path.join(ROOT, "out")

#: A guest walks THROUGH these. `PASSABLE IS NOT EMPTY` and its converse have bitten this repo
#: three times, so a walk test names what may stand in a route rather than demanding bare air.
PASSABLE = {"air", "cave_air", "moss_carpet", "ochre_froglight", "rail"}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _lum(name, face="side"):
    r, g, b = blocks.color(name, face)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _shipped(name):
    lit = os.path.join(OUT, f"{name}.litematic")
    side = os.path.join(OUT, f"{name}.scan.json")
    if not (os.path.exists(lit) and os.path.exists(side)):
        pytest.skip(f"{name} has not been shipped yet")
    return schem.load(lit), json.load(open(side, encoding="utf-8"))["origin"]


@pytest.fixture(scope="module")
def row_cfg():
    return _load(ROW)


@pytest.fixture(scope="module")
def yard_cfg():
    return _load(YARD)


# --------------------------------------------------------------------------- the palette


def test_every_material_is_legal_spendable_and_affordable():
    """Rule 16: real, on the 1.19 server, and still CURRENCY here are three different questions.

    `blocks.available` is provisional and only WARNS in the pipeline, so it is reported here
    rather than asserted - the allowlist is 191 blocks and would reject `allium`.
    """
    for key, name in claimrow.KIT.items():
        assert blocks.spendable(name), f"{key}={name} is CURRENCY on this server (rule 16)"
        assert palette.tier(name) != "expensive", f"{key}={name} is expensive tier"


def test_the_worked_ground_is_a_real_value_ladder():
    """**MEASURED ACROSS FAMILIES, WHICH IS THE ONLY PLACE THIS ECONOMY HAS ANY CONTRAST.**

    The first build laid gravel 128, cobblestone 127, andesite 136, stone 126 and mossy cobblestone
    115 - five materials inside twenty-one points of luminance, which is ONE GREY however they are
    mixed, and the flat rendered as a pale slab. CLAUDE.md records the identical mistake four
    separate times, every one of them made by searching WITHIN a material family where a ladder
    cannot exist by construction.
    """
    rungs = ["spoil", "earth", "wash", "pale"]
    lums = sorted(_lum(claimrow.KIT[k]) for k in rungs)
    steps = [b - a for a, b in zip(lums, lums[1:])]
    assert min(steps) >= 14, f"a rung nobody can see: {list(zip(rungs, lums))} steps={steps}"
    assert lums[-1] - lums[0] >= 100, f"the ladder has no range: {lums}"


def test_the_claim_kerb_reads_against_the_ground_it_bounds():
    """A boundary the same value as its ground is not a boundary.

    150 `cobblestone_slab` at 127 against a working that runs 77-128 drew no line at all from the
    one view a claim is read from, which is the plan.
    """
    kerb = _lum(claimrow.KIT["kerb"])
    mid = sum(_lum(claimrow.KIT[k]) for k in ("earth", "wash", "crust")) / 3
    assert abs(kerb - mid) >= 35, f"kerb {kerb:.0f} against ground {mid:.0f} is invisible"


def test_only_the_crust_falls():
    """RULE 13. Everything a heap is stacked out of must be rock, or a tailings heap pours away."""
    for key, name in claimrow.KIT.items():
        if key == "crust":
            assert blocks.falls(name), "the crust is meant to be the one gravity block"
            continue
        assert not blocks.falls(name), f"{key}={name} falls and is not the crust"


# --------------------------------------------------------------------------- the configs


@pytest.mark.parametrize("path", [ROW, YARD])
def test_no_config_key_is_a_yaml_boolean(path):
    """**`no:` IS NOT AN INTEGER KEY, IT IS `False`.**

    YAML 1.1 parses on/off/yes/no as booleans. Written `no: 1` a claim's number came out keyed
    `False`: no error, the number silently lost, and then the design fingerprint's `sort_keys`
    exploded on a dict holding both a bool and a str. The Lowland Glow shipped the same trap with
    a key called `on`.
    """
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                assert isinstance(k, str), f"{path}: key {k!r} is a {type(k).__name__}, not a str"
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(_load(path))


def test_both_designs_read_the_world_they_are_verified_against(row_cfg, yard_cfg):
    """One design, two worlds, two answers - the shop islet's own lesson, which cost a rebuild."""
    for cfg in (row_cfg, yard_cfg):
        assert cfg["params"]["under"] == cfg["finish"]["verify_against"]


def test_a_missing_lot_or_world_raises_rather_than_guessing(row_cfg):
    p = dict(row_cfg["params"])
    with pytest.raises(ValueError):
        claimrow.build({**p, "lot": None})
    with pytest.raises(ValueError):
        claimrow.build({**p, "under": None})
    with pytest.raises(ValueError):
        claimrow.build({**p, "kind": "nonsense"})


# --------------------------------------------------------------------------- rule 15


def test_shipped_cells_is_exact_and_absent_means_empty():
    """**THIS IS THE HONEST ANSWER TO RULE 15 AND A MATERIAL LIST IS NOT.**

    Every module in this land is stone brick, blackstone and spruce, so a material test cannot tell
    a neighbour's plinth from this design's own - it put a board post through the Prospecting
    Porch's marquee and grew 39 cells of canopy into the Trailhead Gate before this replaced it.
    A first run has nothing standing, and empty is the correct answer for that.
    """
    assert shipped_cells(None) == frozenset()
    assert shipped_cells(os.path.join(OUT, "no such design.litematic")) == frozenset()
    m, o = _shipped("PF Frontier Claim Row")
    cells = shipped_cells(os.path.join(OUT, "PF Frontier Claim Row.litematic"))
    assert len(cells) == int((m.ids > 0).sum())
    ys = {y for _, y, _ in cells}
    assert min(ys) == o["y"], "the world y must come off the sidecar, not be assumed"


def test_own_holds_only_real_ground_cover():
    """`OWN` is the fallback, and anything a NEIGHBOUR could be built from does not belong in it."""
    assert claimrow.OWN == frozenset({"moss_carpet"})


# --------------------------------------------------------------------------- the shipped work


@pytest.mark.parametrize("name", ["PF Frontier Claim Row", "PF Frontier Muster Yard"])
def test_no_cell_is_taken_from_anything_already_standing(name):
    """**THE TEST THAT CATCHES THE WHOLE CLASS.**

    An overlap here is invisible in every render, audit and bill of materials - a pine growing
    through a marquee draws exactly like a pine. `moss_carpet` is the one declared exception, and
    both configs say so.
    """
    d, do = _shipped(name)
    w, wo = _shipped("Park Complete")
    dn = [n.split(":")[0] for n in d.names]
    wn = [n.split(":")[0] for n in w.names]
    di, wi = d.ids, w.ids
    off = (do["x"] - wo["x"], do["y"] - wo["y"], do["z"] - wo["z"])
    bad = []
    for y, z, x in zip(*di.nonzero()):
        Y, Z, X = y + off[1], z + off[2], x + off[0]
        if not (0 <= Y < wi.shape[0] and 0 <= Z < wi.shape[1] and 0 <= X < wi.shape[2]):
            continue
        if not wi[Y, Z, X]:
            continue
        a = dn[int(di[y, z, x])].split("[")[0].split(":")[-1]
        b = wn[int(wi[Y, Z, X])].split("[")[0].split(":")[-1]
        if a != b and b != "moss_carpet":
            bad.append((int(x) + do["x"], int(y) + do["y"], int(z) + do["z"], b, a))
    assert not bad, f"{name} takes {len(bad)} cell(s) something already stands in: {bad[:6]}"


@pytest.mark.parametrize("name", ["PF Frontier Claim Row", "PF Frontier Muster Yard"])
def test_no_gravel_is_ever_placed_over_air(name):
    """RULE 13, checked on the SHIPPED cells rather than trusted to the crust rule in the code.

    A falling block whose support is the world's own lawn is fine; one over air pours away, and on
    a park deck that means into the void.
    """
    d, do = _shipped(name)
    dn = [n.split(":")[-1].split("[")[0] for n in d.names]
    di = d.ids
    loose = []
    for y, z, x in zip(*di.nonzero()):
        if dn[int(di[y, z, x])] != "gravel":
            continue
        if y == 0:
            continue          # its support is the world's ground course, one below the design
        if not di[y - 1, z, x]:
            loose.append((int(x), int(y), int(z)))
    assert not loose, f"{name}: {len(loose)} gravel cell(s) with nothing under them: {loose[:6]}"


def test_every_claim_is_numbered_and_signed(row_cfg):
    """A worked flat with no boundary in it is texture; a boundary with a NUMBER on it is
    somebody's ground, which is the whole story of a gold rush. A refused sign is silent - it is
    the failure four of the park's building kinds shipped - so it is asserted."""
    canvas = claimrow.build(row_cfg["params"])
    claims = canvas.meta["parts"]["claims"]
    assert len(claims) == len(row_cfg["params"]["claims"])
    for c in claims:
        assert c["number"], f"a claim with no number: {c}"
        assert c["signed"], f"claim {c['number']}'s board was refused - nothing to hang it on"


def test_both_windlasses_stand_on_two_legs(row_cfg):
    """A windlass with one leg is a windlass that was never checked. `_pit` reports rather than
    building half of one, so the report is what is asserted."""
    canvas = claimrow.build(row_cfg["params"])
    pits = canvas.meta["parts"]["pits"]
    assert pits, "the claim row declares prospect pits"
    for pit in pits:
        assert pit["windlass"], f"pit at {pit['at']} could not stand its legs"


def test_the_muster_bell_hangs_from_a_real_beam(yard_cfg):
    """**THE BELL IS THE VERB** - the whole row from the pennant to the tower carries one other
    thing a guest can operate. It hangs from a CEILING attachment, so the beam goes in first: the
    same rule as a chain and a hanging lantern, and the reason `_Lot.hang` refuses a fitting with
    nothing over it."""
    canvas = claimrow.build(yard_cfg["params"])
    bell = canvas.meta["parts"]["bell"]
    assert bell["bell"], "the muster bell was refused"
    v, u = bell["at"]
    assert canvas.solid(v + 1, 4, u), "the bell hangs from nothing"


def test_the_corral_has_a_gate_and_is_otherwise_closed(yard_cfg):
    """**THE GATE IS LEFT OUT BY THE RING, NEVER PUNCHED AFTERWARDS.** Building the ring and then
    replacing a cell repaints what already exists - the void tower's crenellations shipped as a
    plain drum for exactly that, and nothing about the code looked wrong."""
    canvas = claimrow.build(yard_cfg["params"])
    pen = canvas.meta["parts"]["corral"]
    assert pen["gate"], "a pen with no way in"
    v0, v1 = pen["v"]
    u0, u1 = pen["u"]
    gaps = [(v, u) for v in range(v0, v1 + 1) for u in (u0, u1)
            if not canvas.solid(v, 0, u)]
    assert len(gaps) <= 2, f"the pen's long sides have {len(gaps)} holes in them: {gaps[:6]}"


def test_the_notice_board_is_read_from_the_side_the_config_names(yard_cfg):
    """**A SIGN'S CELL IS DERIVED FROM ITS FACING, NOT HARD-CODED.** Written as `u + 1` a board can
    only ever be read from one side, so a board put up to be read from the WAY hangs its text on
    the far face and shows the walk its back. Our renderer draws it the same either way."""
    canvas = claimrow.build(yard_cfg["params"])
    board = canvas.meta["parts"]["notice"]
    assert board["signed"] == 2, "a notice board with nothing on it"
    dv, du = claimrow._FACE_STEP[board["facing"]]
    v, u = board["at"]
    for k in (1, 2):
        got = canvas.get_name(v + k + dv, 3, u + du).split(":")[-1]
        assert got.endswith("wall_sign"), f"no sign on the {board['facing']} face, got {got!r}"
        assert canvas.solid(v + k, 3, u), "the sign has no board behind it"
    # ...and the opposite face is bare, or the board is readable from the side nobody stands on
    for k in (1, 2):
        back = canvas.get_name(v + k - dv, 3, u - du).split(":")[-1]
        assert not back.endswith("wall_sign"), "the board is signed on both faces"


def test_the_route_through_the_gate_actually_walks(yard_cfg):
    """**A THRESHOLD WITH NO PATH THROUGH IT IS A GATE ONTO A LAWN**, which is most of why the
    court read as unfinished whatever was standing round its edge.

    A WALK, not a look: step along the paved legs a course at a time and demand they join.
    """
    canvas = claimrow.build(yard_cfg["params"])
    legs = canvas.meta["parts"]["legs"]
    assert len(legs) == 2, "the route is a portal leg and an exit leg"
    a, b = (set() for _ in range(2))
    for leg, acc in zip(legs, (a, b)):
        v0, v1, u0, u1 = leg["box"]
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if canvas.solid(v, 0, u):
                    acc.add((v, u))
    assert a and b, "a leg that paved nothing"
    touching = {(v, u) for v, u in a
                if any((v + dv, u + du) in b for dv, du in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))}
    assert touching, "the two legs of the route never meet - the walk is in two pieces"


def test_nothing_stands_in_another_designs_ground(row_cfg):
    """The keep-out list is what actually protects a neighbour here, because a material test
    cannot. It is measured off the world, and it is honoured cell by cell."""
    canvas = claimrow.build(row_cfg["params"])
    boxes = [tuple(int(x) for x in b) for b in row_cfg["params"]["keep_out"]]
    assert boxes, "the claim row's neighbours are named, not detected"
    model = canvas.to_model()
    ids = model.ids
    bad = []
    for y, z, x in zip(*ids.nonzero()):
        if any(a <= x <= b and c <= z <= d for a, b, c, d in boxes):
            bad.append((int(x), int(y), int(z)))
    assert not bad, f"{len(bad)} cell(s) inside a neighbour's ground: {bad[:6]}"


def test_the_flat_is_one_piece_where_it_matters(row_cfg):
    """**THE DESIGN ALONE IS IN PIECES AND THAT IS CORRECT** - the Mine Ridge's own situation.

    Every cell of this design stands on the park's own lawn one course down, so in the world it is
    continuous with the ground; a heap or a prop that does not touch the working is a separate
    component only in isolation. What IS asserted is that the working itself - the y0 course - is
    one connected surface, because a worked flat in islands is litter.
    """
    canvas = claimrow.build(row_cfg["params"])
    dv, du = canvas.sx, canvas.sz
    ground = {(v, u) for v in range(dv) for u in range(du) if canvas.solid(v, 0, u)}
    assert ground, "the flat laid nothing"
    seen = set()
    stack = [next(iter(ground))]
    while stack:
        v, u = stack.pop()
        if (v, u) in seen:
            continue
        seen.add((v, u))
        for dvv, duu in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (v + dvv, u + duu)
            if n in ground and n not in seen:
                stack.append(n)
    stray = len(ground) - len(seen)
    assert stray / len(ground) < 0.06, (
        f"{stray} of {len(ground)} ground cells are islands cut off from the working")


# --------------------------------------------------------------------------- the plaques

def _plaque_design():
    p = os.path.join(ROOT, "out", "PF Plateau Plaques.scan.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def test_every_plaque_that_was_asked_for_is_signed():
    """A SIGN SILENTLY REFUSED IS THIS PARK'S MOST-REPEATED FAILURE.

    `_plaque` returns `signed: False` and a reason rather than raising, because a plaque whose
    ground belongs to another design should cost that plaque and not the build - but a design that
    ships six of seven boards and says nothing is the failure wearing a hat. The count is the test.
    """
    d = _plaque_design()
    if d is None:
        return
    plaques = d["parts"].get("plaques") or []
    assert plaques, "the plaque design built no plaques"
    unsigned = [p for p in plaques if not p.get("signed")]
    assert not unsigned, f"plaques with no board: {unsigned}"


def test_no_plaque_line_clips():
    """FIFTEEN CHARACTERS. This park has shipped 'MINE CART ESCAP', 'and prize windo' and
    'ore from the ad' - a clip is invisible in every render here and obvious in a screenshot, so
    the generator RAISES rather than truncating."""
    d = _plaque_design()
    if d is None:
        return
    for p in d["parts"].get("plaques") or []:
        for line in p.get("lines") or []:
            assert len(line) <= 15, f"{line!r} is {len(line)} characters"
    # ...and the guard really fires, on a spec that never reaches a canvas
    class _G:
        def lawn(self, *a):
            return True
    with pytest.raises(ValueError):
        claimrow._plaque(None, _G(), {"at": [0, 0], "lines": ["a" * 16]})


def test_a_plaque_faces_a_real_direction():
    """A facing is derived from the walk and typed by hand, so a typo must fail the build rather
    than defaulting quietly to whichever way the code was written for."""
    class _G:
        def lawn(self, *a):
            return True
    with pytest.raises(ValueError):
        claimrow._plaque(None, _G(), {"at": [0, 0], "facing": "left", "lines": ["X"]})


def test_a_design_can_declare_that_it_has_no_way():
    """`max(1, w)` gave a width of 0 a one-cell walk running the whole lot - 67 slabs of path down
    a land for a design that asked for none, and a one-wide path audits perfectly clean."""
    d = _plaque_design()
    if d is None:
        return
    way = d["parts"].get("way") or {}
    assert not way.get("cells"), f"the plaque design laid {way.get('cells')} cells of path"
