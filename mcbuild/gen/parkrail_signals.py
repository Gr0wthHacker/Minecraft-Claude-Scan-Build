"""Inspectable station block signals; all entity events remain explicit inputs.

Memory is a comparator feedback loop with a restoring repeater. Unlike the
legacy locked-repeater helper it is tested for retention after the input ends.
"""


def memory_cell():
    cells = {}
    wires = [(0,0),(0,2),(1,2),(3,2),(4,2),(4,3),(4,4),(3,4),(1,4),(0,4),(0,3),(2,0)]
    for x,z in wires:
        cells[x,1,z] = 'redstone_wire'
    cells[0,1,1] = 'repeater[facing=south,delay=1]'
    cells[2,1,1] = 'repeater[facing=south,delay=1]'
    cells[2,1,2] = 'comparator[facing=east,mode=subtract]'
    cells[2,1,4] = 'repeater[facing=west,delay=1]'
    cells[0,1,-1] = 'detector_rail[shape=north_south]'
    cells[2,1,-1] = 'detector_rail[shape=north_south]'
    for x,y,z in list(cells):
        cells[x,0,z] = 'stone_bricks'
    return cells, {'set':(0,1,-1),'reset':(2,1,-1),'output':(4,1,2)}


def install(c, p):
    """Wire all six approach detectors, persistent memories and holding rails.

    Readout repeaters isolate track detectors from the signal cable. Three
    vertically separated cable routes prevent set/reset/output cross-feeding.
    A dark approach signal is stop: the holding rail needs a lit inverter.
    """
    result = []
    from .parkrail import SPAN
    for st in p['stations']:
        for track, direction, mirror in ((2,1,1),(12,-1,-1)):
            ac = st['at_u']
            def pos(x,y,t):
                return (x if mirror==1 else 14-x, y, ac+direction*t)
            def facing(a,b):
                dx,dz=b[0]-a[0],b[2]-a[2]
                return 'east' if dx>0 else 'west' if dx<0 else 'south' if dz>0 else 'north'
            def put(x,y,t,name,**props):
                q=pos(x,y,t)
                if not c.put(*q,c.raw_state(name,**props)):
                    raise ValueError(f'signal outside railway: {q}')
            def wire(vertices):
                # Vertices are connected by axis-aligned or one-course stairs.
                points=[vertices[0]]
                for end in vertices[1:]:
                    start=points[-1]
                    n=max(abs(end[i]-start[i]) for i in range(3))
                    for k in range(1,n+1):
                        points.append(tuple(round(start[i]+(end[i]-start[i])*k/n) for i in range(3)))
                for i,(x,y,t) in enumerate(points):
                    put(x,y-1,t,'stone_bricks')
                    # Cable trays need air above each dust climb, never buried wiring.
                    c.put(*pos(x,y+1,t),0)
                    straight=(0<i<len(points)-1 and points[i-1][1]==y==points[i+1][1]
                              and tuple(points[i+1][j]-points[i][j] for j in range(3))
                              ==tuple(points[i][j]-points[i-1][j] for j in range(3)))
                    if i % 8 == 5 and straight:
                        put(x,y,t,'repeater',facing=facing(pos(*points[i-1]),pos(*points[i+1])),
                            delay='1',locked='false',powered='false')
                    else:
                        put(x,y,t,'redstone_wire',power='0')
            # Detector readout on the outer kerb; it cannot be triggered by
            # the adjacent powered rail, which is not a redstone signal source.
            for t in (-10,10):
                put(1,12,t,'stone_bricks')
                put(1,13,t,'repeater',facing='west' if mirror==1 else 'east',delay='1',locked='false',powered='false')
                put(0,13,t,'stone_bricks')
            wire([(0,12,-10),(0,11,-11),(1,10,-11),(1,10,-31),(4,10,-31),(4,7,-34),
                  (3,7,-34),(3,7,-29),(4,7,-29)])
            wire([(0,12,10),(0,11,9),(1,10,9),(1,6,5),(1,6,-37),(6,6,-37),(6,7,-36),(6,7,-29)])
            wire([(8,7,-27),(10,7,-27),(10,7,-44),(2,7,-44),(2,10,-41)])
            for t in (-10,10):
                put(0,13,t,'stone_bricks')
            put(6,7,-34,'repeater',facing='south' if direction==1 else 'north',
                delay='1',locked='false',powered='false')
            # Output inversion and strong upward feed through the holding bed.
            put(2,10,-40,'redstone_lamp',lit='false')
            put(2,11,-40,'redstone_torch',lit='true')
            put(2,12,-40,'stone_bricks')
            cells,_=memory_cell()
            for (x,y,t),state in cells.items():
                if t<0: continue  # actual approach/clearance detectors drive the input cables
                name=state.split('[')[0]
                props={}
                if '[' in state:
                    props=dict(part.split('=') for part in state.split('[')[1][:-1].split(','))
                if 'facing' in props:
                    dx={'east':1,'west':-1}.get(props['facing'],0)
                    dt={'south':1,'north':-1}.get(props['facing'],0)
                    props['facing']=facing(pos(0,0,0),pos(dx,0,dt))
                put(x+4,y+6,t-29,name,**props)
            # Covered cable trays read as the viaduct's structural stringers.
            # Keep the detector take-off exposed for inspection at its plinth.
            for t in range(-37,10):
                for y in range(6,11):
                    if c.get_name(*pos(1,y,t)).split(':')[-1] in ('redstone_wire','repeater'):
                        for yy in (y-1,y):
                            if c.get_name(*pos(0,yy,t)).split(':')[-1] not in ('redstone_wire','repeater'):
                                put(0,yy,t,SPAN[st['land']]['pier'])
            # Staff recovery is a physical input on the reset cable, reached
            # from the arcade. It does not bridge or energise a boarding rail.
            for y in range(1,6):
                put(1,y,3,'stone_bricks')
                put(0,y,3,'ladder',facing='west' if mirror==1 else 'east')
            put(0,6,3,'stone_bricks')
            put(0,7,3,'stone_button',face='floor',facing='north',powered='false')
            for y in range(1,5):
                put(1,y,4,'stone_bricks')
            from .parkrail import _Deck
            sx,sy,sz=pos(0,4,4)
            if not _Deck(c,p).sign(sx+p['bounds'][0],sy,sz,'west' if mirror==1 else 'east',
                                   SPAN[st['land']]['wood'],
                                   ['STAFF RESET','CHECK LINE EMPTY','CLEAR HOLD ONLY','NO DISPATCH']):
                raise ValueError('staff reset label has no support')
            result.append({'station':st['title'],'track':'a' if direction==1 else 'b',
                           'set':pos(2,13,-10),'reset':pos(2,13,10),
                           'memory':pos(8,7,-27),'hold':pos(2,13,-40),
                           'brake':pos(2,13,0),'button':pos(3,14,0),
                           'indicator':pos(2,10,-40),'manual_clear':pos(0,7,3),
                           'staff_panel':pos(0,2,3)})
    return result
