"""COVER THE WIRING. One pass, run by every generator that builds a machine.

Jack, on the shipped park: *"we need redstone to be covered, we shouldnt have open ended visible
redstone to players it breaks the experience"*. He is right, and the fault is not in any one
machine - it is that nothing in this pipeline ever asked the question. `audit` asks whether a cell
is legal and supported, `circuit.inspect` asks whether the wiring is sound, `redstone_audit` asks
whether a player can press it and see it happen. **None of them asks whether the player can see the
parts that are supposed to be behind the panel**, and measured across the park's machines the
answer was 900 cells of dust, repeaters, comparators and torches lying on open ground.

THE RULE, and `circuit.visible_redstone` is the contract:

    a player may see INPUTS   - a button, a lever, a plate, a target, a lectern, a hopper's mouth
                     OUTPUTS  - a lamp, a bell, a door, a piston face, a dropper's face
                     STRUCTURE
    and nothing else. Dust, repeaters, comparators and torches are all under a floor, behind a
    panel or inside a casing.

**IT ADDS BLOCKS, AND REPLACES EXACTLY ONE KIND OF THING.** Almost everything it does is drop a
lid into an EMPTY cell, which is what makes it safe to run over a finished build: a design's own
geometry, its signage, its floors and its clearances survive by construction, and the worst a lid
can do is stand where nothing stood before. The single exception is `_soft` - a rug, a railing or a
pane that is the LAST sight line into a machine - and it is documented where it is defined, gated
behind every empty cell having been taken first, and counted separately in the result as `swapped`.

`tests/test_conceal.py` then checks both sides of the pass rather than trusting either half: an
input a player could reach before must still be reachable, and every component's settled state
must be unchanged.

**AND IT IS A FIXPOINT, NOT ONE SWEEP** - the same shape as `Island Night`'s solver. Capping one
cell closes a sight line and can leave a second component that was only reachable through it now
sealed; capping can also open nothing, because filling only ever shrinks the outside set. So it
runs until a round places nothing, and reports how many rounds it took.

THREE THINGS IT REFUSES TO COVER, each of which cost a working machine when it was not refused:

  * **A HOPPER'S MOUTH.** A hopper takes the ball, the coin or the item that IS the input; capping
    the cell above one turns the machine off in the only way a player can see and cannot fix. The
    cell above any hopper is never filled.
  * **THE CELL ABOVE A LIT TORCH.** A torch strongly powers the block above it, so a cap there is
    not a lid - it is a new 15 in the middle of the machine, and it will drive any dust that
    touches it. `ticketing`'s barrier torch pair is two courses from its own lock line and would
    have shorted straight across. The cap goes one course higher and the torch's own cell is
    closed off from the side instead.

  * **A CELL A COMPONENT READS.** A repeater reads its back and a comparator reads its back and
    both sides. An EMPTY cell there delivers nothing - `circuit._aimed` says so in as many words -
    and a block there delivers whatever dust happens to touch it. Capping those turned five casino
    machines off in one pass: every block still legal, supported and affordable, and not one of
    them rolled. Only the cells that would actually be LIVE are refused, because a lid with
    nothing powered touching it reads exactly what the empty cell read, and refusing all of them
    cost sixty-three components their cover for a leak that cannot happen.

**AND A CELL IT MAY NOT CAP IS SEALED AROUND INSTEAD.** Refusing a cell used to end the sweep at
that cell and the sight line simply carried on past it - the casino's bar comparator stayed open to
the sky through the one gap the pass was not allowed to fill, three courses up. The gap becomes a
sealed POCKET, which is the torch chimney generalised to every cell the rules keep hands off.

A cell above a lamp is capped, deliberately and with the trade stated: a `redstone_lamp` is read
from its SIDES here (it stands in a wall or beside a run), not from above, and every generator
that uses one as area lighting rather than as a readout hangs it from a ceiling instead.
"""
from __future__ import annotations

from .. import circuit

# What must never be visible. ONE SOURCE with `circuit.HIDDEN`, so the pass and the test that
# grades it cannot drift - the rule `proportions.measure` and `rubric.score` share, and the absence
# of which is exactly how the `circuits.window` bug survived: the simulator agreed with the build.
HIDE = circuit.HIDDEN

_DIRS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
_STEP = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
_BACK = {"north": "south", "south": "north", "east": "west", "west": "east"}
_LEFT = {"north": "west", "south": "east", "east": "north", "west": "south"}

_TORCH = ("redstone_torch", "redstone_wall_torch")

# A hopper's mouth is an INPUT. See the module docstring.
_OPEN_TOP = ("hopper", "composter", "cauldron", "lectern", "chest", "trapped_chest", "barrel")

# Anything that RADIATES power into whatever touches it, and so into a lid dropped beside it.
_POWERY = {"redstone_wire", "redstone_torch", "redstone_wall_torch", "lever", "redstone_block",
           "observer", "target", "sculk_sensor", "daylight_detector", "trapped_chest",
           "detector_rail", "powered_rail"}

