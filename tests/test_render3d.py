"""The 3D view: the properties that make it worth trusting over an orthographic sheet.

Every assertion here is one of the reasons this renderer exists rather than a detail of how it is
written, because the failure mode of a render tool is that it produces a plausible picture of the
wrong thing and nobody can tell. This repo has shipped exactly that twice:

  * the elevation drew every flank in TOP-face colour, so 46% of the giraffe rendered as end grain;
  * every axolotl sheet looked right while the game looked wrong, because an orthographic view
    ALONG the body axis de-jags a diagonal head by construction.

So: perspective is asserted (it is the whole difference from the ortho tools), the bearing is
asserted against the recorded facing (picked by hand it was got wrong twice in one session), the
vanilla face ladder is pinned by value, and occlusion is asserted to actually occlude - AO and the
cast shadow are the two cues that carry MASS, which is the dimension the panel keeps failing animals
on, and a renderer that quietly did neither would still look fine.
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from mcbuild import nbt, render3d as r3                                    # noqa: E402
from mcbuild.schem import Model                                            # noqa: E402
import look                                                               # noqa: E402


def block(sx, sy, sz, name="white_wool"):
    """A solid box of one block, with air at palette 0 - the layout every Model has."""
    ids = np.zeros((sy, sz, sx), np.int32)
    return Model(ids=ids, palette=[nbt.block_state("air"), nbt.block_state(name)])


def filled(sx, sy, sz, name="white_wool"):
    m = block(sx, sy, sz, name)
    m.ids[:] = 1
    return m


# --------------------------------------------------------------------- perspective

def test_perspective_obeys_the_inverse_square_law():
    """THE reason this exists, and it has an exact law to check against. Move the camera twice as
    far from the same cube and it must cover a QUARTER of the pixels. An orthographic projection
    gives the same area at both distances - which is why a head aimed off the block grid could
    stair-step in game and look clean on every sheet ever rendered of it."""
    m = block(30, 30, 30)
    m.ids[13:17, 13:17, 13:17] = 1
    area = {}
    for d in (40.0, 80.0):
        cam = r3.Camera(pos=(15.0, 15.0, 15.0 - d), target=(15.0, 15.0, 15.0), fov=50)
        img = r3.render(m, cam, 240, 240, ground=False, silhouette=True)
        area[d] = int((img[:, :, 0] < 128).sum())
    assert area[40.0] > 400, "the cube is not being drawn at all"
    ratio = area[40.0] / area[80.0]
    assert 3.5 < ratio < 4.5, f"doubling the distance changed area by {ratio:.2f}x, not ~4x"


def test_a_face_pointing_away_from_the_camera_is_never_drawn():
    """A back face drawn is a hole in the shape; the DDA must report the face it entered through."""
    m = filled(6, 6, 6)
    img = r3.render(m, r3.orbit(m, yaw=0, pitch=0), 120, 120, ground=False, shadows=False, ao=False)
    # looking from +z at a cube of one block: every lit pixel is the +z face, at one brightness
    tones = np.unique(img.reshape(-1, 3), axis=0)
    body = [t for t in tones if not (t[2] > t[0] + 20)]        # drop the sky, which is blue
    assert len(body) == 1, f"one flat face should give one tone, got {len(body)}"


# --------------------------------------------------------------------- the bearing

def test_the_bearing_is_taken_from_the_recorded_facing():
    """bearing 0 must put the camera in FRONT. Picked by hand this was got wrong twice in one
    session, and auditing an animal's backside tells you nothing about its face."""
    m = filled(3, 3, 30)                                   # a bar; call the +z end the head
    head, tail = np.array([1.5, 1.5, 27.0]), np.array([1.5, 1.5, 3.0])
    yaw0, known = look.facing_yaw({"facing": [0, 1]})       # it faces +z
    assert known and yaw0 == pytest.approx(0.0)
    near = {}
    for b in (0, 180):
        p = np.array(r3.orbit(m, yaw=yaw0 + b, pitch=5).pos)
        near[b] = np.linalg.norm(p - head) < np.linalg.norm(p - tail)
    assert near[0] and not near[180], "bearing 0 must look at the head, 180 at the tail"


