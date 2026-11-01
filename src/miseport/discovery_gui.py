"""Optional Japanese Discovery Readiness window for reviewed merchant catalogs.

No network access, vendor submissions or changes to the source catalog.
Tkinter is only imported when the GUI is opened; logic is headless-testable.
"""
from __future__ import annotations

from pathlib import Path

from .core import Catalog
from .discovery import DiscoveryProfile, assess_discovery, _profile_from_file
from .google_feed import inspect_google, google_csv
from .feed_common import atomic_bytes
from .openai_feed import inspect_openai, openai_preview_gzip


def discovery_view(catalog: Catalog, profile: DiscoveryProfile | None = None) -> dict:
    """Compute local-readiness diagnostics without any upload or external calls."""
    readiness = assess_discovery(catalog, profile)
    google = inspect_google(catalog, profile) if profile is not None else None
    openai = inspect_openai(catalog, profile) if profile is not None else None
    errors = {}
    for name, result in (("google", google), ("openai", openai)):
        errors[name] = {
            entry["sku"]: tuple(entry["codes"]) for entry in (result or {}).get("issues", [])
        }
    rows = []
    for row in readiness["products"]:
        sku = row["sku"]
        flags = row["channels"]
        rows.append({
            "sku": sku,
            "google": "要確認" if (errors["google"].get(sku)
                      if google is not None else not flags[
                        "google_merchant_feed_preflight"]["local_fields_complete"]
                      ) else "項目確認済",
            "openai": "要確認" if (errors["openai"].get(sku)
                      if openai is not None else not flags[
                        "openai_stable_feed_preflight"]["local_fields_complete"]
                      ) else "項目確認済",
            "google_issues": (errors["google"].get(sku)
                             if google is not None else tuple(flags[
                                "google_merchant_feed_preflight"]["blocking_codes"])) or (),
            "openai_issues": (errors["openai"].get(sku)
                             if openai is not None else tuple(flags[
                                "openai_stable_feed_preflight"]["blocking_codes"])) or (),
        })
    return {
        "scope": "local_readiness_only",
        "submitted": False, "indexed": None, "agent_discovered": None,
        "product_count": len(rows), "rows": rows,
        "profile_loaded": profile is not None,
        "google_export_blocked": (google is None or google["blocked_rows"] > 0),
        "openai_preview_blocked": (openai is None or openai["blocked_rows"] > 0),
        "readiness": readiness,
    }


