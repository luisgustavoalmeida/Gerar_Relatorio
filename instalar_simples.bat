@echo off
REM ============================================================================
REM Script SIMPLIFICADO para testar onde está fechando
REM ============================================================================

cd /d "%~dp0"
chcp 65001 >nul
setlocal enabledelayedexpansion

title Gerar Relatório RDO - TESTE SIMPLES

cls
echo.
echo ===============================================================
echo   Gerar Relatório RDO - TESTE SIMPLES (SEM TIMEOUTS)
echo ===============================================================
echo.

echo ✓ Verificando Python...
python --version
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado
    pause
    exit /b 1
)
echo ✓ Python OK
pause

echo ✓ Verificando .venv...
if not exist ".venv" (
    echo ⏳ Criando .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ ERRO: Falha ao criar .venv
        pause
        exit /b 1
    )
)
echo ✓ .venv OK
pause

echo ✓ Ativando ambiente virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ERRO: Falha ao ativar
    pause
    exit /b 1
)
echo ✓ Ambiente ativado
pause

echo ✓ Atualizando pip...
python -m pip install --upgrade pip --quiet
echo ✓ pip OK
pause

echo ✓ Instalando dependências...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ ERRO: Falha ao instalar dependências
    pause
    exit /b 1
)
echo ✓ Dependências OK
pause

echo ✓ Verificando main.py...
if not exist "main.py" (
    echo ❌ ERRO: main.py não encontrado
    pause
    exit /b 1
)
echo ✓ main.py OK
pause

echo ✓ Todas as verificações passaram!
echo.
echo Pressione qualquer tecla para iniciar a aplicação...
pause

python main.py

set ERRO=%errorlevel%
echo.
echo Aplicação finalizada com código: %ERRO%
pause
exit /b %ERRO%

