# MisePort 公開ロードマップ

**更新:** 2026-10-29 JST  
**製品の方向:** 日本の小規模ECショップが自分の商品情報を、読み取り専用のAIエージェント用Catalog/MCPへ安全につなぐオープンソース。中央商品データベースや決済ネットワークを必須としません。

## 現在: 商店向けAlpha

- BASE v2 βの**商品読み取り専用**API ConnectorのAlpha実装と、BASE/Shopify公式商品CSVの読み込み原型（いずれも実店舗での適合試験前）。
- 日本語のローカルGUI、URL候補・公開ページ確認、商品情報の監査と更新差分、JSON/JSON-LD、商店別の読み取り専用MCP/REST ZIP生成。
- 商店自身がCloudflare Pagesへ手動で公開する手順、生成ZIPの整合性検証、公開後のMCP/RESTへの読み取り専用接続確認。
- 架空商品の公開デモ、基本MCPツール、Python/Node/CloudflareテストおよびWindows Alpha EXEの自動ビルド。
- 実際のTk GUIから取得した、**架空商品を使用する画面キャプチャ**と日本語ガイド。

[確認済みの範囲・未実施事項](STATUS.md) / [テスト方法](TESTING.md) / [画面ガイド](merchant/VISUAL_GUIDE.ja.md)。

## 2026年11月10日の目標（未リリース）

1. 実店舗の許諾を得たBASE API接続、公開商品の取得・検証を成立させる。
2. 非技術者がWindowsで、商品取込→審査→ZIP生成→公開→Agent照会を自分で操作できることを実証する。
3. 商店管理のHTTPSサイトへの実際の公開、更新、停止、MCP Client接続を検証する。
4. **実在し営業中の日本のEC商店1店以上**の明示的な公開同意に基づき、実商品を使った公開デモと実画面動画を公開する。
5. 内部作業資料と旧資産を正式Release Tag/Source Archive、Pythonパッケージ、商店配信物から除外する。

*これは目標であり、承認待ちの商店の協力、Meta Museの正式Connector掲載、AIによる自然推薦や売上改善を保証するものではありません。*

## その後の開発候補

- 商店が許諾した対応プラットフォーム（Shopify/カラーミー/makeshop/EC-CUBE等）の公式API Adapter、公式CSV形式別の往復検証。
- 商店所有の任意ランナーによる定期同期・非公開商品への追随・復旧・差分通知。
- 正しい商品ページの構造化データや正規商品Feed、Tool仕様改善、Museなど個人AI Agentの自然発見・回答精度に関する再現可能な計測。
- 日本語の追加の画面写真、字幕付き動画、プラットフォーム別の使い方。

[製品方針](PRODUCT_STRATEGY.ja.md) / [商品データ](CATALOG.md) / [MCP接続](MUSE_CONNECT.ja.md) / [GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)。

**注意:** 本ロードマップは公開用の製品情報です。商店の非公開の連絡先・同意や、内部スプリント計画は含みません。
