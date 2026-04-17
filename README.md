# Gerar Relatório Diario de Obra (RDO) - Aplicação Desktop

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows)

Aplicação desktop para geração de Relatórios Diários de Obra (RDO) para projetos de engenharia e serviços no Brasil. Permite o registro detalhado de atividades diárias, controle de horários, cálculo automático de métricas de horas trabalhadas e exportação para planilhas Excel.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Configurações](#configurações)
- [Recursos Avançados](#recursos-avançados)
- [Solução de Problemas](#solução-de-problemas)
- [Contribuição](#contribuição)
- [Licença](#licença)

## Funcionalidades

### Interface Gráfica
- **Calendário Integrado**: Visualização mensal com destaques para dias preenchidos e feriados
- **Abas Organizadas**: Separação entre cabeçalhos fixos e relatórios diários
- **Auto-save**: Salvamento automático após 1.2 segundos de inatividade
- **Validação em Tempo Real**: Verificação de formatos de horário e duração

#### Aba de Cabeçalhos
![Aba de Cabeçalhos](Imagens%20Interface/Cabeçalhos.png)

#### Aba de Relatórios
![Aba de Relatórios](Imagens%20Interface/Relatórios.png)

### Registro de Atividades Diárias
- **Registro de Serviço**: Descrição detalhada das atividades realizadas
- **Registro Extra-Escopo**: Atividades fora do escopo contratual com controle de tempo
- **Registro de Ociosidade**: Períodos de inatividade com justificativa

### Controle de Horários
- **Ponto Eletrônico**: Entrada, saída para almoço, retorno e saída final
- **Deslocamento**: Controle de tempo de ida e volta ao local de trabalho
- **Formatação Automática**: Inserção automática de ":" nos horários (ex: 0830 → 08:30)

### Métricas de Horas
- **Horas Normais**: Cálculo baseado nas regras configuradas
- **Horas Extras 50%**: Sobretempo diurno
- **Horas Extras 100%**: Sobretempo noturno ou domingos/feriados
- **Adicional Noturno**: Horas trabalhadas entre 22:00 e 05:00
- **Relatórios Mensais**: Totais consolidados por mês


### Verificação Ortográfica e Gramatical
- **LanguageTool**: Correção automática em português brasileiro
- **Dicionário Pessoal**: Palavras e siglas específicas do projeto
- **Sugestões Contextuais**: Menu de contexto com correções sugeridas
- **Verificação Automática**: Análise em segundo plano após pausa na digitação

### Exportação para Excel
- **RDO (Relatório Diário de Obra)**: Planilha completa com todos os registros
- **FT (Folha de Tempo)**: Resumo mensal das horas trabalhadas
- **Templates Personalizáveis**: Modelos baseados em arquivos Excel de referência

### Suporte a Feriados Nacionais
- **Sincronização Automática**: Feriados brasileiros via biblioteca `holidays`
- **Configuração Flexível**: Regras personalizáveis para tipos de dia
- **Destaque Visual**: Dias de feriado marcados em vermelho no calendário

## Pré-requisitos

- **Sistema Operacional**: Windows 10 ou superior
- **Python**: Versão 3.8 ou superior
- **Conexão com Internet**: Necessária para verificação ortográfica (LanguageTool online)

## Instalação

### Instalação Automática (Recomendado)

1. **Baixe ou clone o repositório**:
   ```bash
   git clone https://github.com/seu-usuario/gerar-relatorio-rdo.git
   cd gerar-relatorio-rdo
   ```

2. **Execute o script de instalação**:
   - Clique duas vezes em `instalar_simples.bat`
   - Ou execute no terminal: `.\instalar_simples.bat`

O script irá:
- Verificar a instalação do Python
- Criar ambiente virtual (`.venv`)
- Instalar todas as dependências
- Iniciar a aplicação automaticamente

### Instalação Manual

1. **Verifique o Python**:
   ```bash
   python --version
   ```

2. **Crie o ambiente virtual**:
   ```bash
   python -m venv .venv
   ```

3. **Ative o ambiente virtual**:
   ```bash
   .venv\Scripts\activate
   ```

4. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

## Como Usar

### Início Rápido

1. **Execute a aplicação**:
   - Clique duas vezes em `executar.bat`
   - Ou: `python main.py`

2. **Primeiro uso**:
   - Crie um novo cliente clicando em "Novo cliente..."
   - Preencha o contratante e natureza do serviço
   - Configure os cabeçalhos fixos na aba "Cabeçalhos"

3. **Registro diário**:
   - Selecione uma data no calendário
   - Preencha os registros de serviço
   - Informe os horários de ponto
   - Os cálculos de horas são feitos automaticamente

### Fluxo de Trabalho

1. **Configuração Inicial**:
   - Acesse a aba "Cabeçalhos"
   - Preencha informações do projeto (empreendimento, contratante, etc.)

2. **Registro Diário**:
   - Selecione a data desejada no calendário
   - Descreva as atividades realizadas
   - Registre horários de entrada/saída
   - Adicione tempos de deslocamento se necessário

3. **Extra-Escopo e Ociosidade**:
   - Use campos específicos para atividades fora do escopo
   - Registre tempos consumidos nessas atividades

4. **Geração de Relatórios**:
   - Clique em "Gerar Excel (RDO/FT)"
   - Os arquivos serão salvos na pasta `saida_relatorios`

### Atalhos e Dicas

- **Auto-save**: A aplicação salva automaticamente após alterações
- **Calendário**: Dias verdes têm registros; vermelhos são feriados
- **Ortografia**: Clique com botão direito em palavras sublinhadas para correções
- **Dicionário**: Adicione termos técnicos no menu "Revisão > Dicionário pessoal"

## Estrutura do Projeto

```
Gerar_Relatorio/
├── main.py                          # Ponto de entrada da aplicação
├── requirements.txt                 # Dependências Python
├── compilar.bat                     # Script para compilação (futuro)
├── executar.bat                     # Script de execução
├── executar_sem_cmd.bat             # Execução sem manter terminal
├── executar.vbs                     # Execução invisível
├── instalar_simples.bat             # Instalação automatizada
├── rdo_diario/                      # Pacote principal
│   ├── __init__.py
│   ├── gui.py                       # Interface gráfica principal
│   ├── schema.py                    # Estrutura de dados JSON
│   ├── storage.py                   # Gerenciamento de arquivos
│   ├── paths.py                     # Definições de caminhos
│   ├── config_horas.py              # Regras de cálculo de horas
│   ├── calculo_metricas_horas.py    # Lógica de métricas
│   ├── horario_util.py              # Utilitários de horário
│   ├── gerar_excel_relatorios.py    # Exportação Excel
│   ├── verificacao_ortografia.py    # Integração LanguageTool
│   └── dicionario_ortografia_usuario.py # Dicionário pessoal
├── dados_rdo/                       # Dados do usuário
│   ├── _ultimo_cliente.json         # Último cliente usado
│   └── [cliente].json               # Arquivos de dados por cliente
├── template/                        # Templates e configurações
│   ├── _dicionario_ortografia.json  # Dicionário base
│   ├── config_regras_horas.json     # Regras de horas
│   ├── FT.xlsx                      # Template Folha de Tempo
│   ├── RDO.xlsx                     # Template RDO
│   └── mapa_celulas_excel.json      # Mapeamento de células
└── saida_relatorios/                # Relatórios gerados (criado automaticamente)
```

## Configurações

### Regras de Horas

As regras de cálculo de horas podem ser editadas em `template/config_regras_horas.json`:

- **Jornada diária**: Horas normais por dia
- **Intervalo mínimo**: Tempo mínimo de intervalo
- **Adicional noturno**: Percentual e horário
- **Feriados**: Regras específicas para feriados
- **Dias da semana**: Configurações por dia

### Feriados Nacionais

- Acesse "Horas > Sincronizar feriados nacionais (Brasil)..."
- Selecione o ano de referência
- Os feriados são baixados automaticamente

### Dicionário Ortográfico

- Menu "Revisão > Dicionário pessoal..."
- Adicione palavras e siglas específicas
- As comparações ignoram maiúsculas/minúsculas

## Recursos Avançados

### Cálculo de Métricas

O sistema calcula automaticamente:

- **Horas Trabalhadas**: Baseado nos horários de ponto
- **Horas Normais**: Dentro da jornada contratual
- **Extras 50%**: Sobretempo diurno
- **Extras 100%**: Noturno, domingos ou feriados
- **Adicional Noturno**: 22:00 às 05:00
- **Tempo de Serviço**: Horas trabalhadas menos extra-escopo e ociosidade

### Formato dos Dados

Os dados são armazenados em JSON estruturado:

```json
{
  "versao": 1,
  "chave": {
    "contratante": "Empresa XYZ",
    "natureza_servico": "Obras Civis"
  },
  "cabecalho_fixo": {
    "empreendimento": "Condomínio ABC",
    "contratante": "Empresa XYZ"
  },
  "registros_diarios": {
    "2024-01-15": {
      "registro_servico": "Execução de fundações...",
      "ponto_entrada": "08:00",
      "ponto_saida": "17:00",
      "metricas_horas": {
        "trabalhadas": 480,
        "normais": 480,
        "extra_50": 0,
        "extra_100": 0,
        "adicional_noturno": 0
      }
    }
  }
}
```

### Verificação Ortográfica

- **Serviço**: LanguageTool público (gratuito)
- **Limite**: Uso limitado por IP
- **Debounce**: Verificação após 2.8 segundos de pausa
- **Offline**: Funciona sem internet (verificação desabilitada)

## Solução de Problemas

### Problemas Comuns

**Erro ao instalar dependências:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**Aplicação não inicia:**
- Verifique se o ambiente virtual está ativado
- Execute: `python -c "import tkinter; print('Tkinter OK')"`

**Erro de codificação:**
- O projeto usa UTF-8
- Execute `chcp 65001` no terminal antes de usar

**Problemas com Excel:**
- Verifique se os templates estão na pasta `template/`
- Certifique-se de que o Excel não está bloqueando os arquivos

**Verificação ortográfica não funciona:**
- Verifique conexão com internet
- O serviço LanguageTool pode estar temporariamente indisponível

### Logs e Debug

Para debug avançado:
```bash
python main.py > debug.log 2>&1
```

### Limpeza de Dados

Para resetar completamente:
1. Delete a pasta `dados_rdo/`
2. Reinicie a aplicação (será criado um novo cliente)

## Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Diretrizes de Desenvolvimento

- **Python**: Use type hints e docstrings
- **Commits**: Mensagens claras em português
- **Testes**: Adicione testes para novas funcionalidades
- **Documentação**: Atualize o README para mudanças significativas

## Tecnologias Usadas

- **LanguageTool**: Para verificação ortográfica e gramatical
- **tkcalendar**: Para o componente de calendário
- **openpyxl**: Para manipulação de arquivos Excel
- **holidays**: Para feriados brasileiros

---

