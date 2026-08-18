"""Config-driven pipelines. A YAML config describes either a GENERATED
design (`gen: <name>` + params) or a DERIVED design (`source: <file>` +
downscale/polish steps). Both then run the same finishing chain:

    cheapen -> hollow -> audit -> save (+ render sheet)

Example configs live in ../configs/.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

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
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    for k, v in (overrides or {}).items():
        _deep_set(cfg, k, v)
    st = settings or Settings()
    st.schem_dir = cfg.get("schem_dir", st.schem_dir)
    name = cfg.get("name") or os.path.splitext(os.path.basename(path))[0]
    donors = _load_donors(cfg.get("donors", []), st.schem_dir)

    m, world_origin, gen_meta = _source_model(cfg, st, donors)
    _polish(m, cfg)
    res = _finish(m, cfg, world_origin, gen_meta, verbose)
    _save_outputs(m, cfg, st, name, world_origin, gen_meta, ship, render_sheet, verbose)
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
    if fin.get("drop_floaters", True):
        n = _drop_floaters(m, max_size=int(fin.get("floater_max", 3)))
        if verbose and n:
            print(f"dropped {n} floating fragment blocks")
    m.compact_palette()

    res = audit_mod.audit(m, ground=fin.get("ground", True),
                          symmetry=bool(fin.get("symmetry")), symmetry_rows_from=int(fin.get("symmetry_rows_from", 0)),
                          ground_block=fin.get("ground_block"))
    if verbose:
        print(res.report())
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
            "size": {"x": sx, "y": sy, "z": sz}, "generated_by": cfg.get("gen"), **gen_meta}, name=name)
        if verbose:
            print(f"paste origin {world_origin[0]} {world_origin[1]} {world_origin[2]}  ({os.path.basename(side_path)})")
    if render_sheet:
        render.contact_sheet(m).save(os.path.join(st.out_dir, f"{name}.png"))
    if ship:
        import shutil
        shutil.copy(out_path, os.path.join(st.schem_dir, f"{name}.litematic"))
        if side_path:
            shutil.copy(side_path, os.path.join(st.schem_dir, os.path.basename(side_path)))
        if verbose:
            print("shipped ->", os.path.join(st.schem_dir, f"{name}.litematic"))
    if verbose:
        print("wrote", out_path)


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
    merged, overlap = scan_mod.merge(s, m, origin)
    ctx = audit_mod.audit(merged, ground=False)
    if verbose:
        print(f"in context of {', '.join(os.path.basename(f) for f in files)}: overlap {overlap} cells, "
              f"problems {len(ctx.problems)}, cavity cells {ctx.cavity_cells}, leaks {ctx.leaks}")
        for pr in ctx.problems[:15]:
            print("  ", pr)
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
