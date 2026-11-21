"""contact.py PNGDIR OUT.png flip[,flip...] : contact sheet (4 columns, 160x100 thumbs, labelled with the flip) of harness.py PNGs (nearest saved flip <= requested). python3 -I contact.py ..."""
import sys,glob,os
from PIL import Image,ImageDraw
d,out=sys.argv[1:3]; want=[int(x) for x in sys.argv[3].split(',')]
have=sorted(int(os.path.basename(f)[1:6]) for f in glob.glob(d+'/f*.png'))
sel=[max([h for h in have if h<=w] or [have[0]]) for w in want]
W,H=160,100; im=Image.new('RGB',(4*W,((len(sel)+3)//4)*H))
for i,k in enumerate(sel):
    t=Image.open('%s/f%05d.png'%(d,k)).convert('RGB').resize((W,H)); ImageDraw.Draw(t).text((3,3),'%d s'%(k/30),fill=(255,255,0)); im.paste(t,((i%4)*W,(i//4)*H))
im.save(out)
