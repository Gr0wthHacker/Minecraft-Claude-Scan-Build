"""The Midway's four buildings: the lot rule, the ground layer, the grammar, and the economy.

**EVERY CHECK HERE IS ONE A PICTURE CANNOT MAKE.** `render3d` draws a stair facing the wrong way
exactly as it draws one facing the right way, and it draws a fence, a wall, a pane and a set of
iron bars all as full cubes - it has hidden six separate faults on this park already. So the stair
convention, the lot boundary, the collision with the ground layer's own lamp arms, and the slim
vocabulary are all asserted off the BLOCK LIST, never looked at.

Nothing here pins a block count. A count is a snapshot and a snapshot fails the moment the design
improves; what is pinned is a CONTRACT - one connected piece, nothing outside the lot, nothing on a
cell the world already owns, a lintel between its jamb tops, a riser facing its ascent, a sign with
a wall behind it, and a value ladder that is actually a ladder.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pytest
import yaml

from mcbuild import audit as audit_mod, blocks, palette, schem
from mcbuild.gen import midway_builds as MB

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIGS = {
    "arrival_court": ROOT / "configs" / "pf_midway_arrival_court.yaml",
    "snack_window": ROOT / "configs" / "pf_midway_snack_window.yaml",
    "skill_arcade": ROOT / "configs" / "pf_midway_skill_arcade.yaml",
    "prize_point": ROOT / "configs" / "pf_midway_prize_point.yaml",
}
KINDS = tuple(CONFIGS)

#: The shipped ground layer, with `Park Ways`, `Park Rail`, the Carousel and the Sky Lift in it.
#: It is the only evidence about what these lots already contain, and it is 200x600x220, so the
#: tests that need it are the ones that read it and no others.
PARK = ROOT / "out" / "Park Complete.litematic"
PARK_ORIGIN = (97500, 190, 80300)     # the corner of that model, from its own sidecar
LAWN_Y = 202                          # ...and the course its lawn occupies

#: Blocks the game gained AFTER 1.19. The server is 1.19 and the client is 26.2, so any of these
#: is in the registry, has legal states, renders in a card, passes every audit - and cannot be
#: placed. `blocks.available` cannot be the gate: the allowlist is provisional, built from what
#: captures happen to hold, and it rejects `chiseled_stone_bricks`, which is a 1.14 block.
POST_1_19 = {
    "mud", "mud_bricks", "packed_mud", "cherry_planks", "cherry_log", "bamboo_planks",
    "pale_oak_planks", "pale_oak_log", "tuff_bricks", "polished_tuff", "chiseled_tuff",
    "copper_bulb", "copper_grate", "chiseled_copper", "suspicious_sand", "suspicious_gravel",
    "calibrated_sculk_sensor", "crafter", "trial_spawner", "vault", "heavy_core", "resin_block",
    "pink_petals", "torchflower", "pitcher_plant", "short_grass",
}

#: Jack rejected an earlier park at 17.7% of this. It is banned outright, not budgeted.
BANNED = {"cobblestone", "mossy_cobblestone", "cobblestone_slab", "cobblestone_stairs",
          "cobblestone_wall"}

#: The families whose members are not full cubes. `detail %` is the share of a build made of them,
#: and it is the closest single number to "does this look built rather than modelled".
DETAIL = ("trapdoor", "fence", "wall", "button", "lever", "stairs", "slab", "pane", "bars",
          "chain", "end_rod", "carpet", "candle", "lantern", "sign", "torch", "pressure_plate",
          "ladder", "rod", "flower_pot", "scaffolding")


def _params(kind: str) -> dict:
    return yaml.safe_load(CONFIGS[kind].read_text(encoding="utf-8"))["params"]


@pytest.fixture(scope="module")
def built():
    """{kind: (canvas, model, meta)} - built once, because four canvases is four seconds."""
    out = {}
    for kind in KINDS:
        c = MB.build(_params(kind))
        out[kind] = (c, c.to_model(), c.meta)
    return out


def _named(model) -> dict:
    """{(x, y, z): bare block name} for every solid cell of a model."""
    names = [n.split(":")[-1].split("[")[0] for n in model.names]
    out = {}
    ys, zs, xs = np.where(model.solid())
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        out[(x, y, z)] = names[int(model.ids[y, z, x])]
    return out


def _park_cells():
    """{(V, y_above_lawn, U): name} for everything the shipped ground layer holds above its lawn.

    Read once and cached on the function, because the file is 200 x 600 x 220 and three tests want
    it. `y_above_lawn` is 1 for the course a building's floor stands in, which is the same zero the
    generator uses - stating it in one place is the only way two coordinate systems stay agreed.
    """
    if getattr(_park_cells, "_cache", None) is None:
        m = schem.load(str(PARK))
        names = [n.split(":")[-1].split("[")[0] for n in m.names]
        lawn = LAWN_Y - PARK_ORIGIN[1]
        cells = {}
        ys, zs, xs = np.where(m.solid())
        for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
            if y <= lawn:
                continue
            cells[(int(x), int(y) - lawn, int(z))] = names[int(m.ids[y, z, x])]
        _park_cells._cache = cells
    return _park_cells._cache


# ------------------------------------------------------------------ the lot rule


@pytest.mark.parametrize("kind", KINDS)
def test_not_one_cell_leaves_its_lot(kind, built):
    """The lot rule, and it is the whole reason the canvas IS the lot.

    Anything outside is cropped at placement, so a part past the boundary is a part that silently
    does not exist - and a neighbour's column is lost with it. The generator refuses and counts;
    this asserts the count is zero and that the model's own box is exactly the lot.
    """
    c, model, meta = built[kind]
    v0, u0, v1, u1 = meta["lot"]
    sx, _sy, sz = model.shape_xyz
    assert (sx, sz) == (v1 - v0 + 1, u1 - u0 + 1), "the canvas is the lot, and nothing else"
    assert [c.sx, c.sz] == [sx, sz]
    p = _params(kind)
    assert p["lot"] == meta["lot"], "the config's lot and the build's own record must agree"


def test_a_cell_past_the_lot_raises_rather_than_being_dropped():
    """A refusal must be LOUD. A design that quietly loses its outer course audits perfectly and
    ships with a hole in it, which is exactly how this park lost a ride to one lamp."""
    tight = {**_params("prize_point"), "lot": [83, 355, 95, 369]}
    with pytest.raises(ValueError, match="outside lot"):
        MB.build(tight)


@pytest.mark.parametrize("kind", KINDS)
def test_the_building_fronts_west_onto_the_street_it_addresses(kind, built):
    """Every one of the four addresses a street to its WEST - the spine at V6-18 for the Arrival
    Court and the Skill Arcade, midway walk 1 and 2 for the other two - and the ground layer
    already draws a spur to each door. The facing is recorded as the compass word `park.py` uses,
    because `look.py` and `panel.py` both read it and a design with none makes them guess."""
    _c, model, meta = built[kind]
    assert meta["facing"] == "west"
    named = _named(model)
    v0, u0, _v1, _u1 = meta["lot"]
    p = _params(kind)
    spur_u = {"arrival_court": 235, "snack_window": 235,
              "skill_arcade": 362, "prize_point": 362}[kind]
    col = [y for (x, y, z), n in named.items() if z == spur_u - u0]
    assert col, "the spur's own column reaches this building"
    # ...and the doorway is ON that column: some course of it is open where the walls are solid
    front = min(x for (x, _y, _z) in named)
    at_door = {y for (x, y, z), _n in named.items() if x == front and z == spur_u - u0}
    assert 2 not in at_door or 3 not in at_door, \
        "the spur's column runs into a wall rather than a doorway"
    assert p["at"][0] - v0 == 97500, "the world origin is the lot corner, on the park's own frame"


# ------------------------------------------------------------------ the ground layer


@pytest.mark.parametrize("kind", KINDS)
def test_nothing_lands_on_a_cell_the_ground_layer_already_owns(kind, built):
    """THE LOTS ARE NOT EMPTY. `Park Ways`'s lamp masts stand on the verges and their ARMS reach
    two cells into all four of these lots, three to five courses above the lawn. A wall drawn
    through one of those is an overlap that no render can show - a lantern inside a wall draws
    exactly like a wall - so it is measured against the shipped ground layer instead.

    `moss_carpet` is the exception and it is declared as one in every config: the lawn's own
    decorative scatter is broken where a building stands on it, which is what
    `finish.verify_replaceable` means.
    """
    if not PARK.exists():
        pytest.skip(f"{PARK.name} is not in out/ - regenerate it with tools/park_place.py")
    _c, model, meta = built[kind]
    v0, u0, _v1, _u1 = meta["lot"]
    world = _park_cells()
    clash = []
    for (x, y, z), _n in _named(model).items():
        got = world.get((v0 + x, y + 1, u0 + z))
        if got is not None and got != "moss_carpet":
            clash.append((v0 + x, y + 1, u0 + z, got))
    assert clash == [], f"{len(clash)} cell(s) the world already holds: {clash[:6]}"


@pytest.mark.parametrize("kind", KINDS)
def test_the_blocked_boxes_are_the_lamp_arms_the_world_really_has(kind, built):
    """A guard aimed at nothing is a guard that has gone stale. Every cell each config declares
    `blocked` must actually be occupied in the shipped ground layer, or the measurement it was
    derived from has moved and the envelope was set in from a boundary that is no longer there."""
    if not PARK.exists():
        pytest.skip(f"{PARK.name} is not in out/")
    world = _park_cells()
    boxes = _params(kind)["blocked"]
    assert boxes, "every one of these four lots has a lamp arm in it"
    for bv0, by0, bu0, bv1, by1, bu1 in boxes:
        hits = [(v, y, u) for v in range(bv0, bv1 + 1) for y in range(by0, by1 + 1)
                for u in range(bu0, bu1 + 1) if (v, y, u) in world]
        assert hits, f"blocked box {(bv0, by0, bu0, bv1, by1, bu1)} guards nothing any more"


def test_a_design_that_wants_a_blocked_cell_raises():
    """The belt to the envelope's braces. Wanting a cell the ground layer owns must be an error
    here, not an overlap discovered in game an hour later."""
    p = {**_params("prize_point")}
    # the whole counter frontage, declared as somebody else's
    p["blocked"] = list(p["blocked"]) + [[83, 0, 353, 97, 10, 371]]
    with pytest.raises(ValueError, match="ground layer already owns"):
        MB.build(p)


# ------------------------------------------------------------------ the build itself


@pytest.mark.parametrize("kind", KINDS)
def test_it_is_one_piece_with_no_placement_problems(kind, built):
    """A roof of stairs is not connected to itself - course k and course k+1 meet only at a corner
    - so this is the check that says the tympanum and the hip's under-slab are doing their job."""
    _c, model, _meta = built[kind]
    res = audit_mod.audit(model, ground=False, ground_block="moss_block")
    assert res.problems == [], "\n".join(str(p) for p in res.problems[:10])
    assert len(res.components) == 1, f"components: {sorted(res.components, reverse=True)[:6]}"


