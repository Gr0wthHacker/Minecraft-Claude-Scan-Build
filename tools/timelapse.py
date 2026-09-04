"""The island being built, from the captures you already took.

    python tools/timelapse.py                          # every `island` scan, one GIF
    python tools/timelapse.py --name island --bearing 215 --pitch 25 --width 900
    python tools/timelapse.py --box -24249 24 29951 -24151 270 30049   # pin the frame by hand
    python tools/timelapse.py --frames-only            # PNGs, for a video editor

Nothing here is new capability: `render3d` has been able to draw a capture since it was written and
the scans archive holds nineteen `island` captures going back to the first one. What was missing was
the observation that a folder of dated captures of the same box IS a timelapse.

**THE ONE THING THAT MAKES IT WORK IS A FIXED FRAME.** `render3d.orbit` sizes the camera to each
model's own content, which is exactly right for one animal and exactly wrong here: the island grows,
so every frame would be re-framed to its own bounding box and the whole thing would swim - zooming
out as the build gets bigger, and lurching sideways every time something is added at one edge. So
the camera is computed ONCE, from the union of every frame's content, in WORLD coordinates, and
every frame is padded into that same world box before it is drawn.

**And a capture is not the same shape as its neighbours.** Captures cover whatever chunks were
loaded, so their origins and sizes differ; two frames drawn from raw model coordinates would not
even be looking at the same place. Everything is aligned by the sidecar's world origin, which is
the contract this whole project rests on.

Frames are ordered by the capture's own timestamp, not by filename order and not by mtime - mtime
moves when a folder is copied, which this file has already been bitten by once in the archive cap.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcbuild import render3d, scan as scan_mod, schem            # noqa: E402
from mcbuild.profile import load as load_profile                 # noqa: E402

STAMP = re.compile(r"_(\d{8})-(\d{4})$")


def _when(path: pathlib.Path, meta: dict) -> _dt.datetime:
    """The capture's own time. The sidecar's `created` first, the filename stamp second.

    Never the file's mtime: copying a folder rewrites every one of them, and the archive is copied
    by the backup this project now runs nightly.
    """
    c = meta.get("created")
    if c:
        try:
            return _dt.datetime.fromisoformat(str(c).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    m = STAMP.search(path.stem)
    if m:
        return _dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M")
    return _dt.datetime.fromtimestamp(path.stat().st_mtime)


def find(name: str, schem_dir: str) -> list[tuple[pathlib.Path, _dt.datetime]]:
    """Every archived capture under that scan name, oldest first."""
    d = pathlib.Path(schem_dir)
    out = []
    for cand in list((d / "scans").glob(f"{name}_*.litematic")) + list(d.glob(f"{name}.litematic")):
        side = cand.with_suffix("").with_suffix(".scan.json")
        if not side.exists():
            side = cand.parent / (cand.stem + ".scan.json")
        if not side.exists():
            continue
        try:
            meta = scan_mod.load(str(cand)).meta
        except Exception:                                        # noqa: BLE001
            continue
        out.append((cand, _when(cand, meta)))
    out.sort(key=lambda t: t[1])
    return out


def _world_box(scans) -> tuple[np.ndarray, np.ndarray]:
    """The union of every frame's SOLID content, in world coordinates.

    The union of the capture BOXES would be wrong in the other direction: a capture's box is the
    chunks that happened to be loaded, which on a flight across the island is far bigger than
    anything that was ever built in it, and the whole timelapse would be a speck in the middle.
    """
    lo = np.array([np.inf] * 3)
    hi = np.array([-np.inf] * 3)
    for s in scans:
        m = s.model
        solid = m.solid()
        if not solid.any():
            continue
        ys, zs, xs = np.where(solid)
        o = s.origin
        lo = np.minimum(lo, [xs.min() + o[0], ys.min() + o[1], zs.min() + o[2]])
        hi = np.maximum(hi, [xs.max() + 1 + o[0], ys.max() + 1 + o[1], zs.max() + 1 + o[2]])
    return lo, hi


def _place(s, lo: np.ndarray, hi: np.ndarray) -> schem.Model:
    """Re-cut one capture into the shared world box, so every frame is the same grid."""
    size = (hi - lo).astype(int)
    out = s.model.copy()
    ids = np.zeros((size[1], size[2], size[0]), out.ids.dtype)
    o = s.origin
    sy, sz, sx = s.model.ids.shape
    # source window, clipped into the shared box
    x0, y0, z0 = int(lo[0] - o[0]), int(lo[1] - o[1]), int(lo[2] - o[2])
    sx0, sy0, sz0 = max(0, x0), max(0, y0), max(0, z0)
    sx1, sy1, sz1 = min(sx, x0 + size[0]), min(sy, y0 + size[1]), min(sz, z0 + size[2])
    if sx1 > sx0 and sy1 > sy0 and sz1 > sz0:
        dx, dy, dz = sx0 - x0, sy0 - y0, sz0 - z0
        ids[dy:dy + (sy1 - sy0), dz:dz + (sz1 - sz0), dx:dx + (sx1 - sx0)] = \
            s.model.ids[sy0:sy1, sz0:sz1, sx0:sx1]
    out.ids = ids
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="island", help="scan name in the archive (default: island)")
    ap.add_argument("--out", default="out/timelapse", help="output directory")
    ap.add_argument("--bearing", type=float, default=215.0)
    ap.add_argument("--pitch", type=float, default=22.0)
    ap.add_argument("--dist", type=float, default=1.05)
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--height", type=int, default=560)
    ap.add_argument("--ms", type=int, default=700, help="milliseconds per frame in the GIF")
    ap.add_argument("--hold", type=int, default=5, help="repeat the LAST frame this many times")
    ap.add_argument("--frames-only", action="store_true")
    ap.add_argument("--no-shadows", action="store_true")
    ap.add_argument("--box", nargs=6, type=int, metavar=("X0", "Y0", "Z0", "X1", "Y1", "Z1"))
    ap.add_argument("--min-coverage", type=float, default=0.70,
                    help="skip a frame holding less than this fraction of the running maximum "
                         "(0 keeps everything). See the note in the source.")
    a = ap.parse_args(argv)

    prof = load_profile()
    found = find(a.name, prof["schem_dir"])
    if len(found) < 2:
        print(f"need at least two `{a.name}` captures; found {len(found)}. "
              f"The archive is {os.path.join(prof['schem_dir'], 'scans')}", file=sys.stderr)
        return 2

    print(f"{len(found)} capture(s), {found[0][1]:%Y-%m-%d} to {found[-1][1]:%Y-%m-%d}")
    scans = []
    for path, when in found:
        try:
            scans.append((scan_mod.load(str(path)), when))
        except Exception as e:                                   # noqa: BLE001
            print(f"  skipped {path.name}: {e}", file=sys.stderr)
    if len(scans) < 2:
        return 2

    # A CAPTURE THAT LOST A THIRD OF THE ISLAND IN AN HOUR SAW LESS OF IT, IT DID NOT LOSE IT.
    # Every one of these 20 covers the same 56 chunks, so chunk count says nothing - what differs
    # is DEPTH: a scan taken from the deck never receives the lowland's sections, and the archive
    # holds captures ranging 49,762 to 137,857 blocks over the same ground. Played straight, the
    # underworld blinks in and out and the whole thing reads as a glitch.
    #
    # Reported and overridable rather than silent, because a big drop CAN be real: Jack removed
    # 32,369 vines by hand between two of these scans, and a filter that quietly hid that would be
    # editing the history it exists to show.
    kept, dropped, peak = [], [], 0
    for s_, when in scans:
        n = int(s_.model.solid().sum())
        if peak and n < peak * a.min_coverage:
            dropped.append((when, n, peak))
            continue
        peak = max(peak, n)
        kept.append((s_, when, n))
    # ...and the same capture can be in the archive twice (the live file plus its archived copy).
    deduped = []
    for s_, when, n in kept:
        if deduped and deduped[-1][2] == n and (when - deduped[-1][1]).total_seconds() < 60:
            continue
        deduped.append((s_, when, n))
    if dropped:
        print(f"skipped {len(dropped)} partial capture(s) (under {a.min_coverage:.0%} of the "
              f"running peak - a scan from the deck does not receive the lowland):")
        for when, n, pk in dropped:
            print(f"  {when:%Y-%m-%d %H:%M}  {n:,} vs peak {pk:,}")
        print("  --min-coverage 0 keeps them; a real demolition would be filtered too")
    if len(deduped) < len(kept):
        print(f"dropped {len(kept) - len(deduped)} duplicate frame(s)")
    scans = [(s_, when) for s_, when, _ in deduped]
    if len(scans) < 2:
        print("nothing left to animate", file=sys.stderr)
        return 2

    if a.box:
        lo = np.array(a.box[:3], float)
        hi = np.array(a.box[3:], float)
    else:
        lo, hi = _world_box([s for s, _ in scans])
    print(f"shared frame X {lo[0]:.0f}..{hi[0]:.0f}  Y {lo[1]:.0f}..{hi[1]:.0f}  "
          f"Z {lo[2]:.0f}..{hi[2]:.0f}")

    # ONE camera for the whole sequence, from the biggest frame - so nothing swims.
    biggest = max(scans, key=lambda t: int(t[0].model.solid().sum()))[0]
    cam = render3d.orbit(_place(biggest, lo, hi), yaw=a.bearing, pitch=a.pitch, dist=a.dist)

    outdir = pathlib.Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    from PIL import Image, ImageDraw

    frames = []
    for i, (s, when) in enumerate(scans):
        m = _place(s, lo, hi)
        n = int(m.solid().sum())
        img = render3d.render(m, cam, width=a.width, height=a.height,
                              shadows=not a.no_shadows)
        pic = Image.fromarray(img)
        d = ImageDraw.Draw(pic)
        label = f"{when:%Y-%m-%d %H:%M}    {n:,} blocks"
        d.rectangle([0, a.height - 22, a.width, a.height], fill=(20, 20, 24))
        d.text((10, a.height - 17), label, fill=(235, 235, 235))
        p = outdir / f"{a.name}_{i:03d}_{when:%Y%m%d-%H%M}.png"
        pic.save(p)
        frames.append(pic)
        print(f"  {i + 1:2d}/{len(scans)}  {when:%Y-%m-%d %H:%M}  {n:,} blocks -> {p.name}")

    if not a.frames_only:
        gif = outdir / f"{a.name}_timelapse.gif"
        # The last frame is held: an animation that snaps back to an empty island the instant it
        # finishes reads as a glitch rather than as an ending.
        frames[0].save(gif, save_all=True, append_images=frames[1:] + [frames[-1]] * a.hold,
                       duration=a.ms, loop=0, optimize=True)
        print(f"wrote {gif}  ({len(frames)} frames + {a.hold} held, {gif.stat().st_size / 1e6:.1f} MB)")
    grew = int(scans[-1][0].model.solid().sum()) - int(scans[0][0].model.solid().sum())
    span = (scans[-1][1] - scans[0][1]).days or 1
    print(f"{grew:+,} blocks over {span} day(s) = {grew / span:+,.0f}/day")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
