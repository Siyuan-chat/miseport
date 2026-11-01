# MisePort E2 — 自然発見の実測プロトコル（商店MCP未接続）

**状態:** 20件の合成日本語購買質問、研究仕様契約、オフラインの採点ツール。実際のChatGPT/Muse/Gemini露出観測は行っていません。

## E0/E1とは異なるもの

E2はユーザーが店名や商品URLを明示せず、商店MCPを接続せず、普通の買い物相談をしたときにその店の商品が実際に回答や引用に出るかを調べる研究です。MCP接続テスト（E0/E1）、Google Merchant Centerのフィード提出、インデックス登録と混同してはいけません。評価CLI自体はAIへの質問、Web検索、URL取得、API送信をしません。

## 実験の進め方

1. 店舗から商品情報の利用・研究・結果公開について必要な権限を得る。PAT、顧客情報、私的なAI会話ログを収集しない。
2. 20件の一般的な日本語購買質問、対象商品URL、モデル、ホスト、検索設定、反復回数を**実験前に凍結**する。店名・URL・商品IDをプロンプトへ埋め込まない。
3. 実際のホストで、商店MCPが未接続であることを確認する。未接続状態と設定はユーザー申告であり、オフラインの採点器はプラットフォーム側から検証できない。
4. ベースライン試行の回答・商品URL・引用元・実行時刻を記録し、原回答やスクリーンショットは権限のある安全な場所に保管する。原回答のSHA-256をログへ記録する。
5. 商店が公式商品ページや承認済みチャネルを整備した後に、同じ20問・同一ホスト/モデル/設定/反復条件で再度試す。得られるのは比較可能な**記述統計**であり、無作為化や時変要因の制御なしに因果効果とは言えない。

## テスト用の架空データ

テストでは tests/fixtures/e2-shopping-20.synthetic.json に20件の店名未指定の日本語購買質問と架空の対象商品URLを用意しています。tests/fixtures/e2-trace-empty.synthetic.json は**観測0件**の例であり、成功した自然発見実験は存在しません。

```sh
mkdir -p artifacts/discovery
miseport-e2-eval --study tests/fixtures/e2-shopping-20.synthetic.json --trace tests/fixtures/e2-trace-empty.synthetic.json --output artifacts/discovery/e2-empty-report.json
```

出力の baseline/followup の露出率は null、完全な比較ペアは0です。未実施の質問や人間の未レビュー結果を、自動的に「推薦されなかった」と計数しません。

## 実測ログ例（書式のみ、実行した結果ではありません）

```json
{
  "schema_version": "miseport-e2-trace/1.0",
  "study_id": "consented-shop-study-v1",
  "observations": [
    {
      "trial_id": "baseline-E2-01-1",
      "phase": "baseline",
      "prompt_id": "E2-01",
      "replicate": 1,
      "host": "actual-host",
      "model": "actual-model-version",
      "settings_id": "browser-enabled-fixed",
      "captured_at": "2026-11-01T11:00:00+09:00",
      "shop_mcp_connected": false,
      "shop_named_in_prompt": false,
      "reviewed_by": "manual-reviewer",
      "answer_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "observed_product_urls": [],
      "cited_product_urls": [],
      "product_facts_correct": null
    }
  ]
}
```

上例の回答SHA-256はダミーです。実験時に原回答から計算し、元の会話内容をこのGitリポジトリに登録しないでください。観測URLは事前登録した実店舗の target_product_urls に完全一致する必要があります。第三者サイトや曖昧な類似商品は対象商品の発見として入力できません。原回答は採点結果にコピーされません。

人手のレビューが未完成なら reviewed_by/answer_sha256/observed_product_urls/cited_product_urls/product_facts_correct をすべて null としてください。全回答のレビューには発見した対象商品URL、実際の引用URL、商品事実が正確かを明示します。

## 集計と制限

人手でレビューした試行だけを分母として、対象商品露出率、対象商品引用件数、正確な露出率を計算します。前後比較は同じ質問ID・反復番号・ホスト・モデル・設定IDで両方レビューされた試行だけをペアにします。欠測値は比較から外れます。

報告に source_evidence=self_reported_human_review_not_independently_verified、platform_indexing_verified=false、causal_lift_established=false を記録します。商店の試験参加許諾、実際に接続していなかった状態、プラットフォーム検索ログ、推薦順位は個別の証拠がない限り証明されません。

正式な実商店を試験する前に、合成サンプルの店名・商品カテゴリ・質問内容・対象URLを実商店向けの新しい凍結研究仕様に置き換え、別の版として管理してください。
