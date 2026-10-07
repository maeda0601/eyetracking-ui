---
type: Index
title: eyetracking-ui（顔マウスツール）
description: 顔の向き（鼻先の位置）でカーソル移動し、ウインクでクリックするハンズフリーのマウス操作ツール
tags: [eyetracking, mediapipe, pyautogui]
generated:
  by: agent:claude-code
  at: 2026-10-07T00:00:00Z
status: draft
---

# eyetracking-ui（顔マウスツール）

Webカメラで顔を撮影し、鼻先の位置でカーソルを動かし、ウインクでクリックするツールです（Windows 11 想定）。

## 構成

- [start_face_mouse.bat](start_face_mouse.bat) … 起動用バッチファイル（ダブルクリックで起動）
- [settings_face_mouse.bat](settings_face_mouse.bat) … 設定画面を開くバッチファイル
- [scripts/face_mouse.py](scripts/face_mouse.py) … メインスクリプト
- [scripts/face_mouse_settings.py](scripts/face_mouse_settings.py) / [scripts/settings_schema.py](scripts/settings_schema.py) … 設定画面と設定項目の定義
- [scripts/gen_codemap.py](scripts/gen_codemap.py) … コード構造マップの生成スクリプト
- [pyproject.toml](pyproject.toml) / `uv.lock` … 依存パッケージ（uv で管理。`uv sync` で環境構築、`uv run scripts/face_mouse.py` で起動）
- [requirements.txt](requirements.txt) … オフライン環境向けの依存一覧（`uv export` で自動生成）
- [scripts/download_model.py](scripts/download_model.py) … 顔検出モデルの取得
- `models/face_landmarker.task` … MediaPipe Face Landmarker のモデル（`download_model.py` で取得。Git には含めない）
- [README.md](README.md) / [LICENSE](LICENSE) … GitHub 公開用の説明とライセンス（MIT）
- [docs/manual.md](docs/manual.md) … メンバー向け利用マニュアル（まずはこちら。HTML版：[docs/manual.html](docs/manual.html)）
- [docs/](docs/index.md) … ドキュメント一覧
- [okf_summary.md](okf_summary.md) … ドキュメント整理ルール（OKF v0.2）
- [CLAUDE.md](CLAUDE.md) … エージェント向けの開発ルール
