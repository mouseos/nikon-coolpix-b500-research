#!/usr/bin/env python3
"""SUNP BURN FILE (Sunplus / iCatch の書き込み用ファームウェア形式) の構造を読む。

先頭ヘッダのオフセット表、HDR1 / HDR2 / HDR3 の位置、内蔵 FAT イメージ、
本体コードイメージの範囲を、実バイトから割り出す。
推測で補わず、境界は「次の領域の開始と一致するか」で検証する。

使い方:
    python3 parse_burn.py firmware.bin
"""
import struct
import sys

MAGIC = b"SUNP BURN FILE\x00\x00"


def parse_fat_header(data: bytes, off: int) -> dict:
    b = data[off:off + 512]
    bps = struct.unpack_from("<H", b, 11)[0]
    spc = b[13]
    rsvd = struct.unpack_from("<H", b, 14)[0]
    nfats = b[16]
    rootent = struct.unpack_from("<H", b, 17)[0]
    tot16 = struct.unpack_from("<H", b, 19)[0]
    fatsz = struct.unpack_from("<H", b, 22)[0]
    tot32 = struct.unpack_from("<I", b, 32)[0]
    tot = tot16 or tot32
    return {
        "offset": off, "bytes_per_sector": bps, "sectors_per_cluster": spc,
        "reserved_sectors": rsvd, "fats": nfats, "root_entries": rootent,
        "fat_sectors": fatsz, "total_sectors": tot,
        "size": tot * bps, "end": off + tot * bps,
        "fs_type": b[54:62].decode("ascii", errors="replace").strip()
        if b[54:62].strip(b"\x00 ") else b[82:90].decode("ascii", errors="replace").strip(),
    }


def main() -> int:
    data = open(sys.argv[1], "rb").read()
    print(f"file size: {len(data)} (0x{len(data):x})")
    assert data[:16] == MAGIC, "SUNP BURN FILE ではない"
    print("magic: SUNP BURN FILE")

    fields = [struct.unpack_from("<I", data, 0x10 + 4 * i)[0] for i in range(6)]
    names = ["total_size", "hdr1_offset", "hdr2_offset", "main_image_offset",
             "(zero)", "hdr3_offset"]
    for n, v in zip(names, fields):
        print(f"header[0x{0x10 + 4 * names.index(n):02x}] {n}: 0x{v:08x} ({v})")
    assert fields[0] == len(data), "先頭フィールドはファイル全体長と一致するはず"

    hdr1, hdr2, main_off, hdr3 = fields[1], fields[2], fields[3], fields[5]
    print(f"HDR1 @ 0x{hdr1:x}: {data[hdr1:hdr1 + 16]!r}")
    print(f"HDR2 @ 0x{hdr2:x}: {data[hdr2:hdr2 + 16]!r}")
    print(f"HDR3 @ 0x{hdr3:x}: {data[hdr3:hdr3 + 16]!r}")
    print(f"bootloader image: 0x200 .. 0x{hdr1:x} (size 0x{hdr1 - 0x200:x})")

    # HDR2 の直後 (0x120 バイト後) から FAT16 イメージ (ドライブ A: RO_RES)
    fat_a_off = hdr2 + 0x120
    fat_a = parse_fat_header(data, fat_a_off)
    print(f"FAT A (RO_RES): {fat_a}")
    assert fat_a["end"] == fat_a_off + fat_a["size"]

    # FAT A の終端から FAT12 イメージ (ドライブ B: USER_RES)
    fat_b = parse_fat_header(data, fat_a["end"])
    print(f"FAT B (USER_RES): {fat_b}")
    assert fat_b["end"] == main_off, "FAT B の終端は本体イメージ開始と一致するはず"

    print(f"main image: 0x{main_off:x} .. 0x{hdr3:x} (size 0x{hdr3 - main_off:x})")

    # HDR3: バックアップ対象リソースファイルの一覧 (0x70 バイト/件)
    count = data[hdr3 + 16]
    print(f"HDR3 entries: {count}")
    pos = hdr3 + 0x20
    for i in range(count):
        entry = data[pos + i * 0x70: pos + (i + 1) * 0x70]
        print(f"  [{i}] {entry.split(bytes(1))[0].decode('ascii')}")
    tail = pos + count * 0x70
    print(f"tail (DRAM param): 0x{tail:x} .. 0x{len(data):x}, starts {data[tail:tail + 8]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
