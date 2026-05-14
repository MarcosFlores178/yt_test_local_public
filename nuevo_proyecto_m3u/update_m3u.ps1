param(
    [string]$Config = "config.json"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

python generate.py --config $Config
python revive.py --config $Config

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "run.log" -Value "$timestamp`: Proceso de generacion y revive completado."
