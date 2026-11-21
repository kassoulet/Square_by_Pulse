// SQUARE.PAK: header u32 at 8 = directory offset; directory = 24-byte entries {name[12], off, csize, usize}; each entry is an lzw.js stream.
import { lzwDecode } from './lzw.js';
export function pakOpen(u8) {
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength), dir = dv.getUint32(8, true), files = {};
  for (let o = dir; o + 24 <= u8.length; o += 24) {
    const name = String.fromCharCode(...u8.subarray(o, o + 12)).split('\0')[0].toLowerCase(); if (!name) break;
    files[name] = [dv.getUint32(o + 12, true), dv.getUint32(o + 20, true)];
  }
  return { names: Object.keys(files), get: name => { const [off, usize] = files[name.toLowerCase()]; return lzwDecode(u8.subarray(off), usize); } };
}
