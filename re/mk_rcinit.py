"""mk_rcinit.py FLAT.bin GOLDDIR OUT.bin.gz ENTRY a-b[,a-b...]: pack the entry state of a recompiled scene (registers, stack, the memory ranges it needs, the guest's song position per tick)
for web/js/rcscene.mjs.  FLAT.bin = re/snap2flat.py of the snapshot; GOLDDIR = re/rc_gold.py capture.  Layout (gzip): u32 header length, JSON header, then stack bytes and the ranges."""
import sys,json,gzip,struct
flat,gd,out,entry,rng=sys.argv[1:6]
d=open(flat,'rb').read(); meta=json.load(open(gd+'/meta.json')); inp=json.load(open(gd+'/inputs.json')); stack=open(gd+'/stack.bin','rb').read()
R=[tuple(int(x,16) for x in r.split('-')) for r in rng.split(',')]
pos={}
for dt,p,tick,esp in inp: pos[tick]=p
ticks=sorted(pos); h=json.dumps({'entry':int(entry,16),'regs':{k.lower():v for k,v in meta.items()},'esp':meta['ESP'],'stack':len(stack),'ranges':R,'ticks':ticks,'pos':[pos[t] for t in ticks]}).encode()
open(out,'wb').write(gzip.compress(struct.pack('<I',len(h))+h+stack+b''.join(d[a:b] for a,b in R),9))
print(out,'ranges',sum(b-a for a,b in R),'bytes ->',len(open(out,'rb').read()),'gz')
