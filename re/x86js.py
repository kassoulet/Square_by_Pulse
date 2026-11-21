#!/usr/bin/env python3
"""x86js.py - static recompiler: objdump (intel) listing of the original's code -> JavaScript (web/js/plastik-d.gen.mjs).
Only the instruction subset the scenes need (integer + x87; pls_sqrf added div, xchg, rep movs/stos, setcc, indirect calls, PRELUDE/NATIVES/FP24, resume points at present natives).  Usage: x86js.py OUT.mjs LISTING.dis... -- ENTRY...   (see re/NOTES.md)
Registers/flags/x87 stack are module globals, memory is one flat DataView (rt.mjs).  x87 ops are decoded from the opcode bytes, not the text
(objdump's fsub/fdiv mnemonics are reversed in some forms).  Natives (calls we do not translate) are named in NATIVE."""
import re,sys
NATIVE={0x51c7a:'f[S.sp]=Math.trunc(f[S.sp]);',0x51cad:'R.n_fpatan();',0x51e3c:'R.n_present();',0x29c20:'',0x2accc:'S.blk(edi);',0x3d220:'eax=(eax&~0xffff)|R.n_pos();'}   # call+ret net zero: no esp change
import os
for kv in filter(None,os.environ.get('NATIVES','').split('@@')): k,v=kv.split('=',1); NATIVE[int(k,16)]=v   # extra natives: NATIVES='3c20a=expr@@3b700=expr'
FP24=os.environ.get('FP24')   # guest x87 runs with 24-bit precision control: sqrt rounds to float32 too (add/mul/... are rounded in x86rt)
RNG=[tuple(int(y,16) for y in x.split('-')) for x in os.environ.get('RANGE','0-ffffffff').split(',')]; EXTS=set()
def inrng(t): return any(a<=t<b for a,b in RNG)
PATCH={int(kv.split('=',1)[0],16):kv.split('=',1)[1] for kv in filter(None,os.environ.get('PATCHES','').split('@@'))}
def isext(t): return t in NATIVE or not inrng(t)
R32=['eax','ecx','edx','ebx','esp','ebp','esi','edi']
R16={'ax':'eax','cx':'ecx','dx':'edx','bx':'ebx','si':'esi','di':'edi','bp':'ebp','sp':'esp'}
R8L={'al':'eax','cl':'ecx','dl':'edx','bl':'ebx'}; R8H={'ah':'eax','ch':'ecx','dh':'edx','bh':'ebx'}
ins={}
IND=set(); TBL={}
def parse_chunk(lines):
    d={}; last=None
    for l in lines:
        p=l.rstrip('\n').split('\t')
        if len(p)>=3 and re.match(r'\s*[0-9a-f]+:',p[0]):
            a=int(p[0].strip().rstrip(':'),16); b=bytes.fromhex(p[1].strip().replace(' ',''))
            t=p[2].split(); m=t[0]; o=''.join(p[2].split(None,1)[1:]).split('#')[0].strip() if len(t)>1 else ''
            d[a]=[b,m,o]; last=a
        elif len(p)==2 and last in d and re.match(r'\s*[0-9a-f]+:',p[0]): d[last][0]+=bytes.fromhex(p[1].strip().replace(' ',''))   # continuation line (long instruction bytes wrap)
    return d
for fn in sys.argv[2:sys.argv.index('--')]:
    txt=open(fn).read()
    if fn.endswith('.fix'):   # re/mk_fix.py: chunks re-disassembled from true entry points replace the instructions the linear listing got wrong
        for ch in txt.split('Disassembly of section')[1:]:
            d=parse_chunk(ch.split('\n'))
            if d:
                lo=min(d); hi=max(d)+len(d[max(d)][0])
                for a in [a for a in ins if lo<=a<hi]: del ins[a]
                ins.update(d)
    else: ins.update(parse_chunk(txt.split('\n')))
