"""Assemble the evidence a THIRD PARTY needs to say whether a build reads, and ask them properly.

    python tools/panel.py "X jaguar"
    python tools/panel.py "Lowland Jaguar Lunge" --out out/panel_jaguar.png

WHY THIS EXISTS. `rubric.py` measures proportion against the design, surface roughness, palette
coherence, symmetry. An animal can score GOOD on every one of those and still be a spotted table -
that happened, and it took Jack looking at a render to catch it. Nothing in the pipeline asked the
only question that finally matters: WOULD A STRANGER NAME THIS ANIMAL?

That question cannot be measured, so it is asked - but asking it fairly needs the right evidence in
front of the reviewer, and the review needs to come from more than one direction. Two panels, because
they catch different things:

  THE VISUAL CRITIC cares about silhouette, mass and value. Does the outline alone name the animal?
  Is there a line of action, or is it a stack of boxes? Where is the weight? Does the light/dark
  structure describe a form or just a pattern?

  THE MINECRAFT PLAYER cares about how it is received in the world. Does it read at the distance you
  actually walk past it? Does it look BUILT - a deliberate palette, texture variation, detail blocks -
  or like a voxel dump? How big is it next to a player? Would it survive being seen from the three or
  four angles a path allows, rather than the one orthographic view that flatters it?

WHAT IT PUTS IN FRONT OF THEM, and why each panel is here:

  profile      the axis is chosen from the RECORDED FACING, because picking it by hand is a trap -
               it was got wrong twice in one session, and auditing an animal's backside tells you
               nothing about its face
  silhouette   flat black. This is the "would you know it with the colour removed" question from the
               rubric, shown instead of asked. Most failures are visible here first
  value        the same view in greyscale, so the tonal structure can be judged without the coat
               pattern arguing for it
  distance     the profile at 1/2, 1/4 and 1/8 scale - roughly 25, 50 and 100 blocks away. A build
               that only works nose-first is a build nobody will ever see working
  scale        a 2-block player bar beside it, because "is it big enough" is meaningless in the
               abstract and instant next to a person
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import scan                                    # noqa: E402

VISUAL = [
    "Name the animal from the SILHOUETTE alone. If you cannot, nothing else matters.",
    "Where is the weight? A quadruped carries it over the shoulder and the haunch - can you see them?",
    "Is there a line of action, or is the spine a straight rule?",
    "Does the value panel describe a rounded body, or is it a flat shape with a pattern on it?",
    "What is the single worst-reading part, and what would you change FIRST?",
]
PLAYER = [
    "At the 1/4 and 1/8 thumbnails - the distance you actually walk past - what is it?",
    "Does it look BUILT? Deliberate palette, texture variation, detail blocks - or a voxel dump?",
    "Next to the player bar, is it impressive, or is it small and fussy?",
    "Which three angles will people actually see it from, and does it hold up at all three?",
    "What would a comment on this build say if you posted it? Be unkind.",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design")
    ap.add_argument("--zoom", type=int, default=8)
    ap.add_argument("--out")
    a = ap.parse_args()

    s = scan.load(a.design)
    meta = getattr(s, "meta", None) or {}
    facing = meta.get("facing") or [0, 1]
    # THE PROFILE AXIS COMES FROM THE FACING, never from a guess. An animal facing +z shows its
    # profile to a viewer looking along x (`side`); one facing +x shows it along z (`face`).
    profile = "side" if facing[1] else "face"
    name = os.path.splitext(os.path.basename(a.design))[0]
    out = a.out or f"out/panel_{name.replace(' ', '_')}.png"
    tmp = out + ".a.png"
    tmp2 = out + ".b.png"

    def render(views, zoom, dest, extra=()):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "views.py"),
                        a.design, "--zoom", str(zoom), "--views", views, "--out", dest, *extra],
                       check=True, capture_output=True)
        return Image.open(dest).convert("RGB")

    prof = render(profile, a.zoom, tmp)
    other = render("top", max(2, a.zoom // 2), tmp2)

    sil = _flatten(prof, (28, 28, 32))
    val = prof.convert("L").convert("RGB")
    thumbs = [prof.resize((max(1, prof.width // k), max(1, prof.height // k)), Image.NEAREST)
              for k in (2, 4, 8)]

    pad, gap = 16, 18
    strip_w = max(t.width for t in thumbs)
    W = pad * 2 + prof.width + gap + sil.width + gap + val.width + gap + max(strip_w, other.width)
    H = pad * 2 + max(prof.height, other.height + gap + sum(t.height + 6 for t in thumbs)) + 30
    sheet = Image.new("RGB", (W, H), (250, 250, 250))
    x = pad
    for im in (prof, sil, val):
        sheet.paste(im, (x, pad + 30))
        x += im.width + gap
    sheet.paste(other, (x, pad + 30))
    y = pad + 30 + other.height + gap
    for t in thumbs:
        sheet.paste(t, (x, y))
        y += t.height + 6
    # the player bar: 2 blocks tall at the profile's own zoom, so scale is instant
    bar = Image.new("RGB", (max(4, a.zoom), a.zoom * 2), (40, 90, 160))
    sheet.paste(bar, (pad // 2, pad + 30 + prof.height - bar.height))
    sheet.save(out)
    for f in (tmp, tmp2):
        try:
            os.remove(f)
        except OSError:
            pass

    print(f"{out}   {sheet.size[0]}x{sheet.size[1]}")
    print(f"  panels: profile({profile}) | silhouette | value | top + distance thumbs (1/2, 1/4, 1/8)")
    print(f"  the blue bar at the left is a 2-block player, at the profile's scale\n")
    print("PANEL 1 - THE VISUAL CRITIC")
    for q in VISUAL:
        print(f"  - {q}")
    print("\nPANEL 2 - THE MINECRAFT PLAYER")
    for q in PLAYER:
        print(f"  - {q}")
    print("\nWrite both answers down before changing anything. A panel that is not recorded is a "
          "panel that gets quietly overruled by the next score that looks fine.")


def _flatten(im, ink):
    """Everything that is not background, as one flat colour: the silhouette test, shown."""
    px = im.load()
    out = Image.new("RGB", im.size, (250, 250, 250))
    o = out.load()
    for yy in range(im.height):
        for xx in range(im.width):
            r, g, b = px[xx, yy]
            if not (r > 235 and g > 235 and b > 235):
                o[xx, yy] = ink
    return out


if __name__ == "__main__":
    main()
