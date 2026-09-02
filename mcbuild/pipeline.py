"""Config-driven pipelines. A YAML config describes either a GENERATED
design (`gen: <name>` + params) or a DERIVED design (`source: <file>` +
downscale/polish steps). Both then run the same finishing chain:

    cheapen -> hollow -> audit -> save (+ render sheet)

Example configs live in ../configs/.
"""
from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field

import numpy as np
import yaml

from . import audit as audit_mod, render, schem
from .gen import GENERATORS
from .ops import cheapen as cheapen_op, downscale as downscale_op, hollow as hollow_op, polish

from .profile import load as _profile
DEFAULT_SCHEM_DIR = _profile()["schem_dir"]


@dataclass
class Settings:
    schem_dir: str = DEFAULT_SCHEM_DIR
    out_dir: str = "out"
    author: str = "Jack x Claude"
    donors: list[str] = field(default_factory=list)


def _load_donors(paths: list[str], schem_dir: str) -> list[schem.Model]:
    out = []
    for p in paths:
        full = p if os.path.isabs(p) else os.path.join(schem_dir, p)
        if os.path.exists(full):
            out.append(schem.load(full))
    return out


def run_config(path: str, *, settings: Settings | None = None, overrides: dict | None = None,
               ship: bool = False, render_sheet: bool = True, verbose: bool = True) -> tuple[schem.Model, audit_mod.Result]:
    started = time.perf_counter()
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    for k, v in (overrides or {}).items():
        _deep_set(cfg, k, v)
    # Blueprint adoption is deliberately non-invasive: it adds a verified architectural contract
    # to legacy configs without changing their bespoke geometry until that generator is migrated.
    from .blueprint_adapter import apply as apply_blueprint
    cfg, blueprint_plan = apply_blueprint(cfg)
    st = settings or Settings()
    st.schem_dir = cfg.get("schem_dir", st.schem_dir)
    name = cfg.get("name") or os.path.splitext(os.path.basename(path))[0]
    # Optional content-addressed reuse: it is opt-in because a user may deliberately be comparing
    # a generator change, but when enabled it prevents expensive identical regeneration.
    cache_root = cfg.get("cache_dir")
    cache_key = None
    if cache_root and not ship:
        from .cache import artifact_paths, key as cache_key_for
        from .design_compiler import source_digest
        import inspect
        source = ""
        if cfg.get("gen") in GENERATORS:
            source = source_digest(inspect.getsourcefile(GENERATORS[cfg["gen"]].build))
        cache_key = cache_key_for(cfg, source_digest=source)
        cached_lit, cached_side = artifact_paths(cache_root, cache_key)
        if cached_lit.exists():
            os.makedirs(st.out_dir, exist_ok=True)
            out_lit = os.path.join(st.out_dir, f"{name}.litematic")
            shutil.copy2(cached_lit, out_lit)
            if cached_side.exists(): shutil.copy2(cached_side, out_lit.replace(".litematic", ".scan.json"))
            m = schem.load(out_lit)
            res = audit_mod.audit(m, ground=False)
            if verbose: print(f"{name}: reused cache {cache_key[:12]}")
            return m, res
    donors = _load_donors(cfg.get("donors", []), st.schem_dir)

    try:
        m, world_origin, gen_meta = _source_model(cfg, st, donors)
    except ValueError as e:
        if "nothing built" in str(e):
            # A FINISHED design reports complete, it does not raise - the store hall hit
            # this first (100% built, emitted nothing, crashed the pipeline), then the
            # Reaching Root the day Jack finished placing it.
            if verbose:
                print(f"{name}: complete - the world already holds every cell of this design")
            res = audit_mod.Result()
            res.complete = True
            return None, res
        raise
    _polish(m, cfg)
    res = _finish(m, cfg, world_origin, gen_meta, verbose)
    # Every generated sidecar records the mechanics that survived the finish chain.  It is derived
    # from the finished model, not declared by the config, so cheapening/hollowing cannot leave a
    # stale claim about a component that no longer exists.
    from .mechanics import manifest as mechanics_manifest
    from .design import assess as design_assess
    from .journey import evaluate as journey_evaluate
    gen_meta = {**gen_meta, "mechanics": mechanics_manifest(
        m, generator=cfg.get("gen"), roles=cfg.get("roles"))}
    brief = cfg.get("design")
    design = design_assess(m, brief)
    if design["brief"].get("journey"):
        design["journey"] = journey_evaluate(m, design["brief"]["journey"], world_origin)
        if design["brief"].get("enforce") and not design["journey"]["ok"]:
            raise ValueError("design journey contract failed")
    from .scenario import evaluate as scenario_evaluate
    design["scenarios"] = scenario_evaluate(cfg.get("scenarios"), design, gen_meta["mechanics"])
    if design["brief"].get("enforce") and not design["scenarios"]["ok"]:
        raise ValueError("design scenario contract failed")
    if design["brief"].get("visual_review"):
        from .design import render_packet
        review_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        design["visual_packet"] = render_packet(m, os.path.join(st.out_dir, "design_reviews"), review_name)
    from dataclasses import asdict
    from .design_compiler import anchors as compile_anchors, capability_matrix, fingerprint, genome, source_digest, variation
    declared_anchors = compile_anchors(cfg.get("anchors"))
    genome_name = design["brief"].get("style")
    generator_source = ""
    if cfg.get("gen"):
        import inspect
        try:
            generator_source = source_digest(inspect.getsourcefile(GENERATORS[cfg["gen"]].build))
        except (KeyError, TypeError):
            pass
    system = {"fingerprint": fingerprint(cfg, generator_source=generator_source),
              "generator_source_digest": generator_source, "anchors": [asdict(anchor) for anchor in declared_anchors]}
    if genome_name:
        profile = genome(genome_name)
        system["genome"] = profile
        if profile["facades"]:
            system["variation"] = {"facade": variation(cfg.get("name", name), "facade", profile["facades"])}
    system["capabilities"] = capability_matrix(mechanics=gen_meta["mechanics"], design=design,
                                                  anchors_=declared_anchors)
    gen_meta = {**gen_meta, "design": design, "design_system": system,
                **({"blueprint": blueprint_plan} if blueprint_plan else {}),
                **({"park_contract": cfg["park_contract"]} if cfg.get("park_contract") else {})}
    from .efficiency import assess as assess_efficiency
    efficiency = assess_efficiency(m, time.perf_counter() - started, cfg.get("efficiency"))
    gen_meta["efficiency"] = efficiency
    if cfg.get("efficiency", {}).get("enforce") and not efficiency["ok"]:
        raise ValueError("efficiency budget failed: " + "; ".join(efficiency["failures"]))
    from .generator_contract import assess as assess_contract
    from .fun_contract import assess as assess_fun_contract
    from .animal_quality import assess as assess_animal_quality
    from .server_profile import advise_model, current as server_profile, validate_model
    contract = assess_contract(cfg, m, mechanics=gen_meta["mechanics"], design=design)
    fun_contract = assess_fun_contract(cfg.get("fun_contract"))
    animal_spec = cfg.get("animal_contract")
    if animal_spec:
        animal_spec = {**animal_spec, "_visual_review": bool(brief.get("visual_review"))}
    animal_quality = assess_animal_quality(m, generator=cfg.get("gen"), meta=gen_meta,
                                           spec=animal_spec)
    compatibility = validate_model(m)
    # A name a curated capture list happens not to contain is not evidence the server cannot
    # place it - so it is REPORTED, with the list it failed against named, rather than refusing
    # a build. See mcbuild/server_profile.py and CLAUDE.md rule 12.
    unlisted = advise_model(m)
    gen_meta["generator_contract"] = contract
    gen_meta["fun_contract"] = fun_contract
    gen_meta["animal_quality"] = animal_quality
    gen_meta["server_profile"] = server_profile()
    gen_meta["server_compatibility"] = compatibility
    gen_meta["server_unlisted"] = unlisted
    if unlisted and verbose:
        print(f"{name}: {len(unlisted)} block(s) not in the provisional 1.19 list - "
              f"{', '.join(u.rsplit(': ', 1)[-1] for u in unlisted[:8])}"
              f"{' ...' if len(unlisted) > 8 else ''}")
    if cfg.get("world_contract") and (not contract["ok"] or compatibility):
        raise ValueError("world contract failed: " + "; ".join(contract["failures"] + compatibility))
    if cfg.get("fun_contract", {}).get("enforce") and not fun_contract["ok"]:
        raise ValueError("fun contract failed: " + "; ".join(fun_contract["failures"]))
    if cfg.get("animal_contract", {}).get("enforce") and not animal_quality["ok"]:
        raise ValueError("animal quality failed: " + "; ".join(animal_quality["failures"]))
    _save_outputs(m, cfg, st, name, world_origin, gen_meta, ship, render_sheet, verbose)
    if cache_root and cache_key:
        from .cache import artifact_paths
        cached_lit, cached_side = artifact_paths(cache_root, cache_key)
        cached_lit.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(os.path.join(st.out_dir, f"{name}.litematic"), cached_lit)
        side = os.path.join(st.out_dir, f"{name}.scan.json")
        if os.path.exists(side): shutil.copy2(side, cached_side)
    if verbose:
        print(f"performance: {time.perf_counter() - started:.3f}s, {int(m.solid().sum())} blocks")
    return m, res


