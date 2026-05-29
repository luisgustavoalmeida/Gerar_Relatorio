"""
Normalização de texto no formato HH:MM e cálculo da jornada líquida (sem intervalo de almoço).
"""

from __future__ import annotations

import re


def extrair_apenas_digitos(texto: str) -> str:
    """Remove tudo que não for dígito (útil ao interpretar horas coladas ou misturadas)."""
    return "".join(caractere for caractere in texto if caractere.isdigit())


def normalizar_texto_horario(texto: str) -> str:
    """
    Converte entradas variadas para HH:MM válido (24 h) ou string vazia se inválido.

    Exemplos aceites: 13:55, 13:5, 1355, 855 → 08:55 após normalização quando aplicável.
    """
    s = (texto or "").strip().replace(" ", "")
    if not s:
        return ""
    if ":" in s:
        partes = s.split(":", 1)
        dh = extrair_apenas_digitos(partes[0])
        dm = extrair_apenas_digitos(partes[1]) if len(partes) > 1 else ""
        if not dh and not dm:
            return ""
        hora = int(dh) if dh else 0
        minuto = int(dm) if dm else 0
    else:
        d = extrair_apenas_digitos(s)
        if len(d) >= 4:
            hora, minuto = int(d[:2]), int(d[2:4])
        elif len(d) == 3:
            hora, minuto = int(d[0]), int(d[1:])
        elif len(d) == 2:
            hora, minuto = int(d), 0
        elif len(d) == 1:
            hora, minuto = int(d), 0
        else:
            return ""
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return ""
    return f"{hora:02d}:{minuto:02d}"


def interpretar_hora_minuto(texto: str) -> tuple[int, int] | None:
    """
    Devolve (hora, minuto) após normalizar o texto, ou None se não for um horário válido.
    """
    normalizado = normalizar_texto_horario(texto)
    if not normalizado or ":" not in normalizado:
        return None
    parte_hora, parte_minuto = normalizado.split(":", 1)
    try:
        return int(parte_hora), int(parte_minuto)
    except ValueError:
        return None


def _para_minutos_desde_meia_noite(hora_minuto: tuple[int, int]) -> int:
    """Converte (h, m) em minutos desde 00:00."""
    return hora_minuto[0] * 60 + hora_minuto[1]


def calcular_minutos_jornada_liquida(
    entrada: str,
    saida_almoco: str,
    entrada_almoco: str,
    saida: str,
) -> int | None:
    """
    Calcula minutos trabalhados sem contar o almoço.

    Com almoço completo: (saída almoço − entrada) + (saída − entrada almoço).
    Sem almoço (saída e entrada almoço vazios): saída − entrada.
    Devolve None se a combinação for inconsistente ou faltar entrada/saída principais.
    """
    pe = interpretar_hora_minuto(entrada)
    ps = interpretar_hora_minuto(saida_almoco)
    pa = interpretar_hora_minuto(entrada_almoco)
    pf = interpretar_hora_minuto(saida)
    if pe is None or pf is None:
        return None
    tem_almoco = ps is not None and pa is not None
    if tem_almoco:
        m_pe, m_ps, m_pa, m_pf = (
            _para_minutos_desde_meia_noite(pe),
            _para_minutos_desde_meia_noite(ps),
            _para_minutos_desde_meia_noite(pa),
            _para_minutos_desde_meia_noite(pf),
        )
        if not (m_pe < m_ps < m_pa < m_pf):
            return None
        return (m_ps - m_pe) + (m_pf - m_pa)
    if ps is not None or pa is not None:
        return None
    m_pe, m_pf = _para_minutos_desde_meia_noite(pe), _para_minutos_desde_meia_noite(pf)
    if m_pf <= m_pe:
        return None
    return m_pf - m_pe


def formatar_minutos_como_texto(total_minutos: int) -> str:
    """Formata uma duração em minutos como «X h YY min»."""
    horas, minutos = divmod(total_minutos, 60)
    return f"{horas} h {minutos:02d} min"


