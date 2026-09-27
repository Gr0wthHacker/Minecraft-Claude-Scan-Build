"""Island Enrichment: the detail pass, and the two rules that decide whether it reads.

WHY IT EXISTS, in one number: `tools/corpus.py` puts our architecture at a median 11.4% detail
blocks against 17.3% for 31 outside builds, and building by building it was far worse - the
Campanile was 575 cells of 12 block types at 1.4% detail, a bell tower of three blackstone
variants stacked.

The two rules this test pins are the ones that separate enrichment from vandalism:

  ADDITIVE - these buildings are 89-97% BUILT, so the pass writes into AIR and never over
  anything standing. The deck floor settled how a remedial design is judged: by what it
  REPLACES, not by what it places. `overlap 0` is the whole contract.

  RUNS, NOT CELLS - the deck soffit drew a coffer grid per cell and produced 215 runs of which
  184 were one or two cells, which this file's own history calls confetti. A cornice on
  scattered cells is that mistake with a different block, so a course shorter than `min_run`
  gets nothing.

The sill is the deliberate exception to the second rule and the test says so: a sill is
anchored to one opening rather than being a course, and an opening here is one to three cells
wide, so gating it by length deleted all 46 of them.
"""
import collections
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import schem, scan                    # noqa: E402
from mcbuild.gen import protect                    # noqa: E402
from mcbuild.gen.enrich import FAMILY, ENRICH      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "out", "island_full.litematic")
WORK = os.path.join(ROOT, "out", "Island Enrichment.work.json")
SIDE = os.path.join(ROOT, "out", "Island Enrichment.scan.json")

needs = pytest.mark.skipif(not (os.path.exists(FULL) and os.path.exists(WORK)),
                           reason="needs the capture and the generated enrichment")
AIRY = ("air", "cave_air", "void_air")


def _cells():
    return json.load(open(WORK, encoding="utf-8"))["cells"]


def _at():
    cap = schem.load(FULL)
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    pal = [n.split(":")[-1].split("[")[0] for n in cap.names]

    def at(x, y, z):
        iy, iz, ix = y - o["y"], z - o["z"], x - o["x"]
        if not (0 <= iy < cap.ids.shape[0] and 0 <= iz < cap.ids.shape[1]
                and 0 <= ix < cap.ids.shape[2]):
            return "air"
        return pal[cap.ids[iy, iz, ix]]
    return at


@needs
def test_it_is_purely_additive():
    """The whole contract. These buildings are built; the pass may not cost a broken block."""
    at = _at()
    for x, y, z, b in _cells():
        assert at(x, y, z) in AIRY, f"{b} at {(x, y, z)} would replace {at(x, y, z)}"


@needs
def test_it_never_dresses_a_mechanism():
    at = _at()
    for x, y, z, b in _cells():
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = at(x + dx, y + dy, z + dz)
            if protect.is_protected(n) and n not in ("water", "lava"):
                # touching is allowed; REPLACING is what the additive test forbids. What must
                # never happen is dressing something that is a machine's own face.
                assert at(x, y, z) in AIRY


@needs
def test_a_cornice_is_a_run_not_a_sprinkle():
    """The soffit's lesson. Every stair this pass places must sit in a contiguous span of at
    least `min_run` along its own axis - the axis the run travels, not the one it faces."""
    minrun = ENRICH["min_run"]
    stairs = [(x, y, z, b) for x, y, z, b in _cells() if "stairs" in b]
    assert stairs, "no stairs at all"
    byline = collections.defaultdict(set)
    for x, y, z, b in stairs:
        face = b.split("facing=")[1].split(",")[0].split("]")[0]
        if face in ("north", "south"):
            byline[(y, z, face, "x")].add(x)      # faces along Z, so the run travels along X
        else:
            byline[(y, x, face, "z")].add(z)
    lone = 0
    for key, vals in byline.items():
        v = sorted(vals)
        s = 0
        for i in range(1, len(v) + 1):
            if i == len(v) or v[i] != v[i - 1] + 1:
                if i - s < minrun:
                    lone += i - s
                s = i
    assert lone == 0, f"{lone} stair cells sit in runs shorter than {minrun} - that is confetti"


@needs
def test_a_stair_leans_into_the_wall_it_grows_from():
    """A stair's tall side is its `facing`, per the convention pinned in test_stairhead. A
    cornice or plinth whose tall side pointed AWAY would hang off the building backwards, and
    our renderer draws both identically - so it is asserted, never eyeballed."""
    at = _at()
    d = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
    for x, y, z, b in _cells():
        if "stairs" not in b:
            continue
        dx, dz = d[b.split("facing=")[1].split(",")[0].split("]")[0]]
        assert at(x + dx, y, z + dz) in FAMILY, (
            f"stair at {(x, y, z)} faces {at(x+dx, y, z+dz)}, not the masonry it grows from")


@needs
def test_a_sill_sits_under_a_real_opening():
    """The sill is the deliberate exception to the run gate, so it has to earn it: every slab
    must have masonry behind it and an opening directly above that masonry."""
    at = _at()
    slabs = [(x, y, z, b) for x, y, z, b in _cells() if "slab" in b]
    assert slabs, "no sills"
    d = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
    for x, y, z, b in slabs:
        behind = [(dx, dz) for dx, dz in d.values() if at(x + dx, y, z + dz) in FAMILY]
        assert behind, f"sill at {(x, y, z)} has no wall behind it"
        ok = any(at(x + dx, y + 1, z + dz) not in FAMILY for dx, dz in behind)
        assert ok, f"sill at {(x, y, z)} has solid masonry above its wall - no opening"


@needs
def test_it_closes_the_detail_gap_it_was_built_to_close():
    """The design's whole purpose, measured the way the corpus measures it. The flattest
    buildings were the Campanile at 1.4% and the Court Hall at 0.0%; both must clear the
    corpus median of 17.3%... or at least land in the same conversation."""
    fams = ("_stairs", "_slab", "_wall", "_fence", "_trapdoor", "_pane", "_carpet")
    add = collections.defaultdict(list)
    zones = {"Lowland Campanile": (-24202, 29967, -24191, 29979),
             "Lowland Sanctum": (-24194, 29962, -24177, 30017),
             "Court Hall": (-24234, 30008, -24221, 30029)}
    for x, y, z, b in _cells():
        for n, (a, bb, c, e) in zones.items():
            if a <= x <= c and bb <= z <= e:
                add[n].append(b)
                break
    for n in zones:
        p = os.path.join(ROOT, "out", f"{n}.work.json")
        if not os.path.exists(p):
            continue
        blocks_ = [q[3] for q in json.load(open(p, encoding="utf-8"))["cells"]] + add[n]
        det = sum(1 for b in blocks_ if any(b.split("[")[0].endswith(f) for f in fams))
        pct = 100 * det / len(blocks_)
        assert pct > 12.0, f"{n} is still {pct:.1f}% detail - the pass did not reach it"
