"""blur_gold.py OUTDIR [N]: golden data of the zoom blur 0x2a8e8 (+ asm warp at 0x58000) in the people scene: per call the 4 stack args (float32: cx, cy, arg3, arg4), p and S (float32, scene locals), , the buffer rows 0..199 (eax, 320 wide) before and after, once the
multiplication table at 0x121924 (64 fractions x 512).  usage: LOAD=snap.pkl python3 blur_gold.py OUT N   (JUMP=390ab TOFF=218 by default)"""
import sys,os,struct,runpy
out=sys.argv[1]; N=int(sys.argv[2]) if len(sys.argv)>2 else 40; os.makedirs(out,exist_ok=True)
sys.argv=['harness.py',str(10**6),out+'/png','100000']; os.environ.setdefault('JUMP','390ab'); os.environ.setdefault('TOFF','218')
import emucore as E
from unicorn import *
n=[0]; pend=[None]
def enter(*a):
    esp=E.ireg('ESP'); buf=E.ireg('EAX'); args=bytes(E.mu.mem_read(esp+4,16))
    if n[0]==0: open(out+'/mtab.bin','wb').write(bytes(E.mu.mem_read(0x121924-0x400,64*512+0x800)))
    ebp=E.ireg('EBP'); pend[0]=(args,bytes(E.mu.mem_read(buf,64000)),buf,bytes(E.mu.mem_read(ebp-0xc,4))+bytes(E.mu.mem_read(ebp-0x14,4)))
    if n[0]==0: open(out+'/ntab.bin','wb').write(bytes(E.mu.mem_read(0x110be4,512)))
def leave(*a):
    args,pre,buf,a3=pend[0];  post=bytes(E.mu.mem_read(buf,64000))
    open('%s/b%04d.bin'%(out,n[0]),'wb').write(args+a3+pre+post); n[0]+=1
    if n[0]>=N: E.mu.emu_stop()
m=[0]
def fin(*a):   # after the logo composite loop (0x39443): final buffer rows 0..199 of the frame, logo buffer once
    if m[0]==0: open(out+'/logo.bin','wb').write(bytes(E.mu.mem_read(E.u32(0x10ce54),64000)))
    open('%s/f%04d.bin'%(out,m[0]),'wb').write(bytes(E.mu.mem_read(E.u32(0x10d188)+0x1900,64000))); m[0]+=1
E.mu.hook_add(UC_HOOK_CODE,fin,begin=0x39443,end=0x39443); E.mu.hook_add(UC_HOOK_CODE,enter,begin=0x2a8e8,end=0x2a8e8); E.mu.hook_add(UC_HOOK_CODE,leave,begin=0x2a9c1,end=0x2a9c1)
runpy.run_path(os.path.dirname(os.path.abspath(__file__))+'/harness.py')
