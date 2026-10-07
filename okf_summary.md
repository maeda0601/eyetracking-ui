# Open Knowledge Format(OKF)まとめ

参照元:
- [How the Open Knowledge Format can improve data sharing](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing?hl=en)（Google Cloud Blog、OKF v0.1発表時点）
- [GoogleCloudPlatform/knowledge-catalog (okf/SPEC.md)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)（現行仕様、**v0.2**）

> 上記ブログ記事はv0.1発表時のもので、v0.2の内容は含まれていません。本まとめではリポジトリのSPEC.mdを基に**v0.2**の内容に更新しています。

## 概要

**Open Knowledge Format（OKF）** は、Google Cloudが発表した、AIエージェントやLLMが利用する「メタデータ・コンテキスト・キュレーションされた知識」を表現するための**ベンダーニュートラルなオープン仕様**。現行バージョンは **OKF v0.2**（v0.1は2026年6月発表、v0.2で信頼性・鮮度関連のフィールドを追加）。

- 知識を **Markdownファイルのディレクトリ** として表現
- 各ファイルに **YAMLフロントマター** を付与
- 少数の合意された規約により、異なる作成者が書いたwikiを異なるエージェントが翻訳なしで利用可能

著者: Sam McVeety（Data Analytics Tech Lead）、Amir Hormati（BigQuery Tech Lead）（いずれもGoogle Cloud Data Cloud部門）

## 開発の背景・目的

### 課題：断片化したコンテキスト

組織内でAIが必要とする情報（テーブルスキーマ、メトリクス定義、インシデント対応手順、システム間の結合パス、API廃止通知など）は、以下のように分散している。

- 独自APIを持つメタデータカタログ
- Wiki、サードパーティシステム、共有ドライブ
- コードコメント、docstring、ノートブックのセル
- ベテランエンジニアの頭の中

結果として、シンプルな質問に答えるだけでもエージェントは互換性のない複数ソースを組み立てる必要があり、**各ベンダーが同じ問題を独自に解決し直す**非効率が生じていた。

### インスピレーション

Andrej Karpathy氏の [LLM-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) のパターンを正式な仕様に落とし込んだもの。

> "LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass." — Andrej Karpathy

Obsidianボルト、AGENTS.md/CLAUDE.md系ファイル、index.md/log.mdを使うリポジトリなど類似パターンは既に存在していたが、**バラバラで相互運用性がなかった**。

## 技術的な特徴

### 設計原則

1. **最小限の規定** — 各concept documentに必須なのは `type` フィールドのみ
2. **プロデューサー/コンシューマーの独立性** — 書き手と使い手を分離（人間が書いてAIが読む、パイプラインが生成して可視化ツールで見る、等）
3. **フォーマットであり、プラットフォームではない** — 特定クラウド・DB・モデルプロバイダー・エージェントフレームワークに非依存

### 構造

- **バンドル（bundle）**：markdownファイルのディレクトリ
- **コンセプト（concept）**：1ファイル=1コンセプト（テーブル、データセット、メトリクス、プレイブック、ランブック、APIなど）
- ファイルパス自体がコンセプトのID

```
sales/
├── index.md
├── datasets/
│   ├── index.md
│   └── orders_db.md
├── tables/
│   ├── index.md
│   ├── orders.md
│   └── customers.md
└── metrics/
    ├── index.md
    └── weekly_active_users.md
```

**ドキュメント例（v0.2）：**

```yaml
---
type: BigQuery Table
title: Orders
description: One row per completed customer order.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, revenue]
sources:
  - resource: https://docs.acme.internal/sales/orders-schema
    author: human:jane
generated:
  by: agent:enrichment-pipeline
  at: 2026-05-28T14:30:00Z
verified:
  - by: human:jane
    at: 2026-06-01T09:00:00Z
status: stable
stale_after: 2026-12-31
---
# Schema
| Column        | Type      | Description                               |
|---------------|-----------|--------------------------------------------|
| `order_id`    | STRING    | Globally unique order identifier.          |
| `customer_id` | STRING    | FK to [customers](/tables/customers.md).   |

# Joins
Joined with [customers](/tables/customers.md) on `customer_id`.
```

必須フィールド：`type` のみ。推奨フィールド：`title`, `description`, `resource`, `tags`, `sources`, `generated`, `verified`, `status`, `stale_after`

- コンセプト間は通常のMarkdownリンクで結合し、ディレクトリの親子関係より豊かな**グラフ構造**を形成
- オプションで `index.md`（段階的開示用）と `log.md`（変更履歴用）をサポート
- 仕様自体（適合基準、クロスリンク規則、予約ファイル名）は1ページに収まるコンパクトさ
- **適合性の原則**：コンシューマーは未知の`type`値、欠落したオプションフィールド、壊れたリンクがあってもバンドル全体を拒否してはならない（MUST NOT reject）

## v0.2での変更点（v0.1から）

v0.2のキャッチフレーズ：**「v0.2 puts queryable signals in frontmatter」**

### 破壊的変更

1. `timestamp` フィールド → `generated.at` に置き換え（旧`timestamp`へのフォールバックは許容）
2. 本文中の `# Citations` 見出しのリスト → `sources` フロントマターに置き換え

