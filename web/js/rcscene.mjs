// Frame-by-frame driver for the recompiled scenes (web/js/sqr.gen.mjs, made by re/x86js.py): runs the original code of one scene on the flat memory of x86rt.mjs,
// stopping at every page flip.  Time model = re/harness.py: 2 ticks of 60 Hz per flip (30 fps), the song position is a function of the tick (init.pos).
// Seeking = restore the nearest checkpoint (pages that differ from the state after the first flip, every CK flips) and replay.  One scene live at a time (memory is a singleton).
import * as R from './x86rt.mjs';
import {FN, setRegs, getRegs} from './sqr.gen.mjs';
export const CK = 30, PG = 4096, LIM = 0x6400000;   // checkpoint spacing, scan limit (the guest heap 0x4000000.. and the bump allocator 0x6000000..)
class Stop {}
// bytes of a rc*.bin.gz asset (made by re/mk_rcinit.py), gunzipped -> {entry, regs, esp, ranges, ticks, pos, stack(Uint8Array), data(Uint8Array)}
export function unpackInit(u8) {
  const h = new DataView(u8.buffer, u8.byteOffset).getUint32(0, true), H = JSON.parse(new TextDecoder().decode(u8.subarray(4, 4 + h))); let p = 4 + h;
  H.stack = u8.subarray(p, p += H.stack); H.data = u8.subarray(p); return H;
}
export class RcScene {
  // pak: {get(name)->Uint8Array} (web/js/pak.js pakOpen); init: unpackInit(...)
  file(n) { const b = n.split('\\').pop(); return RcScene.ext[b.toLowerCase()] || this.pak.get(b); }   // host files (not in the PAK), e.g. zebou.lzw: RcScene.ext['zebou.lzw'] = bytes
  constructor(init, pak) { this.i = init; this.pak = pak; this.reset(); }
  reset() {
    const i = this.i, m = R.m8; m.fill(0); let p = 0; for (const [a, b] of i.ranges) { m.set(i.data.subarray(p, p + b - a), a); p += b - a; }
    m.set(i.stack, i.esp); R.wr32(i.esp, 0x3ff50005); setRegs({eax: i.regs.eax | 0, ebx: i.regs.ebx | 0, ecx: i.regs.ecx | 0, edx: i.regs.edx | 0, esi: i.regs.esi | 0, edi: i.regs.edi | 0, ebp: i.regs.ebp | 0, esp: i.esp | 0});
    R.S.sp = 8; R.f.fill(0); R.MS.q = i.mal || null; R.MS.i = 0; this.files = []; this.dac = [0, 0]; this.pal = new Uint8Array(768); this.screen = new Uint8Array(320 * 480); this.rows = 200; this.n = -1; this.done = false; this.ck = new Map(); this.base = null; this.hooks();
  }
  hooks() {
    const H = R.H, i = this.i, T = i.ticks; R.S.active = this; H.TPF = 2;
    H.pos = () => { const t = R.rd32(0x10ce4c); let lo = 0, hi = T.length; while (lo < hi) { const m = (lo + hi) >> 1; if (T[m] <= t) lo = m + 1; else hi = m; } R.wr32(0x10ce28, i.pos[Math.max(0, lo - 1)]); };
    H.n_open = a => { let n = ''; for (let c; (c = R.rd8(a++)); ) n += String.fromCharCode(c); this.files.push({d: this.file(n), p: 0}); return this.files.length; };
    H.slurp = a => { let n = ''; for (let c; (c = R.rd8(a++)); ) n += String.fromCharCode(c); return this.file(n); };
    H.n_read = (h, d, n) => { const f = this.files[h - 1]; R.m8.set(f.d.subarray(f.p, f.p + n), d); f.p += n; };
    H.out = (p, v) => { const d = this.dac; if (p === 0x3c8) { d[0] = v; d[1] = 0; } else if (p === 0x3c9) { this.pal[d[0] * 3 + d[1]] = v; if (++d[1] === 3) { d[1] = 0; d[0] = (d[0] + 1) & 255; } } };
    H.present = (buf, rows) => { this.rows = rows; this.screen.set(R.m8.subarray(buf, buf + 320 * rows)); this.palShown = this.pal.slice(); };   // the frame as shown, with the DAC as of the flip
    H.yield = () => { throw new Stop(); };
  }
  // RGBA of the last flip (6-bit DAC -> 8 bit like the original's VGA: v<<2|v>>4)
  rgba(out) { const s = this.screen, P = this.palShown || this.pal, n = 320 * this.rows; for (let k = 0; k < n; k++) { const c = s[k] * 3, o = 4 * k; out[o] = P[c] << 2 | P[c] >> 4; out[o + 1] = P[c + 1] << 2 | P[c + 1] >> 4; out[o + 2] = P[c + 2] << 2 | P[c + 2] >> 4; out[o + 3] = 255; } return this.rows; }
  save() {
    const m = R.m8, m32 = new Uint32Array(R.buf, 0, LIM >> 2), pg = [], B = this.base;
    for (let a = 0; a < LIM; a += PG) { const b = B && B.get(a), e = (a + PG) >> 2; let d = false;
      if (b) { const b32 = new Uint32Array(b.buffer); for (let x = a >> 2, k = 0; x < e; x++, k++) if (m32[x] !== b32[k]) { d = true; break; } } else for (let x = a >> 2; x < e; x++) if (m32[x]) { d = true; break; }
      if (d) pg.push([a, m.slice(a, a + PG)]); }
    this.ck.set(this.n, {pg, regs: getRegs(), sp: R.S.sp, f: R.f.slice(), pal: this.pal.slice(), dac: this.dac.slice(), ms: R.MS.i, files: this.files.map(f => ({d: f.d, p: f.p})), done: this.done, rpc: R.S.rpc, rfn: R.S.rfn, screen: this.screen.slice(), rows: this.rows, palShown: this.palShown && this.palShown.slice()});
  }
  restore(n) {
    const c = this.ck.get(n); R.m8.fill(0); for (const [a, d] of this.base) R.m8.set(d, a); for (const [a, d] of c.pg) R.m8.set(d, a);
    setRegs(c.regs); R.S.sp = c.sp; R.f.set(c.f); this.pal = c.pal.slice(); this.dac = c.dac.slice(); this.files = c.files.map(f => ({d: f.d, p: f.p})); this.n = n; R.MS.i = c.ms; this.done = c.done; R.S.rpc = c.rpc; R.S.rfn = c.rfn; this.screen.set(c.screen); this.rows = c.rows; this.palShown = c.palShown && c.palShown.slice(); this.hooks();
  }
  // run to the next flip; returns false when the scene has returned
  step() {
    if (this.done) return false;
    try { if (this.n < 0) FN[this.i.entry](); else FN[R.S.rfn](R.S.rpc); this.done = true; return false; } catch (e) { if (!(e instanceof Stop)) throw e; }
    this.n++;
    if (this.n === 0) { this.base = new Map(); const m32 = new Uint32Array(R.buf, 0, LIM >> 2); for (let a = 0; a < LIM; a += PG) if (m32.subarray(a >> 2, (a + PG) >> 2).some(x => x)) this.base.set(a, R.m8.slice(a, a + PG)); this.save(); }   // base = state after the first flip
    else if (this.n % CK === 0) this.save();
    return true;
  }
  // picture after n+1 flips (n = 0..); the resume point (R.S.rfn/rpc) is stored with the checkpoint
  // budget (ms, optional): stop stepping after that long so the UI stays responsive; returns whether frame n was reached (the screen then shows frame this.n)
  frame(n, budget) {
    const t0 = budget && performance.now();
    if (R.S.active !== this) { this.hooks(); this.n = 1e9; }
    if (n < this.n || n > this.n + CK) { let b = -1; for (const k of this.ck.keys()) if (k <= n && k > b) b = k; if (n < this.n || b > this.n) { if (b < 0) { this.reset(); } else this.restore(b); } }
    while (this.n < n) { if (!this.step()) return false; if (budget && performance.now() - t0 > budget) break; } return true;
  }
}

RcScene.ext = {};
