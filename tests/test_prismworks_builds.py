"""What the six Prismworks buildings PROMISE, pinned so a later pass cannot quietly drop it.

Every assertion here is a CONTRACT rather than a snapshot of a block count: a test that pins
"2,647 blocks" fails the first time somebody improves the building, which trains people to edit
the test. What is pinned is the things that were expensive to learn - the lot boundary, the park's
own lamp arms, the value ladder measured ACROSS families, the stair convention our renderer cannot
draw wrong, and the fact that this design set claims no mechanism at all.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcbuild import blocks, circuit, palette, schem                      # noqa: E402
from mcbuild.gen import prismworks_builds as pb                          # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")

#: THE GROUND LAYER, READ FROM THE GROUND LAYER'S OWN DESIGNS AND NOT FROM A COMPOSITE.
#:
#: This used to be `out/Park Complete.litematic`, and that is a SNAPSHOT TRAP: `Park Complete` is
#: a composite of the whole park, so the day these six were first generated and merged into it,
#: the fixture began holding THE BUILDINGS THEMSELVES. Three tests then compared each design to
#: its own previous self - "is this lot empty of anything but lawn" answered by a model of the
#: building standing in the lot, and "is the Ascent the tallest thing in the park" answered by the
#: Ascent. All three failed identically before and after any change, which is not a test.
#:
#: What all three actually mean is the GROUND: `Park Ways` (lawn, spine, avenues, walks, spurs,
#: verges, and every lamp mast and arm) plus `Park Rail`. Those are designs, so they cannot
#: absorb their neighbours - and the lamp arms these tests exist to protect are all in the first.
GROUND_PARTS = [os.path.join(ROOT, "out", "Park Ways.litematic"),
                os.path.join(ROOT, "out", "Park Rail.litematic")]
#: ...and the park's OTHER buildings, for the one test that asks whether the Ascent is the
#: tallest thing standing. That question is about neighbours, so it must exclude the Ascent's own
#: lot rather than the whole composite - see `test_the_ascent_tops_out...`.
GROUND = os.path.join(ROOT, "out", "Park Complete.litematic")
CONFIGS = ["pf_prismworks_foundry_gate", "pf_prismworks_prism_array",
           "pf_prismworks_resonance_vault", "pf_prismworks_prism_ascent",
           "pf_prismworks_forge_deck", "pf_prismworks_service_gallery"]

#: The park's own frame. V -> world X, U -> world Z, and the lawn is the course BELOW y=0.
LAWN_Y = pb.ANCHOR[1] - 1

#: Anything a builder clears before laying a plinth. This is the ONLY context block these designs
#: are allowed to stand where - see `test_nothing_but_lawn_trim_is_ever_replaced`.
CLEARABLE = {"moss_carpet"}

#: The land's declared value ladder, darkest first. It is MEASURED below rather than believed:
#: this repo has three separate times concluded that this economy has no value contrast, and all
#: three measurements were taken inside ONE material family, where a ladder cannot exist by
#: construction because dressing a stone does not change how much light it returns.
LADDER = ["recess", "field", "pier", "signal", "high", "glow"]


def _cfg(stem: str) -> dict:
    with open(os.path.join(ROOT, "configs", f"{stem}.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _lum(rgb) -> float:
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


# --------------------------------------------------------------------------- the builds


def _build(stem: str):
    cfg = _cfg(stem)
    canvas = pb.build(cfg["params"])
    return cfg, canvas, canvas.to_model()


@pytest.fixture(scope="module")
def built():
    """Every design, built once. Six canvases is a few seconds; six pipelines is minutes."""
    return {stem: _build(stem) for stem in CONFIGS}


@pytest.fixture(scope="module")
def ground():
    """The ground layer, composited into one array on the park's own frame.

    Built rather than loaded, because the two parts have different origins and the callers index
    it as `[y - (LAWN_Y - 190) ...][U][V]` - the frame `Park Complete` happens to have. Stating
    that conversion once is the only way two coordinate systems stay agreed.
    """
    parts = [p for p in GROUND_PARTS if os.path.exists(p)]
    if not parts:
        pytest.skip("the ground layer designs are not on disk")
    return _composite(parts)


def _composite(paths):
    """A `Model`-alike on the (Y-190, U-80300, V-97500) frame `Park Complete` uses."""
    class _M:
        pass

    out = _M()
    out.ids = np.zeros((220, 600, 200), dtype=np.int32)
    names = ["minecraft:air"]
    index = {"minecraft:air": 0}
    for path in paths:
        m = schem.load(path)
        sc = json.loads(open(path.replace(".litematic", ".scan.json"),
                             encoding="utf-8").read())["origin"]
        ox, oy, oz = int(sc["x"]) - 97500, int(sc["y"]) - 190, int(sc["z"]) - 80300
        remap = {}
        for i, n in enumerate(m.names):
            if n not in index:
                index[n] = len(names)
                names.append(n)
            remap[i] = index[n]
        ys, zs, xs = np.nonzero(m.ids)
        for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
            wy, wz, wx = y + oy, z + oz, x + ox
            if 0 <= wy < 220 and 0 <= wz < 600 and 0 <= wx < 200:
                out.ids[wy, wz, wx] = remap[int(m.ids[y, z, x])]
    out.names = names
    out.solid = lambda: out.ids != 0
    return out


def _cells(model):
    """[(v, u, y, name)] in LOT-LOCAL coordinates, for every solid cell of a design."""
    names = [n.split(":")[-1].split("[")[0] for n in model.names]
    ys, zs, xs = np.nonzero(model.ids)
    return [(int(x), int(z), int(y), names[model.ids[y, z, x]]) for y, z, x in zip(ys, zs, xs)]


def _names(model):
    return {n.split(":")[-1].split("[")[0] for n in model.names
            if n.split(":")[-1].split("[")[0] != "air"}


# --------------------------------------------------------------------------- the palette


def test_the_value_ladder_is_measured_ACROSS_families_and_every_rung_reads():
    """Six stops, darkest to brightest, every gap >= 20 luminance.

    A gap under about 15 is a tone step nobody can see at ten blocks, which is exactly what
    `blackstone` -> `polished_blackstone_bricks` -> `chiseled_polished_blackstone` (38 -> 45 -> 51)
    gives you and why the land's lines have to be geometry OR a cross-family step.
    """
    lums = [_lum(blocks.color(pb.PRISM[k], "side")) for k in LADDER]
    assert lums == sorted(lums), f"the ladder is not monotonic: {list(zip(LADDER, lums))}"
    gaps = [b - a for a, b in zip(lums, lums[1:])]
    assert min(gaps) >= 20, f"a rung nobody can see: {list(zip(LADDER, lums))} gaps {gaps}"
    # ...and the control: the same measurement INSIDE one family fails, which is the whole reason
    # the ladder is built the way it is.
    family = [_lum(blocks.color(n, "side")) for n in
              ("blackstone", "polished_blackstone_bricks", "chiseled_polished_blackstone")]
    assert max(family) - min(family) < 20


def test_every_material_is_cheap_or_ok_available_spendable_and_not_cobblestone(built):
    for stem, (_cfg_, _c, model) in built.items():
        for name in _names(model):
            base = name.replace("_wall_sign", "")
            assert blocks.available(name) or blocks.available(base), f"{stem}: {name} unavailable"
            assert blocks.spendable(name), f"{stem}: {name} is CURRENCY on this server"
            assert palette.tier(name) != "expensive", f"{stem}: {name} is expensive tier"
            assert "cobble" not in name, f"{stem}: {name} - Jack asked for deepslate, not cobble"
            assert "dirt" not in name and "grass" not in name and "podzol" not in name


def test_the_bulk_of_every_building_is_cheap_tier(built):
    """`ok` tier is the small parts. A third of a building in deepslate would blow the policy."""
    for stem, (_cfg_, _c, model) in built.items():
        counts = {}
        for _v, _u, _y, name in _cells(model):
            counts[name] = counts.get(name, 0) + 1
        total = sum(counts.values())
        cheap = sum(n for k, n in counts.items() if palette.tier(k) == "cheap")
        assert cheap / total >= 0.75, f"{stem}: only {cheap / total:.0%} cheap tier"


def test_every_building_has_a_real_palette_and_real_trim(built):
    """15+ block types and >= 12% detail cells - the corpus's own two numbers for 'looks built'.

    Measured against 31 outside builds, their architecture runs 25-60% non-cube detail and ours
    ran 0-25%; stairs, fences and trapdoors were 7-30x under-used here. A plain shed is allowed to
    be the lowest of the six and is not allowed to be bare.
    """
    detail_kinds = ("slab", "stairs", "wall", "trapdoor", "fence", "bars", "chain", "rod",
                    "lantern", "sign", "pane", "carpet")
    for stem, (_cfg_, _c, model) in built.items():
        names = _names(model)
        assert len(names) >= 15, f"{stem}: only {len(names)} block types"
        counts = {}
        for _v, _u, _y, name in _cells(model):
            counts[name] = counts.get(name, 0) + 1
        total = sum(counts.values())
        det = sum(n for k, n in counts.items() if any(d in k for d in detail_kinds))
        assert det / total >= 0.12, f"{stem}: detail {det / total:.1%}"


# --------------------------------------------------------------------------- the lot


def test_not_one_cell_of_any_design_leaves_its_own_lot(built):
    """The lot is the bound, and a cell outside it is CROPPED at placement - simply lost.

    This park has already lost a 111-block ride to a single lamp two cells outside its street.
    `_Lot.put` refuses anything outside and counts it, so a non-zero count is not a safe overrun,
    it is a piece of a building that was never built.
    """
    for stem, (cfg, canvas, _m) in built.items():
        dv, du = cfg["params"]["size"]
        assert (canvas.sx, canvas.sz) == (dv, du), f"{stem}: canvas is not the lot"
        assert canvas.meta["outside_lot_refused"] == 0, (
            f"{stem}: {canvas.meta['outside_lot_refused']} cells were drawn outside the lot and "
            f"thrown away - the geometry that wanted them is missing from the build")


def test_the_lot_of_every_config_is_the_one_the_park_grid_measured(built):
    """The six lots, off `tools/park_lots.PLACEMENT` and PARK_GRID_PLAN's own table."""
    want = {"pf_prismworks_foundry_gate": ((24, 430), (53, 36)),
            "pf_prismworks_prism_array": ((24, 471), (53, 51)),
            "pf_prismworks_resonance_vault": ((82, 471), (53, 41)),
            "pf_prismworks_prism_ascent": ((24, 527), (93, 72)),
            "pf_prismworks_forge_deck": ((130, 527), (24, 66)),
            "pf_prismworks_service_gallery": ((157, 550), (13, 41))}
    for stem, (cfg, canvas, _m) in built.items():
        at, size = want[stem]
        assert tuple(cfg["params"]["at"]) == at
        assert tuple(cfg["params"]["size"]) == size
        # ...and the whole land is Prismworks' own U430-599
        assert 430 <= at[1] and at[1] + size[1] - 1 <= 599
        assert canvas.world_origin == (pb.ANCHOR[0] + at[0], pb.ANCHOR[1], pb.ANCHOR[2] + at[1])


