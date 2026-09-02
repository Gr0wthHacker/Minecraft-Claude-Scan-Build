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
import json
import os
import pathlib
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
    if getattr(a, "by_price", False):
        from . import prices as prices_mod
        from .ops.cheapen import cheapen_by_price
        if not prices_mod.known():
            print("no price book yet - in game: /cscan prices on, then walk the shop")
            return
        rep = cheapen_by_price(m, tolerance=a.tolerance, keep=set(a.keep or []))
        if not rep:
            print("nothing to swap: no PRICED block was both cheaper and close enough in colour")
        for (src, dst), n in rep.most_common():
            sc, dc = prices_mod.buy(src), prices_mod.buy(dst)
            print(f"  {src} -> {dst}: {n} cells, {sc:.1f} -> {dc:.1f} each, saves {(sc - dc) * n:.0f} coins")
        out = _out(a.file, a.out, "_priced")
        schem.save(out, m)
        print("wrote", out)
        return
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
    print(coop.shop(a.designs, a.world, have=coop.load_storage() if a.have else None))


def cmd_storage(a):
    print(coop.storage_report())


def cmd_place(a):
    print("note: /cscan place in game does the same thing and does not need the game closed. "
          "Litematica rewrites this config on exit, so anything written while it runs is lost.",
          file=sys.stderr)
    print(coop.place(a.designs, server=a.server, dim=a.dim, game_dir=a.game_dir, enabled=not a.disabled, dry=a.dry))


def cmd_sync(a):
    print(coop.sync(a.config))


def cmd_craft(a):
    """Resolve a design (or a bare item list) down to raw materials against your containers."""
    import collections
    from . import recipes as recipes_mod
    if not recipes_mod.available():
        print("no recipe data - run: python tools/extract_recipes.py")
        return
    want = collections.Counter()
    for t in a.targets:
        if "=" in t:                                   # craft gold_ingot=64 powered_rail=518
            k, _, v = t.partition("=")
            want[k.split(":")[-1]] += int(v)
            continue
        for _, n in (coop.progress(t, a.world).remaining_cells if a.world
                     else coop.Grid(scan_mod.load(t)).cells()):
            want[n.split(":")[-1]] += 1
    have = collections.Counter() if a.no_have else coop.load_storage(boxed=not a.loose_only)
    plan = recipes_mod.plan(want, have)
    print(f"target: {sum(want.values())} items across {len(want)} kinds"
          + ("" if a.no_have else " | stock: your indexed containers"))
    print(plan.report())


def cmd_prices(a):
    from . import prices as prices_mod
    print(prices_mod.report())


def cmd_plan(a):
    from . import planner
    if a.approve:
        pl = planner.approve(a.approve)
        print(pl.report())
        return
    if a.emit:
        for f in planner.emit(a.emit):
            print("wrote", f)
        return
    if a.upgrade_interfaces:
        pl = planner.upgrade_interfaces(a.upgrade_interfaces)
        anchors = sum(len(m.get("interface", {}).get("anchors", [])) for m in pl.modules)
        print(f"upgraded {pl.name}: {anchors} typed anchors, {len(pl.routes)} routes")
        return
    if a.upgrade_park_contracts:
        pl = planner.upgrade_park_contracts(a.upgrade_park_contracts)
        print(f"upgraded {pl.name}: {len(pl.modules)} park module contract(s)")
        return
    if a.show:
        print(planner.Plan.load(a.show).report())
        return
    pl = planner.make(a.brief or "", a.world, name=a.name, theme=a.theme,
                      island=a.island, plane=a.plane)
    planner.verify(pl)
    pl.save()
    print(pl.report())
    if getattr(pl, "cost", None):
        c = pl.cost
        print(f"  cost: {c['blocks']} blocks, {c['materials']} materials, "
              f"{len(c['short'])} short")


def cmd_parkgate(a):
    """The eight promotion gates PARK_OVERHAUL.md states, over a planned land."""
    from . import gates, planner
    pl = planner.Plan.load(a.plan)
    # These are the PARK gates - PARK_OVERHAUL.md's eight plus the masterplan's two - and run
    # over a casino they would report a building with no ride exits as broken. A category error
    # answered with a long list of failures reads as a defect; it is refused instead.
    if pl.theme not in {"midway", "frontier", "hollow"}:
        print(f"{a.plan} is a {pl.theme!r} plan, not one of the three park lands - "
              "the park gates do not apply to it")
        return 2
    result = gates.run(dict(pl.__dict__), only=set(a.only.split(",")) if a.only else None)
    print(gates.report(result))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(result, indent=1), encoding="utf-8")
        print("wrote", a.json)
    return 0 if result["ok"] else 1