def test_a_sideways_facing_moves_zero_with_it():
    """The frog faces -x. Its head-on bearing cannot be the same number as the elephant's."""
    assert look.facing_yaw({"facing": [-1, 0]})[0] == pytest.approx(-90.0)
    assert look.facing_yaw({"facing": [0, 1]})[0] == pytest.approx(0.0)


def test_an_unrecorded_facing_is_reported_not_guessed():
    """A silent default here is the same trap as picking the axis by hand."""
    for meta in ({}, {"facing": None}, {"facing": [0, 0]}):
        yaw, known = look.facing_yaw(meta)
        assert not known and yaw == 0.0


# --------------------------------------------------------------- structures (compass-word facing)
#
# `gen/park.py` and everything built on it (casino, coaster, bigwheel, civic, frontiertown,
# hollowmanor, monument, streetfurniture) records `facing` as a COMPASS WORD, not a vector -
# park.py's own docstring: "the direction the FRONT looks out; a visitor stands in the +facing
# direction." That is the same fact an animal's nose vector states, so a word must land on the
# same yaw a vector would, via the ONE map that says what a word means (`park._STEP`) rather
# than a second, hand-typed copy that could disagree with it.

def test_a_compass_word_facing_is_converted_via_parks_own_step_map():
    from mcbuild.gen.park import _STEP
    for word, vec in _STEP.items():
        by_word = look.facing_yaw({"facing": word})
        by_vec = look.facing_yaw({"facing": list(vec)})
        assert by_word[0] == pytest.approx(by_vec[0]), word
        assert by_word[1] is True


def test_bearing_zero_faces_a_park_modules_front_door():
    """A visitor 'stands in the +facing direction' and looks at the front door - that is the
    structure's version of an animal's camera standing off the nose looking into the face, so
    bearing 0 must land nearer the door than the back wall, for EVERY compass word, not just the
    one this project has already gotten wrong by hand (CLAUDE.md: got wrong twice in one
    session)."""
    from mcbuild.gen.park import _STEP
    m = filled(9, 5, 7)                                    # a little room, not yet given a facing
    lo, hi = np.zeros(3), np.array([9.0, 5.0, 7.0])
    centre = (lo + hi) / 2
    for word, (dx, dz) in _STEP.items():
        door = centre.copy()
        door[0] = hi[0] - 0.5 if dx > 0 else (lo[0] + 0.5 if dx < 0 else centre[0])
        door[2] = hi[2] - 0.5 if dz > 0 else (lo[2] + 0.5 if dz < 0 else centre[2])
        back = 2 * centre - door                            # the wall on the opposite side
        yaw0, known = look.facing_yaw({"facing": word})
        assert known, word
        p = np.array(r3.orbit(m, yaw=yaw0, pitch=5).pos)
        assert np.linalg.norm(p - door) < np.linalg.norm(p - back), \
            f"facing={word!r}: bearing 0 looked at the back wall, not the door"


def test_an_unknown_compass_word_is_reported_not_guessed():
    """A typo'd or not-yet-invented kind of facing must say so, the same as a missing vector -
    silently defaulting to world +z here is the same trap this file already pins for vectors."""
    for meta in ({"facing": "northeast"}, {"facing": "up"}, {"facing": ""}):
        yaw, known = look.facing_yaw(meta)
        assert not known and yaw == 0.0


def test_the_two_profiles_are_mirror_images_of_a_symmetric_build():
    m = filled(9, 9, 25)
    m.ids[:, :4, :3] = 0                                    # break the symmetry along z only
    a = r3.render(m, r3.orbit(m, yaw=90, pitch=10), 160, 120, silhouette=True, ground=False)
    b = r3.render(m, r3.orbit(m, yaw=270, pitch=10), 160, 120, silhouette=True, ground=False)
    assert (a == b[:, ::-1]).mean() > 0.98


