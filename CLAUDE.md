# CLAUDE.md

# プロジェクト概要

Webカメラで **顔の向き（鼻先の位置）でカーソル移動 ＋ ウインクでクリック** を行う、ハンズフリーのマウス操作ツール（Python）。

- 視線だけのカーソル操作は精度が低くブレやすいため、上記のハイブリッド方式を採用している
- 想定環境：Windows 11、ネットワーク制限のある製造現場。**外部依存は最小限**にする
- 使用ライブラリ：`mediapipe`（Face Landmarker／Tasks API）、OpenCV（mediapipe 経由で入る `opencv-contrib-python`。カメラ取得・確認ウィンドウ）、`pyautogui`（マウス操作）、`tkinter`（標準ライブラリ。画面上部の状態表示）

## 機能要件（実装時の判断基準）

1. カーソル移動：鼻先ランドマークの移動量を画面座標に変換。起動時の顔位置を中心とし、感度は調整可能にする。`c` キーで現在の顔位置を中心に再設定できる
2. ブレ対策：指数平滑化 ＋ 微小な動きを無視するデッドゾーン。ウインク中はカーソルを止めてクリック位置のズレを防ぐ
3. 左クリック／ダブルクリック：左目だけのウインク（EAR＝Eye Aspect Ratio で判定）。0.3秒以上閉じて1秒未満で開けると左クリック（開けた時点で確定）、1秒続けるとダブルクリック
4. 右クリック／スクロール：右目だけのウインク。0.3秒以上閉じて2秒未満で開けると右クリック（開けた時点で確定）、2秒続けるとスクロール保持モード（カーソルを止め、開始時の鼻先の高さを基準に顔の上下でスクロール。もう一度ウインクで解除。解除のウインクではクリックしない）
5. 誤作動防止：両目の通常のまばたきは無視（左右のEAR差で判定）。ウインクは一定時間継続で確定し、クリック後はクールダウンを入れる
6. キー操作（確認ウィンドウ選択時）：`p` で一時停止／再開、`c` で中心の再設定、`q` または `ESC` で終了。グローバルホットキー（Windowsのみ、ウィンドウの有無に関係なく有効）：`Ctrl+Alt+P` で一時停止／再開、`Ctrl+Alt+C` で中心の再設定、`Ctrl+Alt+W` で確認ウィンドウの表示／非表示、`Ctrl+Alt+Q` で終了
7. 起動直後は無効（一時停止）状態とし、両目を2秒閉じ続けると有効にする。有効中に両目を5秒閉じ続けると無効に戻す（通常のまばたきで誤って有効にならないよう継続時間で判定）
8. 起動中は画面上部中央に半透明・最前面・クリック透過の状態表示（tkinter）を常に出す。確認ウィンドウは起動時には表示しない（`Ctrl+Alt+W` で表示）。表示時はカメラ映像にランドマーク、EAR値、状態（ACTIVE／PAUSED／NO FACE）、クリック通知、左ウインクの経過時間を表示
9. 感度・しきい値などのパラメータはファイル冒頭に定数（アッパースネークケース）でまとめる
10. `pyautogui.FAILSAFE` は**有効のまま**にし、その旨をコメントで説明する（画面隅へのマウス移動で緊急停止できるようにするため）

## 開発ルール

- スクリプトは `scripts/` に保存する（メイン：`scripts/face_mouse.py`）
- PEP8準拠、インデント4スペース、関数・変数はスネークケース
- カメラが開けない等のエラーは `try/except` で処理し、日本語のメッセージを出す。握りつぶしは禁止
- 依存パッケージは **uv** で管理する（`pyproject.toml` / `uv.lock`、Python 3.12）。追加・変更は `uv add` で行い、実行は `uv run scripts/face_mouse.py`
- `requirements.txt` はオフライン環境の pip 向けに `uv export --no-hashes --no-dev --no-emit-project -o requirements.txt` で書き出す（手で編集しない）
- コードは古い書き方（`format` など）を維持し、極力 Python 3.6〜でも読める構文にする（実行環境は mediapipe の対応バージョンに従う）
- 動作確認はカメラ・画面操作を伴うため、エージェント側では構文チェックと import 確認までにとどめる

## コード構造マップ（探索コスト削減）

コードを探索する前に、まずこのセクションと [docs/CODEMAP.md](docs/CODEMAP.md) を参照し、対象ファイルを絞り込むこと。grep / Glob による総当たり探索は、マップで見つからない場合にのみ行う。

### 概要（ここは数十行以内に保つ）