def _source_model(cfg, st, donors):
    """Generated (gen:) or derived (source:) model plus its world origin / generator meta."""
    # ---- source model --------------------------------------------------------
    if "gen" in cfg:
        gname = cfg["gen"]
        if gname not in GENERATORS:
            raise KeyError(f"unknown generator {gname}; have {list(GENERATORS)}")
        canvas = GENERATORS[gname].build(cfg.get("params", {}), donors)
        m = canvas.to_model()
        world_origin = getattr(canvas, "world_origin", None)
        gen_meta = getattr(canvas, "meta", {})
    elif "source" in cfg:
        src = cfg["source"]
        src = src if os.path.isabs(src) else os.path.join(st.schem_dir, src)
        m = schem.load(src)
        ds = cfg.get("downscale")
        if ds:
            m = downscale_op(m, ds.get("factor", 2), threshold=ds.get("threshold", 0.42),
                             accents=ds.get("accents"), mirror_x=ds.get("mirror_x", False),
                             min_component=ds.get("min_component", 6))
    else:
        raise ValueError("config needs 'gen' or 'source'")
    if "gen" not in cfg:
        world_origin, gen_meta = None, {}

    return m, world_origin, gen_meta


def _polish(m, cfg):
    # ---- polish steps --------------------------------------------------------
    for step in cfg.get("polish", []) or []:
        op = step.get("op")
        if op == "despeckle":
            polish.despeckle(m, protected=set(step.get("protected", [])),
                             max_size=step.get("max_size", 2), passes=step.get("passes", 2))
        elif op == "paint":
            cells = {(int(k.split(",")[0]), int(k.split(",")[1])): v for k, v in step["cells"].items()}
            polish.paint_front(m, cells, only_if=set(step["only_if"]) if step.get("only_if") else None)
        elif op == "fill":
            polish.fill_front_region(m, tuple(step["y"]), tuple(step["x"]), step["block"],
                                     only_if=set(step["only_if"]) if step.get("only_if") else None)
        elif op == "mirror":
            polish.mirror_front(m, y_from=step.get("y_from", 0), take=step.get("take", "left"))
        elif op == "clean_body":
            polish.clean_body(m, step["base"], keep_front_rows=tuple(step["keep_front_rows"]) if step.get("keep_front_rows") else None,
                              keep_names=set(step.get("keep_names", [])), ground_row_names=set(step.get("ground_row_names", [])))
        else:
            raise ValueError(f"unknown polish op {op}")



