"""mk_fix.py FLAT.bin CODE.dis OUT.fix: objdump's linear listing desyncs after data bytes between functions.  Every call target that is not an instruction start in the listing gets re-disassembled from that address (up to the next good call target, max 0x1000 bytes); x86js.py replaces the old instructions of each chunk (files ending in .fix)."""
import sys,re,subprocess,tempfile,os
flat,dis,out=sys.argv[1:4]
starts=set();tg=set()
for l in open(dis):
    p=l.rstrip('\n').split('\t')
    if len(p)>=3 and re.match(r'\s*[0-9a-f]+:',p[0]):
        starts.add(int(p[0].strip().rstrip(':'),16))
        m=re.match(r'call\s+0x([0-9a-f]+)$',p[2].strip())
        if m: tg.add(int(m.group(1),16))
tg=sorted(t for t in tg if 0x1c000<=t<0x58000); bad=[t for t in tg if t not in starts]; good=[t for t in tg if t in starts]
f=open(flat,'rb'); res=[]
for t in bad:
    end=min([g for g in good if g>t]+[t+0x1000]); end=min(end,t+0x1000); f.seek(t); d=f.read(end-t)
    with tempfile.NamedTemporaryFile(delete=False) as tmp: tmp.write(d)
    o=subprocess.run(['objdump','-D','-b','binary','-mi386','-Mintel','--adjust-vma=0x%x'%t,tmp.name],capture_output=True,text=True).stdout; os.unlink(tmp.name)
    res.append(o)
open(out,'w').write('\n'.join(res)); print(len(bad),'re-disassembled entries:',' '.join('%x'%b for b in bad))
