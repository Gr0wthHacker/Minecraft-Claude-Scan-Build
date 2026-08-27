"""Read other people's builds and report what they do that we do not.

    python tools/corpus.py ~/Downloads                  every .litematic in a folder
    python tools/corpus.py ~/Downloads --vs out         and compare against our own designs
    python tools/corpus.py "a.litematic" "b.litematic"  named files
    python tools/corpus.py ~/Downloads --render out/corpus   write an ortho sheet per build

WHY THIS EXISTS. A downloaded schematic is the only evidence in this project that was not produced
by this project. Every other measurement here is circular in the way CLAUDE.md already admits -
`views.py` renders with the same colour DB the palette picker optimises against, the rubric scores
against tables this repo invented, and nothing built in this system has been placed in Minecraft and
looked at by a stranger. A corpus of builds by people who do this well is the one outside check
available offline, and reading 31 of them by hand produced four findings that no score had caught.
Doing that again by hand for the next thirty would be the same afternoon twice.

WHAT IT MEASURES, AND WHY EACH ONE EARNED ITS PLACE

  shell %   solid cells with at least one air face-neighbour. It separates the two disciplines
            cleanly and with no judgement involved: ARCHITECTURE runs 78-100% shell, SCULPTURE runs
            20-45%. A build that scores 50% is a sculpture with rooms in it, which is a third thing
            (Moon Castle) and the hardest kind to do.

  detail %  cells belonging to a non-cube family - slab, stair, trapdoor, fence, wall, pane, carpet.
            The single sharpest divide found: their architecture is 25-60% detail, ours is 0-25%,
            and the two of ours that score 100% are staircases made entirely of slabs, which is the
            metric being honest rather than flattering.

  ladder    the palette as a tonal ramp: the dominant block's share, and the luminance spread of
            what is left. Their sculptures are one body block at 50-90% plus three to six accents
            spanning ~150 of luminance. See `tools/ladder.py` for finding one we can afford.

  states    which block-STATE properties they actually decide. This is the part a block count
            cannot show and where most of the transferable vocabulary lives - `half=top` stairs,
            `type=top` slabs, and open trapdoors used as vertical panels.

THE STATE HISTOGRAM SEPARATES DECIDED FROM DERIVED, AND MUST. A stair's `shape`, a wall's `up` and
its connections, and a pane's connections are computed by the game from the neighbourhood - CLAUDE.md
settled this for `work.INTENTIONAL` and it is the same fact here. Counting them as technique reads
190 corner stairs as a thing the builder chose and sends someone off to implement corner-shape
resolution that the game does for free. They are reported under DERIVED, separately, and the header
says so, because the interesting half of the histogram is the half you can act on.

WHAT IT DOES NOT DO. It does not score, rank or grade. There is no rubric here and there should not
be: the corpus is evidence about what is possible, and turning it into a number would produce
exactly the failure the panel review exists to catch - a build that measures well and cannot be
named. Look at the renders.
"""
from __future__ import annotations

import argparse
import collections
import colorsys
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcbuild import blocks, nbt, schem            # noqa: E402

# Families whose members are not full cubes. `detail %` is the share of a build made of these, which
# is the closest single number to "does this look built rather than modelled".
DETAIL = ("trapdoor", "fence", "wall", "button", "lever", "stairs", "slab", "pane", "bars",
          "chain", "end_rod", "carpet", "candle", "lantern", "sign", "torch", "pressure_plate",
          "ladder", "rod", "amethyst", "pointed_dripstone", "vine", "flower_pot", "scaffolding")

# Properties the GAME computes from the neighbourhood. Recording them as technique invents work.
# Same list as the reasoning behind `work.INTENTIONAL`, stated from the other side.
DERIVED = {"shape", "up", "north", "south", "east", "west", "distance", "waterlogged", "power",
           "powered", "in_wall", "snowy", "attached", "signal_fire", "occupied", "locked",
           "unstable", "disarmed", "side_chain", "bottom", "level", "age", "moisture"}

# Properties that are only ever a placement DECISION, listed so the report can lead with them.
DECIDED = ("half", "type", "open", "facing", "axis", "face", "hanging", "rotation", "persistent",
           "part", "hinge", "candles", "lit", "instrument", "note", "delay", "flower_amount")


def lum(rgb) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


