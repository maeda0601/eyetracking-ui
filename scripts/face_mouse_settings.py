# -*- coding: utf-8 -*-
"""顔マウスの設定画面（tkinter）

    uv run scripts/face_mouse_settings.py

本体（face_mouse.py）を起動していなくても使える。保存すると設定ファイル
（scripts/face_mouse_config.json）に書き込み、本体が動作中なら約1秒で反映される
（カメラ番号など一部の項目は顔マウスの再起動が必要）。
"""

import ctypes
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import settings_schema as schema

# ============================================================
# パラメータ
# ============================================================

WINDOW_TITLE = "顔マウス 設定"
WINDOW_SIZE = "760x640"
FONT_FAMILY = "Meiryo UI"
LABEL_FONT = (FONT_FAMILY, 10, "bold")
DESC_FONT = (FONT_FAMILY, 9)
BODY_FONT = (FONT_FAMILY, 10)
DESC_COLOR = "#5b6470"
CHANGED_COLOR = "#1d6fb8"       # 既定値から変えた項目の名前の色
RESTART_COLOR = "#9a5b00"       # 「再起動で反映」の色
DESC_WRAP_PX = 640              # 説明文を折り返す幅


def enable_dpi_awareness():
    """高DPI環境で文字がぼやけないようにする（Windowsのみ。失敗しても動作は続ける）"""
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError) as e:
        print("注意: DPI設定を変更できませんでした（表示がぼやける場合があります）: {}".format(e))


def format_number(item, value):
    """数値を刻みに合った桁数の文字列にする"""
    if item["type"] == "int":
        return str(int(value))
    step_text = repr(float(item["step"]))
    decimals = len(step_text.split(".")[1].rstrip("0")) if "." in step_text else 0
    return "{:.{}f}".format(value, max(decimals, 1))


class SettingRow:
    """1項目分の入力欄（項目名・スライダー／チェック・数値欄・説明）

    同じ項目を複数のタブに出す場合も、値は SettingsApp.values で共有する。
    """

    def __init__(self, parent, item, app):
        self.item = item
        self.app = app
        self.ready = False   # 初回表示が済むまでスライダーの変更通知を無視する
        self.frame = ttk.Frame(parent, padding=(4, 6))
        self.frame.columnconfigure(0, weight=1)

        title = item["label"]
        if item.get("restart"):
            title += "　※再起動で反映"
        self.label = tk.Label(self.frame, text=title, font=LABEL_FONT, anchor="w")
        self.label.grid(row=0, column=0, columnspan=2, sticky="w")

        if item["type"] == "bool":
            self.bool_var = tk.BooleanVar()
            check = ttk.Checkbutton(self.frame, text="オン", variable=self.bool_var,
                                    command=self._on_bool_changed)
            check.grid(row=1, column=0, sticky="w", pady=(2, 0))
        else:
            self.scale_var = tk.DoubleVar()
            self.text_var = tk.StringVar()
            scale = tk.Scale(self.frame, from_=item["min"], to=item["max"],
                             resolution=item["step"], orient=tk.HORIZONTAL, showvalue=False,
                             variable=self.scale_var, command=self._on_scale_moved,
                             highlightthickness=0)
            scale.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            entry = ttk.Entry(self.frame, textvariable=self.text_var, width=10, font=BODY_FONT,
                              justify="right")
            entry.grid(row=1, column=1, sticky="e", padx=(10, 0))
            # 直接入力は Enter かフォーカスを外したときに確定する
            entry.bind("<Return>", self._on_text_entered)
            entry.bind("<FocusOut>", self._on_text_entered)

        range_text = ""
        if item["type"] != "bool":
            range_text = "（範囲 {}〜{}、既定値 {}）".format(
                format_number(item, item["min"]), format_number(item, item["max"]),
                format_number(item, app.defaults[item["key"]]))
        else:
            range_text = "（既定値 {}）".format("オン" if app.defaults[item["key"]] else "オフ")
        desc = tk.Label(self.frame, text=item["desc"] + range_text, font=DESC_FONT,
                        fg=DESC_COLOR, anchor="w", justify="left", wraplength=DESC_WRAP_PX)
        desc.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def refresh(self):
        """共有している値を表示に反映する"""
        key = self.item["key"]
        value = self.app.values[key]
        if self.item["type"] == "bool":
            self.bool_var.set(value)
        else:
            self.scale_var.set(value)
            self.text_var.set(format_number(self.item, value))
        self.ready = True
        changed = value != self.app.defaults[key]
        if self.item.get("restart"):
            self.label.configure(fg=RESTART_COLOR if changed else "black")
        else:
            self.label.configure(fg=CHANGED_COLOR if changed else "black")

    def _on_bool_changed(self):
        self.app.set_value(self.item["key"], self.bool_var.get())

    def _on_scale_moved(self, _text):
        if not self.ready:
            return
        key = self.item["key"]
        value = schema.normalize_value(key, self.scale_var.get())
        if value != self.app.values[key]:
            self.app.set_value(key, value)

    def _on_text_entered(self, _event):
        key = self.item["key"]
        try:
            value = schema.normalize_value(key, float(self.text_var.get()))
        except ValueError:
            # 数値として読めない入力は、元の値に戻す
            self.app.set_status("「{}」には数値を入力してください。".format(self.item["label"]))
            self.refresh()
            return
        self.app.set_value(key, value)