def _finish(m, cfg, world_origin, gen_meta, verbose):
    """cheapen -> hollow -> drop floaters -> compact -> audit (in context when configured)."""
    # ---- finishing -----------------------------------------------------------
    fin = cfg.get("finish", {}) or {}
    if fin.get("cheapen", True):
        rep = cheapen_op(m, extra=fin.get("substitutions"), keep=set(fin.get("keep", [])))
        if verbose and rep:
            print("cheapen:", ", ".join(f"{k.split(':')[-1]}:{v}" for k, v in rep.items()))
    if fin.get("hollow", False):
        h = fin["hollow"] if isinstance(fin["hollow"], dict) else {}
        stats = hollow_op(m, shell=h.get("shell", 2), ground=h.get("ground", True),
                          ceiling=h.get("ceiling", False), keep_floor=h.get("keep_floor", True),
                          keep_top_layers=h.get("keep_top_layers", 0))
        if verbose:
            print("hollow:", stats)
    # DEFER_TO: drop any cell another design already claims, so two designs never ask the player
    # to place - or break - the same block twice. Precedence is stated by the config that yields,
    # which means the order you generate in matters: build the winner first.
    if fin.get("carve_for"):
        n = _carve_for(m, world_origin, fin["carve_for"])
        if verbose and n:
            print(f"carved {n} cells out for " + ", ".join(
                os.path.basename(q["design"] if isinstance(q, dict) else q)
                for q in (fin["carve_for"] if isinstance(fin["carve_for"], (list, tuple))
                          else [fin["carve_for"]])))
    if fin.get("defer_to"):
        n = _defer_to(m, world_origin, fin["defer_to"])
        if verbose and n:
            print(f"deferred {n} cells to " + ", ".join(
                os.path.basename(q) for q in fin["defer_to"]))
        # deferral orphans: a cell whose every design neighbour went to another design and
        # which the world does not touch either can never be placed and never looks right.
        # Swept to a FIXPOINT, because orphans cascade - a rail wall kept for its lateral
        # neighbour is orphaned the moment that neighbour's own post defers.
        if n and fin.get("verify_against") and world_origin is not None:
            dropped = _drop_defer_orphans(m, world_origin, fin["verify_against"])
            if verbose and dropped:
                print(f"dropped {dropped} deferral orphan(s) - no neighbour left to place against")
    # TRIM_BURIED: drop design cells the terrain already owns. A cell inside a ground rise can
    # never be placed (a litematica printer places into air only), would be invisible if it were,
    # and stands as permanent amber in /cscan check - the Court Hall's unbuildable-cells problem,
    # solved at the seam instead of reported forever. Opt-in, because for a REPAVING design
    # "the world holds something different" is the work, not an obstruction.
    if fin.get("trim_buried") and fin.get("verify_against") and world_origin is not None:
        n = _trim_buried(m, world_origin, fin["verify_against"],
                         set(gen_meta.get("clear", [])) | set(fin.get("context_clear", [])))
        if verbose and n:
            print(f"trim_buried: {n} cells yielded to existing terrain")
    if fin.get("drop_floaters", True):
        n = _drop_floaters(m, max_size=int(fin.get("floater_max", 3)))
        if verbose and n:
            print(f"dropped {n} floating fragment blocks")
    m.compact_palette()

    res = audit_mod.audit(m, ground=fin.get("ground", True), climb=bool(fin.get("climb")),
                          symmetry=bool(fin.get("symmetry")), symmetry_rows_from=int(fin.get("symmetry_rows_from", 0)),
                          ground_block=fin.get("ground_block"))
    if verbose:
        print(res.report())
    # A REDSTONE DESIGN CANNOT SHIP UNEXAMINED. The audit answers whether every block is legal,
    # supported and affordable, and a circuit passes all of that while doing nothing at all - the
    # one subsystem whose wrongness is invisible in every render, every audit and every BOM. This
    # is a SMELL check, not a proof: it catches dead wire runs, orphaned dust and components
    # nothing can drive. A machine with a contract gets simulated properly by `mcbuild.circuit`.
    # ...but only when there is no CONTEXT coming. A DESIGN HERE IS REMAINING WORK, so half a
    # circuit may already be standing in the world and inspecting the design alone reports every
    # comparator as reading nothing. The first version of this hook did exactly that to the item
    # sorter - four false alarms on a design that is fine - which is the same "verify in context,
    # never in isolation" rule as rule 2, arriving from a new direction.
    from . import circuit as circuit_mod
    if verbose and circuit_mod.has_redstone(m) and not fin.get("verify_against"):
        print(circuit_mod.report(circuit_mod.inspect(m, world_origin or (0, 0, 0))))
    if fin.get("verify_against") and world_origin is not None:
        res = _verify_in_context(m, res, fin["verify_against"], world_origin, verbose,
                                 ignore=set(fin.get("verify_replaceable", [])),
                                 ignore_boxes=gen_meta.get("exclude_boxes", []), dig_above=bool(fin.get("verify_dig_above")),
                                 context_clear=set(gen_meta.get("clear", [])) | set(fin.get("context_clear", [])))

    return res


