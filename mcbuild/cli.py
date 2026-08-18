"""mcbuild command-line interface.

    python -m mcbuild info      <file>
    python -m mcbuild audit     <file> [--symmetry]
    python -m mcbuild render    <file> [--views face,side,top] [--out x.png] [--ascii face]
    python -m mcbuild downscale <file> --factor 2 [--out] [--cheapen] [--hollow]
    python -m mcbuild hollow    <file> [--out]
    python -m mcbuild cheapen   <file> [--out] [--keep orange_concrete]
    python -m mcbuild gen       <config.yaml> [--set params.trunk_height=18] [--ship]
    python -m mcbuild fromimage <image.png> --height 27 [--depth 10] [--out]
"""
from __future__ import annotations

import argparse
import os
import sys

from . import audit as audit_mod, coop, learn as learn_mod, palette, render, scan as scan_mod, schem
from .ops import cheapen as cheapen_op, downscale as downscale_op, from_image, hollow as hollow_op
from .pipeline import Settings, run_config


def _out(path_in: str, out: str | None, suffix: str) -> str:
    if out:
        return out
    base, ext = os.path.splitext(path_in)
    return f"{base}{suffix}{ext or '.litematic'}"


def cmd_info(a):
    m = schem.load(a.file)
    r = audit_mod.audit(m, ground=not a.no_ground)
    print(r.report())


def cmd_audit(a):
    m = schem.load(a.file)
    r = audit_mod.audit(m, ground=not a.no_ground, symmetry=a.symmetry, symmetry_rows_from=a.symmetry_from,
                        ground_block=a.ground_block)
    print(r.report())
    sys.exit(0 if r.ok else 1)


def cmd_render(a):
    m = schem.load(a.file)
    miss = palette.missing_colors(m.names)
    if miss:
        print("warning: no colour for", miss, "(rendered magenta)")
    if a.ascii:
        print(render.ascii_map(m, a.ascii))
        return
    views = tuple(a.views.split(","))
    out = a.out or _out(a.file, None, "").replace(".litematic", f"_{'_'.join(views)}.png")
    render.contact_sheet(m, views=views, scale=a.scale).save(out)
    print("wrote", out)


def cmd_downscale(a):
    m = schem.load(a.file)
    acc = {}
    for s in a.accent or []:
        k, v = s.split("=")
        acc[k] = int(v)
    m = downscale_op(m, a.factor, threshold=a.threshold, accents=acc or None, mirror_x=a.mirror)
    if a.cheapen:
        cheapen_op(m, keep=set(a.keep or []))
    if a.hollow:
        print("hollow:", hollow_op(m, shell=a.shell, ground=not a.no_ground))
    m.compact_palette()
    out = _out(a.file, a.out, f"_x{a.factor:g}")
    n = schem.save(out, m, name=os.path.splitext(os.path.basename(out))[0])
    print(f"wrote {out}: {n} blocks, {len(m.palette)} states")
    print(audit_mod.audit(m, ground=not a.no_ground).report())


def cmd_hollow(a):
    m = schem.load(a.file)
    print("hollow:", hollow_op(m, shell=a.shell, ground=not a.no_ground, ceiling=a.ceiling,
                               keep_floor=not a.no_floor, keep_top_layers=a.keep_top))
    out = _out(a.file, a.out, "_hollow")
    schem.save(out, m)
    print("wrote", out)


def cmd_cheapen(a):
    m = schem.load(a.file)
    extra = {}
    for s in a.sub or []:
        k, v = s.split("=")
        extra[k] = v
    rep = cheapen_op(m, extra=extra or None, keep=set(a.keep or []))
    print("replaced:", ", ".join(f"{k.split(':')[-1]}:{v}" for k, v in rep.items()) or "nothing")
    out = _out(a.file, a.out, "_cheap")
    schem.save(out, m)
    print("wrote", out)
    print(audit_mod.audit(m).report())


def cmd_gen(a):
    over = {}
    for s in a.set or []:
        k, v = s.split("=", 1)
        over[k] = v
    st = Settings(out_dir=a.out_dir)
    m, r = run_config(a.config, settings=st, overrides=over, ship=a.ship, render_sheet=not a.no_render)
    sys.exit(0 if r.ok else 1)