def test_every_design_stands_on_the_lawn_and_owns_no_cell_of_it(built):
    """Y=0 of a canvas is world Y203, the first course above the lawn at Y202."""
    for _stem, (_cfg_, canvas, _m) in built.items():
        assert canvas.world_origin[1] == LAWN_Y + 1


def test_no_lot_is_filled(built):
    """20-40% of every lot stays open ground. A facade field wall to wall is a car park.

    The columns are counted rather than the cells: what makes a lot read as open is the ground you
    can see, not the air over a roof.
    """
    for stem, (cfg, canvas, model) in built.items():
        dv, du = cfg["params"]["size"]
        occupied = {(v, u) for v, u, _y, _n in _cells(model)}
        open_share = 1 - len(occupied) / (dv * du)
        assert open_share >= 0.18, f"{stem}: only {open_share:.0%} of the lot is left open"


# --------------------------------------------------------------------------- the park's lamps


def _lamp_arms(ground_model, at, size):
    """Cells the PARK already occupies inside a lot above the lawn, in lot-local coordinates.

    Re-derived from the shipped ground rather than transcribed: `Park Ways` stands an avenue lamp
    on the lot boundary lines and throws a four-armed `iron_bars` cross at world Y209, one arm of
    which reaches one cell INTO the lot. A hand-copied list of those goes stale the first time a
    lamp rhythm moves; this one cannot.
    """
    v0, u0 = at
    dv, du = size
    names = [n.split(":")[-1].split("[")[0] for n in ground_model.names]
    out = {}
    sub = ground_model.ids[LAWN_Y - 190 + 1:, u0:u0 + du, v0:v0 + dv]
    ys, zs, xs = np.nonzero(sub)
    for y, z, x in zip(ys, zs, xs):
        name = names[sub[y, z, x]]
        if name in CLEARABLE:
            continue
        out[(int(x), int(z), int(y))] = name
    return out


