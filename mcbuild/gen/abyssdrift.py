"""THE ABYSS DRIFT - the field the Abyss Squid swims through.

Jack: "lets add other objects underneath in the empty gaps as appropriate, small rocks floating
or something else, think critically." He chose a jellyfish and the WHOLE void.

WHAT THIS IS, AND WHY IT IS A FIELD AND NOT A SCATTER. The void under the park is 117,350 of
120,000 columns empty (97.8%), Y100-190, and this repo has a scar four deep about exactly the
naive answer: a uniform sprinkle of identical small things reads as CONFETTI - the deck soffit's
grid, the thicket's drifts, the frog's blotches, the claim row's ground all said it. The fix is
always the same: the clustering lives in a LOW-FREQUENCY field, not per cell, so the objects come
out as drifts and clearings rather than an even fuzz. Here the same field also does the second
job the void needs -

TWO THINGS DECIDE WHERE A ROCK GOES, AND BOTH ARE MEASURED.

  VISIBILITY. The deep band is seen by NOBODY except a runner on the two Prism Well helices
  (r14-50, falling Y300->Y95) and whoever stands at the pool floor. There is no other way into
  Y100-190 and there is no sky light at any hour. So effort is graded by closeness to the well
  axis: dense, bright and detailed just outside the fall column, thinning to sparse dark
  silhouettes in the far south, where only a free-flying explorer ever goes. Jack asked for the
  whole void dressed, so the far density is a floor, not a zero - but it is a floor.

  THE HERO. The squid gets a modest second attractor at 0.6 weight so it reads as swimming
  THROUGH a current rather than alone in a box - but never inside its clearance bubble. Debris
  crowding the one thing down there that took 47,000 blocks would be vandalism.

EVERYTHING CARRIES ITS OWN LIGHT, because in a pitch-dark void an unlit rock is a black rock in
black nothing seen by no one. The palette is the squid's, exactly, so the whole underside reads
as one hand: `ochre_froglight` (the only full-block light WITNESSED in a world capture - not the
tier table, not `out/`, which is circular) for the bright nodes that carry at distance, and
amethyst - `amethyst_block` / `budding_amethyst` / `amethyst_cluster` (light 5, cheap, and the
Lowland Portal's own accent) - for the crystal that gives a geode its violet and its texture. A
far rock is nearly dark with one dim bud; a near rock has a froglight geode facing the well.

THE ROCK IS ONE THING, SIZE-GRADED, from a two-cell crystal MOTE (the sea-snow, the plankton,
the depth cue) up to a nine-radius BOULDER that looms. There is no separate "mote system" to go
confetti on its own: a mote is just the small tail of the same size distribution, and it clusters
in the same drifts as everything else.

THE TRAPS, each of which this repo has shipped clean once:

  - `Canvas.solid()`, never `if get()`: -1 out of bounds is TRUTHY (the ladybird's seven caps).
  - Centres are INTEGER and offsets are added to them: `round()` is banker's rounding and does
    not tie-break symmetrically (the ladybird's clod came out as 18 separate towers).
  - NO GRAVITY BLOCKS. Sand/gravel/concrete-powder would pour out of a floating rock (rule 13);
    the stone families do not.
  - A crystal CLUSTER needs a solid face behind it, opposite its `facing`, or it is an unsupported
    block the audit rejects - so a bud is only placed where the rock backs it.
  - Nothing enters the well's r56 fall column, and nothing touches the squid or the park. The
    exclusion is a MASK consulted by the one `put`, so a part added later cannot forget it - the
    Lost Plateau stood a post on a live rail three times, each caught by a walk and not an audit.

WHAT IT DOES NOT CLAIM. It hangs in void, so every cell of it "floats" - the in-context audit
reports free-floating clusters and that is correct, exactly as it is for the squid and every
parkour run. `drop_floaters` is off. Judge form and mass off `tools/look.py`; the light, which is
the whole point, only shows in game - `render3d` has no emission.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01

DRIFT = {
    "seed": 11,
    # the world cell the canvas corner (0,0,0) occupies. The band is Y100-190 under the park's
    # own 200x600 shadow (X97500..97699 / Z80300..80899).
    "at": [97500, 100, 80300],
    "size": [200, 91, 600],           # x, y, z of the canvas: the park shadow, one band

    # THE FALL COLUMN. (x, z, r): a vertical cylinder no cell may enter, all Y. r56 = the well's
    # own r52 lining plus four, the squid's own keep-out number, because a surface inside it does
    # not save a runner who misses a landing - it strands one sixty blocks out with no way back.
    "well": [97590, 80815, 56],

    # THE HERO and how far to stay off it. The squid's cells are loaded from its shipped litematic
    # and its footprint is forbidden with this clearance, so debris hugs its shape rather than its
    # bounding box - which would forfeit the whole central void.
    "squid": "out/Abyss Squid.litematic",
    "squid_clear": 6,
    # the park's own stuff in the band (the well collar and column, the Frontier shaft, the transit
    # lines, the park underside): forbidden with this clearance so nothing crowds a wall or a rail.
    "park": "out/Park Complete.litematic",
    "park_clear": 4,
    # other void designs the field must keep off (the jellies): each footprint forbidden with the
    # squid's clearance, so debris frames them rather than crowding them.
    "avoid": [],
    "edge_inset": 3,                  # keep an object's centre this far in from the shadow edge

    # GRADING. vis in [0,1] is 1 just outside the well and decays to 0 at `vis_range` blocks from
    # the well axis; the squid adds a weaker attractor. Density, brightness and the chance of the
    # richer features all ride on it.
    "vis_range": 190.0,
    "squid_weight": 0.6,
    "squid_range": 70.0,

    # THE DRIFT FIELD. A low-frequency blobby value in [0,1] over cells of `drift_cell`, smoothed,
    # so acceptance comes out as clouds and gaps. THIS is what stops it being confetti.
    "drift_cell": 26,
    "drift_gain": 1.35,               # >1 sharpens clouds; the field is centred near 0.5

    # PLACEMENT. Candidate centres sit on a jittered lattice of this pitch; a candidate is taken
    # when hash < density, and density = (far + (near-far)*vis) * drift. The lattice pitch sets the
    # finest spacing; the acceptance sets how full a cloud gets.
    "pitch": 9,
    "near_density": 0.80,
    "far_density": 0.16,
    "min_gap": 3.0,                   # centres no closer than this (plus their radii)

    # THE SIZE DISTRIBUTION. A rock's radius is drawn as far_min..far_max, biased small, then the
    # rare big ones are allowed only where there is room. Most cells are in the small tail (motes).
    "r_min": 0.8,
    "r_max": 7.5,
    "r_bias": 2.4,                    # >1 pushes the draw toward r_min: many motes, few boulders
    "big_at": 5.5,                    # a rock at or above this radius is a "boulder": gets a geode,
                                      # streamers and a froglight core; below it is a mote/cobble
    "max_boulders": 14,               # a hard cap: a few big silhouettes, not a boulder field. A
                                      # boulder past the cap is demoted to a medium rock, not skipped

    # THE PRINTING SCAFFOLD. Off by default (the art hangs free). On, an MST of connectors is laid
    # between every floating island so the whole field is one connected mass the printer can chain
    # through. The connector block is distinct from the rock palette on purpose: print the design,
    # then `delete all <scaffold_block>` in game to strip every connector and leave the rocks.
    "scaffold": False,
    "scaffold_block": "moss_block",
}

# THE VALUE LADDER, MEASURED ACROSS FAMILIES - never inside one, which is the mistake this repo
# has made four times (stone brick, blackstone, the Mine Ridge, the claim row: a family is one
# material shown four ways and cannot draw a value line). side-face luminance:
#   cobbled_deepslate 77 . blackstone 79 . deepslate 80 . cobblestone 127 . stone 126
# A rock is BEDDED in a few of these by a coarse hash so it reads as rock rather than as one grey.
# NO TUFF and NO ANDESITE (Jack: both expensive in bulk on skyblock; this field is the whole void,
# so hundreds of any one block is real cost) - their weight went mostly to cobblestone, the one
# truly `cheap` grey. The spread is now three darks plus cobblestone as the light anchor.
_ROCK = ["cobbled_deepslate", "blackstone", "cobblestone", "deepslate"]
_ROCK_W = [0.32, 0.16, 0.36, 0.16]

_AXES = {"east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0),
         "south": (0, 0, 1), "north": (0, 0, -1)}


def _load_columns(path, at, size):
    """The XZ footprint (canvas coords) of a shipped design's cells inside our band, or None."""
    try:
        from .. import schem
        import json
        m = schem.load(path)
        side = path.rsplit(".litematic", 1)[0] + ".scan.json"
        o = json.load(open(side))["origin"]
    except Exception:
        return None
    ox, oy, oz = o["x"], o["y"], o["z"]
    ax, ay, az = at
    occ = m.ids != 0
    ys, zs, xs = np.nonzero(occ)
    wx, wy, wz = xs + ox, ys + oy, zs + oz
    band = (wy >= ay) & (wy < ay + size[1])
    cx = wx[band] - ax
    cz = wz[band] - az
    inb = (cx >= 0) & (cx < size[0]) & (cz >= 0) & (cz < size[2])
    mask = np.zeros((size[2], size[0]), bool)
    mask[cz[inb], cx[inb]] = True
    return mask


