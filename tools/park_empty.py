"""THE EMPTY-GROUND AUDIT: where the park is bare, how dead it is, and whether dressing it broke
anything.

    python tools/park_empty.py                          the inventory
    python tools/park_empty.py --with "PF Park Green"    ...with a dressing pass composited
    python tools/park_empty.py --map out/empty.png       and a plan of it
    python tools/park_empty.py --walk                    does the planting cut a route?

WHY THIS EXISTS. Every check this park has measures a design against the world: is the state
legal, is it supported, does it collide, is it affordable. **Not one of them asks whether the
ground BETWEEN the designs is finished**, and that is the question a visitor answers with their
eyes the moment they walk in. This project has the standard written down already, about the
island: *"the plate has no dead ground - every walkable cell is within 4 blocks of something
built or planted, median 0"*. It had simply never been pointed at the park.

WHAT IT MEASURES

    BARE LAWN   a column whose ground course is `moss_block` and which carries nothing above
                it but air and the lawn's own moss trim. Paving is not bare, and neither is a
                tuft of grass: the standard is "built OR PLANTED".
    OPENNESS    a bare column's distance, in the plane, to the nearest column that is NOT bare.
                This is the number that separates a two-cell verge beside a kerb - which is
                DESIGNED lawn and wants nothing - from the middle of a forty-cell field, which is
                a hole. It is also what `gen/parkgreen.py` drives its density from, so the tool
                that finds the problem and the pass that fixes it cannot disagree about it.

A COLUMN PAST THE CAPTURE IS OPEN, NOT BUILT. The lattice is the plot: what is past its edge is
sky, and calling it built would make the park's own outer courses measure as crowded.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, deque

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import schem                                        # noqa: E402

PARK = "out/Park Complete.litematic"
PLANE_Y = 202                       # the course `Park Ways` paves; a build stands on 203
SV, SU = 200, 600                   # the lattice

#: WHAT DOES NOT COUNT AS SOMETHING BEING HERE. Air, and the lawn's own moss trim, which
#: `Park Ways` lays as part of the lawn rather than as dressing on it.
#:
#: **A TUFT OF GRASS COUNTS.** The standard this is measured against is the island's own -
#: *"every walkable cell within 4 blocks of something built OR PLANTED"* - so a flower, a fern
#: or a shrub is a thing, exactly as a wall is. An earlier draft of this file put every small
#: plant in here on the reasoning that dressing is what the audit exists to ADD, and the two
#: readings then disagreed by three thousand columns: the same park measured 1,305 dead cells
#: through `--with` (which counts a design's columns whatever they hold) and 4,443 once that
#: design was SHIPPED and had to be recognised by its materials. One definition, or the tool
#: that finds the hole and the pass that fills it are talking about different parks.
BARE_ABOVE = {"air", "cave_air", "void_air", "moss_carpet"}

LANDS = [("frontier", 0, 169), ("claim reach", 170, 214), ("midway", 215, 384),
         ("prism reach", 385, 429), ("prismworks", 430, 599)]
#: The depth programme, off `PARK_GRID_PLAN.md`. V171-199 is the declared "protected rim and void
#: reserve - 0 paved cells, asserted", so its emptiness is a rule rather than an oversight.
BANDS = [("threshold", 0, 23), ("public", 24, 127), ("exit", 128, 151),
         ("service", 152, 169), ("rim", 170, 199)]


def land_of(u):
    return next((n for n, a, b in LANDS if a <= u <= b), "?")


def band_of(v):
    return next((n for n, a, b in BANDS if a <= v <= b), "?")


def origin_of(path):
    return json.load(open(os.path.splitext(path)[0] + ".scan.json"))["origin"]


def masks(extra=(), without=()):
    """(bare, built) - both [U, V] over the whole lattice.

    `extra` composites a design that is not shipped yet. `without` REMOVES one that is.

    **BOTH WORK ON THE BLOCKS, NOT ON THE COLUMNS.** An earlier draft stamped an `extra` design's
    columns as built whatever they held, which made `--with` and a shipped design disagree by
    every moss carpet the pass laid: the same planting measured one way before it landed and
    another way after. A design is composited exactly as the shipping pipeline composites it.

    **`without` IS WHAT STOPS THIS BEING A SNAPSHOT.** Once a dressing pass is shipped, the park
    contains it, so "before" and "after" measured off `Park Complete` are the same number and any
    test asserting an improvement fails the moment the improvement lands - which is the trap this
    repo has now recorded five times. A design's own cells are knowable exactly: they are in its
    own litematic. So the before state is DERIVED rather than remembered.
    """
    m = schem.load(PARK)
    o = origin_of(PARK)
    names = np.array([n.split(":")[-1] for n in m.names])
    plane = PLANE_Y - o["y"]
    ids = m.ids
    if without:
        ids = ids.copy()
        for path in without:
            g = schem.load(path)
            go = origin_of(path)
            ys, zs, xs = g.ids.nonzero()
            y = ys + go["y"] - o["y"]
            u = zs + go["z"] - o["z"]
            v = xs + go["x"] - o["x"]
            ok = ((y >= 0) & (y < ids.shape[0]) & (u >= 0) & (u < ids.shape[1])
                  & (v >= 0) & (v < ids.shape[2]))
            ids[y[ok], u[ok], v[ok]] = 0
    if extra:
        ids = ids if without else ids.copy()
        by_name = {n: i for i, n in enumerate(names)}
        for path in extra:
            g = schem.load(path)
            go = origin_of(path)
            gn = [n.split(":")[-1] for n in g.names]
            grow = np.array([by_name.get(n, -1) for n in gn])
            miss = sorted({n for n, i in zip(gn, grow) if i < 0} - {"air"})
            if miss:                                       # a block the park has never held
                names = np.concatenate([names, np.array(miss)])
                for k, n in enumerate(miss):
                    by_name[n] = len(names) - len(miss) + k
                grow = np.array([by_name.get(n, -1) for n in gn])
            ys, zs, xs = g.ids.nonzero()
            y = ys + go["y"] - o["y"]
            u = zs + go["z"] - o["z"]
            v = xs + go["x"] - o["x"]
            ok = ((y >= 0) & (y < ids.shape[0]) & (u >= 0) & (u < ids.shape[1])
                  & (v >= 0) & (v < ids.shape[2]))
            src = grow[g.ids[ys[ok], zs[ok], xs[ok]]]
            tgt = ids[y[ok], u[ok], v[ok]]
            ids[y[ok], u[ok], v[ok]] = np.where(tgt == 0, src, tgt)   # first writer wins
    is_ground = names[ids[plane]] == "moss_block"
    heavy = ~np.isin(names, list(BARE_ABOVE))
    occupied = heavy[ids[plane + 1:]].any(axis=0)
    bare = is_ground & ~occupied
    return bare, ~bare


def openness(built):
    """Plane distance from every column to the nearest built one. The park's own edge is sky."""
    INF = 1 << 20
    d = np.full(built.shape, INF, np.int32)
    d[built] = 0
    q = deque((int(a), int(b)) for a, b in zip(*np.nonzero(built)))
    while q:
        u, v = q.popleft()
        n = d[u, v] + 1
        for a, b in ((u + 1, v), (u - 1, v), (u, v + 1), (u, v - 1)):
            if 0 <= a < SU and 0 <= b < SV and d[a, b] > n:
                d[a, b] = n
                q.append((a, b))
    return d


