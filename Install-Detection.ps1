$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$localPython = Join-Path $env:LOCALAPPDATA 'Python/bin/python.exe'
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    if (Test-Path $localPython) { & $localPython -m venv .venv }
    else { py -3 -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 or 3.12, then retry.' }
}
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation failed. Check network access.' }
Write-Host 'Detection dependencies installed. Restart Start.ps1.'
