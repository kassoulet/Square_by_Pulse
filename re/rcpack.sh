#!/bin/sh
# re/rcpack.sh FLAT.bin GOLDDIR MAL.json ENTRY(hex) NFRAMES OUT.bin.gz [WORKDIR]
# Records the 4K pages the recompiled scene reads (temporary instrumentation of x86rt.mjs/sqr.gen.mjs, restored afterwards),
# packs entry state + those pages with mk_rcinit.py, then validates the asset with tools/rc_scene_test.mjs.
cd "$(dirname "$0")/.." || exit 1
FLAT=$1; GOLD=$2; MAL=$3; ENTRY=$4; N=$5; OUT=$6; W=${7:-/tmp}
cp web/js/x86rt.mjs $W/rcp.x86rt.bak; cp web/js/sqr.gen.mjs $W/rcp.sqr.bak; cp tools/rc_run.mjs $W/rcp.run.bak
python3 - <<'P'
p='web/js/x86rt.mjs'; s=open(p).read()
s=s.replace("export const rd8=a=>m8[a],rd16=a=>dv.getUint16(a,true),rd32=a=>dv.getInt32(a,true),","export const RP=new Uint8Array(0x8000); export const rd8=a=>(RP[a>>12]=1,m8[a]),rd16=a=>(RP[a>>12]=RP[(a+1)>>12]=1,dv.getUint16(a,true)),rd32=a=>(RP[a>>12]=RP[(a+3)>>12]=1,dv.getInt32(a,true)),",1)
s=s.replace("export const rdf32=a=>dv.getFloat32(a,true),rdf64=a=>dv.getFloat64(a,true),","export const rdf32=a=>(RP[a>>12]=RP[(a+3)>>12]=1,dv.getFloat32(a,true)),rdf64=a=>(RP[a>>12]=RP[(a+7)>>12]=1,dv.getFloat64(a,true)),",1)
s=s.replace("memcpy=(d,s,n)=>{","memcpy=(d,s,n)=>{for(let q=s>>12;q<=(s+n-1)>>12;q++)RP[q]=1;",1)
s+="\nexport const PX=new Proxy(m8,{get:(t,k)=>{if(typeof k==='string'){const a=+k;if(a===a)RP[a>>>12]=1}return t[k]},set:(t,k,v)=>{t[k]=v;return true}});\n"
open(p,'w').write(s)
p='web/js/sqr.gen.mjs'; s=open(p).read()
mk="const MK=(a,n)=>{for(let q=a>>>12;q<=(a+n-1)>>>12;q++)R.RP[q]=1};"
s=s.replace("function BLEND(d, s, a, c) { const m = R.m8,","function BLEND(d, s, a, c) { "+mk+" MK(s,0x4b000);MK(R.rd32(0x10ce80)&0xffff0000,65536);MK(d,0x4b000); const m = R.m8,",1)
s=s.replace("const m = R.m8, A0 = R.rd32(sp),",mk+" const m = R.m8, A0 = R.rd32(sp),",1)
s=s.replace("{const m=R.m8","{const m=R.PX")
s=s.replace("R.wr32(0x10652c, A0);","MK(R.rd32(sp+12),Math.min(R.rd32(sp+4)*R.rd32(sp+8),0x100000));MK(0x1062b8,256);R.wr32(0x10652c, A0);",1)
open(p,'w').write(s)
P
echo "if (process.env.RPOUT) fs.writeFileSync(process.env.RPOUT, R.RP);" >> tools/rc_run.mjs
MAL=$MAL ENTRY=$ENTRY RPOUT=$W/rcp.rp node tools/rc_run.mjs $FLAT $GOLD $N 2>&1 | grep "frames presented" | cut -c1-200
cp $W/rcp.x86rt.bak web/js/x86rt.mjs; cp $W/rcp.sqr.bak web/js/sqr.gen.mjs; cp $W/rcp.run.bak tools/rc_run.mjs
RANGES=$(python3 - $W/rcp.rp <<'P'
import sys
d=open(sys.argv[1],'rb').read(); r=[]
for i,v in enumerate(d):
    if v:
        if r and r[-1][1]==i: r[-1][1]=i+1
        else: r.append([i,i+1])
print(','.join('%x-%x'%(a<<12,b<<12) for a,b in r))
P
)
MAL=$MAL python3 re/mk_rcinit.py $FLAT $GOLD $OUT $ENTRY $RANGES
node tools/rc_scene_test.mjs $OUT $GOLD $N 2>&1 | head -1
