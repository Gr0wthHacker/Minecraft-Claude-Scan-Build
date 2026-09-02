"""MEASURE THE ATTRACTIONS AGAINST THE GROUND THAT IS ACTUALLY SHIPPED.

`tools/park_lots.py` answers "what lawn does the grid leave", by REBUILDING the design from its
config. This answers the three questions that come after it, and it reads the SHIPPED LITEMATIC
rather than regenerating - so what it reports is what is on disk and what would be placed.

    does the attraction FIT its lot                      --lots
    can it be REACHED and ENTERED, from which street     --access
    do the paths end well, and are they symmetric        --paths
    are the intersections lit symmetrically              --lamps

`render3d` draws a fence, a wall, a rod and iron bars all as full cubes and has hidden six faults
on this park already, so every number here is counted off the block list at y=0..3.

    python tools/park_attractions.py            # all four
    python tools/park_attractions.py --lamps    # just the lamp schedule
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

sys.path.insert(0, ".")
from mcbuild import schem                       # noqa: E402
from tools.park_lots import PLACEMENT, NOT_A_LOT  # noqa: E402

SHIPPED = "out/Park Ways.litematic"
WORLD = "park_final.world.json"

LAWN = "moss_block"
#: the shaft of each land's own lamp, read at y=3 - the one course every lamp design has a mast in
#: and no rim post reaches (a rim post is y1-y2 only).
MASTS = {"lightning_rod", "dark_oak_fence", "polished_blackstone_brick_wall"}

#: the street schedule, as `configs/park_ways.yaml` declares it. Read here rather than parsed out
#: of the config so this tool says which street a measured cell IS - the config says where they go.
SPINE_V, SPINE_HALF = 12, 6              # V6-18,  verge lamp lines V4 and V20
PROM_V, PROM_HALF = 125, 2               # V123-127, verge lamp lines V121 and V129
PROM_GAPS = [(98, 169), (264, 337), (470, 522)]
SERVICE_V, SERVICE_HALF = 155, 1         # V154-156
RIM_V = 170
PLAZA_HALF = 11
#: (land, U, avenue half). The avenue's own verge is half+1 out; the spine's and promenade's is 2.
AVENUES = [("frontier", 43, 2), ("frontier", 96, 1),
           ("midway", 260, 3), ("midway", 341, 3),
           ("prismworks", 468, 1), ("prismworks", 524, 1)]
THRESHOLDS = [171, 213, 386, 428]
WALKS = [("midway walk 1", 74, 1, 215, 257), ("midway walk 2", 77, 1, 344, 384),
         ("prism walk", 79, 1, 469, 523)]
CIRCUS = (125, 235, 13, 5)               # v, u, r, ring  -> island radius r-ring
HERON_LOT = (34, 174, 60, 210)           # feature lot v0,u0,v1,u1

#: THE HEADLINE RIDES AND THE ARRIVAL PIECES. `park_final.world.json` has no Big Wheel, Haunted
#: Manor, Ghost Train or Plummet module - the ferris wheel in this programme is the SKY LIFT, whose
#: parts are `gen: bigwheel, kind: wheel`, and whose own signage calls it "THE BIG WHEEL".
MAJOR = ["Trailhead Gate", "Prospecting Porch", "Mine Coaster", "Mining Square", "Boomtown Spine",
         "Signal Heron", "Arrival Court", "Carousel Court", "Sky Lift", "Skill Arcade",
         "Wyrm's Crossing", "Foundry Gate", "Prism Array", "Resonance Vault", "Prism Ascent",
         "Forge Deck"]


# ---------------------------------------------------------------------------- reading the ship
def read():
    """(ground [V,U] of block names, paved mask, lamp mast list) off the SHIPPED litematic."""
    m = schem.load(SHIPPED)
    names = np.array([n.split(":")[-1].split("[")[0] for n in m.names], dtype=object)
    ground = names[m.ids[0]].T                      # [y,z,x] -> [V,U]
    y3 = names[m.ids[3]].T
    lv, lu = np.nonzero(np.isin(y3, list(MASTS)))
    lamps = [(int(a), int(b)) for a, b in zip(lv, lu)]
    paved = ground != LAWN
    for a, b in lamps:                              # a lamp's own FOOTING replaces the lawn under
        paved[a, b] = False                         # it; a footing is not a street
    return ground, paved, lamps


def modules():
    d = json.load(open(WORLD))
    return {m["name"]: m for m in d["modules"]}


def occupancy(mods):
    return {n: (v, u, mods[n]["footprint"][0], mods[n]["footprint"][1])
            for n, (v, u) in PLACEMENT.items()}


def prom_open(u: int) -> bool:
    return not any(a <= u <= b for a, b in PROM_GAPS)


def street_at(v: int, u: int) -> str:
    """Which declared street a paved cell belongs to. The answer a lot table cannot give."""
    if SPINE_V - SPINE_HALF <= v <= SPINE_V + SPINE_HALF:
        return "spine"
    if PROM_V - PROM_HALF <= v <= PROM_V + PROM_HALF:
        return "back promenade"
    if SERVICE_V - SERVICE_HALF <= v <= SERVICE_V + SERVICE_HALF:
        return "service lane"
    if v == RIM_V:
        return "rim edge"
    for land, au, ah in AVENUES:
        if abs(u - au) <= ah:
            return f"{land} avenue U{au}"
    for tu in THRESHOLDS:
        if abs(u - tu) <= 1:
            return f"threshold U{tu}"
    for nm, wv, wh, u0, u1 in WALKS:
        if abs(v - wv) <= wh and u0 <= u <= u1:
            return nm
    if (v - CIRCUS[0]) ** 2 + (u - CIRCUS[1]) ** 2 <= (CIRCUS[2] + 0.5) ** 2:
        return "circus ring"
    if v <= SPINE_V + PLAZA_HALF:
        return "spine plaza"
    return "unattributed paving"


# ---------------------------------------------------------------------------- 1. the lots
def lots(ground, paved, mods, occ):
    """For each module: the lawn rectangle its placement corner actually commands."""
    lawn = ground == LAWN
    print(f"{'attraction':24} {'declared':>9} {'at V,U':>9} {'lot at that corner':>19}  verdict")
    for nm, (v, u, dv, du) in sorted(occ.items(), key=lambda kv: (kv[1][1], kv[1][0])):
        # DEPTH AND WIDTH MEASURED INDEPENDENTLY, or one failure hides the other.
        deep = 0
        while v + deep < lawn.shape[0] and lawn[v:v + deep + 1, u:u + du].all():
            deep += 1
        # THE WIDTH IS MEASURED AT THE DEEPEST DEPTH THE CORNER ACTUALLY REACHES, not at the
        # declared one. Probed at a depth that is already blocked, every shortfall reports as
        # "46 WIDE short" for a lot that is 47 wide and merely 14 shallow - a report nobody
        # can act on. This is the same rule `park_lots.verify` states.
        use = max(deep, 1)
        wide = 0
        while u + wide < lawn.shape[1] and lawn[v:v + use, u:u + wide + 1].all():
            wide += 1
        ok = deep >= dv and wide >= du
        note = "fits" if ok else " ".join(filter(None, [
            f"{dv - deep} DEEP short" if deep < dv else "",
            f"{du - wide} WIDE short" if wide < du else ""]))
        # a footprint that leaves the lawn is one thing; one that crosses a STREET or the protected
        # rim is another, and the second is a rule break rather than a shortfall.
        over = paved[v:v + dv, u:u + du]
        hits = sorted({street_at(v + a, u + b) for a, b in zip(*np.nonzero(over))})
        rim = v + dv - 1 >= RIM_V
        star = f"  [crosses {', '.join(hits)}]" if hits else ""
        star += "  [ENTERS THE PROTECTED RIM V170-199]" if rim else ""
        print(f"{nm:24} {dv:4}x{du:<4} {v:4},{u:<4} {deep:8} x {wide:<8}  {note}{star}")


# ---------------------------------------------------------------------------- 2. access
def access(ground, paved, lamps, mods, occ):
    """Every public entry: what is in front of it, which street, how far, and what is in the way."""
    print(f"{'attraction':24} {'entry V,U':>10} {'street it addresses':22} {'gap':>4}  obstruction")
    for nm, (v, u, dv, du) in sorted(occ.items(), key=lambda kv: (kv[1][1], kv[1][0])):
        m = mods[nm]
        ent = ([a for a in m["anchors"] if a["kind"] == "entry"]
               or [a for a in m["anchors"] if a["kind"] == "visual_front"])
        if not ent:
            print(f"{nm:24} {'-':>10}  no entry anchor")
            continue
        a = ent[0]
        ev, eu = v + a["position"][0], u + a["position"][2]
        # AN ENTRY FACES LOW V ("west" in the WorldSpec): the spine is on that side of every column.
        blocker = next((n2 for n2, (x, y, e, f) in occ.items()
                        if n2 != nm and x <= ev - 1 < x + e and y <= eu < y + f), None)
        k, st = 1, None
        while k <= 24 and ev - k >= 0:
            if paved[ev - k, eu]:
                st = street_at(ev - k, eu)
                break
            k += 1
        near = [p for p in lamps if abs(p[0] - ev) <= 5 and abs(p[1] - eu) <= 3]
        why = ""
        if blocker:
            why = f"THE BACK OF {blocker.upper()} IS IN FRONT OF THIS DOOR"
        elif st is None:
            why = "no paving within 24 courses of the door"
        elif near:
            why = f"lamp mast {near[0]} stands in the approach"
        print(f"{nm:24} {ev:5},{eu:<4} {(st or '-'):22} {(k if st else 0):4}  {why}")


# ---------------------------------------------------------------------------- 3. the paths
def _components(mask):
    from collections import deque
    sv, su = mask.shape
    seen = np.zeros_like(mask)
    out = []
    for x in range(sv):
        for z in range(su):
            if mask[x, z] and not seen[x, z]:
                q, n = deque([(x, z)]), 0
                seen[x, z] = True
                while q:
                    a, b = q.popleft()
                    n += 1
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        e, f = a + da, b + db
                        if 0 <= e < sv and 0 <= f < su and mask[e, f] and not seen[e, f]:
                            seen[e, f] = True
                            q.append((e, f))
                out.append(n)
    return sorted(out, reverse=True)


def paths(ground, paved):
    """Dead ends, connectivity, and mirror symmetry - measured, not looked at."""
    walk = paved.copy()
    walk[RIM_V, :] = False          # the rim course is a dressed edge, not a route
    sv, su = walk.shape

    comps = _components(walk)
    print(f"paving: {sum(comps)} walkable cells in {len(comps)} component(s) - "
          f"{comps[:4]}")

    # A TERMINATION IS A FACE WHOSE CORRIDOR IS DEEPER THAN THE FACE IS WIDE. Without that test the
    # long SIDE of every street reports as an end, which is 335 findings and no signal.
    print("\nstreet terminations (face >=3 wide, corridor deeper than the face, not at the "
          "envelope edge):")
    found = 0
    for nm, (dx, dz) in {"+V": (1, 0), "-V": (-1, 0), "+U": (0, 1), "-U": (0, -1)}.items():
        perp = (0, 1) if dx else (1, 0)
        face = np.zeros_like(walk)
        for x in range(sv):
            for z in range(su):
                if walk[x, z]:
                    e, f = x + dx, z + dz
                    if not (0 <= e < sv and 0 <= f < su) or not walk[e, f]:
                        face[x, z] = True
        seen = np.zeros_like(face)
        for x in range(sv):
            for z in range(su):
                if not face[x, z] or seen[x, z]:
                    continue
                run, a, b = [], x, z
                while 0 <= a < sv and 0 <= b < su and face[a, b] and not seen[a, b]:
                    seen[a, b] = True
                    run.append((a, b))
                    a, b = a + perp[0], b + perp[1]
                L = len(run)
                ds = []
                for px, pz in run:
                    n = 0
                    while (0 <= px - dx * n < sv and 0 <= pz - dz * n < su
                           and walk[px - dx * n, pz - dz * n]):
                        n += 1
                    ds.append(n)
                D = int(np.median(ds))
                xs = [q[0] for q in run]
                zs = [q[1] for q in run]
                if min(xs) == 0 or max(xs) == sv - 1 or min(zs) == 0 or max(zs) == su - 1:
                    continue
                if L >= 3 and D > L:
                    kind = ("plaza rim at the park's front edge" if max(xs) <= 2 else
                            "circus island edge" if 110 <= min(xs) <= 140 and 220 <= min(zs) <= 250
                            else "*** STUB - ends in open lawn ***")
                    print(f"  {nm} {L:3} wide, corridor {D:4} deep   "
                          f"V{min(xs)}-{max(xs)} U{min(zs)}-{max(zs)}   {kind}")
                    found += 1
    print(f"  {found} terminations")

    print("\nmirror symmetry (geom = paved/lawn mismatch across the axis; "
          "material = block name mismatch):")

    def mv(centre, half, u0, u1, label):
        g = mm = n = 0
        for d in range(1, half + 1):
            for u in range(u0, u1 + 1):
                a, b = centre - d, centre + d
                n += 1
                if walk[a, u] != walk[b, u]:
                    g += 1
                elif walk[a, u] and ground[a, u] != ground[b, u]:
                    mm += 1
        print(f"  {label:38} {n:6} pairs  geom {g:5}  material {mm:5}")

    def mu(centre, half, v0, v1, label):
        g = mm = n = 0
        for d in range(1, half + 1):
            for v in range(v0, v1 + 1):
                a, b = centre - d, centre + d
                n += 1
                if walk[v, a] != walk[v, b]:
                    g += 1
                elif walk[v, a] and ground[v, a] != ground[v, b]:
                    mm += 1
        print(f"  {label:38} {n:6} pairs  geom {g:5}  material {mm:5}")

    mv(SPINE_V, SPINE_HALF, 0, su - 1, "spine V6-18 about V12")
    mv(PROM_V, PROM_HALF, 0, su - 1, "promenade V123-127 about V125")
    mv(SERVICE_V, SERVICE_HALF, 0, su - 1, "service lane V154-156 about V155")
    for land, au, ah in AVENUES:
        mu(au, ah, SPINE_V, SERVICE_V + 1, f"{land} avenue U{au} about its own axis")
    for land, au, ah in AVENUES:
        mu(au, PLAZA_HALF, 1, 23, f"plaza U{au} mirrored in U")
        mv(SPINE_V, PLAZA_HALF, au - PLAZA_HALF, au + PLAZA_HALF, f"plaza U{au} mirrored in V")
    mu(CIRCUS[1], CIRCUS[2], CIRCUS[0] - CIRCUS[2], CIRCUS[0] + CIRCUS[2], "circus mirrored in U")
    mv(CIRCUS[0], CIRCUS[2], CIRCUS[1] - CIRCUS[2], CIRCUS[1] + CIRCUS[2], "circus mirrored in V")

    print("\njunction type at every avenue crossing of the back promenade:")
    for land, au, ah in AVENUES:
        w, e = bool(walk[PROM_V, au - 8]), bool(walk[PROM_V, au + 8])
        print(f"  {land:10} U{au:<4}  promenade west={w!s:5} east={e!s:5}  "
              f"-> {'crossroads' if w and e else 'T-JUNCTION (the promenade gap)'}")


# ---------------------------------------------------------------------------- 4. the lamps
def junctions():
    """Every place two declared streets cross: (label, verge V lines, junction U, minimum setback).

    THE SETBACK IS THE CROSSED STREET'S OWN VERGE OFFSET, PROBED OUTWARD until all four cells are
    clear - which is how the shipped generator does it, and it is right: the thing that has to be
    cleared is a round plaza, and "where does a disc of radius r stop covering the line at depth d"
    is arithmetic that is correct until somebody changes the plaza's shape.
    """
    out = []
    for land, au, _ah in AVENUES:
        out.append((f"spine x {land} avenue U{au}", (4, 20), au, SPINE_HALF + 2))
        out.append((f"promenade x {land} avenue U{au}", (121, 129), au, PROM_HALF + 2))
    for tu in THRESHOLDS:
        # A THRESHOLD IS A STREET AND CROSSES BOTH. Neither the spine nor the promenade pass is
        # given one by the shipped generator, because it walks `avenues` and a threshold is not
        # in that list - which is exactly why these are the crossings still unlit.
        out.append((f"promenade x threshold U{tu}", (121, 129), tu, PROM_HALF + 2))
        # ...and only the SOUTH half of the spine, because a threshold runs V12-156: it leaves the
        # spine at its own centre line, so there is no north quadrant to light and the symmetric
        # answer is a PAIR on V20 rather than a quartet.
        out.append((f"spine x threshold U{tu} (pair, V20 only)", (20,), tu, SPINE_HALF + 2))
    out.append(("the Midway Circus", (121, 129), CIRCUS[1], CIRCUS[2]))
    return out


def lamp_audit(paved, lamps):
    lampset = set(lamps)
    from collections import Counter
    print("lamp masts, by the V line they stand on:")
    for v, n in sorted(Counter(a for a, _ in lamps).items()):
        us = sorted(b for a, b in lamps if a == v)
        print(f"  V{v:<4} {n:3}  U {us[0]}..{us[-1]}")

    print("\nWHAT STANDS AT EACH JUNCTION NOW, as an offset in U from the junction centre.")
    print("A symmetric junction is four lamps at (-k, +k) on each of two lines. "
          "Anything else is what 'weird, non symmetric' looks like as a number.\n")
    print(f"{'junction':40} {'line':>5}  west      east")
    total = matched = 0
    for label, lines, ju, _minoff in junctions():
        for vl in lines:
            near = sorted((b - ju) for a, b in lamps if a == vl and abs(b - ju) <= 16)
            w = [d for d in near if d < 0]
            e = [d for d in near if d > 0]
            total += 2
            pair = bool(w and e and abs(w[-1]) == e[0])
            matched += 2 if pair else 0
            print(f"{label:40} V{vl:<4}  {str(w[-1]) if w else '-':9} "
                  f"{str(e[0]) if e else '-':9} {'PAIRED' if pair else ''}")
    print(f"\n  {matched} of {total} quadrants have a mirror partner on their own line")

    print("\nTHE RULE, and every coordinate it produces: one mast per quadrant at the crossing of")
    print("the two streets' own verge lines, pushed out by ONE setback shared by all of them -")
    print("so a junction is symmetric about both its axes or it carries no lamp at all.\n")
    todo = 0
    for label, lines, ju, minoff in junctions():
        k = minoff
        while k < minoff + 26 and any(
                paved[vl, ju + k] or paved[vl, ju - k] for vl in lines):
            k += 1
        cells = [(vl, ju + s * k) for vl in lines for s in (-1, 1)]
        state = ["already" if c in lampset else ("PAVED" if paved[c] else "free") for c in cells]
        todo += sum(s == "free" for s in state)
        print(f"  {label:42} setback {k:2}  " +
              "  ".join(f"({a},{b}){'*' if s == 'already' else ('!' if s == 'PAVED' else '')}"
                        for (a, b), s in zip(cells, state)))
    print(f"\n  * = a mast already stands there   ! = paved, would be refused")
    print(f"  {todo} masts would have to be added to make every junction symmetric")

    # A RUN IS ALSO A THING THAT CAN BE ASYMMETRIC. An avenue's own posts alternate sides down
    # its length, which is a real street idiom - until one station is dropped and two consecutive
    # posts end up on the same side, which is not.
    print("\navenue run lamps, as an offset from the avenue's own axis:")
    for land, au, ah in AVENUES:
        run = [(v, b - au) for v, b in sorted(lamps)
               if v in (29, 51, 73, 95, 117, 139) and abs(b - au) <= 6]
        sides = [1 if d > 0 else -1 for _v, d in run]
        broken = [i for i in range(1, len(sides)) if sides[i] == sides[i - 1]]
        note = ("alternates cleanly" if not broken else
                f"*** two consecutive posts on the SAME side at V{run[broken[0] - 1][0]} "
                f"and V{run[broken[0]][0]} ***")
        print(f"  {land:10} U{au:<4} {run}  {note}")


def main():
    ap = argparse.ArgumentParser()
    for f in ("lots", "access", "paths", "lamps"):
        ap.add_argument(f"--{f}", action="store_true")
    a = ap.parse_args()
    every = not (a.lots or a.access or a.paths or a.lamps)
    ground, paved, lamps = read()
    mods = modules()
    occ = occupancy(mods)
    if a.lots or every:
        print("=" * 100 + "\n1. THE LOTS\n" + "=" * 100)
        lots(ground, paved, mods, occ)
    if a.access or every:
        print("\n" + "=" * 100 + "\n2. ACCESS\n" + "=" * 100)
        access(ground, paved, lamps, mods, occ)
    if a.paths or every:
        print("\n" + "=" * 100 + "\n3. THE PATHS\n" + "=" * 100)
        paths(ground, paved)
    if a.lamps or every:
        print("\n" + "=" * 100 + "\n4. THE LAMPS\n" + "=" * 100)
        lamp_audit(paved, lamps)
    missing = sorted(set(mods) - set(PLACEMENT) - NOT_A_LOT)
    if missing:
        print(f"\nNOT PLACED BY tools/park_lots.PLACEMENT: {', '.join(missing)}")


if __name__ == "__main__":
    main()
