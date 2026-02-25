$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$activateScript = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $activateScript)) {
    $installer = Join-Path $PSScriptRoot 'install_quantumleap.ps1'
    if (Test-Path $installer) {
        Write-Host 'App is not installed yet. Running installer first...'
        & $installer
    }
}

if (-not (Test-Path $activateScript)) {
    throw 'Virtual environment activation script not found after install. Ensure Python is installed correctly.'
}

. $activateScript

Write-Host 'Starting QuantumLeap Institutional Console...'
python -m streamlit run app.py
