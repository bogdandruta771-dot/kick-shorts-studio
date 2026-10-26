@echo off
setlocal enabledelayedexpansion
title OmniStudio - Master Hub Launcher

echo ============================================================
echo   ⚡ OmniStudio - Master Stream Clipper & Motion Explainer
echo ============================================================
echo.

cd /d "%~dp0"

:: 1. Verify Python availability
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not in PATH!
        echo Please install Python 3.10+ and re-run.
        pause
        exit /b 1
    ) else (
        set "PYTHON_EXE=py"
    )
) else (
    set "PYTHON_EXE=python"
)

:: 2. Prepend local bin directory for FFmpeg
set "PATH=%~dp0bin;%PATH%"

:: 3. Launch Standalone Desktop App or Web App
if "%1"=="--browser" (
    echo [LAUNCH] Starting OmniStudio in browser mode at http://127.0.0.1:7860...
    %PYTHON_EXE% app.py
) else (
    echo [LAUNCH] Starting OmniStudio Standalone Desktop App...
    if exist "OmniStudio.exe" (
        start "" "OmniStudio.exe"
    ) else (
        %PYTHON_EXE% desktop_app.py
    )
)

if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] Application closed or exited with code %errorlevel%.
)
