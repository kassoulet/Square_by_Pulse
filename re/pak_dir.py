#!/usr/bin/env python3
"""pak_dir.py [SQUARE.PAK]: list the directory of SQUARE.PAK ("ALEXC" container, Alex Evans / Statix).
Header: b'ALEXC\\0\\0\\0' + u32 dir_offset (= file size - 24*n). Directory at dir_offset: n x 24 bytes {char name[12] (NUL padded),
u32 offset (absolute), u32 csize, u32 usize}. csize==usize? -> stored (not checked yet). Payload codec: unidentified (see NOTES.md)."""
import struct,sys
p=open(sys.argv[1] if len(sys.argv)>1 else __file__.rsplit('/',2)[0]+'/SQUARE.PAK','rb').read()
assert p[:5]==b'ALEXC'
do=struct.unpack_from('<I',p,8)[0]; n=(len(p)-do)//24; print('dir at',hex(do),n,'entries',(len(p)-do)%24)
tot=0
for i in range(n):
    nm,o,c,u=struct.unpack_from('<12sIII',p,do+24*i); print('%-12s off %8d csize %7d usize %7d %s'%(nm.rstrip(b'\0').decode(),o,c,u,'STORED?' if c==u else '')); tot+=u
print('total usize',tot)
