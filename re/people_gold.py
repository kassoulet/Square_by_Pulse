"""people_gold.py OUTDIR [NCALLS]: golden data of the people scene (0x390ab), stage 'blend + upsample': from the post-start-up snapshot (LOAD env, harness.py) call the scene
and, at every entry of the 2x upsample 0x3900b, store the two source frames A=[ebp-0x20], B=[ebp-0x1c] (192x144 grey), p=[ebp-0xc] (float), the blended 192x144 buffer
(eax) and, after the return, the 320x240 result (edx).  Also dumps the two tables (0x10ce80 pointer: brightness LUT, 0x1062b8: add table) once.  usage: LOAD=snap.pkl python3 people_gold.py OUT N"""
import sys,os,struct,runpy
out=sys.argv[1]; N=int(sys.argv[2]) if len(sys.argv)>2 else 60; os.makedirs(out,exist_ok=True)
sys.argv=['harness.py',str(10**6),out+'/png','100000']; os.environ.setdefault('JUMP','390ab'); os.environ.setdefault('TOFF','218')
import emucore as E
from unicorn import *
n=[0]; pend=[None]
def enter(*a):
    ebp=E.ireg('EBP'); A=E.u32(ebp-0x20); B=E.u32(ebp-0x1c); p=bytes(E.mu.mem_read(ebp-0xc,4)); src=E.ireg('EAX'); dst=E.ireg('EDX')
    if n[0]==0:
        lut=E.u32(0x10ce80); open(out+'/lut.bin','wb').write(bytes(E.mu.mem_read(lut,256*130))); open(out+'/tab.bin','wb').write(bytes(E.mu.mem_read(0x1062b8,1024)))
    pend[0]=(bytes(E.mu.mem_read(A,27648)),bytes(E.mu.mem_read(B,27648)),p,bytes(E.mu.mem_read(src,27648)),dst)
def leave(*a):
    A,B,p,src,dst=pend[0]; open('%s/c%04d.bin'%(out,n[0]),'wb').write(A+B+p+src+bytes(E.mu.mem_read(dst,320*240))); n[0]+=1
    if n[0]>=N: E.mu.emu_stop()
E.mu.hook_add(UC_HOOK_CODE,enter,begin=0x3900b,end=0x3900b); E.mu.hook_add(UC_HOOK_CODE,leave,begin=0x390aa,end=0x390aa)
runpy.run_path(os.path.dirname(os.path.abspath(__file__))+'/harness.py')
