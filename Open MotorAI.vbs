Option Explicit

Dim files, shell, root, python, launcher, command
Set files = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = files.GetParentFolderName(WScript.ScriptFullName)
python = files.BuildPath(root, ".venv\Scripts\pythonw.exe")
If Not files.FileExists(python) Then
    python = files.BuildPath(root, "backend\.venv\Scripts\pythonw.exe")
End If
If Not files.FileExists(python) Then
    python = files.BuildPath(root, ".venv\Scripts\python.exe")
End If
If Not files.FileExists(python) Then
    python = files.BuildPath(root, "backend\.venv\Scripts\python.exe")
End If
launcher = files.BuildPath(root, "scripts\start_motorai.py")
If Not files.FileExists(python) Or Not files.FileExists(launcher) Then
    MsgBox "The local MotorAI environment is missing. Restore the project's Python environment before starting.", 16, "MotorAI"
    WScript.Quit 1
End If
shell.CurrentDirectory = root
command = Chr(34) & python & Chr(34) & " " & Chr(34) & launcher & Chr(34)
shell.Run command, 0, False
