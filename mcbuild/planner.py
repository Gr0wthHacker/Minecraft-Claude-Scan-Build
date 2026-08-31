"""Brief in, PLAN out — and nothing is built until a human says yes.

    python -m mcbuild plan "redstone casino" --world out/island_now.litematic
    python -m mcbuild plan --show casino
    python -m mcbuild plan --approve casino          # the gate. Nothing builds before this.
    python -m mcbuild plan --emit casino             # writes the configs

Jack's choice was **propose -> approve -> build**, and that is the whole architecture here rather
than a setting. The planner proposes; the deterministic pipeline verifies; a human approves; only
then does anything reach the world.

**THE PLANNER DOES NOT UNDERSTAND ENGLISH AND DOES NOT PRETEND TO.** A brief selects a THEME out
of a catalogue and sets its parameters. That is an honest split: the open-ended half (what should a
casino contain, how big, in what style) is a judgement, and the closed half (does it fit, does it
collide, can it be afforded, do the circuits work) is measurement. Wiring an LLM to the first half
is a one-line change - it emits a theme name and a parameter dict - and it still cannot skip the
second half, which is the point. A model that could approve its own plan would be a model that
could build a spotted table at island scale.

What a plan carries, and every one of these is a refusal waiting to happen:

    sited        every module on real ground, inside the plot, not overlapping each other
    costed       through `recipes` against your actual containers, so "can I afford it" is answered
    verified     circuits inspected; a module whose contract cannot be met is REPORTED, not placed
    ordered      dependencies first, using the same `after` the build order already understands
    unverified   what the plan knows it cannot promise, carried forward in writing
"""
from __future__ import annotations

import collections
import datetime as _dt
import json
import os
import pathlib

import numpy as np

from . import plot as plot_mod, scan as scan_mod

PLANS = pathlib.Path("out/plans")

# ---------------------------------------------------------------------- the catalogue
#
# A THEME is a list of modules with a footprint and a generator. Deliberately data rather than
# code: adding "arcade" or "market" should not require touching the planner, and the thing an LLM
# would emit is exactly one of these dicts.
# THE REFERENCE CASINO DOES NOT FIT ON A SKYBLOCK PLOT. It is 135 x 105 and a plot is 99 x 99 -
# 36 over on X and 6 over on Z. Jack: *"it cant be bigger than 99x99 ... but we can go vertically
# higher and much lower"*, and that is the whole shape of the answer: the same volume is 1.45
# floors when it is STACKED, and Y-64 to Y320 is 384 courses of room. So a theme carries a
# `floors` plan rather than sprawling, and every module's footprint is checked against the plot
# before anything is generated.
MAX_FOOTPRINT = 99

THEMES = {
    "casino": {
        "blurb": "a redstone casino: four verified games over two floors, inside a 99x99 plot",
        # TWO FLOORS, BECAUSE THE FOOTPRINT IS THE ONLY THING THAT IS SCARCE. The reference casino
        # is 135x105 and does not fit; the vertical does not run out until Y320. Games below, where
        # a player walks between them; marquee, prize wall and bank above.
        "floors": [
            {"name": "Gaming Floor", "y": 0},
            {"name": "Mezzanine", "y": 12},
        ],
        # FOUR GAMES FROM TWO VERIFIED TOPOLOGIES, at two sets of odds. `high_roller` reads the
        # roll off a bar; `double_or_none` pays only on a win. Both are asserted by simulation at
        # 2 and 3 outcomes - the only mixes with a measured uniform distribution.
        "modules": [
            {"name": "High Roller", "gen": "casino", "kind": "high_roller",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 6, "floor": 0},
            {"name": "Coin Toss", "gen": "casino", "kind": "high_roller",
             "size": [9, 8, 8], "params": {"outcomes": 2, "pit": 2}, "count": 5, "floor": 0},
            {"name": "One In Three", "gen": "casino", "kind": "double_or_none",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 6, "floor": 0},
            {"name": "Even Money", "gen": "casino", "kind": "double_or_none",
             "size": [9, 8, 8], "params": {"outcomes": 2, "pit": 2}, "count": 5, "floor": 0},
            {"name": "Casino Marquee", "gen": "casino", "kind": "marquee",
             "size": [18, 5, 4], "params": {"length": 16}, "count": 4, "floor": 1},
            {"name": "Prize Wall", "gen": "casino", "kind": "prize_wall",
             "size": [4, 5, 12], "params": {"lanes": 5}, "count": 4, "floor": 1},
            {"name": "House Bank", "gen": "casino", "kind": "counter",
             "size": [4, 4, 8], "params": {"lanes": 6}, "count": 3, "floor": 1},
        ],
    },
}


