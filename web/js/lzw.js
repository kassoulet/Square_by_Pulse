// lzw.js - port of the PAK / .LZW bit-stream decoder of SQUARE.EXE (0x1d92e init, 0x2c5fc decode loop, 0x2c6e2 bit reader).
// GIF-like LZW, MSB-first bits: width starts at 9; code 0x100 = end, 0x101 = width+1 (explicit, no implicit growth), 0x102 = reset (next=0x103, width=9,
// then a literal first code); first code of the stream is a plain 9-bit literal; entries are {char, prefix}; KwKwK handled as in GIF.
export function lzwDecode(src, outLen = Infinity) {
  const ch = new Uint8Array(0x10000), pre = new Int32Array(0x10000), out = [];
  let pos = 0, bit = 0, next = 0x103, width = 9;
  const code = () => { let v = 0; for (let i = 0; i < width; i++) { v = (v << 1) | ((src[pos] >> (7 - bit)) & 1); if (++bit == 8) { bit = 0; pos++; } } return v; };
  const stack = [];
  let prev = code(), last = prev & 255; out.push(last);
  while (out.length < outLen && pos < src.length) {
    const c = code();
    if (c == 0x100) break;
    if (c == 0x101) { width++; continue; }
    if (c == 0x102) { next = 0x103; width = 9; prev = code(); last = prev & 255; out.push(last); continue; }
    stack.length = 0; let e = c;
    if (c >= next) { stack.push(last); e = prev; }
    while (e > 255) { stack.push(ch[e]); e = pre[e]; }
    stack.push(e); last = e;
    for (let i = stack.length - 1; i >= 0; i--) out.push(stack[i]);
    ch[next] = e; pre[next] = prev; next++; prev = c;
  }
  return Uint8Array.from(out.length > outLen ? out.slice(0, outLen) : out);
}
