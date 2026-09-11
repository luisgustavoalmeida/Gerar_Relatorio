"""Modelo de cabeçalho reutilizável (campos + assinatura + logo).

No .exe, tudo é gravado ao lado do executável (pastas graváveis), nunca em ``_MEIPASS``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdo_diario.assinaturas import (
    caminho_absoluto,
    caminho_relativo,
    garantir_pasta_assinaturas,
    resolver_assinatura,
    salvar_assinatura_para_funcionario,
)
from rdo_diario.logos import (
    garantir_pasta_logos,
    resolver_logo,
    salvar_logo_para_empresa,
)
from rdo_diario.paths import RAIZ_PROJETO, _pasta_bundle_pyinstaller
from rdo_diario.schema import (
    CAMPOS_JSON_CABECALHO,
    CHAVE_JSON_ASSINATURA_ARQUIVO,
    CHAVE_JSON_LOGO_ARQUIVO,
)


def caminho_modelo_cabecalho() -> Path:
    """Caminho gravável do modelo (raiz do repo ou pasta do .exe)."""
    return RAIZ_PROJETO / "template" / "modelo_cabecalho.json"


def garantir_pastas_imagens_usuario() -> None:
    """Garante pastas graváveis de imagens e template ao lado do .exe / no repo."""
    (RAIZ_PROJETO / "template").mkdir(parents=True, exist_ok=True)
    garantir_pasta_assinaturas()
    garantir_pasta_logos()


def _candidatos_leitura_modelo() -> list[Path]:
    """Ordem: ficheiro local (gravável), depois cópia embutida no bundle do .exe."""
    caminhos = [caminho_modelo_cabecalho()]
    bundle = _pasta_bundle_pyinstaller()
    if bundle is not None:
        caminhos.append(bundle / "template" / "modelo_cabecalho.json")
    return caminhos


def localizar_arquivo_modelo_cabecalho() -> Path | None:
    for path in _candidatos_leitura_modelo():
        if path.is_file():
            return path
    return None


def _nome_funcionario(cab: dict[str, Any]) -> str:
    return str(cab.get("nome_funcionario") or "").strip() or "funcionario"


def _nome_empresa(cab: dict[str, Any]) -> str:
    return (
        str(cab.get("contratada") or "").strip()
        or str(cab.get("contratante") or "").strip()
        or "empresa"
    )


def sincronizar_imagens_no_cabecalho(cabecalho: dict[str, Any]) -> dict[str, Any]:
    """
    Garante que assinatura e logo existem em ``template/assinaturas`` e
    ``template/logos`` (gravável) e devolve o cabeçalho com paths relativos actualizados.

    Usado ao salvar e ao carregar o modelo, para reutilizar imagens entre projectos
    e funcionar correctamente no .exe.
    """
    garantir_pastas_imagens_usuario()
    out = dict(cabecalho)

    nome = _nome_funcionario(out)
    path_ass = resolver_assinatura(nome, out.get(CHAVE_JSON_ASSINATURA_ARQUIVO))
    if path_ass and path_ass.is_file():
        try:
            out[CHAVE_JSON_ASSINATURA_ARQUIVO] = salvar_assinatura_para_funcionario(
                path_ass, nome
            )
        except (OSError, ValueError, FileNotFoundError):
            # Mantém referência relativa se a cópia falhar mas o ficheiro existir
            out[CHAVE_JSON_ASSINATURA_ARQUIVO] = caminho_relativo(path_ass)
    else:
        # Fallback: path absoluto/relativo explícito ainda válido
        abs_ass = caminho_absoluto(str(out.get(CHAVE_JSON_ASSINATURA_ARQUIVO) or ""))
        out[CHAVE_JSON_ASSINATURA_ARQUIVO] = (
            caminho_relativo(abs_ass) if abs_ass else ""
        )

    empresa = _nome_empresa(out)
    path_logo = resolver_logo(empresa, out.get(CHAVE_JSON_LOGO_ARQUIVO))
    if path_logo and path_logo.is_file():
        try:
            out[CHAVE_JSON_LOGO_ARQUIVO] = salvar_logo_para_empresa(path_logo, empresa)
        except (OSError, ValueError, FileNotFoundError):
            out[CHAVE_JSON_LOGO_ARQUIVO] = caminho_relativo(path_logo)
    else:
        abs_logo = caminho_absoluto(str(out.get(CHAVE_JSON_LOGO_ARQUIVO) or ""))
        out[CHAVE_JSON_LOGO_ARQUIVO] = (
            caminho_relativo(abs_logo) if abs_logo else ""
        )

    return out


def montar_dados_modelo_cabecalho(cabecalho: dict[str, Any]) -> dict[str, Any]:
    """Prepara o dicionário a gravar no JSON do modelo (campos + imagens)."""
    dados: dict[str, Any] = {}
    for campo in CAMPOS_JSON_CABECALHO:
        dados[campo] = str(cabecalho.get(campo) or "").strip()
    dados[CHAVE_JSON_ASSINATURA_ARQUIVO] = str(
        cabecalho.get(CHAVE_JSON_ASSINATURA_ARQUIVO) or ""
    ).strip()
    dados[CHAVE_JSON_LOGO_ARQUIVO] = str(cabecalho.get(CHAVE_JSON_LOGO_ARQUIVO) or "").strip()
    return sincronizar_imagens_no_cabecalho(dados)


def salvar_modelo_cabecalho_arquivo(cabecalho: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Grava o modelo em ``template/modelo_cabecalho.json`` (ao lado do .exe)."""
    from rdo_diario.storage import salvar_documento_json

    garantir_pastas_imagens_usuario()
    dados = montar_dados_modelo_cabecalho(cabecalho)
    destino = caminho_modelo_cabecalho()
    salvar_documento_json(destino, dados)
    return destino, dados


def carregar_modelo_cabecalho_arquivo() -> dict[str, Any]:
    """
    Lê o modelo e sincroniza imagens para ``template/assinaturas`` e ``template/logos``.

    Raises:
        FileNotFoundError: se não existir modelo.
        ValueError / json.JSONDecodeError: conteúdo inválido.
    """
    path = localizar_arquivo_modelo_cabecalho()
    if path is None:
        raise FileNotFoundError(
            f"Modelo de cabeçalho não encontrado:\n{caminho_modelo_cabecalho()}"
        )
    with path.open(encoding="utf-8") as f:
        dados = json.load(f)
    if not isinstance(dados, dict):
        raise ValueError("Modelo de cabeçalho inválido (não é um dicionário JSON).")
    # Remove meta interno se existir (salvar_documento_json acrescenta)
    dados = {k: v for k, v in dados.items() if k != "meta"}
    return sincronizar_imagens_no_cabecalho(dados)
