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

    panels = [_render(ids, cols, y0, sy, sx, sz, axis, a.zoom) for axis in a.views.split(",")]
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


def _render(ids, cols, y0, sy, sx, sz, axis, zoom):
    """Nearest surface along the view axis, shaded by how deep that surface sits."""
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
            hit = depth = None
            for d in range(D):
                c = probe(u, v, d)
                if c:
                    hit, depth = c, d
                    break
            if hit is None:
                continue
            # nearer is brighter: a plain silhouette hides every lump the shading reveals
            k = 1.06 - 0.42 * (depth / max(1, D - 1))
            r, g, b = (min(255, int(q * k)) for q in cols[hit])
            for dy in range(zoom):
                for dx in range(zoom):
                    px[u * zoom + dx, (H - 1 - v) * zoom + dy] = (r, g, b)
    return im


if __name__ == "__main__":
    main()