def test_every_lamp_arm_inside_these_lots_is_named_by_its_config_and_left_empty(built, ground):
    """The list is re-derived from the world; the build is asserted to occupy none of it.

    Both halves matter. A lamp arm the config does not know about is a cell the building will
    fight the park for, and a `keep_clear` entry the world does not have is a hole in a wall for
    no reason.
    """
    for stem, (cfg, canvas, model) in built.items():
        at, size = cfg["params"]["at"], cfg["params"]["size"]
        arms = _lamp_arms(ground, at, size)
        assert all(n == "iron_bars" for n in arms.values()), \
            f"{stem}: the park holds something other than a lamp arm in this lot: {arms}"
        declared = {tuple(k) for k in (cfg["params"].get("keep_clear") or [])}
        assert declared == set(arms), f"{stem}: keep_clear {sorted(declared)} != world {sorted(arms)}"
        occupied = {(v, u, y) for v, u, y, _n in _cells(model)}
        assert not (occupied & set(arms)), f"{stem}: built into a lamp arm"


def test_nothing_but_lawn_trim_is_ever_replaced(built, ground):
    """A design cell over an existing block is a collision unless the block is clearable trim.

    This is the cheap half of `finish.verify_against`: it says nothing about placement legality,
    and it is the half that catches a building drawn over somebody else's design.
    """
    names = [n.split(":")[-1].split("[")[0] for n in ground.names]
    for stem, (cfg, canvas, model) in built.items():
        v0, u0 = cfg["params"]["at"]
        clashes = []
        for v, u, y, _n in _cells(model):
            wy = (LAWN_Y + 1 + y) - 190
            if wy >= ground.ids.shape[0]:
                continue
            here = names[ground.ids[wy, u0 + u, v0 + v]]
            if here != "air" and here not in CLEARABLE:
                clashes.append((v, u, y, here))
        assert not clashes, f"{stem}: {len(clashes)} cells over standing park: {clashes[:6]}"


