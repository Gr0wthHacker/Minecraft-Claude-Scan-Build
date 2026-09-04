"""Co-op build tooling on top of chunkscan captures.

    progress   design vs latest scan: % built, what is left (by material / region), deviations
    remaining  export only the unbuilt cells of a design (same origin) so a teammate loads their to-do
    diff       two captures: added / removed / swapped by material and region
    merge      several captures -> one, chunk-aware: the newest scan is authoritative for the chunks it loaded
    shop       bill of materials in stacks / shulkers, cheap-vs-buy, optionally minus what is already built
    place      merge Litematica placement entries (schematic + origin) into the per-world config file

Everything is world-coordinate based via the .scan.json sidecars.
"""
from __future__ import annotations

import collections
import json
import datetime as _dt
import os
from dataclasses import dataclass, field

import numpy as np

from . import morph, palette, scan, schem
from .pipeline import DEFAULT_SCHEM_DIR
from .profile import load as load_profile

AIR = {"air", "cave_air", "void_air"}
# ground cover a design is allowed to replace: counts as "still to build (clear first)", never as a deviation
REPLACEABLE = {"vine", "short_grass", "tall_grass", "fern", "large_fern", "moss_carpet", "snow", "dead_bush",
               "pink_tulip", "white_tulip", "red_tulip", "orange_tulip", "poppy", "dandelion", "azalea",
               "flowering_azalea", "lily_of_the_valley", "cornflower", "oxeye_daisy", "azure_bluet", "allium",
               "sweet_berry_bush", "pink_petals", "glow_lichen", "water"}
ROCK_FAMILY = {"cobblestone", "stone", "mossy_cobblestone", "stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks", "moss_block"}
SLAB_FAMILY = {"stone_brick_slab", "mossy_stone_brick_slab", "cobblestone_slab", "mossy_cobblestone_slab", "smooth_stone_slab"}
# families whose members are interchangeable: the texture mix is cosmetic, so any member counts as built
LOOSE_FAMILIES = (ROCK_FAMILY, SLAB_FAMILY)
# A block a design ships ONLY so that breaking it leaves the thing actually wanted. The lowland's
# pond is ice because a printer places blocks out of your inventory and water is not a block; mine
# the sheet and every cell is a water source, which IS the finished pond. Without this the pond
# reads as 1,111 deviations the moment it is right, and the build loop keeps flying to it.
#
# DIRECTIONAL on purpose, which is why it cannot be a LOOSE_FAMILY: ice found where water was
# wanted is a pond that FROZE - the failure the sky-well court shipped once and the guard lanterns
# exist to prevent - and must stay a deviation.
BECOMES = {"ice": {"water"}}


def _names(m: schem.Model) -> np.ndarray:
    return np.array([n.split(":")[-1] for n in m.names])


class Grid:
    """World-coordinate view over a Scan."""

    def __init__(self, s: scan.Scan):
        self.s = s
        self.names = _names(s.model)
        self.ox, self.oy, self.oz = s.origin
        self.ids = s.model.ids
        self.sy, self.sz, self.sx = self.ids.shape

    def inside(self, x, y, z) -> bool:
        return 0 <= y - self.oy < self.sy and 0 <= z - self.oz < self.sz and 0 <= x - self.ox < self.sx

    def name(self, x, y, z) -> str:
        if not self.inside(x, y, z):
            return "OOB"
        return str(self.names[self.ids[y - self.oy, z - self.oz, x - self.ox]])

    def cells(self):
        for y, z, x in np.argwhere(self.ids > 0):
            yield (int(x + self.ox), int(y + self.oy), int(z + self.oz)), str(self.names[self.ids[y, z, x]])


# ------------------------------------------------------------------ progress / remaining

