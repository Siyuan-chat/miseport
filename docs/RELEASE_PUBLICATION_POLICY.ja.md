# MisePort 11/10 公開・内部ファイル区分ポリシー（リリース時の削除対象）

> **分類: INTERNAL — RELEASE EXCLUDE / リリースまでに公開ブランチから削除・再構成する予定**
>
> **決定:** 2026-10-29 JST。公開GitHubの既存履歴にはすでに内部資料のコミットがある。このファイルを残しても、Release assetから外すだけでも過去のGit履歴は消去されない。
>
> **製品公開ルール:** 「GitHubのmain」「GitHub自動Source archive（タグのtar.gz/zip）」「PyPI sdist/wheel」「配布用インストーラ」「Cloudflareサイト」「Muse提出資料」はすべて**別々の公開面**である。11/10のタグ作成前に、内部資料をmainから除外し、リリース実体とその依存テストを検証する。

## 1. 公開区分を固定する

| 区分 | 意味 | 最終状態 |
|---|---|---|
| **PUBLIC** | 利用者・開発者に必要な製品/導入/セキュリティ/ライセンス資料 | mainとReleaseに必要な範囲だけ保持 |
| **PUBLIC-REVIEW** | 内容・権利・UIとの一致を確認してから公開する資料 | 合格したものだけPUBLICへ |
| **INTERNAL-REMOVE** | 作業指示、社内/個人計画、過去の作業ログ、候補募集・公開同意の運用、公開前のチェックリスト | **11/10タグ前に公開ブランチから削除**。必要なら事前にGitHub外のプライベートな保管先へ移す |
| **ARCHIVE-REPLACE** | 旧ソース参照、廃止候補の画像/Schema、以前の配置実験 | 実行に必要なFixtureのみ匿名化したtests/fixtures等へ移し、旧アーカイブ自体はmain/Releaseから削除 |
| **SECRET-NEVER-COMMIT** | APIキー、PAT、OAuth Secret、顧客/注文データ、商店担当者の連絡先、非公開同意書・撮影元データ | **最初からGitHub・Releaseへ入れない**。発見時は公開を止め、失効/削除/履歴対策を行う |

**注意:** INTERNAL-REMOVEは「一般に秘密が記載されている」と断定するラベルではない。公開製品の利用者には不要な制作・運用文書を指す。既に公開した履歴は単純な削除コミットでは消えない。秘匿すべき情報が実際に含まれていた場合は、関係資格情報を失効させ、GitHubの履歴消去手順と監査を別途実施する。

## 2. main／タグから最終的に削除・置換する内部資料

以下は**現時点ではmainに存在し、過去のコミットも公開済み**。削除対象を明記するが、開発中の運用と証拠を失わないよう**今すぐ一律削除はしない**。

| パス | 11/10の扱い | 公開後に代わりとなるもの |
|---|---|---|
| `PROJECT_STATUS.md` | **INTERNAL-REMOVE**。自動テストの古い状況や運用履歴を含む | 公開 `docs/STATUS.md` と `CHANGELOG.md`、現行CIリンク |
| `docs/DEVELOPMENT_PLAN.zh-CN.md` | **INTERNAL-REMOVE**。作業日付、内部ゲート・担当割当 | 公開用 `docs/ROADMAP.md`（要書き直し） |
| `docs/RELEASE_2026-11-10.ja.md`, `docs/RELEASE_CHECKLIST.md` | **INTERNAL-REMOVE**。公開可否判断の作業資料 | 完了した範囲のみRelease Notesへ |
| `docs/merchant/PILOT_2026-11-10.ja.md` | **INTERNAL-REMOVE**。商店募集・同意フローの運用手順 | 本人が公開承認した実店舗Case Studyのみ |
| `docs/merchant/VIDEO_DEMO_PLAN.ja.md` | **INTERNAL-REMOVE**。撮影スクリプト | 収録済み動画・字幕・操作手順リンク |
| `docs/GITHUB_TESTING.md`, `docs/VALIDATION.md` | **INTERNAL-REMOVE**。検証作業の生ログ・環境推移 | 短い再現可能な `docs/TESTING.md`、CI履歴と公開テスト |
| `docs/LEGACY_BASELINE.md`, `docs/DEPLOYMENT.md` | **INTERNAL-REMOVE / REPLACE**。旧設計との差分・時系列の古い下書き | 現行の `docs/DEPLOY_GUIDE.ja.md` / `docs/HTTP_SERVICE.md` など |
| `docs/SEO_GEO.md` | **INTERNAL-REMOVE**。開発者向け運用メモ | 商品データとAgent向けの公開 `docs/AGENT_GEO.ja.md` |
| `docs/BRAND_VECTOR.md` | **INTERNAL-REMOVE**。承認待ちの再現/制作工程 | 承認済みロゴと公開 `docs/BRAND.md` |
| `docs/merchant/SETUP_GUIDE.ja.md` | **PUBLIC-REVIEW**。将来UIの仮ボタンなどは実実装に置き換えてから正式公開 | 最新UIの実画面・日語操作手順 |
| `docs/MUSE_INTEGRATION.md`, `docs/evidence/muse-demo-20261029.json` | **PUBLIC-REVIEW**。ユーザー識別子・一時パス・API応答・機密を再点検 | 実測を保った公開可能な検証要約・秘匿化済み証拠 |
| `references/legacy-20261027/**`, `references/README.md` | **ARCHIVE-REPLACE**。歴史資料はプライベートに保存、必要な匿名Fixtureを `tests/fixtures/` 等に移す | 公開テストFixtureと移行手順（必要な場合） |
| `assets/brand-v01-review.png`, `assets/geometry-v01.json`, `assets/logo-*.svg`, `assets/logo-*.png`, `assets/favicon.*`, `assets/social-cover.png` | **ARCHIVE-REPLACE**。旧M候補や現在承認されていないブランド案 | 承認済みMisePort店舗/港ロゴ、favicon、OG画像 |
| `docs/RELEASE_PUBLICATION_POLICY.ja.md`（本書） | **INTERNAL-REMOVE**。リリース前のチェックリスト | 必要ならGitHub外で運用 |
| `scripts/package_github.py` | **INTERNAL-REMOVE/REPLACE**。過去のGitHubアップロード用で、製品配布用ではない | 再現可能な正式配布ビルド/確認スクリプト |

