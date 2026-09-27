"""THE ABYSS JELLY - a giant bioluminescent jellyfish drifting in the dark under the park, the
squid's companion in the void and the second thing a Prism Well runner discovers.

Jack chose a jellyfish and the whole void. It is here for the same reason the squid is: it is one
of the three shapes voxels render natively, with no compound muscle anywhere, and CLAUDE.md names
the category outright -

    the BELL is a convex DOME carrying a pattern - the ladybird's own class, and `balloon.py`'s
                                                  "a dome on lines over a box"
    the ORAL ARMS are a few thick trailing columns - tapers
    the TENTACLES are many long thin streamers    - the drifting cue, and pure line

A jellyfish's identity is entirely its silhouette - a lit bell over a curtain of tentacles - and
the silhouette is what this medium keeps and a photograph of muscle is what it loses.

IT LIGHTS ITSELF, because the void is pitch dark at every hour and a dark jelly is invisible. The
bell margin is a ring of `ochre_froglight` (the one full-block light WITNESSED in a world capture -
the same rule the squid records: the tier table and `out/` are both circular), the bell carries
amethyst spots for violet, and the tentacle tips are berried `cave_vines` (light 14) - the thicket
already lights hanging gardens with them.

The BELL IS A WOOL LANTERN WITH GLASS PANELS - not a solid glass dome. Glass is smelted sand and a
full glass shell ran 6000 blocks, so the dome is opaque wool cut into `bell_windows` vertical PANELS
of `light_blue_stained_glass`, wool struts between them. The inner glow (crown cap, manubrium core)
shines THROUGH the panels, so the jelly reads as lit-from-within against the pitch void - the point
of glass - while the wool struts carry the body and hold the glass budget under ~700. `window_frac`
is the glass share of each sector; the skirt, stomach, oral arms and tentacle curtain are all wool.

TRAPS, each shipped clean once in this repo:

  - A TENTACLE IS PURE LINE and line is where 6-connectivity bites: a streamer stepped by hand is
    a chain of diagonal neighbours (the cat's ear tips came off this way). Every streamer is laid
    as a connected thread, filling the corner where two axes change at once.
  - Anything glowing that CLINGS is anchored to a real cell: `glow_lichen` takes a solid face and
    `cave_vines` hang from a solid block above, or they are the frog's silently-missing nostrils.
  - Centres are INTEGER and offsets are added to them (`round()` is banker's rounding).
  - `Canvas.solid()`, never `if get()` (-1 out of bounds is truthy).
  - Nothing enters the Prism Well's fall column: `keep_out` refuses every cell through the one
    `put`, and the closest approach is reported rather than trusted.

WHAT IT DOES NOT CLAIM. It hangs in void, so it floats, and the audit says so - `drop_floaters`
off, like the squid. Judge form off `tools/look.py`; the glow, which is the whole point, only
shows in game because `render3d` has no emission.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01

JELLY = {
    "seed": 3,
    "scale": 1.0,
    "at": None,                       # world cell of canvas corner (0,0,0); set by the config
    "keep_out": None,                 # (x, z, r) the well's fall column, refused per cell

    # ---- the bell. A squashed dome: R across, H tall, a shell `bell_t` thick with a hollow cup
    # under it (a real bell is a cup, and a hollow shell reads better and costs a third).
    "bell_r": 15.0,
    "bell_h": 12.0,
    "bell_t": 2,
    "bell_windows": 10,              # the dome is a WOOL lantern with this many glass panels round it
    "window_frac": 0.34,             # fraction of each sector that is glass (the rest is wool strut)
    "margin_flare": 3.0,              # how far the rim curls outward past the dome
    "margin_drop": 4.0,              # ...and down: the bell skirt

    # ---- the mouth. A few thick frilly oral arms from the centre underside.
    "oral_arms": 4,
    "oral_len": 14.0,
    "oral_r": 2.2,

    # ---- the tentacles. Many long thin streamers off the margin, curving out then trailing down.
    "tentacles": 18,
    "tent_len": 46.0,
    "tent_out": 0.35,                 # how far the tip swings outward, as a fraction of tent_len
    "tent_wave": 0.5,                 # sideways wander, so they do not fall as a stiff cage
    "bead_every": 6,                  # a froglight bead this often down a tentacle

    # ---- palette, witnessed and cheap, coherent with the squid and the drift
    "bell": "light_blue_wool",            # the wool lantern body of the dome (opaque struts)
    "bell_glass": "light_blue_stained_glass",  # the glass panels the inner glow shines through
    "bell_rib": "white_wool",             # opaque radial canals framing the glass panels
    "under": "cyan_wool",                 # the shaded underside/skirt and stomach
    "oral": "pink_wool",              # the mouth-arms, the squid's own pink
    "tent": "light_blue_wool",        # the streamers' core
    "rim": "ochre_froglight",         # the margin's ring of light
    "spot": "amethyst_cluster",       # violet photophores on the bell
}

_AXES = {"east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0),
         "south": (0, 0, 1), "north": (0, 0, -1)}


def _facing(dx, dy, dz):
    for name, v in _AXES.items():
        if v == (dx, dy, dz):
            return name
    return None


class _Body:
    """The one gate. keep_out is refused here so a part added later cannot forget it."""

    def __init__(self, c, at, ko):
        self.c = c
        self.at = at
        self.ko = ko
        self.n = 0
        self.closest = float("inf")

    def put(self, x, y, z, blk) -> bool:
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if not self.c.inb(x, y, z):
            return False
        if self.ko:
            d = math.hypot(self.at[0] + x - self.ko[0], self.at[2] + z - self.ko[1])
            if d < self.ko[2]:
                return False
            if d < self.closest:
                self.closest = d
        self.c.ids[y, z, x] = blk
        self.n += 1
        return True

    def paint(self, x, y, z, blk) -> bool:
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if not self.c.inb(x, y, z) or self.c.ids[y, z, x] == 0:
            return False
        self.c.ids[y, z, x] = blk
        return True

    def solid(self, x, y, z) -> bool:
        return self.c.solid(int(round(x)), int(round(y)), int(round(z)))


def build(cfg: dict, donors=None) -> Canvas:
    p = {**JELLY, **(cfg or {})}
    sc = float(p.get("scale", 1.0))
    seed = int(p["seed"])
    R = float(p["bell_r"]) * sc
    H = float(p["bell_h"]) * sc
    t = max(1, int(round(float(p["bell_t"]) * sc)))
    flare = float(p["margin_flare"]) * sc
    drop = float(p["margin_drop"]) * sc
    TL = float(p["tent_len"]) * sc
    OL = float(p["oral_len"]) * sc

    # ---- the frame. The bell sits at the top; tentacles and arms hang below it, and swing out by
    # tent_out. Sized so nothing is clipped - a canvas one course short truncates silently and
    # still renders as a plausible jelly (the sauropod's own recorded bug).
    reach = (R + flare + TL * float(p["tent_out"]) + TL * float(p["tent_wave"]) * 0.5) * 1.1
    half = int(math.ceil(reach)) + 3
    XC = ZC = half                                    # INTEGER centres, so anything mirrored is exact
    SX = SZ = 2 * half + 1
    # +Y IS UP. The crown is HIGH, the margin below it, the tentacles hang DOWN to low y. The first
    # build had this inverted - crown at the floor, tentacles rising - and it renders as a plausible
    # jelly from every orthographic angle while being upside down in game. margin_y leaves room
    # below it for the whole tentacle curtain.
    margin_y = int(math.ceil(TL)) + int(math.ceil(drop)) + 3
    crown_y = margin_y + int(math.ceil(H))
    SY = crown_y + 4

    c = Canvas(SX, SY, SZ, donors)
    at = tuple(int(v) for v in p["at"]) if p.get("at") else (0, 0, 0)
    ko = tuple(float(v) for v in p["keep_out"]) if p.get("keep_out") else None
    b = _Body(c, at, ko)

    S = {k: c.state(p[k]) for k in ("bell", "bell_glass", "bell_rib", "under", "oral", "tent", "rim")}
    counts = {"bell": 0, "glass": 0, "rim": 0, "spots": 0, "oral": 0, "tentacles": 0, "beads": 0}
    nwin = max(1, int(p["bell_windows"]))
    wfrac = float(p["window_frac"])

    # ---- THE BELL: the top half of a squashed ellipsoid, built as a SHELL (a real bell is a cup,
    # and a hollow shell reads better and costs a third). The ellipsoid is centred on the margin
    # ring: crown at margin_y + H, equator at margin_y. The shell is a WOOL lantern cut into nwin
    # vertical GLASS PANELS - a central glass wedge of angular width wfrac in each sector, a white
    # wool rib on the seam between panels, plain wool everywhere else. The crown cap (dyn near 1)
    # stays solid wool for the froglight disc to sit on.
    twin = 2 * math.pi / nwin
    for y in range(margin_y, crown_y + 1):
        dyn = (y - margin_y) / H                       # 0 at margin, 1 at crown
        for z in range(SZ):
            for x in range(SX):
                q = ((x + 0.5 - XC) / R) ** 2 + dyn ** 2 + ((z + 0.5 - ZC) / R) ** 2
                if abs(math.sqrt(max(q, 1e-9)) - 1.0) * min(R, H) <= t:
                    seg = (math.atan2(z + .5 - ZC, x + .5 - XC) / twin) % 1.0
                    off = abs(seg - 0.5) * 2                # 0 at panel centre, 1 at the seam
                    if dyn < 0.82 and off < wfrac:
                        blk = S["bell_glass"]
                        counts["glass"] += 1
                    elif dyn < 0.82 and off > 0.94:
                        blk = S["bell_rib"]                 # white strut on the seam
                    else:
                        blk = S["bell"]
                    if b.put(x, y, z, blk):
                        counts["bell"] += 1
    # A FROGLIGHT CROWN CAP, so the dome itself carries light in the pitch dark rather than reading
    # as a bare ring of rim lights around a black cap. A small lit disc at the apex.
    for z in range(int(ZC - 3), int(ZC + 4)):
        for x in range(int(XC - 3), int(XC + 4)):
            if math.hypot(x + .5 - XC, z + .5 - ZC) <= 2.4:
                b.paint(x, crown_y, z, S["rim"])
                b.paint(x, crown_y - 1, z, S["rim"])
    # the flared skirt: rings stepping outward and DOWN from the margin, a thick curled lip
    for i in range(1, int(math.ceil(drop)) + 1):
        yy = margin_y - i
        rr = R + flare * (i / max(1.0, drop))
        for z in range(SZ):
            for x in range(SX):
                rho = math.hypot(x + 0.5 - XC, z + 0.5 - ZC)
                if rr - 1.4 <= rho <= rr + 0.6:
                    if b.put(x, yy, z, S["under"]):
                        counts["bell"] += 1

    # ---- THE MANUBRIUM: a solid glowing stalk down the axis from the crown to just below the
    # margin - the stomach. Without it the oral arms hang from the hollow centre of a cup and come
    # off as a separate component (the first build's 179-cell orphan). It carries a froglight core.
    manub_r = max(1.6, R * 0.14)
    manub_bot = margin_y - 1
    for y in range(manub_bot, crown_y - 1):
        rr = manub_r * (0.7 + 0.5 * (crown_y - y) / max(1.0, crown_y - manub_bot))
        for z in range(int(ZC - rr - 1), int(ZC + rr + 2)):
            for x in range(int(XC - rr - 1), int(XC + rr + 2)):
                d = math.hypot(x + 0.5 - XC, z + 0.5 - ZC)
                if d <= rr:
                    b.put(x, y, z, S["rim"] if d <= 0.8 else S["under"])

    # ---- THE MARGIN RING OF LIGHT, and amethyst spots up the dome.
    R_eq = R + flare * 0.15
    for deg in range(0, 360, 3):
        a = math.radians(deg)
        if b.put(XC + math.cos(a) * R_eq, margin_y, ZC + math.sin(a) * R_eq, S["rim"]):
            counts["rim"] += 1
    # spots: walk outward along a ray from the axis at a chosen height, find the outermost solid
    # cell of the dome and hang a cluster on the air past it - the surface-probe rule, never a
    # computed radius, so a spot is always ON the shell however lumpy it came out.
    for i in range(int(R * 1.6)):
        a = hash01(seed, i, 1) * 2 * math.pi
        yy = margin_y + int(round((hash01(seed, i, 2) ** 0.6) * (H - 1)))
        ux, uz = math.cos(a), math.sin(a)
        last = None
        for rr in range(1, int(R + flare + 2)):
            x2, z2 = XC + ux * rr, ZC + uz * rr
            if b.solid(x2, yy, z2):
                last = (int(round(x2)), int(round(z2)))
            elif last is not None:
                ox, oz = int(round(XC + ux * (rr))), int(round(ZC + uz * (rr)))
                face = _facing(1 if ox > last[0] else (-1 if ox < last[0] else 0), 0,
                               1 if oz > last[1] else (-1 if oz < last[1] else 0))
                if face and b.put(ox, yy, oz, c.state(p["spot"], facing=face, waterlogged="false")):
                    counts["spots"] += 1
                break

    # ---- THE ORAL ARMS: thick frilly columns from the manubrium's foot, hanging and curling out.
    for k in range(int(p["oral_arms"])):
        a = 2 * math.pi * k / int(p["oral_arms"]) + 0.4
        pts = []
        n = int(OL) + 2
        for j in range(n):
            f = j / (n - 1)
            swing = OL * 0.30 * f * f
            pts.append((XC + math.cos(a) * swing,
                        manub_bot - OL * f,                   # hang DOWN from the stalk's foot
                        ZC + math.sin(a) * swing))
        _thread(b, pts, float(p["oral_r"]) * sc, S["oral"], taper=True)
        counts["oral"] += 1

    # ---- THE TENTACLES: many long thin streamers off the margin, swinging out then trailing DOWN
    # with a gentle per-strand wander, beaded with froglight and tipped with a glowing cave-vine.
    nt = int(p["tentacles"])
    frog = c.state(p["rim"])
    for k in range(nt):
        a = 2 * math.pi * k / nt
        out = TL * float(p["tent_out"])
        wave = TL * float(p["tent_wave"])
        ph = hash01(seed, k, 7) * 2 * math.pi
        pts = []
        n = int(TL) + 2
        r0 = R_eq
        for j in range(n):
            f = j / (n - 1)
            rr = r0 + out * (1 - (1 - f) ** 2)
            ta = a + (wave * math.sin(f * 3.0 + ph) * f) / max(1.0, rr)
            pts.append((XC + math.cos(ta) * rr,
                        margin_y - f * TL,                    # hang DOWN
                        ZC + math.sin(ta) * rr))
        _thread(b, pts, 0.0, S["tent"], taper=False)
        counts["tentacles"] += 1
        for j in range(int(p["bead_every"]), n, int(p["bead_every"])):
            f = j / (n - 1)
            rr = r0 + out * (1 - (1 - f) ** 2)
            ta = a + (wave * math.sin(f * 3.0 + ph) * f) / max(1.0, rr)
            if b.paint(XC + math.cos(ta) * rr, margin_y - f * TL, ZC + math.sin(ta) * rr, frog):
                counts["beads"] += 1
        # a glowing cave-vine tip, hanging from the streamer's lowest cell
        tipx = int(round(XC + math.cos(a) * (r0 + out)))
        tipz = int(round(ZC + math.sin(a) * (r0 + out)))
        tipy = margin_y - int(TL)
        if b.solid(tipx, tipy, tipz):
            _cavevine(b, c, tipx, tipy, tipz, 2 + int(hash01(seed, k, 9) * 3), seed, k)

    if p.get("at"):
        c.world_origin = at
    c.meta = {
        "kind": "jelly", "scale": sc, "facing": [0, 1],
        "keep_out": list(ko) if ko else None,
        "closest_to_keep_out": None if b.closest == float("inf") else round(b.closest, 1),
        "features_built": counts,
    }
    return c


def _thread(b, pts, r, blk, *, taper):
    """A connected thread through pts, filling the corner where two axes change at once, so a
    hand-stepped streamer is never a chain of diagonal-only neighbours (the ear-tip rule)."""
    prev = None
    n = len(pts)
    for i, (px, py, pz) in enumerate(pts):
        rr = r
        if taper and r > 0:
            rr = max(0.0, r * (1 - i / n))
        cx, cy, cz = int(round(px)), int(round(py)), int(round(pz))
        if rr >= 0.6:
            b.ball((cx, cy, cz), rr, blk)
        else:
            b.put(cx, cy, cz, blk)
        if prev is not None:
            # bridge any gap between prev and this cell one axis at a time
            x0, y0, z0 = prev
            for (a0, a1, ax) in ((x0, cx, 0), (y0, cy, 1), (z0, cz, 2)):
                step = 1 if a1 > a0 else -1
                v = a0
                while v != a1:
                    v += step
                    q = [x0, y0, z0]
                    q[ax] = v
                    if ax >= 1:
                        q[0] = cx
                    if ax >= 2:
                        q[1] = cy
                    b.put(q[0], q[1], q[2], blk)
        prev = (cx, cy, cz)


def _cavevine(b, c, x, y, z, drop, seed, k):
    """A berried cave-vine hanging DOWN from the solid cell at (x,y,z): the glowing tentacle tip."""
    run = []
    for i in range(1, drop + 1):
        yy = y - i
        if not c.inb(x, yy, z) or b.solid(x, yy, z):
            break
        run.append(yy)
    for i, yy in enumerate(run):
        bs = "false" if hash01(seed, k, yy, 3) < 0.2 else "true"
        if i == len(run) - 1:
            b.put(x, yy, z, c.state("cave_vines", berries=bs, age="25"))
        else:
            b.put(x, yy, z, c.state("cave_vines_plant", berries=bs))


# _Body needs a ball helper like the squid's; add it here to keep the class small above.
def _ball(self, p, r, blk) -> int:
    cx, cy, cz = float(p[0]), float(p[1]), float(p[2])
    n = 0
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        dy2 = (y + 0.5 - cy) ** 2
        for z in range(int(cz - r - 1), int(cz + r + 2)):
            dz2 = (z + 0.5 - cz) ** 2
            if dy2 + dz2 > r * r:
                continue
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x + 0.5 - cx) ** 2 + dy2 + dz2 <= r * r:
                    n += 1 if self.put(x, y, z, blk) else 0
    return n


_Body.ball = _ball