@dataclass
class Progress:
    design: str
    total: int = 0
    built: int = 0
    wrong: int = 0
    oob: int = 0
    missing_by: collections.Counter = field(default_factory=collections.Counter)
    wrong_by: collections.Counter = field(default_factory=collections.Counter)
    missing_regions: collections.Counter = field(default_factory=collections.Counter)
    remaining_cells: list = field(default_factory=list)          # ((x,y,z), name)
    clear_first: collections.Counter = field(default_factory=collections.Counter)   # world blocks in the way

    @property
    def pct(self) -> float:
        return 100.0 * self.built / self.total if self.total else 0.0

    def report(self, top: int = 12) -> str:
        lines = [f"{self.design}: {self.built}/{self.total} built ({self.pct:.0f}%), {self.wrong} cells hold a different block, "
                 f"{self.oob} outside the scan box (unknown)",
                 "left: " + ", ".join(f"{k}:{v}" for k, v in self.missing_by.most_common(top))]
        if self.clear_first:
            lines.append("clear first: " + ", ".join(f"{k}:{v}" for k, v in self.clear_first.most_common(8)))
        if self.wrong_by:
            lines.append("deviations (design -> world): " + ", ".join(f"{a}->{b}:{n}" for (a, b), n in self.wrong_by.most_common(8)))
        if self.missing_regions:
            lines.append("left by region (x,z 16-chunk): " + ", ".join(f"({x},{z}):{n}" for (x, z), n in self.missing_regions.most_common(8)))
        return "\n".join(lines)


def _same(want: str, have: str, loose_rock: bool) -> bool:
    if want == have:
        return True
    if have in BECOMES.get(want, ()):
        return True
    return loose_rock and any(want in fam and have in fam for fam in LOOSE_FAMILIES)


