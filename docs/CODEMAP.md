---
type: Code Map
title: コード構造マップ
description: scripts/ 配下の各ファイルの役割と主要シンボル（gen_codemap.py による自動生成）
tags: [codemap, generated]
generated:
  by: script:scripts/gen_codemap.py
  at: 2026-10-07T02:51:26Z
stale_after: 2027-01-05
status: stable
---

# コード構造マップ

> このファイルは [scripts/gen_codemap.py](../scripts/gen_codemap.py) で自動生成しています。手で編集せず、`uv run scripts/gen_codemap.py` を再実行してください。

## [scripts/download_model.py](../scripts/download_model.py)

MediaPipe Face Landmarker のモデルファイルを取得するスクリプト

- `sha256_of(path)` … ファイルの SHA-256 を返す
- `check_model(path)` … モデルファイルが正しいか確かめる。問題なければ None、あれば理由を返す
- `main()`

## [scripts/face_mouse.py](../scripts/face_mouse.py)

顔の向きとウインクでマウスを操作するツール

- `calc_distance(p1, p2)` … 2点間のユークリッド距離を返す
- `calc_ear(landmarks, indices, frame_w, frame_h)` … 指定した目のEAR（Eye Aspect Ratio）を計算する
- `WinkDetector`（reset, get_hold_time, start_cooldown, long_hold_sec, update, …） … 左右のEARからウインクを判定し、実行すべき操作を返す
- `CursorController`（calibrate, update） … 鼻先の位置を画面座標に変換し、平滑化・デッドゾーン処理をしてカーソルを動かす
- `ScrollController`（start, stop, update, label） … スクロール保持モード：開始時の鼻先の高さを基準に、顔の上下でスクロールする
- `GlobalHotkeys`（poll） … ウィンドウのフォーカスに関係なくホットキーを検出する（Windowsのみ）
- `StatusOverlay`（update, close） … 画面上部中央に、常に最前面・半透明・クリック透過の状態表示を出す（tkinter使用）
- `create_landmarker()` … Face Landmarker を生成する（モデルファイルがなければ例外）
- `open_camera()` … カメラを開く（開けなければ例外）
- `draw_landmarks(frame, landmarks)` … 鼻先・目のランドマークを映像に描画する
- `draw_status(frame, paused, ear_left, ear_right, face_found, click_msg)` … 状態・EAR値・操作説明を映像に描画する（OpenCVの制約で英字表示）
- `run()` … メインループ
- `main()`

## [scripts/gen_codemap.py](../scripts/gen_codemap.py)

docs/CODEMAP.md を自動生成するスクリプト

- `first_line(docstring)` … docstring の1行目を返す（無ければ空文字）
- `format_args(func_node)` … 関数の引数名をカンマ区切りで返す（self は除く）
- `collect_symbols(tree)` … モジュール直下のクラス・公開関数を (表示名, 説明) のリストで返す
- `parse_file(path)` … 1ファイルを解析し、(役割, シンボル一覧) を返す
- `build_markdown(entries, now)` … CODEMAP.md の本文を組み立てる
- `main()`
