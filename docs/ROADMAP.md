# MisePort 公開ロードマップ

**更新日:** 2026-10-29 JST  
**ステータス:** 商店向け Alpha。2026-11-10の商店実用版は**目標であり未リリース**。

MisePortは、国内の小さなECショップが**自分で管理する商品データ**をAI Agentに安全につなげる無料優先のオープンソースツールです。中央マーケットプレイスや決済SaaSにはしません。

## 現在実装されているAlpha（商店本番受入は未完了）

- BASE API v2βの**読み取り専用**商品取得、公開商品/種類の検証。実商店のPATでの動作は未確認です。
- BASE/Shopify公式商品CSVのローカル読込（Alpha）、日語GUIの商品確認、SKU/価格/在庫/送料不明・出典・更新時刻を維持した商品出力。
- BASEの公開商品URL候補生成と、店主が明示した最大30件に対する安全側の公開HTTPS確認。
- 商品の追加/変更/削除差分、異なる店舗の商品混入の防止、前回の正常データを保護する更新処理。
- 店舗ごとの商品Catalog/JSON-LDと読み取り専用MCP/RESTの配信用ZIP、およびCloudflare Pagesの手動アップロード説明。
- ZIPの完全性検査、デプロイ後の明示的なMCP/REST読み取り確認機能、Windows Alpha EXEのCIビルド。
- 架空商品だけを使う[公開デモ](https://miseport.pages.dev/)と、1アカウント内のMeta Muse Custom Connector呼出の検証記録。

これらはソースコード・Mockテスト・CIで検証した**Alpha**であり、実際の商店で安全かつ簡単に運用できることの証明ではありません。

## 11/10の目標と公開判定

1. 日本の技術非専門の商店主がWindowsから自力で起動、商品読込・監査・公開物作成を行える。
2. 許諾済みの**実際に営業しているBASE店舗**で、読み取り専用PATによる商品取得、正確性・安全性・公開対象の確認を完了する。
3. 商店管理のHTTPS公開先で商品データ/MCPを確認し、更新・公開停止を再現する。
4. 少なくとも**1店舗の許可済み公開実商品デモ**、実画面の日本語手順・動画を公開する。
5. 秘密・顧客情報・内部作業資料を含まないSource Archive/配布物を実物検査し、最新CI・OSの実行記録を確認する。

**未達項目を「達成済み」とは発表しません。** 外部商店の参加・情報公開許可、Metaの公式Directory登録や自然商品発見は保証できません。

## 次の開発

- 商店主によるWindows実機受入・画面の改善、明確な日本語スクリーンショットとFAQ。
- 許諾済み商店のBASE API・CSV・Cloudflare公開・Muse接続のEnd-to-End実証。
- 認可条件を確認した上での他社EC API対応と公式CSVフォーマット互換性検証。
- 商品ページ/正規Catalog/Agentツールのそれぞれの自然発見・正確性を別々に評価するGEO研究。

## 公式資料

[利用状況](STATUS.md) · [日本語の操作説明](merchant/GUI_ALPHA_GUIDE.ja.md) · [実画面ガイド](merchant/VISUAL_GUIDE.ja.md) · [MCP/API](API.md) · [接続とMuseの制約](MUSE_CONNECT.ja.md) · [Agent GEO](AGENT_GEO.ja.md) · [テスト方法](TESTING.md) · [公開Issue](https://github.com/Siyuan-chat/miseport/issues)