def cmd_fromimage(a):
    m = from_image(a.image, height=a.height, depth=a.depth, profile=a.profile,
                   tiers=tuple(a.tiers.split(",")), mirror=a.mirror,
                   hollow_shell=a.hollow, bg_tolerance=a.bg_tolerance,
                   palette_size=a.palette_size)
    out = a.out or os.path.splitext(a.image)[0] + ".litematic"
    n = schem.save(out, m, name=os.path.splitext(os.path.basename(out))[0])
    print(f"wrote {out}: {n} blocks, {len(m.palette)} states, size {m.shape_xyz}")
    print(audit_mod.audit(m).report())
    if not a.no_render:
        png = os.path.splitext(out)[0] + ".png"
        render.contact_sheet(m).save(png)
        print("wrote", png)


def cmd_scan(a):
    """Inspect a /cscan capture, optionally cut a world-coordinate sub-box out of it."""
    s = scan_mod.load(a.name)
    print(scan_mod.summary(s))
    if a.info:
        print(audit_mod.audit(s.model, ground=False).report())
    if a.cut:
        m, meta = scan_mod.cut(s, *a.cut)
        out = a.out or _out(s.litematic_path, None, "_cut")
        side = scan_mod.save_pair(out, m, meta, name=a.name_out)
        o = meta["origin"]
        print(f"wrote {out} + {os.path.basename(side)}  origin {o['x']} {o['y']} {o['z']}  "
              f"size {meta['size']['x']}x{meta['size']['y']}x{meta['size']['z']}  blocks {meta['non_air_blocks']}")


def cmd_learn(a):
    """Mine real placement relations from captures into mcbuild/data/observed.json."""
    print(learn_mod.learn(a.captures))


def cmd_progress(a):
    for d in a.designs:
        print(coop.progress(d, a.world).report())


def cmd_remaining(a):
    out = a.out or _out(scan_mod.resolve(a.design)[0], None, "_remaining")
    side, p = coop.remaining(a.design, a.world, out)
    print(p.report()); print("wrote", out, "+", os.path.basename(side))


def cmd_diff(a):
    print(coop.diff_report(coop.diff(a.old, a.new)))


def cmd_merge(a):
    print("wrote", coop.merge_scans(a.captures, a.out))


def cmd_shop(a):
    print(coop.shop(a.designs, a.world))


def cmd_place(a):
    print(coop.place(a.designs, server=a.server, dim=a.dim, game_dir=a.game_dir, enabled=not a.disabled, dry=a.dry))


def cmd_sync(a):
    print(coop.sync(a.config))


def cmd_card(a):
    out = a.out or _out(scan_mod.resolve(a.design)[0], None, "_card").replace(".litematic", ".png")
    print("wrote", coop.card(a.design, out, a.world))


