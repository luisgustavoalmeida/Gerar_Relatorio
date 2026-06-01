@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

title Gerar Relatório RDO - Instalação

echo.
echo ===============================================================
echo   Gerar Relatório RDO - Instalação
echo ===============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado.
    echo Instale Python 3.12+ de https://www.python.org/
    pause
    exit /b 1
)

echo Python encontrado:
python --version
echo.

if not exist ".venv" (
    echo Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo ERRO: Falha ao criar .venv
        pause
        exit /b 1
    )
    echo Ambiente virtual criado.
) else (
    echo Ambiente virtual ja existe.
)
echo.

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo ERRO: %PY% nao encontrado.
    pause
    exit /b 1
)

echo Atualizando pip...
"%PY%" -m pip install --upgrade pip --quiet
echo.

echo Instalando dependencias...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo.

echo ===============================================================
echo Instalacao concluida. Iniciando a aplicacao...
echo ===============================================================
echo.

"%PY%" main.py
exit /b %errorlevel%
