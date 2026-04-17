@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM Script para criar ambiente virtual, instalar dependências e iniciar aplicação
REM ============================================================================

title Gerar Relatório RDO - Setup e Execução

echo.
echo ===============================================================
echo   Gerar Relatório RDO - Setup Automático
echo ===============================================================
echo.

REM Detectar arquitetura do sistema
for /f "tokens=2 delims==" %%a in ('wmic os get osarchitecture /value') do set "arch=%%a"
if "%arch%"=="64-bit" (
    set "python_url=https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe"
    set "installer=python-3.14.0-amd64.exe"
    set "python_dir=C:\Program Files\Python314"
) else (
    set "python_url=https://www.python.org/ftp/python/3.14.0/python-3.14.0.exe"
    set "installer=python-3.14.0.exe"
    set "python_dir=C:\Program Files (x86)\Python314"
)

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ⏳ Python não encontrado. Baixando e instalando Python 3.14.0...
    powershell -Command "Invoke-WebRequest -Uri '%python_url%' -OutFile '%installer%'"
    if errorlevel 1 (
        echo ❌ ERRO: Falha ao baixar Python. Verifique sua conexão com a internet.
        pause
        exit /b 1
    )
    echo ✓ Instalador baixado. Instalando...
    %installer% /quiet InstallAllUsers=1 PrependPath=1
    if errorlevel 1 (
        echo ❌ ERRO: Falha ao instalar Python
        pause
        exit /b 1
    )
    echo ✓ Python instalado com sucesso
    del %installer%
    REM Atualizar PATH na sessão atual
    set PATH=%PATH%;%python_dir%;%python_dir%\Scripts
)

echo ✓ Python encontrado:
python --version
echo.

REM Verificar e criar pasta .venv se não existir
if not exist ".venv" (
    echo ⏳ Criando ambiente virtual (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ ERRO: Falha ao criar ambiente virtual
        pause
        exit /b 1
    )
    echo ✓ Ambiente virtual criado com sucesso
) else (
    echo ✓ Ambiente virtual (.venv) já existe
)
echo.

REM Ativar ambiente virtual
echo ⏳ Ativando ambiente virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ERRO: Falha ao ativar ambiente virtual
    pause
    exit /b 1
)
echo ✓ Ambiente virtual ativado
echo.

REM Atualizar pip
echo ⏳ Atualizando pip...
python -m pip install --upgrade pip --quiet
echo ✓ pip atualizado
echo.

REM Instalar dependências
echo ⏳ Instalando dependências do requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ ERRO: Falha ao instalar dependências
    pause
    exit /b 1
)
echo ✓ Dependências instaladas com sucesso
echo.

REM Verificar se main.py existe
if not exist "main.py" (
    echo ❌ ERRO: Arquivo main.py não encontrado
    pause
    exit /b 1
)

REM Iniciar aplicação
echo ===============================================================
echo ✓ Setup concluído! Iniciando aplicação...
echo ===============================================================
echo.

python main.py

REM Se o programa fechar, mostrar mensagem
echo.
echo ===============================================================
echo A aplicação foi finalizada.
echo ===============================================================
pause
