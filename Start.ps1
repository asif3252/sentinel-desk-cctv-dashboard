$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$localPython = Join-Path $env:LOCALAPPDATA 'Python/bin/python.exe'
if (Test-Path '.venv/Scripts/python.exe') { & ./.venv/Scripts/python.exe server.py }
elseif (Test-Path $localPython) { & $localPython server.py }
else { py -3 server.py }