@pytest.mark.parametrize("kind", KINDS)
def test_it_claims_nothing_below_the_course_above_the_lawn(kind, built):
    """The lawn belongs to `Park Ways`. Every cell here is at y0 or above, where y0 is the first
    course over it, so the two designs share the lot without contesting one cell of it."""
    _c, model, _meta = built[kind]
    assert min(y for (_x, y, _z) in _named(model)) >= 0


@pytest.mark.parametrize("kind", KINDS)
def test_every_stair_leans_the_way_its_own_geometry_says(kind, built):
    """A STAIR'S TALL SIDE IS ITS `facing`, and our renderer draws both directions identically.

    Two rules, and every stair in these four buildings is one or the other:
      * a piece of TRIM leans INTO the wall it grows from, so a cell with masonry on the side it
        faces and air on the side behind it is right;
      * a ROOF course leans toward its own ridge, which is the same rule as a flight ascending
        toward its landing.
    Both come to the same measurable thing - the cell a stair FACES must not be air while the cell
    behind it is - so a stair put in backwards fails here and can never be eyeballed.
    """
    _c, model, _meta = built[kind]
    named = _named(model)
    step = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
    backwards = []
    for (x, y, z), n in named.items():
        if not n.endswith("_stairs"):
            continue
        f = model.props_at(x, y, z).get("facing")
        assert f in step, f"{n} at {(x, y, z)} has no legal facing"
        assert blocks.validate(n, model.props_at(x, y, z)) == [], f"{n} at {(x, y, z)}"
        dx, _dy, dz = step[f]
        ahead = (x + dx, y, z + dz) in named or (x + dx, y + 1, z + dz) in named
        behind = (x - dx, y, z - dz) in named or (x - dx, y + 1, z - dz) in named
        if behind and not ahead:
            backwards.append((x, y, z, n, f))
    assert backwards == [], f"{len(backwards)} stair(s) leaning away from their own mass: " \
                            f"{backwards[:6]}"


