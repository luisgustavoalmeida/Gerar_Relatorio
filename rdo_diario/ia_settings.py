"""Configurações globais do assistente IA e gestão de chaves Gemini."""

from __future__ import annotations

import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from rdo_diario.paths import RAIZ_PROJETO
from rdo_diario.schema import CAMPOS_JSON_CABECALHO, ROTULOS_CABECALHO
from rdo_diario.storage import gravar_config_usuario, ler_config_usuario

CHAVE_CONFIG_IA = "assistente_ia"

MODO_ROTACAO_FIXO = "fixo"
MODO_ROTACAO_RODIZIO = "rodizio"
MODOS_ROTACAO_VALIDOS = frozenset({MODO_ROTACAO_FIXO, MODO_ROTACAO_RODIZIO})

# Campos do cabeçalho disponíveis no contexto do prompt (ordem da UI/JSON).
CAMPOS_CONTEXTO_CABECALHO: tuple[str, ...] = tuple(CAMPOS_JSON_CABECALHO)
CAMPOS_CONTEXTO_CABECALHO_PADRAO: tuple[str, ...] = (
    "natureza_servico",
)

MODELOS_GEMINI_SUGERIDOS: tuple[str, ...] = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-pro-latest",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
)

# Modelos retirados / bloqueados para contas novas → substituto
_GEMINI_MODELOS_SUBSTITUTOS: dict[str, str] = {
    "gemini-2.0-flash": "gemini-3.6-flash",
    "gemini-2.0-flash-001": "gemini-3.6-flash",
    "gemini-2.0-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.0-flash-lite-001": "gemini-3.5-flash-lite",
    "gemini-2.5-flash": "gemini-3.6-flash",
    "gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.5-pro": "gemini-3.1-pro-preview",
    "gemini-1.5-flash": "gemini-3.6-flash",
    "gemini-1.5-flash-001": "gemini-3.6-flash",
    "gemini-1.5-flash-002": "gemini-3.6-flash",
    "gemini-1.5-pro": "gemini-3.1-pro-preview",
    "gemini-1.5-pro-001": "gemini-3.1-pro-preview",
    "gemini-1.5-pro-002": "gemini-3.1-pro-preview",
    "gemini-pro": "gemini-3.6-flash",
    "gemini-pro-vision": "gemini-3.6-flash",
}

# No .exe e em desenvolvimento: chaves sempre em template/.env.
ARQUIVO_ENV = RAIZ_PROJETO / "template" / ".env"
# Compatibilidade: instalações antigas com .env na raiz / ao lado do .exe.
ARQUIVO_ENV_LEGADO = RAIZ_PROJETO / ".env"
ARQUIVO_CHAVE_LOCAL = RAIZ_PROJETO / "Chave api IA google.txt"
ENV_GEMINI_API_KEYS = "GEMINI_API_KEYS"
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
ENV_GOOGLE_API_KEY = "GOOGLE_API_KEY"
_SEPARADOR_CHAVES = "|"
_COOLDOWN_PADRAO_SEGUNDOS = 60.0

_PROMPT_PADRAO = (
    "Aja como engenheiro responsável pela redação do relatório diário de atividades. "
    "Reescreva o rascunho em português do Brasil, com texto claro, rico em informação e "
    "apresentável para cliente/fiscalização. Use linguagem técnica profissional, objetiva "
    "e cronológica. Preserve siglas, equipamentos, locais, medições e fatos informados. "
    "Não invente atividades, causas, resultados, datas, quantitativos ou materiais. "
    "Se o rascunho estiver em tópicos ou frases curtas, organize em parágrafos naturais. "
    "Retorne apenas o texto final, sem título, sem markdown e sem comentários extras."
)


def _prompt_padrao() -> dict[str, str]:
    return {
        "id": uuid4().hex,
        "nome": "Reescrita técnica padrão",
        "texto": _PROMPT_PADRAO,
    }


