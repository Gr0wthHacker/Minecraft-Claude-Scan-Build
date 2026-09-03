"""Every sign in the park was blank, and nothing in the pipeline could see it.

A sign is TWO THINGS IN TWO HALVES OF A LITEMATIC - a palette entry and a tile entity - and
`park_place.merge` built a bare `Model(ids, pal)`. Measured before the fix: `PF Front Frontier` 16
tile entities, `PF Claim Lake Menagerie` 19, `PF Trailhead Gate` 6 ... and `Park Complete` **0**.

The blocks were all correct, the audit passed, the BOM was right, and `render3d` draws a sign the
same whether or not it says anything. The only symptom is a guest walking a park where nothing is
named - which is the complaint that found it, three sessions after the signs were written.
"""
from __future__ import annotations

import json
import os

from mcbuild import schem

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")


def _te(name):
    p = os.path.join(OUT, f"{name}.litematic")
    if not os.path.exists(p):
        return None
    return schem.load(p).tile_entities or []


def test_the_composite_carries_the_signs_its_modules_wrote():
    """The one artifact Jack actually places must not be the one that loses the text."""
    got = _te("Park Complete")
    if got is None:
        return
    assert got, "Park Complete carries no sign text at all"
    # ...and it is not a token few: the frontage, the gate and the menagerie alone write dozens
    assert len(got) >= 100, f"only {len(got)} signs carry text in the shipped park"


def test_no_sign_text_stands_without_its_block():
    """A tile entity with no block is a corrupt region, not a lost line.

    `layers.slice_plan` has always stated this rule and the merge never kept it - so a sign whose
    block lost a contested cell had to be dropped with it rather than re-addressed into thin air.
    """
    m = schem.load(os.path.join(OUT, "Park Complete.litematic"))
    ids = m.ids
    orphan = 0
    for t in (m.tile_entities or []):
        v = t.value
        x, y, z = int(v["x"].value), int(v["y"].value), int(v["z"].value)
        if not (0 <= y < ids.shape[0] and 0 <= z < ids.shape[1] and 0 <= x < ids.shape[2]):
            orphan += 1
            continue
        if not int(ids[y, z, x]):
            orphan += 1
    assert orphan == 0, f"{orphan} sign texts have no block under them"


def test_a_signs_text_is_addressed_to_the_cell_its_block_is_in():
    """`_shift_tile` rewrites x/y/z into the merged frame rather than mutating the source.

    Mutated in place, a module merged into two composites in one run would carry the first merge's
    coordinates into the second - which is a whole land's signs landing on the wrong blocks and
    nothing anywhere reporting it.
    """
    m = schem.load(os.path.join(OUT, "Park Complete.litematic"))
    names = [n.split(":")[-1] for n in m.names]
    wrong = []
    for t in (m.tile_entities or []):
        v = t.value
        x, y, z = int(v["x"].value), int(v["y"].value), int(v["z"].value)
        if not (0 <= y < m.ids.shape[0] and 0 <= z < m.ids.shape[1] and 0 <= x < m.ids.shape[2]):
            continue
        n = names[int(m.ids[y, z, x])]
        if "sign" not in n and "lectern" not in n and "chest" not in n and "banner" not in n:
            wrong.append((x, y, z, n))
    assert not wrong, f"sign text landed on non-sign blocks: {wrong[:5]}"


def test_the_lost_plateau_names_its_own_scenery():
    """The measurement this pass answers: the land's scenery - the coaster, the ridge, the canopy,
    the overgrowth, the two dinosaurs, the dig and the rim - is 133,170 blocks, 88% of the land's
    mass, and carried EIGHT signs and FOURTEEN interactive blocks between them.
    """
    m = schem.load(os.path.join(OUT, "Park Complete.litematic"))
    o = json.load(open(os.path.join(OUT, "Park Complete.scan.json"), encoding="utf-8"))["origin"]
    want = {"THE BONE BED", "THE CART LINE", "LOST PLATEAU", "WATCH THE SKY",
            "THE CUTTING", "THE SAUROPOD", "THE RIM WALK"}
    seen = set()
    for t in (m.tile_entities or []):
        v = t.value
        wz = o["z"] + int(v["z"].value)
        if not (80300 <= wz < 80480):
            continue
        try:
            lines = [json.loads(s).get("text", "")
                     for s in [j.value for j in v["front_text"].value["messages"].value]]
        except Exception:                                        # noqa: BLE001
            continue
        head = next((x for x in lines if x.strip()), "")
        if head in want:
            seen.add(head)
    assert seen == want, f"the plaques missing from the shipped land: {sorted(want - seen)}"
