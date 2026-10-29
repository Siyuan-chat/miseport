# MisePort — 日本のEC商品カタログをAIエージェントにつなぐオープンソースMCP

<img src="assets/original/miseport-logo.png" width="260" alt="MisePort（ミセポート）：小さなお店と港の入り口を表すブランドロゴ">

**日本の小さなお店を、AIエージェントへ。**

**日本語（このページ）** · [English](README.en.md) · [公開デモ](https://miseport.pages.dev/) · [MCP接続ガイド](https://miseport.pages.dev/docs/?lang=ja) · [Muse接続方法と検索の仕組み](docs/MUSE_CONNECT.ja.md) · [Agent GEO](docs/AGENT_GEO.ja.md) · [GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)

[![CI](https://github.com/Siyuan-chat/miseport/actions/workflows/ci.yml/badge.svg)](https://github.com/Siyuan-chat/miseport/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-0B2F54)

**MisePort（ミセポート）** は、日本のネットショップ・EC事業者の商品情報を、AIアシスタントやAIエージェントが**出典付きで検索・確認できる形**に整えるオープンソースの開発ツールです。CSV / JSON の商品データを検証し、在庫・価格・送料・更新日時を保持した商品カタログとして、[Model Context Protocol（MCP）](https://modelcontextprotocol.io/) と読み取り専用 API から利用できます。

生成AI検索最適化（**GEO**）やAI時代のEC（**Agentic Commerce／エージェンティックコマース**）に向けた**商品データ基盤**を目指しています。ただし、現行版は商品データの整理と公開実験が中心であり、AIからの推薦順位・検索流入の改善を保証するものではありません。

## まず試す：日本語の商品検索とMCP

| 入口 | できること | 利用条件 |
| --- | --- | --- |
| [ブラウザの公開デモ](https://miseport.pages.dev/) | 架空の商品を日本語で検索し、出典・価格・在庫の記録を確認 | ログイン不要 |
| [MCP接続ガイド](https://miseport.pages.dev/docs/?lang=ja) | 外部MCPクライアントにテスト用の商品ツールを接続 | クライアント側の対応が必要 |
| [REST API / OpenAPI](https://miseport.pages.dev/openapi.json) | 開発用に検索・詳細・参考見積もりなどを呼び出す | 読み取り専用 |
| [ローカルPython版](#ローカルで動かす開発者向け) | 自分で権利を持つCSV/JSONを取り込み、検証・公開用データを準備 | Python 3.10以上 |

**公開デモのデータはすべて架空です。** デモの価格・在庫は過去時点のスナップショットであり、実際の販売、決済、注文、在庫確保には対応していません。公開MCPは `https://miseport.pages.dev/mcp` です。

### 開発中の商店向けAlpha（2026-10-29）

GitHubのソースには **BASE v2 βの読み取り専用商品取込、日語ローカルGUI、商店別MCP/REST配信ZIP生成** のAlphaコードが含まれます。開発環境では `miseport-gui`（GUI）と `miseport-publish`（配信ZIP生成）を試せます。BASEの公式商品ページ規則に基づき、店主が確認した**1件の公開商品URLから同一店舗の候補URLを一括生成**する試作も進めていますが、全件のHTTP検証はまだです。公開商品の更新は店主のレビューを通し、削除差分を確認してから保存します。

**実店舗のBASE API接続、Windows GUI実機の店主受入、商店自身のCloudflare公開、Muse自然検索での発見、11/10正式Releaseはいずれも未検証です。** Alpha実装があることと一般商店向け正式対応は区別してください。[Alpha操作ガイド](docs/merchant/GUI_ALPHA_GUIDE.ja.md)。

## MisePortが解決したいこと

日本の小規模ECでは、商品説明・価格・在庫・送料・税区分などがショップごとに異なる形式で管理されがちです。AIエージェントが商品を比較するには、検索可能な商品名だけでなく、**事実の出典・更新時刻・不明な項目**を区別できることが重要です。

- **商品データを整える：** CSV / JSONを取り込み、SKU・価格・在庫・送料・根拠URLなどを検証
- **AIから安全に読む：** MCPの7つの読み取り専用ツールで商品検索、詳細、在庫スナップショット、参考見積もりなどを提供
- **推測で埋めない：** 送料・税・在庫が未確認なら `null` や `unknown` のまま返す
- **オープンに検証する：** API仕様、Pythonテスト、Cloudflareデモ、Muse接続の検証記録を公開

```text
ECショップの商品CSV / JSON
          ↓
データ検証・出典／更新日時の保持
          ↓
       MisePort
          ├─ CLI（検索・監査・JSON-LD）
          ├─ MCP（7つの読み取り専用ツール）
          └─ REST / OpenAPI（公開の架空デモ）
                         ↓
              対応するAIエージェント
```

## ローカルで動かす（開発者向け）

リポジトリをクローンし、ルートディレクトリで実行してください。開発用依存パッケージのインストールにはネットワーク接続が必要です。

```bash
git clone https://github.com/Siyuan-chat/miseport.git
cd miseport
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

miseport validate examples/products.json
miseport import examples/products.csv --output catalog.json
miseport search コーヒー --catalog examples/products.json
miseport detail coffee-001 --catalog examples/products.json
miseport inventory coffee-001 --catalog examples/products.json
miseport quote coffee-001 --quantity 2 --catalog examples/products.json
miseport audit --catalog examples/products.json
miseport export-jsonld coffee-001 --catalog examples/products.json
```

ローカル検索は全角・半角やかなの正規化に対応した**部分一致**です。意味検索やベクトル検索ではありません。最大10 MiB・10,000商品のカタログを扱い、MCPは起動時点のスナップショットを利用します。詳しくは[API仕様](docs/API.md)・[データ形式](docs/CATALOG.md)を参照してください。

## AIエージェント／MCPクライアントに接続する

ローカル版の`miseport-mcp`はstdio通信に対応しています。クライアントの設定に合わせ、`MISEPORT_CATALOG`に**検証済みカタログの絶対パス**を設定します。

```json
{
  "mcpServers": {
    "miseport": {
      "command": "miseport-mcp",
      "env": {
        "MISEPORT_CATALOG": "/absolute/path/to/examples/products.json"
      }
    }
  }
}
```

公開デモは **Streamable HTTP MCP**（`https://miseport.pages.dev/mcp`）を利用します。ローカルstdio版とは別の実装です。MCP以外の利用向けに[OpenAPI](https://miseport.pages.dev/openapi.json)も公開しています。

| MCPツール | 用途 |
| --- | --- |
| `about_miseport` | サービスの目的・範囲を説明 |
| `search_products` | キーワード・条件による商品検索 |
| `get_product` | SKU指定で商品情報・出典・更新日時を取得 |
| `check_inventory` | 記録された在庫状態・数量を照会（リアルタイム保証なし） |
| `get_quote` | 個数を指定した拘束力のない参考見積もり |
| `audit_catalog` | 商品データの欠落項目などを監査 |
| `export_product_jsonld` | Schema.org Product / OfferのJSON-LDを出力 |

### Meta Museから使えますか？

2026年10月29日、**Museのアカウント内カスタムコネクタ**から、公開デモを利用した7回のMCPツール呼び出しを検証しました（[実測記録](docs/MUSE_INTEGRATION.md)）。これは**個別アカウント内での動作検証**であり、Metaの公式ディレクトリ掲載、全ユーザーへの配布、商用ECでの利用許可を意味しません。

Museを含むクライアントでは、[接続ガイド](https://miseport.pages.dev/docs/?lang=ja)を確認し、対応する接続方法・ツール名・入力項目を実際に確認してからテストしてください。デモに個人情報・APIキー・実際の顧客データを送信しないでください。

## 商店が自分で使えるツールへ（新しい製品方針）

MisePortは**商店所有・ローカルファースト・無料優先**のオープンソースとして発展させます。将来の商店向け画面では、**公式APIを商店主自身が認可して商品を自動取得**し、商品情報を確認して、標準データや公開用パッケージを生成することを主導線とします。自分で設定したAgentによる読込にも将来対応し、APIが使えない店舗にはCSVを残します。商店の商品をMisePort運営側で集中収集するマーケットプレイスは作りません。外部サービスとの互換性は、バージョン付き商品スキーマと入出力アダプターで確保します。

**これは次の開発段階の設計です。現行版にネイティブAPI自動読込、ブラウザでの商店CSV取込・商店別ワンクリック公開はありません。** APIキーは公開デモに入力せず、店舗所有の安全な環境で管理します。 [製品方針（ADR-0001）](docs/PRODUCT_STRATEGY.ja.md) · [自動接続とBYO認証設計（ADR-0002）](docs/CONNECTOR_ARCHITECTURE.ja.md) · [対応プラットフォーム](docs/PLATFORM_COMPATIBILITY.ja.md) · [商店主向け日本語手順書](docs/merchant/SETUP_GUIDE.ja.md) · [動画デモ制作計画](docs/merchant/VIDEO_DEMO_PLAN.ja.md)。

**11/10商店実用版の必須目標:** BASE公式APIを使った公開商品自動取得、日本語の非技術者向けGUI、商店別のMCP/REST公開パッケージと実画面手順書／動画を提供し、**少なくとも1店の営業中の日本EC商店から公開許諾を得た実商品デモ**を発表することを目指します。これは**開発中の目標**であり、現在の公開デモは引き続き架空商品だけです。 [11/10受入基準](docs/RELEASE_2026-11-10.ja.md) · [実商店Pilot](docs/merchant/PILOT_2026-11-10.ja.md) · [内部開発計画（中国語）](docs/DEVELOPMENT_PLAN.zh-CN.md) · [Issue #9](https://github.com/Siyuan-chat/miseport/issues/9)。

### Museの「接続」と一般の商品検索は別

MisePortの公開架空デモは**1つのMuseアカウント内のCustom Connector**で7回のツール呼び出しを実測していますが、Meta公認Directoryへの申請・掲載、未接続の一般ユーザーによる自然検索での表示や推薦は未検証です。[Muse接続と発見の仕組み](docs/MUSE_CONNECT.ja.md) · [個人AIエージェント向けGEO](docs/AGENT_GEO.ja.md)。

## 現在の対応範囲と今後の方向

| 項目 | 2026-10-29時点 |
| --- | --- |
| 商品CSV / JSONの取り込み・検証 | 実装済み |
| 日本語の商品検索、在庫記録、参考見積もり、JSON-LD | 実装済み |
| ローカルMCP（stdio） | 実装済み・テストあり |
| 公開MCP / RESTの架空デモ | 公開・検証記録あり |
| Museアカウント内の接続テスト | 実測記録あり |
| BASE・makeshop・EC-CUBE・Shopifyへの**ネイティブAPI同期** | 未実装 |
| 実店舗の在庫同期・OAuth・複数店舗の権限分離 | 未実装 |
| AgentごとのGEO順位計測、成果保証 | 未実装 |
| 決済・注文・キャンセル・返金 | 未実装 |

開発優先順位と品質基準は[ロードマップ](docs/ROADMAP.md)・[最新のプロジェクト状態](PROJECT_STATUS.md)にまとめています。ショップの実データを接続する前に、権限・出典・プライバシー・運用上の確認が必要です。

## よくある質問（FAQ）

**MisePortは無料ですか？**  
はい。コードは[Apache-2.0](LICENSE)ライセンスで公開しています。Cloudflareなど外部サービスの利用には別途条件・費用が発生する場合があります。

**GEO対策ツールですか？**  
AI検索に読み取らせるための商品情報の整理・出典管理・構造化データ出力を支える基盤です。現行版にSEO順位改善、AIからの推薦獲得、露出量測定の機能はありません。

**BASEやmakeshopなどの日本のECショップで使えますか？**  
利用許可のあるCSV / JSONを準備できればローカルで試せます。ただし、BASE・makeshop・EC-CUBEなどへのログイン、OAuth接続、商品APIの自動同期はまだありません。

**Museから商品購入までできますか？**  
いいえ。現在のMisePortは読み取り専用です。公開デモの商品も架空で、注文・決済はできません。Museの公式承認も未取得です。

**価格や送料が表示されない場合は？**  
未確認の項目を0円や「在庫あり」に置き換えません。データに含まれる出典・更新日時を確認してください。

## ドキュメント・開発参加

[API仕様](docs/API.md) · [データ形式](docs/CATALOG.md) · [Muse実測記録](docs/MUSE_INTEGRATION.md) · [Cloudflareデモ](docs/CLOUDFLARE.md) · [ブランドガイド](docs/BRAND.md) · [セキュリティ](SECURITY.md) · [貢献ガイド](CONTRIBUTING.md) · [商店向けAgent GEO](docs/AGENT_GEO.ja.md)

バグ報告・機能提案は[GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)へ。秘密情報や顧客情報は公開Issueに書き込まないでください。

MisePortはMeta Muse、Shopify、BASE、makeshopなどの公式製品・提携サービスではありません。商標・プラットフォーム利用条件を尊重し、根拠のない検索順位・売上・対応機能の主張はしません。
