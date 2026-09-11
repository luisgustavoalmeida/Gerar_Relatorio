"""Assinaturas do funcionário — reutilizáveis e ligadas ao nome."""

from __future__ import annotations

import shutil
from pathlib import Path

from rdo_diario.paths import PASTA_ASSINATURAS, RAIZ_PROJETO

EXTENSOES_ASSINATURA = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def slug_funcionario(nome: str, max_len: int = 60) -> str:
    """Nome do funcionário → nome de ficheiro seguro."""
    import re

    texto = (nome or "").strip()
    texto = re.sub(r'[<>:"/\\|?*]', "", texto)
    texto = texto.replace(" ", "_")
    texto = re.sub(r"_+", "_", texto).strip("_")
    return (texto or "funcionario")[:max_len]


def garantir_pasta_assinaturas() -> Path:
    PASTA_ASSINATURAS.mkdir(parents=True, exist_ok=True)
    return PASTA_ASSINATURAS


def caminho_absoluto(relativo: str | None) -> Path | None:
    if not relativo or not str(relativo).strip():
        return None
    texto = str(relativo).strip().replace("\\", "/")
    # Compatibilidade: paths antigos em assets/ → template/
    if texto.startswith("assets/assinaturas/"):
        texto = "template/assinaturas/" + texto[len("assets/assinaturas/") :]
    elif texto.startswith("assets/logos/"):
        texto = "template/logos/" + texto[len("assets/logos/") :]
    p = Path(texto)
    if not p.is_absolute():
        p = (RAIZ_PROJETO / p).resolve()
    return p if p.is_file() else None


def caminho_relativo(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(RAIZ_PROJETO)).replace("\\", "/")
    except ValueError:
        return str(path)


def arquivo_padrao_para_nome(nome_funcionario: str) -> Path | None:
    """Procura assinatura já salva para o nome do funcionário."""
    slug = slug_funcionario(nome_funcionario)
    if slug == "funcionario" and not (nome_funcionario or "").strip():
        return None
    pasta = garantir_pasta_assinaturas()
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        candidato = pasta / f"{slug}{ext}"
        if candidato.is_file():
            return candidato
    for arq in sorted(pasta.glob(f"{slug}.*")):
        if arq.suffix.lower() in EXTENSOES_ASSINATURA and arq.is_file():
            return arq
    return None


def resolver_assinatura(nome_funcionario: str, assinatura_arquivo: str | None) -> Path | None:
    """Resolve path absoluto: caminho guardado ou ficheiro padrão do nome."""
    abs_path = caminho_absoluto(assinatura_arquivo)
    if abs_path:
        return abs_path
    return arquivo_padrao_para_nome(nome_funcionario)


def salvar_assinatura_para_funcionario(origem: Path, nome_funcionario: str) -> str:
    """
    Copia a imagem para template/assinaturas/{slug}.ext e devolve o path relativo à raiz.
    """
    origem = Path(origem)
    if not origem.is_file():
        raise FileNotFoundError(f"Arquivo de assinatura não encontrado:\n{origem}")
    ext = origem.suffix.lower()
    if ext not in EXTENSOES_ASSINATURA:
        raise ValueError("Formato não suportado. Use PNG, JPG, WEBP, GIF ou BMP.")
    nome = (nome_funcionario or "").strip()
    if not nome:
        raise ValueError("Informe o nome do funcionário antes de adicionar a assinatura.")

    pasta = garantir_pasta_assinaturas()
    slug = slug_funcionario(nome)
    destino = pasta / f"{slug}{ext}"

    for antigo in pasta.glob(f"{slug}.*"):
        if antigo.resolve() != destino.resolve() and antigo.suffix.lower() in EXTENSOES_ASSINATURA:
            try:
                antigo.unlink()
            except OSError:
                pass

    shutil.copy2(origem, destino)
    return caminho_relativo(destino)