def _lock_origin(m, world_origin, lock):
    """Pad the model with air so its origin corner is `lock` (must be <= the natural origin on every axis).
    Every design then shares one paste origin, and regenerating never moves it."""
    import numpy as np
    lx, ly, lz = lock
    wx, wy, wz = world_origin
    if wx < lx or wy < ly or wz < lz:
        raise ValueError(f"origin_lock {lock} is not <= the design's natural origin {world_origin}; enlarge the lock box")
    sy, sz, sx = m.ids.shape
    ids = np.zeros((sy + wy - ly, sz + wz - lz, sx + wx - lx), np.int32)
    ids[wy - ly:, wz - lz:, wx - lx:] = m.ids
    m.ids = ids
    for t in m.tile_entities:
        for k, d in (("x", wx - lx), ("y", wy - ly), ("z", wz - lz)):
            t.value[k] = type(t.value[k])(t.value[k].id, t.value[k].value + d)
    return m, (lx, ly, lz)


def _after(cfg: dict) -> list[str]:
    """Design names this one must be built AFTER, for the sidecar's `after` list.

    Derived from `finish.defer_to` rather than restated: deferring IS the ordering. A design that
    yields a shared cell to another one cannot be built first - the cell it dropped is the other
    design's, and placing round a hole nobody has filled yet is how you build twice.

    This only ever existed in Python. `finish.defer_to` settled precedence at generation time and
    CLAUDE.md stated the sequences in prose ("portal first, ruinway defers to it"), and none of it
    reached the mod - so `/cscan follow all` walked the tracked list as written. `finish.after` is
    the escape hatch for an order that is real but not expressed as a shared cell, which is what
    the Falls needs: its notch is the plug, and it has to be cut last.
    """
    fin = cfg.get("finish") or {}
    out = []
    for q in fin.get("defer_to") or []:
        base = os.path.basename(str(q))
        for ext in (".litematic", ".scan.json"):
            if base.endswith(ext):
                base = base[: -len(ext)]
        if base and base not in out:
            out.append(base)
    for q in fin.get("after") or []:
        if q not in out:
            out.append(str(q))
    return out


