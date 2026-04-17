"""
Interface gráfica principal do RDO: cliente, cabeçalho, relatório por dia e calendário.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk
from datetime import date, datetime
from pathlib import Path
from typing import Any

from tkcalendar import Calendar

from rdo_diario.calculo_metricas_horas import (
    agregar_metricas_mes,
    calcular_metricas_horas_para_dia,
    formatar_resumo_metricas_texto,
    gerar_relatorio_metricas_mes_texto,
)
from rdo_diario.config_horas import (
    carregar_config_regras_horas,
    conjunto_feriados_iso_para_ano,
    garantir_arquivo_config_regras_existe,
    salvar_config_regras_horas,
    sincronizar_feriados_brasil,
)
from rdo_diario.horario_util import (
    formatar_minutos_como_texto,
    normalizar_duracao_hhmm,
    normalizar_texto_horario,
    texto_duracao_permitido_na_digitacao,
    texto_horario_permitido_na_digitacao,
)
from rdo_diario.gerar_excel_relatorios import gerar_relatorios_excel
from rdo_diario.paths import ARQUIVO_CONFIG_REGRAS_HORAS_JSON, PASTA_DADOS_RDO
from rdo_diario.schema import (
    CAMPOS_JSON_DESLOCAMENTO,
    CAMPOS_JSON_PONTO,
    CAMPOS_JSON_TEXTO_DIA,
    CHAVE_JSON_BATIDAS_PONTO,
    CHAVE_JSON_FOLHA_RELATORIO_MES,
    CHAVE_JSON_METRICAS_HORAS,
    CHAVE_JSON_NUMERO_RELATORIO_MES,
    CAMPOS_JSON_CABECALHO,
    CHAVE_JSON_CONTRATANTE,
    CHAVE_JSON_NATUREZA_SERVICO,
    ROTULOS_CABECALHO,
    ROTULOS_HORARIO,
    ROTULOS_TEMPO_ATIVIDADE_DIA,
    ROTULOS_TEXTO_DIA,
    aplicar_metadados_data_no_registro_diario,
    extrair_horarios_do_registro_dia,
    nome_dia_semana_portugues,
    registro_de_dia_possui_conteudo,
)
from rdo_diario.storage import (
    carregar_documento_json,
    carregar_ou_criar_cliente,
    listar_clientes_salvos,
    obter_documento_cliente_inicial,
    salvar_documento_json,
    salvar_memoria_ultimo_cliente,
)
from rdo_diario.dicionario_ortografia_usuario import (
    adicionar_palavra,
    carregar_lista,
    conjunto_para_filtragem,
    salvar_lista,
    trecho_deve_ser_ignorado,
)
from rdo_diario.verificacao_ortografia import (
    extrair_sugestoes_do_match,
    offset_caractere_para_indice_tk,
    verificar_com_languagetool,
)


# Patch para corrigir bug em tkcalendar 1.5.0: KeyError em tooltip quando widgets são recriados
def _patch_tkcalendar_tooltip() -> None:
    """
    Corrige KeyError em tkcalendar.tooltip.TooltipWrapper.display_tooltip quando tentando
    acessar widget que não existe mais no dicionário interno durante renderização de calendário.
    """
    try:
        from tkcalendar import tooltip as tkcal_tooltip

        if hasattr(tkcal_tooltip, 'TooltipWrapper'):
            original_display = tkcal_tooltip.TooltipWrapper.display_tooltip

            def patched_display(self: Any) -> None:
                try:
                    original_display(self)
                except KeyError:
                    # Widget foi destruído/recriado durante renderização, ignorar erro
                    pass

            tkcal_tooltip.TooltipWrapper.display_tooltip = patched_display
    except Exception:
        # Se não conseguir fazer patch, continuar normalmente
        pass


_patch_tkcalendar_tooltip()


# Tags tkcalendar: número do dia em vermelho só em feriados (JSON em dados_rdo)
TAG_CAL_VM_DU = "cal_vm_du"
TAG_CAL_VM_DU_P = "cal_vm_du_p"
TAG_CAL_VM_FDS = "cal_vm_fds"
TAG_CAL_VM_FDS_P = "cal_vm_fds_p"
TAG_CAL_VM_OM_DU = "cal_vm_om_du"
TAG_CAL_VM_OM_DU_P = "cal_vm_om_du_p"
TAG_CAL_VM_OM_FDS = "cal_vm_om_fds"
TAG_CAL_VM_OM_FDS_P = "cal_vm_om_fds_p"

_TAGS_DESTAQUE_VERMELHO: tuple[str, ...] = (
    TAG_CAL_VM_DU,
    TAG_CAL_VM_DU_P,
    TAG_CAL_VM_FDS,
    TAG_CAL_VM_FDS_P,
    TAG_CAL_VM_OM_DU,
    TAG_CAL_VM_OM_DU_P,
    TAG_CAL_VM_OM_FDS,
    TAG_CAL_VM_OM_FDS_P,
)


def _grelha_datas_exibidas_calendario(cal: Calendar) -> list[date]:
    """Datas de cada célula visível (igual ao `tkcalendar` com «outros» meses)."""
    year, month = cal._date.year, cal._date.month
    g = cal._cal.monthdatescalendar(year, month)
    next_m = month + 1
    y = year
    if next_m == 13:
        next_m = 1
        y += 1
    if len(g) < 6:
        if g[-1][-1].month == month:
            i = 0
        else:
            i = 1
        g.append(cal._cal.monthdatescalendar(y, next_m)[i])
        if len(g) < 6:
            g.append(cal._cal.monthdatescalendar(y, next_m)[i + 1])
    return [d for semana in g for d in semana]


class CalendarRdo(Calendar):
    """
    Corrige o clique em dias do mês anterior/seguinte quando a célula usa estilo de evento
    (verde, feriado, etc.): o ``tkcalendar`` só navega de mês se o estilo for ``normal_om`` /
    ``we_om``, senão interpreta o dia no mês visível errado.

    A data efetiva da célula é obtida pela mesma grelha que o desenho do mês (``monthdatescalendar``).

    Também corrige KeyError em tooltips quando widgets são recriados durante renderização.
    """

    def _on_click(self, event: tk.Event) -> None:  # type: ignore[override]
        if self._properties.get("state") != "normal":
            return
        label = event.widget
        try:
            if "disabled" in label.state():
                return
        except tk.TclError:
            return
        day_txt = str(label.cget("text") or "").strip()
        if not day_txt:
            return
        try:
            dia_rotulo = int(day_txt)
        except ValueError:
            return

        for i in range(6):
            for j in range(7):
                if self._calendar[i][j] != label:
                    continue
                celulas = _grelha_datas_exibidas_calendario(self)
                idx = i * 7 + j
                if idx >= len(celulas):
                    return
                cell_date = celulas[idx]
                if cell_date.day != dia_rotulo:
                    return

                self._remove_selection()
                if cell_date.year != self._date.year or cell_date.month != self._date.month:
                    ym_old = (self._date.year, self._date.month)
                    self.see(cell_date)
                    if (self._date.year, self._date.month) != ym_old:
                        self.event_generate("<<CalendarMonthChanged>>")

                self._sel_date = cell_date
                self._display_selection()
                if self._textvariable is not None:
                    self._textvariable.set(self.format_date(self._sel_date))
                self.event_generate("<<CalendarSelected>>")
                return

        Calendar._on_click(self, event)


def _criar_widget_calendario(pai: tk.Misc, *, compacto: bool = False) -> CalendarRdo:
    """
    Instancia o calendário (subclasse que corrige clique em dias de outros meses).

    Tenta locale pt_BR; se falhar, usa o padrão do sistema.
    """
    fonte = ("Segoe UI", 8) if compacto else ("Segoe UI", 9)
    argumentos: dict = {
        "selectmode": "day",
        "date_pattern": "yyyy-mm-dd",
        "font": fonte,
        "showweeknumbers": True,
        "selectbackground": "#1d4ed8",
        "selectforeground": "#ffffff",
    }
    try:
        return CalendarRdo(pai, locale="pt_BR", **argumentos)
    except Exception:
        return CalendarRdo(pai, **argumentos)


def _configurar_tags_destaque_vermelho(cal: Calendar) -> None:
    """Cores alinhadas ao tema do calendário (fundo) + texto vermelho."""
    fg = "#c1121f"
    cal.tag_config(TAG_CAL_VM_DU, foreground=fg, background=cal.cget("normalbackground"))
    cal.tag_config(TAG_CAL_VM_DU_P, foreground=fg, background="#7ccd7c")
    cal.tag_config(TAG_CAL_VM_FDS, foreground=fg, background=cal.cget("weekendbackground"))
    cal.tag_config(TAG_CAL_VM_FDS_P, foreground=fg, background="#7ccd7c")
    cal.tag_config(TAG_CAL_VM_OM_DU, foreground=fg, background=cal.cget("othermonthbackground"))
    cal.tag_config(TAG_CAL_VM_OM_DU_P, foreground=fg, background="#7ccd7c")
    cal.tag_config(TAG_CAL_VM_OM_FDS, foreground=fg, background=cal.cget("othermonthwebackground"))
    cal.tag_config(TAG_CAL_VM_OM_FDS_P, foreground=fg, background="#7ccd7c")


def _tag_destaque_vermelho_para_data(
    d: date,
    ano_visivel: int,
    mes_visivel: int,
    preenchido: bool,
    feriados_iso: set[str],
) -> str | None:
    """Tag só se a data for feriado no JSON; ``None`` nos restantes dias."""
    if d.isoformat() not in feriados_iso:
        return None
    fds = d.weekday() >= 5
    no_mes_visivel = d.month == mes_visivel and d.year == ano_visivel
    if not no_mes_visivel:
        if fds:
            return TAG_CAL_VM_OM_FDS_P if preenchido else TAG_CAL_VM_OM_FDS
        return TAG_CAL_VM_OM_DU_P if preenchido else TAG_CAL_VM_OM_DU
    if fds:
        return TAG_CAL_VM_FDS_P if preenchido else TAG_CAL_VM_FDS
    return TAG_CAL_VM_DU_P if preenchido else TAG_CAL_VM_DU


def _texto_tooltip_destaque_calendario(d: date) -> str:
    if d.weekday() >= 5:
        return "Feriado (fim de semana)"
    return "Feriado"


class AplicacaoRdo(tk.Tk):
    """Janela principal: seleção de cliente, abas de dados fixos e relatório diário."""

    TAG_EVENTO_DIA_PREENCHIDO = "dia_preenchido"
    TAG_DIA_RELATORIO_EM_EDICAO = "dia_relatorio_em_edicao"
    TAG_ERRO_ORTOGRAFIA = "erro_ortografia"

    def __init__(self) -> None:
        super().__init__()
        self.title("Relatório de atividades diárias")
        self.geometry("980x760")
        self.minsize(720, 600)

        self._documento_atual: dict[str, Any] | None = None
        self._caminho_arquivo_atual: Path | None = None
        self._data_em_edicao: date = date.today()
        self._widgets_cabecalho: dict[str, ttk.Entry] = {}
        self._widgets_campos_dia: dict[str, tk.Text] = {}
        self._widgets_tempo_atividade: dict[str, ttk.Entry] = {}
        self._widgets_horarios: dict[str, ttk.Entry] = {}
        self._id_agendamento_salvar: str | None = None
        self._widget_calendario: Calendar | None = None
        self._combo_selecao_cliente: ttk.Combobox | None = None
        self._mapa_rotulo_para_caminho: dict[str, Path] = {}
        self._rotulo_texto_data: ttk.Label | None = None
        self._rotulo_contagem_mes: ttk.Label | None = None
        self._comando_validacao_entrada_hora = None
        self._comando_validacao_entrada_duracao = None
        self._ortografia_timers_por_widget: dict[int, str] = {}
        self._ortografia_job_id_por_widget: dict[int, int] = {}
        self._ortografia_alvos_por_widget: dict[int, list[dict[str, Any]]] = {}
        self._conjunto_dicionario_ortografia: set[str] = conjunto_para_filtragem()
        self._config_regras_horas: dict[str, Any] = carregar_config_regras_horas()
        self._rotulo_metricas_dia: ttk.Label | None = None
        self._rotulo_metricas_mes: ttk.Label | None = None

        self._montar_barra_menu()
        self._montar_barra_cliente()
        self._comando_validacao_entrada_hora = self.register(
            lambda proposta: texto_horario_permitido_na_digitacao(proposta)
        )
        self._comando_validacao_entrada_duracao = self.register(
            lambda proposta: texto_duracao_permitido_na_digitacao(proposta)
        )
        self._montar_corpo_janela()

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar_janela)
        self.after(200, self._inicializar_apos_abrir)

    def _montar_barra_menu(self) -> None:
        """Cria os menus «Arquivo» e «Revisão»."""
        barra_menu = tk.Menu(self)
        menu_arquivo = tk.Menu(barra_menu, tearoff=0)
        menu_arquivo.add_command(label="Salvar agora", command=self._salvar_documento_agora)
        barra_menu.add_cascade(label="Arquivo", menu=menu_arquivo)
        menu_revisao = tk.Menu(barra_menu, tearoff=0)
        menu_revisao.add_command(
            label="Verificar ortografia e gramática agora",
            command=self._verificar_ortografia_todos_campos_relatorio,
        )
        menu_revisao.add_command(
            label="Dicionário pessoal (palavras e siglas)…",
            command=self._abrir_dialogo_dicionario_ortografia,
        )
        menu_revisao.add_command(
            label="Sobre a verificação ortográfica…",
            command=self._mostrar_info_verificacao_ortografia,
        )
        barra_menu.add_cascade(label="Revisão", menu=menu_revisao)
        menu_horas = tk.Menu(barra_menu, tearoff=0)
        menu_horas.add_command(
            label="Editar regras de horas (JSON)…",
            command=self._abrir_editor_regras_horas,
        )
        menu_horas.add_command(
            label="Sincronizar feriados nacionais (Brasil)…",
            command=self._dialogo_sincronizar_feriados_brasil,
        )
        menu_horas.add_command(
            label="Copiar relatório detalhado do mês (métricas)…",
            command=self._copiar_relatorio_metricas_mes,
        )
        menu_horas.add_separator()
        menu_horas.add_command(
            label="Abrir pasta do ficheiro de regras…",
            command=self._abrir_pasta_config_regras_horas,
        )
        barra_menu.add_cascade(label="Horas", menu=menu_horas)
        self.config(menu=barra_menu)

    def _montar_barra_cliente(self) -> None:
        """Barra superior: combo de clientes, novo cliente e botão salvar."""
        barra = ttk.Frame(self, padding=6)
        barra.pack(fill=tk.X)
        ttk.Label(barra, text="Cliente (contratante + natureza):").pack(side=tk.LEFT, padx=(0, 6))
        self._combo_selecao_cliente = ttk.Combobox(barra, width=70, state="readonly")
        self._combo_selecao_cliente.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self._combo_selecao_cliente.bind("<<ComboboxSelected>>", self._ao_trocar_cliente_combo)
        ttk.Button(barra, text="Novo cliente…", command=self._abrir_dialogo_novo_cliente).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(barra, text="Salvar", command=self._salvar_documento_agora).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            barra,
            text="Gerar Excel (RDO/FT)",
            command=self._gerar_relatorios_excel,
        ).pack(side=tk.LEFT, padx=8)

    def _criar_area_com_rolagem(self, pai: tk.Widget) -> ttk.Frame:
        """
        Devolve um `Frame` interior com scroll vertical; útil para formulários longos.
        """
        externo = ttk.Frame(pai)
        externo.pack(fill=tk.BOTH, expand=True)
        tela = tk.Canvas(externo, highlightthickness=0)
        barra = ttk.Scrollbar(externo, orient=tk.VERTICAL, command=tela.yview)
        interior = ttk.Frame(tela)
        interior.bind(
            "<Configure>",
            lambda _e: tela.configure(scrollregion=tela.bbox("all")),
        )
        id_janela = tela.create_window((0, 0), window=interior, anchor="nw")

        def _ajustar_largura(_evt: tk.Event | None = None) -> None:
            tela.itemconfigure(id_janela, width=tela.winfo_width())

        tela.bind("<Configure>", _ajustar_largura)
        tela.configure(yscrollcommand=barra.set)
        tela.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)

        def _roda_mouse(evento: tk.Event) -> str:
            tela.yview_scroll(int(-1 * (evento.delta / 120)), "units")
            return "break"

        tela.bind("<Enter>", lambda _e: tela.bind_all("<MouseWheel>", _roda_mouse))
        tela.bind("<Leave>", lambda _e: tela.unbind_all("<MouseWheel>"))
        return interior

    def _criar_texto_multilinha_com_rolagem(
        self,
        pai: tk.Widget,
        *,
        altura: int = 9,
        expandir_verticalmente: bool = True,
    ) -> tk.Text:
        """
        Caixa de texto com várias linhas, barra de rolagem vertical e roda do rato.

        Se ``expandir_verticalmente`` for False, a moldura não compete por altura
        (útil para campos baixos e deixar espaço para ponto / outros blocos).
        """
        moldura = ttk.Frame(pai)
        if expandir_verticalmente:
            moldura.pack(fill=tk.BOTH, expand=True, pady=2)
        else:
            moldura.pack(fill=tk.X, expand=False, pady=2)
        barra = ttk.Scrollbar(moldura)
        texto = tk.Text(
            moldura,
            height=altura,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            yscrollcommand=barra.set,
        )
        barra.config(command=texto.yview)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _roda_em_texto(evento: tk.Event) -> str:
            texto.yview_scroll(int(-1 * (evento.delta / 120)), "units")
            return "break"

        texto.bind("<Enter>", lambda _e: texto.bind_all("<MouseWheel>", _roda_em_texto))
        texto.bind("<Leave>", lambda _e: texto.unbind_all("<MouseWheel>"))
        texto.tag_configure(self.TAG_ERRO_ORTOGRAFIA, foreground="#cc0000", underline=True)
        texto.bind(
            "<KeyRelease>",
            lambda e, w=texto: self._ao_tecla_released_campo_relatorio(w, e),
        )
        texto.bind("<Button-3>", lambda e, w=texto: self._menu_correcoes_ortografia(w, e))
        texto.bind("<Control-Button-1>", lambda e, w=texto: self._menu_correcoes_ortografia(w, e))
        return texto

    def _montar_linha_tempo_atividade(self, pai: tk.Widget, chave_json_tempo: str) -> None:
        """Uma linha com rótulo e campo de duração (h:mm) para extra-escopo ou ociosidade."""
        linha = ttk.Frame(pai)
        linha.pack(fill=tk.X, pady=(2, 0))
        rotulo = ROTULOS_TEMPO_ATIVIDADE_DIA[chave_json_tempo]
        ttk.Label(linha, text=rotulo + ":").pack(side=tk.LEFT, padx=(0, 6))
        entrada = ttk.Entry(
            linha,
            width=10,
            font=("Segoe UI", 10),
            validate="key",
            validatecommand=(self._comando_validacao_entrada_duracao, "%P"),
        )
        entrada.pack(side=tk.LEFT)
        entrada.bind("<KeyRelease>", self._ao_tecla_solta_campo_duracao)
        entrada.bind("<FocusOut>", lambda e, w=entrada: self._ao_sair_foco_campo_duracao(w))
        self._widgets_tempo_atividade[chave_json_tempo] = entrada

    def _ao_tecla_released_campo_relatorio(self, widget: tk.Text, evento: tk.Event) -> None:
        """Autosave e debounce da verificação ortográfica (LanguageTool) nos textos do relatório."""
        self._agendar_salvamento_automatico(evento)
        self._agendar_verificacao_ortografia(widget)

    def _rotulo_curto_menu(self, texto: str, maximo: int = 72) -> str:
        """Evita linhas demasiado longas no menu; duplica «&» para o Tk não tratar como atalho."""
        t = texto.replace("\n", " ").replace("\r", " ").strip()
        t = t.replace("&", "&&")
        if len(t) <= maximo:
            return t or " "
        return t[: maximo - 1] + "…"

    def _menu_correcoes_ortografia(self, widget: tk.Text, evento: tk.Event) -> None:
        """Menu de contexto com todas as sugestões do LanguageTool no trecho sob o cursor."""
        try:
            indice = widget.index(f"@{evento.x},{evento.y}")
        except tk.TclError:
            return
        wid = id(widget)
        alvos = self._ortografia_alvos_por_widget.get(wid) or []
        escolhido: dict[str, Any] | None = None
        for alvo in alvos:
            try:
                if widget.compare(indice, ">=", alvo["inicio"]) and widget.compare(indice, "<", alvo["fim"]):
                    escolhido = alvo
                    break
            except tk.TclError:
                continue
        if not escolhido:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label=self._rotulo_curto_menu(escolhido.get("mensagem") or "Problema detectado", 100),
            state=tk.DISABLED,
        )
        menu.add_separator()
        sugestoes: list[str] = escolhido.get("sugestoes") or []
        if not sugestoes:
            menu.add_command(label="(Sem sugestão automática)", state=tk.DISABLED)
        else:
            limite_primeiro_menu = 20
            primeira = sugestoes[:limite_primeiro_menu]
            restantes = sugestoes[limite_primeiro_menu:]
            ini, fim = escolhido["inicio"], escolhido["fim"]
            for sug in primeira:
                menu.add_command(
                    label=self._rotulo_curto_menu(sug, 76),
                    command=lambda s=sug, i=ini, f=fim, w=widget: self._aplicar_sugestao_ortografia(w, i, f, s),
                )
            if restantes:
                sub = tk.Menu(menu, tearoff=0)
                menu.add_cascade(
                    label=self._rotulo_curto_menu(f"Mais sugestões ({len(restantes)})…", 40),
                    menu=sub,
                )
                for sug in restantes:
                    sub.add_command(
                        label=self._rotulo_curto_menu(sug, 76),
                        command=lambda s=sug, i=ini, f=fim, w=widget: self._aplicar_sugestao_ortografia(
                            w, i, f, s
                        ),
                    )
        menu.add_separator()
        try:
            trecho_dic = widget.get(escolhido["inicio"], escolhido["fim"]).strip()
        except tk.TclError:
            trecho_dic = ""
        if trecho_dic:
            menu.add_command(
                label=self._rotulo_curto_menu(f"Adicionar «{trecho_dic}» ao dicionário pessoal", 70),
                command=lambda w=widget, t=trecho_dic, i=escolhido["inicio"], f=escolhido["fim"]: self._adicionar_ao_dicionario_e_reverificar(
                    w, t, i, f
                ),
            )
        try:
            menu.tk_popup(evento.x_root, evento.y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _adicionar_ao_dicionario_e_reverificar(
        self,
        widget: tk.Text,
        trecho: str,
        indice_inicio: str,
        indice_fim: str,
    ) -> None:
        """Guarda o trecho no dicionário local e volta a analisar o campo (ignora maiúsculas)."""
        if not trecho.strip():
            return
        try:
            atual = widget.get(indice_inicio, indice_fim).strip()
        except tk.TclError:
            atual = ""
        if atual.casefold() != trecho.casefold():
            trecho = atual or trecho
        if adicionar_palavra(trecho):
            self._conjunto_dicionario_ortografia = conjunto_para_filtragem()
            messagebox.showinfo(
                "Dicionário pessoal",
                f"«{trecho}» foi adicionado. Os avisos para esta forma deixam de aparecer.",
                parent=self,
            )
        else:
            messagebox.showinfo(
                "Dicionário pessoal",
                f"«{trecho}» já estava no dicionário.",
                parent=self,
            )
        self._executar_verificacao_ortografia(widget)

    def _abrir_dialogo_dicionario_ortografia(self) -> None:
        """Janela para listar, acrescentar e remover entradas do ficheiro JSON local."""
        topo = tk.Toplevel(self)
        topo.title("Dicionário ortográfico pessoal")
        topo.transient(self)
        topo.geometry("420x500")
        ttk.Label(
            topo,
            text="Palavras e siglas que o corretor não deve marcar (comparação sem maiúsculas).",
            wraplength=380,
        ).pack(fill=tk.X, padx=10, pady=(10, 4))
        moldura = ttk.Frame(topo, padding=8)
        moldura.pack(fill=tk.BOTH, expand=True)
        barra = ttk.Scrollbar(moldura)
        lista = tk.Listbox(moldura, height=16, yscrollcommand=barra.set, font=("Segoe UI", 10))
        barra.config(command=lista.yview)
        lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        for item in carregar_lista():
            lista.insert(tk.END, item)
        linha = ttk.Frame(topo, padding=(10, 0))
        linha.pack(fill=tk.X)
        ttk.Label(linha, text="Nova entrada:").pack(side=tk.LEFT)
        entrada = ttk.Entry(linha, width=32)
        entrada.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        def acrescentar() -> None:
            t = entrada.get().strip()
            if not t:
                return
            existentes = {lista.get(i).casefold() for i in range(lista.size())}
            if t.casefold() in existentes:
                messagebox.showinfo("Dicionário", "Esta entrada já está na lista.", parent=topo)
                return
            lista.insert(tk.END, t)
            lista.see(tk.END)
            entrada.delete(0, tk.END)

        def remover_selecionados() -> None:
            for i in reversed(lista.curselection()):
                lista.delete(i)

        botoes = ttk.Frame(topo, padding=10)
        botoes.pack(fill=tk.X)
        ttk.Button(linha, text="Adicionar", command=acrescentar).pack(side=tk.LEFT)
        ttk.Button(botoes, text="Remover selecionado(s)", command=remover_selecionados).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        def guardar_e_fechar() -> None:
            itens = [lista.get(i) for i in range(lista.size())]
            salvar_lista(itens)
            self._conjunto_dicionario_ortografia = conjunto_para_filtragem()
            self._verificar_ortografia_todos_campos_relatorio()
            topo.destroy()

        ttk.Button(botoes, text="Guardar e fechar", command=guardar_e_fechar).pack(side=tk.RIGHT)
        ttk.Button(botoes, text="Cancelar", command=topo.destroy).pack(side=tk.RIGHT, padx=(0, 8))
        entrada.bind("<Return>", lambda _e: acrescentar())

    def _aplicar_sugestao_ortografia(
        self,
        widget: tk.Text,
        indice_inicio: str,
        indice_fim: str,
        texto_corrigido: str,
    ) -> None:
        """Substitui o trecho marcado pela sugestão escolhida e volta a verificar o campo."""
        try:
            widget.delete(indice_inicio, indice_fim)
            widget.insert(indice_inicio, texto_corrigido)
        except tk.TclError:
            return
        wid = id(widget)
        self._ortografia_alvos_por_widget.pop(wid, None)
        widget.tag_remove(self.TAG_ERRO_ORTOGRAFIA, "1.0", tk.END)
        self._agendar_salvamento_automatico()
        self._executar_verificacao_ortografia(widget)

    def _agendar_verificacao_ortografia(self, widget: tk.Text) -> None:
        """Agenda verificação após pausa na digitação (evita exceder o limite gratuito da API)."""
        wid = id(widget)
        anterior = self._ortografia_timers_por_widget.pop(wid, None)
        if anterior is not None:
            try:
                self.after_cancel(anterior)
            except tk.TclError:
                pass
        self._ortografia_timers_por_widget[wid] = self.after(
            2800,
            lambda w=widget: self._executar_verificacao_ortografia(w),
        )

    def _executar_verificacao_ortografia(self, widget: tk.Text) -> None:
        """
        Consulta o LanguageTool em segundo plano e marca trechos com erro em vermelho.

        O texto é enviado ao serviço público (rede necessária). Veja o menu Revisão para detalhes.
        """
        wid = id(widget)
        self._ortografia_timers_por_widget.pop(wid, None)
        try:
            texto_ref = widget.get("1.0", "end-1c")
        except tk.TclError:
            return
        novo_id = self._ortografia_job_id_por_widget.get(wid, 0) + 1
        self._ortografia_job_id_por_widget[wid] = novo_id
        job_local = novo_id

        def trabalho_em_thread() -> None:
            correspondencias = verificar_com_languagetool(texto_ref)

            def aplicar_marcas() -> None:
                try:
                    if not widget.winfo_exists():
                        return
                except tk.TclError:
                    return
                if self._ortografia_job_id_por_widget.get(wid, 0) != job_local:
                    return
                try:
                    atual = widget.get("1.0", "end-1c")
                except tk.TclError:
                    return
                if atual != texto_ref:
                    self._ortografia_alvos_por_widget.pop(wid, None)
                    return
                widget.tag_remove(self.TAG_ERRO_ORTOGRAFIA, "1.0", tk.END)
                alvos: list[dict[str, Any]] = []
                conj_dic = self._conjunto_dicionario_ortografia
                for m in correspondencias:
                    try:
                        o = int(m.get("offset", 0))
                        lg = int(m.get("length", 0))
                    except (TypeError, ValueError):
                        continue
                    if lg <= 0:
                        continue
                    if o + lg > len(atual):
                        continue
                    if trecho_deve_ser_ignorado(atual, o, lg, conj_dic):
                        continue
                    i0 = offset_caractere_para_indice_tk(atual, o)
                    i1 = offset_caractere_para_indice_tk(atual, o + lg)
                    mensagem = str(m.get("message") or "").strip().replace("\n", " ")
                    sugestoes = extrair_sugestoes_do_match(m)
                    alvos.append(
                        {
                            "inicio": i0,
                            "fim": i1,
                            "mensagem": mensagem,
                            "sugestoes": sugestoes,
                        }
                    )
                    widget.tag_add(self.TAG_ERRO_ORTOGRAFIA, i0, i1)
                self._ortografia_alvos_por_widget[wid] = alvos

            self.after(0, aplicar_marcas)

        threading.Thread(target=trabalho_em_thread, daemon=True).start()

    def _verificar_ortografia_todos_campos_relatorio(self) -> None:
        """Dispara verificação imediata em todos os campos de texto do dia (serviço, extra, ociosidade)."""
        for _campo, widget in self._widgets_campos_dia.items():
            wid = id(widget)
            anterior = self._ortografia_timers_por_widget.pop(wid, None)
            if anterior is not None:
                try:
                    self.after_cancel(anterior)
                except tk.TclError:
                    pass
            self._executar_verificacao_ortografia(widget)

    def _mostrar_info_verificacao_ortografia(self) -> None:
        messagebox.showinfo(
            "Verificação ortográfica",
            "A revisão usa o serviço público gratuito LanguageTool (ortografia e gramática em "
            "português do Brasil).\n\n"
            "• O texto dos relatórios é enviado pela internet para análise.\n"
            "• Há limite de uso por IP; a verificação automática só corre alguns segundos após "
            "parar de digitar.\n"
            "• Erros aparecem a vermelho e sublinhados nos três campos de texto do relatório.\n"
            "• Clique com o botão direito (ou Ctrl+clique no Mac) num trecho vermelho para ver "
            "todas as sugestões de correção e aplicar uma delas.\n"
            "• Use «Dicionário pessoal» no menu Revisão para palavras e siglas que não devem ser "
            "marcadas (ficheiro local em dados_rdo).\n\n"
            "Mais informação: https://languagetool.org/",
        )

    def _montar_corpo_janela(self) -> None:
        """Abas «Dados fixos» e «Relatórios», com calendário na segunda."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        aba_cabecalho = ttk.Frame(notebook)
        aba_registros = ttk.Frame(notebook)
        notebook.add(aba_cabecalho, text="Cabeçalhos")
        notebook.add(aba_registros, text="Relatórios de trabalho")

        dica_cab = ttk.Label(
            aba_cabecalho,
            text="Informações destinadas ao cabeçalhos das planilha (RDO e FT).",
            wraplength=800,
        )
        dica_cab.pack(fill=tk.X, padx=8, pady=(8, 4))
        area_rolavel = self._criar_area_com_rolagem(aba_cabecalho)
        form_cab = ttk.Frame(area_rolavel, padding=12)
        form_cab.pack(fill=tk.BOTH, expand=True)
        for indice, campo in enumerate(CAMPOS_JSON_CABECALHO):
            ttk.Label(form_cab, text=ROTULOS_CABECALHO[campo] + ":").grid(
                row=indice, column=0, sticky=tk.NW, pady=4, padx=(0, 10)
            )
            entrada = ttk.Entry(form_cab, width=70)
            entrada.grid(row=indice, column=1, sticky=tk.EW, pady=4)
            entrada.bind("<KeyRelease>", self._agendar_salvamento_automatico)
            self._widgets_cabecalho[campo] = entrada
        form_cab.columnconfigure(1, weight=1)

        painel = ttk.PanedWindow(aba_registros, orient=tk.HORIZONTAL)
        painel.pack(fill=tk.BOTH, expand=True, padx=4, pady=8)

        coluna_formulario = ttk.Frame(painel)
        coluna_calendario = ttk.Frame(painel, width=275)
        painel.add(coluna_formulario, weight=4)
        painel.add(coluna_calendario, weight=0)

        moldura_dia = ttk.LabelFrame(coluna_formulario, text="Relatório: ", padding=8)
        moldura_dia.pack(fill=tk.BOTH, expand=True)

        linha_data = ttk.Frame(moldura_dia)
        linha_data.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(linha_data, text="Data selecionada:").pack(side=tk.LEFT)
        self._rotulo_texto_data = ttk.Label(linha_data, text="", font=("Segoe UI", 11, "bold"))
        self._rotulo_texto_data.pack(side=tk.LEFT, padx=8)
        self._rotulo_contagem_mes = ttk.Label(
            linha_data,
            text="",
            font=("Segoe UI", 10),
            foreground="#333333",
        )
        self._rotulo_contagem_mes.pack(side=tk.LEFT, padx=(12, 0))

        campos = ttk.Frame(moldura_dia)
        campos.pack(fill=tk.BOTH, expand=True)
        for campo in CAMPOS_JSON_TEXTO_DIA:
            ttk.Label(campos, text=ROTULOS_TEXTO_DIA[campo] + ":").pack(anchor=tk.W, pady=(6, 0))
            if campo in ("registro_extra_escopo", "registro_ociosidade"):
                texto = self._criar_texto_multilinha_com_rolagem(
                    campos,
                    altura=2,
                    expandir_verticalmente=False,
                )
            else:
                texto = self._criar_texto_multilinha_com_rolagem(campos, altura=9)
            self._widgets_campos_dia[campo] = texto
            if campo == "registro_extra_escopo":
                self._montar_linha_tempo_atividade(campos, "tempo_extra_escopo")
            elif campo == "registro_ociosidade":
                self._montar_linha_tempo_atividade(campos, "tempo_ociosidade")

        self._montar_secao_horarios(campos)

        moldura_cal = ttk.LabelFrame(coluna_calendario, text="Calendário", padding=4)
        moldura_cal.pack(side=tk.TOP, anchor=tk.N)
        ttk.Label(
            moldura_cal,
            text=(
                "Selecione uma data para visualizar / editar.\n"
                "Verde = relatório salvo·\n"
                "Azul = data em edição.\n"
                "Vermelho = feriado nacional.\n"
            ),
            font=("Segoe UI", 8),
            wraplength=260,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, fill=tk.X)
        self._widget_calendario = _criar_widget_calendario(moldura_cal, compacto=True)
        self._widget_calendario.pack(side=tk.TOP, pady=(4, 0))
        try:
            self._widget_calendario.tag_config(
                self.TAG_EVENTO_DIA_PREENCHIDO,
                background="#7ccd7c",
                foreground="#000000",
            )
            self._widget_calendario.tag_config(
                self.TAG_DIA_RELATORIO_EM_EDICAO,
                background="#ea580c",
                foreground="#ffffff",
            )
            _configurar_tags_destaque_vermelho(self._widget_calendario)
        except tk.TclError:
            pass
        self._widget_calendario.bind("<<CalendarSelected>>", self._ao_selecionar_data_calendario)
        self._widget_calendario.bind("<<CalendarMonthChanged>>", self._ao_mudar_mes_calendario)
        self._montar_painel_metricas_calendario(moldura_cal)

    def _montar_painel_metricas_calendario(self, moldura_cal: ttk.Frame) -> None:
        """Abaixo do calendário: métricas do dia selecionado e totais do mês."""
        painel = ttk.LabelFrame(
            moldura_cal,
            text="Métricas de horas diárias e mensais",
            padding=6,
        )
        painel.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(
            painel,
            text=(
                "Métricas do dia:"
                ),
            font=("Segoe UI", 8),
            wraplength=260,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, fill=tk.X)
        self._rotulo_metricas_dia = ttk.Label(
            painel,
            text="",
            font=("Segoe UI", 9),
            wraplength=260,
            justify=tk.LEFT,
        )
        self._rotulo_metricas_dia.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))
        self._rotulo_metricas_mes = ttk.Label(
            painel,
            text="",
            font=("Segoe UI", 8),
            foreground="#374151",
            wraplength=260,
            justify=tk.LEFT,
        )
        self._rotulo_metricas_mes.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

    def _atualizar_painel_metricas_horas(self) -> None:
        """Atualiza os rótulos sob o calendário com o dia atual e o mês corrente."""
        if not self._rotulo_metricas_dia or not self._rotulo_metricas_mes:
            return
        if not self._documento_atual:
            self._rotulo_metricas_dia.configure(text="(Selecione um cliente.)")
            self._rotulo_metricas_mes.configure(text="")
            return
        payload = self._payload_formulario_dia_sem_contagem_mes()
        m = calcular_metricas_horas_para_dia(
            self._data_em_edicao, payload, self._config_regras_horas
        )
        if not m.get("calculo_valido"):
            self._rotulo_metricas_dia.configure(
                text=str(m.get("mensagem") or "Preencha os horários de ponto para calcular.")
            )
        else:
            self._rotulo_metricas_dia.configure(
                text=(
                    f"Trabalhadas: {formatar_minutos_como_texto(int(m.get('minutos_trabalhados_total') or 0))}\n"
                    f"Normais: {formatar_minutos_como_texto(int(m.get('minutos_normais') or 0))}\n"
                    f"Extra 50%: {formatar_minutos_como_texto(int(m.get('minutos_extra_50') or 0))}\n"
                    f"Extra 100%: {formatar_minutos_como_texto(int(m.get('minutos_extra_100') or 0))}\n"
                    f"Noturno: {formatar_minutos_como_texto(int(m.get('minutos_adicional_noturno') or 0))}"
                )
            )
        regs = self._registros_diarios_efetivos_para_contagem()
        agg = agregar_metricas_mes(
            regs,
            self._data_em_edicao.year,
            self._data_em_edicao.month,
            self._config_regras_horas,
        )
        n = int(agg.get("dias_com_calculo_valido") or 0)
        self._rotulo_metricas_mes.configure(
            text=(
                f"Métricas mensais:\n\n"
                f"Data: {self._data_em_edicao.month:02d}/{self._data_em_edicao.year}\n"
                f"Dias válidos: {n}\n"
                f"{formatar_resumo_metricas_texto(agg)}"
            )
        )

    def _abrir_editor_regras_horas(self) -> None:
        """Janela com o JSON de regras para edição manual."""
        self._config_regras_horas = carregar_config_regras_horas()
        topo = tk.Toplevel(self)
        topo.title("Regras de horas (JSON)")
        topo.transient(self)
        topo.geometry("720x560")
        ttk.Label(
            topo,
            text=str(ARQUIVO_CONFIG_REGRAS_HORAS_JSON),
            font=("Segoe UI", 8),
            foreground="#444444",
        ).pack(fill=tk.X, padx=8, pady=(8, 4))
        corpo = ttk.Frame(topo, padding=(8, 0))
        corpo.pack(fill=tk.BOTH, expand=True)
        texto = scrolledtext.ScrolledText(
            corpo,
            wrap=tk.NONE,
            font=("Consolas", 10),
            undo=True,
        )
        texto.pack(fill=tk.BOTH, expand=True)
        try:
            texto.insert("1.0", json.dumps(self._config_regras_horas, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            texto.insert("1.0", "{}")

        botoes = ttk.Frame(topo, padding=8)
        botoes.pack(fill=tk.X)

        def guardar() -> None:
            bruto = texto.get("1.0", "end-1c")
            try:
                doc = json.loads(bruto)
            except json.JSONDecodeError as erro:
                messagebox.showerror("JSON inválido", str(erro), parent=topo)
                return
            if not isinstance(doc, dict):
                messagebox.showerror("JSON inválido", "O ficheiro deve ser um objeto JSON «{…}».", parent=topo)
                return
            try:
                salvar_config_regras_horas(doc)
            except OSError as erro:
                messagebox.showerror("Gravar", str(erro), parent=topo)
                return
            self._config_regras_horas = carregar_config_regras_horas()
            self._atualizar_painel_metricas_horas()
            self._atualizar_marcadores_calendario()
            messagebox.showinfo("Regras de horas", "Alterações gravadas.", parent=topo)
            topo.destroy()

        ttk.Button(botoes, text="Guardar e fechar", command=guardar).pack(side=tk.RIGHT)
        ttk.Button(botoes, text="Cancelar", command=topo.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _dialogo_sincronizar_feriados_brasil(self) -> None:
        """Pede o ano central e sincroniza feriados BR (ano−1, ano, ano+1)."""
        padrao = self._data_em_edicao.year
        ano = simpledialog.askinteger(
            "Feriados nacionais (Brasil)",
            "Ano de referência (serão atualizados também o ano anterior e o seguinte):",
            initialvalue=padrao,
            minvalue=2000,
            maxvalue=2100,
            parent=self,
        )
        if ano is None:
            return
        anos = sorted({ano - 1, ano, ano + 1})
        try:
            novo = sincronizar_feriados_brasil(self._config_regras_horas, anos)
            salvar_config_regras_horas(novo)
        except RuntimeError as erro:
            messagebox.showerror("Sincronizar feriados", str(erro), parent=self)
            return
        except OSError as erro:
            messagebox.showerror("Gravar", str(erro), parent=self)
            return
        self._config_regras_horas = carregar_config_regras_horas()
        self._atualizar_painel_metricas_horas()
        self._atualizar_marcadores_calendario()
        messagebox.showinfo(
            "Feriados",
            f"Feriados nacionais atualizados para os anos {anos[0]}, {anos[1]} e {anos[2]}.",
            parent=self,
        )

    def _copiar_relatorio_metricas_mes(self) -> None:
        """Gera texto com todas as linhas do mês da data selecionada e copia para a área de transferência."""
        if not self._documento_atual:
            messagebox.showinfo("Relatório", "Abra um cliente primeiro.", parent=self)
            return
        regs = self._registros_diarios_efetivos_para_contagem()
        a, m = self._data_em_edicao.year, self._data_em_edicao.month
        texto = gerar_relatorio_metricas_mes_texto(regs, a, m, self._config_regras_horas)
        try:
            self.clipboard_clear()
            self.clipboard_append(texto)
            self.update()
        except tk.TclError as erro:
            messagebox.showerror("Área de transferência", str(erro), parent=self)
            return
        messagebox.showinfo(
            "Relatório",
            f"Texto do mês {m:02d}/{a} copiado para a área de transferência.",
            parent=self,
        )

    def _abrir_pasta_config_regras_horas(self) -> None:
        """Abre o explorador de ficheiros na pasta `dados_rdo`."""
        pasta = ARQUIVO_CONFIG_REGRAS_HORAS_JSON.parent
        try:
            if sys.platform == "win32":
                os.startfile(pasta)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(pasta)], check=False)
            else:
                subprocess.run(["xdg-open", str(pasta)], check=False)
        except OSError as erro:
            messagebox.showerror("Abrir pasta", str(erro), parent=self)

    def _montar_secao_horarios(self, pai: tk.Widget) -> None:
        """Bloco de horários: linha ponto, linha deslocamento, rótulo de jornada líquida."""
        moldura = ttk.LabelFrame(
            pai,
            text="Horários — ponto e deslocamento (24h, HH:MM)",
            padding=8,
        )
        moldura.pack(fill=tk.X, pady=(14, 6))
        # ttk.Label(
        #     moldura,
        #     text="Ponto na primeira linha; deslocamento ida e volta na segunda.",
        #     font=("Segoe UI", 8),
        # ).pack(anchor=tk.W, pady=(0, 6))

        def par_horario(linha: ttk.Frame, chave_campo: str) -> None:
            bloco = ttk.Frame(linha)
            bloco.pack(side=tk.LEFT, padx=(0, 16), pady=2)
            ttk.Label(bloco, text=ROTULOS_HORARIO[chave_campo] + ":").pack(side=tk.LEFT, padx=(0, 4))
            ent = ttk.Entry(
                bloco,
                width=6,
                font=("Segoe UI", 10),
                validate="key",
                validatecommand=(self._comando_validacao_entrada_hora, "%P"),
            )
            ent.pack(side=tk.LEFT)
            ent.bind("<KeyRelease>", self._ao_tecla_solta_campo_hora)
            ent.bind("<FocusOut>", lambda e, w=ent: self._ao_sair_foco_campo_hora(w))
            self._widgets_horarios[chave_campo] = ent

        linha_ponto = ttk.Frame(moldura)
        linha_ponto.pack(fill=tk.X)
        ttk.Label(linha_ponto, text="Ponto:", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        for chave in CAMPOS_JSON_PONTO:
            par_horario(linha_ponto, chave)

        linha_desloc = ttk.Frame(moldura)
        linha_desloc.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(linha_desloc, text="Deslocamento:", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        for chave in CAMPOS_JSON_DESLOCAMENTO:
            par_horario(linha_desloc, chave)

    def _aplicar_formatacao_campo_entrada(self, entrada: ttk.Entry, tipo: str = "horario") -> None:
        """
        Aplica formatação automática para horários ou durações.
        
        tipo: "horario" (HH:MM) ou "duracao" (H:MM)
        Insere ":" automaticamente após 4 dígitos.
        """
        texto = entrada.get()
        if ":" in texto:
            return
        digitos = "".join(c for c in texto if c.isdigit())
        if len(digitos) == 4:
            normalizador = normalizar_texto_horario if tipo == "horario" else normalizar_duracao_hhmm
            normalizado = normalizador(digitos)
            if normalizado:
                entrada.delete(0, tk.END)
                entrada.insert(0, normalizado)
                entrada.icursor(tk.END)

    def _normalizar_campo_entrada(self, entrada: ttk.Entry, tipo: str = "horario") -> None:
        """
        Normaliza campo ao sair (FocusOut).
        
        tipo: "horario" (HH:MM) ou "duracao" (H:MM)
        Garante que o valor está no formato correto.
        """
        bruto = entrada.get().strip()
        if not bruto:
            return
        normalizador = normalizar_texto_horario if tipo == "horario" else normalizar_duracao_hhmm
        normalizado = normalizador(bruto)
        if normalizado != bruto or (bruto and not normalizado):
            entrada.delete(0, tk.END)
            if normalizado:
                entrada.insert(0, normalizado)

    def _ao_tecla_solta_campo_hora(self, evento: tk.Event) -> None:
        """Após digitar hora: tenta inserir «:» após 4 dígitos, atualiza total e agenda save."""
        widget = evento.widget
        if isinstance(widget, ttk.Entry) and widget in self._widgets_horarios.values():
            self.after_idle(lambda e=widget: self._aplicar_formatacao_campo_entrada(e, "horario"))
        self._atualizar_rotulo_jornada_liquida()
        self._agendar_salvamento_automatico()

    def _ao_sair_foco_campo_hora(self, entrada: ttk.Entry) -> None:
        """Ao sair do campo, normaliza o valor e atualiza totais."""
        self._normalizar_campo_entrada(entrada, "horario")
        self._atualizar_rotulo_jornada_liquida()
        self._agendar_salvamento_automatico()

    def _ao_tecla_solta_campo_duracao(self, evento: tk.Event) -> None:
        """Normaliza duração após quatro dígitos (ex.: 0130 → 1:30) e agenda salvamento."""
        widget = evento.widget
        if isinstance(widget, ttk.Entry) and widget in self._widgets_tempo_atividade.values():
            self.after_idle(lambda e=widget: self._aplicar_formatacao_campo_entrada(e, "duracao"))
        self._agendar_salvamento_automatico()

    def _ao_sair_foco_campo_duracao(self, entrada: ttk.Entry) -> None:
        """Ao sair do campo, aplica normalização de duração h:mm."""
        self._normalizar_campo_entrada(entrada, "duracao")
        self._agendar_salvamento_automatico()

    def _atualizar_rotulo_jornada_liquida(self) -> None:
        """Mantém as métricas do painel do calendário sincronizadas com os horários digitados."""
        self._atualizar_painel_metricas_horas()

    def _payload_formulario_dia_sem_contagem_mes(self) -> dict[str, Any]:
        """
        Lê textos e horários do formulário do dia atual, sem ``numero``/``folha``.

        Usado na contagem do mês para evitar recursão com o payload completo.
        """
        saida: dict[str, Any] = {}
        for chave, widget in self._widgets_campos_dia.items():
            saida[chave] = widget.get("1.0", tk.END).strip()
        for chave, widget in self._widgets_tempo_atividade.items():
            bruto = widget.get().strip()
            saida[chave] = normalizar_duracao_hhmm(bruto) if bruto else ""
        for chave, widget in self._widgets_horarios.items():
            bruto = widget.get().strip()
            saida[chave] = normalizar_texto_horario(bruto) if bruto else ""
        saida.pop(CHAVE_JSON_BATIDAS_PONTO, None)
        saida.pop("jornada_entrada", None)
        saida.pop("jornada_saida", None)
        return saida

    def _montar_dicionario_dia_desde_formulario(self) -> dict[str, Any]:
        """Payload completo do dia para gravar no JSON, incluindo número e folha no mês."""
        saida = self._payload_formulario_dia_sem_contagem_mes()
        saida[CHAVE_JSON_METRICAS_HORAS] = calcular_metricas_horas_para_dia(
            self._data_em_edicao, saida, self._config_regras_horas
        )
        posicao, _total, folha = self._calcular_numero_e_folha_mes()
        saida[CHAVE_JSON_NUMERO_RELATORIO_MES] = posicao
        saida[CHAVE_JSON_FOLHA_RELATORIO_MES] = folha
        aplicar_metadados_data_no_registro_diario(self._data_em_edicao.isoformat(), saida)
        return saida

    def _inicializar_apos_abrir(self) -> None:
        """Primeira carga: combo, documento inicial, data de hoje e marcas no calendário."""
        inicial = obter_documento_cliente_inicial()
        self._atualizar_lista_combo_clientes()
        if inicial is None:
            self._atualizar_rotulo_contagem_relatorios_mes()
            self._atualizar_marcadores_calendario()
            messagebox.showinfo(
                "Primeiro uso",
                "Crie um cliente com o botão «Novo cliente…». "
                "A chave do arquivo é contratante + natureza do serviço.",
            )
            return
        documento, caminho = inicial
        self._documento_atual = documento
        self._caminho_arquivo_atual = caminho
        self._marcar_combo_cliente_atual(documento)
        self._carregar_cabecalho_no_formulario()
        chave = documento.get("chave") or {}
        salvar_memoria_ultimo_cliente(
            str(chave.get(CHAVE_JSON_CONTRATANTE, "")),
            str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
        )
        self._data_em_edicao = date.today()
        if self._widget_calendario:
            self._widget_calendario.selection_set(self._data_em_edicao)
        self._atualizar_rotulo_data_selecionada()
        self._carregar_registro_dia_no_formulario(self._data_em_edicao)
        self._atualizar_marcadores_calendario()

    def _atualizar_lista_combo_clientes(self) -> None:
        """Reconstrói a lista do combobox a partir dos ficheiros em `dados_rdo`."""
        self._mapa_rotulo_para_caminho.clear()
        itens = listar_clientes_salvos()
        rotulos: list[str] = []
        for contratante, natureza, caminho in itens:
            rotulo = f"{contratante} — {natureza}" if contratante and natureza else (
                contratante or natureza or caminho.name
            )
            rotulos.append(rotulo)
            self._mapa_rotulo_para_caminho[rotulo] = caminho
        if self._combo_selecao_cliente:
            self._combo_selecao_cliente["values"] = rotulos

    def _marcar_combo_cliente_atual(self, documento: dict[str, Any]) -> None:
        """Seleciona no combo o item correspondente ao documento carregado."""
        chave = documento.get("chave") or {}
        c = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
        n = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        rotulo = f"{c} — {n}" if c and n else (c or n)
        if self._combo_selecao_cliente and rotulo in self._combo_selecao_cliente["values"]:
            self._combo_selecao_cliente.set(rotulo)

    def _ao_trocar_cliente_combo(self, _evento: tk.Event | None = None) -> None:
        """Troca de cliente: grava o dia atual, abre o novo JSON e recarrega o formulário."""
        if not self._combo_selecao_cliente:
            return
        rotulo = self._combo_selecao_cliente.get().strip()
        caminho = self._mapa_rotulo_para_caminho.get(rotulo)
        if not caminho or not caminho.is_file():
            return
        self._persistir_dia_atual_no_documento()
        self._salvar_documento_agora()
        self._documento_atual = carregar_documento_json(caminho)
        self._caminho_arquivo_atual = caminho
        chave = self._documento_atual.get("chave") or {}
        salvar_memoria_ultimo_cliente(
            str(chave.get(CHAVE_JSON_CONTRATANTE, "")),
            str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
        )
        self._carregar_cabecalho_no_formulario()
        self._carregar_registro_dia_no_formulario(self._data_em_edicao)
        if self._widget_calendario:
            self._widget_calendario.selection_set(self._data_em_edicao)
        self._atualizar_marcadores_calendario()

    def _abrir_dialogo_novo_cliente(self) -> None:
        """Diálogo modal para criar contratante + natureza e abrir o ficheiro novo."""
        topo = tk.Toplevel(self)
        topo.title("Novo cliente")
        topo.transient(self)
        topo.grab_set()
        ttk.Label(topo, text="Contratante (chave):").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        entrada_contratante = ttk.Entry(topo, width=48)
        entrada_contratante.grid(row=0, column=1, padx=8, pady=6)
        ttk.Label(topo, text="Natureza do serviço (chave):").grid(
            row=1, column=0, sticky=tk.W, padx=8, pady=6
        )
        entrada_natureza = ttk.Entry(topo, width=48)
        entrada_natureza.grid(row=1, column=1, padx=8, pady=6)

        def confirmar() -> None:
            c = entrada_contratante.get().strip()
            n = entrada_natureza.get().strip()
            if not c or not n:
                messagebox.showwarning("Validação", "Preencha contratante e natureza do serviço.", parent=topo)
                return
            self._persistir_dia_atual_no_documento()
            self._salvar_documento_agora()
            documento, caminho = carregar_ou_criar_cliente(c, n)
            self._documento_atual = documento
            self._caminho_arquivo_atual = caminho
            salvar_memoria_ultimo_cliente(c, n)
            self._atualizar_lista_combo_clientes()
            self._marcar_combo_cliente_atual(documento)
            self._carregar_cabecalho_no_formulario()
            self._carregar_registro_dia_no_formulario(self._data_em_edicao)
            if self._widget_calendario:
                self._widget_calendario.selection_set(self._data_em_edicao)
            self._atualizar_marcadores_calendario()
            topo.destroy()

        ttk.Button(topo, text="Criar e abrir", command=confirmar).grid(
            row=2, column=0, columnspan=2, pady=12
        )

    def _ao_mudar_mes_calendario(self, _evento: tk.Event | None = None) -> None:
        """Ao mudar mês/ano no calendário, repõe feriados (vermelho) e marcas de registo."""
        self._atualizar_marcadores_calendario()

    def _ao_selecionar_data_calendario(self, _evento: tk.Event | None = None) -> None:
        """Quando o usuário escolhe outro dia no calendário, persiste o anterior e carrega o novo."""
        if not self._widget_calendario:
            return
        nova = self._widget_calendario.selection_get()
        if nova == self._data_em_edicao:
            return
        self._alterar_data_em_edicao(nova)

    def _alterar_data_em_edicao(self, nova_data: date) -> None:
        """Atualiza a data em edição, sincroniza o calendário e o formulário."""
        self._persistir_dia_atual_no_documento()
        self._data_em_edicao = nova_data
        if self._widget_calendario:
            try:
                self._widget_calendario.selection_set(nova_data)
            except tk.TclError:
                pass
        self._atualizar_rotulo_data_selecionada()
        self._carregar_registro_dia_no_formulario(nova_data)
        self._atualizar_marcadores_calendario()
        self._agendar_salvamento_automatico()

    def _atualizar_marcadores_calendario(self) -> None:
        """Repinta feriados (vermelho), registos (verde) e dia em edição."""
        if self._widget_calendario:
            self._pintar_dias_com_registro_no_calendario(self._widget_calendario)

    def _atualizar_rotulo_data_selecionada(self) -> None:
        """Mostra data e dia da semana no rótulo acima do formulário."""
        if self._rotulo_texto_data:
            d = self._data_em_edicao
            self._rotulo_texto_data.configure(
                text=f"{d.strftime('%d/%m/%Y')} ({nome_dia_semana_portugues(d)})"
            )

    def _registros_diarios_efetivos_para_contagem(self) -> dict[str, Any]:
        """
        Cópia de `registros_diarios` em que o dia em edição reflete o formulário atual
        (para a contagem do mês acompanhar a digitação antes do autosave).
        """
        if not self._documento_atual:
            return {}
        copia: dict[str, Any] = dict(self._documento_atual.get("registros_diarios") or {})
        iso = self._data_em_edicao.isoformat()
        payload = self._payload_formulario_dia_sem_contagem_mes()
        if registro_de_dia_possui_conteudo(payload):
            copia[iso] = payload
        else:
            copia.pop(iso, None)
        return copia

    def _datas_com_relatorio_preenchido_no_mes(self, referencia: date) -> list[date]:
        """
        Lista ordenada de datas do mesmo ano/mês de `referencia` que têm relatório com conteúdo.
        """
        prefixo = f"{referencia.year:04d}-{referencia.month:02d}-"
        registros = self._registros_diarios_efetivos_para_contagem()
        datas: list[date] = []
        for iso, registro in registros.items():
            if not iso.startswith(prefixo):
                continue
            if not isinstance(registro, dict):
                continue
            if not registro_de_dia_possui_conteudo(registro):
                continue
            try:
                datas.append(date.fromisoformat(iso))
            except ValueError:
                continue
        datas.sort()
        return datas

    def _calcular_numero_e_folha_mes(self) -> tuple[int | None, int, str]:
        """
        Calcula a posição (1-based) do dia atual entre os relatórios preenchidos do mês,
        o total nesse mês e a cadeia «X de Y» (ou «— de Y» / «0 de 0»).

        Alinhado ao que é gravado em ``numero`` e ``folha`` no JSON do dia.
        """
        if not self._documento_atual:
            return None, 0, "0 de 0"
        ref = self._data_em_edicao
        datas = self._datas_com_relatorio_preenchido_no_mes(ref)
        total = len(datas)
        if total == 0:
            return None, 0, "0 de 0"
        try:
            posicao = datas.index(ref) + 1
            return posicao, total, f"{posicao} de {total}"
        except ValueError:
            return None, total, f"— de {total}"

    def _atualizar_rotulo_contagem_relatorios_mes(self) -> None:
        """
        Atualiza o texto «No mês: X de N»: posição cronológica do dia atual entre os N dias
        preenchidos no mês (ex.: 5.º dia com relatório de 20 no total).
        """
        if not self._rotulo_contagem_mes:
            return
        if not self._documento_atual:
            self._rotulo_contagem_mes.configure(text="No mês: —")
            return
        _pos, _tot, folha = self._calcular_numero_e_folha_mes()
        self._rotulo_contagem_mes.configure(text=f"No mês: {folha}")

    def _pintar_dias_com_registro_no_calendario(self, cal: Calendar) -> None:
        """
        Marca feriados do JSON (número em vermelho), dias com registo (verde),
        e o dia aberto para edição (laranja; a seleção azul fica por cima).

        Chama ``_display_calendar`` no fim para o estilo de seleção não ficar tapado pelos eventos.
        """
        tags_limpar = (
            self.TAG_EVENTO_DIA_PREENCHIDO,
            self.TAG_DIA_RELATORIO_EM_EDICAO,
            *_TAGS_DESTAQUE_VERMELHO,
        )
        for tag in tags_limpar:
            try:
                cal.calevent_remove(tag=tag)
            except tk.TclError:
                pass

        try:
            _configurar_tags_destaque_vermelho(cal)
        except tk.TclError:
            pass

        ano_vis = cal._date.year
        mes_vis = cal._date.month
        celulas = _grelha_datas_exibidas_calendario(cal)
        anos = {d.year for d in celulas}
        feriados_iso: set[str] = set()
        for a in anos:
            feriados_iso |= conjunto_feriados_iso_para_ano(self._config_regras_horas, a)

        datas_com_registro: set[str] = set()
        if self._documento_atual:
            registros = self._documento_atual.get("registros_diarios") or {}
            for iso, registro in registros.items():
                if not isinstance(registro, dict):
                    continue
                if registro_de_dia_possui_conteudo(registro):
                    datas_com_registro.add(str(iso).strip())

        for d in celulas:
            iso = d.isoformat()
            preenchido = iso in datas_com_registro
            tag_vm = _tag_destaque_vermelho_para_data(
                d, ano_vis, mes_vis, preenchido, feriados_iso
            )
            if tag_vm:
                cal.calevent_create(
                    d,
                    _texto_tooltip_destaque_calendario(d),
                    tag_vm,
                )
            elif preenchido and self._documento_atual:
                cal.calevent_create(d, "com dados", self.TAG_EVENTO_DIA_PREENCHIDO)

        if self._documento_atual:
            cal.calevent_create(
                self._data_em_edicao,
                "Relatório aberto para edição",
                self.TAG_DIA_RELATORIO_EM_EDICAO,
            )
        try:
            cal._display_calendar()
        except (tk.TclError, AttributeError):
            pass

    def _carregar_cabecalho_no_formulario(self) -> None:
        """Copia `cabecalho_fixo` do documento para os campos da primeira aba."""
        if not self._documento_atual:
            return
        cabecalho = self._documento_atual.get("cabecalho_fixo") or {}
        for campo, widget in self._widgets_cabecalho.items():
            widget.delete(0, tk.END)
            widget.insert(0, str(cabecalho.get(campo, "") or ""))

    def _copiar_cabecalho_formulario_para_documento(self) -> None:
        """Grava no documento em memória os valores atuais dos campos do cabeçalho."""
        if not self._documento_atual:
            return
        cabecalho = dict(self._documento_atual.get("cabecalho_fixo") or {})
        for campo, widget in self._widgets_cabecalho.items():
            cabecalho[campo] = widget.get().strip()
        self._documento_atual["cabecalho_fixo"] = cabecalho

    def _preencher_formulario_com_registro_dia(self, registro: dict[str, Any]) -> None:
        """Preenche textos do dia a partir de um dicionário de registro."""
        for campo, widget in self._widgets_campos_dia.items():
            valor = str(registro.get(campo, "") or "")
            widget.delete("1.0", tk.END)
            widget.insert("1.0", valor)
        for campo, widget in self._widgets_tempo_atividade.items():
            widget.delete(0, tk.END)
            bruto = str(registro.get(campo, "") or "").strip()
            widget.insert(0, normalizar_duracao_hhmm(bruto) if bruto else "")

    def _carregar_registro_dia_no_formulario(self, dia: date) -> None:
        """Carrega o registro ISO do dia nos widgets (texto + horários normalizados)."""
        if not self._documento_atual:
            return
        iso = dia.isoformat()
        registros = self._documento_atual.setdefault("registros_diarios", {})
        registro_bruto = registros.get(iso) if isinstance(registros.get(iso), dict) else {}
        registro = registro_bruto if isinstance(registro_bruto, dict) else {}
        self._preencher_formulario_com_registro_dia(registro)
        horarios = extrair_horarios_do_registro_dia(registro)
        for campo, widget in self._widgets_horarios.items():
            widget.delete(0, tk.END)
            bruto = str(horarios.get(campo, "") or "").strip()
            widget.insert(0, normalizar_texto_horario(bruto) if bruto else "")
        self._atualizar_rotulo_jornada_liquida()
        self._atualizar_rotulo_contagem_relatorios_mes()
        for w in self._widgets_campos_dia.values():
            self.after(600, lambda x=w: self._executar_verificacao_ortografia(x))

    def _persistir_dia_atual_no_documento(self) -> None:
        """Escreve ou remove o registro do dia atual em `registros_diarios` conforme o conteúdo."""
        if not self._documento_atual:
            return
        iso = self._data_em_edicao.isoformat()
        registros = self._documento_atual.setdefault("registros_diarios", {})
        dados = self._montar_dicionario_dia_desde_formulario()
        if registro_de_dia_possui_conteudo(dados):
            registros[iso] = dados
        elif iso in registros:
            del registros[iso]

    def _agendar_salvamento_automatico(self, _evento: tk.Event | None = None) -> None:
        """Agenda salvamento após um curto atraso (debounce) para não gravar a cada tecla."""
        self._atualizar_rotulo_contagem_relatorios_mes()
        if self._id_agendamento_salvar:
            self.after_cancel(self._id_agendamento_salvar)
        self._id_agendamento_salvar = self.after(1200, self._executar_salvamento_automatico)

    def _executar_salvamento_automatico(self) -> None:
        """Callback do timer: salva sem messagebox de erro visível (silencioso)."""
        self._id_agendamento_salvar = None
        self._salvar_documento_agora(silencioso=True)

    def _salvar_documento_agora(self, silencioso: bool = False) -> None:
        """Persiste documento completo no disco e atualiza memória do último cliente."""
        if not self._documento_atual or not self._caminho_arquivo_atual:
            return
        self._persistir_dia_atual_no_documento()
        self._copiar_cabecalho_formulario_para_documento()
        chave = self._documento_atual.get("chave") or {}
        salvar_memoria_ultimo_cliente(
            str(chave.get(CHAVE_JSON_CONTRATANTE, "")),
            str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")),
        )
        try:
            salvar_documento_json(self._caminho_arquivo_atual, self._documento_atual)
        except OSError as erro:
            if not silencioso:
                messagebox.showerror("Salvar", str(erro))
            return
        self._atualizar_marcadores_calendario()
        self._atualizar_rotulo_contagem_relatorios_mes()
        if not silencioso:
            self.title(f"RDO — salvo {datetime.now().strftime('%H:%M:%S')}")

    def _gerar_relatorios_excel(self) -> None:
        """Gera ou atualiza os ficheiros RDO e FT por mês na pasta `saida_relatorios`."""
        if not self._documento_atual or not self._caminho_arquivo_atual:
            messagebox.showwarning(
                "Gerar Excel",
                "Não há documento carregado. Selecione ou crie um cliente antes de gerar os relatórios.",
            )
            return
        self._persistir_dia_atual_no_documento()
        self._copiar_cabecalho_formulario_para_documento()
        try:
            self._salvar_documento_agora(silencioso=True)
            caminhos = gerar_relatorios_excel(self._documento_atual, self._caminho_arquivo_atual)
        except ValueError as e:
            messagebox.showwarning("Gerar Excel", str(e))
            return
        except OSError as e:
            messagebox.showerror("Gerar Excel", f"Erro ao gravar ficheiros:\n{e}")
            return
        except Exception as e:
            messagebox.showerror("Gerar Excel", f"Não foi possível gerar os relatórios:\n{e}")
            return
        linhas = "\n".join(str(p) for p in caminhos)
        messagebox.showinfo(
            "Gerar Excel",
            f"Foram criados ou atualizados {len(caminhos)} ficheiro(s):\n\n{linhas}",
        )

    def _ao_fechar_janela(self) -> None:
        """Salva em silêncio e encerra a aplicação."""
        try:
            self._salvar_documento_agora(silencioso=True)
        except Exception:
            pass
        self.destroy()


def iniciar_aplicacao() -> None:
    """Garante a pasta de dados e abre a janela principal."""
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    garantir_arquivo_config_regras_existe()
    app = AplicacaoRdo()
    app.mainloop()
