@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ============================================================================
REM Compila o .exe (PyInstaller) e gera os artefactos da GitHub Release:
REM   dist\Gerar_Relatorio.exe
REM   dist\Gerar_Relatorio_<versão>.zip          (anexo da Release — só o .exe)
REM   dist\Gerar_Relatorio_<versão>.sha256.txt
REM   dist\RELEASE_v<versão>.md                 (rascunho de notas + checklist)
REM A versão é lida de template\sobre.json
REM ============================================================================

title Compilador RDO - PyInstaller + Release
set "PY=%~dp0.venv\Scripts\python.exe"

echo.
echo ===============================================================
echo   Gerar Relatório - Compilador .EXE + pacote Release
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

REM Chaves Gemini: sempre em template\.env (embutido no .exe pelo datas do template)
if not exist "template" mkdir template
if exist "template\.env" (
    echo ✓ template\.env encontrado — sera embutido no .exe
) else if exist ".env" (
    echo ⏳ Migrando .env da raiz para template\.env...
    copy /Y ".env" "template\.env" >nul
    if errorlevel 1 (
        echo ❌ ERRO: Nao foi possivel migrar .env para template\.env
        pause
        exit /b 1
    )
    del /F /Q ".env" >nul 2>&1
    echo ✓ template\.env pronto para embutir no .exe
) else (
    echo ⚠️  Aviso: template\.env nao encontrado.
    echo    O assistente IA exigira chaves em template\.env apos a primeira execucao.
)
echo.

REM Spec onefile + icone embutido
"%PY%" -m PyInstaller --noconfirm --clean Gerar_Relatorio.spec

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

if not exist "dist\Gerar_Relatorio.exe" (
    echo ❌ ERRO: dist\Gerar_Relatorio.exe nao foi gerado.
    pause
    exit /b 1
)

echo.
echo ===============================================================
echo ⏳ Preparando artefactos da GitHub Release...
echo ===============================================================
echo.

"%PY%" build_resources\preparar_release.py
if errorlevel 1 (
    echo.
    echo ❌ ERRO: Compilacao OK, mas falhou a geracao do pacote Release.
    echo    Verifique template\sobre.json ^(aplicacao.versao^) e dist\Gerar_Relatorio.exe
    pause
    exit /b 1
)

REM Lê a versão do sobre.json para mensagens finais
for /f "usebackq delims=" %%V in (`"%PY%" -c "import json; print(json.load(open(r'template/sobre.json', encoding='utf-8'))['aplicacao']['versao'])"`) do set "VERSAO=%%V"
if not defined VERSAO set "VERSAO=?"

echo.
echo ===============================================================
echo ✓ COMPILAÇÃO E PACOTE RELEASE CONCLUÍDOS
echo ===============================================================
echo.
echo 📁 Artefactos em dist\:
echo    Gerar_Relatorio.exe
echo    Gerar_Relatorio_%VERSAO%.zip          ^<-- anexar na GitHub Release
echo    Gerar_Relatorio_%VERSAO%.sha256.txt   ^(hashes opcionais^)
echo    RELEASE_v%VERSAO%.md                 ^(notas + checklist^)
echo.
echo 🏷️  Tag sugerida: v%VERSAO%
echo 📎 Anexe apenas o ZIP na Release ^(Latest^).
echo 📝 Abra dist\RELEASE_v%VERSAO%.md para copiar as notas e o checklist.
echo.
echo 📋 Na primeira execucao do .exe, ao lado do executavel sao criadas:
echo    template\  dados_rdo\  saida_relatorios\
echo.
echo 🔑 Chaves Gemini: ficam em template\.env ^(embutido no .exe se existir na compilacao^).
echo.
echo ⚠️  Nao faca commit de dist\ ^(esta no .gitignore^).
echo    Download publico: https://github.com/luisgustavoalmeida/Gerar_Relatorio/releases/latest
echo.
pause