def cmd_layers(a):
    from . import layers
    st = Settings()
    written = layers.slice_plan(a.plan, floor_y=a.floor, prefix=a.prefix)
    for name, n in written:
        print(f"  {name:28s} {n:6d} blocks")
    print(f"{len(written)} layer(s), {sum(n for _x, n in written)} blocks - each one COMPLETE, "
          f"nothing deferred, so they cannot hide each other")
    if a.ship:
        layers.ship(written, st.schem_dir)
        print("shipped to", st.schem_dir)


def cmd_parallel(a):
    from . import parallel
    if a.prepare:
        print("wrote", parallel.prepare(a.prepare))
    elif a.scope:
        print(json.dumps(parallel.scope(a.scope[0], a.scope[1]), indent=2))
    elif a.run:
        print("generated", len(parallel.run_lane(a.run[0], a.run[1], render_sheet=a.render)), "artifact(s)")
    elif a.validate:
        result = parallel.validate(a.validate)
        print(json.dumps(result, indent=2))
    elif a.gate:
        print(json.dumps(parallel.gate(a.gate), indent=2))
    elif a.assemble:
        print("wrote", parallel.assemble(a.assemble, out_dir=a.out_dir, name=a.name))
    elif a.promote:
        print("wrote", parallel.promote(a.promote, out_dir=a.out_dir, name=a.name))
    elif a.dashboard:
        print("wrote", parallel.dashboard(a.dashboard))


def cmd_islands(a):
    from . import islands
    if a.add:
        if not getattr(a, "from_", None):
            print("--add needs --from <capture>: the centre is DISCOVERED from bedrock, never typed")
            return
        isl = islands.add(a.add, a.from_, owner=a.owner or "")
        print(f"{a.add}: bedrock {isl['cx']} {isl['cz']}, radius {isl['radius']}"
              + (f", owner {isl['owner']}" if isl['owner'] else ""))
        return
    if a.where:
        x, z = a.where
        name = islands.at(x, z)
        print(f"{x},{z} -> " + (name or "no island within range"))
        return
    print(islands.report())


def cmd_fleet(a):
    from . import fleet, planner
    if a.release:
        freed = fleet.release(a.release)
        print(f"released {len(freed)}: " + (", ".join(freed) or "nothing"))
        return
    if a.assign:
        pl = planner.Plan.load(a.assign)
        if not pl.approved:
            print(f"plan {a.assign} is NOT approved - nothing is assigned until a human says yes")
            return
        designs = [m["name"] for m in pl.modules]
        accounts = [x.strip() for x in (a.accounts or "").split(",") if x.strip()]
        if not accounts:
            print("name the accounts: --accounts Enroniti,Enroniti2,...")
            return
        # WHERE each design is, read from its own sidecar, so two islands can hold designs of the
        # same name without one account being told its work is taken.
        from . import islands as islands_mod
        where = {}
        for d in designs:
            for cand in (f"out/{d}.litematic", d):
                got = islands_mod.island_of_design(cand)
                if got:
                    where[d] = got
                    break
        st = fleet.assign(designs, accounts, islands_of=where)
        st["plan"] = a.assign
        fleet.save(st)
    print(fleet.report())


def cmd_circuit(a):
    """Inspect a design's redstone, or simulate it against a contract."""
    from . import circuit as circuit_mod
    sc = scan_mod.load(a.design)
    if not circuit_mod.has_redstone(sc.model):
        print(f"{a.design}: no redstone in it")
        return
    findings = circuit_mod.inspect(sc.model, sc.origin)
    print(circuit_mod.report(findings))
    if a.verbose:
        for kind, pos, detail in findings:
            print(f"  {kind:32s} {pos}  {detail}")


def cmd_backup(a):
    from . import backup as backup_mod
    if a.status:
        print(backup_mod.status(a.dest))
        return
    man = backup_mod.run(a.dest, keep=a.keep)
    n = sum(p.get("files", 0) for p in man["parts"].values()
            if isinstance(p, dict) and isinstance(p.get("files"), int))
    size = sum(p.get("bytes", 0) for p in man["parts"].values()
               if isinstance(p, dict) and isinstance(p.get("bytes"), int))
    print(f"backup {man['stamp']}: {n} files, {size/1e6:.0f} MB, ALL VERIFIED -> {man['dir']}")
    if man.get("pruned"):
        print("pruned:", ", ".join(man["pruned"]))


