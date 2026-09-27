"""THE CANOPY WALK - the park's first upward addition, and the contracts that keep it honest."""
import os

import numpy as np
import pytest
import yaml

from mcbuild import scan
from mcbuild.gen import canopywalk as cw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "configs", "pf_canopy_walk.yaml")
OUT = os.path.join(ROOT, "out", "PF Canopy Walk.litematic")


def _params():
    with open(CFG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["params"]


def _fake_surface(dv, du, fn):
    s = np.zeros((dv, du), np.int32)
    for v in range(dv):
        for u in range(du):
            s[v, u] = fn(v, u)
    return s


def test_the_route_never_runs_inside_the_rock():
    """The ONE hard rule. `clear_max` is a cost - a walkway spans a dip - but a deck inside the
    ridge is a deck nobody can walk, and no amount of cheapness may buy it."""
    p = {**cw.WALK, "v0": 0, "v1": 40, "u_mid": 10, "u_slack": 8, "deck_y": 228,
         "clear_min": 3, "clear_max": 16}
    # a ridge with a hump right across the middle of the corridor
    surf = _fake_surface(50, 25, lambda v, u: 240 if (15 <= v <= 25 and u <= 10) else 218)
    path = cw.route(surf, p)
    for (v, u) in path:
        assert p["deck_y"] - int(surf[v, u]) >= p["clear_min"], f"deck inside the rock at v{v} u{u}"


def test_it_goes_ROUND_a_peak_rather_than_over_it():
    """The design's whole premise: hold the deck level and move the route. If the walk climbed
    instead it would be a staircase, and if it flew it would be a viaduct."""
    p = {**cw.WALK, "v0": 0, "v1": 40, "u_mid": 10, "u_slack": 8, "deck_y": 228,
         "clear_min": 3, "clear_max": 16}
    surf = _fake_surface(50, 25, lambda v, u: 240 if (15 <= v <= 25 and u <= 10) else 218)
    us = [u for _v, u in cw.route(surf, p)]
    assert max(us) > 10, "the route never left the peak's own columns"


def test_a_straight_ridge_gives_a_STRAIGHT_walk():
    """`turn_cost` is what stops a least-cost path slaloming for a block of clearance nobody can
    see. With nothing in the way the answer must be a straight line."""
    p = {**cw.WALK, "v0": 0, "v1": 40, "u_mid": 10, "u_slack": 8, "deck_y": 228}
    surf = _fake_surface(50, 25, lambda v, u: 219)
    us = {u for _v, u in cw.route(surf, p)}
    assert len(us) == 1, f"a flat ridge produced a wandering route through {sorted(us)}"


def test_an_unsupported_SPAN_is_bounded_rather_than_ignored():
    """A walkway crosses a dip; it does not fly. A run of columns with no rock within `clear_max`
    is deck with no pier under it, and past `max_span` the design is lying about being carried."""
    p = {**cw.WALK, "v0": 0, "v1": 60, "u_mid": 10, "u_slack": 6, "deck_y": 228, "max_span": 8}
    surf = _fake_surface(70, 20, lambda v, u: 202 if 20 <= v <= 45 else 219)
    with pytest.raises(ValueError, match="pier"):
        cw.route(surf, p)


def test_the_config_asks_the_WORLD_and_the_audit_asks_the_same_one():
    """One design, two worlds, two answers - the drift `Ctx` records the shop islet losing a day
    to. The rock that carries this walk is the rock it is verified against."""
    with open(CFG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    assert cfg["params"]["under"] == cfg["finish"]["verify_against"]
    assert "world" in cfg["params"]["under"], "the route is measured off the world AS BUILT"
    assert "Park Complete" not in cfg["params"]["under"], "a design composite is not the rock"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Canopy Walk is not shipped")
def test_the_shipped_walk_is_one_piece_and_sits_where_it_says():
    s = scan.load(OUT)
    sol = s.model.solid()
    assert sol.sum() > 500, "a walk this short is not a walk"
    ys = np.nonzero(sol.any((1, 2)))[0] + s.origin[1]
    deck = _params()["deck_y"]
    assert ys.min() < deck, "nothing reaches down to the rock - where are the piers?"
    assert ys.max() >= deck, "the deck is missing"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Canopy Walk is not shipped")
def test_the_shipped_walk_can_actually_be_WALKED():
    """**THE ONLY CONTRACT A WALKWAY HAS.** Every other check here is about blocks; this is about a
    person. A deck can be legal, supported, affordable, one connected solid and still have a
    one-block riser in it that nobody can climb - the rim stair shipped exactly that and only a
    walk test could see it.

    Surface heights, so a bottom stair is half a block: the whole route must be crossable in steps
    of at most one course, end to end.
    """
    from collections import deque

    s = scan.load(OUT)
    m = s.model
    ox, oy, oz = s.origin
    names = [n.split(":")[-1] for n in m.names]
    sol = m.solid()

    def surface(x, y, z):
        """The height of the top of this cell, or None if you cannot stand on it."""
        i = int(m.ids[y, z, x])
        n = names[i]
        if n == "air":
            return None
        if n.endswith("_slab"):
            return y + 1.0        # every slab this design lays is type=top
        if n.endswith("_stairs"):
            return y + 1.0        # a stair's back half is full; its top is the cell boundary
        if n.endswith(("_fence", "_log")) or n == "ochre_froglight":
            return y + 1.0 if n == "ochre_froglight" else None
        return y + 1.0

    stand = {}
    Y, Z, X = sol.shape
    for y in range(Y - 1):
        for z in range(Z):
            for x in range(X):
                if not sol[y, z, x]:
                    continue
                h = surface(x, y, z)
                if h is None:
                    continue
                if sol[y + 1, z, x] and names[int(m.ids[y + 1, z, x])] != "air":
                    continue          # something on top of it: not a floor
                stand[(x, z)] = max(stand.get((x, z), -99), h)

    assert len(stand) > 250, f"only {len(stand)} standable cells - that is not a walk"
    xs = sorted({x for x, _z in stand})
    start = min(((x, z) for (x, z) in stand if x == xs[0]), key=lambda c: c[1])
    seen, q = {start}, deque([start])
    while q:
        x, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (x + dx, z + dz)
            if nb in stand and nb not in seen and abs(stand[nb] - stand[(x, z)]) <= 1.0:
                seen.add(nb); q.append(nb)
    reach_x = {x for x, _z in seen}
    assert max(reach_x) >= xs[-1] - 1, (
        f"the walk is not continuous: from its west foot you reach x{ox + max(reach_x)} "
        f"of x{ox + xs[-1]} - {len(seen)} of {len(stand)} standable cells")


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Canopy Walk is not shipped")
def test_the_stray_prune_is_a_SAFETY_NET_and_not_the_design():
    """`_prune_strays` guarantees one piece; this stops it being how one piece is ACHIEVED.

    `stegosaur` records the reasoning: a geometry that needs a lot of stitching is a geometry that
    is wrong, so the net's own count is bounded and the bound is asserted rather than hoped for.
    """
    import json
    meta = json.load(open(os.path.splitext(OUT)[0] + ".scan.json", encoding="utf-8"))
    parts = meta.get("parts", {})
    total = sum(v for k, v in parts.items() if k != "pruned")
    assert parts.get("pruned", 0) <= max(12, total // 100), (
        f"{parts.get('pruned')} cells pruned of {total} - the walk is coming apart faster than it "
        f"is being built, and the net is hiding it")
    assert parts.get("deck", 0) > 300 and parts.get("piers", 0) > 100, parts

def _placed_coaster():
    """The Mine Coaster IN WORLD COORDINATES, AS THE PARK PLACES IT.

    **A LOT MODULE IS NOT PLACED AT ITS OWN SIDECAR ORIGIN**, and auditing against one is how this
    contract was nearly written about the wrong ride: `out/Mine Coaster.litematic` is a retired
    69x94x97 artifact whose sidecar records a world origin **48 blocks** from where the park puts
    the coaster, and comparing against it reports a rail cell taken that is not. What ships is
    `out/PF Mine Coaster.litematic` at its lot, which is the frame `params.ride_at` names.
    """
    p = _params()
    own, env = cw._ride_keepout(p, int(p["anchor"][1]), int(p["lot"][0]), int(p["lot"][1]))
    ax, az = int(p["anchor"][0]) + int(p["at"][0]), int(p["anchor"][2]) + int(p["at"][1])
    to_world = lambda s: {(ax + v, y, az + u) for (v, u, y) in s}
    return to_world(own), to_world(env)


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Canopy Walk is not shipped")
def test_the_walk_takes_NOT_ONE_CELL_OF_THE_RIDE_and_nothing_a_rider_passes_through():
    """THE TRIPWIRE THIS DESIGN SHIPPED WITHOUT, AND BOTH CHECKS THAT SHOULD HAVE CAUGHT IT MISSED.

    `finish.verify_against` audits against a CAPTURE and a capture holds only what is BUILT: the
    Mine Coaster is 62% placed, every one of the 81 cells this walk took off it was in the unbuilt
    38%, and the audit reported overlap 0 honestly. `park_place.clashes` asks the other question -
    which two DESIGNS want one cell - and never saw this one, because a design outside
    `EXTRAS_READY` is not in the composite it compares. So nothing in the pipeline could see two
    piers running down through the ride's trestle at x97615 and x97621, or five cells of timber
    standing in the two courses over live track at x97532.

    A shared TERRAIN cell is a work problem; a cell in the track or in the clearance over it is a
    rider hitting a beam at speed. Both are asserted, and the clearance is the one that matters.
    """
    s = scan.load(OUT)
    ox, oy, oz = s.origin
    ys, zs, xs = np.nonzero(s.model.solid())
    mine = set(zip((xs + ox).tolist(), (ys + oy).tolist(), (zs + oz).tolist()))
    ride, rider = _placed_coaster()
    assert ride, "the ride keep-out is empty - `params.ride` is not reaching the generator"
    hit = sorted(mine & ride)
    assert not hit, f"{len(hit)} cells of the Mine Coaster, e.g. {hit[:4]}"
    over = sorted(mine & rider)
    assert not over, f"{len(over)} cells in the rider's clearance, e.g. {over[:4]}"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Canopy Walk is not shipped")
def test_the_ride_keepout_is_LOAD_BEARING_and_not_decoration():
    """A guard that never fires is a guard nobody can tell from a comment.

    The refusals are recorded on the build, so a `ride` that stops reaching the generator - a
    renamed artifact, a dropped config key - fails here rather than quietly shipping a walk back
    through the coaster. `truss_cables_declined` is the same evidence for the cable: the ride's
    lift hill climbs y236 to y244 through this span, which is above any mast worth building.
    """
    import json
    meta = json.load(open(os.path.splitext(OUT)[0] + ".scan.json", encoding="utf-8"))
    assert meta.get("ride_cells_refused", 0) > 0, (
        "nothing was refused for the ride - the keep-out is not reaching the build")
