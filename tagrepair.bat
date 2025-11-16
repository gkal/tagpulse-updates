@echo off
REM Emergency Fleet Rescue Script v1.0
REM This script bypasses the normal update system and directly downloads/installs emergency fixes
REM Use when the fleet has broken update mechanisms

setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"

echo:
echo ==========================================
echo   TagPulse Emergency Fleet Rescue v1.0
echo ==========================================
echo:
echo This script will:
echo 1. Stop all TagPulse services
echo 2. Download emergency files from GitHub
echo 3. Replace broken executables
echo 4. Restart services
echo.

REM Get the current version for backup purposes
echo Detecting current TagPulse version...
for /f "tokens=3" %%i in ('reg query "HKLM\SOFTWARE\TagPulse\Components" /v Service 2^>nul') do set "CURRENT_VERSION=%%i"
if "%CURRENT_VERSION%"=="" (
    echo ERROR: Could not detect TagPulse version from registry
    echo Please run this script on a machine with TagPulse installed
    pause
    exit /b 1
)

echo Detected problematic version: %CURRENT_VERSION%
echo Will download latest stable version to replace broken installation
echo Stable URL: https://raw.githubusercontent.com/gkal/tagpulse-updates/main/stable
echo:

REM Ask for confirmation
choice /M "Continue with emergency rescue using latest stable version"
if errorlevel 2 exit /b 0

echo:
echo === STEP 1: Stopping TagPulse Services ===
net stop "TagPulseService" 2>nul
net stop "TagPulseLHMService" 2>nul
taskkill /F /IM "TagPulse.exe" 2>nul
taskkill /F /IM "TagPulseService.exe" 2>nul
taskkill /F /IM "TagPulseLHMService.exe" 2>nul
taskkill /F /IM "TagPulseUpdater.exe" 2>nul
echo Services stopped.
echo:

REM Create temp directory for downloads
set "TEMP_DIR=%TEMP%\TagPulseEmergencyRescue"
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

echo === STEP 2: Downloading Latest Stable Files ===
echo:

REM Download and parse manifest to get current versions dynamically
set "STABLE_BASE=https://raw.githubusercontent.com/gkal/tagpulse-updates/main/stable"
echo Downloading latest stable manifest...

REM Download both protobuf and textproto versions (textproto is human-readable)
powershell -Command "try { Invoke-WebRequest -Uri '%STABLE_BASE%/manifest.textproto' -OutFile '%TEMP_DIR%\manifest.textproto' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 (
    echo ERROR: Could not download stable manifest
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo Detecting available versions from manifest...

REM Extract version using very simple approach
echo Extracting version from manifest...

REM Get first version line and save to temp file
findstr /C:"version:" "%TEMP_DIR%\manifest.textproto" | findstr /V "timestamp" | findstr /N "." | findstr "^1:" > "%TEMP_DIR%\first_version.txt"

REM Read the line and extract version manually
set /p VERSION_LINE=<"%TEMP_DIR%\first_version.txt"
REM Remove the line number prefix (1:)
set "VERSION_LINE=%VERSION_LINE:~2%"
REM The line looks like: '  version: "0.5.64"'
REM Extract everything between the quotes
for /f "tokens=2" %%a in ("%VERSION_LINE%") do set "QUOTED_VER=%%a"
REM Remove quotes by taking substring (skip first char, remove last char)
set "CLEAN_VER=%QUOTED_VER:~1,-1%"

echo Found common version: %CLEAN_VER%

REM Create individual version files
echo %CLEAN_VER% > "%TEMP_DIR%\desktop_version.txt"
echo %CLEAN_VER% > "%TEMP_DIR%\service_version.txt"
echo %CLEAN_VER% > "%TEMP_DIR%\lhm_version.txt"
echo %CLEAN_VER% > "%TEMP_DIR%\updater_version.txt"
echo %CLEAN_VER% > "%TEMP_DIR%\ui_version.txt"

echo Found component versions:
echo   DESKTOP: %CLEAN_VER%
echo   SERVICE: %CLEAN_VER%  
echo   LHM: %CLEAN_VER%
echo   UPDATER: %CLEAN_VER%
echo   UI: %CLEAN_VER%

echo Component versions detected successfully.
echo Will replace broken version %CURRENT_VERSION% with latest stable components
echo:

REM Download each component using simpler approach
echo Downloading stable components...

REM Create dynamic download script using parsed versions
echo $base = "%STABLE_BASE%" > "%TEMP_DIR%\download.ps1"
echo $tempDir = "%TEMP_DIR%" >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo try { >> "%TEMP_DIR%\download.ps1"
echo     $desktopVer = (Get-Content "$tempDir\desktop_version.txt").Trim() >> "%TEMP_DIR%\download.ps1"
echo     $serviceVer = (Get-Content "$tempDir\service_version.txt").Trim() >> "%TEMP_DIR%\download.ps1"
echo     $lhmVer = (Get-Content "$tempDir\lhm_version.txt").Trim() >> "%TEMP_DIR%\download.ps1"
echo     $updaterVer = (Get-Content "$tempDir\updater_version.txt").Trim() >> "%TEMP_DIR%\download.ps1"
echo     $uiVer = (Get-Content "$tempDir\ui_version.txt").Trim() >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Downloading components with current stable versions...' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo     Write-Host " " >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     $ProgressPreference = 'SilentlyContinue' >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     Write-Host "Downloading updater component v$updaterVer" >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/updater-$updaterVer.exe" -OutFile "$tempDir\updater.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ Updater downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     Write-Host "Downloading UI component v$uiVer" >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/ui-$uiVer.zip" -OutFile "$tempDir\ui.zip" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ UI downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     Write-Host "Downloading desktop component v$desktopVer" >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/desktop-$desktopVer.exe" -OutFile "$tempDir\desktop.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ Desktop downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     Write-Host "Downloading service component v$serviceVer" >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/service-$serviceVer.exe" -OutFile "$tempDir\service.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ Service downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     Write-Host "Downloading LHM component v$lhmVer - This may take a few minutes" -ForegroundColor Yellow >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/lhm-$lhmVer.exe" -OutFile "$tempDir\lhm.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ LHM downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo: >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'All downloads completed successfully' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo } catch { >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Download failed' -ForegroundColor Red >> "%TEMP_DIR%\download.ps1"
echo     Write-Host $_.Exception.Message -ForegroundColor Red >> "%TEMP_DIR%\download.ps1"
echo     exit 1 >> "%TEMP_DIR%\download.ps1"
echo } >> "%TEMP_DIR%\download.ps1"