class Plan:
    def __init__(self, name: str, theme: str, brief: str = ""):
        self.name = name
        self.theme = theme
        self.brief = brief
        self.created = _dt.datetime.now().isoformat(timespec="seconds")
        self.approved = False
        self.approved_at = ""
        self.island = ""
        self.modules: list = []
        self.notes: list = []
        self.unverified: list = []

    # ------------------------------------------------------------------ io

    def path(self) -> pathlib.Path:
        return PLANS / f"{self.name}.json"

    def save(self) -> str:
        PLANS.mkdir(parents=True, exist_ok=True)
        self.path().write_text(json.dumps(self.__dict__, indent=1), encoding="utf-8")
        return str(self.path())

    @classmethod
    def load(cls, name: str) -> "Plan":
        p = PLANS / f"{name}.json"
        if not p.exists():
            raise FileNotFoundError(f"no plan called {name} (looked in {PLANS})")
        d = json.loads(p.read_text(encoding="utf-8"))
        pl = cls(d["name"], d["theme"], d.get("brief", ""))
        pl.__dict__.update(d)
        return pl

    # ------------------------------------------------------------------ report

    def report(self) -> str:
        out = [f"PLAN {self.name}  ({self.theme})  {'APPROVED' if self.approved else 'NOT APPROVED'}",
               f"  brief: {self.brief or '-'}"]
        if not self.modules:
            out.append("  nothing sited - the ground could not take it")
        for m in self.modules:
            at = m["at"]
            out.append(f"  {m['name']:22s} {m['kind']:11s} at {at[0]} {at[1]} {at[2]}  "
                       f"{m['size'][0]}x{m['size'][1]}x{m['size'][2]}"
                       + (f"  {m['blocks']} blocks" if m.get("blocks") else ""))
            if m.get("contract"):
                out.append(f"      contract: {m['contract']}")
            for f in m.get("circuit", [])[:3]:
                out.append(f"      CIRCUIT: {f}")
        if self.modules:
            xs = [m["at"][0] for m in self.modules] + [m["at"][0] + m["size"][0] for m in self.modules]
            zs = [m["at"][2] for m in self.modules] + [m["at"][2] + m["size"][2] for m in self.modules]
            area = sum(m["size"][0] * m["size"][2] for m in self.modules)
            out.append(f"  spread: X {min(xs)}..{max(xs)}  Z {min(zs)}..{max(zs)}  "
                       f"({area} of {99 * 99} plot cells used by module footprints, "
                       f"{100 * area / (99 * 99):.0f}%)")
        for n in self.notes:
            out.append(f"  note: {n}")
        for u in self.unverified:
            out.append(f"  NOT VERIFIED: {u}")
        out.append("  " + ("build it: python -m mcbuild plan --emit " + self.name
                           if self.approved else
                           "approve with: python -m mcbuild plan --approve " + self.name))
        return "\n".join(out)


# ---------------------------------------------------------------------- siting

def _surface(sc) -> tuple:
    """(height map, name grid) of the capture's topmost solid cell per column, in world coords."""
    m = sc.model
    names = np.array([n.split(":")[-1] for n in m.names])
    solid = m.solid()
    sy, sz, sx = solid.shape
    ox, oy, oz = sc.origin
    # topmost solid per column
    idx = np.where(solid.any(axis=0), solid.shape[0] - 1 - np.argmax(solid[::-1], axis=0), -1)
    return idx, oy, (ox, oz), names, m.ids


def ground_band(sc, tolerance: int = 6) -> tuple:
    """The island's actual GROUND level, measured as the modal surface height.

    THE TOPMOST SOLID CELL IS NOT THE GROUND. On this island the highest block in most columns is
    the sky bird at Y268, so a naive height map sites a casino on a sculpture eighty blocks up -
    which is exactly what the first run of this planner did. That is the night pass's own lesson
    ("the lowest-standable classifier struck a THIRD time") arriving from the opposite direction.

    The mode is the honest statistic here: a plate 2,000 columns wide dominates any number of
    towers, sculptures and floating rocks, and it needs no hand-written Y.
    """
    idx, oy, _, _, _ = _surface(sc)
    vals = idx[idx >= 0]
    if not len(vals):
        return None
    counts = np.bincount(vals.astype(int))
    top = int(counts.argmax()) + oy
    return (top - tolerance, top + tolerance)