addrs=sorted(ins); nxt={a:(addrs[i+1] if i+1<len(addrs) else a+len(ins[a][0])) for i,a in enumerate(addrs)}
def num(s): return int(s,16) if s.lower().startswith('0x') else int(s)
def memexpr(s):   # [..] or ds:0x..  -> JS address expression
    m=re.search(r'ds:(0x[0-9a-f]+)',s)
    if m: return m.group(1)
    m=re.search(r'\[(.*)\]',s); terms=re.findall(r'([+-]?)([a-z0-9*]+)',m.group(1)); out=[]
    for sg,t in terms:
        sg=sg or '+'
        if '*' in t: r,sc=t.split('*'); e='(%s*%s)'%(r,sc)
        else: e=t
        out.append(sg+e)
    return '('+''.join(out).lstrip('+')+'|0)'
SZ={'BYTE':8,'WORD':16,'DWORD':32,'QWORD':64}
def opnd(s,size=None):
    """-> (kind,expr,size,assign-format) ; kind reg/mem/imm"""
    s=s.strip()
    m=re.match(r'(BYTE|WORD|DWORD|QWORD) PTR (.*)',s)
    if m: return ('mem',memexpr(m.group(2)),SZ[m.group(1)])
    if s in R32: return ('reg',s,32)
    if s in R16: return ('reg',s,16)
    if s in R8L or s in R8H: return ('reg',s,8)
    if re.match(r'^-?(0x[0-9a-f]+|\d+)$',s): return ('imm',str(num(s)),size or 32)
    if s.startswith('[') or 'ds:' in s: return ('mem',memexpr(s),size or 32)
    raise Exception('operand '+s)
def get(o):
    k,e,sz=o
    if k=='imm': return e
    if k=='mem': return {8:'rd8(%s)',16:'rd16(%s)',32:'rd32(%s)'}[sz]%e
    if e in R32: return e
    if e in R16: return '(%s&0xffff)'%R16[e]
    if e in R8L: return '(%s&0xff)'%R8L[e]
    return '((%s>>8)&0xff)'%R8H[e]
def put(o,v):
    k,e,sz=o
    if k=='mem': return {8:'wr8(%s,%s);',16:'wr16(%s,%s);',32:'wr32(%s,%s);'}[sz]%(e,v)
    if e in R32: return '%s=(%s)|0;'%(e,v)
    if e in R16: r=R16[e]; return '%s=(%s&~0xffff)|((%s)&0xffff);'%(r,r,v)
    if e in R8L: r=R8L[e]; return '%s=(%s&~0xff)|((%s)&0xff);'%(r,r,v)
    r=R8H[e]; return '%s=(%s&~0xff00)|(((%s)&0xff)<<8);'%(r,r,v)
def sx(v,sz): return '(%s)'%v if sz==32 else ('((%s)<<%d>>%d)'%(v,32-sz,32-sz))
def zx(v,sz): return '(%s)'%v if sz==32 else '((%s)&%s)'%(v,hex((1<<sz)-1))
COND={'e':'zf','ne':'!zf','l':'(sf!==of)','ge':'(sf===of)','le':'(zf||sf!==of)','g':'(!zf&&sf===of)','b':'cf','ae':'!cf','be':'(cf||zf)','a':'(!cf&&!zf)','s':'sf','ns':'!sf','z':'zf','nz':'!zf','c':'cf','nc':'!cf'}
def fl(sz,res,cfe='0',ofe='0'):   # flags from a result expression (already computed into t)
    sh=sz-1
    return 'zf=(%s)===0;sf=((%s)>>>%d&1)===1;cf=%s;of=%s;'%(zx('t',sz) if sz<32 else 't',zx('t',sz) if sz<32 else 't',sh,cfe,ofe)
