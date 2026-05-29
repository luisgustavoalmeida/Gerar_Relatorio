"""Widget de calendário e lógica de marcação de dias (feriados, registos, métricas)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar

from rdo_diario.calculo_metricas_horas import (
    agregar_metricas_mes,
    calcular_metricas_horas_para_dia,
    formatar_resumo_metricas_texto,
)
from rdo_diario.config_horas import conjunto_feriados_iso_para_ano
from rdo_diario.horario_util import formatar_minutos_como_texto
from rdo_diario.schema import (
    descricao_estado_essencial_calendario,
    estado_informacoes_essenciais_dia,
    nome_dia_semana_portugues,
    registro_de_dia_possui_conteudo,
)

if TYPE_CHECKING:
    from rdo_diario.gui.app import AplicacaoRdo


# Patch para corrigir bug em tkcalendar 1.5.0: KeyError em tooltip quando widgets são recriados
def _patch_tkcalendar_tooltip() -> None:
    """
    Corrige KeyError em tkcalendar.tooltip.TooltipWrapper.display_tooltip quando tentando
    acessar widget que não existe mais no dicionário interno durante renderização de calendário.
    """
    try:
        from tkcalendar import tooltip as tkcal_tooltip

        if hasattr(tkcal_tooltip, "TooltipWrapper"):
            original_display = tkcal_tooltip.TooltipWrapper.display_tooltip

            def patched_display(self: Any) -> None:
                try:
                    original_display(self)
                except KeyError:
                    pass

            tkcal_tooltip.TooltipWrapper.display_tooltip = patched_display
    except Exception:
        pass


_patch_tkcalendar_tooltip()


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


def criar_widget_calendario(pai: tk.Misc, *, compacto: bool = False) -> CalendarRdo:
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


def _texto_tooltip_destaque_calendario(d: date) -> str:
    if d.weekday() >= 5:
        return "Feriado (fim de semana)"
    return "Feriado"


class MixinCalendario:
    """Marcação de dias, seleção de data e painel de métricas sob o calendário."""

    TAG_EVENTO_DIA_PREENCHIDO = "dia_preenchido"
    TAG_EVENTO_DIA_PARCIAL = "dia_parcial"
    TAG_DIA_RELATORIO_EM_EDICAO = "dia_relatorio_em_edicao"

    _widget_calendario: Calendar | None
    _rotulo_texto_data: ttk.Label | None
    _rotulo_contagem_mes: ttk.Label | None
    _rotulo_metricas_dia: ttk.Label | None
    _rotulo_metricas_mes: ttk.Label | None
    _data_em_edicao: date
    _documento_atual: dict[str, Any] | None
    _config_regras_horas: dict[str, Any]

    def _montar_coluna_calendario(self, coluna_calendario: ttk.Frame) -> None:
        """Monta calendário compacto, legenda e painel de métricas."""
        moldura_cal = ttk.LabelFrame(coluna_calendario, text="Calendário", padding=4)
        moldura_cal.pack(side=tk.TOP, anchor=tk.N)
        ttk.Label(
            moldura_cal,
            text=(
                "Selecione uma data para visualizar / editar.\n"
                "Verde = registro de serviço e horários válidos (entrada e saída).\n"
                "Laranja = incompleto ou horários inválidos.\n"
                "Azul = data em edição.\n"
                "Vermelho = feriado nacional.\n"
            ),
            font=("Segoe UI", 8),
            wraplength=260,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, fill=tk.X)
        self._widget_calendario = criar_widget_calendario(moldura_cal, compacto=True)
        self._widget_calendario.pack(side=tk.TOP, pady=(4, 0))
        try:
            self._widget_calendario.tag_config(
                self.TAG_EVENTO_DIA_PREENCHIDO,
                background=_COR_CALENDARIO_COMPLETO,
                foreground="#000000",
            )
            self._widget_calendario.tag_config(
                self.TAG_EVENTO_DIA_PARCIAL,
                background=_COR_CALENDARIO_PARCIAL,
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
            text=("Métricas do dia:"),
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
                f"Métricas mensais:\n\n"
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
        Marca feriados (vermelho), dias completos (verde), parciais (laranja)
        e mantém a seleção azul do dia em edição por cima.

        Chama ``_display_calendar`` no fim para o estilo de seleção não ficar tapado pelos eventos.
        """
        tags_limpar = (
            self.TAG_EVENTO_DIA_PREENCHIDO,
            self.TAG_EVENTO_DIA_PARCIAL,
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
            if tag_vm:
                cal.calevent_create(
                    d,
                    _texto_tooltip_destaque_calendario(d),
                    tag_vm,
                )
            elif estado == "completo" and self._documento_atual:
                cal.calevent_create(
                    d,
                    descricao_estado_essencial_calendario(registro_dia),
                    self.TAG_EVENTO_DIA_PREENCHIDO,
                )
            elif estado == "parcial" and self._documento_atual:
                cal.calevent_create(
                    d,
                    descricao_estado_essencial_calendario(registro_dia),
                    self.TAG_EVENTO_DIA_PARCIAL,
                )
        try:
            cal._display_calendar()
        except (tk.TclError, AttributeError):
            pass