_CONFIG_PADRAO: dict[str, Any] = {
    "modelo": MODELOS_GEMINI_SUGERIDOS[0],
    "modo_rotacao": MODO_ROTACAO_FIXO,
    "indice_chave_ativa": 0,
    "indice_rodizio_proximo": 0,
    "dias_historico": 3,
    "minimo_caracteres_historico": 0,
    "remover_primeiro_paragrafo": False,
    "remover_ultimo_paragrafo": False,
    "campos_contexto_cabecalho": list(CAMPOS_CONTEXTO_CABECALHO_PADRAO),
    "prompt_selecionado_id": "",
    "prompts": [_prompt_padrao()],
}

_rr_lock = threading.Lock()
_rr_index = 0
_cooldown_por_chave: dict[str, float] = {}


def _copiar_config_padrao() -> dict[str, Any]:
    return deepcopy(_CONFIG_PADRAO)


def _extrair_chaves_de_texto(texto: str) -> list[str]:
    chaves: list[str] = []
    bruto = (texto or "").replace("\r", "\n").replace(",", _SEPARADOR_CHAVES)
    for parte in bruto.replace("\n", _SEPARADOR_CHAVES).split(_SEPARADOR_CHAVES):
        chave = parte.strip()
        if chave and chave not in chaves:
            chaves.append(chave)
    return chaves


def _desquotar_valor_env(valor: str) -> str:
    texto = valor.strip()
    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in {'"', "'"}:
        return texto[1:-1]
    return texto


def _formatar_valor_env(valor: str) -> str:
    """Aspas + quebras de linha quando o valor tiver múltiplas chaves/linhas."""
    if "\n" in valor or valor.startswith((" ", "\t")) or valor.endswith((" ", "\t")):
        escapado = valor.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escapado}"'
    return valor


def _migrar_env_legado_para_template() -> None:
    """Se só existir .env na raiz, copia para template/.env (local canónico)."""
    if ARQUIVO_ENV.is_file() or not ARQUIVO_ENV_LEGADO.is_file():
        return
    try:
        ARQUIVO_ENV.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_ENV.write_bytes(ARQUIVO_ENV_LEGADO.read_bytes())
    except OSError:
        return


def _caminho_env_leitura() -> Path | None:
    """Sempre template/.env; migra .env legado da raiz se necessário."""
    _migrar_env_legado_para_template()
    if ARQUIVO_ENV.is_file():
        return ARQUIVO_ENV
    if ARQUIVO_ENV_LEGADO.is_file():
        return ARQUIVO_ENV_LEGADO
    return None


def _ler_env() -> dict[str, str]:
    dados: dict[str, str] = {}
    caminho = _caminho_env_leitura()
    if caminho is None:
        return dados
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError:
        return dados

    linhas = texto.splitlines()
    indice = 0
    while indice < len(linhas):
        bruto = linhas[indice].strip()
        indice += 1
        if not bruto or bruto.startswith("#") or "=" not in bruto:
            continue
        chave, _, valor = bruto.partition("=")
        chave = chave.strip()
        valor = valor.strip()
        aspas = valor[:1] if valor[:1] in {'"', "'"} else ""
        if aspas and not (valor.endswith(aspas) and len(valor) >= 2):
            partes = [valor[1:]]
            while indice < len(linhas):
                linha = linhas[indice]
                indice += 1
                if linha.rstrip().endswith(aspas):
                    partes.append(linha.rstrip()[:-1])
                    break
                partes.append(linha)
            valor = "\n".join(partes)
        else:
            valor = _desquotar_valor_env(valor)
        dados[chave] = valor
    return dados