def _dilate(mask, r):
    """Chebyshev dilation by r, numpy only (no scipy) - the ladybird-siting idiom."""
    out = mask.copy()
    for _ in range(int(r)):
        out[:-1, :] |= out[1:, :]
        out[1:, :] |= out[:-1, :]
        out[:, :-1] |= out[:, 1:]
        out[:, 1:] |= out[:, :-1]
    return out


def _drift_field(sx, sz, cell, seed, gain):
    """A smooth blobby value in [0,1] over the XZ plane: bilinear over a coarse hash lattice."""
    gx, gz = sx // cell + 2, sz // cell + 2
    node = np.empty((gz, gx))
    for j in range(gz):
        for i in range(gx):
            node[j, i] = hash01(seed, i, j, 7)
    xs = np.arange(sx) / cell
    zs = np.arange(sz) / cell
    i0 = np.floor(xs).astype(int); j0 = np.floor(zs).astype(int)
    fx = (xs - i0)[None, :]; fz = (zs - j0)[:, None]
    a = node[np.ix_(j0, i0)]; b = node[np.ix_(j0, i0 + 1)]
    c = node[np.ix_(j0 + 1, i0)]; d = node[np.ix_(j0 + 1, i0 + 1)]
    v = (a * (1 - fx) + b * fx) * (1 - fz) + (c * (1 - fx) + d * fx) * fz
    v = 0.5 + (v - 0.5) * gain
    return np.clip(v, 0.0, 1.0)


