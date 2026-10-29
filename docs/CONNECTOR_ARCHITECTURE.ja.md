# ADR-0002 — 公式API自動取込・BYO認証・Agent連携の設計

**決定:** 2026-10-29 JST  
**状態:** 次期製品の要求仕様（PLAN_ONLY / NOT_IMPLEMENTED）  
**基準:** [ADR-0001: 商店所有・ローカルファースト](PRODUCT_STRATEGY.ja.md)  
**対象:** EC管理画面 → 商品情報取得 → MisePort標準カタログ → 店舗所有の公開先

## 目的・ユーザー体験

商品CSVの手動アップロードは**必須ではなくフォールバック**とする。商店主は日本語UIでショップを選び、自分の権限で接続して、初回の商品読込と更新を実行できる。ショップ運営者がMisePort用のPython、Git、Docker、APIコードを書く必要はない。

「独自のAIエージェントを設定済み」「プラットフォームのAPIキーを自分で発行できる」店舗にも対応するが、**LLM/API課金もAgentの導入もMisePortの利用条件にしない**。標準APIが使えるならLLMを介さず決定論的に取得する。

## 3つの取込経路

| モード | 商店が行うこと | 実行者・安全境界 | 優先度 |
|---|---|---|---|
| **A. 公式API（優先）** | ショップを選び、公式OAuthで承認／必要なら読み取り専用トークンを自分の実行環境に登録 | MisePortの読み取り専用Adapter。秘密情報はローカル補助アプリまたは店舗管理のサーバーで保持。公開デモには送らない | P1 |
| **B. BYO Agent（任意）** | 自分のAgentと認可済み公式接続先を設定し、商品データをMisePortの標準Schemaで出力 | Agentはプラットフォーム規約を守る公式API/正規ツールのみ。商品説明内の命令は無視し、ソースと更新日時を記録 | P2 |
| **C. CSV/JSON（予備）** | 各ECの公式エクスポートファイルをドラッグ＆ドロップする | 既存のdeterministic importerと将来のブラウザUI | P1 |

APIとAgentを混同しない。プラットフォームによってOAuth・PAT・アプリ審査・有料プランが必要。**すべての店舗でAPIを使えるとは保証しない**。API連携不可でも公式CSVから利用可能な経路を維持する。

## 最重要: 認証・運用とlocal-firstの両立

静的な公開Webページに商店の長期トークンを貼り付けさせ、そのブラウザから管理APIを直接呼び出す設計は**既定にしない**。CORSに加え、秘密情報漏えい・権限・更新時処理の問題がある。

1. **OAuth対応:** 公式認可画面へ遷移→商店がスコープを確認して承認→必要なバックエンドでトークンを交換・管理。導入元の審査・アプリ登録が必要なら事前に案内する。書き込み権限を要求しない。
2. **PAT/APIキー対応:** プラットフォームが許す最小の**商品読み取り**スコープで発行。秘密の入力欄は商店所有のローカル補助アプリ／セルフホスト側だけに設置する。MisePort公式デモのフォーム、GitHub Issue、動画、ログ、静的バンドルに送らない・記録しない。
3. **無人同期:** ローカル端末がオフなら停止する。常時同期が必要な店には**任意の商店所有ランナー**を提供し、クラウドアカウントの契約・無料枠・秘密保存を明示する。「サーバー不要で24時間同期」を約束しない。
4. **接続解除:** トークン消去、連携先での失効手順、次回同期停止、生成済み公開データの削除・更新を別々に案内する。
5. **セキュリティ検証:** HTTPS、ホスト固定、リダイレクト検証、OAuth state/PKCE（適用可能なフロー）、トークン秘匿、エラー時の非表示、レート制限、秘密のログ除外、疑似資格情報でのテストを必須にする。公式実装で要求される認可モデルに従う。

**BYO Agent ≠ 管理者権限の丸投げ。** Agentが独自の秘密情報を持つ場合、そのAgentの環境で保管する。MisePortに渡すのは最小限の商品情報＋由来。CAPTCHA回避、規約違反の画面スクレイピング、ログイン資格情報の共有を正規経路として提供しない。

## ショップデータ → Canonical Catalog

```text
[EC Platform OAuth / PAT]      [BYO Agent official tools]      [Official platform CSV]
             │                         │                             │
             └─────────────── Source Adapters ───────────────────────┘
                                       │
                     pagination / variant / status / timestamp
                                       ▼
                   Validation + Import Summary + Source Evidence
                                       ▼
                       versioned MisePort Catalog (1.1 baseline)
                                       │
                          merchant review / publish allowlist
                                       ▼
                       portable export / static feed / MCP
```

Adapterインターフェース（提案。現行コードの既存APIではない）:

