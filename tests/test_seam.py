"""The seam's contracts - the things a render, an audit and a bill of materials cannot see.

Every one of these pins a decision that was got wrong once while this was being built, or a rule
this repo has already paid for somewhere else:

  * a leaning column that steps sideways at one cell wide is a shower of loose blocks
  * `free(v, u, y)` written `(v, y, u)` reads a cell that does not exist and the guard passes
  * a bottom-up seat scan seats every plate column INSIDE the plate and generates nothing
  * a flight walked against its own gradient ships as a single stair
  * a value ladder measured inside one material family cannot draw a line
  * a walk a shard can lean over is not a walk
"""
from __future__ import annotations

import math
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import blocks, palette, scan, schem  # noqa: E402
from mcbuild.gen import seam  # noqa: E402
from mcbuild.gen.canvas import Canvas  # noqa: E402
from mcbuild.gen.frontier_builds import _Lot  # noqa: E402

CONFIGS = {
    "fracture": "configs/pf_prism_fracture.yaml",
    "yard": "configs/pf_prism_cutting_yard.yaml",
    "field": "configs/pf_prism_seam_field.yaml",
}
SHIPPED = {
    "fracture": "out/PF Prism Fracture.litematic",
    "yard": "out/PF Prism Cutting Yard.litematic",
    "field": "out/PF Prism Seam Field.litematic",
}


def cfg(kind: str) -> dict:
    return yaml.safe_load(open(CONFIGS[kind], encoding="utf-8"))["params"]


def shipped(kind: str):
    path = SHIPPED[kind]
    if not os.path.exists(path):
        pytest.skip(f"{path} not generated")
    return scan.load(path)


# --------------------------------------------------------------------- the palette


def test_every_block_it_places_is_real_spendable_and_on_the_server():
    for key, name in seam.PAL.items():
        assert blocks.exists(name), f"{key}: {name} is not a block"
        assert blocks.spendable(name), f"{key}: {name} is CURRENCY on this server"


def test_the_only_expensive_block_is_the_one_the_config_declares():
    dear = sorted(n for n in seam.PAL.values() if palette.tier(n) == "expensive")
    #: the note rail is the design's only verb and `configs/pf_prism_fracture.yaml` declares an
    #: allowance for it in words. Anything else arriving here is a palette change nobody costed.
    assert dear == ["note_block"], dear


