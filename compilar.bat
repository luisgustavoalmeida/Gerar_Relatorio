@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ============================================================================
REM Script para compilar a aplicação em executável .EXE usando PyInstaller
REM ============================================================================

title Compilador RDO - PyInstaller
set "PY=%~dp0.venv\Scripts\python.exe"

echo.
echo ===============================================================
echo   Gerar Relatório - Compilador para .EXE
echo ===============================================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado!
    echo    Por favor, instale Python 3.12+ de https://www.python.org/
    pause
    exit /b 1
)

echo ✓ Python encontrado
echo.

REM Verificar/criar .venv
if not exist ".venv" (
    echo ⏳ Criando ambiente virtual...
    python -m venv .venv
    echo ✓ Ambiente virtual criado
) else (
    echo ✓ Ambiente virtual já existe
)
if not exist "%PY%" (
    echo ❌ ERRO: %PY% nao encontrado.
    pause
    exit /b 1
)
echo.

REM Atualizar pip
echo ⏳ Atualizando pip...
"%PY%" -m pip install --upgrade pip --quiet
echo ✓ pip atualizado
echo.

REM Instalar dependências do projeto
echo ⏳ Instalando dependências...
"%PY%" -m pip install -r requirements.txt --quiet
echo ✓ Dependências instaladas
echo.

REM Instalar PyInstaller
echo ⏳ Instalando PyInstaller...
"%PY%" -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo ❌ ERRO: Falha ao instalar PyInstaller
    pause
    exit /b 1
)
echo ✓ PyInstaller instalado
echo.

REM Limpar compilações anteriores
if exist "build" (
    echo ⏳ Limpando compilações anteriores...
    rmdir /s /q build >nul 2>&1
    echo ✓ Pasta 'build' removida
)
if exist "dist" (
    rmdir /s /q dist >nul 2>&1
    echo ✓ Pasta 'dist' removida
)
echo.

REM Compilar com PyInstaller
echo ===============================================================
echo ⏳ Compilando aplicação...
echo    (isso pode levar 1-2 minutos)
echo ===============================================================
echo.

echo ⏳ Preparando icone (varios tamanhos para o Explorer)...
"%PY%" -m pip install pillow --quiet
"%PY%" build_resources\preparar_icone.py
if errorlevel 1 (
    echo ❌ ERRO: Nao foi possivel gerar build_resources\icone_exe.ico
    pause
    exit /b 1
)
echo ✓ Icone: build_resources\icone_exe.ico
echo.

REM Spec onefile (mesmo modelo do Manipulador PDF) + icone embutido
"%PY%" -m PyInstaller --noconfirm --clean gerar_relatorio.spec

if errorlevel 1 (
    echo.
    echo ❌ ERRO: Falha ao compilar
    echo.
    echo ⚠️  Dica de troubleshooting:
    echo    - Verifique se PyInstaller foi instalado corretamente
    echo    - Tente novamente ou execute: reinstalar_pyinstaller.bat
    pause
    exit /b 1
)

echo.
echo ===============================================================
echo ✓ COMPILAÇÃO CONCLUÍDA COM SUCESSO!
echo ===============================================================
echo.
echo 📁 Executavel (onefile):
echo    dist\Gerar_Relatorio.exe
echo.
echo 📋 Na primeira execucao, ao lado do .exe sao criadas:
echo    template\  dados_rdo\  saida_relatorios\
echo.
echo ⚠️  Distribua o .exe; mantenha as pastas geradas na mesma pasta do executavel.
echo.
pause