# **THE ONE THING THIS PASS MAY REPLACE, AND IT IS A DOCUMENTED EXCEPTION.** A lid can only be
# dropped into an EMPTY cell, so a sight line arriving through a rug, a railing or a pane cannot be
# closed by adding anything - and those are the last few, after every empty cell has been taken. A
# rug laid over a wire trench is not a rug: the casino's button run cut the floor course and left
# carpet standing on redstone dust, which the game will not even place. Swapping one for the casing
# material IS "behind a panel".
#
# A FENCE GATE AND A TRAPDOOR ARE DELIBERATELY NOT IN IT. Both were, for one edit, and both are
# things a visitor USES - a lane you walk through, a hatch you lift - so swapping one for a wall
# closes it. Nor is a sign, a button, a lever, a plate, a door, a ladder, a lamp, a bell, a barrel,
# a hopper or a lantern: the exception cannot eat an input, an output or a piece of signage.
#
# Measured across every kind in the park it fires ELEVEN times, and every one is named:
#
#   8   rug cells in four casino games, where the button's own run had already cut the floor out
#       from under them
#   2   rails of the colour wheel's bowl, beside the run that lights its pockets
#   1   saloon chair that a SECOND table's pay line was later laid alongside
_SOFT_SUFFIX = ("_carpet", "_pane", "_fence", "_slab", "_stairs")
_SOFT_EXACT = {"snow", "moss_carpet", "glass", "tinted_glass", "iron_bars"}


def _soft(name: str) -> bool:
    return name in _SOFT_EXACT or name.endswith(_SOFT_SUFFIX)


def _read_cells(name: str, facing: str):
    """The cells this component READS, and which a lid would therefore feed with stray power.

    A REPEATER READS ONLY ITS BACK. Its sides matter for LOCKING and a lock comes from another
    repeater or comparator, never from a plain block - so a lid beside a repeater is free, and
    forbidding it cost six of them their cover in the ticket gates for nothing.
    A COMPARATOR READS ITS BACK AND BOTH SIDES, and all three have to stay as they were.
    """
    if facing not in _STEP:
        return ()
    if name == "repeater":
        return (_STEP[_BACK[facing]],)
    left = _LEFT[facing]
    return (_STEP[_BACK[facing]], _STEP[left], _STEP[_BACK[left]])


def _live(w, cells, q, ignore) -> bool:
    """Would a plain block at `q` be carrying power - is anything live touching it.

    **A REPEATER OR COMPARATOR BESIDE A CELL DELIVERS NOTHING TO IT.** They drive the ONE cell they
    face and nothing else - `circuit._aimed`'s whole rule, and the reason they are used to isolate
    one line from another. Counting a neighbouring comparator as live whichever way it points
    refused a lid in the gap between every pair of the prize counter's stock readers, where a block
    reads exactly zero. Everything that RADIATES counts wherever it sits.
    """
    for dx, dy, dz in _DIRS:
        nb = (q[0] + dx, q[1] + dy, q[2] + dz)
        if nb == ignore:
            continue
        n = cells.get(nb)
        if n is None:
            continue
        if n in ("repeater", "comparator"):
            d = _STEP.get(w.cells[nb][1].get("facing", "north"))
            if d and (nb[0] + d[0], nb[1] + d[1], nb[2] + d[2]) == q:
                return True
            continue
        if n in _POWERY or n.endswith("_button") or n.endswith("_pressure_plate"):
            return True
    return False


def _names(w) -> dict:
    return {p: v[0] for p, v in w.cells.items()}


def visible(w, extra_opaque=()) -> list:
    """The wiring cells a player can currently see, in this `World`."""
    return [p for p, _n in circuit.visible_in(_names(w), extra_opaque)]


