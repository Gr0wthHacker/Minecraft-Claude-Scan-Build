"""Prismworks generators produce bounded, profile-safe physical play spaces.

WHAT THESE PIN, AND WHY EACH ONE EXISTS

The first Prismworks pass audited clean at 5,988 blocks for a landmark budgeted at 32,000-40,000,
and nothing in the suite noticed - because every check this repo had asks whether a block is
legal, supported, affordable and connected, and a thin build is all four. So the tests below are
about DENSITY, CONNECTEDNESS, WATER and the play contract, in that order, and they are written
against the shipped configs rather than against numbers typed here, so the generator and the
config cannot drift apart the way they already did once (the config said 88/16, the WorldSpec
built 130/26, and the two disagreed by 19,000 blocks).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import yaml

from mcbuild import audit, blocks, fluids, fun_contract, morph, palette
from mcbuild.gen import prismworks

CONFIGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs")


def _cfg(name):
    with open(os.path.join(CONFIGS, name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _built(params):
    canvas = prismworks.build(params)
    return canvas, canvas.to_model()


def _names(model):
    return {n.split(":")[-1].split("[")[0] for n in model.names}


def _cells(model):
    """{(x, y, z): block name} for every solid cell, as `fluids` wants it."""
    names = np.array([n.split(":")[-1].split("[")[0] for n in model.names])
    out = {}
    ys, zs, xs = np.where(model.solid())
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        out[(x, y, z)] = names[model.ids[y, z, x]]
    return out


def _one_piece(model):
    """The size of every 6-connected component. Diagonal-only adjacency is NOT adjacency."""
    _, sizes = morph.components(model.solid(), conn=6)
    return sorted(sizes, reverse=True)


# --------------------------------------------------------------- density and tiers

def test_the_ascent_is_built_at_hero_density_for_the_spire_the_worldspec_sites():
    """The budget band, on the params the SHIPPED CONFIG asks for.

    PARK_VISUAL_AND_BUDGET_SPEC section 4 locks the Prism Spire at 32,000-40,000 blocks
    "including core, outer ribs, launch, catches, balconies, crown, and concealed service".
    The floor is pinned hard. The ceiling is pinned loose and deliberately: the park
    coordinator's standing instruction is that over budget is acceptable when the blocks are
    doing real work, and the quality bar replacing it - every element belongs to a route,
    catch, observer, launch or service access - is what the rest of this file tests. A build
    past 50,000 is not "a bit over", it is padding coming back, and that is what fails here.
    """
    params = _cfg("prism_ascent.yaml")["params"]
    _, model = _built(params)
    n = int(model.solid().sum())
    assert 32_000 <= n <= 50_000, f"{n} blocks is outside the Prism Spire's density band"


def test_the_array_and_the_vault_hold_their_own_bands():
    for name, lo, hi in (("prism_array.yaml", 8_000, 10_000),
                         ("resonance_vault.yaml", 8_000, 10_000)):
        _, model = _built(_cfg(name)["params"])
        n = int(model.solid().sum())
        assert lo <= n <= hi, f"{name}: {n} blocks is outside {lo}-{hi}"


def test_every_kind_keeps_the_material_policy():
    """cheap 78-86%, okay accents 10-16%, and nothing expensive that is not declared.

    The `expensive` tier here is `redstone_lamp` and nothing else: every other block the policy
    names as declarable functional expensive - rails, targets, comparators, observers - prices
    as `cheap` under `palette.tier` on this economy, so the honest expensive share is a fraction
    of a percent rather than the policy's nominal 2-5%. Reaching that band would mean several
    hundred more lamps, which is the visual spec's own "neon scattered everywhere" rejection.
    """
    for name in ("prism_ascent.yaml", "prism_array.yaml", "resonance_vault.yaml"):
        cfg = _cfg(name)
        _, model = _built(cfg["params"])
        report = audit.audit(model, ground=False)
        total = report.blocks
        cheap = report.tiers.get("cheap", 0) / total
        okay = report.tiers.get("ok", 0) / total
        assert 0.78 <= cheap <= 0.86, f"{name}: cheap share {cheap:.1%}"
        assert 0.10 <= okay <= 0.16, f"{name}: okay-accent share {okay:.1%}"
        declared = set(cfg.get("expensive_functional", {}))
        spent = {k.split(":")[-1] for k, v in report.bom.items()
                 if palette.tier(k) == "expensive" and v}
        assert spent <= declared, f"{name}: undeclared expensive spend {sorted(spent - declared)}"


def test_nothing_is_off_the_server_or_off_the_economy():
    """1.19 only, and dirt/grass is CURRENCY on this skyblock, never bulk fill."""
    for name in ("prism_ascent.yaml", "prism_array.yaml", "resonance_vault.yaml"):
        _, model = _built(_cfg(name)["params"])
        used = _names(model) - {"air"}
        assert all(blocks.available(b) for b in used), f"{name}: not 1.19"
        unspendable = sorted(b for b in used if not blocks.spendable(b))
        assert not unspendable, f"{name}: currency blocks used as material: {unspendable}"


# --------------------------------------------------------------- connectedness

def test_each_design_is_one_six_connected_piece():
    for name in ("prism_ascent.yaml", "prism_array.yaml", "resonance_vault.yaml"):
        _, model = _built(_cfg(name)["params"])
        sizes = _one_piece(model)
        assert len(sizes) == 1, f"{name}: {len(sizes)} components, largest {sizes[:4]}"


def test_the_audit_finds_no_placement_problem_in_any_kind():
    for name in ("prism_ascent.yaml", "prism_array.yaml", "resonance_vault.yaml"):
        _, model = _built(_cfg(name)["params"])
        report = audit.audit(model, ground=False)
        assert report.ok, f"{name}: {report.problems[:4]}"


def test_a_real_structural_break_is_raised_rather_than_swept():
    """`prune_orphans` drops a stranded cell and REFUSES to hide a broken piece.

    A sweep that deletes anything disconnected is a cover-up: it turns "the ribs came away from
    the masts" into a silently smaller build. The threshold is what makes it a sweep.
    """
    canvas = prismworks.build({"kind": "array"})
    canvas.put(1, 11, 1, canvas.state("stone"))          # one stray: swept
    assert prismworks.prune_orphans(canvas, "test") == 1
    for k in range(12):                                   # a 12-cell island: refused
        canvas.put(1 + k, 11, 1, canvas.state("stone"))
    try:
        prismworks.prune_orphans(canvas, "test")
    except ValueError as exc:
        assert "structural break" in str(exc)
    else:
        raise AssertionError("a 12-cell orphan must be raised, not deleted")


# --------------------------------------------------------------- the Spire's form

def test_the_spire_has_four_structural_masts_running_its_whole_height():
    """PARK_VISUAL_AND_BUDGET_SPEC's required form names four masts, and they are load-bearing.

    Not four decorative corners: each is a 3x3 column standing from the machine base to the
    crown, and everything else in the Spire - collars, catch rings, observer decks - brackets
    back to them.
    """
    canvas, model = _built(_cfg("prism_ascent.yaml")["params"])
    masts = canvas.meta["masts"]
    assert len(masts) == 4
    levels = canvas.meta["levels"]
    solid = model.solid()
    for mx, my, mz in masts:
        column = [y for y in range(levels["base_lo"], levels["crown_lo"])
                  if solid[y, mz, mx]]
        assert len(column) == levels["crown_lo"] - levels["base_lo"], \
            f"mast at {mx},{mz} is not continuous"
    xs = sorted({m[0] for m in masts})
    zs = sorted({m[2] for m in masts})
    assert len(xs) == 2 and len(zs) == 2, "four masts, on the four corners of one cage"


def test_the_run_is_three_acts_in_the_order_a_runner_meets_them():
    canvas, _ = _built(_cfg("prism_ascent.yaml")["params"])
    acts = canvas.meta["acts"]
    assert [a["name"] for a in acts] == ["I", "II", "III"]
    # a descent: every act starts below the one before it and ends below its own start
    for act in acts:
        assert act["to_y"] < act["from_y"], f"act {act['name']} does not descend"
    for a, b in zip(acts, acts[1:]):
        assert b["from_y"] < a["from_y"]
    assert acts[0]["catch_ring_y"] and acts[1]["catch_ring_y"], "acts I and II end on a catch ring"
    assert acts[2]["catch_ring_y"] is None, "act III ends on the Calibration Court, not a ring"


def test_every_normal_jump_is_inside_the_sprint_jump_band():
    """3.0-4.5 centre to centre, from PRISMWORKS_PARKOUR_BRIEF's move table.

    A plunge is deliberately excluded: the brief's own rule is that a major drop gets its own
    enclosed catch and is never called a normal jump.
    """
    canvas, _ = _built(_cfg("prism_ascent.yaml")["params"])
    route = canvas.meta["route"]
    normal = {"ledge", "gate", "transfer"}
    checked = 0
    for prev, here in zip(route, route[1:]):
        if prev[3] not in normal or here[3] not in normal:
            continue
        gap = math.dist((prev[0], prev[2]), (here[0], here[2]))
        assert prismworks.JUMP_MIN <= gap <= prismworks.JUMP_MAX, \
            f"{gap:.2f} blocks between {prev[:3]} and {here[:3]}"
        checked += 1
    assert checked >= 15, "the run has to be mostly ordinary jumps"


def test_every_landing_is_solid_and_has_three_courses_of_headroom():
    canvas, _ = _built(_cfg("prism_ascent.yaml")["params"])
    for x, y, z, kind, _act in canvas.meta["route"]:
        if kind not in ("ledge", "gate", "transfer"):
            continue
        assert canvas.solid(x, y, z), f"no pad at {x},{y},{z}"
        for k in (1, 2, 3):
            assert not canvas.solid(x, y + k, z), f"headroom blocked over {x},{y},{z}"


def test_a_landing_is_never_inside_a_structural_mast():
    canvas, _ = _built(_cfg("prism_ascent.yaml")["params"])
    masts = {(m[0] + a, m[2] + b) for m in canvas.meta["masts"]
             for a in (-1, 0, 1) for b in (-1, 0, 1)}
    for x, y, z, kind, _act in canvas.meta["route"]:
        if kind in ("ledge", "gate", "transfer"):
            assert (x, z) not in masts, f"pad at {x},{y},{z} stands in a mast"


def test_both_plunges_land_in_water():
    """A controlled fall ends in a catch, or it is a damage challenge the brief forbids."""
    canvas, _ = _built(_cfg("prism_ascent.yaml")["params"])
    plunges = [r for r in canvas.meta["route"] if r[3] == "plunge"]
    assert len(plunges) == 2, "one major plunge in Act II, one finale drop"
    for x, y, z, _kind, _act in plunges:
        assert canvas.get_name(x, y, z).split(":")[-1] == "water", \
            f"plunge target at {x},{y},{z} is not water"


def test_the_observer_decks_are_outside_the_route_and_screened_from_it():
    canvas, _ = _built(_cfg("prism_ascent.yaml")["params"])
    decks = canvas.meta["observer_decks"]
    assert decks, "the brief requires separated observer balconies"
    pads = {(x, z) for x, _y, z, kind, _a in canvas.meta["route"]
            if kind in ("ledge", "gate", "transfer")}
    for dx, dy, dz in decks:
        assert (dx, dz) not in pads, "an observer stands on the course"
        screened = any(canvas.get_name(dx + ox, dy + oy, dz + oz).split(":")[-1] == "iron_bars"
                       for ox in range(-6, 7) for oy in (0, 1) for oz in range(-7, 8))
        assert screened, f"observer deck at {dx},{dy},{dz} has no screen"


# --------------------------------------------------------------- water

def test_no_design_leaks_a_single_water_cell():
    """`escapes` and `unenclosed` are different questions and a water design needs both.

    The log flume in this repo returned "the path is wet" and simultaneously poured 199,959
    cells to Y-1908, because only the ride path was ever checked. The Spire's bubble shaft is a
    hundred-and-twenty-course column of source water over an open machine base and is exactly
    the same shape of risk; carving a boarding hole in its casing drained 53,817 cells on the
    first attempt at this rebuild.
    """
    for name in ("prism_ascent.yaml", "prism_array.yaml", "resonance_vault.yaml"):
        _, model = _built(_cfg(name)["params"])
        cells = _cells(model)
        wet = [p for p, n in cells.items() if n == "water"]
        if not wet:
            continue
        sx, sy, sz = model.shape_xyz
        bounds = (0, 0, 0, sx - 1, sy - 1, sz - 1)
        assert fluids.escapes(cells, wet, wet, bounds) == [], f"{name}: water escapes"
        assert fluids.unenclosed(cells, allow=wet) == [], f"{name}: water has no bed or an open side"


def test_the_bubble_shaft_is_a_real_column_over_soul_sand():
    canvas, model = _built(_cfg("prism_ascent.yaml")["params"])
    names = _names(model)
    assert "soul_sand" in names and "water" in names
    assert canvas.meta["water"]["water"] > 800, "a bubble lift is a tall column, not a puddle"
    assert canvas.meta["water"]["escapes"] == 0 and canvas.meta["water"]["unenclosed"] == 0


def test_the_boarding_aperture_is_a_hatch_and_not_a_hole():
    """An open trapdoor is a vertical panel that holds water and that a player closes to pass.

    A gap cut in the casing is the same thing minus the water, which is why the first version
    drained the shaft into the machine base.
    """
    _, model = _built(_cfg("prism_ascent.yaml")["params"])
    from mcbuild import nbt
    hatches = [nbt.state_props(e) for e in model.palette
               if nbt.state_name(e).split(":")[-1] == "oak_trapdoor"]
    assert hatches, "no boarding hatch"
    assert all(p.get("open") == "true" for p in hatches),         "a closed trapdoor is a flap in the floor, not a water lock"


# --------------------------------------------------------------- the array

#: the maze's own bounding box, enclosing wall included - the service strip and the observer
#: gallery outside it are not corridors and must not be graded as if they were.
_MAZE_BOX = (2, 38)


def _array_open(model, canvas):
    """Standable cells inside the maze: air at y=1 with a floor under it."""
    lo, hi = _MAZE_BOX
    open_cells = set()
    for z in range(lo, hi + 1):
        for x in range(lo, hi + 1):
            if not canvas.solid(x, 1, z) and canvas.solid(x, 0, z):
                open_cells.add((x, z))
    return open_cells


def test_the_array_route_walks_from_entry_to_exit():
    canvas, model = _built(_cfg("prism_array.yaml")["params"])
    open_cells = _array_open(model, canvas)
    entry = tuple(canvas.meta["solved_entry"][::2])
    exit_ = tuple(canvas.meta["solved_exit"][::2])
    assert entry in open_cells and exit_ in open_cells
    seen, stack = {entry}, [entry]
    while stack:
        x, z = stack.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in open_cells and n not in seen:
                seen.add(n)
                stack.append(n)
    assert exit_ in seen, "the solved route does not reach the exit"


def test_every_wrong_branch_returns_to_a_known_choice_point():
    """PARK_FULL_BUILD_SPEC P3: "wrong branches return to a known choice point, not a dead end".

    Encoded as geometry rather than as intent: every branch is a LOOP whose far end lands back
    on the solved route, so no open cell in the maze has exactly one open neighbour. A maze
    built the usual way - a spanning tree with dead ends - fails this on its first corridor.
    """
    canvas, model = _built(_cfg("prism_array.yaml")["params"])
    open_cells = _array_open(model, canvas)
    apertures = {tuple(canvas.meta["solved_entry"][::2]), tuple(canvas.meta["solved_exit"][::2])}
    dead = []
    for cell in open_cells:
        if cell in apertures:
            continue
        n = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (cell[0] + dx, cell[1] + dz) in open_cells)
        if n < 2:
            dead.append(cell)
    assert not dead, f"{len(dead)} dead end(s), first {dead[:5]}"
    route = {(p[0], p[2]) for p in canvas.meta["solved_route"]}
    for cp in canvas.meta["choice_points"]:
        assert (cp["world"][0], cp["world"][2]) in route, \
            f"branch {cp['colour']} joins the route nowhere"
        assert cp["branch_len"] >= 6, "a two-cell detour is not a choice"


def test_the_colour_markers_are_attached_to_wall_structure():
    """"Colour marker blocks are attached to wall/floor structures, never floating accents.\""""
    canvas, _ = _built(_cfg("prism_array.yaml")["params"])
    for cp in canvas.meta["choice_points"]:
        assert cp["markers"] >= 1, f"choice point {cp['cell']} has no marker on a wall"


