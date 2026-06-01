"""Widget de calendário e lógica de marcação de dias (feriados, registos, métricas)."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from typing import TYPE_CHECKING, Any

import customtkinter as ctk
from tkcalendar import Calendar

from rdo_diario.calculo_metricas_horas import (
    agregar_metricas_mes,
    calcular_metricas_horas_para_dia,
    formatar_resumo_metricas_texto,
)
from rdo_diario.config_horas import conjunto_feriados_iso_para_ano
from rdo_diario.horario_util import formatar_minutos_como_texto
from rdo_diario.gui.tema import (
    COR_TEXTO,
    COR_TEXTO_SECUNDARIO,
    FONT_AUXILIAR,
    FONT_DATA_SELECIONADA,
    FONT_GRUPO,
    FONT_INTERFACE,
    FONT_METRICAS,
    criar_painel_ctk_com_titulo,
    obter_cores_tema,
    opcoes_calendario_tk_embutido,
)
from rdo_diario.schema import (
    estado_informacoes_essenciais_dia,
    nome_dia_semana_portugues,
    registro_de_dia_possui_conteudo,
)

if TYPE_CHECKING:
    from rdo_diario.gui.app import AplicacaoRdo


TAG_CAL_VM_DU = "cal_vm_du"
TAG_CAL_VM_DU_P = "cal_vm_du_p"
TAG_CAL_VM_FDS = "cal_vm_fds"
TAG_CAL_VM_FDS_P = "cal_vm_fds_p"
TAG_CAL_VM_OM_DU = "cal_vm_om_du"
TAG_CAL_VM_OM_DU_P = "cal_vm_om_du_p"
TAG_CAL_VM_OM_FDS = "cal_vm_om_fds"
TAG_CAL_VM_OM_FDS_P = "cal_vm_om_fds_p"
TAG_CAL_VM_DU_PAR = "cal_vm_du_par"
TAG_CAL_VM_FDS_PAR = "cal_vm_fds_par"
TAG_CAL_VM_OM_DU_PAR = "cal_vm_om_du_par"
TAG_CAL_VM_OM_FDS_PAR = "cal_vm_om_fds_par"

_COR_CALENDARIO_COMPLETO = "#7ccd7c"
_COR_CALENDARIO_PARCIAL = "#ea580c"
TAG_DIA_HOJE = "dia_hoje"

_TAGS_DESTAQUE_VERMELHO: tuple[str, ...] = (
    TAG_CAL_VM_DU,
    TAG_CAL_VM_DU_P,
    TAG_CAL_VM_DU_PAR,
    TAG_CAL_VM_FDS,
    TAG_CAL_VM_FDS_P,
    TAG_CAL_VM_FDS_PAR,
    TAG_CAL_VM_OM_DU,
    TAG_CAL_VM_OM_DU_P,
    TAG_CAL_VM_OM_DU_PAR,
    TAG_CAL_VM_OM_FDS,
    TAG_CAL_VM_OM_FDS_P,
    TAG_CAL_VM_OM_FDS_PAR,
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


def _desativar_tooltips_calendario(cal: Calendar) -> None:
    """Desliga balões do tkcalendar (só usamos ``calevent`` para cores)."""
    tw = cal.tooltip_wrapper

    def _ignorar(_widget: tk.Widget, _text: str = "") -> None:
        pass

    def _limpar_vinculos() -> None:
        tw.widgets.clear()
        tw.bind_enter_ids.clear()
        tw.bind_leave_ids.clear()
        try:
            tw.tooltip.withdraw()
        except tk.TclError:
            pass

    tw.add_tooltip = _ignorar  # type: ignore[method-assign]
    tw.set_tooltip_text = _ignorar  # type: ignore[method-assign]
    tw.remove_all = _limpar_vinculos  # type: ignore[method-assign]
    tw.remove_tooltip = _ignorar  # type: ignore[method-assign]
    tw.display_tooltip = lambda: None  # type: ignore[method-assign]


def aplicar_cores_tema_calendario(cal: Calendar, *, compacto: bool = True) -> None:
    """Reaplica a paleta padrão num calendário já criado."""
    opcoes = opcoes_calendario_tk_embutido(compacto=compacto)
    for chave, valor in opcoes.items():
        if chave == "font":
            continue
        try:
            cal.configure(**{chave: valor})
        except tk.TclError:
            pass


def criar_widget_calendario(pai: tk.Misc, *, compacto: bool = False) -> CalendarRdo:
    """
    Instancia o calendário (subclasse que corrige clique em dias de outros meses).

    Tenta locale pt_BR; se falhar, usa o padrão do sistema.
    """
    argumentos: dict = {
        "selectmode": "day",
        "date_pattern": "yyyy-mm-dd",
        "showweeknumbers": True,
        **opcoes_calendario_tk_embutido(compacto=compacto),
    }
    try:
        cal = CalendarRdo(pai, locale="pt_BR", **argumentos)
    except Exception:
        cal = CalendarRdo(pai, **argumentos)
    _desativar_tooltips_calendario(cal)
    return cal


def _fundo_destaque_dia_hoje(cal: Calendar, tag_status: str | None) -> str:
    """Fundo do dia atual: cor de hoje ou a do estado (verde/laranja/feriado)."""
    if tag_status:
        try:
            return str(cal.tag_cget(tag_status, "background"))
        except (ValueError, tk.TclError):
            pass
    return obter_cores_tema()["calendario_hoje_fundo"]


def _texto_destaque_dia_hoje(
    cal: Calendar,
    d: date,
    ano_visivel: int,
    mes_visivel: int,
    tag_status: str | None,
) -> str:
    """Cor do número igual à da marca de estado ou às demais células do mesmo tipo."""
    if tag_status:
        try:
            return str(cal.tag_cget(tag_status, "foreground"))
        except (ValueError, tk.TclError):
            pass
    fds = d.weekday() >= 5
    no_mes_visivel = d.month == mes_visivel and d.year == ano_visivel
    if not no_mes_visivel:
        if fds:
            return str(cal.cget("othermonthweforeground"))
        return str(cal.cget("othermonthforeground"))
    if fds:
        return str(cal.cget("weekendforeground"))
    return str(cal.cget("normalforeground"))


def _configurar_tag_dia_hoje(cal: Calendar) -> None:
    """Tag do dia atual: fundo destacado; texto igual ao restante do mês."""
    cores = obter_cores_tema()
    cal.tag_config(
        TAG_DIA_HOJE,
        background=cores["calendario_hoje_fundo"],
        foreground=str(cal.cget("normalforeground")),
    )


def _configurar_tags_destaque_vermelho(cal: Calendar) -> None:
    """Cores alinhadas ao tema do calendário (fundo) + texto de erro."""
    fg = obter_cores_tema()["erro"]
    cal.tag_config(TAG_CAL_VM_DU, foreground=fg, background=cal.cget("normalbackground"))
    cal.tag_config(TAG_CAL_VM_DU_P, foreground=fg, background=_COR_CALENDARIO_COMPLETO)
    cal.tag_config(TAG_CAL_VM_DU_PAR, foreground=fg, background=_COR_CALENDARIO_PARCIAL)
    cal.tag_config(TAG_CAL_VM_FDS, foreground=fg, background=cal.cget("weekendbackground"))
    cal.tag_config(TAG_CAL_VM_FDS_P, foreground=fg, background=_COR_CALENDARIO_COMPLETO)
    cal.tag_config(TAG_CAL_VM_FDS_PAR, foreground=fg, background=_COR_CALENDARIO_PARCIAL)
    cal.tag_config(TAG_CAL_VM_OM_DU, foreground=fg, background=cal.cget("othermonthbackground"))
    cal.tag_config(TAG_CAL_VM_OM_DU_P, foreground=fg, background=_COR_CALENDARIO_COMPLETO)
    cal.tag_config(TAG_CAL_VM_OM_DU_PAR, foreground=fg, background=_COR_CALENDARIO_PARCIAL)
    cal.tag_config(TAG_CAL_VM_OM_FDS, foreground=fg, background=cal.cget("othermonthwebackground"))
    cal.tag_config(TAG_CAL_VM_OM_FDS_P, foreground=fg, background=_COR_CALENDARIO_COMPLETO)
    cal.tag_config(TAG_CAL_VM_OM_FDS_PAR, foreground=fg, background=_COR_CALENDARIO_PARCIAL)


def _tag_destaque_vermelho_para_data(
    d: date,
    ano_visivel: int,
    mes_visivel: int,
    estado: str,
    feriados_iso: set[str],
) -> str | None:
    """Tag só se a data for feriado no JSON; ``None`` nos restantes dias."""
    if d.isoformat() not in feriados_iso:
        return None
    fds = d.weekday() >= 5
    no_mes_visivel = d.month == mes_visivel and d.year == ano_visivel
    if not no_mes_visivel:
        if fds:
            if estado == "completo":
                return TAG_CAL_VM_OM_FDS_P
            if estado == "parcial":
                return TAG_CAL_VM_OM_FDS_PAR
            return TAG_CAL_VM_OM_FDS
        if estado == "completo":
            return TAG_CAL_VM_OM_DU_P
        if estado == "parcial":
            return TAG_CAL_VM_OM_DU_PAR
        return TAG_CAL_VM_OM_DU
    if fds:
        if estado == "completo":
            return TAG_CAL_VM_FDS_P
        if estado == "parcial":
            return TAG_CAL_VM_FDS_PAR
        return TAG_CAL_VM_FDS
    if estado == "completo":
        return TAG_CAL_VM_DU_P
    if estado == "parcial":
        return TAG_CAL_VM_DU_PAR
    return TAG_CAL_VM_DU


class MixinCalendario:
    """Marcação de dias, seleção de data e painel de métricas sob o calendário."""

    TAG_EVENTO_DIA_PREENCHIDO = "dia_preenchido"
    TAG_EVENTO_DIA_PARCIAL = "dia_parcial"
    TAG_DIA_RELATORIO_EM_EDICAO = "dia_relatorio_em_edicao"

    _widget_calendario: Calendar | None
    _rotulo_data_atual: ctk.CTkLabel | None
    _rotulo_texto_data: ctk.CTkLabel | None
    _rotulo_contagem_mes: ctk.CTkLabel | None
    _rotulo_metricas_dia: ctk.CTkLabel | None
    _rotulo_metricas_mes: ctk.CTkLabel | None
    _data_em_edicao: date
    _documento_atual: dict[str, Any] | None
    _config_regras_horas: dict[str, Any]

    def _montar_coluna_calendario(self, coluna_calendario: ctk.CTkBaseClass) -> None:
        """Monta calendário compacto, legenda e painel de métricas."""
        grupo_cal, moldura_cal = criar_painel_ctk_com_titulo(coluna_calendario, "Calendário")
        grupo_cal.pack(side=tk.TOP, anchor=tk.N)
        ctk.CTkLabel(
            moldura_cal,
            text=(
                "Selecione uma data para visualizar / editar.\n"
                "Azul = data em edição.\n"
                "Fundo destacado = hoje (sem registo); com registo mantém verde/laranja/vermelho.\n"
                "Verde = registro de serviço e horários válidos.\n"
                "Laranja = incompleto ou horários inválidos.\n"
                "Vermelho = feriado nacional.\n"
            ),
            font=FONT_AUXILIAR,
            text_color=COR_TEXTO_SECUNDARIO,
            wraplength=260,
            justify="left",
            anchor="w",
        ).pack(anchor="w", fill="x")
        hoje = date.today()
        self._rotulo_data_atual = ctk.CTkLabel(
            moldura_cal,
            text=f"Hoje: {hoje.strftime('%d/%m/%Y')} ({nome_dia_semana_portugues(hoje)})",
            font=FONT_DATA_SELECIONADA,
            text_color=COR_TEXTO,
            anchor="w",
        )
        self._rotulo_data_atual.pack(anchor="w", fill="x", pady=(8, 4))
        self._widget_calendario = criar_widget_calendario(moldura_cal, compacto=True)
        self._widget_calendario.pack(side=tk.TOP, pady=(4, 0))
        try:
            cores = obter_cores_tema()
            self._widget_calendario.tag_config(
                self.TAG_EVENTO_DIA_PREENCHIDO,
                background=_COR_CALENDARIO_COMPLETO,
                foreground=cores["texto"],
            )
            self._widget_calendario.tag_config(
                self.TAG_EVENTO_DIA_PARCIAL,
                background=_COR_CALENDARIO_PARCIAL,
                foreground="#FFFFFF",
            )
            _configurar_tags_destaque_vermelho(self._widget_calendario)
        except tk.TclError:
            pass
        self._widget_calendario.bind("<<CalendarSelected>>", self._ao_selecionar_data_calendario)
        self._widget_calendario.bind("<<CalendarMonthChanged>>", self._ao_mudar_mes_calendario)
        self._montar_painel_metricas_calendario(moldura_cal)

    def _montar_painel_metricas_calendario(self, moldura_cal: ctk.CTkBaseClass) -> None:
        """Abaixo do calendário: métricas do dia selecionado e totais do mês."""
        grupo, painel = criar_painel_ctk_com_titulo(
            moldura_cal,
            "Métricas de horas diárias e mensais",
        )
        grupo.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(
            painel,
            text="Métricas do dia:",
            font=FONT_GRUPO,
            wraplength=260,
            justify="left",
            anchor="w",
        ).pack(anchor="w", fill="x")
        self._rotulo_metricas_dia = ctk.CTkLabel(
            painel,
            text="",
            font=FONT_METRICAS,
            wraplength=260,
            justify="left",
            anchor="w",
        )
        self._rotulo_metricas_dia.pack(anchor="w", fill="x", pady=(4, 0))
        ctk.CTkLabel(
            painel,
            text="Métricas mensais:",
            font=FONT_GRUPO,
            wraplength=260,
            justify="left",
            anchor="w",
        ).pack(anchor="w", fill="x", pady=(10, 0))
        self._rotulo_metricas_mes = ctk.CTkLabel(
            painel,
            text="",
            font=FONT_METRICAS,
            wraplength=260,
            justify="left",
            anchor="w",
        )
        self._rotulo_metricas_mes.pack(anchor="w", fill="x", pady=(4, 0))

    def _atualizar_painel_metricas_horas(self: AplicacaoRdo) -> None:
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
                f"Data: {self._data_em_edicao.month:02d}/{self._data_em_edicao.year}\n"
                f"Dias válidos: {n}\n"
                f"{formatar_resumo_metricas_texto(agg)}"
            )
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

    def _alterar_data_em_edicao(self: AplicacaoRdo, nova_data: date) -> None:
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

    def _registros_diarios_efetivos_para_contagem(self: AplicacaoRdo) -> dict[str, Any]:
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
        Marca feriados (vermelho), dias completos (verde), parciais (laranja),
        destaca o dia atual e mantém a seleção azul do dia em edição por cima.

        Chama ``_display_calendar`` no fim para o estilo de seleção não ficar tapado pelos eventos.
        """
        hoje = date.today()
        tags_limpar = (
            self.TAG_EVENTO_DIA_PREENCHIDO,
            self.TAG_EVENTO_DIA_PARCIAL,
            self.TAG_DIA_RELATORIO_EM_EDICAO,
            TAG_DIA_HOJE,
            *_TAGS_DESTAQUE_VERMELHO,
        )
        for tag in tags_limpar:
            try:
                cal.calevent_remove(tag=tag)
            except tk.TclError:
                pass

        try:
            _configurar_tags_destaque_vermelho(cal)
            _configurar_tag_dia_hoje(cal)
        except tk.TclError:
            pass

        ano_vis = cal._date.year
        mes_vis = cal._date.month
        celulas = _grelha_datas_exibidas_calendario(cal)
        anos = {d.year for d in celulas}
        feriados_iso: set[str] = set()
        for a in anos:
            feriados_iso |= conjunto_feriados_iso_para_ano(self._config_regras_horas, a)

        estados_por_data: dict[str, str] = {}
        registros_efetivos: dict[str, Any] = {}
        if self._documento_atual:
            registros_efetivos = self._registros_diarios_efetivos_para_contagem()
            for iso, registro in registros_efetivos.items():
                if not isinstance(registro, dict):
                    continue
                estado = estado_informacoes_essenciais_dia(registro)
                if estado != "vazio":
                    estados_por_data[str(iso).strip()] = estado

        for d in celulas:
            iso = d.isoformat()
            estado = estados_por_data.get(iso, "vazio")
            registro_dia = registros_efetivos.get(iso)
            if not isinstance(registro_dia, dict):
                registro_dia = {}
            tag_vm = _tag_destaque_vermelho_para_data(
                d, ano_vis, mes_vis, estado, feriados_iso
            )
            tag_status: str | None = None
            if tag_vm:
                tag_status = tag_vm
            elif estado == "completo" and self._documento_atual:
                tag_status = self.TAG_EVENTO_DIA_PREENCHIDO
            elif estado == "parcial" and self._documento_atual:
                tag_status = self.TAG_EVENTO_DIA_PARCIAL

            if d == hoje:
                try:
                    cal.tag_config(
                        TAG_DIA_HOJE,
                        background=_fundo_destaque_dia_hoje(cal, tag_status),
                        foreground=_texto_destaque_dia_hoje(
                            cal, d, ano_vis, mes_vis, tag_status
                        ),
                    )
                    cal.calevent_create(d, "", TAG_DIA_HOJE)
                except tk.TclError:
                    pass
            elif tag_status:
                cal.calevent_create(d, "", tag_status)
        try:
            cal._display_calendar()
        except (tk.TclError, AttributeError):
            pass
