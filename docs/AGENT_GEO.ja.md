# Agent GEO for Japanese Merchants — 個人AIエージェントに正しく見つけてもらうためのMisePort設計

**2026-10-29版 / 公開候補（PUBLIC）**  
**重要:** ここに示すのは公開ソースと設計・テスト方法であり、Meta Museの内部ランキングやAgent側の検索アルゴリズムを解析したものではありません。MisePortによるSEO/GEO順位上昇は未実測です。

## 1. 個人助手向けGEOとは？

単にウェブ記事へ「AIにおすすめされる」キーワードを増やすことではない。個人AIエージェントはユーザーの**要求/条件**に合う商品を探索し、出典・品目・価格・配送・在庫・用途・更新時刻を確認して、適切な情報や操作を返す必要がある。

MisePortが目指すのは、**商店が自ら管理する商品事実を、ウェブ検索・正規商品チャネル・接続済みAgentの複数経路で、同じ意味で消費できるようにすること**。

## 2. 三層のGEO（MisePort自身と商店の商品は別の目的）

| 層 | 誰の何が発見される？ | 実行手段 | 注意 |
|---|---|---|---|
| **L1 公開Web / 検索** | 商店の実際の商品ページや販売者ポリシー | 正しい商品タイトル、説明、固有URL、クロール可能なページ、Product/Offer JSON-LD、サイトの内部リンク、sitemap、返品・配送方針 | **既存の商品ページ**への正しい反映が必要。JSON-LDファイルだけ生成しても原ページに自動挿入されない |
| **L2 商品Catalog / Feed・流通チャネル** | 対応するプラットフォームが取り扱う商品情報 | 商店が利用するプラットフォームの**公式チャネル/商品Feed**と許可された外部流通先で、SKU/価格/公開状態を一致させる | Shopify Catalogなど**対象が明示された正規チャネル**を優先。任意のMCP URLを置くだけではShopify Catalog等に登録されない |
| **L3 Agent Tool / Connector** | ユーザーが接続・選択可能な商品検索/説明ツール | Read-only MCP/REST、正確なTool description・JSON Schema・安全なエラー、照会前の説明、実測手順 | Custom Connector個人接続とMeta公認Directoryは別。ツール公開だけでMuseが自動接続することは保証されない |

**MisePortというOSS自体のGEO:** 日本語GitHub README/導入手順、公式デモ、正確な製品制限、使用例、字幕つき動画とGitHubの公開Releaseを整備する。これは**開発者・商店がMisePortを見つける活動**であり、一般消費者に個別商店商品を推薦させるGEOとは分けて計測する。

## 3. 商品をAgentが比較できる形にする

MisePortのCatalogへ（必要ならSchema versionを上げて）次の属性を**出典付き**で用意する。

| 属性群 | 例 | なぜ必要か |
|---|---|---|
| 商品の識別 | 商店ID、商品ID、SKU、親商品/バリエーション、名称、カテゴリ、canonical商品URL | 他商店や同商品バリエーションとの混同を防止 |
| 確認できる価格 | 税込/税抜、通貨JPY、数量ごとの価格、送料・配送地域、割引の適用条件 | ユーザーの「送料込3,000円以内」を**事実に基づいて**判定 |
| 適用できる商品属性 | 産地、素材、サイズ/量、贈答包装、用途、カフェインなど（実商店の根拠がある場合） | 検索語が商品の元名称と異なるニーズを表すときに使う |
| 可用性と条件 | 公開状態、在庫/受注の記録、入荷予定や地域制限、返品/返金ポリシー | その人が実際に購入できる可能性と限界を説明 |
| 鮮度・証拠 | `source_url`、`evidence_url`、`updated_at`、`snapshot_at`、検証結果、`stock_is_live` | 古い価格・在庫を現時点の確定値として答えない |
| 信頼性 | 実店舗の名前・連絡先/サポート・商店の公開ポリシーへのリンク | 身元・アフターサポートを確認。根拠のないレビューや賞を生成しない |

**個人助手のパーソナライズ:** ユーザーが明示した予算、贈答目的、配送先地域、数量、素材等の制約をそのセッションで評価する。Muse内部の個人履歴を取得・推測する機能や、個人的な属性を狙って推薦を誘導する仕組みはMisePortの役割ではない。商店は必要な商品属性を公開し、推薦判断はユーザーとAgent側に残す。

### 例：京都の焙じ茶の贈り物を送料込3,000円以内

「京都産」「ギフト包装あり」「カフェイン控えめ」「税込・送料込3,000円以下」「いま在庫あり」は**別々の検証条件**。価格2,400円でも送料が不明なら条件に合うと断定しない。候補がない時は空の検索結果か「条件不明」を表示する。

現在の`search_products`は**文字列正規化＋部分一致／AND検索**であり、意味検索や個人の購入意図分析ではない。出典付きの構造化フィルタや完全見積もりが必要な場合は将来のSourceAdapter/Canonical Schemaを拡張する。LLMによる類語の推測で不足事実を作らない。

## 4. Tool description を正しく書く（非誘導・検証可能）

良いMCP Tool metadataは「**どんな時に、どのデータを、どの権限で、安全に確認できるか**」を説明する。

```text
search_products — Search this named merchant's published product catalog.
Read-only; returns dated snapshots with SKU, product source URL,
provenance, price/tax/shipping/stock when known.
Use when a user explicitly wants products from this merchant or has
connected this merchant's MisePort endpoint.
Do not assume live inventory, checkout ability, lowest price or
that unknown shipping is free. Return no match honestly.
```

