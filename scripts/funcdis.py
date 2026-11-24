#!/usr/bin/env python3
"""本体イメージの指定範囲を逆アセンブルし、文字列参照に注釈を付ける。

lui/addiu で組み立てたアドレスが文字列を指す場合、その文字列を注釈に表示する。
命令を読んで処理の流れを確かめるための道具。

要 capstone (pip install capstone)。

使い方:
    python3 funcdis.py firmware.bin 0x8039b780 0x8039b890
"""
import sys

from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

BASE = 0x80000000
MAIN_OFF = 0x1714520
MAIN_END = 0x254AD20


def main() -> int:
    data = open(sys.argv[1], "rb").read()
    sl = data[MAIN_OFF:MAIN_END]
    start, end = int(sys.argv[2], 0), int(sys.argv[3], 0)
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    lui_val = {}
    for ins in md.disasm(sl[start - BASE:end - BASE], start):
        ann = ""
        if ins.mnemonic == "lui":
            p = ins.op_str.replace("$", "").split(",")
            try:
                lui_val[p[0].strip()] = (int(p[1].strip(), 0) & 0xFFFF) << 16
            except (ValueError, IndexError):
                pass
        elif ins.mnemonic in ("addiu", "ori"):
            p = ins.op_str.replace("$", "").split(",")
            if len(p) == 3:
                dst, src, imm = p[0].strip(), p[1].strip(), p[2].strip()
                try:
                    immv = int(imm, 0)
                except ValueError:
                    immv = None
                if immv is not None and src in lui_val:
                    v = immv - 0x10000 if (ins.mnemonic == "addiu" and immv > 0x7FFF) else immv
                    va = lui_val[src] + v
                    if BASE <= va < BASE + len(sl):
                        chunk = sl[va - BASE:va - BASE + 48]
                        s = chunk.split(b"\x00")[0]
                        if len(s) >= 3 and all(32 <= c < 127 for c in s):
                            ann = f'  ; -> "{s.decode()}"'
                        else:
                            ann = f"  ; -> {va:#x}"
        print(f"{ins.address:#010x}  {ins.mnemonic:<8} {ins.op_str}{ann}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
