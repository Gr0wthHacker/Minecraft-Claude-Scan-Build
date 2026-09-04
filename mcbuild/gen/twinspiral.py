"""Twin slab helices off the two alcoves of a platform arm, meeting below it in one stair.

Built for the friend island (2026-09-04): a one-course round platform of spruce top slabs at Y198
over open void, with a 2x2 notch framed in stone-brick slabs at each end of its east and west arms.
Jack: "put spiral staircases on each end of the slab which then meet at a lower centre point
combining into a single staircase."

The shape, per arm:

    ALCOVE FLOOR   the four notch cells become bottom slabs, a half step down off the deck
    TWIN HELIX     a 1x1 spruce-log post at the notch's OUTER corner, in open air beyond the rim,
                   with an eight-sector slab helix round it (bottom, top, bottom, top... so the
                   rise is 0.5 a tread and the flight can be WALKED). Its first tread IS the alcove
                   floor; it corkscrews away from the platform first, because the courses just
                   under a top-slab deck have no headroom and only open sky can carry a tread there.
    HAND-OFF       after `meet_turns` turns the tread that points at the arm's middle runs out as a
                   bridge into a stone-brick LANDING hung under the log spoke, and the twin stops.
    TAIL           one wider helix continues down from the landing round a post that hangs from the
                   spoke's own log, and ends on a quarter-turn stone-brick pad.

Three rules that decide whether it can be walked, all enforced per cell rather than trusted:

- A TREAD IS A SECTOR, and every cell of the annulus belongs to exactly one sector per turn: a
  cell's angle round the post picks the nearest of the eight ring directions, so consecutive
  treads tile the ring with no gap and no overlap (the wand's `/cscan fill spiral` rule).
- HEADROOM IS THE AUDIT'S, NOT THE GAME'S. `audit.check_climb` demands the two cells over
  ceil(surface) clear; the game would let a 1.8-tall player stand 0.3 closer under a top slab.
  Built to the stricter rule so the repo's own gate passes, at the cost of one more open-air tread.
- NOTHING IS PLACED WHERE THE WORLD HOLDS ANYTHING - the deck, its frames, and above all the rim
  WATERFALLS, which fall from Y198 to bedrock two cells off each alcove. A tread under a falling
  water column catches it and spreads it seven cells over the stair.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

TWINSPIRAL = {
    "under": None,             # the platform capture; every cell it holds is refused
    "deck_surface": 199.0,     # the walking surface of the deck (top slabs at Y198)
    # one entry per arm: the two twin posts, the two notches, and where the tail hangs
    #   {"a": [x, z], "a_hole": [x0, x1, z0, z1], "b": [x, z], "b_hole": [...], "tail": [x, z]}
    "pairs": [],
    "width": 2,                # tread depth outward from the ring (ring is r=1; band r=2..width+1)
    "tail_width": 3,
    "meet_turns": 2,           # the twins hand off on the first inward tread at or past this
    "tail_courses": 10,        # how far the single stair continues below the landing
    "slab": "spruce_slab",
    "slab_alt": "stone_brick_slab",
    "alt_rate": 0.3,           # share of TREADS (whole wedges) in the second slab
    "post": "spruce_log",
    "tail_post": "spruce_log",
    "landing": "stone_bricks",
    "newel": 0,                # courses the twin post rises above the deck. 0: the audit's climb
                               # gate takes the highest surface as the top, and a newel's top is
                               # a surface nobody walks onto
    "torch_every": 4,          # a wall torch on each post every N courses; 0 for none
    "seed": 0,
}

_AIR = {"air", "cave_air", "void_air"}
_DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]   # E SE S SW W NW N NE
_FACE = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}


def _sector(dx: int, dz: int) -> int:
    """Nearest of the eight ring directions to a cell offset. Never a tie on integer offsets."""
    return int(round(math.degrees(math.atan2(dz, dx)) / 45.0)) % 8


def _slab_at(h: float) -> tuple[int, str]:
    """A walking surface h -> (course, slab type) of the slab that gives it."""
    if h == math.floor(h):
        return int(h) - 1, "top"
    return int(math.floor(h)), "bottom"


_NOT_ANCHOR = _AIR | {"water", "lava", "bubble_column", "vine", "glow_lichen", "moss_carpet",
                      "short_grass", "tall_grass", "fern"}


class _Site:
    """The world plus everything this design has placed so far, asked one question: is it free."""

    def __init__(self, ctx: Ctx | None, w: World):
        self.ctx, self.w = ctx, w

    def world_free(self, x, y, z) -> bool:
        return self.ctx is None or self.ctx.name_at(x, y, z) in _AIR

    def free(self, x, y, z) -> bool:
        return self.world_free(x, y, z) and not self.w.has(x, y, z)

    def headroom(self, x, h, z) -> bool:
        base = int(math.ceil(h))
        return self.free(x, base, z) and self.free(x, base + 1, z)

    def anchored(self, x, y, z) -> bool:
        """Something to place it against: a design cell already standing, or a solid world block.
        Water is not one - the rim waterfalls cut a wedge in two and the far half would float."""
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nx, ny, nz = x + dx, y + dy, z + dz
            if self.w.has(nx, ny, nz):
                return True
            if self.ctx is not None and self.ctx.name_at(nx, ny, nz) not in _NOT_ANCHOR:
                return True
        return False


def _ring(post, r_in: float, r_out: float) -> dict:
    """Every cell of the annulus, by the ring direction nearest its angle, inner cells first."""
    px, pz = post
    rr = int(math.ceil(r_out)) + 1
    by = {j: [] for j in range(8)}
    for dx in range(-rr, rr + 1):
        for dz in range(-rr, rr + 1):
            r = math.hypot(dx, dz)
            if r < r_in or r > r_out + 0.5:
                continue
            by[_sector(dx, dz)].append((px + dx, pz + dz, r))
    for j in by:
        by[j].sort(key=lambda c: c[2])
    return by


def _adjacent(a: list, b: list) -> bool:
    """Do two wedges share an edge in plan? That is what makes a half step between them a step."""
    bs = {(x, z) for (x, z) in b}
    return any((x + dx, z + dz) in bs for (x, z) in a for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def _chain(wedges: list) -> int:
    """How many treads can be walked in sequence from the first before a wedge fails to touch the
    one before it. Every cell already has its headroom; adjacency is the only thing left to ask."""
    n = 0
    for k, cells in enumerate(wedges):
        if not cells or (k and not _adjacent(wedges[k - 1], cells)):
            break
        n += 1
    return n


def _helix(site: _Site, post, j0: int, spin: int, h_top: float, n_half: int, r_out: float,
           p: dict, seed: int, tag: str, r_in: float = 0.5) -> dict:
    """Lay treads round `post` from h_top downward, one sector per half-step.

    A cell is placed only if it is free, has the audit's two clear courses over it, and touches
    something already standing - the post, a wedge-mate, the previous tread, or a world block.
    Each wedge is laid to a FIXPOINT, so a cell whose only anchor is a wedge-mate placed after
    it still goes in (the east-north notch's outer cell has no deck beside it yet)."""
    by = _ring(post, r_in, r_out)
    placed, skipped, wedges = 0, 0, []
    for k in range(n_half):
        h = h_top - 0.5 * k
        j = (j0 + spin * k) % 8
        y, kind = _slab_at(h)
        name = p["slab_alt"] if hash01(k, 7, seed, sum(map(ord, tag))) < p["alt_rate"] else p["slab"]
        todo = [(x, z) for (x, z, r) in by[j] if site.free(x, y, z) and site.headroom(x, h, z)]
        got = []
        changed = True
        while changed and todo:
            changed = False
            for (x, z) in list(todo):
                if site.anchored(x, y, z):
                    site.w.put(x, y, z, name, type=kind, waterlogged="false")
                    got.append((x, z))
                    todo.remove((x, z))
                    changed = True
        skipped += len(by[j]) - len(got)
        placed += len(got)
        wedges.append(got)
    return {"placed": placed, "treads": sum(1 for g in wedges if g), "skipped": skipped,
            "wedges": wedges, "chain": _chain(wedges)}


def _surface(site: _Site, x, h, z, p: dict) -> bool:
    """Whatever block gives a walking surface h: a full block for an integer, a bottom slab else."""
    if h == math.floor(h):
        y = int(h) - 1
        if not site.free(x, y, z):
            return False
        site.w.put(x, y, z, p["landing"])
        return True
    y, kind = _slab_at(h)
    if not site.free(x, y, z):
        return False
    site.w.put(x, y, z, p["slab_alt"], type=kind, waterlogged="false")
    return True


def _post(site: _Site, x, z, y_hi: int, y_lo: int, name: str, **props) -> int:
    n = 0
    for y in range(y_hi, y_lo - 1, -1):
        if site.free(x, y, z):
            site.w.put(x, y, z, name, **props)
            n += 1
    return n


def _torches(site: _Site, x, z, y_hi: int, y_lo: int, every: int, outward: tuple,
             reach: int = 1) -> int:
    """A wall torch on the post's free face every `every` courses, preferring the open side.

    `reach` is how far from the axis the post's face is (1 for a 1x1 post, 2 for a 3x3 core)."""
    if not every:
        return 0
    n = 0
    faces = [outward] + [d for d in _FACE if d != outward]
    for y in range(y_hi, y_lo - 1, -1):
        if (y_hi - y) % every:
            continue
        for (dx, dz) in faces:
            cx, cz = x + dx * reach, z + dz * reach
            if not site.w.has(cx - dx, y, cz - dz):
                continue
            # a wall torch counts as head obstruction in the audit's walk, so the two treads
            # whose headroom this cell belongs to must not exist: the courses under it stay free
            if site.free(cx, y, cz) and site.free(cx, y - 1, cz) and site.free(cx, y - 2, cz):
                site.w.put(cx, y, cz, "wall_torch", facing=_FACE[(dx, dz)])
                n += 1
                break
    return n


def _meet(j0: int, spin: int, jt: int, first: int) -> int:
    """The first half-step at or past `first` whose sector is the one pointing at the tail."""
    for k in range(first, first + 8):
        if (j0 + spin * k) % 8 == jt:
            return k
    raise ValueError("no sector points at the tail")   # unreachable: eight sectors, eight tries


def build_twinspiral(cfg: dict, donors=None) -> Canvas:
    p = {**TWINSPIRAL, **cfg}
    ctx = Ctx(p["under"]) if p.get("under") else None
    w = World()
    site = _Site(ctx, w)
    seed = int(p["seed"])
    deck = float(p["deck_surface"])
    deck_y = int(deck) - 1
    r_out = 1.0 + int(p["width"])
    r_tail = 2.0 + int(p["tail_width"])          # the tail winds round a 3x3 core
    arms = []
    for ai, pair in enumerate(p["pairs"]):
        tx, tz = (int(v) for v in pair["tail"])
        twins = []
        for side in ("a", "b"):
            px, pz = (int(v) for v in pair[side])
            x0, x1, z0, z1 = (int(v) for v in pair[side + "_hole"])
            hole = [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)]
            # the entry sector holds the notch: the twin's first tread is the alcove floor
            j0 = _sector((x0 + x1) - 2 * px, (z0 + z1) - 2 * pz)   # doubled: the centre is a corner
            jt = _sector(tx - px, tz - pz)                          # the hand-off points at the tail
            first_meet = 8 * int(p["meet_turns"]) - 1
            # SPIN IS MEASURED, NOT DECLARED: the top five half-steps need open sky, so take the
            # spin whose first turn keeps more of its treads off the deck's own cells
            best = None
            for spin in (1, -1):
                probe = World()
                s = _Site(ctx, probe)
                _post(s, px, pz, deck_y, deck_y - 8, p["post"], axis="y")
                r = _helix(s, (px, pz), j0, spin, deck - 0.5, 8, r_out, p, seed, f"{ai}{side}")
                score = (r["chain"], r["placed"])
                if best is None or score > best[0]:
                    best = (score, spin)
            spin = best[1]
            k_m = _meet(j0, spin, jt, first_meet)
            h_m = deck - 0.5 - 0.5 * k_m
            y_lo = _slab_at(h_m)[0]
            # the post FIRST: every tread anchors outward from it
            post_cells = _post(site, px, pz, deck_y + int(p["newel"]), y_lo, p["post"], axis="y")
            res = _helix(site, (px, pz), j0, spin, deck - 0.5, k_m + 1, r_out, p, seed,
                         f"{ai}{side}")
            if res["chain"] < len(res["wedges"]):
                raise ValueError(f"arm {ai} twin {side}: the flight breaks at half-step "
                                 f"{res['chain']} (surface {deck - 0.5 - 0.5 * res['chain']})")
            floor_ok = sum(1 for (x, z) in hole if w.has(x, _slab_at(deck - 0.5)[0], z))
            twins.append({"post": [px, pz], "spin": spin, "entry_sector": j0,
                          "meet_half": k_m, "meet_h": h_m, "treads": res["treads"],
                          "cells": res["placed"], "alcove_floor": floor_ok,
                          "dir": list(_DIRS[jt]), "post_cells": post_cells, "y_lo": y_lo})
        if twins[0]["meet_h"] != twins[1]["meet_h"]:
            raise ValueError(f"arm {ai}: the twins hand off at different heights "
                             f"({twins[0]['meet_h']} vs {twins[1]['meet_h']}); the layout must "
                             "be symmetric about the tail post")
        h_m = twins[0]["meet_h"]
        # BRIDGES: from the hand-off wedge's tip straight to the landing's edge, half a step
        # down per cell; the landing sits one more half step down
        h_land = None
        bridge_cells = []
        for t in twins:
            px, pz = t["post"]
            dx, dz = t["dir"]
            dist = max(abs(tx - px), abs(tz - pz))
            h = h_m
            for r in range(int(r_out) + 1, dist - 1):
                h -= 0.5
                bridge_cells.append((px + dx * r, pz + dz * r, h))
            hl = h - 0.5
            if h_land is not None and hl != h_land:
                raise ValueError(f"arm {ai}: bridges arrive at {h_land} and {hl}")
            h_land = hl
        if h_land != math.floor(h_land):
            raise ValueError(f"arm {ai}: the landing would be a slab course ({h_land}); move "
                             "the posts or the tail so the bridges arrive on a whole block")
        y_land = int(h_land) - 1
        # THE CORE: the landing is the top of a solid 3x3 stone-brick newel that carries the
        # single stair below it - every tread of the tail touches it, so nothing under the
        # landing depends on a ring cell the landing's own headroom has taken away
        n_tail = 2 * int(p["tail_courses"]) - 1   # odd: the last tread is a bottom slab, so
                                                  # the pad half a step below it is FULL STONE
        h_pad = h_land - 0.5 * n_tail - 0.5
        y_pad = int(h_pad) - 1
        core = 0
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                core += _post(site, tx + dx, tz + dz, y_land, y_pad, p["landing"])
        # the log from the spoke down onto the landing: the design's anchor to the deck
        hang = _post(site, tx, tz, deck_y - 1, y_land + 1, p["tail_post"], axis="y")
        bridges = 0
        for (bx, bz, bh) in bridge_cells:
            if _surface(site, bx, bh, bz, p):
                bridges += 1
                # A BRIDGE SLAB AND THE LANDING ONE COURSE DOWN ARE DIAGONAL NEIGHBOURS:
                # walkable, and not 6-connected. The column under the slab is the beam - and
                # it runs the core's full height, so the core is a 3x5 pier whose END faces
                # the tail's north and south wedges lean on. As a single block it took the
                # inner cell of those wedges and gave them nothing to anchor to instead.
                if bh != math.floor(bh):
                    _post(site, bx, bz, _slab_at(bh)[0] - 1, y_pad, p["landing"])
        # THE TAIL. Start and spin are measured: the bridges and hand-off wedges sit over the
        # tail's north and south sectors and take their headroom for the first few half-steps,
        # so a start that turns into them first laid an empty sector, and the walk died there.
        # Every start and spin is tried over the first turn; ties go to the side with the least
        # deck over it, the open side.

        def deck_over(d):
            return sum(1 for r in range(1, int(r_tail) + 3)
                       if not site.world_free(tx + d[0] * r, deck_y, tz + d[1] * r))
        best = None
        for j_try in range(8):
            for tspin in (1, -1):
                probe = World()
                probe.cells = dict(w.cells)          # everything standing so far is an obstacle
                r = _helix(_Site(ctx, probe), (tx, tz), j_try, tspin, h_land - 0.5, 8, r_tail,
                           p, seed, f"{ai}t", r_in=1.5)
                # the first tread must step off the landing's own edge
                edge = [(tx + dx, tz + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)]
                onto = bool(r["wedges"] and _adjacent(edge, r["wedges"][0]))
                score = (onto, r["chain"], r["placed"], -deck_over(_DIRS[j_try]))
                if best is None or score > best[0]:
                    best = (score, j_try, tspin)
        _, j_tail, tail_spin = best
        tail = _helix(site, (tx, tz), j_tail, tail_spin, h_land - 0.5, n_tail, r_tail,
                      p, seed, f"{ai}t", r_in=1.5)
        if tail["chain"] < n_tail:
            raise ValueError(f"arm {ai}: the tail breaks at half-step {tail['chain']} "
                             f"(surface {h_land - 0.5 - 0.5 * tail['chain']})")
        # the bottom pad: the next three sectors at the pad's height, as full blocks
        by = _ring((tx, tz), 1.5, r_tail)
        pad = 0
        for extra in range(3):
            j = (j_tail + tail_spin * (n_tail + extra)) % 8
            for (x, z, r) in by[j]:
                if site.headroom(x, h_pad, z) and site.anchored(x, y_pad, z) and \
                        _surface(site, x, h_pad, z, p):
                    pad += 1
        # torches: on the twin posts' open faces, and on the core's
        for t in twins:
            out = (-t["dir"][0], -t["dir"][1])
            t["torches"] = _torches(site, t["post"][0], t["post"][1], deck_y, t["y_lo"],
                                    int(p["torch_every"]), out)
            t.pop("y_lo")
        start = _DIRS[j_tail] if _DIRS[j_tail] in _FACE else (_DIRS[j_tail][0], 0)
        tail_torches = _torches(site, tx, tz, y_land - 1, y_pad, int(p["torch_every"]), start,
                                reach=2)
        arms.append({"tail": [tx, tz], "meet_h": h_m, "landing_h": h_land, "core": core,
                     "hang": hang, "bridges": bridges, "tail_cells": tail["placed"],
                     "tail_treads": tail["treads"], "tail_spin": tail_spin,
                     "tail_start": list(_DIRS[j_tail]), "pad": pad, "pad_h": h_pad,
                     "torches": tail_torches, "twins": twins})
    return w.canvas({"kind": "twinspiral", "deck_surface": deck, "arms": arms})
