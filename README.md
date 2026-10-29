# MisePort — 日本のEC商品カタログをAIエージェントにつなぐオープンソースMCP

<img src="assets/original/miseport-logo.png" width="260" alt="MisePort（ミセポート）のロゴ">

**日本の小さなお店を、AIエージェントへ。**

**日本語** · [English](README.en.md) · [公開デモ](https://miseport.pages.dev/) · [MCP接続ガイド](https://miseport.pages.dev/docs/?lang=ja) · [商店向けガイド（Alpha）](docs/merchant/GUI_ALPHA_GUIDE.ja.md) · [GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)

[![CI](https://github.com/Siyuan-chat/miseport/actions/workflows/ci.yml/badge.svg)](https://github.com/Siyuan-chat/miseport/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-0B2F54)

**MisePort（ミセポート）** は、日本のネットショップの商品情報を、AIエージェントが検索・参照しやすいカタログに整えるオープンソースツールです。

商品データ（CSV / JSON）を検証・正規化し、[Model Context Protocol（MCP）](https://modelcontextprotocol.io/)、CLI、REST API、Schema.org JSON-LDを通じて利用できます。ショップ自身がデータを管理しながら、AIによる商品発見（Agentic Discovery / GEO）に対応するための仕組みを提供します。

## まず試す

| 入口 | 内容 |
| --- | --- |
| [ブラウザ公開デモ](https://miseport.pages.dev/) | サンプル商品を日本語で検索し、価格・在庫記録・出典URLを確認 |
| [MCP接続ガイド](https://miseport.pages.dev/docs/?lang=ja) | 公開デモのMCPエンドポイント（`https://miseport.pages.dev/mcp`）をクライアントに接続 |
| [REST API / OpenAPI](https://miseport.pages.dev/openapi.json) | 商品検索・詳細取得・参考見積もりのAPIを試す |
| [ローカル実行（CLI / MCP）](#ローカルで動かす) | 自分のCSV / JSONを使って検証・検索し、MCPサーバーを起動 |

## 設計の考え方

商品名の表記、税込・税抜価格、在庫状態、送料の扱いはショップによってさまざまです。MisePortは、AIエージェントが商品を比較・紹介するための情報を、**出典・記録日時・未確認項目**とともに整理します。

- **出典と日時を残す：** 商品ページの`source_url`と`updated_at`を保持し、情報の参照元を辿れるようにします。
- **不明な項目を推測で埋めない：** 送料・税区分・在庫数が未確認なら、`null`や`unknown`のまま扱います。
- **日本語の商品を探しやすくする：** 全角・半角、カタカナ・ひらがなを正規化して検索できます。
- **読み取り専用（Read-Only by Design）：** 商品検索・詳細確認・参考見積もりに特化。購入手続きは元のショップの商品ページで行います。
- **ショップ主体のデータ管理：** 各ショップが自分の環境で商品情報を管理・公開する、ローカルファーストの設計です。

### カタログデータの例

[サンプルカタログ](examples/products.json)に含まれる架空の商品の例です。送料が不明な場合は`null`、在庫を確認できない場合は`unknown`として表します。

```json
[
  {
    "sku": "tea-002",
    "name": "宇治 抹茶 30g",
    "price_jpy": 2200,
    "stock": "unknown",
    "tax_included": null,
    "shipping_jpy": null,
    "source_url": "https://example.com/products/tea-002",
    "updated_at": "2026-10-28T12:00:00+09:00",
    "is_demo": true
  }
]
```

```text
ショップの商品CSV / JSON ──┐
BASE API・公式CSV（Alpha） ─┤
                           ▼
                 検証・正規化
                出典・日時の保持
                           ▼
                        MisePort
                 ├─ CLI（検索・監査・変換）
                 ├─ MCP（7つの読み取り専用ツール）
                 ├─ REST API / OpenAPI
                 └─ Schema.org JSON-LD
                           ▼
                AIエージェント／アプリ
```

データ形式の詳細は[カタログ仕様](docs/CATALOG.md)をご覧ください。

## ローカルで動かす

Python 3.10以上の環境で利用できます。リポジトリをクローンし、ルートディレクトリで実行してください。

```bash
git clone https://github.com/Siyuan-chat/miseport.git
cd miseport
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

# 商品データの検証・検索・詳細表示
miseport validate examples/products.json
miseport search 抹茶 --catalog examples/products.json
miseport detail tea-002 --catalog examples/products.json
miseport inventory tea-002 --catalog examples/products.json

# CSV取込・参考見積もり・監査・JSON-LD出力
miseport import examples/products.csv --output catalog.json
miseport quote tea-002 --quantity 2 --catalog examples/products.json
miseport audit --catalog examples/products.json
miseport export-jsonld tea-002 --catalog examples/products.json
```

検索は表記揺れを正規化した部分一致方式です。カタログは最大10 MiB・10,000商品まで扱えます。詳しくは[CLI / API仕様](docs/API.md)を参照してください。

## AIエージェント／MCPクライアントに接続する

ローカルの`miseport-mcp`はstdio通信に対応しています。MCPクライアントの設定ファイルで、カタログの絶対パスを指定します。

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

リモート接続には公開デモの[Streamable HTTP MCP](https://miseport.pages.dev/mcp)も利用できます。

| MCPツール | 機能 |
| --- | --- |
| `about_miseport` | カタログの概要を返す |
| `search_products` | 商品名・キーワード・条件で検索する |
| `get_product` | SKUから商品詳細・出典URL・更新日時を取得する |
| `check_inventory` | 記録されている在庫状態・数量を確認する |
| `get_quote` | 数量を指定して参考金額を試算する（税・送料が未確定なら総額は`null`） |
| `audit_catalog` | 欠落項目やデータの整合性をチェックする |
| `export_product_jsonld` | Schema.org `Product` / `Offer`のJSON-LDを生成する |

Claude DesktopなどのMCP対応クライアントから利用できます。Meta MuseでもCustom Connector経由の接続例があります。詳しくは[Muse接続ガイド](docs/MUSE_CONNECT.ja.md)と[Agent GEOの考え方](docs/AGENT_GEO.ja.md)をご覧ください。

## 商店向けツール（Experimental / Alpha）

コマンドラインに慣れていないショップオーナー向けに、商品データの取り込みから確認、公開用パッケージの生成までを日本語で操作できるツールを開発しています。

- **日本語ローカルGUI（`miseport-gui`）：** 商品の取り込み、更新差分のレビュー、公開前のチェック
- **ECプラットフォーム連携（Alpha）：** BASE v2 β APIからの商品読み込み、BASE / Shopifyの商品CSV取込、公開商品URLの確認補助
- **配信パッケージ生成（`miseport-publish`）：** ショップ自身のCloudflare Pagesなどに公開できる、読み取り専用MCP / REST配信用ZIPの出力

現在は実店舗でのパイロット導入に向けて検証を進めています。操作方法や今後の開発については、[商店向けAlphaガイド](docs/merchant/GUI_ALPHA_GUIDE.ja.md)、[対応プラットフォーム](docs/PLATFORM_COMPATIBILITY.ja.md)、[ロードマップ](docs/ROADMAP.md)をご覧ください。

## よくある質問（FAQ）

**Q. 無料で使えますか？**  
はい。MisePortは[Apache-2.0](LICENSE)ライセンスのオープンソースです。外部ホスティングサービスの費用は利用環境によって異なります。

**Q. BASEやShopifyの商品データを使えますか？**  
標準のCSV / JSONに加え、Alpha機能としてBASE（API / CSV）とShopify（CSV）の読み込みに対応しています。

**Q. AIエージェントから直接注文・決済できますか？**  
MisePortは商品情報の参照に特化したツールです。購入はショップの商品ページから行います。

## ドキュメント・開発参加

[API仕様](docs/API.md) · [データ形式](docs/CATALOG.md) · [Muse接続ガイド](docs/MUSE_CONNECT.ja.md) · [Agent GEO](docs/AGENT_GEO.ja.md) · [Cloudflareデモ](docs/CLOUDFLARE.md) · [製品方針](docs/PRODUCT_STRATEGY.ja.md) · [セキュリティ](SECURITY.md) · [貢献ガイド](CONTRIBUTING.md) · [ブランドガイド](docs/BRAND.md)

バグ報告や機能提案は[GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)へお寄せください。

*記載の会社名・サービス名は各社の商標または登録商標です。MisePortは独立したオープンソースプロジェクトであり、各プラットフォームの公式製品・提携サービスではありません。*
