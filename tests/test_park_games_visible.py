"""CAN A PLAYER SEE THE SCORE, AND REACH THE CONTROL? - the check `park_games` never had.

Every kind in `park_games` has had its circuit asserted by simulation since it was written, and
every one of them passed while being **unplayable**. Jack: *"the games arent playable as they are
facing, theyre ugly, and just not working, these have been a consistent issue."*

Measured off `out/PF Game Target Wall.litematic` as it stood:

    Y206   ############   the lid
    Y205   ##B#######T#   the BELL and the TARGET - the game's own INPUT
           ###LLLLLL###   the six score lamps
    Y204   ############   the plinth
           front face: solid at Y204, Y205 and Y206

A console was a THREE-COURSE SEALED CABINET. Its score lamps were buried in the machine course
behind a solid front in every kind; the `aim` and `striker` discs could not be shot at all; and the
controls sat on the lid, whose top face is **1.4 blocks above a standing player's eye**, so they
pressed a button they could not see on a counter they could not see over.

**A SIMULATED CONTRACT IS A CLAIM ABOUT THE CIRCUIT, NOT ABOUT THE PLAYER.** `mcbuild.circuit`
answers "does the signal reach the lamp"; nothing answered "can anybody see the lamp". This file is
that second question, and it is the one that had been missing for as long as the games have
existed.

    THE READOUT IS VISIBLE    a clear line from outside the front to every score lamp
    THE INPUT IS REACHABLE    the same, to every target, button, lever and plate
    THE WIRE IS NOT           and opening the front must not put a wire where a hand can break it
"""
from __future__ import annotations

import glob
from pathlib import Path

import pytest
import yaml

from mcbuild.gen import park_games

ROOT = Path(__file__).resolve().parents[1]

#: The direction a console's FRONT looks out, as `park.py` records it: "a visitor stands in the
#: +facing direction". So stepping this way from any cell walks out of the cabinet toward the
#: player, and a clear walk is a clear sightline.
STEP = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}

#: What a sightline passes through. Deliberately short: anything not named here is treated as
#: SOLID, which errs toward reporting a lamp hidden that is not rather than passing one that is.
CLEAR = {"air", "cave_air", "oak_wall_sign", "spruce_wall_sign", "stone_button", "lever",
         "redstone_lamp", "target", "bell", "light_weighted_pressure_plate",
         "heavy_weighted_pressure_plate", "barrel", "oak_trapdoor", "iron_door", "iron_trapdoor",
         "glass_pane", "iron_bars",
         # **DUST DOES NOT BLOCK SIGHT.** Redstone wire, a repeater and a comparator are all a
         # sixteenth of a block tall and you look straight over them; leaving them out of this set
         # reported five of the Signal's lamps as walled in by the very wire that lights them.
         # They ARE in the reach set below, which is the set that matters for a hand.
         "redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch"}

CONFIGS = sorted(glob.glob(str(ROOT / "configs" / "pf_game_*.yaml")))


def _build(path):
    cfg = yaml.safe_load(Path(path).read_text())
    if cfg.get("gen") != "park_games":
        pytest.skip(f"{Path(path).name} is not a park_games console")
    c = park_games.build(cfg["params"])
    pal = [e.value["Name"].value.split(":")[-1] for e in c.palette]
    ox, oy, oz = c.world_origin
    cells = {}
    for y in range(c.sy):
        for z in range(c.sz):
            for x in range(c.sx):
                i = int(c.ids[y, z, x])
                if i:
                    cells[(x + ox, y + oy, z + oz)] = pal[i]
    box = (ox, ox + c.sx - 1, oy, oy + c.sy - 1, oz, oz + c.sz - 1)
    return cfg, c, cells, box


def _sees_out(cells, box, start, facing, through=None) -> bool:
    """Is there a clear line from `start` out of the front of the cabinet?

    **THE WALK ENDS AT THE CABINET'S BOX, NOT AT THE FIRST EMPTY CELL.** The first version stopped
    on any cell the design does not fill and called it daylight - so a wire with one course of air
    in front of it and a pane beyond that read as EXPOSED, and two consoles were reported unsafe
    that are not. A cell absent from the model inside its own box is AIR, and air is something you
    keep walking through.
    """
    ok = CLEAR if through is None else through
    dx, dy, dz = STEP[facing]
    x0, x1, y0, y1, z0, z1 = box
    p = (start[0] + dx, start[1] + dy, start[2] + dz)
    for _ in range(40):
        if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1):
            return True                        # out of the cabinet: daylight
        n = cells.get(p)
        if n is not None and n.split("[")[0] not in ok:
            return False
        p = (p[0] + dx, p[1] + dy, p[2] + dz)
    return False


