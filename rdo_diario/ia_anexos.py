"""Anexos de contexto do Assistente IA (Gemini Files API), por projeto."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from rdo_diario.paths import PASTA_ANEXOS_IA, RAIZ_PROJETO
from rdo_diario.schema import (
    CHAVE_JSON_CONTRATANTE,
    CHAVE_JSON_IA_CONTEXTO_ARQUIVOS,
    CHAVE_JSON_NATUREZA_SERVICO,
)

# Margem antes da expiração oficial (~48 h) para forçar reenvio.
_MARGEM_EXPIRACAO_SEGUNDOS = 3600
_TAMANHO_MAX_PDF_BYTES = 50 * 1024 * 1024
_TAMANHO_MAX_GERAL_BYTES = 100 * 1024 * 1024
_TIMEOUT_PROCESSAMENTO_SEGUNDOS = 120.0
MAX_ANEXOS_POR_PROJETO = 10
MAX_ANEXOS_ACTIVOS_ENVIO = 8

# MIME suportados pela Gemini API (plano gratuito / Files API).
MIME_TIPOS_SUPORTADOS: frozenset[str] = frozenset(
    {
        # Documentos
        "application/pdf",
        "text/plain",
        "text/html",
        "text/css",
        "text/csv",
        "text/xml",
        "text/rtf",
        "application/rtf",
        "application/json",
        # Imagens
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/heic",
        "image/heif",
        "image/gif",
        "image/bmp",
        # Áudio
        "audio/wav",
        "audio/mp3",
        "audio/mpeg",
        "audio/aiff",
        "audio/aac",
        "audio/ogg",
        "audio/flac",
        "audio/m4a",
        "audio/mp4",
        "audio/webm",
        "audio/opus",
        "audio/pcm",
        # Vídeo
        "video/mp4",
        "video/mpeg",
        "video/mov",
        "video/quicktime",
        "video/avi",
        "video/x-flv",
        "video/mpg",
        "video/webm",
        "video/wmv",
        "video/3gpp",
        "video/x-msvideo",
    }
)

# Extensões ↔ MIME (quando mimetypes falha ou devolve genérico)
_EXT_PARA_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".csv": "text/csv",
    ".html": "text/html",
    ".htm": "text/html",
    ".json": "application/json",
    ".xml": "text/xml",
    ".rtf": "application/rtf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".aiff": "audio/aiff",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpg",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".wmv": "video/wmv",
    ".flv": "video/x-flv",
    ".3gp": "video/3gpp",
    ".3gpp": "video/3gpp",
}


class ErroAnexoIa(RuntimeError):
    """Erro amigável na gestão/envio de anexos à API."""


def _slug_projeto(contratante: str, natureza: str) -> str:
    combinado = f"{(contratante or '').strip()} - {(natureza or '').strip()}"
    limpo = re.sub(r'[<>:"/\\|?*]', "", combinado)
    nome = limpo.replace(" ", "_")
    nome = re.sub(r"_+", "_", nome).strip("_")
    return (nome or "projeto")[:120]


def slug_projeto_do_documento(documento: dict[str, Any]) -> str:
    chave = documento.get("chave") if isinstance(documento.get("chave"), dict) else {}
    return _slug_projeto(
        str(chave.get(CHAVE_JSON_CONTRATANTE) or ""),
        str(chave.get(CHAVE_JSON_NATUREZA_SERVICO) or ""),
    )


def pasta_anexos_do_projeto(documento: dict[str, Any]) -> Path:
    pasta = PASTA_ANEXOS_IA / slug_projeto_do_documento(documento)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def fingerprint_chave_api(chave: str) -> str:
    return hashlib.sha256((chave or "").encode("utf-8")).hexdigest()[:16]


def sha256_ficheiro(caminho: Path) -> str:
    digestor = hashlib.sha256()
    with caminho.open("rb") as ficheiro:
        while True:
            bloco = ficheiro.read(1024 * 1024)
            if not bloco:
                break
            digestor.update(bloco)
    return digestor.hexdigest()


def resolver_mime(caminho: Path) -> str:
    ext = caminho.suffix.lower()
    if ext in _EXT_PARA_MIME:
        return _EXT_PARA_MIME[ext]
    guess, _ = mimetypes.guess_type(str(caminho))
    if guess and guess in MIME_TIPOS_SUPORTADOS:
        return guess
    if guess == "audio/x-wav":
        return "audio/wav"
    raise ErroAnexoIa(
        f"Tipo de ficheiro não suportado pela API Gemini: «{caminho.name}» "
        f"({guess or 'desconhecido'})."
    )


def extensoes_suportadas_para_dialogo() -> list[tuple[str, str]]:
    """Filtros para filedialog (rótulo, padrões)."""
    exts = sorted({ext.lstrip(".") for ext in _EXT_PARA_MIME})
    padrao = " ".join(f"*.{e}" for e in exts)
    return [
        ("Ficheiros suportados pela API Gemini", padrao),
        ("Todos os ficheiros", "*.*"),
    ]


def obter_bloco_anexos(documento: dict[str, Any]) -> dict[str, Any]:
    bloco = documento.get(CHAVE_JSON_IA_CONTEXTO_ARQUIVOS)
    if not isinstance(bloco, dict):
        bloco = {"usar": False, "itens": []}
        documento[CHAVE_JSON_IA_CONTEXTO_ARQUIVOS] = bloco
    if "usar" not in bloco:
        bloco["usar"] = False
    itens = bloco.get("itens")
    if not isinstance(itens, list):
        bloco["itens"] = []
    return bloco


def listar_itens_anexos(documento: dict[str, Any]) -> list[dict[str, Any]]:
    bloco = obter_bloco_anexos(documento)
    return [item for item in bloco.get("itens") or [] if isinstance(item, dict)]


def caminho_absoluto_anexo(relativo: str | None) -> Path | None:
    """Resolve path absoluto; só aceita ficheiros dentro de ``dados_rdo/anexos_ia/``."""
    if not relativo or not str(relativo).strip():
        return None
    texto = str(relativo).strip().replace("\\", "/")
    if ".." in Path(texto).parts:
        return None
    p = Path(texto)
    if not p.is_absolute():
        p = (RAIZ_PROJETO / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(PASTA_ANEXOS_IA.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def caminho_relativo_anexo(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(RAIZ_PROJETO)).replace("\\", "/")
    except ValueError:
        return str(path)


def definir_usar_anexos(documento: dict[str, Any], usar: bool) -> None:
    obter_bloco_anexos(documento)["usar"] = bool(usar)


def anexos_activos_para_envio(documento: dict[str, Any]) -> list[dict[str, Any]]:
    bloco = obter_bloco_anexos(documento)
    if not bool(bloco.get("usar")):
        return []
    activos: list[dict[str, Any]] = []
    for item in listar_itens_anexos(documento):
        if item.get("activo") is False:
            continue
        caminho = caminho_absoluto_anexo(str(item.get("caminho") or ""))
        if caminho is None:
            continue
        activos.append(item)
        if len(activos) >= MAX_ANEXOS_ACTIVOS_ENVIO:
            break
    return activos


def adicionar_anexo_ao_projeto(documento: dict[str, Any], origem: Path) -> dict[str, Any]:
    origem = Path(origem)
    if not origem.is_file():
        raise ErroAnexoIa(f"Ficheiro não encontrado:\n{origem}")

    itens_actuais = listar_itens_anexos(documento)
    if len(itens_actuais) >= MAX_ANEXOS_POR_PROJETO:
        raise ErroAnexoIa(
            f"Limite de {MAX_ANEXOS_POR_PROJETO} ficheiros por projeto. "
            "Remova algum antes de adicionar outro."
        )

    mime = resolver_mime(origem)
    tamanho = origem.stat().st_size
    if tamanho <= 0:
        raise ErroAnexoIa("O ficheiro está vazio.")
    if mime == "application/pdf" and tamanho > _TAMANHO_MAX_PDF_BYTES:
        raise ErroAnexoIa(
            f"PDF demasiado grande ({tamanho / (1024 * 1024):.1f} MB). "
            f"Limite da API: {_TAMANHO_MAX_PDF_BYTES // (1024 * 1024)} MB."
        )
    if tamanho > _TAMANHO_MAX_GERAL_BYTES:
        raise ErroAnexoIa(
            f"Ficheiro demasiado grande ({tamanho / (1024 * 1024):.1f} MB). "
            f"Limite no app: {_TAMANHO_MAX_GERAL_BYTES // (1024 * 1024)} MB."
        )

    sha_origem = sha256_ficheiro(origem)
    for existente in itens_actuais:
        if str(existente.get("sha256") or "") == sha_origem:
            raise ErroAnexoIa(
                f"Este ficheiro já está no projeto "
                f"(«{existente.get('nome_original') or existente.get('id')}»)."
            )

    pasta = pasta_anexos_do_projeto(documento)
    item_id = uuid4().hex[:12]
    nome_seguro = re.sub(r'[<>:"/\\|?*]', "", origem.name).strip() or "anexo"
    # Evita nomes excessivamente longos no Windows.
    if len(nome_seguro) > 80:
        stem = Path(nome_seguro).stem[:60]
        suf = Path(nome_seguro).suffix[:20]
        nome_seguro = f"{stem}{suf}"
    destino = pasta / f"{item_id}_{nome_seguro}"
    shutil.copy2(origem, destino)

    item = {
        "id": item_id,
        "nome_original": origem.name,
        "caminho": caminho_relativo_anexo(destino),
        "mime": mime,
        "sha256": sha_origem,
        "tamanho": destino.stat().st_size,
        "activo": True,
        "uploads": {},
        "adicionado_em": datetime.now(timezone.utc).isoformat(),
    }
    bloco = obter_bloco_anexos(documento)
    itens = list(bloco.get("itens") or [])
    itens.append(item)
    bloco["itens"] = itens
    if not bool(bloco.get("usar")) and len(itens) == 1:
        # Primeiro ficheiro: activa o uso por omissão (o utilizador pode desmarcar).
        bloco["usar"] = True
    return item


def _tentar_apagar_uploads_remotos(item: dict[str, Any], chaves_api: list[str] | None = None) -> None:
    """Best-effort: apaga na Files API os uploads conhecidos deste item."""
    uploads = item.get("uploads")
    if not isinstance(uploads, dict) or not uploads:
        return
    from google import genai

    mapa_fp = {fingerprint_chave_api(k): k for k in (chaves_api or []) if k}
    for fp, meta in list(uploads.items()):
        if not isinstance(meta, dict):
            continue
        name = str(meta.get("name") or "").strip()
        if not name:
            continue
        chave = mapa_fp.get(str(fp))
        if not chave:
            continue
        try:
            genai.Client(api_key=chave).files.delete(name=name)
        except Exception:
            pass


def remover_anexo_do_projeto(
    documento: dict[str, Any],
    item_id: str,
    *,
    chaves_api: list[str] | None = None,
) -> bool:
    bloco = obter_bloco_anexos(documento)
    itens = list(bloco.get("itens") or [])
    novo: list[dict[str, Any]] = []
    removido = False
    for item in itens:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") == str(item_id):
            removido = True
            _tentar_apagar_uploads_remotos(item, chaves_api)
            caminho = caminho_absoluto_anexo(str(item.get("caminho") or ""))
            if caminho is not None:
                try:
                    caminho.unlink(missing_ok=True)
                except OSError:
                    pass
            continue
        novo.append(item)
    bloco["itens"] = novo
    if not novo:
        bloco["usar"] = False
    return removido


def definir_anexo_activo(documento: dict[str, Any], item_id: str, activo: bool) -> None:
    for item in listar_itens_anexos(documento):
        if str(item.get("id") or "") == str(item_id):
            item["activo"] = bool(activo)
            return


def remover_pasta_anexos_projeto(documento: dict[str, Any] | None, *, slug: str | None = None) -> None:
    """Apaga a pasta local de anexos (ex.: ao excluir o projeto)."""
    alvo_slug = slug
    if not alvo_slug and isinstance(documento, dict):
        alvo_slug = slug_projeto_do_documento(documento)
    if not alvo_slug:
        return
    pasta = PASTA_ANEXOS_IA / alvo_slug
    if pasta.is_dir():
        shutil.rmtree(pasta, ignore_errors=True)


def migrar_anexos_ao_renomear_projeto(
    documento: dict[str, Any],
    *,
    slug_antigo: str,
    slug_novo: str,
) -> None:
    """Move a pasta de anexos e actualiza caminhos relativos no JSON."""
    if not slug_antigo or not slug_novo or slug_antigo == slug_novo:
        return
    origem = PASTA_ANEXOS_IA / slug_antigo
    destino = PASTA_ANEXOS_IA / slug_novo
    if origem.is_dir():
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            # Mescla ficheiros se a pasta nova já existir.
            for ficheiro in origem.rglob("*"):
                if not ficheiro.is_file():
                    continue
                alvo = destino / ficheiro.relative_to(origem)
                alvo.parent.mkdir(parents=True, exist_ok=True)
                if not alvo.exists():
                    shutil.move(str(ficheiro), str(alvo))
            shutil.rmtree(origem, ignore_errors=True)
        else:
            shutil.move(str(origem), str(destino))

    prefixo_antigo = f"dados_rdo/anexos_ia/{slug_antigo}/"
    prefixo_novo = f"dados_rdo/anexos_ia/{slug_novo}/"
    for item in listar_itens_anexos(documento):
        caminho = str(item.get("caminho") or "").replace("\\", "/")
        if caminho.startswith(prefixo_antigo):
            item["caminho"] = prefixo_novo + caminho[len(prefixo_antigo) :]
        # URIs remotos ficam inválidos se a pasta mudou de conteúdo; limpar uploads.
        item["uploads"] = {}


def _parse_expira_em(texto: str | None) -> datetime | None:
    bruto = str(texto or "").strip()
    if not bruto:
        return None
    try:
        if bruto.endswith("Z"):
            bruto = bruto[:-1] + "+00:00"
        return datetime.fromisoformat(bruto)
    except ValueError:
        return None


def _upload_ainda_valido(meta: dict[str, Any], sha256_local: str) -> bool:
    if not isinstance(meta, dict):
        return False
    if str(meta.get("sha256") or "") != sha256_local:
        return False
    if not str(meta.get("uri") or "").strip():
        return False
    expira = _parse_expira_em(str(meta.get("expira_em") or ""))
    if expira is None:
        return False
    agora = datetime.now(timezone.utc)
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    return expira.timestamp() > agora.timestamp() + _MARGEM_EXPIRACAO_SEGUNDOS


def _aguardar_ficheiro_activo(cliente: Any, name: str) -> Any:
    from google.genai import types

    inicio = time.time()
    ultimo = None
    while time.time() - inicio < _TIMEOUT_PROCESSAMENTO_SEGUNDOS:
        ultimo = cliente.files.get(name=name)
        estado = getattr(ultimo, "state", None)
        if estado == types.FileState.ACTIVE or str(getattr(estado, "value", estado)) == "ACTIVE":
            return ultimo
        if estado == types.FileState.FAILED or str(getattr(estado, "value", estado)) == "FAILED":
            erro = getattr(ultimo, "error", None)
            raise ErroAnexoIa(f"A API falhou ao processar o ficheiro «{name}»: {erro or 'FAILED'}")
        time.sleep(0.6)
    raise ErroAnexoIa(f"Tempo esgotado à espera do processamento do ficheiro «{name}».")


def _meta_upload_de_ficheiro_api(ficheiro_api: Any, sha256_local: str) -> dict[str, str]:
    uri = str(getattr(ficheiro_api, "uri", "") or "").strip()
    name = str(getattr(ficheiro_api, "name", "") or "").strip()
    mime = str(getattr(ficheiro_api, "mime_type", "") or "").strip()
    expira = getattr(ficheiro_api, "expiration_time", None)
    if hasattr(expira, "isoformat"):
        expira_txt = expira.isoformat()
    else:
        expira_txt = str(expira or "").strip()
    if not uri or not name:
        raise ErroAnexoIa("A API não devolveu URI/nome do ficheiro enviado.")
    return {
        "name": name,
        "uri": uri,
        "mime": mime,
        "expira_em": expira_txt,
        "sha256": sha256_local,
    }


def garantir_uploads_anexos_para_chave(
    documento: dict[str, Any],
    api_key: str,
    *,
    cliente: Any | None = None,
    ao_estado: Callable[[str], None] | None = None,
) -> list[dict[str, str]]:
    """
    Garante URI válido na Files API para cada anexo activo, nesta chave.

    Devolve lista de ``{uri, mime, nome}`` prontos para o ``generate_content``.
    """
    activos = anexos_activos_para_envio(documento)
    if not activos:
        return []

    sanear_anexos_documento(documento)
    activos = anexos_activos_para_envio(documento)
    if not activos:
        return []

    from google import genai

    cli = cliente or genai.Client(api_key=api_key)
    fp = fingerprint_chave_api(api_key)
    prontos: list[dict[str, str]] = []

    for item in activos:
        caminho = caminho_absoluto_anexo(str(item.get("caminho") or ""))
        if caminho is None:
            raise ErroAnexoIa(
                f"Anexo em falta no disco: {item.get('nome_original') or item.get('id')}. "
                "Remova-o nas Configurações Gemini ou volte a adicioná-lo."
            )
        sha_local = str(item.get("sha256") or "") or sha256_ficheiro(caminho)
        item["sha256"] = sha_local
        mime = str(item.get("mime") or "") or resolver_mime(caminho)
        item["mime"] = mime
        nome_exib = str(item.get("nome_original") or caminho.name)

        uploads = item.get("uploads")
        if not isinstance(uploads, dict):
            uploads = {}
            item["uploads"] = uploads
        meta = uploads.get(fp)
        if isinstance(meta, dict) and _upload_ainda_valido(meta, sha_local):
            # Confirma que a API ainda conhece o ficheiro.
            try:
                remoto = cli.files.get(name=str(meta.get("name") or ""))
                estado = str(getattr(getattr(remoto, "state", None), "value", getattr(remoto, "state", "")) or "")
                if estado in {"ACTIVE", "PROCESSING"}:
                    if estado == "PROCESSING":
                        remoto = _aguardar_ficheiro_activo(cli, str(meta.get("name")))
                        uploads[fp] = _meta_upload_de_ficheiro_api(remoto, sha_local)
                    prontos.append(
                        {
                            "uri": str(uploads[fp].get("uri") or meta.get("uri")),
                            "mime": str(uploads[fp].get("mime") or mime),
                            "nome": nome_exib,
                        }
                    )
                    continue
            except Exception:
                uploads.pop(fp, None)

        if ao_estado:
            ao_estado(f"A enviar «{nome_exib}» para a API Gemini…")
        try:
            enviado = cli.files.upload(
                file=str(caminho),
                config={"mime_type": mime},
            )
            name = str(getattr(enviado, "name", "") or "")
            estado = str(getattr(getattr(enviado, "state", None), "value", getattr(enviado, "state", "")) or "")
            if estado == "PROCESSING" or not str(getattr(enviado, "uri", "") or ""):
                enviado = _aguardar_ficheiro_activo(cli, name)
            uploads[fp] = _meta_upload_de_ficheiro_api(enviado, sha_local)
        except ErroAnexoIa:
            raise
        except Exception as exc:
            raise ErroAnexoIa(f"Falha ao enviar «{nome_exib}» para a API: {exc}") from exc

        prontos.append(
            {
                "uri": uploads[fp]["uri"],
                "mime": uploads[fp].get("mime") or mime,
                "nome": nome_exib,
            }
        )

    return prontos


def montar_conteudos_com_anexos(prompt_texto: str, anexos_remotos: list[dict[str, str]]) -> list[Any]:
    """Monta a lista de Parts (texto + ficheiros) para ``generate_content``."""
    from google.genai import types

    partes: list[Any] = [types.Part.from_text(text=prompt_texto)]
    for anexo in anexos_remotos:
        partes.append(
            types.Part.from_uri(
                file_uri=str(anexo["uri"]),
                mime_type=str(anexo.get("mime") or "application/octet-stream"),
            )
        )
    return partes


def rotulo_projeto_documento(documento: dict[str, Any] | None) -> str:
    if not isinstance(documento, dict):
        return ""
    chave = documento.get("chave") if isinstance(documento.get("chave"), dict) else {}
    c = str(chave.get(CHAVE_JSON_CONTRATANTE) or "").strip()
    n = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO) or "").strip()
    if c and n:
        return f"{c} — {n}"
    return c or n or "(projeto sem nome)"


def _formatar_expira_local(texto: str | None) -> str:
    dt = _parse_expira_em(texto)
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone()
    return local.strftime("%d/%m/%Y %H:%M")


def sanear_anexos_documento(documento: dict[str, Any]) -> dict[str, int]:
    """
    Corrige inconsistências locais: ficheiro em falta, hash alterado, uploads expirados.

    Devolve contagens ``{em_falta, hash_alterado, uploads_limpos}``.
    """
    stats = {"em_falta": 0, "hash_alterado": 0, "uploads_limpos": 0}
    for item in listar_itens_anexos(documento):
        caminho = caminho_absoluto_anexo(str(item.get("caminho") or ""))
        uploads = item.get("uploads")
        if not isinstance(uploads, dict):
            item["uploads"] = {}
            uploads = item["uploads"]

        if caminho is None:
            stats["em_falta"] += 1
            if uploads:
                uploads.clear()
                stats["uploads_limpos"] += 1
            continue

        try:
            sha_atual = sha256_ficheiro(caminho)
            item["tamanho"] = caminho.stat().st_size
        except OSError:
            stats["em_falta"] += 1
            uploads.clear()
            stats["uploads_limpos"] += 1
            continue

        sha_guardado = str(item.get("sha256") or "")
        if sha_guardado and sha_guardado != sha_atual:
            stats["hash_alterado"] += 1
            item["sha256"] = sha_atual
            uploads.clear()
            stats["uploads_limpos"] += 1
            continue
        item["sha256"] = sha_atual

        for fp in list(uploads.keys()):
            meta = uploads.get(fp)
            if not isinstance(meta, dict) or not _upload_ainda_valido(meta, sha_atual):
                uploads.pop(fp, None)
                stats["uploads_limpos"] += 1
    return stats


def limpar_uploads_expirados(documento: dict[str, Any]) -> int:
    """Remove metadados de upload expirados/inválidos. Devolve quantos foram limpos."""
    return int(sanear_anexos_documento(documento).get("uploads_limpos") or 0)


def resumo_estado_anexo(
    item: dict[str, Any],
    chaves_api: list[str],
) -> dict[str, Any]:
    """
    Estado local (sem rede) do anexo face às chaves cadastradas.

    ``nivel``: ok | aviso | erro | neutro
    """
    nome = str(item.get("nome_original") or item.get("id") or "anexo")
    caminho = caminho_absoluto_anexo(str(item.get("caminho") or ""))
    activo = item.get("activo") is not False
    if caminho is None:
        return {
            "nivel": "erro",
            "titulo": f"{nome} — ficheiro em falta no disco",
            "detalhe": "Remova o item ou volte a adicionar o ficheiro.",
            "validas": 0,
            "total_chaves": len(chaves_api),
            "expira_mais_cedo": "",
        }

    sha = str(item.get("sha256") or "")
    try:
        sha_disco = sha256_ficheiro(caminho)
    except OSError:
        sha_disco = ""
    if sha and sha_disco and sha != sha_disco:
        return {
            "nivel": "aviso",
            "titulo": f"{nome} — conteúdo alterado no disco",
            "detalhe": "Será reenviado na próxima reescrita.",
            "validas": 0,
            "total_chaves": len(chaves_api),
            "expira_mais_cedo": "",
        }

    uploads = item.get("uploads") if isinstance(item.get("uploads"), dict) else {}
    validas = 0
    expiracoes: list[datetime] = []
    for chave in chaves_api:
        fp = fingerprint_chave_api(chave)
        meta = uploads.get(fp)
        if isinstance(meta, dict) and _upload_ainda_valido(meta, sha or sha_disco):
            validas += 1
            dt = _parse_expira_em(str(meta.get("expira_em") or ""))
            if dt is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                expiracoes.append(dt)

    total = len(chaves_api)
    expira_txt = ""
    if expiracoes:
        expira_txt = _formatar_expira_local(min(expiracoes).isoformat())

    if total == 0:
        return {
            "nivel": "aviso",
            "titulo": f"{nome} — sem chaves Gemini",
            "detalhe": "Cadastre uma chave para poder enviar o ficheiro.",
            "validas": 0,
            "total_chaves": 0,
            "expira_mais_cedo": "",
        }
    if validas == 0:
        return {
            "nivel": "aviso" if activo else "neutro",
            "titulo": f"{nome} — ainda não enviado à API",
            "detalhe": "Será enviado automaticamente na próxima reescrita (por chave).",
            "validas": 0,
            "total_chaves": total,
            "expira_mais_cedo": "",
        }
    if validas < total:
        return {
            "nivel": "aviso",
            "titulo": f"{nome} — pronto em {validas}/{total} chave(s)",
            "detalhe": (
                f"Válido até {expira_txt}. As outras chaves receberão o ficheiro no rodízio."
                if expira_txt
                else "As outras chaves receberão o ficheiro no rodízio."
            ),
            "validas": validas,
            "total_chaves": total,
            "expira_mais_cedo": expira_txt,
        }
    return {
        "nivel": "ok",
        "titulo": f"{nome} — pronto em todas as chaves ({total})",
        "detalhe": f"Válido até {expira_txt}." if expira_txt else "URI activo na Files API.",
        "validas": validas,
        "total_chaves": total,
        "expira_mais_cedo": expira_txt,
    }


def verificar_anexos_na_api(
    documento: dict[str, Any],
    chaves_api: list[str],
    *,
    ao_estado: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Confirma na API (files.get) os uploads guardados; limpa os inválidos.

    Não faz upload novo — só auditoria. Devolve ``{ok, invalidos, erros}``.
    """
    from google import genai

    sanear_anexos_documento(documento)
    ok = 0
    invalidos = 0
    erros: list[str] = []
    for chave in chaves_api:
        fp = fingerprint_chave_api(chave)
        try:
            cli = genai.Client(api_key=chave)
        except Exception as exc:
            erros.append(f"Chave inválida para verificar: {exc}")
            continue
        for item in listar_itens_anexos(documento):
            uploads = item.get("uploads") if isinstance(item.get("uploads"), dict) else {}
            meta = uploads.get(fp)
            if not isinstance(meta, dict):
                continue
            name = str(meta.get("name") or "").strip()
            nome = str(item.get("nome_original") or item.get("id") or "anexo")
            if ao_estado:
                ao_estado(f"A verificar «{nome}» na API…")
            try:
                remoto = cli.files.get(name=name)
                estado = str(
                    getattr(getattr(remoto, "state", None), "value", getattr(remoto, "state", "")) or ""
                )
                if estado == "ACTIVE":
                    # Actualiza expiração se a API devolver valor fresco.
                    uploads[fp] = _meta_upload_de_ficheiro_api(
                        remoto, str(item.get("sha256") or meta.get("sha256") or "")
                    )
                    ok += 1
                else:
                    uploads.pop(fp, None)
                    invalidos += 1
            except Exception:
                uploads.pop(fp, None)
                invalidos += 1
    return {"ok": ok, "invalidos": invalidos, "erros": erros}


def texto_aviso_privacidade_anexos() -> str:
    return (
        "Privacidade: ao reescrever com ficheiros activos, o conteúdo é enviado à API Google Gemini "
        "(plano gratuito / Files API, retenção ~48 h por chave). Não anexe dados que não possa "
        "partilhar com o Google. A cópia local fica só neste computador, em dados_rdo/anexos_ia/."
    )