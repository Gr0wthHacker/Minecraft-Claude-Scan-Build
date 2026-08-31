"""Render the WHOLE theme park for review - the step this project has never done.

CLAUDE.md, on the park: "Nothing has been looked at in game yet... `tools/look.py` cannot draw
these yet - it wants a facing VECTOR and the park sidecar records a word." That gap is closed in
`tools/look.py` (`facing_yaw` now reads a compass word through `park._STEP`, the same source
every ride generator already imports it from). This tool is what that fix was for: it renders
every module, every zone as a whole, and a distance ladder for the rides that are supposed to
carry the place, using `mcbuild/render3d.py` - perspective, cast shadows, corner AO, real stair
and slab shapes - never a second renderer.

    python tools/parksheet.py                      # everything: every module + all three zones
    python tools/parksheet.py --zone frontier       # one zone only
    python tools/parksheet.py --only "Mine Coaster" # one module's orbit sheet
    python tools/parksheet.py --skip-orbit          # zone + distance sheets only (faster)

WHAT COUNTS AS "THE PARK". Discovered from `configs/*.yaml`, not hand-listed - a module is in scope
if its `gen:` is one of the generators built on `park.py`'s geometry (`park`, `casino`, `coaster`,
`bigwheel`, `civic`, `frontiertown`, `hollowmanor`, `monument`, `streetfurniture`), and its zone is
read from `params.under`, the same capture every one of those configs already names as what it was
verified against. A module the discovery cannot place in a zone is reported, not silently dropped -
the same rule this project applies to an unrecorded facing.

WHOLE-ZONE VIEWS ARE NOT `r3.orbit`'s AUTO-FRAMED CENTRE SHOT. `orbit` centres on content and picks
its own distance, which is right for one module and wrong for an island: it would hover the camera
over the middle of the plot looking down, which is not how anyone experiences the place. Each zone's
gate config states its own `at`, `facing` and `_Frame` geometry - the exact arithmetic
`gen/park.py` places every wall and sign with - so the camera is built by hand at the spot a
visitor actually stands (a few blocks in front of the gate, in the +facing direction, at roughly
eye height) looking the way the gate looks: `d < 0` outside the gate, `d > 0` into the park, per
`_Frame.at`'s own convention.

OUTPUT is written to `out/parksheets/`.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import yaml
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import render3d as r3, scan                          # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look                                                       # noqa: E402

CONFIG_DIR = "configs"
OUT_DIR = "out/parksheets"

# every generator built on park.py's `at`/`facing`/`_Frame` geometry
PARK_GENS = {"park", "casino", "coaster", "bigwheel", "civic",
             "frontiertown", "hollowmanor", "monument", "streetfurniture"}

# the base terrain capture each zone's configs are verified against (park.py's own `under`)
ZONE_BASE = {
    "out/islandleft.litematic": "frontier",
    "out/newisle.litematic": "midway",
    "out/islandright.litematic": "hollow",
}
ZONE_GATE_CONFIG = {
    "frontier": "frontier_gate.yaml",
    "midway": "park_gate.yaml",
    "hollow": "hollow_gate.yaml",
}
# one attraction per zone that is a RIDE, not a shop or a static building - for the distance ladder
ZONE_HEADLINE = {
    "frontier": "Mine Coaster",
    "midway": "The Big Wheel",
    "hollow": "The Plummet",
}


# --------------------------------------------------------------------------- discovery

def discover(config_dir: str = CONFIG_DIR) -> tuple[dict[str, list[str]], list[str]]:
    """{zone: [design name, ...]} for every config using a park-family generator, plus a list of
    names whose zone could not be placed (reported, not dropped - CLAUDE.md rule 12's own posture:
    "I cannot say" is a different answer from "fine")."""
    zones: dict[str, list[str]] = {"frontier": [], "midway": [], "hollow": []}
    unplaced: list[str] = []
    for fn in sorted(os.listdir(config_dir)):
        if not fn.endswith(".yaml"):
            continue
        with open(os.path.join(config_dir, fn), encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        if cfg.get("gen") not in PARK_GENS:
            continue
        name = cfg.get("name") or os.path.splitext(fn)[0]
        under = (cfg.get("params") or {}).get("under")
        zone = ZONE_BASE.get(under)
        if zone is None:
            unplaced.append(name)
            continue
        zones[zone].append(name)
    return zones, unplaced


# --------------------------------------------------------------------------- compositing

def _fold(base: scan.Scan, other: scan.Scan) -> scan.Scan:
    """Composite `other` onto `base` and keep the ORIGIN correct - `scan.merge` grows the box
    toward whichever corner is smaller and does not report the new one, so a caller that keeps
    reusing the old origin (as `tools/plan_merge.py` does) silently misaligns every merge after
    the first one that actually grows the box. This re-derives it with the same min() the merge
    itself used."""
    merged, _overlap = scan.merge(base, other.model, other.origin)
    ox, oy, oz = base.origin
    mx, my, mz = other.origin
    new_origin = (min(ox, mx), min(oy, my), min(oz, mz))
    meta = {**base.meta, "origin": {"x": new_origin[0], "y": new_origin[1], "z": new_origin[2]}}
    return scan.Scan(merged, meta, base.litematic_path, base.sidecar_path)


def zone_composite(zone: str, names: list[str]) -> scan.Scan:
    """The base terrain plus every module, PAVING LAST. A path is drawn under a building on
    purpose (CLAUDE.md: "the paving is laid even UNDER a building... only lamp posts are skipped
    inside a footprint") - so for a picture to show a building rather than the street painted
    through it, the street has to lose the tie, and `scan.merge` gives the tie to whatever was
    folded in FIRST. Buildings first, paths last."""
    base_name = next(k for k, v in ZONE_BASE.items() if v == zone)
    s = scan.load(os.path.splitext(os.path.basename(base_name))[0])
    paths = [n for n in names if "Paths" in n]
    rest = [n for n in names if n not in paths]
    for n in rest + paths:
        s = _fold(s, scan.load(n))
    return s


# --------------------------------------------------------------------------- camera

def gate_yaw(zone: str) -> float:
    """The bearing a visitor stands at: the gate's own recorded `facing`, converted through the
    same `park._STEP` map `tools/look.py.facing_yaw` uses - "a visitor stands in the +facing
    direction" (park.py's own docstring) is exactly an animal's camera standing off the nose."""
    with open(os.path.join(CONFIG_DIR, ZONE_GATE_CONFIG[zone]), encoding="utf-8") as fh:
        p = (yaml.safe_load(fh) or {}).get("params", {})
    yaw0, known = look.facing_yaw({"facing": p.get("facing")})
    assert known, f"{zone} gate config has no recorded facing"
    return yaw0


def gate_camera(zone: str, m, pitch: float = 10.0, dist: float = 1.15,
                 look_high: float = 0.12) -> r3.Camera:
    """A framed shot of the whole zone from the gate's SIDE, looking in.

    A camera hand-placed at the gate's exact recorded `at`, a fixed few blocks out, clips into
    whatever the base capture's leftover starter-pad terrain happens to be sitting nearby -
    CLAUDE.md already warns the starter pad is "in the way" and never fully cleared. `r3.orbit`'s
    own framing (radius from the CONTENT box, not a guessed stand-off) is what every other sheet
    in this project trusts for exactly that reason, so the zone view reuses it: `yaw` is the
    gate's own bearing (so the camera sits on the side of the zone the gate is on), `pitch` is
    low rather than a literal eye height (an eye-height camera this close to a starter-pad mound
    is the clipping problem all over again), and `look_high` keeps the aim near the ground rather
    than at the model's vertical centre, which the coaster and the towers would otherwise pull
    high overhead.
    """
    return r3.orbit(m, yaw=gate_yaw(zone), pitch=pitch, dist=dist, look_high=look_high)


# --------------------------------------------------------------------------- rendering

def render_orbit(name: str, out_dir: str, pitch: float = 10.0) -> str:
    s = scan.load(name)
    m, figure = look.with_scale_figure(s.model)
    if r3.has_shapes(m):
        m = r3.subdivide(m)
    yaw0, known = look.facing_yaw(getattr(s, "meta", None) or {})
    bearings = [0, 45, 90, 135, 180, 225, 270, 315]
    panels = [(look.shot(m, yaw0, b, pitch, 1.0, 360, 280),
               f"{b:>3}  {look.WORDS[b]}") for b in bearings]
    sub = f"eight bearings" + ("" if known else "  -- FACING NOT RECORDED, bearing 0 is world +z")
    sheet = look.grid(panels, 4, name, sub)
    out = os.path.join(out_dir, f"orbit_{name.replace(' ', '_')}.png")
    sheet.save(out)
    return out


def render_zone_view(zone: str, s: scan.Scan, out_dir: str) -> str:
    m = s.model
    if r3.has_shapes(m):
        m = r3.subdivide(m)
    cam = gate_camera(zone, m)
    img = Image.fromarray(r3.render(m, cam, 960, 600))
    out = os.path.join(out_dir, f"zone_{zone}_view.png")
    img.save(out)
    return out


def render_zone_plan(zone: str, s: scan.Scan, out_dir: str) -> str:
    m = s.model
    if r3.has_shapes(m):
        m = r3.subdivide(m)
    cam = r3.orbit(m, yaw=0, pitch=88, dist=1.05, look_high=0.15)
    img = Image.fromarray(r3.render(m, cam, 900, 900, shadows=False))
    out = os.path.join(out_dir, f"zone_{zone}_plan.png")
    img.save(out)
    return out


def render_distance_ladder(name: str, out_dir: str) -> str:
    """Full, 1/2 and 1/4 apparent size - `dist` scales linearly and area falls as its square
    (pinned by `tests/test_render3d.py::test_perspective_obeys_the_inverse_square_law`), so
    dist=1/2/4 is the ladder CLAUDE.md's panel rule asks for: does it still read walked-past
    rather than stood-in-front-of."""
    s = scan.load(name)
    m, _figure = look.with_scale_figure(s.model)
    if r3.has_shapes(m):
        m = r3.subdivide(m)
    yaw0, _known = look.facing_yaw(getattr(s, "meta", None) or {})
    panels = [(look.shot(m, yaw0, 35, 14, d, 420, 320), lbl)
              for d, lbl in ((1.0, "full"), (2.0, "1/2"), (4.0, "1/4"))]
    sheet = look.grid(panels, 3, name, "distance ladder")
    out = os.path.join(out_dir, f"distance_{name.replace(' ', '_')}.png")
    sheet.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zone", choices=("frontier", "midway", "hollow"), default=None)
    ap.add_argument("--only", help="render just one module's orbit sheet by name")
    ap.add_argument("--skip-orbit", action="store_true", help="zone + distance sheets only")
    ap.add_argument("--out-dir", default=OUT_DIR)
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    zones, unplaced = discover()
    if unplaced:
        print(f"UNPLACED (zone unknown, skipped): {unplaced}")

    if a.only:
        t0 = time.perf_counter()
        out = render_orbit(a.only, a.out_dir)
        print(f"{out}  ({time.perf_counter() - t0:.1f}s)")
        return

    zone_list = [a.zone] if a.zone else ["frontier", "midway", "hollow"]

    t0 = time.perf_counter()
    n = 0
    if not a.skip_orbit:
        for zone in zone_list:
            for name in zones[zone]:
                try:
                    out = render_orbit(name, a.out_dir)
                    n += 1
                    print(f"  {out}")
                except Exception as e:                       # a design that fails to load must
                    print(f"  SKIPPED {name}: {e}")           # not stop the rest of the run
    print(f"{n} orbit sheets  ({time.perf_counter() - t0:.1f}s)")

    for zone in zone_list:
        t0 = time.perf_counter()
        comp = zone_composite(zone, zones[zone])
        print(f"{zone}: {len(zones[zone])} modules, "
              f"{int(comp.model.solid().sum())} blocks composited  ({time.perf_counter() - t0:.1f}s)")
        print(" ", render_zone_view(zone, comp, a.out_dir))
        print(" ", render_zone_plan(zone, comp, a.out_dir))
        headline = ZONE_HEADLINE.get(zone)
        if headline:
            try:
                print(" ", render_distance_ladder(headline, a.out_dir))
            except FileNotFoundError as e:
                print(f"  SKIPPED headline {headline}: {e}")


if __name__ == "__main__":
    main()
