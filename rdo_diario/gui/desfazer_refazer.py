"""Desfazer e refazer (Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z) em campos editáveis."""

from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from rdo_diario.gui.tema import texto_interno_campo

_ATALHOS_DESFAZER = ("<Control-z>", "<Control-Z>")
_ATALHOS_REFazer = (
    "<Control-y>",
    "<Control-Y>",
    "<Control-Shift-z>",
    "<Control-Shift-Z>",
)

_pilhas_entrada: dict[int, dict[str, list[str]]] = {}
_handlers_entrada: dict[int, Any] = {}
_instalado_globalmente = False


def _desfazer_texto(event: tk.Event) -> str | None:
    widget = event.widget
    if not isinstance(widget, tk.Text):
        return None
    _habilitar_desfazer_texto(widget)
    try:
        widget.edit_undo()
    except tk.TclError:
        return None
    return "break"


def _refazer_texto(event: tk.Event) -> str | None:
    widget = event.widget
    if not isinstance(widget, tk.Text):
        return None
    _habilitar_desfazer_texto(widget)
    try:
        widget.edit_redo()
    except tk.TclError:
        return None
    return "break"


def _habilitar_desfazer_texto(texto: tk.Text) -> None:
    try:
        if str(texto.cget("undo")) not in ("1", "true"):
            texto.configure(undo=True, autoseparators=True, maxundo=-1)
    except tk.TclError:
        pass


def _garantir_pilha_entrada(entrada: tk.Entry) -> dict[str, list[str]] | None:
    chave = id(entrada)
    pilha = _pilhas_entrada.get(chave)
    if pilha is not None:
        return pilha
    try:
        valor_inicial = entrada.get()
    except tk.TclError:
        return None
    pilha = {"undo": [valor_inicial], "redo": []}
    _pilhas_entrada[chave] = pilha

    def _registrar_alteracao(_event: tk.Event | None = None) -> None:
        try:
            atual = entrada.get()
        except tk.TclError:
            return
        if pilha["undo"] and pilha["undo"][-1] == atual:
            return
        pilha["undo"].append(atual)
        if len(pilha["undo"]) > 200:
            pilha["undo"].pop(0)
        pilha["redo"].clear()

    handler = _registrar_alteracao
    _handlers_entrada[chave] = handler
    entrada.bind("<KeyRelease>", handler, add="+")
    return pilha


def _ao_foco_entrada(event: tk.Event) -> None:
    if isinstance(event.widget, tk.Entry):
        _garantir_pilha_entrada(event.widget)


def _ao_foco_texto(event: tk.Event) -> None:
    if isinstance(event.widget, tk.Text):
        _habilitar_desfazer_texto(event.widget)


def _desfazer_entrada(event: tk.Event) -> str | None:
    entrada = event.widget
    if not isinstance(entrada, tk.Entry):
        return None
    pilha = _garantir_pilha_entrada(entrada)
    if pilha is None or len(pilha["undo"]) <= 1:
        return None
    try:
        atual = entrada.get()
    except tk.TclError:
        return None
    pilha["redo"].append(atual)
    pilha["undo"].pop()
    novo = pilha["undo"][-1]
    try:
        entrada.delete(0, tk.END)
        entrada.insert(0, novo)
    except tk.TclError:
        return None
    return "break"


def _refazer_entrada(event: tk.Event) -> str | None:
    entrada = event.widget
    if not isinstance(entrada, tk.Entry):
        return None
    pilha = _pilhas_entrada.get(id(entrada))
    if pilha is None or not pilha["redo"]:
        return None
    try:
        atual = entrada.get()
    except tk.TclError:
        return None
    pilha["undo"].append(atual)
    novo = pilha["redo"].pop()
    try:
        entrada.delete(0, tk.END)
        entrada.insert(0, novo)
    except tk.TclError:
        return None
    return "break"


def preparar_widget_edicao(widget: tk.Misc) -> None:
    """Ativa desfazer/refazer num ``CTkTextbox``, ``Text``, ``CTkEntry`` ou ``Entry``."""
    if isinstance(widget, ctk.CTkTextbox):
        _habilitar_desfazer_texto(texto_interno_campo(widget))
        return
    if isinstance(widget, tk.Text):
        _habilitar_desfazer_texto(widget)
        return
    if isinstance(widget, ctk.CTkEntry):
        interno = getattr(widget, "_entry", None)
        if isinstance(interno, tk.Entry):
            _garantir_pilha_entrada(interno)
        return
    if isinstance(widget, tk.Entry):
        _garantir_pilha_entrada(widget)


def reiniciar_historico_desfazer_widget(widget: tk.Misc) -> None:
    """Limpa pilhas de desfazer após carregar conteúdo programaticamente (troca de dia, etc.)."""
    if isinstance(widget, ctk.CTkTextbox):
        texto = texto_interno_campo(widget)
        _habilitar_desfazer_texto(texto)
        try:
            texto.edit_reset()
        except tk.TclError:
            pass
        return
    if isinstance(widget, tk.Text):
        _habilitar_desfazer_texto(widget)
        try:
            widget.edit_reset()
        except tk.TclError:
            pass
        return
    interno: tk.Entry | None = None
    if isinstance(widget, ctk.CTkEntry):
        candidato = getattr(widget, "_entry", None)
        if isinstance(candidato, tk.Entry):
            interno = candidato
    elif isinstance(widget, tk.Entry):
        interno = widget
    if interno is None:
        return
    try:
        atual = interno.get()
    except tk.TclError:
        atual = ""
    _pilhas_entrada[id(interno)] = {"undo": [atual], "redo": []}


def registrar_desfazer_refazer_recursivo(raiz: tk.Misc) -> None:
    """Percorre a árvore de widgets e prepara campos editáveis."""
    try:
        filhos = raiz.winfo_children()
    except tk.TclError:
        return
    for filho in filhos:
        registrar_desfazer_refazer_recursivo(filho)
    preparar_widget_edicao(raiz)


def instalar_desfazer_refazer_global(raiz: tk.Misc) -> None:
    """Regista atalhos globais para todos os ``Text`` e ``Entry`` da aplicação."""
    global _instalado_globalmente
    if _instalado_globalmente:
        return
    _instalado_globalmente = True

    for sequencia in _ATALHOS_DESFAZER:
        raiz.bind_class("Text", sequencia, _desfazer_texto, add="+")
        raiz.bind_class("Entry", sequencia, _desfazer_entrada, add="+")
    for sequencia in _ATALHOS_REFazer:
        raiz.bind_class("Text", sequencia, _refazer_texto, add="+")
        raiz.bind_class("Entry", sequencia, _refazer_entrada, add="+")

    raiz.bind_class("Text", "<FocusIn>", _ao_foco_texto, add="+")
    raiz.bind_class("Entry", "<FocusIn>", _ao_foco_entrada, add="+")