class SettingsApp:
    """設定画面のウィンドウ"""

    def __init__(self, root):
        self.root = root
        self.defaults = schema.load_defaults()
        saved = schema.load_config()
        self.values = dict(self.defaults)
        self.values.update(saved)
        self.saved_values = dict(self.values)
        self.rows = []

        root.title(WINDOW_TITLE)
        root.geometry(WINDOW_SIZE)
        root.minsize(560, 420)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        style = ttk.Style(root)
        style.configure(".", font=BODY_FONT)
        style.configure("TNotebook.Tab", padding=(10, 4))

        header = ttk.Frame(root, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        tk.Label(header, font=DESC_FONT, fg=DESC_COLOR, anchor="w", justify="left",
                 text="保存すると、動作中の顔マウスにそのまま反映されます（「※再起動で反映」の項目を除く）。\n"
                      "既定値から変えた項目は名前が青く表示されます。").pack(fill="x")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)
        for tab in schema.TABS:
            if tab == "よく使う":
                items = [schema.SCHEMA_BY_KEY[key] for key in schema.FAVORITE_KEYS]
            else:
                items = [item for item in schema.SCHEMA if item["tab"] == tab]
            self._build_tab(tab, items)

        footer = ttk.Frame(root, padding=(12, 0, 12, 10))
        footer.pack(fill="x")
        ttk.Button(footer, text="このタブを既定値に戻す",
                   command=self.reset_current_tab).pack(side="left")
        ttk.Button(footer, text="すべて既定値に戻す",
                   command=self.reset_all).pack(side="left", padx=(6, 0))
        ttk.Button(footer, text="閉じる", command=self.on_close).pack(side="right")
        ttk.Button(footer, text="保存", command=self.save).pack(side="right", padx=(0, 6))

        self.status_var = tk.StringVar()
        tk.Label(root, textvariable=self.status_var, font=DESC_FONT, fg=DESC_COLOR,
                 anchor="w").pack(fill="x", padx=14, pady=(0, 8))

        self.refresh_all()
        if saved:
            self.set_status("設定ファイルを読み込みました: {}".format(schema.CONFIG_PATH))
        else:
            self.set_status("設定ファイルはまだありません（すべて既定値）。保存すると作成されます。")

    def _build_tab(self, tab, items):
        """スクロールできるタブを作り、項目を並べる"""
        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text=tab)
        canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, padding=(8, 4))
        inner.columnconfigure(0, weight=1)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
        # タブ上でマウスホイールを回したらスクロールする
        canvas.bind("<Enter>", lambda e: canvas.bind_all(
            "<MouseWheel>", lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        for i, item in enumerate(items):
            row = SettingRow(inner, item, self)
            row.frame.grid(row=i * 2, column=0, sticky="ew")
            ttk.Separator(inner).grid(row=i * 2 + 1, column=0, sticky="ew", pady=2)
            row.tab = tab
            self.rows.append(row)

    def set_value(self, key, value):
        """値を変更し、同じ項目を表示している欄をすべて更新する"""
        self.values[key] = value
        for row in self.rows:
            if row.item["key"] == key:
                row.refresh()
        self._update_title()

    def refresh_all(self):
        for row in self.rows:
            row.refresh()
        self._update_title()

    def is_dirty(self):
        """未保存の変更があるか"""
        return self.values != self.saved_values

    def _update_title(self):
        self.root.title(WINDOW_TITLE + ("（未保存の変更あり）" if self.is_dirty() else ""))

    def set_status(self, text):
        self.status_var.set(text)

    def reset_current_tab(self):
        tab = self.notebook.tab(self.notebook.select(), "text")
        keys = {row.item["key"] for row in self.rows if row.tab == tab}
        for key in keys:
            self.values[key] = self.defaults[key]
        self.refresh_all()
        self.set_status("「{}」タブを既定値に戻しました（まだ保存していません）。".format(tab))

    def reset_all(self):
        if not messagebox.askyesno(WINDOW_TITLE, "すべての項目を既定値に戻しますか？\n（保存するまで反映されません）",
                                   parent=self.root):
            return
        self.values = dict(self.defaults)
        self.refresh_all()
        self.set_status("すべて既定値に戻しました（まだ保存していません）。")

    def save(self):
        # 入力途中の数値欄を確定させてから保存する
        self.root.focus_set()
        self.root.update_idletasks()
        try:
            schema.save_config(self.values)
        except OSError as e:
            messagebox.showerror(WINDOW_TITLE, "保存できませんでした。\n{}".format(e), parent=self.root)
            return
        restart_changed = [
            schema.SCHEMA_BY_KEY[key]["label"] for key in self.values
            if schema.SCHEMA_BY_KEY[key].get("restart") and self.values[key] != self.saved_values.get(key)
        ]
        self.saved_values = dict(self.values)
        self._update_title()
        msg = "保存しました。動作中の顔マウスに反映されます。"
        if restart_changed:
            msg += "（{} は顔マウスの再起動後に反映）".format("、".join(restart_changed))
        self.set_status(msg)

    def on_close(self):
        if self.is_dirty():
            answer = messagebox.askyesnocancel(WINDOW_TITLE, "変更が保存されていません。保存して閉じますか？",
                                               parent=self.root)
            if answer is None:
                return
            if answer:
                self.save()
                if self.is_dirty():
                    return  # 保存に失敗した場合は閉じない
        self.root.destroy()


def main():
    enable_dpi_awareness()
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print("設定画面を開けませんでした（tkinter が使えません）: {}".format(e))
        return 1
    try:
        SettingsApp(root)
    except (OSError, ValueError) as e:
        messagebox.showerror(WINDOW_TITLE, "設定画面を開けませんでした。\n{}".format(e))
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
