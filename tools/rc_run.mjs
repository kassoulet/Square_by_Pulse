// Recompiler check: run a statically recompiled scene (ENTRY=hex, default 338a5; web/js/sqr.gen.mjs, made by re/x86js.py) on the snapshot memory and diff every presented frame
// and the DAC palette against the guest capture of re/rc_gold.py.   node tools/rc_run.mjs FLAT.bin GOLDDIR [maxFrames]
import fs from 'fs'; import * as R from '../web/js/x86rt.mjs'; import {FN, setRegs} from '../web/js/sqr.gen.mjs'; import {pakOpen} from '../web/js/pak.js';
const [flat, gd, maxF = 1e9] = process.argv.slice(2), J = n => JSON.parse(fs.readFileSync(gd + '/' + n));
R.m8.set(fs.readFileSync(flat));
const meta = J('meta.json'), inputs = J('inputs.json'), dacg = J('dac.json'), pak = pakOpen(new Uint8Array(fs.readFileSync(new URL('../SQUARE.PAK', import.meta.url))));
R.m8.set(fs.readFileSync(gd + '/stack.bin'), meta.ESP); R.wr32(meta.ESP, 0x3ff50005);
setRegs({eax: meta.EAX | 0, ebx: meta.EBX | 0, ecx: meta.ECX | 0, edx: meta.EDX | 0, esi: meta.ESI | 0, edi: meta.EDI | 0, ebp: meta.EBP | 0, esp: meta.ESP | 0});
const dacByTag = {}; for (const [fr, p, v] of J('dac.json')) if (p === 969) (dacByTag[fr] ||= []).push(v);
let poll = 0, frame = 0, bad = 0, badPal = 0, dacIdx = 0, files = [], pal = new Uint8Array(768), dac = [0, 0];
const dec = new TextDecoder();
R.H.TPF = 2; const posAt = {}; for (const [, pos, tick] of inputs) posAt[tick] = pos;   // the guest's song position is a pure function of the tick (harness: xm_times lookup)
R.H.pos = () => { poll++; if (process.env.TR && posAt[R.rd32(0x10ce4c)] === undefined) console.log("MISS tick", R.rd32(0x10ce4c), "frame", frame); if (process.env.TR) console.log("poll", poll, "tick", R.rd32(0x10ce4c), "pos", posAt[R.rd32(0x10ce4c)], "gold", JSON.stringify(inputs[poll-1]), "fr", frame); R.wr32(0x10ce28, posAt[R.rd32(0x10ce4c)] ?? 0); };   // dt / callbacks / tick now come from the recompiled engine layer (pre338.js)
R.H.n_open = a => { let n = ''; for (let c; (c = R.rd8(a++)); ) n += String.fromCharCode(c); files.push({d: pak.get(n.split('\\').pop()), p: 0}); return files.length; };
R.H.n_read = (h, d, n) => { const f = files[h - 1]; R.m8.set(f.d.subarray(f.p, f.p + n), d); f.p += n; };
let nw = 0, wl = [], nwSave = 0; R.H.out = (p, v) => { if (p === 0x3c9) { nw++; wl.push(v); } if (p === 0x3c8) dac = [v, 0]; else if (p === 0x3c9) { pal[dac[0] * 3 + dac[1]] = v; if (++dac[1] === 3) { dac[1] = 0; dac[0] = (dac[0] + 1) & 255; } } };
class Stop {}
const V2 = []; if (process.env.VT2) globalThis.VT2 = esp => { if (frame >= 79) V2.push([frame, ...[0x62c, 0x60c, 0x610, 0x614, 0x618].map(o => R.rd32(esp + o) >>> 0)]); };
const SLL = []; if (process.env.SL) R.H.tlog = (k, x, r) => { if (frame >= 79) SLL.push([frame, k, x, r]); };
const VTL = []; if (process.env.VT) globalThis.VT = (ecx, esp) => { if (frame >= 79) VTL.push([frame, ecx, [0x8c, 0x90, 0x94, 0xf4].map(o => R.rd32(esp + o) >>> 0)]); };
let tcalc = 0, tlast = performance.now();   // time spent in the scene code (excluding the comparison below)
R.H.present = (buf) => {
  tcalc += performance.now() - tlast; if (process.env.MEMDUMP && frame === +process.env.MEMDUMP) fs.writeFileSync(process.env.MEMF, R.m8.subarray(0x100000, 0x400000));
  const g = fs.readFileSync(gd + '/f' + String(2 * frame).padStart(4, '0')   // the harness hook fires twice per present (ISR trampoline re-enters 0x1d0cf), so golden frame = 2*loop
  + '' + '.bin'); let d = 0, pdif = 0;
  if (process.env.DUMP && frame === +process.env.DUMP) fs.writeFileSync(process.env.DUMPF, R.m8.subarray(buf, buf + 64000));   // debug: dump my frame buffer
  for (let i = 0; i < g.length; i++) d += R.m8[buf + i] !== g[i];
  // palette: the real present 0x1d0cf (not recompiled) programs the DAC from the 768-byte table at 0x121390; the guest's DAC writes of this frame are the reference
  // palette: the ISR callback 0x260d5 (recompiled) writes the DAC per tick; compare the table the DAC holds when the frame is grabbed against the guest's last 768 writes up to this present
  // my writes since the previous present vs the guest's writes of tag 2f-1 (the two ISR ticks after the previous frame): same count and same values
  const G = frame ? (dacByTag[2 * frame - 1] || []) : wl; pdif = frame ? Math.max(Math.abs(G.length - wl.length), G.reduce((x, v, i) => x + (v !== wl[i]), 0)) : 0; if (pdif && process.env.PD) { const ii = G.findIndex((v, i) => v !== wl[i]); console.log('DAC first diff', ii, 'gold', G.slice(ii, ii + 9).join(), 'mine', wl.slice(ii, ii + 9).join()); } nwSave = wl.length; wl = []; nw = 0;
  if (pdif) { badPal++; if (badPal < 4 || process.env.V) console.log('frame', frame, 'DAC writes differ: gold', G.length, 'mine', nwSave); }
  if (d && process.env.V) { const L = []; for (let i = 0; i < g.length; i++) if (R.m8[buf + i] !== g[i]) L.push([i % 320, i / 320 | 0, R.m8[buf + i], g[i]].join(':')); console.log(L.join(' ')); }
  if (d) { bad++; if (bad < 4 || process.env.ALL) console.log('frame', frame, 'differing pixels', d); }
  if (process.env.STOPBAD && (d > 40 || bad > 3)) throw new Stop();   // ablation helper
  frame++; tlast = performance.now(); if (frame >= maxF) throw new Stop();
};
let dacRef = null;
try { FN[parseInt(process.env.ENTRY || '338a5', 16)](); } catch (e) { if (!(e instanceof Stop)) { console.log('error after', frame, 'frames,', bad, 'differing, polls', poll); throw e; } }
if (process.env.VT) fs.writeFileSync(process.env.VT, JSON.stringify(VTL));
if (process.env.SL) fs.writeFileSync(process.env.SL, JSON.stringify(SLL));
if (process.env.VT2) fs.writeFileSync(process.env.VT2, JSON.stringify(V2));
console.log((tcalc / Math.max(frame, 1)).toFixed(1), 'ms/flip in the scene code;', frame, 'frames presented,', bad, 'pixel-differing frames,', badPal, 'palette-differing frames; polls used', poll, '/', inputs.length);
if (badPal > +(process.env.KNOWNPAL || 0)) { console.log('FAIL: DAC writes differ from the guest (more than KNOWNPAL=' + (process.env.KNOWNPAL || 0) + ' frames)'); process.exitCode = 1; }
