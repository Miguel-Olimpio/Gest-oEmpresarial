"""Painel de colaboradores e socios."""

from __future__ import annotations

from tkinter import messagebox

import ttkbootstrap as ttk

from app.services.collaborator_service import CollaboratorService
from app.ui.components import RecordDialog, configure_treeview, help_label, section_title
from app.utils.formatting import format_money


class CollaboratorsPanel(ttk.Frame):
    def __init__(self, master, service: CollaboratorService):
        super().__init__(master, padding=18)
        self.service = service
        section_title(
            self,
            "Colaboradores e Sócios",
            "Cadastre colaboradores e sócios para calcular automaticamente salários e pró-labore nos custos fixos.",
        ).pack(fill="x", pady=(0, 12))
        self._build()
        self.refresh()

    def _build(self) -> None:
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Adicionar colaborador/sócio", bootstyle="primary", command=self.add_collaborator).pack(side="left")
        ttk.Button(actions, text="Editar", bootstyle="secondary", command=self.edit_collaborator).pack(side="left", padx=8)
        ttk.Button(actions, text="Inativar", bootstyle="danger", command=self.inactivate_collaborator).pack(side="left")
        help_label(
            self,
            "Para sócios, o salário base representa o pró-labore. Para colaboradores, representa o salário mensal.",
            900,
        ).pack(anchor="w", fill="x", pady=(0, 10))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, height=15)
        configure_treeview(
            self.tree,
            [
                ("nome", "Nome", 220),
                ("telefone", "Telefone", 130),
                ("tipo", "Tipo", 120),
                ("salario_base", "Salário base / Pró-labore", 170),
                ("status", "Status", 100),
            ],
        )
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def _fields(self, initial: dict | None = None) -> list[dict]:
        initial = initial or {}
        return [
            {"key": "nome", "label": "Nome", "default": initial.get("nome", "")},
            {"key": "telefone", "label": "Telefone", "default": initial.get("telefone", "")},
            {"key": "tipo", "label": "Tipo", "values": ["colaborador", "sócio"], "default": initial.get("tipo", "colaborador")},
            {"key": "salario_base", "label": "Salário base / Pró-labore", "default": initial.get("salario_base", "")},
            {"key": "active", "label": "Status", "values": ["ativo", "inativo"], "default": "ativo" if initial.get("active", True) else "inativo"},
            {"key": "observacoes", "label": "Observações", "default": initial.get("observacoes", "")},
        ]

    def add_collaborator(self) -> None:
        RecordDialog(self, "Adicionar colaborador/sócio", self._fields(), self._save_new).show()

    def edit_collaborator(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("Selecione um registro", "Selecione o colaborador ou sócio que deseja editar.", parent=self)
            return
        RecordDialog(self, "Editar colaborador/sócio", self._fields(row), lambda data: self._save_existing(row["colaborador_id"], data)).show()

    def inactivate_collaborator(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("Selecione um registro", "Selecione o colaborador ou sócio que deseja inativar.", parent=self)
            return
        if not messagebox.askyesno("Confirmar", "Deseja inativar este registro?", parent=self):
            return
        try:
            self.service.inactivate_collaborator(str(row["colaborador_id"]))
        except Exception as exc:
            messagebox.showerror("Não foi possível inativar", str(exc), parent=self)
            return
        self.refresh()

    def _save_new(self, data: dict) -> None:
        self.service.create_collaborator(**data)
        self.refresh()

    def _save_existing(self, colaborador_id: str, data: dict) -> None:
        self.service.update_collaborator(colaborador_id, **data)
        self.refresh()

    def _selected_row(self) -> dict | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return self.service.get_collaborator(str(selected[0]))

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in self.service.list_collaborators(active_only=False):
            status = "Ativo" if row.get("active") else "Inativo"
            self.tree.insert(
                "",
                "end",
                iid=str(row.get("colaborador_id")),
                values=[
                    row.get("nome", ""),
                    row.get("telefone", ""),
                    row.get("tipo", ""),
                    format_money(row.get("salario_base")),
                    status,
                ],
            )