def gen(a):
    b,m,o=ins[a]; n=nxt[a]; ops=[x.strip() for x in re.split(r',(?![^\[]*\])',o)] if o else []
    if b[0]>=0xd8 and b[0]<=0xdf: return fpu(a,b,m,o)
    if len(ops)==2 and m not in('lea','movzx','movsx'):   # a bare memory operand takes the size of the register operand
        for i in (0,1):
            r=ops[1-i]; w=32 if r in R32 else 16 if r in R16 else 8 if (r in R8L or r in R8H) else 0
            if w and 'PTR' not in ops[i] and ('ds:' in ops[i] or ops[i].startswith('[')): ops[i]={8:'BYTE',16:'WORD',32:'DWORD'}[w]+' PTR '+ops[i]
    if m=='mov':
        d=opnd(ops[0]); s=opnd(ops[1],d[2]); return put(d,get(s))
    if m in('movzx','movsx'):
        d=opnd(ops[0]); s=opnd(ops[1]); return put(d,get(s) if m=='movzx' else sx(get(s),s[2]))
    if m=='lea': d=opnd(ops[0]); return put(d,memexpr(ops[1]))
    if m in('add','sub','cmp','and','or','xor','test','adc','sbb'):
        d=opnd(ops[0]); s_=opnd(ops[1],d[2]); sz=d[2]; mk=hex((1<<sz)-1); sb=sz-1
        r='a_=(%s)>>>0;b_=(%s)>>>0;'%(get(d) if sz==32 else get(d),get(s_) if s_[0]!='imm' else str(int(get(s_))&((1<<sz)-1)))
        if sz<32: r='a_=%s;b_=%s;'%(get(d),get(s_) if s_[0]!='imm' else str(int(get(s_))&((1<<sz)-1)))
        if m in('add','adc'):
            c='(cf?1:0)' if m=='adc' else '0'; r+='q_=a_+b_+%s;t=%s;cf=q_>%s;of=(((a_^t)&(b_^t))>>>%d&1)===1;'%(c,'q_|0' if sz==32 else 'q_&'+mk,mk,sb)
        elif m in('sub','cmp','sbb'):
            c='(cf?1:0)' if m=='sbb' else '0'; r+='q_=a_-b_-%s;t=%s;cf=q_<0;of=(((a_^b_)&(a_^t))>>>%d&1)===1;'%(c,'q_|0' if sz==32 else 'q_&'+mk,sb)
        else:
            op={'and':'&','or':'|','xor':'^','test':'&'}[m]; r+='t=(a_%sb_)%s;cf=false;of=false;'%(op,'|0' if sz==32 else '&'+mk)
        r+='zf=(t%s)===0;sf=((t>>>%d)&1)===1;'%('' if sz==32 else '&'+mk,sb)
        if m not in('cmp','test'): r+=put(d,'t')
        return r
    if m in('inc','dec'):
        d=opnd(ops[0]); sz=d[2]; op='+' if m=='inc' else '-'
        return 'a_=%s;t=(a_%s1)|0;zf=%s===0;sf=((%s)>>>%d&1)===1;of=%s;'%(zx(get(d),sz),op,zx('t',sz),zx('t',sz),sz-1,'a_===%s'%('0x7fffffff' if m=='inc' else '-0x80000000') if sz==32 else 'false')+put(d,'t')
    if m=='cdq': return 'edx=eax>>31;'
    if m=='not': d=opnd(ops[0]); return put(d,'~(%s)'%get(d))
    if m=='shld' and re.match(r'^(0x)?[0-9a-f]+$',ops[2]):   # 32-bit, immediate count
        d=opnd(ops[0]); sr=opnd(ops[1]); k=num(ops[2])&31
        if not k: return ''
        return 'a_=%s;t=((a_<<%d)|((%s)>>>%d))|0;cf=((a_>>>%d)&1)===1;zf=t===0;sf=t<0;of=false;'%(get(d),k,get(sr),32-k,32-k)+put(d,'t')
    if m=='neg': d=opnd(ops[0]); sz=d[2]; return 'a_=%s;t=(-a_)|0;cf=a_!==0;of=false;zf=t===0;sf=t<0;'%get(d)+put(d,'t')
    if m in('shl','shr','sar'):
        d=opnd(ops[0]); sz=d[2]; c=ops[1]; k=str(num(c)) if re.match(r'^(0x)?[0-9a-f]+$',c) else None
        if k is None:
            if c!='cl': raise Exception('shift by '+c)
            v=get(d); op={'shl':'a_<<k_','shr':'a_>>>k_','sar':'a_>>k_'}[m]; a0=sx(v,sz) if m=='sar' else zx(v,sz)
            return 'a_=%s;k_=ecx&31;if(k_){t=(%s)|0;cf=%s;zf=%s===0;sf=((%s)>>>%d&1)===1;of=false;'%(a0,op,('((a_>>>(32-k_))&1)===1' if m=='shl' else '((a_>>>(k_-1))&1)===1'),zx('t',sz),zx('t',sz),sz-1)+put(d,'t')+'}'
        k=int(k)&31
        if not k: return ''
        v=get(d)
        if m=='shl': r='a_=%s;t=(a_<<%d)|0;cf=((a_>>>%d)&1)===1;'%(v,k,32-k)
        elif m=='shr': r='a_=%s;t=(a_>>>%d)|0;cf=((a_>>>%d)&1)===1;'%(zx(v,sz),k,k-1)
        else: r='a_=%s;t=(a_>>%d)|0;cf=((a_>>%d)&1)===1;'%(sx(v,sz),k,k-1)
        return r+'zf=%s===0;sf=((%s)>>>%d&1)===1;of=false;'%(zx('t',sz),zx('t',sz),sz-1)+put(d,'t')
    if m=='imul':
        d=opnd(ops[0])
        if len(ops)==2: s=opnd(ops[1]); return put(d,'Math.imul(%s,%s)'%(get(d),get(s)))
        if len(ops)==3: s=opnd(ops[1]); i=opnd(ops[2]); return put(d,'Math.imul(%s,%s)'%(get(s),i[1]))
        return 'b_=BigInt(eax)*BigInt(%s);eax=Number(BigInt.asIntN(32,b_));edx=Number(b_>>32n);cf=of=edx!==(eax>>31);'%get(d)   # edx:eax = eax*r/m32 (signed)
    if m=='mul':
        d=opnd(ops[0])
        if ops[0].strip() in ('al','ah','bl','bh','cl','ch','dl','dh') or 'BYTE' in ops[0]: return 't=(eax&255)*(%s);eax=(eax&~0xffff)|t;cf=of=t>255;'%get(d)
        return 'b_=BigInt(eax>>>0)*BigInt(%s>>>0);eax=Number(BigInt.asIntN(32,b_));edx=Number(BigInt.asIntN(32,b_>>32n));cf=of=edx!==0;'%get(d)
    if m=='idiv': s=opnd(ops[0]); return 'q_=Math.trunc((edx*4294967296+(eax>>>0))/%s);r_=(edx*4294967296+(eax>>>0))-q_*%s;eax=q_|0;edx=r_|0;'%(get(s),get(s))
    if m=='push': s=opnd(ops[0]); return 'r_=%s;esp=(esp-4)|0;wr32(esp,r_);'%get(s)   # value first: push [esp+x] addresses the old esp
    if m=='pop': d=opnd(ops[0]); return 'a_=rd32(esp);esp=(esp+4)|0;'+put(d,'a_')
    if m=='pusha': return 't=esp;'+''.join('esp=(esp-4)|0;wr32(esp,%s);'%('t' if r=='esp' else r) for r in R32)
    if m=='popa': return ''.join('esp=(esp+4)|0;'+('' if r=='esp' else '%s=rd32(esp-4);'%r) for r in reversed(R32))
    if m=='out': return 'R.out(edx&0xffff,%s);'%('eax&0xff' if ops[1]=='al' else 'eax')
    if m in('rol','ror'):
        d=opnd(ops[0]); k=int(num(ops[1]))&31 if ops[1]!='cl' else None; v=get(d); kk=str(k) if k is not None else '(ecx&31)'
        return 'a_=%s>>>0;k_=%s;t=k_?(%s):a_|0;'%(v,kk,'(a_<<k_|a_>>>(32-k_))|0' if m=='rol' else '(a_>>>k_|a_<<(32-k_))|0')+put(d,'t')
    if m=='sahf': return 'cf=(eax>>8&1)===1;zf=(eax>>14&1)===1;sf=(eax>>15&1)===1;'
    if m=='div': s=opnd(ops[0]); return 'k_=%s>>>0;if(edx===0){q_=Math.floor((eax>>>0)/k_);r_=(eax>>>0)-q_*k_;}else{b_=((BigInt(edx>>>0)<<32n)|BigInt(eax>>>0));q_=Number(b_/BigInt(k_));r_=Number(b_%%BigInt(k_));}eax=q_|0;edx=r_|0;'%get(s)   # unsigned; ponytail: no #DE on divide by zero or quotient overflow
    if m=='xchg' and ops[0]!=ops[1]: d=opnd(ops[0]); s=opnd(ops[1]); return 'x_=%s;'%get(d)+put(d,get(s))+put(s,'x_')
    if m=='movs':   # single string move, DF clear
        n=4 if 'DWORD' in ops[0] else 2 if ' WORD' in ' '+ops[0] else 1; ro,wo={4:('rd32','wr32'),2:('rd16','wr16'),1:('rd8','wr8')}[n]
        return '%s(edi,%s(esi));esi=(esi+%d)|0;edi=(edi+%d)|0;'%(wo,ro,n,n)
    if m=='rep' and re.match(r'(movs|stos)',ops[0] if ops else ''):   # ponytail: direction flag assumed clear
        n=4 if 'DWORD' in ops[0] else 2 if ' WORD' in ' '+ops[0] else 1; ro,wo={4:('rd32','wr32'),2:('rd16','wr16'),1:('rd8','wr8')}[n]
        if ops[0].startswith('movs'): return 'while(ecx!==0){%s(edi,%s(esi));esi=(esi+%d)|0;edi=(edi+%d)|0;ecx=(ecx-1)|0;}'%(wo,ro,n,n)
        return 'while(ecx!==0){%s(edi,eax);edi=(edi+%d)|0;ecx=(ecx-1)|0;}'%(wo,n)
    if m.startswith('set') and m[3:] in COND: d=opnd(ops[0]); return put(d,'(%s)?1:0'%COND[m[3:]])
    if m=='nop' or m=='xchg' and ops[0]==ops[1]: return ''
    if m=='jmp' and a in TBL: d=opnd(ops[0]); return 'pc=%s;continue;'%get(d)   # switch table jump
    if m=='jmp': return 'pc=%s;continue;'%hex(num(ops[0].split()[0]))
    if m.startswith('j') and m[1:] in COND: return 'if(%s){pc=%s;continue;}'%(COND[m[1:]],hex(num(ops[0].split()[0])))
    if m=='call' and not re.match(r'^(0x)?[0-9a-f]+$',ops[0].split()[0]):   # indirect: dispatch through the table of generated functions
        return 'r_=%s;esp=(esp-4)|0;R.ind(r_);'%get(opnd(ops[0]))
    if m=='call':
        t=num(ops[0].split()[0]); return ('R.S.rpc=0x%x;R.S.rfn=@E@;'%n if 'PRESENT' in NATIVE[t] else '')+NATIVE[t] if t in NATIVE else 'esp=(esp-4)|0;f_%x();'%t
    if m=='ret': k=num(ops[0]) if ops else 0; return 'esp=(esp+%d)|0;return;'%(4+k)
    raise Exception('unhandled %s %s @%x'%(m,o,a))
