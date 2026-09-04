"""A LABELLED PLAN OF THE ENTRANCE QUARTER, drawn from the shipped park cell by cell.

    python tools/entplan.py

`render3d` is a camera, and a camera framed on the court cannot show the court's connections -
which is exactly the answer Jack gave a picture of the court: *"i dont see it."* This is not a
render at all: every pixel is one cell of `out/Park Complete.litematic`, coloured by what that
cell IS rather than by how light falls on it, with the streets named.

**IT CANNOT FLATTER THE BUILD.** A path is drawn only where the shipped file holds paving, so a
connection that is not there cannot appear here, and one that is there cannot be missed.

Output: ``out/entrance/quarter_labelled.png``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import schem  # noqa: E402

PARK = ROOT / "out" / "Park Complete.litematic"
OUT = ROOT / "out" / "entrance" / "quarter_labelled.png"

V0, V1, U0, U1 = 0, 145, 250, 350     # the quarter: gate, court, midway row, wheel
SCALE = 7                              # pixels per block

LAWN = {"moss_block", "moss_carpet"}
#: (name test, colour). Ordered - the first match wins, so the specific cases precede the field.
KEY = [
    (lambda n: n in LAWN, (104, 138, 66), "lawn"),
    (lambda n: n in ("red_wool", "white_wool"), (206, 106, 106), "street banding"),
    (lambda n: n == "polished_blackstone_bricks", (58, 56, 62), "kerb"),
    # THE PAVILION IS TESTED BEFORE THE STEP, and that order is the whole difference between a
    # diagram and a misleading one: its roof is made of STAIRS, so tested the other way round a
    # canvas roof came out in the colour that means "a step you can walk up" - and the two places
    # a reader is looking hardest at in this picture are the thresholds.
    (lambda n: "crimson" in n or "diorite" in n, (150, 92, 104), "pavilion"),
    (lambda n: "stairs" in n, (232, 198, 96), "step"),
    (lambda n: n == "water", (76, 130, 220), "water"),
    (lambda n: "leaves" in n or n == "azalea", (58, 112, 48), "planting"),
    (lambda n: True, (176, 176, 178), "paving"),
]

#: (V, U, text, anchor) - anchor 'l' draws right of the point, 'r' left of it.
LABELS = [
    (10, 268, "THE SPINE", "l"),
    (21, 300, "13-WIDE SPUR  gate -> court", "l"),
    (51, 260, "WEST AVENUE  U260", "l"),
    (51, 341, "EAST AVENUE  U341", "l"),
    (51, 266, "cross walk", "l"),
    (51, 334, "cross walk", "l"),
    (51, 300, "THE WELCOME COURT", "l"),
    (100, 300, "MIDWAY ROW  8 stalls", "l"),
    (138, 300, "THE BIG WHEEL", "l"),
]


def main() -> int:
    if not PARK.exists():
        raise SystemExit("out/Park Complete.litematic is not shipped")
    m = schem.load(str(PARK))
    o = json.loads(PARK.with_suffix(".scan.json").read_text(encoding="utf-8"))["origin"]
    ox, oy, oz = int(o["x"]), int(o["y"]), int(o["z"])
    names = [n.split(":")[-1].split("[")[0] for n in m.names]

    def surface(v, u):
        """The topmost block in the walking band - the thing a visitor sees underfoot."""
        x, z = v + 97500 - ox, u + 80300 - oz
        for y in range(212, 201, -1):
            slot = int(m.ids[y - oy, z, x])
            if slot:
                return names[slot]
        return None

    w, h = (V1 - V0 + 1) * SCALE, (U1 - U0 + 1) * SCALE
    img = Image.new("RGB", (w, h), (28, 30, 34))
    d = ImageDraw.Draw(img)
    for v in range(V0, V1 + 1):
        for u in range(U0, U1 + 1):
            n = surface(v, u)
            if n is None:
                continue
            colour = next(c for test, c, _label in KEY if test(n))
            px, py = (v - V0) * SCALE, (u - U0) * SCALE
            d.rectangle([px, py, px + SCALE - 1, py + SCALE - 1], fill=colour)

    for v, u, text, anchor in LABELS:
        px, py = (v - V0) * SCALE, (u - U0) * SCALE
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(255, 255, 255),
                  outline=(20, 20, 20), width=2)
        tx = px + 10 if anchor == "l" else px - 10 - d.textlength(text)
        d.text((tx + 1, py - 6), text, fill=(0, 0, 0))
        d.text((tx, py - 7), text, fill=(255, 255, 255))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT}  ({w}x{h}, V{V0}-{V1} across, U{U0}-{U1} down)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