これは**推奨する記述方向**で、すべてのクライアントによる自動選択を保証するものではない。Metaの公式Connector GuidelinesはTool説明に対し、競合を無視する指示、競合サービスからの誘導、無断操作、利用者の意図に反する宣伝を禁止している。商品説明をシステムプロンプトとして扱わない。

追加の開発計画:
- 検索入力を文字列だけに依存させず、属性・価格/税/送料/配送地域・ギフト条件等の検証可能なフィルタに拡張。
- 商品のソース/取得時刻/対応範囲を各応答へ含める。空結果とエラー、認証の問題、未確定を区別。
- API負荷・レート制限・エラー/部分失敗を扱い、公開の範囲を明示。
- 各ToolのJSON Schema、Read/Write注記、20件以上の日本語事例を公開し、Muse側の実行ログで確認する。

## 5. 本質的な発見のギャップ

**その商店のMCPが公開されていても、ユーザーが商店名やURLを知らずCustom Connectorにも未接続なら、MuseがそのMCPを選ぶことは確認できない。**

そのため非接続ユーザーへ向けたGEOの第一歩は、**商品ページと公式プラットフォームのカタログ/フィード**を利用できる状態にすること。Shopifyを使う店舗では、Meta向け商品発見がShopify CatalogやMetaの販売チャネルに依存することが公式に示されている。MisePortはそれをむやみに置き換えるのではなく、元の商品事実を整えて一致させる。

Google Search Centralは実際の購入可能商品ページに Product/Offer の構造化データを置き、可能ならMerchant CenterのFeedも整えることを推奨している。これは**Google検索面の仕様**であってMuseが同じFeedを直接消費すると断定できる資料ではない。独立した公開MCPやGoogle向けFeedを通じたMuseの自然推薦効果は実測が必要。

未公認の `/llms.txt`、`/agents.md`、独自の `.well-known` Manifestを設置しても、Meta Museに自動登録されると宣伝しない。利用可能な情報説明として実装するかどうかは、対象プラットフォームの仕様と実測で決める。

## 6. 効果の計測は3種類に分離する

| テスト群 | 前提 | 観測すること | 混同禁止 |
|---|---|---|---|
| **E1: Tool利用性** | 商品MCPへ**明示的に接続済み** | ツール発見・選択・呼び出し成功率、条件一致、回答正確率、出典、誤推測、レスポンス時間 | 接続成功 ≠ 一般商品検索の露出 |
| **E2: 自然発見性** | 商品MCP**未接続**、商店名を出さない一般的な日語購買依頼 | Museのウェブ探索と商品候補・元URL・出典、有効な価格/送料/在庫情報。元ページや公式Feed状態を揃えて比較 | 一回の推薦 ≠ 恒常ランキング。実際のMuse内部検索順位は不明 |
| **E3: 公認Directory / Channel** | Meta側の審査結果やShopify等のチャネル登録状態を確認 | 設定画面での発見、許可・利用、選ばれるか、正確性。審査待ちなら未測定 | Directory掲載 ≠ 特集・商品推薦の保証 |

追加で**プロジェクトの検索発見（GitHub/検索エンジン/技術コミュニティ）**をE4として別集計。商店商品E2と混合しない。

20件の購買質問セットを使い、金額・用途・包装・配送・未確認/在庫切れ・類義語・誤った条件を組み合わせる。可能なら同じ時点・同条件の前後データで複数回実施して、回答が揺れることを記録。パーソナルエージェントの秘密の個人プロファイル・個人会話を収集しない。パイロット店の露出結果を商店が許可した範囲で公開。

初期のKPI:
- フィールド完備率と証拠付き率、ページとCatalogの価格/状態一致率、スナップショットの鮮度。
- 検索で正しい候補が見つかった割合、条件充足判定の正確率、出典を示す割合、未知情報の誤推測率。
- Tool接続と呼び出し成功率、ユーザー操作の所要時間、商品情報の更新成功率。
- 自然発見時の出現・出典率（結果に現れた回答集合での観測値）。**真のMuse全体の推薦頻度とはみなさない**。

## 7. MisePortにとっての順序

**2026-11-10 商店実用版へ優先する部分:**
1. 商店から公式APIを正しく読み、根拠付きCatalogと適切な公開商品を生成。
2. 実商店の元商品ページへ辿れる公開URL・必要情報・構造化データを作り、商店が実際に設置できる場合のみ適用する。
3. 商店別read-only MCP/RESTを検証し、Museの**接続済み**ツール動作を実演。
4. 1件の許諾済み実商店に対しE1と一部E2の日本語購買質問を実測。未達を明示。

**11/10以降の追加研究候補:**
- 商店の公式ページ、正規Catalog/Feed、MCPを横断する矛盾検出と更新通知。
- プラットフォーム別Feed/商品ページへの実際のデータ反映アダプター。
- Tool metadataとSKU属性の体系的な効果測定、Directory適合の別途審査。

## 原典

- [Meta Muse Connector Guidelines — 審査、Tool定義、Directory discovery](https://platform.muse.ai/docs)
- [Meta Museの仕組み — Connector、Browser、権限](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse)
- [Shopify — Metaでの販売・Shopify Catalog](https://help.shopify.com/en/manual/online-sales-channels/agentic-storefronts/meta)
- [Shopify — Catalogと商品発見](https://help.shopify.com/en/manual/online-sales-channels/agentic-storefronts/products)
- [Google — Product structured data / Merchant listings](https://developers.google.com/search/docs/appearance/structured-data/product)
- [MisePort Muse接続ガイド](MUSE_CONNECT.ja.md)
