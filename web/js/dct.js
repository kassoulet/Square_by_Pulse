// dct.js - exact port of the frame decoder of SQUARE.EXE (0x38f7b -> 0x38cf6, IDCT 0x38938) for PEOPLE.LZW / ZEBOU.LZW.
// Input = the byte stream that the original bit-stream reader (0x1d97a) delivers (re/lzw_dec.py writes it as *.dec); the bit-stream layer itself is NOT ported.
// Per frame: header u8 q, u16 W, u16 H, u8 planes; then for zigzag position 63..0: position 0 = DC as 3-byte pairs (two signed 12-bit values for blocks k,k+1),
// others = one signed byte per block; DC is prefix-summed over the blocks, coefficients are multiplied by (r+c)*q+3 (q of the FIRST frame, the guest builds the table once),
// 8x8 integer IDCT (two passes, fixed point), output transposed and clamped to 0..255.
export const ZZ=[0, 0, 0, 1, 1, 0, 2, 0, 1, 1, 0, 2, 0, 3, 1, 2, 2, 1, 3, 0, 4, 0, 3, 1, 2, 2, 1, 3, 0, 4, 0, 5, 1, 4, 2, 3, 3, 2, 4, 1, 5, 0, 6, 0, 5, 1, 4, 2, 3, 3, 2, 4, 1, 5, 0, 6, 0, 7, 1, 6, 2, 5, 3, 4, 4, 3, 5, 2, 6, 1, 7, 0, 7, 1, 6, 2, 5, 3, 4, 4, 3, 5, 2, 6, 1, 7, 2, 7, 3, 6, 4, 5, 5, 4, 6, 3, 7, 2, 7, 3, 6, 4, 5, 5, 4, 6, 3, 7, 4, 7, 5, 6, 6, 5, 7, 4, 7, 5, 6, 6, 5, 7, 6, 7, 7, 6, 7, 7];
const imul=Math.imul;
function idct(b){const t=new Int32Array(64);
  for(let pass=0;pass<2;pass++){const s=pass?t:b,d=pass?b:t;
    for(let it=0;it<8;it++){const o=it*8,x0=s[o],x1=s[o+1],x2=s[o+2],x3=s[o+3],x4=s[o+4],x5=s[o+5],x6=s[o+6],x7=s[o+7];
      let e=imul(x0+x4|0,0xb505),f=imul(x0-x4|0,0xb505);
      const a=imul(x2,0x61f8)-imul(x6,0xec83)|0,c=imul(x6,0x61f8)+imul(x2,0xec83)|0;
      const t128=e+c|0,x2n=f+a|0,t12c=f-a|0;e=e-c|0;
      const t130=imul(x3+x5|0,0xb505)+0x2000>>14,t134=imul(x3-x5|0,0xb505)+0x2000>>14;
      const t108=x1<<2,e7=x7<<2,t138=t108+t130|0,t13c=t134+e7|0,t140=t108-t130|0,e8=e7-t134|0;
      const t144=imul(t138,0x3ec5)+imul(t13c,0xc7c)|0,t148=imul(t138,0xc7c)-imul(t13c,0x3ec5)|0;
      const t14c=imul(t140,0x238e)+imul(e8,0x3537)|0,e9=imul(t140,0x3537)-imul(e8,0x238e)|0;
      const R=v=>v+0x10000>>17;
      d[0*8+it]=R(t128+t144|0);d[1*8+it]=R(x2n+e9|0);d[2*8+it]=R(t12c+t14c|0);d[3*8+it]=R(t148+e|0);
      d[4*8+it]=R(e-t148|0);d[5*8+it]=R(t12c-t14c|0);d[6*8+it]=R(x2n-e9|0);d[7*8+it]=R(t128-t144|0);}}}
// decode `n` frames from bytes u8; returns [{q,w,h,planes,pix:Uint8Array}] (planes interleaved like the original)
export function decodeFrames(u8,n){let p=0,q0=null;const out=[];
  for(let fi=0;fi<n;fi++){const q=u8[p],w=u8[p+1]|u8[p+2]<<8,h=u8[p+3]|u8[p+4]<<8,pl=u8[p+5];p+=6;if(q0===null)q0=q;
    const nb=(w>>3)*(h*pl>>3),co=new Int32Array(nb*64);
    for(let pos=63;pos>=0;pos--){const r=ZZ[pos*2],c=ZZ[pos*2+1];
      if(!r&&!c){for(let k=0;k<nb;k+=2){const v=u8[p]|u8[p+1]<<8|u8[p+2]<<16;p+=3;co[k*64]=v<<20>>20;if(k+1<nb)co[(k+1)*64]=v<<8>>20;}}
      else for(let k=0;k<nb;k++)co[k*64+r*8+c]=u8[p++]<<24>>24;}
    for(let k=1;k<nb;k++)co[k*64]=co[k*64]+co[(k-1)*64]|0;
    const pix=new Uint8Array(w*h*pl);let k=0;
    for(let pp=0;pp<pl;pp++)for(let y=0;y<h;y+=8)for(let x=0;x<w;x+=8,k++){const b=co.subarray(k*64,k*64+64);
      for(let i=0;i<8;i++)for(let j=0;j<8;j++)b[i*8+j]=imul(b[i*8+j],(i+j)*q0+3);
      idct(b);
      for(let ro=0;ro<8;ro++)for(let cl=0;cl<8;cl++){let v=b[cl*8+ro];v=v<0?0:v>255?255:v;pix[pp+(y+ro)*w+x+cl]=v;}}
    out.push({q,w,h,planes:pl,pix});}
  return out;}
