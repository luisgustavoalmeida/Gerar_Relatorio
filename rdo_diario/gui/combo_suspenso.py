"""Lista suspensa arredondada para ``CTkComboBox`` (substitui o ``tk.Menu`` nativo)."""

from __future__ import annotations

import customtkinter as ctk
import tkinter as tk

from rdo_diario.gui.tema import COR_BORDA, RAIO_BORDA, opcoes_item_lista_suspensa

ALTURA_ITEM_LISTA = 34
ALTURA_MAX_LISTA = 240
MARGEM_LISTA = 6
MARGEM_TELA = 8

_lista_aberta_combo: ctk.CTkComboBox | None = None
_popup_lista_combo: ctk.CTkToplevel | None = None
_bind_fora_lista_combo: str | None = None
_raiz_lista_combo: tk.Misc | None = None


def _area_util_tela(widget: tk.Misc) -> tuple[int, int, int, int]:
    """Retorna (x, y, largura, altura) da área útil do monitor sob o widget."""
    try:
        import sys

        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", wintypes.DWORD),
                ]

            user32 = ctypes.windll.user32
            ponto = wintypes.POINT(int(widget.winfo_rootx()), int(widget.winfo_rooty()))
            monitor = user32.MonitorFromPoint(ponto, 2)  # MONITOR_DEFAULTTONEAREST
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                trabalho = info.rcWork
                return (
                    int(trabalho.left),
                    int(trabalho.top),
                    int(trabalho.right - trabalho.left),
                    int(trabalho.bottom - trabalho.top),
                )
    except Exception:
        pass

    try:
        return (
            int(widget.winfo_vrootx()),
            int(widget.winfo_vrooty()),
            int(widget.winfo_vrootwidth()),
            int(widget.winfo_vrootheight()),
        )
    except tk.TclError:
        return 0, 0, int(widget.winfo_screenwidth()), int(widget.winfo_screenheight())


def _calcular_geometria_popup(
    combo: ctk.CTkComboBox,
    *,
    largura: int,
    altura: int,
) -> tuple[int, int, int, int]:
    """
    Posiciona a lista sob o combo quando há espaço; caso contrário, acima.
    Mantém o popup dentro da área útil do monitor (útil em tela cheia).
    """
    combo.update_idletasks()
    x_combo = int(combo.winfo_rootx())
    y_combo = int(combo.winfo_rooty())
    h_combo = int(combo.winfo_height())
    tela_x, tela_y, tela_w, tela_h = _area_util_tela(combo)
    esquerda = tela_x + MARGEM_TELA
    direita = tela_x + tela_w - MARGEM_TELA
    topo = tela_y + MARGEM_TELA
    fundo = tela_y + tela_h - MARGEM_TELA

    largura = max(40, min(largura, direita - esquerda))
    x = min(max(x_combo, esquerda), direita - largura)

    espaco_abaixo = fundo - (y_combo + h_combo + 2)
    espaco_acima = (y_combo - 2) - topo
    altura_desejada = max(40, altura)

    abrir_acima = espaco_abaixo < altura_desejada and espaco_acima > espaco_abaixo
    if abrir_acima:
        altura_final = min(altura_desejada, max(40, espaco_acima))
        y = y_combo - 2 - altura_final
    else:
        altura_final = min(altura_desejada, max(40, espaco_abaixo))
        y = y_combo + h_combo + 2

    y = min(max(y, topo), fundo - altura_final)
    return x, y, largura, altura_final


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

    altura_conteudo = len(valores) * ALTURA_ITEM_LISTA + 2 * MARGEM_LISTA
    usar_scroll = altura_conteudo > ALTURA_MAX_LISTA
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
    x, y, largura, altura = _calcular_geometria_popup(
        combo,
        largura=largura,
        altura=altura,
    )
    if usar_scroll and isinstance(container, ctk.CTkScrollableFrame):
        # Ajusta a altura rolável ao espaço efetivo disponível na tela.
        altura_interna = max(40, altura - 2 * MARGEM_LISTA - 8)
        try:
            container.configure(height=min(ALTURA_MAX_LISTA, altura_interna))
        except tk.TclError:
            pass
        popup.update_idletasks()
    popup.geometry(f"{largura}x{altura}+{x}+{y}")
    popup.deiconify()
    popup.lift()
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
