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


def test_the_adopted_ride_is_the_artifact_cell_for_cell_except_its_gates(params):
    """**THE ARTIFACT IS THE BACKUP AND THIS IS A DIFF AGAINST IT.** Anything that changed and is
    not a gate the config asked for is a cell the copy lost, moved or re-derived - and a rail's
    `shape`, a stair's `facing` and a trapdoor's `half` are decisions this repo's renderer draws
    identically whichever way round they are."""
    art = _states(schem.load(ART))
    got = _states(minestation.build(params))
    assert set(art) == set(got), (
        f"the copy has {len(set(got) - set(art))} cells the artifact has not and is missing "
        f"{len(set(art) - set(got))}")
    changed = {k for k in art if art[k] != got[k]}
    av, au = (int(a) for a in params["at"])
    plane = int(params["plane"])
    asked = set()
    for g in params["gates"]:
        u0, u1 = (int(a) for a in g["u"])
        for u in range(min(u0, u1), max(u0, u1) + 1):
            asked.add((int(g["v"]) - av, int(g["h"]) + plane, u - au))
    assert changed == asked, (
        f"changed {sorted(changed)[:6]} but the config asks for {sorted(asked)[:6]}")
    for k in changed:
        # a fence in the artifact carries no properties at all, so compare the NAME
        assert art[k].split("[")[0] == "spruce_fence", f"{k} was {art[k]}, not a fence"
        assert got[k].split("[")[0] == "spruce_fence_gate", f"{k} became {got[k]}, not a gate"
        assert "open=true" in got[k], f"{k} is a gate nobody can walk through: {got[k]}"


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