def cores(bare, dist, floor=4):
    """Connected blobs of ground `floor` or more from anything - the holes, not the verges."""
    mask = bare & (dist >= floor)
    seen = np.zeros_like(mask)
    out = []
    for u0 in range(SU):
        for v0 in range(SV):
            if not mask[u0, v0] or seen[u0, v0]:
                continue
            q, cells = deque([(u0, v0)]), []
            seen[u0, v0] = True
            while q:
                u, v = q.popleft()
                cells.append((u, v))
                for a, b in ((u + 1, v), (u - 1, v), (u, v + 1), (u, v - 1)):
                    if 0 <= a < SU and 0 <= b < SV and mask[a, b] and not seen[a, b]:
                        seen[a, b] = True
                        q.append((a, b))
            us = np.array([c[0] for c in cells])
            vs = np.array([c[1] for c in cells])
            out.append({"n": len(cells), "u0": int(us.min()), "u1": int(us.max()),
                        "v0": int(vs.min()), "v1": int(vs.max()),
                        "land": land_of(int(np.median(us))), "band": band_of(int(np.median(vs))),
                        "maxd": int(max(dist[u, v] for u, v in cells))})
    out.sort(key=lambda r: -r["n"])
    return out


def report(bare, dist, label=""):
    d = dist[bare]
    print(f"\n{label}bare lawn {int(bare.sum()):,} of {SU * SV:,} columns "
          f"({100 * bare.sum() / (SU * SV):.1f}%)")
    print(f"  distance to the nearest built or planted thing: "
          f"median {np.median(d):.0f}, mean {d.mean():.2f}, MAX {int(d.max())}")
    for t in (3, 4, 6, 8, 10, 12):
        print(f"    more than {t:2d} away: {int((d > t).sum()):6,}")
    print(f"\n  {'':16}" + "".join(f"{b[0]:>13}" for b in BANDS) + f"{'total':>9}")
    tot = [0] * len(BANDS)
    for ln, u0, u1 in LANDS:
        row = [int((bare[u0:u1 + 1, v0:v1 + 1] & (dist[u0:u1 + 1, v0:v1 + 1] > 4)).sum())
               for _n, v0, v1 in BANDS]
        for i, n in enumerate(row):
            tot[i] += n
        print(f"  {ln:16}" + "".join(f"{n:>13,}" for n in row) + f"{sum(row):>9,}")
    print(f"  {'DEAD (>4)':16}" + "".join(f"{n:>13,}" for n in tot) + f"{sum(tot):>9,}")


