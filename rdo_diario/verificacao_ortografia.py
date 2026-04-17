"""
Verificação ortográfica e gramatical via API pública gratuita do LanguageTool.

Documentação: https://languagetool.org/http-api/
Serviço público: limite de pedidos por IP (uso moderado; debounce na interface).

Os deslocamentos devolvidos pela API referem-se a caracteres Unicode na mesma
string enviada (compatível com índices de ``str`` em Python para texto em português).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

URL_API_LANGUAGETOOL = "https://api.languagetool.org/v2/check"
IDIOMA_PADRAO = "pt-BR"
TAMANHO_MAXIMO_CARACTERES = 30_000


def offset_caractere_para_indice_tk(texto: str, offset: int) -> str:
    """
    Converte posição em caracteres (0-based) na string plana para índice Tk ``line.char``.

    ``texto`` deve ser o mesmo usado na verificação (ex.: ``Text.get("1.0", "end-1c")``).
    """
    if offset < 0:
        offset = 0
    n = len(texto)
    if offset > n:
        offset = n
    prefixo = texto[:offset]
    linha = prefixo.count("\n") + 1
    ult_nl = prefixo.rfind("\n")
    coluna = offset if ult_nl == -1 else offset - ult_nl - 1
    return f"{linha}.{coluna}"


def extrair_sugestoes_do_match(match: dict[str, Any]) -> list[str]:
    """
    Extrai todas as substituições sugeridas pelo LanguageTool para um ``match``.

    Cada item de ``replacements`` na API tem normalmente a chave ``value`` com o texto corrigido.
    """
    saida: list[str] = []
    visto: set[str] = set()
    for item in match.get("replacements") or []:
        if not isinstance(item, dict):
            continue
        valor = item.get("value")
        if not isinstance(valor, str):
            continue
        valor = valor.strip()
        if not valor or valor in visto:
            continue
        visto.add(valor)
        saida.append(valor)
    return saida


def verificar_com_languagetool(texto: str, idioma: str = IDIOMA_PADRAO) -> list[dict[str, Any]]:
    """
    Envia o texto ao LanguageTool e devolve a lista ``matches`` (offset, length, message, …).

    Em falha de rede ou limite do serviço, devolve lista vazia (sem levantar exceção).
    """
    amostra = texto if len(texto) <= TAMANHO_MAXIMO_CARACTERES else texto[:TAMANHO_MAXIMO_CARACTERES]
    if not amostra.strip():
        return []

    payload = urllib.parse.urlencode(
        {
            "text": amostra,
            "language": idioma,
            "enabledOnly": "false",
        }
    ).encode("utf-8")

    requisicao = urllib.request.Request(
        URL_API_LANGUAGETOOL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ):
        return []

    return list(corpo.get("matches") or [])
