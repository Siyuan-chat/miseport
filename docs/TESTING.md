# MisePort テスト・受入範囲

**最終確認:** 2026-10-29 JST  
**目的:** テストの種類と、「何が検証できたか」を明確に区別する。

## 1. 自動契約テスト

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/check_site.py
python -m build
python scripts/verify_distribution.py
```

CIでは複数のWindows/UbuntuとPythonで検証し、Node/Cloudflareの固定の架空商品デモも確認します。実際の結果は[GitHub Actions](https://github.com/Siyuan-chat/miseport/actions)で最新版の成功ジョブとSHAを参照してください。

## 2. Windows GUIと実画面キャプチャ

未署名のWindows Alpha EXEをCIで生成します。これは**ビルドと自動テストに成功した**という意味です。ユーザーがWindowsのデスクトップで本当に操作できるか、初心者が迷わず進められるかは別の受入項目です。

実画面を検査するため、`merchant-gui-visual`のCIで実際の Tkinter GUIを仮想画面上で起動してキャプチャし、3枚のスクリーンショット（初期画面・商品URL監査上部・同画面下部）をArtifactとして生成しています。**デモの画面情報は架空商品、PATなし**。この画面のキャプチャは、手作業でWindows実機のユーザーテストが成功したという証拠ではありません。

```bash
# GUIのある開発環境（ビジュアルテスト時にPillowが必要）
python -m pip install pillow
python -m miseport.gui --capture-screenshots artifacts/gui-screenshots
python scripts/check_gui_screenshots.py artifacts/gui-screenshots
```

## 3. 商店の本番受入（別のゲート）

実商店版を名乗る前に、**許諾を得た運営中のショップ**で、店主自身が接続/商品読み取り/公開確認/Cloudflare配信/MCP照会/取り下げまで再現する必要があります。商品名と価格・在庫の記録を元の管理画面と照合し、秘密情報が配信物へ含まれないことを確認します。

- BASE APIのシミュレーション成功 ≠ 実商店PATが認証された。
- ローカルMCPのシミュレーション成功 ≠ 店主のCloudflareで公開に成功。
- Custom Connectorの個別成功 ≠ Meta公式Directory承認や一般購買質問での自動推薦。
- JSON-LDファイル生成 ≠ 元ショップの商品ページへ構造化データが埋め込まれた。

## 4. Releaseのファイル検査

`scripts/audit_release.py`は公開ZIP/Python sdistのファイル内容を検査します。**GitHubのTag自動Source ArchiveはTagの全追跡ファイルを含む**ため、別途`python scripts/release_preflight.py`で内部資料・古い候補素材を除外したことを確認してからTagを発行します。すでに公開されたGit履歴は単純削除によって非公開にはなりません。

[公開ステータス](STATUS.md) ・ [GitHub Issues](https://github.com/Siyuan-chat/miseport/issues)
