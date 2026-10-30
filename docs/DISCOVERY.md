# Discovery readiness / AI商品発見の準備診断 (Alpha)

MisePortの商品データを**公式チャネルへの提出前に**検査します。AI推薦・検索結果への掲載・Google Merchant Center審査・OpenAI Feedの受理を判定するツールではありません。

## 現在の実装 (D1)

```sh
mkdir -p artifacts/discovery
miseport-discovery-readiness --catalog tests/fixtures/demo-store.reference.json --output artifacts/discovery/readiness.json
```

表示する状態は `local_fields_complete` のみで、`submitted=false`、`accepted/indexed/agent_discovery_observed=null` のままです。架空商品が通過しても実店舗として利用できるという意味ではありません。

- **Google Merchant Center商品データの事前確認:** SKU ID長、商品名・説明、HTTPS商品URL、画像URL、在庫状況を検査します。元の商品ページ上で購入できること、実際の価格・画像が一致すること、ショップの所有権、配送・ポリシー、Merchant Center登録を検証しません。
- **OpenAI Stable Product Feedの事前確認:** `item_id,title,description,url,brand,seller_name,image_url,availability,price` に相当する値の欠落を検査します。Stable仕様では `availability=unknown` は許容されます。Feed提出は現在承認されたパートナー向けで、MisePortは自動登録しません。
- 商店名を商品ブランドに**流用しません**。商品ブランドは商店自身が実ページと照合したときだけ、別のDiscovery Profileに入力できます。Catalogの価格・在庫・画像などの事実は書き換えません。

例: `examples/discovery-profile.example.json` は架空の確認例です。

```sh
miseport-discovery-readiness --catalog tests/fixtures/demo-store.reference.json --profile examples/discovery-profile.example.json --output artifacts/discovery/with-profile.json
```

技術的データ契約: `DiscoveryProfile` (`miseport-discovery/1.0`)。商品ごとの `sku`, `brand`, `brand_verified` を保持し、同一SKU重複、存在しないSKU、商店ID不一致、未知の設定キーを拒否します。`python scripts/export_schemas.py` でJSON Schemaを再生成できます。

## 今後のD2: 本来の商品ページのWeb監査

原販売ページのcanonical、robots/noindex、JSON-LD、sitemap、情報一致などを検証し、**「ページが取得できた」**と**「検索エンジンが実際に登録した」**を分けます。店舗サイトに変更を加えず、認証も要求しません。

## 資料と適用範囲

- Google商品データ仕様: https://support.google.com/merchants/answer/7052112
- Google Merchant Listing: https://developers.google.com/search/docs/appearance/structured-data/merchant-listing
- OpenAI Stable Products (Draftではない): https://developers.openai.com/commerce/specs/file-upload/products
- OpenAIパートナー手続: https://developers.openai.com/commerce/guides/get-started

これらは変更される外部仕様です。実際にFeedを出す段階で再確認してください。**現在はローカル事前検査のみで、Feedの完全なエクスポートやプラットフォームAPI提出は未実装です。**
