import re,sys
L=[]
on=False
for l in open(sys.argv[1]):
    m=re.match(r'\s*([0-9a-f]+):\t(?:[0-9a-f]{2} )+\s*\t?(.*)',l)
    if not m: continue
    a=int(m.group(1),16)
    if a<0x2b6bc: continue
    if a>0x2b8df: break
    L.append((a,m.group(2).strip()))
def mem(op):
    m=re.match(r'BYTE PTR \[(e[sb][ix])([+-]0x[0-9a-f]+)?\]',op); 
    if m:
        r,o=m.groups(); o=int(o,16) if o else 0
        return ('s' if r=='esi' else None,o,r)
    return None
cl_zero=True
out=[];i=0;ind=''
def sgn(o): return ('+%d'%o) if o>=0 else '%d'%o
while i<len(L):
    a,t=L[i]; mn,_,ops=t.partition(' '); ops=[x.strip() for x in ops.split(',')]
    if a==0x2b6bc: out.append('do{bx=0;ax=0;al=0;ah=0;cl=0;'); i+=1; continue
    if mn=='xor': i+=1; continue
    if mn=='mov' and ops[0]=='bl': 
        r,o,_=mem(ops[1]); out.append('bx=m[s%s];'%sgn(o)); i+=1; continue
    if mn in('add','sub') and ops[0]=='bl':
        r,o,_=mem(ops[1]); nm,_,no=L[i+1][1].partition(' '); no=no.strip()
        assert nm==('adc' if mn=='add' else 'sbb') and no.startswith('bh,'),(hex(a),L[i+1]); 
        assert no=='bh, 0x0' or no=='bh,cl' or no.replace(' ','')=='bh,0x0' or no.replace(' ','') =='bh,cl', no
        if no.replace(' ','')=='bh,cl': assert cl_zero
        out.append('bx=(bx%sm[s%s])&65535;'%('+' if mn=='add' else '-',sgn(o))); i+=2; continue
    if mn=='mov' and ops[0] in('al','ah'):
        m=re.match(r'BYTE PTR \[ebx\+0x([0-9a-f]+)\]',ops[1]); assert m
        out.append('%s=m[0x%s+bx];'%(ops[0],m.group(1))); i+=1; continue
    if mn=='inc' and ops[0]=='esi': out.append('s++;'); i+=1; continue
    if mn=='inc' and ops[0]=='edi': out.append('d++;'); i+=1; continue
    if mn=='mov' and ops[0]=='WORD PTR [edi]': out.append('m[d]=al;m[d+1]=ah;'); i+=1; continue
    if mn=='mov' and ops[0]=='cl': out.append('cl=%s;do{'%ops[1]); i+=1; continue
    if mn=='dec' and ops[0]=='cl': out.append('}while(--cl);'); i+=1; assert L[i][1].startswith('jne'); i+=1; continue
    if mn=='dec' and ops[0]=='ch': out.append('}while(--ch);'); i+=1; assert L[i][1].startswith('jne'); i+=1; continue
    raise Exception((hex(a),t))
    i+=1
cl_zero=True
print('{const m=R.m8;let s=(edx+0x280)|0,d=(eax+0x280)|0,ch=0xc3,bx,ax,al,ah,cl;'+''.join(out)+'}')
