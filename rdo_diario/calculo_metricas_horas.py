"""
Cálculo de métricas de jornada a partir dos horários de ponto e das regras em `config_regras_horas.json`.

Classifica minutos em: normais, extra 50%, extra 100%, adicional noturno (com opção de hora reduzida CLT).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from rdo_diario.config_horas import (
    CHAVES_DIAS_SEMANA,
    conjunto_feriados_iso_para_ano,
    garantir_config_reglas_completa,
)
from rdo_diario.horario_util import (
    calcular_minutos_jornada_liquida,
    interpretar_hora_minuto,
    minutos_para_hhmm,
)
from rdo_diario.schema import extrair_horarios_do_registro_dia


def _minutos_desde_meia_noite(texto_hhmm: str) -> int | None:
    p = interpretar_hora_minuto(texto_hhmm)
    if p is None:
        return None
    return p[0] * 60 + p[1]


def _sobreposicao_intervalos(a0: int, a1: int, b0: int, b1: int) -> int:
    """Minutos de sobreposição de [a0,a1) com [b0,b1), intervalos no mesmo dia 0..1440."""
    if a1 <= a0 or b1 <= b0:
        return 0
    ini = max(a0, b0)
    fim = min(a1, b1)
    return max(0, fim - ini)


def _minutos_noturnos_no_intervalo(
    inicio_min: int,
    fim_min: int,
    cfg_noturno: dict[str, Any],
) -> tuple[int, float]:
    """
    Devolve (minutos_físicos_no_período_noturno, minutos_equivalente_hora_reduzida).

    Período noturno legal típico: 22h–5h (atravessa meia-noite). Para batidas só no mesmo dia,
    considera dois trechos no mesmo dia civil: [0, 5h) e [22h, 24h).
    """
    if not cfg_noturno.get("ativo", True):
        return 0, 0.0
    ini_s = str(cfg_noturno.get("inicio") or "22:00")
    fim_s = str(cfg_noturno.get("fim") or "05:00")
    n0 = _minutos_desde_meia_noite(ini_s)
    n1 = _minutos_desde_meia_noite(fim_s)
    if n0 is None or n1 is None:
        return 0, 0.0

    trechos_noturnos: list[tuple[int, int]] = []
    if n0 < n1:
        trechos_noturnos.append((n0, n1))
    else:
        trechos_noturnos.append((0, n1))
        trechos_noturnos.append((n0, 24 * 60))

    min_fis = 0
    for t0, t1 in trechos_noturnos:
        min_fis += _sobreposicao_intervalos(inicio_min, fim_min, t0, t1)

    if not cfg_noturno.get("incluir_hora_reduzida_clt", True):
        return min_fis, float(min_fis)

    mh = int(cfg_noturno.get("minutos_hora_noturna", 52))
    sh = int(cfg_noturno.get("segundos_hora_noturna", 30))
    duracao_hora_noturna_min = mh + sh / 60.0
    if duracao_hora_noturna_min <= 0:
        return min_fis, float(min_fis)
    # 52m30s de relógio = 1h de trabalho noturno → minutos pagos = físicos × (60 / duração_hora)
    equiv = min_fis * (60.0 / duracao_hora_noturna_min)
    return min_fis, float(equiv)


def _segmentos_trabalho_dia(
    entrada: str,
    saida_almoco: str,
    entrada_almoco: str,
    saida: str,
) -> list[tuple[int, int]]:
    """
    Lista de intervalos [início, fim) em minutos desde 00:00 do mesmo dia.
    Só considera o mesmo dia civil (sem turno que atravesse meia-noite).
    """
    pe = interpretar_hora_minuto(entrada)
    pf = interpretar_hora_minuto(saida)
    if pe is None or pf is None:
        return []
    m_pe = pe[0] * 60 + pe[1]
    m_pf = pf[0] * 60 + pf[1]
    ps = interpretar_hora_minuto(saida_almoco)
    pa = interpretar_hora_minuto(entrada_almoco)
    tem_almoco = ps is not None and pa is not None
    if tem_almoco:
        m_ps = ps[0] * 60 + ps[1]
        m_pa = pa[0] * 60 + pa[1]
        if m_ps < m_pe or m_pf < m_pa:
            return []
        return [(m_pe, m_ps), (m_pa, m_pf)]
    if (saida_almoco or "").strip() or (entrada_almoco or "").strip():
        return []
    if m_pf < m_pe:
        return []
    return [(m_pe, m_pf)]


# date.weekday(): 0 = segunda … 6 = domingo
_CHAVE_REGRAS_POR_WEEKDAY: dict[int, str] = {
    0: "segunda",
    1: "terca",
    2: "quarta",
    3: "quinta",
    4: "sexta",
    5: "sabado",
    6: "domingo",
}


def classificar_tipo_dia(d: date, config: dict[str, Any]) -> str:
    """
    Chave usada nas métricas e no JSON do dia: «feriado» ou um dos dias
    «segunda» … «domingo» (conforme `dias_semana` em config_regras_horas.json).
    """
    cfg = garantir_config_reglas_completa(config)
    iso = d.isoformat()
    if iso in conjunto_feriados_iso_para_ano(cfg, d.year):
        return "feriado"
    return _CHAVE_REGRAS_POR_WEEKDAY.get(d.weekday(), "segunda")


def calcular_metricas_horas_para_dia(
    dia: date,
    registro: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Calcula métricas para um registro diário (horários em `registro`).

    Chaves devolvidas alinhadas com `CHAVE_JSON_METRICAS_HORAS` / subcampos em schema.
    """
    cfg = garantir_config_reglas_completa(config)
    tipo = classificar_tipo_dia(dia, cfg)
    dias_sem = cfg.get("dias_semana") or {}
    tipos = cfg.get("tipos_dia") or {}
    if tipo == "feriado":
        regras = tipos.get("feriado") or {}
    else:
        regras = dias_sem.get(tipo) if isinstance(dias_sem.get(tipo), dict) else {}
        if not regras and tipo in CHAVES_DIAS_SEMANA:
            regras = dias_sem.get("segunda") or {}
        if not regras:
            regras = tipos.get("dia_util") or {}
    rotulo = str(regras.get("rotulo") or tipo)

    horarios = extrair_horarios_do_registro_dia(registro)
    e1 = str(horarios.get("ponto_entrada", "") or "").strip()
    s1 = str(horarios.get("ponto_saida_almoco", "") or "").strip()
    e2 = str(horarios.get("ponto_entrada_almoco", "") or "").strip()
    s2 = str(horarios.get("ponto_saida", "") or "").strip()

    minutos_trabalhados = calcular_minutos_jornada_liquida(e1, s1, e2, s2)
    if minutos_trabalhados is None:
        return {
            "tipo_dia": tipo,
            "rotulo_tipo_dia": rotulo,
            "minutos_trabalhados_total": 0,
            "minutos_normais": 0,
            "minutos_extra_50": 0,
            "minutos_extra_100": 0,
            "minutos_adicional_noturno": 0,
            "minutos_adicional_noturno_equivalente": 0.0,
            "trabalhadas_hhmm": "0:00",
            "normais_hhmm": "0:00",
            "extra_50_hhmm": "0:00",
            "extra_100_hhmm": "0:00",
            "adicional_noturno_hhmm": "0:00",
            "adicional_noturno_equivalente_hhmm": "0:00",
            "calculo_valido": False,
            "mensagem": "Preencha os horários entrada/saída e saída/entrada do almoço.",
        }

    jornada_n = int(regras.get("minutos_jornada_normal", 480))
    limite_50 = regras.get("minutos_extra_50_apos_normal")
    try:
        limite_50_int = int(limite_50) if limite_50 is not None and str(limite_50).strip() != "" else 0
    except (TypeError, ValueError):
        limite_50_int = 0
    resto_100 = bool(regras.get("resto_horas_como_extra_100", True))

    excedente = max(0, minutos_trabalhados - max(0, jornada_n))
    min_normais = min(minutos_trabalhados, max(0, jornada_n))
    min_e50 = 0
    min_e100 = 0
    if excedente > 0 and limite_50_int > 0:
        min_e50 = min(excedente, limite_50_int)
        resto = excedente - min_e50
        if resto_100:
            min_e100 = resto
        else:
            min_e50 += resto
    elif excedente > 0:
        if resto_100:
            min_e100 = excedente
        else:
            min_e50 = excedente

    cfg_noturno = (regras.get("adicional_noturno") or {}) if isinstance(regras.get("adicional_noturno"), dict) else {}
    segmentos = _segmentos_trabalho_dia(e1, s1, e2, s2)
    min_not_fis = 0
    min_not_equiv = 0.0
    for a, b in segmentos:
        fis, eq = _minutos_noturnos_no_intervalo(a, b, cfg_noturno)
        min_not_fis += fis
        min_not_equiv += eq

    equiv_arred = round(min_not_equiv, 2)
    return {
        "tipo_dia": tipo,
        "rotulo_tipo_dia": rotulo,
        "minutos_trabalhados_total": minutos_trabalhados,
        "minutos_normais": min_normais,
        "minutos_extra_50": min_e50,
        "minutos_extra_100": min_e100,
        "minutos_adicional_noturno": min_not_fis,
        "minutos_adicional_noturno_equivalente": equiv_arred,
        "trabalhadas_hhmm": minutos_para_hhmm(minutos_trabalhados),
        "normais_hhmm": minutos_para_hhmm(min_normais),
        "extra_50_hhmm": minutos_para_hhmm(min_e50),
        "extra_100_hhmm": minutos_para_hhmm(min_e100),
        "adicional_noturno_hhmm": minutos_para_hhmm(min_not_fis),
        "adicional_noturno_equivalente_hhmm": minutos_para_hhmm(equiv_arred),
        "calculo_valido": True,
        "mensagem": "",
    }


