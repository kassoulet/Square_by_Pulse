"""rc_gold.py OUTDIR [ENTRY=0x338a5 CALLRET=0x339c1]: golden capture of one scene function run from the snapshot (LOAD=post.pkl JUMP=hex TOFF=sec, see harness.py) for the recompiler check:
meta.json (registers at entry), stack.bin (0x800 bytes at esp), inputs.json ([dt ticks, song pos] returned by each poll 0x1ca79(0) at CALLRET), f%04d.bin (64000-byte buffer at every present 0x1d0cf),
dac.json (VGA DAC port writes [frame, port, value]).  usage: LOAD=snap.pkl JUMP=338a5 TOFF=207.8 PYTHONPATH=. python3 rc_gold.py OUT [ENTRY CALLRET]"""
import sys,os,json,runpy
out=sys.argv[1]; ENTRY=int(sys.argv[2],16) if len(sys.argv)>2 else 0x338a5; CALLRET=[int(x,16) for x in (sys.argv[3] if len(sys.argv)>3 else '339c1').split(',')]   # one or more poll return sites; os.makedirs(out,exist_ok=True)
sys.argv=['harness.py',str(10**6),out+'/png','100000']
import emucore as E
from unicorn import *
inp=[]; dac=[]; n=[0]
def entry(*a):
    esp=E.ireg('ESP'); json.dump({r:E.ireg(r) for r in ('EAX','EBX','ECX','EDX','ESI','EDI','EBP','ESP')},open(out+'/meta.json','w'))
    open(out+'/stack.bin','wb').write(bytes(E.mu.mem_read(esp,0x800)))
def poll(*a): inp.append([E.ireg('EAX'),E.u32(0x10ce28),E.u32(0x10ce4c),E.ireg('ESP')])
ROWS={0x1d0cf:200,0x1d1b5:240,0x1d231:480}   # present routines and their row counts (harness.py); file size = 320*rows
def present(*a):
    open('%s/f%04d.bin'%(out,n[0]),'wb').write(bytes(E.mu.mem_read(E.ireg('EAX'),320*ROWS[E.ireg('EIP')]))); n[0]+=1
    json.dump(inp,open(out+'/inputs.json','w')); json.dump(dac,open(out+'/dac.json','w'))
E.extra_out.append(lambda port,val: dac.append([n[0],port,val]))
E.mu.hook_add(UC_HOOK_CODE,entry,begin=ENTRY,end=ENTRY); [E.mu.hook_add(UC_HOOK_CODE,poll,begin=c,end=c) for c in CALLRET]; [E.mu.hook_add(UC_HOOK_CODE,present,begin=a,end=a) for a in ROWS]
if os.environ.get('PRE'):   # PRE=hex addr: also dump the 64000-byte buffer in EAX at that function's entry (pre%04d.bin) and the 4 stack args (pre.json)
    PA=int(os.environ['PRE'],16); pre=[]; pc=[0]
    def prehook(*a):
        esp=E.ireg('ESP'); open('%s/pre%04d.bin'%(out,pc[0]),'wb').write(bytes(E.mu.mem_read(E.ireg('EAX'),64000))); pre.append([E.u32(esp+4+4*i) for i in range(4)]); pc[0]+=1; json.dump(pre,open(out+'/pre.json','w'))
    E.mu.hook_add(UC_HOOK_CODE,prehook,begin=PA,end=PA)
runpy.run_path(os.path.dirname(os.path.abspath(__file__))+'/harness.py')
json.dump(inp,open(out+'/inputs.json','w')); json.dump(dac,open(out+'/dac.json','w'))
