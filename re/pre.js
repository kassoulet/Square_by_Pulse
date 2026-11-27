// natives of the engine layer (guest 0x1c000 region) in terms of the recompiled code; appended to the generated module by x86js.py (PRELUDE)
const callf = a => { esp = (esp - 4) | 0; FN[a](); };
const cbs = type => { for (let i = 0; i < 8; i++) { const p = R.rd32(0x111bfc + 4 * i); if (p && R.rd32(0x111c3c + 4 * i) === type) callf(p); } };
// 0x1ca79(0) = 0x1cab2: song position (the driver supplies it), then the type-0 callbacks once per elapsed 60 Hz tick; returns the number of ticks
function POLL() { R.H.pos(); const t = R.rd32(0x10ce4c); let dt = t - R.rd32(0x10ce50); R.wr32(0x10ce50, t); const n = dt; for (; dt > 0; dt--) cbs(0); return n; }
// present: the harness grabs the frame, then its trampoline runs the MIDAS 60 Hz callback 0x1c0a3 (= 0x1ca79(1) type-1 callbacks, tick++) TPF times
function PRESENT(buf, rows) { R.H.present(buf, rows); for (let i = 0; i < R.H.TPF; i++) { cbs(1); R.wr32(0x10ce4c, R.rd32(0x10ce4c) + 1); } PRESENT_END(); }
R.H.ind = a => { if (!FN[a]) throw new Error('indirect call to unrecompiled 0x' + (a >>> 0).toString(16)); return FN[a](); };   // indirect call: the generated code has already pushed the return slot
// after the ISR ticks the driver may unwind to the caller (frame boundary); the resume point is R.S.rpc in f_R.S.rfn (set before the native call)
const PRESENT_END = () => R.H.yield && R.H.yield();
// 0x31c33 blend (pusha/popa function, registers untouched): dst[i] = (T1[src[i]] + T2[dst[i]] & 255) ^ 0x80 over 0x4b000 bytes, T1/T2 = 256-byte rows of the 64 KB LUT [0x10ce80] selected by cl / by the low byte of ebx
function BLEND(d, s, a, c) { const m = R.m8, L = R.rd32(0x10ce80) & 0xffff0000, t1 = L | (c & 255) << 8, t2 = L | (a & 255) << 8; for (let i = 0; i < 0x4b000; i++) m[d + i] = (m[t1 + m[s + i]] + m[t2 + m[d + i]] & 255) ^ 128; }
// 0x3c104 = Watcom C++ array constructor helper: descriptor d: ctor address at +1, element size at +13; calls ctor(eax=element, edx=size) n times (the EH bookkeeping is dropped)
function ARR(p, n, d) { const c = R.rd32(d + 1), z = R.rd32(d + 13), p0 = p; if (!p) return; for (; n > 0; n--) { eax = p; edx = z; callf(c); p += z; } eax = p0; }   // the helper returns the array start (the caller does lea ebx,[eax-0x28])
// 0x2c25b (stdcall ret 0x14, pusha/popa): scaled sprite blit.  args dst,sx,sy,tex,bright (stack); x0=eax, x1=ebx, y0=edx, y1=ecx on entry.  Builds the 256-entry ramp T at 0x106d30, then per destination pixel
// dst = L[(T[tex[..]] + dst) & 255] with L = 256-byte table at 0x1062b8; 16.16 steps along x (column step table at 0x106530) and y.  The scratch globals 0x106508-0x10652c are written as the original does.
function SPR(eax_, ebx_, ecx_, edx_, sp) {
  const m = R.m8, A0 = R.rd32(sp), A1 = R.rd32(sp + 4), A2 = R.rd32(sp + 8), A3 = R.rd32(sp + 12), A4 = R.rd32(sp + 16);
  R.wr32(0x10652c, A0); R.wr32(0x106520, A1); R.wr32(0x106524, A2); R.wr32(0x106528, A3);
  let a = 0; for (let i = 0; i < 256; i++) { m[0x106d30 + i] = (a >>> 8) & 255; a = (a + A4) >>> 0; if (a >= 0x8000) a = 0x7fff; }
  let x0 = eax_, x1 = ebx_, y0 = edx_, y1 = ecx_;   // the asm's xchg ebx,edx leaves ebx=y0, edx=x1
  if (x0 >= 0x140 || x1 <= 0 || y0 >= 0xc8 || y1 <= 0) return;
  let w = (x1 - x0) | 0; if (w <= 0) return; let h = (y1 - y0) | 0; if (h <= 0) return;
  const dx = Math.floor((Math.imul(0x10000, A1) >>> 0) / (w >>> 0)), dy = Math.floor((Math.imul(0x10000, A2) >>> 0) / (h >>> 0));
  R.wr32(0x10650c, dx); R.wr32(0x106508, dy);
  let xs = 0, ys = 0; let X1 = (x0 + w) | 0, Y1 = (y0 + h) | 0;
  if (x0 < 0) { xs = (-Math.imul(x0, dx)) | 0; x0 = 0; }
  if (X1 > 0x140) X1 = 0x140;
  if (y0 < 0) { ys = (-Math.imul(y0, dy)) | 0; y0 = 0; }
  if (Y1 > 0xc8) Y1 = 0xc8;
  R.wr32(0x106510, xs); R.wr32(0x106514, ys);
  w = (X1 - x0) | 0; if (w <= 0) return; h = (Y1 - y0) | 0; if (h <= 0) return;
  R.wr32(0x106518, w); R.wr32(0x10651c, h);
  let s = (x0 + Math.imul(y0, 0x140) + A0) | 0, e = xs;
  const tb = 0x106530; for (let i = 0; i < w; i++) { R.wr32(tb + 4 * i, e >> 16); e = ((e & 0xffff) + dx) | 0; }
  let yy = ys;
  for (let r = 0; r < h; r++) {
    let b = Math.imul(yy >>> 16, A1) + A3 | 0; yy = (yy + dy) | 0; let p = s;
    for (let i = 0; i < w; i++, p++) { b = (b + R.rd32(tb + 4 * i)) | 0; const d = (m[0x106d30 + m[b]] + m[p]) & 255; m[p] = m[0x1062b8 + d]; }
    s += 0x140;
  }
  R.wr32(0x106514, yy); R.wr32(0x10651c, 0);
}
