"""harness.py - boot the ORIGINAL SQUARE.EXE (emucore) with a virtual clock; grab the 320x200 frame at every page flip (0x1d0cf).
 usage: python3 harness.py NFLIPS OUTDIR [step]   env: TPF = 60 Hz ticks per flip (default 2), RAW=dir -> f%05d.npz (idx+pal) per flip
Clock: before each flip the MIDAS 60 Hz callback 0x1c0a3 is called TPF times through a guest trampoline (runs the 0x1ca79 callback registry and ticks [0x10ce4c]); SCENE lines log the scene-function entries of main.  MIDASgetPlayStatus (0x3a07c) is replaced by an xm_times lookup (No Sound)."""
import sys,os,json,bisect,struct
import emucore as E
from unicorn import *; from unicorn.x86_const import *
import numpy as np
from PIL import Image
# env: JUMP=hexaddr (with LOAD) calls that scene function directly through a stub at 0x3ff50000; TOFF = seconds added to the music clock
NF=int(sys.argv[1]); OUT=sys.argv[2]; STEP=int(sys.argv[3]) if len(sys.argv)>3 else 60
TPF=int(os.environ.get('TPF',2)); TOFF=float(os.environ.get('TOFF',0)); JUMP=int(os.environ.get('JUMP','0'),16); RAW=os.environ.get('RAW')
XM=json.load(open(E.HERE+'/../web/assets/xm_times.json')); ROWS=XM['rows']; TIMES=[r[2] for r in ROWS]
SNAP=os.environ.get('SNAP'); LOAD=os.environ.get('LOAD'); ireg_eip=[0]
import pickle,zlib
REGS=['EAX','EBX','ECX','EDX','ESI','EDI','EBP','ESP','EIP','EFLAGS','CS','DS','ES','SS','FS','GS']
def spans():   # guest memory regions that are ever touched: low 128 MB (heap grows past the initial 64 MB DS limit via int21/4A), mmap arena, LDT page, LFB
    return [(0,0x8000000),(E.ARENA,E.arena_ptr[0]),(E.LDT,E.TOP),(E.LFB,E.LFB+0x100000)]
def save(path):
    # snapshot = registers + non-zero 4K pages + the python-side emucore/harness state (ports, DOS files, selectors, DAC, key queue)
    pages={}
    for a,b in spans():
        for p in range(a,b,0x1000):
            d=bytes(E.mu.mem_read(p,0x1000))
            if d.count(0)!=0x1000: pages[p]=d
    st=dict(regs={r:E.ireg(r) for r in REGS},gdtr=E.mu.reg_read(UC_X86_REG_GDTR),ldtr=E.mu.reg_read(UC_X86_REG_LDTR),cr0=E.mu.reg_read(UC_X86_REG_CR0),
        ports=E.ports,arena=E.arena_ptr[0],nextsel=E.nextsel[0],dosptr=E.dosptr[0],curmode=E.curmode[0],vectors=E.vectors,files=E.files,nextfd=E.nextfd[0],written=E.written,vfs=E.vfs,
        clk=E.clk[0],keybytes=list(E.keybytes),keyq=list(E.keyq),inctr=E._inctr[0],pal=PAL,dac=dac,fl=fl[0])
    pickle.dump((st,pages),open(path+'.tmp','wb'),protocol=4); os.replace(path+'.tmp',path)
    print('SNAPSHOT',path,len(pages),'pages flip',fl[0],flush=True)
def load(path):
    st,pages=pickle.load(open(path,'rb'))
    pass
    for p,d in pages.items(): E.mu.mem_write(p,d)
    E.mu.reg_write(UC_X86_REG_GDTR,st['gdtr']); E.mu.reg_write(UC_X86_REG_LDTR,st['ldtr']); E.mu.reg_write(UC_X86_REG_CR0,st['cr0'])
    for r,v in st['regs'].items(): E.mu.reg_write(E.R(r),v)
    E.ports.update(st['ports']); E.arena_ptr[0]=st['arena']; E.nextsel[0]=st['nextsel']; E.dosptr[0]=st['dosptr']; E.curmode[0]=st['curmode']
    E.vectors.update(st['vectors']); E.files.update(st['files']); E.nextfd[0]=st['nextfd']; E.written.update(st['written']); E.vfs.update(st['vfs'])
    E.clk[0]=st['clk']; E.keybytes[:]=st['keybytes']; E.keyq[:]=st['keyq']; E._inctr[0]=st['inctr']; PAL[:]=st['pal']; dac[:]=st['dac']; fl[0]=st['fl']
    ireg_eip[0]=st['regs']['EIP']
os.makedirs(OUT,exist_ok=True)
if RAW: os.makedirs(RAW,exist_ok=True)
E.keybytes[:]=[0,0x50]*12+[13]
PAL=np.zeros((256,3),np.uint8); dac=[0,0]
def out(port,val):
    if port==0x3c8: dac[0]=val; dac[1]=0
    elif port==0x3c9:
        PAL[dac[0]&255,dac[1]]=((val&63)<<2)|((val&63)>>4); dac[1]+=1
        if dac[1]==3: dac[1]=0; dac[0]+=1
