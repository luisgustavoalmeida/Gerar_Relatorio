@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"

echo ========================================
echo Reinstalando PyInstaller
echo ========================================
echo.

if not exist "%PY%" (
    echo ERRO: Ambiente virtual nao encontrado.
    echo Execute primeiro: instalar_simples.bat ou compilar.bat
    pause
    exit /b 1
)

"%PY%" --version
echo.

echo Desinstalando PyInstaller antigo...
"%PY%" -m pip uninstall pyinstaller -y

echo.
echo Instalando PyInstaller novamente...
"%PY%" -m pip install --force-reinstall pyinstaller

echo.
echo Verificando instalacao...
"%PY%" -m pip show pyinstaller

echo.
echo ========================================
echo PyInstaller foi reinstalado!
echo.
echo Agora execute: compilar.bat
echo ========================================
echo.
pause