def test_a_roof_course_leans_toward_its_own_ridge():
    """The rule above, isolated on a bare gable so it is pinned by construction and not by luck.

    A gable roof over a 9-wide span rises from both eaves; the stair on the low-U side must face
    +U and the one on the high-U side must face -U, or the roof is built inside out and every
    render in this repo draws it identically to a correct one.
    """
    from mcbuild.gen.canvas import Canvas
    c = Canvas(3, 12, 9)
    L = MB._Lot(c, (0, 0, 2, 8))
    MB._gable(L, 0, 0, 2, 8, 2, 0, axis="v", tympanum=False)
    got = {}
    for z in range(9):
        for y in range(2, 12):
            n = c.get_name(1, y, z)
            if n.endswith("_stairs"):
                got[z] = c.reg.palette[c.get(1, y, z)].value["Properties"].value["facing"].value
    assert got[0] == "south" and got[8] == "north", got
    assert all(v == "south" for k, v in got.items() if k < 4)
    assert all(v == "north" for k, v in got.items() if k > 4)


def test_a_pitched_roof_stays_under_the_building_it_covers():
    """A 1:1 slope on a 27-wide hall puts its ridge THIRTEEN courses over its eaves, which is past
    this park's landmark rule - only the Sky Lift and one ride per land may enter the crown. The
    pitch is a parameter for that reason, and halving it must halve the rise."""
    from mcbuild.gen.canvas import Canvas
    highs = {}
    for pitch in (1, 2):
        c = Canvas(3, 40, 27)
        L = MB._Lot(c, (0, 0, 2, 26))
        MB._gable(L, 0, 0, 2, 26, 2, 0, axis="v", pitch=pitch, tympanum=False)
        highs[pitch] = max(y for y in range(40) if c.ids[y].any())
    assert highs[1] - 2 == 13
    assert highs[2] - 2 == 6, "a 1:2 pitch is half the rise, and it is what the Arcade uses"


