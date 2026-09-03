"""MEASURE THE GROUND THE GRID LEAVES.

A path layout is only as good as the LOTS between its paths. The previous park failed exactly
here: blocks came out 84 deep against buildings 20-50 deep, so everything was packed against
everything else and routes ran through buildings. Nothing measured it, so nothing caught it.

This measures every block of lawn `mcbuild.gen.parkways` leaves: its size, its land, its depth
band, the largest rectangle that actually fits inside it, and which of the park's real measured
footprints it can hold.

    python tools/park_lots.py                 the table
    python tools/park_lots.py --assign        ...and a greedy build -> lot assignment
    python tools/park_lots.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque

import numpy as np
import yaml

sys.path.insert(0, ".")
from mcbuild.gen import parkways  # noqa: E402

BANDS = [(0, 23, "threshold"), (24, 127, "public floor"), (128, 151, "exit/observation"),
         (152, 169, "service"), (170, 199, "rim reserve")]


def band_of(v: int) -> str:
    for a, b, n in BANDS:
        if a <= v <= b:
            return n
    return "?"


def params_from_config(path="configs/park_ways.yaml") -> dict:
    cfg = yaml.safe_load(open(path))
    for part in cfg["params"]["parts"]:
        if part.get("gen") == "parkways":
            return part["params"]
    raise SystemExit("no parkways part in config")


def surface(p: dict):
    """(lawn mask [V,U], canvas) - True where a cell is open lawn a building could stand on."""
    c = parkways.build(dict(p))
    sx, sz = c.sx, c.sz
    names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(c.palette)}
    lawn_ids = {i for i, n in names.items() if n == parkways.LAWN}
    top = c.ids[0]                                   # [z, x]
    lawn = np.isin(top, list(lawn_ids)).T            # -> [x, z] = [V, U]
    return lawn, c


def load_modules(path="park_final.world.json"):
    d = json.load(open(path))
    out = []
    for m in d["modules"]:
        fp = m["footprint"]
        out.append({"name": m["name"], "role": m["role"], "land": m.get("style", ""),
                    "v": fp[0], "u": fp[1], "at": m["at"], "area": fp[0] * fp[1]})
    return out


def components(mask: np.ndarray, vmin: int, vmax: int):
    """4-connected lawn blobs inside a V band."""
    sx, sz = mask.shape
    seen = np.zeros_like(mask)
    out = []
    for x0 in range(max(0, vmin), min(sx, vmax + 1)):
        for z0 in range(sz):
            if not mask[x0, z0] or seen[x0, z0]:
                continue
            q, cells = deque([(x0, z0)]), []
            seen[x0, z0] = True
            while q:
                x, z = q.popleft()
                cells.append((x, z))
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = x + dx, z + dz
                    if vmin <= a <= vmax and 0 <= b < sz and mask[a, b] and not seen[a, b]:
                        seen[a, b] = True
                        q.append((a, b))
            out.append(cells)
    return out


def _submask(cells):
    xs = [x for x, _ in cells]
    zs = [z for _, z in cells]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    sub = np.zeros((x1 - x0 + 1, z1 - z0 + 1), bool)
    for x, z in cells:
        sub[x - x0, z - z0] = True
    return sub, x0, z0


def max_rect(cells):
    """Largest axis-aligned rectangle of lawn inside a blob: (area, v, u, dv, du).

    A blob's AREA says nothing about whether a building fits in it - an L of 4,000 cells holds
    no 50x50. The rectangle is the only honest capacity number."""
    sub, x0, z0 = _submask(cells)
    best = (0, 0, 0, 0, 0)
    h = np.zeros(sub.shape[1], int)
    for i in range(sub.shape[0]):
        h = np.where(sub[i], h + 1, 0)
        stack = []
        for j in range(sub.shape[1] + 1):
            cur = int(h[j]) if j < sub.shape[1] else 0
            start = j
            while stack and stack[-1][1] >= cur:
                s, ht = stack.pop()
                if ht * (j - s) > best[0]:
                    best = (ht * (j - s), x0 + i - ht + 1, z0 + s, ht, j - s)
                start = s
            stack.append((start, cur))
    return best


def rect_fits(cells, dv: int, du: int):
    """Where does a dv x du rectangle fit in the blob? (v, u) of its corner, or None."""
    sub, x0, z0 = _submask(cells)
    if sub.shape[0] < dv or sub.shape[1] < du:
        return None
    h = np.zeros(sub.shape[1], int)
    for i in range(sub.shape[0]):
        h = np.where(sub[i], h + 1, 0)
        run = 0
        for j in range(sub.shape[1]):
            run = run + 1 if h[j] >= dv else 0
            if run >= du:
                return (x0 + i - dv + 1, z0 + j - du + 1)
    return None


#: WHERE EACH BUILD GOES, AS (V, U) OF ITS NEAR CORNER. This is the output of the whole exercise:
#: the grid exists to leave these rectangles, and `--verify` proves every cell of every one of
#: them is open lawn in the shipped ground layer. Footprints come from `park_final.world.json`;
#: nothing here edits that file. A module whose declared footprint does not fit is listed with the
#: depth or width it is short - see PARK_GRID_PLAN.md, which is written from this table.
PLACEMENT = {
    # --- Frontier -------------------------------------------------- col A  U0-39 (40 usable)
    "Trailhead Gate":         (24, 0),
    "Prospecting Porch":      (69, 0),
    # --- Frontier -------------------------------------------------- col B  U47-93 (47 usable)
    # **BOOMTOWN SPINE IS RETIRED.** Jack, three times: "they are visually great - but all serve
    # no actual defined purpose"; "i dont want a bunch of buildings to go into, this is just a
    # village then, thats opposite of what i asked for and is exactly what i complained on"; "we
    # can have a small amount of buildings, but the rest should be other things."
    #
    # It was the biggest lot in the land - 53 x 46 - and measured over the shipped park it held
    # **ZERO interactive blocks** across seven false-fronted shops. `PF Frontier Diggings` takes
    # the lot: a worked landscape with a trail, a working yard, two shafts and TWO shops cut into
    # its banks instead of seven standing on the lawn.
    #
    # **THE WALK IT CARRIED IS THE REASON THE REPLACEMENT EXISTS AT ALL.** `Park Ways` paves 0 of
    # this lot's 2,438 columns, so the route from the spine to Mining Square lived inside the
    # module: its boardwalk at world U68-70, meeting the ground layer's spur at V19-23 / U69-71
    # and the V77-79 cross walk. The diggings lays its trail on the same courses.
    #
    # Its config, its generator and `out/PF Boomtown Spine.litematic` are all kept as the record;
    # this table is the one thing that decides whether a module is placed.
    "Mining Square":          (80, 47),      # behind the new V77-79 cross walk; 41 declared
    "Assay and Prize Office": (130, 47),
    # --- Frontier -------------------------------------------------- col C  U99-169 (71 usable)
    "Mine Coaster":           (24, 99),
    "Works Yard":             (157, 125),    # 13 deep available against a declared 18
    # --- Claim Line reach ------------------------------------------ U174-210 (37 usable)
    # "Claim Line" is not here and needs no lot: PARK_FINAL_ARCHITECTED_PLAN calls the reach
    # "one safe, 5-wide causeway", which is the spine and the promenade running through it.
    "Signal Heron":           (34, 174),     # its own reserved garden, V34-60 U174-210
    # --- Midway ---------------------------------------------------- col A  U215-255 (41)
    # THE CAROUSEL TOOK THIS LOT AND THE ARRIVAL COURT CAME OUT. Jack: "i want to put the carousel
    # where currently there is a large rectangular building with an open center, just between the
    # welcome court and the heron; the building thats there can be saved but should be removed."
    #
    # The building was the Arrival Court - 44 x 35 of gateway, ticket hall, open court and turnstile
    # screen. `PF Entry Gate` was built later and does that job on the park's own axis, so this was
    # a SECOND front door standing in the first lot inside the park. Its config, its generator and
    # `out/PF Arrival Court.litematic` are all kept as the record; it is out of this table, which is
    # the one thing that decides whether a module is placed.
    #
    # AND IT IS NOT THE APPROACH. Column A is U215-255, off the U300 entrance axis - the wheel keeps
    # the centre, and "somewhere off to the left or right" is exactly where this is. It also puts the
    # carousel next to the Claim Lake and its heron, which is the reach a visitor walks up first.
    "Carousel Court":         (24, 215),      # 46 x 41 at diameter 39; the lot is 48 x 41
    "Snack Window":           (77, 215),
    # --- Midway ---------------------------------------------------- col B  U265-336 (72)
    # THE FERRIS WHEEL IS THE CENTRE ATTRACTION, so column B's front is cleared for the approach
    # to it and the carousel goes off to the side. Jack: "we want the ferris wheel to be the main
    # center attraction, lets put the carousel somewhere off to the left or right." The wheel
    # already straddles the park's own centre (V100, U300); what stood between it and the
    # entrance was the carousel.
    # COLUMN B IS THE WHEEL'S, AND ONLY THE WHEEL'S. The carousel used to sit behind it at (102, 266)
    # because at diameter 45 it was 47 WIDE and no other Midway column was wider than 41. Rebuilt at
    # 39 it is 41 wide and column A holds it, which is why it could move at all - the size was the
    # whole constraint. Front to back the column now reads: welcome court, the wheel, and V102-153
    # is open ground behind it.
    # SIXTY-ONE WIDE NOW, NOT FORTY-ONE, and still centred on the entrance axis U300. The two
    # flanks either side of the old lot measured 714 columns of bare moss EACH and nothing else -
    # Jack: "we dont want immediate large amounts of empty green" - and at U270-330 the court has
    # exactly the entry gate's own frontage, so the two read as one composition rather than as a
    # gate with a smaller thing behind it.
    "Welcome Court":          (24, 270),
    #: WHAT FILLS THE GAP THE CASCADE LEFT. 41 x 71 at the Cascade's own lot, so column B's depth
    #: schedule is unchanged: 56 + 41 + 9 + 22 + 2 = its own 130. See `configs/pf_midway_row.yaml`.
    "Midway Row":             (80, 266),
    # THE WHEEL MOVED BACK FIFTY BLOCKS (2026-09-03), and it is an improvement rather than a cost.
    # It crowns at Y276, 74 courses over the lawn; at V80 its ring centre stood 72 blocks from the
    # gate's doors, a 46 degree angle - you crane your neck and the whole wheel does not fit the
    # view - and there were SEVEN blocks between it and the back of the Welcome Court. At V130 it
    # is 122 blocks and 31 degrees: the whole wheel, from the moment you clear the gate.
    #
    # V130 IS THE PARK'S OWN GRID LINE, not a number picked to suit. It is where the exit and
    # observation band starts, and where every other lot in that band begins - Frontier Lookout
    # (130, 0), Forge Deck (130, 527).
    "Sky Lift":               (130, 266),     # THE CENTRE ATTRACTION, straight down the axis
    # ...and what the fifty blocks bought: the lot between the Welcome Court and the wheel.
    # "Midway Cascade":       (80, 266),      # 41 x 71 - WITHDRAWN, see below
    #
    # TWO FOUNTAINS ON ONE AXIS, FORTY BLOCKS APART. Jack: *"make sure we get rid of the other
    # fountain there, we should only have 1."* Measured off the shipped park, the Midway held
    # exactly two water designs and both were on U300 - the Welcome Court's basin at V51 (188
    # cells) and the Cascade at V80-116 (369). Walking in through the gate you met one and then
    # the other, which is the thing he first described as *"a center fountain, and then it just
    # leads to a bigger fountain."*
    #
    # THE COURT'S IS THE ONE THAT STAYS, because it is the one he asked for by name in the same
    # breath: *"the court should have a large fountain ideally sophisticated/intricate of
    # stone(s)."*
    #
    # THE CASCADE IS WITHDRAWN FROM PLACEMENT, NOT DELETED. Its config and its 2,096-block
    # artifact are untouched on disk, because it was built against a DIFFERENT instruction -
    # *"move the wheel back and lets fill the area between with something more interesting ...
    # it should instead be a big water fountain sculpture"* - and whoever owns that band needs
    # to see what was there before choosing what replaces it. **V80-120 x U266-336 is empty
    # ground now and that is 41 by 71 of it**, which is a decision for Jack rather than a hole
    # this pass should quietly fill.
    # --- Midway ---------------------------------------------------- col C  U346-384 (39)
    "Skill Arcade":           (24, 346),
    # THE PRIZE POINT IS BACK, and the reason it went is the reason it returns. It was dropped as
    # "1,666 blocks of shed with nothing in it" - true of what was standing then. It now carries
    # the highest show-front share in the park (39.7% colour and canvas against a land median
    # near 20) and a working redemption counter from `configs/pf_game_prize_point.yaml`, and the
    # Arcade's own sign already reads "prizes east". Dropping it would have orphaned a game, a
    # marquee and a sign, which is three references to a building nobody can reach.
    # AT V80, NOT V75. `park_final.world.json` says (75, 348) and V77-79 is the cross walk that
    # every second-rank building in this park stands behind - Mining Square keeps the same line.
    "Prize Point":            (80, 348),
    # "Sky Lift Sloth" hangs from the Sky Lift's own arch. It has no ground lot and needs none.
    # --- Wyrm's Crossing reach ------------------------------------- U389-426 (38 usable)
    # AT THE REACH'S OWN START. The full-resolution skull is 40 wide and the Prism Reach is
    # U385-429, forty-five columns - at U389 a 44-wide module runs to U432, three columns into
    # Prismworks. There is no slack: it starts where the reach does.
    "Wyrm's Crossing":        (24, 385),
    # --- Prismworks ------------------------------------------------ col A  U430-465 (36)
    "Foundry Gate":           (24, 430),
    # --- Prismworks ------------------------------------------------ col B and C
    # FOUR MODULES REMOVED FOR THE PRISM WELL (2026-09-03). Jack: "prism in its current
    # state is not a theme park, its a collection of buildings; this is a failure of
    # design." Prismworks v2 is one hundred-wide mouth cut through the deck at
    # (97590, 80815) with the descent hanging in it, and these four stood INSIDE it -
    # measured against the well's footprint, not guessed:
    #
    #     Prism Array       5,065 cells inside the mouth
    #     Resonance Vault   8,595   - the whole building
    #     Prism Ascent      5,758   - the 84-course spire, in the middle of the hole
    #     Forge Deck          332
    #
    # Cell-for-cell collision UNDERSTATES this and is the wrong test: the Ascent overlaps
    # the well by only 84 cells, because a tower standing in a hole barely touches its
    # collar. What matters is what is inside the mouth, because the mouth is a DIG.
    #
    # Foundry Gate and Service Gallery are measured CLEAR (0 cells inside) and stay: the
    # land keeps its threshold and its back-of-house. They are archived whole in
    # archive/prismworks_v1/ - see PRISMWORKS_V2_PLAN.md.
    "Service Gallery":        (157, 550),    # 13 deep available against a declared 18
}

#: RETIRED MODULES. Built, kept on disk as the record, and deliberately not placed. This is a
#: separate set from `NOT_A_LOT` on purpose: that one means "the grid already draws it", and
#: filing a retirement there would say a building exists somewhere it does not. A name here is a
#: DECISION with a reason, which is the standing rule for a retirement in this repo - a flag with
#: no reason beside it gets removed by whoever finds it inconvenient.
RETIRED = {
    #: 2026-09-03. `PF Entry Gate` was built after it and does the same job on the park's own axis,
    #: so this was a second front door standing in the first lot inside the park - 44 x 35 of
    #: gateway, ticket hall, open court and turnstile screen. The Carousel holds the lot now.
    #: `configs/pf_midway_arrival_court.yaml`, `midway_builds._arrival_court` and
    #: `out/PF Arrival Court.litematic` all stand.
    "Arrival Court",
}

#: MODULES THE GRID ALREADY IS, or that hang off another build. None of them wants a lot:
#: the six "Line" strips ARE the spine, the Claim Line IS the reach's causeway, the Welcome
#: Court IS the Midway's arrival plaza, and the Sloth hangs from the Sky Lift's own arch.
NOT_A_LOT = {"Frontier Line", "Midway Line", "Prismworks Line", "Frontier Reach Line",
             "Prism Reach Line", "Sky Lift Sloth", "Claim Line", "Welcome Court"}


def verify(p, mods, placement=PLACEMENT):
    """For every placed build: is every cell of its footprint open lawn? If not, by how much?"""
    lawn, _c = surface(p)
    sx, sz = lawn.shape
    rows = []
    by_name = {m["name"]: m for m in mods}
    for name, (v, u) in placement.items():
        m = by_name.get(name)
        if not m:
            rows.append((name, v, u, 0, 0, "NOT IN park_final.world.json"))
            continue
        dv, du = m["v"], m["u"]
        # DEPTH AND WIDTH MUST BE MEASURED INDEPENDENTLY OR ONE FAILURE HIDES THE OTHER. Probing
        # width at the DECLARED depth reports "41 wide short" for a lot that is merely 3 short,
        # because the depth probe had already failed - which is a report nobody can act on.
        # w[d] is the widest all-lawn run from this corner at depth d.
        maxd = min(dv, sx - v)
        w = []
        for d in range(1, maxd + 1):
            run = 0
            while u + run < min(sz, u + du + 20) and lawn[v:v + d, u + run].all():
                run += 1
            w.append(run)
        # ...and the pair reported has to be a REAL rectangle. Quoting the width at the declared
        # depth when that depth is blocked reports "46 wide short" for a lot that is 47 wide and
        # merely 14 shallow. `d_use` is the deepest this corner reaches at all; the width is the
        # width THERE.
        d_use = max(range(1, maxd + 1), key=lambda d: d * min(w[d - 1], du), default=0)
        wide_ok = w[d_use - 1] if d_use else 0
        deep_ok = max((d for d in range(1, maxd + 1) if w[d - 1] >= du), default=d_use)
        fits = d_use >= dv and wide_ok >= du
        note = "fits" if fits else " ".join(filter(None, [
            f"{dv - deep_ok} DEEP short" if deep_ok < dv else "",
            f"{du - wide_ok} WIDE short" if wide_ok < du else ""])) + \
            f"  (holds {d_use}x{wide_ok})"
        rows.append((name, v, u, dv, du, note))
    return rows


def land_of(u: int, lands) -> str:
    for L in lands:
        if L["u0"] <= u <= L["u1"]:
            return L["name"]
    for a, b in zip(lands, lands[1:]):
        if a["u1"] < u < b["u0"]:
            return f"{a['name']}|{b['name']}"
    return "?"


def measure(p, vmin=0, vmax=169, minarea=200):
    lawn, _c = surface(p)
    lands = p["lands"]
    reserved = p.get("feature_lots") or []
    rows = []
    for cells in components(lawn, vmin, vmax):
        if len(cells) < minarea:
            continue
        xs = [x for x, _ in cells]
        zs = [z for _, z in cells]
        area, rv, ru, dv, du = max_rect(cells)
        feat = [f["name"] for f in reserved
                if not (f["v1"] < min(xs) or f["v0"] > max(xs)
                        or f["u1"] < min(zs) or f["u0"] > max(zs))]
        rows.append({"v0": min(xs), "v1": max(xs), "u0": min(zs), "u1": max(zs),
                     "cells": len(cells),
                     "land": land_of((min(zs) + max(zs)) // 2, lands),
                     "band": band_of((min(xs) + max(xs)) // 2),
                     "rect": [dv, du], "rect_at": [rv, ru], "rect_area": area,
                     "fill": round(len(cells) / max(1, (max(xs) - min(xs) + 1)
                                                    * (max(zs) - min(zs) + 1)), 2),
                     "feature": feat, "cellset": cells})
    rows.sort(key=lambda r: -r["rect_area"])
    return rows


def assign(rows, mods):
    """Greedy: biggest build first into the tightest lot that still holds it."""
    out, used = [], {}
    for m in sorted(mods, key=lambda m: -m["area"]):
        if m["role"] == "path" and m["v"] <= 6:
            continue                       # the U-long "lines" ARE the spine
        best = None
        for i, r in enumerate(rows):
            if i in used or (m["land"] and m["land"] not in r["land"]):
                continue
            spot = rect_fits(r["cellset"], m["v"], m["u"])
            if spot and (best is None or r["rect_area"] < rows[best[0]]["rect_area"]):
                best = (i, spot)
        if best is None:
            out.append((m, None, None))
        else:
            used[best[0]] = m["name"]
            out.append((m, best[0], best[1]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/park_ways.yaml")
    ap.add_argument("--assign", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--min", type=int, default=200)
    ap.add_argument("--vmax", type=int, default=169)
    ap.add_argument("--json")
    a = ap.parse_args()
    p = params_from_config(a.config)
    if a.verify:
        mods = load_modules()
        rows = verify(p, mods)
        print(f"{'build':26} {'at V,U':>10} {'footprint':>10}  verdict")
        bad = 0
        for name, v, u, dv, du, note in rows:
            bad += note != "fits"
            print(f"{name:26} {v:4},{u:<5} {dv:4} x {du:<4}  {note}")
        missing = sorted({m['name'] for m in mods} - set(PLACEMENT) - NOT_A_LOT)
        print(f"\n{len(rows) - bad}/{len(rows)} fit as placed; {bad} short")
        if missing:
            print(f"NOT PLACED: {', '.join(missing)}")
        return
    rows = measure(p, vmax=a.vmax, minarea=a.min)
    hdr = (f"{'#':>3} {'land':18} {'band':16} {'V span':11} {'U span':11} "
           f"{'cells':>6} {'fill':>5} {'max rect VxU':>13} {'at V,U':>10}  feature")
    print(hdr)
    for i, r in enumerate(rows):
        print(f"{i:>3} {r['land']:18} {r['band']:16} "
              f"{r['v0']:3}-{r['v1']:<7} {r['u0']:3}-{r['u1']:<7} "
              f"{r['cells']:6} {r['fill']:5.2f} {r['rect'][0]:5} x {r['rect'][1]:<5} "
              f"{r['rect_at'][0]:4},{r['rect_at'][1]:<5} {','.join(r['feature'])}")
    print(f"\n{len(rows)} lots >= {a.min} cells; "
          f"{sum(r['cells'] for r in rows)} lawn cells in them")
    if a.assign:
        print("\n=== FIT ===")
        for m, lot, spot in assign(rows, load_modules()):
            if lot is None:
                print(f"  NO LOT   {m['name']:26} {m['v']:3}x{m['u']:<3} {m['land']}")
            else:
                print(f"  lot {lot:<3}  {m['name']:26} {m['v']:3}x{m['u']:<3} "
                      f"at V{spot[0]} U{spot[1]}")
    if a.json:
        for r in rows:
            r.pop("cellset")
        json.dump(rows, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
