"""
Leitura e gravação dos ficheiros JSON por cliente e preferências locais do utilizador.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdo_diario.paths import ARQUIVO_CONFIG_USUARIO_JSON, PASTA_DADOS_RDO, PASTA_RDO_ARQUIVADOS
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


_FICHEIROS_JSON_IGNORAR_LISTAGEM = frozenset(
    {
        ARQUIVO_CONFIG_USUARIO_JSON.name,
    }
)


def _listar_projetos_json_na_pasta(pasta: Path) -> list[tuple[str, str, Path]]:
    """Lista projectos (JSON com objeto ``chave``) numa pasta plana."""
    if not pasta.is_dir():
        return []
    resultado: list[tuple[str, str, Path]] = []
    for caminho in sorted(pasta.glob("*.json")):
        if caminho.name.startswith("_") or caminho.name in _FICHEIROS_JSON_IGNORAR_LISTAGEM:
            continue
        try:
            documento = carregar_documento_json(caminho)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(documento.get("chave"), dict):
            continue
        chave = documento.get("chave") or {}
        c = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
        n = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
        if c or n:
            resultado.append((c, n, caminho))
    return resultado


def listar_clientes_salvos() -> list[tuple[str, str, Path]]:
    """
    Lista clientes vigentes com ficheiro JSON válido (contratante, natureza, caminho).
    Exclui projectos em ``rdo_arquivados/`` e ficheiros de configuração.
    """
    return _listar_projetos_json_na_pasta(PASTA_DADOS_RDO)


def listar_projetos_arquivados() -> list[tuple[str, str, Path]]:
    """Lista projectos guardados em ``dados_rdo/rdo_arquivados/``."""
    return _listar_projetos_json_na_pasta(PASTA_RDO_ARQUIVADOS)


def arquivar_projeto(
    caminho: Path,
    *,
    contratante: str,
    natureza_servico: str,
) -> Path:
    """Move o JSON do projecto para ``rdo_arquivados/``."""
    if not caminho.is_file():
        raise FileNotFoundError(f"Ficheiro não encontrado: {caminho}")
    if caminho.parent.resolve() != PASTA_DADOS_RDO.resolve():
        raise ValueError("Só é possível arquivar projectos em dados_rdo/.")

    PASTA_RDO_ARQUIVADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_RDO_ARQUIVADOS / caminho.name
    if destino.exists():
        raise FileExistsError(f"Já existe um arquivo com o nome «{destino.name}» em rdo_arquivados/.")

    shutil.move(str(caminho), str(destino))

    ultimo = ler_memoria_ultimo_cliente()
    if ultimo and ultimo[0] == contratante.strip() and ultimo[1] == natureza_servico.strip():
        _limpar_memoria_ultimo_cliente()

    return destino


def desarquivar_projeto(caminho: Path) -> Path:
    """Move o JSON de ``rdo_arquivados/`` de volta para ``dados_rdo/``."""
    if not caminho.is_file():
        raise FileNotFoundError(f"Ficheiro não encontrado: {caminho}")
    if caminho.parent.resolve() != PASTA_RDO_ARQUIVADOS.resolve():
        raise ValueError("Só é possível desarquivar projectos de rdo_arquivados/.")

    documento = carregar_documento_json(caminho)
    chave = documento.get("chave") or {}
    c = str(chave.get(CHAVE_JSON_CONTRATANTE, "")).strip()
    n = str(chave.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
    if c and n:
        existente = encontrar_cliente_por_chave(c, n)
        if existente is not None:
            raise FileExistsError(
                f"Já existe um projecto vigente com a chave «{c} — {n}» ({existente.name})."
            )

    PASTA_DADOS_RDO.mkdir(parents=True, exist_ok=True)
    destino = PASTA_DADOS_RDO / caminho.name
    if destino.exists():
        raise FileExistsError(f"Já existe um ficheiro «{destino.name}» em dados_rdo/.")

    shutil.move(str(caminho), str(destino))
    return destino


def encontrar_cliente_por_chave(
    contratante: str,
    natureza_servico: str,
    *,
    ignorar_caminho: Path | None = None,
) -> Path | None:
    """
    Devolve o caminho do JSON se já existir cliente com o mesmo par chave.

    ``ignorar_caminho`` exclui o ficheiro actual (útil ao renomear o cliente aberto).
    """
    c = contratante.strip()
    n = natureza_servico.strip()
    if not c or not n:
        return None
    ignorar = ignorar_caminho.resolve() if ignorar_caminho else None
    for c2, n2, caminho in listar_clientes_salvos():
        if c2 == c and n2 == n:
            if ignorar is not None and caminho.resolve() == ignorar:
                continue
            return caminho
    caminho_por_nome = caminho_arquivo_por_cliente(c, n)
    if caminho_por_nome.is_file():
        if ignorar is None or caminho_por_nome.resolve() != ignorar:
            return caminho_por_nome
    return None


def atualizar_chave_cliente(
    documento: dict[str, Any],
    caminho_atual: Path,
    novo_contratante: str,
    nova_natureza: str,
) -> tuple[dict[str, Any], Path]:
    """
    Atualiza ``chave`` e os campos homónimos em ``cabecalho_fixo``; renomeia o JSON se necessário.
    """
    c = novo_contratante.strip()
    n = nova_natureza.strip()
    if not c or not n:
        raise ValueError("Contratante e natureza do serviço são obrigatórios.")

    novo_caminho = caminho_arquivo_por_cliente(c, n)
    documento["chave"] = {
        CHAVE_JSON_CONTRATANTE: c,
        CHAVE_JSON_NATUREZA_SERVICO: n,
    }
    cabecalho = documento.setdefault("cabecalho_fixo", {})
    cabecalho["contratante"] = c
    cabecalho["natureza_servico"] = n

    salvar_documento_json(novo_caminho, documento)

    if caminho_atual.resolve() != novo_caminho.resolve() and caminho_atual.is_file():
        caminho_atual.unlink()

    return documento, novo_caminho


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


_ARQUIVO_ULTIMO_CLIENTE_LEGADO = PASTA_DADOS_RDO / "_ultimo_cliente.json"
_ARQUIVO_CONFIG_USUARIO_LEGADO = PASTA_DADOS_RDO / "config_usuario.json"


def _migrar_config_usuario_legado_para_template() -> None:
    """Move ``config_usuario.json`` de ``dados_rdo/`` para ``template/`` (actualização)."""
    if not _ARQUIVO_CONFIG_USUARIO_LEGADO.is_file():
        return
    ARQUIVO_CONFIG_USUARIO_JSON.parent.mkdir(parents=True, exist_ok=True)
    if ARQUIVO_CONFIG_USUARIO_JSON.is_file():
        try:
            _ARQUIVO_CONFIG_USUARIO_LEGADO.unlink(missing_ok=True)
        except OSError:
            pass
        return
    try:
        shutil.move(str(_ARQUIVO_CONFIG_USUARIO_LEGADO), str(ARQUIVO_CONFIG_USUARIO_JSON))
    except OSError:
        try:
            shutil.copy2(_ARQUIVO_CONFIG_USUARIO_LEGADO, ARQUIVO_CONFIG_USUARIO_JSON)
            _ARQUIVO_CONFIG_USUARIO_LEGADO.unlink(missing_ok=True)
        except OSError:
            pass


def ler_config_usuario() -> dict[str, Any]:
    """Lê preferências locais em ``template/config_usuario.json`` (tema, geometria, último cliente)."""
    _migrar_config_usuario_legado_para_template()
    if not ARQUIVO_CONFIG_USUARIO_JSON.is_file():
        dados: dict[str, Any] = {}
    else:
        try:
            conteudo = json.loads(ARQUIVO_CONFIG_USUARIO_JSON.read_text(encoding="utf-8"))
            dados = conteudo if isinstance(conteudo, dict) else {}
        except (json.JSONDecodeError, OSError):
            dados = {}
    return _migrar_ultimo_cliente_legado_para_config(dados)


def gravar_config_usuario(dados: dict[str, Any]) -> None:
    """Persiste preferências locais em ``template/config_usuario.json``."""
    ARQUIVO_CONFIG_USUARIO_JSON.parent.mkdir(parents=True, exist_ok=True)
    try:
        ARQUIVO_CONFIG_USUARIO_JSON.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _migrar_ultimo_cliente_legado_para_config(dados: dict[str, Any]) -> dict[str, Any]:
    """Importa `_ultimo_cliente.json` para `config_usuario.json` e remove o ficheiro antigo."""
    if not _ARQUIVO_ULTIMO_CLIENTE_LEGADO.is_file():
        return dados
    try:
        legado = json.loads(_ARQUIVO_ULTIMO_CLIENTE_LEGADO.read_text(encoding="utf-8"))
        if isinstance(legado, dict):
            c = str(legado.get(CHAVE_JSON_CONTRATANTE, "")).strip()
            n = str(legado.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
            if c and n:
                if not str(dados.get(CHAVE_JSON_CONTRATANTE, "")).strip():
                    dados[CHAVE_JSON_CONTRATANTE] = c
                if not str(dados.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip():
                    dados[CHAVE_JSON_NATUREZA_SERVICO] = n
                gravar_config_usuario(dados)
        _ARQUIVO_ULTIMO_CLIENTE_LEGADO.unlink(missing_ok=True)
    except (json.JSONDecodeError, OSError):
        pass
    return dados


def salvar_memoria_ultimo_cliente(contratante: str, natureza_servico: str) -> None:
    """
    Grava o par contratante + natureza em `config_usuario.json` para reabrir na próxima execução.
    """
    dados = ler_config_usuario()
    dados[CHAVE_JSON_CONTRATANTE] = contratante.strip()
    dados[CHAVE_JSON_NATUREZA_SERVICO] = natureza_servico.strip()
    gravar_config_usuario(dados)


def ler_memoria_ultimo_cliente() -> tuple[str, str] | None:
    """
    Lê o último cliente gravado; devolve (contratante, natureza) ou None se inexistente/inválido.
    """
    dados = ler_config_usuario()
    c = str(dados.get(CHAVE_JSON_CONTRATANTE, "")).strip()
    n = str(dados.get(CHAVE_JSON_NATUREZA_SERVICO, "")).strip()
    if c and n:
        return c, n
    return None


def _limpar_memoria_ultimo_cliente() -> None:
    """Remove o último cliente memorizado de `config_usuario.json`."""
    dados = ler_config_usuario()
    alterado = False
    for chave in (CHAVE_JSON_CONTRATANTE, CHAVE_JSON_NATUREZA_SERVICO):
        if chave in dados:
            dados.pop(chave, None)
            alterado = True
    if alterado:
        gravar_config_usuario(dados)


def excluir_cliente_do_disco(
    caminho: Path,
    *,
    contratante: str,
    natureza_servico: str,
) -> None:
    """
    Remove o JSON do cliente e limpa a memória do último cliente se for o mesmo par chave.
    """
    if caminho.is_file():
        caminho.unlink()
    ultimo = ler_memoria_ultimo_cliente()
    if ultimo and ultimo[0] == contratante.strip() and ultimo[1] == natureza_servico.strip():
        _limpar_memoria_ultimo_cliente()


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
