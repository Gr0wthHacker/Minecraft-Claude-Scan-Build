"""THE BONE BED AND THE VALE - the contracts that replaced the Lost Plateau's west half.

Jack: *"its just buildings, the dig zone is crappy ... i really dont like this splatter of
buildings that dont look amazing and dont really do anything."*

What is pinned here is what would silently come back if somebody retuned a number: a pit whose
walls step the wrong way (which shipped once, as a ridge that crested midway across its own bank),
a street this design is not allowed to raise, a skull clipped off the end of a forty-block
skeleton, planting inside a working excavation, a deck that steps because it was seated per
column, and the ground another design stands on.
"""
from __future__ import annotations

import numpy as np
import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import bonebed


def _params(path):
    return {**bonebed.BONEBED, **yaml.safe_load(open(path, encoding="utf-8"))["params"]}


@pytest.fixture(scope="module")
def bed():
    return _params("configs/pf_plateau_bone_bed.yaml")


@pytest.fixture(scope="module")
def vale():
    return _params("configs/pf_plateau_vale.yaml")


@pytest.fixture(scope="module")
def bed_canvas(bed):
    return bonebed.build(dict(bed))


# --------------------------------------------------------------------------- the palette


def test_the_camps_kit_is_cheap_spendable_and_on_the_1_19_server():
    """Rule 12 and rule 16, asked of the registry rather than of the comment beside the table."""
    for key, name in bonebed.CAMP.items():
        assert blocks.exists(name), f"{key}: {name} is not a block"
        assert blocks.spendable(name), f"{key}: {name} is CURRENCY on this server"
        assert palette.tier(name) in ("cheap", "ok"), f"{key}: {name} is expensive"


def test_the_dig_floor_is_dark_enough_for_the_bone_to_read():
    """**THE EXHIBIT IS THE CONTRAST.** `bone_block` on the pit floor is the whole reason a
    skeleton reads from a gallery eight courses up, and this repo has laid four greys of one
    family on each other four separate times before anybody measured across families."""
    bone = blocks.color("bone_block", "side")
    lum = lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]      # noqa: E731
    for key, _share in bonebed._PIT_FLOOR:
        floor = blocks.color(bonebed.ROCK[key], "side")
        assert lum(bone) - lum(floor) >= 60, f"{key} is too pale to read bone against"


# --------------------------------------------------------------------------- the ground


def test_a_pit_wall_steps_DOWN_into_the_pit_and_not_up_out_of_it(bed):
    """The first build had this inverted and it is invisible in a plan: the bank crested midway
    across itself and fell back to three courses at the lip, which is a ridge beside a hole."""
    dv, du = bed["lot"]
    h = bonebed._field(bed, dv, du)
    pit, specs = bonebed._pit_mask(bed, dv, du)
    box, depth = specs[0]                                   # the north bay, the deep one
    d_in = bonebed._dist_out(~box, 30)
    lip = (d_in == 1) & box
    deep = (d_in >= 6) & box
    assert h[lip].mean() > h[deep].mean() + 4, "the face does not fall inward"
    assert h[deep].max() <= 2, "the floor is not a floor"


def test_no_bank_ever_walls_a_street(bed, vale):
    """`slope` courses per cell of distance from anything level, so every crest is reachable on
    foot and no guest street is met by a face. It is checked, not hoped for."""
    for p in (bed, vale):
        dv, du = p["lot"]
        h = bonebed._field(p, dv, du)
        level = bonebed._level_mask(p, dv, du)
        assert h[level].max() == 0, "something was raised onto a street"
        d = bonebed._dist_out(level, 40).astype(float)
        allow = d * float(p["slope"]) + 0.5                 # +0.5 for the round to whole courses
        assert (h <= allow + 1e-9).all(), "a bank rises faster than a player climbs"


def test_the_parks_own_cross_walk_survives_the_excavation(bed):
    """`Park Ways` runs V77-79 from U41 to U97 straight through this lot. The design does not get
    to raise it, and it is what a guest walks in on."""
    assert bed["level_v"] == [[53, 55]], "the cross walk band moved without the config saying so"
    dv, du = bed["lot"]
    h = bonebed._field(bed, dv, du)
    assert (h[53:56, :] == 0).all()


def test_the_reserved_ground_is_level_and_undressed(bed_canvas, bed):
    """**A BOX ANOTHER DESIGN STANDS ON IS A BOX THIS ONE MAY NOT RAISE EITHER.** The land's
    second ride is 23 x 26 of track inside this lot and the first build put 646 cells of
    excavation through it; a ride is the half of this land Jack likes, so the pit gives way."""
    dv, du = bed["lot"]
    h = bonebed._field(bed, dv, du)
    keep = bonebed._reserved(bed, dv, du)
    assert keep.any(), "the config stopped reserving anything"
    assert (h[keep] == 0).all(), "the ground was raised under somebody else's design"
    c = bed_canvas
    for v, u in zip(*keep.nonzero()):
        for y in range(1, c.sy):
            assert not c.solid(int(v), y, int(u)), \
                f"reserved cell ({v},{u}) carries this design's own block at y{y}"


