Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = "C:\Users\Yassir\AppData\Local\Programs\Python\Python310\pythonw.exe"
cmd = """" & pythonw & """ """ & scriptDir & "\supervisor.py"""
WshShell.Run cmd, 0, False
