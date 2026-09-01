"""Every machine on the island, inspected and CENSUSED, in one command.

    python tools/redstone_audit.py                       every shipped design that holds redstone
    python tools/redstone_audit.py "Assay Office"        one design, by name
    python tools/redstone_audit.py --plan park_left      every module of a plan, in build order
    python tools/redstone_audit.py --all                 include designs with no redstone in them
    python tools/redstone_audit.py --quiet               findings only, no census

WHY THIS EXISTS, AND WHY IT IS TWO REPORTS RATHER THAN ONE.

`circuit.inspect` answers *is there anything obviously wrong with this wiring* and it has been
callable per design since the simulator was written - but nothing ever ran it over the FOLDER, so
seven real faults sat in the shipped park across three zones and were found by a human reading a
render. That is the first half, and it is cheap: one command over `out/`.

The second half is the one no existing tool asked at all. A machine can be electrically perfect
and still be unplayable, because a player cannot see electricity. The complaint that produced this
file was *"majority of redstone appears to be broken or flawed or very simple and wont do as
expected"*, and the "very simple" half is not a circuit fault - it is a machine with one hidden
button and one lamp, which from the player's side is a wall you press while nothing legible
happens. So every design is also counted:

    INPUTS       what a player can DO to it - a button, a lever, a plate, a target to shoot,
                 a lectern to turn, a sensor that hears them. Zero inputs is an ornament.
    INDICATORS   what a player can SEE it do - lamps, a bell, a note block, a payout dropper,
                 a door, a piston. One indicator is not a readout.
    SIGNAGE      whether it says what it is and what it pays. A game nobody can work out how to
                 play is an empty structure, and this repo has shipped several.

**THE CENSUS IS DELIBERATELY NOT A SCORE.** It is a table you read, exactly as `tools/corpus.py`
refuses to rank the outside builds it measures - turning it into a number would reproduce the
failure the panel review exists to catch, where a build measures well and cannot be played. What
it does do is name the thin machines out loud, on the same two rules the arcade was written under:
a machine with no input is not a machine, and a machine with one indicator has no readout.

WHAT IT CANNOT SEE, stated because a tool trusted past its limits is worse than none:

  * **It does not run the contracts.** `tests/test_arcade.py` and `tests/test_casino.py` drive each
    machine through the simulator and assert what it promises; that needs a promise written down
    and it belongs in the suite. This is the cheap check that can run on ANY design, including the
    ones nobody wrote a contract for.
  * **It has no entities.** A `target` with nothing to shoot at it and a hopper nobody loads look
    exactly like ones that work.
  * **A finding near the model's own edge may be a cropping artifact** and is marked, the same
    allowance `circuit.near_edge` makes for a downloaded schematic.
"""
from __future__ import annotations

import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import circuit, nbt, schem                       # noqa: E402


# WHAT A PLAYER CAN DO TO A MACHINE. Split by KIND rather than lumped, because the split is the
# interesting part of the answer: a zone of three targets and no buttons is a shooting gallery and
# a zone of three buttons and no targets is a bank of slot machines, and "6 inputs" says neither.
INPUTS = {
    "button": ("stone_button", "oak_button", "polished_blackstone_button", "spruce_button",
               "birch_button", "jungle_button", "acacia_button", "dark_oak_button",
               "crimson_button", "warped_button", "mangrove_button", "bamboo_button",
               "cherry_button"),
    "lever": ("lever",),
    "plate": ("stone_pressure_plate", "oak_pressure_plate", "spruce_pressure_plate",
              "birch_pressure_plate", "jungle_pressure_plate", "acacia_pressure_plate",
              "dark_oak_pressure_plate", "polished_blackstone_pressure_plate",
              "light_weighted_pressure_plate", "heavy_weighted_pressure_plate",
              "crimson_pressure_plate", "warped_pressure_plate", "mangrove_pressure_plate"),
    "target": ("target",),
    "sensor": ("sculk_sensor",),
    "lectern": ("lectern",),
    "tripwire": ("tripwire_hook",),
    "trapped chest": ("trapped_chest",),
    "daylight": ("daylight_detector",),
}

# WHAT A PLAYER CAN SEE IT DO. A `bell` is here and is worth saying twice: it rings on a signal,
# costs an ingot, and is the only cheap OUTPUT on this economy that a player perceives without
# looking at it. `redstone_lamp` and `note_block` are both `expensive` here (`palette.tier`), which
# is why the generators count them into a `budget` rather than scattering them.
INDICATORS = {
    "lamp": ("redstone_lamp",),
    "bell": ("bell",),
    "note block": ("note_block",),
    "payout": ("dropper", "dispenser"),
    "door": ("iron_door", "iron_trapdoor"),
    "piston": ("piston", "sticky_piston"),
}

