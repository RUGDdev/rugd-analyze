# Start the local RUGD Intelligence pilot.
# Uses data\analyze.sqlite. Does not create an account, delete a business, or deploy.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "Python 3.12 was not found at $Python."
    Write-Host "Install Python 3.12 for this Windows user. Administrator rights are not required."
    Write-Host "The python command on this PC is the Windows Store stub. Do not use it."
    exit 1
}

$busy = $false
$probe = New-Object System.Net.Sockets.TcpClient
try {
    $wait = $probe.BeginConnect("127.0.0.1", 8765, $null, $null)
    if ($wait.AsyncWaitHandle.WaitOne(400, $false) -and $probe.Connected) {
        $busy = $true
    }
} catch {
    $busy = $false
} finally {
    $probe.Close()
}
if ($busy) {
    Write-Host "RUGD is already running at http://127.0.0.1:8765."
    Write-Host "This script will not start a second server. One SQLite file supports one process."
    Write-Host "To stop the running server, press Ctrl+C in the window that started it."
    exit 1
}

& $Python -c "import fpdf, pptx"
if ($LASTEXITCODE -ne 0) {
    Write-Host "The pitch-deck libraries are missing."
    Write-Host "From this folder, run:"
    Write-Host "  `"$Python`" -m pip install -r requirements.txt"
    exit 1
}

# Keep this process on the local pilot. Do not print environment values.
$env:PYTHONUNBUFFERED = "1"
Remove-Item Env:RUGD_ENV -ErrorAction SilentlyContinue
Remove-Item Env:RUGD_DATABASE -ErrorAction SilentlyContinue
Remove-Item Env:RUGD_BILLING_SIMULATION -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "RUGD Intelligence local pilot"
Write-Host "Database: data\analyze.sqlite (existing records are kept)"
Write-Host "Address:  http://127.0.0.1:8765"
Write-Host "This script does not create an account and does not set a password."
Write-Host "Register or sign in in the browser. No subscription is required."
Write-Host "Press Ctrl+C in this window to stop. Stopping does not delete saved businesses."
Write-Host ""

& $Python -m app
exit $LASTEXITCODE
