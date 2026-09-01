import sys, json
from mcbuild import pipeline, schem, circuit

cfgs = sys.argv[1:]
for cfg in cfgs:
    res = pipeline.run_config(cfg, ship=False)
    m = res.model if hasattr(res,'model') else None
    print(type(res), [a for a in dir(res) if not a.startswith('_')])
    break
