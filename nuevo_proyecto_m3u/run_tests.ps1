param(
    [string]$VenvDir = ".venv"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonExe = Join-Path $ScriptDir "$VenvDir\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "No se encontró el entorno virtual en '$VenvDir'. Ejecuta primero .\setup_venv.ps1"
}

& $PythonExe -m pytest
