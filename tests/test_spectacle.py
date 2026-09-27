"""The show, against its own recorded contracts.

A firework battery is the worst possible place to discover that a circuit does nothing: it
audits clean, it costs what it should, it renders correctly, and the only place the failure
shows is the sky at nine o'clock. Every assertion about the mechanism here is made BY
SIMULATION through `mcbuild.circuit`, and every assertion about the buildings is made against
the numbers the generator records on its own sidecar - so a build whose promise changes has to
change its test in the same commit.

**A TEST WHOSE BOUND IS LOOSER THAN THE BUG PASSES VACUOUSLY.** `circuits.pulse` shipped as a
bare repeater for months because its test asserted the output was high for "fewer than twenty of
twenty ticks", which a permanent delay satisfies as easily as a pulse. So the firework tests
assert the shape of the behaviour - equal counts, strictly increasing launch order, nothing at
all at rest, nothing at all after the lever goes back - rather than "something happened".
"""
from __future__ import annotations

import numpy as np
import pytest

from mcbuild import audit, blocks, circuit, palette
from mcbuild.gen import GENERATORS, spectacle

KINDS = ("fireworks", "bandstand_show", "foodcourt", "viewing", "leaderboard")
LANDS = ("midway", "frontier", "hollow")
FACINGS = ("east", "north", "west", "south")

_STEP = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}

# A sightline may pass through these: they are not blocks a head stops at, and a lantern hanging
# over a terrace is not a reason to say the show cannot be seen.
_SEE_THROUGH = {"lantern", "soul_lantern", "redstone_wire", "lever", "torch", "redstone_torch",
                "redstone_wall_torch"}


def build(kind, land="midway", facing="east", at=(0, 203, 0), **kw):
    return GENERATORS["spectacle"].build(
        {"at": list(at), "kind": kind, "land": land, "facing": facing, **kw})


def cells(c):
    """Every placed cell in WORLD coordinates, as {(x, y, z): (name, props)}.

    World coordinates because two designs are compared against each other here - the terrace's
    sightline runs into the firework pad - and two grids with different origins cannot be
    reasoned about together. That is the contract every sidecar in this repo carries.
    """
    m = c.to_model()
    ox, oy, oz = c.world_origin
    out = {}
    for y, z, x in np.argwhere(m.ids > 0):
        name = m.names[m.ids[y, z, x]].split(":")[-1].split("[")[0]
        out[(int(x) + ox, int(y) + oy, int(z) + oz)] = (name, m.props_at(int(x), int(y), int(z)))
    return out


def components(cs):
    """6-connected components. A swept feature whose cells are only DIAGONAL neighbours is not
    connected - the ear-tip lesson - so this is the connectivity the game itself uses."""
    seen, n = set(), 0
    for p in cs:
        if p in seen:
            continue
        n += 1
        stack = [p]
        seen.add(p)
        while stack:
            x, y, z = stack.pop()
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + d[0], y + d[1], z + d[2])
                if q in cs and q not in seen:
                    seen.add(q)
                    stack.append(q)
    return n


def sim_of(c):
    return circuit.Circuit.of(c.to_model(), c.world_origin)


# --------------------------------------------------------------------- the firework show

def test_at_rest_nothing_is_powered_and_nothing_fires():
    """THE FIRST HALF OF THE CONTRACT, and the half that shipped broken.

    A redstone torch is LIT on chunk load and takes two ticks to notice the kill switch holding
    its support down. Wired straight through, that transient is a real rising edge on every tap:
    the battery fired ONE SHOT with the lever off, every time the chunk loaded, and the only
    place that shows is the sky. Forty ticks is far longer than the transient, so this is the
    assertion that catches it coming back.
    """
    c = build("fireworks")
    s = sim_of(c)
    s.run(40)
    guns = [tuple(g) for g in c.meta["outputs"]]
    assert s.fired == {} or all(s.fired.get(g, 0) == 0 for g in guns), \
        f"a dispenser fired with the lever off: {dict(s.fired)}"
    assert not any(s.powered(g) for g in guns), "a dispenser is powered at rest"


