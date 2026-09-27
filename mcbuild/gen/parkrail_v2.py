"""Park Line renewal. Coordinates here are local to the fifteen-column viaduct.

The old line remains available for regression comparison. Review greyboxes use
the same massing functions as detail, with mechanisms omitted and a neutral palette.
"""
from __future__ import annotations

import numpy as np

from . import parkrail


def enhance(c, p):
    """Renew the three stations without changing the reach structures or footprint."""
    if c.sx != 15 or p['park_side'] != -1 or p['bounds'][1] != 0:
        raise ValueError('railway renewal requires the registered 15-wide rim section')
    c.ids = np.pad(c.ids, ((0, max(0, 35 - c.sy)), (0, 0), (0, 0)))
    c.sy = c.ids.shape[0]
    grey = p.get('renewal_greybox', False)
    deck = int(p['deck_y'])
    walk = deck + 1

    def put(x, y, z, name, **props):
        if not c.put(x, y, z, c.raw_state(name, **props)):
            raise ValueError(f'railway renewal outside corridor: {(x, y, z)}')

    def box(x0, y0, z0, x1, y1, z1, name):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    put(x, y, z, name)

    contracts = []
    for st in p['stations']:
        ac, land = st['at_u'], st['land']
        pal = parkrail.SPAN[land]
        half = int(p['station_half'])
        step = int(st['stair'])
        portal = ac + step * (half + int(p['head_half']) + 1)
        # Remove the old canopy only. Circulation, entrance and track remain.
        c.ids[walk + 3:, ac-half:ac+half+1, :] = 0
        for pos in list(c.tiles):
            if ac-half <= pos[2] <= ac+half and pos[1] >= walk+3:
                del c.tiles[pos]
        material = {'frontier': 'spruce_planks', 'midway': 'white_wool',
                    'prismworks': 'polished_blackstone_bricks'}[land]
        frame = 'spruce_log' if land == 'frontier' else pal['band']
        # Tall columns have real footings on both platform edges. Cross ties
        # are over headroom, leaving both tracks and the central walk open.
        eave = walk + (7 if land == 'midway' else 6)
        for z in range(ac-half, ac+half+1, 6):
            for x in (3, 11):
                box(x, walk+3, z, x, eave, z, frame)
                box(x, walk, z, x, walk+2, z, pal['pier'])
            box(3, eave, z, 11, eave, z, frame)
            for x in (5,9):
                put(x, eave, z, parkrail.FLUSH_LIGHT)
            if land == 'frontier':
                # Paired stepped knee braces and a king post under each truss.
                for x in (4, 10):
                    box(x, eave-1, z, x, eave, z, frame)
                box(7, eave, z, 7, eave+4, z, frame)
        for z in range(ac-half, ac+half+1):
            for x in range(2, 13):
                if land == 'prismworks':
                    # Three sawtooth bays: each glazed riser faces the next bay.
                    rise = (z-(ac-half)) % 9 // 2
                    roof_y = eave + rise
                    put(x, roof_y, z, pal['roof'], type='bottom')
                    if z > ac-half:
                        prev = ((z-1)-(ac-half)) % 9 // 2
                        if rise > prev:
                            put(x, roof_y-1, z, material)
                        elif rise < prev:
                            box(x, roof_y+1, z, x, eave+4, z, 'cyan_stained_glass')
                else:
                    roof_y = eave + (5-abs(x-7))
                    put(x, roof_y, z, 'spruce_slab' if land == 'frontier' else 'stone_slab', type='bottom')
                    if x != 7:
                        put(x, roof_y-1, z, 'spruce_stairs' if land == 'frontier' else 'stone_brick_stairs',
                            facing='east' if x < 7 else 'west', half='bottom', shape='straight')
                    if z in (ac-half, ac+half) and 3 <= x <= 11:
                        box(x, eave+1, z, x, max(eave+1, roof_y-1), z,
                            frame if x in (3, 7, 11) else material)
        if land == 'midway':
            # Central clock gable: a secondary landmark, below B+35.
            box(5, eave+1, ac-3, 9, eave+9, ac+3, material)
            for y in range(eave+5, eave+10):
                for x in range(5, 10):
                    for z in (ac-4, ac+4):
                        put(x, y, z, 'polished_blackstone_bricks' if x in (5, 9) or y in (eave+5, eave+9) else 'smooth_stone')
            for z in (ac-4, ac+4):
                put(7, eave+7, z, 'black_wool')
                put(7, eave+8, z, 'black_wool')
                put(8, eave+7, z, 'black_wool')
            for x in (4,10):
                for z in range(ac-2,ac+3):
                    for y in range(eave+5,eave+10):
                        put(x,y,z,'polished_blackstone_bricks' if z in (ac-2,ac+2) or y in (eave+5,eave+9) else 'smooth_stone')
                for y,z in ((eave+7,ac),(eave+8,ac),(eave+7,ac+1)):
                    put(x,y,z,'black_wool')
            box(4, eave+10, ac-4, 10, eave+10, ac+4, 'red_wool')
            box(5, eave+11, ac-3, 9, eave+11, ac+3, 'stone_bricks')
        # Portal reads from the avenue: two five-high jambs framing a clear
        # seven-wide opening. Its lintel meets the existing viaduct structure.
        for z in (portal-4, portal+4):
            box(0, 1, z, 1, 7, z, pal['pier'])
        box(0, 8, portal-4, 1, 9, portal+4, frame)
        box(0, 10, portal-5, 1, 10, portal+5, material)
        for z in (portal-3, portal+3):
            put(0, 7, z, parkrail.FLUSH_LIGHT)
        # Recess station-adjacent spandrels behind projecting arch rings.
        # These edits stop at the land boundary; the Isthmus fabric is retained.
        land_bounds = next(a for a in p['lands'] if a['name'] == land)
        for z in range(max(land_bounds['u0'], ac-45), min(land_bounds['u1'], ac+45)+1):
            i = z % int(p['bay']) - int(p['pier_u'])
            if i < 0:
                continue
            spring = parkrail._intrados(i, int(p['bay'])-int(p['pier_u']),
                                       int(p['spring_y']), deck-1-int(p['crown_gap']))
            for outer, inset in ((0, 1), (14, 13)):
                # A stepped ring needs a backing course: recessing its
                # spandrel must not leave the individual voussoirs floating.
                put(inset, spring, z, pal['ring'])
                for y in range(spring+1, deck-1):
                    c.put(outer, y, z, 0)
                    put(inset, y, z, pal['spandrel'])
        # Separate circulation at platform level: queue bays use the non-stair
        # half; the central aisle remains the public return route.
        qz = ac-step*7
        for x in (4, 10):
            for z in range(qz-3, qz+4):
                put(x, deck, z, pal['band'])
                c.put(x,walk,z,0)
                c.put(x,walk+1,z,0)
        for x in (5,9):
            for z in range(qz-2,qz+3):
                put(x,walk,z,pal['post'])
        # Exit and service access are on opposite ends of the station. An
        # additional central flight descends outside the original canopy.
        exit_top = ac-step*(half+3)
        for k in range(walk-1):
            z = exit_top-step*k
            y = deck-k
            for x in (6, 7, 8):
                c.ids[y+1:walk+3, z, x] = 0
                box(x, 1, z, x, y-1, z, pal['pier'])
                put(x, y, z, pal['tread'], facing='south' if step > 0 else 'north', half='bottom', shape='straight')
            for x in (5, 9):
                put(x, walk, z, pal['parapet'])
        # Service is reached from the arcade through a separate ladder hatch,
        # outside both public flights. No guest path is used as a control room.
        service_z = ac + step*(half+10)
        box(11, 1, service_z, 11, deck, service_z, pal['pier'])
        for y in range(1, walk):
            put(10, y, service_z, 'ladder', facing='west')
        put(10, walk, service_z, pal['wood']+'_trapdoor', facing='west', half='bottom', open='false', powered='false', waterlogged='false')
        d = parkrail._Deck(c, p)
        routes={'frontier':('TO MIDWAY','SCENIC TURNBACK'),
                'midway':('TO PRISMWORKS','TO FRONTIER'),
                'prismworks':('SCENIC TURNBACK','TO MIDWAY')}
        for edge,face,z,label in ((3,'east',ac-3,routes[land][0]),
                                  (11,'west',ac+3,routes[land][1])):
            box(edge,walk,z,edge,walk+2,z,pal['wall'])
            x=edge+(1 if face=='east' else -1)
            # THE BOARD STATES THE OPERATING MODEL, and the model changed: a cart is no longer
            # held until somebody finds the button, it leaves on its own dwell. A board that
            # still said BOARD THEN PRESS would be telling a rider the ride will not start
            # without them - which is exactly what an abandoned cart used to prove false.
            if not d.sign(x+p['bounds'][0],walk+2,z,face,pal['wood'],
                          [label,'LET RIDERS EXIT','BOARD - IT GOES','PRESS TO GO NOW']):
                raise ValueError('platform destination board has no support')
        for x, z, text in [(1, portal, ['PARK LINE', st['title'], 'ENTRANCE', 'UP TO PLATFORMS']),
                            (7, qz, ['QUEUE HERE', 'LET RIDERS EXIT', 'NEXT CART SOON', 'FREE PARK LINE']),
                            (7, exit_top+step, ['EXIT', 'DOWN TO ARCADE', 'PARK RETURN', '']),
                            (11, service_z+1, ['STAFF ONLY', 'SIGNAL CABINET', 'RESET / INSPECT',
                                               'STOCK THE CARTS'])]:
            # Independent sign plinths are outside the two-column side walks.
            # Portal sign faces the avenue, using the existing lintel as backing.
            if x == 1:
                placed=d.sign(p['bounds'][0], 9, z, 'west', pal['wood'], text)
            else:
                put(x, walk, z, pal['wall'])
                put(x, walk+1, z, pal['wall'])
                placed=d.sign(x+p['bounds'][0], walk+1, z+step, 'south' if step > 0 else 'north', pal['wood'], text)
            if not placed:
                raise ValueError(f'railway sign has no support at {(x,z)}')
        contracts.append({'land': land, 'title': st['title'], 'entry': [0, 2, portal],
                          'queue': [[4, walk, qz], [10, walk, qz]],
                          'boarding': [[3, walk, ac], [11, walk, ac]],
                          'exit': [7, walk, exit_top], 'return': [7, 2, exit_top-step*(walk-2)],
                          'service': [10, 1, service_z], 'roof_peak': eave+(11 if land=='midway' else 5)})
    c.meta['renewal'] = {'version': 2, 'stations': contracts, 'live_proof': 'pending'}
    # THE FLEET IS A STOCKING CONTRACT, because a minecart is an ENTITY and a litematic is
    # blocks. Nothing in this project can ship one, and until this was written nothing SAID so:
    # the line had six brake bays, six departure buttons, twelve detectors and a full signalling
    # system, and no cart existed anywhere in the park to run on it. The menagerie's rule, in a
    # railway: ship it empty and name exactly what to put in it and where.
    #
    # ONE CART PER BRAKE BAY. A cart set down on a bay has not run over its own dwell trigger, so
    # it waits there for a rider rather than leaving on a timer nobody is there to use - and from
    # the first dispatch onward it circulates under the dwell like any other. Six is therefore
    # both the stock and the resting state.
    c.meta['renewal']['fleet'] = {
        'item': 'minecart', 'count': len(contracts) * 2,
        'place_on': 'each brake bay - see signals[].brake',
        'first_proof': 'run ONE cart round the whole circuit before stocking the rest',
        'min_separation_cells': 30,
    }
    c.legacy_signs = True
    # End promenades extend beyond the last regular twelve-block light interval.
    for z in (1,598):
        put(7,deck,z,parkrail.FLUSH_LIGHT)
    if not grey:
        from .parkrail_signals import install
        c.meta['renewal']['signals'] = install(c, p)
    # Power-source phasing changed around the new detectors. Preserve the
    # existing reaches literally, including their rail beds, rather than
    # allowing that phasing to rewrite the Isthmus.
    original = parkrail.build({**p, 'renewal': False, 'bay_half': 3, 'crop_u': None})
    remap=[]
    for tag in original.reg.palette:
        entry=tag.value
        props={k:v.value for k,v in entry['Properties'].value.items()} if 'Properties' in entry else {}
        remap.append(c.raw_state(entry['Name'].value,**props))
    for lo, hi in ((170,214),(385,429)):
        c.ids[:original.sy,lo:hi+1,:]=np.asarray(remap)[original.ids[:,lo:hi+1,:]]
    if grey:
        # Preserve empty circulation while showing only mass and supports.
        mask = c.ids > 0
        c.ids[mask] = c.state('light_gray_concrete')
        c.tiles.clear()
    return c
