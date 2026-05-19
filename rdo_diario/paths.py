"""
Caminhos fixos do projeto (pastas e ficheiros de estado local).
"""
from pathlib import Path

# Diretório raiz do repositório (pasta que contém `rdo_diario/`, `dados_rdo/`, etc.)
RAIZ_PROJETO: Path = Path(__file__).resolve().parent.parent

# Pasta onde ficam os JSON por cliente
PASTA_DADOS_RDO: Path = RAIZ_PROJETO / "dados_rdo"

# Ficheiro que memoriza o último cliente editado (contratante + natureza)
ARQUIVO_ULTIMO_CLIENTE_JSON: Path = PASTA_DADOS_RDO / "_ultimo_cliente.json"

# Palavras e siglas aceites pelo utilizador (filtro local sobre o LanguageTool)
ARQUIVO_DICIONARIO_ORTOGRAFIA_JSON: Path = RAIZ_PROJETO / "template" / "_dicionario_ortografia.json"

# Regras de jornada, extras, adicional noturno e feriados (editável pela aplicação)
ARQUIVO_CONFIG_REGRAS_HORAS_JSON: Path = RAIZ_PROJETO / "template" / "config_regras_horas.json"

# Mapeamento chaves JSON → células dos modelos Excel (editável pelo utilizador)
ARQUIVO_MAPA_CELULAS_EXCEL_JSON: Path = RAIZ_PROJETO / "template" / "mapa_celulas_excel.json"

# Modelo de cabeçalho padrão (JSON com dados reutilizáveis de cabeçalho)
ARQUIVO_MODELO_CABECALHO_JSON: Path = RAIZ_PROJETO / "template" / "modelo_cabecalho.json"

# Relatórios Excel gerados (RDO e FT por mês)
PASTA_SAIDA_RELATORIOS_EXCEL: Path = RAIZ_PROJETO / "saida_relatorios"