WIRING = {
    "wire": ("redstone_wire",),
    "repeater": ("repeater",),
    "comparator": ("comparator",),
    "torch": ("redstone_torch", "redstone_wall_torch"),
    "block": ("redstone_block",),
    "observer": ("observer",),
    "hopper": ("hopper",),
}

_OF = {n: kind for group in (INPUTS, INDICATORS, WIRING) for kind, names in group.items()
       for n in names}


def _short(name: str) -> str:
    return name.split(":")[-1].split("[")[0]


def counts(model) -> collections.Counter:
    """Block names to cell counts.

    **A BLOCK IS A NAME PLUS ITS STATE, SO A TALLY THAT KEYS ON THE NAME MUST ACCUMULATE.** Two
    palette entries of one block at two facings are two entries; written `c[name] = n` the wheel
    appeared to have one comparator where it has six, which was nearly an hour hunting a bug that
    did not exist.
    """
    out = collections.Counter()
    ids = model.ids
    for i in sorted(set(int(v) for v in ids[ids > 0].ravel().tolist())):
        out[_short(nbt.state_name(model.palette[i]))] += int((ids == i).sum())
    return out


def origin_of(side: dict) -> tuple:
    o = side.get("origin") or (0, 0, 0)
    if isinstance(o, dict):
        return (int(o["x"]), int(o["y"]), int(o["z"]))
    return tuple(int(v) for v in o)


class Report:
    """One design's answer, kept as data so a caller can do something else with it."""

    def __init__(self, name: str, model, side: dict):
        self.name = name
        self.side = side
        self.model = model
        self.origin = origin_of(side)
        self.tally = counts(model)
        self.inputs = {k: sum(self.tally.get(n, 0) for n in v) for k, v in INPUTS.items()}
        self.indicators = {k: sum(self.tally.get(n, 0) for n in v) for k, v in INDICATORS.items()}
        self.wiring = {k: sum(self.tally.get(n, 0) for n in v) for k, v in WIRING.items()}
        self.findings = circuit.inspect(model, self.origin) if self.has_redstone else []

    @property
    def has_redstone(self) -> bool:
        return any(self.wiring.values()) or any(self.inputs.values()) \
            or self.indicators["lamp"] or self.indicators["payout"]

    @property
    def n_inputs(self) -> int:
        return sum(self.inputs.values())

    @property
    def n_indicators(self) -> int:
        return sum(self.indicators.values())

    @property
    def real(self) -> list:
        """Findings that are not the informational quasi-connectivity line.

        QC is MODELLED, not merely warned about, so its line is a note about which cells depend on
        a mechanic most people do not expect - and on a piston machine it fires on every cell of a
        build that demonstrably works. Counting it as a fault is how a checker stops being read.
        """
        return [f for f in self.findings if f[0] != "quasi-connectivity"]

    @property
    def declared(self) -> int:
        """What the design itself says a player interacts with.

        **NOT EVERY INPUT IS A BLOCK.** A plinko ball is thrown into a hopper, a gold pan is a
        shovelful of gravel tipped into a launder, a prize counter is a barrel you open - none of
        those is a button, a lever or a plate, and counting only switches called three real
        machines "nothing to press". The generators already record what the player touches, in
        `inputs`; where they do, that is the better answer, and where they do not, the block count
        is all there is.
        """
        return len(self.side.get("inputs") or [])

    @property
    def thin(self) -> list:
        """The two rules the arcade is written under, applied to whatever is in the folder."""
        out = []
        reachable = self.n_inputs or self.declared
        if self.wiring["wire"] and not reachable:
            out.append("nothing to press: wiring with no input a player can reach")
        seen = self.n_indicators + len(self.side.get("outputs") or [])
        if reachable and seen < 2:
            out.append(f"{self.n_indicators} indicator(s): a player cannot see it happen")
        if reachable and not self.side.get("contract"):
            out.append("no contract recorded - nothing states what it promises")
        return out


# A CAPTURE IS NOT A DESIGN, AND IT CARRIES SOMEBODY ELSE'S REDSTONE. `out/` holds composites and
# world cuts beside the designs, and inspecting one reports every quirk of Jack's own farms as a
# fault of ours - which is the crying-wolf this checker exists not to do. The test is the same one
# `Designs.isDesign` makes in the mod: absence of the CAPTURE markers, never presence of a design
# marker, because a hand-written as-built sidecar has no design marker either.
CAPTURE_MARKS = ("cut_from", "planned_from", "non_air_blocks", "palette_size", "player")


def is_capture(side: dict) -> bool:
    return any(k in side for k in CAPTURE_MARKS)