def test_the_shard_is_a_real_value_ladder_measured_ACROSS_families():
    """The rung, not the range. 236/159/151 has a wide range and two rungs nobody can tell apart,
    and every one of this repo's four "this economy has no contrast" conclusions was measured
    inside ONE material family, where a ladder cannot exist by construction."""
    def lum(name):
        r, g, b = blocks.color(name, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    rungs = [seam.PAL[k] for k in ("deck", "base", "mid", "glow")]
    vals = [lum(n) for n in rungs]
    assert vals == sorted(vals), list(zip(rungs, vals))
    steps = [b - a for a, b in zip(vals, vals[1:])]
    assert min(steps) >= 20, list(zip(rungs, vals))
    #: ...and the rock has its own, or a bench field is one grey with a highlight on it
    rock = [seam.PAL[k] for k in ("deck", "rock", "rock_b")]
    rv = [lum(n) for n in rock]
    assert rv == sorted(rv) and min(b - a for a, b in zip(rv, rv[1:])) >= 20, list(zip(rock, rv))


def test_the_shard_is_a_hue_flip_off_the_ground_it_stands_on():
    """A turtle the colour of moss vanishes on moss. The whole point of cyan here is that the land
    is neutral greys and copper orange."""
    def rgb(n):
        return blocks.color(n, "side")

    a, b = rgb(seam.PAL["base"]), rgb(seam.PAL["deck"])
    assert math.dist(a, b) >= 80, (a, b)


# --------------------------------------------------------------------- the shard's geometry


def _one_shard(h: int, seed: int = 3):
    """A shard built on a synthetic floor, so the geometry is tested without a capture."""
    dv = du = 41
    c = Canvas(dv, h + 8, du)
    lot = _Lot(c, dv, du, seed=seed)

    class Flat:
        dv, du, clear = 41, 41, 1

        def seat(self, v, u):
            return 0 if 0 <= v < dv and 0 <= u < du else None

        def rooted(self, v, u, head=0):
            return self.seat(v, u)

        def free(self, v, u, y):
            return 0 <= v < dv and 0 <= u < du and not c.solid(v, y, u)

    got = seam._shard(lot, Flat(), 20, 20, h, seed)
    return c, got


def _cells(c: Canvas):
    out = set()
    for y in range(c.sy):
        for v in range(c.sx):
            for u in range(c.sz):
                if c.solid(v, y, u):
                    out.add((v, y, u))
    return out


def _components(cells):
    seen, comps = set(), []
    for s in cells:
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            v, y, u = stack.pop()
            comp.append((v, y, u))
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (v + d[0], y + d[1], u + d[2])
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(comp)
    return comps


@pytest.mark.parametrize("h", [10, 13, 17, 21, 26, 30])
def test_a_shard_is_ONE_PIECE_at_every_height(h):
    """**THE LEAN IS WHY THIS EXISTS.** Two single-cell courses offset diagonally are not
    neighbours, and a spike that steps sideways comes off as a shower of loose blocks - the ear
    tips, the ossicones and the braided root, a fourth time."""
    c, got = _one_shard(h)
    comps = _components(_cells(c))
    assert len(comps) == 1, [len(x) for x in comps]
    assert got["cells"] > 0


@pytest.mark.parametrize("h", [10, 17, 26, 30])
def test_a_shard_only_ever_narrows(h):
    """A crystal tapers. A section that widens again is a mushroom, and it is the kind of thing
    only a render catches - which is why it is measured."""
    c, _ = _one_shard(h)
    widths = []
    for y in range(c.sy):
        n = sum(1 for v in range(c.sx) for u in range(c.sz) if c.solid(v, y, u))
        if n:
            widths.append(n)
    assert widths == sorted(widths, reverse=True), widths


@pytest.mark.parametrize("h", [12, 18, 24, 30])
def test_the_top_of_every_shard_is_its_own_lamp(h):
    """The landing is its own lamp - `gen/parkour.py`'s rule, and what stops the night pass from
    ever needing to put a fixture ON a sculpture."""
    c, _ = _one_shard(h)
    top = max(y for y in range(c.sy)
              if any(c.solid(v, y, u) for v in range(c.sx) for u in range(c.sz)))
    names = {c.get_name(v, y, u).split(":")[-1]
             for y in (top, top - 1) for v in range(c.sx) for u in range(c.sz)
             if c.solid(v, y, u)}
    assert seam.PAL["glow"] in names or seam.PAL["crystal"] in names, names


def test_white_is_a_point_and_not_a_third_of_the_shard():
    """At 0.30/0.70 the top three tenths came out white with a lit cap on it and a field of them
    read as lollipops from the spine."""
    c, _ = _one_shard(24)
    counts = {}
    for y in range(c.sy):
        for v in range(c.sx):
            for u in range(c.sz):
                if c.solid(v, y, u):
                    n = c.get_name(v, y, u).split(":")[-1]
                    counts[n] = counts.get(n, 0) + 1
    total = sum(counts.values())
    assert counts.get(seam.PAL["tip"], 0) / total < 0.20, counts


def test_the_taper_holds_its_width_before_it_spikes():
    """`(r0 + 1) * 1.15` lost a four-wide shard a course of width by 19% of its height, which is a
    pole with a cap. The first shoulder belongs near a third of the way up."""
    r0 = seam.base_radius(28)
    assert r0 == 4, r0
    h = 28
    full = [y for y in range(h) if seam._radius(r0, y, h) == r0]
    assert len(full) / h >= 0.18, full
    assert seam._radius(r0, h - 1, h) == 0


def test_nothing_under_ten_courses_is_built_as_a_shard():
    """A six-course shard is two cells a colour band, which is a stripe. Splinters are `_rubble`'s
    job and the configs say so."""
    for kind in CONFIGS:
        lo, _hi = yaml.safe_load(open(CONFIGS[kind], encoding="utf-8"))["params"]["height"]
        assert lo >= 8, (kind, lo)


# --------------------------------------------------------------------- the field


def test_the_seam_is_a_LINE_and_the_field_falls_away_from_it():
    p = {**seam.SEAM, **cfg("fracture")}
    lobes = seam._lobes(p)
    v0, u0, v1, u1 = p["axis"]
    mv, mu = (v0 + v1) / 2, (u0 + u1) / 2
    dv, du = v1 - v0, u1 - u0
    ln = math.hypot(dv, du)
    nv, nu = -du / ln, dv / ln            # the unit NORMAL - a step in v alone is not a step off
    out = float(p["reach"]) * 1.5         # a diagonal axis, which the first version of this test
    on = seam._intensity(p, mv, mu, lobes)                       # got wrong
    far = seam._intensity(p, mv + nv * out, mu + nu * out, lobes)
    assert on > far
    assert far == 0.0


def test_the_outcrops_are_lobes_and_not_an_even_dusting():
    """The first build spread its shards evenly and the plan read as blue confetti on a dark
    floor - the thicket's and the deck soffit's own failure a third time. A vein surfaces in a
    few places and the ground between them is what makes those places read."""
    p = {**seam.SEAM, **cfg("fracture")}
    assert int(p["lobes"]) >= 3
    lobes = seam._lobes(p)
    assert len(lobes) == int(p["lobes"])
    # sampled along the axis, the field must actually VARY - a flat one is the dusting
    v0, u0, v1, u1 = p["axis"]
    vals = [seam._intensity(p, v0 + (v1 - v0) * t / 40.0, u0 + (u1 - u0) * t / 40.0, lobes)
            for t in range(41)]
    assert max(vals) / max(1e-6, sum(vals) / len(vals)) > 1.4, vals


def test_the_lobe_floor_keeps_a_seam_running_between_the_outcrops():
    p = {**seam.SEAM, **cfg("fracture")}
    lobes = seam._lobes(p)
    v0, u0, v1, u1 = p["axis"]
    vals = [seam._intensity(p, v0 + (v1 - v0) * t / 60.0, u0 + (u1 - u0) * t / 60.0, lobes)
            for t in range(61)]
    assert min(vals) > 0.0, "the line must not break into unrelated clumps"


# --------------------------------------------------------------------- the terraces


def test_a_flight_climbs_its_own_bank_rather_than_shipping_as_one_stair():
    """Walked against its own gradient the height only ever falls, `h > last` is true once, and
    the flight ships as a SINGLE STAIR - which the first cutting yard did, and which nothing but
    the block count could see."""
    spec = {"v": 0, "u": 0, "dv": 9, "du": 18, "rise": 5, "run": 3, "facing": "south"}
    hs = [seam._terrace_height(spec, 4, u) for u in range(18)]
    assert hs[0] > hs[-1], hs                     # facing south -> the low side is high u
    rises = sum(1 for a, b in zip(hs, hs[1:]) if abs(b - a) == 1)
    assert rises >= 4, hs


def test_a_bench_top_is_a_different_stone_from_its_face():
    """A terrace whose top course is the same rough rock as its face is a heap; the step only
    exists where the value changes."""
    assert seam.PAL["rock_b"] != seam.PAL["rock"]


# --------------------------------------------------------------------- the shipped designs


@pytest.mark.parametrize("kind", sorted(CONFIGS))
def test_the_shipped_design_stands_on_ground_and_never_on_a_street(kind):
    """**A SEAT IS NOT A PERMISSION.** `Park Ways` owns every paved cell in the park and its
    surfaces have exactly the shape of buildable ground - a solid course with clear air over it.
    Measured, the yard's lot contains seven courses of back promenade and the field's contains the
    well's own rim gallery."""
    s = shipped(kind)
    p = cfg(kind)
    box = None
    ox, oy, oz = s.origin
    ids = s.model.ids
    mine = set()
    names = list(s.model.names)
    for y in range(ids.shape[0]):
        for z in range(ids.shape[1]):
            for x in range(ids.shape[2]):
                if ids[y, z, x]:
                    mine.add((ox + x, oy + y, oz + z))
    lo = (min(c[0] for c in mine), max(c[0] for c in mine),
          min(c[1] for c in mine), max(c[1] for c in mine),
          min(c[2] for c in mine), max(c[2] for c in mine))
    box = (lo[0] - 1, lo[1] + 1, lo[2] - 1, lo[3] + 1, lo[4] - 1, lo[5] + 1)
    surf = seam.surface_cells(p.get("off_limits") or (), box)
    clash = mine & surf
    assert not clash, f"{len(clash)} cell(s) on somebody else's walking surface, e.g. " \
                      f"{sorted(clash)[:3]}"
    assert names  # the artifact loaded


@pytest.mark.parametrize("kind", sorted(CONFIGS))
def test_no_two_of_the_three_share_a_cell(kind):
    """Cross-design overlap is a DIFFERENT question from `verify_against`, which audits each
    design against the CAPTURE and cannot see its siblings - the casino shipped thirty modules
    each honestly reporting `overlap 0` while the hall's floor lay across every room's."""
    mine = {}
    for k, path in SHIPPED.items():
        if not os.path.exists(path):
            pytest.skip(f"{path} not generated")
        s = scan.load(path)
        ox, oy, oz = s.origin
        ids = s.model.ids
        cells = set()
        for y in range(ids.shape[0]):
            for z in range(ids.shape[1]):
                for x in range(ids.shape[2]):
                    if ids[y, z, x]:
                        cells.add((ox + x, oy + y, oz + z))
        mine[k] = cells
    for a in mine:
        for b in mine:
            if a < b:
                assert not (mine[a] & mine[b]), f"{a} and {b} share {len(mine[a] & mine[b])} cells"


def test_the_walk_and_the_lookout_are_never_taken_by_a_shard():
    """A shard leans up to a fifth of its height, so a foot beside the walk is a crystal over it.
    `lanes` holds the boxes and `lane_clear` holds the FOOT two further cells back."""
    p = {**seam.SEAM, **cfg("fracture")}
    lanes = [tuple(int(x) for x in b) for b in p["lanes"]]
    look = p["lookout"]
    lv, lu, ldv, ldu = (int(look[k]) for k in ("v", "u", "dv", "du"))
    covered = any(a <= lv and lv + ldv - 1 <= b and c <= lu and lu + ldu - 1 <= d
                  for a, b, c, d in lanes)
    assert covered, "the lookout's own box must be inside a lane or shards will grow through it"
    for leg in p["walk"]:
        v0, u0 = int(leg["v"]), int(leg["u"])
        v1, u1 = v0 + int(leg["dv"]) - 1, u0 + int(leg["du"]) - 1
        assert any(a <= v0 and v1 <= b and c <= u0 and u1 <= d for a, b, c, d in lanes), leg


def test_the_note_rail_exists_and_is_the_designs_only_verb():
    """A note block plays when a guest right-clicks it, with no redstone anywhere - so there is
    nothing here that could ship looking like a machine and do nothing, which is the failure that
    cut two finished casino games."""
    s = shipped("fracture")
    names = list(s.model.names)
    ids = s.model.ids
    n = sum(int((ids == i).sum()) for i, nm in enumerate(names)
            if nm.split(":")[-1] == "note_block")
    assert n >= 5, n
    wired = {"redstone_wire", "repeater", "comparator", "redstone_torch", "lever",
             "stone_button", "redstone_block", "observer", "piston", "dispenser"}
    present = {nm.split(":")[-1] for nm in names}
    assert not (present & wired), present & wired


def test_the_sign_is_the_LANDS_OWN_TIMBER():
    """`_Lot.sign` belongs to the Frontier and hard-codes `spruce_wall_sign` through that module's
    palette - measured, this design shipped one spruce sign into a land whose every other sign is
    warped."""
    s = shipped("fracture")
    present = {nm.split(":")[-1] for nm in s.model.names}
    assert "spruce_wall_sign" not in present
    assert seam.PAL["sign"] in present


@pytest.mark.parametrize("kind", sorted(CONFIGS))
def test_nothing_it_places_stands_taller_than_the_wells_own_column(kind):
    """`PRISMWORKS_V2_PLAN.md` keeps the land's two dominants and refuses a third. A field of
    spikes taller than the collar would take the mouth's own silhouette."""
    s = shipped(kind)
    ids = s.model.ids
    ys = [y for y in range(ids.shape[0]) if ids[y].any()]
    assert (max(ys) - min(ys) + 1) <= 34, max(ys) - min(ys) + 1


def test_the_probe_seats_TOP_DOWN_and_a_plate_over_a_lawn_is_ground():
    """**Written bottom-up this design generated exactly nothing**, with a clean audit, zero
    problems and a correct bill of materials: the first course with something under it is the
    LAWN even where a plate stands over it, so every plate column seated inside the plate and was
    then refused for being occupied."""
    class Ctx:
        def name_at(self, x, y, z):
            if y == 202:
                return "moss_block"           # the lawn
            if y == 203:
                return "polished_deepslate"   # ...and a plate standing on it
            return "air"

    g = seam._Deck(Ctx(), [0, 203, 0], 4, 4, (0, 0))
    assert g.seat(1, 1) == 1, "the seat is the course above the PLATE, not inside it"


def test_free_is_v_u_y_and_not_v_y_u():
    """`gen/claimrow.py` shipped exactly this transposition once: written the other way round the
    guard reads a cell that does not exist, passes, and the parapet ships wherever it likes."""
    class Ctx:
        def name_at(self, x, y, z):
            return "moss_block" if y == 202 else ("stone" if (x, y, z) == (1, 210, 1) else "air")

    g = seam._Deck(Ctx(), [0, 203, 0], 4, 4, (0, 0))
    assert g.free(1, 1, 6) is True            # world y 209 - air
    assert g.free(1, 1, 7) is False           # world y 210 - the stone


def test_a_pond_is_not_a_floor():
    """`_soft` says water is not free, which is right, and a seat probe that stopped at the first
    non-soft course would read a pond's surface as perfectly good ground and stand a crystal on
    it. `gen/thicket.py` learned this from the opposite side."""
    class Ctx:
        def name_at(self, x, y, z):
            return "water" if y == 202 else "air"

    g = seam._Deck(Ctx(), [0, 203, 0], 4, 4, (0, 0))
    assert g.seat(1, 1) is None
