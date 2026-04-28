@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM Script para compilar a aplicação em executável .EXE usando PyInstaller
REM ============================================================================

title Compilador RDO - PyInstaller

echo.
echo ===============================================================
echo   Gerar Relatório - Compilador para .EXE
echo ===============================================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado!
    echo    Por favor, instale Python 3.14+ de https://www.python.org/
    pause
    exit /b 1
)

echo ✓ Python encontrado
echo.

REM Verificar/criar .venv
if not exist ".venv" (
    echo ⏳ Criando ambiente virtual...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo ✓ Ambiente virtual criado
) else (
    echo ✓ Ambiente virtual já existe
    call .venv\Scripts\activate.bat
)
echo.

REM Atualizar pip
echo ⏳ Atualizando pip...
python -m pip install --upgrade pip --quiet
echo ✓ pip atualizado
echo.

REM Instalar dependências do projeto
echo ⏳ Instalando dependências...
pip install -r requirements.txt --quiet
echo ✓ Dependências instaladas
echo.

REM Instalar PyInstaller
echo ⏳ Instalando PyInstaller...
pip install pyinstaller --quiet
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

REM Ativar ambiente virtual antes de compilar
call .venv\Scripts\activate.bat

REM Usar python -m para executar PyInstaller (mais confiável)
pyinstaller --onedir ^
    --windowed ^
    --add-data "saida_relatorios;saida_relatorios" ^
    --add-data "template;template" ^
    --add-data "dados_rdo;dados_rdo" ^
    --collect-all tkcalendar ^
    --collect-all holidays ^
    --collect-all openpyxl ^
    --name "Gerar_Relatorio" ^
    main.py

if errorlevel 1 (
    echo.
    echo ❌ ERRO: Falha ao compilar
    echo.
    echo ⚠️  Dica de troubleshooting:
    echo    - Verifique se PyInstaller foi instalado corretamente
    echo    - Tente novamente ou use: compilar_alternativo.bat
    pause
    exit /b 1
)

echo.
echo ===============================================================
echo ✓ COMPILAÇÃO CONCLUÍDA COM SUCESSO!
echo ===============================================================
echo.
echo 📁 Localização do executável:
echo    dist\Gerar_Relatorio\Gerar_Relatorio.exe
echo.
echo 📋 Próximos passos:
echo    1. Teste o executável em dist\Gerar_Relatorio\
echo    2. Certifique-se que as pastas dados_rdo\ e template\ estão presentes
echo    3. Distribua o conteúdo de dist\Gerar_Relatorio\
echo.
echo ⚠️  IMPORTANTE:
echo    - As pastas dados_rdo\ e template\ devem estar junto ao .exe
echo    - Não mova o .exe para outro local sozinho
echo    - Distribua toda a pasta dist\Gerar_Relatorio\
echo.
pause

