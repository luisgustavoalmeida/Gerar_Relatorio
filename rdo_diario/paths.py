"""
Caminhos fixos do projeto (pastas e ficheiros de estado local).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _raiz_projeto() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _pasta_bundle_pyinstaller() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def _resolver_pasta(nome: str) -> Path:
    """Pasta ao lado do .exe; senão conteúdo embutido no onefile."""
    local = RAIZ_PROJETO / nome
    if local.exists():
        return local
    bundle = _pasta_bundle_pyinstaller()
    if bundle is not None:
        embutido = bundle / nome
        if embutido.exists():
            return embutido
    return local


def resolver_arquivo_icone_janela() -> Path | None:
    """Caminho do .ico para barra de tarefas (bundle do .exe, repo em dev, ou CustomTkinter)."""
    candidatos: list[Path] = []
    bundle = _pasta_bundle_pyinstaller()
    if bundle is not None:
        candidatos.append(bundle / "build_resources" / "icone_exe.ico")
    if not getattr(sys, "frozen", False):
        candidatos.append(RAIZ_PROJETO / "build_resources" / "icone_exe.ico")
    try:
        import customtkinter

        candidatos.append(
            Path(customtkinter.__file__).resolve().parent
            / "assets"
            / "icons"
            / "CustomTkinter_icon_Windows.ico"
        )
    except ImportError:
        pass
    for caminho in candidatos:
        if caminho.is_file():
            return caminho.resolve()
    return None


def garantir_pastas_executavel() -> None:
    """
    No .exe onefile, copia template/dados/saida do bundle para a pasta do executável
    (gravável). Só cria o que ainda não existir ao lado do .exe.
    """
    if not getattr(sys, "frozen", False):
        return
    bundle = _pasta_bundle_pyinstaller()
    if bundle is None:
        return
    raiz_bundle = Path(bundle)
    for nome in ("template", "dados_rdo", "saida_relatorios"):
        origem = raiz_bundle / nome
        if not origem.is_dir():
            continue
        destino = RAIZ_PROJETO / nome
        if not destino.exists():
            shutil.copytree(origem, destino)
            continue
        if nome != "template":
            destino.mkdir(parents=True, exist_ok=True)
            continue
        # Template já presente: evita varrer o bundle em cada arranque (onefile).
        if (destino / "RDO.xlsx").is_file():
            continue
        for ficheiro in origem.rglob("*"):
            if not ficheiro.is_file():
                continue
            relativo = ficheiro.relative_to(origem)
            alvo = destino / relativo
            if not alvo.is_file():
                alvo.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ficheiro, alvo)


# Diretório raiz do repositório ou pasta do .exe compilado
RAIZ_PROJETO: Path = _raiz_projeto()

# Pasta onde ficam os JSON por cliente
PASTA_DADOS_RDO: Path = RAIZ_PROJETO / "dados_rdo"

# Projetos arquivados (fora da lista de clientes vigentes)
PASTA_RDO_ARQUIVADOS: Path = PASTA_DADOS_RDO / "rdo_arquivados"

# Modelos Excel, regras de horas e ficheiros de ajuda
PASTA_TEMPLATE: Path = _resolver_pasta("template")

# Preferências locais (tema, geometria da janela, último cliente aberto)
ARQUIVO_CONFIG_USUARIO_JSON: Path = PASTA_TEMPLATE / "config_usuario.json"

# Palavras e siglas aceites pelo utilizador (filtro local sobre o LanguageTool)
ARQUIVO_DICIONARIO_ORTOGRAFIA_JSON: Path = _resolver_pasta("template") / "_dicionario_ortografia.json"

# Regras de jornada, extras, adicional noturno e feriados (editável pela aplicação)
ARQUIVO_CONFIG_REGRAS_HORAS_JSON: Path = _resolver_pasta("template") / "config_regras_horas.json"

# Mapeamento chaves JSON → células dos modelos Excel (editável pelo utilizador)
ARQUIVO_MAPA_CELULAS_EXCEL_JSON: Path = _resolver_pasta("template") / "mapa_celulas_excel.json"

# Modelo de cabeçalho padrão (JSON com dados reutilizáveis de cabeçalho)
ARQUIVO_MODELO_CABECALHO_JSON: Path = _resolver_pasta("template") / "modelo_cabecalho.json"

# Conteúdos do menu Ajuda (editáveis sem recompilar)
ARQUIVO_MANUAL_AJUDA_JSON: Path = _resolver_pasta("template") / "manual.json"
ARQUIVO_SOBRE_AJUDA_JSON: Path = _resolver_pasta("template") / "sobre.json"

# Paleta CustomTkinter da aplicação
ARQUIVO_TEMA_APLICACAO_JSON: Path = PASTA_TEMPLATE / "tema_aplicacao.json"

# Relatórios Excel gerados (RDO e FT por mês)
PASTA_SAIDA_RELATORIOS_EXCEL: Path = RAIZ_PROJETO / "saida_relatorios"
