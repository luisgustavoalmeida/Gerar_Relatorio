"""
Definição da estrutura dos dados em JSON.

Os **valores** das constantes CHAVE_JSON_* e CAMPOS_JSON_* são as chaves gravadas no ficheiro.
Mantê-las evita que dados já salvos pelo usuário deixem de ser lidos.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from rdo_diario.horario_util import calcular_tempo_servico_hhmm

# Número da versão do formato do documento (para migrações futuras).
VERSAO_ARQUIVO: int = 1

# --- Chaves dentro do objeto "chave" do JSON ---
CHAVE_JSON_CONTRATANTE: str = "contratante"
CHAVE_JSON_NATUREZA_SERVICO: str = "natureza_servico"

# --- Lista de campos do cabeçalho fixo (objeto cabecalho_fixo) ---
CAMPOS_JSON_CABECALHO: tuple[str, ...] = (
    "natureza_servico",
    "empreendimento",
    "contratante",
    "endereco",
    "cidade",
    "estado",
    "inicio_contratual",
    "termino_contratual",
    "contratada",
    "nome_funcionario",
    "telefone",
    "fiscalizacao",
    "nome_fiscal",
)

# --- Campos de texto livre por dia ---
CAMPOS_JSON_TEXTO_DIA: tuple[str, ...] = (
    "registro_servico",
    "registro_extra_escopo",
    "registro_ociosidade",
)

# Duração (horas:minutos) associada a extra-escopo e ociosidade — gravado no registro do dia
CAMPOS_JSON_TEMPO_ATIVIDADE_DIA: tuple[str, ...] = (
    "tempo_extra_escopo",
    "tempo_ociosidade",
)

# Duração derivada: trabalhadas (métricas) − extra-escopo − ociosidade (gravada após «tempo_ociosidade»)
CHAVE_JSON_TEMPO_SERVICO: str = "tempo_serviço"

# --- Horários de ponto (HH:MM) ---
CAMPOS_JSON_PONTO: tuple[str, ...] = (
    "ponto_entrada",
    "ponto_saida_almoco",
    "ponto_entrada_almoco",
    "ponto_saida",
)

CAMPOS_JSON_DESLOCAMENTO: tuple[str, ...] = (
    "deslocamento_ida",
    "deslocamento_volta",
)

# União ponto + deslocamento (ordem usada na interface)
CAMPOS_JSON_HORARIOS: tuple[str, ...] = CAMPOS_JSON_PONTO + CAMPOS_JSON_DESLOCAMENTO

# Lista legada de batidas (migração)
CHAVE_JSON_BATIDAS_PONTO: str = "batidas_ponto"

# Posição do relatório entre os dias preenchidos do mês (metadados no registro do dia)
CHAVE_JSON_NUMERO_RELATORIO_MES: str = "numero"
CHAVE_JSON_FOLHA_RELATORIO_MES: str = "folha"

# Métricas calculadas (normal / extra 50% / extra 100% / noturno) — preenchido ao gravar o dia.
# Inclui totais em minutos e duplicata em texto H:MM (*_hhmm).
CHAVE_JSON_METRICAS_HORAS: str = "metricas_horas"

# Metadados do dia (espelham a chave do objeto em «registros_diarios» e o calendário).
CHAVE_JSON_DATA_REGISTRO: str = "data"
CHAVE_JSON_DATA_DIA: str = "data_dia"
CHAVE_JSON_DIA_SEMANA: str = "dia_semana"
# Chave **dentro** de «metricas_horas» (tipo de dia nas regras: «Terça-feira», «Feriado», …).
CHAVE_JSON_ROTULO_TIPO_DIA: str = "rotulo_tipo_dia"

# --- Rótulos exibidos na interface (chave = campo JSON) ---
ROTULOS_CABECALHO: dict[str, str] = {
    "empreendimento": "Empreendimento",
    "contratante": "Contratante",
    "natureza_servico": "Natureza do serviço",
    "inicio_contratual": "Início contratual",
    "termino_contratual": "Término contratual",
    "contratada": "Contratada",
    "nome_funcionario": "Nome funcionário",
    "fiscalizacao": "Fiscalização",
    "nome_fiscal": "Nome fiscal",
    "telefone": "Telefone",
    "endereco": "Endereço",
    "cidade": "Cidade",
    "estado": "Estado",
}

ROTULOS_TEXTO_DIA: dict[str, str] = {
    "registro_servico": "Registro serviço",
    "registro_extra_escopo": "Registro extra-escopo",
    "registro_ociosidade": "Registro ociosidade",
}

ROTULOS_TEMPO_ATIVIDADE_DIA: dict[str, str] = {
    "tempo_extra_escopo": "Tempo consumido nesta atividade (h:mm)",
    "tempo_ociosidade": "Tempo consumido nesta atividade (h:mm)",
}

ROTULOS_HORARIO: dict[str, str] = {
    "ponto_entrada": "Entrada",
    "ponto_saida_almoco": "Saída almoço",
    "ponto_entrada_almoco": "Entrada almoço",
    "ponto_saida": "Saída",
    "deslocamento_ida": "Ida",
    "deslocamento_volta": "Volta",
}

# Converte tipo antigo em lista batidas_ponto → nome do campo fixo atual
_NOMES_DIA_SEMANA_PORTUGUES: tuple[str, ...] = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def nome_dia_semana_portugues(d: date) -> str:
    """Nome completo do dia da semana em português, com inicial maiúscula (ex.: «Terça-feira»)."""
    return _NOMES_DIA_SEMANA_PORTUGUES[d.weekday()].capitalize()


def garantir_tempo_servico_no_registro(registro: dict[str, Any]) -> None:
    """
    Define «tempo_serviço» e coloca-o logo a seguir a «tempo_ociosidade» (ordem no JSON).

    Remove a chave legada «tempo_escopo».
    """
    registro.pop("tempo_escopo", None)
    ch = CHAVE_JSON_TEMPO_SERVICO
    registro.pop(ch, None)
    mh = registro.get(CHAVE_JSON_METRICAS_HORAS)
    trab = str(mh.get("trabalhadas_hhmm") or "").strip() if isinstance(mh, dict) else ""
    extra = str(registro.get("tempo_extra_escopo") or "").strip()
    oci = str(registro.get("tempo_ociosidade") or "").strip()
    val = calcular_tempo_servico_hhmm(trab, extra, oci)
    pares = list(registro.items())
    novo: dict[str, Any] = {}
    inseriu = False
    for k, v in pares:
        if k == ch:
            continue
        novo[k] = v
        if k == "tempo_ociosidade":
            novo[ch] = val
            inseriu = True
    if not inseriu:
        novo2: dict[str, Any] = {}
        for k, v in novo.items():
            if k == CHAVE_JSON_METRICAS_HORAS:
                novo2[ch] = val
                inseriu = True
            novo2[k] = v
        novo = novo2
    if not inseriu:
        novo[ch] = val
    registro.clear()
    registro.update(novo)


def aplicar_metadados_data_no_registro_diario(iso_data: str, registro: dict[str, Any]) -> None:
    """
    Preenche a partir da chave ISO do registo:

    - «data» (AAAA-MM-DD)
    - «data_dia» (DD/MM/AAAA, ex.: 30/12/2026)
    - «dia_semana» (dia civil: segunda-feira … domingo, inicial maiúscula)
    - «tempo_serviço» (duração «H:MM», após «tempo_ociosidade»): «metricas_horas.trabalhadas_hhmm»
      − «tempo_extra_escopo» − «tempo_ociosidade»

    O rótulo do tipo de dia nas regras (ex.: «Feriado») fica só em «metricas_horas.rotulo_tipo_dia».
    """
    iso = str(iso_data or "").strip()[:10]
    registro[CHAVE_JSON_DATA_REGISTRO] = iso
    if len(iso) >= 10:
        try:
            d = date.fromisoformat(iso)
            registro[CHAVE_JSON_DATA_DIA] = d.strftime("%d/%m/%Y")
            registro[CHAVE_JSON_DIA_SEMANA] = nome_dia_semana_portugues(d)
        except ValueError:
            registro[CHAVE_JSON_DATA_DIA] = ""
            registro[CHAVE_JSON_DIA_SEMANA] = ""
    else:
        registro[CHAVE_JSON_DATA_DIA] = ""
        registro[CHAVE_JSON_DIA_SEMANA] = ""
    # Legado: «rotulo_tipo_dia» na raiz duplicava «dia_semana» ou «metricas_horas.rotulo_tipo_dia».
    registro.pop(CHAVE_JSON_ROTULO_TIPO_DIA, None)
    garantir_tempo_servico_no_registro(registro)


def normalizar_metadados_registros_diarios(documento: dict[str, Any]) -> None:
    """Garante «data», «data_dia», «dia_semana» e «tempo_serviço»; remove «rotulo_tipo_dia» na raiz (legado)."""
    regs = documento.get("registros_diarios")
    if not isinstance(regs, dict):
        return
    for iso, reg in regs.items():
        if not isinstance(reg, dict):
            continue
        aplicar_metadados_data_no_registro_diario(str(iso), reg)


MAPEAMENTO_TIPO_BATIDA_PARA_CAMPO: dict[str, str] = {
    "entrada_trabalho_1": "ponto_entrada",
    "saida_trabalho_1": "ponto_saida_almoco",
    "entrada_trabalho_2": "ponto_entrada_almoco",
    "saida_trabalho_2": "ponto_saida",
    "entrada_trabalho": "ponto_entrada",
    "saida_intervalo": "ponto_saida_almoco",
    "retorno_intervalo": "ponto_entrada_almoco",
    "saida_trabalho": "ponto_saida",
}


def _normalizar_tipo_batida_legado(tipo: str) -> str:
    """
    Converte identificadores antigos de tipo de batida para o formato canónico
    usado no mapa MAPEAMENTO_TIPO_BATIDA_PARA_CAMPO.
    """
    t = str(tipo or "").strip()
    legado = {
        "entrada_trabalho": "entrada_trabalho_1",
        "saida_intervalo": "saida_trabalho_1",
        "retorno_intervalo": "entrada_trabalho_2",
        "saida_trabalho": "saida_trabalho_2",
    }
    return legado.get(t, t)


def extrair_horarios_do_registro_dia(registro: dict) -> dict[str, str]:
    """
    Obtém os seis campos de horário (ponto + deslocamento) a partir do registro do dia.

    Se o JSON ainda tiver apenas `batidas_ponto` ou `jornada_*`, converte para os campos fixos.
    """
    resultado: dict[str, str] = {
        k: str(registro.get(k, "") or "").strip() for k in CAMPOS_JSON_HORARIOS
    }
    if any(resultado[k] for k in CAMPOS_JSON_PONTO):
        return resultado

    lista = registro.get(CHAVE_JSON_BATIDAS_PONTO)
    if isinstance(lista, list):
        for item in lista:
            if not isinstance(item, dict):
                continue
            tipo_norm = _normalizar_tipo_batida_legado(str(item.get("tipo") or ""))
            campo = MAPEAMENTO_TIPO_BATIDA_PARA_CAMPO.get(tipo_norm)
            if not campo:
                continue
            hora_txt = str(item.get("hora", "") or "").strip()
            if hora_txt:
                resultado[campo] = hora_txt
        if any(resultado[k] for k in CAMPOS_JSON_PONTO):
            return resultado

    je = str(registro.get("jornada_entrada", "") or "").strip()
    js = str(registro.get("jornada_saida", "") or "").strip()
    if je:
        resultado["ponto_entrada"] = je
    if js:
        resultado["ponto_saida"] = js
    return resultado


def registro_de_dia_possui_conteudo(registro: dict) -> bool:
    """
    Indica se o dia deve ser considerado “preenchido” (calendário verde, manter no JSON).

    Considera textos, horários, lista legada de batidas e campos jornada antigos.
    """
    if not registro:
        return False
    for campo in CAMPOS_JSON_TEXTO_DIA:
        if str(registro.get(campo, "") or "").strip():
            return True
    for campo in CAMPOS_JSON_TEMPO_ATIVIDADE_DIA:
        if str(registro.get(campo, "") or "").strip():
            return True
    for campo in CAMPOS_JSON_HORARIOS:
        if str(registro.get(campo, "") or "").strip():
            return True
    if isinstance(registro.get(CHAVE_JSON_BATIDAS_PONTO), list):
        for b in registro[CHAVE_JSON_BATIDAS_PONTO]:
            if isinstance(b, dict) and (
                str(b.get("hora", "") or "").strip()
                or str(b.get("observacao", "") or "").strip()
            ):
                return True
    if str(registro.get("jornada_entrada", "") or "").strip():
        return True
    if str(registro.get("jornada_saida", "") or "").strip():
        return True
    return False


def criar_estrutura_documento_vazio(contratante: str, natureza_servico: str) -> dict:
    """
    Monta o dicionário inicial de um novo cliente (ficheiro JSON vazio mas válido).

    Args:
        contratante: nome do contratante (parte da chave do ficheiro).
        natureza_servico: natureza do serviço (parte da chave do ficheiro).
    """
    c = (contratante or "").strip()
    n = (natureza_servico or "").strip()
    return {
        "versao": VERSAO_ARQUIVO,
        "chave": {
            CHAVE_JSON_CONTRATANTE: c,
            CHAVE_JSON_NATUREZA_SERVICO: n,
        },
        "cabecalho_fixo": {campo: "" for campo in CAMPOS_JSON_CABECALHO},
        "registros_diarios": {},
        "meta": {"ultima_edicao_iso": ""},
    }
