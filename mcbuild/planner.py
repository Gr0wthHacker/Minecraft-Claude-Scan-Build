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
        # **ONE FLOOR, BECAUSE A SECOND ONE IS A STRUCTURE AND NOT A NUMBER.**
        #
        # This said two floors and lifted eleven modules to +12 - and nothing ever BUILT a
        # mezzanine: no deck, no railing, no stairs. All eleven hung in open air eleven blocks
        # over the gaming floor, and a component count of the finished casino found exactly that:
        # one building of 15,710 cells and 45 floating fragments.
        #
        # A floor entry is a lift, and a lift is only legitimate when something carries the thing
        # being lifted. Adding a real gallery - deck, balustrade and a flight down - is a fine
        # thing to build and it is a BUILD, so until it exists everything stands on the ground.
        "floors": [
            {"name": "Gaming Floor", "y": 0},
        ],
        # **FOUR DISTINCT MECHANICS, NOT FOUR NAMES FOR TWO.**
        #
        # The previous lineup was measured cell-for-cell and it was two games wearing four names:
        # High Roller vs Coin Toss were 99.2% the same cells and One In Three vs Even Money 97.8%,
        # because `threshold` pays on a MAXIMUM and a maximum is the same game whatever number you
        # put in it. Changing the odds is not changing the game.
        #
        # What separates these four is the QUESTION the player is answering:
        #
        #   High Roller    what did I roll?          bar        reads a level
        #   One In Three   did I roll high enough?   threshold  a maximum
        #   Lucky Two      did I hit the number?     window     an AND-NOT, middle wins, top loses
        #   Duel           did I beat the house?     compare    two rolls, ties to the player
        #   Colour Wheel   where did it land?        decoder    one roll, three pockets, one lit
        #
        # The Wheel is the first with a different SHAPE as well as a different circuit - a sunken
        # round bowl with a rail, read from above - because four verified mechanics in four
        # identical booths are still four identical rooms.
        #
        # **THE ODDS VARIANTS ARE GONE.** "Coin Toss" was High Roller at 2 outcomes and measured
        # 98.7% the same machine; "Even Money" was One In Three and measured 94.6%. Changing a
        # number is not changing a game, and shipping it under a different name over a different
        # door is the thing that made this read as the same room eighteen times.
        #
        # Each is a different circuit asserted by its own simulation, and each states its odds -
        # a house that cannot state its odds does not know them.
        "modules": [
            # **THE BIGGEST MODULE IS SITED FIRST.** `bays` packs in list order, so the booths
            # filled the grid and the 23x21 wheel reported NO SITE three times - a module is not
            # unsiteable because it is late, it is unsiteable because everything smaller got there
            # first. Largest footprint first is the only order that does not starve it.
            {"name": "Colour Wheel", "gen": "casino", "kind": "wheel",
             "size": [24, 4, 24], "params": {"pit": 2}, "count": 2, "floor": 0},
            {"name": "High Roller", "gen": "casino", "kind": "high_roller",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "One In Three", "gen": "casino", "kind": "double_or_none",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "Lucky Two", "gen": "casino", "kind": "lucky_number",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "Duel", "gen": "casino", "kind": "duel",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "Casino Marquee", "gen": "casino", "kind": "marquee",
             "size": [18, 5, 4], "params": {"length": 16}, "count": 4, "floor": 0},
            {"name": "Prize Wall", "gen": "casino", "kind": "prize_wall",
             "size": [4, 5, 12], "params": {"lanes": 5}, "count": 4, "floor": 0},
            {"name": "House Bank", "gen": "casino", "kind": "counter",
             "size": [4, 4, 8], "params": {"lanes": 6}, "count": 3, "floor": 0},
            # THE BUILDING GOES LAST, AND THAT ORDER IS LOAD-BEARING.
            #
            # `emit` chains `defer_to` down the list, so a later module yields any cell an earlier
            # one already claimed. Built first, the hall's floor would take every room's floor and
            # the rooms would lose the thing that makes them rooms. Built last it lays only the
            # ground BETWEEN them - which is exactly what a hall is.
            #
            # It is also the fix for "nothing to place against": the plot is void, and every design
            # reported free-floating cells because there is no ground on a fresh skyblock island.
            {"name": "Casino Hall", "gen": "casino", "kind": "hall", "anchor": "cover",
             "size": [88, 7, 88], "params": {"width": 88, "depth": 88, "gate": 3},
             "count": 1, "floor": 0},
        ],
    },

    # ------------------------------------------------------------------ the theme park
    #
    # THREE ZONES, ONE PARK, AND THE ZONES ARE THREE SEPARATE PLANS ON PURPOSE. Each is its own
    # island with its own bedrock and its own plot, so a single plan spanning all three would be
    # sited against a boundary that does not exist. `newisle` is the centre and the entrance;
    # left and right lead off it through arches pinned to their own edges.
    #
    # **EACH ZONE IS PLANNED AGAINST ITS CORE, AND THE EXPANSION IS A SECOND PLAN.** Jack builds
    # the inner 100x100 first and grows the plot to 200x200 later, so the core must stand alone
    # and nothing in the outer band may be load-bearing for it. Planning the core against the
    # island's CURRENT radius gets that for free: everything sites inside the ring that already
    # exists, and the expansion adds modules rather than moving them. A plan that had spread over
    # the full 200 would put the plaza's centre and the gate's approach in ground that is not
    # there yet, and expanding would cost a rebuild rather than an addition.
    #
    # The lands differ by PALETTE FAMILY - bright wool, warm wood, dark stone - because three
    # zones that differ only by signage are one zone three times, which is exactly what made the
    # casino read as the same room eighteen times over.
    "midway": {
        "blurb": "the park's front door: gate, plaza, landmark tower and a carnival midway",
        "keywords": ["theme park", "midway", "entrance", "fairground", "carnival", "park centre"],
        "orient": True,
        "paths": True,
        "paths_name": "Midway Paths",
        "floors": [{"name": "Ground", "y": 0}],
        "modules": [
            # LARGEST FIRST. `bays` packs in list order, so a big module listed late finds the
            # grid full of booths and reports NO SITE - the Colour Wheel did exactly that three
            # times. A module is not unsiteable because it is late.
            {"name": "Hall of Mirrors", "gen": "park", "kind": "walkthrough",
             "size": [15, 7, 15],
             "params": {"land": "midway", "width": 13, "depth": 13, "facing": "south"}},
            {"name": "Grand Tower", "gen": "park", "kind": "tower", "size": [15, 32, 15],
             "params": {"land": "midway", "width": 9, "tiers": 5, "facing": "south"}, "count": 1},
            # THE GATE IS THE ONE MODULE WHOSE POSITION IS ITS MEANING. On the southern edge,
            # facing out, so you arrive at it rather than find it.
            {"name": "Park Gate", "gen": "park", "kind": "gate", "size": [15, 9, 7],
             "anchor": "edge", "side": "west",
             "params": {"land": "midway", "lanes": 3, "depth": 6, "facing": "west"}},
            # The ways to the other two zones, each pinned to the edge it points at. An arch to
            # the west that is not on the western edge does not lead anywhere.
            {"name": "Frontier Arch", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "north",
             "params": {"land": "frontier", "width": 7, "height": 6, "facing": "north"}},
            {"name": "Hollow Arch", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "south",
             "params": {"land": "hollow", "width": 7, "height": 6, "facing": "south"}},
            {"name": "Midway Booth", "gen": "park", "kind": "booth", "size": [9, 7, 7],
             "params": {"land": "midway", "width": 7, "depth": 5, "facing": "south"},
             "count": 6},
            {"name": "Food Stall", "gen": "park", "kind": "stall", "size": [9, 7, 7],
             "params": {"land": "midway", "width": 7, "depth": 5, "facing": "north"},
             "count": 4},
            # THE GROUND GOES LAST, for the casino hall's reason: a covering module laid first
            # would take the floor out from under everything sited after it.
            {"name": "Grand Plaza", "gen": "park", "kind": "plaza", "anchor": "cover",
             "size": [72, 5, 72],
             "params": {"land": "midway", "width": 72, "depth": 72, "facing": "south"}},
        ],
    },

    "frontier": {
        "blurb": "the west zone: a mine, a saloon and a prospect tower in spruce and cobble",
        "keywords": ["frontier", "mine", "western", "wild west", "prospect"],
        "orient": True,
        "paths": True,
        "paths_name": "Frontier Paths",
        "floors": [{"name": "Ground", "y": 0}],
        "modules": [
            {"name": "Deep Mine", "gen": "park", "kind": "walkthrough", "size": [19, 7, 19],
             "params": {"land": "frontier", "width": 17, "depth": 15, "facing": "east"}},
            {"name": "The Saloon", "gen": "park", "kind": "walkthrough", "size": [15, 7, 13],
             "params": {"land": "frontier", "width": 13, "depth": 11, "facing": "east"}},
            {"name": "Prospect Tower", "gen": "park", "kind": "tower", "size": [15, 26, 15],
             "params": {"land": "frontier", "width": 9, "tiers": 4, "facing": "east"}},
            {"name": "Frontier Gate", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "south",
             "params": {"land": "frontier", "width": 7, "height": 6, "facing": "south"}},
            {"name": "Tin Can Alley", "gen": "park", "kind": "booth", "size": [9, 7, 7],
             "params": {"land": "frontier", "width": 7, "depth": 5, "facing": "east"},
             "count": 3},
            {"name": "Trading Post", "gen": "park", "kind": "stall", "size": [9, 7, 7],
             "params": {"land": "frontier", "width": 7, "depth": 5, "facing": "west"},
             "count": 5},
            {"name": "Frontier Plaza", "gen": "park", "kind": "plaza", "anchor": "cover",
             "size": [72, 5, 72],
             "params": {"land": "frontier", "width": 72, "depth": 72, "facing": "east"}},
        ],
    },

    "hollow": {
        "blurb": "the east zone: a haunted manor, a crypt and a clock tower in blackstone",
        "keywords": ["hollow", "haunted", "gothic", "crypt", "manor", "spooky"],
        "orient": True,
        "paths": True,
        "paths_name": "Hollow Paths",
        "floors": [{"name": "Ground", "y": 0}],
        "modules": [
            {"name": "Haunted Manor", "gen": "park", "kind": "walkthrough", "size": [21, 7, 19],
             "params": {"land": "hollow", "width": 19, "depth": 17, "facing": "west"}},
            {"name": "The Crypt", "gen": "park", "kind": "walkthrough", "size": [15, 7, 15],
             "params": {"land": "hollow", "width": 13, "depth": 13, "facing": "west"}},
            {"name": "Clock Tower", "gen": "park", "kind": "tower", "size": [15, 32, 15],
             "params": {"land": "hollow", "width": 9, "tiers": 5, "facing": "west"}},
            {"name": "Hollow Gate", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "north",
             "params": {"land": "hollow", "width": 7, "height": 6, "facing": "north"}},
            {"name": "Fortunes", "gen": "park", "kind": "booth", "size": [9, 7, 7],
             "params": {"land": "hollow", "width": 7, "depth": 5, "facing": "west"},
             "count": 3},
            {"name": "Curio Shop", "gen": "park", "kind": "stall", "size": [9, 7, 7],
             "params": {"land": "hollow", "width": 7, "depth": 5, "facing": "east"},
             "count": 4},
            {"name": "Hollow Court", "gen": "park", "kind": "plaza", "anchor": "cover",
             "size": [72, 5, 72],
             "params": {"land": "hollow", "width": 72, "depth": 72, "facing": "west"}},
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
            # THE SPREAD IS READ OFF THE ANCHOR OFFSET, NOT OFF `at`.
            #
            # A module's anchor is not its minimum corner - a game runs from at-6 to at+9 and the
            # hall runs from at-87 to at - so treating `at` as the corner reported the casino
            # spilling 80 blocks past the plot and using 113% of it, when every module was in fact
            # inside. A boundary report that cries wolf is one nobody reads.
            xs, zs, area = [], [], 0
            for m in self.modules:
                fx, _fy, fz = m.get("anchor_offset", (0, 0, 0))
                x0, z0 = m["at"][0] + fx, m["at"][2] + fz
                xs += [x0, x0 + m["size"][0] - 1]
                zs += [z0, z0 + m["size"][2] - 1]
                if not m.get("covers"):          # the hall IS the floor; it is not "used up"
                    area += m["size"][0] * m["size"][2]
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



_FOOTPRINT_CACHE: dict = {}


def measured_footprint(gen: str, kind: str, params: dict, declared):
    """The module's REAL extent relative to its anchor, measured by building one.

    **THE DECLARED SIZE WAS A HAND-TYPED GUESS AND IT WAS WRONG.** A casino game is declared 9x8x8
    and builds 16x10x10 - and not centred on its anchor either: it runs from at-6 to at+9 across
    and at-7 to at+2 along, because the shell, the pit and the payout all extend BACKWARDS from
    the cell the player stands at. So every clearance test, every module-against-module check and
    the plot boundary guard were all measuring a box the build does not occupy, and a game sited
    its floor straight over the island's starter chest twice running.

    This is rule 11 pointed at ourselves: ask the generator, not your memory. Building one module
    costs milliseconds and is cached per (kind, params).

    Returns (ox, oy, oz, w, h, d) - the offsets from `at` and the true size.
    """
    key = (gen, kind, tuple(sorted((k, str(v)) for k, v in params.items())))
    if key in _FOOTPRINT_CACHE:
        return _FOOTPRINT_CACHE[key]
    out = None
    try:
        import numpy as np
        from .gen import GENERATORS
        probe = {**params, "at": [0, 64, 0], "kind": kind, "check": False}
        probe.setdefault("facing", "east")
        c = GENERATORS[gen].build(probe, [])
        m = c.to_model()
        ox, oy, oz = c.world_origin
        names = []
        for tag in m.palette:
            try:
                names.append(tag.value["Name"].value.split(":")[-1])
            except Exception:                                    # noqa: BLE001
                names.append("air")
        solid = ~np.isin(m.ids, [i for i, n in enumerate(names) if n == "air"])
        ys, zs, xs = np.where(solid)
        if len(xs):
            out = (int(xs.min()) + ox, int(ys.min()) + oy - 64, int(zs.min()) + oz,
                   int(xs.max() - xs.min()) + 1, int(ys.max() - ys.min()) + 1,
                   int(zs.max() - zs.min()) + 1)
    except Exception:                                            # noqa: BLE001
        out = None
    if out is None:
        # A MEASUREMENT THAT FAILED IS NOT A MEASUREMENT OF ZERO. Fall back to the declared box
        # and say nothing clever about it.
        out = (0, 0, 0, int(declared[0]), int(declared[1]), int(declared[2]))
    _FOOTPRINT_CACHE[key] = out
    return out



def _plot_bounds(pp):
    b = getattr(pp, "bounds", None)
    if callable(b):
        return b()
    return (pp.cx - pp.radius, pp.cx + pp.radius, pp.cz - pp.radius, pp.cz + pp.radius)


USE_CLEAR = 3          # rule 10: room to stand at a chest, open it and walk past


def _used_cells(sc) -> list:
    """Every cell in the capture holding something a player STANDS AT AND USES.

    Deliberately `protect.is_used` rather than `protect.is_protected`: the protected set is the
    never-OVERWRITE list and holds `wool`, which on this project's own islands is most of the
    sculpture material - used as a keep-clear radius it swallows whole builds. This project has
    made that exact substitution once already, in the night pass, and written it down.
    """
    from .gen import protect
    out = []
    # THE PALETTE HOLDS NBT TAGS, NOT STRINGS, and `str(tag)` is the tag's repr - which contains
    # the block name as a substring, so a careless parse SILENTLY MATCHES THE WRONG THING. The
    # first version of this found one "used" cell on the island and it was the BEDROCK; the chest
    # it was written to protect was never seen, and a module sited straight over it again.
    m = sc.model if hasattr(sc, "model") else sc
    ids = m.ids
    names = []
    for tag in m.palette:
        try:
            names.append(tag.value["Name"].value.split(":")[-1])
        except Exception:                                        # noqa: BLE001
            names.append("air")
    keep = {i for i, n in enumerate(names) if protect.is_used(n)}
    if not keep:
        return out
    import numpy as np
    ox, oy, oz = sc.origin
    for i in keep:
        for (y, z, x) in zip(*np.where(ids == i)):
            out.append((int(x) + ox, int(y) + oy, int(z) + oz))
    return out


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
    # WHAT IS ALREADY THERE AND USED IS NOT SITE, and the planner only ever checked itself.
    #
    # `_clear` compares module against module, so on a fresh island `High Roller 6` sited straight
    # over the STARTER CHEST - the one holding everything the alt owns - and shipped with a single
    # overlap and no placement problem. Rule 10 has been in this project for a year (leave about
    # three blocks of working room around anything you stand at and use); nothing had ever applied
    # it at the SITING stage, because on the main island the ground search happened to avoid them.
    #
    # A used block is seeded into `taken` as a box, so it costs nothing new: the same clearance
    # test that keeps two modules apart keeps a module off a chest.
    taken: list = []
    for (ux, uy, uz) in _used_cells(sc):
        taken.append((ux - USE_CLEAR, uy - USE_CLEAR, uz - USE_CLEAR,
                      USE_CLEAR * 2 + 1, USE_CLEAR * 2 + 1, USE_CLEAR * 2 + 1))
    for mspec in spec["modules"]:
        fx, fy, fz, fw, fh, fd = measured_footprint(
            mspec["gen"], mspec["kind"], dict(mspec.get("params", {})), mspec["size"])
        # **A MODULE THAT WILL BE TURNED MUST RESERVE A SQUARE.** Orientation is decided after
        # siting - it depends on where the module landed relative to the hub - and turning a 9x7
        # building through 90 degrees makes it 7x9, which no longer fits the slot that was
        # reserved for it. Booking the larger dimension on both axes means any of the four
        # facings fits the same slot, so the turn can never push a building into its neighbour.
        # It costs a little packing efficiency and the plots are 13% used.
        orient = bool(spec.get("orient")) and mspec.get("anchor") != "cover"
        bw = bd = max(fw, fd) if orient else 0
        for i in range(int(mspec.get("count", 1))):
            size = ([bw + spacing, fh, bd + spacing] if orient
                    else [fw + spacing, fh, fd + spacing])
            spot = None
            taken_box = None
            bay = None
            # A COVERING MODULE IS NOT COMPETING FOR SPACE, IT IS THE SPACE.
            #
            # The hall's whole job is to lay the ground under and between the rooms, so the
            # overlap test that keeps two games apart is exactly wrong for it: asked to find a
            # free bay it correctly reported NO SITE, because by then the plane is full of rooms.
            # It is centred on the plot instead, and it claims nothing, so nothing sited after it
            # is pushed out.
            if mspec.get("anchor") == "cover" and pl_plot is not None and plane is not None:
                x0, x1, z0, z1 = _plot_bounds(pl_plot)
                cw, cd = size[0] - spacing, size[2] - spacing
                bx = x0 + max(0, ((x1 - x0 + 1) - cw) // 2)
                bz = z0 + max(0, ((z1 - z0 + 1) - cd) // 2)
                pl.modules.append({
                    "name": mspec["name"], "gen": mspec["gen"], "kind": mspec["kind"],
                    "at": [bx - fx, plane, bz - fz], "size": [fw, fh, fd], "roll": 0,
                    "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                    "floor": floors[0]["name"], "covers": True,
                    "params": dict(mspec.get("params", {})), "world": world,
                })
                continue
            # AN EDGE MODULE IS A THRESHOLD, AND A THRESHOLD IS ONLY A THRESHOLD ON THE BOUNDARY.
            #
            # A gate sited by `bays` lands wherever there happens to be a free bay, which is a
            # gatehouse in the middle of a field: you walk round it. Same for the arches that lead
            # to the neighbouring zones - an arch to the west that is not ON the western edge does
            # not point anywhere. So `anchor: edge` pins the module against the named side and
            # centres it along that side, and unlike `cover` it DOES claim its box, because
            # everything else must keep out of the doorway.
            if mspec.get("anchor") == "edge" and pl_plot is not None and plane is not None:
                x0, x1, z0, z1 = _plot_bounds(pl_plot)
                side = mspec.get("side", "south")
                if side in ("west", "east"):
                    bx = x0 if side == "west" else x1 - fw + 1
                    bz = z0 + max(0, ((z1 - z0 + 1) - fd) // 2)
                else:
                    bz = z0 if side == "north" else z1 - fd + 1
                    bx = x0 + max(0, ((x1 - x0 + 1) - fw) // 2)
                taken.append((bx, plane + fy, bz, fw + spacing, fh, fd + spacing))
                pl.modules.append({
                    "name": mspec["name"], "gen": mspec["gen"], "kind": mspec["kind"],
                    "at": [bx - fx, plane, bz - fz], "size": [fw, fh, fd], "roll": 0,
                    "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                    "floor": floors[0]["name"], "edge": side,
                    "params": dict(mspec.get("params", {})), "world": world,
                })
                continue
            # THE GRID FIRST, so the plot is used rather than a strip of it. Each bay still has to
            # pass the SAME ground test a free-form pad would - flat enough, in the band, free -
            # because a tidy grid over rolling terrain is still a build on rolling terrain.
            if plane is not None and pl_plot is not None:
                for (bx, bz) in bays(pl_plot, size, spacing=1):
                    # bays() hands back where the BUILD goes; the anchor is offset from it
                    ax, az = bx - fx, bz - fz
                    if not (pl_plot.contains(bx, bz)
                            and pl_plot.contains(bx + size[0], bz + size[2])):
                        continue
                    if _clear(taken, bx, plane + fy, bz, size):
                        spot = (ax, plane, az, 0)
                        taken_box = (bx, plane + fy, bz, size[0], size[1], size[2])
                        # the RESERVED corner, kept so the module can be re-placed inside its own
                        # slot once its facing is chosen from where it landed
                        bay = (bx, bz, bw or fw, bd or fd)
                        break
            elif pl_plot is not None:
                for (bx, bz) in bays(pl_plot, size, spacing=1):
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
            taken.append(taken_box or (x + fx, y + fy, z + fz, size[0], size[1], size[2]))
            pl.modules.append({
                "name": label, "gen": mspec["gen"], "kind": mspec["kind"],
                "at": [x, y + lift, z], "size": [fw, fh, fd], "roll": roll,
                "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                "floor": floors[min(int(mspec.get("floor", 0)), len(floors) - 1)]["name"],
                "params": dict(mspec.get("params", {})),
                "bay": list(bay) if bay else None,
                "world": world,
            })
    if spec.get("orient") and plane is not None:
        _orient_to_streets(pl, plane)
    if spec.get("paths") and plane is not None:
        _add_paths(pl, spec, plane, world, pl_plot)
    return pl


def _front_of(m):
    """The cell a visitor stands in to face this module's door, in world coordinates.

    `at` is the module's FRONT-LEFT corner and `d` runs from the front INTO the building, so the
    front face is the box edge in the +facing direction - not the minimum corner, and not the
    anchor. Getting this from the box rather than from `at` is the same lesson
    `measured_footprint` records: the declared anchor is not where the build actually is.
    """
    from .gen.park import _STEP
    ax, _ay, az = m["at"]
    ox, _oy, oz = m.get("anchor_offset", (0, 0, 0))
    w, _h, d = m["size"]
    x0, z0 = ax + ox, az + oz
    x1, z1 = x0 + w - 1, z0 + d - 1
    dx, dz = _STEP[m.get("params", {}).get("facing", "east")]
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if dx:
        return ((x1 + 2) if dx > 0 else (x0 - 2), cz)
    return (cx, (z1 + 2) if dz > 0 else (z0 - 2))


def _street_axis(m, cx, cz):
    """Which avenue this module belongs to, and which way it must face to address it.

    Decided from the module's CENTRE rather than from its front, because the front is a function
    of the facing and this is what chooses the facing - reading it off the front would be circular
    and would let the orientation and the spur disagree about which avenue a building is on.
    Returns (facing, along_z) where along_z means it spurs perpendicular to the east-west avenue.
    """
    # **MEASURED FROM THE RESERVED SQUARE, NOT FROM THE BUILT BOX.** Turning a building moves
    # its box, which moves its centre, which can flip the very decision that turned it - one
    # module per zone came out facing one avenue while the recomputed answer named the other, so
    # its shopfront addressed one street and its spur ran to another. The reserved bay does not
    # move when the module turns, so deciding from it is stable by construction.
    bay = m.get("bay")
    if bay and len(bay) == 4:
        bx, bz, bw, bd = bay
        mx, mz = bx + bw // 2, bz + bd // 2
    else:
        x0, z0, x1, z1 = _box_of(m)
        mx, mz = (x0 + x1) // 2, (z0 + z1) // 2
    dx, dz = mx - cx, mz - cz
    if abs(dz) <= abs(dx):
        return ("north" if dz > 0 else "south"), True
    return ("west" if dx > 0 else "east"), False


def _orient_to_streets(pl, plane):
    """Turn every building to address the street it is joined to.

    **HALF OF THEM PRESENTED THEIR BACKS.** `facing` was a theme constant, so a booth sited north
    of the avenue faced exactly the same way as one sited south of it, and about half the park
    showed a blank rear wall to the street its own spur ran to. A shopfront that cannot be seen
    into is a shed.

    This runs AFTER siting because the answer depends on where the module landed, and it is only
    safe because siting reserved a SQUARE: turning a 9x7 building makes it 7x9, and re-measuring
    inside its own slot is what keeps it out of its neighbour. The edge modules are left alone -
    a gate faces out of the park by definition, which is the whole reason it is on the edge.
    """
    hub = next((m for m in pl.modules if m.get("covers")), None)
    if hub is None:
        return
    hx0, hz0, hx1, hz1 = _box_of(hub)
    cx, cz = (hx0 + hx1) // 2, (hz0 + hz1) // 2
    for m in pl.modules:
        if m is hub or m.get("edge") or m["kind"] == "paths" or not m.get("bay"):
            continue
        facing, _along_z = _street_axis(m, cx, cz)
        if facing == m["params"].get("facing"):
            continue
        params = {**m.get("params", {}), "facing": facing}
        fx, fy, fz, fw, fh, fd = measured_footprint(
            m["gen"], m["kind"], params, m.get("declared_size", m["size"]))
        bx, bz = m["bay"][0], m["bay"][1]
        m["params"] = params
        m["at"] = [bx - fx, plane, bz - fz]
        m["anchor_offset"] = [fx, fy, fz]
        m["size"] = [fw, fh, fd]


def _inside_of(m):
    """The cell a visitor stands in on the PARK side of a threshold - the opposite of `_front_of`.

    An edge module faces outward by definition, so its front approach lies beyond the plot; the
    street has to meet it where the park is.
    """
    from .gen.park import _STEP
    x0, z0, x1, z1 = _box_of(m)
    dx, dz = _STEP[m.get("params", {}).get("facing", "east")]
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if dx:
        return ((x0 - 2) if dx > 0 else (x1 + 2), cz)
    return (cx, (z0 - 2) if dz > 0 else (z1 + 2))


def _box_of(m):
    ax, _ay, az = m["at"]
    ox, _oy, oz = m.get("anchor_offset", (0, 0, 0))
    w, _h, d = m["size"]
    return (ax + ox, az + oz, ax + ox + w - 1, az + oz + d - 1)


def _add_paths(pl, spec, plane, world, pl_plot=None):
    """Join every door to an avenue, and both avenues to the hub.

    **A CROSS, NOT A STAR.** Running a spoke from the hub to each of sixteen modules is sixteen
    paths radiating out of one square, which reads as a spider rather than as a street. Both
    avenues run through the hub on cardinal axes instead, so a spur from any door reaches one of
    them by running PERPENDICULAR until it lands - a single straight segment, no corner, and
    connected by construction.
    """
    hub = next((m for m in pl.modules if m.get("covers")), None)
    if hub is None:
        return
    hx0, hz0, hx1, hz1 = _box_of(hub)
    cx, cz = (hx0 + hx1) // 2, (hz0 + hz1) // 2

    others = [m for m in pl.modules if m is not hub and m["kind"] != "paths"]
    obstacles = [list(_box_of(m)) for m in others]
    # **AN EDGE MODULE IS JOINED ON ITS INSIDE FACE, NOT ITS FRONT.** A gate faces OUT of the
    # park - that is what makes it a gate - so its front approach is a cell beyond the plot
    # boundary, which the avenue cannot legally reach and the clamp correctly threw away. All
    # three edge modules came back unreached for that reason, which read as a routing bug and is
    # actually the geometry being right. You walk THROUGH a threshold, so the street meets it on
    # the side the park is on.
    links = [(m, _inside_of(m) if m.get("edge") else _front_of(m)) for m in others]
    fronts = [pt for _m, pt in links]
    if not fronts:
        return

    # **BOTH AVENUES SPAN THE WHOLE PARK, AND THAT IS WHAT MAKES THE NETWORK CONNECTED.**
    #
    # Written the obvious way - an avenue from each EDGE module to the hub - the paving came out
    # as three to five separate islands and missed six doors outright. Two reasons, one cause:
    # an avenue that stops at the hub only covers the half of the axis its gate is on, so a spur
    # from a door on the far side runs out to a coordinate where there is no avenue to land on;
    # and a side zone has only ONE edge module, so one of the two axes never existed at all.
    #
    # Full-length axes fix both by construction. Every front lies within [x0,x1] x [z0,z1], so a
    # perpendicular spur ALWAYS terminates on an avenue, and the two avenues cross at the hub.
    xs = [f[0] for f in fronts] + [cx]
    zs = [f[1] for f in fronts] + [cz]
    # `_plot_bounds` returns (x0, x1, z0, z1) - both X values, THEN both Z values. Unpacked as
    # (x0, z0, x1, z1) the axes scramble into each other and the two avenues span the diagonal of
    # the world: 170,191 cells of paving, which is the only reason it was caught immediately.
    px0, px1, pz0, pz1 = (_plot_bounds(pl_plot) if pl_plot is not None
                          else (min(xs), max(xs), min(zs), max(zs)))
    x0, x1 = max(min(xs), px0 + 2), min(max(xs), px1 - 2)
    z0, z1 = max(min(zs), pz0 + 2), min(max(zs), pz1 - 2)
    routes = [
        {"a": [x0, cz], "b": [x1, cz], "width": 5, "lamps": True},
        {"a": [cx, z0], "b": [cx, z1], "width": 5, "lamps": True},
    ]

    # THE SPURS: each door out to whichever avenue is nearer, perpendicular - a single straight
    # run with no corner, which is only possible because the avenues span the full range.
    for (m, (fx, fz)) in links:
        if m.get("edge"):
            continue          # centred on its own axis, so the avenue already runs to it
        fx = min(max(fx, x0), x1)
        fz = min(max(fz, z0), z1)
        # ONE RULE, SHARED. `_street_axis` decides both which way a building turns and which
        # avenue its spur runs to; asking the question twice in two places is how a shopfront
        # ends up addressing one street while its path goes to the other.
        if _street_axis(m, cx, cz)[1]:
            routes.append({"a": [fx, fz], "b": [fx, cz], "width": 3})
        else:
            routes.append({"a": [fx, fz], "b": [cx, fz], "width": 3})

    routes = [r for r in routes if r["a"] != r["b"]]
    if not routes:
        return
    land = spec["modules"][0]["params"]["land"]
    # **INSERTED BEFORE THE PLAZA, NOT APPENDED AFTER IT.** `layers.slice_plan` resolves a
    # contested cell first-writer-wins in plan order, and the paving and the plaza occupy the
    # same course - appended last, every avenue would be overwritten by the plaza it crosses and
    # the park would have invisible streets. Buildings still come first and still win, which is
    # the order that is actually wanted: building over path over plaza.
    pl.modules.insert(pl.modules.index(hub), {
        "name": spec.get("paths_name", "Park Paths"), "gen": "park", "kind": "paths",
        "at": [cx, plane, cz], "size": [1, 5, 1], "roll": 0,
        "declared_size": [1, 5, 1], "anchor_offset": [0, 0, 0],
        "floor": pl.modules[0]["floor"], "covers": True,
        "params": {"land": land, "facing": "east", "routes": routes, "obstacles": obstacles},
        "world": world,
    })


def _theme_for(brief: str) -> str:
    """Pick a theme from a brief, by keyword.

    DELIBERATELY DUMB, AND SAYS SO. This is the open-ended half of the problem and a keyword match
    is an honest placeholder for a judgement; what it must never do is guess silently, so an
    unmatched brief raises rather than defaulting to the only theme in the catalogue.
    """
    b = (brief or "").lower()
    # **A NAME BEATS A KEYWORD, AND THE TWO PASSES ARE THE WHOLE FIX.** Checked together, the
    # first theme whose EITHER test passes wins - so `midway`'s generic "theme park" keyword
    # swallowed "theme park frontier" and "theme park hollow" alike, and all three zones planned
    # as the centre. Both dry runs came back byte-identical, which is the only reason it was
    # caught: two different briefs producing the same 10,403-block plan is not a coincidence.
    #
    # An explicit name is the strongest possible signal a brief can carry, so it is resolved
    # first, across ALL themes, before any keyword is considered.
    for theme in THEMES:
        if theme in b:
            return theme
    for theme, spec in THEMES.items():
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



def measured_expensive(gen: str, kind: str, params: dict) -> dict:
    """How many CURRENCY-tier blocks one of these modules really places.

    A marquee is sixteen redstone lamps and a lamp cannot be substituted by colour - the nearest
    cheap match is `acacia_planks`, which is a lamp that does not light. So the cost is real and
    the honest thing is to DECLARE it, exactly as the Island Run declares its thirteen slime
    blocks: the repo-wide eight-block ceiling stays meaningful for everything else, and the
    exception sits in the config where a reader meets it.
    """
    from .gen import GENERATORS
    from . import palette
    out: dict = {}
    try:
        probe = {**params, "at": [0, 64, 0], "kind": kind, "check": False}
        probe.setdefault("facing", "east")
        c = GENERATORS[gen].build(probe, [])
        m = c.to_model()
        import numpy as np
        for i, tag in enumerate(m.palette):
            try:
                name = tag.value["Name"].value.split(":")[-1]
            except Exception:                                    # noqa: BLE001
                continue
            n = int((m.ids == i).sum())
            if n and palette.tier(name) == "expensive":
                out[name] = out.get(name, 0) + n
    except Exception:                                            # noqa: BLE001
        return {}
    return out


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
    # THE ORIGIN LOCK IS OFF FOR A PLAN, AND BOTH HALVES OF THAT ARE DELIBERATE.
    #
    # The default lock is the MAIN island's corner, so a casino at 97588/80595 would pad from
    # -24251/29949 - a schematic the size of the world, which passes the pipeline's own
    # "lock <= natural origin" check because it really is below and west of everything.
    #
    # Deriving the lock from THIS island's plot corner fixes the size and is still wrong. The lock
    # exists so a design that regenerates cannot drift, and it pays for that with padding: each
    # module then shipped as a 47x13x40 box holding 224 blocks - 99% AIR - and all 29 placements
    # sat on one corner, overlapping, most of them looking empty from wherever you stand.
    #
    # A PLANNED MODULE DOES NOT NEED THE LOCK, because its `at` is pinned in the config by an
    # approved plan. The origin is already deterministic; the lock only adds air. So each design
    # hugs its own content and its placement sits where the module actually is.
    written = []
    prev: list = []
    for m in pl.modules:
        slug = m["name"].lower().replace(" ", "_")
        cfg = {
            "name": m["name"],
            "gen": m["gen"],
            # THE MODULE'S NAME REACHES THE BUILD, so the door sign says which room this is.
            # Without it every door in the casino reads "HIGH ROLLER" and a player cannot tell
            # one room from the next - which is most of what "it is not clear what any of the
            # games are" meant.
            "params": {**m.get("params", {}), "at": m["at"], "kind": m["kind"],
                       "title": m["name"], "under": m.get("world")},
            "finish": {"verify_against": m.get("world")},
        }
        cfg["origin_lock"] = False
        exp = measured_expensive(m["gen"], m["kind"], dict(m.get("params", {})))
        if exp:
            total = sum(exp.values())
            cfg["expensive_allowance"] = total
            cfg["expensive_reason"] = (
                "; ".join(f"{v}x {k}" for k, v in sorted(exp.items()))
                + " - a light cannot be substituted by colour (the nearest cheap match is a lamp "
                  "that does not light), so this cost is declared rather than hidden")
        # **NOTHING DEFERS ANY MORE, AND THAT IS THE POINT.**
        #
        # `defer_to` settles which design owns a shared cell, and it does that by DELETING the
        # cell from the loser - so every module became a fragment with holes in it, and looking at
        # the casino meant loading a pile of overlapping designs each missing pieces. Three rounds
        # of confusion came out of that, and none of it was ever about the casino.
        #
        # The modules are INTERMEDIATE artifacts now. Each is generated whole, overlaps and all;
        # the conflicts are resolved once, explicitly, in `layers.slice_plan`, which is also the
        # only place that knows the right precedence. What gets placed is the slice.
        p = os.path.join(out_dir, f"{slug}.yaml")
        with open(p, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        written.append(p)
        prev.append(m["name"])
    return written
