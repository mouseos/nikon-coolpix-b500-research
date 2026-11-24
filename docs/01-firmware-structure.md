# ファームウェアの構造

## 結論

アップデーターの中身は `firmware.bin` 1 個だけである。
その正体は Sunplus / iCatch 系の書き込み形式「SUNP BURN FILE」で、
中身は MIPS32 リトルエンディアンのコード 2 本と、FAT ファイルシステム 2 個を
1 ファイルに並べた構造だった。暗号化はされていない。

## アップデーター

- ファイル名は `F-B500-V15W_0_rqle.exe`、12,005,248 バイト。
- 形式は WinRAR SFX。先頭 102,912 バイトが PE32 の SFX モジュールで、
  その後ろに RAR 書庫が続く。
- 書庫の中身は `B500Update/firmware/firmware.bin` (39,106,238 バイト) だけ。
  ハッシュは `evidence/hashes.txt` にある。
- libarchive の RAR 解凍では末尾付近のバイトが壊れてハッシュが一致しない
  ことを実測した。展開は公式 unrar を使う (scripts/extract_updater.py)。

## firmware.bin のレイアウト

先頭 16 バイトが `SUNP BURN FILE`、続く 0x10 から 4 バイトずつの
オフセット表が並ぶ。実測した配置は次のとおり (根拠: evidence/partition-map.txt)。

| 開始 | 終了 | 中身 |
|---|---|---|
| 0x000000 | 0x000200 | ヘッダ (マジック + オフセット表) |
| 0x000200 | 0x093400 | ブートローダ側イメージ (MIPS32LE) |
| 0x093400 | 0x094400 | SUNP BURN HDR 1 |
| 0x094400 | 0x094520 | SUNP BURN HDR 2 |
| 0x094520 | 0x1694520 | FAT16 イメージ (ドライブ A: RO_RES) |
| 0x1694520 | 0x1714520 | FAT12 イメージ (ドライブ B: USER_RES) |
| 0x1714520 | 0x254AD20 | 本体イメージ (MIPS32LE) |
| 0x254AD20 | 0x254B360 | SUNP BURN HDR 3 (校正ファイル一覧) |
| 0x254B360 | 0x254B6BE | DRAM パラメータ (先頭文字列 `DRAMPAR1`) |

境界は推測ではない。FAT16 の BPB が示す総セクタ数 45,056 × 512 バイト =
23,068,672 バイトで、開始位置に足すと FAT12 の開始位置と一致する。
FAT12 の終端は本体イメージの開始位置と一致する。
ヘッダ先頭フィールドはファイル全体長と一致する。

## コードイメージ

- 2 本とも先頭がリセット処理で始まり、読み込み先は 0x80000000 起点。
  逆アセンブルは MIPS32 リトルエンディアンで命令として読める
  (ARM や MIPS ビッグエンディアンでは読めない)。
- 本体イメージは約 14.9 MB。コード、文字列、Wi-Fi / Bluetooth の
  スタック、CardUpdate (カード更新) の実装まで含む。
- SoC は SPCA6350。根拠はリソースファイル `RO_RES/ALCSTR.TXT` と
  `RO_RES/ALCZoom.TXT` の先頭行がどちらも `SPCA6350ALCv1` で始まること。
  SPCA6350 は iCatch Technology (旧 Sunplus 系) のカメラ用 SoC。
- コード内のエラーメッセージには `sp5kFsFileRead()` のような
  iCatch SDK の関数名が残っている。

## リソース (FAT イメージ)

- A: RO_RES は FAT16 で 440 件。UI の背景 JPG、アイコン、フォント、
  36 言語の文言テキスト、音声、画質 (IQ) データ、USB 設定ファイルが入る。
  一覧は evidence/fat-list.txt。
- B: USER_RES は FAT12 で 512 KB。UIDATA.BIN と UIPAIRED.BIN、
  空の RES_JPG フォルダだけが入る。
- バージョンは V1.5。根拠は `RO_RES/USBSTR.TXT` の
  `SIDC_DEVICE_VERSION = "COOLPIX B500 V1.5"` と
  `MSDC_REVISION_ID = "COOLPIX B500 V1.5"` (evidence/usbstr.txt)。

## HDR3 は校正データの保護一覧

HDR3 には 0x70 バイト × 14 件でファイル名が並ぶ。
COLD.BIN、欠陥画素データ (DEFTPXL、BPCAP、BPVIDEO、VIDEOPIX) など、
個体ごとの校正データばかりである。
更新時にこの一覧のファイルを退避・復元し、校正を失わないための
仕組みとみられる (更新側の処理は docs/02 を参照)。