def test_the_battery_fires_in_order_once_per_cycle():
    """THE SECOND HALF: a display, not a bang and not a machine gun.

    Three separate properties, because any one of them alone passes for the wrong reason:

      * every dispenser fires, or the far end of the battery is wired to nothing;
      * they fire the SAME number of times (to within the phase lag at the window's edge), or
        the delay line is dying somewhere along its length;
      * and the launch order is STRICTLY INCREASING along the battery, which is the only thing
        that distinguishes a sequence from all of them going off together.
    """
    c = build("fireworks")
    s = sim_of(c)
    guns = [tuple(g) for g in c.meta["outputs"]]
    s.set(tuple(c.meta["inputs"][0]), True)

    first = {}
    ticks = 400
    for t in range(ticks):
        s.step()
        for g in guns:
            if g not in first and s.fired.get(g, 0):
                first[g] = t

    counts = [s.fired.get(g, 0) for g in guns]
    assert min(counts) > 1, f"a dispenser barely fired: {counts}"
    assert max(counts) - min(counts) <= 1, f"the line dies partway along: {counts}"
    assert len(first) == len(guns), "a dispenser never fired at all"
    order = [first[g] for g in guns]
    assert order == sorted(order) and len(set(order)) == len(order), \
        f"the battery is not a sequence: {order}"
    # ...and it is a DISPLAY, not a machine gun. A dispenser firing every tick would empty 576
    # rockets in under a minute, which is this design's version of the house losing by accident.
    assert max(counts) < ticks // 8, f"far too fast to be a show: {counts}"


def test_the_sequence_fits_inside_the_cycle():
    """MEASURED, NOT TAKEN FROM THE ARITHMETIC IN THE GENERATOR.

    If the cascade takes longer than a cycle, shot 0 of the next wave overtakes the last shot of
    this one and the sky reads as noise. The clamp in `_fireworks` uses a conservative model of
    the cycle; this measures the real thing off the trace and checks the model was not optimistic.
    """
    c = build("fireworks")
    s = sim_of(c)
    guns = [tuple(g) for g in c.meta["outputs"]]
    s.set(tuple(c.meta["inputs"][0]), True)
    hits = []
    for t in range(400):
        s.step()
        if s.fired.get(guns[0], 0) > len(hits):
            hits.append(t)
    assert len(hits) >= 3, "the clock is not running"
    gaps = [b - a for a, b in zip(hits, hits[1:])]
    measured = sum(gaps) / len(gaps)
    assert max(gaps) - min(gaps) <= 1, f"the clock is not periodic: {gaps}"
    assert c.meta["span_ticks"] < measured, \
        f"the cascade ({c.meta['span_ticks']}) outruns the cycle ({measured})"


def test_the_lever_actually_stops_it():
    """A SHOW YOU CANNOT SWITCH OFF IS A LEAK. Not "fires less"; fires NOT AT ALL.

    Settle first, then snapshot, then run twice as long again: an edge already travelling down
    the delay line when the lever moves is allowed to finish, and nothing after that is.
    """
    c = build("fireworks")
    s = sim_of(c)
    lever = tuple(c.meta["inputs"][0])
    guns = [tuple(g) for g in c.meta["outputs"]]
    s.set(lever, True)
    s.run(200)
    assert sum(s.fired.get(g, 0) for g in guns) > 0, "it never started"

    s.set(lever, False)
    s.run(40)                                   # let anything in flight land
    snap = {g: s.fired.get(g, 0) for g in guns}
    s.run(120)
    assert {g: s.fired.get(g, 0) for g in guns} == snap, "it kept firing after the lever went back"


