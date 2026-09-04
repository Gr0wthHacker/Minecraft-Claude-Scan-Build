import yaml, pathlib
from mcbuild.gen import park_entrance as PE
from mcbuild import audit as audit_mod, pipeline, schem
p = yaml.safe_load(pathlib.Path('configs/pf_entry_gate.yaml').read_text())['params']
c = PE.build(p); m = c.to_model(); meta = c.meta
pc = schem.load('out/Park Complete.litematic')
print('Park Complete NOW:', int((pc.ids>0).sum()), 'blocks, shape', pc.ids.shape)
res = audit_mod.audit(m, ground=False)
print('design:', res.blocks, 'blocks, components', res.components, 'problems', len(res.problems),
      'tiers', dict(res.tiers))
pipeline._verify_in_context(m, res, 'out/Park Complete.litematic', c.world_origin, True,
                            ignore=set(), ignore_boxes=[], dig_above=False, context_clear=set())
print('lights', meta['lights'], 'signs', meta['signs'], 'ways refused', meta['ground_layer_refused'])
