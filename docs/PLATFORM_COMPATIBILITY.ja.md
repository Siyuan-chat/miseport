# 日本ECプラットフォーム互換性マトリクス（設計・調査）

**調査日:** 2026-10-29 JST  
**製品実装状態:** 下記の「公式機能がある」は、MisePortでの対応済みを意味しません。**現在のコード（Alpha）は、既存の標準CSV/JSONに加えて**BASE v2βの読み取り専用API接続試作**、**BASEの商品CSVとShopifyの新旧商品CSVの読み取り専用取込試作**を含みます。ただし実商店でのAPI/CSV互換受入は未完了で、プラットフォームへ商品を書き戻す機能はありません。

## 用語と検証レベル

| 区分 | 説明 |
|---|---|
| **API取得** | 認可されたショップのAPIからMisePortが商品を読み取る。できるのはAPI連携を実装し、接続権限を得たショップのみ |
| **CSV読込** | ショップが公式にエクスポートした商品CSVをMisePortへ取り込み、項目を自動対応する |
| **CSV書出** | MisePortから指定ショップが取り込める正式な商品CSV書式を生成し、プラットフォームのテスト環境で確認する |
| **商品更新** | ショップに書き戻す操作。読み取りやファイル出力とは別で、本製品の初期範囲外 |

**互換性の合格条件:** 公開状態、SKU、商品ID、オプション／バリエーション、価格、在庫、税、画像・カテゴリ、エンコーディングを確認。CSV生成だけでは実際にショップへ取り込める保証にならない。書き戻しは将来の別設計にする。

## プラットフォーム別の公式状況

