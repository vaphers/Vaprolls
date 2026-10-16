# run.ps1 - Launch SEO Auditer Web Dashboard and Go Engine
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# Determine Python runtime with installed packages
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
}
if (-not (Test-Path $PythonExe)) {
    $PyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PyCmd) {
        $PythonExe = $PyCmd.Source
    } else {
        Write-Error "Python executable not found."
        exit 1
    }
}

# 1. Ensure Go crawler binary is compiled
$GoBin = Join-Path $ProjectRoot "go-crawler\bin\crawler.exe"
if (-not (Test-Path $GoBin)) {
    $GoCmd = Get-Command go -ErrorAction SilentlyContinue
    if ($GoCmd) {
        Write-Host "Building Go High-Throughput Crawler..." -ForegroundColor Cyan
        Push-Location (Join-Path $ProjectRoot "go-crawler")
        go build -o bin\crawler.exe .\cmd\crawler
        Pop-Location
    }
}

# 2. Start Go Crawler background service if not already running on port 50051
if (Test-Path $GoBin) {
    $tcp = Test-NetConnection -ComputerName 127.0.0.1 -Port 50051 -InformationLevel Quiet -WarningAction SilentlyContinue
    if (-not $tcp) {
        Write-Host "Launching Go Crawl Service on :50051..." -ForegroundColor Green
        Start-Process -FilePath $GoBin -ArgumentList "--port=50051" -WindowStyle Hidden
    }
}

# 3. Ensure React frontend is built
$FrontendDir = Join-Path $ProjectRoot "frontend"
$FrontendDist = Join-Path $FrontendDir "dist"
if (Test-Path $FrontendDir) {
    if (-not (Test-Path $FrontendDist)) {
        Write-Host "Building React Frontend (Vite + Zustand + TanStack Virtual)..." -ForegroundColor Cyan
        Push-Location $FrontendDir
        npm run build
        Pop-Location
    }
}

# 4. Launch Python Web Application
Write-Host "Starting SEO Auditer on http://localhost:8000 ..." -ForegroundColor Green
& $PythonExe (Join-Path $ProjectRoot "main.py") $args

