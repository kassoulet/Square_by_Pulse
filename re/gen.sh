#!/bin/sh
# regenerate web/js/sqr.gen.mjs from the objdump listings (RC=dir with code.dis and g58.dis); usage: re/gen.sh RC_DIR [extra entry points...]
cd "$(dirname "$0")/.." || exit 1; RC=$1; shift
FLAT=$RC/flat.bin NATIVES="$(cat re/natives.env)" PATCHES="$(cat re/patches.env)" NOROUND=2d9c6 PRELUDE=re/pre.js FP24=1 RANGE=1c000-3a000,58000-58400,3b6c5-3b6ef,3bd4c-3bd53 \
 python3 -I re/x86js.py web/js/sqr.gen.mjs "$RC/code.dis" "$RC/code.fix" "$RC/g58.dis" -- 338a5 29a81 260d5 29a3b 366f2 2150c 21520 260a0 2a790 305f7 1faa1 2edbd 2c9b1 1eb7f 31f0a 28f64 243a9 3c06c 1d92e 1d97a "$@" | head -3
