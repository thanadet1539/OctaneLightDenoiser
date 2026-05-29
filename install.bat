@echo off
setlocal enabledelayedexpansion
title Octane Light Denoiser - Installer

set "SRC=%~dp0OctaneLightDenoiser"
if not exist "%SRC%\octanelightdenoiser.pyp" (
  echo [!] Could not find OctaneLightDenoiser next to this installer.
  pause & exit /b 1
)

echo ============================================================
echo   Octane Light Denoiser - Installer
echo ============================================================
echo.

set "MAXON=%APPDATA%\Maxon"
if not exist "%MAXON%" (
  echo [!] "%MAXON%" not found. Copy the OctaneLightDenoiser folder into your
  echo     C4D plugins folder manually, then restart Cinema 4D.
  pause & exit /b 1
)

set /a COUNT=0
for /d %%D in ("%MAXON%\*") do (
  if exist "%%D\plugins\" (
    call :install "%%~fD"
  ) else if exist "%%D\prefs\" (
    call :install "%%~fD"
  )
)

echo.
if !COUNT! GTR 0 (
  echo [OK] Installed into !COUNT! Cinema 4D location^(s^).
  echo      Restart Cinema 4D, then: Extensions menu -^> Octane Light Denoiser
) else (
  echo [!] No Cinema 4D folders detected under "%MAXON%".
  echo     Copy the OctaneLightDenoiser folder into your C4D plugins folder manually.
)
echo.
pause
exit /b 0

:install
set "TARGET=%~1\plugins"
set "DEST=%TARGET%\OctaneLightDenoiser"
if not exist "%TARGET%" mkdir "%TARGET%"
if exist "%DEST%" rmdir /s /q "%DEST%"
xcopy /e /i /y /q "%SRC%" "%DEST%" >nul
if exist "%DEST%\octanelightdenoiser.pyp" (
  echo  installed -^> %TARGET%
  set /a COUNT+=1
) else (
  echo  [!] copy failed -^> %TARGET%
)
exit /b