# --------------------------------------------------------------------------- the geometry


def test_every_design_is_ONE_connected_piece(built):
    for stem, (_cfg_, _c, model) in built.items():
        sol = model.solid()
        seen = np.zeros_like(sol)
        ys, zs, xs = np.nonzero(sol)
        stack = [(int(ys[0]), int(zs[0]), int(xs[0]))]
        seen[stack[0]] = True
        while stack:
            y, z, x = stack.pop()
            for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                a, b, c = y + dy, z + dz, x + dx
                if 0 <= a < sol.shape[0] and 0 <= b < sol.shape[1] and 0 <= c < sol.shape[2] \
                        and sol[a, b, c] and not seen[a, b, c]:
                    seen[a, b, c] = True
                    stack.append((a, b, c))
        assert int(seen.sum()) == int(sol.sum()), \
            f"{stem}: {int(sol.sum()) - int(seen.sum())} cells are not attached to the building"


def test_a_cornice_stair_leans_INTO_the_wall_it_grows_from():
    """A stair's TALL side IS its `facing`, and our renderer draws both directions identically.

    So it is asserted rather than eyeballed. `_cornice` places an upside-down stair in the cell
    OUTSIDE the wall face; its tall side must point back at the wall, or the corbel juts the wrong
    way and every overhang in the land is a shelf with its lip on the outside.
    """
    from mcbuild.gen.canvas import Canvas
    c = Canvas(12, 6, 12)
    lot = pb._Lot(c, {"size": [12, 12]})
    lot.hollow(2, 2, 0, 9, 9, 3, pb.PRISM["field"])
    pb._cornice(lot, 2, 2, 9, 9, 4)
    checks = {(1, 5): "east", (10, 5): "west", (5, 1): "south", (5, 10): "north"}
    for (v, u), want in checks.items():
        state = c.palette[c.get(v, 4, u)].value
        assert state["Name"].value.endswith("_stairs")
        props = state["Properties"].value
        assert props["half"].value == "top"
        assert props["facing"].value == want, f"corbel at {(v, u)} faces {props['facing'].value}"


def test_a_skirt_stair_is_the_bottom_half_and_faces_the_same_way():
    from mcbuild.gen.canvas import Canvas
    c = Canvas(12, 6, 12)
    lot = pb._Lot(c, {"size": [12, 12]})
    lot.hollow(2, 2, 0, 9, 9, 3, pb.PRISM["field"])
    pb._skirt(lot, 2, 2, 9, 9, 0)
    props = c.palette[c.get(1, 0, 5)].value["Properties"].value
    assert props["half"].value == "bottom" and props["facing"].value == "east"