def test_it_starts_again_after_being_stopped():
    """A switch is not a fuse. Off then on has to give the show back."""
    c = build("fireworks")
    s = sim_of(c)
    lever = tuple(c.meta["inputs"][0])
    gun = tuple(c.meta["outputs"][0])
    s.set(lever, True)
    s.run(120)
    s.set(lever, False)
    s.run(60)
    before = s.fired.get(gun, 0)
    s.set(lever, True)
    s.run(200)
    assert s.fired.get(gun, 0) > before


def test_the_kill_switch_is_wired_to_the_clock_and_not_to_the_output():
    """WHY "AT REST" MEANS ANYTHING. Gating the output leaves a clock running behind a shut gate,
    and "nothing is powered" becomes a fact about where you looked. The lever holds the clock's
    own SUPPORT down, so with it off the support is powered and every wire downstream is dark."""
    c = build("fireworks")
    s = sim_of(c)
    sup = tuple(c.meta["clock_support"])
    tap = tuple(c.meta["clock_tap"])
    assert blocks.is_full_cube(s.name(sup)), "the clock's support is not a solid block"
    assert s.name(tap) == "redstone_wire"
    s.run(40)
    assert s.powered(sup), "the kill switch is not holding the clock down at rest"
    assert not s.powered(tap), "the clock loop is live with the lever off"
    s.set(tuple(c.meta["inputs"][0]), True)
    s.run(40)
    assert s.powered(tap), "the lever does not release the clock"


def test_the_battery_does_not_depend_on_quasi_connectivity():
    """A dispenser also fires from the block ABOVE it, even when that block is air - which is
    exactly the cell a rocket has to leave through. A battery that worked only by QC would be a
    battery whose muzzle you may never cover, and this build must not be one: it fires the same
    with QC modelled and with it switched off."""
    for qc in (True, False):
        c = build("fireworks")
        m = c.to_model()
        s = circuit.Circuit.of(m, c.world_origin)
        s.qc = qc
        s.set(tuple(c.meta["inputs"][0]), True)
        s.run(200)
        assert all(s.fired.get(tuple(g), 0) > 0 for g in c.meta["outputs"]), f"qc={qc}"


def test_the_muzzles_are_open_to_the_sky():
    """A ROCKET THAT CANNOT LEAVE THE DISPENSER DETONATES AT THE DISPENSER. There is no roof over
    a launch pad, ever, and nothing in any facing or land may drift into the column."""
    for land in LANDS:
        for facing in FACINGS:
            c = build("fireworks", land, facing)
            cs = cells(c)
            for g in c.meta["muzzles"]:
                for h in range(1, c.meta["clearance"] + 1):
                    q = (g[0], g[1] + h, g[2])
                    assert q not in cs, f"{land}/{facing}: {cs.get(q)} over a muzzle at {q}"


def test_nothing_that_burns_touches_a_dispenser():
    for land in LANDS:
        for facing in FACINGS:
            c = build("fireworks", land, facing)
            cs = cells(c)
            for g in c.meta["muzzles"]:
                for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
                    q = (g[0] + d[0], g[1] + d[1], g[2] + d[2])
                    got = cs.get(q)
                    assert not (got and spectacle.flammable(got[0])), \
                        f"{land}/{facing}: {got} beside a dispenser"


def test_the_rocket_bill_is_stated():
    """The simulator has no entities, so it cannot check that a dispenser was loaded. The one
    thing it can do is say exactly what to put in - the casino's `stock` rule, and the difference
    between a show and a battery of empty tubes."""
    c = build("fireworks")
    stock = c.meta["stock"]
    assert stock and any("rocket" in str(v) for v in stock.values())
    assert str(c.meta["battery"] * 576) in " ".join(str(v) for v in stock.values())


# --------------------------------------------------------------------- the sound question

