"""
Leitura e gravação dos ficheiros JSON por cliente e do ficheiro «último cliente».
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdo_diario.paths import ARQUIVO_ULTIMO_CLIENTE_JSON, PASTA_DADOS_RDO
from rdo_diario.schema import (
    CAMPOS_JSON_CABECALHO,
    CHAVE_JSON_CONTRATANTE,
    CHAVE_JSON_NATUREZA_SERVICO,
    criar_estrutura_documento_vazio,
    normalizar_metadados_registros_diarios,
)


def _gerar_nome_arquivo_cliente(contratante: str, natureza_servico: str) -> str:
    """
    Gera um nome de arquivo baseado em contratante e natureza do serviço.

    Converte para nome seguro: remove caracteres inválidos e usa underscore como separador.
    Exemplo: "Andritiz" + "TAF - UHE GPS - Regulador de Tensão" → "Andritiz_TAF_-_UHE_GPS_-_Regulador_de_Tensão"
    """
    # Combina contratante e natureza
    combinado = f"{contratante.strip()} - {natureza_servico.strip()}"

    # Remove caracteres inválidos em nomes de arquivo (mantém apenas letras, números, espaço, hífen e underscore)
    limpo = re.sub(r'[<>:"/\\|?*]', '', combinado)

    # Substitui espaços por underscore
    nome = limpo.replace(" ", "_")

    # Remove underscores múltiplos
    nome = re.sub(r'_+', '_', nome)

    # Remove underscore no início/fim
    nome = nome.strip("_")

    return nome


def caminho_arquivo_por_cliente(contratante: str, natureza_servico: str) -> Path:
    """
    Devolve o caminho do JSON do cliente, criando a pasta de dados se necessário.

    Nome do arquivo baseado em contratante e natureza do serviço.
    Exemplo: "Andritiz_TAF_-_UHE_GPS_-_Regulador_de_Tensão.json"
    """
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    nome_arquivo = _gerar_nome_arquivo_cliente(contratante, natureza_servico)
    return PASTA_DADOS_RDO / f"{nome_arquivo}.json"


def listar_clientes_salvos() -> list[tuple[str, str, Path]]:
    """
    Lista todos os clientes com ficheiro JSON válido (contratante, natureza, caminho).
    Ignora ficheiros cujo nome começa por «_».
    """
    if not PASTA_DADOS_RDO.is_dir():
        return []
    resultado: list[tuple[str, str, Path]] = []
    for caminho in sorted(PASTA_DADOS_RDO.glob("*.json")):
        if caminho.name.startswith("_"):
            continue
        try:
            documento = carregar_documento_json(caminho)
        except (json.JSONDecodeError, OSError):
            continue
        chave = documento.get("chave") or {}
        c = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
        n = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        if c or n:
            resultado.append((c, n, caminho))
    return resultado


def _garantir_estrutura_cabecalho(documento: dict[str, Any]) -> None:
    """
    Garante que `cabecalho_fixo` existe e tem todas as chaves esperadas; copia natureza da chave se faltar.

    Só aplica a documentos de cliente (com objeto «chave»), para não alterar outros JSON em `dados_rdo/`.
    """
    if not isinstance(documento.get("chave"), dict):
        return
    cabecalho = documento.setdefault("cabecalho_fixo", {})
    for campo in CAMPOS_JSON_CABECALHO:
        cabecalho.setdefault(campo, "")
    if not str(cabecalho.get("natureza_servico", "")).strip():
        chave = documento.get("chave") or {}
        natureza = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        if natureza:
            cabecalho["natureza_servico"] = natureza


def carregar_documento_json(caminho: Path) -> dict[str, Any]:
    """
    Lê um ficheiro JSON e normaliza a estrutura mínima do cabeçalho.
    """
    with caminho.open(encoding="utf-8") as ficheiro:
        documento = json.load(ficheiro)
    _garantir_estrutura_cabecalho(documento)
    normalizar_metadados_registros_diarios(documento)
    return documento


def salvar_documento_json(caminho: Path, documento: dict[str, Any]) -> None:
    """
    Grava o documento em disco com escrita atómica (ficheiro .tmp + replace) e atualiza `meta.ultima_edicao_iso`.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    documento = dict(documento)
    documento.setdefault("meta", {})
    documento["meta"]["ultima_edicao_iso"] = datetime.now(timezone.utc).isoformat()
    normalizar_metadados_registros_diarios(documento)
    temporario = caminho.with_suffix(".json.tmp")
    with temporario.open("w", encoding="utf-8") as ficheiro:
        json.dump(documento, ficheiro, ensure_ascii=False, indent=2)
    temporario.replace(caminho)


def carregar_ou_criar_cliente(contratante: str, natureza_servico: str) -> tuple[dict[str, Any], Path]:
    """
    Abre o JSON do cliente ou cria um novo vazio, grava-o e devolve (documento, caminho).
    """
    caminho = caminho_arquivo_por_cliente(contratante, natureza_servico)
    if caminho.is_file():
        return carregar_documento_json(caminho), caminho
    documento = criar_estrutura_documento_vazio(contratante, natureza_servico)
    documento["cabecalho_fixo"]["contratante"] = contratante.strip()
    documento["cabecalho_fixo"]["natureza_servico"] = natureza_servico.strip()
    salvar_documento_json(caminho, documento)
    return documento, caminho


def salvar_memoria_ultimo_cliente(contratante: str, natureza_servico: str) -> None:
    """
    Grava em `_ultimo_cliente.json` o par contratante + natureza para reabrir na próxima execução.
    """
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    dados = {
        CHAVE_JSON_CONTRATANTE: contratante.strip(),
        CHAVE_JSON_NATUREZA_SERVICO: natureza_servico.strip(),
    }
    with ARQUIVO_ULTIMO_CLIENTE_JSON.open("w", encoding="utf-8") as ficheiro:
        json.dump(dados, ficheiro, ensure_ascii=False, indent=2)


def ler_memoria_ultimo_cliente() -> tuple[str, str] | None:
    """
    Lê o último cliente gravado; devolve (contratante, natureza) ou None se inexistente/inválido.
    """
    if not ARQUIVO_ULTIMO_CLIENTE_JSON.is_file():
        return None
    try:
        with ARQUIVO_ULTIMO_CLIENTE_JSON.open(encoding="utf-8") as ficheiro:
            dados = json.load(ficheiro)
        c = str(dados.get(CHAVE_JSON_CONTRATANTE, "")).strip()
        n = str(dados.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        if c and n:
            return c, n
    except (json.JSONDecodeError, OSError):
        pass
    return None


def obter_documento_cliente_inicial() -> tuple[dict[str, Any], Path] | None:
    """
    Escolhe o documento a abrir ao iniciar: último cliente memorizado, senão o primeiro da lista.
    """
    ultimo = ler_memoria_ultimo_cliente()
    if ultimo:
        c, n = ultimo
        caminho = caminho_arquivo_por_cliente(c, n)
        if caminho.is_file():
            return carregar_documento_json(caminho), caminho
    clientes = listar_clientes_salvos()
    if not clientes:
        return None
    c, n, caminho = clientes[0]
    return carregar_documento_json(caminho), caminho
