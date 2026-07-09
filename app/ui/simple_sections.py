"""Secoes simples com tabela e modal."""

from __future__ import annotations

import ttkbootstrap as ttk

from app.ui.components import RecordDialog, configure_treeview, help_label


class TableSection(ttk.Frame):
    def __init__(
        self,
        master,
        title: str,
        education: str,
        columns,
        fields,
        list_func,
        create_func,
        actions=None,
        summary_func=None,
    ):
        super().__init__(master, padding=10)
        self.fields = fields
        self.list_func = list_func
        self.create_func = create_func
        self.summary_func = summary_func

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=title, font=("Segoe UI", 13, "bold"), bootstyle="primary").pack(side="left")
        ttk.Button(top, text="Cadastrar", bootstyle="primary", command=self._open_create).pack(side="right")
        for text, command in actions or []:
            ttk.Button(top, text=text, bootstyle="secondary", command=command).pack(side="right", padx=(0, 8))
        help_label(self, education, 860).pack(anchor="w", fill="x", pady=(0, 10))
        self.summary_label = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"), bootstyle="primary")
        if self.summary_func:
            self.summary_label.pack(anchor="w", pady=(0, 8))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, height=12)
        configure_treeview(self.tree, columns)
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.refresh()

    def _open_create(self) -> None:
        def save(data):
            self.create_func(**data)
            self.refresh()

        RecordDialog(self, "Cadastrar registro", self.fields, save).show()

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        keys = list(self.tree["columns"])
        for row in self.list_func():
            self.tree.insert("", "end", values=[row.get(key, "") for key in keys])
        if self.summary_func:
            self.summary_label.configure(text=self.summary_func())
