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
                                   ['STAFF RESET','CHECK LINE OK','CLEAR HOLD ONLY','NO DISPATCH']):
                raise ValueError('staff reset label has no support')
            # A NEW CELL MUST NOT LAND ON AN OLD ONE, and `Canvas.put` cannot say so - it
            # overwrites and returns True. The dwell chain runs thirty cells through a corridor
            # that already carries three cable routes at three heights, so it places through a
            # helper that refuses an occupied cell by NAME rather than silently replacing it.
            def place(x,y,t,name,**props):
                q=pos(x,y,t)
                if c.solid(*q):
                    raise ValueError(f'dwell chain would overwrite '
                                     f'{c.get_name(*q).split(":")[-1]} at {q}')
                if not c.put(*q,c.raw_state(name,**props)):
                    raise ValueError(f'dwell chain outside railway: {q}')
            port = {'station':st['title'],'track':'a' if direction==1 else 'b',
                    'set':pos(2,13,-10),'reset':pos(2,13,10),
                    'memory':pos(8,7,-27),'hold':pos(2,13,-40),
                    'brake':pos(2,13,0),'button':pos(3,14,0),
                    'indicator':pos(2,10,-40),'manual_clear':pos(0,7,3),
                    'staff_panel':pos(0,2,3)}
            port.update(dwell(c, p, pos, facing, place, direction))
            result.append(port)
    return result


def dwell(c, p, pos, facing, place, direction):
    """THE DWELL: a repeater chain whose LENGTH is the delay, so every cart departs by itself.

    Without it the railway deadlocks, and the deadlock is not an edge case - it is what happens
    the first time a rider walks away from a cart. The brake bay is released only by its own
    button; the occupancy memory that cart set on arrival is cleared only by the EXIT detector,
    which a parked cart never reaches; and the approach hold forty cells back is dead for as long
    as the memory stands. Simulated on the shipped model that is 20, 100, 400 and 2000 ticks and
    counting. The staff panel clears the MEMORY and not the CART, so the recovery it offers opens
    the hold in front of a platform that is still blocked.

    So the platform is made to clear itself. A third detector on the approach - `dwell_at` cells
    out, between the hold at forty and the arrival readout at ten - starts a chain of repeaters
    that runs along the maintenance kerb to a block beside the brake rail. When it arrives the
    brake goes live and the cart leaves, empty or not, and the exit detector then clears the
    memory and reopens the hold in the ordinary way. THE DELAY IS THE ROUTE: `dwell_delay` ticks
    per repeater over the cells between the trigger and the platform, so moving the trigger moves
    the dwell and there is no second number to keep in step.

    THE KERB IS THE ONLY LANE THERE IS, and that was measured rather than chosen: of the whole
    fifteen-column section, the strip at x=1 beside the running rail is the one place with a
    contiguous free, solid-supported run in all six approach frames. It is free from -45 to +45
    except for the two detector readouts at -10 and +10, so the chain steps OVER the arrival
    readout on a three-block bridge rather than routing round it - there is no round.

    A REPEATER IS THE ONLY SAFE THING TO LAY BESIDE A LIVE RAIL. A repeater outputs from its front
    and nowhere else, so a chain of them beside the running line cannot activate it; redstone dust
    beside a powered rail can. The four dust cells the bridge needs are all a course above the
    rail or a column clear of it.
    """
    D = int(p["dwell_at"])
    delay = str(int(p["dwell_delay"]))
    ahead = pos(0, 0, 1)                       # the compass word for one step toward the platform
    flow = facing(pos(0, 0, 0), ahead)

    def rep(t):
        place(1, 13, t, "repeater", facing=flow, delay=delay, locked="false", powered="false")

    place(1, 13, -D, "redstone_wire", power="0")          # read off the trigger detector beside it
    for t in range(-D + 1, -11):
        rep(t)
    # the bridge over the arrival readout at -10: block, dust, block, dust, block, dust.
    place(1, 13, -11, "stone_bricks")
    place(1, 14, -11, "redstone_wire", power="0")
    place(1, 14, -10, "stone_bricks")
    place(1, 15, -10, "redstone_wire", power="0")
    place(1, 13, -9, "stone_bricks")
    place(1, 14, -9, "redstone_wire", power="0")
    # AND THE BRIDGE COMES DOWN ONTO A BLOCK, NEVER ONTO DUST. Written with one more dust cell at
    # -8 the chain released the brake THIRTY-FIVE TICKS EARLY and by a route nothing in it could
    # see: dust beside a powered rail activates that rail, an activated powered rail carries its
    # own state EIGHT rails each way, and -8 plus eight is the brake. The cart left before it had
    # stopped. Dust strongly powers the block beneath it, so the descent lands on the support and
    # the next repeater reads that - and a repeater outputs from its front alone, so nothing from
    # here to the platform can reach the running line at all.
    for t in range(-8, 0):
        rep(t)
    # The last block is horizontally adjacent to the brake rail, so a strongly powered block here
    # is what sends the cart on. At rest it is an ordinary kerb stone and the bay stays dead.
    place(1, 13, 0, "stone_bricks")
    n = (D - 12) + 8
    return {"trigger": pos(2, 13, -D), "release": pos(1, 13, 0), "repeaters": n,
            "dwell_ticks": n * int(p["dwell_delay"])}
