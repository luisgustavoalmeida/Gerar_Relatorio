@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM Script rápido para executar a aplicação (sem reinstalar dependências)
REM ============================================================================

title Gerar Relatório RDO



REM Verificar se .venv existe
if not exist ".venv" (
    echo ⚠️  Ambiente virtual não encontrado!
    echo    Execute primeiro: instalar_simples.bat
    pause
    exit /b 1
)

REM Ativar ambiente virtual
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ERRO: Falha ao ativar ambiente virtual
    pause
    exit /b 1
)

REM Verificar se main.py existe
if not exist "main.py" (
    echo ❌ ERRO: Arquivo main.py não encontrado
    pause
    exit /b 1
)

REM Iniciar aplicação

python main.py


