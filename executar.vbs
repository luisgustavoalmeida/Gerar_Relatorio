Set objShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = strPath

If Not CreateObject("Scripting.FileSystemObject").FolderExists(".venv") Then
    MsgBox "Erro: Ambiente virtual não encontrado!" & vbCrLf & "Execute primeiro: compilar_alternativo.bat ou iniciar.bat", vbCritical, "Gerar Relatório RDO"
    WScript.Quit 1
End If

REM Executar main.py diretamente sem passar pelo .bat
objShell.Run strPath & "\.venv\Scripts\python.exe " & strPath & "\main.py", 0, False