| プラットフォーム | 正式な商品読取経路 | 商品CSV | MisePortでの開発順序 |
|---|---|---|---|
| **BASE** | [新API β](https://apiv2.thebase.com/docs/) はPAT認証、`GET /api/items`・`items.read`。β版のOAuthは今後追加予定で、正式仕様は変更の可能性あり | [CSV商品管理 App](https://help.thebase.in/hc/ja/articles/900000043803) でダウンロード・更新。利用するApp/商品種に制限あり | **BASE API read-only Alpha実装済み**。公式商品CSVのread-only Alphaも実装、書出/実商店互換は未検証 |
| **Shopify** | [GraphQL Admin API](https://shopify.dev/docs/api/admin-graphql/latest) + アプリ承認（`read_products`、在庫取得に必要なら`read_inventory`）。[認証ガイド](https://shopify.dev/docs/apps/build/authentication-authorization)。汎用「APIキー貼り付け」を推奨しない | [公式商品CSV](https://help.shopify.com/ja/manual/products/import-export/using-csv)。Handle・バリエーション等の依存関係あり | **商品CSV read-only Alpha実装済み**。ネイティブAdmin APIは未実装、実店舗互換とCSV書出は未検証 |
| **カラーミーショップ** | [API](https://help.shop-pro.jp/hc/ja/articles/115009114647)利用可。公式[CLI＆Skills](https://developer.shop-pro.jp/news/releases/release_cli_skills_20260410)はOAuthと`GET /v1/products`を案内 | [商品データのCSVダウンロード](https://shop-pro.jp/functions/csv/)は各プランで利用可能。[操作手順](https://help.shop-pro.jp/hc/ja/articles/360062479334-) | P2。OAuth/既存CLIの再利用可能性、CSVエンコーディングを検証 |
| **makeshop** | [GraphQL shop admin API](https://developers.makeshop.jp/api/)で商品・在庫を取得。利用登録とアプリの認証情報が必要。[API仕様](https://developers.makeshop.jp/api/graphql/index.html) | [2025-12以降の公式CSV書式](https://manual.makeshop.jp/hc/ja/articles/53061016220441-) は列名・フォーマット選択に注意 | P2。認証準備・商品属性マッピング後にパイロット |
| **EC-CUBE 4系** | [Web APIプラグイン](https://doc4.ec-cube.net/eccube-api4)の導入が必要。GraphQL、OAuth2 Authorization Code、Webhook。バージョン別[4.2/4.3系プラグイン](https://www.ec-cube.net/products/detail.php?product_id=2400) | [CSV出力項目設定](https://www.ec-cube.net/manual/ec-cube4/setting/shop_csv.php)がカスタマイズ可能 | P2/P3。管理者のプラグイン導入・権限確認が必要 |
| **STORES** | [開発パートナー申請](https://faq.stores.jp/hc/ja/articles/28207143147545-)が必要。**フリープランではAPI利用不可**。公開APIの制限あり | 公式の利用可能な商品CSV書式・プラン条件を個別確認 | P3。未認可の店舗にはCSV経路。APIの無条件利用を謳わない |
| **Yahoo!ショッピング** | [ストア運営向けAPI](https://developer.yahoo.co.jp/webapi/shopping/)があり、Yahoo! ID連携とアプリ登録が必要。商品・在庫APIを別々に確認 | ストア管理に合わせたCSV形式の具体条件を公式マニュアルで個別検証 | 将来、協力店舗が得られた場合に検討 |
| **楽天市場(RMS)** | 商店管理向けRMS APIは[楽天ウェブサービスとは別](https://webservice.faq.rakuten.net/hc/ja/articles/37599235125913-)。楽天の無料一般APIで店舗管理に接続できるわけではない | RMSの店舗権限と最新ファイル仕様を別途調査 | 将来。無償の一般公開APIで運用可能とは主張しない |

### ソースを読むときの注意

- BASEの旧v1 OAuth資料と新v2 β PAT資料を混同しない。対応対象バージョンをアダプターに記録する。
- makeshopのGraphQLと旧APIは同じではない。エンドポイントや認証は開発者登録に応じた公式情報に従う。
- ShopifyのAdmin APIはアプリ認証とスコープ承認が前提。外部商店向けの「自分のAPIキーを入力するだけ」という説明は不正確。
- STORESの無料プランではAPI利用できないという制約は、MisePortの「無料優先」設計に直接影響する。
- APIで非公開商品・下書き・販売終了商品まで返る場合、公開用Catalogに無条件で含めない。

## 第一回実装の優先順位（未着手）

| 順序 | 作るもの | 受入条件 |
|---|---|---|
| 1 | BASE v2 β読取専用PATコネクタ | 認証状態・`items.read`・ページ処理・公開可否・SKUのテスト。秘密情報をURLやログに載せない |
| 2 | 公式CSVプロファイルの検知・取り込み：BASE / Shopify / makeshop / カラーミー / EC-CUBE | 本物の**匿名化した公式サンプル**と列マッピングの合格記録。文字コード・変体・画像を確認 |
| 3 | Shopify公式アプリ接続、カラーミーOAuth、makeshop | 認可スコープ・失効・レート制限・エラー回復・非公開商品漏出の確認 |
| 4 | **CSV書き出し**（各対象プラットフォーム） | 公式のインポート形式に合致し、sandboxやテストショップで取り込みを実証。重要列欠損なら拒否 |
| 5 | STORES / EC-CUBE / Yahoo / 楽天などの追加 | パートナー登録・管理者権限・利用規約に適合する範囲から実装 |

書出は**エクスポートボタンでファイルをダウンロード**する機能。商品が元のECへ自動登録・変更されるものではない。カタログ生成時のGEO用出力と、ショップ自身の更新用CSVを混同しない。

## 互換性のテスト資産（将来追加）

```text
connectors/
  base/                  # API v2 beta read-only
  shopify/               # OAuth admin GraphQL read-only
  colorme/               # OAuth read-only
  makeshop/              # authorized GraphQL
  eccube/                # optional versioned plugin
profiles/
  base/csv-v<version>/
  shopify/product-csv-v<version>/
  makeshop/csv-v<version>/
  colorme/csv-v<version>/
  eccube/csv-v<version>/
tests/fixtures/platforms/
  <platform>/<version>/<sanitized-fixture>.csv
```

上記は**提案ディレクトリ**であり現在のGitHub実装ではない。外部APIを呼ぶテストは必ずテストショップ・モック・明示許可を使う。利用者の本番資格情報をCIにコミットしない。

関連: [コネクタ設計](CONNECTOR_ARCHITECTURE.ja.md) / [商店主向け手順書](merchant/SETUP_GUIDE.ja.md) / [製品方針](PRODUCT_STRATEGY.ja.md)。