def test_every_opening_has_its_lintel_between_its_jamb_tops():
    """An opening whose lintel sits ON its jambs is a hole with a beam over it. The lintel belongs
    in the course ABOVE the jamb tops, spanning the gap between them - the same rule that made an
    earlier park's door frames read as doors. Measured on the KIT, so no call site can skip it.

    (`Canvas.get_name` answers "minecraft:air", not "air", so a first version of this compared
    against the wrong string, found every cell non-empty and reported a jamb eleven courses tall.
    `Canvas.solid` is the question actually being asked.)
    """
    from mcbuild.gen.canvas import Canvas
    c = Canvas(3, 12, 11)
    L = MB._Lot(c, (0, 0, 2, 10))
    MB._opening(L, 1, 5, -1, 0, 2, 5, 2, 0, glazed=False, sill=False, arch=False)
    jamb = [y for y in range(12) if c.solid(1, y, 2)]           # u = 5 - (2 + 1), the west jamb
    assert jamb == [2, 3, 4, 5], f"a jamb runs to the head of the opening and no further: {jamb}"
    for z in range(3, 8):                                       # the opening itself, u 3..7
        assert c.get_name(1, max(jamb) + 1, z).endswith(MB.PAL["course"]), \
            "the lintel spans the gap in the course ABOVE the jamb tops"
        assert not c.solid(1, max(jamb), z), "the opening itself is open"


