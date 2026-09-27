"""Small additive park furnishings, with explicit sites and no ground edits."""
from .vertical import World

DEFAULTS = {'pieces': [], 'greybox': False}


def piece(spec, greybox=False):
    w = World()
    v, y, u = spec['at']
    land = spec.get('land', 'midway')
    stone = 'polished_deepslate' if land == 'prismworks' else 'stone_bricks'
    wood = 'spruce_planks' if land == 'frontier' else 'dark_oak_planks'
    leaf = 'azalea_leaves' if land == 'prismworks' else 'oak_leaves'
    light = 'soul_lantern' if land == 'prismworks' else 'lantern'
    def put(x, h, z, name, **props):
        if spec.get('rotate'):
            x, z = z, x
        w.put(97500+v+x, y+h, 80300+u+z, name, **props)
    kind = spec['kind']
    if kind == 'planter':
        for x in range(3):
            for z in range(5):
                edge = x in (0, 2) or z in (0, 4)
                put(x, 0, z, stone if edge else 'moss_block')
                if edge:
                    put(x, 1, z, 'polished_deepslate_slab' if land == 'prismworks' else 'stone_brick_slab', type='bottom')
                else:
                    put(x, 1, z, leaf, persistent='true', distance='1')
                    if z in (1, 3):
                        put(x, 2, z, 'flowering_azalea_leaves' if land == 'midway' else leaf,
                            persistent='true', distance='1')
        # Low corner lanterns are part of the planting, not another street mast.
        for z in (0, 4):
            put(1, 1, z, stone)
            put(1, 2, z, light, hanging='false')
    elif kind == 'screen':
        for x in (0, 4):
            for h in range(5):
                put(x, h, 0, 'stripped_spruce_log', axis='y')
        for x in range(5):
            put(x, 5, 0, wood)
            if 0 < x < 4:
                put(x, 1, 0, 'spruce_fence')
                put(x, 2, 0, 'oak_leaves', persistent='true', distance='1')
        for x in (1, 3):
            put(x, 4, 0, light, hanging='true')
        put(2, 5, 0, stone)
    elif kind in ('desk', 'lens'):
        for x in range(2):
            for z in range(5):
                put(x, 0, z, stone)
                put(x, 1, z, wood if kind == 'desk' else 'polished_blackstone_bricks')
        if kind == 'desk':
            for z in (1, 2, 3):
                put(1, 2, z, 'white_wool')
            put(1, 3, 2, 'white_wool')
            put(0, 2, 0, 'lantern', hanging='false')
            put(0, 2, 4, 'spruce_slab', type='bottom')
        else:
            for z in (1, 2, 3):
                put(1, 2, z, 'glass')
            put(1, 3, 2, 'glass')
            put(0, 2, 2, 'pearlescent_froglight')
        put(0, 1, -1, 'spruce_wall_sign', facing='north')
        w.sign(97500+v, y+1, 80300+u-1, front=spec.get('text', []))
    elif kind == 'board':
        for z in (0, 4):
            for h in range(4):
                put(0, h, z, 'stripped_dark_oak_log', axis='y')
        for z in range(5):
            put(0, 3, z, wood)
            put(0, 4, z, 'stone_brick_slab', type='bottom')
        for z in (1, 3):
            put(0, 2, z, wood)
            put(-1, 2, z, 'oak_wall_sign', facing='west')
            w.sign(97500+v-1, y+2, 80300+u+z, front=spec['text'][0 if z==1 else 1])
    elif kind == 'plaque':
        put(0, 0, 0, 'spruce_wall_sign', facing='north')
        w.sign(97500+v, y, 80300+u, front=spec['text'])
    elif kind == 'posy':
        put(0, 0, 0, 'oak_leaves', persistent='true', distance='1')
        put(0, 1, 0, 'flowering_azalea_leaves', persistent='true', distance='1')
    elif kind == 'basket':
        put(0, 0, 0, 'dark_oak_slab', type='top')
        for x,z in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            put(x, 1, z, 'flowering_azalea_leaves', persistent='true', distance='1')
        put(0, 2, 0, 'dark_oak_fence')
        put(0, 3, 0, 'dark_oak_fence')
    else:
        raise ValueError(f'unknown refinement kind: {kind}')
    if greybox:
        w.cells = {p: ('light_gray_wool', {}) for p in w.cells}
        w.signs.clear()
    return w


def build(cfg, donors=None):
    w = World()
    for spec in cfg['pieces']:
        for line in spec.get('text', []):
            for text in (line if isinstance(line, list) else [line]):
                if len(text) > 15:
                    raise ValueError(f'sign line exceeds 15 characters: {text}')
        p = piece(spec, cfg.get('greybox', False))
        if set(p.cells) & set(w.cells):
            raise ValueError(f'refinement pieces overlap at {spec["name"]}')
        w.cells.update(p.cells)
        w.signs.update(p.signs)
    return w.canvas({'kind':'park_refinement', 'pieces':cfg['pieces'],
                     'contract':'Additions only. Existing roads, buildings and terrain remain unchanged.'})
