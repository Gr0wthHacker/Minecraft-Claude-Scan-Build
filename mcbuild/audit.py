"""One audit for every model: placement validity, geometry, cost, symmetry.

Every check I had to write by hand during the session is here so a build
can't ship with a floating lantern, a leaking hollow, or a terracotta bill.

    result = audit(model)
    result.ok           -> bool
    result.problems     -> list[Problem]
    result.report()     -> str
"""
from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from . import morph, nbt, palette
from .schem import Model

# blocks that need something specific to hold them up / against
_SUPPORT_SET = None
OBSERVED_PATH = os.path.join(os.path.dirname(__file__), "data", "observed.json")
_OBSERVED: dict | None = None


def observed_rules() -> dict:
    """{kind: {relation: {neighbour: count}}} mined from real captures by `mcbuild learn`."""
    global _OBSERVED
    if _OBSERVED is None:
        _OBSERVED = {}
        if os.path.exists(OBSERVED_PATH):
            with open(OBSERVED_PATH, encoding="utf-8") as f:
                _OBSERVED = json.load(f).get("rules", {})
    return _OBSERVED


def _seen(kind: str, rel: str, neighbour: str) -> bool:
    return neighbour in observed_rules().get(kind, {}).get(rel, {})


def _held(kind: str, rel: str, neighbour: str) -> bool:
    """A full cube always holds; otherwise only what real worlds have shown to hold."""
    return _is_solid_name(neighbour) or _seen(kind, rel, neighbour)


def _center_support(n: str) -> bool:
    """Vanilla: a standing lantern only needs centre support - fences, walls, posts qualify."""
    return n.endswith("_fence") or n.endswith("_wall") or n in ("end_rod", "lightning_rod")


def _is_chain(n: str) -> bool:
    return n == "chain" or n.endswith("_chain")
DIRV = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
HANGERS = {"vine", "chain", "lantern", "soul_lantern", "pointed_dripstone", "hanging_roots",
           "cave_vines", "cave_vines_plant", "weeping_vines", "weeping_vines_plant"}
GROUND_PLANTS = {"short_grass", "tall_grass", "fern", "large_fern", "dandelion", "poppy",
                 "azalea", "flowering_azalea", "sweet_berry_bush", "dead_bush", "oxeye_daisy",
                 "white_tulip", "azure_bluet", "blue_orchid", "allium", "lily_of_the_valley",
                 "cornflower", "pink_petals", "sapling", "pink_tulip", "red_tulip", "orange_tulip",
                 "wither_rose", "torchflower", "lilac", "rose_bush", "peony", "sunflower"}
DIRT_LIKE = {"dirt", "grass_block", "moss_block", "podzol", "coarse_dirt", "rooted_dirt", "mud",
             "farmland", "mycelium"}


def _is_solid_name(n: str) -> bool:
    """Full-cube-ish blocks that can support things. Conservative."""
    if n in ("air", "cave_air", "void_air", "OOB"):
        return False
    if _is_chain(n):
        return False
    non = HANGERS | GROUND_PLANTS | {"ladder", "torch", "wall_torch", "moss_carpet", "iron_bars",
                                     "glass_pane", "chest", "water", "lava", "snow", "sea_pickle",
                                     "spore_blossom", "big_dripleaf", "small_dripleaf", "lily_pad"}
    if n in non:
        return False
    for suf in ("_carpet", "_pane", "_fence", "_wall", "_button", "_pressure_plate", "_sign",
                "_banner", "_door", "_trapdoor", "_candle", "_sapling", "_flower", "_leaves"):
        if n.endswith(suf) and n != "oak_leaves":
            return n.endswith("_leaves")          # leaves count as support for carpets/vines
    return True


@dataclass
class Problem:
    kind: str
    x: int
    y: int
    z: int
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.kind:14s} @({self.x},{self.y},{self.z}) {self.detail}"


@dataclass
class Result:
    problems: list[Problem] = field(default_factory=list)
    components: list[int] = field(default_factory=list)
    bom: Counter = field(default_factory=Counter)
    tiers: Counter = field(default_factory=Counter)
    cavity_cells: int = 0
    leaks: int = 0
    symmetric: bool | None = None
    size: tuple[int, int, int] = (0, 0, 0)
    blocks: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems and self.leaks == 0

    def report(self) -> str:
        sx, sy, sz = self.size
        lines = [f"size {sx}x{sy}x{sz}  blocks {self.blocks}  states {len(self.bom)}",
                 f"components: {sorted(self.components, reverse=True)[:6]}"
                 + (" (multiple!)" if len(self.components) > 1 else ""),
                 f"cost tiers: " + ", ".join(f"{k}={v}" for k, v in self.tiers.most_common()),
                 f"cavity cells {self.cavity_cells}  leaks {self.leaks}"]
        if self.symmetric is not None:
            lines.append(f"mirror-symmetric (x): {self.symmetric}")
        exp = [(k, v) for k, v in self.bom.most_common() if palette.tier(k) == "expensive"]
        if exp:
            lines.append("EXPENSIVE: " + ", ".join(f"{k.split(':')[-1]}:{v}" for k, v in exp))
        lines.append(f"problems: {len(self.problems)}")
        for p in self.problems[:25]:
            lines.append("  " + str(p))
        if len(self.problems) > 25:
            lines.append(f"  ... {len(self.problems) - 25} more")
        lines.append("BOM: " + ", ".join(f"{k.split(':')[-1]}:{v}" for k, v in self.bom.most_common()))
        return "\n".join(lines)