def open_discovery_window(parent, catalog: Catalog, *,
                          is_current, is_approved):
    """Launch a child dialog. is_current closes stale-context export paths."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    dialog = tk.Toplevel(parent)
    dialog.title("MisePort — AI商品発見の準備状況（Alpha）")
    dialog.geometry("960x650")
    dialog.minsize(760, 490)
    dialog.transient(parent)

    view_catalog = Catalog([p.model_copy(deep=True) for p in catalog.products],
                           metadata=dict(catalog.metadata))
    selected_profile = None
    loaded_label = tk.StringVar(value="ブランド情報: 未指定（商店名から推定しません）")
    message = tk.StringVar(value="ローカル診断のみ。Google/ChatGPTへの掲載確認ではありません。")

    outer = ttk.Frame(dialog, padding=14)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="AI検索・商品掲載の準備状況",
              font=("", 13, "bold")).pack(anchor="w")
    ttk.Label(outer, text="商品データの項目と不足を診断します。"
              " 結果は送信・掲載・インデックス・AI推薦を意味しません。",
              wraplength=880).pack(anchor="w", pady=(6, 10))
    buttons = ttk.Frame(outer)
    buttons.pack(fill="x", pady=6)
    ttk.Label(outer, textvariable=loaded_label,
              wraplength=850).pack(anchor="w", pady=(0, 8))

    results = ttk.Treeview(outer, columns=("sku", "google", "openai"),
                           show="headings", height=10)
    for key, name, width in (("sku", "SKU", 200),
                             ("google", "Google CSV（項目診断）", 260),
                             ("openai", "OpenAI Preview（項目診断）", 270)):
        results.heading(key, text=name)
        results.column(key, width=width)
    results.pack(fill="both", expand=True)
    issues_box = tk.Text(outer, height=6, wrap="word")
    issues_box.pack(fill="x", pady=8)
    issues_box.configure(state="disabled")
    summary = tk.StringVar()
    ttk.Label(outer, textvariable=summary, wraplength=860).pack(anchor="w")
    ttk.Label(outer, textvariable=message, wraplength=860).pack(anchor="w", pady=(5, 8))

    def display_issues(_event=None):
        sel = results.selection()
        if not sel:
            return
        sku = sel[0]
        row = next((x for x in current_view["rows"] if x["sku"] == sku), None)
        if row is None:
            return
        txt = ("SKU: " + sku + "\nGoogle: " +
               (", ".join(row["google_issues"]) or "ローカル項目は確認済") +
               "\nOpenAI: " +
               (", ".join(row["openai_issues"]) or "ローカル項目は確認済"))
        issues_box.configure(state="normal")
        issues_box.delete("1.0", tk.END)
        issues_box.insert("1.0", txt)
        issues_box.configure(state="disabled")
    results.bind("<<TreeviewSelect>>", display_issues)

    current_view = {}

    def redraw():
        nonlocal current_view
        current_view = discovery_view(view_catalog, selected_profile)
        results.delete(*results.get_children())
        for row in current_view["rows"]:
            results.insert("", "end", iid=row["sku"],
                           values=(row["sku"], row["google"], row["openai"]))
        google_ready = sum(not row["google_issues"] for row in current_view["rows"])
        openai_ready = sum(not row["openai_issues"] for row in current_view["rows"])
        summary.set("全" + str(current_view["product_count"]) +
                    "件｜Google必要項目: " + str(google_ready) +
                    "件｜OpenAI必要項目: " + str(openai_ready) +
                    "件（いずれも掲載・提出資格の確認ではありません）")
        google_btn.configure(state="normal" if not current_view[
            "google_export_blocked"] else "disabled")
        openai_btn.configure(state="normal" if not current_view[
            "openai_preview_blocked"] else "disabled")
        if results.get_children():
            results.selection_set(results.get_children()[0])
            display_issues()

    def select_profile():
        nonlocal selected_profile
        if not is_current():
            messagebox.showwarning("店舗情報", "商品が変更されました。改めてデータ確認してください。",
                                   parent=dialog)
            return
        name = filedialog.askopenfilename(
            parent=dialog, title="店主が確認したDiscovery Profile",
            filetypes=[("JSON", "*.json")])
        if not name:
            return
        try:
            candidate = _profile_from_file(name)
            discovery_view(view_catalog, candidate)
        except (OSError, ValueError) as error:
            messagebox.showwarning("プロフィールを確認",
                "店舗ID、SKU、ブランドの確認状況、JSON形式を確認してください。",
                parent=dialog)
            return
        selected_profile = candidate
        loaded_label.set("店主確認済みのDiscovery Profile: " + Path(name).name)
        redraw()

    def export(which):
        if not is_current():
            messagebox.showwarning("再審査", "商品・店舗・URLが変更されました。"
                "変更後の商品データを再確認してください。", parent=dialog)
            return
        if not is_approved():
            messagebox.showwarning("店主の確認", "出力前に元の画面で"
                "公開範囲の確認にチェックしてください。", parent=dialog)
            return
        if selected_profile is None:
            messagebox.showwarning("ブランド確認", "店主が確認したブランド情報を読み込んでください。",
                                   parent=dialog)
            return
        try:
            if which == "google":
                data = google_csv(inspect_google(view_catalog, selected_profile))
                suffix, title = ".csv", "Google商品CSVを保存（自動送信なし）"
                suggested = "google-merchant-jp.csv"
            else:
                data = openai_preview_gzip(inspect_openai(view_catalog, selected_profile))
                suffix, title = ".preview.jsonl.gz", "OpenAI商品データのプレビューを保存"
                suggested = "openai-products.preview.jsonl.gz"
        except ValueError:
            messagebox.showwarning("データ不足", "未確認商品があります。"
                "SKU別の確認項目を修正してください。", parent=dialog)
            redraw()
            return
        filename = filedialog.asksaveasfilename(
            parent=dialog, title=title, initialfile=suggested,
            defaultextension=suffix,
            filetypes=[("対応ファイル", "*" + suffix)])
        if not filename:
            return
        if which == "openai" and not filename.endswith(".preview.jsonl.gz"):
            messagebox.showwarning("保存形式", "OpenAIプレビューの拡張子は"
                ".preview.jsonl.gz としてください。", parent=dialog)
            return
        # Verify again after the save dialog (which can stay open while inputs
        # on the parent change), before touching an existing file.
        if not is_current() or not is_approved():
            messagebox.showwarning("再審査", "店舗の情報または公開確認が変更されました。"
                "再確認してから出力してください。", parent=dialog)
            return
        try:
            atomic_bytes(filename, data)
        except (OSError, ValueError):
            messagebox.showerror("保存失敗", "保存先を確認してください。"
                "既存ファイルは変更していません。", parent=dialog)
            return
        message.set("ローカルに保存しました。Google/ChatGPTへは送信していません。")
        messagebox.showinfo("保存完了", "ファイルを保存しました。"
            "プラットフォームの掲載・承認・AI推薦は未検証です。", parent=dialog)

    ttk.Button(buttons, text="店主確認済みブランドJSONを選択",
               command=select_profile).pack(side="left", padx=(0, 8))
    google_btn = ttk.Button(buttons, text="Google商品CSVを保存",
                            command=lambda: export("google"), state="disabled")
    google_btn.pack(side="left", padx=(0, 8))
    openai_btn = ttk.Button(buttons, text="OpenAIプレビューを保存",
                            command=lambda: export("openai"), state="disabled")
    openai_btn.pack(side="left")
    ttk.Button(outer, text="閉じる", command=dialog.destroy).pack(anchor="e")
    redraw()
    return dialog
