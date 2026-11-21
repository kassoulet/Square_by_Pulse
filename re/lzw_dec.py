"""lzw_dec.py OUTDIR: PEOPLE.LZW / ZEBOU.LZW through the ORIGINAL code under Unicorn.
Per file: (A) open with 0x1d86f (= loader 0x1d76f + bit-stream decoder init 0x1d92e), pull N bytes through the bit-stream reader 0x1d97a -> OUT/<name>.dec  (= the byte stream the DCT layer sees);
(B) re-open and call the frame decoder 0x38f7b once per frame (edx=struct first, then 0) -> OUT/<name>.frames (raw WxH planes) + .hdr (the six header fields per frame).
Run WITHOUT -I (unicorn).  Needs SQ_MEM (unpack_clean.py dump)."""
import sys,os,struct
import emucore as E
from unicorn import *
from unicorn.x86_const import *
OUT=sys.argv[1]; NFR=int(sys.argv[2]) if len(sys.argv)>2 else 117; NDEC=int(sys.argv[3]) if len(sys.argv)>3 else 3000000
E.keybytes[:]=[0,0x50]*12+[13]
E.mu.hook_add(UC_HOOK_CODE,lambda *a:E.mu.emu_stop(),begin=0x1c385,end=0x1c385)
E.run(0x3b1b8)
SENT=0x1c000; NAME=0x3ff70000; STK=0x3ff80000; OUTB=0x30000000; DST=0x20000000
def call(addr,**r):
    E.mu.reg_write(UC_X86_REG_ESP,STK-4); E.mu.mem_write(STK-4,struct.pack('<I',SENT))
    for k,v in r.items(): E.w(k.upper(),v)
    E.mu.emu_start(addr,SENT,timeout=600*10**6)
hdr=[]
E.mu.hook_add(UC_HOOK_CODE,lambda *a:hdr.append((E.ireg('EDX'),E.ireg('EBX'),E.ireg('ECX'),E.u32(E.ireg('ESP')+4))),begin=0x38cf6,end=0x38cf6)
for nm in (b'PEOPLE.LZW',b'ZEBOU.LZW'):
    base=OUT+'/'+nm.decode().lower().split('.')[0]
    E.mu.mem_write(NAME,nm+b'\0')
    call(0x1d86f,eax=NAME); s=E.ireg('EAX')
    call(0x1d97a,eax=s,ebx=NDEC,edx=DST); open(base+'.dec','wb').write(bytes(E.mu.mem_read(DST,NDEC))); print(nm,'dec written',flush=True)
    call(0x1d86f,eax=NAME); s=E.ireg('EAX'); E.wr32(0x131efc,s); E.wr32(0x131f00,0); del hdr[:]
    fr=[]; sz=0
    for k in range(NFR):
        E.mu.mem_write(OUTB,bytes(0x80000))
        try: call(0x38f7b,eax=OUTB,edx=s if k==0 else 0)
        except UcError as e: print('ERR frame',k,e); break
        h=hdr[-1]; n=h[1]*h[2]*h[3]; fr.append(bytes(E.mu.mem_read(OUTB,n))); print(nm,k,h,flush=True) if k<3 or k%20==0 else 0
    open(base+'.frames','wb').write(b''.join(fr)); open(base+'.hdr','w').write(repr(hdr))
