"""Barra de menus superior com listas suspensas CustomTkinter (cantos arredondados)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import customtkinter as ctk
import tkinter as tk

from rdo_diario.gui.tema import (
    COR_BORDA,
    COR_FUNDO_CARD,
    COR_FUNDO_SECUNDARIO,
    COR_TEXTO,
    FONT_INTERFACE,
    RAIO_BORDA,
    opcoes_item_lista_suspensa,
)

LARGURA_MENU_SUSPENSO = 340


@dataclass(frozen=True)
class EntradaMenuBarra:
    """Item de menu ou separador."""

    rotulo: str = ""
    acao: Callable[[], Any] | None = None
    separador: bool = False

    @staticmethod
    def sep() -> EntradaMenuBarra:
        return EntradaMenuBarra(separador=True)


class MenuSuspensoCtk:
    """Botão de menu que abre painel flutuante arredondado."""

    _aberto: MenuSuspensoCtk | None = None

    def __init__(self, pai: ctk.CTkFrame, titulo: str, itens: list[EntradaMenuBarra]) -> None:
        self._raiz = pai.winfo_toplevel()
        self._itens = itens
        self._popup: ctk.CTkToplevel | None = None
        self._bind_id: str | None = None
        largura = max(56, len(titulo) * 8 + 24)
        self._botao = ctk.CTkButton(
            pai,
            text=f"{titulo}  ▾",
            font=FONT_INTERFACE,
            fg_color="transparent",
            text_color=COR_TEXTO,
            hover_color=COR_FUNDO_SECUNDARIO,
            anchor="center",
            width=largura,
            height=28,
            corner_radius=6,
            command=self._alternar,
        )

    def pack(self, **kwargs: Any) -> None:
        self._botao.pack(**kwargs)

    def fechar(self) -> None:
        if self._popup is not None:
            try:
                self._popup.destroy()
            except (tk.TclError, AttributeError):
                pass
            self._popup = None
        if MenuSuspensoCtk._aberto is self:
            MenuSuspensoCtk._aberto = None
        if self._bind_id is not None:
            try:
                self._raiz.unbind("<Button-1>", self._bind_id)
            except tk.TclError:
                pass
            self._bind_id = None

    def _alternar(self) -> None:
        if MenuSuspensoCtk._aberto is not None and MenuSuspensoCtk._aberto is not self:
            MenuSuspensoCtk._aberto.fechar()
        if self._popup is not None:
            self.fechar()
            return
        self._abrir()

    def _abrir(self) -> None:
        popup = ctk.CTkToplevel(self._raiz)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        moldura = ctk.CTkFrame(
            popup,
            fg_color=COR_FUNDO_CARD,
            border_color=COR_BORDA,
            border_width=1,
            corner_radius=RAIO_BORDA,
        )
        moldura.pack(fill="both", expand=True, padx=1, pady=1)

        try:
            for entrada in self._itens:
                if entrada.separador:
                    ctk.CTkFrame(moldura, height=1, fg_color=COR_BORDA).pack(
                        fill="x", padx=10, pady=(4, 4)
                    )
                    continue
                comando = entrada.acao

                def _executar(cmd: Callable[[], Any] | None = comando) -> None:
                    self.fechar()
                    if cmd is not None:
                        cmd()

                ctk.CTkButton(
                    moldura,
                    text=entrada.rotulo,
                    anchor="w",
                    font=FONT_INTERFACE,
                    height=30,
                    command=_executar,
                    **opcoes_item_lista_suspensa(),
                ).pack(fill="x", padx=6, pady=1)
        except Exception:
            try:
                popup.destroy()
            except (tk.TclError, AttributeError):
                pass
            raise

        self._popup = popup
        popup.update_idletasks()
        largura = max(LARGURA_MENU_SUSPENSO, moldura.winfo_reqwidth() + 8)
        altura = moldura.winfo_reqheight() + 4
        x = self._botao.winfo_rootx()
        y = self._botao.winfo_rooty() + self._botao.winfo_height() + 2
        popup.geometry(f"{largura}x{altura}+{x}+{y}")
        popup.deiconify()

        MenuSuspensoCtk._aberto = self
        self._raiz.after(80, self._ligar_fechar_ao_clicar_fora)

    def _ligar_fechar_ao_clicar_fora(self) -> None:
        if self._popup is None:
            return

        def _fora(event: tk.Event) -> None:
            if self._popup is None:
                return
            widget = event.widget
            atual: tk.Misc | None = widget
            while atual is not None:
                if atual is self._popup or atual is self._botao:
                    return
                try:
                    atual = atual.master
                except (AttributeError, tk.TclError):
                    break
            self.fechar()

        try:
            self._bind_id = self._raiz.bind("<Button-1>", _fora, add="+")
        except tk.TclError:
            self._bind_id = None


def criar_barra_menu_ctk(
    pai: ctk.CTkBaseClass,
    menus: list[tuple[str, list[EntradaMenuBarra]]],
) -> tuple[ctk.CTkFrame, list[MenuSuspensoCtk]]:
    """Monta a barra superior com vários menus suspensos."""
    barra = ctk.CTkFrame(pai, fg_color=COR_FUNDO_SECUNDARIO, corner_radius=0)
    barra.pack(fill="x", side="top")

    conteudo = ctk.CTkFrame(barra, fg_color="transparent")
    conteudo.pack(fill="x", anchor="w", padx=4, pady=2)

    widgets: list[MenuSuspensoCtk] = []
    for titulo, itens in menus:
        menu = MenuSuspensoCtk(conteudo, titulo, itens)
        menu.pack(side="left", padx=(2, 0))
        widgets.append(menu)

    return barra, widgets
