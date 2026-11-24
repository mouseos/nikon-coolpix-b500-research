#!/usr/bin/env python3
"""Nikon COOLPIX B500 アップデーター (.exe) から firmware.bin を取り出す。

アップデーターは WinRAR SFX (RAR 自己解凍書庫) で、中には
B500Update/firmware/firmware.bin が 1 個だけ入っている。

注意: libarchive の RAR 解凍は、この書庫では末尾付近のバイトが壊れて
CRC エラーになり、ハッシュが一致しないことを実測で確認した。
そのため、このスクリプトは公式 unrar を使い、最後に SHA-256 を照合する。

使い方:
    python3 extract_updater.py F-B500-V15W_0_rqle.exe <出力ディレクトリ>
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

# unrar で展開して確認した firmware.bin の SHA-256
EXPECTED_FIRMWARE_SHA256 = (
    "b1ab90723d9d1e42957b0fef18bcf186f430bffb2a240f2a36f7c10ad102a50e"
)
EXPECTED_UPDATER_SHA256 = (
    "821279858ea1976ebf26ebccbef088b7b4671def43e61f2f513bf59e85641ba2"
)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    updater = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)

    digest = sha256_of(updater)
    print(f"updater sha256: {digest}")
    if digest != EXPECTED_UPDATER_SHA256:
        print("警告: アップデーターのハッシュが調査対象と違う。別版の可能性がある。")

    unrar = shutil.which("unrar")
    if unrar is None:
        print("エラー: unrar が見つからない。RARLAB 公式 unrar を入れてから再実行すること。")
        print("libarchive 系の解凍はこの書庫でデータが壊れるため使わない。")
        return 1
    subprocess.run(
        [unrar, "x", "-o+", str(updater), str(outdir) + "/"],
        check=True,
    )
    firmware = outdir / "B500Update" / "firmware" / "firmware.bin"
    if not firmware.exists():
        print("エラー: firmware.bin が展開できなかった。")
        return 1
    fdigest = sha256_of(firmware)
    print(f"firmware.bin size: {firmware.stat().st_size}")
    print(f"firmware.bin sha256: {fdigest}")
    if fdigest != EXPECTED_FIRMWARE_SHA256:
        print("エラー: firmware.bin のハッシュが一致しない。展開が壊れている。")
        return 1
    print("OK: ハッシュ一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
