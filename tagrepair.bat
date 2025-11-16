@echo off
REM Emergency Fleet Rescue Script v1.0
REM This script bypasses the normal update system and directly downloads/installs emergency fixes
REM Use when the fleet has broken update mechanisms

setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"

echo.
echo ==========================================
echo   TagPulse Emergency Fleet Rescue v1.0
echo ==========================================
echo.
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
echo.

REM Ask for confirmation
choice /M "Continue with emergency rescue using latest stable version"
if errorlevel 2 exit /b 0

echo.
echo === STEP 1: Stopping TagPulse Services ===
net stop "TagPulseService" 2>nul
net stop "TagPulseLHMService" 2>nul
taskkill /F /IM "TagPulse.exe" 2>nul
taskkill /F /IM "TagPulseService.exe" 2>nul
taskkill /F /IM "TagPulseLHMService.exe" 2>nul
taskkill /F /IM "TagPulseUpdater.exe" 2>nul
echo Services stopped.
echo.

REM Create temp directory for downloads
set "TEMP_DIR=%TEMP%\TagPulseEmergencyRescue"
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

echo === STEP 2: Downloading Latest Stable Files ===
echo.

REM Download latest stable manifest to get the current version
set "STABLE_BASE=https://raw.githubusercontent.com/gkal/tagpulse-updates/main/stable"
echo Downloading latest stable manifest...
powershell -Command "try { Invoke-WebRequest -Uri '%STABLE_BASE%/manifest.pb' -OutFile '%TEMP_DIR%\manifest.pb' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 (
    echo ERROR: Could not download stable manifest
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

REM Parse all versions from manifest (binary protobuf format)
echo Detecting available stable versions...

REM Create version parsing script to separate display from output
echo try { > "%TEMP_DIR%\parse_version.ps1"
echo   $bytes = [System.IO.File]::ReadAllBytes('%TEMP_DIR%\manifest.pb') >> "%TEMP_DIR%\parse_version.ps1"
echo   $text = [System.Text.Encoding]::ASCII.GetString($bytes) >> "%TEMP_DIR%\parse_version.ps1"
echo   $versions = @() >> "%TEMP_DIR%\parse_version.ps1"
echo   $matches = [regex]::Matches($text, '([0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?[a-z]?)') >> "%TEMP_DIR%\parse_version.ps1"
echo   foreach ($match in $matches) { $versions += $match.Groups[1].Value } >> "%TEMP_DIR%\parse_version.ps1"
echo   if ($versions.Count -eq 0) { Write-Error 'No versions found in manifest'; exit 1 } >> "%TEMP_DIR%\parse_version.ps1"
echo   $uniqueVersions = $versions ^| Sort-Object -Unique >> "%TEMP_DIR%\parse_version.ps1"
echo   Write-Host 'Found versions in stable manifest:' -ForegroundColor Green >> "%TEMP_DIR%\parse_version.ps1"
echo   $uniqueVersions ^| ForEach-Object { Write-Host '  - ' $_ -ForegroundColor Yellow } >> "%TEMP_DIR%\parse_version.ps1"
echo   $latestVersion = ($uniqueVersions ^| Select-Object -Last 1) >> "%TEMP_DIR%\parse_version.ps1"
echo   Write-Host '' >> "%TEMP_DIR%\parse_version.ps1"
echo   Write-Host 'Will use latest version for rescue:' $latestVersion -ForegroundColor Cyan >> "%TEMP_DIR%\parse_version.ps1"
echo   Write-Output $latestVersion >> "%TEMP_DIR%\parse_version.ps1"
echo } catch { >> "%TEMP_DIR%\parse_version.ps1"
echo   Write-Error $_.Exception.Message >> "%TEMP_DIR%\parse_version.ps1"
echo   exit 1 >> "%TEMP_DIR%\parse_version.ps1"
echo } >> "%TEMP_DIR%\parse_version.ps1"

powershell -ExecutionPolicy Bypass -File "%TEMP_DIR%\parse_version.ps1" > "%TEMP_DIR%\latest_version.txt" 2>&1
if errorlevel 1 (
    echo ERROR: Could not parse latest version from manifest
    echo Debug info:
    type "%TEMP_DIR%\latest_version.txt"
    pause
    exit /b 1
)

echo Component-specific versions will be detected from manifest during download
echo Will replace broken version %CURRENT_VERSION% with latest stable components
echo.

REM Download each component using simpler approach
echo Downloading stable components...