def check_supports(m: Model, ground_block: str | None = None) -> list[Problem]:
    """`ground_block`: name of the block the schematic will be pasted ONTO
    (e.g. 'moss_block' for surface kits). Cells at y=-1 then read as that
    block instead of OOB, so plants/carpets on the paste surface are valid."""
    names = np.array([n.split(":")[-1] for n in m.names])
    sy, sz, sx = m.ids.shape
    ids = m.ids
    gb = ground_block.split(":")[-1] if ground_block else None

    def nm(x, y, z):
        if y == -1 and gb and 0 <= x < sx and 0 <= z < sz:
            return gb
        if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
            return "OOB"
        return names[ids[y, z, x]]

    out: list[Problem] = []
    for (y, z, x) in zip(*np.where(ids > 0)):
        n = nm(x, y, z)
        p = m.props_at(x, y, z) if n in ("vine", "ladder", "lantern", "soul_lantern",
                                          "pointed_dripstone", "wall_torch") or _is_chain(n) else {}
        if n == "vine":
            ok = nm(x, y + 1, z) == "vine" or (p.get("up") == "true" and _held("vine", "above", nm(x, y + 1, z))) \
                or any(p.get(d) == "true" and _held("vine", "side", nm(x + dx, y, z + dz)) for d, (dx, dz) in DIRV.items())
            if not ok:
                out.append(Problem("vine", x, y, z, "no attachment"))
        elif _is_chain(n):
            if p.get("axis", "y") == "y" and not (_held("chain", "above", nm(x, y + 1, z)) or _is_chain(nm(x, y + 1, z))):
                out.append(Problem("chain", x, y, z, "nothing above"))
        elif n in ("lantern", "soul_lantern"):
            if p.get("hanging") == "true":
                if not (_held("lantern", "above", nm(x, y + 1, z)) or _is_chain(nm(x, y + 1, z))):
                    out.append(Problem("lantern", x, y, z, "hanging from air"))
            elif not (_held("lantern", "below", nm(x, y - 1, z)) or _center_support(nm(x, y - 1, z))):
                out.append(Problem("lantern", x, y, z, f"standing on {nm(x, y - 1, z)}"))
        elif n in ("cave_vines", "cave_vines_plant"):
            a = nm(x, y + 1, z)
            if not (_is_solid_name(a) or a == "cave_vines_plant"):
                out.append(Problem("cave_vines", x, y, z, f"top={a}"))
        elif n == "pointed_dripstone":
            a = nm(x, y + 1, z)
            b = nm(x, y - 1, z)
            if p.get("vertical_direction", "down") == "down":
                if not (_is_solid_name(a) or a == "pointed_dripstone"):
                    out.append(Problem("dripstone", x, y, z, "stalactite from air"))
            elif not (_is_solid_name(b) or b == "pointed_dripstone"):
                out.append(Problem("dripstone", x, y, z, "stalagmite on air"))
        elif n == "hanging_roots":
            if not _is_solid_name(nm(x, y + 1, z)):
                out.append(Problem("hanging_roots", x, y, z, "from air"))
        elif n == "ladder":
            f = p.get("facing", "north")
            dx, dz = DIRV[f]
            if not _held("ladder", "behind", nm(x - dx, y, z - dz)):
                out.append(Problem("ladder", x, y, z, f"no wall behind (facing {f})"))
        elif n == "moss_carpet" or n.endswith("_carpet"):
            b = nm(x, y - 1, z)
            if b in ("air", "OOB"):
                out.append(Problem("carpet", x, y, z, "floating"))
        elif n in GROUND_PLANTS:
            b = nm(x, y - 1, z)
            if b not in DIRT_LIKE and not _seen(f"plant:{n}", "below", b):
                out.append(Problem("plant", x, y, z, f"{n} on {b}"))
        elif n == "wall_torch":
            f = p.get("facing", "north")
            dx, dz = DIRV[f]
            if not _held("wall_torch", "behind", nm(x - dx, y, z - dz)):
                out.append(Problem("wall_torch", x, y, z, "no wall"))
        elif n == "torch":
            if not _held("torch", "below", nm(x, y - 1, z)):
                out.append(Problem("torch", x, y, z, "on air"))
    return out