def test_the_instrument_is_the_one_this_economy_can_afford():
    """MEASURED, NOT ASSUMED. The brief's guess was that a jukebox is the cheap alternative to
    note blocks; `palette.tier` says both are expensive here and a bell is not. If the economy
    ever changes, this fails and the choice gets re-made deliberately rather than inherited."""
    assert palette.tier("note_block") == "expensive"
    assert palette.tier("jukebox") == "expensive"
    assert palette.tier("bell") == "cheap"
    c = build("bandstand_show")
    assert c.meta["bells"] >= 1, "the bandstand has no instrument"
    assert c.meta["budget"] == {}, "the default build spends nothing expensive"


def test_the_expensive_extras_are_counted_and_never_default_on():
    """A plan that says "a bandstand" rather than "5 note blocks you do not own" is not a plan."""
    assert spectacle.SPECTACLE["notes"] == 0
    assert spectacle.SPECTACLE["jukebox"] is False
    c = build("bandstand_show", notes=5, jukebox=True)
    assert c.meta["budget"].get("note_block") == 5
    assert c.meta["budget"].get("jukebox") == 1
    assert c.meta["stock"], "a jukebox with no disc bill is an ornament"


def test_a_note_block_can_actually_sound():
    """A note block only plays with AIR ABOVE IT. Built under the roof it is a silent decoration
    that every check in this pipeline passes."""
    c = build("bandstand_show", notes=6)
    cs = cells(c)
    ranks = [p for p, (n, _) in cs.items() if n == "note_block"]
    assert ranks
    for p in ranks:
        assert (p[0], p[1] + 1, p[2]) not in cs, f"a note block is capped at {p}"


def test_the_bell_hangs_from_a_real_block():
    """Anything CLINGING needs a full block to cling to, tested against what is actually built -
    the belly's three vines hung off wall railings because "solid" meant "not air"."""
    c = build("bandstand_show")
    cs = cells(c)
    bells = [(p, pr) for p, (n, pr) in cs.items() if n == "bell"]
    assert bells
    for p, pr in bells:
        assert pr.get("attachment") == "ceiling"
        above = cs.get((p[0], p[1] + 1, p[2]))
        assert above and blocks.is_full_cube(above[0]), f"a bell hangs from {above} at {p}"


# --------------------------------------------------------------------- the terrace

def test_the_front_row_can_see_the_launch_point():
    """THE ONLY ASSERTION A GRANDSTAND ACTUALLY NEEDS, and it is worthless made against one
    design's own cells: a sightline is about the thing being looked AT. Both designs are
    composited in world coordinates and the segment is walked through the union.
    """
    fw = build("fireworks", at=(0, 203, 0), facing="east")
    launch = tuple(fw.meta["launch"])
    vw = build("viewing", at=(25, 203, -20), facing="west", aim=list(launch))
    assert vw.meta["sightline_to"] == list(launch)
    assert not vw.meta["unverified"], "an aim was given, so the sightline must be checked"

    world = {}
    world.update({p: v[0] for p, v in cells(fw).items()})
    world.update({p: v[0] for p, v in cells(vw).items()})

    assert vw.meta["front_row"], "no front row to look from"
    for eye in vw.meta["front_row"]:
        blocked = _blockers(world, tuple(eye), launch)
        assert not blocked, f"the front row is looking at {blocked[:3]}"


def test_every_row_can_see_it_not_only_the_front_one():
    """A terrace whose back rows look at the row in front is a terrace with one usable row."""
    fw = build("fireworks", at=(0, 203, 0), facing="east")
    launch = tuple(fw.meta["launch"])
    vw = build("viewing", at=(25, 203, -20), facing="west", aim=list(launch), tiers=4)
    world = {}
    world.update({p: v[0] for p, v in cells(fw).items()})
    world.update({p: v[0] for p, v in cells(vw).items()})
    for eye in vw.meta["eyes"]:
        assert not _blockers(world, tuple(eye), launch), f"row at {eye} cannot see the show"