class Build:
    """One schematic, measured. Everything is derived once; nothing is cached across files."""

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.name = path.stem
        self.m = schem.load(str(path))
        self.solid = self.m.solid()
        self.short = [n.split(":")[-1] for n in self.m.names]
        self.counts = collections.Counter()
        for i, c in zip(*np.unique(self.m.ids, return_counts=True)):
            n = self.short[int(i)]
            if n not in ("air", "cave_air", "void_air"):
                self.counts[n] += int(c)
        self.total = sum(self.counts.values())

    # ---- geometry ---------------------------------------------------------
    @property
    def dims(self) -> tuple[int, int, int]:
        if not self.solid.any():
            return (0, 0, 0)
        ys, zs, xs = np.where(self.solid)
        return (int(xs.max() - xs.min()) + 1,
                int(ys.max() - ys.min()) + 1,
                int(zs.max() - zs.min()) + 1)

    def shell_pct(self) -> float:
        """Share of solid cells with at least one air FACE neighbour.

        Padded with air, so the bounding box counts as open - a build sliced by its own box would
        otherwise read as more solid than it is, and every one of these is cropped to content.
        """
        s = self.solid
        if not s.any():
            return 0.0
        p = np.pad(s, 1, constant_values=False)
        enclosed = (p[2:, 1:-1, 1:-1] & p[:-2, 1:-1, 1:-1] & p[1:-1, 2:, 1:-1] &
                    p[1:-1, :-2, 1:-1] & p[1:-1, 1:-1, 2:] & p[1:-1, 1:-1, :-2])
        interior = int((s & enclosed).sum())
        return 100.0 * (int(s.sum()) - interior) / int(s.sum())

    def detail_pct(self) -> float:
        d = sum(c for n, c in self.counts.items() if any(k in n for k in DETAIL))
        return 100.0 * d / self.total if self.total else 0.0

    # ---- palette ----------------------------------------------------------
    def ladder(self, top: int = 8) -> list[tuple[str, int, float | None]]:
        out = []
        for n, c in self.counts.most_common(top):
            rgb = blocks.color(n, "side")
            out.append((n, c, lum(rgb) if rgb else None))
        return out

    def tone_spread(self) -> tuple[float, float, float]:
        """(dominant share %, count-weighted luminance sd, luminance range) over the whole build.

        The sd is weighted by cell count on purpose: a palette with forty blocks in it is not tonal
        variety if 90% of the cells are one of them.
        """
        vals, wts = [], []
        for n, c in self.counts.items():
            rgb = blocks.color(n, "side")
            if rgb:
                vals.append(lum(rgb))
                wts.append(c)
        if not vals:
            return (0.0, 0.0, 0.0)
        v, w = np.array(vals), np.array(wts, float)
        mean = float((v * w).sum() / w.sum())
        sd = float(np.sqrt(((v - mean) ** 2 * w).sum() / w.sum()))
        dom = 100.0 * self.counts.most_common(1)[0][1] / self.total
        return (dom, sd, float(v.max() - v.min()))

    # ---- states -----------------------------------------------------------
    def states(self) -> tuple[collections.Counter, collections.Counter]:
        """(decided, derived) as Counters of 'prop=value' weighted by cells."""
        per_id = collections.Counter()
        for i, c in zip(*np.unique(self.m.ids, return_counts=True)):
            per_id[int(i)] += int(c)
        dec, der = collections.Counter(), collections.Counter()
        for i, entry in enumerate(self.m.palette):
            n = nbt.state_name(entry).split(":")[-1]
            c = per_id.get(i, 0)
            if not c or n in ("air", "cave_air", "void_air"):
                continue
            for k, v in nbt.state_props(entry).items():
                (der if k in DERIVED else dec)[f"{k}={v}"] += c
        return dec, der

    def furniture(self) -> tuple[collections.Counter, collections.Counter]:
        te, ent = collections.Counter(), collections.Counter()
        for t in self.m.tile_entities:
            v = t.value.get("id")
            te[v.value.split(":")[-1] if v else "?"] += 1
        for t in self.m.entities:
            v = t.value.get("id")
            ent[v.value.split(":")[-1] if v else "?"] += 1
        return te, ent


def gather(paths: list[str]) -> list[Build]:
    files: list[pathlib.Path] = []
    for p in paths:
        q = pathlib.Path(p).expanduser()
        files.extend(sorted(q.glob("*.litematic")) if q.is_dir() else [q])
    out = []
    for f in files:
        try:
            out.append(Build(f))
        except Exception as e:                      # a corpus is other people's files
            print(f"  ! {f.name}: {type(e).__name__}: {e}", file=sys.stderr)
    return out