def check_symmetry(m: Model, axis: str = "x", rows_from: int = 0) -> bool:
    """Front-face material mirror symmetry (about the model's centre)."""
    s = m.solid()
    sy, sz, sx = s.shape
    zi = np.where(s, np.arange(sz)[None, :, None], -1)
    front = zi.max(axis=1)
    names = m.names
    for y in range(rows_from, sy):
        for x in range(sx):
            xm = sx - 1 - x
            a = names[m.ids[y, front[y, x], x]] if front[y, x] >= 0 else None
            b = names[m.ids[y, front[y, xm], xm]] if front[y, xm] >= 0 else None
            if a != b:
                return False
    return True


def audit(m: Model, *, ground: bool = True, symmetry: bool = False,
          symmetry_rows_from: int = 0, ground_block: str | None = None,
          states: bool = True, reach: bool = False) -> Result:
    r = Result()
    s = m.solid()
    r.size = m.shape_xyz
    r.blocks = int(s.sum())
    names = m.names
    r.bom = Counter(names[i] for i in m.ids[s].tolist())
    for k, v in r.bom.items():
        r.tiers[palette.tier(k)] += v
    _, sizes = morph.components(s, conn=6)
    r.components = sizes
    ext = morph.flood_outside(s, pad=True, ground=ground)
    cav = (~s) & ~ext
    r.cavity_cells = int(cav.sum())
    r.problems = check_supports(m, ground_block=ground_block)
    if states:
        r.problems += check_states(m)
    if reach:
        r.problems += check_reach(m)
    if symmetry:
        r.symmetric = check_symmetry(m, rows_from=symmetry_rows_from)
    return r


# ------------------------------------------------------------------ state sanity

# A block state the game computes from its neighbours. If the design disagrees, Litematica paints the
# cell red forever even though you placed the right block - the vault's wall railings hit exactly this.
_FACING = {"stairs", "furnace", "chest", "trapped_chest", "ladder", "anvil", "dispenser", "dropper",
           "observer", "piston", "sticky_piston", "repeater", "comparator", "hopper", "loom",
           "smoker", "blast_furnace", "lectern", "beehive", "bee_nest", "carved_pumpkin"}


def check_states(m: Model) -> list:
    """Block states that cannot be right: a missing required property, or a value out of its set."""
    out = []
    s = m.solid()
    seen = {}
    for i, e in enumerate(m.palette):
        name = nbt.state_name(e).split(":")[-1]
        props = nbt.state_props(e)
        bad = _state_problem(name, props)
        if bad:
            seen[i] = bad
    if not seen:
        return out
    ys, zs, xs = np.where(s)
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        i = int(m.ids[y, z, x])
        if i in seen:
            out.append(Problem("state", x, y, z, seen[i]))
    return out


def _state_problem(name: str, props: dict) -> str | None:
    base = name.rsplit("_", 1)[-1]
    if name.endswith("_stairs"):
        for k, allowed in (("facing", {"north", "south", "east", "west"}), ("half", {"top", "bottom"}),
                           ("shape", {"straight", "inner_left", "inner_right", "outer_left", "outer_right"})):
            if props.get(k) not in allowed:
                return f"{name} {k}={props.get(k)!r}"
    if name.endswith("_slab") and props.get("type") not in {"top", "bottom", "double"}:
        return f"{name} type={props.get('type')!r}"
    if name.endswith("_wall"):
        for k in ("north", "south", "east", "west"):
            if props.get(k) not in {"none", "low", "tall"}:
                return f"{name} {k}={props.get(k)!r}"
        if props.get("up") not in {"true", "false"}:
            return f"{name} up={props.get('up')!r}"
    if base in _FACING and "facing" in props and props["facing"] not in {
            "north", "south", "east", "west", "up", "down"}:
        return f"{name} facing={props['facing']!r}"
    if name == "lantern" and props.get("hanging") not in {"true", "false"}:
        return f"lantern hanging={props.get('hanging')!r}"
    return None


# ------------------------------------------------------------------ reachability

def check_reach(m: Model, *, head: int = 2) -> list:
    """Cells with nowhere for a player to stand while placing them.

    `check_supports` says a block CAN exist; this says you can get to it. A cell is reachable when
    some neighbour within one step is open for `head` blocks - that is where you stand. Under-island
    work is where this bites, which is most of this island."""
    out = []
    s = m.solid()
    sy, sz, sx = s.shape
    open_ = ~s
    stand = open_.copy()
    for d in range(1, head):
        stand &= np.concatenate([open_[d:], np.zeros((d, sz, sx), bool)], axis=0)
    ys, zs, xs = np.where(s)
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        ok = False
        for dy, dz, dx in ((0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0)):
            ny, nz, nx = y + dy, z + dz, x + dx
            if 0 <= ny < sy and 0 <= nz < sz and 0 <= nx < sx and stand[ny, nz, nx]:
                ok = True
                break
        if not ok:
            out.append(Problem("reach", x, y, z, "no open cell beside it to stand in and place from"))
    return out
