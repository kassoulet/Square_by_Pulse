// people.js - the 'people' scene of SQUARE (scene function 0x390ab, last scene, music position >= 0xc20 = order 48 row 32 = t 218.001 s).
// blend(): the two 192x144 DCT frames A,B (from dct.js) cross-faded as in the original loop 0x3932b..0x3935c; up2x(): the original 0x3900b (160x120 window at (8,9) -> 320x240).
// Exact (golden-diffed against the original, see tools/cmp_people_blend.mjs): blend() given the guest's p, up2x().  NOT ported: the radial zoom blur 0x2a8e8 (+ generated code at 0x58000), the logo overlay.
const f32 = Math.fround;
export function tab(i) { return i < 128 ? i : 127; }   // add table at 0x1062b8 (clamps to 127), see NOTES
export function weights(p) {   // p = frame position (float32).  returns [k1,k2] LUT rows: LUT[k][a] = (a*k)>>7
  const i = Math.trunc(p), fr = f32(p - i), w1 = f32(1 - fr);
  const amp = f32((Math.sin(f32(p * 0.2)) * 0.3 + 0.69) * 128);
  return [Math.trunc(f32(amp * w1)), Math.trunc(f32(amp * fr))];
}
export function blend(A, B, p) {
  const [k1, k2] = weights(p), out = new Uint8Array(27648);
  for (let i = 0; i < 27648; i++) out[i] = tab(((A[i] * k1) >> 7) + ((B[i] * k2) >> 7));
  return out;
}
export function up2x(s) {   // s = 192x144 buffer -> 320x240 (stride 320)
  const d = new Uint8Array(320 * 240), at = (y, x) => s[(y + 9) * 192 + x + 8];
  for (let y = 0; y < 120; y++) for (let x = 0; x < 160; x++) {
    const c = at(y, x), r = at(y, x + 1), b = at(y + 1, x), o = 2 * y * 320 + 2 * x;
    d[o] = c >> 1; d[o + 1] = (c + r) >> 2; d[o + 320] = (b + c) >> 3; d[o + 321] = (r + 2 * c + b) >> 4;
  }
  return d;
}