class _Field:
    """The one gate every cell passes through, so the exclusions cannot be forgotten."""

    def __init__(self, c, at, blocked_xz, well):
        self.c = c
        self.at = at
        self.blk = blocked_xz          # (z, x): True = may not build here
        self.well = well
        self.n = 0
        self.closest_well = float("inf")
        self.closest_squid = float("inf")

    def free_col(self, x, z) -> bool:
        return self.c.inb(x, 0, z) and not self.blk[int(z), int(x)]

    def put(self, x, y, z, blk) -> bool:
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if not self.c.inb(x, y, z) or self.blk[z, x]:
            return False
        self.c.ids[y, z, x] = blk
        self.n += 1
        d = math.hypot(self.at[0] + x - self.well[0], self.at[2] + z - self.well[1])
        if d < self.closest_well:
            self.closest_well = d
        return True

    def solid(self, x, y, z) -> bool:
        return self.c.solid(int(round(x)), int(round(y)), int(round(z)))

    def scaffold(self, x, y, z, blk) -> bool:
        """Place a temporary connector cell: air only, inside the band, never in an excluded
        column (the squid, the park, a rail, the well column). It never overwrites a rock, so a
        line drawn straight through a lump simply fuses to it instead of eating it."""
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if not self.c.inb(x, y, z) or self.blk[z, x] or self.c.ids[y, z, x] != 0:
            return False
        self.c.ids[y, z, x] = blk
        return True