E.extra_out.append(out)
ST=0x3ff90000; fl=[0]; TRAMP=0x3ff60000; skip=[0]
# ISR trampoline: pushfd; pushad; call 0x1c0a3 (the MIDAS 60 Hz callback: 0x1ca79(1) + tick++) x TPF; popad; popfd; jmp flip
def mk_tramp(target):
    c=b'\x9c\x60'
    for i in range(TPF): c+=b'\xe8'+struct.pack('<i',0x1c0a3-(TRAMP+len(c)+5))
    c+=b'\x61\x9d\xe9'; c+=struct.pack('<i',target-(TRAMP+len(c)+4)); return c
def getstatus(*a):
    esp=E.ireg('ESP'); p=E.u32(esp+4); t=E.u32(0x10ce4c)/60.0+TOFF
    i=max(0,bisect.bisect_right(TIMES,t)-1); r=ROWS[i]
    E.mu.mem_write(p,struct.pack('<IIII',r[0],XM['orders'][r[0]],r[1],0)); E.w('EAX',1)   # status struct is filled IN PLACE (arg = struct address; the earlier ST-pointer version made pos = 0xFE40xxxx)
    E.w('ESP',esp+4); E.mu.reg_write(UC_X86_REG_EIP,E.u32(esp))
def flip(rows,*a):
    if not skip[0]:
        if SNAP and not os.path.exists(SNAP): save(SNAP)
        skip[0]=1; E.mu.mem_write(TRAMP,mk_tramp(E.ireg('EIP'))); E.mu.reg_write(UC_X86_REG_EIP,TRAMP); return
    skip[0]=0
    k=fl[0]; fl[0]+=1
    fb=np.frombuffer(bytes(E.mu.mem_read(E.ireg('EAX'),320*rows)),np.uint8).reshape(rows,320)
    if RAW: np.savez_compressed('%s/f%05d.npz'%(RAW,k),idx=fb,pal=PAL)
    if k%STEP==0: Image.fromarray(PAL[fb]).save('%s/f%05d.png'%(OUT,k)); print('flip',k,'t=%.1f pos=%d'%(E.u32(0x10ce4c)/60,E.u32(0x10ce28)),flush=True)
    if k>=NF: E.mu.emu_stop(); return
E.mu.hook_add(UC_HOOK_CODE,getstatus,begin=0x3a07c,end=0x3a07c)
for a,rows in ((0x1d0cf,200),(0x1d1b5,240),(0x1d231,480)): E.mu.hook_add(UC_HOOK_CODE,lambda *x,rows=rows:flip(rows),begin=a,end=a)   # present routines: 0x1d0cf 200 rows (or plain copy), 0x1d1b5 240 rows, 0x1d231 480 rows (eax = source)
SC=[0x2f7d7,0x29a81,0x366f2,0x305f7,0x1faa1,0x2edbd,0x31f0a,0x28f64,0x243a9,0x34674,0x33b7e,0x32a9a,0x2f420,0x338a5,0x390ab]
SNAPSC=os.environ.get('SNAPSCENE'); SNAPOUT=os.environ.get('SNAPOUT')   # SNAPSCENE=hex scene entry, SNAPOUT=file: snapshot at that scene's entry and stop (full run needed for scenes that depend on heap state left by earlier scenes)
def snapsc(*x):
    if SNAPSC and SNAPOUT and E.ireg('EIP')==int(SNAPSC,16): save(SNAPOUT); E.mu.emu_stop()
if SNAPSC: E.mu.hook_add(UC_HOOK_CODE,snapsc,begin=int(SNAPSC,16),end=int(SNAPSC,16))
for a in SC: E.mu.hook_add(UC_HOOK_CODE,lambda *x,a=a:print('SCENE %#x flip %d t=%.2f order/row %d'%(a,fl[0],E.u32(0x10ce4c)/60,E.u32(0x10ce28)),flush=True),begin=a,end=a)
if LOAD:
    load(LOAD); st=ireg_eip[0]
    if JUMP:   # stub: call scene; hlt-equivalent = stop hook
        STUB=0x3ff50000; E.mu.mem_write(STUB,b'\xe8'+struct.pack('<i',JUMP-(STUB+5))+b'\x90'*4)
        E.mu.hook_add(UC_HOOK_CODE,lambda *a:(print('SCENE RETURNED flip',fl[0]),E.mu.emu_stop()),begin=STUB+5,end=STUB+5); st=STUB-6
        # the snapshot does not carry the x87 control word and Unicorn's softfloat keeps 80-bit precision until the first fldcw: load CW=0 (PC=24, nearest) like the demo's own state before the scene
        E.mu.mem_write(STUB-0x10,struct.pack('<H',int(os.environ.get('FPCW','0'),16))); E.mu.mem_write(STUB-6,b'\xd9\x2d'+struct.pack('<I',STUB-0x10))
    E.run(st)
else: E.run(0x3b1b8)
print('stopped',hex(E.ireg('EIP')),'flips',fl[0],E.tr[-4:])
