"""pak_extract.py OUTDIR: decode every SQUARE.PAK file with the ORIGINAL loader code under Unicorn.
Runs the demo to the end of the PAK open (0x1c385, after the PAK open 0x1d655), then calls the file loader 0x1d76f(name) (-> struct {+0 FILE*, +4 buffer, +8 size};
the decoder is 0x1d92e) for each name of the directory (re/pak_dir.py layout) and writes the decoded buffers.  Run WITHOUT -I (unicorn)."""
import sys,os,struct
import emucore as E
from unicorn import *
from unicorn.x86_const import *
OUT=sys.argv[1]; os.makedirs(OUT,exist_ok=True)
E.keybytes[:]=[0,0x50]*12+[13]
E.mu.hook_add(UC_HOOK_CODE,lambda *a:E.mu.emu_stop(),begin=0x1c385,end=0x1c385)
E.run(0x3b1b8)
assert E.ireg('EIP')==0x1c385,hex(E.ireg('EIP'))
p=open(E.GAME+'/SQUARE.PAK','rb').read(); do=struct.unpack_from('<I',p,8)[0]
SENT=0x1c000; NAME=0x3ff70000; STK=0x3ff80000
for i in range((len(p)-do)//24):
    nm,o,c,u=struct.unpack_from('<12sIII',p,do+24*i); nm=nm.rstrip(b'\0')
    E.mu.mem_write(NAME,nm+b'\0'); E.mu.reg_write(UC_X86_REG_ESP,STK-4); E.mu.mem_write(STK-4,struct.pack('<I',SENT))
    E.w('EAX',NAME); E.mu.reg_write(UC_X86_REG_EIP,0x1d76f)
    try: E.mu.emu_start(0x1d76f,SENT,timeout=60*10**6)
    except UcError as e: print('ERR',nm,e,hex(E.ireg('EIP'))); continue
    s=E.ireg('EAX'); DST=0x20000000
    E.mu.reg_write(UC_X86_REG_ESP,STK-4); E.mu.mem_write(STK-4,struct.pack('<I',SENT)); E.w('EAX',s); E.w('EBX',u); E.w('EDX',DST)
    try: E.mu.emu_start(0x1d97a,SENT,timeout=60*10**6)       # 0x1d97a = read(struct, count, dest): runs the bit-stream decoder
    except UcError as e: print('ERR read',nm,e,hex(E.ireg('EIP'))); continue
    print(nm.decode(),'read',u,'ret',E.ireg('EAX'),flush=True)
    open(OUT+'/'+nm.decode(),'wb').write(bytes(E.mu.mem_read(DST,u)))