def test_a_parapet_is_actually_crenellated(built):
    """Merlon gaps are LEFT EMPTY by the loop that draws the parapet, never punched afterwards.

    Building a full ring and alternating merlons over it repaints cells that already exist: it
    alternates perfectly, changes nothing, and the crown ships as a plain drum. That shipped once
    on the void tower and nothing about the code looked wrong.
    """
    from mcbuild.gen.canvas import Canvas
    c = Canvas(20, 8, 20)
    lot = pb._Lot(c, {"size": [20, 20]})
    merlons = pb._parapet(lot, 2, 2, 17, 17, 1, every=3, tall=2)
    assert merlons > 0
    top = [c.get_name(v, 2, u).split(":")[-1] for v, u, _a, _b, _t in pb._perimeter(2, 2, 17, 17)]
    assert "air" in top, "the parapet has no gaps - it is a drum"
    assert any(n != "air" for n in top), "the parapet has no merlons"


def test_every_sign_hangs_on_a_wall_and_fits_the_sign(built):
    """A wall sign floating in air draws exactly like one on a wall in every render we have."""
    for stem, (_cfg_, canvas, model) in built.items():
        for (x, y, z), tile in canvas.tiles.items():
            state = canvas.palette[canvas.get(x, y, z)].value
            assert state["Name"].value.endswith("_wall_sign"), f"{stem}: text on a non-sign"
            facing = state["Properties"].value["facing"].value
            dv = {"east": 1, "west": -1}.get(facing, 0)
            du = {"south": 1, "north": -1}.get(facing, 0)
            assert canvas.solid(x - dv, y, z - du), f"{stem}: a sign hung on nothing at {(x, y, z)}"
            for line in tile["front"]:
                assert len(line) <= pb.SIGN_WIDTH + 12   # the JSON wrapper, not the text
        assert canvas.meta["signs"] >= 1, f"{stem}: nobody can be told what this building is"


def test_every_lantern_has_something_to_hang_from_or_stand_on(built):
    for stem, (_cfg_, canvas, model) in built.items():
        for v, u, y, name in _cells(model):
            if name != "soul_lantern":
                continue
            hanging = canvas.palette[canvas.get(v, y, u)].value["Properties"].value["hanging"].value
            other = canvas.solid(v, y + 1, u) if hanging == "true" else canvas.solid(v, y - 1, u)
            assert other, f"{stem}: a lantern on nothing at {(v, u, y)}"


# --------------------------------------------------------------------------- the mechanisms


def test_this_design_set_claims_no_mechanism_at_all(built):
    """PRISMWORKS_GENERATOR.md: a generator must not imply a circuit by placing hardware.

    Two finished casino games were cut rather than shipped as machines this repo could not judge
    by simulation. So there is no redstone in any of these six, and the day one of them grows a
    circuit this test fails and sends whoever added it to `mcbuild/circuit.py` first.
    """
    for stem, (_cfg_, _c, model) in built.items():
        assert not circuit.has_redstone(model), f"{stem}: redstone with no simulated contract"


def test_every_config_declares_an_enforced_fun_contract_and_typed_anchors():
    for stem in CONFIGS:
        cfg = _cfg(stem)
        fun = cfg.get("fun_contract") or {}
        assert fun.get("enforce") is True, f"{stem}: fun_contract is not enforced"
        assert fun.get("class") in {"experience", "recovery", "orientation", "route",
                                    "scenic_support"}
        assert fun.get("player_verbs"), f"{stem}: no player verbs"
        assert str(fun.get("outcome", "")).strip(), f"{stem}: no visible outcome"
        if fun["class"] == "experience":
            for field in ("reset", "service_access", "bypass"):
                assert str(fun.get(field, "")).strip(), f"{stem}: experience missing {field}"
        else:
            assert str(fun.get("spatial_job", "")).strip()
        names = {a["name"] for a in cfg["anchors"]}
        if "ride" in cfg.get("roles", []):
            assert {"queue_entry", "boarding", "ride_exit", "service_access"} <= names, stem
        assert cfg.get("origin_lock") is False, f"{stem}: origin_lock must be off"
        assert cfg["finish"]["verify_against"].endswith("Park Complete.litematic")


def test_the_generator_records_what_it_cannot_certify(built):
    for stem, (_cfg_, canvas, _m) in built.items():
        assert canvas.meta["requires_in_game"], f"{stem}: claims everything is proven"
        assert canvas.meta["contract"]


# --------------------------------------------------------------------------- the headline


