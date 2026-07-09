"""Componentes reutilizaveis de interface."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

from app.ui.window_icon import apply_window_icon


class ScrollableFrame(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, background="white")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas, padding=12)
        self.window_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y", padx=(6, 0))

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_body_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if self.winfo_containing(event.x_root, event.y_root) is not None:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def help_label(parent, text: str, wraplength: int = 780):
    return ttk.Label(parent, text=text, bootstyle="secondary", wraplength=wraplength, justify="left", anchor="w")


def section_title(parent, title: str, subtitle: str):
    frame = ttk.Frame(parent)
    ttk.Label(frame, text=title, font=("Segoe UI", 18, "bold"), bootstyle="primary").pack(anchor="w")
    help_label(frame, subtitle, 900).pack(anchor="w", pady=(4, 0), fill="x")
    return frame


def metric_card(parent, title: str, value: str, text: str):
    frame = ttk.Frame(parent, padding=14, bootstyle="light")
    ttk.Label(frame, text=title, font=("Segoe UI", 10, "bold"), bootstyle="primary").pack(anchor="w")
    ttk.Label(frame, text=value, font=("Segoe UI", 17, "bold")).pack(anchor="w", pady=(8, 2))
    help_label(frame, text, 250).pack(anchor="w", fill="x")
    return frame


def configure_treeview(tree: ttk.Treeview, columns: list[tuple[str, str, int]]) -> None:
    tree["columns"] = [key for key, _label, _width in columns]
    tree["show"] = "headings"
    for key, label, width in columns:
        tree.heading(key, text=label, anchor="center")
        tree.column(key, width=width, minwidth=70, anchor="center", stretch=True)


def _resolve(value):
    return value() if callable(value) else value


class RecordDialog:
    def __init__(self, parent, title: str, fields: list[tuple[str, str]], on_save, initial: dict | None = None):
        self.parent = parent
        self.title = title
        self.fields = fields
        self.on_save = on_save
        self.initial = initial or {}
        self.entries: dict[str, ttk.Entry | ttk.Combobox] = {}
        self.window: tk.Toplevel | None = None

    def show(self) -> None:
        win = tk.Toplevel(self.parent)
        self.window = win
        win.title(self.title)
        win.geometry("760x620")
        win.minsize(620, 460)
        win.resizable(True, True)
        apply_window_icon(win)
        try:
            win.transient(self.parent.winfo_toplevel())
        except tk.TclError:
            pass

        container = ttk.Frame(win, padding=10)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        scroll = ScrollableFrame(container)
        scroll.grid(row=0, column=0, sticky="nsew")
        form = scroll.body

        for index, field in enumerate(self.fields):
            if isinstance(field, dict):
                key = field["key"]
                label = field["label"]
                default = _resolve(field.get("default", self.initial.get(key, "")))
                values = _resolve(field.get("values", [])) or []
            else:
                key, label = field
                default = self.initial.get(key, "")
                values = []
            ttk.Label(form, text=label, font=("Segoe UI", 9, "bold")).grid(row=index * 2, column=0, sticky="w", pady=(6, 2))
            if values:
                widget = ttk.Combobox(form, values=values)
                widget.set(str(default or ""))
            else:
                widget = ttk.Entry(form)
                widget.insert(0, str(default or ""))
            widget.grid(row=index * 2 + 1, column=0, sticky="ew", pady=(0, 4))
            self.entries[key] = widget
        form.columnconfigure(0, weight=1)

        footer = ttk.Frame(container, padding=(0, 10, 0, 0))
        footer.grid(row=1, column=0, sticky="ew")
        ttk.Button(footer, text="Cancelar", bootstyle="secondary", command=win.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Salvar", bootstyle="primary", command=self._save).pack(side="right")

    def _save(self) -> None:
        data = {key: entry.get() for key, entry in self.entries.items()}
        try:
            self.on_save(data)
        except Exception as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=self.window)
            return
        if self.window is not None:
            self.window.destroy()
