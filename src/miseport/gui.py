"""First functional Japanese merchant GUI prototype, local-only and read-only.

Usage: python -m miseport.gui
The current prototype supports BASE fetch/review/export; it does not host MCP.
Do not paste credentials into a public web page.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import threading
from urllib.parse import urlsplit

from .base_v2 import BaseAPIError, map_base_items
from .source_adapters import get_source_adapter, MerchantProfile
from .source_context import capture_source_context, context_is_current, SourceContextError
from .platform_csv import (
    PlatformCSVError, import_base_product_csv, import_shopify_product_csv
)
from .importers import load_catalog
from .refresh import commit_refresh, plan_refresh, RefreshError
from .publisher import PublicationError, build_merchant_zip
from .base_urls import (
    BaseURLValidationError, candidate_product_urls, validate_manual_product_urls
)
from .public_url_probe import check_product_urls, URLProbeError, MAX_URL_CHECKS
from .merchant_onboarding import merchant_deploy_guide, DeploymentGuideError
from .deployment_probe import check_live_merchant_deployment, DeploymentCheckError
from .bundle_probe import inspect_merchant_zip, BundleVerificationError


def parse_product_urls(text: str) -> dict[int, str]:
    """Parse one 'BASE item ID = verified product URL' per line."""
    result = {}
    if len(text) > 200_000:
        raise ValueError("URL一覧が長すぎます。")
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        left, sep, right = line.partition("=")
        if not sep or not left.strip().isascii() or not left.strip().isdigit():
            raise ValueError("商品URLの" + str(line_number) + "行目は「商品ID=公開URL」です。")
        key = int(left.strip())
        url = right.strip()
        parsed = urlsplit(url)
        if (key < 1 or key in result or parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password or any(c.isspace() for c in url)
                or len(url) > 2048):
            raise ValueError("商品URLの" + str(line_number) + "行目を確認してください。")
        result[key] = url
    return result


def preview_mapping(items: list[dict], merchant_id: str, merchant_name: str,
                    merchant_homepage: str, url_lines: str, is_demo: bool = False):
    provided = parse_product_urls(url_lines)
    validate_manual_product_urls(provided, merchant_homepage.strip())
    return map_base_items(
        items,
        merchant_id=merchant_id.strip(), merchant_name=merchant_name.strip(),
        merchant_homepage=merchant_homepage.strip(),
        source_urls=provided, is_demo=is_demo,
        snapshot_at=datetime.now(timezone.utc),
    )


def main():
    """Open a local window only. Never starts an HTTP listener or stores a token."""
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1:] == ["--version"]:
            print("MisePort merchant GUI 0.1 prototype")
            return
        raise SystemExit("Only --version is supported")
    import tkinter as tk
    import webbrowser
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("MisePort — お店の商品をAIへ")
    root.geometry("1000x690")
    root.minsize(780, 540)

    jobs = queue.Queue()
    items = []
    current = None
    current_inputs = None
    csv_loaded = None
    source_mode = "api"
    csv_loaded_profile = None
    last_bundle = None
    loaded_source = None

    def source_config(mode):
        if mode == "api":
            return ("api", "base", "")
        return ("csv", csv_kind.get(), sample_url.get().strip())

    def source_at_inputs(mode):
        kind, platform, sample = source_config(mode)
        return capture_source_context(
            kind, platform, merchant_id.get(), merchant_name.get(),
            homepage.get(), example_url=sample)

    def imported_for_current_shop():
        kind, platform, sample = source_config(source_mode)
        return context_is_current(
            loaded_source, mode=kind, platform=platform,
            merchant_id=merchant_id.get(), merchant_name=merchant_name.get(),
            merchant_homepage=homepage.get(), example_url=sample)

    def label(row, name, value="", width=30, secret=False):
        ttk.Label(row, text=name).pack(side="left", padx=(0, 8))
        entry = ttk.Entry(row, width=width, show="●" if secret else "")
        entry.pack(side="left", fill="x", expand=True)
        if value:
            entry.insert(0, value)
        return entry

    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="MisePort（試作） / BASEの商品を読み取り専用で取得",
              font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))
    ttk.Label(frame, text="公式API・items.readのPATはこのPC内で一時使用し、保存しません。"
              " 商品URLはショップ側で確認したURLを登録してください。",
              wraplength=900).pack(anchor="w", pady=(0, 10))

    row1 = ttk.Frame(frame)
    row1.pack(fill="x", pady=3)
    merchant_id = label(row1, "店舗ID", "my-shop", 15)
    merchant_name = label(row1, "店舗名", "", 24)
    row2 = ttk.Frame(frame)
    row2.pack(fill="x", pady=3)
    homepage = label(row2, "店舗トップのURL", "https://", 48)
    row3 = ttk.Frame(frame)
    row3.pack(fill="x", pady=3)
    pat = label(row3, "BASE PAT", "", 48, True)

    controls = ttk.Frame(frame)
    controls.pack(fill="x", pady=8)
    status = tk.StringVar(value="未接続。公開デモにPATを送信しません。")
    btn = ttk.Button(controls, text="① BASEから商品を読み込む")
    btn.pack(side="left")
    ttk.Label(controls, textvariable=status, wraplength=680).pack(side="left", padx=12)
    csv_controls = ttk.Frame(frame)
    csv_controls.pack(fill="x", pady=4)
    ttk.Label(csv_controls, text="APIを使わない場合:").pack(side="left", padx=(0, 7))
    csv_kind = tk.StringVar(value="BASEの商品CSV")
    csv_picker = ttk.Combobox(csv_controls, width=24, state="readonly",
                              textvariable=csv_kind,
                              values=("BASEの商品CSV", "Shopifyの商品CSV"))
    csv_picker.pack(side="left")
    csv_btn = ttk.Button(csv_controls, text="商品CSVを選ぶ（読み取り専用）")
    csv_btn.pack(side="left", padx=10)
    ttk.Label(csv_controls, text="販売中・公開済み商品だけを出力対象にします。",
              wraplength=500).pack(side="left")

    tabs = ttk.Notebook(frame)
    tabs.pack(fill="both", expand=True)
    products_page = ttk.Frame(tabs, padding=8)
    mapping_page = ttk.Frame(tabs, padding=8)
    tabs.add(products_page, text="② 商品一覧")
    tabs.add(mapping_page, text="③ 商品URL・監査・出力")

    tree = ttk.Treeview(products_page, columns=("id", "name", "price", "stock", "status"),
                        show="headings", height=12)
    for name, title, width in (
        ("id", "商品ID / SKU", 125), ("name", "商品名", 360),
        ("price", "税込価格", 120), ("stock", "在庫", 70),
        ("status", "状態", 150),
    ):
        tree.heading(name, text=title)
        tree.column(name, width=width)
    tree.pack(fill="both", expand=True)

    ttk.Label(mapping_page, text="BASEの商品ページ形式（店舗URL/items/商品ID）を使って、"
              "確認済みの1商品からURL候補を一括生成できます。"
              " 候補は実際のWebアクセス検証済みではありません。"
              " 正しい店を開けるか、公開前に店主が確認してください。",
              wraplength=850).pack(anchor="w", pady=4)
    sample_row = ttk.Frame(mapping_page)
    sample_row.pack(fill="x", pady=4)
    ttk.Label(sample_row, text="実際に確認した1商品のURL:").pack(side="left", padx=(0, 7))
    sample_url = ttk.Entry(sample_row, width=48)
    sample_url.pack(side="left", fill="x", expand=True)
    candidate_buttons = ttk.Frame(mapping_page)
    candidate_buttons.pack(fill="x", pady=3)
    candidate_btn = ttk.Button(candidate_buttons, text="商品URLの候補を一括生成")
    candidate_btn.pack(side="left", padx=(0, 8))
    link_btn = ttk.Button(candidate_buttons, text="公開商品URLを最大30件確認")
    link_btn.pack(side="left")
    urls = tk.Text(mapping_page, height=8, wrap="none")
    urls.pack(fill="x", pady=6)
    link_probe_status = tk.StringVar(value="商品URLのネットワーク検査はまだ行っていません。")
    ttk.Label(mapping_page, textvariable=link_probe_status,
              wraplength=900).pack(anchor="w", pady=2)
    review_status = tk.StringVar(value="まだ商品を取得していません。")
    ttk.Label(mapping_page, textvariable=review_status, wraplength=900).pack(anchor="w", pady=6)
    output = ttk.Frame(mapping_page)
    output.pack(fill="x", pady=6)
    review_btn = ttk.Button(output, text="④ データの確認")
    review_btn.pack(side="left")
    export_btn = ttk.Button(output, text="⑤ カタログJSONを保存", state="disabled")
    export_btn.pack(side="left", padx=10)
    bundle_btn = ttk.Button(output, text="⑥ 商店用MCP/REST ZIPを生成", state="disabled")
    bundle_btn.pack(side="left", padx=10)
    guide_btn = ttk.Button(output, text="⑦ Cloudflare公開手順")
    guide_btn.pack(side="left")
    site_row = ttk.Frame(mapping_page)
    site_row.pack(fill="x", pady=5)
    ttk.Label(site_row, text="Cloudflare Pagesの公開URL:").pack(side="left", padx=(0, 7))
    target_origin = ttk.Entry(site_row, width=48)
    target_origin.pack(side="left", fill="x", expand=True)
    target_origin.insert(0, "https://your-store.pages.dev")
    live_row = ttk.Frame(mapping_page)
    live_row.pack(fill="x", pady=4)
    live_btn = ttk.Button(live_row, text="⑧ 公開後のMCP接続を確認", state="disabled")
    live_btn.pack(side="left", padx=(0, 8))
    live_status = tk.StringVar(value="ZIPを公開後にMCPとREST APIを検査できます。")
    ttk.Label(live_row, textvariable=live_status, wraplength=680).pack(side="left")
    consent = tk.BooleanVar(value=False)
    ttk.Checkbutton(mapping_page, variable=consent, text="公開商品とリンクを店主が確認し、"
                    "第三者へ配信する前に内容を再確認します。").pack(anchor="w", pady=7)
    ttk.Label(mapping_page, text="ZIPには公開商品だけを入れます。クラウドへの自動公開はしません。"
              " ZIPを商店ご自身のCloudflare Pagesにアップロードしてください。"
              " 商品の鮮度やMuseによる自動発見は保証しません。",
              wraplength=840).pack(anchor="w")

    def apply_items(received, import_context):
        nonlocal items, current, current_inputs, csv_loaded, source_mode, last_bundle, loaded_source
        if (import_context != source_at_inputs("api")):
            status.set("読み込み中に店舗情報が変更されました。新しい店舗情報で再取得してください。")
            messagebox.showwarning("店舗の確認",
                "商品を読み込んだ後に店舗情報が変わりました。誤った店の商品を"
                "公開しないため、現在の読み込み結果は破棄しました。")
            return
        items = received
        loaded_source = import_context
        source_mode = "api"
        csv_loaded = None
        current = None
        current_inputs = None
        last_bundle = None
        live_btn.configure(state="disabled")
        live_status.set("商品を公開してから接続テストを行います。")
        link_probe_status.set("商品URLのネットワーク検査はまだ行っていません。")
        export_btn.configure(state="disabled")
        bundle_btn.configure(state="disabled")
        consent.set(False)
        tree.delete(*tree.get_children())
        for item in items:
            tree.insert("", "end", values=(
                item.get("id"), item.get("name") or "（名称未登録）",
                "未設定" if item.get("price") is None else str(item.get("price")) + "円",
                item.get("stock", "?"),
                "公開中" if item.get("visible") is True else "非公開",
            ))
        status.set(str(len(items)) + "件を取得しました。商品URLを確認してください。")
        tabs.select(products_page)

    def fetch():
        nonlocal loaded_source, current, current_inputs
        token = pat.get()
        pat.delete(0, tk.END)
        if not token:
            messagebox.showwarning("認証", "ショップ所有者のBASE PATを入力してください。")
            return
        try:
            context = source_at_inputs("api")
        except SourceContextError as exc:
            messagebox.showwarning("店舗の確認", str(exc))
            return
        # A failed refresh cannot leave a previous approval available for
        # export under possibly changed shop fields.
        loaded_source = None
        current = None
        current_inputs = None
        consent.set(False)
        export_btn.configure(state="disabled")
        bundle_btn.configure(state="disabled")
        btn.configure(state="disabled")
        csv_btn.configure(state="disabled")
        status.set("BASEから取得中…この画面を閉じるとPATは保存されません。")

        def worker(one_time_token, imported_context):
            try:
                result = get_source_adapter("base").fetch_public(one_time_token)
                jobs.put(("success", (result, imported_context)))
            except BaseAPIError as error:
                jobs.put(("error", str(error)))
            except Exception:
                jobs.put(("error", "商品の取得に失敗しました。詳細は接続設定を確認してください。"))
            # This worker never persists or logs the token.
        threading.Thread(target=worker, args=(token, context), daemon=True).start()
        del token

    def poll():
        nonlocal current, current_inputs
        try:
            kind, value = jobs.get_nowait()
        except queue.Empty:
            root.after(120, poll)
            return
        if kind in ("live_result", "live_error"):
            live_btn.configure(state="normal")
            bundle_checked, data = value
            if bundle_checked != last_bundle:
                live_status.set("別のZIPが生成されました。再度接続テストしてください。")
            elif kind == "live_error":
                live_status.set(data)
                messagebox.showwarning("公開MCPの検査", data)
            else:
                live_status.set("公開先を確認しました。商品" +
                    str(data["product_count"]) + "件、MCP " +
                    str(len(data["mcp_tools"])) +
                    "ツール。実際のMuseからの発見・利用は別の検証です。")
                messagebox.showinfo("MCP/REST接続が成功しました",
                    "登録された商品情報と生成ZIPのバージョンが一致し、"
                    "MCP initialize・tools/list・get_productが成功しました。"
                    " 本番運用やMetaでの推薦を保証するものではありません。")
        elif kind in ("url_result", "url_error"):
            link_btn.configure(state="normal")
            snapshot, payload = value
            if snapshot != review_inputs():
                link_probe_status.set("検査後に入力が変わりました。もう一度確認してください。")
            elif kind == "url_error":
                link_probe_status.set(payload)
                messagebox.showwarning("商品URLの検査", payload)
            else:
                counts = payload
                link_probe_status.set(
                    "公開URL検査：" + str(counts["confirmed"]) + "件のページ確認、"
                    + str(counts["uncertain"]) + "件が要確認、"
                    + str(counts["rejected"]) + "件が閲覧不可です。"
                    " ページの事実と商品IDは店主が最後に確認してください。")
                if counts["rejected"]:
                    current = None
                    current_inputs = None
                    consent.set(False)
                    export_btn.configure(state="disabled")
                    bundle_btn.configure(state="disabled")
                    review_status.set("404等のページが含まれます。商品URLを修正して再審査してください。")
                if counts["uncertain"] or counts["rejected"]:
                    samples = ", ".join(
                        str(item["item_id"]) + " (" + item["code"] + ")"
                        for item in counts["results"] if item["state"] != "confirmed")
                    messagebox.showwarning("商品URLの検査",
                        "確実に確認できないURLがあります：\n" + samples[:700]
                        + "\n公開前に店主が修正してください。")
        else:
            btn.configure(state="normal")
            csv_btn.configure(state="normal")
            if kind == "success":
                records, context = value
                apply_items(records, context)
            else:
                status.set(value + " 直前の確認結果は無効です。再取得してください。")
                messagebox.showerror("接続エラー", value)
        root.after(120, poll)

    def review_inputs():
        return (merchant_id.get(), merchant_name.get(), homepage.get(),
                urls.get("1.0", "end").strip(), sample_url.get(),
                csv_kind.get(), source_mode)

    def load_csv():
        nonlocal current, current_inputs, csv_loaded, csv_loaded_profile, source_mode, items, last_bundle, loaded_source
        filename = filedialog.askopenfilename(title="公式商品CSVを選ぶ",
                   filetypes=[("CSVファイル", "*.csv")])
        if not filename:
            return
        if not messagebox.askyesno("CSV商品の確認",
                "店舗オーナーとして、公式の公開商品CSVと実際の公開商品URL例を確認しましたか？"
                " 商品が未公開・内部資料の場合は読み込みを取り消してください。"):
            return
        try:
            frozen_context = source_at_inputs("csv")
            profile = MerchantProfile(
                merchant_id=merchant_id.get().strip(),
                merchant_name=merchant_name.get().strip(),
                merchant_homepage=homepage.get().strip(),
                verified_product_urls={}, is_demo=False)
            if csv_kind.get() == "BASEの商品CSV":
                result = import_base_product_csv(
                    filename, profile,
                    confirmed_example_url=sample_url.get().strip(),
                    merchant_confirmed=True)
            else:
                if not messagebox.askyesno("通貨の確認",
                        "このShopifyショップの商品CSVの価格は日本円（JPY）ですか？"):
                    return
                one_location = messagebox.askyesno("在庫場所の確認",
                        "在庫を正確に扱える単一の在庫拠点のみを使用していますか？"
                        " 複数拠点または不明の場合は「いいえ」を選んでください。")
                result = import_shopify_product_csv(
                    filename, profile, confirmed_example_url=sample_url.get().strip(),
                    merchant_confirmed=True, currency_jpy=True,
                    single_location=one_location)
        except (ValueError, PlatformCSVError, OSError):
            messagebox.showerror("商品CSVを確認してください",
                "商品CSVの列・文字コード・店の公開商品URL例を確認してください。"
                " 注文/顧客CSVは利用できません。")
            return
        csv_loaded = result
        loaded_source = frozen_context
        last_bundle = None
        live_btn.configure(state="disabled")
        live_status.set("CSVを変更しました。新しいZIPを生成してから接続テストしてください。")
        csv_loaded_profile = csv_kind.get()
        source_mode = "csv"
        items = []
        current = None
        current_inputs = None
        consent.set(False)
        export_btn.configure(state="disabled")
        bundle_btn.configure(state="disabled")
        urls.delete("1.0", tk.END)
        tree.delete(*tree.get_children())
        for p in result.catalog.products:
            tree.insert("", "end", values=(
                p.sku, p.name, str(p.price_jpy) + "円",
                p.stock_quantity if p.stock_quantity is not None else "不明",
                "CSV公開候補",
            ))
        status.set("商品CSVを" + str(result.source_rows) +
                   "行読み込みました。③でデータを確認してください。"
                   " CSVの確認日時は元の更新日時と異なります。")
        review_status.set("CSVの出典、価格、公開状態、商品URLを確認してください。")
        tabs.select(mapping_page)

    def auto_urls():
        nonlocal current, current_inputs
        if source_mode != "api" or not items or not imported_for_current_shop():
            messagebox.showwarning("商品URL", "BASEから商品を読み込んでください。")
            return
        if not messagebox.askyesno("商品URLの一括生成",
                "サンプルURLを実際のショップ画面で確認しましたか？\n"
                "BASEの標準URLルールを使って候補を生成します。"
                " ほかの商品URLは必ずしもWeb実測済みではありません。"):
            return
        try:
            candidates = candidate_product_urls(items, homepage.get().strip(),
                sample_url.get().strip(), merchant_confirmed=True)
        except BaseURLValidationError as exc:
            messagebox.showerror("URLを確認してください", str(exc))
            return
        urls.delete("1.0", tk.END)
        urls.insert("1.0", "\n".join(str(k) + "=" + v
                    for k, v in sorted(candidates.items())))
        current = None
        current_inputs = None
        consent.set(False)
        export_btn.configure(state="disabled")
        bundle_btn.configure(state="disabled")
        link_probe_status.set("候補URLは推測です。必要なら「公開商品URLを確認」でネットワーク照合できます。")
        review_status.set(str(len(candidates)) + "件のURL候補を生成しました。"
            " API商品IDに基づく候補です。公開前に確認してからデータ審査を押してください。")
        tabs.select(mapping_page)

    def verify_urls():
        if source_mode != "api" or not items or not imported_for_current_shop():
            messagebox.showwarning("商品URLの検査",
                "BASE API商品を読み込み、商品URL候補を用意してください。")
            return
        try:
            addresses = parse_product_urls(urls.get("1.0", "end").strip())
            validate_manual_product_urls(addresses, homepage.get().strip())
            if not addresses or len(addresses) > MAX_URL_CHECKS:
                raise URLProbeError("一度に1〜30件のURLを検査してください。")
        except (ValueError, BaseURLValidationError, URLProbeError):
            messagebox.showwarning("商品URLの検査",
                "同じショップの公開商品URLを1〜30件入力してください。")
            return
        if not messagebox.askyesno("公開商品URLの確認",
            "店主が許可した同じショップの公開商品ページだけを検査しますか？\n"
            "最大30件、HTTPSの公開URLだけに読み取りアクセスします。"
            " BASE PATは送信しません。"
            " 運用中のショップに負荷がかからないよう必要な時だけ実行してください。"):
            return
        link_btn.configure(state="disabled")
        snapshot = review_inputs()
        saved_homepage = homepage.get().strip()
        link_probe_status.set("公開ページを確認しています。途中結果を公開することはありません。")
        def worker():
            try:
                report = check_product_urls(addresses, saved_homepage).summary()
                jobs.put(("url_result", (snapshot, report)))
            except (ValueError, OSError):
                jobs.put(("url_error", (snapshot,
                    "URLを検査できませんでした。後で再試行するか、店主自身がページを確認してください。")))
        threading.Thread(target=worker, daemon=True).start()

    def review():
        nonlocal current, current_inputs
        try:
            if not imported_for_current_shop():
                raise ValueError("店舗名・URL・CSVの種類が変わりました。商品を再読込してください。")
            if source_mode == "csv":
                if csv_loaded is None or csv_loaded_profile != csv_kind.get():
                    raise ValueError("CSVの種類を確認し、もう一度読み込んでください。")
                result = csv_loaded
            else:
                if not items:
                    raise ValueError("まずBASEから商品を取得してください。")
                result = preview_mapping(
                    items, merchant_id.get(), merchant_name.get(), homepage.get(),
                    urls.get("1.0", "end").strip(),
                )
        except (ValueError, TypeError) as error:
            review_status.set(str(error))
            export_btn.configure(state="disabled")
            bundle_btn.configure(state="disabled")
            current = None
            current_inputs = None
            return
        current = result
        current_inputs = review_inputs()
        consent.set(False)
        summary = result.summary()
        message = (str(summary["mapped_products"]) + "件の公開候補。"
                   + str(len(summary["issues"])) + "件の確認事項。")
        if summary["issues"]:
            message += " " + " / ".join(x["code"] + ": " + x["message"]
                                      for x in summary["issues"][:5])
        review_status.set(message)
        export_btn.configure(state="normal" if result.publishable else "disabled")
        bundle_btn.configure(state="normal" if result.publishable else "disabled")

    def save():
        if (current is None or not current.publishable or
                current_inputs != review_inputs() or not imported_for_current_shop()):
            messagebox.showwarning("確認", "商品情報をすべて確認してください。")
            return
        if not consent.get():
            messagebox.showwarning("確認", "公開範囲の確認にチェックしてください。")
            return
        filename = filedialog.asksaveasfilename(
            title="カタログJSONを保存", defaultextension=".json",
            filetypes=[("JSON", "*.json")], initialfile="miseport-catalog.json")
        if filename:
            path = Path(filename)
            try:
                old = load_catalog(path) if path.exists() else None
                changes = plan_refresh(old, current)
                approve_removed = False
                if changes.removed:
                    approve_removed = messagebox.askyesno(
                        "削除される商品を確認",
                        str(len(changes.removed)) + "件が今回の公開対象から削除されます。"
                        "前回のファイルは、新しい完全な情報で置き換えられます。"
                        "削除を承認しますか？"
                    )
                    if not approve_removed:
                        return
                commit_refresh(path, current, approve_removed=approve_removed)
            except (OSError, ValueError, RefreshError):
                messagebox.showerror("保存失敗",
                    "保存先・店舗情報・前回のカタログを確認してください。"
                    " 古い正常なファイルを勝手に上書きしません。")
            else:
                messagebox.showinfo("保存しました",
                    "追加" + str(len(changes.added)) + "件 / "
                    "変更" + str(len(changes.changed)) + "件 / "
                    "削除" + str(len(changes.removed)) + "件。\n"
                    "ローカルに完全な商品カタログを保存しました。"
                    " 公開済みクラウドは自動更新されません。")

    def save_bundle():
        nonlocal last_bundle
        if (current is None or not current.publishable or not consent.get()
                or current_inputs != review_inputs() or not imported_for_current_shop()):
            messagebox.showwarning("確認", "公開対象と商品URLを店主が確認してください。")
            return
        name = filedialog.asksaveasfilename(
            title="商店用ZIPを保存", defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")], initialfile="miseport-merchant-pages.zip")
        if not name:
            return
        try:
            meta = build_merchant_zip(current.catalog, name,
                origin=target_origin.get().strip(),
                merchant_approved=True, demo_mode=False)
        except (PublicationError, OSError, ValueError):
            messagebox.showerror("生成失敗",
                "配信URLや商品情報を確認してください。古いファイルは変更していません。")
        else:
            first_product = current.catalog.products[0]
            last_bundle = (
                str(name), target_origin.get().strip(),
                meta["snapshot_generated_at"], meta["product_count"],
                first_product.sku, first_product.source_url, first_product.price_jpy,
            )
            live_btn.configure(state="normal")
            live_status.set("商店自身のCloudflareへアップロード後、ここでMCP接続を確認できます。")
            messagebox.showinfo("ZIPを生成しました",
                str(meta["product_count"]) + "件の公開商品を保存しました。\n"
                "このZIPはまだWebへ公開されていません。"
                "「⑦ Cloudflare公開手順」からアップロード方法を確認してください。")

    def show_deploy_guide():
        if last_bundle is None:
            messagebox.showwarning("公開手順",
                "先に商品を審査し、「⑥ 商店用MCP/REST ZIPを生成」で"
                "ZIPファイルを保存してください。")
            return
        filepath, origin, *_ = last_bundle
        try:
            guide = merchant_deploy_guide(origin)
        except DeploymentGuideError as exc:
            messagebox.showerror("公開先", str(exc))
            return
        dialog = tk.Toplevel(root)
        dialog.title("MisePort — Cloudflare Pages 公開の手順")
        dialog.geometry("850x560")
        dialog.transient(root)
        layout = ttk.Frame(dialog, padding=14)
        layout.pack(fill="both", expand=True)
        ttk.Label(layout, text="このZIPを店主ご自身のCloudflareに公開します",
                  font=("", 12, "bold")).pack(anchor="w", pady=(0, 7))
        ttk.Label(layout, text="保存したZIP: " + Path(filepath).name,
                  wraplength=770).pack(anchor="w")
        guide_text = tk.Text(layout, wrap="word", width=94, height=19, padx=9, pady=9)
        guide_text.pack(fill="both", expand=True, pady=9)
        guide_text.insert("1.0", "\n\n".join(guide.steps_ja) + "\n\n"
                          "公開予定のMCP: " + guide.mcp_url
                          + "\n確認用: " + guide.health_url
                          + "\n商品API: " + guide.origin + "/api/products\n"
                          "注意: ZIP生成とオンライン稼働は別です。"
                          " 最終的なHTTPSとMCPを実際のクライアントで確認してください。")
        guide_text.configure(state="disabled")
        links = ttk.Frame(layout)
        links.pack(fill="x", pady=6)
        ttk.Button(links, text="Cloudflare管理画面を開く",
            command=lambda: webbrowser.open(guide.dashboard_url)).pack(side="left", padx=4)
        ttk.Button(links, text="Cloudflare公式手順",
            command=lambda: webbrowser.open(guide.docs_url)).pack(side="left", padx=4)
        def copy_mcp():
            dialog.clipboard_clear()
            dialog.clipboard_append(guide.mcp_url)
            dialog.update_idletasks()
            messagebox.showinfo("コピーしました",
                "公開予定のMCP URLをコピーしました。オンライン接続は別途確認してください。",
                parent=dialog)
        ttk.Button(links, text="MCP URLをコピー",
                   command=copy_mcp).pack(side="left", padx=4)
        ttk.Button(links, text="閉じる", command=dialog.destroy).pack(side="right", padx=4)

    def verify_live():
        if last_bundle is None:
            messagebox.showwarning("公開の確認", "まず商店用のZIPを生成してください。")
            return
        if not messagebox.askyesno("公開先のMCPを確認",
            "商店自身がCloudflareへZIPをアップロードした後、公開HTTPSサイトへ"
            "商品APIとMCPの読み取り要求を送ります。"
            " BASE PATやCloudflare認証情報は送信しません。実行しますか？"):
            return
        selected = last_bundle
        live_btn.configure(state="disabled")
        live_status.set("指定した公開先でMCPと商品データを確認しています。")

        def worker():
            try:
                path, origin, stamp, count, sku, source_url, price = selected
                local = inspect_merchant_zip(path, expected_origin=origin)
                if (local["product_count"] != count
                        or local["snapshot_generated_at"] != stamp):
                    raise DeploymentCheckError("保存済みZIPが前回の内容と一致しません。")
                report = check_live_merchant_deployment(
                    origin, expected_snapshot_at=stamp,
                    expected_product_count=count, expected_sku=sku,
                    expected_source_url=source_url, expected_price_jpy=price,
                ).summary()
                jobs.put(("live_result", (selected, report)))
            except (DeploymentCheckError, BundleVerificationError, ValueError, OSError):
                jobs.put(("live_error", (selected,
                    "公開先がZIPと一致しないか、MCPに接続できませんでした。"
                    " CloudflareのURL、ZIPの再デプロイ、/healthzを確認してください。")))
        threading.Thread(target=worker, daemon=True).start()

    btn.configure(command=fetch)
    live_btn.configure(command=verify_live)
    csv_btn.configure(command=load_csv)
    candidate_btn.configure(command=auto_urls)
    link_btn.configure(command=verify_urls)
    guide_btn.configure(command=show_deploy_guide)
    bundle_btn.configure(command=save_bundle)
    review_btn.configure(command=review)
    export_btn.configure(command=save)
    root.after(120, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