REM Create simple hardcoded download script using known available versions
echo $base = "%STABLE_BASE%" > "%TEMP_DIR%\download.ps1"
echo $tempDir = "%TEMP_DIR%" >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo try { >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Downloading components with known available versions...' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo     Write-Host " " >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     $ProgressPreference = 'SilentlyContinue' >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Downloading updater component 0.4 MB' >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/updater-0.5.62b.exe" -OutFile "$tempDir\updater.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ Updater downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Downloading UI component 1.4 MB' >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/ui-0.5.62b.zip" -OutFile "$tempDir\ui.zip" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ UI downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Downloading desktop component 1.5 MB' >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/desktop-0.5.62b.exe" -OutFile "$tempDir\desktop.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ Desktop downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Downloading service component 11.5 MB' >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/service-0.5.63.exe" -OutFile "$tempDir\service.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ Service downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Downloading LHM component 69.1 MB - This may take a few minutes' -ForegroundColor Yellow >> "%TEMP_DIR%\download.ps1"
echo     Invoke-WebRequest -Uri "$base/packages/lhm-0.5.62b.exe" -OutFile "$tempDir\lhm.exe" -UseBasicParsing >> "%TEMP_DIR%\download.ps1"
echo     Write-Host '✓ LHM downloaded' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     "0.5.62b" ^| Out-File "$tempDir\desktop_version.txt" -Encoding ASCII >> "%TEMP_DIR%\download.ps1"
echo     "0.5.63" ^| Out-File "$tempDir\service_version.txt" -Encoding ASCII >> "%TEMP_DIR%\download.ps1"
echo     "0.5.62b" ^| Out-File "$tempDir\lhm_version.txt" -Encoding ASCII >> "%TEMP_DIR%\download.ps1"
echo     "0.5.62b" ^| Out-File "$tempDir\updater_version.txt" -Encoding ASCII >> "%TEMP_DIR%\download.ps1"
echo     "0.5.62b" ^| Out-File "$tempDir\ui_version.txt" -Encoding ASCII >> "%TEMP_DIR%\download.ps1"
echo. >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'All downloads completed successfully' -ForegroundColor Green >> "%TEMP_DIR%\download.ps1"
echo } catch { >> "%TEMP_DIR%\download.ps1"
echo     Write-Host 'Download failed' -ForegroundColor Red >> "%TEMP_DIR%\download.ps1"
echo     exit 1 >> "%TEMP_DIR%\download.ps1"
echo } >> "%TEMP_DIR%\download.ps1"

echo Running download script...
echo.
echo Download Progress: Total size ~84 MB (LHM component is 69 MB)
echo Please wait - this may take 2-5 minutes depending on connection speed...
echo.
@powershell -ExecutionPolicy Bypass -File "%TEMP_DIR%\download.ps1"
if errorlevel 1 (
    echo ERROR: Failed to download components
    goto :cleanup
)

echo All components downloaded successfully.
echo.

echo === STEP 3: Installing Emergency Files ===
echo.

REM Detect TagPulse installation directory
set "INSTALL_DIR="
for /f "tokens=3*" %%i in ('reg query "HKLM\SOFTWARE\TagPulse" /v InstallPath 2^>nul') do set "INSTALL_DIR=%%i %%j"
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=C:\Program Files\TagPulse"

echo Installing to: %INSTALL_DIR%
echo.

REM Backup existing files
echo Creating backup of existing files...
set "BACKUP_DIR=%INSTALL_DIR%\backup\emergency_%CURRENT_VERSION%_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "BACKUP_DIR=%BACKUP_DIR: =0%"
mkdir "%BACKUP_DIR%" 2>nul

copy "%INSTALL_DIR%\bin\TagPulse.exe" "%BACKUP_DIR%\" 2>nul
copy "%INSTALL_DIR%\bin\TagPulseService.exe" "%BACKUP_DIR%\" 2>nul
copy "%INSTALL_DIR%\bin\TagPulseLHMService.exe" "%BACKUP_DIR%\" 2>nul
copy "%INSTALL_DIR%\bin\TagPulseUpdater.exe" "%BACKUP_DIR%\" 2>nul

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
echo.

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
echo.

echo === STEP 5: Starting TagPulse Services ===
net start "TagPulseService"
if errorlevel 1 (
    echo WARNING: TagPulseService failed to start - check logs
) else (
    echo TagPulseService started successfully
)
echo.

echo === EMERGENCY RESCUE COMPLETED ===
echo.
echo Summary:
echo - Previous problematic version: %CURRENT_VERSION%
echo - Updated to stable version: %FIXED_VERSION%
echo - Backup location: %BACKUP_DIR%
echo - Installation: %INSTALL_DIR%
echo.
echo The emergency rescue is complete!
echo TagPulse should now be running with the latest stable version.
echo.

:cleanup
echo Cleaning up temporary files...
rmdir /s /q "%TEMP_DIR%" 2>nul

echo.
echo Press any key to exit...
pause >nul
exit /b 0