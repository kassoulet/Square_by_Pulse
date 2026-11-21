// node tools/cmp_people_blend.mjs DIR : golden diff of web/js/people.js blend()+up2x() against the original (re/people_gold.py output c%04d.bin)
import fs from 'fs'; import { blend, up2x } from '../web/js/people.js';
let nb = 0, nu = 0, n = 0;
for (const f of fs.readdirSync(process.argv[2]).filter(f => /^c\d+\.bin$/.test(f)).sort()) {
  const b = fs.readFileSync(process.argv[2] + '/' + f), A = b.subarray(0, 27648), B = b.subarray(27648, 55296), p = b.readFloatLE(55296), S = b.subarray(55300, 55300 + 27648), D = b.subarray(55300 + 27648);
  const s = blend(A, B, p); for (let i = 0; i < 27648; i++) if (s[i] != S[i]) nb++;
  const u = up2x(S); for (let i = 0; i < 320 * 240; i++) if (u[i] != D[i]) nu++; n++;
}
console.log(n, 'calls: blend differing bytes', nb, ', up2x differing bytes', nu);
