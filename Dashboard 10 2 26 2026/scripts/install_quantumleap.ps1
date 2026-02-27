$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Progress -Activity 'QuantumLeap Setup' -Status 'Preparing installer' -PercentComplete 5

if (-not (Test-Path '.venv')) {
    Write-Host 'Creating virtual environment (.venv)...'
    python -m venv .venv
}

$activateScript = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $activateScript)) {
    throw 'Virtual environment activation script not found. Ensure Python is installed correctly.'
}

Write-Progress -Activity 'QuantumLeap Setup' -Status 'Activating virtual environment' -PercentComplete 25
. $activateScript

Write-Progress -Activity 'QuantumLeap Setup' -Status 'Upgrading pip' -PercentComplete 45
python -m pip install --upgrade pip

Write-Progress -Activity 'QuantumLeap Setup' -Status 'Installing dependencies' -PercentComplete 70
python -m pip install -r requirements.txt

$shortcutScript = Join-Path $PSScriptRoot 'create_desktop_shortcut.ps1'
if (Test-Path $shortcutScript) {
    Write-Progress -Activity 'QuantumLeap Setup' -Status 'Creating desktop shortcut' -PercentComplete 90
    & $shortcutScript
}

Write-Progress -Activity 'QuantumLeap Setup' -Status 'Launching app' -PercentComplete 100 -Completed
Write-Host 'Setup complete. Launching QuantumLeap Institutional Console...'
python -m streamlit run app.py --server.headless false
