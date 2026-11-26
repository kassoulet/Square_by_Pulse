"""rc_mal.py: record the guest malloc results (0x3b4bb entry: size in eax -> [size, ptr, header, next header]) of a scene run from a snapshot; replayed by web/js/x86rt.mjs malloc (MS.q) so guest-heap-layout-dependent reads see the same bytes.  usage: OUT=mal.json LOAD=snap.pkl PYTHONPATH=. python3 rc_mal.py   (edit NF below = snapshot flip + scene flips)"""
import sys,os,runpy,json
sys.argv=['harness.py',os.environ.get('NF','3990'),'/tmp/claude-1000/dbg28png','100000']
import emucore as E
from unicorn import *
seq=[]; pend=[]
def ent(uc,addr,sz,ud):
    esp=E.ireg('ESP'); ret=E.u32(esp); size=E.ireg('EAX')&0xffffffff
    seq.append([size,0,0,0]); idx=len(seq)-1
    def r(uc2,a,s,u):
        seq[idx][1]=E.ireg('EAX')&0xffffffff; seq[idx][2]=E.u32(seq[idx][1]-4) if seq[idx][1] else 0; seq[idx][3]=E.u32(seq[idx][1]-4+(seq[idx][2]&~1)) if seq[idx][1] else 0; 
        if seq[idx][1]:
            b=bytes(E.mu.mem_read(seq[idx][1],size)).rstrip(b'\0')   # stale heap bytes the guest block holds at return (replayed by x86rt malloc)
            if b: seq[idx].append(__import__('base64').b64encode(b).decode())
        E.mu.hook_del(h[0])
    h=[E.mu.hook_add(UC_HOOK_CODE,r,begin=ret,end=ret)]
E.mu.hook_add(UC_HOOK_CODE,ent,begin=0x3b4bb,end=0x3b4bb)
try: runpy.run_path('harness.py')
finally: json.dump(seq,open(os.environ['OUT'],'w'))