def test_the_pads_own_stand_can_see_its_own_show():
    """The fireworks kind carries two rows of its own, for the casual watcher who did not walk
    round to the grandstand. They are on the far side of the safety rail and they must clear it,
    the control station and the dispensers - which is the same measurement, made inside one
    design instead of across two, so it holds in all four facings."""
    for facing in FACINGS:
        c = build("fireworks", facing=facing)
        world = {p: v[0] for p, v in cells(c).items()}
        launch = tuple(c.meta["launch"])
        assert c.meta["seat_cells"], "the stand has no seats"
        for seat in c.meta["seat_cells"]:
            eye = (seat[0], seat[1] + 1, seat[2])
            assert not _blockers(world, eye, launch), f"{facing}: seat at {seat} cannot see it"


def test_a_terrace_with_no_aim_says_so_rather_than_passing_quietly():
    """A check that was never made must not read as a check that passed. This repo's most
    repeated failure is a thing that does nothing, quietly."""
    vw = build("viewing")
    assert vw.meta["sightline_to"] is None
    assert any("UNCHECKED" in u for u in vw.meta["unverified"])


def _blockers(world, a, b):
    ax, ay, az = (v + 0.5 for v in a)
    bx, by, bz = (v + 0.5 for v in b)
    steps = int(max(abs(bx - ax), abs(by - ay), abs(bz - az)) * 4) + 1
    hits = []
    for s in range(1, steps):
        t = s / steps
        p = (int(np.floor(ax + (bx - ax) * t)),
             int(np.floor(ay + (by - ay) * t)),
             int(np.floor(az + (bz - az) * t)))
        if p in (tuple(a), tuple(b)):
            continue
        name = world.get(p)
        if name and name not in _SEE_THROUGH:
            hits.append((p, name))
    return hits


def test_the_rail_is_below_eye_level():
    """A rail at seat height is a fence across the view. The front row's eyes are one course
    above its seat and the rail is one course below THAT, which is what lets it exist at all."""
    c = build("viewing")
    cs = cells(c)
    rails = [p for p, (n, _) in cs.items() if n.endswith("_fence")]
    assert rails
    eye_y = {p[1] for p in c.meta["front_row"]}
    assert len(eye_y) == 1
    assert max(p[1] for p in rails) < min(eye_y)


# --------------------------------------------------------------------- the places people use

@pytest.mark.parametrize("kind", KINDS)
def test_every_serving_block_has_room_to_be_used(kind):
    """RULE 10, ASSERTED RATHER THAN COMMENTED. About three blocks of working room in front of
    anything a player opens, or you cannot stand, open it and walk past.

    A block with no facing - a composter, a bin - is used from ABOVE, so what it needs is the
    cell over it, and asking it the wrong question would pass every one of them.
    """
    for land in LANDS:
        for facing in FACINGS:
            c = build(kind, land, facing)
            cs = cells(c)
            for s in c.meta.get("service", []):
                pos = tuple(s["pos"])
                if s["facing"]:
                    dx, dz = _STEP[s["facing"]]
                    for step in range(1, spectacle._WORK_ROOM + 1):
                        for hh in (0, 1):
                            q = (pos[0] + dx * step, pos[1] + hh, pos[2] + dz * step)
                            assert q not in cs, \
                                f"{kind}/{land}/{facing}: {s['use']} is walled in at {q}"
                else:
                    assert (pos[0], pos[1] + 1, pos[2]) not in cs, \
                        f"{kind}: {s['use']} cannot be reached from above"


def test_the_food_court_is_actually_served_and_seated():
    """It is the most-used building in a real park, and "some barrels in a shed" is what it looks
    like when the numbers are not stated."""
    c = build("foodcourt")
    m = c.meta
    assert m["stalls"] >= 3 and m["tables"] >= 2 and m["seats"] >= 8
    uses = {s["use"] for s in m["service"]}
    assert {"barrel", "smoker", "composter"} <= uses, uses
    cs = cells(c)
    assert any(n == "lantern" or n == "soul_lantern" for (n, _) in cs.values()), "no light"