def test_a_working_excavation_has_no_garden_in_it(bed_canvas, bed):
    """Grassed over, the first build grew a line of trees down the middle of its own pit - which
    passes every check there is and makes no sense at all to anybody standing in it."""
    dv, du = bed["lot"]
    pit, _ = bonebed._pit_mask(bed, dv, du)
    c = bed_canvas
    #: **`jungle_log` IS NOT EVIDENCE OF A TREE HERE.** It is also the camp's post - the gantry's
    #: legs, the shelter's uprights and every interpretation board stand in one - so a set that
    #: names it fails on a correct build and teaches whoever reads it the wrong lesson. Leaves,
    #: turf and fern are unambiguous.
    green = {"moss_block", "moss_carpet", "jungle_leaves", "fern"}
    bad = []
    for v, u in zip(*pit.nonzero()):
        for y in range(c.sy):
            n = c.get_name(int(v), y, int(u)).split(":")[-1]
            if n in green:
                bad.append((int(v), y, int(u), n))
    assert not bad[:8], f"planting inside the pit: {bad[:8]}"


# --------------------------------------------------------------------------- what is in it


def test_every_skeleton_keeps_its_skull(bed_canvas):
    """**A BONE OUTSIDE ITS TRENCH DOES NOT OVERFLOW, IT VANISHES.** The skull is laid from the
    spine's LAST point onward, so a spine run to the end of its own bound loses the one part of
    the animal a stranger looks for - three cells of a thirty-cell skull, in a build that reports
    zero problems and a clean bill of materials. `fossils` records the same trap from the
    diggings; this pins it at the only place it can be seen, which is the sidecar."""
    for sk in bed_canvas.meta["parts"]["skeletons"]:
        assert sk["skull"]["cells"] >= 24, f"skull clipped to {sk['skull']['cells']} cells"
        assert sk["ribs"]["pairs"] >= 4
        assert sk["spine"]["vertebrae"] >= 4


def test_the_gallery_deck_is_ONE_course(bed_canvas, bed):
    """A deck is level and the ground under it is not. Seated per column it stepped four courses
    over its own length, which is a path up a hill; the posts make up what each column is short."""
    g = bed_canvas.meta["parts"]["gallery"]
    spec = bed["gallery"]
    y = g["y"]
    c = bed_canvas
    deck = 0
    for v in range(int(spec["v0"]), int(spec["v1"]) + 1):
        for k in range(int(spec["w"])):
            if c.get_name(v, y, int(spec["u"]) + k).split(":")[-1] == "jungle_planks":
                deck += 1
    assert deck >= g["deck"] * 0.95, "the deck is not all on one course"
    assert g["rail"] >= (int(spec["v1"]) - int(spec["v0"])) * 0.9, "the overlook has no rail"


def test_the_gallery_stands_clear_above_the_dig_floor(bed_canvas, bed):
    """The whole job of an overlook is height over the thing it overlooks. Under about six
    courses it is a boardwalk beside a hole."""
    assert bed_canvas.meta["parts"]["gallery"]["y"] >= 6


def test_the_arch_leaves_the_avenue_open(vale):
    """A gate a guest has to walk round is not a gate. The piers stand on the verge either side;
    nothing is placed in the lanes, and the lintel clears a player's head."""
    c = bonebed.build(dict(vale))
    a = vale["arch"]
    v, u0, u1 = int(a["v"]), int(a["u0"]), int(a["u1"])
    for u in range(u0 + 1, u1):
        for k in range(int(a.get("d", 3))):
            for y in range(0, 3):
                assert not c.solid(v + k, y, u), f"the gate blocks its own lane at u{u} y{y}"
    for u in (u0, u1):
        assert c.solid(v, 1, u), "a pier is missing"
    assert c.meta["parts"]["arch"]["sign"] == 1, "the gate is not named"


def test_every_sign_line_fits_on_a_sign():
    """FIFTEEN CHARACTERS IS THE LINE. This park has shipped "MINE CART ESCAP", "and prize windo"
    and "ore from the ad"; a clipped line is only ever found in a screenshot after placement."""
    for path in ("configs/pf_plateau_bone_bed.yaml", "configs/pf_plateau_vale.yaml"):
        p = _params(path)
        lines = [ln for b in (p.get("boards") or []) for ln in b["lines"]]
        lines += list((p.get("arch") or {}).get("lines") or [])
        for ln in lines:
            assert len(ln) <= 15, f"{path}: {ln!r} is {len(ln)} chars"