def _save_outputs(m, cfg, st, name, world_origin, gen_meta, ship, render_sheet, verbose):
    lock = cfg.get("origin_lock", _profile().get("origin_lock"))
    if world_origin is not None and lock and cfg.get("origin_lock") is not False:
        m, world_origin = _lock_origin(m, world_origin, tuple(int(v) for v in lock))
    os.makedirs(st.out_dir, exist_ok=True)
    out_path = os.path.join(st.out_dir, f"{name}.litematic")
    schem.save(out_path, m, name=name, author=st.author)
    side_path = None
    if world_origin is not None:
        from . import scan as scan_mod
        sx, sy, sz = m.shape_xyz
        side_path = scan_mod.save_pair(out_path, m, {
            "origin": {"x": world_origin[0], "y": world_origin[1], "z": world_origin[2]},
            "size": {"x": sx, "y": sy, "z": sz}, "generated_by": cfg.get("gen"),
            **({"after": _after(cfg)} if _after(cfg) else {}), **gen_meta}, name=name)
        from . import work as work_mod
        work_path = work_mod.write(out_path, m, world_origin, name, gen_meta.get("dig", []))
        if verbose:
            print(f"paste origin {world_origin[0]} {world_origin[1]} {world_origin[2]}  ({os.path.basename(side_path)})")
    if render_sheet:
        render.contact_sheet(m).save(os.path.join(st.out_dir, f"{name}.png"))
    if ship:
        import shutil
        shutil.copy(out_path, os.path.join(st.schem_dir, f"{name}.litematic"))
        if side_path:
            shutil.copy(side_path, os.path.join(st.schem_dir, os.path.basename(side_path)))
            shutil.copy(work_path, os.path.join(st.schem_dir, os.path.basename(work_path)))
        if verbose:
            print("shipped ->", os.path.join(st.schem_dir, f"{name}.litematic"))
    if verbose:
        print("wrote", out_path)


def _trim_buried(m, origin, capture, context_clear: set) -> int:
    """Zero design cells where the capture holds a DIFFERENT block that is not air and not in
    the clear list. Same-state cells stay: they are the design's own built progress."""
    import numpy as np
    from . import nbt, scan as scan_mod
    files = capture if isinstance(capture, (list, tuple)) else [capture]
    s = scan_mod.load(files[0])
    ox, oy, oz = s.origin
    wnames = [n.split(":")[-1] for n in s.model.names]
    passable = np.array([n in ("air", "cave_air", "void_air") or n in context_clear
                         for n in wnames])
    wkeys = [nbt.state_key(e) for e in s.model.palette]
    dkeys = [nbt.state_key(e) for e in m.palette]
    mx, my, mz = origin
    trimmed = 0
    ys, zs, xs = np.where(m.ids > 0)
    for y, z, x in zip(ys, zs, xs):
        wy, wz, wx = y + my - oy, z + mz - oz, x + mx - ox
        if not (0 <= wy < s.model.ids.shape[0] and 0 <= wz < s.model.ids.shape[1]
                and 0 <= wx < s.model.ids.shape[2]):
            continue
        wi = int(s.model.ids[wy, wz, wx])
        if passable[wi]:
            continue
        if wkeys[wi] == dkeys[int(m.ids[y, z, x])]:
            continue                                   # already built correctly - keep
        m.ids[y, z, x] = 0
        trimmed += 1
    return trimmed


