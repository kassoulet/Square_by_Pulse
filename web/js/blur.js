// Radial zoom blur of Square: 0x2a8e8 (tables) + 0x58000 (asm warp), bit-exact against the guest.
// buf = Uint8Array, 320 wide, 200 rows, modified in place in the guest's order (left/right halves, rows up from cy then down).
const f32 = Math.fround;
export function blur(buf, cx, cy, a3, a4) {
  cx = f32(cx); cy = f32(cy); a3 = f32(a3); a4 = f32(a4);
  const tx = new Int32Array(320), ty = new Int32Array(200), T = new Uint8Array(256);
  for (let x = 0; x < 320; x++) tx[x] = Math.trunc((x - cx) * 64 * a4);
  for (let y = 0; y < 200; y++) ty[y] = Math.trunc((y - cy) * 64 * a4);
  const rne = v => { const r = Math.round(v); return Math.abs(v % 1) === 0.5 && (r & 1) ? r - 1 : r; };
  let acc = 0; for (let i = 0; i < 256; i++) { T[i] = rne(acc) & 255; acc += a3; }   // fist: round to nearest even, low byte
  const W = (f, d) => (Math.trunc(d * f / 64)) & 255;                                 // weight table 0x121924
  const px = Math.min(319, Math.max(0, Math.trunc(cx))), py = Math.min(199, Math.max(0, Math.trunc(cy)));
  const at = i => buf[i] ?? 0;
  const one = (x, y) => {
    const fy = ty[y] & 63, fx = tx[x] & 63, o = (ty[y] >> 6) * 320 + y * 320 + x + (tx[x] >> 6);
    const a = at(o), b = at(o + 320), c = at(o + 1), d = at(o + 321);
    const v1 = (a + W(fy, b - a)) & 255, v2 = (c + W(fy, d - c)) & 255;
    const v = (v1 + W(fx, v2 - v1)) & 255, i = y * 320 + x, s = buf[i] + T[v];
    buf[i] = s > 255 ? 255 : s;
  };
  for (const dir of [-1, 1]) {
    const y0 = dir < 0 ? py : py + 1;
    for (let y = y0; y >= 0 && y < 200; y += dir) for (let x = px - 1; x >= 0; x--) one(x, y);
    // guest order: left half of all rows first, then right half of all rows
    for (let y = y0; y >= 0 && y < 200; y += dir) for (let x = px; x < 320; x++) one(x, y);
  }
}

// Blur arguments of the people scene (0x39372..0x393f2): two 3-term sine "noise" curves (guest 0x1e27a) steer the zoom centre.
// NTAB is the guest's byte table 0x110be4 (rand()&0x7f filled at start-up; the rand seed is NOT reproduced, this is the table of one captured run).
const NTAB = [39,32,48,13,90,47,112,71,123,107,57,27,16,23,28,36,114,90,122,117,116,42,96,94,53,31,18,22,34,59,70,92,38,33,13,6,21,64,114,1,55,97,65,62,14,57,4,17,76,86,46,4,112,12,118,16,30,75,98,80,32,102,127,31,25,71,82,38,103,26,110,94,58,99,66,123,82,4,16,77,116,52,30,17,14,102,11,44,10,34,94,92,79,73,64,87,116,78,101,92,40,92,44,44,61,111,98,1,113,87,70,102,96,52,46,11,38,88,98,0,48,34,44,104,68,67,13,20,47,117,44,21,44,36,112,58,115,2,72,126,2,15,45,106,7,18,69,95,12,126,68,91,69,72,115,34,21,49,110,98];
// The guest runs the x87 with 24-bit precision control: every operation rounds to float32 (hence f32 around each step).
function noise(e, t) {
  let s10 = f32(0.005), s8 = f32(0.001), acc = 0;
  for (let i = 0; i < 3; i++) {
    const v = f32(f32(f32((NTAB[e] + 0x40) * s8) * t) + (NTAB[e + 1] - 0x40));
    acc = f32(acc + f32(Math.sin(v) * f32((NTAB[e + 2] + 0x40) * s10)));
    e += 3; s10 = f32(s10 * 0.5); s8 = f32(s8 * 2);
  }
  return acc;
}
export function blurArgs(p, S) {
  const t = f32(p * 0.5), v = f32(f32(S * 0.42) + 0.5);
  return [f32(f32(noise(0x86, t) * 50) + 160), f32(f32(noise(0x48, t) * 50) + 100), v > 0.93 ? f32(0.93) : f32(v), f32(-0.028)];
}
