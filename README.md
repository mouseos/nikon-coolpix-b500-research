# Nikon COOLPIX B500 ファームウェア調査

COOLPIX B500 の公式ファームウェアアップデーター (V1.5) を展開し、
中身の構造とコードを解析した記録である。
判定はすべて、命令 (逆アセンブル) を読んだ結果か、データ構造や
実ファイルの内容を解析した結果に基づく。
文字列を抜き出しただけの推測は根拠にしていない。

## 結論の一覧

| 調査項目 | 結論 |
|---|---|
| ファームウェア改変 (署名) | 署名検証はない。マジック文字列の比較と書き込み後の読み戻し比較だけ。改変の壁は署名ではない (実機書き込みは未検証) |
| RAW 画像取得 | 通常撮影では不可 (JPEG のみ)。RAW を SD へ書き出す関数は実装されているが、通常の撮影経路から呼ばれない |
| マニュアルフォーカス | 不可。"Manual" は AF エリア位置の手動選択であり、距離の手動調整ではない |
| NR を切る | メニューに項目はない。NR は IQ データ側のパラメータで決まるソフトウェア処理 |
| USB ウェブカメラ | UVC 実装一式は入っているが、製品 UI からは有効化できない。デバッグコンソールの "pc" コマンドで起動する設計 |
| ISO・露光の限界突破 | 制限は AE のエントリテーブルのソフトウェア制限。内部 API では直接指定できる |
| 自作 UI | UI はデータ駆動。リソース差し替えは可能、新規画面はコード改変が要る |
| 外部 PC 操作 | 転送のみ (MTP/PTP、マスストレージ)。撮影制御はスマホ向け Wi-Fi のみ |
| 工場・テストモード | 実在する。校正未完了の個体は自動で入り、校正済みの個体は SD カードに `EnableTest.txt` を置くと入る |
| ハードウェアの限界 | 止めているのは全てソフトウェア。センサーは Sony IMX206 で、RAW 出力、位置指定フォーカス駆動、広い露光範囲の実装がある |
| HDR | 実装済み (Morpho EasyHDR の複数枚合成)。ただし使えるのは逆光シーンの中だけ |
| 動画の上限 | 時間上限 (1800 秒) とビットレートはソフト側の値で改造で動かせる。解像度は 1080p が天井、4K の経路はない。動画 HDR はそのままでは実装できない |
| ISP の未使用機能 | WDR はデータ不在で未構成。Super Resolution も呼び出しの形跡がない。レンズ補正と画質処理は使い切れている |

## 目次

- [01 ファームウェアの構造](docs/01-firmware-structure.md)
  — SUNP BURN FILE のレイアウト、FAT イメージ、SPCA6350
- [02 ファームウェア改変の可能性 (署名検証)](docs/02-modification-and-signature.md)
  — マジック比較と読み戻し memcmp の実測
- [03 RAW 画像の取得](docs/03-raw-capture.md)
  — RAW 書き出し関数 (0x803672C0) と呼び出し関係
- [04 マニュアルフォーカス](docs/04-manual-focus.md)
  — AF エリアモードの実内容と駆動コード
- [05 ノイズリダクションを切る](docs/05-noise-reduction.md)
  — reduceNoise の呼び出し条件と IQ データ
- [06 USB ウェブカメラ](docs/06-usb-webcam.md)
  — USBUVC.BIN のディスクリプタと "pc" コマンド
- [07 ISO と露光時間の上限・下限の突破](docs/07-iso-shutter-limits.md)
  — AE エントリと内部 API
- [08 自作 UI の可能性](docs/08-custom-ui.md)
  — UIDATA.BIN (FIF1) とリソース駆動の UI
- [09 外部 PC からの操作](docs/09-pc-control.md)
  — USBSTR.TXT、MTP/PTP、Wi-Fi リモートの範囲
- [10 デバッグコンソール](docs/10-debug-console.md)
  — コマンドハンドラと未確認の接続方法
- [11 工場・テストモード](docs/11-factory-test-mode.md)
  — 入り方 (COLDDATA のフラグと `EnableTest.txt`) と校正項目の中身
- [12 ハードウェアとして可能か](docs/12-hardware-capability.md)
  — IMX206 と駆動系の実装から見た項目ごとの判定
- [13 HDR は実装できるか](docs/13-hdr.md)
  — Morpho EasyHDR の実装と、逆光シーンへの限定、拡張の余地
- [14 動画の HDR、時間上限、ビットレート、解像度上限](docs/14-video-limits.md)
  — 時間上限の定数、HW エンコーダ、WDR のデータ不在、1080p の天井
- [15 ISP の未使用機能](docs/15-isp-unused-features.md)

- [16 同一チップ他機種とのファームウェア比較](docs/16-cross-model-comparison.md)
  — WDR、Super Resolution、JPEG Ultra、Hi-ISO フローの利用状況

## 調査方法

1. アップデーター (WinRAR SFX) を公式 unrar で展開し、
   firmware.bin のハッシュを照合する。
2. SUNP ヘッダと FAT の BPB を読み、領域の境界を実測で確定する。
3. 本体イメージを MIPS32 リトルエンディアンとして逆アセンブルし、
   文字列への参照 (lui/addiu の組) をたどって関数を特定する。
4. 特定した関数の命令を読み、処理の流れを結論の根拠にする。

再現用のスクリプトは scripts にある。

- `extract_updater.py` — 展開とハッシュ照合
- `parse_burn.py` — 構造の解析と境界の検証
- `fat_list.py` — 内蔵 FAT の一覧と取り出し
- `xref_scan.py` — 文字列への参照元の走査
- `funcdis.py` — 文字列注釈付き逆アセンブル
- `parse_uvc.py` — USBUVC.BIN のディスクリプタ解析

根拠の実物 (逆アセンブルの抜粋、一覧、ディスクリプタ解析結果) は
evidence にある。ファームウェア本体と展開したリソースは、
Nikon の著作物のためこのリポジトリには含めない。

## 対象

- アップデーター: F-B500-V15W_0_rqle.exe (ファームウェア V1.5)
- firmware.bin: 39,106,238 バイト、
  SHA-256 は evidence/hashes.txt
- 解析日: 2026-11-24
