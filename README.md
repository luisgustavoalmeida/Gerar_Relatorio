# Gerar Relatório — Relatório Diário de Obra (RDO)

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Versão](https://img.shields.io/badge/Versão-1.0.7-informational.svg)](template/sobre.json)
[![Windows](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![Download](https://img.shields.io/github/v/release/luisgustavoalmeida/Gerar_Relatorio?label=Download)](https://github.com/luisgustavoalmeida/Gerar_Relatorio/releases/latest)

Aplicação desktop para registo de atividades diárias em projetos de engenharia e serviços em geral. Permite o registo detalhado de atividades, controlo de horários de ponto, cálculo automático de métricas de horas (normais, extras, noturno), assinatura e logo nas planilhas, assistente de reescrita com Google Gemini e exportação para Excel (RDO e Folha de Tempo).

**Versão atual:** 1.0.7 · **Formato dos dados (JSON):** 1 · **Plataforma:** Windows 10 ou superior

**Utilizadores finais (Windows):** baixe o executável em [Releases](https://github.com/luisgustavoalmeida/Gerar_Relatorio/releases/latest) — não é necessário instalar Python.

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

- **Seleção de projeto:** combobox no topo da janela (contratante + natureza do serviço); cada projeto tem um ficheiro JSON em `dados_rdo/`
- **Barra de menus CustomTkinter:** listas suspensas arredondadas (*Arquivo*, *Revisão*, *IA*, *Horas*, *Exibir*, *Ajuda*)
- **Abas:** *Cabeçalhos* (13 campos fixos, assinatura e logo), *Relatórios de trabalho* (calendário + métricas) e *Assistente IA*
- **Calendário partilhado:** a mesma coluna de calendário serve *Relatórios de trabalho* e *Assistente IA* — a data seleccionada aplica-se às duas abas
- **Tema claro/escuro:** alternância em *Exibir → Alternar tema claro/escuro*; preferência gravada em `template/config_usuario.json`; paleta editável em `template/tema_aplicacao.json`
- **Preferências locais unificadas:** `template/config_usuario.json` memoriza tema, geometria, aba aberta, último projeto e bloco `assistente_ia`; na primeira execução após actualização, importa automaticamente `_ultimo_cliente.json` ou `dados_rdo/config_usuario.json` se existirem
- **Geometria da janela:** tamanho e posição gravados automaticamente ao redimensionar ou mover a janela; na próxima execução, a janela reabre na mesma posição (se ainda couber no ecrã)
- **Aba memorizada:** a última aba seleccionada (*Cabeçalhos*, *Relatórios de trabalho* ou *Assistente IA*) é restaurada ao reabrir a aplicação
- **Campos de texto adaptáveis:** *Registro de serviço* cresce com a janela; *extra-escopo* e *ociosidade* expandem ao receber foco e recolhem ao sair
- **Desfazer/refazer:** `Ctrl+Z` e `Ctrl+Y` (ou `Ctrl+Shift+Z`) nos campos de texto e entradas
- **Assistente IA com Gemini:** rascunho por dia, reescrita com prompt 100% editável, rodízio persistente de chaves, histórico filtrável, contexto de cabeçalho seleccionável, **ficheiros de contexto por projeto** (Files API) e diálogo *Ver conversa com a API*
- **Painel de métricas rolável:** dia, mês e projeto cabem em ecrãs mais baixos (altura mínima 1075×700; abertura padrão 1075×900)
- **Auto-save:** gravação automática cerca de **1,2 s** após parar de digitar
- **Validação em tempo real:** formatação de horários (`0830` → `08:30`) e indicação visual de dias incompletos ou inválidos

![Aba Cabeçalhos — tema claro](Imagens%20Interface/Cabe%C3%A7alhos_tema_claro.png)

![Aba Cabeçalhos — tema escuro](Imagens%20Interface/Cabe%C3%A7alhos_tema_escuro.png)

*Aba **Cabeçalhos** — informações reutilizáveis, assinatura do funcionário e logo da empresa para as planilhas RDO e FT (temas claro e escuro).*

### Assinatura e logo da empresa

Na aba *Cabeçalhos*, abaixo dos 13 campos de texto:

- **Assinatura:** adicionar/remover imagem do funcionário (pré-visualização); ficheiro em `template/assinaturas/` nomeado pelo **Nome funcionário**
- **Logo empresa:** adicionar/remover logo da contratada; ficheiro em `template/logos/` nomeado pela **Contratada**
- **Exportação:** a assinatura é inserida no RDO (área de visto) e na FT (Emitente); o logo vai para o RDO em **C1:C5** — proporção preservada, sem alterar altura das linhas
- **Modelo de cabeçalho:** *Arquivo → Salvar / Carregar modelo de cabeçalho* inclui campos **e** as imagens, para reutilizar noutros projetos
- **Executável (.exe):** imagens e modelo ficam ao lado do `.exe` em `template/` (pastas graváveis)

![Aba Relatórios de trabalho — tema claro](Imagens%20Interface/Relat%C3%B3rios_tema_claro.png)

![Aba Relatórios de trabalho — tema escuro](Imagens%20Interface/Relat%C3%B3rios_tema_escuro.png)

*Aba **Relatórios de trabalho** — registo diário, horários de ponto, calendário com código de cores e métricas (dia, mês e projeto).*

![Aba Assistente IA — tema claro](Imagens%20Interface/Relat%C3%B3rios_assistente_IA_tema_claro.png)

![Aba Assistente IA — tema escuro](Imagens%20Interface/Relat%C3%B3rios_assistente_IA_tema_escuro.png)

*Aba **Assistente IA** — rascunho do dia, reescrita com Gemini e texto editável antes de aplicar no relatório (calendário e métricas partilhados; temas claro e escuro).*

#### Cores do calendário

| Cor | Significado |
|-----|-------------|
| **Azul** | Data selecionada para edição |
| **Negrito** | Dia de hoje |
| **Verde** | Registro de serviço **e** horários de ponto **válidos** (informações essenciais completas) |
| **Laranja** | Falta registro de serviço, horários incompletos ou horários que não respeitam as regras abaixo |
| **Sem destaque** | Nenhum registro de serviço nem horário preenchido naquele dia |
| **Vermelho** (número do dia) | Feriado nacional (fundo verde ou laranja se o dia também tiver dados, conforme o estado acima); passe o rato sobre o dia para ver o nome do feriado |

O calendário atualiza enquanto digita (antes do auto-save gravar no disco), refletindo o dia aberto no formulário. Clique no botão **+** no canto do painel do calendário para mostrar ou ocultar a legenda das cores.

### Registro de atividades diárias

- **Registro de serviço:** descrição detalhada das atividades realizadas
- **Assistente IA:** rascunho diário com autosave offline; reescrita via Gemini; texto editável antes de aplicar em *Registro serviço*, *extra-escopo* ou *ociosidade*
- **Registro extra-escopo:** atividades fora do escopo contratual, com tempo associado (h:mm)
- **Registro de ociosidade:** períodos de inatividade com justificativa e tempo (h:mm)
- **Tempo de serviço:** calculado automaticamente (horas trabalhadas − extra-escopo − ociosidade)
- **Numeração no mês:** cada dia com conteúdo recebe automaticamente `numero` (posição) e `folha` («X de Y») entre os relatórios preenchidos do mês; o rótulo **No mês:** ao lado da data reflecte o mesmo valor e estes campos são copiados para o Excel

### Controlo de horários

- **Ponto eletrônico:** Entrada, Saída almoço, Entrada almoço, Saída
- **Turno que atravessa meia-noite:** se a *Saída* for menor que a *Entrada* (ex.: 22:00→06:00), o sistema assume término no dia seguinte e conta horas e adicional noturno nos dois lados da meia-noite; com almoço, cada batida pode virar a meia-noite uma vez
- **Deslocamento:** Ida e Volta como **duração** do percurso (formato h:mm, ex.: `0:30`); não substituem entrada/saída para o dia ficar verde no calendário
- **Incluir Deslocamento:** caixa no formulário do dia; se marcada, a Folha de Tempo antecipa a Entrada pela Ida, atrasa a Saída pela Volta e inclui esse tempo nas horas da planilha e nas métricas; se desmarcada, o deslocamento fica só informativo (comportamento anterior)
- **Validação de ponto** (para o dia ficar **verde** no calendário):
  - **Entrada** e **Saída** são obrigatórias
  - **Sem intervalo de almoço:** deixe *Saída almoço* e *Entrada almoço* vazios; entrada e saída em ordem cronológica (com ou sem virada de dia)
  - **Com almoço:** preencha os quatro horários em ordem cronológica (entrada → saída almoço → entrada almoço → saída), permitindo no máximo uma virada de meia-noite por batida
  - Preencher só um dos campos de almoço, só entrada ou só saída, ou violar a ordem cronológica deixa o dia em **laranja**

### Métricas de horas

Painel *Métricas* abaixo do calendário (área rolável), com três blocos:

- **Métricas do dia:** horas trabalhadas, normais, extra 50%, extra 100%, adicional noturno e deslocamento do dia em edição
- **Métricas do mês:** totais do mês visível no calendário (dias com cálculo válido; deslocamento também soma quando preenchido)
- **Métricas do projeto:** totais acumulados de todos os meses com registos válidos (período e número de meses com dados)

Quando *Incluir Deslocamento* está marcado, trabalhadas, normais, extras e noturno incluem a Ida+Volta; o tópico **Deslocamento** continua a mostrar essa duração em separado.

Classificação com base em `template/config_regras_horas.json`:

- **Horas normais:** jornada normal configurada por dia da semana
- **Horas extras 50%:** sobretempo diurno após a jornada normal
- **Horas extras 100%:** restante ou conforme regras (noturno, domingos, feriados)
- **Adicional noturno:** horas entre 22:00 e 06:00 (configurável; suporte opcional à hora reduzida CLT; correcto em turnos que atravessam meia-noite)

O menu *Horas → Copiar relatório detalhado do mês (métricas)* copia o resumo mensal para a área de transferência.

### Verificação ortográfica e gramatical

- **LanguageTool** (API pública online, pt-BR) — sem pacote pip adicional; usa `urllib` da biblioteca padrão
- **Dicionário pessoal:** palavras e siglas específicas do projeto (`template/_dicionario_ortografia.json`)
- **Sugestões contextuais:** menu de contexto (botão direito) com correções sugeridas
- **Verificação automática:** análise em segundo plano após **2,8 s** de pausa na digitação
- **Âmbito:** campos do relatório diário e também rascunho / texto reescrito do Assistente IA e editor de prompts

### Assistente IA (Google Gemini)

- **Aba Assistente IA:** rascunho livre por data (campo `ia_rascunho` no JSON do projeto) e área de texto reescrito editável
- **Prompt 100% editável:** o texto enviado à API é o prompt global seleccionado em *IA → Configurações Gemini...*, mais o contexto operacional do dia (sem envelope fixo do sistema)
- **Histórico:** últimos N dias com `registro_servico` preenchido; filtro por mínimo de caracteres; opções para remover 1.º ou último parágrafo
- **Contexto do cabeçalho:** escolha quais campos do cabeçalho do projeto entram no prompt (padrão: só *Natureza do serviço*)
- **Chaves:** lista com Adicionar/Remover; botão **Criar chave no Google AI Studio** abre [a página oficial de chaves](https://aistudio.google.com/api-keys); gravadas em `template/.env` como `GEMINI_API_KEYS` (uma chave por linha); conta fixa ou **rodízio** (índice persistido entre sessões); em 429/cota a chave entra em cooldown e tenta a seguinte. Passo a passo em [Chaves Gemini (`.env`)](#chaves-gemini-env).
- **Anexos de contexto:** em *IA → Configurações Gemini...* pode adicionar vários ficheiros (PDF, imagem, texto, áudio, vídeo suportados pela API; máx. 10/projeto) ligados ao **projeto aberto**; checkbox global e por ficheiro; estado por chave (*pronto* / *precisa enviar* / *válido até…*); botões **Verificar na API**, **Limpar expirados** e **Abrir pasta**; envio pela [Files API](https://ai.google.dev/gemini-api/docs/files) (~48 h) com reenvio automático no rodízio; cópias em `dados_rdo/anexos_ia/`. Detalhes em [Anexos de contexto (Files API)](#anexos-de-contexto-files-api).
- **Modelo:** lista preenchida pela API (*Atualizar lista* / *Testar modelo*)
- **Prompt de fábrica:** `template/prompt_ia_padrao.txt` (inclui instruções para usar anexos como referência técnica); edições do utilizador ficam em `config_usuario.json`
- **Ver conversa:** *IA → Ver conversa com a API...* mostra o prompt completo e a resposta da última reescrita do dia seleccionado
- **Internet:** necessária apenas no momento da reescrita; o rascunho continua a gravar offline

### Exportação para Excel

- **RDO (Relatório Diário de Obra):** uma folha por dia com registro, a partir de `template/RDO.xlsx` (inclui logo, assinatura e data de geração)
- **FT (Folha de Tempo):** resumo mensal, a partir de `template/FT.xlsx` (inclui assinatura na área Emitente)
- **Mapeamento:** células definidas em `template/mapa_celulas_excel.json` (cabeçalho, campos diários, `assinatura`, `logo`, data de geração, `numero` e `folha`)
- **Saída:** `saida_relatorios/<contratante>/<natureza>/` com ficheiros nomeados por mês, tipo, natureza do serviço e funcionário — por exemplo `2026-05_RDO_Supervisorio_UHE_Rondon_Luis_Gustavo_de_Almeida.xlsx` e o equivalente `FT_...`
- **Por mês ou completo:** *Arquivo → Gerar Excel — mês em edição (RDO/FT)* exporta só o mês da data seleccionada no calendário; *Gerar Excel — todos os meses (RDO/FT)* gera **todos os meses** com dias que tenham conteúdo no JSON do projeto (texto, horários ou tempos)
- **FT e deslocamento:** na exportação da Folha de Tempo as métricas são recalculadas; com *Incluir Deslocamento* activo, os horários de ponto na planilha reflectem Ida/Volta e as colunas de horas usam o mesmo cálculo do painel de métricas

### Gestão de projetos

- **Novo projeto:** *Arquivo → Novo projeto* cria um JSON em `dados_rdo/` (contratante + natureza)
- **Editar chave:** *Arquivo → Editar chave do projeto* altera contratante e/ou natureza; renomeia o ficheiro JSON e actualiza o cabeçalho fixo (com validação de chave duplicada)
- **Arquivar:** *Arquivo → Arquivar projeto* move o JSON para `dados_rdo/rdo_arquivados/` (sai da lista do combobox; os relatórios Excel em `saida_relatorios/` mantêm-se)
- **Desarquivar:** *Arquivo → Desarquivar projeto* restaura um JSON de `rdo_arquivados/` para `dados_rdo/`
- **Excluir:** *Arquivo → Excluir projeto* remove o JSON e a pasta de relatórios Excel associada (irreversível)

> **Nota:** o repositório inclui `template/RDO.xlsx` e `template/FT.xlsx` para exportação dos relatórios.

### Feriados nacionais

- Sincronização via biblioteca `holidays` (Brasil)
- Menu *Horas → Sincronizar feriados nacionais* (atualiza ano anterior, ano corrente e ano seguinte)
- Regras de feriado configuráveis em `template/config_regras_horas.json`
- Dias de feriado marcados em vermelho no calendário; o nome do feriado aparece num balão ao passar o rato sobre o dia

## Pré-requisitos

- **Sistema operacional:** Windows 10 ou superior
- **Python:** 3.12 ou superior (para execução a partir do código-fonte)
- **Conexão com internet:** LanguageTool (ortografia) e Google Gemini (Assistente IA)
- **Chave(s) Gemini:** ficheiro `template/.env` com `GEMINI_API_KEYS` (uma chave por linha) — não versionado no Git
- **Microsoft Excel** ou compatível para abrir os relatórios gerados (`.xlsx`)

## Instalação

### Executável Windows (recomendado)

Para usar a aplicação **sem instalar Python**:

1. Abra a página de [Releases](https://github.com/luisgustavoalmeida/Gerar_Relatorio/releases/latest).
2. Em **Assets**, baixe o ficheiro **`Gerar_Relatorio_*.zip`** (ex.: `Gerar_Relatorio_1.0.7.zip`).
3. Extraia o zip para uma pasta de sua preferência (ex.: `Documentos\Gerar_Relatorio`).
4. Execute **`Gerar_Relatorio.exe`**.
5. (Opcional, Assistente IA) Confirme ou edite `template/.env` com as chaves Gemini — veja [Chaves Gemini (.env)](#chaves-gemini-env). O `compilar.bat` embute este ficheiro no `.exe`.

Na primeira execução são criadas, ao lado do `.exe`, as pastas `template/` (com modelos, `config_usuario.json`, `.env` se embutido, `assinaturas/` e `logos/`), `dados_rdo/` e `saida_relatorios/`. Mantenha-as na mesma pasta do executável.

> Os binários **não** ficam no repositório Git (`dist/` está no `.gitignore`). Cada versão publicada tem o [zip anexado na Release](https://github.com/luisgustavoalmeida/Gerar_Relatorio/releases/latest).

### Instalação a partir do código-fonte (desenvolvimento)

#### Automática

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

#### Manual

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

#### Atalhos de execução (Windows)

| Script | Descrição |
|--------|-----------|
| `executar.bat` | Ativa `.venv` e executa `python main.py` |
| `executar_sem_cmd.bat` | Execução via PowerShell oculto |
| `executar.vbs` | Execução sem janela de terminal visível |

## Como usar

### Início rápido

1. **Execute a aplicação** (`executar.bat` ou `python main.py`).

2. **Primeiro uso:**
   - Menu **Arquivo → Novo projeto** (ou diálogo automático ao abrir)
   - Preencha contratante e natureza do serviço
   - Configure os cabeçalhos fixos na aba **Cabeçalhos**

3. **Registo diário:**
   - Selecione uma data no calendário (destaque azul)
   - Preencha o **Registro de serviço** e os horários de **Entrada** e **Saída** (e almoço, se houver)
   - O dia fica **verde** quando as informações essenciais estão corretas; **laranja** indica pendência ou horário inválido
   - As métricas de horas são calculadas automaticamente quando os horários são válidos

4. **Gerar relatórios:**
   - Menu **Arquivo → Gerar Excel — mês em edição (RDO/FT)** para o mês da data seleccionada, ou **Gerar Excel — todos os meses (RDO/FT)** para exportar tudo
   - Os ficheiros são gravados em `saida_relatorios/`

### Fluxo de trabalho

1. **Configuração inicial:** aba *Cabeçalhos* — empreendimento, contratante, contratada, fiscalização, etc. (13 campos); opcionalmente assinatura e logo
2. **Modelo reutilizável:** *Arquivo → Salvar modelo de cabeçalho* / *Carregar modelo de cabeçalho* (`template/modelo_cabecalho.json` + imagens em `template/assinaturas/` e `template/logos/`)
3. **Registo diário:** selecione a data, descreva atividades, registe ponto e deslocamento
4. **Extra-escopo e ociosidade:** campos dedicados com tempo consumido
5. **Assistente IA (opcional):** *IA → Configurações Gemini...* (chaves e, se quiser, ficheiros de contexto do projeto) → aba *Assistente IA* → rascunho → *Reescrever com Gemini* → *Usar este texto* no campo desejado
6. **Exportação:** *Arquivo → Gerar Excel — mês em edição* ou *Gerar Excel — todos os meses*

### Atalhos e dicas

- **Auto-save:** grava após ~1,2 s de inatividade; *Arquivo → Salvar agora* força gravação imediata
- **Desfazer/refazer:** `Ctrl+Z` / `Ctrl+Y` nos campos editáveis
- **Janela e abas:** redimensione ou mova à vontade — geometria e aba activa são memorizadas para a próxima sessão
- **Contagem no mês** («No mês: X de Y»): posição cronológica do dia entre os dias com qualquer conteúdo no mês (alinhada a `numero` e `folha` no JSON e no Excel); as cores do calendário usam só registro de serviço e validação de ponto
- **Ortografia:** clique com o botão direito em palavras sublinhadas para correções (também no Assistente IA)
- **Dicionário:** *Revisão → Dicionário pessoal*
- **IA:** *IA → Configurações Gemini...* (chaves, rodízio, modelo, histórico, **ficheiros de contexto do projeto**, cabeçalho e prompts); *IA → Ver conversa com a API...* para inspeccionar o último pedido
- **Projetos:** troque no combobox superior; use *Arquivar* / *Desarquivar* para projectos concluídos; *Editar chave* se contratante ou natureza mudarem
- **Ajuda integrada:** *Ajuda → Manual* e *Ajuda → Sobre* (conteúdo editável em `template/manual.json` e `template/sobre.json`, sem recompilar)

## Menus da aplicação

### Arquivo

| Item | Função |
|------|--------|
| Salvar agora | Grava o JSON do projeto imediatamente |
| Novo projeto | Cria um novo projecto (novo ficheiro em `dados_rdo/`) |
| Editar chave do projeto (contratante + natureza) | Altera a chave e renomeia o JSON; actualiza cabeçalho fixo |
| Limpar informações do dia em edição | Apaga o registo do dia seleccionado |
| Excluir projeto | Remove o JSON, os anexos de contexto da IA e a pasta de relatórios Excel associada |
| Arquivar projeto | Move o JSON para `dados_rdo/rdo_arquivados/` (fora da lista vigente) |
| Desarquivar projeto | Restaura um JSON de `rdo_arquivados/` para `dados_rdo/` |
| Gerar Excel — mês em edição (RDO/FT) | Exporta RDO e FT do mês da data seleccionada no calendário |
| Gerar Excel — todos os meses (RDO/FT) | Exporta todos os meses com registos no projeto |
| Abrir pasta relatórios | Abre `saida_relatorios/` no explorador |
| Salvar / Carregar modelo de cabeçalho | Reutiliza cabeçalhos **e** imagens (assinatura/logo) entre projetos |
| Abrir Templates / Abrir dados (.json) | Abre pastas `template/` e `dados_rdo/` |

### Revisão

| Item | Função |
|------|--------|
| Verificar ortografia e gramática agora | Analisa os campos de texto do dia (inclui Assistente IA) |
| Dicionário pessoal | Edita termos aceites localmente |
| Sobre a verificação ortográfica | Informação sobre LanguageTool e privacidade |

### Horas

| Item | Função |
|------|--------|
| Editar regras de horas e feriados | Editor integrado de `config_regras_horas.json` |
| Sincronizar feriados nacionais | Importa feriados BR (biblioteca `holidays`) |
| Copiar relatório detalhado do mês (métricas) | Copia texto de métricas do mês para a área de transferência |
| Abrir pasta do arquivo de regras | Abre a pasta de `config_regras_horas.json` |

### IA

| Item | Função |
|------|--------|
| Ver conversa com a API... | Mostra o prompt completo e a resposta da última reescrita do dia seleccionado |
| Configurações Gemini... | Chaves (lista + link Google AI Studio), rodízio/conta fixa, modelo, histórico, **ficheiros de contexto do projeto aberto**, campos de cabeçalho e prompts globais |

### Exibir

| Item | Função |
|------|--------|
| Alternar tema claro/escuro | Troca a aparência da interface (tema, geometria, aba e último projeto gravados em `template/config_usuario.json`) |

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
├── Gerar_Relatorio.spec             # Spec PyInstaller (onefile)
├── LEIA-ME-PRIMEIRO.txt             # Resumo rápido de compilação
│
├── instalar_simples.bat             # Instalação automatizada (.venv + deps + execução)
├── instalar_dependencias.bat        # Instala dependências de requirements.txt (Python global)
├── executar.bat                     # Execução com .venv
├── executar_sem_cmd.bat / executar.vbs
├── compilar.bat                     # Build onefile com .venv local
├── reinstalar_pyinstaller.bat       # Reinstala PyInstaller no .venv
│
├── build_resources/                 # Ícone e pacote da GitHub Release
│   ├── preparar_icone.py
│   ├── preparar_release.py          # Zip versionado, SHA-256 e RELEASE_v*.md
│   └── icone_exe.ico
│
├── rdo_diario/                      # Pacote principal
│   ├── paths.py                     # Caminhos raiz, template, dados, saída
│   ├── schema.py                    # Estrutura JSON, validação do calendário
│   ├── storage.py                   # Leitura/gravação atómica por projeto
│   ├── ia_settings.py               # Preferências IA, .env e rodízio de chaves
│   ├── ia_service.py                # Chamadas Gemini (google-genai) e montagem do prompt
│   ├── ia_anexos.py                 # Ficheiros de contexto (Files API) por projeto
│   ├── assinaturas.py               # Imagens de assinatura (template/assinaturas/)
│   ├── logos.py                     # Logos da empresa (template/logos/)
│   ├── modelo_cabecalho.py          # Salvar/carregar modelo com imagens
│   ├── config_horas.py              # Regras de horas e feriados
│   ├── calculo_metricas_horas.py    # Normais, extras 50/100%, noturno
│   ├── horario_util.py              # Normalização HH:MM, jornada líquida
│   ├── gerar_excel_relatorios.py    # Exportação RDO/FT (openpyxl + imagens)
│   ├── verificacao_ortografia.py    # Integração LanguageTool (HTTP)
│   ├── dicionario_ortografia_usuario.py
│   ├── ajuda_conteudo.py            # Renderização Manual/Sobre a partir de JSON
│   └── gui/
│       ├── app.py                   # Janela principal (AplicacaoRdo)
│       ├── menu.py                  # Menus Arquivo, Revisão, IA, Horas, Exibir, Ajuda
│       ├── menu_barra.py            # Barra de menus CustomTkinter
│       ├── calendario.py            # Calendário mensal + métricas
│       ├── formulario_dia.py        # Formulário diário
│       ├── assistente_ia.py         # Aba Assistente IA e diálogo da conversa API
│       ├── ia_configuracoes.py      # Janela Configurações Gemini
│       ├── desfazer_refazer.py      # Ctrl+Z / Ctrl+Y em campos editáveis
│       ├── ortografia.py            # Debounce e menu de contexto
│       ├── tema.py                  # Paleta claro/escuro
│       ├── combo_suspenso.py        # Combobox aprimorado (CustomTkinter)
│       └── icone_janela.py          # Ícone da janela e barra de tarefas
│
├── dados_rdo/                       # Um JSON por projeto vigente
│   ├── anexos_ia/                   # Ficheiros de contexto da IA (por projeto)
│   └── rdo_arquivados/              # Projectos arquivados
│   ├── rdo_arquivados/              # Projetos arquivados (fora do combobox)
│   └── [Contratante_-_Natureza].json
│
├── template/
│   ├── .env                         # Chaves Gemini (local; não versionado; embutido no .exe)
│   ├── RDO.xlsx / FT.xlsx           # Modelos Excel
│   ├── mapa_celulas_excel.json      # Mapeamento JSON → células (incl. assinatura/logo)
│   ├── modelo_cabecalho.json        # Modelo reutilizável (campos + refs às imagens)
│   ├── assinaturas/                 # Imagens de assinatura do funcionário
│   ├── logos/                       # Logos da contratada
│   ├── config_regras_horas.json
│   ├── config_usuario.json          # Preferências locais + assistente_ia (não versionado)
│   ├── manual.json / sobre.json
│   ├── tema_aplicacao.json
│   └── _dicionario_ortografia.json
│
├── saida_relatorios/                # Excel gerados
└── Imagens Interface/               # Capturas para documentação
```

## Configurações

### Regras de horas

Ficheiro: `template/config_regras_horas.json` (versão **2** do formato de configuração)

- **dias_semana:** jornada normal, limite de extra 50%, extra 100%, adicional noturno por dia da semana
- **tipos_dia.feriado:** regras específicas para feriados
- **feriados.por_ano:** datas sincronizadas (menu *Horas → Sincronizar feriados nacionais*)
- **adicional_noturno:** horário de início/fim, hora reduzida CLT opcional (`incluir_hora_reduzida_clt`)

Edite pelo menu *Horas → Editar regras de horas e feriados* ou diretamente no ficheiro.

### Preferências locais (`config_usuario.json`)

Ficheiro em `template/config_usuario.json` (não versionado; específico de cada instalação):

| Chave | Conteúdo |
|-------|----------|
| `tema_aparencia` | `"dark"` ou `"light"` |
| `geometria_janela` | Tamanho e posição da janela (`LARGURAxALTURA±X±Y`) |
| `aba_ativa` | `"Cabeçalhos"`, `"Relatórios de trabalho"` ou `"Assistente IA"` |
| `contratante` / `natureza_servico` | Último projeto aberto |
| `assistente_ia` | Bloco de configuração do Gemini (ver abaixo) |

Bloco `assistente_ia` (editável também em *IA → Configurações Gemini...*):

| Chave | Conteúdo |
|-------|----------|
| `modelo` | ID do modelo Gemini (ex.: `gemini-2.5-flash`) |
| `modo_rotacao` | `"fixo"` ou `"rodizio"` |
| `indice_chave_ativa` | Índice da conta fixa |
| `indice_rodizio_proximo` | Próxima chave no rodízio (persistido entre sessões) |
| `dias_historico` | Quantos dias anteriores com `registro_servico` entram no prompt |
| `minimo_caracteres_historico` | Ignora dias de histórico abaixo deste tamanho (`0` = sem filtro) |
| `remover_primeiro_paragrafo` / `remover_ultimo_paragrafo` | Ajustes ao texto histórico |
| `campos_contexto_cabecalho` | Lista de campos do cabeçalho incluídos no prompt (padrão: `natureza_servico`) |
| `prompt_selecionado_id` / `prompts` | Biblioteca global de prompts editáveis |

Na primeira leitura após actualização, o ficheiro é importado automaticamente se existir em `dados_rdo/config_usuario.json` ou `_ultimo_cliente.json` (ficheiros legados removidos após migração).

### Chaves Gemini (`.env`)

As chaves **não** ficam em `config_usuario.json`. Ficam sempre em **`template/.env`** (variável **`GEMINI_API_KEYS`**, **uma chave por linha**), tanto em desenvolvimento como no `.exe`.

Para criar uma chave e cadastrá-la na aplicação:

1. Abra [Google AI Studio — chaves de API](https://aistudio.google.com/api-keys) e inicie sessão com a conta Google. Na aplicação, o mesmo endereço abre pelo botão **Criar chave no Google AI Studio**, em *IA → Configurações Gemini...*.
2. Se for a primeira vez, aceite os termos da API Gemini.
3. Clique em **Create API key** (Criar chave de API).
4. Escolha um projeto novo (o site pode criar um automaticamente) ou um projeto Google Cloud já existente. Não é preciso configurar pagamento para começar no plano gratuito.
5. Copie a chave (começa por `AIza`). Trate-a como uma senha.
6. Na aplicação, abra *IA → Configurações Gemini...*, cole a chave no campo **Nova chave** e clique em **Adicionar**.
7. Clique em **Guardar**. O ficheiro `template/.env` é atualizado sozinho.

Com mais de uma conta, repita os passos e, em **Execução**, escolha **Rodízio a cada reescrita**. Se uma conta atingir o limite (erro 429), a aplicação pausa essa chave e tenta a seguinte. O passo a passo também está no manual da aplicação: *Ajuda → Manual*, secção **7.2**.

```env
GEMINI_API_KEYS="
AIza...chave1
AIza...chave2
"
```

- Gestão pela UI: *IA → Configurações Gemini...* → lista Adicionar / Remover (grava `template/.env` automaticamente)
- O ficheiro está no `.gitignore` — não faça commit de chaves
- O `compilar.bat` embute `template/.env` no `.exe` junto com o resto da pasta `template/`
- Sem `.env` / sem chaves, o resto da aplicação funciona; só a reescrita Gemini fica indisponível

### Anexos de contexto (Files API)

Os ficheiros de contexto **não** são globais: ficam ligados ao **projeto aberto** no combobox (metadados em `ia_contexto_arquivos` no JSON; cópias em `dados_rdo/anexos_ia/<projeto>/`).

1. Abra o projeto desejado.
2. *IA → Configurações Gemini...* → secção **Contexto do projeto (ficheiros)**.
3. **Adicionar…** (PDF, imagem, texto, áudio ou vídeo suportados pela API; máx. 10 por projeto).
4. Marque **Usar ficheiros como contexto na reescrita** (e o checkbox de cada ficheiro).
5. **Salvar** / fechar e use *Reescrever com Gemini*.

Comportamento:

- A API **não** guarda conversa entre pedidos; em cada reescrita a app envia de novo o prompt (e referencia os ficheiros).
- Upload via [Files API](https://ai.google.dev/gemini-api/docs/files) (~48 h por chave Google). O estado na UI mostra se já está *pronto* nessa chave ou se *precisa enviar*.
- Com **rodízio**, se a chave seguinte ainda não tiver o URI, o app faz upload automaticamente antes de gerar.
- Botões **Verificar na API**, **Limpar expirados** e **Abrir pasta** ajudam a auditar e limpar metadados.
- O prompt de fábrica (`template/prompt_ia_padrao.txt`) já orienta o modelo a usar anexos só para terminologia/precisão, sem inventar factos fora do rascunho e dos anexos. Pode editar o prompt em *Configurações Gemini…*.

Ao **excluir** o projeto, a pasta de anexos correspondente é removida. Ao **renomear** a chave do projeto, a pasta e os caminhos são migrados.

### Tema e aparência da interface

- Menu *Exibir → Alternar tema claro/escuro* (preferência em `template/config_usuario.json`, chave `tema_aparencia`)
- Cores e estilos editáveis em `template/tema_aplicacao.json` (sem recompilar o executável)
- Tamanho, posição e aba activa gravados automaticamente; tamanho mínimo predefinido: 1075×700 px (abertura padrão 1075×900)

### Dicionário ortográfico

- Menu *Revisão → Dicionário pessoal*
- Termos guardados em `template/_dicionario_ortografia.json`
- Comparações ignoram maiúsculas/minúsculas

### Ajuda e Sobre

Edite `template/manual.json` e `template/sobre.json`; as alterações aparecem ao reabrir os diálogos *Ajuda → Manual* e *Ajuda → Sobre* (sem recompilar o executável, desde que a pasta `template/` esteja junto ao `.exe`).
Versão actual da aplicação: **1.0.7** (`template/sobre.json`).
## Recursos avançados

### Estado essencial do dia (calendário)

Lógica em `rdo_diario/schema.py` (`estado_informacoes_essenciais_dia`, `horarios_ponto_validos_no_registro`, `calcular_numero_e_folha_mes`, `mapa_numero_folha_por_mes`), reutilizando `calcular_minutos_jornada_liquida` em `horario_util.py`. Cálculo de métricas em `rdo_diario/calculo_metricas_horas.py` (`calcular_metricas_horas_para_dia`, `agregar_metricas_mes`, `agregar_metricas_totais`).

- **Completo (verde):** texto em *Registro de serviço* + ponto válido (entrada e saída, ordem cronológica)
- **Parcial (laranja):** só serviço, só horários, horários inválidos ou só deslocamento preenchido
- **Hoje (negrito):** dia actual destacado em negrito no calendário
- **Vazio:** sem registro de serviço e sem nenhum horário preenchido

### Formato dos dados (JSON)

Versão do formato: **1** (`schema.VERSAO_ARQUIVO`). Um ficheiro por projeto em `dados_rdo/` (projectos arquivados em `dados_rdo/rdo_arquivados/`):

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
      "numero": 3,
      "folha": "3 de 12",
      "ia_rascunho": "Anotações livres do dia...",
      "ia_ultima_resposta": "Relatório reescrito pelo Gemini...",
      "ia_prompt_id": "",
      "ia_prompt_nome": "",
      "metricas_horas": {
        "trabalhadas": 480,
        "normais": 480,
        "extra_50": 0,
        "extra_100": 0,
        "adicional_noturno": 0
      }
    }
  },
  "ia_contexto_arquivos": {
    "usar": true,
    "itens": [
      {
        "id": "abc123",
        "nome_original": "memorial.pdf",
        "caminho": "dados_rdo/anexos_ia/Empresa_XYZ_-_Obras_Civis/abc123_memorial.pdf",
        "mime": "application/pdf",
        "sha256": "...",
        "tamanho": 123456,
        "activo": true,
        "uploads": {}
      }
    ]
  },
  "meta": {
    "ultima_edicao_iso": "2026-01-15T18:30:00"
  }
}
```

A gravação usa ficheiro temporário (`.json.tmp`) e substituição atómica, reduzindo risco de corrupção em caso de falha durante o save. Os campos `numero` e `folha` são recalculados automaticamente para todos os dias com conteúdo do mês sempre que o registo diário é persistido.

### Verificação ortográfica

- **Serviço:** LanguageTool público (`https://api.languagetool.org/v2/check`, pt-BR)
- **Limite:** uso limitado por IP no serviço gratuito
- **Debounce:** verificação após 2,8 s de pausa
- **Offline:** funciona sem internet (verificação desactivada; resto da aplicação normal)

### Assistente IA e API Gemini

- Preferências em `template/config_usuario.json` → `assistente_ia`; chaves só em `template/.env`
- Anexos por projeto: `ia_contexto_arquivos` no JSON + `rdo_diario/ia_anexos.py` (Files API)
- Montagem do prompt e chamadas em `rdo_diario/ia_service.py`; rodízio e `.env` em `rdo_diario/ia_settings.py`
- Em erro 429/cota, a chave actual entra em cooldown e a aplicação tenta a seguinte automaticamente
- *IA → Ver conversa com a API...* mostra o último pedido/resposta do dia (útil para afinar o prompt)
- O histórico de dias anteriores é **local** (reenviado no prompt); a API não mantém conversa entre pedidos

## Compilação para executável (.exe)

A aplicação pode ser empacotada com **PyInstaller** (modo **onefile**, sem consola).

### Compilar

```cmd
compilar.bat
```

O script cria o `.venv` (se necessário), instala dependências de `requirements.txt` (inclui PyInstaller, Pillow e `google-genai`), gera o ícone em `build_resources/`, compila com `Gerar_Relatorio.spec` e, no fim, corre `build_resources/preparar_release.py` para montar o pacote da GitHub Release. A versão do zip e das notas vem de `template/sobre.json` (`aplicacao.versao`).

### Resultado

```
dist/
├── Gerar_Relatorio.exe                      # teste local
├── Gerar_Relatorio_<versão>.zip             # anexo da GitHub Release (só o .exe)
├── Gerar_Relatorio_<versão>.sha256.txt      # hashes SHA-256 (opcional anexar)
└── RELEASE_v<versão>.md                     # rascunho de notas + checklist (não anexar)
```

Na **primeira execução**, ao lado do `.exe` são criadas automaticamente as pastas `template/` (modelos Excel, ajuda, `config_usuario.json` de modelo, `.env` com chaves se embutido na compilação, `assinaturas/` e `logos/`), `dados_rdo/` e `saida_relatorios/` (copiadas do bundle interno). Mantenha estas pastas na mesma pasta do executável.

### Publicar uma versão (GitHub Release)

Não faça commit de `dist/` no Git. Após `compilar.bat`:

1. Confirme a versão e as notas em `template/sobre.json` (e o rascunho em `dist/RELEASE_vX.Y.Z.md`).
2. Faça push do código da versão para `main`.
3. Em GitHub → **Releases** → **Create a new release** (ou edite a release existente).
4. Use a tag `vX.Y.Z` (ex.: `v1.0.7`), cole as notas do ficheiro `RELEASE_v…md`, anexe **apenas** `dist/Gerar_Relatorio_*.zip` (opcional: o `.sha256.txt`) e publique como **Latest release**.
5. O download fica em: https://github.com/luisgustavoalmeida/Gerar_Relatorio/releases/latest

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

**Assistente IA / Gemini não responde:**
- Crie a chave em [Google AI Studio — chaves de API](https://aistudio.google.com/api-keys) e cadastre-a em *IA → Configurações Gemini...* (botão **Criar chave no Google AI Studio**, campo **Nova chave**, **Adicionar**, **Guardar**). O passo a passo está em [Chaves Gemini (`.env`)](#chaves-gemini-env)
- Confirme que existe `template/.env` (ao lado do `.exe` ou no projecto) com `GEMINI_API_KEYS`
- Teste o modelo em *IA → Configurações Gemini... → Testar modelo*
- Em cota esgotada (429), adicione outra chave ou aguarde o cooldown; o rodízio tenta a próxima automaticamente
- Use *IA → Ver conversa com a API...* para ver o erro devolvido pela API

**Anexos de contexto não entram na reescrita:**
- Confirme o projeto correcto no combobox e o checkbox **Usar ficheiros como contexto na reescrita**
- Veja o estado do ficheiro (*pronto* / *precisa enviar*); use **Verificar na API** ou aguarde a próxima reescrita (upload automático)
- Confirme que o ficheiro ainda existe em `dados_rdo/anexos_ia/` (**Abrir pasta**)
- PDF até ~50 MB; outros tipos conforme a API; máx. 10 ficheiros por projeto

**Exportação FT falha:**
- Confirme que `template/FT.xlsx` existe junto ao `.exe` (ou no repositório em desenvolvimento)

### Logs e debug

```bash
python main.py > debug.log 2>&1
```

### Limpeza de dados

Para recomeçar do zero:

1. Feche a aplicação
2. Apague os JSON de projeto em `dados_rdo/`, a pasta `dados_rdo/anexos_ia/` se quiser, e, se necessário, `dados_rdo/rdo_arquivados/` (opcional: `template/config_usuario.json` para repor preferências)
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
| **Python 3.12+ / CustomTkinter** | Interface gráfica principal (tema claro/escuro) |
| **tkcalendar** | Calendário mensal |
| **google-genai** | Assistente IA — reescrita com Google Gemini |
| **openpyxl** | Exportação RDO e Folha de Tempo |
| **holidays** | Feriados nacionais do Brasil |
| **LanguageTool** (API HTTP) | Ortografia e gramática online |
| **PyInstaller** | Compilação para `.exe` (`compilar.bat` / `Gerar_Relatorio.spec`) |
| **Pillow** | Assinatura/logo na interface e no Excel; ícone multi-tamanho do `.exe` |

Dependências em `requirements.txt`: `customtkinter`, `tkcalendar`, `google-genai`, `holidays`, `openpyxl`, `pyinstaller`, `pillow`.