def _verify_in_context(m, res, capture, origin, verbose: bool, ignore: set | None = None, ignore_boxes=(),
                       dig_above: bool = False, context_clear: set | None = None):
    """Composite onto the real capture (plus any extra context files, e.g. an already-designed belly)
    and audit THAT: overlaps with existing blocks and any placement problem in context become the
    gating problems (the capture itself audits clean). `ignore` names are only cleared where the
    design places a block (they are the blocks the player digs out first)."""
    import numpy as np
    from . import scan as scan_mod
    files = capture if isinstance(capture, (list, tuple)) else [capture]
    s = scan_mod.load(files[0])
    for extra in files[1:]:
        e = scan_mod.load(extra)
        merged, _ = scan_mod.merge(s, e.model, e.origin)
        s = scan_mod.Scan(merged, {**s.meta, "origin": {"x": min(s.origin[0], e.origin[0]), "y": min(s.origin[1], e.origin[1]),
                                                       "z": min(s.origin[2], e.origin[2])}}, s.litematic_path, s.sidecar_path)
    ox, oy, oz = s.origin
    if context_clear:                               # blocks the player clears wholesale first (the old vine strands)
        names = np.array([n.split(":")[-1] for n in s.model.names])
        s.model.ids = np.where(np.isin(names, list(context_clear))[s.model.ids], 0, s.model.ids)
    if ignore:
        names = np.array([n.split(":")[-1] for n in s.model.names])
        repl = np.isin(names, list(ignore))[s.model.ids]
        mx, my, mz = origin
        msy, msz, msx = m.ids.shape
        design = np.zeros_like(repl)
        y0, z0, x0 = my - oy, mz - oz, mx - ox
        ys_ = slice(max(0, y0), min(repl.shape[0], y0 + msy)); zs_ = slice(max(0, z0), min(repl.shape[1], z0 + msz)); xs_ = slice(max(0, x0), min(repl.shape[2], x0 + msx))
        sub = m.ids[ys_.start - y0:ys_.stop - y0, zs_.start - z0:zs_.stop - z0, xs_.start - x0:xs_.stop - x0] > 0
        design[ys_, zs_, xs_] = sub
        if dig_above:                                # plants sitting on the cells the design replaces
            design[1:] |= design[:-1]
        s.model.ids = np.where(repl & design, 0, s.model.ids)
    for x1, y1, z1, x2, y2, z2 in ignore_boxes:          # decor the player re-hangs afterwards
        s.model.ids[max(0, min(y1, y2) - oy):max(y1, y2) - oy + 1, max(0, min(z1, z2) - oz):max(z1, z2) - oz + 1,
                    max(0, min(x1, x2) - ox):max(x1, x2) - ox + 1] = 0
    # Audit the context ALONE first. Every finite cut truncates vines, chains and lanterns at its
    # edges, so a capture has problems of its own - island_deep has 42, island_void 72 - and reporting
    # them against the design sends you hunting faults you did not cause.
    baseline = {(pr.kind, pr.x, pr.y, pr.z) for pr in audit_mod.audit(s.model, ground=False).problems}
    merged, overlap = scan_mod.merge(s, m, origin)
    overlap -= _already_built_cells(m, origin, s)   # a cell the world already holds correctly is built, not a collision
    ctx = audit_mod.audit(merged, ground=False)
    ctx.problems = [pr for pr in ctx.problems if (pr.kind, pr.x, pr.y, pr.z) not in baseline]
    if verbose:
        print(f"in context of {', '.join(os.path.basename(f) for f in files)}: overlap {overlap} cells, "
              f"NEW problems {len(ctx.problems)} (capture already had {len(baseline)}), "
              f"cavity cells {ctx.cavity_cells}, leaks {ctx.leaks}")
        for pr in ctx.problems[:15]:
            print("  ", pr)
    from . import circuit as circuit_mod
    if verbose and circuit_mod.has_redstone(m):
        # Inspect the design AS IT WILL STAND: the composite, not the remainder. And diff against
        # the context ALONE, exactly as the audit's `baseline` above does - the island already has
        # twelve quasi-connectivity risks and seven orphaned dust groups of its own, and reporting
        # those against a new design sends you hunting faults you did not cause.
        before = {(k, tuple(pos)) for k, pos, _ in circuit_mod.inspect(s.model, s.origin)}
        new = [f for f in circuit_mod.inspect(merged, s.origin)
               if (f[0], tuple(f[1])) not in before]
        print(circuit_mod.report(new).replace("circuit:", "circuit (new):"))
    n_cl, n_cells = _floating(m, origin, s)
    if verbose and n_cl:
        print(f"buildability: {n_cl} free-floating cluster(s), {n_cells} cells - need temporary scaffold (nothing adjacent to place against)")
    res.floating = (n_cl, n_cells)
    res.problems = list(ctx.problems)
    if overlap:
        res.problems.append(audit_mod.Problem("overlap", 0, 0, 0, f"{overlap} cells collide with existing blocks"))
    res.leaks = ctx.leaks
    return res


