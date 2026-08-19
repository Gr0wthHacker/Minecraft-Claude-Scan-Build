"""Big orthographic views of a design, for judging FORM - which a contact-sheet card is too small for.

    python tools/views.py "Void Giraffe" --zoom 10 --out out/giraffe_views.png
    python tools/views.py "Void Giraffe" --crop-top 15          # just the head

Three things it does that `mcbuild card` does not, all of which matter when the question is "does this
read as the animal":

  * takes the NEAREST surface block along the view axis, not a middle slice, so you see the skin
  * shades by depth, so a flat silhouette becomes a form you can actually judge roundness on
  * zooms, so a face is big enough to criticise

The card stays the thing for a build sheet - counts, shulkers, paste origin. This is for looking.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcbuild import palette, scan            # noqa: E402
from mcbuild.gen import shell                # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("design")
    ap.add_argument("--zoom", type=int, default=8)
    ap.add_argument("--crop-top", type=int, default=0, help="only the top N courses (e.g. a head)")
    ap.add_argument("--views", default="side,face,top",
                    help="comma list of side,face,rear,front,top. `face` looks from the FAR z end - "
                         "for a design facing +z that is the one showing you its face; `rear` is the "
                         "z=0 end. Getting these backwards means auditing an animal's backside.")
    ap.add_argument("--out", default="out/views.png")
    a = ap.parse_args()

    s = scan.load(a.design)
    ids = s.model.ids
    names = [n.split(":")[-1].split("[")[0] for n in s.model.names]
    cols = {i: palette.color_of(n) for i, n in enumerate(names)}
    sy, sz, sx = ids.shape
    y0 = max(0, sy - a.crop_top) if a.crop_top else 0

    part = {}
    for i, n in enumerate(s.model.names):
        frac = shell.volume_fraction(n)
        if frac < 1.0:
            half = "top" if "type=top" in n else "bottom"
            part[i] = (frac, half)
    panels = [_render(ids, cols, y0, sy, sx, sz, axis, a.zoom, part) for axis in a.views.split(",")]
    gap = 18
    W = sum(p.width for p in panels) + gap * (len(panels) - 1)
    H = max(p.height for p in panels)
    out = Image.new("RGB", (W, H), (255, 255, 255))
    x = 0
    for p in panels:
        out.paste(p, (x, 0))
        x += p.width + gap
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out)
    print(f"{a.out}  {out.size[0]}x{out.size[1]}   ({' | '.join(a.views.split(','))})")


def _render(ids, cols, y0, sy, sx, sz, axis, zoom, part=None):
    """Nearest surface along the view axis, shaded by how deep that surface sits.

    `part` maps a palette index to (fill fraction, which half) for blocks that do not fill their
    cell. Without it a slab draws as a full cube and half-block surfacing is INVISIBLE here - which
    would make this tool agree that nothing had changed while the game showed something smoother.
    The validation in this repo is already circular enough (we render with the same colour table the
    palette picker optimises against); it must not also be blind to the geometry.
    """
    if axis == "side":                      # look along +x
        W, H, D = sz, sy - y0, sx
        def probe(u, v, d): return int(ids[v + y0, u, d])
    elif axis in ("rear", "front"):         # look along +z: sees the z=0 end first
        W, H, D = sx, sy - y0, sz
        def probe(u, v, d): return int(ids[v + y0, d, u])
    elif axis == "face":                    # look along -z: sees the high-z end first
        W, H, D = sx, sy - y0, sz
        def probe(u, v, d): return int(ids[v + y0, sz - 1 - d, sx - 1 - u])
    else:                                   # top-down, look along -y
        W, H, D = sx, sz, sy - y0
        def probe(u, v, d): return int(ids[sy - 1 - d, v, u])

    im = Image.new("RGB", (W * zoom, H * zoom), (247, 247, 247))
    px = im.load()
    for v in range(H):
        for u in range(W):
            # Collect hits until the cell is visually full. A partial block covers only part of its
            # cell, and whatever stands BEHIND it shows through the rest - so stopping at the first
            # hit painted the background into the gap and drew white slots through the elephant's
            # ears that do not exist. Draw the near partial, then keep looking for something to
            # fill the remainder.
            spans = []                                   # (lo, hi, colour) in cell-local rows
            free = [(0, zoom)]
            for d in range(D):
                c = probe(u, v, d)
                if not c:
                    continue
                k = 1.06 - 0.42 * (d / max(1, D - 1))
                rgb = tuple(min(255, int(q * k)) for q in cols[c])
                frac, half = (part or {}).get(c, (1.0, None))
                if frac >= 1.0 or axis == "top" or zoom < 2:
                    lo, hi = 0, zoom
                else:
                    # `dy` counts DOWN the image inside the cell, so a bottom slab is the high rows
                    n = max(1, int(round(zoom * frac)))
                    lo, hi = (zoom - n, zoom) if half == "bottom" else (0, n)
                still = []
                for f0, f1 in free:
                    a, b_ = max(f0, lo), min(f1, hi)
                    if a < b_:
                        spans.append((a, b_, rgb))
                    if f0 < a:
                        still.append((f0, a))
                    if b_ < f1:
                        still.append((b_, f1))
                free = still
                if not free:
                    break
            for lo, hi, rgb in spans:
                for dy in range(lo, hi):
                    for dx in range(zoom):
                        px[u * zoom + dx, (H - 1 - v) * zoom + dy] = rgb
    return im


if __name__ == "__main__":
    main()
