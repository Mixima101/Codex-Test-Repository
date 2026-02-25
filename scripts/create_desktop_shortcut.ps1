$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptDir
$launcherScript = Join-Path $scriptDir 'launch_quantumleap.ps1'
if (-not (Test-Path $launcherScript)) {
    throw "Cannot find launcher script at: $launcherScript"
}

$powershellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not (Test-Path $powershellExe)) {
    $powershellExe = 'powershell.exe'
}

$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'QuantumLeap Institutional Console.lnk'

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powershellExe
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcherScript`""
$shortcut.WorkingDirectory = $env:USERPROFILE
$shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
$shortcut.Description = 'Launch QuantumLeap Institutional Console'
$shortcut.Save()

Write-Host "Desktop shortcut created/updated: $shortcutPath"
Write-Host "Shortcut target: $powershellExe"
Write-Host "Launcher script: $launcherScript"