def _floating(m, origin, s):
    """Design clusters (6-conn) touching nothing in the merged context."""
    from . import morph
    import numpy as np
    labels, sizes = morph.components(m.ids > 0, conn=6)
    names = np.array([n.split(":")[-1] for n in s.model.names])
    ox, oy, oz = s.origin; mx, my, mz = origin
    sy, sz, sx = s.model.ids.shape

    def solid(X, Y, Z):
        y, z, x = Y - oy, Z - oz, X - ox
        return 0 <= y < sy and 0 <= z < sz and 0 <= x < sx and s.model.ids[y, z, x] > 0 and str(names[s.model.ids[y, z, x]]) != "vine"

    n_cl = n_cells = 0
    for i, sz_ in enumerate(sizes, 1):
        comp = np.argwhere(labels == i)
        if not any(solid(x + mx + dx, y + my + dy, z + mz + dz) for y, z, x in comp
                   for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))):
            n_cl += 1; n_cells += int(sz_)
    return n_cl, n_cells


def _carve_for(m: schem.Model, world_origin, specs) -> int:
    """Zero every cell inside another design's WALKING ENVELOPE - its dig list and the headroom
    over the things you stand on.

    `defer_to` handles two designs wanting the same CELL. This handles the other case: a design
    that must leave a HOLE for another one to pass through. The shop islet's lens fill sits exactly
    where the Lowland Stair screws down through it, and the well was cut by hand once - with a note
    in the config saying *"regenerating this design re-fills the well and must be followed by
    re-carving"* and a test as the tripwire.

    THAT NOTE IS THE BUG. A step that has to be remembered is a step that gets lost, and it was:
    regenerating the islet to fix an unrelated grass problem re-filled the well and the tripwire
    fired. It is part of the pipeline now, so the carve survives every regeneration by construction.

    Each spec is `{design: <path>, headroom: 4, over: slab}` - the dig cells always, plus
    `headroom` courses above every cell of `over` (a substring of the block name).
    """
    if world_origin is None:
        return 0
    from . import scan as scan_mod
    ox, oy, oz = world_origin
    hit = 0
    for spec in (specs if isinstance(specs, (list, tuple)) else [specs]):
        if isinstance(spec, str):
            spec = {"design": spec}
        try:
            other = scan_mod.load(spec["design"])
        except Exception:                                        # noqa: BLE001
            continue
        head = int(spec.get("headroom", 4))
        over = spec.get("over", "slab")
        env = set()
        for d in (other.meta.get("dig") or []):
            if isinstance(d, dict):
                env.add((int(d["x"]), int(d["y"]), int(d["z"])))
            elif isinstance(d, (list, tuple)) and len(d) >= 3:
                env.add((int(d[0]), int(d[1]), int(d[2])))
        om = other.model
        names = [n.split(":")[-1] for n in om.names]
        bx, by, bz = other.origin
        for y, z, x in zip(*np.nonzero(om.ids != 0)):
            if over and over not in names[om.ids[y, z, x]]:
                continue
            for k in range(head):
                env.add((int(bx + x), int(by + y + k), int(bz + z)))
        for (wx, wy, wz) in env:
            lx, ly, lz = wx - ox, wy - oy, wz - oz
            if (0 <= lx < m.ids.shape[2] and 0 <= ly < m.ids.shape[0]
                    and 0 <= lz < m.ids.shape[1] and m.ids[ly, lz, lx]):
                m.ids[ly, lz, lx] = 0
                hit += 1
    return hit


def _defer_to(m: schem.Model, world_origin, paths) -> int:
    """Zero every cell that one of `paths` also fills.

    Overlapping designs are not a rendering problem, they are a WORK problem: the player places a
    block, the next placement tells them it is wrong, and they break it and place it again. The
    four deck designs shared 39 such cells before this existed.
    """
    if world_origin is None:
        return 0
    from . import scan as scan_mod
    ox, oy, oz = world_origin
    hit = 0
    for q in (paths if isinstance(paths, (list, tuple)) else [paths]):
        try:
            other = scan_mod.load(q)
        except Exception:
            continue
        om = other.model
        bx, by, bz = other.origin
        for y, z, x in zip(*np.nonzero(om.ids != 0)):
            lx, ly, lz = bx + x - ox, by + y - oy, bz + z - oz
            if (0 <= lx < m.ids.shape[2] and 0 <= ly < m.ids.shape[0]
                    and 0 <= lz < m.ids.shape[1] and m.ids[ly, lz, lx]):
                m.ids[ly, lz, lx] = 0
                hit += 1
                # a deferred cell takes its dependants with it: a lantern, torch or rail
                # wall standing on a cell that just went to another design is this design's
                # cell standing on air - the Lowland Stair shipped both kinds once
                if ly + 1 < m.ids.shape[0] and m.ids[ly + 1, lz, lx]:
                    above = m.names[m.ids[ly + 1, lz, lx]].split(":")[-1].split("[")[0]
                    if above in ("lantern", "soul_lantern", "torch") \
                            or above.endswith("_wall"):
                        nbrs = 0
                        for ddx, ddy, ddz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                              (0, 0, 1), (0, 0, -1)):
                            ax2, ay2, az2 = lx + ddx, ly + 1 + ddy, lz + ddz
                            if (0 <= ax2 < m.ids.shape[2] and 0 <= ay2 < m.ids.shape[0]
                                    and 0 <= az2 < m.ids.shape[1]
                                    and m.ids[ay2, az2, ax2]):
                                nbrs += 1
                        if nbrs == 0:
                            m.ids[ly + 1, lz, lx] = 0
                            hit += 1
    return hit


