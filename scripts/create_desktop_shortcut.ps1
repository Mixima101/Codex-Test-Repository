$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$target = Join-Path $scriptDir 'launch_quantumleap.bat'
if (-not (Test-Path $target)) {
    throw "Cannot find launcher at: $target"
}

$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'QuantumLeap Institutional Console.lnk'

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = Split-Path -Parent $target
$shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
$shortcut.Description = 'Launch QuantumLeap Institutional Console'
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath"
