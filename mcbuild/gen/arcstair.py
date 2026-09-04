"""Two mirrored curved flights off a platform corner's notches, meeting at the waterfall's middle.

Built for the friend island (2026-09-04). The platform is a round deck of spruce top slabs at
Y198 over open void; each arm carries a 2x2 notch on either flank near its tip, and between two
neighbouring arms a two-wide WATERFALL falls along the diagonal from the deck to bedrock. Jack:
"connect two ends, so that they circle and meet in the center of where the multiple water streams
are", and "the stairs are symmetrical in materials etc, they should be duplicate and then meet in
the middle".

The shape, per corner, in a CANONICAL frame where the corner is north-west of the platform's
centre (every other corner is a sign flip of it, and the second flight is the first reflected
across the diagonal - so it is a duplicate by construction, materials included):

    NOTCH FLOOR   the four notch cells become spruce bottom slabs, a half step down off the deck
    FLIGHT        an ARC of treads round the platform's centre, OUTSIDE the waterfall curtain,
                  one sector per half-step: a stone-brick block for a whole-number surface, a
                  spruce bottom slab on a stone-brick stringer for a half one. Block, slab, block,
                  slab: the stone carries the flight and the spruce is the half step, and every
                  tread touches the one before it in its own course, so the flight is one piece
                  with no post.
    THE MEETING   both flights end at the diagonal, flat, one half step above a landing of
                  stone-brick slabs on top of a solid 3x3 STONE PIER standing in the curtain's
                  middle.
    THE DESCENT   one wider helix winds down round the pier and ends on a stone pad.

Three rules, each enforced per cell rather than trusted:

- A TREAD IS A SECTOR of the arc, and every band cell belongs to exactly one sector, so the
  treads tile the arc with no gap and no overlap.
- HEADROOM IS THE AUDIT'S: two clear cells over ceil(surface). Everything here is outside the
  deck's rim, so only the flights' own upper courses and the pier's landing ever take it.
- NOTHING GOES WHERE THE WORLD HOLDS ANYTHING, and never in a waterfall column: a tread under
  falling water catches it and spreads it seven cells over the stair. Water anchors nothing.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

ARCSTAIR = {
    "under": None,             # the platform capture; every cell it holds is refused
    "center": None,            # world (x, z) of the platform's centre cell
    "corner": "NW",            # NW | NE | SW | SE
    "deck_surface": 199.0,     # the deck's walking surface (top slabs at Y198)
    # canonical (north-west) layout, as offsets from the centre: the notch on the west arm's
    # north flank, and the cell it opens onto. The north arm's west notch is its mirror.
    "notch": [-16, -15, -5, -4],
    "exit": [-16, -6],
    "r_in": 17.0,              # the arc's inner radius: just outside the curtain's outer row
    "width": 3,                # tread depth outward
    "steps": None,             # half-steps from the notch to the meeting; even, derived if None
    "pier": 15,                # the pier's centre is this far out along the diagonal
    "tail_width": 3,
    "tail_courses": 10,
    "block": "stone_bricks",
    "slab": "spruce_slab",
    "landing_slab": "stone_brick_slab",
    "tail_slab": "spruce_slab",
    "tail_slab_alt": "stone_brick_slab",
    "alt_rate": 0.3,
    "torch_every": 4,
    "seed": 0,
}

_AIR = {"air", "cave_air", "void_air"}
_NOT_ANCHOR = _AIR | {"water", "lava", "bubble_column", "vine", "glow_lichen", "moss_carpet",
                      "short_grass", "tall_grass", "fern"}
_CORNER = {"NW": (1, 1), "NE": (-1, 1), "SW": (1, -1), "SE": (-1, -1)}
_DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]   # E SE S SW W NW N NE
_FACE = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}


def _sector8(du: int, dv: int) -> int:
    return int(round(math.degrees(math.atan2(dv, du)) / 45.0)) % 8


class _Site:
    """The world and the design, addressed in the CANONICAL frame (u east, v south, corner NW).

    Every query and every placement goes through `to_world`, so a corner is a sign flip and the
    build itself never knows which one it is on. A wall torch's facing is flipped with it."""

    def __init__(self, ctx: Ctx | None, w: World, center, corner: str):
        self.ctx, self.w = ctx, w
        self.cx, self.cz = center
        self.sx, self.sz = _CORNER[corner]

    def to_world(self, u, v):
        return self.cx + self.sx * u, self.cz + self.sz * v

    def name_at(self, u, y, v) -> str:
        if self.ctx is None:
            return "air"
        x, z = self.to_world(u, v)
        return self.ctx.name_at(x, y, z)

    def world_free(self, u, y, v) -> bool:
        return self.name_at(u, y, v) in _AIR

    def has(self, u, y, v) -> bool:
        x, z = self.to_world(u, v)
        return self.w.has(x, y, z)

    def free(self, u, y, v) -> bool:
        return self.world_free(u, y, v) and not self.has(u, y, v)

    def headroom(self, u, h, v) -> bool:
        base = int(math.ceil(h))
        return self.free(u, base, v) and self.free(u, base + 1, v)

    def anchored(self, u, y, v) -> bool:
        for du, dy, dv in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            if self.has(u + du, y + dy, v + dv):
                return True
            if self.name_at(u + du, y + dy, v + dv) not in _NOT_ANCHOR:
                return True
        return False

    def put(self, u, y, v, name, **props):
        x, z = self.to_world(u, v)
        if name == "wall_torch":
            f = props["facing"]
            flip = {"east": "west", "west": "east"} if self.sx < 0 else {}
            flip.update({"south": "north", "north": "south"} if self.sz < 0 else {})
            props = {**props, "facing": flip.get(f, f)}
        self.w.put(x, y, z, name, **props)

    def name(self, u, y, v):
        x, z = self.to_world(u, v)
        return self.w.name(x, y, z)