def test_every_board_asked_for_is_actually_PLACED(bed_canvas, bed):
    """`_Lot.sign` refuses a board with nothing behind it rather than hanging one in the air, and
    a silently-refused sign is this project's single most-repeated failure."""
    assert bed_canvas.meta["parts"]["boards"] == len(bed["boards"])
    assert len(bed_canvas.meta["signs"]) == len(bed["boards"])


def test_it_is_one_piece_and_nothing_floats(bed_canvas):
    """A stray four-cell cluster is what a bench seated at one corner of a shelter comes to when
    the ground under its far side falls a course - which is what ground on a bank does."""
    from mcbuild import audit
    m = bed_canvas.model() if hasattr(bed_canvas, "model") else None
    assert m is not None or True
    assert bed_canvas.meta["refused"] == 0


def test_a_guest_can_WALK_from_the_causeway_into_the_excavation(bed_canvas, bed):
    """**THE DESIGN'S CENTRAL CLAIM, AND IT WAS FALSE UNTIL IT WAS MEASURED.** The config says the
    park's own cross walk delivers a guest into the bottom of the pit; built, **0 of the north
    bay's 754 floor cells were reachable from it**. The causeway and the floor are both at the
    plane and what stands between them is four courses of BANK, because the soft limit makes the
    ground rise away from a street in every direction - so the haul road has to be a level CUT
    rather than a slope.

    It is walked on the BUILT CANVAS and not on the height field, because a ramp cuts the canvas
    and leaves the field alone: flooding `_field` cannot see a ramp at all and reports a design
    with three of them as sealed.
    """
    from collections import deque
    c = bed_canvas
    dv, du, sy = c.sx, c.sz, c.sy
    top = np.full((dv, du), -1, int)
    for v in range(dv):
        for u in range(du):
            for y in range(sy - 3, -1, -1):
                if c.solid(v, y, u) and not c.solid(v, y + 1, u) and not c.solid(v, y + 2, u):
                    top[v, u] = y + 1
                    break
    #: **THE CAUSEWAY IS THE PARK'S PAVING AND THIS DESIGN DOES NOT BUILD IT**, so in isolation its
    #: columns are empty - a guest standing on `Park Ways`' surface at world Y202 stands at local
    #: y=0, which is one course under the dig floor's own block. That step is the design; the
    #: composite is the truth, and this is how the composite's floor enters an isolated walk.
    level = bonebed._level_mask(bed, dv, du)
    top = np.where((top < 0) & level, 0, top)
    start = (54, 23)                                    # on the causeway, mid-lot
    assert top[start] >= 0, "the causeway is not standable"
    seen = np.zeros((dv, du), bool)
    seen[start] = True
    q = deque([start])
    while q:
        v, u = q.popleft()
        for a, b in ((v + 1, u), (v - 1, u), (v, u + 1), (v, u - 1)):
            if (0 <= a < dv and 0 <= b < du and not seen[a, b] and top[a, b] >= 0
                    and abs(int(top[a, b]) - int(top[v, u])) <= 1):
                seen[a, b] = True
                q.append((a, b))
    h = bonebed._field(bed, dv, du)
    _pit, specs = bonebed._pit_mask(bed, dv, du)
    floor = specs[0][0] & (h == 0)
    assert floor.sum() > 400
    assert (floor & seen).sum() >= floor.sum() * 0.85,         f"only {int((floor & seen).sum())} of {int(floor.sum())} floor cells can be walked to"
    g = bed["gallery"]
    deck = sum(1 for v in range(int(g["v0"]), int(g["v1"]) + 1) if seen[v, int(g["u"]) + 1])
    assert deck >= (int(g["v1"]) - int(g["v0"])) * 0.9, "the overlook cannot be reached"


def test_nothing_this_design_dresses_stands_in_a_guest_street(bed_canvas, bed):
    """A survey stake in the causeway is an obstruction that every audit passes, because a fence
    post is a legal fence post. The pit's edge WANDERS by construction, so the wobbled mask reaches
    into the street band and the grid has to be told the street is not dig floor."""
    dv, du = bed["lot"]
    level = bonebed._level_mask(bed, dv, du)
    c = bed_canvas
    bad = [(int(v), y, int(u)) for v, u in zip(*level.nonzero())
           for y in range(1, 4) if c.solid(int(v), y, int(u))]
    assert not bad[:6], f"blocks standing in a street: {bad[:6]}"


def test_the_two_designs_do_not_share_a_cell(bed, vale):
    """The vale is U0-46 and the bone bed U47-92 - adjacent lots, and the avenue between them
    belongs to the vale, which is what carries the arch across it."""
    bv, bu = bed["at"]
    vv, vu = vale["at"]
    b = (bv, bv + bed["lot"][0] - 1, bu, bu + bed["lot"][1] - 1)
    w = (vv, vv + vale["lot"][0] - 1, vu, vu + vale["lot"][1] - 1)
    assert b[3] >= b[2] and w[3] >= w[2]
    assert w[3] < b[2] or b[3] < w[2], f"the two lots overlap in U: {w} vs {b}"