**公開保持候補（公開内容を検証）:** `README.md`（日本語）、`README.en.md`、`LICENSE`、`SECURITY.md`、`CONTRIBUTING.md`、`CHANGELOG.md`、`docs/API.md`、`docs/CATALOG.md`、`docs/ROADMAP.md`（公開用に更新）、`docs/CLOUDFLARE.md`（旧情報の点検）、`docs/HTTP_SERVICE.md`、`docs/SDK.md`、`docs/PRODUCT_STRATEGY.ja.md`、`docs/CONNECTOR_ARCHITECTURE.ja.md`（設計／実装区分を残す）、`docs/PLATFORM_COMPATIBILITY.ja.md`、`docs/merchant/SETUP_GUIDE.ja.md`（本番UIに合わせる）、`docs/MUSE_CONNECT.ja.md`、`docs/AGENT_GEO.ja.md`、コード・ライセンス確認済み資産・必要なテスト。

公開用の文書・製品でも、未実装/非公式/個別Museアカウントの機能を本番導入済みと表現しない。

## 3. 現状の技術的リスク（今のままではRelease不可）

1. **`MANIFEST.in` は `recursive-include docs *.md` と `recursive-include references *.md *.json`、さらに `PROJECT_STATUS.md` を指定。** 現行のPython sdistが内部資料を含み得るため、11/10までに**公開対象の明示allowlist**に変更する必要がある。wheel/sdistの実際の内容を双方確認し、旧Fixtureに依存する検証を移行する。
2. **`scripts/package_github.py` は `docs`・`references` フォルダ全体、`PROJECT_STATUS.md` を収集する。** これは当初のGitHubアップロード用であり、今のままでは正式な商店配布に使ってはならない。
3. GitHubの**Release自動Source code (zip/tar.gz)はタグ時点の全追跡ファイル**を含む。Release assetだけを選別しても内部資料がタグに残れば自動アーカイブから取得できる。**タグ前にmainから対象を除外する必要がある**。
4. READMEや公開ドキュメントが内部資料へのリンクを持つ。削除前に公開の `docs/STATUS.md`、`docs/ROADMAP.md`、`docs/TESTING.md` 等へリンクを差し替える。リンクチェックを必須にする。
5. 本番の公開WebサイトとCloudflare ZIPは別の配布経路。ZIPに内部開発資料・認証情報・商店の非公開データ・公開許諾外の素材が含まれないことを**実ファイル一覧で確認**。
6. 商店提供データ／許諾／個人情報は公開Issueに記載しない。許可を得たケースの公開前に法律・商標・データ権利を確認する。

## 4. 11/10 タグ／Release前に必ず走らせるファイル監査

- [ ] INTERNAL-REMOVE/ARCHIVE-REPLACEの対象をGitHub外のプライベート場所へ退避し、公開ブランチ上の参照を公衆向け資料へ置換。
- [ ] 旧文書・不要ブランド候補をmainから削除、テストFixtureを必要なものだけ残して契約テストを通す。
- [ ] `MANIFEST.in`・リリース用packagerを明示allowlistへ変更。実際の`sdist`・`wheel`・Windows配布物の内容をmanifest/ハッシュで確認。
- [ ] 公開RepoとRelease自動Source archiveの**両方**に内部ドキュメントがないか確認。GitHubの履歴が残ることを理解し、敏感情報は別途履歴対策。
- [ ] README／サイト／文書の内部リンク、公開先、権利、StatusとTest結果、Muse説明、法律表記を再点検。
- [ ] 実商店名や実商品を公開する前に、商店が指定した範囲の同意、修正、撤回・削除フローを確認。
- [ ] 監査結果を**公開可能な短いRelease QA要約**にする（内部メモ・未公開商店情報は含めない）。

**現時点の判定（2026-10-29）: BLOCKED — 内部資料がmainにあり、公開配布マニフェストが未分離。** この記載はすでに公開された履歴からの削除を意味せず、タグ前作業を必須にする宣言。