def _rock(f, cx, cy, cz, r, mats, bright, seed):
    """One floating rock: an irregular lump, bedded, with light appropriate to how far out it is.

    `bright` in [0,1] is the visibility at the rock: it decides whether the rock is a dark
    silhouette with a single dim bud (far) or a geode with a froglight core facing the well (near).
    """
    c = f.c
    # a lump: the primary sphere plus one or two smaller offset bulges, so the outline is not a
    # ball. Offsets are added to INTEGER centres. Jitter roughens the surface a little.
    cx, cy, cz = int(round(cx)), int(round(cy)), int(round(cz))
    lobes = [(cx, cy, cz, r)]
    n_extra = 0 if r < 2.0 else (1 if r < 4.0 else 2)
    for k in range(n_extra):
        a = hash01(seed, k, 1) * 2 * math.pi
        rr = r * (0.45 + 0.25 * hash01(seed, k, 2))
        off = r * 0.55
        lobes.append((cx + int(round(off * math.cos(a))),
                      cy + int(round((hash01(seed, k, 3) - 0.5) * r)),
                      cz + int(round(off * math.sin(a))), rr))

    def jit(x, y, z):
        return (hash01(x, y, z, seed) - 0.5) * (0.9 if r >= 3 else 0.3)

    placed = []
    for (lx, ly, lz, lr) in lobes:
        for y in range(int(ly - lr - 1), int(ly + lr + 2)):
            for z in range(int(lz - lr - 1), int(lz + lr + 2)):
                for x in range(int(lx - lr - 1), int(lx + lr + 2)):
                    d = math.sqrt((x + .5 - lx) ** 2 + (y + .5 - ly) ** 2 + (z + .5 - lz) ** 2)
                    if d <= lr + jit(x, y, z):
                        # BEDDED: the material is a coarse hash on the cell, so a rock is a mix of
                        # the family rather than a speckle of it, and reads as stone.
                        h = hash01(x // 3, y // 3, z // 3, seed)
                        acc = 0.0
                        name = mats[-1]
                        for nm, w in zip(_ROCK, _ROCK_W):
                            acc += w
                            if h < acc:
                                name = nm
                                break
                        if f.put(x, y, z, c.state(name)):
                            placed.append((x, y, z))
    if not placed:
        return None
    # a real, solid representative cell for the scaffold to anchor to - the placed cell nearest the
    # centre, so a mote whose exact centre came out air still gives the connector a cell to reach.
    rep = min(placed, key=lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2 + (q[2] - cz) ** 2)

    # WHERE THE LIGHT GOES: toward the well, so a near rock's glow is seen from the sightline.
    dirx = f.well[0] - (f.at[0] + cx)
    dirz = f.well[1] - (f.at[2] + cz)
    dl = math.hypot(dirx, dirz) or 1.0
    ux, uz = dirx / dl, dirz / dl
    fx, fy, fz = cx + ux * (r - 0.4), cy + 0.6, cz + uz * (r - 0.4)

    frog = c.state("ochre_froglight")
    if r >= 2.2 and bright > 0.18:
        # a froglight core just under the well-facing surface: it reads as a lit vein/node.
        nodes = 1 + int(r >= 5) + int(r >= 8)
        for i in range(nodes):
            a = (hash01(seed, i, 5) - 0.5) * 1.6
            px = fx + math.cos(a) * (0.6 + i)
            pz = fz + math.sin(a) * (0.6 + i)
            f.put(px, fy + (hash01(seed, i, 6) - 0.5) * r, pz, frog)

    # CRYSTAL: amethyst clusters on a few surface cells, facing outward. The mote's only light when
    # it is too small for a froglight, and the geode's violet everywhere else. The cluster is backed
    # by the rock's OWN stone - `amethyst_block` and `calcite` are both expensive tier here, so a
    # geode is grown straight out of the rock rather than lined with a violet backing.
    n_bud = max(1, int(r * (0.7 + 0.8 * bright)))
    for i in range(n_bud):
        # a surface cell in a random outward direction
        a = hash01(seed, i, 8) * 2 * math.pi
        b = (hash01(seed, i, 9) - 0.5) * math.pi
        dx, dy, dz = math.cos(b) * math.cos(a), math.sin(b), math.cos(b) * math.sin(a)
        sx = cx + dx * (r - 0.2); sy = cy + dy * (r - 0.2); sz = cz + dz * (r - 0.2)
        # the outward face and the cell just past it
        ax = int(round(sx)); ay = int(round(sy)); az = int(round(sz))
        ox = int(round(sx + dx)); oy = int(round(sy + dy)); oz = int(round(sz + dz))
        if not f.solid(ax, ay, az) or f.solid(ox, oy, oz):
            continue
        face = _facing(ox - ax, oy - ay, oz - az)
        if face:
            f.put(ox, oy, oz, c.state("amethyst_cluster", facing=face, waterlogged="false"))
    return rep


def _facing(dx, dy, dz):
    if dx or dy or dz:
        for name, (vx, vy, vz) in _AXES.items():
            if (vx, vy, vz) == (dx, dy, dz):
                return name
    return None


def _streamers(f, cx, cy, cz, r, seed):
    """Glowing cave-vines off a big rock's underside - the 'kelp', the alive/drifting cue, and
    a self-lit one.

    A vine hangs from the rock's own solid cell above it, and each segment carries the next, so
    the column is legal and 6-connected - which `hanging_roots` are NOT: they do not stack, so a
    column of them is illegal past the first, which is the audit's own finding (`from air`). Most
    segments are berried (`cave_vines[berries=true]` is light 14), so a streamer is a hanging
    string of warm points - the abyss lighting itself, the thicket's own idiom.
    """
    n = 1 + int(r >= 5) + int(r >= 8)
    for k in range(n):
        a = hash01(seed, k, 20) * 2 * math.pi
        bx = int(round(cx + math.cos(a) * r * 0.5))
        bz = int(round(cz + math.sin(a) * r * 0.5))
        # the underside of the rock in this column: solid with air below
        top = None
        for y in range(int(cy), int(cy - r - 2), -1):
            if f.solid(bx, y, bz) and not f.solid(bx, y - 1, bz):
                top = y
                break
        if top is None:
            continue
        drop = 3 + int((r + 4) * hash01(seed, k, 21))
        run = []
        for i in range(1, drop + 1):
            y = top - i
            if not f.c.inb(bx, y, bz) or f.solid(bx, y, bz):
                break
            run.append(y)
        for i, y in enumerate(run):
            bs = "false" if hash01(seed, k, y, 22) < 0.25 else "true"   # mostly berried = light 14
            if i == len(run) - 1:
                f.put(bx, y, bz, f.c.state("cave_vines", berries=bs, age="25"))
            else:
                f.put(bx, y, bz, f.c.state("cave_vines_plant", berries=bs))


def _spark(f, cx, cy, cz, seed):
    """A lone glowing point - the far star, the bright fleck of plankton. One froglight or one
    crystal nugget, floating. A single full-block light floats legally; a bare cluster does not,
    so a crystal spark is a core block plus one bud."""
    c = f.c
    if hash01(seed, cx, cz, 3) < 0.5:
        return (cx, cy, cz) if f.put(cx, cy, cz, c.state("ochre_froglight")) else None
    # a crystal nugget: a deepslate core (witnessed, not `budding_amethyst`, which is not
    # obtainable in survival) with an amethyst cluster budding off the top.
    if f.put(cx, cy, cz, c.state("deepslate")):
        f.put(cx, cy + 1, cz, c.state("amethyst_cluster", facing="up", waterlogged="false"))
        return (cx, cy, cz)
    return None


def _path(a, b):
    """The 6-connected cells from a to b, excluding the start: one axis step per move (largest
    remaining delta first), so the run is a near-straight staircase that is legal to place and
    walk. Shared by the freeness test and the draw, so what is tested is exactly what is laid."""
    x, y, z = a
    tx, ty, tz = b
    guard = 0
    while (x, y, z) != (tx, ty, tz) and guard < 8192:
        guard += 1
        dx, dy, dz = tx - x, ty - y, tz - z
        if abs(dx) >= abs(dy) and abs(dx) >= abs(dz):
            x += 1 if dx > 0 else -1
        elif abs(dy) >= abs(dz):
            y += 1 if dy > 0 else -1
        else:
            z += 1 if dz > 0 else -1
        yield x, y, z


def _free(f, a, b) -> bool:
    """True if a connector from a to b would be unobstructed: every path cell is in the band and in
    no excluded column. It may pass THROUGH a rock (that only fuses it); it may not pass through the
    squid, the park, a rail or the well column - so a broken edge is rejected outright rather than
    laid as a dead stub that orphans a cluster."""
    for x, y, z in _path(a, b):
        if not f.c.inb(x, y, z) or f.blk[z, x]:
            return False
    return True


def _line(f, a, b, blk) -> int:
    """Lay a 6-connected run of scaffold from a to b, air cells only, and return the count. Called
    only on an edge `_free` has already cleared, so nothing is skipped mid-run."""
    return sum(1 for (x, y, z) in _path(a, b) if f.scaffold(x, y, z, blk))


def _connect(f, centres, blk, k=10, max_edge=48.0):
    """Fuse the floating islands with a forest of connectors. Kruskal over each cluster's k nearest
    neighbours, keeping only edges whose straight line is actually unobstructed (`_free`) - so a
    connector routes AROUND the squid via the ring of clusters instead of dying against its
    footprint, and the only components left are the ones the squid genuinely walls off. Shortest
    free edge first, union-find, so it is a minimum forest. Once one seed block is placed per
    remaining region the printer chains the rest; `delete all <block>` strips every connector."""
    n = len(centres)
    if n < 2:
        return 0
    pts = np.array(centres, dtype=float)
    # k nearest neighbours per node (vectorised); candidate edges are those pairs, deduped i<j.
    kk = min(k, n - 1)
    edges = {}
    for i in range(n):
        d = np.linalg.norm(pts - pts[i], axis=1)
        d[i] = np.inf
        for j in np.argpartition(d, kk)[:kk]:
            j = int(j)
            if d[j] > max_edge:
                continue
            key = (i, j) if i < j else (j, i)
            edges[key] = d[j]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    laid = 0
    for (i, j), _d in sorted(edges.items(), key=lambda e: e[1]):
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        a = tuple(int(v) for v in pts[i])
        b = tuple(int(v) for v in pts[j])
        if not _free(f, a, b):
            continue
        laid += _line(f, a, b, blk)
        parent[ri] = rj

    # SECOND PASS: whatever the local kNN graph left in separate components, bridge with the
    # shortest unobstructed edge between any two of them - not limited to nearest neighbours, so a
    # lone far-south mote reaches the mass however far it is. Kruskal again over these long bridges.
    roots = {}
    for i in range(n):
        roots.setdefault(find(i), []).append(i)
    comps = list(roots.values())
    bridges = []
    for ci in range(len(comps)):
        for cj in range(ci + 1, len(comps)):
            best = None
            for i in comps[ci]:
                d = np.linalg.norm(pts[comps[cj]] - pts[i], axis=1)
                m = int(np.argmin(d))
                if best is None or d[m] < best[0]:
                    best = (float(d[m]), i, comps[cj][m])
            if best is not None:
                bridges.append(best)
    for _d, i, j in sorted(bridges, key=lambda e: e[0]):
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        a = tuple(int(v) for v in pts[i])
        b = tuple(int(v) for v in pts[j])
        if not _free(f, a, b):
            continue
        laid += _line(f, a, b, blk)
        parent[ri] = rj
    return laid


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DRIFT, **(cfg or {})}
    seed = int(p["seed"])
    at = tuple(int(v) for v in p["at"])
    sx, sy, sz = (int(v) for v in p["size"])
    well = (float(p["well"][0]), float(p["well"][1]), float(p["well"][2]))

    c = Canvas(sx, sy, sz, donors)

    # ---- the exclusion mask (2D). The squid nearly fills the vertical band, so a column-wise
    # exclusion loses almost no usable void and costs one array instead of a 10-million-cell
    # dilation. Well cylinder + squid footprint + park stuff, each dilated by its own clearance.
    blocked = np.zeros((sz, sx), bool)
    zz, xx = np.mgrid[0:sz, 0:sx]
    wd = np.hypot(at[0] + xx - well[0], at[2] + zz - well[1])
    blocked |= wd < well[2]
    excl = [(p["squid"], p["squid_clear"]), (p["park"], p["park_clear"])]
    excl += [(path, p["squid_clear"]) for path in p.get("avoid", [])]
    for path, clr in excl:
        m = _load_columns(path, at, (sx, sy, sz))
        if m is not None:
            blocked |= _dilate(m, clr)
    # keep centres off the very edge so nothing pokes out of the shadow into daylight
    inset = int(p["edge_inset"])
    blocked[:inset, :] = True; blocked[-inset:, :] = True
    blocked[:, :inset] = True; blocked[:, -inset:] = True

    f = _Field(c, at, blocked, well)

    # ---- the fields that grade the whole void
    drift = _drift_field(sx, sz, int(p["drift_cell"]), seed, float(p["drift_gain"]))
    # squid centroid (world XZ) for the second attractor
    sqm = _load_columns(p["squid"], at, (sx, sy, sz))
    if sqm is not None and sqm.any():
        szc, sxc = np.nonzero(sqm)
        sq_wx = at[0] + sxc.mean(); sq_wz = at[2] + szc.mean()
    else:
        sq_wx, sq_wz = well[0], well[1]

    def vis(wx, wz):
        dw = math.hypot(wx - well[0], wz - well[1])
        v = max(0.0, 1.0 - max(0.0, dw - well[2]) / float(p["vis_range"]))
        ds = math.hypot(wx - sq_wx, wz - sq_wz)
        vs = float(p["squid_weight"]) * max(0.0, 1.0 - ds / float(p["squid_range"]))
        return min(1.0, max(v, vs))

    # ---- place, on a jittered lattice, accepting into the drifts.
    #
    # THE ORDER IS SHUFFLED, NOT SPATIAL, and that is not cosmetic. The first version iterated
    # south-to-north and stopped at a block budget, so it spent the whole budget in the far south
    # before ever reaching the well - and four boulders ate half of it. The nearest cell to the
    # well came out 224 blocks away, in the one zone that has to be the densest. Totals are ruled
    # by DENSITY now (a finite lattice, graded by visibility, needs no cutoff), the order is a
    # hash so no position is favoured, and boulders are capped by count so a few big silhouettes
    # cannot become the whole field.
    pitch = int(p["pitch"])
    counts = {"rocks": 0, "motes": 0, "boulders": 0, "sparks": 0, "streamers": 0}
    centres = []                       # one representative solid cell per cluster, for the scaffold
    ybase, ytop = 2, sy - 3
    cand = [(gx, gz) for gz in range(0, sz, pitch) for gx in range(0, sx, pitch)]
    cand.sort(key=lambda g: hash01(seed, g[0], g[1], 99))
    max_boulders = int(p["max_boulders"])
    for gx, gz in cand:
        k = (gx // pitch) * 7919 + (gz // pitch)
        jx = gx + int((hash01(seed, k, 1) - 0.5) * pitch)
        jz = gz + int((hash01(seed, k, 2) - 0.5) * pitch)
        if not (0 <= jx < sx and 0 <= jz < sz) or blocked[jz, jx]:
            continue
        wx, wz = at[0] + jx, at[2] + jz
        v = vis(wx, wz)
        dens = (float(p["far_density"]) + (float(p["near_density"]) - float(p["far_density"])) * v)
        dens *= drift[jz, jx]
        if hash01(seed, jx, jz, 4) >= dens:
            continue
        jy = ybase + int(hash01(seed, jx, jz, 5) * (ytop - ybase))
        # a spark, or a rock whose radius is drawn small-biased and capped by how open it is
        if hash01(seed, jx, jz, 6) < 0.10 + 0.10 * (1 - v):
            rep = _spark(f, jx, jy, jz, seed ^ k)
            if rep:
                counts["sparks"] += 1
                centres.append(rep)
            continue
        u = hash01(seed, jx, jz, 7) ** float(p["r_bias"])
        r = float(p["r_min"]) + u * (float(p["r_max"]) - float(p["r_min"]))
        # a boulder is only allowed where its whole footprint column is free AND the count is not
        # yet spent - otherwise it is demoted to a medium rock rather than skipped.
        if r >= float(p["big_at"]):
            room = all(f.free_col(jx + dx, jz + dz)
                       for dx in range(-int(r), int(r) + 1, 2)
                       for dz in range(-int(r), int(r) + 1, 2))
            if not room or counts["boulders"] >= max_boulders:
                r = float(p["big_at"]) - 1.0
        before = f.n
        rep = _rock(f, jx, jy, jz, r, _ROCK, v, seed ^ k)
        if rep is not None and f.n > before:
            centres.append(rep)
            if r < 2.0:
                counts["motes"] += 1
            elif r >= float(p["big_at"]):
                counts["boulders"] += 1
                _streamers(f, jx, jy, jz, r, seed ^ k)
                counts["streamers"] += 1
            else:
                counts["rocks"] += 1

    # ---- the printing scaffold: fuse every floating island with connectors of a distinct block.
    if p.get("scaffold"):
        counts["scaffold"] = _connect(f, centres, c.state(str(p["scaffold_block"])))

    c.world_origin = at
    c.meta = {
        "kind": "abyssdrift",
        "well": list(well),
        "closest_to_well": None if f.closest_well == float("inf") else round(f.closest_well, 1),
        "blocks": int((c.ids != 0).sum()),
        "features_built": counts,
        "scaffold_block": str(p["scaffold_block"]) if p.get("scaffold") else None,
    }
    return c