def pads(sc, size, plot=None, roll: int = 1, limit: int = 200, y_range=None) -> list:
    """Every flat-enough patch of ground the given footprint fits on.

    FLAT ENOUGH IS MEASURED, NOT ASSUMED. `roll` is how many courses the ground may vary across
    the footprint; this project has learned twice that a build sited on rolling terrain either
    floats on the low side or buries its feet on the high one.

    Returns [(x, y, z, roll)] with y the course the module stands ON.
    """
    idx, oy, (ox, oz), names, ids = _surface(sc)
    w, h, d = (int(v) for v in size)
    out = []
    H, W = idx.shape                    # (z, x)
    for zi in range(0, H - d):
        for xi in range(0, W - w):
            win = idx[zi:zi + d, xi:xi + w]
            if (win < 0).any():
                continue
            spread = int(win.max() - win.min())
            if spread > roll:
                continue
            top = int(win.max()) + oy + 1
            if y_range is not None and not (y_range[0] <= top <= y_range[1]):
                continue
            x, z = xi + ox, zi + oz
            # BOTH CORNERS, because a footprint is a box: checking only its origin sites a
            # module that starts inside the plot and finishes over the line, which is exactly how
            # the Island Run put 120 cells past the edge.
            if plot is not None and not (plot.contains(x, z) and plot.contains(x + w, z + d)):
                continue
            out.append((x, int(win.max()) + oy + 1, z, spread))
            if len(out) >= limit:
                return out
    return out


