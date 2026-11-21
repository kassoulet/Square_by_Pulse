// Check web/js/rcscene.mjs (the browser driver) against the golden frames: node tools/rc_scene_test.mjs INIT.bin.gz GOLDDIR [frames=40]  (frame n of the driver = golden file 2n)
import fs from 'fs'; import zlib from 'zlib'; import {RcScene, unpackInit} from '../web/js/rcscene.mjs'; import {pakOpen} from '../web/js/pak.js';
const [initf, gd, N = 40] = process.argv.slice(2);
const pak = pakOpen(new Uint8Array(fs.readFileSync(new URL('../web/assets/SQUARE.PAK', import.meta.url)))), S = new RcScene(unpackInit(new Uint8Array(zlib.gunzipSync(fs.readFileSync(initf)))), pak);
const bad = n => { const g = fs.readFileSync(gd + '/f' + String(2 * n).padStart(4, '0') + '.bin'); let d = 0; for (let i = 0; i < g.length; i++) d += S.screen[i] !== g[i]; return d; };
// DAC: replay the guest's palette port writes (dac.json: [tag, port, value]; tag <= 2n-1 precede present n) and compare with the palette the driver shows with frame n
const dg = JSON.parse(fs.readFileSync(gd + '/dac.json')); let gp = new Uint8Array(768), gi = 0, gk = [0, 0], npal = 0;
const palBad = n => { for (; gi < dg.length && dg[gi][0] <= 2 * n - 1; gi++) { const [, p, v] = dg[gi]; if (p === 968) gk = [v, 0]; else if (p === 969) { gp[gk[0] * 3 + gk[1]] = v; if (++gk[1] === 3) { gk[1] = 0; gk[0] = (gk[0] + 1) & 255; } } } const P = S.palShown; let d = 0; for (let i = 0; i < 768; i++) d += P[i] !== gp[i]; return d; };
let nb = 0; for (let n = 0; n < +N; n++) { if (!S.frame(n)) { console.log('scene returned at', n); break; } nb += bad(n) > 0; if (n >= 2) npal += palBad(n) > 0; }
// seek: jump around (forward, backward over checkpoints) and compare again
let sk = 0; for (const n of [+N - 1, 3, +N >> 1, 0, +N - 2]) { S.frame(n); sk += bad(n) > 0; }
console.log(N, 'frames stepped,', nb, 'differing,', npal, 'palette-differing; 5 seeks,', sk, 'differing');
if (+N > 0 && npal) { console.log('FAIL: DAC palette differs from the guest'); process.exitCode = 1; }