@pytest.mark.parametrize("kind", KINDS)
def test_every_sign_has_a_wall_behind_it_and_reads_within_its_width(kind, built):
    """Four of an earlier park's seven building kinds hung a sign on the one column that has an
    opening in it, and it is invisible in every render: a wall sign floating in air draws exactly
    like one on a wall. Fifteen characters is where a line clips mid-word."""
    _c, model, meta = built[kind]
    named = _named(model)
    step = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
    signs = [(p, n) for p, n in named.items() if n.endswith("_wall_sign")]
    assert len(signs) == meta["signs"] >= 3, "every one of these is named on its own front"
    for (x, y, z), _n in signs:
        f = model.props_at(x, y, z)["facing"]
        dx, dz = step[f]
        assert (x - dx, y, z - dz) in named, f"sign at {(x, y, z)} facing {f} has no wall behind it"
    for tile in model.tile_entities or []:
        pass
    for lines in _sign_lines(model):
        for line in lines:
            assert len(line) <= MB.SIGN_WIDTH, f"{line!r} clips mid-word on a sign"


def _sign_lines(model):
    """Every sign's four lines, off the model's own tile entities."""
    import json as _json
    out = []
    for tag in model.tile_entities or []:
        d = tag.value
        for side in ("front_text", "back_text"):
            if side not in d:
                continue
            msgs = d[side].value["messages"].value
            out.append([_json.loads(t.value).get("text", "") for t in msgs])
    return out


@pytest.mark.parametrize("kind", KINDS)
def test_every_lantern_hangs_from_something_that_can_hold_one(kind, built):
    """`LanternBlock` overrides `canSurvive` and asks `canSupportCenter` of the block above, so a
    slab, a stair, a fence or a wall qualifies and a TRAPDOOR does not. The first build hung four
    off the valance over the box office and the audit named all four; `_lamp` asks now, which
    means a lamp with nothing to hang from is simply not placed - so this also asserts that each
    build actually GOT its lamps, because a silently refused fixture is this repo's oldest bug."""
    _c, model, meta = built[kind]
    named = _named(model)
    lamps = [p for p, n in named.items() if n == "lantern"]
    assert len(lamps) == meta["lamps"] >= 5, "a building nobody can see inside is not lit"
    for (x, y, z) in lamps:
        above = named.get((x, y + 1, z))
        assert above is not None and MB._can_hang(above), \
            f"lantern at {(x, y, z)} hangs from {above}"


@pytest.mark.parametrize("kind", KINDS)
def test_it_has_a_real_way_in_and_a_separate_way_for_staff(kind, built):
    """Every build card asks for a public front and a service rear that a guest never crosses.
    A doorway is a hole in a wall with a lintel over it, so it is measured as a hole: the front
    wall and the back wall each have a run of open cells at standing height."""
    _c, model, _meta = built[kind]
    named = _named(model)
    xs = [x for (x, _y, _z) in named]
    front, back = min(xs), max(xs)
    for plane, what in ((front, "front"), (back, "back")):
        wall = {(y, z) for (x, y, z) in named if x == plane}
        if not wall:
            continue
        zs = {z for (_y, z) in wall}
        gaps = [z for z in zs if (2, z) not in wall and (1, z) not in wall]
        assert gaps, f"the {what} of this building is solid at standing height: no way through"