echo Running download script...
echo:
echo Download Progress: Total size ~84 MB (LHM component is 69 MB)
echo Please wait - this may take 2-5 minutes depending on connection speed...
echo:
@powershell -ExecutionPolicy Bypass -File "%TEMP_DIR%\download.ps1"
if errorlevel 1 (
    echo ERROR: Failed to download components
    goto :cleanup
)

echo All components downloaded successfully.
echo:

echo === STEP 3: Installing Emergency Files ===
echo:

REM Detect TagPulse installation directory
set "INSTALL_DIR="
for /f "tokens=3*" %%i in ('reg query "HKLM\SOFTWARE\TagPulse" /v InstallPath 2^>nul') do set "INSTALL_DIR=%%i %%j"
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=C:\Program Files\TagPulse"

echo Installing to: %INSTALL_DIR%
echo:

REM Skip backup - this is emergency rescue for broken installations

echo   1. Installing desktop component...
copy "%TEMP_DIR%\desktop.exe" "%INSTALL_DIR%\bin\TagPulse.exe" /Y
if errorlevel 1 (
    echo ERROR: Failed to install desktop component
    goto :cleanup
)

echo   2. Installing service component...
copy "%TEMP_DIR%\service.exe" "%INSTALL_DIR%\bin\TagPulseService.exe" /Y
if errorlevel 1 (
    echo ERROR: Failed to install service component
    goto :cleanup
)

echo   3. Installing LHM component...
copy "%TEMP_DIR%\lhm.exe" "%INSTALL_DIR%\bin\TagPulseLHMService.exe" /Y
if errorlevel 1 (
    echo ERROR: Failed to install LHM component
    goto :cleanup
)

echo   4. Installing updater component...
copy "%TEMP_DIR%\updater.exe" "%INSTALL_DIR%\bin\TagPulseUpdater.exe" /Y
if errorlevel 1 (
    echo ERROR: Failed to install updater component
    goto :cleanup
)

echo   5. Installing UI component...
REM Extract UI component
powershell -Command "Expand-Archive -Path '%TEMP_DIR%\ui.zip' -DestinationPath '%INSTALL_DIR%\ui' -Force"
if errorlevel 1 (
    echo ERROR: Failed to install UI component
    goto :cleanup
)

echo All components installed successfully.
echo:

echo === STEP 4: Updating Registry Versions ===

REM Read actual versions that were installed
set /p DESKTOP_VER=<"%TEMP_DIR%\desktop_version.txt"
set /p SERVICE_VER=<"%TEMP_DIR%\service_version.txt"  
set /p LHM_VER=<"%TEMP_DIR%\lhm_version.txt"
set /p UPDATER_VER=<"%TEMP_DIR%\updater_version.txt"
set /p UI_VER=<"%TEMP_DIR%\ui_version.txt"

echo Updating registry with component-specific versions:
echo   Desktop: %DESKTOP_VER%
echo   Service: %SERVICE_VER%
echo   LHM: %LHM_VER%
echo   Updater: %UPDATER_VER%
echo   UI: %UI_VER%

reg add "HKLM\SOFTWARE\TagPulse\Components" /v Desktop /t REG_SZ /d "%DESKTOP_VER%" /f >nul
reg add "HKLM\SOFTWARE\TagPulse\Components" /v Service /t REG_SZ /d "%SERVICE_VER%" /f >nul
reg add "HKLM\SOFTWARE\TagPulse\Components" /v LHM /t REG_SZ /d "%LHM_VER%" /f >nul
reg add "HKLM\SOFTWARE\TagPulse\Components" /v Updater /t REG_SZ /d "%UPDATER_VER%" /f >nul
reg add "HKLM\SOFTWARE\TagPulse\Components" /v UI /t REG_SZ /d "%UI_VER%" /f >nul
echo Registry updated with actual component versions
echo:

echo === STEP 5: Starting TagPulse Services ===
net start "TagPulseService"
if errorlevel 1 (
    echo WARNING: TagPulseService failed to start - check logs
) else (
    echo TagPulseService started successfully
)
echo:

echo === EMERGENCY RESCUE COMPLETED ===
echo:
echo Summary:
echo - Previous problematic version: %CURRENT_VERSION%
echo - Updated to stable version: %CLEAN_VER%
echo - Installation: %INSTALL_DIR%
echo - No backup created (emergency rescue mode)
echo:
echo The emergency rescue is complete!
echo TagPulse should now be running with the latest stable version.
echo:

:cleanup
echo Cleaning up temporary files...
rmdir /s /q "%TEMP_DIR%" 2>nul

echo:
echo Press any key to exit...
pause >nul
exit /b 0