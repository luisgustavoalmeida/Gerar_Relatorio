# Gerar Relatório — Relatório Diário de Obra (RDO)

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Versão](https://img.shields.io/badge/Versão-1.0.3-informational.svg)](template/sobre.json)
[![Windows](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows)

Aplicação desktop para registo de atividades diárias em projetos de engenharia e serviços no Brasil. Permite o registo detalhado de atividades, controlo de horários de ponto, cálculo automático de métricas de horas (normais, extras, noturno) e exportação para planilhas Excel (RDO e Folha de Tempo).

**Versão atual:** 1.0.3 · **Formato dos dados (JSON):** 1 · **Plataforma:** Windows 10 ou superior

## Sumário

- [Funcionalidades](#funcionalidades)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Como usar](#como-usar)
- [Menus da aplicação](#menus-da-aplicação)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Configurações](#configurações)
- [Recursos avançados](#recursos-avançados)
- [Compilação para executável (.exe)](#compilação-para-executável-exe)
- [Solução de problemas](#solução-de-problemas)
- [Contribuição](#contribuição)
- [Autor e contacto](#autor-e-contacto)
- [Tecnologias](#tecnologias)

## Funcionalidades

### Interface gráfica

- **Seleção de cliente:** combobox no topo da janela (contratante + natureza do serviço); cada cliente tem um ficheiro JSON em `dados_rdo/`
- **Abas:** *Cabeçalhos* (13 campos fixos reutilizáveis) e *Relatórios de trabalho* (formulário diário + calendário + métricas)
- **Auto-save:** gravação automática cerca de **1,2 s** após parar de digitar
- **Validação em tempo real:** formatação de horários (`0830` → `08:30`) e indicação visual de dias incompletos ou inválidos

![Aba Cabeçalhos — campos reutilizáveis para RDO e FT](Imagens%20Interface/Cabe%C3%A7alhos.png)

*Aba **Cabeçalhos** — informações reutilizáveis para as planilhas RDO e FT.*

![Aba Relatórios de trabalho — formulário diário, calendário e métricas](Imagens%20Interface/Relat%C3%B3rios.png)

*Aba **Relatórios de trabalho** — registo diário, horários de ponto, calendário com código de cores e métricas mensais.*

#### Cores do calendário

| Cor | Significado |
|-----|-------------|
| **Verde** | Registro de serviço **e** horários de ponto **válidos** (informações essenciais completas) |
| **Laranja** | Falta registro de serviço, horários incompletos ou horários que não respeitam as regras abaixo |
| **Azul** | Data selecionada para edição |
| **Sem destaque** | Nenhum registro de serviço nem horário preenchido naquele dia |
| **Vermelho** (número do dia) | Feriado nacional (fundo verde ou laranja se o dia também tiver dados, conforme o estado acima) |

O calendário atualiza enquanto digita (antes do auto-save gravar no disco), refletindo o dia aberto no formulário. A legenda acima do calendário explica o significado de cada cor.

### Registro de atividades diárias

- **Registro de serviço:** descrição detalhada das atividades realizadas
- **Registro extra-escopo:** atividades fora do escopo contratual, com tempo associado (h:mm)
- **Registro de ociosidade:** períodos de inatividade com justificativa e tempo (h:mm)
- **Tempo de serviço:** calculado automaticamente (horas trabalhadas − extra-escopo − ociosidade)

### Controlo de horários

- **Ponto eletrônico:** Entrada, Saída almoço, Entrada almoço, Saída
- **Deslocamento:** Ida e Volta (não substituem entrada/saída para o dia ficar verde no calendário)
- **Validação de ponto** (para o dia ficar **verde** no calendário):
  - **Entrada** e **Saída** são obrigatórias
  - **Sem intervalo de almoço:** deixe *Saída almoço* e *Entrada almoço* vazios; exige **Entrada** anterior à **Saída**
  - **Com almoço:** preencha os quatro horários em ordem cronológica estrita (entrada → saída almoço → entrada almoço → saída)
  - Preencher só um dos campos de almoço, só entrada ou só saída, ou violar a ordem cronológica deixa o dia em **laranja**

### Métricas de horas

Painel *Métricas de horas diárias e mensais* abaixo do calendário:

- **Horas normais:** com base nas regras em `template/config_regras_horas.json`
- **Horas extras 50%:** sobretempo diurno após a jornada normal
- **Horas extras 100%:** restante ou conforme regras (noturno, domingos, feriados)
- **Adicional noturno:** horas entre 22:00 e 06:00 (configurável; suporte opcional à hora reduzida CLT)
- **Totais mensais:** consolidados no painel e copiáveis via menu *Horas*

### Verificação ortográfica e gramatical

- **LanguageTool** (API pública online, pt-BR) — sem pacote pip adicional; usa `urllib` da biblioteca padrão
- **Dicionário pessoal:** palavras e siglas específicas do projeto (`template/_dicionario_ortografia.json`)
- **Sugestões contextuais:** menu de contexto (botão direito) com correções sugeridas
- **Verificação automática:** análise em segundo plano após **2,8 s** de pausa na digitação

### Exportação para Excel

- **RDO (Relatório Diário de Obra):** uma folha por dia com registro, a partir de `template/RDO.xlsx`
- **FT (Folha de Tempo):** resumo mensal, a partir de `template/FT.xlsx`
- **Mapeamento:** células definidas em `template/mapa_celulas_excel.json`
- **Saída:** `saida_relatorios/<contratante>/<natureza>/RDO_YYYY-MM.xlsx` e `FT_YYYY-MM.xlsx`
- Gera **todos os meses** que tenham registos no JSON do cliente (não apenas o mês visível no calendário)

> **Nota:** o repositório inclui `template/RDO.xlsx`. O ficheiro `template/FT.xlsx` é necessário para exportar a Folha de Tempo — coloque-o na pasta `template/` se ainda não existir no seu ambiente.

### Feriados nacionais

- Sincronização via biblioteca `holidays` (Brasil)
- Menu *Horas → Sincronizar feriados nacionais* (atualiza ano anterior, ano corrente e ano seguinte)
- Regras de feriado configuráveis em `template/config_regras_horas.json`
- Dias de feriado marcados em vermelho no calendário

## Pré-requisitos

- **Sistema operacional:** Windows 10 ou superior
- **Python:** 3.12 ou superior (para execução a partir do código-fonte)
- **Conexão com internet:** necessária para verificação ortográfica (LanguageTool online)
- **Microsoft Excel** ou compatível para abrir os relatórios gerados (`.xlsx`)

## Instalação

### Instalação automática (recomendado)

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/luisgustavoalmeida/Gerar_Relatorio.git
   cd Gerar_Relatorio
   ```

2. **Execute o script de instalação:**
   - Clique duas vezes em `instalar_simples.bat`
   - Ou no terminal: `.\instalar_simples.bat`

O script irá:

- Verificar a instalação do Python
- Criar o ambiente virtual (`.venv`)
- Instalar as dependências de `requirements.txt`
- Iniciar a aplicação

### Instalação manual

1. **Verifique o Python:**
   ```bash
   python --version
   ```

2. **Crie e ative o ambiente virtual:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute:**
   ```bash
   python main.py
   ```

### Atalhos de execução (Windows)

| Script | Descrição |
|--------|-----------|
| `executar.bat` | Ativa `.venv` e executa `python main.py` |
| `executar_sem_cmd.bat` | Execução via PowerShell oculto |
| `executar.vbs` | Execução sem janela de terminal visível |

## Como usar

### Início rápido

1. **Execute a aplicação** (`executar.bat` ou `python main.py`).

2. **Primeiro uso:**
   - Menu **Arquivo → Novo cliente** (ou diálogo automático ao abrir)
   - Preencha contratante e natureza do serviço
   - Configure os cabeçalhos fixos na aba **Cabeçalhos**

3. **Registo diário:**
   - Selecione uma data no calendário (destaque azul)
   - Preencha o **Registro de serviço** e os horários de **Entrada** e **Saída** (e almoço, se houver)
   - O dia fica **verde** quando as informações essenciais estão corretas; **laranja** indica pendência ou horário inválido
   - As métricas de horas são calculadas automaticamente quando os horários são válidos

4. **Gerar relatórios:**
   - Menu **Arquivo → Gerar Excel (RDO/FT)**
   - Os ficheiros são gravados em `saida_relatorios/`

### Fluxo de trabalho

1. **Configuração inicial:** aba *Cabeçalhos* — empreendimento, contratante, contratada, fiscalização, etc. (13 campos)
2. **Modelo reutilizável:** *Arquivo → Salvar modelo de cabeçalho* / *Carregar modelo de cabeçalho* (`template/modelo_cabecalho.json`)
3. **Registo diário:** selecione a data, descreva atividades, registe ponto e deslocamento
4. **Extra-escopo e ociosidade:** campos dedicados com tempo consumido
5. **Exportação:** *Arquivo → Gerar Excel (RDO/FT)* para todos os meses com dados

### Atalhos e dicas

- **Auto-save:** grava após ~1,2 s de inatividade; *Arquivo → Salvar agora* força gravação imediata
- **Contagem no mês** («No mês: X de Y»): posição cronológica entre dias com qualquer conteúdo; as cores do calendário usam só registro de serviço e validação de ponto
- **Ortografia:** clique com o botão direito em palavras sublinhadas para correções
- **Dicionário:** *Revisão → Dicionário pessoal*
- **Ajuda integrada:** *Ajuda → Manual* e *Ajuda → Sobre* (conteúdo editável em `template/manual.json` e `template/sobre.json`, sem recompilar)

## Menus da aplicação

### Arquivo

| Item | Função |
|------|--------|
| Salvar agora | Grava o JSON do cliente imediatamente |
| Novo cliente | Cria um novo projeto (novo ficheiro em `dados_rdo/`) |
| Limpar informações do dia em edição | Apaga o registo do dia selecionado |
| Excluir cliente | Remove o JSON do cliente e a pasta de relatórios Excel associada |
| Gerar Excel (RDO/FT) | Exporta todos os meses com registos |
| Abrir pasta relatórios | Abre `saida_relatorios/` no explorador |
| Salvar / Carregar modelo de cabeçalho | Reutiliza cabeçalhos entre clientes |
| Abrir Templates / Abrir dados (.json) | Abre pastas `template/` e `dados_rdo/` |

### Revisão

| Item | Função |
|------|--------|
| Verificar ortografia e gramática agora | Analisa os campos de texto do dia |
| Dicionário pessoal | Edita termos aceites localmente |
| Sobre a verificação ortográfica | Informação sobre LanguageTool e privacidade |

### Horas

| Item | Função |
|------|--------|
| Editar regras de horas (.json) | Editor integrado de `config_regras_horas.json` |
| Sincronizar feriados nacionais | Importa feriados BR (biblioteca `holidays`) |
| Copiar relatório detalhado do mês (métricas) | Copia texto de métricas do mês para a área de transferência |
| Abrir pasta do arquivo de regras | Abre a pasta de `config_regras_horas.json` |

### Ajuda

| Item | Função |
|------|--------|
| Manual | Conteúdo de `template/manual.json` |
| Sobre | Versão, autor, repositório e doação PIX (`template/sobre.json`) |

## Estrutura do projeto

```
Gerar_Relatorio/
├── main.py                          # Ponto de entrada (iniciar_aplicacao)
├── requirements.txt                 # Dependências Python
├── Gerar_Relatorio.spec             # Spec PyInstaller (gerado/atualizado na compilação)
├── COMPILAR_INSTRUCOES.md           # Guia detalhado de build .exe
├── LEIA-ME-PRIMEIRO.txt               # Resumo rápido de compilação
│
├── instalar_simples.bat             # Instalação automatizada (.venv + deps)
├── instalar_dependencias.bat        # Instala deps + PyInstaller (Python global)
├── executar.bat                     # Execução com .venv
├── executar_sem_cmd.bat / executar.vbs
├── compilar.bat                     # Build com .venv local
├── compilar_exe_global.bat          # Build com Python global + ícone
├── criar_atalhos.bat                # Atalhos para pastas junto ao .exe compilado
│
├── rdo_diario/                      # Pacote principal
│   ├── paths.py                     # Caminhos raiz, template, dados, saída
│   ├── schema.py                    # Estrutura JSON, validação do calendário
│   ├── storage.py                   # Leitura/gravação atómica por cliente
│   ├── config_horas.py              # Regras de horas e feriados
│   ├── calculo_metricas_horas.py    # Normais, extras 50/100%, noturno
│   ├── horario_util.py              # Normalização HH:MM, jornada líquida
│   ├── gerar_excel_relatorios.py    # Exportação RDO/FT (openpyxl)
│   ├── verificacao_ortografia.py    # Integração LanguageTool (HTTP)
│   ├── dicionario_ortografia_usuario.py
│   ├── ajuda_conteudo.py            # Renderização Manual/Sobre a partir de JSON
│   └── gui/
│       ├── app.py                   # Janela principal (AplicacaoRdo)
│       ├── menu.py                  # Menus Arquivo, Revisão, Horas, Ajuda
│       ├── calendario.py            # Calendário mensal + métricas
│       ├── formulario_dia.py        # Formulário diário
│       └── ortografia.py            # Debounce e menu de contexto
│
├── dados_rdo/                       # Um JSON por cliente
│   ├── _ultimo_cliente.json         # Último cliente aberto
│   └── [Contratante_-_Natureza].json
│
├── template/
│   ├── RDO.xlsx                     # Modelo RDO
│   ├── FT.xlsx                      # Modelo Folha de Tempo (necessário para export FT)
│   ├── mapa_celulas_excel.json      # Mapeamento JSON → células Excel
│   ├── config_regras_horas.json     # Regras de jornada, extras e noturno
│   ├── modelo_cabecalho.json        # Modelo reutilizável de cabeçalho
│   ├── _dicionario_ortografia.json
│   ├── manual.json                  # Manual (Ajuda → Manual)
│   └── sobre.json                   # Sobre (Ajuda → Sobre)
│
├── saida_relatorios/                # Relatórios Excel gerados (criada automaticamente)
└── Icone/                           # icone.ico / icone.png (compilação)
```

## Configurações

### Regras de horas

Ficheiro: `template/config_regras_horas.json` (versão **2** do formato de configuração)

- **dias_semana:** jornada normal, limite de extra 50%, extra 100%, adicional noturno por dia da semana
- **tipos_dia.feriado:** regras específicas para feriados
- **feriados.por_ano:** datas sincronizadas (menu *Horas → Sincronizar feriados nacionais*)
- **adicional_noturno:** horário de início/fim, hora reduzida CLT opcional (`incluir_hora_reduzida_clt`)

Edite pelo menu *Horas → Editar regras de horas (.json)* ou diretamente no ficheiro.

### Dicionário ortográfico

- Menu *Revisão → Dicionário pessoal*
- Termos guardados em `template/_dicionario_ortografia.json`
- Comparações ignoram maiúsculas/minúsculas

### Ajuda e Sobre

Edite `template/manual.json` e `template/sobre.json`; as alterações aparecem ao reabrir os diálogos *Ajuda → Manual* e *Ajuda → Sobre* (sem recompilar o executável, desde que a pasta `template/` esteja junto ao `.exe`).

## Recursos avançados

### Estado essencial do dia (calendário)

Lógica em `rdo_diario/schema.py` (`estado_informacoes_essenciais_dia`, `horarios_ponto_validos_no_registro`), reutilizando `calcular_minutos_jornada_liquida` em `horario_util.py`.

- **Completo (verde):** texto em *Registro de serviço* + ponto válido (entrada e saída, ordem cronológica)
- **Parcial (laranja):** só serviço, só horários, horários inválidos ou só deslocamento preenchido
- **Vazio:** sem registro de serviço e sem nenhum horário preenchido

### Formato dos dados (JSON)

Versão do formato: **1** (`schema.VERSAO_ARQUIVO`). Um ficheiro por cliente em `dados_rdo/`:

```json
{
  "versao": 1,
  "chave": {
    "contratante": "Empresa XYZ",
    "natureza_servico": "Obras Civis"
  },
  "cabecalho_fixo": {
    "natureza_servico": "Obras Civis",
    "empreendimento": "Condomínio ABC",
    "contratante": "Empresa XYZ",
    "endereco": "",
    "cidade": "",
    "estado": "",
    "inicio_contratual": "",
    "termino_contratual": "",
    "contratada": "",
    "nome_funcionario": "",
    "telefone": "",
    "fiscalizacao": "",
    "nome_fiscal": ""
  },
  "registros_diarios": {
    "2026-01-15": {
      "registro_servico": "Execução de fundações...",
      "ponto_entrada": "08:00",
      "ponto_saida_almoco": "12:00",
      "ponto_entrada_almoco": "13:00",
      "ponto_saida": "17:00",
      "metricas_horas": {
        "trabalhadas": 480,
        "normais": 480,
        "extra_50": 0,
        "extra_100": 0,
        "adicional_noturno": 0
      }
    }
  },
  "meta": {
    "ultima_edicao_iso": "2026-01-15T18:30:00"
  }
}
```

A gravação usa ficheiro temporário (`.json.tmp`) e substituição atómica, reduzindo risco de corrupção em caso de falha durante o save.

### Verificação ortográfica

- **Serviço:** LanguageTool público (`https://api.languagetool.org/v2/check`, pt-BR)
- **Limite:** uso limitado por IP no serviço gratuito
- **Debounce:** verificação após 2,8 s de pausa
- **Offline:** funciona sem internet (verificação desactivada; resto da aplicação normal)

## Compilação para executável (.exe)

A aplicação pode ser empacotada com **PyInstaller** (modo `--onedir`, sem consola).

### Opção rápida

```cmd
compilar_exe_global.bat
```

Ou, com ambiente virtual local:

```cmd
compilar.bat
```

### Resultado

```
dist/Gerar_Relatorio/
├── Gerar_Relatorio.exe
├── template/          # Modelos e configs (embutidos no build)
├── dados_rdo/
└── saida_relatorios/
```

As pastas `template/`, `dados_rdo/` e `saida_relatorios/` devem permanecer **junto ao `.exe`**. Detalhes adicionais em `COMPILAR_INSTRUCOES.md` e `LEIA-ME-PRIMEIRO.txt`.

## Solução de problemas

### Problemas comuns

**Erro ao instalar dependências:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**Aplicação não inicia:**
- Verifique se o ambiente virtual está activado
- Execute: `python -c "import tkinter; print('Tkinter OK')"`

**Erro de codificação:**
- O projecto usa UTF-8
- Execute `chcp 65001` no terminal antes de usar, se necessário

**Problemas com Excel:**
- Confirme que `template/RDO.xlsx` e `template/FT.xlsx` existem
- Feche ficheiros `.xlsx` abertos no Excel antes de exportar
- Verifique `template/mapa_celulas_excel.json` se células não forem preenchidas

**Verificação ortográfica não funciona:**
- Verifique ligação à internet
- O serviço LanguageTool pode estar temporariamente indisponível

**Exportação FT falha:**
- Coloque `FT.xlsx` em `template/` (modelo da Folha de Tempo)

### Logs e debug

```bash
python main.py > debug.log 2>&1
```

### Limpeza de dados

Para recomeçar do zero:

1. Feche a aplicação
2. Apague o conteúdo de `dados_rdo/` (ou ficheiros individuais de cliente)
3. Reinicie a aplicação

## Contribuição

1. Faça fork do projecto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit das alterações (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Diretrizes

- **Python:** type hints e docstrings
- **Commits:** mensagens claras em português
- **Documentação:** actualize o README para mudanças significativas

## Autor e contacto

| | |
|---|---|
| **Desenvolvedor** | Luís Gustavo de Almeida |
| **Organização** | Megawatt Sistemas |
| **E-mail profissional** | luis.gustavo@megawatt.net.br |
| **E-mail pessoal** | lga.gustavo.a@gmail.com |
| **LinkedIn** | [luís-gustavo-de-almeida](https://www.linkedin.com/in/luís-gustavo-de-almeida) |
| **Discord** | luisgustavoalmeida |
| **Repositório** | [github.com/luisgustavoalmeida/Gerar_Relatorio](https://github.com/luisgustavoalmeida/Gerar_Relatorio) |

Este software é **gratuito**. Se quiser apoiar o desenvolvimento, pode enviar uma doação voluntária via **PIX**:

**Chave PIX:** CPF 069.524.336-51

(A chave também está em `template/sobre.json`, editável sem recompilar.)

## Tecnologias

| Tecnologia | Uso |
|------------|-----|
| **Python 3.12+ / Tkinter** | Interface gráfica principal |
| **tkcalendar** | Calendário mensal |
| **openpyxl** | Exportação RDO e Folha de Tempo |
| **holidays** | Feriados nacionais do Brasil |
| **LanguageTool** (API HTTP) | Ortografia e gramática online |
| **PyInstaller** | Compilação para `.exe` (scripts de build) |

Dependências em `requirements.txt`: `tkcalendar`, `holidays`, `openpyxl`.
