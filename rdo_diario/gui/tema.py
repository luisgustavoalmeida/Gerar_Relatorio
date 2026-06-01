"""Paleta de cores, dimensões e alternância claro/escuro da interface gráfica."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any, Literal

import customtkinter as ctk

from rdo_diario.paths import ARQUIVO_CONFIG_USUARIO_JSON, ARQUIVO_TEMA_APLICACAO_JSON

ModoAparencia = Literal["dark", "light"]
CorTema = tuple[str, str]  # (claro, escuro)

NOME_ESTILO_TTK = "Rdo"
CHAVE_TEMA = "tema_aparencia"
MODO_ATUAL: ModoAparencia = "dark"


def _par(claro: str, escuro: str) -> CorTema:
    return (claro, escuro)


# Cores adaptativas — cada constante vale para claro e escuro ao mesmo tempo
COR_PRIMARIA = _par("#1a73e8", "#1a73e8")
COR_PRIMARIA_HOVER = _par("#1557b0", "#1557b0")
COR_FUNDO = _par("#f4f4f8", "#1e1e2e")
COR_FUNDO_SECUNDARIO = _par("#eaeaef", "#252536")
COR_FUNDO_CARD = _par("#ffffff", "#2a2a3d")
COR_BORDA = _par("#c5c5d2", "#3d3d5c")
COR_TEXTO = _par("#1c1c28", "#e8e8f0")
COR_TEXTO_SECUNDARIO = _par("#5f5f78", "#9898b0")
COR_SUCESSO = _par("#188038", "#34a853")
COR_AVISO = _par("#e37400", "#fbbc04")
COR_ERRO = _par("#d93025", "#ea4335")
COR_ERRO_HOVER = _par("#b3261e", "#c5221f")
COR_TEXTO_BOTAO_ATIVO = _par("#ffffff", "#ffffff")
COR_CALENDARIO_FDS_FUNDO = _par("#dce4f5", "#343652")
COR_CALENDARIO_FDS_TEXTO = _par("#4a5a8a", "#a8b4e0")
COR_CALENDARIO_FDS_OM_FUNDO = _par("#cfd8eb", "#2e3048")
COR_CALENDARIO_FDS_OM_TEXTO = _par("#6b7a9a", "#7878a0")
COR_CALENDARIO_HOJE_FUNDO = _par("#7eb3f5", "#5a74c4")

# Dimensões
LARGURA_JANELA = 1140
ALTURA_JANELA = 910
PADDING = 16
RAIO_BORDA = 10

# Tipografia — nomes indicam o papel na interface (Segoe UI)
FONT_JANELA_TITULO = ("Segoe UI", 14, "bold")           # diálogos modais (ajuda, sobre, ortografia)
FONT_PAINEL_TITULO = ("Segoe UI", 12, "bold")           # títulos de grupos (Relatório, Calendário…)
FONT_GRUPO = ("Segoe UI", 11, "bold")                   # subgrupos (Ponto, Métricas do dia, data em destaque)
FONT_INTERFACE = ("Segoe UI", 14)                       # rótulos, campos e texto digitável do relatório
FONT_CAMPO_SELECAO = ("Segoe UI", 14)                   # texto dentro de comboboxes e listas suspensas
FONT_DATA_SELECIONADA = ("Segoe UI", 12)                # valor da data ativa no formulário
FONT_CONTAGEM_MES = ("Segoe UI", 12)                    # «No mês: X de N» no formulário
FONT_METRICAS = ("Segoe UI", 11)                        # valores do painel de métricas (sidebar)
FONT_DICA_ABA = ("Segoe UI", 11)                        # texto explicativo no topo das abas
FONT_ABA = ("Segoe UI", 12, "bold")                     # botões «Cabeçalhos» / «Relatórios de trabalho»
FONT_AUXILIAR = ("Segoe UI", 9)                         # legendas compactas (calendário, etc.)
FONT_BOTAO = ("Segoe UI", 12, "bold")                   # botões (reserva / tema CTk)
FONT_CALENDARIO = ("Segoe UI", 9)                       # células do calendário compacto
FONT_CALENDARIO_EXPANSO = ("Segoe UI", 9)               # calendário em layout amplo


def _indice_modo_aparencia() -> int:
    """Índice 0=claro, 1=escuro — alinhado ao CustomTkinter após troca de tema."""
    modo_ctk = ctk.get_appearance_mode()
    if modo_ctk == "Dark":
        return 1
    if modo_ctk == "Light":
        return 0
    return 1 if MODO_ATUAL == "dark" else 0


def resolver_cor(par: CorTema) -> str:
    """Devolve a cor do par (claro, escuro) conforme o modo atual."""
    return par[_indice_modo_aparencia()]


def carregar_tema_salvo() -> ModoAparencia:
    """Lê o tema salvo em config_usuario.json; padrão: escuro."""
    arquivo = ARQUIVO_CONFIG_USUARIO_JSON
    if not arquivo.is_file():
        return "dark"
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        modo = dados.get(CHAVE_TEMA, "dark")
        if modo in ("dark", "light"):
            return modo  # type: ignore[return-value]
    except Exception:
        pass
    return "dark"


def salvar_tema(modo: ModoAparencia) -> None:
    """Persiste a preferência de tema."""
    arquivo = ARQUIVO_CONFIG_USUARIO_JSON
    dados: dict[str, Any] = {}
    if arquivo.is_file():
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except Exception:
            dados = {}
    dados[CHAVE_TEMA] = modo
    try:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def aplicar_tema(modo: ModoAparencia, persistir: bool = True) -> ModoAparencia:
    """Ativa claro/escuro com a paleta padrão da aplicação."""
    global MODO_ATUAL

    if modo not in ("dark", "light"):
        modo = "dark"

    MODO_ATUAL = modo
    ctk.set_appearance_mode(modo)
    if ARQUIVO_TEMA_APLICACAO_JSON.is_file():
        ctk.set_default_color_theme(str(ARQUIVO_TEMA_APLICACAO_JSON))
    else:
        ctk.set_default_color_theme("blue")

    if persistir:
        salvar_tema(modo)

    return modo


def inicializar_tema() -> ModoAparencia:
    """Carrega e aplica o tema salvo (ou escuro)."""
    return aplicar_tema(carregar_tema_salvo(), persistir=False)


def alternar_tema() -> ModoAparencia:
    """Alterna entre claro e escuro."""
    novo: ModoAparencia = "light" if MODO_ATUAL == "dark" else "dark"
    return aplicar_tema(novo)


def configurar_aparencia() -> ModoAparencia:
    """Alias de compatibilidade para inicialização da aplicação."""
    return inicializar_tema()


def _modo_ctk() -> str:
    return "Dark" if MODO_ATUAL == "dark" else "Light"


def obter_cores_tema() -> dict[str, str]:
    """Paleta resolvida para widgets ttk/tk embutidos."""
    return {
        "fundo": resolver_cor(COR_FUNDO),
        "fundo_superior": resolver_cor(COR_FUNDO_SECUNDARIO),
        "entrada": resolver_cor(COR_FUNDO_CARD),
        "texto": resolver_cor(COR_TEXTO),
        "texto_discreto": resolver_cor(COR_TEXTO_SECUNDARIO),
        "borda": resolver_cor(COR_BORDA),
        "scroll": resolver_cor(COR_PRIMARIA),
        "scroll_trilho": resolver_cor(COR_FUNDO_SECUNDARIO),
        "destaque": resolver_cor(COR_PRIMARIA),
        "sucesso": resolver_cor(COR_SUCESSO),
        "aviso": resolver_cor(COR_AVISO),
        "erro": resolver_cor(COR_ERRO),
        "texto_botao": resolver_cor(COR_TEXTO_BOTAO_ATIVO),
        "calendario_fds_fundo": resolver_cor(COR_CALENDARIO_FDS_FUNDO),
        "calendario_fds_texto": resolver_cor(COR_CALENDARIO_FDS_TEXTO),
        "calendario_fds_om_fundo": resolver_cor(COR_CALENDARIO_FDS_OM_FUNDO),
        "calendario_fds_om_texto": resolver_cor(COR_CALENDARIO_FDS_OM_TEXTO),
        "calendario_hoje_fundo": resolver_cor(COR_CALENDARIO_HOJE_FUNDO),
    }


def opcoes_menu_tk_embutido() -> dict[str, str]:
    """Cores para ``tk.Menu`` (barra interna e menus de contexto)."""
    cores = obter_cores_tema()
    return {
        "bg": cores["entrada"],
        "fg": cores["texto"],
        "activebackground": cores["destaque"],
        "activeforeground": cores["texto_botao"],
        "disabledforeground": cores["texto_discreto"],
        "relief": "flat",
        "borderwidth": 0,
    }


def configurar_menu_tk(menu: tk.Menu) -> None:
    """Aplica a paleta a um menu e a submenus em cascata."""
    try:
        menu.configure(**opcoes_menu_tk_embutido())
    except tk.TclError:
        pass
    try:
        ultimo = menu.index("end")
    except tk.TclError:
        return
    if ultimo is None:
        return
    for indice in range(ultimo + 1):
        try:
            if menu.type(indice) != "cascade":
                continue
            filho = menu.nametowidget(menu.entrycget(indice, "menu"))
            if isinstance(filho, tk.Menu):
                configurar_menu_tk(filho)
        except tk.TclError:
            continue


def registrar_painel_tema(pai: tk.Misc, painel: ctk.CTkFrame) -> None:
    """Regista molduras para atualização na troca claro/escuro."""
    raiz = pai.winfo_toplevel()
    if not hasattr(raiz, "_paineis_tema_ctk"):
        raiz._paineis_tema_ctk = []  # type: ignore[attr-defined]
    raiz._paineis_tema_ctk.append(painel)  # type: ignore[attr-defined]


def atualizar_paineis_tema_registados(janela: tk.Misc) -> None:
    """Reaplica tuplas de cor e redesenha painéis CTk após alternar tema."""
    for painel in getattr(janela, "_paineis_tema_ctk", []):
        try:
            painel.configure(fg_color=COR_FUNDO, border_color=COR_BORDA)
            painel._set_appearance_mode(_modo_ctk())
            painel._draw()
        except Exception:
            pass


def _filhos_para_tema(janela: tk.Misc) -> list[tk.Misc]:
    """Filhos visíveis na árvore, incluindo conteúdo em ``Canvas.create_window``."""
    filhos: list[tk.Misc] = []
    try:
        filhos.extend(janela.winfo_children())
    except Exception:
        pass

    canvas = getattr(janela, "_parent_canvas", None)
    if canvas is not None:
        try:
            filhos.extend(canvas.winfo_children())
        except Exception:
            pass
        _anexar_janelas_canvas(canvas, filhos)

    if type(janela).__name__ == "Canvas":
        _anexar_janelas_canvas(janela, filhos)

    return filhos


def _anexar_janelas_canvas(canvas: tk.Canvas, filhos: list[tk.Misc]) -> None:
    try:
        for item_id in canvas.find_all():
            if canvas.type(item_id) != "window":
                continue
            nome = canvas.itemcget(item_id, "window")
            if not nome:
                continue
            widget = canvas.nametowidget(nome)
            if widget not in filhos:
                filhos.append(widget)
    except Exception:
        pass


def _atualizar_scrollable_frame_tema(scroll: ctk.CTkScrollableFrame) -> None:
    """Atualiza fundo do canvas e dos filhos após alternar claro/escuro."""
    modo = _modo_ctk()
    fundo = resolver_cor(COR_FUNDO)
    try:
        scroll._set_appearance_mode(modo)
    except Exception:
        pass
    try:
        scroll._parent_frame._set_appearance_mode(modo)
        scroll._parent_frame._draw()
        scroll._parent_canvas.configure(bg=fundo)
        tk.Frame.configure(scroll, bg=fundo)
        scroll._scrollbar._set_appearance_mode(modo)
        scroll._scrollbar._draw()
        for filho in scroll.winfo_children():
            if isinstance(filho, ctk.CTkBaseClass):
                filho.configure(bg_color="transparent")
                filho._draw()
    except Exception:
        pass


def _redesenhar_widget(widget: tk.Misc) -> None:
    """Força atualização visual após troca de appearance mode."""
    modo = _modo_ctk()

    if type(widget).__name__ == "CTkScrollableFrame":
        _atualizar_scrollable_frame_tema(widget)
        return

    if isinstance(widget, ctk.CTkBaseClass):
        if hasattr(widget, "_set_appearance_mode"):
            try:
                widget._set_appearance_mode(modo)
            except Exception:
                pass

        if isinstance(widget, ctk.CTkTextbox):
            try:
                widget.configure(
                    border_color=COR_BORDA,
                    fg_color=COR_FUNDO_CARD,
                    text_color=COR_TEXTO,
                )
            except Exception:
                pass
        elif isinstance(widget, ctk.CTkEntry):
            try:
                widget.configure(
                    border_color=COR_BORDA,
                    fg_color=COR_FUNDO_CARD,
                    text_color=COR_TEXTO,
                )
            except Exception:
                pass
        elif isinstance(widget, ctk.CTkFrame):
            try:
                fg = widget.cget("fg_color")
                if fg in ("transparent", "Transparent", None):
                    widget.configure(bg_color="transparent")
                else:
                    cfg = widget.cget("border_width")
                    if cfg and int(cfg) > 0:
                        widget.configure(fg_color=COR_FUNDO, border_color=COR_BORDA)
            except Exception:
                pass
        elif isinstance(widget, ctk.CTkLabel):
            try:
                widget.configure(bg_color="transparent")
            except Exception:
                pass

        if hasattr(widget, "_draw"):
            try:
                widget._draw()
            except Exception:
                pass
        return


def _atualizar_widget_tk_embutido(widget: tk.Misc) -> None:
    """Atualiza cores de Canvas, Text e Listbox após troca de tema."""
    if isinstance(widget, tk.Canvas):
        try:
            widget.configure(bg=cor_canvas_tk())
        except tk.TclError:
            pass
        return

    if isinstance(widget, tk.Text):
        opcoes = opcoes_texto_tk_embutido()
        try:
            widget.configure(
                bg=opcoes["bg"],
                fg=opcoes["fg"],
                insertbackground=opcoes["insertbackground"],
                selectbackground=opcoes["selectbackground"],
                selectforeground=opcoes["selectforeground"],
                highlightbackground=opcoes["highlightbackground"],
                highlightcolor=opcoes["highlightcolor"],
            )
        except tk.TclError:
            pass
        return

    if isinstance(widget, tk.Listbox):
        try:
            widget.configure(**opcoes_listbox_tk_embutido())
        except tk.TclError:
            pass


def _percorrer_arvore_tema(janela: tk.Misc, visitados: set[int], processar: Any) -> None:
    wid = id(janela)
    if wid in visitados:
        return
    visitados.add(wid)

    filhos = _filhos_para_tema(janela)

    for filho in filhos:
        _percorrer_arvore_tema(filho, visitados, processar)

    processar(janela)


def forcar_redesenho_tema(janela: tk.Misc, visitados: set[int] | None = None) -> None:
    """
    Percorre a árvore (filhos antes do pai) e força redesenho CTk + tk embutidos.
    ``refresh_apos_tema`` só corre no final, na janela raiz.
    """
    if visitados is None:
        visitados = set()

    def _processar(widget: tk.Misc) -> None:
        _redesenhar_widget(widget)
        _atualizar_widget_tk_embutido(widget)

    _percorrer_arvore_tema(janela, visitados, _processar)

    atualizar_paineis_tema_registados(janela)

    hook = getattr(janela, "refresh_apos_tema", None)
    if callable(hook):
        try:
            hook()
        except Exception:
            pass

def _copiar_layout_ttk(estilo: ttk.Style, nome: str, base: str) -> None:
    try:
        estilo.layout(nome, estilo.layout(base))
    except tk.TclError:
        pass


def _aplicar_estilo_ttk(estilo: ttk.Style, nome: str, *, layout_base: str | None = None, **opcoes: Any) -> None:
    estilo.configure(nome, **opcoes)
    if layout_base:
        _copiar_layout_ttk(estilo, nome, layout_base)
    if nome.startswith(f"{NOME_ESTILO_TTK}."):
        legado = nome[len(NOME_ESTILO_TTK) + 1 :]
        if legado and not legado.startswith("TLabel."):
            estilo.configure(legado, **opcoes)


def configurar_estilo_ttk(janela: tk.Misc) -> ttk.Style:
    """Aplica a paleta padrão aos widgets ``ttk``."""
    cores = obter_cores_tema()
    estilo = ttk.Style(janela)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    p = NOME_ESTILO_TTK
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TLabel",
        layout_base="TLabel",
        background=cores["fundo"],
        foreground=cores["texto"],
    )
    for variante, extra in (
        ("Secundario", {"foreground": cores["texto_discreto"]}),
        ("Negrito", {"foreground": cores["texto"], "font": ("Segoe UI", 11, "bold")}),
    ):
        nome = f"{p}.TLabel.{variante}"
        estilo.configure(nome, background=cores["fundo"], **extra)
        _copiar_layout_ttk(estilo, nome, "TLabel")
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TLabelframe",
        layout_base="TLabelframe",
        background=cores["fundo"],
        foreground=cores["texto"],
        bordercolor=cores["borda"],
        relief="solid",
        borderwidth=1,
    )
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TLabelframe.Label",
        layout_base="TLabelframe.Label",
        background=cores["fundo"],
        foreground=cores["texto"],
        font=("Segoe UI", 11, "bold"),
    )
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TFrame",
        layout_base="TFrame",
        background=cores["fundo"],
    )
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TFrame.BarraSuperior",
        layout_base="TFrame",
        background=cores["fundo_superior"],
    )
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TMenubutton",
        layout_base="TMenubutton",
        background=cores["fundo_superior"],
        foreground=cores["texto"],
        bordercolor=cores["fundo_superior"],
        arrowcolor=cores["texto"],
        relief="flat",
        padding=(8, 4),
    )
    for alvo in (f"{p}.TMenubutton", "TMenubutton"):
        estilo.map(
            alvo,
            background=[("active", cores["entrada"]), ("pressed", cores["borda"])],
            foreground=[("disabled", cores["texto_discreto"])],
        )
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TEntry",
        layout_base="TEntry",
        fieldbackground=cores["entrada"],
        foreground=cores["texto"],
        insertcolor=cores["texto"],
        bordercolor=cores["borda"],
        lightcolor=cores["borda"],
        darkcolor=cores["borda"],
    )
    for alvo in (f"{p}.TEntry", "TEntry"):
        estilo.map(
            alvo,
            fieldbackground=[
                ("readonly", cores["entrada"]),
                ("disabled", cores["fundo_superior"]),
            ],
            foreground=[("disabled", cores["texto_discreto"])],
        )
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TScrollbar",
        layout_base="Vertical.TScrollbar",
        background=cores["scroll_trilho"],
        troughcolor=cores["fundo"],
        bordercolor=cores["fundo"],
        arrowcolor=cores["texto"],
        darkcolor=cores["scroll_trilho"],
        lightcolor=cores["scroll_trilho"],
    )
    for alvo in (f"{p}.TScrollbar", "TScrollbar"):
        estilo.map(
            alvo,
            background=[("active", cores["scroll"]), ("pressed", cores["destaque"])],
        )
    _aplicar_estilo_ttk(
        estilo,
        f"{p}.TPanedwindow",
        layout_base="TPanedwindow",
        background=cores["fundo"],
    )
    try:
        estilo.configure("Sash", sashthickness=5, background=cores["borda"])
    except tk.TclError:
        pass

    return estilo


def opcoes_calendario_tk_embutido(*, compacto: bool = False) -> dict[str, Any]:
    cores = obter_cores_tema()
    return {
        "font": FONT_CALENDARIO if compacto else FONT_CALENDARIO_EXPANSO,
        "background": cores["fundo"],
        "foreground": cores["texto"],
        "headersbackground": cores["fundo_superior"],
        "headersforeground": cores["texto"],
        "selectbackground": cores["destaque"],
        "selectforeground": resolver_cor(COR_TEXTO_BOTAO_ATIVO),
        "normalbackground": cores["entrada"],
        "normalforeground": cores["texto"],
        "weekendbackground": cores["calendario_fds_fundo"],
        "weekendforeground": cores["calendario_fds_texto"],
        "othermonthforeground": cores["texto_discreto"],
        "othermonthbackground": cores["fundo_superior"],
        "othermonthweforeground": cores["calendario_fds_om_texto"],
        "othermonthwebackground": cores["calendario_fds_om_fundo"],
        "bordercolor": cores["borda"],
        "disabledbackground": cores["fundo_superior"],
        "disabledforeground": cores["texto_discreto"],
    }


def cor_canvas_tk() -> str:
    return obter_cores_tema()["fundo"]


def raio_borda() -> int:
    return RAIO_BORDA


def opcoes_caixa_texto_ctk(*, altura_px: int) -> dict[str, Any]:
    """Parâmetros visuais padrão para ``CTkTextbox`` (tuplas claro/escuro)."""
    return {
        "height": altura_px,
        "corner_radius": RAIO_BORDA,
        "border_width": 1,
        "border_color": COR_BORDA,
        "fg_color": COR_FUNDO_CARD,
        "text_color": COR_TEXTO,
        "font": FONT_INTERFACE,
        "wrap": "word",
        "activate_scrollbars": True,
    }


def opcoes_campo_entrada_ctk(*, largura: int | None = None) -> dict[str, Any]:
    opcoes: dict[str, Any] = {
        "corner_radius": RAIO_BORDA,
        "border_width": 1,
        "border_color": COR_BORDA,
        "fg_color": COR_FUNDO_CARD,
        "text_color": COR_TEXTO,
        "font": FONT_INTERFACE,
    }
    if largura is not None:
        opcoes["width"] = largura
    return opcoes


def opcoes_item_lista_suspensa(*, selecionado: bool = False) -> dict[str, Any]:
    """Estilo comum de hover/seleção para itens de menu e listas suspensas."""
    return {
        "fg_color": COR_FUNDO_SECUNDARIO if selecionado else "transparent",
        "hover_color": COR_PRIMARIA,
        "text_color": COR_TEXTO,
        "corner_radius": 6,
    }


def opcoes_tabview_ctk() -> dict[str, Any]:
    """Parâmetros visuais para ``CTkTabview`` (botões das abas)."""
    return {
        "corner_radius": RAIO_BORDA,
        "border_width": 1,
        "border_color": COR_BORDA,
        "fg_color": COR_FUNDO_CARD,
        "segmented_button_fg_color": COR_FUNDO,
        "segmented_button_selected_color": COR_PRIMARIA,
        "segmented_button_selected_hover_color": COR_PRIMARIA_HOVER,
        "segmented_button_unselected_color": COR_FUNDO_SECUNDARIO,
        "segmented_button_unselected_hover_color": COR_BORDA,
        "text_color": COR_TEXTO,
        "anchor": "nw",
    }


def configurar_abas_tabview(tabview: ctk.CTkTabview) -> None:
    """Aplica fonte e alinhamento à esquerda nos botões das abas."""
    tabview._segmented_button.configure(font=FONT_ABA)
    for botao in tabview._segmented_button._buttons_dict.values():
        botao.configure(anchor="w")


def opcoes_combo_ctk(*, largura: int | None = None) -> dict[str, Any]:
    """Parâmetros visuais para ``CTkComboBox`` (valor selecionado e lista)."""
    opcoes: dict[str, Any] = {
        "corner_radius": RAIO_BORDA,
        "border_width": 1,
        "border_color": COR_BORDA,
        "fg_color": COR_FUNDO_CARD,
        "button_color": COR_FUNDO_SECUNDARIO,
        "button_hover_color": COR_BORDA,
        "dropdown_fg_color": COR_FUNDO_CARD,
        "dropdown_hover_color": COR_PRIMARIA,
        "dropdown_text_color": COR_TEXTO,
        "text_color": COR_TEXTO,
        "font": FONT_CAMPO_SELECAO,
        "dropdown_font": FONT_CAMPO_SELECAO,
    }
    if largura is not None:
        opcoes["width"] = largura
    return opcoes


def texto_interno_campo(widget: ctk.CTkTextbox | tk.Text) -> tk.Text:
    """``tk.Text`` interno (ortografia, tags) a partir de ``CTkTextbox`` ou ``tk.Text``."""
    if isinstance(widget, ctk.CTkTextbox):
        return widget._textbox
    return widget


def resolver_entrada_ctk(
    widget: tk.Misc,
    *conjuntos: dict[str, ctk.CTkEntry],
) -> ctk.CTkEntry | None:
    """Devolve o ``CTkEntry`` quando o evento vem do widget ou do ``_entry`` interno."""
    for entradas in conjuntos:
        encontrado = resolver_ctk_entry(widget, entradas)
        if encontrado is not None:
            return encontrado
    return None


def criar_painel_ctk_com_titulo(pai: ctk.CTkBaseClass, titulo: str) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
    """Moldura arredondada com título — grupos visuais CustomTkinter."""
    externo = ctk.CTkFrame(
        pai,
        fg_color=COR_FUNDO,
        corner_radius=RAIO_BORDA,
        border_width=1,
        border_color=COR_BORDA,
    )
    registrar_painel_tema(pai, externo)
    ctk.CTkLabel(externo, text=titulo, font=FONT_PAINEL_TITULO, anchor="w").pack(
        fill="x", padx=12, pady=(10, 4)
    )
    conteudo = ctk.CTkFrame(externo, fg_color="transparent")
    conteudo.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    return externo, conteudo


def opcoes_texto_tk_embutido() -> dict[str, Any]:
    """Cores para ``tk.Text`` em diálogos (ajuda, etc.)."""
    cores = obter_cores_tema()
    return {
        "bg": cores["entrada"],
        "fg": cores["texto"],
        "insertbackground": cores["texto"],
        "selectbackground": cores["destaque"],
        "selectforeground": resolver_cor(COR_TEXTO_BOTAO_ATIVO),
        "highlightthickness": 1,
        "highlightbackground": cores["borda"],
        "highlightcolor": cores["destaque"],
        "borderwidth": 0,
    }


def opcoes_listbox_tk_embutido() -> dict[str, Any]:
    cores = obter_cores_tema()
    return {
        "bg": cores["entrada"],
        "fg": cores["texto"],
        "selectbackground": cores["destaque"],
        "selectforeground": resolver_cor(COR_TEXTO_BOTAO_ATIVO),
        "highlightthickness": 0,
        "borderwidth": 0,
    }


def aplicar_validacao_entrada_ctk(entrada: ctk.CTkEntry, comando: str) -> None:
    entrada._entry.configure(validate="key", validatecommand=(comando, "%P"))


def icursor_fim_entrada_ctk(entrada: ctk.CTkEntry) -> None:
    entrada._entry.icursor(tk.END)


def resolver_ctk_entry(
    widget: tk.Misc,
    entradas: dict[str, ctk.CTkEntry],
) -> ctk.CTkEntry | None:
    if isinstance(widget, ctk.CTkEntry) and widget in entradas.values():
        return widget
    for entrada in entradas.values():
        if widget is entrada._entry:
            return entrada
    return None
