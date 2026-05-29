@echo off
REM Compilar para .exe usando Python global do sistema
REM Autor: Build Script
REM Data: 2026-04-27

echo ========================================
echo Compilando Gerar_Relatorio para .exe
echo ========================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não está instalado ou não está no PATH!
    echo.
    echo Solução:
    echo 1. Instale Python de: https://www.python.org/downloads/
    echo 2. Certifique-se de marcar "Add Python to PATH" durante instalação
    echo.
    pause
    exit /b 1
)

echo Usando Python instalado no sistema:
python --version
echo.

REM Instalar PyInstaller globalmente
echo.
echo Instalando PyInstaller (pode levar alguns minutos)...
echo.
pip install --upgrade pip
pip install pyinstaller
pip install -r requirements.txt

if errorlevel 1 (
    echo ERRO: Falha ao instalar dependências!
    pause
    exit /b 1
)

echo.
echo Verificacao concluida!

REM Limpar compilações anteriores
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Comando PyInstaller com --onedir
echo.
echo ========================================
echo Iniciando compilação (pode demorar 2-5 minutos)
echo ========================================
echo.

REM Comando PyInstaller com --onedir
echo.
echo ========================================
echo Iniciando compilacao (pode demorar 2-5 minutos)
echo ========================================
echo.

REM Tentar com pyinstaller diretamente
pyinstaller --onedir ^
    --windowed ^
    --icon "Icone\icone.ico" ^
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
    echo Tentando novamente com python -m PyInstaller...
    echo.

    python -m PyInstaller --onedir ^
        --windowed ^
        --icon "Icone\icone.ico" ^
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
        echo ERRO: Compilacao falhou!
        echo.
        echo Tente manualmente:
        echo pip install --force-reinstall pyinstaller
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo SUCESSO! Compilacao concluida!
echo ========================================
echo.
echo EXECUTAVEL: dist\Gerar_Relatorio\Gerar_Relatorio.exe
echo.
echo PROXIMAS ACOES:
echo 1. Abra a pasta: dist\Gerar_Relatorio\
echo 2. Duplo-clique em: Gerar_Relatorio.exe
echo 3. Os relatorios gerados ficarao em: saida_relatorios/
echo.
echo Dica: Coloque um atalho de Gerar_Relatorio.exe no Desktop
echo para facil acesso!
echo.
pause