def cmd_card(a):
    out = a.out or _out(scan_mod.resolve(a.design)[0], None, "_card").replace(".litematic", ".png")
    print("wrote", coop.card(a.design, out, a.world))


def cmd_floating(a):
    n, cells, samples = coop.floating_clusters(a.design, a.context)
    print(f"{n} free-floating cluster(s), {cells} cells; e.g. {samples}")


def cmd_blueprint(a):
    """Compile a JSON architectural brief before committing to costly block generation."""
    from . import blueprint
    with open(a.brief, encoding="utf-8") as fh:
        spec = json.load(fh)
    result = blueprint.compile(spec)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("wrote", a.out)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    if a.enforce and not result["quality"]["ok"]:
        raise SystemExit("blueprint quality failed: " + "; ".join(result["quality"]["failures"]))


def cmd_worldspec(a):
    """Compile a bounded Skyblock world brief and report its composition gate."""
    from . import composition, worldnav, worldspec
    with open(a.brief, encoding="utf-8") as fh:
        result = worldspec.compile(json.load(fh))
    result["composition"] = composition.assess(result)
    result["navigation"] = worldnav.audit(result)
    if a.emit:
        result["emitted_configs"] = worldspec.emit_configs(result, a.emit)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("wrote", a.out)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    if a.enforce and (not result["composition"]["ok"] or not result["navigation"]["ok"]):
        failures = result["composition"]["failures"] + result["navigation"]["failures"]
        raise SystemExit("world acceptance failed: " + "; ".join(failures))


def cmd_worldvalidate(a):
    from . import worldassembly
    entry = [int(v) for v in a.entry]
    destinations = [[int(v) for v in point.split(",")] for point in a.destination or []]
    result = worldassembly.validate(a.artifacts, entry=entry, destinations=destinations)
    print(json.dumps(result, indent=2))
    if not result["ok"]: raise SystemExit(1)


def cmd_worldbuild(a):
    from . import design, visual_grade, worldexport, worldrender, worldspec
    with open(a.brief, encoding="utf-8") as fh: plan = worldspec.compile(json.load(fh))
    world = worldrender.infrastructure(plan)
    paths = worldexport.export_chunks(world, a.out, prefix=a.name or plan["name"])
    # Grade per chunk to keep sparse-world review proportional to actual placed content.
    grades = []
    for path in paths:
        from . import schem
        model = schem.load(path)
        review_name = os.path.splitext(os.path.basename(path))[0]
        grades.append({"artifact": path, **visual_grade.assess(model, required_lights=0),
                       "review_packet": design.render_packet(model, os.path.join(a.out, "reviews"), review_name)})
    print(json.dumps({"artifacts": paths, "grades": grades}, indent=2))


