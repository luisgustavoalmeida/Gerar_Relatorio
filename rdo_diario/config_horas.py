"""
Carregamento e gravação de `config_regras_horas.json` e sincronização de feriados do Brasil.

O ficheiro é criado com valores padrão na primeira utilização. A lista de feriados pode ser
atualizada pelo menu da aplicação com base no calendário nacional (biblioteca `holidays`).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdo_diario.paths import ARQUIVO_CONFIG_REGRAS_HORAS_JSON, PASTA_DADOS_RDO

VERSAO_CONFIG_REGRAS: int = 2

# Chaves canónicas em `dias_semana` (segunda-feira = 0 … domingo = 6 em `date.weekday()`).
CHAVES_DIAS_SEMANA: tuple[str, ...] = (
    "segunda",
    "terca",
    "quarta",
    "quinta",
    "sexta",
    "sabado",
    "domingo",
)

_BLOCO_NOTURNO_PADRAO: dict[str, Any] = {
    "ativo": True,
    "inicio": "22:00",
    "fim": "05:00",
    "incluir_hora_reduzida_clt": True,
    "minutos_hora_noturna": 52,
    "segundos_hora_noturna": 30,
}

_BLOCO_DIA_UTIL_PADRAO: dict[str, Any] = {
    "rotulo": "Dia útil",
    "minutos_jornada_normal": 480,
    "minutos_extra_50_apos_normal": 120,
    "resto_horas_como_extra_100": True,
    "adicional_noturno": dict(_BLOCO_NOTURNO_PADRAO),
}

_BLOCO_FIM_SEMANA_PADRAO: dict[str, Any] = {
    "minutos_jornada_normal": 0,
    "minutos_extra_50_apos_normal": 0,
    "resto_horas_como_extra_100": True,
    "adicional_noturno": dict(_BLOCO_NOTURNO_PADRAO),
}

_DEFAULT_DIAS_SEMANA: dict[str, Any] = {
    "segunda": {
        "rotulo": "Segunda-feira",
        **{k: v for k, v in _BLOCO_DIA_UTIL_PADRAO.items() if k != "rotulo"},
    },
    "terca": {
        "rotulo": "Terça-feira",
        **{k: v for k, v in _BLOCO_DIA_UTIL_PADRAO.items() if k != "rotulo"},
    },
    "quarta": {
        "rotulo": "Quarta-feira",
        **{k: v for k, v in _BLOCO_DIA_UTIL_PADRAO.items() if k != "rotulo"},
    },
    "quinta": {
        "rotulo": "Quinta-feira",
        **{k: v for k, v in _BLOCO_DIA_UTIL_PADRAO.items() if k != "rotulo"},
    },
    "sexta": {
        "rotulo": "Sexta-feira",
        **{k: v for k, v in _BLOCO_DIA_UTIL_PADRAO.items() if k != "rotulo"},
    },
    "sabado": {
        "rotulo": "Sábado",
        **dict(_BLOCO_FIM_SEMANA_PADRAO),
    },
    "domingo": {
        "rotulo": "Domingo",
        **dict(_BLOCO_FIM_SEMANA_PADRAO),
    },
}

DEFAULT_CONFIG_REGRAS_HORAS: dict[str, Any] = {
    "versao": VERSAO_CONFIG_REGRAS,
    "descricao": (
        "Regras para classificar horas (normal, extra 50%, extra 100%, adicional noturno). "
        "Configure cada dia da semana em «dias_semana»; feriados em «tipos_dia.feriado» "
        "(datas em «feriados.por_ano»). Menu: «Sincronizar feriados BR»."
    ),
    "dias_semana": json.loads(json.dumps(_DEFAULT_DIAS_SEMANA)),
    "tipos_dia": {
        "feriado": {
            "rotulo": "Feriado",
            "minutos_jornada_normal": 0,
            "minutos_extra_50_apos_normal": 0,
            "resto_horas_como_extra_100": True,
            "adicional_noturno": dict(_BLOCO_NOTURNO_PADRAO),
        },
    },
    "feriados": {
        "por_ano": {},
        "ultima_sincronizacao_iso": "",
        "fonte_sincronizacao": "holidays (Brasil)",
    },
}


def _deep_merge_defaults(alvo: dict[str, Any], padrao: dict[str, Any]) -> None:
    for chave, valor in padrao.items():
        if chave not in alvo:
            alvo[chave] = json.loads(json.dumps(valor)) if isinstance(valor, (dict, list)) else valor
            continue
        if isinstance(valor, dict) and isinstance(alvo.get(chave), dict):
            _deep_merge_defaults(alvo[chave], valor)  # type: ignore[arg-type]


def _migrar_v1_tipos_dia_para_dias_semana(dados: dict[str, Any]) -> None:
    """
    Ficheiros com versão < 2: copia `tipos_dia.dia_util` para segunda…sexta
    e `sabado`/`domingo` para os respetivos dias (preserva comportamento antigo).
    """
    tipos = dados.get("tipos_dia")
    if not isinstance(tipos, dict):
        return
    du = tipos.get("dia_util") if isinstance(tipos.get("dia_util"), dict) else None
    sab = tipos.get("sabado") if isinstance(tipos.get("sabado"), dict) else None
    dom = tipos.get("domingo") if isinstance(tipos.get("domingo"), dict) else None
    if not du and not sab and not dom:
        return
    ds = dados.setdefault("dias_semana", {})
    if not isinstance(ds, dict):
        dados["dias_semana"] = {}
        ds = dados["dias_semana"]

    def copiar(b: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(b))

    if du:
        for ch in ("segunda", "terca", "quarta", "quinta", "sexta"):
            ds[ch] = copiar(du)
    if sab:
        ds["sabado"] = copiar(sab)
    if dom:
        ds["domingo"] = copiar(dom)


def _garantir_chaves_dias_semana(dados: dict[str, Any]) -> None:
    """Garante as sete chaves em «dias_semana» com fusão dos campos em falta."""
    ds = dados.setdefault("dias_semana", {})
    if not isinstance(ds, dict):
        dados["dias_semana"] = {}
        ds = dados["dias_semana"]
    ref = DEFAULT_CONFIG_REGRAS_HORAS.get("dias_semana") or {}
    for ch in CHAVES_DIAS_SEMANA:
        if ch not in ds or not isinstance(ds.get(ch), dict):
            ds[ch] = json.loads(json.dumps(ref.get(ch) or {}))
            continue
        if isinstance(ref.get(ch), dict):
            _deep_merge_defaults(ds[ch], ref[ch])


def garantir_config_reglas_completa(bruto: dict[str, Any]) -> dict[str, Any]:
    """Garante chaves mínimas copiando valores padrão onde faltarem."""
    dados = dict(bruto)
    versao_ficheiro = int(dados.get("versao") or 1)
    _deep_merge_defaults(dados, DEFAULT_CONFIG_REGRAS_HORAS)
    if versao_ficheiro < VERSAO_CONFIG_REGRAS:
        _migrar_v1_tipos_dia_para_dias_semana(dados)
    _garantir_chaves_dias_semana(dados)
    dados["versao"] = VERSAO_CONFIG_REGRAS
    feriados = dados.setdefault("feriados", {})
    feriados.setdefault("por_ano", {})
    feriados["por_ano"] = _normalizar_feriados_por_ano(feriados.get("por_ano"))
    feriados.setdefault("ultima_sincronizacao_iso", "")
    feriados.setdefault("fonte_sincronizacao", "holidays (Brasil)")
    return dados


def _normalizar_feriados_por_ano(bruto_por_ano: Any) -> dict[str, dict[str, str]]:
    """
    Normaliza `feriados.por_ano` para o formato canónico:
    `{"2026": {"2026-01-01": "Confraternização Universal", ...}}`.

    Aceita formatos legados:
    - lista de datas (`["2026-01-01", ...]`)
    - lista de objetos (`[{"data": "...", "nome": "..."}, ...]`)
    - dicionário data->nome (formato novo)
    """
    resultado: dict[str, dict[str, str]] = {}
    if not isinstance(bruto_por_ano, dict):
        return resultado
    for ano_chave, valor in bruto_por_ano.items():
        ano = str(ano_chave).strip()
        if not ano:
            continue
        mapa_ano: dict[str, str] = {}
        if isinstance(valor, dict):
            for data_iso, nome in valor.items():
                d = str(data_iso).strip()
                if not d:
                    continue
                mapa_ano[d] = str(nome or "").strip()
        elif isinstance(valor, list):
            for item in valor:
                if isinstance(item, str):
                    d = item.strip()
                    if d:
                        mapa_ano[d] = mapa_ano.get(d, "")
                    continue
                if isinstance(item, dict):
                    d = str(item.get("data") or item.get("date") or "").strip()
                    if not d:
                        continue
                    n = str(item.get("nome") or item.get("name") or "").strip()
                    mapa_ano[d] = n
        if mapa_ano:
            resultado[ano] = dict(sorted(mapa_ano.items()))
    return resultado


def carregar_config_regras_horas(caminho: Path | None = None) -> dict[str, Any]:
    """Lê o JSON de regras ou devolve o padrão fundido se o ficheiro não existir."""
    alvo = caminho or ARQUIVO_CONFIG_REGRAS_HORAS_JSON
    if not alvo.is_file():
        return garantir_config_reglas_completa({})
    try:
        with alvo.open(encoding="utf-8") as f:
            bruto = json.load(f)
        if not isinstance(bruto, dict):
            return garantir_config_reglas_completa({})
        return garantir_config_reglas_completa(bruto)
    except (json.JSONDecodeError, OSError):
        return garantir_config_reglas_completa({})


def garantir_arquivo_config_regras_existe() -> None:
    """Cria `config_regras_horas.json` com o padrão na primeira execução, se ainda não existir."""
    if ARQUIVO_CONFIG_REGRAS_HORAS_JSON.is_file():
        return
    salvar_config_regras_horas(garantir_config_reglas_completa({}))


def salvar_config_regras_horas(documento: dict[str, Any], caminho: Path | None = None) -> None:
    """Grava o JSON com escrita atómica."""
    alvo = caminho or ARQUIVO_CONFIG_REGRAS_HORAS_JSON
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    doc = dict(documento)
    doc.setdefault("versao", VERSAO_CONFIG_REGRAS)
    temporario = alvo.with_suffix(".json.tmp")
    with temporario.open("w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    temporario.replace(alvo)


def sincronizar_feriados_brasil(config: dict[str, Any], anos: list[int]) -> dict[str, Any]:
    """
    Preenche `feriados.por_ano` com feriados nacionais do Brasil (biblioteca `holidays`).

    Não remove feriados municipais ou entradas manuais já existentes: faz união por ano.
    """
    try:
        import holidays as lib_holidays  # type: ignore[import-untyped]
    except ImportError as erro:
        raise RuntimeError(
            "Instale o pacote «holidays» (pip install holidays) para sincronizar feriados."
        ) from erro

    cfg = garantir_config_reglas_completa(dict(config))
    feriados = cfg.setdefault("feriados", {})
    por_ano = _normalizar_feriados_por_ano(feriados.get("por_ano"))

    for ano in anos:
        ch = str(int(ano))
        br = lib_holidays.country_holidays("BR", years=int(ano))
        existentes = dict(por_ano.get(ch) or {})
        for d, nome in br.items():
            data_iso = d.isoformat()
            nome_txt = str(nome or "").strip()
            # Mantém nome manual caso já exista no JSON.
            if data_iso in existentes and str(existentes[data_iso]).strip():
                continue
            existentes[data_iso] = nome_txt
        por_ano[ch] = dict(sorted(existentes.items()))

    feriados["por_ano"] = por_ano
    feriados["ultima_sincronizacao_iso"] = datetime.now(timezone.utc).isoformat()
    feriados["fonte_sincronizacao"] = "holidays (Brasil)"
    return cfg


def conjunto_feriados_iso_para_ano(config: dict[str, Any], ano: int) -> set[str]:
    """Conjunto de datas ISO (AAAA-MM-DD) consideradas feriado naquele ano."""
    cfg = garantir_config_reglas_completa(config)
    por_ano = _normalizar_feriados_por_ano((cfg.get("feriados") or {}).get("por_ano"))
    ch = str(int(ano))
    return set((por_ano.get(ch) or {}).keys())


def nome_feriado_por_data(config: dict[str, Any], data_iso: str) -> str:
    """Nome do feriado para uma data ISO, ou vazio quando não houver."""
    if not data_iso or len(data_iso) < 10:
        return ""
    ano = data_iso[:4]
    cfg = garantir_config_reglas_completa(config)
    por_ano = _normalizar_feriados_por_ano((cfg.get("feriados") or {}).get("por_ano"))
    return str((por_ano.get(ano) or {}).get(data_iso) or "").strip()
