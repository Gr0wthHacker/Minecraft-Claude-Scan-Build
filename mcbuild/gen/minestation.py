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

    # the cells that become gates, in the SOURCE's own local coordinates
    want = {}
    for g in (p.get("gates") or []):
        u0, u1 = (int(a) for a in g["u"])
        for u in range(min(u0, u1), max(u0, u1) + 1):
            want[(int(g["v"]) - av, int(g["h"]) + plane, u - au)] = str(g.get("facing", "north"))

    w = World()
    opened, wrong = 0, []
    ys, zs, xs = m.solid().nonzero()
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        idx = int(m.ids[y, z, x])
        key = (int(x), int(y), int(z))
        if key in want:
            if "fence" not in names[idx] or "gate" in names[idx]:
                wrong.append((key, names[idx]))
            else:
                w.put(x, y, z, names[idx].replace("_fence", "_fence_gate"),
                      facing=want[key], open="true", powered="false", in_wall="false")
                opened += 1
                continue
        w.put(x, y, z, names[idx], **{k: str(v) for k, v in props[idx].items()})

    absent = sorted(set(want) - {(int(x), int(y), int(z))
                                for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())})
    if wrong or absent:
        raise ValueError(
            "minestation: a gate was asked for where the ride does not fence. "
            + "; ".join(f"local {k} is {n}" for k, n in wrong[:4])
            + ("; nothing at all at " + ", ".join(map(str, absent[:4])) if absent else ""))

    sy, sz, sx = m.ids.shape
    c = w.canvas({
        "kind": "minestation",
        "source": src,
        "gates_opened": opened,
        "size": [int(sx), int(sy), int(sz)],
        "contract": "the Mine Coaster's own artifact, copied state for state in its own axes, "
                    "with named fence cells of its station turned into open fence gates so the "
                    "platform can be walked into from the concourse and out of from the track",
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