def _escrever_env(atualizacoes: dict[str, str | None]) -> None:
    """Atualiza chaves em template/.env preservando comentários e entradas não alteradas."""
    _migrar_env_legado_para_template()
    linhas_atuais: list[str] = []
    if ARQUIVO_ENV.is_file():
        try:
            linhas_atuais = ARQUIVO_ENV.read_text(encoding="utf-8").splitlines()
        except OSError:
            linhas_atuais = []
    elif ARQUIVO_ENV_LEGADO.is_file():
        try:
            linhas_atuais = ARQUIVO_ENV_LEGADO.read_text(encoding="utf-8").splitlines()
        except OSError:
            linhas_atuais = []

    vistas: set[str] = set()
    novas_linhas: list[str] = []
    indice = 0
    while indice < len(linhas_atuais):
        linha = linhas_atuais[indice]
        bruto = linha.strip()
        indice += 1
        if not bruto or bruto.startswith("#") or "=" not in bruto:
            novas_linhas.append(linha)
            continue

        chave = bruto.split("=", 1)[0].strip()
        valor_bruto = bruto.split("=", 1)[1].strip()
        aspas = valor_bruto[:1] if valor_bruto[:1] in {'"', "'"} else ""
        bloco = [linha]
        if aspas and not (valor_bruto.endswith(aspas) and len(valor_bruto) >= 2):
            while indice < len(linhas_atuais):
                cont = linhas_atuais[indice]
                indice += 1
                bloco.append(cont)
                if cont.rstrip().endswith(aspas):
                    break

        if chave in atualizacoes:
            vistas.add(chave)
            valor = atualizacoes[chave]
            if valor is None:
                continue
            novas_linhas.append(f"{chave}={_formatar_valor_env(valor)}")
            continue
        novas_linhas.extend(bloco)

    for chave, valor in atualizacoes.items():
        if chave in vistas or valor is None:
            continue
        novas_linhas.append(f"{chave}={_formatar_valor_env(valor)}")

    ARQUIVO_ENV.parent.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO_ENV.with_suffix(".env.tmp")
    texto_final = "\n".join(novas_linhas).rstrip()
    temporario.write_text((texto_final + "\n") if texto_final else "", encoding="utf-8")
    temporario.replace(ARQUIVO_ENV)

    for chave, valor in atualizacoes.items():
        if valor is None:
            os.environ.pop(chave, None)
        else:
            os.environ[chave] = valor


def _campos_contexto_cabecalho_normalizados(valor: Any) -> list[str]:
    permitidos = set(CAMPOS_CONTEXTO_CABECALHO)
    escolhidos: list[str] = []
    if isinstance(valor, list):
        for item in valor:
            campo = str(item or "").strip()
            if campo in permitidos and campo not in escolhidos:
                escolhidos.append(campo)
    # Mantém a ordem canônica do cabeçalho.
    return [campo for campo in CAMPOS_CONTEXTO_CABECALHO if campo in escolhidos]


def rotulo_campo_contexto_cabecalho(campo: str) -> str:
    return str(ROTULOS_CABECALHO.get(campo) or campo)


def _prompts_normalizados(valor: Any) -> list[dict[str, str]]:
    prompts: list[dict[str, str]] = []
    if isinstance(valor, list):
        for item in valor:
            if not isinstance(item, dict):
                continue
            texto = str(item.get("texto") or "").strip()
            if not texto:
                continue
            nome = str(item.get("nome") or "Prompt sem nome").strip() or "Prompt sem nome"
            prompts.append(
                {
                    "id": str(item.get("id") or uuid4().hex).strip() or uuid4().hex,
                    "nome": nome,
                    "texto": texto,
                }
            )
    if prompts:
        return prompts
    return [_prompt_padrao()]


