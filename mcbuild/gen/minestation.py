"""The Mine Coaster, ADOPTED AND EDITED - the ride's own artifact, with its station opened up.

Jack: "i dont think its actually built to exit there, it seems like they just exit from same
area, can we save the current rollercoaster and edit this properly."

He is right, and dressing the outside had run out of road. Measured off the composite, the
station's own platform - V28-30 x U118-125 in park coordinates - is a SEALED PEN: a
`spruce_fence` runs the whole of V27 across U119-123 and another the whole of V31, with no gate
in either. It is enterable from neither the concourse in front of it nor the track behind it, so
the east "exit" the frontage had been given was a gate opening onto a fence.

WHY THIS FILE RATHER THAN A HAND-EDITED LITEMATIC
-------------------------------------------------
`tools/park_place.modules` prefers `out/PF <name>.litematic` over
`out/park_final/artifacts/<name>.litematic`, so writing this design is how the park is handed an
edited ride WITHOUT touching the artifact - which stays exactly as it is as the backup, is
re-read from disk on every run, and is the thing this generator is a diff against. The edits are
code with tests rather than bytes nobody can review.

**THE RIDE IS COPIED STATE FOR STATE, AND IN ITS OWN AXES.** A rail's `shape`, a stair's
`facing` and a trapdoor's `half` are decisions and this repo's renderer draws a wrong one
identically to a right one, so nothing is re-derived. And the emitted model keeps the SOURCE'S
OWN CORNER: `park_place` positions a module by its model's corner, so a canvas cropped even one
cell tighter than the artifact would slide the whole ride - and the ridge's tunnel, stand-off and
adit are all measured against where it stands today.

WHAT IS CHANGED, AND NOTHING ELSE
---------------------------------
`gates` names fence cells, in PARK coordinates because that is what everything here is measured
in, and turns them into `spruce_fence_gate[open=true]`. A gate rather than a hole: a gap in a
fence reads as a fence somebody broke, a gate reads as a way through. Every named cell is CHECKED
to be a fence first and the build RAISES if it is not, because a gate asked for on a cell the
ride does not fence there would otherwise be a silent no-op - this project's most-repeated
failure shape.
"""
from __future__ import annotations

from .. import nbt, schem
from .vertical import World

MINESTATION = {
    "source": None,        # the artifact to adopt
    "at": [0, 0],          # [V, U] the source's own (x=0, z=0) stands at, for reading `gates`
    "plane": 0,            # the course of the source that is its ground
    "gates": None,         # [{v, u: [u0, u1], h, facing}] fence cells that become gates
    "plain": None,         # [{v, u: [u0, u1], h}] powered rails that become PLAIN rail
    "dispatch": None,      # {plinth: {v,u,h,block}, button: {v,u,h,facing}}
}


