"""THE PTEROSAUR - a membrane on a finger, perched over the Lost Plateau.

Jack: *"lets do the pterosaur after."*

**IT IS THE OTHER HALF OF THE RULE THE SAUROPOD IS BUILT ON.** CLAUDE.md's line is planar and
columnar against volumetric: the sauropod is columns, and this is the PLANE. A pterosaur's whole
identity is a sheet - each wing is a single membrane stretched from the body along one hugely
elongated finger - and a one-thick sheet is what voxels render best of anything. The island's own
sky bird (an 83-block wingspan of layered primaries) and `gen/bat.py` are the two worked examples,
and both are recorded successes.

**IT IS NOT `bat.py` RE-COLOURED.** Jack, on the causeway: *"get rid of the gecko and bat - those
are used assets, we want NEW things."* The bat's wing is a mammal's - four fingers, four spans of
membrane, and a body slung under it. A pterosaur's is ONE finger and one span, the body sits on top
of the wing rather than under it, and the crest is half of what names the animal. Sharing a
category is not sharing a build.

**HALF-SPREAD, NOT SPREAD.** The bat's own record: *"`spread` 0.75 beats 1.0 and that was measured,
not assumed: fully spread the wing is one flat plate, half-furled it keeps a stepped outline and
the finger struts and black tips are the tell."* A fully spread wing here is a rectangle with a
head on it.

**AND IT CARRIES ITS OWN PERCH**, which is the bat's other recorded lesson: *"the bat carries its
own ceiling ... so the design is self-contained and can hang in open air."* A crag under the feet
means the animal can stand anywhere with sky over it rather than needing a roof somebody else
built - and the Vantage Lookout, the obvious perch, is measured: its deck is 8 x 15 and a
34-wingspan animal on it reaches eight cells past the park's own boundary.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx

#: Checked against `blocks.available` (1.19), `blocks.spendable` and `palette.tier` by
#: `tests/test_pterosaur.py`, which asks the registry rather than trusting this list.
HIDE = {
    # **THE MEMBRANE IS DARK BECAUSE IT IS READ AGAINST SKY.** A wing is a silhouette before it is
    # anything else, and the one thing behind it is always the sky - so the sheet is the darkest
    # cheap tone there is and the body is a step up from it.
    "wing": "gray_wool",           # L67
    "wing_edge": "black_wool",     # L21 - the leading finger and the trailing hem
    "body": "brown_wool",          # L79
    "belly": "light_gray_wool",    # L141
    "crest": "red_wool",           # L65 - the identity, and the land's own show tone
    "beak": "bone_block",          # L225 - pale, so the head reads against the dark wing
    "eye": "black_wool",
    "claw": "bone_block",
    "rock": "cobbled_deepslate",
    "rock_b": "andesite",
    "rock_c": "stone",
    "moss": "moss_block",
    "vine": "vine",
}

#: +f is FORWARD, toward the head - `park._Frame`'s convention, so a facing bug is one bug.
_STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

PTEROSAUR = {
    "kind": "pteranodon",
    "at": None,                 # [V, U] - under the feet
    "anchor": [97500, 203, 80300],
    "under": None,              # the world it stands over, so the crag meets real ground
    "facing": "west",
    "span": 34,                 # WINGTIP TO WINGTIP, which is the animal's real measurement
    "spread": 0.72,             # 1.0 is a flat plate - see the module docstring
    "perch": True,              # carry its own crag, so it can stand anywhere with sky over it
    "perch_h": 6,
    "seed": 0,
    "title": "THE PTEROSAUR",
}


class _Frame:
    """The animal's own axes: (forward, side, up). One frame, one facing bug."""

    def __init__(self, c: Canvas, cv: int, cu: int, facing: str):
        if facing not in _STEP:
            raise ValueError(f"a pterosaur needs a real facing, not {facing!r}")
        self.c, self.cv, self.cu = c, cv, cu
        self.fx, self.fz = _STEP[facing]
        self.sx, self.sz = -self.fz, self.fx
        self.facing = facing
        self.refused = 0
        self.fixed: set = set()

    def at(self, f, s):
        return (self.cv + self.fx * f + self.sx * s, self.cu + self.fz * f + self.sz * s)

    def put(self, f, s, y, key, protect=False) -> bool:
        v, u = self.at(int(round(f)), int(round(s)))
        y = int(round(y))
        if not (0 <= v < self.c.sx and 0 <= u < self.c.sz and 0 <= y < self.c.sy):
            self.refused += 1
            return False
        self.c.put(v, y, u, self.c.state(HIDE.get(key, key)))
        if protect:
            self.fixed.add((v, y, u))
        return True