def fpu(a,b,m,o):
    r=fpu_(a,b,m,o)
    if FP24: r=r.replace('Math.sqrt(f[sp])','Math.fround(Math.sqrt(f[sp]))')
    return re.sub(r'(?<![A-Za-z_.])sp(?![A-Za-z_])','S.sp',r).replace('eax=(eax&~0xffff)|fsw;','eax=(eax&~0xffff)|S.fsw;')
def fpu_(a,b,m,o):
    o0=b[0]; mod=b[1]>>6; reg=(b[1]>>3)&7; i=b[1]&7
    mem=re.search(r'(BYTE|WORD|DWORD|QWORD|TBYTE) PTR (.*)',o)
    if mod!=3:
        ad=memexpr(mem.group(2)); ar={0xd8:('rdf32',32),0xdc:('rdf64',64),0xd9:('rdf32',32),0xdd:('rdf64',64),0xdb:('rd32',32),0xdf:('rd16',16),0xda:('rd32',32),0xde:('rd16',16)}[o0]
        arith=['add','mul','com','comp','sub','subr','div','divr']
        if o0 in(0xd8,0xdc):
            rd='%s(%s)'%(ar[0],ad)
            if reg in(2,3): return 'fp_com(%s);'%rd+('sp++;' if reg==3 else '')
            return 'fp_%s(%s);'%(arith[reg],rd)
        if o0==0xd9:
            if reg==0: return 'fpush(rdf32(%s));'%ad
            if reg==2: return 'wrf32(%s,f[sp]);'%ad
            if reg==3: return 'wrf32(%s,f[sp]);sp++;'%ad
            if reg==5: return ''  # fldcw: CW is constant in our model (0x127f; frndint is native)
            if reg==7: return 'wr16(%s,0x127f);'%ad
        if o0==0xdd:
            if reg==0: return 'fpush(rdf64(%s));'%ad
            if reg==2: return 'wrf64(%s,f[sp]);'%ad
            if reg==3: return 'wrf64(%s,f[sp]);sp++;'%ad
        if o0==0xdb:
            if reg==0: return 'fpush(rd32(%s)|0);'%ad
            if reg in(2,3): return 'wr32(%s,fist(f[sp]));%s'%(ad,'sp++;' if reg==3 else '')
        if o0==0xdf and reg==7: return 'R.wrf64i(%s,f[sp]);sp++;'%ad
        if o0==0xdf and reg==5: return 'fpush((rd32(%s+4)|0)*4294967296+(rd32(%s)>>>0));'%(ad,ad)
        if o0==0xdf and reg==0: return 'fpush(sx16(rd16(%s)));'%ad
        raise Exception('fpu mem %x /%d %s @%x'%(o0,reg,o,a))
    arith=['add','mul','com','comp','sub','subr','div','divr']
    if o0==0xd8: return 'fp_%s_st(%d);'%(arith[reg],i) if reg not in(2,3) else ('fp_com_st(%d);'%i if reg==2 else 'fp_com_st(%d);sp++;'%i)
    if o0==0xdc:   # st(i) = st(i) op st0 ; reg 4/5 and 6/7 swapped vs d8
        nm={0:'add',1:'mul',4:'subr',5:'sub',6:'divr',7:'div'}[reg]; return 'fp_%s_to(%d);'%(nm,i)
    if o0==0xde:
        if reg==3 and i==1: return 'fp_com_st(1);sp+=2;'
        nm={0:'add',1:'mul',4:'subr',5:'sub',6:'divr',7:'div'}[reg]; return 'fp_%s_to(%d);sp++;'%(nm,i)
    if o0==0xd9:
        if reg==0: return 'fpush(f[sp+%d]);'%i
        if reg==1: return 'fxch(%d);'%i
        t={(4,0):'f[sp]=-f[sp];',(4,1):'f[sp]=Math.abs(f[sp]);',(5,0):'fpush(1);',(5,6):'fpush(0);',(7,2):'f[sp]=Math.sqrt(f[sp]);',(7,6):'f[sp]=Math.sin(f[sp]);',(7,7):'f[sp]=Math.cos(f[sp]);',(7,4):'f[sp]=Math.trunc(f[sp]);'}
        if (reg,i) in t: return t[(reg,i)]
        raise Exception('fpu d9 %x %x @%x'%(reg,i,a))
    if o0==0xdd:
        if reg==3: return 'f[sp+%d]=f[sp];sp++;'%i
        if reg==2: return 'f[sp+%d]=f[sp];'%i
    if o0==0xdf and b[1]==0xe0: return 'eax=(eax&~0xffff)|fsw;'
    raise Exception('fpu reg %x %x @%x %s'%(o0,b[1],a,o))
