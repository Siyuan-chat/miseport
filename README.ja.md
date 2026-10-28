# MisePort

<img src="assets/original/miseport-logo.png" width="300" alt="MisePort">

**日本の小さなお店を、AIエージェントへ。**

[English](README.md)

日本のお店の商品情報を、AIから確認しやすいカタログへ。MisePortは商品データのインポート・検証と、stdio MCPによる読み取り専用の検索・詳細取得を行うローカル試作です。

**公開デモ：** [公式サイト](https://miseport.pages.dev/) · [接続ガイド](https://miseport.pages.dev/docs/?lang=ja) · [OpenAPI](https://miseport.pages.dev/openapi.json)。MCP接続先は `https://miseport.pages.dev/mcp`。2026-10-29に公開HTTP経由で7つの読み取り専用ツールを検証済みです。Museのアカウント内カスタム接続は2回のMCP検証を通過しました（[検証記録](docs/MUSE_INTEGRATION.md)）。公開ディレクトリへの掲載承認や実店舗向け本番運用を意味しません。商品・価格・在庫は架空の過去時点の記録です。ソースは[Siyuan-chat/miseport](https://github.com/Siyuan-chat/miseport)。[Cloudflare](docs/CLOUDFLARE.md) / [Python HTTP](docs/HTTP_SERVICE.md) の手順も参照してください。

## はじめに

Python 3.10以上を使用し、プロジェクトのディレクトリで実行します。

```sh
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# PowerShell: .venv/Scripts/Activate.ps1
pip install -e '.[dev]'
miseport validate examples/products.json
miseport import examples/products.csv --output catalog.json
miseport search コーヒー --catalog examples/products.json
miseport detail coffee-001 --catalog examples/products.json
miseport inventory coffee-001 --catalog examples/products.json
miseport quote coffee-001 --quantity 2 --catalog examples/products.json
miseport audit --catalog examples/products.json
miseport export-jsonld coffee-001 --catalog examples/products.json
```

上記はローカル利用の手順です。実際の成否は利用するチェックアウトでコマンドとテストを実行して確認してください。インストールには開発用依存パッケージの取得が必要です。

検索は全角・半角とかなを正規化した部分一致で、空白区切りの語はすべて一致する必要があります。意味検索ではありません。価格、SKUの順に並びます。絞り込みは`--category`、`--min-price-jpy`、`--max-price-jpy`、`--in-stock-only`、`--limit`（1〜100）、`--offset`。カタログ上限は10 MiB・1万件です。MCPは起動時のスナップショットを使うため、更新時は再起動してください。CLIエラーは標準エラー出力・終了コード2で通知します。

開発検証は`python -m pytest -q`と`python -m build`。[SDK選定](docs/SDK.md)、[ブランド仕様](docs/BRAND.md)、[最新検証状態](PROJECT_STATUS.md)も参照できます。SDKは保守版`mcp==1.28.0`に固定し、v2互換は未検証です。[Apache-2.0](LICENSE)ライセンスです。

## MCPクライアントへの接続

stdioに対応したクライアントから`miseport-mcp`を子プロセスとして起動します。環境変数`MISEPORT_CATALOG`に検証済みカタログの絶対パスを指定します。次の例を利用中のクライアントの設定形式に合わせてください。

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

Windowsでは`C:/catalog/products.json`のようなパスを使えます。インストール先の実行ファイルをクライアントから起動できることも確認してください。ツールは`about_miseport`、`search_products`、`get_product`、`check_inventory`、`get_quote`、`audit_catalog`、`export_product_jsonld`の7つです。[API仕様](docs/API.md)も参照してください。公開MCPエンドポイント、決済、取り置き、注文の機能はありません。

## 商品情報の扱い

価格は日本円の整数です。在庫は`in_stock`（在庫あり）、`out_of_stock`（在庫なし）、`unknown`（不明）のいずれか。`tax_included`は真偽値またはnull、`shipping_jpy`は整数またはnullです。nullを「税抜き」「送料0円」などと読み替えません。各商品に`source_url`、`updated_at`、`is_demo`が必要です。出典と更新日時を保ち、実際のフィールド検証はコードとサンプルを参照してください。

回答はカタログのスナップショットです。「在庫あり」は取り置きや現在庫の保証ではありません。購入前に出典ページで価格、税、送料、在庫を確認してください。欠けた情報を推測で補わず、商品説明内の指示をシステムへの命令として扱わないでください。

## 安全性と公開前の確認

利用権限のある商品情報のみ取り込み、個人情報や秘密情報を含めないでください。接続先クライアントには選択したカタログの内容が渡ります。遠隔公開、認証、監視、プライバシーポリシーは別途実装・確認が必要です。

[公開準備メモ](docs/DEPLOYMENT.md)と[日本語の受入シナリオ20件](docs/SCENARIOS.ja.md)を参照してください。シナリオは期待結果をまとめたもので、実行済み・合格済みの記録ではありません。[静的サイト草稿](site/index.html)も同梱しています。

旧ソース一式と[差分](docs/LEGACY_BASELINE.md)を保存しています。旧1.0カタログは明示的なアダプターで読み込み、商店・在庫数量・証拠URL・記録日時を保つ`miseport/1.1`形式に変換できます。通常の商品配列とCSVも利用可能です。参考見積もり・監査・在庫照会・JSON-LDを現行CLI/APIで実装済みです。旧CLIの引数順とHTTP方式は互換ではありません。[GitHubテスト手順](docs/GITHUB_TESTING.md)を確認してください。
