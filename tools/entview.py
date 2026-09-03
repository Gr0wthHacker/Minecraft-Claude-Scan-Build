"""Render named plan-coordinate views of the assembled park.

    python tools/entview.py gate_approach court_axis wheel_axis

V is the cross axis (0 at the public edge), U the long axis, both in the WorldSpec lattice that
`tools/park_place.py` places into. The eye heights are above the build plane, not above the model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import render3d as r3, scan  # noqa: E402

ANCHOR = (97500, 202, 80300)
PLANE = 203
OUT = ROOT / "out" / "entrance"

#: name -> (eye V/U, target V/U, eye height, target height)
VIEWS = {
    #: THE EYE STANDS WHERE A PLAYER'S EYE IS: the floor course is h0, a visitor's feet are h1
    #: and their eye is h2. Put at h5 - which is a comfortable-looking number and three courses
    #: over a player's head - the camera renders the bunting as a wall across the view and the
    #: walk-up as a corridor, which is a picture of a park nobody is standing in.
    "gate_outside":  ((-22, 300), (40, 300), 3, 12),
    "gate_through":  ((10, 300), (95, 300), 2, 14),
    "court_axis":    ((21, 300), (100, 300), 2, 25),
    "court_walk":    ((36, 300), (100, 300), 2, 20),
    "court_high":    ((-10, 300), (95, 300), 45, 20),
    "wheel_axis":    ((60, 300), (95, 300), 2, 30),
    "court_plan":    ((60, 299), (60, 300), 120, 0),
    "gate_side":     ((60, 240), (5, 300), 20, 14),
    "court_iso2":    ((-6, 250), (55, 300), 30, 8),
    "arrival_north": ((50, 200), (50, 300), 12, 16),
    #: THE WHOLE ENTRANCE QUARTER IN ONE FRAME - the gate, the spur, the court, both avenues and
    #: the two cross walks. Every other view here is framed on the court, which is exactly why
    #: "I don't see it" was the right answer to a picture of the court.
    "quarter_plan":  ((47, 299), (47, 300), 145, 0),
    "cross_west":    ((51, 248), (51, 300), 4, 6),
    "cross_east":    ((51, 352), (51, 300), 4, 6),
    "court_close":   ((22, 300), (55, 300), 3, 6),
    "court_iso":     ((5, 258), (55, 305), 26, 6),
    "court_top":     ((49, 299), (49, 300), 70, 0),
    "lamp_close":    ((26, 262), (32, 269), 4, 5),
}


def main(names) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    s = scan.load(str(ROOT / "out" / "Park Complete.litematic"))
    ox, oy, oz = s.origin
    m = s.model
    print(f"model {m.ids.shape} origin {s.origin}")
    for name in names or VIEWS:
        eye, tgt, eh, th = VIEWS[name]
        e = (eye[0] + ANCHOR[0] - ox, PLANE + eh - oy, eye[1] + ANCHOR[2] - oz)
        t = (tgt[0] + ANCHOR[0] - ox, PLANE + th - oy, tgt[1] + ANCHOR[2] - oz)
        cam = r3.Camera(tuple(map(float, e)), tuple(map(float, t)), fov=55.0)
        px = r3.render(m, cam, 1280, 800, ground=False)
        Image.fromarray(np.asarray(px, dtype=np.uint8)).save(OUT / f"{name}.png")
        print("wrote", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
