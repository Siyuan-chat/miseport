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


## D2 — 元の公開商品ページ監査（2026-10-30 Alpha）

この機能は商店の**本来の商品ページ**のHTTP応答、canonical、robots.txt（Googlebot / OAI-SearchBot）、meta / X-Robots-Tag noindex、Product JSON-LDのSKU/URL/名前/価格/在庫記述を読み取り比較します。サンプルを使う場合は**すべてローカルで実行**し、Webへアクセスしません。

```sh
miseport-web-discovery-audit --catalog tests/fixtures/demo-store.reference.json --offline-manifest examples/discovery-web-evidence.demo.json --output artifacts/discovery/page-audit.json
```

`examples/discovery-*.demo.*` は架空の原本HTML / robots.txt資料です。オフライン入力はスナップショットの**コピー**であり、実際にページが配信されているという証明ではありません。

実店舗へのネットワーク検査は、商店がそのショップの公開商品ページへの読み取りアクセスを明示的に許可した場合に限って、次のように**個別に開始**できます（自動定期巡回ではありません）。

```sh
miseport-web-discovery-audit --catalog /path/to/merchant-reviewed.json --live --merchant-approved --max-products 5 --output artifacts/discovery/live-audit.json
```

同じ店舗のHTTPSページのみ、最大10商品、各リクエスト最大4秒、HTML 128KiB、robots.txt 64KiB。DNSは公開IPに制限しTLS検証済みIPへ接続します。Cookie / API Token /認証情報を送らず、リダイレクトを追いません。URLクエリ付きの商品の**オンライン検査は今は未対応**で、オフラインデータ監査に切り替えます。商品ページが大きすぎる場合や、robots.txtを取得できない場合は、結果を未検証のまま残します。

検査項目が満たされても、**Googleにインデックス済み、Merchant Listing掲載可能、ChatGPT / Museで自然発見された、売上が向上した**などの証明にはなりません。インデックス状況は、権限のあるSearch Console等の別証拠を待って記録します。商店所有の既存商品ページは変更せず、重複商品ページを勝手に生成しません。


## 資料と適用範囲

- Google商品データ仕様: https://support.google.com/merchants/answer/7052112
- Google Merchant Listing: https://developers.google.com/search/docs/appearance/structured-data/merchant-listing
- OpenAI Stable Products (Draftではない): https://developers.openai.com/commerce/specs/file-upload/products
- OpenAIパートナー手続: https://developers.openai.com/commerce/guides/get-started

これらは変更される外部仕様です。実際にFeedを出す段階で再確認してください。**現在はローカル事前検査のみで、Feedの完全なエクスポートやプラットフォームAPI提出は未実装です。**
