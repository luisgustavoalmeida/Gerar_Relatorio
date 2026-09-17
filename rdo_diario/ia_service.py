"""Serviço de reescrita de relatórios diários com Google Gemini."""

from __future__ import annotations

import hashlib
import threading
import time
from datetime import date
from typing import Any

from rdo_diario.ia_settings import (
    MODELOS_GEMINI_SUGERIDOS,
    carregar_config_ia,
    listar_chaves_gemini,
    marcar_cooldown_chave_gemini,
    mascarar_chave,
    obter_ordem_chaves_para_interacao,
    obter_prompt_selecionado,
    rotulo_campo_contexto_cabecalho,
)

_GEMINI_EXCLUIR_SUBSTR = (
    "tts",
    "image",
    "embedding",
    "lyria",
    "robotics",
    "computer-use",
    "deep-research",
    "antigravity",
    "transcribe",
    "customtools",
    "omni",
    "live",
)

_GEMINI_MODELS_TTL = 30 * 60
_gemini_models_cache: dict[str, tuple[float, list[str]]] = {}
_gemini_models_lock = threading.Lock()


class ErroAssistenteIa(RuntimeError):
    """Erro amigável para a camada de interface."""

    def __init__(self, mensagem: str, *, offline: bool = False) -> None:
        super().__init__(mensagem)
        self.offline = offline


