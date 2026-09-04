"""THE PARK'S GRAND CENTREPIECE: a five-tier monument, ~50 courses, read from three islands.

**WHY THIS EXISTS.** The first centre of the entrance zone was rejected as *"just a bunch of
shops"* - a plane of equal-sized boxes with nothing to walk towards. A zone needs ONE thing that
is unmistakably more important than everything else in it, and the only way voxels say IMPORTANT
is HEIGHT and TIERS: a base you climb, a podium you read, a colonnade you see through, a shaft
that tapers, and a figure on top. Each tier is narrower and taller than the one below, so the
silhouette converges to a point and the eye is carried up it from forty blocks away.

    1  STEPPED BASE   four concentric discs, 29 across, two-cell treads you can sit on
    2  PODIUM         a drum with pilasters, RECESSED inscription panels, moulded cap and base
    3  COLONNADE      eight to twelve columns carrying an entablature - THE GAPS ARE THE POINT
    4  SHAFT          a fluted taper with a gilded collar partway up
   4.5 GALLERY        a railed, lit deck on the shaft's own capital, reached by...
    -  THE CLIMB      a portal on the flank, a spiral stair tower, a landing and a fenced bridge
    5  CROWN          a WINGED figure, 21 blocks across, built as one-thick sheets, standing ON
                       the gallery rather than screwed to the tower's tip

**IT IS AN OBSERVATION TOWER AND FOR ONE WHOLE VERSION NOBODY COULD TELL.** Everything above was
built and the verdict from the first person to look at the finished park was that they had no
idea what the centrepiece was or what it was for. Two separate faults, and neither is a matter
of taste:

- **THE WAY IN WAS BEHIND THE PODIUM**, diametrically opposite the axis a visitor walks up. A
  feature whose entrance you cannot see does not exist. The stair tower is on the LEFT FLANK now
  (`TURRET_AT`), in silhouette from the approach and clear of the monument's own face; its foot
  is a framed, lit, signed PORTAL (`_portal`) standing on its own forecourt; and the walkway ring
  between the base and the apron's edge is repaved from the front round to that door with a
  gilded dash every third cell (`_approach`), because a plan view is how this park is reviewed
  and paving is the only cue that survives one.
- **AND THE CLIMB COULD NOT BE CLIMBED.** The riser that ties each tread to the last was placed
  one course ABOVE the previous tread - exactly the cell a player standing on it occupies - so
  every step in the flight had a solid block resting on it. The audit, the legality check, the
  connectivity check, the tread-path check and the stair-facing check all passed, because every
  one of them asks about BLOCKS and the failure was in the AIR. `tests/test_monument.py` now
  floods the STANDING space from the portal's own threshold cell and requires the gallery deck
  to be in it - the axolotl's lesson (a flood seeded in the void proves nothing) applied to a
  staircase, and seeded from the door rather than from a cell that happened to work.

So there is a real, findable path: a portal, 39 treads wound round a newel and lit every four
courses (`_turret`), a railed landing with the stairwell left open (`_landing`), a fenced bridge
(`_bridge`), and a railed gallery with lanterns under its own deck, a bell and a plaque naming
what lies which way (`_gallery`).

**THE CROWN IS PLANAR AND THAT IS NOT A STYLE CHOICE.** This repo cannot build volumetric muscle
and has the panel verdicts to prove it: every cat and both bears are retired, and the jaguar at
2.6x and 60,000 blocks failed exactly as the 27-block one did. What voxels render natively is
flat sheets and straight tapers - the two builds players picked out unprompted were an 83-block
wingspan bird and a giraffe's NECK. So the figure is a columnar robed body with SHEET wings: one
cell thick in the d axis, layered with a covert at the shoulder, ribbed with dark feather struts,
and swept so the outline tapers to the tip. No anatomy is attempted anywhere on it.

**A CIRCLE IS A DISTANCE TEST, NEVER AN OUTLINE YOU DRAW** - `civic`'s own rule, and every disc,
ring and band here goes through `civic._disc` / `_cells` / `_annulus` rather than being drawn by
hand. A hand-drawn ring at radius 14 is an octagon that lost.

**A RING IS A COURSE.** `park`'s min-run gate exists because the deck soffit drew 215 trim runs
of which 184 were one or two cells - confetti. A radial moulding is the opposite case: every
stair ring laid below is a CLOSED annulus of sixteen cells or more, continuous the whole way
round, and `_moulding` is the one place that lays one so the count can be asserted rather than
hoped for. The same rule the fountain and the bandstand already follow.

GEOMETRY is `park`'s, imported rather than restated - two modules each owning a copy of "which
way does a stair lean" is how a facing bug becomes two facing bugs:

    at       the FRONT-LEFT floor corner, in world coordinates
    facing   the direction the front looks out; -d is the facing direction, +d goes in
    i, d, h  frontage, depth, course;  at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)

Everything radial is placed about a centre at frame coordinates `(c, c)` where `c = PAD_R`, so a
cell is named by its offset `(di, dd)` from the axis - exactly as `civic._fountain` does it. The
FRONT of the monument is `-dd`, which is why the pilaster ring starts at -90 degrees: the front
and back pilasters then exist at every column count, and the inscription has a solid wall behind
it whatever else is configured.

MATERIALS. Everything is `park.LANDS[land]` plus `end_rod` for the finial and `civic._BALUSTRADE`
for the gallery rail, both cheap, spendable and 1.19-legal like every key of every land. No dirt
or grass (CURRENCY on this server), no sand or gravel (they would pour off the corbels into the
void), nothing expensive. The land's `accent` is GILDING and is rationed: capitals, the collar
band, the frieze triglyphs, the mantle, the halo and the finial - about one accent cell in forty.

THE DETAIL VOCABULARY. Stairs already carried every moulding here; the climb adds the two
families this repo's own corpus measurement says it under-uses - `pal["fence"]` as a banister and
a bridge rail, `_BALUSTRADE`'s wall as the gallery rim - which took the whole monument from 12.9%
detail-vocabulary blocks to 14.6%, measured the same way `tools/corpus.py` measures an outside
build. No trapdoors: there was no cell on this design a shutter or a shelf actually belonged on,
and forcing one in for the percentage is exactly the "move a palette number" mistake this repo's
own notes on the deck gallery and the deck soffit already recorded and reversed.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .civic import (
    _BALUSTRADE, _Plaques, _annulus, _cells, _d_dir, _disc, _face_out_radial, _i_dir, _lamp_post,
    _pane_props, _put_free, _slab, _stair,
)
from .park import LANDS, SIGN_WIDTH, _BACK, _STEP, _Frame
from .vertical import Ctx, World

MONUMENT = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "monument",
    "facing": "east",
    "land": "midway",
    "title": None,              # what the inscription reads
    "lines": None,              # the rest of the inscription, three lines
    "columns": 8,               # the colonnade: eight to twelve, and EVEN (see _ring_points)
    "wings": 10,                # the crown's half-span, so the wingspan is 2*wings + 1
    "viewpoints": None,         # what the gallery plaque names, and which way each lies
    "seed": 0,
    "sign": True,
}

# WHAT YOU CAN SEE FROM THE TOP, which is the reward the plaque promises and the only thing on
# the gallery that could not have been guessed from the ground. The three islands run along Z -
# left is NORTH (the frontier), right is SOUTH (the hollow) - and the gate is on the midway's
# west edge with the big wheel on its east, so these are WORLD directions and do not move when
# the monument's own `facing` does. Overridable, because a monument in another park looks out
# on other things.
VIEWPOINTS = ("N THE FRONTIER", "S THE HOLLOW", "W THE GATE", "E THE BIG WHEEL")

# ---- the tiers, in courses above the plaza. Stated once, here, because every one of them is
# read by two or three stages and a height that drifts between them is a floating cornice.
STEP_R = (14, 12, 10, 8)        # h = 0, 1, 2, 3 - two-cell treads, so each ring is a seat
PAD_R = STEP_R[0] + 2           # the paving the whole thing stands on
POD_R = 7                       # the dado drum
PLI_R = 8                       # the plinth, one proud of the dado
CAP_R = 9                       # the podium cap and the colonnade's plate
COL_R = 7                       # the column ring; its 3x3 bases reach 8.49, inside CAP_R

H_PLINTH = 4                    # the proud base
H_FLARE = 5                     # the flare up to the dado
H_DADO0, H_DADO1 = 6, 10        # the dado, five courses
H_PANEL0, H_PANEL1 = 8, 9       # the recessed inscription panels
H_PODCORN = 11                  # the podium's corbelled cornice
H_CAP = 12                      # the cap: the colonnade floor
H_COLBASE = 13
H_COL0, H_COL1 = 14, 18         # the column shafts - five clear courses of OPENING
H_CAPITAL = 19
H_PLATE = 20                    # the architrave: one plate, so the colonnade cannot float
H_FRIEZE = 21
H_CORNICE = 22
H_COPE = 23

H_SHAFT0 = 13                   # the shaft starts on the cap and rises through the colonnade
H_COLLAR = 27                   # the moulded collar: corbel, band, return
H_TAPER0, H_TAPER1 = 29, 36     # the upper, narrower shaft
H_SHAFTCAP = 37
H_ABACUS = 38                   # the shaft's own capital

# ---- tier 4.5: THE GALLERY, because a plaque that says "the view is free" has to mean it. It
# sits on the abacus - one clear course above the shaft cap, safely below the crown - so the
# crown reads as a figure STANDING on the tower rather than a finial screwed to its tip.
# GAL_R WAS 4 AND A FOUR-RADIUS DECK IS A LEDGE. Read from the plaza forty courses down, the
# gallery has to be a PLACE - the crown's own plinth eats the middle nine cells and four lamps
# take four more, so at r=4 there were twelve cells a visitor could stand on and the deck read as
# a collar round the shaft. At r=5 there are thirty-six, the corbel throws a real shadow line,
# and four lanterns hang UNDER it, which is the one cue that says "occupied" from below.
GAL_R = 5
H_GALLERY = H_ABACUS + 1        # the floor you actually stand on
H_GALLERY_RAIL = H_GALLERY + 1  # the balustrade course
FIG0 = H_GALLERY_RAIL + 1       # the crown's own floor, one clear course above the rail
# NOTHING MAY HANG OVER THE DECK AT HEAD HEIGHT. A visitor standing on the gallery floor occupies
# FIG0-1 and FIG0, so the crown's wings start one course higher than its own feet - built from
# FIG0 the wing tips at t=2 and t=4 sat exactly where a head goes, on the only two cells the
# bridge arrives across.
WING_LO = FIG0 + 1

# THE STAIR TOWER IS ON THE LEFT FLANK, NOT BEHIND THE PODIUM, and that is the whole of this
# design's legibility. Shipped once at (0, CAP_R+6) - dead astern, diametrically opposite the way
# a visitor walks up - and the verdict was that nobody could tell the monument was climbable at
# all. On the flank axis it stands clear of the monument's own face (a tower in FRONT of the
# podium hides the inscription, which is the other thing the front is for), it is in silhouette
# from the moment you start walking, and its portal faces the plaza.
#
# CAP_R+5 = 14 is not a taste: at 14 both of the turret's cardinal outriggers - the banister at
# td-2 and the lit pedestal at td+2 - land at |offset| 12 and 16, inside the apron and inside the
# module's own 33x33 footprint. At 15 the outer one lands at 17 and hangs off the plot.
TURRET_D = CAP_R + 5
TURRET_AT = (-TURRET_D, 0)
# THE _SPIRAL INDEX OF THE FIRST TREAD, chosen so the flight starts on the cell nearest the
# plaza: `_SPIRAL[6]` is (0,-1), one step toward the front, which is where the portal opens.
TURRET_PHASE = 6
PORTAL_D = -3                   # the portal's own dd - three cells in front of the newel
PORTAL_I = TURRET_AT[0] - 1     # ...and its doorway column, one out from the newel

MIN_HEIGHT = 45                 # asserted: below this it is a bollard, not a monument
MIN_WINGSPAN = 15               # asserted: below this the wings read as shoulders
MIN_RING = 3                    # a moulding ring shorter than this is confetti, not a course
MIN_CLIMB = 30                  # asserted: a "climb" under this many treads is a doorstep


# ------------------------------------------------------------------ radial helpers

def _band(r0, r1):
    """Every cell with r0 < distance <= r1, in a stable order. A BAND, not a shell.

    `civic._border` is inside-with-a-neighbour-outside, which is right for a roof ring and wrong
    for anything that has to be watertight or continuous: at radius eight it skips its own
    diagonals. A band is the full set and cannot be stepped over.
    """
    inner = set(_cells(0, r0, _disc))
    return [t for t in _cells(0, r1, _disc) if t not in inner]


def _shell(r):
    """The one-cell skin of a disc, ordered ROUND THE RING rather than by row.

    The order is what makes bays derivable: the pilasters land on it by index, and the panel
    between two pilasters is a contiguous slice of it. Sorted by row instead, a "bay" is a set of
    cells scattered over half the drum.
    """
    inside = set(_cells(0, r, _disc))
    ring = [t for t in inside
            if any((t[0] + ux, t[1] + uz) not in inside
                   for ux, uz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    return sorted(ring, key=lambda t: math.atan2(t[1], t[0]))


def _inward(di, dd):
    """The neighbour one step toward the axis, along whichever axis dominates.

    A recessed panel is a REAL recess - the skin cell is left out and this cell is what you see
    through the gap - so it has to be a cell that is genuinely behind the skin. On a disc's
    one-cell shell it always is: a shell cell sits at radius r-ish and this one at r-1-ish, which
    is never itself on the shell.
    """
    if abs(di) >= abs(dd):
        return (di - (1 if di > 0 else -1), dd)
    return (di, dd - (1 if dd > 0 else -1))


def _ring_points(r, n):
    """`n` points on a circle of radius `r`, STARTING AT THE FRONT and never outside the disc.

    Two things this has to get right, both of which shipped wrong somewhere in this repo first:

    THE FIRST POINT IS THE FRONT (-dd). Started at angle zero the front is a point only when n is
    a multiple of four, so at ten columns there is no column, and no pilaster, on the axis a
    visitor walks up - and the inscription, which needs a solid wall behind it, has nowhere to go.
    Started at -90 with an even `n`, the front AND the back are both points at every count.

    AND A POINT MUST LIE INSIDE THE DISC IT STANDS ON. Rounded off the circle, ten points at
    radius seven put two of them at 7.28, whose 3x3 base reaches 8.6 - past the cap that carries
    it, so the moulding ships as floating stairs. The radius is walked in rather than the point
    being clamped, so the ring stays a circle instead of a circle with two dents in it.

    A collapse is an ERROR, not a smaller colonnade: `civic._bandstand` shipped every square
    plan with four columns under a contract that says eight, because a set literal de-duplicated
    them in silence and the only witness was a number in its own sidecar.
    """
    pts, seen = [], []
    for k in range(n):
        a = -math.pi / 2 + 2 * math.pi * k / n
        rr = float(r)
        while True:
            p = (int(round(rr * math.cos(a))), int(round(rr * math.sin(a))))
            if p[0] * p[0] + p[1] * p[1] <= r * r or rr <= 1.0:
                break
            rr -= 0.25
        if p in seen:
            raise ValueError(f"{n} points collapse onto {len(seen)} at radius {r}")
        seen.append(p)
        pts.append(p)
    return pts


def _put(w, f, c, di, dd, h, block, **props):
    w.put(*f.at(c + di, c + dd, h), block, **props)


def _fence_props(f, along_i=False, along_d=False):
    """A fence's connection flags, set ALONG the run it belongs to.

    Exactly `_pane_props`' rule and exactly its reason - a fence with every side false renders as
    a lone post rather than as a rail - except that a rail RING turns corners, so the two axes are
    asked for separately and a corner asks for both.
    """
    pr = {"north": "false", "south": "false", "east": "false", "west": "false",
          "waterlogged": "false"}
    if along_i:
        pr[_i_dir(f, 1)] = "true"
        pr[_i_dir(f, -1)] = "true"
    if along_d:
        pr[_d_dir(f, 1)] = "true"
        pr[_d_dir(f, -1)] = "true"
    return pr


def _fill(w, f, c, r, h, block):
    for (di, dd) in _cells(0, r, _disc):
        _put(w, f, c, di, dd, h, block)
    return len(_cells(0, r, _disc))


def _moulding(w, f, pal, c, r, h, half):
    """One closed ring of stairs leaning INTO the mass - a flare when `half='bottom'`, a corbel
    when `half='top'`. THE RING IS THE COURSE, and it is asserted to be a real one.

    A stair's tall side is its `facing`, so a moulding faces inward: the full half against the
    wall, the low half hanging out over air. Our renderer draws both directions identically,
    which is exactly why this is one function rather than a judgement made at nine call sites.
    """
    ring = _annulus(r, _disc)
    assert len(ring) >= MIN_RING, f"moulding ring at r={r} is {len(ring)} cells, not a course"
    for (di, dd) in ring:
        _stair(w, f, c + di, c + dd, h, pal["stair"], _BACK[_face_out_radial(f, di, dd)], half)
    return len(ring)


# ------------------------------------------------------------------ tier 1: the stepped base

def _base(w, f, pal, c, seed):
    """Four concentric steps with a two-cell tread each, on a paved apron.

    TWO CELLS, NOT ONE. A one-cell tread is a kerb you trip over; two is somewhere to sit, which
    is what turns the foot of a monument into the place a zone gathers. The rim of each step is a
    ring of stairs so the climb is a half step rather than a wall, and the whole thing is a stack
    of DISCS - the mass under each tread is solid, so nothing anywhere in the base can float.
    """
    spokes = hash01(seed, 7) < 0.5
    n = 0
    for (di, dd) in _cells(0, PAD_R, _disc):
        x, y, z = f.at(c + di, c + dd, -1)
        if spokes and (di == 0 or dd == 0 or abs(di) == abs(dd)):
            blk = pal["accent"] if max(abs(di), abs(dd)) > STEP_R[0] else pal["trim"]
        elif x % 6 == 0 or z % 6 == 0:
            blk = pal["trim"]
        elif (x + z) % 2 == 0:
            blk = pal["ground"]
        else:
            blk = pal["path"]
        w.put(x, y, z, blk)
        n += 1
    for h, r in enumerate(STEP_R):
        rim = set(_annulus(r, _disc))
        for (di, dd) in _cells(0, r, _disc):
            if (di, dd) in rim:
                _stair(w, f, c + di, c + dd, h, pal["stair"],
                       _BACK[_face_out_radial(f, di, dd)])
            else:
                _put(w, f, c, di, dd, h, pal["ground"] if (h % 2 == 0) else pal["path"])
            n += 1
    return n


# ------------------------------------------------------------------ tier 2: the podium

def _podium(w, f, pal, c, say, title, lines, pilasters):
    """A drum with pilasters, recessed panels, and a moulded base and cap.

    THE PANELS ARE A REAL RECESS, not a darker block painted on the skin. The skin cell is left
    out over two courses and the cell BEHIND it takes the dark trim, so the panel carries its own
    shadow - which is the one thing that reads at forty blocks and the one thing a flat colour
    cannot fake. The frame cell either side of every pilaster stays, so the drum reads as bays
    rather than as a slot cut round it.

    AND A BAY TOO SHORT TO PANEL IS LEFT SOLID. At twelve columns the bays are three cells wide
    and two of those are frame, so a panel would be a single dark cell per bay - the deck
    soffit's confetti, in a recess. The gate is on what is PLACED, so a bay is either panelled
    properly or not at all.
    """
    pil = set(pilasters)
    shell = _shell(POD_R)
    idx = {t: k for k, t in enumerate(shell)}
    # THE PILASTER HAS TO BE A CELL OF THE SKIN. `pilasters` comes off the ring at radius POD_R
    # and the skin is what the disc actually rasterises to, so a point can round to a cell just
    # inside it; snapped to the nearest skin cell, a pilaster is always part of the wall it is
    # supposed to be a thickening of.
    seats = []
    for p in pilasters:
        near = min(shell, key=lambda t: (t[0] - p[0]) ** 2 + (t[1] - p[1]) ** 2)
        seats.append(near)
    frame = set()
    for s in seats:
        k = idx[s]
        for j in (k - 1, k, k + 1):
            frame.add(shell[j % len(shell)])

    # ---- the plinth: two courses at PLI_R, the upper one in trim, then the flare
    _fill(w, f, c, PLI_R, 3, pal["ground"])
    _fill(w, f, c, PLI_R, H_PLINTH, pal["trim"])
    _fill(w, f, c, POD_R, H_FLARE, pal["ground"])
    _moulding(w, f, pal, c, PLI_R, H_FLARE, "bottom")

    # ---- the dado
    panels = 0
    bays = []
    for k in range(len(seats)):
        a, b = idx[seats[k]], idx[seats[(k + 1) % len(seats)]]
        span = [shell[(a + j) % len(shell)] for j in range(1, (b - a) % len(shell))]
        bays.append([t for t in span if t not in frame])
    for h in range(H_DADO0, H_DADO1 + 1):
        for (di, dd) in _cells(0, POD_R, _disc):
            _put(w, f, c, di, dd, h, pal["ground"])
        for (di, dd) in shell:
            _put(w, f, c, di, dd, h, pal["wall"])
        for (di, dd) in seats:
            _put(w, f, c, di, dd, h, pal["post"])
        if H_PANEL0 <= h <= H_PANEL1:
            for bay in bays:
                if len(bay) < MIN_RING:
                    continue
                for (di, dd) in bay:
                    del w.cells[f.at(c + di, c + dd, h)]
                    ii, dj = _inward(di, dd)
                    _put(w, f, c, ii, dj, h, pal["trim"])
                    panels += 1

    # ---- the cornice and the cap
    _fill(w, f, c, POD_R, H_PODCORN, pal["trim"])
    _moulding(w, f, pal, c, PLI_R, H_PODCORN, "top")
    _moulding(w, f, pal, c, CAP_R, H_PODCORN, "top")
    _fill(w, f, c, CAP_R, H_CAP, pal["trim"])

    # ---- the inscription, ON A PILASTER. The panels are holes for two courses and the sign's
    # support is checked, not assumed - `park._sign` places NOTHING when the wall behind it has
    # an opening in it, and says nothing about having done so. A pilaster is solid by
    # construction at every course of the dado, and seats[0] is the front one by construction.
    fi, fd = seats[0]
    bi, bd = seats[len(seats) // 2]
    say(w, f, pal, c + fi, c + fd - 1, H_PANEL0, f.facing,
        [title[:SIGN_WIDTH]] + [str(s)[:SIGN_WIDTH] for s in lines[:3]])
    say(w, f, pal, c + bi, c + bd + 1, H_PANEL0, f.back,
        [s[:SIGN_WIDTH] for s in
         ("THE MONUMENT", "", "climb the tower", "view is free")])

    # AND ONE AT EYE LEVEL ON THE FRONT PLINTH, because the inscription is eight courses up and
    # the question it has to answer - what IS this, and what do I do here - is asked by somebody
    # standing at the bottom of the steps. Hung on the plinth's own face, which is solid at every
    # course, rather than on the dado, which is a hole for two of them.
    say(w, f, pal, c, c - PLI_R - 1, H_PLINTH - 1, f.facing,
        ["OBSERVATION", "TOWER", "climb the tower", "view is free"])

    return panels, len(bays)


# ------------------------------------------------------------------ tier 3: the colonnade

def _colonnade(w, f, pal, c, columns, seed):
    """A ring of columns carrying an entablature. THE OPENINGS BETWEEN THEM ARE THE POINT.

    The rule this whole park is built on is that what makes voxels read as architecture is
    REGULARITY AND OPENINGS, NOT DAMAGE - the void tower's first attempt was a sheared jagged
    stub and was rejected on sight as *"a tossed grouping of vague blocks"*. So the columns are
    identical, evenly spaced, and there are five clear courses between the base and the capital
    that you can see the sky through from any angle.

    THE ARCHITRAVE IS ONE SOLID PLATE, and that is structural rather than stylistic. Laid as a
    ring it is a rasterised annulus whose cells meet diagonally in places, six-connectivity does
    not see a diagonal, and the entire crown - shaft, collar, figure and all - hangs off whichever
    fragment happened to touch a column. A plate cannot do that, and the openings are still
    openings: you look through the colonnade from the SIDE, not from above.
    """
    lanterns = 0
    for (di, dd) in _ring_points(COL_R, columns):
        ring3 = [(di + a, dd + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
        for (ii, dj) in ring3:            # the base: a 3x3 ring, three cells to an edge
            _stair(w, f, c + ii, c + dj, H_COLBASE, pal["stair"],
                   _face_out_radial(f, di - ii, dd - dj), "bottom")
        _put(w, f, c, di, dd, H_COLBASE, pal["trim"])
        for h in range(H_COL0, H_COL1 + 1):
            _put(w, f, c, di, dd, h, pal["post"])
        for (ii, dj) in ring3:            # the capital, corbelled back out
            _stair(w, f, c + ii, c + dj, H_CAPITAL, pal["stair"],
                   _face_out_radial(f, di - ii, dd - dj), "top")
        _put(w, f, c, di, dd, H_CAPITAL, pal["accent"])       # gilding, one cell per column

    _fill(w, f, c, CAP_R, H_PLATE, pal["trim"])
    for (di, dd) in _band(POD_R, CAP_R):
        _put(w, f, c, di, dd, H_FRIEZE, pal["wall"])
        _put(w, f, c, di, dd, H_CORNICE, pal["trim"])
        _slab(w, f, c + di, c + dd, H_COPE, pal["slab"], "bottom")
    _moulding(w, f, pal, c, CAP_R + 1, H_CORNICE, "top")

    # TRIGLYPHS OVER THE COLUMNS, which is the whole of the gilding on this tier: a frieze
    # alternating accent all the way round is a hundred cells of yellow and reads as a hazard
    # stripe. One gilded cell over each column's own axis is a rhythm.
    for (di, dd) in _ring_points(CAP_R, columns):
        _put(w, f, c, di, dd, H_FRIEZE, pal["accent"])

    # LANTERNS HANGING IN THE GAPS, never off a column. `hanging=true` wants a FULL block
    # directly above, and the architrave plate is exactly that - which is the other reason it is
    # a plate. A gap cell that a capital moulding already took is SKIPPED rather than overwritten.
    gaps = _ring_points(COL_R, columns * 2)
    for k, (di, dd) in enumerate(gaps):
        if k % 2 == 0:
            continue
        if w.has(*f.at(c + di, c + dd, H_CAPITAL)):
            continue
        _put(w, f, c, di, dd, H_CAPITAL, pal["light"], hanging="true", waterlogged="false")
        lanterns += 1
    return lanterns


# ------------------------------------------------------------------ tier 4: the shaft

def _flutes(r):
    """The skin of a shaft of radius r, in angular order, so alternating it gives VERTICAL
    stripes. Alternated on `(di + dd) % 2` instead it is a checkerboard, which at this scale is
    noise rather than fluting."""
    return sorted(_annulus(r, _disc), key=lambda t: math.atan2(t[1], t[0]))


def _shaft_courses(w, f, pal, c, r, h0, h1):
    """A fluted taper: the core solid, the skin alternating light and dark round the ring.

    The alternation is `wall` against `trim`, NOT against the accent. A gilded flute the whole
    height of the shaft is two hundred cells of yellow and the collar it is supposed to set off
    stops being an event.
    """
    ring = _flutes(r)
    for h in range(h0, h1 + 1):
        for (di, dd) in _cells(0, r - 1, _disc):
            _put(w, f, c, di, dd, h, pal["ground"])
        for k, (di, dd) in enumerate(ring):
            _put(w, f, c, di, dd, h, pal["wall"] if k % 2 == 0 else pal["trim"])
    return (h1 - h0 + 1) * len(_cells(0, r, _disc))


def _shaft(w, f, pal, c):
    """The shaft, with a moulded collar where it steps in.

    A TAPER NEEDS AN EVENT WHERE IT CHANGES. Stepped straight from five across to three, the
    join reads as a mistake - two shafts stacked. The collar is a corbel out, a gilded band and a
    return in, which turns the step into the reason for the step.
    """
    n = _shaft_courses(w, f, pal, c, 2, H_SHAFT0, H_COLLAR - 1)
    _moulding(w, f, pal, c, 3, H_COLLAR - 1, "top")
    for (di, dd) in _cells(0, 3, _disc):
        _put(w, f, c, di, dd, H_COLLAR, pal["accent"] if abs(di) + abs(dd) > 1 else pal["trim"])
    _shaft_courses(w, f, pal, c, 2, H_COLLAR + 1, H_COLLAR + 1)
    _moulding(w, f, pal, c, 3, H_COLLAR + 1, "bottom")
    n += _shaft_courses(w, f, pal, c, 1, H_TAPER0, H_TAPER1)

    # the shaft's own capital: a 3x3 ring of stairs, three cells to an edge, then an abacus
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            if (a, b) == (0, 0):
                _put(w, f, c, 0, 0, H_SHAFTCAP, pal["trim"])
            else:
                _stair(w, f, c + a, c + b, H_SHAFTCAP, pal["stair"],
                       _face_out_radial(f, -a, -b), "top")
    _fill(w, f, c, 2, H_ABACUS, pal["trim"])
    return n


# ------------------------------------------------------------------ tier 4.5: the climb

# The eight offsets of a lighthouse spiral - three cells around a centre post. THE ORDER IS
# CHECKED, NOT ASSUMED: every consecutive pair here differs by exactly one cell on exactly one
# axis, which is what lets each tread's `facing` be asserted the stairhead way - "a flight that
# ascends toward D has every tread facing=D" - even though the direction of travel turns a full
# revolution every eight treads. `tests/test_monument.py` pins the shape, not just the read-out.
_SPIRAL = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _turret(w, f, pal, c, td, h0, h1, phase=0):
    """A detached stair tower on the monument's flank: a newel post with eight treads a
    revolution, every one of them exactly one step and one course from the last.

    **THE RISER GOES UNDER THE NEXT TREAD, NEVER ON TOP OF THE LAST ONE, AND THAT IS THE WHOLE
    DIFFERENCE BETWEEN A STAIRCASE AND A SCULPTURE OF ONE.** A tread and the one before it do not
    share a face - they are one course up and one cell over - so something has to tie them
    together or the spiral audits as thirty-nine floating stairs. The first version put that
    something at the PREVIOUS tread's offset ONE COURSE UP, which is exactly the cell a player
    standing on that tread occupies: every tread in the flight had a solid block resting on it,
    and the climb this monument's own plaque promises **could not be walked at all**. It passed
    every check in the pipeline - legal states, one connected piece, treads a real path, every
    facing correct - because all of those ask about BLOCKS and none of them asks about the air.
    Placed under the NEXT tread instead it ties the same two cells together (it touches the tread
    above it, and the tread beside it at its own course, since two consecutive `_SPIRAL` offsets
    are one step apart - checked, not assumed, at the top of this file) and it is under the stair
    where a riser belongs. `tests/test_monument.py` now floods the STANDING space from the portal.

    `phase` is the `_SPIRAL` index of the first tread, so the flight can be made to start on the
    side the door is on rather than wherever index zero happens to fall.

    THE NEWEL stops one course below the landing, which caps the tower; it is additional rather
    than load-bearing - the risers already chain every tread to its neighbours - but it gives the
    eye something to spiral round and the lamps something to stand on.

    ONLY THE FOUR CARDINAL TREADS CARRY A BANISTER OR A LAMP. Doubling a cardinal offset
    (east -> two east) lands on a cell that shares a face with the tread; doubling a diagonal one
    (south-east -> two south-east) lands on a cell that only touches it at the CORNER, which is
    the same non-adjacency this docstring just paid for once already. **And the FIRST tread gets
    neither**: its outrigger stands in the doorway, one cell in front of the entry tread, which
    is a fence across the only way in.

    A LAMP EVERY FOUR COURSES, NOT EVERY EIGHT. An unlit spiral is a spiral nobody takes, and one
    pedestal a revolution left eleven-course gaps of darkness on a flight forty courses tall.
    """
    treads, rails, lamps, mouth = [], 0, 0, []
    for h in range(h0, h1):
        k = (h - h0 + phase) % 8
        di, dd = _SPIRAL[k]
        ndi, ndd = _SPIRAL[(k + 1) % 8]
        face = _face_out_radial(f, ndi - di, ndd - dd)
        pos = f.at(c + td[0] + di, c + td[1] + dd, h)
        w.put(*pos, pal["stair"], facing=face, half="bottom", shape="straight",
              waterlogged="false")
        treads.append((pos, face))
        # THE LAST TWO TREADS' OWN COLUMNS. The landing floor is one course above the top tread,
        # so it roofs the head of anyone standing on the tread below that one as well: a mouth
        # of one cell let a climber reach the second-from-top step and stop there, with nothing
        # in the build looking wrong. Two is what a spiral's stairwell actually is.
        mouth = ([(di, dd)] + mouth)[:2]
        if h > h0:
            w.put(*f.at(c + td[0] + di, c + td[1] + dd, h - 1), pal["post"])
        if k % 2 == 0 and h > h0:                          # cardinal, and never the entry tread
            oi, od = td[0] + di * 2, td[1] + dd * 2
            if k in (0, 4):                                # a lit pedestal, twice a lap
                w.put(*f.at(c + oi, c + od, h), pal["post"])
                lamps += int(_put_free(w, f, c + oi, c + od, h + 1, pal["light"],
                                       hanging="false", waterlogged="false"))
            else:                                          # the banister, the rest of the lap
                w.put(*f.at(c + oi, c + od, h), pal["fence"],
                      north="false", south="false", east="false", west="false",
                      waterlogged="false")
                rails += 1
    for h in range(h0 - 1, h1):         # the newel, up to the landing it carries
        w.put(*f.at(c + td[0], c + td[1], h), pal["post"])
    return treads, rails, lamps, tuple((td[0] + a, td[1] + b) for (a, b) in mouth)


def _landing(w, f, pal, c, td, h, mouth):
    """The stair's own top platform - five by five, railed, with the stairwell left open.

    **THE STAIRWELL MOUTH IS LEFT EMPTY BY THE LOOP**, never punched afterwards: the last tread
    is one course below this floor, so a player standing on it occupies exactly that column, and
    a platform laid solid over the top of the flight is a ceiling on the last step. Same rule as
    the gallery's rail gap and the podium's panels, for the same reason.

    AND THE RAIL IS ON THE OUTER RING ONLY. Railing the inner ring as well leaves nowhere to
    stand: the platform is three cells across inside its own parapet, and a fence in every one of
    them is a cage. What the outer ring buys is that the walk from the stairwell round to the
    bridge is protected on every side without a single walking cell being blocked.
    """
    floor = rails = 0
    mouth = set(mouth)
    for di in range(td[0] - 2, td[0] + 3):
        for dd in range(td[1] - 2, td[1] + 3):
            if (di, dd) in mouth:
                continue
            _put(w, f, c, di, dd, h, pal["trim"])
            floor += 1
    gate = (td[0] + 2, td[1])           # where the bridge leaves; the rail opens for it
    for di in range(td[0] - 2, td[0] + 3):
        for dd in range(td[1] - 2, td[1] + 3):
            if abs(di - td[0]) != 2 and abs(dd - td[1]) != 2:
                continue
            if (di, dd) == gate:
                continue
            _put(w, f, c, di, dd, h + 1, pal["fence"],
                 **_fence_props(f, along_i=abs(dd - td[1]) == 2, along_d=abs(di - td[0]) == 2))
            rails += 1
    return floor, rails


def _portal(w, f, pal, say, c, td, steps):
    """**THE WAY IN, BUILT AS A DOOR SOMEBODY CAN SEE FROM THE PLAZA.**

    The monument was climbable and unmistakably did not look it: thirty-nine treads, a bridge and
    a railed gallery, and the verdict from someone looking at the finished thing was that they
    could not tell what the structure was for. A feature nobody can find the entrance to does not
    exist, so the entrance is now a piece of architecture in its own right - two jambs, a lintel,
    a signboard above it and a standing lamp on each shoulder - standing on its own forecourt
    three cells in front of the first tread, with its face turned toward the approach.

    IT IS A REAL OPENING, three courses clear, and the walk from it to the first tread is checked
    by the same flood that checks the climb. A framed doorway that is not the way in is worse
    than no doorway at all - it is a sign pointing at a wall.
    """
    i0, i1 = PORTAL_I - 1, PORTAL_I + 1
    dd = PORTAL_D
    for di in (i0, i1):                                     # the jambs
        for h in range(0, 3):
            _put(w, f, c, di, dd, h, pal["post"])
    for di in range(i0, i1 + 1):                            # the lintel, then the signboard
        _put(w, f, c, di, dd, 3, pal["trim"])
        _put(w, f, c, di, dd, 4, pal["wall"])
        _put(w, f, c, di, dd, 5, pal["trim"])
    _put(w, f, c, PORTAL_I, dd, 4, pal["accent"])           # the keystone, gilded
    lamps = 0
    for di in (i0, i1):
        lamps += int(_put_free(w, f, c + di, c + dd, 6, pal["light"],
                               hanging="false", waterlogged="false"))
    # THE BOARD READS FROM THE PLAZA. `f.facing` puts the text on the -dd face and the board
    # itself one course behind it, which is the support `park._sign` checks for.
    say(w, f, pal, PORTAL_I + c, c + dd - 1, 4, f.facing,
        ["CLIMB THE TOWER", f"{steps} steps up", "VIEW FROM", "THE TOP"])
    say(w, f, pal, i0 + c, c + dd - 1, 2, f.facing,
        ["TOWER ENTRANCE", "free to climb", "", ""])
    return lamps


def _gallery(w, f, pal, say, c, viewpoints):
    """THE VIEWING GALLERY the plaque promises: a corbelled ring around the shaft's own capital,
    railed at 1.5 blocks so the view over it is real, lit above AND BELOW, and named.

    THE GAP IN THE RAIL IS LEFT BY THE LOOP, never punched afterwards - the void tower's own
    rule, paid for once already on this file's own colonnade and podium. It falls exactly where
    `_bridge` lands, because both read the same `GAL_R` and `TURRET_AT` rather than one of them
    guessing it.

    **FOUR LANTERNS HANG UNDER THE DECK, and they are the only thing on this monument that says
    "somebody is up there" from the ground.** A rail read from forty courses below is a thin dark
    line; a lit soffit under an overhanging deck is a shape, and the corbel that throws the
    shadow is already built. They hang from the gallery's own floor, which is a full block - a
    lantern under a slab reads as hanging from air, which this repo has shipped once.

    AND THERE IS SOMETHING TO FIND AT THE TOP. A climb whose reward is the same view you could
    infer from the ground is a climb nobody makes twice: the deck carries a bell you can ring and
    a plaque naming what lies which way, both of which need no signal and cannot be got wrong.
    """
    n = _moulding(w, f, pal, c, GAL_R, H_ABACUS, "top")        # corbel: the abacus out to GAL_R
    n += _fill(w, f, c, GAL_R, H_GALLERY, pal["trim"])         # the floor
    rail = _BALUSTRADE.get(pal["ground"], "stone_brick_wall")
    gap = (-GAL_R, 0)
    rails = 0
    for (di, dd) in sorted(_annulus(GAL_R, _disc)):
        if (di, dd) == gap:
            continue
        _put(w, f, c, di, dd, H_GALLERY_RAIL, rail)
        _slab(w, f, c + di, c + dd, H_GALLERY_RAIL + 1, pal["slab"], "bottom")
        rails += 1
    lamps = 0
    for (di, dd) in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        if _put_free(w, f, c + di, c + dd, H_GALLERY_RAIL, pal["light"],
                     hanging="false", waterlogged="false"):
            lamps += 1
    under = 0
    for (di, dd) in ((3, 0), (-3, 0), (0, 3), (0, -3)):
        if _put_free(w, f, c + di, c + dd, H_ABACUS, pal["light"],
                     hanging="true", waterlogged="false"):
            under += 1
    # A BELL RINGS ON A RIGHT-CLICK AND NEEDS NOTHING WIRED TO IT, which is why it is here and a
    # note block is not: `palette.tier("note_block") == "expensive"` before anyone even asks what
    # would drive it, and nothing that carries a signal ships from this repo unverified.
    _put(w, f, c, 3, 2, H_GALLERY_RAIL, "bell",
         attachment="floor", facing=f.facing, powered="false")
    say(w, f, pal, c, c + 4, H_GALLERY_RAIL, f.facing,
        ["VIEW FROM THE", "TOP OF THE PARK", "ring the bell", ""])
    say(w, f, pal, c, c - 4, H_GALLERY_RAIL, f.back, list(viewpoints)[:4])
    return n, rails, lamps, under


def _bridge(w, f, pal, c, td, h):
    """A single-file, fenced walkway from the gallery's own rail gap out to the stair tower's
    landing, along the flank axis the tower stands on.

    Both ends are read off `GAL_R` and `td`, never re-typed, which is the same discipline
    `_gallery`'s gap and `_landing`'s rail gate already follow - numbers agreeing by construction
    rather than by two people remembering to keep them in step.
    """
    props = _pane_props(f, along_i=True)
    n = 0
    for k in range(GAL_R, abs(td[0]) - 1):
        _put(w, f, c, -k, 0, h, pal["trim"])
        for dd in (-1, 1):
            w.put(*f.at(c - k, c + dd, h + 1), pal["fence"], **props)
        n += 1
    return n


# ------------------------------------------------------------------ the approach on the ground

def _approach(w, f, pal, say, c, td, steps):
    """The forecourt at the tower's foot, the marked route to it, and the fingerpost that names
    it from the bottom of the front steps.

    **THE ROUTE IS DRAWN ON THE GROUND, because that is the only cue that survives a plan view.**
    Everything else added for legibility - the portal, its lamps, its board - is an elevation
    cue, and the way this park is actually reviewed is from above. The walkway ring between the
    base's lowest step and the apron's edge is repaved from the front round to the door in the
    land's own path block with a gilded dash every third cell, so from overhead there is a line
    leading off the axis a visitor arrives on and ending at a doorway.

    The forecourt is a small rectangle of paving at the tower's foot. It exists because the apron
    is a DISC and the portal is a straight three-cell frame: the outer jamb sits at radius 16.3,
    a third of a block outside the circle, and a jamb standing on nothing is the floating-cell
    failure this repo checks for on every design. It stays inside the module's own 33x33 - the
    furthest cell it reaches is exactly `PAD_R` on both axes.
    """
    yard = 0
    for di in range(td[0] - 2, td[0] + 3):
        for dd in range(PORTAL_D - 3, td[1] + 3):
            if abs(di) > PAD_R or abs(dd) > PAD_R:
                continue
            if _put_free(w, f, c + di, c + dd, -1, pal["path"]):
                yard += 1

    ring = [t for t in _band(STEP_R[0], PAD_R) if t[0] <= 0 and t[1] <= 0]
    ring.sort(key=lambda t: -math.atan2(t[1], t[0]))
    # THE BED IS THE TRIM, NOT THE PATH. Laid in `pal["path"]` the route was only its dashes:
    # the apron is already a checker of ground and path, so a path-coloured ribbon on it is
    # invisible from above and the whole point of drawing it on the ground is lost. The trim is
    # the dark end of the cheap value ladder in every land - 215 points of luminance across five
    # cheap stops, measured across families rather than within one - so a trim ribbon with a
    # gilded dash every third cell is the strongest line this economy can draw.
    for k, (di, dd) in enumerate(ring):
        _put(w, f, c, di, dd, -1, pal["accent"] if k % 3 == 0 else pal["trim"])

    # THE FINGERPOST, at the foot of the front steps and ON the marked route, so the first thing
    # a visitor reads is that there is a tower and it is free.
    fi, fd = -3, -(PAD_R - 1)
    for h in range(0, 3):
        _put(w, f, c, fi, fd, h, pal["post"])
    _put(w, f, c, fi, fd, 3, pal["trim"])
    _put(w, f, c, fi, fd, 4, pal["light"], hanging="false", waterlogged="false")
    say(w, f, pal, c + fi, c + fd - 1, 2, f.facing,
        ["VIEWING TOWER", f"{steps} steps up", "free to climb", "follow the path"])
    return yard, len(ring)


# ------------------------------------------------------------------ tier 5: the crown

def _wing(w, f, pal, c, side, wings, sh):
    """One wing: a ONE-THICK SHEET in the i-h plane, swept up and tapering to the tip.

    This is the whole reason the crown is a winged figure rather than a person. A sheet is what
    this medium renders natively - the sky bird's 83-block wingspan and the giraffe's neck are
    the two builds players picked out unprompted, and both are flat or columnar. A pair of arms
    modelled with mass would be the jaguar's shoulder again.

    THE TAPER IS THE FIGURE. Both edges rise outward and the underside rises faster, so the
    outline converges - a spread wing rather than a rectangle with feathers drawn on it. Every
    column overlaps its neighbour by construction (the top gains at most one course and the
    bottom exactly one), so the sheet is one connected piece and cannot ship as nine slats.

    THE STRUTS ARE WHAT MAKE IT READ AS FEATHERS. Every other column drops two courses further
    and takes the dark trim, so the trailing edge is scalloped and ribbed instead of being a
    straight diagonal cut. A single flat tone at this size is a paper aeroplane.
    """
    n = 0
    for t in range(2, wings + 1):
        k = t - 2
        top = sh + 1 + k // 2
        bot = sh - 5 + k
        tail = bot - 2 if k % 2 == 0 else bot
        for hh in range(max(WING_LO, tail), top + 1):
            blk = pal["trim"] if hh < bot else pal["wall"]
            _put(w, f, c, side * t, 0, hh, blk)
            n += 1
        if k <= 2:                      # the coverts: a second sheet at the shoulder only
            for dd in (-1, 1):
                for hh in range(max(WING_LO, bot), max(bot, top - 1) + 1):
                    _put(w, f, c, side * t, dd, hh, pal["wall"])
                    n += 1
    return n


def _crown(w, f, pal, c, wings):
    """A robed columnar figure with sheet wings, and the light that picks it out.

    Robed and columnar for the reason the whole file exists: a robe is a cone and a mantle is a
    stripe, and both are shapes voxels give away free. There is no musculature, no shoulder mass
    and no attempt at a face - the figure is named by its OUTLINE, which is what the wings are.
    """
    sh = FIG0 + 5                       # the shoulder: where the wings leave the body
    body = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
    # THE PLINTH, AND IT IS STRUCTURAL. Without it the figure's lowest course is FIG0 and the
    # only thing under it is open air over the gallery deck - the crown was hanging off the four
    # lamps beside it, which is a hundred and sixty cells of statue keyed to a lantern. It is
    # also what a statue stands on, and it takes the nine deck cells a visitor could not have
    # stood on anyway (the figure is over their head there).
    for (a, b) in body:
        _put(w, f, c, a, b, FIG0 - 1, pal["trim"])
    for h in range(FIG0, sh + 1):
        for (a, b) in body:
            _put(w, f, c, a, b, h, pal["wall"])
    for h in range(FIG0 + 2, sh + 1):   # the mantle, down the front face
        _put(w, f, c, 0, -1, h, pal["accent"])
    for h in (FIG0, FIG0 + 1):          # the hem, in the darker trim so the robe has a foot
        for (a, b) in body:
            if abs(a) + abs(b) > 1:
                _put(w, f, c, a, b, h, pal["trim"])

    wing = sum(_wing(w, f, pal, c, s, wings, sh) for s in (1, -1))

    _put(w, f, c, 0, 0, sh + 1, pal["trim"])                    # the neck
    for h in (sh + 2, sh + 3):                                  # the head
        for (a, b) in body:
            _put(w, f, c, a, b, h, pal["wall"] if h == sh + 2 else pal["trim"])
    for (a, b) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):   # the halo
        _put(w, f, c, a, b, sh + 4, pal["accent"])
    _put(w, f, c, 0, 0, sh + 5, "end_rod", facing="up")

    # LIGHT ON THE GALLERY FLOOR, NOT ON THE FIGURE. A lamp set into a sculpture is a hole in it -
    # the island night pass's own rule, and its cost model exists to keep fixtures off a coat.
    # These four stand on the gallery's own deck, a course below the hem, which is ordinary
    # ground by any reading, and they uplight the robe and the underside of both wings AND light
    # the gallery a visitor is actually standing on.
    lamps = 0
    for (di, dd) in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        if _put_free(w, f, c + di, c + dd, FIG0 - 1, pal["light"],
                     hanging="false", waterlogged="false"):
            lamps += 1
    return wing, lamps, sh + 5


# ------------------------------------------------------------------ the build

def _monument(w: World, p: dict, ctx) -> dict:
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    c = PAD_R
    seed = int(p["seed"]) + f.x * 41 + f.z * 3
    columns = int(p["columns"])
    wings = int(p["wings"])
    if not 8 <= columns <= 12 or columns % 2:
        raise ValueError(f"columns must be an EVEN number from 8 to 12, not {columns}")
    if 2 * wings + 1 < MIN_WINGSPAN:
        raise ValueError(f"wings={wings} is a span of {2 * wings + 1}, under {MIN_WINGSPAN}")

    title = str(p.get("title") or "THE MONUMENT").upper()
    lines = list(p.get("lines") or [])
    lines += ["raised by the", "park company", "for the island"][len(lines):]

    viewpoints = list(p.get("viewpoints") or VIEWPOINTS)

    pad = _base(w, f, pal, c, seed)
    panels, bays = _podium(w, f, pal, c, say, title, lines,
                           _ring_points(POD_R, columns))
    hung = _colonnade(w, f, pal, c, columns, seed)
    _shaft(w, f, pal, c)
    gal_floor, gal_rails, gal_lamps, gal_under = _gallery(w, f, pal, say, c, viewpoints)
    td = TURRET_AT
    treads, turret_rails, turret_lamps, mouth = _turret(
        w, f, pal, c, td, 0, H_GALLERY, TURRET_PHASE)
    land_floor, land_rails = _landing(w, f, pal, c, td, H_GALLERY, mouth)
    bridge = _bridge(w, f, pal, c, td, H_GALLERY)
    wing, crown_lamps, top = _crown(w, f, pal, c, wings)
    yard, marked = _approach(w, f, pal, say, c, td, len(treads))
    portal_lamps = _portal(w, f, pal, say, c, td, len(treads))

    # LAMP POSTS ROUND THE FOOT, on the lowest step, standing clear of the one above it. A post
    # carries its own light and the lantern STANDS on the cap: written `hanging=true` it looks
    # for a block above, finds open sky, and is a lantern hanging from nothing.
    #
    # AND ONE OF THE EIGHT IS SKIPPED, BECAUSE IT STOOD IN THE STAIRCASE. `_ring_points` puts a
    # post on every axis at radius STEP_R[0]-1, which is one cell inside the turret's own lit
    # pedestal - and the posts are placed LAST, so the post won and overwrote a tread. A stair
    # with a lamp post where its third step should be is a stair that stops at the second.
    posts = skipped = 0
    for (di, dd) in _ring_points(STEP_R[0] - 1, 8):
        if max(abs(di - td[0]), abs(dd - td[1])) <= 2:
            skipped += 1
            continue
        _lamp_post(w, f, pal, c + di, c + dd, 1, 3)
        posts += 1

    span = 2 * wings + 1
    assert top >= MIN_HEIGHT, f"monument is {top} tall, under the {MIN_HEIGHT}-course floor"
    assert span >= MIN_WINGSPAN, f"wingspan {span} is under {MIN_WINGSPAN}"
    assert len(treads) >= MIN_CLIMB, \
        f"the climb is {len(treads)} treads, under the {MIN_CLIMB}-tread floor"
    return {"kind": "monument", "height": top, "base": 2 * STEP_R[0] + 1, "pad": pad,
            "steps": len(STEP_R), "columns": columns, "bays": bays, "panels": panels,
            "wingspan": span, "wing_cells": wing,
            "lanterns": (hung + crown_lamps + posts + gal_lamps + gal_under + turret_lamps
                         + portal_lamps),
            "posts": posts, "posts_skipped": skipped,
            # THE WAY IN, in world coordinates, so a test can walk from the DOOR rather than from
            # a cell somebody chose because it happened to work.
            "door": f.at(c + PORTAL_I, c + PORTAL_D, 0),
            "portal_lanterns": portal_lamps, "forecourt": yard, "marked_route": marked,
            "landing_floor": land_floor, "landing_rails": land_rails, "stair_mouth": mouth,
            # THE CLIMB. `climb_treads` is the ordered path itself - world position and facing
            # per tread - so a test can walk it directly rather than re-deriving `_SPIRAL` on its
            # own and testing a copy of the code instead of the code.
            "climb_treads": treads, "climb_length": len(treads),
            "climb_rails": turret_rails + gal_rails + land_rails,
            "climb_lanterns": turret_lamps + gal_lamps + gal_under + portal_lamps,
            "bridge": bridge, "gallery_height": H_GALLERY, "gallery_radius": GAL_R,
            "gallery_floor": gal_floor, "gallery_rails": gal_rails,
            "gallery_soffit_lanterns": gal_under, "turret_at": td,
            "signs": say.want, "signs_placed": say.got,
            "contract": "five tiers, each narrower and taller than the one below: a four-step "
                        "base you can sit on, a panelled podium, a colonnade you can see "
                        "through, a fluted taper with a gilded collar, and a planar winged "
                        "figure at least 45 courses up - and an OBSERVATION TOWER anyone can "
                        "find: a lit, signed portal on the flank facing the approach, a marked "
                        "route to it across the apron, a spiral stair lit every four courses, a "
                        "railed landing, a fenced bridge, and a railed gallery with a bell and a "
                        "plaque naming the view - walkable from the door to the deck"}


BUILDERS = {"monument": _monument}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MONUMENT, **cfg}
    if not p.get("at"):
        raise ValueError("monument needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown monument kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"monument/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