def _normalizar_config(config: dict[str, Any] | None) -> dict[str, Any]:
    base = _copiar_config_padrao()
    origem = config if isinstance(config, dict) else {}

    modelo = str(origem.get("modelo") or base["modelo"]).strip() or base["modelo"]
    if modelo.startswith("models/"):
        modelo = modelo[len("models/") :]
    modelo = _GEMINI_MODELOS_SUBSTITUTOS.get(modelo, modelo)
    modo = str(origem.get("modo_rotacao") or base["modo_rotacao"]).strip().lower()
    if modo not in MODOS_ROTACAO_VALIDOS:
        modo = base["modo_rotacao"]
    try:
        dias = max(0, int(origem.get("dias_historico", base["dias_historico"])))
    except (TypeError, ValueError):
        dias = int(base["dias_historico"])
    try:
        minimo_caracteres = max(
            0, int(origem.get("minimo_caracteres_historico", base["minimo_caracteres_historico"]))
        )
    except (TypeError, ValueError):
        minimo_caracteres = int(base["minimo_caracteres_historico"])
    try:
        indice = max(0, int(origem.get("indice_chave_ativa", base["indice_chave_ativa"])))
    except (TypeError, ValueError):
        indice = int(base["indice_chave_ativa"])
    try:
        indice_rodizio = max(0, int(origem.get("indice_rodizio_proximo", base["indice_rodizio_proximo"])))
    except (TypeError, ValueError):
        indice_rodizio = int(base["indice_rodizio_proximo"])

    prompts = _prompts_normalizados(origem.get("prompts"))
    prompt_ids = {item["id"] for item in prompts}
    prompt_selecionado_id = str(origem.get("prompt_selecionado_id") or "").strip()
    if prompt_selecionado_id not in prompt_ids:
        prompt_selecionado_id = prompts[0]["id"]

    return {
        "modelo": modelo,
        "modo_rotacao": modo,
        "indice_chave_ativa": indice,
        "indice_rodizio_proximo": indice_rodizio,
        "dias_historico": dias,
        "minimo_caracteres_historico": minimo_caracteres,
        "remover_primeiro_paragrafo": bool(origem.get("remover_primeiro_paragrafo")),
        "remover_ultimo_paragrafo": bool(origem.get("remover_ultimo_paragrafo")),
        "campos_contexto_cabecalho": _campos_contexto_cabecalho_normalizados(
            origem.get("campos_contexto_cabecalho", base["campos_contexto_cabecalho"])
        ),
        "prompt_selecionado_id": prompt_selecionado_id,
        "prompts": prompts,
    }


def carregar_config_ia() -> dict[str, Any]:
    dados = ler_config_usuario()
    bloco = dados.get(CHAVE_CONFIG_IA) if isinstance(dados, dict) else {}
    return _normalizar_config(bloco if isinstance(bloco, dict) else {})


def salvar_config_ia(config: dict[str, Any]) -> dict[str, Any]:
    mesclado = carregar_config_ia()
    if isinstance(config, dict):
        mesclado.update(config)
    normalizado = _normalizar_config(mesclado)
    dados = ler_config_usuario()
    dados[CHAVE_CONFIG_IA] = normalizado
    gravar_config_usuario(dados)
    return normalizado


def obter_prompt_selecionado(config: dict[str, Any] | None = None) -> dict[str, str]:
    cfg = config or carregar_config_ia()
    prompts = _prompts_normalizados(cfg.get("prompts"))
    selecionado = str(cfg.get("prompt_selecionado_id") or "").strip()
    for item in prompts:
        if item["id"] == selecionado:
            return item
    return prompts[0]


def listar_chaves_gemini() -> list[str]:
    env = _ler_env()
    chaves: list[str] = []
    for origem in (
        env.get(ENV_GEMINI_API_KEYS, ""),
        env.get(ENV_GEMINI_API_KEY, ""),
        env.get(ENV_GOOGLE_API_KEY, ""),
        os.getenv(ENV_GEMINI_API_KEYS, ""),
        os.getenv(ENV_GEMINI_API_KEY, ""),
        os.getenv(ENV_GOOGLE_API_KEY, ""),
    ):
        for chave in _extrair_chaves_de_texto(str(origem or "")):
            if chave not in chaves:
                chaves.append(chave)

    if ARQUIVO_CHAVE_LOCAL.is_file():
        try:
            texto_local = ARQUIVO_CHAVE_LOCAL.read_text(encoding="utf-8")
        except OSError:
            texto_local = ""
        for chave in _extrair_chaves_de_texto(texto_local):
            if chave not in chaves:
                chaves.append(chave)
    return chaves


def _listar_chaves_somente_env() -> list[str]:
    """Chaves persistidas no .env (sem arquivo local auxiliar)."""
    env = _ler_env()
    chaves: list[str] = []
    for origem in (
        env.get(ENV_GEMINI_API_KEYS, ""),
        env.get(ENV_GEMINI_API_KEY, ""),
        env.get(ENV_GOOGLE_API_KEY, ""),
    ):
        for chave in _extrair_chaves_de_texto(str(origem or "")):
            if chave not in chaves:
                chaves.append(chave)
    return chaves