@pytest.mark.parametrize("path", CONFIGS, ids=[Path(p).stem for p in CONFIGS])
def test_every_score_lamp_can_be_seen_from_the_front(path):
    """THE READOUT IS THE GAME. A machine whose result nobody can see has not told anybody
    anything, however correct its circuit is."""
    cfg, c, cells, box = _build(path)
    facing = c.meta["facing"]
    lamps = [tuple(q) for q in c.meta.get("outputs") or []
             if cells.get(tuple(q), "").split("[")[0] == "redstone_lamp"]
    if not lamps:
        pytest.skip(f"{cfg['name']} has no lamp readout")
    blind = [p for p in lamps if not _sees_out(cells, box, p, facing)]
    assert not blind, f"{cfg['name']}: {len(blind)} of {len(lamps)} score lamps are walled in"


@pytest.mark.parametrize("path", CONFIGS, ids=[Path(p).stem for p in CONFIGS])
def test_every_input_can_be_reached_from_the_front(path):
    """A target you cannot shoot and a button you cannot see are not inputs.

    `aim` and `striker` take an ARROW, so this is literally a question about the flight path;
    `pair`, `starter`, `pattern` and `counter` take a hand, and a hand needs the same clear line.
    """
    cfg, c, cells, box = _build(path)
    facing = c.meta["facing"]
    ins = [tuple(q) for q in c.meta.get("inputs") or []]
    assert ins, f"{cfg['name']} has no input at all"
    blind = [p for p in ins if not _sees_out(cells, box, p, facing)]
    assert not blind, f"{cfg['name']}: {len(blind)} of {len(ins)} inputs cannot be reached"


@pytest.mark.parametrize("path", CONFIGS, ids=[Path(p).stem for p in CONFIGS])
def test_opening_the_front_did_not_put_a_wire_where_a_hand_can_reach_it(path):
    """The ring is a wall for a reason and the window is a hole in it, so this is the price of the
    fix and it has to be paid explicitly: no wire, repeater, comparator or torch may have a clear
    line out of the front. `_ring` already reports the cells it walls AROUND; this asks the same
    question of everything the window newly exposed."""
    cfg, c, cells, box = _build(path)
    facing = c.meta["facing"]
    # **SIGHT AND REACH ARE DIFFERENT QUESTIONS AND THE PANE IS THE WHOLE DIFFERENCE.** A lamp
    # behind glass is visible and a wire behind glass is not reachable, so this walk is the strict
    # one: AIR only. That is what makes the glazed window a shopfront rather than a hole.
    loose = [p for p, n in cells.items()
             if n.split("[")[0] in park_games.MACHINE
             and _sees_out(cells, box, p, facing, through=set())]
    assert not loose, f"{cfg['name']}: {len(loose)} machine cells are exposed through the window"


@pytest.mark.parametrize("path", CONFIGS, ids=[Path(p).stem for p in CONFIGS])
def test_the_control_is_at_eye_level_and_not_on_the_roof(path):
    """**A CONTROL ON THE LID IS ABOVE A STANDING PLAYER'S EYE.** A player's eye is 1.62 above the
    floor they stand on, which is the console's own base course; the lid's top face is two courses
    over that. Every control now sits ON THE FRONT at the machine course - one course up, dead in
    the eye line - and this pins it, because "it is reachable" was true of the old placement too
    and it was still unplayable."""
    cfg, c, cells, box = _build(path)
    base = c.world_origin[1]
    hands = [tuple(q) for q in c.meta.get("inputs") or []
             if cells.get(tuple(q), "").split("[")[0] in ("stone_button", "lever")]
    if not hands:
        pytest.skip(f"{cfg['name']} is not operated by hand")
    high = [p for p in hands if p[1] - base > 1]
    assert not high, (f"{cfg['name']}: {len(high)} control(s) sit more than one course above the "
                      f"floor - on the lid rather than on the front")