def _tread(site: _Site, u, h, v, p: dict, slab: str, slabs_only: bool = False) -> bool:
    """One cell of a walking surface h: a stone block for a whole number, else a spruce bottom
    slab with a stone stringer under it. The stringer is what makes consecutive treads one
    piece - a bottom slab and the block a course down beside it are diagonal neighbours.

    `slabs_only` is the helix round the pier: it has the pier to hang from, so a whole-number
    surface is a top slab and nothing is laid under a bottom one - built of blocks and
    stringers it rendered as a lump of masonry rather than a stair."""
    if not site.headroom(u, h, v):
        return False
    if slabs_only:
        y, kind = (int(h) - 1, "top") if h == math.floor(h) else (int(math.floor(h)), "bottom")
        if not site.free(u, y, v) or not site.anchored(u, y, v):
            return False
        site.put(u, y, v, slab, type=kind, waterlogged="false")
        return True
    if h == math.floor(h):
        y = int(h) - 1
        if not site.free(u, y, v) or not site.anchored(u, y, v):
            return False
        site.put(u, y, v, p["block"])
        return True
    y = int(math.floor(h))
    if not site.free(u, y, v):
        return False
    under = site.free(u, y - 1, v)
    if not (site.anchored(u, y, v) or (under and site.anchored(u, y - 1, v))):
        return False
    site.put(u, y, v, slab, type="bottom", waterlogged="false")
    if under:
        site.put(u, y - 1, v, p["block"])
    return True


