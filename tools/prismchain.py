"""Rebuild the Prism Well chain IN ORDER, because every step reads the one before it.

    python tools/prismchain.py            # the whole chain
    python tools/prismchain.py --from descent

THE ORDER IS THE POINT, and it is not `defer_to`'s kind of order. Each of these designs is
generated against a capture the previous one produced, so running them out of sequence does not
merely mis-resolve a shared cell - it verifies against a world that does not exist:

    1  PF Prism Well      cut + collar + gallery + pier + column   verified against park_future
    2  prism_cut          park_future with the well's DIG applied  (the mouth actually open)
    3  prism_site         prism_cut + the well                     the course's collision world
    4  PF Prism Descent   the DECK run, r20->14 inside the mouth   verified against prism_site
    5  prism_deck         prism_site + the deck run
    6  PF Crown Descent   the SKY run, Y298->Y100 at r30           verified against prism_deck
    7  PF Prism Rig       the gantry, from BOTH recorded routes    one source, so it cannot drift
    8  prism_all          prism_deck + sky run + rig
    9  PF Signal Zero     the catch, the chamber and the bell      verified against prism_all

`park_future` is Park Complete MINUS the twelve archived v1 Prismworks designs - the park as it
will be. It is the honest context: verifying against Park Complete would report the whole mouth
as a collision with buildings that are coming out. Rebuild it with --park if the park moves.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dataclasses                                   # noqa: E402
import numpy as np                                   # noqa: E402

from mcbuild import schem, scan                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# WHAT COMES OUT OF `Park Complete` TO MAKE `park_future`, and it is two different lists for
# two different reasons.
#
# The v1 designs come out because they are RETIRED - archived in archive/prismworks_v1/ and
# coming out of the world.
#
# The v2 designs come out because `Park Complete` NOW CONTAINS THEM, and a design cannot be
# verified against a stale copy of itself. The Prism Well grew a tower and immediately reported
# eight overlaps against its own previous build: the collar had not moved, the material under it
# had. CLAUDE.md already records this trap on the Frontier - "verify_against out/Park Complete
# is now self-referential for these two designs" - and here it is, load-bearing.
V1 = ["PF Foundry Gate", "PF Prism Array", "PF Resonance Vault", "PF Prism Ascent",
      "PF Forge Deck", "PF Service Gallery", "PF Vantage Prism Summit", "PF Front Prismworks",
      "PF Water Wyrm Garden", "PF Game The Alignment", "PF Game The Vault",
      "PF Game Ascent Signal",
      # ...and v2's own previous build, or every regeneration fights the last one
      "PF Prism Well", "PF Prism Descent", "PF Crown Descent", "PF Prism Rig",
      "PF Signal Zero"]
STEPS = ["well", "descent", "crown", "rig", "signal"]
CONFIG = {"well": "configs/pf_prism_well.yaml", "descent": "configs/pf_prism_descent.yaml",
          "crown": "configs/pf_crown_descent.yaml", "rig": "configs/pf_prism_rig.yaml",
          "signal": "configs/pf_signal_zero.yaml"}


def _out(*p):
    return os.path.join(ROOT, "out", *p)


def _gen(cfg):
    print(f"\n=== {cfg} ===", flush=True)
    r = subprocess.run([sys.executable, "-m", "mcbuild", "gen", cfg], cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"{cfg} failed")


def _copy_sidecar(src, name, note):
    sc = json.load(open(_out(f"{src}.scan.json"), encoding="utf-8"))
    sc["name"] = name
    sc["file"] = f"{name}.litematic"
    sc["note"] = note
    json.dump(sc, open(_out(f"{name}.scan.json"), "w", encoding="utf-8"), indent=1)


def build_park_future():
    """Park Complete minus the twelve archived v1 Prismworks designs."""
    m = schem.load(_out("Park Complete.litematic"))
    s = scan.load(_out("Park Complete.scan.json"))
    ox, oy, oz = s.origin
    air = [i for i, n in enumerate(m.names) if n == "minecraft:air"][0]
    ids, gone = m.ids.copy(), 0
    for n in V1:
        f = _out(f"{n}.work.json")
        if not os.path.exists(f):
            print(f"  ! no work.json for {n} - not subtracted")
            continue
        for c in json.load(open(f, encoding="utf-8"))["cells"]:
            x, y, z = c[0] - ox, c[1] - oy, c[2] - oz
            if (0 <= y < ids.shape[0] and 0 <= z < ids.shape[1] and 0 <= x < ids.shape[2]
                    and ids[y, z, x] != air):
                ids[y, z, x] = air
                gone += 1
    # AND THEN SWEEP WHAT THE SUBTRACTION LEFT STANDING ON AIR. Removing a building removes the
    # ground cover that sat ON it: park_future came out with 31 moss carpets hanging over
    # nothing, Park Complete has none, and every design verified against it inherited those 31 as
    # its own problems. A context that is not a possible world makes every audit against it a
    # lie - and this one is cheap to fix, because in the real world the carpet comes off with the
    # roof it was lying on.
    # AND EMPTY THE WELL'S OWN CYLINDER, because subtracting by work.json always lags a build.
    #
    # `Park Complete` contains the LAST shipped well; the subtraction above uses the CURRENT
    # work.json. Those are different sets the moment the design changes, so whatever the old
    # build had and the new one does not stays behind - and the new design then reports overlaps
    # against its own previous self. It happened twice: eight cells when the tower arrived, four
    # more when the shaft was rebuilt, each time at the radius the old lattice posts stood at.
    #
    # The airspace over the mouth and the void under it belong to Prismworks v2 and to nothing
    # else - the three retained v1 designs are measured CLEAR of the cylinder - so the honest
    # context is one with that cylinder empty. The DECK COURSE ITSELF IS KEPT: the well digs it,
    # and a context that has already removed it cannot tell you whether the dig is right.
    import math
    wcx, wcz, wr = 97590, 80815, 62
    deck = 202
    cleared = 0
    for x in range(wcx - wr, wcx + wr + 1):
        for z in range(wcz - wr, wcz + wr + 1):
            if math.hypot(x - wcx, z - wcz) > wr:
                continue
            i, k = x - ox, z - oz
            if not (0 <= i < ids.shape[2] and 0 <= k < ids.shape[1]):
                continue
            for j in range(ids.shape[0]):
                if oy + j == deck or ids[j, k, i] == air:
                    continue
                ids[j, k, i] = air
                cleared += 1
    print(f"  cleared {cleared} cells from the well's cylinder (r{wr}, deck course kept)")

    needs_floor = ("carpet", "rail", "pressure_plate", "redstone_wire", "snow", "sapling",
                   "dead_bush", "short_grass", "tall_grass", "fern", "flower", "tulip",
                   "mushroom", "sugar_cane", "torch")
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    loose = [i for i, n in enumerate(names)
             if any(k in n for k in needs_floor) and "wall_torch" not in n]
    swept = 0
    for _ in range(6):
        hit = 0
        idxs = np.argwhere(np.isin(ids, loose))
        for y, z, x in idxs:
            if y == 0 or ids[y - 1, z, x] == air:
                ids[y, z, x] = air
                hit += 1
        swept += hit
        if not hit:
            break
    n = schem.save(_out("park_future.litematic"),
                   dataclasses.replace(m, ids=ids, root=None), name="park_future")
    _copy_sidecar("Park Complete", "park_future",
                  "Park Complete MINUS the twelve archived v1 Prismworks designs - the park as "
                  "it will be, and the context Prismworks v2 is verified against. "
                  "See archive/prismworks_v1/ and tools/prismchain.py.")
    print(f"park_future: {gone} v1 cells cleared, {swept} left standing on air swept, "
          f"{n} blocks")


def apply_dig(base, design, out, note):
    """`base` with `design`'s dig list applied - the removals a litematic cannot express."""
    m = schem.load(_out(f"{base}.litematic"))
    s = scan.load(_out(f"{base}.scan.json"))
    ox, oy, oz = s.origin
    air = [i for i, n in enumerate(m.names) if n == "minecraft:air"][0]
    ids, dug = m.ids.copy(), 0
    md = json.load(open(_out(f"{design}.scan.json"), encoding="utf-8"))
    for x, y, z in md.get("dig") or ():
        i, j, k = x - ox, y - oy, z - oz
        if (0 <= j < ids.shape[0] and 0 <= k < ids.shape[1] and 0 <= i < ids.shape[2]
                and ids[j, k, i] != air):
            ids[j, k, i] = air
            dug += 1
    n = schem.save(_out(f"{out}.litematic"),
                   dataclasses.replace(m, ids=ids, root=None), name=out)
    _copy_sidecar(base, out, note)
    print(f"{out}: {dug} cells dug out of {base}, {n} blocks")