# ------------------------------------------------------------------ the economy and the palette


@pytest.mark.parametrize("kind", KINDS)
def test_every_block_is_real_1_19_spendable_and_does_not_fall(kind, built):
    """`grass_block` and every form of dirt are CURRENCY on this server: real, legal, placeable and
    money. That is a third axis beside "does it exist" and "does 1.19 have it"."""
    _c, model, _meta = built[kind]
    for name in {n.split(":")[-1].split("[")[0] for n in model.names} - {"air"}:
        assert blocks.exists(name), name
        assert name not in POST_1_19, f"{name} is newer than the 1.19 server"
        assert blocks.spendable(name), f"{name} is currency on this server"
        assert not blocks.falls(name), f"{name} falls, and these have air under them"


@pytest.mark.parametrize("kind", KINDS)
def test_the_park_s_banned_block_appears_nowhere(kind, built):
    """Jack: "use deep slates etc as necessary, smooth stones, bricks" - and an earlier park was
    rejected at 17.7% cobblestone. It is banned outright rather than budgeted."""
    _c, model, _meta = built[kind]
    got = {n.split(":")[-1].split("[")[0] for n in model.names} & BANNED
    assert not got, f"cobblestone: {sorted(got)}"


@pytest.mark.parametrize("kind", KINDS)
def test_nothing_expensive_is_spent(kind, built):
    """Nothing here is declared functional, so nothing expensive is bought. The `ok` tier is the
    counters, sills, glazing and the paving's lighter grey - the small parts, and a minority."""
    _c, model, _meta = built[kind]
    res = audit_mod.audit(model, ground=False, ground_block="moss_block")
    assert res.tiers.get("expensive", 0) == 0
    assert res.tiers.get("ok", 0) / res.blocks <= 0.20
    assert res.tiers.get("cheap", 0) / res.blocks >= 0.80


@pytest.mark.parametrize("kind", KINDS)
def test_it_is_detailed_and_its_palette_is_deep(kind, built):
    """The one number that separates outside architecture from ours: their builds run 25-60% of
    cells in a non-cube family and ours ran 0-25%. Stairs, slabs, walls, fences, trapdoors, panes
    and signs are what makes a voxel wall read as built rather than as modelled."""
    _c, model, _meta = built[kind]
    counts = {}
    for i in model.ids[model.solid()].tolist():
        n = model.names[i].split(":")[-1].split("[")[0]
        counts[n] = counts.get(n, 0) + 1
    total = sum(counts.values())
    detail = sum(v for k, v in counts.items() if any(d in k for d in DETAIL))
    assert detail / total >= 0.17, f"detail is {detail / total:.1%}"
    assert len(counts) >= 15, f"palette is {len(counts)} blocks"
    assert max(counts.values()) / total <= 0.30, "no single block may be a third of a building"


