// all PAK entries decoded by web/js/pak.js vs the guest decodes in DIR (re/lzw_dec.py output): node tools/cmp_pak.mjs SQUARE.PAK DIR
import fs from 'fs'; import { pakOpen } from '../web/js/pak.js';
const p = pakOpen(new Uint8Array(fs.readFileSync(process.argv[2]))); let bad = 0;
for (const n of p.names) { const a = p.get(n), b = fs.readFileSync(process.argv[3] + '/' + n); if (a.length !== b.length || Buffer.compare(Buffer.from(a), b)) { bad++; console.log('DIFF', n, a.length, b.length); } }
console.log(p.names.length, 'entries,', bad, 'differ');