def test_the_leaderboard_records_the_gap_it_cannot_fill():
    """`blocks.exists("item_frame")` is False - it is an entity - so the wall the brief asks for
    cannot be built as described. A feature quietly dropped is this repo's oldest failure; it is
    written into `unverified` instead, and the check is on the FACT rather than on the wording."""
    assert not blocks.exists("item_frame")
    assert not blocks.exists("armor_stand")
    c = build("leaderboard")
    assert c.meta["boards"] >= 2
    assert any("item frame" in u for u in c.meta["unverified"])
    assert all(s["use"] == "lectern" for s in c.meta["service"])


@pytest.mark.parametrize("kind", KINDS)
def test_seats_can_be_sat_on(kind):
    """A seat with a block on its head is a step. Measured over the SEATS the build records, not
    over every stair in it - a cornice is a stair with a roof on it, by design, and asserting
    headroom over all of them would have failed a correct building."""
    c = build(kind)
    cs = cells(c)
    for p in c.meta.get("seat_cells", []):
        assert cs[tuple(p)][0].endswith("_stairs"), f"{kind}: {p} is not a seat"
        assert (p[0], p[1] + 1, p[2]) not in cs, f"{kind}: no headroom over the seat at {p}"


# --------------------------------------------------------------------- every kind, every land

@pytest.mark.parametrize("kind", KINDS)
def test_one_piece_in_every_land_and_every_facing(kind):
    """A structure in two pieces is one structure and a shape floating beside it. The plot is
    VOID, so nothing here is held up by terrain and the pad is the only thing joining it."""
    for land in LANDS:
        for facing in FACINGS:
            c = build(kind, land, facing)
            n = components(cells(c))
            assert n == 1, f"{kind}/{land}/{facing} is in {n} pieces"


@pytest.mark.parametrize("kind", KINDS)
def test_legal_affordable_and_placeable(kind):
    for land in LANDS:
        c = build(kind, land)
        r = audit.audit(c.to_model())
        assert not r.problems, f"{kind}/{land}: {[str(x) for x in r.problems[:4]]}"
        assert r.tiers.get("expensive", 0) == 0, f"{kind}/{land}: {dict(r.tiers)}"
        for name in r.bom:
            short = name.split(":")[-1].split("[")[0]
            assert blocks.exists(short), f"{kind}: {short} is not a block"
            assert blocks.spendable(short), f"{kind}: {short} is CURRENCY on this server"


@pytest.mark.parametrize("kind", KINDS)
def test_no_ignition_source_anywhere(kind):
    """Fire spreads from `fire`, `soul_fire` and lava, and TNT does the rest. None of them is
    placed by this module in any land - which is a stronger guarantee than a clearance rule, and
    it is why the campfire in the food court is safe."""
    for land in LANDS:
        cs = cells(build(kind, land))
        for p, (n, _) in cs.items():
            assert n not in spectacle._IGNITES, f"{kind}/{land}: {n} at {p}"


def test_a_cook_fire_keeps_a_ring_clear_of_anything_that_burns():
    for land in LANDS:
        c = build("foodcourt", land)
        cs = cells(c)
        for p, (n, _) in cs.items():
            if n not in ("campfire", "soul_campfire"):
                continue
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                got = cs.get((p[0] + d[0], p[1] + d[1], p[2] + d[2]))
                assert not (got and spectacle.flammable(got[0])), f"{land}: {got} beside a fire"


def test_the_flammable_test_is_not_vacuous():
    """A safety predicate that answers False to everything passes every safety test. Both
    directions are pinned so the rule cannot be softened into a no-op."""
    for n in ("oak_planks", "white_wool", "spruce_fence", "red_carpet", "oak_leaves", "bookshelf"):
        assert spectacle.flammable(n), n
    for n in ("stone", "stone_bricks", "cobblestone", "deepslate_bricks", "dispenser",
              "polished_blackstone_bricks", "lantern", "barrel"):
        assert not spectacle.flammable(n), n


