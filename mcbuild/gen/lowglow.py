"""The Lowland Glow - the lighting pass, solved by propagation rather than placed by eye.

THE AUDIT THAT PRODUCED IT (2026-08-22, Jack: find a way to add more light in smart ways,
all changes final, mismatches accepted). Block light was PROPAGATED through the composite of
the capture and every tracked design - the court hall's freeze-guard method, scene-wide -
and the surface classified cell by cell. The findings that shaped the design:

- The walking surface was mostly fine: 250 spawnable columns out of 6,321, in 19 clusters.
  The ground's own lantern grid plus Jack's 39 ochre froglights already carry the floor -
  92 of the ground design's 212 lanterns are lost to accepted mismatches, and the froglights
  are what replaced them.
- THE DARK WAS ON TOP OF THINGS, not on the ground: the axolotl's back (90 wool cells), the
  ring's crown, the sanctum's crests, the campanile's deck, house A's roof, tree canopies,
  four stair treads mid-gap between rail lanterns. Light placed at eye level never reaches
  a crown, and a spawnable crown puts a zombie on the portal at night.
- 3,700 columns hide dark buried seams UNDER the massif fill - unlightable from outside,
  reported, out of scope.

THE SOLVER: story fixtures first (measured by hand), then a greedy cover - the right tool
per surface, full re-propagation each round - until ZERO spawnable surface cells remain.
29 fixtures. The per-surface rules ARE the design:

- moss and rock       -> ochre froglight, FLUSH (dig the turf cell) - Jack's own idiom,
                         39 already on this floor
- ruin masonry crests -> soul lanterns: the quarter's cold flame, and light 10 covers what
                         five amethysts cannot
- tree canopies and the axolotl's back -> glow lichen, face-down: a lush cave grows light
                         on what stands still long enough. NOTHING else is ever placed on
                         an animal.
- the harbor shallows -> sea pickles, waterlogged threes: the water lights itself
- one warm lantern on house A's chimney (the hamlet's only warm light after the hearth),
  one soul lantern HUNG in the watergate arch, one on the campanile's crown deck beside
  the owl, one on a stair rail post over the four dark treads.

tests/test_lowland_glow.py re-runs the propagation over the finished composite and asserts
the zero. If any design moves and a dark cell opens, that test - not a player at night -
is what finds it.
"""
from __future__ import annotations

from .canvas import Canvas
from .vertical import Ctx, World
from .ruinring import _PASSABLE

LOWGLOW = {
    "under": None,
    # every list is world cells, measured by the solver and PINNED
    "froglights": [],          # [x, y, z] - the SURFACE cell it replaces; goes on the dig list
    "lichen": [],              # [x, y, z] - air cell with solid below; clings face-down
    "souls": [],               # [x, y, z] - standing soul lanterns on crests and rails
    "lanterns": [],            # [x, y, z] - standing warm lanterns
    "hanging": [],             # [x, y, z] - soul lanterns hung from a ceiling
    "pickles": [],             # [x, y, z] - water cells, three pickles each
    # designs whose UNBUILT cells count as footing (a lamp on the stair's rail post, the
    # campanile's cap, the hamlet's chimney) - the fixture waits for them, build order.
    # NOT named "on": YAML 1.1 parses on/off/yes/no as BOOLEANS, and the key vanished.
    "footing": [],
    "seed": 0,
}

_SOLID_EXTRA = {"water"}


def build_lowglow(cfg: dict, donors=None) -> Canvas:
    p = {**LOWGLOW, **cfg}
    if not p.get("under"):
        raise ValueError("lowglow needs params.under")
    ctx = Ctx(p["under"])
    support = set()
    if p.get("footing"):
        import numpy as np
        from .vertical import load_capture
        for path in p["footing"]:
            m, (ox, oy, oz) = load_capture(path)
            ys, zs, xs = np.where(m.ids > 0)
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
                support.add((x + ox, y + oy, z + oz))

    def solid(x, y, z):
        return ctx.name_at(x, y, z) not in _PASSABLE | _SOLID_EXTRA or (x, y, z) in support

    w = World()
    dig = []
    feats = {k: 0 for k in ("froglights", "lichen", "souls", "lanterns", "hanging",
                            "pickles")}
    for (x, y, z) in p["froglights"]:
        n = ctx.name_at(x, y, z)
        if n in _PASSABLE:
            raise ValueError(f"froglight at {(x, y, z)} replaces nothing - resite it")
        dig.append((x, y, z))                          # flush: the turf goes first
        w.put(x, y, z, "ochre_froglight")
        feats["froglights"] += 1
    for (x, y, z) in p["lichen"]:
        if not solid(x, y - 1, z):
            raise ValueError(f"lichen at {(x, y, z)} has nothing below to cling to")
        w.put(x, y, z, "glow_lichen", down="true", up="false", north="false",
              south="false", east="false", west="false", waterlogged="false")
        feats["lichen"] += 1
    for key, block, hang in (("souls", "soul_lantern", False),
                             ("lanterns", "lantern", False),
                             ("hanging", "soul_lantern", True)):
        for (x, y, z) in p[key]:
            anchor = (x, y + 1, z) if hang else (x, y - 1, z)
            if not solid(*anchor):
                raise ValueError(f"{block} at {(x, y, z)} has no {'ceiling' if hang else 'floor'}")
            w.put(x, y, z, block, hanging="true" if hang else "false",
                  waterlogged="false")
            feats[key] += 1
    for (x, y, z) in p["pickles"]:
        if ctx.name_at(x, y, z) != "water":
            raise ValueError(f"pickle at {(x, y, z)} is not in water")
        if ctx.name_at(x, y - 1, z) in _PASSABLE | _SOLID_EXTRA:
            raise ValueError(f"pickle at {(x, y, z)} has no bed to grow on")
        w.put(x, y, z, "sea_pickle", pickles="3", waterlogged="true")
        feats["pickles"] += 1
    return w.canvas({"kind": "lowglow", "profile_view": "top", "facing": [0, 1],
                     "features_built": feats, "dig": [list(d) for d in dig]})