### 追加されたフィールド・概念

- **`sources`**（出典）：概念の派生元資料。`resource`（必須）、`id`、`title`に加え、信頼性を推測するための客観的信号として`author`、`usage_count`、`last_modified`を保持可能。**OKFはスコアを保存せず信号のみを記録**し、信頼度自体の判断はコンシューマー側に委ねる設計
- **`generated`**（生成情報）：コンテンツの作成者・生成日時。`by`（アクター、必須）、`at`（最終更新日時）
- **`verified`**（検証情報）：誰が/何が内容を出典や対象と照合して確認したかの履歴。複数の検証イベントを記録可能（例：人間の承認＋夜間バッチ処理による確認を同時記録）。単一検証者の場合は配列でなくマッピング1つでも可
- **`status`**（ライフサイクル）：`draft`（未レビュー）／`stable`（デフォルト、利用可能）／`deprecated`（廃止済みだがリンク保持のため残存）の3値
- **`stale_after`**（鮮度）：`YYYY-MM-DD`形式の絶対日付で陳腐化のタイミングを指定。相対TTLではなく絶対日付とすることで、読み取り時点に依存しない単純な日付比較が可能
- **新しい概念タイプ `Attested Computation`**（計算の証明）：関連フィールドとして`runtime`, `parameters`, `computation`, `executor`, `attester`
- 新しい規約的見出し `# Computation`
- アクター表記の規約（`generated.by`、`verified[].by`で使う`human:xxx` / `agent:xxx`等の記法）

### 信頼性（Trust）の仕組み

`verified`フィールドの内容から3段階の **Trust Tier** が導出される。

| Trust Tier | 条件 |
|---|---|
| `unverified` | `verified`キーが存在しない |
| `machine-confirmed` | 非human（`agent:`等）のアクターのみによる検証 |
| `human-reviewed` | human:アクターによる検証が含まれる |

これらは**"advisory signals, not access control"**（助言的な信号であり、アクセス制御ではない）とされ、Tierが低い概念でも拒否されることはない。

### 鮮度（Freshness）の仕組み

`stale_after`（陳腐化の閾値日付）と `generated.at`（コンテンツの最終変更日時）の組み合わせで判断する。両者は独立した概念であり、**「コンテンツは再確認なしに変更されることもあり、事実は再生成なしに再確認されることもある」**という関係。

### Attested Computationについて

「provenance（出典）はその主張がどこから来たかに答え、attestation（証明）はその数値が言った通りの方法で生成されたかに答える」という区別が明示されている。計算そのものを独立した概念として扱い、`executor`（実行方法）と`attester`（決定論的な検証コード、LLMは使用しない）によって、実行された計算が正しいかを機械的に検証できる。

## メリット

- **markdownのみ** — 任意のエディタで読める、GitHubでレンダリング可能、既存の検索ツールでインデックス可能
- **ファイルのみ** — tarball配布、gitリポジトリでホスト、ファイルシステムへのマウントが可能
- **YAMLフロントマターのみ** — 構造化フィールドをクエリ可能
- 複雑な圧縮方式・新規ランタイム・必須SDKが**不要**
- コードと一緒にバージョン管理できる
- 人間にも読みやすく、エージェントにも解析可能（翻訳レイヤー不要）

## リリース内容（参考実装）

1. **エンリッチメントエージェント**：BigQueryデータセットを走査し各テーブル/ビューのOKFコンセプトドラフトを作成。第2段階のLLMパスで公式ドキュメントをクロールし引用・スキーマ・結合パスを追加
2. **静的HTML可視化ツール**：OKFバンドルをインタラクティブなグラフビューに変換する自己完結型ファイル（バックエンド不要、データ非送信）
3. **3つのサンプルバンドル**：GA4 eコマース、Stack Overflow、Bitcoin公開データセット

## 関連組織・パートナー

- 公開元：Google Cloud Data Cloudチーム
- 統合先：Google Cloudの [Knowledge Catalog](https://cloud.google.com/blog/products/data-analytics/introducing-the-google-cloud-knowledge-catalog) がOKFを取り込み、エージェント向けに提供
- GitHub：[GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) にリポジトリ・仕様書・サンプルバンドルを公開
- Google製品を超えた**採用・コントリビューション・代替実装**を明示的に歓迎

## ユースケース

- テーブルスキーマの説明
- ビジネスメトリクスの定義（例：週間アクティブユーザーの計算方法）
- インシデント対応ランブック
- システム間の結合パス文書化
- 古いAPIの非推奨通知

## 今後の展望

- **OKFは出発点であり、完成した標準ではない**（v0.1→v0.2で早くも破壊的変更を含む改訂が行われている）
- より多くのプロデューサー・コンシューマーが登場し、エージェントが実際に必要とする知識表現を集団的に学ぶ中で仕様は進化予定
- 推奨アクション：
  - 仕様書を読む
  - 自分のソースシステム用のプロデューサーを書く
  - コンシューマー（ビューア、検索インデックス、推論エージェント）を書く
  - 自分のデータで参考実装を試す
  - Issue登録・PR送信・拡張提案（バージョン管理され後方互換性のある成長を前提に設計）