def table(builds: list[Build], title: str) -> None:
    print(f"\n### {title}  ({len(builds)} builds)")
    print(f"{'build':44s} {'dims':>14s} {'blocks':>8s} {'pal':>4s} {'shell%':>7s} "
          f"{'detail%':>8s} {'dom%':>6s} {'lum sd':>7s}")
    for b in sorted(builds, key=lambda b: -b.total):
        dx, dy, dz = b.dims
        dom, sd, _ = b.tone_spread()
        print(f"{b.name[:44]:44s} {f'{dx}x{dy}x{dz}':>14s} {b.total:8d} {len(b.counts):4d} "
              f"{b.shell_pct():7.1f} {b.detail_pct():8.1f} {dom:6.0f} {sd:7.0f}")


def rollup(builds: list[Build], top: int) -> None:
    dec, der = collections.Counter(), collections.Counter()
    fam, te, ent = collections.Counter(), collections.Counter(), collections.Counter()
    for b in builds:
        d1, d2 = b.states()
        dec.update(d1)
        der.update(d2)
        t, e = b.furniture()
        te.update(t)
        ent.update(e)
        for n, c in b.counts.items():
            for k in DETAIL:
                if k in n:
                    fam[k] += c
                    break

    print("\n### DETAIL FAMILIES (cells across the corpus)")
    for k, c in fam.most_common(top):
        print(f"  {c:8d}  {k}")

    print("\n### PLACEMENT DECISIONS - properties a builder chooses; this is the transferable half")
    for k, c in sorted(dec.most_common(top * 2), key=lambda kv: (kv[0].split("=")[0], -kv[1])):
        print(f"  {c:8d}  {k}")

    print("\n### DERIVED - the GAME computes these from neighbours. Do not implement them.")
    for k, c in der.most_common(8):
        print(f"  {c:8d}  {k}")

    if te:
        print("\n### TILE ENTITIES (furniture)")
        for k, c in te.most_common(top):
            print(f"  {c:8d}  {k}")
    if ent:
        print("\n### ENTITIES (paintings, frames, stands - decoration we have never used)")
        for k, c in ent.most_common(top):
            print(f"  {c:8d}  {k}")


