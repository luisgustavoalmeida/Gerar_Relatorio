@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM Script para criar ambiente virtual, instalar dependências e iniciar aplicação
REM ============================================================================

title Gerar Relatório RDO - Setup e Execução

echo.
echo ===============================================================
echo   Gerar Relatório RDO - Setup Automático
echo ===============================================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado!
    echo    Por favor, instale Python 3.14+ de https://www.python.org/downloads/
    echo    Certifique-se de marcar "Add Python to PATH" durante a instalação.
    pause
    exit /b 1
)

echo ✓ Python encontrado:
python --version
echo.

REM Verificar e criar pasta .venv se não existir
if not exist ".venv" (
    echo ⏳ Criando ambiente virtual (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ ERRO: Falha ao criar ambiente virtual
        pause
        exit /b 1
    )
    echo ✓ Ambiente virtual criado com sucesso
) else (
    echo ✓ Ambiente virtual (.venv) já existe
)
echo.

REM Ativar ambiente virtual
echo ⏳ Ativando ambiente virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ERRO: Falha ao ativar ambiente virtual
    pause
    exit /b 1
)
echo ✓ Ambiente virtual ativado
echo.

REM Atualizar pip
echo ⏳ Atualizando pip...
python -m pip install --upgrade pip --quiet
echo ✓ pip atualizado
echo.

REM Instalar dependências
echo ⏳ Instalando dependências do requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ ERRO: Falha ao instalar dependências
    pause
    exit /b 1
)
echo ✓ Dependências instaladas com sucesso
echo.

REM Verificar se main.py existe
if not exist "main.py" (
    echo ❌ ERRO: Arquivo main.py não encontrado
    pause
    exit /b 1
)

REM Iniciar aplicação
echo ===============================================================
echo ✓ Setup concluído! Iniciando aplicação...
echo ===============================================================
echo.

python main.py

REM Se o programa fechar, mostrar mensagem
echo.
echo ===============================================================
echo A aplicação foi finalizada.
echo ===============================================================
pause