def _adjacent(a: list, b: list) -> bool:
    bs = set(b)
    return any((u + du, v + dv) in bs for (u, v) in a for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def _chain(wedges: list) -> int:
    n = 0
    for k, cells in enumerate(wedges):
        if not cells or (k and not _adjacent(wedges[k - 1], cells)):
            break
        n += 1
    return n


def _lay(site: _Site, wedge_cells: list, h: float, p: dict, slab: str,
         slabs_only: bool = False) -> list:
    """Lay one tread's cells to a fixpoint, so a cell may lean on a mate placed after it."""
    todo = list(wedge_cells)
    got = []
    changed = True
    while changed and todo:
        changed = False
        for (u, v) in list(todo):
            if _tread(site, u, h, v, p, slab, slabs_only):
                got.append((u, v))
                todo.remove((u, v))
                changed = True
    return got


def _flight(site: _Site, p: dict, mirror: bool, deck: float, n: int, band: list,
            th0: float, dth: float) -> dict:
    """The arc from the notch to the diagonal. `mirror` builds the second flight as the first
    reflected across u = v: the same sectors, the same materials, cell for cell."""
    def angle(u, v):
        if mirror:
            u, v = v, u
        return math.degrees(math.atan2(v, u)) % 360.0
    wedges = []
    for k in range(1, n + 1):
        lo = th0 + (k - 1.5) * dth
        hi = th0 + (k - 0.5) * dth
        cells = []
        for (u, v, r) in band:
            a = angle(u, v)
            if lo <= a < hi or (k == n and abs(a - hi) < 1e-9):
                cells.append((u, v))
        h = deck - 0.5 - 0.5 * k
        wedges.append(_lay(site, cells, h, p, p["slab"]))
    return {"wedges": wedges, "chain": _chain(wedges), "cells": sum(len(w) for w in wedges)}


def _helix(site: _Site, post, j0: int, spin: int, h_top: float, n_half: int, r_in: float,
           r_out: float, p: dict, seed: int) -> dict:
    """The descent round the pier: eight sectors, half a step each, slabs only (bottom then top),
    spruce with the odd tread in stone brick for tone. The pier is what it hangs from."""
    pu, pv = post
    rr = int(math.ceil(r_out)) + 1
    by = {j: [] for j in range(8)}
    for du in range(-rr, rr + 1):
        for dv in range(-rr, rr + 1):
            r = math.hypot(du, dv)
            if r < r_in or r > r_out + 0.5:
                continue
            by[_sector8(du, dv)].append((pu + du, pv + dv, r))
    for j in by:
        by[j].sort(key=lambda c: c[2])
    wedges = []
    for k in range(n_half):
        h = h_top - 0.5 * k
        j = (j0 + spin * k) % 8
        slab = p["tail_slab_alt"] if hash01(k, 11, seed) < p["alt_rate"] else p["tail_slab"]
        wedges.append(_lay(site, [(u, v) for (u, v, r) in by[j]], h, p, slab, slabs_only=True))
    return {"wedges": wedges, "chain": _chain(wedges), "cells": sum(len(w) for w in wedges),
            "by": by}


def _torches(site: _Site, pu, pv, y_hi: int, y_lo: int, every: int, reach: int) -> int:
    if not every:
        return 0
    n = 0
    for y in range(y_hi, y_lo - 1, -1):
        if (y_hi - y) % every:
            continue
        for (du, dv) in _FACE:
            u, v = pu + du * reach, pv + dv * reach
            if not site.has(u - du, y, v - dv):
                continue
            if site.free(u, y, v) and site.free(u, y - 1, v) and site.free(u, y - 2, v):
                site.put(u, y, v, "wall_torch", facing=_FACE[(du, dv)])
                n += 1
                break
    return n


def build_arcstair(cfg: dict, donors=None) -> Canvas:
    p = {**ARCSTAIR, **cfg}
    if not p.get("center"):
        raise ValueError("arcstair needs params.center, the platform's centre cell")
    ctx = Ctx(p["under"]) if p.get("under") else None
    w = World()
    site = _Site(ctx, w, tuple(int(v) for v in p["center"]), str(p["corner"]).upper())
    deck = float(p["deck_surface"])
    deck_y = int(deck) - 1
    seed = int(p["seed"])
    u0, u1, v0, v1 = (int(v) for v in p["notch"])
    eu, ev = (int(v) for v in p["exit"])
    r_in = float(p["r_in"])
    r_out = r_in + int(p["width"]) - 1
    d = int(p["pier"])

    # 1. THE NOTCH FLOORS - a half step down, anchored to the deck's own frame slabs
    floors = []
    for mirror in (False, True):
        cells = [(u, v) for u in range(u0, u1 + 1) for v in range(v0, v1 + 1)]
        if mirror:
            cells = [(v, u) for (u, v) in cells]
        got = _lay(site, cells, deck - 0.5, p, p["slab"])
        floors.append(len(got))

    # 2. THE ARC. Sectors run from the exit cell's angle to the diagonal (225 degrees in the
    # canonical frame); an even count, so the meeting lands on a half step and the landing
    # slabs sit flat with the last tread.
    th_exit = math.degrees(math.atan2(ev, eu)) % 360.0
    th_meet = 225.0
    span = th_meet - th_exit
    n = int(p["steps"]) if p.get("steps") else 2 * max(1, int(round(math.radians(span) * r_in / 2)))
    dth = span / (n - 0.5)
    rr = int(math.ceil(r_out)) + 1
    band = []
    for u in range(-rr, 1):
        for v in range(-rr, 1):
            r = math.hypot(u, v)
            if r_in - 0.5 <= r <= r_out + 0.5:
                band.append((u, v, r))
    band.sort(key=lambda c: c[2])
    h_last = deck - 0.5 - 0.5 * n            # the last tread's surface: a half step
    y_last = int(math.floor(h_last))

    # 3. THE PIER, laid before the flights so their last treads can lean on it: solid stone from
    # the landing course down to the pad, with the landing itself a course of stone-brick slabs
    # flat with the flights' last treads
    n_tail = 2 * int(p["tail_courses"])      # even: the descent starts on a block and ends on
                                             # a slab, so the pad a half step under it is stone
    h_pad = h_last - 0.5 - 0.5 * n_tail
    y_pad = int(h_pad) - 1
    pier = 0
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            for y in range(y_last - 1, y_pad - 1, -1):
                if site.free(-d + du, y, -d + dv):
                    site.put(-d + du, y, -d + dv, p["block"])
                    pier += 1
            if site.free(-d + du, y_last, -d + dv):
                site.put(-d + du, y_last, -d + dv, p["landing_slab"], type="bottom",
                         waterlogged="false")

    flights = []
    for mirror in (False, True):
        f = _flight(site, p, mirror, deck, n, band, th_exit, dth)
        if f["chain"] < n:
            raise ValueError(f"flight {'B' if mirror else 'A'} breaks at half-step {f['chain'] + 1} "
                             f"(surface {deck - 0.5 - 0.5 * (f['chain'] + 1)})")
        flights.append(f)

    mirrored = dict(w.cells)                 # everything so far is meant to be symmetric
    # 4. THE DESCENT round the pier: start and spin measured for the longest walkable chain
    r_tail_in, r_tail_out = 1.5, 2.0 + int(p["tail_width"])
    h_top = h_last - 0.5
    best = None
    for j in range(8):
        for spin in (1, -1):
            probe = World()
            probe.cells = dict(w.cells)
            s = _Site(ctx, probe, (site.cx, site.cz), str(p["corner"]).upper())
            r = _helix(s, (-d, -d), j, spin, h_top, 8, r_tail_in, r_tail_out, p, seed)
            edge = [(-d + du, -d + dv) for du in (-1, 0, 1) for dv in (-1, 0, 1)]
            onto = bool(r["wedges"] and _adjacent(edge, r["wedges"][0]))
            score = (onto, r["chain"], r["cells"])
            if best is None or score > best[0]:
                best = (score, j, spin)
    _, j_tail, spin = best
    tail = _helix(site, (-d, -d), j_tail, spin, h_top, n_tail, r_tail_in, r_tail_out, p, seed)
    if tail["chain"] < n_tail:
        raise ValueError(f"the descent breaks at half-step {tail['chain'] + 1}")
    pad = 0
    for extra in range(3):
        j = (j_tail + spin * (n_tail + extra)) % 8
        for (u, v, r) in tail["by"][j]:
            if _tread(site, u, h_pad, v, p, p["slab"]):
                pad += 1
    torches = _torches(site, -d, -d, y_last - 1, y_pad, int(p["torch_every"]), reach=2)

    # 5. THE MIRROR, verified rather than assumed: every cell of flight A has its twin in B with
    # the same block, except where the world itself is asymmetric (a deck cell missing on one
    # side), and those are counted
    asym = 0
    for (x, y, z), (name, props) in mirrored.items():
        u, v = (x - site.cx) * site.sx, (z - site.cz) * site.sz
        mx, mz = site.to_world(v, u)
        other = mirrored.get((mx, y, mz))
        if other is None or other[0] != name:
            asym += 1
    meta = {"kind": "arcstair", "corner": str(p["corner"]).upper(), "center": list(p["center"]),
            "deck_surface": deck, "steps": n, "sector_deg": round(dth, 3),
            "exit_deg": round(th_exit, 2), "meet_h": h_last, "landing_h": h_last,
            "notch_floor": floors, "flight_cells": [f["cells"] for f in flights],
            "pier": pier, "pier_at": [-d, -d], "tail_cells": tail["cells"], "tail_spin": spin,
            "tail_start": list(_DIRS[j_tail]), "pad": pad, "pad_h": h_pad, "torches": torches,
            "asymmetric_cells": asym}
    return w.canvas(meta)