def _cliente_gemini(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def _nome_modelo_limpo(nome: str) -> str:
    texto = (nome or "").strip()
    if texto.startswith("models/"):
        return texto[len("models/") :]
    return texto


def _modelo_util_para_reescrita(model_id: str) -> bool:
    m = _nome_modelo_limpo(model_id).lower()
    if not m.startswith("gemini-"):
        return False
    if m.startswith("gemini-2.") or m.startswith("gemini-1."):
        return False
    return not any(trecho in m for trecho in _GEMINI_EXCLUIR_SUBSTR)


def _ordenar_modelos_gemini(ids: list[str]) -> list[str]:
    preferencia = list(MODELOS_GEMINI_SUGERIDOS)
    rank = {mid: indice for indice, mid in enumerate(preferencia)}

    def chave(mid: str) -> tuple[int, str]:
        return (rank.get(mid, 1000), mid)

    return sorted(ids, key=chave)


def listar_modelos_gemini(api_key: str) -> tuple[list[str], str | None]:
    """Consulta ``models.list`` e devolve IDs úteis para reescrita de texto.

    Retorna ``(lista, erro_ou_None)``. Em falha, ``lista`` fica vazia.
    """
    key = (api_key or "").strip()
    if not key:
        return [], "Informe a chave Gemini para listar os modelos."

    cache_key = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    agora = time.time()
    with _gemini_models_lock:
        hit = _gemini_models_cache.get(cache_key)
        if hit and agora - hit[0] < _GEMINI_MODELS_TTL and hit[1]:
            return hit[1], None

    try:
        client = _cliente_gemini(key)
        encontrados: list[str] = []
        for modelo in client.models.list():
            nome = _nome_modelo_limpo(str(getattr(modelo, "name", "") or ""))
            if not nome:
                continue
            actions = (
                getattr(modelo, "supported_actions", None)
                or getattr(modelo, "supported_generation_methods", None)
                or []
            )
            actions_l = {str(a).lower().replace("_", "") for a in actions}
            if actions_l and "generatecontent" not in actions_l:
                continue
            if _modelo_util_para_reescrita(nome):
                encontrados.append(nome)
        unicos = list(dict.fromkeys(encontrados))
        ordenados = _ordenar_modelos_gemini(unicos)
        if not ordenados:
            return [], "A API não retornou modelos de texto compatíveis com a reescrita."
        with _gemini_models_lock:
            _gemini_models_cache[cache_key] = (time.time(), ordenados)
        return ordenados, None
    except Exception as exc:
        return [], f"Não foi possível listar modelos: {exc}"


def testar_modelo_gemini(api_key: str, modelo: str) -> tuple[bool, str]:
    """Chamada mínima de ``generateContent`` para validar chave + modelo."""
    key = (api_key or "").strip()
    model_name = _nome_modelo_limpo(modelo)
    if not key:
        return False, "Informe ao menos uma chave Gemini antes de testar."
    if not model_name:
        return False, "Selecione um modelo Gemini para testar."

    try:
        client = _cliente_gemini(key)
        resposta = client.models.generate_content(
            model=model_name,
            contents="Responda apenas com a palavra OK.",
        )
        texto = _extrair_texto_resposta(resposta).strip()
        if not texto:
            return False, f"O modelo «{model_name}» respondeu vazio."
        amostra = texto.replace("\n", " ")
        if len(amostra) > 120:
            amostra = amostra[:117] + "…"
        return True, f"Modelo «{model_name}» OK com a chave {mascarar_chave(key)}.\nResposta: {amostra}"
    except Exception as exc:
        mensagem = str(exc).strip() or type(exc).__name__
        if len(mensagem) > 400:
            mensagem = mensagem[:397] + "…"
        low = mensagem.lower()
        dica = ""
        if "high demand" in low or "try again later" in low:
            dica = "\n\nAlta demanda temporária nesse modelo. Tente outro Flash ou aguarde alguns minutos."
        elif "429" in mensagem or "quota" in low or "rate" in low:
            dica = "\n\nCota/limite da chave. Aguarde, troque de chave ou escolha outro modelo."
        elif "404" in mensagem or "no longer available" in low or "not found" in low:
            dica = "\n\nModelo indisponível para esta conta. Atualize a lista pela API e escolha outro."
        return False, f"Falha no teste de «{model_name}»:\n{mensagem}{dica}"


def _extrair_texto_resposta(resposta: Any) -> str:
    texto = getattr(resposta, "text", None)
    if texto:
        return str(texto).strip()

    candidatos = getattr(resposta, "candidates", None) or []
    partes: list[str] = []
    for candidato in candidatos:
        conteudo = getattr(candidato, "content", None)
        blocos = getattr(conteudo, "parts", None) or []
        for bloco in blocos:
            valor = getattr(bloco, "text", None)
            if valor:
                partes.append(str(valor))
    return "\n".join(parte.strip() for parte in partes if str(parte).strip()).strip()


def _texto_sem_blocos_markdown(texto: str) -> str:
    bruto = (texto or "").strip()
    if bruto.startswith("```") and bruto.endswith("```"):
        linhas = bruto.splitlines()
        if len(linhas) >= 2:
            return "\n".join(linhas[1:-1]).strip()
    return bruto


def _paragrafos(texto: str) -> list[str]:
    normalizado = str(texto or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalizado:
        return []
    if "\n\n" in normalizado:
        return [bloco.strip() for bloco in normalizado.split("\n\n") if bloco.strip()]
    # Sem linhas em branco: trata cada linha não vazia como parágrafo lógico
    # (comum em rascunhos/relatórios curtos).
    linhas = [linha.strip() for linha in normalizado.split("\n") if linha.strip()]
    return linhas if len(linhas) > 1 else [normalizado]


def _aplicar_filtro_paragrafos(
    texto: str,
    *,
    remover_primeiro: bool,
    remover_ultimo: bool,
) -> str:
    paragrafos = _paragrafos(texto)
    if remover_primeiro and paragrafos:
        paragrafos = paragrafos[1:]
    if remover_ultimo and paragrafos:
        paragrafos = paragrafos[:-1]
    return "\n\n".join(paragrafos).strip()


def _coletar_historico_aprovado(
    documento: dict[str, Any],
    data_referencia: date,
    *,
    dias_historico: int,
    remover_primeiro_paragrafo: bool,
    remover_ultimo_paragrafo: bool,
    minimo_caracteres: int = 0,
) -> list[dict[str, str]]:
    if dias_historico <= 0:
        return []

    registros = documento.get("registros_diarios")
    if not isinstance(registros, dict):
        return []

    minimo = max(0, int(minimo_caracteres or 0))
    historico: list[tuple[date, str]] = []
    for iso, registro in registros.items():
        if not isinstance(registro, dict):
            continue
        try:
            data_registro = date.fromisoformat(str(iso).strip()[:10])
        except ValueError:
            continue
        if data_registro >= data_referencia:
            continue
        texto = str(registro.get("registro_servico") or "").strip()
        if not texto:
            continue
        texto = _aplicar_filtro_paragrafos(
            texto,
            remover_primeiro=remover_primeiro_paragrafo,
            remover_ultimo=remover_ultimo_paragrafo,
        )
        if not texto:
            continue
        if minimo > 0 and len(texto) < minimo:
            continue
        historico.append((data_registro, texto))

    historico.sort(key=lambda item: item[0])
    selecionados = historico[-dias_historico:]
    return [
        {
            "data": item[0].isoformat(),
            "texto": item[1],
        }
        for item in selecionados
    ]


def _resumo_projeto(documento: dict[str, Any], config: dict[str, Any] | None = None) -> str:
    cfg = config or {}
    campos = cfg.get("campos_contexto_cabecalho")
    if not isinstance(campos, list):
        campos = []
    if not campos:
        return "- (nenhum campo de cabeçalho selecionado no contexto)"

    cabecalho = documento.get("cabecalho_fixo") if isinstance(documento.get("cabecalho_fixo"), dict) else {}
    chave = documento.get("chave") if isinstance(documento.get("chave"), dict) else {}
    linhas: list[str] = []
    for campo in campos:
        campo_id = str(campo or "").strip()
        if not campo_id:
            continue
        valor = cabecalho.get(campo_id)
        if campo_id in {"contratante", "natureza_servico"} and not str(valor or "").strip():
            valor = chave.get(campo_id)
        texto = str(valor or "").strip()
        if not texto:
            continue
        rotulo = rotulo_campo_contexto_cabecalho(campo_id)
        linhas.append(f"- {rotulo}: {texto}")
    return "\n".join(linhas).strip() or "- Projeto sem detalhes preenchidos nos campos selecionados."


def _montar_prompt_reescrita(
    documento: dict[str, Any],
    data_referencia: date,
    rascunho: str,
    config: dict[str, Any],
    historico: list[dict[str, str]],
) -> str:
    prompt_usuario = obter_prompt_selecionado(config)
    if historico:
        blocos_historico = [
            f"[{item['data']}]\n{item['texto']}" for item in historico if item.get("texto")
        ]
        texto_historico = "\n\n".join(blocos_historico)
    else:
        texto_historico = "(nenhum dia anterior selecionado)"

    return (
        f"{prompt_usuario['texto'].strip()}\n\n"
        "Contexto do projeto:\n"
        f"{_resumo_projeto(documento, config)}\n\n"
        f"Data do relatório em reescrita: {data_referencia.strftime('%d/%m/%Y')}\n\n"
        f"Histórico aprovado considerado ({len(historico)} dia(s)):\n"
        f"{texto_historico}\n\n"
        "Rascunho do dia:\n"
        f"{rascunho.strip()}\n"
    )


# Envelope fixo antigo (pré-1.0.7): bloco de sistema + «Orientações adicionais do engenheiro:».
# Não usar a primeira frase isolada — o prompt de fábrica actual começa com o mesmo texto.
_MARCA_PROMPT_SISTEMA_OBSOLETO = "Orientações adicionais do engenheiro:"


def prompt_enviado_e_obsoleto(texto: str) -> bool:
    """Detecta o envelope fixo antigo (já removido do envio à API)."""
    return _MARCA_PROMPT_SISTEMA_OBSOLETO in str(texto or "")


def montar_prompt_reescrita_diario(
    documento: dict[str, Any],
    data_referencia: date,
    rascunho: str,
    *,
    config: dict[str, Any] | None = None,
) -> str:
    """Monta o prompt exatamente como será enviado na próxima reescrita."""
    cfg = config or carregar_config_ia()
    historico = _coletar_historico_aprovado(
        documento,
        data_referencia,
        dias_historico=int(cfg.get("dias_historico") or 0),
        remover_primeiro_paragrafo=bool(cfg.get("remover_primeiro_paragrafo")),
        remover_ultimo_paragrafo=bool(cfg.get("remover_ultimo_paragrafo")),
        minimo_caracteres=int(cfg.get("minimo_caracteres_historico") or 0),
    )
    return _montar_prompt_reescrita(
        documento,
        data_referencia,
        str(rascunho or "").strip(),
        cfg,
        historico,
    )


def _erro_indica_quota(exc: BaseException) -> bool:
    texto = str(exc).lower()
    return any(
        trecho in texto
        for trecho in ("429", "quota", "rate limit", "rate_limit", "resource_exhausted", "too many requests")
    )


def _erro_indica_offline(exc: BaseException) -> bool:
    texto = str(exc).lower()
    return any(
        trecho in texto
        for trecho in (
            "connection",
            "network",
            "timed out",
            "timeout",
            "dns",
            "ssl",
            "unreachable",
            "socket",
            "name resolution",
        )
    )


def reescrever_rascunho_diario(
    documento: dict[str, Any],
    data_referencia: date,
    rascunho: str,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    texto_rascunho = str(rascunho or "").strip()
    if not texto_rascunho:
        raise ErroAssistenteIa("Escreva um rascunho do dia antes de pedir a reescrita.")

    cfg = config or carregar_config_ia()
    chaves = listar_chaves_gemini()
    if not chaves:
        raise ErroAssistenteIa(
            "Nenhuma chave Gemini foi configurada. Abra IA -> Configurações Gemini para informar as chaves."
        )

    modelo = str(cfg.get("modelo") or "").strip()
    if not modelo:
        raise ErroAssistenteIa("Defina um modelo Gemini nas configurações da IA.")

    historico = _coletar_historico_aprovado(
        documento,
        data_referencia,
        dias_historico=int(cfg.get("dias_historico") or 0),
        remover_primeiro_paragrafo=bool(cfg.get("remover_primeiro_paragrafo")),
        remover_ultimo_paragrafo=bool(cfg.get("remover_ultimo_paragrafo")),
        minimo_caracteres=int(cfg.get("minimo_caracteres_historico") or 0),
    )
    prompt = _montar_prompt_reescrita(documento, data_referencia, texto_rascunho, cfg, historico)

    erros: list[str] = []
    ordem_chaves = obter_ordem_chaves_para_interacao(cfg)
    if not ordem_chaves:
        raise ErroAssistenteIa("Nenhuma chave Gemini válida foi encontrada.")

    for _indice, chave in ordem_chaves:
        try:
            cliente = _cliente_gemini(chave)
            resposta = cliente.models.generate_content(
                model=modelo,
                contents=prompt,
            )
            texto = _texto_sem_blocos_markdown(_extrair_texto_resposta(resposta))
            if not texto:
                erros.append(f"{mascarar_chave(chave)}: resposta vazia")
                continue
            prompt_selecionado = obter_prompt_selecionado(cfg)
            return {
                "texto_reescrito": texto,
                "historico": historico,
                "historico_usado": len(historico),
                "modelo": modelo,
                "prompt_id": prompt_selecionado["id"],
                "prompt_nome": prompt_selecionado["nome"],
                "prompt_enviado": prompt,
                "chave_mascarada": mascarar_chave(chave),
            }
        except ErroAssistenteIa:
            raise
        except Exception as exc:
            if _erro_indica_quota(exc):
                marcar_cooldown_chave_gemini(chave)
            offline = _erro_indica_offline(exc)
            erros.append(f"{mascarar_chave(chave)}: {exc}")
            if offline:
                raise ErroAssistenteIa(
                    "Sem conexão com o Gemini no momento. O rascunho continua salvo localmente para tentar novamente depois.",
                    offline=True,
                ) from exc
            continue

    detalhe = "\n".join(erros[:4]).strip()
    mensagem = "Não foi possível obter uma reescrita do Gemini."
    if detalhe:
        mensagem += f"\n\nTentativas:\n{detalhe}"
    raise ErroAssistenteIa(mensagem)