def is_slice(side: dict) -> bool:
    """A build STEP, not a machine - `mcbuild.layers` cuts one plan into floor/machines/walls.

    **RULE 2, APPLIED TO OUR OWN SLICING: verify in CONTEXT, never in isolation.** Every circuit
    that crosses a layer boundary is cut there, so the wire under the floor reads as dust with no
    source and the dropper above it reads as unwired. Inspecting the four layers of one park zone
    reported 301 such findings and not one of them was a defect. The whole is `<prefix> Complete`
    and that is what gets inspected.
    """
    return bool(side.get("slice"))


def load(name: str, folder: str) -> Report | None:
    lit = os.path.join(folder, name + ".litematic")
    side = os.path.join(folder, name + ".scan.json")
    if not os.path.exists(lit) or not os.path.exists(side):
        return None
    with open(side, encoding="utf-8") as f:
        meta = json.load(f)
    return Report(name, schem.load(lit), meta)


def names_in(folder: str) -> list:
    return sorted(f[:-len(".litematic")] for f in os.listdir(folder)
                  if f.endswith(".litematic")
                  and os.path.exists(os.path.join(folder, f[:-len(".litematic")] + ".scan.json")))


def plan_names(plan: str, folder: str) -> list:
    path = plan if os.path.exists(plan) else os.path.join(folder, "plans", plan + ".json")
    with open(path, encoding="utf-8") as f:
        return [m["name"] for m in json.load(f)["modules"]]


def _row(r: Report) -> str:
    ins = ", ".join(f"{n}x {k}" for k, n in r.inputs.items() if n) or "-"
    outs = ", ".join(f"{n}x {k}" for k, n in r.indicators.items() if n) or "-"
    wire = ", ".join(f"{n} {k}" for k, n in r.wiring.items() if n) or "-"
    lines = [f"  {r.name}   [{r.side.get('kind', r.side.get('generated_by', '?'))}]",
             f"      press   {ins}",
             f"      see     {outs}",
             f"      wiring  {wire}"]
    if r.side.get("contract"):
        lines.append(f"      says    {r.side['contract']}")
    if r.declared and not r.n_inputs:
        lines.append(f"      touch   {r.declared} declared input(s) that are not a switch - "
                     f"a ball, a shovelful, a barrel")
    if r.side.get("signed") is False:
        lines.append("      SIGNAGE a sign this design meant to place was refused")
    for t in r.thin:
        lines.append(f"      THIN    {t}")
    for kind, pos, detail in r.findings:
        edge = " (at the model's own edge)" if circuit.near_edge(r.model, r.origin, pos) else ""
        lines.append(f"      {'NOTE' if kind == 'quasi-connectivity' else 'FAULT'}   "
                     f"{kind} at {pos}{edge} - {detail}")
    return "\n".join(lines)


# `out/` is where every design this project ships lands, next to its sidecar. Not read from
# `profile.yaml`: that names the SCHEMATICS folder the game loads, which also holds captures and
# scratch fills, and this is a question about designs.
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def main(argv: list) -> int:
    folder = OUT
    quiet = "--quiet" in argv
    everything = "--all" in argv
    argv = [a for a in argv if a not in ("--quiet", "--all")]
    if "--plan" in argv:
        i = argv.index("--plan")
        wanted = plan_names(argv[i + 1], folder)
        argv = argv[:i] + argv[i + 2:]
    elif argv:
        wanted = list(argv)
    else:
        wanted = names_in(folder)

    reports, missing, captures = [], [], []
    for name in wanted:
        r = load(name, folder)
        if r is None:
            missing.append(name)
        elif (is_capture(r.side) or is_slice(r.side)) and not everything:
            captures.append(name)
        elif r.has_redstone or everything:
            reports.append(r)

    faults = [r for r in reports if r.real]
    thin = [r for r in reports if r.thin]
    print(f"redstone audit: {len(reports)} design(s) with redstone in {folder}")
    if missing:
        print(f"  ({len(missing)} named design(s) not in the folder: {', '.join(missing[:4])})")
    if captures:
        print(f"  ({len(captures)} capture(s)/build slice(s) skipped - not whole machines; "
              f"--all to see)")
    print(f"  {sum(len(r.real) for r in faults)} fault(s) across {len(faults)} design(s); "
          f"{len(thin)} thin")
    print()
    for r in reports:
        if quiet and not r.real:
            continue
        print(_row(r))
        print()

    tot_in = collections.Counter()
    tot_out = collections.Counter()
    for r in reports:
        tot_in.update({k: v for k, v in r.inputs.items() if v})
        tot_out.update({k: v for k, v in r.indicators.items() if v})
    print("across every design counted")
    print("  press  " + (", ".join(f"{n}x {k}" for k, n in tot_in.most_common()) or "-"))
    print("  see    " + (", ".join(f"{n}x {k}" for k, n in tot_out.most_common()) or "-"))
    # A NON-ZERO EXIT IS FOR CI, NOT FOR THE READER: a fault is a fault, thinness is a judgement.
    return 1 if faults else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