def draw(bare, dist, path):
    from PIL import Image, ImageDraw
    img = np.zeros((SV, SU, 3), np.uint8)
    b, d = bare.T, dist.T
    img[~b] = (55, 57, 63)
    img[b & (d <= 1)] = (110, 140, 85)
    img[b & (d == 2)] = (150, 178, 105)
    img[b & (d == 3)] = (196, 206, 110)
    img[b & (d >= 4) & (d <= 5)] = (232, 198, 80)
    img[b & (d >= 6) & (d <= 7)] = (238, 150, 55)
    img[b & (d >= 8)] = (222, 70, 60)
    im = Image.fromarray(img).resize((SU * 2, SV * 2), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for v in (0, 6, 19, 24, 124, 128, 152, 155, 170, 187, 200):
        dr.line([(0, v * 2), (SU * 2, v * 2)], fill=(90, 120, 190))
    for _n, u0, _u1 in LANDS:
        dr.line([(u0 * 2, 0), (u0 * 2, SV * 2)], fill=(190, 90, 190))
    im.save(path)
    print(f"\nwrote {path}  (dark = built . green = verge . yellow-red = dead ground)")


# --------------------------------------------------------------------------- the walk


def walkable(extra=()):
    """Standable columns on the park's own surface, Y199-213 - `Nav.standable`'s rule.

    **PLANTING CAN WALL A LAWN, AND NOTHING ELSE IN THIS REPO WOULD SEE IT.** A hedge is a legal,
    supported, affordable, non-colliding run of leaves; two courses of it across a narrow lawn is
    also a fence. So the dressing has to be flooded, not just audited.
    """
    m = schem.load(PARK)
    o = origin_of(PARK)
    names = np.array([n.split(":")[-1] for n in m.names])
    passable = np.isin(names, ["air", "cave_air", "void_air", "moss_carpet", "short_grass",
                               "grass", "tall_grass", "fern", "large_fern", "dead_bush",
                               "poppy", "dandelion", "blue_orchid", "allium", "azure_bluet",
                               "oxeye_daisy", "cornflower", "lily_of_the_valley", "red_tulip",
                               "orange_tulip", "white_tulip", "pink_tulip", "vine",
                               "glow_lichen", "sweet_berry_bush"])
    y0, y1 = 199 - o["y"], 213 - o["y"]
    solid = np.zeros((y1 - y0 + 1, SU, SV), bool)
    sub = m.ids[y0:y1 + 1, :SU, :SV]
    solid[:, :sub.shape[1], :sub.shape[2]] = ~passable[sub]
    for path in extra:
        g = schem.load(path)
        go = origin_of(path)
        gn = np.array([n.split(":")[-1] for n in g.names])
        gp = np.isin(gn, ["air", "cave_air", "void_air", "moss_carpet", "short_grass", "grass",
                          "tall_grass", "fern", "large_fern", "poppy", "dandelion", "blue_orchid",
                          "allium", "azure_bluet", "oxeye_daisy", "cornflower",
                          "lily_of_the_valley", "red_tulip", "orange_tulip", "white_tulip",
                          "pink_tulip", "sweet_berry_bush"])
        ys, zs, xs = (~gp[g.ids]).nonzero()
        Y = ys + go["y"] - o["y"] - y0
        U = zs + go["z"] - o["z"]
        V = xs + go["x"] - o["x"]
        ok = (Y >= 0) & (Y < solid.shape[0]) & (U >= 0) & (U < SU) & (V >= 0) & (V < SV)
        solid[Y[ok], U[ok], V[ok]] = True
    # a cell you can stand IN: solid under, two clear courses
    stand = np.zeros(solid.shape, bool)
    stand[1:-1] = solid[:-2] & ~solid[1:-1] & ~solid[2:]
    return stand


def flood(stand, seed):
    seen = np.zeros(stand.shape, bool)
    y, u, v = seed
    q = deque([(y, u, v)])
    seen[y, u, v] = True
    while q:
        y, u, v = q.popleft()
        for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = u + du, v + dv
            if not (0 <= a < SU and 0 <= b < SV):
                continue
            for dy in (0, 1, -1):                 # a step up or down of one
                c = y + dy
                if 0 <= c < stand.shape[0] and stand[c, a, b] and not seen[c, a, b]:
                    seen[c, a, b] = True
                    q.append((c, a, b))
                    break
    return seen


def walk_check(extra):
    """Flood the surface with and without the dressing and report what the dressing cut off."""
    base = walkable()
    after = walkable(extra)
    ys, us, vs = np.nonzero(base[:, 290:311, 19:24])       # the spine behind the entry gate
    if not len(ys):
        print("\nwalk: no seed found on the spine - skipped")
        return
    seed = (int(ys[0]), int(us[0]) + 290, int(vs[0]) + 19)
    a = flood(base, seed)
    b = flood(after, seed)
    # A CELL THE DRESSING STANDS IN IS NOT CUT OFF, IT IS PLANTED - it stopped being standable
    # because a shrub is now in it. A cell that is STILL standable and no longer reachable is
    # the real finding: something has been walled in.
    lost = int((a & ~b & after).sum())
    planted = int((a & ~b & ~after).sum())
    print(f"\nwalk from the spine at U{seed[1]} V{seed[2]}:")
    print(f"  reachable before {int(a.sum()):,}   after {int(b.sum()):,}")
    print(f"  columns the planting OCCUPIES  {planted:,}   (expected - a shrub is not a hole)")
    print(f"  columns cut off behind it      {lost:,}"
          + ("   <-- a planting has walled something in" if lost else "   OK"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with", dest="extra", action="append", default=[],
                    help="a design name in out/ to composite on - one not shipped yet")
    ap.add_argument("--without", dest="drop", action="append", default=[],
                    help="a design name in out/ to REMOVE from the shipped park, so a pass that "
                         "has landed can still be measured against the ground it fixed")
    ap.add_argument("--map", help="write a plan of the result here")
    ap.add_argument("--cores", type=int, default=12, help="how many dead cores to list")
    ap.add_argument("--walk", action="store_true", help="flood the surface and check for walls")
    a = ap.parse_args()
    def _paths(names):
        out = [f"out/{n}.litematic" if not n.endswith(".litematic") else n for n in names]
        for p in out:
            if not os.path.exists(p):
                raise SystemExit(f"not shipped: {p}")
        return out

    extra, drop = _paths(a.extra), _paths(a.drop)
    if extra or drop:
        bare0, built0 = masks(without=drop)
        report(bare0, openness(built0), "BEFORE  ")
        bare, built = masks(extra)
        d = openness(built)
        report(bare, d, "AFTER   ")
    else:
        bare, built = masks()
        d = openness(built)
        report(bare, d)

    print(f"\nthe holes, {a.cores} biggest (4 or more from anything):")
    print(f"  {'cells':>7} {'land':13} {'band':10} {'V span':>11} {'U span':>13} {'worst':>6}")
    for r in cores(bare, d)[:a.cores]:
        print(f"  {r['n']:>7,} {r['land']:13} {r['band']:10} "
              f"{r['v0']:>4}-{r['v1']:<6} {r['u0']:>5}-{r['u1']:<7} {r['maxd']:>6}")
    if a.map:
        draw(bare, d, a.map)
    if a.walk:
        walk_check(extra)


if __name__ == "__main__":
    main()
