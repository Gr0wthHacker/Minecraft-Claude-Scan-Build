import json,yaml,numpy as np
from pathlib import Path
from mcbuild import scan,blocks,worldassembly
from mcbuild.gen import parkrefinement
from tools.park_refinement import apply

def test_additions_preserve_every_existing_cell_and_avoid_capture():
 base=scan.load('out/premium_refinement/base.litematic');capture=scan.load('out/park_stitch_audit.litematic')
 addition=scan.load('out/PF Premium Refinement.litematic');merged=apply(base.model,base.origin)
 assert np.array_equal(merged.ids[base.model.ids>0],base.model.ids[base.model.ids>0])
 assert int(merged.solid().sum()-base.model.solid().sum())==136
 for y,z,x in zip(*addition.model.solid().nonzero()):
  X,Y,Z=addition.origin[0]+x,addition.origin[1]+y,addition.origin[2]+z
  assert capture.model.ids[Y-capture.origin[1],Z-capture.origin[2],X-capture.origin[0]]==0
  assert not 170<=Z-80300<=214 and not 385<=Z-80300<=429

def test_config_matches_artifact_and_materials():
 cfg=yaml.safe_load(Path('configs/pf_premium_refinement.yaml').read_text())['params']
 model=parkrefinement.build(cfg).to_model();saved=scan.load('out/PF Premium Refinement.litematic').model
 assert np.array_equal(model.ids,saved.ids)
 assert model.names==saved.names
 for name in model.names[1:]:assert blocks.available(name) and blocks.spendable(name)

def test_guest_access():
 result=worldassembly.validate(['out/premium_refinement/base.litematic','out/PF Premium Refinement.litematic'],entry=(97512,203,80600),destinations=[(97519,203,80582),(97540,204,80664),(97555,204,80664),(97528,204,80418),(97647,203,80372)])
 assert result['ok'],result
 Path('out/premium_refinement/worldvalidate.json').write_text(json.dumps(result,indent=2))