def cmd_floating(a):
    n, cells, samples = coop.floating_clusters(a.design, a.context)
    print(f"{n} free-floating cluster(s), {cells} cells; e.g. {samples}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mcbuild", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info"); p.add_argument("file"); p.add_argument("--no-ground", action="store_true"); p.set_defaults(fn=cmd_info)
    p = sub.add_parser("audit"); p.add_argument("file"); p.add_argument("--symmetry", action="store_true")
    p.add_argument("--symmetry-from", type=int, default=0); p.add_argument("--no-ground", action="store_true")
    p.add_argument("--ground-block", help="block the schematic is pasted onto, e.g. moss_block"); p.set_defaults(fn=cmd_audit)
    p = sub.add_parser("render"); p.add_argument("file"); p.add_argument("--views", default="face,side,front,top")
    p.add_argument("--scale", type=int, default=10); p.add_argument("--out"); p.add_argument("--ascii", choices=["face", "front", "side"]); p.set_defaults(fn=cmd_render)
    p = sub.add_parser("downscale"); p.add_argument("file"); p.add_argument("--factor", type=float, required=True)
    p.add_argument("--threshold", type=float, default=0.42); p.add_argument("--accent", action="append", help="name=min_count")
    p.add_argument("--mirror", action="store_true"); p.add_argument("--cheapen", action="store_true"); p.add_argument("--keep", action="append")
    p.add_argument("--hollow", action="store_true"); p.add_argument("--shell", type=int, default=2)
    p.add_argument("--no-ground", action="store_true"); p.add_argument("--out"); p.set_defaults(fn=cmd_downscale)
    p = sub.add_parser("hollow"); p.add_argument("file"); p.add_argument("--shell", type=int, default=2)
    p.add_argument("--no-ground", action="store_true"); p.add_argument("--ceiling", action="store_true")
    p.add_argument("--no-floor", action="store_true"); p.add_argument("--keep-top", type=int, default=0); p.add_argument("--out"); p.set_defaults(fn=cmd_hollow)
    p = sub.add_parser("cheapen"); p.add_argument("file"); p.add_argument("--sub", action="append", help="src=dst")
    p.add_argument("--keep", action="append"); p.add_argument("--out"); p.set_defaults(fn=cmd_cheapen)
    p = sub.add_parser("gen"); p.add_argument("config"); p.add_argument("--set", action="append", help="dotted.key=value")
    p.add_argument("--ship", action="store_true"); p.add_argument("--out-dir", default="out"); p.add_argument("--no-render", action="store_true"); p.set_defaults(fn=cmd_gen)
    p = sub.add_parser("scan", help="inspect/cut a chunkscan capture (name in schematics dir, or a path)")
    p.add_argument("name"); p.add_argument("--info", action="store_true", help="also run the audit/BOM")
    p.add_argument("--cut", nargs=6, type=int, metavar=("X1", "Y1", "Z1", "X2", "Y2", "Z2"), help="world-coord sub-box")
    p.add_argument("--out"); p.add_argument("--name-out"); p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("learn", help="learn placement rules from real captures (names or paths)")
    p.add_argument("captures", nargs="+"); p.set_defaults(fn=cmd_learn)
    p = sub.add_parser("progress", help="design(s) vs a world capture: % built, what is left, deviations")
    p.add_argument("designs", nargs="+"); p.add_argument("--world", default="island"); p.set_defaults(fn=cmd_progress)
    p = sub.add_parser("remaining", help="export only the unbuilt cells of a design (same origin)")
    p.add_argument("design"); p.add_argument("--world", default="island"); p.add_argument("--out"); p.set_defaults(fn=cmd_remaining)
    p = sub.add_parser("diff", help="what changed between two captures (old new)")
    p.add_argument("old"); p.add_argument("new"); p.set_defaults(fn=cmd_diff)
    p = sub.add_parser("merge", help="merge several captures into one (newest scan wins per loaded chunk)")
    p.add_argument("captures", nargs="+"); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_merge)
    p = sub.add_parser("shop", help="shopping list in stacks/shulkers, optionally minus what is built (--world)")
    p.add_argument("designs", nargs="+"); p.add_argument("--world"); p.set_defaults(fn=cmd_shop)
    p = sub.add_parser("place", help="write Litematica placements (schematic + origin) into the per-world config; game must be closed")
    p.add_argument("designs", nargs="+"); p.add_argument("--server"); p.add_argument("--dim")
    p.add_argument("--game-dir"); p.add_argument("--disabled", action="store_true"); p.add_argument("--dry", action="store_true"); p.set_defaults(fn=cmd_place)
    p = sub.add_parser("sync", help="after /cscan: cut latest scan, regenerate remaining designs, progress + shop, learn")
    p.add_argument("--config", default="sync.yaml"); p.set_defaults(fn=cmd_sync)
    p = sub.add_parser("card", help="one PNG per design for chat: renders + origin + BOM (+ progress with --world)")
    p.add_argument("design"); p.add_argument("--world"); p.add_argument("--out"); p.set_defaults(fn=cmd_card)
    p = sub.add_parser("floating", help="design clusters touching nothing in the given context captures (need scaffold)")
    p.add_argument("design"); p.add_argument("context", nargs="+"); p.set_defaults(fn=cmd_floating)
    p = sub.add_parser("fromimage"); p.add_argument("image"); p.add_argument("--height", type=int, required=True)
    p.add_argument("--depth", type=int, default=8); p.add_argument("--profile", choices=["loft", "slab"], default="loft")
    p.add_argument("--tiers", default="cheap"); p.add_argument("--mirror", action="store_true"); p.add_argument("--hollow", type=int)
    p.add_argument("--bg-tolerance", type=int, default=40); p.add_argument("--palette-size", type=int)
    p.add_argument("--out"); p.add_argument("--no-render", action="store_true"); p.set_defaults(fn=cmd_fromimage)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
