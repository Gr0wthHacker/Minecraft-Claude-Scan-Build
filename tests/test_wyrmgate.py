"""THE WYRM GATE - the skull straddling the rim railway, and the contracts that make that safe.

Jack: *"are we able to place the skull so that the mouth 'opens' around the railway, the back of
the skeleton is towards the void and the mouth gap is where the railway passes through sideways"*.

Everything here is a property nothing else in the pipeline can see. The audit reports a legal,
supported, affordable build whether the railway still runs under it or not; the renderer draws a
skull facing the park exactly like one facing the void; and `overlap 0` against the CAPTURE says
nothing about the two walks this design crosses, because a promenade and an arcade are made of
air. So: the facing is measured, the corridor is measured course by course, and the walks are
flooded rather than looked at.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import blocks, palette, schem  # noqa: E402
from mcbuild.gen import asset, wyrmgate  # noqa: E402

CONFIG = ROOT / "configs" / "pf_wyrm_gate.yaml"
SOURCE = ROOT / "reference" / "bone_ruins_skull.litematic"
RAIL = ROOT / "out" / "Park Rail.litematic"

pytestmark = pytest.mark.skipif(not SOURCE.exists(), reason="the reference asset is not here")


@pytest.fixture(scope="module")
def params():
    """The SHIPPED config, with the generator's own defaults under it - which is what gets built.
    A test that read only the yaml would be testing half a parameter set."""
    return {**wyrmgate.GATE, **yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["params"]}


@pytest.fixture(scope="module")
def gate(params):
    return wyrmgate.build(dict(params))


@pytest.fixture(scope="module")
def cells(gate, params):
    """{(V, Y, U): block name} in WORLD coordinates - which is the only frame these rules live in."""
    at_v, at_u = (int(v) for v in params["at"])
    ay = int(params["anchor"][1])
    names = [e.value["Name"].value.split(":")[-1] for e in gate.palette]
    out = {}
    for y, u, v in zip(*(gate.ids > 0).nonzero()):
        out[(at_v + int(v), ay + int(y), at_u + int(u))] = names[int(gate.ids[y, u, v])]
    return out


@pytest.fixture(scope="module")
def rail():
    if not RAIL.exists():
        pytest.skip("the railway artifact is not built here")
    m = schem.load(str(RAIL))
    return m


# --------------------------------------------------------------------------- the facing


def test_the_turn_puts_the_face_at_the_PARK_and_not_at_the_void():
    """THE ONE THING A PICTURE CANNOT CHECK, AND THE ONE THIS TEST GOT WRONG FIRST.

    v1 asserted that the CRANIUM starts at the model's low-V edge. That is true of `rotate: 90`
    and says NOTHING about which end of the cranium the face is on - and 90 is the turn that
    points the face at the void. Jack, on the build that shipped: *"the skull is oriented the
    wrong way, we can be looking at the back of a flat skull, it loses its meaning."*

    The measure is the EYE SOCKETS, which are cavities: along the socket courses and inside the
    socket's own two bands of the face's width, the model is empty on the side you look in from
    and solid where the nasal and the socket's back wall stand. So the shipped turn must leave
    that mass in the FAR half of the model's depth - the void half - with the openings pointed at
    the park. Our renderer draws a skull facing either way identically, which is why this is
    arithmetic and not a picture.
    """
    #: the two socket bands, in the model's own 54-wide face axis, off the elevation
    socket_u = list(range(9, 21)) + list(range(33, 45))
    def mass(rotate):
        band = (asset.build({"source": str(SOURCE), "rotate": rotate, "prune": 8}).ids > 0)[40:51]
        prof = [int(band[:, socket_u, v].sum()) for v in range(band.shape[2])]
        half = len(prof) // 2
        return sum(prof[:half]), sum(prof[half:])

    near, far = mass(270)
    assert far > near * 5, f"270 must leave the sockets' mass on the void side: {near} / {far}"
    other_near, other_far = mass(90)
    assert other_near > other_far * 5, f"90 is the turn that faces the void: {other_near} / {other_far}"


def test_the_config_uses_that_turn(params):
    assert int(params["rotate"]) == 270


# --------------------------------------------------------------------------- the railway


def test_not_one_cell_of_the_railway_is_taken(cells, rail, params):
    """The strongest property this design has, and it is a property of the CONSTRUCTION: the
    generator loads the railway and refuses every cell of it, so this cannot drift."""
    rv, ry, ru = (int(v) for v in params["rail_at"])
    sol = rail.solid()
    hit = [(V, Y, U) for (V, Y, U) in cells
           if 0 <= V - rv < sol.shape[2] and 0 <= Y - ry < sol.shape[0]
           and 0 <= U - ru < sol.shape[1] and sol[Y - ry, U - ru, V - rv]]
    assert not hit, f"{len(hit)} cells stand where the railway does, e.g. {hit[:5]}"


def test_the_girder_band_is_clear_ACROSS_THE_WHOLE_CORRIDOR(cells, params):
    """A litematic cannot say "and a train goes through here", so this is the rule that says it.

    Seven courses - the box girder, the rails, and the headroom a walker on the promenade and a
    rider in a cart each need - are refused everywhere between the two parapets. Refusing only
    the artifact's own cells would leave the promenade walled up and every check passing, because
    a promenade is made of air.
    """
    c0, c1 = (int(v) for v in params["corridor"])
    g0, g1 = (int(v) for v in params["girder"])
    arch = int(params.get("arch") or 0)
    bad = [(V, Y, U) for (V, Y, U) in cells
           if c0 <= V <= c1 and g0 <= Y <= g1 + wyrmgate._arch(V, c0, c1, arch)]
    assert not bad, f"{len(bad)} cells stand in the railway's own clearance, e.g. {bad[:5]}"


def test_the_cut_leaves_an_ARCH_and_not_a_sawn_plane(cells, params):
    """A rider's entire view of this design is the soffit over the track. Cut with a flat band it
    is a horizontal plane fifteen columns wide, which reads as a beam rather than as a jaw - so
    the clearance rises at the centre and the SOFFIT has to prove it: the middle of the corridor
    must be open higher than its edges wherever the skull roofs it at all."""
    c0, c1 = (int(v) for v in params["corridor"])
    g1 = int(params["girder"][1])
    mid = (c0 + c1) // 2
    roof = {}
    for (V, Y, U) in cells:
        if c0 <= V <= c1 and Y > g1:
            key = (V, U)
            roof[key] = min(roof.get(key, 10 ** 6), Y)
    edge = [y for (V, _u), y in roof.items() if V in (c0 + 1, c1 - 1)]
    centre = [y for (V, _u), y in roof.items() if abs(V - mid) <= 1]
    assert edge and centre, "the corridor is not roofed at all - there is no portal to measure"
    assert min(centre) > min(edge), \
        f"the soffit is flat: centre opens to {min(centre)}, edge to {min(edge)}"


def test_the_walks_this_design_CROSSES_are_bored_and_not_blocked(cells, params):
    """Two of them, and neither is optional: the line's own arcade at the plate, and `Park Ways`'
    rim boundary line in front of the viaduct."""
    for lane in params["keep_clear"]:
        bad = [(V, Y, U) for (V, Y, U) in cells
               if lane["v0"] <= V <= lane["v1"] and lane["y0"] <= Y <= lane["y1"]]
        assert not bad, f"{len(bad)} cells close the walk at {lane}, e.g. {bad[:4]}"


def test_the_footprint_is_clear_of_every_lamp_mast_and_station_on_the_line(cells, rail, params):
    """THE SITE IS A WINDOW, and it is 54 columns wide because the skull is. The line carries a
    mast every sixty columns and three stations; nothing of it stands above the deck inside this
    window, which is what lets the design roof the corridor at all."""
    rv, ry, ru = (int(v) for v in params["rail_at"])
    g1 = int(params["girder"][1])
    c0, c1 = (int(v) for v in params["corridor"])
    us = {U for (_v, _y, U) in cells}
    sol = rail.solid()
    tall = [(V, ry + y, U) for y in range(sol.shape[0]) for U in sorted(us)
            for V in range(c0, c1 + 1)
            if ry + y > g1 and 0 <= U - ru < sol.shape[1] and 0 <= V - rv < sol.shape[2]
            and sol[y, U - ru, V - rv]]
    assert not tall, f"the railway stands above the deck inside this window: {tall[:5]}"


# --------------------------------------------------------------------------- the mouth


def _roof(cells, rail_v: int, above: int) -> dict:
    """{U: the lowest cell of the skull standing over this rail}, per column of the crossing."""
    out: dict = {}
    for (V, Y, U) in cells:
        if V == rail_v and Y > above:
            out[U] = min(out.get(U, 10 ** 6), Y)
    return out


def test_BOTH_TRACKS_RUN_THROUGH_THE_MOUTH_and_not_past_it(cells, params):
    """The whole request, as a measurement.

    Every column of both tracks inside this footprint has skull OVER it: the train does not run
    beside a skull or under the front of one, it runs the length of the mouth. A design that
    merely stood next to the line, or reached across one end of it, would pass every other test
    in this file.
    """
    g1, deck = int(params["girder"][1]), int(params["deck"])
    us = sorted({U for (_v, _y, U) in cells})
    for rail_v in (174, 184):
        roof = _roof(cells, rail_v, g1)
        missing = [u for u in range(us[0] + 2, us[-1] - 1) if u not in roof]
        assert not missing, f"the track at V{rail_v} is open to the sky at u={missing[:8]}"
        assert min(roof.values()) >= deck + 4,             f"the roof over V{rail_v} comes down to {min(roof.values())}, deck is {deck}"


def test_THE_THROAT_OPENS_OUT_BEHIND_THE_JAW(cells, params):
    """A bore is not a mouth. **THE FAR TRACK IS THE ONE THAT MEASURES THIS**, and that follows
    from the geometry rather than from taste: the mouth is a RECESS about eleven columns deep and
    the railway's corridor is fifteen wide, so the near track at V174 runs in the open part of the
    recess - roofed seven to fourteen courses up, no portal at all - while the far track at V184
    passes through the jaw's own mass, ducks under the rami, and opens out between them.

    If those two numbers were ever the same, the design would be a fifty-four column bore through
    a lump, which is what the first placement built: sunk ten courses, the palate came down into
    the clearance and the mouth was gone.
    """
    g1 = int(params["girder"][1])
    roof = _roof(cells, 184, g1)
    us = sorted(roof)
    span = us[-1] - us[0]
    portal = min(roof[u] for u in us if u <= us[0] + span // 6 or u >= us[-1] - span // 6)
    throat = max(roof[u] for u in us if us[0] + span // 3 <= u <= us[-1] - span // 3)
    assert throat >= portal + 10, f"the throat ({throat}) barely clears the portal ({portal})"
    # ...and the near track never has a portal at all: it is in the open part of the recess
    near = _roof(cells, 174, g1)
    assert min(near.values()) >= int(params["deck"]) + 6,         f"the near track is roofed down to {min(near.values())} - it should be in open recess"


def test_the_garden_in_its_JAW_survives_UNDER_the_girder(cells, params):
    """THE ASSET IS NOT A BARE SKULL - its jaw holds a diorama with terraces, trees, a pond, steps
    and a golden shrine - and the six-course sink exists to put the whole of that UNDER the girder
    rather than through it. Any less and the deck slices its trees off.

    The pond and the grass are the tell, and the LEAVES ARE NOT: the eye sockets are planted too,
    so 418 of the 577 leaf cells in this build are up in the face and counting them all was a test
    measuring the wrong feature.
    """
    g0 = int(params["girder"][0])
    beds = {"water", "short_grass", "tall_grass"}
    garden = [(V, Y, U) for (V, Y, U), n in cells.items() if n in beds]
    assert len(garden) >= 30, "the garden is gone"
    high = [c for c in garden if c[1] >= g0]
    assert not high, f"{len(high)} garden cells stand inside the railway's clearance: {high[:4]}"
    leaves = [c for c in cells.items() if c[1].endswith("leaves") and c[0][1] < g0]
    assert len(leaves) > 150, f"only {len(leaves)} leaf cells are under the girder"


# --------------------------------------------------------------------------- the site


def test_the_back_is_toward_the_VOID_and_stays_on_the_plot(cells, params):
    """"The back of the skeleton is towards the void" is a placement, so it is measured as one: the
    mass behind the railway's corridor, the face in front of it, and nothing past the plot edge."""
    c0, c1 = (int(v) for v in params["corridor"])
    behind = sum(1 for (V, _y, _u) in cells if V > c1)
    front = sum(1 for (V, _y, _u) in cells if V < c0)
    # THE FACE IS THE DENSEST PART OF THIS ASSET, so "more mass behind than in front" is not the
    # measure and asserting it that way failed on a correct build: four columns of face outweigh
    # thirteen of hollow throat, 5,647 to 3,096. What "back to the void" means geometrically is
    # that the skull's DEPTH runs outward - the face stands clear of the corridor on the park side
    # and the mass reaches the rim behind it.
    assert front > 400, "the face must stand clear of the corridor, or the track reads as being " \
                        "in front of a skull rather than inside its mouth"
    assert behind > 1500, f"only {behind} cells stand behind the line - the back is not on the rim"
    assert max(V for V, _y, _u in cells) <= 199, "the design runs off the plot"
    assert min(Y for _v, Y, _u in cells) >= int(params["anchor"][1]), "it digs below the plate"


