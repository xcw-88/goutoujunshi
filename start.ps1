[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$nodeModules = Join-Path $frontendDir "node_modules"
$dataDir = Join-Path $repoRoot "data"
$logDir = Join-Path $dataDir "logs"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.12+ was not found. Install Python and reopen PowerShell."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js 20.9+ was not found. Install Node.js and reopen PowerShell."
}
if (-not (Test-Path -LiteralPath $backendPython)) {
    throw "Backend environment is missing. Run: cd backend; python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e '.[dev]'"
}
if (-not (Test-Path -LiteralPath $nodeModules)) {
    throw "Frontend dependencies are missing. Run: cd frontend; npm install"
}
if (-not (Test-Path -LiteralPath (Join-Path $backendDir ".env")) -and -not $env:GOUTOU_API_KEY) {
    Write-Warning "backend/.env is absent and GOUTOU_API_KEY is unset. The app will start; configure the model on the Settings page."
}

New-Item -ItemType Directory -Force -Path $logDir, (Join-Path $dataDir "uploads"), (Join-Path $dataDir "exports") | Out-Null
$npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source
$backendOut = Join-Path $logDir "backend.out.log"
$backendErr = Join-Path $logDir "backend.err.log"
$frontendOut = Join-Path $logDir "frontend.out.log"
$frontendErr = Join-Path $logDir "frontend.err.log"

$backendProcess = Start-Process -FilePath $backendPython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $backendDir -WindowStyle Hidden -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
$frontendProcess = Start-Process -FilePath $npmCommand -ArgumentList @("run", "dev") -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru

Start-Sleep -Seconds 2
if ($backendProcess.HasExited) {
    throw "Backend stopped during startup. See data/logs/backend.err.log"
}
if ($frontendProcess.HasExited) {
    throw "Frontend stopped during startup. See data/logs/frontend.err.log"
}

Write-Host ""
Write-Host "Goutoujunshi Web" -ForegroundColor Yellow
Write-Host ""
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:3000"
Write-Host "API Docs: http://127.0.0.1:8000/docs"
Write-Host ""
Write-Host "Press Ctrl+C to stop both services. Logs: data/logs/"

try {
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    throw "A service stopped unexpectedly. Check data/logs/."
}
finally {
    foreach ($process in @($backendProcess, $frontendProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            $process.Kill($true)
        }
    }
}