def _run(fr: _Frame, a, b, key, protect=False, width=0) -> int:
    """A line of cells from a to b that is actually 6-CONNECTED.

    **A CHAIN STEPPED BY HAND IS A ROW OF DIAGONAL NEIGHBOURS, WHICH IS NOT CONNECTED.** Written
    as `f + k * 0.8, y + k * 0.7` the neck, the beak and the crest each came apart into two or
    three floating pieces - 8 cells of beak here, 5 of crest there - and this island has shed a
    feature to exactly that four times now: two sets of ear tips, an ossicone, a mane in seven
    fragments. The fix is always the same: step fine enough that consecutive samples share a face,
    and fill the corner where two axes change at once.
    """
    n = 0
    dist = max(abs(b[0] - a[0]), abs(b[1] - a[1]), abs(b[2] - a[2]))
    steps = max(1, int(dist * 3))
    prev = None
    for i in range(steps + 1):
        t = i / steps
        f = a[0] + (b[0] - a[0]) * t
        s2 = a[1] + (b[1] - a[1]) * t
        y = a[2] + (b[2] - a[2]) * t
        cell = (round(f), round(s2), round(y))
        if cell == prev:
            continue
        if prev is not None and sum(1 for p, q in zip(cell, prev) if p != q) > 1:
            # two axes moved at once - fill the corner, or the two cells are only diagonal
            n += 1 if fr.put(cell[0], prev[1], prev[2], key, protect) else 0
        n += 1 if fr.put(cell[0], cell[1], cell[2], key, protect) else 0
        for w in range(1, width + 1):
            for sgn in (1, -1):
                n += 1 if fr.put(cell[0], cell[1] + sgn * w, cell[2], key, protect) else 0
        prev = cell
    return n