def test_the_prism_ascent_is_columnar_and_planar(built):
    """The one build in this set whose SHAPE is the deliverable.

    Columnar: the core's width never grows with height. Planar: every fin is exactly three cells
    thick across its own blade and reaches at least eight out at the bottom. Those two properties
    are what this repo has measured as the difference between a shape voxels render natively and
    one they render worst - and a tower that quietly grows a belly fails here rather than in a
    render nobody looked at.
    """
    _cfg_, canvas, model = built["pf_prismworks_prism_ascent"]
    meta = canvas.meta
    assert meta["top"] == 84, "the height is a decision measured against the Sky Lift's 74"
    sol = model.solid()

    def extent(y):
        if not sol[y].any():
            return 0
        zs, xs = np.nonzero(sol[y])
        return max(int(xs.max() - xs.min()) + 1, int(zs.max() - zs.min()) + 1)

    # y15 is the first course clear of the podium's own parapet lamps; above it there is nothing
    # but the tower, its fins and its crown.
    widths = [extent(y) for y in range(15, 84)]
    assert widths[0] == max(widths), "the tower is widest somewhere other than its own base"
    # No belly. The only permitted swell is the two cells a setback corbel or a fin's leading
    # light projects; anything more is the shape this medium renders worst.
    for y, (a, b) in enumerate(zip(widths, widths[1:]), start=15):
        assert b <= a + 2, f"the tower swells at y{y + 1}: {a} -> {b}"
    assert widths[-1] <= widths[0] // 2, "the crown is not a crown, it is a second storey"

    # PLANAR: a fin is a blade three cells thick, not a buttress. Sampled at two courses clear of
    # every projecting ring, on the +V face, beyond the core's own footprint.
    cv, cu = 46, 36
    for y, core_r in ((20, 6), (40, 5)):
        zs, xs = np.nonzero(sol[y])
        us = {int(z) for z, x in zip(zs, xs) if x > cv + core_r}
        assert us == {cu - 1, cu, cu + 1}, f"the +V fin at y{y} is {sorted(us)}, not a 3-cell blade"


@pytest.mark.skip(reason="THE PRISM ASCENT IS RETIRED, and this pins a contract only a placed "
                        "module can have. Prismworks v1 was replaced by the Prism Well and the "
                        "Ascent left `park_place.EXTRAS_READY` with the Foundry Gate, the Array, "
                        "the Resonance Vault and the Forge Deck - so `Park Complete` no longer "
                        "contains it, and what it is being asked to out-top is `PF Crown Descent`, "
                        "which carries the column to Y300 and is the land's headline now. It also "
                        "adds a hard-coded 190 for the composite's origin, which is 94 - nobody's "
                        "constant, as `test_park_entrance.py` records after the same 96-course "
                        "error. Delete this with the design, or re-point it at the Well.")
def test_the_ascent_tops_out_over_the_tallest_thing_already_in_the_park(built):
    """It is a dominant, not a competitor - and the number it has to beat is measured, not recalled.

    THE MEASUREMENT MUST EXCLUDE THE ASCENT'S OWN LOT. This read `Park Complete` whole, and
    `Park Complete` is a composite: the day the Ascent was first generated and merged into it,
    the "tallest thing already in the park" became THE ASCENT, `mine > park_top` became
    `286 > 286`, and the test failed identically whatever anybody did to the design. That is the
    snapshot trap this repo has now shipped four times, and the fix is the same each time - ask
    the question about the NEIGHBOURS, which means masking out the thing being judged.
    """
    if not os.path.exists(GROUND):
        pytest.skip("out/Park Complete.litematic is not on disk")
    park = schem.load(GROUND)
    sol = park.solid().copy()
    _cfg, canvas, model = built["pf_prismworks_prism_ascent"]
    (v0, u0), (dv, du) = _cfg["params"]["at"], _cfg["params"]["size"]
    sol[:, u0:u0 + du, v0:v0 + dv] = False          # the columns this design itself owns
    park_top = max(y for y in range(sol.shape[0]) if sol[y].any()) + 190
    mine = max(y for y, _z, _x in zip(*np.nonzero(model.solid()))) + canvas.world_origin[1]
    assert mine > park_top, f"the headline ({mine}) is not the tallest thing in the park ({park_top})"
    assert mine - park_top <= 20, "a dominant, not a spike nothing else can answer"


