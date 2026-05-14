param(
    [string]$VenvDir = ".venv"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

python -m venv $VenvDir

$PythonExe = Join-Path $ScriptDir "$VenvDir\Scripts\python.exe"

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt

Write-Host "Entorno virtual listo en $VenvDir"
Write-Host "Para activarlo manualmente: .\$VenvDir\Scripts\Activate.ps1"
