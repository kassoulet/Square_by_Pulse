// Runtime for the statically recompiled original code (sqr338.gen.mjs): flat memory + x87 stack. Adapted from ../_done/plastikx/web/js/x86rt.mjs. The guest x87 runs with 24-bit precision control: add/sub/mul/div/sqrt results are rounded to float32 (F). Memory = low 128 MB of the guest (re/snap2flat.py).
const MEM=0x8000000; export const buf=new ArrayBuffer(MEM), m8=new Uint8Array(buf), dv=new DataView(buf);
export const rd8=a=>m8[a],rd16=a=>dv.getUint16(a,true),rd32=a=>dv.getInt32(a,true),wr8=(a,v)=>{m8[a]=v;},wr16=(a,v)=>dv.setUint16(a,v,true),wr32=(a,v)=>dv.setInt32(a,v,true);
export const rdf32=a=>dv.getFloat32(a,true),rdf64=a=>dv.getFloat64(a,true),wrf32=(a,v)=>dv.setFloat32(a,v,true),wrf64=(a,v)=>dv.setFloat64(a,v,true);
export const f=new Float64Array(16), S={sp:8,fsw:0,pos:()=>0,present:()=>{},blk:()=>{}};
export const fpush=v=>{f[--S.sp]=v;}, fxch=i=>{const t=f[S.sp];f[S.sp]=f[S.sp+i];f[S.sp+i]=t;}, sx16=v=>v<<16>>16;
export const fist=v=>{if(!(Math.abs(v)<2147483648))return -2147483648;const r=Math.round(v);return (Math.abs(v-Math.trunc(v))===0.5&&(r&1))?r-1:r|0;};   // round to nearest even
const F=Math.fround;
const _d=new Float64Array(1),_u=new Uint32Array(_d.buffer);
// 24-bit precision control: round a*b / a+b once to float32.  F(a*b) rounds twice (53 then 24 bits), which is wrong when the double result lands exactly on a float32 tie
// and an operand is not itself a float32 (fld qword, native results); an error term of the exact operation settles the tie.
const tie=p=>{_d[0]=p;return (_u[0]&0x1fffffff)===0x10000000;};
const nudge=(p,up)=>{_d[0]=p;_u[0]+=up?1:-1;return F(_d[0]);};
export let P53=false; export const setPC53=b=>{P53=b;};   // PC=53 (CW 0x127f, the demo's real control word): results stay doubles, rounded to float32 only by the stores
const mulr=(a,b)=>{if(P53)return a*b;const p=a*b,r=F(p);if(F(a)===a&&F(b)===b||!tie(p))return r;
 let c=134217729*a,ah=c-(c-a),al=a-ah;c=134217729*b;const bh=c-(c-b),bl=b-bh;const e=((ah*bh-p)+ah*bl+al*bh)+al*bl;
 return e===0?r:nudge(p,(e>0)===(p>0));};
const divr=(a,b)=>{if(P53)return a/b;const p=a/b,r=F(p);if(F(a)===a&&F(b)===b||!tie(p))return r;
 let c=134217729*p,ph=c-(c-p),pl=p-ph;c=134217729*b;const bh=c-(c-b),bl=b-bh;const m=((ph*bh-p*b)+ph*bl+pl*bh)+pl*bl;   // p*b = fl(p*b)+m exactly
 const e=(a-p*b)-m;return e===0?r:nudge(p,(e>0)===(b>0)===(p>0));};   // e = a-p*b: true quotient is above p when e has the sign of b
const addr=(a,b)=>{if(P53)return a+b;const p=a+b,r=F(p);if(F(a)===a&&F(b)===b||!tie(p))return r;
 const bb=p-a,e=(a-(p-bb))+(b-bb);return e===0?r:nudge(p,(e>0)===(p>0));};

