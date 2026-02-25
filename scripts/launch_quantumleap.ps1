$ErrorActionPreference = 'Stop'

$shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'QuantumLeap Institutional Console.lnk'
$shortcutScript = Join-Path $PSScriptRoot 'create_desktop_shortcut.ps1'
if ((-not (Test-Path $shortcutPath)) -and (Test-Path $shortcutScript)) {
    Write-Host 'Creating desktop shortcut...'
    & powershell -NoProfile -ExecutionPolicy Bypass -File $shortcutScript
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path '.venv')) {
    Write-Host 'Creating virtual environment (.venv)...'
    python -m venv .venv
}

$activateScript = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $activateScript)) {
    throw 'Virtual environment activation script not found. Ensure Python is installed correctly.'
}

. $activateScript

Write-Host 'Upgrading pip...'
python -m pip install --upgrade pip

Write-Host 'Installing dependencies from requirements.txt...'
python -m pip install -r requirements.txt

Write-Host 'Starting QuantumLeap Institutional Console...'
python -m streamlit run app.py