def test_the_gate_passage_is_walk_through_and_on_the_spur(built):
    """A gate's job is a hole, and the hole has to be on the path the ground layer already drew.

    `Park Ways` lands the Foundry Gate spur at U447-449; the passage is centred on U448 and runs
    clean through the block, so the composition is read from the spine straight down it.
    """
    cfg, canvas, model = built["pf_prismworks_foundry_gate"]
    u0 = cfg["params"]["at"][1]
    door = 448 - u0
    assert canvas.meta["passage_width"] == 7
    for v in range(0, 22):
        for y in range(1, 8):
            assert not canvas.solid(v, y, door), f"the passage is blocked at v{v} y{y}"
    # ...and its own reveal is not: a doorway with no jamb is a gap in a wall. The block stands
    # one column in from the lot line so its trim has somewhere to go, so the jamb is at v1.
    assert canvas.solid(1, 3, door - 4) and canvas.solid(1, 3, door + 4)
    # ...and the threshold reaches the lot line, where the ground layer's spur stops
    assert canvas.solid(0, 0, door)


def test_the_forge_deck_is_a_raised_walk_the_whole_length_of_its_lot(built):
    """The exit band is programmed for observation; a deck you cannot walk is a plinth."""
    cfg, canvas, model = built["pf_prismworks_forge_deck"]
    deck_y = canvas.meta["deck_y"]
    du = cfg["params"]["size"][1]
    walk = [u for u in range(1, du - 1)
            if canvas.solid(11, deck_y, u) and not canvas.solid(11, deck_y + 1, u)]
    assert len(walk) >= du - 6, f"the deck is only walkable for {len(walk)} of {du}"


def test_the_service_gallery_stays_out_of_the_protected_rim(built):
    """13 deep, not the declared 18: V170 is the rim edge and V171-199 carries nothing at all."""
    cfg, canvas, model = built["pf_prismworks_service_gallery"]
    v0, dv = cfg["params"]["at"][0], cfg["params"]["size"][0]
    assert v0 + dv - 1 <= 169, "this shed reaches the rim edge"

# --------------------------------------------------------------------------- the machine land

#: THE MATERIALS THAT SAY MACHINE. Jack: "we still need to properly design the prism area", and
#: he could not tell it WAS Prismworks. Rendered from eight bearings the first build of these six
#: was correct architecture with no identity: every material in the land sat between luminance 38
#: and 73 and every one of them was grey, so the eye read one hue and called it stone.
PLANT = ("copper",)                     # the warm metal, and the land's only hue
SIGNAL = ("cyan_wool", "light_blue_wool", "froglight", "lightning_rod")


def _names_of(model):
    names = [n.split(":")[-1].split("[")[0] for n in model.names]
    out = {}
    ys, zs, xs = np.nonzero(model.ids)
    for y, z, x in zip(ys, zs, xs):
        out[(int(x), int(z), int(y))] = names[model.ids[y, z, x]]
    return out


@pytest.mark.parametrize("stem", CONFIGS)
def test_every_building_wears_the_land_s_plant_metal(built, stem):
    """ONE COPPER BAND PER BUILDING, AT THE CORNICE, AND THAT IS THE LAND'S SIGNATURE.

    `waxed_copper_block` is L124 against a L45 field - 79 points AND a full hue flip - and it is
    CHEAP here where plain `copper_block` is expensive, which is not something to remember but
    something `palette.tier` was asked. It is confined to a cornice, a setback collar and a
    gantry: a warm metal used as a wall would turn a cold land warm, which is the opposite
    failure and just as bad.
    """
    _cfg, _c, model = built[stem]
    got = set(_names_of(model).values())
    assert any(any(t in n for t in PLANT) for n in got), \
        f"{stem} carries no plant metal at all - it is six greys, which reads as one"


@pytest.mark.parametrize("stem", CONFIGS)
def test_the_plant_metal_is_a_line_and_never_a_wall(built, stem):
    """A cornice band is a line. If copper ever becomes a field the land stops being deepslate,
    so the ceiling is stated here rather than left to whoever adds the next building."""
    _cfg, _c, model = built[stem]
    named = _names_of(model)
    copper = sum(1 for n in named.values() if any(t in n for t in PLANT))
    assert copper / max(1, len(named)) <= 0.12, \
        f"{stem}: {100 * copper / len(named):.1f}% copper - that is cladding, not a band"


def test_the_plant_metal_is_cheap_available_and_has_a_matching_trim_family():
    """Asked of the registry, never of a memory: `copper_block` is EXPENSIVE on this economy and
    `waxed_copper_block` is cheap, which is exactly the sort of thing this repo has got wrong by
    reaching for the obvious name."""
    for key in ("plant", "pstair", "pslab"):
        n = pb.PRISM[key]
        assert blocks.available(n), n
        assert blocks.spendable(n), n
        assert palette.tier(n) != "expensive", n
    r, g, b = blocks.color(pb.PRISM["plant"], "side")
    assert r > b + 60, "the plant metal has to be a real hue against a grey land"


