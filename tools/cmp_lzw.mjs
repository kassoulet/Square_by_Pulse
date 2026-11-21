// node tools/cmp_lzw.mjs PAKDIR [LZWDIR]: decode every SQUARE.PAK entry (and PEOPLE/ZEBOU.LZW) with web/js/lzw.js and compare with the guest's decode (re/pak_extract.py, re/lzw_dec.py)
import fs from 'fs'; import { lzwDecode } from '../web/js/lzw.js';
const root = new URL('..', import.meta.url).pathname, [pd, ld] = process.argv.slice(2);
const p = fs.readFileSync(root + 'SQUARE.PAK'), dv = new DataView(p.buffer, p.byteOffset), dir = dv.getUint32(8, true);
let bad = 0, n = 0;
const cmp = (name, got, want) => { n++; let d = got.length != want.length ? -1 : 0; for (let i = 0; i < want.length && d >= 0; i++) if (got[i] != want[i]) d++; if (d) { bad++; console.log('DIFF', name, got.length, want.length, d); } };
for (let o = dir; o + 24 <= p.length; o += 24) {
  const name = Buffer.from(p.subarray(o, o + 12)).toString('latin1').replace(/\0.*/, ''), off = dv.getUint32(o + 12, true), us = dv.getUint32(o + 20, true);
  cmp(name, lzwDecode(p.subarray(off), us), fs.readFileSync(pd + '/' + name));
}
if (ld) for (const f of ['PEOPLE', 'ZEBOU']) { const w = fs.readFileSync(`${ld}/${f.toLowerCase()}.dec`); const g = lzwDecode(fs.readFileSync(root + f + '.LZW')); cmp(f + '.LZW (' + g.length + ' bytes, guest tail past the end-code ignored)', g, w.subarray(0, g.length)); }
console.log(n, 'streams compared,', bad, 'differing');
