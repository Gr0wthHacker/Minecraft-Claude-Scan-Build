## The panel review — the last step before shipping

`python tools/panel.py "<design>"`. The rubric measures proportion, surface, palette, symmetry, and
an animal can score GOOD on every one of them and still be a spotted table. That happened. Nothing in
the pipeline asked the only question that finally matters: **would a stranger name this animal?**

It cannot be measured, so it is asked — but asking it fairly needs the right evidence, from more than
one direction. The sheet shows the profile (axis chosen from the RECORDED FACING, because picking it
by hand was got wrong twice in one session), a flat **silhouette**, a greyscale **value** panel, the
plan, **distance thumbnails** at 1/2, 1/4 and 1/8, and a 2-block **player bar** for scale. Then two
panels, because they catch different things — the visual critic on silhouette, mass, line and value;
the Minecraft player on distance legibility, whether it looks BUILT, scale against a person, and the
three or four angles a path actually allows.

**Write both verdicts down.** A panel that is not recorded is one the next good-looking score quietly
overrules.

### First verdicts (2026-08-19)

**X elephant — PASSES both.** The silhouette alone names it: trunk curve, ear, domed head, columnar
legs. The value panel shows real rounding. It still reads as an elephant at the 1/8 thumbnail. This
is the control the panel is calibrated against.

**X jaguar — FAILS both, badly.**

*Visual critic.* You cannot name it from the silhouette — it reads as a low table, or a bull; the
only cat cue is the tail. There is no weight anywhere: the outline is a constant-depth rectangle from
shoulder to rump, so the animal has no centre of gravity. No line of action — the spine is a straight
rule and the belly is a second straight rule parallel to it, which is the most inert shape available.
The value panel is flat, and the pale belly is a hard-edged band that *reinforces* the slab rather
than describing a form. Fix first: **the legs** — constant-width posts at the extreme corners are
exactly what makes it a table.

*Minecraft player.* At 1/4 and 1/8 it is a brown smudge with a line coming off it; the spots turn to
noise rather than pattern. It does not look built — one wood tone with black wool speckles, no block
variety doing any work, no stairs or slabs breaking the grid. Scale is fine, ~15 player-heights long.
Of the three angles a path gives you, only the side is even attempted, and the plan view reads better
than the profile, which is backwards for something standing on the ground. The comment it would get:
*"why does your jaguar have four table legs and a flat back?"*

### Second pass — what fixing all five did (2026-08-19)

All five were done. The jaguar is no longer a table and no longer a deer; the silhouette reads as a
cat. The specific changes, and what each was actually worth:

1. **The belly got its own line.** `_body` now takes a fifth keyframe column, `lift`, so the
   underside is set independently of the floor. High through the loin, near zero under the chest.
   This is the one that stopped the profile being two parallel horizontals.
2. **Legs got a thigh, a cannon and a foot.** The visible part ran near-constant at +0.15, -0.30,
   +0.05, +0.40 — a post. It now tapers 1.05 → -0.20 → 0.30.
3. **The barrel went bimodal** — mass over haunch and shoulder, waist between. Fixes the plan view
   outright.
4. **The back got a shoulder rise**, via the depth-taper column.
5. **The felid skull was wrong in two ways at once.** Its half-width tapered steadily to a point
   while its centre drooped, which is a SNOUT — the panel read it as a deer and was right. And
   `head length` was 0.329 of shoulder height where a cat's is about a quarter. Now blunt, wide
   through the cheeks, and 0.258.

**Size is still the ceiling.** At 27 blocks the barrel is ~10 deep, so a 0.15 tuck is one and a half
blocks and most of this is sub-block. It reads as a cat, marginally. At 2.6x it reads clearly, the
rosettes resolve into actual rings rather than speckle, and the tuck and the taper are all visible.
**If a cat matters, build it big** — that is what the emerging half-figure is for.

No animal regressed: bear .84, lion .86, capybara .83, leopard .82, elephant .81, giraffe .80,
jaguar .80, polar_bear .78.

**Still open:** the back is flat across the middle (a cat's rather is, so this may be fine); the
legs still read as posts at 27 blocks; and the bear's eyes still do not read against `mangrove_wood`.

### What the two panels agree on, in order

1. **Legs must merge into the body as a haunch and a shoulder**, and taper to a slim cannon. Posts at
   the corners are the single biggest failure.
2. **The belly line must not be parallel to the back.** It is `floor = rump + (chest - rump) * t` —
   a straight line by construction, so a deep chest and a tucked loin cannot be expressed at all.
3. **The back line needs a shoulder rise and a rump fall** to break the horizontal.
4. **The barrel is a spindle** — widest mid-body, tapering to both ends. A quadruped is widest at the
   shoulder and haunch with a waist between. A bimodal width profile was tested and fixes the PLAN
   view immediately; it does nothing for the profile, which is governed by (2).
5. **The surface must look built** — a 3-tone coat and real use of the slab shell, not one tone plus
   speckles.

**The pattern across all eight animals:** this system succeeds where identity is HARDWARE — the
elephant's trunk and ears, the giraffe's neck, the capybara genuinely being a blocky rodent — and
fails where identity is MUSCLE AND PROPORTION, which is every cat and both bears. Scaling does not
help: the jaguar at scale 1.7 with 8,349 blocks fails exactly as the 27-block one does.

