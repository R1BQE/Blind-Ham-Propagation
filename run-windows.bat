@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 (
    echo.
    echo Cannot open the project directory.
    pause
    exit /b 1
)
git pull --ff-only
if errorlevel 1 (
    popd
    echo.
    echo Git update failed. Check the repository and try again.
    pause
    exit /b 1
)
popd
start "" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\run_windows.ps1"
exit /b 0