@pytest.mark.parametrize("kind", KINDS)
def test_every_structure_says_what_it_is(kind):
    """A sign is the only thing in this park that tells a visitor there is a show at nine. And a
    wall sign needs a FULL BLOCK behind it: `park._sign` asks only whether the cell behind is
    occupied, which passed a nameplate hung on a lantern and one hung on a cornice stair - both
    of which the game would simply refuse to place. A line over fifteen characters clips
    mid-word, and the only place that shows is a screenshot of the finished build.
    """
    for land in LANDS:
        for facing in FACINGS:
            c = build(kind, land, facing)
            cs = cells(c)
            signs = [(p, pr) for p, (n, pr) in cs.items() if n.endswith("_wall_sign")]
            assert signs, f"{kind}/{land}/{facing} has no sign at all"
            assert len(signs) == c.meta["signs"], "the build miscounted its own signs"
            for p, pr in signs:
                dx, dz = _STEP[pr["facing"]]
                behind = cs.get((p[0] - dx, p[1], p[2] - dz))
                assert behind and blocks.is_full_cube(behind[0]), \
                    f"{kind}/{land}/{facing}: sign at {p} hangs on {behind}"
            model = c.to_model()
            for line in _sign_lines(model):
                assert len(line) <= 15, f"{kind}: sign line {line!r} clips"


def _sign_lines(model):
    """Every line of text the model carries, read out of the tile entities rather than out of the
    generator - what ships is what is in the file."""
    import json
    out = []
    for te in getattr(model, "tile_entities", None) or []:
        body = te.value
        for side in ("front_text", "back_text"):
            block = body.get(side)
            if block is None:
                continue
            for msg in block.value.get("messages").value:
                try:
                    txt = json.loads(msg.value)
                except Exception:
                    txt = msg.value
                if isinstance(txt, dict):
                    txt = txt.get("text", "")
                out.append(str(txt))
    return out


@pytest.mark.parametrize("kind", KINDS)
def test_the_reported_footprint_is_what_was_actually_built(kind):
    """A planner packs what it is TOLD. `width`/`depth` name the structure; the pad margin and
    the firework pad's own stand are ground nobody mentioned, and a bay booked from the nominal
    numbers is a bay two buildings share. It must also be the same whichever way the thing
    faces, or three quarters of a plan is sited against the wrong rectangle."""
    seen = set()
    for facing in FACINGS:
        c = build(kind, facing=facing)
        frontage, into = c.meta["footprint"]
        x, _y, z = c.to_model().shape_xyz
        want = (z, x) if facing in ("east", "west") else (x, z)
        assert (frontage, into) == want
        assert frontage >= c.meta["width"] and into >= c.meta["depth"]
        seen.add((frontage, into))
    assert len(seen) == 1, f"{kind}'s footprint moves with its facing: {seen}"


def test_the_service_list_cannot_grow_a_name_nothing_checks():
    """A fixture recorded under an unknown `use` reads as "no serving blocks here" rather than
    as an error, which is how a work-room rule stops being a rule."""
    with pytest.raises(ValueError):
        spectacle._serve([], spectacle._Frame({"at": [0, 0, 0], "facing": "east"}),
                         0, 0, 0, "anvil", "east")


def test_the_kinds_are_registered_and_reject_nonsense():
    assert GENERATORS["spectacle"] is spectacle
    assert set(spectacle.BUILDERS) == set(KINDS)
    for bad in ({"kind": "carousel"}, {"land": "seaside"}, {"facing": "up"}):
        with pytest.raises(ValueError):
            build(**{"kind": "fireworks", **bad})
    with pytest.raises(ValueError):
        GENERATORS["spectacle"].build({"kind": "fireworks"})
