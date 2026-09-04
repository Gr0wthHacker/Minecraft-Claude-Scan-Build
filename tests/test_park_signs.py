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
import pathlib

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

def _front(te):
    """The four front lines of one tile entity, or None if it carries no text."""
    try:
        msgs = te.value["front_text"].value["messages"].value
    except Exception:                                            # noqa: BLE001
        return None
    out = []
    for j in msgs:
        s = j.value
        try:
            s = json.loads(s)
        except Exception:                                        # noqa: BLE001
            pass
        out.append(s.get("text", "") if isinstance(s, dict) else str(s))
    return out


def test_no_sign_in_the_shipped_park_is_clipped_mid_word():
    """**THE PARK HAS SHIPPED FIVE SIGNS CUT MID-WORD**, from five different generators, and no
    check anywhere could see one: a clipped sign is a legal, supported, affordable 1.19 block,
    and `render3d` draws it identically to a whole one. The damage shows in a screenshot.

        MINE CART ESCAP   keep to the wal   112-cell circui   wade in and hol   prismworks: eas

    They arrived by four different routes - a config title, a config line an author had already
    shortened by hand, a computed line that crossed the width when its number gained a digit,
    and two literals - so guarding any ONE of those routes leaves the class open. THE SHIPPED
    COMPOSITE IS THE ONE PLACE EVERY ROUTE CAN BE SEEN AT ONCE, so that is what this reads.

    A line of exactly SIGN_WIDTH is fine and there are dozens: what is caught is a line at the
    limit whose last word is cut, which is a word the generator could not finish.
    """
    from mcbuild.gen.park import SIGN_WIDTH
    m = schem.load(os.path.join(OUT, "Park Complete.litematic"))
    o = json.load(open(os.path.join(OUT, "Park Complete.scan.json"), encoding="utf-8"))["origin"]
    words = set()
    for te in (m.tile_entities or []):
        for line in _front(te) or []:
            for w in str(line).replace("-", " ").split():
                words.add(w.strip(",.:;!?").lower())
    bad = []
    for te in (m.tile_entities or []):
        lines = _front(te) or []
        assert all(len(x) <= SIGN_WIDTH for x in lines), f"over-wide line: {lines}"
        for line in lines:
            if len(line) != SIGN_WIDTH:
                continue
            tail = line.split()[-1].strip(",.:;!?").lower() if line.split() else ""
            # A cut word is a strict PREFIX of a word used whole somewhere else in the park -
            # "escap" of "escape", "wal" of "wall", "circui" of "circuit", "eas" of "east". A
            # short real word ("way", "top") is a prefix of nothing that is spelt out anywhere.
            #
            # AN INFLECTION IS NOT A CLIP, and that is not a nicety: `THE CRUSHER` says "five
            # heads", so "ran to the head" - a deliberate two-line split - reads as "head" cut
            # out of "heads" and the guard cries wolf on a correct sign. A check that flags a
            # good build is a check nobody runs.
            if len(tail) >= 3 and any(w != tail and w.startswith(tail)
                                      and w[len(tail):] not in ("s", "es", "ing")
                                      for w in words):
                v = te.value
                bad.append((o["x"] + int(v["x"].value), o["z"] + int(v["z"].value), line))
    assert not bad, "signs clipped mid-word in the shipped park: " + str(bad)

def test_no_config_in_the_park_declares_a_sign_string_it_cannot_fit():
    """The other half of the clipping guard, and the half that catches a NEW word.

    The shipped-park check above can only see a cut word whose whole form is spelt out on some
    other sign - it caught `wal`, `eas` and `hol` and could never have caught `MINE CART ESCAP`,
    because nothing else in the park says "escape". So the source is checked too: a `title:` or
    `lines:` entry over the width is a clip waiting to be printed, whatever route it takes to
    the board. Only configs whose design is actually IN the composite are read - a config for a
    retired module may say what it likes, since nobody will ever stand in front of it.

    AND THE STRING HAS TO ACTUALLY REACH A BOARD CUT. `pf_lost_plateau.yaml` declares the
    title `THE LOST PLATEAU` at sixteen and its generator SPLITS it - the shipped sign reads
    "THE LOST / PLATEAU" and nothing is lost. Flagging that would be crying wolf on a correct
    build, so the test is whether the string's first SIGN_WIDTH characters stand on a board
    verbatim: `MINE CART ESCAP` does, `THE LOST PLATEA` does not.
    """
    import yaml
    from mcbuild.gen.park import SIGN_WIDTH
    sc = json.load(open(os.path.join(OUT, "Park Complete.scan.json"), encoding="utf-8"))
    shipped = set(sc["contains"])
    m = schem.load(os.path.join(OUT, "Park Complete.litematic"))
    shown = {ln for te in (m.tile_entities or []) for ln in (_front(te) or [])
             if len(ln) == SIGN_WIDTH}
    bad = []
    for f in sorted(pathlib.Path(ROOT, "configs").glob("*.yaml")):
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        if not isinstance(d, dict) or d.get("name") not in shipped:
            continue

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("title", "lines"):
                        for s in (v if isinstance(v, list) else [v]):
                            if isinstance(s, str) and len(s) > SIGN_WIDTH \
                                    and s[:SIGN_WIDTH] in shown:
                                bad.append((f.name, k, s, s[:SIGN_WIDTH]))
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(d)
    assert not bad, ("config sign strings that reach a board CUT at %d: %s"
                     % (SIGN_WIDTH, bad))