def test_NOTHING_FLOATS_and_the_body_is_one_piece(gate):
    """**EVERY PIECE STANDS ON THE PARK'S OWN PLATE**, which is the honest form of this rule here.

    The design is deliberately in three pieces and each of them is grounded: the skull and its
    forecourt are cut apart by the arcade lane bored under the viaduct - five columns wide and
    five courses tall, which is the passage the railway's own pier already leaves - and the lamps
    set into the bare rim are one cell each on the plate. Demanding one component would either
    force a bridge across the railway's own walk or force the fixtures off the ground they exist
    to light. What must never happen is a piece with nothing under it.
    """
    solid = gate.ids > 0
    nb = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    seen = np.zeros(solid.shape, bool)
    parts = []
    for start in map(tuple, np.argwhere(solid)):
        if seen[start]:
            continue
        stack, cells = [start], []
        seen[start] = True
        while stack:
            cur = stack.pop()
            cells.append(cur)
            for d in nb:
                q = (cur[0] + d[0], cur[1] + d[1], cur[2] + d[2])
                if all(0 <= q[i] < solid.shape[i] for i in range(3)) and solid[q] and not seen[q]:
                    seen[q] = True
                    stack.append(q)
        parts.append(cells)
    parts.sort(key=len, reverse=True)
    assert len(parts[0]) > 0.9 * int(solid.sum()),         f"the body is not one piece: {[len(p) for p in parts[:6]]}"
    floating = [len(p) for p in parts if min(cell[0] for cell in p) > 0]
    assert not floating, f"{len(floating)} pieces stand on nothing: {sorted(floating)[-6:]}"


