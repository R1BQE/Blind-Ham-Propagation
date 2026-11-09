$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $env:TEMP "blind-ham-propagation"
$StdoutLog = Join-Path $LogDir "server.out.log"
$StderrLog = Join-Path $LogDir "server.err.log"
$Url = "http://127.0.0.1:8765/"

function Write-LauncherLog([string]$Message) {
    Add-Content -Path (Join-Path $LogDir "launcher.log") -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message)
}

function Show-LauncherError([string]$Message) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Message, "Blind-Ham Propagation", "OK", "Error") | Out-Null
}

try {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Set-Location $Root
    Write-LauncherLog "Starting update."

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git не найден. Установи Git for Windows и повтори запуск."
    }
    if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python 3 не найден. Установи Python 3.11 или новее."
    }

    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw "git pull завершился с ошибкой. Проверь launcher.log." }

    $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        Write-LauncherLog "Creating virtual environment."
        if (Get-Command py -ErrorAction SilentlyContinue) {
            py -3 -m venv (Join-Path $Root ".venv")
        } else {
            python -m venv (Join-Path $Root ".venv")
        }
        if ($LASTEXITCODE -ne 0) { throw "Не удалось создать .venv." }
    }

    Write-LauncherLog "Updating Python packages."
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Не удалось обновить pip." }
    & $VenvPython -m pip install --upgrade -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Не удалось установить зависимости. Проверь доступ к PyPI и логи." }

    # Do not start a second copy if this project's local server is already running.
    try {
        $Existing = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/v1/health" -TimeoutSec 2
        if ($Existing.service -eq "blind-ham-propagation") {
            Start-Process $Url
            Write-LauncherLog "An existing local instance was opened in the browser."
            exit 0
        }
    } catch {
        # No service is listening; start our own instance below.
    }

    $env:BLIND_HAM_LOCAL_SESSION = "1"
    $Server = Start-Process -FilePath $VenvPython -ArgumentList "-m backend.run_local" -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
    Write-LauncherLog ("Started server process PID {0}." -f $Server.Id)

    $Ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 1
        if ($Server.HasExited) { throw "Сервер завершился при запуске. Подробности: $StderrLog" }
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/v1/health" -TimeoutSec 2
            if ($Health.status -eq "ok") { $Ready = $true; break }
        } catch {}
    }
    if (-not $Ready) {
        Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue
        throw "Сервер не ответил за 60 секунд. Подробности: $StderrLog"
    }

    Start-Process $Url
    Write-LauncherLog "Browser opened. Waiting for local server to stop."
    while (-not $Server.HasExited) {
        Start-Sleep -Seconds 2
        $Server.Refresh()
    }
    Write-LauncherLog "Local server stopped."
}
catch {
    Write-LauncherLog ("ERROR: " + $_.Exception.Message)
    Show-LauncherError ($_.Exception.Message + "`n`nЛог запуска: " + (Join-Path $LogDir "launcher.log"))
}
