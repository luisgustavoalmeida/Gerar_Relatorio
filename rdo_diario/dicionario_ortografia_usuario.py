"""
Dicionário pessoal de palavras e siglas para filtrar avisos do LanguageTool.

A API pública gratuita não integra dicionários customizados; guardamos entradas
localmente e ignoramos correspondências cujo trecho coincide (sem diferenciar maiúsculas).
"""

from __future__ import annotations

import json
from rdo_diario.paths import ARQUIVO_DICIONARIO_ORTOGRAFIA_JSON, PASTA_DADOS_RDO


def carregar_lista() -> list[str]:
    """Devolve a lista de entradas guardadas (ordem arbitrária)."""
    if not ARQUIVO_DICIONARIO_ORTOGRAFIA_JSON.is_file():
        return []
    try:
        with ARQUIVO_DICIONARIO_ORTOGRAFIA_JSON.open(encoding="utf-8") as ficheiro:
            dados = json.load(ficheiro)
    except (json.JSONDecodeError, OSError):
        return []
    palavras = dados.get("palavras")
    if not isinstance(palavras, list):
        return []
    return [str(p).strip() for p in palavras if str(p).strip()]


def salvar_lista(itens: list[str]) -> None:
    """Grava lista única (comparação sem distinção de maiúsculas), ordenada alfabeticamente."""
    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    unicos: list[str] = []
    visto: set[str] = set()
    for p in itens:
        p = str(p).strip()
        if not p:
            continue
        ch = p.casefold()
        if ch in visto:
            continue
        visto.add(ch)
        unicos.append(p)
    unicos.sort(key=str.casefold)
    with ARQUIVO_DICIONARIO_ORTOGRAFIA_JSON.open("w", encoding="utf-8") as ficheiro:
        json.dump({"palavras": unicos}, ficheiro, ensure_ascii=False, indent=2)


def conjunto_para_filtragem() -> set[str]:
    """Conjunto de chaves em minúsculas para testar trechos devolvidos pelo corretor."""
    return {p.casefold() for p in carregar_lista()}


def trecho_deve_ser_ignorado(
    texto_plano: str,
    offset: int,
    length: int,
    conjunto_casefold: set[str],
) -> bool:
    """
    Indica se o trecho ``texto_plano[offset:offset+length]`` está no dicionário pessoal.
    """
    if offset < 0 or length <= 0 or offset + length > len(texto_plano):
        return False
    trecho = texto_plano[offset : offset + length]
    chave = trecho.casefold().strip()
    if not chave:
        return False
    return chave in conjunto_casefold


def adicionar_palavra(palavra: str) -> bool:
    """
    Acrescenta uma entrada ao ficheiro se ainda não existir (ignora maiúsculas).

    Devolve True se foi acrescentada, False se estava duplicada ou vazia.
    """
    p = palavra.strip()
    if not p:
        return False
    lista = carregar_lista()
    chaves = {x.casefold() for x in lista}
    if p.casefold() in chaves:
        return False
    lista.append(p)
    salvar_lista(lista)
    return True
