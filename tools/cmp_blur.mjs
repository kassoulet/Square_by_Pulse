// golden diff of web/js/blur.js against guest 0x2a8e8 captures (re/blur_gold.py): node tools/cmp_blur.mjs DIR
// header per call: cx cy arg3 arg4 p S (float32), then 64000 bytes before and 64000 after.
import fs from 'fs'; import { blur, blurArgs } from '../web/js/blur.js'; import { pakOpen } from '../web/js/pak.js'; import { tab } from '../web/js/people.js';
const d = process.argv[2]; let bad = 0, n = 0, badArgs = 0, badFin = 0;
const lr = pakOpen(new Uint8Array(fs.readFileSync(new URL('../SQUARE.PAK', import.meta.url)))).get('logo.raw'), LG = Uint8Array.from(lr.subarray(768, 768 + 64000), v => v === 255 ? 255 : v + 128);
for (const f of fs.readdirSync(d).filter(f => /^b\d+\.bin$/.test(f)).sort()) {
  const b = fs.readFileSync(d + '/' + f), a = new Float32Array(b.buffer.slice(b.byteOffset, b.byteOffset + 24));
  const mine = blurArgs(a[4], a[5]); if (mine.some((v, i) => v !== a[i])) { badArgs++; if (badArgs < 4) console.log(f, 'args', mine, [...a]); }
  const buf = Uint8Array.from(b.subarray(24, 24 + 64000)); blur(buf, a[0], a[1], a[2], a[3]);
  let diff = 0; for (let i = 0; i < 64000; i++) diff += buf[i] !== b[24 + 64000 + i]; n++; bad += diff > 0;
  const ff = d + '/' + f.replace('b', 'f'); if (!fs.existsSync(ff)) continue; const fin = fs.readFileSync(ff); let fd = 0; for (let i = 0; i < 64000; i++) fd += (LG[i] === 255 ? tab(buf[i]) : LG[i]) !== fin[i]; badFin += fd > 0;   // logo composite (0x393fb..0x39441), logo.raw from the PAK
  if (diff) console.log(f, 'differing pixels', diff);
}
console.log(n, 'calls,', bad, 'blur with differences,', badArgs, 'with different args,', badFin, 'with a different final (logo composite) frame');
