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


_MINUTOS_DIA = 24 * 60
# Limite de segurança: jornada contínua absurda (ex.: batidas iguais mal interpretadas).
_MAX_MINUTOS_JORNADA = 36 * 60


def minutos_relogio_para_hhmm(minutos_desde_meia_noite: int) -> str:
    """Converte minutos (qualquer sinal/excesso) para HH:MM no relógio 00:00–23:59."""
    m = int(minutos_desde_meia_noite) % _MINUTOS_DIA
    if m < 0:
        m += _MINUTOS_DIA
    h, mins = divmod(m, 60)
    return f"{h:02d}:{mins:02d}"


def _encadear_minuto_relogio(anterior_abs: int, relogio_min: int) -> int | None:
    """
    Próximo instante absoluto após ``anterior_abs``.

    Se o relógio for menor que o da batida anterior no dia civil, assume virada
    de meia-noite (+24 h). No máximo uma virada por batida.
    """
    local_ant = anterior_abs % _MINUTOS_DIA
    dia = anterior_abs // _MINUTOS_DIA
    if relogio_min > local_ant:
        candidato = dia * _MINUTOS_DIA + relogio_min
    elif relogio_min < local_ant:
        candidato = (dia + 1) * _MINUTOS_DIA + relogio_min
    else:
        return None
    if candidato <= anterior_abs:
        return None
    return candidato


def _batidas_ponto_minutos_absolutos(
    entrada: str,
    saida_almoco: str,
    entrada_almoco: str,
    saida: str,
) -> list[int] | None:
    """
    Batidas em minutos absolutos (0 = 00:00 do dia da Entrada), com suporte a virada de dia.

    Sem almoço: [entrada, saída].
    Com almoço: [entrada, saída_almoço, entrada_almoço, saída].
    None se incompleto ou ordem impossível.
    """
    pe = interpretar_hora_minuto(entrada)
    pf = interpretar_hora_minuto(saida)
    if pe is None or pf is None:
        return None
    ps = interpretar_hora_minuto(saida_almoco)
    pa = interpretar_hora_minuto(entrada_almoco)
    tem_almoco = ps is not None and pa is not None
    if not tem_almoco and ((saida_almoco or "").strip() or (entrada_almoco or "").strip()):
        return None

    m_pe = _para_minutos_desde_meia_noite(pe)
    m_pf = _para_minutos_desde_meia_noite(pf)
    if not tem_almoco:
        if m_pf > m_pe:
            return [m_pe, m_pf]
        if m_pf < m_pe:
            # Saída no dia seguinte.
            return [m_pe, m_pf + _MINUTOS_DIA]
        return None

    m_ps = _para_minutos_desde_meia_noite(ps)
    m_pa = _para_minutos_desde_meia_noite(pa)
    t0 = m_pe
    t1 = _encadear_minuto_relogio(t0, m_ps)
    if t1 is None:
        return None
    t2 = _encadear_minuto_relogio(t1, m_pa)
    if t2 is None:
        return None
    t3 = _encadear_minuto_relogio(t2, m_pf)
    if t3 is None:
        return None
    return [t0, t1, t2, t3]


def intervalos_jornada_minutos_absolutos(
    entrada: str,
    saida_almoco: str,
    entrada_almoco: str,
    saida: str,
) -> list[tuple[int, int]] | None:
    """
    Intervalos de trabalho [início, fim) em minutos absolutos (almoço excluído).

    Suporta virada de meia-noite entre batidas. None se inválido.
    """
    batidas = _batidas_ponto_minutos_absolutos(entrada, saida_almoco, entrada_almoco, saida)
    if not batidas:
        return None
    if len(batidas) == 2:
        intervalos = [(batidas[0], batidas[1])]
    elif len(batidas) == 4:
        intervalos = [(batidas[0], batidas[1]), (batidas[2], batidas[3])]
    else:
        return None
    for a, b in intervalos:
        if b <= a:
            return None
    total = sum(b - a for a, b in intervalos)
    if total <= 0 or total > _MAX_MINUTOS_JORNADA:
        return None
    return intervalos


def aplicar_deslocamento_aos_intervalos(
    intervalos: list[tuple[int, int]],
    deslocamento_ida: str,
    deslocamento_volta: str,
) -> list[tuple[int, int]]:
    """Antecipa o início pela Ida e atrasa o fim pela Volta (durações)."""
    if not intervalos:
        return []
    min_ida = duracao_hhmm_para_minutos(deslocamento_ida)
    min_volta = duracao_hhmm_para_minutos(deslocamento_volta)
    saida = [ (a, b) for a, b in intervalos ]
    a0, b0 = saida[0]
    saida[0] = (a0 - min_ida, b0)
    a1, b1 = saida[-1]
    saida[-1] = (a1, b1 + min_volta)
    return saida


