"""Logos da empresa (contratada) — reutilizáveis entre projetos."""

from __future__ import annotations

import shutil
from pathlib import Path

from rdo_diario.assinaturas import caminho_absoluto, caminho_relativo, slug_funcionario
from rdo_diario.paths import PASTA_LOGOS

EXTENSOES_LOGO = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def slug_empresa(nome: str) -> str:
    return slug_funcionario(nome or "", max_len=60) or "empresa"


def garantir_pasta_logos() -> Path:
    PASTA_LOGOS.mkdir(parents=True, exist_ok=True)
    return PASTA_LOGOS


def arquivo_padrao_para_empresa(nome_empresa: str) -> Path | None:
    """Procura logo já salva para o nome da empresa (contratada)."""
    slug = slug_empresa(nome_empresa)
    if slug == "empresa" and not (nome_empresa or "").strip():
        return None
    pasta = garantir_pasta_logos()
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        candidato = pasta / f"{slug}{ext}"
        if candidato.is_file():
            return candidato
    for arq in sorted(pasta.glob(f"{slug}.*")):
        if arq.suffix.lower() in EXTENSOES_LOGO and arq.is_file():
            return arq
    return None


def resolver_logo(nome_empresa: str, logo_arquivo: str | None) -> Path | None:
    """Resolve path absoluto: caminho guardado ou ficheiro padrão do nome da empresa."""
    abs_path = caminho_absoluto(logo_arquivo)
    if abs_path:
        return abs_path
    return arquivo_padrao_para_empresa(nome_empresa)


def salvar_logo_para_empresa(origem: Path, nome_empresa: str) -> str:
    """
    Copia a imagem para template/logos/{slug}.ext e devolve o path relativo à raiz.
    """
    origem = Path(origem)
    if not origem.is_file():
        raise FileNotFoundError(f"Arquivo de logo não encontrado:\n{origem}")
    ext = origem.suffix.lower()
    if ext not in EXTENSOES_LOGO:
        raise ValueError("Formato não suportado. Use PNG, JPG, WEBP, GIF ou BMP.")
    nome = (nome_empresa or "").strip()
    if not nome:
        raise ValueError("Informe a «Contratada» antes de adicionar o logo.")

    pasta = garantir_pasta_logos()
    slug = slug_empresa(nome)
    destino = pasta / f"{slug}{ext}"

    for antigo in pasta.glob(f"{slug}.*"):
        if antigo.resolve() != destino.resolve() and antigo.suffix.lower() in EXTENSOES_LOGO:
            try:
                antigo.unlink()
            except OSError:
                pass

    shutil.copy2(origem, destino)
    return caminho_relativo(destino)
