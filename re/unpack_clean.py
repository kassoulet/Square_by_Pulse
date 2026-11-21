#!/usr/bin/env python3
"""unpack_clean.py - run SQUARE.EXE's own PMODE/W 1.22 loader under Unicorn until the program entry 0x3b1b8 (Watcom _cstart `jmp short`, string 'WATCOM C/C++32 Run-Time system' at 0x3b1ba)
and dump 64 MB RAM.   usage: python3 unpack_clean.py OUT.bin   (needs unicorn, so no -I; ~30 s)"""
import sys
EXE=__file__.rsplit('/',2)[0]+'/SQUARE.EXE'; OUT=sys.argv[1]
sys.argv=['x','0',EXE,'0x2730','0x356',OUT]
sys.path.insert(0,__file__.rsplit('/',1)[0])
import unpack_pmodew as U
from unicorn import *; from unicorn.x86_const import *
def at_entry(uc,a,sz,ud):
    print('ENTRY',hex(a),{r:hex(uc.reg_read(getattr(__import__('unicorn.x86_const',fromlist=['x']),'UC_X86_REG_'+r))) for r in ('CS','DS','ES','SS','ESP','EAX','EBX','ECX','EDX','ESI','EDI')})
    open(OUT,'wb').write(bytes(uc.mem_read(0,0x4000000))); uc.emu_stop()
ENTRY=0x3b1b8
U.mu.hook_add(UC_HOOK_CODE,at_entry,begin=ENTRY,end=ENTRY)
try: U.mu.emu_start(U.SEG*16+0x5e,0,timeout=120*10**6)
except UcError as e: print('err',e)
print("emu_start returned; cs:eip",hex(U.reg("CS")),hex(U.reg("EIP")))
