"""The jungle taking the camp back - and the four faults it produced before it was right.

Every one of these shipped a design that audited perfectly clean. A vine whose flags name the wrong
face hangs in air and renders identically to one on a wall; a roof asked the WALL question grows
nothing and reports a number; and a pass that replaces rather than adds is a pass a litematica
printer can never build, because a printer places into AIR.
"""
from __future__ import annotations

import json
import os

import yaml

from mcbuild import blocks, palette, schem
from mcbuild.gen import overgrowth
from mcbuild.gen.frontier_scatter import shipped_cells

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED = os.path.join(ROOT, "out", "PF Frontier Overgrowth.litematic")
CFG = os.path.join(ROOT, "configs", "pf_frontier_overgrowth.yaml")
_SIDE = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def _model():
    return schem.load(SHIPPED) if os.path.exists(SHIPPED) else None


def _world():
    """The COMPOSITE, because a vine clings to somebody else's wall.

    The design's own artifact holds vines and carpet and nothing to hang them on - the camp is
    eleven other modules - so asking the design about its own supports is rule 2 from the wrong
    side. This is `finish.verify_against`'s question, asked in a test.
    """
    p = os.path.join(ROOT, "out", "Park Complete.litematic")
    if not os.path.exists(p) or not os.path.exists(SHIPPED):
        return None, None
    o = json.load(open(os.path.join(ROOT, "out", "Park Complete.scan.json")))["origin"]
    return schem.load(p), o


def test_a_vines_flags_name_the_face_it_actually_clings_to():
    """The flags are WHICH FACE it hangs on, not which way it points.

    Written as the opposite - the back of the side it grew from - 2,948 vines in the first build
    named a face with open air behind it, and every one of them rendered exactly like a vine on a
    wall. `work.MULTIFACE` records these precisely because they are a DECISION; every other block's
    connection flags are derived by the game and are not.
    """
    m = _model()
    w, o = _world()
    if m is None or w is None:
        return
    ms = json.load(open(SHIPPED.replace(".litematic", ".scan.json")))["origin"]
    wn = [n.split(":")[-1] for n in w.names]
    names = [n.split(":")[-1] for n in m.names]
    sy, su, sv = m.ids.shape
    seen = bad = 0
    for y in range(sy):
        for u in range(su):
            for v in range(sv):
                i = int(m.ids[y, u, v])
                if not i or names[i] != "vine":
                    continue
                seen += 1
                pr = m.props_at(v, y, u)
                on = [s for s in _SIDE if pr.get(s) == "true"]
                if len(on) != 1:
                    bad += 1
                    continue
                dv, du = _SIDE[on[0]]
                iv = ms["x"] + v + dv - o["x"]
                iu = ms["z"] + u + du - o["z"]
                iy = ms["y"] + y - o["y"]
                if not (0 <= iy < w.ids.shape[0] and 0 <= iu < w.ids.shape[1]
                        and 0 <= iv < w.ids.shape[2]):
                    continue
                k = int(w.ids[iy, iu, iv])
                if not k or wn[k] in ("air", "vine"):
                    bad += 1
    assert seen, "the shipped overgrowth has no vines"
    assert bad == 0, f"{bad} of {seen} vines name a face with nothing on it"


def test_it_never_replaces_a_standing_block():
    """ADDITIVE, and that is a buildability rule rather than a courtesy.

    A litematica printer places into air and never replaces, so a swapped cell is a cell nobody can
    ever print: it would stand as permanent amber in `/cscan check` for the life of the park. The
    ship reports this as `overlap 0` and this asserts it against the artifact rather than the log.
    """
    m = _model()
    w, o = _world()
    if m is None or w is None:
        return
    own = shipped_cells(SHIPPED)
    assert own, "the shipped overgrowth has no cells"
    wn = [n.split(":")[-1] for n in w.names]
    names = [n.split(":")[-1] for n in m.names]
    ms = json.load(open(SHIPPED.replace(".litematic", ".scan.json")))["origin"]
    sy, su, sv = m.ids.shape
    hit = 0
    for y in range(sy):
        for u in range(su):
            for v in range(sv):
                i = int(m.ids[y, u, v])
                if not i:
                    continue
                iv, iu, iy = (ms["x"] + v - o["x"], ms["z"] + u - o["z"], ms["y"] + y - o["y"])
                if not (0 <= iy < w.ids.shape[0] and 0 <= iu < w.ids.shape[1]
                        and 0 <= iv < w.ids.shape[2]):
                    continue
                k = int(w.ids[iy, iu, iv])
                # the composite CONTAINS this design, so its own block is what should be there
                if k and wn[k] != names[i] and wn[k] != "moss_carpet":
                    hit += 1
    assert hit == 0, f"{hit} cells stand where the park holds something else"


def test_a_roof_is_not_a_wall():
    """`ROOF` is derived from the registry, never typed out.

    The first build asked `supports_side` about a stair and a slab and grew moss on 486 of ~35,000
    target cells. Rule 11: ask the game.
    """
    for n in ("stone_brick_stairs", "stone_brick_slab", "cobblestone_slab"):
        assert n in overgrowth.ROOF, f"{n} carries a carpet and is not in ROOF"
        assert n not in overgrowth.WALL, f"{n} cannot carry a vine and must not be in WALL"
    for n in overgrowth.ROOF:
        assert blocks.supports_top(n), f"{n} cannot carry a carpet"


def test_nothing_it_grows_is_currency_or_expensive():
    """Rule 16. Moss is used because dirt and grass are MONEY on this server."""
    m = _model()
    if m is None:
        return
    for n in m.names:
        name = n.split(":")[-1]
        if name == "air":
            continue
        assert blocks.spendable(name), f"{name} is currency"
        assert palette.tier(name) != "expensive", f"{name} is expensive"


def test_it_keeps_out_of_the_two_designs_that_own_their_own_ground():
    """The plateau's surface is `gen/plateau.py`'s and the rim strip is `PF Frontier Rim`'s.

    Two land-dressing passes on one surface is what `finish.defer_to` exists to stop, and the ship
    reported exactly that as three cells of clash before the rim was reserved here.
    """
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    boxes = cfg["params"]["keep_out"]
    assert any(b[2] >= 99 for b in boxes), "the plateau's own lot is not kept out"
    assert any(b[0] >= 185 for b in boxes), "the rim's own ground is not kept out"