```text
SourceAdapter:
  platform_id / api_version / auth_kind / supported_scopes
  connect(auth_reference) -> connection_status
  fetch_products(cursor?, changed_since?) -> Page<SourceRecord>
  normalize(record) -> MappedProduct + MappingWarnings
  disconnect() -> revoked_or_removed_status

ExportAdapter:
  target_format / format_version / source_links
  validate(catalog) -> warnings + blocking_errors
  render(catalog, options) -> files + manifest + checksums
```

- 商品とバリエーションは安定識別子(`platform`, `shop`, `product_id`, `variant_id`など)で区別。数量や価格が商品単位かSKU単位かを失わない。
- 価格はJPY整数、税区分と送料の条件は独立した意味を持つ。不明を0にしない。非公開・下書き・個人向け商品は**既定で公開対象から除外**し、確認画面で明示する。APIが非公開商品を返すことがあるため必須。
- `source_url` / `evidence_url` / `updated_at` / `snapshot_at`と、読込時刻・変換バージョン・認可対象店舗を記録し、公開前に根拠を確認する。
- 既存の`miseport/1.1`への変換は検証を通す。多拠点在庫・複数通貨・複数SKUなど表現できない情報は警告として残し、必要なら**バージョンアップ**を提案する。黙ったフィールド追加や値の切り捨ては不可。

## 同期動作と品質

**初期目標:** 初回「接続→テスト→全件取得」、次回「今すぐ再取得」。差分同期・定期同期・Webhookは**プラットフォームの正式サポート確認後**に追加。各ショップのレート制限・API更新に対応し、失効時は再承認を案内する。

- 発行済みの公開カタログを更新する前に、差分（追加/更新/非公開/削除/取得失敗）を表示。
- API取得が途中で失敗したときは古い公開版を勝手に上書きしない。完全性が確認できたスナップショットに切り替え、最終成功時刻を表示。
- 削除・非公開の伝播、古い情報のTTL、更新日時、明示的な「公開停止」ボタンを設計に含める。
- 注文・個人情報・顧客・売上データのスコープは要求しない。売上分析や決済は製品の基本構成外。
- 監査ログは秘密情報・個人情報を除外し、商品IDのハッシュや要約を使って再現可能にする。

## 出力互換性: 4つの区別

1. **APIから読み取る（Read API）** — ショップ→MisePort。読み取り権限のみ。
2. **公式CSVを取り込む（Import CSV）** — ショップのエクスポート書式→MisePort。自動列対応の精度をテスト。
3. **プラットフォーム別CSVを生成する（Export CSV）** — MisePort→対象プラットフォームの**所定のCSV書式**。SKU/バリエーション/画像/カテゴリ/公開状態等を含む変換の完全性を確認。対応済みを名乗るのは、サンプル・往復テスト・実機による試験を通過してから。
4. **プラットフォームへ書き戻す（Write API / CSV upload）** — 商品更新を伴う**別の高リスク機能**。今は対象外。将来は明示的な書込認可・全変更差分・バックアップ・ユーザー承認・ロールバックを必要とする。

中心となる成果物は標準JSON、JSON-LD、読取専用MCP/REST。**プラットフォームCSV出力は追加アダプター**として扱い、完全互換を簡単に約束しない（例: ShopifyのCSV更新にはVariant/Handle依存項目がある）。必要ならGoogle Merchant Center等の公開仕様フィードに別アダプターを提供するが、現在の対応を主張しない。

## 完成判定

- 初回導入: 技術非専門者が日本語画面から公式の読取権限を設定し、1ショップの公開商品を取得できる。実地ユーザーテストで所要時間を記録。
- API最小権限: 読取専用・秘密がソース/静的JS/ログ/公開ZIPに含まれない。
- 精度: 公式バックエンドとSKU/バリエーション/価格/在庫/公開状態を照合し、欠落を警告、未確認を未知として残す。
- 更新: 再同期に重複や非公開漏出がなく、部分失敗で既存公開データを破壊しない。
- 互換: プラットフォームCSV往復または実機受入、文字コード・列名・画像URL・行数・ID維持を評価。
- サポート: **画面ごとの日本語手順書、よくある質問、エラー復旧、認証失効・解除、動画デモ**が対応機能と同時に公開される。
- **現行**: 2026-10-29時点でAPI自動取込・一般商店向けノーコード接続・プラットフォームネイティブCSV出力は**未実装**。公開デモは架空商品の読取に限定。

参照: [プラットフォーム互換性](PLATFORM_COMPATIBILITY.ja.md) / [商店主の操作手順](merchant/SETUP_GUIDE.ja.md) / [画面操作手順](merchant/VISUAL_GUIDE.ja.md) / [商品契約](CATALOG.md) / [Muse統合の実測](MUSE_INTEGRATION.md)。
