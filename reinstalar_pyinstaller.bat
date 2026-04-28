@echo off
REM Reinstalar PyInstaller corretamente
REM Autor: Build Script
REM Data: 2026-04-27

echo ========================================
echo Reinstalando PyInstaller
echo ========================================
echo.

python --version

echo.
echo Desinstalando PyInstaller antigo...
pip uninstall pyinstaller -y

echo.
echo Instalando PyInstaller novamente...
pip install --force-reinstall pyinstaller

echo.
echo Verificando instalacao...
pip show pyinstaller

echo.
echo ========================================
echo PyInstaller foi reinstalado!
echo.
echo Agora execute: compilar_exe_global.bat
echo ========================================
echo.
pause

