# Muse × MisePort 接続・検索・発見の仕組み（日本語）

**更新:** 2026-10-29 JST  
**対象:** 商店主／開発者  
**状態:** **アカウント内Custom Connectorの接続は実測済み**。一般ユーザー向けの公認掲載、自動発見、自然検索からの集客は未検証。

## 最初に押さえる3つの違い

| レイヤー | 何が起きるか | 実証状況 |
|---|---|---|
| **A. ユーザーごとのCustom Connector** | ユーザー／Museが明示的なAPI情報を使って接続し、ツールを呼び出す | **実測済み**：個別Museアカウントに `custom.miseport-demo`、2026-10-29の2回の検証で7ツール呼び出し |
| **B. 公式Connector Directory** | 開発者が申請→Metaが機能・安全・法務・E2Eを審査→承認された場合にMuse内で検出・接続できる | **未申請／未承認** |
| **C. 一般の商品検索** | Museがウェブ閲覧や利用できる商品Catalog/チャネルから候補商品を見つける | MisePortの自然発見実績は**未測定** |

**重要:** 公開 `/mcp` や `llms.txt` を置いたら全Museユーザーに自動的に発見・使用・推薦される、という仕組みは公式に確認できない。承認Directoryへの掲載やウェブ検索結果も商品推薦を保証しない。

## 現在の架空商品デモをMuseで使う

1. Museを起動する（日本では2026-10-23に利用が開始された）。接続操作はアカウントの実際のUIに従い、必要であれば **Settings > Connectors** で既存接続を確認する。
2. Museに「次のドキュメントを読んで、私のアカウント用の**読み取り専用**MisePort Demo Custom Connectorを作って」と依頼する。認証・コード作成の詳細はアカウントの機能により異なり、**誰でも必ずURLを貼るだけで成功するとは保証しない**。
3. 渡す公開情報：**接続ガイド** `https://miseport.pages.dev/docs/`、**MCPエンドポイント** `https://miseport.pages.dev/mcp`、**REST/OpenAPI** `https://miseport.pages.dev/openapi.json`。**架空デモは認証不要**で、本当の商品や商店トークンを扱わない。
4. MCPを利用する場合、Streamable HTTPで`initialize`→`tools/list`→`tools/call`を正しいJSON-RPC形式で実施する。2026-10-29の実測ではMuse側がクライアントコードを生成・修正して呼び出した。Custom Connectorの `CONNECTOR.md`、`connector.yaml`、ツール呼出コードは**そのユーザーのMuse環境で作られたもの**で、MetaがMisePortを全体へ登録したわけではない。
5. 架空商品で「ほうじ茶を検索」「tea-001の詳細」「在庫の記録」「2個の送料込み参考額」を試す。旧実験のtea-001数量2は **4,150円の非拘束参考額**。商品は実在しない／`stock_is_live=false`。実購入はできない。

### Museに伝えるサンプル文（架空商品だけ）

```text
MisePortの公開デモを私のCustom Connectorとして接続して使いたいです。
接続ガイド: https://miseport.pages.dev/docs/
MCP (Streamable HTTP): https://miseport.pages.dev/mcp
OpenAPI fallback: https://miseport.pages.dev/openapi.json
名前: MisePort Demo
架空の商品情報のみを読み取る7つのツールを確認してください。
まず「ほうじ茶」をsearch_productsで探し、tea-001の価格・出典・更新日時を表示してください。
決済や注文は行わず、情報が不明なら推測しないでください。
```

これは**接続を依頼する例文**であり、Museの個別UIで全自動にインストールされることを保証するものではない。外部ネットワーク接続やツール利用はMuseの権限管理と安全確認に従う。

## Museの検索はどの段階で行われるか

```text
ユーザー: 「京都の焙じ茶で、贈り物、送料込3,000円以内」
                     │
        Muse: タスク解釈・利用可能手段を選択
                     │
      ┌──────────────┼──────────────────────┐
      ▼              ▼                      ▼
  Web閲覧/検索    商品Catalog/Feed     接続済み/承認済みTool
      │              │                      │
   商店のURL      各チャネルの在庫       search_products等
      └──────────────┼──────────────────────┘
                     ▼
       商店・SKU/種類・価格・条件を確認
                     ▼
      正確な回答、出典、未確認事項を表示
```