def compare(theirs: list[Build], ours: list[Build]) -> None:
    """The two numbers that actually differed, and nothing else - a gap list, not a scoreboard."""
    def band(bs, lo, hi):
        return [b for b in bs if lo <= b.shell_pct() < hi]

    print("\n### THE GAP, by discipline")
    print(f"{'':22s} {'n':>4s} {'detail% median':>15s} {'palette median':>15s} {'dom% median':>12s}")
    for label, lo, hi in (("sculpture (shell<55)", 0.0, 55.0), ("architecture (shell>=55)", 55.0, 101.0)):
        for who, bs in (("theirs", theirs), ("ours", ours)):
            sel = band(bs, lo, hi)
            if not sel:
                continue
            det = float(np.median([b.detail_pct() for b in sel]))
            pal = float(np.median([len(b.counts) for b in sel]))
            dom = float(np.median([b.tone_spread()[0] for b in sel]))
            print(f"{label:22s} {who:>6s} {len(sel):4d} {det:15.1f} {pal:15.0f} {dom:12.0f}")

    mine = {n for b in ours for n in b.counts}
    gap = collections.Counter()
    for b in theirs:
        for n, c in b.counts.items():
            if n not in mine:
                gap[n] += c
    print(f"\n### BLOCKS THEY USE THAT NO DESIGN OF OURS CONTAINS ({len(gap)} blocks)")
    for n, c in gap.most_common(20):
        try:
            ok = blocks.available(n) and blocks.spendable(n)
        except Exception:
            ok = False
        print(f"  {c:8d}  {n:32s} {'' if ok else '(currency or not on this server)'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="folders or .litematic files")
    ap.add_argument("--vs", help="folder of OUR designs to compare against, e.g. out")
    ap.add_argument("--top", type=int, default=16)
    ap.add_argument("--ladders", action="store_true", help="print each build's tonal ladder")
    ap.add_argument("--render", help="directory to write an orthographic sheet per build")
    ap.add_argument("--min-blocks", type=int, default=200,
                    help="skip anything smaller; --vs folders are full of test scraps")
    a = ap.parse_args()

    theirs = [b for b in gather(a.paths) if b.total >= a.min_blocks]
    if not theirs:
        ap.error("nothing loaded")
    table(theirs, "CORPUS")
    rollup(theirs, a.top)

    if a.ladders:
        print("\n### TONAL LADDERS")
        for b in sorted(theirs, key=lambda b: -b.total):
            dom, sd, rng = b.tone_spread()
            print(f"\n  {b.name}  dominant {dom:.0f}%, weighted sd {sd:.0f}, range {rng:.0f}")
            for n, c, lv in b.ladder():
                pct = 100.0 * c / b.total
                print(f"     {c:8d} {pct:5.1f}%  lum {lv if lv is None else round(lv, 1)!s:>6s}  {n}")

    if a.vs:
        ours = [b for b in gather([a.vs]) if b.total >= a.min_blocks]
        # A capture is the whole world, not a design; it would dominate every median.
        ours = [b for b in ours if not b.name.startswith(("island_", "islet_", "lowland_planned"))]
        table(ours, "OURS")
        compare(theirs, ours)

    if a.render:
        out = pathlib.Path(a.render)
        out.mkdir(parents=True, exist_ok=True)
        for b in theirs:
            try:
                sheet(b, out / f"{b.name}.png")
            except Exception as e:
                print(f"  ! render {b.name}: {e}", file=sys.stderr)
        print(f"\nwrote {len(theirs)} sheets to {out}")


def sheet(b: Build, dest: pathlib.Path, zoom: int = 3) -> None:
    """Side / face / plan, nearest-surface with depth shading. The same three `views.py` gives a
    design of ours - but that one needs a scan sidecar, and a download has none."""
    from PIL import Image
    s, ids = b.solid, b.m.ids
    ys, zs, xs = np.where(s)
    ids = ids[ys.min():ys.max() + 1, zs.min():zs.max() + 1, xs.min():xs.max() + 1]
    s = s[ys.min():ys.max() + 1, zs.min():zs.max() + 1, xs.min():xs.max() + 1]
    sy, sz, sx = s.shape
    cache: dict[tuple[str, str], np.ndarray] = {}

    def col(n, face):
        if (n, face) not in cache:
            c = blocks.color(n, face) or (190, 80, 190)   # magenta = no colour recorded
            cache[(n, face)] = np.array(c, float)
        return cache[(n, face)]

    panels = []
    for view in ("side", "face", "top"):
        if view == "side":
            shape, axis, face, rev = (sy, sz), 2, "side", False
        elif view == "face":
            shape, axis, face, rev = (sy, sx), 1, "side", True
        else:
            shape, axis, face, rev = (sz, sx), 0, "top", True
        img = np.zeros((*shape, 3))
        dep = np.zeros(shape)
        hit = np.zeros(shape, bool)
        n_slices = s.shape[axis]
        order = range(n_slices - 1, -1, -1) if rev else range(n_slices)
        for step, k in enumerate(order):
            sl = s[:, :, k] if axis == 2 else (s[:, k, :] if axis == 1 else s[k])
            il = ids[:, :, k] if axis == 2 else (ids[:, k, :] if axis == 1 else ids[k])
            fresh = sl & ~hit
            if not fresh.any():
                continue
            for i in np.unique(il[fresh]):
                sel = fresh & (il == i)
                img[sel] = col(b.short[int(i)], face)
            dep[fresh] = step
            hit |= fresh
        rng = dep[hit].max() if hit.any() and dep[hit].max() > 0 else 1
        img = np.clip(img * (1.0 - 0.45 * (dep / rng))[..., None], 0, 255)
        img[~hit] = (22, 22, 26)
        panels.append((img[::-1] if view != "top" else img).astype(np.uint8))

    h = max(p.shape[0] for p in panels)
    w = sum(p.shape[1] for p in panels) + 8 * (len(panels) - 1)
    canvas = np.full((h, w, 3), 16, np.uint8)
    x0 = 0
    for p in panels:
        canvas[:p.shape[0], x0:x0 + p.shape[1]] = p
        x0 += p.shape[1] + 8
    Image.fromarray(canvas).resize((w * zoom, h * zoom), Image.NEAREST).save(dest)


if __name__ == "__main__":
    main()
