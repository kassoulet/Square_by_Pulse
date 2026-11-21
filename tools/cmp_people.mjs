// golden diff: web/js/dct.js against the original frame decoder run under Unicorn (re/lzw_dec.py -> people.dec / people.frames).  usage: node tools/cmp_people.mjs DIR
import fs from 'fs';import {decodeFrames} from '../web/js/dct.js';
const D=process.argv[2],dec=fs.readFileSync(D+'/people.dec'),gold=fs.readFileSync(D+'/people.frames');
const fr=decodeFrames(dec,117);let bad=0,tot=0;
fr.forEach((f,i)=>{const g=gold.subarray(i*f.pix.length,(i+1)*f.pix.length);let n=0;for(let k=0;k<g.length;k++)if(g[k]!==f.pix[k])n++;tot+=g.length;bad+=n;if(n)console.log('frame',i,'differs in',n,'bytes');});
console.log(fr.length,'frames,',tot,'bytes compared,',bad,'differing');process.exit(bad?1:0);