def bays(plot, size, spacing: int = 3, margin: int = 4) -> list:
    """Lay the plot out as a GRID of bays, the way a floor is actually planned.

    **FIRST FIT DOES NOT USE A PLOT, IT FILLS A STRIP.** `pads` returns the first 200 flat spots it
    finds, which on a 99x99 plot is one row along the near edge - so the first few modules took
    them all and every module after that reported NO SITE beside 94% empty ground. The plan used
    **6%** of the plot and looked like a queue rather than a casino.

    A grid is also simply what the thing IS: bays of equal size, aisles between them, a margin off
    the boundary so nothing is built against the void. Returned in a spiral from the centre, so a
    half-full plan is a cluster around the middle rather than a line down one side.
    """
    x0, z0, x1, z1 = plot.bounds
    w, _h, d = (int(v) for v in size)
    stride_x, stride_z = w + spacing, d + spacing
    cols = max(1, ((x1 - x0 + 1) - 2 * margin) // stride_x)
    rows = max(1, ((z1 - z0 + 1) - 2 * margin) // stride_z)
    # centre the grid in the plot rather than pinning it to a corner
    used_x, used_z = cols * stride_x - spacing, rows * stride_z - spacing
    ox = x0 + ((x1 - x0 + 1) - used_x) // 2
    oz = z0 + ((z1 - z0 + 1) - used_z) // 2
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append((ox + c * stride_x, oz + r * stride_z))
    mid_c, mid_r = (cols - 1) / 2, (rows - 1) / 2
    out.sort(key=lambda t: ((t[0] - (ox + mid_c * stride_x)) ** 2
                            + (t[1] - (oz + mid_r * stride_z)) ** 2))
    return out


def _clear(taken: list, x, y, z, size) -> bool:
    """Does this footprint miss everything already placed. Boxes, because a module is a box."""
    w, h, d = (int(v) for v in size)
    for (ax, ay, az, aw, ah, ad) in taken:
        if (x < ax + aw and ax < x + w and z < az + ad and az < z + d
                and y < ay + ah and ay < y + h):
            return False
    return True


# ---------------------------------------------------------------------- planning

def make(brief: str, world: str, name: str | None = None, theme: str | None = None,
         plot_from: str | None = None, spacing: int = 2, island: str | None = None,
         plane: int | None = None) -> Plan:
    """Site a theme's modules on real ground and cost them. Nothing is generated yet.

    `island` names an entry in the island registry, so a plan can target a DIFFERENT island from
    the one this tooling grew up on - which is the whole point of a fresh plot for the casino. The
    plot then comes from that registry entry rather than from the capture's own bedrock, so a
    capture that happens to include two islands cannot pick the wrong square.
    """
    theme = theme or _theme_for(brief)
    if theme not in THEMES:
        raise ValueError(f"no theme {theme!r}; have {sorted(THEMES)}")
    spec = THEMES[theme]
    pl = Plan(name or theme, theme, brief)

    sc = scan_mod.load(world)
    try:
        if island:
            from . import islands as islands_mod
            pl_plot = islands_mod.plot_of(island)
            if pl_plot is None:
                raise ValueError(f"no island called {island!r} - "
                                 f"python -m mcbuild islands --add {island} --from {world}")
            pl.island = island
            pl.notes.append(f"island {island} (owner {islands_mod.owner(island) or '-'}): {pl_plot}")
        else:
            pl_plot = plot_mod.find(plot_from or world)
            pl.notes.append(f"plot {pl_plot}")
    except Exception as e:                                       # noqa: BLE001
        pl_plot = None
        # NOT FOUND IS NOT INSIDE. A boundary guard that silently passes everything is the failure
        # it exists to prevent, so the plan says so rather than quietly siting off the island.
        pl.notes.append(f"PLOT UNKNOWN ({e}) - nothing is boundary-checked")

    # A SKYBLOCK PLOT HAS NO GROUND, and requiring some is how a correct planner refuses a
    # perfectly buildable island. A fresh island is a 12x12 starter pad in 99x99 of void: every
    # pad search returns nothing and every module reports NO SITE, which reads as "the terrain is
    # awkward" when the truth is that there is no terrain at all.
    #
    # `plane` is the answer, and it is a DECLARATION rather than a discovery: you say which course
    # the gaming floor stands on and the modules are laid out on the grid at that height. Every
    # other guard still applies - the plot boundary, the overlap between modules, the vertical
    # stacking - because those are the ones that are about correctness rather than about terrain.
    #
    # Each module carries its own floor and its own pit floor, so nothing hangs unsupported once
    # it is built; what a plane cannot promise is something to place the FIRST block against, and
    # the plan says so rather than letting the printer discover it.
    band = None if plane is not None else ground_band(sc)
    if plane is not None:
        pl.notes.append(f"sited on a DECLARED BUILD PLANE at Y{plane} - this plot has no ground, "
                        f"so the layout is the grid and each module carries its own floor")
        pl.notes.append("the first module has nothing to place against: stand a starter platform "
                        "under the gaming floor, or build outward from the island's own pad")
    if band:
        pl.notes.append(f"ground band Y{band[0]}..{band[1]} (modal surface) - "
                        f"nothing is sited on a rooftop or a sculpture")
    # A MODULE BIGGER THAN THE PLOT CAN NEVER BE SITED, and finding that out as "NO SITE" after a
    # full pad search reads like the ground being awkward rather than the design being impossible.
    for mspec in spec["modules"]:
        w_, _h, d_ = mspec["size"]
        if w_ > MAX_FOOTPRINT or d_ > MAX_FOOTPRINT:
            pl.notes.append(f"{mspec['name']}: {w_}x{d_} is larger than the {MAX_FOOTPRINT}x"
                            f"{MAX_FOOTPRINT} plot - it cannot fit at any position")
    floors = spec.get("floors") or [{"name": "Ground", "y": 0}]
    if len(floors) > 1:
        pl.notes.append(f"stacked over {len(floors)} floor(s): "
                        + ", ".join(f"{f['name']} at +{f['y']}" for f in floors)
                        + " - the plot is 99x99 but the vertical is free")
    taken: list = []
    for mspec in spec["modules"]:
        for i in range(int(mspec.get("count", 1))):
            size = [mspec["size"][0] + spacing, mspec["size"][1], mspec["size"][2] + spacing]
            spot = None
            # THE GRID FIRST, so the plot is used rather than a strip of it. Each bay still has to
            # pass the SAME ground test a free-form pad would - flat enough, in the band, free -
            # because a tidy grid over rolling terrain is still a build on rolling terrain.
            if plane is not None and pl_plot is not None:
                for (bx, bz) in bays(pl_plot, size, spacing=3):
                    if _clear(taken, bx, plane, bz, size):
                        spot = (bx, plane, bz, 0)
                        break
            elif pl_plot is not None:
                for (bx, bz) in bays(pl_plot, size, spacing=3):
                    hits = [q for q in pads(sc, size, pl_plot, y_range=band, limit=4000)
                            if q[0] == bx and q[2] == bz]
                    if hits and _clear(taken, hits[0][0], hits[0][1], hits[0][2], size):
                        spot = hits[0]
                        break
            if spot is None and plane is None:
                for (x, y, z, roll) in pads(sc, size, pl_plot, y_range=band, limit=4000):
                    if _clear(taken, x, y, z, size):
                        spot = (x, y, z, roll)
                        break
            lift = floors[min(int(mspec.get("floor", 0)), len(floors) - 1)]["y"]
            label = mspec["name"] + (f" {i + 1}" if int(mspec.get("count", 1)) > 1 else "")
            if spot is None:
                why = ("no free bay left on the plane" if plane is not None
                       else "nothing flat enough and free")
                pl.notes.append(f"{label}: NO SITE - {why} at {size[0]}x{size[2]}")
                continue
            x, y, z, roll = spot
            taken.append((x, y, z, size[0], size[1], size[2]))
            pl.modules.append({
                "name": label, "gen": mspec["gen"], "kind": mspec["kind"],
                "at": [x, y + lift, z], "size": mspec["size"], "roll": roll,
                "floor": floors[min(int(mspec.get("floor", 0)), len(floors) - 1)]["name"],
                "params": dict(mspec.get("params", {})),
                "world": world,
            })
    return pl


def _theme_for(brief: str) -> str:
    """Pick a theme from a brief, by keyword.

    DELIBERATELY DUMB, AND SAYS SO. This is the open-ended half of the problem and a keyword match
    is an honest placeholder for a judgement; what it must never do is guess silently, so an
    unmatched brief raises rather than defaulting to the only theme in the catalogue.
    """
    b = (brief or "").lower()
    for theme, spec in THEMES.items():
        if theme in b:
            return theme
        if any(word in b for word in spec.get("keywords", [])):
            return theme
    raise ValueError(f"no theme matches {brief!r}; have {sorted(THEMES)}. "
                     f"Pass --theme explicitly, or add one to planner.THEMES")


def verify(pl: Plan, quiet: bool = True) -> Plan:
    """Generate every module in memory, inspect its circuits, and cost it.

    THIS RUNS BEFORE APPROVAL, WHICH IS THE ENTIRE POINT. A plan you approve should already know
    whether its machines work, what they cost and whether they fit - approving a list of names is
    approving nothing.
    """
    from . import circuit as circuit_mod, recipes as recipes_mod, coop
    from .gen import GENERATORS

    have = coop.load_storage()
    total = collections.Counter()
    for m in pl.modules:
        gen = GENERATORS.get(m["gen"])
        if gen is None:
            m["circuit"] = [f"unknown generator {m['gen']}"]
            continue
        params = {**m.get("params", {}), "at": m["at"], "kind": m["kind"],
                  "under": m.get("world"), "check": True}
        try:
            canvas = gen.build(params, [])
        except Exception as e:                                   # noqa: BLE001
            m["circuit"] = [f"BUILD FAILED: {e}"]
            continue
        model = canvas.to_model() if hasattr(canvas, "to_model") else canvas
        m["blocks"] = int((model.ids > 0).sum())
        meta = getattr(canvas, "meta", {}) or {}
        m["contract"] = meta.get("contract", "")
        for u in meta.get("unverified", []) or []:
            if u not in pl.unverified:
                pl.unverified.append(u)
        origin = getattr(canvas, "world_origin", None) or (0, 0, 0)
        if circuit_mod.has_redstone(model):
            m["circuit"] = [f"{k} at {p}: {d}"
                            for k, p, d in circuit_mod.inspect(model, origin)][:8]
        else:
            m["circuit"] = []
        for i, n in zip(*np.unique(model.ids[model.ids > 0], return_counts=True)):
            total[model.names[i].split(":")[-1]] += int(n)

    if total:
        plan_r = recipes_mod.plan(total, have) if recipes_mod.available() else None
        pl.cost = {"blocks": int(sum(total.values())),
                   "materials": len(total),
                   "short": dict(plan_r.short) if plan_r else {},
                   "from_stock": dict(plan_r.used) if plan_r else {}}
    return pl


def approve(name: str) -> Plan:
    pl = Plan.load(name)
    pl.approved = True
    pl.approved_at = _dt.datetime.now().isoformat(timespec="seconds")
    pl.save()
    return pl


def emit(name: str, out_dir: str = "configs") -> list:
    """Write one config per module — and REFUSE if the plan is not approved.

    The gate is here rather than in the CLI so that no other caller can route around it.
    """
    import yaml
    pl = Plan.load(name)
    if not pl.approved:
        raise PermissionError(
            f"plan {name} is not approved. Nothing is emitted until a human says yes: "
            f"python -m mcbuild plan --approve {name}")
    written = []
    prev = None
    for m in pl.modules:
        slug = m["name"].lower().replace(" ", "_")
        cfg = {
            "name": m["name"],
            "gen": m["gen"],
            "params": {**m.get("params", {}), "at": m["at"], "kind": m["kind"],
                       "under": m.get("world")},
            "finish": {"verify_against": m.get("world")},
        }
        # BUILD ORDER, from the same `after` the mod already understands: a module placed later
        # defers to the one before it, so two of them never ask for the same cell twice.
        if prev:
            cfg["finish"]["defer_to"] = [f"out/{prev}.litematic"]
        p = os.path.join(out_dir, f"{slug}.yaml")
        with open(p, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        written.append(p)
        prev = m["name"]
    return written