def progress(design: str, world: str, *, loose_rock: bool = True, ignore_world: set | None = None) -> Progress:
    """`loose_rock`: any belly-palette rock counts as built (texture variants are cosmetic).
    `ignore_world`: world blocks a design may replace -> counted as still-to-build, not as a deviation."""
    ignore_world = REPLACEABLE if ignore_world is None else set(ignore_world)
    d = Grid(scan.load(design)); w = Grid(scan.load(world))
    p = Progress(os.path.basename(d.s.litematic_path))
    for (x, y, z), want in d.cells():
        p.total += 1
        have = w.name(x, y, z)
        if have == "OOB":
            p.oob += 1
            continue
        if _same(want, have, loose_rock):
            p.built += 1
        elif have in AIR or have in ignore_world:
            if have not in AIR:
                p.clear_first[have] += 1
            p.missing_by[want] += 1
            p.missing_regions[(x // 16 * 16, z // 16 * 16)] += 1
            p.remaining_cells.append(((x, y, z), want))
        else:
            p.wrong += 1
            p.wrong_by[(want, have)] += 1
    return p


def remaining(design: str, world: str, out: str, *, loose_rock: bool = True) -> tuple[str, Progress]:
    """Write <out>.litematic + .scan.json holding only the unbuilt cells (same origin as the design)."""
    d = scan.load(design)
    p = progress(design, world, loose_rock=loose_rock)
    names = _names(d.model)
    keep = np.zeros(d.model.ids.shape, bool)
    ox, oy, oz = d.origin
    for (x, y, z), _ in p.remaining_cells:
        keep[y - oy, z - oz, x - ox] = True
    m = d.model.copy()
    m.ids = np.where(keep, m.ids, 0)
    m.tile_entities = [t for t in m.tile_entities if keep[t.value["y"].value, t.value["z"].value, t.value["x"].value]]
    m.compact_palette()
    meta = {**d.meta, "remaining_of": os.path.basename(d.litematic_path), "world": os.path.basename(world),
            "built_pct": round(p.pct, 1), "non_air_blocks": int((m.ids > 0).sum())}
    side = scan.save_pair(out, m, meta, name=os.path.splitext(os.path.basename(out))[0])
    return side, p


# ------------------------------------------------------------------ diff

def diff(a: str, b: str) -> dict:
    """What changed from capture a to capture b (b newer). Only where both scans have data."""
    A = Grid(scan.load(a)); B = Grid(scan.load(b))
    added, removed, swapped, regions = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    x0, x1 = max(A.ox, B.ox), min(A.ox + A.sx, B.ox + B.sx)
    y0, y1 = max(A.oy, B.oy), min(A.oy + A.sy, B.oy + B.sy)
    z0, z1 = max(A.oz, B.oz), min(A.oz + A.sz, B.oz + B.sz)
    na = A.names[A.ids[y0 - A.oy:y1 - A.oy, z0 - A.oz:z1 - A.oz, x0 - A.ox:x1 - A.ox]]
    nb = B.names[B.ids[y0 - B.oy:y1 - B.oy, z0 - B.oz:z1 - B.oz, x0 - B.ox:x1 - B.ox]]
    ch = na != nb
    for (y, z, x) in np.argwhere(ch):
        wa, wb = str(na[y, z, x]), str(nb[y, z, x])
        regions[(int((x + x0) // 16 * 16), int((z + z0) // 16 * 16))] += 1
        if wa in AIR:
            added[wb] += 1
        elif wb in AIR:
            removed[wa] += 1
        else:
            swapped[(wa, wb)] += 1
    return {"changed": int(ch.sum()), "added": added, "removed": removed, "swapped": swapped, "regions": regions,
            "box": ((x0, y0, z0), (x1 - 1, y1 - 1, z1 - 1))}


def diff_report(d: dict, top: int = 10) -> str:
    (x0, y0, z0), (x1, y1, z1) = d["box"]
    lines = [f"compared box x {x0}..{x1} y {y0}..{y1} z {z0}..{z1}: {d['changed']} cells changed",
             "added:   " + ", ".join(f"{k}:{v}" for k, v in d["added"].most_common(top)),
             "removed: " + ", ".join(f"{k}:{v}" for k, v in d["removed"].most_common(top)),
             "swapped: " + ", ".join(f"{a}->{b}:{v}" for (a, b), v in d["swapped"].most_common(top)),
             "regions: " + ", ".join(f"({x},{z}):{v}" for (x, z), v in d["regions"].most_common(top))]
    return "\n".join(lines)


# ------------------------------------------------------------------ merge

def merge_scans(paths: list[str], out: str) -> str:
    """Union of captures. Ordered oldest -> newest by 'created'; a newer scan is authoritative (air included)
    for the chunks it loaded; older scans only fill chunks the newer ones did not load."""
    scans = sorted((scan.load(p) for p in paths), key=lambda s: s.meta.get("created", ""))
    box = _union_box(scans)
    (x0, y0, z0), (x1, y1, z1) = box
    ids = np.zeros((y1 - y0 + 1, z1 - z0 + 1, x1 - x0 + 1), np.int32)
    pal: list = [scans[0].model.palette[0]]
    key_index = {}
    claimed = np.zeros((z1 - z0 + 1, x1 - x0 + 1), bool)          # columns already owned by a newer scan
    chunks_all = set()
    for s in reversed(scans):                                       # newest first
        g = Grid(s)
        own = np.zeros_like(claimed)
        for cx, cz in s.meta.get("chunks_included", []):
            own[max(0, cz * 16 - z0):cz * 16 + 16 - z0, max(0, cx * 16 - x0):cx * 16 + 16 - x0] = True
            chunks_all.add((cx, cz))
        own &= ~claimed
        # restrict to the scan's own box footprint
        foot = np.zeros_like(own); foot[g.oz - z0:g.oz - z0 + g.sz, g.ox - x0:g.ox - x0 + g.sx] = True
        own &= foot
        _paste_columns(ids, pal, key_index, g, own, (x0, y0, z0))
        claimed |= own
    m = schem.Model(ids, pal)
    m.compact_palette()
    meta = {**scans[-1].meta, "origin": {"x": x0, "y": y0, "z": z0}, "size": {"x": ids.shape[2], "y": ids.shape[0], "z": ids.shape[1]},
            "merged_from": [os.path.basename(s.litematic_path) for s in scans], "chunks_included": sorted(list(c) for c in chunks_all),
            "non_air_blocks": int((ids > 0).sum())}
    return scan.save_pair(out, m, meta, name=os.path.splitext(os.path.basename(out))[0])


def _union_box(scans):
    xs = [s.origin[0] for s in scans] + [s.origin[0] + s.model.ids.shape[2] - 1 for s in scans]
    ys = [s.origin[1] for s in scans] + [s.origin[1] + s.model.ids.shape[0] - 1 for s in scans]
    zs = [s.origin[2] for s in scans] + [s.origin[2] + s.model.ids.shape[1] - 1 for s in scans]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _paste_columns(ids, pal, key_index, g: Grid, own: np.ndarray, origin):
    """Copy every column of g where own[z,x] is set (air included), re-indexing its palette."""
    from .nbt import state_key
    x0, y0, z0 = origin
    remap = {}
    for i, tag in enumerate(g.s.model.palette):
        k = state_key(tag)
        if k not in key_index:
            key_index[k] = len(pal); pal.append(tag)
        remap[i] = key_index[k]
    lut = np.array([remap[i] for i in range(len(g.s.model.palette))], np.int32)
    zs, xs = np.where(own)
    for z, x in zip(zs, xs):
        gz, gx = z + z0 - g.oz, x + x0 - g.ox
        col = lut[g.ids[:, gz, gx]]
        ids[g.oy - y0:g.oy - y0 + g.sy, z, x] = col


# ------------------------------------------------------------------ shop

def load_storage(schem_dir: str | None = None, boxed: bool = True) -> collections.Counter:
    """What chunkscan has seen inside your containers: {item: count} from schematics/storage.json.

    `boxed` counts what is inside SHULKER BOXES that are inside those containers, which the mod
    records separately in `inBoxes`. The build loop keeps the two apart on purpose - a boxed block
    is not placeable until you set the box down - but for "do I own enough to make this" a boxed
    block is owned, and bulk storage on this island IS boxes in chests. Pass False for the
    placeable-right-now question.
    """
    path = os.path.join(schem_dir or load_profile()["schem_dir"], "storage.json")
    have = collections.Counter()
    if not os.path.exists(path):
        return have
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for c in data.get("containers", []):
        for item, n in (c.get("items") or {}).items():
            have[item.split(":")[-1]] += int(n)
        if boxed:
            for item, n in (c.get("inBoxes") or {}).items():
                have[item.split(":")[-1]] += int(n)
    return have


def storage_report(schem_dir: str | None = None) -> str:
    path = os.path.join(schem_dir or load_profile()["schem_dir"], "storage.json")
    if not os.path.exists(path):
        return "no storage.json yet - open some containers in game with chunkscan 0.3 running"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("containers", [])
    lines = [f"{len(rows)} containers indexed"]
    for c in sorted(rows, key=lambda c: -sum((c.get("items") or {}).values()))[:15]:
        items = c.get("items") or {}
        top = ", ".join(f"{k.split(':')[-1]}:{v}" for k, v in sorted(items.items(), key=lambda kv: -kv[1])[:4])
        name = c.get("label") or c.get("zone") or c.get("block")
        lines.append(f"  #{c['id']:<3} {name:<18} {c['x']} {c['y']} {c['z']}  {sum(items.values()):5d} items  {top}")
    return "\n".join(lines)


def load_prices(path: str = "prices.yaml") -> dict:
    """Optional {block_name: coins} table (your server's shop). Absent -> tiers only."""
    if not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return {str(k).split(":")[-1]: float(v) for k, v in (yaml.safe_load(f) or {}).items()}


def shop(designs: list[str], world: str | None = None, prices: dict | None = None, have: collections.Counter | None = None) -> str:
    prices = load_prices() if prices is None else prices
    need = collections.Counter()
    for dpath in designs:
        if world:
            for _, n in progress(dpath, world).remaining_cells:
                need[n] += 1
        else:
            for _, n in Grid(scan.load(dpath)).cells():
                need[n] += 1
    lines = [f"{'block':26s} {'count':>6s} {'stacks':>7s} {'shulk':>6s}  tier" + ("      have  short" if have is not None else "") + ("   coins" if prices else "")]
    total_coins = 0.0
    for name, n in need.most_common():
        tier = palette.tier("minecraft:" + name)
        cost = prices.get(name)
        line = f"{name:26s} {n:6d} {n / 64:7.1f} {n / 1728:6.2f}  {tier}"
        if have is not None:
            got = have.get(name, 0)
            line += f"  {got:8d}  {max(0, n - got):5d}"
        if prices:
            line += f"   {n * cost:8.0f}" if cost is not None else "        ?"
            total_coins += n * (cost or 0)
        lines.append(line)
    total = sum(need.values())
    by_tier = collections.Counter()
    for name, n in need.items():
        by_tier[palette.tier("minecraft:" + name)] += n
    if have is not None:
        short = sum(max(0, n - have.get(k, 0)) for k, n in need.items())
        lines.append(f"in your indexed containers: {sum(min(n, have.get(k, 0)) for k, n in need.items())} of {total}; still short {short}")
    lines.append(f"total {total} blocks = {total / 64:.0f} stacks = {total / 1728:.1f} shulkers; "
                 + ", ".join(f"{k} {v}" for k, v in by_tier.most_common())
                 + (f"; ~{total_coins:.0f} coins (priced items only)" if prices else ""))
    return "\n".join(lines)


# ------------------------------------------------------------------ buildability

def floating_clusters(design: str, context: list[str]) -> tuple[int, int, list]:
    """6-connected clusters of the design that touch nothing in the context captures (need temporary scaffold)."""
    d = scan.load(design)
    ctxs = [Grid(scan.load(c)) for c in context]
    labels, sizes = morph.components(d.model.ids > 0, conn=6)
    ox, oy, oz = d.origin
    NB = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    n_cl = n_cells = 0; samples = []
    for i, sz_ in enumerate(sizes, 1):
        comp = np.argwhere(labels == i)
        touch = any(g.name(x + ox + dx, y + oy + dy, z + oz + dz) not in ("air", "OOB", "vine")
                    for y, z, x in comp for g in ctxs for dx, dy, dz in NB)
        if not touch:
            n_cl += 1; n_cells += int(sz_)
            y, z, x = comp[0]; samples.append((int(x + ox), int(y + oy), int(z + oz)))
    return n_cl, n_cells, samples[:5]


# ------------------------------------------------------------------ sync

def write_tracked(cfg: dict, schem_dir: str) -> list[str]:
    """Tell the MOD which designs are live work.

    `sync.yaml` is the only place that knows: `progress:` is the list Jack actually tracks, against
    61 designs sitting in the schematics folder. The mod could not see it - it has gson and no YAML
    parser, and sync.yaml lives in the repo rather than beside the schematics - so bare
    `/cscan place` placed ALL of them, and `plan` could only ever be asked about one design at a
    time.

    This is the same one-source route as `chunkscan_rules.json`, with one difference that matters:
    those rules are baked into the JAR because they change when the GAME does, and this list changes
    whenever Jack edits a yaml file. So it is written beside the schematics and read at runtime.
    """
    names = []
    for d in cfg.get("progress", []) or []:
        base = os.path.basename(str(d))
        for ext in (".litematic", ".scan.json", ".work.json"):
            if base.endswith(ext):
                base = base[: -len(ext)]
                break
        if base and base not in names:
            names.append(base)
    out = {"_comment": "GENERATED by `python -m mcbuild sync` from sync.yaml's `progress:` list. "
                       "The mod reads this so `/cscan place` and `/cscan plan` mean the designs you "
                       "actually track, not everything in the folder.",
           "tracked": names,
           "written": _dt.datetime.now().isoformat(timespec="seconds")}
    path = os.path.join(schem_dir, "designs.json")
    os.makedirs(schem_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return names


def sync(cfg_path: str = "sync.yaml", verbose: bool = True) -> str:
    """After a fresh /cscan: cut the latest scan -> regenerate remaining-work designs -> progress + shop -> learn."""
    import subprocess, sys, yaml
    from . import learn as learn_mod
    prof = load_profile()
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    scan_name = cfg.get("scan", prof["scan"]); cut = cfg.get("cut", prof["cut"]); world_out = cfg.get("world_out", prof["world_out"])
    lines = []
    s = scan.load(scan_name)
    m, meta = scan.cut(s, *cut)
    scan.save_pair(world_out, m, meta, name=os.path.splitext(os.path.basename(world_out))[0])
    lines.append(f"cut {scan_name} ({s.meta.get('created')}) -> {world_out}")
    for c in cfg.get("regen", []):
        r = subprocess.run([sys.executable, "-m", "mcbuild", "gen", c, "--ship", "--no-render"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = [l for l in r.stdout.splitlines() if l.startswith(("in context", "paste origin", "shipped", "buildability"))]
        lines.append(f"regen {c}: " + " | ".join(tail) if r.returncode == 0 else f"regen {c}: FAILED\n{r.stdout[-800:]}{r.stderr[-800:]}")
    # PROGRESS IS MEASURED AGAINST THE FULL DEPTH, NOT THE PLATE CUT. `world_out` is the
    # Y150+ box the plate designs verify against; reporting a below-island design against it
    # counts every cell under Y150 as "outside the scan box (unknown)" and calls it unbuilt.
    # It read every lowland design as 0% for the whole life of that scene - a stair 74% built
    # reported 6/2139 - and the velocity slope was out by about four times. `full_out` names
    # a capture that holds the whole island; without one this falls back to the old behaviour.
    full_out = cfg.get("full_out")
    prog_world = full_out if full_out and os.path.exists(full_out) else world_out
    if prog_world != world_out:
        lines.append(f"progress measured against {prog_world} (full depth)")
    rows = {}
    for d in cfg.get("progress", []):
        pr = progress(d, prog_world)
        rows[os.path.basename(d)] = (pr.built, pr.total)
        lines.append(pr.report(top=8))
    if cfg.get("progress"):
        lines.append(shop(cfg["progress"], prog_world))
        from . import history as history_mod
        history_mod.record(rows)                       # one row per sync: gives progress a slope
        lines.append(history_mod.report())
    if cfg.get("learn", True):
        lines.append(learn_mod.learn([world_out]).splitlines()[0])
    tracked = write_tracked(cfg, prof["schem_dir"])
    lines.append(f"tracked {len(tracked)} design(s) -> designs.json (the mod reads this for "
                 f"`/cscan place` and `/cscan plan`)")
    # THE SCAN IS THE THING THAT CANNOT BE REGENERATED, and this is the moment a new one exists.
    # Backing up on any other schedule backs up the world as it was before the change that made
    # the run worth doing. A failure here is REPORTED and never fatal: a sync that dies because
    # the backup drive is full has lost the sync as well as the backup.
    if cfg.get("backup", True):
        from . import backup as backup_mod
        try:
            man = backup_mod.run(keep=cfg.get("backup_keep", backup_mod.KEEP))
            n = sum(p.get("files", 0) for p in man["parts"].values()
                    if isinstance(p, dict) and isinstance(p.get("files"), int))
            lines.append(f"backup {man['stamp']}: {n} files verified -> {man['dir']}"
                         + (f" (pruned {len(man['pruned'])})" if man.get("pruned") else ""))
        except Exception as e:                              # noqa: BLE001
            lines.append(f"BACKUP FAILED: {e}")
    return "\n".join(lines)


def adopt(design: str, world: str, *, loose_rock: bool = True) -> str:
    """Rewrite a design so the blocks you actually placed become the design.

    Every cell where the world holds something DIFFERENT from the design takes the world's block.
    Cells the world has not built yet are left alone, so remaining-work reporting still works - this
    only silences deviations you have already decided you are happy with.
    """
    d = scan.load(design)
    wsc = scan.load(world)
    g = Grid(wsc)
    dn = _names(d.model)
    changed = collections.Counter()
    ys, zs, xs = np.where(d.model.ids > 0)
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        X, Y, Z = x + d.origin[0], y + d.origin[1], z + d.origin[2]
        if not g.inside(X, Y, Z):
            continue
        have = g.name(X, Y, Z)
        want = dn[d.model.ids[y, z, x]]
        if have in AIR or have == want or _same(want, have, loose_rock):
            continue
        idx = d.model.ensure_state(have, **wsc.model.props_at(X - wsc.origin[0], Y - wsc.origin[1],
                                                             Z - wsc.origin[2]))
        d.model.ids[y, z, x] = idx
        changed[f"{want} -> {have}"] += 1
    if not changed:
        return f"{os.path.basename(design)}: nothing to adopt - no deviations"
    d.model.compact_palette()
    schem.save(d.litematic_path, d.model, name=d.meta.get("name", "design"))
    total = sum(changed.values())
    top = ", ".join(f"{k} x{v}" for k, v in changed.most_common(6))
    return f"{os.path.basename(design)}: adopted {total} cell(s) - {top}"


# ------------------------------------------------------------------ design card

def card(design: str, out: str, world: str | None = None) -> str:
    """One PNG for chat: contact sheet + name/origin/size/BOM in stacks (+ progress if a world scan is given)."""
    from PIL import Image, ImageDraw
    from . import render
    s = scan.load(design)
    sheet = render.contact_sheet(s.model, views=("face", "side", "top"), scale=6)
    bom = collections.Counter(n for _, n in Grid(s).cells())
    ox, oy, oz = s.origin; sx, sy, sz = s.size
    text = [s.meta.get("name") or os.path.basename(s.litematic_path), f"paste origin  {ox} {oy} {oz}",
            f"size {sx}x{sy}x{sz}   blocks {sum(bom.values())}"]
    if world:
        p = progress(design, world); text.append(f"built {p.pct:.0f}%  left {sum(p.missing_by.values())}")
    text.append("")
    text += [f"{n:22s} {v:5d}  ({v / 64:.1f} st)" for n, v in bom.most_common(14)]
    W = max(sheet.width, 420); H = sheet.height + 18 * len(text) + 24
    img = Image.new("RGB", (W, H), (24, 26, 32)); img.paste(sheet, (0, 0)); d = ImageDraw.Draw(img)
    for i, t in enumerate(text):
        d.text((10, sheet.height + 8 + 18 * i), t, fill=(235, 235, 235))
    img.save(out)
    return out


# ------------------------------------------------------------------ Litematica placements

def litematica_world_file(server: str, dim: str, game_dir: str) -> str:
    return os.path.join(game_dir, "config", "litematica", f"litematica_{server}_dim_{dim.replace(':', '_')}.json")


def place(designs: list[str], *, server: str | None = None, dim: str | None = None, game_dir: str | None = None,
          schem_dir: str | None = None, enabled: bool = True, dry: bool = False) -> str:
    """Upsert one placement per design (matched by name) into Litematica's per-world file.
    Run with the game CLOSED or before joining that world: Litematica overwrites the file on exit."""
    prof = load_profile()
    server = server or prof["server"]; dim = dim or prof["dim"]; game_dir = game_dir or prof["game_dir"]; schem_dir = schem_dir or prof["schem_dir"]
    path = litematica_world_file(server, dim, game_dir)
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    pl = data.setdefault("placements", {}).setdefault("placements", [])
    out = []
    for dpath in designs:
        s = scan.load(dpath)
        name = s.meta.get("name") or os.path.splitext(os.path.basename(s.litematic_path))[0]
        target = os.path.join(schem_dir, os.path.basename(s.litematic_path))
        entry = {"schematic": os.path.normpath(target).replace("/", "\\"), "name": name, "origin": list(s.origin),
                 "rotation": "NONE", "mirror": "NONE", "ignore_entities": False, "enabled": bool(enabled),
                 "enable_render": True, "render_enclosing_box": False, "locked": True, "locked_coords": 7, "bb_color": 0x00FF7F}
        idx = next((i for i, e in enumerate(pl) if e.get("name") == name), None)
        if idx is None:
            pl.append(entry); out.append(f"+ {name} @ {s.origin}")
        else:
            pl[idx] = {**pl[idx], **entry}; out.append(f"~ {name} @ {s.origin}")
    if not dry:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    return f"{'(dry) ' if dry else ''}{path}\n" + "\n".join(out) + "\nNOTE: do this with the game closed; Litematica rewrites the file when you leave the world."
