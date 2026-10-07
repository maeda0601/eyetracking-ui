---
type: Playbook
title: 顔マウスツールの使い方
description: face_mouse.py のインストール手順・モデル配置・操作方法・パラメータ調整のポイント
tags: [eyetracking, mediapipe, pyautogui, usage]
sources:
  - resource: ../scripts/face_mouse.py
generated:
  by: agent:claude-code
  at: 2026-10-07T01:00:00Z
status: draft
---

# 顔マウスツールの使い方

[scripts/face_mouse.py](../scripts/face_mouse.py) は、顔の向きでカーソルを動かし、ウインクでクリックするツールです。

## インストール

依存パッケージは [uv](https://docs.astral.sh/uv/) で管理しています（`pyproject.toml` / `uv.lock`）。Python 3.12 を使います。

```
uv sync
```

- `.venv` に仮想環境が作られ、`uv.lock` に記録されたバージョンがそのまま入ります
- パッケージを追加・変更するときは `uv add <パッケージ名>` を使い、その後 `uv export --no-hashes --no-dev --no-emit-project -o requirements.txt` で `requirements.txt` も更新します
- オフラインのPCでは、ネットにつながるPC（Python 3.12）で `py -3.12 -m pip wheel -r requirements.txt -w wheels` を実行し、`wheels` フォルダを持ち込んで次の手順でインストールします
  （pyautogui などは wheel が配布されていないため、`pip download` ではなく `pip wheel` でビルド済みの形にして持ち込みます）
  1. `uv venv --python 3.12`
  2. `uv pip install --no-index --find-links wheels -r requirements.txt`

## モデルファイルの配置（必須）

mediapipe 0.10.30 以降では旧API（`mp.solutions`）が削除されたため、Face Landmarker のモデルファイルが必要です。

```
uv run scripts/download_model.py
```

- `models/face_landmarker.task`（約3.6MB）に保存し、SHA-256 で中身を確認します（`start_face_mouse.bat` の初回起動時にも自動実行）
- モデルはリポジトリに含めていません（`.gitignore` で除外）
- ダウンロードできない環境では、次のURLをブラウザで開いて `models/face_landmarker.task` に保存する
  `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`

## 起動

```
uv run scripts/face_mouse.py
```

起動直後は **無効（PAUSED）状態** です。カーソルは動かず、クリックもしません。

- 両目を **2秒** 閉じ続けると有効（ACTIVE）になります（閉じている間は画面に `ACTIVATING 1.2s / 2.0s` のように経過時間が出ます）
- 初めて有効になったときの顔の位置が、カーソルの中心（画面中央）になります
- 有効中に両目を **5秒** 閉じ続けると無効に戻ります（`DEACTIVATING 2.0s / 5.0s` のように経過時間が出ます）
- 切り替えた後は、いったん目を開けるまで次の切り替えは起きません
- `p` キーや `Ctrl+Alt+P` でも切り替えられます

## 操作方法

| 操作 | 動作 |
|---|---|
| 顔を上下左右に向ける | カーソル移動 |
| 左目だけを0.3秒以上閉じて、1秒未満で開ける | 左クリック（目を開けた時点で確定） |
| 左目だけを1秒以上閉じる | ダブルクリック（1秒に達した時点で確定） |
| 右目だけを0.3秒以上閉じて、2秒未満で開ける | 右クリック（目を開けた時点で確定） |
| 右目だけを2秒以上閉じる | スクロール保持モード開始（カーソル停止、顔の上下でスクロール、もう一度ウインクで解除） |
| 両目のまばたき | 無視される |
| 無効状態で両目を2秒閉じる | 有効にする |
| 有効状態で両目を5秒閉じる | 無効に戻す |
| `p` キー | 一時停止／再開 |
| `c` キー | 今の顔の位置を中心に再設定 |
| `q` / `ESC` キー | 終了 |
| `Ctrl+Alt+P` | 一時停止／再開 |
| `Ctrl+Alt+C` | 今の顔の位置を中心に再設定 |
| `Ctrl+Alt+W` | 確認ウィンドウ（カメラ映像）の表示／非表示 |
| `Ctrl+Alt+Q` | 終了 |
| 実際のマウスを画面の四隅へ移動 | 緊急停止（pyautogui の FAILSAFE） |

- 起動中は **画面上部中央に半透明の小さな状態表示** が常に出ます（例：`顔マウス：無効（両目2秒で有効）`、`顔マウス：有効`）。クリックは下のウィンドウへ透過するので、操作の邪魔にはなりません
- 確認ウィンドウ「Face Mouse」は **起動時には表示されません**。EAR値や状態を見たいときは `Ctrl+Alt+W` で表示してください（`SHOW_WINDOW_ON_START = True` で起動時から表示）
- 確認ウィンドウの×ボタンで閉じても動作は続きます。終了は `Ctrl+Alt+Q` です
- ウィンドウ非表示中は、有効／無効の切り替えやクリックの結果がコンソールに表示されます
- `p` / `c` / `q` / `ESC` は確認ウィンドウが表示中かつアクティブなときだけ有効です
- `Ctrl+Alt+*` はどのウィンドウを操作中でも効きます（Windowsのみ）。キー入力は横取りしないため、操作中のアプリにも同じキーが届きます。他のアプリと重なる場合は `HOTKEY_*` 定数で変更してください

## 調整のポイント

パラメータは設定画面（`settings_face_mouse.bat`、または動作中に `Ctrl+Alt+S`）で変更できます。保存すると動作中のツールに約1秒で反映されます（カメラ番号などは再起動後）。既定値は `face_mouse.py` 冒頭の定数で、設定画面の値は `scripts/face_mouse_config.json` に保存されます。

- カーソルが動きすぎる／足りない → `SENSITIVITY_X` / `SENSITIVITY_Y`
- カーソルが震える → `SMOOTHING_ALPHA` を小さく、`DEAD_ZONE_PX` を大きく
- ウインクが反応しない → 画面左上の `L-EAR` / `R-EAR` を見ながら `EAR_CLOSED_THRESHOLD` を上げる
- ウインク中に反対の目もつられて細くなり、判定が途切れる → `WINK_EAR_DIFF` / `WINK_KEEP_EAR_DIFF`（左右のEAR差の条件）を小さくする
- 誤クリックが多い → `WINK_HOLD_SEC` や `CLICK_COOLDOWN_SEC` を長くする
- 状態表示を薄く／濃くしたい → `OVERLAY_ALPHA`。消したい → `SHOW_STATUS_OVERLAY = False`
- 有効化／無効化までの時間を変えたい → `ACTIVATE_HOLD_SEC` / `DEACTIVATE_HOLD_SEC`。起動直後から有効にしたい → `START_PAUSED = False`
- ダブルクリックまでの時間を変えたい → `DOUBLE_CLICK_HOLD_SEC`（左ウインク中は画面に `L-HOLD 0.6s / 1.0s` のように経過時間が出る）
- スクロール保持の開始時間・速度 → `SCROLL_HOLD_SEC` / `SCROLL_SPEED_GAIN` / `SCROLL_MAX_NOTCHES_PER_SEC` / `SCROLL_DEAD_ZONE`