_ORPHAN_PASSABLE = {"air", "cave_air", "void_air", "vine", "glow_lichen", "moss_carpet",
                    "short_grass", "tall_grass", "fern", "large_fern", "azalea",
                    "flowering_azalea", "hanging_roots", "water"}


def _drop_defer_orphans(m: schem.Model, origin, capture) -> int:
    """After defer_to: remove cells with no design neighbour AND no world contact."""
    from . import scan as scan_mod
    files = capture if isinstance(capture, (list, tuple)) else [capture]
    s = scan_mod.load(files[0])
    snames = [n.split(":")[-1].split("[")[0] for n in s.model.names]
    sox, soy, soz = s.origin
    ox, oy, oz = origin

    def world_solid(wx, wy, wz):
        ly, lz, lx = wy - soy, wz - soz, wx - sox
        if not (0 <= ly < s.model.ids.shape[0] and 0 <= lz < s.model.ids.shape[1]
                and 0 <= lx < s.model.ids.shape[2]):
            return False
        return snames[s.model.ids[ly, lz, lx]] not in _ORPHAN_PASSABLE

    dropped = 0
    changed = True
    while changed:
        changed = False
        for y, z, x in zip(*np.nonzero(m.ids != 0)):
            alone = True
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                               (0, 0, 1), (0, 0, -1)):
                ny, nz, nx = y + dy, z + dz, x + dx
                if (0 <= ny < m.ids.shape[0] and 0 <= nz < m.ids.shape[1]
                        and 0 <= nx < m.ids.shape[2] and m.ids[ny, nz, nx]):
                    alone = False
                    break
                if world_solid(ox + nx, oy + ny, oz + nz):
                    alone = False
                    break
            if alone:
                m.ids[y, z, x] = 0
                dropped += 1
                changed = True
    return dropped


def _drop_floaters(m: schem.Model, max_size: int = 3) -> int:
    """Remove tiny disconnected fragments that are NOT resting on y0."""
    from . import morph
    s = m.solid()
    labels, sizes = morph.components(s, conn=26)
    n = 0
    for i, sz in enumerate(sizes, 1):
        if sz > max_size:
            continue
        cells = labels == i
        if cells[0].any():                       # touches the ground plane: keep
            continue
        m.ids[cells] = 0
        n += sz
    return n


def _deep_set(d: dict, dotted: str, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = _coerce(value)


def _coerce(v):
    if isinstance(v, str):
        for cast in (int, float):
            try:
                return cast(v)
            except ValueError:
                pass
        if v.lower() in ("true", "false"):
            return v.lower() == "true"
        if v.startswith("[") and v.endswith("]"):
            return [_coerce(x.strip()) for x in v[1:-1].split(",") if x.strip()]
    return v


def _already_built_cells(m, origin, s) -> int:
    """Design cells whose world block is a match: the design is built there, so it is not a collision.

    Without this every finished design reports its own blocks as overlaps the moment you build it."""
    import numpy as np
    from .coop import _same
    ox, oy, oz = s.origin
    mx, my, mz = origin
    csy, csz, csx = s.model.ids.shape
    msy, msz, msx = m.ids.shape
    wn = [n.split(":")[-1] for n in s.model.names]
    dn = [n.split(":")[-1] for n in m.names]
    n = 0
    ys, zs, xs = np.where(m.ids > 0)
    for y, z, x in zip(ys, zs, xs):
        wy_, wz_, wx_ = my + y - oy, mz + z - oz, mx + x - ox
        if not (0 <= wy_ < csy and 0 <= wz_ < csz and 0 <= wx_ < csx):
            continue
        wi = s.model.ids[wy_, wz_, wx_]
        if wi and _same(dn[m.ids[y, z, x]], wn[wi], True):
            n += 1
    return n
