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

## D3 — Google Merchant Center JP商品CSV（2026-11-01）

`miseport-export-google` は日本向けJPY商品Feedの基本フィールドCSVをローカル作成します。**実際のShop登録、Googleの審査・販売者ポリシーや画像クローラビリティ、送料設定、掲載・AI表示は別条件**です。

```sh
miseport-export-google --catalog /path/to/merchant-reviewed.json --profile /path/to/discovery-profile.json --output artifacts/discovery/google-jp.csv --report artifacts/discovery/google-diagnostics.json
```

独立した `--profile` で商店が照合済みの `brand_verified=true` を確認してください。初期バージョンはID、商品名、説明、HTTPS商品URL、HTTPS画像、確定した在庫状態、税込・正のJPY価格、実ブランドを**すべての公開商品について**要求します。1件でも条件に合わない場合、既存CSVは上書きせず失敗します。価格が未知・税が未確認なら空欄を補いません。CSVは引用符・改行・日本語を正常にエスケープし、提出は行いません。

ブランド例外、GTIN/MPN、状態、配送ポリシーや商品ジャンル別条件は公式仕様と商店の実態に応じた追加確認が必要です。**テスト用架空商品を本物として提出しないため、`is_demo=true` は直接出力できません。**

参照: https://support.google.com/merchants/answer/7052112?hl=en

## D4 — OpenAI Stable商品Feedのローカルプレビュー (2026-11-01)

正式な提携・日本市場の利用許可が**まだない**ことを前提に、Stableの基本9フィールドに合った `JSONL.gz` を**オフラインのプレビューとしてのみ**作成します。

```sh
miseport-export-openai-preview --catalog /path/to/merchant-reviewed.json --profile /path/to/discovery-profile.json --output artifacts/discovery/openai.preview.jsonl.gz --report artifacts/discovery/openai-preview-report.json
```

- `item_id,title,description,url,brand,seller_name,image_url,availability,price` を正規化・検査します。価格の形式は例えば `1850 JPY`。確認済みブランドが必須で、在庫 `unknown` は仕様どおり明示します。
- 欠損した商品が1件でもあればプレビュー自体を生成せず、以前の出力も保護します。成功した場合は再現可能なgzipと文字コードUTF-8を使います。
- 出力名は必ず `.preview.jsonl.gz` で終わる必要があります。`output_status=local_preview_only`、`market_approved=false`、`partner_approved=false` を機械可読レポートに記録します。
- OpenAIの**標準アップロード対象市場は現在US**です。日本のJPY商品を提出できるとは主張せず、OpenAIの明示的な市場・通貨の受入確認が必要です。MisePortにはSFTP接続・自動送信・決済APIはありません。
- 商店の原ページが購入可能であること、画像や価格の真実性、広告要件、レビュー・送料・返品・GTINなどの追加ルールもこのローカルプレビューでは独立検証しません。

公式仕様: https://developers.openai.com/commerce/specs/file-upload/products および https://developers.openai.com/commerce/specs/file-upload/overview

## D5 — 日语商家 GUI 的 AI 商品发现诊断（Alpha）

商店商品导入、URL 检查和「④ データの確認」通过后，现有 GUI 中会出现 **「AI商品発見の準備状況」**。该窗口沿用**已审查且未发生店铺、URL 或来源变更的 Catalog**，列出 Google / OpenAI 的逐 SKU 字段缺口。

1. 点击「店主確認済みブランドJSONを選択」，读取单独的 Discovery Profile（格式见 `examples/discovery-profile.example.json`）。品牌不会由商家名称自动推断；只接受同店铺的 SKU。
2. 查看各 SKU 的缺失项。界面显示的「項目確認済」只是本地格式准备状况，**不是平台收录、商家资格或者 AI 推荐证据**。
3. 需要保存时，在主界面勾选已审核公开范围。Google CSV 和 OpenAI Preview 按原先 D3/D4 的完整快照校验。若有任一不合格商品，则不能导出。即使已通过本地数据检查，也不会自动提交到 Google 或 OpenAI。
4. 如果主界面源数据、店铺名称或审核状态发生变化，导出操作将被拒绝。更改后必须重新完成商品审核并打开新窗口。

**关键限制：** `OpenAIプレビューを保存` 只会生成 `.preview.jsonl.gz` 本地文件；**日本市场尚未获得相应的 OpenAI Partner/Market 授权**。Google CSV 需要额外在 Merchant Center 官方渠道进行账号、页面、内容及商业政策验证；本工具不负责账号提交。Tkinter 商家真实操作、Windows 实机易用性仍待试点验收。

这个功能不保存 BASE PAT，不调用外部网络，不修改原始商品数据，也不会将本地诊断上传到 MisePort 网站。
