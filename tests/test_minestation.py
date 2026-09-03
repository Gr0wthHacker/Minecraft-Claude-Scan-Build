"""The Mine Coaster, adopted and edited: what may change, and what must not.

Jack: "i dont think its actually built to exit there, it seems like they just exit from same
area, can we save the current rollercoaster and edit this properly."

This design is a DIFF against `out/park_final/artifacts/Mine Coaster.litematic`, which is the
backup and is never written to. So the tests here are mostly about what stayed the same: a copy
that quietly loses a cell, moves a corner or re-derives a rail's shape is a ride that no longer
matches the mountain measured around it.
"""
from __future__ import annotations

import os
import sys
from collections import deque

import numpy as np
import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import nbt, scan, schem                      # noqa: E402
from mcbuild.circuit import Circuit                       # noqa: E402
from mcbuild.gen import minestation                       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "configs", "pf_mine_coaster.yaml")
ART = os.path.join(ROOT, "out", "park_final", "artifacts", "Mine Coaster.litematic")
COMPLETE = os.path.join(ROOT, "out", "Park Complete.litematic")

#: the park lattice - `tools/park_place.ANCHOR` and the course a guest stands on
A = (97500, 80300)
PLANE = 203


@pytest.fixture(scope="module")
def params():
    with open(CFG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["params"]


def _states(model):
    """{(x, y, z): "name[k=v,...]"} for every non-air cell.

    Written against BOTH a `schem.Model` and a `Canvas`, because the artifact comes off disk as
    one and the design comes out of the generator as the other - and the whole point here is to
    compare them. `ids != 0` is air-index-zero in both; the name check is what makes that safe
    rather than assumed.
    """
    names = [nbt.state_name(e).split(":")[-1] for e in model.palette]
    props = [nbt.state_props(e) for e in model.palette]
    out = {}
    for y, z, x in zip(*(model.ids != 0).nonzero()):
        i = int(model.ids[y, z, x])
        if names[i] == "air":
            continue
        pr = ",".join(f"{k}={v}" for k, v in sorted(props[i].items()))
        out[(int(x), int(y), int(z))] = f"{names[i]}[{pr}]" if pr else names[i]
    return out


def _asked(params):
    """{local cell: what it is for} - every change the config asks for, and nothing else."""
    av, au = (int(a) for a in params["at"])
    plane = int(params["plane"])

    def span(spec, what):
        u0, u1 = (int(a) for a in spec["u"])
        for u in range(min(u0, u1), max(u0, u1) + 1):
            yield (int(spec["v"]) - av, int(spec["h"]) + plane, u - au), what

    out = {}
    for g in params.get("gates") or []:
        out.update(dict(span(g, "gate")))
    for r in params.get("plain") or []:
        out.update(dict(span(r, "isolator")))
    d = params.get("dispatch")
    if d:
        for k in ("plinth", "button"):
            c = d[k]
            out[(int(c["v"]) - av, int(c["h"]) + plane, int(c["u"]) - au)] = k
    return out


def test_the_adopted_ride_is_the_artifact_cell_for_cell_except_what_the_config_asks_for(params):
    """**THE ARTIFACT IS THE BACKUP AND THIS IS A DIFF AGAINST IT.** Anything that changed, was
    added or went missing and is not in the config is a cell the copy lost, moved or re-derived -
    and a rail's `shape`, a stair's `facing` and a trapdoor's `half` are decisions this repo's
    renderer draws identically whichever way round they are."""
    art = _states(schem.load(ART))
    got = _states(minestation.build(params))
    asked = _asked(params)
    added, gone = set(got) - set(art), set(art) - set(got)
    assert not gone, f"the copy is missing {len(gone)} cells of the artifact, eg {sorted(gone)[:4]}"
    assert added == {k for k, v in asked.items() if v in ("plinth", "button")}, (
        f"the copy adds {sorted(added)} but the config asks for the dispatch only")
    changed = {k for k in art if k in got and art[k] != got[k]}
    assert changed == {k for k, v in asked.items() if v in ("gate", "isolator")}, (
        f"changed {sorted(changed)} against asked {sorted(asked)}")
    for k in changed:
        # a fence and a rail in the artifact carry no properties, so compare the NAME
        if asked[k] == "gate":
            assert art[k].split("[")[0] == "spruce_fence", f"{k} was {art[k]}, not a fence"
            assert got[k].split("[")[0] == "spruce_fence_gate", f"{k} became {got[k]}"
            assert "open=true" in got[k], f"{k} is a gate nobody can walk through: {got[k]}"
        else:
            assert art[k].split("[")[0] == "powered_rail", f"{k} was {art[k]}, not a powered rail"
            assert got[k].split("[")[0] == "rail", f"{k} became {got[k]}, not a plain rail"
            # THE SHAPE IS WHAT MAKES THE LOOP A LOOP and it must be carried, not re-derived
            a = dict(kv.split("=") for kv in art[k].split("[")[1][:-1].split(","))
            g = dict(kv.split("=") for kv in got[k].split("[")[1][:-1].split(","))
            assert a["shape"] == g["shape"], f"{k} changed shape {a['shape']} -> {g['shape']}"


def test_the_copy_keeps_the_artifacts_own_corner_and_size(params):
    """A Canvas is sized to its own content, so a copy that lost a cell on an edge comes out a
    size smaller - and `park_place` positions a module by its model's CORNER, which would slide
    the whole ride against a mountain whose tunnel box, stand-off and adit are all measured to
    where it stands today."""
    a = schem.load(ART)
    c = minestation.build(params)
    assert (c.ids.shape) == (a.ids.shape), f"the copy is {c.ids.shape}, the artifact {a.ids.shape}"


def test_a_gate_asked_for_where_there_is_no_fence_raises(params):
    """A gate placed on a cell the ride does not fence there would be a SILENT no-op, which is
    this project's most-repeated failure shape - so it is an error instead."""
    bad = {**params, "gates": [{"v": 29, "u": [120, 120], "h": 1, "facing": "north"}]}
    with pytest.raises(ValueError, match="does not fence"):
        minestation.build(bad)


def test_a_gate_faces_ACROSS_the_fence_it_is_set_into(params):
    """A FENCE GATE'S POSTS STAND PERPENDICULAR TO ITS `facing`, so a gate set into a fence that
    runs along U must face along V or it joins nothing - it reads as a gate dropped beside the
    rail rather than set into the line, and our renderer draws every facing identically. Written
    `facing: north` first, which is along the run."""
    art = _states(schem.load(ART))
    got = _states(minestation.build(params))
    av, au = (int(a) for a in params["at"])
    plane = int(params["plane"])
    for g in params["gates"]:
        v, h = int(g["v"]) - av, int(g["h"]) + plane
        u0, u1 = (int(a) - au for a in g["u"])
        # the run is whichever axis the artifact's own fence continues along
        along_u = any(art.get((v, h, u), "").split("[")[0] == "spruce_fence"
                      for u in (min(u0, u1) - 1, max(u0, u1) + 1))
        assert along_u, f"the fence at v{v} h{h} does not run along U - re-measure before trusting"
        for u in range(min(u0, u1), max(u0, u1) + 1):
            face = dict(kv.split("=") for kv in got[(v, h, u)].split("[")[1][:-1].split(","))
            assert face["facing"] in ("east", "west"), (
                f"the gate at v{v} u{u} faces {face['facing']}, along its own fence run")


def _passable(pal):
    AIRY = {"air", "cave_air", "void_air", "vine", "glow_lichen", "short_grass", "tall_grass",
            "fern", "moss_carpet", "torch", "wall_torch", "lantern", "rail", "powered_rail",
            "detector_rail", "spruce_wall_sign", "spruce_sign"}
    out = []
    for e in pal:
        n = nbt.state_name(e).split(":")[-1]
        p = nbt.state_props(e)
        # AN OPEN FENCE GATE IS A DOORWAY. Read as solid - which a name-only test does - the two
        # gates this design exists to add measure as two more fence cells and the exit reports
        # as sealed, which is the exact bug being fixed reappearing in its own test.
        out.append(n in AIRY or (n.endswith("_fence_gate") and str(p.get("open")) == "true"))
    return np.array(out)


@pytest.mark.skipif(not os.path.exists(COMPLETE), reason="the park has not been composited")
def test_a_rider_can_walk_off_the_train_and_out_of_the_building():
    """THE WHOLE POINT. A rider steps off at the track lane beside the station and has to reach
    the verge, through the platform and the concourse, without climbing anything or crossing a
    rail. Measured on the shipped composite, not on this design alone - the way out runs through
    the frontage's own exit gate and the ground layer's spur."""
    s = scan.load(COMPLETE)
    ox, oy, oz = s.origin
    ids = s.model.ids
    ok = _passable(s.model.palette)
    solid = ~ok
    Vs, Us, Hs = range(18, 46), range(96, 140), range(-2, 8)
    sol = {(V, U, h): bool(solid[ids[PLANE + h - oy, U + A[1] - oz, V + A[0] - ox]])
           for V in Vs for U in Us for h in Hs}

    def stand(p):
        V, U, h = p
        return ((V, U, h - 1) in sol and (V, U, h + 1) in sol and sol[(V, U, h - 1)]
                and not sol[(V, U, h)] and not sol[(V, U, h + 1)])

    nodes = {p for p in sol if stand(p)}
    src = [p for p in nodes if p[0] == 31 and 118 <= p[1] <= 124]
    assert src, "there is nowhere to stand beside the track at the station"
    dst = {p for p in nodes if p[0] == 19 and 119 <= p[1] <= 121}
    assert dst, "the exit spur does not reach the verge"
    seen, dq = set(src), deque(src)
    while dq:
        V, U, h = dq.popleft()
        for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dh in (0, 1, -1):
                q = (V + dv, U + du, h + dh)
                if q in nodes and q not in seen:
                    seen.add(q)
                    dq.append(q)
    assert dst & seen, "a rider who steps off the train cannot walk out of the station"


# --------------------------------------------------------------------------- the circuit

#: which two cells each rail shape links to, as offsets. An ascending rail's first entry is its
#: HIGH end. This is the game's own table, not a convention of ours.
LINK = {"north_south": [(0, 0, -1), (0, 0, 1)], "east_west": [(-1, 0, 0), (1, 0, 0)],
        "ascending_north": [(0, 1, -1), (0, 0, 1)], "ascending_south": [(0, 1, 1), (0, 0, -1)],
        "ascending_east": [(1, 1, 0), (-1, 0, 0)], "ascending_west": [(-1, 1, 0), (1, 0, 0)],
        "south_east": [(0, 0, 1), (1, 0, 0)], "south_west": [(0, 0, 1), (-1, 0, 0)],
        "north_west": [(0, 0, -1), (-1, 0, 0)], "north_east": [(0, 0, -1), (1, 0, 0)]}
CORNERS = {"south_east", "south_west", "north_west", "north_east"}


def _rails(model):
    names = [nbt.state_name(e).split(":")[-1] for e in model.palette]
    props = [nbt.state_props(e) for e in model.palette]
    out, occ, power = {}, {}, set()
    for y, z, x in zip(*(model.ids != 0).nonzero()):
        i = int(model.ids[y, z, x])
        pos = (int(x), int(y), int(z))
        occ[pos] = names[i]
        if names[i] in ("rail", "powered_rail"):
            out[pos] = (names[i], props[i].get("shape"))
        if names[i] == "redstone_block":
            power.add(pos)
    return out, occ, power


def _links(rails):
    """The two rails each rail actually joins - a neighbour may be a course up or down."""
    adj = {}
    for p, (_n, sh) in rails.items():
        outs = []
        for dx, dy, dz in LINK[sh]:
            for ddy in (0, -1, 1):
                q = (p[0] + dx, p[1] + dy + ddy, p[2] + dz)
                if q in rails:
                    outs.append(q)
                    break
        adj[p] = outs
    return adj


@pytest.fixture(scope="module")
def ride():
    return schem.load(os.path.join(ROOT, "out", "PF Mine Coaster.litematic"))


def test_the_track_is_one_closed_loop(ride):
    """A RIDE IS A CIRCUIT OR IT IS A SIDING. Every rail joins exactly two others and the whole
    lot is one piece - a cart that leaves the station has to arrive back at it. The isolators
    this design adds are PLAIN RAIL rather than air precisely so this stays true."""
    rails, _occ, _pw = _rails(ride)
    adj = _links(rails)
    loose = [p for p, v in adj.items() if len(v) != 2]
    assert not loose, f"{len(loose)} rails do not join two others, eg {loose[:4]}"
    seen, comps = set(), []
    for p in rails:
        if p in seen:
            continue
        comp, stack = {p}, [p]
        seen.add(p)
        while stack:
            q = stack.pop()
            for r in adj[q] + [r for r, o in adj.items() if q in o]:
                if r not in comp:
                    comp.add(r)
                    seen.add(r)
                    stack.append(r)
        comps.append(len(comp))
    assert len(comps) == 1, f"the track is in {len(comps)} pieces: {sorted(comps, reverse=True)}"


def test_every_corner_is_a_plain_rail_that_links_both_ways(ride):
    """A POWERED RAIL HAS NO CURVED SHAPE - off `data/blocks.json`, its shapes are the six
    straight and ascending ones - so every corner must be plain rail. And a corner is flat: if a
    neighbour does not link back to it, the game has re-derived the turn as a slope and the
    circuit dead-ends there. Our renderer draws every shape identically."""
    rails, _occ, _pw = _rails(ride)
    for p, (n, sh) in rails.items():
        if sh not in CORNERS:
            continue
        assert n == "rail", f"the corner at {p} is a {n}, which has no curved shape"
        for dx, dy, dz in LINK[sh]:
            e = (p[0] + dx, p[1] + dy, p[2] + dz)
            assert e in rails, f"the corner at {p} has an end reaching no rail at {e}"
            back = [(e[0] + a, e[1] + b, e[2] + c) for a, b, c in LINK[rails[e][1]]]
            assert p in back, f"the rail at {e} does not link back to the corner at {p}"


def test_every_track_cell_has_two_clear_courses_over_it(ride):
    """A rider sits in the cart; two courses of clearance is the ride's own contract and the
    difference between a tunnel and a suffocation trap."""
    rails, occ, _pw = _rails(ride)
    OK = {"air", "rail", "powered_rail", "vine", "glow_lichen", "lantern"}
    blocked = [(p, d, occ[(p[0], p[1] + d, p[2])]) for p in rails for d in (1, 2)
               if occ.get((p[0], p[1] + d, p[2]), "air") not in OK]
    assert not blocked, f"{len(blocked)} track cells are roofed too low, eg {blocked[:4]}"


def test_only_the_station_rails_are_braked(ride, params):
    """**AN UNPOWERED POWERED RAIL IS A BRAKE**, so a dead rail anywhere but the station is a
    cart that stops in mid-air. Measured on the artifact all 278 were energised, which is why the
    ride had no station at all; this design cuts exactly three out of the chain."""
    rails, _occ, power = _rails(ride)
    adj = _links(rails)

    def fed(p):
        x, y, z = p
        return any((x + a, y + b, z + c) in power for a, b, c in
                   ((0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)))

    src = {p for p, (n, _s) in rails.items() if n == "powered_rail" and fed(p)}
    dist = {p: 0 for p in src}
    dq = deque(src)
    while dq:
        p = dq.popleft()
        if dist[p] >= 8:                     # a powered rail carries eight further, no more
            continue
        for q in adj[p]:
            if rails[q][0] == "powered_rail" and dist.get(q, 99) > dist[p] + 1:
                dist[q] = dist[p] + 1
                dq.append(q)
    av, au = (int(a) for a in params["at"])
    plane = int(params["plane"])
    dead = {(p[0] + av, p[2] + au, p[1] - plane)
            for p, (n, _s) in rails.items() if n == "powered_rail" and p not in dist}
    assert dead == {(32, 118, 1), (32, 119, 1), (32, 120, 1)}, (
        f"the braked rails are {sorted(dead)}, not the station's three")


def test_the_station_holds_a_cart_at_rest_and_the_button_dispatches_it(ride, params):
    """THE CONTRACT, ASSERTED BY SIMULATION rather than claimed - the rule this repo cut two
    finished casino games for. At rest the three station rails carry no power, so a cart coasting
    in stops on them; the button strongly powers the plinth beside them, which activates all
    three; and when the button's pulse runs out they go dead again so the NEXT cart stops too."""
    c = Circuit.of(ride)
    av, au = (int(a) for a in params["at"])
    plane = int(params["plane"])
    hold = [(32 - av, 1 + plane, u - au) for u in (118, 119, 120)]
    btn = tuple(params["dispatch"]["button"][k] for k in ("v", "h", "u"))
    btn = (btn[0] - av, btn[1] + plane, btn[2] - au)
    assert c.name(btn) == "stone_button", f"there is no dispatch button at {btn}"
    for _ in range(6):
        c.step()
    assert not any(c.powered(p) for p in hold), "the station is live at rest - a cart never stops"
    c.press(btn, ticks=10)
    for _ in range(4):
        c.step()
    assert all(c.powered(p) for p in hold), "the button does not dispatch the cart"
    for _ in range(16):
        c.step()
    assert not any(c.powered(p) for p in hold), (
        "the station stays live after the press - the next cart will not stop")