def test_the_service_strip_never_touches_the_public_route():
    canvas, model = _built(_cfg("prism_array.yaml")["params"])
    open_cells = _array_open(model, canvas)
    for px, py, pz in canvas.meta["service_panels"]:
        assert (px, pz) not in open_cells, "a reset panel stands in the maze corridor"
    assert len(canvas.meta["service_panels"]) == len(canvas.meta["choice_points"])


# --------------------------------------------------------------- the vault

def test_the_vault_has_three_separated_individually_testable_inputs():
    canvas, _ = _built(_cfg("resonance_vault.yaml")["params"])
    stations = canvas.meta["stations"]
    assert len(stations) == 3
    for station in stations:
        x, y, z = station["input"]
        assert canvas.get_name(x, y, z).split(":")[-1] == "stone_button", \
            "an input a player cannot press is not an input"
    for a in stations:                       # separated: 2-4 players standing apart
        for b in stations:
            if a is b:
                continue
            gap = math.dist(a["stand"], b["stand"])
            assert gap >= 8, f"stations {a['index']} and {b['index']} are {gap:.1f} apart"


def test_every_station_can_see_one_shared_state_panel():
    """PARK_FULL_BUILD_SPEC P5: one obvious completion, "not an invisible comparator state"."""
    canvas, _ = _built(_cfg("resonance_vault.yaml")["params"])
    px, py, pz = canvas.meta["state_panel"]
    lamps = 0
    for x in range(px - 4, px + 5):
        for z in range(pz - 4, pz + 5):
            for y in range(py - 2, py + 3):
                if canvas.get_name(x, y, z).split(":")[-1] == "redstone_lamp":
                    lamps += 1
    assert lamps >= 12, "the shared panel is a lamp face on every side, not one bulb"
    for station in canvas.meta["stations"]:
        sx, sy, sz = station["stand"]
        assert math.dist((sx, sz), (px, pz)) <= 16, "a station that cannot read the panel"
        # nothing full-height between the station and the panel: they share one room
        steps = 12
        for i in range(1, steps):
            t = i / steps
            bx = int(round(sx + (px - sx) * t))
            bz = int(round(sz + (pz - pz + pz - pz) * t + (pz - sz) * t))
            if abs(bx - px) <= 2 and abs(bz - pz) <= 2:
                break
            assert not canvas.solid(bx, sy + 2, bz), \
                f"station {station['index']} is walled off from the panel at {bx},{bz}"


