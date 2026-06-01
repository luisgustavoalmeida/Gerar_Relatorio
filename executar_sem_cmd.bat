@echo off
REM Script para executar a aplicação via PowerShell (sem janela cmd visível)

REM Verificar se ambiente virtual existe
if not exist ".venv" (
    powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Erro: Ambiente virtual não encontrado!', 'Gerar Relatório RDO', 'OK', 'Error')"
    exit /b 1
)

REM Executar via PowerShell (sem janela cmd visível)
powershell -WindowStyle Hidden -Command "& '.\executar.bat'"

