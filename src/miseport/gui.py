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

from .base_v2 import BaseV2Client, BaseAPIError, map_base_items
from .importers import save_catalog


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
    return map_base_items(
        items,
        merchant_id=merchant_id.strip(), merchant_name=merchant_name.strip(),
        merchant_homepage=merchant_homepage.strip(),
        source_urls=parse_product_urls(url_lines), is_demo=is_demo,
        snapshot_at=datetime.now(timezone.utc),
    )


def main():
    """Open a local window only. Never starts an HTTP listener or stores a token."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("MisePort — お店の商品をAIへ")
    root.geometry("1000x690")
    root.minsize(780, 540)

    jobs = queue.Queue()
    items = []
    current = None

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

    tabs = ttk.Notebook(frame)
    tabs.pack(fill="both", expand=True)
    products_page = ttk.Frame(tabs, padding=8)
    mapping_page = ttk.Frame(tabs, padding=8)
    tabs.add(products_page, text="② 商品一覧")
    tabs.add(mapping_page, text="③ 商品URL・監査・出力")

    tree = ttk.Treeview(products_page, columns=("id", "name", "price", "stock", "status"),
                        show="headings", height=12)
    for name, title, width in (
        ("id", "BASE ID", 85), ("name", "商品名", 360),
        ("price", "税込価格", 120), ("stock", "在庫", 70),
        ("status", "状態", 150),
    ):
        tree.heading(name, text=title)
        tree.column(name, width=width)
    tree.pack(fill="both", expand=True)

    ttk.Label(mapping_page, text="公開する商品のURLを確認して入力してください。"
              " 1行につき「商品ID=https://実際の商品ページ」を指定します。"
              " APIの管理用リンクから推測したURLは使いません。",
              wraplength=850).pack(anchor="w", pady=4)
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
    consent = tk.BooleanVar(value=False)
    ttk.Checkbutton(mapping_page, variable=consent, text="公開商品とリンクを店主が確認し、"
                    "第三者へ配信する前に内容を再確認します。").pack(anchor="w", pady=7)
    ttk.Label(mapping_page, text="このバージョンは「JSONのローカル保存」までです。"
              " MCP公開・商品ページSEO改善・商店別クラウド配信は別途検証が必要です。",
              wraplength=840).pack(anchor="w")

    def apply_items(received):
        nonlocal items, current
        items = received
        current = None
        export_btn.configure(state="disabled")
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
                result = BaseV2Client().fetch_items(one_time_token)
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

    def review():
        nonlocal current
        try:
            if not items:
                raise ValueError("まずBASEから商品を取得してください。")
            result = preview_mapping(
                items, merchant_id.get(), merchant_name.get(), homepage.get(),
                urls.get("1.0", "end").strip(),
            )
        except (ValueError, TypeError) as error:
            review_status.set(str(error))
            export_btn.configure(state="disabled")
            current = None
            return
        current = result
        summary = result.summary()
        message = (str(summary["mapped_products"]) + "件の公開候補。"
                   + str(len(summary["issues"])) + "件の確認事項。")
        if summary["issues"]:
            message += " " + " / ".join(x["code"] + ": " + x["message"]
                                      for x in summary["issues"][:5])
        review_status.set(message)
        export_btn.configure(state="normal" if result.publishable else "disabled")

    def save():
        if current is None or not current.publishable:
            messagebox.showwarning("確認", "商品情報をすべて確認してください。")
            return
        if not consent.get():
            messagebox.showwarning("確認", "公開範囲の確認にチェックしてください。")
            return
        filename = filedialog.asksaveasfilename(
            title="カタログJSONを保存", defaultextension=".json",
            filetypes=[("JSON", "*.json")], initialfile="miseport-catalog.json")
        if filename:
            try:
                save_catalog(current.catalog, Path(filename))
            except (OSError, ValueError):
                messagebox.showerror("保存失敗", "保存できませんでした。保存先を確認してください。")
            else:
                messagebox.showinfo("保存しました", "ローカルのJSONに保存しました。\n"
                    "これはクラウド公開やリアルタイム同期を意味しません。")

    btn.configure(command=fetch)
    review_btn.configure(command=review)
    export_btn.configure(command=save)
    root.after(120, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