def test_the_vault_posts_a_solo_fallback():
    """"A posted solo fallback is mandatory if no group is available.\""""
    canvas, _ = _built(_cfg("resonance_vault.yaml")["params"])
    sx, sy, sz = canvas.meta["solo_fallback"]
    posted = any("SOLO" in "".join(t["front"])
                 for pos, t in canvas.tiles.items()
                 if abs(pos[0] - sx) <= 4 and abs(pos[2] - sz) <= 4)
    assert posted, "the solo fallback is not posted where a lone player can read it"


def test_the_guest_vestibule_does_not_open_into_the_service_ring():
    """Maintenance isolation is a wall, not a rule written in a sidecar."""
    canvas, _ = _built(_cfg("resonance_vault.yaml")["params"])
    cx = cz = 39 // 2
    # walking the entry vestibule at head height, every cell either side of it must be solid.
    # The vestibule spans the outer shell to the service ring wall, and only that: past the ring
    # you are in the room, where an open side is the room.
    for x in range(1, 6):
        if not canvas.solid(x, 2, cz):        # inside the tunnel
            assert canvas.solid(x, 2, cz - 2) and canvas.solid(x, 2, cz + 2), \
                f"the entry tunnel is open to the service ring at x={x}"


# --------------------------------------------------------------- signage and contracts

