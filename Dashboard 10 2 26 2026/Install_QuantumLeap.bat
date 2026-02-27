@echo off
set SCRIPT_DIR=%~dp0scripts\
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_quantumleap.ps1"
if %errorlevel% neq 0 (
  echo.
  echo Install failed. Press any key to close...
  pause >nul
)
