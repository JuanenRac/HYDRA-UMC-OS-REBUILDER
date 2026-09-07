' =============================================================================
' HYDRA-UMC-OS-REBUILDER - Silent Qt Quick desktop launcher: run-gui.vbs
' Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
' GPL-3.0 - see LICENSE
' =============================================================================
'
' This launcher is intentionally separate from run.bat: Windows starts a
' visible cmd.exe for any double-clicked .bat before its contents can run.
' WScript starts the venv's pythonw.exe directly, so this is the completely
' console-free double-click entry point for the graphical updater.
Option Explicit

Dim fileSystem, shell, root, pythonw, command
Set fileSystem = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fileSystem.GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"

If Not fileSystem.FileExists(pythonw) Then
    shell.Popup "HYDRA-UMC-OS-REBUILDER needs its GUI runtime first. Run build.bat once, then launch run-gui.vbs.", 0, "HYDRA-UMC-OS-REBUILDER", 48
    WScript.Quit 1
End If

command = Chr(34) & pythonw & Chr(34) & " -m hydra_umc_os_rebuilder.main"
shell.Run command, 0, False
