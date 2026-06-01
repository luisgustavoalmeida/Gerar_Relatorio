"""Ícone da janela e barra de tarefas (Windows / Tk)."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import Misc

from rdo_diario.paths import resolver_arquivo_icone_janela


def preparar_icone_processo_windows() -> None:
    """
    Evita que o Windows agrupe a app com o ícone genérico do Python na barra de tarefas.
    Deve ser chamado antes de criar qualquer janela.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "GerarRelatorio.AtividadesDiarias.1"
        )
    except (AttributeError, OSError):
        pass


def aplicar_icone_janela(janela: Misc) -> None:
    """Define o ícone da janela (barra de tarefas e canto do título)."""
    caminho = resolver_arquivo_icone_janela()
    if caminho is None:
        return
    texto = str(caminho)
    try:
        janela.iconbitmap(texto)
    except tk.TclError:
        try:
            janela.iconbitmap(default=texto)
        except tk.TclError:
            pass
