"""emucore.py - run the unpacked SQUARE.EXE (PMODE/W 1.22 flat 32-bit, Watcom C + MIDAS 0.7.b1) under Unicorn with DOS/DPMI/VESA/VGA stubs.
Start state = RAM dump made by unpack_clean.py at the program entry 0x3b1b8 (path in env SQ_MEM, default scratch).
Flat model: selectors DS=0x858 / CS=0x860 are base 0 (the dump's own GDT is reused), so linear == offset.  No IDT: Unicorn gives us every `int n`."""
import os,struct,sys,collections
from unicorn import *
from unicorn.x86_const import *
R=lambda n:getattr(sys.modules['unicorn.x86_const'],'UC_X86_REG_'+n)
HERE=os.path.dirname(os.path.abspath(__file__)); GAME=os.path.dirname(HERE)
MEMF=os.environ.get('SQ_MEM','/tmp/claude-1000/-home-gautier-SynologyDrive-code-current-demoports/32c9b7ad-cb1e-451b-a282-9c45f32c7e6e/scratchpad/sq/mem.bin')
mu=Uc(UC_ARCH_X86,UC_MODE_32)
TOP=0x40000000
mu.mem_map(0,TOP)
mu.mem_write(0,open(MEMF,'rb').read())
GDT=0x1b700; GDTLIM=0x86f
mu.reg_write(UC_X86_REG_GDTR,(0,GDT,GDTLIM,0))
# DS limit 64 MB: Watcom's sbrk starts the heap at lsl+1
mu.mem_write(GDT+0x858,struct.pack('<HHBBBB',0x3fff,0,0,0x93,0xc0,0))
LDT=0x3ff00000
def setdesc(idx,base,limit,g=0):
    mu.mem_write(LDT+idx*8,struct.pack('<HHBBBB',limit&0xffff,base&0xffff,(base>>16)&0xff,0xf3,(g<<7)|0x40|(limit>>16),(base>>24)&0xff))
def getbase(idx):
    d=bytes(mu.mem_read(LDT+idx*8,8)); return d[2]|d[3]<<8|d[4]<<16|d[7]<<24
LDTN=512
for i in range(LDTN): setdesc(i,0,0)
PSP=0xff00
_a=os.environ.get('ARGS')       # command tail of the program (PSP:80h = length, text, CR); Watcom cstart builds argv from it
if _a is not None: mu.mem_write(PSP+0x80,bytes([len(_a)+1])+b' '+_a.encode()+b'\r')
setdesc(4,PSP,0xff)             # selector 0x24 = PSP (Watcom cstart: mov ax,24h)
mu.reg_write(UC_X86_REG_LDTR,(0x30,LDT,LDTN*8-1,0x82))
mu.reg_write(UC_X86_REG_CR0,mu.reg_read(UC_X86_REG_CR0)|1)
for r,s in [('CS',0x860),('DS',0x858),('ES',0x58),('SS',0x858),('FS',0x858),('GS',0x858)]: mu.reg_write(R(r),s)
mu.reg_write(UC_X86_REG_ESP,0x14b110)
def ireg(n): return mu.reg_read(R(n))
def w(r,v): mu.reg_write(R(r),v&0xffffffff)
def wax(v): w('EAX',(ireg('EAX')&0xffff0000)|(v&0xffff))
def setcf(v):
    f=ireg('EFLAGS'); mu.reg_write(UC_X86_REG_EFLAGS,(f|1) if v else (f&~1))
def cstr(a):
    b=bytearray()
    while True:
        c=mu.mem_read(a,1)[0]
        if c==0: return bytes(b).decode('latin1')
        b.append(c); a+=1
def u32(a): return struct.unpack('<I',bytes(mu.mem_read(a,4)))[0]
def wr32(a,v): mu.mem_write(a,struct.pack('<I',v&0xffffffff))
# ---- host files ----
files={}; nextfd=[5]; written={}; vfs={}; stdout_cap=[]   # written: name -> bytes of files the program created; stdout_cap: DOS handle 1/2 writes
def hostfile(name):
    if name in vfs: return vfs[name]
    n=os.path.basename(name.replace('\\','/')).lower()
    if n=='con': return b''
    for f in os.listdir(GAME):
        if f.lower()==n and os.path.isfile(GAME+'/'+f): return open(GAME+'/'+f,'rb').read()
    return None
# ---- DPMI / VBE ----
nextsel=[8]
ARENA=0x10000000; arena_ptr=[ARENA]
def aalloc(n):
    a=arena_ptr[0]; arena_ptr[0]+=(n+0xfff)&~0xfff; return a
