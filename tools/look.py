"""LOOK at a build in 3D, from the angles a player actually gets, in one image.

    python tools/look.py "X elephant"                       # the orbit sheet: 8 bearings round it
    python tools/look.py "Lowland Frog" --sheet panel       # the review sheet, for a verdict
    python tools/look.py "Lowland Frog" --bearing 0 --pitch 4 --dist 0.5 --big     # one close look

WHO THIS IS FOR. Not a build sheet and not a presentation - this is the working loop for whoever is
SHAPING an animal: generate, look, change one thing, look again. The orthographic tools cannot close
that loop, because the three things that have actually gone wrong with animals here are invisible to
an axis projection. See `mcbuild/render3d.py` for that argument; the short version is that the
axolotl's head read as a blob in game and correct on every sheet, because projecting along the body
axis de-jags a diagonal by construction.

THE BEARING IS RELATIVE TO THE ANIMAL, NOT TO THE WORLD, and that is not a convenience. This repo
has already picked a view axis by hand and got it wrong twice in one session - "auditing an animal's
backside tells you nothing about its face" - so the sidecar's recorded `facing` decides where zero
is, exactly as `panel.py` chooses its profile axis:

    bearing   0   head-on, you are looking into its face
             90   profile
            180   tail-on
            270   the other profile

A design with no recorded facing says so and falls back to world +z, because a silent default here
is the same trap wearing a different hat.

PITCH is how far the camera is lifted above the horizon: 0 is a player's eye, and that is the
default, because a statue is seen from the ground and every flattering render in this repo so far
has been from above. 90 is the plan.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import render3d as r3, scan                          # noqa: E402
from mcbuild.gen.park import _STEP as _COMPASS                    # noqa: E402

WORDS = {0: "head-on", 45: "3/4 front", 90: "profile", 135: "3/4 rear",
         180: "tail-on", 225: "3/4 rear", 270: "profile", 315: "3/4 front"}


def _font(size: int):
    for p in ("C:/Windows/Fonts/segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def facing_yaw(meta: dict) -> tuple[float, bool]:
    """Camera yaw that puts you in FRONT of the build, and whether the sidecar actually said so.

    An ANIMAL records `facing` as a vector - the direction its own nose points, away from the
    body. A STRUCTURE (`mcbuild/gen/park.py` and everything built on it: casino, coaster,
    bigwheel, civic, frontiertown, hollowmanor, monument, streetfurniture) records it as a
    COMPASS WORD instead - "the direction the front looks out; a visitor stands in the +facing
    direction" (park.py's own docstring). Those are the SAME fact stated two ways: a visitor
    standing in +facing, looking back at the front door, is exactly the animal's camera standing
    off the nose looking back at the face. So a word is converted to the vector `park._STEP`
    already gives it - imported from there rather than re-guessed, because this project has
    picked a bearing convention by hand before and got it wrong twice in one session.

    A design with no recorded facing SAYS SO rather than defaulting quietly - the same rule for
    a missing vector and for a word that is not in `_STEP` (a typo, or a future kind that has not
    picked one yet).
    """
    f = (meta or {}).get("facing")
    if not f:
        return 0.0, False
    if isinstance(f, str):
        f = _COMPASS.get(f)
        if f is None:
            return 0.0, False
    fx, fz = float(f[0]), float(f[1])
    if fx == 0 and fz == 0:
        return 0.0, False
    return math.degrees(math.atan2(fx, fz)), True


def with_scale_figure(m, clear: int = 3):
    """A 1x2x1 player-height marker on the ground beside the build.

    "Is it big enough" is meaningless in the abstract and instant next to a person - `panel.py`
    already makes that argument with a flat blue bar. In perspective a bar pasted on the image would
    lie, because it has no depth; a real 1x2x1 in the scene stands on the same ground and casts the
    same shadow, so it shrinks with distance exactly as the animal does.
    """
    lo, hi = r3.content_box(m)
    out = m.copy()
    x = int(hi[0]) + clear
    y, z = int(lo[1]), int((lo[2] + hi[2]) / 2)
    sy, sz, sx = out.ids.shape
    padx = max(0, x + 1 - sx)
    if padx or y + 2 > sy or z >= sz:
        out.ids = np.pad(out.ids, ((0, max(0, y + 2 - sy)), (0, max(0, z + 1 - sz)), (0, padx)))
        sy, sz, sx = out.ids.shape
    if not (0 <= x < sx and 0 <= z < sz and y + 1 < sy):
        return m, False
    i = out.ensure_state("minecraft:blue_wool")
    out.ids[y, z, x] = i
    out.ids[y + 1, z, x] = i
    return out, True


def shot(m, yaw0: float, bearing: float, pitch: float, dist: float, w: int, h: int, **kw):
    cam = r3.orbit(m, yaw=yaw0 + bearing, pitch=pitch, dist=dist,
                   look_high=kw.pop("look_high", 0.45))
    return Image.fromarray(r3.render(m, cam, w, h, **kw))


def grid(panels, cols: int, title: str, sub: str = "") -> Image.Image:
    """Lay labelled panels out on one sheet. ONE image, because the point is to see them together -
    an animal that reads at 90 and dies at 45 is a fact about the animal, not about two renders."""
    fb, ft = _font(15), _font(19)
    pad, lab = 10, 22
    pw = max(p[0].width for p in panels)
    ph = max(p[0].height for p in panels)
    rows = (len(panels) + cols - 1) // cols
    top = 34 if title else 0
    W = pad + cols * (pw + pad)
    H = top + pad + rows * (ph + lab + pad)
    sheet = Image.new("RGB", (W, H), (246, 246, 248))
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((pad, 7), title, font=ft, fill=(20, 20, 24))
        if sub:
            d.text((pad + 8 + d.textlength(title, font=ft), 11), sub, font=fb, fill=(120, 120, 130))
    for i, (im, cap) in enumerate(panels):
        cx = pad + (i % cols) * (pw + pad)
        cy = top + pad + (i // cols) * (ph + lab + pad)
        sheet.paste(im, (cx, cy))
        d.rectangle([cx, cy, cx + im.width - 1, cy + im.height - 1], outline=(205, 205, 212))
        while d.textlength(cap, font=fb) > im.width - 4 and len(cap) > 4:
            cap = cap[:-2] + "…"          # a caption that runs into the next panel labels it
        d.text((cx + 2, cy + im.height + 4), cap, font=fb, fill=(45, 45, 55))
    return sheet


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design")
    ap.add_argument("--sheet", choices=("orbit", "panel", "one"), default="orbit")
    ap.add_argument("--bearing", type=float, default=0.0, help="degrees from head-on (sheet=one)")
    ap.add_argument("--pitch", type=float, default=8.0, help="0 = a player's eye, 90 = the plan")
    ap.add_argument("--dist", type=float, default=1.0, help="1 = framed, 0.5 = close, 4 = far")
    ap.add_argument("--big", action="store_true", help="one large panel instead of the sheet size")
    ap.add_argument("--no-ground", action="store_true", help="for anything that hangs in the void")
    ap.add_argument("--no-figure", action="store_true", help="drop the player-height marker")
    ap.add_argument("--no-shapes", action="store_true",
                    help="draw stairs and slabs as full cubes, as this tool always used to")
    ap.add_argument("--look-high", type=float, default=0.45,
                    help="what fraction up the build the camera aims: 0.85 is a head")
    ap.add_argument("--out")
    a = ap.parse_args()

    s = scan.load(a.design)
    m = s.model
    meta = getattr(s, "meta", None) or {}
    yaw0, known = facing_yaw(meta)
    name = os.path.splitext(os.path.basename(a.design))[0]
    out = a.out or f"out/look_{name.replace(' ', '_')}_{a.sheet}.png"

    figure = False
    if not a.no_figure:
        m, figure = with_scale_figure(m)
    # STAIRS AND SLABS GET THEIR REAL SHAPE, and only then. Subdividing is 2x the march and it
    # computes AO on the half-cell grid, so it changes the image - applied to everything it
    # would silently move every sheet in the repo. Applied to the models that actually contain
    # a shape block it changes exactly the ones that were being drawn WRONG. (AFTER the scale
    # figure, so the player marker is subdivided with the build and stays 2 blocks tall.)
    shaped = r3.has_shapes(m) and not a.no_shapes
    if shaped:
        m = r3.subdivide(m)
    kw = dict(ground=not a.no_ground, look_high=a.look_high)
    t0 = time.perf_counter()

    if a.sheet == "one":
        w, h = (1100, 800) if a.big else (720, 540)
        im = shot(m, yaw0, a.bearing, a.pitch, a.dist, w, h, **kw)
        im.save(out)
        cap = f"bearing {a.bearing:g} pitch {a.pitch:g} dist {a.dist:g}"
    elif a.sheet == "orbit":
        w, h = (440, 340) if a.big else (360, 280)
        bearings = [0, 45, 90, 135, 180, 225, 270, 315]
        panels = [(shot(m, yaw0, b, a.pitch, a.dist, w, h, **kw),
                   f"{b:>3}  {WORDS[b]}") for b in bearings]
        grid(panels, 4, name, f"eight bearings, pitch {a.pitch:g}").save(out)
        cap = "8 bearings"
    else:
        w, h = (420, 330) if a.big else (360, 280)
        panels = [
            (shot(m, yaw0, 0, a.pitch, 1.0, w, h, **kw), "  0  head-on"),
            (shot(m, yaw0, 90, a.pitch, 1.0, w, h, **kw), " 90  profile"),
            (shot(m, yaw0, 40, 26, 1.0, w, h, **kw), " 40  three-quarter, raised"),
            (shot(m, yaw0, 0, 88, 1.0, w, h, **kw), "     plan"),
            (shot(m, yaw0, 90, a.pitch, 1.0, w, h, silhouette=True, **kw),
             " 90  SILHOUETTE - name it from this alone"),
            (shot(m, yaw0, 90, a.pitch, 1.0, w, h, value=True, **kw),
             " 90  VALUE - a rounded body, or a flat shape with a pattern?"),
            (shot(m, yaw0, 40, a.pitch, 3.0, w, h, **kw), "     at distance (~3x)"),
            (shot(m, yaw0, 40, a.pitch, 6.0, w, h, **kw), "     at distance (~6x)"),
        ]
        grid(panels, 4, name, "the review sheet").save(out)
        cap = "panel"

    dt = time.perf_counter() - t0
    print(f"{out}   ({cap}, {dt:.1f}s)")
    print(f"  facing {meta.get('facing')}" + ("" if known else "  <-- NOT RECORDED, bearing 0 is world +z"))
    if figure:
        print("  the blue 1x2 column beside it is a player, standing on the same ground")
    if shaped:
        print("  stairs and slabs drawn at their REAL shape (2x2x2 half-cells)")
    if a.sheet == "panel":
        print("\n  Name it from the SILHOUETTE alone. If you cannot, nothing else matters.")
        print("  Where is the weight? Is there a line of action, or is the spine a straight rule?")
        print("  Does it still read at 6x - the distance anyone actually walks past it?")
        print("  Which of the eight bearings is the worst, and what would you change FIRST?")


if __name__ == "__main__":
    main()