# --------------------------------------------------------------------- the light

def test_the_face_ladder_is_vanillas_and_is_pinned_by_value():
    """Top 1.0, north/south 0.8, east/west 0.6, bottom 0.5. Not a taste choice - it is what the
    game does, so it decides which faces of a build can carry a detail at all. Drifting off it
    would make this renderer disagree with the world about which faces are readable."""
    assert r3.FACE_SHADE[(1, 1)] == 1.00 and r3.FACE_SHADE[(1, -1)] == 0.50
    assert r3.FACE_SHADE[(2, 1)] == r3.FACE_SHADE[(2, -1)] == 0.80
    assert r3.FACE_SHADE[(0, 1)] == r3.FACE_SHADE[(0, -1)] == 0.60


def test_corner_ao_is_minecrafts_rule_not_an_approximation_of_it():
    """Two edge neighbours occluded is FULLY dark whatever the diagonal does. That is the game's own
    rule; a smooth falloff instead would round off exactly the inside corners that tell you a haunch
    stands proud of a flank."""
    dims = np.array([6, 6, 6], np.int32)
    occ = np.zeros((6, 6, 6), bool)
    occ[2, 2, 2] = True                                     # occ is [y, z, x]; the block is (2,2,2)
    vox = np.array([[2, 2, 2]], np.int32)
    ax, sg = np.array([1], np.int8), np.array([1], np.int8)  # its top face
    hit = np.array([[2.99, 3.0, 2.99]])                      # landing in the +x +z corner
    assert r3._corner_ao(occ, vox, ax, sg, hit, dims)[0] == pytest.approx(1.0),         "an unoccluded face must be fully lit"
    occ[3, 3, 2] = True                                      # the +z edge neighbour, one course up
    occ[3, 2, 3] = True                                      # the +x edge neighbour
    # the corner value is blended bilinearly across the face, so landing a hundredth of a block off
    # the corner cannot read exactly 0 - what matters is that the corner is dark and the middle of
    # the same face, which has three lit corners pulling on it, is not
    corner = r3._corner_ao(occ, vox, ax, sg, hit, dims)[0]
    middle = r3._corner_ao(occ, vox, ax, sg, np.array([[2.5, 3.0, 2.5]]), dims)[0]
    assert corner < 0.02, "both edges occluded must go dark, whatever the diagonal does"
    # and the middle is pinned to the value the rule derives, not to a threshold: with one corner
    # fully dark, two corners at 2/3 (one edge neighbour each) and one fully lit, the bilinear
    # centre is (1 + 2/3 + 2/3 + 0) / 4 = 7/12. A smooth-falloff AO would not land here.
    assert middle == pytest.approx(7 / 12, abs=0.01),         f"the darkening must be a CORNER with a lit middle, got {middle:.3f}"


def test_ao_darkens_a_floor_beside_a_wall_and_not_the_open_floor():
    """The image-level version of the same property, because the algorithm being right does not
    prove it is wired to the shading."""
    m = block(40, 20, 40)
    m.ids[0, :, :] = 1                                       # a floor
    m.ids[1:14, 18:22, 18:22] = 1                            # a tower standing on it
    cam = r3.Camera(pos=(20.0, 44.0, 19.0), target=(20.0, 0.0, 20.0), fov=55)
    lit = r3.render(m, cam, 220, 220, ground=False, shadows=False, ao=False).astype(float)
    occ = r3.render(m, cam, 220, 220, ground=False, shadows=False, ao=True).astype(float)
    changed = lit.sum(axis=2) - occ.sum(axis=2)
    assert changed.max() > 20, "AO is computed but is not reaching the shading"
    # the darkening must be CONCENTRATED at the wall foot, not spread over the open floor
    assert (changed > 10).mean() < 0.25, "AO is dimming the whole image rather than the corners"