@pytest.mark.parametrize("stem", CONFIGS)
def test_the_signal_is_a_SEQUENCE_and_not_a_sparkle(built, stem):
    """PRECISION AND SEQUENCE IS THE LAND'S BRIEF, and what it shipped was 388 cyan cells
    scattered through 14,664 - which at any distance is speckle on a dark wall.

    The measure of a sequence is that its signal cells form RUNS rather than singletons: a
    pilaster strip is a vertical ladder and a blade edge is a continuous line, so most signal
    cells have a signal cell directly above or below them. A scatter has almost none.
    """
    _cfg, _c, model = built[stem]
    named = _names_of(model)
    sig = {k for k, n in named.items() if any(t in n for t in SIGNAL)}
    assert len(sig) >= 35, f"{stem} has {len(sig)} signal cells - that is not a signal"
    # A RUN IN ANY DIRECTION, not just a vertical one. The first version of this measured only
    # vertical stacking and reported four correct buildings at 43-49%, because a shaft ring and
    # a crown band are HORIZONTAL sequences and count for nothing under that rule. What separates
    # a sequence from a sparkle is whether a signal cell has a signal NEIGHBOUR at all.
    runs = sum(1 for (v, u, y) in sig
               if any((v + a, u + b, y + c) in sig for a, b, c in
                      ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))))
    assert runs / len(sig) >= 0.65, (
        f"{stem}: only {100 * runs / len(sig):.0f}% of the signal is in runs - the rest is "
        "speckle, which is what 388 scattered cyan cells looked like at fifty blocks")


def test_a_pilaster_strip_climbs_from_pier_through_signal_to_a_lit_head():
    """The ladder is what makes the land COUNTABLE, and it is asserted on a bare box so the
    order cannot drift with whatever building happens to call it."""
    from mcbuild.gen.canvas import Canvas
    c = Canvas(11, 20, 11)
    L = pb._Lot(c, {"at": [0, 0], "size": [11, 11], "seed": 0})
    L.hollow(1, 1, 0, 9, 9, 0, pb.PRISM["pier"])
    for y in range(1, 13):
        L.ring(1, 1, 9, 9, y, pb.PRISM["field"])
    pb._pilasters(L, 1, 1, 9, 9, 1, 12, bay=4)
    col = [c.get_name(0, y, 5).split(":")[-1] for y in range(1, 13)]
    assert pb.PRISM["signal"] in col, col
    assert pb.PRISM["high"] in col, col
    assert pb.PRISM["glow"] in col, col
    # the head is the LAST thing on the strip, under the capital
    assert col.index(pb.PRISM["glow"]) > col.index(pb.PRISM["signal"]), col


@pytest.mark.parametrize("stem", ["pf_prismworks_foundry_gate", "pf_prismworks_prism_array",
                                  "pf_prismworks_resonance_vault"])
def test_the_parapets_carry_an_instrument_array(built, stem):
    """A machine land has instruments where a fairground has flags, and a lightning rod is one
    block: white, on a rhythm, on top of a merlon that is really there."""
    _cfg, _c, model = built[stem]
    named = _names_of(model)
    rods = [k for k, n in named.items() if n == pb.PRISM["mast"]]
    assert len(rods) >= 4, f"{stem} has {len(rods)} instruments on its parapet"
    for (v, u, y) in rods:
        assert (v, u, y - 1) in named, f"{stem}: an instrument at {(v, u, y)} floats"


def test_the_ascent_s_blade_edges_are_ONE_CONTINUOUS_LINE_OF_LIGHT(built):
    """The single biggest thing that tells this tower from a dark spire.

    The leading edge of each fin was `high` every EIGHTH course and `pier` between, which at
    fifty blocks is speckle - the same failure eight retired mammal coats had. It is continuous
    now, with a `glow` every eight so a guest can count the stages.
    """
    _cfg, _c, model = built["pf_prismworks_prism_ascent"]
    named = _names_of(model)
    bright = {pb.PRISM["high"], pb.PRISM["glow"]}
    cv, cu = 46, 36
    # the +V blade's own tip column, over the courses the fin actually spans
    runs = 0
    for y in range(10, 55):
        col = [(v, cu, y) for v in range(cv + 7, cv + 20)]
        if any(named.get(k) in bright for k in col):
            runs += 1
    assert runs >= 40, f"the blade edge is lit on only {runs} of 45 courses - that is a sparkle"
