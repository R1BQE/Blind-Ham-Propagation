@echo off
setlocal
start "" /b powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\run_windows.ps1"
exit /b 0
