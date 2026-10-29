# MisePort — 日本のEC商品カタログをAIエージェントにつなぐオープンソースMCP

<img src="assets/original/miseport-logo.png" width="260" alt="MisePort（ミセポート）のロゴ">

**日本の小さなお店を、AIエージェントへ。**

**日本語（このページ）** · [English](README.en.md) · [公開デモ](https://miseport.pages.dev/) · [MCP接続ガイド](https://miseport.pages.dev/docs/?lang=ja) · [商店向けAlphaガイド](docs/merchant/GUI_ALPHA_GUIDE.ja.md) · [実画面に基づく日本語手順](docs/merchant/VISUAL_GUIDE.ja.md) · [GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)

[![CI](https://github.com/Siyuan-chat/miseport/actions/workflows/ci.yml/badge.svg)](https://github.com/Siyuan-chat/miseport/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-0B2F54)

**MisePort（ミセポート）** は、日本の独立系ネットショップやEC事業者の商品情報を、AIエージェントが**出典URLと記録日時を確認しながら参照できる形**に整えるオープンソースツールです。

商品CSV / JSONを検証・正規化し、[Model Context Protocol（MCP）](https://modelcontextprotocol.io/)・CLI・読み取り専用REST API・Schema.org JSON-LDで活用できます。ショップが自分のデータを管理し、AIによる商品発見（Agentic Discovery）やGEO（生成AI検索最適化）の土台となる情報を、推測に頼らず提供することを目指しています。

## まず試す

| 入口 | できること | 必要なもの |
| --- | --- | --- |
| [ブラウザの公開デモ](https://miseport.pages.dev/) | 架空の商品を日本語で検索し、価格・在庫記録・出典を確認 | ログイン不要 |
| [MCP接続ガイド](https://miseport.pages.dev/docs/?lang=ja) | 公開デモのMCP（`https://miseport.pages.dev/mcp`）を対応クライアントから利用 | MCP対応クライアント |
| [REST API / OpenAPI](https://miseport.pages.dev/openapi.json) | 商品検索・詳細・参考見積もりなどをHTTPで呼び出す | HTTPクライアント |
| [ローカルPython版](#ローカルで動かす開発者向け) | 手元の商品CSV / JSONを検証し、検索・MCP・JSON-LD出力を試す | Python 3.10以上 |

> **公開デモは架空の商品データ専用です。** 価格・在庫は記録されたスナップショットであり、実際の販売・注文・決済・在庫確保には対応しません。デモにAPIキー、顧客情報などの秘密情報を送信しないでください。

## MisePortが大切にしていること

ネットショップごとに異なる商品名、価格の税込・税抜表示、在庫状態、送料条件。AIエージェントが商品を扱う際には、情報を検索できるだけでなく、**「どこから来た情報か」「いつの記録か」「何がまだ分からないか」**を区別できることが大切です。

- **出典を残す：** 商品ページの`source_url`と`updated_at`などを保持し、回答の根拠を確認できるようにします。
- **不明なことは不明のまま：** 税区分・送料・在庫数量が未確認なら、`0円`や「在庫あり」と補わず、`null`や`unknown`で表します。
- **読み取り専用でつなぐ（Read-Only by Design）：** 商品検索・詳細確認・参考見積もりに機能を限定し、注文、決済、ショップ側データへの書き戻しは行いません。購入は元のショップの商品ページで行います。
- **ショップの管理権を尊重する：** 中央集約型のマーケットプレイスではなく、商店自身が商品データを管理・確認して公開できる、ローカルファーストの仕組みを目指します。

### 商品データの例

以下は[サンプルカタログ](examples/products.json)に基づく、**架空の商品1件を収めた標準カタログJSON**です。`shipping_jpy: null`は「送料無料」ではなく「送料が不明」、`stock: "unknown"`は「在庫ありと確認できない」ことを意味します。

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

`updated_at`はカタログに記録された日時であり、外部の商品ページをリアルタイムで照合した証明ではありません。取得時点を別途保持する場合は`snapshot_at`を使用できます。データ形式の詳細は[カタログ仕様](docs/CATALOG.md)を参照してください。

```text
ショップの商品CSV / JSON ──┐
BASE API・公式CSV（Alpha） ─┤
                           ▼
               検証・正規化・出典の保持
                           ▼
                        MisePort
                 ├─ CLI（検索・監査）
                 ├─ MCP（7つの読み取り専用ツール）
                 ├─ REST / OpenAPI
                 └─ Schema.org JSON-LD
                           ▼
                対応するAIエージェント
```

## ローカルで動かす（開発者向け）

リポジトリをクローンし、ルートディレクトリで実行します。初回のパッケージインストールにはネットワーク接続が必要です。

```bash
git clone https://github.com/Siyuan-chat/miseport.git
cd miseport
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

# サンプル商品の検証・検索
miseport validate examples/products.json
miseport search 抹茶 --catalog examples/products.json
miseport detail tea-002 --catalog examples/products.json

# CSV取込・参考見積もり・監査・JSON-LD出力
miseport import examples/products.csv --output catalog.json
miseport quote tea-002 --quantity 2 --catalog examples/products.json
miseport audit --catalog examples/products.json
miseport export-jsonld tea-002 --catalog examples/products.json
```

検索は全角・半角、カタカナ・ひらがななどを正規化した**決定論的な部分一致検索**です。ベクトル検索や意味検索ではありません。カタログの上限は10 MiB・10,000商品で、ローカルMCPは起動時点に読み込んだスナップショットを参照します。詳しくは[CLI / MCP API仕様](docs/API.md)をご覧ください。

## AIエージェント／MCPクライアントに接続する

ローカル版の`miseport-mcp`は**stdio**に対応しています。MCPクライアントの設定に、検証済みカタログの**絶対パス**を指定してください。

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

リモート接続には公開デモの[Streamable HTTP MCP](https://miseport.pages.dev/mcp)を利用できます。こちらはローカルstdio版とは別の配信実装です。MCPを使わないアプリ向けには[OpenAPI](https://miseport.pages.dev/openapi.json)も用意しています。

| MCPツール | 用途 |
| --- | --- |
| `about_miseport` | カタログの提供範囲・デモ状態・制約を説明 |
| `search_products` | 商品名・キーワード・条件で検索 |
| `get_product` | SKUから商品情報、出典URL、記録日時を取得 |
| `check_inventory` | 記録された在庫状態・数量を確認 |
| `get_quote` | 数量を指定して拘束力のない参考金額を計算 |
| `audit_catalog` | 欠落項目やデータの整合性を確認 |
| `export_product_jsonld` | Schema.org `Product` / `Offer`のJSON-LDを出力 |

見積もりは購入可能性や送料込み総額を必ず確定するものではありません。税区分や送料が不明な場合、総額は`null`になります。また、JSON-LDの出力だけでショップの商品ページが自動更新されることはありません。

### Meta Museとの接続について

2026年10月29日、**個別のMeta Museアカウント内で作成したCustom Connector**から、MisePortの架空商品デモに対して**計7回のMCPツール呼び出し**を確認しました。

これは接続できることの個別検証です。**Metaの公式Connector Directoryへの掲載、一般ユーザーによる自動発見、自然検索からの推薦とは別**です。接続の仕組みと検証範囲は[Muse接続ガイド](docs/MUSE_CONNECT.ja.md)と[Agent GEOの考え方](docs/AGENT_GEO.ja.md)にまとめています。

## 商店向けAlphaとロードマップ

MisePortは開発者向けCLIに加え、**店主が日本語の画面で商品を読み込み、内容を確認し、自分で公開用データを作成できるツール**へと開発を進めています。

### 開発状況（2026年10月29日時点）

| 機能 | 状況 |
| --- | --- |
| CSV / JSONの検証・取込、検索、監査、JSON-LD出力 | 実装済み |
| ローカルMCP（stdio）・架空商品の公開MCP / RESTデモ | 実装済み・テストあり |
| 日本語対応のローカルGUI（`miseport-gui`） | **Alpha実装済み** |
| BASE v2 β APIの商品読込、BASE / Shopifyの商品CSV読込 | **読み取り専用Alpha実装済み** |
| 商店別MCP / REST配信ZIP生成（`miseport-publish`）と公開後の接続確認 | **Alpha実装済み** |
| 実店舗API接続・Windows実機での店主受入・許諾済み実商品デモ | **2026年11月10日の目標／未完了** |
| その他のECプラットフォームのネイティブAPI同期・無人自動更新 | 今後の検討対象 |

現在のAlphaには、BASEの公開商品URL候補生成、店主が明示的に指定した最大30件の公開HTTPSページの確認、データ更新時の削除差分レビューなども含まれます。BASE商品CSVはUTF-8 / CP932、Shopify商品CSVはUTF-8を想定しています。

これらは**ソースコード上のAlpha機能**であり、実店舗のAPI・CSV環境での受入や、非技術者によるWindows GUIの実機利用はまだ完了していません。生成したZIPは店主自身のCloudflare Pages等に**手動で公開**する方式で、ショップへの商品書き戻しは行いません。

**次のマイルストーン（2026年11月10日・目標）：** 日本のEC商店が、自分の商品を読み込み・確認し、自分の管理する公開先からAIエージェントへ提供できること。実商店の協力と別途の公開許諾が得られた場合には、実商品を用いたデモ公開も目指します。

詳しくは[商店向けAlpha操作ガイド](docs/merchant/GUI_ALPHA_GUIDE.ja.md) · [対応プラットフォーム](docs/PLATFORM_COMPATIBILITY.ja.md) · [製品方針](docs/PRODUCT_STRATEGY.ja.md) · [ロードマップ](docs/ROADMAP.md) · [Issue #9](https://github.com/Siyuan-chat/miseport/issues/9)をご覧ください。

## よくある質問（FAQ）

**Q. MisePortは無料で使えますか？**  
はい。ソースコードは[Apache-2.0](LICENSE)ライセンスで公開しています。Cloudflareなど外部サービスを利用する場合は、そのサービスの利用条件や料金が別途適用されます。

**Q. 導入すればAI検索（GEO）の推薦順位が上がりますか？**  
MisePortが提供するのは、出典付きの商品情報をAIから参照しやすくするための基盤です。検索順位、推薦、流入数や売上の改善を保証するものではありません。

**Q. BASEやShopifyの店舗でも使えますか？**  
標準CSV / JSONの検証に加え、BASE API・BASE商品CSV・Shopify商品CSVの読み取り専用Alphaを試せます。実店舗との互換性は引き続き検証中です。APIキーは公開デモではなく、店主が管理するローカル環境で扱ってください。

**Q. AIエージェントから注文・決済できますか？**  
いいえ。MisePortは商品情報の読み取りに限定しています。購入する際は元のショップの商品ページをご利用ください。

**Q. 送料や在庫数が空欄・不明になるのはなぜですか？**  
未確認の情報を確定値として表示しないためです。`null`は「0」、`unknown`は「在庫あり」を意味しません。判断に必要な場合は、記録日時と元の商品ページをご確認ください。

## ドキュメント・開発参加

[API仕様](docs/API.md) · [データ形式](docs/CATALOG.md) · [Muse接続と発見](docs/MUSE_CONNECT.ja.md) · [Agent GEO](docs/AGENT_GEO.ja.md) · [Cloudflareデモ](docs/CLOUDFLARE.md) · [セキュリティ](SECURITY.md) · [貢献ガイド](CONTRIBUTING.md) · [ブランドガイド](docs/BRAND.md)

不具合報告や機能提案は[GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)へ。秘密情報、APIキー、顧客データは公開Issueに記載しないでください。

*MisePortはMeta Muse、BASE、Shopify、makeshop等の公式製品・提携サービスではありません。各社の商標およびプラットフォーム利用条件を尊重し、根拠のない提携・推薦・対応状況の表示は行いません。*
