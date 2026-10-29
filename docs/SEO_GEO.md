# GitHub SEO / GEO 公開運用メモ — MisePort

最終更新: 2026-10-29 JST。対象: [Siyuan-chat/miseport](https://github.com/Siyuan-chat/miseport)。

## 基本方針

対象読者は日本のEC事業者と、MCP・Agent Commerceを実装する開発者。GitHubの主READMEは日本語、英語版は[README.en.md](../README.en.md)。英語・日本語の自然な説明を優先し、不自然なキーワード連呼や「Muse公式認定」などの未検証表現を禁止する。検索結果への掲載やAI回答への引用は保証できない。

## GitHubリポジトリのAbout設定（要オーナー操作）

- **Description（推奨案）:** `日本のEC商品カタログをAIエージェントへ接続するオープンソースMCP。CSV/JSONの検証、出典付き商品検索、在庫・送料・参考見積もり、JSON-LDに対応。`
- **Website:** `https://miseport.pages.dev/`（独自ドメイン取得後に更新）
- **Topics（推奨）:** `mcp`, `agentic-commerce`, `japanese-ecommerce`, `ai-agents`, `product-catalog`, `generative-engine-optimization`, `json-ld`, `python`, `cloudflare-workers`, `open-source`
- **Social preview:** 現行の店舗と港のロゴを基にした確認済みの共有画像を設定する。廃止された“M”の候補画像は使わない。

READMEの編集だけではAbout、Topics、Website、Social previewは変更されない。GitHubのリポジトリ管理画面から反映し、実際の表示を確認すること。

## 検索者の質問に答える情報構成

| 検索意図（例） | 入口 | 必要な証拠 |
| --- | --- | --- |
| 日本 EC MCP / ネットショップ AIエージェント | READMEトップ | 何をするか、7ツール、試用手順 |
| BASE makeshop 商品データ AI 接続 | README FAQ | ネイティブ連携は未実装と明記 |
| Muse カスタムコネクタ 商品検索 | 接続ガイド・Muse実測記録 | 実測7件、アカウント内のみ、正式認定ではない |
| 商品JSON-LD / 商品データGEO | README機能表・API仕様 | 出力形式、出典・更新日時・null処理 |
| OSS agent commerce 日本語 | README/README.en | Apache-2.0、再現手順、CI |

## 計測と検証

1. GitHubのREADME・About・Issues・リリースに一貫した製品名、検証可能な機能、公式URLを維持する。
2. ウェブサイトのcanonical・sitemap・robotsとOpenAPIの公開先を検査する。独自ドメインへ切り替えた場合は旧URLを整理する。
3. Search Console（導入できる場合）は **miseport.pages.dev または将来の独自ドメイン** のみを扱う。GitHubドメインのSearch Console所有権を前提にしない。
4. GEOの評価は固定した日本語質問群で繰り返し実施し、引用の有無・誤答・出典・MCPツールの成功率を別々に記録する。「AIが学習した」や「推薦が確定した」とは表現しない。
5. コミュニティ投稿は各規約に従い、許可・動作確認・投稿の事実を分けて記録する。自動スパムや大量のSEO記事は作らない。

## 製品の未実装事項

実ショップ自動同期、OAuth、マルチテナント、リアルタイム価格・在庫、実売上、決済・注文、ランキング測定は現段階のプロダクト機能ではない。将来の企画を本文に含めるときは「計画」と示す。

関連: [PROJECT_STATUS](../PROJECT_STATUS.md)、[Muse検証](MUSE_INTEGRATION.md)、[Cloudflare](CLOUDFLARE.md)、[ロードマップ](ROADMAP.md)。
