@echo off
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%launch_quantumleap.ps1"
if %errorlevel% neq 0 (
  echo.
  echo Launch failed. Press any key to close...
  pause >nul
)
