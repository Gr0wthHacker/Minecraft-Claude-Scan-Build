"""The human review packet for the WorldSpec park.

PARK_VISUAL_AND_BUDGET_SPEC.md lists the views a human must sign off before detail is promoted,
and it is the only gate this pipeline cannot answer for itself: "Reject a view if a landmark has
no readable silhouette, one module blocks another's approach view, a creature looks detached, or
bright accents flatten the hierarchy." Nothing about a block count sees any of those.

Every view is rendered with `mcbuild/render3d.py` - perspective, cast shadows, corner AO, real
stair and slab shapes - never a second renderer.

    python tools/parkpacket.py                 the whole packet
    python tools/parkpacket.py --view spire    one view
    python tools/parkpacket.py --big           1280x800 instead of 900x560

**CAMERAS ARE PLACED IN PLAN COORDINATES, NOT BY AUTO-FRAMING.** `r3.orbit` centres on content
and picks its own distance, which is right for one sculpture and wrong for a park: it hovers over
the middle of the plot looking down, which is not where anybody stands. Each view below names the
V/U point a visitor occupies and the V/U point they are looking at, straight out of the build
spec's own lot schedule, so the packet shows the approach the spec asks about rather than a
convenient angle.

**WHAT THIS DOES NOT JUDGE: COLOUR.** Every block is drawn as one flat RGB from the same database
the palette picker optimises against - this repo's oldest recorded circularity. Judge form, mass,
silhouette and occlusion here; judge palette in game.

Output goes to ``out/park_final/packet/``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import render3d as r3, scan, worldspec  # noqa: E402

OUT = ROOT / "out" / "park_final" / "packet"
PLACED = ROOT / "out" / "park_final" / "placed"

#: Night is not a colour filter - it is a different SUN and a much weaker key, so a build whose
#: only legibility comes from daylight silhouette is exposed rather than flattered.
NIGHT = {"sun": (-0.35, 0.55, -0.25), "bg": (26, 30, 44), "shadow_strength": 0.12,
         "ao_strength": 0.75}

#: name -> (eye V/U, target V/U, eye height above the build plane, target height, note)
#: V is depth from the public edge, U is the long axis - the plan's own lattice.
VIEWS = {
    # EVERY EYE STANDS ON THE PUBLIC SPINE (V12) or on a declared route, because that is where a
    # visitor is. Placed a few blocks into a lot instead, the camera sits inside the building it
    # was meant to be looking at, and renders a black frame that looks like a broken renderer.
    "arrival":        ((-25, 170), (70, 300), 22, 35, "park arrival facing Midway"),
    "frontier":       ((-40, 40), (85, 125), 30, 45, "Frontier approach and the Mine Ridge profile"),
    "midway_court":   ((-30, 250), (110, 330), 30, 45, "Midway court facing Sky Lift and the Sloth"),
    "prism_reach":    ((12, 380), (45, 430), 4, 22, "Prism Reach facing Foundry Gate and the Wyrm"),
    "foundry_spire":  ((12, 430), (70, 562), 6, 70, "Foundry Gate facing the Spire"),
    "spire_day":      ((12, 560), (70, 562), 6, 80, "Prism Spire, day"),
    "spire_night":    ((12, 560), (70, 562), 6, 80, "Prism Spire, night"),
    "spire_launch":   ((12, 520), (70, 562), 100, 100, "Prism Spire at launch level"),
    "spire_catch":    ((12, 520), (70, 562), 14, 12, "Prism Spire at catch level"),
    "forge_deck":     ((12, 500), (75, 560), 8, 60, "Forge Deck side, looking back at the Spire"),
    "heron":          ((12, 20), (67, 20), 12, 35, "Signal Heron at its intended approach"),
    "heron_close":    ((36, 20), (67, 20), 34, 44, "Signal Heron, close"),
    "sloth":          ((12, 358), (118, 358), 6, 18, "Sky Lift Sloth from below"),
    "wyrm":           ((12, 400), (48, 405), 5, 14, "Wyrm's Crossing at its approach"),
    # the composition view: high, and OFF the axis so the look direction is not straight down -
    # a target directly under the eye leaves the up vector undefined and the frame unstable.
    "crowns":         ((-140, 60), (100, 330), 300, 30, "overhead: only the three high crowns"),
}


#: render3d draws a ground plane so a cast shadow has somewhere to land, which is the right cue
#: for a sculpture standing on a floor and wrong for a park: this park brings its OWN deck, and
#: the plane lands below it as a grey checker under everything. Only the close creature views -
#: where "does it meet the ground" is the actual question - keep it.
GROUND = {"heron_close", "sloth", "wyrm"}



def assembled() -> scan.Scan:
    """Fold every placed module into one artifact. Buildings first is deliberate - a path is laid
    under a building on purpose, so for a picture to show the building rather than the street
    painted through it, the street has to lose the tie, and `scan.merge` gives the tie to
    whatever was folded in FIRST."""
    parts = sorted(PLACED.glob("*.litematic"))
    if not parts:
        raise SystemExit("nothing placed - run tools/parkbuild.py then tools/parkassemble.py")
    paving = [p for p in parts if any(k in p.stem for k in ("Claim Line", "Forge Deck",
                                                            "Welcome Court", "Mining Square"))]
    base = scan.load(str(parts[0]))
    for path in [p for p in parts[1:] if p not in paving] + paving:
        other = scan.load(str(path))
        merged, _ = scan.merge(base, other.model, other.origin)
        ox, oy, oz = base.origin; mx, my, mz = other.origin
        new = (min(ox, mx), min(oy, my), min(oz, mz))
        base = scan.Scan(merged, {**base.meta, "origin": {"x": new[0], "y": new[1], "z": new[2]}},
                         base.litematic_path, base.sidecar_path)
    return base


def occupied(model, point) -> bool:
    """Is the camera standing inside a block? A camera in a wall renders a black frame that
    looks exactly like a broken renderer, so it is reported rather than shipped."""
    x, y, z = (int(round(v)) for v in point)
    sy, sz, sx = model.ids.shape
    if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
        return False
    return bool(model.solid()[y, z, x])


def camera(s: scan.Scan, plane: int, eye_vu, target_vu, eye_h, target_h) -> r3.Camera:
    """A camera at a plan V/U point. The model array is local to the merged origin, so the plan
    lattice is converted once here rather than at every call site."""
    ox, oy, oz = s.origin
    eye = (eye_vu[0] - ox, plane + eye_h - oy, eye_vu[1] - oz)
    target = (target_vu[0] - ox, plane + target_h - oy, target_vu[1] - oz)
    return r3.Camera(tuple(map(float, eye)), tuple(map(float, target)), fov=52.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--view", action="append", help="render only these views")
    ap.add_argument("--big", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    plan = worldspec.compile(json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8")))
    plane = int(plan["site"]["build_plane"])
    s = assembled()
    model = s.model
    sy, sz, sx = model.ids.shape
    print(f"assembled {sx}x{sy}x{sz}, {int(model.solid().sum()):,} blocks, origin {s.origin}")

    width, height = (1280, 800) if args.big else (900, 560)
    wanted = set(args.view or VIEWS)
    written = []
    for name, (eye, target, eh, th, note) in VIEWS.items():
        if name not in wanted:
            continue
        cam = camera(s, plane, eye, target, eh, th)
        if occupied(model, cam.pos):
            print(f"  {name:<16}SKIPPED - the camera stands inside a block at plan V{eye[0]} "
                  f"U{eye[1]} +{eh}. Move the eye onto a route.")
            continue
        opts = dict(NIGHT) if name.endswith("_night") else {}
        opts["ground"] = name in GROUND
        image = r3.render(model, cam, width, height, **opts)
        path = OUT / f"{name}.png"
        Image.fromarray(image).save(path)
        written.append(str(path))
        print(f"  {name:<16}{note}")
    print(f"\nwrote {len(written)} views to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
