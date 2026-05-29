@echo off
setlocal enabledelayedexpansion
title Octane Light Denoiser - Uninstaller

echo ============================================================
echo   Octane Light Denoiser - Uninstaller
echo ============================================================
echo.

set "MAXON=%APPDATA%\Maxon"
set /a COUNT=0
if exist "%MAXON%" (
  for /d %%D in ("%MAXON%\*") do (
    if exist "%%D\plugins\OctaneLightDenoiser\" (
      rmdir /s /q "%%D\plugins\OctaneLightDenoiser"
      echo  removed -^> %%D\plugins
      set /a COUNT+=1
    )
  )
)

echo.
if !COUNT! GTR 0 (
  echo [OK] Removed from !COUNT! location^(s^). Restart Cinema 4D.
) else (
  echo [i] Nothing to remove ^(plugin not found^).
)
echo.
pause
exit /b 0