dosptr=[0x60000]
LFB=0x30000000
VBEMODES={0x101:(640,480,8),0x100:(640,400,8),0x4101:(640,480,8)}
curmode=[0]; on_setmode=[]
vectors={}      # PM interrupt vectors set via int21/25 or dpmi 0205
def vbe(no,a,st):
    if no!=0x10: print('RMINT',hex(no),[hex(x) for x in st]); return True
    eax=st[7]; ax=eax&0xffff
    es=struct.unpack('<H',bytes(mu.mem_read(a+0x22,2)))[0]; di=st[0]&0xffff
    def ret(v):
        st[7]=(eax&0xffff0000)|v; mu.mem_write(a,struct.pack('<8I',*st))
    if ax==0x4f00:
        p=(es<<4)+di
        blk=bytearray(512); blk[0:4]=b'VESA'; struct.pack_into('<H',blk,4,0x0200)
        struct.pack_into('<I',blk,6,(es<<16)|(di+0x100)); struct.pack_into('<I',blk,10,1)
        struct.pack_into('<I',blk,14,(es<<16)|(di+0x120)); struct.pack_into('<H',blk,18,64*16)
        ml=sorted(VBEMODES)
        for i,m in enumerate(ml): struct.pack_into('<H',blk,0x120+2*i,m)
        struct.pack_into('<H',blk,0x120+2*len(ml),0xffff); blk[0x100:0x108]=b'pyvbe\0\0'
        mu.mem_write(p,bytes(blk)); ret(0x4f); return True
    if ax==0x4f01:
        m=st[6]&0xffff; p=(es<<4)+di
        print('VBE modeinfo',hex(m))
        if (m&0x1ff) not in VBEMODES: ret(0x14f); return True
        w_,h_,bpp=VBEMODES[m&0x1ff]; blk=bytearray(256)
        struct.pack_into('<H',blk,0,0x9b); blk[2]=7; blk[3]=7
        struct.pack_into('<HHHH',blk,4,64,64,0xa000,0)
        struct.pack_into('<H',blk,0x10,w_); struct.pack_into('<HH',blk,0x12,w_,h_)
        blk[0x16]=8;blk[0x17]=16;blk[0x18]=1;blk[0x19]=bpp;blk[0x1a]=1;blk[0x1b]=4;blk[0x1c]=1
        struct.pack_into('<I',blk,0x28,LFB); mu.mem_write(p,bytes(blk)); ret(0x4f); return True
    if ax==0x4f02:
        bx=st[4]&0xffff; curmode[0]=bx; print('VBE setmode',hex(bx)); [f() for f in on_setmode]; ret(0x4f); return True
    if ax in(0x4f05,0x4f07,0x4f09,0x4f06,0x4f08,0x4f0a): ret(0x4f); return True
    if ax==0x4f03: st[4]=curmode[0]; ret(0x4f); return True
    print('VBE?',hex(ax)); return False
def dpmi(uc):
    ax=ireg('EAX')&0xffff; bx=ireg('EBX')&0xffff; cx=ireg('ECX')&0xffff; dx=ireg('EDX')&0xffff
    setcf(0)
    if ax==0x0000: n=cx; wax((nextsel[0]<<3)|7); nextsel[0]+=n; return True
    if ax==0x0006: b=getbase(bx>>3); w('ECX',b>>16); w('EDX',b&0xffff); return True
    if ax==0x0007: setdesc(bx>>3,(cx<<16)|dx,0xfffff,1); return True   # limit set by 0008
    if ax==0x0008:
        l=(cx<<16)|dx; i=bx>>3; b=getbase(i)
        if l>0xfffff: setdesc(i,b,l>>12,1)
        else: setdesc(i,b,l,0)
        return True
    if ax in(0x0009,0x000b,0x0003): return True
    if ax==0x000a: setdesc(nextsel[0],getbase(bx>>3),0xfffff,1); wax((nextsel[0]<<3)|7); nextsel[0]+=1; return True
    if ax==0x0100:
        a=dosptr[0]; dosptr[0]+=bx*16; wax(a>>4); w('EDX',(nextsel[0]<<3)|7); setdesc(nextsel[0],a,bx*16-1,0); nextsel[0]+=1; return True
    if ax==0x0101: return True
    if ax==0x0200: w('ECX',0); w('EDX',0); return True
    if ax==0x0204: w('ECX',0x860); w('EDX',vectors.get(('pm',ireg('EBX')&0xff),0)); return True
    if ax==0x0205: vectors[('pm',bx&0xff)]=ireg('EDX'); print('PM vec',hex(bx&0xff),hex(ireg('EDX'))); return True
    if ax in(0x0201,0x0600,0x0601,0x0602,0x0603): return True
    if ax==0x0400: wax(0x0090); w('EBX',3); w('ECX',4); w('EDX',0x0868); return True
    if ax==0x0500:
        a=ireg('EDI'); mu.mem_write(a,struct.pack('<12I',0x4000000,0x4000,0x4000,0x4000,0x8000,0x4000,0x4000,0x8000,0x1000,0,0,0)); return True
    if ax==0x0501:
        n=(bx<<16)|cx; a=aalloc(n); w('EBX',a>>16); w('ECX',a&0xffff); w('ESI',0); w('EDI',a&0xffff|1); return True
    if ax in(0x0502,0x0801): return True   # free memory block / free physical mapping (exit path)
    if ax==0x0800:
        sz=((ireg('ESI')&0xffff)<<16)|(ireg('EDI')&0xffff); print('PHYMAP',hex((bx<<16)|cx),hex(sz)); w('EBX',LFB>>16); w('ECX',LFB&0xffff); return True
    if ax==0x0300:
        a=ireg('EDI'); st=list(struct.unpack('<8I',bytes(mu.mem_read(a,32)))); return vbe(ireg('EBX')&0xff,a,st)
    return False
