#!/usr/bin/env python3
"""firmware.bin 内の内蔵 FAT イメージ (A: RO_RES / B: USER_RES) を読む。

ディレクトリエントリと FAT チェーンをたどってファイル一覧を作る。
--extract を付けると、指定ファイルをそのまま取り出す。

使い方:
    python3 fat_list.py firmware.bin            一覧を表示
    python3 fat_list.py firmware.bin --extract RO_RES/USBSTR.TXT out.txt
"""
import struct
import sys

FAT_A_OFF = 0x94520     # FAT16, ドライブ A: (RO_RES)
FAT_B_OFF = 0x1694520   # FAT12, ドライブ B: (USER_RES)


class FatImage:
    def __init__(self, data: bytes, bs_off: int):
        self.data = data
        self.bs = bs_off
        b = data[bs_off:bs_off + 512]
        self.bps = struct.unpack_from("<H", b, 11)[0]
        self.spc = b[13]
        self.rsvd = struct.unpack_from("<H", b, 14)[0]
        self.nfats = b[16]
        self.rootent = struct.unpack_from("<H", b, 17)[0]
        tot16 = struct.unpack_from("<H", b, 19)[0]
        self.fatsz = struct.unpack_from("<H", b, 22)[0]
        tot32 = struct.unpack_from("<I", b, 32)[0]
        self.tot = tot16 or tot32
        self.fat_off = bs_off + self.rsvd * self.bps
        self.root_off = bs_off + (self.rsvd + self.nfats * self.fatsz) * self.bps
        self.data_off = self.root_off + self.rootent * 32
        self.is_fat12 = self.fatsz <= 10

    def chain(self, start: int):
        out, c = [], start
        while c >= 2 and len(out) < 200000:
            out.append(c)
            if self.is_fat12:
                off = self.fat_off + c * 3 // 2
                v = struct.unpack_from("<H", self.data, off)[0]
                v = (v >> 4) if c & 1 else (v & 0xFFF)
                if v >= 0xFF8:
                    break
            else:
                v = struct.unpack_from("<H", self.data, self.fat_off + c * 2)[0]
                if v >= 0xFFF8:
                    break
            c = v
        return out

    def read_clusters(self, start: int) -> bytes:
        size = self.spc * self.bps
        return b"".join(
            self.data[self.data_off + (c - 2) * size:
                      self.data_off + (c - 2) * size + size]
            for c in self.chain(start))

    def read_file(self, start: int, size: int) -> bytes:
        return self.read_clusters(start)[:size]

    def list_dir(self, dir_data: bytes, path: str, out: list):
        lfn = ""
        for i in range(0, len(dir_data), 32):
            e = dir_data[i:i + 32]
            if len(e) < 32 or e[0] == 0:
                break
            if e[0] == 0xE5:
                lfn = ""
                continue
            attr = e[11]
            if attr == 0x0F:  # LFN エントリ
                chars = e[1:11] + e[14:26] + e[28:32]
                lfn = chars.decode("utf-16-le", errors="ignore").rstrip("\x00\uffff") + lfn
                continue
            raw = e[0:8].decode("ascii", errors="replace").strip()
            ext = e[8:11].decode("ascii", errors="replace").strip()
            name = lfn or (raw + ("." + ext if ext else ""))
            lfn = ""
            if name in (".", ".."):
                continue
            clus = struct.unpack_from("<H", e, 26)[0]
            size = struct.unpack_from("<I", e, 28)[0]
            full = path + name
            out.append((full, attr, clus, size))
            if attr & 0x10 and clus >= 2:
                self.list_dir(self.read_clusters(clus), full + "/", out)

    def root_list(self):
        out = []
        root = self.data[self.root_off:self.root_off + self.rootent * 32]
        self.list_dir(root, "", out)
        return out


def main() -> int:
    args = sys.argv[1:]
    data = open(args[0], "rb").read()
    images = [("A_RO_RES_FAT16", FatImage(data, FAT_A_OFF)),
              ("B_USER_RES_FAT12", FatImage(data, FAT_B_OFF))]
    if "--extract" in args:
        i = args.index("--extract")
        want, outpath = args[i + 1], args[i + 2]
        for _, img in images:
            for name, attr, clus, size in img.root_list():
                if name == want and not (attr & 0x10):
                    open(outpath, "wb").write(img.read_file(clus, size))
                    print(f"extracted {want} ({size} bytes) -> {outpath}")
                    return 0
        print(f"not found: {want}")
        return 1
    for label, img in images:
        files = img.root_list()
        print(f"=== {label} ({len(files)} entries) ===")
        for name, attr, clus, size in files:
            kind = "DIR " if attr & 0x10 else "FILE"
            print(f"{kind} {size:>9} clus={clus:<6} {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