def _wing(fr: _Frame, d: dict, side: int) -> dict:
    """One wing: a leading FINGER, a membrane behind it, and struts across it.

    **THE FINGER IS THE WING.** A pterosaur's whole span hangs off one elongated digit, and drawing
    that leading edge as a distinct darker line is the single thing that stops a membrane reading
    as a grey rectangle - it is the same trick as the bat's finger struts, which its own record
    calls "the tell".

    The membrane's trailing edge is a CURVE, tucked in toward the tip. Straight, the wing is a
    parallelogram; curved, it is a wing.
    """
    half = d["half"]
    n = struts = 0
    steps = max(8, int(half * 2))
    lead = []
    for i in range(steps + 1):
        t = i / steps
        s = side * half * t
        # the finger sweeps FORWARD and lifts as it goes out - a half-spread wing is held up
        f = d["shoulder_f"] + d["sweep"] * (t ** 1.35)
        y = d["shoulder_y"] + d["lift"] * math.sin(math.pi * 0.5 * t)
        lead.append((f, s, y))
    for i, (f, s, y) in enumerate(lead):
        t = i / steps
        # **THE FINGER IS DRAWN AS A RUN, NOT AS SAMPLES WITH A PATCH.** The hand-written corner
        # fill only mended a change in HEIGHT; where the sweep and the lift moved together the last
        # sample was diagonal to the one before it, and both wingtips - two cells each - came away
        # as floating components at spans 30 and 46 while every other span was fine. A bug that
        # passes the example you tried is the worst kind, so the run handles every corner.
        if i:
            n += _run(fr, lead[i - 1], (f, s, y), "wing_edge", protect=True)
        else:
            n += 1 if fr.put(f, s, y, "wing_edge", protect=True) else 0
        # the membrane, back from the finger: deep at the shoulder, tucked at the tip
        chord = d["chord"] * (1.0 - 0.72 * (t ** 1.6))
        k = 1
        while k <= chord:
            key = "wing_edge" if k >= chord - 0.6 else "wing"
            n += 1 if fr.put(f - k, s, y - k * d["droop"], key) else 0
            k += 1
        if i and i % max(2, steps // 4) == 0:       # a strut, so the sheet has structure in it
            for k in range(1, int(chord)):
                fr.put(f - k, s, y - k * d["droop"], "wing_edge")
            struts += 1
    return {"cells": n, "struts": struts, "tip": lead[-1]}


def _body(fr: _Frame, d: dict) -> int:
    """A short deep body sitting ON the wing root, with the legs tucked under it."""
    n = 0
    for i in range(d["body_len"]):
        t = i / max(1, d["body_len"] - 1)
        f = d["shoulder_f"] - d["body_len"] * 0.5 + i
        r = 1.0 + 1.4 * math.sin(math.pi * min(1.0, (t + 0.15) / 1.15))
        ri = int(math.ceil(r))
        for ds in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                if ds * ds + dy * dy > r * r:
                    continue
                key = "belly" if dy < -r * 0.35 else "body"
                n += 1 if fr.put(f, ds, d["shoulder_y"] + dy, key) else 0
    return n


def _head(fr: _Frame, d: dict) -> dict:
    """A long beak and the backswept crest, which is half of what names a pteranodon.

    **THE CREST MUST BREAK THE OUTLINE OR IT DOES NOTHING** - the lion's mane taught this island
    that a feature inside the silhouette is not a feature. It stands clear behind the skull and it
    is the one warm colour on the animal.
    """
    # **THE NECK STARTS INSIDE THE BODY, NOT IN FRONT OF IT.** Begun at the body's nominal front
    # face the two were a half-cell apart, `round()` sent them to different cells, and the head -
    # neck, beak, crest and both eyes, 35 cells - shipped as a separate floating component. A join
    # between two parts is made by OVERLAPPING them, never by abutting a computed edge.
    f0 = d["shoulder_f"] + d["body_len"] * 0.5 - 1.5
    y0 = d["shoulder_y"] + 1
    nk = d["neck"]
    hf, hy = f0 + nk * 0.8, y0 + nk * 0.7
    # **THE NECK RUNS FROM THE BODY'S CENTRE, NOT FROM ITS FACE.** Started at the front face it
    # joined at some spans and not others - span 38 shipped the whole head as a 42-cell floating
    # component while 34 and 40 were fine, which is the worst kind of bug: one that passes the
    # example you tried. A run that begins INSIDE the mass cannot miss it at any size.
    n = _run(fr, (d["shoulder_f"], 0, d["shoulder_y"]), (hf, 0, hy), "body", width=1)
    # the skull: three cells deep, so the beak leaves something rather than starting in mid-air
    for df in range(0, 3):
        for ds in (-1, 0, 1):
            n += 1 if fr.put(hf + df, ds, hy, "beak") else 0
    n += _run(fr, (hf + 2, 0, hy), (hf + d["beak"], 0, hy - 1.2), "beak")   # a long tapering beak
    # **THE CREST MUST BREAK THE OUTLINE OR IT DOES NOTHING** - the lion's mane taught this island
    # that a feature inside the silhouette is not a feature. Backswept, clear of the skull, and the
    # only warm colour on the animal.
    ct = d["crest"]
    crest = _run(fr, (hf, 0, hy + 1), (hf - ct * 0.9, 0, hy + 1 + ct * 0.85), "crest", protect=True)
    crest += _run(fr, (hf - 1, 0, hy + 1), (hf - ct * 0.55, 0, hy + 1 + ct * 0.5), "crest",
                  protect=True)
    eyes = 0
    for ds in (1, -1):
        eyes += 1 if fr.put(hf + 1, ds, hy + 1, "eye", protect=True) else 0
    return {"cells": n, "crest": crest, "eyes": eyes}


def _crag(fr: _Frame, d: dict, seed: int) -> dict:
    """The rock it stands on, so the design is self-contained.

    The bat's own record: *"the bat carries its own ceiling ... that freed it from competing with
    the birds for airspace."* Same idea upside down - a perch means this animal needs no roof
    somebody else built, and the Vantage Lookout, the obvious perch, is eight cells too narrow.
    """
    h = int(d["perch_h"])
    n = 0
    for y in range(h):
        t = y / max(1, h - 1)
        # **THE TOP MUST BE WIDE ENOUGH FOR THE FEET.** Tapered to 45% the crown was 1.5 of radius
        # and the claws stood at two cells out - so the animal and its own perch shipped as two
        # separate components, which is the bat perch's recorded failure the other way up.
        r = d["crag_r"] * (1.0 - 0.28 * t)
        ri = int(math.ceil(r))
        for df in range(-ri, ri + 1):
            for ds in range(-ri, ri + 1):
                if df * df + ds * ds > r * r:
                    continue
                q = hash01(df, ds, y, seed + 5)
                key = "rock" if q < 0.5 else ("rock_b" if q < 0.8 else "rock_c")
                if y == h - 1 and q < 0.35:
                    key = "moss"
                n += 1 if fr.put(d["shoulder_f"] - 1 + df, ds, y, key) else 0
    return {"cells": n, "height": h}


def _feet(fr: _Frame, d: dict) -> int:
    """Claws gripping the crag - **the one thing that stops it reading as a wing on a rock.**"""
    n = 0
    y = d["perch_h"] if d["perch_h"] else 0
    f = d["shoulder_f"] - 1
    for ds in (-2, 2):
        n += _run(fr, (f, ds, y), (f, ds, d["shoulder_y"]), "body")
        n += _run(fr, (f - 1, ds, y), (f + 1, ds, y), "claw")
        # ...and inboard to the crag's own crown, so the foot is ON the rock rather than beside it
        n += _run(fr, (f, ds, y), (f, ds - ds // 2, y), "claw")
    return n


def _stitch(c: Canvas, key: str = "wing_edge") -> dict:
    """Join anything the geometry left detached to the main mass, and REPORT how much.

    **CHASING EACH CASE DID NOT CONVERGE.** Three separate joins here came apart at some sizes and
    not others - a head at span 38, both wingtips at 30 and 46 - and every fix that patched one
    arithmetic corner left another. A generator whose contract is "one piece" should GUARANTEE it
    rather than hope the rounding is kind at the size somebody happens to pick, so the last pass
    measures the components it actually built and bridges the strays with a straight run.

    The count is returned rather than swallowed: a build that needs twenty cells of stitching is a
    build whose geometry is wrong, and the test asserts a low ceiling on it for that reason.
    """
    from collections import deque

    cells = {(v, y, u) for v in range(c.sx) for y in range(c.sy) for u in range(c.sz)
             if c.solid(v, y, u)}
    seen, comps = set(), []
    for start in cells:
        if start in seen:
            continue
        q, group = deque([start]), []
        seen.add(start)
        while q:
            v, y, u = q.popleft()
            group.append((v, y, u))
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (v + d[0], y + d[1], u + d[2])
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        comps.append(group)
    comps.sort(key=len, reverse=True)
    if len(comps) < 2:
        return {"strays": 0, "bridged": 0}
    main = set(comps[0])
    blk = c.state(HIDE[key])
    bridged = 0
    for group in comps[1:]:
        a = min(group, key=lambda p: min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
                                         + (p[2] - q[2]) ** 2 for q in main))
        b = min(main, key=lambda q: (a[0] - q[0]) ** 2 + (a[1] - q[1]) ** 2 + (a[2] - q[2]) ** 2)
        cur = list(a)
        for axis in (1, 0, 2):                       # up first, then along, then across
            while cur[axis] != b[axis]:
                cur[axis] += 1 if b[axis] > cur[axis] else -1
                if not c.solid(*cur):
                    c.put(cur[0], cur[1], cur[2], blk)
                    bridged += 1
        main.update(group)
    return {"strays": len(comps) - 1, "bridged": bridged}


def _dims(span: float, spread: float, perch_h: int) -> dict:
    """Everything as a fraction of the SPAN, so one number scales the animal.

    CLAUDE.md: *"Feature sizes must scale ... anything in absolute blocks has this latent"* - and
    the sauropod had exactly that, its legs and head frozen while its body grew.
    """
    S = float(span)
    return {
        "half": S * 0.5,
        "chord": max(3.0, S * 0.185),
        "sweep": S * 0.16 * (1.4 - spread),
        "lift": S * 0.30 * (1.15 - spread),
        "droop": 0.16 * (1.0 - spread) + 0.05,
        "shoulder_f": 0.0,
        "shoulder_y": perch_h + max(3, S * 0.10),
        "body_len": max(5, int(S * 0.20)),
        "neck": max(2, int(S * 0.075)),
        "beak": max(4, int(S * 0.235)),
        "crest": max(3, int(S * 0.135)),
        "crag_r": max(2.5, S * 0.10),
        "perch_h": perch_h,
    }


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PTEROSAUR, **(cfg or {})}
    span = float(p.get("span") or 34)
    if span < 16:
        raise ValueError("a pterosaur under a 16-block span has no membrane left to read; its "
                         "identity is the SHEET and a sheet needs room")
    spread = min(1.0, max(0.35, float(p.get("spread") or 0.72)))
    perch_h = int(p.get("perch_h") or 0) if p.get("perch") else 0
    d = _dims(span, spread, perch_h)
    seed = int(p.get("seed", 0))
    facing = str(p.get("facing", "west"))
    if facing not in _STEP:
        raise ValueError(f"a pterosaur needs a real facing, not {facing!r}")

    # **THE BOX IS SIZED BY THE FACING**, the sauropod's own recorded bug: a canvas always long in
    # X is long in the wrong axis for a north-south animal, and it clips the thing silently.
    length = int(d["body_len"] + d["neck"] + d["beak"] + d["chord"] + 10)
    width = int(span + 6)
    sy = int(d["shoulder_y"] + d["lift"] + d["crest"] + 8)
    along_x = facing in ("east", "west")
    sx = length if along_x else width
    sz = width if along_x else length
    c = Canvas(sx, sy, sz, donors)
    back = int(d["chord"] + d["body_len"] * 0.5 + 3)
    cv = back if along_x else sx // 2
    cu = sz // 2 if along_x else back
    if facing == "east":
        cv = sx - back
    if facing == "south":
        cu = sz - back
    fr = _Frame(c, cv, cu, facing)

    parts = {}
    if perch_h:
        parts["crag"] = _crag(fr, d, seed)
    parts["wings"] = [_wing(fr, d, 1), _wing(fr, d, -1)]
    parts["body"] = _body(fr, d)
    parts["head"] = _head(fr, d)
    parts["feet"] = _feet(fr, d) if perch_h else 0
    parts["stitch"] = _stitch(c)

    at_v, at_u = (int(x) for x in (p.get("at") or (0, 0)))
    ax, ay, az = (int(x) for x in p["anchor"])
    y = ay
    if p.get("under"):
        ctx = Ctx(p["under"])
        x0, z0 = ax + at_v, az + at_u
        for probe in range(ay + 60, ay - 12, -1):
            n = ctx.name_at(x0, probe, z0).split(":")[-1]
            if n not in ("air", "cave_air", "void_air", "moss_carpet"):
                y = probe + 1
                break
    c.world_origin = (ax + at_v - fr.cv, y, az + at_u - fr.cu)
    c.meta = {
        "kind": "pterosaur",
        "land": "frontier",
        "facing": facing,
        "span": round(span, 1),
        "spread": spread,
        "profile_axis": "u" if along_x else "v",
        "refused": fr.refused,
        "parts": parts,
        "contract": (
            "a pteranodon perched on its own crag: two membranes each hung from ONE elongated "
            "finger drawn as a dark leading edge, held half-spread so the outline steps rather "
            "than flattening, a short body sitting on the wing root, a long pale beak and a "
            "backswept crest that stands clear of the skull."),
    }
    return c
