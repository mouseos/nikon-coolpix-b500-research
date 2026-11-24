#!/usr/bin/env python3
"""RO_RES/USBUVC.BIN の USB ディスクリプタ列を順に読む。

USBUVC.BIN は UVC (USB Video Class) のコンフィギュレーション
ディスクリプタ一式を収めたリソースファイルである。
先頭から bLength / bDescriptorType をたどって分解する。

使い方:
    python3 parse_uvc.py firmware.bin
"""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fat_list import FatImage, FAT_A_OFF  # noqa: E402

NAMES = {2: "CONFIGURATION", 4: "INTERFACE", 5: "ENDPOINT",
         0x0B: "INTERFACE_ASSOCIATION", 0x24: "CLASS_SPECIFIC",
         0x25: "CLASS_SPECIFIC_EP"}


def main() -> int:
    data = open(sys.argv[1], "rb").read()
    img = FatImage(data, FAT_A_OFF)
    blob = None
    for name, attr, clus, size in img.root_list():
        if name == "RO_RES/USBUVC.BIN":
            blob = img.read_file(clus, size)
            print(f"USBUVC.BIN size={size}")
            break
    if blob is None:
        print("USBUVC.BIN が見つからない")
        return 1
    i = 0
    while i < len(blob):
        ln = blob[i]
        if ln == 0:
            print(f"{i:#06x} len=0 stop")
            break
        t = blob[i + 1] if i + 1 < len(blob) else 0
        extra = ""
        if t == 2:
            extra = (f" wTotalLength={blob[i+2] | (blob[i+3] << 8)}"
                     f" bNumInterfaces={blob[i+4]}")
        elif t == 4:
            extra = (f" if={blob[i+2]} alt={blob[i+3]} eps={blob[i+4]}"
                     f" class={blob[i+5]:#x} sub={blob[i+6]:#x} proto={blob[i+7]:#x}")
        elif t == 5:
            extra = (f" ep={blob[i+2]:#x} attr={blob[i+3]}"
                     f" maxpkt={blob[i+4] | (blob[i+5] << 8)} interval={blob[i+6]}")
        elif t in (0x24, 0x25):
            extra = f" subtype={blob[i+2]:#x}"
            guid = blob[i + 4:i + 20]
            if guid[0:4].isalpha() and t == 0x24 and blob[i + 2] in (4, 8):
                extra += f" formatGUID={guid[:4].decode(errors='replace')}"
        print(f"{i:#06x} len={ln:<3} type={t:#04x} {NAMES.get(t, '')}{extra}")
        i += ln
    print(f"end at {i:#x} of {len(blob):#x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