def test_no_sign_in_any_kind_hangs_on_nothing():
    """A sign on a column that has an opening in it draws exactly like one on a wall."""
    for name in ("prism_ascent.yaml", "prism_array.yaml", "resonance_vault.yaml"):
        canvas, _ = _built(_cfg(name)["params"])
        assert canvas.meta["signs"] >= 4, f"{name}: a play space nobody can be told the rules in"
        prismworks.check_signs(canvas, name)          # raises if any is unsupported


def test_every_kind_states_what_it_has_not_proved():
    for name, expect in (("prism_ascent.yaml", "bubble_ascent"),
                         ("prism_array.yaml", "walkthrough_route"),
                         ("resonance_vault.yaml", "three_input_completion_circuit")):
        canvas, _ = _built(_cfg(name)["params"])
        assert expect in canvas.meta["requires_in_game"]


def test_experience_fun_contract_requires_outcome_reset_service_and_bypass():
    bad = fun_contract.assess({"class": "experience", "player_verbs": ["jump"], "outcome": "finish"})
    assert not bad["ok"]
    good = fun_contract.assess({
        "class": "experience", "player_verbs": ["jump"], "outcome": "finish",
        "reset": "staff reset", "service_access": "rear gallery", "bypass": "public path",
    })
    assert good["ok"]
    assert not fun_contract.assess({"class": "route", "player_verbs": [], "outcome": "exit",
                                    "spatial_job": "connect"})["ok"]


def test_an_unknown_kind_is_refused_by_name():
    try:
        prismworks.build({"kind": "spire"})
    except ValueError as exc:
        assert "ascent" in str(exc)
    else:
        raise AssertionError("an unknown kind must not build something plausible")