def minutos_para_hhmm(total_minutos: int | float) -> str:
    """
    Converte duração em minutos para «H:MM» ou «HH:MM» (horas podem ultrapassar 23).

    Valores não inteiros são arredondados ao minuto mais próximo; negativos viram «0:00».
    """
    try:
        m = int(round(float(total_minutos)))
    except (TypeError, ValueError):
        m = 0
    if m < 0:
        m = 0
    horas, mins = divmod(m, 60)
    return f"{horas}:{mins:02d}"


def texto_horario_permitido_na_digitacao(proposta: str) -> bool:
    """
    Validação para `validatecommand` do Tk: só dígitos e «:», comprimento máximo durante a digitação.
    """
    if proposta == "":
        return True
    if len(proposta) > 5:
        return False
    return re.match(r"^[0-9:]+$", proposta) is not None


def normalizar_duracao_hhmm(texto: str) -> str:
    """
    Normaliza duração em horas e minutos (não é relógio: horas podem passar de 23).

    Exemplos: «2:30», «130» (1 h 30 min), «8» (8 horas), «8:15» (8 horas 15 min).
    Devolve string «H:MM» ou «HH:MM» ou vazio se inválido (minutos > 59 ou horas > 999).

    Nota: Interpreta números como horas (igual ao campo de entrada):
      • 1 dígito «8» → 8:00 (8 horas)
      • 2 dígitos «45» → 45:00 (45 horas)
      • 3 dígitos «130» → 1:30 (1 hora 30 minutos)
      • 4+ dígitos «1330» → 13:30
    """
    s = (texto or "").strip().replace(" ", "")
    if not s:
        return ""
    if ":" in s:
        partes = s.split(":", 1)
        dh = extrair_apenas_digitos(partes[0])
        dm = extrair_apenas_digitos(partes[1]) if len(partes) > 1 else ""
        if not dh and not dm:
            return ""
        horas = int(dh) if dh else 0
        minutos = int(dm) if dm else 0
    else:
        d = extrair_apenas_digitos(s)
        # Igual ao normalizar_texto_horario, mas sem limite de 23 horas
        if len(d) >= 4:
            horas, minutos = int(d[:-2]), int(d[-2:])
        elif len(d) == 3:
            horas, minutos = int(d[0]), int(d[1:])
        elif len(d) == 2:
            horas, minutos = int(d), 0  # 2 dígitos = horas (não minutos!)
        elif len(d) == 1:
            horas, minutos = int(d), 0  # 1 dígito = horas (não minutos!)
        else:
            return ""
    if not (0 <= minutos <= 59 and 0 <= horas <= 999):
        return ""
    return f"{horas}:{minutos:02d}"


def texto_duracao_permitido_na_digitacao(proposta: str) -> bool:
    """Como o horário, mas permite mais caracteres para horas longas (ex.: «150:30»)."""
    if proposta == "":
        return True
    if len(proposta) > 8:
        return False
    return re.match(r"^[0-9:]+$", proposta) is not None


def duracao_hhmm_para_minutos(texto: str) -> int:
    """Converte duração «H:MM» (via `normalizar_duracao_hhmm`) em minutos; inválido ou vazio → 0."""
    n = normalizar_duracao_hhmm((texto or "").strip())
    if not n:
        return 0
    partes = n.split(":", 1)
    try:
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
    except ValueError:
        return 0
    if not (0 <= m <= 59 and 0 <= h <= 9999):
        return 0
    return h * 60 + m


def calcular_tempo_servico_hhmm(
    trabalhadas_hhmm: str,
    tempo_extra_escopo: str,
    tempo_ociosidade: str,
) -> str:
    """
    Duração «tempo_serviço» = trabalhadas − (extra-escopo + ociosidade), em «H:MM».

    Usa as mesmas regras de texto que `normalizar_duracao_hhmm`; resultado mínimo «0:00».
    """
    t = duracao_hhmm_para_minutos(trabalhadas_hhmm)
    e = duracao_hhmm_para_minutos(tempo_extra_escopo)
    o = duracao_hhmm_para_minutos(tempo_ociosidade)
    return minutos_para_hhmm(max(0, t - e - o))
