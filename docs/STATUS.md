# MisePort 公開ステータス（Alpha）

**最終確認:** 2026-10-29 JST  
**正式商店版の目標:** 2026-11-10（**未リリース**）  
**現状:** オープンソースの商店向け Alpha コードと、架空商品の公開デモを提供中。実商店による公開運用・Muse自然発見は未検証。

## 現在動いているもの

- Pythonの商品カタログ・検証・JSON-LD/読み取り専用MCP（7ツール）と、架空の商品を使用する [公開デモ](https://miseport.pages.dev/)。
- BASE API v2β の商品読み取り専用接続コード（商店所有PAT、明示的な読取権限、手動再取得）と、BASE/Shopifyの商品CSVのローカル取り込み Alpha。
- 日本語のローカル GUI Alpha：ショップの選択、商品と公開URLの確認、カタログJSON保存、商店向けMCP/REST ZIP生成、Cloudflareへの手動公開案内、公開後の読み取り専用MCPチェック。
- 商品とショップの識別、出典・更新時刻、未確認の値、失敗した再取得や非公開商品についての安全側の処理。
- CIで実行する Python/Node/Cloudflare契約テストと、未署名Windows Alpha EXEのビルド。実物のTkinter GUIの画面キャプチャも、架空データで自動生成しています。
- 未署名Windows EXEのGUI起動スモークテスト（実際の利用者受入とは別）、合成商品20件のMCPプロトコル評価、商品カタログ2ファイル間のオフライン整合性検査。

## まだ完了していないもの

| 項目 | 状態 |
|---|---|
| 実在するBASE店舗での認可・商品取得の受入 | **未検証** |
| Windowsの非技術者によるクリック操作・導入テスト | **未検証** |
| 店舗のCloudflareアカウントでの公開、更新、公開停止 | **未検証** |
| 実際の店舗の掲載許諾がある商品デモ | **未確保** |
| Meta Muse Custom Connectorでの実商店の独立接続 | **未検証** |
| Meta Connector Directoryへの正式申請・承認 | **未申請** |
| Museが非接続ユーザーに自然推薦すること | **未検証** |
| 11月10日正式Release用の内部ファイル除外・資産確認 | **準備中** |

**注意:** [Muse接続を試験済み](MUSE_CONNECT.ja.md)と記載されるのは、1アカウント内の**架空商品デモのCustom Connector**についてです。ほかの商店がMeta公式ディレクトリに掲載されたことや、消費者への推薦を意味しません。

**日本語図解:** 実際のTkinter GUI画面を架空商品で撮影した[3枚の画像入りHTML操作ガイド](merchant/GUI_VISUAL_ALPHA.html)を公開しています。実店舗での受入はまだありません。

## 参照

- [日本語README](../README.md) ・ [商店の操作説明](merchant/GUI_ALPHA_GUIDE.ja.md) ・ [画面付き手順](merchant/VISUAL_GUIDE.ja.md)
- [導入とMCPの仕様](API.md) ・ [公開Cloudflareデモ](CLOUDFLARE.md) ・ [品質とテスト方法](TESTING.md)
- [製品方針](PRODUCT_STRATEGY.ja.md) ・ [公開ロードマップ](ROADMAP.md) ・ [GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)

このページは公開可能な**検証済みの範囲**のみを要約します。開発用の内部作業記録や商店参加希望者の非公開資料は、正式Releaseに含めません。