**これは複数の可能な流入経路の概念モデル**であり、Muse内部の秘密アルゴリズムや実際の優先順位を示すものではない。

- **Custom Connector接続済みの明示検索:** ユーザーが特定店での検索を頼んだ時に、その店のMCPツールが使えるか確認する。MisePortの現行ローカル`search_products`は文字列正規化後の部分一致/複数語ANDであり、意味検索ではない。商品が多い時は絞り込み・ページングが必要。
- **未接続ユーザーの自然検索:** その店のMCPエンドポイントを知らなくてもMuseがウェブページや対応商品Feed/チャネル経由で見つける可能性がある。**商品Feedの配信先ごとに利用条件・接続条件が異なる**。一般MCPサーバーの自動登録とは違う。
- **公式Directory:** 承認されたConnectorはMuseのエージェントとSettings内でdiscoverable。これはMetaの文書で確認できる。ただし採用・ランキング・取り上げられ方は保証されない。

## Muse公式Connector掲載を目指す場合

申請窓口: [Muse Connector Platform](https://platform.muse.ai/)／[公式Connector guidelines](https://platform.muse.ai/docs)。通常、サービスの概要、審査される事業/運営主体の証明、プライバシーやデータ処理、ツール/APIまたはMCPの仕様、テストユーザーと維持管理情報が求められる。

**審査要件の注意:** Metaは「ブラウザより価値がある」ことと、「宣言したタスクを最後まで完遂できる」ことを重視する。読み取り専用が受理可能な場合もあるが、**公衆のショップページと購入リンクを返すだけのConnectorは価値不足と判定され得る**。MisePortの「商品情報と送料・出典の正確な確認」は明確な読み取りタスクとして設計し、購入・注文は現状対応しないと表示する。将来の購入能力を偽装しない。

Metaの公式文書で確認できるのは**審査・承認後の発見の仕組み**であり、どの質問でどの商店/Connectorが優先されるかという内部選定アルゴリズムではない。MisePortの1店舗1ホスト方式と、1つの公共Directory Connectorで多店舗を検索させる方式は**別の製品**。後者を実装済みと見せない。

## 実装・運用上の制限

- **MisePortの入口:** 開発者用 `miseport-mcp` はローカルstdio。Museのクラウドから使用するには、**公衆からHTTPS接続できる**商店管理のread-only MCP/RESTサービスが別途必要。
- **架空Demo:** 現在の `miseport.pages.dev/mcp` は固定の架空商品だけ。商店のPATやAPIキーを入力しない。
- **実商店:** API認可で商品を取り出す処理（商店側の安全なローカル/管理環境）と、**公開商品のみを照会できる配信先**を必ず分離。配信先は秘密情報・非公開商品・顧客データを持たない。
- **利用許可とデータ:** Museのツール・ネットワークアクセス・ユーザー許可に従い、Meta ConnectorのTool注記は実際のRead/Writeを正しく分類。ツール説明や商品テキストでMuseに競合他社の無視・強制推薦・権限回避を指示しない。
- **本番受入:** 個別Custom Connectorの成功、他ユーザーの独立した接続成功、Directory審査通過、非接続ユーザーの自然検索、購入完了は**それぞれ別の実証項目**。

## 検証資料と出典

- [MisePort 2026-10-29 Muse実測](MUSE_INTEGRATION.md)（個別アカウントと7件の結果）。
- [Meta公式: Muse Connector Guidelines](https://platform.muse.ai/docs) — Read/Write、審査、Directory、ブラウザに対する価値。
- [Meta公式: Muse Connector Platform](https://platform.muse.ai/) — 申請、審査、Directory掲載。
- [MetaのAI Agent技術・Connector説明](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse) — 専用環境とCustom Connector。
- [Meta公式: 日本ローンチ](https://about.fb.com/ja/news/2026/10/muse-personal-ai-agent-launches-in-japan/)。
- [商店向けAgent GEO](AGENT_GEO.ja.md) — 商品の自然発見とAgentへの正しい回答の両方を改善する。