export const fp_add=v=>{f[S.sp]=addr(f[S.sp],v);},fp_mul=v=>{f[S.sp]=mulr(f[S.sp],v);},fp_sub=v=>{f[S.sp]=addr(f[S.sp],-v);},fp_subr=v=>{f[S.sp]=addr(v,-f[S.sp]);},fp_div=v=>{f[S.sp]=divr(f[S.sp],v);},fp_div_raw=v=>{f[S.sp]=f[S.sp]/v;},fp_divr=v=>{f[S.sp]=divr(v,f[S.sp]);};
export const fp_add_st=i=>{f[S.sp]=addr(f[S.sp],f[S.sp+i]);},fp_mul_st=i=>{f[S.sp]=mulr(f[S.sp],f[S.sp+i]);},fp_sub_st=i=>{f[S.sp]=addr(f[S.sp],-f[S.sp+i]);},fp_subr_st=i=>{f[S.sp]=addr(f[S.sp+i],-f[S.sp]);},fp_div_st=i=>{f[S.sp]=divr(f[S.sp],f[S.sp+i]);},fp_divr_st=i=>{f[S.sp]=divr(f[S.sp+i],f[S.sp]);};
export const fp_add_to=i=>{f[S.sp+i]=addr(f[S.sp+i],f[S.sp]);},fp_mul_to=i=>{f[S.sp+i]=mulr(f[S.sp+i],f[S.sp]);},fp_sub_to=i=>{f[S.sp+i]=addr(f[S.sp+i],-f[S.sp]);},fp_subr_to=i=>{f[S.sp+i]=addr(f[S.sp],-f[S.sp+i]);},fp_div_to=i=>{f[S.sp+i]=divr(f[S.sp+i],f[S.sp]);},fp_divr_to=i=>{f[S.sp+i]=divr(f[S.sp],f[S.sp+i]);};
const cmp=(a,b)=>{S.fsw=a!==a||b!==b?0x4500:a>b?0:a<b?0x100:0x4000;};
export const fp_com=v=>cmp(f[S.sp],v), fp_com_st=i=>cmp(f[S.sp],f[S.sp+i]);
export const n_fpatan=()=>{fxch(1);const x=f[S.sp],y=f[S.sp+1];f[S.sp+1]=Math.atan2(y,x);S.sp++;};
export const n_pos=()=>S.pos(), n_present=()=>S.present();
// hooks the driver fills in: out(port,val) VGA ports, n_poll() frame poll 0x1ca79, n_open/n_read file loader, present(buf), memset, ext(addr) = call into code that was not recompiled
export const H={out(){},n_poll(){throw new Error('n_poll')},n_open(){throw new Error('n_open')},slurp(){throw new Error('slurp')},n_read(){},present(){},};
export const out=(p,v)=>H.out(p,v),n_poll=()=>H.n_poll(),n_open=a=>H.n_open(a),slurp=a=>H.slurp(a),n_read=(h,d,n)=>H.n_read(h,d,n),present=(b,e)=>H.present(b,e),memset=(a,v,n)=>m8.fill(v,a,a+n),ext=a=>{throw new Error('call to non-recompiled code 0x'+a.toString(16));};

export const wrf64i=(a,v)=>{let r=Math.round(v);if(Math.abs(v-Math.trunc(v))===0.5&&(r&1))r-=1;const lo=((r%4294967296)+4294967296)%4294967296;dv.setUint32(a,lo,true);dv.setInt32(a+4,Math.floor(r/4294967296),true);};   // fistp qword, round to nearest even
// libc/engine natives for the second scene (29a81): bump allocator (free is a no-op), memcpy, port input, indirect calls (unused)
let brk=0x6000000; export const MS={q:null,i:0};   // MS.q = [[size,addr]...]: replay the guest's own malloc results (guest-heap-layout-dependent reads past a buffer then see the same bytes as the original)
export const malloc=n=>{if(MS.q){let j=MS.i;while(j<MS.q.length&&MS.q[j][0]!==(n>>>0))j++;if(j<MS.q.length){MS.i=j+1;const a=MS.q[j][1];if(MS.q[j][2]){wr32(a-4,MS.q[j][2]);if(MS.q[j][3])wr32(a-4+(MS.q[j][2]&~1),MS.q[j][3]);}if(MS.q[j][4]){const t=atob(MS.q[j][4]);m8.fill(0,a,a+n);for(let i=0;i<t.length;i++)m8[a+i]=t.charCodeAt(i);}return a;}}const p=brk;brk+=((n+15)&~15)+64;return p;}, memcpy=(d,s,n)=>{m8.copyWithin(d,s,s+n);return d;}, inp=p=>H.inp?H.inp(p):0, ind=a=>H.ind(a);
// transcendental natives (the guest ran under QEMU/Unicorn: its x87 sin/exp are the host libm's double functions)
export const cos=x=>Math.cos(x);
export const sin=x=>{let r=Math.sin(x);if(H.tlog)H.tlog('s',x,r);return r;}, exp=x=>{   // 0x3c4c2 = fmul log2e; frndint; fsub; f2xm1; fld1; fadd; fscale at 24-bit precision: the product and the +1 round to float32
  if(x<=-709.7827128933839)return 0; const t=F(x*Math.LOG2E); let n=Math.round(t); if(Math.abs(t-Math.trunc(t))===0.5&&(n&1))n-=1;
  const r=F(Math.pow(2,F(t-n))-1+1)*Math.pow(2,n); if(H.tlog)H.tlog('e',x,r); return r;}, ln=x=>(Math.log(x)/Math.log(2))*Math.LN2;   // ln: fyl2x as Unicorn does it (host double log(x)/log(2)*ln2)
// 0x3c354 = pow(st0=x, st1=y) of the Watcom runtime: integer y with 1<=|y|<2^240 uses square-and-multiply with every fmul rounded to float32 (24-bit precision control); otherwise exp(F(ln2*y) * log2|x|)
export const pow=(x,y)=>{
  if(x===0)return 0;
  if(Number.isInteger(y)&&Math.abs(y)>=1&&Math.abs(y)<2**240){
    let k=Math.abs(y),a=x; while(!(k&1)&&k>1){a=F(a*a);k=Math.floor(k/2);}   // squarings while the low bit is 0
    k=Math.floor(k/2); let c=a, r=a; while(k){c=F(c*c); if(k&1)r=F(r*c); k=Math.floor(k/2);}
    return y<0?F(1/r):r;
  }
  return exp((Math.log(Math.abs(x))/Math.log(2))*F(Math.LN2*y));
};