FW={'add','sub','cmp','and','or','xor','test','neg','shl','shr','sar'}   # overwrite all flags we model
FR={'adc','sbb','sahf_','lahf','pushf'}
def live(a,depth=60):
    """may the flags set by the instruction at a be read before being overwritten?  (conservative: unknown -> True)"""
    a=nxt.get(a)
    while depth>0 and a in ins:
        m=ins[a][1]; depth-=1
        if m.startswith('j') and m[1:] in COND: return True
        if m in FR or m.startswith('set') or m.startswith('cmov'): return True
        if m=='jmp': a=num(ins[a][2].split()[0]); continue
        if m in('ret','call'): return False
        if m in FW: return False
        a=nxt.get(a)
    return True
def strip(code):
    code=re.sub(r'(?<![A-Za-z_.])(?:cf|of|zf|sf)=[^;]*;','',code)
    for v in ('a_','b_'):   # operand temporaries only the flags used
        if not re.search(r'(?<![A-Za-z_])%s(?!=)'%v,code): code=re.sub(r'(?<![A-Za-z_])%s=[^;]*;'%v,'',code)
    return code
def reach(entry):
    seen=set(); todo=[entry]; calls=set()
    while todo:
        a=todo.pop()
        while a in ins and a not in seen:
            seen.add(a); b,m,o=ins[a]
            if m=='call':
                if not re.match(r'^(0x)?[0-9a-f]+$',o.split()[0]): IND.add(a); a=nxt[a]; continue   # an indirect call returns: keep scanning
                t=num(o.split()[0])
                if not isext(t): calls.add(t)
                elif t not in NATIVE: EXTS.add(t)
            if m=='jmp' or (m.startswith('j') and m[1:] in COND):
                if not re.match(r'^(0x)?[0-9a-f]+$',o.split()[0]):
                    tm=re.search(r'\[(\w+)\*4\+(0x[0-9a-f]+)\]',o)   # switch jump table jmp [reg*4+table] (cs: or ds:): the targets are read from the FLAT image
                    if m=='jmp' and tm and os.environ.get('FLAT'):
                        fl=open(os.environ['FLAT'],'rb'); fl.seek(int(tm.group(2),16)); tb=[]
                        while len(tb)<64:
                            v=int.from_bytes(fl.read(4),'little')
                            if not(0x1c000<=v<0x58000 and v in ins): break
                            tb.append(v)
                        todo.extend(tb); TBL[a]=tb
                    else: IND.add(a)
                    break
                todo.append(num(o.split()[0]))
            if m=='jmp' or m=='ret': break
            a=nxt[a]
    return sorted(seen),calls
