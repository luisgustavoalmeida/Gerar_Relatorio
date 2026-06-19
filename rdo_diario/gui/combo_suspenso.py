"""Lista suspensa arredondada para ``CTkComboBox`` (substitui o ``tk.Menu`` nativo)."""

from __future__ import annotations

import customtkinter as ctk
import tkinter as tk

from rdo_diario.gui.tema import COR_BORDA, RAIO_BORDA, opcoes_item_lista_suspensa

ALTURA_ITEM_LISTA = 34
ALTURA_MAX_LISTA = 240
MARGEM_LISTA = 6

_lista_aberta_combo: ctk.CTkComboBox | None = None
_popup_lista_combo: ctk.CTkToplevel | None = None
_bind_fora_lista_combo: str | None = None
_raiz_lista_combo: tk.Misc | None = None


def _fechar_lista_combo_suspenso() -> None:
    """Fecha o painel flutuante da lista, se estiver aberto."""
    global _lista_aberta_combo, _popup_lista_combo, _bind_fora_lista_combo, _raiz_lista_combo

    if _popup_lista_combo is not None:
        try:
            _popup_lista_combo.destroy()
        except (tk.TclError, AttributeError):
            pass
        _popup_lista_combo = None

    _lista_aberta_combo = None

    if _bind_fora_lista_combo is not None and _raiz_lista_combo is not None:
        try:
            _raiz_lista_combo.unbind("<Button-1>", _bind_fora_lista_combo)
        except tk.TclError:
            pass
    _bind_fora_lista_combo = None
    _raiz_lista_combo = None


def _ligar_fechar_ao_clicar_fora(combo: ctk.CTkComboBox) -> None:
    global _bind_fora_lista_combo, _raiz_lista_combo

    if _popup_lista_combo is None:
        return

    raiz = combo.winfo_toplevel()

    def _fora(event: tk.Event) -> None:
        if _popup_lista_combo is None:
            return
        widget = event.widget
        atual: tk.Misc | None = widget
        while atual is not None:
            if atual is _popup_lista_combo or atual is combo:
                return
            try:
                atual = atual.master
            except (AttributeError, tk.TclError):
                break
        _fechar_lista_combo_suspenso()

    try:
        _raiz_lista_combo = raiz
        _bind_fora_lista_combo = raiz.bind("<Button-1>", _fora, add="+")
    except tk.TclError:
        _bind_fora_lista_combo = None


def _abrir_lista_arredondada(combo: ctk.CTkComboBox) -> None:
    global _lista_aberta_combo, _popup_lista_combo

    if combo.cget("state") == "disabled":
        return

    valores = [v for v in (combo.cget("values") or []) if str(v).strip()]
    if not valores:
        return

    _fechar_lista_combo_suspenso()

    raiz = combo.winfo_toplevel()
    popup = ctk.CTkToplevel(raiz)
    popup.withdraw()
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)

    cor_fundo = combo.cget("dropdown_fg_color")
    fonte = combo._dropdown_menu.cget("font")
    selecionado = combo.get()

    moldura = ctk.CTkFrame(
        popup,
        fg_color=cor_fundo,
        border_color=COR_BORDA,
        border_width=1,
        corner_radius=RAIO_BORDA,
    )
    moldura.pack(fill="both", expand=True, padx=1, pady=1)

    usar_scroll = len(valores) * ALTURA_ITEM_LISTA > ALTURA_MAX_LISTA
    if usar_scroll:
        container: ctk.CTkBaseClass = ctk.CTkScrollableFrame(
            moldura,
            fg_color="transparent",
            height=ALTURA_MAX_LISTA,
            corner_radius=RAIO_BORDA - 2,
        )
    else:
        container = ctk.CTkFrame(moldura, fg_color="transparent")

    container.pack(fill="both", expand=True, padx=MARGEM_LISTA, pady=MARGEM_LISTA)

    for valor in valores:
        def _selecionar(v: str = valor) -> None:
            _fechar_lista_combo_suspenso()
            combo._dropdown_callback(v)

        atual = valor == selecionado
        ctk.CTkButton(
            container,
            text=valor,
            anchor="w",
            font=fonte,
            height=ALTURA_ITEM_LISTA - 4,
            command=_selecionar,
            **opcoes_item_lista_suspensa(selecionado=atual),
        ).pack(fill="x", pady=1)

    _popup_lista_combo = popup
    _lista_aberta_combo = combo

    popup.update_idletasks()
    largura = max(combo.winfo_width(), moldura.winfo_reqwidth() + 8)
    altura = moldura.winfo_reqheight() + 4
    x = combo.winfo_rootx()
    y = combo.winfo_rooty() + combo.winfo_height() + 2
    popup.geometry(f"{largura}x{altura}+{x}+{y}")
    popup.deiconify()
    popup.bind("<Escape>", lambda _event: _fechar_lista_combo_suspenso())
    raiz.after(80, lambda: _ligar_fechar_ao_clicar_fora(combo))


def configurar_combo_ctk_aprimorado(combo: ctk.CTkComboBox) -> None:
    """Clique em todo o campo + lista suspensa arredondada (em vez do menu nativo)."""
    for tag in ("inner_parts_left", "border_parts_left"):
        combo._canvas.tag_bind(tag, "<Button-1>", combo._clicked)

    def _abrir_pelo_texto(_event=None):
        combo._clicked()
        return "break"

    combo._entry.bind("<Button-1>", _abrir_pelo_texto, add=True)

    def _abrir(_combo: ctk.CTkComboBox = combo) -> None:
        _abrir_lista_arredondada(_combo)

    combo._open_dropdown_menu = _abrir  # type: ignore[method-assign]
