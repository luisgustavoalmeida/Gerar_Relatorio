@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo.
    echo ERRO: Ambiente virtual nao encontrado.
    echo Execute primeiro: instalar_simples.bat
    echo.
    pause
    exit /b 1
)

"%PY%" main.py
exit /b %errorlevel%
