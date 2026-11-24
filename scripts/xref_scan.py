#!/usr/bin/env python3
"""文字列への lui/addiu 参照を MIPS32LE コードから探す。

このファームウェアは文字列ポインタをデータテーブルに置かない。
コードが lui (上位16ビット) と addiu (下位16ビット) の組でアドレスを
組み立てるので、その組を追跡すると文字列の参照元命令が分かる。
ASCII 文字列の存在だけで判断せず、必ず参照元命令まで確認するための道具。

要 capstone (pip install capstone)。

使い方:
    python3 xref_scan.py firmware.bin "A:\\RO_RES\\USBUVC.BIN" [...]
"""
import sys

from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

BASE = 0x80000000
MAIN_OFF = 0x1714520
MAIN_END = 0x254AD20


def main() -> int:
    data = open(sys.argv[1], "rb").read()
    sl = data[MAIN_OFF:MAIN_END]
    targets = {}
    for s in sys.argv[2:]:
        raw = s.encode("latin1")
        fo = data.find(raw, MAIN_OFF)
        if fo < MAIN_OFF:
            print(f"skip (本体イメージ内に無い): {s!r}")
            continue
        targets[BASE + (fo - MAIN_OFF)] = s
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    lui_val = {}
    for ins in md.disasm(sl, BASE):
        if ins.mnemonic == "lui":
            p = ins.op_str.replace("$", "").split(",")
            try:
                lui_val[p[0].strip()] = (int(p[1].strip(), 0) & 0xFFFF) << 16
            except (ValueError, IndexError):
                pass
        elif ins.mnemonic in ("addiu", "ori"):
            p = ins.op_str.replace("$", "").split(",")
            if len(p) != 3:
                continue
            dst, src, imm = p[0].strip(), p[1].strip(), p[2].strip()
            try:
                immv = int(imm, 0)
            except ValueError:
                continue
            if src in lui_val:
                v = immv - 0x10000 if (ins.mnemonic == "addiu" and immv > 0x7FFF) else immv
                va = lui_val[src] + v
                if va in targets:
                    print(f"HIT {targets[va]} at {ins.address:#x}: "
                          f"{ins.mnemonic} {ins.op_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
