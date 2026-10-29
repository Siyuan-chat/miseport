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
from .platform_csv import (
    PlatformCSVError, import_base_product_csv, import_shopify_product_csv
)
from .importers import load_catalog
from .refresh import commit_refresh, plan_refresh, RefreshError
from .publisher import PublicationError, build_merchant_zip
from .base_urls import (
    BaseURLValidationError, candidate_product_urls, validate_manual_product_urls
)


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
    candidate_btn = ttk.Button(mapping_page, text="商品URLの候補を一括生成")
    candidate_btn.pack(anchor="w", pady=3)
    urls = tk.Text(mapping_page, height=8, wrap="none")
    urls.pack(fill="x", pady=6)
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
    site_row = ttk.Frame(mapping_page)
    site_row.pack(fill="x", pady=5)
    ttk.Label(site_row, text="Cloudflare Pagesの公開URL:").pack(side="left", padx=(0, 7))
    target_origin = ttk.Entry(site_row, width=48)
    target_origin.pack(side="left", fill="x", expand=True)
    target_origin.insert(0, "https://your-store.pages.dev")
    consent = tk.BooleanVar(value=False)
    ttk.Checkbutton(mapping_page, variable=consent, text="公開商品とリンクを店主が確認し、"
                    "第三者へ配信する前に内容を再確認します。").pack(anchor="w", pady=7)
    ttk.Label(mapping_page, text="ZIPには公開商品だけを入れます。クラウドへの自動公開はしません。"
              " ZIPを商店ご自身のCloudflare Pagesにアップロードしてください。"
              " 商品の鮮度やMuseによる自動発見は保証しません。",
              wraplength=840).pack(anchor="w")

    def apply_items(received):
        nonlocal items, current, current_inputs, csv_loaded, source_mode
        items = received
        source_mode = "api"
        csv_loaded = None
        current = None
        current_inputs = None
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
        token = pat.get()
        pat.delete(0, tk.END)
        if not token:
            messagebox.showwarning("認証", "ショップ所有者のBASE PATを入力してください。")
            return
        btn.configure(state="disabled")
        status.set("BASEから取得中…この画面を閉じるとPATは保存されません。")

        def worker(one_time_token):
            try:
                result = get_source_adapter("base").fetch_public(one_time_token)
                jobs.put(("success", result))
            except BaseAPIError as error:
                jobs.put(("error", str(error)))
            except Exception:
                jobs.put(("error", "商品の取得に失敗しました。詳細は接続設定を確認してください。"))
            # This worker never persists or logs the token.
        threading.Thread(target=worker, args=(token,), daemon=True).start()
        del token

    def poll():
        try:
            kind, value = jobs.get_nowait()
        except queue.Empty:
            root.after(120, poll)
            return
        btn.configure(state="normal")
        if kind == "success":
            apply_items(value)
        else:
            status.set(value)
            messagebox.showerror("接続エラー", value)
        root.after(120, poll)

    def review_inputs():
        return (merchant_id.get(), merchant_name.get(), homepage.get(),
                urls.get("1.0", "end").strip(), sample_url.get(),
                csv_kind.get(), source_mode)

    def load_csv():
        nonlocal current, current_inputs, csv_loaded, csv_loaded_profile, source_mode, items
        filename = filedialog.askopenfilename(title="公式商品CSVを選ぶ",
                   filetypes=[("CSVファイル", "*.csv")])
        if not filename:
            return
        if not messagebox.askyesno("CSV商品の確認",
                "店舗オーナーとして、公式の公開商品CSVと実際の公開商品URL例を確認しましたか？"
                " 商品が未公開・内部資料の場合は読み込みを取り消してください。"):
            return
        try:
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
        if source_mode != "api" or not items:
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
        review_status.set(str(len(candidates)) + "件のURL候補を生成しました。"
            " API商品IDに基づく候補です。公開前に確認してからデータ審査を押してください。")
        tabs.select(mapping_page)

    def review():
        nonlocal current, current_inputs
        try:
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
        if current is None or not current.publishable or current_inputs != review_inputs():
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
        if (current is None or not current.publishable or not consent.get()
                or current_inputs != review_inputs()):
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
            messagebox.showinfo("ZIPを生成しました",
                str(meta["product_count"]) + "件の公開商品を保存しました。\n"
                "このZIPはまだWebへ公開されていません。"
                " 商店のCloudflare Pagesで手動配置とURL確認が必要です。")

    btn.configure(command=fetch)
    csv_btn.configure(command=load_csv)
    candidate_btn.configure(command=auto_urls)
    bundle_btn.configure(command=save_bundle)
    review_btn.configure(command=review)
    export_btn.configure(command=save)
    root.after(120, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
