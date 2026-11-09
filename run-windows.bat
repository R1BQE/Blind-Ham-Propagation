@echo off
setlocal
git -C "%~dp0" pull --ff-only
if errorlevel 1 (
    echo.
    echo Git update failed. Check the repository and try again.
    pause
    exit /b 1
)
start "" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\run_windows.ps1"
exit /b 0