BAD=[]
def main():
    ents=[int(x,16) for x in sys.argv[sys.argv.index('--')+1:]]
    funcs=[]; todo=list(ents); done=set()
    out=["// GENERATED by re/x86js.py from the original binary's code (see re/NOTES.md, recompiler evaluation).  Do not edit.\nimport * as R from './x86rt.mjs';\nconst {rd8,rd16,rd32,wr8,wr16,wr32,rdf32,rdf64,wrf32,wrf64,f,fpush,fxch,fist,sx16,fp_add,fp_mul,fp_sub,fp_subr,fp_div,fp_divr,fp_com,fp_add_st,fp_mul_st,fp_sub_st,fp_subr_st,fp_div_st,fp_divr_st,fp_com_st,fp_add_to,fp_mul_to,fp_sub_to,fp_subr_to,fp_div_to,fp_divr_to}=R;\nconst S=R.S;let k_=0,eax=0,ecx=0,edx=0,ebx=0,esp=0,ebp=0,esi=0,edi=0,cf=false,zf=false,sf=false,of=false,a_=0,b_=0,x_=0,t=0,q_=0,r_=0;\n// sp (x87 stack pointer) lives in S.sp: use accessor shims\n"]
    body=[]
    while todo:
        e=todo.pop()
        if e in done: continue
        done.add(e); s,c=reach(e); todo+=list(c)
        lab=set()
        for a in s:
            m=ins[a][1]
            if (m=='jmp' or (m.startswith('j') and m[1:] in COND)) and re.match(r'^(0x)?[0-9a-f]+$',ins[a][2].split()[0]): lab.add(num(ins[a][2].split()[0]))
        L=['export function f_%x(pc0){let pc=pc0||%s;for(;;){switch(pc){'%(e,hex(e))]; CS=[]   # CS: (address, case text) in address order
        for a in s:
            try: g=gen(a)
            except Exception as ex: BAD.append((e,str(ex))); g='throw new Error("unhandled");'
            if os.environ.get('HIST'): g='(globalThis.HC||(globalThis.HC={}))[%d]=(globalThis.HC[%d]|0)+1;'%(a,a)+g   # HIST=1: per-instruction execution counts (profiling aid, globalThis.HC)
            g=PATCH.get(a,'')+g   # PATCHES='addr=js@@addr=js': JS run before the instruction at addr (hand-optimised loops)
            g=g.replace('@E@','0x%x'%e)
            t='case %s:/*%s %s*/ %s'%(hex(a),ins[a][1],ins[a][2],g if (ins[a][1] not in FW|{'inc','dec','adc','sbb','imul'} or live(a)) else strip(g))
            if nxt[a] not in s and ins[a][1] not in('ret','jmp'): t+='pc=%s;continue;'%hex(nxt[a])
            CS.append((a,t))
        PIECE=int(os.environ.get('PIECE','100'))
        if len(CS)<=PIECE*3:
            L+=[t for a,t in CS]; L.append('default:throw new Error("pc "+pc.toString(16))}}}')
            body.append('\n'.join(L))
        else:   # V8 does not optimise one huge switch-in-a-loop function (and runs it in the interpreter): split into pieces of PIECE instructions; a piece returns the next pc when control leaves it (-1 = ret)
            ch=[CS[i:i+PIECE] for i in range(0,len(CS),PIECE)]; out_=[]
            for k,c in enumerate(ch):
                inside={a for a,t in c}; fix=lambda t:re.sub(r'pc=(?!0x[0-9a-f]+;)([^;]+);continue;',r'return \1;',re.sub(r'return;','return -1;',re.sub(r'pc=(0x[0-9a-f]+);continue;',lambda m_:m_.group(0) if int(m_.group(1),16) in inside else 'return %s;'%m_.group(1),t)))
                last=c[-1][0]; tail='' if ins[last][1] in('ret','jmp') or (nxt[last] not in s) else 'return %s;'%hex(nxt[last])
                out_.append('function f_%x_%d(pc){for(;;){switch(pc){'%(e,k)+''.join(fix(t) for a,t in c)+tail+'default:throw new Error("pc "+pc.toString(16))}}}'%())
            disp='export function f_%x(pc0){let pc=pc0||%s;for(;;){'%(e,hex(e))+'pc='+''.join('pc<%s?f_%x_%d(pc):'%(hex(ch[k+1][0][0]),e,k) for k in range(len(ch)-1))+'f_%x_%d(pc);if(pc<0)return;}}'%(e,len(ch)-1)
            body.append('\n'.join(out_)+'\n'+disp)
    print('externals:',' '.join('%x'%x for x in sorted(EXTS)));print(len(IND),'indirect call/jmp sites:',' '.join('%x'%x for x in sorted(IND))[:300]);print(len(done),'functions',len(BAD),'unhandled');[print(' f_%x: %s'%b) for b in BAD[:60]]; print('called:',' '.join('%x'%x for x in sorted(done)))
    pre=open(os.environ['PRELUDE']).read() if os.environ.get('PRELUDE') else ''   # PRELUDE=file: JS appended to the module (native helpers that touch the registers / FN)
    open(sys.argv[1],'w').write(''.join(out)+pre+'\n'.join(body)+'\nexport const FN={'+','.join('0x%x:f_%x'%(e,e) for e in sorted(done))+'};'+'\nexport function setRegs(o){({eax,ecx,edx,ebx,esp,ebp,esi,edi}=o);}\nexport function getRegs(){return {eax,ecx,edx,ebx,esp,ebp,esi,edi};}\n')
main()