def cmd_worldtickets(a):
    from . import tickets, worldschema
    with open(a.plan, encoding="utf-8") as fh: plan = json.load(fh)
    errors = worldschema.validate(plan)
    if errors: raise SystemExit("strict WorldSpec invalid: " + "; ".join(errors))
    print("wrote", *tickets.write(plan, a.out), sep="\n")


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
    p.add_argument("--keep", action="append"); p.add_argument("--out")
    p.add_argument("--by-price", action="store_true",
                   help="use the SERVER's real prices (from /cscan prices) instead of the tier table")
    p.add_argument("--tolerance", type=float, default=30.0, help="max RGB distance a swap may move the colour")
    p.set_defaults(fn=cmd_cheapen)
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
    p.add_argument("designs", nargs="+"); p.add_argument("--world")
    p.add_argument("--have", action="store_true", help="subtract what chunkscan has indexed in your containers")
    p.set_defaults(fn=cmd_shop)
    p = sub.add_parser("storage", help="what chunkscan has indexed inside your containers")
    p.set_defaults(fn=cmd_storage)
    p = sub.add_parser("place", help="DEPRECATED, prefer /cscan place in game: writes Litematica placements into the per-world config; the game must be CLOSED or Litematica overwrites them on exit")
    p.add_argument("designs", nargs="+"); p.add_argument("--server"); p.add_argument("--dim")
    p.add_argument("--game-dir"); p.add_argument("--disabled", action="store_true"); p.add_argument("--dry", action="store_true"); p.set_defaults(fn=cmd_place)
    p = sub.add_parser("adopt", help="take the blocks you actually placed as the design, so progress stops flagging them")
    p.add_argument("designs", nargs="+"); p.add_argument("--world", default="out/island_now.litematic")
    p.set_defaults(fn=cmd_adopt)
    p = sub.add_parser("work", help="write <design>.work.json so /cscan need|next|check can read it")
    p.add_argument("designs", nargs="+"); p.add_argument("--ship", action="store_true"); p.set_defaults(fn=cmd_work)
    p = sub.add_parser("history", help="blocks placed per sync and how many syncs are left")
    p.set_defaults(fn=cmd_history)
    p = sub.add_parser("sync", help="after /cscan: cut latest scan, regenerate remaining designs, progress + shop, learn")
    p.add_argument("--config", default="sync.yaml"); p.set_defaults(fn=cmd_sync)
    p = sub.add_parser("craft", help="resolve a design (or item=count) to RAW materials through the recipe tree")
    p.add_argument("targets", nargs="+", help="design name/path, or item=count")
    p.add_argument("--world", help="only the UNBUILT cells, measured against this capture")
    p.add_argument("--no-have", action="store_true", help="ignore your containers; price it from nothing")
    p.add_argument("--loose-only", action="store_true", help="do not count items inside shulker boxes")
    p.set_defaults(fn=cmd_craft)
    p = sub.add_parser("plan", help="brief -> a sited, costed, circuit-verified island plan you approve")
    p.add_argument("brief", nargs="?", help='e.g. "redstone casino"')
    p.add_argument("--world", default="out/island_now.litematic")
    p.add_argument("--theme"); p.add_argument("--name")
    p.add_argument("--island", help="plan onto a registered island (see: mcbuild islands)")
    p.add_argument("--plane", type=int,
                   help="Y of the gaming floor on a plot with NO GROUND (a fresh skyblock island): "
                        "lay the grid at this course instead of searching for flat terrain")
    p.add_argument("--show"); p.add_argument("--approve"); p.add_argument("--emit")
    p.add_argument("--upgrade-park-contracts", help="add purpose/access contracts without changing a park layout")
    p.add_argument("--upgrade-interfaces", help="add typed anchors and role-typed circulation to an existing park plan, without re-siting it")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("parkgate", help="the eight promotion gates over a planned land: interface, route, capacity, mechanics, safety, wayfinding, night, visual")
    p.add_argument("plan")
    p.add_argument("--only", help="comma-separated gate names (default: all eight)")
    p.add_argument("--json", help="write the full result here for a promotion record")
    p.set_defaults(fn=cmd_parkgate)
    p = sub.add_parser("layers", help="re-slice a plan into complete build steps: floor, machines, walls, fittings")
    p.add_argument("plan")
    p.add_argument("--floor", type=int, required=True, help="Y of the walking surface")
    p.add_argument("--prefix", help="name prefix for the layers (default: the plan's name)")
    p.add_argument("--ship", action="store_true", help="copy them to the schematics folder")
    p.set_defaults(fn=cmd_layers)
    p = sub.add_parser("parallel", help="agent-safe staged generation and deterministic assembly for an approved plan")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", help="freeze an approved plan into isolated lane configs")
    group.add_argument("--scope", nargs=2, metavar=("PLAN", "LANE"), help="print a worker's read/write ownership contract")
    group.add_argument("--run", nargs=2, metavar=("PLAN", "LANE"), help="generate one frozen lane")
    group.add_argument("--validate", help="check staging completeness and cross-lane collisions")
    group.add_argument("--gate", help="show the promotable evidence and stated manual reviews")
    group.add_argument("--assemble", help="publish a plan-ordered composite after validation")
    group.add_argument("--promote", help="pass the acceptance gate and publish a composite")
    group.add_argument("--dashboard", help="write a static review dashboard from staged evidence")
    p.add_argument("--render", action="store_true", help="render individual staged artifacts during --run")
    p.add_argument("--out-dir", default="out", help="destination directory for --assemble")
    p.add_argument("--name", help="published composite name for --assemble")
    p.set_defaults(fn=cmd_parallel)
    p = sub.add_parser("blueprint", help="compile a program-driven building brief (JSON) into architectural contracts")
    p.add_argument("brief", help="JSON brief with name, program, width, and depth")
    p.add_argument("--out", help="write the compiled blueprint JSON")
    p.add_argument("--enforce", action="store_true", help="fail when architectural quality gates fail")
    p.set_defaults(fn=cmd_blueprint)
    p = sub.add_parser("worldspec", help="compile a bounded Skyblock world brief (JSON) into regions, plots, and routes")
    p.add_argument("brief", help="JSON Skyblock site/world brief")
    p.add_argument("--out", help="write the compiled world plan JSON")
    p.add_argument("--emit", help="write strict per-module generator configs to this directory")
    p.add_argument("--enforce", action="store_true", help="fail when composition gates fail")
    p.set_defaults(fn=cmd_worldspec)
    p = sub.add_parser("worldvalidate", help="block-accurate walk/collision audit across assembled Skyblock artifacts")
    p.add_argument("artifacts", nargs="+", help="generated Litematica artifacts with .scan.json sidecars")
    p.add_argument("--entry", nargs=3, required=True, metavar=("X", "Y", "Z"))
    p.add_argument("--destination", action="append", help="world X,Y,Z; repeat for every required stop")
    p.set_defaults(fn=cmd_worldvalidate)
    p = sub.add_parser("worldbuild", help="render WorldSpec infrastructure into sparse Skyblock chunk artifacts")
    p.add_argument("brief", help="JSON Skyblock WorldSpec")
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--name", help="chunk artifact prefix")
    p.set_defaults(fn=cmd_worldbuild)
    p = sub.add_parser("worldtickets", help="write implementation tickets from a strict compiled WorldSpec")
    p.add_argument("plan", help="compiled strict WorldSpec JSON")
    p.add_argument("--out", required=True, help="ticket directory")
    p.set_defaults(fn=cmd_worldtickets)
    p = sub.add_parser("islands", help="the islands this tooling knows: centre from BEDROCK, never typed")
    p.add_argument("--add", help="name it")
    p.add_argument("--from", dest="from_", help="capture to discover the bedrock in")
    p.add_argument("--owner", help="whose island it is (a LABEL, not a permission)")
    p.add_argument("--where", nargs=2, type=int, metavar=("X", "Z"))
    p.set_defaults(fn=cmd_islands)
    p = sub.add_parser("fleet", help="split an approved plan across up to 5 alts (shared schematics dir)")
    p.add_argument("--assign", help="plan name to split")
    p.add_argument("--accounts", help="comma-separated account names")
    p.add_argument("--release", help="hand back everything one account holds")
    p.set_defaults(fn=cmd_fleet)
    p = sub.add_parser("circuit", help="does the redstone work: dead runs, unwired parts, QC risk")
    p.add_argument("design"); p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_circuit)
    p = sub.add_parser("prices", help="what the shop charges, as read in game by /cscan prices on")
    p.set_defaults(fn=cmd_prices)
    p = sub.add_parser("backup", help="full VERIFIED backup of repo + git history + schematics (runs inside sync too)")
    p.add_argument("--dest", help="where to write it (default $MCTEST_BACKUP_DIR, else ~/mctest-backups)")
    p.add_argument("--keep", type=int, default=7, help="how many generations to keep (never below 1)")
    p.add_argument("--status", action="store_true", help="list what backups exist and how old they are")
    p.set_defaults(fn=cmd_backup)
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
    # **A GATE THAT CANNOT FAIL A BUILD IS A REPORT.** Every command here returns None and exits
    # 0; `parkgate` returns 1 when a land is blocked, so it can be the thing a pipeline stops on.
    # Propagating the value costs nothing for the commands that return nothing.
    code = a.fn(a)
    if code:
        raise SystemExit(int(code))


if __name__ == "__main__":
    main()


def cmd_work(a):
    import shutil
    from . import work as work_mod
    from .profile import load as load_profile
    prof = load_profile()
    for d in a.designs:
        out = work_mod.regenerate(d, prof["schem_dir"])
        print("wrote", out)
        if a.ship:
            dest = os.path.join(prof["schem_dir"], os.path.basename(out))
            if os.path.abspath(dest) != os.path.abspath(out):
                shutil.copy(out, dest)
                print("shipped ->", dest)


def cmd_history(a):
    from . import history as history_mod
    print(history_mod.report())


def cmd_adopt(a):
    for d in a.designs:
        print(coop.adopt(d, a.world))