def agregar_metricas_mes(
    registros_diarios: dict[str, Any],
    ano: int,
    mes: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Soma métricas de todos os dias do mês com cálculo válido."""
    chaves = (
        "minutos_trabalhados_total",
        "minutos_normais",
        "minutos_extra_50",
        "minutos_extra_100",
        "minutos_adicional_noturno",
    )
    totais: dict[str, int] = {k: 0 for k in chaves}
    equiv_not = 0.0
    dias_com_ponto = 0
    prefixo = f"{ano:04d}-{mes:02d}-"
    for iso, reg in (registros_diarios or {}).items():
        if not isinstance(iso, str) or not iso.startswith(prefixo):
            continue
        if not isinstance(reg, dict):
            continue
        try:
            d = date.fromisoformat(iso)
        except ValueError:
            continue
        m = calcular_metricas_horas_para_dia(d, reg, config)
        if not m.get("calculo_valido"):
            continue
        dias_com_ponto += 1
        for k in chaves:
            totais[k] += int(m.get(k) or 0)
        equiv_not += float(m.get("minutos_adicional_noturno_equivalente") or 0.0)

    saida: dict[str, Any] = {k: int(totais[k]) for k in chaves}
    saida["minutos_adicional_noturno_equivalente"] = round(equiv_not, 2)
    saida["dias_com_calculo_valido"] = dias_com_ponto
    return saida


def gerar_relatorio_metricas_mes_texto(
    registros_diarios: dict[str, Any],
    ano: int,
    mes: int,
    config: dict[str, Any],
) -> str:
    """
    Texto multilinha com cada dia do mês que tenha ponto válido e respetivas métricas
    (útil para colar num relatório ou e-mail).
    """
    from rdo_diario.horario_util import formatar_minutos_como_texto

    prefixo = f"{ano:04d}-{mes:02d}-"
    linhas: list[str] = [
        f"Relatório de métricas — {mes:02d}/{ano}",
        "",
    ]
    dias: list[tuple[str, dict[str, Any]]] = []
    for iso, reg in sorted((registros_diarios or {}).items()):
        if not isinstance(iso, str) or not iso.startswith(prefixo):
            continue
        if not isinstance(reg, dict):
            continue
        try:
            d = date.fromisoformat(iso)
        except ValueError:
            continue
        m = calcular_metricas_horas_para_dia(d, reg, config)
        if not m.get("calculo_valido"):
            continue
        dias.append((iso, m))

    if not dias:
        linhas.append("Nenhum dia com ponto válido neste mês.")
        return "\n".join(linhas)

    for iso, m in dias:
        linhas.append(
            f"{iso} — {m.get('rotulo_tipo_dia', '')}: "
            f"trab. {formatar_minutos_como_texto(int(m.get('minutos_trabalhados_total') or 0))}, "
            f"norm. {formatar_minutos_como_texto(int(m.get('minutos_normais') or 0))}, "
            f"50% {formatar_minutos_como_texto(int(m.get('minutos_extra_50') or 0))}, "
            f"100% {formatar_minutos_como_texto(int(m.get('minutos_extra_100') or 0))}, "
            f"not. {formatar_minutos_como_texto(int(m.get('minutos_adicional_noturno') or 0))} "
            f"(equiv. {float(m.get('minutos_adicional_noturno_equivalente') or 0):.1f} min)"
        )
    linhas.append("")
    linhas.append("Totais do mês:")
    agg = agregar_metricas_mes(registros_diarios, ano, mes, config)
    linhas.append(formatar_resumo_metricas_texto(agg))
    return "\n".join(linhas)


def formatar_resumo_metricas_texto(metricas: dict[str, Any]) -> str:
    """Totais em h:mm — um indicador por linha (interface e relatório copiado)."""
    from rdo_diario.horario_util import formatar_minutos_como_texto

    def fmt(k: str) -> str:
        return formatar_minutos_como_texto(int(metricas.get(k) or 0))

    eq = float(metricas.get("minutos_adicional_noturno_equivalente") or 0)
    linhas = [
        f"Trabalhadas: {fmt('minutos_trabalhados_total')}",
        f"Normais: {fmt('minutos_normais')}",
        f"Extra 50%: {fmt('minutos_extra_50')}",
        f"Extra 100%: {fmt('minutos_extra_100')}",
        f"Noturno: {fmt('minutos_adicional_noturno')}",
    ]
    return "\n".join(linhas)