def _fixtures_on_the_plate(gate) -> dict:
    """Every cell this design lays directly on the park's own plate, with nothing of its own under
    it. They are the lamps set into the ground the skull shades."""
    names = [e.value["Name"].value.split(":")[-1] for e in gate.palette]
    out = {}
    for u in range(gate.sz):
        for v in range(gate.sx):
            i = int(gate.ids[0, u, v])
            if i and not gate.solid(v, 1, u):
                out[(v, 0, u)] = names[i]
    return out


def test_the_booby_trap_in_the_garden_is_NOT_shipped(cells, gate):
    """The ruins are trapped: 77 TNT and eight pressure plates round the chest and the gold. A
    fine thing in somebody's own diorama, and not a thing to hang over a working railway."""
    assert not [c for c, n in cells.items() if n in ("tnt", "stone_pressure_plate")]
    assert gate.meta["dropped"].get("tnt") == 77, "the count is recorded, or nobody knows it went"


def test_every_block_is_cheap_or_ok_spendable_and_real(cells):
    """DIRT IS CURRENCY HERE and the asset is full of it; `asset.SAFE` swaps it for moss. This is
    the check that says the swap actually happened over the cells that SHIPPED."""
    bad = {n for n in set(cells.values()) if palette.tier(n) == "expensive"}
    assert not bad, f"expensive blocks: {sorted(bad)}"
    unspendable = {n for n in set(cells.values()) if not blocks.spendable(n)}
    assert not unspendable, f"currency on this server: {sorted(unspendable)}"
    unreal = {n for n in set(cells.values()) if not blocks.exists(n)}
    assert not unreal, f"not real blocks: {sorted(unreal)}"


def test_the_tunnel_and_the_ground_it_shades_are_LIT(gate, params):
    """A covered tunnel over live rails is a mob standing on the deck at night, and the rim behind
    the railway is the darkest ground in this part of the park - 460 standable cells at block
    light zero before this design existed. The lamps are IN the roof and IN the ground, never laid
    on the coat, so the count is the only thing a test can check here; the propagation itself is
    checked over the finished composite by hand and recorded in the config."""
    lamps = gate.meta["lamps"]
    assert lamps["roof"] >= 4, f"the mouth's roof carries {lamps['roof']} lamps over 54 columns"
    assert lamps["rim"] >= 8, f"the ground this design shades carries {lamps['rim']} lamps"