def test_the_build_casts_a_shadow_on_the_ground():
    """A voxel animal in a void has no cue for how its legs meet the floor; the contact shadow is
    that cue, and "the legs read as posts at the corners" was the first complaint about the jaguar."""
    m = block(40, 12, 40)
    m.ids[6:12, 16:24, 16:24] = 1                           # a post held above the ground plane
    m.ids[0, :, :] = 1                                      # a floor for it to cast onto
    cam = r3.Camera(pos=(20.0, 30.0, -34.0), target=(20.0, 2.0, 20.0), fov=50)
    with_s = r3.render(m, cam, 200, 200, ground=False, shadows=True, ao=False).astype(float)
    without = r3.render(m, cam, 200, 200, ground=False, shadows=False, ao=False).astype(float)
    assert with_s.mean() < without.mean(), "shadows switched on changed nothing"
    assert (with_s.sum(axis=2) < without.sum(axis=2) - 12).mean() > 0.01, "no shadow fell"


def test_a_top_face_is_brighter_than_a_side_face_of_the_same_block():
    m = filled(8, 8, 8)
    img = r3.render(m, r3.orbit(m, yaw=45, pitch=35), 200, 200,
                    ground=False, shadows=False, ao=False)
    body = img.reshape(-1, 3)
    body = body[~(body[:, 2] > body[:, 0] + 20)]            # drop sky
    lum = body @ np.array([0.299, 0.587, 0.114])
    assert lum.max() > lum.min() * 1.3, "top and side came out the same brightness"


# --------------------------------------------------------------------- the panels

def test_the_silhouette_is_exactly_two_tones():
    """It is the 'would you know it with the colour removed' question shown rather than asked, so
    anything that leaks a third tone into it is defeating the panel."""
    m = filled(9, 9, 9)
    img = r3.render(m, r3.orbit(m), 120, 120, silhouette=True)
    assert len(np.unique(img.reshape(-1, 3), axis=0)) == 2


def test_the_value_panel_is_grey_but_not_flat():
    m = filled(10, 10, 10, "orange_wool")
    img = r3.render(m, r3.orbit(m, yaw=40, pitch=30), 140, 140, value=True).astype(int)
    assert (img[:, :, 0] == img[:, :, 1]).all() and (img[:, :, 1] == img[:, :, 2]).all()
    assert img[:, :, 0].std() > 4, "a value panel with no range cannot answer the roundness question"


def test_the_player_marker_is_scene_geometry_not_a_pasted_bar():
    """In perspective a bar drawn on the image has no depth and would lie about scale. A real
    1x2x1 stands on the same ground and shrinks with distance exactly as the build does."""
    m = filled(6, 6, 6)
    before = int(m.solid().sum())
    out, ok = look.with_scale_figure(m)
    assert ok and int(out.solid().sum()) == before + 2
    lo, hi = r3.content_box(m)
    lo2, hi2 = r3.content_box(out)
    assert hi2[0] > hi[0], "the marker must stand beside the build, not inside it"
    assert lo2[1] == lo[1], "and on the same ground, or it says nothing about height"


def test_the_orbit_frames_the_whole_build_at_every_bearing():
    """Framing must not change between bearings, or the sheet compares two different zooms and an
    animal looks to grow a haunch by being turned round."""
    m = filled(8, 20, 40)
    d = [np.linalg.norm(np.array(r3.orbit(m, yaw=b).pos) - np.array(r3.orbit(m, yaw=b).target))
         for b in (0, 45, 90, 135, 180)]
    assert max(d) - min(d) < 1e-6


def test_an_empty_build_does_not_crash_the_camera():
    m = block(4, 4, 4)
    img = r3.render(m, r3.orbit(m), 60, 60)
    assert img.shape == (60, 60, 3)
