import sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mcbuild import scan,render3d
from tools.park_refinement import apply
from PIL import Image,ImageDraw
base=scan.load('out/premium_refinement/base.litematic');after=copy.copy(base);after.model=apply(base.model,base.origin)
views=[('Arrival planting',(22,290),(33,282),(18,270,48,302),204.6),('Garden backdrop',(43,362),(40,352),(30,346,63,381),205.6),('Lab specimen',(148,70),(148,76),(130,60,155,85),207.6),('Coaster field kit',(28,122),(31,120),(21,107,40,129),207.6)]
page=Image.new('RGB',(1000,1120))
for row,(title,eye,target,b,yeye) in enumerate(views):
 for col,s in enumerate((base,after)):
  v0,u0,v1,u1=b;m,_=scan.cut(s,97500+v0,200,80300+u0,97500+v1,224,80300+u1)
  cam=render3d.Camera((eye[0]-v0,yeye-200,eye[1]-u0),(target[0]-v0,5,target[1]-u0),fov=70)
  im=Image.fromarray(render3d.render(m,cam,500,280,ground=False));ImageDraw.Draw(im).text((8,8),title+(' / before' if col==0 else ' / after'),fill='white',stroke_width=1,stroke_fill='black');page.paste(im,(col*500,row*280))
page.save('out/premium_refinement/before_after.png')