def salvar_chaves_gemini(chaves: list[str]) -> list[str]:
    anteriores = _listar_chaves_somente_env()
    limpas = _extrair_chaves_de_texto("\n".join(chaves))
    if limpas:
        # Uma chave por linha no .env (entre aspas). Só GEMINI_API_KEYS — sem variável singular.
        _escrever_env(
            {
                ENV_GEMINI_API_KEYS: "\n".join(limpas),
                ENV_GEMINI_API_KEY: None,
                ENV_GOOGLE_API_KEY: None,
            }
        )
    else:
        _escrever_env(
            {
                ENV_GEMINI_API_KEYS: None,
                ENV_GEMINI_API_KEY: None,
                ENV_GOOGLE_API_KEY: None,
            }
        )
    if limpas != anteriores:
        redefinir_rotacao_gemini()
    return limpas


def mascarar_chave(chave: str) -> str:
    texto = (chave or "").strip()
    if not texto:
        return ""
    if len(texto) <= 8:
        return "*" * len(texto)
    return texto[:4] + "..." + texto[-4:]


def nome_arquivo_importacao_chaves() -> str:
    return ARQUIVO_CHAVE_LOCAL.name


def _persistir_indice_rodizio_proximo(indice: int) -> None:
    """Grava o próximo índice do rodízio para continuar após fechar o app."""
    indice_norm = max(0, int(indice))
    global _rr_index
    with _rr_lock:
        _rr_index = indice_norm
    dados = ler_config_usuario()
    bloco = dados.get(CHAVE_CONFIG_IA) if isinstance(dados, dict) else {}
    if not isinstance(bloco, dict):
        bloco = {}
    if int(bloco.get("indice_rodizio_proximo") or 0) == indice_norm:
        return
    bloco = _normalizar_config(bloco)
    bloco["indice_rodizio_proximo"] = indice_norm
    dados[CHAVE_CONFIG_IA] = bloco
    gravar_config_usuario(dados)


def _indice_rodizio_persistido() -> int:
    cfg = carregar_config_ia()
    try:
        return max(0, int(cfg.get("indice_rodizio_proximo") or 0))
    except (TypeError, ValueError):
        return 0


def redefinir_rotacao_gemini() -> None:
    global _rr_index
    chaves = set(listar_chaves_gemini())
    with _rr_lock:
        _rr_index = 0
        for chave in list(_cooldown_por_chave.keys()):
            if chave not in chaves:
                _cooldown_por_chave.pop(chave, None)
    _persistir_indice_rodizio_proximo(0)


def _cooldown_ativo(chave: str, agora: float) -> bool:
    ate = _cooldown_por_chave.get(chave, 0.0)
    if ate <= agora:
        _cooldown_por_chave.pop(chave, None)
        return False
    return True


def marcar_cooldown_chave_gemini(chave: str, segundos: float | None = None) -> None:
    if not chave:
        return
    with _rr_lock:
        _cooldown_por_chave[chave] = time.time() + (
            segundos if segundos is not None else _COOLDOWN_PADRAO_SEGUNDOS
        )


def obter_ordem_chaves_para_interacao(config: dict[str, Any] | None = None) -> list[tuple[int, str]]:
    cfg = config or carregar_config_ia()
    chaves = listar_chaves_gemini()
    if not chaves:
        return []
    total = len(chaves)
    agora = time.time()
    modo_rodizio = str(cfg.get("modo_rotacao") or MODO_ROTACAO_FIXO) == MODO_ROTACAO_RODIZIO
    proximo: int | None = None
    if modo_rodizio:
        inicio = _indice_rodizio_persistido() % total
        proximo = (inicio + 1) % total
    else:
        inicio = int(cfg.get("indice_chave_ativa") or 0) % total
    with _rr_lock:
        global _rr_index
        if modo_rodizio and proximo is not None:
            _rr_index = proximo
        indices = [(inicio + deslocamento) % total for deslocamento in range(total)]
        disponiveis = [idx for idx in indices if not _cooldown_ativo(chaves[idx], agora)]
        finais = disponiveis or indices
    if modo_rodizio and proximo is not None:
        _persistir_indice_rodizio_proximo(proximo)
    return [(idx, chaves[idx]) for idx in finais]
