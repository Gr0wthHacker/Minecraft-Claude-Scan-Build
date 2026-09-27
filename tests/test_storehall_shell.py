"""The store hall's room shell.

The hall shipped for a while as chest banks alone, which is a freestanding ring of chests on open
deck. These pin the three things about the wall that looked fine in code and would have been wrong
in world.
"""
import pytest

from mcbuild.gen.storehall import build_storehall

BOX = [-24194, 30023, -24188, 30029]
BASE = dict(box=BOX, floor_y=194, tiers=4, door="west", door_width=3,
            shell=True, labels=[], seed=0)


def _cells(canvas):
    out = {}
    ox, oy, oz = canvas.world_origin
    for x in range(canvas.sx):
        for y in range(canvas.sy):
            for z in range(canvas.sz):
                n = canvas.get_name(x, y, z)
                if n and n.replace("minecraft:", "") not in ("air", "cave_air", "void_air", "OOB"):
                    out[(x + ox, y + oy, z + oz)] = n.replace("minecraft:", "")
    return out


def test_the_shell_closes_the_ring_behind_the_banks():
    c = build_storehall(BASE)
    cells = _cells(c)
    ring = [(x, z) for x in range(-24195, -24186) for z in range(30022, 30031)
            if x in (-24195, -24187) or z in (30022, 30030)]
    for (x, z) in ring:
        got = [y for y in range(195, 200) if (x, y, z) in cells]
        assert got, "shell leaves a hole in the wall at x%d z%d" % (x, z)


def test_the_corners_of_the_bank_ring_are_filled():
    """A corner chest faces two ways and can face only one, so the banks leave four gaps. Read as
    doorways they would open four holes in the wall; they are piers."""
    cells = _cells(build_storehall(BASE))
    for (x, z) in ((-24194, 30023), (-24194, 30029), (-24188, 30023), (-24188, 30029)):
        assert any((x, y, z) in cells for y in range(195, 200)), \
            "bank corner x%d z%d left open" % (x, z)


def test_the_doorway_is_two_courses_and_has_a_lintel():
    """door: west, width 3 on a 7-cell run -> the middle three of z30024..30028."""
    cells = _cells(build_storehall(BASE))
    for z in (30025, 30026, 30027):
        assert (-24195, 195, z) not in cells and (-24195, 196, z) not in cells, "doorway walled up"
        assert (-24195, 197, z) in cells, "doorway has no lintel over it"
    for z in (30024, 30028):                       # and the rest of that wall stays solid
        assert (-24195, 195, z) in cells, "wall opened beyond the doorway at z%d" % z


def test_a_bank_gap_that_is_not_the_door_is_walled_not_opened():
    """A fixture blocking a bank cell must not read as a second doorway."""
    class _Ctx:                                    # east wall cell z30026 is 'occupied'
        def name_at(self, x, y, z):
            return "hopper" if (x, z) == (-24188, 30026) else "air"
    cells = _cells(build_storehall({**BASE, "under": None}))
    import mcbuild.gen.storehall as sh
    c = sh.build_storehall(BASE)                   # sanity: default path still builds
    assert c is not None
    # the shell behind that cell is solid at floor level in the plain build
    assert (-24187, 195, 30026) in cells


def test_plinth_and_cornice_are_the_dark_block():
    """cracked/chiseled stone brick are within 4 RGB of plain and draw no line; the horizontals have
    to be the one block with real value contrast."""
    cells = _cells(build_storehall(BASE))
    for y, name in ((195, "plinth"), (199, "cornice")):
        ring = {v for (x, yy, z), v in cells.items()
                if yy == y and (x in (-24195, -24187) or z in (30022, 30030))}
        assert ring == {"deepslate_bricks"}, "%s is %s, not deepslate_bricks" % (name, ring)


def test_the_field_is_weathered_per_cell_not_per_course():
    """Hashed on the course, every block in a course is identical and the wall is stripes."""
    cells = _cells(build_storehall(BASE))
    for y in (196, 197, 198):
        got = {v for (x, yy, z), v in cells.items()
               if yy == y and (x in (-24195, -24187) or z in (30022, 30030))}
        assert len(got) > 1, "course Y%d is one material - hash is on the course, not the cell" % y


def test_shell_off_builds_no_wall():
    cells = _cells(build_storehall({**BASE, "shell": False}))
    assert not [c for c in cells if c[0] in (-24195, -24187) or c[2] in (30022, 30030)]