def build(cfg: dict, donors=None):
    p = {**MINESTATION, **cfg}
    src = p.get("source")
    if not src:
        raise ValueError("minestation needs params.source = the ride's own .litematic")
    m = schem.load(src)
    av, au = (int(a) for a in p["at"])
    plane = int(p["plane"])
    names = [nbt.state_name(e).split(":")[-1] for e in m.palette]
    props = [nbt.state_props(e) for e in m.palette]

    def _local(v, u, h):
        return (int(v) - av, int(h) + plane, int(u) - au)

    def _span(spec):
        u0, u1 = (int(a) for a in spec["u"])
        for u in range(min(u0, u1), max(u0, u1) + 1):
            yield _local(spec["v"], u, spec["h"])

    # the cells that become gates, in the SOURCE's own local coordinates
    want = {}
    for g in (p.get("gates") or []):
        for key in _span(g):
            want[key] = str(g.get("facing", "north"))

    # **THE ISOLATORS, AND WHY A STATION NEEDS THEM.** Measured on the artifact, all 278 of the
    # ride's powered rails are energised - 54 fed directly by a `redstone_block` and the rest by
    # the eight-rail chain off those - so a cart never stops anywhere on the circuit, which is
    # exactly why it has no station. An UNPOWERED powered rail is a brake; the way to make three
    # of them unpowered is to cut the chain either side, and a PLAIN rail does not carry it.
    # Plain rather than air: the loop has to stay closed, and `test_the_track_is_one_closed_loop`
    # says so.
    plain = {k for spec in (p.get("plain") or []) for k in _span(spec)}

    w = World()
    opened, isolated, wrong = 0, 0, []
    ys, zs, xs = m.solid().nonzero()
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        idx = int(m.ids[y, z, x])
        key = (int(x), int(y), int(z))
        if key in plain:
            if names[idx] != "powered_rail":
                wrong.append((key, names[idx]))
            else:
                # THE SHAPE IS CARRIED. A rail's shape is what makes the loop a loop, and this
                # repo's renderer draws every shape identically.
                w.put(x, y, z, "rail", shape=str(props[idx].get("shape", "north_south")),
                      waterlogged="false")
                isolated += 1
                continue
        if key in want:
            if "fence" not in names[idx] or "gate" in names[idx]:
                wrong.append((key, names[idx]))
            else:
                w.put(x, y, z, names[idx].replace("_fence", "_fence_gate"),
                      facing=want[key], open="true", powered="false", in_wall="false")
                opened += 1
                continue
        w.put(x, y, z, names[idx], **{k: str(v) for k, v in props[idx].items()})

    absent = sorted((set(want) | plain) - {(int(x), int(y), int(z))
                                for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())})
    if wrong or absent:
        raise ValueError(
            "minestation: a gate was asked for where the ride does not fence. "
            + "; ".join(f"local {k} is {n}" for k, n in wrong[:4])
            + ("; nothing at all at " + ", ".join(map(str, absent[:4])) if absent else ""))

    # -- the dispatch -------------------------------------------------------------------------
    # A STRONGLY-POWERED BLOCK BESIDE A POWERED RAIL ACTIVATES IT, and a button on a block
    # strongly powers that block - so the plinth stands in the boarding lane against the braked
    # rails and the button goes on its far face, where an operator on the platform can press it
    # and a rider already in the cart can still reach it.
    d = p.get("dispatch")
    dispatch = None
    if d:
        pl, bt = d["plinth"], d["button"]
        px, py, pz = _local(pl["v"], pl["u"], pl["h"])
        bx, by, bz = _local(bt["v"], bt["u"], bt["h"])
        for key, what in (((px, py, pz), "plinth"), ((bx, by, bz), "button")):
            if key in {(int(x), int(y), int(z))
                       for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}:
                raise ValueError(f"minestation: the dispatch {what} at local {key} is not empty "
                                 f"in the ride - it would overwrite a cell of the artifact")
        w.put(px, py, pz, str(pl.get("block", "stone_bricks")))
        w.put(bx, by, bz, str(bt.get("block", "stone_button")),
              face="wall", facing=str(bt["facing"]), powered="false")
        dispatch = {"plinth": [px, py, pz], "button": [bx, by, bz]}

    sy, sz, sx = m.ids.shape
    c = w.canvas({
        "kind": "minestation",
        "source": src,
        "gates_opened": opened,
        "rails_isolated": isolated,
        "dispatch": dispatch,
        "size": [int(sx), int(sy), int(sz)],
        "contract": "the Mine Coaster's own artifact, copied state for state in its own axes, "
                    "with named fence cells of its station turned into open fence gates so the "
                    "platform can be walked into from the concourse and out of from the "
                    "track, a braked station section held by plain-rail isolators either side, "
                    "and a button that powers it to dispatch",
        "unverified": ["not placed in game", "the ride's circuit and trestles are the artifact's "
                       "own and are not re-derived here"],
    })
    got = (c.sx, c.sy, c.sz) if hasattr(c, "sx") else (c.ids.shape[2], c.ids.shape[0], c.ids.shape[1])
    if got != (int(sx), int(sy), int(sz)):
        # A CANVAS IS SIZED TO ITS OWN CONTENT, so a copy that lost a cell on an edge comes out a
        # size smaller - and `park_place` positions a module by its model's corner, which would
        # slide the whole ride against a mountain measured to where it stands today.
        raise ValueError(f"minestation: the copy is {got}, the artifact is "
                         f"{(int(sx), int(sy), int(sz))} - it would place off by the difference")
    return c
