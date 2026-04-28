@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM Script para criar atalhos (symbolic links) das pastas necessárias
REM no diretório dist\Gerar_Relatorio\
REM ============================================================================

title Criador de Atalhos - Gerar Relatório

REM Verificar privilégios de administrador
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo ===============================================================
    echo   ⚠️  PRIVILÉGIOS DE ADMINISTRADOR NECESSÁRIOS
    echo ===============================================================
    echo.
    echo Este script precisa de privilégios de administrador para criar
    echo os symbolic links. Tentando re-executar com privilégios elevados...
    echo.

    REM Usar PowerShell para re-executar como administrador
    powershell -Command "Start-Process cmd -ArgumentList '/c, \"%~0\"' -Verb RunAs"
    exit /b 0
)

echo.
echo ===============================================================
echo   Gerar Relatório - Criador de Atalhos
echo ===============================================================
echo.

REM Obter diretório do script
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo Diretório base: %SCRIPT_DIR%
echo.

REM Definir caminhos absolutos
set "DIST_PATH=%SCRIPT_DIR%\dist\Gerar_Relatorio"
set "SAIDA_SRC=%SCRIPT_DIR%\saida_relatorios"
set "TEMPLATE_SRC=%SCRIPT_DIR%\template"
set "DADOS_SRC=%SCRIPT_DIR%\dados_rdo"

REM Verificar se a pasta dist\Gerar_Relatorio existe
if not exist "%DIST_PATH%" (
    echo ❌ ERRO: Pasta dist\Gerar_Relatorio não encontrada!
    echo    Caminho esperado: %DIST_PATH%
    echo    Execute primeiro o compilar.bat para gerar a estrutura
    pause
    exit /b 1
)

echo ✓ Pasta dist\Gerar_Relatorio encontrada
echo.

echo ⏳ Criando atalhos (symbolic links)...
echo.

REM Criar atalho para saida_relatorios
if not exist "%DIST_PATH%\saida_relatorios" (
    mklink /d "%DIST_PATH%\saida_relatorios" "%SAIDA_SRC%"
    if errorlevel 1 (
        echo ❌ ERRO ao criar atalho para saida_relatorios
    ) else (
        echo ✓ Atalho criado: saida_relatorios
    )
) else (
    echo ⚠️  saida_relatorios já existe
)

REM Criar atalho para template
if not exist "%DIST_PATH%\template" (
    mklink /d "%DIST_PATH%\template" "%TEMPLATE_SRC%"
    if errorlevel 1 (
        echo ❌ ERRO ao criar atalho para template
    ) else (
        echo ✓ Atalho criado: template
    )
) else (
    echo ⚠️  template já existe
)

REM Criar atalho para dados_rdo
if not exist "%DIST_PATH%\dados_rdo" (
    mklink /d "%DIST_PATH%\dados_rdo" "%DADOS_SRC%"
    if errorlevel 1 (
        echo ❌ ERRO ao criar atalho para dados_rdo
    ) else (
        echo ✓ Atalho criado: dados_rdo
    )
) else (
    echo ⚠️  dados_rdo já existe
)

echo.
echo ===============================================================
echo ✓ ATALHOS CRIADOS COM SUCESSO!
echo ===============================================================
echo.
echo 📁 Atalhos criados em:
echo    dist\Gerar_Relatorio\
echo.
echo 📋 Pastas vinculadas:
echo    - saida_relatorios
echo    - template
echo    - dados_rdo
echo.
echo Agora você pode executar o Gerar_Relatorio.exe normalmente!
echo.
pause