def segmentos_locais_para_noturno(
    intervalos_abs: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """
    Parte intervalos absolutos em trechos no relógio local 0..1440
    (fim = 1440 representa 24:00), para cruzar com a janela noturna.
    """
    locais: list[tuple[int, int]] = []
    for inicio_abs, fim_abs in intervalos_abs:
        if fim_abs <= inicio_abs:
            continue
        cur = inicio_abs
        while cur < fim_abs:
            dia_inicio = (cur // _MINUTOS_DIA) * _MINUTOS_DIA
            dia_fim = dia_inicio + _MINUTOS_DIA
            trecho_fim = min(fim_abs, dia_fim)
            local_a = cur - dia_inicio
            local_b = trecho_fim - dia_inicio  # 1..1440
            if local_b > local_a:
                locais.append((local_a, local_b))
            cur = trecho_fim
    return locais


def calcular_minutos_jornada_liquida(
    entrada: str,
    saida_almoco: str,
    entrada_almoco: str,
    saida: str,
) -> int | None:
    """
    Calcula minutos trabalhados sem contar o almoço.

    Suporta término no dia seguinte (ex.: Entrada 22:00, Saída 06:00 → 8 h).
    Com almoço: soma os dois períodos; cada batida pode virar a meia-noite uma vez.
    Devolve None se a combinação for inconsistente ou faltar entrada/saída principais.
    """
    intervalos = intervalos_jornada_minutos_absolutos(
        entrada, saida_almoco, entrada_almoco, saida
    )
    if not intervalos:
        return None
    return sum(b - a for a, b in intervalos)


def formatar_minutos_como_texto(total_minutos: int) -> str:
    """Formata uma duração em minutos como «X h YY min»."""
    horas, minutos = divmod(max(0, int(total_minutos)), 60)
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


def minutos_deslocamento_ida_volta(deslocamento_ida: str, deslocamento_volta: str) -> int:
    """Soma as durações de ida e volta (HH:MM interpretado como duração)."""
    return duracao_hhmm_para_minutos(deslocamento_ida) + duracao_hhmm_para_minutos(
        deslocamento_volta
    )


def ajustar_horario_por_minutos(horario_hhmm: str, delta_minutos: int) -> str:
    """
    Soma ``delta_minutos`` a um horário de relógio HH:MM.

    O resultado envolve no ciclo de 24 h (ex.: 23:30 + 1 h → 00:30; 00:30 − 1 h → 23:30).
    Vazio ou inválido → string vazia.
    """
    par = interpretar_hora_minuto(horario_hhmm)
    if par is None:
        return ""
    total = _para_minutos_desde_meia_noite(par) + int(delta_minutos)
    return minutos_relogio_para_hhmm(total)


def horarios_ponto_com_deslocamento_para_ft(
    ponto_entrada: str,
    ponto_saida_almoco: str,
    ponto_entrada_almoco: str,
    ponto_saida: str,
    deslocamento_ida: str,
    deslocamento_volta: str,
) -> dict[str, str]:
    """
    Horários de ponto para a FT quando o deslocamento entra no cálculo:

    - Ida (duração) antecipa a Entrada (pode ir para o dia anterior no relógio);
    - Volta (duração) atrasa a Saída (pode ir para o dia seguinte no relógio);
    - Almoço permanece igual.
    """
    intervalos = intervalos_jornada_minutos_absolutos(
        ponto_entrada,
        ponto_saida_almoco,
        ponto_entrada_almoco,
        ponto_saida,
    )
    entrada = str(ponto_entrada or "").strip()
    saida = str(ponto_saida or "").strip()
    if intervalos:
        estendidos = aplicar_deslocamento_aos_intervalos(
            intervalos, deslocamento_ida, deslocamento_volta
        )
        entrada = minutos_relogio_para_hhmm(estendidos[0][0])
        saida = minutos_relogio_para_hhmm(estendidos[-1][1])
    else:
        min_ida = duracao_hhmm_para_minutos(deslocamento_ida)
        min_volta = duracao_hhmm_para_minutos(deslocamento_volta)
        if entrada and min_ida > 0:
            entrada = ajustar_horario_por_minutos(entrada, -min_ida) or entrada
        if saida and min_volta > 0:
            saida = ajustar_horario_por_minutos(saida, min_volta) or saida
    return {
        "ponto_entrada": entrada,
        "ponto_saida_almoco": str(ponto_saida_almoco or "").strip(),
        "ponto_entrada_almoco": str(ponto_entrada_almoco or "").strip(),
        "ponto_saida": saida,
    }