tr=[]; cnt=collections.Counter(); keyq=[]; keybytes=[]; clk=[0]; hooks_int={}
def intr(uc,no,_):
    eax=ireg('EAX'); ah=(eax>>8)&0xff; al=eax&0xff
    cnt[(no,ah if no!=0x31 else eax&0xffff)]+=1
    tr.append((no,hex(eax&0xffff),hex(ireg('EIP')),hex(ireg('ESP')))); del tr[:-40]
    if no in hooks_int and hooks_int[no](): return
    if no==0x21:
        if ah==0x30:
            if ireg('EBX')==0x50484152: mu.reg_write(UC_X86_REG_EAX,0x44580005); mu.reg_write(UC_X86_REG_EBX,0x34); return
            mu.reg_write(UC_X86_REG_EAX,0x0005); return
        if ah==0xff: mu.reg_write(UC_X86_REG_EAX,0); return
        if ah==0x4a:
            n=ireg('EBX'); print('int21/4A es=%x ebx=%x'%(ireg('ES'),n))
            if n and (ireg('ES')&0xfff8)==0x858:   # resize the flat DS (PMODE/W): ebx = new size in 4K pages
                mu.mem_write(GDT+0x858,struct.pack('<HHBBBB',(n-1)&0xffff,0,0,0x93,0xc0|(((n-1)>>16)&15),0)); mu.reg_write(R('DS'),0x858)
            setcf(0); return
        if ah==0x2c:
            clk[0]+=1; t=clk[0]//10
            mu.reg_write(UC_X86_REG_ECX,(10<<8)|((t//6000)%60)); mu.reg_write(UC_X86_REG_EDX,(((t//100)%60)<<8)|(t%100)); return
        if ah==0x2a: mu.reg_write(UC_X86_REG_ECX,1997); mu.reg_write(UC_X86_REG_EDX,(4<<8)|4); wax(0x2a00|5); return
        if ah==0x35: mu.reg_write(UC_X86_REG_EBX,vectors.get(('pm',al),0)); mu.reg_write(UC_X86_REG_ES,0x860); return
        if ah==0x25: vectors[('pm',al)]=ireg('EDX'); print('int21/25 vec',hex(al),hex(ireg('EDX'))); return
        if ah==0x0c: keybytes.clear(); return        # flush keyboard buffer (+ no-op function): menu button handlers
        if ah==0x0b: wax(0xb00|(0xff if keybytes else 0)); return
        if ah==0x08 or ah==0x07 or ah==0x01: wax(ah<<8|(keybytes.pop(0) if keybytes else 0)); return
        if ah==0x44: mu.reg_write(UC_X86_REG_EDX,0x80); setcf(0); return
        if ah==0x3d:
            n=cstr(ireg('EDX')); f=hostfile(n); print('OPEN',n,'->',None if f is None else len(f))
            if f is None: mu.reg_write(UC_X86_REG_EAX,2); setcf(1); return
            fd=nextfd[0]; nextfd[0]+=1; files[fd]=[f,0]; mu.reg_write(UC_X86_REG_EAX,fd); setcf(0); return
        if ah==0x3c:
            n=cstr(ireg('EDX')); fd=nextfd[0]; nextfd[0]+=1; files[fd]=[b'',0,n]; print('CREATE',repr(n)); mu.reg_write(UC_X86_REG_EAX,fd); setcf(0); return
        if ah==0x41: n=cstr(ireg('EDX')); print('DELETE',repr(n)); vfs.pop(n,None); setcf(0); return
        if ah==0x3e:
            f=files.pop(ireg('EBX'),None)
            if f and len(f)>2: written[f[2]]=vfs[f[2]]=f[0]   # file created by the program (never touches the host disk)
            setcf(0); return
        if ah==0x3f:
            f=files.get(ireg('EBX'));
            if f is None: wax(6); setcf(1); return
            n=ireg('ECX'); b=f[0][f[1]:f[1]+n]; mu.mem_write(ireg('EDX'),b); f[1]+=len(b); w('EAX',len(b)); setcf(0); return
        if ah==0x42:
            f=files.get(ireg('EBX'))
            if f is None: wax(6); setcf(1); return
            o=struct.unpack('<i',struct.pack('<I',(ireg('ECX')<<16|ireg('EDX'))&0xffffffff))[0]
            f[1]=o if al==0 else f[1]+o if al==1 else len(f[0])+o
            mu.reg_write(UC_X86_REG_EAX,f[1]&0xffff); mu.reg_write(UC_X86_REG_EDX,f[1]>>16); setcf(0); return
        if ah==0x40:
            n=ireg('ECX'); b=bytes(mu.mem_read(ireg('EDX'),n))
            f=files.get(ireg('EBX'))
            if f is not None and len(f)>2: f[0]+=b; w('EAX',n); setcf(0); return
            if ireg('EBX') in (1,2): stdout_cap.append(b)
            sys.stdout.write('[write %d] '%ireg('EBX')+b.decode('latin1')+'\n'); w('EAX',n); setcf(0); return
        if ah==0x4c: print('EXIT',al); uc.emu_stop(); return
        if ah==0x09: print('PRINT',cstr(ireg('EDX')).split('$')[0]); return
    if no==0x10:
        if ah==0x4f:
            a=0x3ff80000; st=[ireg('EDI'),ireg('ESI'),ireg('EBP'),0,ireg('EBX'),ireg('EDX'),ireg('ECX'),eax]
            mu.mem_write(a,struct.pack('<8I',*st))
            if vbe(0x10,a,st): w('EAX',struct.unpack('<8I',bytes(mu.mem_read(a,32)))[7]); return
        if ah==0:
            print('SETMODE',hex(al))
            if al==0x13: mu.mem_write(0xa0000,bytes(64000))   # mode set clears video memory
            return
        if ah==0x0e: sys.stdout.write(chr(al)); return
        if ah in(1,2,5,6,7,9,0x0a,0x0b,0x0c,0x10,0x11): return
        if ah==0x0f: wax(0x5003); return
        if ah==3: w('ECX',0x0607); w('EDX',0); return
    if no==0x16:
        if ah in(0,0x10): wax(keyq.pop(0) if keyq else 0); return
        if ah in(1,0x11):
            f=ireg('EFLAGS'); mu.reg_write(UC_X86_REG_EFLAGS,(f&~0x40) if keyq else (f|0x40))
            if keyq: wax(keyq[0])
            return
    if no==0x33: wax(0); return          # no mouse driver
    if no==0x2f and eax&0xffff==0x1686: wax(0); return
    if no==0x31 and dpmi(uc): return
    print(f"UNHANDLED INT {no:02x} ax={eax&0xffff:04x} ebx={ireg('EBX'):x} ecx={ireg('ECX'):x} edx={ireg('EDX'):x} eip={ireg('EIP'):x}")
    uc.emu_stop()
mu.hook_add(UC_HOOK_INTR,intr)
def mem_inv(uc,access,addr,size,val,_):
    print('MEMFAULT',access,hex(addr),size,'eip',hex(ireg('EIP'))); return False
mu.hook_add(UC_HOOK_MEM_UNMAPPED,mem_inv)
ports={}; _inctr=[0]
def _in(uc,port,size,_):
    _inctr[0]+=1
    if port==0x3da: return 8 if (_inctr[0]&1) else 0
    if port==0x40: return (65535-(_inctr[0]*37))&0xff
    return ports.get(port,0)
extra_out=[]
def _out(uc,port,size,val,_):
    ports[port]=val
    for f in extra_out: f(port,val)
mu.hook_add(UC_HOOK_INSN,_in,None,1,0,UC_X86_INS_IN)
mu.hook_add(UC_HOOK_INSN,_out,None,1,0,UC_X86_INS_OUT)
def run(start,n=0,timeout=0):
    try: mu.emu_start(start,0,timeout=timeout,count=n)
    except UcError as e: print('ERR',e,hex(ireg('EIP')))
if __name__=='__main__':
    run(0x3b1b8,n=int(sys.argv[1]) if len(sys.argv)>1 else 50000000)
    print('stopped eip',hex(ireg('EIP')),dict(cnt)); print(tr[-12:])