def test_the_value_ladder_is_measured_ACROSS_FAMILIES_and_is_actually_a_ladder():
    """This repo has concluded four separate times that its economy has no value contrast, and
    every one of those measurements was taken INSIDE one material family, where a ladder cannot
    exist by construction. Measured across families the rungs are real, and this asserts the
    smallest adjacent step rather than the range - a wide range with two rungs nobody can tell
    apart is not a ladder."""
    def lum(n):
        r, g, b = blocks.color(n)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    rungs = [PAL for PAL in (MB.PAL["plinth"], MB.PAL["band"], MB.PAL["field"], MB.PAL["frame"])]
    vals = [lum(n) for n in rungs]
    assert vals == sorted(vals), f"{list(zip(rungs, vals))} is not in order"
    steps = [b - a for a, b in zip(vals, vals[1:])]
    assert min(steps) >= 18, f"the smallest rung is {min(steps):.0f} and reads as no line at all"
    # ...and the rungs come from at least three different MATERIALS. `blocks.kind` answers "block"
    # for all four, which is the registry's own type and not a material family, so the family is
    # taken off the name: a qualifier (polished, cracked, bricks, ...) and a dye name are the two
    # things that never change how much light a material returns.
    dressing = {"polished", "cracked", "chiseled", "smooth", "cut", "brick", "bricks", "block",
                "blocks", "tiles", "stairs", "slab", "wall", "red", "white", "black", "light",
                "gray", "grey"}

    def family(n):
        return "_".join(w for w in n.split("_") if w not in dressing)

    assert len({family(n) for n in rungs}) >= 3,         f"a ladder inside one family is not a ladder: {sorted(family(n) for n in rungs)}"


def test_the_texture_dither_is_hashed_on_the_CELL_and_never_on_the_COURSE():
    """Hashed on the course, every block in a course comes out identical and the wall is
    horizontal stripes - which the deck soffit shipped once. Two cells one course apart in the
    same column must be able to differ."""
    seen = {MB._field(0, 40, y, 300) for y in range(40)}
    assert len(seen) == 2, "a whole column came out one material"
    row = {MB._field(0, 40, 5, u) for u in range(60)}
    assert len(row) == 2, "a whole course came out one material"


@pytest.mark.parametrize("kind", KINDS)
def test_no_street_furniture_stands_outside_the_building(kind, built):
    """Jack threw the previous attempt's plazas, queue rails, ridegates, booths, arches, markers,
    lampposts, flagpoles and benches away as chaos, and the ground layer already draws every lamp
    and every path in this park. So NOTHING here stands clear of its own building: every cell
    above the floor course is part of a wall, a roof or a fitting attached to one, and the only
    thing this module lays on open ground is the threshold that joins a spur to a door."""
    _c, model, _meta = built[kind]
    named = _named(model)
    solid = set(named)
    loose = []
    for (x, y, z), n in named.items():
        if y == 0:
            continue                       # the floor and the threshold: ground, not furniture
        touching = any((x + dx, y + dy, z + dz) in solid
                       for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1),
                                          (0, -1, 0), (0, 1, 0)))
        if not touching:
            loose.append((x, y, z, n))
    assert loose == [], f"{len(loose)} free-standing cell(s): {loose[:6]}"
    assert not any(n in ("oak_fence", "cobblestone_wall") and y == 1 and
                   all((x + dx, y, z + dz) not in solid for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                   for (x, y, z), n in named.items()), "a lone post on open ground is a lamppost"


@pytest.mark.parametrize("kind", KINDS)
def test_the_meta_states_a_contract_the_next_session_can_check(kind, built):
    """A build whose promise lives only in a chat message is one nobody can audit a month later."""
    _c, _model, meta = built[kind]
    assert meta["kind"] == "midway_build" and meta["build"] == kind
    assert meta["name"].startswith("PF "), "the PF prefix keeps these clear of the retired park"
    assert "contract" in meta and str(meta["lot"][0]) in meta["contract"]
    assert meta["openings"] > 0


def test_each_build_card_s_own_count_is_what_shipped(built):
    """The three things the build cards state as NUMBERS: exactly three arcade bays, at most six
    seats at the food counter, and a turnstile screen with more than one gate in it."""
    assert built["skill_arcade"][2]["bays"] == 3, "the card allows exactly three bays"
    assert built["snack_window"][2]["seats"] <= 6, "'build last; max 6 seats'"
    assert built["snack_window"][2]["seats"] == 6
    assert built["arrival_court"][2]["gates"] >= 3, "a single turnstile is a bottleneck"
