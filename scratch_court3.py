"""Swap the hand-placed parterres for DERIVED ones: whatever lawn the composition leaves."""
p = 'mcbuild/gen/midway_builds.py'
s = open(p, encoding='utf-8').read()

# 1. a helper that turns leftover lawn into planted parterres, inserted before _welcome_court
HELPER = '''def _parterres(L, open_cells, mid, axis, m, *, min_area=36) -> int:
    """EVERY PATCH OF LAWN THE COMPOSITION LEAVES BECOMES A PLANTED BED. Derived, not placed.

    Jack, on the first build of this court: *"it fills the space nicely, we dont want immediate
    large amounts of empty green."* Hand-placing four beds answers that only where somebody
    remembered to put one, and it answered it for the 41-wide lot and not for the 61-wide one -
    which is exactly how the two flanks came to be 714 columns of bare moss each in the first
    place.

    So the lawn is whatever the walk, the roundel, the pavilions and the queue do not take, and
    every connected piece of it bigger than `min_area` gets a kerb, a clipped hedge on that kerb,
    and trees on a LATTICE ANCHORED ON THE COURT'S OWN CENTRE. Anchoring the lattice on (mid,
    axis) rather than on each patch is what keeps the planting symmetric: two mirrored patches
    get mirrored trees because the lattice is mirrored, and nothing has to be typed twice.

    A tree is planted only where its whole crown fits inside the patch, so a bed never overhangs
    its own hedge - the check a render cannot make, because a leaf over a kerb draws exactly like
    a leaf over moss.
    """
    seen, beds = set(), 0
    for cell in sorted(open_cells):
        if cell in seen:
            continue
        patch, stack = set(), [cell]
        seen.add(cell)
        while stack:
            v, u = stack.pop()
            patch.add((v, u))
            for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (v + dv, u + du)
                if nxt in open_cells and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        if len(patch) < min_area:
            continue
        edge = {(v, u) for v, u in patch
                if any((v + dv, u + du) not in patch
                       for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
        inner = patch - edge
        for v, u in edge:
            L.put(v, 0, u, PAL["inlay"])
            L.put(v, 1, u, PAL["cap"], type="bottom", waterlogged="false")
        for v, u in inner:
            L.put(v, 0, u, PAL["lawn"])
        for v, u in sorted(inner):
            if (v - mid) % 7 or (u - axis) % 7:
                continue
            crown = {(v + dv, u + du) for dv in range(-2, 3) for du in range(-2, 3)}
            if crown <= inner:
                _tree(L, v, u, m)
        for v, u in sorted(inner):                 # low planting, off the same lattice
            if (v - mid) % 7 == 3 and (u - axis) % 7 == 3:
                L.put(v, 1, u, PAL["shrub"])
        _hedge(L, sorted(edge), m)
        beds += 1
    m["beds"] += beds
    return beds


'''
s = s.replace('def _welcome_court(L, p) -> dict:', HELPER + 'def _welcome_court(L, p) -> dict:', 1)

# 2. drop the hand-placed bed geometry
old_beds = '''    # THE FOUR PARTERRES, on the quadrant centres and mirrored twice. Thirteen by seventeen: big
    # enough for two trees and a hedge round them, which is what stops a bed reading as a pot.
    beds = [(v, u, du) for v, du in ((mid - 16, 1), (mid + 16, -1))
            for u in (axis - 17, axis + 17)]
    bed_in, bed_kerb = set(), set()
    for bv, bu, _d in beds:
        inner = {(v, u) for v in range(bv - 5, bv + 6) for u in range(bu - 7, bu + 8)}
        outer = {(v, u) for v in range(bv - 6, bv + 7) for u in range(bu - 8, bu + 9)}
        bed_in |= inner
        bed_kerb |= outer - inner

    # the two rear garden rooms, framed on their inner edges so the frame never enters the queue
    rooms = [(v0 + 40, u0, v1, u0 + 9), (v0 + 40, u1 - 9, v1, u1)]
    room_kerb = set()
    for rv0, ru0, rv1, ru1 in rooms:
        room_kerb |= {(rv0, u) for u in range(ru0, ru1 + 1)}
        room_kerb |= {(v, ru0 if ru0 > u0 else ru1) for v in range(rv0, rv1 + 1)}
'''
assert old_beds in s
s = s.replace(old_beds, '')

old_loop = '''            if v in (v0, v1) or u in (u0, u1) or (v, u) in bed_kerb or (v, u) in room_kerb:
                mat = PAL["inlay"]                 # the kerb: this court's own dark line
            elif (v, u) in bed_in:
                mat = PAL["lawn"]
            elif (v, u) in paved:
                mat = _court_pave(v, u, mid, axis, seed, half, rad)
            else:
                mat = PAL["lawn"]
            m["floor"] += bool(L.put(v, 0, u, mat))
'''
assert old_loop in s
s = s.replace(old_loop, '''            if v in (v0, v1) or u in (u0, u1):
                mat = PAL["inlay"]                 # the kerb: this court's own dark line
            elif (v, u) in paved:
                mat = _court_pave(v, u, mid, axis, seed, half, rad)
            else:
                lawn.add((v, u))
                continue                           # laid by `_parterres`, which needs the shape
            m["floor"] += bool(L.put(v, 0, u, mat))
''')

s = s.replace('''    m = {"signs": 0, "lamps": 0, "benches": 0, "trees": 0, "beds": 0, "floor": 0, "water": 0,
         "steps": 0, "hedge": 0, "bunting": 0, "axis": axis, "centre": mid}''',
              '''    m = {"signs": 0, "lamps": 0, "benches": 0, "trees": 0, "beds": 0, "floor": 0, "water": 0,
         "steps": 0, "hedge": 0, "bunting": 0, "axis": axis, "centre": mid}
    lawn: set = set()                              # what the composition leaves: see `_parterres`''')

# 3. replace the parterre and garden-room sections
old_sections = '''    # -- 4. the parterres ------------------------------------------------------------------------
    for bv, bu, _d in beds:
        _hedge(L, [(v, u) for v, u in bed_kerb
                   if max(abs(v - bv) - 5, abs(u - bu) - 7) == 1], m)
        for du in (-4, 4):
            _tree(L, bv, bu + du, m)
        for dv, du in ((-3, 0), (3, 0), (0, -7), (0, 7)):
            L.put(bv + dv, 1, bu + du, PAL["shrub"])
        m["beds"] += 1

    # -- 5. the garden rooms ---------------------------------------------------------------------
    # ONE OF THESE HOLDS THE WHEEL'S QUEUE AND THE OTHER HOLDS SEATS, and only the second is built
    # in: a frame drawn round somebody else's design is the most a court may honestly do there.
    for rv0, ru0, rv1, ru1 in rooms:
        if any((rv0 + 1, u) in queue for u in range(ru0, ru1 + 1)):
            continue
        cu = (ru0 + ru1) // 2
        _tree(L, rv0 + 4, cu, m)
        _bench(L, rv0 + 8, cu, -1, 0, 3, m)
        _standard(L, rv0 + 2, cu, m)

'''
assert old_sections in s
s = s.replace(old_sections, '''    # -- 4. the parterres, derived from whatever lawn the composition leaves ---------------------
    _parterres(L, lawn, mid, axis, m)

''')
s = s.replace('    # -- 6. the standards,', '    # -- 5. the standards,')

open(p, 'w', encoding='utf-8').write(s)
print('ok')
