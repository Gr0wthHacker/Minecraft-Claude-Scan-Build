"""EVERY TREE, LAMP AND BOULDER IN THE PARK, AND WHAT IT IS STANDING IN.

Jack: *"audit all placements of things like trees and lamp posts, make sure its artistic, it
makes sense, doesnt obstruct pathways or buildings."*

**THE DRESSING IS THE ONE THING NOTHING IN THIS REPO COULD SEE.** Every check the park has is
about a BLOCK - is the state legal, is it supported, is it affordable, is it in 1.19, does it
collide - and a tree floating one course over a flower passes all of them. So does a boulder
through a hedge, a trunk through another tree's canopy, and four trunks under one blob of
leaves. `render3d` draws a floating tree exactly as it draws a planted one, and the bill of
materials is right either way. The only symptom is a park full of half-eaten planting.

And the questions are CROSS-DESIGN, which is why no generator can answer them from inside
itself: `frontier_scatter._Ground.free` asks the WORLD, which is the capture, and the capture
does not contain what the pass laid ten iterations ago - nor what the design next door will lay
tomorrow. **A DESIGN'S OWN CANVAS IS NOT THE WORLD, AND NEITHER IS ITS NEIGHBOUR'S.**

So this reads the SHIPPED COMPOSITE, attributes every cell to the module that placed it, and
asks five things a person walking the park would ask:

    ROOTED      is every tree standing in soil, or is it floating on a tuft, a rock or a hedge
    SPACED      how close do trunks get - a crown is radius 2, so two trunks two apart are one
                blob with two poles out of it rather than a stand of trees
    CLEAR       does anything stand in a street, at the feet or at the head
    OPEN        does anything stand in a doorway
    LIT         does every lamp mast carry a light, and does any light sit buried in leaves

    python tools/park_dressing.py                     the whole park
    python tools/park_dressing.py --design "PF Park Green"
    python tools/park_dressing.py --worst 30          name more of the offenders

It writes nothing and is a standalone diagnostic: it needs `out/Park Ways.litematic`,
`out/Park Rail.litematic` and the module artifacts, which is what `tools/park_place.py` places.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from mcbuild import schem                                          # noqa: E402
import park_place as pp                                            # noqa: E402

#: WHAT A PLANT MAY ROOT IN - rule 11, and the same dirt family every generator here uses.
#: `air` is in it because a trunk's own base course on open terrain has nothing under it to name.
SOIL = frozenset({"moss_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "grass_block",
                  "mycelium", "mud", "farmland", "dirt_path", "clay", "sand", "red_sand",
                  "gravel", "mossy_cobblestone", "air"})

#: WHAT COUNTS AS DRESSING - a thing placed ON the ground rather than being the ground or a
#: building. A log and a leaf are a tree; a boulder is its own kind; the rest is furniture.
DRESSING = frozenset({"azalea", "flowering_azalea", "sweet_berry_bush", "cobblestone", "andesite",
                      "stone", "mossy_cobblestone", "cobbled_deepslate", "stone_brick_slab",
                      "diorite", "granite"})

LIGHTS = frozenset({"lantern", "soul_lantern", "ochre_froglight", "verdant_froglight",
                    "pearlescent_froglight", "sea_lantern", "glowstone", "shroomlight", "end_rod",
                    "redstone_lamp", "campfire", "torch", "soul_torch", "jack_o_lantern"})

#: A LAMP IS ITS PLINTH, NOT ITS SHAFT, and that distinction is the whole of the detector. The
#: prismworks lamp's mast is `polished_blackstone_brick_wall` - and so is the rim edge POST that
#: `Park Ways` stands every six blocks along V170, two courses tall and correctly unlit. Keyed on
#: the mast alone this reported 26 lamps with no light, every one of them a post doing its job.
#: Keyed on the two-course plinth a lamp actually has, it reports none.
PLINTHS = {"frontier": ("stone_bricks", "chiseled_stone_bricks"),
           "midway": ("smooth_stone", "chiseled_stone_bricks"),
           "prismworks": ("polished_deepslate", "deepslate_tiles")}


# --------------------------------------------------------------------------- the attribution


class Park:
    """The composite, plus WHO placed every cell of it.

    `park_place.merge` already tracks an owner per cell and throws it away; this is the same walk,
    kept. Without it every finding here reads as "something is wrong somewhere in 430,000 blocks",
    which is not a finding.
    """

    def __init__(self):
        items = pp.modules(report=False)
        ways = schem.load(str(ROOT / "out" / "Park Ways.litematic"))
        rail = schem.load(str(ROOT / "out" / "Park Rail.litematic"))
        _model, origin = pp.merge(items)

        height = 220
        sz, sx = ways.ids.shape[1], ways.ids.shape[2]
        self.own = np.full((height, sz, sx), -1, np.int16)
        self.blk = np.zeros((height, sz, sx), np.int32)
        self.pal: list[str] = ["air"]
        self.src: list[str] = []
        index: dict[str, int] = {"air": 0}

        def lay(m, ov, oy, ou, tag):
            si = len(self.src)
            self.src.append(tag)
            names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(m.palette)}
            for y, z, x in zip(*m.solid().nonzero()):
                cy, cz, cx = int(y) + oy, int(z) + ou, int(x) + ov
                if not (0 <= cy < height and 0 <= cz < sz and 0 <= cx < sx):
                    continue
                if self.own[cy, cz, cx] >= 0:         # first writer wins, as the merge does
                    continue
                n = names[int(m.ids[y, z, x])]
                slot = index.get(n)
                if slot is None:
                    slot = index[n] = len(self.pal)
                    self.pal.append(n)
                self.own[cy, cz, cx] = si
                self.blk[cy, cz, cx] = slot

        oy = 0 - min(0, origin[1])
        for name, v, u, m, plane in items:
            lay(m, v, -plane + 1 + oy, u, name)
        rv = yaml.safe_load((ROOT / "configs" / "park_rail.yaml").read_text(encoding="utf-8"))
        lay(rail, int(rv["params"]["bounds"][0]), oy, 0, "Park Rail")
        lay(ways, 0, oy, 0, "Park Ways")

        self.origin = (pp.ANCHOR[0], pp.ANCHOR[1] + min(0, origin[1]), pp.ANCHOR[2])
        self.name = np.array(self.pal)
        self.sy, self.sz, self.sx = self.blk.shape

    # -- helpers ---------------------------------------------------------
    def y(self, world: int) -> int:
        return world - self.origin[1]

    def world(self, x: int, y: int, z: int) -> tuple[int, int, int]:
        return self.origin[0] + int(x), self.origin[1] + int(y), self.origin[2] + int(z)

    def at(self, x: int, y: int, z: int) -> str:
        if not (0 <= y < self.sy and 0 <= z < self.sz and 0 <= x < self.sx):
            return "OOB"
        return self.pal[self.blk[y, z, x]]

    def owner(self, x: int, y: int, z: int) -> str:
        o = self.own[y, z, x]
        return self.src[o] if o >= 0 else "-"

    def ids_of(self, pred) -> list[int]:
        return [i for i, n in enumerate(self.pal) if pred(n)]


# --------------------------------------------------------------------------- the objects


def trees(p: Park) -> list[dict]:
    """Every TREE: a log column of three or more with leaves at its top.

    **A LOG COLUMN IS NOT A TREE.** Asked without the crown test this counts a coaster's trestle
    posts, a pergola's uprights and a building's corner posts - 1,291 of them against 481 real
    trees - and then reports every one as "not rooted in soil", which they correctly are not. The
    crown is what makes it a tree, and what makes the soil question apply at all.

    AND THE CROWN MUST BE THIS TRUNK'S OWN. Taken as "any leaf within two cells of the top" the
    Mine Coaster's spruce trestle and the Welcome Court's pergola posts both came back as trees,
    because the Lost Plateau's canopy hangs over them - fourteen structural posts reported as
    badly planted trees, which is a tool crying wolf on a correct build. A crown SITS ON its
    trunk, so it is tested in the 3x3 directly over the top course, and it has to belong to the
    design that placed the trunk.
    """
    logs = set(p.ids_of(lambda n: n.endswith("_log") or n.endswith("_wood") or n.endswith("_stem")))
    leaf = set(p.ids_of(lambda n: n.endswith("_leaves")))
    T = np.isin(p.blk, list(logs))
    L = np.isin(p.blk, list(leaf))
    out = []
    zs, xs = np.nonzero(T.any(axis=0))
    for z, x in sorted({(int(a), int(b)) for a, b in zip(zs, xs)}):
        col = [y for y in range(p.sy) if T[y, z, x]]
        runs, cur = [], [col[0]]
        for a, b in zip(col, col[1:]):
            if b == a + 1:
                cur.append(b)
            else:
                runs.append(cur)
                cur = [b]
        runs.append(cur)
        for r in runs:
            if len(r) < 3:
                continue
            top = r[-1]
            mine = p.own[r[0], z, x]
            crown = any(L[top + dy, z + dz, x + dx] and p.own[top + dy, z + dz, x + dx] == mine
                        for dy in (0, 1) for dz in (-1, 0, 1) for dx in (-1, 0, 1)
                        if 0 <= top + dy < p.sy and 0 <= z + dz < p.sz and 0 <= x + dx < p.sx)
            if crown:
                out.append({"x": x, "z": z, "y0": r[0], "y1": top,
                            "owner": p.owner(x, r[0], z),
                            "under": p.at(x, r[0] - 1, z),
                            "kind": p.at(x, r[0], z)})
    return out


def lamps(p: Park) -> list[dict]:
    """Every street lamp, found by its PLINTH - see `PLINTHS` for why not by its mast."""
    out = []
    y0, y1 = p.y(202), p.y(203)
    for land, (pad, collar) in PLINTHS.items():
        if pad not in p.pal or collar not in p.pal:
            continue
        m = (p.blk[y0] == p.pal.index(pad)) & (p.blk[y1] == p.pal.index(collar))
        for z, x in zip(*np.nonzero(m)):
            z, x = int(z), int(x)
            lit = any(p.at(x + dx, y, z + dz) in LIGHTS
                      for y in range(y1, min(p.sy, y1 + 9))
                      for dz in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2))
            out.append({"x": x, "z": z, "land": land, "lit": lit, "owner": p.owner(x, y0, z)})
    return out


def damaged_lamp_masts(p: Park) -> list[dict]:
    """Check every intended mast, including lamps whose plinth was overwritten.

    Detecting only surviving plinths excluded precisely the buried lamps the
    audit needed to find. The ground-layer artifact is the independent roster.
    """
    ways = schem.load(str(ROOT / 'out/Park Ways.litematic'))
    names = np.array([e.value['Name'].value.split(':')[-1] for e in ways.palette])
    out = []
    for land, (pad, collar) in PLINTHS.items():
        mask = (names[ways.ids[0]] == pad) & (names[ways.ids[1]] == collar)
        for z, x in zip(*np.nonzero(mask)):
            for y in range(1, min(9, ways.ids.shape[0])):
                wanted = str(names[ways.ids[y, z, x]])
                if wanted == 'air':
                    continue
                actual = p.at(int(x), p.y(202 + y), int(z))
                if actual != wanted:
                    out.append({'world': p.world(x, p.y(202+y), z),
                                'land': land, 'wanted': wanted, 'actual': actual})
    return out


# --------------------------------------------------------------------------- the questions


def in_tub(p: Park, t: dict) -> bool:
    """Is this trunk standing in a RAISED PLANTER rather than in the ground?

    **A TUB IS MASONRY UNDER A TREE AND IS NOT A FAULT.** The Welcome Court's four planters are a
    3x3 rim of paving with a slab cap and the trunk in the middle, which is exactly how a paved
    court is planted without losing its floor - and read as "six trees growing out of a stone
    floor" by a soil test that knows nothing about rims. The discriminator is the rim: a tub's
    trunk is ringed by its own masonry at its own base course, a tree standing on a street is not.
    """
    n = 0
    for dz in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dz == 0 and dx == 0:
                continue
            if p.at(t["x"] + dx, t["y0"], t["z"] + dz) not in PASSABLE_ISH:
                n += 1
    return n >= 6


#: Anything a rim is NOT made of. Deliberately generous - the question is only whether a solid
#: kerb rings the trunk, so air, this pass's own planting and a neighbour's leaves all say "no".
PASSABLE_ISH = frozenset({"air", "cave_air", "void_air", "OOB", "moss_carpet", "short_grass",
                          "fern", "tall_grass", "large_fern", "vine", "glow_lichen"})


def not_rooted(p: Park, ts: list[dict]) -> list[dict]:
    """A tree whose base cell is neither standing in the dirt family nor sitting in a tub.

    A tuft, a flower or a moss carpet under a trunk is a tree floating one course off the ground
    with something jammed underneath it - which is what a later drift overwriting the tree's own
    bottom log leaves behind, and what the module contract's *"never replaces a standing block"*
    was claiming could not happen.
    """
    return [t for t in ts if t["under"] not in SOIL and not in_tub(p, t)]


def unsupported(p: Park, ts: list[dict]) -> list[dict]:
    """A tree with NOTHING AT ALL under it - floating in open air.

    Worse than the soil question and a different fault: `PF Lost Plateau`'s canopy plants on the
    Mine Ridge's rock, and where its own moss cap did not reach, eight of its trunks begin three
    and four courses above the last solid block with a curtain of its own vines hanging in the
    gap. `under` reads `vine` and a vine is not support.
    """
    out = []
    for t in ts:
        y = t["y0"] - 1
        while y >= 0 and p.at(t["x"], y, t["z"]) in PASSABLE_ISH and t["y0"] - y <= 6:
            y -= 1
        gap = t["y0"] - y - 1
        if gap > 0:
            out.append({**t, "gap": gap, "rests_on": p.at(t["x"], y, t["z"])})
    return out


def crowded(ts: list[dict], clear: int = 3) -> list[tuple[dict, int]]:
    """Trunks within `clear` of another trunk, chebyshev - a thicket rather than a stand."""
    pts = [(t["x"], t["z"]) for t in ts]
    out = []
    for i, t in enumerate(ts):
        best = 10 ** 6
        for j, (a, b) in enumerate(pts):
            if i != j:
                best = min(best, max(abs(t["x"] - a), abs(t["z"] - b)))
        if best < clear:
            out.append((t, best))
    return out


def street_mask(p: Park) -> np.ndarray:
    """The park's real streets: paved by the ground layer, with paving either side.

    **A LAMP'S OWN PLINTH IS PAVING-COLOURED AND IS NOT A STREET.** Taken as "any non-moss cell
    the ground layer owns at the paving course", every lamp standing on open lawn reads as a
    one-cell street with its own post in the middle of it - 810 false findings, and the three
    worst in the list were one lamp seen three ways. A street cell has street either side of it;
    a plinth has at most two paved neighbours and usually none.
    """
    ways = p.src.index("Park Ways")
    y = p.y(202)
    paved = (p.own[y] == ways) & (p.blk[y] != 0) & (p.name[p.blk[y]] != "moss_block")
    nb = np.zeros(paved.shape, int)
    nb[1:] += paved[:-1]
    nb[:-1] += paved[1:]
    nb[:, 1:] += paved[:, :-1]
    nb[:, :-1] += paved[:, 1:]
    return paved & (nb >= 3)


def in_street(p: Park) -> Counter:
    """Dressing standing in a street, at the feet or at the head."""
    street = street_mask(p)
    dress = set(p.ids_of(lambda n: n.endswith("_leaves") or n.endswith("_log") or n in DRESSING))
    hits = Counter()
    for wy, where in ((203, "feet"), (204, "head")):
        y = p.y(wy)
        for z, x in zip(*np.nonzero(street & np.isin(p.blk[y], list(dress)))):
            hits[(where, p.owner(int(x), y, int(z)), p.at(int(x), y, int(z)))] += 1
    return hits


def in_doorway(p: Park) -> Counter:
    """Another design's dressing standing in the opening of somebody's door or gate."""
    doors = set(p.ids_of(lambda n: n.endswith("_door") or n.endswith("_fence_gate")))
    dress = set(p.ids_of(lambda n: n.endswith("_leaves") or n.endswith("_log") or n in DRESSING))
    hits = Counter()
    for y, z, x in zip(*np.isin(p.blk, list(doors)).nonzero()):
        mine = p.own[y, z, x]
        for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1):
                a, b, c = int(y) + dy, int(z) + dz, int(x) + dx
                if not (0 <= a < p.sy and 0 <= b < p.sz and 0 <= c < p.sx):
                    continue
                if p.own[a, b, c] >= 0 and p.own[a, b, c] != mine and p.blk[a, b, c] in dress:
                    hits[(p.src[mine], p.src[p.own[a, b, c]], p.pal[p.blk[a, b, c]])] += 1
    return hits


def buried_lights(p: Park) -> Counter:
    """A light with leaves on three or more of its six sides - a lamp inside a canopy."""
    leaf = np.isin(p.blk, list(p.ids_of(lambda n: n.endswith("_leaves"))))
    lit = [p.pal.index(n) for n in LIGHTS if n in p.pal]
    hits = Counter()
    for y, z, x in zip(*np.isin(p.blk, lit).nonzero()):
        n = sum(1 for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                     (0, -1, 0), (0, 0, 1), (0, 0, -1))
                if 0 <= y + dy < p.sy and 0 <= z + dz < p.sz and 0 <= x + dx < p.sx
                and leaf[y + dy, z + dz, x + dx])
        if n >= 3:
            hits[(p.src[p.own[y, z, x]], p.pal[p.blk[y, z, x]])] += 1
    return hits


def kept_by(design: str) -> int:
    """Cells a design's own later drift would have eaten and did not.

    Measured by the GENERATOR and recorded in its sidecar as `parts.kept`; this is the reader, so
    the whole audit stays one command. A number climbing here says the drifts are fighting and
    the density has gone past what the ground can hold.
    """
    side = ROOT / "out" / f"{design}.scan.json"
    if not side.exists():
        return -1
    return int(json.loads(side.read_text(encoding="utf-8")).get("parts", {}).get("kept", -1))


# --------------------------------------------------------------------------- the report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--design", help="report only this module's own dressing")
    ap.add_argument("--worst", type=int, default=12, help="how many offenders to name")
    ap.add_argument("--clear", type=int, default=3, help="how close two trunks may stand")
    args = ap.parse_args()

    p = Park()
    ts = trees(p)
    ls = lamps(p)
    if args.design:
        ts = [t for t in ts if t["owner"] == args.design]
        ls = [x for x in ls if x["owner"] == args.design]

    print(f"{len(ts)} trees and {len(ls)} street lamps, "
          f"over {int((p.own >= 0).sum()):,} placed cells\n")

    bad = not_rooted(p, ts)
    print(f"ROOTED   {len(ts) - len(bad)}/{len(ts)} trees stand in soil or in a raised tub")
    for (o, u), n in Counter((t["owner"], t["under"]) for t in bad).most_common(args.worst):
        e = next(t for t in bad if t["owner"] == o and t["under"] == u)
        print(f"    {n:>4}  {o:<26}on {u:<22} e.g. {p.world(e['x'], e['y0'], e['z'])}")

    air = unsupported(p, ts)
    print(f"\nSTANDING {len(ts) - len(air)}/{len(ts)} trees have a solid block under the trunk")
    for (o, g, r), n in Counter((t["owner"], t["gap"], t["rests_on"])
                                for t in air).most_common(args.worst):
        e = next(t for t in air if t["owner"] == o and t["gap"] == g)
        print(f"    {n:>4}  {o:<26}{g} course(s) of air over {r:<16} "
              f"e.g. {p.world(e['x'], e['y0'], e['z'])}")

    cr = crowded(ts, args.clear)
    print(f"\nSPACED   {len(ts) - len(cr)}/{len(ts)} trunks stand {args.clear}+ from a neighbour")
    print("         (a WOODLAND is meant to be dense - read this per DESIGN, and judge the "
          "ornamental passes by it, not the canopies)")
    if cr:
        for o, n in Counter(t["owner"] for t, _ in cr).most_common(args.worst):
            print(f"    {n:>4}  {o:<26}closest {min(g for t, g in cr if t['owner'] == o)}")
        print(f"    tightest gaps: {sorted(n for _, n in cr)[:10]}")

    st = in_street(p)
    print(f"\nCLEAR    {sum(st.values())} dressing cells stand in a street")
    for k, n in st.most_common(args.worst):
        print(f"    {n:>4}  at {k[0]:<5}{k[1]:<26}{k[2]}")

    dw = in_doorway(p)
    print(f"\nOPEN     {sum(dw.values())} dressing cells stand in somebody's doorway")
    for k, n in dw.most_common(args.worst):
        print(f"    {n:>4}  {k[0]} door <- {k[1]} {k[2]}")

    dark = [x for x in ls if not x["lit"]]
    damaged = damaged_lamp_masts(p)
    print(f"\nINTACT   {len(damaged)} intended lamp mast cells overwritten")
    for cell in damaged[:args.worst]:
        print(f"    {cell}")
    bl = buried_lights(p)
    print(f"\nLIT      {len(ls) - len(dark)}/{len(ls)} lamps carry a light; "
          f"{sum(bl.values())} lights sit buried in leaves")
    for x in dark[:args.worst]:
        print(f"    DARK  {x['land']:<12}{p.world(x['x'], p.y(202), x['z'])}")
    for k, n in bl.most_common(args.worst):
        print(f"    {n:>4}  buried  {k[0]:<26}{k[1]}")

    print("")
    for d in ("PF Park Green", "PF Park Rim Green"):
        k = kept_by(d)
        if k >= 0:
            print(f"KEPT     {d}: {k} cells a later drift would have eaten and did not")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
