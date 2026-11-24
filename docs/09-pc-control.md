# 外部 PC からの操作

## 結論

PC から使えるのは画像転送だけである。USB は MTP/PTP と
マスストレージ、Wi-Fi のリモート撮影はスマホアプリ (SnapBridge)
向けであり、PC から撮影を制御する公開手段はない。
ファームウェア内部では、デバッグコンソールが最も広い操作面になる。

## 根拠 1: USB の素性は USBSTR.TXT に書かれている

RO_RES/USBSTR.TXT の実内容 (evidence/usbstr.txt) では、
ベンダー ID は 0x04B0 (Nikon) で、製品 ID は
マスストレージ (MSDC)、PTP (SIDC)、PC カメラ (PCCAM) の
3 モードとも 0x0362 である。
SIDC のデバイス名は "NIKON DSC COOLPIX B500"、
版数は "COOLPIX B500 V1.5"。
転送プロトコルは公式仕様でも MTP/PTP と明記されている。

PC カメラ (PCCAM) の製品 ID が定義自体はされている点は、
docs/06 の UVC 実装の存在と符合する。ただし製品 UI からは
選べない。

## 根拠 2: Wi-Fi リモートはスマホ向けの内部プロトコル

コードには、Wi-Fi 経由のアプリ命令を UI 側へ渡す
`MSG_UI_WIFI_APCMD_*` というメッセージ群と、
"PTP Access via wifi" という表示がある。
これは SnapBridge 連携の実装であり、PC 向けの公開 API ではない。
Nikon の PC 用リモート制御ソフト (Camera Control Pro 等) の
対応機種にも B500 は入っていない。

## 根拠 3: デバッグコンソールが内部の操作面

docs/10 のとおり、本体にはデバッグコンソールが組み込まれており、
USB モード切替、ISO の強制、フォーカスの位置指定などを
コマンドで操作できる。PC からの本格的な操作を狙うなら、
公開プロトコルではなくこのコンソールが対象になる。
ただし接続方法は未確定である。
