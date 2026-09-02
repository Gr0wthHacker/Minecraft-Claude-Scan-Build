import yaml, pathlib
from PIL import Image
from mcbuild.gen import park_entrance as PE
from mcbuild import render3d as r3
p = yaml.safe_load(pathlib.Path('configs/pf_entry_gate.yaml').read_text())['params']
c = PE.build(p); m = c.to_model()
outd = pathlib.Path('_look'); outd.mkdir(exist_ok=True)
for name, yaw, pitch, dist in (("front", 270, 14, 1.0), ("threequarter", 305, 22, 1.0),
                               ("plan", 270, 85, 1.0), ("back", 90, 16, 1.0)):
    cam = r3.orbit(m, yaw=yaw, pitch=pitch, dist=dist)
    Image.fromarray(r3.render(m, cam, width=1150, height=470)).save(outd / f"g2_{name}.png")
print("ok")
