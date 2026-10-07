# CLAUDE.md

> このファイルは新規プロジェクト用のテンプレートです。
> プロジェクト直下に `CLAUDE.md` としてコピーし、`<< >>` の箇所を書き換え、
> 不要なセクションは丸ごと削除してください。

# プロジェクト指示

## ファイル整理の仕様（Open Knowledge Format / OKF v0.2準拠）

このプロジェクトでは、ファイル・ドキュメントを **[okf_summary.md](okf_summary.md)** にまとめた **Open Knowledge Format（OKF）v0.2** の仕様に従って整理すること。新規にドキュメントを作成・保存する際は、必ず以下のルールを適用する。

### 基本構造

- 知識は **Markdownファイルのディレクトリ（バンドル）** として表現する
- 1ファイル＝1コンセプト（例：調査結果、テーブル定義、メトリクス、手順書など）とし、**ファイルパス自体をコンセプトのIDとする**
- ディレクトリ構成例：

  ```
  project-root/
  ├── index.md
  ├── research/
  │   ├── index.md
  │   └── repository-research.md
  └── docs/
      ├── index.md
      └── ...
  ```

### YAMLフロントマター

各Markdownファイルの先頭に、以下のYAMLフロントマターを付与する。

- **必須フィールド**: `type`（例：`Research Note`, `Table`, `Metric`, `Playbook` など、内容を表す種別）
- **推奨フィールド**:
  - `title` — コンセプトのタイトル
  - `description` — 概要（1〜2文）
  - `resource` — 参照元URL等（あれば）
  - `tags` — 分類タグ
  - `sources` — 派生元資料（`resource`必須、`author`, `usage_count`, `last_modified`等を任意で付与）
  - `generated` — 作成情報（`by`: 作成者/エージェント名は必須、`at`: 生成・最終更新日時）
  - `verified` — 検証情報（`by`, `at`。人間によるレビューかエージェントによる確認かを区別する）
  - `status` — ライフサイクル（`draft` / `stable` / `deprecated`）
  - `stale_after` — 陳腐化タイミング（`YYYY-MM-DD`の絶対日付）

フロントマター記述例：

```yaml
---
type: Research Note
title: stablyai/orca リポジトリ調査
description: OrcaのGitHubリポジトリ概要・機能・ディスク使用量の調査結果
tags: [orca, github, research]
sources:
  - resource: https://github.com/stablyai/orca
generated:
  by: agent:claude-code
  at: 2026-08-31T10:00:00Z
status: stable
---
```

### 運用ルール

- コンセプト間の関連付けは通常のMarkdownリンク（`[表示名](パス)`）で行い、ディレクトリの親子関係より豊かなグラフ構造を作る
- 段階的開示が必要なディレクトリには `index.md` を、変更履歴が必要なものには `log.md` を任意で置く
- **適合性の原則**: 未知の`type`、欠落したオプションフィールド、壊れたリンクがあっても、ファイル・バンドル全体を拒否せず読み進めること（MUST NOT reject）
- 既存ファイル（例：[orca-repository-research.md](orca-repository-research.md)）を更新する際も、上記フロントマターを追記・維持すること
- 仕様の詳細・背景・v0.1からの変更点は [okf_summary.md](okf_summary.md) を参照すること

## コード構造マップ（探索コスト削減）

コードを探索する前に、まずこのセクションと [docs/CODEMAP.md](docs/CODEMAP.md) を参照し、対象ファイルを絞り込むこと。grep / Glob による総当たり探索は、マップで見つからない場合にのみ行う。

### 概要（ここは数十行以内に保つ）

<< ディレクトリごとの役割と入口ファイルを1行ずつ記述する。例: >>

- `src/api/` … HTTPハンドラ。ルーティングは `routes.py`
- `src/services/` … 業務ロジック。受注処理は `order_service.py`
- `src/db/` … SQLiteアクセス。スキーマは `schema.sql`

### 主要な処理フロー

<< 機能をまたぐ処理の流れを記述する。例: >>

- 受注登録: 画面 `templates/order.html` → API `src/api/order.py` → `src/services/order_service.py` → `src/db/order_repo.py`

### 規約・注意箇所

<< 命名規則、触ってはいけないファイル、生成物の場所などを記述する。例: >>

- `src/legacy/` は他システム連携のため変更禁止
- `*_generated.py` は自動生成物のため直接編集しない

### 詳細マップ（docs/CODEMAP.md）の運用ルール

- 関数・クラスの一覧は `CLAUDE.md` には書かず、`docs/CODEMAP.md` に分離する（毎回のトークン消費を抑えるため）
- `docs/CODEMAP.md` は手書きせず、スクリプト（例: `scripts/gen_codemap.py`。Pythonの `ast` や `ctags` を利用）で自動生成する
- 粒度はファイル単位を基本とし、「役割1行＋主要シンボル数個（docstringの1行目）」程度にとどめる
- 構造を変更する作業（ファイル追加・移動・削除、公開関数の追加など）の後は、生成スクリプトを再実行してマップを更新する（Claude Codeのhooksで自動化してもよい）
- マップの記述と実際のコードが食い違う場合は、コードを正としてマップを修正する
- `docs/CODEMAP.md` にも上記OKFのフロントマターを付与する（例: `type: Code Map`、`generated`、`stale_after`）

## 応答言語

- すべての説明・回答は日本語で行う（ユーザーのグローバル指示に準拠）
- プランモードでプランを作成したら、plan.mdファイルとして保存する
- コードコメントも日本語で記述する
- エラーメッセージの説明も日本語で行う
- ユーザーの判断を求める場合はAskUserQuestionを利用