def merge(base, designs, out, note):
    cmd = [sys.executable, os.path.join(ROOT, "tools", "plan_merge.py"),
           _out(f"{base}.litematic")] + [_out(f"{d}.litematic") for d in designs] \
        + ["-o", _out(f"{out}.litematic")]
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"merge into {out} failed")
    _copy_sidecar(base, out, note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", choices=STEPS, default="well")
    ap.add_argument("--park", action="store_true", help="rebuild park_future first")
    a = ap.parse_args()
    i = STEPS.index(a.start)

    if a.park or not os.path.exists(_out("park_future.litematic")):
        build_park_future()

    if i <= 0:
        _gen(CONFIG["well"])
    if i <= 1:
        apply_dig("park_future", "PF Prism Well", "prism_cut",
                  "park_future with the Prism Well's dig list applied - the mouth actually open.")
        merge("prism_cut", ["PF Prism Well"], "prism_site",
              "prism_cut plus the Prism Well - the world the descent is sited and verified in.")
        _gen(CONFIG["descent"])
    if i <= 2:
        merge("prism_site", ["PF Prism Descent"], "prism_deck",
              "prism_site plus the DECK run - what the sky run is sited against, so the two "
              "concentric helices cannot claim a cell of each other.")
        _gen(CONFIG["crown"])
    if i <= 3:
        _gen(CONFIG["rig"])
    if i <= 4:
        merge("prism_deck", ["PF Crown Descent", "PF Prism Rig"], "prism_all",
              "prism_deck plus the sky run and the gantry over both - the floor's context.")
        if i <= 4 and os.path.exists(os.path.join(ROOT, CONFIG["signal"])):
            _gen(CONFIG["signal"])
        else:
            print(f"\n(no {CONFIG['signal']} yet - stopping after prism_all)")
    print("\nchain complete")


if __name__ == "__main__":
    main()
