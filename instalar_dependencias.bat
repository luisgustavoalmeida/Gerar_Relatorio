@echo off
REM Instalar todas as dependências necessárias
REM Execute este arquivo uma única vez

echo ========================================
echo Instalando dependências do projeto...
echo ========================================
echo.

REM Instalar pip (se não tiver)
python -m pip install --upgrade pip

REM Instalar dependências do projeto
echo Instalando dependências de requirements.txt...
pip install -r requirements.txt

REM Instalar PyInstaller para compilação
echo Instalando PyInstaller...
pip install pyinstaller

echo.
echo ========================================
echo Instalação concluída!
echo Agora você pode executar: compilar_exe.bat
echo ========================================
pause