def conceal(w, opaque: str, protect=(), rounds: int = 12, **props) -> dict:
    """Cap every sight line into the wiring with `opaque`.

    `protect` is cells the caller knows a player must be able to occupy or reach through - a
    doorway, a queue lane, the cell in front of a button. Nothing is placed in one, and a component
    that is still visible only through a protected cell is REPORTED rather than silently left: a
    concealment that quietly gives up is the "does nothing, quietly" failure this repo keeps
    writing rules about.

    Returns {"placed", "rounds", "left"} - `left` being the cells it could not close.
    """
    protect = {tuple(p) for p in protect}
    placed = 0
    used = 0
    swapped = 0
    # **SOFT REPLACEMENT IS A LAST RESORT, NOT A FIRST MOVE.** Adding a lid is free; swapping a
    # railing for a wall changes how the thing LOOKS, so it happens only once every empty cell has
    # been taken and a sight line is still open. `soft` flips on the first round that places
    # nothing, which is exactly the round the pass used to give up on.
    soft = False
    for used in range(1, rounds + 1):
        cells = _names(w)
        air = circuit.outside(cells)
        # Cells that must never take a cap, derived fresh each round because the geometry moves.
        forbid = set(protect)
        for pos, name in cells.items():
            if name in _OPEN_TOP:
                forbid.add((pos[0], pos[1] + 1, pos[2]))
            if name in _TORCH:
                # THE CELL ABOVE A LIT TORCH IS A POWER SOURCE, NOT A LID. See the docstring.
                forbid.add((pos[0], pos[1] + 1, pos[2]))
            if name == "hopper":
                # **A HOPPER BESIDE A POWERED BLOCK IS A LOCKED HOPPER**, and `circuit` has no
                # entities, so it cannot see one: nothing in the simulator would report a ticket
                # slot that has stopped taking tickets. `ticketing._torch_pair` designed this out
                # by hand - "which is why none of this is visible from the lane" - and a lid dropped
                # beside a hopper into a live cell puts it straight back. Only LIVE cells are
                # refused; a plain block against a hopper is a wall.
                for dx, dy, dz in _DIRS:
                    q = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
                    if q not in cells and _live(w, cells, q, None):
                        forbid.add(q)
            if name in ("repeater", "comparator"):
                # **A LID IS A CONDUCTOR, AND A CONDUCTOR AT AN INPUT IS A SHORT.** A repeater
                # reads whatever is behind it and a comparator reads its back and both sides; an
                # EMPTY cell there delivers nothing (`circuit._aimed` says so in as many words),
                # and a block there delivers whatever dust happens to touch it. Capping those
                # cells turned five casino machines off in one pass - every one of them still
                # audited clean, still cost the same, and no longer rolled. The front is fine:
                # driving a solid block is what a repeater is for.
                facing = w.cells[pos][1].get("facing", "north")
                for d in _read_cells(name, facing):
                    q = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
                    # ...and only where the lid would actually be LIVE. A block in a read cell
                    # with nothing powered touching it reads exactly what the empty cell read -
                    # zero - so refusing every one of them cost sixty-three components their cover
                    # for a leak that could not happen. What matters is a lid bridging a live run
                    # into an input, which is what turned five casino machines off in one pass.
                    if _live(w, cells, q, pos):
                        forbid.add(q)
        wanted = [p for p, _n in circuit.visible_in(cells)]
        if not wanted:
            break
        seen_wanted = set(wanted)
        this = 0
        for x, y, z in wanted:
            for dx, dy, dz in _DIRS:
                q = (x + dx, y + dy, z + dz)
                if q in forbid or q not in air:
                    continue
                if q in cells:
                    # THE ONE REPLACEMENT, and only as a last resort - see `_soft`.
                    if not soft or not _soft(cells[q]) or cells[q] == opaque:
                        continue
                    swapped += 1
                w.put(q[0], q[1], q[2], opaque, **props)
                cells[q] = opaque
                this += 1
        # **A CELL THAT MAY NOT TAKE A LID IS SEALED AROUND INSTEAD.** A comparator's own side is
        # forbidden - a block there would feed it - so capping stops dead at that cell and the
        # sight line simply carries on past it: the casino's bar comparator was open to the sky
        # through the one gap the pass was not allowed to fill, three courses up. Making that gap a
        # sealed POCKET closes it without putting anything where the machine reads. It is the
        # torch chimney below, generalised to every cell the rules keep hands off.
        for x, y, z in wanted:
            for dx, dy, dz in _DIRS:
                q = (x + dx, y + dy, z + dz)
                if q in cells or q not in air or q not in forbid or q in protect:
                    continue
                for ex, ey, ez in _DIRS:
                    r = (q[0] + ex, q[1] + ey, q[2] + ez)
                    if r in cells or r in forbid or r in protect or r == (x, y, z):
                        continue
                    w.put(r[0], r[1], r[2], opaque, **props)
                    cells[r] = opaque
                    this += 1

        # **A TORCH IS SEALED WITH A CHIMNEY, NOT A LID.** Its own cap is forbidden above, so the
        # cell above it stays open and the torch stays visible for ever - the "does nothing,
        # quietly" ending. Ringing that cell and roofing it one course higher makes it a sealed
        # pocket the outside cannot reach, with air still directly over the torch and no new 15
        # anywhere in the machine.
        for pos, name in list(cells.items()):
            if name not in _TORCH or pos not in seen_wanted:
                continue
            a = (pos[0], pos[1] + 1, pos[2])
            if a in cells:
                continue
            # **AND THE ROOF OF THE CHIMNEY NEEDS SOMETHING TO HOLD ON TO.** A lid one course over
            # an air gap touches the four walls only DIAGONALLY, so the first version shipped the
            # safe in five pieces - one building and four single blocks hanging over its torches.
            # 6-connectivity again, and the audit's component count was the only thing that saw it.
            # The ring is carried up a course with the lid, so every cell has a face neighbour.
            ring = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)]
            want = [(a[0] + dx, a[1], a[2] + dz) for dx, _dy, dz in ring]
            want += [(a[0] + dx, a[1] + 1, a[2] + dz) for dx, _dy, dz in ring]
            want.append((a[0], a[1] + 1, a[2]))
            for q in want:
                if q == pos or q in cells or q in protect:
                    continue
                w.put(q[0], q[1], q[2], opaque, **props)
                cells[q] = opaque
                this += 1
        placed += this
        if not this:
            if soft:
                break
            soft = True
    left = visible(w)
    return {"placed": placed, "swapped": swapped, "rounds": used, "left": left}