- `scripts/face_mouse.py` … メインスクリプト（カメラ取得 → ランドマーク検出 → カーソル移動・クリック判定 → 表示）。`WinkDetector`（ウインク判定）、`CursorController`（平滑化・デッドゾーン）、`ScrollController`（スクロール保持モード）、`GlobalHotkeys`（グローバルホットキー）、`run()`（メインループ）
- `start_face_mouse.bat` … 起動用バッチ（`.venv` が無ければ `uv sync`、あれば `.venv` の Python で直接起動）。日本語を含むため **Shift-JIS（cp932）・CRLF** で保存する
- `scripts/gen_codemap.py` … `docs/CODEMAP.md` を `ast` で自動生成するスクリプト（`uv run scripts/gen_codemap.py`）
- `models/face_landmarker.task` … MediaPipe Face Landmarker のモデル（`scripts/download_model.py` で取得。Git には含めない。mediapipe 1.x は旧 `mp.solutions` が無く Tasks API 必須）
- `scripts/download_model.py` … モデルの取得（SHA-256 で検証）
- `README.md` / `LICENSE`（MIT）… GitHub 公開用（maeda0601/eyetracking-ui、Public）。コミットの作者メールは GitHub の noreply アドレス（リポジトリのローカル設定）
- `pyproject.toml` / `uv.lock` / `.python-version` … uv のプロジェクト定義・ロックファイル（OpenCV は mediapipe 経由の opencv-contrib-python を使うため個別指定しない）
- `requirements.txt` … `uv export` で書き出したオフライン用の依存一覧（自動生成）
- `docs/manual.md` … メンバー向け利用マニュアル（利用者向け／導入担当者向けの2部構成）。HTML版 `docs/manual.html` もある。操作・パラメータ・エラーメッセージを変えたら両方を合わせて更新する
- `docs/usage.md` … インストール・操作方法（開発者向けメモ）
- `docs/CODEMAP.md` … 関数・クラスの詳細マップ（自動生成。手で編集しない）
- `index.md` / `docs/index.md` … OKF の段階的開示用インデックス
- `okf_summary.md` … ドキュメント整理ルール（OKF v0.2）の仕様まとめ
- `CLAUDE.template.md` … 本ファイルの元テンプレート（編集不要）

### 主要な処理フロー

- メインループ：`cv2.VideoCapture` でフレーム取得 → mediapipe で顔ランドマーク検出 → 鼻先座標を平滑化・デッドゾーン処理 → `pyautogui.moveTo` → 左右EARからウインク判定 → `pyautogui.click` → 確認ウィンドウ描画・キー入力処理

### 規約・注意箇所

- パラメータ（感度、平滑化係数、デッドゾーン、EARしきい値、ウインク確定時間、クールダウン、有効化時間）はハードコードせず、冒頭の定数を参照する
- `pyautogui.FAILSAFE = False` にする変更は禁止

### 詳細マップ（docs/CODEMAP.md）の運用ルール

- 関数・クラスの一覧は `CLAUDE.md` には書かず、`docs/CODEMAP.md` に分離する（毎回のトークン消費を抑えるため）
- `docs/CODEMAP.md` は手書きせず、スクリプト（例: `scripts/gen_codemap.py`。Pythonの `ast` を利用）で自動生成する
- 粒度はファイル単位を基本とし、「役割1行＋主要シンボル数個（docstringの1行目）」程度にとどめる
- 構造を変更する作業（ファイル追加・移動・削除、公開関数の追加など）の後は、生成スクリプトを再実行してマップを更新する
- マップの記述と実際のコードが食い違う場合は、コードを正としてマップを修正する
- `docs/CODEMAP.md` にもOKFのフロントマターを付与する（例: `type: Code Map`、`generated`、`stale_after`）

## ファイル整理の仕様（Open Knowledge Format / OKF v0.2準拠）

ドキュメントは **[okf_summary.md](okf_summary.md)** にまとめた **OKF v0.2** に従って整理する。新規にドキュメント（調査メモ、手順書、使い方説明など）を作成する際は以下を適用する。※ソースコードや `requirements.txt` は対象外。

### 基本構造

- 知識は **Markdownファイルのディレクトリ（バンドル）** として表現する
- 1ファイル＝1コンセプトとし、**ファイルパス自体をコンセプトのIDとする**
- ディレクトリ構成例：

  ```
  eyetracking-ui/
  ├── index.md
  ├── scripts/
  │   ├── face_mouse.py
  │   └── gen_codemap.py
  └── docs/
      ├── index.md
      ├── CODEMAP.md
      └── usage.md
  ```

### YAMLフロントマター

- **必須フィールド**: `type`（例：`Research Note`, `Playbook`, `Code Map` など）
- **推奨フィールド**: `title`, `description`, `resource`, `tags`, `sources`, `generated`（`by` 必須, `at`）, `verified`（`by`, `at`）, `status`（`draft` / `stable` / `deprecated`）, `stale_after`（`YYYY-MM-DD`）

```yaml
---
type: Playbook
title: 顔マウスツールの使い方
description: インストール手順と操作方法（ウインクでクリック、pで一時停止）
tags: [eyetracking, mediapipe, usage]
generated:
  by: agent:claude-code
  at: 2026-10-06T00:00:00Z
status: draft
---
```

### 運用ルール

- コンセプト間の関連付けは通常のMarkdownリンク（`[表示名](パス)`）で行う
- 段階的開示が必要なディレクトリには `index.md` を、変更履歴が必要なものには `log.md` を任意で置く
- **適合性の原則**: 未知の`type`、欠落したオプションフィールド、壊れたリンクがあっても、ファイル・バンドル全体を拒否せず読み進めること（MUST NOT reject）
- 既存ドキュメントを更新する際も、フロントマターを追記・維持すること

## 応答言語

- すべての説明・回答は日本語で行う（ユーザーのグローバル指示に準拠）
- プランモードでプランを作成したら、plan.mdファイルとして保存する
- コードコメントも日本語で記述する
- エラーメッセージの説明も日本語で行う
- ユーザーの判断を求める場合はAskUserQuestionを利用
